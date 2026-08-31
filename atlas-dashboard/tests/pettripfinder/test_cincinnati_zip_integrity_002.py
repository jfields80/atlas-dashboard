"""PTF-CINCINNATI-HARDENED-SYNC-002 Phase 3 -- the two Florence ZIPs.

The defect
----------
Two Cincinnati identities on Meijer Drive in Florence, Boone County KY carried
postal codes that are not Florence and, in one case, are not a Kentucky postal
code at all::

    extended stay america florence meijer drive   40142   Hardin County KY
    laquinta inn and suites florence              41242   does not exist

Both arrived that way from ``visit_cincy`` and both were DIAGNOSED at discovery
time rather than corrected: ``cincinnati_candidate_ledger_001.json`` carries an
explicit ``postal_code_defect`` on each row, and PTF-CINCINNATI-URL-ROUTING-
RECOVERY-001C wrote "brand page states ZIP 41042 ... Not corrected here." into
both routes. That prose is still there, and these tests are why it can stay: it
is now the record of a defect that has been cleared.

Why it mattered
---------------
Cincinnati declares no ``census_membership_basis``, so it is a CORRIDOR_REGISTRY
market: a row belongs to the market when a corridor claims its postal code.
Neither 40142 nor 41242 is claimed by any Cincinnati corridor, so under
``market_membership.decide`` both rows returned OUT_OF_MARKET_BOUNDARY_DECISION
-- and one of them, Extended Stay America Florence Meijer Drive, is a LIVE
founder-signed published pet-friendly profile. A hardened recensus would have
evicted a published hotel on the strength of a typo.

Corroboration, already owned
----------------------------
Nothing was re-fetched to decide this. PTF-CINCINNATI-CAPTURE-PASS1-001
rendered the property's own page at extendedstayamerica.com and recorded
``identity_binding.postal_code = "41042"`` from it. The hotel's own website is
the authority for its own postal code, and it had already been captured.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder.discovery import market_membership as MM
from scripts.pettripfinder.discovery.census_projection import corridor_zips
from scripts.pettripfinder.markets import load_markets, market_by_id
from scripts.pettripfinder.markets.contract import MEMBERSHIP_CORRIDOR_REGISTRY

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_DIR = REPO_ROOT / "launch_packages" / "pettripfinder"
CENSUS = PACKAGE_DIR / "identity_census" / "cincinnati-oh.json"
ROUTING = (PACKAGE_DIR / "markets" / "authority" / "cincinnati-oh"
           / "identity_routing.json")
SEED = (PACKAGE_DIR / "markets" / "authority" / "cincinnati-oh"
        / "seed_businesses.csv")
PARTITION = PACKAGE_DIR / "cincinnati_final_partition_001.json"
CAPTURE = (PACKAGE_DIR / "markets" / "reports"
           / "cincinnati_capture_pass1_001_results.json")
#: A repaired identity's route can live in the shard or in any ledger that
#: removed it. Both of these identities are now published, so both routes have
#: left the shard -- which is the point of the seed-inventory rule, not a loss.
LEDGERS = [PACKAGE_DIR / "markets" / "reports" / name for name in (
    "cincinnati_route_retirement_002_ledger.json",
    "cincinnati_route_retirement_004_ledger.json",
    "cincinnati_route_retirement_004_seed_ledger.json")]

MARKET_ID = "cincinnati-oh"
FLORENCE = "41042"
CORRIDOR = "cincinnati-oh__erlanger-florence-airport"
ESA = "extended stay america florence meijer drive"

#: The two codes this work order corrected, keyed by the identity that carried
#: each one.
REPAIRED = {ESA: "40142", "laquinta inn and suites florence": "41242"}


def _load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def rows():
    return {h["identity_key"]: h for h in _load(CENSUS)["hotels"]}


@pytest.fixture(scope="module")
def zip_registry():
    return corridor_zips(market_by_id(load_markets(), MARKET_ID))


# ----------------------------------------------------------------- the repair

@pytest.mark.parametrize("identity_key", sorted(REPAIRED))
def test_the_census_now_states_the_florence_postal_code(rows, identity_key):
    assert rows[identity_key]["postal_code"] == FLORENCE


@pytest.mark.parametrize("identity_key", sorted(REPAIRED))
def test_the_routing_record_states_the_same_postal_code(identity_key):
    """Wherever the identity's route now lives, it agrees with the census.

    LaQuinta is still routed -- it is unresolved, and a route is how its policy
    page will be found. Extended Stay America is published, so PTF-CINCINNATI-
    HARDENED-SYNC-002 removed its route: a published identity's seed row is the
    source of truth for its URL, and a route beside it is a second copy. The
    removed record is preserved verbatim in the retirement ledger, and it had
    to carry the repair too -- a ledger that still said 40142 would be a
    corrected fact and its uncorrected archive disagreeing about one hotel.
    """
    records = {r["hotel_ref"]["identity_key"]: r for r in _load(ROUTING)["routes"]}
    for ledger in LEDGERS:
        for r in _load(ledger)["removed_routes"]:
            records.setdefault(r["hotel_ref"]["identity_key"], r)
    assert records[identity_key]["identity_context"]["postal_code"] == FLORENCE


@pytest.mark.parametrize("identity_key", sorted(REPAIRED))
def test_the_partition_states_the_same_postal_code(identity_key):
    items = {i["identity_key"]: i for i in _load(PARTITION)["items"]}
    assert items[identity_key]["postal_code"] == FLORENCE


def test_the_published_seed_row_states_the_same_postal_code():
    """The ESA property is published, so its seed row is inventory.

    A seed row that disagrees with the census is how a published profile ends
    up keyed to a postal code no corridor claims.
    """
    lines = [ln for ln in SEED.read_text(encoding="utf-8").splitlines()
             if ln.startswith("Extended Stay America Florence Meijer Drive,")]
    assert len(lines) == 1
    assert ",KY,%s," % FLORENCE in lines[0]


# ------------------------------------------------------ membership, the point

@pytest.mark.parametrize("identity_key", sorted(REPAIRED))
def test_the_identity_is_in_market_under_corridor_registry(rows, zip_registry,
                                                           identity_key):
    """The whole reason to repair a postal code in a CORRIDOR_REGISTRY market.

    ``coords_in_bounds`` is None because these rows state no coordinates --
    which under the hardened rule is silence, never contrary evidence.
    """
    outcome, why, corridor = MM.decide(
        rows[identity_key], basis=MEMBERSHIP_CORRIDOR_REGISTRY,
        corridor_of_zip=zip_registry, coords_in_bounds=None)
    assert outcome == MM.IN_MARKET, why
    assert corridor == CORRIDOR


@pytest.mark.parametrize("identity_key,bad", sorted(REPAIRED.items()))
def test_the_old_postal_code_would_have_evicted_the_identity(rows,
                                                             zip_registry,
                                                             identity_key,
                                                             bad):
    """The defect, reproduced -- so nobody has to take the claim on trust.

    One of these two rows is a published profile. Under the code the census is
    about to be re-run through, the typo alone was enough to put it outside the
    market it is published in.
    """
    before = dict(rows[identity_key], postal_code=bad)
    outcome, _why, corridor = MM.decide(
        before, basis=MEMBERSHIP_CORRIDOR_REGISTRY,
        corridor_of_zip=zip_registry, coords_in_bounds=None)
    assert outcome == MM.BOUNDARY_DECISION
    assert corridor == ""


@pytest.mark.parametrize("bad", sorted(set(REPAIRED.values())))
def test_no_corridor_claims_either_of_the_old_codes(zip_registry, bad):
    assert bad not in zip_registry
    assert zip_registry[FLORENCE] == CORRIDOR


# ----------------------------------------------------------- the corroboration

def test_the_property_own_page_is_what_states_41042():
    """No re-fetch decided this: the capture that published the hotel did.

    If this assertion ever fails, the repair has lost the only first-party
    evidence behind it and must be re-argued rather than re-asserted.
    """
    captured = {r["identity_key"]: r for r in _load(CAPTURE)["rows"]}
    esa = captured[ESA]
    assert esa["identity_binding"]["postal_code"] == FLORENCE
    assert esa["outcome"] == "PUBLICATION_CANDIDATE"


def test_the_diagnosis_prose_is_preserved_verbatim():
    """The routing notes still say the census carried the wrong ZIP.

    They are the evidence FOR this repair. A later reader who finds 41042
    everywhere and no record of why must not conclude nothing happened, and a
    tidy-up that rewrote the prose would erase exactly that.
    """
    text = ROUTING.read_text(encoding="utf-8") + "".join(
        p.read_text(encoding="utf-8") for p in LEDGERS)
    for bad in REPAIRED.values():
        assert bad in text, "the %s diagnosis was rewritten away" % bad
    assert '"postal_code": "40142"' not in text
    assert '"postal_code": "41242"' not in text


# -------------------------------------------------------- nothing else moved

def test_the_census_still_holds_every_identity(rows):
    """A blanket string replace over a market's authority is how an unrelated
    ZIP moves. This pins the blast radius at the two rows the founder named.
    """
    # 256 -> 257: PTF-CINCINNATI-MAINSTAY-CENSUS-SPLIT-013 replaced the conflated 'Comfort Suites Mainstay Hotel' with the two real Choice properties at 2347 Reading Road (oh720 Building A, oh721 Building B), so the census is 256 - 1 + 2 = 257.
    assert len(rows) == 257
    assert set(REPAIRED) <= {k for k, h in rows.items()
                             if h["postal_code"] == FLORENCE}


def test_every_lodging_identity_sits_in_a_claimed_postal_code(rows,
                                                              zip_registry):
    """After the repair one census row is unclaimed, and it is not lodging.

    ``first farm inn`` is a Petersburg KY farm stay already ruled
    OUT_OF_CURRENT_CATEGORY; the census's own geography note reports it as an
    unassigned row rather than as a failure.
    """
    unclaimed = sorted(k for k, h in rows.items()
                       if h["postal_code"][:5] not in zip_registry)
    assert unclaimed == ["first farm inn"]
    assert rows["first farm inn"]["lodging_state"] == "NOT_LODGING"
