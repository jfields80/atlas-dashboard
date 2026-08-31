"""PTF-GEOGRAPHY-NORMALIZATION-001 -- geography, gated.

Phase C established which identities exist and what state each is in. Phase D
establishes WHERE each one belongs, and proves the placement is reproducible:
re-running assignment from the committed configuration must return exactly what
the census stores, for all 550 rows across four markets.

The two tests worth reading first are
``test_a_zip_outranks_a_generic_mailing_city`` and
``test_a_city_never_matches_across_a_state_line``. Together they are the change
Phase D exists to make.
"""

from __future__ import annotations

import collections
import json
from pathlib import Path

import pytest

from scripts.pettripfinder.markets import assign_hotels, load_markets, market_by_id
from scripts.pettripfinder.markets.assignment import (
    TIER_CITY, TIER_EXPLICIT, TIER_UNASSIGNED, TIER_ZIP,
)
from scripts.pettripfinder.markets.contract import (
    SCHEMA_VERSION, MarketContractError, parse_market,
)
from scripts.pettripfinder.normalize_census_geography import recompute

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_DIR = REPO_ROOT / "launch_packages" / "pettripfinder"
CENSUS_DIR = PACKAGE_DIR / "identity_census"

COLUMBUS = "columbus-oh"
CLEVELAND = "cleveland-akron-canton-oh"
DAYTON = "dayton-oh"
CINCINNATI = "cincinnati-oh"
PITTSBURGH = "pittsburgh-pa"
DETROIT = "detroit-ann-arbor-mi"
INDIANAPOLIS = "indianapolis-in"
MILWAUKEE = "milwaukee-wi"
MARKETS = (COLUMBUS, CLEVELAND, DAYTON, CINCINNATI, PITTSBURGH, DETROIT,
           INDIANAPOLIS, MILWAUKEE)

EXPECTED_STATES = {COLUMBUS: ["OH"], CLEVELAND: ["OH"], DAYTON: ["OH"],
                   CINCINNATI: ["OH", "KY", "IN"], PITTSBURGH: ["PA"],
                   DETROIT: ["MI"], INDIANAPOLIS: ["IN"], MILWAUKEE: ["WI"]}
EXPECTED_ROUTE_MODE = {COLUMBUS: "legacy_unprefixed", CLEVELAND: "market_prefixed",
    DAYTON: "market_prefixed", CINCINNATI: "market_prefixed",
    PITTSBURGH: "market_prefixed", DETROIT: "market_prefixed",
    INDIANAPOLIS: "market_prefixed", MILWAUKEE: "market_prefixed"}
EXPECTED_ROWS = {COLUMBUS: 112, CLEVELAND: 188, DAYTON: 129, CINCINNATI: 256,
                 # 96 -> 101 at PTF-PITTSBURGH-FOUNDER-HOLD-RESOLUTION-005,
                 # an ADD-ONLY promotion of five identities that each
                 # carried a founder signature the sync could not apply
                 # while the identity did not exist. All 96 preserved.
                 # 143 -> 247 at PTF-DETROIT-ANN-ARBOR-HARDENED-SYNC-029.
                 # This lineage carried only Detroit's pre-recensus
                 # scaffold; the hardened market's promoted census is
                 # 247 identities, transplanted whole.
                 PITTSBURGH: 101, DETROIT: 247,
                 # PTF-INDIANAPOLIS-FOUNDER-PROMOTION-004 promoted the 257-identity recensus.
                 INDIANAPOLIS: 257,
                 MILWAUKEE: 147}
# Cincinnati was 121 until PTF-CINCINNATI-CENSUS-RECONCILIATION-001 rebuilt it
# from six official destination-marketing directories instead of from its own
# corridor registry.


def census(market_id):
    path = CENSUS_DIR / ("%s.json" % market_id)
    if not path.is_file():
        pytest.skip("%s is not present" % path.name)
    return json.loads(path.read_text(encoding="utf-8-sig"))


def market(market_id):
    return market_by_id(load_markets(), market_id)


def corridor_doc(market_id):
    return json.loads((PACKAGE_DIR / "markets" / ("%s.json" % market_id))
                      .read_text(encoding="utf-8-sig"))


# --------------------------------------------------------------------------
# schema
# --------------------------------------------------------------------------

