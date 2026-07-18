"""AES-DATA-001 importer -- self-contained local HTML review report
(mission section 19). No external CSS/JS/fonts/assets. Read-only: it shows
the candidate and prints the exact CLI commands for approval/rejection/
export; it does not itself perform approval.

AES-DATA-002C: when ``candidate.sources`` is non-empty (an aggregate
candidate), the report additionally renders an aggregate summary, a full
per-source breakdown (every supplied source, included or not), and source
chips (``[S1]``, ``[S2]``, ...) on every evidence line so a reader can see
which page supported which fact. A single-source candidate (``sources ==
()``) renders through the EXACT SAME code paths as before this phase, with
every new branch's contribution reducing to the empty string -- byte-
identical output, proven by tests.
"""

from __future__ import annotations

import html
from pathlib import Path
from typing import Dict, Tuple

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer import normalize as N
from scripts.pettripfinder.importer.models import CandidateListing, Conflict, SourceRecord

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

# AES-DATA-002C: appended to ``_CSS`` only for an aggregate report (Task 3/4).
# A single-source report's <style> block stays byte-identical to the
# pre-002C output -- proven by TestReviewReportBackwardCompat.
_AGGREGATE_CSS = (
    ".chip{display:inline-block;background:#e3ebf3;color:#102a4c;border-radius:4px;"
    "padding:0 5px;font-size:12px;font-weight:700;font-family:monospace}"
    ".chip-unknown{background:#f8d7da;color:#7a1420}"
    ".source-row{border:1px solid #e3ebf3;border-radius:8px;padding:10px 12px;margin:8px 0}"
    ".source-included{border-left:4px solid #1e7a3a}"
    ".source-excluded{border-left:4px solid #c2410c}"
    ".source-unusable{border-left:4px solid #b3261e}"
    ".status{font-weight:700;font-size:13px;margin-left:6px}"
)

# AES-DATA-003B: appended to ``_CSS`` only when a candidate carries domain-
# pack capabilities/category-detail (veterinary today). A candidate with
# ``capabilities == ()`` and ``category_detail is None`` (every legacy
# lodging/parks/dining candidate) renders through the exact same code paths
# as before this phase, with the new blocks reducing to "" -- byte-identical
# output, proven by tests.
_CAPABILITY_CSS = (
    ".cap-SUPPORTED{color:#1e7a3a}.cap-EXPLICITLY_ABSENT{color:#6b7280}"
    ".cap-CONFLICTED{color:#b3261e}.cap-UNKNOWN{color:#c2410c}"
    ".highrisk{display:inline-block;background:#fde2e1;color:#7a1420;border-radius:4px;"
    "padding:0 5px;font-size:11px;font-weight:700;margin-left:6px}"
)


def _e(v: str) -> str:
    return html.escape(str(v), quote=True)


def _evidence_for(candidate: CandidateListing, field: str):
    return [ev for ev in candidate.evidence if ev.field_name == field]


# --------------------------------------------------------------------------- #
# Source-chip resolution (AES-DATA-002C Task 4). Matches an evidence row's
# ``source_url`` to a ``SourceRecord`` by exact URL first, then by
# normalized URL (so a trailing-slash or scheme-case difference still
# resolves) -- never fuzzy. A URL that matches nothing renders
# "[UNKNOWN SOURCE]" and is tallied into a visible report warning; it never
# crashes and never silently drops the evidence line.
# --------------------------------------------------------------------------- #

def _source_chip_maps(c: CandidateListing) -> Tuple[Dict[str, str], Dict[str, str]]:
    exact: Dict[str, str] = {}
    norm: Dict[str, str] = {}
    for s in c.sources:
        chip = "[%s]" % s.source_id
        for u in (s.final_url, s.requested_url):
            if not u:
                continue
            exact.setdefault(u, chip)
            key = N.normalize_url(u) or u
            norm.setdefault(key, chip)
    return (exact, norm)


