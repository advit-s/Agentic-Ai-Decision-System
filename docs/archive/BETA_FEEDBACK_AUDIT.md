# Beta Feedback Audit — v1.34

> **Version:** 1.34.0-dev
> **Milestone:** Local Beta Feedback Loop + Issue Templates
> **Date:** 2026-06-24

## Current State

### What exists today
- GitHub issue tracker (no templates — free-form text only)
- No PR template
- Beta QA checklist (`docs/BETA_QA_CHECKLIST.md`)
- Beta release notes (`docs/BETA_RELEASE_NOTES.md`)
- Demo path documentation (`docs/DEMO_PATH.md`)

### Gaps

| Area | What's Missing | Priority |
|------|---------------|----------|
| Bug reporting | No structured template — reporters don't provide version, OS, steps to reproduce | High |
| Feature requests | No structured template — vague requests without local-first constraints | Medium |
| Beta feedback | No structured template — feedback is unstructured | High |
| PR review | No PR template — PRs lack impact checklist | Medium |
| Diagnostics | No safe diagnostic script — users paste raw logs with secrets | High |
| Reviewer onboarding | No reviewer guide — new testers don't know what or how to test | High |
| Bug bash process | No bug bash checklist — structured test areas undefined | Medium |
| Known limitations | Spread across multiple docs — contradictory or stale | High |
| Issue triage | No label taxonomy, no severity definitions, no triage process | Medium |
| Example issues | No examples — reporters don't know what good looks like | Low |

## v1.34 Plan

| Action | Artifact |
|--------|----------|
| Create bug report template | `.github/ISSUE_TEMPLATE/bug_report.yml` |
| Create feature request template | `.github/ISSUE_TEMPLATE/feature_request.yml` |
| Create beta feedback template | `.github/ISSUE_TEMPLATE/beta_feedback.yml` |
| Create docs issue template | `.github/ISSUE_TEMPLATE/docs_issue.yml` |
| Create PR template | `.github/pull_request_template.md` |
| Create safe diagnostics script | `scripts/collect-diagnostics.sh` |
| Create beta reviewer guide | `docs/BETA_REVIEWER_GUIDE.md` |
| Create bug bash checklist | `docs/BUG_BASH_CHECKLIST.md` |
| Create known limitations registry | `docs/KNOWN_LIMITATIONS.md` |
| Create issue triage doc | `docs/ISSUE_TRIAGE.md` |
| Create example issues | `docs/EXAMPLE_ISSUES.md` |
| Update README | Add beta callout and links |
| Add frontend feedback links | Help navigation in app |

## Acceptance

v1.34 feedback loop is ready when:
- Template artifacts exist and collect actionable details
- Diagnostics script is safe by default (no secrets)
- Reviewer guide is clear enough for a non-contributor to follow
- Known limitations are centralized and non-contradictory
- Docs link together coherently
