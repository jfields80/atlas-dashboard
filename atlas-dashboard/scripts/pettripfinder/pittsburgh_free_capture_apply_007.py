# -*- coding: utf-8 -*-
"""PTF-PITTSBURGH-IDENTITY-CLOSE-007 Phases 2/4/6 -- apply the free-capture results.

    python -m scripts.pettripfinder.pittsburgh_free_capture_apply_007
    python -m scripts.pettripfinder.pittsburgh_free_capture_apply_007 --write

Three attended-Chrome captures and one IHG directory read, all at $0.00.

PUBLISHED
---------
Hyatt Regency Pittsburgh International Airport (pitap) states "We welcome your
traveling pet companions" and "Please inform the hotel at least three days in
advance of your arrival if a pet is staying with you." That is prose plus a
concrete requirement, not the amenity chip PTF-POLICY-PARSER-SEMANTIC-
HARDENING-017 warns about. No fee, weight or count appears anywhere on the
surface, so none is published.

TWO POISONED ROUTES RETIRED
----------------------------
A route is a standing instruction to go and read a page. Both of these now point
somewhere that would teach a later run something false, so the URL is cleared
and the reason recorded:

  sunnyledge boutique hotel   https://sunnyledge.com now redirects to a domain
                              reseller's "for sale" page.
  holiday inn express         .../cranberry/fklpa/ is Holiday Inn Express &
  pittsburgh cranberry        Suites FRANKLIN - OIL CITY, 225 Singh Drive,
  township                    Cranberry PA 16319 in VENANGO county -- about
                              seventy miles from the Butler-county Cranberry
                              Township (16066) the census row means.

Neither retirement asserts the property closed. Closure is not inferred from a
lapsed domain or from absence in a directory; both rows keep their identity
question and stay unresolved with a next action.

WHAT THE IHG DIRECTORY ACTUALLY PROVED
----------------------------------------
IHG's own Cranberry Township page, sorted by distance from downtown Cranberry
Township, lists 21 properties. It includes Candlewood Suites at 20036 Route 19,
Cranberry Township 16066 -- so the directory does cover that ZIP -- and contains
NO Holiday Inn Express in 16066; the nearest are Monaca (10.6 mi) and Butler
(15.1 mi). fklpa does not appear on it at all. That is strong evidence there is
no HIE in Cranberry Township, and it is recorded as evidence rather than
converted into a closure ruling.

POLICY_NOT_FOUND, RECORDED SO IT CAN BE FALSIFIED
---------------------------------------------------
Mansions on Fifth: three first-party surfaces checked, none containing the word
"pet", each with its URL and digest written down. PTF-MILWAUKEE-CLOSURE-
ASSESSMENT-031 found POLICY_NOT_FOUND unfalsifiable precisely because nobody
recorded where they had looked.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import market_authority as MA                  # noqa: E402
from scripts.pettripfinder import policy_migration as PM                  # noqa: E402
from scripts.pettripfinder.contracts import census as CENSUS_CONTRACT     # noqa: E402
from scripts.pettripfinder.contracts import enums                         # noqa: E402
from scripts.pettripfinder.contracts.fee_computation import classify      # noqa: E402
from scripts.pettripfinder.pittsburgh_hardened_sync_004 import (          # noqa: E402
    CENSUS, MARKET_ID, PACKAGE, REPORTS, _load, _write)

WORK_ORDER = "PTF-PITTSBURGH-IDENTITY-CLOSE-007"
AS_OF = "2026-08-31"
OPERATOR = "jfields80"
CAPTURES = (_REPO_ROOT / "data" / "acquisition"
            / "pittsburgh_pa_free_capture_007" / "captures.json")
APPLICATION = REPORTS / "pittsburgh_identity_close_007_free_capture.json"
ROUTE_LEDGER = REPORTS / "pittsburgh_identity_close_007_poisoned_routes.json"

PUBLISH_KEY = "hyatt regency pittsburgh international airport"
POISONED = OrderedDict((
    ("sunnyledge boutique hotel", OrderedDict((
        ("why", "The committed official_url https://sunnyledge.com now "
                "redirects to a domain reseller's sale page titled "
                "'SunnyLedge.com is for sale | HugeDomains'. The route would "
                "teach a later run that a marketing page is this hotel."),
        ("evidence_sha256",
         "sha256:8bfdad746643789831113db0dbd88d52645e4fbb083bdf86b8c33363aaa54b0e"),
        ("next_action",
         "Recover a current first-party route for Sunnyledge before any "
         "capture. The domain lapsing is NOT evidence the property closed; "
         "confirm the identity before ruling on the category."),
    ))),
    ("holiday inn express pittsburgh cranberry township", OrderedDict((
        ("why", "The committed official_url ends /cranberry/fklpa/, which is "
                "Holiday Inn Express & Suites Franklin - Oil City at 225 Singh "
                "Drive, Cranberry PA 16319 in Venango county -- roughly seventy "
                "miles from the Butler-county Cranberry Township (16066) this "
                "census row means. Pennsylvania has two Cranberrys and the "
                "route bound the wrong one."),
        ("evidence_sha256",
         "sha256:2a9b27f04ae399c2b7492e571641461be9e20bd0a962b1ce3e3b76bdd260efd1"),
        ("next_action",
         "IHG's own Cranberry Township directory lists 21 properties including "
         "Candlewood Suites in 16066, and contains no Holiday Inn Express in "
         "that ZIP. Settle whether this identity exists at all before "
         "re-routing it; do not infer closure from the directory alone."),
    ))),
))


class ApplyError(RuntimeError):
    pass


def build():
    captures = {c["identity_key"]: c for c in _load(CAPTURES)["captures"]}
    census = _load(CENSUS)
    rows = {h["identity_key"]: h for h in census["hotels"]}
    package = _load(PACKAGE)
    published = {h["identity_key"] for h in package["hotels"]}
    excluded = {e["normalized_name"]
                for e in MA.load_market_exclusions_document(MARKET_ID)["exclusions"]}

    # -- publish the one clean pet-friendly row ------------------------------ #
    cap = captures[PUBLISH_KEY]
    if PUBLISH_KEY in published or PUBLISH_KEY in excluded:
        raise ApplyError("%s already holds authority" % PUBLISH_KEY)
    row = rows[PUBLISH_KEY]
    for field in ("address", "city", "state", "postal_code"):
        if not str(row.get(field) or "").strip():
            raise ApplyError("%s: publishing needs %s" % (PUBLISH_KEY, field))
    entries: List[Dict] = []
    for field, quote in cap["quotes"].items():
        entry = OrderedDict((
            ("field", field), ("quote", quote),
            ("source_url", cap["source_url"]),
            ("artifact_class", "PUBLICATION_GRADE_EVIDENCE"),
            ("artifact_sha256", cap["artifact_sha256"]),
            ("artifact_kind", "rendered_html"),
            ("captured_at", AS_OF),
            ("capture_method", "browser_assisted"),
            ("source_grade", "PT1_FIRST_PARTY"),
        ))
        entry["evidence_ref"] = PM.evidence_ref_for(entry)
        entries.append(entry)
    facts = OrderedDict((
        ("pets_allowed", True),
        ("reservation_requirement", cap["quotes"]["reservation_requirement"]),
    ))
    record = OrderedDict((
        ("key", PUBLISH_KEY), ("name", row["canonical_name"]),
        ("facts", facts), ("evidence", entries),
        ("evidence_count", len(entries)),
        ("evidence_quote", " [.] ".join(e["quote"] for e in entries)),
        ("source_url", cap["source_url"]),
        ("source_type", "EXACT_ENTITY_DOMAIN"),
        ("verification_state", "VERIFIED_PET_FRIENDLY"),
        ("verification_date", AS_OF), ("verified_at", AS_OF),
        ("worker_model_id", ""), ("worker_prompt_version", ""),
        ("worker_result_hash", cap["artifact_sha256"].split(":")[-1]),
        ("worker_routing_version", ""), ("worker_validator_version", ""),
        ("schema_version", enums.POLICY_SCHEMA_VERSION),
        ("identity_key", PUBLISH_KEY), ("market_id", MARKET_ID),
    ))
    record["computation_class"] = classify(facts).computation_class
    record["approval"] = OrderedDict((
        ("decision", "APPROVED_AFTER_CURRENT_REVIEW"),
        ("operator", OPERATOR), ("approval_date", AS_OF),
        ("caveats", [
            "FREE ATTENDED CAPTURE under %s: provider calls 0, spend $0.00. "
            "The property code %s is present on the captured page."
            % (WORK_ORDER, cap["property_code"]),
            "The page states the permission as PROSE plus a concrete "
            "requirement, not merely a 'Pet Friendly' amenity chip. No fee, "
            "weight limit or pet count appears anywhere on the surface, so none "
            "is published -- source silence is absence.",
            "Digest taken over the rendered outerHTML in the SAME JavaScript "
            "call as both quotes; raw bytes are not retained because the live "
            "page mutates between calls.",
        ]),
        ("record_hash", PM.record_hash(
            {k: v for k, v in record.items() if k != "approval"})),
        ("evidence_hash", PM.evidence_hash(entries)),
    ))
    package["hotels"] = list(package["hotels"]) + [record]
    problems = PM.validate_migrated(package)
    if problems:
        raise ApplyError("the package does not validate: %s" % problems[:6])

    # -- retire the two poisoned routes -------------------------------------- #
    fixed = json.loads(json.dumps(census))
    retired = []
    for key, detail in POISONED.items():
        target = next((h for h in fixed["hotels"] if h["identity_key"] == key), None)
        if target is None:
            raise ApplyError("%s is not a registered identity" % key)
        current = str(target.get("official_url") or "").strip()
        if not current:
            continue
        retired.append(OrderedDict((
            ("identity_key", key),
            ("canonical_name", target.get("canonical_name")),
            ("retired_official_url", current),
            ("why", detail["why"]),
            ("evidence_sha256", detail["evidence_sha256"]),
            ("next_action", detail["next_action"]),
            ("retired_at", AS_OF), ("retired_by", WORK_ORDER),
            ("asserts_closure", False),
        )))
        target["official_url"] = ""
        target["url_shape"] = ""
    if fixed.get("count") != census.get("count"):
        raise ApplyError("the census count moved")
    issues = CENSUS_CONTRACT.validate(fixed, market_states=["PA"])
    if issues:
        raise ApplyError("the census does not validate: %s" % list(issues)[:5])

    report = OrderedDict((
        ("schema", "ptf-market-free-capture/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET_ID), ("as_of", AS_OF),
        ("provider_calls", 0), ("usd_spent", 0.0),
        ("rows_attempted", 3),
        ("published_pet_friendly", 1),
        ("verified_no_pets", 0),
        ("policy_not_found", 1),
        ("routes_retired", len(retired)),
        ("policy_not_found_detail", captures["mansions on fifth"]),
        ("published", OrderedDict((
            ("identity_key", PUBLISH_KEY),
            ("artifact_sha256", cap["artifact_sha256"]),
            ("facts", facts)))),
        ("retired_routes", retired),
    ))
    return fixed, package, retired, report


def run(write: bool) -> int:
    census, package, retired, report = build()
    print("provider calls      : %d" % report["provider_calls"])
    print("spend               : $%.2f" % report["usd_spent"])
    print("rows attempted      : %d" % report["rows_attempted"])
    print("  published PF      : %d (%s)" % (report["published_pet_friendly"], PUBLISH_KEY))
    print("  POLICY_NOT_FOUND  : %d (mansions on fifth, 3 surfaces recorded)" % report["policy_not_found"])
    print("poisoned routes retired: %d" % len(retired))
    for r in retired:
        print("   %-52s %s" % (r["identity_key"][:51], r["retired_official_url"][:52]))
    print("package after       : %d" % len(package["hotels"]))
    print("census              : %d (unchanged)" % census["count"])
    if not write:
        print("(check only -- pass --write)")
        return 0
    _write(CENSUS, census)
    print("WROTE %s" % CENSUS.name)
    _write(PACKAGE, package)
    print("WROTE %s (%d records)" % (PACKAGE.name, len(package["hotels"])))
    _write(ROUTE_LEDGER, OrderedDict((
        ("schema", "ptf-market-route-retirement-ledger/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET_ID), ("as_of", AS_OF),
        ("why", "Each route below now points at something that would teach a "
                "later run something false. The URL is cleared from the census "
                "row and preserved here."),
        ("asserts_no_closure",
         "No row here is ruled closed. A lapsed domain and an absence from a "
         "brand directory are both evidence about a ROUTE, not about whether a "
         "building operates."),
        ("count", len(retired)), ("retired_routes", retired))))
    print("WROTE %s" % ROUTE_LEDGER.name)
    _write(APPLICATION, report)
    print("WROTE %s" % APPLICATION.name)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        return run(args.write)
    except ApplyError as exc:
        print("REFUSED: %s" % exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
