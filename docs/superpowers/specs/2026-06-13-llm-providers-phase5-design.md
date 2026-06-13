# Phase 5: Real LLM Provider Integration — Design Spec

> **Status:** Draft for review  
> **Version:** 1.0  
> **Date:** 2026-06-13  
> **Applies to:** Agentic Decision System v1.12.0

---

## 1. Goal

Transform the workflow builder from a system that looks like n8n to one that *works* like n8n — where the AI/Analysis nodes (TechAnalyst, RiskAnalyst, ExtractClaims, VerifyClaims, WriteReport) actually call real LLM providers instead of returning fake data. The system follows a **"one unified API, fake by default"** principle: a single OpenAI-compatible `/chat/completions` provider type covers every backend from OpenAI to OpenRouter to Ollama, and workflows work without any API key configured (falling back to the fake provider).

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                   AI/Workflow Nodes                  │
│  TechAnalyst │ RiskAnalyst │ Extract │ Verify │ Write │
└──────────────────────┬──────────────────────────────┘
                       │  picks provider + model
┌──────────────────────▼──────────────────────────────┐
│            Provider Resolution Layer                 │
│  - Resolves "name/model" to real API endpoint        │
│  - Handles auth, rate limiting, retry               │
│  - Streams tokens back through execution context    │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│         Provider Configuration Store                 │
│  ┌────────────────┐  ┌────────────────┐             │
│  │ "opencode"     │  │ "openai"       │             │
│  │ (default — 1st)│  │ key: OPENAI_KEY│             │
│  │ key: OPENCODE  │  │ model: gpt-4o  │             │
│  │ model: claude  │  │                │             │
│  └────────────────┘  └────────────────┘             │
│  ┌────────────────┐  ┌────────────────┐             │
│  │ "openrouter"   │  │ "local"        │             │
│  │ key: OR_KEY    │  │ key: none      │             │
│  │ model: sonnet  │  │ model: llama3  │             │
│  └────────────────┘  └────────────────┘             │
└─────────────────────────────────────────────────────┘
```

### 2.1 Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Provider type | Single `openai_compat` | Any provider with an OpenAI-compatible `/chat/completions` endpoint works — OpenAI, OpenRouter, opencode, NVIDIA NIM, Groq, Cerebras, Gemini, Ollama, etc. |
| Default provider | First in the list | No `is_default` flag needed. First entry is the system default. opencode is first in the default config. |
| API keys | Environment variables | Keys never stored in the config file. Only env var names (`OPENCODE_API_KEY`, `OPENAI_API_KEY`, etc.) are recorded in `providers.json`. |
| Fallback | Fake provider | If no real provider is configured, or if API keys are missing, AI nodes return fake/placeholder data. Every test works without API keys. |
| Transport | OpenAI Chat Completions format | `/chat/completions` with `stream: true`. System prompt → `system` role, input data → `user` role. |
| Streaming | Via existing ExecutionEvent / WebSocket | Each LLM token is emitted as an `ExecutionEvent(type="node_output")` and streamed to the frontend through the existing WebSocket. |

### 2.2 Provider Resolution Order

1. **Per-node override** — if the node's `config.provider` is set, use that provider. If `config.model` is set, use that model (otherwise use the provider's `default_model`).
2. **System default** — the first provider in the list. Use its `default_model`.
3. **Fake provider** — no real provider configured. Returns deterministic stub data. Never fails.

---

## 3. Provider Configuration

### 3.1 Config File

Stored at `.decision_system/providers.json` — created automatically if it doesn't exist.

```json
{
  "providers": [
    {
      "name": "opencode",
      "api_base": "https://opencode.ai/zen/v1",
      "api_key_env": "OPENCODE_API_KEY",
      "default_model": "claude-sonnet-4-20250514"
    },
    {
      "name": "openai",
      "api_base": "https://api.openai.com/v1",
      "api_key_env": "OPENAI_API_KEY",
      "default_model": "gpt-4o"
    },
    {
      "name": "openrouter",
      "api_base": "https://openrouter.ai/api/v1",
      "api_key_env": "OPENROUTER_API_KEY",
      "default_model": "anthropic/claude-sonnet-4-20250514"
    },
    {
      "name": "local",
      "api_base": "http://localhost:11434/v1",
      "api_key_env": null,
      "default_model": "llama3"
    }
  ]
}
```

### 3.2 Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Unique identifier. Used in node configs and UI dropdowns. Alphanumeric + hyphens only. |
| `api_base` | string | yes | Base URL of the OpenAI-compatible API. Must point to the root of the API (e.g., `https://api.openai.com/v1`, not `/v1/chat/completions`). |
| `api_key_env` | string\|null | no | Name of the environment variable holding the API key. `null` for local providers that don't need auth. |
| `default_model` | string | yes | The model to use when no per-node model override is set. |

