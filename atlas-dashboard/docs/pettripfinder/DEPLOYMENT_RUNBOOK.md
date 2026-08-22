# PetTripFinder Columbus — Deployment Runbook (Netlify)

**PETTRIPFINDER-PROD-005A.** This runbook governs the local assembly of the
deploy bundle (Stage A, implemented) and documents the **future** remote stages
(B–F). Every command in the "future" sections is a **future command only** — do
**not** execute any of them in Stage A. Each remote stage has its own explicit
human approval gate; no earlier approval carries forward.

Authorities:
- Sprint plan: `docs/pettripfinder/PETTRIPFINDER-PROD-005-NETLIFY-HOSTING-SPRINT.md`
- Release gates: `deploy/netlify/release_contracts/<market_id>.json` — **one
  contract per market** (PTF-PER-MARKET-RELEASE-CONTRACTS-001). The former
  single `deploy/netlify/release_contract.json` was Columbus-calibrated and has
  been removed; see §1.6.
- Credentials (names only): `docs/pettripfinder/CREDENTIALS_CONTRACT.md`

> **Stale figures.** The record counts, package hash, file counts, and held-hotel
> figures quoted in §0, §1.4, §6 and §7 below are PROD-005A-era (Columbus at 14
> published hotels). They are **not** the current authority. The current expected
> figures for every market live in that market's release contract and are printed
> by `python -m scripts.pettripfinder.release_contracts`.

---

## 0. Prerequisites

- Repository at the released commit (`main == origin/main`), regression green.
- Committed policy package present and unchanged: 14 records, schema `1.1`,
  SHA-256 `d836b5d9b3f86a6c5c8141264ea16f611c02a5f7014896bfee0098e82be0cd0c`
  (verify with `python scripts/pettripfinder/export_hotel_policy_facts.py --check`).
- Python environment per `docs/development/environment.md` (Pydantic v1).
- **No** Netlify CLI, account, login, or credentials are required for Stage A.
- The Netlify CLI, an account/project, and credentials are required only from
  Stage B onward, and only after their own approval gates.

---

## 1. Stage A — Local assembly (implemented; safe, reversible, no remote action)

### 1.1 Assemble the preview bundle

```sh
python scripts/pettripfinder/assemble_netlify_bundle.py \
  --context preview \
  --market columbus-oh \
  --output data/deployment_staging/pettripfinder/prod005a_preview
```

### 1.2 Assemble the production bundle

```sh
python scripts/pettripfinder/assemble_netlify_bundle.py \
  --context production \
  --market columbus-oh \
  --output data/deployment_staging/pettripfinder/prod005a_production
```

