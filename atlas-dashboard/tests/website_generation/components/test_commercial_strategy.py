"""Commercial strategy layer tests (AES-WEB-002L.1; EXTEND_EXISTING_RECIPE_
SYSTEM verdict) -- unit coverage for the two new pure modules
(``constants.commercial_strategy``, ``components.commercial_strategy``) and
their wiring into ``ComponentEngine.compile()``.

Distinct from ``test_repetition.py`` (the analogous J.20 composition_rules.py
matrix) in subject only -- same constants-hold-data/components-hold-logic
split, same "unit coverage here, end-to-end proof in the dedicated
integration test" division of labor. The PetTripFinder-specific real-chain
regression proof (§H of the mission's test matrix) lives in
``tests/website_generation/integration/test_pettripfinder_pilot_chain.py``'s
``TestCommercialStrategyRegression`` instead, alongside every other
PetTripFinder pilot-fixture-driven proof.

Sections mirror the mission's own A-G/I lettering (§H lives in the
integration file above; §J is the full ``pytest tests -q`` regression run,
not a unit test):

A. CommercialStrategy model
B. Classification
C. Strategy-keyed recipe lookup
D. Primary CTA defaults
E. Trust defaults
F. Component Engine integration
G. Same-engine, multi-strategy proof (real ComponentEngine, no manual
   manifest construction)
I. Architecture invariants
"""

from __future__ import annotations

import pytest

from engines.website_generation.brand.brand_engine import BrandEngine
from engines.website_generation.components.commercial_strategy import (
    classify_commercial_strategy,
    get_recipe_slots,
)
from engines.website_generation.components.component_engine import ComponentEngine
from engines.website_generation.constants.commercial_strategy import (
    COMMERCIAL_STRATEGY_VERSION,
    PAGE_COMMERCIAL_DEFAULTS,
    STRATEGY_DIRECTORY,
    STRATEGY_FALLBACK,
    STRATEGY_LEAD_GENERATION,
    STRATEGY_ORDER,
)
from engines.website_generation.constants.components import (
    LEAD_GEN_LANDING_RECIPE_SLOTS,
    RECIPE_SLOTS_BY_PAGE_ROLE,
    RECIPE_SLOTS_BY_STRATEGY_AND_ROLE,
)
from engines.website_generation.contracts.artifacts import (
    BusinessSpec,
    ContentBlock,
    ContentPackage,
    PagePlan,
    SiteArchitecture,
)
from engines.website_generation.contracts.enums import ArtifactKind, PageRole
from engines.website_generation.contracts.errors import ComponentResolutionError
from engines.website_generation.contracts.render_data import LinkSpec
from engines.website_generation.contracts.versions import ENGINE_VERSIONS, SCHEMA_VERSIONS


# --------------------------------------------------------------------------- #
# Fixtures / helpers (self-contained -- mirrors every sibling test module's
# established pattern of not sharing fixtures across test files)
# --------------------------------------------------------------------------- #

def _spec(**overrides) -> BusinessSpec:
    fields = dict(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.BUSINESS_SPEC],
        artifact_kind=ArtifactKind.BUSINESS_SPEC,
        source_hashes={},
        business_name="Test Directory",
        niche="pet travel",
        audience="pet owners",
        value_proposition="find pet-friendly places",
        monetization_model="affiliate_booking_links",
    )
    fields.update(overrides)
    return BusinessSpec(**fields)


def _sa(pages) -> SiteArchitecture:
    return SiteArchitecture(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.SITE_ARCHITECTURE],
        artifact_kind=ArtifactKind.SITE_ARCHITECTURE,
        source_hashes={},
        pages=tuple(pages),
        nav_routes=(),
        sitemap_routes=tuple(p.route for p in pages),
    )


def _cp(blocks) -> ContentPackage:
    return ContentPackage(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.CONTENT_PACKAGE],
        artifact_kind=ArtifactKind.CONTENT_PACKAGE,
        source_hashes={},
        blocks=tuple(blocks),
    )


def _brand():
    return BrandEngine().resolve(_spec())


_HOME_PAGE = PagePlan(route="/", page_type="home", title="Home")


