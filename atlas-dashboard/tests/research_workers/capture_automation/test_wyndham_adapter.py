"""PTF-CAPTURE-004B -- the Wyndham adapter.

Wyndham is the friendliest brand in this package to reach and the hardest to
SEE: the whole policy sits in the DOM at 0x0 pixels until an ordinary "Hotel
Policies" link is clicked. So the tests that matter are the ones about the
reveal click and about not mistaking the brand page for a property.
"""

from __future__ import annotations

from typing import Tuple

import pytest

from services.research_workers.capture_automation.adapters import (
    adapter_for, known_brands,
)
from services.research_workers.capture_automation.adapters.wyndham import (
    WyndhamAdapter,
)
from services.research_workers.capture_automation.contracts import DomSnapshot

WEST_HILLIARD_URL = ("https://www.wyndhamhotels.com/laquinta/columbus-ohio/"
                     "la-quinta-columbus-west-hilliard/overview")
DUBLIN_URL = ("https://www.wyndhamhotels.com/laquinta/dublin-ohio/"
              "la-quinta-inn-columbus-dublin/overview")
BRAND_URL = "https://www.wyndhamhotels.com/laquinta/about-us/pet-friendly"

WEST_HILLIARD_POLICY = (
    "Service Animals - ADA-defined service animals are welcome free of charge. "
    "/ Dogs Allowed - 2 dogs max. 75lbs or less per pet. / Fees - 25 USD per "
    "pet per night. Max 75 USD per stay. / Other Information - Contact hotel "
    "for additional details and availability.")
DUBLIN_POLICY = (
    "Service Animals - ADA-defined service animals are welcome free of charge. "
    "/ Pets Allowed - 2 pets max. Cats and dogs only. 75lbs or less per pet. / "
    "Fees - Non-refundable 25 USD nightly for up to 2 pets. Max 75 USD per "
    "stay. / Other Information - Contact hotel for additional details.")

REVEAL_HTML = ('<a href="#" data-target="#hotelPoliciesLightbox">Hotel Policies</a>'
               '<div class="row policy-lists"><div class="policy-items pet-policy">'
               '<span class="pet-policy-desc">%s</span></div></div>')


def dom(url, policy, *, html=None):
    body = REVEAL_HTML % policy if html is None else html
    return DomSnapshot(
        final_url=url, canonical_url=url,
        title="La Quinta Inn & Suites by Wyndham",
        html="<html><body>%s</body></html>" % body,
        text="Pet & Service Animal Policy " + policy, jsonld=())


@pytest.fixture()
def adapter():
    return WyndhamAdapter()


# --------------------------------------------------------------------------- #
# Registration.
# --------------------------------------------------------------------------- #

def test_wyndham_is_registered():
    assert "wyndham" in known_brands()
    assert adapter_for("wyndham").brand == "wyndham"


def test_registering_wyndham_did_not_disturb_the_other_brands():
    assert set(known_brands()) == {"hilton", "ihg", "marriott", "wyndham",
                                   "bestwestern", "choice", "redroof"}


def test_hyatt_is_still_unregistered():
    """Kasada is still Kasada. Adding one brand must not quietly add another."""
    assert adapter_for("hyatt") is None


# --------------------------------------------------------------------------- #
# Property vs brand page.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("url", [WEST_HILLIARD_URL, DUBLIN_URL])
def test_property_pages_are_accepted(adapter, url):
    assert adapter.url_is_property_page(url) is True


def test_the_brand_pet_friendly_page_is_refused(adapter):
    """The page the Dublin retrieval actually landed on. It describes no single
    hotel, so capturing it would attribute a brand policy to one property."""
    assert adapter.url_is_property_page(BRAND_URL) is False


@pytest.mark.parametrize("url", [
    "https://www.wyndhamhotels.com/laquinta/about-us/terms",
    "https://www.wyndhamhotels.com/days-inn/about-us/pet-friendly",
])
def test_any_about_us_page_is_refused(adapter, url):
    """Structural, not a page blocklist -- /about-us/ is where Wyndham puts
    brand content, whichever brand it is."""
    assert adapter.url_is_property_page(url) is False


# --------------------------------------------------------------------------- #
# The reveal click -- the whole reason this adapter exists.
# --------------------------------------------------------------------------- #

def test_the_plan_clicks_hotel_policies(adapter):
    d = dom(WEST_HILLIARD_URL, WEST_HILLIARD_POLICY)
    steps = adapter.interaction_plan(d, adapter.locate_policy(d))
    clicks = [s for s in steps if s.action == "click_text"]
    assert clicks, "no reveal click planned"
    assert clicks[0].text == "Hotel Policies"
    assert "hotelPoliciesLightbox" in clicks[0].selector


def test_no_click_is_planned_when_the_control_is_absent(adapter):
    """An adapter must not propose clicking something the page does not have."""
    d = dom(WEST_HILLIARD_URL, WEST_HILLIARD_POLICY,
            html='<div class="policy-items pet-policy">%s</div>' % WEST_HILLIARD_POLICY)
    steps = adapter.interaction_plan(d, adapter.locate_policy(d))
    assert [s for s in steps if s.action == "click_text"] == []


def test_the_policy_container_is_scrolled_into_view(adapter):
    d = dom(DUBLIN_URL, DUBLIN_POLICY)
    steps = adapter.interaction_plan(d, adapter.locate_policy(d))
    scrolls = [s for s in steps if s.action == "scroll_into_view"]
    assert scrolls and scrolls[0].optional is False


def test_consent_is_never_dismissed(adapter):
    """Measured: these pages render no consent banner at all. The rule holds
    regardless -- dismissing one is an operator decision, not an adapter's."""
    assert adapter.consent_selectors() == ()


# --------------------------------------------------------------------------- #
# Locating the policy.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("url,policy", [(WEST_HILLIARD_URL, WEST_HILLIARD_POLICY),
                                        (DUBLIN_URL, DUBLIN_POLICY)])
def test_the_policy_block_is_located_on_both_properties(adapter, url, policy):
    loc = adapter.locate_policy(dom(url, policy))
    assert loc is not None
    assert "Allowed" in loc.text_excerpt or "ADA-defined" in loc.text_excerpt
    # the brand anchors are what lift a block whose amounts carry no dollar sign
    assert loc.matched_anchors
    assert loc.confidence != "LOW"


def test_the_container_selector_is_unique_to_the_pet_policy(adapter):
    """The IHG trap: a selector matching every policy panel made the runner
    measure a collapsed parking block. Wyndham gives each region its own class,
    so the pet one is addressable."""
    assert adapter.container_selectors[0] == "div.policy-items.pet-policy"
    assert "pet" in adapter.container_selectors[0]


def test_brand_anchors_cover_the_wording_wyndham_actually_uses(adapter):
    joined = " ".join(adapter.extra_anchors).lower()
    for phrase in ("pet & service animal policy", "dogs allowed", "pets allowed"):
        assert phrase in joined


def test_identity_hint_is_additive_only(adapter):
    """A readiness hint may make the wait finish sooner; it may never be what
    decides identity."""
    assert adapter.identity_selectors() == ("script[type='application/ld+json']",)