`--market` is explicit and selects the release contract. It defaults to
`columbus-oh` (this repository's named production market) so existing invocations
keep their meaning; state it anyway, because the market is what the bundle *is*.

Both outputs are under the gitignored `data/` tree. The assembler makes **no**
network request, reads **no** credential, and never writes outside the requested
`--output` root.

### 1.3 Preview vs production context

The **only** intended difference between the two bundles is `site/_headers`:

- **preview** — includes `X-Robots-Tag: noindex, nofollow, noarchive` so a
  non-production preview deploy is never indexed.
- **production** — does **not** include that directive (the production site must
  be indexable).

All other bytes under `site/` are identical between contexts.

### 1.4 Expected output structure

```
<output>/
  site/                       ← the ONLY publishable directory (use with --dir)
    index.html, styles.css, hotel-profile.css, sitemap.xml, robots.txt, llms.txt
    about/  contact/  methodology/
    pet-friendly-hotels/   (14 verified hotel profiles + index + policy-comparison + dublin/)
    pet-friendly-parks/  pet-friendly-restaurants/  go/
    _headers                ← Netlify header rules (context-specific)
    _redirects              ← Netlify redirect rules (www → apex)
  deployment_manifest.json  ← reports live OUTSIDE site/ so they never publish
  file_hash_manifest.json
  route_inventory.json
  validation_report.json
```

Expected counts: **207 files** under `site/` (200 HTML + `styles.css`,
`hotel-profile.css`, `sitemap.xml`, `robots.txt`, `llms.txt`, `_headers`,
`_redirects`), **14** hotel-profile routes, **11** held hotels absent.

### 1.5 Release-gate review

`validation_report.json` records every gate in
`deploy/netlify/release_contracts/<market_id>.json` → `minimum_release_gates`.
Confirm `all_gates_pass: true`, `minimum_gates_missing: []`,
`failing_gates: {}`. Record `deployment_manifest.json → bundle_sha256` as the
release identity. The CLI `--dir` value is the **binding** publish source; only
`site/` is ever uploaded.

### 1.6 Per-market release contracts

Each market owns a complete, self-contained contract under
`deploy/netlify/release_contracts/`. There is no base file and no inheritance:
one market's edit cannot move another market's expectations, and an assembly is
refused outright if the contract's `market_id` is not the market being built.

Every contract is additionally gated against its own committed authority — the
market's identity census, policy package, exclusion registry, seed inventory,
corridor routes, and any reconciliation manifest it commits. Verify all of them
without building anything:

```sh
python -m scripts.pettripfinder.release_contracts
```

Current markets and their contracts:

| Market | Contract | Published | Confirmed / unresolved |
|---|---|---|---|
| `columbus-oh` | `release_contracts/columbus-oh.json` | 88 | no census committed |
| `cleveland-akron-canton-oh` | `release_contracts/cleveland-akron-canton-oh.json` | 19 | 188 / 161 |
| `dayton-oh` | `release_contracts/dayton-oh.json` | 33 | 129 / 90 |

**What a passing contract means.** It is a *structural* statement: that market's
package is internally consistent and safe to publish as a static bundle. It is
**not** a deployment authorization and it does **not** claim the market is
complete — Cleveland and Dayton pass with 161 and 90 identities still
unresolved. Every deploy in §§3–5 still needs its own separate approval gate.

---

## 2. Stage B — Netlify project provisioning *(future; approval-gated)*

**Approval gate B (separate):** installing/authenticating the CLI **and**
creating the Netlify project.

Operator actions (not Claude): create/select the Netlify account/team; create
**one** project (e.g. `pettripfinder-columbus`); authenticate via browser login
**or** a scoped personal-access token; record the generated **site ID** in a
secret store (never Git); **disable automatic Git production deploys** (this
pilot uses manual prebuilt deploys only); provide the credentials to the
environment as `NETLIFY_SITE_ID` and `NETLIFY_AUTH_TOKEN`.

### Future CLI installation approval gate
Do not install the Netlify CLI until Stage B is authorized. Installation is the
operator's action or an explicitly approved step.

### Future authentication approval gate
Do not run `netlify login` or use `NETLIFY_AUTH_TOKEN` until Stage B is
authorized.

### Project-linking procedure
Link at deploy time via the `NETLIFY_SITE_ID` env var passed to
`netlify deploy --site "$NETLIFY_SITE_ID"`. Do **not** create or commit
`.netlify/state.json`.

### Credential presence checks (no values)
See `docs/pettripfinder/CREDENTIALS_CONTRACT.md`. Confirm presence only; never
print a value.

---

## 3. Stage C — Non-production preview deploy *(future; approval-gated)*

**Approval gate C (separate):** creating a preview deploy.

1. Re-assemble the preview bundle (§1.1) and confirm `bundle_sha256` matches the
   reviewed release identity.
2. **Future preview command (do not run in Stage A):**

   ```sh
   netlify deploy --dir <preview-site-path> --site "$NETLIFY_SITE_ID" --no-build
   ```

   where `<preview-site-path>` is the assembled `…/prod005a_preview/site`
   directory. This is a **non-production** deploy (no `--prod`), no domain
   attached.
3. **Capture the immutable deploy ID** and the preview URL from the CLI output;
   record them in the release notes.
4. **No-domain preview validation:** confirm the preview URL is reachable, the
   preview is `noindex` (from `_headers`), all 14 verified hotel profiles load,
   all 11 held hotels 404 (incl. Drury Plaza), evidence links resolve, CSS/assets
   load, desktop + mobile render, and there are no console errors. Confirm no
   `pettripfinder.com` attachment and no credential/runtime leakage.
5. **Operator approves the exact deploy ID** for eventual production promotion.

---

## 4. Stage D — Custom domain & DNS preflight *(future; NO DNS change)*

Identify the registrar and authoritative DNS provider (fail closed if not
confidently identified); inventory **all** DNS records; explicitly preserve
MX/SPF/DKIM/DMARC/verification/unrelated-subdomain records; obtain the exact
Netlify apex + `www` targets from the project's domain settings; fill the DNS
worksheet in the sprint plan (§11) with before/after values and exact rollback
values. **No DNS write in this stage.**

---

## 5. Stage E — Controlled production publish *(future; irreversible-class)*

**Approval gates E (each separate, immediately before the write):** attach
domain; **each** DNS record; production publish.

Ordered sequence (each remote write separately authorized):
1. Verify commit, package hash, bundle hash, 14 routes, all gates.
2. Confirm the exact immutable deploy ID from Stage C.
3. Snapshot existing DNS.
4. Attach the custom domain in Netlify.
5. Apply **only** apex + `www` DNS changes (nothing else).
6. Confirm TLS issued (HTTPS valid).
7. Confirm apex serves and `www` redirects **once** to apex.
8. **Future production command (do not run in Stage A):**

   ```sh
   netlify deploy --prod --no-build --dir <production-site-path> --site "$NETLIFY_SITE_ID"
   ```

   where `<production-site-path>` is the assembled `…/prod005a_production/site`.
9. Post-publish verification (§6).
10. Record deploy ID + hashes into the production verification report. Stop.

### Immutable deploy ID capture
Record every deploy ID (preview and production). Netlify deploys are immutable
and atomic; the production deploy ID is the rollback target.

---

## 6. Post-publish verification *(future)*

- `https://pettripfinder.com/` → 200, canonical = apex.
- All 14 hotel routes → 200; each shows the exact `source_url` evidence link.
- `…/drury-plaza-hotel-columbus-downtown/` → **404** (held).
- `sitemap.xml` → 200, all `<loc>` under `https://pettripfinder.com`, no `/go/`,
  no held hotel; `robots.txt` → `Sitemap: https://pettripfinder.com/sitemap.xml`,
  `Disallow: /go/`.
- `www` → apex single 301; HTTPS valid; no redirect loop.
- Re-confirm committed package hash `d836b5d9…` and deployed `bundle_sha256`.
- **HSTS activation gate:** only after HTTPS is confirmed stable, enable
  `Strict-Transport-Security` in `headers.production` as a **separate reviewed
  change** (no preload; `includeSubDomains` only after its own review). Not part
  of Stage A.

---

## 7. Rollback procedure *(future)*

First release has no prior live version. Rollback = restore the last known-good
Netlify deploy **when one exists**, otherwise **detach the domain / restore prior
DNS** (from the Stage-D worksheet). Netlify atomic deploys mean **no manual cache
purge** is required. **Immediate rollback triggers:** any held hotel reachable;
a fabricated/incorrect policy fact or flattened tiered fee; a wrong/absent
evidence link; broken navigation / missing CSS; a credential or runtime path in
output; live package hash ≠ `d836b5d9…`; TLS failure or redirect loop.

---

## 8. Forbidden actions (Stage A)

Do **not**, in Stage A: install the Netlify CLI; authenticate; create or link a
Netlify project; create `.netlify/state.json`; create a preview or production
deploy; upload any file; call a Netlify API; attach a domain; change DNS or TLS;
publish; display or store any credential value; commit or push. Every command in
§§2–7 is a **future command only**.

---

## 9. Human approval checkpoints (summary)

| Gate | Before |
|---|---|
| B1 | Installing / authenticating the Netlify CLI |
| B2 | Creating the Netlify project |
| C | Creating a preview deploy |
| E1 | Attaching `pettripfinder.com` |
| E2 | **Each** DNS record change |
| E3 | Publishing to production |
| F | Rolling back production |
| — | Enabling continuous (Git) deployment |

---

## 10. Measurement (PTF-MEASUREMENT-001) — future enablement only

Authority: `docs/pettripfinder/MEASUREMENT_CONTRACT.md`. The committed
`deploy/netlify/measurement.json` is **disabled** (`enabled: false`,
`provider.kind: none`); in that state generation emits no provider script, no
`page_view`, no `build_id`, and the composed bundle hash does not move. The
global deployment manifest pins the config's SHA-256 (`measurement.config_sha256`)
and six measurement/affiliate gates alongside the control files.

Enabling measurement is its **own release** (contract §9): edit the config,
allow the provider host in `headers.production` / `headers.preview`, rebuild,
re-stamp the manifest, and authorize the **new** bundle hash under a deployment
work order. It is never folded into a deployment that was authorized against a
different hash. No provider is configured and no affiliate program is enrolled
today; Search Console verification, Netlify Analytics and affiliate enrollment
are external business tasks that change no byte here.

---

## 11. Launch participation (PTF-FIRST-MULTI-MARKET-PRODUCTION-DEPLOYMENT-046)

Source readiness and launch participation are two different questions.
`assemble_production_site.market_eligibility` answers the first from the
market's own authority (census, final partition, policy authority, minimum
published) and reports it as `assemblable`. The second is the founder's, and
it is recorded in **`deploy/netlify/launch_participation.json`**
(`ptf-launch-participation/1.0`, read by
`scripts/pettripfinder/launch_participation.py`):

