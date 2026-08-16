"""PTF-MULTI-MARKET-INVENTORY-SCOPING-001 -- market isolation and assembly.

Synthetic markets throughout. Cleveland's real proposed authority is NOT
integrated by this work order, and Dayton's inventory lives in an isolated
worktree, so proving isolation with fixtures is the only way to prove it
without importing either market's facts.

What these tests are really defending: adding a market must be ADDITIVE. A new
market's package may add routes to the production site and may not, under any
circumstance, change an existing market's routes, hashes, reconciliation, or
its corridor-unassigned-but-published hotels.
"""

from __future__ import annotations

import hashlib

import pytest

from scripts.pettripfinder.market_ownership import (
    MARKET_ID_FIELD, MarketOwnershipError, owned_by,
)
from scripts.pettripfinder.market_package import (
    MarketPackage, MarketPackageError, assemble_market_packages, hash_owned_files,
)

COLUMBUS = "columbus-oh"
CLEVELAND = "cleveland-akron-canton-oh"
DAYTON = "dayton-oh"
REGISTRY = {COLUMBUS, CLEVELAND, DAYTON}


def hotel(name, market_id, city="Somewhere"):
    return {"name": name, "category": "pet-friendly-hotels", "city": city,
            "state": "OH", MARKET_ID_FIELD: market_id}


#: One inventory holding three markets at once -- the state this architecture
#: exists to make safe.
MIXED = [
    hotel("Columbus Downtown Inn", COLUMBUS, "Columbus"),
    hotel("Columbus Westerville Suites", COLUMBUS, "Westerville"),
    hotel("Cleveland Beachwood Inn", CLEVELAND, "Beachwood"),
    hotel("Cleveland Downtown Suites", CLEVELAND, "Cleveland"),
    hotel("Dayton Oregon District Inn", DAYTON, "Dayton"),
]


def package(market_id, hotel_routes, corridor_routes=(), *, unassigned=(),
            confirmed=10, published=None, no_pets=1, unresolved=2, site=None):
    published = len(hotel_routes) if published is None else published
    hashes = ({r: hashlib.sha256(("%s:%s" % (market_id, r)).encode()).hexdigest()
               for r in tuple(hotel_routes) + tuple(corridor_routes)}
              if site is None else site)
    return MarketPackage(
        market_id=market_id, authority_commit="deadbeef",
        confirmed_identity_count=confirmed, published_pet_friendly_count=published,
        verified_no_pets_count=no_pets, unresolved_count=unresolved,
        hotel_routes=tuple(hotel_routes), corridor_routes=tuple(corridor_routes),
        corridor_unassigned_hotels=tuple(unassigned), file_hashes=hashes)


# --------------------------------------------------------------------------- #
# Selection isolation
# --------------------------------------------------------------------------- #

class TestMarketSelectionIsolation:

    def test_a_cleveland_hotel_is_excluded_from_a_columbus_package(self):
        names = [r["name"] for r in owned_by(MIXED, COLUMBUS, registered=REGISTRY)]
        assert names == ["Columbus Downtown Inn", "Columbus Westerville Suites"]
        assert "Cleveland Beachwood Inn" not in names

    def test_the_same_cleveland_hotel_is_included_in_a_cleveland_package(self):
        names = [r["name"] for r in owned_by(MIXED, CLEVELAND, registered=REGISTRY)]
        assert names == ["Cleveland Beachwood Inn", "Cleveland Downtown Suites"]

    def test_a_dayton_hotel_is_excluded_from_both(self):
        for market in (COLUMBUS, CLEVELAND):
            names = [r["name"] for r in owned_by(MIXED, market, registered=REGISTRY)]
            assert "Dayton Oregon District Inn" not in names
        assert [r["name"] for r in owned_by(MIXED, DAYTON, registered=REGISTRY)] == [
            "Dayton Oregon District Inn"]

    def test_every_row_lands_in_exactly_one_package(self):
        seen = []
        for market in REGISTRY:
            seen += [r["name"] for r in owned_by(MIXED, market, registered=REGISTRY)]
        assert sorted(seen) == sorted(r["name"] for r in MIXED)
        assert len(seen) == len(set(seen))

    def test_a_shared_city_name_does_not_cause_crossover(self):
        """Ohio has a Dublin near Columbus. If another market ever lists one
        too, city text must not move ownership."""
        rows = [hotel("Dublin Inn Columbus", COLUMBUS, "Dublin"),
                hotel("Dublin Inn Cleveland", CLEVELAND, "Dublin")]
        assert [r["name"] for r in owned_by(rows, COLUMBUS, registered=REGISTRY)] == [
            "Dublin Inn Columbus"]
        assert [r["name"] for r in owned_by(rows, CLEVELAND, registered=REGISTRY)] == [
            "Dublin Inn Cleveland"]

    def test_one_hotel_cannot_silently_publish_in_two_markets(self):
        rows = MIXED + [hotel("Columbus Downtown Inn", CLEVELAND, "Cleveland")]
        with pytest.raises(MarketOwnershipError) as e:
            owned_by(rows, COLUMBUS, registered=REGISTRY)
        assert "two primary markets" in str(e.value)


