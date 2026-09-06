"""PTF-TOLEDO-OH-NEW-MARKET-001 -- the Toledo shadow market's own gates.

Toledo is NOT a registered market. This order builds a complete, evidence-bound
shadow market and stops at the serialized promotion boundary, so every gate here
asserts two kinds of thing:

1. **The shadow market is internally sound** -- its contract parses, its postal
   partition is a partition, its census rows carry the evidence that admitted
   them, its routes carry the identity they claim to serve, and no policy fact
   has leaked into an identity record.
2. **The boundary held** -- Toledo is absent from every registry, pin and
   authority that would make it a live market, and this order changed none of
   them.

The second kind matters as much as the first. PTF-047 established that
registering market N+1 invalidates the current production deployment record;
a new-market order that quietly created ``markets/toledo-oh.json`` would look
successful and would have broken the ten live markets.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import pytest

from scripts.pettripfinder.discovery.market_config import load_market_config
from scripts.pettripfinder.markets import contract as MC
from scripts.pettripfinder.site_data import normalize_name

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE = REPO_ROOT / "launch_packages" / "pettripfinder"
REPORTS = PACKAGE / "markets" / "reports"
MARKET = "toledo-oh"

PROPOSED_CONTRACT = PACKAGE / "markets" / "proposed" / "toledo-oh.json"
PROPOSED_CENSUS = PACKAGE / "identity_census_proposed" / "toledo-oh.json"
OWNED_EVIDENCE = REPORTS / "toledo_oh_owned_evidence_001.json"
LEAD_SOURCES = REPORTS / "toledo_oh_lead_sources_001.json"
BRAND_CITY_PAGES = REPORTS / "toledo_oh_brand_city_pages_001.json"
RECONCILIATION = REPORTS / "toledo_oh_census_reconciliation_001.json"
GAP_MATRIX = REPORTS / "toledo_oh_competitor_gap_matrix_001.json"
ROUTING = REPORTS / "toledo_oh_routing_001.json"
ATTENDED = REPORTS / "toledo_oh_attended_capture_001.json"
CLEAN_AUTHORITY = REPORTS / "toledo_oh_clean_authority_001.json"
EVIDENCE_AUDIT = REPORTS / "toledo_oh_evidence_audit_001.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


# --------------------------------------------------------------------------- #
# The serialized boundary. These run first because nothing else matters if the
# order crossed it.
# --------------------------------------------------------------------------- #

def test_toledo_is_not_a_registered_market():
    """markets/*.json IS the registry. Toledo must not be in it."""
    registered = {p.stem for p in (PACKAGE / "markets").glob("*.json")}
    assert MARKET not in registered
    assert MARKET not in {m.market_id for m in MC.load_markets()}


def test_toledo_has_no_authority_shard_and_no_registered_census():
    assert not (PACKAGE / "markets" / "authority" / MARKET).exists()
    assert not (PACKAGE / "identity_census" / ("%s.json" % MARKET)).exists()
    assert not (PACKAGE / ("hotel_policy_facts_%s.json" % MARKET)).exists()


def test_toledo_is_absent_from_every_current_state_pin():
    pins = REPO_ROOT / "tests" / "pettripfinder" / "pins"
    market_state = _load(pins / "market_state.json")
    deployment = _load(pins / "deployment_state.json")
    assert MARKET not in market_state["markets"]
    for block in ("live", "source"):
        assert MARKET not in deployment[block]["participating_markets"]
        assert MARKET not in deployment[block]["profile_counts"]


def test_toledo_has_no_release_contract_and_no_launch_participation():
    assert not (REPO_ROOT / "deploy" / "netlify" / "release_contracts"
                / ("%s.json" % MARKET)).is_file()
    participation = REPO_ROOT / "deploy" / "netlify" / "launch_participation.json"
    if participation.is_file():
        assert MARKET not in json.dumps(_load(participation))


def test_production_truth_is_unchanged_by_this_order():
    """The ten live markets, 786 profiles and 945 routes this order started from."""
    live = _load(REPO_ROOT / "tests" / "pettripfinder" / "pins"
                 / "deployment_state.json")["live"]
    assert live["deploy_id"] == "6a9d33f5dc8c3d1cf9464376"
    assert len(live["participating_markets"]) == 10
    assert live["total_profiles"] == 786
    assert live["sitemap_route_count"] == 945


# --------------------------------------------------------------------------- #
# Geography.
# --------------------------------------------------------------------------- #

def test_discovery_config_loads_and_is_ohio_only():
    cfg = load_market_config(MARKET)
    assert cfg.market_id == MARKET
    assert cfg.state == "OH"
    assert len(cfg.cells) >= 12
    for cell in cfg.cells:
        assert cfg.bounds.contains(cell.center_lat, cell.center_lng), cell.cell_id


def test_discovery_box_does_not_overlap_a_committed_market_box():
    """Toledo's box must not sit inside another market's committed box."""
    tol = load_market_config(MARKET).bounds
    for other in ("cleveland-akron-canton-oh", "dayton-oh", "detroit-ann-arbor-mi",
                  "columbus-oh", "cincinnati-oh"):
        b = load_market_config(other).bounds
        overlaps = (tol.min_lat < b.max_lat and tol.max_lat > b.min_lat
                    and tol.min_lng < b.max_lng and tol.max_lng > b.min_lng)
        assert not overlaps, "toledo-oh discovery box overlaps %s" % other


def test_proposed_contract_parses_against_the_real_contract_module():
    cfg = MC.parse_market(_load(PROPOSED_CONTRACT), source=str(PROPOSED_CONTRACT))
    assert cfg.market_id == MARKET
    assert cfg.states == ("OH",)
    assert cfg.route_mode == MC.ROUTE_MODE_MARKET_PREFIXED
    assert cfg.census_membership_basis == MC.MEMBERSHIP_CORRIDOR_REGISTRY
    assert len(cfg.corridors) >= 10


def test_the_postal_partition_is_a_partition():
    """Every ZIP is claimed by exactly one corridor, or the market places a hotel twice."""
    cfg = MC.parse_market(_load(PROPOSED_CONTRACT), source=str(PROPOSED_CONTRACT))
    claims = Counter(z for c in cfg.corridors for z in c.included_postal_codes)
    assert not [z for z, n in claims.items() if n > 1]
    assert all(re.fullmatch(r"\d{5}", z) for z in claims)


def test_bowling_green_was_never_quietly_admitted():
    """The corridor exists, and its state is a NAMED decision, never a default.

    PTF-TOLEDO-OH-NEW-MARKET-001 authored it HELD FOR FOUNDER DECISION. Founder
    ruling TOLEDO-R1A then admitted it, and PTF-TOLEDO-OH-PROMOTION-AND-
    APPLICATION-002 discharged the hold. This gate follows that: it requires the
    note to say one of those two things by name, and it still requires the
    Bowling Green, KENTUCKY distinction under either.
    """
    cfg = MC.parse_market(_load(PROPOSED_CONTRACT), source=str(PROPOSED_CONTRACT))
    bg = [c for c in cfg.corridors if c.slug == "bowling-green"]
    assert len(bg) == 1
    raw = [c for c in _load(PROPOSED_CONTRACT)["corridors"]
           if c["slug"] == "bowling-green"][0]
    note = raw.get("_boundary_note", "")
    held = "HELD FOR FOUNDER DECISION" in note
    admitted = "TOLEDO-R1A" in note and "ADMITTED" in note
    assert held or admitted, note[:200]
    assert not (held and admitted), "the note may not claim both states"
    assert "KENTUCKY" in note, "the note must distinguish Bowling Green, OH from Bowling Green, KY"
    if admitted:
        rulings = _load(PACKAGE / "toledo_oh_founder_rulings_001.json")
        live = [r for r in rulings["rulings"] if r["ruling_id"] == "TOLEDO-R1A-BOWLING-GREEN-INCLUDED"]
        assert live, "the note cites TOLEDO-R1A but no such ruling is recorded"
        assert live[0]["disposition"] == "ADMIT_AS_THE_TOLEDO_SOUTHERN_BOWLING_GREEN_CORRIDOR"
        assert raw["included_postal_codes"] == ["43402"], "the corridor may not be widened"


# --------------------------------------------------------------------------- #
# Owned evidence and the acquisition ladder.
# --------------------------------------------------------------------------- #

def test_owned_evidence_was_read_before_anything_was_fetched():
    doc = _load(OWNED_EVIDENCE)
    assert doc["http_requests"] == 0
    assert doc["usd_spent"] == 0.0
    assert doc["counts"]["owned_leads"] > 0


def test_a_locality_token_never_admitted_a_property_in_another_state_or_country():
    """Toledo, SPAIN and Bowling Green, KENTUCKY are in the same brand roster."""
    doc = _load(OWNED_EVIDENCE)
    dropped = {r["property_code"]: r for r in doc["dropped_with_reason"]
               if r.get("property_code")}
    assert "madto" in dropped, "Toledo, Spain must be dropped by name"
    assert "SPAIN" in dropped["madto"]["why"].upper()
    for kentucky in ("bwgcy", "bwgfb", "bwgts", "bnabh"):
        assert kentucky in dropped
        assert "KENTUCKY" in dropped[kentucky]["why"].upper()
    admitted = {r.get("property_code") for r in doc["owned_leads"]}
    assert "madto" not in admitted and "bwgcy" not in admitted


def test_no_cross_market_identity_collision():
    doc = _load(OWNED_EVIDENCE)
    assert doc["counts"]["cross_market_collision_hits"] == 0
    assert len(doc["registered_censuses_scanned"]) >= 10


def test_every_free_lane_spent_nothing():
    for path in (OWNED_EVIDENCE, LEAD_SOURCES, BRAND_CITY_PAGES, ROUTING):
        doc = _load(path)
        assert doc.get("usd_spent", 0.0) == 0.0, path.name
        assert doc.get("paid_provider_calls", 0) == 0, path.name


def test_refusals_were_reprobed_rather_than_inherited():
    """A refusal is a fact about a moment; the prior list was five days old."""
    doc = _load(BRAND_CITY_PAGES)
    probe = doc["refusal_reprobe"]
    assert len(probe) >= 7
    for fam, block in probe.items():
        assert block["attempts"], fam
        for attempt in block["attempts"]:
            assert attempt["at"].startswith("2026-"), fam


def test_hilton_came_from_its_own_city_page_not_a_sitemap_walk():
    doc = _load(BRAND_CITY_PAGES)
    assert doc["hilton"]["cities_served"] >= 10
    assert doc["counts"]["hilton_tol_codes"] >= 10
    for code, row in doc["hilton"]["codes"].items():
        assert row["route"].startswith("https://www.hilton.com/en/hotels/%s-" % code)


# --------------------------------------------------------------------------- #
# The competitor lane is a lead lane.
# --------------------------------------------------------------------------- #

def test_the_competitor_category_filter_was_measured_not_assumed():
    doc = _load(LEAD_SOURCES)
    probe = doc["category_filter_probe"]
    assert probe["verdict"] in (
        "INERT_FILTER_TREAT_ALL_ROWS_AS_MIXED_LODGING",
        "LIVE_FILTER_HOTELS_COHORT_IS_A_REAL_SUBSET")
    assert set(probe["probes"]) == {"ALL_LODGING", "HOTELS_ONLY", "RENTALS_ONLY"}


def test_page_one_was_not_mistaken_for_the_cohort():
    doc = _load(LEAD_SOURCES)
    per_city = doc["counts"]["pages_and_rows_per_city"]
    assert any(b["pages_walked"] > 1 for b in per_city.values())


def test_no_competitor_row_entered_the_census_on_competitor_evidence_alone():
    gaps = _load(GAP_MATRIX)
    census = _load(PROPOSED_CENSUS)
    keys = {h["identity_key"] for h in census["hotels"]}
    for row in gaps["true_missing_identities_competitor_only"]:
        assert normalize_name(row["canonical_name"]) not in keys
    for h in census["hotels"]:
        assert h["lanes"] != ["COMPETITOR_LEAD"], h["canonical_name"]


# --------------------------------------------------------------------------- #
# The census.
# --------------------------------------------------------------------------- #

def test_the_proposed_census_is_marked_proposed():
    doc = _load(PROPOSED_CENSUS)
    assert doc["status"] == "PROPOSED_NOT_REGISTERED"
    assert doc["market_id"] == MARKET
    assert doc["count"] == len(doc["hotels"])


def test_every_admitted_identity_has_hard_evidence_and_a_corridor():
    doc = _load(PROPOSED_CENSUS)
    cfg = MC.parse_market(_load(PROPOSED_CONTRACT), source=str(PROPOSED_CONTRACT))
    corridors = {c.corridor_id for c in cfg.corridors}
    zips = {z: c.corridor_id for c in cfg.corridors for z in c.included_postal_codes}
    assert doc["hotels"], "the census must not be empty"
    for h in doc["hotels"]:
        assert h["classification"] == "TRUE_HOTEL_IDENTITY", h["canonical_name"]
        assert h["street"] or h["phone"], h["canonical_name"]
        assert h["postal_code"] in zips, h["canonical_name"]
        assert h["corridor"] in corridors, h["canonical_name"]
        assert h["corridor"] == zips[h["postal_code"]], h["canonical_name"]
        assert h["assignment_basis"] == "postal_code"
        assert h["evidence"], h["canonical_name"]


def test_no_identity_record_carries_a_pet_policy():
    """Identity evidence never establishes a policy. Fail loudly if it leaks."""
    from scripts.pettripfinder.identity_evidence import POLICY_FIELD_NAMES
    doc = _load(PROPOSED_CENSUS)
    for h in doc["hotels"] + doc["non_admitted"]:
        assert h["policy_state"] == "POLICY_NOT_VERIFIED", h["canonical_name"]
        leaked = POLICY_FIELD_NAMES & set(h)
        assert not leaked, (h["canonical_name"], sorted(leaked))
        for obs in h["evidence"]:
            assert not (POLICY_FIELD_NAMES & set(obs)), h["canonical_name"]


def test_identity_keys_are_unique_and_normalised():
    doc = _load(PROPOSED_CENSUS)
    keys = [h["identity_key"] for h in doc["hotels"]]
    assert len(keys) == len(set(keys))
    for h in doc["hotels"]:
        assert h["identity_key"] == normalize_name(h["canonical_name"])
        assert h["identity_key"], h["canonical_name"]


def test_a_rebrand_is_held_rather_than_published_under_a_guessed_name():
    doc = _load(PROPOSED_CENSUS)
    rebrands = [r for r in doc["non_admitted"]
                if r["classification"] == "SAME_IDENTITY_REBRAND_SUCCESSOR"]
    assert rebrands, "the Radisson/Delta pair at 3100 Glendale must be held"
    for r in rebrands:
        assert r["street"], r["canonical_name"]
        assert "founder ruling" in r["classification_reason"]


def test_a_name_only_row_never_became_an_identity():
    doc = _load(PROPOSED_CENSUS)
    for r in doc["non_admitted"]:
        if r["classification"] == "NAME_ONLY_UNRESOLVED":
            assert not (r["street"] and r["postal_code"]), r["canonical_name"]


def test_michigan_rows_were_found_deliberately_and_never_admitted():
    doc = _load(LEAD_SOURCES)
    assert doc["counts"]["outside_market_state_mi"] > 0
    census = _load(PROPOSED_CENSUS)
    for h in census["hotels"]:
        assert h["state"] in ("OH", ""), h["canonical_name"]


def test_a_name_binding_never_crossed_a_town_or_an_area():
    """The bindings this order made must not contradict a stated place."""
    recon = _load(RECONCILIATION)
    census = _load(PROPOSED_CENSUS)
    by_key = {h["identity_key"]: h for h in census["hotels"]}
    for b in recon["name_attachment"]["bindings"]:
        target = by_key.get(normalize_name(b["bound_to"]))
        if target is None:
            continue
        offered = normalize_name(b["observation_name"])
        for town in ("monroe", "milan", "findlay", "fostoria", "wauseon",
                     "port clinton", "dundee"):
            if town in offered:
                assert town in normalize_name(target["city"] or ""), (
                    "%r bound to a building in %r" % (b["observation_name"], target["city"]))


# --------------------------------------------------------------------------- #
# Routing.
# --------------------------------------------------------------------------- #

def test_every_route_is_bound_to_the_identity_it_serves():
    doc = _load(ROUTING)
    census_keys = {h["identity_key"] for h in _load(PROPOSED_CENSUS)["hotels"]}
    for r in doc["routes"]:
        assert r["identity_key"] in census_keys, r["canonical_name"]
        if r.get("url"):
            assert r["url"].startswith("https://"), r["canonical_name"]
            assert " " not in r["url"], r["canonical_name"]


def test_a_route_on_another_chains_host_was_rejected():
    """Destination Toledo links redroofinns.com from its Baymont partner page."""
    doc = _load(ROUTING)
    mismatched = [r for r in doc["routes"] if r["routing_state"] == "ROUTE_BRAND_MISMATCH"]
    assert mismatched, "the Baymont -> redroofinns.com route must be rejected"
    for r in mismatched:
        assert not r["url"]
        rej = r["rejected_route"]
        assert rej["name_family"] != rej["host_family"]


def test_identity_fill_routes_are_not_in_the_census():
    doc = _load(ROUTING)
    census_keys = {h["identity_key"] for h in _load(PROPOSED_CENSUS)["hotels"]}
    for r in doc.get("identity_fill_routes", []):
        assert r["identity_key"] not in census_keys, r["canonical_name"]
        assert r["routing_state"] == "ROUTED_FOR_IDENTITY_FILL"


# --------------------------------------------------------------------------- #
# The attended lane, and the audit that governs every lane.
# --------------------------------------------------------------------------- #

def test_the_attended_pass_spent_nothing_and_answered_no_bot_check():
    doc = _load(ATTENDED)
    assert doc["usd_spent"] == 0.0
    assert doc["paid_provider_calls"] == 0
    assert doc["firecrawl_credits"] == 0
    assert "No credential was entered" in doc["no_bot_check_was_answered"]


def test_every_attended_read_confirmed_its_identity_on_the_pages_own_address():
    doc = _load(ATTENDED)
    assert doc["counts"]["pages_read"] == doc["counts"]["identity_confirmed"]
    for r in doc["rows"]:
        sig = r["identity_signals"]
        assert sig.get("address_on_page"), r["property_code"]
        assert sig.get("postal_code"), r["property_code"]
        assert r["exact_quote"], r["property_code"]


def test_a_property_code_selected_but_the_page_admitted():
    """Marriott's TOL prefix reaches Findlay, Port Clinton and Wauseon."""
    doc = _load(ATTENDED)
    outside = {r["property_code"] for r in doc["rows"] if not r["in_market"]}
    assert {"tolfi", "tolfc", "toltf", "tolfx", "tolllru"} <= outside
    census_keys = {h["identity_key"] for h in _load(PROPOSED_CENSUS)["hotels"]}
    for r in doc["rows"]:
        if r["in_market"]:
            continue
        assert normalize_name(r["identity_signals"].get("name_on_page") or "") not in census_keys


def test_a_service_animals_only_row_is_a_refusal_not_an_acceptance():
    doc = _load(ATTENDED)
    rows = [r for r in doc["rows"] if r.get("service_animals_only")]
    assert rows, "Fairfield Bowling Green states 'Service Animals Only'"
    for r in rows:
        assert r["extraction"]["pets_allowed"] is False, r["property_code"]


def test_the_hilton_read_came_from_the_policy_node_not_the_review_prose():
    doc = _load(ATTENDED)
    how = doc["how_each_brand_was_read"]["HILTON"]
    assert "review" in how and "petsInfo" in how
    for r in doc["rows"]:
        if r["brand"] != "HILTON":
            continue
        assert r["surface"] == "__NEXT_DATA__ petsInfo node"
        assert not re.search(r"we (asked|were told|searched)", r["exact_quote"], re.I)


def test_every_clean_row_carries_a_quote_a_source_and_an_identity():
    doc = _load(CLEAN_AUTHORITY)
    rows = doc["clean_pet_friendly"] + doc["clean_verified_no_pets"]
    assert rows
    for a in rows:
        assert a["source_url"], a["canonical_name"]
        assert a["identity_signals"], a["canonical_name"]
        assert a["evidence"], a["canonical_name"]
        assert any((e.get("quote") or "").strip() for e in a["evidence"]), a["canonical_name"]
        assert a["extraction"].get("pets_allowed") is not None, a["canonical_name"]
        assert not a["audit_problems"], a["canonical_name"]


def test_no_identity_appears_twice_in_the_clean_inventory():
    """Two Hilton codes share 101 N Summit Street; one identity, two hotels."""
    doc = _load(CLEAN_AUTHORITY)
    keys = [a["identity_key"] for a in
            doc["clean_pet_friendly"] + doc["clean_verified_no_pets"]]
    assert len(keys) == len(set(keys))


def test_a_read_on_an_unresolved_identity_is_held():
    """6425 Kit Lane is both a Best Western and a Baymont in this run's evidence."""
    audit = _load(EVIDENCE_AUDIT)
    classes = {p["class"] for a in audit["reads"] for p in a["audit_problems"]}
    assert "IDENTITY_UNRESOLVED_BY_THE_MERGE" in classes
    assert "TWO_PROPERTIES_READ_ONTO_ONE_IDENTITY" in classes
    clean_keys = {a["identity_key"] for a in
                  _load(CLEAN_AUTHORITY)["clean_pet_friendly"]
                  + _load(CLEAN_AUTHORITY)["clean_verified_no_pets"]}
    for a in audit["reads"]:
        if a["audit_verdict"] == "HELD":
            assert a["identity_key"] not in clean_keys or not a["identity_key"]


def test_promotion_readiness_is_stated_with_its_reasons():
    doc = _load(REPORTS / "toledo_oh_shadow_market_001.json")
    assert doc["promotion_ready"] in ("YES", "NO")
    assert doc["projected"]["census"] > 0
    assert doc["projected"]["resolved"] + doc["projected"]["unresolved"] ==         doc["projected"]["census"]
    assert doc["projected"]["profiles"] == doc["projected"]["pet_friendly"]
    if doc["promotion_ready"] == "YES":
        assert doc["blockers"] == []
        assert doc["required_before_promotion"], "a YES must still name what the founder owes"


def test_paid_readiness_quotes_no_cost_it_did_not_measure():
    doc = _load(REPORTS / "toledo_oh_paid_readiness_001.json")
    assert doc["shared_ledgers"]["written"] == "NONE"
    assert doc["shared_ledgers"]["toledo_rows_in_either"] == 0
    assert doc["verdict"]["required_for_promotion"] == []
    for lane in ("bright_data", "places_paid_identity_discovery"):
        assert "UNQUOTED" in doc[lane]["expected_cost"], lane
        assert doc[lane]["required_for_promotion"] is False, lane


def test_the_founder_packet_is_grouped_and_every_item_is_answerable():
    doc = _load(REPORTS / "toledo_oh_founder_packet_001.json")
    groups = {i["group"] for i in doc["items"]}
    assert {"A_IDENTITY", "B_GEOGRAPHY", "C_CATEGORY", "F_CROSS_MARKET"} <= groups
    for i in doc["items"]:
        for field in ("identity", "evidence", "proposed_action", "recommendation",
                      "census_effect", "authority_effect", "routing_effect",
                      "reversibility", "blocks_promotion"):
            assert i.get(field), (i["group"], field)
        assert i["blocks_promotion"] in ("YES", "NO")


def test_parallel_safety_found_no_violation():
    doc = _load(REPORTS / "toledo_oh_parallel_safety_001.json")
    assert doc["counts"]["violations"] == 0
    m = doc["mechanical_assertions"]
    for k in ("fort_wayne_files_changed", "lexington_files_changed",
              "other_registered_market_files_changed", "shared_globals_changed",
              "market_registry_changed", "registered_census_changed",
              "market_authority_shards_changed", "shared_current_state_pins_changed",
              "deployment_files_changed", "shared_ledgers_written",
              "shared_factory_code_changed"):
        assert m[k] == 0, k
    assert m["production_assembly"] == "NOT RUN"
    assert m["deployed"] == "NO"


def test_the_regression_classification_reports_no_true_new_failure():
    doc = _load(REPORTS / "toledo_oh_regression_classification_001.json")
    assert doc["byte_identity_proof"]["proof_holds"] is True
    assert doc["counts"]["TRUE_NEW_FAILURE"] == 0


def test_no_clean_row_rests_on_a_fee_a_weight_or_a_count_alone():
    doc = _load(CLEAN_AUTHORITY)
    for a in doc["clean_pet_friendly"]:
        supporting = [e for e in a["evidence"] if "pets_allowed" in (e.get("field_refs") or [])]
        assert supporting, a["canonical_name"]


def test_the_audit_ran_over_every_lane_that_produced_a_read():
    audit = _load(EVIDENCE_AUDIT)
    lanes = set(audit["counts"]["by_lane"])
    assert {"DIRECT_STATIC", "FIRECRAWL", "ATTENDED_BROWSER"} <= lanes
    assert audit["counts"]["reads_audited"] == (
        audit["counts"]["clean_pet_friendly"] + audit["counts"]["clean_verified_no_pets"]
        + audit["counts"]["held"])


@pytest.mark.parametrize("report", [
    "toledo_oh_owned_evidence_001.json",
    "toledo_oh_lead_sources_001.json",
    "toledo_oh_brand_city_pages_001.json",
    "toledo_oh_census_reconciliation_001.json",
    "toledo_oh_competitor_gap_matrix_001.json",
    "toledo_oh_routing_001.json",
    "toledo_oh_attended_capture_001.json",
    "toledo_oh_ladder_plan_001.json",
    "toledo_oh_evidence_audit_001.json",
    "toledo_oh_clean_authority_001.json",
    "toledo_oh_founder_packet_001.json",
    "toledo_oh_paid_readiness_001.json",
    "toledo_oh_shadow_market_001.json",
    "toledo_oh_parallel_safety_001.json",
    "toledo_oh_regression_classification_001.json",
])
def test_every_report_names_this_work_order_and_this_market(report):
    doc = _load(REPORTS / report)
    assert doc["work_order"] == "PTF-TOLEDO-OH-NEW-MARKET-001"
    assert doc["market_id"] == MARKET
