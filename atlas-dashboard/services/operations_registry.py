"""
atlas/services/operations_registry.py

AES-009B — reusable operation-descriptor framework for the Operations
Center UI.

Decouples "what operations exist" (this module) from "how a specific
operation executes" (e.g. services/pipeline_execution_service.py for
Directory Launch) so future operations -- pipeline-backed or not --
can be added by extending list_operations() without touching the
route or template.

Introduces no new business capability: AES-009B is a pure refactor of
AES-009A's Operations Center. Directory Launch remains the only
registered operation and its behavior/URLs are unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass

from services.orchestrator.pipelines.directory_launch import PIPELINE_NAME


@dataclass(frozen=True)
class OperationDescriptor:
    """
    Lightweight metadata for one operation shown on the Operations
    Center page.

    Attributes:
        key: Stable identifier for the operation.
        name: Display name shown on its card.
        description: Short summary shown on its card.
        icon: Single glyph rendered on its card.
        route: Where the card's "Configure & Run" action points --
            an in-page anchor (e.g. "#run-...") today; may become a
            full URL for a future operation with its own dedicated
            page.
        status: "available" once wired to a real run panel/route;
            future operations can be listed as e.g. "coming_soon"
            before their execution path exists.
    """

    key: str
    name: str
    description: str
    icon: str
    route: str
    status: str = "available"


def list_operations() -> list[OperationDescriptor]:
    """
    Returns every operation to display on the Operations Center page.

    AES-009B scope: exactly one entry (Directory Launch). Extending
    this list is how future operations (Opportunity Scan, Website
    Audit, Marketing, etc.) get added -- no route or template change
    required as long as they follow the same descriptor shape.
    """
    return [
        OperationDescriptor(
            key=PIPELINE_NAME,
            name="Directory Launch",
            description=(
                "Runs the Directory Launch pipeline: Blueprint -> Ingestion -> "
                "Launch Kit -> Directory Builder -> Preview, using an existing "
                "completed Investment Committee decision."
            ),
            icon="▶",
            route=f"#run-{PIPELINE_NAME}",
            status="available",
        )
    ]
