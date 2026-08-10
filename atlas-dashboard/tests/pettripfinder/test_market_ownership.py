"""PTF-MULTI-MARKET-INVENTORY-SCOPING-001 -- explicit market ownership.

The defect being locked out: the generator used to select every approved
inventory row, so a second market's hotels would publish inside the first
market's package the moment their rows existed.

The near-miss being locked out with it: the obvious fix -- "select the hotels a
corridor claims" -- would have deleted twelve live Columbus hotels, because
corridor assignment has an "unassigned, published anyway" tier and twelve
published hotels sit in it. Several tests below exist purely to keep ownership
and corridor membership from being quietly re-fused.

Counts asserted here are measured from the live authority, not from the work
order's prose. Where the two disagreed, the measurement won and the difference
is called out in the test that measures it.
"""

from __future__ import annotations

import pytest

from scripts.pettripfinder.market_ownership import (
    MARKET_ID_FIELD, MarketOwnershipError, owned_by, ownership_of,
    ownership_summary, registered_market_ids, validate_ownership,
)
from scripts.pettripfinder.markets import assign_hotels, load_markets, market_by_id
from scripts.pettripfinder.site_data import (
    load_published_hotel_policy_facts, normalize_name, read_production_rows,
    verified_public_hotels,
)

COLUMBUS = "columbus-oh"
CLEVELAND = "cleveland-akron-canton-oh"
DAYTON = "dayton-oh"

#: A synthetic registry. Dayton has no committed market config yet -- its
#: configuration belongs to the isolated Dayton worktree, and inventing one
#: here would collide with that work. Ownership validation takes the registry
#: as a parameter precisely so isolation can be proven without it.
SYNTHETIC_REGISTRY = {COLUMBUS, CLEVELAND, DAYTON}


def row(name, market_id=COLUMBUS, **extra):
    base = {"name": name, "category": "pet-friendly-hotels", "city": "Columbus",
            "state": "OH", "postal_code": "43215"}
    base.update(extra)
    if market_id is not None:
        base[MARKET_ID_FIELD] = market_id
    return base


# --------------------------------------------------------------------------- #
# Ownership contract
# --------------------------------------------------------------------------- #

class TestOwnershipContract:

    def test_a_registered_market_id_is_accepted(self):
        rows = [row("A"), row("B")]
        assert validate_ownership(rows, registered=SYNTHETIC_REGISTRY) == {
            "a": COLUMBUS, "b": COLUMBUS}

    def test_a_missing_market_id_fails_closed(self):
        """Absent ownership must never default to the market being built --
        defaulting is exactly how a foreign row would enter a package."""
        with pytest.raises(MarketOwnershipError) as e:
            validate_ownership([row("A"), row("B", market_id=None)],
                               registered=SYNTHETIC_REGISTRY)
        assert "no market_id" in str(e.value)

    def test_a_blank_market_id_fails_closed(self):
        with pytest.raises(MarketOwnershipError):
            validate_ownership([row("A", market_id="   ")], registered=SYNTHETIC_REGISTRY)

    def test_an_unknown_market_id_fails_closed(self):
        with pytest.raises(MarketOwnershipError) as e:
            validate_ownership([row("A", market_id="cleveland-oh")],
                               registered=SYNTHETIC_REGISTRY)
        assert "not in the committed registry" in str(e.value)

    def test_duplicate_primary_ownership_fails(self):
        """One identity, two markets. Whichever package built last would win,
        and the hotel would appear in both or neither depending on order."""
        with pytest.raises(MarketOwnershipError) as e:
            validate_ownership([row("Hotel X", market_id=COLUMBUS),
                                row("Hotel X", market_id=CLEVELAND)],
                               registered=SYNTHETIC_REGISTRY)
        assert "two primary markets" in str(e.value)

    def test_the_same_market_twice_is_not_a_conflict(self):
        """Two rows for one identity in ONE market is a different problem
        (inventory duplication) and is not this contract's failure to report."""
        validate_ownership([row("Hotel X"), row("Hotel X")],
                           registered=SYNTHETIC_REGISTRY)

    def test_building_for_an_unregistered_market_fails(self):
        with pytest.raises(MarketOwnershipError) as e:
            owned_by([row("A")], "atlantis-oh", registered=SYNTHETIC_REGISTRY)
        assert "unregistered market" in str(e.value)

    def test_every_row_is_validated_not_only_the_selected_ones(self):
        """A malformed Cleveland row must break the Cleveland build, not pass
        silently because a Columbus build happened to run first."""
        rows = [row("Good"), row("Bad", market_id=None)]
        with pytest.raises(MarketOwnershipError):
            owned_by(rows, COLUMBUS, registered=SYNTHETIC_REGISTRY)

    def test_the_registry_is_the_authority_not_a_constant_here(self):
        live = registered_market_ids()
        assert COLUMBUS in live and CLEVELAND in live
        assert live == {m.market_id for m in load_markets()}

    def test_ownership_summary_reports_missing_rows(self):
        assert ownership_summary([row("A"), row("B", market_id=None)]) == {
            "<missing>": 1, COLUMBUS: 1}


