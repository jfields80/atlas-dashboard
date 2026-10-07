"""PTF-SALT-LAKE-CITY-UT-FOUNDER-LAUNCH-AUTHORIZATION-003 -- the founder's Salt Lake City / Park City launch decision
(cloned in shape from New Orleans' 003 writer).

    python -m scripts.pettripfinder.salt_lake_city_ut_launch_participation_003
    python -m scripts.pettripfinder.salt_lake_city_ut_launch_participation_003 --write

THIS RECORDS A DECISION, IT DOES NOT MAKE ONE
---------------------------------------------
The founder granted it in this order, in these words (transcribed, nothing signed in anyone's name):

    The founder explicitly authorizes launch of: salt-lake-city-ut ONLY for the exact CURRENT registered Salt Lake
    City package created by PTF-SALT-LAKE-CITY-UT-REGISTRATION-AND-STAGING-002 and bound to: 2822639c. The founder
    approves the current safe publication cohort: 133 pet-friendly profiles. Keep ALL unresolved / held rows
    unpublished.

The order told the decision NOT to guess the package id from a truncated console recap; it is read here from the
committed readiness packet (``the_digests_this_readiness_binds.sealed_package_id``) and must equal the one package the
registration commit 2822639c sealed: pkg-salt-lake-city-ut-6d474d2906ae01e0, whose content is the source-ready shadow
package pkg-salt-lake-city-ut-f084558e8d8acabe (PTF-SALT-LAKE-CITY-UT-HARDENED-SOURCE-READY-001). The shadow id and the
superseded cb60864b seal are never authorized.

The founder kept unpublished: all 47 unresolved rows; Hyatt Place Salt Lake City / Cottonwood (its first-party page
welcomes pets but also states "No pets are allowed in 4th-floor rooms" -- the shared reader is not weakened and no
disposition is forced); Hyatt Place Salt Lake City / Lehi (its first-party page prints ZIP 84048 while the other
identity evidence says 84043 -- no ZIP is invented or normalised); the three Vail Canyons Village rows; the preopening
row; every timeshare / vacation-ownership, private condo / residence and unbound resort-campus identity; every
source-silent / exhausted row; and the verified-no-pets rows as hotel profiles. No identity_resolutions.json entry is
written. This module writes that decision down. It must never be run to admit a market on its own initiative, and it
refuses if the committed state does not match what the founder was shown.

A FIRST AUTHORIZATION, NOT A RE-AUTHORIZATION: Salt Lake City has never been authorized or deployed, so no
``founder_authorization_superseded`` entry is written, and the module refuses if one exists for this market.

THE BASIS IS DERIVED, NEVER TYPED. Every number and digest in ``decision_basis`` is read at run time from committed
documents. Each founder decision is a GUARD: if the committed state disagrees with it, nothing is written.

THE CHAIN IS EXTENDED, NOT REWRITTEN (``launch_participation.extend_decision``). NO OTHER MARKET MOVES.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import launch_participation as LP     # noqa: E402

WORK_ORDER = "PTF-SALT-LAKE-CITY-UT-FOUNDER-LAUNCH-AUTHORIZATION-003"
REGISTRATION_ORDER = "PTF-SALT-LAKE-CITY-UT-REGISTRATION-AND-STAGING-002"
SOURCE_ORDER = "PTF-SALT-LAKE-CITY-UT-HARDENED-SOURCE-READY-001"
MARKET = "salt-lake-city-ut"
DECIDED_ON = "2026-10-07"
PACKAGE = _REPO_ROOT / "launch_packages" / "pettripfinder"
REPORTS = PACKAGE / "markets" / "reports"
FOUNDER_PACKET_PATH = REPORTS / "salt_lake_city_ut_authorization_readiness_002.json"
CLASSIFICATION_PATH = REPORTS / "salt_lake_city_ut_registration_classification.json"
CHECKS_PATH = REPORTS / "salt_lake_city_ut_registration_checks_002.json"
ACTIONABILITY_PATH = REPORTS / "salt_lake_city_ut_actionability_001.json"
CLEAN_PATH = REPORTS / "salt_lake_city_ut_clean_authority_001.json"
FEES_PATH = REPORTS / "salt_lake_city_ut_fee_withholding_001.json"
SAFETY_PATH = REPORTS / "salt_lake_city_ut_publication_safety_audit_001.json"
PARTITION_PATH = PACKAGE / "salt_lake_city_ut_final_partition_001.json"
PATH = LP.PARTICIPATION_PATH

REGISTRATION_COMMIT = "2822639c"
#: the source-ready SHADOW package (its content is registered as the authorized package, the shadow id never is), and
#: the source-ready order's superseded seal (kept in git history)
REFUSED_PACKAGE_PREFIXES = ("pkg-salt-lake-city-ut-f084558e", "pkg-salt-lake-city-ut-cb60864b")
PACKAGES_DIR = PACKAGE / "markets" / "packages" / MARKET

COHORT_PET_FRIENDLY = 133
COHORT_VERIFIED_NO_PETS = 29
HELD_UNRESOLVED = 47
HELD_ROUTER_EXHAUSTED = 45
#: Salt Lake City's one founder-class row: a first-party page that welcomes pets and refuses them on one floor
HELD_FOUNDER_KEYS = ["hyatt place salt lake city cottonwood"]
HELD_PREOPENING = 1
HELD_TIMESHARE = 19
HELD_MILITARY = 4
PARK_CITY_ROWS = 32
#: the held rows the founder named, by committed identity key (each must be held and publish nothing)
NAMED_HELD = OrderedDict((
    ("hyatt_place_cottonwood_floor_refusal", ("hyatt place salt lake city cottonwood",)),
    ("hyatt_place_lehi_postal_conflict", ("hyatt place salt lake city lehi",)),
    ("vail_canyons_village_server_error", ("grand summit hotel at canyons village", "silverado lodge at canyons village",
                                           "sundial lodge at canyons village")),
    ("preopening", ("the ascent park city tapestry collection by hilton",)),
))
FEES = OrderedDict((("fees_published", 21), ("tiered_fees_withheld", 39), ("unsafe_single_fees_withheld", 13),
                    ("misleading_single_fees_published", 0)))

FOUNDER_WORDS = ("The founder explicitly authorizes launch of: salt-lake-city-ut ONLY for the exact CURRENT registered "
                 "Salt Lake City package created by PTF-SALT-LAKE-CITY-UT-REGISTRATION-AND-STAGING-002 and bound to: "
                 "2822639c. The founder approves the current safe publication cohort: 133 pet-friendly profiles. "
                 "Keep ALL unresolved / held rows unpublished.")

_AMOUNT = re.compile(r"\$\s*([0-9]+(?:\.[0-9]{1,2})?)|([0-9]+(?:\.[0-9]{1,2})?)\s*USD")


def _sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rel(path: Path) -> str:
    return str(path.relative_to(_REPO_ROOT)).replace("\\", "/")


def _load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=OrderedDict)


def _fold(v) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", str(v or "").lower()).split())


def _git(*args: str) -> str:
    return subprocess.run(("git",) + args, cwd=str(_REPO_ROOT), capture_output=True, text=True,
                          check=True).stdout.strip()


def _registered_package_id() -> str:
    """The package the registration commit sealed, read from git (never typed from a recap): exactly one package file
    is ADDED under markets/packages/salt-lake-city-ut by 2822639c."""
    rel = "atlas-dashboard/" + _rel(PACKAGES_DIR) + "/"
    added = [p for p in _git("diff-tree", "--no-commit-id", "--name-only", "--diff-filter=A", "-r",
                             REGISTRATION_COMMIT).splitlines() if p.startswith(rel) and p.endswith(".json")]
    if len(added) != 1:
        raise SystemExit("%s: registration commit %s adds %d package files, not 1: %s"
                         % (WORK_ORDER, REGISTRATION_COMMIT, len(added), added))
    return Path(added[0]).stem


def _registration_commit(package_path: Path) -> Dict:
    """The founder bound the decision to the registration commit: it must exist, be an ancestor of HEAD, and carry
    the authorized package's exact bytes (the working tree's blob, line endings normalised by git)."""
    full = _git("rev-parse", "--verify", REGISTRATION_COMMIT + "^{commit}")
    head = _git("rev-parse", "HEAD")
    ancestor = subprocess.run(("git", "merge-base", "--is-ancestor", full, head), cwd=str(_REPO_ROOT)).returncode == 0
    rel = "atlas-dashboard/" + _rel(package_path)
    at_commit = _git("rev-parse", "%s:%s" % (full, rel))
    in_tree = _git("hash-object", str(package_path))
    return OrderedDict((("registration_commit", full), ("ancestor_of_head", ancestor),
                        ("package_path", rel), ("package_blob_at_registration_commit", at_commit),
                        ("package_blob_in_tree", in_tree), ("same_package_bytes", at_commit == in_tree)))


def _packet(package_id: str) -> Dict:
    packet = _load(FOUNDER_PACKET_PATH)
    if packet.get("status") != "AUTHORIZATION_READY" or packet.get("market_id") != MARKET:
        raise SystemExit("%s: the readiness packet is %r for %r, not AUTHORIZATION_READY for %s"
                         % (WORK_ORDER, packet.get("status"), packet.get("market_id"), MARKET))
    rv2 = packet["regression_v2"]
    if rv2.get("CHANGE_CLASS") != "COMPOSITE_FRESH_MARKET_DATA_ONLY" \
            or rv2.get("FULL_REGRESSION_REQUIRED") != "NO" \
            or rv2.get("classification_source") != "AUTOMATIC" \
            or packet["registration_proof"].get("ELIGIBLE") != "YES":
        raise SystemExit("%s: the readiness packet is not an eligible, automatically classified fresh-market "
                         "registration" % WORK_ORDER)
    bound = packet["the_digests_this_readiness_binds"]["sealed_package_id"]
    if bound != package_id or bound.startswith(REFUSED_PACKAGE_PREFIXES):
        raise SystemExit("%s: the readiness packet binds %r; registration commit %s sealed %s"
                         % (WORK_ORDER, bound, REGISTRATION_COMMIT, package_id))
    return packet


def _basis(packet: Dict, package_path: Path) -> Dict:
    """What the founder was shown, read from committed state at run time."""
    census_path = PACKAGE / "identity_census" / ("%s.json" % MARKET)
    policy_path = PACKAGE / ("hotel_policy_facts_%s.json" % MARKET)
    shard_path = PACKAGE / "markets" / "authority" / MARKET / "hotel_exclusions.json"
    contract_path = _REPO_ROOT / "deploy" / "netlify" / "release_contracts" / ("%s.json" % MARKET)
    census, policy, shard = _load(census_path), _load(policy_path), _load(shard_path)
    contract = _load(contract_path)
    actionability = _load(ACTIONABILITY_PATH)
    classification, checks = _load(CLASSIFICATION_PATH), _load(CHECKS_PATH)
    fees, safety = _load(FEES_PATH), _load(SAFETY_PATH)
    package = _load(package_path)
    no_pets = sum(1 for e in shard["exclusions"] if e["exclusion_state"] == "VERIFIED_NO_PETS")
    binds = packet["the_digests_this_readiness_binds"]
    rv2 = packet["regression_v2"]
    hotels = policy["hotels"]
    published = {h.get("identity_key") or h.get("key") for h in hotels}
    excluded = {e.get("identity_key") or e.get("normalized_name") for e in shard["exclusions"]}

    rows = actionability["rows"]
    exhausted = [r["identity_key"] for r in rows if r["actionability"] == "AUTHORIZED_ROUTER_EXHAUSTED"]
    founder_rows = [r for r in rows if r["actionability"] == "REQUIRES_FOUNDER"]
    preopening = [r["identity_key"] for r in rows if r["actionability"] == "HELD_UNTIL_OPENING"]
    held_keys = {r["identity_key"] for r in rows}
    non_admitted = {h["identity_key"]: h.get("classification") for h in census.get("non_admitted") or ()}
    named = OrderedDict()
    for label, keys in NAMED_HELD.items():
        named[label] = OrderedDict((
            ("identity_keys", list(keys)),
            ("states", [("UNRESOLVED_HELD" if k in held_keys else non_admitted.get(k) or "MISSING") for k in keys]),
            ("published_rows", len(set(keys) & (published | excluded)))))
    # the registration's own municipality, Park City and market-text gates (a row publishes the municipality its own
    # postal code carries; a Park City premises is Park City, UT, never Salt Lake City; no clone-parent text)
    mu, txt = checks["municipality_safety"], checks["market_text_safety"]
    gates = checks["gates"]
    geography_decision = OrderedDict((
        ("registration_gate_municipality", gates.get("municipality_safety")),
        ("registration_gate_park_city_identity", gates.get("park_city_identity_safety")),
        ("registration_gate_canyon_resort", gates.get("canyon_resort_safety")),
        ("registration_gate_market_text", gates.get("market_text_safety")),
        ("qualifying_by_county", mu["QUALIFYING_BY_COUNTY"]),
        ("park_city_rows", mu["PARK_CITY_ROWS"]),
        ("park_city_profiles_labeled_salt_lake_city", mu["PARK_CITY_PROFILES_LABELED_SALT_LAKE_CITY"]),
        ("salt_lake_city_wrong_city_identities", mu["SALT_LAKE_CITY_WRONG_CITY_IDENTITIES"]),
        ("municipality_not_carried_by_its_postal_code", mu["MUNICIPALITY_NOT_CARRIED_BY_ITS_POSTAL_CODE"]),
        ("not_utah", mu["NOT_UTAH"]),
        ("seed_rows_address_rewritten", mu["SEED_ROWS_ADDRESS_REWRITTEN"]),
        ("fixed_identities_correct", all(v["correct"] for v in mu["fixed_identities"].values())),
        ("published_by_municipality", mu["published_by_municipality"]),
        ("clone_text_residue", OrderedDict((k, v) for k, v in txt.items() if k.endswith("_TEXT_RESIDUE"))),
        ("salt_lake_city_market_label_correct", txt["SALT_LAKE_CITY_MARKET_LABEL_CORRECT"]),
        ("rows_not_in_utah", sorted(h["identity_key"] for h in census["hotels"] if (h.get("state") or "") != "UT")),
    ))

    non = census.get("non_admitted") or ()
    timeshare = [h["canonical_name"] for h in non
                 if h["classification"] == "NON_LODGING" and str(h.get("classification_reason")).startswith("TIMESHARE")]
    military = [h["canonical_name"] for h in non
                if str(h.get("classification_reason")).startswith("MILITARY_RESTRICTED")]
    shard_names = {_fold(e.get("canonical_name")) for e in shard["exclusions"]}
    policy_names = {_fold(h.get("name")) for h in hotels}
    admitted_names = {_fold(h["canonical_name"]) for h in census["hotels"]}

    def outside(names):
        return OrderedDict((
            ("rows", len(names)), ("names", names),
            ("qualifying_census_rows", sum(1 for n in names if _fold(n) in admitted_names)),
            ("verified_no_pets_exclusions", sum(1 for n in names if _fold(n) in shard_names)),
            ("pet_friendly_records", sum(1 for n in names if _fold(n) in policy_names))))

    multi_amount, multi_with_fee = 0, []
    for h in hotels:
        quotes = " ".join(e.get("quote", "") for e in h.get("evidence", []))
        amounts = {float(a or b) for a, b in _AMOUNT.findall(quotes)}
        if len(amounts) > 1:
            multi_amount += 1
            if (h.get("facts") or {}).get("pet_fee"):
                multi_with_fee.append(h.get("identity_key"))

    held = checks["held_row_safety"]

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
        ("registration_classification_document", entry_of(CLASSIFICATION_PATH)),
        ("registration_checks_document", entry_of(CHECKS_PATH)),
        ("founder_words", FOUNDER_WORDS),
        ("package_id_source",
         "read mechanically: the one package file registration commit %s added, equal to the readiness packet's "
         "sealed_package_id (the founder's console recap was truncated and is not used)" % REGISTRATION_COMMIT),
        ("registration_commit_binding", _registration_commit(package_path)),
        ("refused_packages", [
            "pkg-salt-lake-city-ut-f084558e8d8acabe (the source-ready SHADOW package; its content is registered as "
            "%s, the shadow id is never authorized)" % binds["sealed_package_id"],
            "pkg-salt-lake-city-ut-cb60864b (the source-ready order's superseded seal; kept in git history)"]),
        ("parent_deploy_id", binds["parent_live_deploy_id"]),
        ("parent_release_digest", binds["parent_release_digest"]),
        ("registered_package_id", binds["sealed_package_id"]),
        ("registered_package_digest", binds["sealed_package_digest"]),
        ("package_file_digest_field", package["package_digest"]),
        ("content_identical_to_source_ready", checks["registered_package"]["content_identical_to"]),
        ("content_fields_identical", all(checks["registered_package"]["content_fields"].values())),
        ("fast_receipt", binds["fast_receipt"]),
        ("fast_receipt_digest", binds["fast_receipt_digest"]),
        ("market_bundle_sha256", binds["changed_market_bundle_sha256"]),
        ("registration_class", rv2["CHANGE_CLASS"]),
        ("registration_base", (classification.get("registration_base") or {}).get("base")),
        ("registration_classification_source", classification.get("classification_source")),
        ("classifier_checks_passed", sum(1 for v in classification["new_market_registration_data_only"]["checks"].values()
                                         if v.get("pass"))),
        ("shared_paths", classification["new_market_registration_data_only"]["accounting"]["SHARED_BEHAVIOR_PATHS"]),
        ("unknown_paths", classification["new_market_registration_data_only"]["accounting"]["UNKNOWN_PATHS"]),
        ("full_regression_required", rv2["FULL_REGRESSION_REQUIRED"]),
        ("broad_regression_runs", rv2["REMOTE_BROAD_JOBS_REQUIRED"]),
        ("registration_staging_gates", checks["ALL_STAGING_GATES"]),
        ("registration_staging_gate_count", "%d/%d" % (sum(1 for v in gates.values() if v == "PASS"), len(gates))),
        ("projected_accounting", checks["projected_accounting"]),
        ("census_count", census["count"]),
        ("pet_friendly_publication_count", len(hotels)),
        ("verified_no_pets_count", no_pets),
        ("holds_unresolved", census["count"] - len(hotels) - no_pets),
        ("actionable_unresolved_remaining", actionability["actionable_unresolved_remaining"]),
        ("source_ready", actionability["TECHNICAL_SOURCE_READY"]),
        ("coverage_ready", actionability["COVERAGE_READY"]),
        ("resolution_rate", round(actionability["resolved"] / census["count"], 4)),
        ("corridor_pages_published", contract["routes"]["published_corridor_route_count"]),
        ("decision_1_authorize_registered_cohort", OrderedDict((
            ("published_pet_friendly", len(hotels)),
            ("verified_no_pets_as_exclusions_only", no_pets),
            ("verified_no_pets_published_as_profiles", len(published & excluded))))),
        ("decision_2_unresolved_rows_remain_held", OrderedDict((
            ("unresolved_rows", len(rows)), ("published_rows", len({r["identity_key"] for r in rows} & published))))),
        ("decision_3_named_rows_remain_held", named),
        ("decision_4_founder_rows_remain_held", OrderedDict((
            ("actionability_founder_rows", len(founder_rows)),
            ("founder_rows", [r["identity_key"] for r in founder_rows]),
            ("published_rows", len({r["identity_key"] for r in founder_rows} & published)),
            ("shared_reader_weakened", False),
            ("disposition_forced", False),
            ("identity_resolutions_ruling_written", bool(checks["identity_resolutions_written"])),
            ("zip_invented_or_normalised", False)))),
        ("decision_5_router_exhausted_rows_remain_held", OrderedDict((
            ("held_rows", len(exhausted)), ("published_rows", len(set(exhausted) & published))))),
        ("decision_6_preopening_rows_remain_held", OrderedDict((
            ("held_rows", len(preopening)), ("published_rows", len(set(preopening) & published))))),
        ("decision_7_no_flattened_fees", OrderedDict((
            ("fee_withholding", OrderedDict((k, fees[k]) for k in FEES)),
            ("withheld_fees_flattened", checks["fee_withholding_preserved"]["WITHHELD_FEES_FLATTENED"]),
            ("published_records_quoting_more_than_one_amount", multi_amount),
            ("of_which_publishing_a_single_fee", len(multi_with_fee)),
            ("rows", multi_with_fee)))),
        ("decision_8_timeshare_outside_hotel_inventory", outside(timeshare)),
        ("decision_9_military_restricted_outside_hotel_inventory", outside(military)),
        ("decision_10_private_condo_residence_and_resort_campus_unpublished", OrderedDict((
            ("private_condo_residence_or_rental_rows", held["private_condo_residence_or_rental"]["rows"]),
            ("private_condo_residence_or_rental_published", held["private_condo_residence_or_rental"]["published"]),
            ("timeshare_rows", held["timeshare"]["rows"]),
            ("timeshare_published", held["timeshare"]["published"]),
            ("vail_resort_campus_rows", held["founder_ruling_vail_park_city_mountain"]["rows"]),
            ("vail_resort_campus_published", held["founder_ruling_vail_park_city_mountain"]["published"])))),
        ("decision_11_municipalities_never_flattened", geography_decision),
        ("reader_safety", OrderedDict((k, safety["counts"][k]) for k in (
            "pet_friendly_with_explicit_refusal", "question_only_pet_friendly", "service_animal_only_pet_friendly",
            "preopening_or_closed_published", "timeshare_or_vacation_ownership_published",
            "military_restricted_published", "misleading_single_fee_published", "park_city_labeled_salt_lake_city",
            "canyon_resort_published", "vacation_rental_or_condo_published", "shared_reader_disagrees"))),
        ("cross_market_safety",
         "Salt Lake City carries %d bare-chain-shaped names and %d bare-chain collisions; cross-market collisions %d; "
         "duplicate excluded identities %d; live properties moved or displaced %d (the registration checks searched "
         "every census, registry row and live profile)."
         % (checks["cross_market_safety"]["BARE_CHAIN_NAMES"], checks["cross_market_safety"]["BARE_CHAIN_COLLISIONS"],
            checks["cross_market_safety"]["CROSS_MARKET_COLLISIONS"],
            checks["cross_market_safety"]["DUPLICATE_EXCLUDED_IDENTITIES"],
            checks["cross_market_safety"]["LIVE_PROPERTIES_MOVED_OR_DISPLACED"])),
        ("not_authorized_by_this_decision", [
            "the source-ready shadow id pkg-salt-lake-city-ut-f084558e8d8acabe, the superseded cb60864b seal, or any "
            "other or earlier package",
            "new paid spend or any reopened acquisition",
            "weaker evidence rules or a change to the shared reader or factory code",
            "self-signing identity_resolutions.json",
            "publishing Hyatt Place Cottonwood as pet-friendly or as verified no-pets",
            "inventing or normalising Hyatt Place Lehi's ZIP",
            "retrying the Vail / Park City Mountain server-error pages",
            "an invented replacement identity, route, ZIP or domain",
            "publication of any held row, or of a verified-no-pets row as a hotel profile",
            "admitting a timeshare / vacation-ownership, private condo / residence, unbound resort-campus or "
            "military-restricted identity as a hotel or exclusion",
            "labelling a Park City premises as Salt Lake City",
            "flattening a tiered, capped, conditional or multi-amount fee into a single number",
            "deploying: this records the launch decision only",
        ]),
        ("policy_package", entry_of(policy_path)),
        ("exclusion_shard", entry_of(shard_path)),
        ("release_contract", entry_of(contract_path)),
        ("identity_census", entry_of(census_path)),
        ("final_partition", entry_of(PARTITION_PATH)),
        ("actionability", entry_of(ACTIONABILITY_PATH)),
        ("clean_authority", entry_of(CLEAN_PATH)),
        ("registered_package", entry_of(package_path)),
    ))


def _guards(basis: Dict, package_id: str) -> None:
    d1, d2 = basis["decision_1_authorize_registered_cohort"], basis["decision_2_unresolved_rows_remain_held"]
    d3, d4 = basis["decision_3_named_rows_remain_held"], basis["decision_4_founder_rows_remain_held"]
    d5, d6 = basis["decision_5_router_exhausted_rows_remain_held"], basis["decision_6_preopening_rows_remain_held"]
    d7 = basis["decision_7_no_flattened_fees"]
    d8, d9 = basis["decision_8_timeshare_outside_hotel_inventory"], basis["decision_9_military_restricted_outside_hotel_inventory"]
    d10, geo = basis["decision_10_private_condo_residence_and_resort_campus_unpublished"], \
        basis["decision_11_municipalities_never_flattened"]
    rc = basis["registration_commit_binding"]
    pa = basis["projected_accounting"]

    def outside_ok(d, n):
        return d["rows"] == n and not d["qualifying_census_rows"] and not d["verified_no_pets_exclusions"] \
            and not d["pet_friendly_records"]

    checks = [
        (basis["registered_package_id"] == package_id
         and basis["package_file_digest_field"] == basis["registered_package_digest"]
         and not package_id.startswith(REFUSED_PACKAGE_PREFIXES),
         "the bound package is %s, not %s" % (basis["registered_package_id"], package_id)),
        (basis["content_identical_to_source_ready"] == "pkg-salt-lake-city-ut-f084558e8d8acabe"
         and basis["content_fields_identical"], "the registered content is not the source-ready package's"),
        (rc["ancestor_of_head"] and rc["same_package_bytes"],
         "registration commit %s does not carry the authorized package bytes: %s" % (REGISTRATION_COMMIT, dict(rc))),
        (basis["registration_classification_source"] == "AUTOMATIC" and basis["classifier_checks_passed"] == 15
         and basis["shared_paths"] == 0 and basis["unknown_paths"] == 0 and basis["full_regression_required"] == "NO"
         and basis["broad_regression_runs"] == 0,
         "the registration evidence is not automatic / 15 of 15 / 0 shared / 0 unknown / broad NO"),
        (basis["registration_staging_gates"] == "PASS", "the registration staging gates did not pass"),
        (pa["SALT_LAKE_CITY_PROJECTED_PROFILES"] == COHORT_PET_FRIENDLY and pa["CANDIDATE_MARKETS"] == 45
         and pa["CANDIDATE_PROFILES"] == 4373, "projected accounting %s" % dict(pa)),
        (basis["pet_friendly_publication_count"] == COHORT_PET_FRIENDLY
         and basis["verified_no_pets_count"] == COHORT_VERIFIED_NO_PETS and basis["census_count"] == 209,
         "the cohort is %d/%d, not %d/%d" % (basis["pet_friendly_publication_count"], basis["verified_no_pets_count"],
                                             COHORT_PET_FRIENDLY, COHORT_VERIFIED_NO_PETS)),
        (d1["verified_no_pets_published_as_profiles"] == 0, "a verified-no-pets row is also a profile"),
        (d2["unresolved_rows"] == HELD_UNRESOLVED == basis["holds_unresolved"] and d2["published_rows"] == 0,
         "unresolved rows %s" % dict(d2)),
        (all(v["published_rows"] == 0 and set(v["states"]) == {"UNRESOLVED_HELD"} for v in d3.values()),
         "named held rows %s" % json.dumps(d3)),
        (d4["founder_rows"] == HELD_FOUNDER_KEYS and d4["published_rows"] == 0
         and not d4["identity_resolutions_ruling_written"],
         "founder rows do not match: %s" % json.dumps(d4)),
        (d5["held_rows"] == HELD_ROUTER_EXHAUSTED and d5["published_rows"] == 0, "router-exhausted %s" % dict(d5)),
        (d6["held_rows"] == HELD_PREOPENING and d6["published_rows"] == 0, "preopening %s" % dict(d6)),
        (dict(d7["fee_withholding"]) == dict(FEES) and d7["of_which_publishing_a_single_fee"] == 0
         and d7["withheld_fees_flattened"] == 0, "fees do not match: %s" % json.dumps(d7)),
        (outside_ok(d8, HELD_TIMESHARE), "a timeshare identity is in hotel inventory: %s" % json.dumps(d8)),
        (outside_ok(d9, HELD_MILITARY), "a military-restricted identity is in hotel inventory: %s" % json.dumps(d9)),
        (d10["private_condo_residence_or_rental_published"] == 0 and d10["timeshare_published"] == 0
         and d10["vail_resort_campus_rows"] == 3 and d10["vail_resort_campus_published"] == 0,
         "private condo / residence / resort campus: %s" % json.dumps(d10)),
        (geo["registration_gate_municipality"] == "PASS" and geo["registration_gate_park_city_identity"] == "PASS"
         and geo["registration_gate_canyon_resort"] == "PASS" and geo["registration_gate_market_text"] == "PASS"
         and geo["park_city_rows"] == PARK_CITY_ROWS and geo["park_city_profiles_labeled_salt_lake_city"] == 0
         and not geo["salt_lake_city_wrong_city_identities"]
         and not geo["municipality_not_carried_by_its_postal_code"] and not geo["not_utah"]
         and not geo["seed_rows_address_rewritten"] and geo["fixed_identities_correct"]
         and not any(geo["clone_text_residue"].values()) and geo["salt_lake_city_market_label_correct"]
         and not geo["rows_not_in_utah"],
         "municipalities / Park City / market text: %s" % json.dumps(geo)),
        (not any(basis["reader_safety"].values()), "reader safety: %s" % dict(basis["reader_safety"])),
        (basis["actionable_unresolved_remaining"] == 0, "actionable unresolved is not 0"),
        (basis["coverage_ready"] == "YES" and basis["source_ready"] == "YES", "the market is not source/coverage ready"),
    ]
    failed = [why for ok, why in checks if not ok]
    if failed:
        raise SystemExit("%s: the committed state does not match the founder's decision: %s" % (WORK_ORDER, failed))


def flip(write: bool = False) -> Dict:
    prior_bytes = PATH.read_bytes()
    prior = json.loads(prior_bytes.decode("utf-8-sig"), object_pairs_hook=OrderedDict)
    previous_sha = LP.participation_sha256(PATH)
    package_id = _registered_package_id()
    package_path = PACKAGES_DIR / ("%s.json" % package_id)
    packet = _packet(package_id)
    authorized_before = LP.authorized_market_ids(prior)
    if MARKET in authorized_before:
        raise SystemExit("%s: %s is already authorized" % (WORK_ORDER, MARKET))
    if LP.launch_status(MARKET, prior) != LP.SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH:
        raise SystemExit("%s: %s reads %s" % (WORK_ORDER, MARKET, LP.launch_status(MARKET, prior)))
    superseded = (prior.get("decision") or {}).get(LP.FOUNDER_AUTHORIZATION_SUPERSEDED) or []
    if any(e.get("market_id") == MARKET for e in superseded):
        raise SystemExit("%s: %s carries a supersession entry; this is a FIRST authorization" % (WORK_ORDER, MARKET))

    basis = _basis(packet, package_path)
    _guards(basis, package_id)

    document = json.loads(prior_bytes.decode("utf-8-sig"), object_pairs_hook=OrderedDict)
    hit = 0
    for market in document["markets"]:
        if market["market_id"] != MARKET:
            continue
        hit += 1
        market["launch_status"] = LP.FOUNDER_AUTHORIZED_FOR_LAUNCH
        market["note"] = (
            "%d pet-friendly profiles and %d verified-no-pets over a %d-identity census, built from zero by %s, "
            "registered by %s as COMPOSITE_FRESH_MARKET_DATA_ONLY (automatic base and classification, FAST 15/15, 0 "
            "broad runs), and ADMITTED here by %s, the founder's launch decision for package %s bound to registration "
            "commit %s. The %d unresolved rows -- among them Hyatt Place Cottonwood, Hyatt Place Lehi, the three Vail "
            "Canyons Village rows and the preopening Ascent -- stay held by that same decision and publish nothing. "
            "Municipalities are never flattened: a Park City premises publishes as Park City, UT, and every Wasatch "
            "Front premises as its own municipality, never as Salt Lake City. Hidden from global navigation and from "
            "the sitemap flags exactly as every recently launched market is at this stage."
            % (basis["pet_friendly_publication_count"], basis["verified_no_pets_count"], basis["census_count"],
               SOURCE_ORDER, REGISTRATION_ORDER, WORK_ORDER, basis["registered_package_digest"][:23],
               REGISTRATION_COMMIT, basis["holds_unresolved"]))
    if hit != 1:
        raise SystemExit("%s: expected exactly one %s row, found %d" % (WORK_ORDER, MARKET, hit))

    reason = (
        "Founder authorizes Salt Lake City / Park City / Wasatch Front, Utah to participate in the next production "
        "assembly as the FORTY-FIFTH market, on registered package %s (%s, market bundle %s), bound to registration "
        "commit %s, and does NOT authorize the source-ready shadow id pkg-salt-lake-city-ut-f084558e8d8acabe or the "
        "superseded cb60864b seal. %d of %d identities publish (%d verified-no-pets as exclusions only, %d held) at a "
        "%.2f%% resolution rate with ACTIONABLE UNRESOLVED = 0 and coverage READY. All %d unresolved rows remain held "
        "-- Hyatt Place Salt Lake City / Cottonwood (its first-party page welcomes pets but states 'No pets are allowed "
        "in 4th-floor rooms'; the shared reader is not weakened and no disposition is forced), Hyatt Place Salt Lake "
        "City / Lehi (first-party ZIP 84048 against 84043 elsewhere; no ZIP is invented or normalised), the three Vail "
        "Canyons Village rows (server-error pages, not retried), the preopening Ascent and the router-exhausted rest; "
        "no identity_resolutions.json ruling is written or self-signed; the %d timeshare / vacation-ownership "
        "identities, the private condo / residence / rental identities and the %d military-restricted identities "
        "remain outside qualifying hotel inventory; every Park City premises publishes as Park City, UT (0 labelled "
        "Salt Lake City); no paid spend, no reopened acquisition and no weaker evidence rule is authorized; no tiered, "
        "capped, conditional or multi-amount fee is flattened. Bound to the readiness packet of %s (%s), itself bound "
        "to the current live parent (deploy %s, release-index digest %s). Founder's words: '%s' Every other market's "
        "decision is unchanged, and every other waiting market remains NOT authorized for launch."
        % (basis["registered_package_id"], basis["registered_package_digest"], basis["market_bundle_sha256"],
           basis["registration_commit_binding"]["registration_commit"],
           basis["pet_friendly_publication_count"], basis["census_count"], basis["verified_no_pets_count"],
           basis["holds_unresolved"], basis["resolution_rate"] * 100, basis["holds_unresolved"],
           basis["decision_8_timeshare_outside_hotel_inventory"]["rows"],
           basis["decision_9_military_restricted_outside_hotel_inventory"]["rows"],
           REGISTRATION_ORDER, _rel(FOUNDER_PACKET_PATH), basis["parent_deploy_id"], basis["parent_release_digest"],
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
                        ("other_rows_changed", 0),
                        ("previous_record_sha256", previous_sha),
                        ("lineage_records", len(document["decision"]["lineage"]["records"])),
                        ("supersedes", document["decision"]["supersedes"]),
                        ("decision_basis", basis)))


if __name__ == "__main__":
    result = flip(write="--write" in sys.argv)
    print(json.dumps({k: result[k] for k in ("markets_before", "markets_after", "gained", "lost", "written",
                                             "decision_problems", "other_rows_changed", "previous_record_sha256",
                                             "lineage_records", "supersedes")}, indent=1))
    b = result["decision_basis"]
    for k in ("registered_package_id", "registered_package_digest", "registration_base",
              "registration_classification_source", "classifier_checks_passed", "registration_staging_gate_count",
              "census_count", "pet_friendly_publication_count", "verified_no_pets_count", "holds_unresolved",
              "actionable_unresolved_remaining", "resolution_rate", "coverage_ready", "corridor_pages_published"):
        print("%-36s %s" % (k, b[k]))
    print("%-36s %s" % ("registration_commit_binding", json.dumps(b["registration_commit_binding"])))
    for k in ("decision_2_unresolved_rows_remain_held", "decision_3_named_rows_remain_held",
              "decision_4_founder_rows_remain_held", "decision_5_router_exhausted_rows_remain_held",
              "decision_6_preopening_rows_remain_held", "decision_7_no_flattened_fees",
              "decision_8_timeshare_outside_hotel_inventory", "decision_9_military_restricted_outside_hotel_inventory",
              "decision_10_private_condo_residence_and_resort_campus_unpublished",
              "decision_11_municipalities_never_flattened"):
        print("%-36s %s" % (k, json.dumps({kk: vv for kk, vv in b[k].items() if kk not in ("names", "rows")
                                           or not isinstance(vv, list)})))
    print("%-36s %s" % ("reader_safety", json.dumps(b["reader_safety"])))
