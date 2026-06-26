# Release Checklist — v1.35.0-dev

> **Version:** 1.35.0-dev
> **Milestone:** Public Beta Release Candidate + Demo Video Script
> **Date:** 2026-06-24
> **Category:** Release Process

This checklist is reusable for all future beta releases. Check each item before tagging a release.

---

## Pre-Release

### Version
- [ ] `pyproject.toml` version is updated
- [ ] `src/decision_system/__init__.py` version matches
- [ ] Frontend fallback version is updated (AppNav.jsx, api.js)
- [ ] `docs/CURRENT_STATE.md` header reflects current version
- [ ] `CHANGELOG.md` has entry for this version

### Git Hygiene
- [ ] `git status --short` — working tree is clean
- [ ] `git diff --check` — no whitespace errors
- [ ] All new files are tracked
- [ ] Generated artifacts are gitignored

### Backend Tests
- [ ] `python -m pytest -q` — all tests pass
- [ ] Targeted test suites pass individually:
  - [ ] `tests/test_security.py`
  - [ ] `tests/test_graph_api.py`
  - [ ] `tests/test_data_sources/`
  - [ ] `tests/test_verification`
  - [ ] `tests/test_providers`
  - [ ] `tests/test_workflow_engine/test_api.py`
  - [ ] `tests/test_connectors.py`
  - [ ] `tests/test_connector_sync.py`
  - [ ] `tests/test_connector_reliability.py`

### Frontend
- [ ] `cd web/workflow-builder && npm test` — all tests pass
- [ ] `cd web/workflow-builder && npm run build` — builds without errors
- [ ] No new console errors or warnings in app shell

### Scripts
- [ ] `bash -n scripts/*.sh` — all shell scripts parse without syntax errors
- [ ] `./scripts/doctor-local.sh` — 0 failures
- [ ] `./scripts/validate-local.sh` — all checks pass
- [ ] `./scripts/collect-diagnostics.sh` — output is safe (no secrets)

### Docker (if available)
- [ ] `docker compose up --build` — both containers start
- [ ] Frontend loads at `http://localhost:3000`
- [ ] Backend responds at `http://localhost:8000/health`
- [ ] `./scripts/local-smoke-test.sh` passes
- [ ] `./scripts/e2e-local-demo-smoke.sh` passes

### Documentation
- [ ] README is accurate and up to date
- [ ] Known limitations are current
- [ ] Issue templates reference current version
- [ ] PR template is up to date
- [ ] Docs links are not broken
- [ ] Version references are consistent across docs

### Feedback Flow
- [ ] README links to reviewer guide
- [ ] Reviewer guide links to issue templates
- [ ] Issue templates ask for diagnostics
- [ ] Diagnostics script redacts secrets
- [ ] Known limitations linked from all relevant docs

## Release

### Tag
- [ ] Git tag created (e.g., `v1.35.0-dev`)
- [ ] Tag pushed to origin
- [ ] Release notes drafted (use `docs/PUBLIC_BETA_RELEASE_CANDIDATE.md`)

### Validation (Post-Release)
- [ ] Fresh clone + setup works end-to-end
- [ ] Docker compose up works from clean state
- [ ] Demo path is walkable from fresh install

## Environment-Blocked Checks

If Docker is unavailable, note:
```
Docker smoke — environment-blocked (Docker not available)
E2E demo smoke — environment-blocked (requires running backend)
```

If Tesseract is unavailable, note:
```
OCR tests — environment-dependent (Tesseract not installed)
```
