# Phase 5: Real LLM Provider Integration — Implementation Plan

> **Status:** Draft  
> **Version:** 1.0  
> **Date:** 2026-06-13  
> **Based on:** `docs/superpowers/specs/2026-06-13-llm-providers-phase5-design.md`

## Goal

Add a provider configuration system and wire real LLM calls into the 5 AI/Analysis nodes (TechAnalyst, RiskAnalyst, ExtractClaims, VerifyClaims, WriteReport). One unified OpenAI-compatible provider type. Fake-by-default. No API keys required for tests.

---

## Task Dependency Graph

```
                  ┌──────────────┐
                  │ Task 1:      │
                  │ Provider     │
                  │ models+store │
                  └──────┬───────┘
                         │
                  ┌──────▼───────┐
                  │ Task 2:      │
                  │ LLMClient    │
                  │ (HTTP caller)│
                  └──────┬───────┘
                         │
                  ┌──────▼───────┐
                  │ Task 3:      │
                  │ Provider     │
                  │ resolution   │
                  │ in engine    │
                  └──────┬───────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
   ┌──────▼──────┐ ┌────▼──────┐ ┌─────▼──────┐
   │ Task 4:     │ │ Task 5:   │ │ Task 6:    │
   │ AI nodes    │ │ Provider  │ │ Provider   │
   │ wire LLM    │ │ API routes│ │ CLI        │
   └──────┬──────┘ └────┬──────┘ └─────┬──────┘
          │              │              │
          └──────────────┼──────────────┘
                         │
                  ┌──────▼───────┐
                  │ Task 7:      │
                  │ Provider     │
                  │ API mock +   │
                  │ frontend     │
                  └──────────────┘
```

---

## Task 1: Provider models and JSON store

**Files to create:**
- `src/decision_system/workflow_engine/providers/__init__.py`
- `src/decision_system/workflow_engine/providers/store.py`

**Approach: Test-first.**

1. Write tests in `tests/test_workflow_engine/test_providers/test_store.py`:
   - `test_load_creates_default_when_missing` — no file exists → auto-creates with opencode entry
   - `test_load_returns_providers` — existing valid file → returns ProviderConfig list
   - `test_get_default_returns_first` — returns first provider
   - `test_get_default_returns_none_when_empty` — empty list → None
   - `test_get_by_name` — finds by name, returns None for missing
   - `test_save_persists` — save then load returns same data
   - `test_add_provider` — appends to list, duplicate name raises
   - `test_remove_provider` — removes by name, missing raises
   - `test_set_default_reorders` — moves named provider to first position
   - `test_auto_create_file_content` — verify default content has opencode first with correct fields
   - `test_config_path_is_relative_to_decision_system_dir` — uses `.decision_system/providers.json`

2. Run tests — they should fail (no code yet).

3. Implement `ProviderConfig` (Pydantic BaseModel) and `ProviderStore` in `store.py`:
   - `load()` reads JSON, validates with ProviderConfig, defaults to `[{opencode}]`
   - `save()` writes JSON
   - `get_default()`, `get(name)`, `add()`, `remove(name)`, `set_default(name)`
   - Always use `.decision_system/providers.json` relative to cwd
   - File permissions: owner read/write only for the config dir

4. Run tests — all pass.

