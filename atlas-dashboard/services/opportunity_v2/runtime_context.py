"""
runtime_context.py — Atlas Safe System Bootstrap Layer

Prevents:
- circular imports
- unsafe initialization order
- partial memory loads
"""

from .learning_memory import update_learning_weights
from .persistence import load_memory


class RuntimeContext:
    def __init__(self):
        self.memory = None
        self.weights = None
        self.initialized = False

    def initialize(self):
        """
        Safe boot sequence for Atlas core systems.
        """

        self.memory = load_memory()
        self.weights = update_learning_weights()
        self.initialized = True

        print("[Atlas] Runtime context initialized")
        print(f"[Atlas] Memory records: {len(self.memory.outcomes)}")
        print(f"[Atlas] Learning weights: {self.weights}")


# global singleton
runtime = RuntimeContext()