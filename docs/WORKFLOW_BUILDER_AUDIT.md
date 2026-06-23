# Workflow Builder UX Audit

> **Date:** 2026-06-23
> **Version:** 1.22.0-dev
> **Audit Scope:** Frontend workflow builder UI, backend API integration, mock/live mode

---

## What works

| Feature | Status | Notes |
|---------|--------|-------|
| Node palette with categories | ✅ Works | 5 categories: Triggers, Data, AI/Analysis, Output, Flow Control |
| Drag-and-drop canvas | ✅ Works | React Flow canvas with snap-to-grid, minimap, controls |
| Node connections | ✅ Works | Edge creation between nodes |
| Config panel | ✅ Works | Auto-generated form from config_schema, provider dropdown |
| Execution panel | ✅ Works | Live status updates, elapsed timer, node status badges |
| Execution timeline | ✅ Works | Bar chart with durations |
| Run workflow | ✅ Works | Triggers execution via API |
| Template dialog | ✅ Works | Load templates from predefined list |
| Trust dashboard | ✅ Works | Shows trust metrics and report actions |
| Provider Manager | ✅ Works | CRUD for provider configurations |
| Schedule Manager | ✅ Works | List, create, delete schedule triggers |
| Execution history | ✅ Works | List and detail views |
| Execution comparison | ✅ Works | Side-by-side diff |
| Workflow diff | ✅ Works | Visual version comparison |
| Review gates | ✅ Works | Approve/reject with notes |
| Keyboard shortcuts | ✅ Works | Ctrl+S, Delete, Escape, etc. |
| Shortcuts help | ✅ Works | Modal with all shortcuts |
| Toast notifications | ✅ Works | Info/success/warning/error |
| Theme toggle | ✅ Works | Dark/light mode |
| Resizable panels | ✅ Works | Adjustable panel widths |
| Claim ledger panel | ✅ Works | Status badges, filter by status |
| Verification integration | ✅ Works | Verify claims, contradictions, trust reports |
| Export markdown/JSON | ✅ Works | Trust report and claim export |

## What is confusing

| Issue | Details |
|-------|---------|
| **Node category naming** | Current categories (Triggers, Data, AI/Analysis, Output, Flow Control) don't match the mental model users need. Evidence, Verification, Review, and Report nodes are mixed into AI/Analysis and Output. |
| **Node labels vs backend types** | Some nodes have technical backend type names visible in config panel (e.g., `decision_system.evidence_synthesis`) while labels are human-readable (e.g., "Evidence Synthesis"). The config panel shows the raw type. |
| **Provider field in config** | Provider is a simple dropdown with "fake", "nvidia_nim", "ollama" but this doesn't use the new v1.21 provider runtime. It's hardcoded in mockData.js. |
| **Template categories** | Template categories (Starter, Research, Data Analysis, Compliance, Full Pipeline) don't align with the new node catalog categories. |
| **Error policy dropdown** | Shown on ALL nodes, but only relevant for certain node types. Confusing to novice users. |
| **Save vs Run** | Multiple save buttons and run buttons. Users may not know the save state before running. |
| **Mock vs Live mode** | App auto-detects live backend but the API client has mock fallback. No clear indicator of which mode is active. |
| **"Code" node** | Disabled but still visible in palette with tooltip about being unsafe. Could confuse. |

## What is mock-only

| Feature | Mock | Live | Notes |
|---------|------|------|-------|
| Node types list | ✅ Full mock list | ✅ Real API | Falls back to mock when API unavailable |
| Workflow CRUD | ✅ Mock | ✅ Real | |
| Execute workflow | ✅ Mock | ✅ Real | |
| Provider CRUD | ✅ Mock | ✅ Real | Uses workflow_engine provider API |
| Schedule CRUD | ✅ Mock | ✅ Real | |
| Reviews | ✅ Mock | ✅ Real | |
| Trust reports | ✅ Mock | ✅ Real | Uses verification API |
| Evidence synthesis | ❌ | ✅ Real | Only available in live mode |
| Provider Manager UI | ✅ Both | ✅ Both | Real data with mock fallback |

## What nodes exist

Nodes currently defined in mockData.js (frontend palette):

| Node Type | Label | Category | Notes |
|-----------|-------|----------|-------|
| `decision_system.trigger_manual` | Manual Trigger | trigger | ✅ |
| `decision_system.input_text` | Input Text | trigger | ✅ |
| `decision_system.retrieve` | Retrieve Evidence | data | ✅ |
| `decision_system.technical_analyst` | Technical Analyst | ai | ✅ |
| `decision_system.risk_analyst` | Risk Analyst | ai | ✅ |
| `decision_system.extract_claims` | Extract Claims | ai | ✅ |
| `decision_system.verify_claims` | Verify Claims | ai | ✅ |
| `decision_system.write_report` | Write Report | output | ✅ |
| `decision_system.extract_graph` | Extract Graph | data | ✅ |
| `decision_system.profile_data` | Profile Data | data | ✅ |
| `decision_system.map_ontology` | Map Ontology | data | ✅ |
| `decision_system.detect_patterns` | Detect Patterns | data | ✅ |
| `decision_system.war_room` | Run War Room | ai | ✅ |
| `decision_system.filter` | Filter | flow | ✅ |
| `decision_system.merge` | Merge | flow | ✅ |
| `decision_system.code` | Code | flow | ❌ Disabled/unsafe |
| `decision_system.cron_trigger` | Cron Trigger | trigger | ✅ |
| `decision_system.webhook_trigger` | Webhook Trigger | trigger | ✅ |
| `decision_system.file_watch_trigger` | File Watch Trigger | trigger | ✅ |
| `decision_system.researcher` | Researcher | ai | ✅ |
| `decision_system.critic` | Critic / Judge | ai | ✅ |
| `decision_system.synthesizer` | Decision Synthesizer | ai | ✅ |
| `decision_system.review_gate` | Review Gate | ai | ✅ Wrong category |
| `decision_system.data_analyst` | Data Analyst | ai | ✅ |
| `decision_system.planner` | Planner | ai | ✅ |
| `decision_system.auditor` | Auditor | ai | ✅ |
| `decision_system.compliance_checker` | Compliance Checker | ai | ✅ |
| `decision_system.code_runner` | Code Runner | ai | ✅ |
| `decision_system.contradiction_scan` | Contradiction Scan | ai | ✅ Wrong category |
| `decision_system.evidence_search` | Evidence Search | ai | ✅ Wrong category |
| `decision_system.verification_summary` | Verification Summary | ai | ✅ Wrong category |
| `decision_system.claim_verifier_v2` | Claim Verifier v2 | ai | ✅ Wrong category |
| `decision_system.evidence_synthesis` | Evidence Synthesis | ai | ✅ Wrong category |

