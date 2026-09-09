"""PTF-NASHVILLE-TN-EVIDENCE-RECOVERY-003 -- the free static recapture lane.

Re-reads the recovery rows whose host the probe found reachable by a plain
first-party GET, and writes evidence that satisfies the DURABLE CAPTURE
CONTRACT: requested URL, final URL, lane, timestamp, identity signals, the raw
bytes on disk, the sha256 of those bytes, the byte length, the operative quote
and only contract-supported parsed facts.

The point of this order is that a byte count is not a capture. So the hash is
computed over the bytes this process actually received, in the same call that
took the quote, and the bytes are written to disk beside it. Nothing here
derives a hash from a URL, a quote, or anything else that could be produced
without fetching the page.

Identity is decided by the page, not by the row: ``marriott_surface.read_identity``
reads the page's own name, street, postal, locality and phone, and the row is
refused if they do not agree with the census identity being recovered.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from pathlib import Path

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.brightdata import marriott_surface as MS  # noqa: E402

WORK_ORDER = "PTF-NASHVILLE-TN-EVIDENCE-RECOVERY-003"
MARKET_ID = "nashville-tn"
RUN_ID = "nashville_tn_recovery_static_003"
LANE = "DIRECT_STATIC"

PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
COHORT = os.path.join(REPORTS, "nashville_tn_recovery_cohort_003.json")
ARTIFACTS = Path(_DASH) / "data" / "acquisition" / RUN_ID
OUT = os.path.join(REPORTS, "nashville_tn_static_recapture_003.json")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/128.0.0.0 Safari/537.36")

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _slug(text):
    return re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower()).strip("-")


def _text(html):
    body = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", " ", html)
    return _WS.sub(" ", _TAG.sub(" ", body)).strip()


def fetch(url, timeout=40):
    request = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    with urllib.request.urlopen(request, timeout=timeout,
                               context=ssl.create_default_context()) as response:
        raw = response.read()
        return raw, response.geturl(), response.status


def policy_block(text, window=600):
    """A bounded window around the page's own pet-policy statement, or "".

    Bounded on purpose: an unbounded page scrape lets a guest review, a
    neighbouring amenity list or an unrelated FAQ contribute to a quote that is
    supposed to be the operator's policy sentence.
    """
    match = re.search(r"(pets?\s+(are\s+)?(welcome|allowed|permitted|accepted|not\s+allowed)"
                      r"|pet\s+policy|pet\s+friendly|no\s+pets)", text, re.I)
    if not match:
        return ""
    start = max(0, match.start() - 120)
    return text[start:match.start() + window].strip()


def operative_quote(block, reading, *, kind):
    """The quote the GATE calls operative, chosen by the gate and not by this module.

    The reader offers several quotes for one policy block, and they are not
    equally strong: WoodSpring's page yields the bare amenity label
    "pet-friendly" alongside "Limit 2 dogs under 80 lbs per room. No cats.".
    Citing the first would be refused as AMENITY_CHIP_ONLY -- correctly -- while
    the second states the policy. So the candidates are handed to
    ``first_party_binding.classify_quote`` in order and the first it calls
    ELIGIBLE is used. If it calls none of them operative, that is recorded as
    the finding rather than papered over with the least-bad string.
    """
    from scripts.pettripfinder import first_party_binding as FPB

    candidates = [q for q in (
        getattr(reading, "both_species_quote", "") or "",
        getattr(reading, "dogs_only_quote", "") or "",
        getattr(reading, "pets_allowed_quote", "") or "",
        getattr(reading, "pets_refused_quote", "") or "",
        block,
    ) if str(q).strip()]
    tried = []
    for candidate in candidates:
        text = " ".join(str(candidate).split())[:400]
        verdict, why = FPB.classify_quote(text, kind=kind, context=block)
        tried.append(OrderedDict((("quote", text[:200]), ("verdict", verdict))))
        if verdict == FPB.ELIGIBLE:
            return text, tried
    return "", tried


def read_policy(block):
    """Only what the shared reader reads. This module parses nothing itself."""
    from scripts.pettripfinder.brightdata import policy_reading as PR
    reading = PR.parse(block)
    facts = OrderedDict()
    if reading.pets_allowed is not None:
        facts["pets_allowed"] = reading.pets_allowed
    for charge in (reading.charges or ()):
        if getattr(charge, "amount_minor", None) is not None:
            facts["pet_fee"] = int(charge.amount_minor)
            facts["fee_currency"] = "USD"
            if getattr(charge, "basis", ""):
                facts["fee_basis"] = charge.basis
            if getattr(charge, "scope", ""):
                facts["fee_scope"] = charge.scope
            break
    if reading.weight_value is not None:
        facts["weight_limit"] = float(reading.weight_value)
        facts["weight_limit_unit"] = getattr(reading, "weight_unit", "") or "lb"
    if reading.pet_count_limit is not None:
        facts["pet_count_limit"] = int(reading.pet_count_limit)
    kind = "no_pets" if reading.pets_allowed is False else "pet_friendly"
    quote, tried = operative_quote(block, reading, kind=kind)
    return facts, quote, tried


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hosts", default="www.woodspring.com",
                    help="comma-separated hosts the probe found reachable")
    ap.add_argument("--include-adjunct", action="store_true")
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)

    hosts = {h.strip() for h in args.hosts.split(",") if h.strip()}
    doc = _load(COHORT)
    targets = [(r, "RECOVERY_COHORT") for r in doc["recovery_cohort"]]
    if args.include_adjunct:
        targets += [(r, "ADJUNCT") for r in doc["adjunct"]]
    targets = [(r, kind) for r, kind in targets
               if r["official_url"].startswith("http")
               and r["official_url"].split("/")[2] in hosts]

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    rows, requests = [], 0
    started = time.monotonic()
    for row, kind in targets:
        url = row["official_url"]
        captured_at = datetime.now(timezone.utc).isoformat()
        try:
            raw, final_url, status = fetch(url)
            requests += 1
        except Exception as exc:                                    # noqa: BLE001
            rows.append(OrderedDict((
                ("identity_key", row["identity_key"]), ("membership", kind),
                ("requested_url", url), ("outcome", "CAPTURE_FAILED"),
                ("detail", "%s: %s" % (type(exc).__name__, exc))[:200],
                ("captured_at", captured_at))))
            requests += 1
            continue

        digest = hashlib.sha256(raw).hexdigest()
        slug = _slug(row["canonical_name"])
        artifact = ARTIFACTS / slug / "document.html"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_bytes(raw)

        html = raw.decode("utf-8", "replace")
        signals = MS.read_identity(html, final_url=final_url)
        text = _text(html)
        block = policy_block(text)
        facts, quote, tried = read_policy(block) if block else (OrderedDict(), "", [])

        page_postal = (getattr(signals, "postal_code", "") or "")[:5]
        page_street = (getattr(signals, "address_on_page", "") or "").lower()
        # A row HELD out of the registered census carries no census postal, so
        # the expectation falls back to what the SHADOW's own read of the same
        # page recorded. Comparing a page against nothing is not a check.
        expect_postal = ((row.get("postal_code") or "")
                         or (row.get("old_identity_signals") or {}).get("postal_code") or "")[:5]
        expect_street = (row.get("address")
                         or (row.get("old_identity_signals") or {}).get("address_on_page")
                         or "").lower()
        street_number = re.match(r"\s*(\d+)", expect_street)
        street_agrees = bool(street_number and page_street.strip().startswith(street_number.group(1)))
        identity_confirmed = bool(page_postal and page_postal == expect_postal and street_agrees)

        rows.append(OrderedDict((
            ("identity_key", row["identity_key"]),
            ("canonical_name", row["canonical_name"]),
            ("membership", kind),
            ("brand", row.get("brand") or ""),
            ("requested_url", url),
            ("final_url", final_url),
            ("http_status", status),
            ("capture_lane", LANE),
            ("run_id", RUN_ID),
            ("captured_at", captured_at),
            ("page_sha256", digest),
            ("byte_length", len(raw)),
            ("artifact_path", str(artifact.relative_to(Path(_DASH))).replace("\\", "/")),
            ("artifact_committed", False),
            ("identity_signals", OrderedDict((
                ("name_on_page", getattr(signals, "name_on_page", "") or ""),
                ("address_on_page", getattr(signals, "address_on_page", "") or ""),
                ("locality", getattr(signals, "locality", "") or ""),
                ("region", getattr(signals, "region", "") or ""),
                ("postal_code", getattr(signals, "postal_code", "") or ""),
                ("phone_on_page", getattr(signals, "phone_on_page", "") or ""),
                ("property_code_on_page", getattr(signals, "property_code", "") or ""),
                ("canonical_url", getattr(signals, "canonical_url", "") or ""),
            ))),
            ("identity_confirmed", identity_confirmed),
            ("identity_binding_method", "PAGE_POSTAL_AND_STREET_NUMBER"),
            ("surface", "bounded policy window in the page's own static markup"),
            ("policy_block", block[:800]),
            ("exact_quote", quote),
            ("quote_candidates_the_gate_judged", tried),
            ("extraction", facts),
            ("outcome", "VALID" if (identity_confirmed and quote) else
             "IDENTITY_MISMATCH" if not identity_confirmed else "SOURCE_SILENT"),
        )))

    elapsed = round(time.monotonic() - started, 2)
    out = OrderedDict((
        ("schema", "ptf-evidence-recapture/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("run_id", RUN_ID),
        ("lane", "DIRECT_STATIC (free first-party GET)"),
        ("paid_provider_calls", 0),
        ("usd_spent", 0.0),
        ("firecrawl_credits", 0),
        ("free_http_requests", requests),
        ("durable_capture_contract",
         "every row records the requested URL, the final URL, the lane, an ISO capture "
         "timestamp, the page's own identity signals, the raw bytes on disk, the sha256 OF THOSE "
         "BYTES, the byte length, the operative quote and only contract-supported facts. The "
         "hash is computed in the same call that took the quote and cannot be produced without "
         "fetching the page."),
        ("artifact_root", str(ARTIFACTS.relative_to(Path(_DASH))).replace("\\", "/")),
        ("artifacts_are_gitignored",
         "data/ is gitignored, so the bytes are local. What is COMMITTED and durable is the "
         "sha256, the byte length, the final URL, the timestamp and the bounded policy window -- "
         "which is exactly what the legacy attended lane failed to record."),
        ("counts", OrderedDict(sorted(Counter(r["outcome"] for r in rows).items()))),
        ("seconds", elapsed),
        ("rows", rows),
    ))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    for r in rows:
        print("%-46s %-16s %s" % (r["identity_key"][:46], r["outcome"],
                                  (r.get("page_sha256") or "")[:16]))
    print("requests:", requests, "| seconds:", elapsed, "| $0.00 | 0 credits")
    print("written :", os.path.relpath(args.out, _DASH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
