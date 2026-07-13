"""SEO Engine package (AES-WEB-001 §5.8 / Part 2).

Internal sequencing label: AES-WEB-002J.5. Deterministic compiler:
``(SiteArchitecture, ContentPackage, BusinessSpec) -> SEOPackage``. Compiles
titles (Decision D2), meta descriptions (Decision D1), self-canonical URLs
(Decision D3), the sitemap plan, and a fixed site-level robots plan
(Decision D5) from already-validated artifacts. Structured data is out of
scope for this delivery (Decision D4): this package never reads
``BrandPackage`` or ``ComponentManifest`` and never emits JSON-LD, schema
types, or any structured-data field.

Operator decision carried through this delivery: not wired into pipeline
execution. ``PHASE1_EXECUTED_STAGES`` still records only
``spec_compilation``; ``seo_compilation`` remains ``NOT_EXECUTED`` in the
``BuildManifest`` until an operator explicitly authorizes wiring it in.
"""

from engines.website_generation.seo.seo_engine import SEOEngine

__all__ = ["SEOEngine"]
