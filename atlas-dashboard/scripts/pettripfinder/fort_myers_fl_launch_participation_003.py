"""PTF-FORT-MYERS-FL-FOUNDER-LAUNCH-AUTHORIZATION-003 -- the founder's Fort Myers / Cape Coral / Sanibel launch decision
(cloned in shape from the previous market's 003 writer).

    python -m scripts.pettripfinder.fort_myers_fl_launch_participation_003
    python -m scripts.pettripfinder.fort_myers_fl_launch_participation_003 --write

THIS RECORDS A DECISION, IT DOES NOT MAKE ONE
---------------------------------------------
The founder granted it in this order, in these words (transcribed, nothing signed in anyone's name):

    The founder explicitly authorizes launch of: fort-myers-fl using ONLY the exact registered Fort Myers package
    mechanically resolved from the completed staging order. Bind this decision to: 6a425592. The founder approves the
    existing safe publication cohort: 57 pet-friendly profiles. No publication expansion is authorized. Keep ALL held /
    unresolved rows unpublished.

TWO COMMITS, NAMED APART
------------------------
* ``REGISTRATION_COMMIT`` 19c47422 is the commit that ADDED the registered package file (the first registration commit).
* ``FOUNDER_BINDING_COMMIT`` 6a425592 is the BUILD commit the registration's readiness packet was computed on (the
  staging-gate module stopped importing a shared renderer; no package byte moved). The founder bound the decision to
  6a425592, NOT to 19c47422.

The package id is never typed from a recap: it is the one package file under markets/packages/fort-myers-fl at
6a425592, which 19c47422 added, and it must equal the readiness packet's ``sealed_package_id``. Its content is the
source-ready shadow package pkg-fort-myers-fl-68b3cfa8bc4758c5 (PTF-FORT-MYERS-FL-HARDENED-SOURCE-READY-001); the
shadow id is never authorized, and the source-ready order's failed first seal (FAST J FAIL, outputs discarded, never
committed) has no package file at all.

The founder kept unpublished: all 51 unresolved rows; the Comfort Suites / MainStay Suites pair at 9455 Old Luckett
(two hotels on one campus; no identity_resolutions.json ruling); 4760 S Cleveland (Quality Inn is the current identity
candidate and stays held, Travelodge is retired rebrand history, and no Travelodge evidence migrates -- the published
Travelodge at 13353 N Cleveland is a different building); Latitude 26 Waterfront Inn & Suites (conflicting county
evidence; no new Lee / Collier ruling); Pink Shell Beach Resort & Marina and Edison Beach House (first-party refusals
the shared reader does not classify; the shared reader is not modified and no disposition is forced). This module
writes that decision down. It must never be run to admit a market on its own initiative, and it refuses if the
committed state does not match what the founder was shown.

A FIRST AUTHORIZATION, NOT A RE-AUTHORIZATION: Fort Myers has never been authorized or deployed, so no
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import launch_participation as LP     # noqa: E402

WORK_ORDER = "PTF-FORT-MYERS-FL-FOUNDER-LAUNCH-AUTHORIZATION-003"
REGISTRATION_ORDER = "PTF-FORT-MYERS-FL-REGISTRATION-AND-STAGING-002"
SOURCE_ORDER = "PTF-FORT-MYERS-FL-HARDENED-SOURCE-READY-001"
MARKET = "fort-myers-fl"
DECIDED_ON = "2026-10-08"
PACKAGE = _REPO_ROOT / "launch_packages" / "pettripfinder"
REPORTS = PACKAGE / "markets" / "reports"
FOUNDER_PACKET_PATH = REPORTS / "fort_myers_fl_registration_authorization_readiness.json"
CLASSIFICATION_PATH = REPORTS / "fort_myers_fl_registration_classification.json"
CHECKS_PATH = REPORTS / "fort_myers_fl_registration_checks_002.json"
ACTIONABILITY_PATH = REPORTS / "fort_myers_fl_actionability_001.json"
CLEAN_PATH = REPORTS / "fort_myers_fl_clean_authority_001.json"
FEES_PATH = REPORTS / "fort_myers_fl_fee_withholding_001.json"
SAFETY_PATH = REPORTS / "fort_myers_fl_publication_safety_audit_001.json"
OPERATING_PATH = REPORTS / "fort_myers_fl_operating_status_accounting_001.json"
PARTITION_PATH = PACKAGE / "fort_myers_fl_final_partition_001.json"
PATH = LP.PARTICIPATION_PATH

REGISTRATION_COMMIT = "19c47422"
FOUNDER_BINDING_COMMIT = "6a425592"
#: the source-ready SHADOW package (its content is registered as the authorized package, the shadow id never is)
REFUSED_PACKAGE_PREFIXES = ("pkg-fort-myers-fl-68b3cfa8",)
SOURCE_PACKAGE = "pkg-fort-myers-fl-68b3cfa8bc4758c5"
PACKAGES_DIR = PACKAGE / "markets" / "packages" / MARKET
#: what may change between the founder-binding commit and the commit this decision is written on: the registration
#: order's own reports and final report, nothing the assembler reads as market data
POST_BINDING_ALLOWED = re.compile(r"^(atlas-dashboard/launch_packages/pettripfinder/markets/reports/fort_myers_fl_"
                                  r"registration_[a-z_0-9]+\.json|PTF-FORT-MYERS-FL-REGISTRATION-AND-STAGING-002_"
                                  r"FINAL\.md)$")

COHORT_PET_FRIENDLY = 57
COHORT_VERIFIED_NO_PETS = 34
CENSUS = 142
HELD_UNRESOLVED = 51
HELD_ROUTER_EXHAUSTED = 49
#: the two founder-class rows: first-party refusals the shared reader does not classify
HELD_FOUNDER_KEYS = ["edison beach house hotel", "pink shell beach resort and marina"]
HELD_PREOPENING = 0
#: the held rows the founder named, by registration-gate group (each must be held and publish nothing)
NAMED_HELD_GROUPS = OrderedDict((
    ("old_luckett_9455_comfort_suites_and_mainstay", ("founder_ruling_old_luckett_dual_brand", 2)),
    ("s_cleveland_4760_quality_inn_travelodge_retired", ("founder_ruling_4760_cleveland_rebrand", 1)),
    ("latitude_26_waterfront", ("founder_ruling_latitude_26", 5)),
    ("pink_shell_and_edison_beach_house", ("founder_ruling_pink_shell_edison", 2)),
))
FEES = OrderedDict((("fees_published", 5), ("tiered_fees_withheld", 22), ("unsafe_single_fees_withheld", 5),
                    ("misleading_single_fees_published", 0)))
NONOPERATING = ("TEMPORARILY_CLOSED", "CLOSED_FOR_REBUILD", "PERMANENTLY_CLOSED", "DEMOLISHED", "PREOPENING")

FOUNDER_WORDS = ("The founder explicitly authorizes launch of: fort-myers-fl using ONLY the exact registered Fort Myers "
                 "package mechanically resolved from the completed staging order. Bind this decision to: 6a425592. "
                 "The founder approves the existing safe publication cohort: 57 pet-friendly profiles. No publication "
                 "expansion is authorized. Keep ALL held / unresolved rows unpublished.")

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


def _is_ancestor(older: str, newer: str) -> bool:
    return subprocess.run(("git", "merge-base", "--is-ancestor", older, newer), cwd=str(_REPO_ROOT)).returncode == 0


def _registered_package_id() -> str:
    """The package the founder-binding commit carries, read from git (never typed from a recap): exactly one package
    file is present under markets/packages/fort-myers-fl at 6a425592, and it is the one 19c47422 ADDED."""
    rel = "atlas-dashboard/" + _rel(PACKAGES_DIR) + "/"
    at_binding = [p for p in _git("ls-tree", "-r", "--name-only", "--full-tree", FOUNDER_BINDING_COMMIT).splitlines()
                  if p.startswith(rel) and p.endswith(".json")]
    added = [p for p in _git("diff-tree", "--no-commit-id", "--name-only", "--diff-filter=A", "-r",
                             REGISTRATION_COMMIT).splitlines() if p.startswith(rel) and p.endswith(".json")]
    if len(at_binding) != 1 or added != at_binding:
        raise SystemExit("%s: %s carries %s and %s added %s -- not exactly one registered package"
                         % (WORK_ORDER, FOUNDER_BINDING_COMMIT, at_binding, REGISTRATION_COMMIT, added))
    return Path(at_binding[0]).stem


def _commit_binding(package_path: Path, packet: Dict) -> Dict:
    """The founder bound the decision to 6a425592: it must exist, descend from the registration commit, be an ancestor
    of HEAD, carry the authorized package's exact bytes, predate the readiness packet, and nothing the assembler reads
    as market data may have moved after it."""
    binding = _git("rev-parse", "--verify", FOUNDER_BINDING_COMMIT + "^{commit}")
    registration = _git("rev-parse", "--verify", REGISTRATION_COMMIT + "^{commit}")
    head = _git("rev-parse", "HEAD")
    rel = "atlas-dashboard/" + _rel(package_path)
    at_binding = _git("rev-parse", "%s:%s" % (binding, rel))
    at_registration = _git("rev-parse", "%s:%s" % (registration, rel))
    in_tree = _git("hash-object", str(package_path))
    since = [p for p in _git("diff", "--name-only", binding, head).splitlines() if p]
    committed_at = _git("show", "-s", "--format=%cI", binding)
    prepared_at = packet.get("prepared_at")
    packet_after = (datetime.fromisoformat(prepared_at.replace("Z", "+00:00"))
                    >= datetime.fromisoformat(committed_at).astimezone(timezone.utc)) if prepared_at else False
    return OrderedDict((
        ("founder_binding_commit", binding), ("registration_commit", registration),
        ("registration_commit_is_ancestor_of_binding", _is_ancestor(registration, binding)),
        ("binding_is_ancestor_of_head", _is_ancestor(binding, head)),
        ("package_path", rel), ("package_blob_at_binding_commit", at_binding),
        ("package_blob_at_registration_commit", at_registration), ("package_blob_in_tree", in_tree),
        ("same_package_bytes", at_binding == in_tree == at_registration),
        ("binding_committed_at", committed_at), ("readiness_packet_prepared_at", prepared_at),
        ("readiness_packet_prepared_after_binding_commit", packet_after),
        ("paths_changed_since_binding", since),
        ("only_registration_reports_changed_since_binding", all(POST_BINDING_ALLOWED.match(p) for p in since)),
        ("not_bound_to", "19c47422 (the first registration commit; its staging-gate module imported a shared "
                         "renderer and the first readiness packet refused it)"),
    ))


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
        raise SystemExit("%s: the readiness packet binds %r; the founder-binding commit %s carries %s"
                         % (WORK_ORDER, bound, FOUNDER_BINDING_COMMIT, package_id))
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
    fees, safety, operating = _load(FEES_PATH), _load(SAFETY_PATH), _load(OPERATING_PATH)
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
    held = checks["held_row_safety"]
    named = OrderedDict()
    for label, (group, n) in NAMED_HELD_GROUPS.items():
        named[label] = OrderedDict((("registration_gate_group", group), ("expected_rows", n),
                                    ("rows", held[group]["rows"]), ("published_rows", held[group]["published"])))
    cleveland, luckett = checks["founder_ruling_4760_s_cleveland"], checks["founder_ruling_9455_old_luckett"]
    named["s_cleveland_4760_quality_inn_travelodge_retired"].update((
        ("census_classification", [c["classification"] for c in cleveland["census"]]),
        ("seed_or_policy_rows_at_4760", len(cleveland["seed_rows_at_4760"]) + len(cleveland["pet_friendly_at_4760"])
         + len(cleveland["verified_no_pets_at_4760"])),
        ("travelodge_evidence_migrated_to_4760", cleveland["TRAVELODGE_EVIDENCE_MIGRATED_TO_4760"]),
        ("quality_inn_4760_promoted", cleveland["QUALITY_INN_4760_PROMOTED"]),
        ("published_travelodge_is_a_different_building",
         [(r["address"], r["postal_code"]) for r in cleveland["travelodge_published_records"]]),
    ))
    named["old_luckett_9455_comfort_suites_and_mainstay"].update((
        ("census_classification", [c["classification"] for c in luckett["census"]]),
        ("seed_or_policy_rows_at_9455", len(luckett["seed_rows_at_9455"]) + len(luckett["pet_friendly_at_9455"])
         + len(luckett["verified_no_pets_at_9455"])),
    ))
    named["latitude_26_waterfront"]["census_states"] = checks["founder_ruling_latitude_26"]

    mu, txt = checks["municipality_safety"], checks["market_text_safety"]
    gates = checks["gates"]
    geography_decision = OrderedDict((
        ("registration_gate_municipality", gates.get("municipality_safety")),
        ("registration_gate_naples_collier", gates.get("naples_collier_safety")),
        ("registration_gate_boundary_island", gates.get("boundary_island_safety")),
        ("registration_gate_market_text", gates.get("market_text_safety")),
        ("qualifying_by_county", mu["QUALIFYING_BY_COUNTY"]),
        ("wrong_city_fort_myers_identities", mu["WRONG_CITY_FORT_MYERS_IDENTITIES"]),
        ("own_municipality_flattened_to_fort_myers", mu["OWN_MUNICIPALITY_FLATTENED_TO_FORT_MYERS"]),
        ("naples_profiles_admitted", mu["NAPLES_PROFILES_ADMITTED"]),
        ("naples_seed_rows", mu["NAPLES_SEED_ROWS"]),
        ("not_florida", mu["NOT_FLORIDA"]),
        ("seed_rows_address_rewritten", mu["SEED_ROWS_ADDRESS_REWRITTEN"]),
        ("published_by_municipality", mu["published_by_municipality"]),
        ("clone_text_residue", OrderedDict((k, v) for k, v in txt.items() if k.endswith("_RESIDUE"))),
        ("fort_myers_market_label_correct", txt["FORT_MYERS_MARKET_LABEL_CORRECT"]),
        ("market_label", txt["market_label"]),
        ("policy_package_market_field", txt["policy_package_market_field"]),
        ("rows_not_in_florida", sorted(h["identity_key"] for h in census["hotels"] if (h.get("state") or "") != "FL")),
    ))

    non = census.get("non_admitted") or ()
    timeshare = [h["canonical_name"] for h in non
                 if h["classification"] == "NON_LODGING" and str(h.get("classification_reason")).startswith("TIMESHARE")]
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

    # the operating-status rows mark every RESOLVED row "published" (pet-friendly profiles and verified-no-pets
    # exclusions alike); the cohort that becomes hotel profiles is the pet-friendly set
    status_rows = operating["operating_status_accounting"]["rows"]
    published_status = OrderedDict(sorted(
        (s, sum(1 for r in status_rows if r["identity_key"] in published and r["status"] == s))
        for s in {r["status"] for r in status_rows if r["identity_key"] in published}))
    nonoperating_published = sorted(r["identity_key"] for r in status_rows
                                    if r["identity_key"] in published and r["status"] in NONOPERATING + ("STATUS_UNKNOWN",))

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
         "read mechanically: the one package file under markets/packages/%s at founder-binding commit %s (added by "
         "registration commit %s), equal to the readiness packet's sealed_package_id" %
         (MARKET, FOUNDER_BINDING_COMMIT, REGISTRATION_COMMIT)),
        ("founder_binding_commit", FOUNDER_BINDING_COMMIT),
        ("commit_binding", _commit_binding(package_path, packet)),
        ("refused_packages", [
            "%s (the source-ready SHADOW package; its content is registered as %s, the shadow id is never authorized)"
            % (SOURCE_PACKAGE, binds["sealed_package_id"]),
            "the source-ready order's failed first seal (FAST J FAIL; outputs discarded, never committed, no package "
            "file exists)"]),
        ("packages_on_disk", sorted(p.stem for p in PACKAGES_DIR.glob("*.json"))),
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
        ("projected_accounting", OrderedDict((k, v) for k, v in checks["projected_accounting"].items()
                                             if k != "fort_myers_served_routes")),
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
            ("verified_no_pets_published_as_profiles", len(published & excluded)),
            ("unapproved_fort_myers_profiles", checks["UNAPPROVED_FORT_MYERS_PROFILES"])))),
        ("decision_2_unresolved_rows_remain_held", OrderedDict((
            ("unresolved_rows", len(rows)), ("published_rows", len({r["identity_key"] for r in rows} & published))))),
        ("decision_3_named_rows_remain_held", named),
        ("decision_4_founder_rows_remain_held", OrderedDict((
            ("actionability_founder_rows", len(founder_rows)),
            ("founder_rows", sorted(r["identity_key"] for r in founder_rows)),
            ("published_rows", len({r["identity_key"] for r in founder_rows} & published)),
            ("shared_reader_modified", False),
            ("disposition_forced", False),
            ("identity_resolutions_ruling_written", bool(checks["identity_resolutions_written"]))))),
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
        ("decision_9_private_condo_residence_rental_unpublished", OrderedDict((
            ("private_condo_residence_or_rental_rows", held["private_condo_residence_or_rental"]["rows"]),
            ("private_condo_residence_or_rental_published", held["private_condo_residence_or_rental"]["published"]),
            ("timeshare_rows", held["timeshare"]["rows"]),
            ("timeshare_published", held["timeshare"]["published"])))),
        ("decision_10_operating_status", OrderedDict((
            ("published_by_status", published_status),
            ("nonoperating_or_unknown_published", nonoperating_published),
            ("rows_with_a_nonoperating_signal",
             operating["operating_status_accounting"]["rows_with_a_nonoperating_signal"]),
            ("nonoperating_published", operating["operating_status_accounting"]["NONOPERATING_PUBLISHED"]),
            ("current_operation_proven_for_every_published_property",
             operating["operating_status_accounting"]["CURRENT_OPERATION_PROVEN_FOR_EVERY_PUBLISHED_PROPERTY"])))),
        ("decision_11_municipalities_never_flattened", geography_decision),
        ("decision_12_route_schemes", OrderedDict((
            ("destinations_checked", checks["route_scheme_safety"]["destinations_checked"]),
            ("invalid_route_schemes", checks["route_scheme_safety"]["INVALID_ROUTE_SCHEMES"]),
            ("fast_rule_j", checks["fast_receipt"]["rule_J"])))),
        ("reader_safety", OrderedDict((k, safety["counts"][k]) for k in safety["counts"])),
        ("cross_market_safety",
         "Fort Myers carries %d bare-chain-shaped names and %d bare-chain collisions; cross-market collisions %d; "
         "duplicate excluded identities %d; live properties moved or displaced %d (the registration checks searched "
         "every census, registry row and live profile)."
         % (checks["cross_market_safety"]["BARE_CHAIN_NAMES"], checks["cross_market_safety"]["BARE_CHAIN_COLLISIONS"],
            checks["cross_market_safety"]["CROSS_MARKET_COLLISIONS"],
            checks["cross_market_safety"]["DUPLICATE_EXCLUDED_IDENTITIES"],
            checks["cross_market_safety"]["LIVE_PROPERTIES_MOVED_OR_DISPLACED"])),
        ("not_authorized_by_this_decision", [
            "the source-ready shadow id %s, the source-ready order's failed first seal, or any other or earlier "
            "package" % SOURCE_PACKAGE,
            "binding to the first registration commit 19c47422",
            "any publication expansion beyond the 57 registered pet-friendly profiles",
            "new paid spend, provider retries, browser work or any reopened acquisition",
            "weaker evidence rules or a change to the shared reader or factory code",
            "writing or self-signing identity_resolutions.json",
            "resolving the 9455 Old Luckett shared-building identity, or publishing Comfort Suites or MainStay Suites",
            "promoting the held Quality Inn at 4760 S Cleveland, or migrating retired Travelodge evidence to it",
            "a new Lee / Collier county ruling for Latitude 26 Waterfront Inn & Suites",
            "forcing a verified-no-pets or pet-friendly disposition on Pink Shell or Edison Beach House",
            "an invented replacement identity, route, ZIP or domain",
            "publication of any held row, or of a verified-no-pets row as a hotel profile",
            "publication of a nonoperating, closed, preopening or status-unknown identity",
            "admitting a timeshare / vacation-ownership, vacation rental or private condo / residence identity",
            "labelling a Cape Coral, Fort Myers Beach, Sanibel, Captiva, Estero, Bonita Springs or North Fort Myers "
            "premises as Fort Myers, or admitting any Naples / Collier premises",
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
        ("operating_status", entry_of(OPERATING_PATH)),
        ("registered_package", entry_of(package_path)),
    ))


def _guards(basis: Dict, package_id: str) -> None:
    d1, d2 = basis["decision_1_authorize_registered_cohort"], basis["decision_2_unresolved_rows_remain_held"]
    d3, d4 = basis["decision_3_named_rows_remain_held"], basis["decision_4_founder_rows_remain_held"]
    d5, d6 = basis["decision_5_router_exhausted_rows_remain_held"], basis["decision_6_preopening_rows_remain_held"]
    d7, d8 = basis["decision_7_no_flattened_fees"], basis["decision_8_timeshare_outside_hotel_inventory"]
    d9, d10 = basis["decision_9_private_condo_residence_rental_unpublished"], basis["decision_10_operating_status"]
    geo, d12 = basis["decision_11_municipalities_never_flattened"], basis["decision_12_route_schemes"]
    cb = basis["commit_binding"]
    pa = basis["projected_accounting"]
    cleveland = d3["s_cleveland_4760_quality_inn_travelodge_retired"]
    luckett = d3["old_luckett_9455_comfort_suites_and_mainstay"]
    latitude = d3["latitude_26_waterfront"]["census_states"]

    checks = [
        (basis["registered_package_id"] == package_id
         and basis["package_file_digest_field"] == basis["registered_package_digest"]
         and not package_id.startswith(REFUSED_PACKAGE_PREFIXES) and basis["packages_on_disk"] == [package_id],
         "the bound package is %s, not %s (on disk %s)" % (basis["registered_package_id"], package_id,
                                                           basis["packages_on_disk"])),
        (basis["content_identical_to_source_ready"] == SOURCE_PACKAGE and basis["content_fields_identical"],
         "the registered content is not the source-ready package's"),
        (cb["founder_binding_commit"].startswith(FOUNDER_BINDING_COMMIT)
         and not cb["founder_binding_commit"].startswith(REGISTRATION_COMMIT)
         and cb["registration_commit_is_ancestor_of_binding"] and cb["binding_is_ancestor_of_head"]
         and cb["same_package_bytes"] and cb["readiness_packet_prepared_after_binding_commit"]
         and cb["only_registration_reports_changed_since_binding"],
         "founder-binding commit %s does not carry the authorized package: %s" % (FOUNDER_BINDING_COMMIT, dict(cb))),
        (basis["registration_classification_source"] == "AUTOMATIC" and basis["classifier_checks_passed"] == 15
         and basis["shared_paths"] == 0 and basis["unknown_paths"] == 0 and basis["full_regression_required"] == "NO"
         and basis["broad_regression_runs"] == 0 and basis["registration_class"] == "COMPOSITE_FRESH_MARKET_DATA_ONLY",
         "the registration evidence is not automatic / 15 of 15 / 0 shared / 0 unknown / broad NO"),
        (basis["registration_staging_gates"] == "PASS", "the registration staging gates did not pass"),
        (pa["FORT_MYERS_PROJECTED_PROFILES"] == COHORT_PET_FRIENDLY and pa["FORT_MYERS_RELEASE_INDEX_ROUTES"] == 62
         and pa["FORT_MYERS_SERVED_ROUTES"] == 63 and pa["CANDIDATE_MARKETS"] == 46
         and pa["CANDIDATE_PROFILES"] == 4430 and pa["CANDIDATE_RELEASE_INDEX_ROUTES"] == 4869
         and pa["CANDIDATE_SERVED_ROUTES"] == 4948, "projected accounting %s" % dict(pa)),
        (basis["pet_friendly_publication_count"] == COHORT_PET_FRIENDLY
         and basis["verified_no_pets_count"] == COHORT_VERIFIED_NO_PETS and basis["census_count"] == CENSUS,
         "the cohort is %d/%d, not %d/%d" % (basis["pet_friendly_publication_count"], basis["verified_no_pets_count"],
                                             COHORT_PET_FRIENDLY, COHORT_VERIFIED_NO_PETS)),
        (d1["verified_no_pets_published_as_profiles"] == 0 and d1["unapproved_fort_myers_profiles"] == 0,
         "a verified-no-pets row is also a profile, or an unapproved profile exists: %s" % dict(d1)),
        (d2["unresolved_rows"] == HELD_UNRESOLVED == basis["holds_unresolved"] and d2["published_rows"] == 0,
         "unresolved rows %s" % dict(d2)),
        (all(v["published_rows"] == 0 and v["rows"] == v["expected_rows"] for v in d3.values()),
         "named held rows %s" % json.dumps(d3)),
        (cleveland["census_classification"] == ["SAME_IDENTITY_REBRAND_SUCCESSOR"]
         and cleveland["seed_or_policy_rows_at_4760"] == 0 and cleveland["travelodge_evidence_migrated_to_4760"] == 0
         and cleveland["quality_inn_4760_promoted"] == 0
         and all(not a.startswith("4760") for a, _z in cleveland["published_travelodge_is_a_different_building"]),
         "4760 S Cleveland ruling %s" % json.dumps(cleveland)),
        (luckett["census_classification"] == ["SAME_CAMPUS_DISTINCT_ENTITY"] * 2
         and luckett["seed_or_policy_rows_at_9455"] == 0, "9455 Old Luckett ruling %s" % json.dumps(luckett)),
        ("OUTSIDE_MARKET" in latitude.get("latitude 26 waterfront inn and suites", ""),
         "Latitude 26 Waterfront Inn & Suites' registered treatment moved: %s" % json.dumps(latitude)),
        (d4["founder_rows"] == HELD_FOUNDER_KEYS and d4["published_rows"] == 0
         and not d4["identity_resolutions_ruling_written"],
         "founder rows do not match: %s" % json.dumps(d4)),
        (d5["held_rows"] == HELD_ROUTER_EXHAUSTED and d5["published_rows"] == 0, "router-exhausted %s" % dict(d5)),
        (d6["held_rows"] == HELD_PREOPENING and d6["published_rows"] == 0, "preopening %s" % dict(d6)),
        (dict(d7["fee_withholding"]) == dict(FEES) and d7["of_which_publishing_a_single_fee"] == 0
         and d7["withheld_fees_flattened"] == 0, "fees do not match: %s" % json.dumps(d7)),
        (not d8["qualifying_census_rows"] and not d8["verified_no_pets_exclusions"] and not d8["pet_friendly_records"],
         "a timeshare identity is in hotel inventory: %s" % json.dumps(d8)),
        (d9["private_condo_residence_or_rental_published"] == 0 and d9["timeshare_published"] == 0,
         "private condo / residence / rental: %s" % json.dumps(d9)),
        (not d10["nonoperating_or_unknown_published"] and d10["nonoperating_published"] == 0
         and d10["current_operation_proven_for_every_published_property"]
         and sum(d10["published_by_status"].values()) == COHORT_PET_FRIENDLY,
         "operating status: %s" % json.dumps(d10)),
        (geo["registration_gate_municipality"] == "PASS" and geo["registration_gate_naples_collier"] == "PASS"
         and geo["registration_gate_boundary_island"] == "PASS" and geo["registration_gate_market_text"] == "PASS"
         and not geo["wrong_city_fort_myers_identities"] and not geo["own_municipality_flattened_to_fort_myers"]
         and not geo["naples_profiles_admitted"] and not geo["naples_seed_rows"] and not geo["not_florida"]
         and not geo["seed_rows_address_rewritten"] and not any(geo["clone_text_residue"].values())
         and geo["fort_myers_market_label_correct"] and not geo["rows_not_in_florida"],
         "municipalities / Naples / market text: %s" % json.dumps(geo)),
        (d12["invalid_route_schemes"] == 0 and d12["fast_rule_j"] == "PASS", "route schemes: %s" % dict(d12)),
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
            "broad runs), and ADMITTED here by %s, the founder's launch decision for package %s bound to commit %s. "
            "The %d unresolved rows -- among them the Comfort Suites / MainStay Suites pair at 9455 Old Luckett, the "
            "held Quality Inn at 4760 S Cleveland, Latitude 26 Waterfront, Pink Shell and Edison Beach House -- stay "
            "held by that same decision and publish nothing. Municipalities are never flattened: Cape Coral, Fort "
            "Myers Beach, Sanibel, Captiva, Estero, Bonita Springs and North Fort Myers premises publish as their own "
            "municipality, and no Naples / Collier premises is admitted. Hidden from global navigation and from the "
            "sitemap flags exactly as every recently launched market is at this stage."
            % (basis["pet_friendly_publication_count"], basis["verified_no_pets_count"], basis["census_count"],
               SOURCE_ORDER, REGISTRATION_ORDER, WORK_ORDER, basis["registered_package_digest"][:23],
               FOUNDER_BINDING_COMMIT, basis["holds_unresolved"]))
    if hit != 1:
        raise SystemExit("%s: expected exactly one %s row, found %d" % (WORK_ORDER, MARKET, hit))

    reason = (
        "Founder authorizes Fort Myers / Cape Coral / Sanibel, Florida to participate in the next production assembly "
        "as the FORTY-SIXTH market, on registered package %s (%s, market bundle %s), bound to commit %s (the BUILD "
        "commit of the readiness packet; NOT the first registration commit %s), and does NOT authorize the "
        "source-ready shadow id %s or the source-ready order's failed first seal. %d of %d identities publish (%d "
        "verified-no-pets as exclusions only, %d held) at a %.2f%% resolution rate with ACTIONABLE UNRESOLVED = 0 and "
        "coverage READY. No publication expansion is authorized. All %d unresolved rows remain held -- Comfort Suites "
        "and MainStay Suites at 9455 Old Luckett (two hotels on one campus; the shared-building identity is not "
        "resolved here), the Quality Inn at 4760 S Cleveland (the current identity candidate, held and not promoted; "
        "Travelodge is retired rebrand history and none of its policy evidence migrates; the published Travelodge at "
        "13353 N Cleveland is a different building), Latitude 26 Waterfront Inn & Suites (conflicting county "
        "evidence; no new Lee / Collier ruling), Pink Shell Beach Resort & Marina and Edison Beach House (first-party "
        "refusals the shared reader does not classify; the shared reader is not modified and no disposition is "
        "forced) and the router-exhausted rest; no identity_resolutions.json ruling is written or self-signed; the %d "
        "timeshare / vacation-ownership identities and the private condo / residence / rental identities remain "
        "outside qualifying hotel inventory; no nonoperating, closed or preopening identity publishes; every Cape "
        "Coral, Fort Myers Beach, Sanibel, Captiva, Estero, Bonita Springs and North Fort Myers premises publishes as "
        "its own municipality and no Naples / Collier premises is admitted; no paid spend, no provider retry, no "
        "browser work and no weaker evidence rule is authorized; no tiered, capped, conditional or multi-amount fee "
        "is flattened. Bound to the readiness packet of %s (%s), itself bound to the current live parent (deploy %s, "
        "release-index digest %s). Founder's words: '%s' Every other market's decision is unchanged, and every other "
        "waiting market remains NOT authorized for launch."
        % (basis["registered_package_id"], basis["registered_package_digest"], basis["market_bundle_sha256"],
           basis["commit_binding"]["founder_binding_commit"], REGISTRATION_COMMIT, SOURCE_PACKAGE,
           basis["pet_friendly_publication_count"], basis["census_count"], basis["verified_no_pets_count"],
           basis["holds_unresolved"], basis["resolution_rate"] * 100, basis["holds_unresolved"],
           basis["decision_8_timeshare_outside_hotel_inventory"]["rows"],
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
              "actionable_unresolved_remaining", "resolution_rate", "coverage_ready", "corridor_pages_published",
              "packages_on_disk"):
        print("%-36s %s" % (k, b[k]))
    print("%-36s %s" % ("commit_binding", json.dumps(b["commit_binding"])))
    for k in ("decision_2_unresolved_rows_remain_held", "decision_3_named_rows_remain_held",
              "decision_4_founder_rows_remain_held", "decision_5_router_exhausted_rows_remain_held",
              "decision_6_preopening_rows_remain_held", "decision_7_no_flattened_fees",
              "decision_8_timeshare_outside_hotel_inventory", "decision_9_private_condo_residence_rental_unpublished",
              "decision_10_operating_status", "decision_11_municipalities_never_flattened",
              "decision_12_route_schemes"):
        print("%-36s %s" % (k, json.dumps({kk: vv for kk, vv in b[k].items() if kk not in ("names", "rows")
                                           or not isinstance(vv, list)})))
    print("%-36s %s" % ("reader_safety", json.dumps(b["reader_safety"])))
