"""Content Engine package (AES-WEB-001 §5.4 / Part 2).

Internal sequencing label: AES-WEB-002J.4. Deterministic validation
airlock: ``(SiteArchitecture, ContentCandidates, BusinessSpec) ->
ContentPackage``. Validates candidates against slot schemas and policy
constraints (banned phrases, placeholder markers, length bounds); never
authors, generates, rewrites, summarizes, expands, or varies copy -- there
is no phrase library, no sentence template, no runtime model call, no
network access, and no filesystem access anywhere in this package (Decision
A1). Copy authorship belongs to an operator or a future authorized
cognition phase.

Operator decision carried through this delivery: not wired into pipeline
execution. ``PHASE1_EXECUTED_STAGES`` still records only
``spec_compilation``; ``content_drafting`` and ``content_validation`` both
remain ``NOT_EXECUTED`` in the ``BuildManifest`` until an operator
explicitly authorizes wiring them in.
"""

from engines.website_generation.content.content_engine import ContentEngine

__all__ = ["ContentEngine"]
