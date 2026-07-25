"""Minimal, isolated ACDIS package scaffold."""

from .contracts.placeholders import CompetitorInput, EvidenceItem, EvidenceType, OpportunityInput
from .safeguards.path_fence import PathFenceError, ensure_acdis_path, get_active_git_root, get_approved_root

__all__ = [
    "CompetitorInput",
    "EvidenceItem",
    "EvidenceType",
    "OpportunityInput",
    "PathFenceError",
    "ensure_acdis_path",
    "get_active_git_root",
    "get_approved_root",
]
