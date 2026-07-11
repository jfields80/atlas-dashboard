"""Pipeline package: the single engine-layer composition point (§3.1).

Exports the public pipeline class. The pure state machine's transition
internals remain internal (importable directly only by architecture and
state-machine tests).
"""

from engines.website_generation.pipeline.website_generation_pipeline import (
    WebsiteGenerationBuildResult,
    WebsiteGenerationPipeline,
)

__all__ = ["WebsiteGenerationBuildResult", "WebsiteGenerationPipeline"]