| `launch_status` | Meaning | Joins the composed bundle |
|---|---|---|
| `FOUNDER_AUTHORIZED_FOR_LAUNCH` | source-ready and founder-authorized | **yes** (the only admitting status) |
| `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH` | passes every assembly condition; withheld by founder decision | no |
| `NOT_SOURCE_READY` | fails an assembly condition; no authorization could admit it | no |
| *(unlisted)* | reads as `UNLISTED`; never authorized | no, and the build fails |

Rules, all enforced by gates the global deployment manifest requires:

- Every registered market must carry a row
  (`global.launch_participation_explicit`), so a market can be neither
  silently excluded nor silently included.
- A status may not claim a readiness the source does not have
  (`global.launch_participation_agrees_with_source`).
- The record is pinned by SHA-256 in the global deployment manifest
  (`launch_participation.sha256`), and `verify_manifest` also checks that the
  set the record authorizes is the set the manifest says participated. A
  participation change is therefore a **different artifact** with a new bundle
  hash, exactly like a control-file or measurement-config change.
- Withdrawing a market here touches none of its authority: its release
  contract still verifies, its data is unchanged, and
  `assemble_netlify_bundle --market <id>` still builds it alone.

First multi-market launch (founder decision, 2026-08-22): Columbus, Cleveland,
Dayton, Milwaukee, Pittsburgh are `FOUNDER_AUTHORIZED_FOR_LAUNCH`; Indianapolis
(8 profiles, contract verifying) is
`SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH` on coverage grounds;
Cincinnati and Detroit are `NOT_SOURCE_READY`. Print the current record with
`python -m scripts.pettripfinder.launch_participation`.
