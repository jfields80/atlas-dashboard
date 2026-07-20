"""PTF-PROD-002 -- integration tests: the real Columbus generator dispatches
hotel profiles through the APPROVED renderer.

These build the controlled three-hotel review sample with ``--fixture-facts``
(the committed review fixture), so they are fully reproducible in a clean
checkout without the gitignored operational corpus. The DEFAULT sample and the
full production build read the real operational facts -- proven separately by
test_generate_columbus_site.py (guarded on the operational corpus). No network;
writes only to pytest tmp_path; never mutates inventory.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import re

import pytest

from scripts.generate_pettripfinder_columbus_site import run_sample
from scripts.pettripfinder import hotel_profile_page
from scripts.pettripfinder.site_data import PRODUCTION_CSV

_EXPECTED_SLUGS = {
    "drury-inn-suites-columbus-grove-city",
    "days-inn-by-wyndham-grove-city-columbus-south",
    "sonesta-columbus-downtown",
}


@pytest.fixture(scope="module")
def sample(tmp_path_factory):
    # Default (no --fixture-facts): the NORMAL production path, sourced from the
    # tracked publishable package -- reproducible in a clean checkout.
    out = tmp_path_factory.mktemp("prod002_sample")
    code = run_sample(str(out))
    assert code == 0
    return out


def _hotel(sample, slug):
    return (sample / "pet-friendly-hotels" / slug / "index.html").read_text(encoding="utf-8")


# 1. Real generator dispatches hotel profiles through the approved renderer.
def test_dispatches_through_approved_renderer(sample):
    for slug in _EXPECTED_SLUGS:
        t = _hotel(sample, slug)
        assert 'class="fh-hero"' in t and 'class="fh-facts"' in t and "fh-verif" in t


# 2. Old hotel-profile markup path is not used.
def test_old_markup_path_not_used(sample):
    for slug in _EXPECTED_SLUGS:
        t = _hotel(sample, slug)
        assert "ptf-policy-table" not in t
        assert "ptf-badge--verified" not in t
        assert 'class="ac-listing' not in t     # base AES-WEB listing layout


# 3. Fixture JSON is not the source for actual production market pages.
def test_fixture_json_not_production_source(sample):
    # The production page builder never reads the committed fixture file; the
    # fixture only enters via the explicit --fixture-facts test switch.
    src = inspect.getsource(hotel_profile_page)
    assert "hotel_profile_fixtures" not in src
    # The NORMAL sample sources facts from the tracked publishable package, not
    # the review fixture.
    report = json.loads((sample / "_sample_report.json").read_text(encoding="utf-8"))
    assert report["facts_source"] == "published_launch_package"
    assert report["renderer"].endswith("render_production_hotel_profile")


# 4. Rich real record maps correctly.
def test_rich_record_maps_correctly(sample):
    t = _hotel(sample, "drury-inn-suites-columbus-grove-city")
    assert "Policy verified" in t
    assert "$50" in t
    assert "Grove City corridor · Columbus, OH" in t


# 5. Sparse real record maps correctly -- generic pet-friendly, species NOT inferred.
def test_sparse_record_maps_correctly(sample):
    t = _hotel(sample, "days-inn-by-wyndham-grove-city-columbus-south")
    assert "Policy verified" in t          # verified, but sparse
    assert "Not stated by the reviewed source" in t
    assert "Grove City corridor · Columbus, OH" in t
    # PTF-PROD-002A: a generic pets-allowed policy shows the policy + an explicit
    # unstated species, never a fabricated "Dogs -- Welcome".
    assert "Pets welcome" in t
    assert re.search(r'<div class="k">Species</div><div class="v [^"]*">Not stated</div>', t)
    assert "<div class=\"v yes\">Welcome</div>" not in t   # no "Dogs -- Welcome" cell
    assert re.search(r'<div class="k">Dogs</div>', t) is None


# 6. CSS asset is emitted and referenced correctly.
def test_css_asset_emitted_and_referenced(sample):
    assert (sample / "hotel-profile.css").exists()
    for slug in _EXPECTED_SLUGS:
        assert 'href="/hotel-profile.css"' in _hotel(sample, slug)


# 7. Canonical and structured data remain valid.
def test_canonical_and_structured_data_valid(sample):
    for slug in _EXPECTED_SLUGS:
        t = _hotel(sample, slug)
        m = re.search(r'<link rel="canonical" href="([^"]+)"', t)
        assert m and m.group(1) == "https://pettripfinder.com/pet-friendly-hotels/%s/" % slug
        types = [json.loads(p.replace("<\\/", "</")).get("@type")
                 for p in re.findall(r'<script type="application/ld\+json">(.*?)</script>', t)]
        assert "LodgingBusiness" in types
        assert "BreadcrumbList" in types


# 8. Controlled sample contains only the selected records.
def test_sample_contains_only_selected_records(sample):
    slugs = {p.parent.name for p in (sample / "pet-friendly-hotels").glob("*/index.html")}
    assert slugs == _EXPECTED_SLUGS


# 9. Deterministic output.
def test_deterministic_output(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    run_sample(str(a))
    run_sample(str(b))
    for slug in _EXPECTED_SLUGS:
        assert (a / "pet-friendly-hotels" / slug / "index.html").read_bytes() == \
               (b / "pet-friendly-hotels" / slug / "index.html").read_bytes()


# 10. Non-hotel page rendering path remains unchanged.
def test_non_hotel_path_unchanged():
    # The full generator still routes parks/restaurants through enrich_place_profile;
    # the PTF-PROD-002 change is confined to the hotel loop.
    from scripts import generate_pettripfinder_columbus_site as gen
    src = inspect.getsource(gen.run)
    assert "enrich_place_profile" in src           # non-hotel path intact
    assert "render_production_hotel_profile" in src  # hotels via approved renderer


# 11. No "nearby" label without coordinates.
def test_no_nearby_without_coordinates(sample):
    for slug in _EXPECTED_SLUGS:
        t = _hotel(sample, slug).lower()
        assert "also in" not in t          # the old same-city nearby phrasing
        assert "miles away" not in t and "km away" not in t
        assert "distance-based recommendations aren’t available" in t


# 12. Inventory remains unchanged by generation.
def test_inventory_unchanged(sample):
    before = hashlib.sha256(PRODUCTION_CSV.read_bytes()).hexdigest()
    run_sample(str(sample.parent / "again"))
    after = hashlib.sha256(PRODUCTION_CSV.read_bytes()).hexdigest()
    assert before == after


# 13. The normal sample sources verified facts from the tracked package, and the
# tracked package carries no operational/private metadata.
def test_published_package_is_the_default_source(sample):
    from scripts.pettripfinder.site_data import (
        PUBLISHED_FACTS_PATH, load_published_hotel_policy_facts)
    facts = load_published_hotel_policy_facts()
    assert facts, "tracked publishable package must be present and non-empty"
    pkg = json.loads(PUBLISHED_FACTS_PATH.read_text(encoding="utf-8"))
    for h in pkg["hotels"]:
        # publishable identity/state/fields only -- never operational internals
        assert set(h).issubset({
            "key", "name", "verification_state", "facts", "evidence_quote",
            "verified_at", "source_url", "source_type", "evidence_count"})
        assert "candidate_id" not in h and "candidate_path" not in h
