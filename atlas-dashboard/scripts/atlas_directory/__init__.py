"""Atlas Directory — reusable directory-presentation system.

A niche-agnostic presentation kit for Atlas directory products. It renders a
family of directory pages (homepage, market, corridor/submarket group, category
directory, listing profile, comparison, editorial) from a ``DirectoryConfig``
plus typed view models — with **no** hardcoded market, geography, category, or
domain-field assumptions. PetTripFinder is the first configuration built on it
(see ``scripts/pettripfinder/premium/``); a second directory reuses the same
components by supplying its own config + adapters.

Design rules:
  * Reusable components receive all content and labels through typed view models
    and ``DirectoryConfig`` — never literal niche strings.
  * Geographic grouping terminology is configurable (corridor / neighborhood /
    district / service area / region / …) via ``GeoTerm``.
  * Domain-specific rich content (e.g. a listing's attribute chips, an evidence
    block, editorial prose) is passed in as pre-rendered, pre-escaped HTML
    fragments produced by the niche adapter, so the reusable renderer stays free
    of domain fields while still composing rich pages.
  * Self-contained: system serif/sans stacks, one stylesheet, no framework, no
    external asset, no network.
"""
