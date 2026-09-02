"""
Tests for the web scraper.

Covers:
  - URL normalization
  - SSRF rejection (loopback, private IPs)
  - Link extraction
  - Title & text snippet extraction
  - CrawlOptions validation
  - Scrapling-backed scraping flow
  - DB schema (SQL logic via plain sqlite3)
"""
import os
import asyncio
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.pop("API_KEY", None)
os.environ["DEV_MODE"] = "1"

import pytest
from pydantic import ValidationError

from crawler.models import CrawlOptions, PageResult, CrawlResult, CrawlJob, JobStatus
from crawler.crawler import (
    crawl,
    normalize_url,
    extract_links,
    extract_title,
    extract_text_snippet,
    is_private_ip,
)


# ── URL Normalization ──────────────────────────────────────────────────────────

class TestNormalizeUrl:
    def test_strips_fragment(self):
        assert normalize_url("https://example.com/page#section") == "https://example.com/page"

    def test_lowercases_scheme_and_host(self):
        assert normalize_url("HTTPS://EXAMPLE.COM/Path") == "https://example.com/Path"

    def test_strips_trailing_slash(self):
        assert normalize_url("https://example.com/page/") == "https://example.com/page"

    def test_preserves_query(self):
        assert normalize_url("https://example.com/search?q=test") == "https://example.com/search?q=test"

    def test_root_path(self):
        assert normalize_url("https://example.com") == "https://example.com/"

    def test_root_path_with_trailing_slash(self):
        assert normalize_url("https://example.com/") == "https://example.com/"


# ── SSRF Protection ───────────────────────────────────────────────────────────

class TestSSRFProtection:
    def test_loopback_ipv4_blocked(self):
        assert is_private_ip("127.0.0.1") is True

    def test_localhost_blocked(self):
        assert is_private_ip("localhost") is True

    def test_private_class_a_blocked(self):
        assert is_private_ip("10.0.0.1") is True

    def test_private_class_b_blocked(self):
        assert is_private_ip("172.16.0.1") is True

    def test_private_class_c_blocked(self):
        assert is_private_ip("192.168.1.1") is True

    def test_public_ip_allowed(self):
        assert is_private_ip("93.184.216.34") is False

    def test_unresolvable_host_blocked(self):
        assert is_private_ip("this-host-definitely-does-not-exist-xyz123.invalid") is True


# ── HTML Parsing ───────────────────────────────────────────────────────────────

SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head><title>Test Page</title></head>
<body>
  <nav>Navigation</nav>
  <h1>Hello World</h1>
  <p>This is a test page with some content.</p>
  <a href="/about">About</a>
  <a href="https://other.com/page">External</a>
  <a href="#top">Anchor</a>
  <a href="mailto:test@example.com">Email</a>
  <a href="relative/path">Relative</a>
  <script>var x = 1;</script>
