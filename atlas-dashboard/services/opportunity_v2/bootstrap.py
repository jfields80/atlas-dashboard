"""
bootstrap.py — Atlas System Initialization Layer

This ensures:
- Learning memory loads from disk on startup
- System state is restored consistently
- No silent resets between runs
"""

from .persistence import load_memory
from .learning_memory import get_memory, OpportunityOutcome


def initialize_memory_system():
    """
    Loads persisted learning memory from disk (persistence.load_memory)
    and replays it into the live in-process LearningMemory singleton
    (learning_memory.get_memory) so runtime state reflects what was
    persisted on a prior run.

    Lives here rather than in persistence.py: persistence.py is
    deliberately kept free of any import from learning_memory.py to
    avoid a circular import (learning_memory.py already imports from
    persistence.py). bootstrap.py sits above both, so it's the correct
    place for code that touches both modules.
    """
    persisted = load_memory()
    memory = get_memory()

    for outcome in persisted.outcomes:
        memory.record_outcome(
            OpportunityOutcome(
                niche_name=outcome.niche_name,
                predicted_score=outcome.predicted_score,
                actual_outcome_score=outcome.actual_outcome_score,
                recommendation=outcome.recommendation,
                success=outcome.success,
            )
        )

    return memory


def boot_atlas():
    """
    Call this ONCE when Flask app starts.
    Restores full learning + memory state.
    """

    print("[Atlas] Booting intelligence system...")

    # Load persisted learning memory into runtime
    initialize_memory_system()

    memory = get_memory()

    print("[Atlas] Memory loaded:")
    print(f"  - Records: {len(memory.outcomes)}")
    print(f"  - Success Rate: {memory.success_rate():.2f}")
    print(f"  - Avg Error: {memory.average_error():.2f}")

    print("[Atlas] System ready.")