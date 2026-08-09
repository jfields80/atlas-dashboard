"""PTF-COLUMBUS-SELECTOR-CLOSEOUT-001 -- the last three Columbus policy cases.

Three hotels reached their pages, confirmed their identities, and still
reported POLICY_NOT_FOUND. This module holds what the retained DOM said about
each, so the selectors are answerable to markup a brand actually served rather
than to anybody's recollection of it.

The fixtures under ``closeout_fixtures/`` are verbatim fragments of artifacts
written by PTF-COLUMBUS-FINAL-CLOSURE-001, each carrying the sha256 of the file
it was cut from. They are STRUCTURAL grounding: they prove where a container
is, never what a hotel's policy is. Policy values for publication come from the
authoritative capture and nowhere else -- which is also why they live in their
own directory and not in ``fixtures/``, whose corpus-wide tests assert that
every member has a locatable policy. Le Meridien's captured state is the whole
point precisely because it does not.
"""

from __future__ import annotations

import hashlib
import json
import pathlib

import pytest

from services.research_workers.capture_automation.adapters.registry import (
    adapter_for,
)
from services.research_workers.capture_automation.contracts import DomSnapshot
from services.research_workers.capture_automation.policy_locator import (
    CONFIDENCE_HIGH, locate_policy,
)

from .conftest import fixture_names, snapshot_for

GROUNDING_DIR = pathlib.Path(__file__).parent / "closeout_fixtures"
REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]


def grounding(name: str) -> dict:
    return json.loads((GROUNDING_DIR / name).read_text("utf-8"))


def snapshot_from(url: str, text: str, title: str = "") -> DomSnapshot:
    return DomSnapshot.from_capture_payload(
        {"final_url": url, "requested_url": url, "title": title,
         "html": "", "text": text, "jsonld": []})


LE_MERIDIEN = grounding("marriott-cmhdm-le-meridien.json")
DRURY = grounding("drury-plaza-columbus-downtown.json")
EXTENDED_STAY = grounding("extendedstay-columbus-dublin.json")


class TestTheGroundingIsWhatItClaimsToBe:
    """If these drift, every assertion below is about the wrong page."""

    @pytest.mark.parametrize("fixture", [LE_MERIDIEN, DRURY, EXTENDED_STAY])
    def test_each_fragment_names_a_source_artifact_and_its_digest(self, fixture):
        assert fixture["source_artifact"].startswith("data/worker_runs/")
        assert len(fixture["source_sha256"]) == 64

    @pytest.mark.parametrize("fixture", [LE_MERIDIEN, DRURY, EXTENDED_STAY])
    def test_the_source_artifact_still_hashes_to_what_was_recorded(self, fixture):
        """The retained runs are gitignored, so skip rather than fail where the
        batch directory is absent -- but never pass silently on a changed one."""
        path = REPO_ROOT / fixture["source_artifact"]
        if not path.exists():
            pytest.skip("retained capture batch not present in this checkout")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == fixture["source_sha256"], fixture["hotel"]

    @pytest.mark.parametrize("fixture", [LE_MERIDIEN, DRURY, EXTENDED_STAY])
    def test_each_fragment_refuses_to_be_read_as_policy_evidence(self, fixture):
        assert "NOT_A_POLICY_EVIDENCE_SOURCE" in fixture["labels"]


# --------------------------------------------------------------------------- #
# Le Meridien Columbus, The Joseph -- Marriott template B
# --------------------------------------------------------------------------- #

class TestLeMeridienDefect:
    """Reproduce the failure before claiming to have fixed it."""

    def test_the_captured_page_yields_a_policy_block_with_no_policy_in_it(self):
        loc = locate_policy(snapshot_from(LE_MERIDIEN["page_url"],
                                          LE_MERIDIEN["captured_text"]))
        assert loc is not None, "the run reported a location, not a miss"
        # What it found is the accordion's own button labels, in order.
        for label in ("Pet Policy", "Smoke-Free Policy", "Cash Free",
                      "Community Fee Notice", "Our History"):
            assert label in loc.text_excerpt
        # And nothing a policy is made of.
        for value in ("$", "lbs", "Maximum Number of Pets"):
            assert value not in loc.text_excerpt

    def test_the_policy_is_in_the_served_html_and_not_in_the_rendered_text(self):
        assert "Maximum Number of Pets in Room: 2" in \
            LE_MERIDIEN["property_details_accordion_html"]
        assert "Maximum Number of Pets in Room" not in LE_MERIDIEN["captured_text"]

    def test_this_page_has_none_of_the_band_every_other_marriott_paints(self):
        """The template difference, stated as a check rather than a claim."""
        html = (LE_MERIDIEN["property_details_accordion_html"]
                + LE_MERIDIEN["additional_information_accordion_html"])
        assert "hotel-info__column" not in html
        assert "HOTEL INFORMATION" not in LE_MERIDIEN["captured_text"]


