# Directory Blueprint Engine — Quick Start

Atlas Phase 3 subsystem. Converts an approved (BUILD/TEST) opportunity into a
complete directory business blueprint.

## Install layout

Extract the ZIP directly into `C:\Atlas\atlas-dashboard`. It adds:

```
engines/directory_blueprint/     # pure planning engines (7 modules)
services/directory_blueprint_service.py
repositories/directory_blueprint_repository.py
models/directory_blueprint_schema.sql
tests/test_directory_blueprint.py
docs/directory_blueprint_engine.md   # full developer guide
docs/directory_blueprint_README.md   # this file
integration_changes/README.md        # optional, no existing files modified
```

No existing files are overwritten. `services/opportunity_v2/` and
`services/pipeline_runner.py` are untouched.

## Verify

```
python -m pytest tests\test_directory_blueprint.py -v
```

Expected: 48 passed. Requires pydantic (v1 or v2) and pytest. No Flask.

## 30-second usage

```python
import sqlite3
from engines.directory_blueprint import (
    BlueprintRequest, OpportunityInput, CommitteeInput, CommitteeRecommendation,
)
from services import directory_blueprint_service as svc

request = BlueprintRequest(
    opportunity=OpportunityInput(name="SkilledTradePathway", niche="skilled trades training", score=68.0),
    committee=CommitteeInput(recommendation=CommitteeRecommendation.TEST, confidence=0.4),
)
conn = sqlite3.connect("atlas.db")
result = svc.generate_and_store_blueprint(conn, request)
print(result.status)                                # GENERATED
print(result.blueprint.monetization_plan.primary_model)
print(result.blueprint.implementation_roadmap.total_estimated_effort_weeks)
```

WATCH/PASS recommendations return a NOT_ELIGIBLE result — no blueprint, no write.
Replaying identical inputs returns DUPLICATE with the originally stored document.

See `docs/directory_blueprint_engine.md` for architecture, diagrams, scoring
constants, and extension points.
