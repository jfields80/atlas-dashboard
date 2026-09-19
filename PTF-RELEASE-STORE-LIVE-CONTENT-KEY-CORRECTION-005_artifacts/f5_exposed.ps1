$mods = @(
 'tests/pettripfinder/test_toledo_oh_promotion_002.py',
 'tests/pettripfinder/test_regression_delta_001.py',
 'tests/pettripfinder/test_registration_data_only_001.py',
 'tests/pettripfinder/test_nashville_tn_launch_005.py',
 'tests/pettripfinder/test_lexington_ky_launch_006.py',
 'tests/pettripfinder/test_composite_fresh_market_001.py',
 'tests/pettripfinder/test_atlas_throughput_007.py',
 'tests/pettripfinder/test_atlas_throughput_006.py',
 'tests/pettripfinder/test_atlas_throughput_005.py',
 'tests/pettripfinder/test_atlas_throughput_004.py',
 'tests/pettripfinder/test_atlas_throughput_003.py',
 'tests/pettripfinder/test_atlas_throughput_002.py'
)
$runs = @(
 @{ name = 'A_fix';    cwd = 'C:\Atlas-PTF-Release-Audit\atlas-dashboard' },
 @{ name = 'B_repair'; cwd = 'C:\t\rfd3a\atlas-dashboard' }
)
foreach ($r in $runs) {
  $xml = "C:\t\mig4\f5_$($r.name).xml"
  $log = "C:\t\mig4\f5_$($r.name).log"
  $start = Get-Date
  Push-Location $r.cwd
  & python -m pytest @mods -q -p no:cacheprovider -o junit_family=xunit2 "--junitxml=$xml" *> $log
  $code = $LASTEXITCODE
  Pop-Location
  "$($r.name) exit=$code seconds=$([math]::Round(((Get-Date) - $start).TotalSeconds,1))" | Out-File -Append -Encoding utf8 C:\t\mig4\f5_exposed_status.txt
}
"DONE" | Out-File -Append -Encoding utf8 C:\t\mig4\f5_exposed_status.txt
