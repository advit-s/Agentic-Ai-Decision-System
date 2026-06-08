#!/usr/bin/env bash
# scripts/build-v1.2-security.sh
# v1.2 security package build script.
#
# This script creates the new security package files, updates .gitignore,
# updates the CHANGELOG, and stages changes (without committing).
# Run from the repository root.
set -euo pipefail

me="$(basename "$0")"

die () { printf '%s: error: %s\n' "$me" "$1" >&2; exit 1; }

# ---------- Check working tree ----------
git diff --quiet || die 'working tree has uncommitted changes; stash or commit first'
git diff --cached --quiet || die 'staged changes present; commit or reset first'

# ---------- Verify current version ----------
CURRENT_VERSION="$(grep -E '^version = ' pyproject.toml | sed 's/version = "\(.*\)".*/\1/')"
echo "Current version: $CURRENT_VERSION"
[[ "$CURRENT_VERSION" == "1.1.0" ]] || die "expected version 1.1.0 in pyproject.toml before applying changes"

echo "Applying v1.2 changes..."
echo ""

echo "1/6: Add .decision_system/security/ to .gitignore"
# (Already applied if .gitignore already has it.)
grep -q "security/" .gitignore || {
  sed -i "/\.decision_system\/connectors\//i\.decision_system\/security\/" .gitignore
}
echo " - OK"

echo "2/6: Update version to 1.2.0 in pyproject.toml and __init__.py"
sed -i 's/version = "1.1.0"/version = "1.2.0"/' pyproject.toml
sed -i 's/__version__ = "1.1.0"/__version__ = "1.2.0"/' src/decision_system/__init__.py
echo " - OK"

echo "3/6: Ensure security package files and CLI commands are in place"
# The following files should already be in src/decision_system/security/:
# - __init__.py
# - models.py
# - secret_scan.py
# - redaction.py
# - audit.py
# - policy.py
# - approvals.py
# - store.py
# And cli.py should contain the security and approval app registrations.
for f in src/decision_system/security/__init__.py \
         src/decision_system/security/models.py \
         src/decision_system/security/secret_scan.py \
         src/decision_system/security/redaction.py \
         src/decision_system/security/audit.py \
         src/decision_system/security/policy.py \
         src/decision_system/security/approvals.py \
         src/decision_system/security/store.py \
         src/decision_system/security/inspector.py \
         src/decision_system/api/routes_security.py \
         tests/test_security.py; do
  [[ -f "$f" ]] || die "missing required file: $f"
done
echo " - OK"

echo "4/6: Stage new files"
git add scripts/build-v1.2-security.sh || true
git add scripts/regenerate-pretest.sh || true
git add scripts/regenerate-selective-code-review.sh || true
git add scripts/sync-v0.7.2.sh || true
echo " - OK"

echo "5/6: Verify key import names match .models.py"
python -c "from decision_system.security.models import SecretFinding, SecretScanResult, RedactionPreviewResult, AuditEvent, PolicyCheck, PolicyCheckResult, ApprovalRequest" \
  || die "security module imports failed"
echo " - OK"

echo "6/6: Quick commit observations"
echo "Run the following to complete the update:"
echo "  git add .gitignore pyproject.toml src/decision_system/__init__.py src/decision_system/cli.py src/decision_system/security/ src/decision_system/api/routes_security.py tests/test_security.py"
echo "  git commit -m 'feat(v1.2): security, governance, audit package'"
echo ""
echo "Changes apply cleanly. Status:"
git status --short
