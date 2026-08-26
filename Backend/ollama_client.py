"""
Works identically for local (offline) and Ollama Cloud (online) —
the LLMConfig passed in determines which endpoint and headers to use.
"""
import json
import requests
from typing import Optional

from llm_config import LLMConfig, KNOWN_CLOUD_MODELS


class OllamaClient:
    def __init__(self, config: LLMConfig):
        self.config = config

    def is_available(self) -> bool:
        try:
            r = requests.get(
                f"{self.config.host}/api/tags",
                headers=self.config.headers,
                timeout=5,
            )
            return r.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def list_models(self) -> list[str]:
        """
        Offline: returns whatever you have locally (ollama pull ...).
        Online:  fetches from Ollama Cloud; merges with KNOWN_CLOUD_MODELS
                 as a safety net for any gaps in the API response.
        """
        try:
            r = requests.get(
                f"{self.config.host}/api/tags",
                headers=self.config.headers,
                timeout=10,
            )
            r.raise_for_status()
            remote = [m["name"] for m in r.json().get("models", [])]
        except requests.exceptions.RequestException:
            remote = []

        if self.config.mode == "online":
            return sorted(set(remote) | set(KNOWN_CLOUD_MODELS))
        return remote

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.4,
        json_mode: bool = False,
    ) -> str:
        """Single-turn generation — returns raw text string."""
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system:
            payload["system"] = system
        if json_mode:
            payload["format"] = "json"

        r = requests.post(
            f"{self.config.host}/api/generate",
            json=payload,
            headers=self.config.headers,
            timeout=300,
        )
        r.raise_for_status()
        return r.json()["response"]

    def generate_json(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.2,
        retries: int = 2,
    ) -> dict:
        """
        Generate and parse JSON, with fence-stripping and brace-matching
        recovery for models that ignore format='json'.
        NOTE: this only fixes SYNTAX errors (malformed JSON).
              Schema validation is handled separately in json_generator.py.
        """
        last_err = None
        for _ in range(retries + 1):
            raw = self.generate(
                prompt, system=system, temperature=temperature, json_mode=True
            )
            cleaned = raw.strip()

            # Strip markdown code fences some models add despite format=json
            if cleaned.startswith("```"):
                lines = cleaned.strip("`").splitlines()
                cleaned = "\n".join(
                    lines[1:] if lines[0].lower().startswith("json") else lines
                )

            try:
                return json.loads(cleaned)
            except json.JSONDecodeError as e:
                last_err = e
                # Best-effort: find the outermost {...} block
                start, end = cleaned.find("{"), cleaned.rfind("}")
                if start != -1 and end > start:
                    try:
                        return json.loads(cleaned[start : end + 1])
                    except json.JSONDecodeError as e2:
                        last_err = e2

        raise ValueError(
            f"Model did not return valid JSON after {retries + 1} attempts: {last_err}"
        )
