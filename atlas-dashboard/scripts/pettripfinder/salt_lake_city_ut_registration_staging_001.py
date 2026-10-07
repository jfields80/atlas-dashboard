"""PTF-SALT-LAKE-CITY-UT-HARDENED-SOURCE-READY-001 -- Phase 29: STAGE Salt Lake City / Park City's authority.

Turns this order's clean-authority adjudication into the two documents a registered market is built from, and
validates both against the contracts that own them:

  1. the staged POLICY PACKAGE  markets/staging/salt-lake-city-ut/launch_package/hotel_policy_facts_salt-lake-city-ut.json
     -- schema-1.3 facts, every published fact cited to the quote it rests on.
  2. the PROPOSED AUTHORITY     markets/staging/salt-lake-city-ut/salt_lake_city_ut_proposed_authority_001.json
     -- the ptf-market-proposed-authority/1.0 shape `market_registration_cli` reads to write the shard.

SHADOW_UNTIL_REGISTERED. BOTH documents stay inside this market's own staging tree; neither is written to the
package root, because the root is where a REGISTERED market's documents live and Salt Lake City is registered
nowhere. A registration order later copies them there, and when it does the registration input MUST be named
`<market_us>_proposed_authority_NNN.json` AT THE PACKAGE ROOT -- the classifier recognises the ROLE by that
name, and Orlando lost all fifteen checks to calling it anything else. The staged name already matches, so the
later copy is a move and not a rename.

NOT A FOUNDER SIGNATURE
------------------------
``reviewer_id`` / ``founder_reviewer_id`` on every row is the WORK ORDER string, never a person and never the
operator's name -- this order stages the market without a row-by-row founder review; the founder's decision in
the modern lane is on the exact candidate digest, which is never created here. Writing the operator's name
would be a false attribution (see the Orlando V2 precedent, which states this same rule verbatim).

Nothing here fetches, spends or deploys.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.contracts import enums                     # noqa: E402
from scripts.pettripfinder.contracts import fee_computation as FC     # noqa: E402
from scripts.pettripfinder.contracts import policy_schema as PS       # noqa: E402
# The census identity_key IS the market's normalized key (ptf_identity_key expands "&" to "and", which
# site_data.normalize_name does not); the registration CLI joins the authority to the census on it, so every
# staged row states the census key and never a second spelling of the same name.

WORK_ORDER = "PTF-SALT-LAKE-CITY-UT-HARDENED-SOURCE-READY-001"
MARKET_ID = "salt-lake-city-ut"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CLEAN = os.path.join(REPORTS, "salt_lake_city_ut_clean_authority_001.json")
CENSUS = os.path.join(PKG, "identity_census_proposed", "salt-lake-city-ut.json")
STAGING = os.path.join(PKG, "markets", "staging", "salt-lake-city-ut")
#: SHADOW: the policy package goes inside the staged launch_package (where the shadow seal reads it) and the
#: proposed authority beside it in the market's own staging root. The ROLE NAME is already the one a later
#: registration order needs at the package root.
PACKAGE_OUT = os.path.join(STAGING, "launch_package", "hotel_policy_facts_salt-lake-city-ut.json")
AUTHORITY_OUT = os.path.join(STAGING, "salt_lake_city_ut_proposed_authority_001.json")
#: DENVER: every fee the package does NOT publish, and why -- machine-readable for the source-ready accounting.
FEE_REPORT_OUT = os.path.join(REPORTS, "salt_lake_city_ut_fee_withholding_001.json")
#: PORTLAND: this order's first-party reads span TWO UTC days (the lanes began 2026-10-03T21:33Z and the attended
#: browser read log runs past midnight UTC), so no single day is typed here. CAPTURED_AT is an UPPER BOUND on every
#: capture this package cites: the attended-browser recorder's own real-clock stamp of its LAST read (the last lane
#: this order ran), read from the committed log -- deterministic for a reproduction and never ahead of the clock.
def _last_browser_read_stamp():
    _log = os.path.join(PKG, "markets", "staging", "salt-lake-city-ut", "raw_captures", "browser_reads_001.jsonl")
    _stamps = []
    with open(_log, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                _stamps.append(json.loads(line)["captured_at"])
    _last = max(_stamps)
    return _last[:-1] + "+00:00" if _last.endswith("Z") else _last


CAPTURED_AT = _last_browser_read_stamp()
OBSERVED_AT = CAPTURED_AT[:10]
REVIEWED_AT = CAPTURED_AT[:10]

LANE_GRADE = {
    "PROPERTY_PAGE_ATTENDED": ("attended_browser", "PT2_BRAND", "rendered_html"),
    "PROPERTY_PAGE_STATIC": ("direct_static_fetch", "PT2_BRAND", "rendered_html"),
    "FIRECRAWL": ("direct_static_fetch", "PT2_BRAND", "rendered_html"),
}
_WEIGHT_RX = re.compile(r"(\d+(?:\.\d+)?)\s*(?:lbs?|pounds)\b", re.I)

#: A TIERED FEE IS NOT ONE NUMBER. Hilton states "1-4nts $75, 5+nts $125 per stay" at most Denver Hilton
#: properties, and writing 7500 cents asserts a fee the page does not state for a five-night stay -- the shared
#: first-party binding caught it as FACT_CONTRADICTED, correctly. When a quote names more than one DISTINCT
#: amount the fee is NOT COMPUTABLE: the acceptance, the weight limit, the count and the species still publish
#: from the same quote, because the page states each of those exactly once. A quote that repeats the SAME amount
#: ("1-6 nights: $100 / STAY | 7-30 nights (includes $100 cleaning fee)") is not tiered and still computes.
_DOLLAR_RX = re.compile(r"\$\s*(\d+(?:\.\d{1,2})?)")
#: DENVER: Marriott and Sonesta write the amount as "USD 125" / "125 USD" / "75.00USD", never with a dollar sign.
_USD_RX = re.compile(r"\bUSD\s*\$?\s*(\d+(?:\.\d{1,2})?)\b|\b(\d+(?:\.\d{1,2})?)\s*USD\b", re.I)
TIERED_FEES_OMITTED = []
#: DENVER: A SINGLE FEE CAN MISLEAD TOO. A fee publishes with a BASIS (per night / per stay), and the reader
#: used to default an unstated basis to per_stay -- The Crawford's quote ends "a charge of $50 per n" (cut mid-word
#: at "night") and was staged as $50 per STAY. A fee now publishes only when the quote itself states its basis, no
#: stay-length condition bends it, and the page does not state two bases or two amounts for it. Every withheld fee
#: is listed with its reason; the acceptance, weight, count and species still publish from the same quote.
FEES_WITHHELD_UNSAFE = []
_PER_NIGHT_RX = re.compile(r"per\s+night|nightly|/\s*night|per\s+day\b|/\s*day\b|\bdaily\b|fee\s+per\s+night", re.I)
#: SAN ANTONIO: a DAILY fee is per DAY and a nightly fee per NIGHT -- each is published as the page states it, and
#: neither ever becomes per stay (Drury: "a daily fee of $50 per room"; Best Western Windsor Pointe: "20.00 USD per
#: day"). The SCOPE is published only when the quote states it ("per pet" / "per room").
_PER_DAY_RX = re.compile(r"per\s+day\b|/\s*day\b|\bdaily\b", re.I)
_PER_PET_RX = re.compile(r"\bper\s+pet\b|\beach\s+pet\b|\bpets?\s*,?\s*per\s+(?:night|day|stay)", re.I)
_PER_ROOM_RX = re.compile(r"\bper\s+room\b|\beach\s+room\b", re.I)
#: PHOENIX: Omni states "A $150 non-refundable cleaning fee for each room will be charged for your stay" -- a
#: per-stay basis in the page's own words.
_PER_STAY_RX = re.compile(r"per\s+stay|/\s*stay\b|\bstay\b\s*\|?\s*$|one[- ]time|per\s+visit|per\s+reservation"
                          r"|charged\s+for\s+(?:your|the)\s+stay"
                          # SALT LAKE CITY: AC Hotel Salt Lake City Downtown's own page, "$75 pet fee for entire stay"
                          # beside the template field "Non-Refundable Pet Fee Per Night: ..." -- two bases, never a
                          # nightly $75.
                          r"|(?:for|per)\s+(?:the\s+)?(?:entire|whole)\s+stay", re.I)
_STAY_LENGTH_RX = re.compile(
    r"\b\d+\s*(?:-|to|\u2013|\u2014|\?)\s*\d+\s*(?:n\b|nts?\b|nights?)|\b\d+\s*\+\s*(?:n\b|nts?\b|nights?)"
    r"|up\s+to\s+(?:one|two|\d+)\s+(?:weeks?|nights?)|\bor\s+less\b|length\s+of\s+stay|\bcaps?\s+at\b"
    r"|additional\s+fee\)|from\s+\d+\s+to\s+\d+\s+nights|nights?\s+(?:or\s+more|and\s+(?:over|up))|variable"
    # PORTLAND: Courtyard Portland Downtown/Convention Center states "fee increases after 5 nights" beside a template
    # "$100.00 per stay"; The Society Hotel's daily fee carries "(maximum charge of $..." -- both bend one amount.
    r"|(?:increases?|changes?|rises?)\s+after\s+\d+\s+(?:nights?|days?)|maximum\s+charge|max(?:imum)?\s+charge"
    # MINNEAPOLIS: Hyatt Regency Bloomington's own page, "One to seven nights: $100 nonrefundable pet fee, per stay" --
    # the stay length spelled in words; a stay of eight nights or more is charged something the page does not state.
    r"|\b(?:one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+(?:-|to|through)\s+"
    r"(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fourteen|thirty|\d+)\s+nights?\b"
    # NEW ORLEANS (kept): Extended Stay America's own page, "Not to exceed a $25.00 per day cleaning fee plus tax, for the
    # first six (6) nights, per pet" -- a daily fee capped by stay length; "$25 per day" alone would overstate a long
    # stay.
    r"|\b(?:for\s+the\s+)?first\s+(?:one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s*(?:\(\d+\)\s*)?"
    r"(?:nights?|days?)\b|\bnot\s+to\s+exceed\b", re.I)
#: PORTLAND: Residence Inn Portland Vancouver states "$100 non-refundable, per stay/per month for extended stays" -- a
#: per-stay amount that is ALSO a monthly amount is two bases, never one per-stay fee.
_PER_MONTH_RX = re.compile(r"per\s+month|/\s*month\b|monthly", re.I)
_RANGE_RX = re.compile(r"\b\d+\s*-\s*\d+\s*USD\b|\$\s*\d+\s*-\s*\$?\s*\d+", re.I)
_WAIVED_RX = re.compile(r"\bwaived?\b[^.|]{0,30}\b(?:pet\s+)?fee\b|\bfee\b[^.|]{0,30}\bwaived\b", re.I)
_ADDITIONAL_PET_RX = re.compile(r"\b(?:first|one)\s+pet\s+(?:stays?\s+)?free\b"
                                r"|\b(?:second|additional|each\s+additional)\s+pets?\b[^.|]{0,20}\$", re.I)


def _stated_amounts(quote):
    amounts = {float(m.group(1)) for m in _DOLLAR_RX.finditer(quote or "")}
    for m in _USD_RX.finditer(quote or ""):
        amounts.add(float(m.group(1) or m.group(2)))
    return amounts


#: SALT LAKE CITY: A FEE SENTENCE THE CAPTURE CUT IS NOT A WHOLE FEE. The attended browser's accessibility tree cuts a
#: node at 100 characters, and Choice's own page for Comfort Inn & Suites Salt Lake City Airport reads "60.00 USD
#: non-refundable charge per stay, per dog, up to seven nigh" -- the stay-length condition is cut mid-word, and Radisson
#: Hotel Salt Lake City Downtown's "Pet Charge 75.00 USD Per Pet, Per Stay. Non-Refundable deposit o.." names a second
#: charge whose amount is cut. When the quote ends mid-sentence and that last sentence speaks of a fee, a charge, a
#: deposit, an amount or a stay length, the fee is withheld; the acceptance still publishes.
#: Only a segment the tree could have cut counts: one at least CUT_NODE_LENGTH characters long. A brand's short
#: structured field ("Maximum Number of Pets in Room: 2") ends without punctuation by design and is never "cut".
CUT_NODE_LENGTH = 95
_TERMINAL_RX = re.compile(r"[.!?)]\s*$")
_CUT_WORD_RX = re.compile(r"\b[A-Za-z]{1,2}\.{2}$")   # "Non-Refundable deposit o.." -- a word cut before Choice's ".."
_CUT_FEE_TAIL_RX = re.compile(r"\d|\$|\busd\b|\bfees?\b|deposit|charge|\bnights?\b|\bnigh\b|\bstays?\b|\bdays?\b",
                              re.I)


def _fee_sentence_cut(quote):
    last = re.split(r"\s*\|\s*", (quote or "").strip())[-1]
    if len(last) < CUT_NODE_LENGTH:
        return False
    tail = re.split(r"(?<=[.!?])\s+", last)[-1]
    if _TERMINAL_RX.search(last) and not _CUT_WORD_RX.search(last):
        return False
    return bool(_CUT_FEE_TAIL_RX.search(tail))


#: "<fee word or amount> [up to three words] per <pet|room>" -- the scope attached to the fee, never to a count.
_FEE_SCOPE_RX = (r"(?:\bfees?\b|\bcharge\b|\$\s*\d+(?:\.\d+)?|\b\d+(?:\.\d+)?\s*usd\b|\busd\s*\d+(?:\.\d+)?)"
                 r"(?:[\s,]+(?!per\b)[\w-]+){0,3}?(?:[\s,]+per\s+(?:night|day|stay)\b)?[\s,]+(?:per|each)\s+%s\b")


def _fee_sentences(quote, cents):
    """The quote's sentences / field segments that state the fee amount (``cents``), joined; '' when none does."""
    whole = cents / 100.0
    want = {("%d" % whole) if whole == int(whole) else "", "%.2f" % whole} - {""}
    parts = [p for p in re.split(r"\s*\|\s*|(?<=[.!?])\s+", quote or "") if p]
    hits = [p for p in parts if any(re.search(r"(?<![\d.])%s(?![\d])" % re.escape(w), p) for w in want)]
    return " ".join(hits)


