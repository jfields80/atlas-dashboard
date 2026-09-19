"""PTF-MIAMI-FL-HARDENED-SOURCE-READY-001 -- Phase 26: STAGE Miami's authority (shadow until registered).

Turns this order's clean-authority adjudication into the two documents a registered market is built from, and
validates both against the contracts that own them:

  1. the staged POLICY PACKAGE  markets/staging/miami-fl/launch_package/hotel_policy_facts_miami-fl.json
     -- schema-1.3 facts, every published fact cited to the quote it rests on.
  2. the PROPOSED AUTHORITY     markets/staging/miami-fl/miami_fl_proposed_authority_001.json
     -- the ptf-market-proposed-authority/1.0 shape `market_registration_cli` reads to write the shard.

SHADOW UNTIL REGISTERED. This order writes nothing at the package root and registers nothing: both documents
are staged inside the market's own zone.

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
from scripts.pettripfinder.site_data import normalize_name            # noqa: E402

WORK_ORDER = "PTF-MIAMI-FL-HARDENED-SOURCE-READY-001"
MARKET_ID = "miami-fl"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CLEAN = os.path.join(REPORTS, "miami_fl_clean_authority_001.json")
CENSUS = os.path.join(PKG, "identity_census_proposed", "miami-fl.json")
STAGING = os.path.join(PKG, "markets", "staging", "miami-fl")
PACKAGE_OUT = os.path.join(STAGING, "launch_package", "hotel_policy_facts_miami-fl.json")
AUTHORITY_OUT = os.path.join(STAGING, "miami_fl_proposed_authority_001.json")
OBSERVED_AT = "2026-09-19"
CAPTURED_AT = "2026-09-19T21:00:00+00:00"

LANE_GRADE = {
    "PROPERTY_PAGE_ATTENDED": ("attended_browser", "PT2_BRAND", "rendered_html"),
    "PROPERTY_PAGE_STATIC": ("direct_static_fetch", "PT2_BRAND", "rendered_html"),
    "FIRECRAWL": ("direct_static_fetch", "PT2_BRAND", "rendered_html"),
}
_WEIGHT_RX = re.compile(r"(\d+(?:\.\d+)?)\s*(?:lbs?|pounds)\b", re.I)


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
    if pf.get("pet_fee_cents") is not None:
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
                ("key", normalize_name(c["canonical_name"])), ("identity_key", key), ("name", c["canonical_name"]),
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
                ("identity_key", key), ("normalized_name", normalize_name(c["canonical_name"])),
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
                ("identity_key", key), ("normalized_name", normalize_name(c["canonical_name"])),
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
        ("market", "Miami, Florida"), ("schema_version", PS.SCHEMA_VERSION), ("market_id", MARKET_ID),
        ("work_order", WORK_ORDER), ("as_of", OBSERVED_AT),
        ("note", "Greater Miami's STAGED policy package (shadow until registered). Every record is one first-party "
                "read of the property's own page, and every published fact is cited to the quote it rests on. "
                "Refundability is absent, not false, when the source stated neither refundable nor non-refundable."),
        ("hotels", hotels),
    ])
    pkg_issues = PS.validate_package(package)

    authority = OrderedDict([
        ("schema", "ptf-market-proposed-authority/1.0"),
        ("what_this_is", "Greater Miami's authority as this order proposes it, STAGED and not registered. "
                        "Registration makes the market BUILDABLE; launch_participation.json decides whether it "
                        "is BUILT into production, and this order leaves that undone. The founder gate in the "
                        "modern lane is on the exact candidate digest, not on each row."),
        ("market_id", MARKET_ID), ("work_order", WORK_ORDER),
        ("registered", False), ("staged_shadow_until_registered", True), ("published", False), ("deployed", False),
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
    else:
        print("(dry run; pass --write to commit the documents)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
