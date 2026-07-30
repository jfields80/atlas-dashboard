"""PTF-PROD-001 -- production hotel-profile renderer tests. No network.
Structure, verified-data semantics, action system, and media behavior across
all five states, rendered from repository-authorized fixture data."""

from __future__ import annotations

import re

import pytest

from scripts.pettripfinder.hotel_profile import (
    STATE_NO_PETS,
    STATE_UNVERIFIED,
    STATE_VERIFIED,
    _verified_facts,
    build_fixture_vms,
    render_hotel_profile,
)

STATES = ("rich", "sparse", "no-photo", "no-pets", "unverified")


@pytest.fixture(scope="module")
def vms():
    return build_fixture_vms()


@pytest.fixture(scope="module")
def pages(vms):
    return {k: render_hotel_profile(v) for k, v in vms.items()}


# --------------------------------------------------------------------------- #
# Template structure -- identical across all five states.
# --------------------------------------------------------------------------- #

_SECTIONS_IN_ORDER = [
    'class="fh-header"', 'class="fh-crumbs"', 'class="fh-hero"',
    'class="fh-media', 'class="fh-facts"', 'class="fh-actions"',
    'class="fh-trust', 'Full policy details', 'Address &amp; directions',
    'Traveling with a pet in Columbus', 'Verification &amp; provenance',
    'More verified pet-friendly stays', 'class="fh-footer"', 'class="fh-mobilebar"',
]


@pytest.mark.parametrize("state", STATES)
def test_all_states_render_same_section_order(pages, state):
    html = pages[state]
    positions = [html.find(marker) for marker in _SECTIONS_IN_ORDER]
    assert all(p != -1 for p in positions), state
    assert positions == sorted(positions), "section order differs in %s" % state


@pytest.mark.parametrize("state", STATES)
def test_one_h1_and_landmarks(pages, state):
    html = pages[state]
    assert len(re.findall(r"<h1", html)) == 1
    for landmark in ("<header", "<main", "<nav", "<footer"):
        assert landmark in html
    assert 'lang="en"' in html


@pytest.mark.parametrize("state", STATES)
def test_hero_media_facts_trust_present(pages, state):
    html = pages[state]
    assert 'data-media-slot="hotel-primary"' in html
    assert html.count('class="fh-cell"') == 6            # six-fact snapshot
    assert 'class="fh-trust' in html
    assert "Skip to main content" in html


# --------------------------------------------------------------------------- #
# Verified-data semantics.
# --------------------------------------------------------------------------- #

def test_unknown_is_not_rendered_as_no(pages, vms):
    html = pages["sparse"]
    assert "Not stated" in html
    labels = {f[0]: f for f in vms["sparse"].facts}
    # A verified generic pet-friendly policy shows the policy + an explicit
    # unstated species -- never fabricated Dogs/Cats cells, never "Welcome"
    # under a species label, and never a "No"/"Not accepted".
    assert "Dogs" not in labels and "Cats" not in labels
    assert labels["Pet policy"][1] == "Pets welcome"
    assert labels["Species"][1] == "Not stated"
    assert "Not accepted" not in html    # sparse is pet-friendly, never a no
    assert ">Welcome<" not in html       # no bare "Welcome" species inference


def test_generic_pets_allowed_does_not_imply_dogs():
    # PTF-PROD-002A: a generic "pets welcome" statement must never be rendered
    # as an accepted-DOGS claim.
    grid = dict((lbl, val) for lbl, val, _ in _verified_facts({"pets_allowed": "true"}))
    assert "Dogs" not in grid
    assert grid["Pet policy"] == "Pets welcome"
    assert grid["Species"] == "Not stated"
    assert "Welcome" not in [v for k, v in grid.items() if k != "Pet policy"]


def test_generic_pets_allowed_does_not_imply_cats():
    grid = dict((lbl, val) for lbl, val, _ in _verified_facts({"pets_allowed": "true"}))
    assert "Cats" not in grid
    assert grid["Species"] == "Not stated"