5. **Commit:**
```
git add src/decision_system/workflow_engine/providers/
git add tests/test_workflow_engine/test_providers/
git commit -m "feat(providers): ProviderConfig model and ProviderStore with JSON persistence

- ProviderConfig Pydantic model (name, api_base, api_key_env, default_model)
- ProviderStore: load, save, get_default, get, add, remove, set_default
- Auto-creates default config with opencode as first/default provider
- ~400 lines (tests + implementation)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: LLMClient — unified HTTP caller

**Files to create:**
- `src/decision_system/workflow_engine/providers/exceptions.py`
- `src/decision_system/workflow_engine/providers/client.py`

**Approach:** Build a mockable HTTP client that speaks OpenAI `/chat/completions` format.

1. Write tests in `tests/test_workflow_engine/test_providers/test_client.py`:
   - `test_chat_completion_basic` — sends correct request body, returns response
   - `test_chat_completion_streaming` — calls on_token for each chunk
   - `test_chat_completion_accumulates_full_text` — returned text matches concatenated chunks
   - `test_chat_completion_without_streaming` — non-streaming path
   - `test_authentication_error` — 401 maps to AuthenticationError
   - `test_rate_limit_error` — 429 maps to RateLimitError
   - `test_model_not_found` — 404 maps to ModelNotFoundError (or provider-specific)
   - `test_timeout` — httpx timeout raises TimeoutError
   - `test_server_error` — 500 maps to ProviderError
   - `test_api_key_from_env` — uses os.environ[config.api_key_env]
   - `test_no_api_key_sends_no_header` — when api_key_env is None
   - `test_trailing_slash_stripped` — api_base `.../v1/` becomes `.../v1`
   - `test_custom_model_override` — passes model param instead of default_model

2. Run tests — fail.

3. Implement `exceptions.py`:
   ```python
   class ProviderError(Exception):
       def __init__(self, message: str, status_code: int = 500):
           ...

   class AuthenticationError(ProviderError): ...
   class RateLimitError(ProviderError): ...
   class ModelNotFoundError(ProviderError): ...
   class TimeoutError(ProviderError): ...
   ```

4. Implement `client.py` — `LLMClient` class:
   - `__init__` stores config, resolves API key from env
   - `chat_completion()` uses `httpx.AsyncClient`:
     - `POST {api_base}/chat/completions`
     - Headers: `Authorization: Bearer {api_key}` (if key present), `Content-Type: application/json`
     - Body: `{"model": ..., "messages": [...], "stream": true}`
     - Parses SSE: `data: {"choices":[{"delta":{"content":"..."}}]}`
     - Calls `on_token` per token, accumulates full text
     - Error mapping via `map_response_error(status_code, body)`
     - Timeout: 30s read timeout via httpx
   - Error helpers map HTTP status codes to exception types

5. Move `openai` dependency from optional `nvidia` to core in `pyproject.toml`:
   - Add `"openai>=1.0,<2.0"` to `[project.dependencies]`
   - Remove from `[project.optional-dependencies] nvidia`

6. Add `pytest-httpx` to dev dependencies:
   - Add `"pytest-httpx>=0.30,<1.0"` to `[project.optional-dependencies] dev`

7. Run tests — all pass.

8. **Commit:**
```
git add src/decision_system/workflow_engine/providers/exceptions.py
git add src/decision_system/workflow_engine/providers/client.py
git add tests/test_workflow_engine/test_providers/test_client.py
git add pyproject.toml
git commit -m "feat(providers): LLMClient — unified OpenAI-compatible HTTP caller

- LLMClient with streaming chat_completion() via httpx
- SSE parsing with on_token callback and text accumulation
- ProviderError exception hierarchy (auth, rate-limit, timeout, model, server)
- 30s read timeout, custom model override support
- Moved openai from optional nvidia to core dependency
- Added pytest-httpx for HTTP mocking in tests

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Provider resolution in the execution engine

**Files to modify:**
- `src/decision_system/workflow_engine/engine/context.py`
- `src/decision_system/workflow_engine/engine/executor.py`

**Goal:** `ExecutionContext` gains a `resolve_provider()` helper that resolves node override → system default → fake.

1. Write tests for `test_providers_resolution.py` (or add to `test_providers/`):
   - `test_resolve_with_node_override` — node specifies provider + model → returns ProviderConfig + model
   - `test_resolve_with_node_provider_only` — node specifies provider, no model → ProviderConfig + default_model
   - `test_resolve_without_override` — no node provider → returns system default
   - `test_resolve_fallback_to_fake` — no providers configured → returns None
   - `test_resolve_invalid_provider_name` — node references nonexistent provider → falls to default → if no default → None
   - `test_provider_store_passed_through_executor` — DAGEngine creates ExecutionContext with ProviderStore

2. Modify `execution/context.py`:
   - Add `provider_store: ProviderStore` field
   - Add `resolve_provider(self, provider_name: str | None = None, model: str | None = None) -> tuple[ProviderConfig | None, str | None]`:
     - If `provider_name` is set → `store.get(provider_name)`
     - If found → return `(config, model or config.default_model)`
     - If not found → try `store.get_default()`
     - If found → return `(default_config, default_config.default_model)`
     - If no providers → return `(None, None)`

