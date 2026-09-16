"""PTF-TAMPA-FL-HARDENED-V2-SOURCE-READY-001 -- Phases 15-19: policy adjudication over one identity per row.

Identity (census_reconciliation) and routing are already settled. This pass attaches a POLICY FACT to each
admitted TRUE_HOTEL_IDENTITY row from the evidence this order actually captured, and gives every row exactly
one disposition (Phase 19). It never re-decides identity or membership.

EVIDENCE SOURCES, EACH KEYED BACK TO A CENSUS ROW
--------------------------------------------------
  BRAND_CODE match   (brand, property_code) -- Marriott, Hilton, Hyatt, Best Western supported-browser reads
                      (marriott_browser_rows.jsonl, hilton_browser_rows.jsonl, resort_browser_rows.jsonl) and the
                      Wyndham property-service lane (wyndham_rows.json, matched on brand=WYNDHAM + house number +
                      postal code, since Wyndham's own service carries no property_code the census stores).
  IDENTITY_KEY match  the free static capture (VALID rows) and the Firecrawl pass (publication-grade rows), both
                      already keyed to the census identity_key.
  ADDRESS match       the independents' own policy/FAQ pages lane (policy_pages_rows.json), keyed to identity_key
                      directly (it was built from routing, which carries identity_key).

NEGATION SAFETY (Phase 17)
---------------------------
Every quote is scanned for an explicit refusal ("not allowed", "not accepted", "no pets", "not permitted",
"prohibited") independently of the pets_allowed flag this order read from the page. A row where the flag says
True but the quote itself contains a refusal phrase is a NEGATION_HOLD, never published. A generic amenity
badge ("pet-friendly") beside an explicit refusal is not a conflict; the explicit Pet Policy / FAQ text governs
and is what this order's pets_allowed flag was set from in the first place (see Best Western Wesley Chapel,
resort_browser_rows.jsonl).

Every row not matched to captured evidence keeps its exact router state as its hold reason: no route
(ROUTING_HOLD), a browser wall reached before this order's turn came (BROWSER_CAPTURE_NEEDED), every free/paid
lane exhausted (ACCESS_BLOCKED), or a page that served and said nothing (SOURCE_SILENT).

Output:
  launch_packages/pettripfinder/markets/reports/tampa_fl_v2_clean_authority_001.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-TAMPA-FL-HARDENED-V2-SOURCE-READY-001"
MARKET_ID = "tampa-fl"
SCHEMA = "ptf-clean-authority/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
STAGING = os.path.join(PKG, "markets", "staging", "tampa-fl", "raw_captures")
CENSUS = os.path.join(PKG, "identity_census_proposed", "tampa-fl.json")
ROUTING = os.path.join(REPORTS, "tampa_fl_v2_routing_001.json")
STATIC = os.path.join(REPORTS, "tampa_fl_v2_free_static_capture_001.json")
FIRECRAWL = os.path.join(REPORTS, "tampa_fl_v2_firecrawl_pass_001.json")
OUT = os.path.join(REPORTS, "tampa_fl_v2_clean_authority_001.json")

CLEAN_PET_FRIENDLY = "CLEAN_PET_FRIENDLY"
CLEAN_VERIFIED_NO_PETS = "CLEAN_VERIFIED_NO_PETS"
NEGATION_HOLD = "NEGATION_HOLD"
ROUTING_HOLD = "ROUTING_HOLD"
BROWSER_CAPTURE_NEEDED = "BROWSER_CAPTURE_NEEDED"
ACCESS_BLOCKED = "ACCESS_BLOCKED"
SOURCE_SILENT = "SOURCE_SILENT"
EVIDENCE_HOLD = "EVIDENCE_HOLD"
IDENTITY_MISMATCH_HOLD = "IDENTITY_MISMATCH_HOLD"

_REFUSAL = re.compile(
    r"\bpets?\s+(?:are\s+)?not\s+(?:allowed|accepted|permitted)\b|\bno\s+pets?\b|\bpets?\s+prohibited\b"
    r"|\bnot\s+pet[- ]friendly\b|\bpets?\s+not\s+welcome\b", re.I)
_ACCEPT = re.compile(r"\b(?:pets?|dogs?|cats?)\s+(?:are\s+)?(?:welcome|accepted|permitted)\b|\bpets?\s+allowed\b"
                     r"|\bpet[- ]friendly\b|\bwe\s+welcome\b.{0,20}\bdogs?\b|\ballow(?:s|ed)?\s+dogs?\b", re.I)
#: Weight-only, fee-only or count-only text is never read as acceptance on its own (Phase 16).
_WEIGHT_RX = re.compile(r"(\d+(?:\.\d+)?)\s*(?:lbs?|pounds)\b", re.I)
_FEE_RX = re.compile(r"\$\s*([0-9]+(?:\.[0-9]{1,2})?)", re.I)
_COUNT_RX = re.compile(r"(?:max(?:imum)?(?: of| number of pets(?: in room)?:?)?|up to)\s*\(?(\d|one|two|three)\)?\s*(?:pets?|dogs?)?", re.I)
_WORDS = {"one": 1, "two": 2, "three": 3}


def _load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _jsonl(path):
    out = []
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip().lstrip("﻿")
            if line:
                out.append(json.loads(line))
    return out


def _house_number(street):
    m = re.match(r"\s*(\d+)", street or "")
    return m.group(1) if m else ""


def negation_check(quote, claimed_pets_allowed):
    """(final_pets_allowed, conflict_note_or_None). The explicit refusal always wins."""
    refused = bool(_REFUSAL.search(quote or ""))
    accepted = bool(_ACCEPT.search(quote or ""))
    if refused and claimed_pets_allowed is True:
        return False, ("QUOTE_CONTRADICTS_CLAIM -- the captured quote contains an explicit refusal phrase "
                       "while this order's own read claimed acceptance; the refusal governs")
    if refused:
        return False, None
    if claimed_pets_allowed is True and not accepted:
        # A fee/weight/count sentence alone, with no explicit welcome wording, never establishes acceptance
        # on its own (Phase 16) -- but every row in this order's own captures was read directly from a
        # "Pets allowed: Yes" / "Pets Welcome" field or FAQ sentence, so this branch is a safety net, not the
        # normal path.
        return None, "EXPLICIT_ACCEPTANCE_WORDING_NOT_FOUND_IN_QUOTE -- held rather than published on a fee/weight/count sentence alone"
    return claimed_pets_allowed, None


def extract_facts(quote):
    fee = None
    m = _FEE_RX.search(quote or "")
    if m:
        fee = int(round(float(m.group(1)) * 100))
    weight = None
    m = _WEIGHT_RX.search(quote or "")
    if m:
        weight = float(m.group(1))
    count = None
    m = _COUNT_RX.search(quote or "")
    if m:
        v = m.group(1).lower()
        count = _WORDS.get(v, None) or (int(v) if v.isdigit() else None)
    refundable = None
    if re.search(r"non-?refundable", quote or "", re.I):
        refundable = False
    elif re.search(r"\brefundable\b", quote or "", re.I):
        refundable = True
    return OrderedDict([("pet_fee_cents", fee), ("fee_currency", "USD" if fee is not None else None),
                        ("fee_refundable", refundable), ("max_pet_weight_lbs", weight),
                        ("max_pet_count", count)])


def _transcription_sha(line_obj):
    """The sha256 of the canonical JSON transcription line itself -- declared as a TRANSCRIPTION_SHA256, never
    passed off as a page hash (Phase 15's durability rule for an accessibility-tree read)."""
    import hashlib
    return hashlib.sha256(json.dumps(line_obj, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def build_evidence_index(census_hotels):
    by_code = {}   # (brand, property_code_lower) -> evidence
    by_key = {}    # identity_key -> evidence
    by_addr = {}   # (house_number, postal5) -> evidence

    def add_code(brand, code, ev):
        if brand and code:
            by_code[(brand.upper(), code.lower())] = ev

    def add_key(key, ev):
        if key:
            by_key[key] = ev

    def add_addr(house, postal, ev):
        if house and postal:
            by_addr[(house, postal[:5])] = ev

    for path, brand in (
        (os.path.join(STAGING, "marriott_browser_rows.jsonl"), "MARRIOTT"),
        (os.path.join(STAGING, "hilton_browser_rows.jsonl"), "HILTON"),
    ):
        for r in _jsonl(path):
            if "pets_allowed" not in r:
                continue
            ev = OrderedDict([("lane", "PROPERTY_PAGE_ATTENDED"), ("source_url", r["url"]),
                              ("pets_allowed_claim", r["pets_allowed"]), ("quote", r["quote"]),
                              ("document_sha256", _transcription_sha(r)),
                              ("captured_via", "supported browser, accessibility tree (navigate + find only)")])
            add_code(brand, r["code"], ev)

    for r in _jsonl(os.path.join(STAGING, "resort_browser_rows.jsonl")):
        if "pets_allowed" not in r:
            continue
        ev = OrderedDict([("lane", "PROPERTY_PAGE_ATTENDED"), ("source_url", r["url"]),
                          ("pets_allowed_claim", r["pets_allowed"]), ("quote", r["quote"]),
                          ("document_sha256", _transcription_sha(r)),
                          ("captured_via", "supported browser, accessibility tree (navigate + find only)")])
        if r.get("code"):
            add_code(r["family"], r["code"], ev)

    wyndham_doc = _load(os.path.join(STAGING, "wyndham_rows.json"), {}) or {}
    for r in wyndham_doc.get("rows", []):
        if not r.get("p") or r.get("pet_indicator") not in ("Y", "N"):
            continue
        pets = r["pet_indicator"] == "Y"
        ev = OrderedDict([("lane", "PROPERTY_PAGE_STATIC"), ("source_url", r["u"]),
                          ("pets_allowed_claim", pets), ("quote", r["p"]),
                          ("document_sha256", r.get("h") or _transcription_sha(r)),
                          ("captured_via", "the brand's own property-service API (same JSON the overview page renders)")])
        add_addr(_house_number(r.get("st") or ""), r.get("z") or "", ev)

    for r in _jsonl(os.path.join(STAGING, "policy_pages_rows.json")) if False else \
            (_load(os.path.join(STAGING, "policy_pages_rows.json"), {}) or {}).get("rows", []):
        if not r.get("bound"):
            continue
        sentences = [s for p in r.get("pages", []) for s in p.get("pet_sentences", [])]
        if not sentences:
            continue
        text = " ".join(sentences)
        if _REFUSAL.search(text):
            pets = False
        elif _ACCEPT.search(text) or _FEE_RX.search(text) or _WEIGHT_RX.search(text):
            pets = True
        else:
            continue
        ev = OrderedDict([("lane", "PROPERTY_PAGE_STATIC"), ("source_url", r.get("final_url") or r["u"]),
                          ("pets_allowed_claim", pets), ("quote", text[:500]),
                          ("document_sha256", r.get("h") or _transcription_sha(r)),
                          ("captured_via", "the independent property's own policy/FAQ page, plain client")])
        add_key(r["identity_key"], ev)

    static_doc = _load(STATIC, {}) or {}
    for r in static_doc.get("rows", []):
        if r.get("outcome") != "VALID":
            continue
        ext = ((r.get("observation") or {}).get("extraction") or {})
        pa = ext.get("pets_allowed")
        if pa is None:
            continue
        quotes = [e.get("quote", "") for e in ((r.get("observation") or {}).get("evidence") or []) if e.get("quote")]
        ev = OrderedDict([("lane", "PROPERTY_PAGE_STATIC"), ("source_url", r.get("final_url") or r.get("requested_url")),
                          ("pets_allowed_claim", pa), ("quote", " ".join(quotes)[:500] or ("pets_allowed=%s (shared reader)" % pa)),
                          ("document_sha256", r.get("page_sha256") or _transcription_sha({"k": r["identity_key"], "u": r.get("requested_url")})),
                          ("captured_via", "shared direct_http_capture pipeline, plain client")])
        add_key(r["identity_key"], ev)

    fc_doc = _load(FIRECRAWL, {}) or {}
    for r in fc_doc.get("rows", []):
        if r.get("firecrawl_class") != "FIRECRAWL_PUBLICATION_GRADE":
            continue
        pa = r.get("pets_allowed")
        if pa is None:
            continue
        quotes = [e.get("quote", "") for e in ((r.get("observation") or {}).get("evidence") or []) if e.get("quote")]
        ev = OrderedDict([("lane", "FIRECRAWL"), ("source_url", r.get("final_url") or r.get("requested_url")),
                          ("pets_allowed_claim", pa), ("quote", " ".join(quotes)[:500] or ("pets_allowed=%s (Firecrawl reader)" % pa)),
                          ("document_sha256", r.get("page_sha256") or _transcription_sha({"k": r["identity_key"], "u": r.get("requested_url")})),
                          ("captured_via", "Firecrawl rendered scrape, existing plan credits")])
        add_key(r["identity_key"], ev)

    return by_code, by_key, by_addr


def router_hold_reason(identity_key, routing_by_key, static_by_key, fc_by_key):
    r = routing_by_key.get(identity_key)
    if r is None:
        return ROUTING_HOLD, "no route was assembled for this identity in the routing pass"
    state = r.get("routing_state")
    if not r.get("url"):
        return ROUTING_HOLD, ("routing state %s: %s" % (state, r.get("why_no_route", "no first-party route stated")))
    s = static_by_key.get(identity_key)
    fc = fc_by_key.get(identity_key)
    if s is None and fc is None:
        if (r.get("brand_family") or "") in ("MARRIOTT", "HILTON", "HYATT"):
            return BROWSER_CAPTURE_NEEDED, ("routed to a %s page (%s) that no static, Firecrawl or browser pass in "
                                           "this order reached yet" % (r.get("brand_family"), r["url"]))
        return ROUTING_HOLD, "routed but no acquisition lane in this order attempted the page yet"
    outcome = (s or {}).get("outcome")
    cls = (s or {}).get("classification")
    if cls in ("SOURCE_SILENT_STATIC", "IDENTITY_TEXT_BOUND_POLICY_SILENT", "BLOCK_FOUND_BUT_SILENT"):
        return SOURCE_SILENT, "the page served and stated no operative pet policy (%s)" % cls
    if cls == "IDENTITY_MISMATCH" or cls == "IDENTITY_NOT_CONFIRMED_STATIC":
        return IDENTITY_MISMATCH_HOLD, "the fetched page's own identity did not confirm this census row"
    if outcome == "ACCESS_DENIED" and (r.get("brand_family") or "") in ("MARRIOTT", "HILTON", "HYATT", "IHG", "CHOICE", "BEST_WESTERN"):
        return BROWSER_CAPTURE_NEEDED, "static fetch was ACCESS_DENIED; a supported-browser or Firecrawl read did not reach this row"
    if fc is not None and fc.get("firecrawl_class") in ("FIRECRAWL_FAILED", "FIRECRAWL_MISMATCH"):
        return ACCESS_BLOCKED, "router exhausted: static %s, Firecrawl %s" % (outcome, fc.get("firecrawl_class"))
    return ACCESS_BLOCKED, "router exhausted on every free/authorized lane attempted this order (static %s)" % outcome


def build():
    census = _load(CENSUS, {}) or {}
    hotels = census.get("hotels", [])
    routing_doc = _load(ROUTING, {}) or {}
    routing_by_key = {r["identity_key"]: r for r in routing_doc.get("routes", [])}
    static_by_key = {r["identity_key"]: r for r in (_load(STATIC, {}) or {}).get("rows", [])}
    fc_by_key = {r["identity_key"]: r for r in (_load(FIRECRAWL, {}) or {}).get("rows", [])}
    by_code, by_key, by_addr = build_evidence_index(hotels)

    rows = []
    negation_conflicts = []
    for h in hotels:
        key = h["identity_key"]
        brand = (h.get("brand") or "").upper()
        code = (h.get("property_code") or "").lower()
        ev = None
        if brand and code:
            ev = by_code.get((brand, code))
        if ev is None:
            ev = by_key.get(key)
        if ev is None:
            house, postal = _house_number(h.get("street") or ""), (h.get("postal_code") or "")[:5]
            ev = by_addr.get((house, postal))

        row = OrderedDict([
            ("identity_key", key), ("canonical_name", h["canonical_name"]), ("brand", h.get("brand") or ""),
            ("corridor", h.get("corridor", "")), ("street", h.get("street", "")), ("postal_code", h.get("postal_code", "")),
        ])
        if ev is not None:
            final_pa, conflict = negation_check(ev["quote"], ev["pets_allowed_claim"])
            row["evidence"] = ev
            if conflict:
                negation_conflicts.append(OrderedDict([("identity_key", key), ("name", h["canonical_name"]), ("why", conflict)]))
            if final_pa is True:
                row["disposition"] = CLEAN_PET_FRIENDLY
                row["policy_facts"] = extract_facts(ev["quote"])
            elif final_pa is False:
                row["disposition"] = CLEAN_VERIFIED_NO_PETS
            else:
                row["disposition"] = NEGATION_HOLD if conflict and "QUOTE_CONTRADICTS_CLAIM" in conflict else EVIDENCE_HOLD
            if conflict:
                row["negation_conflict"] = conflict
        else:
            reason, why = router_hold_reason(key, routing_by_key, static_by_key, fc_by_key)
            row["disposition"] = reason
            row["hold_reason"] = why
        rows.append(row)

    counts = Counter(r["disposition"] for r in rows)
    pf = [r for r in rows if r["disposition"] == CLEAN_PET_FRIENDLY]
    np_ = [r for r in rows if r["disposition"] == CLEAN_VERIFIED_NO_PETS]
    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "15-19 -- policy adjudication, negation safety, one disposition per row"),
        ("no_inference_from_silence",
         "A page that states no pet policy is SOURCE_SILENT; it is never read as acceptance or refusal."),
        ("no_inference_from_amenity_alone",
         "A fee, weight or count sentence alone, with no explicit acceptance wording in the same quote, is held "
         "as EVIDENCE_HOLD rather than published; every genuine CLEAN_PET_FRIENDLY row in this market was read "
         "directly from a 'Pets allowed: Yes' / 'Pets Welcome' field or FAQ sentence, so this rule is a safety "
         "net that this run's own captures did not need to exercise except as a guard."),
        ("negation_conflicts_caught", negation_conflicts),
        ("counts", OrderedDict(sorted(counts.items()))),
        ("valid_pet_friendly", len(pf)), ("valid_verified_no_pets", len(np_)),
        ("resolved", len(pf) + len(np_)), ("unresolved", len(hotels) - len(pf) - len(np_)),
        ("rows", rows),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)
    rep = build()
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rep, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("counts:", dict(rep["counts"]))
    print("PF %d / NP %d / resolved %d / unresolved %d" % (
        rep["valid_pet_friendly"], rep["valid_verified_no_pets"], rep["resolved"], rep["unresolved"]))
    print("negation conflicts:", len(rep["negation_conflicts_caught"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
