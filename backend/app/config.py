"""Runtime configuration, read once from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    # LLM: "auto" picks Anthropic, then OpenAI, then Ollama, then offline.
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "auto").strip().lower())
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", "").strip())
    anthropic_model: str = field(default_factory=lambda: os.getenv("ANTHROPIC_MODEL", "claude-opus-5-5").strip())
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", "").strip())
    openai_model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-5-mini").strip())
    openai_base_url: str = field(default_factory=lambda: os.getenv("OPENAI_BASE_URL", "").strip())
    openai_embedding_model: str = field(
        default_factory=lambda: os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small").strip()
    )
    ollama_base_url: str = field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "").strip())
    ollama_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "qwen2.5:7b").strip())
    use_embeddings: bool = field(default_factory=lambda: _bool("USE_EMBEDDINGS", True))

    data_dir: Path = field(default_factory=lambda: Path(os.getenv("DATA_DIR", str(BASE_DIR / "var"))))
    demo_dir: Path = field(default_factory=lambda: Path(os.getenv("DEMO_DIR", str(BASE_DIR / "data" / "demo"))))
    snapshot_dir: Path = field(
        default_factory=lambda: Path(os.getenv("SNAPSHOT_DIR", str(BASE_DIR / "data" / "snapshot")))
    )
    static_dir: Path = field(default_factory=lambda: Path(os.getenv("STATIC_DIR", str(BASE_DIR / "static"))))
    auto_seed: bool = field(default_factory=lambda: _bool("AUTO_SEED", True))
    llm_timeout: float = field(default_factory=lambda: float(os.getenv("LLM_TIMEOUT", "120")))
    max_parallel_llm: int = field(default_factory=lambda: int(os.getenv("MAX_PARALLEL_LLM", "4")))

    @property
    def db_path(self) -> Path:
        return self.data_dir / "mirror_org.db"


settings = Settings()
