"""Commercial completeness gate tests (AES-WEB-002L.2; AES-WEB-001 §5.10).

CG-CMP-010 ("required role components present per §6.1 matrix") is a
pre-existing, registered, ``executable=True`` gate (AES-WEB-002I) that was
never wired into ``QualityGateEngine``'s evaluated set until this delivery.
AES-WEB-002L.2 reads it as commercial-completeness verification: for a page
whose ``(commercial_strategy, page_role)`` declares requirements in
``PAGE_COMMERCIAL_DEFAULTS`` (AES-WEB-002L.1), the real rendered output must
honestly satisfy them (primary CTA, required trust surfaces, a non-empty
commercial main) -- verification of already-declared requirements, never a
new requirement invented here (DECLARE -> COMPOSE -> VERIFY).

Sections mirror the mission's own lettering:

A. Gate registration
B. Requirement resolution (same PAGE_COMMERCIAL_DEFAULTS authority)
C. Primary CTA
D. Trust surfaces
E. Disclosure (a "disclosure" trust surface, DIRECTORY's case)
F. Commercially empty main
G. Strategy isolation
I. QualityReport integration
J. Architecture invariants

(§H PetTripFinder proof lives in
``tests/website_generation/integration/test_pettripfinder_pilot_chain.py``,
alongside every other real-chain PetTripFinder proof; §K is the full
``pytest tests -q`` regression run, not a unit test.)
"""

from __future__ import annotations

import pytest

from engines.website_generation.constants.commercial_strategy import (
    PAGE_COMMERCIAL_DEFAULTS as PAGE_COMMERCIAL_DEFAULTS_VIA_CONSTANTS,
)
from engines.website_generation.constants.gates import (
    COMPONENT_GATE_REGISTRATIONS,
    GATE_FAMILY_CG_COMPOSITION,
    GATE_SEVERITY_BLOCKING,
)
from engines.website_generation.contracts.artifacts import (
    ComponentManifest,
    PagePlan,
    SiteArchitecture,
)
from engines.website_generation.contracts.enums import ArtifactKind
from engines.website_generation.contracts.versions import ENGINE_VERSIONS, SCHEMA_VERSIONS
from engines.website_generation.gates import fact_extractor
from engines.website_generation.gates.fact_extractor import (
    _commercial_requirement_facts,
    extract_page_composition_facts,
)
from engines.website_generation.gates.quality_gate_engine import QualityGateEngine

from ._qge_fixtures import bundle_from_html, content_package, seo_package

_DIRECTORY = "directory"
_LEAD_GENERATION = "lead_generation"


# --------------------------------------------------------------------------- #
# Fixtures / helpers (self-contained, per this package's own convention)
# --------------------------------------------------------------------------- #

def _sa(route: str = "/", page_type: str = "home") -> SiteArchitecture:
    return SiteArchitecture(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.SITE_ARCHITECTURE],
        artifact_kind=ArtifactKind.SITE_ARCHITECTURE,
        source_hashes={},
        pages=(PagePlan(route=route, page_type=page_type, title="T"),),
        nav_routes=(),
        sitemap_routes=(route,),
    )


def _manifest(commercial_strategy: str) -> ComponentManifest:
    return ComponentManifest(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.COMPONENT_MANIFEST],
        artifact_kind=ArtifactKind.COMPONENT_MANIFEST,
        source_hashes={"commercial_strategy": commercial_strategy},
    )


def _report_for(html: str, *, commercial_strategy: str, page_type: str = "home"):
    return QualityGateEngine().evaluate(
        bundle_from_html({"index.html": html}),
        seo_package(),
        content_package(),
        _sa("/", page_type),
        component_manifest=_manifest(commercial_strategy),
    )


def _cmp_010(report):
    return next(g for g in report.gate_results if g.gate_id == "CG-CMP-010")


