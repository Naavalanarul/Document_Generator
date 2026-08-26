"""
or PresentationPlan via the local/cloud Ollama model.

For sources longer than one context window, _condense_if_long() summarises
each chunk first, then the planner synthesises from the summaries.
"""
from ollama_client import OllamaClient
from ingestion import chunk_text
from json_generator import generate_json
from schemas import DocumentPlan, PresentationPlan

DOC_SYSTEM_PROMPT = """You are a document structuring assistant.
Given source material, produce a JSON object matching this EXACT shape:
{
  "title": "string",
  "subtitle": "string",
  "sections": [
    {
      "heading": "string",
      "paragraphs": ["string"],
      "bullets": [
        {"text": "string", "sub_bullets": ["string"]}
      ]
    }
  ]
}
Rules:
- Use paragraphs for narrative content, bullets for scannable lists.
- Keep headings concise (under 6 words).
- Do NOT invent facts not present in the source material.
- Respond with ONLY the JSON object, nothing else."""

SLIDE_SYSTEM_PROMPT = """You are a presentation structuring assistant.
Given source material, produce a JSON object matching this EXACT shape:
{
  "title": "string",
  "subtitle": "string",
  "slides": [
    {
      "title": "string",
      "bullets": ["string"],
      "speaker_notes": "string"
    }
  ]
}
Rules:
- 3-7 bullets per slide, each under 12 words.
- Spread content across slides rather than cramming.
- speaker_notes can be longer — they're for the presenter, not the screen.
- Do NOT invent facts not present in the source material.
- Respond with ONLY the JSON object, nothing else."""


def _condense_if_long(client: OllamaClient, text: str, max_chars: int = 6000) -> str:
    """
    If source text is too long for one prompt, summarise each chunk
    individually, then join the summaries as the working source text.
    This keeps the planner prompt within the model's context window.
    """
    chunks = chunk_text(text, max_chars=max_chars)
    if len(chunks) == 1:
        return text

    print(f"  [Planner] Source too long — summarising {len(chunks)} chunks...")
    summaries = []
    for i, chunk in enumerate(chunks, 1):
        summary = client.generate(
            f"Summarise the key facts from this excerpt "
            f"(part {i}/{len(chunks)}) in 200 words or fewer. "
            f"Preserve specific numbers, names, and dates.\n\n---\n{chunk}\n---",
            temperature=0.2,
        )
        summaries.append(summary)
    return "\n\n".join(summaries)


def plan_document(
    client: OllamaClient, source_text: str, instructions: str = ""
) -> DocumentPlan:
    working = _condense_if_long(client, source_text)
    prompt = f"Source material:\n---\n{working}\n---\n"
    if instructions:
        prompt += f"\nAdditional instructions: {instructions}\n"
    prompt += "\nProduce the JSON document plan now."

    return generate_json(
        prompt,
        DocumentPlan,
        model=client.config.model,
        system=DOC_SYSTEM_PROMPT,
        host=client.config.host,
        headers=client.config.headers,
    )


def plan_presentation(
    client: OllamaClient, source_text: str, instructions: str = ""
) -> PresentationPlan:
    working = _condense_if_long(client, source_text)
    prompt = f"Source material:\n---\n{working}\n---\n"
    if instructions:
        prompt += f"\nAdditional instructions: {instructions}\n"
    prompt += "\nProduce the JSON slide plan now."

    return generate_json(
        prompt,
        PresentationPlan,
        model=client.config.model,
        system=SLIDE_SYSTEM_PROMPT,
        host=client.config.host,
        headers=client.config.headers,
    )
