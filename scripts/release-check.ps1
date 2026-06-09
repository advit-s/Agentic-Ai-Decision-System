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

# Git detection: check if we're inside a Git repository
$inGit = 0
git rev-parse --is-inside-work-tree 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) {
    $inGit = 1
    Write-Host "[INFO] Git repository detected — using git ls-files for tracking checks" -ForegroundColor Cyan
} else {
    Write-Host "[INFO] Not inside a Git repository — using filesystem fallback checks" -ForegroundColor Yellow
}

# 1. No __pycache__ in tracked files
if ($inGit -eq 1) {
    $pycache = (git ls-files | Select-String "__pycache__").Count
} else {
    $pycache = @(Get-ChildItem -Recurse -Directory -Filter __pycache__ -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notmatch '\.venv' -and $_.FullName -notmatch '\.git' }).Count
}
Check "No __pycache__ in tracked files" $(if ($pycache -eq 0) { 0 } else { 1 })

# 2. No .pyc in tracked files
if ($inGit -eq 1) {
    $pyc = (git ls-files | Select-String "\.pyc$").Count
} else {
    $pyc = @(Get-ChildItem -Recurse -Filter "*.pyc" -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notmatch '\.venv' -and $_.FullName -notmatch '\.git' }).Count
}
Check "No .pyc files in tracked files" $(if ($pyc -eq 0) { 0 } else { 1 })

# 3. No .decision_system/ tracked
if ($inGit -eq 1) {
    $ds = (git ls-files | Select-String "^\.decision_system/").Count
} else {
    $ds = $(if (Test-Path ".decision_system") { 1 } else { 0 })
}
Check "No .decision_system/ tracked" $(if ($ds -eq 0) { 0 } else { 1 })

# 4. No datasets/ tracked
if ($inGit -eq 1) {
    $datasets = (git ls-files | Select-String "^datasets/").Count
} else {
    $datasets = $(if (Test-Path "datasets") { 1 } else { 0 })
}
Check "No datasets/ tracked" $(if ($datasets -eq 0) { 0 } else { 1 })

# 5. No .env tracked
if ($inGit -eq 1) {
    $envCount = (git ls-files | Select-String "^\.env$").Count
} else {
    $envCount = $(if (Test-Path ".env") { 1 } else { 0 })
}
Check "No .env tracked" $(if ($envCount -eq 0) { 0 } else { 1 })

# 6. No secrets in tracked source (basic grep check)
if ($inGit -eq 1) {
    $secrets = 0
    $sourceFiles = git ls-files | Select-String "\.(py|md|txt|json|yaml|yml|toml|cfg|ini|sh)$" | % { $_.Line }
    foreach ($file in $sourceFiles) {
        if ($file -match '__pycache__' -or $file -match '\.decision_system') { continue }
        $content = Get-Content $file -Raw -ErrorAction SilentlyContinue
        if ($content -match '(?i)(sk-[a-zA-Z0-9]{20,}|AKIA[A-Z0-9]{16}|nvapi-[a-zA-Z0-9\-_]{20,})') {
            $secrets++
        }
    }
} else {
    $secrets = @(Get-ChildItem -Recurse -Include "*.py","*.md","*.txt","*.json","*.yaml","*.yml","*.toml","*.cfg","*.ini","*.sh" -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notmatch '\.venv' -and $_.FullName -notmatch '\.git' -and $_.FullName -notmatch '\.decision_system' } |
        Select-String -Pattern '(?i)(sk-[a-zA-Z0-9]{20,}|AKIA[A-Z0-9]{16}|nvapi-[a-zA-Z0-9\-_]{20,})' -SimpleMatch:$false).Count
}
Check "No obvious secrets in tracked source" $(if ($secrets -eq 0) { 0 } else { 1 })

# 7. Package install works
pip install -e ".[dev]" 2>$null | Out-Null
Check "Package install works" 0

# 8. Tests pass
$testResult = 0
python -m pytest -q --tb=no 2>$null
if ($LASTEXITCODE -ne 0) { $testResult = 1 }
Check "Tests pass" $testResult

# 9. CLI import is fast
$importResult = 0
python -c "import time; t=time.time(); import decision_system.cli; e=time.time()-t; print(f'CLI import: {e:.3f}s'); assert e < 3.0" 2>$null
if ($LASTEXITCODE -ne 0) { $importResult = 1 }
Check "CLI import under 3s" $importResult

# 10. check-hygiene
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
