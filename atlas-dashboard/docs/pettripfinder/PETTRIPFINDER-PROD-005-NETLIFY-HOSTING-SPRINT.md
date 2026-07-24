# PETTRIPFINDER-PROD-005 — Netlify Hosting-Configuration Sprint Plan

**Type:** planning / architecture authority (binding for PROD-005).
**Status:** DRAFT for operator review. No hosting configuration implemented; no
Netlify account, project, CLI, login, deploy, domain, DNS, TLS, or credential
created or touched by this document.

**Document location note.** The repository's architecture docs live flat under
`docs/` (WGE authorities) with ADRs in `docs/architecture/decisions/`. PetTripFinder
is a *product built on* the Website Generation Engine, so its operational/hosting
docs are grouped under a new `docs/pettripfinder/` subdirectory (the path the
operator specified). This file is the only repository write authorized by this
task, and it is not committed here.

---

## 0. Binding context (verified at preflight)

| Fact | Value |
|---|---|
| Git baseline | `5b9dc04654be309803df4a7e386d8e3e90668921` (main == origin/main) |
| Committed policy package | 14 records · schema 1.1 · SHA-256 `d836b5d9b3f86a6c5c8141264ea16f611c02a5f7014896bfee0098e82be0cd0c` |
| Approved RC | `data/deployment_staging/pettripfinder/prod004_columbus_rc1/` (gitignored) |
| RC bundle SHA-256 | `56c57bb83044ffedb8276306f517a68b5d25a8f09acb64c78ca68f02f7fd0099` |
| RC contents | 209 files · 200 HTML · 14 hotel routes · 0 held · 29/29 gates pass |
| Production domain | `https://pettripfinder.com` (apex, canonical); `www` → apex redirect |
| Provider | **Netlify** (operator decision) — prebuilt static upload, not Git-run build |
| Existing hosting authority | **None** (no config/CI/DNS/deploy exists) |
| Generator | `python scripts/generate_pettripfinder_columbus_site.py --output <dir>` (deterministic, committed inputs only) |
| Publishable root | `site/` |

**Operating model (PROD-005 first release):** generate + validate locally from
committed authority → assemble a deploy bundle → **manual** prebuilt deploy to
Netlify (`--dir`), *not* Netlify-run Python builds; keep the current external
registrar/DNS initially, changing only the minimum website records; apex is
canonical, `www`→apex; immutable Netlify deploy history for rollback; Git-driven
continuous deployment is a **later, separately authorized** phase.

---

## 1. Stage breakdown (gated)

| Stage | Purpose | Remote/irreversible? | Approval gate before it |
|---|---|---|---|
| **A — Local Netlify authority** | Repo-side config + assembler + tests | No (local, tracked files) | — (implementation stage; commit-gated as usual) |
| **B — Netlify project provisioning** | Create remote project, no domain | Yes (remote, reversible) | CLI install/auth **and** project creation |
| **C — Non-production preview deploy** | Upload bundle to a preview URL, no domain | Yes (remote, reversible) | Preview deploy |
| **D — Domain & DNS preflight** | Prepare `pettripfinder.com`, **no DNS change** | No (read-only inventory) | — (read-only; DNS write gated in E) |
| **E — Controlled production publish** | Promote deploy + attach domain + minimal DNS | Yes (**irreversible-ish**: DNS/TLS) | Attach-domain, each DNS record, production publish (each separate) |
| **F — Post-launch & rollback readiness** | Verify + establish rollback point | No (verify/monitor) | Rollback (if triggered) |

**No step combines DNS cutover with the initial artifact upload.** The bundle is
uploaded and fully validated on a Netlify preview URL (Stage C) *before* any DNS
record is touched (Stage E). Domain attachment, each DNS change, and the
production promotion are independent, separately-approved actions.

---

## 2. Stage A — Local Netlify authority (repo-side)

Create and validate all repository-side hosting config with **no** remote change.

