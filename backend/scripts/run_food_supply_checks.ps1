param(
  [switch]$SkipOpenSpec,
  [switch]$SkipFrontendBuild
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..\..")
$pytestBaseTemp = Join-Path $repoRoot "backend\var\pytest-food-supply"

Set-Location $repoRoot
if (-not (Test-Path $pytestBaseTemp)) {
  New-Item -ItemType Directory -Force $pytestBaseTemp | Out-Null
}

if (-not $SkipOpenSpec) {
  $openspec = Get-Command openspec -ErrorAction SilentlyContinue
  if ($openspec) {
    & openspec validate enhance-food-supply-advanced-optimization --strict
  } else {
    Write-Warning "openspec command not found; skipped strict validation."
  }
}

& .\backend\.venv\Scripts\python.exe -B -m pytest backend\tests\test_food_supply_case_service.py -q --basetemp $pytestBaseTemp -p no:cacheprovider

if (-not $SkipFrontendBuild) {
  Push-Location .\frontend
  try {
    & npm run build
  } finally {
    Pop-Location
  }
}
