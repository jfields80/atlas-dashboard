"""Demand Research service layer (AES-SEO-001 §3.4).

The I/O side of the Demand Mapping subsystem: project adapters, and — in
later phases — evidence providers, budget enforcement, and approval
orchestration. All filesystem/network/credential access for the subsystem
lives here; the deterministic core in ``engines/demand_mapping/`` never
touches any of it.

Phase B ships project inventory adapters only (``adapters/``).
"""
