"""AES-WORK-001C -- consolidated, self-contained batch HTML report.

Renders ``<output_root>/batches/<batch_id>/report.html``: one page covering
every job in a batch run, in manifest order, with the exact operator
approve/reject commands already established by the single-source CLI
(``scripts/import_official_url.py``'s own "next:" line). Pure/deterministic:
``build_batch_report_html`` is a pure function of
``(BatchState, BatchManifest, batch_dir)`` -- ``batch_dir`` is only ever a
computation input (used to make candidate/report links relative to where
the report itself lives), never touched on disk by this function. No
clock, no randomness -- the same inputs always produce the same bytes
(Task 5/15).

No external CSS, no JavaScript, no external assets: every byte needed to
render the page lives in the file itself. No batch-level approval action is
ever rendered -- only the existing, unchanged per-candidate CLI commands
(never auto-run, never a form, never a button that POSTs anywhere).

Depends on batch.py for its contract types (BatchState/JobState/BatchManifest
and the JOB_*/RECOMMEND_* vocabulary) -- a one-directional dependency.
``batch.py`` imports this module back only via a deferred, function-local
import inside ``run_batch`` to avoid a circular top-level import.
"""

from __future__ import annotations

import os
import tempfile
from html import escape
from pathlib import Path

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.batch import (
    JOB_DONE,
    JOB_FAILED,
    JOB_PENDING,
    JOB_RUNNING,
    JOB_SKIPPED,
    BatchManifest,
    BatchState,
    JobState,
)

_TOTAL_ORDER = (
    ("jobs", "Jobs"), ("done", "Done"), ("failed", "Failed"),
    ("pending", "Pending"), ("running", "Running"), ("disabled", "Disabled"),
    ("ready", "READY"), ("review", "REVIEW"), ("reject", "REJECT"),
)

_STATE_BADGE_CLASS = {
    JOB_DONE: "badge-done", JOB_FAILED: "badge-failed",
    JOB_PENDING: "badge-pending", JOB_RUNNING: "badge-running",
    JOB_SKIPPED: "badge-skipped",
}

_RECOMMEND_BADGE_CLASS = {
    C.RECOMMEND_READY: "badge-ready", C.RECOMMEND_REVIEW: "badge-review",
    C.RECOMMEND_REJECT: "badge-reject",
}

_CSS = """
body{font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;margin:0;
  padding:2rem;background:#f7f7f8;color:#1a1a1a;}
h1{font-size:1.4rem;margin:0 0 .25rem;}
h2{font-size:1.1rem;margin:0 0 .5rem;}
.meta{color:#555;font-size:.85rem;margin-bottom:1.5rem;}
.meta code{background:#eee;padding:.1rem .3rem;border-radius:3px;}
table{border-collapse:collapse;margin-bottom:1.5rem;}
.totals td,.totals th{padding:.35rem .75rem;text-align:right;
  border:1px solid #ddd;background:#fff;}
.totals th{background:#eee;text-align:center;}
.job{background:#fff;border:1px solid #ddd;border-radius:6px;
  padding:1rem 1.25rem;margin-bottom:1rem;}
.job h3{margin:0 0 .5rem;font-size:1rem;}
.field{margin:.15rem 0;font-size:.85rem;}
.field .k{color:#555;display:inline-block;min-width:11rem;}
.field code,.cmd code{background:#f0f0f0;padding:.1rem .3rem;border-radius:3px;
  font-size:.8rem;word-break:break-all;}
.badge{display:inline-block;padding:.05rem .5rem;border-radius:10px;
  font-size:.75rem;font-weight:600;color:#fff;}
.badge-done{background:#2e7d32;}
.badge-failed{background:#c62828;}
.badge-pending{background:#9e9e9e;}
.badge-running{background:#1565c0;}
.badge-skipped{background:#6d4c41;}
.badge-ready{background:#2e7d32;}
.badge-review{background:#f9a825;color:#1a1a1a;}
.badge-reject{background:#c62828;}
.cmd{margin-top:.5rem;padding-top:.5rem;border-top:1px dashed #ddd;}
.cmd div{margin:.2rem 0;}
.links a{margin-right:1rem;}
.reasons{color:#8a5a00;}
.error{color:#c62828;}
ul.sources{margin:.25rem 0;padding-left:1.25rem;font-size:.8rem;}
"""


