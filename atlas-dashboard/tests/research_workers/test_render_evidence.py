"""PTF-CAPTURE-004A -- policy-level RENDER_REQUIRED.

``RENDER_REQUIRED`` is CAPTURE_WORTHY: assigning it is a licence to put a human
and a browser on a hotel. So the interesting tests here are not the two that
qualify -- they are the five that must not, because a loose rule would reroute
pages the automated path already handles onto the manual one and turn clean
records into REVIEW.

The Wyndham cases run against fixtures built from the real pages, which pin the
measured behaviour: the static HTML carries "Pet &amp; Service Animal Policy"
and no policy values; the rendered DOM carries the values once the ordinary
"Hotel Policies" control is opened.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from services.research_workers.render_evidence import (
    IDENTITY_INSUFFICIENT, MIN_STATIC_TEXT_CHARS, NO_RENDERED_EVIDENCE,
    NO_STATIC_POLICY_LANDMARK, NOT_PROPERTY_SCOPED, NOT_SUCCESSFUL_RETRIEVAL,
    PAGE_IS_BLOCKED, POLICY_VALUES_REQUIRE_RENDERING, STATIC_ALREADY_HAS_VALUES,
    STATIC_SHELL_TOO_THIN, classify_render_requirement, has_policy_landmark,
    policy_value_signals,
)

#: Kept OUT of capture_automation/fixtures on purpose. That directory is a
#: corpus of saved DOM snapshots, and its tests parametrize over "every real
#: page" in it -- dropping a differently-shaped file there broke 30 of them.
FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "render_evidence"


def load(name):
    return json.loads((FIXTURES / (name + ".json")).read_text("utf-8"))


def classify(fx, *, ok=True, identity=True, prop=True, rendered=None):
    return classify_render_requirement(
        retrieval_succeeded=ok,
        identity_sufficient=identity,
        property_scoped=prop,
        static_html=fx["static_html_excerpt"],
        static_text=fx["static_visible_text"],
        rendered_text=fx["rendered_policy_text"] if rendered is None else rendered,
    )


# --------------------------------------------------------------------------- #
# The fixtures must keep saying what they were built to say.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("name", ["wyndham-laquinta-west-hilliard",
                                  "wyndham-laquinta-dublin"])
def test_fixture_pins_the_observed_wyndham_behaviour(name):
    fx = load(name)
    assert "Pet &amp; Service Animal Policy" in fx["static_html_excerpt"]
    # the VALUES are absent statically...
    assert "ADA-defined service animals" not in fx["static_visible_text"]
    assert "75lbs" not in fx["static_visible_text"]
    # ...and present once rendered
    assert "ADA-defined service animals" in fx["rendered_policy_text"]
    assert "75lbs or less per pet" in fx["rendered_policy_text"]
    # and a reader can only see them after the ordinary control is opened
    assert fx["rendered_policy_painted_before_click"] is False
    assert fx["rendered_policy_painted_after_click"] is True


def test_the_two_properties_state_different_policies():
    """Proof the policy is property-specific, not a brand boilerplate: if these
    were identical, rendering them would prove nothing about the property."""
    wh = load("wyndham-laquinta-west-hilliard")["rendered_policy_text"]
    du = load("wyndham-laquinta-dublin")["rendered_policy_text"]
    assert wh != du
    assert "Dogs Allowed" in wh and "Cats and dogs only" in du


# --------------------------------------------------------------------------- #
# A + B: the two Wyndham properties qualify.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("name", ["wyndham-laquinta-west-hilliard",
                                  "wyndham-laquinta-dublin"])
def test_wyndham_property_qualifies(name):
    v = classify(load(name))
    assert v.qualifies is True
    assert v.reason == POLICY_VALUES_REQUIRE_RENDERING
    assert v.static_signals == ()
    assert "weight_limit" in v.rendered_signals
    assert "pet_count" in v.rendered_signals


# --------------------------------------------------------------------------- #
# C: an established-path brand must not be reclassified.
# --------------------------------------------------------------------------- #

MARRIOTT_STATIC = (
    "Pet Policy Pets Welcome 2 pets 50lbs max per room w/non refundable fee "
    "contact for details max $150/stay Non-Refundable Pet Fee Per Night: $50.00 "
    "Maximum Pet Weight: 50.0lbs Maximum Number of Pets in Room: 2 " + "filler " * 400)
HILTON_STATIC = (
    "Pets Pets Welcome Non-refundable fee: $75.00 Maximum Pet Weight: 75 lbs "
    "Maximum Number of Pets in Room: 2 " + "filler " * 400)
IHG_STATIC = (
    "Our Pet Policy: This is a dog only hotel. Up to two friendly pups under "
    "80 lbs are welcome. " + "filler " * 400)


@pytest.mark.parametrize("static", [MARRIOTT_STATIC, HILTON_STATIC, IHG_STATIC])
def test_a_brand_whose_values_are_already_static_never_qualifies(static):
    """Marriott, Hilton and IHG serve their values to the path we already have.
    Reclassifying them would manufacture manual work and downgrade records that
    publish cleanly today."""
    v = classify_render_requirement(
        retrieval_succeeded=True, identity_sufficient=True, property_scoped=True,
        static_html="<div class='pet-policy'>Pet Policy</div>",
        static_text=static,
        rendered_text=static)
    assert v.qualifies is False
    assert v.reason == STATIC_ALREADY_HAS_VALUES
    assert v.static_signals != ()


# --------------------------------------------------------------------------- #
# D: the brand-generic page.
# --------------------------------------------------------------------------- #

def test_generic_brand_pet_friendly_page_does_not_qualify():
    """Same domain, same brand, plenty of pet words -- but it describes no
    property. This is the page the Dublin retrieval actually landed on."""
    fx = load("wyndham-laquinta-brand-pet-friendly")
    v = classify(fx, prop=False)
    assert v.qualifies is False
    assert v.reason == NOT_PROPERTY_SCOPED


def test_generic_brand_page_still_refused_even_if_called_property_scoped():
    """Belt and braces: if an upstream bug ever mislabelled the brand page as
    property-scoped, it must still fail on the evidence itself."""
    fx = load("wyndham-laquinta-brand-pet-friendly")
    v = classify(fx, prop=True)
    assert v.qualifies is False
    assert v.reason in (NO_STATIC_POLICY_LANDMARK, STATIC_ALREADY_HAS_VALUES,
                        NO_RENDERED_EVIDENCE)


# --------------------------------------------------------------------------- #
# E: wrong property / insufficient identity.
# --------------------------------------------------------------------------- #

def test_insufficient_identity_does_not_qualify():
    v = classify(load("wyndham-laquinta-west-hilliard"), identity=False)
    assert v.qualifies is False
    assert v.reason == IDENTITY_INSUFFICIENT


# --------------------------------------------------------------------------- #
# F: gated and shell cases keep their own classifications.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("marker", [
    "Please sign in to continue",
    "Verify you are human",
    "Access Denied",
    "Checking your browser before accessing",
])
def test_gated_pages_are_reported_as_gated_not_as_needing_render(marker):
    """These already have correct statuses upstream (ACCESS_BLOCKED). The rule
    must never relabel one as 'just needs rendering', which would send an
    operator to a wall."""
    v = classify_render_requirement(
        retrieval_succeeded=True, identity_sufficient=True, property_scoped=True,
        static_html="<div class='pet-policy'>Pet Policy</div>",
        static_text=marker + " " + ("filler " * 400),
        rendered_text="Dogs Allowed - 2 dogs max. 75lbs or less per pet.")
    assert v.qualifies is False
    assert v.reason == PAGE_IS_BLOCKED


def test_empty_javascript_shell_does_not_qualify():
    """An empty shell is the ORIGINAL RENDER_REQUIRED case and must keep going
    through FETCH_STATUS_JAVASCRIPT_REQUIRED, not this rule."""
    v = classify_render_requirement(
        retrieval_succeeded=True, identity_sufficient=True, property_scoped=True,
        static_html="<div class='pet-policy'></div>",
        static_text="Loading...",
        rendered_text="Dogs Allowed - 2 dogs max. 75lbs or less per pet.")
    assert v.qualifies is False
    assert v.reason == STATIC_SHELL_TOO_THIN


def test_a_failed_retrieval_never_qualifies():
    v = classify(load("wyndham-laquinta-west-hilliard"), ok=False)
    assert v.qualifies is False
    assert v.reason == NOT_SUCCESSFUL_RETRIEVAL


# --------------------------------------------------------------------------- #
# G: a page that merely says "pets".
# --------------------------------------------------------------------------- #

def test_a_page_mentioning_pets_without_a_landmark_does_not_qualify():
    """"Our pet-friendly hotel is located off exit 15" is marketing prose. If
    that counted as a policy landmark, half the web would qualify."""
    v = classify_render_requirement(
        retrieval_succeeded=True, identity_sufficient=True, property_scoped=True,
        static_html="<p>Our pet-friendly hotel is near the mall. Pets welcome!</p>",
        static_text="Our pet-friendly hotel is near the mall. Pets welcome! "
                    + ("filler " * 400),
        rendered_text="Dogs Allowed - 2 dogs max. 75lbs or less per pet.")
    assert v.qualifies is False
    assert v.reason == NO_STATIC_POLICY_LANDMARK


def test_landmark_requires_a_policy_section_not_the_word_pets():
    assert has_policy_landmark("<h2>Pet Policy</h2>") is True
    assert has_policy_landmark("<h2>Pet &amp; Service Animal Policy</h2>") is True
    assert has_policy_landmark("<div class='policy-items pet-policy'>") is True
    assert has_policy_landmark("<p>pets welcome</p>") is False
    assert has_policy_landmark("<p>we love pets</p>") is False


def test_no_rendered_values_does_not_qualify():
    """The page simply does not publish a policy. Sending an operator to render
    it would be sending them to look at nothing."""
    v = classify_render_requirement(
        retrieval_succeeded=True, identity_sufficient=True, property_scoped=True,
        static_html="<div class='pet-policy'>Pet Policy</div>",
        static_text="Pet Policy " + ("filler " * 400),
        rendered_text="Pet Policy Contact the hotel for details.")
    assert v.qualifies is False
    assert v.reason == NO_RENDERED_EVIDENCE


# --------------------------------------------------------------------------- #
# The value detector itself.
# --------------------------------------------------------------------------- #

def test_value_signals_ignore_sentiment_and_catch_quantities():
    assert policy_value_signals("Pets are welcome at our hotel.") == ()
    assert "money_amount" in policy_value_signals("Fees - 25 USD per pet per night.")
    assert "money_amount" in policy_value_signals("A $50.00 fee applies.")
    assert "weight_limit" in policy_value_signals("75lbs or less per pet")
    assert "pet_count" in policy_value_signals("2 dogs max")


def test_no_brand_or_domain_appears_in_the_decision_logic():
    """The rule must key on evidence, not on who served it. A domain allowlist
    would be a bypass wearing a classifier's clothes."""
    import inspect

    from services.research_workers import render_evidence

    src = inspect.getsource(render_evidence.classify_render_requirement)
    src += inspect.getsource(render_evidence.has_policy_landmark)
    src += inspect.getsource(render_evidence.policy_value_signals)
    for brand in ("wyndham", "laquinta", "la quinta", "marriott", "hilton",
                  "ihg", "hyatt", ".com"):
        assert brand not in src.lower(), brand


