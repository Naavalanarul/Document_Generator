"""
CLI entrypoint for the web crawler.

Usage:
  python -m crawler.cli crawl <url> [--max-depth N] [--max-pages N] [--concurrency N] [--output FILE]

Examples:
  python -m crawler.cli crawl https://example.com
  python -m crawler.cli crawl https://example.com --max-depth 1 --max-pages 5 --output results.json
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
        description="Web crawler CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # crawl subcommand
    crawl_parser = subparsers.add_parser("crawl", help="Crawl a website")
    crawl_parser.add_argument("url", help="Start URL to crawl")
    crawl_parser.add_argument("--max-depth", type=int, default=2, help="Max crawl depth (default: 2)")
    crawl_parser.add_argument("--max-pages", type=int, default=200, help="Max pages to crawl (default: 200)")
    crawl_parser.add_argument("--concurrency", type=int, default=5, help="Concurrent requests (default: 5)")
    crawl_parser.add_argument("--no-same-host", action="store_true", help="Allow crawling external hosts")
    crawl_parser.add_argument("--no-robots", action="store_true", help="Ignore robots.txt")
    crawl_parser.add_argument("--output", "-o", type=str, default=None, help="Output JSON file (default: stdout)")

    args = parser.parse_args()

    if args.command == "crawl":
        options = CrawlOptions(
            start_url=args.url,
            max_depth=args.max_depth,
            max_pages=args.max_pages,
            concurrency=args.concurrency,
            same_host_only=not args.no_same_host,
            respect_robots=not args.no_robots,
        )

        print(f"🕷️  Crawling {args.url} (depth={options.max_depth}, max={options.max_pages})...", file=sys.stderr)

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
            f"\n📊 Crawled {result.pages_crawled} pages, "
            f"{result.pages_failed} failed, "
            f"{result.elapsed_seconds}s elapsed",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
