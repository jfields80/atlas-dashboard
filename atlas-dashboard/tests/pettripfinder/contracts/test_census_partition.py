"""PTF-CONTRACT-FOUNDATION-001 -- census, partition and the routing invariant.

The rule these tests exist to defend: membership is COMPARED, never inferred by
subtraction. ``unresolved = confirmed - published - no_pets`` is correct
arithmetic for every wrong membership -- swap a published identity for one
absent from the census and the total does not move.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder.contracts import census, enums, partition

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_DIR = REPO_ROOT / "launch_packages" / "pettripfinder"


def codes(issues):
    return {i.code for i in issues}


def row(**kw):
    base = {"identity_key": "hampton inn dayton", "canonical_name": "Hampton Inn Dayton",
            "slug": "hampton-inn-dayton", "market_id": "dayton-oh", "city": "Dayton",
            "state": "OH", "postal_code": "45402",
            "identity_state": enums.IDENTITY_CONFIRMED,
            "lodging_state": enums.LODGING_CONFIRMED,
            "policy_state": enums.POLICY_NOT_VERIFIED}
    base.update(kw)
    return base


def document(rows, **kw):
    base = {"schema": enums.CENSUS_SCHEMA, "market_id": "dayton-oh",
            "count": len(rows), "hotels": rows}
    base.update(kw)
    return base


class TestCensus:

    def test_clean_row_validates(self):
        assert census.validate(document([row()])) == ()

    def test_declared_count_must_match_rows(self):
        """The cheapest signal that a document was edited in two places."""
        assert "COUNT_MISMATCH" in codes(census.validate(document([row()], count=2)))

    def test_identity_key_must_be_canonical(self):
        issues = census.validate(document([row(
            identity_key="Hampton Inn Dayton")]))
        assert "NOT_CANONICAL" in codes(issues)

    def test_identity_key_must_derive_from_the_name(self):
        """The check that catches a mangled but well-formed key.

        "le m ridien columbus the joseph" looks canonical and is not what the
        name produces -- only comparing against the name can see that.
        """
        issues = census.validate(document([row(
            identity_key="le m ridien columbus the joseph",
            canonical_name="Le Méridien Columbus, The Joseph")]))
        assert "KEY_NAME_MISMATCH" in codes(issues)

    def test_ownership_is_explicit(self):
        """Defaulting an unowned row once made every Columbus exclusion
        count as Cleveland's."""
        issues = census.validate(document([row(market_id="columbus-oh")]))
        assert "WRONG_MARKET" in codes(issues)

    def test_duplicate_identity_rejected(self):
        assert "DUPLICATE_IDENTITY" in codes(census.validate(document([row(), row()])))

    def test_state_must_be_in_the_market(self):
        """Sixteen Kentucky properties must not publish as Ohio."""
        issues = census.validate(document([row(state="KY")]), market_states=["OH"])
        assert "STATE_NOT_IN_MARKET" in codes(issues)

    def test_multi_state_market_accepts_its_states(self):
        issues = census.validate(document([row(state="KY")]),
                                 market_states=["OH", "KY", "IN"])
        assert "STATE_NOT_IN_MARKET" not in codes(issues)

    def test_assignment_basis_needs_the_value_that_fired(self):
        """121 Cincinnati rows claim postal_code; seven have no such ZIP."""
        issues = census.validate(document([row(
            assignment_basis=enums.BASIS_POSTAL_CODE, assignment_value="")]))
        assert "MISSING_REQUIRED" in codes(issues)

    def test_legacy_schema_name_is_read(self):
        issues = census.validate(document([row()], schema="ptf-identity-census/1.0"))
        assert "BAD_SCHEMA" not in codes(issues)

    def test_legacy_city_name_basis_translates(self):
        """"city_name" is the state-blind ancestor of "city_state"."""
        issues = census.validate(document([row(
            assignment_basis="city_name", assignment_value="Dayton")]))
        assert not codes(issues) & {"BAD_ENUM", "BASIS_NOT_IMPLEMENTED"}

    def test_unimplemented_basis_is_its_own_defect(self):
        """A basis the assigner has no tier for can never be reproduced.

        ``assignment.py`` implements explicit, city and ZIP. Eleven committed
        Dayton rows claim ``county_name``, so no run of the assigner will ever
        agree with them -- the reproducibility gate cannot pass while they
        stand.
        """
        issues = census.validate(document([row(
            assignment_basis="county_name", assignment_value="Darke")]))
        assert "BASIS_NOT_IMPLEMENTED" in codes(issues)

    def test_policy_fact_in_the_lodging_axis_is_its_own_defect(self):
        """Whether a property takes pets says nothing about it being a hotel."""
        issues = census.validate(document([row(lodging_state="LODGING_NO_PETS")]))
        assert "AXIS_VIOLATION" in codes(issues)

    def test_committed_no_pets_policy_spelling_is_accepted(self):
        """The census, exclusion registry and partition all say VERIFIED_NO_PETS.

        A fourth name for one concept is the divergence this freeze ends, so
        the committed spelling wins over a newly invented one.
        """
        issues = census.validate(document([row(
            policy_state=enums.VERIFIED_NO_PETS)]))
        assert "BAD_ENUM" not in codes(issues)