def _directory_home_blocks():
    """Every content block a real DIRECTORY/home compile needs against the
    current registered catalog (hero h1/subhead, nav.utility.bar's message,
    legal.footer.directory's two required slots) -- empirically confirmed
    minimal (no category pages, no directory.search.primary selection)."""
    return [
        ContentBlock(page_route="/", slot_id="hero_h1", text="Find pet-friendly places"),
        ContentBlock(page_route="/", slot_id="subhead", text="Verified businesses."),
        ContentBlock(page_route="/", slot_id="message", text="Some listings are sponsored."),
        ContentBlock(page_route="/", slot_id="footer_legal", text="(c) Test Directory."),
        ContentBlock(page_route="/", slot_id="disclosures", text="Some listings may be sponsored."),
    ]


def _lead_generation_home_blocks():
    """The one real content block a LEAD_GENERATION/home compile needs:
    form.lead.quote's required "disclosure" slot. lead-gen-landing carries
    no header/footer slots of its own (LEAD_GEN_LANDING_RECIPE_SLOTS is a
    narrow 4-slot table -- see constants/components.py); hero/trust both
    resolve to the empty layout.section.container fallback (hero.leadgen.
    offer is unregistered; trust.statistics.strip's "statistics" slot is
    categorically SOURCE_UNAVAILABLE -- both documented, pre-existing J.1
    gaps, unchanged by this delivery); social_proof_listings is optional
    with no real candidate and is silently omitted."""
    return [
        ContentBlock(
            page_route="/", slot_id="disclosure",
            text="Your request is shared with quote-matched service providers.",
        ),
    ]


def _ids(page_components):
    return [inst.component_id for inst in page_components.components]


def _page(manifest, route):
    return next(p for p in manifest.pages if p.route == route)


# --------------------------------------------------------------------------- #
# A. CommercialStrategy model
# --------------------------------------------------------------------------- #

class TestCommercialStrategyModel:
    def test_two_v1_strategy_ids(self):
        assert STRATEGY_DIRECTORY == "directory"
        assert STRATEGY_LEAD_GENERATION == "lead_generation"

    def test_strategy_order_is_exactly_two_v1_strategies(self):
        assert STRATEGY_ORDER == (STRATEGY_DIRECTORY, STRATEGY_LEAD_GENERATION)
        assert len(STRATEGY_ORDER) == 2

    def test_fallback_is_directory(self):
        assert STRATEGY_FALLBACK == STRATEGY_DIRECTORY

    def test_version_is_1_0_0(self):
        assert COMMERCIAL_STRATEGY_VERSION == "1.0.0"


# --------------------------------------------------------------------------- #
# B. Classification
# --------------------------------------------------------------------------- #

class TestClassification:
    def test_generic_monetization_language_stays_directory(self):
        # AES-WEB-002L.1 explicit requirement: generic monetization
        # language never classifies as LEAD_GENERATION merely because
        # money is involved. This is PetTripFinder's real value.
        spec = _spec(monetization_model="affiliate_booking_links")
        assert classify_commercial_strategy(spec) == STRATEGY_DIRECTORY

    def test_minimal_spec_falls_back_to_directory(self):
        spec = _spec(niche="x", audience="y", value_proposition="z", monetization_model="")
        assert classify_commercial_strategy(spec) == STRATEGY_DIRECTORY

    @pytest.mark.parametrize("field", ["niche", "audience", "value_proposition", "monetization_model"])
    def test_lead_gen_phrase_in_each_classification_field_triggers_lead_generation(self, field):
        spec = _spec(**{field: "we handle every free estimate request"})
        assert classify_commercial_strategy(spec) == STRATEGY_LEAD_GENERATION

    def test_lead_gen_phrase_in_directory_taxonomy_triggers_lead_generation(self):
        spec = _spec(directory_taxonomy=("quote request", "roofing"))
        assert classify_commercial_strategy(spec) == STRATEGY_LEAD_GENERATION

    def test_bare_lead_substring_in_unrelated_prose_does_not_trigger(self):
        # Adversarial case: "leading" contains "lead" as a substring, and
        # "quotebook" contains "quote" -- neither is one of the multi-word
        # phrases STRATEGY_KEYWORDS declares, so classification must not
        # false-positive on ordinary prose.
        spec = _spec(
            niche="a leading pet-friendly travel directory",
            value_proposition="publishes its own price quotebook every quarter",
        )
        assert classify_commercial_strategy(spec) == STRATEGY_DIRECTORY

    def test_business_name_is_never_consulted(self):
        # business_name carries strong LEAD_GENERATION-sounding language;
        # every classification-eligible field does not. Must stay DIRECTORY.
        spec = _spec(
            business_name="Free Estimate Quote Request Lead Generation LLC",
            niche="pet travel", audience="pet owners",
            value_proposition="find pet-friendly places",
            monetization_model="affiliate_booking_links",
        )
        assert classify_commercial_strategy(spec) == STRATEGY_DIRECTORY

    def test_classification_is_case_insensitive(self):
        spec = _spec(value_proposition="Request A FREE ESTIMATE today")
        assert classify_commercial_strategy(spec) == STRATEGY_LEAD_GENERATION

    def test_classification_is_pure_and_deterministic(self):
        spec = _spec(value_proposition="schedule a consultation now")
        first = classify_commercial_strategy(spec)
        second = classify_commercial_strategy(spec)
        assert first == second == STRATEGY_LEAD_GENERATION


