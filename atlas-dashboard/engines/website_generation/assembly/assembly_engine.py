"""AssemblyEngine -- (RenderedPageSet, SEOPackage, BrandPackage,
ListingDataset?) -> SiteBundle (AES-WEB-001 §5.9 / Part 2; AES-WEB-002M.1
media-asset mapping).

Internal sequencing label: AES-WEB-002J.10. Produces the complete static
site as a deterministic ``SiteBundle``: injects the ``SEOPackage``'s
per-route metadata (title, meta description, self-canonical URL) and the
shared-stylesheet link into each rendered page's ``<head>`` (preserving the
Renderer's body byte-for-byte), maps every route to a bundle-root-relative
output file, emits ``sitemap.xml``/``robots.txt`` from the SEO artifact, and
computes the bundle-level hash (hash of the sorted file map, §5.9).

Pure, deterministic, serializable, byte-stable, and -- per §5.9 -- **No file
I/O**: the same (RenderedPageSet, SEOPackage, BrandPackage) always produces
the same SiteBundle (or the same batch of diagnostics). No network,
filesystem, CAS, model, randomness, or clock/UUID access. The (future)
``site_bundle_repository`` (§9.3) materializes the bundle to disk; the
assembled text travels inside the returned artifact (SiteBundle schema
1.1.0's ``files``) so a pure engine can hand it off without touching the
filesystem -- the same reasoning J.8 applied to RenderedPageSet. Not wired
into pipeline execution -- ``assembly`` remains ``NOT_EXECUTED`` in the
``BuildManifest`` (``PHASE1_EXECUTED_STAGES`` is unchanged by this module).

Boundary (§5.9, §3.1): Assembly never re-renders body markup, recomputes SEO
decisions (it consumes the SEOPackage verbatim -- no title/meta/canonical is
invented; JSON-LD is absent from the SEO artifact by SEO Decision D4 and is
therefore not injected), selects components, executes quality gates (§5.10),
builds deployment ZIPs (§9.3), or mutates any input. It injects metadata the
SEO Engine already produced, maps files, and emits sitemap/robots -- nothing
more.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from engines.website_generation.constants.build import STAGE_ASSEMBLY
from engines.website_generation.contracts.artifacts import (
    BrandPackage,
    BundleAssetRef,
    BundleFile,
    ListingDataset,
    RenderedPageSet,
    SEOPackage,
    SiteBundle,
    artifact_sha256,
    canonical_json,
    sha256_of_text,
)
from engines.website_generation.contracts.enums import ArtifactKind
from engines.website_generation.contracts.errors import AssemblyError
from engines.website_generation.contracts.interfaces import AssemblyEngineInterface
from engines.website_generation.contracts.versions import ENGINE_VERSIONS, SCHEMA_VERSIONS
from engines.website_generation.assembly.assembly_builders import (
    ROBOTS_FILENAME,
    SHARED_STYLESHEET_FILENAME,
    SITEMAP_FILENAME,
    build_head_additions,
    build_robots,
    build_sitemap,
    collect_media_assets,
    inject_head,
    is_safe_url,
    media_asset_path,
    route_to_output_path,
    stylesheet_href_for,
)

# Fixed diagnostics key order (readability/debugging only -- dict equality
# does not depend on key order), mirroring the seo_engine/renderer
# discipline of a declared, documented order.
_DIAGNOSTIC_BUCKET_ORDER: Tuple[str, ...] = (
    "payload_hash_mismatches",
    "missing_page_html",
    "missing_seo_routes",
    "unknown_seo_routes",
    "invalid_output_paths",
    "unsafe_canonical_urls",
    "head_injection_failures",
    "unsafe_sitemap_urls",
    "invalid_media_assets",
    "duplicate_output_paths",
    "output_path_case_collisions",
)


class AssemblyEngine(AssemblyEngineInterface):
    """Assemble a deterministic ``SiteBundle`` from a ``RenderedPageSet``,
    ``SEOPackage``, and ``BrandPackage`` (AES-WEB-001 §5.9)."""

    version = ENGINE_VERSIONS["assembly"]

    def assemble(
        self,
        rendered_page_set: RenderedPageSet,
        seo_package: SEOPackage,
        brand_package: BrandPackage,
        listing_dataset: Optional[ListingDataset] = None,
    ) -> SiteBundle:
        """Total function over structurally valid inputs; batch-fails
        otherwise (mirrors the RenderError/SEOCompilationError batch
        discipline). No input is mutated (all frozen); file order and
        diagnostics are pure functions of the inputs' declared content --
        never of dict/set iteration order (AES-WEB-001 §1.1). No partial
        ``SiteBundle`` is ever returned when diagnostics exist.

        ``listing_dataset`` (AES-WEB-002M.1, additive, optional): supplied,
        every listing asset explicitly marked ``bundle_allowed`` is mapped
        to its deterministic content-addressed bundle path
        (``assets/media/<sha256>.<ext>``), entered into ``file_map`` (so
        ``bundle_hash`` covers it through the same sorted-file-map hash as
        always), and declared in ``SiteBundle.assets`` -- references only,
        the raw bytes never enter the artifact (§4.3); the
        site_bundle_repository materializes them (§9.3). An authorized
        asset that cannot be mapped (unknown MIME type, malformed hash,
        conflicting declarations) is an ``invalid_media_assets`` batch
        failure -- the operator authorized bundling, so failing to bundle
        must be loud, never silent. Omitted (every pre-M.1 caller), the
        emitted ``file_map``/``bundle_hash`` are byte-identical to pre-M.1
        output.
        """
        diagnostics: Dict[str, List[Any]] = {}

        html_by_route: Dict[str, str] = {
            detail.route: detail.html for detail in rendered_page_set.page_details
        }
        seo_by_route: Dict[str, Any] = {
            entry.route: entry for entry in seo_package.entries
        }
        rendered_routes = {page.route for page in rendered_page_set.pages}

        # Integrity: every declared page hash must match its supplied payload
        # (§14) -- Assembly never silently trusts or repairs a mismatch.
        self._verify_payload_hashes(rendered_page_set, html_by_route, diagnostics)

        # An SEO entry for a route that was never rendered cannot be applied
        # (§11); collect deterministically.
        for route in sorted(seo_by_route):
            if route not in rendered_routes:
                self._add(diagnostics, "unknown_seo_routes", {"route": route})

        assembled: List[Tuple[str, str]] = []  # (output_path, final_html)
        for page in sorted(rendered_page_set.pages, key=lambda p: p.route):
            route = page.route
            html = html_by_route.get(route)
            if html is None:
                self._add(diagnostics, "missing_page_html", {"route": route})
                continue

            seo_entry = seo_by_route.get(route)
            if seo_entry is None:
                self._add(diagnostics, "missing_seo_routes", {"route": route})
                continue

            output_path, path_error = route_to_output_path(route)
            if output_path is None:
                self._add(
                    diagnostics,
                    "invalid_output_paths",
                    {"route": route, "reason": path_error},
                )
                continue

            if seo_entry.canonical_url and not is_safe_url(seo_entry.canonical_url):
                self._add(
                    diagnostics,
                    "unsafe_canonical_urls",
                    {"route": route, "canonical_url": seo_entry.canonical_url},
                )
                continue

            head_additions = build_head_additions(
                title=seo_entry.title,
                meta_description=seo_entry.meta_description,
                canonical_url=seo_entry.canonical_url,
                stylesheet_href=stylesheet_href_for(output_path),
            )
            final_html, head_error = inject_head(html, head_additions)
            if final_html is None:
                self._add(
                    diagnostics,
                    "head_injection_failures",
                    {"route": route, "output_path": output_path, "reason": head_error},
                )
                continue

            assembled.append((output_path, final_html))

        # Site-level files: shared stylesheet, sitemap, robots.
        shared_css = rendered_page_set.shared_css
        site_files: List[Tuple[str, str]] = [
            (SHARED_STYLESHEET_FILENAME, shared_css),
        ]

        unsafe_sitemap = [
            url for url in seo_package.sitemap_routes if not is_safe_url(url)
        ]
        if unsafe_sitemap:
            self._add(
                diagnostics,
                "unsafe_sitemap_urls",
                {"urls": sorted(set(unsafe_sitemap))},
            )
        else:
            site_files.append(
                (SITEMAP_FILENAME, build_sitemap(seo_package.sitemap_routes))
            )
            site_files.append(
                (ROBOTS_FILENAME, build_robots(seo_package.robots_directives))
            )

        bundle_assets = self._map_media_assets(listing_dataset, diagnostics)

        all_files = assembled + site_files
        all_paths = [path for path, _content in all_files] + [
            asset.path for asset in bundle_assets
        ]
        self._check_path_conflicts(all_paths, diagnostics)

        if diagnostics:
            raise AssemblyError(
                "SiteBundle assembly failed; see diagnostics",
                stage=STAGE_ASSEMBLY,
                diagnostics=self._ordered(diagnostics),
            )

        return self._build_bundle(
            all_files, bundle_assets,
            rendered_page_set, seo_package, brand_package, listing_dataset,
        )

    # -- integrity ---------------------------------------------------------

    def _verify_payload_hashes(
        self,
        rendered_page_set: RenderedPageSet,
        html_by_route: Dict[str, str],
        diagnostics: Dict[str, List[Any]],
    ) -> None:
        for page in sorted(rendered_page_set.pages, key=lambda p: p.route):
            html = html_by_route.get(page.route)
            if html is None:
                continue  # reported as missing_page_html in the main walk
            actual = sha256_of_text(html)
            if page.html_hash and page.html_hash != actual:
                self._add(
                    diagnostics,
                    "payload_hash_mismatches",
                    {
                        "route": page.route,
                        "declared": page.html_hash,
                        "actual": actual,
                        "kind": "page_html",
                    },
                )
        css_hash = rendered_page_set.shared_css_hash
        if css_hash and css_hash != sha256_of_text(rendered_page_set.shared_css):
            self._add(
                diagnostics,
                "payload_hash_mismatches",
                {
                    "declared": css_hash,
                    "actual": sha256_of_text(rendered_page_set.shared_css),
                    "kind": "shared_css",
                },
            )

    def _map_media_assets(
        self,
        listing_dataset: Optional[ListingDataset],
        diagnostics: Dict[str, List[Any]],
    ) -> List[BundleAssetRef]:
        """Map every bundle-authorized listing asset to its deterministic
        content-addressed bundle entry (AES-WEB-002M.1). Pure -- derives
        paths from (hash, MIME) declarations only; never reads bytes (the
        Assembly Engine has no CAS access, §5.9). Fail-closed both ways:
        an *unauthorized* asset (``bundle_allowed=False``) is skipped --
        the licensing default is refusal -- while an *authorized* asset
        that cannot be mapped is a batch failure, never a silent drop."""
        if listing_dataset is None:
            return []
        pairs, issues = collect_media_assets(listing_dataset)
        for issue in issues:
            self._add(diagnostics, "invalid_media_assets", {"reason": issue})
        bundle_assets: List[BundleAssetRef] = []
        for asset_hash, mime_type in pairs:
            path, error = media_asset_path(asset_hash, mime_type)
            if path is None:
                self._add(
                    diagnostics,
                    "invalid_media_assets",
                    {
                        "asset_hash": asset_hash,
                        "mime_type": mime_type,
                        "reason": error,
                    },
                )
                continue
            bundle_assets.append(
                BundleAssetRef(
                    path=path, asset_hash=asset_hash, mime_type=mime_type
                )
            )
        return bundle_assets

    @staticmethod
    def _check_path_conflicts(
        paths: List[str], diagnostics: Dict[str, List[Any]]
    ) -> None:
        seen: Dict[str, int] = {}
        seen_lower: Dict[str, str] = {}
        duplicates: List[str] = []
        collisions: List[Dict[str, str]] = []
        for path in paths:
            seen[path] = seen.get(path, 0) + 1
            lower = path.lower()
            if lower in seen_lower and seen_lower[lower] != path:
                collisions.append({"a": seen_lower[lower], "b": path})
            seen_lower.setdefault(lower, path)
        duplicates = sorted(p for p, n in seen.items() if n > 1)
        if duplicates:
            diagnostics.setdefault("duplicate_output_paths", [])
            diagnostics["duplicate_output_paths"].extend(
                {"path": p} for p in duplicates
            )
        if collisions:
            diagnostics.setdefault("output_path_case_collisions", [])
            diagnostics["output_path_case_collisions"].extend(
                sorted(collisions, key=lambda c: (c["a"], c["b"]))
            )

    # -- bundle assembly ---------------------------------------------------

    @staticmethod
    def _build_bundle(
        files: List[Tuple[str, str]],
        bundle_assets: List[BundleAssetRef],
        rendered_page_set: RenderedPageSet,
        seo_package: SEOPackage,
        brand_package: BrandPackage,
        listing_dataset: Optional[ListingDataset],
    ) -> SiteBundle:
        ordered = sorted(files, key=lambda item: item[0])
        file_map: Dict[str, str] = {
            path: sha256_of_text(content) for path, content in ordered
        }
        # AES-WEB-002M.1: binary asset entries join the same path -> content-
        # hash map (their file_map value is the asset's own CAS hash --
        # sha256-of-raw-bytes and sha256-of-UTF-8-text are one convention),
        # so §5.9's sorted-file-map bundle hash covers them unchanged.
        for asset in bundle_assets:
            file_map[asset.path] = asset.asset_hash
        bundle_files = tuple(
            BundleFile(path=path, content=content) for path, content in ordered
        )
        # §5.9: the bundle-level hash is the hash of the sorted file map.
        bundle_hash = sha256_of_text(canonical_json(file_map))
        source_hashes = {
            "rendered_page_set": artifact_sha256(rendered_page_set),
            "seo_package": artifact_sha256(seo_package),
            "brand_package": artifact_sha256(brand_package),
        }
        if listing_dataset is not None:
            source_hashes["listing_dataset"] = artifact_sha256(listing_dataset)
        return SiteBundle(
            schema_version=SCHEMA_VERSIONS[ArtifactKind.SITE_BUNDLE],
            artifact_kind=ArtifactKind.SITE_BUNDLE,
            source_hashes=source_hashes,
            file_map=file_map,
            bundle_hash=bundle_hash,
            files=bundle_files,
            assets=tuple(sorted(bundle_assets, key=lambda a: a.path)),
        )

    # -- diagnostics helpers ------------------------------------------------

    @staticmethod
    def _add(
        diagnostics: Dict[str, List[Any]], bucket: str, entry: Any
    ) -> None:
        diagnostics.setdefault(bucket, [])
        diagnostics[bucket].append(entry)

    @staticmethod
    def _ordered(diagnostics: Dict[str, List[Any]]) -> Dict[str, List[Any]]:
        return {
            key: diagnostics[key]
            for key in _DIAGNOSTIC_BUCKET_ORDER
            if key in diagnostics
        }