_PAGE_OPEN = '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>T</title></head><body>'
_PAGE_CLOSE = "</body></html>"
_HEADER = '<header><nav aria-label="Main"><a href="/about">About</a></nav></header>'
_HERO_WITH_CTA = (
    '<section data-atlas-c="hero-search-directory"><h1>H</h1><p>P</p>'
    '<a class="ac-cta ac-cta--action" href="#main">Browse the directory</a></section>'
)
_HERO_NO_CTA = '<section data-atlas-c="hero-search-directory"><h1>H</h1><p>P</p></section>'
_HERO_WRONG_CTA = (
    '<section data-atlas-c="hero-search-directory"><h1>H</h1>'
    '<a class="ac-cta ac-cta--action" href="/somewhere-else">Go</a></section>'
)
_HERO_PROSE_CTA = '<section data-atlas-c="hero-search-directory"><h1>H</h1><p>Browse the directory</p></section>'
_MAIN_REAL = '<main id="main"><section data-atlas-c="directory-categories-grid"><ul><li><a href="/x/">X</a></li></ul></section></main>'
_MAIN_EMPTY = '<main id="main"></main>'
_MAIN_SHELL_ONLY = '<main id="main"><section data-atlas-c="layout-section-container"></section></main>'
_FOOTER_WITH_DISCLOSURE = (
    '<footer><div data-atlas-c="legal-footer-directory">'
    "<p>Legal facts.</p><p>Some listings are sponsored, always labeled.</p></div></footer>"
)
_FOOTER_NO_DISCLOSURE = (
    '<footer><div data-atlas-c="legal-footer-directory"><p>Legal facts.</p></div></footer>'
)
_FOOTER_ABSENT = "<footer><p>Legal facts.</p></footer>"


def _directory_home(hero: str = _HERO_WITH_CTA, main: str = _MAIN_REAL, footer: str = _FOOTER_WITH_DISCLOSURE) -> str:
    return _PAGE_OPEN + _HEADER + hero + main + footer + _PAGE_CLOSE


_LEAD_GEN_TRUST = '<section data-atlas-c="trust-statistics-strip"><p>4.9 average rating</p></section>'
_LEAD_GEN_TRUST_PROSE_ONLY = "<p>We are a trusted, reliable service.</p>"
_LEAD_GEN_FORM = (
    '<form data-atlas-c="form-lead-quote" action="/" method="post">'
    "<p>Your request is shared with quote-matched providers.</p>"
    "<button>Submit</button></form>"
)


def _lead_generation_home(trust: str = _LEAD_GEN_TRUST, form: str = _LEAD_GEN_FORM) -> str:
    main = "<main id=\"main\">" + trust + form + "</main>"
    return _PAGE_OPEN + main + _PAGE_CLOSE


# --------------------------------------------------------------------------- #
# A. Gate registration
# --------------------------------------------------------------------------- #

class TestGateRegistration:
    def test_cg_cmp_010_registered_exactly_once(self):
        matches = [reg for reg in COMPONENT_GATE_REGISTRATIONS if reg.gate_id == "CG-CMP-010"]
        assert len(matches) == 1

    def test_cg_cmp_010_family_and_severity(self):
        reg = next(r for r in COMPONENT_GATE_REGISTRATIONS if r.gate_id == "CG-CMP-010")
        assert reg.family == GATE_FAMILY_CG_COMPOSITION
        assert reg.severity == GATE_SEVERITY_BLOCKING

    def test_no_new_gate_ids_added(self):
        # AES-WEB-002L.2 wires up a pre-existing registered gate; it does
        # not add one. The "73, not 63" + CG-STR-006 closed inventory
        # (constants/gates.py AMB-002I-02/04) stays at 74.
        assert len(COMPONENT_GATE_REGISTRATIONS) == 74

    def test_omitting_component_manifest_leaves_cg_cmp_010_deferred(self):
        report = _report_for(_directory_home(), commercial_strategy=_DIRECTORY)
        # Build the same report without component_manifest to prove the
        # omitted-input path independently of the helper's own default.
        no_manifest_report = QualityGateEngine().evaluate(
            bundle_from_html({"index.html": _directory_home()}),
            seo_package(), content_package(), _sa(),
        )
        assert "CG-CMP-010" in no_manifest_report.deferred_gate_ids
        assert "CG-CMP-010" not in report.deferred_gate_ids


# --------------------------------------------------------------------------- #
# B. Requirement resolution
# --------------------------------------------------------------------------- #

