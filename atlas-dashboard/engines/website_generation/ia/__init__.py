"""Information Architecture Engine package (AES-WEB-001 §5.3 / Part 2 /
Part 13 Phase 2).

Internal sequencing label: AES-WEB-002J.3. Deterministic, pure
``(BusinessSpec, BrandPackage) -> SiteArchitecture`` planning: page
inventory, route/slug derivation, page-role assignment, hierarchy, and
internal-link topology from spec taxonomy rules. No I/O, no clock, no
randomness, no AI, no network (§2.2/§3.2 purity invariants). No component
selection, no component-registry import, no content, no SEO, no layout, no
rendering (§5.3 boundary; AES-WEB-002 §26).

Approved operator scope for this delivery: exactly one home page plus one
deterministic category page per ``directory_taxonomy`` entry -- no city
pages, route/corridor pages, listing-profile page instances, geography
trees, inventory-backed structures, or saved-account surfaces (no such
inputs exist yet; BusinessSpec/BrandPackage are not modified to invent
them).

Operator decision carried through this delivery: not wired into pipeline
execution. ``PHASE1_EXECUTED_STAGES`` still records only
``spec_compilation``; ``ia_planning`` remains ``NOT_EXECUTED`` in the
``BuildManifest`` until an operator explicitly authorizes wiring it in.
"""

from engines.website_generation.ia.information_architecture_engine import (
    InformationArchitectureEngine,
)

__all__ = ["InformationArchitectureEngine"]
