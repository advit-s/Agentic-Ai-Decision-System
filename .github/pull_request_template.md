# Pull Request — v1.34.0-dev

> **This is a local MVP beta candidate.** Do not claim production readiness, enterprise security, or cloud-native features unless explicitly scoped.

## What Changed

<!-- Describe the changes in 1-3 sentences. What does this PR do? -->

## Why It Changed

<!-- What problem does this solve? Link to GitHub issue if applicable. -->

## Checklist

### Code Quality
- [ ] Backend tests pass (`python -m pytest -q`)
- [ ] Frontend tests pass (`cd web/workflow-builder && npm test`)
- [ ] Frontend builds without errors (`cd web/workflow-builder && npm run build`)
- [ ] Shell scripts parse without syntax errors (`bash -n scripts/*.sh`)
- [ ] Hygiene check passes (`decision-system check-hygiene`)

### Documentation
- [ ] README updated if behavior changed
- [ ] CHANGELOG updated with version and changes
- [ ] Docs updated if behavior changed
- [ ] Known limitations updated if new limitation discovered

### Local-First Impact
- [ ] Works offline with fake provider (no API keys required)
- [ ] No cloud services or external write actions added
- [ ] No telemetry or automatic data upload added
- [ ] Data remains under `.decision_system/` storage

### Security / RBAC Impact
- [ ] No secrets exposed in UI, logs, or diagnostics
- [ ] Workspace isolation respected if data operations changed
- [ ] RBAC permissions considered if governance mode affected

### Connector / Write-Action Impact
- [ ] No new write connectors added (read-only only)
- [ ] No new external write actions added

### UI Changes (if applicable)
- [ ] Screenshots attached
- [ ] Empty/error states handled

## Known Limitations
<!-- List any known limitations this PR introduces or does not address. -->
