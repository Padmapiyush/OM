import json
import httpx
from app.core.config import get_settings


class OllamaClient:
    def __init__(self, base_url: str | None = None, model: str | None = None):
        settings = get_settings()
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model

    async def generate_json(self, prompt: str, fallback: dict) -> dict:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(f"{self.base_url}/api/generate", json={"model": self.model, "prompt": prompt, "format": "json", "stream": False})
                response.raise_for_status()
                text = response.json().get("response", "{}")
                return json.loads(text)
        except Exception:
            return fallback

    async def generate_text(self, prompt: str, fallback: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(f"{self.base_url}/api/generate", json={"model": self.model, "prompt": prompt, "stream": False})
                response.raise_for_status()
                return response.json().get("response", fallback).strip()
        except Exception:
            return fallback
