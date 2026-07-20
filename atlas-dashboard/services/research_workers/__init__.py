"""ATLAS-WORKERS-001 -- Atlas research-worker pilot.

The first controlled Atlas research worker: a HOTEL_POLICY_RESEARCH extraction
worker plus an offline, deterministic benchmark. This package owns the worker
CONTRACT that OpenClaw will operate later.

Ownership boundary (do not blur):
  * AI model      -- reads supplied source content, proposes structured facts.
  * OpenClaw      -- schedules assignments, discovers sources, retrieves pages,
                     invokes this worker. (Not installed in this phase.)
  * Atlas (here)  -- owns schemas, validation, evidence, queues, publishing,
                     and the READY/REVIEW/REJECT decision. The worker NEVER
                     approves or publishes a record.

The worker analyzes ONLY the documents supplied in its assignment; it never
browses implicitly and never makes a network call unless explicitly authorized
through the spending airlock (services.research_workers.providers).
"""
