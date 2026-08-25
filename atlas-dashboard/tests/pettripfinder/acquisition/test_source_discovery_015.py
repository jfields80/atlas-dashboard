"""PTF-INDEPENDENT-POLICY-URL-DISCOVERY-LAYER-015 -- the reusable layer.

Promoting a measured algorithm to production is where it quietly stops being
the measured algorithm. So the central test here is not a unit test at all: it
replays the eleven Milwaukee independents through the new module and requires
the same eight URLs work order 014 selected. A reusable implementation that
disagrees with the measurement justifying it is a different algorithm wearing
its name.

The rest guard the three rules that cost something to learn, and the one that
cost money:

  * a candidate must come from a link the page CONTAINS -- never a convention;
  * same-domain is not property binding, because two of these operators run
    several hotels on one domain;
  * a page that disclaims specificity can never be property-specific evidence;
  * and provider REQUESTS are not documents on disk. 014 recorded 2 credits for
    a 23-document run because a cache-only rebuild overwrote the real figure
    with its own delta. The ledger here is monotonic for that reason and a test
    drives the exact scenario.

Nothing in this work order may move a route, a reader, the census or any
authority file, and the overlay it writes is explicitly not authority.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from scripts.pettripfinder.acquisition import providers as PROVIDERS
from scripts.pettripfinder.acquisition import registry as REGISTRY
from scripts.pettripfinder.acquisition import source_discovery as SD
from scripts.pettripfinder.acquisition import source_discovery_replay_015 as R15
from . import authority_freeze as AUTHORITY_FREEZE

REPO_ROOT = Path(__file__).resolve().parents[3]
REPORTS = REPO_ROOT / "launch_packages" / "pettripfinder" / "markets" / "reports"
REPLAY = REPORTS / "ptf_source_discovery_replay_015.json"
DISCOVERY_014 = REPORTS / "ptf_independent_url_discovery_014.json"
OVERLAY = SD.overlay_path(REPO_ROOT, "milwaukee-wi")
ROUTES_PATH = (REPO_ROOT / "scripts" / "pettripfinder" / "acquisition"
               / "routes.json")

HOME = ('<a href="/amenities/">Amenities</a>'
        '<a href="/faq/">FAQ</a>'
        '<a href="/dogs/">Dogs</a>'
        '<a href="/privacy-policy/">Privacy</a>'
        '<a href="https://directory.test/hotel">Directory listing pets</a>')


def _text(html: str) -> str:
    import re
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


def _presence(result: str, concepts=None):
    def classify(text, identity_ok):
        if not identity_ok:
            return {"presence": "UNUSABLE_DOCUMENT", "why": "", "concepts": {}}
        return {"presence": result, "why": "stub", "concepts": concepts or {}}
    return classify


def _fetcher(pages):
    def fetch(url):
        html = pages.get(url, "")
        return {"html": html, "final_url": url, "requested": bool(html)}
    return fetch


def _discover(**overrides):
    kwargs = dict(
        identity_key="k", property_name="Example Lodge Pewaukee",
        starting_url="https://example.test/pewaukee/", home_html=HOME,
        fetch=_fetcher({"https://example.test/dogs/": "<p>Example Lodge. "
                                                      "$20 per night per dog.</p>"}),
        to_text=_text, classify_presence=_presence("FULL_POLICY_PRESENT"))
    kwargs.update(overrides)
    return SD.discover(**kwargs)


# --------------------------------------------------------------------------- #
# 1. Determinism
# --------------------------------------------------------------------------- #

class TestDiscoveryIsDeterministic:
    def test_the_same_inputs_give_the_same_answer(self):
        first, second = _discover(), _discover()
        assert first.to_dict() == second.to_dict()

    def test_ranking_is_stable_and_ordered_by_specificity(self):
        ranked = SD.rank_candidates(HOME, "https://example.test/")
        assert [c.url for c in ranked] == [c.url for c in
                                           SD.rank_candidates(HOME, "https://example.test/")]
        assert ranked[0].url.endswith("/dogs/")
        assert ranked[0].score >= ranked[-1].score

    def test_the_ranking_table_is_ordered_high_to_low(self):
        scores = [score for score, _why, _rx in SD.RANKING]
        assert scores == sorted(scores, reverse=True)


# --------------------------------------------------------------------------- #
# 2 & 7. First-party only, bounded
# --------------------------------------------------------------------------- #

class TestCandidatesAreFirstPartyAndBounded:
    def test_a_third_party_link_is_classified_not_followed(self):
        ranked = SD.rank_candidates(HOME, "https://example.test/")
        third = [c for c in ranked if c.relationship == "THIRD_PARTY"]
        assert third, "the directory link must be seen and classified"
        result = _discover()
        for row in result.rejected:
            assert "directory.test" not in row["url"]
        assert result.discovered_url is not None
        assert "directory.test" not in result.discovered_url

    def test_nothing_is_synthesised_from_a_convention(self):
        assert SD.rank_candidates("<html>no links</html>",
                                  "https://example.test/") == []
        result = _discover(home_html="<html>no links</html>")
        assert result.status == SD.NO_POLICY_URL_FOUND
        assert result.discovered_url is None

    def test_privacy_and_booking_surfaces_are_excluded(self):
        urls = {c.url for c in SD.rank_candidates(HOME, "https://example.test/")}
        assert not any("privacy" in u for u in urls)

    def test_the_candidate_budget_is_fixed_and_enforced(self):
        assert SD.CANDIDATE_BUDGET == 3
        seen = []

        def counting_fetch(url):
            seen.append(url)
            return {"html": "<p>nothing</p>", "final_url": url, "requested": True}

        many = "".join('<a href="/faq%d/">FAQ %d</a>' % (i, i) for i in range(20))
        _discover(home_html=many, fetch=counting_fetch,
                  classify_presence=_presence("NO_POLICY_PRESENT"))
        assert len(seen) <= SD.CANDIDATE_BUDGET


# --------------------------------------------------------------------------- #
# 3 & 6. Identity is mandatory; same-domain is not identity
# --------------------------------------------------------------------------- #

class TestIdentityIsMandatory:
    def test_a_different_location_on_the_same_domain_is_refused(self):
        identity = SD.validate_identity(
            "Wildwood Lodge", "https://w.test/pewaukee/",
            "https://w.test/clive/faqs/", "Wildwood Lodge Clive. Dogs $20.")
        assert identity["confirmed"] is False
        assert identity["location_conflict"] is True

    def test_the_property_own_location_is_accepted(self):
        identity = SD.validate_identity(
            "Wildwood Lodge", "https://w.test/pewaukee/",
            "https://w.test/pewaukee/faqs/", "Wildwood Lodge Pewaukee.")
        assert identity["confirmed"] is True

    def test_a_page_type_is_not_a_location(self):
        """The fix for the location bug nearly disqualified a hotel for having
        both a /contact/ page and an /amenities/ page."""
        identity = SD.validate_identity(
            "The Plaza Hotel", "https://p.test/contact/",
            "https://p.test/amenities/", "The Plaza Hotel. $50 pet fee.")
        assert identity["location_conflict"] is False
        assert identity["confirmed"] is True

    def test_a_disclaiming_page_can_never_bind(self):
        identity = SD.validate_identity(
            "WoodSpring Menomonee", "https://w.test/locations/menomonee/",
            "https://w.test/offers/pet-friendly-hotel",
            "WoodSpring Menomonee. Restrictions apply and may vary by location.")
        assert identity["confirmed"] is False
        assert identity["disclaims"] is True

    def test_a_generic_operator_page_is_graded_generic_and_rejected(self):
        candidate = SD.Candidate(url="https://w.test/offers/x", anchor_text="pets",
                                 score=100, matched_rule="r",
                                 relationship="SAME_DOMAIN")
        quality = SD.grade_source(candidate, {"disclaims": True,
                                              "location_conflict": False,
                                              "same_domain": True,
                                              "tokens_found": ["woodspring"]})
        assert quality == "generic_brand_or_operator_page"
        assert quality not in SD.ACCEPTABLE_QUALITY

    def test_an_unbound_candidate_never_becomes_policy_url_found(self):
        result = _discover(
            fetch=_fetcher({"https://example.test/dogs/":
                            "<p>Rates may vary by location. Pets $20.</p>"}))
        assert result.status != SD.POLICY_URL_FOUND
        assert result.rejected


# --------------------------------------------------------------------------- #
# 4 & 5. Policy presence is required; amenity is not policy
# --------------------------------------------------------------------------- #

class TestPolicyPresenceIsRequired:
    def test_amenity_only_content_becomes_amenity_url_only(self):
        result = _discover(classify_presence=_presence("AMENITY_ONLY"))
        assert result.status == SD.AMENITY_URL_ONLY
        assert result.status != SD.POLICY_URL_FOUND

    def test_a_page_with_no_policy_is_not_promoted(self):
        result = _discover(classify_presence=_presence("NO_POLICY_PRESENT"))
        assert result.status == SD.NO_POLICY_URL_FOUND
        assert result.discovered_url is None

    def test_full_and_partial_both_qualify(self):
        for presence in ("FULL_POLICY_PRESENT", "PARTIAL_POLICY_PRESENT"):
            result = _discover(classify_presence=_presence(presence))
            assert result.status == SD.POLICY_URL_FOUND, presence

    def test_presence_classification_is_injected_not_owned(self):
        """It stays the 013 taxonomy; this module does not invent a second
        opinion about what a policy is."""
        assert "classify_presence" in inspect.signature(SD.discover).parameters
        source = inspect.getsource(SD)
        assert "policy_reading" not in source

    def test_every_status_it_can_return_is_in_the_contract(self):
        for status in (SD.POLICY_URL_FOUND, SD.AMENITY_URL_ONLY,
                       SD.NO_POLICY_URL_FOUND, SD.IDENTITY_AMBIGUOUS,
                       SD.DISCOVERY_BLOCKED):
            assert status in SD.STATUSES

    def test_a_result_carries_the_contract_and_its_reasoning(self):
        result = _discover()
        data = result.to_dict()
        assert data["contract"] == SD.CONTRACT
        for key in ("starting_url", "discovered_url", "first_party",
                    "identity_confirmed", "identity_reason", "policy_presence",
                    "source_quality", "discovery_reason",
                    "candidates_considered", "status"):
            assert key in data, key


class TestBlockedIsDistinctFromAbsent:
    def test_every_candidate_failing_to_return_a_document_is_blocked(self):
        result = _discover(fetch=lambda url: {"html": "", "final_url": "",
                                              "requested": True})
        assert result.status == SD.DISCOVERY_BLOCKED

    def test_documents_that_arrive_without_policy_are_not_blocked(self):
        result = _discover(classify_presence=_presence("NO_POLICY_PRESENT"))
        assert result.status == SD.NO_POLICY_URL_FOUND


# --------------------------------------------------------------------------- #
# 8 & 9. Cache replay, and the 014 cost defect
# --------------------------------------------------------------------------- #

class TestUsageAccounting:
    def test_a_cached_replay_makes_no_provider_request(self, tmp_path):
        ledger = SD.UsageLedger(path=tmp_path / "usage.json")
        _discover(fetch=lambda url: {"html": "<p>x</p>", "final_url": url,
                                     "requested": False})
        ledger.record(requested=False)
        ledger.save()
        assert ledger.provider_requests == 0
        assert ledger.cache_hits == 1

    def test_a_cache_only_rebuild_cannot_lower_historical_usage(self, tmp_path):
        """THE 014 DEFECT, driven exactly: a 23-document run recorded 2 credits
        because the final rebuild measured its own near-zero delta and
        overwrote the real figure."""
        path = tmp_path / "usage.json"
        first = SD.UsageLedger(path=path)
        for _ in range(23):
            first.record(requested=True)
        first.save()
        assert first.provider_requests == 23

        rebuild = SD.UsageLedger(path=path).load()
        for _ in range(23):
            rebuild.record(requested=False)     # every document now cached
        rebuild.save()

        assert json.loads(path.read_text())["provider_requests"] == 23
        assert SD.UsageLedger(path=path).load().provider_requests == 23

    def test_requests_and_documents_stay_distinguishable(self, tmp_path):
        ledger = SD.UsageLedger(path=tmp_path / "usage.json")
        ledger.record(requested=True)
        ledger.record(requested=False)
        ledger.save()
        stored = json.loads((tmp_path / "usage.json").read_text())
        assert stored["provider_requests"] == 1
        assert stored["cache_hits"] == 1
        assert "never decreases" in stored["note"]

    def test_the_committed_replay_spent_nothing(self):
        if not REPLAY.is_file():
            pytest.skip("replay not run in this worktree")
        usage = json.loads(REPLAY.read_text(encoding="utf-8-sig"))["usage"]
        assert usage["provider_requests"] == 0
        assert usage["cache_hits"] > 0


# --------------------------------------------------------------------------- #
# 10. Equivalence to 014
# --------------------------------------------------------------------------- #

class TestTheMilwaukeeReplayReproduces014:
    def _doc(self):
        if not REPLAY.is_file():
            pytest.skip("replay not run in this worktree")
        return json.loads(REPLAY.read_text(encoding="utf-8-sig"))

    def test_it_is_equivalent_with_no_deviations(self):
        eq = self._doc()["equivalence"]
        assert eq["deviations"] == []
        assert eq["equivalent"] is True

    def test_it_reproduces_the_measured_counts(self):
        eq = self._doc()["equivalence"]
        assert eq["status_counts"]["POLICY_URL_FOUND"] == 8
        assert eq["status_counts"]["NO_POLICY_URL_FOUND"] == 3
        assert all(eq["matches_expected_014"].values())

    def test_every_selected_url_matches_014_exactly(self):
        for row in self._doc()["equivalence"]["rows"]:
            assert row["url_015"] == row["url_014"], row["identity_key"]
            assert row["status_015"] == row["status_014"], row["identity_key"]

    def test_the_expected_counts_are_pinned_in_code_not_read_back(self):
        """Reading the target from the artifact would make the check circular."""
        assert R15.EXPECTED_014 == {"POLICY_URL_FOUND": 8,
                                    "NO_POLICY_URL_FOUND": 3}
        assert R15.EXPECTED_COHORT == 11


# --------------------------------------------------------------------------- #
# The overlay
# --------------------------------------------------------------------------- #

class TestTheSourceRoutingOverlay:
    def _doc(self):
        if not OVERLAY.is_file():
            pytest.skip("overlay not written in this worktree")
        return json.loads(OVERLAY.read_text(encoding="utf-8-sig"))

    def test_it_declares_itself_not_authority(self):
        doc = self._doc()
        assert doc["is_policy_authority"] is False
        assert doc["publishes_policy"] is False

    def test_it_preserves_the_original_url_on_every_row(self):
        for row in self._doc()["records"]:
            assert row["original_source_url"]

    def test_it_carries_provenance_and_a_commit_on_every_row(self):
        for row in self._doc()["records"]:
            provenance = row["provenance"]
            assert provenance["measured_by"].endswith("DISCOVERY-014")
            assert provenance["implemented_by"].endswith("LAYER-015")
            assert len(provenance["commit"]) == 40

    def test_unresolved_properties_keep_their_existing_url(self):
        for row in self._doc()["records"]:
            if row["status"] != SD.POLICY_URL_FOUND:
                assert row["use_for_acquisition"] == row["original_source_url"]
                assert row["discovered_url"] is None

    def test_resolution_prefers_a_discovery_and_falls_back_to_the_census(self):
        assert SD.resolve_source_url(
            REPO_ROOT, "milwaukee-wi", "the pfister hotel",
            "https://www.thepfisterhotel.com/").endswith("/accommodations/pets/")
        assert SD.resolve_source_url(
            REPO_ROOT, "milwaukee-wi", "the clarke hotel",
            "https://www.theclarkehotel.com/") == "https://www.theclarkehotel.com/"
        assert SD.resolve_source_url(
            REPO_ROOT, "milwaukee-wi", "not a real key",
            "https://fallback.test/") == "https://fallback.test/"


# --------------------------------------------------------------------------- #
# 11-14. Freezes
# --------------------------------------------------------------------------- #

class TestNothingElseMoved:
    def test_the_census_was_not_edited(self):
        """official_url stays canonical there; the overlay is a preference."""
        source = inspect.getsource(R15)
        assert "identity_census" not in source
        assert "final_partition" not in source

    def test_provider_routes_are_unchanged(self):
        registry = REGISTRY.load()
        assert registry["version"] == 4
        assert registry["default"]["provider"] == PROVIDERS.BRIGHTDATA_BROWSER
        for brand in ("MOTEL6", "RED_ROOF", "MARRIOTT", "HILTON"):
            assert registry["brands"][brand]["provider"] == \
                PROVIDERS.BRIGHTDATA_BROWSER
        for brand in ("CHOICE", "WYNDHAM", "IHG"):
            assert registry["brands"][brand]["provider"] == PROVIDERS.FIRECRAWL
        assert set(registry["domains"]) == {"www.choicehotels.com"}

    def test_the_route_table_does_not_cite_this_work_order(self):
        assert "LAYER-015" not in ROUTES_PATH.read_text(encoding="utf-8")

    def test_the_readers_are_unchanged(self):
        source = inspect.getsource(SD)
        assert "policy_reading" not in source
        assert "read_generically" not in source

    def test_the_failure_taxonomy_is_unchanged(self):
        from scripts.pettripfinder.acquisition import failures as F
        assert F.ESCALATING | F.TERMINAL == set(F.FAILURES)
        assert not F.may_escalate(F.POLICY_NOT_FOUND)

    def test_no_milwaukee_policy_authority_exists(self):
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


    def test_the_replay_artifact_records_every_boundary(self):
        if not REPLAY.is_file():
            pytest.skip("replay not run in this worktree")
        doc = json.loads(REPLAY.read_text(encoding="utf-8-sig"))
        for key in ("routes_changed", "reader_changed", "census_edited",
                    "authority_written", "policies_published"):
            assert doc[key] is False, key

    def test_the_layer_cannot_reach_either_bright_data_provider(self):
        source = inspect.getsource(SD)
        for forbidden in ("brightdata", "browser_capture", "unlocker_capture"):
            assert forbidden not in source, forbidden

    def test_the_layer_does_not_fetch_by_itself(self):
        """The fetcher is injected, so a replay runs from cache and a test runs
        with no network at all."""
        assert "fetch" in inspect.signature(SD.discover).parameters

        # Checked by IMPORTS, not by searching the text. Two earlier versions
        # of this assertion matched prose: "urllib" hit the urlparse import
        # (string work, not networking) and "requests" hit the phrase
        # "provider requests" in a comment. A substring test over source is a
        # test of the prose.
        import ast
        tree = ast.parse(Path(SD.__file__).read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        assert "urllib" in imported, "urlparse is expected and is not networking"
        for network in ("http", "socket", "requests", "httpx", "aiohttp"):
            assert network not in imported, network
        # And no sibling module that can reach a provider.
        assert not [m for m in imported if "capture" in m or "firecrawl" in m]