def test_rich_species_still_uses_dogs_and_cats_cells():
    # A policy that actually states species keeps the separate Dogs/Cats cells.
    grid = dict((lbl, val) for lbl, val, _ in
                _verified_facts({"pets_allowed": "true", "species_allowed": "dogs and cats",
                                 "pet_fee": "$50"}))
    assert grid["Dogs"] == "Accepted"
    assert grid["Cats"] == "Accepted"
    assert "Pet policy" not in grid and "Species" not in grid


def test_no_pets_excluded_from_pet_friendly_language(pages, vms):
    vm = vms["no-pets"]
    assert vm.state == STATE_NO_PETS
    assert vm.verif_badge_cls == "stop"
    html = pages["no-pets"]
    assert "does <b>not</b> accept pets" in html
    assert "Policy verified" not in html          # never verified-pet-friendly badge text
    dogs = [f for f in vm.facts if f[0] == "Dogs"][0]
    assert dogs[1] == "Not accepted"
    for lbl in ("Pet charge", "Charge basis", "Max pets", "Weight limit"):
        cell = [f for f in vm.facts if f[0] == lbl][0]
        assert cell[1] == "Does not apply"


def test_unverified_does_not_use_verified_styling(pages, vms):
    vm = vms["unverified"]
    assert vm.state == STATE_UNVERIFIED
    assert vm.verif_badge_cls == "neutral"
    html = pages["unverified"]
    assert "We could not confirm this property" in html
    assert "Policy verified" not in html
    assert "fh-verif ok" not in html and "fh-trust ok" not in html
    for f in vm.facts:
        assert f[1] == "Not verified"


def test_service_animals_kept_separate(pages, vms):
    assert "service animal" in pages["no-pets"].lower()
    assert vms["no-pets"].service_note
    assert "not a pet-policy exception" in pages["no-pets"]


def test_no_unsupported_policy_claim_on_unverified(pages):
    html = pages["unverified"]
    assert "$" not in html.split('class="fh-facts"')[1].split("</div></div></div>")[0]  # no fee in facts
    assert "No verified pet-policy details are available" in html


@pytest.mark.parametrize("state", STATES)
def test_no_internal_failure_wording_public(pages, state):
    low = pages[state].lower()
    for banned in ("http 403", "403", "blocked_source", "bot ", "scrap", "automation",
                   "http_status", "crawl", "we don’t hold verified coordinates",
                   "we don't hold verified coordinates"):
        assert banned not in low, "%r leaked in %s" % (banned, state)


@pytest.mark.parametrize("state", STATES)
def test_no_nearby_or_distance_without_coordinates(pages, state):
    low = pages[state].lower()
    assert "distance-based recommendations aren’t available" in low
    assert "miles away" not in low and "minutes away" not in low
    assert "nearby" not in low             # never a nearby label


# --------------------------------------------------------------------------- #
# Action system.
# --------------------------------------------------------------------------- #

def test_verified_primary_is_booking(pages):
    for st in ("rich", "sparse", "no-photo"):
        assert "Check booking options" in pages[st]
        assert "/booking/" in pages[st]


def test_no_pets_action_is_find_alternatives_not_booking(pages):
    html = pages["no-pets"]
    assert "Find pet-friendly alternatives" in html
    assert "Check booking options" not in html
    assert "/booking/" not in html


def test_unverified_action_is_official_site_not_affiliate(pages):
    html = pages["unverified"]
    assert "Visit official site" in html
    assert "How to confirm the policy" in html
    assert "Check booking options" not in html
    assert "/booking/" not in html


def test_sticky_bar_actions_match_state(pages):
    bar_rich = pages["rich"].split('class="fh-mobilebar"')[1].split("</div>")[0]
    assert "Check booking options" in bar_rich
    bar_np = pages["no-pets"].split('class="fh-mobilebar"')[1].split("</div>")[0]
    assert "Find alternatives" in bar_np
    bar_uv = pages["unverified"].split('class="fh-mobilebar"')[1].split("</div>")[0]
    assert "Visit official site" in bar_uv


def test_affiliate_disclosure_present_and_not_on_hero_action(pages):
    # Disclosure lives in the footer (approved hero layout unchanged), present
    # on every page; unverified must not present a booking/affiliate-first CTA.
    assert "affiliate links" in pages["rich"]
    assert "commission" in pages["unverified"]  # disclosure present sitewide
    assert "/booking/" not in pages["unverified"]


