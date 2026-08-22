# PetTripFinder — Measurement Contract

**PTF-MEASUREMENT-001 (Phase 1 + 1b).** This document is the authority for how
the site measures itself and how a booking action may carry an affiliate
destination. Code owns the mechanics (`scripts/pettripfinder/measurement.py`,
`scripts/pettripfinder/affiliate_destinations.py`,
`scripts/pettripfinder/commercial_actions.py`); this document owns the rules.

**Current state (committed):** measurement is **disabled**; no analytics
provider is configured; no affiliate provider is enrolled; no affiliate
destination exists. Generation with this state produces the same bytes it
produced before the measurement layer existed (composed production bundle
`8ea6131e9fe8689fc23d3a362ae12ffaa2155c687737c6f5fcde03b5a22c42b8`).

---

## 1. Event contract

Defined in `commercial_actions.py` and unchanged by this work order.

| Event | Emitted by | Status |
|---|---|---|
| `page_view` | every content page, on load | enabled path only |
| `listing_profile_view` | hotel profile pages, after `page_view` | enabled path only |
| `policy_comparison_view` | policy-comparison pages, after `page_view` | enabled path only |
| `listing_impression` | reserved | not emitted |
| `filter_applied` | hotel category toolbar | live (no-op without a provider) |
| `outbound_official_click` | `/go/…/official-website/` | live (no-op without a provider) |
| `outbound_booking_click` | `/go/…/booking/` | live (no-op without a provider) |
| `directions_click` | `/go/…/directions/` | live (no-op without a provider) |
| `phone_click` | `/go/…/call/` | live (no-op without a provider) |
| `report_change_click` | `/go/…/report-change/` | live (no-op without a provider) |

`EVENT_TYPES` is frozen. Adding an event is a contract change with its own
work order.

## 2. Dimensions

`EVENT_DIMENSIONS`: `market`, `page_type`, `route`, `listing_id`,
`listing_state`, `category`, `corridor`, `action_position`,
`verification_status`, `affiliate_provider`, **`build_id`** (new).

`EVENT_OPTIONAL_DIMENSIONS`: `filter_value` (carried by `filter_applied` since
AES-SITE-001; now declared).

Rules:

- Every required key is present on an enabled-path event, `""` when not
  applicable.
- `build_id` is emitted **only when a build supplies it**, i.e. when
  measurement is enabled. A disabled build's `/go/` pages are byte-identical to
  the ones generated before `build_id` existed.
- `affiliate_provider` is `""` unless the page's destination is a resolved
  affiliate destination (§7).

### `build_id`

The first 12 hex characters of the owning market's committed policy-package
SHA-256 — the `policy_package.expected_sha256` its release contract pins (the
package file's own hash when no contract exists; `""` for a market with no
package). Global pages use the anchor market's id.

It is **market-local** on purpose: adding another market to the composed
bundle moves no byte of this market's pages, which is an existing
assembler invariant (`test_adding_a_market_moves_no_earlier_market_owned_byte`).
It carries no clock and reads no environment.

## 3. The provider-neutral hook

`window.ptfAnalytics.emit(name, dims)` forwards to
`window.__ptfAnalyticsProvider(name, dims)` when that is a function and swallows
every error. **Nothing in the repository assigns `__ptfAnalyticsProvider` while
measurement is disabled.** No vendor name, script, host, or identifier appears
in code; the provider is configuration (§4).

## 4. Configuration — `deploy/netlify/measurement.json`

Schema `ptf-measurement-config/1.0`, validated fail-closed by
`measurement.load_measurement_config` (unknown keys, wrong types, and
`enabled: true` without a usable provider all refuse the build).

```
enabled            false
provider.kind      none | beacon_script
provider.script_src, event_endpoint   https URLs whose host is in allowed_hosts
provider.site_domain
provider.allowed_hosts                 bare lowercase hostnames
build_id.source    market_policy_package_sha256 (length 12)
go_pages.adapter   inline_send_beacon
```

**Disabled-by-default rule.** `enabled: false` / `kind: none` is the committed
state. In that state `inject_page_measurement` returns its input unchanged,
`provider_head_snippet`, `provider_adapter_js` and `inline_beacon_provider_js`
return `""`, and the generator skips the measurement pass entirely. The
`measurement.no_external_script_when_disabled` gate proves no page loads an
external script.

## 5. The enabled path (dormant)

When a later release sets `enabled: true` with a `beacon_script` provider:

- **Content pages** get, once, before `</head>`: a deferred vendor
  `<script src>` from the configured host; an inline adapter assigning
  `window.__ptfAnalyticsProvider` that delivers via `navigator.sendBeacon`
  (keepalive `fetch` fallback); the shared `ptfAnalytics` interface; then the
  page's events (§1). Both tags carry `data-ptf-measurement="page"`, which the
  `measurement.snippet_once_per_content_page` gate counts.
- **`/go/` pages** get an **inline** adapter placed before `ANALYTICS_JS`.
  They load **no external script**.

### The `/go/` `sendBeacon` requirement

A `/go/` page runs `ptfAnalytics.emit(...)` and then `location.replace(...)`
on the next statement. A deferred or async vendor script is not initialised by
then; a conventional tag would lose essentially every outbound click. The
enabled path therefore never depends on a vendor script being ready on a `/go/`
page: the inline adapter hands the event to `navigator.sendBeacon`, which the
browser delivers after navigation has begun. Any provider chosen must accept
a `sendBeacon` POST at its event endpoint.

