"""Build constants: stage order, retry ceilings (AES-WEB-001 §6.3, Part 13).

Stage names are plain strings (not enums) because this package may import
nothing beyond the standard library (§3.2). The pipeline maps stage names
to BuildState values; the mapping is asserted by tests.
"""

PIPELINE_VERSION = "1.0.0"

STAGE_SPEC_COMPILATION = "spec_compilation"
STAGE_BRAND_RESOLUTION = "brand_resolution"
STAGE_IA_PLANNING = "ia_planning"
STAGE_CONTENT_DRAFTING = "content_drafting"
STAGE_CONTENT_VALIDATION = "content_validation"
STAGE_COMPONENT_RESOLUTION = "component_resolution"
STAGE_LAYOUT_COMPOSITION = "layout_composition"
STAGE_RENDERING = "rendering"
STAGE_SEO_COMPILATION = "seo_compilation"
STAGE_ASSEMBLY = "assembly"
STAGE_GATING = "gating"
STAGE_CERTIFICATION = "certification"
STAGE_PACKAGING = "packaging"

# Canonical stage order for the active build sequence (§6.2).
ACTIVE_STAGE_SEQUENCE = (
    STAGE_SPEC_COMPILATION,
    STAGE_BRAND_RESOLUTION,
    STAGE_IA_PLANNING,
    STAGE_CONTENT_DRAFTING,
    STAGE_CONTENT_VALIDATION,
    STAGE_COMPONENT_RESOLUTION,
    STAGE_LAYOUT_COMPOSITION,
    STAGE_RENDERING,
    STAGE_SEO_COMPILATION,
    STAGE_ASSEMBLY,
    STAGE_GATING,
    STAGE_CERTIFICATION,
    STAGE_PACKAGING,
)

# Stages the Phase 1 skeleton pipeline actually executes. Every other
# stage is recorded in the BuildManifest as NOT_EXECUTED (Sprint 1
# directive: unimplemented stages are never reported successful).
PHASE1_EXECUTED_STAGES = (STAGE_SPEC_COMPILATION,)

# Retry ceilings (§6.3). Deterministic stages are never retried: same
# input yields the same failure, so their ceiling is 1 attempt.
MAX_COGNITION_ATTEMPTS_PER_CELL = 3
MAX_GATE_REWORK_CYCLES = 2
MAX_DEPLOY_VERIFY_ATTEMPTS = 3

# ---------------------------------------------------------------------------
# Part 13 Phase 2 scope clarification (AES-WEB-001 v1.1.0 amendment A4)
# ---------------------------------------------------------------------------
#
# AES-WEB-002 §34.3-A4 clarifies AES-WEB-001 Part 13 Phase 2: the Phase 2
# "minimal component registry (header, hero, listing grid, detail block,
# text section, footer)" scope is superseded by the AES-WEB-002 A–K wave
# structure. Phase 2's deliverable proof (fixture spec -> byte-stable static
# site) is achieved at AES-WEB-002D exit (Waves 1–3 plus a provisional
# listing card) and completed through AES-WEB-002J; AES-WEB-002K remains the
# certification / golden-fixture boundary. This is a roadmap clarification
# only — no contract change, and no permission to implement those phases now.
PHASE2_SCOPE_SUPERSEDED_BY = "AES-WEB-002 A-K wave structure"
PHASE2_INITIAL_PROOF_MILESTONE = "AES-WEB-002D"
MVP_INTEGRATION_PROOF_MILESTONE = "AES-WEB-002J"
CERTIFICATION_GOLDEN_FIXTURE_BOUNDARY = "AES-WEB-002K"