class TestLeMeridienSelector:

    def test_the_control_the_adapter_clicks_exists_on_the_page(self):
        adapter = adapter_for("marriott")
        selector, label = adapter.expand_text_controls[0]
        html = LE_MERIDIEN["property_details_accordion_html"]
        assert "faq-accordion-faq-question" in selector
        assert "faq-accordion-faq-question" in html
        assert label == "Hotel Information"
        assert ">\n        %s\n" % label in html or label in html

    def test_the_control_is_a_button_not_a_link(self):
        """A label-addressed click must not be able to navigate away."""
        selector, _ = adapter_for("marriott").expand_text_controls[0]
        assert selector.startswith("button")

    def test_the_plan_emits_that_click_for_this_page(self):
        adapter = adapter_for("marriott")
        dom = DomSnapshot.from_capture_payload(
            {"final_url": LE_MERIDIEN["page_url"],
             "requested_url": LE_MERIDIEN["page_url"], "title": "",
             "html": LE_MERIDIEN["property_details_accordion_html"],
             "text": LE_MERIDIEN["captured_text"], "jsonld": []})
        steps = adapter.interaction_plan(dom, adapter.locate_policy(dom))
        assert ("click_text", "Hotel Information") in [
            (s.action, s.text) for s in steps]

    def test_the_expanded_block_is_the_real_policy_and_outscores_the_chrome(self):
        """Same page, same locator, with the accordion body now in the rendered
        text -- which is exactly what the click produces."""
        expanded = (LE_MERIDIEN["captured_text"] + "\n"
                    + LE_MERIDIEN["property_details_visible_text"])
        loc = locate_policy(snapshot_from(LE_MERIDIEN["page_url"], expanded))
        assert loc is not None
        assert loc.confidence == CONFIDENCE_HIGH
        assert "Maximum Number of Pets in Room: 2" in loc.text_excerpt
        assert "Non-Refundable Pet Fee" in loc.text_excerpt
        assert "100.0lbs" in loc.text_excerpt
        assert "Smoke-Free Policy" not in loc.text_excerpt

    def test_the_two_surfaces_on_this_page_agree(self):
        """The marketing accordion states the same three numbers. Agreement is
        not required to publish, but a disagreement here would be a contradiction
        to preserve rather than a selector to pick between."""
        prose = LE_MERIDIEN["additional_information_visible_text"]
        assert "$50" in prose and "100lbs" in prose and "in Room: 2" in prose


class TestExistingMarriottCapturesStayGreen:

    @pytest.mark.parametrize("name", fixture_names("marriott"))
    def test_every_corpus_page_still_locates_its_own_policy(self, name):
        loc = adapter_for("marriott").locate_policy(snapshot_for(name))
        assert loc is not None, name
        assert loc.confidence == CONFIDENCE_HIGH, name
        assert "Pet Policy" in loc.text_excerpt or "Pets Welcome" in loc.text_excerpt

    @pytest.mark.parametrize("name", fixture_names("marriott"))
    def test_dropping_the_dead_selectors_changed_no_excerpt(self, name):
        """The four removed selectors were guesses that matched nothing, and
        the handle falls back to text anyway. Prove the located block is
        byte-identical to what the core locator produces unaided."""
        dom = snapshot_for(name)
        adapter = adapter_for("marriott")
        assert adapter.locate_policy(dom).text_excerpt == locate_policy(
            dom, extra_anchors=adapter.extra_anchors).text_excerpt

    @pytest.mark.parametrize("name", fixture_names("marriott"))
    def test_the_template_a_band_is_what_those_pages_render(self, name):
        assert "HOTEL INFORMATION" in json.loads(
            (pathlib.Path(__file__).parent / "fixtures" / name).read_text("utf-8")
        )["text"], name


# --------------------------------------------------------------------------- #
# Drury Plaza Hotel Columbus Downtown
# --------------------------------------------------------------------------- #

