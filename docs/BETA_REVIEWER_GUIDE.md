# Beta Reviewer Guide — v1.34.0-dev

> **Version:** 1.34.0-dev
> **Milestone:** Local Beta Feedback Loop + Issue Templates
> **Date:** 2026-06-24

## Who This Beta Is For

- Developers evaluating local-first intelligence tools
- Teams exploring company document analysis workflows
- Contributors interested in LangGraph, Chroma, or agent-based systems
- Anyone who wants to test an offline-capable document intelligence platform

## What This App Does

The Agentic Decision System is a local-first Company Intelligence Engine. It:
- Ingests documents (PDF, DOCX, XLSX, MD, TXT, CSV, JSON)
- Indexes them in a local vector store (Chroma)
- Runs bounded LangGraph workflows to analyze content
- Extracts entities, relationships, risks, and metrics
- Generates evidence-backed trust reports with verified claims

## What to Test

| Area | Focus |
|------|-------|
| Setup | Install on your machine with Docker or local scripts |
| Data upload | Upload sample documents, verify parsing |
| Demo path | Follow the 18-step demo walkthrough |
| Workflows | Run demo workflows with fake provider |
| Graph extraction | Extract entities and relationships |
| Claims | Verify claim ledger behavior |
| Reports | Generate and export trust reports |
| Connectors | Test local folder and GitHub import |
| Error handling | Try edge cases — empty files, large uploads, cancel mid-operation |

## Quickstart

```bash
# Option A: Docker (recommended)
docker compose up --build
# Open http://localhost:3000

# Option B: Local scripts
./scripts/setup-local.sh
./scripts/start-local.sh --all
# Open http://localhost:5173
```

## Recommended Test Sessions

### 10-Minute Smoke Test
1. Run `./scripts/doctor-local.sh` then `./scripts/validate-local.sh`
2. Start the app (`./scripts/start-local.sh --all`)
3. Open the frontend and create a workspace
4. Upload a sample `.md` file from `demo/sample-data/`
5. Run a demo workflow with the fake provider
6. View the generated report

### 30-Minute Test
1. Complete the 10-minute smoke test
2. Upload multiple file types (PDF, DOCX, CSV)
3. Test evidence search
4. Run graph extraction
5. Verify claims in the claim ledger
6. Export a report as Markdown
7. Check the audit log
8. Run `./scripts/backup-local-data.sh` and verify the backup

## What Feedback Is Most Useful

- **Install issues**: Did setup work? If not, what failed?
- **Demo path**: Could you follow the demo? Where did you get stuck?
- **UI clarity**: Was anything confusing or hard to find?
- **Report quality**: Did the trust reports make sense?
- **Connector usefulness**: Are the import/sync features valuable?
- **Missing features**: What do you wish existed?
- **Docs gaps**: What documentation was missing or unclear?

## What Not to Upload

- **Do not upload real sensitive company data** unless you understand the local storage model and security limitations
- Use the sample data in `demo/sample-data/` for initial testing
- If you must test with real data, ensure it is non-confidential and anonymized

## How to Report Bugs

1. Collect diagnostics: `./scripts/collect-diagnostics.sh`
2. Open a GitHub issue using the **Bug Report** template
3. Include:
   - App version
   - Your OS, Python, and Node versions
   - Setup method (Docker or local scripts)
   - Steps to reproduce
   - Expected vs actual behavior
   - Diagnostics output (with secrets redacted)

## How to Collect Diagnostics

```bash
./scripts/collect-diagnostics.sh
# Output: diagnostics/<timestamp>/diagnostics.txt
```

The diagnostics script is safe by default — it **does not collect**:
- API keys, tokens, or passwords
- `.env` contents
- Uploaded documents or evidence chunks
- Report contents
- Absolute file contents from your local system

## Known Limitations

Review [KNOWN_LIMITATIONS.md](./KNOWN_LIMITATIONS.md) before testing — it lists:
- Current beta limitations
- What is intentionally not implemented
- Environment requirements (Tesseract, Python 3.11+, Node 18+)

## How to Provide General Feedback

Use the **Beta Feedback** issue template. Positive and negative feedback are both valuable.

---

*Thank you for testing! Your feedback directly shapes the next milestones.*