### Proposed repository files to ADD (Stage A)
Authored + versioned in the repo (the source of truth); a deterministic assembler
copies the Netlify control files into the freshly-generated `site/`:
- `deploy/netlify/_headers` — security + cache header rules (source of truth).
- `deploy/netlify/_redirects` — `www`→apex + any host/HTTPS rules.
- `deploy/netlify/netlify.toml` — publish dir + headers/redirects (belt-and-suspenders; see §4).
- `deploy/netlify/preview_headers_overlay` — a preview-only `X-Robots-Tag: noindex` overlay applied ONLY to non-production deploys.
- `scripts/pettripfinder/assemble_netlify_bundle.py` — **deterministic assembler**: (1) run the generator into an isolated dir, (2) copy `deploy/netlify/{_headers,_redirects,netlify.toml}` into the bundle, (3) run the PROD-004 release gates + a forbidden-file scan, (4) emit `deployment_manifest.json` with git commit + package hash + bundle hash. Fails closed on any gate.
- `docs/pettripfinder/DEPLOYMENT_RUNBOOK.md` — the step-by-step operator+Claude runbook (mirrors Stages B–F).
- `docs/pettripfinder/CREDENTIALS_CONTRACT.md` — **names only**: `NETLIFY_AUTH_TOKEN`, `NETLIFY_SITE_ID` (values never stored; env-var only).
- `tests/pettripfinder/test_prod005_netlify_config.py` — config + bundle-integrity tests (§8).

**Authoritative-source rule.** `_headers`/`_redirects`/`netlify.toml` **originate in
`deploy/netlify/` (tracked, tested)** and enter `site/` **only** via the assembler.
Hand-edited files inside a generated release directory are never authority — the
assembler regenerates `site/` deterministically and re-injects the control files,
so a manual edit in a release dir is overwritten and a test asserts the assembled
bundle's control files byte-match the tracked sources.

### Stage-A deliverables
netlify.toml · `_headers` · `_redirects` · security-header policy (§5) ·
cache-control policy (§6) · custom 404 behavior (see §4) · deterministic bundle
assembler + verifier · deployment runbook · credential contract (names only) ·
config + bundle-integrity tests.

**Expected files added/changed in Stage A:** the 8 files above (all additive; no
change to the generator, the committed package, or existing tests except adding
the new test file). If a 404 page or asset-versioning change is required, it would
touch the generator — flagged as a **decision** in Stage A, not assumed.

---

## 3. Stage B — Netlify project provisioning (remote, no domain)

Create the remote project **without** attaching `pettripfinder.com` and without
publishing the production domain.

**Operator-controlled actions:** create/select the Netlify account/team; create
**one** PetTripFinder project; choose a stable project name (e.g. `pettripfinder-columbus`);
authenticate via browser login **or** a scoped personal-access token; record the
generated **site ID** securely (password manager / secret store, never Git);
verify team/ownership; **disable automatic Git production deploys**; keep manual
deploy control.

**Exact information Claude will need from the operator afterward (never the values):**
- confirmation the project exists + its **project name**;
- the **Netlify site ID** provided **as the env var `NETLIFY_SITE_ID`** (Claude reads the env var; the operator never pastes the value into chat);
- a scoped **`NETLIFY_AUTH_TOKEN`** provided as an env var;
- confirmation that Git auto-deploy is disabled.

Claude never logs in, never installs the CLI, and never sees token/site-ID values —
they arrive only as environment variables at the authorized implementation stage.

---

## 4. Stage C — Non-production preview deployment (remote, no domain)

Upload the reviewed static bundle to a **preview** Netlify URL; do not connect the
production domain.

**Requirements:** deploy the exact reviewed RC **or** a freshly regenerated
byte-identical bundle (verify bundle SHA-256 == `56c57bb8…` first); use a
**non-production** deploy (`netlify deploy` without `--prod`, or a draft/branch
deploy); record the Netlify **deploy ID** + immutable deploy URL; run the full
route/content/link/metadata/desktop/mobile smoke suite (§8) against the preview
URL; apply the **preview `X-Robots-Tag: noindex`** overlay so the preview is not
indexed; confirm no `pettripfinder.com` attachment, no runtime/credential leakage.

**Approval gate before proceeding to Stage D/E:** operator reviews the preview URL
+ the smoke-test report and explicitly approves the exact deploy ID for eventual
production promotion.

---

## 5. Stage D — Custom domain & DNS preflight (NO DNS change)

Prepare `pettripfinder.com` **without** changing live DNS.

