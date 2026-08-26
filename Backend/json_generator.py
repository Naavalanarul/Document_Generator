"""
Layer 1 (syntax)  — json.loads() catches malformed JSON
Layer 2 (schema)  — Pydantic model_validate() catches wrong shapes/missing fields

On failure, the exact error is fed back to the model to self-correct.
Each retry re-states the ORIGINAL prompt + only the latest error,
keeping prompt size constant across retries (never grows unboundedly).
"""
import json
from typing import Optional

import requests
from pydantic import BaseModel, ValidationError

OLLAMA_HOST = "http://localhost:11434"


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
        print(f"  [LLM] Attempt {attempt + 1}/{max_retries}...")
        raw = call_llm(current_prompt, model=model, system=system, host=host, headers=headers)

        try:
            # Layer 1: JSON syntax
            parsed = json.loads(raw)

            # Layer 2: schema shape
            validated = pydantic_model.model_validate(parsed)

            print(f"  [LLM] Success on attempt {attempt + 1}")
            return validated

        except json.JSONDecodeError as e:
            print(f"  [LLM] JSON syntax error: {e}")
            current_prompt = (
                f"{prompt}\n\n"
                f"Your last response was not valid JSON. Error:\n{e}\n\n"
                f"Respond with ONLY the raw JSON object — "
                f"no markdown fences, no commentary, no truncation."
            )

        except ValidationError as e:
            print(f"  [LLM] Schema validation error:\n{e}")
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
