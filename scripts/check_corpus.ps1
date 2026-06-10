$files = @(
    "corpus\public-domain\hong-lou-meng\hlm.json",
    "corpus\user\jl.json",
    "corpus\user\lz.json"
)

$totalSlices = 0
$allPassed = $true

foreach ($file in $files) {
    Write-Host "`n=== $file ===" -ForegroundColor Cyan
    $raw = Get-Content $file -Raw -Encoding UTF8
    $data = $raw | ConvertFrom-Json
    Write-Host "Slice count: $($data.Count)"
    
    foreach ($item in $data) {
        $len = $item.text.Length
        $totalSlices++
        if ($len -ge 450 -and $len -le 550) {
            Write-Host "  OK   $($item.slice_id): ${len} chars" -ForegroundColor Green
        } else {
            Write-Host "  FAIL $($item.slice_id): ${len} chars" -ForegroundColor Red
            $allPassed = $false
        }
    }
}

Write-Host "`n=== Summary ===" -ForegroundColor Cyan
Write-Host "Total slices: $totalSlices"
if ($allPassed) {
    Write-Host "ALL PASSED" -ForegroundColor Green
} else {
    Write-Host "SOME FAILED (need 450-550 chars)" -ForegroundColor Red
}
