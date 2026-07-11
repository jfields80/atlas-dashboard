"""BusinessSpec compilation package (AES-WEB-001 §5.1).

The sole ingestion point from the rest of Atlas into the Website
Generation Engine. Nothing downstream reads upstream Atlas models
directly.
"""

from engines.website_generation.speccompiler.business_spec_compiler import (
    BusinessSpecCompiler,
)

__all__ = ["BusinessSpecCompiler"]
