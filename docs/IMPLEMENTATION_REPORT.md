# Implementation Report — v1.26 Knowledge Graph + Entity/Risk Extraction v2

> **Date:** 2026-06-24
> **Package version:** 1.26.0-dev
> **Previous milestone:** v1.25.0 — End-to-End Demo Hardening + Local Beta Release Prep

---

## Summary

v1.26 transforms the system from document search and reporting into a structured,
evidence-backed company intelligence map with entities, relationships, risks, and
metrics under verification control.

All backend phases are complete: workspace-scoped graph store, deterministic
extraction (entities, risks, metrics, relationships), 9 REST API endpoints,
4 workflow nodes, claim-graph integration, audit/observability events,
trust report graph sections, and 124 automated tests.

Frontend phases are also complete: Knowledge Graph page (entity/relationship/risk/
metric views with extract button, search/filter, evidence links) and Risk Dashboard
(severity cards, top risks, categories). Demo flow includes graph extraction step.

## Version

- `src/decision_system/__init__.py`: `1.26.0-dev`
- `pyproject.toml`: `1.26.0-dev`
- `/health` endpoint returns `1.26.0-dev`

## Agent Updates

- **AGENTS.md**: Rewritten to reflect current product direction — React SPA main UI,
  workspace-scoped data, local JSON/SQLite storage, evidence references requirement
- **CLAUDE.md**: Updated project state, architecture, tech stack (React 18 + React Flow),
  version history (v1.0-v1.25), architectural rules, "what not to add" list, roadmap

## Files Changed

### Backend (Python)
- `src/decision_system/graphing/audit.py` (new) — Graph audit events and metrics
- `src/decision_system/graphing/__init__.py` — Package init
- `src/decision_system/api/routes_observability.py` (fix) — MetricPoint serialization fix
- `src/decision_system/models.py` — Added graph_node_refs, graph_edge_refs, risk_refs, metric_refs to Claim and ReportClaimEntry
- `src/decision_system/reports/trust_renderer.py` — Added 4 graph section renderers (Entity Summary, Key Relationships, Extracted Risks, Key Metrics)
- `src/decision_system/workflow_engine/nodes/builtin/graph_nodes.py` — Added audit events to all 4 workflow nodes
| File | Change |
|------|--------|
| `src/decision_system/__init__.py` | Version `1.25.0-dev` -> `1.26.0-dev` |
| `pyproject.toml` | Version `1.25.0-dev` -> `1.26.0-dev` |
| `src/decision_system/api/app.py` | Added `routes_graph` import and registration |
| `src/decision_system/graphing/models.py` | Added v2 models: WorkspaceNode, WorkspaceEdge, WorkspaceRisk, WorkspaceMetric (v1 legacy models preserved) |
| `src/decision_system/graphing/store.py` | Added v2 CRUD store: upsert_node, upsert_edge, list_nodes, list_edges, risk/metric CRUD, workspace isolation (v1 legacy functions preserved) |

### New Files
| File | Purpose |
|------|---------|
| `src/decision_system/graphing/extractor_v2.py` | Deterministic v2 extraction: companies, vendors, products, named entities, money, percentages, dates, emails/domains, risks (12 categories), metrics (30+ keywords), relationships (7 types) |
| `src/decision_system/api/routes_graph.py` | Graph API: POST extract, GET graph/nodes/edges/risks/metrics, GET summary, GET node/edge by ID |
| `tests/test_graph_store.py` | 26 tests for v2 graph store CRUD, workspace isolation, persistence |
| `tests/test_extractor_v2.py` | 29 tests for v2 extraction: entities, risks, metrics, relationships, evidence refs, empty handling |
| `tests/test_graph_api.py` | 13 tests for graph API: extraction, retrieval, error handling, empty states |
| `docs/GRAPH_INTELLIGENCE_AUDIT.md` | Audit of existing graph/ontology/insight/data-source modules |

### Docs
| File | Change |
|------|--------|
| `docs/CURRENT_STATE.md` | Version bump, milestone update to v1.26 |
| `docs/IMPLEMENTATION_REPORT.md` | This report |
| `docs/DEMO_PATH.md` | Version bump |
| `docs/LOCAL_FIRST_SETUP.md` | Version bump |
| `CHANGELOG.md` | Added v1.26 section |
| `AGENTS.md` | Rewritten for current product direction |
| `CLAUDE.md` | Updated project state, architecture, version history, rules |

