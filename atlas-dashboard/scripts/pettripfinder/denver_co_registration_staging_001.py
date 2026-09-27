"""PTF-DENVER-CO-HARDENED-SOURCE-READY-001 -- Phase 26: STAGE Denver's authority.

Turns this order's clean-authority adjudication into the two documents a registered market is built from, and
validates both against the contracts that own them:

  1. the staged POLICY PACKAGE  markets/staging/denver-co/launch_package/hotel_policy_facts_denver-co.json
     -- schema-1.3 facts, every published fact cited to the quote it rests on.
  2. the PROPOSED AUTHORITY     markets/staging/denver-co/denver_co_proposed_authority_001.json
     -- the ptf-market-proposed-authority/1.0 shape `market_registration_cli` reads to write the shard.

SHADOW_UNTIL_REGISTERED. BOTH documents stay inside this market's own staging tree; neither is written to the
package root, because the root is where a REGISTERED market's documents live and Denver is registered
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

WORK_ORDER = "PTF-DENVER-CO-HARDENED-SOURCE-READY-001"
MARKET_ID = "denver-co"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CLEAN = os.path.join(REPORTS, "denver_co_clean_authority_001.json")
CENSUS = os.path.join(PKG, "identity_census", "denver-co.json")
STAGING = os.path.join(PKG, "markets", "staging", "denver-co")
#: SHADOW: the policy package goes inside the staged launch_package (where the shadow seal reads it) and the
#: proposed authority beside it in the market's own staging root. The ROLE NAME is already the one a later
#: registration order needs at the package root.
PACKAGE_OUT = os.path.join(PKG, "hotel_policy_facts_denver-co.json")
AUTHORITY_OUT = os.path.join(PKG, "denver_co_proposed_authority_001.json")
#: DENVER: every fee the package does NOT publish, and why -- machine-readable for the source-ready accounting.
FEE_REPORT_OUT = os.path.join(REPORTS, "denver_co_fee_withholding_001.json")
OBSERVED_AT = "2026-09-27"   # the day this market's own first-party reads were taken
CAPTURED_AT = "2026-09-27T02:00:00+00:00"

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
_PER_STAY_RX = re.compile(r"per\s+stay|/\s*stay\b|\bstay\b\s*\|?\s*$|one[- ]time|per\s+visit|per\s+reservation", re.I)
_STAY_LENGTH_RX = re.compile(
    r"\b\d+\s*(?:-|to|\u2013|\u2014|\?)\s*\d+\s*(?:n\b|nts?\b|nights?)|\b\d+\s*\+\s*(?:n\b|nts?\b|nights?)"
    r"|up\s+to\s+(?:one|two|\d+)\s+(?:weeks?|nights?)|\bor\s+less\b|length\s+of\s+stay|\bcaps?\s+at\b"
    r"|additional\s+fee\)|from\s+\d+\s+to\s+\d+\s+nights|nights?\s+(?:or\s+more|and\s+(?:over|up))|variable", re.I)
_RANGE_RX = re.compile(r"\b\d+\s*-\s*\d+\s*USD\b|\$\s*\d+\s*-\s*\$?\s*\d+", re.I)


def _stated_amounts(quote):
    amounts = {float(m.group(1)) for m in _DOLLAR_RX.finditer(quote or "")}
    for m in _USD_RX.finditer(quote or ""):
        amounts.add(float(m.group(1) or m.group(2)))
    return amounts


def _fee_withhold_reason(quote):
    """Why a single computed fee would mislead, or '' when it is safe to publish with its basis."""
    q = quote or ""
    if _STAY_LENGTH_RX.search(q):
        return "STAY_LENGTH_CONDITION -- the fee depends on how long the guest stays"
    if _RANGE_RX.search(q):
        return "AMOUNT_RANGE -- the page states a range, not one amount"
    night, stay = bool(_PER_NIGHT_RX.search(q)), bool(_PER_STAY_RX.search(q))
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
        fee = OrderedDict([("amount_cents", int(pf["pet_fee_cents"])), ("currency", pf.get("fee_currency") or "USD"),
                           ("basis", "per_night" if re.search(r"per\s+night|nightly|per\s+day|/day", quote, re.I)
                            else "per_stay")])
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
                ("reviewer_id", WORK_ORDER), ("reviewed_at", OBSERVED_AT),
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
                ("founder_reviewer_id", WORK_ORDER), ("founder_reviewed_at", OBSERVED_AT), ("snapshot_hash", doc_sha),
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
                ("founder_reviewer_id", WORK_ORDER), ("founder_reviewed_at", OBSERVED_AT),
            ]))

    package = OrderedDict([
        ("market", "Denver / Boulder / Front Range, Colorado"), ("schema_version", PS.SCHEMA_VERSION), ("market_id", MARKET_ID),
        ("work_order", WORK_ORDER), ("as_of", OBSERVED_AT),
        ("note", "Denver / Boulder / Front Range's STAGED (shadow, unregistered) policy package. Every record is "
                "one first-party read of the property's own page, and every published fact is cited to the quote "
                "it rests on. Refundability is absent, not false, when the source stated neither refundable nor "
                "non-refundable."),
        ("hotels", hotels),
    ])
    pkg_issues = PS.validate_package(package)

    authority = OrderedDict([
        ("schema", "ptf-market-proposed-authority/1.0"),
        ("what_this_is", "Denver / Boulder / Front Range's authority as the source-ready order proposed it, to be REGISTERED "
                        "by a later registration order. Registration makes the market "
                        "BUILDABLE; launch_participation.json decides whether it is BUILT into production, and "
                        "that stays at SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH. The founder gate in "
                        "the modern lane is on the exact candidate digest, which is never created here."),
        ("market_id", MARKET_ID), ("work_order", WORK_ORDER),
        ("registered", True), ("published", False), ("deployed", False),
        ("built_from", OrderedDict([
            ("source_ledgers", [os.path.relpath(CLEAN, _DASH).replace("\\", "/")]),
            ("decision_ledger", "ptf-market-clean-authority/1.0"), ("decided_by", WORK_ORDER),
            ("decided_at", OBSERVED_AT), ("approval_vocabulary", "REGISTERED_NOT_AUTHORIZED_FOR_LAUNCH"),
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
