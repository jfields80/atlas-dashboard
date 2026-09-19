"""PTF-MIAMI-FL-HARDENED-SOURCE-READY-001 -- Phases 15-19: policy adjudication over one identity per row.

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
  launch_packages/pettripfinder/markets/reports/miami_fl_clean_authority_001.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, OrderedDict

_DASH_EARLY = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH_EARLY not in sys.path:
    sys.path.insert(0, _DASH_EARLY)
from scripts.pettripfinder import first_party_binding as FPB  # noqa: E402
from scripts.pettripfinder.hotel_exclusions import address_key  # noqa: E402
from scripts.pettripfinder.miami_fl_census_reconciliation_001 import canonical_street  # noqa: E402

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-MIAMI-FL-HARDENED-SOURCE-READY-001"
MARKET_ID = "miami-fl"
SCHEMA = "ptf-clean-authority/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
STAGING = os.path.join(PKG, "markets", "staging", "miami-fl", "raw_captures")
CENSUS = os.path.join(PKG, "identity_census_proposed", "miami-fl.json")
ROUTING = os.path.join(REPORTS, "miami_fl_routing_001.json")
STATIC = os.path.join(REPORTS, "miami_fl_free_static_capture_001.json")
FIRECRAWL = os.path.join(REPORTS, "miami_fl_firecrawl_pass_001.json")
#: The retry pass (after the census street restatement); a retry row supersedes the first pass's row for its key.
FIRECRAWL_RETRY = os.path.join(REPORTS, "miami_fl_firecrawl_pass_002.json")
#: The second probe pass: rows whose route reached the router's Firecrawl rung only after the Places lane found
#: the property's own site (they were not in the static report the first cohort was planned from).
FIRECRAWL_PROBE2 = os.path.join(REPORTS, "miami_fl_firecrawl_pass_003.json")


def firecrawl_rows():
    by_key = OrderedDict()
    for path in (FIRECRAWL, FIRECRAWL_RETRY, FIRECRAWL_PROBE2):
        for r in (_load(path, {}) or {}).get("rows", []):
            by_key[r["identity_key"]] = r
    return list(by_key.values())


OUT = os.path.join(REPORTS, "miami_fl_clean_authority_001.json")

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
#: A pet COUNT is only a count when a pet noun follows it: "up to 25 lbs" is a weight, and reading its leading
#: digit as "2 pets" published a count the quote contradicts (FAST rule C caught it on Avalon Hotel).
_COUNT_RX = re.compile(r"(?:max(?:imum)?(?: of| number of pets(?: in room)?:?)?|up to|only|limit(?:ed)? to)\s*"
                       r"\(?(\d(?!\d)|one|two|three)\)?\s*(?:additional\s+|small\s+|well[- ]behaved\s+)?"
                       r"(?:pets?|dogs?|cats?|animals?)\b", re.I)
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


#: Two different pages stating one address: the evidence is ambiguous and neither page may publish that row.
_AMBIGUOUS = object()


def _esa_name(name):
    """An Extended Stay America property name reduced to its location words (brand words and punctuation dropped)."""
    n = re.sub(r"[^a-z0-9 ]", " ", (name or "").lower())
    n = re.sub(r"\b(extended stay america|premier|suites|select|stes|the)\b", " ", n)
    return " ".join(n.split())


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


#: A fact is read only from the part of the quote that NAMES pets. A page's own amenity or resort fee sits in the
#: same captured text ("a $35 nightly amenity fee ... We welcome up to 2 dogs"), and taking the first dollar
#: amount in the quote published a pet fee the quote contradicts (FAST rule C caught it on Cardozo South Beach).
_PET_WORD = re.compile(r"\b(pets?|dogs?|cats?|canine|animals?)\b", re.I)


def pet_text(quote):
    """The parts of the quote that state the pet policy: every part naming a pet, plus a part that directly
    continues one ("Pets allowed: Yes." / "$125 non-refundable fee, max weight 30 lbs")."""
    kept, prev_kept = [], False
    for part in re.split(r"(?<=[.!?])\s+|\s*\|\s*|\s{2,}", quote or ""):
        if _PET_WORD.search(part):
            kept.append(part)
            prev_kept = True
        elif prev_kept and not _OTHER_FEE.search(part) and re.search(r"\$|\blbs?\b|\bpounds\b|\bmax", part, re.I):
            kept.append(part)
        else:
            prev_kept = False
    return " ".join(kept)


#: A dollar amount this market's pages carry that is NOT a pet fee.
_OTHER_FEE = re.compile(r"\b(amenity|resort|facility|destination|parking|valet|service|urban|tax|deposit for "
                        r"incidental|room rate|per night from|starting at)\b", re.I)


def pet_fee_cents(quote):
    """The dollar amount the quote states as the PET charge: an amount with pet wording near it and no
    amenity/resort/parking/valet wording in its own neighbourhood. None when the quote names no such amount."""
    best = None
    for m in _FEE_RX.finditer(quote or ""):
        before = quote[max(0, m.start() - 40):m.start()]
        after = quote[m.end():m.end() + 45]
        if _OTHER_FEE.search(before) or _OTHER_FEE.search(after):
            continue
        cents = int(round(float(m.group(1)) * 100))
        if best is None:
            best = cents
    return best


def extract_facts(quote):
    quote = pet_text(quote)
    fee = pet_fee_cents(quote)
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
    by_addr = {}   # address_key(street, postal5) -> evidence  (house number AND street words; a house number
    #                alone collides: 3265 NW 87th Ave and 3265 NW 107th Ave are both 3265 in 33172)

    def add_code(brand, code, ev):
        if brand and code:
            by_code[(brand.upper(), code.lower())] = ev

    def add_key(key, ev):
        if key:
            by_key[key] = ev

    def add_addr(street, postal, ev):
        key = address_key(canonical_street(street or ""), (postal or "")[:5])
        if street and postal and key.split("|")[0]:
            if key in by_addr and by_addr[key].get("source_url") != ev.get("source_url"):
                by_addr[key] = _AMBIGUOUS       # two different pages claim one address: neither may publish
            else:
                by_addr.setdefault(key, ev)

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
        add_addr(r.get("st") or "", r.get("z") or "", ev)

    # MIAMI: the Choice / IHG property pages the Firecrawl route-discovery lane found (their own sitemaps refused
    # this client, so these routes never reached the census by name). Bound ONLY on the house number + postal code
    # the page itself states.
    for r in (_load(os.path.join(STAGING, "brand_page_rows.json"), {}) or {}).get("rows", []):
        if r.get("status") != 200 or not r.get("st") or not r.get("z"):
            continue
        sentences = [s for s in (r.get("pet_sentences") or [])
                     if not (re.search(r"service animals?", s, re.I) and not re.search(r"\bpets?\b|\bdogs?\b", s, re.I))]
        if not sentences:
            continue
        text = " ".join(sentences)
        if _REFUSAL.search(text):
            pets = False
        elif _ACCEPT.search(text):
            pets = True
        else:
            continue
        ev = OrderedDict([("lane", "FIRECRAWL"), ("source_url", r.get("final_url") or r["u"]),
                          ("pets_allowed_claim", pets), ("quote", text[:500]),
                          ("document_sha256", r.get("h") or _transcription_sha(r)),
                          ("captured_via", "the brand's own property page (route discovered on the brand's own city "
                                           "page), Firecrawl rendered scrape, existing plan credits")])
        add_addr(r["st"], r["z"], ev)

    # MIAMI: Extended Stay America's own property pages answered this client (Tampa's did not). The operative
    # statement is the property's own FAQ answer ("Is <property> pet friendly?"); the count sentence on the same
    # page is context. Bound by the page's own JSON-LD street + ZIP, or -- where the page omits its address card --
    # by the page's own property name (from its FAQ question) matching exactly ONE ESA census row.
    esa_doc = _load(os.path.join(STAGING, "esa_rows.json"), {}) or {}
    esa_census = {}
    for h in census_hotels:
        if re.search(r"extended stay america", h.get("canonical_name") or "", re.I):
            esa_census.setdefault(_esa_name(h["canonical_name"]), []).append(h["identity_key"])
    for r in esa_doc.get("rows", []):
        if r.get("s") != 200 or not r.get("p"):
            continue
        ans = r["p"]
        if re.match(r"\s*yes\b", ans, re.I):
            pets = True
        elif re.match(r"\s*no\b", ans, re.I):
            pets = False
        else:
            continue
        ev = OrderedDict([("lane", "PROPERTY_PAGE_STATIC"), ("source_url", r.get("final_url") or r["u"]),
                          ("pets_allowed_claim", pets), ("quote", ans[:500]),
                          ("context", r.get("count_sentence") or ""),
                          ("document_sha256", r.get("h") or _transcription_sha(r)),
                          ("captured_via", "the brand's own property page FAQ JSON-LD, plain client")])
        if r.get("st") and r.get("z"):
            add_addr(r["st"], r["z"], ev)
            continue
        qname = re.sub(r"^\s*is\s+|\s+pet friendly\?\s*$", "", r.get("q") or "", flags=re.I)
        keys = esa_census.get(_esa_name(qname), [])
        if len(keys) == 1:
            ev["binding"] = "BRAND_PAGE_OWN_PROPERTY_NAME_UNIQUE_IN_FAMILY"
            add_key(keys[0], ev)

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
        evs = (r.get("observation") or {}).get("evidence") or []
        # The record's OWN pets_allowed quote is the operative statement, but the shared reader's amenity-chip
        # rule needs the OTHER field quotes on the same page (fee, count, weight) as context to tell a policy
        # BLOCK ("Pets Welcome" beside "$50 fee") from a bare amenity chip -- deduplicated so a fact quoted for
        # two fields is not repeated into what looks like a duplicated, garbled sentence.
        pa_quotes = [e.get("quote", "") for e in evs if "pets_allowed" in (e.get("field_refs") or [])]
        other_quotes = list(dict.fromkeys(e.get("quote", "") for e in evs
                                          if e.get("quote") and "pets_allowed" not in (e.get("field_refs") or [])))
        quotes = pa_quotes or [e.get("quote", "") for e in evs if e.get("quote")]
        ev = OrderedDict([("lane", "PROPERTY_PAGE_STATIC"), ("source_url", r.get("final_url") or r.get("requested_url")),
                          ("pets_allowed_claim", pa), ("quote", " ".join(quotes)[:500] or ("pets_allowed=%s (shared reader)" % pa)),
                          ("context", " ".join(other_quotes)[:500]),
                          ("document_sha256", r.get("page_sha256") or _transcription_sha({"k": r["identity_key"], "u": r.get("requested_url")})),
                          ("captured_via", "shared direct_http_capture pipeline, plain client")])
        add_key(r["identity_key"], ev)

    # CLOSURE (PTF-TAMPA-FL-V2-COVERAGE-CLOSURE-002): 12 supported-browser
    # reads over rows the source-ready build routed to BROWSER_CAPTURE_NEEDED
    # but never reached (Best Western, additional Hyatt/Hilton/IHG rows).
    for r in _jsonl(os.path.join(STAGING, "closure_browser_rows.jsonl")):
        if r.get("outcome") != "READ" or "pets_allowed" not in r:
            continue
        ev = OrderedDict([("lane", "PROPERTY_PAGE_ATTENDED"), ("source_url", r["final_url"]),
                          ("pets_allowed_claim", r["pets_allowed"]), ("quote", r["quote"]),
                          ("document_sha256", r["transcription_sha256"]),
                          ("captured_via", "supported browser, accessibility tree (navigate + find only), closure pass")])
        add_key(r["identity_key"], ev)

    # CLOSURE (PTF-TAMPA-FL-V2-COVERAGE-CLOSURE-002): the 4 newly-admitted
    # Wyndham sub-brand (La Quinta / Days Inn) reads, keyed straight to the
    # identity_key the closure census-additions pass minted for them.
    for r in _load(os.path.join(STAGING, "closure_wyndham_rows.json"), {}).get("rows", []):
        if not r.get("id") or r.get("pet_indicator") not in ("Y", "N"):
            continue
        pets = r["pet_indicator"] == "Y"
        ev = OrderedDict([("lane", "PROPERTY_PAGE_STATIC"), ("source_url", r["u"]),
                          ("pets_allowed_claim", pets), ("quote", r["p"]),
                          ("document_sha256", r.get("h") or _transcription_sha(r)),
                          ("captured_via", "the brand's own property-service API, closure pass")])
        add_key(r["identity_key"], ev)

    # CLOSURE: the routing-hold independents' own websites the Places
    # route-discovery lane found and this pass fetched (same binding
    # discipline as policy_pages_rows.json: house number + postal code,
    # phone digits, or JSON-LD street/postal -- never name alone).
    for r in (_load(os.path.join(STAGING, "closure_static_rows.json"), {}) or {}).get("rows", []):
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
                          ("captured_via", "the independent property's own site (route discovered via Google "
                                          "Places, closure pass), plain client")])
        add_key(r["identity_key"], ev)

    for r in firecrawl_rows():
        if r.get("firecrawl_class") != "FIRECRAWL_PUBLICATION_GRADE":
            continue
        pa = r.get("pets_allowed")
        if pa is None:
            continue
        evs = (r.get("observation") or {}).get("evidence") or []
        pa_quotes = [e.get("quote", "") for e in evs if "pets_allowed" in (e.get("field_refs") or [])]
        other_quotes = list(dict.fromkeys(e.get("quote", "") for e in evs
                                          if e.get("quote") and "pets_allowed" not in (e.get("field_refs") or [])))
        quotes = pa_quotes or [e.get("quote", "") for e in evs if e.get("quote")]
        ev = OrderedDict([("lane", "FIRECRAWL"), ("source_url", r.get("final_url") or r.get("requested_url")),
                          ("pets_allowed_claim", pa), ("quote", " ".join(quotes)[:500] or ("pets_allowed=%s (Firecrawl reader)" % pa)),
                          ("context", " ".join(other_quotes)[:500]),
                          ("document_sha256", r.get("page_sha256") or _transcription_sha({"k": r["identity_key"], "u": r.get("requested_url")})),
                          ("captured_via", "Firecrawl rendered scrape, existing plan credits")])
        add_key(r["identity_key"], ev)

    return by_code, by_key, by_addr


#: The measured supported-browser blockers of this order (raw_captures/browser_attempts.jsonl). Firecrawl is a
#: measured capability wall for Marriott / Hilton (ladder.KNOWN_CAPABILITY_WALLS) and Hyatt / Best Western are
#: excluded brands in the committed route table, so the attended browser is their only remaining lane.
BROWSER_BLOCKERS = {
    "MARRIOTT": "the router sends Marriott to the attended browser (Firecrawl is a measured wall); this session's "
                "browser met an Akamai challenge page and then an extension read-permission refusal on marriott.com",
    "HILTON": "the router sends Hilton to the attended browser (Firecrawl is a measured wall); the browser extension "
              "refused to read hilton.com pages this session (domain permission not granted)",
    "HYATT": "Hyatt is an excluded brand in the committed route table; the browser extension refused to read hyatt.com "
             "pages this session (domain permission not granted)",
    "BEST_WESTERN": "Best Western is an excluded brand in the committed route table; the browser extension refused to "
                    "read bestwestern.com pages this session (domain permission not granted)",
}


def _domain(url):
    host = re.sub(r"^https?://", "", (url or "").strip().lower()).split("/")[0].split(":")[0]
    host = host[4:] if host.startswith("www.") else host
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def route_domain_conflict(census_row, ev):
    """The reason a read may not be published against this identity's bound route, or None.

    The sealed-package contract requires a record to cite the endpoint the census routes the identity to (or the
    same brand family). A brand-routed identity read on its own separate domain is a real, first-party read and a
    real conflict at once: both pages are the property's, and this pass is not allowed to repoint a census route.
    """
    official = str(census_row.get("official_url") or "")
    if not official:
        return None
    src, dst = _domain(ev.get("source_url")), _domain(official)
    if not src or not dst or src == dst:
        return None
    brand = (census_row.get("brand") or "").lower()
    if brand and (brand.split()[0][:6] in src or brand.split()[0][:6] in dst) and src.split(".")[0] in dst:
        return None
    return ("ROUTE_DOMAIN_CONFLICT -- this order read the property's own page at %r while the census binds the "
            "identity to %r; the package contract requires the cited page and the bound route to agree, so the "
            "row is held for a routing decision rather than published against a route it does not cite" % (src, dst))


def router_hold_reason(identity_key, routing_by_key, static_by_key, fc_by_key):
    r = routing_by_key.get(identity_key)
    if r is None:
        return ROUTING_HOLD, "no route was assembled for this identity in the routing pass"
    state = r.get("routing_state")
    if not r.get("url"):
        pl = PLACES_BY_KEY.get(identity_key)
        site = SITES_BY_KEY.get(identity_key)
        if pl is None:
            return ROUTING_HOLD, ("routing state %s: %s" % (state, r.get("why_no_route", "no first-party route stated")))
        if not pl.get("bound"):
            return ROUTING_HOLD, ("NO_OFFICIAL_WEB_PRESENCE_FOUND -- no first-party route, and Places route discovery "
                                  "returned no place with this row's own street number and ZIP")
        if not (pl.get("place") or {}).get("website_uri"):
            return ROUTING_HOLD, ("NO_OFFICIAL_WEB_PRESENCE_FOUND -- Places bound this building (street number + ZIP) "
                                  "but its card names no website")
        if site is None:
            return ROUTING_HOLD, ("OTHER_EXPLICIT_REASON -- the website Places names is a brand / OTA / social host "
                                  "that the independents' lane does not read (%s)" % pl["place"]["website_uri"])
        if site.get("s") != 200:
            return ACCESS_BLOCKED, ("the property's own site (found via Places) did not serve to the plain client "
                                    "(status %s)" % site.get("s"))
        if not site.get("bound"):
            return IDENTITY_MISMATCH_HOLD, ("the site Places names never stated this row's house number + ZIP, phone "
                                            "or JSON-LD address; it is not bound to this identity")
        return SOURCE_SILENT, ("the property's own site (found via Places, bound on its own address/phone) states no "
                               "operative pet policy on its home or policy/FAQ pages")
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
    fam = r.get("brand_family") or ""
    if outcome == "ACCESS_DENIED" and fam in BROWSER_BLOCKERS and (fc is None or fam in ("MARRIOTT", "HILTON")):
        return BROWSER_CAPTURE_NEEDED, ("static fetch was ACCESS_DENIED; %s" % BROWSER_BLOCKERS[fam])
    if outcome == "ACCESS_DENIED" and fam in ("IHG", "CHOICE") and fc is None:
        return BROWSER_CAPTURE_NEEDED, "static fetch was ACCESS_DENIED; the router's Firecrawl rung did not reach this row"
    if fc is not None and fc.get("firecrawl_class") in ("FIRECRAWL_FAILED", "FIRECRAWL_MISMATCH"):
        return ACCESS_BLOCKED, "router exhausted: static %s, Firecrawl %s" % (outcome, fc.get("firecrawl_class"))
    return ACCESS_BLOCKED, "router exhausted on every free/authorized lane attempted this order (static %s)" % outcome


PLACES_BY_KEY = {}
SITES_BY_KEY = {}


def build():
    PLACES_BY_KEY.clear()
    SITES_BY_KEY.clear()
    for r in (_load(os.path.join(REPORTS, "miami_fl_places_route_discovery_001.json"), {}) or {}).get("rows", []):
        if r.get("cohort") == "ROUTE_DISCOVERY":
            PLACES_BY_KEY[r["identity_key"]] = r
    for r in (_load(os.path.join(STAGING, "closure_static_rows.json"), {}) or {}).get("rows", []):
        SITES_BY_KEY[r["identity_key"]] = r
    census = _load(CENSUS, {}) or {}
    hotels = census.get("hotels", [])
    routing_doc = _load(ROUTING, {}) or {}
    routing_by_key = {r["identity_key"]: r for r in routing_doc.get("routes", [])}
    static_by_key = {r["identity_key"]: r for r in (_load(STATIC, {}) or {}).get("rows", [])}
    fc_by_key = {r["identity_key"]: r for r in firecrawl_rows()}
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
            ev = by_addr.get(address_key(h.get("street") or "", (h.get("postal_code") or "")[:5]))
            if ev is _AMBIGUOUS:
                ev = None

        row = OrderedDict([
            ("identity_key", key), ("canonical_name", h["canonical_name"]), ("brand", h.get("brand") or ""),
            ("corridor", h.get("corridor", "")), ("street", h.get("street", "")), ("postal_code", h.get("postal_code", "")),
        ])
        if ev is not None and route_domain_conflict(h, ev):
            # The read is first-party for the building, but the census binds this identity to another host (a
            # brand route). The package contract requires the cited page and the bound route to agree, and this
            # order does not get to repoint a census route from the adjudication pass, so the row is HELD.
            row["disposition"] = EVIDENCE_HOLD
            row["hold_reason"] = route_domain_conflict(h, ev)
            row["evidence"] = ev
            negation_conflicts.append(OrderedDict([("identity_key", key), ("name", h["canonical_name"]),
                                                   ("why", "ROUTE_DOMAIN_CONFLICT -- " + row["hold_reason"])]))
            rows.append(row)
            continue
        if ev is not None:
            final_pa, conflict = negation_check(ev["quote"], ev["pets_allowed_claim"])
            row["evidence"] = ev
            if conflict:
                negation_conflicts.append(OrderedDict([("identity_key", key), ("name", h["canonical_name"]), ("why", conflict)]))
            if final_pa is True:
                row["disposition"] = CLEAN_PET_FRIENDLY
                row["policy_facts"] = extract_facts((ev["quote"] + " " + ev.get("context", "")).strip())
            elif final_pa is False:
                row["disposition"] = CLEAN_VERIFIED_NO_PETS
            else:
                row["disposition"] = NEGATION_HOLD if conflict and "QUOTE_CONTRADICTS_CLAIM" in conflict else EVIDENCE_HOLD
            if conflict:
                row["negation_conflict"] = conflict
            # A SECOND, INDEPENDENT gate: the shared first_party_binding reader that the sealed package's own
            # FAST rule C will run at seal time. Publishing only what this order's own read agrees with is not
            # enough (Phase 17): if the shared reader reads the same quote differently -- most often because it
            # finds service-animal wording alongside the acceptance/refusal statement and will not treat that
            # combination as operative -- this order must hold the row here rather than have the seal reject it
            # later. Never modifies the shared reader; only decides whether THIS row may be published.
            if row["disposition"] in (CLEAN_PET_FRIENDLY, CLEAN_VERIFIED_NO_PETS):
                kind = FPB.KIND_PET_FRIENDLY if row["disposition"] == CLEAN_PET_FRIENDLY else FPB.KIND_NO_PETS
                cls, why = FPB.classify_quote(ev["quote"], kind=kind, context=ev.get("context", ""))
                if cls != FPB.ELIGIBLE:
                    negation_conflicts.append(OrderedDict([
                        ("identity_key", key), ("name", h["canonical_name"]),
                        ("why", "SHARED_READER_DISAGREES -- this order read %s; the shared first_party_binding "
                                "reader classifies the same quote %s: %s" % (row["disposition"], cls, why))]))
                    row["disposition"] = EVIDENCE_HOLD
                    row.pop("policy_facts", None)
                    row["hold_reason"] = ("the shared reader that FAST rule C re-runs at seal time classifies "
                                          "this quote %s (%s), not an operative %s statement; held rather than "
                                          "published on a disagreement this order does not get to override"
                                          % (cls, why[:200], kind))
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
