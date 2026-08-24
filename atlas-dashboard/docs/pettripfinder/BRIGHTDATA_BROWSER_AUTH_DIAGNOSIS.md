# Bright Data Browser API — `407 wrong_password` diagnosis

**PTF-ST-LOUIS-PAID-ACQUISITION-002, resume attempt, 2026-08-23.** Names only.
This document contains **no credential values** and never will.

## Verdict

The Bright Data **Browser API** credential is refused by the vendor. The refusal
is not caused by anything in this repository, and it is not caused by the way
the credential is spelled in the environment. **The password stored in
`BRIGHTDATA_BROWSER_AUTH` is not the password Bright Data holds for zone
`scraping_browser1`.**

The work order stops here. No paid cohort ran, no property was fetched, nothing
was published, deployed, or registered.

## Preflight result

`scripts/pettripfinder/acquisition/lane_preflight.py`, run against live vendors:

| Lane | Presents | Verdict |
|---|---|---|
| Firecrawl | `FIRECRAWL_API_KEY` | **AUTHENTICATED** — 884 credits |
| Bright Data Browser | `BRIGHTDATA_BROWSER_AUTH` | **AUTHENTICATION_REJECTED** — `407 Auth Failed (wrong_password)` |
| Bright Data Web Unlocker | `brightdata` CLI stored token | **AUTHENTICATED** — zone `mcp_unlocker`, `us` exit |

Record: `launch_packages/pettripfinder/st_louis_mo_lane_preflight_002_resume.json`.
Byte-for-byte the same verdicts as the first attempt
(`st_louis_mo_lane_preflight_002.json`), which is what prompted the diagnosis
below rather than a second rotation request.

Account: **$15.81** available, $38.23 month-to-date. The probes moved neither
figure; the zone meter lags, so that is not a claim that they were free.

## What was ruled out, and how

Four candidate causes. Each was tested with a WebSocket upgrade against
`brd.superproxy.io:9222` carrying an explicitly constructed
`Authorization: Basic` header, so the exact bytes on the wire were chosen by the
test rather than by a URL parser. No browser session is opened, so the whole
sweep is a handful of TLS handshakes.

### 1. The operator's update never reached the process — RULED OUT

`BRIGHTDATA_BROWSER_AUTH` is defined in the Windows **user** environment
(`HKCU\Environment`), not machine-wide. A value updated after a long-lived
process starts would not reach that process. The value this session inherited
was compared for equality against the value currently stored in the registry:
**identical**. The session is probing the current credential.

### 2. Our URL layer mangles a reserved character — RULED OUT

`client.browser_endpoint` hands Playwright a raw `wss://user:password@host`
string and lets Playwright serialise it. This password contains a URL-reserved
character, and PAID-ACQUISITION-002 had already caught one live defect in
exactly that area (a `#` arriving as `%23`), so a percent-encoding mismatch was
the leading hypothesis.

Four spellings were sent — password as stored, percent-encoded, and each of
those again with the username country-pinned the way every capture path pins it.
**All four returned `407 wrong_password`.** The serialisation is exonerated: no
spelling of this secret is accepted, so no encoding fix can help.

### 3. A mangled paste — RULED OUT

A correct password can arrive wrong: copied out of a URL and left
percent-encoded, pasted with its surrounding quotes, or pasted as a whole
`user:password` pair into the password field alone. Every applicable transform
was tried against the real username. **All returned `407 wrong_password`.**

The stored secret is also not the `brightdata` CLI's own API token — that token
and this password are different lengths, so one was not pasted over the other.

### 4. The zone is dead, suspended, or misnamed — RULED OUT

Two independent controls.

**The zone opens sessions.** The `brightdata` CLI drives browser zones with its
own API token rather than the zone password:

```sh
brightdata browser open "https://geo.brdtest.com/welcome.txt" \
  --zone scraping_browser1 --country us --json
# -> {"status":200,...}
```

`scraping_browser1` returns **200**. A deliberately bogus zone name returns
**403**, so `--zone` is honoured and the 200 is really that zone. The zone is
alive, active, and usable by this account.

**Bright Data's own error discriminates.** The vendor does not answer
`wrong_password` to every bad credential — it names which half failed:

| Username sent | Vendor response |
|---|---|
| the real username | `407 Auth Failed (wrong_password)` |
| real customer, bogus zone | `407 Auth Failed (zone_not_found)` |
| bogus customer, real zone | `403 Auth Failed (wrong_customer_name)` |
| nonsense | `407 Auth Failed (zone_not_found)` |

Our customer **and** our zone both resolve. Only the secret is refused. This is
the fact that makes the verdict a statement rather than an inference.

## What the operator has to do

Read the password for zone **`scraping_browser1`** out of the Bright Data
control panel — *Proxies & Scraping Infrastructure* → `scraping_browser1` →
the zone's **Access parameters** — and set `BRIGHTDATA_BROWSER_AUTH` to

```
wss://brd-customer-<id>-zone-scraping_browser1:<zone password>@brd.superproxy.io:9222
```

Note that this is the **zone password**, which is not the account API token and
not the Web Unlocker's credential. If the control panel's password already
matches what is stored, rotate it there and take the new value; a rotation that
was begun and not completed leaves the console showing a password the edge has
not yet accepted.

Then re-run the preflight. It is the gate:

```sh
python -m scripts.pettripfinder.acquisition.lane_preflight \
  --label "PTF-ST-LOUIS-PAID-ACQUISITION-002 resume"
# exit 0 = all three lanes authenticated, paid cohort may start
```

## The gap this run exposed

Both preflight records are identical, and **neither can tell you whether the
credential changed between them.** "The operator rotated the password and it
still fails" and "the operator's rotation never landed" produce the same record.
Ruling that out cost a live registry comparison this session; a non-secret
fingerprint of the credential in the report — a truncated digest, which reveals
nothing — would let the second run state it as a fact. Recommended, not built:
the work order stops before code changes.

## Credential handling in this run

No credential value was printed, written, or committed. Every vendor string
passed through `client.redact` / `client.redact_truncate` before reaching output;
the `407` above kept the vendor's diagnosis and lost the secret, which is the
trade `redact_truncate` was added to make. The diagnostic probes reported only
transform **names** and HTTP status lines, and were run from the scratchpad
rather than the repository.