class TestMarketSchema:

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_schema_version(self, market_id):
        assert corridor_doc(market_id)["schema"] == SCHEMA_VERSION == "ptf-market/1.1"

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_states_and_primary(self, market_id):
        m = market(market_id)
        assert list(m.states) == EXPECTED_STATES[market_id]
        assert m.primary_state_code == m.states[0]
        # The alias survives because title generation, meta descriptions and
        # JSON-LD across three live markets read it.
        assert m.state_code == m.primary_state_code

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_route_mode_is_explicit(self, market_id):
        assert market(market_id).route_mode == EXPECTED_ROUTE_MODE[market_id]

    def test_route_mode_is_required(self):
        doc = corridor_doc(DAYTON)
        del doc["route_mode"]
        with pytest.raises(MarketContractError) as e:
            parse_market(doc, "test")
        assert "route_mode" in str(e.value)

    def test_states_must_begin_with_the_primary(self):
        doc = dict(corridor_doc(CINCINNATI), states=["KY", "OH", "IN"])
        with pytest.raises(MarketContractError) as e:
            parse_market(doc, "test")
        assert "primary state" in str(e.value)

    def test_alias_must_agree_with_the_primary(self):
        """Two answers to one question is how a market ends up claiming both."""
        doc = dict(corridor_doc(CINCINNATI), state_code="KY")
        with pytest.raises(MarketContractError):
            parse_market(doc, "test")

    def test_a_corridor_may_not_claim_a_state_its_market_does_not_span(self):
        doc = json.loads(json.dumps(corridor_doc(DAYTON)))
        doc["corridors"][0]["state_code"] = "KY"
        with pytest.raises(MarketContractError) as e:
            parse_market(doc, "test")
        assert "not among its market" in str(e.value)


class TestMarketStateOwnership:

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_every_row_state_is_one_the_market_spans(self, market_id):
        allowed = set(market(market_id).states)
        for row in census(market_id)["hotels"]:
            assert row["state"] in allowed, row["canonical_name"]

    def test_cincinnati_really_is_tri_state(self):
        """96/16/9 before the rebuild. Kentucky grew nearly fivefold, because
        the airport and Florence clusters the old census never surveyed are
        almost all on the Kentucky side of the river."""
        counts = collections.Counter(r["state"] for r in census(CINCINNATI)["hotels"])
        assert counts == {"OH": 170, "KY": 77, "IN": 9}

    def test_a_kentucky_property_is_not_relabelled_ohio(self):
        """The market's primary state may never overwrite a row's own."""
        ky = [r for r in census(CINCINNATI)["hotels"] if r["state"] == "KY"]
        assert ky
        assert market(CINCINNATI).primary_state_code == "OH"
        assert all(r["state"] == "KY" for r in ky)


# --------------------------------------------------------------------------
# precedence
# --------------------------------------------------------------------------

def _row(name, city="", state="OH", zip5=""):
    return {"name": name, "city": city, "state": state, "postal_code": zip5}