class TestRequirementResolution:
    def test_fact_extractor_reads_the_same_page_commercial_defaults_object(self):
        # §15 same-declaration-source invariant: no copied requirement
        # table. `is` identity, not just equal values.
        assert fact_extractor.PAGE_COMMERCIAL_DEFAULTS is PAGE_COMMERCIAL_DEFAULTS_VIA_CONSTANTS

    def test_no_defaults_declared_passes_trivially(self):
        present, missing = _commercial_requirement_facts("<main></main>", "category", _DIRECTORY)
        assert present is True
        assert missing == ()

    def test_unknown_strategy_passes_trivially(self):
        present, missing = _commercial_requirement_facts(_directory_home(), "home", "not_a_real_strategy")
        assert present is True
        assert missing == ()


# --------------------------------------------------------------------------- #
# C. Primary CTA
# --------------------------------------------------------------------------- #

class TestPrimaryCTA:
    def test_required_and_present_passes(self):
        present, missing = _commercial_requirement_facts(_directory_home(), "home", _DIRECTORY)
        assert present is True

    def test_required_and_absent_fails(self):
        present, missing = _commercial_requirement_facts(_directory_home(hero=_HERO_NO_CTA), "home", _DIRECTORY)
        assert present is False
        assert any("primary CTA" in m for m in missing)

    def test_wrong_href_fails(self):
        present, missing = _commercial_requirement_facts(_directory_home(hero=_HERO_WRONG_CTA), "home", _DIRECTORY)
        assert present is False
        assert any("primary CTA" in m for m in missing)

    def test_text_only_prose_does_not_satisfy_cta(self):
        # Adversarial: the CTA's own label text appears in prose, but with
        # no real <a href="#main"> anchor -- must still fail.
        present, missing = _commercial_requirement_facts(_directory_home(hero=_HERO_PROSE_CTA), "home", _DIRECTORY)
        assert present is False
        assert any("primary CTA" in m for m in missing)

    def test_optional_cta_absent_does_not_fail(self):
        # LEAD_GENERATION/home declares no primary_cta_href -- nothing to
        # verify, so a page with no CTA anchor at all still passes the CTA
        # sub-check (it may still fail on other requirements).
        present, missing = _commercial_requirement_facts(_lead_generation_home(), "home", _LEAD_GENERATION)
        assert not any("primary CTA" in m for m in missing)


# --------------------------------------------------------------------------- #
# D. Trust surfaces
# --------------------------------------------------------------------------- #

class TestTrustSurfaces:
    def test_required_and_present_passes(self):
        present, missing = _commercial_requirement_facts(_lead_generation_home(), "home", _LEAD_GENERATION)
        assert present is True

    def test_missing_fails_with_exact_requirement_named(self):
        present, missing = _commercial_requirement_facts(
            _lead_generation_home(trust=""), "home", _LEAD_GENERATION
        )
        assert present is False
        assert any("trust_adjacent_to_form" in m for m in missing)

    def test_unrelated_prose_does_not_satisfy_trust_requirement(self):
        # Adversarial: the word "trust" appears in real prose, but no real
        # trust.* component (no data-atlas-c="trust-*") is present.
        present, missing = _commercial_requirement_facts(
            _lead_generation_home(trust=_LEAD_GEN_TRUST_PROSE_ONLY), "home", _LEAD_GENERATION
        )
        assert present is False
        assert any("trust_adjacent_to_form" in m for m in missing)


# --------------------------------------------------------------------------- #
# E. Disclosure (DIRECTORY's declared "disclosure" trust surface)
# --------------------------------------------------------------------------- #

