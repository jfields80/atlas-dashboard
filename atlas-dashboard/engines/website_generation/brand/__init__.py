"""Brand Engine package (AES-WEB-001 §5.2 / Part 2 / Part 13 Phase 2).

Internal sequencing label: AES-WEB-002J.2. Deterministic, pure
``BusinessSpec -> BrandPackage`` resolution: family classification, token
resolution (palette/type/spacing/radius/extended), WCAG 2.x contrast
evidence, and voice-profile assembly. No I/O, no clock, no randomness, no
AI, no network (§2.2/§3.2 purity invariants).

Operator decision carried through this delivery: not wired into pipeline
execution. ``PHASE1_EXECUTED_STAGES`` still records only
``spec_compilation``; ``brand_resolution`` remains ``NOT_EXECUTED`` in the
``BuildManifest`` until an operator explicitly authorizes wiring it in.
Component brand-affinity scoring likewise stays the documented no-op
(``components/selection/selector.py`` is untouched by this delivery).
"""

from engines.website_generation.brand.brand_engine import BrandEngine

__all__ = ["BrandEngine"]
