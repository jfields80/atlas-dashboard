"""QualityGateEngine -- (SiteBundle, SEOPackage, ContentPackage,
SiteArchitecture) -> QualityReport (AES-WEB-001 §5.10 / Part 2).

Internal sequencing label: AES-WEB-002J.11. Executes the registered gate
list (``constants/gates.py``) in declared order against the assembled
artifacts and returns a deterministic ``QualityReport``. Every gate content
failure is a typed ``GateResult`` (``passed=False``) -- never an exception
(§5.10: "Every gate returns a typed result ... raising is reserved for gate
malfunction"). Only gate *malfunction* (no HTML in the bundle, a check that
itself raises) is a ``GateExecutionError``.

Honest real-output coverage (the AES-005A quality-gate lesson, §5.10). The
73 AES-WEB-002 §21 component gates were built (AES-WEB-002I) to run against a
rich *synthetic* fact vocabulary (``gates/checks/``). Only the gates whose
every read-field a deterministic static HTML scan can honestly derive from
the real ``SiteBundle`` are evaluated here; the rest are reported in the
report's ``deferred_gate_ids`` -- never fed a fabricated default and falsely
passed. The evaluated set is the emitted-markup safety/structure family:

* CG-RND-002 (basic HTML structural conformance -- static subset),
  CG-RND-005 (no inline scripts / unapproved inline styles),
  CG-RND-006 (no-JS baseline present), CG-RND-008 (no duplicate DOM ids /
  no internal-metadata leakage), CG-RND-009 (no unsafe URLs);
* CG-CMP-005 (heading hierarchy), CG-CMP-006 (landmark hierarchy),
  CG-CMP-008 (no nested interactive controls).

Deferred (documented in the AES-WEB-002J.11 report): the remaining CG-RND
gates (need re-render/probes), all CG-CON/CG-COM/CG-RSP (need instance-level
binding facts the minimal ``ComponentManifest`` does not yet carry), all
CG-A11Y (need the resolved CSS cascade / layout: contrast, focus, touch
targets), all CG-SEO (need SEO-gate check functions and richer facts), the
CG-STR-006 reservation, and CG-RND-010 / structured-data (no JSON-LD exists
-- SEO Decision D4). These stay covered by their two-fixture synthetic
contract tests, which this delivery does not touch.

Deterministic, pure, serializable, byte-stable: the same four artifacts
always produce the same ``QualityReport``. No filesystem, network, CAS,
model, randomness, or clock/UUID access; no output is repaired and no input
is mutated. Report persistence is a repository concern (§9) -- this engine
writes nothing. Not wired into pipeline execution -- ``gating`` remains
``NOT_EXECUTED`` in the ``BuildManifest`` (``PHASE1_EXECUTED_STAGES`` is
unchanged by this module).
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Tuple

from engines.website_generation.constants.build import STAGE_GATING
from engines.website_generation.constants.gates import (
    COMPONENT_GATE_REGISTRATIONS,
    GATE_SEVERITY_BLOCKING,
    GATE_SEVERITY_INFO,
    GATE_SEVERITY_WARNING,
)
from engines.website_generation.contracts.artifacts import (
    ContentPackage,
    GateResult,
    QualityReport,
    SEOPackage,
    SiteArchitecture,
    SiteBundle,
    artifact_sha256,
)
from engines.website_generation.contracts.enums import ArtifactKind, GateSeverity
from engines.website_generation.contracts.errors import GateExecutionError
from engines.website_generation.contracts.interfaces import QualityGateEngineInterface
from engines.website_generation.contracts.versions import ENGINE_VERSIONS, SCHEMA_VERSIONS
from engines.website_generation.gates.checks import (
    CheckOutcome,
    SyntheticPage,
    SyntheticRenderedPage,
)
from engines.website_generation.gates.checks import composition_checks, rendering_checks
from engines.website_generation.gates.fact_extractor import (
    extract_page_composition_facts,
    extract_rendered_page_facts,
)

_SEVERITY_ENUM: Dict[str, GateSeverity] = {
    GATE_SEVERITY_BLOCKING: GateSeverity.BLOCKING,
    GATE_SEVERITY_WARNING: GateSeverity.WARNING,
    GATE_SEVERITY_INFO: GateSeverity.INFO,
}

# Fact kinds an evaluated gate's check function consumes.
_FACT_RENDERED = "rendered"       # SyntheticRenderedPage from extract_rendered_page_facts
_FACT_COMPOSITION = "composition" # SyntheticPage from extract_page_composition_facts

# The explicit, ordered set of gates this engine evaluates against real
# assembled HTML, each mapped to its tested check function (reused verbatim
# from gates/checks/ -- no logic duplication) and the fact kind whose every
# read-field the fact extractor honestly fills. No dynamic discovery; adding
# a gate here is a one-line, reviewable edit.
_EVALUATED_GATES: Tuple[Tuple[str, Callable[[Any], CheckOutcome], str], ...] = (
    ("CG-CMP-005", composition_checks.check_cg_cmp_005, _FACT_COMPOSITION),
    ("CG-CMP-006", composition_checks.check_cg_cmp_006, _FACT_COMPOSITION),
    ("CG-CMP-008", composition_checks.check_cg_cmp_008, _FACT_COMPOSITION),
    ("CG-RND-002", rendering_checks.check_cg_rnd_002, _FACT_RENDERED),
    ("CG-RND-005", rendering_checks.check_cg_rnd_005, _FACT_RENDERED),
    ("CG-RND-006", rendering_checks.check_cg_rnd_006, _FACT_RENDERED),
    ("CG-RND-008", rendering_checks.check_cg_rnd_008, _FACT_RENDERED),
    ("CG-RND-009", rendering_checks.check_cg_rnd_009, _FACT_RENDERED),
)

_EVALUATED_GATE_IDS = frozenset(gid for gid, _fn, _kind in _EVALUATED_GATES)

# The registry's severity per gate id (declared order preserved by the
# registry itself). Built once at import from the single source of truth.
_GATE_SEVERITY: Dict[str, str] = {
    reg.gate_id: reg.severity for reg in COMPONENT_GATE_REGISTRATIONS
}

# Every registered gate id, in the registry's declared (lexicographic) order.
_ALL_REGISTERED_GATE_IDS: Tuple[str, ...] = tuple(
    reg.gate_id for reg in COMPONENT_GATE_REGISTRATIONS
)


class QualityGateEngine(QualityGateEngineInterface):
    """Evaluate a deterministic ``QualityReport`` from the assembled
    artifacts (AES-WEB-001 §5.10)."""

    version = ENGINE_VERSIONS["quality_gate_engine"]

    def evaluate(
        self,
        site_bundle: SiteBundle,
        seo_package: SEOPackage,
        content_package: ContentPackage,
        site_architecture: SiteArchitecture,
    ) -> QualityReport:
        """Total function over structurally valid inputs. Neither input is
        mutated (all frozen); gate order, page order, and findings are pure
        functions of the inputs' declared content -- never of dict/set
        iteration order (AES-WEB-001 §1.1). Raises ``GateExecutionError``
        only on engine malfunction; every gate content verdict is a
        ``GateResult``. No partial report is returned on malfunction.
        """
        pages = self._html_pages(site_bundle)
        if not pages:
            raise GateExecutionError(
                "SiteBundle contains no HTML page to gate",
                stage=STAGE_GATING,
                diagnostics={"file_count": len(site_bundle.files)},
            )

        rendered_facts: List[Tuple[str, SyntheticRenderedPage]] = []
        composition_facts: List[Tuple[str, SyntheticPage]] = []
        for path, html in pages:
            rendered_facts.append((path, extract_rendered_page_facts(path, html)))
            composition_facts.append((path, extract_page_composition_facts(path, html)))

        gate_results: List[GateResult] = []
        execution_faults: List[Dict[str, str]] = []
        for gate_id, check, fact_kind in _EVALUATED_GATES:
            facts = rendered_facts if fact_kind == _FACT_RENDERED else composition_facts
            result = self._run_gate_over_pages(gate_id, check, facts, execution_faults)
            if result is not None:
                gate_results.append(result)

        if execution_faults:
            raise GateExecutionError(
                "Quality gate execution faulted; see diagnostics",
                stage=STAGE_GATING,
                diagnostics={"check_exceptions": execution_faults},
            )

        deferred = tuple(
            gid for gid in _ALL_REGISTERED_GATE_IDS if gid not in _EVALUATED_GATE_IDS
        )
        certified = self._compute_certified(gate_results, deferred)

        return QualityReport(
            schema_version=SCHEMA_VERSIONS[ArtifactKind.QUALITY_REPORT],
            artifact_kind=ArtifactKind.QUALITY_REPORT,
            source_hashes={
                "site_bundle": artifact_sha256(site_bundle),
                "seo_package": artifact_sha256(seo_package),
                "content_package": artifact_sha256(content_package),
                "site_architecture": artifact_sha256(site_architecture),
            },
            gate_results=tuple(gate_results),
            certified=certified,
            certificate=None,
            deferred_gate_ids=deferred,
        )

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _html_pages(site_bundle: SiteBundle) -> List[Tuple[str, str]]:
        """Every HTML page file in the bundle, sorted by path for
        deterministic evaluation order."""
        return sorted(
            ((bf.path, bf.content) for bf in site_bundle.files if bf.path.endswith(".html")),
            key=lambda item: item[0],
        )

    def _run_gate_over_pages(
        self,
        gate_id: str,
        check: Callable[[Any], CheckOutcome],
        facts: List[Tuple[str, Any]],
        execution_faults: List[Dict[str, str]],
    ) -> GateResult:
        """Run one gate's check across every page; the gate passes iff it
        passes on every page. A check that itself raises is an execution
        fault (recorded; surfaced as GateExecutionError), never a silent
        pass or a content failure."""
        failing: List[str] = []
        for path, page_facts in facts:
            try:
                outcome = check(page_facts)
            except Exception as exc:  # a check bug is a malfunction, not a verdict
                execution_faults.append(
                    {"gate_id": gate_id, "path": path, "error": repr(exc)}
                )
                continue
            if not outcome.passed:
                failing.append("%s: %s" % (path, outcome.details))

        severity = _SEVERITY_ENUM[_GATE_SEVERITY[gate_id]]
        if failing:
            details = "; ".join(failing)
        else:
            details = "%d page(s) evaluated; all pass" % len(facts)
        return GateResult(
            gate_id=gate_id,
            severity=severity,
            passed=not failing,
            details=details,
        )

    @staticmethod
    def _compute_certified(
        gate_results: List[GateResult], deferred: Tuple[str, ...]
    ) -> bool:
        """A LaunchCertificate is warranted only when every BLOCKING gate is
        evaluated and passing (§5.10). A deferred gate of BLOCKING severity
        means a blocking gate was *not* confirmed, so certification is
        honestly withheld -- this engine never certifies on the strength of
        gates it did not run."""
        for result in gate_results:
            if result.severity is GateSeverity.BLOCKING and not result.passed:
                return False
        for gate_id in deferred:
            if _GATE_SEVERITY.get(gate_id) == GATE_SEVERITY_BLOCKING:
                return False
        return True
