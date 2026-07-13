"""Layout Engine package (AES-WEB-001 §5.6 / Part 2).

Internal sequencing label: AES-WEB-002J.7. Deterministic composer:
``(ComponentManifest, BrandPackage) -> LayoutPlan``. Groups each page's
resolved component instances into ``RegionKind`` regions, preserves
manifest page and component order, and records deterministic grid and
responsive placement drawn only from each component's own registry
contract and the injected ``BrandPackage`` tokens. Never selects
components or variants, never emits markup, CSS, or media queries.

Operator decision carried through this delivery: not wired into pipeline
execution. ``PHASE1_EXECUTED_STAGES`` still records only
``spec_compilation``; ``layout_composition`` remains ``NOT_EXECUTED`` in
the ``BuildManifest`` until an operator explicitly authorizes wiring it in.
"""

from engines.website_generation.layouts.layout_engine import LayoutEngine

__all__ = ["LayoutEngine"]
