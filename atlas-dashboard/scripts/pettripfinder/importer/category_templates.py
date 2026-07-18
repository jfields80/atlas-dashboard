"""AES-DATA-001 importer -- category-specific field whitelists (mission
section 10). Deliberately small: only the fields PetTripFinder V1 needs.
Anything outside a category's allowed set is rejected deterministically by
the extractor parser and evidence layer -- no broad ontology.

AES-DATA-003A: the per-category field tuples now live in
``domain_packs/lodging.py``/``parks.py``/``dining.py`` as the source of
truth; this module is a thin, behavior-preserving compatibility shim that
delegates to the domain-pack registry. Every public name here (functions,
dict shape/content, ``PETS_ALLOWED_FIELD``, ``REQUIRED_CSV_FIELDS``) is
unchanged for existing callers -- ``allowed_fields``/``allowed_field_order``
still return the exact same values for the three existing categories, and
still return the empty default (never raise) for an unrecognized one.
"""

from __future__ import annotations

from typing import Dict, FrozenSet, Tuple

from scripts.pettripfinder.importer.constants import REQUIRED_CSV_FIELDS  # re-exported
from scripts.pettripfinder.importer.domain_packs.base import UnknownCategoryError
from scripts.pettripfinder.importer.domain_packs.registry import default_registry

# The boolean pet-friendliness field per category (drives no_pets / no
# pet-evidence recommendation logic).
PETS_ALLOWED_FIELD = "pets_allowed"

# Computed once at import time from the registry (which itself matches the
# original literal tuples exactly -- proven by test_domain_packs.py) so any
# caller reading these dicts directly still sees identical shape/content.
ALLOWED_FIELDS_BY_CATEGORY: Dict[str, FrozenSet[str]] = {
    cat: default_registry.for_category(cat).allowed_fields
    for cat in default_registry.category_ids()
}
ALLOWED_FIELD_ORDER: Dict[str, Tuple[str, ...]] = {
    cat: default_registry.for_category(cat).field_order
    for cat in default_registry.category_ids()
}


def allowed_fields(category: str) -> FrozenSet[str]:
    try:
        return default_registry.for_category(category).allowed_fields
    except UnknownCategoryError:
        return frozenset()


def allowed_field_order(category: str) -> Tuple[str, ...]:
    try:
        return default_registry.for_category(category).field_order
    except UnknownCategoryError:
        return ()
