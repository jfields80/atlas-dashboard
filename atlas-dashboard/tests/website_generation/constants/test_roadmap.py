"""Part 13 Phase 2 roadmap clarification tests (amendment A4).

The AES-WEB-001 Part 13 authority is an external document; amendment A4
(AES-WEB-002 §34.3-A4) is a roadmap clarification that IS recordable in the
repository against the Phase-1 code that already represents phase/roadmap
scope (``constants/build.py``). These tests assert the clarification wording
is represented in-repo — no external document is fabricated.
"""

from __future__ import annotations

from engines.website_generation.constants import build


class TestPhase2RoadmapClarification:
    def test_phase2_scope_superseded_by_wave_structure(self):
        assert build.PHASE2_SCOPE_SUPERSEDED_BY == "AES-WEB-002 A-K wave structure"

    def test_initial_phase2_proof_at_002d_exit(self):
        assert build.PHASE2_INITIAL_PROOF_MILESTONE == "AES-WEB-002D"

    def test_mvp_integration_proof_through_002j(self):
        assert build.MVP_INTEGRATION_PROOF_MILESTONE == "AES-WEB-002J"

    def test_certification_golden_boundary_is_002k(self):
        assert build.CERTIFICATION_GOLDEN_FIXTURE_BOUNDARY == "AES-WEB-002K"

    def test_clarification_documented_in_module(self):
        # The amendment rationale is recorded as documentation in the module
        # that owns Part 13 phase scope.
        import inspect

        source = inspect.getsource(build)
        assert "34.3-A4" in source
        assert "roadmap clarification" in source.lower()
