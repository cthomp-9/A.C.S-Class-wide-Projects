$root = Split-Path $PSScriptRoot -Parent
Set-Location "$root\scratch"

if (!(Test-Path "project3_test.bin")) {
    throw "SSD test file missing!"
}

if ((Get-Item "project3_test.bin").Length -ne 8589934592) {
    throw "Unexpected test file size!"
}

$out = "..\data\raw"

function Run-Test($name, $rw, $mix, $qd) {
    Write-Host "Running $name"

    & fio --name=$name `
        --filename=project3_test.bin `
        --allow_file_create=0 `
        --size=8G `
        --rw=$rw `
        --rwmixread=$mix `
        --bs=4k `
        --ioengine=windowsaio `
        --direct=1 `
        --iodepth=$qd `
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

# Read/write ratios at QD=16
$mixes = @(100, 0, 70, 50)

foreach ($mix in $mixes) {
    $rw = if ($mix -eq 100) {
        "randread"
    } elseif ($mix -eq 0) {
        "randwrite"
    } else {
        "randrw"
    }

    for ($trial=1; $trial -le 3; $trial++) {
        Run-Test "mix_${mix}_trial$trial" $rw $mix 16
    }
}

# Queue-depth sweep: 4k random reads
$depths = @(1,2,4,8,16,32,64,128,256)

foreach ($qd in $depths) {
    for ($trial=1; $trial -le 3; $trial++) {
        Run-Test "qd_${qd}_trial$trial" "randread" 100 $qd
    }
}

Write-Host "All mix and QD experiments finished!"
