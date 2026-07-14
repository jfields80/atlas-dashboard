"""ContentEngine behavior: determinism, PetTripFinder golden validation,
route/slot/policy failures, scope protection, and artifact-store
integration (AES-WEB-001 §5.4 / Part 2; AES-WEB-002J.4).
"""

from __future__ import annotations

import ast
import inspect
import pathlib
from typing import Tuple

import pytest

from engines.website_generation import (
    ArtifactKind,
    BrandPackage,
    BusinessSpec,
    ContentCandidate,
    ContentEngine,
    ContentPackage,
    ContentValidationError,
    SiteArchitecture,
    WebsiteGenerationError,
)
from engines.website_generation.brand import BrandEngine
from engines.website_generation.constants.content import (
    HERO_H1_MAX_CHARS,
    INTRO_MAX_CHARS,
    INTRO_MIN_CHARS,
    SLOT_HERO_H1,
    SLOT_INTRO,
)
from engines.website_generation.contracts.artifacts import (
    PagePlan,
    artifact_sha256,
    canonical_artifact_json,
)
from engines.website_generation.contracts.errors import ArtifactValidationError
from engines.website_generation.contracts.interfaces import ContentEngineInterface
from engines.website_generation.contracts.versions import (
    ENGINE_VERSIONS,
    SCHEMA_VERSIONS,
)
from engines.website_generation.ia import InformationArchitectureEngine
from engines.website_generation.speccompiler.business_spec_compiler import (
    BusinessSpecCompiler,
)
from repositories.artifact_store_repository import ArtifactStoreRepository

# ---------------------------------------------------------------------------
# PetTripFinder proof fixture (§14) -- explicitly authored here, deterministic,
# within every slot's length bound, free of banned phrases and placeholder
# markers, and asserting no count/claim beyond what a human operator would
# plausibly write about the golden BusinessSpec (verified pet-friendly stays,
# United States, featured-listings monetization).
# ---------------------------------------------------------------------------

HOME_HERO_H1 = "Find Pet-Friendly Stays Across the US"
HOME_INTRO = (
    "Pet Trip Finder helps traveling pet owners find verified "
    "pet-friendly hotels, parks, and restaurants across the United "
    "States, with details checked before they go live."
)
HOTELS_HERO_H1 = "Pet-Friendly Hotels Worth Booking"
HOTELS_INTRO = (
    "Browse pet-friendly hotels with clear pet policies, so you can "
    "book a stay that welcomes your dog or cat without any "
    "last-minute surprises at the front desk."
)
PARKS_HERO_H1 = "Parks Where Pets Are Welcome"
PARKS_INTRO = (
    "Explore parks that allow leashed pets, from quiet neighborhood "
    "greenspaces to larger regional trails, each one noted with the "
    "specific rules that apply on site."
)
RESTAURANTS_HERO_H1 = "Restaurants With Pet-Friendly Patios"
RESTAURANTS_INTRO = (
    "Find restaurants with pet-friendly patios and outdoor seating, "
    "so your next meal out does not mean leaving your pet behind in "
    "the car or at home."
)


def _candidate(
    route: str, slot_id: str, body: str, origin: str = "human"
) -> ContentCandidate:
    return ContentCandidate(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.CONTENT_CANDIDATE],
        artifact_kind=ArtifactKind.CONTENT_CANDIDATE,
        source_hashes={},
        page_route=route,
        slot_id=slot_id,
        body=body,
        origin=origin,
    )


def _pettripfinder_candidates() -> Tuple[ContentCandidate, ...]:
    return (
        _candidate("/", SLOT_HERO_H1, HOME_HERO_H1),
        _candidate("/", SLOT_INTRO, HOME_INTRO),
        _candidate("/hotels/", SLOT_HERO_H1, HOTELS_HERO_H1),
        _candidate("/hotels/", SLOT_INTRO, HOTELS_INTRO),
        _candidate("/parks/", SLOT_HERO_H1, PARKS_HERO_H1),
        _candidate("/parks/", SLOT_INTRO, PARKS_INTRO),
        _candidate("/restaurants/", SLOT_HERO_H1, RESTAURANTS_HERO_H1),
        _candidate("/restaurants/", SLOT_INTRO, RESTAURANTS_INTRO),
    )


