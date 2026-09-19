$exposed = @(
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
 @{ name = 'focused'; mods = @('tests/pettripfinder/test_release_factory_bounded_repair_002.py') },
 @{ name = 'exposed'; mods = $exposed }
)
New-Item -ItemType Directory -Force C:\t\mig6 | Out-Null
Push-Location C:\t\int6\atlas-dashboard
foreach ($r in $runs) {
  $start = Get-Date
  & python -m pytest @($r.mods) -q -p no:cacheprovider -o junit_family=xunit2 "--junitxml=C:\t\mig6\i6_$($r.name).xml" *> "C:\t\mig6\i6_$($r.name).log"
  "$($r.name) exit=$LASTEXITCODE seconds=$([math]::Round(((Get-Date) - $start).TotalSeconds,1))" | Out-File -Append -Encoding utf8 C:\t\mig6\i6_status.txt
}
Pop-Location
"DONE" | Out-File -Append -Encoding utf8 C:\t\mig6\i6_status.txt
