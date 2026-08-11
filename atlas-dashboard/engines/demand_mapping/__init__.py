"""Atlas Demand Mapping subsystem (AES-SEO-001).

Deterministic core for page-opportunity planning: given frozen inventory
profiles and frozen evidence snapshots, decide which page opportunities may
deserve to exist, which must be deferred, and which must be rejected.

Delivered so far: Phase A contracts (``contracts/``) and the Phase B
deterministic profiler (``profiling/``). Opportunity-generation, gate,
provider, and persistence logic belong to later phases (AES-SEO-001 §23.1)
and do not exist yet.

Import law (AES-SEO-001 §3.3): this package imports only the standard
library (minus the banned modules), pydantic, and itself. It never imports
services, repositories, routes, or any other engine package. Enforced by
``tests/demand_mapping/test_import_audit.py``.
"""
