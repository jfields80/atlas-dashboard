"""PTF-ST-LOUIS-MARKET-001 -- build a market's identity census from discovery.

    python scripts/pettripfinder/market_census_cli.py \
      --market st-louis-mo \
      --candidates data/discovery/st_louis_market_001/candidates/st-louis-mo_candidates.json \
      --contract launch_packages/pettripfinder/markets/pending/st-louis-mo.json \
      --observed-at 2026-08-23 \
      --work-order PTF-ST-LOUIS-MARKET-001

Writes ``launch_packages/pettripfinder/identity_census/<market>.json`` (a
``ptf-market-identity-census/1.1`` document through the canonical constructors)
and ``launch_packages/pettripfinder/<market>_candidate_ledger_001.json`` (every
discovery candidate, with the disposition that kept it out or let it in).

``--contract`` exists because a market being built is not yet registered:
``markets/*.json`` IS the registry, and registering market N+1 forces a row in
the founder's launch participation record, whose sha256 the current production
deployment manifest pins. A market can be censused, closed and reviewed long
before anyone should touch that file, so this reads the contract from a path.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import census_partition_builder as CPB
from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.discovery import census_projection as CP
from scripts.pettripfinder.discovery.market_config import load_market_config
from scripts.pettripfinder.markets.contract import parse_market

CENSUS_DIR = _REPO_ROOT / "launch_packages" / "pettripfinder" / "identity_census"
PACKAGE_DIR = _REPO_ROOT / "launch_packages" / "pettripfinder"


def _in_bounds_map(candidates, market_id):
    """candidate_id -> whether its own coordinates sit inside the discovery box."""
    try:
        geo = load_market_config(market_id)
    except KeyError:
        return None
    out = {}
    for candidate in candidates:
        lat, lng = candidate.get("latitude"), candidate.get("longitude")
        out[candidate.get("candidate_id", "")] = (
            bool(lat is not None and lng is not None
                 and geo.bounds.contains(float(lat), float(lng))))
    return out


def build(market_id: str, candidates_path: Path, contract_path: Path, *,
          observed_at: str, work_order: str, source_authorities):
    candidates = json.loads(candidates_path.read_text(encoding="utf-8"))
    contract = parse_market(
        json.loads(contract_path.read_text(encoding="utf-8")),
        source=contract_path.name)
    if contract.market_id != market_id:
        raise SystemExit("ERROR: contract is for %r, not %r"
                         % (contract.market_id, market_id))

    admitted, ledger = CP.project(
        candidates, contract, observed_at=observed_at, work_order=work_order,
        in_bounds=_in_bounds_map(candidates, market_id))
    unique, collisions = CP.resolve_identity_key_collisions(admitted)
    corridors = CP.assign_corridors(unique, contract)

    # project() ledgered every survivor as ADMITTED; the collision resolver has
    # since held some of them. Re-label those entries, because a ledger whose
    # ADMITTED count exceeds the census row count is a ledger that does not
    # reconcile -- and reconciliation is the only reason it exists.
    held = {}
    for collision in collisions:
        for row in collision["held_for_review"]:
            held[row["candidate_id"]] = collision
    for entry in ledger:
        collision = held.get(entry["candidate_id"])
        if collision is None or entry["disposition"] != CP.ADMITTED:
            continue
        entry["disposition"] = CP.IDENTITY_COLLISION
        entry["why"] = (
            "identity key %r is also the key of a different building at %r; a "
            "census cannot hold two rows under one key, so this row is held for "
            "a human to name" % (collision["identity_key"], collision["kept_address"]))
        entry["collides_with_candidate_id"] = collision["kept_candidate_id"]

    # corridor_id -> the state that corridor declares. A provider that omits
    # the state has not made the property stateless: exactly one corridor
    # claims its postal code and that corridor knows which state it is in.
    corridor_state = {c.corridor_id: c.state_code for c in contract.corridors}

    rows = []
    derived_states = []
    for row in unique:
        candidate = row["candidate"]
        corridor, basis, value = corridors[row["identity_key"]]
        state = (candidate.get("state") or "").strip()
        state_source = "provider"
        if not state and corridor:
            state = corridor_state.get(corridor, "")
            state_source = "corridor_registry"
            if state:
                derived_states.append(OrderedDict((
                    ("identity_key", row["identity_key"]),
                    ("canonical_name", row["canonical_name"]),
                    ("postal_code", (candidate.get("postal_code") or "")[:5]),
                    ("corridor", corridor),
                    ("derived_state", state),
                    ("why", "the discovery provider stated no state; the "
                            "corridor that claims this postal code declares "
                            "one, and exactly one corridor may claim it"),
                )))
        rows.append(CPB.census_row(
            identity_key=row["identity_key"],
            canonical_name=row["canonical_name"],
            slug=CPB.slugify(row["canonical_name"]),
            market_id=market_id,
            address=(candidate.get("address_line") or "").split(",")[0].strip(),
            city=candidate.get("city", ""),
            state=state,
            postal_code=(candidate.get("postal_code") or "")[:5],
            phone=CP._phone(candidate),
            identity_state=row["identity_state"],
            lodging_state=row["lodging_state"],
            policy_state=enums.POLICY_NOT_VERIFIED,
            corridor=corridor,
            assignment_basis=basis,
            assignment_value=value,
            source="discovery",
            source_id=candidate.get("candidate_id", ""),
            observed_at=observed_at,
            provenance="%s:%s" % (work_order, "+".join(CP._providers(candidate))),
            official_url=CP._official_url(candidate),
            carried=OrderedDict((
                ("normalized_name", row["identity_key"]),
                ("discovery_cells", list(CP._cells(candidate))),
                ("discovery_providers", list(CP._providers(candidate))),
                ("discovery_review_state", candidate.get("review_state", "")),
                ("website_state", candidate.get("website_state", "")),
                ("latitude", candidate.get("latitude")),
                ("longitude", candidate.get("longitude")),
                ("lodging_basis", row["lodging_why"]),
                ("state_source", state_source),
            )),
        ))

    counts = Counter(r["identity_state"] for r in rows)
    document = CPB.census_document(
        market_id, rows,
        captured_at=observed_at,
        note=("%s built this census by projecting a persisted multi-provider "
              "discovery candidate set through discovery.census_projection: "
              "category, then membership by the corridor registry, then "
              "address-less identity reconciliation, then the canonical row "
              "constructor. Every discovery candidate that did not become a row "
              "is in the candidate ledger with its disposition; the ledger and "
              "this document sum to the discovered universe." % work_order),
        source_authorities=source_authorities,
        carried=OrderedDict((
            ("work_order", work_order),
            ("identity_state_counts", OrderedDict(sorted(counts.items()))),
            ("built_by", "scripts/pettripfinder/market_census_cli.py"),
            ("market_contract_source", str(contract_path.as_posix())),
            ("discovery_candidates_source", str(candidates_path.as_posix())),
            ("identity_key_collisions", collisions),
            ("states_derived_from_the_corridor_registry", derived_states),
            ("suspected_duplicates_for_review",
             CP.suspected_duplicates(rows)),
        )),
    )
    document["work_order"] = work_order
    return document, ledger, collisions


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market", required=True)
    parser.add_argument("--candidates", required=True)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--observed-at", required=True)
    parser.add_argument("--work-order", required=True)
    parser.add_argument("--source-authority", action="append", default=[])
    parser.add_argument("--ledger-out", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    document, ledger, collisions = build(
        args.market, Path(args.candidates), Path(args.contract),
        observed_at=args.observed_at, work_order=args.work_order,
        source_authorities=args.source_authority)

    dispositions = Counter(e["disposition"] for e in ledger)
    print("market                : %s" % args.market)
    print("discovery candidates  : %d" % sum(dispositions.values()))
    for name in CP.LEDGER_DISPOSITIONS:
        print("  %-34s: %d" % (name, dispositions.get(name, 0)))
    print("census rows           : %d" % document["count"])
    admitted_entries = dispositions.get(CP.ADMITTED, 0)
    if admitted_entries != document["count"]:
        raise SystemExit(
            "ERROR: ledger admits %d candidates but the census holds %d rows -- "
            "the two must reconcile exactly"
            % (admitted_entries, document["count"]))
    print("identity states       : %s" % dict(document["identity_state_counts"]))
    print("identity-key collapses: %d" % len(collisions))

    if args.dry_run:
        return 0

    census_path = CENSUS_DIR / ("%s.json" % args.market)
    sha = CPB.write_json(census_path, document)
    print("census                : %s (%s)" % (census_path, sha))

    ledger_path = Path(args.ledger_out) if args.ledger_out else (
        PACKAGE_DIR / ("%s_candidate_ledger_001.json" % args.market.replace("-", "_")))
    ledger_doc = OrderedDict((
        ("schema", "ptf-market-candidate-ledger/1.0"),
        ("what_this_is",
         "Every discovery candidate considered for this market's census, with "
         "the one disposition that admitted or excluded it. A census without "
         "this file states what a market contains; with it, the market can also "
         "say what it deliberately does not contain, and why."),
        ("market_id", args.market),
        ("work_order", args.work_order),
        ("observed_at", args.observed_at),
        ("count", len(ledger)),
        ("disposition_counts", OrderedDict(sorted(dispositions.items()))),
        ("candidates", sorted(ledger, key=lambda e: (e["disposition"], e["candidate_id"]))),
    ))
    ledger_sha = CPB.write_json(ledger_path, ledger_doc)
    print("candidate ledger      : %s (%s)" % (ledger_path, ledger_sha))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