def _fee_withhold_reason(quote):
    """Why a single computed fee would mislead, or '' when it is safe to publish with its basis."""
    q = quote or ""
    if _fee_sentence_cut(q):
        return ("FEE_SENTENCE_CUT -- the capture ends mid-sentence inside a statement about the fee, a charge, a "
                "deposit or a stay length, so the amount's conditions are not all visible")
    # SEATTLE: Residence Inn Seattle East/Redmond's page states "Enjoy a waived pet fee, covered by the Redmond
    # Tourism Promotion Area" beside the brand template's "Non-Refundable Pet Fee Per Stay: $150.00"; publishing the
    # $150 would contradict the property's own sentence.
    if _WAIVED_RX.search(q):
        return "FEE_STATED_AS_WAIVED -- the page states the pet fee is waived beside a template amount"
    # SEATTLE: Red Roof Seattle Airport states "First pet stays free. Second pet $15 per night." -- the amount
    # applies only to an ADDITIONAL pet, and a single fee would charge the first pet too.
    if _ADDITIONAL_PET_RX.search(q):
        return "ADDITIONAL_PET_ONLY -- the amount applies only to a second or additional pet"
    if _STAY_LENGTH_RX.search(q):
        return "STAY_LENGTH_CONDITION -- the fee depends on how long the guest stays"
    if _RANGE_RX.search(q):
        return "AMOUNT_RANGE -- the page states a range, not one amount"
    night, stay = bool(_PER_NIGHT_RX.search(q)), bool(_PER_STAY_RX.search(q))
    if _PER_MONTH_RX.search(q) and (night or stay):
        return "TWO_BASES -- the page states a monthly basis beside a nightly or per-stay one for the fee"
    if night and stay:
        return "TWO_BASES -- the page states both a nightly and a per-stay basis for the fee"
    if not (night or stay):
        return "BASIS_NOT_STATED -- the page states an amount but not whether it is charged per night or per stay"
    return ""


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _ev_ref(*parts):
    return "ev:" + hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()[:16]


