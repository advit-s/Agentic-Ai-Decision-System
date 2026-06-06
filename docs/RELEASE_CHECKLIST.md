# Release Checklist

Use this checklist before cutting any milestone release (vX.Y.Z).

## Install

- [ ] `python -m venv .venv && .venv\Scripts\activate` (Windows)
- [ ] `python -m venv .venv && source .venv/bin/activate` (macOS/Linux)
- [ ] `python -m pip install -e ".[dev]"`
- [ ] No dependency resolution errors.

## Tests

- [ ] `python -m pytest -q` - all tests pass, exit code 0.
- [ ] No warnings about missing API keys or excluded skips.

## Smoke Commands

Run these offline with no API key configured:

- [ ] `decision-system index`
- [ ] `decision-system inspect-index`
- [ ] `decision-system ask "Should we migrate billing?"`
- [ ] `decision-system extract-graph`
- [ ] `decision-system inspect-graph`

## Evaluation

- [ ] `decision-system eval`
- [ ] `decision-system eval-war-room`
- [ ] `decision-system eval-providers`
- [ ] `decision-system eval --json` (formatted output)
- [ ] `decision-system eval-war-room --json` (formatted output)
- [ ] `decision-system eval-providers --json` (formatted output)
- [ ] All eval cases pass.

## Repo Hygiene

- [ ] `git status --short` - working tree is clean (no accidental changes).
- [ ] `.env` is not tracked by Git (should NOT appear in `git ls-files`).
- [ ] `.decision_system/` is not tracked by Git.
- [ ] `__pycache__/` and `*.pyc` are not tracked by Git.
- [ ] `.pytest_cache/` is not tracked by Git.
- [ ] `evals/results/*.json` generated files are not tracked by Git.
- [ ] `.decision_system/provider_evals/` provider evaluation results are not tracked by Git.
- [ ] `datasets/` (raw public dataset downloads) is not tracked by Git.
- [ ] `company_data/**/imported_*.csv` files are not tracked by Git.
- [ ] `.decision_system/` directories (graph, profiles, ontology, insights, contexts, evals, provider_evals, orchestration, war_room) are all in `.gitignore`.
- [ ] `decision-system check-hygiene` passes (warnings acceptable, failures require action).
- [ ] `decision-system check-hygiene --json` returns valid structured JSON.

## Configuration Defaults

- [ ] `.env.example` has `DECISION_PROVIDER=fake`.
- [ ] `pyproject.toml` has the `decision-system = "decision_system.cli:app"` entry point.
- [ ] No real API keys or secrets in any committed file (grep for `sk-`, `api_key`, `token`).

## Documentation

- [ ] `README.md` reflects current CLI commands.
- [ ] `CHANGELOG.md` has an entry for the new version.
- [ ] `CLAUDE.md` version history or task list reflects the milestone.
- [ ] Any new CLI commands are documented in README.md.
- [ ] Architecture diagram or section in `docs/ARCHITECTURE.md` is current.

## Git Hygiene

- [ ] All tracked files in `.decision_system/` are removed from the index (use `git rm --cached -r .decision_system/` if needed).
- [ ] All tracked `__pycache__/` files are removed from the index.
- [ ] All tracked `.pyc` files are removed from the index.
- [ ] All tracked `.pytest_cache/` files are removed from the index.
- [ ] `.gitignore` covers all generated paths listed above.
- [ ] No generated demo data (`company_data/**/imported_*`) is in the index.

## Skills Directory Audit

The following skills directories may exist in the repo:

| Directory | Description | Action |
|--- |--- |--- |
| `~/.claude/skills/` or `.claude/skills/` | Claude Code user-level skills (canonical for Claude Code) | Keep; add to `.gitignore` if local |
| `\.agents\skills\` | Possibly stow from an older agent installer | Verify intent; ignore or clean up as needed |
| `\.local-skill-pack\` | Temporary skill pack (canonical for Claude Code) | Verify intent; ignore or clean up as needed |

- [ ] `~/.claude/skills/` (global user scope for Claude Code) is canonical - do not modify under project root.
- [ ] If any skill directories under the project root are duplicates or temporary, document intent in this section.
- [ ] Do not delete skill directories without explicit approval.
