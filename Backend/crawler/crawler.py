"""
Core web crawler.

Async breadth-first crawler with:
  - Configurable depth, page count, and concurrency limits
  - Same-host enforcement (optional)
  - robots.txt compliance
  - SSRF hardening (rejects loopback / private IPs)
  - HTML link extraction via BeautifulSoup
"""
from __future__ import annotations

import asyncio
import ipaddress
import logging
import re
import socket
import time
from typing import Callable, Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import aiohttp
from bs4 import BeautifulSoup

from crawler.models import CrawlOptions, CrawlResult, PageResult

log = logging.getLogger(__name__)

# IPs we refuse to connect to (SSRF protection)
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),       # loopback
    ipaddress.ip_network("10.0.0.0/8"),         # private class A
    ipaddress.ip_network("172.16.0.0/12"),      # private class B
    ipaddress.ip_network("192.168.0.0/16"),     # private class C
    ipaddress.ip_network("169.254.0.0/16"),     # link-local
    ipaddress.ip_network("::1/128"),            # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),           # IPv6 ULA
    ipaddress.ip_network("fe80::/10"),          # IPv6 link-local
]


def is_private_ip(hostname: str) -> bool:
    """Resolve hostname and check if it points to a blocked/private IP."""
    try:
        infos = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for family, _, _, _, sockaddr in infos:
            ip = ipaddress.ip_address(sockaddr[0])
            for net in _BLOCKED_NETWORKS:
                if ip in net:
                    return True
    except (socket.gaierror, OSError, ValueError):
        return True  # if we can't resolve, treat as blocked
    return False


def normalize_url(url: str) -> str:
    """Normalize a URL: lowercase scheme+host, strip fragments, trailing slashes."""
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    host = parsed.netloc.lower()
    path = parsed.path.rstrip("/") or "/"
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{scheme}://{host}{path}{query}"


def extract_links(html: str, base_url: str) -> list[str]:
    """Extract and resolve all <a href=...> links from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme in ("http", "https"):
            links.append(normalize_url(absolute))
    return list(set(links))  # deduplicate


def extract_title(html: str) -> str:
    """Extract the <title> text from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.find("title")
    return title_tag.get_text(strip=True) if title_tag else ""


def extract_text_snippet(html: str, max_len: int = 500) -> str:
    """Extract visible body text, return first max_len chars."""
    soup = BeautifulSoup(html, "html.parser")
    # Remove script/style elements
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len]


async def _fetch_robots(session: aiohttp.ClientSession, base_url: str, user_agent: str) -> Optional[RobotFileParser]:
    """Fetch and parse robots.txt for a host."""
    parsed = urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        async with session.get(robots_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                text = await resp.text()
                rp = RobotFileParser()
                rp.parse(text.splitlines())
                return rp
    except Exception:
        pass
    return None


async def _crawl_page(
    session: aiohttp.ClientSession,
    url: str,
    timeout: int,
) -> tuple[int, str, str]:
    """Fetch a page, return (status_code, content_type, body_text)."""
    async with session.get(
        url,
        timeout=aiohttp.ClientTimeout(total=timeout),
        allow_redirects=True,
        max_redirects=5,
    ) as resp:
        content_type = resp.content_type or ""
        body = ""
        if "text/html" in content_type:
            body = await resp.text(errors="replace")
        return resp.status, content_type, body


async def crawl(
    options: CrawlOptions,
    on_page: Optional[Callable[[PageResult], None]] = None,
    on_status: Optional[Callable[[str], None]] = None,
    cancel_event: Optional[asyncio.Event] = None,
) -> CrawlResult:
    """
    Breadth-first async web crawler.

    Args:
        options:       Crawl configuration.
        on_page:       Optional callback per page crawled.
        on_status:     Optional callback for status messages.
        cancel_event:  Set this event to cancel the crawl mid-run.

    Returns:
        CrawlResult with all page data.
    """
    start_time = time.monotonic()
    result = CrawlResult(start_url=options.start_url)

    start_parsed = urlparse(options.start_url)
    start_host = start_parsed.netloc.lower()

    # SSRF check on start URL
    hostname = start_parsed.hostname or ""
    if is_private_ip(hostname):
        raise ValueError(
            f"SSRF protection: {options.start_url!r} resolves to a private/loopback IP. "
            "Crawling private networks is blocked."
        )

    # Robots.txt cache per host
    robots_cache: dict[str, Optional[RobotFileParser]] = {}

    # BFS state
    visited: set[str] = set()
    queue: asyncio.Queue[tuple[str, int]] = asyncio.Queue()
    await queue.put((normalize_url(options.start_url), 0))
    semaphore = asyncio.Semaphore(options.concurrency)

    connector = aiohttp.TCPConnector(limit=options.concurrency, ttl_dns_cache=300)
    async with aiohttp.ClientSession(
        connector=connector,
        headers={"User-Agent": options.user_agent},
    ) as session:
        # Pre-fetch robots.txt for the start host
        if options.respect_robots:
            robots_cache[start_host] = await _fetch_robots(session, options.start_url, options.user_agent)

        async def process_url(url: str, depth: int) -> None:
            if cancel_event and cancel_event.is_set():
                return

            norm = normalize_url(url)
            if norm in visited:
                return
            visited.add(norm)

            if result.pages_crawled + result.pages_failed >= options.max_pages:
                return

            parsed = urlparse(norm)
            host = parsed.netloc.lower()

            # Same-host check
            if options.same_host_only and host != start_host:
                return

            # SSRF check
            host_name = parsed.hostname or ""
            if is_private_ip(host_name):
                log.warning("SSRF blocked: %s", norm)
                return

            # Robots.txt check
            if options.respect_robots:
                if host not in robots_cache:
                    robots_cache[host] = await _fetch_robots(session, norm, options.user_agent)
                rp = robots_cache.get(host)
                if rp and not rp.can_fetch(options.user_agent, norm):
                    log.debug("Blocked by robots.txt: %s", norm)
                    return

            page = PageResult(url=norm, depth=depth)
            page_start = time.monotonic()

            try:
                async with semaphore:
                    status, content_type, body = await _crawl_page(session, norm, options.timeout_seconds)

                page.status_code = status
                page.content_type = content_type
                page.elapsed_ms = int((time.monotonic() - page_start) * 1000)

                if body:
                    page.title = extract_title(body)
                    page.text_snippet = extract_text_snippet(body)

                    if depth < options.max_depth:
                        links = extract_links(body, norm)
                        page.links_found = links
                        for link in links:
                            if normalize_url(link) not in visited:
                                await queue.put((link, depth + 1))

                result.pages_crawled += 1
                if on_status:
                    on_status(f"Crawled [{result.pages_crawled}]: {norm}")

            except Exception as e:
                page.error = str(e)
                page.elapsed_ms = int((time.monotonic() - page_start) * 1000)
                result.pages_failed += 1
                log.debug("Error crawling %s: %s", norm, e)

            result.pages.append(page)
            if on_page:
                on_page(page)

        # BFS loop
        while not queue.empty():
            if cancel_event and cancel_event.is_set():
                result.cancelled = True
                break

            if result.pages_crawled + result.pages_failed >= options.max_pages:
                break

            # Drain up to `concurrency` items from queue
            batch: list[tuple[str, int]] = []
            while not queue.empty() and len(batch) < options.concurrency:
                batch.append(await queue.get())

            tasks = [process_url(url, depth) for url, depth in batch]
            await asyncio.gather(*tasks)

    result.elapsed_seconds = round(time.monotonic() - start_time, 2)
    return result
