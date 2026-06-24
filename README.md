# Agentic AI Decision System

> **⚠️ PUBLIC BETA RELEASE CANDIDATE** — v1.35.0-dev
> This is a **local MVP beta** for evaluation purposes. Not production-ready.
> Best tested with [sample/demo data](./demo/sample-data/) first.
> **Do not upload sensitive production data** unless you understand the [local storage model](./docs/LOCAL_FIRST_SETUP.md) and current [security limitations](./docs/KNOWN_LIMITATIONS.md).
> See [Public Beta Release Notes](./docs/PUBLIC_BETA_RELEASE_CANDIDATE.md) for the full release overview.

A local-first, self-hosted **company intelligence automation app** that turns files, datasets, and read-only connector imports into searchable evidence, verified claims, knowledge graphs, and trust reports.

This is n8n for company intelligence — fully local, offline-capable, no API keys required.

## What It Does

| Capability | How |
|-----------|-----|
| **Ingest** documents | PDF, DOCX, XLSX, MD, TXT, CSV, JSON + OCR for scanned docs |
| **Index** into searchable evidence | Chroma vector store with keyword fallback |
| **Extract** entities, risks, metrics | Knowledge graph with 14 node types, 12 edge types |
| **Analyze** with bounded workflows | LangGraph state machine (6+ node types) |
| **Verify** claims against evidence | Deterministic verifier with contradiction detection |
| **Report** with cited evidence | Trust reports in Markdown with full citations |
| **Connect** read-only data sources | Local folder, GitHub, URL import (all read-only) |
| **Run** fully offline | Fake provider built-in, no API keys needed |

## Quickstart (60 seconds)

```bash
# Option A: Docker (recommended)
docker compose up --build
# Open http://localhost:3000

# Option B: Local scripts
cp .env.example .env
./scripts/setup-local.sh
./scripts/start-local.sh --all
# Open http://localhost:5173
```

## Demo Path (20 minutes)

1. Open the app and create a workspace
2. Upload sample files from [`demo/sample-data/`](./demo/sample-data/)
3. Parse and index — chunks appear in evidence search
4. Configure the **Fake Provider** (no API key needed)
5. Run a demo workflow (e.g., "Local Trust Report Demo")
6. View extracted claims in the Claim Ledger
7. Explore the Knowledge Graph
8. Generate and export a Trust Report

Full walkthrough: [`docs/DEMO_PATH.md`](./docs/DEMO_PATH.md)

## Screenshots

*Screenshots coming soon. See [`docs/SCREENSHOT_GUIDE.md`](./docs/SCREENSHOT_GUIDE.md) for the capture checklist.*

## What Works Today

All core features are functional and tested offline:

- Document ingestion (PDF, DOCX, XLSX, MD, TXT, CSV, JSON + OCR)
- Chroma vector search with workspace-scoped isolation
- Bounded LangGraph workflows with 6 specialized nodes
- Entity, relationship, risk, and metric extraction
- Claim ledger with verified/contradicted/unsupported/pending statuses
- Trust report generation with Markdown export
- Read-only connectors (Local Folder, GitHub, URL import)
- Connector sync with duplicate detection and pagination
- Visual workflow builder (React Flow-based SPA)
- Knowledge graph visualization
- RBAC governance mode (demo mode is default)
- Audit logging and observability metrics
- Backup and reset scripts
- 1,647 passing tests (offline, no API keys)

## Known Limitations

- **Not production-ready** — no enterprise auth, no encryption at rest
- **Single-user default** — governed mode adds RBAC but no multi-user sessions
- **OCR requires Tesseract** — text-based documents still work
- **Sequential workflows** — no parallel branching yet
- **Read-only connectors only** — data is never modified externally
- **English only** — only English Tesseract language data bundled
- Full list: [`docs/KNOWN_LIMITATIONS.md`](./docs/KNOWN_LIMITATIONS.md)

## How to Give Feedback

- **Bug report**: Use the [Bug Report template](.github/ISSUE_TEMPLATE/bug_report.yml)
- **Feature request**: Use the [Feature Request template](.github/ISSUE_TEMPLATE/feature_request.yml)
- **Beta feedback**: Use the [Beta Feedback template](.github/ISSUE_TEMPLATE/beta_feedback.yml)
- **Collect diagnostics first**: `./scripts/collect-diagnostics.sh` (safe — no secrets collected)
- See the [Beta Reviewer Guide](./docs/BETA_REVIEWER_GUIDE.md) for detailed testing guidance

## Project Status

| Milestone | Status |
|-----------|--------|
| v1.34 — Beta Feedback Loop | ✅ Complete |
| **v1.35 — Public Beta Release Candidate** | **🔵 Current** |
| v1.36 — Public Beta Feedback Triage | 📅 Planned |

See [CHANGELOG](./CHANGELOG.md) for full version history.

## Documentation

| Resource | Link |
|----------|------|
| Setup Guide | [`docs/LOCAL_FIRST_SETUP.md`](./docs/LOCAL_FIRST_SETUP.md) |
| Demo Walkthrough | [`docs/DEMO_PATH.md`](./docs/DEMO_PATH.md) |
| Beta Release Notes | [`docs/PUBLIC_BETA_RELEASE_CANDIDATE.md`](./docs/PUBLIC_BETA_RELEASE_CANDIDATE.md) |
| Reviewer Guide | [`docs/BETA_REVIEWER_GUIDE.md`](./docs/BETA_REVIEWER_GUIDE.md) |
| Known Limitations | [`docs/KNOWN_LIMITATIONS.md`](./docs/KNOWN_LIMITATIONS.md) |
| Architecture | [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) |
| Product Vision | [`docs/PRODUCT_VISION.md`](./docs/PRODUCT_VISION.md) |
| API Reference | (FastAPI auto-docs at `http://localhost:8000/docs`) |

## Commands

```bash
decision-system index              # Index documents
decision-system ask "question"     # Run analysis workflow
decision-system serve-api          # Start API server
decision-system check-hygiene      # Verify repo hygiene
decision-system extract-graph      # Extract knowledge graph
decision-system build-context      # Build decision context
decision-system run-war-room       # Run war-cabinet analysis
```

See the full CLI reference: `decision-system --help`


---

## Repository Hygiene

```bash
decision-system check-hygiene
decision-system check-hygiene --json
```

## License

MIT License. See `LICENSE`.

## Version History

| Version | Focus |
|---------|-------|
| **v1.35** | Public Beta Release Candidate + Demo Video Script |
| v1.34 | Local Beta Feedback Loop + Issue Templates |
| v1.33 | End-to-End Beta QA + Bug Bash |
| v1.32 | Beta Packaging, Installer Scripts + Local Release Polish |
| v1.31 | Connector Reliability, Rate Limits + Large Import Handling |
| v1.30 | Connector Expansion + OAuth/Token Setup UX |
| v1.29 | Connector Scheduling + Incremental Sync |
| v1.28 | Connector Read-Only Imports + External Knowledge Sync |
| v1.27 | Security, Auth, RBAC + Governance Foundation |
| v1.26 | Knowledge Graph + Entity/Risk Extraction v2 |
| v1.25 | End-to-End Demo Hardening + Local Beta Release Prep |
| v1.24 | Single App Integration + Data Sources in React Workflow Builder |
| v1.23 | Document Parsing Expansion + PDF/DOCX/XLSX Support |

Earlier versions (v0.1–v1.22): See [CHANGELOG](./CHANGELOG.md).

---

*Made with ❤️ for local-first, evidence-backed company intelligence.*
