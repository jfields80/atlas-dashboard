"""Directory Blueprint Service.

Service-layer orchestration for Atlas Phase 3:
    * Validates raw input dicts into a ``BlueprintRequest``
    * Enforces the BUILD/TEST eligibility gate
    * Invokes the deterministic blueprint engine
    * Persists results through the repository (idempotent on input hash)

Atlas contract: business logic and orchestration only — zero SQL, no Flask.
The canonical API is the module-level functions; ``DirectoryBlueprintService``
is a compatibility shim only.
"""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, Optional

from engines.directory_blueprint.blueprint_generator import (
    BLUEPRINT_ENGINE_VERSION,
    generate_blueprint,
    is_blueprint_eligible,
)
from engines.directory_blueprint.blueprint_models import (
    BlueprintRequest,
    DirectoryBlueprint,
)
from engines.directory_blueprint.pydantic_compat import (
    model_from_dict,
    model_from_json,
    model_to_json,
)
from repositories import directory_blueprint_repository as blueprint_repo

# ---------------------------------------------------------------------------
# Result contract
# ---------------------------------------------------------------------------

RESULT_GENERATED = "GENERATED"
RESULT_DUPLICATE = "DUPLICATE"
RESULT_NOT_ELIGIBLE = "NOT_ELIGIBLE"


class BlueprintServiceResult:
    """Plain result object (no Pydantic needed at the service boundary)."""

    __slots__ = ("status", "blueprint", "blueprint_id", "reason")

    def __init__(
        self,
        status: str,
        blueprint: Optional[DirectoryBlueprint] = None,
        blueprint_id: Optional[int] = None,
        reason: str = "",
    ):
        self.status = status
        self.blueprint = blueprint
        self.blueprint_id = blueprint_id
        self.reason = reason

    @property
    def generated(self) -> bool:
        return self.status == RESULT_GENERATED


# ---------------------------------------------------------------------------
# Canonical functional API
# ---------------------------------------------------------------------------


def build_request(payload: Dict[str, Any]) -> BlueprintRequest:
    """Validate a raw dict (e.g. assembled from pipeline outputs) into a request."""
    return model_from_dict(BlueprintRequest, payload)


def generate_and_store_blueprint(
    conn: sqlite3.Connection, request: BlueprintRequest
) -> BlueprintServiceResult:
    """Full orchestration: gate -> generate -> persist (idempotent).

    Never raises for the not-eligible case; returns a NOT_ELIGIBLE result so
    pipeline callers can log the decision without exception handling.
    """
    if not is_blueprint_eligible(request):
        return BlueprintServiceResult(
            status=RESULT_NOT_ELIGIBLE,
            reason=(
                "Committee recommendation %s does not authorize a blueprint "
                "(requires BUILD or TEST)" % request.committee.recommendation.value
            ),
        )

    blueprint = generate_blueprint(request)

    blueprint_repo.ensure_schema(conn)
    existing = blueprint_repo.find_by_input_hash(
        conn, blueprint.input_hash, blueprint.engine_version
    )
    if existing is not None:
        stored = model_from_json(DirectoryBlueprint, existing["blueprint_json"])
        return BlueprintServiceResult(
            status=RESULT_DUPLICATE,
            blueprint=stored,
            blueprint_id=int(existing["id"]),
            reason="Identical input hash already stored for this engine version",
        )

    blueprint_id = blueprint_repo.insert_blueprint(
        conn,
        project_slug=blueprint.project_profile.project_slug,
        engine_version=blueprint.engine_version,
        input_hash=blueprint.input_hash,
        committee_recommendation=request.committee.recommendation.value,
        data_confidence_tag=blueprint.data_confidence_tag.value,
        blueprint_json=model_to_json(blueprint),
    )
    return BlueprintServiceResult(
        status=RESULT_GENERATED, blueprint=blueprint, blueprint_id=blueprint_id
    )


def generate_and_store_from_payload(
    conn: sqlite3.Connection, payload: Dict[str, Any]
) -> BlueprintServiceResult:
    """Convenience wrapper: validate the raw payload, then orchestrate."""
    return generate_and_store_blueprint(conn, build_request(payload))


def load_latest_blueprint(
    conn: sqlite3.Connection, project_slug: str
) -> Optional[DirectoryBlueprint]:
    """Load and re-validate the most recent stored blueprint for a project."""
    blueprint_repo.ensure_schema(conn)
    row = blueprint_repo.get_latest_blueprint_for_slug(conn, project_slug)
    if row is None:
        return None
    return model_from_json(DirectoryBlueprint, row["blueprint_json"])


ENGINE_VERSION = BLUEPRINT_ENGINE_VERSION


class DirectoryBlueprintService:
    """Compatibility shim over the canonical functional API."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def generate_and_store(self, request: BlueprintRequest) -> BlueprintServiceResult:
        return generate_and_store_blueprint(self._conn, request)

    def generate_and_store_from_payload(self, payload: Dict[str, Any]) -> BlueprintServiceResult:
        return generate_and_store_from_payload(self._conn, payload)

    def load_latest(self, project_slug: str) -> Optional[DirectoryBlueprint]:
        return load_latest_blueprint(self._conn, project_slug)
