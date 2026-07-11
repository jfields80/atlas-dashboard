# Atlas Claude Code Instructions

## Project

You are working on **Atlas Investment OS**, an enterprise-grade software platform for discovering, evaluating, building, and managing profitable digital businesses.

Repository:

C:\Atlas\atlas-dashboard

GitHub:

https://github.com/jfields80/atlas-dashboard

---

# Current Status

Current completed milestone:

**AES-WEB-002B — Website Generation Engine, Wave 1 component catalog**

Progress to date (Website Generation Engine): AES-WEB-001 Phase 1 → amendments
A1–A4 (v1.1.0) → AES-WEB-002A (contracts + registry foundation) →
AES-WEB-002B (Wave 1: 15 layout/atom component definitions registered).
AES-DEP-001 (dependency baseline) and AES-REPO-001 (docs/patches
reorganization) are also complete. See `docs/architecture/authorities/` for
the governing architecture and `patches/` for the integration patches
covering this work (not yet merged to `main` — see Integration Patches
below).

Regression Status (verified baseline, pydantic 1.10.x + Flask):

- `python -m pytest tests/website_generation/ -q` → 254 passed
- `python -m pytest tests/ -q` → 1290 passed, exit 0
- `python -m compileall engines/website_generation` → clean

Latest milestone commit (on `main`):

fafde52 — AES-WEB-001 Phase 1: contracts, spine, and golden skeleton

Work since that commit (A1–A4 through AES-REPO-001) lives as uncommitted
work / integration patches in `patches/` pending operator integration — see
Integration Patches below for the exact apply order.

---

# Development Philosophy

Atlas is enterprise software.

Every engineering decision should prioritize long-term quality over short-term speed.

## Core Priorities

1. Maintainability
2. Determinism
3. Testability
4. Readability
5. Scalability

## Engineering Principles

- Prefer explicit code over clever code.
- Favor small, composable modules with single responsibilities.
- Every subsystem should be independently testable.
- Preserve public APIs unless explicitly approved.
- Deterministic behavior is preferred over convenience.
- Code should be understandable by another senior engineer.

### Optimization Rule

Never optimize for writing the fewest lines of code.

Always optimize for the next developer reading the code.

---

# Architecture Rules

Atlas follows strict architectural boundaries.

- Repository Pattern is mandatory.
- Services contain business logic.
- Repositories own persistence.
- Routes orchestrate only.
- Zero SQL in routes.
- Zero HTML/CSS/JS in business logic.
- Engines must remain deterministic.
- Pydantic contracts are immutable.
- Public contracts must remain stable.
- Every engine requires unit tests.
- Full regression is required before every commit.

---

# Never Do These Things

Never move files unless explicitly requested.

Never rename public classes.

Never rename public methods.

Never remove existing tests.

Never rewrite working modules.

Never redesign completed subsystems.

Never break Repository Pattern.

Never introduce SQL into routes.

Never introduce Flask dependencies into engines.

Never introduce side effects into deterministic engines.

Never bypass immutable contracts.

Never commit code unless regression is passing.

---

# Environment Setup

Dependencies are declared in `requirements.txt` (runtime) and
`requirements-dev.txt` (adds pytest). Atlas runs on **Pydantic v1** — do not
install Pydantic 2.x (it breaks the legacy models). Set up a clean env with
`python -m pip install -r requirements-dev.txt`. Full details, version
constraints, and the Pydantic-v1 rationale are in
`docs/development/environment.md`.

---

# Architecture Documentation

**`docs/architecture/authorities/` is the canonical source** for the
Website Generation Engine architecture documents:

- `AES-WEB-001_Implementation_Architecture.md` — pipeline implementation authority
- `AES-WEB-002_Commercial_Component_System_Architecture.md` — component-system authority
- `website_generation_engine_architecture.md` — Master Blueprint (intent authority)
- `Atlas_Website_Generation_Architecture_Index.md` — navigation aid ONLY (zero normative force)

Authority precedence (conflict rule): **Blueprint intent > AES-WEB-001 >
AES-WEB-002 > implementation tasks.** The Index never overrides an
authority. Amendments happen by version bump only, never silently.

Architecture Decision Records live in `docs/architecture/decisions/`
(e.g. `ADR-WEB-COMPONENT-FAMILY-TAXONOMY.md` — the normative 17-member
ComponentFamily set). Cite the source authority section (not the Index)
when making architecture-sensitive changes.

Repository layout reference: `docs/development/repository_layout.md`.

---

# Integration Patches

Sprint deliverables awaiting integration are stored in `patches/` as
sequentially numbered git patches (`0001-…` through `0005-…`). New patches
continue the numbering (next: `0006`). Apply order on a fresh clone of
`main` (Phase 1, commit `fafde52`):

1. `0003-AES-DEP-001-dependency-baseline.patch` (`git apply`)
2. `0001-AES-WEB-001-v1.1.0-apply-amendments-A1-A4.patch` (`git am`)
3. `0002-AES-WEB-002A-contracts-registry-selection-skeleton.patch` (`git apply`)
4. `0004-AES-WEB-002B-component-catalog-foundation.patch` (`git apply`)
5. `0005-AES-REVIEW-001A-pre-002C-repairs.patch` (`git apply`)

After the stack: `python -m pytest tests/ -q` must exit 0 (verified: 1290+
passed on the pre-0005 stack; see the report for each patch under
`docs/architecture/` history for exact counts).

---

# Regression Rules

Before every commit, run:

python -m pytest tests -v

A commit is not considered complete until the entire regression suite passes.

---

# Regression Fix Policy

When fixing regressions:

1. Read the current repository implementation.
2. Preserve existing imports.
3. Preserve public classes.
4. Preserve public methods.
5. Preserve immutable contracts.
6. Apply the smallest safe change.
7. Never rewrite modules from memory.

---

# Completed Subsystems

## AES-005A — Website Intelligence

Completed components:

- Immutable Models
- Constants
- Scoring Engine
- Recommendation Engine
- Audit Engine
- Work Order Planner
- Website Intelligence Pipeline

This subsystem is considered complete.

Do not redesign or rewrite AES-005A unless explicitly instructed.

---

# Current Development Phase

Next planned work: **AES-WEB-002C** (the next AES-WEB-002 catalog wave),
per the wave plan in `docs/architecture/authorities/
AES-WEB-002_Commercial_Component_System_Architecture.md` §31 and the
roadmap map in `Atlas_Website_Generation_Architecture_Index.md`. Do not
begin AES-WEB-002C or any later wave without explicit operator instruction.

Before writing any code:

1. Inspect the repository (including `patches/` for unintegrated prior work).
2. Read the exact authority section(s) governing the requested scope from
   `docs/architecture/authorities/` — never rely on a summary.
3. Review current interfaces (`engines/website_generation/contracts/`,
   `engines/website_generation/components/registry.py`).
4. Propose the implementation plan.
5. Wait for approval before modifying files.

---

# Expected Workflow

For every new feature:

1. Understand the existing implementation.
2. Design before coding.
3. Make the minimum required change.
4. Add or update tests.
5. Run targeted regression.
6. Run full regression.
7. Review changes.
8. Commit only after all tests pass.

Atlas values correctness, maintainability, and architectural consistency above development speed.