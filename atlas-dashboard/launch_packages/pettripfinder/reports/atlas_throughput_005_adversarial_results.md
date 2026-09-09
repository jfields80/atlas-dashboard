# ATLAS-THROUGHPUT-005 — adversarial results

`tests/pettripfinder/test_atlas_throughput_005.py`: **52 tests, 0 failing** (15.4 s). The cases that need a
real whole-site compose are proved once by the committed pilot and asserted from its recorded run; every case
about the coordinator's rules runs directly against synthetic releases, because those rules must hold for
markets this repository has not built yet.

## Crash matrix

- **10_corrupted_after_authorization** — {"outcome": "ACTIVATION_REFUSED", "refusals": ["CANDIDATE_CORRUPT: staged bundle hashes 75f5ab2f046275cd, manifest says 437439f275b2f276"], "restored": true}
- **1_crash_before_staging** — {"live_unchanged": true}
- **2_crash_after_staging** — {"host_calls": 0, "live_unchanged": true}
- **3_crash_after_authorization** — {"host_calls": 0, "live_unchanged": true}
- **4_activation_timeout** — {"deployments": 1, "outcome": "ACTIVATION_UNKNOWN", "reconciled_action": "REPAIR_RECORD -- the activation landed; write the record, do not redeploy", "recorded_as_live": false}
- **5_local_write_failed_after_success** — {"action": "REPAIR_RECORD -- the activation landed; write the record, do not redeploy", "host_has_activation": true, "second_deploy_avoided": true}
- **8_duplicate_activate_is_idempotent** — {"deployments": 1, "idempotent_replay": true}
- **9_duplicate_authorization** — {"same_authorization_id": true, "same_candidate": true}
