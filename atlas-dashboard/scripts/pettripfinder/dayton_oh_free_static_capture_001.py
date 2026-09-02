"""PTF-DAYTON-OH-HARDENED-REVALIDATION-001 -- Phases 8 / 9 / 11.

Free FIRST-PARTY static capture through the canonical lanes, market-scoped to
Dayton. This is the Cleveland phase-9 harness
(``cleveland_akron_canton_oh_free_static_capture_009.py``) re-pointed at
``dayton-oh`` and given a target source Dayton actually owns: its committed
final partition. No shared or generic module is modified.

    acquisition.direct_http_capture.run_attempt         one HTTPS GET through
        the canonical gates -- denial markers -> page health -> identity read
        and assessment -> policy locator -> reader; artifacts persisted under
        data/acquisition/<run>/<slug>/attempt-01/.
    acquisition.market_observation_store.observation_for reader ->
        publication_grade.assess -> ptf-market-observation-store record.

No vendor, no browser, no price. Every target is captured at most ONCE per run;
a rerun reuses the attempt on disk. Nothing is written to authority: the output
is one report of observations and classifications keyed on the page's own
sha256.
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
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key  # noqa: E402

WORK_ORDER = "PTF-DAYTON-OH-HARDENED-REVALIDATION-001"
MARKET_ID = "dayton-oh"
SCHEMA = "ptf-free-static-capture/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
AUTH = os.path.join(PKG, "markets", "authority", MARKET_ID)
REPORTS = os.path.join(PKG, "markets", "reports")
PARTITION = os.path.join(PKG, "dayton_final_partition_001.json")
SPACING_SECONDS = 1.5

ATTENDED_HOSTS = ("hilton.com", "marriott.com", "ihg.com", "choicehotels.com", "bestwestern.com",
                  "radissonhotels", "redroof.com", "extendedstayamerica.com", "hyatt.com", "sonesta.com")
BRANDS = [
    ("MARRIOTT", r"marriott|courtyard|residence inn|springhill|fairfield|towneplace|ac hotel|aloft|westin|sheraton|moxy|element"),
    ("HILTON", r"hilton|hampton|embassy suites|homewood|home2|doubletree|tru by|tapestry|canopy|ardent"),
    ("IHG", r"holiday inn|crowne plaza|staybridge|candlewood|even hotel|avid|intercontinental|kimpton|hotel indigo"),
    ("CHOICE", r"comfort inn|comfort suites|quality inn|sleep inn|clarion|cambria|mainstay|suburban|econo lodge|rodeway|woodspring"),
    ("WYNDHAM", r"wyndham|baymont|days inn|super 8|ramada|travelodge|la quinta|microtel|howard johnson|hawthorn|americinn|wingate"),
    ("ESA", r"extended stay america"),
    ("BEST_WESTERN", r"best western|surestay"),
    ("MOTEL6", r"motel 6|studio 6"),
    ("RED_ROOF", r"red roof"),
    ("SONESTA", r"sonesta"),
    ("RADISSON", r"radisson|country inn"),
    ("DRURY", r"drury"),
    ("HYATT", r"hyatt"),
    ("MAGNUSON", r"magnuson"),
]


def brand_of(name: str) -> str:
    n = name.lower()
    for fam, rx in BRANDS:
        if re.search(rx, n):
            return fam
    return "INDEPENDENT"


def host_of(url: str) -> str:
    m = re.match(r"https?://([^/]+)", url or "")
    return m.group(1).lower().replace("www.", "") if m else ""


def read_json(path):
    with open(path, "r", encoding="utf-8") as fh:
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


def text_bound_read(attempt_root: Path, crow, brand: str):
    """Fallback over a document the canonical gate DECLINED (declined-01/).

    The page's own text is bound to the census row on street number plus postal,
    or on telephone, and only then is the policy block located and read.
    Identity here is TEXT-bound rather than structured-data-bound, so the result
    is a candidate for attended confirmation and never a clean row.
    """
    declined = attempt_root / "declined-01" / "rendered.html"
    if not declined.is_file() or crow is None:
        return None
    html = declined.read_text(encoding="utf-8", errors="replace")
    text_path = attempt_root / "declined-01" / "page-text.txt"
    text = text_path.read_text(encoding="utf-8", errors="replace") if text_path.is_file() else ZCR.full_document_text(html)
    c_street = crow.get("address") or ""
    c_num = (re.match(r"\s*(\d+)", c_street) or [None, ""])[1] if c_street else ""
    c_postal = (crow.get("postal_code") or "")[:5]
    c_phone = digits(crow.get("phone") or "")
    parts = c_street.split()
    hay = text + "\n" + ZCR.full_document_text(html)
    street_ok = bool(c_num) and len(parts) > 1 and bool(
        re.search(r"\b" + re.escape(c_num) + r"\b[^\n]{0,40}" + re.escape(parts[1][:4]), hay, re.I))
    postal_ok = bool(c_postal) and bool(re.search(r"\b" + c_postal + r"\b", hay))
    phone_ok = bool(c_phone) and c_phone in re.sub(r"[^0-9]", "", hay)
    bound = (street_ok and postal_ok) or (phone_ok and (postal_ok or street_ok))
    out = OrderedDict([
        ("street_number_agrees", street_ok),
        ("postal_agrees", postal_ok),
        ("phone_agrees", phone_ok),
        ("text_bound", bound),
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
            ("found", True),
            ("walk", walk),
            ("block_chars", len(hit.text)),
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


def targets_from_args(args, census, policy, exclusions):
    """Dayton's target source is its own committed final partition, plus -- for
    the phase-11 live contradiction audit -- its live authority."""
    targets = []
    if args.partition_states:
        wanted = set(args.partition_states)
        for it in read_json(PARTITION)["items"]:
            if it["final_state"] in wanted and (it.get("official_url") or ""):
                targets.append(OrderedDict([
                    ("identity_key", it["identity_key"]),
                    ("url", it["official_url"]),
                    ("origin", "PARTITION:" + it["final_state"]),
                ]))
    if args.routes:
        doc = read_json(args.routes)
        for r in doc.get("routes_recovered") or doc.get("rows") or []:
            if r.get("identity_key") and r.get("url") and r.get("status", "ROUTING_CONFIRMED") == "ROUTING_CONFIRMED":
                targets.append(OrderedDict([
                    ("identity_key", r["identity_key"]),
                    ("url", r["url"]),
                    ("origin", "PHASE_7_ROUTING"),
                ]))
    if args.live:
        for p in policy:
            targets.append(OrderedDict([
                ("identity_key", p["identity_key"]),
                ("url", p.get("source_url") or p.get("official_url") or ""),
                ("origin", "LIVE_PET_FRIENDLY"),
            ]))
        for e in exclusions:
            targets.append(OrderedDict([
                ("identity_key", ptf_identity_key(e["canonical_name"])),
                ("url", e.get("official_url") or e.get("source_url") or ""),
                ("origin", "LIVE_VERIFIED_NO_PETS"),
            ]))
    seen = set()
    out = []
    for t in targets:
        k = (t["identity_key"], t["url"])
        if k in seen or not t["url"]:
            continue
        seen.add(k)
        out.append(t)
    return out


def build(args) -> OrderedDict:
    census = {r["identity_key"]: r for r in read_json(os.path.join(PKG, "identity_census", MARKET_ID + ".json"))["hotels"]}
    policy = read_json(os.path.join(PKG, "hotel_policy_facts_" + MARKET_ID + ".json"))["hotels"]
    policy_by_key = {p["identity_key"]: p for p in policy}
    exclusions = read_json(os.path.join(AUTH, "hotel_exclusions.json"))["exclusions"]
    excl_keys = {ptf_identity_key(e["canonical_name"]) for e in exclusions}
    targets = targets_from_args(args, census, policy, exclusions)
    if args.skip_attended_hosts:
        targets = [t for t in targets if not any(h in host_of(t["url"]) for h in ATTENDED_HOSTS)]
    if args.limit:
        targets = targets[: args.limit]
    run_id = args.run_id
    run_dir = Path(_DASH) / "data" / "acquisition" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    print("targets", len(targets), "run", run_id, flush=True)

    rows = []
    requests = 0
    for i, t in enumerate(targets):
        key = t["identity_key"]
        crow = census.get(key)
        name = crow["canonical_name"] if crow else key
        brand = brand_of(name)
        slug = (crow or {}).get("slug") or re.sub(r"[^a-z0-9]+", "-", key).strip("-")
        attempt_dir = run_dir / slug / "attempt-01"
        target = BC.CaptureTarget(
            slug=slug,
            hotel=name,
            requested_url=t["url"],
            property_code=DEDUP.property_code({"official_url": t["url"]}),
            market_id=MARKET_ID,
            normalized_name=key,
            identity_key=key,
            street_identity=(crow or {}).get("street_identity", ""),
            expected_postal_code=((crow or {}).get("postal_code") or "")[:5],
            expected_street=(crow or {}).get("address", ""),
            expected_phone=(crow or {}).get("phone", ""),
            expected_locality=(crow or {}).get("city", ""),
            identity_brand=brand,
            census_matched=crow is not None,
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
                ("outcome", a.get("outcome")),
                ("final_url", a.get("final_url")),
                ("title", a.get("title")),
                ("detail", a.get("detail")),
                ("body_chars", a.get("body_chars")),
                ("identity", a.get("identity")),
                ("payload_keys", sorted((payload or {}).keys()) if isinstance(payload, dict) else None),
                ("fetched_at", a.get("started_at")),
            ])
            record_path.parent.mkdir(parents=True, exist_ok=True)
            record_path.write_text(json.dumps(rec, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
        html_path = attempt_dir / "rendered.html"
        row = OrderedDict([
            ("identity_key", key),
            ("canonical_name", name),
            ("brand", brand),
            ("origin", t["origin"]),
            ("requested_url", t["url"]),
            ("live_state", "PET_FRIENDLY_LIVE" if key in policy_by_key
             else "VERIFIED_NO_PETS_LIVE" if key in excl_keys else "UNRESOLVED_OR_NEW"),
            ("outcome", rec.get("outcome")),
            ("final_url", rec.get("final_url")),
            ("title", (rec.get("title") or "")[:160]),
            ("detail", (rec.get("detail") or "")[:300]),
            ("identity_assessment", rec.get("identity")),
            ("page_sha256", sha256_file(html_path)),
            ("artifact_dir", str(attempt_dir.relative_to(_DASH)) if attempt_dir.is_dir() else ""),
        ])
        if rec.get("outcome") == "VALID" and (attempt_dir / "policy-block.txt").is_file():
            result = {
                "identity_key": key, "canonical_name": name, "brand": brand,
                "corridor": (crow or {}).get("corridor", ""), "source_url": t["url"], "outcome": "VALID",
                "final_url": rec.get("final_url") or t["url"], "artifact_dir": str(attempt_dir),
                "identity_confirmed": bool((rec.get("identity") or {}).get("confirmed", True)),
                "locator_strategy": "",
            }
            try:
                obs, grade, refusal = MOS.observation_for(result, run_id=run_id, market_id=MARKET_ID, census_row=crow)
                ext = ((obs or {}).get("observation") or {}).get("extraction") or {}
                row["observation"] = OrderedDict([
                    ("extraction", ext),
                    ("evidence", ((obs or {}).get("observation") or {}).get("evidence")),
                    ("withheld_fields", (obs or {}).get("withheld_fields")),
                    ("publication_grade", grade),
                    ("refusal_reason", refusal),
                    ("reader_provenance", (obs or {}).get("reader_provenance")),
                    ("membrane", (obs or {}).get("membrane")),
                ])
                pa = ext.get("pets_allowed")
                pg_ok = bool(grade) and str((grade or {}).get("verdict") or (grade or {}).get("grade") or "").endswith("CONFIRMED")
                if pa is True:
                    row["classification"] = "CLEAN_PET_FRIENDLY_CANDIDATE" if pg_ok else "PET_FRIENDLY_READ_NOT_PUBLICATION_GRADE"
                elif pa is False:
                    row["classification"] = "CLEAN_VERIFIED_NO_PETS_CANDIDATE" if pg_ok else "NO_PETS_READ_NOT_PUBLICATION_GRADE"
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
            tb = text_bound_read(run_dir / slug, crow, brand)
            if tb is not None:
                row["text_bound_read"] = tb
                rd = tb.get("reader") or {}
                if tb["text_bound"] and rd.get("pets_allowed") is True:
                    row["classification"] = "PET_FRIENDLY_READ_TEXT_BOUND"
                elif tb["text_bound"] and rd.get("pets_allowed") is False:
                    row["classification"] = "NO_PETS_READ_TEXT_BOUND"
                elif tb["text_bound"] and rec.get("outcome") == "IDENTITY_MISMATCH":
                    row["classification"] = "IDENTITY_TEXT_BOUND_POLICY_SILENT"
                elif rec.get("outcome") == "IDENTITY_MISMATCH":
                    row["classification"] = "IDENTITY_NOT_CONFIRMED_STATIC"
        if row["live_state"] != "UNRESOLVED_OR_NEW":
            cls = row["classification"]
            if cls in ("CLEAN_PET_FRIENDLY_CANDIDATE", "PET_FRIENDLY_READ_NOT_PUBLICATION_GRADE"):
                row["live_audit"] = "CURRENTLY_CORRECT" if row["live_state"] == "PET_FRIENDLY_LIVE" else "WRONG_LIVE_POLICY_CANDIDATE"
                if row["live_state"] == "PET_FRIENDLY_LIVE":
                    pub = policy_by_key[key]["facts"]
                    ext = row["observation"]["extraction"]
                    fee_pub = (pub.get("pet_fee") or {}).get("amount_cents")
                    raw = ext.get("pet_fee")
                    fee_new = raw if isinstance(raw, int) else (raw or {}).get("amount_minor") if isinstance(raw, dict) else None
                    row["fee_comparison"] = OrderedDict([("published_cents", fee_pub), ("page_minor", fee_new)])
                    if fee_pub is not None and fee_new is not None and fee_pub != fee_new:
                        row["live_audit"] = "POTENTIAL_STALE_POLICY"
            elif cls in ("CLEAN_VERIFIED_NO_PETS_CANDIDATE", "NO_PETS_READ_NOT_PUBLICATION_GRADE"):
                row["live_audit"] = "CURRENTLY_CORRECT" if row["live_state"] == "VERIFIED_NO_PETS_LIVE" else "WRONG_LIVE_POLICY_CANDIDATE"
            elif cls == "PET_FRIENDLY_READ_TEXT_BOUND":
                row["live_audit"] = ("CURRENTLY_CORRECT_TEXT_BOUND" if row["live_state"] == "PET_FRIENDLY_LIVE"
                                     else "WRONG_LIVE_POLICY_CANDIDATE_TEXT_BOUND")
            elif cls == "NO_PETS_READ_TEXT_BOUND":
                row["live_audit"] = ("CURRENTLY_CORRECT_TEXT_BOUND" if row["live_state"] == "VERIFIED_NO_PETS_LIVE"
                                     else "WRONG_LIVE_POLICY_CANDIDATE_TEXT_BOUND")
            elif cls == "IDENTITY_TEXT_BOUND_POLICY_SILENT":
                row["live_audit"] = "NO_CHANGE_SIGNAL_PAGE_SILENT"
            elif cls in ("IDENTITY_MISMATCH", "IDENTITY_NOT_CONFIRMED_STATIC"):
                row["live_audit"] = "IDENTITY_NOT_CONFIRMED_STATICALLY"
            elif cls in ("ACCESS_BLOCKED_PLAIN_CLIENT", "NEEDS_ATTENDED_RENDER", "TRANSPORT_FAILED"):
                row["live_audit"] = "NOT_RE_READABLE_STATICALLY"
            else:
                row["live_audit"] = "NO_CHANGE_SIGNAL"
        rows.append(row)
        if (i + 1) % 10 == 0:
            print("  ", i + 1, "/", len(targets), "requests", requests, flush=True)

    return OrderedDict([
        ("schema", SCHEMA),
        ("work_order", WORK_ORDER),
        ("phase", args.phase_label),
        ("market_id", MARKET_ID),
        ("run_id", run_id),
        ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("lane", "direct_http (first-party static; no vendor, no browser, no price)"),
        ("paid_provider_calls", 0),
        ("usd_spent", 0.0),
        ("free_http_requests_this_run", requests),
        ("targets", len(targets)),
        ("classification_counts", OrderedDict(sorted(Counter(r["classification"] for r in rows).items()))),
        ("live_audit_counts", OrderedDict(sorted(Counter(r.get("live_audit") for r in rows if r.get("live_audit")).items()))),
        ("rows", rows),
    ])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="dayton_oh_free_static_001")
    ap.add_argument("--out", default=os.path.join(REPORTS, "dayton_oh_free_static_capture_001.json"))
    ap.add_argument("--phase-label", default="9 -- zero-cost policy capture (static)")
    ap.add_argument("--partition-states", nargs="*", default=None)
    ap.add_argument("--routes", default=None)
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--skip-attended-hosts", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--refetch", action="store_true")
    args = ap.parse_args(argv)
    rep = build(args)
    with open(args.out, "wb") as fh:
        fh.write((json.dumps(rep, indent=1, ensure_ascii=False, default=str) + "\n").encode("utf-8"))
    print("written", os.path.relpath(args.out, _DASH))
    print("classification:", dict(rep["classification_counts"]))
    print("live audit:", dict(rep["live_audit_counts"]))
    print("requests", rep["free_http_requests_this_run"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
