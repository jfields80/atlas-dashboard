"""Atlas Demand Mapping subsystem (AES-SEO-001).

Deterministic core for page-opportunity planning: given frozen inventory
profiles and frozen evidence snapshots, decide which page opportunities may
deserve to exist, which must be deferred, and which must be rejected.

Phase A ships contracts only (AES-SEO-001 §23.1 Phase A). No profiling,
opportunity-generation, gate, provider, or persistence logic exists yet.

Import law (AES-SEO-001 §3.3): this package imports only the standard
library (minus the banned modules), pydantic, and itself. It never imports
services, repositories, routes, or any other engine package. Enforced by
``tests/demand_mapping/test_import_audit.py``.
"""