def _resolve_chip(
    source_url: str, exact_map: Dict[str, str], norm_map: Dict[str, str],
) -> Tuple[str, bool]:
    """Returns ``(chip_label, unmapped)``."""
    if source_url in exact_map:
        return (exact_map[source_url], False)
    key = N.normalize_url(source_url) or source_url
    if key in norm_map:
        return (norm_map[key], False)
    return ("[UNKNOWN SOURCE]", True)


# --------------------------------------------------------------------------- #
# Conflict-type labeling (Task 5): a deterministic mapping from the
# ``precedence_note`` each conflict-building call site already sets --
# never inferred, never fuzzy.
# --------------------------------------------------------------------------- #

_CONFLICT_TYPE_LABELS = {
    "aggregate_geography_conflict": C.REASON_GEOGRAPHY_CONFLICT,
    "aggregate_policy_conflict": C.REASON_POLICY_CONFLICT,
    "entity_name_canonicalization": C.REASON_IDENTITY_CONFLICT,
    "phone_role_precedence": "phone_role_conflict",
    "structured_metadata_over_llm_text": C.REASON_CONFLICTING_EVIDENCE,
}


def _conflict_type(cf: Conflict) -> str:
    return _CONFLICT_TYPE_LABELS.get(cf.precedence_note, cf.precedence_note or C.REASON_CONFLICTING_EVIDENCE)


# --------------------------------------------------------------------------- #
# Sources card (Task 3): every supplied source, included or not -- no source
# may silently disappear.
# --------------------------------------------------------------------------- #

def _source_status(s: SourceRecord) -> Tuple[str, str]:
    """Returns ``(css_class, status_label)``."""
    if not s.usable:
        return ("source-unusable", "UNUSABLE: %s" % (s.fetch_reason or "unknown"))
    if s.excluded_reason:
        return ("source-excluded", "EXCLUDED: %s" % s.excluded_reason)
    return ("source-included", "INCLUDED")


def _source_record_html(s: SourceRecord) -> str:
    css_class, status_label = _source_status(s)
    snap = s.snapshot
    observed_at = snap.observed_at if snap else ""
    raw_hash = snap.raw_content_hash if snap else ""
    text_hash = snap.normalized_text_hash if snap else ""
    warnings_html = ("<div class=\"muted\">warnings: %s</div>" % _e(", ".join(s.warnings))
                     if s.warnings else "")
    # AES-DATA-003F (Task 5): "" for every legacy candidate and every
    # excluded/unusable source -- omitted entirely, so a legacy report's
    # markup is byte-identical to before this phase.
    applicability_html = (
        '<div class="muted">applicability: %s</div>' % _e(s.applicability)
        if s.applicability else "")
    return (
        '<div class="source-row %s">'
        '<div><span class="fname">[%s]</span> <span class="muted">%s</span>'
        '<span class="status">%s</span></div>'
        '<div class="muted">requested: %s</div>'
        '<div class="muted">final: %s</div>'
        '<div class="muted">relationship: %s (%s)</div>'
        '<div class="muted">observed_at: %s</div>'
        '<div class="muted">provider: %s &middot; model: %s &middot; prompt: %s</div>'
        '<div class="muted">raw hash: %s</div>'
        '<div class="muted">text hash: %s</div>'
        '%s'
        '%s'
        '</div>'
    ) % (
        css_class, _e(s.source_id), _e(s.role), _e(status_label),
        _e(s.requested_url), _e(s.final_url),
        _e(s.source_relationship), _e(s.source_relationship_reason),
        _e(observed_at), _e(s.extraction_provider), _e(s.extraction_model),
        _e(s.prompt_version), _e(raw_hash), _e(text_hash),
        applicability_html, warnings_html,
    )


def _sources_card_html(c: CandidateListing) -> str:
    rows = "".join(_source_record_html(s) for s in c.sources)
    return '<div class="card"><h3>Sources</h3>%s</div>' % rows


# --------------------------------------------------------------------------- #
# Aggregate summary (Task 6). Only data already persisted on CandidateListing
# / SourceRecord -- no new fields, no inferred operator context.
# --------------------------------------------------------------------------- #

