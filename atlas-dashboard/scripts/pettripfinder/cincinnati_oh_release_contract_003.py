"""PTF-CINCINNATI-PROMOTION-AND-APPLICATION-003 -- re-author the Cincinnati release contract.

A release contract states what the market's authority ought to contain, and the
verifier compares it against what the authority actually derives. After a promotion
the two disagree by construction, so the contract is re-stated here.

EVERY NUMBER IS READ, NEVER TYPED
---------------------------------
The values written below come from ``release_contracts.derive_authority`` -- the
same derivation the verifier uses to judge the result. Hand-typing a count would
make the contract agree with the author rather than with the authority, which is
the one thing it exists to prevent. The content digest likewise comes from the
derivation and is never computed here by a second, private method.

WHAT IS DELIBERATELY NOT REWRITTEN
----------------------------------
The signed-authority provenance list is APPENDED to, not replaced: the orders that
signed the original 99 records still signed them, and this order is added beside
them rather than over them. The prose notes are rewritten to say what actually
happened, including the rows this promotion did not apply, because a contract that
records only the additions would be a contract that quietly hides the holds.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import release_contracts as RC          # noqa: E402

WORK_ORDER = "PTF-CINCINNATI-PROMOTION-AND-APPLICATION-003"
SOURCE_ORDER = "PTF-CINCINNATI-PARALLEL-REVALIDATION-002"
MARKET = "cincinnati-oh"
CONTRACT_PATH = (_REPO_ROOT / "deploy" / "netlify" / "release_contracts"
                 / ("%s.json" % MARKET))

RECONCILIATION_NOTE = (
    "verified_no_pets counts ONLY VERIFIED_NO_PETS records this market owns. "
    "unresolved is UNKNOWN and never negative evidence. %s promoted the "
    "reader-validated clean inventory from %s -- 31 pet-friendly and 26 "
    "verified-no-pets -- moving published 99 -> 130, no-pets 49 -> 75, resolved "
    "154 -> 211 and unresolved 103 -> 46. The census did not move: this order "
    "promoted policy, not membership. Two of the 28 clean no-pets rows were NOT "
    "applied. The Cincinnatian Hotel is held by founder decision because its only "
    "visible evidence is a service-animal sentence beside a structured flag, and "
    "this market has already ruled that a bare structured flag is not a refusal. "
    "Cincinnati Marriott at RiverCenter is held by the publication guard: "
    "address_key drops the street directional, so its refusal at 10 West "
    "RiverCenter Blvd would bar the already-published Embassy Suites at 10 East. "
    "Both keep their evidence committed." % (WORK_ORDER, SOURCE_ORDER))

PACKAGE_NOTE = (
    "The verified hotel identities are DERIVED from this package at assembly time "
    "via scripts.pettripfinder.site_data.verified_public_hotels(); they are not "
    "restated here. Records 100-130 were appended by %s and each carries its own "
    "approval block naming that order; the original 99 are unchanged. Seven of the "
    "31 appended records publish with pet_fee WITHHELD -- six because the committed "
    "reader refused the field, and Holiday Inn Express Fairfield because its page "
    "states three different charges for the same thing and founder item D1 directs "
    "that no price be published rather than that one of the three be chosen."
    % WORK_ORDER)


def _load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def reauthor(write: bool = False) -> Dict:
    contract = _load(CONTRACT_PATH)
    derived = RC.derive_authority(MARKET)

    before = json.loads(json.dumps(contract))

    pkg = contract["policy_package"]
    pkg["expected_sha256"] = derived.policy_package_sha256
    pkg["expected_record_count"] = derived.policy_package_record_count
    pkg["note"] = PACKAGE_NOTE

    surface = contract["public_surface"]
    surface["public_hotel_profile_count"] = derived.published_hotel_profiles
    surface["seed_hotel_rows"] = derived.seed_hotel_rows

    routes = contract["routes"]
    routes["hotel_route_count"] = derived.hotel_route_count
    routes["published_corridor_route_count"] = derived.corridor_route_count

    rec = contract["reconciliation"]
    rec["published_pet_friendly"] = derived.published_hotel_profiles
    rec["verified_no_pets"] = derived.verified_no_pets
    rec["resolved"] = derived.resolved
    rec["unresolved"] = derived.unresolved
    rec["note"] = RECONCILIATION_NOTE

    signed = contract.get("signed_authority") or {}
    for field in ("work_orders", "artifacts"):
        values: List[str] = list(signed.get(field) or ())
        if WORK_ORDER not in values:
            values.append(WORK_ORDER)
        signed[field] = values
    if "signed_authority_total" in signed:
        signed["signed_authority_total"] = derived.policy_package_record_count
    contract["signed_authority"] = signed

    if write:
        # LF-exact: deploy/**/*.json is pinned to eol=lf in .gitattributes.
        CONTRACT_PATH.write_bytes(
            (json.dumps(contract, indent=1) + "\n").encode("utf-8"))

    changed = [k for k in contract
               if json.dumps(contract[k], sort_keys=True)
               != json.dumps(before.get(k), sort_keys=True)]
    return {"work_order": WORK_ORDER, "written": write,
            "sections_changed": changed,
            "expected_record_count": pkg["expected_record_count"],
            "published_pet_friendly": rec["published_pet_friendly"],
            "verified_no_pets": rec["verified_no_pets"],
            "resolved": rec["resolved"], "unresolved": rec["unresolved"],
            "hotel_route_count": routes["hotel_route_count"],
            "published_corridor_route_count":
                routes["published_corridor_route_count"]}


if __name__ == "__main__":
    print(json.dumps(reauthor(write="--write" in sys.argv), indent=1))
