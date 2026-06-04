from functools import lru_cache
from pathlib import Path
from pydantic import BaseModel, Field
import os


class Settings(BaseModel):
    app_name: str = "AI Mailbox Manager"
    database_url: str = Field(default_factory=lambda: f"sqlite:///{Path(os.getenv('LOCALAPPDATA', Path.home())) / 'AI Mailbox Manager' / 'mailbox.db'}")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3")
    enable_openai: bool = os.getenv("ENABLE_OPENAI", "false").lower() == "true"
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    graph_client_id: str | None = os.getenv("GRAPH_CLIENT_ID")
    graph_tenant: str = os.getenv("GRAPH_TENANT", "common")
    cors_origins: list[str] = ["https://localhost:3000", "http://localhost:3000", "https://localhost:5173", "http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.database_url.startswith("sqlite:///"):
        Path(settings.database_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    return settings
