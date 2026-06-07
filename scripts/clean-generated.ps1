#requires -Version 5.1
param(
    [switch]$Force
)

if ($Force) {
    Write-Host "=== Removing generated/cache files (force) ==="
    python -m decision_system.devtools.clean_generated --force
} else {
    Write-Host "=== Dry run: would remove generated/cache files ==="
    Write-Host "    Re-run with -Force to actually delete: .\scripts\clean-generated.ps1 -Force"
    python -m decision_system.devtools.clean_generated
}