3. Modify `executor.py`:
   - `DAGEngine.__init__` accepts optional `provider_store: ProviderStore | None`
   - Creates `ProviderStore()` if not provided
   - Passes `provider_store` into each `ExecutionContext`

4. Run all tests — pass.

5. **Commit:**
```
git add src/decision_system/workflow_engine/engine/context.py
git add src/decision_system/workflow_engine/engine/executor.py
git add tests/test_workflow_engine/test_providers/
git commit -m "feat(engine): provider resolution in ExecutionContext

- ExecutionContext.resolve_provider(): node override → system default → fake
- DAGEngine creates and passes ProviderStore through execution
- No changes to existing execution logic (backward compatible)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Wire real LLM into AI analysis nodes

**File to modify:**
- `src/decision_system/workflow_engine/nodes/analysis_nodes.py`

**Nodes to update (5 total):**
- TechAnalystNode
- RiskAnalystNode
- ExtractClaimsNode
- VerifyClaimsNode
- WriteReportNode

**Pattern for each node:**

1. Add a `_call_llm(self, context, system_prompt, user_prompt)` method that:
   - Calls `context.resolve_provider(self.config.get("provider"), self.config.get("model"))`
   - If config is None → calls existing `_fake_*()` method (backward compatible)
   - Creates `LLMClient(config)`
   - Calls `client.chat_completion()` with system + user messages
   - Returns parsed result

2. Each node's existing `execute()` method stays the same — just the internal LLM call path changes:
   - TechAnalyst: `_call_llm(...)` → parse technical findings JSON
   - RiskAnalyst: `_call_llm(...)` → parse risk items JSON
   - ExtractClaims: `_call_llm(...)` → parse claims JSON array
   - VerifyClaims: `_call_llm(...)` → parse verification results JSON
   - WriteReport: `_call_llm(...)` → return raw markdown text

3. Write tests:
   - For each node, test both paths: fake provider (no config) and real provider (mocked)
   - `test_tech_analyst_fake` — existing behavior unchanged
   - `test_tech_analyst_with_provider` — mock LLMClient, verify correct messages sent and output parsed
   - `test_risk_analyst_with_provider` — same pattern
   - `test_extract_claims_with_provider` — same pattern
   - `test_verify_claims_with_provider` — same pattern
   - `test_write_report_with_provider` — same pattern

4. Run all tests — pass.

5. **Commit:**
```
git add src/decision_system/workflow_engine/nodes/analysis_nodes.py
git add tests/
git commit -m "feat(nodes): wire real LLM calls into 5 AI analysis nodes

- TechAnalyst, RiskAnalyst, ExtractClaims, VerifyClaims, WriteReport
- Each node calls _call_llm() which resolves provider and calls LLMClient
- Falls back to fake provider when no real provider is configured
- Backward compatible — existing tests unchanged, new mock-http tests added

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Provider API routes

**File to create:**
- `src/decision_system/workflow_engine/api_providers.py`

**File to modify:**
- `src/decision_system/workflow_engine/api.py`

1. Write tests in `tests/test_workflow_engine/test_api_providers.py`:
   - `test_list_providers_empty` — no providers → `{"providers": []}` (override store)
   - `test_list_providers_with_data` — returns provider list (no api_key_env exposed)
   - `test_list_returns_api_key_configured` — boolean, not the env var name
   - `test_add_provider` — POST creates, returns created provider
   - `test_add_duplicate_name` — returns 409
   - `test_add_invalid_body` — missing required fields → 422
   - `test_update_provider` — PUT updates existing
   - `test_update_nonexistent` — returns 404
   - `test_delete_provider` — DELETE removes, subsequent GET returns 404
   - `test_delete_nonexistent` — returns 404
   - `test_set_default` — PUT reorders provider to first
   - `test_set_default_nonexistent` — returns 404

