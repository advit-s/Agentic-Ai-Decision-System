# Getting Started

This guide gets you from a fresh clone to a working local run.

## 1. Install

Windows:

```bash
git clone <repo-url>
cd <repo-name>
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
```

macOS/Linux:

```bash
git clone <repo-url>
cd <repo-name>
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## 2. Run Tests

```bash
python -m pytest -q
```

The tests use the fake provider and do not require an API key.

## 3. Add Demo Docs

The repo includes `company_docs/demo_billing.md`. You can add more local `.md` or `.txt` files to `company_docs/`, but do not commit private company documents.

## 4. Run With Fake Provider

```bash
decision-system index
decision-system inspect-index
decision-system ask "Should we migrate billing?"
decision-system ask "Should we migrate billing?" --show-evidence
decision-system eval
```

The fake provider is deterministic and works offline.

## 5. Run With NVIDIA NIM

Copy the example environment file:

```bash
copy .env.example .env
```

On macOS/Linux:

```bash
cp .env.example .env
```

Edit `.env`:

```env
DECISION_PROVIDER=nvidia_nim
NVIDIA_API_KEY=your_key_here
NVIDIA_NIM_MODEL=deepseek-ai/deepseek-v4-flash
```

Run:

```bash
decision-system ask "Should we migrate billing?" --provider nvidia_nim
```

Never commit `.env` or real API keys.

## 6. If Something Breaks

- Re-run from the repo root.
- Confirm your virtual environment is active.
- Run `python -m pip install -e ".[dev]"` again.
- Use `decision-system inspect-index` to confirm documents were indexed.
- Use the fake provider first before trying NVIDIA NIM.
- See `docs/TROUBLESHOOTING.md`.