# --------------------------------------------------------------------------- #
# Fixture hygiene. These are derived from real pages, so the same standing
# check the capture corpus carries applies here -- a new fixture directory
# does not get to opt out of it.
# --------------------------------------------------------------------------- #

_URL = __import__("re").compile(r'https?://[^\s"\'<>\\]+')

_PRIVATE = __import__("re").compile(
    r"(?i)(sessiontoken|gclid|gbraid|wbraid|fbclid|msclkid|wt\.mc_id|"
    r"gclsrc|gad_source|gad_campaignid|utm_[a-z]+)")


@pytest.mark.parametrize("path", sorted(
    (pathlib.Path(__file__).parent / "fixtures" / "render_evidence").glob("*.json")))
def test_fixture_carries_nothing_private(path):
    raw = path.read_text("utf-8")
    hit = _PRIVATE.search(raw)
    assert hit is None, "%s carries %r" % (path.name, hit.group(0) if hit else "")


@pytest.mark.parametrize("path", sorted(
    (pathlib.Path(__file__).parent / "fixtures" / "render_evidence").glob("*.json")))
def test_no_fixture_url_carries_a_query_string(path):
    urls = _URL.findall(path.read_text("utf-8"))
    assert urls, "fixture records no source URL at all"
    offenders = [u for u in urls if "?" in u]
    assert not offenders, offenders[:3]