2. Implement `api_providers.py`:
   - Module-level `_provider_store = ProviderStore()` singleton (same pattern as `api.py`)
   - `router = APIRouter(prefix="/providers", tags=["providers"])`
   - `GET /` → `list_providers()` — returns `{"providers": [...]}` with `api_key_configured` boolean
   - `POST /` → `add_provider(body)` — validate, store.get to check duplicate, store.add, 201
   - `PUT /{name}` → `update_provider(name, body)` — validate, store.get to find, store.save after update
   - `DELETE /{name}` → `delete_provider(name)` — store.remove, 200
   - `PUT /{name}/set-default` → `set_default(name)` — store.set_default, 200
   - All return `api_error(...)` helpers from models.py for errors

3. Modify `api.py`:
   - Import `api_providers` router
   - Include it: `router.include_router(api_providers.router)`

4. Run tests — pass.

5. **Commit:**
```
git add src/decision_system/workflow_engine/api_providers.py
git add src/decision_system/workflow_engine/api.py
git add tests/test_workflow_engine/test_api_providers.py
git commit -m "feat(api): provider CRUD API routes

- GET/POST/PUT/DELETE /providers + PUT /providers/{name}/set-default
- api_key_configured boolean (never exposes env var names)
- Follows existing api.py singleton pattern
- 14 new tests

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Provider CLI commands

**File to modify:**
- `src/decision_system/workflow_engine/cli.py`
- `src/decision_system/cli.py`

1. Write tests in `tests/test_workflow_engine/test_cli.py` (appended to existing test file):
   - `test_providers_list_empty`
   - `test_providers_list_with_data`
   - `test_providers_add`
   - `test_providers_add_duplicate`
   - `test_providers_remove`
   - `test_providers_remove_nonexistent`
   - `test_providers_set_default`
   - `test_providers_check` — shows which providers have valid keys

2. Add `providers_app` Typer sub-app to `cli.py`:
   ```
   decision-system providers list
   decision-system providers add [--name] [--api-base] [--api-key-env] [--default-model]
   decision-system providers remove <name>
   decision-system providers set-default <name>
   decision-system providers check
   ```

3. Wire `providers_app` into the CLI tree (probably under `workflow` or as a top-level group).

4. Run tests — pass.

5. **Commit:**
```
git add src/decision_system/workflow_engine/cli.py
git add tests/
git commit -m "feat(cli): provider management CLI commands

- list, add, remove, set-default, check sub-commands
- ASCII table output with Rich
- Integrated into workflow CLI tree

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Frontend — mock API + ProviderManager + ProviderSelector

**Files to create:**
- `web/workflow-builder/src/components/ProviderManager.jsx`
- `web/workflow-builder/src/styles/provider-manager.css`
- `web/workflow-builder/src/components/ProviderSelector.jsx`

**Files to modify:**
- `web/workflow-builder/src/api.js`
- `web/workflow-builder/src/mockData.js`
- `web/workflow-builder/src/App.jsx`
- `web/workflow-builder/src/components/WorkflowToolbar.jsx`

**7a: Mock API**

1. Add to `mockData.js`:
   ```javascript
   export const MOCK_PROVIDERS = [
     { name: "opencode", api_base: "https://opencode.ai/zen/v1",
       api_key_configured: true, default_model: "claude-sonnet-4-20250514" },
     { name: "openai", api_base: "https://api.openai.com/v1",
       api_key_configured: false, default_model: "gpt-4o" },
     { name: "local", api_base: "http://localhost:11434/v1",
       api_key_configured: false, default_model: "llama3" },
   ];
   ```

2. Add to `api.js`:
   ```javascript
   export function listProviders() {
     if (isMockMode()) return Promise.resolve({ providers: MOCK_PROVIDERS.slice() });
     return apiFetch("/providers").then(r => r.json());
   }
   export async function addProvider(config) { ... }
   export async function updateProvider(name, config) { ... }
   export async function deleteProvider(name) { ... }
   export async function setDefaultProvider(name) { ... }
   ```

**7b: ProviderSelector component**

Reusable dropdown for node config panels:
- Fetches providers on mount via `listProviders()`
- Dropdown: "Use default" + each provider as `provider-name / model-name`
- Optional model text input below dropdown
- `onChange(provider, model)` callback
- States: loading spinner, empty state, error retry

**7c: ProviderManager component**

Full provider management panel:
- Provider list (card-style)
- Each card: name (bold), base URL, model, API key status icon
  - Green checkmark + "Key set" if `api_key_configured: true`
  - Red warning + "Key missing" if `api_key_configured: false`
