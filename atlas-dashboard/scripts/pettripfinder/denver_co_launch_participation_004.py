"""PTF-DENVER-CO-FOUNDER-LAUNCH-AUTHORIZATION-004 -- the founder's Denver launch decision.

    python -m scripts.pettripfinder.denver_co_launch_participation_004
    python -m scripts.pettripfinder.denver_co_launch_participation_004 --write

THIS RECORDS A DECISION, IT DOES NOT MAKE ONE
---------------------------------------------
The founder granted it in this conversation, explicitly and in these words:

    AUTHORIZE: pkg-denver-co-07f10db29ab56d98
    DO NOT AUTHORIZE: pkg-denver-co-91b2e0a2

That package is the corrected 288-profile Denver cohort (PTF-DENVER-CO-PREAUTH-PREOPENING-CORRECTION-003), whose
coverage the founder approved (denver_co_founder_coverage_decision_003.json): 288 pet-friendly profiles and 46
verified-no-pets exclusions publish; the 52 no-website rows, the 16 founder-decision rows (seven dual-brand
buildings and the two ESA title-collision rows), the 38 router-exhausted rows and the not-yet-open ECHO Suites
Thornton row stay unpublished. This module writes that decision down. It must never be run to admit a market on
its own initiative, and it refuses if the committed state does not match what the founder was shown -- in
particular, if the readiness packet binds any package other than pkg-denver-co-07f10db29ab56d98, or binds the
superseded pkg-denver-co-91b2e0a2.

A FIRST AUTHORIZATION, NOT A RE-AUTHORIZATION
----------------------------------------------
Denver has never been authorized and never deployed, so no ``founder_authorization_superseded`` entry is written,
and the module refuses if one exists for this market.

THE BASIS IS DERIVED, NEVER TYPED
----------------------------------
Every number and digest in ``decision_basis`` is read at run time from the committed census, policy package,
exclusion shard, release contract, final partition, actionability, clean-authority and coverage-decision reports,
readiness packet and FAST receipt. Each founder decision is a GUARD: if the committed state disagrees with it,
nothing is written.

THE CHAIN IS EXTENDED, NOT REWRITTEN (``launch_participation.extend_decision``).
NO OTHER MARKET MOVES.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import launch_participation as LP     # noqa: E402

WORK_ORDER = "PTF-DENVER-CO-FOUNDER-LAUNCH-AUTHORIZATION-004"
CORRECTION_ORDER = "PTF-DENVER-CO-PREAUTH-PREOPENING-CORRECTION-003"
REGISTRATION_ORDER = "PTF-DENVER-CO-REGISTRATION-AND-STAGING-002"
SOURCE_ORDER = "PTF-DENVER-CO-HARDENED-SOURCE-READY-001"
MARKET = "denver-co"
DECIDED_ON = "2026-09-28"
PACKAGE = _REPO_ROOT / "launch_packages" / "pettripfinder"
REPORTS = PACKAGE / "markets" / "reports"
FOUNDER_PACKET_PATH = REPORTS / "denver_co_registration_authorization_readiness.json"
ACTIONABILITY_PATH = REPORTS / "denver_co_actionability_001.json"
CLEAN_PATH = REPORTS / "denver_co_clean_authority_001.json"
COVERAGE_DECISION_PATH = REPORTS / "denver_co_founder_coverage_decision_003.json"
PARTITION_PATH = PACKAGE / "denver_co_final_partition_001.json"
PATH = LP.PARTICIPATION_PATH

#: The package the founder authorized, and the one the founder refused, exactly as stated.
AUTHORIZED_PACKAGE_ID = "pkg-denver-co-07f10db29ab56d98"
REFUSED_PACKAGE_PREFIX = "pkg-denver-co-91b2e0a2"

#: The approved cohort and the held groups, as the corrected coverage decision states them.
COHORT_PET_FRIENDLY = 288
COHORT_VERIFIED_NO_PETS = 46
HELD_NO_WEBSITE = 52
HELD_FOUNDER = 16
HELD_DUAL_BRAND = 14
HELD_ESA_TITLE = 2
HELD_ROUTER_EXHAUSTED = 38
HELD_PREOPENING = 1
#: Each dual-brand building is TWO hotels held on one address_key the adjudicator states in its own hold reason.
DUAL_BRAND_KEYS = ("455|zang|80021", "620|federal|80204", "5980|tower|80249", "550|15th|80202",
                   "2556|oswego|80010", "6951|yampa|80249", "9231|arapahoe|80112")
PREOPENING_KEY = "echo suites denver north thornton opening early 2027"

FOUNDER_WORDS = "AUTHORIZE: pkg-denver-co-07f10db29ab56d98. DO NOT AUTHORIZE: pkg-denver-co-91b2e0a2."

_AMOUNT = re.compile(r"\$\s*([0-9]+(?:\.[0-9]{1,2})?)|([0-9]+(?:\.[0-9]{1,2})?)\s*USD")


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
    bound = packet["the_digests_this_readiness_binds"]["sealed_package_id"]
    if bound != AUTHORIZED_PACKAGE_ID or bound.startswith(REFUSED_PACKAGE_PREFIX):
        raise SystemExit("%s: the readiness packet binds %r; the founder authorized %s and refused %s"
                         % (WORK_ORDER, bound, AUTHORIZED_PACKAGE_ID, REFUSED_PACKAGE_PREFIX))
    return packet


def _basis(packet: Dict) -> Dict:
    """What the founder was shown, read from committed state at run time."""
    census_path = PACKAGE / "identity_census" / ("%s.json" % MARKET)
    policy_path = PACKAGE / ("hotel_policy_facts_%s.json" % MARKET)
    shard_path = PACKAGE / "markets" / "authority" / MARKET / "hotel_exclusions.json"
    contract_path = _REPO_ROOT / "deploy" / "netlify" / "release_contracts" / ("%s.json" % MARKET)
    census, policy, shard = _load(census_path), _load(policy_path), _load(shard_path)
    contract, partition = _load(contract_path), _load(PARTITION_PATH)
    actionability, coverage, clean = _load(ACTIONABILITY_PATH), _load(COVERAGE_DECISION_PATH), _load(CLEAN_PATH)
    no_pets = sum(1 for e in shard["exclusions"] if e["exclusion_state"] == "VERIFIED_NO_PETS")
    binds = packet["the_digests_this_readiness_binds"]
    rv2 = packet["regression_v2"]
    hotels = policy["hotels"]
    published = {h.get("identity_key") or h.get("key") for h in hotels}
    excluded = {e.get("identity_key") or e.get("normalized_name") for e in shard["exclusions"]}

    # Every held group is taken from the actionability document's own per-row classes, and every group is
    # checked against the published cohort: a decision that says a row stays held, written beside a package
    # that publishes it, would be a record of something that did not happen.
    rows = actionability["rows"]
    no_website = [r["identity_key"] for r in rows if r["actionability"] == "REQUIRES_NEW_SPEND"]
    founder_rows = [r["identity_key"] for r in rows if r["actionability"] == "REQUIRES_FOUNDER"]
    exhausted = [r["identity_key"] for r in rows if r["actionability"] == "AUTHORIZED_ROUTER_EXHAUSTED"]
    preopening = [r["identity_key"] for r in rows if r["actionability"] == "HELD_UNTIL_OPENING"]
    esa_title = [r["identity_key"] for r in rows
                 if r["actionability"] == "REQUIRES_FOUNDER" and "title" in (r.get("why") or "")]
    # The dual-brand pairs by the adjudicator's own address_key inside the hold reason -- never by a word in a name.
    dual = [i for i in partition["items"]
            if any(("address_key %s" % k) in (i.get("next_action") or "") for k in DUAL_BRAND_KEYS)]
    by_key = Counter(k for i in dual for k in DUAL_BRAND_KEYS if ("address_key %s" % k) in (i.get("next_action") or ""))
    preopening_held = [p["identity_key"] for p in clean.get("preopening_held") or ()]

    # Fee safety: a published record whose own quote states more than one amount carries no single fee.
    multi_amount, multi_with_fee = 0, []
    for h in hotels:
        quotes = " ".join(e.get("quote", "") for e in h.get("evidence", []))
        amounts = {float(a or b) for a, b in _AMOUNT.findall(quotes)}
        if len(amounts) > 1:
            multi_amount += 1
            if (h.get("facts") or {}).get("pet_fee"):
                multi_with_fee.append(h.get("identity_key"))

    def entry_of(path: Path) -> Dict:
        return OrderedDict((("path", _rel(path)), ("sha256", _sha256_of(path))))

    return OrderedDict((
        ("what_this_is",
         "What the founder was shown when deciding. These are a RECORD of the basis, not an authority: the "
         "assembler derives every one of them from the market's own census, package, shard, partition and "
         "release contract, and a status that disagrees with the source fails the build."),
        ("market_id", MARKET),
        ("founder_authorization_packet", CORRECTION_ORDER),
        ("founder_authorization_packet_document", entry_of(FOUNDER_PACKET_PATH)),
        ("founder_coverage_decision_document", entry_of(COVERAGE_DECISION_PATH)),
        ("founder_words", FOUNDER_WORDS),
        ("refused_package", REFUSED_PACKAGE_PREFIX + " (the superseded 289-profile package; never authorized)"),
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
        ("coverage_ready_mechanical", actionability["COVERAGE_READY"]),
        ("coverage_ready_by_founder_decision", coverage["coverage_decision_re_evaluated"]["COVERAGE_READY"]),
        ("resolution_rate", round(actionability["resolved"] / census["count"], 4)),
        ("corridor_pages_published", contract["routes"]["published_corridor_route_count"]),
        ("decision_1_authorize_corrected_cohort", OrderedDict((
            ("published_pet_friendly", len(hotels)),
            ("verified_no_pets_as_exclusions_only", no_pets),
            ("verified_no_pets_published_as_profiles", len(published & excluded)),
        ))),
        ("decision_2_no_website_rows_remain_held", OrderedDict((
            ("held_rows", len(no_website)),
            ("published_rows", len(set(no_website) & published)),
            ("paid_places_usage_authorized", False),
        ))),
        ("decision_3_founder_decision_rows_remain_held", OrderedDict((
            ("actionability_founder_rows", len(founder_rows)),
            ("dual_brand_address_keys", list(DUAL_BRAND_KEYS)),
            ("dual_brand_held_rows", len(dual)),
            ("dual_brand_rows_per_address_key", OrderedDict((k, by_key.get(k, 0)) for k in DUAL_BRAND_KEYS)),
            ("esa_title_collision_rows", len(esa_title)),
            ("published_rows", len(set(founder_rows) & published)),
            ("identity_resolutions_ruling_written", False),
            ("esa_display_name_invented", False),
        ))),
        ("decision_4_router_exhausted_rows_remain_held", OrderedDict((
            ("held_rows", len(exhausted)),
            ("published_rows", len(set(exhausted) & published)),
        ))),
        ("decision_5_preopening_row_remains_held", OrderedDict((
            ("identity_key", PREOPENING_KEY),
            ("held_rows", len(preopening)),
            ("held_by_the_clean_authority_preopening_rule", PREOPENING_KEY in preopening_held),
            ("published_rows", len(set(preopening) & published)),
        ))),
        ("decision_6_no_flattened_fees", OrderedDict((
            ("published_records_quoting_more_than_one_amount", multi_amount),
            ("of_which_publishing_a_single_fee", len(multi_with_fee)),
        ))),
        ("not_authorized_by_this_decision", [
            "pkg-denver-co-91b2e0a2 (the superseded 289-profile package)",
            "paid Google Places usage",
            "weaker evidence rules",
            "self-signing identity_resolutions.json",
            "an invented ESA display name",
            "publication of any held row, including the not-yet-open ECHO Suites Thornton",
            "flattening a tiered or multi-part fee into a single number",
            "deployment",
        ]),
        ("policy_package", entry_of(policy_path)),
        ("exclusion_shard", entry_of(shard_path)),
        ("release_contract", entry_of(contract_path)),
        ("identity_census", entry_of(census_path)),
        ("final_partition", entry_of(PARTITION_PATH)),
        ("actionability", entry_of(ACTIONABILITY_PATH)),
        ("clean_authority", entry_of(CLEAN_PATH)),
    ))


def _guards(basis: Dict) -> None:
    d1, d2 = basis["decision_1_authorize_corrected_cohort"], basis["decision_2_no_website_rows_remain_held"]
    d3, d4 = basis["decision_3_founder_decision_rows_remain_held"], basis["decision_4_router_exhausted_rows_remain_held"]
    d5, d6 = basis["decision_5_preopening_row_remains_held"], basis["decision_6_no_flattened_fees"]
    checks = [
        (basis["registered_package_id"] == AUTHORIZED_PACKAGE_ID,
         "the bound package is %s, not %s" % (basis["registered_package_id"], AUTHORIZED_PACKAGE_ID)),
        (basis["pet_friendly_publication_count"] == COHORT_PET_FRIENDLY
         and basis["verified_no_pets_count"] == COHORT_VERIFIED_NO_PETS,
         "the cohort is %d/%d, not the corrected %d/%d" % (basis["pet_friendly_publication_count"],
                                                            basis["verified_no_pets_count"], COHORT_PET_FRIENDLY,
                                                            COHORT_VERIFIED_NO_PETS)),
        (d1["verified_no_pets_published_as_profiles"] == 0, "a verified-no-pets row is also a profile"),
        (d2["held_rows"] == HELD_NO_WEBSITE and d2["published_rows"] == 0,
         "no-website rows %d held / %d published, not %d / 0" % (d2["held_rows"], d2["published_rows"], HELD_NO_WEBSITE)),
        (d3["actionability_founder_rows"] == HELD_FOUNDER and d3["published_rows"] == 0
         and d3["dual_brand_held_rows"] == HELD_DUAL_BRAND
         and all(n == 2 for n in d3["dual_brand_rows_per_address_key"].values())
         and d3["esa_title_collision_rows"] == HELD_ESA_TITLE,
         "founder rows %d (dual %d by key %s, ESA %d) / %d published" % (
             d3["actionability_founder_rows"], d3["dual_brand_held_rows"],
             dict(d3["dual_brand_rows_per_address_key"]), d3["esa_title_collision_rows"], d3["published_rows"])),
        (d4["held_rows"] == HELD_ROUTER_EXHAUSTED and d4["published_rows"] == 0,
         "router-exhausted rows %d held / %d published, not %d / 0" % (d4["held_rows"], d4["published_rows"],
                                                                       HELD_ROUTER_EXHAUSTED)),
        (d5["held_rows"] == HELD_PREOPENING and d5["published_rows"] == 0
         and d5["held_by_the_clean_authority_preopening_rule"],
         "the preopening row is not held exactly once and unpublished: %s" % dict(d5)),
        (d6["of_which_publishing_a_single_fee"] == 0, "a multi-amount record publishes a single fee"),
        (basis["actionable_unresolved_remaining"] == 0,
         "actionable unresolved is %r, not 0" % basis["actionable_unresolved_remaining"]),
        (basis["coverage_ready_by_founder_decision"] == "YES", "no recorded founder coverage decision"),
        (basis["source_ready"] == "YES", "the market is not source-ready"),
    ]
    failed = [why for ok, why in checks if not ok]
    if failed:
        raise SystemExit("%s: the committed state does not match the founder's decision: %s" % (WORK_ORDER, failed))


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
    _guards(basis)

    document = json.loads(prior_bytes.decode("utf-8-sig"), object_pairs_hook=OrderedDict)
    hit = 0
    for market in document["markets"]:
        if market["market_id"] != MARKET:
            continue
        hit += 1
        market["launch_status"] = LP.FOUNDER_AUTHORIZED_FOR_LAUNCH
        market["note"] = (
            "%d pet-friendly profiles and %d verified-no-pets over a %d-identity census, built from zero by %s, "
            "registered by %s and corrected before authorization by %s (the not-yet-open ECHO Suites Thornton "
            "held) as COMPOSITE_FRESH_MARKET_DATA_ONLY (FAST 15/15, 0 broad runs), and ADMITTED here by %s, the "
            "founder's launch decision for package %s. The 52 no-website rows, the 16 founder-decision rows "
            "(seven dual-brand buildings and two ESA title-collision rows), the 38 router-exhausted rows and the "
            "not-yet-open row stay held by that same decision and publish nothing. Hidden from global navigation "
            "and from the sitemap flags exactly as every recently launched market is at this stage."
            % (basis["pet_friendly_publication_count"], basis["verified_no_pets_count"], basis["census_count"],
               SOURCE_ORDER, REGISTRATION_ORDER, CORRECTION_ORDER, WORK_ORDER,
               basis["registered_package_digest"][:23]))
    if hit != 1:
        raise SystemExit("%s: expected exactly one %s row, found %d" % (WORK_ORDER, MARKET, hit))

    reason = (
        "Founder authorizes Denver / Boulder / Front Range to participate in the next production assembly as the "
        "THIRTY-SIXTH market, on registered package %s (%s, market bundle %s), and explicitly does NOT authorize "
        "the superseded package %s. %d of %d identities publish (%d verified-no-pets as exclusions only, %d held) "
        "at a %.2f%% resolution rate with ACTIONABLE UNRESOLVED = 0; coverage is READY by the founder's recorded "
        "decision. The 52 no-website rows, the 16 founder-decision rows, the 38 router-exhausted rows and the "
        "not-yet-open ECHO Suites Thornton row remain held; no identity_resolutions.json ruling is written or "
        "self-signed; no ESA display name is invented; no paid Places usage and no weaker evidence rule is "
        "authorized; no tiered or multi-part fee is flattened. Bound to the readiness packet of %s (%s), itself "
        "bound to the current live parent (deploy %s, release-index digest %s). Founder's words: '%s' Every other "
        "market's decision is unchanged, and every other waiting market remains NOT authorized for launch."
        % (basis["registered_package_id"], basis["registered_package_digest"], basis["market_bundle_sha256"],
           REFUSED_PACKAGE_PREFIX, basis["pet_friendly_publication_count"], basis["census_count"],
           basis["verified_no_pets_count"], basis["holds_unresolved"], basis["resolution_rate"] * 100,
           CORRECTION_ORDER, _rel(FOUNDER_PACKET_PATH), basis["parent_deploy_id"], basis["parent_release_digest"],
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
    problems = []
    if write:
        PATH.write_bytes(new_bytes)
        problems = LP.decision_problems(json.loads(new_bytes.decode("utf-8")), PATH)
        if problems:
            PATH.write_bytes(prior_bytes)
            raise SystemExit("%s: decision_problems %s -- the prior record was restored" % (WORK_ORDER, problems))
    return OrderedDict((("work_order", WORK_ORDER), ("written", write),
                        ("markets_before", len(authorized_before)), ("markets_after", len(authorized_after)),
                        ("gained", gained), ("lost", lost), ("decision_problems", problems),
                        ("previous_record_sha256", previous_sha),
                        ("lineage_records", len(document["decision"]["lineage"]["records"])),
                        ("supersedes", document["decision"]["supersedes"]),
                        ("decision_basis", basis)))


if __name__ == "__main__":
    result = flip(write="--write" in sys.argv)
    print(json.dumps({k: result[k] for k in ("markets_before", "markets_after", "gained", "lost", "written",
                                             "decision_problems", "previous_record_sha256", "lineage_records",
                                             "supersedes")}, indent=1))
    b = result["decision_basis"]
    for k in ("registered_package_id", "census_count", "pet_friendly_publication_count", "verified_no_pets_count",
              "holds_unresolved", "actionable_unresolved_remaining", "resolution_rate", "coverage_ready_mechanical",
              "coverage_ready_by_founder_decision", "corridor_pages_published"):
        print("%-36s %s" % (k, b[k]))
    for k in ("decision_2_no_website_rows_remain_held", "decision_3_founder_decision_rows_remain_held",
              "decision_4_router_exhausted_rows_remain_held", "decision_5_preopening_row_remains_held",
              "decision_6_no_flattened_fees"):
        print("%-36s %s" % (k, json.dumps({kk: vv for kk, vv in b[k].items() if not isinstance(vv, (list, dict))})))
