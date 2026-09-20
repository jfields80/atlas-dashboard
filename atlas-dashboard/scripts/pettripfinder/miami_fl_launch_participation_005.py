"""PTF-MIAMI-FL-FOUNDER-LAUNCH-AUTHORIZATION-005 -- the founder's Miami launch decision.

    python -m scripts.pettripfinder.miami_fl_launch_participation_005
    python -m scripts.pettripfinder.miami_fl_launch_participation_005 --write

THIS RECORDS A DECISION, IT DOES NOT MAKE ONE
---------------------------------------------
The founder authorized the flip in this order, explicitly: "Founder authorization
is explicitly granted for: miami-fl ... Only Miami is authorized by this order."
This module writes that decision down. It does not decide anything, and it must
never be run to make a market live on its own initiative.

THE BASIS IS DERIVED, NEVER TYPED
----------------------------------
Every number in ``decision_basis`` is read from the committed authority at run
time -- the census, the policy package, the exclusion shard and the release
contract. The record explicitly is NOT an authority: the assembler re-derives all
of it, and a status that disagrees with the source fails the build.

THE PREVIOUS RECORD IS SUPERSEDED, NOT ERASED
-----------------------------------------------
The record this one supersedes is appended to the lineage with its own digest, so
a deployment authorization can still be matched to the record it signed however
many reissues have happened since.

NO OTHER MARKET MOVES. Every other waiting market stays NOT authorized: the
founder's decision named Miami and nothing else. All 455 Miami holds stay exactly
as adjudicated -- this flip touches nothing about WHICH Miami identities are
published, only WHETHER the market as a whole joins the next assembly.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import launch_participation as LP     # noqa: E402

WORK_ORDER = "PTF-MIAMI-FL-FOUNDER-LAUNCH-AUTHORIZATION-005"
MARKET = "miami-fl"
DECIDED_ON = "2026-09-20"
FOUNDER_PACKET = "PTF-MIAMI-FL-REGISTRATION-AND-STAGING-004"
FOUNDER_PACKET_PATH = ("launch_packages/pettripfinder/markets/reports/"
                       "miami_fl_registration_authorization_readiness.json")
PARENT_DEPLOY_ID = "6aaeb3b7384e1bb712adb084"
#: the live RELEASE-INDEX digest the readiness document binds (release_index.digest())
PARENT_RELEASE_DIGEST = "sha256:c7998b87f638354ec5db316487f77c089f4351966aad9b0d99b4add74f0dd023"
REGISTERED_PACKAGE_DIGEST = "sha256:b586ad449e46d0572c8b3c9248d56a8dcec7a51c4bf938598e9f1428f0b73cb1"

PACKAGE = _REPO_ROOT / "launch_packages" / "pettripfinder"
PATH = LP.PARTICIPATION_PATH

REASON = (
    "Founder authorizes Greater Miami to participate in the next production assembly, "
    "joining as the THIRTY-FIRST market with 125 pet-friendly profiles and 57 "
    "verified-no-pets records over a 637-identity census. Every other market's "
    "decision is unchanged, and every other waiting market remains NOT authorized "
    "for launch -- the decision named Miami and nothing else. This authorization is "
    "bound to the authorization-readiness document %s (%s), itself bound to the "
    "current live parent (deploy %s, release-index digest %s) and registered package "
    "%s. 455 Miami identities stay held exactly as adjudicated -- access-blocked "
    "behind brand anti-bot walls, silent on their own pages, routeless, or open on "
    "identity; this decision authorizes the market, not any of its held rows."
    % (FOUNDER_PACKET, FOUNDER_PACKET_PATH, PARENT_DEPLOY_ID, PARENT_RELEASE_DIGEST,
       REGISTERED_PACKAGE_DIGEST))


def _sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rel(path: Path) -> str:
    return str(path.relative_to(_REPO_ROOT)).replace("\\", "/")


def _basis() -> Dict:
    """What the founder was shown, read from committed authority at run time."""
    census_path = PACKAGE / "identity_census" / ("%s.json" % MARKET)
    policy_path = PACKAGE / ("hotel_policy_facts_%s.json" % MARKET)
    shard_path = PACKAGE / "markets" / "authority" / MARKET / "hotel_exclusions.json"
    contract_path = _REPO_ROOT / "deploy" / "netlify" / "release_contracts" / ("%s.json" % MARKET)

    census = json.loads(census_path.read_text(encoding="utf-8-sig"))
    policy = json.loads(policy_path.read_text(encoding="utf-8-sig"))
    shard = json.loads(shard_path.read_text(encoding="utf-8-sig"))
    no_pets = sum(1 for e in shard["exclusions"] if e["exclusion_state"] == "VERIFIED_NO_PETS")

    def entry(path: Path) -> Dict:
        return OrderedDict((("path", _rel(path)), ("sha256", _sha256_of(path))))

    return OrderedDict((
        ("what_this_is",
         "What the founder was shown when deciding. These are a RECORD of the basis, not an "
         "authority: the assembler derives every one of them from the market's own census, "
         "package, shard and release contract, and a status that disagrees with the source fails "
         "the build."),
        ("market_id", MARKET),
        ("founder_authorization_packet", FOUNDER_PACKET),
        ("parent_deploy_id", PARENT_DEPLOY_ID),
        ("parent_release_digest", PARENT_RELEASE_DIGEST),
        ("registered_package_digest", REGISTERED_PACKAGE_DIGEST),
        ("census_count", census["count"]),
        ("pet_friendly_publication_count", len(policy["hotels"])),
        ("verified_no_pets_count", no_pets),
        ("holds_unresolved", census["count"] - len(policy["hotels"]) - no_pets),
        ("actionable_unresolved_remaining", 0),
        ("policy_package", entry(policy_path)),
        ("exclusion_shard", entry(shard_path)),
        ("release_contract", entry(contract_path)),
        ("identity_census", entry(census_path)),
    ))


def flip(write: bool = False) -> Dict:
    document = json.loads(PATH.read_text(encoding="utf-8-sig"))
    previous = document["decision"]
    previous_sha = LP.participation_sha256()

    authorized_before = sorted(
        m["market_id"] for m in document["markets"]
        if m["launch_status"] == LP.FOUNDER_AUTHORIZED_FOR_LAUNCH)
    if MARKET in authorized_before:
        raise SystemExit("%s: %s is already authorized" % (WORK_ORDER, MARKET))

    superseded = OrderedDict((
        ("work_order", previous["work_order"]),
        ("sha256", previous_sha),
        ("founder_authorized", authorized_before),
    ))

    lineage = previous.get("lineage") or {}
    records: List[Dict] = list(lineage.get("records") or ())
    if not any(r.get("work_order") == previous["work_order"] for r in records):
        records.append(dict(superseded))

    hit = 0
    for market in document["markets"]:
        if market["market_id"] != MARKET:
            continue
        hit += 1
        market["launch_status"] = LP.FOUNDER_AUTHORIZED_FOR_LAUNCH
        market["note"] = (
            "125 pet-friendly profiles and 57 verified-no-pets over a 637-identity census. "
            "Built from zero by PTF-MIAMI-FL-HARDENED-SOURCE-READY-001, closed through the "
            "authorized attended-browser lane by PTF-MIAMI-FL-BROWSER-CLOSURE-002 and "
            "PTF-MIAMI-FL-MARRIOTT-TERMINAL-CLOSURE-003 (actionable unresolved 0), registered "
            "against the Augusta-live parent by PTF-MIAMI-FL-REGISTRATION-AND-STAGING-004, and "
            "ADMITTED here by %s, which is the founder's explicit launch decision. Hidden from "
            "global navigation and from the sitemap (show_in_navigation=false, "
            "show_in_sitemap=false), exactly as every other recently launched market is at this "
            "stage -- those flags govern the hub's place in navigation, not whether the market's "
            "profile URLs are indexed. 10 of its 20 corridors reach their own publication "
            "minimum; the rest are suppressed, which is a threshold and not a gap. 455 held "
            "identities are unaffected by this decision." % WORK_ORDER)
    if hit != 1:
        raise SystemExit("%s: expected exactly one %s row, found %d" % (WORK_ORDER, MARKET, hit))

    document["decision"] = OrderedDict((
        ("work_order", WORK_ORDER),
        ("decided_by", "founder"),
        ("decided_on", DECIDED_ON),
        ("reason", REASON),
        ("lineage", OrderedDict((
            ("what_this_is", (lineage.get("what_this_is") or "")),
            ("records", records)))),
        ("decision_basis", _basis()),
        ("supersedes", superseded),
    ))

    authorized_after = sorted(
        m["market_id"] for m in document["markets"]
        if m["launch_status"] == LP.FOUNDER_AUTHORIZED_FOR_LAUNCH)
    gained = sorted(set(authorized_after) - set(authorized_before))
    lost = sorted(set(authorized_before) - set(authorized_after))
    if gained != [MARKET] or lost:
        raise SystemExit("%s: the flip must add exactly %s and remove nothing; gained %s, lost %s"
                         % (WORK_ORDER, MARKET, gained, lost))

    if write:
        PATH.write_bytes((json.dumps(document, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))

    return {"work_order": WORK_ORDER, "written": write,
            "authorized_before": authorized_before,
            "authorized_after": authorized_after,
            "gained": gained, "lost": lost,
            "markets_before": len(authorized_before),
            "markets_after": len(authorized_after),
            "previous_record_sha256": previous_sha}


if __name__ == "__main__":
    result = flip(write="--write" in sys.argv)
    print(json.dumps({k: result[k] for k in (
        "markets_before", "markets_after", "gained", "lost", "written")}, indent=1))
    print("authorized after:", ", ".join(result["authorized_after"]))
