"""System status endpoint for the local API.

Provides a comprehensive status view for diagnostics without leaking secrets.
"""

from __future__ import annotations

import os
from pathlib import Path
from decision_system._data_root import get_data_root

from fastapi import APIRouter

from decision_system import __version__
from decision_system.config import load_settings

router = APIRouter(tags=["system"])


def _import_available(module_name: str) -> bool:
    """Check if an optional Python module is importable."""
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False


def _count_workspaces(settings) -> int:
    """Count workspace directories in the data dir."""
    from pathlib import Path
    from decision_system._data_root import get_data_root
    data_dir = Path(settings.workspace_db_path).parent if hasattr(settings, 'workspace_db_path') else get_data_root()
    ws_dir = data_dir / "workspaces"
    if ws_dir.is_dir():
        count = sum(1 for p in ws_dir.iterdir() if p.is_dir() and not p.name.startswith("."))
        return count
    return 0


@router.get("/system/status")
def system_status() -> dict:
    """Return a comprehensive system status for diagnostics.

    This endpoint never leaks secrets or tokens.
    Security mode, provider type, and data dir are reported safely.
    """
    settings = load_settings()
    data_dir = os.environ.get(
        "DECISION_SYSTEM_DATA_DIR",
        str(settings.store_dir.parent if hasattr(settings, 'store_dir') else ".decision_system"),
    )

    # Count providers from the providers store
    provider_count = 0
    try:
        from decision_system.providers.store import ProviderStore
        store = ProviderStore()
        provider_count = len(store.list_providers())
    except Exception:
        pass

    # Count connectors from registry
    connector_count = 0
    try:
        from decision_system.connectors.registry import list_connectors
        connector_count = len(list_connectors())
    except Exception:
        pass

    # Check demo data availability
    demo_data_available = (
        Path("demo/sample-data").is_dir()
        or Path("company_data/manifest.json").exists()
    )

    # Check workspace count
    try:
        workspace_count = _count_workspaces(settings)
    except Exception:
        workspace_count = 0

    # Check OCR availability
    ocr_available = _import_available("tesserocr")
    doc_parsing_available = _import_available("pypdf") or _import_available("docx")

    security_mode = os.environ.get("DECISION_SYSTEM_SECURITY_MODE", "demo")

    # Build warnings list
    warnings = []
    if security_mode == "demo":
        warnings.append("Running in demo security mode — no real access control enforced.")
    if not ocr_available:
        warnings.append("OCR not available — scanned PDFs and images will not be parsed.")
    if not doc_parsing_available:
        warnings.append("Document parsing dependencies not installed — PDF/DOCX/XLSX may not be readable.")

    return {
        "version": __version__,
        "data_dir": data_dir,
        "security_mode": security_mode,
        "provider_type": settings.provider if hasattr(settings, 'provider') else "unknown",
        "provider_count": provider_count,
        "connector_count": connector_count,
        "workspace_count": workspace_count,
        "demo_data_available": demo_data_available,
        "ocr_available": ocr_available,
        "doc_parsing_available": doc_parsing_available,
        "warnings": warnings,
    }