### 3.3 Default Config

When first created (no `providers.json` exists), the system auto-creates a config with a single entry:

```json
{
  "providers": [
    {
      "name": "opencode",
      "api_base": "https://opencode.ai/zen/v1",
      "api_key_env": "OPENCODE_API_KEY",
      "default_model": "claude-sonnet-4-20250514"
    }
  ]
}
```

This makes opencode the first/default provider out of the box.

---

## 4. Backend Components

### 4.1 Provider Store (`src/decision_system/workflow_engine/providers/store.py`)

Reads and writes `.decision_system/providers.json`. Core model:

```python
class ProviderConfig(BaseModel):
    name: str
    api_base: str
    api_key_env: str | None = None
    default_model: str

class ProviderStore:
    def __init__(self, path: Path = Path(".decision_system/providers.json")):
        self._path = path

    def load(self) -> list[ProviderConfig]:
        """Load providers. Creates default if file doesn't exist."""

    def save(self, providers: list[ProviderConfig]) -> None:
        """Overwrite the full provider list."""

    def get_default(self) -> ProviderConfig | None:
        """First provider in the list, or None if list is empty."""

    def get(self, name: str) -> ProviderConfig | None:
        """Look up provider by name."""

    def add(self, provider: ProviderConfig) -> None:
        """Append a new provider. Raises on duplicate name."""

    def remove(self, name: str) -> None:
        """Remove provider by name. Raises if not found."""

    def set_default(self, name: str) -> None:
        """Reorder provider to the first position."""
```

### 4.2 LLM Client (`src/decision_system/workflow_engine/providers/client.py`)

Makes actual HTTP calls to OpenAI-compatible APIs:

```python
class LLMClient:
    def __init__(self, config: ProviderConfig):
        self.api_base = config.api_base.rstrip("/")
        self.model = config.default_model
        self.api_key = os.getenv(config.api_key_env) if config.api_key_env else None

    async def chat_completion(
        self,
        messages: list[dict],
        model: str | None = None,
        stream: bool = True,
        on_token: Callable[[str], Awaitable[None]] | None = None,
    ) -> str:
        """
        POST /chat/completions with streaming.
        Yields tokens to on_token callback.
        Returns full accumulated response text.
        Throws ProviderError on failure.
        """
```

**Error handling:**

| Exception | HTTP Status | Frontend Display |
|-----------|-------------|------------------|
| `AuthenticationError` | 401 | "Invalid API key for provider X" |
| `RateLimitError` | 429 | "Rate limited by provider X — retrying..." |
| `TimeoutError` | — | "Provider X timed out after 30s" |
| `ModelNotFoundError` | 404 | "Model Y not found on provider X" |
| `ProviderError` | 500 | "Provider X returned an error: ..." |

### 4.3 AI Node Integration

Each of the 5 AI nodes is updated to use the provider system. The node config gains optional fields:

```json
{
  "id": "analyst1",
  "type": "decision_system.tech_analyst",
  "config": {
    "provider": "opencode",
    "model": "claude-sonnet-4-20250514"
  }
}
```

- **If `provider` is omitted:** resolve to system default → fake
- **If `model` is omitted:** use the provider's `default_model`

**Execution pattern** (applied to all 5 AI nodes):

```python
async def execute(self, context: ExecutionContext, input_data: dict) -> dict:
    # 1. Build prompts
    system_prompt = self._build_system_prompt(input_data)
    user_prompt = self._build_user_prompt(input_data)

    # 2. Resolve provider
    provider_cfg = context.resolve_provider(
        self.config.get("provider"),
        self.config.get("model")
    )

    # 3. No real provider → use fake
    if provider_cfg is None:
        return self._fake_response(input_data)

    # 4. Call LLM with streaming
    client = LLMClient(provider_cfg)
    result = await client.chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        model=self.config.get("model"),
        stream=True,
        on_token=lambda token: context.emit_stream(token),
    )

    # 5. Parse and return
    return self._parse_result(result)
```

