"""Quality gate check modules (AES-WEB-002I — Component Gate Families).

AES-WEB-001 Part 2 defines this package as the future home of the Quality
Gate Engine (``quality_gate_engine.py``) plus one check module per gate
family. Per the AES-WEB-002I Architectural Preflight's Ambiguity Register
(decision AMB-002I-01, operator-approved), this delivery builds only the
``checks/`` subpackage: pure, individually testable gate-check functions
registered as data in ``constants/gates.py``. It does NOT build:

* ``quality_gate_engine.py`` (the engine that executes a registered gate
  list against a real ``SiteBundle`` — AES-WEB-001 Part 10, Part 13 Phase 3)
* a ``GateCheck`` abstract interface (``contracts/interfaces.py`` already
  documents this as deferred "until a phase consumes it" — that phase is
  not this one)
* ``engines/website_generation/rendering/`` (AES-WEB-001 Part 2, Part 13
  Phase 2 — never built; the standing AES-WEB-002B-H operator decision to
  keep the component system declarative-only continues through this
  delivery)

The acceptance condition stated in AES-WEB-002 §31 for this phase —
"Quality Gate Engine runs the extended list deterministically" — is
therefore explicitly NOT met by this delivery and remains deferred to a
future sprint once the Quality Gate Engine and a real Renderer exist.

This package is independent of the legacy ``engines/website_generator``
package (which has its own, unrelated ``quality_gate.py`` — see that
package's own docstring), and of ``engines/website_intelligence``.
"""

from __future__ import annotations
