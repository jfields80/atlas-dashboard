"""PTF-NASHVILLE-TN-NEW-MARKET-001 -- the Nashville shadow market's own gates.

Nashville is NOT a registered market. This order builds a complete,
evidence-bound shadow market and stops at the serialized promotion boundary, so
every gate here asserts two kinds of thing:

1. **The shadow market is internally sound** -- its contract parses, its postal
   partition is a partition, its census rows carry the evidence that admitted
   them, its routes carry the identity they claim to serve, and no policy fact
   has leaked into an identity record.
2. **The boundary held** -- Nashville is absent from every registry, pin and
   authority that would make it a live market, and this order changed none of
   them.

The second kind matters as much as the first. PTF-047 established that
registering market N+1 invalidates the current production deployment record; a
new-market order that quietly created ``markets/nashville-tn.json`` would look
successful and would have broken the eleven live markets.

Nashville is also the first market this factory has built with a FRINGE THAT
WAS HELD RATHER THAN GUESSED. Five corridors -- Franklin/Cool Springs, Mount
Juliet, Hendersonville, Smyrna/La Vergne and Lebanon -- exist in the contract
claiming NO postal code, so their hotels are discovered, identified and then
classified OUTSIDE_MARKET. Several gates below exist to prove that the hold is
mechanical rather than rhetorical: a held ZIP may never also be an admitted one,
and no held row may reach the clean inventory.
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

#: The order that DID discharge the boundary gates below. It ran, under the name
#: PTF-NASHVILLE-TN-PROMOTION-AND-NEW-LANE-LAUNCH-PREP-002 rather than the one
#: the shadow order predicted, and it registered Nashville: the market contract
#: and the census MOVED out of markets/proposed/ and identity_census_proposed/,
#: an authority shard and a release contract now exist, and the participation
#: record carries a nashville-tn row.
#:
#: The five boundary gates are therefore RETIRED below rather than deleted. Each
#: is kept as a record of what the shadow order promised and a pointer to the
#: order that discharged it, because a gate that vanishes leaves no evidence it
#: was ever honoured. Every other gate in this file describes how the market was
#: BUILT, is still true of the moved artifact, and still runs.
PROMOTION = "PTF-NASHVILLE-TN-PROMOTION-AND-NEW-LANE-LAUNCH-PREP-002"

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE = REPO_ROOT / "launch_packages" / "pettripfinder"
REPORTS = PACKAGE / "markets" / "reports"
MARKET = "nashville-tn"

def _either(registered: Path, proposed: Path) -> Path:
    """The registered artifact once this market is promoted, else the proposed one.

    PTF-NASHVILLE-TN-PROMOTION-AND-APPLICATION-002 MOVED both files. Every gate
    below that describes how the market was BUILT is still true of the moved
    artifact, so it follows the file rather than being retired with the boundary.
    """
    return registered if registered.is_file() else proposed


PROPOSED_CONTRACT = _either(PACKAGE / "markets" / "nashville-tn.json",
                            PACKAGE / "markets" / "proposed" / "nashville-tn.json")
PROPOSED_CENSUS = _either(PACKAGE / "identity_census" / "nashville-tn.json",
                          PACKAGE / "identity_census_proposed" / "nashville-tn.json")
REGISTERED = (PACKAGE / "markets" / "nashville-tn.json").is_file()
OWNED_EVIDENCE = REPORTS / "nashville_tn_owned_evidence_001.json"
LEAD_SOURCES = REPORTS / "nashville_tn_lead_sources_001.json"
BRAND_CITY_PAGES = REPORTS / "nashville_tn_brand_city_pages_001.json"
BRAND_SITEMAPS = REPORTS / "nashville_tn_brand_sitemaps_001.json"
RECONCILIATION = REPORTS / "nashville_tn_census_reconciliation_001.json"
GAP_MATRIX = REPORTS / "nashville_tn_competitor_gap_matrix_001.json"
ROUTING = REPORTS / "nashville_tn_routing_001.json"
ATTENDED = REPORTS / "nashville_tn_attended_capture_001.json"
CLEAN_AUTHORITY = REPORTS / "nashville_tn_clean_authority_001.json"
EVIDENCE_AUDIT = REPORTS / "nashville_tn_evidence_audit_001.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


# --------------------------------------------------------------------------- #
# The serialized boundary. These run first because nothing else matters if the
# order crossed it.
# --------------------------------------------------------------------------- #

#: The five gates below were LIVE assertions until PROMOTION ran. They are
#: retired by name, with what each one guarded and what discharged it, and one
#: gate replaces the whole group: the promotion must have moved the artifacts
#: rather than copied them, because a market that exists in BOTH the proposed
#: and the registered location is two markets as far as every glob is concerned.
RETIRED_BOUNDARY_GATES = {
    "test_nashville_is_not_a_registered_market":
        "markets/nashville-tn.json now exists, written by %s." % PROMOTION,
    "test_nashville_has_no_authority_shard_and_no_registered_census":
        "the authority shard, the registered census and the policy package now "
        "exist, written by %s." % PROMOTION,
    "test_nashville_is_absent_from_every_current_state_pin":
        "pins/market_state.json carries a nashville-tn pin (180 / 8 / 5), added "
        "by %s. The deployment pins do NOT carry it and must not: Nashville is "
        "registered, not live." % PROMOTION,
    "test_nashville_has_no_release_contract_and_no_launch_participation":
        "deploy/netlify/release_contracts/nashville-tn.json now exists and the "
        "participation record carries a nashville-tn row reading "
        "SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH, written by %s."
        % PROMOTION,
    "test_production_truth_is_unchanged_by_this_order":
        "this pinned deploy 6a9e0476 at 11 / 803 / 966, which "
        "PTF-LEXINGTON-KY-FRESH-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006 "
        "superseded with 6aa17212 at 12 / 823 / 991. The statement it was "
        "making -- a new-market order must not quietly register market N+1 -- "
        "is now made by the deployment pins themselves and by "
        "test_registering_nashville_moved_no_live_market below.",
}


def test_the_boundary_gates_this_order_promised_were_discharged_not_deleted():
    """Every retired gate names the order that discharged it and why.

    A boundary gate that simply disappears leaves no evidence it was ever
    honoured; retiring it by name is how PTF-LEXINGTON-KY-FRESH-FOUNDER-
    AUTHORIZATION-AND-LIVE-LAUNCH-006 closed the twelve its launch falsified,
    and this file follows it.
    """
    assert len(RETIRED_BOUNDARY_GATES) == 5
    for name, why in RETIRED_BOUNDARY_GATES.items():
        assert name.startswith("test_")
        assert PROMOTION in why or "SUPERSED" in why.upper() or "superseded" in why


def test_the_promotion_registered_the_market_exactly_once():
    """The registry is markets/*.json, and Nashville is in it once.

    The proposed contract and census are RETAINED as the record of the shadow
    build -- they are not the registry, ``load_markets()`` does not read
    ``markets/proposed/``, and deleting them would destroy the only committed
    statement of what the market looked like before the modern gates ran. What
    must be true is that the REGISTRY carries exactly one Nashville.
    """
    assert (PACKAGE / "markets" / ("%s.json" % MARKET)).is_file()
    assert (PACKAGE / "identity_census" / ("%s.json" % MARKET)).is_file()
    ids = [m.market_id for m in MC.load_markets()]
    assert ids.count(MARKET) == 1
    registered = _load(PACKAGE / "identity_census" / ("%s.json" % MARKET))
    assert registered["status"] == "REGISTERED"
    assert registered["count"] == len(registered["hotels"])


def test_registering_nashville_moved_no_live_market():
    """The half of the retired production-truth gate that is still true.

    Registering a market must not touch a market that is already live. The
    deployment pins are the record of what production serves, and Nashville
    must be absent from BOTH blocks: registered is not live.
    """
    deployment = _load(REPO_ROOT / "tests" / "pettripfinder" / "pins"
                       / "deployment_state.json")
    for block in ("live", "source"):
        assert MARKET not in deployment[block]["participating_markets"], block
        assert MARKET not in deployment[block]["profile_counts"], block
    live = deployment["live"]
    assert len(live["participating_markets"]) == len(live["profile_counts"])
    assert live["total_profiles"] == sum(live["profile_counts"].values())


# --------------------------------------------------------------------------- #
# Geography.
# --------------------------------------------------------------------------- #

def test_discovery_config_loads_and_is_tennessee_only():
    cfg = load_market_config(MARKET)
    assert cfg.market_id == MARKET
    assert cfg.state == "TN"
    assert len(cfg.cells) >= 20
    for cell in cfg.cells:
        assert cfg.bounds.contains(cell.center_lat, cell.center_lng), cell.cell_id


def test_the_discovery_box_is_larger_than_the_market_on_purpose():
    """Every held fringe town must be INSIDE the box, or the hold is uninformed.

    A corridor held for a founder ruling whose inventory was never fetched is not
    a hold, it is an omission dressed as one. The box therefore reaches Franklin,
    Mount Juliet, Hendersonville, Smyrna and Lebanon even though the corridor
    registry claims none of their postal codes.
    """
    cfg = load_market_config(MARKET)
    fringe = {"nashville-tn__cool-springs-franklin", "nashville-tn__mount-juliet",
              "nashville-tn__hendersonville", "nashville-tn__smyrna-la-vergne",
              "nashville-tn__lebanon-i40-east"}
    present = {c.cell_id for c in cfg.cells}
    assert fringe <= present, sorted(fringe - present)
    for cell in cfg.cells:
        if cell.cell_id in fringe:
            assert cfg.bounds.contains(cell.center_lat, cell.center_lng), cell.cell_id


def test_discovery_box_does_not_overlap_a_committed_market_box():
    """Nashville's box must not sit inside another market's committed box."""
    nash = load_market_config(MARKET).bounds
    for other in ("louisville-ky", "indianapolis-in", "cincinnati-oh", "st-louis-mo",
                  "columbus-oh"):
        b = load_market_config(other).bounds
        overlaps = (nash.min_lat < b.max_lat and nash.max_lat > b.min_lat
                    and nash.min_lng < b.max_lng and nash.max_lng > b.min_lng)
        assert not overlaps, "nashville-tn discovery box overlaps %s" % other


def test_proposed_contract_parses_against_the_real_contract_module():
    cfg = MC.parse_market(_load(PROPOSED_CONTRACT), source=str(PROPOSED_CONTRACT))
    assert cfg.market_id == MARKET
    assert cfg.states == ("TN",)
    assert cfg.route_mode == MC.ROUTE_MODE_MARKET_PREFIXED
    assert cfg.census_membership_basis == MC.MEMBERSHIP_CORRIDOR_REGISTRY
    assert len(cfg.corridors) >= 15


def test_the_postal_partition_is_a_partition():
    """Every ZIP is claimed by exactly one corridor, or the market places a hotel twice."""
    cfg = MC.parse_market(_load(PROPOSED_CONTRACT), source=str(PROPOSED_CONTRACT))
    claims = Counter(z for c in cfg.corridors for z in c.included_postal_codes)
    assert not [z for z, n in claims.items() if n > 1]
    assert all(re.fullmatch(r"\d{5}", z) for z in claims)


def test_a_held_zip_is_never_also_an_admitted_zip():
    """The hold is mechanical, not rhetorical.

    A corridor held for a founder ruling carries its candidate postal codes in
    ``_held_postal_codes`` and an EMPTY ``included_postal_codes``. If a held ZIP
    ever appeared in an admitted corridor as well, the market would claim the
    fringe while claiming to hold it, and every hotel in it would be silently
    published.
    """
    raw = _load(PROPOSED_CONTRACT)
    admitted = {z for c in raw["corridors"] for z in c.get("included_postal_codes") or []}
    held = {z for c in raw["corridors"] for z in c.get("_held_postal_codes") or []}
    assert held, "this market's whole fringe doctrine rests on there being holds"
    assert not (held & admitted), sorted(held & admitted)
    for c in raw["corridors"]:
        if c.get("_held_postal_codes"):
            assert c["included_postal_codes"] == [], c["slug"]
            assert c.get("_hold") == "FOUNDER_GEOGRAPHY_HOLD", c["slug"]


def test_the_five_named_fringe_areas_are_all_held_by_name():
    """The order named five areas to evaluate; each must be a NAMED decision."""
    raw = _load(PROPOSED_CONTRACT)
    held = {c["slug"] for c in raw["corridors"] if c.get("_held_postal_codes")}
    assert held == {"cool-springs-franklin", "mount-juliet-i40-east", "hendersonville",
                    "smyrna-la-vergne", "lebanon-i40-east"}, sorted(held)


def test_brentwood_and_goodlettsville_were_admitted_with_their_evidence():
    """Two fringe areas ARE admitted, and the contract says why in its own note."""
    raw = _load(PROPOSED_CONTRACT)
    note = raw["_boundary_note"]
    admitted = {z for c in raw["corridors"] for z in c.get("included_postal_codes") or []}
    assert "37027" in admitted and "37072" in admitted
    assert "Brentwood" in note and "Goodlettsville" in note
    assert "straddles" in note.lower(), "37072's county-line straddle is the evidence"


def test_the_opryland_corridor_claims_no_zip_and_is_not_a_hold():
    """37214 carries two traveler markets; the split is by name, not by ZIP.

    Opryland must claim no postal code (37214 belongs to airport-donelson for
    MEMBERSHIP) and must NOT be a founder hold: it is an admitted corridor that
    classifies by ``explicit_hotel_ids``, which outranks the ZIP tier in
    ``markets.assignment.assign_hotels``.
    """
    raw = _load(PROPOSED_CONTRACT)
    opry = [c for c in raw["corridors"] if c["slug"] == "opryland-music-valley"]
    assert len(opry) == 1
    assert opry[0]["included_postal_codes"] == []
    assert "_hold" not in opry[0]
    airport = [c for c in raw["corridors"] if c["slug"] == "airport-donelson"][0]
    assert "37214" in airport["included_postal_codes"]


# --------------------------------------------------------------------------- #
# Owned evidence and the acquisition ladder.
# --------------------------------------------------------------------------- #

def test_owned_evidence_was_read_before_anything_was_fetched():
    """Rung 0. Seventy Nashville leads for zero requests and zero dollars."""
    doc = _load(OWNED_EVIDENCE)
    assert doc["free_http_requests"] == 0
    assert doc["paid_provider_calls"] == 0
    assert doc["usd_spent"] == 0.0
    assert doc["owned_leads_total"] > 0


def test_an_airport_code_never_admitted_a_property_in_another_market():
    """BNA is an AIRPORT code and it reaches most of Middle Tennessee.

    Clarksville, Cookeville, Columbia, Murfreesboro, Manchester, Tullahoma and
    two KENTUCKY towns all carry BNA-prefixed Marriott property codes. If the
    prefix were allowed to admit a row, every one of them would enter this
    market's census.
    """
    doc = _load(OWNED_EVIDENCE)
    dropped = {r["property_code"]: r for r in doc["dropped_rows"]
               if r.get("property_code")}
    for code, town in (("bnabh", "KENTUCKY"), ("bnakv", "KENTUCKY"),
                       ("bnack", "COOKEVILLE"), ("bnacr", "CLARKSVILLE"),
                       ("bnacb", "MURFREESBORO"), ("bnafc", "COLUMBIA")):
        assert code in dropped, code
        assert town in dropped[code]["why"].upper(), code
        assert dropped[code]["verdict"] == "DROPPED_CODE_PREFIX_REACHES_ANOTHER_MARKET"
    admitted = {r.get("property_code") for r in doc["owned_leads"]}
    assert not ({"bnabh", "bnack", "bnacb", "bnakv"} & admitted)


def test_a_locality_token_never_admitted_a_property_in_another_state_or_country():
    """Brentwood is in Los Angeles and in INDIA; Mount Juliet is in JAMAICA."""
    doc = _load(OWNED_EVIDENCE)
    dropped = {r["property_code"]: r for r in doc["dropped_rows"]
               if r.get("property_code")}
    for code, where in (("laxpb", "LOS ANGELES"), ("dedrb", "INDIA"),
                        ("oakpc", "CALIFORNIA"), ("avlhv", "NORTH CAROLINA"),
                        ("kkyak", "JAMAICA")):
        assert code in dropped, code
        assert where in dropped[code]["why"].upper(), code
    admitted = {r.get("property_code") for r in doc["owned_leads"]}
    assert not ({"laxpb", "dedrb", "oakpc", "avlhv", "kkyak"} & admitted)


def test_a_brand_url_that_states_another_state_was_dropped():
    """Franklin, Lebanon, Madison and Bellevue are Ohio towns too.

    The first pass of this scan produced three non-Marriott "Nashville leads",
    and all three were Franklin, OHIO -- a Ramada, a Super 8 and a Drury whose
    own URLs say ``-ohio/``. A brand's URL stating a state is a first-party
    statement of geography and it settles a locality token outright.
    """
    doc = _load(OWNED_EVIDENCE)
    by_verdict = doc["dropped_by_reason"]
    assert by_verdict.get("DROPPED_URL_STATES_ANOTHER_STATE", 0) > 0
    for r in doc["dropped_rows"]:
        if r["verdict"] == "DROPPED_URL_STATES_ANOTHER_STATE":
            assert r["url_states_state"] not in ("tennessee", "tn"), r["url"]


def test_no_cross_market_identity_collision():
    doc = _load(OWNED_EVIDENCE)
    scan = doc["cross_market_collision_scan"]
    assert scan["collisions_found"] == 0
    assert len(scan["censuses_scanned"]) >= 10


def test_every_free_lane_spent_nothing():
    for path in (OWNED_EVIDENCE, LEAD_SOURCES, BRAND_CITY_PAGES, BRAND_SITEMAPS, ROUTING):
        doc = _load(path)
        assert doc.get("usd_spent", 0.0) == 0.0, path.name
        assert doc.get("paid_provider_calls", 0) == 0, path.name


def test_refusals_were_reprobed_rather_than_inherited():
    """A refusal is a fact about a moment; the inherited list was five days old.

    The committed Ohio harvests recorded eight families as refusing a plain
    client. This order re-probed fifteen and most of them served, which is the
    whole reason the sitemap rung exists for this market at all.
    """
    doc = _load(BRAND_CITY_PAGES)
    probe = doc["refusal_reprobe"]
    assert len(probe) >= 12
    for fam, block in probe.items():
        assert block["attempts"], fam
        for attempt in block["attempts"]:
            assert attempt["at"].startswith("2026-"), fam
    assert doc["counts"]["families_served_on_some_host"] > 0


def test_serving_robots_txt_is_not_serving_a_sitemap():
    """Measured, not assumed, and it is what sends a family down the ladder.

    Several families answered robots.txt WITH a sitemap URL and then refused
    that very sitemap to the same client seconds later. A market that read the
    robots.txt answer as availability would have called them silent.
    """
    city = _load(BRAND_CITY_PAGES)
    maps = _load(BRAND_SITEMAPS)
    served_robots = {f for f, v in city["refusal_reprobe"].items() if v["any_host_served"]}
    refused_sitemap = {f for f, v in maps["families"].items()
                       if v["verdict"] == "SITEMAP_REFUSED_TO_THIS_CLIENT"}
    assert refused_sitemap, "the finding this gate exists for must be present"
    assert refused_sitemap <= served_robots, sorted(refused_sitemap - served_robots)
    for fam in refused_sitemap:
        why = maps["families"][fam]["why"]
        assert "NOT evidence" in why, fam


def test_every_brand_sitemap_walk_was_bounded():
    """Toledo lost 25 minutes to an unbounded walk that produced nothing."""
    maps = _load(BRAND_SITEMAPS)
    for fam, v in maps["families"].items():
        assert v["request_cap"] > 0, fam
        assert v["requests_spent"] <= v["request_cap"], fam
        assert v["cap_reached"] is False, "%s stopped with work outstanding" % fam


def test_hilton_came_from_its_own_city_pages_not_a_sitemap_walk():
    doc = _load(BRAND_CITY_PAGES)
    maps = _load(BRAND_SITEMAPS)
    assert doc["hilton"]["cities_served"] >= 10
    assert doc["counts"]["hilton_bna_codes"] >= 10
    for code, row in doc["hilton"]["codes"].items():
        assert row["route"].startswith("https://www.hilton.com/en/hotels/%s-" % code)
    # The same answer was NOT available from the sitemap, which is the point.
    assert maps["families"]["HILTON"]["verdict"] != \
        "ROUTES_READ_FROM_THE_BRAND_OWN_SITEMAP"


# --------------------------------------------------------------------------- #
# The competitor lane is a lead lane.
# --------------------------------------------------------------------------- #

def test_the_competitor_category_filter_was_measured_not_assumed():
    """And the measurement changed the lane.

    The unfiltered path returned 399 rows and the filtered one 245, with 250
    rows in the first that are not in the second -- "Hart Suite 8 by Avantstay",
    "2BR Urban Bungalow". Those are short-term rentals. The FILTERED path is
    what supplies leads; the unfiltered cohort is kept only as the measurement.
    """
    doc = _load(LEAD_SOURCES)
    bf = doc["bringfido"]
    probe = bf["category_filter_test"]["nashville_tn_us"]
    assert probe["verdict"] in ("PATH_FILTER_IS_LIVE",
                                "PATH_FILTER_IS_INERT_SAME_COHORT_BOTH_WAYS")
    if probe["verdict"] == "PATH_FILTER_IS_LIVE":
        assert bf["lead_cohort_is_the_filtered_hotel_path"] is True
        assert bf["short_term_rental_rows_measured_and_excluded"] > 0
        assert bf["distinct_leads"] <= probe["unfiltered_rows"] * 2


def test_the_headline_count_is_never_read_as_the_cohort():
    """Antioch's page states 5 results and serves 399. They are two facts."""
    doc = _load(LEAD_SOURCES)
    per_city = doc["bringfido"]["per_city"]
    assert per_city
    for city, b in per_city.items():
        assert "headline_result_count_the_page_states" in b, city
        assert "rows_actually_parsed" in b, city
        assert "headline_equals_parsed" in b, city


def test_page_one_was_not_mistaken_for_the_cohort():
    doc = _load(LEAD_SOURCES)
    per_city = doc["bringfido"]["per_city"]
    assert any(b["pages_fetched"] > 1 for b in per_city.values())


def test_a_city_page_that_serves_a_radius_was_not_walked_twenty_times():
    """A BringFido city slug picks a CENTRE; the list is a radius."""
    doc = _load(LEAD_SOURCES)
    verdicts = {b["cohort_verdict"] for b in doc["bringfido"]["per_city"].values()}
    assert "WALKED_IN_FULL" in verdicts
    for city, b in doc["bringfido"]["per_city"].items():
        if b["cohort_verdict"] == "COHORT_IS_A_SUBSET_OF_THE_NASHVILLE_WALK":
            assert b["pages_fetched"] == 1, city


def test_the_destination_refusal_is_recorded_as_a_refusal_not_a_silence():
    """Toledo's CVB roster was that market's best rung. Nashville's refused."""
    doc = _load(LEAD_SOURCES)
    orgs = doc["official_destination_sources"]
    assert orgs, "the destination organisations must have been probed"
    for org, block in orgs.items():
        assert block["verdict"] in ("SERVED", "REFUSED_ON_EVERY_URL_TRIED"), org
        if block["verdict"] == "REFUSED_ON_EVERY_URL_TRIED":
            assert "NOT evidence" in block["why"], org
            assert block["attempts"], org


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

def test_the_census_declares_which_side_of_the_boundary_it_is_on():
    """The status is not decoration: it says whether this file IS the registry.

    Before PROMOTION the census lived in ``identity_census_proposed/`` and read
    PROPOSED_NOT_REGISTERED; after it, in ``identity_census/`` reading
    REGISTERED. A file whose status disagrees with its directory is the one
    thing this gate exists to refuse, in either direction.
    """
    doc = _load(PROPOSED_CENSUS)
    assert doc["market_id"] == MARKET
    assert doc["count"] == len(doc["hotels"])
    expected = "REGISTERED" if REGISTERED else "PROPOSED_NOT_REGISTERED"
    assert doc["status"] == expected
    in_registry_dir = PROPOSED_CENSUS.parent.name == "identity_census"
    assert in_registry_dir == (doc["status"] == "REGISTERED")


def test_every_admitted_identity_has_hard_evidence_and_a_corridor():
    """And its corridor follows the SAME tier order the assembler uses.

    ``markets.assignment.assign_hotels`` resolves an explicit naming at tier 2
    and a ZIP at tier 3. The census mirrors that: a row whose basis is
    ``explicit`` must be named by that corridor's registry, and a row whose
    basis is ``postal_code`` must sit in the corridor its ZIP claims. A census
    that disagreed with the assembler would place hotels one way and publish
    them another.
    """
    doc = _load(PROPOSED_CENSUS)
    cfg = MC.parse_market(_load(PROPOSED_CONTRACT), source=str(PROPOSED_CONTRACT))
    corridors = {c.corridor_id for c in cfg.corridors}
    zips = {z: c.corridor_id for c in cfg.corridors for z in c.included_postal_codes}
    explicit = {k: c.corridor_id for c in cfg.corridors for k in c.explicit_hotel_ids}
    assert doc["hotels"], "the census must not be empty"
    for h in doc["hotels"]:
        assert h["classification"] == "TRUE_HOTEL_IDENTITY", h["canonical_name"]
        assert h["street"] or h["phone"], h["canonical_name"]
        assert h["postal_code"] in zips, h["canonical_name"]
        assert h["corridor"] in corridors, h["canonical_name"]
        assert h["evidence"], h["canonical_name"]
        if h["assignment_basis"] == "explicit":
            assert explicit.get(h["identity_key"]) == h["corridor"], h["canonical_name"]
            assert h["assignment_value"] == h["identity_key"], h["canonical_name"]
        else:
            assert h["assignment_basis"] == "postal_code", h["canonical_name"]
            assert h["corridor"] == zips[h["postal_code"]], h["canonical_name"]
            assert h["identity_key"] not in explicit, h["canonical_name"]


def test_no_identity_record_carries_a_pet_policy():
    """Identity evidence never establishes a policy. Fail loudly if it leaks.

    ``policy_state`` is the one field allowed to say what the POLICY layer
    decided, and only on a registered census: PROMOTION marks the thirteen rows
    whose first-party read survived the modern gates POLICY_CONFIRMED or
    VERIFIED_NO_PETS, and every other row stays POLICY_NOT_VERIFIED. What may
    never appear -- in any row, in either file, on either side of the boundary
    -- is a policy FIELD sitting in an identity record or in an identity
    observation. That is the leak this gate was written for and it is unchanged.
    """
    from scripts.pettripfinder.identity_evidence import POLICY_FIELD_NAMES
    doc = _load(PROPOSED_CENSUS)
    allowed = ({"POLICY_NOT_VERIFIED", "POLICY_CONFIRMED", "VERIFIED_NO_PETS"}
               if REGISTERED else {"POLICY_NOT_VERIFIED"})
    for h in doc["hotels"] + doc["non_admitted"]:
        assert h["policy_state"] in allowed, (h["canonical_name"], h["policy_state"])
        leaked = POLICY_FIELD_NAMES & set(h)
        assert not leaked, (h["canonical_name"], sorted(leaked))
        for obs in h.get("evidence") or ():
            assert not (POLICY_FIELD_NAMES & set(obs)), h["canonical_name"]
    if REGISTERED:
        verified = [h for h in doc["hotels"] if h["policy_state"] != "POLICY_NOT_VERIFIED"]
        published = _load(PACKAGE / ("hotel_policy_facts_%s.json" % MARKET))["hotels"]
        refused = _load(PACKAGE / "markets" / "authority" / MARKET
                        / "hotel_exclusions.json")["exclusions"]
        assert len(verified) == len(published) + len(refused)


def test_identity_keys_are_unique_and_normalised():
    doc = _load(PROPOSED_CENSUS)
    keys = [h["identity_key"] for h in doc["hotels"]]
    assert len(keys) == len(set(keys))
    for h in doc["hotels"]:
        assert h["identity_key"] == normalize_name(h["canonical_name"])
        assert h["identity_key"], h["canonical_name"]


def test_a_rebrand_is_held_rather_than_published_under_a_guessed_name():
    """One address, two chain identities in the evidence, is a founder ruling."""
    doc = _load(PROPOSED_CENSUS)
    rebrands = [r for r in doc["non_admitted"]
                if r["classification"] == "SAME_IDENTITY_REBRAND_SUCCESSOR"]
    for r in rebrands:
        assert r["street"], r["canonical_name"]
        assert "founder ruling" in r["classification_reason"]
    keys = {h["identity_key"] for h in doc["hotels"]}
    for r in rebrands:
        assert r["identity_key"] not in keys, r["canonical_name"]


def test_a_name_only_row_never_became_an_identity():
    doc = _load(PROPOSED_CENSUS)
    for r in doc["non_admitted"]:
        if r["classification"] == "NAME_ONLY_UNRESOLVED":
            assert not (r["street"] and r["postal_code"]), r["canonical_name"]


def test_no_admitted_identity_states_a_state_other_than_tennessee():
    census = _load(PROPOSED_CENSUS)
    for h in census["hotels"]:
        assert h["state"] in ("TN", ""), (h["canonical_name"], h["state"])


def test_a_state_name_is_normalised_rather_than_truncated():
    """Marriott writes "Tennessee"; Hilton writes "TN". Both are Tennessee.

    Truncating the first to two characters yields "TE", which matches no state
    code -- and membership reads an unrecognised state as AFFIRMATIVE evidence
    that the property is elsewhere. Twenty real Nashville hotels were
    classified OUTSIDE_MARKET by exactly that before the normaliser existed.
    """
    census = _load(PROPOSED_CENSUS)
    bad = [r for r in census["hotels"] + census["non_admitted"]
           if (r.get("state") or "") not in ("", "TN", "KY", "AL", "GA", "MS", "AR", "MO",
                                             "VA", "NC")]
    assert not bad, sorted({r["state"] for r in bad})
    truncated = [r for r in census["non_admitted"]
                 if "state is TE" in (r.get("classification_reason") or "")]
    assert not truncated, "a truncated state name reached a membership decision"


def test_the_held_fringe_was_discovered_and_then_excluded_by_postal_code():
    """The hold has to bite on real inventory, or it is an omission."""
    raw = _load(PROPOSED_CONTRACT)
    held = {z for c in raw["corridors"] for z in c.get("_held_postal_codes") or []}
    census = _load(PROPOSED_CENSUS)
    for h in census["hotels"]:
        assert h["postal_code"] not in held, h["canonical_name"]
    found = [r for r in census["non_admitted"]
             if r["classification"] == "OUTSIDE_MARKET"
             and (r.get("postal_code") or "") in held]
    assert found, "no held-ZIP inventory was discovered, so the hold is uninformed"


def test_a_name_binding_never_crossed_a_town_or_an_area():
    """The bindings this order made must not contradict a stated place.

    Every town here is one a lead source actually names next to Nashville, and
    several of them are HELD fringe areas: a name-only row that says Franklin
    or Smyrna must never bind to a building inside the admitted market.
    """
    recon = _load(RECONCILIATION)
    census = _load(PROPOSED_CENSUS)
    by_key = {h["identity_key"]: h for h in census["hotels"]}
    for b in recon["name_attachment"]["bindings"]:
        target = by_key.get(normalize_name(b["bound_to"]))
        if target is None:
            continue
        offered = normalize_name(b["observation_name"])
        for town in ("franklin", "smyrna", "murfreesboro", "clarksville",
                     "lebanon", "hendersonville", "gallatin", "memphis",
                     "columbia", "cookeville"):
            if (" %s " % town) in (" %s " % offered):
                assert town in normalize_name(target["city"] or ""), (
                    "%r bound to a building in %r" % (b["observation_name"], target["city"]))


# --------------------------------------------------------------------------- #
# Routing.
# --------------------------------------------------------------------------- #

def test_every_route_is_bound_to_the_identity_it_serves():
    """A route serves a census identity, resolved the way the factory joins.

    The routing report keys each route by the name the LANE captured it under;
    a census row may carry that as an alias of its fuller canonical name, so
    the join goes through the alias table -- the same one
    ``nashville_tn_registration_002`` uses. One route resolves to no registered
    identity and that is not a drift: WoodSpring Suites Hermitage is HELD out of
    the registered census (no committed source states its city), so this gate
    allows exactly the routes whose identity the holds file names.
    """
    doc = _load(ROUTING)
    census = _load(PROPOSED_CENSUS)["hotels"]
    census_keys = {h["identity_key"] for h in census}
    for h in census:
        census_keys.update(h.get("identity_key_aliases") or ())
    held = set()
    holds = PACKAGE / "nashville_tn_identity_holds_002.json"
    if REGISTERED and holds.is_file():
        held = {h["identity_key_proposed"] for h in _load(holds)["holds"]}
    for r in doc["routes"]:
        assert r["identity_key"] in census_keys or r["identity_key"] in held, \
            r["canonical_name"]
        if r.get("url"):
            # http, not just https: an independent Nashville hotel publishes
            # its own site on whichever scheme it chose, and rewriting that
            # would be inventing a URL the source never stated.
            assert r["url"].startswith(("https://", "http://")), r["canonical_name"]
            assert " " not in r["url"], r["canonical_name"]


def test_a_route_on_another_chains_host_is_rejected_rather_than_captured():
    """The guard has to be live even in a run where nothing trips it.

    Toledo's destination roster linked redroofinns.com from a Baymont partner
    page. Following that would have published a Red Roof policy under a Baymont
    name, and only the name-family / host-family check catches it.
    """
    doc = _load(ROUTING)
    assert "a_route_is_a_proposal" in doc
    for r in doc["routes"]:
        if r["routing_state"] == "ROUTE_BRAND_MISMATCH":
            assert not r["url"]
            rej = r["rejected_route"]
            assert rej["name_family"] != rej["host_family"]
        if r.get("url"):
            assert r["binding_caveat"], r["canonical_name"]


def test_no_route_is_a_brand_locator_index():
    """A directory URL is never a route.

    The map source states ``choicehotels.com/tennessee/white-house/quality-inn-hotels``
    for a hotel that is in Nashville: a brand town INDEX, and the wrong town.
    Capturing it would read a list as a policy.
    """
    doc = _load(ROUTING)
    index_shape = re.compile(
        r"(/hotels/?$|-hotels/?$|/locations/?$|/find-hotels|/hotel-search|/search)", re.I)
    for r in doc["routes"] + doc.get("identity_fill_routes", []):
        u = r.get("url") or ""
        if u:
            assert not index_shape.search(u), (r["canonical_name"], u)


def test_a_legacy_marriott_route_was_repaired_from_the_brands_own_inventory():
    """A property code that will not parse is a routing repair, not a credit.

    Detroit PASS-008 lost 49 of 65 Firecrawl attempts to exactly this class.
    Where the map source states a legacy, fact-sheet or bare-code Marriott URL,
    the route is rewritten into the shape the brand publishes today.
    """
    doc = _load(ROUTING)
    repaired = [r for r in doc["routes"] if r.get("route_repair")]
    for r in repaired:
        rep = r["route_repair"]
        assert rep["as_stated_by_source"] != rep["repaired_to"], r["canonical_name"]
        assert rep["repaired_to"].startswith("https://www.marriott.com/en-us/hotels/")
        assert rep["repaired_to"].endswith("/overview/")


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
    """154 pages, 154 identities confirmed on the address the page itself states."""
    doc = _load(ATTENDED)
    assert doc["counts"]["pages_read"] == doc["counts"]["identity_confirmed"]
    for r in doc["rows"]:
        sig = r["identity_signals"]
        assert sig.get("address_on_page"), r["property_code"]
        assert sig.get("postal_code"), r["property_code"]


def test_a_page_that_states_no_policy_yields_no_policy():
    """SOURCE SILENCE is neither an acceptance nor a refusal.

    Two of the 154 pages carry no operative pet statement at all: Marriott's
    bnama publishes no Pet Policy row, and Hilton's bnaleci ships no petsInfo
    node. Both are identity-confirmed and in market, and neither may contribute
    a pets_allowed value in either direction.
    """
    doc = _load(ATTENDED)
    silent = [r for r in doc["rows"] if not r["exact_quote"]]
    assert silent, "the silence this gate exists for must be present"
    for r in silent:
        assert r["extraction"].get("pets_allowed") is None, r["property_code"]
        assert r["identity_confirmed"] is True, r["property_code"]


def test_a_property_code_selected_but_the_page_admitted():
    """The sharpest case in this market is bnafs.

    Marriott's own roster slugs it ``springhill-suites-franklin-mint``, its
    property code carries the Nashville BNA prefix, and its street is literally
    5629 NASHVILLE Rd. Three separate signals point at this market. Its own
    page states Franklin, KENTUCKY 42134, and that is what decides.
    """
    doc = _load(ATTENDED)
    rows = {r["property_code"]: r for r in doc["rows"]}
    outside = {c for c, r in rows.items() if not r["in_market"]}
    assert "bnafs" in outside
    assert rows["bnafs"]["identity_signals"]["postal_code"] == "42134"
    # Murfreesboro, Memphis and the held fringe, all reached by a BNA code or a
    # Nashville-area Hilton city page and all excluded on their own addresses.
    assert {"bnacb" if "bnacb" in rows else "bnamy", "mbtdtdt", "memphhf",
            "bnamj", "bnasy"} <= outside
    census_keys = {h["identity_key"] for h in _load(PROPOSED_CENSUS)["hotels"]}
    for r in doc["rows"]:
        if r["in_market"]:
            continue
        assert normalize_name(r["identity_signals"].get("name_on_page") or "") \
            not in census_keys, r["property_code"]


def test_a_service_animals_only_row_is_a_refusal_not_an_acceptance():
    """Two Nashville Fairfields say ADA service animals only. That is a NO."""
    doc = _load(ATTENDED)
    rows = [r for r in doc["rows"] if r.get("service_animals_only")]
    assert rows, "the service-animal carve-outs this gate exists for must be present"
    for r in rows:
        assert r["extraction"]["pets_allowed"] is False, r["property_code"]
    # And the Hilton side: every Hilton row carries the same service-animal
    # sentence, and it never turns a refusal into an acceptance.
    sa = doc.get("rows")
    refusals = [r for r in sa if r["brand"] == "HILTON"
                and r["extraction"].get("pets_allowed") is False]
    assert refusals, "Hilton Brentwood/Nashville Suites states service animals only"
    for r in refusals:
        assert "Service animals only" in r["exact_quote"] or \
            "service animal" in r["exact_quote"].lower(), r["property_code"]


def test_the_hilton_read_came_from_the_policy_node_not_the_review_prose():
    """A Hilton property page also carries guest reviews that mention pets."""
    doc = _load(ATTENDED)
    how = doc["how_each_brand_was_read"]["HILTON"]
    assert "review" in how and "petsInfo" in how
    for r in doc["rows"]:
        if r["brand"] != "HILTON":
            continue
        assert r["surface"] == "__NEXT_DATA__ petsInfo node"
        assert not re.search(r"\b(we|our family|the staff) (asked|were told|searched|said)\b",
                             r["exact_quote"], re.I)


def test_the_marriott_read_came_from_the_page_not_its_translation_table():
    """Marriott ships an i18n dictionary containing "hws.petPolicy":"Pet Policy".

    A search loose enough to match that would read a translation table as a
    hotel's policy. The read anchors on a CLOSING TAG, which the dictionary
    entry has none of, and the two markup shapes Marriott actually renders are
    both recorded on the row.
    """
    doc = _load(ATTENDED)
    how = doc["how_each_brand_was_read"]["MARRIOTT"]
    assert "Pet Policy" in how
    for r in doc["rows"]:
        if r["brand"] != "MARRIOTT" or not r["exact_quote"]:
            continue
        assert "hws." not in r["exact_quote"], r["property_code"]
        assert "petPolicy" not in r["exact_quote"], r["property_code"]


def test_the_attended_pass_read_two_origins_not_one_hundred_and_fifty_four():
    """A brand is batched by SAME-ORIGIN FETCH, not by 154 navigations."""
    doc = _load(ATTENDED)
    assert "ORIGIN" in doc["how_the_batch_ran"]
    assert doc["counts"]["pages_read"] >= 100


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


def test_a_held_read_never_reaches_the_clean_inventory():
    """Whatever the audit holds is excluded, whichever class held it."""
    audit = _load(EVIDENCE_AUDIT)
    clean = _load(CLEAN_AUTHORITY)
    clean_keys = {a["identity_key"] for a in
                  clean["clean_pet_friendly"] + clean["clean_verified_no_pets"]}
    for a in audit["reads"]:
        if a["audit_verdict"] == "HELD":
            assert a["audit_problems"], a["canonical_name"]
            assert a["identity_key"] not in clean_keys or not a["identity_key"]


def test_source_silence_never_became_a_policy():
    """A page that served and said nothing about pets settles nothing."""
    audit = _load(EVIDENCE_AUDIT)
    assert "SOURCE_SILENT_ENCODED_AS_POLICY" in audit["failure_classes_tested"]
    for a in audit["reads"]:
        if a["pets_allowed"] is None:
            assert a["audit_verdict"] == "HELD", a["canonical_name"]


def test_promotion_readiness_is_stated_with_its_reasons():
    doc = _load(REPORTS / "nashville_tn_shadow_market_001.json")
    assert doc["promotion_ready"] in ("YES", "NO")
    assert doc["projected"]["census"] > 0
    assert doc["projected"]["resolved"] + doc["projected"]["unresolved"] ==         doc["projected"]["census"]
    assert doc["projected"]["profiles"] == doc["projected"]["pet_friendly"]
    if doc["promotion_ready"] == "YES":
        assert doc["blockers"] == []
        assert doc["required_before_promotion"], "a YES must still name what the founder owes"


def test_paid_readiness_quotes_no_cost_it_did_not_measure():
    doc = _load(REPORTS / "nashville_tn_paid_readiness_001.json")
    assert doc["shared_ledgers"]["written"] == "NONE"
    assert doc["shared_ledgers"]["nashville_rows_in_either"] == 0
    assert doc["verdict"]["required_for_promotion"] == []
    for lane in ("bright_data", "places_paid_identity_discovery"):
        assert "UNQUOTED" in doc[lane]["expected_cost"], lane
        assert doc[lane]["required_for_promotion"] is False, lane


def test_the_founder_packet_is_grouped_and_every_item_is_answerable():
    doc = _load(REPORTS / "nashville_tn_founder_packet_001.json")
    groups = {i["group"] for i in doc["items"]}
    assert {"A_IDENTITY", "B_GEOGRAPHY", "C_CATEGORY", "F_CROSS_MARKET"} <= groups
    # Every held fringe corridor must reach the founder by name, with the
    # inventory its ruling would admit. A hold nobody is asked to rule on is
    # not a hold.
    raw = _load(PROPOSED_CONTRACT)
    held = [c["name"] for c in raw["corridors"] if c.get("_held_postal_codes")]
    geo = " | ".join(i["identity"] for i in doc["items"] if i["group"] == "B_GEOGRAPHY")
    for name in held:
        assert name in geo, name
    for i in doc["items"]:
        for field in ("identity", "evidence", "proposed_action", "recommendation",
                      "census_effect", "authority_effect", "routing_effect",
                      "reversibility", "blocks_promotion"):
            assert i.get(field), (i["group"], field)
        assert i["blocks_promotion"] in ("YES", "NO")


def test_parallel_safety_found_no_violation():
    doc = _load(REPORTS / "nashville_tn_parallel_safety_001.json")
    assert doc["counts"]["violations"] == 0
    m = doc["mechanical_assertions"]
    for k in ("detroit_files_changed", "fort_wayne_files_changed", "lexington_files_changed",
              "other_registered_market_files_changed", "shared_globals_changed",
              "market_registry_changed", "registered_census_changed",
              "market_authority_shards_changed", "shared_current_state_pins_changed",
              "deployment_files_changed", "shared_ledgers_written",
              "shared_factory_code_changed"):
        assert m[k] == 0, k
    assert m["production_assembly"] == "NOT RUN"
    assert m["deployed"] == "NO"
    # The one shared file this order rewrote is a GENERATED report the suite
    # reproduces, and it is allowed only under a proof that the delta was
    # exactly this order's own test module. A rewrite without that proof is a
    # violation like any other shared write.
    assert m["shared_generated_reports_rewritten_without_proof"] == 0
    repin = _load(REPORTS / "nashville_tn_test_inventory_repin_003.json")
    proof = repin["proof"]
    assert proof["proof_holds"] is True
    assert proof["modules_removed"] == []
    assert proof["modules_altered"] == []
    assert proof["modules_added_that_this_order_does_not_own"] == []
    assert all("nashville_tn" in mod for mod in proof["modules_added"])


def test_the_regression_classification_reports_no_true_new_failure():
    """Every failing node id carries exactly one class, and none is TRUE_NEW."""
    doc = _load(REPORTS / "nashville_tn_regression_classification_001.json")
    assert doc["byte_identity_proof"]["proof_holds"] is True
    assert doc["counts"]["TRUE_NEW_FAILURE"] == 0
    classes = {"PRE_EXISTING", "TRUE_NEW_FAILURE", "EXPECTED_EPOCH_CHANGE",
               "TEST_HARNESS_FLAKE", "MISSING_GITIGNORED_FIXTURE_IN_A_FRESH_WORKTREE",
               "SELF_REFERENTIAL_GATE_CLOSED_BY_RERUN"}
    for f in doc["failures"]:
        assert f["class"] in classes, f["node_id"]
        assert f["why"], f["node_id"]


def test_a_self_referential_gate_is_closed_by_EXECUTING_it():
    """This very gate reads the report that classifies it.

    A lane log captured before the report existed cannot classify such a gate
    without circularity: the gate fails because the report says TRUE_NEW, and
    the report says TRUE_NEW because the gate failed. Nothing is waved through
    on that account. Each self-referential gate is RE-EXECUTED against the
    finished report and the re-run decides, which is the delta-closure rule --
    closed by node id, by running it -- applied to the classifier's own tail.
    A failing re-run stays TRUE_NEW_FAILURE.
    """
    doc = _load(REPORTS / "nashville_tn_regression_classification_001.json")
    closure = doc.get("self_referential_gate_closure")
    if closure is None:
        return
    assert closure["nodes"], "a closure block with no nodes proves nothing"
    if closure.get("status") == "AWAITING_RERUN":
        # The transient pass-1 state, seen only by the re-run itself.
        return
    for n in closure["nodes"]:
        assert n["rerun_after_the_report_was_written"] in ("PASSED", "FAILED")
        if n["rerun_after_the_report_was_written"] == "FAILED":
            assert n["class"] == "TRUE_NEW_FAILURE", n["node_id"]
        else:
            assert n["class"] == "SELF_REFERENTIAL_GATE_CLOSED_BY_RERUN", n["node_id"]


def test_the_two_lane_runs_are_compared_by_set_not_by_count():
    """A matching COUNT can hide one failure arriving as another departs."""
    doc = _load(REPORTS / "nashville_tn_regression_classification_001.json")
    ident = doc["failure_set_identity"]
    assert "measured" in ident
    if ident["measured"]:
        assert ident["sets_identical"] is True, (ident["only_in_run_1"],
                                                 ident["only_in_run_2"])
        assert not ident["only_in_run_1"] and not ident["only_in_run_2"]


def test_no_clean_row_rests_on_a_fee_a_weight_or_a_count_alone():
    doc = _load(CLEAN_AUTHORITY)
    for a in doc["clean_pet_friendly"]:
        supporting = [e for e in a["evidence"] if "pets_allowed" in (e.get("field_refs") or [])]
        assert supporting, a["canonical_name"]


def test_the_audit_ran_over_every_lane_that_produced_a_read():
    audit = _load(EVIDENCE_AUDIT)
    lanes = set(audit["counts"]["by_lane"])
    assert "ATTENDED_BROWSER" in lanes
    assert "DIRECT_STATIC" in lanes
    assert audit["counts"]["reads_audited"] == (
        audit["counts"]["clean_pet_friendly"] + audit["counts"]["clean_verified_no_pets"]
        + audit["counts"]["held"])


@pytest.mark.parametrize("report", [
    "nashville_tn_owned_evidence_001.json",
    "nashville_tn_lead_sources_001.json",
    "nashville_tn_brand_city_pages_001.json",
    "nashville_tn_brand_sitemaps_001.json",
    "nashville_tn_census_reconciliation_001.json",
    "nashville_tn_free_static_capture_001.json",
    "nashville_tn_firecrawl_pass_001.json",
    "nashville_tn_competitor_gap_matrix_001.json",
    "nashville_tn_routing_001.json",
    "nashville_tn_attended_capture_001.json",
    "nashville_tn_ladder_plan_001.json",
    "nashville_tn_evidence_audit_001.json",
    "nashville_tn_clean_authority_001.json",
    "nashville_tn_founder_packet_001.json",
    "nashville_tn_paid_readiness_001.json",
    "nashville_tn_shadow_market_001.json",
    "nashville_tn_parallel_safety_001.json",
    "nashville_tn_corridor_explicit_002.json",
    "nashville_tn_test_inventory_repin_003.json",
    "nashville_tn_speed_benchmark_004.json",
    "nashville_tn_regression_classification_001.json",
])
def test_every_report_names_this_work_order_and_this_market(report):
    doc = _load(REPORTS / report)
    assert doc["work_order"] == "PTF-NASHVILLE-TN-NEW-MARKET-001"
    assert doc["market_id"] == MARKET
