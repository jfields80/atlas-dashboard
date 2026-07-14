"""InformationArchitectureEngine — (BusinessSpec, BrandPackage) ->
SiteArchitecture (AES-WEB-001 §5.3 / Part 2).

Deterministic, pure, serializable, byte-stable: the same
``(BusinessSpec, BrandPackage)`` pair always produces the same
``SiteArchitecture``. No network access, no filesystem access, no model
calls, no randomness, no clock-dependent behavior (§5.3). Not wired into
pipeline execution -- ``ia_planning`` remains ``NOT_EXECUTED`` in the
``BuildManifest`` (``PHASE1_EXECUTED_STAGES`` is unchanged by this module).

Approved page universe (operator decision, extended by AES-WEB-002K.1):
exactly one home page plus one category page per
``BusinessSpec.directory_taxonomy`` entry, plus (K.1, additive) one
``business-profile`` page per ``ListingRecord`` when an optional
``listing_dataset`` is supplied. City/geography structure and every other
page role remain out of scope for this delivery (``BusinessSpec.geography``
is a single free-form string), and BusinessSpec/BrandPackage are not
modified to invent one. ``brand`` is carried solely as declared provenance
(``source_hashes``); §5.3 derives structure "from spec taxonomy rules".
Profile routes follow the ADR-WEB-LISTING-DATASET §6 convention exactly
(``/<category-slug>/<listing-slug>/``) and are excluded from ``nav_routes``
(site-wide navigation names category routes only, never every business) but
included in ``sitemap_routes`` and the page graph (hierarchy/link topology)
like any other page.

Home and category page titles are now always real (AES-WEB-002K.1) --
``spec.business_name`` for home, the taxonomy entry's own text for each
category -- never ``""``. This is an intentional, always-on behavior change
(regardless of whether ``listing_dataset`` is supplied): real navigation
labels require real page titles, and IA is the only stage that has both
the taxonomy entry text and the business name in hand.

This module never selects components, imports the component registry,
chooses recipes, generates content, generates SEO, creates layouts, or
renders anything (§5.3 boundary; AES-WEB-002 §26). It also never imports
``components/`` (the K.1 render-data/route-derivation helpers there are
off limits) -- ``_listing_route``/``_category_route`` below are a small,
documented duplication of ``components.content_projection``'s identical
route grammar, the same "contracts/rendering has no legal cross-import"
precedent this repository already applies to ``is_safe_url``.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from engines.website_generation.constants.ia import (
    CATEGORY_ROUTE_TEMPLATE,
    CONTENT_SLOTS_BY_ROLE,
    HOME_ROUTE,
    PAGE_ROLE_CATEGORY,
    PAGE_ROLE_EDITORIAL_GUIDE,
    PAGE_ROLE_HOME,
)
from engines.website_generation.contracts.artifacts import (
    BrandPackage,
    BusinessSpec,
    InternalLinkIntent,
    ListingDataset,
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

# AES-WEB-002K.1: local, not imported from constants/ia.py (that table
# governs only the home/category recipe families this module already knew
# about) -- profile pages carry no content_slots (matching every existing
# business-profile PagePlan fixture precedent; the Component Engine's
# recipe resolution keys purely off page_type, never PagePlan.content_slots).
PAGE_ROLE_BUSINESS_PROFILE = "business-profile"

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


def _listing_route(category_slug: str, listing_slug: str) -> str:
    """Same grammar as ``components.content_projection.listing_route``
    (documented duplication -- see module docstring): ``ia/`` has no legal
    import path to ``components/``."""
    return "%s%s/" % (_category_route(category_slug), listing_slug)


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

    def plan(
        self,
        spec: BusinessSpec,
        brand: BrandPackage,
        listing_dataset: Optional[ListingDataset] = None,
        editorial_pages: Tuple[Tuple[str, str], ...] = (),
    ) -> SiteArchitecture:
        """Total function over valid inputs; batch-fails otherwise.

        Deterministic guarantees: neither input is mutated (all three are
        frozen); the page inventory, routes, hierarchy, and link topology
        are pure functions of ``spec.directory_taxonomy``, the optional
        ``listing_dataset``'s categories/listings, and the optional
        ``editorial_pages`` only.

        ``editorial_pages`` (PILOT-PTF-1, additive, empty-by-default):
        explicit ``(route, title)`` pairs for static/trust pages (about,
        methodology, contact) -- these carry no taxonomy or listing source,
        so, unlike category/profile routes, IA does not derive them; the
        caller supplies the exact route and a real, non-empty title. Each
        becomes a real ``PageRole.EDITORIAL_GUIDE`` page: in the page graph,
        in ``sitemap_routes``, and in ``nav_routes`` (footer-eligible, per
        the Component Engine's render-data navigation split) -- never a
        second, bespoke page-role string (AES-WEB-002 §6.1's eighteen-role
        taxonomy already names this role; see constants/ia.py's
        ``PAGE_ROLE_EDITORIAL_GUIDE`` docstring).
        """
        self._validate_spec(spec)
        category_pairs = self._resolve_category_routes(spec.directory_taxonomy)
        category_routes = tuple(route for route, _title in category_pairs)
        profile_triples = self._resolve_profile_routes(listing_dataset)
        editorial_pairs = self._resolve_editorial_pages(editorial_pages)
        editorial_routes = tuple(route for route, _title in editorial_pairs)

        home_title = _normalized(spec.business_name)
        pages = self._build_pages(category_pairs, home_title, profile_triples, editorial_pairs)
        hierarchy = self._build_hierarchy(category_routes, profile_triples, editorial_routes)
        links = self._build_link_topology(category_routes, profile_triples)
        page_ids = {page.route: _stable_page_id(page.route) for page in pages}

        _validate_site_graph(pages, hierarchy, links, page_ids)

        # AES-WEB-002K.1: profile routes are real pages (sitemap-crawlable,
        # part of the page graph) but never site-wide navigation entries --
        # a directory with hundreds of listings must not explode its header
        # nav to one link per business.
        sitemap_routes_sorted = tuple(sorted(page.route for page in pages))
        nav_routes_sorted = tuple(sorted(
            page.route for page in pages
            if page.page_type != PAGE_ROLE_BUSINESS_PROFILE
        ))

        source_hashes = {
            "business_spec": artifact_sha256(spec),
            "brand_package": artifact_sha256(brand),
        }
        if listing_dataset is not None:
            source_hashes["listing_dataset"] = artifact_sha256(listing_dataset)

        return SiteArchitecture(
            schema_version=SCHEMA_VERSIONS[ArtifactKind.SITE_ARCHITECTURE],
            artifact_kind=ArtifactKind.SITE_ARCHITECTURE,
            source_hashes=source_hashes,
            pages=pages,
            nav_routes=nav_routes_sorted,
            sitemap_routes=sitemap_routes_sorted,
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
    def _resolve_category_routes(taxonomy: Tuple[str, ...]) -> Tuple[Tuple[str, str], ...]:
        """One deterministic ``(route, title)`` pair per taxonomy entry --
        ``title`` is the entry's own (whitespace-normalized) text, never a
        route-derived guess (AES-WEB-002K.1: real navigation labels need
        real titles).

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

        return tuple(sorted(
            (route, _normalized(entries[0])) for route, entries in route_to_entries.items()
        ))

    @staticmethod
    def _resolve_profile_routes(
        listing_dataset: Optional[ListingDataset],
    ) -> Tuple[Tuple[str, str, str], ...]:
        """One ``(route, title, parent_category_route)`` triple per
        ``ListingRecord`` (ADR-WEB-LISTING-DATASET §6 route convention;
        AES-WEB-002K.1) -- empty when no dataset is supplied, byte-identical
        to pre-K.1 behavior in that case. ``title`` is the listing's own
        ``business_name``, never a route-derived guess. Batch-reports every
        listing whose ``category_id`` does not resolve to a real
        ``ListingCategory``; duplicate-route collisions across listings
        surface via the existing ``_validate_site_graph`` page-level check
        below (no need to re-derive that logic here)."""
        if listing_dataset is None:
            return ()
        categories_by_id = {c.category_id: c for c in listing_dataset.categories}
        unresolved: List[str] = []
        triples: List[Tuple[str, str, str]] = []
        for listing in listing_dataset.listings:
            category = categories_by_id.get(listing.category_id)
            if category is None:
                unresolved.append(listing.listing_id)
                continue
            parent_route = _category_route(category.slug)
            route = _listing_route(category.slug, listing.slug)
            triples.append((route, _normalized(listing.business_name), parent_route))

        if unresolved:
            raise ArchitecturePlanningError(
                "SiteArchitecture planning failed; listing_dataset has "
                "unresolvable category references",
                diagnostics={"unresolved_listing_category_refs": sorted(unresolved)},
            )

        return tuple(sorted(triples))

    @staticmethod
    def _resolve_editorial_pages(
        editorial_pages: Tuple[Tuple[str, str], ...],
    ) -> Tuple[Tuple[str, str], ...]:
        """Validate and normalize the caller-supplied ``(route, title)``
        pairs for static/trust pages. Batch-reports every malformed route
        (must be ``"/segment/"`` shaped -- leading and trailing slash, one
        or more non-slash characters) and every blank title; duplicate
        routes among ``editorial_pages`` are caught here (a clearer,
        editorial-specific message) rather than deferred to the generic
        cross-role ``_validate_site_graph`` duplicate check."""
        malformed: List[str] = []
        blank_titles: List[str] = []
        seen_routes: Set[str] = set()
        duplicates: Set[str] = set()
        resolved: List[Tuple[str, str]] = []
        for route, title in editorial_pages:
            if not re.match(r"^/[a-z0-9-]+/$", route):
                malformed.append(route)
                continue
            normalized_title = _normalized(title)
            if not normalized_title:
                blank_titles.append(route)
                continue
            if route in seen_routes:
                duplicates.add(route)
                continue
            seen_routes.add(route)
            resolved.append((route, normalized_title))

        if malformed or blank_titles or duplicates:
            diagnostics: Dict[str, Any] = {}
            if malformed:
                diagnostics["malformed_editorial_routes"] = sorted(malformed)
            if blank_titles:
                diagnostics["blank_editorial_titles"] = sorted(blank_titles)
            if duplicates:
                diagnostics["duplicate_editorial_routes"] = sorted(duplicates)
            raise ArchitecturePlanningError(
                "SiteArchitecture planning failed; editorial_pages is invalid",
                diagnostics=diagnostics,
            )
        return tuple(sorted(resolved))

    @staticmethod
    def _build_pages(
        category_pairs: Tuple[Tuple[str, str], ...],
        home_title: str,
        profile_triples: Tuple[Tuple[str, str, str], ...],
        editorial_pairs: Tuple[Tuple[str, str], ...] = (),
    ) -> Tuple[PagePlan, ...]:
        pages = [
            PagePlan(
                route=HOME_ROUTE,
                page_type=PAGE_ROLE_HOME,
                title=home_title,
                content_slots=CONTENT_SLOTS_BY_ROLE[PAGE_ROLE_HOME],
            )
        ]
        for route, title in category_pairs:
            pages.append(
                PagePlan(
                    route=route,
                    page_type=PAGE_ROLE_CATEGORY,
                    title=title,
                    content_slots=CONTENT_SLOTS_BY_ROLE[PAGE_ROLE_CATEGORY],
                )
            )
        for route, title, _parent_route in profile_triples:
            pages.append(
                PagePlan(route=route, page_type=PAGE_ROLE_BUSINESS_PROFILE, title=title)
            )
        for route, title in editorial_pairs:
            pages.append(
                PagePlan(
                    route=route,
                    page_type=PAGE_ROLE_EDITORIAL_GUIDE,
                    title=title,
                    content_slots=CONTENT_SLOTS_BY_ROLE[PAGE_ROLE_EDITORIAL_GUIDE],
                )
            )
        return tuple(sorted(pages, key=lambda page: page.route))

    @staticmethod
    def _build_hierarchy(
        category_routes: Tuple[str, ...],
        profile_triples: Tuple[Tuple[str, str, str], ...],
        editorial_routes: Tuple[str, ...] = (),
    ) -> Tuple[PageHierarchyEntry, ...]:
        hierarchy = [PageHierarchyEntry(route=HOME_ROUTE, parent_route="")]
        for route in category_routes:
            hierarchy.append(
                PageHierarchyEntry(route=route, parent_route=HOME_ROUTE)
            )
        for route, _title, parent_route in profile_triples:
            hierarchy.append(PageHierarchyEntry(route=route, parent_route=parent_route))
        for route in editorial_routes:
            # Editorial/trust pages hang directly off home, like categories
            # -- there is no taxonomy parent for "about"/"methodology".
            hierarchy.append(PageHierarchyEntry(route=route, parent_route=HOME_ROUTE))
        return tuple(sorted(hierarchy, key=lambda entry: entry.route))

    @staticmethod
    def _build_link_topology(
        category_routes: Tuple[str, ...],
        profile_triples: Tuple[Tuple[str, str, str], ...],
    ) -> Tuple[InternalLinkIntent, ...]:
        # Conservative, hierarchy-derived intent only: home links to every
        # category (discovery), each category links back to home (its
        # parent) plus (AES-WEB-002K.1, additive) every one of its own
        # profile pages when a listing_dataset was supplied. No sibling
        # cross-links or numeric floors/ceilings are invented -- that
        # policy belongs to a later phase (AES-WEB-002 §6.2), not this
        # delivery.
        profiles_by_parent: Dict[str, List[str]] = {}
        for route, _title, parent_route in profile_triples:
            profiles_by_parent.setdefault(parent_route, []).append(route)

        links = []
        if category_routes:
            links.append(
                InternalLinkIntent(from_route=HOME_ROUTE, to_routes=category_routes)
            )
        for route in category_routes:
            to_routes = (HOME_ROUTE,) + tuple(sorted(profiles_by_parent.get(route, ())))
            links.append(InternalLinkIntent(from_route=route, to_routes=to_routes))
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
