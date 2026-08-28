"""
Works identically for local (offline) and Ollama Cloud (online) —
the LLMConfig passed in determines which endpoint and headers to use.
"""
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