def _facts(pets_allowed, pf, quote):
    out = OrderedDict()
    out["pets_allowed"] = bool(pets_allowed)
    if not out["pets_allowed"]:
        return out
    weight = pf.get("max_pet_weight_lbs")
    if weight is not None and float(weight) > 0:
        out["weight_limit"] = OrderedDict([("value", float(weight)), ("unit", "lb"), ("operator", "lte"),
                                           ("scope", "per_pet")])
    tiered = _stated_amounts(quote)
    unsafe = _fee_withhold_reason(quote) if pf.get("pet_fee_cents") is not None else ""
    if pf.get("pet_fee_cents") is not None and len(tiered) > 1:
        TIERED_FEES_OMITTED.append(OrderedDict([
            ("stated_amounts_usd", sorted(tiered)),
            ("fee_the_reader_computed_cents", int(pf["pet_fee_cents"])),
            ("quote", quote),
            ("why", "the page states a different fee for a different stay length; one number would assert a "
                    "price the page does not state, so the fee is omitted and the row publishes without one"),
        ]))
    elif unsafe:
        FEES_WITHHELD_UNSAFE.append(OrderedDict([
            ("fee_the_reader_computed_cents", int(pf["pet_fee_cents"])), ("why", unsafe), ("quote", quote),
        ]))
    elif pf.get("pet_fee_cents") is not None:
        # PHOENIX: THE PUBLISHED BASIS IS THE ONE THE SAFETY CHECK READ. Drury states "a daily fee of $50 per
        # room": the safety check (_PER_NIGHT_RX) reads "daily" as nightly and passes the fee, but the basis
        # used to be re-derived from a narrower pattern without "daily" and fell to per_stay -- a nightly fee
        # published as a one-time fee. The basis is now taken from the same pattern that cleared the fee.
        fee = OrderedDict([("amount_cents", int(pf["pet_fee_cents"])), ("currency", pf.get("fee_currency") or "USD"),
                           ("basis", ("per_day" if _PER_DAY_RX.search(quote) else "per_night")
                            if _PER_NIGHT_RX.search(quote) else "per_stay")])
        # SALT LAKE CITY: THE SCOPE IS THE FEE SENTENCE'S OWN. Outbound Park City states "two dogs per room ... A $50
        # nightly pet fee applies." -- "per room" scopes the dog COUNT, and reading it from the whole quote published a
        # per-room fee the page never states. Only the sentences (or field segments) that carry the fee amount decide.
        # Within that sentence the scope must attach to the FEE itself ("fee per room", "100 USD plus tax per room",
        # "$75 per pet") -- "2 pets per room with $150 non-refundable fee per stay" scopes the count, not the fee.
        _fee_text = _fee_sentences(quote, int(pf["pet_fee_cents"]))
        _pet = bool(_FEE_SCOPE_RX % "pet" and re.search(_FEE_SCOPE_RX % "pet", _fee_text, re.I))
        _room = bool(re.search(_FEE_SCOPE_RX % "room", _fee_text, re.I))
        if _pet != _room:
            fee["scope"] = "per_pet" if _pet else "per_room"
        # A REFUNDABLE amount is a deposit under the shared fee/deposit contract
        # (other_charges[kind=refundable_deposit]), never a pet_fee.refundable=True -- and this order does not
        # build a separate other_charges record, so a refundable component is safely omitted here rather than
        # written into the wrong field. Only an explicit non-refundable statement is ever written.
        if pf.get("fee_refundable") is False:
            fee["refundable"] = False
        out["pet_fee"] = fee
    if pf.get("max_pet_count") is not None:
        out["pet_count_limit"] = int(pf["max_pet_count"])
    species = []
    if re.search(r"\bdogs?\b", quote, re.I) and re.search(r"\bcats?\b", quote, re.I):
        species = ["cat", "dog"]
    elif re.search(r"\bdogs?\s+only\b", quote, re.I):
        species = ["dog"]
    if species:
        out["species"] = OrderedDict((s, "accepted") for s in sorted(species))
        out["species_source_grade"] = OrderedDict((s, "PT2_BRAND") for s in sorted(species))
    return out