def item(**kw):
    base = {"identity_key": "hampton inn dayton", "canonical_name": "Hampton Inn Dayton",
            "final_state": enums.AWAITING_POLICY_ARTIFACT, "resolved": False,
            "next_action": "Capture the property's pet-policy surface.",
            "next_action_source": "dayton_work_browser_pass_001",
            "determined_by": "ptf_contract_foundation_001"}
    base.update(kw)
    return base


def partition_doc(items, **kw):
    base = {"schema": enums.PARTITION_SCHEMA, "market_id": "dayton-oh",
            "items": items}
    base.update(kw)
    return base


class TestPartition:

    def test_clean_blocker_row_validates(self):
        assert partition.validate(partition_doc([item()])) == ()

    def test_terminal_row_may_not_carry_a_next_action(self):
        """A published hotel with outstanding work is a contradiction."""
        issues = partition.validate(partition_doc([item(
            final_state=enums.PUBLISHED_PET_FRIENDLY, resolved=True,
            next_action="Capture something")]))
        assert "TERMINAL_WITH_ACTION" in codes(issues)

    def test_terminal_row_must_be_resolved(self):
        issues = partition.validate(partition_doc([item(
            final_state=enums.PUBLISHED_PET_FRIENDLY, resolved=False,
            next_action="")]))
        assert "TERMINAL_NOT_RESOLVED" in codes(issues)

    def test_blocker_row_needs_exactly_one_next_action(self):
        issues = partition.validate(partition_doc([item(next_action="")]))
        assert "MISSING_REQUIRED" in codes(issues)

    def test_blocker_row_needs_its_provenance(self):
        issues = partition.validate(partition_doc([item(determined_by="")]))
        assert "MISSING_REQUIRED" in codes(issues)

    def test_blocker_may_not_claim_resolved(self):
        issues = partition.validate(partition_doc([item(resolved=True)]))
        assert "BLOCKER_MARKED_RESOLVED" in codes(issues)

    def test_out_of_category_is_terminal(self):
        assert partition.validate(partition_doc([item(
            final_state=enums.OUT_OF_CURRENT_CATEGORY, resolved=True,
            next_action="")])) == ()

    def test_every_state_has_a_written_meaning(self):
        """Four markets must not drift into four definitions of one state."""
        for state in enums.PARTITION_STATES:
            assert partition.STATE_MEANINGS.get(state), state

    @pytest.mark.parametrize("legacy,expected", [
        ("ADR_ACCESS_BLOCKED", enums.ACCESS_BLOCKED),
        ("ANTI_BOT_CHALLENGE", enums.ACCESS_BLOCKED),
        ("NO_OFFICIAL_URL", enums.AWAITING_OFFICIAL_URL),
        ("AFFIRMATIVE_POLICY_TRANSCRIBED_NO_ARTIFACT", enums.AWAITING_POLICY_ARTIFACT),
        ("POLICY_MODAL_BLANK", enums.AWAITING_ATTENDED_CAPTURE),
    ])
    def test_legacy_aliases_fold(self, legacy, expected):
        assert partition.normalise_blocker(legacy) == expected

    def test_canonical_state_is_unchanged(self):
        assert partition.normalise_blocker(enums.ACCESS_BLOCKED) == enums.ACCESS_BLOCKED


