"""SEOEngine — (SiteArchitecture, ContentPackage, BusinessSpec) ->
SEOPackage (AES-WEB-001 §5.8 / Part 2).

Internal sequencing label: AES-WEB-002J.5. Compiles titles (Decision D2),
meta descriptions (Decision D1), self-canonical URLs (Decision D3), the
sitemap plan, and a fixed site-level robots plan (Decision D5) from
already-validated artifacts. Structured data is out of scope for this
delivery (Decision D4) -- this module never reads ``BrandPackage`` or
``ComponentManifest`` and never emits JSON-LD, schema types, or any
structured-data field.

Deterministic, pure, serializable, byte-stable: the same
``(SiteArchitecture, ContentPackage, BusinessSpec)`` triple always produces
the same ``SEOPackage`` (or the same batch of diagnostics), regardless of
``ContentPackage.blocks`` input order. No network access, no filesystem
access, no model calls, no randomness, no clock-dependent behavior. Not
wired into pipeline execution -- ``seo_compilation`` remains
``NOT_EXECUTED`` in the ``BuildManifest`` (``PHASE1_EXECUTED_STAGES`` is
unchanged by this module).
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from engines.website_generation.constants.seo import ROBOTS_DIRECTIVES
from engines.website_generation.contracts.artifacts import (
    BusinessSpec,
    ContentPackage,
    PagePlan,
    SEOEntry,
    SEOPackage,
    SiteArchitecture,
    artifact_sha256,
)
from engines.website_generation.contracts.enums import ArtifactKind
from engines.website_generation.contracts.errors import SEOCompilationError
from engines.website_generation.contracts.interfaces import SEOEngineInterface
from engines.website_generation.contracts.versions import (
    ENGINE_VERSIONS,
    SCHEMA_VERSIONS,
)
from engines.website_generation.seo.seo_validators import (
    canonical_length_violation,
    compose_title,
    duplicate_routes,
    index_content_blocks,
    meta_length_violation,
    missing_content_slots,
    role_source_slots,
    title_collisions,
    title_length_violation,
    truncate_meta_description,
    unknown_content_routes,
)

# Fixed diagnostics key order (readability/debugging only -- dict equality
# does not depend on key order). Mirrors content_engine.py's
# _STRUCTURAL_BUCKET_KEYS discipline of a declared, documented order.
_DIAGNOSTIC_BUCKET_ORDER: Tuple[str, ...] = (
    "duplicate_route_records",
    "unknown_routes",
    "unsupported_page_types",
    "missing_content",
    "meta_length_violations",
    "title_length_violations",
    "canonical_length_violations",
    "title_uniqueness_violations",
)


def _ordered(diagnostics: Dict[str, Any]) -> Dict[str, Any]:
    return {key: diagnostics[key] for key in _DIAGNOSTIC_BUCKET_ORDER if key in diagnostics}


class SEOEngine(SEOEngineInterface):
    """Compile a deterministic ``SEOPackage`` from a ``SiteArchitecture``,
    ``ContentPackage``, and ``BusinessSpec``."""

    version = ENGINE_VERSIONS["seo_engine"]

    def compile(
        self,
        site_architecture: SiteArchitecture,
        content_package: ContentPackage,
        business_spec: BusinessSpec,
    ) -> SEOPackage:
        """Total function over structurally valid inputs; batch-fails
        otherwise.

        Deterministic guarantees: none of the three inputs are mutated (all
        are frozen); entry order, title/meta composition, and diagnostics
        are pure functions of ``site_architecture``'s declared page order
        and each page's looked-up content blocks -- never of
        ``content_package.blocks``' input order (AES-WEB-001 §1.1
        replayability contract). Content blocks are looked up by
        ``(page_route, slot_id)``, never by positional order.
        """
        pages = tuple(site_architecture.pages)
        routes = [page.route for page in pages]
        block_index = index_content_blocks(content_package.blocks)

        diagnostics: Dict[str, Any] = {}

        dup_routes = duplicate_routes(routes)
        if dup_routes:
            diagnostics["duplicate_route_records"] = list(dup_routes)

        unknown_routes = unknown_content_routes(content_package.blocks, routes)
        if unknown_routes:
            diagnostics["unknown_routes"] = list(unknown_routes)

        entries, titles_by_route, page_diagnostics = self._resolve_and_compose(
            pages, block_index, business_spec.business_name
        )
        diagnostics.update(page_diagnostics)

        collisions = title_collisions(titles_by_route)
        if collisions:
            diagnostics["title_uniqueness_violations"] = list(collisions)

        if diagnostics:
            raise SEOCompilationError(
                "SEOPackage compilation failed; see diagnostics",
                diagnostics=_ordered(diagnostics),
            )

        return SEOPackage(
            schema_version=SCHEMA_VERSIONS[ArtifactKind.SEO_PACKAGE],
            artifact_kind=ArtifactKind.SEO_PACKAGE,
            source_hashes=self._build_source_hashes(
                site_architecture, content_package, business_spec
            ),
            entries=tuple(sorted(entries, key=lambda entry: entry.route)),
            sitemap_routes=tuple(sorted(site_architecture.sitemap_routes)),
            robots_directives=ROBOTS_DIRECTIVES,
        )

    @staticmethod
    def _resolve_and_compose(
        pages: Tuple[PagePlan, ...],
        block_index: Dict[Tuple[str, str], Any],
        business_name: str,
    ) -> Tuple[List[SEOEntry], Dict[str, str], Dict[str, Any]]:
        """Per-page resolution and composition (D1/D2): role lookup ->
        content-presence check -> title/meta composition -> length checks.

        Each page short-circuits into exactly one of ``unsupported_page_types``
        (no rule-table entry for ``page.page_type``), ``missing_content``
        (a required slot has no block for this route), or a composed
        ``SEOEntry`` plus its own length-violation diagnostics -- never more
        than one of these per page.
        """
        unsupported: List[Dict[str, str]] = []
        missing: List[Dict[str, str]] = []
        meta_violations: List[Dict[str, Any]] = []
        title_violations: List[Dict[str, Any]] = []
        canonical_violations: List[Dict[str, Any]] = []
        entries: List[SEOEntry] = []
        titles_by_route: Dict[str, str] = {}

        for page in pages:
            slots = role_source_slots(page.page_type)
            if slots is None:
                unsupported.append({"route": page.route, "page_type": page.page_type})
                continue
            title_slot, meta_slot = slots

            missing_slots = missing_content_slots(page, title_slot, meta_slot, block_index)
            if missing_slots:
                for slot_id in missing_slots:
                    missing.append({"route": page.route, "slot_id": slot_id})
                continue

            hero_text = block_index[(page.route, title_slot)].text
            intro_text = block_index[(page.route, meta_slot)].text

            meta_violation = meta_length_violation(page.route, intro_text)
            if meta_violation is not None:
                meta_violations.append(meta_violation)

            title = compose_title(hero_text, business_name)
            title_violation = title_length_violation(page.route, title)
            if title_violation is not None:
                title_violations.append(title_violation)

            canonical_violation = canonical_length_violation(page.route)
            if canonical_violation is not None:
                canonical_violations.append(canonical_violation)

            titles_by_route[page.route] = title
            entries.append(
                SEOEntry(
                    route=page.route,
                    title=title,
                    meta_description=truncate_meta_description(intro_text),
                    canonical_url=page.route,
                )
            )

        diagnostics: Dict[str, Any] = {}
        if unsupported:
            diagnostics["unsupported_page_types"] = sorted(
                unsupported, key=lambda item: item["route"]
            )
        if missing:
            diagnostics["missing_content"] = sorted(
                missing, key=lambda item: (item["route"], item["slot_id"])
            )
        if meta_violations:
            diagnostics["meta_length_violations"] = sorted(
                meta_violations, key=lambda item: item["route"]
            )
        if title_violations:
            diagnostics["title_length_violations"] = sorted(
                title_violations, key=lambda item: item["route"]
            )
        if canonical_violations:
            diagnostics["canonical_length_violations"] = sorted(
                canonical_violations, key=lambda item: item["route"]
            )

        return entries, titles_by_route, diagnostics

    @staticmethod
    def _build_source_hashes(
        site_architecture: SiteArchitecture,
        content_package: ContentPackage,
        business_spec: BusinessSpec,
    ) -> Dict[str, str]:
        """Provenance over every input artifact that produced this package
        (§4.1)."""
        return {
            "site_architecture": artifact_sha256(site_architecture),
            "content_package": artifact_sha256(content_package),
            "business_spec": artifact_sha256(business_spec),
        }