class TestDisclosure:
    def test_present_passes(self):
        present, _missing = _commercial_requirement_facts(_directory_home(), "home", _DIRECTORY)
        assert present is True

    def test_absent_footer_fails(self):
        present, missing = _commercial_requirement_facts(
            _directory_home(footer=_FOOTER_ABSENT), "home", _DIRECTORY
        )
        assert present is False
        assert any("disclosure" in m for m in missing)

    def test_footer_present_without_disclosure_paragraph_fails(self):
        present, missing = _commercial_requirement_facts(
            _directory_home(footer=_FOOTER_NO_DISCLOSURE), "home", _DIRECTORY
        )
        assert present is False
        assert any("disclosure" in m for m in missing)

    def test_no_declared_requirement_means_no_disclosure_check(self):
        # A role with no PAGE_COMMERCIAL_DEFAULTS entry (e.g. category)
        # never requires disclosure -- not every page becomes a disclosure
        # page.
        present, missing = _commercial_requirement_facts(
            _directory_home(footer=_FOOTER_ABSENT), "category", _DIRECTORY
        )
        assert present is True
        assert missing == ()


# --------------------------------------------------------------------------- #
# F. Commercially empty main
# --------------------------------------------------------------------------- #

class TestCommerciallyEmptyMain:
    def test_real_commercial_body_passes(self):
        present, missing = _commercial_requirement_facts(_directory_home(), "home", _DIRECTORY)
        assert present is True

    def test_empty_main_fails(self):
        present, missing = _commercial_requirement_facts(
            _directory_home(main=_MAIN_EMPTY), "home", _DIRECTORY
        )
        assert present is False
        assert any("main region is empty" in m for m in missing)

    def test_shell_only_main_fails(self):
        present, missing = _commercial_requirement_facts(
            _directory_home(main=_MAIN_SHELL_ONLY), "home", _DIRECTORY
        )
        assert present is False
        assert any("no non-shell commercial content" in m for m in missing)

    def test_header_and_footer_content_does_not_count_as_main_content(self):
        # Adversarial: header/footer both carry real, non-shell components
        # (nav, legal footer) -- neither is inside <main>, so an empty
        # <main> must still fail.
        html = _directory_home(main=_MAIN_EMPTY)
        assert 'data-atlas-c="legal-footer-directory"' in html
        present, missing = _commercial_requirement_facts(html, "home", _DIRECTORY)
        assert present is False
        assert any("main region is empty" in m for m in missing)

    def test_valid_directory_home_passes_whole_check(self):
        present, missing = _commercial_requirement_facts(_directory_home(), "home", _DIRECTORY)
        assert present is True and missing == ()

    def test_valid_lead_generation_home_main_not_flagged_empty(self):
        present, missing = _commercial_requirement_facts(_lead_generation_home(), "home", _LEAD_GENERATION)
        assert not any("main region" in m for m in missing)

    def test_one_valid_surface_hidden_among_empty_shells_still_counts(self):
        # Two empty layout.section.container shells plus one real form --
        # the real, pre-existing shape LEAD_GENERATION/home's recipe
        # produces today (hero.leadgen.offer unregistered, trust.
        # statistics.strip categorically unbindable).
        html = (
            _PAGE_OPEN
            + '<main id="main">'
            + '<section data-atlas-c="layout-section-container"></section>'
            + '<section data-atlas-c="layout-section-container"></section>'
            + _LEAD_GEN_FORM
            + "</main>"
            + _PAGE_CLOSE
        )
        present, missing = _commercial_requirement_facts(html, "home", _LEAD_GENERATION)
        assert not any("main region" in m for m in missing)


# --------------------------------------------------------------------------- #
# G. Strategy isolation
# --------------------------------------------------------------------------- #

class TestStrategyIsolation:
    def test_directory_requirements_do_not_leak_into_lead_generation(self):
        # A page satisfying LEAD_GENERATION's requirements is not
        # evaluated against DIRECTORY's disclosure/CTA requirements.
        present, missing = _commercial_requirement_facts(_lead_generation_home(), "home", _LEAD_GENERATION)
        assert present is True
        assert not any("disclosure" in m for m in missing)

    def test_lead_generation_requirements_do_not_leak_into_directory(self):
        present, missing = _commercial_requirement_facts(_directory_home(), "home", _DIRECTORY)
        assert present is True
        assert not any("trust_adjacent_to_form" in m for m in missing)

    def test_same_html_different_declared_strategy_can_disagree(self):
        # The DIRECTORY-valid page has no form.lead.quote and no
        # trust.statistics.strip -- evaluated as LEAD_GENERATION/home it
        # must fail (both requirements genuinely absent).
        present, missing = _commercial_requirement_facts(_directory_home(), "home", _LEAD_GENERATION)
        assert present is False


