"""
Selects between:
  - "offline": local Ollama server (localhost:11434), no auth
  - "online":  Ollama Cloud (https://ollama.com), needs OLLAMA_API_KEY

Both use the identical /api/generate + /api/tags HTTP shape —
only host and auth headers differ, so nothing else in the codebase
needs to change when you switch modes.
"""
import os
from dataclasses import dataclass
from typing import Optional

KNOWN_CLOUD_MODELS = [
    "gpt-oss:20b-cloud",
    "gpt-oss:120b-cloud",
    "deepseek-v3.1:671b-cloud",
    "qwen3-coder:480b-cloud",
    "glm-4.6:cloud",
    "kimi-k2:1t-cloud",
]


@dataclass
class LLMConfig:
    mode: str             # "offline" | "online"
    model: str            # e.g. "llama3.1" or "gpt-oss:120b-cloud"
    api_key: Optional[str] = None

    def __post_init__(self):
        if self.mode not in ("offline", "online"):
            raise ValueError(f"mode must be 'offline' or 'online', got {self.mode!r}")
        if self.mode == "online" and not self.api_key:
            self.api_key = os.environ.get("OLLAMA_API_KEY")
            if not self.api_key:
                raise ValueError(
                    "mode='online' requires an api_key or OLLAMA_API_KEY env var.\n"
                    "Get one at: https://ollama.com -> Settings -> API Keys"
                )

    @property
    def host(self) -> str:
        return "https://ollama.com" if self.mode == "online" else "http://localhost:11434"

    @property
    def headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"} if self.mode == "online" else {}
