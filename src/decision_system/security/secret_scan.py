"""Deterministic local secret scanner.

Scans tracked repo text files for obvious credential patterns without
calling external services.  Binary and ignored directories are skipped
by default.  Full secret values are never returned; only masked previews
are included in results.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Literal

from decision_system.security.models import SecretFinding, SecretScanResult

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_SCAN_ROOT = Path(".")
DEFAULT_SCAN_DIRS: tuple[str, ...] = (
    ".git",
    ".venv",
    "venv",
    ".decision_system",
    ".pytest_cache",
    "__pycache__",
)
DEFAULT_IGNORE_DIRS: frozenset[str] = frozenset(
    DEFAULT_SCAN_DIRS + ("node_modules", "dist", "build", "egg-info")
)
# Users should configure raw public-dataset directories through the data
# catalog.  The scan explicitly skips the top-level "datasets/" folder
# when the caller passes it; see _SKIP_DATASETS_DIR below.
_SKIP_DATASETS_DIR = "datasets"

# Extensions we consider *text-like*.  Everything else is treated as binary.
_TEXT_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".py",
        ".js",
        ".ts",
        ".sh",
        ".md",
        ".txt",
        ".rst",
        ".yaml",
        ".yml",
        ".toml",
        ".cfg",
        ".ini",
        ".json",
        ".env",
        ".env.example",
        ".env.local",
        ".env.*.local",
        ".html",
        ".css",
        ".csv",
        ".sql",
    }
)


# ---------------------------------------------------------------------------
# Pattern catalog
# ---------------------------------------------------------------------------
# Order matters: more specific patterns first.
_PATTERNS: list[tuple[str, str, str]] = [
    (
        "private_key",
        (
            r"(?i)-----BEGIN\s+(?:RSA\s+)?PRIVATE KEY-----"
            r".{0,120}?"
            r"(?:[A-Za-z0-9+/=]+\n)*"
            r"-----END\s+(?:RSA\s+)?PRIVATE\s+KEY-----"
        ),
        "low",
    ),
    (
        "aws_key",
        (
            r"(?:AKIA|ASIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA)[0-9A-Z]{16}"
        ),
        "high",
    ),
    (
        "token",
        (
            r"(?i)(token|access_token|bearer)\s*[=:]\s*"
            r"['\"]?([A-Za-z0-9_\-]{20,})['\"]?"
        ),
        "high",
    ),
    (
        "api_key",
        (
            r"(?i)(api[_\-\s]?key|apikey)\s*[=:]\s*"
            r"['\"]?([A-Za-z0-9_\-]{16,})['\"]?"
        ),
        "high",
    ),
    (
        "env_file",
        (
            r"(?i)^\s*(?:OPENAI_API_KEY|ANTHROPIC_API_KEY|NVIDIA_API_KEY|"
            r"GITHUB_TOKEN|JIRA_TOKEN|SLACK_TOKEN|DATABASE_URL|SECRET_KEY|"
            r"PRIVATE_KEY|SERVICE_ACCOUNT)\s*=\s*.+$"
        ),
        "critical",
    ),
    (
        "generic_secret",
        (
            r"(?i)^\s*(?:PASSWORD|PASS|SECRET|CREDENTIAL)\s*=\s*.+$"
        ),
        "medium",
    ),
    (
        "sk_prefix",
        r"(?i)\bsk-[A-Za-z0-9]{20,}\b",
        "high",
    ),
    (
        "nvapi_prefix",
        r"(?i)\bnvapi-[A-Za-z0-9\-_]{20,}\b",
        "high",
    ),
]
# Map internal pattern names to the SecretType model literal.
_TYPE_MAP: dict[str, str] = {
    "private_key": "private_key",
    "aws_key": "aws_key",
    "token": "token",
    "api_key": "api_key",
    "env_file": "env_file",
    "generic_secret": "other",
    "sk_prefix": "api_key",
    "nvapi_prefix": "api_key",
}

_COMPILED: list[tuple[str, re.Pattern[str], str]] = [
    (name, re.compile(pat, re.MULTILINE | re.DOTALL), sev)
    for name, pat, sev in _PATTERNS
]


# ---------------------------------------------------------------------------
# Scanning logic
# ---------------------------------------------------------------------------

def _extension(path: Path) -> str:
    """Return the file extension, handling dotfiles like ``.env`` correctly."""
    name = path.name
    last_dot = name.rfind(".")
    if last_dot < 0:
        return ""
    # If the only dot is the leading one (.env), return ".env" not ""
    return name[last_dot:].lower()


def _is_ignored(path: Path, root: Path) -> bool:
    """Return True when *path* should be skipped (binary file or ignored dir)."""
    rel_str = str(path.relative_to(root))

    # Skip binary files by extension.
    if _extension(path) not in _TEXT_EXTENSIONS:
        return True

    # Skip files inside ignored directories.
    for part in path.parts:
        if part in _IGNORE_DIRS:
            return True

    # Skip raw public dataset folder when explicitly passed.
    if _SKIP_DATASETS_DIR in path.parts:
        return True

    return False


_IGNORE_DIRS: frozenset[str] = DEFAULT_IGNORE_DIRS


def _mask_text(text: str) -> str:
    """Return a safe display string: first+last 4 chars, rest ***."""
    if len(text) <= 8:
        return "*" * len(text)
    return f"{text[:4]}{'*' * (len(text) - 8)}{text[-4:]}"


def scan_repo(
    root: str | Path = DEFAULT_SCAN_ROOT,
    *,
    extra_ignore_dirs: Iterable[str] | None = None,
) -> SecretScanResult:
    """Scan *root* for secrets and return aggregated results."""
    root_path = Path(root).resolve()
    ignored: frozenset[str] = _IGNORE_DIRS | frozenset(
        extra_ignore_dirs or []
    )

    findings: list[SecretFinding] = []
    files_scanned = 0
    files_skipped = 0

    try:
        iterable = sorted(root_path.rglob("*"))
    except (OSError, PermissionError):
        iterable = []

    for file_path in iterable:
        if not file_path.is_file():
            continue
        rel = file_path.relative_to(root_path)
        rel_str = str(rel)

        # Skip ignored directories.
        skip = False
        for part in file_path.parts:
            if part in ignored:
                skip = True
                break
        if skip:
            files_skipped += 1
            continue

        # Skip binary files by extension.
        if _extension(file_path) not in _TEXT_EXTENSIONS:
            files_skipped += 1
            continue

        files_scanned += 1
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except (OSError, PermissionError):
            files_skipped += 1
            continue

        lines = content.splitlines()
        for line_idx, line in enumerate(lines, start=1):
            # Skip comment / empty lines for some patterns.
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            for pattern_name, compiled, default_sev in _COMPILED:
                for match in compiled.finditer(line):
                    raw = match.group(0)
                    preview = _mask_text(raw)
                    findings.append(
                        SecretFinding(
                            finding_id=f"{pattern_name}-{rel_str}-{line_idx}-{match.start()}",
                            source_path=rel_str,
                            line_number=line_idx,
                            secret_type=_TYPE_MAP.get(pattern_name, "other"),
                            severity=default_sev,
                            matched_preview=preview,
                            recommendation=_default_recommendation(pattern_name),
                        )
                    )

    # Determine overall status.
    critical = sum(1 for f in findings if f.severity == "critical")
    high = sum(1 for f in findings if f.severity == "high")
    if critical or high:
        status: Literal["ok", "warn", "fail"] = "warn"
    elif findings:
        status = "warn"
    else:
        status = "ok"

    return SecretScanResult(
        scanned_path=str(root_path),
        files_scanned=files_scanned,
        files_skipped=files_skipped,
        findings=findings,
        overall_status=status,
    )


def _default_recommendation(secret_type: str) -> str:
    recommendations = {
        "api_key": "Rotate the API key now and remove it from all tracked files.",
        "token": "Rotate the token and remove it from version-controlled files.",
        "password": "Remove the hard-coded password and use a secrets manager.",
        "private_key": "Remove the private key immediately and rotate the key pair.",
        "aws_key": "Remove the AWS access key, revoke it in IAM, and update services.",
        "env_file": "Move this credential to an untracked .env file and add it to .gitignore.",
        "other": "Move this credential to a secrets manager or untracked .env.",
    }
    return recommendations.get(secret_type, "Remove this credential from version control.")
