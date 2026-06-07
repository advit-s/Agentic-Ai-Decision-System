#!/usr/bin/env pwsh
$ErrorActionPreference='SilentlyContinue'
Write-Host "=== Removing generated/cache files ==="
Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force
Remove-Item .pytest_cache -Recurse -Force
Remove-Item .decision_system -Recurse -Force
Write-Host "Done."