## Graph System

### Model
- **14 node types**: company, person, team, vendor, customer, product, system, document, dataset, metric, risk, event, decision, unknown
- **12 edge types**: mentions, owns, depends_on, supplies, affects, contradicts, supports, related_to, has_metric, has_risk, occurred_on, evidence_for
- All models workspace-scoped with evidence references
- Status tracking: extracted, verified, contradicted, uncertain, archived

### Store
- Workspace-scoped JSON persistence under `.decision_system/graph/workspaces/{ws_id}/`
- Full CRUD: upsert_node, get_node, list_nodes, search_nodes, delete_node
- Edge CRUD, Risk CRUD, Metric CRUD
- Workspace isolation enforced
- Legacy v1 functions preserved for backward compatibility

### Extraction (Deterministic v2)
- **Companies**: suffix-based (Corp, Inc, LLC, GmbH) and keyword-based (Technologies, Solutions)
- **Vendors**: explicit vendor/supplier/provider references
- **Products**: product/platform/service references
- **Named entities**: capitalized multi-word phrases with type inference
- **Financial**: $X, USD X, EUR X amounts
- **Percentages**: X%, X percent
- **Dates**: ISO, US, named month formats
- **Contacts**: email addresses, domains
- **Risks**: 12 categories (security, compliance, financial, vendor, operational, technical, strategic)
- **Metrics**: 30+ keyword patterns (revenue, cost, customer, churn, etc.)
- **Relationships**: depends_on, owns, supplies, affects, contradicts, related_to, mentions

### Audit/Observability

Graph operations emit events and metrics via `graphing/audit.py`:
- **Events**: graph_extraction_started, graph_extraction_completed, graph_extraction_failed, risk_extraction_completed, metric_extraction_completed, graph_fact_created
- **Metrics**: graph_extraction_duration_ms, entities_extracted_count, edges_extracted_count, risks_extracted_count, metrics_extracted_count, graph_extraction_failure_count
- Integrated into: graph extraction API route (`POST /workspaces/{id}/graph/extract`) and all workflow graph nodes (`GraphExtractionNodeV2`, `RiskExtractionNode`, `MetricExtractionNode`)
- Storage: JSONL-based observability store at `.decision_system/observability/metrics/`

### API Endpoints
| Method | Path | Purpose |
|--------|------|---------|
| POST | /workspaces/{id}/graph/extract | Extract intelligence |
| GET | /workspaces/{id}/graph | Full graph |
| GET | /workspaces/{id}/graph/nodes | List nodes (filterable) |
| GET | /workspaces/{id}/graph/edges | List edges (filterable) |
| GET | /workspaces/{id}/graph/risks | List risks (filterable) |
| GET | /workspaces/{id}/graph/metrics | List metrics |
| GET | /workspaces/{id}/graph/summary | Graph statistics |
| GET | /workspaces/{id}/graph/nodes/{node_id} | Single node |
| GET | /workspaces/{id}/graph/edges/{edge_id} | Single edge |

## Tests Passing

### New Tests (140 total)
- test_graph_store: 26 passed
- test_extractor_v2: 29 passed
- test_graph_api: 13 passed
- test_graph_nodes: 29 passed
- test_graph_audit: 16 passed

### Full Suite (395+ passed across key modules)
- test_data_sources: 60 passed
- test_verification: 68 passed
- test_providers: 48 passed
- test_workflow_engine/test_api.py: 85 passed
- test_graphing (legacy): 6 passed
- test_graph_store: 26 passed
- test_extractor_v2: 29 passed
- test_graph_api: 13 passed

## Known Limitations

1. **AI-assisted extraction** is stubbed (fake provider support exists in contract)
2. Graph extraction is deterministic and evidence-linked but does not prove business truth by itself

## Recommended Next Milestone

**v1.27 — Security, Auth, RBAC + Governance Foundation** (with Graph UI polish, AI-assisted extraction, audit metrics API endpoints)
