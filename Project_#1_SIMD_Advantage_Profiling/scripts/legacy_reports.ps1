# Optional: collect reports for your ORIGINAL separate .c files.
# Usage from their folder: powershell -ExecutionPolicy Bypass -File path\to\legacy_reports.ps1
param([string]$SourceDirectory = ".")
Set-Location (Resolve-Path $SourceDirectory)
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force -Path 'reports' | Out-Null
$cases = @(
  @{ Source='kernels.c';           Stem='legacy_float_native';     Flags=@('-O3','-march=native') },
  @{ Source='kernels_double.c';    Stem='legacy_double_native';    Flags=@('-O3','-march=native') },
  @{ Source='kernels_alignment.c'; Stem='legacy_alignment_native'; Flags=@('-O3','-march=native') },
  @{ Source='kernels_stride.c';    Stem='legacy_stride_native';    Flags=@('-O3','-march=native') },
  @{ Source='kernels_bandwidth.c'; Stem='legacy_bandwidth_native'; Flags=@('-O3','-march=native') }
)
foreach ($item in $cases) {
  if (-not (Test-Path $item.Source)) {
    Write-Warning "Skipped missing file $($item.Source)"
    continue
  }
  $report = "reports\$($item.Stem)_vectorization.txt"
  $exe = "reports\$($item.Stem).exe"
  & gcc @($item.Flags) "-fopt-info-vec-all=$report" $item.Source '-o' $exe
  if ($LASTEXITCODE -ne 0) { throw "Failed compiling $($item.Source)" }
  Write-Host "Saved $report"
}
# The compute program explicitly uses AVX2/FMA intrinsics. Assembly is more
# appropriate than an auto-vectorization report for that program.
if (Test-Path 'kernels_compute.c') {
  & gcc -O3 -march=native -mavx2 -mfma -S -masm=intel `
    'kernels_compute.c' '-o' 'reports\legacy_compute.s'
  if ($LASTEXITCODE -ne 0) { throw 'Failed compute assembly compile' }
  Select-String -Path 'reports\legacy_compute.s' -Pattern 'vfmadd' |
    Select-Object -First 12 | Out-File 'reports\legacy_compute_fma_evidence.txt'
  Write-Host 'Saved compute FMA assembly evidence.'
}
Write-Host 'Reports are raw compiler evidence; quote only the relevant kernel lines in your report.'