class TestReconciliationBySet:

    def test_agreement(self):
        keys = {"hampton inn dayton"}
        rec = partition.reconcile(keys, partition_doc([item()]))
        assert rec.agrees
        assert rec.unresolved == 1 and rec.resolved == 0

    def test_missing_from_partition_is_caught(self):
        keys = {"hampton inn dayton", "drury inn and suites dayton"}
        rec = partition.reconcile(keys, partition_doc([item()]))
        assert not rec.agrees
        assert rec.missing_from_partition == ("drury inn and suites dayton",)

    def test_swap_is_caught_though_the_count_is_unchanged(self):
        """The case subtraction cannot see.

        One identity in, one identity out: the totals match perfectly and the
        membership is wrong. Only a set comparison catches it.
        """
        keys = {"hampton inn dayton"}
        rec = partition.reconcile(keys, partition_doc([item(
            identity_key="drury inn and suites dayton",
            canonical_name="Drury Inn & Suites Dayton")]))
        assert rec.census_count == rec.partition_count == 1
        assert not rec.agrees
        assert rec.missing_from_partition == ("hampton inn dayton",)
        assert rec.missing_from_census == ("drury inn and suites dayton",)

    def test_duplicate_row_is_caught(self):
        rec = partition.reconcile({"hampton inn dayton"},
                                  partition_doc([item(), item()]))
        assert rec.duplicated_in_partition == ("hampton inn dayton",)

    def test_counts_are_derived_from_the_partition(self):
        rows = [item(final_state=enums.PUBLISHED_PET_FRIENDLY, resolved=True,
                     next_action=""),
                item(identity_key="drury inn and suites dayton",
                     final_state=enums.VERIFIED_NO_PETS, resolved=True,
                     next_action=""),
                item(identity_key="quality inn greenville")]
        rec = partition.reconcile(
            {"hampton inn dayton", "drury inn and suites dayton",
             "quality inn greenville"}, partition_doc(rows))
        assert (rec.published, rec.verified_no_pets, rec.resolved,
                rec.unresolved) == (1, 1, 2, 1)


class TestRoutingSubsetOfCensus:

    def route(self, name, market_id="dayton-oh", **kw):
        base = {"routing_id": "route-%s" % name, "market_id": market_id,
                "hotel_ref": {"canonical_name": name},
                "status": enums.ROUTING_CONFIRMED}
        base.update(kw)
        return base

    def test_route_inside_census_is_clean(self):
        assert partition.routing_subset_violations(
            [self.route("Hampton Inn Dayton")], {"hampton inn dayton"},
            market_id="dayton-oh") == ()

    def test_orphan_route_is_reported(self):
        issues = partition.routing_subset_violations(
            [self.route("Eastland Inn Restaurant")], {"hampton inn dayton"},
            market_id="dayton-oh")
        assert "ROUTE_NOT_IN_CENSUS" in codes(issues)

    def test_other_markets_are_not_this_markets_problem(self):
        assert partition.routing_subset_violations(
            [self.route("Some Columbus Hotel", market_id="columbus-oh")],
            {"hampton inn dayton"}, market_id="dayton-oh") == ()

    def test_retired_route_is_exempt(self):
        """Retirement is how an orphan is resolved, not deletion."""
        assert partition.routing_subset_violations(
            [self.route("Eastland Inn Restaurant", status=enums.ROUTING_RETIRED)],
            {"hampton inn dayton"}, market_id="dayton-oh") == ()

    def test_ampersand_and_hyphen_no_longer_produce_phantoms(self):
        """The divergence that made Dayton report two orphans it does not have."""
        census_keys = {"holiday inn express and suites greenville",
                       "comfort suites springfield i 70"}
        routes = [self.route("Holiday Inn Express & Suites Greenville"),
                  self.route("Comfort Suites Springfield I-70")]
        assert partition.routing_subset_violations(
            routes, census_keys, market_id="dayton-oh") == ()


