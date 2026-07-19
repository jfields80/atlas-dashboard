"""AES-SITE-001 -- comparison/corridor/methodology page generator tests.
No network."""

from __future__ import annotations

import json
import re

from scripts.pettripfinder.site_pages import (
    build_comparison_page,
    build_corridor_page,
    build_methodology_page,
)

_ROWS = [
    {"name": "B Hotel", "route": "/pet-friendly-hotels/b-hotel/", "area": "Columbus, OH",
     "species_allowed": "dogs and cats", "pet_fee": "$50", "fee_basis": "per night",
     "pet_count_limit": "2", "weight_limit": "", "verified_at": "2026-07-18"},
    {"name": "A Hotel", "route": "/pet-friendly-hotels/a-hotel/", "area": "Dublin, OH",
     "species_allowed": "", "pet_fee": "", "fee_basis": "", "pet_count_limit": "",
     "weight_limit": "", "verified_at": ""},
]


def test_comparison_page_sorted_alphabetically_not_input_order():
    page = build_comparison_page(_ROWS)
    a_pos = page.index("A Hotel")
    b_pos = page.index("B Hotel")
    assert a_pos < b_pos


def test_comparison_page_shows_not_stated_for_missing_fields():
    page = build_comparison_page(_ROWS)
    assert "Not stated" in page
    assert "$50" in page


def test_comparison_page_never_claims_best():
    page = build_comparison_page(_ROWS)
    for banned in ("best hotel", "top pick", "#1", "guaranteed"):
        assert banned not in page.lower()


def test_comparison_page_links_to_every_hotel():
    page = build_comparison_page(_ROWS)
    assert '/pet-friendly-hotels/a-hotel/' in page
    assert '/pet-friendly-hotels/b-hotel/' in page


def test_comparison_page_has_valid_json_ld():
    page = build_comparison_page(_ROWS)
    payloads = re.findall(r'<script type="application/ld\+json">(.*?)</script>', page)
    assert payloads
    for p in payloads:
        json.loads(p.replace("<\\/", "</"))


def test_comparison_page_indexable_by_default():
    page = build_comparison_page(_ROWS)
    assert 'name="robots" content="index, follow"' in page


def test_corridor_page_lists_only_supplied_hotels():
    page = build_corridor_page("Dublin", "dublin", [_ROWS[1]])
    assert "A Hotel" in page
    assert "B Hotel" not in page
    assert "Dublin" in page


def test_corridor_page_route_and_canonical():
    page = build_corridor_page("Dublin", "dublin", [_ROWS[1]])
    assert 'href="https://pettripfinder.com/pet-friendly-hotels/dublin/"' in page


def test_methodology_page_describes_real_verification_not_stale_text():
    page = build_methodology_page()
    assert "we do not currently operate a formal verification program" not in page.lower()
    assert "Policy verified" in page
    assert "service-animal" in page.lower() or "service animal" in page.lower()
    assert "never fabricate" in page.lower()


def test_methodology_page_linked_route():
    page = build_methodology_page()
    assert 'href="https://pettripfinder.com/methodology/"' in page
