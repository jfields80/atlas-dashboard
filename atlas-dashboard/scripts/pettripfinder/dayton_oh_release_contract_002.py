"""PTF-DAYTON-OH-HARDENED-APPLICATION-002 -- Phase 11.

Re-author Dayton's release contract against the authority this order applied.

A contract is valid only where the reviewed document and the derived authority
agree on every field, and neither half alone is sufficient: derivation alone
would recompute its own expectation and prove nothing, and a reviewed document
alone would drift the moment an inventory changed. So this pass DERIVES every
number from Dayton's own committed authority and writes the derived value into
the document, together with a note saying what moved and why.

What moves, and why:

  policy package    47 -> 54 records, and its sha256 with them.
  public surface    47 -> 54 published of 54 seed rows, still 0 held.
  reconciliation    published 47 -> 54, no-pets 8 -> 24, resolved 55 -> 78,
                    unresolved 74 -> 51. The census does NOT move: it stays
                    pinned at 129.
  routes            47 -> 54 hotel routes; published corridors 12 -> 13, because
                    Washington Court House reached its publication minimum of one
                    when this order published the Holiday Inn Express there. The
                    number is recomputed from the deterministic assignment rather
                    than preserved.

The identity_census note is also rewritten, because this order closed the
discrepancy it had carried since PTF-DAYTON-WORK-BROWSER-INTEGRATION-001: the
census set of eight no-pets annotations and the registry set of eight were not
the same eight, and Holiday Inn Express & Suites Troy sat UNADJUDICATED because
a research agent had counted it with no quote, capture or hash. This order read
Troy's own page, bound it on street, postal and telephone, and admitted it on
evidence.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import OrderedDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import release_contracts as RC  # noqa: E402

MARKET = "dayton-oh"
CONTRACT = _REPO_ROOT / "deploy" / "netlify" / "release_contracts" / ("%s.json" % MARKET)
WORK_ORDER = "PTF-DAYTON-OH-HARDENED-APPLICATION-002"
SOURCE_ORDER = "PTF-DAYTON-OH-HARDENED-REVALIDATION-001"


def build(write: bool):
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    derived = RC.derive_authority(MARKET)
    recon = derived.reconciliation()

    contract["policy_package"]["expected_sha256"] = derived.policy_package_sha256
    contract["policy_package"]["expected_record_count"] = derived.policy_package_record_count
    contract["policy_package"]["schema_note"] = (
        "Schema %s. %s raised the record count from 47 to %d by applying the seven "
        "CLEAN_PET_FRIENDLY rows %s recovered at $0 through the attended lane. Every "
        "applied record carries its exact first-party quote, the document sha256 of "
        "the page it was read from, an artifact sha256, a capture timestamp and an "
        "identity binding on the property's own premises; facts the schema cannot "
        "represent safely are withheld with their source language rather than forced."
        % (derived.policy_package_schema_version, WORK_ORDER,
           derived.policy_package_record_count, SOURCE_ORDER))

    contract["public_surface"]["seed_hotel_rows"] = derived.seed_hotel_rows
    contract["public_surface"]["public_hotel_profile_count"] = derived.published_hotel_profiles
    contract["public_surface"]["excluded_public_profile_count"] = derived.excluded_public_profiles

    contract["routes"]["hotel_route_count"] = derived.hotel_route_count
    contract["routes"]["published_corridor_route_count"] = derived.corridor_route_count
    contract["routes"]["note"] = (
        "route_mode market_prefixed: this market's hub, corridor and policy-comparison "
        "pages live under /pet-friendly-hotels/dayton-oh/. %d of its eighteen configured "
        "corridors publish. %s raised that from twelve: Washington Court House reached "
        "its publication minimum of one when this order published the Holiday Inn Express "
        "there. Nothing was added to the market and no corridor lost its route; the number "
        "is recomputed from the deterministic assignment rather than preserved."
        % (derived.corridor_route_count, WORK_ORDER))

    contract["reconciliation"]["confirmed_identities"] = recon["confirmed_identities"]
    contract["reconciliation"]["published_pet_friendly"] = recon["published_pet_friendly"]
    contract["reconciliation"]["verified_no_pets"] = recon["verified_no_pets"]
    contract["reconciliation"]["resolved"] = recon["resolved"]
    contract["reconciliation"]["unresolved"] = recon["unresolved"]
    contract["reconciliation"]["note"] = (
        "verified_no_pets counts ONLY VERIFIED_NO_PETS records this market owns in its "
        "exclusion shard. unresolved is UNKNOWN, never negative evidence: a failed "
        "capture answers nothing. %s moved published 47 -> %d and no-pets 8 -> %d by "
        "applying the 23-row clean inventory; the census is unchanged at %d, because this "
        "order promoted POLICY and not membership. unresolved is counted from "
        "dayton_final_partition_002.json rather than derived by subtraction."
        % (WORK_ORDER, recon["published_pet_friendly"], recon["verified_no_pets"],
           recon["confirmed_identities"]))

    contract["identity_census"]["note"] = (
        "The census is PINNED at %d and this order did not move it. %s closed the "
        "no-pets discrepancy this contract had carried since "
        "PTF-DAYTON-WORK-BROWSER-INTEGRATION-001, where the census set of eight "
        "annotations and the exclusion registry's eight were not the same eight and "
        "Holiday Inn Express & Suites Troy stayed UNADJUDICATED because a research "
        "agent had counted it with no quote, capture or hash: Troy's own page was read, "
        "bound on street, postal and telephone, and admitted on evidence. The registry "
        "now holds %d. CENSUS COVERAGE IS NOT CONFIRMED: %s could not register a local "
        "OSM extract for this market and Marriott refused 244 of the 252 property pages "
        "the free brand harvest scoped here, so zero confirmed-missing identities means "
        "no candidate reached the evidence bar, NOT that 129 is exhaustive."
        % (recon["confirmed_identities"], WORK_ORDER, recon["verified_no_pets"], SOURCE_ORDER))

    contract["deployment_authorization"]["means"] = (
        "A passing contract means this market's assembled package is STRUCTURALLY "
        "deployable: its authority files agree, its routes match its reviewed inventory, "
        "no held identity leaks, and every publish/tech gate holds. It is not a "
        "deployment authorization and it makes no claim that the market's identity "
        "universe is fully resolved -- %d of this market's %d confirmed identities are "
        "still unresolved, and the census itself has not been proven complete."
        % (recon["unresolved"], recon["confirmed_identities"]))

    problems = RC.contract_disagreements(contract, derived)
    print("derived: %d confirmed / %d published / %d no-pets / %d resolved / %d unresolved"
          % (recon["confirmed_identities"], recon["published_pet_friendly"],
             recon["verified_no_pets"], recon["resolved"], recon["unresolved"]))
    print("routes: %d hotel / %d corridor" % (derived.hotel_route_count, derived.corridor_route_count))
    print("disagreements after re-authoring:", len(problems))
    for p in problems:
        print("   -", p)
    if problems:
        raise SystemExit("contract still disagrees with derived authority")
    if write:
        CONTRACT.write_bytes((json.dumps(contract, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
        print("WRITTEN", CONTRACT.relative_to(_REPO_ROOT).as_posix())
    else:
        print("(dry run)")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    build(args.write)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