class TestAssignmentPrecedence:

    def test_a_zip_outranks_a_generic_mailing_city(self):
        """The change Phase D exists to make.

        Four Cincinnati properties carry the mailing city "Cincinnati" and sit
        fifteen miles east in Eastgate. City-first sent them downtown.
        """
        m = market(CINCINNATI)
        rows = [_row("eastgate test", city="Cincinnati", zip5="45255")]
        a = assign_hotels(m, rows, fail_closed=False)
        corridor = a.corridor_of["eastgate test"][0]
        assert corridor.endswith("eastgate-batavia")
        assert a.basis_of["eastgate test"] == (TIER_ZIP, "45255")

    def test_a_city_never_matches_across_a_state_line(self):
        """Dayton, Kentucky is not Dayton, Ohio."""
        m = market(CINCINNATI)
        ky = [c for c in m.corridors if c.state_code == "KY"]
        assert ky, "the tri-state market must declare Kentucky corridors"
        corridor = ky[0]
        city = corridor.included_cities[0]
        in_state = assign_hotels(m, [_row("k", city=city, state="KY")],
                                 fail_closed=False)
        assert in_state.corridor_of.get("k")
        # Same city string, wrong state: no match, and no guess.
        out_of_state = assign_hotels(m, [_row("k", city=city, state="OH")],
                                     fail_closed=False)
        assert not out_of_state.corridor_of.get("k")

    def test_explicit_outranks_everything(self):
        m = market(COLUMBUS)
        explicit = [c for c in m.corridors if c.explicit_hotel_ids]
        assert explicit
        key = explicit[0].explicit_hotel_ids[0]
        a = assign_hotels(m, [_row(key, city="Dublin", zip5="43215")],
                          fail_closed=False)
        assert a.corridor_of[key] == (explicit[0].corridor_id,)
        assert a.basis_of[key][0] == TIER_EXPLICIT

    def test_exclusion_removes_a_hotel_a_zip_would_otherwise_place(self):
        """Exclusion is the highest tier: it removes eligibility outright.

        Listing the same id as BOTH explicit and excluded is rejected by the
        contract, so the exclusion is tested against a hotel the ZIP tier would
        otherwise have claimed.
        """
        m = market(DAYTON)
        zipped = [c for c in m.corridors if c.included_postal_codes][0]
        code = zipped.included_postal_codes[0]
        placed = assign_hotels(m, [_row("excluded test", zip5=code)],
                               fail_closed=False)
        assert placed.corridor_of["excluded test"] == (zipped.corridor_id,)

        doc = json.loads(json.dumps(corridor_doc(DAYTON)))
        for c in doc["corridors"]:
            if c["corridor_id"] == zipped.corridor_id:
                c["excluded_hotel_ids"] = ["excluded test"]
        a = assign_hotels(parse_market(doc, "test"),
                          [_row("excluded test", zip5=code)], fail_closed=False)
        assert not a.corridor_of.get("excluded test")

    def test_no_match_is_unassigned_never_guessed(self):
        a = assign_hotels(market(DAYTON),
                          [_row("nowhere inn", city="Zanesville", zip5="43701")],
                          fail_closed=False)
        assert not a.corridor_of.get("nowhere inn")
        assert a.basis_of.get("nowhere inn", (TIER_UNASSIGNED, ""))[0] \
            in (TIER_UNASSIGNED, "")

    def test_city_is_only_consulted_when_the_zip_does_not_resolve(self):
        m = market(DAYTON)
        city_corridor = [c for c in m.corridors if c.included_cities][0]
        a = assign_hotels(m, [_row("c", city=city_corridor.included_cities[0],
                                   zip5="99999")], fail_closed=False)
        assert a.basis_of["c"][0] == TIER_CITY


# --------------------------------------------------------------------------
# basis integrity
# --------------------------------------------------------------------------

class TestBasisIntegrity:

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_every_stored_basis_is_provable(self, market_id):
        """No human judgement may be labelled postal_code.

        Cincinnati recorded 121 rows as ``postal_code`` when several of those
        ZIPs appeared in no corridor at all, and Dayton recorded eleven as
        ``county_name`` for a tier that does not exist.
        """
        m = market(market_id)
        for row in census(market_id)["hotels"]:
            basis = row["assignment_basis"]
            value = row["assignment_value"]
            assert basis in (TIER_EXPLICIT, TIER_ZIP, TIER_CITY, TIER_UNASSIGNED)
            if basis == TIER_UNASSIGNED:
                assert row["corridor"] is None and value == ""
                continue
            corridor = m.corridor_by_id(row["corridor"])
            if basis == TIER_ZIP:
                assert value in corridor.included_postal_codes, row["canonical_name"]
                assert value == row["postal_code"][:5]
            elif basis == TIER_CITY:
                assert row["city"].lower() in [c.lower() for c in corridor.included_cities]
                if corridor.state_code:
                    assert corridor.state_code == row["state"]
            elif basis == TIER_EXPLICIT:
                assert value in corridor.explicit_hotel_ids

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_no_county_basis_survives(self, market_id):
        """No county tier exists, so no row may claim one."""
        for row in census(market_id)["hotels"]:
            assert row["assignment_basis"] != "county_name", row["canonical_name"]


