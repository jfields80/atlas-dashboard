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

**AES-WEB-002E — Website Generation Engine, Wave 4 listing/profile catalog**

Progress to date (Website Generation Engine): AES-WEB-001 Phase 1 →
amendments A1–A4 (v1.1.0) → AES-WEB-002A (contracts + registry foundation)
→ AES-WEB-002B (Wave 1: 15 layout/atom primitives) → AES-WEB-002C (Wave 2:
8 navigation/legal/status components) → AES-WEB-002D (Wave 3: 9
hero/directory/status.results.zero components, plus the amendment-A4
provisional `listing.card.standard`, plus the production component-
selection pipeline resolving the home/category recipes for real) →
AES-WEB-002E (Wave 4: the full 12-component §27.5 listing/profile inventory
— `listing.card.featured`, `listing.card.sponsored`, `listing.row.compact`,
the seven-component `profile.*` family, and `content.description.business`
— plus the business-profile recipe table, §26.6). AES-DEP-001 (dependency
baseline) is also complete and merged. See `docs/` for the governing
architecture documents (`AES-WEB-001_Implementation_Architecture.md`,
`AES-WEB-002 — Commercial Component System Architecture (1).md`,
`website_generation_engine_architecture (2).md`, and the navigation-only
`Atlas Website Generation Architecture Index.md`) — all prior sprints'
patches have already been integrated into `main`; there is no pending
`patches/` directory.

Operator decision carried into and through AES-WEB-002E: no `rendering/` or
`gates/` package exists yet; emitters remain declared metadata only
(`RenderingContract.emitter_key`, unvalidated), consistent with the
AES-WEB-002B/C/D precedent. Every registered component, across all four
waves, stays at `PROPOSED` lifecycle — none is promoted to `ACTIVE`.

Regression Status (verified baseline, pydantic 1.10.x + Flask):

- `python -m pytest tests/website_generation/ -q` → 533 passed
- `python -m pytest tests/ -q` → 1578 passed, exit 0
- `python -m compileall engines/website_generation` → clean

Latest milestone commit (on `main` at the start of the AES-WEB-002E session):

a182020 — AES-WEB-002D: implement directory discovery wave

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

**`docs/` is the canonical source** for the Website Generation Engine
architecture documents (there is no `docs/architecture/authorities/`
subdirectory in this repository — the authority documents live directly
under `docs/`):

- `AES-WEB-001_Implementation_Architecture.md` — pipeline implementation authority
- `AES-WEB-002 — Commercial Component System Architecture (1).md` — component-system authority
- `website_generation_engine_architecture (2).md` — Master Blueprint (intent authority)
- `Atlas Website Generation Architecture Index.md` — navigation aid ONLY (zero normative force)

Authority precedence (conflict rule): **Blueprint intent > AES-WEB-001 >
AES-WEB-002 > implementation tasks.** The Index never overrides an
authority. Amendments happen by version bump only, never silently.

Architecture Decision Records live in `docs/architecture/decisions/`
(e.g. `ADR-WEB-COMPONENT-FAMILY-TAXONOMY.md` — the normative 17-member
ComponentFamily set). Cite the source authority section (not the Index)
when making architecture-sensitive changes.

Do not move, rename, reorganize, or rewrite these authority documents;
correct only clearly stale paths/status prose elsewhere (e.g. in this file)
when they conflict with the actual repository layout.

---

# Integration History

Earlier sprints (A1–A4 amendments, AES-DEP-001 dependency baseline,
AES-WEB-002A/B/C) were staged as sequentially numbered git patches under a
`patches/` directory; all of that work has since been integrated into
`main` (see the "Current Status" commit above), and `patches/` no longer
exists in the repository. New sprint work is developed directly against
`main` per the branch/workflow instructions given for that session — there
is no standing patch-staging step to repeat.

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

Next planned work: **AES-WEB-002F** (Wave 5 — Trust, Conversion, and Forms,
§27.6), per the wave plan in `docs/AES-WEB-002 — Commercial Component
System Architecture (1).md` §31 and the roadmap map in `docs/Atlas Website
Generation Architecture Index.md`. AES-WEB-002E completed Wave 4 (§27.5):
`catalog/listings_profiles.py`'s `WAVE4_COMPONENTS` now carries all twelve
listing/profile components (`listing.card.standard` — provisional since
002D under amendment A4 — plus the eleven components 002E delivered), and
the business-profile recipe (§26.6) is authored as
`BUSINESS_PROFILE_RECIPE_SLOTS` in `constants/components.py`. 002F is
responsible for the thirteen-component Wave 5 inventory (`trust.*`,
`cta.*`, `form.*`) plus their fixtures. Per the standing operator decision
carried through 002D and 002E, no `rendering/` package, real emitters, or
`ACTIVE` lifecycle promotion are in scope unless an operator explicitly
authorizes that expansion. Do not begin AES-WEB-002F or any later wave
without explicit operator instruction.

Before writing any code:

1. Inspect the repository for prior work (`git log`, existing
   `engines/website_generation/` packages — there is no `patches/`
   directory to check; all prior sprints are already merged to `main`).
2. Read the exact authority section(s) governing the requested scope from
   `docs/` — never rely on a summary.
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