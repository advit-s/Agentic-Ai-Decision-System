# Graph Intelligence Audit — v1.26 Baseline

> **Date:** 2026-06-23
> **Version:** 1.26.0-dev
> **Audit scope:** Existing graph, ontology, insight, data-source, and workflow modules

---

## 1. Existing Graph System (`src/decision_system/graphing/`)

### 1.1 Models (`models.py`)

| Aspect | Current State | v1.26 Target |
|--------|---------------|--------------|
| Node types | 11 literal types (project, system, team, person, vendor, customer, incident, risk, decision, technology, unknown) | Expand to include company, product, document, dataset, metric, event, and allow dynamic extension |
| Edge types | 8 literal types (depends_on, owned_by, caused, affects, blocks, mitigates, contradicts, related_to) | Expand to mentions, supplies, has_metric, has_risk, occurred_on, evidence_for |
| Node fields | entity_id, name, entity_type, source_evidence_ids, source_filenames, confidence | Add workspace_id, normalized_name, description, status (extracted/verified/contradicted/uncertain/archived), evidence_ids, chunk_ids, metadata, timestamps |
| Edge fields | relationship_id, source_entity_id, relation_type, target_entity_id, source_evidence_ids, source_filenames, confidence | Add workspace_id, label, status, evidence_ids, chunk_ids, metadata, timestamps |
| Workspace isolation | **None** — no workspace_id field | Required — all nodes/edges scoped to workspace |
| Evidence refs | source_evidence_ids, source_filenames | Add dedicated evidence_ids, chunk_ids arrays |

### 1.2 Store (`store.py`)

| Aspect | Current State | v1.26 Target |
|--------|---------------|--------------|
| Location | `.decision_system/graph/knowledge_graph.json` | `.decision_system/graph/` (directory with workspace subdirs) |
| Format | Single JSON file per-repo | One store per workspace |
| API | save_knowledge_graph(), load_knowledge_graph() | upsert_node, upsert_edge, list_nodes, list_edges, get_node, get_edge, search_nodes, delete_node, delete_edge, list_graph_for_workspace |
| Concurrency | No protection | Simple file-lock or atomic write |
| Merge/duplicate | No dedup logic | Dedup by normalized_name within workspace |

### 1.3 Extractor (`extractor.py`)

| Aspect | Current State | v1.26 Target |
|--------|---------------|--------------|
| Method | Rule-based patterns only | Rule-based (deterministic) + optional AI-assisted |
| Patterns | 7 relation patterns + CONTRADICTS marker | Expanded: company names, vendor names, product names, money amounts, percentages, dates, emails/domains, risk phrases, metric names, document titles |
| Entity inference | Keyword-based (team, vendor, customer, etc.) | Improved heuristic + concept-based |
| Risk extraction | **None** (only contradictions) | Risk phrases, financial signals, vendor issues, security/compliance |
| Metric extraction | **None** | Currency, percentages, counts, dates, financial metrics |
| Event extraction | **None** | Dates, milestones, incidents |

### 1.4 Inspector (`inspector.py`)

| Aspect | Current State | v1.26 Target |
|--------|---------------|--------------|
| Output | Entity/relationship counts, top connected entities | Expand to risks, metrics; workspace-filtered |
| Risk dashboard | **None** | Risk count, severity, categories, top risks |
| Metric summary | **None** | Metric types, values, evidence counts |

---

## 2. Existing Ontology System (`src/decision_system/ontology/`)

### 2.1 Models

| Aspect | Status |
|--------|--------|
| Purpose | Maps CSV columns to business concepts |
| Concept types | entity, metric, signal, relationship, risk, process, unknown |
| 38 built-in concepts | Revenue, expense, profit_margin, customer_segment, etc. |
| Relevance to v1.26 | Ontology concepts can be reused as entity types and for categorizing extracted risks/metrics |

### 2.2 Gaps for v1.26
- Ontology is CSV-focused, not graph-focused
- No built-in graph entity concepts (company, vendor, product, team)
- No mapping from extracted entities to ontology concepts

---

## 3. Existing Insight System (`src/decision_system/insights/`)

### 3.1 Models

| Aspect | Status |
|--------|--------|
| Insight fields | insight_id, title, description, category, severity, confidence, source_type, source_ids, evidence_summary, recommended_action |
| Severity levels | low, medium, high, critical |
| Categories | 16 categories (revenue_risk, profit_margin_risk, etc.) |

### 3.2 Detectors

| Detector | Source | Reusable for v1.26? |
|----------|--------|---------------------|
| Missing data | Profile | No (data quality, not graph) |
| Data quality | Profile | No |
| Sales channel concentration | CSV | No |
| Customer concentration | CSV | No |
| Revenue risk | CSV | Partial — pattern for risk detection |
| Marketing ROI | CSV | No |
| Feedback risk | CSV | No |
| Product risk | CSV | No |
| Competitor risk | CSV | No |
| Operations bottleneck | CSV | No |
| Analytics conversion | CSV | No |
| Strategic gap | CSV | No |
| Dependency risk | Graph | **Yes** — pattern for graph-based risk |
| Contradiction | Graph | **Yes** — pattern for graph-based detection |
| Ownership gap | Graph | **Yes** — pattern for ownership detection |