def _aggregate_summary_html(c: CandidateListing) -> str:
    proposed = dict(c.proposed_fields)
    total = len(c.sources)
    included = sum(1 for s in c.sources if s.usable and not s.excluded_reason)
    excluded = sum(1 for s in c.sources if s.usable and s.excluded_reason)
    unusable = sum(1 for s in c.sources if not s.usable)
    reasons = ", ".join(c.recommendation_reasons) or "none"
    return (
        '<div class="card"><h3>Aggregate summary</h3>'
        '<div class="muted">candidate name: %s</div>'
        '<div class="muted">category: %s</div>'
        '<div class="muted">expected city / state: %s / %s</div>'
        '<div class="muted">sources supplied: %d &middot; included: %d &middot; '
        'excluded: %d &middot; unusable: %d</div>'
        '<div class="muted">aggregation version: %s</div>'
        '<div class="muted">recommendation: <span class="rec %s">%s</span> '
        '&middot; reasons: %s</div>'
        '</div>'
    ) % (
        _e(c.context.candidate_name or proposed.get("name", "")),
        _e(c.context.category or proposed.get("category", "")),
        _e(c.context.expected_city), _e(c.context.expected_state),
        total, included, excluded, unusable, _e(c.aggregation_version),
        _e(c.recommendation), _e(c.recommendation), _e(reasons),
    )


# --------------------------------------------------------------------------- #
# Aggregate conflicts table (Task 5): field / competing value / source chip
# / evidence quote / extraction method / conflict type / resolution status.
# The existing simple single-source table is untouched.
# --------------------------------------------------------------------------- #

def _aggregate_conflicts_html(c: CandidateListing, chip_html) -> str:
    ctype_rows = []
    for cf in c.conflicts:
        ctype = _conflict_type(cf)
        for val in cf.competing_values:
            matching_evs = [e for e in cf.evidence if e.proposed_value == val]
            if not matching_evs:
                ctype_rows.append(
                    "<tr><td>%s</td><td>%s</td><td colspan=\"4\" class=\"muted\">"
                    "(no matching evidence row)</td><td>%s</td></tr>" % (
                        _e(cf.field_name), _e(val), _e(cf.resolution_status)))
                continue
            for e in matching_evs:
                ctype_rows.append(
                    "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td>"
                    "<td>%s</td><td>%s</td><td>%s</td></tr>" % (
                        _e(cf.field_name), _e(val), chip_html(e.source_url),
                        _e(e.snapshot_quote), _e(e.extraction_method),
                        _e(ctype), _e(cf.resolution_status)))
    return (
        '<div class="card"><h3>Conflicts</h3><table><tr><th>Field</th>'
        '<th>Competing value</th><th>Source</th><th>Evidence quote</th>'
        '<th>Method</th><th>Conflict type</th><th>Status</th></tr>%s</table></div>'
        % "".join(ctype_rows)
    ) if c.conflicts else ""


# --------------------------------------------------------------------------- #
# AES-DATA-003B: domain-pack capability / category-detail rendering
# (Task 14). Read-only display of data already validated upstream
# (candidate.py/aggregate.py's capability projection) -- this module infers
# nothing and never establishes a fact; it only shows the state, value,
# high-risk marker, source, and evidence quote already attached to each
# ``Capability``. Empty for every candidate with no capabilities/detail
# (every legacy category, and any veterinary candidate with none evidenced).
# --------------------------------------------------------------------------- #

def _capability_evidence_quote(c: CandidateListing, evidence_index: int) -> Tuple[str, str]:
    """Returns ``(quote, method)`` for the evidence entry a capability points
    at, or ``("", "")`` if the index is out of range (defensive only -- the
    projection layer guarantees a valid index for every non-UNKNOWN state)."""
    if 0 <= evidence_index < len(c.evidence):
        ev = c.evidence[evidence_index]
        return (ev.snapshot_quote, ev.extraction_method)
    return ("", "")


