"""AES-DATA-001 -- entity-name canonicalization and precedence (live park-
name defect). A page/OG title carrying site branding is not a material
conflict with the clean entity name; genuinely different names still
conflict. No network."""

from __future__ import annotations

import pytest

from repositories.artifact_store_repository import ArtifactStoreRepository
from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer import normalize as N
from scripts.pettripfinder.importer.candidate import run_import
from scripts.pettripfinder.importer.extraction import StaticFactExtractor
from scripts.pettripfinder.importer.fetch import StaticPageFetcher
from scripts.pettripfinder.importer.models import ImportContext

_URL = "https://www.metroparks.net/parks-and-trails/scioto-audubon"


def _run(og_title, llm_name, tmp_path, *, candidate_name="", extra_body=""):
    html = (
        "<!doctype html><html><head>"
        '<meta property="og:title" content="%s">'
        '<meta property="og:url" content="%s">'
        "</head><body><h1>%s</h1>"
        "<p>400 W Whittier Street, Columbus, OH 43215</p><p>P: 614-202-5197</p>"
        "<p>Fenced dog park with separate areas for large dogs and small dogs. "
        "Elsewhere pets must be on a leash no longer than 6 feet.</p>%s"
        "</body></html>" % (og_title, _URL, llm_name, extra_body))
    fetcher = StaticPageFetcher()
    fetcher.add_html(_URL, html)
    extractor = StaticFactExtractor({"facts": [
        {"field": "name", "value": llm_name, "quote": llm_name},
        {"field": "pets_allowed", "value": "true", "quote": "Fenced dog park"},
        {"field": "address", "value": "400 W Whittier Street, Columbus, OH 43215",
         "quote": "400 W Whittier Street, Columbus, OH 43215"},
        {"field": "phone", "value": "614-202-5197", "quote": "P: 614-202-5197"},
        {"field": "fenced", "value": "true", "quote": "Fenced dog park"},
        {"field": "small_dog_area", "value": "true",
         "quote": "separate areas for large dogs and small dogs"},
        {"field": "large_dog_area", "value": "true",
         "quote": "separate areas for large dogs and small dogs"},
        {"field": "leash_rule", "value": "pets must be on a leash no longer than 6 feet",
         "quote": "pets must be on a leash no longer than 6 feet"},
    ]})
    cas = ArtifactStoreRepository(tmp_path / "cas")
    ctx = ImportContext(category="parks", expected_city="Columbus",
                        expected_state="OH", candidate_name=candidate_name)
    return run_import(_URL, ctx, fetcher=fetcher, extractor=extractor, cas=cas,
                      observed_at="2026-07-16", created_at="1970-01-01T00:00:00")


# --------------------------------------------------------------------------- #
# Canonicalization unit tests.
# --------------------------------------------------------------------------- #

class TestNameCanonicalization:
    @pytest.mark.parametrize("branded", [
        "Scioto Audubon - Metro Parks - Central Ohio Park System",   # hyphen
        "Scioto Audubon | Metro Parks",                              # pipe
        "Metro Parks: Scioto Audubon",                               # prefix
        "Scioto Audubon — Central Ohio Park System",            # em dash
    ])
    def test_branded_title_compatible_with_entity(self, branded):
        assert N.names_compatible("Scioto Audubon", branded) is True

    def test_clean_entity_strips_branding(self):
        assert N.clean_entity_name(
            "Scioto Audubon - Metro Parks - Central Ohio Park System") == "Scioto Audubon"
        assert N.clean_entity_name("Metro Parks: Scioto Audubon") == "Scioto Audubon"

    @pytest.mark.parametrize("a,b", [
        ("Scioto Audubon", "Battelle Darby Creek"),
        ("Scioto Audubon", "Scioto Grove"),
        ("Scioto Audubon Park", "Scioto Audubon Hotel"),
        ("Scioto Audubon", "Old Scioto Audubon Trailhead Foundation"),  # partial overlap
    ])
    def test_genuinely_different_names_conflict(self, a, b):
        assert N.names_compatible(a, b) is False


# --------------------------------------------------------------------------- #
# Pipeline tests.
# --------------------------------------------------------------------------- #

class TestNameResolutionPipeline:
    def test_branded_og_no_conflict_and_ready(self, tmp_path):
        c = _run("Scioto Audubon - Metro Parks - Central Ohio Park System",
                 "Scioto Audubon", tmp_path)
        assert not any(cf.field_name == "name" for cf in c.conflicts)
        assert dict(c.proposed_fields)["name"] == "Scioto Audubon"
        assert c.recommendation == C.RECOMMEND_READY
        # Both source values preserved as name evidence.
        methods = {w for e in c.evidence if e.field_name == "name" for w in e.warnings}
        assert "name_source:OPEN_GRAPH" in methods
        assert "name_source:LLM_TEXT" in methods

    def test_operator_hint_matching_page_evidence(self, tmp_path):
        c = _run("Scioto Audubon - Metro Parks - Central Ohio Park System",
                 "Scioto Audubon", tmp_path,
                 candidate_name="Scioto Audubon Metro Park",
                 extra_body="<p>Welcome to Scioto Audubon Metro Park.</p>")
        assert dict(c.proposed_fields)["name"] == "Scioto Audubon Metro Park"
        assert c.recommendation == C.RECOMMEND_READY

    def test_unrelated_names_still_conflict(self, tmp_path):
        c = _run("Battelle Darby Creek - Metro Parks - Central Ohio Park System",
                 "Scioto Audubon", tmp_path)
        assert any(cf.field_name == "name" for cf in c.conflicts)
        assert c.recommendation == C.RECOMMEND_REVIEW

    def test_partial_overlap_still_conflicts(self, tmp_path):
        c = _run("Scioto Audubon - Metro Parks", "Scioto Audubon Preserve", tmp_path)
        assert any(cf.field_name == "name" for cf in c.conflicts)
        assert c.recommendation == C.RECOMMEND_REVIEW


def test_scioto_audubon_full_candidate_ready(tmp_path):
    """Mission requirements 6/7: the full Scioto Audubon candidate is READY
    with every supported field, no name conflict."""
    c = _run("Scioto Audubon - Metro Parks - Central Ohio Park System",
             "Scioto Audubon", tmp_path)
    p = dict(c.proposed_fields)
    f = dict(c.pet_facts)
    assert p["name"] == "Scioto Audubon"
    assert p["address"] == "400 W Whittier Street"
    assert p["city"] == "Columbus" and p["state"] == "OH"
    assert p["postal_code"] == "43215"
    assert p["phone"] == "614-202-5197"
    assert f.get("fenced") == "true"
    assert f.get("small_dog_area") == "true" and f.get("large_dog_area") == "true"
    assert bool(f.get("leash_rule"))
    assert not any(cf.field_name == "name" for cf in c.conflicts)
    assert c.recommendation == C.RECOMMEND_READY
