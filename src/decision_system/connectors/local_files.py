"""Real local-files connector: dry-run scan and safe copy-based import."""
from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from decision_system.connectors.models import (
    ConnectorDefinition,
    ConnectorDryRunFile,
    ConnectorDryRunResult,
    ConnectorImportJob,
    ConnectorImportResult,
    ConnectorType,
)
from decision_system.connectors.store import save_job

_SUPPORTED_EXTENSIONS: set[str] = {".md", ".txt", ".csv", ".json"}

_SKIP_DIR_NAMES: set[str] = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
}

_PROTECTED_FILENAMES: set[str] = {
    ".env",
    ".gitignore",
    ".env.example",
}

_KEY_FILE_PATTERNS: tuple[str, ...] = (
    ".key",
    ".pem",
    ".p12",
    ".pfx",
    ".private",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
)


def _should_skip_directory(name: str) -> bool:
    return name in _SKIP_DIR_NAMES


def _should_skip_file(path: Path) -> tuple[bool, str]:
    """Return (skip, reason) for a file that must not be imported."""
    name = path.name
    if name in _PROTECTED_FILENAMES:
        return True, f"Protected file: {name}"
    if name.endswith(".env"):
        return True, "Environment file (.env)"
    for suffix in _KEY_FILE_PATTERNS:
        if name.endswith(suffix):
            return True, f"Private key-like file: {name}"
    if path.parts and path.parts[0] == "datasets":
        return True, "Raw dataset inside ignored datasets/ folder"
    return False, ""


def _target_category(extension: str) -> str:
    if extension in {".md", ".txt"}:
        return "documents"
    if extension == ".csv":
        return "datasets"
    if extension == ".json":
        return "json"
    return "other"


def _walk(source_path: Path):
    """Yield (root, dirs, files) from os.walk, sorting for determinism."""
    import os

    for root, dirs, files in os.walk(source_path):
        dirs.sort()
        files.sort()
        yield root, dirs, files


def _collect_files(
    source_path: Path,
) -> tuple[list[tuple[Path, str]], list[tuple[Path, str]]]:
    """Walk source_path and return (included, skipped) file lists.

    Symlinks are rejected to prevent importing files from outside the source
    root.  The resolved path of every candidate file is verified to stay
    under *source_path* before it is included.
    """
    included: list[tuple[Path, str]] = []
    skipped: list[tuple[Path, str]] = []

    if not source_path.exists():
        return included, skipped

    source_root = source_path.resolve()

    for root, dirs, files in _walk(source_path):
        dirs[:] = [d for d in dirs if not _should_skip_directory(d)]
        for name in files:
            file_path = Path(root) / name
            skip, reason = _should_skip_file(file_path)
            if skip:
                skipped.append((file_path, reason))
                continue

            # Reject symlinks — they can point outside the import root.
            if file_path.is_symlink():
                skipped.append((file_path, "Symlinked files are not importable"))
                continue

            # Reject files whose resolved path escapes the source root.
            resolved = file_path.resolve()
            try:
                resolved.relative_to(source_root)
            except ValueError:
                skipped.append(
                    (file_path, "Resolved path escapes source root")
                )
                continue

            extension = file_path.suffix.lower()
            if extension not in _SUPPORTED_EXTENSIONS:
                skipped.append((file_path, f"Unsupported extension: {extension}"))
                continue
            included.append((file_path, _target_category(extension)))
    return included, skipped


def _normalize_target(
    dest_root: Path,
    source_file: Path,
    source_root: Path,
    category: str,
) -> Path:
    """Compute the destination path for an import copy."""
    try:
        rel = source_file.relative_to(source_root)
    except ValueError:
        rel = Path(source_file.name)

    if category in {"documents", "datasets"}:
        return dest_root / category / "imported" / rel.name
    if category == "json":
        return dest_root / "imported_json" / rel
    return dest_root / category / "imported" / source_file.name