class TestOwnershipIsNotCorridorMembership:

    def test_a_hotel_can_be_owned_and_corridor_unassigned(self):
        """The property the whole work order turns on."""
        market = market_by_id(load_markets(), COLUMBUS)
        r = row("Nowhere Inn", city="Zanesville", postal_code="43701")
        assignment = assign_hotels(market, [r], fail_closed=False)
        assert [x["name"] for x in assignment.unassigned] == ["Nowhere Inn"]
        assert owned_by([r], COLUMBUS, registered=SYNTHETIC_REGISTRY) == [r]

    def test_corridor_assignment_never_confers_ownership(self):
        """A Cleveland-owned row whose city a Columbus corridor happens to
        list is still not Columbus inventory."""
        r = row("Dublin Cleveland Inn", market_id=CLEVELAND, city="Dublin")
        assert owned_by([r], COLUMBUS, registered=SYNTHETIC_REGISTRY) == []
        assert owned_by([r], CLEVELAND, registered=SYNTHETIC_REGISTRY) == [r]


# --------------------------------------------------------------------------- #
# Columbus preservation -- against the real committed authority
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def live():
    rows = read_production_rows()
    hotels = [r for r in owned_by(rows, COLUMBUS)
              if r.get("category") == "pet-friendly-hotels"]
    verified = verified_public_hotels(hotels, load_published_hotel_policy_facts())
    market = market_by_id(load_markets(), COLUMBUS)
    return {"rows": rows, "hotels": hotels, "verified": verified, "market": market,
            "assignment": assign_hotels(market, verified, fail_closed=False)}


class TestColumbusPreservation:

    def test_every_inventory_row_has_valid_ownership(self, live):
        """Inventory is multi-market since Cleveland landed; what must hold is
        that EVERY row states a registered owner, not that one market owns
        them all."""
        owner = validate_ownership(live["rows"], context="live inventory")
        assert set(owner.values()) <= registered_market_ids()
        assert COLUMBUS in set(owner.values())

    def test_all_88_published_hotels_belong_to_columbus(self, live):
        assert len(live["verified"]) == 88
        assert all(ownership_of(r) == COLUMBUS for r in live["verified"])

    def test_the_columbus_package_selects_exactly_the_owned_rows(self, live):
        """116 Columbus rows out of a seed that now also holds Cleveland's."""
        selected = owned_by(live["rows"], COLUMBUS)
        assert len(selected) == 116
        assert len(selected) < len(live["rows"])
        assert all(ownership_of(r) == COLUMBUS for r in selected)

    def test_route_count_remains_88(self, live):
        selected = [r for r in owned_by(live["rows"], COLUMBUS)
                    if r.get("category") == "pet-friendly-hotels"]
        assert len(verified_public_hotels(
            selected, load_published_hotel_policy_facts())) == 88

    def test_the_14_verified_no_pets_retain_their_status(self):
        """Scoped by market. The file now also carries Cleveland's 8, and
        counting the file would report every market's negative evidence as
        this one's."""
        from scripts.pettripfinder.hotel_exclusions import load_exclusions
        no_pets = [e for e in load_exclusions()
                   if e.get("market_id") == COLUMBUS
                   and e.get("exclusion_state") == "VERIFIED_NO_PETS"]
        assert len(no_pets) == 14
        # Columbus also holds 2 OUT_OF_CURRENT_CATEGORY rows; counting its
        # slice of the file would report 16 and overstate negative evidence.
        assert len([e for e in load_exclusions()
                    if e.get("market_id") == COLUMBUS]) == 16

    def test_the_corridor_unassigned_published_hotels_remain(self, live):
        """MEASURED = 12. The work order says 16; that figure was never
        computed against the live authority. What matters is not the number but
        that every one of them stays owned and publication-eligible, which is
        what this asserts."""
        unassigned = live["assignment"].unassigned
        assert len(unassigned) == 12
        assert all(ownership_of(r) == COLUMBUS for r in unassigned)
        published = {normalize_name(r["name"]) for r in live["verified"]}
        assert {normalize_name(r["name"]) for r in unassigned} <= published

    def test_the_unassigned_hotels_are_the_expected_identities(self, live):
        assert sorted(r["name"] for r in live["assignment"].unassigned) == sorted([
            "Aloft Columbus Westerville",
            "BrewDog DogHouse Columbus",
            "Embassy Suites Columbus - Airport/Corporate Exchange",
            "Fairfield Inn & Suites Columbus New Albany",
            "Hampton Inn & Suites Canal Winchester Columbus",
            "Hampton Inn & Suites Columbus-Easton Area",
            "Hampton Inn and Suites Columbus Scioto Downs",
            "Hilton Garden Inn Columbus Easton",
            "Home2 Suites New Albany Columbus",
            "Sonesta Simply Suites Columbus Airport Gahanna",
            "TownePlace Suites Columbus Airport Gahanna",
            "TownePlace Suites Columbus Easton Area",
        ])

    def test_no_cleveland_identity_can_enter_a_columbus_build(self, live):
        """Against the real 188-identity Cleveland census, not a fixture."""
        import json
        from pathlib import Path
        census = (Path(__file__).resolve().parents[2] / "launch_packages"
                  / "pettripfinder" / "identity_census"
                  / "cleveland-akron-canton-oh.json")
        cleveland = {h["normalized_name"]
                     for h in json.loads(census.read_text(encoding="utf-8-sig"))["hotels"]}
        assert len(cleveland) >= 180
        selected = {normalize_name(r["name"]) for r in owned_by(live["rows"], COLUMBUS)}
        assert selected & cleveland == set()

    def test_reconciliation_remains_114_88_14_102_12(self):
        from scripts.pettripfinder.build_market_manifest import build_package
        pkg = build_package(COLUMBUS, confirmed_identity_count=114)
        assert pkg.reconciliation() == (114, 88, 14, 102, 12)
        assert len(pkg.hotel_routes) == 88
        assert len(pkg.corridor_routes) == 9
        assert len(pkg.corridor_unassigned_hotels) == 12
