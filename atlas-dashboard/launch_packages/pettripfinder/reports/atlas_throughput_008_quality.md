# ATLAS-THROUGHPUT-008 — correctness

| assertion | result |
|---|---|
| HANDOFF_BYTE_IDENTICAL | True |
| LIVE_MARKETS_PRESERVED | True |
| PAID_PROVIDER_CALLS | 0 |
| REAL_DEPLOYMENTS | 0 |
| STALE_PARENT_ACTIVATION | 0 |
| UNCHANGED_MARKET_REBUILDS | 0 |
| UNEXPECTED_CHANGES | 0 |
| UNEXPECTED_MARKET_REMOVAL | 0 |
| UNEXPECTED_PROFILE_REMOVAL | 0 |
| UNEXPECTED_ROUTE_REMOVAL | 0 |
| VERIFICATION_PASSED | False |
| WRONG_ARTIFACT_DEPLOY | 0 |

Every release also carried its own diff, and no release changed a market its intended delta did not name.

## Stale parent

{
 "host_untouched": true,
 "outcome": "ACTIVATION_REFUSED",
 "refusals": [
  "STALE_PARENT: authorized parent 637e228fc74392b6 but f7c64621936b6df0 is live"
 ],
 "scenario": "release 1's candidate re-offered after releases 2 and 3 moved live"
}
