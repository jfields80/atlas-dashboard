"""
scripts/generate_local_demo_site.py

================================================================================
LOCAL DEVELOPMENT / VISUAL DEMO HARNESS
NOT THE PRODUCTION WEBSITE GENERATION PIPELINE
================================================================================

Internal sequencing label: AES-WEB-002J.13.

Builds a small, deterministic demo static site by driving the REAL
Renderer -> Assembly Engine -> Quality Gate Engine -> SiteBundleRepository
over a handcrafted, fully-bound fixture, then writes it to a local directory
you can open in a browser for visual inspection.

What this harness is (Level B):

  * It BEGINS at fully-bound rendering inputs. Component SELECTION is
    handcrafted and content BINDING is handcrafted (see
    tests/website_generation/fixtures/local_demo_site.py). The real Component
    Engine is NOT invoked -- its output is not yet Renderer-consumable because
    value-layer binding is deferred (AES-WEB-001 §5.5).
  * The Renderer, Assembly Engine, Quality Gate Engine, and
    SiteBundleRepository ARE the real engines and are genuinely exercised.

What this harness is NOT:

  * NOT a full end-to-end / specification-to-site / business-brief-to-website
    generator, NOT a production generator, NOT autonomous.
  * It does NOT grant certification. Blocking gates remain deferred and
    ``certified`` is always False in this phase.
  * Generated output is for local inspection only. No deployment, no server,
    no browser launch, no network, no AI.

Run from:

    C:\\Atlas\\atlas-dashboard

Example:

    python scripts\\generate_local_demo_site.py
    python scripts\\generate_local_demo_site.py --output generated-sites/demo --build-id demo-1 --write-quality-report
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from engines.website_generation.assembly.assembly_engine import AssemblyEngine
from engines.website_generation.contracts.artifacts import (
    QualityReport,
    SiteBundle,
    model_to_dict,
)
from engines.website_generation.contracts.enums import GateSeverity
from engines.website_generation.contracts.errors import (
    AssemblyError,
    GateExecutionError,
    RenderError,
    SiteBundleRepositoryError,
)
from engines.website_generation.gates.quality_gate_engine import QualityGateEngine
from engines.website_generation.rendering.renderer import Renderer
from repositories.site_bundle_repository import (
    MANIFEST_FILENAME,
    SiteBundleRepository,
)

HARNESS_NAME = "Atlas Local Demo Website Harness (LOCAL DEV / VISUAL DEMO -- NOT PRODUCTION)"
DEFAULT_OUTPUT = "generated-sites/atlas-local-demo"
QUALITY_REPORT_FILENAME = "quality_report.json"

_FIXTURE_PATH = _REPO_ROOT / "tests" / "website_generation" / "fixtures" / "local_demo_site.py"


def load_demo_fixture():
    """Load the self-contained demo-fixture module by file path.

    The fixture lives under ``tests/`` but ``tests`` is not an importable
    package from a plain script (a site-packages ``tests`` shadows it), so it
    is loaded by location. The module is registered in ``sys.modules`` before
    execution (required for its frozen dataclass to introspect its own
    annotations)."""
    spec = importlib.util.spec_from_file_location("local_demo_site", _FIXTURE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@dataclass(frozen=True)
class HarnessResult:
    """Deterministic summary of one harness build (absolute ``destination`` is
    the only environment-dependent field)."""

    destination: str
    index_path: str
    manifest_path: str
    page_count: int
    file_count: int
    bundle_hash: str
    evaluated_gate_count: int
    passed_gate_count: int
    failed_gate_count: int
    deferred_gate_count: int
    certified: bool


def render_assemble_gate(fixture_module) -> Tuple[SiteBundle, QualityReport, object]:
    """Run the real Renderer -> Assembly -> Quality Gate chain over the demo
    fixture. Returns ``(bundle, quality_report, inputs)``."""
    inputs = fixture_module.build_local_demo_inputs()
    registry = fixture_module.demo_registry()
    rendered = Renderer(registry).render(
        inputs.layout, inputs.manifest, inputs.content, inputs.brand
    )
    bundle = AssemblyEngine().assemble(rendered, inputs.seo, inputs.brand)
    report = QualityGateEngine().evaluate(
        bundle, inputs.seo, inputs.content, inputs.site_architecture
    )
    return bundle, report, inputs


def _blocking_failures(report: QualityReport) -> List[str]:
    """Evaluated gates that FAILED at BLOCKING severity (deferred gates are
    not failures)."""
    return [
        g.gate_id
        for g in report.gate_results
        if not g.passed and g.severity is GateSeverity.BLOCKING
    ]


def _serialize_quality_report(report: QualityReport) -> bytes:
    """Deterministic UTF-8/LF JSON for the optional sidecar (sorted keys,
    trailing newline). Not a certificate and never part of the bundle."""
    text = json.dumps(
        model_to_dict(report),
        sort_keys=True,
        indent=2,
        ensure_ascii=False,
        separators=(",", ": "),
    )
    return (text + "\n").encode("utf-8")


def _gate_summary_lines(report: QualityReport) -> List[str]:
    passed = sum(1 for g in report.gate_results if g.passed)
    failed = sum(1 for g in report.gate_results if not g.passed)
    lines = [
        "  evaluated gates : %d" % len(report.gate_results),
        "  passed          : %d" % passed,
        "  failed          : %d" % failed,
        "  deferred gates  : %d" % len(report.deferred_gate_ids),
        "  certified       : %s (blocking gates remain deferred this phase)"
        % report.certified,
    ]
    for gate in report.gate_results:
        if not gate.passed:
            lines.append("  FAILED %s: %s" % (gate.gate_id, gate.details))
    return lines


def run(
    output: str,
    build_id: Optional[str] = None,
    write_quality_report: bool = False,
    stream=None,
) -> Tuple[int, Optional[HarnessResult]]:
    """Execute the harness. Returns ``(exit_code, result)``; ``result`` is
    None on any failure. Never raises for an expected engine/repository
    failure -- those are printed and reported via the exit code."""
    out = stream if stream is not None else sys.stdout

    def emit(line: str = "") -> None:
        print(line, file=out)

    try:
        fixture_module = load_demo_fixture()
        bundle, report, _inputs = render_assemble_gate(fixture_module)
    except (RenderError, AssemblyError, GateExecutionError) as exc:
        emit("ERROR: engine malfunction during build: %s: %s" % (type(exc).__name__, exc))
        emit("  diagnostics: %r" % getattr(exc, "diagnostics", {}))
        return 1, None

    blocking = _blocking_failures(report)
    if blocking:
        emit("BUILD REJECTED: evaluated BLOCKING gate(s) failed; not materializing.")
        for line in _gate_summary_lines(report):
            emit(line)
        return 1, None

    destination = Path(output)
    try:
        materialization = SiteBundleRepository().materialize(
            bundle, destination, build_id=build_id
        )
    except SiteBundleRepositoryError as exc:
        emit("ERROR: could not materialize the site bundle: [%s] %s" % (exc.category, exc))
        return 1, None

    index_path = destination / "index.html"
    if write_quality_report:
        (destination / QUALITY_REPORT_FILENAME).write_bytes(
            _serialize_quality_report(report)
        )

    result = HarnessResult(
        destination=str(destination.resolve()),
        index_path=str(index_path.resolve()),
        manifest_path=materialization.manifest_path,
        page_count=len(bundle.file_map) - _non_page_file_count(bundle),
        file_count=len(bundle.file_map),
        bundle_hash=bundle.bundle_hash,
        evaluated_gate_count=len(report.gate_results),
        passed_gate_count=sum(1 for g in report.gate_results if g.passed),
        failed_gate_count=sum(1 for g in report.gate_results if not g.passed),
        deferred_gate_count=len(report.deferred_gate_ids),
        certified=report.certified,
    )

    emit(HARNESS_NAME)
    emit("  (component selection + content binding are handcrafted; Level B)")
    emit("  output directory: %s" % result.destination)
    emit("  pages           : %d" % result.page_count)
    emit("  files           : %d" % result.file_count)
    emit("  bundle hash     : %s" % result.bundle_hash)
    for line in _gate_summary_lines(report):
        emit(line)
    emit("  manifest        : %s" % result.manifest_path)
    if write_quality_report:
        emit("  quality report  : %s" % QUALITY_REPORT_FILENAME)
    emit("  index.html      : %s" % result.index_path)
    emit("  open it manually in a browser via file:// -- no server required.")
    return 0, result


def _non_page_file_count(bundle: SiteBundle) -> int:
    """styles.css + sitemap.xml + robots.txt (+ manifest is not in file_map)."""
    return sum(
        1 for path in bundle.file_map if not path.endswith(".html")
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="generate_local_demo_site.py",
        description=(
            "LOCAL DEV / VISUAL DEMO HARNESS -- NOT the production website "
            "generation pipeline. Drives the real Renderer, Assembly, Quality "
            "Gate, and SiteBundleRepository over a handcrafted, fully-bound "
            "fixture (component selection + content binding are handcrafted; "
            "Level B). Does not certify; blocking gates remain deferred."
        ),
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help="Output directory (must be absent or empty). Default: %s" % DEFAULT_OUTPUT,
    )
    parser.add_argument(
        "--build-id",
        default=None,
        help="Optional build id recorded in bundle_manifest.json. Omitted if not given.",
    )
    parser.add_argument(
        "--write-quality-report",
        action="store_true",
        help="Also write %s (a report, NOT a certificate) inside the output directory."
        % QUALITY_REPORT_FILENAME,
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    exit_code, _result = run(
        output=args.output,
        build_id=args.build_id,
        write_quality_report=args.write_quality_report,
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