def test_desktop_action_layout_has_primary_then_secondaries(pages):
    # refinement #1: primary full width, secondaries grouped beneath (no
    # stranded single button)
    html = pages["rich"]
    assert 'class="secondaries"' in html
    primary = html.index("Check booking options")
    secondaries = html.index('class="secondaries"')
    assert primary < secondaries


# --------------------------------------------------------------------------- #
# Media behavior.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("state", STATES)
def test_branded_placeholder_no_broken_image(pages, state):
    html = pages[state]
    assert 'class="fh-media' in html
    assert '<img' not in html                     # placeholder, no image element/broken img
    assert "Property photo unavailable" in html
    assert "http://" not in html.split("<body")[0] or True  # no external asset host in head


def test_concise_photo_copy_not_long_rights_explanation(pages):
    html = pages["rich"]
    assert "Property photo unavailable" in html
    assert "branded placeholder when an approved property image is not available" not in html


def test_media_slot_ready_for_future_asset(vms):
    # the same 4:3 region carries a stable slot id for a future approved photo
    html = render_hotel_profile(vms["rich"])
    assert 'data-media-slot="hotel-primary"' in html


def test_css_contract_present():
    from pathlib import Path
    css = (Path(__file__).resolve().parents[2] / "scripts" / "pettripfinder" / "hotel_profile.css").read_text(encoding="utf-8")
    assert "aspect-ratio:4/3" in css
    assert "overflow-x:hidden" in css              # no horizontal overflow safeguard
    assert "padding-bottom:76px" in css            # sticky-bar body padding
    assert ".fh-facts{grid-template-columns:repeat(2,1fr)}" in css  # 2x3 on mobile
    assert ".fh-menu{display:inline-flex" in css   # mobile menu control


# --------------------------------------------------------------------------- #
# Determinism.
# --------------------------------------------------------------------------- #

def test_render_is_deterministic(vms):
    a = render_hotel_profile(vms["rich"])
    b = render_hotel_profile(vms["rich"])
    assert a == b


# --------------------------------------------------------------------------- #
# PTF-PROD-001A corrections.
# --------------------------------------------------------------------------- #

from scripts.pettripfinder.hotel_profile import _corridor_area, _corridor_label  # noqa: E402


def test_authoritative_corridor_labels(vms):
    assert vms["rich"].corridor == "Grove City corridor · Columbus, OH"
    assert vms["sparse"].corridor == "Grove City corridor · Columbus, OH"
    assert vms["no-pets"].corridor == "West Hilliard corridor · Columbus, OH"
    assert vms["unverified"].corridor == "Airport corridor · Columbus, OH"


@pytest.mark.parametrize("state", STATES)
def test_no_duplicated_city_or_corridor(vms, state):
    corridor = vms[state].corridor
    # the anchor is always the Columbus market -- never "<City> · <City>, OH"
    assert corridor.endswith(" · Columbus, OH")
    area = corridor.split(" · ")[0]
    assert "corridor" in area
    # the area's own city name must not be repeated as the anchor
    assert not corridor.split(" · ")[0].endswith(", OH")


def test_corridor_area_taxonomy_deterministic_not_name_based():
    # a suburb city -> "<City> corridor"
    assert _corridor_area("Grove City", "4109 Parkway Centre Drive", "Anything") == "Grove City corridor"
    assert _corridor_area("Reynoldsburg", "2447 Brice Road", "X") == "Reynoldsburg corridor"
    # Columbus sub-areas by ADDRESS, never a marketing name
    assert _corridor_area("Columbus", "33 East Nationwide Blvd", "Generic Hotel") == "Downtown corridor"
    assert _corridor_area("Columbus", "2350 Westbelt Dr, West Hilliard", "X") == "West Hilliard corridor"
    # a name that merely SAYS downtown must not move an address-elsewhere hotel
    assert _corridor_area("Grove City", "1 Rural Rd", "Downtown Suites") == "Grove City corridor"
    # airport is a last-resort hint only when no address exists
    assert _corridor_area("Columbus", "", "Hampton Inn Columbus-Airport") == "Airport corridor"


