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

**AES-005A Website Intelligence Subsystem**

Regression Status:

- 715 tests passing
- Full regression green

Latest milestone commit:

2744cfa — Complete AES-005A Website Intelligence Pipeline

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

Next planned subsystem:

**AES-006 — Atlas Orchestrator**

Before writing any code:

1. Inspect the repository.
2. Understand the existing architecture.
3. Review current interfaces.
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