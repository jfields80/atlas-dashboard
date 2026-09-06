"""PTF-TOLEDO-OH-NEW-MARKET-001 -- Phases 10 and 13, free first-party static capture.

One HTTPS GET per route through the canonical gates, for two cohorts:

  ROUTED          the 37 confirmed Toledo identities that carry a first-party
                  route. The question is the PET POLICY.
  IDENTITY_FILL   the 23 brand-roster properties whose existence and route the
                  brand's own inventory states but which no source gave an
                  address. The question is first the ADDRESS -- a property code
                  selects, the page admits -- and only then the policy.

The lane is ``acquisition.direct_http_capture.run_attempt``: denial markers ->
page health -> identity read and assessment -> policy locator -> reader, with
every artifact persisted under ``data/acquisition/<run>/<slug>/attempt-01/``.
``market_observation_store.observation_for`` then grades the read.

No vendor, no browser, no price. Each target is captured at most ONCE per run;
a rerun reuses the attempt on disk. Nothing is written to any authority.

WHAT THIS RUN WILL NOT DO
-------------------------
It will not treat a route as confirmed because a directory stated it. Every row
carries the identity it claims to serve, and the identity assessment on the
page's own address, phone or property code decides. It will not read a policy
off a page whose identity did not confirm, and it will not infer acceptance
from a fee, a weight, a count or an amenity chip: that judgement belongs to the
reader and the publication grade, both of which this module only reports.

Output:
  launch_packages/pettripfinder/markets/reports/toledo_oh_free_static_capture_001.json
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter, OrderedDict
from pathlib import Path

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.acquisition import direct_http_capture as DHC  # noqa: E402
from scripts.pettripfinder.acquisition import market_observation_store as MOS  # noqa: E402
from scripts.pettripfinder.brightdata import browser_capture as BC  # noqa: E402
from scripts.pettripfinder.discovery import identity_dedup as DEDUP  # noqa: E402
from scripts.pettripfinder.brightdata import unlocker_capture as UC  # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR  # noqa: E402
from scripts.pettripfinder.brightdata import marriott_surface as MS  # noqa: E402
from scripts.pettripfinder.acquisition import zero_cost_recovery as ZCR  # noqa: E402

WORK_ORDER = "PTF-TOLEDO-OH-NEW-MARKET-001"
MARKET_ID = "toledo-oh"
SCHEMA = "ptf-free-static-capture/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CENSUS = os.path.join(PKG, "identity_census_proposed", "toledo-oh.json")
ROUTING = os.path.join(REPORTS, "toledo_oh_routing_001.json")
SPACING_SECONDS = 1.2

BRANDS = [
    ("MARRIOTT", r"marriott|courtyard|residence inn|springhill|fairfield|towneplace|ac hotel|"
                 r"aloft|westin|sheraton|moxy|element|renaissance|delta hotels|city express"),
    ("HILTON", r"hilton|hampton|embassy suites|homewood|home2|doubletree|tru |tapestry|canopy|spark"),
    ("IHG", r"holiday inn|crowne plaza|staybridge|candlewood|even hotel|avid|intercontinental|"
            r"kimpton|hotel indigo"),
    ("CHOICE", r"comfort inn|comfort suites|quality inn|sleep inn|clarion|cambria|mainstay|"
               r"suburban|econo lodge|rodeway|woodspring"),
    ("WYNDHAM", r"wyndham|baymont|days inn|super 8|ramada|travelodge|la quinta|microtel|"
                r"howard johnson|hawthorn|americinn|wingate"),
    ("ESA", r"extended stay america"),
    ("BEST_WESTERN", r"best western|surestay"),
    ("MOTEL6", r"motel 6|studio 6"),
    ("RED_ROOF", r"red roof"),
    ("SONESTA", r"sonesta|americas best value"),
    ("RADISSON", r"radisson|country inn"),
    ("DRURY", r"drury"),
]


def brand_of(name: str) -> str:
    n = (name or "").lower()
    for fam, rx in BRANDS:
        if re.search(rx, n):
            return fam
    return "INDEPENDENT"


def read_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def as_plain(obj):
    if dataclasses.is_dataclass(obj):
        return {k: as_plain(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, (list, tuple)):
        return [as_plain(x) for x in obj]
    if isinstance(obj, dict):
        return {k: as_plain(v) for k, v in obj.items()}
    return obj


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else ""


def digits(v):
    return re.sub(r"[^0-9]", "", v or "")[-10:]


def address_from_page(attempt_root: Path):
    """The address the property's OWN page states, for an identity-fill row.

    Read from the page's structured data via the capture record's identity
    block where present; this is what turns a brand-roster row into a census
    candidate, and it is the only thing allowed to.
    """
    for sub in ("attempt-01", "declined-01"):
        rec = attempt_root / sub / "identity.json"
        if rec.is_file():
            try:
                return json.loads(rec.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                pass
    return None


def text_bound_read(attempt_root: Path, row, brand: str):
    """A read over a document the canonical gate DECLINED.

    The page's own text is bound to the census row on street number plus postal,
    or on telephone, and only then is the policy block located and read. Identity
    here is TEXT-bound rather than structured-data-bound, so the result is a
    candidate for attended confirmation and never a clean row.
    """
    declined = attempt_root / "declined-01" / "rendered.html"
    if not declined.is_file() or row is None:
        return None
    html = declined.read_text(encoding="utf-8", errors="replace")
    text_path = attempt_root / "declined-01" / "page-text.txt"
    text = (text_path.read_text(encoding="utf-8", errors="replace")
            if text_path.is_file() else ZCR.full_document_text(html))
    c_street = row.get("street") or ""
    c_num = (re.match(r"\s*(\d+)", c_street) or [None, ""])[1] if c_street else ""
    c_postal = (row.get("postal_code") or "")[:5]
    c_phone = digits(row.get("phone") or "")
    parts = c_street.split()
    hay = text + "\n" + ZCR.full_document_text(html)
    street_ok = bool(c_num) and len(parts) > 1 and bool(
        re.search(r"\b" + re.escape(c_num) + r"\b[^\n]{0,40}" + re.escape(parts[1][:4]), hay, re.I))
    postal_ok = bool(c_postal) and bool(re.search(r"\b" + c_postal + r"\b", hay))
    phone_ok = bool(c_phone) and c_phone in re.sub(r"[^0-9]", "", hay)
    bound = (street_ok and postal_ok) or (phone_ok and (postal_ok or street_ok))
    out = OrderedDict([
        ("street_number_agrees", street_ok), ("postal_agrees", postal_ok),
        ("phone_agrees", phone_ok), ("text_bound", bound),
        ("document_sha256", hashlib.sha256(declined.read_bytes()).hexdigest()),
    ])
    hit = UC.locate_policy_in_html(html)
    walk = "STATIC_HTML_WALK"
    if not hit.found:
        hit = UC.locate_policy_in_text(ZCR.full_document_text(html))
        walk = "FULL_DOCUMENT_TEXT_RECOVERY"
    if not hit.found:
        out["reader"] = OrderedDict([("found", False), ("walk", walk)])
        return out
    try:
        if brand == "MARRIOTT":
            reading = MS.parse_policy_block(hit.text, locator_id=WORK_ORDER)
            result = MS.to_extraction(reading, location=MARKET_ID)
        else:
            reading = PR.parse(hit.text, strategy=hit.strategy or WORK_ORDER)
            result = PR.to_extraction(reading, location=MARKET_ID)
        out["reader"] = OrderedDict([
            ("found", True), ("walk", walk), ("block_chars", len(hit.text)),
            ("pets_allowed", result.extraction.get("pets_allowed")),
            ("pets_allowed_quote", (getattr(reading, "pets_allowed_quote", "") or "")[:300]),
            ("extraction", result.extraction),
            ("withheld", dict(result.withheld)),
            ("evidence_quotes", [e.get("quote", "")[:300] for e in result.evidence][:6]),
            ("service_animal_quote", (getattr(reading, "service_animal_quote", "") or "")[:200]),
            ("brand_generic", bool(getattr(reading, "brand_generic", False))),
        ])
    except Exception as exc:  # noqa: BLE001
        out["reader"] = OrderedDict([("found", True), ("error", repr(exc))])
    return out


def targets():
    routing = read_json(ROUTING)
    census = {h["identity_key"]: h for h in read_json(CENSUS)["hotels"]}
    out = []
    for r in routing["routes"]:
        if not r.get("url"):
            continue
        row = census.get(r["identity_key"], {})
        out.append(OrderedDict([
            ("cohort", "ROUTED"), ("identity_key", r["identity_key"]),
            ("canonical_name", r["canonical_name"]), ("url", r["url"]),
            ("routing_state", r["routing_state"]), ("corridor", r.get("corridor", "")),
            ("street", row.get("street", "")), ("city", row.get("city", "")),
            ("postal_code", row.get("postal_code", "")), ("phone", row.get("phone", "")),
            ("street_identity", row.get("street_identity", "")),
        ]))
    for r in routing.get("identity_fill_routes", []):
        out.append(OrderedDict([
            ("cohort", "IDENTITY_FILL"), ("identity_key", r["identity_key"]),
            ("canonical_name", r["canonical_name"]), ("url", r["url"]),
            ("routing_state", r["routing_state"]), ("corridor", ""),
            ("street", ""), ("city", ""), ("postal_code", ""), ("phone", ""),
            ("street_identity", ""),
        ]))
    seen, uniq = set(), []
    for t in out:
        k = (t["identity_key"], t["url"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(t)
    return uniq


def build(args) -> OrderedDict:
    tgts = targets()
    if args.cohort:
        tgts = [t for t in tgts if t["cohort"] == args.cohort]
    if args.limit:
        tgts = tgts[: args.limit]
    run_id = args.run_id
    run_dir = Path(_DASH) / "data" / "acquisition" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    print("targets", len(tgts), "run", run_id, flush=True)

    rows, requests = [], 0
    for i, t in enumerate(tgts):
        key = t["identity_key"]
        name = t["canonical_name"]
        brand = brand_of(name)
        slug = re.sub(r"[^a-z0-9]+", "-", key).strip("-")[:80]
        attempt_dir = run_dir / slug / "attempt-01"
        target = BC.CaptureTarget(
            slug=slug, hotel=name, requested_url=t["url"],
            property_code=DEDUP.property_code({"official_url": t["url"]}),
            market_id=MARKET_ID, normalized_name=key, identity_key=key,
            street_identity=t.get("street_identity", ""),
            expected_postal_code=(t.get("postal_code") or "")[:5],
            expected_street=t.get("street", ""), expected_phone=t.get("phone", ""),
            expected_locality=t.get("city", ""), identity_brand=brand,
            census_matched=t["cohort"] == "ROUTED",
        )
        record_path = run_dir / slug / "attempt-01.record.json"
        if record_path.is_file() and not args.refetch:
            rec = json.loads(record_path.read_text(encoding="utf-8"))
        else:
            time.sleep(SPACING_SECONDS)
            attempt, payload = DHC.run_attempt(target, 1, run_dir=run_dir, brand=brand)
            requests += 1
            a = as_plain(attempt)
            rec = OrderedDict([
                ("outcome", a.get("outcome")), ("final_url", a.get("final_url")),
                ("title", a.get("title")), ("detail", a.get("detail")),
                ("body_chars", a.get("body_chars")), ("identity", a.get("identity")),
                ("fetched_at", a.get("started_at")),
            ])
            record_path.parent.mkdir(parents=True, exist_ok=True)
            record_path.write_text(json.dumps(rec, indent=1, ensure_ascii=False, default=str),
                                   encoding="utf-8")
        html_path = attempt_dir / "rendered.html"
        row = OrderedDict([
            ("cohort", t["cohort"]), ("identity_key", key), ("canonical_name", name),
            ("brand", brand), ("routing_state", t["routing_state"]),
            ("corridor", t.get("corridor", "")),
            ("requested_url", t["url"]), ("outcome", rec.get("outcome")),
            ("final_url", rec.get("final_url")), ("title", (rec.get("title") or "")[:160]),
            ("detail", (rec.get("detail") or "")[:300]),
            ("identity_assessment", rec.get("identity")),
            ("page_sha256", sha256_file(html_path)),
            ("artifact_dir", str(attempt_dir.relative_to(_DASH)) if attempt_dir.is_dir() else ""),
        ])
        if rec.get("outcome") == "VALID" and (attempt_dir / "policy-block.txt").is_file():
            result = {
                "identity_key": key, "canonical_name": name, "brand": brand,
                "corridor": t.get("corridor", ""), "source_url": t["url"], "outcome": "VALID",
                "final_url": rec.get("final_url") or t["url"], "artifact_dir": str(attempt_dir),
                "identity_confirmed": bool((rec.get("identity") or {}).get("confirmed", True)),
                "locator_strategy": "",
            }
            census_row = None
            if t["cohort"] == "ROUTED":
                census_row = OrderedDict([
                    ("identity_key", key), ("canonical_name", name),
                    ("address", t.get("street", "")), ("postal_code", t.get("postal_code", "")),
                    ("phone", t.get("phone", "")), ("city", t.get("city", "")),
                    ("corridor", t.get("corridor", "")),
                ])
            try:
                obs, grade, refusal = MOS.observation_for(result, run_id=run_id,
                                                          market_id=MARKET_ID,
                                                          census_row=census_row)
                ext = ((obs or {}).get("observation") or {}).get("extraction") or {}
                row["observation"] = OrderedDict([
                    ("extraction", ext),
                    ("evidence", ((obs or {}).get("observation") or {}).get("evidence")),
                    ("withheld_fields", (obs or {}).get("withheld_fields")),
                    ("publication_grade", grade), ("refusal_reason", refusal),
                    ("reader_provenance", (obs or {}).get("reader_provenance")),
                    ("membrane", (obs or {}).get("membrane")),
                ])
                pa = ext.get("pets_allowed")
                pg_ok = bool(grade) and str(
                    (grade or {}).get("verdict") or (grade or {}).get("grade") or ""
                ).endswith("CONFIRMED")
                if pa is True:
                    row["classification"] = ("CLEAN_PET_FRIENDLY_CANDIDATE" if pg_ok
                                             else "PET_FRIENDLY_READ_NOT_PUBLICATION_GRADE")
                elif pa is False:
                    row["classification"] = ("CLEAN_VERIFIED_NO_PETS_CANDIDATE" if pg_ok
                                             else "NO_PETS_READ_NOT_PUBLICATION_GRADE")
                else:
                    row["classification"] = "BLOCK_FOUND_BUT_SILENT"
            except Exception as exc:  # noqa: BLE001
                row["observation_error"] = repr(exc)
                row["classification"] = "OBSERVATION_ERROR"
        else:
            oc = rec.get("outcome") or "CAPTURE_FAILED"
            row["classification"] = {
                "POLICY_NOT_FOUND": "SOURCE_SILENT_STATIC",
                "UNHYDRATED": "NEEDS_ATTENDED_RENDER",
                "ACCESS_DENIED": "ACCESS_BLOCKED_PLAIN_CLIENT",
                "IDENTITY_MISMATCH": "IDENTITY_MISMATCH",
                "BLANK_PAGE": "NEEDS_ATTENDED_RENDER",
                "NAVIGATION_FAILED": "TRANSPORT_FAILED",
                "UNEXPECTED_PAGE": "UNEXPECTED_PAGE",
                "CAPTURE_FAILED": "TRANSPORT_FAILED",
            }.get(oc, "OTHER:" + oc)
        if rec.get("outcome") in ("IDENTITY_MISMATCH", "POLICY_NOT_FOUND"):
            tb = text_bound_read(run_dir / slug, t if t["cohort"] == "ROUTED" else None, brand)
            if tb is not None:
                row["text_bound_read"] = tb
                rd = tb.get("reader") or {}
                if tb["text_bound"] and rd.get("pets_allowed") is True:
                    row["classification"] = "PET_FRIENDLY_READ_TEXT_BOUND"
                elif tb["text_bound"] and rd.get("pets_allowed") is False:
                    row["classification"] = "NO_PETS_READ_TEXT_BOUND"
                elif tb["text_bound"]:
                    row["classification"] = "IDENTITY_TEXT_BOUND_POLICY_SILENT"
                elif rec.get("outcome") == "IDENTITY_MISMATCH":
                    row["classification"] = "IDENTITY_NOT_CONFIRMED_STATIC"
        if t["cohort"] == "IDENTITY_FILL":
            ident = rec.get("identity") or {}
            row["address_read_from_page"] = OrderedDict([
                ("name_on_page", ident.get("name_on_page")),
                ("address_on_page", ident.get("address_on_page")),
                ("postal_code", ident.get("postal_code")),
                ("phone_on_page", ident.get("phone_on_page")),
                ("property_code_on_page", ident.get("property_code_on_page")),
            ])
        rows.append(row)
        if (i + 1) % 10 == 0:
            print("  ", i + 1, "/", len(tgts), "requests", requests, flush=True)

    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER),
        ("phase", "10 and 13 -- free first-party static capture and classification"),
        ("market_id", MARKET_ID), ("run_id", run_id),
        ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("lane", "direct_http (first-party static; no vendor, no browser, no price)"),
        ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("free_http_requests_this_run", requests),
        ("no_inference_from_silence",
         "A page that states no pet policy is SOURCE_SILENT. It is not a refusal, it is not an "
         "acceptance, and it never becomes either here."),
        ("counts", OrderedDict([
            ("targets", len(rows)),
            ("by_cohort", OrderedDict(sorted(Counter(r["cohort"] for r in rows).items()))),
            ("by_outcome", OrderedDict(sorted(Counter(str(r["outcome"]) for r in rows).items()))),
            ("by_classification",
             OrderedDict(sorted(Counter(r["classification"] for r in rows).items()))),
            ("by_brand", OrderedDict(sorted(Counter(r["brand"] for r in rows).items()))),
        ])),
        ("rows", rows),
    ])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPORTS,
                                                  "toledo_oh_free_static_capture_001.json"))
    ap.add_argument("--run-id", default="toledo_oh_free_static_001")
    ap.add_argument("--cohort", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--refetch", action="store_true")
    args = ap.parse_args(argv)
    rep = build(args)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1, default=str)
        fh.write("\n")
    c = rep["counts"]
    print("targets        :", c["targets"], dict(c["by_cohort"]))
    print("outcomes       :", dict(c["by_outcome"]))
    print("classification :", dict(c["by_classification"]))
    print("requests       :", rep["free_http_requests_this_run"])
    print("written        :", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
