# Scraper module (`Backend/crawler`)

This module now uses a **Scrapling-based scraping flow** instead of the previous breadth-first crawler.

## What changed

- Removed the old `aiohttp` + `BeautifulSoup` crawling engine (queue/depth/concurrency traversal).
- Added `scrapling` as the HTTP/parsing engine for page fetch + extraction.
- Kept the existing `/api/crawl` job endpoints and persistence model, but each job now performs robust single-page scraping.
- Added retry/timeout controls:
  - `timeout_seconds`
  - `retries`
  - `retry_delay_seconds`
  - `follow_redirects`

## Behavior

- SSRF protections are still enforced (private/loopback targets are blocked).
- Requests use Scrapling's static `AsyncFetcher` with retries and redirect safety.
- HTML extraction now returns:
  - page title
  - normalized links
  - cleaned text snippet

## Migration notes

- API route paths are unchanged (`/api/crawl`), but request options changed from crawl-depth/concurrency style to scrape retry/timeout style.
- CLI command is now:
  - `python -m crawler.cli scrape <url> ...`
