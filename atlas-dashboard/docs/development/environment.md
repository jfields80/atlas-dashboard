# Atlas Development Environment (AES-DEP-001)

This document standardizes the supported dependency set so Windows, Claude
Code, clean virtual environments, and future CI all install the same
packages. It is a dependency-management baseline only — it changes no
business logic and does not migrate Atlas to Pydantic 2.

## Supported baseline

| Component | Constraint | Proven-working |
|---|---|---|
| Python | 3.11+ | 3.11.15 |
| pydantic | `>=1.10.13,<2.0` | 1.10.13 |
| Flask | `>=2.2,<4.0` | 3.1.3 |
| requests | `>=2.28,<3.0` | 2.33.1 |
| beautifulsoup4 | `>=4.11,<5.0` | (runtime dep of quality_audit) |
| PyYAML | `>=6.0,<7.0` | 6.0.1 |
| pytest (dev) | `>=7.0,<10.0` | 9.1.1 |

## Why Pydantic must stay on v1 (`<2`)

Atlas's legacy base models (`engines/directory_builder/models.py`,
`engines/website_generator/models.py`) declare **both** a
`model_config = ConfigDict(...)` (available in Pydantic 1.10.x via a
forward-compat shim) **and** a nested `class Config:` for v1/v2
compatibility. Every Pydantic **2.x** release (2.0 → 2.13) rejects that
combination with a hard error:

```
pydantic.errors.PydanticUserError: "Config" and "model_config" cannot be used together
```

Under Pydantic **1.10.x** the `model_config` attribute is inert and
`class Config` is authoritative, so the models import cleanly. Until an
explicit Pydantic-2 migration sprint refactors these models, the `<2`
ceiling is mandatory. The Website Generation Engine contracts
(`engines/website_generation/…`) are already written for v1/v2
compatibility and pass under both.

## Set up a clean environment

From the application root (`atlas-dashboard/`):

```bash
python -m venv .venv
# Windows:        .venv\Scripts\activate
# macOS / Linux:  source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

`.venv/` is git-ignored. Runtime-only deployments can install
`requirements.txt` instead of `requirements-dev.txt`.

## Verify

```bash
python -m pytest tests/website_generation/ -q     # component/WGE suite
python -m pytest tests/ -q                         # full regression (exit 0)
python -m compileall engines/website_generation    # byte-compile check
```

The full suite must exit 0 with no collection errors. Collection errors of
the form `"Config" and "model_config" cannot be used together` mean Pydantic
2.x was installed — reinstall from `requirements-dev.txt`.

## Scope notes

- Only **direct** dependencies are declared; pip resolves transitives.
- `beautifulsoup4` is a direct runtime import of
  `services/opportunity_v2/quality_audit.py`; it is declared even though the
  current test subset does not exercise it.
- No `pyproject.toml`, Poetry, Pipenv, Hatch, Docker, or CI is introduced by
  this baseline.