def _fmt_relpath(path_str: str, batch_dir: Path) -> str:
    """A path relative to the report's own directory when practical
    (Task 5: "Use paths relative to the batch report when practical"),
    falling back to the raw stored path string (e.g. cross-drive on
    Windows, or simply empty for a job with no candidate yet). HTML
    ``href`` values always use forward slashes regardless of platform --
    ``os.path.relpath`` returns OS-native separators (backslashes on
    Windows), which a browser will NOT treat as a path separator, so the
    result is normalized before use."""
    if not path_str:
        return ""
    try:
        rel = os.path.relpath(path_str, start=str(batch_dir))
    except ValueError:
        return path_str
    return rel.replace(os.sep, "/")


def _job_section(job_id: str, candidate_name: str, js: JobState, batch_dir: Path) -> str:
    state_badge = (
        '<span class="badge %s">%s</span>'
        % (_STATE_BADGE_CLASS.get(js.execution_state, ""), escape(js.execution_state)))
    rec_badge = ""
    if js.recommendation:
        rec_badge = (
            '<span class="badge %s">%s</span>'
            % (_RECOMMEND_BADGE_CLASS.get(js.recommendation, ""), escape(js.recommendation)))

    rows = [
        ("Execution state", state_badge),
        ("Last action", escape(js.last_action) if js.last_action else "&mdash;"),
        ("Fingerprint", "<code>%s</code>" % escape(js.fingerprint)),
        ("Run ID", escape(js.run_id) if js.run_id else "&mdash;"),
    ]
    if js.skip_reason:
        rows.append(("Skip reason", escape(js.skip_reason)))
    if js.recommendation:
        rows.append(("Recommendation", rec_badge))
    if js.recommendation_reasons:
        rows.append(("Reasons", '<span class="reasons">%s</span>'
                     % escape(", ".join(js.recommendation_reasons))))
    if js.error_type:
        rows.append(("Error", '<span class="error">%s: %s</span>'
                     % (escape(js.error_type), escape(js.error_message))))
    if js.provider or js.model or js.prompt_version:
        rows.append(("Provider / model / prompt", "%s / %s / %s" % (
            escape(js.provider) or "&mdash;", escape(js.model) or "&mdash;",
            escape(js.prompt_version) or "&mdash;")))
    if js.snapshot_hashes:
        rows.append(("Snapshot hashes", "<br>".join(
            "<code>%s</code>" % escape(h) for h in js.snapshot_hashes)))
    if js.provider_request_count or js.input_tokens or js.output_tokens:
        rows.append(("Usage", "%d provider request(s), %d input / %d output tokens%s" % (
            js.provider_request_count, js.input_tokens, js.output_tokens,
            (" (~$%s, pricing %s)" % (escape(js.estimated_cost_usd),
                                      escape(js.pricing_version))
             if js.estimated_cost_usd else ""))))

    fields_html = "\n".join(
        '<div class="field"><span class="k">%s</span>%s</div>' % (escape(label), value)
        for label, value in rows)

    sources_html = ""
    if js.source_outcomes:
        items = "".join(
            "<li><code>%s</code> %s &mdash; %s</li>"
            % (escape(sid), escape(role), escape(status))
            for sid, role, status in js.source_outcomes)
        sources_html = '<div class="field"><span class="k">Source outcomes</span></div><ul class="sources">%s</ul>' % items

    links = []
    cmd_html = ""
    if js.candidate_path:
        candidate_rel = _fmt_relpath(js.candidate_path, batch_dir)
        links.append('<a href="%s">candidate JSON</a>' % escape(candidate_rel, quote=True))
        # The exact commands the existing single-source CLI itself prints
        # (scripts/import_official_url.py) -- never a new/batch-level action.
        approve_cmd = ("python scripts/approve_import_candidate.py --candidate %s "
                       "--decision approve" % js.candidate_path)
        reject_cmd = ("python scripts/approve_import_candidate.py --candidate %s "
                      "--decision reject" % js.candidate_path)
        cmd_html = (
            '<div class="cmd">'
            '<div><code>%s</code></div>'
            '<div><code>%s</code></div>'
            "</div>" % (escape(approve_cmd), escape(reject_cmd)))
    if js.report_path:
        report_rel = _fmt_relpath(js.report_path, batch_dir)
        links.append('<a href="%s">candidate report</a>' % escape(report_rel, quote=True))
    links_html = ('<div class="field links">%s</div>' % " ".join(links)) if links else ""

    return (
        '<div class="job">'
        "<h3>%s &mdash; %s</h3>"
        "%s\n%s\n%s\n%s"
        "</div>"
    ) % (escape(job_id), escape(candidate_name) or "&mdash;",
        fields_html, sources_html, links_html, cmd_html)


