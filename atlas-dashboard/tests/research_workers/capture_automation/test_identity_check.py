"""Identity verification against the real corpus.

Two properties matter here above all: the right hotel passes, and the wrong
hotel fails closed. The second is the one that could put a wrong pet policy on
a real property's page, so it gets the harder tests.
"""

from __future__ import annotations

import pytest

from services.research_workers.capture_automation.contracts import DomSnapshot
from services.research_workers.capture_automation.identity_check import (
    identity_from_jsonld, observe_identity, verify_identity,
)

from .conftest import entry_for, fixture_names, load_fixture, snapshot_for


class TestObservation:
    @pytest.mark.parametrize("name", fixture_names())
    def test_property_code_comes_out_of_the_url(self, name):
        entry = entry_for(name)
        observed = observe_identity(snapshot_for(name),
                                    known_codes=[entry.expected_property_code])
        assert observed.property_code == entry.expected_property_code

    @pytest.mark.parametrize("name", fixture_names())
    def test_name_is_recovered(self, name):
        assert observe_identity(snapshot_for(name)).name

    def test_jsonld_beats_a_stale_title(self):
        """Hilton serves the page title 'Embassy Suites by Hilton Columbus
        Airport' on the Hilton Garden Inn Columbus Airport property page. A
        title-trusting implementation mislabels that hotel; this one does not."""
        payload = load_fixture("hilton-cmhcagi.json")
        assert "Embassy Suites" in payload["title"]
        observed = observe_identity(DomSnapshot.from_capture_payload(payload))
        assert observed.name == "Hilton Garden Inn Columbus Airport"
        assert "Embassy" not in observed.name

    def test_missing_jsonld_falls_back_to_title(self):
        dom = DomSnapshot(final_url="https://www.marriott.com/en-us/hotels/"
                                    "cmhxx-test-hotel/overview/",
                          title="Test Hotel | Something Marketing")
        assert observe_identity(dom).name == "Test Hotel"

    def test_malformed_jsonld_costs_the_block_not_the_capture(self):
        dom = DomSnapshot(final_url="https://www.marriott.com/en-us/hotels/"
                                    "cmhxx-test-hotel/overview/",
                          title="Test Hotel",
                          jsonld=({"@type": "WebPage", "name": "not a hotel"},))
        assert observe_identity(dom).name == "Test Hotel"

    def test_graph_nested_jsonld_is_flattened(self):
        blocks = ({"@graph": [{"@type": "Hotel", "name": "Nested Inn",
                               "telephone": "+16145551234"}]},)
        assert identity_from_jsonld(blocks).name == "Nested Inn"


# Hilton's /hotel-info/ page shape carries a JSON-LD Hotel block with a name
# and nothing else -- no telephone, no postal address. assess_identity returns
# AMBIGUOUS on that evidence, which is not publishable, so this page shape
# cannot be captured unattended and routes to a human instead.
#
# Recorded as a known limitation rather than smoothed over. Weakening the
# identity gate to admit a name-only match would let one hotel's policy attach
# to another property, and that is the exact failure this pipeline exists to
# prevent. The operator captures these five-per-hundred pages with the
# extension.
IDENTITY_UNVERIFIABLE_SHAPES = frozenset({"hilton-cmhchhf.json"})


class TestTheRightHotelPasses:
    @pytest.mark.parametrize("name", sorted(
        set(fixture_names()) - IDENTITY_UNVERIFIABLE_SHAPES))
    def test_real_page_matches_its_own_queue_entry(self, name):
        verdict = verify_identity(snapshot_for(name), entry_for(name),
                                  observed_at="2026-07-31T00:00:00Z")
        assert verdict.ok, "%s failed: %s %s" % (name, verdict.reason, verdict.detail)

    @pytest.mark.parametrize("name", sorted(IDENTITY_UNVERIFIABLE_SHAPES))
    def test_thin_identity_page_is_unverifiable_not_captured(self, name):
        """Fails closed, and says why in a way that routes to a human."""
        verdict = verify_identity(snapshot_for(name), entry_for(name),
                                  observed_at="2026-07-31T00:00:00Z")
        assert not verdict.ok
        assert verdict.reason == "IDENTITY_UNVERIFIABLE"
        from services.research_workers.capture_automation.reasons import retry_for
        assert retry_for(verdict.reason) == "manual"


class TestTheWrongHotelFailsClosed:
    def test_different_property_code_is_refused(self):
        entry = entry_for("marriott-cmham.json", expected_property_code="cmhzz")
        verdict = verify_identity(snapshot_for("marriott-cmham.json"), entry)
        assert not verdict.ok
        assert verdict.reason == "PROPERTY_CODE_MISMATCH"

    def test_one_marriott_page_never_satisfies_another_marriott_entry(self):
        """Same brand, same city, same page template -- the case a weaker check
        would wave through."""
        entry = entry_for("marriott-cmhsi.json")          # Sheraton Worthington
        verdict = verify_identity(snapshot_for("marriott-cmham.json"), entry)
        assert not verdict.ok

    def test_search_url_is_refused_before_content_is_considered(self):
        """PTF-WORKERS-007: shape is judged first, because a query-driven URL is
        never a stable citation whatever the page happens to say."""
        payload = load_fixture("marriott-cmham.json")
        payload["final_url"] = ("https://www.marriott.com/search/findHotels.mi"
                                "?destination=Columbus")
        verdict = verify_identity(DomSnapshot.from_capture_payload(payload),
                                  entry_for("marriott-cmham.json"))
        assert not verdict.ok
        assert verdict.reason == "SEARCH_URL"

    def test_redirect_off_property_is_refused(self):
        payload = load_fixture("marriott-cmham.json")
        payload["final_url"] = "https://www.marriott.com/en-us/default.mi"
        verdict = verify_identity(DomSnapshot.from_capture_payload(payload),
                                  entry_for("marriott-cmham.json"))
        assert not verdict.ok
        assert verdict.reason in ("REDIRECTED_OFF_PROPERTY", "PROPERTY_CODE_MISMATCH")

    def test_page_with_no_identity_evidence_is_unverifiable_not_mismatched(self):
        """'We cannot tell' and 'this is the wrong hotel' get different reasons,
        because only one of them is worth handing to a human."""
        entry = entry_for("marriott-cmham.json", expected_property_code="")
        dom = DomSnapshot(
            final_url="https://www.marriott.com/en-us/hotels/cmham-columbus-"
                      "airport-marriott/overview/",
            title="", text="This page is nearly empty.")
        verdict = verify_identity(dom, entry)
        assert not verdict.ok
        assert verdict.reason == "IDENTITY_UNVERIFIABLE"

    def test_a_refusal_always_names_a_declared_reason(self):
        from services.research_workers.capture_automation.reasons import (
            EXCEPTION_REASONS,
        )
        entry = entry_for("marriott-cmham.json", expected_property_code="cmhzz")
        verdict = verify_identity(snapshot_for("marriott-cmham.json"), entry)
        assert verdict.reason in EXCEPTION_REASONS