### 3.3 Gaps for v1.26
- No risk entity extraction (risks as first-class graph nodes)
- No metric extraction (metrics as first-class graph nodes)
- No event extraction
- Insight store is separate from graph store
- No API for risk/metric listing

---

## 4. Existing Data Sources Module (`src/decision_system/data_sources/`)

### 4.1 Strengths for v1.26
- **Workspace-scoped models** — DataSource, DataSourceChunk, EvidenceSearchResult all have workspace_id
- **Workspace isolation** — All operations respect workspace boundaries
- **Evidence tracking** — Chunks have source_id, workspace_id, evidence_id
- **File parsing** — PDF/DOCX/XLSX/TXT/MD/CSV/JSON parsers exist
- **OCR support** — tesserocr-based image/PDF OCR

### 4.2 Integration Points
- Graph extraction should consume parsed chunks (DataSourceChunk) and evidence search results
- Evidence references should link to DataSourceChunk IDs
- Workspace isolation pattern should be followed by graph store

---

## 5. Existing API Structure (`src/decision_system/api/`)

### 5.1 Current Routes
- `/health` — Health check with version
- `/workspaces/*` — Workspace CRUD
- `/data-sources/*` — File upload, parse, index, search
- `/providers/*` — Provider management
- `/verification/*` — Claim verification
- `/executions/*` — Workflow execution reports
- `/ontology` — Ontology mapping
- `/insights` — Insight display
- `/war-room/*` — War-cabinet protocol
- `/orchestration/*` — Orchestration pipeline

### 5.2 Missing for v1.26
- `POST /workspaces/{id}/graph/extract` — Trigger graph extraction
- `GET /workspaces/{id}/graph` — Full workspace graph
- `GET /workspaces/{id}/graph/nodes` — List nodes
- `GET /workspaces/{id}/graph/edges` — List edges
- `GET /workspaces/{id}/risks` — List risks
- `GET /workspaces/{id}/metrics` — List metrics
- `GET /graph/nodes/{node_id}` — Single node
- `GET /graph/edges/{edge_id}` — Single edge

### 5.3 Route patterns to follow
- Lazy loading in `app.py` (add `routes_graph.py`)
- Workspace-scoped paths: `/workspaces/{workspace_id}/graph/...`
- Pydantic models for request/response

---

## 6. Existing Workflow Nodes (`src/decision_system/workflow_engine/nodes/`)

### 6.1 Current Graph-Related Nodes
| Node | Exists? | Notes |
|------|---------|-------|
| Retrieve Evidence | ✅ Built-in evidence_nodes.py | Workspace-scoped |
| Extract Graph | ✅ Built-in data_nodes.py | Uses existing `graphing/` extractor |
| Profile Data | ✅ Built-in data_nodes.py | CSV profiling |
| Detect Patterns | ✅ Built-in data_nodes.py | Uses insight detectors |

### 6.2 Missing for v1.26
| Node | Purpose |
|------|---------|
| GraphExtractionNode | v2 graph extraction with expanded entity/risk/metric types |
| RiskExtractionNode | Extract risks from documents |
| MetricExtractionNode | Extract metrics from documents |
| GraphSummaryNode | Summarize graph for report integration |

---

## 7. Test Coverage (`tests/`)

### 7.1 Existing Graph Tests
| Test file | Coverage |
|-----------|----------|
| tests/test_graphing/ | Basic entity/relationship extraction tests |
| tests/test_graph_extractor.py | Extractor tests |
| tests/test_graph_inspector.py | Inspector tests |

### 7.2 Missing for v1.26
- Graph store CRUD tests (workspace-scoped)
- Entity extraction v2 tests
- Relationship extraction v2 tests
- Risk extraction tests
- Metric extraction tests
- Graph API route tests
- Workflow node tests
- Report integration tests
- UI helper tests
- Audit event tests

---

## 8. Gap Summary

| Area | Gap | Priority | Effort |
|------|-----|----------|--------|
| Graph model | No workspace_id, limited types, no risk/metric nodes | High | Medium |
| Graph store | Single-file, no CRUD, no dedup | High | Medium |
| Entity extraction | Limited patterns, no money/date/domain | High | Medium |
| Relationship extraction | 7 patterns only | High | Small |
| Risk extraction | None as graph nodes | High | Medium |
| Metric extraction | None as graph nodes | High | Medium |
| AI-assisted extraction | Not implemented | Medium | Medium |
| Graph APIs | No endpoints | High | Small |
| Workflow nodes | No graph v2 nodes | High | Small |
| Graph UI | No knowledge graph section | High | Large |
| Risk dashboard | No risk visualization | High | Medium |
| Report integration | No graph sections in reports | Medium | Small |
| Audit events | No graph events | Medium | Small |
| Tests | Graph v1 tests exist, v2 needed | High | Medium |

---

## 9. Recommendations

1. **Reuse workspace isolation patterns** from `data_sources/` module
2. **Reuse evidence/chunk tracking patterns** from `data_sources/` models
3. **Reuse Insight model** as inspiration for Risk and Metric models
4. **Reuse existing `graphing/` extractor** as foundation — add patterns, don't rewrite
5. **Follow API route patterns** from existing workspace-scoped routes
6. **Follow workflow node patterns** from existing `builtin/data_nodes.py`
7. **Integrate with existing InsightStore** for risk aggregation
8. **Add workspace-scoped graph store** under `.decision_system/graph/workspaces/{ws_id}/`
