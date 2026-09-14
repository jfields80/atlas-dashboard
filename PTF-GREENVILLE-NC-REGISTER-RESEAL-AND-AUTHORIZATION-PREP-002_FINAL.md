# PTF-GREENVILLE-NC-REGISTER-RESEAL-AND-AUTHORIZATION-PREP-002 — FINAL

Status: **AWAITING_FOUNDER_AUTHORIZATION**. Nothing deployed.

Branch `worker/ptf-greenville-nc-market-001`.

| Step | Commit |
|---|---|
| Merge of the Fayetteville-live parent | fc6d5126 (ec764bef) |
| Registration | 89fbaa9e |
| Classification + readiness | 2073d3a7 |

## Phase 1 — current verified live (read from host + canonical records, 2026-09-14T02:04:02Z; rechecked 02:09:30Z and 02:28:29Z)

| field | value |
|---|---|
| host deployment id | 6aa750d8fa36419d3c84ecbc (ready) |
| live release digest | e6c669cf14980efc44eaee4799e060e28888cac510498310595fcd125939f965 |
| source commit | c4db424ba6b4351158708889c803643be9edc2a3 |
| sitemap digest | 3cb2fc6d20d6fda185345d8d25b30e5489099959b48c516dfa6ae79668b9a99f |
| markets / profiles / routes | 19 / 1221 / 1438 |
| rollback target | 6aa60a3e018fd6b1b9a40450 |
| Fayetteville live | YES (30 routes) |
| Greenville / Jacksonville live | NO / NO (0 routes each) |
| verification | VERIFIED |

## Phases 2–3 — source-ready inputs and the stale shadow package

Report: `greenville_nc_registration_preflight_002.json`.

- **Source-ready counts:** 75 discovered, 28 census, 8 PF, 5 no-pets, 13 resolved, 15 unresolved. Every census identity is in the partition exactly once.
- **Source-ready diff:** 0 non-Greenville paths. The tree was clean.
- **Shadow package `pkg-greenville-nc-a5f2010468463650`:**
  - It is `SHADOW_UNTIL_REGISTERED`, and its seal still verifies.
  - The registered package store holds no copy of it, and the receipt store holds no eligible receipt for it.
  - Its parent differs from the current live state on every rule-N field.
  - **Production-selectable: NO.** It is kept as history only.

## Phase 4 — registration

- **Inputs carried unchanged:** census hotel and non-admitted rows, the market document, the partition and the four shard files. Each is identical to the source-ready staged copy. The policy package and census differ only in note / status text.
- **Lane:** generic `register` then `seal --work-order`. The contract was derived by `release_contracts`, with 0 disagreements. `build_global_authority --check` is clean.
- **Regression V2 against base ec764bef:** `COMPOSITE_FRESH_MARKET_DATA_ONLY`. All 58 paths are accounted for: 15 market-local, 13 registration, 30 derived, 0 shared, 0 unknown.
- **Checks:** 15/15 PASS. Full regression required: NO. Broad requested / run / remote: 0 / 0 / 0. Unchanged markets rebuilt: 0.
- **Registration to AUTHORIZATION_READY:** 2 min 26 s.

## Phases 5–6 — final package + FAST

- **Package:** `pkg-greenville-nc-f2113468ddfb4b06`, digest sha256:f2113468ddfb4b0622164d854f18e29118126e26c9014d498d4f64aec83a476c. Reproducible: YES.
- **Build input key:** sha256:2f8e4d18c2f34a87e508f14d190e0dccbf9371016da274c87010d8cf48e385d2
- **Intended delta digest:** sha256:05f353e06f0977f8b702e86165a17d34ef099f04ccf717c231cd24a679a4258b
- **Validation receipt:** sha256:db6453c5fac75a0bc091d0c84216d5480e675e08e7a4246b34a9f613caad0d6d. FAST 15/15 PASS, 0 unknown, 0 failed.

## Phases 7–10 — candidate

- **Parent recheck:** the parent was unchanged immediately before composition and again after the builds. STALE_PARENT = NO.
- **Candidate digest:** 5009281dac4e2289563aeed8efcd40568311994781794894cef41e6fe872b7be. This is also the deployment artifact digest.
- **Reproducibility:** a second, independent worktree build produced the same digest. FINAL_CANDIDATE_REPRODUCIBLE = YES.
- **Sitemap digest:** 00163f47164155a4886c9d3fcecd0c2af7b80f61e704731ddd17783dfe2b262f
- **Partition:** resolved generically from the contract. No assembler edit.
- **Parent → candidate:** 19 / 1221 / 1438 becomes 20 / 1229 / 1449.
  - Greenville adds 8 profiles, 11 sitemap routes and 10 release-index routes.
  - Removed: 0. Unexpected market, profile, route or file changes: 0.
  - All 19 live markets keep identical profile counts.
- **Non-participation:** Jacksonville, Atlanta, Outer Banks, Boone–Blowing Rock, Pinehurst and Detroit do not participate and have 0 files in their namespaces.

## Phase 11 — founder packet

`greenville_nc_founder_authorization_packet_002.json` records:
- all full digests;
- the holds by class;
- corridor coverage and requested-area coverage;
- rollback to 6aa750d8fa36419d3c84ecbc / e6c669cf14980efc44eaee4799e060e28888cac510498310595fcd125939f965.

## Phase 12 — hard stop

No authorization was written. Nothing was deployed. Factory code changed: NO.