def _capabilities_card_html(c: CandidateListing, chip_html) -> str:
    if not c.capabilities:
        return ""
    rows = []
    for cap in c.capabilities:
        quote, method = _capability_evidence_quote(c, cap.evidence_index)
        risk_html = '<span class="highrisk">HIGH-RISK</span>' if cap.high_risk else ""
        quote_html = (
            '<div class="ev">%s%s <span class="muted">(%s)</span></div>' % (
                chip_html(cap.source_url), _e(quote), _e(method))
            if quote else ""
        )
        rows.append(
            "<tr><td>%s</td><td class=\"cap-%s\">%s</td><td>%s</td><td>%s%s</td></tr>" % (
                _e(cap.capability_id), _e(cap.state), _e(cap.state),
                _e(cap.value) or '<span class="muted">(n/a)</span>',
                risk_html, quote_html))
    return (
        '<div class="card"><h3>Capabilities</h3><table><tr><th>Capability</th>'
        '<th>State</th><th>Value</th><th>Evidence</th></tr>%s</table></div>'
        % "".join(rows)
    )


def _category_detail_card_html(c: CandidateListing) -> str:
    if c.category_detail is None or not c.category_detail.fields:
        return ""
    rows = "".join(
        "<tr><td>%s</td><td>%s</td></tr>" % (_e(k), _e(v))
        for k, v in c.category_detail.fields)
    return (
        '<div class="card"><h3>Category detail (%s)</h3><table>'
        '<tr><th>Field</th><th>Value</th></tr>%s</table></div>'
        % (_e(c.category_detail.detail_type), rows)
    )


def _pack_provenance_html(c: CandidateListing) -> str:
    if not c.pack_id:
        return ""
    return (
        '<div class="muted">domain pack: %s v%s &middot; capability schema: %s</div>'
        % (_e(c.pack_id), _e(c.pack_version), _e(c.capability_schema_version))
    )


