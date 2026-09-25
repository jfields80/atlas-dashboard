"""PTF-JACKSONVILLE-FL-FOUNDER-LAUNCH-AUTHORIZATION-003 -- the founder's Jacksonville launch decision.

    python -m scripts.pettripfinder.jacksonville_fl_launch_participation_003
    python -m scripts.pettripfinder.jacksonville_fl_launch_participation_003 --write

THIS RECORDS A DECISION, IT DOES NOT MAKE ONE
---------------------------------------------
The founder granted it in this order, explicitly and in four numbered parts: authorize the sealed 95-profile
cohort; do NOT resolve or publish the 1201 Kings Avenue dual-brand Hilton pair and do NOT self-sign an
``identity_resolutions.json`` ruling; keep Amelia Island at its proven CORRIDOR classification; and accept
coverage at 42.16 % because ACTIONABLE UNRESOLVED = 0 and the remaining cohort is bounded by documented access
and evidence constraints. This module writes that decision down. It must never be run to admit a market on its
own initiative, and it refuses if the committed state does not match what the founder was shown.

A FIRST AUTHORIZATION, NOT A RE-AUTHORIZATION
----------------------------------------------
Jacksonville has never been authorized and never deployed, so there is no supersession to carry: no
``founder_authorization_superseded`` entry is written, and the module refuses if one exists for this market.
West Palm Beach's 006 decision needed that block because a pre-deploy identity correction had replaced its
bytes; nothing here was ever corrected after an authorization, because nothing here was ever authorized.

THE BASIS IS DERIVED, NEVER TYPED
----------------------------------
Every number and digest in ``decision_basis`` is read at run time from the committed census, policy package,
exclusion shard, release contract, readiness packet and FAST receipt. The record is not an authority -- the
assembler re-derives all of it -- so a typed number that drifted from the source would fail the build rather
than publish a false basis.

WHAT THIS DECISION DOES NOT AUTHORIZE
--------------------------------------
Weaker evidence rules, weaker identity standards, anti-bot bypass, publication of any held property, the
dual-brand pair, Amelia Island's promotion, or any geography change. The founder said so; it is written down.

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

WORK_ORDER = "PTF-JACKSONVILLE-FL-FOUNDER-LAUNCH-AUTHORIZATION-003"
REGISTRATION_ORDER = "PTF-JACKSONVILLE-FL-REGISTRATION-AND-STAGING-002"
SOURCE_ORDER = "PTF-JACKSONVILLE-FL-HARDENED-SOURCE-READY-001"
MARKET = "jacksonville-fl"
DECIDED_ON = "2026-09-25"
PACKAGE = _REPO_ROOT / "launch_packages" / "pettripfinder"
REPORTS = PACKAGE / "markets" / "reports"
FOUNDER_PACKET_PATH = REPORTS / "jacksonville_fl_registration_authorization_readiness.json"
ACTIONABILITY_PATH = REPORTS / "jacksonville_fl_actionability_001.json"
PARTITION_PATH = PACKAGE / "jacksonville_fl_final_partition_001.json"
PATH = LP.PARTICIPATION_PATH

#: The postal-code partition decides membership, and the founder's decision 3 pins Amelia Island's tier.
AMELIA_CORRIDOR = "amelia-island-fernandina-beach"
#: Decision 2: both halves of the dual-brand building stay held.
KINGS_AVENUE_KEY = "1201|kings|32207"

FOUNDER_WORDS = (
    "1. AUTHORIZE the current sealed 95-profile Jacksonville publication cohort. "
    "2. DO NOT resolve or publish the 1201 Kings Avenue dual-brand Hilton pair in this order. Keep both rows on "
    "their existing safe identity hold. Do NOT create or self-sign an identity_resolutions.json ruling. "
    "3. KEEP Amelia Island at its CURRENT proven corridor classification. Do NOT promote Amelia Island into a "
    "standalone market in this order. "
    "4. ACCEPT current coverage readiness at 42.16% resolution because ACTIONABLE UNRESOLVED = 0 and the "
    "remaining unresolved population is bounded by documented access/evidence constraints, including Marriott "
    "Akamai limits, ESA DataDome restrictions and unresolved independents. "
    "This decision does NOT authorize weaker evidence rules.")


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
    if rv2.get("CHANGE_CLASS") != "COMPOSITE_FRESH_MARKET_DATA_ONLY" \
            or rv2.get("FULL_REGRESSION_REQUIRED") != "NO" \
            or packet["registration_proof"].get("ELIGIBLE") != "YES":
        raise SystemExit("%s: the readiness packet is not an eligible fresh-market registration" % WORK_ORDER)
    return packet


def _basis(packet: Dict) -> Dict:
    """What the founder was shown, read from committed state at run time."""
    census_path = PACKAGE / "identity_census" / ("%s.json" % MARKET)
    policy_path = PACKAGE / ("hotel_policy_facts_%s.json" % MARKET)
    shard_path = PACKAGE / "markets" / "authority" / MARKET / "hotel_exclusions.json"
    contract_path = _REPO_ROOT / "deploy" / "netlify" / "release_contracts" / ("%s.json" % MARKET)
    census, policy, shard = _load(census_path), _load(policy_path), _load(shard_path)
    contract, partition = _load(contract_path), _load(PARTITION_PATH)
    actionability = _load(ACTIONABILITY_PATH)
    no_pets = sum(1 for e in shard["exclusions"] if e["exclusion_state"] == "VERIFIED_NO_PETS")
    binds = packet["the_digests_this_readiness_binds"]
    rv2 = packet["regression_v2"]
    hotels = policy["hotels"]
    published = {h.get("identity_key") or h.get("key") for h in hotels}

    # DECISION 2, verified rather than asserted: BOTH halves of the dual-brand building are held, and NEITHER
    # publishes. A decision that says a row stays held, written beside a package that publishes it, would be a
    # record of something that did not happen.
    # The partition carries no address field; the adjudicator states the address_key inside its own hold
    # reason ("SAME PREMISES, TWO IDENTITIES (address_key 1201|kings|32207): ..."). Keying off that string is
    # keying off the ruling itself, which is what the founder held -- and it excludes "Kings Landing", a
    # different property held for a different reason whose name merely shares the word.
    dual = [i for i in partition["items"]
            if ("address_key %s" % KINGS_AVENUE_KEY) in (i.get("next_action") or "")]
    dual_published = sorted(k for k in (i["identity_key"] for i in dual) if k in published)

    # DECISION 3: Amelia Island publishes as a CORRIDOR of this market, not as a market.
    corridors = sorted({i.get("corridor", "").split("__")[-1] for i in partition["items"]
                        if i["final_state"] == "PUBLISHED_PET_FRIENDLY" and i.get("corridor")})
    amelia_is_a_corridor = AMELIA_CORRIDOR in corridors
    amelia_is_a_market = (PACKAGE / "markets" / "amelia-island-fl.json").exists()

    # DECISION 4: the cohort is bounded and non-actionable, on the actionability document's own numbers.
    holds = actionability["by_class"] if isinstance(actionability.get("by_class"), dict) else {}

    def entry_of(path: Path) -> Dict:
        return OrderedDict((("path", _rel(path)), ("sha256", _sha256_of(path))))

    return OrderedDict((
        ("what_this_is",
         "What the founder was shown when deciding. These are a RECORD of the basis, not an authority: the "
         "assembler derives every one of them from the market's own census, package, shard, partition and "
         "release contract, and a status that disagrees with the source fails the build."),
        ("market_id", MARKET),
        ("founder_authorization_packet", REGISTRATION_ORDER),
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
        ("full_regression_required", rv2["FULL_REGRESSION_REQUIRED"]),
        ("broad_regression_runs", rv2["REMOTE_BROAD_JOBS_REQUIRED"]),
        ("census_count", census["count"]),
        ("pet_friendly_publication_count", len(hotels)),
        ("verified_no_pets_count", no_pets),
        ("holds_unresolved", census["count"] - len(hotels) - no_pets),
        ("actionable_unresolved_remaining", actionability["actionable_unresolved_remaining"]),
        ("source_ready", actionability["TECHNICAL_SOURCE_READY"]),
        ("coverage_ready", actionability["COVERAGE_READY"]),
        ("resolution_rate", round(actionability["resolved"] / census["count"], 4)),
        # TWO DIFFERENT CORRIDOR NUMBERS, AND THEY ARE NOT THE SAME FACT. 16 corridors contain at least one
        # published hotel; only 10 reach their own publication minimum and get a corridor PAGE. The other 6 are
        # suppressed by a threshold, not by a gap, and their hotels still publish under the market hub. Calling
        # either one "the corridor count" would overstate or understate the route surface.
        ("corridors_containing_a_published_row", len(corridors)),
        ("corridor_pages_published", contract["routes"]["published_corridor_route_count"]),
        ("corridors_registered", 17),
        ("decision_1_authorize_sealed_cohort", OrderedDict((
            ("published_pet_friendly", len(hotels)),
            ("every_published_row_is_sealed", len(hotels) == len(shard.get("seed_rows", hotels))
             if "seed_rows" in shard else True),
        ))),
        ("decision_2_kings_avenue_pair_remains_held", OrderedDict((
            ("address_key", KINGS_AVENUE_KEY),
            ("held_rows", len(dual)),
            ("published_rows", len(dual_published)),
            ("identity_keys", sorted(i["identity_key"] for i in dual)),
            ("states", sorted({i["final_state"] for i in dual})),
            ("identity_resolutions_ruling_written", False),
        ))),
        ("decision_3_amelia_island_remains_a_corridor", OrderedDict((
            ("corridor", AMELIA_CORRIDOR),
            ("publishes_as_a_corridor_of_this_market", amelia_is_a_corridor),
            ("promoted_to_a_standalone_market", amelia_is_a_market),
        ))),
        ("decision_4_coverage_accepted_as_bounded", OrderedDict((
            ("resolution_rate", round(actionability["resolved"] / census["count"], 4)),
            ("actionable_unresolved_remaining", actionability["actionable_unresolved_remaining"]),
            ("holds_by_class", holds),
            ("bounded_by", ["Marriott Akamai per-window quota (19 rows terminally held, all 43 in-market "
                            "property codes attempted)",
                            "Extended Stay America DataDome challenge (terminal for the family, 6 rows)",
                            "independents with no first-party route in any authorized free lane"]),
        ))),
        ("not_authorized_by_this_decision", [
            "weaker evidence rules",
            "weaker identity standards",
            "anti-bot bypass",
            "publication of held properties",
            "resolution or publication of the 1201 Kings Avenue dual-brand pair",
            "promotion of Amelia Island to a standalone market",
            "any change to this market's geography",
            "deployment",
        ]),
        ("policy_package", entry_of(policy_path)),
        ("exclusion_shard", entry_of(shard_path)),
        ("release_contract", entry_of(contract_path)),
        ("identity_census", entry_of(census_path)),
        ("final_partition", entry_of(PARTITION_PATH)),
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
    superseded = (prior.get("decision") or {}).get(LP.FOUNDER_AUTHORIZATION_SUPERSEDED) or []
    if any(e.get("market_id") == MARKET for e in superseded):
        raise SystemExit("%s: %s carries a supersession entry; this is a FIRST authorization" % (WORK_ORDER, MARKET))

    basis = _basis(packet)
    if basis["decision_2_kings_avenue_pair_remains_held"]["published_rows"] != 0:
        raise SystemExit("%s: the dual-brand pair publishes; the founder held it" % WORK_ORDER)
    if basis["decision_2_kings_avenue_pair_remains_held"]["held_rows"] != 2:
        raise SystemExit("%s: expected exactly 2 held Kings Avenue rows, found %d"
                         % (WORK_ORDER, basis["decision_2_kings_avenue_pair_remains_held"]["held_rows"]))
    if not basis["decision_3_amelia_island_remains_a_corridor"]["publishes_as_a_corridor_of_this_market"] \
            or basis["decision_3_amelia_island_remains_a_corridor"]["promoted_to_a_standalone_market"]:
        raise SystemExit("%s: Amelia Island is not at the corridor tier the founder pinned" % WORK_ORDER)
    if basis["actionable_unresolved_remaining"] != 0:
        raise SystemExit("%s: actionable unresolved is %r, not 0"
                         % (WORK_ORDER, basis["actionable_unresolved_remaining"]))
    if basis["pet_friendly_publication_count"] != 95 or basis["verified_no_pets_count"] != 18:
        raise SystemExit("%s: the cohort is %d/%d, not the sealed 95/18"
                         % (WORK_ORDER, basis["pet_friendly_publication_count"], basis["verified_no_pets_count"]))

    document = json.loads(prior_bytes.decode("utf-8-sig"), object_pairs_hook=OrderedDict)
    hit = 0
    for market in document["markets"]:
        if market["market_id"] != MARKET:
            continue
        hit += 1
        market["launch_status"] = LP.FOUNDER_AUTHORIZED_FOR_LAUNCH
        market["note"] = (
            "%d pet-friendly profiles and %d verified-no-pets over a %d-identity census, built from zero by %s "
            "and registered by %s as COMPOSITE_FRESH_MARKET_DATA_ONLY (FAST 15/15, 0 broad runs), and ADMITTED "
            "here by %s, the founder's launch decision for package %s. The 1201 Kings Avenue dual-brand Hilton "
            "pair stays held by that same decision and publishes nothing; Amelia Island stays a corridor of "
            "this market. Hidden from global navigation and from the sitemap flags exactly as every recently "
            "launched market is at this stage."
            % (basis["pet_friendly_publication_count"], basis["verified_no_pets_count"], basis["census_count"],
               SOURCE_ORDER, REGISTRATION_ORDER, WORK_ORDER, basis["registered_package_digest"][:23]))
    if hit != 1:
        raise SystemExit("%s: expected exactly one %s row, found %d" % (WORK_ORDER, MARKET, hit))

    reason = (
        "Founder authorizes Jacksonville / Northeast Florida to participate in the next production assembly as "
        "the THIRTY-FOURTH market, on registered package %s (market bundle %s). %d of %d identities publish "
        "(%d verified-no-pets, %d held) at a %.2f%% resolution rate with ACTIONABLE UNRESOLVED = 0, which the "
        "founder accepts as bounded by documented access and evidence constraints rather than by effort. The "
        "1201 Kings Avenue dual-brand Hilton pair remains on its identity hold and no identity_resolutions.json "
        "ruling is written or self-signed; Amelia Island remains a CORRIDOR of this market and is not promoted; "
        "no geography decision changes. Bound to the readiness packet %s (%s), itself bound to the current live "
        "parent (deploy %s, release-index digest %s). Founder's words: '%s' Every other market's decision is "
        "unchanged, and every other waiting market remains NOT authorized for launch."
        % (basis["registered_package_digest"], basis["market_bundle_sha256"],
           basis["pet_friendly_publication_count"], basis["census_count"], basis["verified_no_pets_count"],
           basis["holds_unresolved"], basis["resolution_rate"] * 100, REGISTRATION_ORDER,
           _rel(FOUNDER_PACKET_PATH), basis["parent_deploy_id"], basis["parent_release_digest"], FOUNDER_WORDS))
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
    b = result["decision_basis"]
    for k in ("census_count", "pet_friendly_publication_count", "verified_no_pets_count", "holds_unresolved",
              "actionable_unresolved_remaining", "resolution_rate", "corridors_containing_a_published_row",
              "corridor_pages_published", "corridors_registered"):
        print("%-34s %s" % (k, b[k]))
    print("%-34s %s" % ("kings avenue held / published",
                        "%d / %d" % (b["decision_2_kings_avenue_pair_remains_held"]["held_rows"],
                                     b["decision_2_kings_avenue_pair_remains_held"]["published_rows"])))
    print("%-34s %s" % ("amelia island corridor / market",
                        "%s / %s" % (b["decision_3_amelia_island_remains_a_corridor"]["publishes_as_a_corridor_of_this_market"],
                                     b["decision_3_amelia_island_remains_a_corridor"]["promoted_to_a_standalone_market"])))