class TestDrurySelector:

    def test_the_container_selector_names_the_dialog_and_its_policies_block(self):
        selector = adapter_for("drury").container_selectors[0]
        assert selector == "#additional-info-modal .policies"
        assert 'id="additional-info-modal"' in DRURY["modal_html"]
        assert DRURY["modal_html"].count('class="policies"') == 1

    def test_the_trigger_the_adapter_clicks_is_a_visible_link_on_the_page(self):
        selector, label = adapter_for("drury").expand_text_controls[0]
        assert 'data-target="#additional-info-modal"' in DRURY["trigger_html"]
        assert "section-text-link" in DRURY["trigger_html"]
        assert "section-text-link" in selector
        assert label in DRURY["trigger_html"]

    def test_the_dialog_is_shut_on_arrival_which_is_why_the_run_missed_it(self):
        assert 'aria-hidden="true"' in DRURY["modal_html"]

    def test_the_container_is_the_property_speaking_not_the_brand(self):
        """A brand block cannot carry this hotel's room count and its own
        parking rate."""
        text = DRURY["modal_visible_text"]
        assert "Number of rooms: 180" in text
        assert "On-site covered parking: $24 per night" in text

    def test_the_opened_dialog_yields_a_high_confidence_property_policy(self):
        loc = adapter_for("drury").locate_policy(
            snapshot_from(DRURY["page_url"], DRURY["modal_visible_text"]))
        assert loc is not None
        assert loc.confidence == CONFIDENCE_HIGH
        assert "Dogs and cats accepted" in loc.text_excerpt
        assert "$50 per room plus tax" in loc.text_excerpt
        assert "combined weight of 80 pounds" in loc.text_excerpt

    def test_the_terminator_keeps_other_policies_out_of_the_excerpt(self):
        """Without it the excerpt runs 599 characters and picks up a people
        count and a rollaway rate -- two numbers an extractor could read as
        pet facts."""
        adapter = adapter_for("drury")
        dom = snapshot_from(DRURY["page_url"], DRURY["modal_visible_text"])
        narrowed = adapter.locate_policy(dom).text_excerpt
        unnarrowed = locate_policy(dom, extra_anchors=adapter.extra_anchors).text_excerpt

        assert "Maximum of five (5) people" in unnarrowed
        assert "Rollaways are available for $15" in unnarrowed
        assert "Maximum of five (5) people" not in narrowed
        assert "Rollaways" not in narrowed
        assert "Payment Policy" not in narrowed
        assert len(narrowed) < len(unnarrowed)

    def test_a_terminator_can_only_shorten_a_block(self):
        """The property that makes this an allowed narrowing rather than a
        brand rewriting the core."""
        from services.research_workers.capture_automation.policy_locator import (
            extract_block,
        )
        text = DRURY["modal_visible_text"]
        start = text.index("Pet Policy")
        assert len(extract_block(text, start, ("Payment Policy",))[0]) <= \
            len(extract_block(text, start)[0])

    def test_the_shut_page_locates_nothing(self):
        """Everything outside the dialog. This is the state the run saw."""
        outside = DRURY["modal_visible_text"].split("Hotel Information")[0]
        assert adapter_for("drury").locate_policy(
            snapshot_from(DRURY["page_url"], outside)) is None


class TestDruryTerminatorIsBrandScoped:

    def test_no_other_brand_inherits_it(self):
        for brand in ("marriott", "hilton", "ihg", "wyndham", "bestwestern",
                      "choice", "redroof", "extendedstay"):
            assert "Payment Policy" not in adapter_for(brand).extra_terminators, brand

    def test_the_core_terminator_list_was_not_touched(self):
        from services.research_workers.capture_automation.policy_locator import (
            BLOCK_TERMINATORS,
        )
        assert "Payment Policy" not in BLOCK_TERMINATORS


# --------------------------------------------------------------------------- #
# Extended Stay America Suites Columbus Dublin -- the selector NOT written
# --------------------------------------------------------------------------- #

class TestExtendedStayHasNoPropertyPolicyContainer:
    """These are the reasons a selector was refused here. They are tests so
    that wiring one up later has to argue with evidence first."""

    def test_the_only_policies_container_on_the_page_is_the_brand_modal(self):
        assert EXTENDED_STAY["policy_container_ids"] == [
            "servicesAndPoliciesModal", "servicesAndPoliciesModalTitle"]
        assert EXTENDED_STAY["property_scoped_policy_classes"] == []

    def test_that_modal_opens_with_a_site_wide_user_agreement(self):
        opening = EXTENDED_STAY["modal_opening_html"]
        assert "Site User Agreement" in opening
        assert "websites" in opening

    def test_its_pet_fee_is_a_ceiling_and_defers_to_the_property(self):
        text = EXTENDED_STAY["pet_section_visible_text"]
        assert "up to a $25" in text
        assert "not to exceed $15" in text
        assert "Please contact the property for questions" in text

    def test_the_adapter_declares_no_container_and_no_expander(self):
        adapter = adapter_for("extendedstay")
        assert adapter.container_selectors == ()
        assert adapter.expand_selectors == ()
        assert adapter.expand_text_controls == ()

    def test_the_refusal_is_written_down_where_the_next_reader_will_look(self):
        import services.research_workers.capture_automation.adapters.extendedstay \
            as module
        doc = module.__doc__ or ""
        assert "ceiling" in doc
        assert "servicesAndPoliciesModal" in doc
