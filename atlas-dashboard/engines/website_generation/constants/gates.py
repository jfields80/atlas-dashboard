"""Quality gate identifiers and severities (AES-WEB-001 §10.1-§10.2).

Phase 1 pinned gate family identifiers and severity names only, as plain
strings (stdlib-only package rule §3.2). AES-WEB-002I (this module's
current delivery) adds the full AES-WEB-002 §21 component gate catalog as
registration *data*: gate IDs, families, severities, remediation owners,
and pass-condition descriptions. It does NOT add an executable Quality
Gate Engine — see "Scope and deferral" below.

Accessibility gate severities (AES-WEB-001 v1.1.0 amendment A2)
--------------------------------------------------------------
Amendment A2 (AES-WEB-002 §12.7 severity map, §21.4 accessibility gate
family, registered under the AES-WEB-001 §3.5 mechanism) strengthens the
AES-WEB-001 §10.2 accessibility row: defects affecting alt text, contrast,
labels, keyboard/focus, semantic structure, heading hierarchy, landmarks,
and form-completion accessibility are BLOCKING (there is no "conversion
exception" to accessibility — AES-WEB-002 E7). Only optimization-tier
findings remain WARNING. This module pins the authorized severity policy
as constants.

AES-WEB-002I — component gate catalog registration
----------------------------------------------------
Scope and deferral (AES-WEB-002I Architectural Preflight, Ambiguity
Register, operator-approved decisions):

* AMB-002I-01 — declarative and fixture-only. ``COMPONENT_GATE_REGISTRATIONS``
  below is pure data (gate identity, severity, ownership, description). The
  pure, individually testable check *functions* that give each executable
  gate real logic live in ``engines/website_generation/gates/checks/``,
  operating on hand-authored synthetic fixture data (see that package's
  docstrings). No Quality Gate Engine, no ``GateCheck`` interface, and no
  ``rendering/`` package are built by this delivery — those remain
  deferred to a future sprint. The AES-WEB-002 §31 acceptance phrase
  "Quality Gate Engine runs the extended list deterministically" is
  explicitly NOT satisfied by this delivery.
* AMB-002I-02 — 73, not 63. AES-WEB-002 §21's closing line and §34.1 state
  "63 component gates"; the seven per-family tables in §21.1-§21.7
  enumerate 10+11+10+13+9+12+8 = 73 distinct gate IDs. This discrepancy is
  pre-existing (recorded as D1 in the non-authoritative Architecture
  Index, docs/Atlas Website Generation Architecture Index.md §13.4). Per
  operator decision, the 73 individually enumerated gate IDs are
  authoritative over the inconsistent "63" prose summary, and all 73 are
  registered below. No new ADR is authored for this decision this sprint
  (operator instruction); the decision is recorded here, in the
  AES-WEB-002I test suite, and in the delivery commit message instead.
* AMB-002I-03 — fixtures are in-code, not file-based. AES-WEB-002 §31's
  002I entry frames this phase as "integration, not greenfield" of
  fixtures accumulated in Waves 1-7. In fact, only fixture ID *strings*
  (``ComponentDefinition.example_fixture_ids``) accumulated in those
  waves — no fixture *data* exists anywhere in the repository
  (``tests/website_generation/fixtures/`` holds only an ``__init__.py``).
  Per operator decision, this delivery authors good/bad fixture data as
  frozen, deterministic, in-code synthetic Python objects colocated with
  the new gate tests (``tests/website_generation/gates/``), and does not
  create or migrate to a physical fixture-file system.
* AMB-002I-04 — CG-STR-006 is a reservation, not an executable gate.
  AES-WEB-002 references ``CG-STR-006`` (the zero-state rule) prospectively
  as an AES-WEB-001 structural-family gate ID (§6.2, §21.2's CG-CMP-010
  note, §27.4/§27.8), and it is already forward-referenced by a live
  component (``catalog/discovery.py``'s ``status.results.zero``
  ``quality_gate_requirements``). AES-WEB-001 itself defines gate families
  only, never individual W1 gate IDs, and the Architecture Index assigns
  CG-STR-006's actual implementation to a future W1-Phase-3 Quality Gate
  Engine delivery. Per operator decision, CG-STR-006 is registered below
  as a namespace reservation (id, family, severity, remediation owner)
  only — ``executable=False``, no check function, no check module. Do not
  treat its registration as a completed executable check.

Scope note on module coverage — CG-A11Y and CG-SEO are registered, not
executable, this sprint. AES-WEB-002 §21.4/§21.5 name
``accessibility_checks.py`` and ``seo_checks.py`` as the CG-A11Y/CG-SEO
check modules, framed as "extensions" of base AES-WEB-001 files that do
not exist anywhere in this repository. The operator's authorized-new-file
list for this delivery names exactly five check modules
(``component_checks.py``, ``composition_checks.py``, ``rendering_checks.py``,
``commercial_checks.py``, ``responsive_checks.py``) — no sixth or seventh
module. Two independent, pre-existing AES-WEB-002A regression tests
confirm this is not an oversight but a deliberate architectural boundary:
``tests/website_generation/architecture/test_import_audit.py``'s
``_AUTHORIZED_GATE_CHECK_MODULES`` whitelist and
``test_public_surface.py``'s ``A3_AUTHORIZED_PACKAGES["gates"]`` inline
comment both enumerate the identical five modules. Consistent with the
CG-STR-006 pattern (AMB-002I-04) and this discovered boundary, the
thirteen CG-A11Y and nine CG-SEO gates are registered below with full
identity/severity/ownership/description metadata but ``executable=False``
and ``check_module=""`` — no accessibility_checks.py or seo_checks.py is
created, and no CG-A11Y/CG-SEO check function exists this sprint. Their
executable check logic is deferred to whichever future delivery is
authorized to create those two modules.
"""

