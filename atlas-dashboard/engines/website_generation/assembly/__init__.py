"""Assembly Engine package (AES-WEB-001 §5.9).

Public: :class:`~engines.website_generation.assembly.assembly_engine.AssemblyEngine`.
Internal (not exported from the top-level ``engines.website_generation``
package, matching the ``RendererInterface``/``RenderError`` precedent):
``AssemblyEngineInterface``, ``AssemblyError``, and the pure builder
primitives in ``assembly_builders``.
"""

from engines.website_generation.assembly.assembly_engine import AssemblyEngine

__all__ = ["AssemblyEngine"]