### 4.4 Streaming

- Each LLM token is emitted as `ExecutionEvent(type="node_output", data={"token": "..."})`
- The existing WebSocket (`WS /executions/{id}/stream`) already streams execution events
- The frontend's execution panel accumulates tokens and displays them in the output tab
- The full accumulated text is returned as the node's output for downstream nodes

### 4.5 API Routes

Mounted under `/api/providers` in the existing FastAPI router:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/providers` | List all providers (no API key values exposed) |
| `POST` | `/api/providers` | Add a new provider |
| `PUT` | `/api/providers/{name}` | Update an existing provider |
| `DELETE` | `/api/providers/{name}` | Remove a provider |
| `PUT` | `/api/providers/{name}/set-default` | Move provider to first position |

**GET response format:**

```json
{
  "providers": [
    {
      "name": "opencode",
      "api_base": "https://opencode.ai/zen/v1",
      "api_key_configured": true,
      "default_model": "claude-sonnet-4-20250514"
    }
  ]
}
```

Note: `api_key_env` is never returned to the frontend. Only a boolean `api_key_configured` indicates whether the env var is set.

### 4.6 CLI Commands

Added to `decision-system workflow`:

```
decision-system providers list                      — list configured providers
decision-system providers list --verbose             — show API base URLs
decision-system providers add                        — interactive add
decision-system providers add --name openai
    --api-base https://api.openai.com/v1
    --api-key-env OPENAI_API_KEY
    --default-model gpt-4o                           — non-interactive add
