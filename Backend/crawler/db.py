"""
SQLite persistence layer for the web crawler.

Uses aiosqlite for async access.  The DB file location is configurable
via the DB_PATH environment variable (default: crawler_data/crawler.db
relative to Backend/).
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Optional

import aiosqlite

from crawler.models import CrawlJob, CrawlOptions, JobStatus, PageResult

_MIGRATIONS_DIR = Path(__file__).parent / "migrations"
_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "crawler_data" / "crawler.db"
DB_PATH = os.environ.get("DB_PATH", str(_DEFAULT_DB_PATH))


async def _get_db() -> aiosqlite.Connection:
    """Open a connection (caller must close / use as context manager)."""
    db_path = Path(DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(str(db_path))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db() -> None:
    """Run the migration SQL to ensure tables exist."""
    schema_sql = (_MIGRATIONS_DIR / "initial.sql").read_text()
    async with await _get_db() as db:
        await db.executescript(schema_sql)
        await db.commit()


# ── Job CRUD ───────────────────────────────────────────────────────────────────

async def create_job(job_id: str, options: CrawlOptions) -> CrawlJob:
    job = CrawlJob(
        id=job_id,
        start_url=options.start_url,
        status=JobStatus.PENDING,
        options=options,
        created_at=time.time(),
    )
    async with await _get_db() as db:
        await db.execute(
            """INSERT INTO jobs (id, start_url, status, options, pages_crawled,
               pages_failed, error, created_at, finished_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                job.id,
                job.start_url,
                job.status.value,
                job.options.model_dump_json(),
                job.pages_crawled,
                job.pages_failed,
                job.error,
                job.created_at,
                job.finished_at,
            ),
        )
        await db.commit()
    return job


async def update_job_status(
    job_id: str,
    status: JobStatus,
    pages_crawled: int = 0,
    pages_failed: int = 0,
    error: Optional[str] = None,
) -> None:
    finished_at = time.time() if status in (JobStatus.DONE, JobStatus.ERROR, JobStatus.CANCELLED) else None
    async with await _get_db() as db:
        await db.execute(
            """UPDATE jobs
               SET status = ?, pages_crawled = ?, pages_failed = ?,
                   error = ?, finished_at = ?
               WHERE id = ?""",
            (status.value, pages_crawled, pages_failed, error, finished_at, job_id),
        )
        await db.commit()


async def get_job(job_id: str) -> Optional[CrawlJob]:
    async with await _get_db() as db:
        cursor = await db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        return _row_to_job(row)


async def list_jobs(limit: int = 50, status_filter: Optional[str] = None) -> list[CrawlJob]:
    async with await _get_db() as db:
        if status_filter:
            cursor = await db.execute(
                "SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status_filter, limit),
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
        rows = await cursor.fetchall()
        return [_row_to_job(r) for r in rows]


async def cancel_job(job_id: str) -> bool:
    """Mark a pending/running job as cancelled.  Returns True if updated."""
    async with await _get_db() as db:
        cursor = await db.execute(
            """UPDATE jobs SET status = 'cancelled', finished_at = ?
               WHERE id = ? AND status IN ('pending', 'running')""",
            (time.time(), job_id),
        )
        await db.commit()
        return cursor.rowcount > 0


# ── Page persistence ───────────────────────────────────────────────────────────

async def insert_page(job_id: str, page: PageResult) -> int:
    """Insert a crawled page and its outbound links.  Returns the page row id."""
    async with await _get_db() as db:
        cursor = await db.execute(
            """INSERT INTO pages (job_id, url, status_code, title, text_snippet,
               content_type, depth, error, elapsed_ms, crawled_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                job_id,
                page.url,
                page.status_code,
                page.title,
                page.text_snippet,
                page.content_type,
                page.depth,
                page.error,
                page.elapsed_ms,
                time.time(),
            ),
        )
        page_id = cursor.lastrowid

        if page.links_found:
            await db.executemany(
                "INSERT INTO links (page_id, source_url, target_url) VALUES (?, ?, ?)",
                [(page_id, page.url, link) for link in page.links_found],
            )
        await db.commit()
        return page_id


async def get_job_pages(job_id: str, limit: int = 500) -> list[dict]:
    """Return crawled pages for a job as dicts."""
    async with await _get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM pages WHERE job_id = ? ORDER BY id LIMIT ?",
            (job_id, limit),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _row_to_job(row) -> CrawlJob:
    return CrawlJob(
        id=row["id"],
        start_url=row["start_url"],
        status=JobStatus(row["status"]),
        options=CrawlOptions.model_validate_json(row["options"]),
        pages_crawled=row["pages_crawled"],
        pages_failed=row["pages_failed"],
        error=row["error"],
        created_at=row["created_at"],
        finished_at=row["finished_at"],
    )
