<#
PTF new-market bootstrap -- the factory lineage contract (PTF-RELEASE-FACTORY-PRODUCTION-MERGE-AUTHORIZATION-006).

    powershell -NoProfile -ExecutionPolicy Bypass -File bootstrap_new_market.ps1 `
        -Market memphis-tn -WorkOrder PTF-MEMPHIS-TN-HARDENED-V2-SOURCE-READY-001 [-DryRun]

What it guarantees:
  1. CURRENT_LIVE_SOURCE_COMMIT is resolved MECHANICALLY by the repaired resolver
     (release_index live-source) from every ref's deployment records, with the served
     sitemap hashed against the live record. origin/main is never used: it is reported
     stale and ignored.
  2. The new market branch starts from a commit that contains BOTH current live and the
     release-factory repair:
       - live contains the factory ref  -> start at the live commit (a later launch already
                                            carries the factory);
       - the factory ref contains live  -> start at the factory ref;
       - neither                        -> STOP: live and factory lineages diverged; integrate
                                            them under their own order first.
  3. The worktree path is short (C:\Atlas-<market>), which the FAST work dirs require.
Nothing is deployed, registered or authorized by this script.
#>
param(
    [Parameter(Mandatory = $true)][string]$Market,
    [Parameter(Mandatory = $true)][string]$WorkOrder,
    [string]$Repo = 'C:\Atlas-PTF-Release-Audit',
    [string]$FactoryRef = 'origin/worker/ptf-release-factory-integration-006',
    [string]$Branch = '',
    [string]$Worktree = '',
    [switch]$DryRun
)
$ErrorActionPreference = 'Stop'
if (-not $Branch)   { $Branch = "worker/ptf-$Market-market-001" }
if (-not $Worktree) { $Worktree = "C:\Atlas-$Market" }

function Git-Ok([string[]]$GitArgs) {
    & git -C $Repo @GitArgs
    if ($LASTEXITCODE -ne 0) { throw "git $($GitArgs -join ' ') failed ($LASTEXITCODE)" }
}

# 0. Current refs.
Git-Ok @('fetch', '--prune', 'origin')
$factory = (& git -C $Repo rev-parse --verify "$FactoryRef^{commit}").Trim()
if ($LASTEXITCODE -ne 0) { throw "factory ref $FactoryRef not found" }

# 1. Resolve CURRENT_LIVE_SOURCE_COMMIT with the factory's own (repaired) resolver.
$tag = [guid]::NewGuid().ToString('N').Substring(0, 8)
$probe = "C:\t\livesrc-$tag"
$out = "C:\t\livesrc-$tag.json"
Git-Ok @('worktree', 'add', '--detach', $probe, $factory)
try {
    $live = $null
    foreach ($attempt in 1, 2) {           # the host check fails closed; one retry for a dropped connection
        Push-Location "$probe\atlas-dashboard"
        & python -m scripts.pettripfinder.release_index live-source --verify-host --json --out $out | Out-Null
        $rc = $LASTEXITCODE
        Pop-Location
        $live = Get-Content $out -Raw | ConvertFrom-Json
        if ($rc -eq 0 -and $live.RESOLVED -eq 'YES' -and $live.host_verified -eq $true) { break }
        Start-Sleep -Seconds 20
    }
} finally {
    & git -C $Repo worktree remove --force $probe | Out-Null
}
if ($live.RESOLVED -ne 'YES' -or $live.host_verified -ne $true) {
    throw "CURRENT LIVE NOT VERIFIED: $($live.problems -join '; ')"
}
$liveCommit = $live.CURRENT_LIVE_SOURCE_COMMIT

# 2. Choose the base: a commit that contains live AND the factory repair.
& git -C $Repo merge-base --is-ancestor $factory $liveCommit
$liveHasFactory = ($LASTEXITCODE -eq 0)
& git -C $Repo merge-base --is-ancestor $liveCommit $factory
$factoryHasLive = ($LASTEXITCODE -eq 0)
if ($liveHasFactory)     { $base = $liveCommit; $why = 'live already contains the factory' }
elseif ($factoryHasLive) { $base = $factory;    $why = 'the factory ref contains live' }
else { throw "STOP: live $($liveCommit.Substring(0,12)) and factory $($factory.Substring(0,12)) have diverged" }

$summary = [ordered]@{
    market                     = $Market
    work_order                 = $WorkOrder
    CURRENT_LIVE_SOURCE_COMMIT = $liveCommit
    live_deploy_id             = $live.live_deploy_id
    live_markets               = @($live.participating_markets).Count
    live_profiles              = $live.total_profiles
    live_routes                = $live.sitemap_route_count
    host_verified              = $live.host_verified
    origin_main_stale_ignored  = $live.origin_main_stale
    factory_ref                = "$FactoryRef @ $($factory.Substring(0,12))"
    base                       = $base
    base_rule                  = $why
    branch                     = $Branch
    worktree                   = $Worktree
    dry_run                    = [bool]$DryRun
}
$summary | ConvertTo-Json | Write-Output
Remove-Item $out -ErrorAction SilentlyContinue
if ($DryRun) { return }

# 3. The market branch and its short-path worktree.
if (Test-Path $Worktree) { throw "$Worktree already exists" }
Git-Ok @('worktree', 'add', '-b', $Branch, $Worktree, $base)
Write-Output "BOOTSTRAPPED $Branch at $($base.Substring(0,12)) in $Worktree"
