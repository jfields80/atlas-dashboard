"""Determinism tests for J.9 components (AES-WEB-002J.9; AES-WEB-001
§1.1/§5.7, CG-RND-001).

Covers: identical inputs produce equal models / canonical JSON / artifact
hashes / byte-identical HTML+CSS across all 40 J.9 components; fresh Renderer
instances agree; registry construction order and emitter-table family order
do not affect output.
"""

from __future__ import annotations

import pytest

from engines.website_generation.components.registry import ComponentRegistry
from engines.website_generation.contracts.artifacts import (
    artifact_sha256,
    canonical_artifact_json,
)

from . import J9_COMPONENT_IDS, real_brand_package, real_registry, render_single_component


class TestPerComponentDeterminism:
    @pytest.mark.parametrize("component_id", J9_COMPONENT_IDS)
    def test_byte_identical_html_and_css(self, component_id):
        registry = real_registry()
        brand = real_brand_package()
        a = render_single_component(registry, brand, component_id, include_optional=True)
        b = render_single_component(registry, brand, component_id, include_optional=True)
        assert a.page_details[0].html == b.page_details[0].html
        assert a.shared_css == b.shared_css

    @pytest.mark.parametrize("component_id", J9_COMPONENT_IDS)
    def test_equal_models_and_hashes(self, component_id):
        registry = real_registry()
        brand = real_brand_package()
        a = render_single_component(registry, brand, component_id)
        b = render_single_component(registry, brand, component_id)
        assert a == b
        assert canonical_artifact_json(a) == canonical_artifact_json(b)
        assert artifact_sha256(a) == artifact_sha256(b)


class TestConstructionOrderIndependence:
    def test_reversed_registry_yields_same_render(self):
        registry_a = real_registry()
        definitions = list(registry_a.all_definitions())
        registry_b = ComponentRegistry(list(reversed(definitions)))
        brand = real_brand_package()
        for component_id in ("listing.card.sponsored", "form.lead.quote", "legal.statement.standard"):
            a = render_single_component(registry_a, brand, component_id, include_optional=True)
            b = render_single_component(registry_b, brand, component_id, include_optional=True)
            assert a.page_details[0].html == b.page_details[0].html


class TestEmitterTableOrderIndependence:
    def test_all_seven_family_tables_merge_order_independent(self):
        from engines.website_generation.rendering.emitters_discovery import (
            DISCOVERY_EMITTERS,
        )
        from engines.website_generation.rendering.emitters_layout_atoms import (
            LAYOUT_ATOMS_EMITTERS,
        )
        from engines.website_generation.rendering.emitters_listings_profiles import (
            LISTINGS_PROFILES_EMITTERS,
        )
        from engines.website_generation.rendering.emitters_monetization_status import (
            MONETIZATION_STATUS_EMITTERS,
        )
        from engines.website_generation.rendering.emitters_navigation import (
            NAVIGATION_EMITTERS,
        )
        from engines.website_generation.rendering.emitters_seo_editorial import (
            SEO_EDITORIAL_EMITTERS,
        )
        from engines.website_generation.rendering.emitters_trust_conversion import (
            TRUST_CONVERSION_EMITTERS,
        )

        tables = [
            LAYOUT_ATOMS_EMITTERS, NAVIGATION_EMITTERS, DISCOVERY_EMITTERS,
            LISTINGS_PROFILES_EMITTERS, TRUST_CONVERSION_EMITTERS,
            SEO_EDITORIAL_EMITTERS, MONETIZATION_STATUS_EMITTERS,
        ]
        forward = {}
        for t in tables:
            forward.update(t)
        backward = {}
        for t in reversed(tables):
            backward.update(t)
        assert set(forward) == set(backward)
        assert len(forward) == 72