# --------------------------------------------------------------------------- #
# Multi-market assembly
# --------------------------------------------------------------------------- #

class TestMultiMarketAssembly:

    def test_two_validated_packages_combine(self):
        cbus = package(COLUMBUS, ["/pet-friendly-hotels/cbus-a/"],
                       ["/pet-friendly-hotels/dublin/"], unassigned=("Cbus B",))
        cle = package(CLEVELAND, ["/cleveland-akron-canton/hotels/cle-a/"],
                      ["/cleveland-akron-canton/beachwood/"])
        out = assemble_market_packages([cbus, cle])
        assert out["market_count"] == 2
        assert out["total_owned_routes"] == 4
        assert out["route_owner"]["/pet-friendly-hotels/cbus-a/"] == COLUMBUS
        assert out["route_owner"]["/cleveland-akron-canton/beachwood/"] == CLEVELAND

    def test_adding_a_market_does_not_change_the_others_hashes(self):
        cbus = package(COLUMBUS, ["/pet-friendly-hotels/cbus-a/"])
        alone = assemble_market_packages([cbus])
        with_cle = assemble_market_packages(
            [cbus, package(CLEVELAND, ["/cleveland-akron-canton/hotels/cle-a/"])])
        assert (alone["per_market"][COLUMBUS]["owned_file_hashes"]
                == with_cle["per_market"][COLUMBUS]["owned_file_hashes"])

    def test_adding_a_market_does_not_change_the_others_reconciliation(self):
        cbus = package(COLUMBUS, ["/pet-friendly-hotels/cbus-a/"],
                       confirmed=114, published=88, no_pets=14, unresolved=12)
        alone = assemble_market_packages([cbus])["per_market"][COLUMBUS]["reconciliation"]
        both = assemble_market_packages(
            [cbus, package(CLEVELAND, ["/cle/x/"])])["per_market"][COLUMBUS]["reconciliation"]
        assert alone == both
        assert both["confirmed_identities"] == 114 and both["unresolved"] == 12

    def test_corridor_unassigned_hotels_are_never_dropped_by_assembly(self):
        cbus = package(COLUMBUS, ["/pet-friendly-hotels/cbus-a/"],
                       unassigned=("Aloft Westerville", "Home2 New Albany"))
        out = assemble_market_packages([cbus, package(CLEVELAND, ["/cle/x/"])])
        assert out["per_market"][COLUMBUS]["corridor_unassigned_but_published"] == 2

    def test_a_route_collision_is_refused_not_resolved(self):
        a = package(COLUMBUS, ["/pet-friendly-hotels/shared/"])
        b = package(CLEVELAND, ["/pet-friendly-hotels/shared/"])
        with pytest.raises(MarketPackageError) as e:
            assemble_market_packages([a, b])
        assert "route collision" in str(e.value)

    def test_shared_corridor_names_are_fine_when_routes_differ(self):
        """Two markets may both have a 'Downtown' corridor. Only identical
        ROUTES are a collision."""
        a = package(COLUMBUS, ["/h/a/"], ["/downtown-columbus/"])
        b = package(CLEVELAND, ["/h/b/"], ["/cleveland-akron-canton/downtown/"])
        out = assemble_market_packages([a, b])
        assert out["total_owned_routes"] == 4

    def test_the_same_market_twice_is_refused(self):
        p = package(COLUMBUS, ["/h/a/"])
        with pytest.raises(MarketPackageError) as e:
            assemble_market_packages([p, p])
        assert "supplied twice" in str(e.value)

    def test_a_market_may_not_claim_a_global_route(self):
        p = package(COLUMBUS, ["/"], [])
        with pytest.raises(MarketPackageError) as e:
            assemble_market_packages([p], global_routes=["/", "/methodology/"])
        assert "globally-owned route" in str(e.value)

    def test_an_empty_assembly_is_refused(self):
        with pytest.raises(MarketPackageError):
            assemble_market_packages([])

    def test_assembly_is_deterministic(self):
        pkgs = [package(COLUMBUS, ["/h/a/"]), package(CLEVELAND, ["/h/b/"])]
        assert assemble_market_packages(pkgs) == assemble_market_packages(pkgs)