from typing import Dict, NamedTuple, Tuple

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

# ---------------------------------------------------------------------------
# AES-WEB-002I — Component gate catalog (AES-WEB-002 §21)
# ---------------------------------------------------------------------------

# New gate families introduced by this delivery (AES-WEB-002 §21.1-21.3,
# §21.6-21.7). CG-A11Y and CG-SEO deliberately reuse the existing
# GATE_FAMILY_ACCESSIBILITY / GATE_FAMILY_SEO constants above — §21.4/§21.5
# describe them as *extensions* of those W1 families, not new families.
GATE_FAMILY_CG_CONTRACT = "component_contract"
GATE_FAMILY_CG_COMPOSITION = "composition"
GATE_FAMILY_CG_RENDERING = "rendering_component"
GATE_FAMILY_CG_COMMERCIAL = "commercial"
GATE_FAMILY_CG_RESPONSIVE = "responsive"

COMPONENT_GATE_FAMILIES = (
    GATE_FAMILY_CG_CONTRACT,
    GATE_FAMILY_CG_COMPOSITION,
    GATE_FAMILY_CG_RENDERING,
    GATE_FAMILY_ACCESSIBILITY,
    GATE_FAMILY_SEO,
    GATE_FAMILY_CG_COMMERCIAL,
    GATE_FAMILY_CG_RESPONSIVE,
)

# Remediation owner codes, verbatim from the AES-WEB-002 §21 preamble key:
# "R registry/definition, CE Component Engine binding, CT content,
# RN renderer/emitter, RC recipe/LayoutPlan." Multi-owner gates keep the
# authority's exact "X/Y" notation rather than picking one.
REMEDIATION_OWNER_REGISTRY = "R"
REMEDIATION_OWNER_COMPONENT_ENGINE = "CE"
REMEDIATION_OWNER_CONTENT = "CT"
REMEDIATION_OWNER_RENDERER = "RN"
REMEDIATION_OWNER_RECIPE = "RC"


