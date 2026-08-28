"""
FastAPI router for the web crawler.

Endpoints:
  POST /api/crawl            — start a new crawl job
  GET  /api/crawl/jobs       — list all crawl jobs
  GET  /api/crawl/jobs/{id}  — get job details + crawled pages
  POST /api/crawl/jobs/{id}/cancel — cancel a running job

Protected by the same X-API-Key middleware as the rest of the app
(when API_KEY env var is set).
"""
from __future__ import annotations

import asyncio
import logging
import uuid

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from crawler.models import CrawlOptions, JobStatus
from crawler import db
from crawler.crawler import crawl

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/crawl", tags=["crawler"])


# ── Request / response models ─────────────────────────────────────────────────

class StartCrawlRequest(BaseModel):
    url: str
    max_depth: int = 2
    max_pages: int = 200
    concurrency: int = 5
    same_host_only: bool = True
    respect_robots: bool = True


class StartCrawlResponse(BaseModel):
    job_id: str
    status_url: str


# ── Background task runner ─────────────────────────────────────────────────────

# Track cancel events so we can stop crawls in-flight
_cancel_events: dict[str, asyncio.Event] = {}


async def _run_crawl_job(job_id: str, options: CrawlOptions) -> None:
    """Background task that runs the crawl and updates the DB."""
    cancel_event = asyncio.Event()
    _cancel_events[job_id] = cancel_event

    try:
        await db.update_job_status(job_id, JobStatus.RUNNING)

        async def on_page(page):
            await db.insert_page(job_id, page)

        result = await crawl(
            options,
            on_page=lambda p: asyncio.ensure_future(db.insert_page(job_id, p)),
            on_status=lambda msg: log.info("[Crawl %s] %s", job_id[:8], msg),
            cancel_event=cancel_event,
        )

        if result.cancelled:
            await db.update_job_status(
                job_id, JobStatus.CANCELLED,
                pages_crawled=result.pages_crawled,
                pages_failed=result.pages_failed,
            )
        else:
            await db.update_job_status(
                job_id, JobStatus.DONE,
                pages_crawled=result.pages_crawled,
                pages_failed=result.pages_failed,
            )

    except Exception as exc:
        log.exception("Crawl job %s failed", job_id)
        await db.update_job_status(job_id, JobStatus.ERROR, error=str(exc))
    finally:
        _cancel_events.pop(job_id, None)


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("", response_model=StartCrawlResponse)
async def start_crawl(req: StartCrawlRequest, background_tasks: BackgroundTasks):
    """Start a new crawl job.  Returns immediately with a job_id."""
    job_id = uuid.uuid4().hex

    options = CrawlOptions(
        start_url=req.url,
        max_depth=req.max_depth,
        max_pages=req.max_pages,
        concurrency=req.concurrency,
        same_host_only=req.same_host_only,
        respect_robots=req.respect_robots,
    )

    await db.create_job(job_id, options)
    background_tasks.add_task(_run_crawl_job, job_id, options)

    return StartCrawlResponse(
        job_id=job_id,
        status_url=f"/api/crawl/jobs/{job_id}",
    )


@router.get("/jobs")
async def list_jobs(limit: int = 50, status: str = None):
    """List crawl jobs, optionally filtered by status."""
    jobs = await db.list_jobs(limit=limit, status_filter=status)
    return {"jobs": [j.model_dump() for j in jobs]}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, include_pages: bool = True):
    """Get job details and optionally its crawled pages."""
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(404, f"Crawl job {job_id!r} not found")

    result = job.model_dump()
    if include_pages:
        result["pages"] = await db.get_job_pages(job_id)
    return result


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a pending or running crawl job."""
    # Signal the crawl loop to stop
    cancel_event = _cancel_events.get(job_id)
    if cancel_event:
        cancel_event.set()

    updated = await db.cancel_job(job_id)
    if not updated:
        job = await db.get_job(job_id)
        if not job:
            raise HTTPException(404, f"Crawl job {job_id!r} not found")
        raise HTTPException(400, f"Job is already {job.status.value}, cannot cancel")

    return {"job_id": job_id, "status": "cancelled"}
