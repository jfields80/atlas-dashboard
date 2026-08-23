"""Build a market's authority from signed rows only, WITHOUT registering it.

    python scripts/pettripfinder/market_proposed_authority_cli.py \
      --market st-louis-mo --decisions <founder_decisions.json> \
      --store <observation_store.json> --census <census.json> \
      --out <proposed_authority.json>

WHY "PROPOSED", AND WHY IT IS NOT A SHARD
-----------------------------------------
The real home for a market's authority is
``launch_packages/pettripfinder/markets/authority/<market_id>/``, and putting
St. Louis there now would be a registration in all but name. ``market_authority``
lists that directory to decide which markets exist and RAISES on a shard whose
market has no contract in ``markets/*.json`` -- so creating one would break the
global build, which the live deployment manifest pins.

PTF-047 established the coupling: registering market N+1 invalidates the current
production deployment record. So this artifact carries the authority in the SAME
SHAPE the shards use and lives outside the registry. Promoting it later is a move
plus a market contract, not a rewrite.

WHAT MAY BECOME AUTHORITY
-------------------------
Only a row the founder SIGNED. The decision ledger is the gate, not the review,
not the publication grade and not the readiness state -- each of those is a
statement the machine made, and none of them is an approval. A row missing from
the ledger is missing from the authority, and the run says so rather than
inferring it back in.

EVERY CITATION SURVIVES
-----------------------
An authority row carries its evidence quotes, its source URL, its snapshot hash,
its reader provenance, its withheld fields and its non-inferences. Withheld
fields are carried FORWARD, not dropped: "not stated" is a fact about the source
that a published page must be able to render, and a authority row that silently
loses it is how a blank becomes an implied zero.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.contracts import enums  # noqa: E402
from scripts.pettripfinder.contracts import founder_approval as FA  # noqa: E402

SCHEMA = "ptf-market-proposed-authority/1.0"


class ProposedAuthorityError(RuntimeError):
    pass


def _slug(market_id: str, identity_key: str) -> str:
    prefix = "".join(part[0] for part in market_id.split("-")[:3] if part)
    return "%s-%s" % (prefix, identity_key.replace(" ", "-"))


def build(decisions: Mapping, store: Mapping, census: Mapping) -> Dict:
    market_id = decisions.get("market_id", "")
    rows = {r["identity_key"]: r for r in store.get("records") or ()}
    hotels = {h["identity_key"]: h for h in census.get("hotels") or ()}

    pet_friendly: List[Dict] = []
    exclusions: List[Dict] = []
    unresolved: List[Dict] = []

    for signed in decisions.get("signed") or ():
        key = signed["identity_key"]
        record = rows.get(key)
        hotel = hotels.get(key, {})
        if record is None:
            unresolved.append(OrderedDict((
                ("identity_key", key),
                ("why", "signed but absent from the observation store"))))
            continue
        if not FA.is_publishable(signed["founder_decision"]):
            unresolved.append(OrderedDict((
                ("identity_key", key),
                ("why", "founder decision %r does not publish"
                        % signed["founder_decision"]))))
            continue
        # The signature is bound to a hash. If the record moved since, the
        # signature no longer covers it and this is not authority.
        current = (record.get("observation") or {}).get("snapshot_hash", "")
        if signed.get("bound_snapshot_hash") and current and \
                signed["bound_snapshot_hash"] != current:
            unresolved.append(OrderedDict((
                ("identity_key", key),
                ("why", "the record changed after it was signed: bound %s, now %s"
                        % (signed["bound_snapshot_hash"][:12], current[:12])))))
            continue

        observation = record.get("observation") or {}
        common = OrderedDict((
            ("canonical_name", signed.get("canonical_name", "")),
            ("normalized_name", key),
            ("address", hotel.get("address", "")),
            ("city", hotel.get("city", "")),
            ("state", hotel.get("state", "")),
            ("postal_code", hotel.get("postal_code", "")),
            ("corridor", signed.get("corridor", "")),
            ("official_url", observation.get("source_url", "")),
            ("source_url", observation.get("source_url", "")),
            ("source_type", observation.get("source_type", "")),
            ("authority_tier", observation.get("authority_tier", "")),
            ("snapshot_hash", observation.get("snapshot_hash", "")),
            ("observed_at", observation.get("observed_at", "")),
            ("capture_method", observation.get("capture_method", "")),
            ("evidence", list(observation.get("evidence") or ())),
            ("reader_provenance", record.get("reader_provenance", {})),
            ("withheld_fields", record.get("withheld_fields", {})),
            ("non_inferences", list(record.get("non_inferences") or ())),
            ("publication_grade", (record.get("publication_grade") or {}).get(
                "verdict", "")),
            ("membrane_verdict", (record.get("membrane") or {}).get("verdict", "")),
            ("readiness_state", (record.get("readiness") or {}).get("state", "")),
            ("founder_decision", signed["founder_decision"]),
            ("founder_reviewer_id", signed["founder_reviewer_id"]),
            ("founder_reviewed_at", signed["founder_reviewed_at"]),
            ("bound_semantic_hash", signed.get("bound_semantic_hash", "")),
        ))

        if signed["proposes_authority"] == enums.VERIFIED_NO_PETS:
            entry = OrderedDict(common)
            entry["exclusion_id"] = _slug(market_id, key)
            entry["exclusion_state"] = enums.VERIFIED_NO_PETS
            quotes = [e.get("quote", "") for e in observation.get("evidence") or ()]
            entry["evidence_quote"] = quotes[0] if quotes else ""
            exclusions.append(entry)
        else:
            entry = OrderedDict(common)
            entry["authority_state"] = enums.PUBLISHED_PET_FRIENDLY
            entry["facts"] = dict(observation.get("extraction") or {})
            pet_friendly.append(entry)

    pet_friendly.sort(key=lambda r: r["normalized_name"])
    exclusions.sort(key=lambda r: r["normalized_name"])

    return OrderedDict((
        ("schema", SCHEMA),
        ("what_this_is",
         "A market's authority, built ONLY from founder-signed rows and held "
         "outside the authority registry. Creating a shard directory under "
         "markets/authority/ would register the market, and a registered market "
         "invalidates the live deployment record (PTF-047). This carries the "
         "same shape so promotion is a move, not a rewrite."),
        ("market_id", market_id),
        ("work_order", decisions.get("work_order", "")),
        ("registered", False),
        ("published", False),
        ("deployed", False),
        ("built_from", OrderedDict((
            ("decision_ledger", decisions.get("schema", "")),
            ("decided_by", decisions.get("decided_by", "")),
            ("decided_at", decisions.get("decided_at", "")),
            ("approval_vocabulary", decisions.get("approval_vocabulary", "")),
        ))),
        ("gate", "only a row the founder SIGNED becomes authority; the review, "
                 "the publication grade and the readiness state are statements "
                 "the machine made and none of them is an approval"),
        ("signed_rows_in", len(decisions.get("signed") or ())),
        ("pet_friendly_count", len(pet_friendly)),
        ("verified_no_pets_count", len(exclusions)),
        ("authority_total", len(pet_friendly) + len(exclusions)),
        ("unresolved", unresolved),
        ("pet_friendly", pet_friendly),
        ("verified_no_pets", exclusions),
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--market", required=True)
    parser.add_argument("--decisions", required=True)
    parser.add_argument("--store", required=True)
    parser.add_argument("--census", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--expect-total", type=int, default=None)
    args = parser.parse_args(argv)

    decisions = json.loads(Path(args.decisions).read_text(encoding="utf-8"))
    store = json.loads(Path(args.store).read_text(encoding="utf-8"))
    census = json.loads(Path(args.census).read_text(encoding="utf-8"))
    document = build(decisions, store, census)

    if document["unresolved"]:
        raise ProposedAuthorityError(
            "%d signed row(s) could not become authority: %s"
            % (len(document["unresolved"]),
               json.dumps(document["unresolved"][:3])))
    if args.expect_total is not None and \
            document["authority_total"] != args.expect_total:
        raise ProposedAuthorityError(
            "expected %d authority rows and built %d"
            % (args.expect_total, document["authority_total"]))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print("pet-friendly    : %d" % document["pet_friendly_count"])
    print("verified-no-pets: %d" % document["verified_no_pets_count"])
    print("authority total : %d" % document["authority_total"])
    print("registered      : %s" % document["registered"])
    print("written         : %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
