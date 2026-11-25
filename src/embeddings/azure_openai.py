"""Azure OpenAI helpers. Prefer `src.generation.llm` for RAG generation."""

from __future__ import annotations

from typing import Dict, List, Optional

import requests

from src.config import config, get_secret


class AzureOpenAIClient:
    def __init__(self, cfg: Optional[dict] = None):
        self.cfg = cfg or config
        self.api_key = get_secret(self.cfg, "AZURE_OPENAI_API_KEY") or get_secret(
            self.cfg, "AZURE_OPENAI_KEY"
        )
        self.endpoint = (self.cfg.get("AZURE_OPENAI_ENDPOINT") or "").rstrip("/")
        self.model = (
            self.cfg.get("AZURE_OPENAI_DEPLOYMENT")
            or self.cfg.get("AZURE_OPENAI_MODEL")
            or ""
        )
        self.api_version = str(
            self.cfg.get("AZURE_OPENAI_API_VERSION") or "2024-02-15-preview"
        )
        self.timeout = float(self.cfg.get("HTTP_TIMEOUT_SECONDS", 30) or 30)

    def generate_embeddings(self, texts: List[str]) -> List[Dict]:
        url = (
            f"{self.endpoint}/openai/deployments/{self.model}/embeddings"
            f"?api-version={self.api_version}"
        )
        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key,
        }
        data = {"input": texts}
        response = requests.post(url, headers=headers, json=data, timeout=self.timeout)
        response.raise_for_status()
        return response.json().get("data", [])

    def generate_text(self, prompt: str, max_tokens: int = 512) -> str:
        """Chat completions — same path used by LLM_PROVIDER=azure_openai."""
        from src.generation.llm import _generate_azure_openai

        return _generate_azure_openai(prompt, max_tokens, dict(self.cfg))
