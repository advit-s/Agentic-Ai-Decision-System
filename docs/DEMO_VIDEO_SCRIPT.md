# Demo Video Script — v1.35.0-dev

> **Version:** 1.35.0-dev
> **Milestone:** Public Beta Release Candidate + Demo Video Script
> **Target length:** 5–8 minutes
> **Audience:** Developers, technical evaluators, open-source reviewers

---

## Prerequisites

Before recording:
- [ ] Docker installed OR local scripts working
- [ ] Frontend: `cd web/workflow-builder && npm run build` completed
- [ ] Sample data: `demo/sample-data/` exists with demo files
- [ ] Fake provider configured (default — no API key needed)
- [ ] Screen recording tool ready (e.g., OBS, QuickTime, Peek)
- [ ] Terminal with large font and clear color scheme
- [ ] Browser window at 1280x720 or 1920x1080

---

## Scene 1: Opening (30 seconds)

**Visual:** Terminal + browser side by side

**Narration:**
"Welcome to the Agentic AI Decision System — a local-first, self-hosted company intelligence automation app. It turns your documents, datasets, and read-only imports into searchable evidence, verified claims, knowledge graphs, and trust reports. Everything runs locally, with no API keys required."

**Screen action:**
- Show README or project page briefly
- Type: `docker compose up --build` (or `./scripts/start-local.sh --all`)

---

## Scene 2: App Shell (30 seconds)

**Visual:** Browser loading the app

**Narration:**
"Once the app starts, you'll see the React SPA with the sidebar navigation. Notice the beta label and version — this is v1.35, the public beta release candidate. The sidebar shows all main sections: Workspace, Data Sources, Evidence Search, Connectors, Knowledge Graph, Workflow Builder, and more."

**Screen action:**
- Show app loading
- Mouse over sidebar items
- Point out beta label and version

---

## Scene 3: Workspace + Data Upload (60 seconds)

**Visual:** Data Sources page

**Narration:**
"First, create a workspace — this is where all your data stays isolated. Then upload documents. The system supports PDF, DOCX, XLSX, MD, TXT, CSV, and JSON files. Let me upload a few sample documents from the demo folder."

**Screen action:**
- Create workspace
- Upload demo files: `demo/sample-data/*.md`
- Show upload progress
- Show parsed files in the source list

---

## Scene 4: Evidence Search (30 seconds)

**Visual:** Evidence Search page

**Narration:**
"After indexing, you can search across all your uploaded documents. The system uses Chroma vector search for semantic matching, with keyword fallback. Results show source references and relevance scores."

**Screen action:**
- Type a search query
- Show results with source documents
- Click a result to show detail

---

## Scene 5: Configure Provider (20 seconds)

**Visual:** Provider Manager page

**Narration:**
"The Fake Provider is built in and requires no configuration — it generates deterministic analysis so you can test the full workflow without any API keys. Real LLM providers like OpenAI and Ollama are optional."

**Screen action:**
- Show Provider Manager with Fake Provider selected
- Show provider status as "configured"

---

## Scene 6: Run Workflow (60 seconds)

**Visual:** Workflow Builder page

**Narration:**
"The workflow builder lets you create and run analysis workflows. Let's load the 'Local Trust Report Demo' workflow — it runs through evidence retrieval, technical analysis, risk analysis, claim extraction, verification, and report writing."

**Screen action:**
- Load demo workflow
- Click "Run"
- Show execution progress (node states updating)
- Show execution complete

---

## Scene 7: Claim Ledger (30 seconds)

**Visual:** Claim Ledger page

**Narration:**
"After execution, extracted claims appear in the Claim Ledger. Each claim has a status — verified, unsupported, or contradicted — with evidence references. You can verify all claims or scan for contradictions."

**Screen action:**
- Show claim list with status badges
- Verify claims
- Show evidence references

---

## Scene 8: Knowledge Graph (45 seconds)

**Visual:** Knowledge Graph page

**Narration:**
"The system also extracts entities, relationships, risks, and metrics into a knowledge graph. You can explore connected entities, view risk severity levels, and click through to evidence sources."

**Screen action:**
- Show graph visualization
- Pan and zoom
- Click an entity to show details
- Show risks and metrics panels

---

## Scene 9: Trust Report (45 seconds)

**Visual:** Reports page

**Narration:**
"Finally, generate a Trust Report — a Markdown document with executive summary, evidence analysis, claim verification results, risk assessment, and graph analysis. Every citation links back to source evidence. Export it as Markdown to share with stakeholders."

**Screen action:**
- Generate report
- Show report sections
- Click evidence citations
- Export as Markdown
- Open exported .md file

---

## Scene 10: Feedback + Closing (30 seconds)

**Visual:** Browser + terminal

**Narration:**
"This is the public beta release candidate, and we'd love your feedback. If you find a bug, collect diagnostics with `./scripts/collect-diagnostics.sh` and open an issue using the templates. Check the Reviewer Guide for detailed testing guidance. Thanks for watching!"

**Screen action:**
- Run `./scripts/collect-diagnostics.sh`
- Show output
- Point to GitHub issue templates link

---

## Backup Plan

| Scenario | Fallback |
|----------|----------|
| Docker unavailable | Use local scripts: `./scripts/start-local.sh --all` |
| OCR/Tesseract unavailable | Use text-based documents only (`.md`, `.txt`) |
| Frontend build needed | Mention `cd web/workflow-builder && npm run build` |
| No sample data | Create a simple `.md` file with test content |
| Screen recording limitations | Describe steps as screenshots |

## Closing Call to Action

"Try it yourself: clone the repo, run `docker compose up --build`, and follow the demo path. Report issues, suggest features, and tell us what you think. Your feedback shapes the next milestones."
