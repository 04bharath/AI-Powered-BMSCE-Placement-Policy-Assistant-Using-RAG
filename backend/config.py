"""Central, environment-driven configuration for CampusCompass."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _csv(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


@dataclass(frozen=True)
class Settings:
    # Models (configurable without touching application logic)
    # "ollama" (local) | "groq" | "xai" | "openai_compatible" (cloud APIs; needs LLM_API_KEY)
    llm_provider: str = os.getenv("LLM_PROVIDER", "ollama").strip().lower()
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    llm_model: str = os.getenv("LLM_MODEL", "llama3.2:3b")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    # Optional override; required for "openai_compatible". Groq/xAI have built-in defaults.
    llm_base_url: str = os.getenv("LLM_BASE_URL", "")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    llm_timeout_seconds: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "120"))
    embedding_model: str = os.getenv(
        "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
    )

    # Optional web search for general/current-information questions. Policy questions
    # remain restricted to the indexed policy PDFs.
    web_search_enabled: bool = os.getenv("ENABLE_WEB_SEARCH", "false").lower() == "true"
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
    web_search_max_results: int = int(os.getenv("WEB_SEARCH_MAX_RESULTS", "4"))
    web_search_timeout_seconds: float = float(os.getenv("WEB_SEARCH_TIMEOUT_SECONDS", "15"))

    # Storage
    chroma_dir: Path = Path(os.getenv("CHROMA_PERSIST_DIR", str(BASE_DIR / ".chroma")))
    upload_dir: Path = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads")))
    registry_path: Path = Path(
        os.getenv("REGISTRY_PATH", str(BASE_DIR / ".chroma" / "registry.json"))
    )
    collection_name: str = os.getenv("CHROMA_COLLECTION", "placement_policy")

    # CORS / limits
    allowed_origins: list[str] = field(
        default_factory=lambda: _csv(
            os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
        )
    )
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "25"))

    # Retrieval / chunking (initial values to evaluate, not universally optimal)
    # Retrieval / chunking
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "500"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "75"))

    top_k: int = int(os.getenv("RETRIEVAL_TOP_K", "3"))
    fetch_k: int = int(os.getenv("RETRIEVAL_FETCH_K", "6"))

    # Maximum accepted cosine distance
    max_distance: float = float(
        os.getenv("RETRIEVAL_MAX_DISTANCE", "0.75")
    )

    enable_rerank: bool = (
        os.getenv("ENABLE_RERANK", "false").lower() == "true"
    )

    rerank_model: str = os.getenv(
        "RERANK_MODEL",
        "cross-encoder/ms-marco-MiniLM-L-6-v2"
    )

    # Admin auth: a bearer token supplied by the operator. No default -> admin disabled.
    admin_token: str = os.getenv("ADMIN_API_TOKEN", "")

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


def get_settings() -> Settings:
    return Settings()
