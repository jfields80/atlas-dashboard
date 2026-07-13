"""Quality gate package (AES-WEB-002I check families + AES-WEB-002J.11
Quality Gate Engine).

AES-WEB-001 Part 2 defines this package as the home of the Quality Gate
Engine (``quality_gate_engine.py``, AES-WEB-001 §5.10) plus one check module
per gate family. It was built in two authorized stages:

* AES-WEB-002I built the ``checks/`` subpackage: 51 pure, individually
  testable gate-check functions registered as data in ``constants/gates.py``,
  validated two-fixture-law style against a synthetic fact vocabulary
  (``checks/__init__.py``). At that time no Quality Gate Engine, Renderer, or
  Assembly existed, so the §31 acceptance condition ("Quality Gate Engine
  runs the extended list deterministically") was explicitly deferred "to a
  future sprint once the Quality Gate Engine and a real Renderer exist."
* AES-WEB-002J.11 builds that engine, now that the Renderer (J.8/J.9) and
  Assembly (J.10) exist: ``quality_gate_engine.py`` (the §5.10
  ``QualityGateEngine``) plus ``fact_extractor.py`` (deterministic static
  extraction of the gate-read facts a real ``SiteBundle``'s HTML supplies).
  The engine evaluates every gate whose facts a static HTML scan can
  honestly derive and reports the rest as ``deferred_gate_ids`` -- it never
  feeds a synthetic default to a gate and calls it passed (the AES-005A
  honesty lesson). The synthetic ``checks/`` remain the contract tests,
  unchanged.

This package is independent of the legacy ``engines/website_generator``
package (which has its own, unrelated ``quality_gate.py`` — see that
package's own docstring), and of ``engines/website_intelligence``.
"""

from __future__ import annotations

from engines.website_generation.gates.quality_gate_engine import QualityGateEngine

__all__ = ["QualityGateEngine"]