def build_batch_report_html(state: BatchState, manifest: BatchManifest, batch_dir) -> str:
    """Pure function: identical ``(state, manifest, batch_dir)`` input
    always produces identical HTML output. Job order is always manifest
    order, never completion order. ``batch_dir`` is the directory
    report.html will actually be written to (candidate/report links are
    computed relative to it, per Task 5) -- it never touches disk here,
    it is only ever a computation input."""
    batch_dir = Path(batch_dir)
    totals = {k: 0 for k, _label in _TOTAL_ORDER}
    totals["jobs"] = len(state.jobs)
    by_id = {js.job_id: js for js in state.jobs}
    for job in manifest.jobs:
        js = by_id.get(job.job_id)
        if js is None:
            continue
        if js.execution_state == JOB_DONE:
            totals["done"] += 1
        elif js.execution_state == JOB_FAILED:
            totals["failed"] += 1
        elif js.execution_state == JOB_PENDING:
            totals["pending"] += 1
        elif js.execution_state == JOB_RUNNING:
            totals["running"] += 1
        elif js.execution_state == JOB_SKIPPED:
            totals["disabled"] += 1
        if js.recommendation == C.RECOMMEND_READY:
            totals["ready"] += 1
        elif js.recommendation == C.RECOMMEND_REVIEW:
            totals["review"] += 1
        elif js.recommendation == C.RECOMMEND_REJECT:
            totals["reject"] += 1

    totals_row = "".join(
        "<th>%s</th>" % escape(label) for _key, label in _TOTAL_ORDER)
    totals_vals = "".join(
        "<td>%d</td>" % totals[key] for key, _label in _TOTAL_ORDER)

    usage = {"provider_request_count": 0, "input_tokens": 0, "output_tokens": 0}
    for js in state.jobs:
        usage["provider_request_count"] += js.provider_request_count
        usage["input_tokens"] += js.input_tokens
        usage["output_tokens"] += js.output_tokens

    jobs_html = "\n".join(
        _job_section(job.job_id, job.candidate_name, by_id[job.job_id], batch_dir)
        for job in manifest.jobs if job.job_id in by_id)

    title = "Batch report: %s" % escape(state.batch_id)
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>%s</title>
<style>%s</style>
</head>
<body>
<h1>%s</h1>
<div class="meta">
  <div><span class="field-k">batch_name:</span> %s</div>
  <div>manifest_hash: <code>%s</code></div>
  <div>extractor: <code>%s</code> &middot; model: <code>%s</code> &middot; observed_at: <code>%s</code></div>
  <div>importer_version: <code>%s</code> &middot; aggregation_version: <code>%s</code></div>
  <div>provider requests: %d &middot; input tokens: %d &middot; output tokens: %d</div>
</div>
<h2>Totals</h2>
<table class="totals">
<tr>%s</tr>
<tr>%s</tr>
</table>
<h2>Jobs</h2>
%s
</body>
</html>
""" % (
        title, _CSS, title,
        escape(manifest.batch_name), escape(state.manifest_hash),
        escape(state.extractor), escape(state.model), escape(state.observed_at),
        escape(C.IMPORTER_VERSION), escape(C.AGGREGATION_VERSION),
        usage["provider_request_count"], usage["input_tokens"], usage["output_tokens"],
        totals_row, totals_vals, jobs_html,
    )


def _atomic_write_text(path, text: str) -> None:
    """Independent atomic writer for report.html: same-directory temp file
    + os.replace, mirroring (but not importing) batch.py's own
    ``_atomic_write_json`` -- the same established repository idiom, kept
    as a small deliberate duplication rather than a cross-module import,
    which is exactly what would reintroduce the batch.py<->batch_report.py
    cycle this module's docstring describes avoiding."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".part")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                pass
        os.replace(tmp_name, str(path))
    except Exception:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


def write_batch_report(html: str, batch_dir) -> Path:
    path = Path(batch_dir) / "report.html"
    _atomic_write_text(path, html)
    return path