def _spec(golden_compiler_input) -> BusinessSpec:
    return BusinessSpecCompiler().compile(golden_compiler_input)


def _site_for(spec: BusinessSpec) -> SiteArchitecture:
    brand = BrandEngine().resolve(spec)
    return InformationArchitectureEngine().plan(spec, brand)


def _raw_spec(**overrides) -> BusinessSpec:
    fields = dict(
        schema_version="1.0.0",
        artifact_kind=ArtifactKind.BUSINESS_SPEC,
        source_hashes={},
        business_name="Pet Trip Finder",
        niche="pet travel",
        audience="pet owners",
        value_proposition="verified pet-friendly stays",
        directory_taxonomy=(),
    )
    fields.update(overrides)
    return BusinessSpec(**fields)


def _site_with_pages(*pages: PagePlan) -> SiteArchitecture:
    """Hand-built SiteArchitecture for structural edge cases the real IA
    Engine output cannot exercise (every current fixture page declares both
    hero_h1 and intro). ``ContentEngine.validate()`` only reads ``pages``;
    hierarchy/link-topology are irrelevant to it and left empty -- the
    ``SiteArchitecture`` model itself performs no cross-field validation
    (that is IA's ``_validate_site_graph``, never invoked here)."""
    routes = tuple(page.route for page in pages)
    return SiteArchitecture(
        schema_version="1.1.0",
        artifact_kind=ArtifactKind.SITE_ARCHITECTURE,
        source_hashes={},
        pages=tuple(pages),
        nav_routes=routes,
        sitemap_routes=routes,
        page_ids={},
        page_hierarchy=(),
        internal_link_topology=(),
    )


def _without(
    candidates: Tuple[ContentCandidate, ...], route: str, slot_id: str
) -> Tuple[ContentCandidate, ...]:
    return tuple(
        c for c in candidates if not (c.page_route == route and c.slot_id == slot_id)
    )


class TestDeterminism:
    def test_deterministic_equality(self, golden_compiler_input):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        candidates = _pettripfinder_candidates()
        engine = ContentEngine()
        first = engine.validate(site, candidates, spec)
        second = engine.validate(site, candidates, spec)
        assert canonical_artifact_json(first) == canonical_artifact_json(second)

    def test_identical_artifact_hashes_across_repeated_calls(
        self, golden_compiler_input
    ):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        candidates = _pettripfinder_candidates()
        engine = ContentEngine()
        hashes = {
            artifact_sha256(engine.validate(site, candidates, spec)) for _ in range(3)
        }
        assert len(hashes) == 1

    def test_identical_results_across_fresh_engine_instances(
        self, golden_compiler_input
    ):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        candidates = _pettripfinder_candidates()
        hashes = {
            artifact_sha256(ContentEngine().validate(site, candidates, spec))
            for _ in range(3)
        }
        assert len(hashes) == 1

    def test_candidate_input_order_does_not_alter_canonical_output(
        self, golden_compiler_input
    ):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        candidates = _pettripfinder_candidates()
        forward = ContentEngine().validate(site, candidates, spec)
        backward = ContentEngine().validate(
            site, tuple(reversed(candidates)), spec
        )
        assert canonical_artifact_json(forward) == canonical_artifact_json(backward)

    def test_shuffled_candidate_order_does_not_alter_canonical_output(
        self, golden_compiler_input
    ):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        candidates = _pettripfinder_candidates()
        shuffled = candidates[5:] + candidates[:5]
        a = ContentEngine().validate(site, candidates, spec)
        b = ContentEngine().validate(site, shuffled, spec)
        assert canonical_artifact_json(a) == canonical_artifact_json(b)

    def test_diagnostic_ordering_is_deterministic_regardless_of_input_order(
        self, golden_compiler_input
    ):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        # Only 2 of the 8 required candidates supplied, plus one targeting
        # an unknown route -- exercises two diagnostic categories at once.
        candidates = (
            _candidate("/nonexistent/", SLOT_HERO_H1, "Not a real page"),
            _candidate("/restaurants/", SLOT_HERO_H1, RESTAURANTS_HERO_H1),
            _candidate("/", SLOT_HERO_H1, HOME_HERO_H1),
        )
        with pytest.raises(ContentValidationError) as first:
            ContentEngine().validate(site, candidates, spec)
        with pytest.raises(ContentValidationError) as second:
            ContentEngine().validate(site, tuple(reversed(candidates)), spec)
        assert first.value.diagnostics == second.value.diagnostics