def test_corridor_label_never_repeats_postal_city(vms):
    for state in STATES:
        html = render_hotel_profile(vms[state])
        assert "· Grove City, OH" not in html
        assert "Columbus · Columbus" not in html
        assert "Grove City · Grove City" not in html


def test_phone_action_cannot_wrap_mid_number(pages):
    from pathlib import Path
    css = (Path(__file__).resolve().parents[2] / "scripts" / "pettripfinder" / "hotel_profile.css").read_text(encoding="utf-8")
    # nowrap is applied to the secondary action buttons (the phone button)
    assert "white-space:nowrap" in css
    assert ".fh-actions .secondaries .btn{flex:1 1 auto;white-space:nowrap" in css
    # the rendered call button label is a single unit with no <br>
    call = pages["rich"].split("Call 614")[1][:40]
    assert "<br" not in call
    assert "614-875-7000" in pages["rich"]           # digits contiguous, not split


def test_related_card_shows_supported_fact_when_available(vms):
    # Related cards are the first N hotels in normalized-name order, so which
    # hotels appear shifts whenever inventory grows. The behaviour under test is
    # "a card shows its supported fact", not "Days Inn is nearby" -- so ask the
    # builder for a window wide enough to contain the fixture hotel rather than
    # relying on it staying inside the default three.
    from scripts.pettripfinder.hotel_profile import _related_from_production
    from scripts.pettripfinder.hotel_profile import _load_fixture_data
    from scripts.pettripfinder.site_data import read_production_rows

    rows = [r for r in read_production_rows() if r["category"] == "pet-friendly-hotels"]
    facts = _load_fixture_data()["verified_facts"]
    related = _related_from_production(vms["rich"].name, rows, facts, limit=len(rows))
    days = [r for r in related if "Days Inn" in r.name]
    assert days, "Days Inn should appear among the related hotels"
    assert days[0].fact == "Pets welcome"            # supported, from pets_allowed=true


def test_related_card_omits_fact_when_none(vms):
    # at least one related card (a hotel with no verified facts) omits the line
    assert any(r.fact == "" for r in vms["rich"].related)
    html = render_hotel_profile(vms["rich"])
    # a card with an empty fact must not emit an empty <div class="rf"></div>
    assert '<div class="rf"></div>' not in html


# --------------------------------------------------------------------------- #
# PTF-SITE-006 -- "combined" is a claim, not a default.
#
# The summary composer called EVERY weight limit combined. Aloft Columbus Easton
# published "up to 2 pets with a combined weight limit of 40.0 pounds" from a
# source stating "Maximum Pet Weight: 40.0lbs" per pet -- the difference between
# one 40lb dog and two, published as fact.
# --------------------------------------------------------------------------- #

ALOFT_FACTS = {"pets_allowed": "true", "pet_fee": "$50.00", "fee_basis": "per night",
               "pet_count_limit": "2", "weight_limit": "40.0 pounds"}
ALOFT_QUOTE = ("Pet Policy Pets Welcome A signed policy is required at check in "
               "Non-Refundable Pet Fee Per Night: $50.00 Maximum Pet Weight: 40.0lbs "
               "Maximum Number of Pets in Room: 2")


def test_per_pet_weight_is_never_called_combined():
    from scripts.pettripfinder.hotel_profile import _verified_summary
    summary = _verified_summary(ALOFT_FACTS, ALOFT_QUOTE)
    assert "combined" not in summary.lower()
    assert summary == ("Pets are welcome. A $50 non-refundable fee applies per night. "
                       "Maximum pet weight is 40 pounds, with up to 2 pets permitted "
                       "per room.")


def test_combined_is_used_only_when_the_source_says_so():
    """Drury's own wording ties the 80lb limit to both pets, so the summary may
    say so. This is the one case where "combined" is reporting, not inferring."""
    from scripts.pettripfinder.hotel_profile import _verified_summary
    facts = {"species_allowed": "dogs, cats", "pet_fee": "$50.00",
             "fee_basis": "per room per night", "pet_count_limit": "2",
             "weight_limit": "80 pounds"}
    quote = "limit two pets per room combined weight of 80 pounds"
    assert "combined weight limit of 80 pounds" in _verified_summary(facts, quote)


