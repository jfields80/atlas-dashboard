"""
persistence.py — Atlas Memory Persistence Layer (CLEAN, NO CIRCULAR IMPORTS)
"""

import json
import os

_STORAGE_FILE = "atlas_learning_memory.json"


# ─────────────────────────────────────────────
# PURE DATA STRUCTURES (NO IMPORTS FROM CORE)
# ─────────────────────────────────────────────

class OpportunityOutcomeDTO:
    def __init__(self, niche_name, predicted_score, actual_outcome_score, recommendation, success):
        self.niche_name = niche_name
        self.predicted_score = predicted_score
        self.actual_outcome_score = actual_outcome_score
        self.recommendation = recommendation
        self.success = success


class LearningMemoryDTO:
    def __init__(self):
        self.outcomes = []


# ─────────────────────────────────────────────
# SAVE
# ─────────────────────────────────────────────

def save_memory(memory):
    data = {
        "outcomes": [
            {
                "niche_name": o.niche_name,
                "predicted_score": o.predicted_score,
                "actual_outcome_score": o.actual_outcome_score,
                "recommendation": o.recommendation,
                "success": o.success,
            }
            for o in memory.outcomes
        ]
    }

    with open(_STORAGE_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ─────────────────────────────────────────────
# LOAD
# ─────────────────────────────────────────────

def load_memory():
    memory = LearningMemoryDTO()

    if not os.path.exists(_STORAGE_FILE):
        return memory

    try:
        with open(_STORAGE_FILE, "r") as f:
            data = json.load(f)

        for o in data.get("outcomes", []):
            memory.outcomes.append(
                OpportunityOutcomeDTO(
                    niche_name=o.get("niche_name", ""),
                    predicted_score=o.get("predicted_score", 0),
                    actual_outcome_score=o.get("actual_outcome_score", 0),
                    recommendation=o.get("recommendation", "UNKNOWN"),
                    success=o.get("success", False),
                )
            )

    except Exception as e:
        print("[Atlas Persistence Error]", str(e))
        return LearningMemoryDTO()

    return memory