**Requirements:** identify the current **registrar** and **authoritative DNS
provider** (fail closed if not confidently identified); inventory **all** existing
DNS records; explicitly preserve **MX / SPF / DKIM / DMARC / domain-verification /
unrelated-subdomain** records; obtain the **exact Netlify targets** for apex and
`www` from the project's domain settings (placeholders until B exists — commonly
apex `ALIAS/ANAME → apex-loadbalancer.netlify.com` or `A → 75.2.60.5`, and `www
CNAME → <site>.netlify.app`; **to be confirmed from Netlify at implementation, not
assumed**); define apex as primary, `www`→apex redirect; verify TLS prerequisites
(Netlify auto-provisions Let's Encrypt once DNS resolves); reduce TTL **only** if
useful and explicitly approved; produce the before/after DNS worksheet (§7) with
exact rollback values. **No DNS write in this stage.**

---

## 6. Stage E — Controlled production publish (irreversible-class)

Publish the already-approved immutable deploy and connect the domain, in this
exact order — each remote write is a separate approved action:
1. Verify git commit `5b9dc04`, package hash `d836b5d9…`, RC/bundle hash `56c57bb8…`, route count 14, all release gates.
2. Confirm the exact immutable Netlify **deploy ID** selected for production (from Stage C).
3. Capture existing DNS state (snapshot).
4. **Attach** the custom domain in Netlify.
5. Apply **only** the reviewed DNS changes (apex + `www`; nothing else).
6. Confirm TLS (certificate issued, HTTPS valid).
7. Confirm apex serves + `www` redirects once to apex.
8. Run post-publish smoke tests (§8, production host).
9. Confirm sitemap + robots use the apex domain.
10. Confirm all 14 verified hotel profiles reachable.
11. Confirm all 11 held hotels absent (incl. Drury Plaza → 404).
12. Record deploy ID + timestamps + hashes into the production verification report.
13. Stop and report.

**Production publish + each DNS write require an explicit, separate final human
authorization immediately before the remote write.** No earlier approval carries
forward.

---

## 7. Stage F — Post-launch observation & rollback readiness

Save the production deploy ID + URL; preserve the RC + deployment manifests;
verify Netlify deploy history exists (now a real rollback point); document restore
of the previous deploy. **First-release rollback** = restore the last known-good
Netlify deploy **when one exists**, otherwise **detach the domain / restore prior
DNS** (there is no prior website version on first launch). Monitor HTTP status,
TLS, canonical URLs, sitemap, robots, broken links, and key routes. Define
immediate rollback triggers (below). Separate genuine launch defects from later
SEO/content improvements.

**Immediate rollback triggers:** any held hotel (esp. Drury Plaza) reachable; a
fabricated/incorrect policy fact or flattened tiered fee rendered; a wrong/absent
evidence link; broken navigation / missing CSS; a credential or runtime path in
output; the live committed-package hash ≠ `d836b5d9…`; TLS failure or redirect loop.

---

## 8. Netlify configuration design

| Concern | Design |
|---|---|
| Publish directory | `site/` (the prebuilt bundle) |
| Local production build command | `python scripts/generate_pettripfinder_columbus_site.py --output <bundle>/site` then the assembler injects `deploy/netlify/*` |
| Manual **preview** deploy | `netlify deploy --dir site --site "$NETLIFY_SITE_ID"` (no `--prod`) |
| Manual **production** deploy | `netlify deploy --prod --dir site --site "$NETLIFY_SITE_ID"` (after all gates + final approval) |
| Project linking | via `NETLIFY_SITE_ID` env var (not a committed `.netlify/state.json`) |
| Site ID / token storage | env vars only (`NETLIFY_SITE_ID`, `NETLIFY_AUTH_TOKEN`); never in Git/logs/tests |
| Headers | `_headers` (see §9) |
| Redirects | `_redirects`: `www`→apex 301 force; host/HTTPS normalized by Netlify |
| 404 handling | a committed `404.html` in `site/` (Netlify serves it for unknown paths). **Decision:** generate a branded 404 in the generator, or add a static one via the assembler — flagged for Stage A. Held-hotel routes simply don't exist → 404. |
| Cache rules | §10 |
| HTML caching | `Cache-Control: public, max-age=0, must-revalidate` (atomic deploys; instant updates) |
| Immutable asset caching | **NOT yet** — `styles.css` is not content-hashed, so long-immutable caching is unsafe; short-cache w/ revalidation until asset versioning is added (later) |
| sitemap/robots content types | Netlify serves `.xml` as `application/xml` and `.txt` as `text/plain` (confirmed by preview smoke test) |
| `www`→apex | 301 redirect (apex stays canonical) |
| HTTP→HTTPS | Netlify forces HTTPS once TLS is issued |
| Trailing slash | directory routes (`/route/`) already end in `/`; keep Netlify "pretty URLs" default (no forced strip) |
| `/go/` routes | remain `noindex`; `robots.txt` `Disallow: /go/` already in the bundle |
| Directory listings | Netlify never lists directories (serves `index.html` or 404) |
| Forbidden-file protection | only `site/` is uploaded (`--dir site`); `data/`, `tests/`, `scripts/`, `.git`, patch files, `launch_packages/` never ship. A Stage-A test asserts the assembled bundle contains no `.py`/`.git`/`data/`/repo internals. |

All identifiers (`NETLIFY_SITE_ID`, `<site>.netlify.app`, deploy IDs, DNS targets)
are **placeholders** until the project exists; none are fabricated here.

---

## 9. Security-header plan (`_headers`)

Conservative baseline. **CSP starts REPORT-ONLY** — the bundle has **194 pages with
inline `<script>`** (the `/go/` client redirects + the home analytics/filter script)
and **14 pages with inline `style=""` attributes**, so an enforced strict CSP
(`script-src 'self'`) would silently break the redirects and interactivity.

| Header | Initial value | Notes / validation |
|---|---|---|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | enable **after** HTTPS confirmed; add `preload` only later, deliberately |
| `X-Content-Type-Options` | `nosniff` | safe immediately |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | safe immediately |
| `Permissions-Policy` | `geolocation=(), camera=(), microphone=(), payment=()` | deny features the site never uses |
| `X-Frame-Options` | `DENY` | plus `frame-ancestors 'none'` when CSP is enforced |
| Cross-Origin-Opener-Policy | `same-origin` | validate no popups/embeds break (site has none) |
| `Content-Security-Policy` | **Report-Only** first: `default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'` with `Content-Security-Policy-Report-Only` | outbound `<a href>` evidence/official links are **not** CSP-restricted. Enforcement requires first hashing/nonce-ing or externalizing the 194 inline scripts + removing the 14 inline `style=""` (a generator change) — a **separate follow-up**, not this sprint. |
| `X-Robots-Tag` | `noindex` **on preview deploys only** | never on production; production must be indexable |

**CSP must not break:** local CSS (`style-src 'self'` — served same-origin ✓),
internal navigation (same-origin ✓), outbound official-policy links (`<a>` not
restricted ✓), `/go/` redirects (inline script — allowed via report-only /
`'unsafe-inline'` initially ✓), inline `style=""` (allowed via `'unsafe-inline'`
initially ✓). Strict enforcement is gated on a tested follow-up.

---

## 10. Cache & release policy

- **HTML:** `max-age=0, must-revalidate` — atomic Netlify deploys serve consistent HTML; updates are instant.
- **XML (sitemap) / robots.txt:** short cache (e.g. `max-age=300`) so changes propagate quickly.
- **Static assets (`styles.css`, monogram-less):** filenames are **not** hash-versioned → **not** safe for immutable long-cache; use `max-age=3600, must-revalidate` until asset content-hashing is added (later generator change).
- **Cache purge after rollback:** Netlify serves each deploy from immutable storage and switches atomically — rolling back to a prior deploy needs **no manual edge purge**. (If an external CDN is ever placed in front, a purge step is required — not in this model.)
- **Atomic deploys:** each Netlify deploy is immutable + all-or-nothing.
- **Release naming:** `prod-005-columbus-<git7>-<pkg8>-<bundle8>` (e.g. `prod-005-columbus-5b9dc04-d836b5d9-56c57bb8`).
- **Manifest retention:** keep `deployment_manifest.json` + the production verification report per release.
- **RC→deploy traceability — every release maps to:** git commit · policy-package hash · RC bundle hash · Netlify deploy ID · production verification report.

---

## 11. Domain & DNS plan

Primary `pettripfinder.com`; alias `www.pettripfinder.com` → apex (**canonical stays
apex**, never `www`). **Keep the current external DNS provider**; change only the
minimum website records. **Do not assume Netlify DNS.**

### DNS inventory worksheet (fill during Stage D; do not change during preflight)
| Type | Name | Current value | Current TTL | Proposed value | Proposed TTL | Reason | Rollback value | Approval |
|---|---|---|---|---|---|---|---|---|
| A / ALIAS | `pettripfinder.com` | *(inventory)* | *(inv.)* | *(Netlify apex target)* | *(e.g. 300 during cutover)* | point apex at Netlify | *(current value)* | ☐ |
| CNAME | `www` | *(inventory)* | *(inv.)* | `<site>.netlify.app` | *(300)* | www→Netlify (then redirect to apex) | *(current value)* | ☐ |
| MX | `pettripfinder.com` | *(inventory — PRESERVE)* | — | **unchanged** | — | email | — | n/a |
| TXT (SPF/DKIM/DMARC/verify) | *(various — PRESERVE)* | *(inventory)* | — | **unchanged** | — | email auth / verification | — | n/a |
| *(other subdomains)* | *(inventory — PRESERVE unless intended)* | — | — | **unchanged** | — | — | — | n/a |

**Safeguards:** never touch MX/SPF/DKIM/DMARC/verification/unrelated subdomains;
only apex + `www` change; record exact rollback values before any write; lower TTL
only if approved, to shorten cutover risk.

---

## 12. Test & acceptance matrix

**Repository configuration (Stage A, automated):** `netlify.toml`/`_headers`/`_redirects`
parse; **no secrets** anywhere in tracked config/tests; publish root is `site/`;
bundle assembly is **deterministic** (two assemblies byte-identical); **forbidden
files excluded** (no `.py`/`data/`/`tests/`/`.git`/patches in `site/`); header +
redirect rules match the design; assembled control files byte-match `deploy/netlify/` sources.

**Preview deployment (Stage C, manual + scripted smoke):** immutable deploy URL
reachable; **no production-domain attachment**; **noindex** on preview; 14 verified
hotel profiles; 11 held hotels absent (Drury Plaza 404); exact evidence links;
CSS/assets load; desktop + mobile render; **no console errors**.

**Production domain (Stage E, post-publish):** apex resolves; `www` redirects
**once** to apex; HTTPS valid; **no redirect loop**; canonical host = apex; sitemap
host = apex; robots `Sitemap:` host = apex; 404 behavior correct; all key routes
expected status; `/go/` routes `noindex`.

**Rollback (Stage F):** previous deploy identifiable; rollback procedure
executable; DNS restoration values recorded; post-rollback verification defined.

---

## 13. Human approval gates (each separate; none implied by an earlier one)

Separate explicit approval is required before: (1) installing/authenticating the
Netlify CLI; (2) creating the Netlify project; (3) creating a preview deploy;
(4) attaching `pettripfinder.com`; (5) modifying **any** DNS record; (6) publishing
to production; (7) rolling back production; (8) enabling continuous deployment.

---

## 14. Time, cost & risk

| Stage | Est. effort | Operator actions | Claude/code actions | Remote irreversible? |
|---|---|---|---|---|
| A — local authority | 0.5–1 day | review/approve config | write config + assembler + tests | No |
| B — provisioning | 15–30 min | create account/project, provide env vars | none remote | Yes (reversible) |
| C — preview deploy | 30–60 min | approve deploy | assemble + deploy + smoke tests | Yes (reversible) |
| D — DNS preflight | 30–60 min | share registrar/DNS access/read | inventory + worksheet | No |
| E — production publish | 30–90 min + DNS/TLS propagation | final auth per remote write | promote + attach + minimal DNS + verify | **Yes (DNS/TLS)** |
| F — post-launch | ongoing | monitor | verification report + monitors | No |

**Failure modes & recovery:** DNS misconfig → revert to recorded rollback values;
TLS not issued → wait for propagation / re-verify DNS; a held hotel appears →
immediate rollback (detach domain / restore deploy); CSP breakage → CSP is
report-only, so no breakage (enforcement deferred); wrong deploy promoted →
promote the correct immutable deploy ID.

**Cost:** Netlify has a free tier that typically covers a small static pilot, **but
pricing/limits are the provider's and can change** — do not assert free-or-paid
without verified account state at implementation. Custom domain + TLS via Netlify
are standard; registrar/DNS costs are the operator's existing arrangement. No
charge is incurred by this plan.

---

## 15. Recommended first implementation stage

**PROD-005A — Implement Local Netlify Deployment Authority** (Stage A): author
`netlify.toml` + `_headers` + `_redirects` + the deterministic bundle assembler +
the config/bundle-integrity tests + the runbook + the credential contract — all
local, tracked, testable, with **no** remote action. This is the safe, reversible
foundation; every remote stage (B–F) is separately gated afterward.
