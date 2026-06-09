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
- [ ] `.decision_system/` directories (graph, profiles, ontology, insights, contexts, evals, provider_evals, orchestration, war_room, workspaces) are all in `.gitignore`.
## Connector Integrity (v1.1)

- [ ] `.decision_system/connectors/` is in `.gitignore` and ignored by Git.
- [ ] No connector secrets or OAuth tokens are stored or committed.
- [ ] Connector stubs (GitHub, Jira, Slack, Email) do not perform network calls.
- [ ] `connectors dry-run` works offline with no external I/O.
- [ ] `connectors import` works offline and only writes to generated paths.
- [ ] Connector imports skip protected files (`.env`, keys, cache directories).
- [ ] Connector imports skip unsupported files with a clear reason.
- [ ] Duplicate job saves do not corrupt existing connector job state.
- [ ] Exported zip has no `__pycache__/` or `*.pyc` files.
- [ ] `decision-system connectors list` shows 5 connectors with correct stub flags.

## Security Integration (v1.2)

- [ ] `.decision_system/security/` is in `.gitignore` and ignored by Git.
- [ ] `decision-system scan-secrets` runs offline and returns a finding summary.
- [ ] `decision-system scan-secrets --json` returns structured findings.
- [ ] Secret scanner never prints full secret values (masked preview only).
- [ ] `decision-system redact-preview "..."` returns redacted text and findings without modifying files.
- [ ] `decision-system redact-preview "..." --json` returns structured redaction result.
- [ ] `decision-system audit-log` reads `.decision_system/security/audit/audit_log.jsonl` and handles missing log.
- [ ] `decision-system policy-check` runs all 7 checks and reports OK/WARN/FAIL.
- [ ] `decision-system policy-check --json` returns structured policy result.
- [ ] `decision-system approval request --reason "..."` creates a local approval record.
- [ ] `decision-system approval list` shows pending requests.
- [ ] `decision-system approval inspect <id>` handles missing ID gracefully.
- [ ] `GET /security/policy`, `POST /security/redact-preview`, and `GET /security/audit` return structured responses via TestClient.
- [ ] All security tests pass with synthetic data only (no real API keys).
- [ ] No external service calls in `decision_system/security/` modules.
- [ ] Web UI security section renders policy status, audit summary, and approvals from mock data.

## Observability Integration (v1.3)

- [ ] `.decision_system/observability/` is in `.gitignore` and ignored by Git.
- [ ] `decision-system metrics` lists collected metric names or shows "No metrics collected yet."
- [ ] `decision-system metrics --json` returns structured JSON with count and metric summaries.
- [ ] `decision-system eval-history` shows recent evaluation runs.
- [ ] `decision-system eval-history --json` returns structured eval run data.
- [ ] `decision-system quality-report` generates a report with score and recommendations.
- [ ] `decision-system quality-report --json` returns structured quality report JSON.
- [ ] `decision-system trace-summary` shows recent workflow trace summaries.
- [ ] `decision-system trace-summary --json` returns structured trace data.
- [ ] All observability CLI commands work via both top-level (`decision-system metrics`) and sub-app (`decision-system observability metrics`) paths.
- [ ] 28 observability tests pass offline.
- [ ] Note: The observability module has working tests and CLI plumbing but is NOT populated by the core workflow. This is a known standalone foundation — data recording hooks are not yet wired into `ask`, `run-war-room`, or other workflow commands.

## Docker and Deployment (v1.4)

- [ ] `Dockerfile` exists at repo root and builds successfully: `docker build -t decision-system .`
- [ ] `docker-compose.yml` exists and starts the service: `docker compose up` (exit cleanly with Ctrl+C).
- [ ] `.dockerignore` excludes `.venv`, `__pycache__`, `.decision_system/`, `.env`, `datasets/`.
- [ ] `scripts/dev.sh` and `scripts/dev.ps1` provide install, test, api, smoke, and hygiene commands.
- [ ] `scripts/release-check.sh` and `scripts/release-check.ps1` verify generated file hygiene and run dry-clean by default.
- [ ] Release check scripts require `--force` to actually clean generated state.
- [ ] `docs/DEPLOYMENT.md` documents Docker build, compose, and volume mount instructions.

## Enterprise Readiness (v1.5)

- [ ] `decision-system enterprise-readiness` prints prototype-ready assessment with 13 pass + 11 gap items.
- [ ] `decision-system enterprise-readiness --json` returns structured JSON with readiness level and missing items.
- [ ] Assessment does not contact external services or require provider keys.
- [ ] `docs/ENTERPRISE_READINESS.md` documents the full gap analysis.

## Final Prototype Hardening (v1.6)

- [ ] All 49 CLI commands verified working offline with fake provider.
- [ ] CLI refactoring complete: `cli_security.py`, `cli_observability.py`, `cli_enterprise.py` are separate modules with registration functions.
- [ ] CLI import speed is under 3.0 seconds (no slow imports at module level).
- [ ] `decision-system check-hygiene` passes (warnings acceptable, failures require action).
- [ ] `decision-system check-hygiene --json` returns valid structured JSON.
- [ ] `clean-generated.sh` and `clean-generated.ps1` exist and are dry-run by default.
- [ ] 650 tests pass offline with no API keys.
- [ ] No tracked generated state in the working tree.
- [ ] All CHANGELOG.md entries are up to date for v1.6.

## Configuration Defaults

- [ ] `.env.example` has `DECISION_PROVIDER=fake`.
- [ ] `pyproject.toml` has the `decision-system = "decision_system.cli:app"` entry point.
- [ ] No real API keys or secrets in any committed file (grep for `sk-`, `api_key`, `token`).

## Documentation

- [ ] `README.md` reflects current CLI commands and all v1.x sections.
- [ ] `CHANGELOG.md` has an entry for the new version.
- [ ] `CLAUDE.md` version history or task list reflects the milestone.
- [ ] `docs/ARCHITECTURE.md` covers all subsystems through the current release.
- [ ] `docs/DECISIONS.md` has ADRs for all versions through the current release.
- [ ] `docs/RELEASE_CHECKLIST.md` itself is up to date.
- [ ] Any new CLI commands are documented in README.md.
- [ ] Architecture diagram or section in `docs/ARCHITECTURE.md` is current.

## Git Hygiene

- [ ] All tracked files in `.decision_system/` are removed from the index (use `git rm --cached -r .decision_system/` if needed).
- [ ] All tracked `__pycache__/` files are removed from the index.
- [ ] All tracked `.pyc` files are removed from the index.
- [ ] All tracked `.pytest_cache/` files are removed from the index.
- [ ] `.gitignore` covers all generated paths listed above.
- [ ] No generated demo data (`company_data/**/imported_*`) is in the index.

## Generated File Cleanup

Before cutting a release, use the safe cleanup helper (`scripts/clean-generated.sh --force` / `scripts/clean-generated.ps1 -Force`) which is dry-run by default. It protects `datasets/`, `.env`, `company_docs/`, and `company_data/`. Two convenience scripts are provided:

- macOS/Linux: `scripts/clean-generated.sh`
- Windows/PowerShell: `scripts/clean-generated.ps1`

Or run the equivalent commands directly:

- [ ] Bash: `find . -type d -name __pycache__ -prune -exec rm -rf {} + && rm -rf .pytest_cache .decision_system`
- [ ] PowerShell: `Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force; Remove-Item .pytest_cache -Recurse -Force -ErrorAction SilentlyContinue; Remove-Item .decision_system -Recurse -Force -ErrorAction SilentlyContinue`
- [ ] Verify `git status --short` shows no generated files after cleanup.

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
