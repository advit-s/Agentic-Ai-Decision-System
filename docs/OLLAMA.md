# Ollama Provider

## What It Does

The Ollama provider lets the decision workflow test a local model through
Ollama's local HTTP API. It is optional and only runs when explicitly selected.
The fake provider remains the default for offline development and tests.

The provider asks Ollama for strict JSON and validates responses into Pydantic
models:

- `AgentMemo`
- `Claim`

The local retriever, claim ledger, verifier, and report renderer remain in
control. Ollama does not own final report generation.

## Configure `.env`

Copy `.env.example` to `.env` and set:

```env
DECISION_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
OLLAMA_TEMPERATURE=0
OLLAMA_MAX_TOKENS=2048
OLLAMA_TIMEOUT_SECONDS=60
```

Use a model you have pulled locally. Do not commit `.env`.

## Local Setup

Install and start Ollama from the official Ollama app or CLI, then pull a
model:

```bash
ollama pull llama3.1:8b
ollama serve
```

The provider calls only the configured local `OLLAMA_BASE_URL`, normally
`http://localhost:11434`. It does not require external internet during a run
once the model is already pulled.

## Smoke Tests

Fake provider smoke test:

```bash
decision-system provider-smoke --provider fake
decision-system eval-provider --provider fake
```

Ollama smoke test, only after Ollama is running and `OLLAMA_MODEL` is set:

```bash
decision-system provider-health
decision-system provider-smoke --provider ollama
decision-system eval-provider --provider ollama
decision-system ask "Should we migrate billing?" --provider ollama
```

If `OLLAMA_MODEL` is missing, provider eval skips gracefully. If Ollama is not
running, provider smoke and ask fail with a clear local connection message.

## Limitations

- Tests use mocked client/HTTP responses only.
- Model quality is not guaranteed.
- JSON output can still be malformed; malformed responses fail safely.
- No tool calling, database access, frontend, connectors, or war-room
  integration is added in v0.7.