# --------------------------------------------------------------------------- #
# C. Strategy-keyed recipe lookup
# --------------------------------------------------------------------------- #

class TestRecipeLookup:
    def test_directory_aliases_every_page_role_byte_for_byte(self):
        # True aliasing (`is`, not `==`): zero table duplication for the
        # fallback strategy -- DIRECTORY's map is the exact same tuple
        # object RECIPE_SLOTS_BY_PAGE_ROLE already references.
        for role in PageRole:
            assert get_recipe_slots(STRATEGY_DIRECTORY, role.value) is RECIPE_SLOTS_BY_PAGE_ROLE[role.value]

    def test_lead_generation_overrides_only_home(self):
        assert get_recipe_slots(STRATEGY_LEAD_GENERATION, "home") is LEAD_GEN_LANDING_RECIPE_SLOTS
        assert get_recipe_slots(STRATEGY_LEAD_GENERATION, "home") is not RECIPE_SLOTS_BY_PAGE_ROLE["home"]

    def test_lead_generation_aliases_every_other_role_byte_for_byte(self):
        for role in PageRole:
            if role.value == "home":
                continue
            assert get_recipe_slots(STRATEGY_LEAD_GENERATION, role.value) is RECIPE_SLOTS_BY_PAGE_ROLE[role.value]

    def test_unknown_strategy_returns_none(self):
        assert get_recipe_slots("not_a_real_strategy", "home") is None

    def test_unknown_role_returns_none(self):
        assert get_recipe_slots(STRATEGY_DIRECTORY, "not_a_real_role") is None
        assert get_recipe_slots(STRATEGY_LEAD_GENERATION, "not_a_real_role") is None

    def test_exactly_two_strategies_registered(self):
        assert set(RECIPE_SLOTS_BY_STRATEGY_AND_ROLE) == {STRATEGY_DIRECTORY, STRATEGY_LEAD_GENERATION}


# --------------------------------------------------------------------------- #
# D. Primary CTA defaults
# --------------------------------------------------------------------------- #

class TestCTADefaults:
    def test_directory_home_has_a_real_cta_target(self):
        defaults = PAGE_COMMERCIAL_DEFAULTS[(STRATEGY_DIRECTORY, "home")]
        assert defaults["primary_cta_label"] == "Browse the directory"
        assert defaults["primary_cta_href"] == "#main"
        assert defaults["primary_cta_external"] is False

    def test_lead_generation_home_names_no_render_target(self):
        # AES-WEB-002L.1 explicit requirement: no fabricated CTA target
        # when no safe rendering target exists (hero.search.directory is
        # not part of the lead-gen-landing recipe).
        defaults = PAGE_COMMERCIAL_DEFAULTS[(STRATEGY_LEAD_GENERATION, "home")]
        assert defaults["primary_cta_label"] == "Start your estimate"
        assert "primary_cta_href" not in defaults

    def test_cta_labels_differ_between_strategies(self):
        directory_label = PAGE_COMMERCIAL_DEFAULTS[(STRATEGY_DIRECTORY, "home")]["primary_cta_label"]
        lead_gen_label = PAGE_COMMERCIAL_DEFAULTS[(STRATEGY_LEAD_GENERATION, "home")]["primary_cta_label"]
        assert directory_label != lead_gen_label

    def test_build_hero_cta_data_directory(self):
        cta = ComponentEngine._build_hero_cta_data(STRATEGY_DIRECTORY, "home")
        assert cta == LinkSpec(label="Browse the directory", href="#main", external=False)

    def test_build_hero_cta_data_lead_generation_is_none(self):
        # No render-wiring target declared -- honest omission, not a crash.
        assert ComponentEngine._build_hero_cta_data(STRATEGY_LEAD_GENERATION, "home") is None

    def test_build_hero_cta_data_unknown_combo_is_none(self):
        assert ComponentEngine._build_hero_cta_data(STRATEGY_DIRECTORY, "category") is None
        assert ComponentEngine._build_hero_cta_data("bogus", "home") is None