class TestPetTripFinderGolden:
    def test_all_eight_candidates_validate(self, golden_compiler_input):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        package = ContentEngine().validate(site, _pettripfinder_candidates(), spec)
        assert len(package.blocks) == 8

    def test_every_declared_slot_is_populated(self, golden_compiler_input):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        package = ContentEngine().validate(site, _pettripfinder_candidates(), spec)
        bound = {(b.page_route, b.slot_id) for b in package.blocks}
        expected = {
            (page.route, slot_id)
            for page in site.pages
            for slot_id in page.content_slots
        }
        assert bound == expected

    def test_output_order_follows_architecture_and_declared_slot_order(
        self, golden_compiler_input
    ):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        package = ContentEngine().validate(site, _pettripfinder_candidates(), spec)
        expected_order = [
            (page.route, slot_id)
            for page in site.pages
            for slot_id in page.content_slots
        ]
        actual_order = [(b.page_route, b.slot_id) for b in package.blocks]
        assert actual_order == expected_order

    def test_block_text_matches_candidate_body_byte_for_byte(
        self, golden_compiler_input
    ):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        candidates = _pettripfinder_candidates()
        package = ContentEngine().validate(site, candidates, spec)
        body_by_key = {(c.page_route, c.slot_id): c.body for c in candidates}
        for block in package.blocks:
            assert block.text == body_by_key[(block.page_route, block.slot_id)]

    def test_source_hashes_reference_every_input_artifact(
        self, golden_compiler_input
    ):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        candidates = _pettripfinder_candidates()
        package = ContentEngine().validate(site, candidates, spec)
        expected = {
            "site_architecture": artifact_sha256(site),
            "business_spec": artifact_sha256(spec),
        }
        for candidate in candidates:
            key = "content_candidate:%s:%s" % (
                candidate.page_route,
                candidate.slot_id,
            )
            expected[key] = artifact_sha256(candidate)
        assert package.source_hashes == expected

    def test_schema_version_and_artifact_kind_are_enforced(
        self, golden_compiler_input
    ):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        package = ContentEngine().validate(site, _pettripfinder_candidates(), spec)
        assert package.artifact_kind == ArtifactKind.CONTENT_PACKAGE
        assert package.schema_version == "1.0.0"


class TestArtifactStoreIntegration:
    def test_content_package_stores_after_storing_every_source(
        self, golden_compiler_input, tmp_path
    ):
        store = ArtifactStoreRepository(tmp_path / "cas")
        spec = _spec(golden_compiler_input)
        spec_hash = store.put(spec)

        brand = BrandEngine().resolve(spec)
        store.put(brand)  # required for the SiteArchitecture's own provenance

        site = InformationArchitectureEngine().plan(spec, brand)
        site_hash = store.put(site)

        candidates = _pettripfinder_candidates()
        for candidate in candidates:
            store.put(candidate)

        package = ContentEngine().validate(site, candidates, spec)
        assert package.source_hashes["site_architecture"] == site_hash
        assert package.source_hashes["business_spec"] == spec_hash

        package_hash = store.put(package)
        assert package_hash == artifact_sha256(package)
        assert store.exists(package_hash)

        loaded = store.get(package_hash, ArtifactKind.CONTENT_PACKAGE)
        assert isinstance(loaded, ContentPackage)
        assert loaded.blocks == package.blocks

    def test_content_package_rejects_storage_without_its_sources(
        self, golden_compiler_input, tmp_path
    ):
        store = ArtifactStoreRepository(tmp_path / "cas")
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        package = ContentEngine().validate(site, _pettripfinder_candidates(), spec)
        with pytest.raises(ArtifactValidationError):
            store.put(package)


