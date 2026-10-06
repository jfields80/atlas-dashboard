"""PTF-KANSAS-CITY-MO-FOUNDER-LAUNCH-AUTHORIZATION-003 -- the founder's Kansas City launch decision (cloned in shape
from Minneapolis's 003 writer).

    python -m scripts.pettripfinder.kansas_city_mo_launch_participation_003
    python -m scripts.pettripfinder.kansas_city_mo_launch_participation_003 --write

THIS RECORDS A DECISION, IT DOES NOT MAKE ONE
---------------------------------------------
The founder granted it in this order, in these words (transcribed, nothing signed in anyone's name):

    The founder explicitly authorizes launch of: kansas-city-mo ONLY for: pkg-kansas-city-mo-140e35291a2195c3. Bind
    this decision to: d054d6c0. Do NOT authorize: pkg-kansas-city-mo-24718ac004c967b8 or any earlier Kansas City
    package. The founder accepts the current safe publication cohort: 161 pet-friendly profiles.

That package is the registered 161-profile / 60-no-pets Kansas City cohort (PTF-KANSAS-CITY-MO-REGISTRATION-AND-STAGING-002),
whose content is the source-ready package pkg-kansas-city-mo-24718ac004c967b8 (PTF-KANSAS-CITY-MO-HARDENED-SOURCE-READY-001).
The founder kept unpublished: all 69 unresolved rows; the six dual-brand rows in three buildings (Aloft + Element North
Kansas City at 1875 Diamond Pkwy; AC Hotel + Residence Inn Lenexa City Center at 8710 Penrose Ln; Courtyard + Residence
Inn Kansas City Downtown / Convention Center at 1535 Baltimore Ave); the Hilton Garden Inn Overland Park and Sleep Inn
Olathe rebrand holds; ESA Kansas City - Airport - Tiffany Springs; the four preopening rows; every timeshare /
vacation-ownership row; every other committed held row; and the 60 verified-no-pets rows as hotel profiles. No
identity_resolutions.json entry is written, no rebrand hold is resolved, the fake anti-virus Crossland page is never
revisited and no CAPTCHA is bypassed. This module writes that decision down. It must never be run to admit a market on
its own initiative, and it refuses if the committed state does not match what the founder was shown -- in particular,
if the readiness packet binds any package other than pkg-kansas-city-mo-140e35291a2195c3, or if the registration commit
d054d6c0 does not carry that package's exact bytes.

A FIRST AUTHORIZATION, NOT A RE-AUTHORIZATION: Kansas City has never been authorized or deployed, so no
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
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import launch_participation as LP     # noqa: E402

WORK_ORDER = "PTF-KANSAS-CITY-MO-FOUNDER-LAUNCH-AUTHORIZATION-003"
REGISTRATION_ORDER = "PTF-KANSAS-CITY-MO-REGISTRATION-AND-STAGING-002"
SOURCE_ORDER = "PTF-KANSAS-CITY-MO-HARDENED-SOURCE-READY-001"
MARKET = "kansas-city-mo"
DECIDED_ON = "2026-10-06"
PACKAGE = _REPO_ROOT / "launch_packages" / "pettripfinder"
REPORTS = PACKAGE / "markets" / "reports"
FOUNDER_PACKET_PATH = REPORTS / "kansas_city_mo_registration_authorization_readiness.json"
CLASSIFICATION_PATH = REPORTS / "kansas_city_mo_registration_classification.json"
CHECKS_PATH = REPORTS / "kansas_city_mo_registration_checks_002.json"
ACTIONABILITY_PATH = REPORTS / "kansas_city_mo_actionability_001.json"
CLEAN_PATH = REPORTS / "kansas_city_mo_clean_authority_001.json"
FEES_PATH = REPORTS / "kansas_city_mo_fee_withholding_001.json"
SAFETY_PATH = REPORTS / "kansas_city_mo_publication_safety_audit_001.json"
PARTITION_PATH = PACKAGE / "kansas_city_mo_final_partition_001.json"
PATH = LP.PARTICIPATION_PATH

AUTHORIZED_PACKAGE_ID = "pkg-kansas-city-mo-140e35291a2195c3"
AUTHORIZED_PACKAGE_PATH = PACKAGE / "markets" / "packages" / MARKET / ("%s.json" % AUTHORIZED_PACKAGE_ID)
REGISTRATION_COMMIT = "d054d6c0"
#: the source-ready SHADOW package (its content is registered as the authorized package, the shadow id never is), and
#: the source-ready order's first shadow seal (superseded by the fixed-point seal, removed, never committed)
REFUSED_PACKAGE_PREFIXES = ("pkg-kansas-city-mo-24718ac0", "pkg-kansas-city-mo-154f5c6b")

COHORT_PET_FRIENDLY = 161
COHORT_VERIFIED_NO_PETS = 60
HELD_UNRESOLVED = 69
HELD_ROUTER_EXHAUSTED = 59
#: Kansas City's six founder-class rows are the three dual-brand buildings (two hotels at one street address each);
#: no other row awaits a founder ruling.
HELD_FOUNDER = 6
HELD_FOUNDER_KEYS = []
HELD_DUAL_BRAND = 6
HELD_DUAL_BRAND_BUILDINGS = 3
HELD_PREOPENING = 4
HELD_TIMESHARE = 1
HELD_MILITARY = 2
#: the held rows the founder named, by committed identity key (each must be held and publish nothing)
NAMED_HELD = OrderedDict((
    ("dual_brand_1875_diamond_pkwy", ("aloft by marriott north kansas city", "element by marriott north kansas city")),
    ("dual_brand_8710_penrose_ln", ("ac hotel lenexa city center", "residence inn by marriott lenexa city center")),
    ("dual_brand_1535_baltimore_ave", ("courtyard by marriott kansas city downtown convention center",
                                       "residence inn by marriott kansas city downtown convention center")),
    ("rebrand_hilton_garden_inn_overland_park", ("hilton garden inn overland park",)),
    ("rebrand_sleep_inn_olathe", ("sleep inn olathe kansas city",)),
    ("esa_tiffany_springs", ("extended stay america suites kansas city airport tiffany springs",)),
    ("crossland_route_identity_never_revisited", ("extended stay kansas city",)),
    ("preopening", ("doubletree by hilton kci", "home2 suites by hilton kansas city speedway",
                    "spark by hilton kansas city airport", "the park hotel on the plaza")),
))
FEES = OrderedDict((("fees_published", 25), ("tiered_fees_withheld", 37), ("unsafe_single_fees_withheld", 17),
                    ("misleading_single_fees_published", 0)))

FOUNDER_WORDS = ("The founder explicitly authorizes launch of: kansas-city-mo ONLY for: "
                 "pkg-kansas-city-mo-140e35291a2195c3. Bind this decision to: d054d6c0. "
                 "Do NOT authorize: pkg-kansas-city-mo-24718ac004c967b8 or any earlier Kansas City package. "
                 "The founder accepts the current safe publication cohort: 161 pet-friendly profiles.")

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


def _registration_commit() -> Dict:
    """The founder bound the decision to the registration commit: it must exist, be an ancestor of HEAD, and carry
    the authorized package's exact bytes (the working tree's blob, line endings normalised by git)."""
    full = _git("rev-parse", "--verify", REGISTRATION_COMMIT + "^{commit}")
    head = _git("rev-parse", "HEAD")
    ancestor = subprocess.run(("git", "merge-base", "--is-ancestor", full, head), cwd=str(_REPO_ROOT)).returncode == 0
    rel = "atlas-dashboard/" + _rel(AUTHORIZED_PACKAGE_PATH)
    at_commit = _git("rev-parse", "%s:%s" % (full, rel))
    in_tree = _git("hash-object", str(AUTHORIZED_PACKAGE_PATH))
    return OrderedDict((("registration_commit", full), ("ancestor_of_head", ancestor),
                        ("package_path", rel), ("package_blob_at_registration_commit", at_commit),
                        ("package_blob_in_tree", in_tree), ("same_package_bytes", at_commit == in_tree)))


def _packet() -> Dict:
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
    if bound != AUTHORIZED_PACKAGE_ID or bound.startswith(REFUSED_PACKAGE_PREFIXES):
        raise SystemExit("%s: the readiness packet binds %r; the founder authorized %s only"
                         % (WORK_ORDER, bound, AUTHORIZED_PACKAGE_ID))
    return packet


def _basis(packet: Dict) -> Dict:
    """What the founder was shown, read from committed state at run time."""
    census_path = PACKAGE / "identity_census" / ("%s.json" % MARKET)
    policy_path = PACKAGE / ("hotel_policy_facts_%s.json" % MARKET)
    shard_path = PACKAGE / "markets" / "authority" / MARKET / "hotel_exclusions.json"
    contract_path = _REPO_ROOT / "deploy" / "netlify" / "release_contracts" / ("%s.json" % MARKET)
    census, policy, shard = _load(census_path), _load(policy_path), _load(shard_path)
    contract = _load(contract_path)
    actionability, clean = _load(ACTIONABILITY_PATH), _load(CLEAN_PATH)
    classification, checks = _load(CLASSIFICATION_PATH), _load(CHECKS_PATH)
    fees, safety = _load(FEES_PATH), _load(SAFETY_PATH)
    package = _load(AUTHORIZED_PACKAGE_PATH)
    no_pets = sum(1 for e in shard["exclusions"] if e["exclusion_state"] == "VERIFIED_NO_PETS")
    binds = packet["the_digests_this_readiness_binds"]
    rv2 = packet["regression_v2"]
    hotels = policy["hotels"]
    published = {h.get("identity_key") or h.get("key") for h in hotels}
    excluded = {e.get("identity_key") or e.get("normalized_name") for e in shard["exclusions"]}
    admitted = {h["identity_key"]: h for h in census["hotels"]}

    rows = actionability["rows"]
    exhausted = [r["identity_key"] for r in rows if r["actionability"] == "AUTHORIZED_ROUTER_EXHAUSTED"]
    founder_rows = [r for r in rows if r["actionability"] == "REQUIRES_FOUNDER"]
    dual = [r["identity_key"] for r in founder_rows if r["disposition"] == "IDENTITY_MISMATCH_HOLD"]
    others = [r["identity_key"] for r in founder_rows if r["disposition"] != "IDENTITY_MISMATCH_HOLD"]
    preopening = [r["identity_key"] for r in rows if r["actionability"] == "HELD_UNTIL_OPENING"]
    held_keys = {r["identity_key"] for r in rows}
    non_admitted = {h["identity_key"]: h.get("classification") for h in census.get("non_admitted") or ()}
    named = OrderedDict()
    for label, keys in NAMED_HELD.items():
        named[label] = OrderedDict((
            ("identity_keys", list(keys)),
            ("states", [("UNRESOLVED_HELD" if k in held_keys else non_admitted.get(k) or "MISSING") for k in keys]),
            ("published_rows", len(set(keys) & (published | excluded)))))
    # the registration's own two-state and market-text gates (Missouri 630-658 / Kansas 660-679, no state rewritten;
    # no Minneapolis / Twin Cities and no Portland / Oregon text in the registered documents; the label is Kansas City's)
    xs, txt = checks["cross_state_safety"], checks["market_text_safety"]
    geography_decision = OrderedDict((
        ("registration_gate_cross_state", checks["gates"].get("cross_state_safety")),
        ("registration_gate_market_text", checks["gates"].get("market_text_safety")),
        ("missouri_qualifying_hotels", xs["MISSOURI_QUALIFYING_HOTELS"]),
        ("kansas_qualifying_hotels", xs["KANSAS_QUALIFYING_HOTELS"]),
        ("ks_hotels_mislabeled_mo", xs["KS_HOTELS_MISLABELED_MO"]),
        ("mo_hotels_mislabeled_ks", xs["MO_HOTELS_MISLABELED_KS"]),
        ("seed_rows_state_rewritten", xs["SEED_ROWS_STATE_REWRITTEN"]),
        ("fixed_identities_correct", all(v["correct"] for v in xs["fixed_identities"].values())),
        ("minneapolis_st_paul_text_residue", txt["MINNEAPOLIS_ST_PAUL_MARKET_TEXT_RESIDUE"]),
        ("oregon_portland_text_residue", txt["OREGON_PORTLAND_TEXT_RESIDUE"]),
        ("kansas_city_market_label_correct", txt["KANSAS_CITY_MARKET_LABEL_CORRECT"]),
        ("rows_not_in_missouri_or_kansas", sorted(h["identity_key"] for h in census["hotels"]
                                                  if (h.get("state") or "") not in ("MO", "KS"))),
    ))
    # a dual-brand building is two hotels at one street address: the house number and postal code name the building
    buildings = Counter("%s|%s" % (str(admitted[k]["street"]).split()[0].rstrip("ABCDEFGHabcdefgh"),
                                   admitted[k]["postal_code"]) for k in dual)

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
        ("registration_commit_binding", _registration_commit()),
        ("refused_packages", [
            "pkg-kansas-city-mo-24718ac004c967b8 (the source-ready SHADOW package; its content is registered as %s, "
            "the shadow id is never authorized)" % AUTHORIZED_PACKAGE_ID,
            "pkg-kansas-city-mo-154f5c6b4f5d360c (the source-ready order's first shadow seal, superseded by its "
            "fixed-point seal; removed, never committed)"]),
        ("parent_deploy_id", binds["parent_live_deploy_id"]),
        ("parent_release_digest", binds["parent_release_digest"]),
        ("registered_package_id", binds["sealed_package_id"]),
        ("registered_package_digest", binds["sealed_package_digest"]),
        ("package_file_digest_field", package["package_digest"]),
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
            ("dual_brand_rows", len(dual)), ("dual_brand_buildings", OrderedDict(sorted(buildings.items()))),
            ("other_founder_rows", others),
            ("published_rows", len({r["identity_key"] for r in founder_rows} & published)),
            ("identity_resolutions_ruling_written", False),
            ("replacement_route_or_domain_invented", False)))),
        ("decision_5_router_exhausted_rows_remain_held", OrderedDict((
            ("held_rows", len(exhausted)), ("published_rows", len(set(exhausted) & published))))),
        ("decision_6_preopening_rows_remain_held", OrderedDict((
            ("held_rows", len(preopening)), ("published_rows", len(set(preopening) & published))))),
        ("decision_7_no_flattened_fees", OrderedDict((
            ("fee_withholding", OrderedDict((k, fees[k]) for k in FEES)),
            ("published_records_quoting_more_than_one_amount", multi_amount),
            ("of_which_publishing_a_single_fee", len(multi_with_fee)),
            ("rows", multi_with_fee)))),
        ("decision_8_timeshare_outside_hotel_inventory", outside(timeshare)),
        ("decision_9_military_restricted_outside_hotel_inventory", outside(military)),
        ("decision_10_two_states_never_flattened", geography_decision),
        ("reader_safety", OrderedDict((k, safety["counts"][k]) for k in (
            "pet_friendly_with_explicit_refusal", "question_only_pet_friendly", "service_animal_only_pet_friendly",
            "preopening_or_closed_published", "timeshare_or_vacation_ownership_published",
            "military_restricted_published", "misleading_single_fee_published"))),
        ("cross_market_safety",
         "Kansas City carries %d bare-chain-shaped names and %d bare-chain collisions; cross-market collisions %d; "
         "duplicate excluded identities %d (the registration checks searched every census, registry row and live "
         "profile)." % (checks["cross_market_safety"]["BARE_CHAIN_NAMES"],
                        checks["cross_market_safety"]["BARE_CHAIN_COLLISIONS"],
                        checks["cross_market_safety"]["CROSS_MARKET_COLLISIONS"],
                        checks["cross_market_safety"]["DUPLICATE_EXCLUDED_IDENTITIES"])),
        ("not_authorized_by_this_decision", [
            "the source-ready shadow id pkg-kansas-city-mo-24718ac004c967b8, or any other or earlier package",
            "new paid spend or any reopened acquisition",
            "weaker evidence rules or a change to the shared reader or factory code",
            "self-signing identity_resolutions.json (the three dual-brand buildings stay held)",
            "resolving the Hilton Garden Inn Overland Park or Sleep Inn Olathe rebrand holds",
            "publishing ESA Kansas City - Airport - Tiffany Springs, or bypassing its CAPTCHA",
            "revisiting the fake anti-virus Crossland page or using it as evidence",
            "an invented replacement identity, route or domain",
            "publication of any held row, or of a verified-no-pets row as a hotel profile",
            "admitting a timeshare / vacation-ownership or military-restricted identity as a hotel or exclusion",
            "flattening a tiered or multi-part fee into a single number",
            "deploying: this records the launch decision only",
        ]),
        ("policy_package", entry_of(policy_path)),
        ("exclusion_shard", entry_of(shard_path)),
        ("release_contract", entry_of(contract_path)),
        ("identity_census", entry_of(census_path)),
        ("final_partition", entry_of(PARTITION_PATH)),
        ("actionability", entry_of(ACTIONABILITY_PATH)),
        ("clean_authority", entry_of(CLEAN_PATH)),
        ("registered_package", entry_of(AUTHORIZED_PACKAGE_PATH)),
    ))


def _guards(basis: Dict) -> None:
    d1, d2 = basis["decision_1_authorize_registered_cohort"], basis["decision_2_unresolved_rows_remain_held"]
    d3, d4 = basis["decision_3_named_rows_remain_held"], basis["decision_4_founder_rows_remain_held"]
    d5, d6 = basis["decision_5_router_exhausted_rows_remain_held"], basis["decision_6_preopening_rows_remain_held"]
    d7 = basis["decision_7_no_flattened_fees"]
    d8, d9 = basis["decision_8_timeshare_outside_hotel_inventory"], basis["decision_9_military_restricted_outside_hotel_inventory"]
    rc = basis["registration_commit_binding"]

    def outside_ok(d, n):
        return d["rows"] == n and not d["qualifying_census_rows"] and not d["verified_no_pets_exclusions"] \
            and not d["pet_friendly_records"]

    checks = [
        (basis["registered_package_id"] == AUTHORIZED_PACKAGE_ID
         and basis["package_file_digest_field"] == basis["registered_package_digest"],
         "the bound package is %s, not %s" % (basis["registered_package_id"], AUTHORIZED_PACKAGE_ID)),
        (rc["ancestor_of_head"] and rc["same_package_bytes"],
         "registration commit %s does not carry the authorized package bytes: %s" % (REGISTRATION_COMMIT, dict(rc))),
        (basis["registration_classification_source"] == "AUTOMATIC" and basis["classifier_checks_passed"] == 15
         and basis["shared_paths"] == 0 and basis["unknown_paths"] == 0 and basis["full_regression_required"] == "NO",
         "the registration evidence is not automatic / 15 of 15 / 0 shared / 0 unknown / broad NO"),
        (basis["registration_staging_gates"] == "PASS", "the registration staging gates did not pass"),
        (basis["pet_friendly_publication_count"] == COHORT_PET_FRIENDLY
         and basis["verified_no_pets_count"] == COHORT_VERIFIED_NO_PETS,
         "the cohort is %d/%d, not %d/%d" % (basis["pet_friendly_publication_count"], basis["verified_no_pets_count"],
                                             COHORT_PET_FRIENDLY, COHORT_VERIFIED_NO_PETS)),
        (d1["verified_no_pets_published_as_profiles"] == 0, "a verified-no-pets row is also a profile"),
        (d2["unresolved_rows"] == HELD_UNRESOLVED == basis["holds_unresolved"] and d2["published_rows"] == 0,
         "unresolved rows %s" % dict(d2)),
        (all(v["published_rows"] == 0 and "MISSING" not in v["states"] for v in d3.values()),
         "named held rows %s" % json.dumps(d3)),
        (d4["actionability_founder_rows"] == HELD_FOUNDER and d4["published_rows"] == 0
         and d4["dual_brand_rows"] == HELD_DUAL_BRAND
         and len(d4["dual_brand_buildings"]) == HELD_DUAL_BRAND_BUILDINGS
         and d4["other_founder_rows"] == HELD_FOUNDER_KEYS,
         "founder rows do not match: %s" % json.dumps(d4)),
        (d5["held_rows"] == HELD_ROUTER_EXHAUSTED and d5["published_rows"] == 0, "router-exhausted %s" % dict(d5)),
        (d6["held_rows"] == HELD_PREOPENING and d6["published_rows"] == 0, "preopening %s" % dict(d6)),
        (dict(d7["fee_withholding"]) == dict(FEES) and d7["of_which_publishing_a_single_fee"] == 0,
         "fees do not match: %s" % json.dumps(d7)),
        (outside_ok(d8, HELD_TIMESHARE), "a timeshare identity is in hotel inventory: %s" % json.dumps(d8)),
        (outside_ok(d9, HELD_MILITARY), "a military-restricted identity is in hotel inventory: %s" % json.dumps(d9)),
        (basis["decision_10_two_states_never_flattened"]["registration_gate_cross_state"] == "PASS"
         and basis["decision_10_two_states_never_flattened"]["registration_gate_market_text"] == "PASS"
         and basis["decision_10_two_states_never_flattened"]["missouri_qualifying_hotels"] == 189
         and basis["decision_10_two_states_never_flattened"]["kansas_qualifying_hotels"] == 101
         and not basis["decision_10_two_states_never_flattened"]["ks_hotels_mislabeled_mo"]
         and not basis["decision_10_two_states_never_flattened"]["mo_hotels_mislabeled_ks"]
         and not basis["decision_10_two_states_never_flattened"]["seed_rows_state_rewritten"]
         and basis["decision_10_two_states_never_flattened"]["fixed_identities_correct"]
         and not basis["decision_10_two_states_never_flattened"]["minneapolis_st_paul_text_residue"]
         and not basis["decision_10_two_states_never_flattened"]["oregon_portland_text_residue"]
         and basis["decision_10_two_states_never_flattened"]["kansas_city_market_label_correct"]
         and not basis["decision_10_two_states_never_flattened"]["rows_not_in_missouri_or_kansas"],
         "two states / market text: %s" % json.dumps(basis["decision_10_two_states_never_flattened"])),
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
            "registered by %s as COMPOSITE_FRESH_MARKET_DATA_ONLY (automatic base and classification, FAST 15/15, 0 "
            "broad runs), and ADMITTED here by %s, the founder's launch decision for package %s bound to registration "
            "commit %s. The %d unresolved rows -- among them the six dual-brand rows in three buildings (1875 Diamond "
            "Pkwy, 8710 Penrose Ln, 1535 Baltimore Ave), ESA Tiffany Springs and the four preopening hotels -- stay "
            "held by that same decision and publish nothing, as do the Hilton Garden Inn Overland Park and Sleep Inn "
            "Olathe rebrand holds. Missouri and Kansas are two states of this market, never flattened. Hidden from "
            "global navigation and from the sitemap flags exactly as every recently launched market is at this stage."
            % (basis["pet_friendly_publication_count"], basis["verified_no_pets_count"], basis["census_count"],
               SOURCE_ORDER, REGISTRATION_ORDER, WORK_ORDER, basis["registered_package_digest"][:23],
               REGISTRATION_COMMIT, basis["holds_unresolved"]))
    if hit != 1:
        raise SystemExit("%s: expected exactly one %s row, found %d" % (WORK_ORDER, MARKET, hit))

    reason = (
        "Founder authorizes Kansas City / Greater Kansas City, Missouri & Kansas to participate in the next production "
        "assembly as the FORTY-THIRD market, on registered package %s (%s, market bundle %s), bound to registration "
        "commit %s, and does NOT authorize the source-ready shadow id pkg-kansas-city-mo-24718ac004c967b8 or any "
        "earlier Kansas City package. %d of %d identities publish (%d verified-no-pets as exclusions only, %d held) at "
        "a %.2f%% resolution rate with ACTIONABLE UNRESOLVED = 0 and coverage READY. All %d unresolved rows remain "
        "held -- the six dual-brand rows in three buildings (Aloft + Element North Kansas City at 1875 Diamond Pkwy, "
        "AC Hotel + Residence Inn Lenexa City Center at 8710 Penrose Ln, Courtyard + Residence Inn Kansas City "
        "Downtown / Convention Center at 1535 Baltimore Ave), ESA Kansas City - Airport - Tiffany Springs, the four "
        "preopening hotels and the router-exhausted rest; the Hilton Garden Inn Overland Park and Sleep Inn Olathe "
        "rebrand holds stay unresolved and unpublished; no identity_resolutions.json ruling is written or "
        "self-signed; the %d timeshare / vacation-ownership identities and %d military-restricted identities remain "
        "outside qualifying hotel inventory; the shared reader is not weakened; no CAPTCHA is bypassed and the fake "
        "anti-virus Crossland page is never revisited; no replacement identity, route or domain is invented; no paid "
        "spend, no reopened acquisition and no weaker evidence rule is authorized; no tiered or multi-part fee is "
        "flattened. Bound to the readiness packet of %s (%s), itself bound to the current live parent (deploy %s, "
        "release-index digest %s). Founder's words: '%s' Every other market's decision is unchanged, and every other "
        "waiting market remains NOT authorized for launch."
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
              "registration_classification_source", "classifier_checks_passed", "census_count",
              "pet_friendly_publication_count", "verified_no_pets_count", "holds_unresolved",
              "actionable_unresolved_remaining", "resolution_rate", "coverage_ready", "corridor_pages_published"):
        print("%-36s %s" % (k, b[k]))
    print("%-36s %s" % ("registration_commit_binding", json.dumps(b["registration_commit_binding"])))
    for k in ("decision_2_unresolved_rows_remain_held", "decision_3_named_rows_remain_held",
              "decision_4_founder_rows_remain_held", "decision_5_router_exhausted_rows_remain_held",
              "decision_6_preopening_rows_remain_held", "decision_7_no_flattened_fees",
              "decision_8_timeshare_outside_hotel_inventory", "decision_9_military_restricted_outside_hotel_inventory",
              "decision_10_two_states_never_flattened"):
        print("%-36s %s" % (k, json.dumps({kk: vv for kk, vv in b[k].items() if kk not in ("names", "rows")
                                           or not isinstance(vv, list)})))
    print("%-36s %s" % ("reader_safety", json.dumps(b["reader_safety"])))