class TestDuplicatePostalCodes:

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_no_market_registers_a_zip_twice(self, market_id):
        owners = collections.defaultdict(list)
        for c in market(market_id).corridors:
            for code in c.included_postal_codes:
                owners[code].append(c)
        for code, matched in owners.items():
            if len(matched) > 1:
                assert all(c.allow_multi_corridor for c in matched), code

    def test_an_unauthorised_duplicate_fails_at_market_load(self):
        """Caught from the config alone, once -- not once per hotel."""
        doc = json.loads(json.dumps(corridor_doc(CINCINNATI)))
        doc["corridors"][0]["included_postal_codes"] = ["45255"]
        doc["corridors"][0]["allow_multi_corridor"] = False
        with pytest.raises(MarketContractError) as e:
            parse_market(doc, "test")
        assert "45255" in str(e.value)

    def test_the_45044_conflict_is_resolved(self):
        """It was registered to two corridors, neither authorising sharing."""
        owners = [c.corridor_id for c in market(CINCINNATI).corridors
                  if "45044" in c.included_postal_codes]
        assert len(owners) == 1
        assert owners[0].endswith("middletown-monroe")


# --------------------------------------------------------------------------
# reproducibility -- the whole point
# --------------------------------------------------------------------------

class TestReproducibility:

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_stored_equals_recomputed(self, market_id):
        recomputed, changes = recompute(market_id)
        assert changes == [], [c["canonical_name"] for c in changes[:6]]
        assert len(recomputed["hotels"]) == EXPECTED_ROWS[market_id]

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_unassigned_rows_really_match_nothing(self, market_id):
        m = market(market_id)
        for row in census(market_id)["hotels"]:
            if row["corridor"] is not None:
                continue
            zip5 = (row.get("postal_code") or "")[:5]
            city = (row.get("city") or "").lower()
            for c in m.corridors:
                assert row["identity_key"] not in c.explicit_hotel_ids
                assert not (zip5 and zip5 in c.included_postal_codes), \
                    "%s is unassigned but its ZIP is registered" % row["canonical_name"]


class TestKnownGeographyRepairs:

    def test_no_eastgate_property_resolves_to_downtown_cincinnati(self):
        """The named defect. ZIP 45255/45245 is Eastgate, not Downtown."""
        rows = [r for r in census(CINCINNATI)["hotels"]
                if r["postal_code"][:5] in ("45255", "45245")]
        assert len(rows) == 9
        for row in rows:
            assert row["corridor"].endswith("eastgate-batavia"), row["canonical_name"]

    def test_dayton_north_is_registered(self):
        rows = [r for r in census(DAYTON)["hotels"] if r["postal_code"][:5] == "45414"]
        assert len(rows) == 17
        assert {r["corridor"].split("__")[-1] for r in rows} == {"airport-vandalia"}

    def test_beavercreek_45431_is_registered(self):
        rows = [r for r in census(DAYTON)["hotels"] if r["postal_code"][:5] == "45431"]
        assert len(rows) == 8
        assert {r["corridor"].split("__")[-1] for r in rows} == {"fairborn-beavercreek"}

    def test_45440_belongs_to_kettering_not_xenia(self):
        """It was registered to Xenia while its one census row sat in Kettering."""
        rows = [r for r in census(DAYTON)["hotels"] if r["postal_code"][:5] == "45440"]
        assert rows
        assert {r["corridor"].split("__")[-1] for r in rows} == {"kettering-centerville"}
        xenia = market(DAYTON).corridor_by_id("dayton-oh__xenia")
        assert "45440" not in xenia.included_postal_codes

    def test_the_eleven_county_rows_all_resolve_by_postal_code(self):
        """Every one was already reproducible; only its label was impossible."""
        for name in ("Americas Best Value Inn Celina", "Cobblestone Hotel & Suites Eaton",
                     "Golden Inn New Paris", "Hearthstone Inn Cedarville",
                     "Springs Motel Yellow Springs"):
            row = next(r for r in census(DAYTON)["hotels"]
                       if r["canonical_name"] == name)
            assert row["assignment_basis"] == TIER_ZIP, name
            assert row["corridor"] is not None


class TestNoGeographicInferenceFromNames:

    def test_a_row_with_no_stated_city_stays_without_one(self):
        """"SpringHill Suites Columbus Airport Gahanna" states no city.

        Reading "Gahanna" off the hotel's name would be inference, and a brand
        string is not a geographic fact.
        """
        row = next(r for r in census(COLUMBUS)["hotels"]
                   if r["identity_key"] == "springhill suites columbus airport gahanna")
        assert row["city"] == ""
        # Its ZIP is stated, so it is placed by ZIP or not at all -- never by
        # the word in its name.
        assert row["assignment_basis"] in (TIER_ZIP, TIER_UNASSIGNED)

    def test_assignment_never_reads_the_display_name(self):
        m = market(CINCINNATI)
        a = assign_hotels(m, [_row("Hotel Eastgate Downtown Airport", city="",
                                   state="OH", zip5="")], fail_closed=False)
        assert not a.corridor_of.get("hotel eastgate downtown airport")


