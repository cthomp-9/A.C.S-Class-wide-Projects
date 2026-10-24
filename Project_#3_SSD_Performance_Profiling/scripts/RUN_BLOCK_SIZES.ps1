$root = Split-Path $PSScriptRoot -Parent
Set-Location "$root\scratch"

if (!(Test-Path "project3_test.bin")) {
    throw "SSD test file missing!"
}

$out = "$root\data\raw"
$sizes = @("4k","16k","32k","64k","128k","256k")
$patterns = @("randread","randwrite","read","write")

foreach ($bs in $sizes) {
    foreach ($rw in $patterns) {
        for ($trial = 1; $trial -le 3; $trial++) {

            $name = "block_${bs}_${rw}_trial$trial"
            Write-Host "Running $name"

            & fio --name=$name `
                --filename=project3_test.bin `
                --allow_file_create=0 `
                --size=8G `
                --rw=$rw `
                --bs=$bs `
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
}

Write-Host "All block-size experiments finished!"