# --------------------------------------------------------------------------- #
# E. Trust defaults
# --------------------------------------------------------------------------- #

class TestTrustDefaults:
    def test_directory_home_trust_surfaces(self):
        defaults = PAGE_COMMERCIAL_DEFAULTS[(STRATEGY_DIRECTORY, "home")]
        assert defaults["required_trust_surfaces"] == ("disclosure",)

    def test_lead_generation_home_trust_surfaces(self):
        defaults = PAGE_COMMERCIAL_DEFAULTS[(STRATEGY_LEAD_GENERATION, "home")]
        assert defaults["required_trust_surfaces"] == ("trust_adjacent_to_form",)

    def test_trust_surfaces_differ_between_strategies(self):
        directory_surfaces = PAGE_COMMERCIAL_DEFAULTS[(STRATEGY_DIRECTORY, "home")]["required_trust_surfaces"]
        lead_gen_surfaces = PAGE_COMMERCIAL_DEFAULTS[(STRATEGY_LEAD_GENERATION, "home")]["required_trust_surfaces"]
        assert directory_surfaces != lead_gen_surfaces


# --------------------------------------------------------------------------- #
# F. Component Engine integration
# --------------------------------------------------------------------------- #

class TestComponentEngineIntegration:
    def test_default_omitted_strategy_is_byte_identical_to_explicit_directory(self):
        sa = _sa([_HOME_PAGE])
        cp = _cp(_directory_home_blocks())
        brand = _brand()
        implicit = ComponentEngine().compile(sa, cp, brand_package=brand)
        explicit = ComponentEngine().compile(
            sa, cp, brand_package=brand, commercial_strategy=STRATEGY_DIRECTORY,
        )
        assert implicit == explicit

    def test_unsupported_strategy_reported_honestly(self):
        sa = _sa([_HOME_PAGE])
        cp = _cp(_directory_home_blocks())
        with pytest.raises(ComponentResolutionError) as exc:
            ComponentEngine().compile(sa, cp, commercial_strategy="not_a_real_strategy")
        diagnostics = exc.value.diagnostics
        assert diagnostics["unsupported_page_roles"] == [
            {"route": "/", "page_type": "home", "commercial_strategy": "not_a_real_strategy"}
        ]

    def test_source_hashes_always_carry_strategy_provenance(self):
        sa = _sa([_HOME_PAGE])
        cp = _cp(_directory_home_blocks())
        result = ComponentEngine().compile(sa, cp, brand_package=_brand())
        source_hashes = result.component_manifest.source_hashes
        assert source_hashes["commercial_strategy"] == STRATEGY_DIRECTORY
        assert source_hashes["commercial_strategy_version"] == COMMERCIAL_STRATEGY_VERSION


# --------------------------------------------------------------------------- #
# G. Same-engine, multi-strategy proof
# --------------------------------------------------------------------------- #

