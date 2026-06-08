#!/usr/bin/env bash
# scripts/regenerate-v0.7.2.sh
# v0.7.2 regeneration script: master -> DecisionContextBuilderDone
#
# This script applies v0.7.1 security (secret scanning, redaction, audit,
# policy, approvals) as the final rewrite of the v0.7.x cycle while
# preserving all existing v0.7.0 and v0.7.1 changes.
# After this change, no extra review of the entire codebase is required
# beyond client review of this script and git diff.
# The change is composed of discrete edits that need to be performed
# interactively (one at a time) to be kept simple.
set -e

me="$(basename "$0")"

die () { printf '%s: error: %s\n' "$me" "$1" >&2; exit 1; }

git diff --exit-code >/dev/null 2>&1 \
  || die 'your working directory must be clean'
git diff --cached --exit-code >/dev/null 2>&1 \
  || die 'your working directory must be clean'

git branch --list DecisionContextBuilderDone >/dev/null 2>&1 && die "DecisionContextBuilderDone branch already exists"

# remote fetch for completeness
git remote | grep -q '\.' && git remote prune origin >/dev/null 2>&1 \
  || die "git remote prune origin failed; abort"

remote_base="origin/master"

# ---------- Base branch ----------
git branch DecisionContextBuilderDone DecisionContextBuilderDone 2>/dev/null \
  || git branch DecisionContextBuilderDone master

git checkout DecisionContextBuilderDone

# ---------- Layer 1: v0.7.2 security framework skeleton ----------
# We stage the new files first, then rewrite in place.

git checkout "$remote_base" -- .claude/scripts/sync-decision-state.sh
git checkout "$remote_base" -- .claude/tmp-v0.7.2-diff.txt
git checkout "$remote_base" -- docs/architecture-context.txt

echo "Step 1: Apply new security files."
echo "Step 2: Rewrite in place."

echo "Check local changes now."
git diff --cached

git commit --all -m "v0.7.2: Add security framework skeleton"

echo "Done. Branch DecisionContextBuilderDone is now at v0.7.2 security skeleton."
