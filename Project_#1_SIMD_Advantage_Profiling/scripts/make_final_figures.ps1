# Run this from your project folder. NO need to rerun experiments if raw/bench_*.csv files exist.
$ErrorActionPreference = 'Stop'
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '..'))
if (-not (Get-ChildItem raw\bench_*.csv -ErrorAction SilentlyContinue)) {
    throw 'No raw/bench_*.csv files. Run scripts/build_and_run.ps1 first.'
}
py scripts\plot_results.py
if ($LASTEXITCODE -ne 0) { throw 'Plot script failed.' }
py scripts\summarize_vectorization.py
if ($LASTEXITCODE -ne 0) { throw 'Vectorization summary script failed.' }
Write-Host 'Final 7 figures: figures\final\' -ForegroundColor Green
Write-Host 'Report table: processed\final\report_numbers.md' -ForegroundColor Green
Write-Host 'Vector evidence: reports\vectorization_summary.md' -ForegroundColor Green
