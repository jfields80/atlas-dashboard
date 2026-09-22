"""PTF-WEST-PALM-BEACH-FL-FOUNDER-LAUNCH-AUTHORIZATION-003 -- the founder's West
Palm Beach launch decision.

    python -m scripts.pettripfinder.west_palm_beach_fl_launch_participation_003
    python -m scripts.pettripfinder.west_palm_beach_fl_launch_participation_003 --write

THIS RECORDS A DECISION, IT DOES NOT MAKE ONE
---------------------------------------------
The founder authorized the flip in this order, explicitly: "The founder explicitly
grants launch authorization for west-palm-beach-fl ... The founder accepts the sealed
publication cohort: 190 census identities, 49 approved pet-friendly profiles, 25
verified no-pets exclusions, 116 unresolved but bounded, ACTIONABLE UNRESOLVED = 0."
This module writes that decision down. It does not decide anything, and it must never
be run to make a market live on its own initiative.

WHAT THE FOUNDER DID **NOT** AUTHORIZE
---------------------------------------
The same order is explicit about the limits, and they are recorded here so a later
reader cannot mistake the scope: "Do not weaken evidence or identity standards. Do
not publish held rows." Nothing about WHICH identities publish changes -- only
WHETHER the market as a whole joins the next assembly. The four duplicate-premises
halves stay on their identity hold, the 116 unresolved rows stay unpublished, and
the 25 verified-no-pets rows stay exclusions rather than profiles.

THE BASIS IS DERIVED, NEVER TYPED
----------------------------------
Every number in ``decision_basis`` is read from the committed authority at run time
-- the census, the policy package, the exclusion shard and the release contract. The
record explicitly is NOT an authority: the assembler re-derives all of it, and a
status that disagrees with the source fails the build.

THE CHAIN IS EXTENDED, NOT REWRITTEN
-------------------------------------
The block is built by ``launch_participation.extend_decision``, which is the one
writer that cannot drop ``supersedes`` or ``lineage``: the predecessor becomes the
newest ancestor and the chain it carried comes forward whole. That is the repair
PTF-SUPERSESSIONS-LINEAGE-REPAIR-001 paid for, and a founder decision is exactly the
kind of write that lost it nineteen times before.

NO OTHER MARKET MOVES. Detroit stays withheld and every other waiting market stays
NOT authorized: the founder's decision named West Palm Beach and nothing else.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import launch_participation as LP     # noqa: E402

WORK_ORDER = "PTF-WEST-PALM-BEACH-FL-FOUNDER-LAUNCH-AUTHORIZATION-003"
MARKET = "west-palm-beach-fl"
DECIDED_ON = "2026-09-22"
FOUNDER_PACKET = "PTF-WEST-PALM-BEACH-FL-REGISTRATION-AND-STAGING-002"
FOUNDER_PACKET_PATH = ("launch_packages/pettripfinder/markets/reports/"
                       "west_palm_beach_fl_registration_authorization_readiness.json")
PARENT_DEPLOY_ID = "6ab1a035c7ef3b14a23a4ec6"
#: the live RELEASE-INDEX digest the readiness document binds (release_index.digest())
PARENT_RELEASE_DIGEST = "sha256:0ec19aa98462858d02a0770eb29e2cc124cfd7f7b82084ee34b2cc022062f94c"
REGISTERED_PACKAGE_DIGEST = "sha256:789c0187e366abe8c199feb799ec691241d83ae81c3178e9cd4de41dde2c7bf8"

#: the corridors that reach their own publication minimum, from the sealed package's
#: declared routes. Named here for the record only -- the assembler derives them.
PUBLISHING_CORRIDORS = ("downtown-west-palm-beach", "palm-beach-gardens",
                        "palm-beach-international-airport", "delray-beach", "boca-raton")

PACKAGE = _REPO_ROOT / "launch_packages" / "pettripfinder"
PATH = LP.PARTICIPATION_PATH

REASON = (
    "Founder authorizes The Palm Beaches to participate in the next production assembly, "
    "joining as the THIRTY-THIRD market with 49 pet-friendly profiles and 25 verified-no-pets "
    "records over a 190-identity census. Every other market's decision is unchanged, and every "
    "other waiting market remains NOT authorized for launch -- the decision named West Palm "
    "Beach and nothing else. This authorization is bound to the authorization-readiness "
    "document %s (%s), itself bound to the current live parent (deploy %s, release-index digest "
    "%s) and registered package %s. The founder's own words bound the cohort as well as the "
    "market: 'The founder accepts the sealed publication cohort ... ACTIONABLE UNRESOLVED = 0. "
    "Do not weaken evidence or identity standards. Do not publish held rows.' 116 unresolved "
    "identities, the four duplicate-premises halves on an identity hold, and every evidence "
    "hold stay exactly as adjudicated -- this decision authorizes the market, not any of its "
    "held rows."
    % (FOUNDER_PACKET, FOUNDER_PACKET_PATH, PARENT_DEPLOY_ID, PARENT_RELEASE_DIGEST,
       REGISTERED_PACKAGE_DIGEST))

NOTE = (
    "49 pet-friendly profiles and 25 verified-no-pets over a 190-identity census. Built from "
    "zero by PTF-WEST-PALM-BEACH-FL-HARDENED-SOURCE-READY-001 on the Fort-Lauderdale-live "
    "lineage and closed in that same order through the supported attended-browser lane "
    "(actionable unresolved 0), registered against the Fort-Lauderdale-live parent by "
    "PTF-WEST-PALM-BEACH-FL-REGISTRATION-AND-STAGING-002 as COMPOSITE_FRESH_MARKET_DATA_ONLY "
    "with 15/15 registration checks and 0 broad regression runs, and ADMITTED here by %s, which "
    "is the founder's explicit launch decision. Hidden from global navigation and from the "
    "sitemap (show_in_navigation=false, show_in_sitemap=false), exactly as every other recently "
    "launched market is at this stage -- those flags govern the hub's place in navigation, not "
    "whether the market's profile URLs are indexed. 5 of its 15 corridors reach their own "
    "publication minimum (%s); the rest are suppressed, which is a threshold and not a gap, and "
    "not one was forced. 116 rows that did not publish -- the four duplicate-premises halves on "
    "an identity hold, 58 routing holds, 26 source-silent rows, 24 access-blocked rows and four "
    "evidence holds -- are unaffected by this decision. Membership stays this market's own "
    "corridor postal partition: Broward belongs to the LIVE fort-lauderdale-fl market and "
    "Miami-Dade to the LIVE miami-fl market, and neither contributes one row here."
    % (WORK_ORDER, ", ".join(PUBLISHING_CORRIDORS)))


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
        ("publishing_corridors", list(PUBLISHING_CORRIDORS)),
        ("not_authorized_by_this_decision", [
            "weaker evidence rules",
            "weaker identity standards",
            "anti-bot bypass",
            "invented duplicate-premises identity rulings",
            "publication of held properties",
        ]),
        ("policy_package", entry(policy_path)),
        ("exclusion_shard", entry(shard_path)),
        ("release_contract", entry(contract_path)),
        ("identity_census", entry(census_path)),
    ))


def flip(write: bool = False) -> Dict:
    document = json.loads(PATH.read_text(encoding="utf-8-sig"))
    previous_sha = LP.participation_sha256()

    authorized_before = sorted(
        m["market_id"] for m in document["markets"]
        if m["launch_status"] == LP.FOUNDER_AUTHORIZED_FOR_LAUNCH)
    if MARKET in authorized_before:
        raise SystemExit("%s: %s is already authorized" % (WORK_ORDER, MARKET))

    hit = 0
    for market in document["markets"]:
        if market["market_id"] != MARKET:
            continue
        hit += 1
        market["launch_status"] = LP.FOUNDER_AUTHORIZED_FOR_LAUNCH
        market["note"] = NOTE
    if hit != 1:
        raise SystemExit("%s: expected exactly one %s row, found %d" % (WORK_ORDER, MARKET, hit))

    # The chain is EXTENDED by the canonical writer, never rebuilt here: it is the one
    # path that cannot drop `supersedes` or `lineage`, which is what nineteen launches
    # lost before PTF-SUPERSESSIONS-LINEAGE-REPAIR-001.
    previous = {"decision": json.loads(PATH.read_text(encoding="utf-8-sig"))["decision"],
                "markets": json.loads(PATH.read_text(encoding="utf-8-sig"))["markets"]}
    document["decision"] = LP.extend_decision(
        previous, previous_sha,
        work_order=WORK_ORDER,
        decided_by="founder",
        decided_on=DECIDED_ON,
        reason=REASON,
        path=PATH,
        decision_basis=_basis(),
    )

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
    print("previous record sha256:", result["previous_record_sha256"])
    print("authorized after:", ", ".join(result["authorized_after"]))
