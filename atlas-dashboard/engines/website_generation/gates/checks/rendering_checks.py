"""CG-RND — Rendering gates (AES-WEB-002 §21.3).

Ten gates checking emitted-markup properties: determinism, HTML validity,
escaping, attribute/class stability, inline script/style prohibition,
no-JS baselines, external-request prohibition, DOM id uniqueness,
URL safety, and structured-data well-formedness.

Every gate in this family fundamentally requires real rendered output —
AES-WEB-002 §21 preamble lists "rendered output" as an input, and §29.1
assumed a pre-existing ``rendering/`` package this repository does not
have (AMB-002I-01, operator-approved: declarative/fixture-only scope).
These checks therefore run only against
:class:`~engines.website_generation.gates.checks.SyntheticRenderedPage` —
a hand-authored, in-code stand-in for what a real Renderer + HTML/CSS
analysis pass would report. A passing result here proves the check
*logic* is correct on its fixture pair; it proves nothing about any real
emitted HTML, because no real HTML exists yet. Real Renderer integration
remains deferred to a future delivery.

Remediation owner: RN = renderer/emitter (all ten); CE = Component Engine
for CG-RND-010 (structured-data fragment authorship).
"""

from __future__ import annotations

from engines.website_generation.gates.checks import CheckOutcome, SyntheticRenderedPage


def _page_ref(page: SyntheticRenderedPage) -> str:
    return f"route={page.route!r}"


def check_cg_rnd_001(page: SyntheticRenderedPage) -> CheckOutcome:
    """CG-RND-001: deterministic output — double-render hash equality."""
    if page.render_hash_a == page.render_hash_b:
        return CheckOutcome(True, f"{_page_ref(page)}: double-render hashes match")
    return CheckOutcome(
        False,
        f"{_page_ref(page)}: double-render hash mismatch "
        f"({page.render_hash_a!r} != {page.render_hash_b!r})",
    )


def check_cg_rnd_002(page: SyntheticRenderedPage) -> CheckOutcome:
    """CG-RND-002: valid HTML (deterministic conformance checker)."""
    if page.html_conformant and not page.conformance_errors:
        return CheckOutcome(True, f"{_page_ref(page)}: HTML conformant")
    return CheckOutcome(
        False,
        f"{_page_ref(page)}: HTML conformance errors {page.conformance_errors!r}",
    )


def check_cg_rnd_003(page: SyntheticRenderedPage) -> CheckOutcome:
    """CG-RND-003: all interpolated content escaped (marker-probe fixtures)."""
    if not page.escaped_probe_leaks:
        return CheckOutcome(True, f"{_page_ref(page)}: no unescaped probe leaks")
    return CheckOutcome(
        False, f"{_page_ref(page)}: unescaped content leaked {page.escaped_probe_leaks!r}"
    )


def check_cg_rnd_004(page: SyntheticRenderedPage) -> CheckOutcome:
    """CG-RND-004: stable attribute order + stable class names across builds."""
    if page.attribute_order_stable and page.class_names_stable:
        return CheckOutcome(True, f"{_page_ref(page)}: attribute order and classes stable")
    problems = []
    if not page.attribute_order_stable:
        problems.append("attribute order unstable")
    if not page.class_names_stable:
        problems.append("class names unstable")
    return CheckOutcome(False, f"{_page_ref(page)}: {'; '.join(problems)}")


def check_cg_rnd_005(page: SyntheticRenderedPage) -> CheckOutcome:
    """CG-RND-005: zero inline scripts; zero unapproved inline styles."""
    if page.inline_script_count == 0 and page.unapproved_inline_style_count == 0:
        return CheckOutcome(True, f"{_page_ref(page)}: no inline scripts or unapproved styles")
    return CheckOutcome(
        False,
        f"{_page_ref(page)}: {page.inline_script_count} inline script(s), "
        f"{page.unapproved_inline_style_count} unapproved inline style(s)",
    )


def check_cg_rnd_006(page: SyntheticRenderedPage) -> CheckOutcome:
    """CG-RND-006: no-JS baseline paths present for every interactive
    contract."""
    if page.no_js_baseline_present:
        return CheckOutcome(True, f"{_page_ref(page)}: no-JS baseline present")
    return CheckOutcome(
        False, f"{_page_ref(page)}: no-JS baseline missing for an interactive contract"
    )


def check_cg_rnd_007(page: SyntheticRenderedPage) -> CheckOutcome:
    """CG-RND-007: zero external requests in bundle (MVP); asset refs
    resolve."""
    if page.external_request_hosts:
        return CheckOutcome(
            False, f"{_page_ref(page)}: external request host(s) {page.external_request_hosts!r}"
        )
    if page.unresolved_asset_refs:
        return CheckOutcome(
            False, f"{_page_ref(page)}: unresolved asset ref(s) {page.unresolved_asset_refs!r}"
        )
    return CheckOutcome(True, f"{_page_ref(page)}: zero external requests, all assets resolve")


def check_cg_rnd_008(page: SyntheticRenderedPage) -> CheckOutcome:
    """CG-RND-008: no duplicate DOM ids; no internal-metadata markers in
    output."""
    seen = set()
    duplicates = set()
    for dom_id in page.dom_ids:
        if dom_id in seen:
            duplicates.add(dom_id)
        seen.add(dom_id)
    if duplicates:
        return CheckOutcome(False, f"{_page_ref(page)}: duplicate DOM id(s) {sorted(duplicates)!r}")
    if page.internal_metadata_markers:
        return CheckOutcome(
            False,
            f"{_page_ref(page)}: internal metadata marker(s) leaked "
            f"{page.internal_metadata_markers!r}",
        )
    return CheckOutcome(True, f"{_page_ref(page)}: DOM ids unique, no internal markers")


def check_cg_rnd_009(page: SyntheticRenderedPage) -> CheckOutcome:
    """CG-RND-009: no unsafe URLs (scheme whitelist) anywhere in emitted
    markup."""
    if not page.unsafe_urls:
        return CheckOutcome(True, f"{_page_ref(page)}: no unsafe URLs")
    return CheckOutcome(False, f"{_page_ref(page)}: unsafe URL(s) {page.unsafe_urls!r}")


def check_cg_rnd_010(page: SyntheticRenderedPage) -> CheckOutcome:
    """CG-RND-010: structured-data fragments well-formed pre-compilation."""
    if page.structured_data_fragments_well_formed:
        return CheckOutcome(True, f"{_page_ref(page)}: structured-data fragments well-formed")
    return CheckOutcome(False, f"{_page_ref(page)}: malformed structured-data fragment(s)")


CHECKS = {
    "CG-RND-001": check_cg_rnd_001,
    "CG-RND-002": check_cg_rnd_002,
    "CG-RND-003": check_cg_rnd_003,
    "CG-RND-004": check_cg_rnd_004,
    "CG-RND-005": check_cg_rnd_005,
    "CG-RND-006": check_cg_rnd_006,
    "CG-RND-007": check_cg_rnd_007,
    "CG-RND-008": check_cg_rnd_008,
    "CG-RND-009": check_cg_rnd_009,
    "CG-RND-010": check_cg_rnd_010,
}
