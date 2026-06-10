"""Demo data validator — verifies demo docs/mock data contain no real secrets.

Scans demo documents (``company_docs/demo_*``) and mock JSON fixtures
(``web/mock-data/*``, ``src/decision_system/web/mock-data/*``) for
patterns that look like real credentials, private keys, production
secrets, or large raw datasets.

This is a deterministic offline check — no network calls, no LLM.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ValidationFinding:
    """One finding from a demo data validation pass."""

    file_path: str
    line_number: int
    pattern: str
    detail: str
    severity: str  # "error" or "warning"


@dataclass
class DemoDataValidationResult:
    """Aggregated result of a demo data validation pass."""

    files_scanned: int = 0
    findings: list[ValidationFinding] = field(default_factory=list)
    passed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "files_scanned": self.files_scanned,
            "findings": [
                {
                    "file_path": f.file_path,
                    "line_number": f.line_number,
                    "pattern": f.pattern,
                    "detail": f.detail,
                    "severity": f.severity,
                }
                for f in self.findings
            ],
            "passed": self.passed,
            "finding_count": len(self.findings),
        }


# Patterns that indicate real secrets (never expected in demo data)
_SECRET_PATTERNS: list[tuple[str, str, str]] = [
    # API keys / tokens
    ("api_key", r"(?i)(sk-[A-Za-z0-9]{20,}|nvapi-[A-Za-z0-9\-_]{20,})", "API key pattern detected"),
    # AWS keys
    ("aws_key", r"(?i)(AKIA|ASIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA)[0-9A-Z]{16}", "AWS access key pattern detected"),
    # Private keys (inline)
    ("private_key", r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----", "Private key block detected"),
    # Real-looking email addresses with suspicious domains
    ("suspicious_email", r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", "Email address found (check it's a demo email)"),
    # Connection strings containing passwords
    ("conn_string", r"(?i)(password|pwd|secret)\s*[:=]\s*\S{8,}", "Hardcoded credential-like value"),
    # Very large files (>100KB in demo data)
    ("large_file", r"N/A", "File is unusually large for demo data"),
]

# Known-good demo email domains
_DEMO_EMAIL_DOMAINS = {
    "example.com",
    "demo.com",
    "test.com",
    "local.dev",
    "acme.com",
    "company.com",
    "yourcompany.com",
}

# File size limit for demo files (100 KB)
_MAX_DEMO_FILE_SIZE = 100 * 1024


def validate_demo_data(
    project_root: str | Path = ".",
) -> DemoDataValidationResult:
    """Scan demo documents and mock data for real secrets.

    Returns a ``DemoDataValidationResult`` with findings (if any) and a
    ``passed`` boolean.
    """
    root = Path(project_root).resolve()
    result = DemoDataValidationResult()

    # Files to scan
    scan_globs: list[str] = [
        "company_docs/demo_*",
        "company_docs/demo_*/**",
        "web/mock-data/*.json",
        "src/decision_system/web/mock-data/*.json",
    ]

    scanned_files: set[Path] = set()

    for pattern in scan_globs:
        for p in root.glob(pattern):
            if p.is_file() and p not in scanned_files:
                scanned_files.add(p)

    result.files_scanned = len(scanned_files)

    for file_path in sorted(scanned_files):
        # Check file size
        size = file_path.stat().st_size
        if size > _MAX_DEMO_FILE_SIZE:
            result.findings.append(
                ValidationFinding(
                    file_path=str(file_path.relative_to(root)),
                    line_number=0,
                    pattern="large_file",
                    detail=f"File is {size} bytes (max allowed: {_MAX_DEMO_FILE_SIZE})",
                    severity="warning",
                )
            )
            result.passed = False

        try:
            lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue

        for line_num, line in enumerate(lines, start=1):
            for pattern_name, regex, detail in _SECRET_PATTERNS:
                if pattern_name == "large_file":
                    continue  # already checked above
                if pattern_name == "suspicious_email":
                    # Check emails - flag non-demo domains
                    for match in re.finditer(regex, line):
                        email = match.group(0)
                        domain = email.split("@")[-1] if "@" in email else ""
                        if domain.lower() not in _DEMO_EMAIL_DOMAINS:
                            result.findings.append(
                                ValidationFinding(
                                    file_path=str(file_path.relative_to(root)),
                                    line_number=line_num,
                                    pattern=pattern_name,
                                    detail=f"Non-demo email: {email}",
                                    severity="warning",
                                )
                            )
                    continue
                if re.search(regex, line):
                    result.findings.append(
                        ValidationFinding(
                            file_path=str(file_path.relative_to(root)),
                            line_number=line_num,
                            pattern=pattern_name,
                            detail=detail,
                            severity="error",
                        )
                    )

    result.passed = len([f for f in result.findings if f.severity == "error"]) == 0
    return result


def validation_to_text(result: DemoDataValidationResult) -> str:
    """Render validation result as human-readable text."""
    lines = [
        "# Demo Data Validation",
        "",
        f"Files scanned: {result.files_scanned}",
        f"Findings: {len(result.findings)}",
        f"Passed: {'YES' if result.passed else 'NO'}",
        "",
    ]

    if result.findings:
        errors = [f for f in result.findings if f.severity == "error"]
        warnings = [f for f in result.findings if f.severity == "warning"]

        if errors:
            lines.extend(["## Errors", ""])
            for f in errors:
                lines.append(f"- {f.file_path}:{f.line_number} [{f.pattern}] {f.detail}")
            lines.append("")

        if warnings:
            lines.extend(["## Warnings", ""])
            for f in warnings:
                lines.append(f"- {f.file_path}:{f.line_number} [{f.pattern}] {f.detail}")
            lines.append("")

    if result.passed:
        lines.append("No secrets found in demo data. ✓")

    return "\n".join(lines)
