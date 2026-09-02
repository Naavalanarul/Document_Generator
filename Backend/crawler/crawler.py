"""
Core web scraper.

Scrapling-based single-page scraper with:
  - SSRF hardening (rejects loopback / private IPs)
  - Retry/timeout controls delegated to Scrapling AsyncFetcher
  - CSS-based content extraction inspired by Scrapling's parser flow
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

from scrapling import Selector
from scrapling.fetchers import AsyncFetcher
import trafilatura

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
            _ = family
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
    selector = Selector(content=html, url=base_url)
    links = []
    for href in selector.css("a::attr(href)").getall():
        cleaned = href.strip()
        if not cleaned or cleaned.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        absolute = urljoin(base_url, cleaned)
        parsed = urlparse(absolute)
        if parsed.scheme in ("http", "https"):
            links.append(normalize_url(absolute))
    return list(set(links))


def extract_title(html: str) -> str:
    """Extract the <title> text from HTML."""
    selector = Selector(content=html, url="https://example.com/")
    return (selector.css("title::text").get(default="") or "").strip()


def extract_text_snippet(html: str, max_len: int = 500) -> str:
    """Extract visible body text, return first max_len chars."""
    cleaned_html = re.sub(
        r"<(script|style|nav|header|footer)\b[^>]*>.*?</\1>",
        " ",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    text = trafilatura.extract(
        cleaned_html,
        include_comments=False,
        include_links=False,
        favor_recall=True,
        output_format="txt",
    ) or ""
    if not text:
        selector = Selector(content=cleaned_html, url="https://example.com/")
        text = " ".join(selector.css("body ::text").getall())
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len]


async def crawl(
    options: CrawlOptions,
    on_page: Optional[Callable[[PageResult], None]] = None,
    on_status: Optional[Callable[[str], None]] = None,
    cancel_event: Optional[asyncio.Event] = None,
) -> CrawlResult:
    """
    Scrapling-based async web scraper.

    Args:
        options:       Scrape configuration.
        on_page:       Optional callback per page scraped.
        on_status:     Optional callback for status messages.
        cancel_event:  Set this event to cancel the scrape.

    Returns:
        CrawlResult with the scraped page data.
    """
    start_time = time.monotonic()
    result = CrawlResult(start_url=options.start_url)
    target_url = normalize_url(options.start_url)
    parsed_start = urlparse(target_url)
    start_host = parsed_start.netloc.lower()
    page = PageResult(url=target_url, depth=0)
    page_start = time.monotonic()

    if cancel_event and cancel_event.is_set():
        result.cancelled = True
        result.elapsed_seconds = round(time.monotonic() - start_time, 2)
        return result

    hostname = parsed_start.hostname or ""
    if is_private_ip(hostname):
        raise ValueError(
            f"SSRF protection: {options.start_url!r} resolves to a private/loopback IP. "
            "Scraping private networks is blocked."
        )

    try:
        response = await AsyncFetcher.get(
            target_url,
            timeout=options.timeout_seconds,
            retries=options.retries,
            retry_delay=options.retry_delay_seconds,
            follow_redirects="safe" if options.follow_redirects else False,
            headers={"User-Agent": options.user_agent},
            stealthy_headers=True,
        )

        final_url = normalize_url(response.url)
        final_host = urlparse(final_url).hostname or ""
        if is_private_ip(final_host):
            raise ValueError(
                f"SSRF protection: redirect target {final_url!r} resolves to a private/loopback IP."
            )

        page.url = final_url
        page.status_code = int(getattr(response, "status", 0) or 0)
        page.content_type = str(response.headers.get("content-type", ""))
        page.elapsed_ms = int((time.monotonic() - page_start) * 1000)

        if "text/html" in page.content_type.lower():
            html = response.html_content
            page.title = extract_title(html)
            page.text_snippet = extract_text_snippet(html)
            links = extract_links(html, final_url)
            if options.same_host_only:
                links = [l for l in links if urlparse(l).netloc.lower() == start_host]
            page.links_found = links

        result.pages_crawled = 1
        if on_status:
            on_status(f"Scraped [1]: {final_url}")

    except Exception as e:
        page.error = str(e)
        page.elapsed_ms = int((time.monotonic() - page_start) * 1000)
        result.pages_failed = 1
        log.debug("Error scraping %s: %s", target_url, e)

    result.pages.append(page)
    if on_page:
        on_page(page)

    if cancel_event and cancel_event.is_set():
        result.cancelled = True

    result.elapsed_seconds = round(time.monotonic() - start_time, 2)
    return result
