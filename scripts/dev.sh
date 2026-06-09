#!/usr/bin/env bash
# dev.sh - Local development helper for the Agentic Decision System
# Usage: ./scripts/dev.sh [command]
#
# Commands:
#   install    - Install package in dev mode
#   test       - Run pytest
#   api        - Start the local FastAPI server
#   smoke      - Run smoke test commands
#   hygiene    - Run check-hygiene
#   help       - Show this help

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cmd_install() {
    echo "Installing package in dev mode..."
    cd "$PROJECT_DIR"
    pip install -e ".[dev]" --break-system-packages 2>/dev/null || pip install -e ".[dev]"
    echo "Done."
}

cmd_test() {
    echo "Running tests..."
    cd "$PROJECT_DIR"
    python -m pytest -q "$@"
}

cmd_api() {
    echo "Starting local FastAPI server..."
    cd "$PROJECT_DIR"
    decision-system serve-api --reload
}

cmd_smoke() {
    echo "Running smoke tests..."
    cd "$PROJECT_DIR"
    decision-system --help
    decision-system check-hygiene
    decision-system init-data-catalog
    decision-system seed-demo-data --force
    decision-system profile-data
    decision-system map-ontology
    decision-system detect-patterns
    decision-system run-orchestration "Where are we losing money?"
    decision-system build-context "Where are we losing money?"
    decision-system run-war-room "Where are we losing money?"
    decision-system eval-war-room
    decision-system eval-providers
    decision-system eval
    decision-system scan-secrets 2>/dev/null || decision-system security scan-secrets
    decision-system metrics
    decision-system eval-history
    decision-system quality-report
    decision-system trace-summary
    echo "Smoke tests complete."
}

cmd_hygiene() {
    cd "$PROJECT_DIR"
    decision-system check-hygiene
}

cmd_help() {
    echo "Agentic Decision System - Local Development Helper"
    echo ""
    echo "Usage: ./scripts/dev.sh [command]"
    echo ""
    echo "Commands:"
    echo "  install    - Install package in dev mode"
    echo "  test       - Run pytest (pass extra args after)"
    echo "  api        - Start the local FastAPI server"
    echo "  smoke      - Run smoke test commands"
    echo "  hygiene    - Run check-hygiene"
    echo "  help       - Show this help"
}

case "${1:-help}" in
    install) cmd_install ;;
    test)    shift; cmd_test "$@" ;;
    api)     cmd_api ;;
    smoke)   cmd_smoke ;;
    hygiene) cmd_hygiene ;;
    help|*)  cmd_help ;;
esac