def _evidence(key, lane, quote, source_url, doc_sha, facts):
    method, grade, kind = LANE_GRADE.get(lane, ("direct_static_fetch", "PT2_BRAND", "rendered_html"))
    entries = []
    for field, value in facts.items():
        entries.append(OrderedDict([
            ("field", field), ("quote", quote), ("source_url", source_url),
            ("value", json.dumps(value, sort_keys=True) if isinstance(value, (dict, list))
             else str(value).lower() if isinstance(value, bool) else str(value)),
            ("evidence_ref", _ev_ref(key, field, doc_sha or source_url)),
            ("artifact_class", "PUBLICATION_GRADE_EVIDENCE"),
            ("artifact_sha256", ("sha256:" + doc_sha) if doc_sha else ""),
            ("artifact_kind", kind), ("captured_at", CAPTURED_AT), ("capture_method", method),
            ("source_grade", grade),
        ]))
    return entries


def build():
    clean = _load(CLEAN)
    census = {h["identity_key"]: h for h in _load(CENSUS)["hotels"]}
    rows_by_key = {r["identity_key"]: r for r in clean["rows"]}

    hotels, pet_friendly, exclusions, refused = [], [], [], []
    unresolved_keys = []

    for r in clean["rows"]:
        key = r["identity_key"]
        c = census.get(key)
        if c is None:
            continue
        disp = r["disposition"]
        if disp not in ("CLEAN_PET_FRIENDLY", "CLEAN_VERIFIED_NO_PETS"):
            unresolved_keys.append(key)
            continue
        ev = r.get("evidence") or {}
        quote = ev.get("quote") or ""
        # The evidence entries staged for EVERY fact field of this record must all cite text from the SAME
        # artifact (first_party_binding._context groups an acceptance quote's context by matching
        # artifact_sha256, never by field): a bare "pets allowed" quote is an AMENITY_CHIP_ONLY on its own even
        # though the record's own fee/count context, captured separately, proves it is a real policy block.
        # Every field's staged quote is therefore the full quote+context text, not the short quote alone.
        full_quote = (quote + " " + ev.get("context", "")).strip() or quote
        lane = ev.get("lane") or ""
        source_url = ev.get("source_url") or c.get("official_url") or ""
        doc_sha = ev.get("document_sha256") or ""

        if disp == "CLEAN_PET_FRIENDLY":
            pf = r.get("policy_facts") or {}
            facts = _facts(True, pf, full_quote)
            issues = PS.validate_facts(facts)
            if issues:
                refused.append((key, "; ".join(str(i) for i in issues)[:160]))
                continue
            record = OrderedDict([
                ("key", key), ("identity_key", key), ("name", c["canonical_name"]),
                ("market_id", MARKET_ID), ("schema_version", PS.SCHEMA_VERSION), ("facts", facts),
                ("computation_class", FC.classify(facts).computation_class),
                ("verification_state", "VERIFIED_PET_FRIENDLY"),
                ("reviewer_id", WORK_ORDER), ("reviewed_at", REVIEWED_AT),
                ("evidence", _evidence(key, lane, full_quote, source_url, doc_sha, facts)),
            ])
            r_issues = PS.validate_record(record)
            if r_issues:
                refused.append((key, "; ".join(str(i) for i in r_issues)[:160]))
                continue
            hotels.append(record)
            pet_friendly.append(OrderedDict([
                ("identity_key", key), ("normalized_name", key),
                ("canonical_name", c["canonical_name"]), ("address", c.get("street") or ""),
                ("city", c.get("city") or ""), ("state", c.get("state") or ""),
                ("postal_code", (c.get("postal_code") or "")[:5]),
                ("official_url", c.get("official_url") or source_url), ("source_url", source_url),
                ("observed_at", OBSERVED_AT), ("brand", c.get("brand") or ""), ("corridor", c.get("corridor") or ""),
                ("evidence", record["evidence"]), ("evidence_quote", quote), ("facts", dict(facts)),
                ("authority_state", enums.PUBLISHED_PET_FRIENDLY), ("publication_grade", "PUBLICATION_GRADE_EVIDENCE"),
                ("readiness_state", "READY"), ("founder_decision", "REGISTERED_NOT_AUTHORIZED_FOR_LAUNCH"),
                ("founder_reviewer_id", WORK_ORDER), ("founder_reviewed_at", REVIEWED_AT), ("snapshot_hash", doc_sha),
            ]))
        else:
            exclusions.append(OrderedDict([
                ("identity_key", key), ("normalized_name", key),
                ("canonical_name", c["canonical_name"]), ("address", c.get("street") or ""),
                ("city", c.get("city") or ""), ("state", c.get("state") or ""),
                ("postal_code", (c.get("postal_code") or "")[:5]),
                ("official_url", c.get("official_url") or source_url), ("source_url", source_url),
                ("observed_at", OBSERVED_AT), ("brand", c.get("brand") or ""), ("corridor", c.get("corridor") or ""),
                ("evidence", _evidence(key, lane, quote, source_url, doc_sha, OrderedDict([("pets_allowed", False)]))),
                ("evidence_quote", quote),
                ("exclusion_id", "%s--%s" % (MARKET_ID, re.sub(r"[^a-z0-9]+", "-", key).strip("-"))),
                ("exclusion_state", enums.VERIFIED_NO_PETS), ("snapshot_hash", doc_sha),
                ("publication_grade", "PUBLICATION_GRADE_EVIDENCE"), ("readiness_state", "READY"),
                ("founder_decision", "REGISTERED_NOT_AUTHORIZED_FOR_LAUNCH"),
                ("founder_reviewer_id", WORK_ORDER), ("founder_reviewed_at", REVIEWED_AT),
            ]))

    package = OrderedDict([
        ("market", "Salt Lake City / Park City / Wasatch Front, Utah"), ("schema_version", PS.SCHEMA_VERSION),
        ("market_id", MARKET_ID),
        ("work_order", WORK_ORDER), ("as_of", REVIEWED_AT),
        ("note", "Salt Lake City / Park City / Wasatch Front's STAGED (shadow, unregistered) policy package. Every record is "
                "one first-party read of the property's own page, and every published fact is cited to the quote "
                "it rests on. Refundability is absent, not false, when the source stated neither refundable nor "
                "non-refundable."),
        ("hotels", hotels),
    ])
    pkg_issues = PS.validate_package(package)

    authority = OrderedDict([
        ("schema", "ptf-market-proposed-authority/1.0"),
        ("what_this_is", "Salt Lake City / Park City / Wasatch Front's authority as the source-ready order proposed it, to be REGISTERED "
                        "by a later registration order. Registration makes the market "
                        "BUILDABLE; launch_participation.json decides whether it is BUILT into production, and "
                        "that stays at SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH. The founder gate in "
                        "the modern lane is on the exact candidate digest, which is never created here."),
        ("market_id", MARKET_ID), ("work_order", WORK_ORDER),
        ("registered", True), ("published", False), ("deployed", False),
        ("built_from", OrderedDict([
            ("source_ledgers", [os.path.relpath(CLEAN, _DASH).replace("\\", "/")]),
            ("decision_ledger", "ptf-market-clean-authority/1.0"), ("decided_by", WORK_ORDER),
            ("decided_at", REVIEWED_AT), ("approval_vocabulary", "REGISTERED_NOT_AUTHORIZED_FOR_LAUNCH"),
        ])),
        ("gate", "a row reaches this document only with an operative first-party quote bound to an ADMITTED "
                "census identity; nothing here is authorised for launch"),
        ("signed_rows_in", len(pet_friendly) + len(exclusions)),
        ("superseded_count", 0), ("superseded_rows", []), ("identity_confirmations", []),
        ("pet_friendly_count", len(pet_friendly)), ("verified_no_pets_count", len(exclusions)),
        ("authority_total", len(pet_friendly) + len(exclusions)),
        ("unresolved", unresolved_keys),
        ("pet_friendly", pet_friendly), ("verified_no_pets", exclusions),
    ])
    return package, authority, pkg_issues, refused


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    package, authority, issues, refused = build()
    print("policy records   :", len(package["hotels"]))
    print("authority PF     :", authority["pet_friendly_count"])
    print("authority no-pets:", authority["verified_no_pets_count"])
    print("refused          :", len(refused))
    for k, why in refused[:10]:
        print("   -", k, "::", why)
    print("package issues   :", len(issues))
    for i in issues[:10]:
        print("   !", str(i)[:200])
    print("computation      :", dict(Counter(h["computation_class"] for h in package["hotels"])))
    print("unsafe single fees withheld:", len(FEES_WITHHELD_UNSAFE),
          dict(Counter(x["why"].split(" --")[0] for x in FEES_WITHHELD_UNSAFE)))
    print("tiered fees omitted:", len(TIERED_FEES_OMITTED))
    for t in TIERED_FEES_OMITTED:
        print("   ", t["stated_amounts_usd"], "|", t["quote"][:96])
    if issues:
        print("NOT WRITTEN -- the package must validate before it is committed")
        return 1
    if args.write:
        for path, doc in ((PACKAGE_OUT, package), (AUTHORITY_OUT, authority)):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(doc, fh, indent=1, ensure_ascii=False)
                fh.write("\n")
            print("written          :", os.path.relpath(path, _DASH))
        fee_report = OrderedDict([
            ("schema", "ptf-fee-withholding/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
            ("rule", "a fee publishes only as one amount whose basis (per night / per stay) the quote itself states, "
                     "with no stay-length condition, no range, no second basis and no second amount; otherwise the "
                     "fee is withheld and the acceptance, weight, count and species still publish"),
            ("fees_published", sum(1 for h in package["hotels"] if "pet_fee" in h["facts"])),
            ("tiered_fees_withheld", len(TIERED_FEES_OMITTED)),
            ("unsafe_single_fees_withheld", len(FEES_WITHHELD_UNSAFE)),
            ("unsafe_by_reason", OrderedDict(sorted(Counter(x["why"].split(" --")[0]
                                                            for x in FEES_WITHHELD_UNSAFE).items()))),
            ("misleading_single_fees_published", 0),
            ("tiered", TIERED_FEES_OMITTED), ("unsafe", FEES_WITHHELD_UNSAFE),
        ])
        with open(FEE_REPORT_OUT, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(fee_report, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        print("written          :", os.path.relpath(FEE_REPORT_OUT, _DASH))
    else:
        print("(dry run; pass --write to commit the documents)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
