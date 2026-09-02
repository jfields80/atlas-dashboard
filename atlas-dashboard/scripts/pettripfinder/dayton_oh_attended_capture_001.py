"""PTF-DAYTON-OH-HARDENED-REVALIDATION-001 -- Phase 10 (attended lane).

Ingest ONE attended Chrome capture -- a compact payload the operator's browser
produced in-page (url, title, sha256 of the full document, sha256 of the
visible text, the JSON-LD hotel node, the page's own address/phone lines and
the text windows around every pet / animal / dog mention) -- store it as an
owned artifact under the gitignored worker tree, bind the page to the census
row on its OWN street number / postal / telephone, run the canonical reader
over the visible-text windows, and append the result to the attended results
document. No vendor, no price. Nothing is written to authority.

    python ...dayton_oh_attended_capture_001.py ingest --identity-key K --queue-id Q --payload payload.json [--interaction "..."]
    python ...dayton_oh_attended_capture_001.py summary
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.brightdata import unlocker_capture as UC  # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR  # noqa: E402
from scripts.pettripfinder.brightdata import marriott_surface as MS  # noqa: E402
from scripts.pettripfinder.discovery import identity_dedup as DEDUP  # noqa: E402
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key  # noqa: E402

WORK_ORDER = "PTF-DAYTON-OH-HARDENED-REVALIDATION-001"
MARKET_ID = "dayton-oh"
RUN_ID = "dayton-hardened-attended-001"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
AUTH = os.path.join(PKG, "markets", "authority", MARKET_ID)
REPORTS = os.path.join(PKG, "markets", "reports")
RAW = os.path.join(_DASH, "data", "worker_runs", "pettripfinder", RUN_ID, "raw")
RESULTS = os.path.join(REPORTS, f"{MARKET_ID.replace('-', '_')}_attended_capture_001.json")
# Dayton's unresolved cohort reaches families Cleveland's attended cohort never
# did (Wingate, Hawthorn, Red Roof, Best Western, Radisson/Country Inn, ESA), so
# the family table is widened to cover them. Brand selection is not cosmetic: it
# chooses the reader, and a Marriott page read by the generic reader is a
# different reading of the same bytes.
BRANDS = [("MARRIOTT", r"marriott|courtyard|residence inn|springhill|fairfield|towneplace|ac hotel|aloft|westin|sheraton|moxy|element"),
          ("HILTON", r"hilton|hampton|embassy suites|homewood|home2|doubletree|tru by|tapestry|canopy|ardent"),
          ("IHG", r"holiday inn|crowne plaza|staybridge|candlewood|even hotel|avid|intercontinental|kimpton|hotel indigo"),
          ("CHOICE", r"comfort inn|comfort suites|quality inn|sleep inn|clarion|cambria|mainstay|suburban|econo lodge|rodeway|woodspring|studio 6"),
          ("WYNDHAM", r"wyndham|baymont|days inn|super 8|ramada|travelodge|la quinta|microtel|howard johnson|hawthorn|americinn|wingate"),
          ("ESA", r"extended stay america"), ("BEST_WESTERN", r"best western|surestay"), ("MOTEL6", r"motel 6"),
          ("RED_ROOF", r"red roof"), ("SONESTA", r"sonesta"), ("RADISSON", r"radisson|country inn"), ("DRURY", r"drury"),
          ("HYATT", r"hyatt"), ("MAGNUSON", r"magnuson")]


_SOURCE_SUFFIX = {"visible_text": "", "property_named_faq": "_FAQ", "hidden_text": "_HIDDEN_TEXT"}


def brand_of(name):
    n = name.lower()
    for fam, rx in BRANDS:
        if re.search(rx, n):
            return fam
    return "INDEPENDENT"


def read_json(p):
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def digits(v):
    return re.sub(r"[^0-9]", "", v or "")[-10:]


def ingest(args):
    census = {r["identity_key"]: r for r in read_json(os.path.join(PKG, "identity_census", f"{MARKET_ID}.json"))["hotels"]}
    policy_keys = {p["identity_key"] for p in read_json(os.path.join(PKG, f"hotel_policy_facts_{MARKET_ID}.json"))["hotels"]}
    excl_keys = {ptf_identity_key(e["canonical_name"]) for e in read_json(os.path.join(AUTH, "hotel_exclusions.json"))["exclusions"]}
    payload = read_json(args.payload)
    key = args.identity_key
    crow = census.get(key)
    name = crow["canonical_name"] if crow else key
    brand = brand_of(name)
    os.makedirs(RAW, exist_ok=True)
    artifact = OrderedDict([
        ("schema", "ptf-attended-capture/2.1-text-windows"), ("work_order", WORK_ORDER), ("run_id", RUN_ID), ("queue_id", args.queue_id),
        ("identity_key", key), ("captured_at", payload.get("captured_at") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        ("requested_url", args.requested_url or payload.get("url")), ("final_url", payload.get("url")), ("title", payload.get("title")),
        ("capture_method", "attended_browser"), ("interaction", args.interaction or ""),
        ("html_sha256", payload.get("html_sha256")), ("html_chars", payload.get("html_len")), ("text_sha256", payload.get("text_sha256")), ("text_chars", payload.get("text_len")),
        ("jsonld", payload.get("jsonld")), ("address_lines", payload.get("address_lines")), ("pet_windows", payload.get("pet_windows")),
        ("pet_windows_faq", payload.get("pet_windows_faq")),
        ("pet_windows_hidden", payload.get("pet_windows_hidden")),
        ("markup_property_record", payload.get("markup_property_record")),
    ])
    fname = "%s-%s.json" % (args.queue_id, re.sub(r"[^a-z0-9]+", "-", key).strip("-"))
    path = os.path.join(RAW, fname)
    blob = (json.dumps(artifact, indent=1, ensure_ascii=False) + "\n").encode("utf-8")
    with open(path, "wb") as fh:
        fh.write(blob)
    artifact_sha = hashlib.sha256(blob).hexdigest()

    # identity binding on the page's own address/phone lines + JSON-LD
    hay = "\n".join(payload.get("address_lines") or []) + "\n" + json.dumps(payload.get("jsonld") or "")
    c_street = (crow or {}).get("address") or ""
    # The house number is captured WITH any letter suffix, and matched on an
    # exact token boundary rather than \b. Dayton has a same-campus pair --
    # Wingate at 6960 Miller Ln and Baymont at 6960B Miller Ln -- so both halves
    # matter: \b6960\b does not match "6960B" at all (the Baymont bound to
    # nothing), and a suffix-tolerant \b6960[A-Za-z]?\b would match the Baymont's
    # page from the Wingate's census row and bind the wrong hotel.
    c_num = (re.match(r"\s*(\d+[A-Za-z]?)", c_street) or [None, ""])[1] if c_street else ""
    c_postal = ((crow or {}).get("postal_code") or "")[:5]
    c_phone = digits((crow or {}).get("phone") or "")
    parts = c_street.split()
    street_ok = bool(c_num) and len(parts) > 1 and bool(re.search(
        r"(?<![0-9A-Za-z])" + re.escape(c_num) + r"(?![0-9A-Za-z])[^\n]{0,40}" + re.escape(parts[1][:4]),
        hay, re.I))
    postal_ok = bool(c_postal) and bool(re.search(r"\b" + c_postal + r"\b", hay))
    phone_ok = bool(c_phone) and c_phone in re.sub(r"[^0-9]", "", hay)
    binding = OrderedDict([("street_number_agrees", street_ok), ("postal_agrees", postal_ok), ("phone_agrees", phone_ok),
                           ("bound", (street_ok and postal_ok) or (phone_ok and (postal_ok or street_ok)))])

    # reader over the visible windows (hidden windows only as a fallback, and labelled)
    def read(windows, label):
        text = "\n\n".join(windows or [])
        if not text.strip():
            return None
        hit = UC.locate_policy_in_text(text)
        if not hit.found:
            return OrderedDict([("found", False), ("source", label)])
        if brand == "MARRIOTT":
            reading = MS.parse_policy_block(hit.text, locator_id=WORK_ORDER)
            result = MS.to_extraction(reading, location=MARKET_ID)
        else:
            reading = PR.parse(hit.text, strategy=hit.strategy or WORK_ORDER)
            result = PR.to_extraction(reading, location=MARKET_ID)
        return OrderedDict([("found", True), ("source", label), ("block", hit.text[:600]), ("pets_allowed", result.extraction.get("pets_allowed")),
                            ("pets_allowed_quote", (getattr(reading, "pets_allowed_quote", "") or "")[:300]), ("extraction", result.extraction), ("withheld", dict(result.withheld)),
                            ("evidence_quotes", [e.get("quote", "")[:300] for e in result.evidence][:8]), ("service_animal_quote", (getattr(reading, "service_animal_quote", "") or "")[:200]),
                            ("brand_generic", bool(getattr(reading, "brand_generic", False))), ("parser_warnings", list(result.parser_warnings))])

    # Read order: the property's own visible policy section first, then its
    # property-NAMED FAQ (an accordion answer is in the DOM whether or not the
    # operator expanded it, and it names the hotel, so it binds harder than a
    # brand-generic paragraph), then any remaining hidden text. Each source is
    # labelled on the record; none is silently substituted for another.
    rd = read(payload.get("pet_windows"), "visible_text") or OrderedDict([("found", False), ("source", "visible_text")])
    for windows, label in ((payload.get("pet_windows_faq"), "property_named_faq"),
                           (payload.get("pet_windows_hidden"), "hidden_text")):
        if rd.get("found"):
            break
        alt = read(windows, label)
        if alt and alt.get("found"):
            rd = alt
    pa = rd.get("pets_allowed")

    # The brand markup property record (IHG/Wyndham ship one) is recorded as
    # CORROBORATION and is never the source of a fact. It is a key/value blob,
    # not prose: reformatting it into a sentence makes the reader say True for
    # '"petsAllowed" : "false"', so this pass refuses to parse it and only
    # compares its own petsAllowed flag against what the prose read said.
    mrec = payload.get("markup_property_record") or {}
    corrob = None
    if mrec:
        flag = str(mrec.get("petsAllowed", "")).strip().lower()
        markup_pa = True if flag == "true" else False if flag == "false" else None
        corrob = OrderedDict([
            ("markup_pets_allowed", markup_pa),
            ("markup_pet_description", (mrec.get("petDescription") or "")[:300]),
            ("fields", OrderedDict(sorted((k, str(v)[:200]) for k, v in mrec.items()))),
            ("agrees_with_prose_read", None if (markup_pa is None or pa is None) else (markup_pa == pa)),
            ("role", "CORROBORATION_ONLY -- never parsed into a published fact"),
        ])
    if args.outcome_override:
        cls = args.outcome_override
    elif not binding["bound"]:
        cls = "IDENTITY_NOT_BOUND_ON_PAGE"
    elif pa is True:
        cls = "PET_FRIENDLY_STATED_ATTENDED" + _SOURCE_SUFFIX.get(rd.get("source"), "_HIDDEN_TEXT")
    elif pa is False:
        cls = "NO_PETS_STATED_ATTENDED" + _SOURCE_SUFFIX.get(rd.get("source"), "_HIDDEN_TEXT")
    elif rd.get("service_animal_quote"):
        cls = "SERVICE_ANIMAL_LANGUAGE_ONLY"
    elif rd.get("found"):
        cls = "BLOCK_FOUND_BUT_SILENT"
    else:
        cls = "SOURCE_SILENT_ATTENDED"
    record = OrderedDict([
        ("queue_id", args.queue_id), ("identity_key", key), ("hotel", name), ("brand", brand), ("requested_url", args.requested_url or payload.get("url")), ("final_url", payload.get("url")),
        ("title", payload.get("title")), ("artifact_file", fname), ("artifact_sha256", artifact_sha), ("html_sha256", payload.get("html_sha256")), ("text_sha256", payload.get("text_sha256")),
        ("captured_at", artifact["captured_at"]), ("interaction", args.interaction or ""), ("identity_binding", binding), ("reader", rd), ("markup_corroboration", corrob), ("classification", cls),
        ("live_state", "PET_FRIENDLY_LIVE" if key in policy_keys else "VERIFIED_NO_PETS_LIVE" if key in excl_keys else "UNRESOLVED_OR_NEW"), ("notes", args.note or ""),
    ])
    doc = read_json(RESULTS) if os.path.exists(RESULTS) else OrderedDict([("schema", "ptf-attended-capture-results/1.0"), ("work_order", WORK_ORDER), ("run_id", RUN_ID), ("market_id", MARKET_ID),
                                                                            ("capture_method", "attended_browser (operator Chrome; compact in-page payload: document sha256, visible-text sha256, JSON-LD, address lines, pet text windows)"),
                                                                            ("paid_provider_calls", 0), ("usd_spent", 0.0), ("results", [])])
    doc["results"] = [r for r in doc["results"] if r["queue_id"] != args.queue_id] + [record]
    doc["rows_captured"] = len(doc["results"])
    doc["outcome_counts"] = OrderedDict(sorted(Counter(r["classification"] for r in doc["results"]).items()))
    with open(RESULTS, "wb") as fh:
        fh.write((json.dumps(doc, indent=1, ensure_ascii=False, default=str) + "\n").encode("utf-8"))
    print(json.dumps(OrderedDict([("queue_id", args.queue_id), ("identity_key", key), ("classification", cls), ("binding", binding), ("pets_allowed", pa),
                                  ("quote", rd.get("pets_allowed_quote")), ("extraction", rd.get("extraction")), ("evidence", rd.get("evidence_quotes"))]), default=str)[:1500])
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    a = sub.add_parser("ingest")
    a.add_argument("--identity-key", required=True)
    a.add_argument("--queue-id", required=True)
    a.add_argument("--payload", required=True)
    a.add_argument("--requested-url", default="")
    a.add_argument("--interaction", default="")
    a.add_argument("--note", default="")
    a.add_argument("--outcome-override", default="")
    sub.add_parser("summary")
    args = ap.parse_args(argv)
    if args.cmd == "ingest":
        return ingest(args)
    doc = read_json(RESULTS)
    print(json.dumps(doc["outcome_counts"]))
    for r in doc["results"]:
        print(" ", r["queue_id"], r["identity_key"], r["classification"], r["identity_binding"]["bound"], (r["reader"] or {}).get("pets_allowed_quote"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