</body>
</html>
"""


class TestExtractLinks:
    def test_resolves_relative_links(self):
        links = extract_links(SAMPLE_HTML, "https://example.com/current")
        assert "https://example.com/about" in links

    def test_includes_absolute_links(self):
        links = extract_links(SAMPLE_HTML, "https://example.com/")
        assert "https://other.com/page" in links

    def test_skips_fragments(self):
        links = extract_links(SAMPLE_HTML, "https://example.com/")
        assert not any("#top" in l for l in links)

    def test_skips_mailto(self):
        links = extract_links(SAMPLE_HTML, "https://example.com/")
        assert not any("mailto:" in l for l in links)

    def test_resolves_relative_paths(self):
        links = extract_links(SAMPLE_HTML, "https://example.com/dir/")
        assert "https://example.com/dir/relative/path" in links


class TestExtractTitle:
    def test_extracts_title(self):
        assert extract_title(SAMPLE_HTML) == "Test Page"

    def test_no_title(self):
        assert extract_title("<html><body>No title</body></html>") == ""


class TestExtractTextSnippet:
    def test_extracts_visible_text(self):
        snippet = extract_text_snippet(SAMPLE_HTML)
        assert "Hello World" in snippet
        assert "test page" in snippet

    def test_strips_script(self):
        snippet = extract_text_snippet(SAMPLE_HTML)
        assert "var x" not in snippet

    def test_strips_nav(self):
        snippet = extract_text_snippet(SAMPLE_HTML)
        assert "Navigation" not in snippet

    def test_max_length(self):
        snippet = extract_text_snippet(SAMPLE_HTML, max_len=10)
        assert len(snippet) <= 10


# ── CrawlOptions Validation ───────────────────────────────────────────────────

class TestCrawlOptions:
    def test_defaults(self):
        opts = CrawlOptions(start_url="https://example.com")
        assert opts.retries == 2
        assert opts.timeout_seconds == 15
        assert opts.same_host_only is True

    def test_timeout_bounds(self):
        with pytest.raises(ValidationError):
            CrawlOptions(start_url="https://example.com", timeout_seconds=0)
        with pytest.raises(ValidationError):
            CrawlOptions(start_url="https://example.com", timeout_seconds=121)

    def test_retries_bounds(self):
        with pytest.raises(ValidationError):
            CrawlOptions(start_url="https://example.com", retries=-1)
        with pytest.raises(ValidationError):
            CrawlOptions(start_url="https://example.com", retries=11)

    def test_retry_delay_bounds(self):
        with pytest.raises(ValidationError):
            CrawlOptions(start_url="https://example.com", retry_delay_seconds=-0.1)


class _FakeResponse:
    def __init__(self, url: str, status: int, headers: dict[str, str], html_content: str):
        self.url = url
        self.status = status
        self.headers = headers
        self.html_content = html_content


class TestScrapeFlow:
    def test_scrape_uses_scrapling_fetcher(self, monkeypatch):
        calls = []

        async def fake_get(url, **kwargs):
            calls.append((url, kwargs))
            return _FakeResponse(
                url="https://example.com/final",
                status=200,
                headers={"content-type": "text/html; charset=utf-8"},
                html_content=SAMPLE_HTML,
            )

        monkeypatch.setattr("crawler.crawler.AsyncFetcher.get", fake_get)
        monkeypatch.setattr("crawler.crawler.is_private_ip", lambda _hostname: False)
        opts = CrawlOptions(start_url="https://example.com/start")
        result = asyncio.run(crawl(opts))

        assert result.pages_crawled == 1
        assert result.pages_failed == 0
        assert len(result.pages) == 1
        assert result.pages[0].title == "Test Page"
        assert "https://example.com/about" in result.pages[0].links_found
        assert calls[0][1]["timeout"] == opts.timeout_seconds
        assert calls[0][1]["retries"] == opts.retries
        assert calls[0][1]["retry_delay"] == opts.retry_delay_seconds

    def test_scrape_failure_is_recorded(self, monkeypatch):
        async def fake_get(url, **kwargs):
            raise TimeoutError("timed out")

        monkeypatch.setattr("crawler.crawler.AsyncFetcher.get", fake_get)
        monkeypatch.setattr("crawler.crawler.is_private_ip", lambda _hostname: False)
        opts = CrawlOptions(start_url="https://example.com")
        result = asyncio.run(crawl(opts))

        assert result.pages_crawled == 0
        assert result.pages_failed == 1
        assert len(result.pages) == 1
        assert "timed out" in (result.pages[0].error or "")


# ── DB Tests (plain sqlite3 to avoid aiosqlite thread issues in tests) ────────

def _init_test_db() -> sqlite3.Connection:
    """Create a fresh in-memory DB with the crawler schema."""
    schema_path = Path(__file__).resolve().parent.parent / "crawler" / "migrations" / "initial.sql"
    schema = schema_path.read_text()
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(schema)
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


class TestCrawlerDB:
    def test_create_and_get_job(self):
        conn = _init_test_db()
        opts = CrawlOptions(start_url="https://example.com")
        now = time.time()
        conn.execute(
            """INSERT INTO jobs (id, start_url, status, options, pages_crawled,
               pages_failed, error, created_at, finished_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("test-123", opts.start_url, "pending", opts.model_dump_json(), 0, 0, None, now, None),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", ("test-123",)).fetchone()
        assert row is not None
        assert row["start_url"] == "https://example.com"
        assert row["status"] == "pending"

    def test_list_jobs(self):
        conn = _init_test_db()
        opts = CrawlOptions(start_url="https://example.com")
        now = time.time()
        for jid in ("job-1", "job-2", "job-3"):
            conn.execute(
                """INSERT INTO jobs (id, start_url, status, options, pages_crawled,
                   pages_failed, created_at) VALUES (?, ?, ?, ?, 0, 0, ?)""",
                (jid, opts.start_url, "pending", opts.model_dump_json(), now),
            )
        conn.commit()
        rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
        assert len(rows) == 3

    def test_update_job_status(self):
        conn = _init_test_db()
        opts = CrawlOptions(start_url="https://example.com")
        now = time.time()
        conn.execute(
            """INSERT INTO jobs (id, start_url, status, options, pages_crawled,
               pages_failed, created_at) VALUES (?, ?, ?, ?, 0, 0, ?)""",
            ("status-test", opts.start_url, "pending", opts.model_dump_json(), now),
        )
        conn.commit()

        conn.execute("UPDATE jobs SET status = ? WHERE id = ?", ("running", "status-test"))
        conn.commit()
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", ("status-test",)).fetchone()
        assert row["status"] == "running"

        conn.execute(
            "UPDATE jobs SET status = ?, pages_crawled = ?, finished_at = ? WHERE id = ?",
            ("done", 5, time.time(), "status-test"),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", ("status-test",)).fetchone()
        assert row["status"] == "done"
        assert row["pages_crawled"] == 5
        assert row["finished_at"] is not None

    def test_cancel_pending_job(self):
        conn = _init_test_db()
        opts = CrawlOptions(start_url="https://example.com")
        conn.execute(
            """INSERT INTO jobs (id, start_url, status, options, pages_crawled,
               pages_failed, created_at) VALUES (?, ?, ?, ?, 0, 0, ?)""",
            ("cancel-test", opts.start_url, "pending", opts.model_dump_json(), time.time()),
        )
        conn.commit()

        cursor = conn.execute(
            "UPDATE jobs SET status = 'cancelled', finished_at = ? WHERE id = ? AND status IN ('pending', 'running')",
            (time.time(), "cancel-test"),
        )
        conn.commit()
        assert cursor.rowcount == 1
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", ("cancel-test",)).fetchone()
        assert row["status"] == "cancelled"

    def test_cancel_done_job_fails(self):
        conn = _init_test_db()
        opts = CrawlOptions(start_url="https://example.com")
        conn.execute(
            """INSERT INTO jobs (id, start_url, status, options, pages_crawled,
               pages_failed, created_at) VALUES (?, ?, ?, ?, 0, 0, ?)""",
            ("done-job", opts.start_url, "done", opts.model_dump_json(), time.time()),
        )
        conn.commit()
        cursor = conn.execute(
            "UPDATE jobs SET status = 'cancelled' WHERE id = ? AND status IN ('pending', 'running')",
            ("done-job",),
        )
        conn.commit()
        assert cursor.rowcount == 0

    def test_insert_and_get_pages(self):
        conn = _init_test_db()
        opts = CrawlOptions(start_url="https://example.com")
        now = time.time()
        conn.execute(
            """INSERT INTO jobs (id, start_url, status, options, pages_crawled,
               pages_failed, created_at) VALUES (?, ?, ?, ?, 0, 0, ?)""",
            ("pages-test", opts.start_url, "pending", opts.model_dump_json(), now),
        )
        cursor = conn.execute(
            """INSERT INTO pages (job_id, url, status_code, title, text_snippet,
               content_type, depth, error, elapsed_ms, crawled_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("pages-test", "https://example.com", 200, "Example", "Hello world",
             "text/html", 0, None, 150, now),
        )
        page_id = cursor.lastrowid
        assert page_id > 0

        conn.executemany(
            "INSERT INTO links (page_id, source_url, target_url) VALUES (?, ?, ?)",
            [(page_id, "https://example.com", "https://example.com/about"),
             (page_id, "https://example.com", "https://example.com/contact")],
        )
        conn.commit()

        pages = conn.execute("SELECT * FROM pages WHERE job_id = ?", ("pages-test",)).fetchall()
        assert len(pages) == 1
        assert pages[0]["url"] == "https://example.com"
        assert pages[0]["title"] == "Example"

        links = conn.execute("SELECT * FROM links WHERE page_id = ?", (page_id,)).fetchall()
        assert len(links) == 2

    def test_get_nonexistent_job(self):
        conn = _init_test_db()
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", ("nonexistent",)).fetchone()
        assert row is None

    def test_foreign_key_constraint(self):
        """Pages must reference a valid job_id."""
        conn = _init_test_db()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """INSERT INTO pages (job_id, url, status_code, title, text_snippet,
                   content_type, depth, elapsed_ms, crawled_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                ("nonexistent-job", "https://example.com", 200, "", "", "text/html", 0, 0, time.time()),
            )