- Action buttons per card: "Make Default" (if not first), "Edit", "Delete"
- "Add Provider" button at top
- Add/Edit modal form:
  - Name (required, text), Base URL (required, URL), API Key Env Var (optional, text), Default Model (required, text)
  - "The API key value is read from the environment variable, not stored here"
- Delete confirmation dialog
- States: loading, empty, error, normal, submitting

**7d: Integration**

- `App.jsx`: Add `providerPanel` state (boolean), toggling `ProviderManager` in right panel area alongside ConfigPanel/ExecutionPanel/ScheduleManager
- `WorkflowToolbar.jsx`: Add "Providers" button with active state (same pattern as Schedules)
- ProviderManager styling in `provider-manager.css`

4. Run frontend in mock mode — verify all states render correctly.

5. **Commit:**
```
git add web/workflow-builder/src/api.js
git add web/workflow-builder/src/mockData.js
git add web/workflow-builder/src/components/ProviderManager.jsx
git add web/workflow-builder/src/components/ProviderSelector.jsx
git add web/workflow-builder/src/styles/provider-manager.css
git add web/workflow-builder/src/App.jsx
git add web/workflow-builder/src/components/WorkflowToolbar.jsx
git commit -m "feat(ui): provider management UI — ProviderManager, ProviderSelector, mock API

- ProviderManager: list, add, edit, delete providers with API key status
- ProviderSelector: per-node provider dropdown for node config panels
- Mock mode with 3 default providers (opencode, openai, local)
- 'Providers' button in toolbar, panel integrated into right panel
- ~450 lines (JSX + CSS + API + mock data)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Integration tests + final verification

**Files to create:**
- `tests/test_workflow_engine/test_providers_integration.py`

1. Write end-to-end integration tests:
   - `test_full_pipeline` — create provider via store → execute workflow with AI node → verify LLM called
   - `test_workflow_with_mixed_providers` — multiple nodes, each with different provider configs
   - `test_workflow_fallback_to_fake` — no providers → workflow completes with fake data
   - `test_streaming_through_execution` — LLM tokens flow through emit_stream
   - `test_node_error_propagation` — provider fails → node error → execution continues per policy

2. Run **all** tests — verify no regressions:
   ```bash
   python -m pytest -q
   ```

3. Bump version in `src/decision_system/__init__.py`:
   ```python
   __version__ = "1.12.0"
   ```

4. Update `CHANGELOG.md`:
   ```markdown
   ## v1.12.0 (2026-06-13)
   ### Added
   - Provider configuration system (.decision_system/providers.json)
   - LLMClient: unified OpenAI-compatible HTTP caller with streaming
   - Real LLM calls in TechAnalyst, RiskAnalyst, ExtractClaims, VerifyClaims, WriteReport nodes
   - Provider resolution: node override → system default → fake fallback
   - Provider CRUD API routes
   - Provider CLI commands (list, add, remove, set-default, check)
   - ProviderManager UI component (frontend)
   - ProviderSelector per-node dropdown (frontend)
   - Mock providers for frontend development
   - N~ new tests (total running: N+916)
   ```
   (Fill in N after counting)

5. **Commit:**
```
git add tests/test_workflow_engine/test_providers_integration.py
git add src/decision_system/__init__.py
git add CHANGELOG.md
git commit -m "release: v1.12.0 — Phase 5 real LLM provider integration

- 8 tasks completed
- N new tests (total: M)
- Full provider lifecycle: config → resolution → LLM call → streaming → UI

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: Self-review and final verification

- [ ] Run `python -m pytest -q` — all tests pass (916 existing + new)
- [ ] Run `decision-system workflow providers list` — shows opencode default
- [ ] Run with `DECISION_PROVIDER=fake` (no providers.json) — AI nodes return fake data
- [ ] Verify frontend renders in mock mode
- [ ] Verify provider config file is auto-created on first access
- [ ] Check no API keys are stored in config files
- [ ] Check all 5 AI nodes handle both fake and real paths
- [ ] Review CHANGELOG entry is complete
- [ ] Verify no `.decision_system/` artifacts committed
- [ ] Run `decision-system check-hygiene` if available
