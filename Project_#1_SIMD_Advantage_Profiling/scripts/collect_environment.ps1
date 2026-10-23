$ErrorActionPreference = 'Stop'
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '..'))
New-Item -ItemType Directory -Force -Path 'reports' | Out-Null
$out = 'reports\environment.txt'
'Project #1 machine and compiler configuration' | Set-Content $out
("Collected at: " + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')) | Add-Content $out
"`nGCC:" | Add-Content $out
(gcc --version | Select-Object -First 1) | Add-Content $out
"`nWindows:" | Add-Content $out
(Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber | Format-List | Out-String) | Add-Content $out
"`nCPU:" | Add-Content $out
(Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed,CurrentClockSpeed | Format-List | Out-String) | Add-Content $out
"`nRAM (capacity, configured speed, manufacturer):" | Add-Content $out
(Get-CimInstance Win32_PhysicalMemory | Select-Object Capacity,ConfiguredClockSpeed,Manufacturer | Format-Table | Out-String) | Add-Content $out
"`nActive power policy:" | Add-Content $out
(powercfg /getactivescheme | Out-String) | Add-Content $out
@'

Measurement notes to verify manually:
- Benchmark uses one thread and pins to Windows logical CPU 0 if possible.
- Logical CPU 0 core type (P/E): NOT independently verified.
- Turbo/frequency policy: dynamic unless externally controlled; record Windows power plan.
- SMT state: inferred logical/physical counts, not independently verified in firmware.
- Background work: document what else was running.
- SIMD widths must be verified from compiler reports; native CPU flags are target-dependent.
- Recorded TSC ticks per element are invariant TSC reference ticks, NOT true retired core cycles.
'@ | Add-Content $out
Write-Host "Saved $out"