class GateRegistration(NamedTuple):
    """One registered gate's identity and metadata (AES-WEB-002 §21).

    Pure data — no behavior. ``executable`` is True for the 73 AES-WEB-002
    §21 component gates (each has a real check function in
    ``gates/checks/``, tested two-fixture-law style against synthetic
    fixtures — AMB-002I-01/03) and False only for the CG-STR-006
    reservation (AMB-002I-04). ``check_module`` is the dotted module
    holding the check function, or ``""`` when not executable.
    ``severity`` is the gate's primary/blocking-worthy severity;
    ``severity_note`` preserves any split-severity nuance from §21
    verbatim (e.g. CG-A11Y-012, CG-SEO-004) without inventing a second
    gate ID.
    """

    gate_id: str
    family: str
    severity: str
    severity_note: str
    remediation_owner: str
    description: str
    executable: bool
    check_module: str
    source_section: str


# Explicit, ordered tuple — lexicographic by gate_id, mirroring the
# REGISTERED_COMPONENTS convention (AES-WEB-002 §15.2) so merge conflicts
# stay visible. 73 AES-WEB-002 §21 component gates + 1 CG-STR-006
# reservation (AMB-002I-04) = 74 entries.
COMPONENT_GATE_REGISTRATIONS: Tuple[GateRegistration, ...] = (
    # --- CG-A11Y — Accessibility (§21.4; extends GATE_FAMILY_ACCESSIBILITY) ---
    GateRegistration(
        "CG-A11Y-001", GATE_FAMILY_ACCESSIBILITY, GATE_SEVERITY_BLOCKING, "",
        "CE/RN",
        "Labels: every control programmatically labeled; icon-only controls have A11Y_LABEL",
        False, "", "§21.4",
    ),
    GateRegistration(
        "CG-A11Y-002", GATE_FAMILY_ACCESSIBILITY, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RENDERER,
        "Declared keyboard behavior present (state-machine markup assertions §12.6)",
        False, "", "§21.4",
    ),
    GateRegistration(
        "CG-A11Y-003", GATE_FAMILY_ACCESSIBILITY, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RENDERER,
        "Focus: visible ring token wired; no outline:none without replacement; trap contracts valid",
        False, "", "§21.4",
    ),
    GateRegistration(
        "CG-A11Y-004", GATE_FAMILY_ACCESSIBILITY, GATE_SEVERITY_BLOCKING, "",
        "R/RN",
        "Contrast: every declared text/surface pairing meets AA (Brand-embedded ratios)",
        False, "", "§21.4",
    ),
    GateRegistration(
        "CG-A11Y-005", GATE_FAMILY_ACCESSIBILITY, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RENDERER,
        "Touch targets >= 44px via tokens",
        False, "", "§21.4",
    ),
    GateRegistration(
        "CG-A11Y-006", GATE_FAMILY_ACCESSIBILITY, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RENDERER,
        "Reduced-motion resolution exists for all motion tokens used",
        False, "", "§21.4",
    ),
    GateRegistration(
        "CG-A11Y-007", GATE_FAMILY_ACCESSIBILITY, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RENDERER,
        "Semantic roles correct per semantic_element + state machines",
        False, "", "§21.4",
    ),
    GateRegistration(
        "CG-A11Y-008", GATE_FAMILY_ACCESSIBILITY, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RENDERER,
        "Live-region declarations valid where contracted",
        False, "", "§21.4",
    ),
    GateRegistration(
        "CG-A11Y-009", GATE_FAMILY_ACCESSIBILITY, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RENDERER,
        "Dialog/drawer behavior markup valid (trap, escape, labeling)",
        False, "", "§21.4",
    ),
    GateRegistration(
        "CG-A11Y-010", GATE_FAMILY_ACCESSIBILITY, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_CONTENT,
        'Informative images have non-empty alt; decorative are alt=""',
        False, "", "§21.4",
    ),
    GateRegistration(
        "CG-A11Y-011", GATE_FAMILY_ACCESSIBILITY, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RECIPE,
        "Skip link first-focusable on every page",
        False, "", "§21.4",
    ),
    GateRegistration(
        "CG-A11Y-012", GATE_FAMILY_ACCESSIBILITY, GATE_SEVERITY_BLOCKING,
        "BLOCKING (summary/association) / WARNING (autocomplete) — §21.4 split severity",
        REMEDIATION_OWNER_RENDERER,
        "Form error summary + inline association + autocomplete attrs",
        False, "", "§21.4",
    ),
    GateRegistration(
        "CG-A11Y-013", GATE_FAMILY_ACCESSIBILITY, GATE_SEVERITY_WARNING, "",
        REMEDIATION_OWNER_CONTENT,
        "Alt length <= ceiling; non-redundant link text",
        False, "", "§21.4",
    ),
    # --- CG-CMP — Composition (§21.2) ---
    GateRegistration(
        "CG-CMP-001", GATE_FAMILY_CG_COMPOSITION, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RECIPE,
        "Every instance's parent region in allowed_parent_regions",
        True, "engines.website_generation.gates.checks.composition_checks", "§21.2",
    ),
    GateRegistration(
        "CG-CMP-002", GATE_FAMILY_CG_COMPOSITION, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RECIPE,
        "All children in allowed_child_components, none in forbidden set",
        True, "engines.website_generation.gates.checks.composition_checks", "§21.2",
    ),
    GateRegistration(
        "CG-CMP-003", GATE_FAMILY_CG_COMPOSITION, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RECIPE,
        "Composition depth <= 6",
        True, "engines.website_generation.gates.checks.composition_checks", "§21.2",
    ),
    GateRegistration(
        "CG-CMP-004", GATE_FAMILY_CG_COMPOSITION, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RECIPE,
        "No recursive composition (family within own subtree, layout.*/atom.* exempt)",
        True, "engines.website_generation.gates.checks.composition_checks", "§21.2",
    ),
    GateRegistration(
        "CG-CMP-005", GATE_FAMILY_CG_COMPOSITION, GATE_SEVERITY_BLOCKING, "",
        "RN/RC",
        "Heading hierarchy: exactly one H1, no level skips, ownership per §9.3",
        True, "engines.website_generation.gates.checks.composition_checks", "§21.2",
    ),
    GateRegistration(
        "CG-CMP-006", GATE_FAMILY_CG_COMPOSITION, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RENDERER,
        "Landmark hierarchy: one main/header/footer; multi-nav labeled",
        True, "engines.website_generation.gates.checks.composition_checks", "§21.2",
    ),
    GateRegistration(
        "CG-CMP-007", GATE_FAMILY_CG_COMPOSITION, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RECIPE,
        "CTA hierarchy + repetition within §16.3 policy",
        True, "engines.website_generation.gates.checks.composition_checks", "§21.2",
    ),
    GateRegistration(
        "CG-CMP-008", GATE_FAMILY_CG_COMPOSITION, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RENDERER,
        "No nested interactive controls",
        True, "engines.website_generation.gates.checks.composition_checks", "§21.2",
    ),
    GateRegistration(
        "CG-CMP-009", GATE_FAMILY_CG_COMPOSITION, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RECIPE,
        "<= 2 concurrent sticky regions; no sticky overlap",
        True, "engines.website_generation.gates.checks.composition_checks", "§21.2",
    ),
    GateRegistration(
        "CG-CMP-010", GATE_FAMILY_CG_COMPOSITION, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RECIPE,
        "Required role components present per §6.1 matrix (extends AES-WEB-001 "
        "structural family; registered alongside CG-STR-006 zero-state rule)",
        True, "engines.website_generation.gates.checks.composition_checks", "§21.2",
    ),
    GateRegistration(
        "CG-CMP-011", GATE_FAMILY_CG_COMPOSITION, GATE_SEVERITY_WARNING, "",
        REMEDIATION_OWNER_RECIPE,
        "Section count <= role ceiling",
        True, "engines.website_generation.gates.checks.composition_checks", "§21.2",
    ),
    # --- CG-COM — Commercial (§21.6) ---
    GateRegistration(
        "CG-COM-001", GATE_FAMILY_CG_COMMERCIAL, GATE_SEVERITY_BLOCKING, "",
        "RN/CE",
        "Every SPONSORED/FEATURED render carries visible + semantic disclosure (E5)",
        True, "engines.website_generation.gates.checks.commercial_checks", "§21.6",
    ),
    GateRegistration(
        "CG-COM-002", GATE_FAMILY_CG_COMMERCIAL, GATE_SEVERITY_BLOCKING, "",
        "CT/RC",
        "Ranked lists bind rationale/methodology; sponsored never presented as rank (E6)",
        True, "engines.website_generation.gates.checks.commercial_checks", "§21.6",
    ),
    GateRegistration(
        "CG-COM-003", GATE_FAMILY_CG_COMMERCIAL, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_CONTENT,
        "Every review/testimonial block carries evidence_ref (E2)",
        True, "engines.website_generation.gates.checks.commercial_checks", "§21.6",
    ),
    GateRegistration(
        "CG-COM-004", GATE_FAMILY_CG_COMMERCIAL, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_COMPONENT_ENGINE,
        "Verification badges render only on VERIFIED content state (E10)",
        True, "engines.website_generation.gates.checks.commercial_checks", "§21.6",
    ),
    GateRegistration(
        "CG-COM-005", GATE_FAMILY_CG_COMMERCIAL, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_CONTENT,
        "Urgency claims reference spec-backed offer with expiry (E1)",
        True, "engines.website_generation.gates.checks.commercial_checks", "§21.6",
    ),
    GateRegistration(
        "CG-COM-006", GATE_FAMILY_CG_COMMERCIAL, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_COMPONENT_ENGINE,
        "Non-exact PriceSpec renders bound disclaimer (E4)",
        True, "engines.website_generation.gates.checks.commercial_checks", "§21.6",
    ),
    GateRegistration(
        "CG-COM-007", GATE_FAMILY_CG_COMMERCIAL, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RENDERER,
        "Consent controls equal-weight; no pre-checked marketing consent (E8)",
        True, "engines.website_generation.gates.checks.commercial_checks", "§21.6",
    ),
    GateRegistration(
        "CG-COM-008", GATE_FAMILY_CG_COMMERCIAL, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_COMPONENT_ENGINE,
        "CTA label class matches conversion goal (E9 table)",
        True, "engines.website_generation.gates.checks.commercial_checks", "§21.6",
    ),
    GateRegistration(
        "CG-COM-009", GATE_FAMILY_CG_COMMERCIAL, GATE_SEVERITY_WARNING, "",
        REMEDIATION_OWNER_RECIPE,
        "Trust component adjacent to lead forms",
        True, "engines.website_generation.gates.checks.commercial_checks", "§21.6",
    ),
    GateRegistration(
        "CG-COM-010", GATE_FAMILY_CG_COMMERCIAL, GATE_SEVERITY_WARNING, "",
        "R/RC",
        "Form friction budgets (§16.5)",
        True, "engines.website_generation.gates.checks.commercial_checks", "§21.6",
    ),
    GateRegistration(
        "CG-COM-011", GATE_FAMILY_CG_COMMERCIAL, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RECIPE,
        "Page conversion hierarchy matches recipe resolution (§16.6)",
        True, "engines.website_generation.gates.checks.commercial_checks", "§21.6",
    ),
    GateRegistration(
        "CG-COM-012", GATE_FAMILY_CG_COMMERCIAL, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RECIPE,
        "Monetization blocks appear only on roles permitted by §6.1; per-page sponsored caps",
        True, "engines.website_generation.gates.checks.commercial_checks", "§21.6",
    ),
    # --- CG-CON — Contract (§21.1) ---
    GateRegistration(
        "CG-CON-001", GATE_FAMILY_CG_CONTRACT, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_COMPONENT_ENGINE,
        "Every instance's component_id exists in registry",
        True, "engines.website_generation.gates.checks.component_checks", "§21.1",
    ),
    GateRegistration(
        "CG-CON-002", GATE_FAMILY_CG_CONTRACT, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_COMPONENT_ENGINE,
        "Instance version within registry's supported versions",
        True, "engines.website_generation.gates.checks.component_checks", "§21.1",
    ),
    GateRegistration(
        "CG-CON-003", GATE_FAMILY_CG_CONTRACT, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_COMPONENT_ENGINE,
        "All required props bound; types valid",
        True, "engines.website_generation.gates.checks.component_checks", "§21.1",
    ),
    GateRegistration(
        "CG-CON-004", GATE_FAMILY_CG_CONTRACT, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_COMPONENT_ENGINE,
        "No unknown props",
        True, "engines.website_generation.gates.checks.component_checks", "§21.1",
    ),
    GateRegistration(
        "CG-CON-005", GATE_FAMILY_CG_CONTRACT, GATE_SEVERITY_BLOCKING, "",
        "CE/CT",
        "All required content slots bound; cardinality respected",
        True, "engines.website_generation.gates.checks.component_checks", "§21.1",
    ),
    GateRegistration(
        "CG-CON-006", GATE_FAMILY_CG_CONTRACT, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_COMPONENT_ENGINE,
        "Variant exists in supported_variants",
        True, "engines.website_generation.gates.checks.component_checks", "§21.1",
    ),
    GateRegistration(
        "CG-CON-007", GATE_FAMILY_CG_CONTRACT, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_COMPONENT_ENGINE,
        "No DEPRECATED component without recorded build allowance; no RETIRED/BLOCKED "
        "ever; no x. in certifiable builds",
        True, "engines.website_generation.gates.checks.component_checks", "§21.1",
    ),
    GateRegistration(
        "CG-CON-008", GATE_FAMILY_CG_CONTRACT, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_REGISTRY,
        "compatibility_range satisfied vs renderer/token/registry versions",
        True, "engines.website_generation.gates.checks.component_checks", "§21.1",
    ),
    GateRegistration(
        "CG-CON-009", GATE_FAMILY_CG_CONTRACT, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_CONTENT,
        "Every ASSET_REF resolves in CAS with correct AssetRole",
        True, "engines.website_generation.gates.checks.component_checks", "§21.1",
    ),
    GateRegistration(
        "CG-CON-010", GATE_FAMILY_CG_CONTRACT, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_COMPONENT_ENGINE,
        "Every ROUTE_REF exists in SiteArchitecture",
        True, "engines.website_generation.gates.checks.component_checks", "§21.1",
    ),
    # --- CG-RND — Rendering (§21.3) ---
    GateRegistration(
        "CG-RND-001", GATE_FAMILY_CG_RENDERING, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RENDERER,
        "Deterministic output: double-render hash equality per page",
        True, "engines.website_generation.gates.checks.rendering_checks", "§21.3",
    ),
    GateRegistration(
        "CG-RND-002", GATE_FAMILY_CG_RENDERING, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RENDERER,
        "Valid HTML (deterministic conformance checker over emitted set)",
        True, "engines.website_generation.gates.checks.rendering_checks", "§21.3",
    ),
    GateRegistration(
        "CG-RND-003", GATE_FAMILY_CG_RENDERING, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RENDERER,
        "All interpolated content escaped (marker-probe fixtures)",
        True, "engines.website_generation.gates.checks.rendering_checks", "§21.3",
    ),
    GateRegistration(
        "CG-RND-004", GATE_FAMILY_CG_RENDERING, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RENDERER,
        "Stable attribute order + stable class names across builds",
        True, "engines.website_generation.gates.checks.rendering_checks", "§21.3",
    ),
    GateRegistration(
        "CG-RND-005", GATE_FAMILY_CG_RENDERING, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RENDERER,
        "Zero inline scripts; zero unapproved inline styles",
        True, "engines.website_generation.gates.checks.rendering_checks", "§21.3",
    ),
    GateRegistration(
        "CG-RND-006", GATE_FAMILY_CG_RENDERING, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RENDERER,
        "No-JS baseline paths present for every interactive contract",
        True, "engines.website_generation.gates.checks.rendering_checks", "§21.3",
    ),
    GateRegistration(
        "CG-RND-007", GATE_FAMILY_CG_RENDERING, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RENDERER,
        "Zero external requests in bundle (MVP); asset refs resolve",
        True, "engines.website_generation.gates.checks.rendering_checks", "§21.3",
    ),
    GateRegistration(
        "CG-RND-008", GATE_FAMILY_CG_RENDERING, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RENDERER,
        "No duplicate DOM ids; no internal-metadata markers in output",
        True, "engines.website_generation.gates.checks.rendering_checks", "§21.3",
    ),
    GateRegistration(
        "CG-RND-009", GATE_FAMILY_CG_RENDERING, GATE_SEVERITY_BLOCKING, "",
        "RN/CT",
        "No unsafe URLs (scheme whitelist) anywhere in emitted markup",
        True, "engines.website_generation.gates.checks.rendering_checks", "§21.3",
    ),
    GateRegistration(
        "CG-RND-010", GATE_FAMILY_CG_RENDERING, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_COMPONENT_ENGINE,
        "Structured-data fragments well-formed pre-compilation",
        True, "engines.website_generation.gates.checks.rendering_checks", "§21.3",
    ),
    # --- CG-RSP — Responsive (§21.7) ---
    GateRegistration(
        "CG-RSP-001", GATE_FAMILY_CG_RESPONSIVE, GATE_SEVERITY_BLOCKING, "",
        "R/CE",
        "Every instance has a valid resolved ResponsiveContract",
        True, "engines.website_generation.gates.checks.responsive_checks", "§21.7",
    ),
    GateRegistration(
        "CG-RSP-002", GATE_FAMILY_CG_RESPONSIVE, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RENDERER,
        "No prohibited horizontal overflow (deterministic CSS analysis: fixed widths "
        "> container at 320)",
        True, "engines.website_generation.gates.checks.responsive_checks", "§21.7",
    ),
    GateRegistration(
        "CG-RSP-003", GATE_FAMILY_CG_RESPONSIVE, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RECIPE,
        "Mobile order defined; visual-vs-DOM reorder within §11.3 rule",
        True, "engines.website_generation.gates.checks.responsive_checks", "§21.7",
    ),
    GateRegistration(
        "CG-RSP-004", GATE_FAMILY_CG_RESPONSIVE, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_REGISTRY,
        "Tables declare adaptation; no data loss mode",
        True, "engines.website_generation.gates.checks.responsive_checks", "§21.7",
    ),
    GateRegistration(
        "CG-RSP-005", GATE_FAMILY_CG_RESPONSIVE, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RENDERER,
        "Image behavior: aspect token + srcset policy present",
        True, "engines.website_generation.gates.checks.responsive_checks", "§21.7",
    ),
    GateRegistration(
        "CG-RSP-006", GATE_FAMILY_CG_RESPONSIVE, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RENDERER,
        "Sticky behavior bounded (offsets, z-tokens, footer clearance)",
        True, "engines.website_generation.gates.checks.responsive_checks", "§21.7",
    ),
    GateRegistration(
        "CG-RSP-007", GATE_FAMILY_CG_RESPONSIVE, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RENDERER,
        "Reflow-safe at 200% zoom (CSS analysis of absolute units)",
        True, "engines.website_generation.gates.checks.responsive_checks", "§21.7",
    ),
    GateRegistration(
        "CG-RSP-008", GATE_FAMILY_CG_RESPONSIVE, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RENDERER,
        "Touch-target verification at sm breakpoint",
        True, "engines.website_generation.gates.checks.responsive_checks", "§21.7",
    ),
    # --- CG-SEO — SEO (§21.5; extends GATE_FAMILY_SEO) ---
    GateRegistration(
        "CG-SEO-001", GATE_FAMILY_SEO, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RENDERER,
        "Heading rules (crawl view = §9.3 result; no hidden headings)",
        False, "", "§21.5",
    ),
    GateRegistration(
        "CG-SEO-002", GATE_FAMILY_SEO, GATE_SEVERITY_BLOCKING, "",
        "RN/CT",
        'Paid outbound links carry rel="sponsored"; UGC outbound nofollow ugc',
        False, "", "§21.5",
    ),
    GateRegistration(
        "CG-SEO-003", GATE_FAMILY_SEO, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RENDERER,
        "All internal links crawlable <a href> resolving to SiteArchitecture routes",
        False, "", "§21.5",
    ),
    GateRegistration(
        "CG-SEO-004", GATE_FAMILY_SEO, GATE_SEVERITY_BLOCKING,
        "BLOCKING (floors) / WARNING (ceilings) — §21.5 split severity",
        REMEDIATION_OWNER_RECIPE,
        "Internal-linking floors/ceilings per role (§6.2)",
        False, "", "§21.5",
    ),
    GateRegistration(
        "CG-SEO-005", GATE_FAMILY_SEO, GATE_SEVERITY_BLOCKING, "",
        "CE (fragments)",
        "Compiled structured data schema-valid; no conflicting duplicate entities",
        False, "", "§21.5",
    ),
    GateRegistration(
        "CG-SEO-006", GATE_FAMILY_SEO, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RENDERER,
        "User-visible content = crawler-visible content",
        False, "", "§21.5",
    ),
    GateRegistration(
        "CG-SEO-007", GATE_FAMILY_SEO, GATE_SEVERITY_WARNING, "",
        REMEDIATION_OWNER_CONTENT,
        "Duplicate content-block reuse <= page ceiling",
        False, "", "§21.5",
    ),
    GateRegistration(
        "CG-SEO-008", GATE_FAMILY_SEO, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_CONTENT,
        "Visible NAP <-> LocalBusiness markup parity",
        False, "", "§21.5",
    ),
    GateRegistration(
        "CG-SEO-009", GATE_FAMILY_SEO, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RECIPE,
        "Pagination markup crawl-safe; breadcrumb rules per role",
        False, "", "§21.5",
    ),
    # --- CG-STR-006 — reservation only (AMB-002I-04); not executable ---
    GateRegistration(
        "CG-STR-006", GATE_FAMILY_STRUCTURAL, GATE_SEVERITY_BLOCKING, "",
        REMEDIATION_OWNER_RECIPE,
        "Zero-state rule: pages with zero eligible results render a designed "
        "empty/zero-results state, not a blank or broken page. RESERVATION ONLY "
        "(AMB-002I-04) — no executable check function; implementation belongs to "
        "a future AES-WEB-001 Quality Gate Engine delivery.",
        False, "", "AES-WEB-001 §10.2 family; cited prospectively by AES-WEB-002 §6.2/§21.2/§27",
    ),
)

# Derived, deterministic lookups (pure data transforms — no I/O, no clock).
COMPONENT_GATE_IDS: Tuple[str, ...] = tuple(
    reg.gate_id for reg in COMPONENT_GATE_REGISTRATIONS
)
COMPONENT_GATE_BY_ID: Dict[str, GateRegistration] = {
    reg.gate_id: reg for reg in COMPONENT_GATE_REGISTRATIONS
}
EXECUTABLE_COMPONENT_GATE_IDS: Tuple[str, ...] = tuple(
    reg.gate_id for reg in COMPONENT_GATE_REGISTRATIONS if reg.executable
)
RESERVED_ONLY_GATE_IDS: Tuple[str, ...] = tuple(
    reg.gate_id for reg in COMPONENT_GATE_REGISTRATIONS if not reg.executable
)

# AES-WEB-002 §21 enumerates 73 gates across its seven per-family tables
# (10+11+10+13+9+12+8); its own closing line says "63" (AMB-002I-02, D1).
# This constant pins the operative, enumerated count so a future change is
# a visible test failure, not a silent drift.
AES_WEB_002_SECTION_21_ENUMERATED_GATE_COUNT = 73
