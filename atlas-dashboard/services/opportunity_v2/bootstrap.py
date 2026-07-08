"""
bootstrap.py — Atlas System Initialization Layer

This ensures:
- Learning memory loads from disk on startup
- System state is restored consistently
- No silent resets between runs
"""

from .persistence import initialize_memory_system
from .learning_memory import get_memory


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