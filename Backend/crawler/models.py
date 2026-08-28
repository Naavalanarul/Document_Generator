"""
Pydantic models for the web crawler.

CrawlOptions  — configuration for a crawl run
PageResult    — data captured from a single page
CrawlResult   — aggregate result of a crawl run
CrawlJob      — persistent job record (maps to SQLite row)
"""
from __future__ import annotations

import time
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    CANCELLED = "cancelled"
    ERROR = "error"


class CrawlOptions(BaseModel):
    """Tunables for a crawl run.  All have safe defaults."""
    start_url: str
    max_depth: int = Field(default=2, ge=0, le=10)
    max_pages: int = Field(default=200, ge=1, le=10000)
    concurrency: int = Field(default=5, ge=1, le=50)
    same_host_only: bool = True
    respect_robots: bool = True
    timeout_seconds: int = Field(default=15, ge=1, le=120)
    user_agent: str = "DocGenCrawler/1.0 (+https://github.com/Naavalanarul/Document_Generator)"


class PageResult(BaseModel):
    """Data captured from a single crawled page."""
    url: str
    status_code: int = 0
    title: str = ""
    text_snippet: str = ""       # first ~500 chars of body text
    content_type: str = ""
    links_found: list[str] = Field(default_factory=list)
    depth: int = 0
    error: Optional[str] = None
    elapsed_ms: int = 0


class CrawlResult(BaseModel):
    """Aggregate output of a complete crawl run."""
    start_url: str
    pages_crawled: int = 0
    pages_failed: int = 0
    pages: list[PageResult] = Field(default_factory=list)
    elapsed_seconds: float = 0.0
    cancelled: bool = False


class CrawlJob(BaseModel):
    """Persistent job record — mirrors the SQLite `jobs` table."""
    id: str
    start_url: str
    status: JobStatus = JobStatus.PENDING
    options: CrawlOptions
    pages_crawled: int = 0
    pages_failed: int = 0
    error: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    finished_at: Optional[float] = None
