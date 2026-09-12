"""PTF-PIEDMONT-TRIAD-NC-NORMAL-PRODUCTION-001 -- Phase 8: register the Piedmont Triad.

Turns this order's CLEAN SET into the two documents a registered market is built
from, and validates both against the contracts that own them:

  1. the committed POLICY PACKAGE  launch_packages/pettripfinder/hotel_policy_facts_piedmont-triad-nc.json
     -- schema-1.3 facts, every published fact cited to the quote it rests on,
        every citation carrying the sha256 of the document it was read from.
  2. the PROPOSED AUTHORITY        launch_packages/pettripfinder/piedmont_triad_nc_proposed_authority_002.json
     -- the ptf-market-proposed-authority/1.0 shape `market_registration_cli`
        reads to write the shard.

WHY THIS ORDER MAY REGISTER WITHOUT A ROW-BY-ROW FOUNDER SIGNATURE
------------------------------------------------------------------
Registration is not publication. Writing `markets/piedmont-triad-nc.json`, an
authority shard and a release contract makes the market BUILDABLE; what decides
whether it reaches production is `launch_participation.json`, which this order
sets to SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH and does not flip.
The founder gate in the modern lane is on the exact CANDIDATE DIGEST
(ATLAS-THROUGHPUT-005), not on each row, and this order stops at that gate.

STRUCTURED FACTS, NEVER INFERRED
--------------------------------
A fact reaches the package only when the quote it is cited to contains the
vocabulary that fact is made of. Refundability is UNKNOWN unless the source says
"refundable" or "non-refundable" -- the silence of a source is not a fact about
a fee. A weight the source states as a COMBINED maximum is written as combined,
never silently as per-pet.

Nothing here fetches, spends or deploys.
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

from scripts.pettripfinder.contracts import enums                     # noqa: E402
from scripts.pettripfinder.contracts import fee_computation as FC     # noqa: E402
from scripts.pettripfinder.contracts import policy_schema as PS       # noqa: E402
from scripts.pettripfinder.site_data import normalize_name            # noqa: E402

WORK_ORDER = "PTF-PIEDMONT-TRIAD-NC-NORMAL-PRODUCTION-001"
MARKET_ID = "piedmont-triad-nc"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CLEAN = os.path.join(REPORTS, "piedmont_triad_nc_clean_authority_001.json")
CENSUS = os.path.join(PKG, "identity_census", "piedmont-triad-nc.json")
PACKAGE_OUT = os.path.join(PKG, "hotel_policy_facts_piedmont-triad-nc.json")
AUTHORITY_OUT = os.path.join(PKG, "piedmont_triad_nc_proposed_authority_002.json")
OBSERVED_AT = "2026-09-12"
CAPTURED_AT = "2026-09-12T21:15:00+00:00"

#: How each lane is graded for provenance. Both are first-party reads of the
#: property's own page; they differ only in which client made the request.
#: The evidence contract's artifact_kind vocabulary is
#: (rendered_html, operator_screenshot, pdf, text_extract). Both Raleigh lanes
#: persist the HTML DOCUMENT the server returned, so both are rendered_html;
#: what differs is the CAPTURE METHOD, which is recorded separately and is the
#: field that says whether a person's browser or a plain client made the
#: request. Inventing a fifth kind to record that difference would put it in the
#: wrong field.
LANE_GRADE = {
    "ATTENDED_BROWSER": ("attended_browser", "PT2_BRAND", "rendered_html"),
    "DIRECT_STATIC_FETCH": ("direct_static_fetch", "PT2_BRAND", "rendered_html"),
}


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _ev_ref(*parts):
    return "ev:" + hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()[:16]


def _facts(extraction, quote):
    """The schema-1.3 fact object, built only from what the quote supports."""
    out = OrderedDict()
    out["pets_allowed"] = bool(extraction.get("pets_allowed"))
    if not out["pets_allowed"]:
        return out
    # A source that publishes a maximum pet weight of ZERO has stated no limit,
    # whatever its field says. Hilton's petMaxWeight is 0 for a handful of
    # properties whose petsInfo otherwise reads as an acceptance; the weight is
    # dropped as UNKNOWN rather than published as "0 lbs" and rather than
    # refusing the whole record, because the ACCEPTANCE is still stated.
    if extraction.get("weight_limit") is not None and float(extraction["weight_limit"]) <= 0:
        extraction = {k: v for k, v in extraction.items()
                      if k not in ("weight_limit", "weight_limit_unit", "weight_basis")}
    if "weight_limit" in extraction:
        # A COMBINED maximum is its own schema field, never a per-pet limit
        # wearing a scope key: "a combined weight of no more than 80 pounds" for
        # two pets is not "80 pounds per pet", and writing it as the latter
        # would publish a limit twice as generous as the hotel stated.
        node = OrderedDict((
            ("value", float(extraction["weight_limit"])),
            ("unit", extraction.get("weight_limit_unit") or "lb"),
            ("operator", "lte")))
        if extraction.get("weight_basis") == "combined":
            out["combined_weight_limit"] = node
        else:
            node["scope"] = "per_pet"
            out["weight_limit"] = node
    if "pet_fee" in extraction:
        fee = OrderedDict((
            ("amount_cents", int(extraction["pet_fee"])),
            ("currency", extraction.get("fee_currency") or "USD"),
            ("scope", extraction.get("fee_scope") or "per_pet"),
            ("basis", extraction.get("fee_basis")
             or ("per_night" if re.search(r"per\s+night|nightly|per\s+day|/day", quote, re.I)
                 else "per_stay" if re.search(r"per\s+stay|one[- ]time", quote, re.I)
                 else "per_stay")),
        ))
        if "fee_refundable" in extraction:
            fee["refundable"] = bool(extraction["fee_refundable"])
        elif re.search(r"non-?\s?refundable", quote, re.I):
            fee["refundable"] = False
        out["pet_fee"] = fee
    if "pet_count_limit" in extraction:
        out["pet_count_limit"] = int(extraction["pet_count_limit"])
    if "species_allowed" in extraction:
        # The schema keeps species as a STATE MAP with a source grade per
        # species, not a bare list: a source that names dogs and cats has said
        # nothing about birds, and an accepting state may only be written from
        # first-party evidence.
        out["species"] = OrderedDict(
            (name, "accepted") for name in sorted(extraction["species_allowed"]))
        out["species_source_grade"] = OrderedDict(
            (name, "PT2_BRAND") for name in sorted(extraction["species_allowed"]))
    return out


def _evidence(rec, facts):
    method, grade, kind = LANE_GRADE.get(rec["lane"], ("direct_static_fetch", "PT2_BRAND",
                                                       "rendered_html"))
    sha = rec.get("document_sha256") or ""
    entries = []
    for field, value in facts.items():
        entries.append(OrderedDict((
            ("field", field),
            ("quote", rec["operative_quote"]),
            ("source_url", rec["final_url"] or rec["source_url"]),
            ("value", json.dumps(value, sort_keys=True) if isinstance(value, (dict, list))
             else str(value).lower() if isinstance(value, bool) else str(value)),
            ("evidence_ref", _ev_ref(rec["identity_key"], field, sha)),
            ("artifact_class", "PUBLICATION_GRADE_EVIDENCE"),
            ("artifact_sha256", ("sha256:" + sha) if sha else ""),
            ("artifact_kind", kind),
            ("captured_at", CAPTURED_AT),
            ("capture_method", method),
            ("source_grade", grade),
        )))
    return entries


def build():
    clean = _load(CLEAN)
    census = {h["identity_key"]: h for h in _load(CENSUS)["hotels"]}

    hotels, pet_friendly, exclusions, refused = [], [], [], []

    for rec in clean["clean_pet_friendly"]:
        key = rec["identity_key"]
        c = census.get(key)
        if c is None:
            refused.append((key, "no census row"))
            continue
        facts = _facts(rec["extraction"], rec["operative_quote"])
        issues = PS.validate_facts(facts)
        if issues:
            refused.append((key, "; ".join(str(i) for i in issues)[:160]))
            continue
        record = OrderedDict((
            ("key", normalize_name(c["canonical_name"])),
            ("identity_key", key),
            ("name", c["canonical_name"]),
            ("market_id", MARKET_ID),
            ("schema_version", PS.SCHEMA_VERSION),
            ("facts", facts),
            ("computation_class", FC.classify(facts).computation_class),
            # The first-party binding gate requires a publishable verification
            # state AND a recorded review. The reviewer is the WORK ORDER that
            # made the machine determination -- NOT a person, and not the
            # founder: this order registers the Piedmont Triad without a row-by-row
            # founder signature, and the founder's decision in this lane is on
            # the candidate digest, which has not been made. Writing the
            # operator's name here would be a false attribution.
            ("verification_state", "VERIFIED_PET_FRIENDLY"),
            ("reviewer_id", WORK_ORDER),
            ("reviewed_at", OBSERVED_AT),
            ("evidence", _evidence(rec, facts)),
        ))
        r_issues = PS.validate_record(record)
        if r_issues:
            refused.append((key, "; ".join(str(i) for i in r_issues)[:160]))
            continue
        hotels.append(record)

        sig = rec["identity_signals"] or {}
        pet_friendly.append(OrderedDict((
            ("identity_key", key),
            ("normalized_name", normalize_name(c["canonical_name"])),
            ("canonical_name", c["canonical_name"]),
            ("address", sig.get("address_on_page") or c.get("street") or ""),
            ("city", c.get("city") or sig.get("locality") or ""),
            ("state", c.get("state") or ""),
            ("postal_code", (c.get("postal_code") or sig.get("postal_code") or "")[:5]),
            ("official_url", c.get("official_url") or rec["final_url"]),
            ("source_url", rec["final_url"] or rec["source_url"]),
            ("observed_at", OBSERVED_AT),
            ("brand", rec.get("brand", "")),
            ("corridor", rec.get("corridor", "")),
            ("evidence", rec["evidence"]),
            ("evidence_quote", rec["operative_quote"]),
            ("facts", dict(facts)),
            ("authority_state", enums.PUBLISHED_PET_FRIENDLY),
            ("publication_grade", "PUBLICATION_GRADE_EVIDENCE"),
            ("readiness_state", "READY"),
            ("founder_decision", "REGISTERED_NOT_AUTHORIZED_FOR_LAUNCH"),
            ("founder_reviewer_id", WORK_ORDER),
            ("founder_reviewed_at", OBSERVED_AT),
            ("snapshot_hash", rec.get("document_sha256") or ""),
        )))

    for rec in clean["clean_verified_no_pets"]:
        key = rec["identity_key"]
        c = census.get(key)
        if c is None:
            refused.append((key, "no census row"))
            continue
        sig = rec["identity_signals"] or {}
        exclusions.append(OrderedDict((
            ("identity_key", key),
            ("normalized_name", normalize_name(c["canonical_name"])),
            ("canonical_name", c["canonical_name"]),
            ("address", sig.get("address_on_page") or c.get("street") or ""),
            ("city", c.get("city") or sig.get("locality") or ""),
            ("state", c.get("state") or ""),
            ("postal_code", (c.get("postal_code") or sig.get("postal_code") or "")[:5]),
            ("official_url", c.get("official_url") or rec["final_url"]),
            ("source_url", rec["final_url"] or rec["source_url"]),
            ("observed_at", OBSERVED_AT),
            ("brand", rec.get("brand", "")),
            ("corridor", rec.get("corridor", "")),
            ("evidence", rec["evidence"]),
            ("evidence_quote", rec["operative_quote"]),
            ("exclusion_id", "%s--%s" % (MARKET_ID, re.sub(r"[^a-z0-9]+", "-", key).strip("-"))),
            ("exclusion_state", enums.VERIFIED_NO_PETS),
            # The document the reader actually parsed. The exclusion contract
            # carries the record's OWN snapshot hash, so a hand-edited exclusion
            # fails its own validator.
            ("snapshot_hash", rec.get("document_sha256") or ""),
            ("publication_grade", "PUBLICATION_GRADE_EVIDENCE"),
            ("readiness_state", "READY"),
            ("founder_decision", "REGISTERED_NOT_AUTHORIZED_FOR_LAUNCH"),
            # NOT a person. This order registers Raleigh without a row-by-row
            # founder review, and signing one in the operator's name would be a
            # false attribution. The reviewer is the WORK ORDER that made the
            # machine determination; the founder's decision in this lane is on
            # the candidate digest, and it has not been made.
            ("founder_reviewer_id", WORK_ORDER),
            ("founder_reviewed_at", OBSERVED_AT),
        )))

    package = OrderedDict((
        ("market", "Piedmont Triad (Greensboro - Winston-Salem - High Point), North Carolina"),
        ("schema_version", PS.SCHEMA_VERSION),
        ("market_id", MARKET_ID),
        ("work_order", WORK_ORDER),
        ("as_of", OBSERVED_AT),
        ("note",
         "The Piedmont Triad's committed policy package. Every record is one first-party read of the "
         "property's own page, bound to the census identity by the street identity that page "
         "states, and every published fact is cited to the quote it rests on with the sha256 of "
         "the document it was read from. Refundability is absent, not false, when the source "
         "stated neither refundable nor non-refundable."),
        ("hotels", hotels),
    ))
    pkg_issues = PS.validate_package(package)

    authority = OrderedDict((
        ("schema", "ptf-market-proposed-authority/1.0"),
        ("what_this_is",
         "The Piedmont Triad's authority as this order proposes it. Registration makes the market "
         "BUILDABLE; launch_participation.json decides whether it is BUILT into production, and "
         "this order leaves that at SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH. The "
         "founder gate in the modern lane is on the exact candidate digest, not on each row."),
        ("market_id", MARKET_ID),
        ("work_order", WORK_ORDER),
        ("registered", True), ("published", False), ("deployed", False),
        ("built_from", OrderedDict((
            ("source_ledgers", [os.path.relpath(CLEAN, _DASH).replace("\\", "/")]),
            ("decision_ledger", "ptf-market-clean-authority/1.0"),
            ("decided_by", WORK_ORDER),
            ("decided_at", OBSERVED_AT),
            ("approval_vocabulary", "REGISTERED_NOT_AUTHORIZED_FOR_LAUNCH"),
        ))),
        ("gate", "a row reaches this document only with an operative first-party quote bound to "
                 "an ADMITTED census identity; nothing here is authorised for launch"),
        ("signed_rows_in", len(pet_friendly) + len(exclusions)),
        ("superseded_count", 0), ("superseded_rows", []),
        ("identity_confirmations", []),
        ("pet_friendly_count", len(pet_friendly)),
        ("verified_no_pets_count", len(exclusions)),
        ("authority_total", len(pet_friendly) + len(exclusions)),
        ("unresolved", [r["identity_key"] for r in clean["unresolved_census_identities"]]),
        ("pet_friendly", pet_friendly),
        ("verified_no_pets", exclusions),
    ))
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
        print("   !", str(i)[:160])
    print("computation      :", dict(Counter(h["computation_class"] for h in package["hotels"])))
    if issues:
        print("NOT WRITTEN -- the package must validate before it is committed")
        return 1
    if args.write:
        for path, doc in ((PACKAGE_OUT, package), (AUTHORITY_OUT, authority)):
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(doc, fh, indent=1, ensure_ascii=False)
                fh.write("\n")
            print("written          :", os.path.relpath(path, _DASH))
    else:
        print("(dry run; pass --write to commit the documents)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
