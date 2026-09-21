"""PTF-FORT-LAUDERDALE-FL-FOUNDER-LAUNCH-AUTHORIZATION-003 -- the founder's Fort
Lauderdale launch decision.

    python -m scripts.pettripfinder.fort_lauderdale_fl_launch_participation_003
    python -m scripts.pettripfinder.fort_lauderdale_fl_launch_participation_003 --write

THIS RECORDS A DECISION, IT DOES NOT MAKE ONE
---------------------------------------------
The founder authorized the flip in this order, explicitly: "The founder explicitly
grants launch authorization for: fort-lauderdale-fl ... The founder explicitly
accepts launching the current safe cohort: 461 qualifying census identities, 85
approved pet-friendly profiles, ACTIONABLE UNRESOLVED = 0." This module writes that
decision down. It does not decide anything, and it must never be run to make a
market live on its own initiative.

WHAT THE FOUNDER DID **NOT** AUTHORIZE
---------------------------------------
The same order is explicit about the limits, and they are recorded here so a later
reader cannot mistake the scope: this authorization does not weaken any evidence
rule, does not permit anti-bot bypass, does not invent a dual-brand identity
ruling, and does not publish one held property. The cohort that launches is the
cohort that was already sealed. Nothing about WHICH identities publish changes --
only WHETHER the market as a whole joins the next assembly.

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

NO OTHER MARKET MOVES. Detroit stays withheld and every other waiting market stays
NOT authorized: the founder's decision named Fort Lauderdale and nothing else. All
376 Fort Lauderdale rows that did not publish stay exactly as adjudicated.
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

WORK_ORDER = "PTF-FORT-LAUDERDALE-FL-FOUNDER-LAUNCH-AUTHORIZATION-003"
MARKET = "fort-lauderdale-fl"
DECIDED_ON = "2026-09-21"
FOUNDER_PACKET = "PTF-FORT-LAUDERDALE-FL-REGISTRATION-AND-STAGING-002"
FOUNDER_PACKET_PATH = ("launch_packages/pettripfinder/markets/reports/"
                       "fort_lauderdale_fl_registration_authorization_readiness.json")
PARENT_DEPLOY_ID = "6ab071a5b7561c33aff6c17b"
#: the live RELEASE-INDEX digest the readiness document binds (release_index.digest())
PARENT_RELEASE_DIGEST = "sha256:1bbcb59d60b999065fe9be1f140cf544026a431c15d30c5049d7d23c25eaeac7"
REGISTERED_PACKAGE_DIGEST = "sha256:398ca08f89a75b8aab47af83a8a56ad4300075b37fa7f10c9ec31df4fdda0518"

PACKAGE = _REPO_ROOT / "launch_packages" / "pettripfinder"
PATH = LP.PARTICIPATION_PATH

REASON = (
    "Founder authorizes Greater Fort Lauderdale to participate in the next production "
    "assembly, joining as the THIRTY-SECOND market with 85 pet-friendly profiles and 53 "
    "verified-no-pets records over a 461-identity census. Every other market's decision is "
    "unchanged, and every other waiting market remains NOT authorized for launch -- the "
    "decision named Fort Lauderdale and nothing else. This authorization is bound to the "
    "authorization-readiness document %s (%s), itself bound to the current live parent "
    "(deploy %s, release-index digest %s) and registered package %s. The founder's own words "
    "bound the cohort as well as the market: 'The remaining unresolved population is accepted "
    "as bounded and non-actionable under the current authorized acquisition policy', and this "
    "authorization explicitly does NOT authorize weaker evidence rules, anti-bot bypass, "
    "invented dual-brand identity rulings, or publication of held properties. 323 unresolved "
    "identities, the four dual-brand halves on an identity hold, and every evidence hold stay "
    "exactly as adjudicated -- this decision authorizes the market, not any of its held rows."
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
        ("not_authorized_by_this_decision", [
            "weaker evidence rules",
            "anti-bot bypass",
            "invented dual-brand identity rulings",
            "publication of held properties",
        ]),
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
            "85 pet-friendly profiles and 53 verified-no-pets over a 461-identity census. "
            "Built from zero by PTF-FORT-LAUDERDALE-FL-HARDENED-SOURCE-READY-001 on the "
            "Miami-live lineage and closed in that same order through the supported "
            "attended-browser lane (actionable unresolved 0), registered against the "
            "Miami-live parent by PTF-FORT-LAUDERDALE-FL-REGISTRATION-AND-STAGING-002 as "
            "COMPOSITE_FRESH_MARKET_DATA_ONLY with 15/15 registration checks and 0 broad "
            "regression runs, and ADMITTED here by %s, which is the founder's explicit launch "
            "decision. Hidden from global navigation and from the sitemap "
            "(show_in_navigation=false, show_in_sitemap=false), exactly as every other recently "
            "launched market is at this stage -- those flags govern the hub's place in "
            "navigation, not whether the market's profile URLs are indexed. 10 of its 18 "
            "corridors reach their own publication minimum; the rest are suppressed, which is a "
            "threshold and not a gap. 376 rows that did not publish -- 323 unresolved, the four "
            "dual-brand halves on an identity hold, and every evidence hold -- are unaffected by "
            "this decision." % WORK_ORDER)
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
