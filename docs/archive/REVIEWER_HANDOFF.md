# Reviewer Handoff — v1.35.0-dev

> **Version:** 1.35.0-dev
> **Milestone:** Public Beta Release Candidate + Demo Video Script
> **Date:** 2026-06-24

## What to Install

- **Docker** (recommended) — install Docker and Docker Compose
- OR **Python 3.11+** and **Node.js 18+** for local scripts
- **Tesseract** (optional) — for OCR of scanned documents

## How to Run

```bash
# Docker (recommended)
git clone <repo-url>
cd Agentic-Ai-Decision-System
cp .env.example .env
docker compose up --build
# Open http://localhost:3000

# Local scripts (alternative)
cp .env.example .env
./scripts/setup-local.sh
./scripts/start-local.sh --all
# Open http://localhost:5173
```

## What to Test First

1. **Doctor check:** `./scripts/doctor-local.sh`
2. **Validation:** `./scripts/validate-local.sh`
3. **Demo walkthrough:** Follow [`docs/DEMO_PATH.md`](./docs/DEMO_PATH.md)
4. **Quick test (10 min):** Upload demo files, run a demo workflow, view the report
5. **Extended test (30 min):** Test connectors, sync, graph extraction, claim ledger

## What Not to Upload

- **Do not upload real sensitive company data** — use sample files from `demo/sample-data/`
- If you must test with real data, ensure it is non-confidential and anonymized

## How to Collect Diagnostics

```bash
./scripts/collect-diagnostics.sh
# Output: diagnostics/<timestamp>/diagnostics.txt
```

**Safe by default** — does NOT collect API keys, tokens, `.env` contents, or uploaded documents.

## How to Report Bugs

1. Collect diagnostics first
2. Open a [Bug Report](.github/ISSUE_TEMPLATE/bug_report.yml)
3. Include: app version, OS, steps to reproduce, expected vs actual behavior, diagnostics

## How to Submit Beta Feedback

Use the [Beta Feedback template](.github/ISSUE_TEMPLATE/beta_feedback.yml).

## Known Limitations

See [KNOWN_LIMITATIONS.md](./docs/KNOWN_LIMITATIONS.md).

Key points:
- Not production-ready
- No enterprise auth or encryption at rest
- OCR requires Tesseract
- Read-only connectors only
- Sequential workflows only

## Expected Time Commitment

| Activity | Time |
|----------|------|
| Install + smoke test | 10 minutes |
| Full demo walkthrough | 20 minutes |
| Extended testing | 30–60 minutes |
| Bug report submission | 5–10 minutes |

## Questions?

Open a GitHub Discussion or use the issue templates.
