# Case console launcher (Phase 1: startup guarantee + data warmup)
# Usage: .\scripts\launch_case_console.ps1
# Starts Flask :5000 -> waits /api/ready -> import/apply -> geocode-regions -> verify

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $MyInvocation.MyCommand.Path "..\..")
$venvPython = Join-Path $repoRoot "backend\.venv\Scripts\python.exe"
$runPy = Join-Path $repoRoot "backend\run.py"
$base = "http://127.0.0.1:5000"

Set-Location $repoRoot

if (-not (Test-Path $venvPython)) {
    Write-Host "[ERROR] venv python not found: $venvPython" -ForegroundColor Red
    exit 1
}

Write-Host "[LAUNCH] Starting Flask backend :5000 (background)..." -ForegroundColor Cyan
$proc = Start-Process -FilePath $venvPython -ArgumentList "`"$runPy`"" -PassThru -WindowStyle Minimized
Write-Host "       PID = $($proc.Id)" -ForegroundColor Gray

$ready = $false
$readyPayload = $null
for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Seconds 2
    try {
        $readyPayload = Invoke-RestMethod -Uri "$base/api/ready" -TimeoutSec 3 -ErrorAction Stop
        if ($readyPayload.status -eq "ready" -or $readyPayload.database_runtime) {
            $ready = $true
            break
        }
    } catch {
        Write-Host "       waiting for backend... ($($i*2)s)" -ForegroundColor Gray
    }
}

if (-not $ready) {
    Write-Host "[ERROR] backend not ready in 80s." -ForegroundColor Red
    Write-Host "       Check backend/.env.local POSTGRES_DATABASE_URL or port 5000 conflict." -ForegroundColor Yellow
    Write-Host "       Tip: use 127.0.0.1 not localhost; stop old 5000 process first." -ForegroundColor Yellow
    exit 1
}

$db = $readyPayload.database_runtime
Write-Host "[OK] backend ready: backend=$($db.backend) shipment_facts=$($db.shipment_facts)" -ForegroundColor Green

Write-Host "[WARMUP] importing case data (import/apply)..." -ForegroundColor Cyan
try {
    $importResp = Invoke-RestMethod -Uri "$base/api/cases/food-supply/import/apply" -Method Post -Body '{"persist":true}' -ContentType "application/json" -TimeoutSec 60 -ErrorAction Stop
    Write-Host "       nodes=$($importResp.summary.node_count) facilities=$($importResp.summary.facility_count) stores=$($importResp.summary.b_store_count)" -ForegroundColor Green
} catch {
    Write-Host "       [WARN] import/apply failed: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host "[WARMUP] batch geocoding (geocode-regions)..." -ForegroundColor Cyan
try {
    $geoResp = Invoke-RestMethod -Uri "$base/api/cases/food-supply/c2c/geocode-regions" -Method Post -Body '{"persist":true,"provider":"amap"}' -ContentType "application/json" -TimeoutSec 300 -ErrorAction Stop
    $s = $geoResp.summary
    Write-Host "       total=$($s.total) resolved=$($s.resolved) cached=$($s.cached) needs=$($s.needs_geocoding) authenticity=$($geoResp.authenticity_level)" -ForegroundColor Green
} catch {
    Write-Host "       [WARN] geocode-regions failed: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host "[VERIFY] c2c_clusters..." -ForegroundColor Cyan
try {
    $clusters = Invoke-RestMethod -Uri "$base/api/cases/food-supply/c2c/clusters" -TimeoutSec 30 -ErrorAction Stop
    $aCount = ($clusters.clusters | Where-Object { $_.cluster_authenticity_level -eq "A" }).Count
    Write-Host "       clusters=$($clusters.summary.cluster_count) A-level=$aCount C-level=$($clusters.summary.cluster_count - $aCount)" -ForegroundColor Green
} catch {
    Write-Host "       [WARN] clusters verify failed: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "[OK] Case console ready" -ForegroundColor Green
Write-Host "       backend: $base" -ForegroundColor White
Write-Host "       frontend: http://127.0.0.1:5173 (open new terminal: cd frontend; npm run dev)" -ForegroundColor White
Write-Host "       stop backend: Stop-Process -Id $($proc.Id)" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop backend..." -ForegroundColor Gray
$proc.WaitForExit()
