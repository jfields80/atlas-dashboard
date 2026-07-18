"""AES-DATA-002A -- source-set contracts and per-source seam (behavior-
preserving foundation). This phase adds additive multi-source data contracts
(``SourceRecord`` on ``CandidateListing``) and mechanically splits per-page
evidence collection (``_collect_page_evidence`` -> ``PageEvidence``) from
candidate-level resolution (``_resolve_page_fields``), plus a new
``import_source`` primitive. No aggregation, identity gate, or merging logic
exists yet -- these tests prove the split and the new contracts change
NOTHING about the existing single-URL importer's observable behavior, and
that legacy candidate JSON keeps loading. No network."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from repositories.artifact_store_repository import ArtifactStoreRepository
from scripts.import_official_url import _build_static
from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.candidate import (
    PageEvidence,
    SourceImportResult,
    _assemble,
    _collect_page_evidence,
    _resolve_page_fields,
    candidate_from_dict,
    candidate_to_dict,
    dumps_candidate,
    import_source,
    run_import,
)
from scripts.pettripfinder.importer.category_templates import allowed_fields
from scripts.pettripfinder.importer.extraction import StaticFactExtractor
from scripts.pettripfinder.importer.fetch import StaticPageFetcher
from scripts.pettripfinder.importer.models import (
    CandidateListing,
    ImportContext,
    SourceRecord,
    SourceSnapshot,
)
from scripts.pettripfinder.importer.source_snapshot import build_snapshot
from scripts.pettripfinder.importer.structured_metadata import extract_structured_metadata

_FIXTURES = Path(__file__).parent / "fixtures"


def _context_from(obj: dict) -> ImportContext:
    ctx = obj.get("context", {})
    return ImportContext(
        category=ctx.get("category", ""), expected_city=ctx.get("expected_city", ""),
        expected_state=ctx.get("expected_state", ""),
        candidate_name=ctx.get("candidate_name", ""),
        source_type_hint=ctx.get("source_type_hint", ""),
        source_relationship_hint=ctx.get("source_relationship_hint", ""))


def _load_fixture(name: str):
    """Return ``(url, context, fetcher, extractor)`` for a gold fixture."""
    obj = json.loads((_FIXTURES / name).read_text(encoding="utf-8"))
    url = obj["url"]
    fetcher, extractor = _build_static(url, str(_FIXTURES / name))
    return (url, _context_from(obj), fetcher, extractor)


# --------------------------------------------------------------------------- #
# A. PageEvidence parity.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("fixture", [
    "hotel_01_strong.json", "park_01_offleash.json", "restaurant_01_patio.json",
])
class TestPageEvidenceParity:
    def _manual_collect(self, fixture, tmp_path):
        """Replicate the pre-seam fetch -> snapshot -> structured -> extract
        preamble by hand, then call the split primitives directly."""
        url, ctx, fetcher, extractor = _load_fixture(fixture)
        cas = ArtifactStoreRepository(tmp_path / "cas")
        fetch = fetcher.fetch(url)
        assert fetch.ok
        snapshot = build_snapshot(fetch, cas, "2026-07-17", C.REL_UNKNOWN)
        html_bytes = cas.get_bytes(snapshot.raw_content_hash)
        structured = extract_structured_metadata(html_bytes.decode("utf-8"))
        extraction = extractor.extract(
            snapshot.normalized_text, ctx.category, allowed_fields(ctx.category))
        return (url, ctx, snapshot, structured, extraction)

    def test_collect_then_resolve_equals_assemble(self, fixture, tmp_path):
        url, ctx, snapshot, structured, extraction = self._manual_collect(fixture, tmp_path)
        source_url = snapshot.final_url

        page = _collect_page_evidence(
            snapshot, structured, extraction.facts, ctx.category, source_url, ctx)
        assert isinstance(page, PageEvidence)
        # Collection never resolves a final name/phone.
        assert "name" not in page.accepted
        assert "phone" not in page.accepted

        split_result = _resolve_page_fields(page, snapshot, ctx.category, source_url, ctx)
        direct_result = _assemble(
            snapshot, structured, extraction.facts, ctx.category, source_url, ctx)

        split_evidence, split_conflicts, split_accepted, split_mismatch = split_result
        direct_evidence, direct_conflicts, direct_accepted, direct_mismatch = direct_result

        assert split_evidence == direct_evidence
        assert split_conflicts == direct_conflicts
        assert split_accepted == direct_accepted
        assert split_mismatch == direct_mismatch

    def test_public_candidate_fields_match_expected(self, fixture, tmp_path):
        obj = json.loads((_FIXTURES / fixture).read_text(encoding="utf-8"))
        url, ctx, fetcher, extractor = _load_fixture(fixture)
        cas = ArtifactStoreRepository(tmp_path / "cas2")
        candidate = run_import(
            url, ctx, fetcher=fetcher, extractor=extractor, cas=cas,
            observed_at="2026-07-17", created_at="1970-01-01T00:00:00")
        assert candidate.recommendation == obj["expected_recommendation"]

        # Cross-check: the split primitives over a FRESH cas reproduce the
        # exact evidence/conflict tuples the full pipeline finalized (no
        # postal derivation fires for these fixtures, so no divergence).
        url2, ctx2, snapshot, structured, extraction = self._manual_collect(fixture, tmp_path)
        page = _collect_page_evidence(
            snapshot, structured, extraction.facts, ctx2.category, snapshot.final_url, ctx2)
        evidence, conflicts, accepted, _mismatch = _resolve_page_fields(
            page, snapshot, ctx2.category, snapshot.final_url, ctx2)
        assert tuple(evidence) == candidate.evidence
        assert tuple(conflicts) == candidate.conflicts
        assert accepted.get("name") == dict(candidate.proposed_fields)["name"]


# --------------------------------------------------------------------------- #
# B. import_source parity.
# --------------------------------------------------------------------------- #

_SCIOTO_URL = "https://www.metroparks.net/parks-and-trails/scioto-audubon"


def _scioto_static():
    html = (
        "<!doctype html><html><head>"
        '<meta property="og:title" content="Scioto Audubon - Metro Parks - '
        'Central Ohio Park System">'
        '<meta property="og:url" content="%s">'
        "</head><body><h1>Scioto Audubon</h1>"
        "<p>400 W Whittier Street, Columbus, OH 43215</p><p>P: 614-202-5197</p>"
        "<p>Fenced dog park with separate areas for large dogs and small dogs.</p>"
        "</body></html>" % _SCIOTO_URL)
    fetcher = StaticPageFetcher()
    fetcher.add_html(_SCIOTO_URL, html)
    extractor = StaticFactExtractor({"facts": [
        {"field": "name", "value": "Scioto Audubon", "quote": "Scioto Audubon"},
        {"field": "pets_allowed", "value": "true", "quote": "Fenced dog park"},
        {"field": "address", "value": "400 W Whittier Street, Columbus, OH 43215",
         "quote": "400 W Whittier Street, Columbus, OH 43215"},
        {"field": "phone", "value": "614-202-5197", "quote": "P: 614-202-5197"},
        {"field": "fenced", "value": "true", "quote": "Fenced dog park"},
    ]})
    ctx = ImportContext(category="parks", expected_city="Columbus", expected_state="OH")
    return (_SCIOTO_URL, ctx, fetcher, extractor)


_LANDGRANT_URL = "https://landgrantbrewing.com/faq/"


def _landgrant_live_replay_static():
    """The exact live-payload shape (AES-DATA-001 live regression): a SINGLE
    LLM name fact whose value is the short brand form, quoted from the h1's
    full name -- the case that drove the expected-city suffix repair."""
    html = (
        "<!doctype html><html><head>"
        '<meta property="og:title" content="FAQ | Land-Grant Brewing Columbus '
        '| Hours, Parking &amp; More">'
        '<meta property="og:url" content="%s">'
        "</head><body><h1>Land-Grant Brewing Columbus</h1>"
        "<p>Well-behaved dogs are welcome in our beer garden and on the "
        "patio. Dogs are not able to join you inside our Wintergarden "
        "Igloos.</p></body></html>" % _LANDGRANT_URL)
    fetcher = StaticPageFetcher()
    fetcher.add_html(_LANDGRANT_URL, html)
    extractor = StaticFactExtractor({"facts": [
        {"field": "name", "value": "Land-Grant Brewing",
         "quote": "Land-Grant Brewing Columbus"},
        {"field": "pets_allowed", "value": "true",
         "quote": "Well-behaved dogs are welcome in our beer garden and on the patio"},
        {"field": "patio_or_outdoor_only", "value": "true",
         "quote": "Well-behaved dogs are welcome in our beer garden and on the patio"},
        {"field": "indoor_prohibited", "value": "true",
         "quote": "Dogs are not able to join you inside our Wintergarden Igloos"},
    ]})
    ctx = ImportContext(
        category="restaurants", expected_city="Columbus", expected_state="OH",
        candidate_name="Land-Grant Brewing Columbus",
        source_relationship_hint="EXACT_ENTITY_DOMAIN")
    return (_LANDGRANT_URL, ctx, fetcher, extractor)


def _hotel_01_static():
    return _load_fixture("hotel_01_strong.json")


class TestImportSourceParity:
    @pytest.mark.parametrize("build", [
        _hotel_01_static,
        _scioto_static,
        _landgrant_live_replay_static,
    ], ids=["hotel_01_strong", "scioto_branded_park", "landgrant_live_replay"])
    def test_import_source_matches_run_import(self, build, tmp_path):
        url, ctx, fetcher, extractor = build()
        cas = ArtifactStoreRepository(tmp_path / "cas")

        source = import_source(
            url, ctx, fetcher=fetcher, extractor=extractor, cas=cas,
            observed_at="2026-07-17")
        assert isinstance(source, SourceImportResult)
        assert source.usable is True
        assert source.snapshot is not None
        assert source.page_evidence is not None
        assert source.extraction_provider in ("static", "")

        candidate = run_import(
            url, ctx, fetcher=fetcher, extractor=extractor, cas=cas,
            observed_at="2026-07-17", created_at="1970-01-01T00:00:00")

        assert candidate.source_relationship == source.source_relationship
        assert candidate.source_relationship_reason == source.source_relationship_reason
        assert candidate.extraction_provider == source.extraction_provider
        assert candidate.extraction_model == source.extraction_model
        assert candidate.prompt_version == source.prompt_version
        assert candidate.snapshot.raw_content_hash == source.snapshot.raw_content_hash
        assert candidate.snapshot.normalized_text_hash == source.snapshot.normalized_text_hash


# --------------------------------------------------------------------------- #
# C. Serialization.
# --------------------------------------------------------------------------- #

def _hotel_candidate(tmp_path):
    url, ctx, fetcher, extractor = _load_fixture("hotel_01_strong.json")
    cas = ArtifactStoreRepository(tmp_path / "cas")
    return run_import(url, ctx, fetcher=fetcher, extractor=extractor, cas=cas,
                      observed_at="2026-07-17", created_at="1970-01-01T00:00:00")


class TestSerialization:
    def test_default_round_trip(self, tmp_path):
        c = _hotel_candidate(tmp_path)
        assert c.sources == ()
        assert c.aggregation_version == ""
        reloaded = candidate_from_dict(json.loads(dumps_candidate(c)))
        assert reloaded == c

    def test_single_source_omits_new_keys(self, tmp_path):
        c = _hotel_candidate(tmp_path)
        d = candidate_to_dict(c)
        assert "sources" not in d
        assert "aggregation_version" not in d

    def test_synthetic_two_source_round_trip(self, tmp_path):
        c = _hotel_candidate(tmp_path)
        rec_a = SourceRecord(
            source_id="S1", requested_url="https://a.test/faq",
            final_url="https://a.test/faq", role=C.SOURCE_ROLE_PRIMARY,
            usable=True, fetch_reason="", excluded_reason="",
            source_relationship=C.REL_EXACT_ENTITY_DOMAIN,
            source_relationship_reason="operator_hint", snapshot=None,
            extraction_provider="static", extraction_model="static-fixture",
            prompt_version="1.0.0", warnings=("normalized_text_truncated_50kb",))
        rec_b = SourceRecord(
            source_id="S2", requested_url="https://a.test/contact",
            final_url="https://a.test/contact", role=C.SOURCE_ROLE_SUPPLEMENTAL,
            usable=False, fetch_reason=C.REASON_BLOCKED_SOURCE,
            excluded_reason="", source_relationship="", source_relationship_reason="",
            snapshot=None)
        aggregate = replace(c, sources=(rec_a, rec_b), aggregation_version=C.AGGREGATION_VERSION)

        d = candidate_to_dict(aggregate)
        assert d["aggregation_version"] == C.AGGREGATION_VERSION
        assert [s["source_id"] for s in d["sources"]] == ["S1", "S2"]

        reloaded = candidate_from_dict(json.loads(json.dumps(d)))
        assert reloaded.sources == (rec_a, rec_b)
        assert reloaded.aggregation_version == C.AGGREGATION_VERSION
        assert reloaded == aggregate

    def test_source_record_with_snapshot_round_trip(self, tmp_path):
        c = _hotel_candidate(tmp_path)
        rec = SourceRecord(
            source_id="S1", requested_url=c.snapshot.requested_url,
            final_url=c.snapshot.final_url, role=C.SOURCE_ROLE_PRIMARY,
            usable=True, fetch_reason="", excluded_reason="",
            source_relationship=c.source_relationship,
            source_relationship_reason=c.source_relationship_reason,
            snapshot=c.snapshot)
        aggregate = replace(c, sources=(rec,), aggregation_version=C.AGGREGATION_VERSION)
        reloaded = candidate_from_dict(json.loads(dumps_candidate(aggregate)))
        assert reloaded.sources[0].snapshot == c.snapshot
        assert reloaded == aggregate

    def test_deterministic_repeated_dumps(self, tmp_path):
        c = _hotel_candidate(tmp_path)
        assert dumps_candidate(c) == dumps_candidate(c)

        rec = SourceRecord(
            source_id="S1", requested_url="https://a.test/faq",
            final_url="https://a.test/faq", role=C.SOURCE_ROLE_PRIMARY,
            usable=True, fetch_reason="", excluded_reason="",
            source_relationship=C.REL_EXACT_ENTITY_DOMAIN,
            source_relationship_reason="operator_hint", snapshot=None)
        aggregate = replace(c, sources=(rec,), aggregation_version=C.AGGREGATION_VERSION)
        assert dumps_candidate(aggregate) == dumps_candidate(aggregate)
        # LF line endings, sorted keys: no CRs, alphabetical top-level keys.
        blob = dumps_candidate(aggregate)
        assert "\r" not in blob


# --------------------------------------------------------------------------- #
# D. Legacy compatibility.
# --------------------------------------------------------------------------- #

class TestLegacyCompatibility:
    def test_old_shape_dict_has_no_new_keys(self, tmp_path):
        c = _hotel_candidate(tmp_path)
        d = candidate_to_dict(c)
        assert "sources" not in d
        assert "aggregation_version" not in d

    def test_old_shape_dict_loads_with_defaults(self, tmp_path):
        c = _hotel_candidate(tmp_path)
        old_shape = candidate_to_dict(c)
        assert "sources" not in old_shape and "aggregation_version" not in old_shape
        reloaded = candidate_from_dict(old_shape)
        assert reloaded.sources == ()
        assert reloaded.aggregation_version == ""
        assert reloaded == c

    def test_pre_002_json_string_loads(self, tmp_path):
        """A literal pre-AES-DATA-002 JSON blob (no sources/aggregation_version
        keys anywhere, as every candidate persisted before this phase looks)
        still loads cleanly."""
        c = _hotel_candidate(tmp_path)
        raw = json.loads(dumps_candidate(c))
        assert "sources" not in raw
        assert "aggregation_version" not in raw
        reloaded = candidate_from_dict(raw)
        assert reloaded.sources == ()
        assert reloaded.aggregation_version == ""


# --------------------------------------------------------------------------- #
# E. No new behavior: no aggregate reason slug from any existing single-
# source path, across every gold fixture in the suite.
# --------------------------------------------------------------------------- #

_AGGREGATE_REASON_SLUGS = frozenset({
    C.REASON_IDENTITY_CONFLICT, C.REASON_GEOGRAPHY_CONFLICT,
    C.REASON_POLICY_CONFLICT, C.REASON_INCOMPLETE_SOURCE_SET,
})


class TestNoNewBehavior:
    @pytest.mark.parametrize("fixture_path", sorted(_FIXTURES.glob("*.json")),
                             ids=lambda p: p.stem)
    def test_no_aggregate_reason_emitted(self, fixture_path, tmp_path):
        obj = json.loads(fixture_path.read_text(encoding="utf-8"))
        if "expected_recommendation" not in obj:
            pytest.skip("not a gold fixture")
        url = obj.get("url", "https://example.test/%s" % fixture_path.stem)
        fetcher, extractor = _build_static(url, str(fixture_path))
        cas = ArtifactStoreRepository(tmp_path / "cas")
        candidate = run_import(
            url, _context_from(obj), fetcher=fetcher, extractor=extractor, cas=cas,
            observed_at="2026-07-17", created_at="1970-01-01T00:00:00")
        assert candidate.recommendation == obj["expected_recommendation"]
        assert not (set(candidate.recommendation_reasons) & _AGGREGATE_REASON_SLUGS)
        assert candidate.sources == ()
        assert candidate.aggregation_version == ""


# --------------------------------------------------------------------------- #
# AES-DATA-003E live-validation defect: a structured (JSON-LD ``streetAddress``,
# already street-only) address and an LLM-extracted address quoting the
# page's own full "street, city, state zip" text line were compared BEFORE
# either had its locality tail stripped (city/state aren't resolved yet at
# this point in the pipeline) -- so the exact same real-world address was
# reported as a material ``conflicting_evidence`` conflict purely from
# formatting (trailing ", City, ST ZIP" present on one side, absent or
# differently punctuated on the other). Observed live across 5 of 8 real
# Columbus businesses in the 003E validation run (MedVet Columbus, Pet
# Palace, Designer Paws Salon, Fangs & Fur, Petco Weinland Park), each
# correctly publishing a clean final address despite the spurious conflict
# -- proving the defect was in conflict DETECTION, not in what eventually
# got published. Fixed via ``_same_address`` (candidate.py): the two values
# are re-normalized with the operator's expected_city/expected_state before
# a genuine conflict is recorded.
# --------------------------------------------------------------------------- #

class TestAddressConflictFalsePositive:
    _URL = "https://www.samestreetaddress.test/"

    def _static(self, structured_street: str, llm_full_line: str):
        html = (
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<script type=\"application/ld+json\">{\"@context\": "
            "\"https://schema.org\", \"@type\": \"VeterinaryCare\", "
            "\"name\": \"Same Street Address Clinic\", \"telephone\": "
            "\"614-555-0100\", \"url\": \"%s\", \"address\": {\"@type\": "
            "\"PostalAddress\", \"streetAddress\": \"%s\", "
            "\"addressLocality\": \"Worthington\", \"addressRegion\": \"OH\", "
            "\"postalCode\": \"43085\"}}</script></head>"
            "<body><h1>Same Street Address Clinic</h1>"
            "<p>Address: %s</p>"
            "<p>We provide general veterinary practice services.</p>"
            "</body></html>"
        ) % (self._URL, structured_street, llm_full_line)
        fetcher = StaticPageFetcher()
        fetcher.add_html(self._URL, html)
        extractor = StaticFactExtractor({"facts": [
            {"field": "general_practice", "value": "true",
             "quote": "We provide general veterinary practice services"},
            {"field": "address", "value": llm_full_line,
             "quote": "Address: %s" % llm_full_line},
        ]})
        ctx = ImportContext(
            category="veterinary", expected_city="Worthington", expected_state="OH")
        return (self._URL, ctx, fetcher, extractor)

    def _run(self, structured_street, llm_full_line, tmp_path):
        url, ctx, fetcher, extractor = self._static(structured_street, llm_full_line)
        cas = ArtifactStoreRepository(tmp_path / "cas")
        return run_import(url, ctx, fetcher=fetcher, extractor=extractor, cas=cas,
                          observed_at="2026-07-18", created_at="1970-01-01T00:00:00")

    def test_comma_before_locality_is_not_a_conflict(self, tmp_path):
        # Structured: street-only. LLM: full line, comma before city (the
        # exact MedVet Columbus live shape).
        c = self._run(
            "300 E. Wilson Bridge Rd.",
            "300 E. Wilson Bridge Rd., Worthington, OH 43085", tmp_path)
        assert not any(cf.field_name == "address" for cf in c.conflicts)
        assert dict(c.proposed_fields)["address"] == "300 E. Wilson Bridge Rd."

    def test_period_before_locality_is_not_a_conflict(self, tmp_path):
        # The Pet Palace/Designer Paws/Fangs & Fur/Petco live shape: no
        # comma at all before the city name.
        c = self._run(
            "300 E. Wilson Bridge Rd.",
            "300 E. Wilson Bridge Rd. Worthington, OH 43085", tmp_path)
        assert not any(cf.field_name == "address" for cf in c.conflicts)
        assert dict(c.proposed_fields)["address"] == "300 E. Wilson Bridge Rd."

    def test_genuinely_different_street_is_still_a_conflict(self, tmp_path):
        # A real disagreement (different street number) must still be
        # caught -- this fix narrows a false positive, it never weakens
        # genuine conflict detection.
        c = self._run(
            "300 E. Wilson Bridge Rd.",
            "425 Some Other Street, Worthington, OH 43085", tmp_path)
        address_conflicts = [cf for cf in c.conflicts if cf.field_name == "address"]
        assert len(address_conflicts) == 1
        assert address_conflicts[0].precedence_note == "structured_metadata_over_llm_text"
