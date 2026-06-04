# NVIDIA NIM Provider

## What It Does

The NVIDIA NIM provider lets the workflow call a hosted model through LangChain's `ChatNVIDIA` integration. It is optional. The fake provider remains the default for tests and offline development.

The provider asks for strict JSON and validates model output into Pydantic models:

- `AgentMemo`
- `Claim`

The local verifier and report writer still control claim verification and final report generation.

## Configure `.env`

Copy `.env.example` to `.env` and set your own key:

```env
DECISION_PROVIDER=nvidia_nim
NVIDIA_API_KEY=your_key_here
NVIDIA_NIM_MODEL=deepseek-ai/deepseek-v4-flash
NVIDIA_TEMPERATURE=0
NVIDIA_TOP_P=0.95
NVIDIA_MAX_TOKENS=4096
NVIDIA_REASONING_ENABLED=false
NVIDIA_REASONING_EFFORT=medium
```

Never commit `.env` or real API keys.

## Model Name Config

Use the exact model ID shown in NVIDIA Build. Put that value in `NVIDIA_NIM_MODEL`.

## Reasoning Config

Set `NVIDIA_REASONING_ENABLED=true` only for models and endpoints that support reasoning options. `NVIDIA_REASONING_EFFORT` defaults to `medium`.

## Max Token Config

`NVIDIA_MAX_TOKENS` limits provider output. If JSON responses are truncated, increase it. If responses are slow or expensive, lower it.

## Smoke Test

Index demo docs with the fake provider first:

```bash
decision-system index
decision-system ask "Should we migrate billing?"
```

Then run one NVIDIA-backed question:

```bash
decision-system ask "Should we migrate billing?" --provider nvidia_nim --show-evidence
```

Do not save or commit real provider output if it contains private information.

## Default Provider

`DECISION_PROVIDER=fake` is the safe default. It keeps tests and evals offline.