class TestRouteAndSlotFailures:
    def test_unknown_route_rejected(self, golden_compiler_input):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        candidates = _pettripfinder_candidates() + (
            _candidate("/nonexistent/", SLOT_HERO_H1, "Nonexistent Page Hero"),
        )
        with pytest.raises(ContentValidationError) as excinfo:
            ContentEngine().validate(site, candidates, spec)
        refs = excinfo.value.diagnostics["unknown_route_candidates"]
        assert {"page_route": "/nonexistent/", "slot_id": SLOT_HERO_H1} in refs
        assert excinfo.value.stage == "content_validation"
        assert excinfo.value.retryable is False

    def test_unsupported_slot_id_rejected(self, golden_compiler_input):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        candidates = _pettripfinder_candidates() + (
            _candidate("/", "seo_meta_description", "Unsupported slot body."),
        )
        with pytest.raises(ContentValidationError) as excinfo:
            ContentEngine().validate(site, candidates, spec)
        refs = excinfo.value.diagnostics["unsupported_slot_candidates"]
        assert {"page_route": "/", "slot_id": "seo_meta_description"} in refs

    def test_undeclared_slot_for_page_rejected(self):
        site = _site_with_pages(
            PagePlan(route="/", page_type="home", content_slots=(SLOT_HERO_H1,)),
        )
        spec = _raw_spec()
        candidates = (
            _candidate("/", SLOT_HERO_H1, "A Perfectly Valid Hero Title"),
            _candidate("/", SLOT_INTRO, "I" * 50),
        )
        with pytest.raises(ContentValidationError) as excinfo:
            ContentEngine().validate(site, candidates, spec)
        refs = excinfo.value.diagnostics["undeclared_slot_candidates"]
        assert {"page_route": "/", "slot_id": SLOT_INTRO} in refs

    def test_duplicate_route_slot_binding_rejected(self, golden_compiler_input):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        candidates = _pettripfinder_candidates() + (
            _candidate("/", SLOT_HERO_H1, "A Second Competing Home Hero"),
        )
        with pytest.raises(ContentValidationError) as excinfo:
            ContentEngine().validate(site, candidates, spec)
        duplicates = excinfo.value.diagnostics["duplicate_bindings"]
        assert {
            "page_route": "/",
            "slot_id": SLOT_HERO_H1,
            "candidate_count": 2,
        } in duplicates

    def test_missing_required_slot_rejected(self, golden_compiler_input):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        candidates = _without(_pettripfinder_candidates(), "/", SLOT_INTRO)
        with pytest.raises(ContentValidationError) as excinfo:
            ContentEngine().validate(site, candidates, spec)
        missing = excinfo.value.diagnostics["missing_required_slots"]
        assert {"page_route": "/", "slot_id": SLOT_INTRO} in missing

    def test_duplicate_candidates_rejected_as_ambiguous_binding(
        self, golden_compiler_input
    ):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        candidates = _pettripfinder_candidates() + (
            _candidate("/hotels/", SLOT_INTRO, "A second, different intro."),
        )
        with pytest.raises(ContentValidationError) as excinfo:
            ContentEngine().validate(site, candidates, spec)
        assert "duplicate_bindings" in excinfo.value.diagnostics

    def test_malformed_empty_route_candidate_rejected(self, golden_compiler_input):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        candidates = _pettripfinder_candidates() + (
            _candidate("", SLOT_HERO_H1, "Body text with no route"),
        )
        with pytest.raises(ContentValidationError) as excinfo:
            ContentEngine().validate(site, candidates, spec)
        refs = excinfo.value.diagnostics["unknown_route_candidates"]
        assert {"page_route": "", "slot_id": SLOT_HERO_H1} in refs

    def test_page_with_no_slots_requires_no_candidate(self):
        site = _site_with_pages(
            PagePlan(
                route="/",
                page_type="home",
                content_slots=(SLOT_HERO_H1, SLOT_INTRO),
            ),
            PagePlan(route="/about/", page_type="legal", content_slots=()),
        )
        spec = _raw_spec()
        candidates = (
            _candidate("/", SLOT_HERO_H1, "A Perfectly Valid Hero Title"),
            _candidate("/", SLOT_INTRO, "I" * 50),
        )
        package = ContentEngine().validate(site, candidates, spec)
        assert len(package.blocks) == 2
        assert not any(b.page_route == "/about/" for b in package.blocks)


