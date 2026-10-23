# Run in the root of this folder from VS Code's PowerShell terminal:
#   powershell -ExecutionPolicy Bypass -File .\scripts\build_and_run.ps1
# Or, for both data types in all experiments:
#   powershell -ExecutionPolicy Bypass -File .\scripts\build_and_run.ps1 -Full
param([switch]$Full)
$ErrorActionPreference = 'Stop'
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '..'))
New-Item -ItemType Directory -Force -Path 'build','raw','reports','processed','figures' | Out-Null
if (-not (Get-Command gcc -ErrorAction SilentlyContinue)) { throw 'gcc not found. Check your PATH.' }

$builds = @(
  @{ Name = 'scalar';  Flags = @('-O3','-march=native','-fno-tree-vectorize','-fno-tree-slp-vectorize') },
  @{ Name = 'default'; Flags = @('-O3') },
  @{ Name = 'native';  Flags = @('-O3','-march=native') }
)
$types = @(
  @{ Name = 'float32'; Flags = @() },
  @{ Name = 'float64'; Flags = @('-DDTYPE_DOUBLE=1') }
)

foreach ($dtype in $types) {
  foreach ($build in $builds) {
    $stem = "$($dtype.Name)_$($build.Name)"
    $exe = "build\$stem.exe"
    $report = "reports\$stem`_vectorization.txt"
    $allFlags = @('-std=c11') + $build.Flags + $dtype.Flags
    $flagFile = "reports\$stem`_flags.txt"
    ('gcc ' + ($allFlags -join ' ') + ' src\simd_benchmark.c -o ' + $exe) | Set-Content $flagFile
    Write-Host "`nCompiling $stem" -ForegroundColor Cyan
    # One report for every build, including scalar (normally blank).
    & gcc @allFlags "-fopt-info-vec-all=$report" 'src\simd_benchmark.c' '-o' $exe
    if ($LASTEXITCODE -ne 0) { throw "Compile failed: $stem" }
    $modes = if ($dtype.Name -eq 'float32' -or $Full) { @('baseline','alignment','stride') } else { @('baseline') }
    foreach ($mode in $modes) {
      $csv = "raw\bench_$($mode)_$stem.csv"
      Write-Host "Running $stem / $mode" -ForegroundColor Yellow
      & ".\$exe" $mode $build.Name $csv
      if ($LASTEXITCODE -ne 0) { throw "Benchmark failed: $stem / $mode" }
    }
  }
}
Write-Host "`nFinished. Raw trials in raw/, compiler reports in reports/." -ForegroundColor Green
Write-Host "Run: py scripts\summarize_vectorization.py; py scripts\plot_results.py"