class TestPackageClaimsMustBeReal:

    def test_a_claimed_route_with_no_file_is_refused(self, tmp_path):
        """A package that claims a route it never produced would pass any hash
        comparison by having nothing to compare."""
        (tmp_path / "real").mkdir()
        (tmp_path / "real" / "index.html").write_text("<html></html>", encoding="utf-8")
        assert hash_owned_files(tmp_path, ["/real/"])
        with pytest.raises(MarketPackageError) as e:
            hash_owned_files(tmp_path, ["/ghost/"])
        assert "does not exist" in str(e.value)


class TestClevelandCompatibilityWithoutIntegration:
    """PHASE 9. Cleveland's real proposed authority is deliberately NOT
    integrated here. What must be provable now is only that the architecture
    can ACCEPT Cleveland-owned inventory without that inventory reaching a
    Columbus package -- so the check runs against the live Columbus inventory
    with one synthetic Cleveland row added."""

    def test_a_cleveland_row_added_to_live_inventory_never_enters_columbus(self):
        from scripts.pettripfinder.site_data import read_production_rows

        live = read_production_rows()
        baseline = owned_by(live, COLUMBUS)
        assert len(baseline) == 116

        contaminated = live + [hotel("Cleveland Beachwood Marriott", CLEVELAND,
                                     "Beachwood")]
        after = owned_by(contaminated, COLUMBUS)
        assert len(after) == 116
        assert [r["name"] for r in after] == [r["name"] for r in baseline]

    def test_that_same_row_is_selected_by_a_cleveland_package(self):
        from scripts.pettripfinder.site_data import read_production_rows

        live = read_production_rows()
        before = len(owned_by(live, CLEVELAND))
        contaminated = live + [
            hotel("Cleveland Beachwood Marriott", CLEVELAND, "Beachwood")]
        selected = owned_by(contaminated, CLEVELAND)
        assert len(selected) == before + 1
        assert "Cleveland Beachwood Marriott" in [r["name"] for r in selected]

    def test_live_inventory_now_carries_cleveland_rows(self):
        """Superseded by PTF-CLEVELAND-OVERNIGHT-AUTHORITY-001: Cleveland is
        integrated as a source package. What still matters is that its rows are
        owned and disjoint from Columbus's."""
        from scripts.pettripfinder.site_data import read_production_rows

        cle = owned_by(read_production_rows(), CLEVELAND)
        # 19 -> 21: the two Drury properties published by
        # PTF-CLEVELAND-POLICY-CAPTURE-INTEGRATION-003.
        assert len(cle) == 81  # after PTF-CLEVELAND-PASS3-FOUNDER-DECISIONS-001
        assert all(r[MARKET_ID_FIELD] == CLEVELAND for r in cle)
