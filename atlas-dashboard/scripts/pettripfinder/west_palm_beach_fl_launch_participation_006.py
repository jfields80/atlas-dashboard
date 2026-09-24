"""PTF-WEST-PALM-BEACH-FL-FOUNDER-LAUNCH-AUTHORIZATION-006 -- the founder's NEW
West Palm Beach launch decision, for the CORRECTED package.

    python -m scripts.pettripfinder.west_palm_beach_fl_launch_participation_006
    python -m scripts.pettripfinder.west_palm_beach_fl_launch_participation_006 --write

THIS RECORDS A DECISION, IT DOES NOT MAKE ONE
---------------------------------------------
The founder granted it in this order, explicitly: "The founder explicitly grants a NEW
launch authorization for the corrected West Palm Beach package ... Authorize the corrected
West Palm Beach publication cohort. The Hilton Garden Inn Boca Raton identity correction has
been reviewed and accepted. The superseded package/authorization does not carry forward."
This module writes that decision down. It must never be run to admit a market on its own
initiative.

A NEW DECISION, NOT THE OLD ONE RESTORED
-----------------------------------------
PTF-WEST-PALM-BEACH-FL-FOUNDER-LAUNCH-AUTHORIZATION-003 authorized package 789c0187. A
pre-deploy identity correction replaced those bytes; PTF-WEST-PALM-BEACH-FL-CORRECTED-
REREGISTRATION-005 recorded a package-bound ``founder_authorization_superseded`` entry and
returned the row to SOURCE_READY. That entry stays exactly where it was written -- in the
005 decision, which this decision's lineage carries forward with its sha256 and the
superseded market id. It is NOT copied into this block: this block authorizes West Palm
Beach again, and a supersession entry for an authorized market is a contradiction the chain
refuses. The history this decision rests on is instead recorded in ``decision_basis``
(``reauthorizes_after_supersession``) -- the superseding decision, both package digests and
every superseded deployment authorization -- so a reader can see what did NOT carry forward.

THE BASIS IS DERIVED, NEVER TYPED
----------------------------------
Every number and digest in ``decision_basis`` is read at run time from the committed
authority, the committed re-registration readiness packet and the committed receipt. The
record is NOT an authority: the assembler re-derives all of it.

THE CHAIN IS EXTENDED, NOT REWRITTEN (``launch_participation.extend_decision``).
NO OTHER MARKET MOVES.
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

WORK_ORDER = "PTF-WEST-PALM-BEACH-FL-FOUNDER-LAUNCH-AUTHORIZATION-006"
MARKET = "west-palm-beach-fl"
DECIDED_ON = "2026-09-24"
FOUNDER_PACKET = "PTF-REREGISTRATION-TRUSTED-FACTORY-BASELINE-CORRECTION-002"
PACKAGE = _REPO_ROOT / "launch_packages" / "pettripfinder"
REPORTS = PACKAGE / "markets" / "reports"
FOUNDER_PACKET_PATH = REPORTS / "west_palm_beach_fl_registration_authorization_readiness.json"
REREGISTRATION_REPORT_PATH = REPORTS / "west_palm_beach_fl_reregistration_participation.json"
PATH = LP.PARTICIPATION_PATH

FOUNDER_WORDS = (
    "The founder explicitly grants a NEW launch authorization for the corrected West Palm Beach "
    "package. ... Authorize the corrected West Palm Beach publication cohort. The Hilton Garden Inn "
    "Boca Raton identity correction has been reviewed and accepted. The superseded "
    "package/authorization does not carry forward.")


def _sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rel(path: Path) -> str:
    return str(path.relative_to(_REPO_ROOT)).replace("\\", "/")


def _load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=OrderedDict)


def _packet() -> Dict:
    packet = _load(FOUNDER_PACKET_PATH)
    if packet.get("status") != "AUTHORIZATION_READY" or packet.get("market_id") != MARKET:
        raise SystemExit("%s: the readiness packet is %r for %r, not AUTHORIZATION_READY for %s"
                         % (WORK_ORDER, packet.get("status"), packet.get("market_id"), MARKET))
    rv2 = packet["regression_v2"]
    if rv2.get("CHANGE_CLASS") != "AUTHORIZED_NONLIVE_MARKET_REREGISTRATION_DATA_ONLY" \
            or rv2.get("FULL_REGRESSION_REQUIRED") != "NO" or packet["registration_proof"].get("ELIGIBLE") != "YES":
        raise SystemExit("%s: the readiness packet is not an eligible narrow re-registration" % WORK_ORDER)
    if (packet.get("reregistration") or {}).get("old_authorizations_authorize_the_corrected_package") is not False:
        raise SystemExit("%s: the packet does not state that the old authorization transfers nothing" % WORK_ORDER)
    return packet


def _basis(packet: Dict, prior: Dict) -> Dict:
    """What the founder was shown, read from committed state at run time."""
    census_path = PACKAGE / "identity_census" / ("%s.json" % MARKET)
    policy_path = PACKAGE / ("hotel_policy_facts_%s.json" % MARKET)
    shard_path = PACKAGE / "markets" / "authority" / MARKET / "hotel_exclusions.json"
    contract_path = _REPO_ROOT / "deploy" / "netlify" / "release_contracts" / ("%s.json" % MARKET)
    census, policy, shard = _load(census_path), _load(policy_path), _load(shard_path)
    no_pets = sum(1 for e in shard["exclusions"] if e["exclusion_state"] == "VERIFIED_NO_PETS")
    binds = packet["the_digests_this_readiness_binds"]
    rv2 = packet["regression_v2"]
    rereg = packet["reregistration"]
    superseding = prior["decision"]
    entries = superseding.get(LP.FOUNDER_AUTHORIZATION_SUPERSEDED) or []
    if len(entries) != 1 or entries[0].get("market_id") != MARKET:
        raise SystemExit("%s: the current decision is not %s's package-bound supersession" % (WORK_ORDER, MARKET))
    entry = entries[0]
    if entry["corrected_package_digest"] != binds["sealed_package_digest"]:
        raise SystemExit("%s: the supersession's corrected package %s is not the packet's %s"
                         % (WORK_ORDER, entry["corrected_package_digest"], binds["sealed_package_digest"]))
    hotels = policy["hotels"]
    names = [h.get("canonical_name") or h.get("name") for h in hotels]

    def entry_of(path: Path) -> Dict:
        return OrderedDict((("path", _rel(path)), ("sha256", _sha256_of(path))))

    return OrderedDict((
        ("what_this_is",
         "What the founder was shown when deciding. These are a RECORD of the basis, not an "
         "authority: the assembler derives every one of them from the market's own census, "
         "package, shard and release contract, and a status that disagrees with the source fails "
         "the build."),
        ("market_id", MARKET),
        ("founder_authorization_packet", FOUNDER_PACKET),
        ("founder_authorization_packet_document", entry_of(FOUNDER_PACKET_PATH)),
        ("founder_words", FOUNDER_WORDS),
        ("parent_deploy_id", binds["parent_live_deploy_id"]),
        ("parent_release_digest", binds["parent_release_digest"]),
        ("registered_package_id", binds["sealed_package_id"]),
        ("registered_package_digest", binds["sealed_package_digest"]),
        ("fast_receipt", binds["fast_receipt"]),
        ("fast_receipt_digest", binds["fast_receipt_digest"]),
        ("market_bundle_sha256", binds["changed_market_bundle_sha256"]),
        ("registration_class", rv2["CHANGE_CLASS"]),
        ("registration_base", rv2["registration_base"]),
        ("trusted_factory_baseline", rv2.get("trusted_factory_baseline")),
        ("census_count", census["count"]),
        ("pet_friendly_publication_count", len(hotels)),
        ("verified_no_pets_count", no_pets),
        ("holds_unresolved", census["count"] - len(hotels) - no_pets),
        ("actionable_unresolved_remaining", 0),
        ("identity_correction_accepted", OrderedDict((
            ("corrected_name", "Hilton Garden Inn Boca Raton"),
            ("property_code", "bctbrgi"),
            ("published", "Hilton Garden Inn Boca Raton" in names),
            ("erroneous_name_absent", not any("apple ten" in str(n).lower() for n in names)),
        ))),
        ("reauthorizes_after_supersession", OrderedDict((
            ("superseding_decision", OrderedDict((("work_order", superseding["work_order"]),
                                                  ("sha256", LP.participation_sha256(PATH))))),
            ("superseded_founder_decision", entry["authorizing_decision"]),
            ("superseded_package_digest", entry["superseded_package_digest"]),
            ("corrected_package_digest", entry["corrected_package_digest"]),
            ("superseded_deployment_authorizations", entry["deployment_authorizations"]),
            ("old_authorizations_authorize_this_package", rereg["old_authorizations_authorize_the_corrected_package"]),
        ))),
        ("not_authorized_by_this_decision", [
            "the superseded package or any authorization of it",
            "weaker evidence rules",
            "weaker identity standards",
            "anti-bot bypass",
            "publication of held properties",
        ]),
        ("policy_package", entry_of(policy_path)),
        ("exclusion_shard", entry_of(shard_path)),
        ("release_contract", entry_of(contract_path)),
        ("identity_census", entry_of(census_path)),
    ))


def flip(write: bool = False) -> Dict:
    prior_bytes = PATH.read_bytes()
    prior = json.loads(prior_bytes.decode("utf-8-sig"), object_pairs_hook=OrderedDict)
    previous_sha = LP.participation_sha256(PATH)
    packet = _packet()
    authorized_before = LP.authorized_market_ids(prior)
    if MARKET in authorized_before:
        raise SystemExit("%s: %s is already authorized" % (WORK_ORDER, MARKET))
    if LP.launch_status(MARKET, prior) != LP.SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH:
        raise SystemExit("%s: %s reads %s" % (WORK_ORDER, MARKET, LP.launch_status(MARKET, prior)))
    basis = _basis(packet, prior)
    if not basis["identity_correction_accepted"]["published"] \
            or not basis["identity_correction_accepted"]["erroneous_name_absent"]:
        raise SystemExit("%s: the corrected identity is not what the policy package publishes" % WORK_ORDER)

    document = json.loads(prior_bytes.decode("utf-8-sig"), object_pairs_hook=OrderedDict)
    hit = 0
    for market in document["markets"]:
        if market["market_id"] != MARKET:
            continue
        hit += 1
        market["launch_status"] = LP.FOUNDER_AUTHORIZED_FOR_LAUNCH
        market["note"] = (
            "%d pet-friendly profiles and %d verified-no-pets over a %d-identity census. Re-registered after "
            "a pre-deploy identity correction (Hilton Garden Inn Boca Raton, bctbrgi, replacing a DBPR "
            "licensee name) by PTF-WEST-PALM-BEACH-FL-CORRECTED-REREGISTRATION-005 and %s as "
            "AUTHORIZED_NONLIVE_MARKET_REREGISTRATION_DATA_ONLY (17/17, 0 broad runs), and ADMITTED here by %s, "
            "the founder's NEW launch decision for corrected package %s. The superseded package %s and its "
            "deployment authorization authorize nothing. Hidden from global navigation and from the sitemap "
            "flags exactly as every recently launched market is at this stage."
            % (basis["pet_friendly_publication_count"], basis["verified_no_pets_count"], basis["census_count"],
               FOUNDER_PACKET, WORK_ORDER, basis["registered_package_digest"][:23],
               basis["reauthorizes_after_supersession"]["superseded_package_digest"][:23]))
    if hit != 1:
        raise SystemExit("%s: expected exactly one %s row, found %d" % (WORK_ORDER, MARKET, hit))

    reason = (
        "Founder authorizes West Palm Beach to participate in the next production assembly as the "
        "THIRTY-THIRD market, on the CORRECTED package %s (market bundle %s). This is a NEW decision: the "
        "founder authorization of package %s (%s) was superseded by %s before any deployment, and neither it "
        "nor deployment authorization(s) %s carry forward. Bound to the re-registration readiness packet %s "
        "(%s), itself bound to the current live parent (deploy %s, release-index digest %s). Founder's words: "
        "'%s' Every other market's decision is unchanged, and every other waiting market remains NOT "
        "authorized for launch."
        % (basis["registered_package_digest"], basis["market_bundle_sha256"],
           basis["reauthorizes_after_supersession"]["superseded_package_digest"],
           basis["reauthorizes_after_supersession"]["superseded_founder_decision"]["work_order"],
           basis["reauthorizes_after_supersession"]["superseding_decision"]["work_order"],
           [a["authorization_id"] for a in basis["reauthorizes_after_supersession"]["superseded_deployment_authorizations"]],
           FOUNDER_PACKET, _rel(FOUNDER_PACKET_PATH), basis["parent_deploy_id"], basis["parent_release_digest"],
           FOUNDER_WORDS))
    document["decision"] = LP.extend_decision(
        prior, previous_sha, work_order=WORK_ORDER, decided_by="founder", decided_on=DECIDED_ON,
        reason=reason, path=PATH, decision_basis=basis)

    authorized_after = LP.authorized_market_ids(document)
    gained = sorted(set(authorized_after) - set(authorized_before))
    lost = sorted(set(authorized_before) - set(authorized_after))
    if gained != [MARKET] or lost:
        raise SystemExit("%s: the flip must add exactly %s and remove nothing; gained %s, lost %s"
                         % (WORK_ORDER, MARKET, gained, lost))
    other_rows = [m for m in document["markets"] if m["market_id"] != MARKET]
    if other_rows != [m for m in prior["markets"] if m["market_id"] != MARKET]:
        raise SystemExit("%s: another market's row moved" % WORK_ORDER)
    new_bytes = (json.dumps(document, indent=1, ensure_ascii=False) + "\n").encode("utf-8")
    if write:
        PATH.write_bytes(new_bytes)
        problems = LP.decision_problems(json.loads(new_bytes.decode("utf-8")), PATH)
        if problems:
            PATH.write_bytes(prior_bytes)
            raise SystemExit("%s: decision_problems %s -- the prior record was restored" % (WORK_ORDER, problems))
    return OrderedDict((("work_order", WORK_ORDER), ("written", write),
                        ("markets_before", len(authorized_before)), ("markets_after", len(authorized_after)),
                        ("gained", gained), ("lost", lost), ("previous_record_sha256", previous_sha),
                        ("lineage_records", len(document["decision"]["lineage"]["records"])),
                        ("supersedes", document["decision"]["supersedes"]),
                        ("decision_basis", basis)))


if __name__ == "__main__":
    result = flip(write="--write" in sys.argv)
    print(json.dumps({k: result[k] for k in ("markets_before", "markets_after", "gained", "lost", "written",
                                             "previous_record_sha256", "lineage_records", "supersedes")},
                     indent=1))