def run_dry_run(
    connector_id: str,
    source_path: str | Path,
) -> ConnectorDryRunResult:
    """Scan a local directory and report what would be imported."""
    resolved = Path(source_path)
    if not resolved.is_absolute():
        resolved = Path.cwd() / resolved

    warnings: list[str] = []

    if not resolved.exists():
        return ConnectorDryRunResult(
            connector_id=connector_id,
            source_path=str(resolved),
            files=[],
            skipped_files=[],
            warnings=["Source path does not exist."],
            would_import_count=0,
        )

    if not resolved.is_dir():
        return ConnectorDryRunResult(
            connector_id=connector_id,
            source_path=str(resolved),
            files=[],
            skipped_files=[],
            warnings=["Source path is not a directory."],
            would_import_count=0,
        )

    included, skipped = _collect_files(resolved)

    files = [
        ConnectorDryRunFile(
            source_path=str(fp),
            relative_path=str(
                fp.relative_to(resolved) if fp != resolved else fp.name
            ),
            filename=fp.name,
            extension=fp.suffix.lower(),
            size_bytes=fp.stat().st_size,
            target_category=_target_category(fp.suffix.lower()),
            action="import",
            reason="",
        )
        for fp, _ in included
    ]

    skipped_files = [
        ConnectorDryRunFile(
            source_path=str(fp),
            filename=fp.name,
            extension=fp.suffix.lower(),
            size_bytes=fp.stat().st_size,
            target_category=_target_category(fp.suffix.lower()),
            action="skip",
            reason=reason,
        )
        for fp, reason in skipped
    ]

    if not files and not skipped_files:
        warnings.append("No files found (empty directory).")

    return ConnectorDryRunResult(
        connector_id=connector_id,
        source_path=str(resolved),
        files=files,
        skipped_files=skipped_files,
        warnings=warnings,
        would_import_count=len(files),
        created_at=datetime.now(timezone.utc),
    )


def run_local_files_import(
    connector_id: str,
    source_path: str | Path,
) -> ConnectorImportResult:
    """Import safe local files into generated connector output directories."""
    source_root = Path(source_path)
    if not source_root.is_absolute():
        source_root = Path.cwd() / source_root

    job_id = _make_job_id()
    dest_root = Path(".decision_system") / "connectors"
    status = "completed"
    warnings: list[str] = []
    imported_files: list[str] = []
    skipped_files: list[str] = []
    output_paths: list[str] = []

    dry = run_dry_run(connector_id, source_root)

    for file_info in dry.files + dry.skipped_files:
        source_file = Path(file_info.source_path)
        if not source_file.exists():
            skipped_files.append(file_info.source_path)
            continue

        if file_info.action == "skip":
            skipped_files.append(file_info.source_path)
            continue

        category = file_info.target_category
        target = _normalize_target(dest_root, source_file, source_root, category)
        target.parent.mkdir(parents=True, exist_ok=True)

        # Verify target stays under the connector output root.
        target_resolved = target.resolve()
        try:
            target_resolved.relative_to(dest_root.resolve())
        except ValueError:
            warnings.append(
                f"Target path {target} escapes connector root — skipped"
            )
            skipped_files.append(file_info.source_path)
            continue

        _copy_safe(source_file, target, warnings)
        imported_files.append(file_info.source_path)
        output_paths.append(str(target))


    job = ConnectorImportJob(
        job_id=job_id,
        connector_id=connector_id,
        status=status,
        source_path=str(source_root),
        imported_files=imported_files,
        skipped_files=skipped_files,
        warnings=list(dry.warnings) + warnings,
        output_paths=output_paths,
        created_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    save_job(job)

    return ConnectorImportResult(
        job=job,
        dry_run=False,
        imported_count=len(imported_files),
        skipped_count=len(skipped_files),
    )


def _copy_safe(src: Path, dst: Path, warnings: list[str]) -> None:
    """Copy a file, never overwriting an existing file silently."""
    if dst.exists():
        stem = dst.stem
        suffix = dst.suffix
        parent = dst.parent
        counter = 1
        while dst.exists():
            dst = parent / f"{stem}-{counter}{suffix}"
            counter += 1
        warnings.append(f"Existing file skipped; wrote to {dst.name}")
    shutil.copy2(src, dst)


def _make_job_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
