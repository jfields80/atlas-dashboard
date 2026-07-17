"""AES-DATA-001 importer -- immutable data models.

Frozen dataclasses shared across the importer, with deterministic
``to_dict``/``from_dict`` JSON serialization (sorted keys are applied at
write time by the persistence layer). No I/O, no network, no third-party
imports -- pure contracts, mirroring the ``directory_ingestion`` and WGE
frozen-model discipline.

None of these are WGE ``ArtifactKind``s; candidates persist as ordinary
JSON under a gitignored ``data/import`` root (mission sections 12/14).
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional, Tuple


# --------------------------------------------------------------------------- #
# Fetch result (raw acquisition; produced by a PageFetcher).
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class FetchResult:
    """The raw outcome of one fetch attempt. ``ok`` is True only when a
    usable HTML/XHTML body was retrieved; every other outcome carries a
    stable ``reason`` slug and ``ok=False`` (mission section 5)."""

    requested_url: str
    ok: bool
    final_url: str = ""
    http_status: int = 0
    content_type: str = ""
    body: bytes = b""
    redirect_chain: Tuple[str, ...] = ()
    response_headers: Tuple[Tuple[str, str], ...] = ()   # bounded subset
    reason: str = ""                                     # slug on failure
    warnings: Tuple[str, ...] = ()

    def headers_dict(self) -> dict:
        return {k: v for k, v in self.response_headers}


# --------------------------------------------------------------------------- #
# Source snapshot (immutable evidence anchor; raw bytes live in CAS).
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class SourceSnapshot:
    requested_url: str
    final_url: str
    observed_at: str
    http_status: int
    content_type: str
    redirect_chain: Tuple[str, ...]
    page_title: str
    canonical_url: str
    response_header_subset: Tuple[Tuple[str, str], ...]
    raw_content_hash: str                # sha256 of raw bytes in CAS
    normalized_text_hash: str            # sha256 of the exact text below
    normalized_text: str                 # bounded (<= 50 KB); what the LLM saw
    extraction_version: str
    fetch_warnings: Tuple[str, ...]
    source_relationship: str

    def to_dict(self) -> dict:
        d = asdict(self)
        # never inline raw HTML -- only the hash is kept (already the case).
        return d


# --------------------------------------------------------------------------- #
# Extraction output (from a FactExtractor -- static or Anthropic).
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class ProposedFact:
    """One field the extractor proposes. ``char_start``/``char_end`` are
    optional offsets into the snapshot normalized text; ``-1`` means the
    extractor supplied none and evidence validation must relocate the quote.
    ``ambiguous`` and ``warning`` are advisory inputs to validation, never
    trusted as authority."""

    field_name: str
    proposed_value: str
    quote: str
    char_start: int = -1
    char_end: int = -1
    ambiguous: bool = False
    warning: str = ""


@dataclass(frozen=True)
class ExtractionResult:
    facts: Tuple[ProposedFact, ...] = ()
    provider: str = ""
    model: str = ""
    prompt_version: str = ""
    ok: bool = True
    retries: int = 0
    error: str = ""                      # reason slug when ok is False


# --------------------------------------------------------------------------- #
# Evidence (every material published field must carry one).
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class ExtractedEvidence:
    field_name: str
    proposed_value: str
    source_wording: str
    source_url: str
    snapshot_quote: str                  # <= 300 chars, verbatim in snapshot
    char_start: int
    char_end: int
    extraction_method: str
    support_state: str                   # SUPPORTED | AMBIGUOUS | UNSUPPORTED
    warnings: Tuple[str, ...] = ()


# --------------------------------------------------------------------------- #
# Conflict (two evidence sources disagree on one field).
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Conflict:
    field_name: str
    competing_values: Tuple[str, ...]
    evidence: Tuple[ExtractedEvidence, ...]
    precedence_note: str = ""
    resolution_status: str = "UNRESOLVED"


# --------------------------------------------------------------------------- #
# Candidate listing (durable JSON; non-artifact).
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class ImportContext:
    category: str = ""
    expected_city: str = ""
    expected_state: str = ""
    candidate_name: str = ""
    source_type_hint: str = ""
    source_relationship_hint: str = ""


# --------------------------------------------------------------------------- #
# Source record (AES-DATA-002A contract; additive). One supplied URL's
# outcome within a candidate: single-source candidates carry an empty
# ``sources`` tuple on ``CandidateListing`` (unchanged shape); a future
# multi-source aggregate populates one ``SourceRecord`` per supplied URL.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    requested_url: str
    final_url: str
    role: str
    usable: bool
    fetch_reason: str
    excluded_reason: str
    source_relationship: str
    source_relationship_reason: str
    snapshot: Optional[SourceSnapshot]
    extraction_provider: str = ""
    extraction_model: str = ""
    prompt_version: str = ""
    warnings: Tuple[str, ...] = ()


@dataclass(frozen=True)
class CandidateListing:
    candidate_id: str
    created_at: str
    context: ImportContext
    snapshot: SourceSnapshot
    proposed_fields: Tuple[Tuple[str, str], ...]   # ordered CSV-compatible pairs
    pet_facts: Tuple[Tuple[str, str], ...]         # ordered structured pet facts
    evidence: Tuple[ExtractedEvidence, ...]
    missing_required: Tuple[str, ...]
    ambiguous_fields: Tuple[str, ...]
    conflicts: Tuple[Conflict, ...]
    warnings: Tuple[str, ...]
    category_confidence: str
    geography_confidence: str
    source_relationship: str
    source_relationship_reason: str
    extraction_provider: str
    extraction_model: str
    prompt_version: str
    extraction_version: str
    recommendation: str
    recommendation_reasons: Tuple[str, ...]
    review_status: str
    operator_edits: Tuple[Tuple[str, str, str], ...] = ()   # (field, old, new)
    approval_metadata: Tuple[Tuple[str, str], ...] = ()
    # AES-DATA-002A (additive; defaults preserve the AES-DATA-001 shape): a
    # single-source candidate carries sources=() and aggregation_version="".
    sources: Tuple[SourceRecord, ...] = ()
    aggregation_version: str = ""

    def proposed_dict(self) -> dict:
        return {k: v for k, v in self.proposed_fields}

    def pet_facts_dict(self) -> dict:
        return {k: v for k, v in self.pet_facts}
