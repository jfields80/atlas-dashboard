"""InformationArchitectureEngine — (BusinessSpec, BrandPackage) ->
SiteArchitecture (AES-WEB-001 §5.3 / Part 2).

Deterministic, pure, serializable, byte-stable: the same
``(BusinessSpec, BrandPackage)`` pair always produces the same
``SiteArchitecture``. No network access, no filesystem access, no model
calls, no randomness, no clock-dependent behavior (§5.3). Not wired into
pipeline execution -- ``ia_planning`` remains ``NOT_EXECUTED`` in the
``BuildManifest`` (``PHASE1_EXECUTED_STAGES`` is unchanged by this module).

Approved page universe (operator decision): exactly one home page plus one
category page per ``BusinessSpec.directory_taxonomy`` entry. Every other
page role, city/geography structure, and inventory-backed page is out of
scope for this delivery -- the current inputs do not support deriving them
(``BusinessSpec.geography`` is a single free-form string; there is no
listing-inventory input), and BusinessSpec/BrandPackage are not modified to
invent one. ``brand`` is carried solely as declared provenance
(``source_hashes``); §5.3 derives structure "from spec taxonomy rules".

This module never selects components, imports the component registry,
chooses recipes, generates content, generates SEO, creates layouts, or
renders anything (§5.3 boundary; AES-WEB-002 §26).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Set, Tuple

from engines.website_generation.constants.ia import (
    CATEGORY_ROUTE_TEMPLATE,
    CONTENT_SLOTS_BY_ROLE,
    HOME_ROUTE,
    PAGE_ROLE_CATEGORY,
    PAGE_ROLE_HOME,
)
from engines.website_generation.contracts.artifacts import (
    BrandPackage,
    BusinessSpec,
    InternalLinkIntent,
    PageHierarchyEntry,
    PagePlan,
    SiteArchitecture,
    artifact_sha256,
    sha256_of_text,
)
from engines.website_generation.contracts.enums import ArtifactKind
from engines.website_generation.contracts.errors import ArchitecturePlanningError
from engines.website_generation.contracts.interfaces import (
    InformationArchitectureEngineInterface,
)
from engines.website_generation.contracts.versions import (
    ENGINE_VERSIONS,
    SCHEMA_VERSIONS,
)

_REQUIRED_SPEC_FIELDS: Tuple[str, ...] = (
    "business_name",
    "niche",
    "audience",
    "value_proposition",
)

_SLUG_DISALLOWED_RUN = re.compile(r"[^a-z0-9]+")


def _normalized(value: str) -> str:
    """Whitespace-normalized scalar text: stripped, inner runs collapsed."""
    return " ".join(str(value).split())


def slugify(text: str) -> str:
    """Deterministic route-slug derivation (AES-WEB-001 §5.3).

    Lower-cases, collapses every run of characters outside ``[a-z0-9]`` to
    a single hyphen, and strips leading/trailing hyphens. A pure function
    of ``text`` only -- no locale, no clock, no randomness. Returns ``""``
    when no derivable slug remains (e.g. punctuation-only text).
    """
    lowered = text.strip().lower()
    return _SLUG_DISALLOWED_RUN.sub("-", lowered).strip("-")


def _category_route(slug: str) -> str:
    return CATEGORY_ROUTE_TEMPLATE % slug


def _stable_page_id(route: str) -> str:
    """Short, deterministic, content-derived page identifier.

    A pure function of ``route`` only -- never a UUID or random value
    (§3.2). Distinct from the route itself while remaining perfectly
    stable across runs and process restarts.
    """
    return "pg_" + sha256_of_text(route)[:16]


class InformationArchitectureEngine(InformationArchitectureEngineInterface):
    """Plan a deterministic ``SiteArchitecture`` from a ``BusinessSpec`` and
    a ``BrandPackage``."""

    version = ENGINE_VERSIONS["information_architecture_engine"]

    def plan(self, spec: BusinessSpec, brand: BrandPackage) -> SiteArchitecture:
        """Total function over valid inputs; batch-fails otherwise.

        Deterministic guarantees: neither input is mutated (both are
        frozen); the page inventory, routes, hierarchy, and link topology
        are pure functions of ``spec.directory_taxonomy`` only.
        """
        self._validate_spec(spec)
        category_routes = self._resolve_category_routes(spec.directory_taxonomy)

        pages = self._build_pages(category_routes)
        hierarchy = self._build_hierarchy(category_routes)
        links = self._build_link_topology(category_routes)
        page_ids = {page.route: _stable_page_id(page.route) for page in pages}

        _validate_site_graph(pages, hierarchy, links, page_ids)

        routes_sorted = tuple(sorted(page.route for page in pages))

        return SiteArchitecture(
            schema_version=SCHEMA_VERSIONS[ArtifactKind.SITE_ARCHITECTURE],
            artifact_kind=ArtifactKind.SITE_ARCHITECTURE,
            source_hashes={
                "business_spec": artifact_sha256(spec),
                "brand_package": artifact_sha256(brand),
            },
            pages=pages,
            nav_routes=routes_sorted,
            sitemap_routes=routes_sorted,
            page_ids=page_ids,
            page_hierarchy=hierarchy,
            internal_link_topology=links,
        )

    @staticmethod
    def _validate_spec(spec: BusinessSpec) -> None:
        """Require non-empty normalized required fields, batch-reported."""
        missing: List[str] = []
        for field_name in _REQUIRED_SPEC_FIELDS:
            if not _normalized(getattr(spec, field_name, "")):
                missing.append(field_name)
        if missing:
            raise ArchitecturePlanningError(
                "SiteArchitecture planning failed; missing required fields: "
                + ", ".join(missing),
                diagnostics={"missing_fields": missing},
            )

    @staticmethod
    def _resolve_category_routes(taxonomy: Tuple[str, ...]) -> Tuple[str, ...]:
        """One deterministic category route per taxonomy entry.

        Batch-reports (never first-failure-only) every taxonomy entry with
        no derivable slug and every collision where two distinct entries
        slugify to the same route.
        """
        slugs_by_entry: Dict[str, str] = {}
        unsluggable: List[str] = []
        for entry in taxonomy:
            slug = slugify(entry)
            if slug:
                slugs_by_entry[entry] = slug
            else:
                unsluggable.append(entry)

        route_to_entries: Dict[str, List[str]] = {}
        for entry, slug in slugs_by_entry.items():
            route_to_entries.setdefault(_category_route(slug), []).append(entry)
        duplicate_routes = {
            route: tuple(sorted(entries))
            for route, entries in route_to_entries.items()
            if len(entries) > 1
        }

        if unsluggable or duplicate_routes:
            diagnostics: Dict[str, Any] = {}
            if unsluggable:
                diagnostics["unsluggable_taxonomy_entries"] = list(unsluggable)
            if duplicate_routes:
                diagnostics["duplicate_routes"] = {
                    route: list(entries)
                    for route, entries in sorted(duplicate_routes.items())
                }
            raise ArchitecturePlanningError(
                "SiteArchitecture planning failed; directory_taxonomy does "
                "not yield unique routes",
                diagnostics=diagnostics,
            )

        return tuple(sorted(route_to_entries))

    @staticmethod
    def _build_pages(category_routes: Tuple[str, ...]) -> Tuple[PagePlan, ...]:
        pages = [
            PagePlan(
                route=HOME_ROUTE,
                page_type=PAGE_ROLE_HOME,
                title="",
                content_slots=CONTENT_SLOTS_BY_ROLE[PAGE_ROLE_HOME],
            )
        ]
        for route in category_routes:
            pages.append(
                PagePlan(
                    route=route,
                    page_type=PAGE_ROLE_CATEGORY,
                    title="",
                    content_slots=CONTENT_SLOTS_BY_ROLE[PAGE_ROLE_CATEGORY],
                )
            )
        return tuple(sorted(pages, key=lambda page: page.route))

    @staticmethod
    def _build_hierarchy(
        category_routes: Tuple[str, ...]
    ) -> Tuple[PageHierarchyEntry, ...]:
        hierarchy = [PageHierarchyEntry(route=HOME_ROUTE, parent_route="")]
        for route in category_routes:
            hierarchy.append(
                PageHierarchyEntry(route=route, parent_route=HOME_ROUTE)
            )
        return tuple(sorted(hierarchy, key=lambda entry: entry.route))

    @staticmethod
    def _build_link_topology(
        category_routes: Tuple[str, ...]
    ) -> Tuple[InternalLinkIntent, ...]:
        # Conservative, hierarchy-derived intent only: home links to every
        # category (discovery), each category links back to home (its
        # parent). No sibling cross-links or numeric floors/ceilings are
        # invented -- that policy belongs to a later phase (AES-WEB-002
        # §6.2), not this delivery.
        links = []
        if category_routes:
            links.append(
                InternalLinkIntent(from_route=HOME_ROUTE, to_routes=category_routes)
            )
        for route in category_routes:
            links.append(
                InternalLinkIntent(from_route=route, to_routes=(HOME_ROUTE,))
            )
        return tuple(sorted(links, key=lambda link: link.from_route))


def _walk_to_root(route: str, parent_by_route: Dict[str, str], max_steps: int) -> str:
    """Follow parent pointers from ``route``.

    Returns ``"ok"`` (the chain reaches a declared root), ``"broken"`` (a
    parent is missing or undeclared), or ``"cycle"`` (the chain fails to
    terminate within ``max_steps`` -- impossible unless it revisits a node,
    since there are at most ``max_steps - 1`` distinct routes to visit).
    """
    current = route
    for _ in range(max_steps + 1):
        if current not in parent_by_route:
            return "broken"
        parent = parent_by_route[current]
        if parent == "":
            return "ok"
        current = parent
    return "cycle"


def _validate_site_graph(
    pages: Tuple[PagePlan, ...],
    hierarchy: Tuple[PageHierarchyEntry, ...],
    links: Tuple[InternalLinkIntent, ...],
    page_ids: Dict[str, str],
) -> None:
    """Structural invariants every SiteArchitecture must satisfy (AES-WEB-001
    §5.3): exactly one root page, no duplicate routes or page ids, no
    cycles, no orphan pages, every non-root page has a valid parent, and
    every internal-link target exists. Batch-reports every violation found
    at once -- never first-failure-only.

    Defense-in-depth: unreachable via valid ``InformationArchitectureEngine
    .plan()`` input (construction always yields a valid two-level tree),
    and independently unit-tested against hand-built broken graphs.
    """
    problems: Dict[str, Any] = {}

    routes = [page.route for page in pages]
    route_set = set(routes)
    if len(route_set) != len(routes):
        seen: Set[str] = set()
        dupes: Set[str] = set()
        for route in routes:
            if route in seen:
                dupes.add(route)
            seen.add(route)
        problems["duplicate_page_routes"] = sorted(dupes)

    id_values = list(page_ids.values())
    if len(set(id_values)) != len(id_values):
        seen_ids: Set[str] = set()
        dupe_ids: Set[str] = set()
        for page_id in id_values:
            if page_id in seen_ids:
                dupe_ids.add(page_id)
            seen_ids.add(page_id)
        problems["duplicate_page_ids"] = sorted(dupe_ids)

    parent_by_route = {entry.route: entry.parent_route for entry in hierarchy}
    roots = sorted(route for route, parent in parent_by_route.items() if parent == "")
    if len(roots) != 1:
        problems["root_count"] = len(roots)

    invalid_parents = sorted(
        entry.route
        for entry in hierarchy
        if entry.parent_route and entry.parent_route not in route_set
    )
    if invalid_parents:
        problems["invalid_parents"] = invalid_parents

    max_steps = len(parent_by_route) + 1
    cyclic: List[str] = []
    orphaned: List[str] = []
    for route in routes:
        status = _walk_to_root(route, parent_by_route, max_steps)
        if status == "cycle":
            cyclic.append(route)
        elif status == "broken":
            orphaned.append(route)
    if cyclic:
        problems["cyclic_pages"] = sorted(set(cyclic))
    if orphaned:
        problems["orphan_pages"] = sorted(set(orphaned))

    invalid_link_sources = sorted(
        {link.from_route for link in links if link.from_route not in route_set}
    )
    invalid_link_targets = sorted(
        {
            target
            for link in links
            for target in link.to_routes
            if target not in route_set
        }
    )
    if invalid_link_sources:
        problems["invalid_link_sources"] = invalid_link_sources
    if invalid_link_targets:
        problems["invalid_link_targets"] = invalid_link_targets

    if problems:
        raise ArchitecturePlanningError(
            "SiteArchitecture failed structural validation",
            diagnostics=problems,
        )
