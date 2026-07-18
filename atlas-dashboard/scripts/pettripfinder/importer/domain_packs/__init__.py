"""AES-DATA-003A -- domain-pack foundation: declarative, category-scoped
extraction/normalization/composition metadata, plus a deterministic registry.

This package is a pure-data foundation, not a plugin framework (mission
doctrine): every ``DomainPack`` is a frozen dataclass built from literal
tuples/frozensets, validated at construction, with at most a narrowly
bounded pure-function reference for legacy composition compatibility. No
pack performs I/O, network access, provider calls, dynamic imports, or
global-state mutation.

AES-DATA-003A registers exactly the three categories the importer already
serves (hotels, parks, restaurants) as compatibility descriptors that
reproduce today's behavior byte-for-byte -- no new category, no populated
capability, no live extraction change. See ``base.py`` for the contracts,
``registry.py`` for the registry, ``capabilities.py`` for the (currently
unused) capability taxonomy skeleton, and ``lodging.py``/``parks.py``/
``dining.py`` for the three legacy pack descriptors.
"""

from __future__ import annotations
