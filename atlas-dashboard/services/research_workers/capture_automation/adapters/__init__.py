"""Brand adapters. Phase 1 ships Marriott and Hilton."""

from .base import BrandAdapter, BaseAdapter
from .registry import adapter_for, known_brands, register

__all__ = ["BrandAdapter", "BaseAdapter", "adapter_for", "known_brands", "register"]
