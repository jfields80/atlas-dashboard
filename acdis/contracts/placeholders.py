from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EvidenceType(str, Enum):
    FACT = "FACT"
    INFERENCE = "INFERENCE"
    HYPOTHESIS = "HYPOTHESIS"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class EvidenceItem:
    evidence_type: EvidenceType
    summary: str
    source: str


@dataclass(frozen=True)
class OpportunityInput:
    name: str
    description: str


@dataclass(frozen=True)
class CompetitorInput:
    name: str
    notes: str
