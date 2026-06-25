"""Local security mode settings.

Controls whether the system runs in ``demo`` (no login, all access) or
``governed`` (permissions enforced) mode. Settings are stored locally
under ``.decision_system/identity/security_settings.json``.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from decision_system._data_root import get_data_root
from typing import Any, Literal

from pydantic import BaseModel, Field

from decision_system.identity.models import UserRole

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

SECURITY_MODE = Literal["demo", "governed"]

def _default_security_settings_path() -> Path:
    return get_data_root() / "identity" / "security_settings.json"


class SecuritySettings(BaseModel):
    """Local security governance settings.

    These settings control how strictly permissions are enforced. In demo
    mode, the app behaves as before (no login, all access). In governed
    mode, all permission checks are active.
    """

    model_config = {"extra": "forbid"}

    security_mode: SECURITY_MODE = Field(
        default="demo",
        description="'demo' = no login, full access. 'governed' = permissions enforced.",
    )
    default_role: UserRole = Field(
        default=UserRole.OWNER,
        description="Default role assigned to new users.",
    )
    exports_require_admin: bool = Field(
        default=True,
        description="If true, only admin/owner can export reports.",
    )
    review_requires_reviewer_role: bool = Field(
        default=True,
        description="If true, only reviewer/admin/owner can resolve review gates.",
    )
    audit_retention_days: int | None = Field(
        default=None,
        description="Optional audit log retention in days. None = keep all.",
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------

_cached_settings: SecuritySettings | None = None


def _settings_path() -> Path:
    return _default_security_settings_path()


def load_settings() -> SecuritySettings:
    """Load security settings from disk, returning defaults if not found."""
    global _cached_settings
    path = _settings_path()
    if not path.exists():
        settings = SecuritySettings()
        save_settings(settings)
        _cached_settings = settings
        return settings
    try:
        with path.open("r") as f:
            data = json.load(f)
        settings = SecuritySettings.model_validate(data)
        _cached_settings = settings
        return settings
    except (json.JSONDecodeError, OSError, ValueError):
        settings = SecuritySettings()
        _cached_settings = settings
        return settings


def save_settings(settings: SecuritySettings) -> SecuritySettings:
    """Save security settings to disk."""
    global _cached_settings
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    settings.updated_at = datetime.now(timezone.utc).isoformat()
    with path.open("w") as f:
        json.dump(settings.model_dump(mode="json"), f, indent=2)
    _cached_settings = settings
    return settings


def update_settings(**kwargs: Any) -> SecuritySettings:
    """Update one or more security settings and persist."""
    settings = load_settings()
    for key, value in kwargs.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    save_settings(settings)
    return settings


def is_demo_mode() -> bool:
    """Check if the system is in demo mode."""
    return load_settings().security_mode == "demo"
