"""Project a market's signed authority into a schema-1.2 policy package.

    python scripts/pettripfinder/market_policy_package_cli.py \
      --authority <proposed_authority.json> \
      --out launch_packages/pettripfinder/hotel_policy_facts_<market_id>.json

WHY THIS EXISTS
---------------
``site_data.verified_public_hotels`` reads a committed policy package and treats
it as THE authority: a seed row absent from it is not published, and a package
record with no seed row FAILS CLOSED. Every release contract points at one by
path, sha256, schema version and record count. Five markets have one; a market
built on the generic path had no way to produce it.

THE PROJECTION IS PROVED, NOT TRUSTED
--------------------------------------
Reshaping facts is where a wrong number gets published. So every record this
module builds is run through ``contracts.policy_schema.validate_facts`` -- the
repository's own 1.2 validator -- and the run REFUSES TO WRITE if any record
raises a single issue. A projection that cannot pass the schema it claims to
target is not a projection, it is a guess.

WHAT THE RESHAPING MAY AND MAY NOT DO
--------------------------------------
It may only re-express what the reader already extracted. Three rules, each one
a thing this corpus learned the expensive way:

* ``species_allowed`` is an AFFIRMATIVE-MENTION LIST, not an allow-list
  (PTF-POLICY-PARSER-SEMANTIC-HARDENING-017 retracted the opposite reading).
  ``["dog"]`` becomes ``{"dogs": "accepted"}`` and says NOTHING about cats. An
  absent species stays absent, because every consumer renders that as "Not
  stated"; writing ``{"cats": "prohibited"}`` there would invent a refusal.
* ``weight_limit`` keeps whatever the source stated and nothing else. The
  operator and the scope are emitted ONLY when the reader emitted them --
  defaulting "up to" to ``lte`` is a guest-visible error in both directions, and
  the reader's own non_inferences say so.
* A withheld field is not carried across as a value. It stays withheld, and the
  package's record simply lacks it, which is what renders as "Not stated".

Nothing here publishes. The package carries ``published: false``; flipping that
is a separate act by a publication work order, exactly as PTF-MILWAUKEE-
PUBLICATION-042 did for its market.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.contracts import enums  # noqa: E402
from scripts.pettripfinder.contracts import policy_schema as PS  # noqa: E402

SCHEMA_VERSION = "1.2"

#: reader species token -> package species key. Only these two are recognised;
#: an unknown token is reported rather than guessed at.
_SPECIES_KEY = {"dog": "dogs", "cat": "cats"}


class PolicyPackageError(RuntimeError):
    pass


def project_facts(source: Mapping) -> Tuple[Dict, List[str]]:
    """``(facts, notes)`` -- the 1.2 fact block for one authority row."""
    facts: Dict = OrderedDict()
    notes: List[str] = []

    if "pets_allowed" in source:
        facts["pets_allowed"] = bool(source["pets_allowed"])

    species: Dict[str, str] = OrderedDict()
    for token in source.get("species_allowed") or ():
        key = _SPECIES_KEY.get(str(token).lower())
        if key is None:
            notes.append("unrecognised species token %r; not projected" % token)
            continue
        species[key] = enums.SPECIES_ACCEPTED
    # An explicit refusal is a fact and is carried; an ABSENT species is not.
    if source.get("cats_allowed") is False:
        species["cats"] = enums.SPECIES_PROHIBITED
    if species:
        facts["species"] = OrderedDict(sorted(species.items()))

    weight = source.get("weight_limit")
    if isinstance(weight, Mapping) and weight.get("value") is not None:
        node = OrderedDict((("value", weight["value"]),
                            ("unit", weight.get("unit", "lb"))))
        # operator and scope ONLY if the source stated them.
        for optional in ("operator", "scope"):
            if weight.get(optional):
                node[optional] = weight[optional]
        facts["weight_limit"] = node

    if source.get("fee_tiers"):
        facts["fee_tiers"] = [dict(t) for t in source["fee_tiers"]]
    elif source.get("pet_fee") is not None:
        fee = OrderedDict((("amount_cents", source["pet_fee"]),
                           ("currency", source.get("fee_currency", "USD"))))
        for key, target in (("fee_basis", "basis"), ("fee_scope", "scope")):
            if source.get(key):
                fee[target] = source[key]
        facts["pet_fee"] = fee

    if source.get("fee_cap") is not None:
        cap = source["fee_cap"]
        if isinstance(cap, Mapping):
            # The reader spells the amount ``amount_minor``; schema 1.2 spells
            # it ``amount_cents``. Same integer, same unit -- a rename, not a
            # conversion. ``qualifier_stated`` is REQUIRED by the schema and is
            # deliberately NOT filled in here: it is a claim about whether the
            # source named a pet count or an ordinal, and _check_cap exists
            # because a cap whose quote named one and whose structure lost it
            # published a ceiling the hotel never quoted.
            node = OrderedDict()
            if cap.get("amount_minor") is not None:
                node["amount_cents"] = cap["amount_minor"]
            elif cap.get("amount_cents") is not None:
                node["amount_cents"] = cap["amount_cents"]
            node["currency"] = cap.get("currency", "USD")
            for optional in ("basis", "scope"):
                if cap.get(optional):
                    node[optional] = cap[optional]
            if cap.get("qualifier_stated") is not None:
                node["qualifier_stated"] = bool(cap["qualifier_stated"])
            facts["fee_cap"] = node
        else:
            facts["fee_cap"] = OrderedDict(
                (("amount_cents", cap),
                 ("currency", source.get("fee_currency", "USD"))))
    if source.get("pet_deposit") is not None:
        facts["pet_deposit"] = OrderedDict(
            (("amount_cents", source["pet_deposit"]),
             ("currency", source.get("fee_currency", "USD"))))

    if source.get("pet_count_limit") is not None:
        facts["pet_count_limit"] = source["pet_count_limit"]
    if source.get("pet_count_scope"):
        facts["pet_count_scope"] = source["pet_count_scope"]
    if source.get("service_animal_exception"):
        facts["service_animal_exception"] = source["service_animal_exception"]

    return (facts, notes)


def build(authority: Mapping, *, market_name: str) -> Dict:
    market_id = authority.get("market_id", "")
    hotels: List[Dict] = []
    refusals: List[Dict] = []

    for row in authority.get("pet_friendly") or ():
        facts, notes = project_facts(row.get("facts") or {})
        issues = PS.validate_facts(facts)
        if issues:
            refusals.append(OrderedDict((
                ("identity_key", row["normalized_name"]),
                ("issues", [("%s: %s -- %s" % (i.path, i.code, i.detail))
                            for i in issues]))))
            continue
        record = OrderedDict((
            ("key", row["normalized_name"]),
            ("name", row["canonical_name"]),
            ("facts", facts),
            ("evidence", [OrderedDict((
                ("field", (item.get("field_refs") or [""])[0]),
                ("quote", item.get("quote", "")),
                ("source_url", row.get("source_url", "")),
                ("evidence_ref", item.get("evidence_ref", "")),
                ("artifact_class", "PUBLICATION_GRADE_EVIDENCE"),
                ("artifact_sha256", "sha256:%s" % row.get("snapshot_hash", "")),
                ("artifact_kind", "rendered_html"),
                ("captured_at", row.get("observed_at", "")),
                ("capture_method", row.get("capture_method", "")),
                ("source_grade", "PT1_FIRST_PARTY"),
            )) for item in (row.get("evidence") or ())]),
            ("withheld_fields", row.get("withheld_fields") or {}),
            ("non_inferences", list(row.get("non_inferences") or ())),
            ("founder_decision", row.get("founder_decision", "")),
            ("founder_reviewer_id", row.get("founder_reviewer_id", "")),
            ("founder_reviewed_at", row.get("founder_reviewed_at", "")),
        ))
        if notes:
            record["projection_notes"] = notes
        hotels.append(record)

    hotels.sort(key=lambda r: r["key"])
    return OrderedDict((
        ("market", market_name),
        ("schema_version", SCHEMA_VERSION),
        ("market_id", market_id),
        ("what_this_is",
         "The publishable pet-policy facts for this market, projected from its "
         "founder-signed authority. Every record's fact block passed "
         "contracts.policy_schema.validate_facts before this file was written."),
        ("published", False),
        ("publication_note",
         "published:false -- this package is pre-publication. Flipping the flag "
         "is a separate act by a publication work order."),
        ("derived_from", OrderedDict((
            ("authority", authority.get("schema", "")),
            ("source_ledgers", (authority.get("built_from") or {}).get(
                "source_ledgers", [])),
            ("decided_by", (authority.get("built_from") or {}).get(
                "decided_by", "")),
        ))),
        ("count", len(hotels)),
        ("refusals", refusals),
        ("hotels", hotels),
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--authority", required=True)
    parser.add_argument("--market-name", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--expect-count", type=int, default=None)
    args = parser.parse_args(argv)

    authority = json.loads(Path(args.authority).read_text(encoding="utf-8"))
    document = build(authority, market_name=args.market_name)

    if document["refusals"]:
        raise PolicyPackageError(
            "%d record(s) failed schema 1.2 validation and the package was NOT "
            "written: %s" % (len(document["refusals"]),
                             json.dumps(document["refusals"][:3], indent=1)))
    if args.expect_count is not None and document["count"] != args.expect_count:
        raise PolicyPackageError(
            "expected %d records and projected %d"
            % (args.expect_count, document["count"]))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(document, indent=1, ensure_ascii=False) + "\n"
    out.write_text(payload, encoding="utf-8", newline="\n")
    print("records projected : %d" % document["count"])
    print("schema validated  : every record, 0 issues")
    print("published flag    : %s" % document["published"])
    print("sha256            : %s" % hashlib.sha256(
        out.read_bytes()).hexdigest())
    print("written           : %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