# --------------------------------------------------------------------------- #
# I. QualityReport integration
# --------------------------------------------------------------------------- #

class TestQualityReportIntegration:
    def test_commercial_finding_appears_in_the_same_report(self):
        report = _report_for(_directory_home(main=_MAIN_EMPTY), commercial_strategy=_DIRECTORY)
        ids = {g.gate_id for g in report.gate_results}
        assert "CG-CMP-010" in ids
        # Every other evaluated gate is still present in the same report --
        # no separate commercial report type.
        assert "CG-RND-002" in ids

    def test_blocking_failure_prevents_certification(self):
        report = _report_for(_directory_home(main=_MAIN_EMPTY), commercial_strategy=_DIRECTORY)
        assert _cmp_010(report).passed is False
        assert report.certified is False

    def test_deterministic_finding_order_across_repeated_calls(self):
        html = _directory_home(hero=_HERO_NO_CTA, footer=_FOOTER_NO_DISCLOSURE)
        first = _report_for(html, commercial_strategy=_DIRECTORY)
        second = _report_for(html, commercial_strategy=_DIRECTORY)
        assert _cmp_010(first).details == _cmp_010(second).details

    def test_component_manifest_recorded_in_source_hashes(self):
        report = _report_for(_directory_home(), commercial_strategy=_DIRECTORY)
        assert "component_manifest" in report.source_hashes

    def test_source_hashes_omit_component_manifest_when_not_supplied(self):
        report = QualityGateEngine().evaluate(
            bundle_from_html({"index.html": _directory_home()}),
            seo_package(), content_package(), _sa(),
        )
        assert "component_manifest" not in report.source_hashes


# --------------------------------------------------------------------------- #
# J. Architecture invariants
# --------------------------------------------------------------------------- #

class TestLeadGenerationRealChain:
    """AES-WEB-002L.2 §11: drives the real QualityGateEngine.evaluate()
    (not the unit-level _commercial_requirement_facts helper) for
    LEAD_GENERATION/home -- fixture only, matching AES-WEB-002L.1's own
    "structural proof, not a commercially validated business" scope."""

    def test_a_valid_composition_passes(self):
        report = _report_for(_lead_generation_home(), commercial_strategy=_LEAD_GENERATION)
        assert _cmp_010(report).passed is True

    def test_b_missing_trust_surface_is_a_deterministic_blocking_finding(self):
        report = _report_for(
            _lead_generation_home(trust=""), commercial_strategy=_LEAD_GENERATION
        )
        result = _cmp_010(report)
        assert result.passed is False
        assert result.severity is result.severity.BLOCKING
        assert "trust_adjacent_to_form" in result.details

    def test_d_empty_commercial_main_is_a_deterministic_blocking_finding(self):
        html = _PAGE_OPEN + '<main id="main"></main>' + _PAGE_CLOSE
        report = _report_for(html, commercial_strategy=_LEAD_GENERATION)
        result = _cmp_010(report)
        assert result.passed is False
        assert "main region is empty" in result.details


class TestArchitectureInvariants:
    def test_quality_gate_engine_version_is_1_1_0(self):
        assert ENGINE_VERSIONS["quality_gate_engine"] == "1.1.0"

    def test_no_new_engine_class_introduced(self):
        assert QualityGateEngine.__module__ == "engines.website_generation.gates.quality_gate_engine"

    def test_gates_package_imports_only_contracts_constants_gates(self):
        # Mirrors test_import_audit.py's own mechanically-enforced boundary
        # (this test would have caught the assembly/-import mistake this
        # delivery made and fixed during implementation).
        import ast
        import inspect

        from engines.website_generation.gates import quality_gate_engine as mod

        tree = ast.parse(inspect.getsource(mod))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("engines.website_generation."):
                    top = node.module.split(".")[2] if len(node.module.split(".")) > 2 else ""
                    assert top in ("contracts", "constants", "gates"), (
                        "quality_gate_engine.py has out-of-matrix import %r" % node.module
                    )
