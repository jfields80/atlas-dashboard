# PTF-BOONE-BLOWING-ROCK-NC-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-003 — FINAL

**Boone – Blowing Rock, North Carolina is LIVE** as the 21st market. The founder-authorized candidate was deployed unchanged, and all 30 targeted live checks pass.

## Parent (pre-Boone Greenville-live)

| Field | Value |
|---|---|
| Host deployment | `6aa75f87aebd8377ccd67304` |
| Release digest | `5009281dac4e2289563aeed8efcd40568311994781794894cef41e6fe872b7be` |
| Source commit | `2073d3a7f7490d9192d230e271aab1d50c3316ef` |
| Sitemap digest | `00163f47164155a4886c9d3fcecd0c2af7b80f61e704731ddd17783dfe2b262f` |
| Markets / profiles / routes | 20 / 1229 / 1449 |
| Verification | VERIFIED; `STALE_PARENT = NO` at Phase 1 and again immediately before deploy |

## Authorization

- **Authorization id:** `ptf-auth-boone-blowing-rock-003-fd9749799dd8`
- **Scope:** `boone-blowing-rock-nc` only.
- **Bound digests, read in full from `boone_blowing_rock_nc_founder_authorization_packet_002.json`:**

| Bound item | Digest |
|---|---|
| Parent release | `5009281dac4e2289563aeed8efcd40568311994781794894cef41e6fe872b7be` |
| Boone package | `sha256:c3376def8d1effa66198c70d6b30bb081daf1bec52f85f3530d2b0edf1f03ea4` |
| Build input key | `sha256:11839e15c9a16926aacfaf08c7023b3646e67058dc57666cb23aab1e38c31604` |
| Intended delta | `sha256:707e92cd18708dd63cdad2e2b459b98bf538370d37c89c4249c191a6e84c9606` |
| Validation receipt | `sha256:c6118c0240a3c5d7d45cf55f22c8a1a802b973d203c8d4c5adc4c21b73860124` |
| Final candidate = deployment artifact | `fd9749799dd8e7c715ada0dc7b6a29806f825a05864c2cc772804e2204e0bca2` |
| Candidate sitemap | `f6f0a27a8762719bdb7d02a9c572bd7ef647640e2f2aa1c82125594507656962` |

- **Participation:** the one-row flip reproduced the exact participation bytes the candidate was composed under.
- **Holds:** the 28 unresolved rows and all holds were left untouched.
- **Gate:** it opened for `boone-blowing-rock-nc` only. Probes refused Jacksonville, Detroit, Atlanta, Outer Banks, Greenville, Fayetteville and an unnamed market. After verification the entry was consumed, the gate set to `ENABLED = NO`, and the allowlist emptied.

## Deploy

| Item | Value |
|---|---|
| Release operation | `ptf-auth-boone-blowing-rock-003-fd9749799dd8` |
| Host deployment | **`6aa76e5d940d5025e8262319`** |
| Command | `netlify deploy --prod --no-build --dir C:\t\bbr2a\site` |
| Deploy start / complete | 03:47:05Z / 03:47:52Z (46.6 s) |
| Byte check | the existing artifact was re-hashed before deploy and equals the authorized digest |
| After authorization | no build, no reassembly, no re-seal, no regeneration |

## Live verification — 30 / 30 PASS

- **Live release:** the live sitemap hashes to the authorized candidate. The host shows `6aa76e5d940d5025e8262319` as published and ready.
- **Boone pages:**
  - The hub, both corridor pages (Boone, Blowing Rock) and the policy-comparison page each return 200.
  - Three sampled profiles in each corridor return 200.
  - Boone has 11 live profiles and 15 live routes.
- **Routes:** all 1464 live routes return 200 (0 broken). The live route set equals the artifact's.
- **Delta:**
  - 15 routes added, all in Boone's namespace; 0 removed.
  - The release index counts 14. The only route it does not count is `/pet-friendly-hotels/boone-blowing-rock-nc/policy-comparison/`.
- **Totals:** 21 markets / 1240 profiles / 1464 routes.
- **Existing markets:** Greenville, Fayetteville, Asheville, Wilmington, Triad, Charlotte, Raleigh, Nashville, Lexington and Toledo are all still live. All 20 prior fragments are route-identical to the parent.
- **Queued markets:** Jacksonville, Atlanta, Outer Banks, Pinehurst, Hickory and Detroit are non-live; each hub returns 404.
- **Unexpected changes:** 0 market, 0 profile, 0 route.
- **Rollback target:** `6aa75f87aebd8377ccd67304`, release `5009281dac4e2289563aeed8efcd40568311994781794894cef41e6fe872b7be` (Greenville-live).

**First verification run (recorded, not hidden):**
- It reported 27 / 30. Checks 22, 26 and 27 failed because my scratch verifier read the candidate manifest as the parent manifest (a doubled path substitution), so it compared 21 fragments with 20.
- In that run every host-side fact already matched: the sitemap hash equalled the authorized candidate, 1464 / 1464 routes returned 200, and only Boone routes differed from the parent.
- I pointed the verifier at the Greenville-live artifact and re-ran it with no change to the site: 30 / 30.
- No rollback was needed.

## Recorded live state

- **Canonical record:** `deploy/netlify/deployment_records/ptf-deploy-boone-blowing-rock-003-6aa76e5d940d5025e8262319.json`
- **Pin:** `tests/pettripfinder/pins/deployment_state.json`, live block
- **Verification receipt:** `markets/reports/boone_blowing_rock_nc_live_verification_003.json`

The live-state reader now returns:
- **Deploy:** `6aa76e5d940d5025e8262319`
- **Release:** `fd9749799dd8e7c715ada0dc7b6a29806f825a05864c2cc772804e2204e0bca2`
- **Sitemap:** `f6f0a27a8762719bdb7d02a9c572bd7ef647640e2f2aa1c82125594507656962`
- **Totals:** 21 / 1240 / 1464
- **Rollback:** `6aa75f87aebd8377ccd67304`
- **Problems:** none

## Performance

| Measure | Value |
|---|---|
| REGISTRATION_TO_AUTH_READY | 2 min 55 s (order 002) |
| FOUNDER_AUTHORIZATION_PROCESSING | 4.7 s |
| FINAL_PARENT_CHECK | 4.7 s (plus a 6.0 s byte check) |
| HOST_DEPLOYMENT | 46.6 s |
| LIVE_VERIFICATION | 28.5 s (the corrected run; the first run took 35.7 s) |
| AUTHORIZATION_TO_VERIFIED_LIVE | 3 min 43 s |
| Local broad regressions / remote broad jobs / unchanged live markets rebuilt | 0 / 0 / 0 |

No factory, classifier, assembler or shared-test code changed.