## 6. Privacy

Preference: a **cookieless** provider that needs no consent banner and
collects no personal data. No identifier in any dimension is personal. The
`Content-Security-Policy-Report-Only` header stays report-only; enabling a
provider adds its host to `script-src` and `connect-src` in
`deploy/netlify/headers.production` and `headers.preview` as part of the
enabling release (§9), never before.

## 7. Affiliate destination doctrine

An affiliate destination is **authority**, not configuration.

- **Provider registry** — `deploy/netlify/affiliate_providers.json`
  (`ptf-affiliate-providers/1.0`): `provider_id`, `display_name`,
  `allowed_destination_hosts`, `disclosure`, `rel` (fixed:
  `nofollow sponsored noopener`), `enrolled`. A listed provider is not an
  enrolled one; `enrolled` is `false` until the business holds an approved
  program. **Currently: 0 providers.**
- **Per-market shard** —
  `launch_packages/pettripfinder/markets/authority/<market_id>/affiliate_destinations.json`
  (`ptf-affiliate-destinations/1.0`), keyed by the policy package's
  `identity_key`: `provider_id`, `program_id`, `destination_url`,
  `official_url_at_mapping`, `approved_by`, `approved_at`, `status`.
  **Currently: 8 shards, 0 rows.** The shard rule applies — a market writer
  edits its own shard only; the cross-market view is derived in memory and
  there is no generated global file.
- **Identity binding** — a row resolves only for the seed row whose
  normalized name is its `identity_key`, in its own market, and only while the
  seed row's `website_url` still equals `official_url_at_mapping`. A property
  that changed its official URL refuses its mapping until a human re-approves
  it.
- **Host allowlisting** — `destination_url` must be `https`, credential-free,
  and on a host (or subdomain of a host) in the provider's allowlist.
- **Founder approval** — `approved_by` and `approved_at` are a human
  attestation. The build never fills them in; a row without them is refused.
  Nobody signs in another person's name.
- **Fail closed** — unknown provider, unenrolled provider, unlisted host,
  unknown identity, drifted official URL, market mismatch, malformed URL,
  duplicate row: each **raises** and stops the build. Only "no mapping" falls
  back, and that fallback is today's behaviour: the official URL,
  `affiliate_provider` empty, `rel="noopener"`.
- **Resolved destinations** reach the redirect layer as
  `AffiliateDestination(provider_id, destination_url, rel)`; the booking
  interstitial's fallback link then carries `rel="nofollow sponsored noopener"`.

### The booking CTA is a separate decision

`/go/<id>/booking/` pages are built for every verified pet-friendly hotel but
**no approved renderer links to them**. Adding a booking CTA to the
founder-approved hotel profile design, and making the commission disclosure
conditional on a destination existing, are a founder/design decision outside
this contract. Populating a shard does not create a visible link.

## 8. Search Console doctrine

Code readiness is complete: every page self-canonicalises to the apex,
`sitemap.xml` is the site (gated), `robots.txt` names it, production headers
carry no `noindex`. Verification is a **business task**: prefer a Domain
property verified by a DNS TXT record at the registrar (no bundle change); an
HTML meta tag or verification file is acceptable only if DNS access is
unavailable (each moves the bundle hash). Submit `/sitemap.xml` after
verification and again after the first multi-market deployment. No Search
Console property exists today.

## 9. Enable / disable release procedure

Enabling measurement is a **content release** with its own bundle hash.

1. Business: choose a cookieless provider meeting §5/§6; obtain `script_src`,
   `event_endpoint`, `site_domain`.
2. Edit `deploy/netlify/measurement.json`: `enabled: true`,
   `provider.kind: beacon_script`, the three values, `allowed_hosts`.
3. Append the provider host to `script-src` and `connect-src` in
   `deploy/netlify/headers.production` and `headers.preview`.
4. Rebuild: `python -m scripts.pettripfinder.assemble_production_site --output <short path>`.
   Expect a **new** bundle hash; every content page carries one snippet; every
   `/go/` page carries the inline adapter and `build_id`.
5. Re-stamp `deploy/netlify/global_deployment_manifest.json` from the bundle
   manifest (`global_deployment.write_manifest`); it pins
   `measurement.config_sha256` alongside the control files.
6. A deployment work order authorizes **that** `bundle_sha256` and **that**
   commit. `deployment_authorized` stays `false` until it does.

Disabling reverses steps 2–3 and repeats 4–6.

## 10. Gates

Global (`global_deployment.REQUIRED_GLOBAL_GATES`) and single-market:

| Gate | Passes when |
|---|---|
| `measurement.config_valid` | the committed config validates |
| `measurement.snippet_once_per_content_page` | each content page carries its block exactly once (enabled) / never (disabled) |
| `measurement.no_external_script_when_disabled` | no `<script src="http…">` anywhere while disabled |
| `affiliate.destinations_allowlisted` | every mapped destination host is in its provider's allowlist |
| `affiliate.identity_bound` | every mapped row has a seed row whose `website_url` still matches |
| `affiliate.no_destination_without_enrolled_provider` | no row names an unknown or unenrolled provider |

All six pass vacuously in the committed state.

## 11. What this contract does not claim

No provider is configured. No program is enrolled. No destination exists. No
Search Console property exists. No Netlify Analytics is enabled. The live
production site is unchanged by Phase 1 + 1b.
