"""Environment-backed configuration for local v0.1 runs.

Settings intentionally stay small: docs directory, Chroma store directory,
collection name, and provider name. This avoids database or deployment config
until the core workflow is proven.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    """Resolved runtime paths and provider choice for one command run."""

    docs_dir: Path
    store_dir: Path
    collection_name: str
    provider: str


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
        store_dir=Path(os.getenv("DECISION_STORE_DIR", ".decision_system/chroma")),
        collection_name=os.getenv("DECISION_COLLECTION", "decision_chunks"),
        provider=os.getenv("DECISION_PROVIDER", "fake"),
    )
