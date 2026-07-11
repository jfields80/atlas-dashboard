"""Quality gate identifiers and severities (AES-WEB-001 §10.1-§10.2).

The executable gate registry (ordered gate list with check callables)
arrives in Phase 3. Phase 1 pins gate family identifiers and severity
names only, as plain strings (stdlib-only package rule §3.2).

Accessibility gate severities (AES-WEB-001 v1.1.0 amendment A2)
--------------------------------------------------------------
Amendment A2 (AES-WEB-002 §12.7 severity map, §21.4 accessibility gate
family, registered under the AES-WEB-001 §3.5 mechanism) strengthens the
AES-WEB-001 §10.2 accessibility row: defects affecting alt text, contrast,
labels, keyboard/focus, semantic structure, heading hierarchy, landmarks,
and form-completion accessibility are BLOCKING (there is no "conversion
exception" to accessibility — AES-WEB-002 E7). Only optimization-tier
findings remain WARNING. This module pins the authorized severity policy
as constants; the executable gate catalog itself is AES-WEB-002I and is
NOT implemented here.
"""

GATE_SEVERITY_BLOCKING = "BLOCKING"
GATE_SEVERITY_WARNING = "WARNING"
GATE_SEVERITY_INFO = "INFO"

GATE_FAMILY_STRUCTURAL = "structural"
GATE_FAMILY_CONTENT = "content"
GATE_FAMILY_SEO = "seo"
GATE_FAMILY_ACCESSIBILITY = "accessibility"
GATE_FAMILY_INTEGRITY = "integrity"

GATE_FAMILIES = (
    GATE_FAMILY_STRUCTURAL,
    GATE_FAMILY_CONTENT,
    GATE_FAMILY_SEO,
    GATE_FAMILY_ACCESSIBILITY,
    GATE_FAMILY_INTEGRITY,
)

# ---------------------------------------------------------------------------
# Accessibility gate severity policy (amendment A2; AES-WEB-002 §12.7/§21.4)
# ---------------------------------------------------------------------------

# BLOCKING accessibility defect categories. Certification is impossible while
# any of these is present (AES-WEB-002 §12.7 BLOCKING clause, §21.4 gate
# family). These elevate the AES-WEB-001 §10.2 accessibility row.
ACCESSIBILITY_DEFECT_MISSING_ALT_TEXT = "missing_or_invalid_alt_text"
ACCESSIBILITY_DEFECT_CONTRAST = "contrast_failure"
ACCESSIBILITY_DEFECT_MISSING_LABELS = "missing_labels"
ACCESSIBILITY_DEFECT_KEYBOARD_FOCUS = "keyboard_focus_failure"
ACCESSIBILITY_DEFECT_SEMANTIC_STRUCTURE = "semantic_structure_failure"
ACCESSIBILITY_DEFECT_HEADING_HIERARCHY = "heading_hierarchy_defect"
ACCESSIBILITY_DEFECT_LANDMARK = "landmark_defect"
ACCESSIBILITY_DEFECT_FORM_COMPLETION = "form_completion_accessibility_failure"

ACCESSIBILITY_BLOCKING_DEFECTS = (
    ACCESSIBILITY_DEFECT_MISSING_ALT_TEXT,
    ACCESSIBILITY_DEFECT_CONTRAST,
    ACCESSIBILITY_DEFECT_MISSING_LABELS,
    ACCESSIBILITY_DEFECT_KEYBOARD_FOCUS,
    ACCESSIBILITY_DEFECT_SEMANTIC_STRUCTURE,
    ACCESSIBILITY_DEFECT_HEADING_HIERARCHY,
    ACCESSIBILITY_DEFECT_LANDMARK,
    ACCESSIBILITY_DEFECT_FORM_COMPLETION,
)

# Optimization-tier accessibility findings remain WARNING (AES-WEB-002 §12.7
# WARNING clause: suboptimal reading order, missing autocomplete, verbose
# alt text beyond the length ceiling, redundant link text).
ACCESSIBILITY_WARNING_DEFECTS = (
    "suboptimal_reading_order",
    "missing_autocomplete",
    "verbose_alt_text",
    "redundant_link_text",
)

# Severity registration for the accessibility gate family (AES-WEB-001 §3.5
# registration mechanism: an explicit, deterministic list in constants — no
# dynamic scanning). Maps each defect category to its severity name.
ACCESSIBILITY_GATE_SEVERITIES = {
    **{d: GATE_SEVERITY_BLOCKING for d in ACCESSIBILITY_BLOCKING_DEFECTS},
    **{d: GATE_SEVERITY_WARNING for d in ACCESSIBILITY_WARNING_DEFECTS},
}