class TestCommittedAuthority:
    """The invariant, measured on what is actually committed."""

    def _census_keys(self, market_id):
        path = PACKAGE_DIR / "identity_census" / ("%s.json" % market_id)
        if not path.is_file():
            pytest.skip("%s census is not committed" % market_id)
        return census.identity_keys(
            json.loads(path.read_text(encoding="utf-8-sig")))

    def _routes(self):
        path = PACKAGE_DIR / "identity_routing.json"
        if not path.is_file():
            pytest.skip("identity_routing.json is not present")
        return json.loads(path.read_text(encoding="utf-8-sig"))["routes"]

    def test_dayton_satisfies_the_invariant(self):
        violations = partition.routing_subset_violations(
            self._routes(), self._census_keys("dayton-oh"), market_id="dayton-oh")
        assert violations == ()

    def test_cleveland_violations_are_now_repaired(self):
        """Phase A pinned two; PTF-CENSUS-PARTITION-NORMALIZATION-001 fixed them.

        A restaurant and a cross-category inn held accommodation routes to
        identities Cleveland's hotel census does not contain. They were
        resolved by RETIRING the routes -- not by admitting two non-hotels to a
        hotel census, which would have made the membership rule defeat its own
        purpose.
        """
        violations = partition.routing_subset_violations(
            self._routes(), self._census_keys("cleveland-akron-canton-oh"),
            market_id="cleveland-akron-canton-oh")
        assert violations == ()

        retired = {r["hotel_ref"]["canonical_name"] for r in self._routes()
                   if r["status"] == enums.ROUTING_RETIRED}
        # PTF-CINCINNATI-PASS1-AUTHORITY-APPLICATION-001 retired 26 more --
        # Cincinnati's own founder-decided identities, now seed inventory or
        # a verified-no-pets exclusion instead of a live route.
        # PTF-CINCINNATI-21C-FOUNDER-DECISION-APPLICATION-001 retired the
        # 27th (21c Museum Hotel Cincinnati) once it was published.
        assert retired == {
            "Eastland Inn Restaurant", "The Welshfield Inn",
            "21c Museum Hotel Cincinnati",
            "BEST WESTERN PLUS Hannaford Inn & Suites",
            "Baymont by Wyndham Lawrenceburg", "Baymont by Wyndham Monroe",
            "Best Western Clermont", "Best Western Inn Florence",
            "Best Western Plus Whitewater Inn",
            "Best Western Premier Mariemont Inn", "Butler Inn",
            "Days Inn & Suites by Wyndham Cincinnati North",
            "Days Inn Batavia", "Days Inn Cincinnati East",
            "DoubleTree by Hilton Lawrenceburg",
            "Doubletree by Hilton Cincinnati Airport",
            "Extended Stay America Florence Meijer Drive",
            "Extended Stay America Florence Turfway Road",
            "Extended Stay America Suites - Cincinnati - Covington",
            "HomeTowne Studios Florence Cincinnati Airport",
            "Motel 6 Florence - Commerce Dr.", "Motel 6 Sharonville",
            "Motel 6 Walton/Richwood",
            "Red Roof Inn Cincinnati East - Eastgate",
            "Red Roof Inn Cincinnati North - Mason", "Red Roof Inn Greendale",
            "Red Roof Inn Richwood",
            "Sonesta ES Suites Cincinnati-Sharonville East",
            "Sonesta ES Suites Cincinnati-Sharonville West"}
        # The census was NOT expanded to 190 to house them.
        assert len(self._census_keys("cleveland-akron-canton-oh")) == 188

    def test_dayton_census_geography_defects_are_pinned(self):
        """Eleven unreproducible corridor claims and eight axis violations.

        A larger instance of the same defect the Cincinnati audit found: a
        stored basis that the assignment code cannot produce. Pinned so Phase D
        notices when it is fixed.
        """
        path = PACKAGE_DIR / "identity_census" / "dayton-oh.json"
        if not path.is_file():
            pytest.skip("Dayton census is not committed")
        issues = census.validate(json.loads(path.read_text(encoding="utf-8-sig")))
        # PTF-GEOGRAPHY-NORMALIZATION-001 resolved all eleven. Every one was
        # already reproducible by its ZIP -- Celina 45822, Eaton 45320, New
        # Paris 45347, Cedarville 45314, Yellow Springs 45387 -- so only the
        # LABEL was impossible, and no county tier had to be invented to keep a
        # placement that the postal registry already supported.
        assert sum(1 for i in issues if i.code == "BASIS_NOT_IMPLEMENTED") == 0
        # The eight axis violations do NOT survive. Phase C moved the no-pets
        # fact out of the lodging axis, where it never belonged.
        assert sum(1 for i in issues if i.code == "AXIS_VIOLATION") == 0

    def test_cleveland_partition_covers_its_census(self):
        path = PACKAGE_DIR / "cleveland_final_partition_002.json"
        if not path.is_file():
            pytest.skip("Cleveland partition is not committed")
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
        rec = partition.reconcile(self._census_keys("cleveland-akron-canton-oh"),
                                  doc, market_id="cleveland-akron-canton-oh")
        assert rec.census_count == rec.partition_count == 188
        assert rec.missing_from_partition == ()
        assert rec.missing_from_census == ()
        assert rec.duplicated_in_partition == ()
        assert (rec.published, rec.verified_no_pets) == (99, 40)  # after PTF-CLEVELAND-PASS4-DECISION-APPLICATION-001
        assert rec.resolved == 139 and rec.unresolved == 49  # after Pass-4 decisions
