"""
Endpoints:
  GET  /health          check Ollama is reachable
  GET  /models          list available models for the chosen mode
  POST /upload          save an uploaded file, return its server-side path
  POST /generate        run the full pipeline (async by default, ?sync=true for old behaviour)
  GET  /jobs/{job_id}   poll async job status
  GET  /download/{file} serve the generated file
"""
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from fastapi import (
    FastAPI, UploadFile, File, Form, HTTPException, Request, Query,
)
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.background import BackgroundTasks

from llm_config import LLMConfig
from ollama_client import OllamaClient
from ingestion import extract_text, extract_text_from_url, SUPPORTED_EXTENSIONS
from planner import plan_document, plan_presentation
from web_search import search_and_fetch
from generators.docx_gen import generate_docx
from generators.pptx_gen import generate_pptx
from generators.pdf_gen import generate_pdf
from crawler.routes import router as crawler_router
from crawler.db import init_db as init_crawler_db

log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Configuration via environment ──────────────────────────────────────────────
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_MB", "25")) * 1024 * 1024
API_KEY = os.environ.get("API_KEY", "")  # empty ⇒ auth disabled
DEV_MODE = os.environ.get("DEV_MODE", "1") == "1"
ALLOWED_ORIGINS = os.environ.get(
    "ALLOWED_ORIGINS",
    "*" if DEV_MODE else "",
).split(",")
FILE_EXPIRY_HOURS = int(os.environ.get("FILE_EXPIRY_HOURS", "24"))


# ── In-memory job store (Section 7) ───────────────────────────────────────────

@dataclass
class JobInfo:
    status: str = "pending"  # pending → running → done | error
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)


_jobs: dict[str, JobInfo] = {}


# ── Lifespan: cleanup old files on startup (Section 8) ─────────────────────────

def _cleanup_old_files(directory: Path, max_age_hours: int) -> int:
    """Delete files older than *max_age_hours* from *directory*."""
    cutoff = time.time() - max_age_hours * 3600
    removed = 0
    if not directory.exists():
        return removed
    for f in directory.iterdir():
        if f.is_file() and f.stat().st_mtime < cutoff:
            f.unlink(missing_ok=True)
            removed += 1
    return removed


@asynccontextmanager
async def lifespan(app: FastAPI):
    n_up = _cleanup_old_files(UPLOAD_DIR, FILE_EXPIRY_HOURS)
    n_out = _cleanup_old_files(OUTPUT_DIR, FILE_EXPIRY_HOURS)
    if n_up or n_out:
        log.info(
            "Startup cleanup: removed %d upload(s), %d output(s) older than %dh",
            n_up, n_out, FILE_EXPIRY_HOURS,
        )
    # Initialize scraper database
    await init_crawler_db()
    log.info("Scraper database initialized")
    yield


app = FastAPI(title="Local Doc Generator", lifespan=lifespan)

# CORS ──────────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Scraper router
app.include_router(crawler_router)


# ── Optional API-key middleware (Section 3) ────────────────────────────────────

@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    if not API_KEY:
        return await call_next(request)
    # Always allow docs / openapi / health without auth
    if request.url.path in ("/docs", "/openapi.json", "/redoc", "/health"):
        return await call_next(request)
    provided = request.headers.get("X-API-Key", "")
    if provided != API_KEY:
        return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key"})
    return await call_next(request)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _sanitize_filename(name: str) -> str:
    """Strip directory components and reject path-traversal attempts."""
    clean = Path(name).name  # strip all dir components
    if not clean or ".." in clean or "/" in clean or "\\" in clean:
        raise HTTPException(400, f"Invalid filename: {name!r}")
    return clean


def _make_client(mode: str, model: str, api_key: str = "") -> OllamaClient:
    config = LLMConfig(
        mode=mode,
        model=model,
        api_key=api_key or None,
    )
    return OllamaClient(config)


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/health")
def health(mode: str = "offline", model: str = "llama3.1", api_key: str = ""):
    try:
        client = _make_client(mode, model, api_key)
    except ValueError as e:
        return {"available": False, "error": str(e)}
    return {"available": client.is_available(), "mode": mode, "model": model}


@app.get("/models")
def models(mode: str = "offline", api_key: str = ""):
    try:
        # Use a placeholder model name just to build the config
        config = LLMConfig(mode=mode, model="placeholder", api_key=api_key or None)
        client = OllamaClient(config)
        return {"models": client.list_models(), "mode": mode}
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    paths = []
    for f in files:
        safe_name = _sanitize_filename(f.filename or "file")

        # Validate extension against ingestion whitelist
        ext = Path(safe_name).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                400,
                f"Unsupported file extension {ext!r}. "
                f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
            )

        # Read content and enforce size limit
        content = await f.read()
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                413,
                f"File {safe_name!r} exceeds the {MAX_UPLOAD_BYTES // (1024*1024)}MB upload limit.",
            )

        dest = UPLOAD_DIR / f"{uuid.uuid4().hex}_{safe_name}"
        dest.write_bytes(content)
        paths.append(str(dest))

    return {"file_paths": paths}


