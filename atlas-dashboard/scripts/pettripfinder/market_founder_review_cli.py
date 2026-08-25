"""PTF-ST-LOUIS-MARKET-001 -- the founder-review package, derived not asserted.

Every publication-grade candidate, with everything a founder needs to decide and
nothing that would decide for them:

    which property        identity key, canonical name, address, corridor
    which page            source URL, final URL, snapshot hash
    what it says          the parsed facts, exactly as the reader produced them
    what backs it         every evidence quote, with the field it supports
    what is NOT claimed   withheld fields and the reason for each
    lineage               provider, reader, locator walk, block hash
    proposed verdict      a RECOMMENDATION, spelled so it cannot be mistaken
                          for an approval
    hash material         the semantic-approval/1.0 projection and its hash

THE RECOMMENDATION IS NOT AN APPROVAL
--------------------------------------
Every row leaves here as ``MACHINE_REVIEWED_PENDING_OPERATOR`` -- a value the
approval vocabulary already defines as "a machine's opinion awaiting a person.
Not publishable." No code path in this module can write
``APPROVED_AFTER_CURRENT_REVIEW``, and no reviewer id is invented: the decision
fields are present and EMPTY, for a human to fill.

WHY THE HASH TRAVELS WITH THE PACKAGE
--------------------------------------
``semantic-approval/1.0`` splits the approved MEANING from the provenance that
happens to surround it, so an approval survives a re-run and does not survive
a changed fact. Recording the projection and its hash at review time is what
lets a later apply step prove the founder approved THIS record -- and refuse if
a fact moved underneath it.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Sequence

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import approval_binding as AB
from scripts.pettripfinder import census_partition_builder as CPB
from scripts.pettripfinder.contracts import enums

PACKAGE_DIR = _REPO_ROOT / "launch_packages" / "pettripfinder"
CENSUS_DIR = PACKAGE_DIR / "identity_census"

SCHEMA = "ptf-founder-review-package/1.0"
PUBLICATION_GRADE_CONFIRMED = "PUBLICATION_GRADE_CONFIRMED"

#: The only review status this module may write.
PENDING = enums.MACHINE_REVIEWED_PENDING_OPERATOR

RECOMMEND_PET_FRIENDLY = "RECOMMEND_AUTHORITY_PET_FRIENDLY"
RECOMMEND_VERIFIED_NO_PETS = "RECOMMEND_AUTHORITY_VERIFIED_NO_PETS"
RECOMMEND_HOLD = "RECOMMEND_HOLD_EVIDENCE_INCOMPLETE"


def recommendation(extraction: Mapping, withheld: Mapping) -> str:
    pets = extraction.get("pets_allowed")
    if pets is True:
        return RECOMMEND_PET_FRIENDLY
    if pets is False:
        return RECOMMEND_VERIFIED_NO_PETS
    return RECOMMEND_HOLD


def candidate_record(observation_record: Mapping, census_row: Mapping) -> Dict:
    observation = observation_record["observation"]
    extraction = observation.get("extraction") or {}
    withheld = observation_record.get("withheld_fields") or {}
    provenance = observation_record.get("reader_provenance") or {}

    # The record whose MEANING a founder is being asked to approve. Field names
    # are the semantic-approval/1.0 ones so the projection is exact.
    approvable = OrderedDict((
        ("identity_key", observation_record["identity_key"]),
        ("canonical_name", observation_record["canonical_name"]),
        ("market_id", census_row["market_id"]),
        ("brand", observation_record.get("brand", "")),
        ("policy_schema_version", enums.POLICY_SCHEMA_VERSION),
        ("proposed_facts", dict(extraction)),
        ("withheld_fields", dict(withheld)),
        ("service_animal_statement", extraction.get("service_animal_statement", "")),
        ("is_refusal", extraction.get("pets_allowed") is False),
        ("evidence", [dict(e) for e in (observation.get("evidence") or ())]),
        ("publication_grade",
         (observation_record.get("publication_grade") or {}).get("verdict", "")),
        ("identity_check", dict(observation.get("identity_check") or {})),
        ("review_status", PENDING),
        ("frozen_semantics_violations", []),
        # Nested exactly where semantic-approval/1.0 looks for them. WHICH page
        # and WHICH block are part of the approved meaning; how the bytes were
        # obtained is not.
        ("provenance", OrderedDict((
            ("source_url", observation.get("source_url", "")),
            ("final_url", observation.get("source_url", "")),
            ("snapshot_hash", observation.get("snapshot_hash", "")),
            ("authority_tier", observation.get("authority_tier", "")),
            ("source_type", observation.get("source_type", "")),
            ("retrieved_at", observation.get("retrieved_at", "")),
            ("capture_method", observation.get("capture_method", "")),
            ("provider", observation_record.get("provider", "")),
            ("reader", observation_record.get("reader", "")),
            ("raw_pointer", observation.get("raw_pointer", "")),
            ("obs_id", observation.get("obs_id", "")),
        ))),
        ("rederivation", OrderedDict((
            ("evidence_block_sha256", provenance.get("block_sha256", "")),
        ))),
    ))

    return OrderedDict((
        ("identity_key", observation_record["identity_key"]),
        ("canonical_name", observation_record["canonical_name"]),
        ("address", census_row.get("address", "")),
        ("city", census_row.get("city", "")),
        ("state", census_row.get("state", "")),
        ("postal_code", census_row.get("postal_code", "")),
        ("corridor", census_row.get("corridor", "")),
        ("brand", observation_record.get("brand", "")),
        ("source_url", observation.get("source_url", "")),
        ("snapshot_hash", observation.get("snapshot_hash", "")),
        ("proposed_facts", dict(extraction)),
        ("evidence", [dict(e) for e in (observation.get("evidence") or ())]),
        ("withheld_fields", dict(withheld)),
        ("non_inferences", list(observation_record.get("non_inferences") or ())),
        ("flags", [dict(f) for f in (observation.get("flags") or ())]),
        ("membrane", observation_record.get("membrane") or {}),
        ("readiness", observation_record.get("readiness") or {}),
        ("publication_grade", observation_record.get("publication_grade") or {}),
        ("lineage", OrderedDict((
            ("provider", observation_record.get("provider", "")),
            ("provider_product", "direct HTTPS GET (first-party, no vendor)"),
            ("reader", observation_record.get("reader", "")),
            ("reader_module", provenance.get("module", "")),
            ("locator_contract", provenance.get("locator_contract", "")),
            ("locator_walk", provenance.get("locator_walk", "")),
            ("locator_strategy", provenance.get("locator_strategy", "")),
            ("block_sha256", provenance.get("block_sha256", "")),
            ("document_sha256", provenance.get("document_sha256", "")),
            ("raw_pointer", observation.get("raw_pointer", "")),
        ))),
        ("recommendation", recommendation(extraction, withheld)),
        ("recommendation_is_not_an_approval",
         "A recommendation is a machine reading. Only a founder decision "
         "creates authority; this row is MACHINE_REVIEWED_PENDING_OPERATOR."),
        ("review_status", PENDING),
        ("founder_decision", ""),
        ("founder_reviewer_id", ""),
        ("founder_reviewed_at", ""),
        ("founder_note", ""),
        ("semantic_approval", OrderedDict((
            ("binding_contract", AB.BINDING_CONTRACT_VERSION),
            ("semantic_hash", AB.semantic_hash(approvable)),
            ("projection", AB.semantic_projection(approvable)),
            ("unclassified_fields", AB.unclassified_fields(approvable)),
        ))),
    ))


def build(market_id: str, census: Mapping, observations: Mapping, *,
          work_order: str, as_of: str) -> Dict:
    rows = {r["identity_key"]: r for r in census["hotels"]}
    candidates: List[Dict] = []
    for record in observations.get("records") or ():
        verdict = (record.get("publication_grade") or {}).get("verdict")
        if verdict != PUBLICATION_GRADE_CONFIRMED:
            continue
        census_row = rows.get(record["identity_key"])
        if census_row is None:
            raise SystemExit("ERROR: observation for %r has no census row"
                             % record["identity_key"])
        candidates.append(candidate_record(record, census_row))
    candidates.sort(key=lambda c: c["identity_key"])

    statuses = Counter(c["review_status"] for c in candidates)
    if set(statuses) - {PENDING}:
        raise SystemExit("ERROR: a candidate left this builder with a review "
                         "status other than %s" % PENDING)

    return OrderedDict((
        ("schema", SCHEMA),
        ("what_this_is",
         "Every publication-grade St. Louis candidate, packaged for a founder "
         "decision. Nothing here is an approval; every row is "
         "MACHINE_REVIEWED_PENDING_OPERATOR with empty decision fields."),
        ("market_id", market_id),
        ("work_order", work_order),
        ("as_of", as_of),
        ("derived_from", observations.get("derived_from", "")),
        ("approval_vocabulary", "founder-approval-vocabulary/1.0"),
        ("binding_contract", AB.BINDING_CONTRACT_VERSION),
        ("count", len(candidates)),
        ("recommendation_counts",
         OrderedDict(sorted(Counter(c["recommendation"] for c in candidates).items()))),
        ("review_status_counts", OrderedDict(sorted(statuses.items()))),
        ("founder_instructions",
         "For each candidate set founder_decision to one of the "
         "founder-approval-vocabulary/1.0 values, founder_reviewer_id to your "
         "own identifier -- never an operator's on their behalf -- and "
         "founder_reviewed_at to the date you decided. A row you do not decide "
         "stays pending and publishes nothing."),
        ("candidates", candidates),
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market", required=True)
    parser.add_argument("--observations", required=True)
    parser.add_argument("--work-order", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--out", default="")
    parser.add_argument("--census", default="",
                        help="the census to read; default identity_census/"
                             "<market>.json. A re-census of a registered market "
                             "is built beside its live census, never over it")
    args = parser.parse_args(argv)

    census_path = Path(args.census) if args.census else CENSUS_DIR / ("%s.json" % args.market)
    census = json.loads(census_path.read_text(encoding="utf-8"))
    observations = json.loads(Path(args.observations).read_text(encoding="utf-8"))
    document = build(args.market, census, observations,
                     work_order=args.work_order, as_of=args.as_of)

    out = Path(args.out) if args.out else (
        PACKAGE_DIR / ("%s_founder_review_packet_001.json"
                       % args.market.replace("-", "_")))
    sha = CPB.write_json(out, document)
    print("candidates      : %d" % document["count"])
    print("recommendations : %s" % dict(document["recommendation_counts"]))
    print("review statuses : %s" % dict(document["review_status_counts"]))
    print("written         : %s (%s)" % (out, sha))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
