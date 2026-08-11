"""Deterministic inventory profiling (AES-SEO-001 §7, Phase B).

One engine, one verb: ``InventoryProfiler.profile`` turns a frozen
``GenericInventorySnapshot`` into a ``DimensionProfileSet``. Pure and
deterministic per §4 — no I/O, no clock, no randomness, no network.
"""

from engines.demand_mapping.profiling.inventory_profiler import (
    InventoryProfiler,
    ProfilingError,
)

__all__ = ["InventoryProfiler", "ProfilingError"]