class TestDuplicateRouteRobustness:
    """SiteArchitecture is trusted, already-validated upstream input (§13):
    a duplicate route is not repaired here. These prove the engine still
    behaves predictably against one -- resolving against the same
    deduplicated (last-occurrence-wins) view every check uses, never
    crashing, and never double-emitting a block for a route that appears
    more than once in ``pages``.
    """

    def test_duplicate_route_with_different_slots_does_not_raise_keyerror(self):
        site = _site_with_pages(
            PagePlan(route="/about/", page_type="legal", content_slots=(SLOT_HERO_H1,)),
            PagePlan(route="/about/", page_type="legal", content_slots=(SLOT_INTRO,)),
        )
        spec = _raw_spec()
        candidates = (_candidate("/about/", SLOT_INTRO, "I" * 50),)
        package = ContentEngine().validate(site, candidates, spec)
        assert [(b.page_route, b.slot_id) for b in package.blocks] == [
            ("/about/", SLOT_INTRO)
        ]

    def test_duplicate_route_with_identical_slots_does_not_double_emit(self):
        site = _site_with_pages(
            PagePlan(route="/about/", page_type="legal", content_slots=(SLOT_HERO_H1,)),
            PagePlan(route="/about/", page_type="legal", content_slots=(SLOT_HERO_H1,)),
        )
        spec = _raw_spec()
        candidates = (_candidate("/about/", SLOT_HERO_H1, "A Valid Title"),)
        package = ContentEngine().validate(site, candidates, spec)
        assert [(b.page_route, b.slot_id) for b in package.blocks] == [
            ("/about/", SLOT_HERO_H1)
        ]


