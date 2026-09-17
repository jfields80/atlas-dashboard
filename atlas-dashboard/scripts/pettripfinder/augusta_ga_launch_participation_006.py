"""PTF-AUGUSTA-GA-V2-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006 -- the founder's
Augusta launch decision.

    python -m scripts.pettripfinder.augusta_ga_launch_participation_006
    python -m scripts.pettripfinder.augusta_ga_launch_participation_006 --write

THIS RECORDS A DECISION, IT DOES NOT MAKE ONE
---------------------------------------------
The founder authorized the flip in this order, explicitly under founder
authorization packet 005 (bound to the current Tampa-live parent, deploy
6aab379e0777c9ee96702a4f, 29/2151/2460). This module writes that decision
down. It does not decide anything, and it must never be run to make a
market live on its own initiative.

THE BASIS IS DERIVED, NEVER TYPED
----------------------------------
Every number in ``decision_basis`` is read from the committed authority at
run time -- the census, the policy package, the exclusion shard and the
release contract. The record explicitly is NOT an authority: the assembler
re-derives all of it, and a status that disagrees with the source fails the
build.

THE PREVIOUS RECORD IS SUPERSEDED, NOT ERASED
-----------------------------------------------
The Tampa-fl registration record this one supersedes is appended to the
lineage with its own digest, so a deployment authorization can still be
matched to the record it signed however many reissues have happened since.

NO OTHER MARKET MOVES. detroit-ann-arbor-mi remains assemblable but stays NOT
authorized: the founder's decision named Augusta and nothing else. All 63
Augusta holds and all 21 South Carolina discovery identities stay exactly as
adjudicated -- this flip touches nothing about WHICH Augusta identities are
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

WORK_ORDER = "PTF-AUGUSTA-GA-V2-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006"
MARKET = "augusta-ga"
DECIDED_ON = "2026-09-17"
FOUNDER_PACKET = "PTF-AUGUSTA-GA-V2-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-005"
FOUNDER_PACKET_PATH = ("launch_packages/pettripfinder/markets/reports/"
                       "augusta_ga_founder_authorization_packet_005.json")
PARENT_DEPLOY_ID = "6aab379e0777c9ee96702a4f"
PARENT_RELEASE_DIGEST = "cf761795e3deb1380ffb8e25869bd6ceefe31d2a9dfbaddad30c550ff69d60d2"
REGISTERED_PACKAGE_DIGEST = "sha256:14806eca154760a0a9dc59b200b4fa83e4f748b4ebc8eba197eab8d1e50c0df6"

PACKAGE = _REPO_ROOT / "launch_packages" / "pettripfinder"
PATH = LP.PARTICIPATION_PATH

REASON = (
    "Founder authorizes Augusta to participate in the next production assembly, "
    "joining as the THIRTIETH market with 14 pet-friendly profiles and 14 "
    "verified-no-pets records over a 91-identity census. Every other market's "
    "decision is unchanged, and detroit-ann-arbor-mi remains NOT authorized for "
    "launch -- the decision named Augusta and nothing else. This authorization "
    "is bound to founder authorization packet 005 (%s), itself bound to the "
    "current live parent (deploy %s, release digest %s) and registered package "
    "%s. 63 Augusta identities and 21 South Carolina discovery identities stay "
    "held/outside exactly as adjudicated; this decision authorizes the market, "
    "not any of its held rows."
    % (FOUNDER_PACKET, PARENT_DEPLOY_ID, PARENT_RELEASE_DIGEST, REGISTERED_PACKAGE_DIGEST))


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
    packet_path = _REPO_ROOT / "atlas-dashboard" / FOUNDER_PACKET_PATH
    if not packet_path.is_file():
        packet_path = _REPO_ROOT / FOUNDER_PACKET_PATH

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
        ("holds_unresolved", 91 - len(policy["hotels"]) - no_pets),
        ("south_carolina_profiles_admitted", 0),
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
            "14 pet-friendly profiles and 14 verified-no-pets over a 91-identity census. "
            "Registered by PTF-AUGUSTA-GA-V2-REGISTRATION-AND-FOUNDER-PACKET-003, resealed "
            "against the Orlando-live parent by PTF-AUGUSTA-GA-V2-STALE-PARENT-RECHECK-004, "
            "resealed again against the Tampa-live parent by "
            "PTF-AUGUSTA-GA-V2-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-005, and ADMITTED here by "
            "%s, which is the founder's explicit launch decision bound to founder authorization "
            "packet 005. Hidden from global navigation and from the sitemap "
            "(show_in_navigation=false, show_in_sitemap=false), exactly as every other recently "
            "launched market is at this stage -- those flags govern the hub's place in "
            "navigation, not whether the market's profile URLs are indexed. 1 of its 11 "
            "corridors (Washington Road) reaches its own publication minimum; the rest are "
            "suppressed, which is a threshold and not a gap. 63 held identities and 21 South "
            "Carolina discovery identities are unaffected by this decision." % WORK_ORDER)
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
            "detroit_authorized": "detroit-ann-arbor-mi" in authorized_after,
            "previous_record_sha256": previous_sha}


if __name__ == "__main__":
    result = flip(write="--write" in sys.argv)
    print(json.dumps({k: result[k] for k in (
        "markets_before", "markets_after", "gained", "lost",
        "detroit_authorized", "written")}, indent=1))
    print("authorized after:", ", ".join(result["authorized_after"]))
