# Local-First Setup — Provider Runtime & AI-Assisted Evidence Synthesis

## Overview

v1.21 adds a local provider runtime that enables AI-assisted evidence synthesis
without requiring cloud API keys. You can use:

- **Fake provider** — built-in, deterministic, no network needed (default for dev/tests)
- **Ollama** — local LLM server (recommended for offline use)
- **OpenAI-compatible endpoint** — LM Studio, vLLM, LocalAI, etc.
- **OpenAI / Anthropic** — cloud providers (requires API key)

## Quick start (no API key needed)

```bash
# The fake provider is pre-configured for development.
# No setup required — all tests and demo workflows use it by default.

# Verify it works:
decision-system index
decision-system ask "What are the key risks?"
```

## Ollama setup

1. Install Ollama from https://ollama.com
2. Pull a model:
   ```bash
   ollama pull llama3.2
   ```
3. Ensure Ollama is running:
   ```bash
   curl http://localhost:11434/api/tags
   ```
4. Add a provider via the UI or API:
   ```bash
   curl -X POST http://localhost:8000/providers \
     -H "Content-Type: application/json" \
     -d '{"name": "Local Ollama", "provider_type": "ollama", "base_url": "http://localhost:11434"}'
   ```
5. Test the connection:
   ```bash
   curl http://localhost:8000/providers/<provider_id>/test
   ```
6. Set as default:
   ```bash
   curl -X POST http://localhost:8000/providers/default?provider_id=<provider_id>
   ```

## OpenAI-compatible local endpoint setup

Supports any server that provides an OpenAI-compatible API:

- LM Studio: http://localhost:1234/v1
- vLLM: http://localhost:8000/v1
- LocalAI: http://localhost:8080/v1
- Ollama (OpenAI-compatible mode): http://localhost:11434/v1

```bash
curl -X POST http://localhost:8000/providers \
  -H "Content-Type: application/json" \
  -d '{"name": "LM Studio", "provider_type": "openai_compatible", "base_url": "http://localhost:1234/v1"}'
```

## Cloud provider setup

Cloud providers require an API key supplied via environment variable:

```bash
export OPENAI_API_KEY="sk-..."
```

Then configure:

```bash
curl -X POST http://localhost:8000/providers \
  -H "Content-Type: application/json" \
  -d '{"name": "OpenAI", "provider_type": "openai", "api_key_env": "OPENAI_API_KEY"}'
```

## Security and privacy

- **Local data stays local** unless you explicitly configure a cloud provider.
- **Ollama/local endpoints** run on your machine or local network.
- **Cloud providers** send selected evidence and prompts to the provider.
- **API keys** should be supplied by environment variables, never stored in
  config files or committed to version control.
- Do **not** use cloud providers with sensitive data unless you understand the risk.

## Provider statuses

| Status | Meaning |
|--------|---------|
| `configured` | Provider is saved but not yet tested |
| `healthy` | Provider is reachable and responsive |
| `offline` | Provider endpoint is unreachable |
| `missing_config` | Required API key is not set |
| `error` | Provider returned an error |

## Running the AI-assisted demo workflow

```bash
# This requires a configured provider (fake works without network)
decision-system serve-api

# Then in the UI (http://localhost:3000):
# 1. Create a workspace
# 2. Upload documents
# 3. Configure a provider
# 4. Load the "AI-Assisted Evidence Synthesis" workflow
# 5. Run it
```

## How evidence synthesis works

1. Evidence is retrieved from the workspace (vector or keyword search)
2. Evidence is formatted and sent to the configured provider with a prompt template
3. Provider generates structured output (summary, claims, risks, etc.)
4. Output is parsed by the structured output parser
5. Draft claims are saved as `pending` (not trusted)
6. If auto-verify is enabled, claims are verified against workspace evidence
7. Only verified claims appear in trust reports

## Important honesty text

> AI-assisted synthesis can help draft summaries and claims, but generated content
> is not automatically trusted. Claims must be verified against local workspace
> evidence, and unsupported or contradicted claims remain visible.