class TestPolicyFailures:
    def test_banned_phrase_rejected_case_insensitively(self, golden_compiler_input):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        candidates = _without(
            _pettripfinder_candidates(), "/", SLOT_INTRO
        ) + (
            _candidate(
                "/",
                SLOT_INTRO,
                "This is a PAWSOME place to find pet-friendly stays fast today.",
            ),
        )
        with pytest.raises(ContentValidationError) as excinfo:
            ContentEngine().validate(site, candidates, spec)
        violations = excinfo.value.diagnostics["banned_phrase_violations"]
        assert violations == [
            {"page_route": "/", "slot_id": SLOT_INTRO, "phrases": ["pawsome"]}
        ]

    def test_ordinary_inflection_of_a_banned_word_is_not_rejected(
        self, golden_compiler_input
    ):
        # "unleash" is banned as a marketing imperative, but "unleashed" is
        # ordinary descriptive usage (e.g. an off-leash area) and must not
        # be false-flagged by raw substring matching.
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        body = (
            "This fenced field lets dogs run unleashed safely before you "
            "continue on to your next stop."
        )
        assert INTRO_MIN_CHARS <= len(body) <= INTRO_MAX_CHARS
        candidates = _without(_pettripfinder_candidates(), "/", SLOT_INTRO) + (
            _candidate("/", SLOT_INTRO, body),
        )
        package = ContentEngine().validate(site, candidates, spec)
        home_intro = next(
            b.text
            for b in package.blocks
            if b.page_route == "/" and b.slot_id == SLOT_INTRO
        )
        assert home_intro == body

    def test_todo_marker_rejected(self, golden_compiler_input):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        body = "TODO write the real introduction copy for this page later."
        assert len(body) >= INTRO_MIN_CHARS
        candidates = _without(_pettripfinder_candidates(), "/", SLOT_INTRO) + (
            _candidate("/", SLOT_INTRO, body),
        )
        with pytest.raises(ContentValidationError) as excinfo:
            ContentEngine().validate(site, candidates, spec)
        violations = excinfo.value.diagnostics["placeholder_violations"]
        assert violations == [
            {"page_route": "/", "slot_id": SLOT_INTRO, "markers": ["TODO"]}
        ]

    def test_lorem_marker_rejected(self, golden_compiler_input):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        body = "Lorem ipsum dolor sit amet, consectetur adipiscing elit sed."
        assert len(body) >= INTRO_MIN_CHARS
        candidates = _without(_pettripfinder_candidates(), "/", SLOT_INTRO) + (
            _candidate("/", SLOT_INTRO, body),
        )
        with pytest.raises(ContentValidationError) as excinfo:
            ContentEngine().validate(site, candidates, spec)
        violations = excinfo.value.diagnostics["placeholder_violations"]
        assert violations == [
            {"page_route": "/", "slot_id": SLOT_INTRO, "markers": ["lorem"]}
        ]

    def test_brace_placeholder_rejected(self, golden_compiler_input):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        body = "Welcome to {{business_name}}, your stop for pet travel info."
        assert len(body) >= INTRO_MIN_CHARS
        candidates = _without(_pettripfinder_candidates(), "/", SLOT_INTRO) + (
            _candidate("/", SLOT_INTRO, body),
        )
        with pytest.raises(ContentValidationError) as excinfo:
            ContentEngine().validate(site, candidates, spec)
        violations = excinfo.value.diagnostics["placeholder_violations"]
        assert violations == [
            {
                "page_route": "/",
                "slot_id": SLOT_INTRO,
                "markers": ["{{", "}}"],
            }
        ]

    def test_hero_h1_over_max_length_rejected(self, golden_compiler_input):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        long_hero = "A" * (HERO_H1_MAX_CHARS + 1)
        candidates = _without(_pettripfinder_candidates(), "/", SLOT_HERO_H1) + (
            _candidate("/", SLOT_HERO_H1, long_hero),
        )
        with pytest.raises(ContentValidationError) as excinfo:
            ContentEngine().validate(site, candidates, spec)
        violations = excinfo.value.diagnostics["length_violations"]
        assert {
            "page_route": "/",
            "slot_id": SLOT_HERO_H1,
            "reason": "too_long",
            "length": HERO_H1_MAX_CHARS + 1,
            "limit": HERO_H1_MAX_CHARS,
        } in violations

    def test_hero_h1_empty_or_whitespace_only_rejected(self, golden_compiler_input):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        candidates = _without(_pettripfinder_candidates(), "/", SLOT_HERO_H1) + (
            _candidate("/", SLOT_HERO_H1, "    "),
        )
        with pytest.raises(ContentValidationError) as excinfo:
            ContentEngine().validate(site, candidates, spec)
        violations = excinfo.value.diagnostics["length_violations"]
        assert {
            "page_route": "/",
            "slot_id": SLOT_HERO_H1,
            "reason": "empty_or_whitespace",
            "length": 4,
            "limit": 1,
        } in violations

    def test_hero_h1_zero_width_space_only_rejected(self, golden_compiler_input):
        # U+200B is not str.isspace(); a naive strip()-based floor would
        # accept this as "1 non-whitespace character" while it renders as a
        # blank, invisible heading.
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        candidates = _without(_pettripfinder_candidates(), "/", SLOT_HERO_H1) + (
            _candidate("/", SLOT_HERO_H1, "​"),
        )
        with pytest.raises(ContentValidationError) as excinfo:
            ContentEngine().validate(site, candidates, spec)
        violations = excinfo.value.diagnostics["length_violations"]
        assert {
            "page_route": "/",
            "slot_id": SLOT_HERO_H1,
            "reason": "empty_or_whitespace",
            "length": 1,
            "limit": 1,
        } in violations

    def test_underscore_joined_todo_placeholder_rejected(self, golden_compiler_input):
        # Python regex's default \b treats "_" as a word character; the
        # letter-adjacency boundary must still catch this common
        # placeholder-naming style.
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        body = "Our TODO_INTRO_COPY draft is not ready for publishing yet."
        assert len(body) >= INTRO_MIN_CHARS
        candidates = _without(_pettripfinder_candidates(), "/", SLOT_INTRO) + (
            _candidate("/", SLOT_INTRO, body),
        )
        with pytest.raises(ContentValidationError) as excinfo:
            ContentEngine().validate(site, candidates, spec)
        violations = excinfo.value.diagnostics["placeholder_violations"]
        assert violations == [
            {"page_route": "/", "slot_id": SLOT_INTRO, "markers": ["TODO"]}
        ]

    def test_intro_under_min_rejected(self, golden_compiler_input):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        short_intro = "A" * (INTRO_MIN_CHARS - 1)
        candidates = _without(_pettripfinder_candidates(), "/", SLOT_INTRO) + (
            _candidate("/", SLOT_INTRO, short_intro),
        )
        with pytest.raises(ContentValidationError) as excinfo:
            ContentEngine().validate(site, candidates, spec)
        violations = excinfo.value.diagnostics["length_violations"]
        assert {
            "page_route": "/",
            "slot_id": SLOT_INTRO,
            "reason": "too_short",
            "length": INTRO_MIN_CHARS - 1,
            "limit": INTRO_MIN_CHARS,
        } in violations

    def test_intro_over_max_rejected(self, golden_compiler_input):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        long_intro = "A" * (INTRO_MAX_CHARS + 1)
        candidates = _without(_pettripfinder_candidates(), "/", SLOT_INTRO) + (
            _candidate("/", SLOT_INTRO, long_intro),
        )
        with pytest.raises(ContentValidationError) as excinfo:
            ContentEngine().validate(site, candidates, spec)
        violations = excinfo.value.diagnostics["length_violations"]
        assert {
            "page_route": "/",
            "slot_id": SLOT_INTRO,
            "reason": "too_long",
            "length": INTRO_MAX_CHARS + 1,
            "limit": INTRO_MAX_CHARS,
        } in violations

    def test_valid_boundary_lengths_accepted(self, golden_compiler_input):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        candidates = (
            _candidate("/", SLOT_HERO_H1, "H" * HERO_H1_MAX_CHARS),
            _candidate("/", SLOT_INTRO, "I" * INTRO_MIN_CHARS),
            _candidate("/hotels/", SLOT_HERO_H1, "H"),
            _candidate("/hotels/", SLOT_INTRO, "I" * INTRO_MAX_CHARS),
            _candidate("/parks/", SLOT_HERO_H1, PARKS_HERO_H1),
            _candidate("/parks/", SLOT_INTRO, PARKS_INTRO),
            _candidate("/restaurants/", SLOT_HERO_H1, RESTAURANTS_HERO_H1),
            _candidate("/restaurants/", SLOT_INTRO, RESTAURANTS_INTRO),
        )
        package = ContentEngine().validate(site, candidates, spec)
        assert len(package.blocks) == 8

    def test_multiple_violation_categories_batched_in_one_pass(
        self, golden_compiler_input
    ):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        candidates = (
            _candidate("/nonexistent/", SLOT_HERO_H1, "Off-architecture route"),
            _candidate("/", SLOT_HERO_H1, "A" * (HERO_H1_MAX_CHARS + 1)),
            # "/" intro, "/hotels/" hero_h1 + intro, "/parks/" hero_h1 +
            # intro, "/restaurants/" hero_h1 + intro all left unsupplied.
        )
        with pytest.raises(ContentValidationError) as excinfo:
            ContentEngine().validate(site, candidates, spec)
        diagnostics = excinfo.value.diagnostics
        assert "unknown_route_candidates" in diagnostics
        assert "length_violations" in diagnostics
        assert "missing_required_slots" in diagnostics