## What nodes are missing from UI

| Missing Node | Backend Exists | Priority | Notes |
|-------------|---------------|----------|-------|
| **Start** (always-first) | ✅ | High | Need a clear start node that's always first |
| **Manual Input** (dedicated) | ✅ | Medium | InputText already exists, but could be renamed |
| **Evidence Search** (clearer) | ✅ | High | Currently called "Retrieve Evidence" |
| **Evidence Synthesis** (clearer) | ✅ | High | Already exists, needs clearer category |
| **Claim Verification** (clearer) | ✅ | High | Already exists, needs clearer category |
| **Contradiction Scan** | ✅ | High | Already exists, verify category |
| **Verification Summary** | ✅ | Medium | Already exists, verify category |
| **Review Gate** | ✅ | Medium | Already exists, wrong category |
| **Trust Report** | ✅ | High | New node type for trust report generation |

## What API endpoints are used

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/workflows/nodes` | GET | List node types | ✅ |
| `/workflows` | GET/POST | List/create workflows | ✅ |
| `/workflows/{id}` | GET/PUT/DELETE | CRUD single workflow | ✅ |
| `/workflows/{id}/execute` | POST | Execute workflow | ✅ |
| `/executions/{id}` | GET | Get execution detail | ✅ |
| `/executions` | GET | List execution history | ✅ |
| `/executions/{id}/stream` | WS | Live execution events | ✅ |
| `/executions/{id}/replay` | WS | Replay execution events | ✅ |
| `/providers` | GET/POST | List/create providers | ✅ (conflict between old and new routes) |
| `/providers/{name}` | GET/PUT/DELETE | Provider CRUD | ✅ (conflict) |
| `/providers/system/default` | POST | Set default provider | ✅ (conflict) |
| `/schedules` | GET/POST | Schedule CRUD | ✅ |
| `/reviews` | GET | List reviews | ✅ |
| `/reviews/{id}/resolve` | POST | Resolve review | ✅ |
| `/workspaces/{id}/claims` | GET | List claims | ✅ |
| `/workspaces/{id}/contradictions` | GET | List contradictions | ✅ |
| `/workspaces/{id}/trust-report` | GET | Generate trust report | ✅ |
| `/workspaces/{id}/export` | GET | Export workspace | ✅ |

## Known UX gaps

| Gap | Severity | Description |
|-----|----------|-------------|
| No pre-run validation | High | User can run workflow with missing fields, disconnected nodes |
| No execution debugger | High | Cannot inspect node inputs/outputs after execution |
| Canvas execution status | Medium | Node status updates work but could be more prominent |
| Empty workspace state | Medium | Empty state not helpful for first-time users |
| First-run onboarding | High | No onboarding flow for new users |
| Provider dropdown in palette | Medium | Provider selection uses hardcoded enum, not real provider store |
| Template limiting | Medium | Templates use specialist node types, not evidence/verification/trust flow |
| No import/export | Medium | Cannot export/import workflow JSON |
| Autosave indicator | Low | Has unsaved changes indicator but no auto-save |
| Version history UI | Low | Version support exists but not exposed in UI |
| Error display polish | Medium | Error messages functional but not user-friendly |
| Keyboard navigation | Medium | Some panels not fully keyboard-accessible |
| Color-only status | Low | Some status indicators rely on color alone |

## v1.22 fixes planned

See `docs/WORKFLOW_BUILDER.md` and milestone plan for the complete list.

Priority order:

1. Node catalog cleanup (categories, labels, safety)
2. Node configuration panels (dedicated per-type config UI)
3. Workflow validation before run
4. Execution run experience (live status)
5. Execution debugger panel
6. Guided demo templates
7. First-run onboarding
8. Provider selection UX inside workflows
9. Report actions from workflow result
10. Workflow import/export
11. Autosave and version visibility
12. Error and empty state polish
13. Accessibility and usability pass

## Future gaps (beyond v1.22)

| Gap | Description |
|-----|-------------|
| PDF/DOCX/XLSX parsing | Only txt, md, csv supported |
| Workspace export/import | Existing but not fully reliable |
| Frontend Data Sources page | Basic, needs real API connection |
| Real-time collaboration | Not planned (local-first) |
| Undo/redo | Missing from canvas |
| Node search | Palette can get large, needs search |
| Conditional branching | Workflow engine supports if/else but no UI |
| Loop/iteration | No for-each node type |
| Docker Compose v2 | Improved networking and startup |
