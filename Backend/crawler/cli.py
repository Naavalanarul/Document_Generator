"""
CLI entrypoint for the web scraper.

Usage:
  python -m crawler.cli scrape <url> [--timeout-seconds N] [--retries N] [--output FILE]

Examples:
  python -m crawler.cli scrape https://example.com
  python -m crawler.cli scrape https://example.com --retries 3 --output results.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys

from crawler.models import CrawlOptions
from crawler.crawler import crawl


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="crawler",
        description="Web scraper CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # scrape subcommand
    scrape_parser = subparsers.add_parser("scrape", help="Scrape a website")
    scrape_parser.add_argument("url", help="URL to scrape")
    scrape_parser.add_argument("--no-same-host", action="store_true", help="Allow extracted links from external hosts")
    scrape_parser.add_argument("--timeout-seconds", type=int, default=15, help="Request timeout (default: 15)")
    scrape_parser.add_argument("--retries", type=int, default=2, help="Retry attempts (default: 2)")
    scrape_parser.add_argument("--retry-delay-seconds", type=float, default=1.0, help="Retry delay (default: 1.0)")
    scrape_parser.add_argument("--no-redirects", action="store_true", help="Disable redirects")
    scrape_parser.add_argument("--output", "-o", type=str, default=None, help="Output JSON file (default: stdout)")

    args = parser.parse_args()

    if args.command == "scrape":
        options = CrawlOptions(
            start_url=args.url,
            same_host_only=not args.no_same_host,
            timeout_seconds=args.timeout_seconds,
            retries=args.retries,
            retry_delay_seconds=args.retry_delay_seconds,
            follow_redirects=not args.no_redirects,
        )

        print(
            f"🕷️  Scraping {args.url} (timeout={options.timeout_seconds}s, retries={options.retries})...",
            file=sys.stderr,
        )

        result = asyncio.run(crawl(
            options,
            on_status=lambda msg: print(f"  {msg}", file=sys.stderr),
        ))

        output = result.model_dump_json(indent=2)

        if args.output:
            with open(args.output, "w") as f:
                f.write(output)
            print(f"\n✅ Results written to {args.output}", file=sys.stderr)
        else:
            print(output)

        print(
            f"\n📊 Scraped {result.pages_crawled} pages, "
            f"{result.pages_failed} failed, "
            f"{result.elapsed_seconds}s elapsed",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
