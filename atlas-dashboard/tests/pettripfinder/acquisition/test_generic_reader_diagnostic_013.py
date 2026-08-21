"""PTF-GENERIC-READER-FIRECRAWL-DIAGNOSTIC-013 -- measuring, not fixing.

A diagnostic whose classifier is wrong is worse than no diagnostic: it produces
a confident number that sends the next work order in the wrong direction. This
one was wrong twice during its own execution, and both mistakes are pinned here
so they cannot come back.

  * The first run counted a ROOM RATE as a pet fee. "Best rate / My6 member
    rate / $89" satisfied a bare ``$NN`` pattern, and two Motel 6 pages were
    reported as containing partial policy when they contain an amenity chip and
    a marketing sentence. Substantive terms now require a pet word within
    reach -- the same rule ``policy_reading`` applies for the same reason.
  * The correction then over-swung and scored two documents with unmistakable
    policy as AMENITY_ONLY, because the pet-proximity regex had been written
    with literal backspace bytes instead of ``\\b``. It matched nothing, so
    every substantive term was discarded. Invisible in a diff, fatal to the
    result.

So the tests below check the classifier against text whose right answer is not
in dispute, in both directions: an amenity label must never be FULL, and a
stated fee must never be missed.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from scripts.pettripfinder.acquisition import generic_reader_diagnostic_013 as D
from scripts.pettripfinder.acquisition import providers as PROVIDERS
from scripts.pettripfinder.acquisition import registry as REGISTRY
from . import authority_freeze as AUTHORITY_FREEZE

REPO_ROOT = Path(__file__).resolve().parents[3]
REPORTS = REPO_ROOT / "launch_packages" / "pettripfinder" / "markets" / "reports"
DIAGNOSTIC = REPORTS / "ptf_generic_reader_diagnostic_013.json"
ROUTES_PATH = (REPO_ROOT / "scripts" / "pettripfinder" / "acquisition"
               / "routes.json")

# Verbatim from the persisted Milwaukee documents.
AMENITY_CHIP = ("Read more Amenities Pets Allowed Coin Laundry Elevator "
                "Restaurant Nearby Wi-Fi Kids Stay Free View all amenities "
                "Choose your room Best rate My6 member rate Flexible rate")
REAL_POLICY_STUDIO6 = ("There is a non-refundable pet fee of $25 per day "
                       "applies for the first 6 days, and $15 per day "
                       "thereafter except for service animals.")
REAL_POLICY_WILDWOOD = ("Dog Friendly All dogs are welcome at the Wildwood "
                        "Lodge and we look forward to pampering your furry "
                        "friend. A $20 fee applies per night.")
ROOM_RATES_ONLY = ("Choose your room Best rate $89 My6 member rate $79 "
                   "Flexible rate $99 Book now")


def _presence(text: str) -> str:
    return D.classify_presence(text, identity_ok=True)["presence"]


# --------------------------------------------------------------------------- #
# The classifier, in both directions
# --------------------------------------------------------------------------- #

class TestAmenityContentIsNeverAPolicy:
    def test_an_amenity_chip_is_amenity_only(self):
        assert _presence(AMENITY_CHIP) == "AMENITY_ONLY"

    def test_an_amenity_chip_can_never_be_full_policy(self):
        assert _presence(AMENITY_CHIP) != "FULL_POLICY_PRESENT"

    def test_a_room_rate_is_not_a_pet_fee(self):
        """The first run of this diagnostic made exactly this mistake."""
        assert "fee" not in D.scan_document(ROOM_RATES_ONLY)
        assert _presence(ROOM_RATES_ONLY) == "NO_POLICY_PRESENT"

    def test_a_price_far_from_any_pet_word_is_ignored(self):
        text = "Rooms from $129 per night. " + "filler. " * 40 + "Pets allowed."
        assert "fee" not in D.scan_document(text)


class TestRealPolicyIsRecognised:
    def test_a_stated_fee_with_a_basis_is_recognised_as_policy(self):
        """This snippet states three actionable terms -- fee, basis and
        non-refundability -- and never says the words "pets allowed". That is
        PARTIAL by design: terms without an allow/refuse statement are policy
        content, but the surface has not said whether pets are accepted. In
        the live document the signal appears elsewhere on the page and the
        same text classifies FULL."""
        result = D.classify_presence(REAL_POLICY_STUDIO6, identity_ok=True)
        assert result["presence"] == "PARTIAL_POLICY_PRESENT"
        assert set(result["substantive_concepts"]) >= {"fee", "basis"}
        assert result["presence"] != "NO_POLICY_PRESENT"

    def test_the_same_terms_with_an_acceptance_statement_are_full_policy(self):
        assert _presence("Pets are welcome. " + REAL_POLICY_STUDIO6) ==             "FULL_POLICY_PRESENT"

    def test_a_dog_policy_with_a_nightly_fee_is_recognised(self):
        result = D.classify_presence(REAL_POLICY_WILDWOOD, identity_ok=True)
        assert result["presence"] in ("FULL_POLICY_PRESENT",
                                      "PARTIAL_POLICY_PRESENT")
        assert "fee" in result["concepts"]

    def test_weight_and_count_language_counts_as_policy(self):
        text = ("Pets are welcome. Maximum 2 pets per room, 50 lbs each.")
        result = D.classify_presence(text, identity_ok=True)
        assert result["presence"] == "FULL_POLICY_PRESENT"
        assert set(result["substantive_concepts"]) >= {"weight", "count"}

    def test_the_pet_proximity_regex_actually_matches_a_pet_word(self):
        """It once contained literal backspace bytes instead of \\b and matched
        nothing, silently discarding every substantive term."""
        assert D._PET_WORD_RE.search("a pet fee")
        assert D._PET_WORD_RE.search("all dogs are welcome")
        assert "\x08" not in D._PET_WORD_RE.pattern

    def test_no_regex_in_this_module_contains_a_control_character(self):
        source = Path(D.__file__).read_bytes()
        assert b"\x08" not in source
        assert b"\x0c" not in source


class TestPresenceIsJudgedWithoutTheReader:
    def test_the_scan_never_calls_the_reader(self):
        """Layer B must be independent, or a reader failure would look like an
        empty document and the whole diagnostic would be circular."""
        for fn in (D.scan_document, D.classify_presence):
            source = inspect.getsource(fn)
            assert "locate_policy_in_html" not in source
            assert "PR.parse" not in source
            assert "read_generically" not in source

    def test_a_document_the_reader_cannot_bound_can_still_hold_policy(self):
        """The finding this work order exists for."""
        assert _presence(REAL_POLICY_WILDWOOD) != "NO_POLICY_PRESENT"
        reader = D.read_generically("<html><body>%s</body></html>"
                                    % REAL_POLICY_WILDWOOD)
        verdict = D.compare(
            D.classify_presence(REAL_POLICY_WILDWOOD, identity_ok=True), reader)
        assert verdict["verdict"] in ("READER_MISS", "READER_PARTIAL",
                                      "READER_CORRECT")

    def test_an_unusable_document_is_not_scored_as_absent_policy(self):
        assert D.classify_presence("anything", identity_ok=False)["presence"] \
            == "UNUSABLE_DOCUMENT"


# --------------------------------------------------------------------------- #
# Cohort
# --------------------------------------------------------------------------- #

class TestCohortSelectionIsDeterministic:
    def test_it_returns_the_same_cohort_every_time(self):
        first = [r["identity_key"] for r in D.cohort()["selected"]]
        second = [r["identity_key"] for r in D.cohort()["selected"]]
        assert first == second

    def test_it_respects_the_cap(self):
        selection = D.cohort()
        assert len(selection["selected"]) <= D.COHORT_CAP

    def test_the_method_is_recorded_and_names_the_ordering(self):
        method = D.cohort()["selection_method"]
        assert "identity_key" in method
        assert "cannot select for expected success" in method

    def test_the_brands_with_a_decision_behind_them_enter_whole(self):
        classes = [r["class"] for r in D.cohort()["selected"]]
        universe = [r["class"] for r in D.generic_universe()]
        assert classes.count("MOTEL6") == universe.count("MOTEL6")
        assert classes.count("RED_ROOF") == universe.count("RED_ROOF")

    def test_excluded_rows_are_named_not_dropped_silently(self):
        selection = D.cohort()
        assert isinstance(selection["excluded_by_cap"], list)
        assert len(selection["selected"]) + len(selection["excluded_by_cap"]) \
            == selection["universe_total"]


# --------------------------------------------------------------------------- #
# Safety
# --------------------------------------------------------------------------- #

class TestTheDiagnosticCannotTouchProduction:
    def test_it_never_imports_a_bright_data_capture_path(self):
        source = inspect.getsource(D)
        for forbidden in ("browser_capture", "cross_brand_capture",
                          "brightdata_browser", "brightdata_web_unlocker"):
            assert forbidden not in source, forbidden

    def test_it_only_ever_calls_firecrawl(self):
        source = inspect.getsource(D.acquire)
        assert "FC.fetch" in source
        assert "capture_property" not in source

    def test_it_writes_no_route_and_no_authority(self):
        """Checked by looking for WRITES, not for the words. An earlier version
        searched the source for "routes.json" and matched the module docstring
        saying it does not touch routes.json."""
        source = inspect.getsource(D)
        assert "hotel_policy_facts" not in source
        writes = [ln.strip() for ln in source.splitlines()
                  if ("write_bytes" in ln or "write_text" in ln
                      or "open(" in ln and '"w' in ln)]
        # The only writes are the diagnostic's own artifacts.
        for line in writes:
            assert ("target.write_bytes" in line or "out.write_bytes" in line), line

    def test_no_production_route_moved(self):
        registry = REGISTRY.load()
        assert registry["version"] == 4
        assert registry["brands"]["MOTEL6"]["provider"] == \
            PROVIDERS.BRIGHTDATA_BROWSER
        assert registry["brands"]["RED_ROOF"]["provider"] == \
            PROVIDERS.BRIGHTDATA_BROWSER
        assert registry["default"]["provider"] == PROVIDERS.BRIGHTDATA_BROWSER
        for brand in ("CHOICE", "WYNDHAM", "IHG"):
            assert registry["brands"][brand]["provider"] == PROVIDERS.FIRECRAWL

    def test_no_policy_authority_was_created(self):
        """NARROWED by PTF-MILWAUKEE-FOUNDER-DECISION-036.

        This claimed the work order created no Milwaukee authority, which
        was true and still is. Read against the live filesystem it became
        "Milwaukee may never have one", and the founder has since approved
        96 records explicitly and in writing. The historical claim is
        checked against the commit; the standing claim -- that authority is
        recorded and never live inventory, and that every row in it was
        approved by a human -- is checked beside it.
        """
        AUTHORITY_FREEZE.assert_commit_created_no_authority("35dfac2")
        AUTHORITY_FREEZE.assert_authority_is_recorded_not_live()
        AUTHORITY_FREEZE.assert_every_authority_row_was_approved_by_a_human()


    def test_the_route_table_does_not_cite_this_work_order(self):
        assert "DIAGNOSTIC-013" not in ROUTES_PATH.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# The committed result
# --------------------------------------------------------------------------- #

class TestTheCommittedDiagnostic:
    def _doc(self):
        if not DIAGNOSTIC.is_file():
            pytest.skip("diagnostic not run in this worktree")
        return json.loads(DIAGNOSTIC.read_text(encoding="utf-8-sig"))

    def test_it_changed_nothing(self):
        doc = self._doc()
        assert doc["routes_changed"] is False
        assert doc["authority_written"] is False
        assert doc["policies_published"] is False

    def test_no_bright_data_was_used(self):
        cost = self._doc()["cost"]
        assert cost["bright_data_attempts"] == 0
        assert cost["bright_data_usd"] == 0.0

    def test_the_failure_modes_are_reported_by_class_not_averaged(self):
        """The work order forbids averaging fundamentally different failure
        modes into one number, and these classes genuinely differ."""
        by_class = self._doc()["by_class"]
        assert set(by_class) >= {"MOTEL6", "RED_ROOF", "INDEPENDENT"}
        for stats in by_class.values():
            assert "presence" in stats and "verdicts" in stats

    def test_a_homepage_is_not_blamed_on_the_provider(self):
        """Fetching a site root successfully and finding no policy is a URL
        gap. Calling it a provider limitation would send the next work order
        to the wrong layer."""
        causes = [r.get("limitation_cause", "") for r in self._doc()["properties"]]
        assert any(c.startswith("URL_IS_NOT_A_POLICY_PAGE") for c in causes)

    def test_every_recoverable_document_names_its_supporting_snippets(self):
        for row in self._doc()["properties"]:
            presence = row["layer_b_presence"]
            if presence["presence"] in ("FULL_POLICY_PRESENT",
                                        "PARTIAL_POLICY_PRESENT"):
                assert presence["concepts"], row["identity_key"]
                assert presence["substantive_concepts"], row["identity_key"]

    def test_the_architectural_decision_follows_from_the_rates(self):
        doc = self._doc()
        rates = doc["rates"]
        decision = doc["architectural_decision"]
        opportunity = rates["reader_opportunity_rate_pct"]
        provider = rates["provider_limitation_rate_pct"]
        if decision == "READER_HARDENING_JUSTIFIED":
            assert opportunity >= 60 and provider < 50
        elif decision == "PROVIDER_IS_PRIMARY_LIMIT":
            assert opportunity < 30
        else:
            assert decision == "MIXED"

    def test_identity_was_evaluated_for_every_document(self):
        doc = self._doc()
        assert sum(doc["layer_a_identity"].values()) == doc["rates"]["documents"]
