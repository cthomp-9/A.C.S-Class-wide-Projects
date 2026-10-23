# Run from the extracted project folder. This script always uses its own location.
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Get-Command gcc -ErrorAction SilentlyContinue)) { throw 'GCC not found. Open the MSYS2 UCRT64 terminal or configure gcc on PATH.' }
if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw 'Python launcher py not found. Install Python and enable its launcher.' }
Write-Host '1/4: Collecting hardware information...' -ForegroundColor Cyan
& powershell -ExecutionPolicy Bypass -File '.\scripts\collect_environment.ps1'
if ($LASTEXITCODE -ne 0) { throw 'Hardware information step failed.' }
Write-Host '2/4: Compiling and running all three kernels (all configurations)...' -ForegroundColor Cyan
& powershell -ExecutionPolicy Bypass -File '.\scripts\build_and_run.ps1' -Full
if ($LASTEXITCODE -ne 0) { throw 'Benchmark failed.' }
Write-Host '3/4: Installing graphing dependencies...' -ForegroundColor Cyan
& py -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
Write-Host '4/4: Making seven final graphs and vectorization summary...' -ForegroundColor Cyan
& powershell -ExecutionPolicy Bypass -File '.\scripts\make_final_figures.ps1'
if ($LASTEXITCODE -ne 0) { throw 'Graph generation failed.' }
Write-Host 'SUCCESS: See figures\final and processed\final and reports.' -ForegroundColor Green