class TestScopeProtection:
    def test_engine_does_not_create_content_for_unsupplied_slots(
        self, golden_compiler_input
    ):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        with pytest.raises(ContentValidationError):
            ContentEngine().validate(site, (), spec)

    def test_text_is_preserved_rather_than_rewritten(self, golden_compiler_input):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        package = ContentEngine().validate(
            site, _pettripfinder_candidates(), spec
        )
        home_intro = next(
            b.text
            for b in package.blocks
            if b.page_route == "/" and b.slot_id == SLOT_INTRO
        )
        assert home_intro == HOME_INTRO

    def test_unsupported_claims_pass_through_unmodified_not_fact_checked(
        self, golden_compiler_input
    ):
        # The engine performs no fact-checking (§11): a candidate's claim,
        # once supplied, passes through unchanged -- the engine never
        # appends, strips, or invents a claim of its own.
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        claim = (
            "Every listing on this page is checked by our team before it "
            "goes live, and Pet Trip Finder never charges pet owners a fee."
        )
        assert INTRO_MIN_CHARS <= len(claim) <= INTRO_MAX_CHARS
        candidates = _without(_pettripfinder_candidates(), "/", SLOT_INTRO) + (
            _candidate("/", SLOT_INTRO, claim),
        )
        package = ContentEngine().validate(site, candidates, spec)
        home_intro = next(
            b.text
            for b in package.blocks
            if b.page_route == "/" and b.slot_id == SLOT_INTRO
        )
        assert home_intro == claim

    def test_validate_signature_has_no_brand_package_parameter(self):
        signature = inspect.signature(ContentEngine.validate)
        assert list(signature.parameters) == [
            "self",
            "site_architecture",
            "candidates",
            "business_spec",
        ]
        for parameter in signature.parameters.values():
            assert parameter.annotation is not BrandPackage
            assert "BrandPackage" not in str(parameter.annotation)

    def test_only_validate_is_a_public_method(self):
        # Decision A2: no generate()/resolve()/draft()/author().
        public_methods = {
            name
            for name in vars(ContentEngine)
            if not name.startswith("_") and callable(getattr(ContentEngine, name))
        }
        assert public_methods == {"validate"}

    def test_content_package_source_hashes_never_reference_brand(
        self, golden_compiler_input
    ):
        spec = _spec(golden_compiler_input)
        site = _site_for(spec)
        package = ContentEngine().validate(site, _pettripfinder_candidates(), spec)
        assert "brand_package" not in package.source_hashes

    def test_content_package_imports_are_within_the_authorized_boundary(self):
        # No brand/ia sibling-engine import, no component/gate/pipeline
        # import, and (because those are the only non-stdlib names the
        # allowed set admits) no Flask/requests/socket/anthropic/openai/
        # uuid/random/time/datetime/logging/filesystem dependency either --
        # nothing outside {contracts, constants, content, stdlib} can appear
        # in either source file.
        allowed_stdlib = {"__future__", "typing", "unicodedata"}
        content_dir = pathlib.Path(inspect.getfile(ContentEngine)).parent
        for path in sorted(content_dir.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module] if node.module else []
                else:
                    continue
                for name in names:
                    top = name.split(".")[0]
                    if top in allowed_stdlib:
                        continue
                    assert name.startswith(
                        "engines.website_generation.contracts"
                    ) or name.startswith(
                        "engines.website_generation.constants"
                    ) or name.startswith(
                        "engines.website_generation.content"
                    ), "%s imports out-of-boundary %r" % (path, name)


