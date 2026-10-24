$root = Split-Path $PSScriptRoot -Parent
$file = "project3_test.bin"
$out = "..\data\raw"

Set-Location (Join-Path $root "scratch")
if (!(Test-Path $file)) {
    throw "Test file missing. Stopping for safety."
}

$tests = @(
    @{Name="randread_4k";   RW="randread";  BS="4k"},
    @{Name="randwrite_4k";  RW="randwrite"; BS="4k"},
    @{Name="seqread_128k";  RW="read";      BS="128k"},
    @{Name="seqwrite_128k"; RW="write";     BS="128k"}
)

foreach ($test in $tests) {
    for ($trial=1; $trial -le 3; $trial++) {
        $name = "$($test.Name)_trial$trial"
        Write-Host "Running $name"

        & fio --name=$name `
            --filename="$file" `
            --allow_file_create=0 `
            --size=8G `
            --rw=$($test.RW) `
            --bs=$($test.BS) `
            --ioengine=windowsaio `
            --direct=1 `
            --iodepth=1 `
            --numjobs=1 `
            --time_based=1 `
            --runtime=10 `
            --ramp_time=2 `
            --refill_buffers=1 `
            --buffer_compress_percentage=0 `
            --clat_percentiles=1 `
            --percentile_list=50:95:99:99.9 `
            --eta=never `
            --output-format=json `
            --output="$out\$name.json"

        if ($LASTEXITCODE -ne 0) {
            throw "FIO failed on $name"
        }
    }
}

Write-Host "All baseline trials finished!"

