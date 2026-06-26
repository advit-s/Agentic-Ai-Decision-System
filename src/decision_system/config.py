"""Environment-backed configuration for local decision-system runs.

Settings intentionally stay local and environment-driven. Hosted provider
credentials must come from `.env` or process environment variables, never code.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from decision_system._data_root import get_data_root


@dataclass(frozen=True)
class Settings:
    """Resolved runtime paths and provider choice for one command run."""

    docs_dir: Path
    store_dir: Path
    collection_name: str
    provider: str
    # NVIDIA NIM
    nvidia_api_key: str
    nvidia_nim_model: str
    nvidia_temperature: float
    nvidia_top_p: float
    nvidia_max_tokens: int
    nvidia_reasoning_enabled: bool
    nvidia_reasoning_effort: str
    nvidia_nim_base_url: str
    # Ollama
    ollama_base_url: str
    ollama_model: str
    ollama_temperature: float
    ollama_max_tokens: int
    ollama_timeout_seconds: int
    # Workspace path (set at call time via env or computed lazily)
    workspace_db_path: str = ""


def load_settings() -> Settings:
    """Load settings from `.env` and process environment variables.

    Returns:
        Immutable `Settings` with safe local defaults.

    Side effects:
        Calls `load_dotenv()` so local `.env` values can override defaults.
    """

    load_dotenv()

    return Settings(
        docs_dir=Path(os.getenv("DECISION_DOCS_DIR", "company_docs")),
        store_dir=Path(os.getenv("DECISION_STORE_DIR", str(get_data_root() / "chroma"))),
        collection_name=os.getenv("DECISION_COLLECTION", "decision_chunks"),
        provider=os.getenv("DECISION_PROVIDER", "fake"),
        nvidia_api_key=os.getenv("NVIDIA_API_KEY", ""),
        nvidia_nim_model=os.getenv("NVIDIA_NIM_MODEL", ""),
        nvidia_temperature=float(os.getenv("NVIDIA_TEMPERATURE", "0")),
        nvidia_top_p=float(os.getenv("NVIDIA_TOP_P", "0.95")),
        nvidia_max_tokens=int(os.getenv("NVIDIA_MAX_TOKENS", "4096")),
        nvidia_nim_base_url=os.getenv("NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1"),
        nvidia_reasoning_enabled=_env_bool("NVIDIA_REASONING_ENABLED", default=False),
        nvidia_reasoning_effort=os.getenv("NVIDIA_REASONING_EFFORT", "medium"),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", ""),
        ollama_temperature=float(os.getenv("OLLAMA_TEMPERATURE", "0")),
        ollama_max_tokens=int(os.getenv("OLLAMA_MAX_TOKENS", "2048")),
        ollama_timeout_seconds=int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "60")),
        workspace_db_path=os.getenv(
            "DECISION_WORKSPACE_DB",
            str(get_data_root() / "workspaces" / "workspaces.sqlite"),
        ),
    )


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
