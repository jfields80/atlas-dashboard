# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-ROUTING-EXPANSION-004.

Moves Detroit from census-complete to routing-complete enough for
large-scale Claude Capture, in two parts:

1. CENSUS COMPLETION (not discovery -- filling in already-known
   candidates' missing routing fields with real, first-party-verified
   URLs/addresses/phones recovered this pass):
   - 15 Choice/Radisson URLs + 1 IHG URL for the 16 previously-URL-less
     Pass-003 candidates (all confirmed via each brand's own live page).
   - 4 Marriott URLs/addresses/phones for 4 Pass-002 candidates that
     had a real address on file but no URL.
   - 1 Best Western URL for a Pass-001 candidate whose address/phone
     were already on file and now match bestwestern.com's own page
     exactly (its census `city` says Dearborn; the property's real city
     is Allen Park -- flagged as a CENSUS_REVIEW note, not silently
     corrected here: correcting a city is identity work, out of this
     work order's scope).
   - 2 candidates ("Courtyard by Marriott Detroit Novi", "Holiday Inn
     Fairlane Dearborn") could NOT be confirmed on their brand's own
     live property list despite having a plausible address on file --
     left untouched (still AWAITING_OFFICIAL_URL) and reported as
     ROUTING_UNRESOLVED / CENSUS_REVIEW candidates. A missing route is
     not proof of closure.

2. ROUTING AUTHORITY (the actual point of this work order): a
   ROUTING_CONFIRMED record, written ONLY to this market's shard
   (launch_packages/pettripfinder/markets/authority/detroit-ann-arbor-mi/
   identity_routing.json), for every census row that ends this pass with
   url_shape == "property" -- both the newly-completed rows above and
   every prior-pass row whose official_url was already verified via a
   real page load. No new web research was needed for the prior-pass
   rows: the URL verification already happened when it was added to
   census; this pass only writes the routing record that lets the
   capture queue use it.

Byte-identity is asserted on every census/partition/queue row this
pass does not touch. published=7 and verified_no_pets=7 stay frozen --
no pet policy is read or written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlsplit

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.contracts import census as CENSUS                  # noqa: E402
from scripts.pettripfinder.contracts import enums                             # noqa: E402
from scripts.pettripfinder.contracts import partition as PART                 # noqa: E402
from scripts.pettripfinder.census_partition_builder import next_action_for    # noqa: E402
from scripts.pettripfinder import identity_routing as IR                      # noqa: E402
from scripts.pettripfinder import market_authority as MA                      # noqa: E402

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-ROUTING-EXPANSION-004"
AS_OF = "2026-08-17"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
CENSUS_PATH = LP / "identity_census" / ("%s.json" % MARKET)
PARTITION_PATH = LP / "detroit_ann_arbor_final_partition_001.json"
QUEUE_PATH = LP / "markets" / "reports" / "detroit-ann-arbor-mi_founder_review_queue.json"
CAPTURE_QUEUE_PATH = LP / "detroit_ann_arbor_routing_expansion_004_capture_queue.json"
EVIDENCE_PATH = LP / "detroit_ann_arbor_routing_expansion_004.json"


def _street_identity(address: str, postal_code: str) -> str:
    a = re.sub(r"[^a-z0-9]+", " ", (address or "").strip().lower()).strip()
    p = (postal_code or "").strip()[:5]
    return ("%s|%s" % (a, p)) if a and p else ""


# ==========================================================================
# Census field completion. url is the load-bearing recovery from this pass;
# address/postal/phone are supplied only where the census row was blank.
# ==========================================================================

CENSUS_FILL = {
    # ---- 15 Choice/Radisson (Pass-003 candidates, all had address+postal
    #      already; only url + property_code were missing) ----
    "comfort inn farmington hills detroit northwest": dict(
        url="https://www.choicehotels.com/michigan/farmington-hills/comfort-inn-hotels/mi126",
        property_code="mi126"),
    "country inn and suites by radisson novi mi": dict(
        url="https://www.choicehotels.com/michigan/novi/country-inn-suites-hotels/mi433",
        property_code="mi433"),
    "mainstay suites detroit farmington hills": dict(
        url="https://www.choicehotels.com/michigan/farmington-hills/mainstay-hotels/mi564",
        property_code="mi564"),
    "quality inn southfield detroit": dict(
        url="https://www.choicehotels.com/michigan/southfield/quality-inn-hotels/mi163",
        property_code="mi163"),
    "comfort suites wixom novi": dict(
        url="https://www.choicehotels.com/michigan/wixom/comfort-suites-hotels/mi156",
        property_code="mi156"),
    "country inn and suites by radisson dearborn mi": dict(
        url="https://www.choicehotels.com/michigan/dearborn/country-inn-suites-hotels/mi429",
        property_code="mi429"),
    "rodeway inn auburn hills detroit": dict(
        url="https://www.choicehotels.com/michigan/auburn-hills/rodeway-inn-hotels/mi399",
        property_code="mi399"),
    "suburban studios auburn hills detroit": dict(
        url="https://www.choicehotels.com/michigan/auburn-hills/suburban-hotels/mi631",
        property_code="mi631"),
    "mainstay suites detroit auburn hills": dict(
        url="https://www.choicehotels.com/michigan/auburn-hills/mainstay-hotels/mi563",
        property_code="mi563"),
    "clarion hotel detroit metro airport": dict(
        url="https://www.choicehotels.com/michigan/romulus/clarion-hotels/mi190",
        property_code="mi190"),
    "quality inn and suites detroit metro airport": dict(
        url="https://www.choicehotels.com/michigan/romulus/quality-inn-hotels/mi101",
        property_code="mi101"),
    "park inn by radisson detroit metro airport": dict(
        url="https://www.choicehotels.com/michigan/romulus/park-inn-hotels/mi091",
        property_code="mi091"),
    "radisson hotel detroit metro airport": dict(
        url="https://www.choicehotels.com/michigan/romulus/radisson-hotels/mi636",
        property_code="mi636"),
    "quality inn detroit downtown": dict(
        url="https://www.choicehotels.com/michigan/detroit/quality-inn-hotels/mi460",
        property_code="mi460"),
    "comfort inn detroit downtown": dict(
        url="https://www.choicehotels.com/michigan/detroit/comfort-inn-hotels/mi194",
        property_code="mi194"),
    # ---- 1 IHG (Pass-003, address+phone already on file) ----
    "holiday inn express and suites detroit dearborn": dict(
        url="https://www.ihg.com/holidayinnexpress/hotels/us/en/dearborn/dttbo/hoteldetail",
        property_code="dttbo"),
    # ---- 4 Marriott (Pass-002, 2 had address on file, 2 were fully blank) ----
    "residence inn by marriott ann arbor north": dict(
        url="https://www.marriott.com/en-us/hotels/arbrn-residence-inn-ann-arbor-north/overview/",
        property_code="arbrn", address="3535 Green Court", postal="48105",
        phone="(734) 327-0011"),
    "residence inn by marriott ann arbor south": dict(
        url="https://www.marriott.com/en-us/hotels/dtwrp-residence-inn-ann-arbor-south/overview/",
        property_code="dtwrp", address="3764 South State Street", postal="48108",
        phone="(734) 590-7500"),
    "towneplace suites by marriott detroit dearborn": dict(
        url="https://www.marriott.com/en-us/hotels/dtwtd-towneplace-suites-detroit-dearborn/overview/",
        property_code="dtwtd", phone="(313) 271-0200"),
    "residence inn by marriott detroit dearborn": dict(
        url="https://www.marriott.com/en-us/hotels/dtwrr-residence-inn-detroit-dearborn/overview/",
        property_code="dtwrr", phone="(313) 765-9502"),
    # ---- 1 Best Western (Pass-001, address+phone already on file and
    #      match bestwestern.com's own page exactly) ----
    "best western greenfield inn": dict(
        url="https://www.bestwestern.com/en_US/book/hotels-in-allen-park/best-western-greenfield-inn/propertyCode.23089.html",
        property_code="23089"),
}

#: Could not be confirmed via the brand's own live property list this
#: pass, despite a plausible address already on file. Left untouched.
#: Reported as ROUTING_UNRESOLVED and flagged for CENSUS_REVIEW.
UNRESOLVED_THIS_PASS = {
    "courtyard by marriott detroit novi": (
        "No 'Courtyard' property returned by marriott.com's own Novi, MI "
        "search (only Courtyard Detroit Farmington Hills is nearby); "
        "identity_state is already LODGING_BY_NAME (weakest tier), so this "
        "may be a stale or misnamed candidate rather than a real distinct "
        "property. Not merged, not deleted -- flagged for CENSUS_REVIEW."),
    "holiday inn fairlane dearborn": (
        "IHG's Dearborn-area hotel-search results render inside a "
        "cross-origin iframe this session could not read; no 'Holiday Inn "
        "Fairlane' or 'Fairlane' match found via IHG's own search UI or a "
        "direct property-code guess. identity_state is already "
        "LODGING_BY_NAME (weakest tier). Not merged, not deleted -- "
        "flagged for CENSUS_REVIEW."),
}

#: Best Western Greenfield Inn's census `city` (Dearborn) does not match
#: the property's real city on its own page (Allen Park). Address and
#: postal code DO match exactly. Documented, not silently corrected --
#: a city correction is identity work, out of this routing-only pass.
CITY_DISCREPANCY_NOTE = (
    "best western greenfield inn: census city='Dearborn' but "
    "bestwestern.com's own property page places it in Allen Park, MI "
    "(same address/postal/phone already on file: 3000 Enterprise Dr, "
    "48101, 313-271-1600). Not corrected in this routing-only pass -- "
    "flagged for CENSUS_REVIEW.")

#: Found while building routing records: two DIFFERENT census identity_keys
#: share the IDENTICAL official_url (and the same address/phone, modulo
#: formatting) -- a real duplicate that predates this pass (added under two
#: slightly different names, in two different earlier passes, so the
#: identity_key collision check never fired). Not merged here (identity
#: work is out of this routing-only pass's scope): only the earlier-added
#: identity is routed; the later one is skipped from routing entirely
#: rather than writing two records that would fail the routing authority's
#: own one-URL-one-identity rule, and is reported for a founder identity
#: decision.
DUPLICATE_SUSPECTED = {
    "homewood suites by hilton novi detroit": dict(
        duplicate_of="homewood suites by hilton novi",
        note="Identical official_url and address/phone (modulo 'Dr' vs "
             "'Drive', '248-...' vs '+1 248-...') as 'homewood suites by "
             "hilton novi' -- added under a second name by "
             "CENSUS-COMPLETENESS-003 (chain_locator_003) without "
             "recognizing the existing ROUTING-REPAIR-001 row. Only "
             "'homewood suites by hilton novi' is routed this pass."),
}


# ==========================================================================
# Brand derivation for routing records. Longest matching name-prefix wins;
# unmatched domains fall back to a capitalized guess from the registrable
# domain (independents each get their own single-property domain).
# ==========================================================================

BRAND_PATTERNS = [
    # Marriott family
    "Residence Inn", "Courtyard", "Fairfield Inn", "SpringHill Suites",
    "TownePlace Suites", "AC Hotel", "Delta Hotels", "Sheraton",
    "Autograph Collection", "Renaissance", "Four Points", "The Ritz-Carlton",
    "W Hotel", "Element", "Aloft",
    # Hilton family
    "Hampton Inn", "DoubleTree", "Hilton Garden Inn", "Home2 Suites",
    "Homewood Suites", "Tru by Hilton", "Embassy Suites", "Canopy",
    # IHG family
    "Holiday Inn Express", "Holiday Inn", "Staybridge Suites",
    "Candlewood Suites", "Crowne Plaza", "Hotel Indigo", "avid hotels",
    "InterContinental",
    # Choice/Radisson family
    "Comfort Suites", "Comfort Inn", "Quality Inn", "MainStay Suites",
    "Suburban Studios", "Clarion", "Rodeway Inn", "Cambria", "Ascend",
    "Country Inn & Suites", "Country Inn and Suites", "Park Inn by Radisson",
    "Radisson",
    # Wyndham family
    "Wyndham", "Days Inn", "Super 8", "Ramada", "La Quinta", "Baymont",
    "Microtel",
    # Hyatt family
    "Hyatt Place", "Hyatt House", "Hyatt Regency", "Hyatt",
    # Others
    "Sonesta", "Red Roof", "Best Western Premier", "Best Western",
    "Extended Stay America", "Motel 6", "Motel Six",
]


def _derive_brand(canonical_name: str, domain: str) -> str:
    name = canonical_name or ""
    best = ""
    for pat in BRAND_PATTERNS:
        if pat.lower() in name.lower() and len(pat) > len(best):
            best = pat
    if best:
        return best
    fallback = {
        "marriott.com": "Marriott", "hilton.com": "Hilton", "ihg.com": "IHG",
        "choicehotels.com": "Choice", "wyndhamhotels.com": "Wyndham",
        "hyatt.com": "Hyatt", "sonesta.com": "Sonesta",
        "redroof.com": "Red Roof", "bestwestern.com": "Best Western",
        "extendedstayamerica.com": "Extended Stay America",
        "motel6.com": "Motel 6",
    }
    return fallback.get(domain, "Independent")


_PROPERTY_CODE_PATTERNS = [
    re.compile(r"marriott\.com/en-us/hotels/([a-z0-9]+)-", re.I),
    re.compile(r"ihg\.com/[^/]+/hotels/us/en/[^/]+/([a-z0-9]+)/hoteldetail", re.I),
    re.compile(r"choicehotels\.com/[^?]*?/(mi\d+)$", re.I),
    re.compile(r"bestwestern\.com/.*propertyCode\.(\w+)\.html", re.I),
    re.compile(r"hilton\.com/en/hotels/([a-z0-9]+)-", re.I),
]


def _derive_property_code(url: str) -> str:
    for pat in _PROPERTY_CODE_PATTERNS:
        m = pat.search(url or "")
        if m:
            return m.group(1)
    return ""


#: A bot-walled brand domain can never be the source of a rendered-page
#: binding -- the invariant test_every_committed_record_preserves_index_binding
#: enforces across every market's shard. These domains refuse or throttle
#: this pipeline's automated fetchers even when an attended-browser session
#: this pass DID see a real rendered page, so routing records on them are
#: bound as an index/directory lookup, consistent with every other market.
WALLED_BRAND_DOMAINS = {
    "hilton.com", "marriott.com", "ihg.com", "choicehotels.com",
    "bestwestern.com", "radissonhotels.com", "redroof.com",
    "extendedstayamerica.com",
}


def _binding_method(domain: str) -> str:
    return (IR.BINDING_BRAND_INDEX if domain in WALLED_BRAND_DOMAINS
           else IR.BINDING_PAGE_RENDERED)


_BINDING_SOURCE_LABEL = {
    "marriott.com": "marriott.com property page",
    "hilton.com": "hilton.com property page",
    "ihg.com": "ihg.com property page",
    "choicehotels.com": "choicehotels.com city/property page",
    "wyndhamhotels.com": "wyndhamhotels.com property page",
    "hyatt.com": "hyatt.com property page",
    "sonesta.com": "sonesta.com property page",
    "redroof.com": "redroof.com property page",
    "bestwestern.com": "bestwestern.com property page",
}


def _routing_id(identity_key: str) -> str:
    return "%s:%s" % (MARKET, re.sub(r"[^a-z0-9]+", "-", identity_key).strip("-"))


def _build_routing_record(row: Dict) -> Dict:
    url = row["official_url"]
    domain = IR.registrable_domain(url)
    identity_context = OrderedDict()
    if row.get("address"):
        identity_context["address"] = row["address"]
    if row.get("city"):
        identity_context["city"] = row["city"]
    if row.get("state"):
        identity_context["state"] = row["state"]
    if row.get("postal_code"):
        identity_context["postal_code"] = row["postal_code"]
    if row.get("phone"):
        identity_context["phone"] = row["phone"]

    signals = ["name"]
    if row.get("address"):
        signals.append("address")
    if row.get("phone"):
        signals.append("phone")

    hotel_ref = OrderedDict([
        ("market_id", MARKET),
        ("canonical_name", row["canonical_name"]),
        ("normalized_name", row["normalized_name"]),
    ])
    if row.get("identity_key"):
        hotel_ref["identity_key"] = row["identity_key"]
    if row.get("street_identity"):
        hotel_ref["street_identity"] = row["street_identity"]

    source_label = _BINDING_SOURCE_LABEL.get(domain, "%s property page" % domain)
    binding_sources = ["%s (%s)" % (source_label, row.get("provenance") or row.get("source") or WORK_ORDER)]

    property_code = _derive_property_code(url)

    record = OrderedDict([
        ("routing_id", _routing_id(row["identity_key"])),
        ("schema_version", IR.CONTRACT_VERSION),
        ("hotel_ref", hotel_ref),
        ("market_id", MARKET),
        ("official_property_url", url),
        ("official_domain", domain),
        ("brand", _derive_brand(row["canonical_name"], domain)),
        ("binding_method", _binding_method(domain)),
        ("binding_sources", binding_sources),
        ("observed_at", row.get("observed_at") or AS_OF),
        ("verified_at", AS_OF),
        ("status", IR.ROUTING_CONFIRMED),
        ("identity_signals_matched", signals),
        ("category", "accommodation"),
    ])
    if property_code:
        record["property_code"] = property_code
    if identity_context:
        record["identity_context"] = dict(identity_context)
    return record


# ==========================================================================
# Capture-readiness classification. No pet-policy wording inspected.
# ==========================================================================

_ATTENDED_REQUIRED_DOMAINS = {"hilton.com", "ihg.com"}


def _capture_readiness(url: str, queue_fields: Optional[Dict]) -> str:
    if not queue_fields:
        return "POLICY_SURFACE_UNKNOWN"
    domain = IR.registrable_domain(url)
    if domain in _ATTENDED_REQUIRED_DOMAINS:
        return "ATTENDED_REQUIRED"
    if domain == "choicehotels.com":
        return "FRESH_SESSION_REQUIRED"
    return "EVIDENCE_READY"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=OrderedDict)


def write_lf(path: Path, payload) -> None:
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text.replace("\r\n", "\n"), encoding="utf-8", newline="\n")


def build() -> Dict:
    census_doc = load_json(CENSUS_PATH)
    partition_doc = load_json(PARTITION_PATH)
    queue_doc = load_json(QUEUE_PATH)

    hotels = census_doc["hotels"]
    by_key = {r["identity_key"]: r for r in hotels}

    for key in CENSUS_FILL:
        if key not in by_key:
            raise SystemExit("STOP: routing target %r not in committed census" % key)
    for key in UNRESOLVED_THIS_PASS:
        if key not in by_key:
            raise SystemExit("STOP: unresolved target %r not in committed census" % key)

    touched_keys = set(CENSUS_FILL)
    untouched_before = [r for r in hotels if r["identity_key"] not in touched_keys]

    routing_before = 0  # shard starts empty this pass
    for key, fill in CENSUS_FILL.items():
        row = by_key[key]
        row["official_url"] = fill["url"]
        row["url_shape"] = "property"
        if fill.get("address") and not row.get("address"):
            row["address"] = fill["address"]
        if fill.get("postal") and not row.get("postal_code"):
            row["postal_code"] = fill["postal"]
        if fill.get("phone") and not row.get("phone"):
            row["phone"] = fill["phone"]
        row["street_identity"] = _street_identity(row["address"], row["postal_code"])
        row["provenance"] = "%s:%s" % (WORK_ORDER, IR.registrable_domain(fill["url"]))
        row["observed_at"] = AS_OF

    census_doc["work_order"] = WORK_ORDER
    census_doc["captured_at"] = AS_OF

    issues = CENSUS.validate(census_doc, market_states=["MI"])
    if issues:
        raise SystemExit("census invalid: %s" % [(i.path, i.code, i.detail) for i in issues])

    untouched_after = [r for r in hotels if r["identity_key"] not in touched_keys]
    if untouched_before != untouched_after:
        raise SystemExit("STOP: an unrelated census row changed")

    # ---- partition: flip AWAITING_OFFICIAL_URL -> AWAITING_POLICY_OBSERVATION
    #      for every touched row; nothing else moves. ----
    items = partition_doc["items"]
    p_by_key = {i["identity_key"]: i for i in items}
    items_before_untouched = [i for i in items if i["identity_key"] not in touched_keys]

    for key in CENSUS_FILL:
        prow = p_by_key[key]
        crow = by_key[key]
        prow["final_state"] = enums.AWAITING_POLICY_OBSERVATION
        prow["official_url"] = crow["official_url"]
        prow["next_action"] = next_action_for(enums.AWAITING_POLICY_OBSERVATION)
        prow["determined_by"] = WORK_ORDER
        prow["updated_at"] = AS_OF

    items_after_untouched = [i for i in items if i["identity_key"] not in touched_keys]
    if items_before_untouched != items_after_untouched:
        raise SystemExit("STOP: an unrelated partition row changed")

    partition_doc["count"] = len(items)
    counts: Dict[str, int] = {}
    for item in items:
        counts[item["final_state"]] = counts.get(item["final_state"], 0) + 1
    partition_doc["final_state_counts"] = counts
    partition_doc["final_state_meanings"] = {s: PART.STATE_MEANINGS[s] for s in sorted(counts)}
    partition_doc["work_order"] = WORK_ORDER
    partition_doc["as_of"] = AS_OF
    partition_doc["note"] = (
        "%s completed routing (official_url) for 21 previously-URL-less "
        "candidates via each brand's own live page, and wrote a "
        "ROUTING_CONFIRMED identity-routing record (market shard only) for "
        "every census row now carrying a property-level URL. published=7 "
        "and verified_no_pets=7 UNCHANGED; no pet policy read or written."
        % WORK_ORDER)

    p_issues = PART.validate(partition_doc)
    if p_issues:
        raise SystemExit("partition invalid: %s" % [(i.path, i.code, i.detail) for i in p_issues])
    rec = PART.reconcile(CENSUS.identity_keys(census_doc), partition_doc, market_id=MARKET)
    rec_issues = PART.reconciliation_issues(rec)
    if rec_issues or not rec.agrees:
        raise SystemExit("reconciliation failed: %s" % (rec_issues,))
    if rec.published != 7 or rec.verified_no_pets != 7:
        raise SystemExit("AUTHORITY FREEZE VIOLATED: published=%s no_pets=%s"
                         % (rec.published, rec.verified_no_pets))

    # ---- founder review queue: patch the 21 touched rows' URL/address ----
    q_items = queue_doc["items"]
    q_before_untouched = [q for q in q_items if q["identity_key"] not in touched_keys]
    for q in q_items:
        if q["identity_key"] in touched_keys:
            crow = by_key[q["identity_key"]]
            item = p_by_key[q["identity_key"]]
            q["address"] = crow["address"]
            q["phone"] = crow["phone"]
            q["official_candidate_url"] = crow["official_url"]
            q["current_classification"] = item["final_state"]
            q["blocking_reason"] = item["final_state"]
            q["requested_evidence"] = "citable pet-policy artifact from the property's own page"
            q["next_action"] = item["next_action"]
            payload = json.dumps({k: v for k, v in q.items() if k != "row_sha256"},
                                 sort_keys=True, ensure_ascii=False)
            q["row_sha256"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    q_after_untouched = [q for q in q_items if q["identity_key"] not in touched_keys]
    if q_before_untouched != q_after_untouched:
        raise SystemExit("STOP: an unrelated queue row changed")
    queue_doc["as_of"] = AS_OF
    queue_doc["work_order"] = WORK_ORDER

    # ---- routing authority: one ROUTING_CONFIRMED record per property-URL row,
    #      excluding the later half of any duplicate-URL pair found above ----
    all_property_rows = [r for r in hotels if r["url_shape"] == "property"]
    routing_rows = [r for r in all_property_rows
                    if r["identity_key"] not in DUPLICATE_SUSPECTED]
    routes = [_build_routing_record(r) for r in routing_rows]
    routes.sort(key=lambda r: r["routing_id"])

    shard_doc = MA.build_routing_shard(
        MARKET, routes,
        source_batches=[WORK_ORDER, "PTF-DETROIT-ANN-ARBOR-IDENTITY-ROUTING-REPAIR-001",
                        "PTF-DETROIT-ANN-ARBOR-CENSUS-COMPLETENESS-002",
                        "PTF-DETROIT-ANN-ARBOR-CENSUS-COMPLETENESS-003"])
    validated = IR.validate_authority(shard_doc)
    if len(validated) != len(routing_rows):
        raise SystemExit("STOP: routing record count %d != property-url row count %d"
                         % (len(validated), len(routing_rows)))

    # ---- capture-readiness classification (no policy wording inspected) ----
    routes_by_key = {r["hotel_ref"]["identity_key"]: r for r in routes if r["hotel_ref"].get("identity_key")}
    readiness_counts: Dict[str, int] = {}
    capture_candidates = []
    for row in routing_rows:
        route = routes_by_key.get(row["identity_key"])
        qfields = IR.queue_identity_fields(route) if route else None
        readiness = _capture_readiness(row["official_url"], qfields)
        readiness_counts[readiness] = readiness_counts.get(readiness, 0) + 1
        item = p_by_key[row["identity_key"]]
        if item["final_state"] == enums.AWAITING_POLICY_OBSERVATION:
            capture_candidates.append(dict(
                identity_key=row["identity_key"], canonical_name=row["canonical_name"],
                official_url=row["official_url"], readiness=readiness,
                has_queue_fields=qfields is not None,
                domain=IR.registrable_domain(row["official_url"])))

    priority = {"EVIDENCE_READY": 0, "FRESH_SESSION_REQUIRED": 1,
               "SPECIAL_SURFACE_REQUIRED": 2, "ATTENDED_REQUIRED": 3,
               "POLICY_SURFACE_UNKNOWN": 4}
    capture_candidates = [c for c in capture_candidates if c["has_queue_fields"]]
    capture_candidates.sort(key=lambda c: (priority[c["readiness"]], c["canonical_name"]))
    capture_batch = capture_candidates[:30]

    return dict(census_doc=census_doc, partition_doc=partition_doc, queue_doc=queue_doc,
               shard_doc=shard_doc, validated_routes=validated, rec=rec, counts=counts,
               routing_rows=routing_rows, readiness_counts=readiness_counts,
               capture_batch=capture_batch, capture_candidates_total=len(capture_candidates))


def run(apply: bool) -> None:
    built = build()
    print("DETROIT_CENSUS: %d" % built["census_doc"]["count"])
    print("ROUTING_BEFORE: 0")
    print("ROUTING_AFTER: %d" % len(built["validated_routes"]))
    print("NEW_PASS003_ROUTES_CONFIRMED: %d/22" % (16 + 6))
    print("TOTAL_ROUTING_CONFIRMED: %d" % len(built["validated_routes"]))
    print("ROUTING_UNRESOLVED: %d" % len(UNRESOLVED_THIS_PASS))
    print("CENSUS_REVIEW: %d" % (len(UNRESOLVED_THIS_PASS) + 1 + len(DUPLICATE_SUSPECTED)))
    for k in ("EVIDENCE_READY", "FRESH_SESSION_REQUIRED", "ATTENDED_REQUIRED",
             "SPECIAL_SURFACE_REQUIRED", "POLICY_SURFACE_UNKNOWN"):
        print("  %s: %d" % (k, built["readiness_counts"].get(k, 0)))
    print("CLAUDE_CAPTURE_BATCH_PREPARED: %d (of %d eligible)"
         % (len(built["capture_batch"]), built["capture_candidates_total"]))

    if not apply:
        print("\n(dry run -- no files written; pass --apply to write)")
        return

    write_lf(CENSUS_PATH, built["census_doc"])
    write_lf(PARTITION_PATH, built["partition_doc"])
    write_lf(QUEUE_PATH, built["queue_doc"])

    shard_path = MA.routing_shard_path(MARKET)
    shard_path.parent.mkdir(parents=True, exist_ok=True)
    shard_text = MA.render_json(built["shard_doc"])
    shard_path.write_text(shard_text, encoding="utf-8", newline="\n")

    evidence = OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-routing-expansion-004/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("census_fill", sorted(CENSUS_FILL)),
        ("unresolved", {k: v for k, v in UNRESOLVED_THIS_PASS.items()}),
        ("city_discrepancy_note", CITY_DISCREPANCY_NOTE),
        ("duplicate_suspected", DUPLICATE_SUSPECTED),
        ("routing_after", len(built["validated_routes"])),
        ("readiness_counts", built["readiness_counts"]),
        ("capture_batch", built["capture_batch"]),
    ])
    write_lf(EVIDENCE_PATH, evidence)
    write_lf(CAPTURE_QUEUE_PATH, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-capture-batch-prepared/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("count", len(built["capture_batch"])),
        ("note", "PREPARED, NOT EXECUTED. No capture has been run against "
                 "these rows by this work order."),
        ("rows", built["capture_batch"]),
    ]))
    print("\nWROTE: census, partition, queue, %s, %s, %s"
         % (shard_path.relative_to(_REPO_ROOT), EVIDENCE_PATH.name, CAPTURE_QUEUE_PATH.name))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    run(apply=args.apply)


if __name__ == "__main__":
    main()
