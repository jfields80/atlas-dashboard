"""PTF-CINCINNATI-DEPLOYMENT-AND-LAUNCH-AUTHORIZATION-004 -- the founder's Cincinnati launch decision.

    python -m scripts.pettripfinder.cincinnati_oh_launch_participation_004
    python -m scripts.pettripfinder.cincinnati_oh_launch_participation_004 --write

This is the ONE lever that moves a market from source-ready to live. Until it
flips, Cincinnati's 130 published profiles exist in authority and reach no
reader; PTF-CINCINNATI-PROMOTION-AND-APPLICATION-003 proved exactly that by
reassembling the bundle and reproducing production byte for byte.

THIS RECORDS A DECISION, IT DOES NOT MAKE ONE
---------------------------------------------
The founder authorized the flip in PTF-CINCINNATI-DEPLOYMENT-AND-LAUNCH-
AUTHORIZATION-004, in the words "YES -- authorize the Cincinnati participation
flip". This module writes that decision down. It does not decide anything, and
it must never be run to make a market live on its own initiative.

THE BASIS IS DERIVED, NEVER TYPED
---------------------------------
Every number and digest in ``decision_basis`` is read from the committed
authority at run time -- the census, the policy package, the exclusion shard and
the release contract. The record explicitly is NOT an authority: the assembler
re-derives all of it, and a status that disagrees with the source fails the
build. Typing a count here would let the record and the market drift apart while
still looking signed.

THE PREVIOUS RECORD IS SUPERSEDED, NOT ERASED
---------------------------------------------
The Grand Rapids record this one supersedes is appended to the lineage with its
own digest, so a deployment authorization can still be matched to the record it
signed however many reissues have happened since.

NO OTHER MARKET MOVES. Detroit is assemblable at 121 published and stays
NOT authorized: the founder's decision named Cincinnati and nothing else, and a
launch record that quietly carried a second market would be the worst kind of
defect this file could hold.
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

WORK_ORDER = "PTF-CINCINNATI-DEPLOYMENT-AND-LAUNCH-AUTHORIZATION-004"
MARKET = "cincinnati-oh"
DECIDED_ON = "2026-09-06"
PROMOTION_ORDER = "PTF-CINCINNATI-PROMOTION-AND-APPLICATION-003"
SOURCE_COMMIT = "a0cec800f619a2ffd3a865511877b8f8afa407f6"

PACKAGE = _REPO_ROOT / "launch_packages" / "pettripfinder"
PATH = LP.PARTICIPATION_PATH

REASON = (
    "Founder authorizes Cincinnati to participate in the next production "
    "assembly, joining as the TENTH market with 130 pet-friendly profiles. Every "
    "other market's decision is unchanged, and detroit-ann-arbor-mi remains NOT "
    "authorized for launch even though it is assemblable at 121 published -- the "
    "decision named Cincinnati and nothing else. %s promoted the market to 130 "
    "published and 75 verified-no-pets over an unmoved 257-identity census, "
    "proved the promotion moved no byte of the live bundle while participation "
    "stayed off, and prepared the exact candidate a flip would produce. This row "
    "consumes that preparation." % PROMOTION_ORDER)


def _sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rel(path: Path) -> str:
    return str(path.relative_to(_REPO_ROOT)).replace("\\", "/")


def _basis() -> Dict:
    """What the founder was shown, read from committed authority at run time."""
    census_path = PACKAGE / "identity_census" / ("%s.json" % MARKET)
    policy_path = PACKAGE / ("hotel_policy_facts_%s.json" % MARKET)
    shard_path = (PACKAGE / "markets" / "authority" / MARKET
                  / "hotel_exclusions.json")
    contract_path = (_REPO_ROOT / "deploy" / "netlify" / "release_contracts"
                     / ("%s.json" % MARKET))

    census = json.loads(census_path.read_text(encoding="utf-8-sig"))
    policy = json.loads(policy_path.read_text(encoding="utf-8-sig"))
    shard = json.loads(shard_path.read_text(encoding="utf-8-sig"))
    no_pets = sum(1 for e in shard["exclusions"]
                  if e["exclusion_state"] == "VERIFIED_NO_PETS")

    def entry(path: Path) -> Dict:
        return OrderedDict((("path", _rel(path)), ("sha256", _sha256_of(path))))

    return OrderedDict((
        ("what_this_is",
         "What the founder was shown when deciding. These are a RECORD of the "
         "basis, not an authority: the assembler derives every one of them from "
         "the market's own census, package, shard and release contract, and a "
         "status that disagrees with the source fails the build."),
        ("market_id", MARKET),
        ("source_commit", SOURCE_COMMIT),
        ("census_count", census["count"]),
        ("pet_friendly_publication_count", len(policy["hotels"])),
        ("verified_no_pets_count", no_pets),
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
            "130 pet-friendly profiles and 75 verified-no-pets over a "
            "257-identity census; release contract verifies with zero "
            "disagreements. Promoted by %s and ADMITTED here by %s, which is the "
            "founder's explicit launch decision. Hidden from global navigation "
            "and from the market listing: show_in_navigation=false and "
            "show_in_sitemap=false, exactly as live Louisville is -- those flags "
            "govern the hub's place in navigation, not whether the market's "
            "profile URLs are indexed, and its 148 routes do enter sitemap.xml."
            % (PROMOTION_ORDER, WORK_ORDER))
    if hit != 1:
        raise SystemExit("%s: expected exactly one %s row, found %d"
                         % (WORK_ORDER, MARKET, hit))

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
        raise SystemExit(
            "%s: the flip must add exactly %s and remove nothing; gained %s, "
            "lost %s" % (WORK_ORDER, MARKET, gained, lost))

    if write:
        PATH.write_bytes((json.dumps(document, indent=1) + "\n").encode("utf-8"))

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
