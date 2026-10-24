
# Project 2 - Reproduce memory experiments
# Results are saved separately to avoid overwriting original data.

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$mlc = Join-Path $root "tools\mlc.exe"
$output = Join-Path $root "data\reproduced"

New-Item -ItemType Directory -Force $output | Out-Null

if (-not (Test-Path $mlc)) {
    throw "Intel MLC not found at $mlc"
}

# 1. Cache and DRAM latency: 5 trials each
$levels = @{
    L1 = 16
    L2 = 128
    L3 = 4096
    DRAM = 512000
}

foreach ($level in @("L1", "L2", "L3", "DRAM")) {
    for ($trial = 1; $trial -le 5; $trial++) {
        "Memory: $level | Trial: $trial" |
            Out-File "$output\$($level)_latency.txt" -Append
        & $mlc --idle_latency -e -r "-b$($levels[$level])" -c0 |
            Out-File "$output\$($level)_latency.txt" -Append
    }
}

# 2. System-wide peak bandwidth: 5 trials
for ($trial = 1; $trial -le 5; $trial++) {
    "Bandwidth Trial $trial" |
        Out-File "$output\bandwidth_5trials.txt" -Append
    & $mlc --peak_injection_bandwidth -e |
        Out-File "$output\bandwidth_5trials.txt" -Append
}

# 3. Sequential/random stride experiments: 3 trials each
foreach ($pattern in @("Sequential", "Random")) {
    foreach ($stride in @(64, 256, 1024)) {

        for ($trial = 1; $trial -le 3; $trial++) {
            $latencyArgs = @(
                "--idle_latency", "-e", "-c0", "-b131072",
                "-l$stride"
            )

            $bandwidthArgs = @(
                "--loaded_latency", "-T", "-R", "-e",
                "-k0", "-b131072", "-l$stride", "-t3"
            )

            if ($pattern -eq "Random") {
                $latencyArgs += "-r"
                $bandwidthArgs += "-U"
            }

            "Pattern: $pattern | Stride: $stride B | Trial: $trial" |
                Out-File "$output\latency_$($pattern)_$($stride)B.txt" -Append

            & $mlc @latencyArgs |
                Out-File "$output\latency_$($pattern)_$($stride)B.txt" -Append

            "Pattern: $pattern | Stride: $stride B | Trial: $trial" |
                Out-File "$output\bandwidth_$($pattern)_$($stride)B.txt" -Append

            & $mlc @bandwidthArgs |
                Out-File "$output\bandwidth_$($pattern)_$($stride)B.txt" -Append
        }
    }
}

# 4. Working-set sweep: 3 trials per size
$sizes = @(
    16, 32, 64, 128, 256, 512, 1024, 2048,
    4096, 8192, 16384, 32768, 65536, 131072, 524288
)

foreach ($size in $sizes) {
    for ($trial = 1; $trial -le 3; $trial++) {
        "Buffer: $size KiB | Trial: $trial" |
            Out-File "$output\working_set_sweep.txt" -Append

        & $mlc --idle_latency -e -r -c0 "-b$size" -l256 |
            Out-File "$output\working_set_sweep.txt" -Append
    }
}

# 5. Read/write mixes: 5 trials each
$mixes = @{
    "100_Read" = "-R"
    "100_Write_NT" = "-W6"
    "50_Read_50_Write" = "-W5"
}

foreach ($mix in $mixes.Keys) {
    for ($trial = 1; $trial -le 5; $trial++) {
        "Workload: $mix | Trial: $trial" |
            Out-File "$output\mix_$mix.txt" -Append

        & $mlc --loaded_latency -T -e -k0 -b131072 -t3 $mixes[$mix] |
            Out-File "$output\mix_$mix.txt" -Append
    }
}

# 6. Loaded-latency sweep: 5 trials
for ($trial = 1; $trial -le 5; $trial++) {
    "Loaded Latency Trial $trial" |
        Out-File "$output\loaded_latency_5trials.txt" -Append

    & $mlc --loaded_latency -e -r -U -R -k1-7 -b131072 -t3 |
        Out-File "$output\loaded_latency_5trials.txt" -Append
}

Write-Host "Experiments completed. Results saved to $output"
