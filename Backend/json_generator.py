"""
Layer 1 (syntax)  — json.loads() catches malformed JSON
Layer 2 (schema)  — Pydantic model_validate() catches wrong shapes/missing fields

On failure, the exact error is fed back to the model to self-correct.
Each retry re-states the ORIGINAL prompt + only the latest error,
keeping prompt size constant across retries (never grows unboundedly).
"""
import json
import logging
import re
from typing import Optional

import requests
from pydantic import BaseModel, ValidationError

log = logging.getLogger(__name__)

OLLAMA_HOST = "http://localhost:11434"


def sanitize_json_response(raw: str) -> str:
    """
    Best-effort recovery for LLM outputs that wrap JSON in markdown
    fences or include preamble/trailing text.

    Strategy (in order):
      1. Strip ```json ... ``` fences.
      2. If the result still isn't parseable, extract the outermost {...} block.
    """
    cleaned = raw.strip()

    # Strip markdown code fences some models add despite format=json
    if cleaned.startswith("```"):
        # Remove opening fence line and closing fence
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned, count=1)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned, count=1)
        cleaned = cleaned.strip()

    # If it already looks like valid JSON, return as-is
    try:
        json.loads(cleaned)
        return cleaned
    except json.JSONDecodeError:
        pass

    # Best-effort: find the outermost {...} block
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end > start:
        candidate = cleaned[start : end + 1]
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass

    # Return what we have — let the caller's json.loads() produce
    # the actual error for the retry loop
    return cleaned


def call_llm(
    prompt: str,
    model: str = "llama3.1",
    system: Optional[str] = None,
    host: str = OLLAMA_HOST,
    headers: Optional[dict] = None,
) -> str:
    """
    Single call to the Ollama API.
    format='json' is a token-level grammar constraint — it guarantees
    syntactically valid JSON, but NOT that the JSON matches your schema.
    That's what the Pydantic layer below handles.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "format": "json",
        "stream": False,
    }
    if system:
        payload["system"] = system

    response = requests.post(
        f"{host}/api/generate",
        json=payload,
        headers=headers or {},
        timeout=300,
    )
    response.raise_for_status()
    return response.json()["response"]


def generate_json(
    prompt: str,
    pydantic_model: type[BaseModel],
    model: str = "llama3.1",
    system: Optional[str] = None,
    host: str = OLLAMA_HOST,
    headers: Optional[dict] = None,
    max_retries: int = 3,
) -> BaseModel:
    """
    Generate JSON from the LLM and validate against a Pydantic schema.
    Automatically asks the model to self-correct on both types of failure:
      - JSON syntax errors  (json.JSONDecodeError)
      - Schema shape errors (pydantic.ValidationError)
    """
    current_prompt = prompt

    for attempt in range(max_retries):
        log.info("  [LLM] Attempt %d/%d...", attempt + 1, max_retries)
        raw = call_llm(current_prompt, model=model, system=system, host=host, headers=headers)

        # Fence-stripping + brace-matching recovery before parsing
        sanitized = sanitize_json_response(raw)

        try:
            # Layer 1: JSON syntax
            parsed = json.loads(sanitized)

            # Layer 2: schema shape
            validated = pydantic_model.model_validate(parsed)

            log.info("  [LLM] Success on attempt %d", attempt + 1)
            return validated

        except json.JSONDecodeError as e:
            log.warning("  [LLM] JSON syntax error: %s", e)
            current_prompt = (
                f"{prompt}\n\n"
                f"Your last response was not valid JSON. Error:\n{e}\n\n"
                f"Respond with ONLY the raw JSON object — "
                f"no markdown fences, no commentary, no truncation."
            )

        except ValidationError as e:
            log.warning("  [LLM] Schema validation error:\n%s", e)
            current_prompt = (
                f"{prompt}\n\n"
                f"Your last response was valid JSON but did not match the required schema.\n"
                f"Validation errors:\n{e}\n\n"
                f"Return corrected JSON that fixes every field listed above. "
                f"Keep everything else the same."
            )

    raise RuntimeError(
        f"Max retries ({max_retries}) exceeded: "
        f"LLM failed to produce a valid {pydantic_model.__name__}."
    )
