$root = Split-Path $PSScriptRoot -Parent
Set-Location "$root\scratch"

if (!(Test-Path "project3_test.bin")) {
    throw "SSD test file missing!"
}

if ((Get-Item "project3_test.bin").Length -ne 8589934592) {
    throw "Unexpected test file size!"
}

$sizes = @("1G", "4G", "8G")

foreach ($size in $sizes) {
    for ($trial = 1; $trial -le 3; $trial++) {

        $name = "working_${size}_trial$trial"
        Write-Host "Running $name"

        & fio --name=$name `
            --filename=project3_test.bin `
            --allow_file_create=0 `
            --size=$size `
            --rw=randread `
            --bs=4k `
            --ioengine=windowsaio `
            --direct=1 `
            --iodepth=16 `
            --numjobs=1 `
            --time_based=1 `
            --runtime=10 `
            --ramp_time=2 `
            --eta=never `
            --output-format=json `
            --output="..\data\raw\$name.json"

        if ($LASTEXITCODE -ne 0) {
            throw "FIO failed on $name"
        }
    }
}

Write-Host "Working-set experiments finished!"