class TestContractsAndArchitecture:
    def test_content_package_schema_remains_1_0_0(self):
        assert SCHEMA_VERSIONS[ArtifactKind.CONTENT_PACKAGE] == "1.0.0"

    def test_content_candidate_schema_remains_1_0_0(self):
        assert SCHEMA_VERSIONS[ArtifactKind.CONTENT_CANDIDATE] == "1.0.0"

    def test_no_new_artifact_kind_was_added(self):
        # AES-WEB-002J.17 (ADR-WEB-LISTING-DATASET) added the additive
        # thirteenth kind, LISTING_DATASET -- unrelated to the Content
        # Engine, but this guard enumerates every kind so it must include it.
        assert {kind.value for kind in ArtifactKind} == {
            "BUSINESS_SPEC",
            "BRAND_PACKAGE",
            "SITE_ARCHITECTURE",
            "CONTENT_CANDIDATE",
            "CONTENT_PACKAGE",
            "COMPONENT_MANIFEST",
            "LAYOUT_PLAN",
            "RENDERED_PAGE_SET",
            "SEO_PACKAGE",
            "SITE_BUNDLE",
            "QUALITY_REPORT",
            "BUILD_MANIFEST",
            "LISTING_DATASET",
        }

    def test_engine_versions_contains_content_engine_1_0_0(self):
        assert ENGINE_VERSIONS["content_engine"] == "1.0.0"
        assert ContentEngine.version == "1.0.0"

    def test_content_validation_error_hierarchy_and_defaults(self):
        assert issubclass(ContentValidationError, WebsiteGenerationError)
        error = ContentValidationError("boom", diagnostics={"x": 1})
        assert error.stage == "content_validation"
        assert error.retryable is False
        assert error.diagnostics == {"x": 1}

    def test_content_engine_interface_is_abstract_and_internal(self):
        assert issubclass(ContentEngine, ContentEngineInterface)
        with pytest.raises(TypeError):
            ContentEngineInterface()  # abstract; cannot be instantiated

    def test_content_engine_is_publicly_exported(self):
        import engines.website_generation as wge

        assert "ContentEngine" in wge.__all__
        assert wge.ContentEngine is ContentEngine
        assert "ContentValidationError" in wge.__all__
