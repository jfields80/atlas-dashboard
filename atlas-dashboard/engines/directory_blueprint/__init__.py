"""Directory Intelligence & Blueprint Engine (Atlas Phase 3).

Public API:
    generate_blueprint(request) -> DirectoryBlueprint   (canonical)
    is_blueprint_eligible(request) -> bool
    BlueprintGenerator                                  (compatibility shim)
"""

from engines.directory_blueprint.blueprint_generator import (
    BLUEPRINT_ENGINE_NAME,
    BLUEPRINT_ENGINE_VERSION,
    BlueprintGenerator,
    generate_blueprint,
    is_blueprint_eligible,
)
from engines.directory_blueprint.blueprint_models import (
    BlueprintRequest,
    CommitteeInput,
    CommitteeRecommendation,
    DirectoryBlueprint,
    ExpansionClassificationInput,
    MarketCapacityInput,
    OpportunityInput,
    PortfolioContextInput,
)

__all__ = [
    "BLUEPRINT_ENGINE_NAME",
    "BLUEPRINT_ENGINE_VERSION",
    "BlueprintGenerator",
    "BlueprintRequest",
    "CommitteeInput",
    "CommitteeRecommendation",
    "DirectoryBlueprint",
    "ExpansionClassificationInput",
    "MarketCapacityInput",
    "OpportunityInput",
    "PortfolioContextInput",
    "generate_blueprint",
    "is_blueprint_eligible",
]
