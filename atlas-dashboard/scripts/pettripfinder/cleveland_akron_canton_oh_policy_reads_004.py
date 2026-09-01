"""PTF-CLEVELAND-AKRON-CANTON-HARDENED-POLICY-004 -- Phases 1, 3, 4, 5, 9.

Free policy evidence for the remaining shadow-admitted Cleveland identities
(the Order-002/003 rows without publication-grade policy evidence) plus the
two identities this order reads for the first time (the Holiday Inn Express
Richfield same-address question and Red Roof Akron after its postal proof),
through the same lanes Orders 001 and 003 used:

    cohort            Phase 1: rebuild the cohort mechanically from the shadow
                      census, the live package and the Order-003 results
    run-static        acquisition.direct_http_capture.run_attempt (one HTTPS
                      GET through the paid lanes' own gates) followed by
                      market_observation_store.observation_for; artifacts land
                      under data/acquisition/<run>/<slug>/attempt-01/
    ingest-attended   one attended Chrome payload (document sha256, JSON-LD,
                      address lines, pet text windows) read by the canonical
                      reader over the visible-text windows, identity bound on
                      the page's OWN street number + postal (+ phone)
    ingest-owned      the same ingestion over an OWNED full-page artifact from
                      an earlier Cleveland pass (Phase 3: reuse before reading)
    classify          exactly one of CLEAN_PET_FRIENDLY / CLEAN_VERIFIED_NO_PETS /
                      POLICY_NOT_FOUND / SOURCE_SILENT / SOURCE_CONTRADICTORY /
                      FOUNDER_EXCEPTION / IDENTITY_MISMATCH / CAPTURE_FAILED

Property routes located this order come from the brands' own pages (the ESA
city page, Choice listing pages, the IHG search list) and are recorded on the
row. No paid provider. Nothing is written to live authority.
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
from scripts.pettripfinder.brightdata import unlocker_capture as UC  # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR  # noqa: E402
from scripts.pettripfinder.brightdata import marriott_surface as MS  # noqa: E402
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key  # noqa: E402
from scripts.pettripfinder.discovery import identity_dedup as DEDUP  # noqa: E402
from scripts.pettripfinder.markets.contract import slugify  # noqa: E402

WORK_ORDER = "PTF-CLEVELAND-AKRON-CANTON-HARDENED-POLICY-004"
MARKET_ID = "cleveland-akron-canton-oh"
M = MARKET_ID.replace("-", "_")
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
AUTH = os.path.join(PKG, "markets", "authority", MARKET_ID)
REPORTS = os.path.join(PKG, "markets", "reports")
ADMISSION = os.path.join(PKG, "identity_census_admission", f"{MARKET_ID}.json")
RESULTS = os.path.join(REPORTS, f"{M}_policy_reads_004.json")
RUN_ID = f"{M}_policy_reads_004"
RAW = os.path.join(_DASH, "data", "worker_runs", "pettripfinder", "cleveland-hardened-policy-004", "raw")
# Hosts that render the policy client-side (attended lane). extendedstayamerica.com is NOT here: its
# property pages carry the policy in the served document (Indianapolis free policy pass 008).
ATTENDED_HOSTS = ("hilton.com", "marriott.com", "ihg.com", "choicehotels.com", "bestwestern.com", "radissonhotels", "redroof.com", "hyatt.com", "ritzcarlton.com", "wyndhamhotels.com", "sonesta.com")
BRANDS = [("MARRIOTT", r"marriott|courtyard|residence inn|springhill|fairfield|towneplace|ac hotel|aloft|westin|sheraton|ritz|autograph"),
          ("HILTON", r"hilton|hampton|embassy suites|homewood|home2|doubletree|tru by"), ("IHG", r"holiday inn|crowne plaza|staybridge|candlewood|kimpton|hotel indigo"),
          ("CHOICE", r"comfort inn|comfort suites|quality inn|sleep inn|clarion|cambria|mainstay|suburban|econo lodge|country inn"),
          ("WYNDHAM", r"wyndham|baymont|days inn|super 8|ramada|travelodge|la quinta|microtel|wingate"), ("ESA", r"extended stay america"),
          ("BEST_WESTERN", r"best western"), ("SONESTA", r"sonesta"), ("RED_ROOF", r"red roof"), ("MOTEL6", r"motel 6")]

ESA = "https://www.extendedstayamerica.com/hotels/oh/cleveland/"
CHOICE = "https://www.choicehotels.com/ohio/"
# Property routes located this order from the brands' own pages (identity_key -> (url, how located)).
ROUTES_004 = {
    "extended stay america suites cleveland airport north olmsted": (ESA + "airport-north-olmsted", "ESA city page (static) property link"),
    "extended stay america suites cleveland westlake": (ESA + "westlake", "ESA city page (static) property link"),
    "extended stay america suites cleveland beachwood orange place south": (ESA + "beachwood-orange-place-south", "ESA city page (static) property link"),
    "extended stay america suites cleveland brooklyn": (ESA + "brooklyn", "ESA city page (static) property link"),
    "extended stay america select suites cleveland mentor": (ESA + "mentor", "ESA city page (static) property link"),
    "extended stay america suites cleveland great northern mall": (ESA + "great-northern-mall", "ESA city page (static) property link"),
    "extended stay america suites cleveland middleburg heights": (ESA + "middleburg-heights", "ESA city page (static) property link"),
    "extended stay america select suites cleveland airport": (ESA + "airport", "ESA city page (static) property link"),
    "comfort inn and suites cuyahoga falls akron": (CHOICE + "cuyahoga-falls/comfort-inn-hotels/oh842", "Choice Cuyahoga Falls listing page (attended): 1420 Main Street 44221"),
    "country inn and suites by radisson macedonia northfield": (CHOICE + "macedonia/country-inn-suites-hotels/oh875", "Choice Avon listing page JSON-LD (owned P3-002 artifact)"),
    "comfort inn cleveland airport": (CHOICE + "middleburg-heights/comfort-inn-hotels/oh439", "Choice Avon listing page JSON-LD (owned P3-002 artifact)"),
    "quality inn middleburg heights near cleveland airport": (CHOICE + "middleburg-heights/quality-inn-hotels/oh716", "Choice Avon listing page JSON-LD (owned P3-002 artifact)"),
    "mainstay suites middleburg heights cleveland airport": (CHOICE + "middleburg-heights/mainstay-hotels/oh837", "Choice Avon listing page JSON-LD (owned P3-002 artifact)"),
    "quality inn and suites oakwood village cleveland south": (CHOICE + "oakwood-village/quality-inn-hotels/oh643", "Choice Avon listing page JSON-LD (owned P3-002 artifact)"),
    "candlewood suites cleveland south independence": ("https://www.ihg.com/candlewood/hotels/us/en/independence/cleip/hoteldetail", "IHG search list (attended) hotel link"),
    "candlewood suites beachwood cleveland": ("https://www.ihg.com/candlewood/hotels/us/en/beachwood/cleop/hoteldetail", "IHG search list (attended) hotel link"),
}
# Identities read for the first time this order (not shadow rows yet): name, street, city, postal, phone, url, how located.
EXTRA = [
    ("Holiday Inn Express & Suites Cleveland-Richfield", "5171 Brecksville Road", "Richfield", "44286", "+1-330-523-5000", "https://www.ihg.com/holidayinnexpress/hotels/us/en/richfield/clerf/hoteldetail", "IHG search list (attended) hotel link; Phase 6 same-address question"),
    ("Red Roof Inn Akron", "2939 S Arlington Rd", "Akron", "44312", "", "https://www.redroof.com/property/oh/akron/rri207", "identity_reads_002 TM-005 route; postal proven this order from the page's own property data"),
    ("Extended Stay America Select Suites Cleveland - Airport", "20829 Emerald Pkwy", "Cleveland", "44135", "", ESA + "airport", "ESA city page (static) property link; successor question on the registered WoodSpring premises"),
]
SERVICE_ONLY = re.compile(r"\bservice animals?\b", re.I)


def brand_of(name):
    n = (name or "").lower()
    for fam, rx in BRANDS:
        if re.search(rx, n):
            return fam
    return "INDEPENDENT"


def host_of(url):
    m = re.match(r"https?://([^/]+)", url or "")
    return m.group(1).lower().replace("www.", "") if m else ""


def read_json(p):
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as fh:
        fh.write((json.dumps(d, indent=1, ensure_ascii=False, default=str) + "\n").encode("utf-8"))


def as_plain(o):
    if dataclasses.is_dataclass(o):
        return {k: as_plain(v) for k, v in dataclasses.asdict(o).items()}
    if isinstance(o, (list, tuple)):
        return [as_plain(x) for x in o]
    if isinstance(o, dict):
        return {k: as_plain(v) for k, v in o.items()}
    return o


def digits(v):
    return re.sub(r"[^0-9]", "", v or "")[-10:]


def route_for(h):
    key = h["identity_key"]
    if key in ROUTES_004:
        return ROUTES_004[key][0], ROUTES_004[key][1]
    url = h.get("official_url") or ""
    return url, ("row official_url" if url else "")


def targets():
    """Every shadow-admitted row plus the EXTRA identities; the cohort filter is applied in cmd_cohort."""
    shadow = read_json(ADMISSION)
    rows = [h for h in shadow["hotels"] if str((h.get("admission") or {}).get("status", "")).startswith("SHADOW_ADMITTED")]
    for name, street, city, pc, phone, url, how in EXTRA:
        rows.append(OrderedDict([("identity_key", ptf_identity_key(name)), ("canonical_name", name), ("slug", slugify(name)), ("address", street), ("city", city), ("postal_code", pc), ("phone", phone),
                                 ("official_url", url), ("street_identity", "%s|%s" % (street.lower(), pc)), ("extra_004", how)]))
    return rows


def load():
    return read_json(RESULTS) if os.path.exists(RESULTS) else OrderedDict([("schema", "ptf-shadow-policy-reads/1.1"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID), ("run_id", RUN_ID),
                                                                             ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", 0), ("browser_page_loads", 0), ("rows", [])])


def upsert(doc, row):
    doc["rows"] = [r for r in doc["rows"] if r["identity_key"] != row["identity_key"]] + [row]
    write_json(RESULTS, doc)


# ---------------------------------------------------------------- Phase 1: cohort
def cmd_cohort(args):
    doc = load()
    live = {p["identity_key"] for p in read_json(os.path.join(PKG, f"hotel_policy_facts_{MARKET_ID}.json"))["hotels"]}
    excl = {ptf_identity_key(e["canonical_name"]) for e in read_json(os.path.join(AUTH, "hotel_exclusions.json"))["exclusions"]}
    reads3 = read_json(os.path.join(REPORTS, f"{M}_policy_reads_003.json"))
    c3 = {c["identity_key"]: c for c in reads3["classification"]}
    owned = {"la quinta inn and suites by wyndham cleveland airport west": "data/worker_runs/pettripfinder/cleveland-attended-capture-003/raw/P3-061-la-quinta-cleveland-airport-west.json"}
    out = []
    for h in targets():
        key = h["identity_key"]
        url, how = route_for(h)
        prior = c3.get(key, {}).get("classification")
        if key in live or key in excl:
            continue  # already authority
        if prior in ("CLEAN_PET_FRIENDLY", "CLEAN_VERIFIED_NO_PETS"):
            continue  # publication-grade evidence already bound in Order 003
        if key in owned:
            start, why = "OWNED_EVIDENCE_REUSE", "owned attended artifact carries the operative property policy (%s)" % owned[key]
        elif not url:
            start, why = "IDENTITY_BLOCKED", "no first-party route located"
        elif any(x in host_of(url) for x in ATTENDED_HOSTS):
            start, why = "FREE_ATTENDED", "policy region is client-rendered on %s" % host_of(url)
        else:
            start, why = "FREE_STATIC", "served document carries the policy on %s" % host_of(url)
        out.append(OrderedDict([("identity_key", key), ("canonical_name", h["canonical_name"]), ("brand", brand_of(h["canonical_name"])), ("route", url), ("route_located_by", how),
                                ("order_003_result", prior), ("shadow_row", "extra_004" not in h), ("starting_lane", start), ("why", why)]))
    doc["cohort"] = out
    doc["cohort_counts"] = OrderedDict(sorted(Counter(x["starting_lane"] for x in out).items()))
    doc["cohort_size"] = len(out)
    write_json(RESULTS, doc)
    print("cohort", len(out), dict(doc["cohort_counts"]))
    for x in out:
        print(" ", x["starting_lane"].ljust(21), x["identity_key"][:52].ljust(52), x["order_003_result"] or "-", "|", x["route"][:80])
    return 0


# ---------------------------------------------------------------- Phase 4: static lane
def cmd_run_static(args):
    doc = load()
    done = {r["identity_key"] for r in doc["rows"]}
    cohort = {c["identity_key"]: c for c in doc.get("cohort", [])}
    run_dir = Path(_DASH) / "data" / "acquisition" / RUN_ID
    run_dir.mkdir(parents=True, exist_ok=True)
    for h in targets():
        key = h["identity_key"]
        c = cohort.get(key)
        if not c or c["starting_lane"] != "FREE_STATIC" or (key in done and not args.refetch):
            continue
        if args.only and key not in args.only:
            continue
        url = c["route"]
        brand = brand_of(h["canonical_name"])
        target = BC.CaptureTarget(slug=h["slug"], hotel=h["canonical_name"], requested_url=url, property_code=DEDUP.property_code({"official_url": url}), market_id=MARKET_ID,
                                  normalized_name=key, identity_key=key, street_identity=h.get("street_identity", ""), expected_postal_code=h["postal_code"], expected_street=h["address"],
                                  expected_phone=h.get("phone", ""), expected_locality=h.get("city", ""), identity_brand=brand, census_matched=True)
        time.sleep(2.0)
        attempt, payload = DHC.run_attempt(target, 1, run_dir=run_dir, brand=brand)
        doc["free_http_requests"] += 1
        a = as_plain(attempt)
        attempt_dir = run_dir / h["slug"] / "attempt-01"
        row = OrderedDict([("identity_key", key), ("canonical_name", h["canonical_name"]), ("brand", brand), ("lane", "STATIC"), ("requested_url", url), ("final_url", a.get("final_url")),
                           ("outcome", a.get("outcome")), ("detail", (a.get("detail") or "")[:300]), ("identity_assessment", a.get("identity")),
                           ("document_sha256", hashlib.sha256((attempt_dir / "rendered.html").read_bytes()).hexdigest() if (attempt_dir / "rendered.html").is_file() else None),
                           ("artifact_dir", str(attempt_dir.relative_to(_DASH)) if attempt_dir.is_dir() else ""), ("captured_at", a.get("started_at"))])
        if a.get("outcome") == "VALID" and (attempt_dir / "policy-block.txt").is_file():
            result = {"identity_key": key, "canonical_name": h["canonical_name"], "brand": brand, "corridor": h.get("corridor", ""), "source_url": url, "outcome": "VALID",
                      "final_url": a.get("final_url") or url, "artifact_dir": str(attempt_dir), "identity_confirmed": bool((a.get("identity") or {}).get("confirmed", True)), "locator_strategy": ""}
            try:
                obs, grade, refusal = MOS.observation_for(result, run_id=RUN_ID, market_id=MARKET_ID, census_row=h)
                o = (obs or {}).get("observation") or {}
                row["observation"] = OrderedDict([("extraction", o.get("extraction")), ("evidence", o.get("evidence")), ("withheld_fields", (obs or {}).get("withheld_fields")),
                                                  ("publication_grade", grade), ("refusal_reason", refusal), ("reader_provenance", (obs or {}).get("reader_provenance"))])
            except Exception as exc:  # noqa: BLE001
                row["observation_error"] = repr(exc)
        upsert(doc, row)
        print(" ", key, a.get("outcome"), (a.get("detail") or "")[:80], (row.get("observation") or {}).get("extraction"))
    return 0


# ---------------------------------------------------------------- reader over text windows
def read_windows(windows, brand):
    text = "\n\n".join(windows or [])
    if not text.strip():
        return None
    hit = UC.locate_policy_in_text(text)
    if not hit.found:
        return OrderedDict([("found", False)])
    reader_used = "generic"
    reading = PR.parse(hit.text, strategy=hit.strategy or WORK_ORDER)
    result = PR.to_extraction(reading, location=MARKET_ID)
    if brand == "MARRIOTT":
        m_reading = MS.parse_policy_block(hit.text, locator_id=WORK_ORDER)
        m_result = MS.to_extraction(m_reading, location=MARKET_ID)
        if m_result.extraction.get("pets_allowed") is not None or result.extraction.get("pets_allowed") is None:
            reading, result, reader_used = m_reading, m_result, "marriott"
        else:
            reader_used = "generic (marriott reader left pets_allowed SOURCE_SILENT on the FAQ form)"
    return OrderedDict([("found", True), ("reader_used", reader_used), ("block", hit.text[:700]), ("pets_allowed", result.extraction.get("pets_allowed")), ("pets_allowed_quote", (getattr(reading, "pets_allowed_quote", "") or "")[:300]),
                        ("extraction", result.extraction), ("withheld", dict(result.withheld)), ("evidence_quotes", [e.get("quote", "")[:300] for e in result.evidence][:8]),
                        ("service_animal_quote", (getattr(reading, "service_animal_quote", "") or "")[:200]), ("brand_generic", bool(getattr(reading, "brand_generic", False))),
                        ("contradictions", list(getattr(reading, "contradictions", ()) or ())), ("parser_warnings", list(result.parser_warnings))])


def ingest(h, payload, lane, requested_url, interaction, note, outcome, source_artifact=""):
    doc = load()
    os.makedirs(RAW, exist_ok=True)
    brand = brand_of(h["canonical_name"])
    fname = "PR-%s.json" % re.sub(r"[^a-z0-9]+", "-", h["identity_key"]).strip("-")
    artifact = OrderedDict([("schema", "ptf-attended-capture/2.1-text-windows"), ("work_order", WORK_ORDER), ("identity_key", h["identity_key"]), ("captured_at", payload.get("captured_at")),
                            ("requested_url", requested_url or payload.get("url")), ("final_url", payload.get("url")), ("title", payload.get("title")),
                            ("capture_method", "attended_browser" if lane == "ATTENDED" else "owned_attended_artifact"), ("source_artifact", source_artifact), ("interaction", interaction or ""),
                            ("html_sha256", payload.get("html_sha256")), ("text_sha256", payload.get("text_sha256")), ("jsonld", payload.get("jsonld")), ("address_lines", payload.get("address_lines")),
                            ("pet_windows", payload.get("pet_windows")), ("pet_windows_hidden", payload.get("pet_windows_hidden")), ("notes", payload.get("notes")),
                            ("property_code", payload.get("property_code")), ("pre_interaction_html_sha256", payload.get("pre_interaction_html_sha256")), ("embedded_property_data", payload.get("embedded_property_data"))])
    blob = (json.dumps(artifact, indent=1, ensure_ascii=False) + "\n").encode("utf-8")
    open(os.path.join(RAW, fname), "wb").write(blob)
    hay = "\n".join(payload.get("address_lines") or []) + "\n" + json.dumps(payload.get("jsonld") or "")
    c_num = (re.match(r"\s*(\d+)", h["address"]) or [None, ""])[1]
    c_pc, c_ph = h["postal_code"], digits(h.get("phone"))
    parts = h["address"].split()
    street_ok = bool(c_num) and len(parts) > 1 and bool(re.search(r"\b" + re.escape(c_num) + r"\b[^\n]{0,40}" + re.escape(parts[1][:4]), hay, re.I))
    number_ok = bool(c_num) and bool(re.search(r"\b" + re.escape(c_num) + r"\b", hay))
    postal_ok = bool(re.search(r"\b" + c_pc + r"\b", hay))
    phone_ok = bool(c_ph) and c_ph in re.sub(r"[^0-9]", "", hay)
    binding = OrderedDict([("street_number_agrees", street_ok), ("house_number_agrees", number_ok), ("postal_agrees", postal_ok), ("phone_agrees", phone_ok),
                           ("bound", (street_ok and postal_ok) or (number_ok and postal_ok) or (phone_ok and (postal_ok or street_ok)))])
    rd = read_windows(payload.get("pet_windows"), brand) or OrderedDict([("found", False)])
    src = "visible_text"
    if not rd.get("found") and payload.get("pet_windows_hidden"):
        rd2 = read_windows(payload.get("pet_windows_hidden"), brand)
        if rd2 and rd2.get("found"):
            rd, src = rd2, "hidden_text"
    row = OrderedDict([("identity_key", h["identity_key"]), ("canonical_name", h["canonical_name"]), ("brand", brand), ("lane", lane), ("requested_url", requested_url or payload.get("url")),
                       ("final_url", payload.get("url")), ("outcome", outcome or ("VALID" if rd.get("found") else "POLICY_NOT_FOUND")), ("identity_binding", binding), ("document_sha256", payload.get("html_sha256")),
                       ("text_sha256", payload.get("text_sha256")), ("artifact_file", fname), ("artifact_sha256", hashlib.sha256(blob).hexdigest()), ("source_artifact", source_artifact),
                       ("captured_at", payload.get("captured_at")), ("interaction", interaction or ""), ("reader", rd), ("reader_source", src), ("note", note or "")])
    upsert(doc, row)
    print(json.dumps(OrderedDict([("identity_key", h["identity_key"]), ("lane", lane), ("bound", binding["bound"]), ("pets_allowed", rd.get("pets_allowed")), ("quote", rd.get("pets_allowed_quote")), ("extraction", rd.get("extraction"))]), default=str)[:700])
    return 0


def row_for(identity_key):
    rows = {h["identity_key"]: h for h in targets()}
    return rows[identity_key]


def cmd_ingest_attended(args):
    h = row_for(args.identity_key)
    payload = read_json(args.payload)
    doc = load()
    doc["browser_page_loads"] = doc.get("browser_page_loads", 0) + 1
    write_json(RESULTS, doc)
    return ingest(h, payload, "ATTENDED", args.requested_url, args.interaction, args.note, args.outcome)


def cmd_ingest_owned(args):
    """Reuse an owned full-page attended artifact (earlier Cleveland pass): no page is loaded."""
    h = row_for(args.identity_key)
    art = read_json(os.path.join(_DASH, args.artifact))
    text = art.get("text") or ""
    windows = [m.group(0).strip()[:900] for m in re.finditer(r"[^\n]{0,300}\b(?:pets?|dogs?|animals?)\b[^\n]{0,600}", text, re.I)]
    windows = list(OrderedDict.fromkeys(windows))[:8]
    jsonld = []
    for j in art.get("jsonld") or []:
        try:
            jsonld.append(json.loads(j) if isinstance(j, str) else j)
        except Exception:  # noqa: BLE001
            jsonld.append(j)
    addr = list(OrderedDict.fromkeys(re.findall(r"[^\n]*\b(?:OH|Ohio)\b[^\n]*\b44\d{3}\b[^\n]*", text) + re.findall(r"\+?1?[-. (]*\d{3}[-. )]*\d{3}[-. ]*\d{4}", text)))[:8]
    payload = OrderedDict([("url", art.get("final_url")), ("title", art.get("title")), ("captured_at", art.get("captured_at")), ("html_sha256", art.get("html_sha256")), ("text_sha256", art.get("text_sha256")),
                           ("jsonld", jsonld), ("address_lines", addr), ("pet_windows", windows), ("pet_windows_hidden", []),
                           ("notes", "owned artifact %s (work order %s, interaction %r) reused; no page loaded this order" % (args.artifact, art.get("work_order"), art.get("interaction")))])
    return ingest(h, payload, "OWNED_EVIDENCE_REUSE", art.get("requested_url"), art.get("interaction") or "", args.note, "", source_artifact=args.artifact)


def cmd_record_failure(args):
    h = row_for(args.identity_key)
    doc = load()
    upsert(doc, OrderedDict([("identity_key", h["identity_key"]), ("canonical_name", h["canonical_name"]), ("brand", brand_of(h["canonical_name"])), ("lane", args.lane), ("requested_url", args.requested_url),
                             ("final_url", None), ("outcome", args.outcome), ("detail", args.detail), ("document_sha256", None), ("captured_at", None)]))
    print(" ", h["identity_key"], args.outcome, args.detail[:80])
    return 0


# ---------------------------------------------------------------- Phase 9: classify
def cmd_classify(args):
    doc = load()
    have = {r["identity_key"]: r for r in doc["rows"]}
    cohort = {c["identity_key"]: c for c in doc.get("cohort", [])}
    out = []
    for key, c in cohort.items():
        r = have.get(key)
        rec = OrderedDict([("identity_key", key), ("canonical_name", c["canonical_name"]), ("route", c["route"]), ("starting_lane", c["starting_lane"]), ("lane", (r or {}).get("lane"))])
        if r is None:
            cls, why = "CAPTURE_FAILED", "no read performed this order (%s)" % c["why"]
        elif r["lane"] == "STATIC":
            o = r.get("observation") or {}
            ext = o.get("extraction") or {}
            pa = ext.get("pets_allowed")
            grade = str((o.get("publication_grade") or {}).get("verdict") or (o.get("publication_grade") or {}).get("grade") or "")
            if r["outcome"] == "IDENTITY_MISMATCH":
                cls, why = "IDENTITY_MISMATCH", r.get("detail")
            elif r["outcome"] in ("ACCESS_DENIED", "NAVIGATION_FAILED", "CAPTURE_FAILED", "BLANK_PAGE", "UNEXPECTED_PAGE", "ATTENDED_ACCESS_BLOCKED"):
                cls, why = "CAPTURE_FAILED", "%s: %s" % (r["outcome"], r.get("detail"))
            elif r["outcome"] == "UNHYDRATED":
                cls, why = "CAPTURE_FAILED", "static lane cannot read it: the policy region is a client-rendered template"
            elif r["outcome"] == "POLICY_NOT_FOUND":
                cls, why = "POLICY_NOT_FOUND", r.get("detail")
            elif pa is not None and grade.endswith("CONFIRMED") and all(len((e.get("quote") or "").split()) <= 2 for e in (o.get("evidence") or [])):
                cls, why = "FOUNDER_EXCEPTION", "the only quote is a phrase, marketing copy rather than a policy statement with terms"
            elif pa is True and grade.endswith("CONFIRMED"):
                cls, why = "CLEAN_PET_FRIENDLY", "static first-party capture, publication grade"
            elif pa is False and grade.endswith("CONFIRMED"):
                cls, why = "CLEAN_VERIFIED_NO_PETS", "static first-party capture, publication grade"
            elif pa is None:
                cls, why = "SOURCE_SILENT", "block found but no pets statement"
            else:
                cls, why = "FOUNDER_EXCEPTION", "policy read but not publication grade: %s" % o.get("refusal_reason")
        else:
            rd = r.get("reader") or {}
            pa = rd.get("pets_allowed")
            bound = (r.get("identity_binding") or {}).get("bound")
            if r.get("outcome") in ("CAPTURE_FAILED", "ATTENDED_ACCESS_BLOCKED"):
                cls, why = "CAPTURE_FAILED", "%s: %s" % (r.get("outcome"), r.get("detail") or r.get("note") or r.get("interaction"))
            elif r.get("outcome") == "IDENTITY_MISMATCH" or not bound:
                cls, why = "IDENTITY_MISMATCH", "page's own address does not bind to the admitted premises"
            elif rd.get("contradictions"):
                cls, why = "SOURCE_CONTRADICTORY", "; ".join(str(x) for x in rd["contradictions"])[:200]
            elif not rd.get("found"):
                # The canonical reader found no bounded block. If the page nevertheless states an explicit
                # acceptance/refusal in its own words, that is a reader false negative to put before the
                # founder with the exact quote (Kimpton precedent, Order 001) -- never a silent page.
                windows = list((read_json(os.path.join(RAW, r["artifact_file"])).get("pet_windows") or [])) if r.get("artifact_file") else []
                explicit = [w for w in windows if re.search(r"\bpets? (are|is) (not )?(accepted|allowed|welcome|permitted)\b|\bpet[- ]friendly \(|\bpet fee\b|\bpet free and deposit\b", w, re.I)]
                if explicit:
                    cls, why = "FOUNDER_EXCEPTION", "reader found no bounded block, but the page states in its own words: %s" % " | ".join(repr(w[:160]) for w in explicit[:2])
                else:
                    cls, why = ("SOURCE_SILENT", "page(s) read; no pet or animal policy statement") if str(r.get("note", "")).startswith("SILENT") else ("POLICY_NOT_FOUND", "no bounded policy block on the page(s) read")
            elif rd.get("brand_generic"):
                cls, why = "FOUNDER_EXCEPTION", "block is brand-generic copy, not this property's policy"
            elif pa is True and r.get("reader_source") == "visible_text":
                cls, why = "CLEAN_PET_FRIENDLY", "%s first-party capture; identity bound on the page's own premises; property policy sentence quoted" % r["lane"].lower().replace("_", " ")
            elif pa is False and r.get("reader_source") == "visible_text":
                cls, why = "CLEAN_VERIFIED_NO_PETS", "%s first-party capture; identity bound; refusal sentence quoted" % r["lane"].lower().replace("_", " ")
            elif pa in (True, False):
                cls, why = "FOUNDER_EXCEPTION", "policy read only from collapsed (hidden) page text: %s" % ("pets allowed" if pa else "no pets")
            elif rd.get("service_animal_quote"):
                cls, why = "SOURCE_SILENT", "only service-animal language; no ordinary pet statement"
            else:
                cls, why = "SOURCE_SILENT", "block found but no pets statement"
            if cls.startswith("CLEAN") and rd.get("pets_allowed_quote") and len(rd["pets_allowed_quote"].split()) < 2:
                cls, why = "FOUNDER_EXCEPTION", "the pets statement is a bare phrase (%r), not a sentence with terms" % rd["pets_allowed_quote"]
        rec["classification"], rec["why"] = cls, why
        if r:
            quote = (r.get("reader") or {}).get("pets_allowed_quote") or (((r.get("observation") or {}).get("evidence") or [{}])[0].get("quote") if r.get("observation") else None)
            rec["evidence"] = OrderedDict([("document_sha256", r.get("document_sha256")), ("artifact", r.get("artifact_file") or r.get("artifact_dir")), ("source_artifact", r.get("source_artifact") or ""),
                                           ("final_url", r.get("final_url")), ("captured_at", r.get("captured_at")), ("interaction", r.get("interaction") or ""), ("identity_binding", r.get("identity_binding")),
                                           ("quote", quote), ("extraction", (r.get("reader") or {}).get("extraction") or ((r.get("observation") or {}).get("extraction"))),
                                           ("withheld", (r.get("reader") or {}).get("withheld") or ((r.get("observation") or {}).get("withheld_fields")))])
        out.append(rec)
    doc["classification"] = out
    doc["classification_counts"] = OrderedDict(sorted(Counter(x["classification"] for x in out).items()))
    doc["rows_attempted"] = len([k for k in have if k in cohort])
    doc["targets"] = len(out)
    write_json(RESULTS, doc)
    print("attempted", doc["rows_attempted"], "of", len(out), dict(doc["classification_counts"]))
    for x in out:
        print(" ", x["classification"].ljust(22), "|", x["identity_key"][:46].ljust(46), "|", (x["why"] or "")[:80])
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("cohort")
    s = sub.add_parser("run-static")
    s.add_argument("--refetch", action="store_true")
    s.add_argument("--only", nargs="*", default=None)
    a = sub.add_parser("ingest-attended")
    a.add_argument("--identity-key", required=True)
    a.add_argument("--payload", required=True)
    a.add_argument("--requested-url", default="")
    a.add_argument("--interaction", default="")
    a.add_argument("--note", default="")
    a.add_argument("--outcome", default="")
    o = sub.add_parser("ingest-owned")
    o.add_argument("--identity-key", required=True)
    o.add_argument("--artifact", required=True)
    o.add_argument("--note", default="")
    f = sub.add_parser("record-failure")
    f.add_argument("--identity-key", required=True)
    f.add_argument("--lane", default="ATTENDED")
    f.add_argument("--outcome", default="ATTENDED_ACCESS_BLOCKED")
    f.add_argument("--requested-url", default="")
    f.add_argument("--detail", default="")
    sub.add_parser("classify")
    args = ap.parse_args(argv)
    return {"cohort": cmd_cohort, "run-static": cmd_run_static, "ingest-attended": cmd_ingest_attended, "ingest-owned": cmd_ingest_owned, "record-failure": cmd_record_failure, "classify": cmd_classify}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
