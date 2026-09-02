"""Shared fixtures for Launch Kit tests."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

import pytest

# Make the repository root importable when running pytest from anywhere.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture
def full_blueprint() -> Dict[str, Any]:
    """A representative Phase 3A-style blueprint with every tracked section."""
    return {
        "project_profile": {
            "name": "Pet Trip Finder",
            "niche": "pet-friendly travel",
        },
        "seo_blueprint": {
            "url_map": [
                {"url": "/", "page_type": "home", "notes": "Homepage"},
                {
                    "url": "/hotels/",
                    "page_type": "category",
                    "notes": "Pet-friendly hotels",
                },
                {
                    "url": "/columbus-oh/hotels/",
                    "page_type": "location_category",
                },
            ],
            "pages": [
                {
                    "url": "/hotels/",
                    "page_type": "category",
                    "title": "Pet-Friendly Hotels",
                    "meta_description": "Find hotels that welcome pets.",
                    "primary_keyword": "pet friendly hotels",
                    "secondary_keywords": ["dog friendly hotels", "pet hotels"],
                    "priority": 1,
                },
                {
                    "url": "/",
                    "page_type": "home",
                    "title": "Pet Trip Finder",
                    "meta_description": "Plan trips with your pet.",
                    "primary_keyword": "pet friendly travel",
                    "priority": 1,
                },
            ],
        },
        "content_strategy": {
            "items": [
                {
                    "title": "10 Best Dog-Friendly Hotels in Columbus",
                    "content_type": "listicle",
                    "target_keyword": "dog friendly hotels columbus",
                    "priority": 1,
                },
                {
                    "title": "How to Road Trip With a Cat",
                    "content_type": "guide",
                    "target_keyword": "road trip with cat",
                    "priority": 2,
                },
            ]
        },
        "monetization_plan": {
            "primary_model": "featured_listings",
            "secondary_models": ["affiliate_booking", "display_ads"],
            "target_first_dollar_days": 30,
        },
        "ai_task_definitions": [
            {
                "name": "Write category page intros",
                "task_type": "content_generation",
                "phase": "content",
                "depends_on": [],
                "priority": 1,
            },
            {
                "task_id": "CUSTOM-2",
                "name": "Enrich listings with amenities",
                "task_type": "enrichment",
                "phase": "data",
                "depends_on": ["T001"],
                "priority": 2,
            },
        ],
        "roadmap": {
            "phases": [
                {
                    "name": "Foundation",
                    "tasks": ["Set up hosting", "Configure domain"],
                },
                {
                    "name": "Data",
                    "tasks": [
                        {"title": "Import seed listings"},
                        "Verify top 20 listings",
                    ],
                },
                {"name": "Empty Phase", "tasks": []},
            ]
        },
        "risk_analysis": {
            "risks": [
                {
                    "name": "Thin content penalty",
                    "severity": "high",
                    "mitigation": "Minimum 300 words per category page",
                },
                {"name": "Data staleness", "severity": "medium"},
            ]
        },
    }


@pytest.fixture
def full_seed_package() -> Dict[str, Any]:
    """A representative Phase 3B-style seed package."""
    return {
        "listings": [
            {
                "id": "L001",
                "name": "The Barkley Hotel",
                "category": "Hotels",
                "city": "Columbus",
                "state": "OH",
                "website": "https://example.com/barkley",
                "rating": 4.5,
                "amenities": ["dog park", "pet spa"],
            },
            {
                "id": "L002",
                "name": "Paws Inn",
                "category": "Hotels",
                "city": "Dublin",
                "state": "OH",
                "phone": "614-555-0100",
            },
            {
                "id": "L003",
                "name": "Whisker Campground",
                "category": "Campgrounds",
                "city": "Columbus",
                "state": "OH",
            },
        ],
        "categories": [
            {"name": "Hotels", "listing_count": 2},
            {"name": "Campgrounds", "listing_count": 1},
        ],
        "locations": [
            {"name": "Columbus", "state": "OH"},
            {"name": "Dublin", "state": "OH"},
        ],
        "data_quality": {
            "verified_count": 1,
            "estimated_count": 2,
            "duplicate_groups": 0,
        },
    }


@pytest.fixture
def sparse_blueprint() -> Dict[str, Any]:
    """A blueprint with no optional sections at all."""
    return {"project_profile": {"name": "Sparse Project"}}


@pytest.fixture
def sparse_seed_package() -> Dict[str, Any]:
    """A seed package with no explicit sections at all."""
    return {}


# --------------------------------------------------------------------------- #
# PTF-FACTORY-THROUGHPUT-HARDENING-001 -- test lanes.
#
# Lane and market markers come from ONE committed table
# (scripts/pettripfinder/regression_lanes.py) and are applied here at
# collection, so `-m policy_schema` and `--ptf-market dayton-oh` select the
# same modules the lane runner would run. Nothing outside tests/pettripfinder
# is marked.
# --------------------------------------------------------------------------- #

DASHBOARD_ROOT = Path(__file__).resolve().parent
if str(DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_ROOT))


def pytest_addoption(parser):
    group = parser.getgroup("pettripfinder")
    group.addoption("--ptf-market", action="store", default=None,
                    help="run only the tests in this market's targeted lane "
                         "(its own modules plus the per-market contract rows)")


def pytest_collection_modifyitems(config, items):
    from scripts.pettripfinder import regression_lanes as LANES

    wanted_market = config.getoption("--ptf-market")
    ptf_root = LANES.PTF_TESTS.resolve()
    keep, drop = [], []
    for item in items:
        try:
            rel = Path(str(item.fspath)).resolve().relative_to(ptf_root).as_posix()
        except ValueError:
            if wanted_market:
                drop.append(item)
            else:
                keep.append(item)
            continue
        lanes = LANES.lanes_for(rel)
        for lane in lanes:
            item.add_marker(getattr(pytest.mark, lane))
        market = LANES.market_for(rel)
        if market:
            item.add_marker(pytest.mark.ptf_market(market))
        if wanted_market:
            targeted = (market == wanted_market
                        or rel in LANES.PER_MARKET_CONTRACT_MODULES)
            (keep if targeted else drop).append(item)
        else:
            keep.append(item)
    if wanted_market:
        items[:] = keep
        config.hook.pytest_deselected(items=drop)
