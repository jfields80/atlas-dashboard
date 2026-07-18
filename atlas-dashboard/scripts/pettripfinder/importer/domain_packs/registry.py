"""AES-DATA-003A -- deterministic domain-pack registry.

A ``DomainPackRegistry`` is a simple, ordered lookup table from category ID
to the ``DomainPack`` that serves it. Registration order is the only source
of ordering (``category_ids()``/``packs()`` both reflect it); there is no
sorting, no priority system, and no silent fallback -- an unresolved
category always raises ``UnknownCategoryError``.

The module-level ``default_registry`` is the single canonical registry for
this phase, built once at import time from the three legacy pack
descriptors. Nothing in this codebase registers a pack after that -- by
convention, not by an enforced runtime lock (kept simple per mission
Amendment 3; a later phase may add packs to a still-being-assembled
registry, but never mutates ``default_registry`` after import).
"""

from __future__ import annotations

from typing import Dict, Tuple

from scripts.pettripfinder.importer.domain_packs.base import (
    DomainPack,
    DuplicateCategoryRegistrationError,
    UnknownCategoryError,
)


class DomainPackRegistry:
    def __init__(self) -> None:
        self._by_category: Dict[str, DomainPack] = {}
        self._packs: Tuple[DomainPack, ...] = ()

    def register(self, pack: DomainPack) -> None:
        for cat in pack.category_ids:
            if cat in self._by_category:
                raise DuplicateCategoryRegistrationError(
                    "category %r is already registered to pack %r -- cannot "
                    "register pack %r for the same category"
                    % (cat, self._by_category[cat].pack_id, pack.pack_id))
        for cat in pack.category_ids:
            self._by_category[cat] = pack
        self._packs = self._packs + (pack,)

    def for_category(self, category_id: str) -> DomainPack:
        try:
            return self._by_category[category_id]
        except KeyError:
            raise UnknownCategoryError(
                "no domain pack is registered for category %r" % (category_id,)) from None

    def category_ids(self) -> Tuple[str, ...]:
        """Every registered category, in deterministic registration order
        (each pack's own ``category_ids`` order, packs in registration
        order)."""
        out = []
        for pack in self._packs:
            out.extend(pack.category_ids)
        return tuple(out)

    def packs(self) -> Tuple[DomainPack, ...]:
        return self._packs


def _build_default_registry() -> DomainPackRegistry:
    # Deferred imports: lodging/parks/dining/veterinary import constants.py
    # (a pure leaf module) but never this registry module, so this stays a
    # one-directional dependency with no cycle.
    from scripts.pettripfinder.importer.domain_packs.dining import DINING_PACK
    from scripts.pettripfinder.importer.domain_packs.lodging import LODGING_PACK
    from scripts.pettripfinder.importer.domain_packs.parks import PARKS_PACK
    from scripts.pettripfinder.importer.domain_packs.veterinary import VETERINARY_PACK

    registry = DomainPackRegistry()
    registry.register(LODGING_PACK)
    registry.register(PARKS_PACK)
    registry.register(DINING_PACK)
    registry.register(VETERINARY_PACK)   # AES-DATA-003B: first non-legacy pack
    return registry


default_registry = _build_default_registry()
