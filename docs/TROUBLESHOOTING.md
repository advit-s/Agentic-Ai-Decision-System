# Troubleshooting

## `ModuleNotFoundError`

Make sure the virtual environment is active and install the package in editable mode:

```bash
python -m pip install -e ".[dev]"
```

Run commands from the repo root.

## No Documents Indexed

Check that `company_docs/` contains `.md` or `.txt` files:

```bash
decision-system index
decision-system inspect-index
```

The repo includes `company_docs/demo_billing.md` for smoke tests.

## Missing `.env`

The fake provider does not need `.env`. NVIDIA NIM does. Copy `.env.example` to `.env` and run from the repo root.

## Missing NVIDIA Key

If you see `NVIDIA_API_KEY is required`, set your own key:

```env
NVIDIA_API_KEY=your_key_here
```

Never commit `.env`.

## Invalid Model Name

Use the exact model ID from NVIDIA Build:

```env
NVIDIA_NIM_MODEL=deepseek-ai/deepseek-v4-flash
```

If the endpoint rejects the model, confirm the model is available for your account.

## Chroma Deprecation Warning

Chroma may emit dependency deprecation warnings during tests. If tests pass, the warning is usually safe to ignore for local development.

## Windows Path Issues

This repo may live in a path with spaces, such as OneDrive Desktop folders. Run commands from the repo root and quote paths when needed.

## JSON Parsing Failure From Real Model Output

The NVIDIA provider expects strict JSON. If a real model returns Markdown, prose, or truncated JSON:

- lower prompt complexity
- increase `NVIDIA_MAX_TOKENS`
- keep `NVIDIA_TEMPERATURE=0`
- try a model with stronger structured-output behavior
- rerun with the fake provider to confirm the local workflow still works

## Wrong Provider

Check `.env`:

```env
DECISION_PROVIDER=fake
```

You can override one run:

```bash
decision-system ask "Should we migrate billing?" --provider fake
```
