"""
Web crawler package.

Public API:
  from crawler import crawl, CrawlOptions, CrawlResult
  from crawler.models import PageResult, CrawlJob, JobStatus
  from crawler.db import init_db, create_job, get_job, list_jobs
  from crawler.routes import router as crawler_router
"""
from crawler.crawler import crawl
from crawler.models import CrawlOptions, CrawlResult

__all__ = ["crawl", "CrawlOptions", "CrawlResult"]
