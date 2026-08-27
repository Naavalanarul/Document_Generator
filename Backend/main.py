"""
Endpoints:
  GET  /health          check Ollama is reachable
  GET  /models          list available models for the chosen mode
  POST /upload          save an uploaded file, return its server-side path
  POST /generate        run the full pipeline, return a download URL
  GET  /download/{file} serve the generated file
"""
import uuid
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from llm_config import LLMConfig
from ollama_client import OllamaClient
from ingestion import extract_text, extract_text_from_url
from planner import plan_document, plan_presentation
from web_search import search_and_fetch
from generators.docx_gen import generate_docx
from generators.pptx_gen import generate_pptx
from generators.pdf_gen import generate_pdf

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Local Doc Generator")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


def _make_client(mode: str, model: str, api_key: str = "") -> OllamaClient:
    config = LLMConfig(
        mode=mode,
        model=model,
        api_key=api_key or None,
    )
    return OllamaClient(config)


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
        dest = UPLOAD_DIR / f"{uuid.uuid4().hex}_{f.filename}"
        dest.write_bytes(await f.read())
        paths.append(str(dest))
    return {"file_paths": paths}


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
            + ("Start it with `ollama serve`." if mode == "offline" else "Check your API key.")
        )

    # 1. Extract source text
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
    elif source_type == "web_search":
        if not search_query:
            raise HTTPException(400, "search_query is required")
        source_text = search_and_fetch(search_query)
    else:
        raise HTTPException(400, "source_type must be file, url, or web_search")

    if not source_text.strip():
        raise HTTPException(422, "No text could be extracted from the source")

    # 2. Plan + 3. Render
    out_id = uuid.uuid4().hex
    if output_format == "pptx":
        plan = plan_presentation(client, source_text, instructions)
        out_path = OUTPUT_DIR / f"{out_id}.pptx"
        generate_pptx(plan, str(out_path))
    else:
        plan = plan_document(client, source_text, instructions)
        out_path = OUTPUT_DIR / f"{out_id}.{output_format}"
        if output_format == "docx":
            generate_docx(plan, str(out_path))
        else:
            generate_pdf(plan, str(out_path))

    return {
        "file_path": str(out_path),
        "download_url": f"/download/{out_path.name}",
    }


@app.get("/download/{filename}")
def download(filename: str):
    path = OUTPUT_DIR / filename
    if not path.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(path, filename=filename)
