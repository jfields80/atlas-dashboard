"""PTF-GRAND-RAPIDS-HOLLAND-CHOICE-ROUTING-REPAIR-007 -- distinct properties may
not inherit one property URL.

Seven distinct Choice-brand identities in Grand Rapids-Holland -- a Comfort Inn
in Grandville, a Comfort Inn on 28th Street, a Comfort Suites on Caterpillar
Court, a Comfort Suites in Comstock Park, an Econo Lodge on Kraft Avenue, a
Rodeway Inn on Fairlanes Avenue and a Sleep Inn on 29th Street, at seven
addresses with seven telephone numbers -- all carried one URL::

    choicehotels.com/michigan/walker/quality-inn-hotels

which is a brand index for a Quality Inn none of them is. OpenStreetMap's
``website`` tag is hand-typed and bulk-edited, and nine candidates carried it.

Two separate defences are pinned here, because the collision had two halves and
only one of them was ever caught:

1. Routing already refused the brand index (ROUTE_NEEDS_PROPERTY_URL), so no
   paid lane was ever sent there. That guard must not regress.
2. Zero-cost URL recovery then tried to repair those rows from prior evidence,
   and bound "Comfort Inn" to a prior "Comfort Suites Grandville" sighting on a
   SHARED TELEPHONE. ``url_names_the_property`` passed it, because "comfort"
   really does appear in ``comfort-suites-hotels``. Sibling sub-brands share
   their distinctive word, so reading the URL is not enough: the sighting's own
   NAME has to be read too.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.pettripfinder.acquisition import market_routing as MR
from scripts.pettripfinder.discovery import census_projection as CP
from scripts.pettripfinder.discovery import census_url_recovery as UR

REPO_ROOT = Path(__file__).resolve().parents[3]
CENSUS = REPO_ROOT / "launch_packages" / "pettripfinder" / "identity_census"

BRAND_INDEX_URL = "https://www.choicehotels.com/michigan/walker/quality-inn-hotels"


def _candidate(cid, name, url=BRAND_INDEX_URL):
    return {
        "candidate_id": cid, "name": name, "website_url": url,
        "website_state": "OFFICIAL_WEBSITE_PRESENT",
    }


class TestABrandIndexIsNobodysOfficialUrl:

    def test_a_brand_index_claimed_by_many_candidates_is_dropped(self):
        candidates = [_candidate("a", "Comfort Inn"),
                      _candidate("b", "Sleep Inn & Suites"),
                      _candidate("c", "Econo Lodge & Suites")]
        shared = CP.shared_brand_index_urls(candidates)
        assert shared == {BRAND_INDEX_URL: 3}

    def test_a_brand_index_claimed_by_one_candidate_is_left_alone(self):
        """Honest about that row, and routing already says what it is worth."""
        assert CP.shared_brand_index_urls([_candidate("a", "Comfort Inn")]) == {}

    def test_a_shared_PROPERTY_page_is_not_swept_up(self):
        """This guard is about brand indexes. Two identities on one property
        page are a duplicate question, answered by the dedup gate, not here."""
        url = "https://www.hilton.com/en/hotels/GRRDTDT-canopy/"
        candidates = [_candidate("a", "Canopy", url), _candidate("b", "Canopy GR", url)]
        assert CP.shared_brand_index_urls(candidates) == {}

    def test_routing_still_refuses_a_brand_index(self):
        """The guard that meant no money was ever at risk."""
        assert MR.classify_url_shape(BRAND_INDEX_URL) == MR.BRAND_INDEX


class TestRecoveryMayNotLendAUrlAcrossSubBrands:
    """The defect that actually produced a wrong URL."""

    def test_a_comfort_inn_may_not_take_a_comfort_suites_url(self):
        ok, why = UR.names_may_share_a_url(
            "Comfort Inn", "Comfort Suites Grandville Grand Rapids SW")
        assert ok is False
        assert "two properties" in why

    def test_the_url_text_check_alone_would_have_accepted_it(self):
        """Why the name check had to be added: the URL really does say
        "comfort", so reading the URL can never separate these two."""
        named, _ = UR.url_names_the_property(
            "Comfort Inn",
            "https://www.choicehotels.com/en-ca/michigan/grandville/"
            "comfort-suites-hotels/mi169")
        assert named is True

    def test_a_rodeway_inn_may_take_its_own_qualified_sighting(self):
        """The guard must not refuse a correct binding: one name contains the
        other, same brand, same city."""
        ok, _ = UR.names_may_share_a_url(
            "Rodeway Inn", "Rodeway Inn Grandville Grand Rapids")
        assert ok is True

    def test_an_identical_name_may_share(self):
        assert UR.names_may_share_a_url("Comfort Inn", "Comfort Inn")[0] is True

    def test_a_sighting_with_no_name_is_not_judged_here(self):
        """Absence of a name is not evidence of a conflict; the URL check still
        has to pass."""
        assert UR.names_may_share_a_url("Comfort Inn", "")[0] is True

    def test_an_unrelated_brand_may_not_lend_its_url(self):
        ok, _ = UR.names_may_share_a_url(
            "Sleep Inn & Suites", "Spark by Hilton Grand Rapids")
        assert ok is False


class TestGrandRapidsFixture:
    """The real proposed census, after the repair."""

    SEVEN = ("comfort inn", "comfort inn airport", "comfort suites",
             "comfort suites grand rapids north", "econo lodge and suites",
             "rodeway inn", "sleep inn and suites")

    def _rows(self):
        path = CENSUS / "recensus" / "grand-rapids-holland-mi.json"
        if not path.is_file():
            return None
        return {r["identity_key"]: r
                for r in json.loads(path.read_text(encoding="utf-8"))["hotels"]}

    def test_no_two_identities_share_the_brand_index_url(self):
        rows = self._rows()
        if rows is None:
            return
        holders = [k for k, r in rows.items()
                   if (r.get("official_url") or "").rstrip("/").lower()
                   == BRAND_INDEX_URL.rstrip("/").lower()]
        assert holders == [], holders

    def test_no_two_of_the_seven_share_any_official_url(self):
        rows = self._rows()
        if rows is None:
            return
        seen = {}
        for key in self.SEVEN:
            row = rows.get(key)
            if not row:
                continue
            url = (row.get("official_url") or "").rstrip("/").lower()
            if url:
                assert url not in seen, (
                    "%s and %s share %s" % (key, seen[url], url))
                seen[url] = key
