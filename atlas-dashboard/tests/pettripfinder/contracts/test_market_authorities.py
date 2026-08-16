"""PTF-CENSUS-PARTITION-NORMALIZATION-001 -- the four markets, gated.

The point of Phase C is that the system now knows exactly which identities
exist and what state each one is in. These tests are what makes that claim
checkable rather than asserted.

The critical one is ``test_a_swap_is_caught_though_the_count_is_unchanged``.
Every count in this system used to be derived by subtraction -- unresolved =
confirmed - published - no_pets -- which is correct arithmetic for every WRONG
membership. Swap one identity for another and the totals do not move. Only a
set comparison sees it, and that test is the proof the gates catch what
subtraction cannot.
"""

from __future__ import annotations

import collections
import json
from pathlib import Path

import pytest

from scripts.pettripfinder.contracts import census, enums, partition
from scripts.pettripfinder.contracts.identity_key import (
    is_canonical_key, ptf_identity_key,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_DIR = REPO_ROOT / "launch_packages" / "pettripfinder"
CENSUS_DIR = PACKAGE_DIR / "identity_census"

COLUMBUS = "columbus-oh"
CLEVELAND = "cleveland-akron-canton-oh"
DAYTON = "dayton-oh"
CINCINNATI = "cincinnati-oh"

MARKETS = (COLUMBUS, CLEVELAND, DAYTON, CINCINNATI)

PARTITION_FILES = {
    COLUMBUS: "columbus_final_partition_001.json",
    CLEVELAND: "cleveland_final_partition_002.json",
    DAYTON: "dayton_final_partition_001.json",
    CINCINNATI: "cincinnati_final_partition_001.json",
}

#: What each market holds. Pinned so a change to an authority shows up here
#: rather than silently altering a number the rest of the program reasons about.
EXPECTED = {
    COLUMBUS: {"census": 112, "published": 88, "no_pets": 14,
               "out_of_category": 2, "unresolved": 8},
    # 21/8/159 until PTF-CLEVELAND-PASS2-FOUNDER-DECISIONS-001 applied the
    # founder's rulings on the attended-capture packet.
    CLEVELAND: {"census": 188, "published": 41, "no_pets": 31,
                "out_of_category": 0, "unresolved": 116},
    DAYTON: {"census": 129, "published": 47, "no_pets": 8,
             "out_of_category": 0, "unresolved": 74},
    # 121/0/0/0/121 until PTF-CINCINNATI-CENSUS-RECONCILIATION-001 rebuilt the
    # census from independent discovery. The six out-of-category rows are the
    # short-term rentals and guesthouses the directories list beside hotels.
    CINCINNATI: {"census": 256, "published": 0, "no_pets": 0,
                 "out_of_category": 6, "unresolved": 250},
}


def load(path):
    p = Path(path)
    if not p.is_file():
        pytest.skip("%s is not present in this worktree" % p.name)
    return json.loads(p.read_text(encoding="utf-8-sig"))


def census_doc(market_id):
    return load(CENSUS_DIR / ("%s.json" % market_id))


def partition_doc(market_id):
    return load(PACKAGE_DIR / PARTITION_FILES[market_id])


def routes():
    return load(PACKAGE_DIR / "identity_routing.json")["routes"]


def published_keys(policy_file):
    return {ptf_identity_key(h["name"])
            for h in load(PACKAGE_DIR / policy_file)["hotels"]}


POLICY_FILES = {
    COLUMBUS: "hotel_policy_facts.json",
    CLEVELAND: "hotel_policy_facts_cleveland-akron-canton-oh.json",
    DAYTON: "hotel_policy_facts_dayton-oh.json",
}


# --------------------------------------------------------------------------
# census
# --------------------------------------------------------------------------

class TestCensus:

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_schema_and_count(self, market_id):
        doc = census_doc(market_id)
        assert doc["schema"] == enums.CENSUS_SCHEMA
        assert doc["market_id"] == market_id
        assert doc["count"] == len(doc["hotels"]) == EXPECTED[market_id]["census"]

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_every_identity_key_is_canonical(self, market_id):
        for row in census_doc(market_id)["hotels"]:
            assert is_canonical_key(row["identity_key"]), row["canonical_name"]
            assert row["identity_key"] == ptf_identity_key(row["canonical_name"])

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_identities_are_unique(self, market_id):
        keys = [r["identity_key"] for r in census_doc(market_id)["hotels"]]
        assert len(keys) == len(set(keys))

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_ownership_is_explicit_on_every_row(self, market_id):
        """Defaulting an unowned row once made every Columbus exclusion count
        as Cleveland's."""
        for row in census_doc(market_id)["hotels"]:
            assert row["market_id"] == market_id, row["canonical_name"]

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_every_row_names_its_source(self, market_id):
        """A reconstructed universe has to be auditable row by row."""
        for row in census_doc(market_id)["hotels"]:
            assert row["provenance"], row["canonical_name"]

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_state_axes_are_closed_vocabularies(self, market_id):
        for row in census_doc(market_id)["hotels"]:
            assert row["identity_state"] in enums.IDENTITY_STATES
            assert row["lodging_state"] in enums.LODGING_STATES, row["canonical_name"]
            assert row["policy_state"] in enums.CENSUS_POLICY_STATES
            assert row["collision_state"] in enums.COLLISION_STATES

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_no_policy_fact_in_the_lodging_axis(self, market_id):
        """Whether a property takes pets says nothing about it being a hotel."""
        for row in census_doc(market_id)["hotels"]:
            assert row["lodging_state"] not in enums.LODGING_AXIS_VIOLATIONS, \
                row["canonical_name"]

    #: The one census row whose committed evidence does not state a city.
    #: SpringHill Suites Columbus Airport Gahanna is a routing-only identity
    #: whose record gives street, ZIP, phone and state but no city string.
    #: Deriving "Gahanna" from the hotel's NAME, or from a ZIP lookup, would be
    #: inference, and this contract does not infer facts a source did not
    #: state. The gap is pinned here so it stays visible instead of being
    #: quietly filled or quietly tolerated.
    KNOWN_CITY_GAP = "springhill suites columbus airport gahanna"

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_contract_validator_accepts_it(self, market_id):
        doc = census_doc(market_id)
        rows = doc["hotels"]
        blocking = []
        for issue in census.validate(doc):
            # Phase D owns corridor semantics. The assignment values and bases
            # these rows carry are preserved exactly as committed, and repairing
            # them here would hide what Phase D has to see.
            if issue.code == "BASIS_NOT_IMPLEMENTED":
                continue
            if issue.code == "MISSING_REQUIRED" and "assignment_value" in issue.path:
                continue
            if issue.code == "MISSING_REQUIRED" and issue.path.endswith(".city"):
                index = int(issue.path.split("[")[1].split("]")[0])
                if rows[index]["identity_key"] == self.KNOWN_CITY_GAP:
                    continue
            blocking.append(issue)
        assert blocking == [], [str(i) for i in blocking[:6]]

    def test_the_one_city_gap_is_exactly_the_documented_row(self):
        """No other identity may quietly acquire a blank city."""
        blank = [(m, r["identity_key"]) for m in MARKETS
                 for r in census_doc(m)["hotels"] if not r["city"]]
        assert blank == [(COLUMBUS, self.KNOWN_CITY_GAP)]

    def test_that_row_still_carries_the_locality_its_source_does_state(self):
        """The city is unknown; the ZIP and street are not, and are kept."""
        row = next(r for r in census_doc(COLUMBUS)["hotels"]
                   if r["identity_key"] == self.KNOWN_CITY_GAP)
        assert row["postal_code"] == "43230"
        assert row["address"] and row["state"] == "OH"


# --------------------------------------------------------------------------
# partition
# --------------------------------------------------------------------------

class TestPartition:

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_schema(self, market_id):
        doc = partition_doc(market_id)
        assert doc["schema"] == enums.PARTITION_SCHEMA
        assert doc["market_id"] == market_id

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_membership_is_exactly_the_census(self, market_id):
        keys = census.identity_keys(census_doc(market_id))
        rec = partition.reconcile(keys, partition_doc(market_id),
                                  market_id=market_id)
        assert rec.missing_from_partition == ()
        assert rec.missing_from_census == ()
        assert rec.duplicated_in_partition == ()
        assert rec.census_count == rec.partition_count
        assert rec.agrees

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_counts_come_from_the_partition(self, market_id):
        keys = census.identity_keys(census_doc(market_id))
        rec = partition.reconcile(keys, partition_doc(market_id),
                                  market_id=market_id)
        want = EXPECTED[market_id]
        assert rec.published == want["published"]
        assert rec.verified_no_pets == want["no_pets"]
        assert rec.out_of_category == want["out_of_category"]
        assert rec.unresolved == want["unresolved"]
        # Derived by counting rows, never by subtracting one bucket from another.
        assert rec.resolved + rec.unresolved == want["census"]

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_contract_validator_accepts_it(self, market_id):
        issues = partition.validate(partition_doc(market_id))
        assert issues == (), [str(i) for i in issues[:6]]

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_every_state_is_canonical(self, market_id):
        for item in partition_doc(market_id)["items"]:
            assert item["final_state"] in enums.PARTITION_STATES


class TestNextActionInvariant:

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_every_unresolved_row_has_exactly_one_operational_action(self, market_id):
        forbidden = ("tbd", "unknown", "review later", "n/a", "")
        for item in partition_doc(market_id)["items"]:
            if item["final_state"] in enums.TERMINAL_STATES:
                continue
            action = item["next_action"].strip()
            assert action.lower() not in forbidden, item["canonical_name"]
            assert len(action) > 20, item["canonical_name"]
            assert item["next_action_source"], item["canonical_name"]
            assert item["determined_by"], item["canonical_name"]

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_terminal_rows_carry_nothing_outstanding(self, market_id):
        """A published hotel with work still to do is a contradiction."""
        for item in partition_doc(market_id)["items"]:
            if item["final_state"] not in enums.TERMINAL_STATES:
                continue
            assert item["next_action"] == "", item["canonical_name"]
            assert item["resolved"] is True, item["canonical_name"]


class TestTerminalDispositionsMatchAuthority:

    @pytest.mark.parametrize("market_id", (COLUMBUS, CLEVELAND, DAYTON))
    def test_published_set_matches_the_policy_package(self, market_id):
        published = published_keys(POLICY_FILES[market_id])
        in_partition = {i["identity_key"] for i in partition_doc(market_id)["items"]
                        if i["final_state"] == enums.PUBLISHED_PET_FRIENDLY}
        assert in_partition == published

    @pytest.mark.parametrize("market_id", (COLUMBUS, CLEVELAND, DAYTON))
    def test_terminal_sets_match_the_exclusion_registry(self, market_id):
        exclusions = load(PACKAGE_DIR / "hotel_exclusions.json")["exclusions"]
        for state in (enums.VERIFIED_NO_PETS, enums.OUT_OF_CURRENT_CATEGORY):
            expected = {ptf_identity_key(e["canonical_name"]) for e in exclusions
                        if e["market_id"] == market_id
                        and e["exclusion_state"] == state}
            found = {i["identity_key"] for i in partition_doc(market_id)["items"]
                     if i["final_state"] == state}
            assert found == expected, "%s / %s" % (market_id, state)

    def test_category_exits_are_never_counted_as_no_pets(self):
        """Counting them together would overstate negative evidence by two.

        A bed-and-breakfast we do not cover has said nothing about pets.
        """
        keys = census.identity_keys(census_doc(COLUMBUS))
        rec = partition.reconcile(keys, partition_doc(COLUMBUS), market_id=COLUMBUS)
        assert rec.verified_no_pets == 14
        assert rec.out_of_category == 2
        assert rec.verified_no_pets + rec.out_of_category == 16

    def test_cincinnati_publishes_nothing_and_refuses_nothing(self):
        """Silence is not a refusal, and no evidence is not a publication.

        Out-of-category IS a terminal state and Cincinnati now carries six of
        them -- guesthouses and short-term rentals its directories list beside
        hotels. That is a category ruling, not a pet-policy finding, so the two
        states this test actually guards are the other two.
        """
        doc = partition_doc(CINCINNATI)
        states = collections.Counter(i["final_state"] for i in doc["items"])
        assert states[enums.PUBLISHED_PET_FRIENDLY] == 0
        assert states[enums.VERIFIED_NO_PETS] == 0
        assert states[enums.OUT_OF_CURRENT_CATEGORY] == 6
        assert len(doc["items"]) == 256


# --------------------------------------------------------------------------
# the test subtraction cannot pass
# --------------------------------------------------------------------------

class TestMembershipCatchesWhatSubtractionCannot:

    def base(self):
        keys = census.identity_keys(census_doc(DAYTON))
        return keys, partition_doc(DAYTON)

    def test_a_swap_is_caught_though_the_count_is_unchanged(self):
        """One identity in, one out. Every total matches. Membership is wrong.

        This is the whole reason the contract compares sets: the arithmetic
        that used to derive `unresolved` would report this as healthy.
        """
        keys, doc = self.base()
        tampered = json.loads(json.dumps(doc))
        tampered["items"][0]["identity_key"] = "a hotel that does not exist"
        tampered["items"][0]["canonical_name"] = "A Hotel That Does Not Exist"
        rec = partition.reconcile(keys, tampered, market_id=DAYTON)
        assert rec.census_count == rec.partition_count      # totals agree
        assert not rec.agrees                               # membership does not
        assert len(rec.missing_from_partition) == 1
        assert rec.missing_from_census == ("a hotel that does not exist",)

    def test_a_missing_row_is_caught(self):
        keys, doc = self.base()
        tampered = json.loads(json.dumps(doc))
        tampered["items"].pop()
        rec = partition.reconcile(keys, tampered, market_id=DAYTON)
        assert not rec.agrees and len(rec.missing_from_partition) == 1

    def test_a_duplicate_row_is_caught(self):
        keys, doc = self.base()
        tampered = json.loads(json.dumps(doc))
        tampered["items"].append(json.loads(json.dumps(tampered["items"][0])))
        rec = partition.reconcile(keys, tampered, market_id=DAYTON)
        assert not rec.agrees and len(rec.duplicated_in_partition) == 1

    def test_a_foreign_market_identity_is_caught(self):
        keys, doc = self.base()
        foreign = sorted(census.identity_keys(census_doc(CLEVELAND)) - keys)[0]
        tampered = json.loads(json.dumps(doc))
        tampered["items"][0]["identity_key"] = foreign
        rec = partition.reconcile(keys, tampered, market_id=DAYTON)
        assert not rec.agrees
        assert foreign in rec.missing_from_census


# --------------------------------------------------------------------------
# routing
# --------------------------------------------------------------------------

class TestRoutingSubsetOfCensus:

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_no_active_accommodation_route_outside_the_census(self, market_id):
        keys = census.identity_keys(census_doc(market_id))
        violations = partition.routing_subset_violations(
            routes(), keys, market_id=market_id)
        assert violations == (), [str(v) for v in violations]

    def test_every_route_carries_a_canonical_identity_key(self):
        for route in routes():
            ref = route["hotel_ref"]
            assert is_canonical_key(ref["identity_key"]), ref["canonical_name"]
            assert ref["identity_key"] == ptf_identity_key(ref["canonical_name"])

    def test_every_route_declares_its_category(self):
        for route in routes():
            assert route["category"] in enums.ROUTING_CATEGORIES

    def test_the_two_cleveland_orphans_are_retired_not_deleted(self):
        """History survives: the URL and its binding evidence stay on record."""
        retired = {r["hotel_ref"]["identity_key"]: r for r in routes()
                   if r["status"] == enums.ROUTING_RETIRED}
        assert set(retired) == {"eastland inn restaurant", "the welshfield inn"}
        for route in retired.values():
            assert route["retired_at"] and route["retired_reason"]
            assert route["official_property_url"]
            assert route["binding_sources"]

    def test_the_census_was_not_expanded_to_house_them(self):
        """Fixing membership by admitting non-hotels would defeat the rule."""
        assert census_doc(CLEVELAND)["count"] == 188
        keys = census.identity_keys(census_doc(CLEVELAND))
        assert "eastland inn restaurant" not in keys
        assert "the welshfield inn" not in keys

    def test_no_published_identity_holds_an_active_route(self):
        """Two writers of the same fact eventually disagree."""
        for market_id, policy_file in POLICY_FILES.items():
            published = published_keys(policy_file)
            active = {r["hotel_ref"]["identity_key"] for r in routes()
                      if r["market_id"] == market_id
                      and r["status"] != enums.ROUTING_RETIRED}
            assert active & published == set(), market_id

    def test_no_two_active_routes_share_a_url(self):
        seen = {}
        for route in routes():
            if route["status"] == enums.ROUTING_RETIRED:
                continue
            url = route["official_property_url"]
            assert url not in seen, "%s and %s share %s" % (
                seen.get(url), route["hotel_ref"]["canonical_name"], url)
            seen[url] = route["hotel_ref"]["canonical_name"]


class TestCanonicalKeyResolvesTheFormattingSplit:
    """The defect that made membership unevaluable."""

    def test_dayton_has_no_phantom_orphans(self):
        """"I-70" vs "I 70" and "&" vs "and" were two normalisers, not two hotels."""
        keys = census.identity_keys(census_doc(DAYTON))
        for name in ("Comfort Suites Springfield I-70",
                     "Holiday Inn Express & Suites Greenville"):
            assert ptf_identity_key(name) in keys, name
        assert partition.routing_subset_violations(
            routes(), keys, market_id=DAYTON) == ()

    def test_cleveland_orphans_were_genuine_and_are_not_normalised_away(self):
        """A canonical key must not manufacture a match that does not exist."""
        keys = census.identity_keys(census_doc(CLEVELAND))
        for name in ("Eastland Inn Restaurant", "The Welshfield Inn"):
            assert ptf_identity_key(name) not in keys, name


# --------------------------------------------------------------------------
# collisions
# --------------------------------------------------------------------------

class TestIdentityCollisions:

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_no_duplicate_canonical_key(self, market_id):
        keys = [r["identity_key"] for r in census_doc(market_id)["hotels"]]
        assert len(keys) == len(set(keys))

    @pytest.mark.parametrize("market_id", MARKETS)
    def test_shared_address_is_reported_not_merged(self, market_id):
        """Not every shared address is a duplicate.

        A hotel and a taproom can share a campus, and the repository already
        records one such resolution explicitly. Two independently discovered
        identities are not merged because a string matches.
        """
        by_address = {}
        for row in census_doc(market_id)["hotels"]:
            addr = (row["address"] or "").strip().lower()
            if not addr:
                continue
            by_address.setdefault(addr, []).append(row)
        for addr, rows in by_address.items():
            if len(rows) > 1:
                # Both survive as distinct identities; that is the contract.
                assert len({r["identity_key"] for r in rows}) == len(rows), addr