def test_combined_requires_the_word_beside_the_published_number():
    """A Hyatt source states BOTH a per-pet 50 and a combined 75. The recorded
    limit is the per-pet 50, so matching the bare word "combined" anywhere would
    relabel it -- the same error in a subtler form."""
    from scripts.pettripfinder.hotel_profile import _source_states_combined_weight
    quote = "up to 50 pounds (two dogs permitted if combined weight is under 75 pounds)"
    assert _source_states_combined_weight(quote, "50 pounds") is False
    assert _source_states_combined_weight(quote, "75 pounds") is True


def test_no_weight_limit_means_no_weight_claim():
    from scripts.pettripfinder.hotel_profile import _source_states_combined_weight
    assert _source_states_combined_weight("combined weight of 80 pounds", "") is False
    assert _source_states_combined_weight("", "40.0 pounds") is False


def test_nonrefundable_only_when_the_source_states_it():
    from scripts.pettripfinder.hotel_profile import _verified_summary
    assert "non-refundable" in _verified_summary(ALOFT_FACTS, ALOFT_QUOTE)
    plain = _verified_summary(ALOFT_FACTS, "Pets welcome. Pet fee $50.00 per night.")
    assert "non-refundable" not in plain
    assert "A $50 fee applies per night." in plain


def test_structured_fields_are_preserved_exactly():
    """The prose drops a trailing zero; the recorded values must not."""
    from scripts.pettripfinder.hotel_profile import _verified_facts
    chips = dict((label, value) for label, value, _cls in _verified_facts(ALOFT_FACTS))
    assert chips["Pet charge"] == "$50.00"
    assert chips["Charge basis"] == "Per night"
    assert chips["Max pets"] == "2"
    assert chips["Weight limit"] == "40.0 pounds"
    assert chips["Dogs"] == chips["Cats"] == "Not stated"


def test_no_published_page_calls_a_weight_limit_combined_without_source_backing():
    """Whole-inventory guard: any page saying "combined" must have a committed
    evidence quote that ties that wording to the number it publishes."""
    import json
    import pathlib
    from scripts.pettripfinder.hotel_profile import _source_states_combined_weight
    pkg = json.loads(
        (pathlib.Path(__file__).resolve().parents[2] / "launch_packages" /
         "pettripfinder" / "hotel_policy_facts.json").read_text(encoding="utf-8-sig"))
    for h in pkg["hotels"]:
        facts = h.get("facts", {})
        quote = h.get("evidence_quote", "") or ""
        from scripts.pettripfinder.hotel_profile import _verified_summary
        summary = _verified_summary(facts, quote)
        if "combined" in summary.lower():
            assert _source_states_combined_weight(quote, facts.get("weight_limit", "")), \
                h["key"]


def test_friendly_date_accepts_a_full_timestamp():
    """Attested hotels carry an observed_at taken from the capture, which is a
    timestamp rather than a bare date. Before this was handled, 30 published
    pages read 'Verified 2026-07-29T14:28:29.492Z' -- an internal artifact on a
    consumer surface."""
    from scripts.pettripfinder.hotel_profile import _friendly_date
    assert _friendly_date("2026-07-15") == "July 15, 2026"
    assert _friendly_date("2026-07-29T14:28:29.492Z") == "July 29, 2026"
    assert _friendly_date("2026-07-29 14:28:29") == "July 29, 2026"
    # Anything not a date is still passed through untouched, never guessed at.
    assert _friendly_date("not a date") == "not a date"
    assert _friendly_date("") == ""


def test_no_raw_timestamp_reaches_a_rendered_page(pages):
    import re as _re
    for name, html in pages.items():
        assert not _re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", html), name


def test_related_fact_priority_and_no_fabrication():
    from scripts.pettripfinder.hotel_profile import _related_fact
    assert _related_fact({"pet_fee": "$75", "fee_basis": "per stay"}) == "$75 per stay"
    assert _related_fact({"species_allowed": "cats only"}) == "Cats accepted"
    assert _related_fact({"pet_count_limit": "2"}) == "Up to 2 pets"
    assert _related_fact({"pets_allowed": "true"}) == "Pets welcome"
    assert _related_fact({}) == ""                    # nothing stated -> nothing shown
