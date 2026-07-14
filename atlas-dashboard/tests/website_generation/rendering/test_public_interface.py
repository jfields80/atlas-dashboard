"""Renderer public-interface tests (AES-WEB-002J.8; AES-WEB-001 §5.7).

Covers: public export, internal-helper concealment, engine version
registration, constructor injection, and RendererInterface conformance.
"""

from __future__ import annotations

import pytest

import engines.website_generation as wge
from engines.website_generation.contracts.errors import RenderError
from engines.website_generation.contracts.interfaces import (
    ComponentRegistryView,
    RendererInterface,
)
from engines.website_generation.rendering.renderer import Renderer

from . import real_brand_package, real_registry


class TestPublicExport:
    def test_renderer_is_exported(self):
        assert "Renderer" in wge.__all__
        assert wge.Renderer is Renderer

    def test_renderer_interface_not_exported(self):
        assert "RendererInterface" not in wge.__all__

    def test_render_error_not_exported(self):
        assert "RenderError" not in wge.__all__

    def test_rendered_page_set_v1_not_exported(self):
        assert "RenderedPageSetV1" not in wge.__all__


class TestEngineVersion:
    def test_renderer_version_registered(self):
        # AES-WEB-002J.15 bumped 1.0.0 -> 1.1.0 for the applied visual CSS
        # layer (ADR-WEB-VISUAL-TOKEN-APPLICATION; §11.4 snapshot-level change).
        # AES-WEB-002K.1 bumps 1.1.0 -> 1.2.0 for optional render_data
        # threading (real hyperlinks/enrichment; contracts/versions.py).
        assert wge.ENGINE_VERSIONS["renderer"] == "1.2.0"

    def test_renderer_class_version_matches_registry(self):
        assert Renderer.version == wge.ENGINE_VERSIONS["renderer"]


class TestConstructorInjection:
    def test_renderer_requires_registry(self):
        with pytest.raises(TypeError):
            Renderer()  # type: ignore[call-arg]

    def test_renderer_accepts_registry_view(self):
        registry = real_registry()
        renderer = Renderer(registry)
        assert renderer._registry is registry

    def test_renderer_implements_interface(self):
        assert issubclass(Renderer, RendererInterface)
        registry = real_registry()
        assert isinstance(Renderer(registry), RendererInterface)


class TestRenderErrorShape:
    def test_render_error_is_website_generation_error(self):
        err = RenderError("boom", diagnostics={"x": 1})
        assert err.stage == "rendering"
        assert err.retryable is False
        assert err.diagnostics == {"x": 1}

    def test_render_error_stage_defaults_to_rendering(self):
        assert RenderError("boom").stage == "rendering"


class TestRegistryProtocolOnly:
    def test_component_registry_view_is_abc(self):
        # The Renderer's constructor type-hints ComponentRegistryView (a
        # protocol), never the concrete ComponentRegistry class directly --
        # rendering/ has no legal import path to components/ (AES-WEB-002J.7
        # decision D-3 precedent).
        assert ComponentRegistryView.__abstractmethods__
