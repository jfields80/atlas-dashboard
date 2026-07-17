"""AES-DATA-001 importer -- self-contained local HTML review report
(mission section 19). No external CSS/JS/fonts/assets. Read-only: it shows
the candidate and prints the exact CLI commands for approval/rejection/
export; it does not itself perform approval.
"""

from __future__ import annotations

import html
from pathlib import Path

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.models import CandidateListing

_CSS = (
    "body{font:16px/1.5 -apple-system,Segoe UI,Roboto,Arial,sans-serif;"
    "margin:0;background:#f3f8fd;color:#102a4c}"
    "main{max-width:900px;margin:0 auto;padding:24px}"
    "h1{font-size:26px;margin:0 0 4px}"
    ".rec{display:inline-block;padding:4px 12px;border-radius:999px;font-weight:700;color:#fff}"
    ".READY{background:#1e7a3a}.REVIEW{background:#c2410c}.REJECT{background:#b3261e}"
    ".card{background:#fff;border:1px solid #d9e2ec;border-radius:10px;padding:16px;margin:16px 0}"
    ".field{border-bottom:1px solid #eef2f7;padding:8px 0}"
    ".field:last-child{border-bottom:0}"
    ".fname{font-weight:700}.fval{color:#102a4c}"
    ".ev{color:#42566b;font-size:14px;margin:4px 0 0;padding-left:12px;border-left:3px solid #d9e2ec}"
    ".state-SUPPORTED{color:#1e7a3a}.state-AMBIGUOUS{color:#c2410c}.state-UNSUPPORTED{color:#b3261e}"
    ".muted{color:#42566b;font-size:14px}"
    "code,pre{background:#0f2a4c;color:#e8f2fe;border-radius:6px;padding:2px 6px;font-size:13px}"
    "pre{padding:12px;overflow-x:auto;white-space:pre-wrap}"
    "table{border-collapse:collapse;width:100%}td,th{border:1px solid #e3ebf3;padding:6px 8px;"
    "text-align:left;font-size:14px;vertical-align:top}"
    ".warn{color:#b3261e}"
)


def _e(v: str) -> str:
    return html.escape(str(v), quote=True)


def _evidence_for(candidate: CandidateListing, field: str):
    return [ev for ev in candidate.evidence if ev.field_name == field]


def render_report_html(candidate: CandidateListing, candidate_json_path: str = "") -> str:
    c = candidate
    proposed = dict(c.proposed_fields)
    rec = _e(c.recommendation)

    rows = []
    for col in C.SEED_CSV_COLUMNS:
        val = proposed.get(col, "")
        ev_html = ""
        for ev in _evidence_for(c, col):
            ev_html += (
                '<div class="ev"><span class="state-%s">[%s]</span> '
                '%s <span class="muted">(%s)</span></div>' % (
                    _e(ev.support_state), _e(ev.support_state),
                    _e(ev.snapshot_quote), _e(ev.extraction_method)))
        marker = ' <span class="warn">(missing)</span>' if (
            col in c.missing_required) else ""
        rows.append(
            '<div class="field"><span class="fname">%s</span>: '
            '<span class="fval">%s</span>%s%s</div>' % (
                _e(col), _e(val) or '<span class="muted">(empty)</span>', marker, ev_html))

    def _pet_quote(field: str) -> str:
        for ev in _evidence_for(c, field):
            if ev.support_state != "UNSUPPORTED":
                return '<div class="ev">%s <span class="muted">(%s)</span></div>' % (
                    _e(ev.snapshot_quote), _e(ev.extraction_method))
        return ""

    pet_rows = "".join(
        "<tr><td>%s</td><td>%s%s</td></tr>" % (_e(k), _e(v), _pet_quote(k))
        for k, v in c.pet_facts) or \
        '<tr><td colspan="2" class="muted">none</td></tr>'

    conflicts_html = ""
    for cf in c.conflicts:
        conflicts_html += "<tr><td>%s</td><td>%s</td></tr>" % (
            _e(cf.field_name), _e(" vs ".join(cf.competing_values)))
    conflicts_block = (
        '<div class="card"><h3>Conflicts</h3><table><tr><th>Field</th>'
        '<th>Competing values</th></tr>%s</table></div>' % conflicts_html
    ) if c.conflicts else ""

    warnings_html = "".join("<li>%s</li>" % _e(w) for w in c.warnings) or \
        '<li class="muted">none</li>'
    reasons_html = "".join("<li>%s</li>" % _e(r) for r in c.recommendation_reasons) or \
        '<li class="muted">none</li>'

    json_path = _e(candidate_json_path)
    approve_cmd = "python scripts/approve_import_candidate.py --candidate %s --decision approve" % json_path
    reject_cmd = "python scripts/approve_import_candidate.py --candidate %s --decision reject" % json_path

    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<title>Import candidate %s</title><style>%s</style></head><body><main>"
        "<h1>%s</h1>"
        "<p><span class=\"rec %s\">%s</span> "
        "<span class=\"muted\">review status: %s</span></p>"
        "<div class=\"card\"><h3>Source</h3>"
        "<div class=\"muted\">requested: %s</div>"
        "<div class=\"muted\">final: %s</div>"
        "<div class=\"muted\">relationship: %s (%s)</div>"
        "<div class=\"muted\">http: %s &middot; content-type: %s</div>"
        "<div class=\"muted\">category: %s &middot; geography confidence: %s</div>"
        "<div class=\"muted\">provider: %s &middot; model: %s &middot; prompt: %s</div>"
        "<div class=\"muted\">raw hash: %s</div>"
        "<div class=\"muted\">text hash: %s</div>"
        "<div class=\"muted\">candidate json: %s</div></div>"
        "<div class=\"card\"><h3>Proposed listing fields</h3>%s</div>"
        "<div class=\"card\"><h3>Structured pet facts</h3><table>"
        "<tr><th>Fact</th><th>Value</th></tr>%s</table></div>"
        "%s"
        "<div class=\"card\"><h3>Recommendation reasons</h3><ul>%s</ul></div>"
        "<div class=\"card\"><h3>Warnings</h3><ul>%s</ul></div>"
        "<div class=\"card\"><h3>Next commands</h3>"
        "<p class=\"muted\">This report is read-only. Approve or reject from the CLI:</p>"
        "<pre>%s\n%s</pre></div>"
        "</main></body></html>"
    ) % (
        _e(c.candidate_id), _CSS, _e(proposed.get("name") or c.candidate_id),
        rec, rec, _e(c.review_status),
        _e(c.snapshot.requested_url), _e(c.snapshot.final_url),
        _e(c.source_relationship), _e(c.source_relationship_reason),
        _e(c.snapshot.http_status), _e(c.snapshot.content_type),
        _e(proposed.get("category")), _e(c.geography_confidence),
        _e(c.extraction_provider), _e(c.extraction_model), _e(c.prompt_version),
        _e(c.snapshot.raw_content_hash), _e(c.snapshot.normalized_text_hash),
        json_path, "".join(rows), pet_rows, conflicts_block, reasons_html,
        warnings_html, _e(approve_cmd), _e(reject_cmd),
    )


def write_report(candidate: CandidateListing, reports_dir, candidate_json_path: str = "") -> Path:
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / ("%s.html" % candidate.candidate_id)
    path.write_text(render_report_html(candidate, candidate_json_path),
                    encoding="utf-8", newline="\n")
    return path
