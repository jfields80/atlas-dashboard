"""PTF-CLEVELAND-AKRON-CANTON-HARDENED-REVALIDATION-001 -- Phase 6.

Replay EVERY owned Cleveland evidence artifact (the pass-2/3/4 attended
captures, ptf-attended-capture/2.0, html+text embedded) through the CURRENT
canonical reader stack:

    unlocker_capture.locate_policy_in_html  ->  policy_reading.parse
    ->  policy_reading.to_extraction   (Marriott: marriott_surface)
    +   policy_surface.read_identity / assess_identity   (page vs census row)
    +   zero_cost_recovery.full_document_text            (when the walk is silent)

Zero network. Zero spend. Nothing is re-acquired. Nothing is written to
authority. The output is one report keyed on the artifact's committed sha256
(document hash, never a short block hash), classifying each replay against
(a) the outcome the original pass committed and (b) the identity's LIVE state,
so stranded publication-grade evidence, stranded no-pets evidence, evidence
the old parsers rejected but the current reader reads, and identity
mismatches all surface mechanically.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import re
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.brightdata import unlocker_capture as UC  # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR  # noqa: E402
from scripts.pettripfinder.brightdata import policy_surface as PS  # noqa: E402
from scripts.pettripfinder.brightdata import marriott_surface as MS  # noqa: E402
from scripts.pettripfinder.acquisition import zero_cost_recovery as ZCR  # noqa: E402
from scripts.pettripfinder.discovery import identity_dedup as DEDUP  # noqa: E402
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key  # noqa: E402

WORK_ORDER = "PTF-CLEVELAND-AKRON-CANTON-HARDENED-REVALIDATION-001"
MARKET_ID = "cleveland-akron-canton-oh"
SCHEMA = "ptf-owned-evidence-replay/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
AUTH = os.path.join(PKG, "markets", "authority", MARKET_ID)
REPORTS = os.path.join(PKG, "markets", "reports")
RAW_ROOT = os.path.join(_DASH, "data", "worker_runs", "pettripfinder")

PASSES = [
    ("cleveland_pass2_capture_results.json", "cleveland-attended-capture-002"),
    ("cleveland_pass3_capture_results.json", "cleveland-attended-capture-003"),
    ("cleveland_pass4_capture_results.json", "cleveland-attended-capture-004"),
]

BLOCK_MARKERS = re.compile(r"access denied|just a moment|pardon our interruption|request unsuccessful|attention required|"
                           r"verify you are a human|are you a robot|enable javascript and cookies|incapsula|"
                           r"please enable cookies|kasada|blocked|forbidden", re.I)

HOST_BRAND = [
    ("marriott.com", "MARRIOTT"), ("hilton.com", "HILTON"), ("ihg.com", "IHG"), ("choicehotels.com", "CHOICE"),
    ("wyndhamhotels.com", "WYNDHAM"), ("hyatt.com", "HYATT"), ("bestwestern.com", "BEST_WESTERN"),
    ("extendedstayamerica.com", "ESA"), ("redroof.com", "RED_ROOF"), ("sonesta.com", "SONESTA"),
    ("druryhotels.com", "DRURY"), ("motel6.com", "MOTEL6"), ("studio6.com", "MOTEL6"), ("radissonhotels", "RADISSON"),
    ("magnusonhotels.com", "MAGNUSON"), ("myplacehotels.com", "MY_PLACE"), ("intownsuites.com", "INTOWN"),
]


def read_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def brand_of(url: str, declared: str = "") -> str:
    if declared:
        return declared.upper()
    u = (url or "").lower()
    for host, fam in HOST_BRAND:
        if host in u:
            return fam
    return "INDEPENDENT"


def as_plain(obj):
    if dataclasses.is_dataclass(obj):
        return {k: as_plain(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, (list, tuple)):
        return [as_plain(x) for x in obj]
    if isinstance(obj, dict):
        return {k: as_plain(v) for k, v in obj.items()}
    return obj


def clip(s, n=400):
    s = s or ""
    return s if len(s) <= n else s[:n] + " ..."


def read_block(block: str, brand: str, strategy: str):
    if brand == "MARRIOTT":
        reading = MS.parse_policy_block(block, locator_id=WORK_ORDER)
        result = MS.to_extraction(reading, location=MARKET_ID)
    else:
        reading = PR.parse(block, strategy=strategy or WORK_ORDER)
        result = PR.to_extraction(reading, location=MARKET_ID)
    return reading, result


def locate(html: str, text: str):
    """Three walks in order: static HTML walk, the captured visible text, the
    whole document with every tag stripped (zero_cost_recovery)."""
    hit = UC.locate_policy_in_html(html) if html else None
    if hit is not None and hit.found:
        return hit, "STATIC_HTML_WALK"
    if text:
        hit2 = UC.locate_policy_in_text(text)
        if hit2.found:
            return hit2, "CAPTURED_VISIBLE_TEXT"
    if html:
        full = ZCR.full_document_text(html)
        hit3 = UC.locate_policy_in_text(full)
        if hit3.found:
            return hit3, "FULL_DOCUMENT_TEXT_RECOVERY"
    return hit, "NOT_FOUND"


def digits(v):
    return re.sub(r"[^0-9]", "", v or "")[-10:]


def physical_binding(signals, crow, text):
    """Page-vs-census premises check on the page's OWN address block: street
    number, 5-digit postal and telephone. Proposes identity; never decides it."""
    page_street = (signals.get("street") or signals.get("street_address") or "")
    page_postal = (signals.get("postal_code") or "")[:5]
    page_phone = digits(signals.get("telephone") or signals.get("phone") or "")
    c_street = crow.get("address") or ""
    c_postal = (crow.get("postal_code") or "")[:5]
    c_phone = digits(crow.get("phone") or "")
    m_num = re.match(r"\s*(\d+)", c_street)
    c_num = m_num.group(1) if m_num else ""
    p_num_m = re.match(r"\s*(\d+)", page_street)
    p_num = p_num_m.group(1) if p_num_m else ""
    hay = text or ""
    parts = c_street.split()
    street_number_agrees = False
    if c_num:
        if p_num == c_num:
            street_number_agrees = True
        elif len(parts) > 1:
            pattern = r"\b" + re.escape(c_num) + r"\b[^\n]{0,40}" + re.escape(parts[1][:4].lower())
            street_number_agrees = bool(re.search(pattern, hay, re.I))
    postal_agrees = bool(c_postal) and (page_postal == c_postal or bool(re.search(r"\b" + c_postal + r"\b", hay)))
    phone_agrees = bool(c_phone) and (page_phone == c_phone or c_phone in re.sub(r"[^0-9]", "", hay))
    return OrderedDict([("street_number_agrees", street_number_agrees), ("postal_agrees", postal_agrees), ("phone_agrees", phone_agrees),
                        ("bound", (street_number_agrees and postal_agrees) or (phone_agrees and (postal_agrees or street_number_agrees)))])


def identity_of(row, census_by_key, census_by_slug):
    key = row.get("identity_key")
    if key and key in census_by_key:
        return key, census_by_key[key]
    hid = row.get("hotel_id")
    if hid and hid in census_by_slug:
        return census_by_slug[hid]["identity_key"], census_by_slug[hid]
    if hid and hid in census_by_key:
        return hid, census_by_key[hid]
    name = row.get("hotel") or ""
    k2 = ptf_identity_key(name) if name else ""
    if k2 in census_by_key:
        return k2, census_by_key[k2]
    return key or k2, None


def build(limit=0) -> OrderedDict:
    census = read_json(os.path.join(PKG, "identity_census", f"{MARKET_ID}.json"))["hotels"]
    census_by_key = {r["identity_key"]: r for r in census}
    census_by_slug = {r["slug"]: r for r in census}
    policy = read_json(os.path.join(PKG, f"hotel_policy_facts_{MARKET_ID}.json"))["hotels"]
    policy_by_key = {p["identity_key"]: p for p in policy}
    exclusions = read_json(os.path.join(AUTH, "hotel_exclusions.json"))["exclusions"]
    excl_keys = {ptf_identity_key(e["canonical_name"]) for e in exclusions}
    routing = read_json(os.path.join(AUTH, "identity_routing.json"))["routes"]
    route_by_key = {r["hotel_ref"]["identity_key"]: r for r in routing}
    unresolved = read_json(os.path.join(PKG, "cleveland_unresolved_manifest.json"))
    unresolved_keys = {ptf_identity_key(i["canonical_name"]) for i in unresolved["items"]}

    records = []
    n = 0
    for results_name, run_dir in PASSES:
        doc = read_json(os.path.join(PKG, results_name))
        raw_dir = os.path.join(RAW_ROOT, run_dir, "raw")
        for row in doc["results"]:
            refs = [(row.get("artifact_file"), row.get("artifact_file_sha256"), "primary")]
            supp = row.get("supplementary_artifact")
            if isinstance(supp, dict) and supp.get("artifact_file"):
                refs.append((supp["artifact_file"], supp.get("artifact_file_sha256"), "supplementary"))
            for name, committed_sha, role in refs:
                if not name:
                    continue
                n += 1
                if limit and n > limit:
                    break
                rec = OrderedDict([
                    ("artifact_file", name), ("role", role), ("run", run_dir), ("results_document", results_name),
                    ("queue_id", row.get("queue_id")), ("hotel", row.get("hotel")),
                    ("committed_outcome", row.get("outcome")), ("artifact_sha256", committed_sha),
                ])
                key, crow = identity_of(row, census_by_key, census_by_slug)
                rec["identity_key"] = key
                rec["identity_in_census"] = crow is not None
                live = ("PET_FRIENDLY_LIVE" if key in policy_by_key else
                        "VERIFIED_NO_PETS_LIVE" if key in excl_keys else
                        "UNRESOLVED" if key in unresolved_keys else "NOT_IN_CENSUS" if crow is None else "PARTITIONED_OTHER")
                rec["live_state"] = live
                path = os.path.join(raw_dir, name)
                if not os.path.exists(path):
                    rec["replay"] = "ARTIFACT_MISSING"
                    records.append(rec)
                    continue
                try:
                    art = read_json(path)
                except Exception as exc:  # noqa: BLE001
                    rec["replay"] = "ARTIFACT_UNREADABLE"
                    rec["error"] = repr(exc)
                    records.append(rec)
                    continue
                html = art.get("html") or ""
                text = art.get("text") or ""
                title = art.get("title") or ""
                final_url = art.get("final_url") or row.get("final_url") or ""
                brand = brand_of(final_url, row.get("brand") or "")
                rec.update([("final_url", final_url), ("title", title), ("brand", brand),
                            ("html_sha256_recorded", art.get("html_sha256")), ("html_bytes", len(html)), ("text_chars", len(text)),
                            ("interaction", art.get("interaction"))])

                blocked = bool(BLOCK_MARKERS.search(title)) or (len(text) < 400 and bool(BLOCK_MARKERS.search(text)))
                rec["access_blocked_markers"] = blocked

                # identity: page vs census row
                ident = OrderedDict()
                try:
                    signals = PS.read_identity(html, final_url=final_url, title=title, brand=brand)
                    if crow is not None:
                        exp_url = crow.get("official_url") or (route_by_key.get(key, {}).get("official_property_url") or "") or final_url
                        exp_code = DEDUP.property_code({"official_url": exp_url}) if exp_url else ""
                        assess = PS.assess_identity(signals, expected_name=crow["canonical_name"], expected_property_code=exp_code,
                                                    expected_url=exp_url, expected_postal_code=(crow.get("postal_code") or "")[:5],
                                                    expected_street=crow.get("address") or "", expected_phone=crow.get("phone") or "",
                                                    expected_locality=crow.get("city") or "")
                        a = as_plain(assess)
                        ident["assessment"] = a
                        ident["confirmed"] = bool(a.get("confirmed", a.get("identity_confirmed", a.get("verdict") in ("CONFIRMED", "IDENTITY_CONFIRMED"))))
                    s = as_plain(signals)
                    ident["page_name"] = s.get("name") or s.get("page_name")
                    ident["page_street"] = s.get("street") or s.get("street_address")
                    ident["page_postal"] = s.get("postal_code")
                    ident["page_phone"] = s.get("telephone") or s.get("phone")
                    ident["property_code"] = s.get("property_code")
                    ident["jsonld_present"] = s.get("jsonld_present")
                    if crow is not None:
                        ident["physical_binding"] = physical_binding(s, crow, text)
                except Exception as exc:  # noqa: BLE001
                    ident["error"] = repr(exc)
                rec["identity"] = ident

                # policy block + reader
                hit, walk = locate(html, text)
                rec["locator_walk"] = walk
                if hit is None or not hit.found:
                    rec["reader"] = OrderedDict([("found", False)])
                    rec["replay"] = "ACCESS_BLOCKED" if blocked else "SILENT_NO_POLICY_BLOCK"
                else:
                    try:
                        reading, result = read_block(hit.text, brand, getattr(hit, "strategy", "") or "")
                        ex = result.extraction
                        rd = OrderedDict([
                            ("found", True), ("strategy", getattr(hit, "strategy", "")), ("block_chars", len(hit.text)),
                            ("pets_allowed", ex.get("pets_allowed")),
                            ("pets_allowed_quote", clip(getattr(reading, "pets_allowed_quote", "") or "")),
                            ("extraction", ex), ("withheld", dict(result.withheld)),
                            ("non_inferences", list(result.non_inferences)), ("flags", list(result.flags)),
                            ("parser_warnings", list(result.parser_warnings)),
                            ("service_animal_quote", clip(getattr(reading, "service_animal_quote", "") or "")),
                            ("brand_generic", bool(getattr(reading, "brand_generic", False))),
                            ("contradictions", list(getattr(reading, "contradictions", ()) or ())),
                            ("evidence_quotes", [clip(e.get("quote", "")) for e in result.evidence][:6]),
                        ])
                        rec["reader"] = rd
                        pa = ex.get("pets_allowed")
                        if blocked and pa is None:
                            rec["replay"] = "ACCESS_BLOCKED"
                        elif pa is True:
                            rec["replay"] = "PET_FRIENDLY_STATED"
                        elif pa is False:
                            rec["replay"] = "NO_PETS_STATED"
                        elif rd["service_animal_quote"]:
                            rec["replay"] = "SERVICE_ANIMAL_LANGUAGE_ONLY"
                        else:
                            rec["replay"] = "BLOCK_FOUND_BUT_SILENT"
                    except Exception as exc:  # noqa: BLE001
                        rec["reader"] = OrderedDict([("found", True), ("error", repr(exc))])
                        rec["replay"] = "READER_ERROR"

                # cross-classification against live authority
                cls = []
                confirmed = rec["identity"].get("confirmed")
                pb = rec["identity"].get("physical_binding") or {}
                if not confirmed and pb.get("bound"):
                    confirmed = True
                    rec["identity"]["confirmed_by"] = "PHYSICAL_BINDING"
                elif confirmed:
                    rec["identity"]["confirmed_by"] = "CANONICAL_ASSESSMENT"
                if rec["replay"] == "PET_FRIENDLY_STATED":
                    if live == "PET_FRIENDLY_LIVE":
                        cls.append("AGREES_WITH_LIVE_PF")
                        # facts agreement with the published row
                        pub = policy_by_key[key]["facts"]
                        ex = rec["reader"]["extraction"]
                        fee_pub = (pub.get("pet_fee") or {}).get("amount_cents")
                        fee_raw = ex.get("pet_fee")
                        fee_new = fee_raw.get("amount_minor") if isinstance(fee_raw, dict) else (fee_raw if isinstance(fee_raw, int) else None)
                        rec["facts_agreement"] = OrderedDict([("published_fee_cents", fee_pub), ("replayed_fee_minor", fee_new),
                                                              ("published_weight", pub.get("weight_limit")), ("replayed_weight", ex.get("weight_limit")),
                                                              ("published_count", pub.get("pet_count_limit")), ("replayed_count", ex.get("pet_count_limit"))])
                        if fee_pub is not None and fee_new is not None and fee_pub != fee_new:
                            cls.append("FEE_DISAGREES_WITH_PUBLISHED")
                    elif live == "VERIFIED_NO_PETS_LIVE":
                        cls.append("CONTRADICTS_LIVE_NO_PETS")
                    else:
                        cls.append("STRANDED_PF_EVIDENCE" if confirmed else "STRANDED_PF_EVIDENCE_IDENTITY_UNCONFIRMED")
                elif rec["replay"] == "NO_PETS_STATED":
                    if live == "VERIFIED_NO_PETS_LIVE":
                        cls.append("AGREES_WITH_LIVE_NO_PETS")
                    elif live == "PET_FRIENDLY_LIVE":
                        cls.append("CONTRADICTS_LIVE_PF")
                    else:
                        cls.append("STRANDED_NO_PETS_EVIDENCE" if confirmed else "STRANDED_NO_PETS_EVIDENCE_IDENTITY_UNCONFIRMED")
                if rec["committed_outcome"] in ("POLICY_NOT_FOUND", "CAPTURE_FAILED", "IDENTITY_UNCERTAIN") and rec["replay"] in ("PET_FRIENDLY_STATED", "NO_PETS_STATED"):
                    cls.append("NEWLY_READABLE_BY_CURRENT_READER")
                if rec["committed_outcome"] in ("AFFIRMATIVE_STRUCTURED", "AFFIRMATIVE_PARTIAL", "NEGATIVE") and rec["replay"] in ("SILENT_NO_POLICY_BLOCK", "BLOCK_FOUND_BUT_SILENT"):
                    cls.append("CURRENT_READER_SILENT_WHERE_PASS_READ")
                if confirmed is False and rec["identity_in_census"]:
                    cls.append("IDENTITY_NOT_CONFIRMED_BY_PAGE")
                if rec.get("reader", {}).get("brand_generic"):
                    cls.append("BRAND_GENERIC_BLOCK")
                rec["classification"] = cls or ["NO_AUTHORITY_SIGNAL"]
                records.append(rec)
            if limit and n > limit:
                break

    by_key = OrderedDict()
    for r in records:
        by_key.setdefault(r["identity_key"], []).append(r)

    def count(field):
        return OrderedDict(sorted(Counter(r.get(field) for r in records).items(), key=lambda kv: str(kv[0])))

    cls_counts = Counter(c for r in records for c in r.get("classification", []))
    stranded_pf = sorted({r["identity_key"] for r in records if "STRANDED_PF_EVIDENCE" in r.get("classification", [])})
    stranded_np = sorted({r["identity_key"] for r in records if "STRANDED_NO_PETS_EVIDENCE" in r.get("classification", [])})
    contradictions = [OrderedDict([("identity_key", r["identity_key"]), ("artifact", r["artifact_file"]), ("live_state", r["live_state"]),
                                   ("replay", r["replay"]), ("quote", r.get("reader", {}).get("pets_allowed_quote"))])
                      for r in records if any(c.startswith("CONTRADICTS_") for c in r.get("classification", []))]
    fee_dis = [OrderedDict([("identity_key", r["identity_key"]), ("artifact", r["artifact_file"]), ("facts", r.get("facts_agreement"))])
               for r in records if "FEE_DISAGREES_WITH_PUBLISHED" in r.get("classification", [])]

    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER), ("phase", "6 -- replay all owned Cleveland evidence"),
        ("market_id", MARKET_ID), ("as_of", "2026-09-01"),
        ("reader_provenance", OrderedDict([
            ("locator", "scripts/pettripfinder/brightdata/unlocker_capture.py: locate_policy_in_html / locate_policy_in_text"),
            ("recovery", "scripts/pettripfinder/acquisition/zero_cost_recovery.py: full_document_text"),
            ("reader", "scripts/pettripfinder/brightdata/policy_reading.py: parse -> to_extraction (Marriott: marriott_surface)"),
            ("identity", "scripts/pettripfinder/brightdata/policy_surface.py: read_identity -> assess_identity"),
        ])),
        ("network_requests", 0), ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("artifacts_replayed", len(records)), ("identities_covered", len(by_key)),
        ("replay_counts", count("replay")), ("locator_walk_counts", count("locator_walk")),
        ("committed_outcome_counts", count("committed_outcome")), ("live_state_counts", count("live_state")),
        ("classification_counts", OrderedDict(sorted(cls_counts.items()))),
        ("stranded_pet_friendly_identities", stranded_pf),
        ("stranded_no_pets_identities", stranded_np),
        ("live_contradictions", contradictions),
        ("fee_disagreements_with_published", fee_dis),
        ("records", records),
    ])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPORTS, f"{MARKET_ID.replace('-', '_')}_evidence_replay_006.json"))
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args(argv)
    rep = build(limit=args.limit)
    with open(args.out, "wb") as fh:
        fh.write((json.dumps(rep, indent=1, ensure_ascii=False, default=str) + "\n").encode("utf-8"))
    print("written", os.path.relpath(args.out, _DASH))
    print("artifacts", rep["artifacts_replayed"], "identities", rep["identities_covered"])
    print("replay:", dict(rep["replay_counts"]))
    print("walk:", dict(rep["locator_walk_counts"]))
    print("classification:", dict(rep["classification_counts"]))
    print("stranded PF:", rep["stranded_pet_friendly_identities"])
    print("stranded no-pets:", rep["stranded_no_pets_identities"])
    print("contradictions:", len(rep["live_contradictions"]), "fee disagreements:", len(rep["fee_disagreements_with_published"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
