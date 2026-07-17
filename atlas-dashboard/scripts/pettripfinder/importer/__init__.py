"""AES-DATA-001 Official URL Importer V1.

Upstream, script-layer PetTripFinder subsystem: one official URL ->
SSRF-safe fetch -> immutable source snapshot -> evidence-backed candidate ->
local review -> explicit approval -> staging CSV -> explicit promotion into
the tracked seed CSV. Not a WGE engine (network + LLM live here, outside the
deterministic website-generation pipeline). No new ArtifactKind.
"""

from scripts.pettripfinder.importer.constants import (
    EXTRACTION_VERSION,
    IMPORTER_VERSION,
    PROMPT_VERSION,
)

__all__ = ["EXTRACTION_VERSION", "PROMPT_VERSION", "IMPORTER_VERSION"]