class TestUnassignedIsLegitimate:

    def test_published_hotels_may_be_unassigned(self):
        """Twelve published Columbus hotels sit in this tier, and always have.

        Forcing every hotel into a corridor would place properties by guess.
        """
        rows = [r for r in census(COLUMBUS)["hotels"] if r["corridor"] is None]
        assert rows
        assert all(r["assignment_basis"] == TIER_UNASSIGNED for r in rows)

    def test_assignment_does_not_raise_on_unassigned(self):
        m = market(COLUMBUS)
        rows = [{"name": r["identity_key"], "city": r["city"], "state": r["state"],
                 "postal_code": r["postal_code"]} for r in census(COLUMBUS)["hotels"]]
        a = assign_hotels(m, rows, fail_closed=True)
        assert a.unassigned


class TestCrossMarketOwnership:

    def test_no_identity_appears_in_two_market_censuses(self):
        seen = collections.defaultdict(list)
        for market_id in MARKETS:
            for row in census(market_id)["hotels"]:
                seen[row["identity_key"]].append(market_id)
        duplicates = {k: v for k, v in seen.items() if len(set(v)) > 1}
        # PTF-INDIANAPOLIS-FOUNDER-PROMOTION-004: a generic-path census keeps a bare chain name exactly as
        # discovery observed it ("Home2 Suites by Hilton", an Indianapolis
        # BUDGET_DEFERRED row); the same bare key exists in Cleveland. Neither
        # is authority, both markets route market_prefixed, and the collision
        # is recorded here rather than resolved by renaming a census row.
        # PTF-DETROIT-ANN-ARBOR-HARDENED-SYNC-029 brought Detroit onto this
        # lineage carrying a second bare chain name: a census row recorded
        # as plain "Comfort Suites" (1565 North Opdyke Road, Auburn Hills)
        # where Indianapolis already holds the same bare key. Detroit's
        # own identity screen in order 025 had ALREADY flagged that row as
        # a probable duplicate of the published "Comfort Suites Auburn
        # Hills Detroit", and PTF-PITTSBURGH-FOUNDER-HOLD-RESOLUTION-005
        # refused the same key for the same reason. It is UNRESOLVED and
        # in NEITHER market's authority -- not published, not excluded --
        # so it is recorded here exactly as the Home2 collision is,
        # rather than resolved by renaming a census row inside a sync.
        known_bare_name_collisions = {
            "home2 suites by hilton": [CLEVELAND, INDIANAPOLIS],
            "comfort suites": [DETROIT, INDIANAPOLIS],
        }
        assert {k: sorted(set(v)) for k, v in duplicates.items()} == {
            k: sorted(v) for k, v in known_bare_name_collisions.items()}


class TestIdempotenceAndPreservation:

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_recompute_is_idempotent(self, market_id):
        once, _ = recompute(market_id)
        twice, changes = recompute(market_id)
        assert changes == []
        assert json.dumps(once, sort_keys=True) == json.dumps(twice, sort_keys=True)

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_only_the_three_owned_fields_can_differ(self, market_id):
        """The Phase C lesson, kept: a patch must not become a rebuild."""
        source = census(market_id)
        patched, _ = recompute(market_id)
        owned = {"corridor", "assignment_basis", "assignment_value"}
        for before, after in zip(source["hotels"], patched["hotels"]):
            assert set(before) == set(after), "a field was added or dropped"
            for key in before:
                if key not in owned:
                    assert before[key] == after[key], "%s changed %s" % (
                        before.get("canonical_name"), key)

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_census_membership_is_untouched(self, market_id):
        source = census(market_id)
        patched, _ = recompute(market_id)
        assert ([r["identity_key"] for r in source["hotels"]]
                == [r["identity_key"] for r in patched["hotels"]])
        assert source["count"] == patched["count"] == EXPECTED_ROWS[market_id]