def _run_pipeline(
    output_format: str,
    source_type: str,
    client: OllamaClient,
    source_text: str,
    source_urls: list[str],
    instructions: str,
) -> dict:
    """Core pipeline: plan → render.  Returns the result dict."""
    out_id = uuid.uuid4().hex
    if output_format == "pptx":
        plan = plan_presentation(client, source_text, instructions, sources=source_urls)
        out_path = OUTPUT_DIR / f"{out_id}.pptx"
        generate_pptx(plan, str(out_path))
    else:
        plan = plan_document(client, source_text, instructions, sources=source_urls)
        out_path = OUTPUT_DIR / f"{out_id}.{output_format}"
        if output_format == "docx":
            generate_docx(plan, str(out_path))
        else:
            generate_pdf(plan, str(out_path))

    return {
        "file_path": str(out_path),
        "download_url": f"/download/{out_path.name}",
    }


def _run_job(job_id: str, **kwargs):
    """Background wrapper that updates the in-memory job store."""
    job = _jobs[job_id]
    job.status = "running"
    try:
        result = _run_pipeline(**kwargs)
        job.result = result
        job.status = "done"
    except Exception as exc:
        log.exception("Job %s failed", job_id)
        job.error = str(exc)
        job.status = "error"


@app.post("/generate")
async def generate(
    output_format: str = Form(...),    # "docx" | "pptx" | "pdf"
    source_type: str  = Form(...),     # "file" | "url" | "web_search"
    mode: str         = Form("offline"),  # "offline" | "online"
    model: str        = Form("llama3.1"),
    api_key: str      = Form(""),
    instructions: str = Form(""),
    file_paths: str   = Form(None),
    url: str          = Form(None),
    search_query: str = Form(None),
    sync: bool        = Query(False),
):
    if output_format not in {"docx", "pptx", "pdf"}:
        raise HTTPException(400, "output_format must be docx, pptx, or pdf")

    try:
        client = _make_client(mode, model, api_key)
    except ValueError as e:
        raise HTTPException(400, str(e))

    if not client.is_available():
        raise HTTPException(
            503,
            f"Ollama ({mode}) is not reachable. "
            + ("Start it with `ollama serve`." if mode == "offline" else "Check your API key."),
        )

    # Model pre-check (Section 4): fail fast if model doesn't exist
    available_models = client.list_models()
    # Strip tags for comparison (e.g. "llama3.1:latest" matches "llama3.1")
    model_names = {m.split(":")[0] for m in available_models} | set(available_models)
    if model not in model_names:
        raise HTTPException(
            400,
            f"Model {model!r} is not available. "
            f"Available models: {', '.join(sorted(available_models))}",
        )

    # 1. Extract source text
    source_urls: list[str] = []
    if source_type == "file":
        if not file_paths:
            raise HTTPException(400, "file_paths missing")
        source_text = ""
        for fp in file_paths.split(","):
            if Path(fp).exists():
                source_text += extract_text(fp) + "\n\n"
    elif source_type == "url":
        if not url:
            raise HTTPException(400, "url is required")
        source_text = extract_text_from_url(url)
        source_urls = [url]
    elif source_type == "web_search":
        if not search_query:
            raise HTTPException(400, "search_query is required")
        source_text, source_urls = search_and_fetch(search_query)
    else:
        raise HTTPException(400, "source_type must be file, url, or web_search")

    if not source_text.strip():
        raise HTTPException(422, "No text could be extracted from the source")

    pipeline_kwargs = dict(
        output_format=output_format,
        source_type=source_type,
        client=client,
        source_text=source_text,
        source_urls=source_urls,
        instructions=instructions,
    )

    # Synchronous mode (backward compat)
    if sync:
        result = _run_pipeline(**pipeline_kwargs)
        return result

    # Async mode (default) — enqueue and return job_id
    job_id = uuid.uuid4().hex
    _jobs[job_id] = JobInfo()
    bg = BackgroundTasks()
    bg.add_task(_run_job, job_id, **pipeline_kwargs)

    # Attach background tasks — FastAPI runs them after response is sent
    return JSONResponse(
        content={"job_id": job_id, "status_url": f"/jobs/{job_id}"},
        status_code=202,
        background=bg,
    )


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    payload: dict = {"job_id": job_id, "status": job.status}
    if job.status == "done":
        payload["result"] = job.result
    elif job.status == "error":
        payload["error"] = job.error
    return payload


@app.get("/download/{filename}")
def download(filename: str):
    safe_name = _sanitize_filename(filename)
    path = OUTPUT_DIR / safe_name
    # Extra guard: ensure resolved path is under OUTPUT_DIR
    if not path.resolve().is_relative_to(OUTPUT_DIR.resolve()):
        raise HTTPException(400, "Invalid filename")
    if not path.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(path, filename=safe_name)