class TestMultiStrategyProof:
    """Drives the real, single ComponentEngine class against an identical
    HOME PagePlan, differing only in ``commercial_strategy`` -- no manual
    manifest construction, no hand-repair. Proves the same generation
    system produces materially different commercial composition for
    DIRECTORY vs. LEAD_GENERATION."""

    def test_same_engine_class_drives_both_strategies(self):
        directory_engine = ComponentEngine()
        lead_gen_engine = ComponentEngine()
        assert type(directory_engine) is type(lead_gen_engine) is ComponentEngine

    def test_selected_components_differ_materially(self):
        brand = _brand()
        directory_result = ComponentEngine().compile(
            _sa([_HOME_PAGE]), _cp(_directory_home_blocks()),
            brand_package=brand, commercial_strategy=STRATEGY_DIRECTORY,
        )
        lead_gen_result = ComponentEngine().compile(
            _sa([_HOME_PAGE]), _cp(_lead_generation_home_blocks()),
            brand_package=brand, commercial_strategy=STRATEGY_LEAD_GENERATION,
        )
        directory_ids = set(_ids(_page(directory_result.component_manifest, "/")))
        lead_gen_ids = set(_ids(_page(lead_gen_result.component_manifest, "/")))

        assert directory_ids != lead_gen_ids
        assert "hero.search.directory" in directory_ids
        assert "hero.search.directory" not in lead_gen_ids
        assert "form.lead.quote" in lead_gen_ids
        assert "form.lead.quote" not in directory_ids

    def test_hero_cta_render_data_differs_between_strategies(self):
        brand = _brand()
        directory_result = ComponentEngine().compile(
            _sa([_HOME_PAGE]), _cp(_directory_home_blocks()),
            brand_package=brand, commercial_strategy=STRATEGY_DIRECTORY,
        )
        lead_gen_result = ComponentEngine().compile(
            _sa([_HOME_PAGE]), _cp(_lead_generation_home_blocks()),
            brand_package=brand, commercial_strategy=STRATEGY_LEAD_GENERATION,
        )
        directory_ctas = [e.data.cta for e in directory_result.render_data.entries if e.data.cta is not None]
        lead_gen_ctas = [e.data.cta for e in lead_gen_result.render_data.entries if e.data.cta is not None]

        assert directory_ctas == [LinkSpec(label="Browse the directory", href="#main", external=False)]
        # hero.search.directory is not part of the lead-gen-landing recipe,
        # and no other selected component (layout.section.container,
        # form.lead.quote) is a render-data cta producer -- honestly empty.
        assert lead_gen_ctas == []

    def test_commercial_strategy_provenance_differs(self):
        brand = _brand()
        directory_result = ComponentEngine().compile(
            _sa([_HOME_PAGE]), _cp(_directory_home_blocks()),
            brand_package=brand, commercial_strategy=STRATEGY_DIRECTORY,
        )
        lead_gen_result = ComponentEngine().compile(
            _sa([_HOME_PAGE]), _cp(_lead_generation_home_blocks()),
            brand_package=brand, commercial_strategy=STRATEGY_LEAD_GENERATION,
        )
        assert directory_result.component_manifest.source_hashes["commercial_strategy"] == "directory"
        assert lead_gen_result.component_manifest.source_hashes["commercial_strategy"] == "lead_generation"


# --------------------------------------------------------------------------- #
# I. Architecture invariants
# --------------------------------------------------------------------------- #

class TestArchitectureInvariants:
    def test_artifact_kind_count_unchanged_at_thirteen(self):
        assert len(ArtifactKind) == 13

    def test_business_spec_schema_unchanged(self):
        assert set(BusinessSpec.__fields__) == {
            "schema_version", "artifact_kind", "source_hashes",
            "business_name", "niche", "audience", "value_proposition",
            "directory_taxonomy", "monetization_model", "geography",
            "legal_footer_facts",
        }

    def test_component_manifest_schema_version_unchanged(self):
        assert SCHEMA_VERSIONS[ArtifactKind.COMPONENT_MANIFEST] == "1.1.0"

    def test_component_engine_version_is_1_5_0(self):
        assert ENGINE_VERSIONS["component_engine"] == "1.5.0"

    def test_renderer_version_is_1_4_0(self):
        assert ENGINE_VERSIONS["renderer"] == "1.4.0"

    def test_constants_module_imports_no_contracts_or_sibling_constants(self):
        import ast
        import inspect

        from engines.website_generation.constants import commercial_strategy as mod

        tree = ast.parse(inspect.getsource(mod))
        imported_roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imported_roots.add(alias.name.split(".")[0])
        disallowed = {"engines"} & imported_roots
        assert not disallowed, "constants/commercial_strategy.py must stay stdlib-only"
