# PTF-BOONE-BLOWING-ROCK-NC-REGISTER-RESEAL-AND-AUTHORIZATION-PREP-002 — FINAL

**STATUS: AWAITING_FOUNDER_AUTHORIZATION.** Boone – Blowing Rock is #21 in the founder's new release order.
Nothing was deployed, no authorization was created, and the production gate was not activated.

Packet: `atlas-dashboard/launch_packages/pettripfinder/markets/reports/boone_blowing_rock_nc_founder_authorization_packet_002.json`

## Current verified live (parent)

| Field | Value |
|---|---|
| Host deployment | `6aa75f87aebd8377ccd67304` (Netlify published, ready) |
| Live release digest | `5009281dac4e2289563aeed8efcd40568311994781794894cef41e6fe872b7be` |
| Source commit | `2073d3a7f7490d9192d230e271aab1d50c3316ef` (merged here from `595bfeeb`) |
| Sitemap digest | `00163f47164155a4886c9d3fcecd0c2af7b80f61e704731ddd17783dfe2b262f` |
| Markets / profiles / routes | 20 / 1229 / 1449 |
| Rollback target of the parent | `6aa750d8fa36419d3c84ecbc` |
| Verification | VERIFIED at 03:01:57Z, 03:07:40Z and 03:31:07Z |

The live participants include Greenville and Fayetteville. The queued markets have 0 live routes: Boone, Jacksonville, Atlanta, Outer Banks, Pinehurst, Hickory and Detroit.

## Boone source inputs (verified unchanged)

| Measure | Value |
|---|---|
| Discovered / census | 161 / 44 |
| Pet-friendly / no-pets | 11 / 5 |
| Resolved / unresolved | 16 / 28 |

- **Accounting:** each identity is accounted for exactly once.
- **Banner Elk / Sugar / Beech exclusion:** holds. No census hotel is in 28604 or Avery County. 27 rows are OUTSIDE with the `banner-elk-sugar-beech-nc` reason; 2 more Banner Elk-ZIP rows are NON_LODGING cabins.
- **Shared-reader holds:** preserved, and the shared reader is unchanged. The 1850 Hotel, Windmoor, Blowing Rock Manor, Hemlock Inn, Rhode's Motor Lodge and The Inn at Crestwood all remain AWAITING_POLICY_OBSERVATION.
- **Carry-over into the registered paths:** census hotels and non-admitted rows, the market document, the partition and the four shard files are identical to the source-ready copies. The census and policy package differ only in note/status text.

## Stale shadow package

`pkg-boone-blowing-rock-nc-f96555872b51866d` is NOT production-selectable:
- its zone is SHADOW_UNTIL_REGISTERED;
- it is absent from `markets/packages` and has no eligible receipt;
- its parent is the Asheville-era release, so rule N fails it.

It is recorded as superseded for final-release purposes. The historical files are kept.

## Registration (against the Greenville-live parent)

| Item | Value |
|---|---|
| Change class | COMPOSITE_FRESH_MARKET_DATA_ONLY (mechanical, not forced) |
| Changed paths | 73 accounted / 73, unknown 0 |
| Proofs | 15/15 PASS (change set, market-local zone, discovery config, registration input, identity resolutions, participation, release contract, build closure, derived globals, sealed package, FAST receipt, expected release, identity routes, market-state pin, release integrity) |
| Broad regression | local requested 0, local run 0, remote required 0 |
| Unchanged markets rebuilt | 0 |
| REGISTRATION_TO_AUTH_READY | 2 min 55 s from the first registration write (2 min 19 s from `register`) |

## Final package

| Item | Value |
|---|---|
| Package | `pkg-boone-blowing-rock-nc-c3376def8d1effa6` |
| Package digest | `sha256:c3376def8d1effa66198c70d6b30bb081daf1bec52f85f3530d2b0edf1f03ea4` |
| Build input key | `sha256:11839e15c9a16926aacfaf08c7023b3646e67058dc57666cb23aab1e38c31604` |
| Intended delta digest | `sha256:707e92cd18708dd63cdad2e2b459b98bf538370d37c89c4249c191a6e84c9606` |
| Validation receipt | `sha256:c6118c0240a3c5d7d45cf55f22c8a1a802b973d203c8d4c5adc4c21b73860124` |
| FAST | 15/15 PASS, 0 unknown, 0 failed |
| Reproducible | YES: sealed twice in-process, and again in a clean checkout (below) |

## Final candidate

| Item | Value |
|---|---|
| Candidate / deployment artifact digest | `fd9749799dd8e7c715ada0dc7b6a29806f825a05864c2cc772804e2204e0bca2` (builds a and b identical) |
| Sitemap digest | `f6f0a27a8762719bdb7d02a9c572bd7ef647640e2f2aa1c82125594507656962` |
| Parent → candidate | 20 / 1229 / 1449 → **21 / 1240 / 1464** |
| Boone profiles added | 11 |
| Boone sitemap routes added | 15 |
| Boone release-index routes added | 14 |
| Removed markets / profiles / routes | 0 / 0 / 0 |
| Unexpected market / profile / route / file changes | 0 / 0 / 0 / 0 |

- **Why the sitemap adds one more route than the release index:** the extra sitemap route is `/pet-friendly-hotels/boone-blowing-rock-nc/policy-comparison/`, which the release index does not count.
- **What changed on disk:** every other file is byte-identical to the live artifact. The only additions are 15 files in Boone's namespace and 55 `/go/` interstitials; the only changed file is `sitemap.xml`.
- **Live markets:** all 20 are preserved at identical profile counts. The named ones are Greenville, Fayetteville, Asheville, Wilmington, Triad, Charlotte, Raleigh, Nashville, Lexington and Toledo.
- **Queued markets:** none participates, and none has a file in its namespace (Jacksonville, Atlanta, Outer Banks, Pinehurst, Hickory, Detroit).

## Line endings

- **Discovery config:** it has no `eol` attribute, so a clean checkout writes it with CRLF. It is not a package dependency input.
- **Clean-checkout reseal:** a clean worktree at `17421f78` rebuilt the package to the identical digest `c3376def…03ea4`, using the same source sha and seal time. A plain reseal changes only `created_from_source_sha`, `sealed_at` and the derived id. The shared writer writes the file with CRLF in the working copy, and its LF-normalised bytes equal the committed blob.
- **Candidate artifacts:** builds a and b are byte-identical file for file.
- No correction was needed.

## Rollback

Rollback deployment `6aa75f87aebd8377ccd67304`, release digest `5009281dac4e2289563aeed8efcd40568311994781794894cef41e6fe872b7be` (Greenville-live).

## Hard stop

Stopped before founder authorization, production-gate activation and host deployment.
