# release-check.ps1 - Verify the repo is clean and ready for release (PowerShell)

$ProjectDir = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectDir

$Pass = 0
$Fail = 0

function Check($Name, $Result) {
    if ($Result -eq 0) {
        Write-Host "[PASS] $Name" -ForegroundColor Green
        $script:Pass++
    } else {
        Write-Host "[FAIL] $Name" -ForegroundColor Red
        $script:Fail++
    }
}

# 1. No __pycache__ in tracked files
$pycache = (git ls-files | Select-String "__pycache__").Count
Check "No __pycache__ in tracked files" $(if ($pycache -eq 0) { 0 } else { 1 })

# 2. No .pyc in tracked files
$pyc = (git ls-files | Select-String "\.pyc$").Count
Check "No .pyc files in tracked files" $(if ($pyc -eq 0) { 0 } else { 1 })

# 3. No .decision_system/ tracked
$ds = (git ls-files | Select-String "^\.decision_system/").Count
Check "No .decision_system/ tracked" $(if ($ds -eq 0) { 0 } else { 1 })

# 4. No datasets/ tracked
$datasets = (git ls-files | Select-String "^datasets/").Count
Check "No datasets/ tracked" $(if ($datasets -eq 0) { 0 } else { 1 })

# 5. No .env tracked
$env = (git ls-files | Select-String "^\.env$").Count
Check "No .env tracked" $(if ($env -eq 0) { 0 } else { 1 })

# 6. Package install works
pip install -e ".[dev]" 2>$null | Out-Null
Check "Package install works" 0

# 7. Tests pass
$testResult = 0
python -m pytest -q --tb=no 2>$null
if ($LASTEXITCODE -ne 0) { $testResult = 1 }
Check "Tests pass" $testResult

# 8. CLI import is fast
$importResult = 0
python -c "import time; t=time.time(); import decision_system.cli; e=time.time()-t; print(f'CLI import: {e:.3f}s'); assert e < 3.0" 2>$null
if ($LASTEXITCODE -ne 0) { $importResult = 1 }
Check "CLI import under 3s" $importResult

# 9. check-hygiene
$hygieneResult = 0
decision-system check-hygiene 2>$null
if ($LASTEXITCODE -ne 0) { $hygieneResult = 1 }
Check "check-hygiene passes" $hygieneResult

Write-Host ""
Write-Host "Release Check: $Pass passed, $Fail failed"
if ($Fail -gt 0) {
    Write-Host "RESULT: NOT READY FOR RELEASE" -ForegroundColor Red
    exit 1
} else {
    Write-Host "RESULT: READY FOR RELEASE" -ForegroundColor Green
}