decision-system providers remove <name>              — remove by name
decision-system providers set-default <name>          — reorder to first
decision-system providers check                      — show which providers have valid API keys
```

---

## 5. Frontend Changes

### 5.1 ProviderManager Component

A new settings panel for managing providers:

- **Provider list:** Cards showing name, base URL, default model, and API key status (green checkmark / red warning)
- **Add Provider:** Form with fields: name, base URL, API key env var, default model
- **Set Default:** "Make Default" button on each card — reorders to first position
- **Delete:** With confirmation dialog
- **Keyboard:** Enter to submit forms, Escape to close

**States:**
- **Loading:** Skeleton cards while providers load
- **Empty:** "No providers configured. Add one to start using real AI." with an Add button
- **Error:** Red banner if the backend call fails, with retry button
- **Normal:** Scrollable card list
- **Adding/Editing:** Modal form overlay

### 5.2 ProviderSelector Component

The per-node provider dropdown (already stubbed in Phase 3):

- Dropdown populated from `GET /api/providers`
- Each item shows: `provider-name / model-name`
- "Use default" option at the top
- Model input (text or dropdown) to override per-node

### 5.3 Mock Data

Mock providers for frontend development without the backend:

```javascript
// mockData.js
export const MOCK_PROVIDERS = [
  { name: "opencode", api_base: "https://opencode.ai/zen/v1",
    api_key_configured: true, default_model: "claude-sonnet-4-20250514" },
  { name: "openai", api_base: "https://api.openai.com/v1",
    api_key_configured: false, default_model: "gpt-4o" },
  { name: "local", api_base: "http://localhost:11434/v1",
    api_key_configured: false, default_model: "llama3" },
];
```

### 5.4 API Client Functions

Added to `api.js` following the same `isMockMode()` pattern:

```javascript
export function listProviders() { /* mock → apiFetch */ }
export function addProvider(config) { /* mock → apiFetch */ }
export function updateProvider(name, config) { /* mock → apiFetch */ }
export function deleteProvider(name) { /* mock → apiFetch */ }
export function setDefaultProvider(name) { /* mock → apiFetch */ }
```

### 5.5 Integration Points

- **WorkflowToolbar:** New "Providers" button (active state like Schedules)
- **App.jsx:** `providerPanel` state, toggles ProviderManager in the right panel
- **Right panel:** ProviderManager replaces ConfigPanel/ExecutionPanel/ScheduleManager when active

---

## 6. AI Node Details

### 6.1 TechAnalyst

| Aspect | Detail |
|--------|--------|
| System prompt | "You are a senior technical analyst examining company data. Analyze the provided documents and identify technical patterns, architecture issues, and implementation concerns." |
| Input structure | Retrieved documents and context |
| Output structure | List of technical findings with evidence citations |
| Parser | Extract technical findings JSON array |

### 6.2 RiskAnalyst

| Aspect | Detail |
|--------|--------|
| System prompt | "You are a risk analyst evaluating business risks. Analyze the provided context and identify potential risks, their severity, and mitigations." |
| Input structure | TechnicalAnalyst output + documents |
| Output structure | List of risk items with severity ratings |
| Parser | Extract risk items JSON array |

### 6.3 ExtractClaims

| Aspect | Detail |
|--------|--------|
| System prompt | "Extract factual claims from the following text. Each claim must be a single, verifiable statement. Output as a JSON array." |
| Input structure | Raw text from documents |
| Output structure | List of claim strings |
| Parser | Extract claims JSON array |

### 6.4 VerifyClaims

| Aspect | Detail |
|--------|--------|
| System prompt | "Given these claims and the supporting evidence, verify each claim. Classify as: supported, unsupported, or contradicted. Provide evidence citations." |
| Input structure | Claims + evidence documents |
| Output structure | Claims with verification status and citations |
| Parser | Extract verification results JSON array |

### 6.5 WriteReport

| Aspect | Detail |
|--------|--------|
| System prompt | "Write a structured decision report based on the following findings, risks, and verified claims. Include an executive summary, analysis, and recommendations." |
| Input structure | Full workflow state (findings, risks, claims, verdicts) |
| Output structure | Markdown report string |
| Parser | Return raw markdown text |

---

## 7. Testing Strategy

| Layer | What's tested | External deps? |
|-------|--------------|----------------|
| **ProviderStore** | CRUD, defaults, first-is-default, persistence, missing file, auto-create default | None |
| **LLMClient** | Request format, headers, streaming, error mapping, timeout | HTTPX mock |
| **Provider resolution** | Node override → system default → fake, missing provider fallback, model override | None |
| **AI node parsing** | Each node correctly parses mock LLM output (JSON extraction, markdown) | None |
| **Full execution** | End-to-end workflow execution with mocked provider returns correct structured output | HTTPX mock |
| **API routes** | CRUD endpoints, validation, error codes, set-default reordering | None |
| **CLI commands** | list, add, remove, set-default, check, error messages | None |
| **Frontend** | ProviderManager renders, CRUD calls work, mock mode | None |

**Key principle:** Every test works with **no API key.** The fake provider is the default. HTTP calls are mocked at the httpx layer for LLMClient tests.

---

## 8. File Manifest

### New Files

| Path | Purpose |
|------|---------|
| `src/decision_system/workflow_engine/providers/__init__.py` | Package exports |
| `src/decision_system/workflow_engine/providers/store.py` | ProviderConfig model + ProviderStore CRUD |
| `src/decision_system/workflow_engine/providers/client.py` | LLMClient — OpenAI-compatible HTTP caller |
| `src/decision_system/workflow_engine/providers/exceptions.py` | ProviderError hierarchy |
| `src/decision_system/workflow_engine/api_providers.py` | FastAPI provider CRUD routes |
| `web/workflow-builder/src/components/ProviderManager.jsx` | Provider list + CRUD UI |
| `web/workflow-builder/src/styles/provider-manager.css` | Styling for provider UI |
| `web/workflow-builder/src/components/ProviderSelector.jsx` | Per-node provider dropdown |
| `tests/test_workflow_engine/test_providers/test_store.py` | ProviderStore tests |
| `tests/test_workflow_engine/test_providers/test_client.py` | LLMClient tests |
| `tests/test_workflow_engine/test_providers/__init__.py` | Package init |
| `tests/test_workflow_engine/test_api_providers.py` | Provider API route tests |
| `tests/test_workflow_engine/test_providers_integration.py` | End-to-end provider integration |

### Modified Files

| Path | Change |
|------|--------|
| `src/decision_system/workflow_engine/api.py` | Mount provider routes, expose resolve_provider in context |
| `src/decision_system/workflow_engine/engine/executor.py` | Wire provider store into ExecutionContext |
| `src/decision_system/workflow_engine/engine/context.py` | Add resolve_provider() helper, provider_store reference |
| `src/decision_system/workflow_engine/nodes/__init__.py` | Update node registry exports |
| `src/decision_system/workflow_engine/nodes/analysis_nodes.py` | Add _call_llm() to 5 AI nodes |
| `src/decision_system/workflow_engine/cli.py` | Add provider CLI sub-commands |
| `src/decision_system/cli.py` | Wire provider CLI group |
| `web/workflow-builder/src/App.jsx` | Integrate ProviderManager panel, provider state |
| `web/workflow-builder/src/components/WorkflowToolbar.jsx` | Add Providers button |
| `web/workflow-builder/src/api.js` | Add provider CRUD functions |
| `web/workflow-builder/src/mockData.js` | Add mock providers |
| `src/decision_system/__init__.py` | Bump to v1.12.0 |
| `CHANGELOG.md` | Add v1.12.0 release notes |

---

## 9. Dependency Changes

- **`pyproject.toml`:** Move `openai>=1.0,<2.0` from `[project.optional-dependencies] nvidia` to core `dependencies`. It's no longer optional — it's the unified API client for all providers.
- **No new external dependencies.** OpenAI SDK is already in the project as an optional dep. HTTPX is already a transitive dep via FastAPI.
- **Dev dependencies:** Add `pytest-httpx>=0.30,<1.0` for HTTP mocking. (Or use `httpx`'s built-in `Transport` mock.)

---

## 10. Error Scenarios & Edge Cases

| Scenario | Handling |
|----------|----------|
| No `.decision_system/providers.json` | Auto-create with opencode as default |
| Provider name already exists | Return 409 Conflict on API, error message on CLI |
| Provider not found | Return 404 on API, error message on CLI |
| API key env var not set | `api_key_configured: false` in GET response. Node execution fails with authentication error. |
| LLM client timeout (30s) | Raise TimeoutError, node fails with timeout status |
| LLM returns non-JSON when JSON expected | Return raw text wrapped in `{ "raw_output": "..." }` — node continues without crashing |
| Rate limited | 3 retries with exponential backoff (2s, 4s, 8s), then fail |
| Provider returns 500 | Map to ProviderError, node fails |
| Stream drops mid-response | Return partial accumulated text, node shows `partial_output: true` |
| Empty provider list | resolve_provider returns None → all AI nodes use fake provider |
| Workflow with mixed providers | Each node has its own provider config — no cross-contamination |
| Invalid model name for provider | Provider returns 404, node fails with model_not_found error |
| Switching provider config mid-execution | Provider config is read at node execution time — changes take effect immediately |

---

## 11. Future Considerations (Out of Scope)

These are explicitly NOT part of Phase 5 but are documented for future phases:

- **Anthropic Messages transport** — If an Anthropic-native transport is needed later, it can be added as a second `type` without changing the config format.
- **Cost tracking dashboard** — Per-node token counts can be recorded but a visual dashboard is Phase 6+.
- **Provider health monitoring** — Periodic provider health checks and auto-failover is Phase 6+.
- **Multi-user provider config** — Currently a single global config. Per-user or per-workspace providers would need the database migration (planned for later).
- **Function/tool calling** — The `/chat/completions` endpoint supports tools, but tool use in nodes is Phase 6+.
- **Embedding providers** — Provider config is for chat completions only. Embedding providers (for retrieval) are a separate concern.
- **Plugin system for custom provider types** — Adding a new provider type currently requires code. A plugin-based provider system is Phase 6+.

---

## 12. Verification Checklist

- [ ] All 916 existing tests still pass with no API key configured
- [ ] New provider store tests cover: create default, CRUD, persistence, first-is-default
- [ ] New LLM client tests cover: request format, streaming, error handling, timeout
- [ ] New provider resolution tests cover: node override, system default, fake fallback
- [ ] New API route tests cover: CRUD, validation, set-default, error codes
- [ ] New CLI tests cover: list, add, remove, set-default, check
- [ ] AI nodes fall back to fake provider when no real provider is configured
- [ ] AI nodes stream tokens through WebSocket during real provider execution
- [ ] Frontend ProviderManager renders all states (loading, empty, list, error)
- [ ] Frontend ProviderSelector shows providers from backend and falls back to mock
- [ ] Mock mode works without backend running
- [ ] `CHANGELOG.md` and version bumped
