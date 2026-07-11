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
