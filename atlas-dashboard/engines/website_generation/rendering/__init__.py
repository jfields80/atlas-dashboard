"""Renderer package (AES-WEB-001 §5.7; AES-WEB-002 §20).

Public: :class:`~engines.website_generation.rendering.renderer.Renderer`.
Internal (not exported from the top-level ``engines.website_generation``
package, matching the ``LayoutEngineInterface``/``LayoutCompositionError``
precedent): ``RendererInterface``, ``RenderError``, ``EMITTER_TABLE``, and
every ``emitters_*`` module.
"""

from engines.website_generation.rendering.renderer import Renderer

__all__ = ["Renderer"]
