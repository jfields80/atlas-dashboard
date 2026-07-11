"""Quality gate identifiers and severities (AES-WEB-001 §10.1-§10.2).

The executable gate registry (ordered gate list with check callables)
arrives in Phase 3. Phase 1 pins gate family identifiers and severity
names only, as plain strings (stdlib-only package rule §3.2).
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