def render_report_html(candidate: CandidateListing, candidate_json_path: str = "") -> str:
    c = candidate
    proposed = dict(c.proposed_fields)
    rec = _e(c.recommendation)
    is_aggregate = bool(c.sources)

    exact_map, norm_map = _source_chip_maps(c) if is_aggregate else ({}, {})
    unmapped_count = [0]

    def _chip_html(source_url: str) -> str:
        if not is_aggregate or not source_url:
            return ""
        label, unmapped = _resolve_chip(source_url, exact_map, norm_map)
        if unmapped:
            unmapped_count[0] += 1
        css = "chip chip-unknown" if unmapped else "chip"
        return '<span class="%s">%s</span> ' % (css, _e(label))

    rows = []
    for col in C.SEED_CSV_COLUMNS:
        val = proposed.get(col, "")
        ev_html = ""
        for ev in _evidence_for(c, col):
            ev_html += (
                '<div class="ev"><span class="state-%s">[%s]</span> '
                '%s%s <span class="muted">(%s)</span></div>' % (
                    _e(ev.support_state), _e(ev.support_state), _chip_html(ev.source_url),
                    _e(ev.snapshot_quote), _e(ev.extraction_method)))
        marker = ' <span class="warn">(missing)</span>' if (
            col in c.missing_required) else ""
        rows.append(
            '<div class="field"><span class="fname">%s</span>: '
            '<span class="fval">%s</span>%s%s</div>' % (
                _e(col), _e(val) or '<span class="muted">(empty)</span>', marker, ev_html))

    def _pet_quote(field: str) -> str:
        supported = [ev for ev in _evidence_for(c, field) if ev.support_state != "UNSUPPORTED"]
        if not is_aggregate:
            if not supported:
                return ""
            ev = supported[0]
            return '<div class="ev">%s <span class="muted">(%s)</span></div>' % (
                _e(ev.snapshot_quote), _e(ev.extraction_method))
        # Aggregate: every corroborating source's evidence, each chipped.
        out = ""
        for ev in supported:
            out += '<div class="ev">%s%s <span class="muted">(%s)</span></div>' % (
                _chip_html(ev.source_url), _e(ev.snapshot_quote), _e(ev.extraction_method))
        return out

    pet_rows = "".join(
        "<tr><td>%s</td><td>%s%s</td></tr>" % (_e(k), _e(v), _pet_quote(k))
        for k, v in c.pet_facts) or \
        '<tr><td colspan="2" class="muted">none</td></tr>'

    if is_aggregate:
        conflicts_block = _aggregate_conflicts_html(c, _chip_html)
    else:
        conflicts_html = ""
        for cf in c.conflicts:
            conflicts_html += "<tr><td>%s</td><td>%s</td></tr>" % (
                _e(cf.field_name), _e(" vs ".join(cf.competing_values)))
        conflicts_block = (
            '<div class="card"><h3>Conflicts</h3><table><tr><th>Field</th>'
            '<th>Competing values</th></tr>%s</table></div>' % conflicts_html
        ) if c.conflicts else ""

    warnings = list(c.warnings)
    if is_aggregate and unmapped_count[0]:
        warnings.append(
            "%d evidence row(s) could not be matched to a known source "
            "(shown as [UNKNOWN SOURCE])" % unmapped_count[0])
    warnings_html = "".join("<li>%s</li>" % _e(w) for w in warnings) or \
        '<li class="muted">none</li>'
    reasons_html = "".join("<li>%s</li>" % _e(r) for r in c.recommendation_reasons) or \
        '<li class="muted">none</li>'

    aggregate_summary_block = _aggregate_summary_html(c) if is_aggregate else ""
    sources_block = _sources_card_html(c) if is_aggregate else ""
    has_pack_data = bool(c.capabilities or c.category_detail)
    capabilities_block = _capabilities_card_html(c, _chip_html)
    category_detail_block = _category_detail_card_html(c)
    pack_provenance_html = _pack_provenance_html(c)

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
        "%s"
        "<div class=\"card\"><h3>Source</h3>"
        "<div class=\"muted\">requested: %s</div>"
        "<div class=\"muted\">final: %s</div>"
        "<div class=\"muted\">relationship: %s (%s)</div>"
        "<div class=\"muted\">http: %s &middot; content-type: %s</div>"
        "<div class=\"muted\">category: %s &middot; geography confidence: %s</div>"
        "<div class=\"muted\">provider: %s &middot; model: %s &middot; prompt: %s</div>"
        "<div class=\"muted\">raw hash: %s</div>"
        "<div class=\"muted\">text hash: %s</div>"
        "<div class=\"muted\">candidate json: %s</div>%s</div>"
        "%s"
        "<div class=\"card\"><h3>Proposed listing fields</h3>%s</div>"
        "<div class=\"card\"><h3>Structured pet facts</h3><table>"
        "<tr><th>Fact</th><th>Value</th></tr>%s</table></div>"
        "%s"
        "%s"
        "%s"
        "<div class=\"card\"><h3>Recommendation reasons</h3><ul>%s</ul></div>"
        "<div class=\"card\"><h3>Warnings</h3><ul>%s</ul></div>"
        "<div class=\"card\"><h3>Next commands</h3>"
        "<p class=\"muted\">This report is read-only. Approve or reject from the CLI:</p>"
        "<pre>%s\n%s</pre></div>"
        "</main></body></html>"
    ) % (
        _e(c.candidate_id),
        _CSS + (_AGGREGATE_CSS if is_aggregate else "") + (_CAPABILITY_CSS if has_pack_data else ""),
        _e(proposed.get("name") or c.candidate_id),
        rec, rec, _e(c.review_status),
        aggregate_summary_block,
        _e(c.snapshot.requested_url), _e(c.snapshot.final_url),
        _e(c.source_relationship), _e(c.source_relationship_reason),
        _e(c.snapshot.http_status), _e(c.snapshot.content_type),
        _e(proposed.get("category")), _e(c.geography_confidence),
        _e(c.extraction_provider), _e(c.extraction_model), _e(c.prompt_version),
        _e(c.snapshot.raw_content_hash), _e(c.snapshot.normalized_text_hash),
        json_path, pack_provenance_html, sources_block, "".join(rows), pet_rows,
        capabilities_block, category_detail_block, conflicts_block, reasons_html,
        warnings_html, _e(approve_cmd), _e(reject_cmd),
    )


def write_report(candidate: CandidateListing, reports_dir, candidate_json_path: str = "") -> Path:
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / ("%s.html" % candidate.candidate_id)
    path.write_text(render_report_html(candidate, candidate_json_path),
                    encoding="utf-8", newline="\n")
    return path
