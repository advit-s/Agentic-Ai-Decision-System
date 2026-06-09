# dev.ps1 - Local development helper for the Agentic Decision System (PowerShell)
# Usage: .\scripts\dev.ps1 [command]
#
# Commands:
#   install    - Install package in dev mode
#   test       - Run pytest
#   api        - Start the local FastAPI server
#   smoke      - Run smoke test commands
#   hygiene    - Run check-hygiene
#   help       - Show this help

param(
    [string]$Command = "help"
)

$ProjectDir = Split-Path -Parent $PSScriptRoot

function Install-Pkg {
    Write-Host "Installing package in dev mode..."
    Set-Location $ProjectDir
    pip install -e ".[dev]"
    Write-Host "Done."
}

function Run-Test {
    Write-Host "Running tests..."
    Set-Location $ProjectDir
    python -m pytest -q @Args
}

function Start-Api {
    Write-Host "Starting local FastAPI server..."
    Set-Location $ProjectDir
    decision-system serve-api --reload
}

function Run-Smoke {
    Write-Host "Running smoke tests..."
    Set-Location $ProjectDir
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
    decision-system security scan-secrets
    decision-system metrics
    decision-system eval-history
    decision-system quality-report
    decision-system trace-summary
    Write-Host "Smoke tests complete."
}

function Run-Hygiene {
    Set-Location $ProjectDir
    decision-system check-hygiene
}

function Show-Help {
    Write-Host "Agentic Decision System - Local Development Helper"
    Write-Host ""
    Write-Host "Usage: .\scripts\dev.ps1 [command]"
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  install    - Install package in dev mode"
    Write-Host "  test       - Run pytest"
    Write-Host "  api        - Start the local FastAPI server"
    Write-Host "  smoke      - Run smoke test commands"
    Write-Host "  hygiene    - Run check-hygiene"
    Write-Host "  help       - Show this help"
}

switch ($Command) {
    "install" { Install-Pkg }
    "test"    { Run-Test }
    "api"     { Start-Api }
    "smoke"   { Run-Smoke }
    "hygiene" { Run-Hygiene }
    default   { Show-Help }
}
