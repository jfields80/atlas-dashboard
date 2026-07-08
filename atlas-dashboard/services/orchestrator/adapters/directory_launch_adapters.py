"""
atlas/services/orchestrator/adapters/directory_launch_adapters.py

Thin stage-handler adapters wiring the "directory_launch_v1" pipeline
(AES-006 Phase 2) through the generalized orchestrator framework
(AES-006 Phase 1).

Each function below is marshaling only — it translates between the
orchestrator's generic context dict and the real, already-implemented
service/engine contracts. No scoring, decision, or business logic is
introduced here; every substantive computation still happens inside
the existing services this module calls.

Known, deliberate approximations (documented, not hidden):

  * ``OpportunityInput`` requires ``description``, ``target_customer``,
    ``competition_level``, and ``monetization_signals`` — none of
    these exist in ``opportunity_records`` or in ``DecisionResult`` /
    ``PortfolioDecisionResult``. Per explicit product decision, the
    caller must supply them via the pipeline's ``opportunity_extra``
    seed key; ``blueprint_stage`` raises rather than fabricating
    defaults.
  * The Blueprint engine's ``location_hierarchy`` output
    (``levels``/``example_paths``) has no real tree structure to
    translate into the ingestion engine's ``LocationNode`` tree. Per
    explicit product decision, ``location_hierarchy=()`` is passed to
    ``BlueprintInput`` for this pipeline version. Revisit once the
    Blueprint engine produces an actual structured location tree.
  * The v3 committee's decision vocabulary (BUILD/TEST/DEFER/REJECT)
    does not line up 1:1 with the Blueprint engine's own
    ``CommitteeRecommendation`` enum (BUILD/TEST/WATCH/PASS). DEFER is
    mapped to WATCH ("wait and see") and REJECT to PASS ("pass on
    this opportunity") — a lexical best-fit, irrelevant to the
    eligibility gate itself since only BUILD/TEST are ever actionable.
  * Ingestion's ``SeedPackage.businesses`` (``NormalizedListing``, with
    ``TaggedValue``-wrapped fields and a *tuple* of categories) and the
    Launch Kit engine's ``seed_businesses.json`` extractor (flat,
    plain-string ``name``/``category``/``city``/``state``) are
    genuinely different shapes. Per explicit product decision:
      - a listing's first category (ingestion's own deterministic
        order — never alphabetized or otherwise re-ranked) becomes the
        single ``category`` string; a listing with zero categories is
        skipped and recorded in ``launch_kit_result["warnings"]``.
      - a listing whose ``city`` or ``state`` is tagged
        ``Provenance.UNKNOWN`` is skipped entirely (also warned) rather
        than writing a blank string that would look like real, if
        empty, data.
    Future Atlas versions should evolve the Launch Kit engine to accept
    multiple categories per listing rather than collapsing them here.
  * The Launch Kit engine's URL-map extractor (both its explicit-
    blueprint and generated-fallback code paths) always emits a
    ``url`` CSV column, but Directory Builder's ``UrlMapEntry`` model
    requires ``path``. Also a latent shape mismatch between two
    already-completed subsystems — there is no seed-data shaping that
    changes this hardcoded key name, so it is fixed at the file level:
    ``_patch_url_map_csv_column`` renames the column in the exported
    ``url_map.csv`` after the Launch Kit engine writes it, rather than
    editing the frozen engine itself.
  * Only the Blueprint's ``project_profile`` fields are wired through
    to the Launch Kit engine for this pipeline version — the richer
    SEO/content-strategy/monetization/roadmap/risk sections are not
    mapped in Phase 2 scope, so the resulting launch kit's SEO, content,
    monetization, and AI-task files are intentionally minimal (empty
    where the engine finds no corresponding seed data). Wiring those
    sections through is a larger, separate mapping effort.
  * The Launch Kit engine's own ``locations.json`` deriver (used when
    no explicit ``locations`` are supplied in the seed package) writes
    each entry keyed by ``name``, but the Directory Builder's
    ``LocationDef`` model requires ``city`` — a latent shape mismatch
    between two already-completed subsystems, invisible until they are
    actually chained together as this pipeline does. Rather than patch
    either frozen engine, the adapter supplies explicit location
    entries (unique city/state pairs already present on the flattened
    listings, keyed correctly as ``city``) so the Launch Kit engine's
    buggy derivation path is never triggered.
"""

from __future__ import annotations

import csv
import re
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from engines.directory_blueprint.blueprint_models import (
    BlueprintRequest,
    CommitteeInput,
    CommitteeRecommendation,
    CompetitionLevel,
    DirectoryBlueprint,
    GeographicScope,
    OpportunityInput,
)
from engines.directory_builder.models import BuildResult
from engines.preview.preview_models import PreviewBuild
from engines.directory_ingestion.ingestion_models import (
    BlueprintInput,
    CategoryNode as IngestionCategoryNode,
    Provenance,
    RawListing,
    SeedPackage,
    SourceType,
)
from repositories.directory_builder.launch_package_repository import LaunchPackageRepository
from repositories.directory_builder.project_assembly_repository import ProjectAssemblyRepository
from repositories.directory_ingestion_repository import DirectoryIngestionRepository
from services import directory_blueprint_service
from services.directory_builder_service import DirectoryBuilderService
from services.directory_ingestion_service import DirectoryIngestionService, IngestionResult
from services.investment_committee import PortfolioDecisionResult
from services.launch_kit_service import LaunchKitService
from services.preview_service import PreviewService

_COMMITTEE_RECOMMENDATION_MAP: dict[str, CommitteeRecommendation] = {
    "BUILD": CommitteeRecommendation.BUILD,
    "TEST": CommitteeRecommendation.TEST,
    "DEFER": CommitteeRecommendation.WATCH,
    "REJECT": CommitteeRecommendation.PASS,
}

_REQUIRED_OPPORTUNITY_EXTRA_KEYS = (
    "description",
    "target_customer",
    "competition_level",
    "monetization_signals",
)


class DirectoryLaunchAdapterError(ValueError):
    """Raised when a Directory Launch stage adapter receives unusable input."""


# ---------------------------------------------------------------------------
# Stage 1: blueprint
# ---------------------------------------------------------------------------

def blueprint_stage(
    conn: sqlite3.Connection,
    committee_decision: PortfolioDecisionResult,
    opportunity_extra: Mapping[str, Any],
) -> DirectoryBlueprint:
    """
    Builds a ``BlueprintRequest`` from the committee decision plus the
    caller-supplied ``opportunity_extra`` fields, then generates and
    persists a ``DirectoryBlueprint`` via the existing blueprint
    service. Halts the pipeline (raises) if the committee decision is
    not blueprint-eligible (i.e. not BUILD/TEST).
    """
    missing = [key for key in _REQUIRED_OPPORTUNITY_EXTRA_KEYS if key not in opportunity_extra]
    if missing:
        raise DirectoryLaunchAdapterError(
            f"opportunity_extra is missing required keys: {missing}"
        )

    core = committee_decision.core_decision

    opportunity = OpportunityInput(
        name=core.niche_slug,
        niche=core.niche_slug,
        description=opportunity_extra["description"],
        score=core.score_breakdown.total_score,
        confidence=core.confidence,
        geographic_scope=GeographicScope(core.geographic_scope.upper()),
        primary_market=core.geographic_scope,
        target_customer=opportunity_extra["target_customer"],
        competition_level=CompetitionLevel(opportunity_extra["competition_level"].upper()),
        monetization_signals=list(opportunity_extra["monetization_signals"]),
    )

    recommendation = _COMMITTEE_RECOMMENDATION_MAP.get(committee_decision.portfolio_recommendation)
    if recommendation is None:
        raise DirectoryLaunchAdapterError(
            f"Unrecognized portfolio_recommendation: "
            f"{committee_decision.portfolio_recommendation!r}"
        )

    committee = CommitteeInput(
        recommendation=recommendation,
        confidence=committee_decision.portfolio_confidence,
        rationale=committee_decision.committee_rationale,
    )

    request = BlueprintRequest(opportunity=opportunity, committee=committee)
    result = directory_blueprint_service.generate_and_store_blueprint(conn, request)

    if result.status == directory_blueprint_service.RESULT_NOT_ELIGIBLE:
        raise DirectoryLaunchAdapterError(
            f"Directory Launch pipeline halted at blueprint stage: {result.reason}"
        )

    return result.blueprint


# ---------------------------------------------------------------------------
# Stage 2: ingestion
# ---------------------------------------------------------------------------

def _flatten_category_tree(
    nodes: list, parent_slug: str | None = None
) -> list[IngestionCategoryNode]:
    """
    Mechanically flattens the Blueprint engine's recursive category
    tree (``name``, ``slug``, ``subcategories``) into the ingestion
    engine's flat ``CategoryNode`` shape (``slug``, ``name``,
    ``parent_slug``). Pure structural translation — no new hierarchy
    logic is introduced.
    """
    flat: list[IngestionCategoryNode] = []
    for node in nodes:
        flat.append(IngestionCategoryNode(slug=node.slug, name=node.name, parent_slug=parent_slug))
        flat.extend(_flatten_category_tree(node.subcategories, parent_slug=node.slug))
    return flat


def _blueprint_to_ingestion_input(blueprint: DirectoryBlueprint) -> BlueprintInput:
    return BlueprintInput(
        directory_slug=blueprint.project_profile.project_slug,
        directory_name=blueprint.project_profile.project_name,
        category_hierarchy=tuple(
            _flatten_category_tree(blueprint.directory_architecture.category_tree)
        ),
        location_hierarchy=(),
        profile_schema_fields=tuple(
            field.name for field in blueprint.business_profile_schema.fields
        ),
    )


def _raw_listings_from_business_rows(rows: list[Mapping[str, Any]]) -> list[RawListing]:
    """
    Maps rows shaped like ``services.database.Database.get_businesses_detailed()``
    into the ingestion engine's ``RawListing`` contract.
    """
    listings: list[RawListing] = []
    for row in rows:
        payload = tuple(
            sorted((str(key), "" if value is None else str(value)) for key, value in row.items())
        )
        listings.append(
            RawListing(
                raw_id=str(row["id"]),
                source_type=SourceType.USER_SUBMITTED,
                source_name="atlas_businesses_table",
                source_url=row.get("website"),
                payload=payload,
            )
        )
    return listings


def ingestion_stage(
    conn: sqlite3.Connection,
    blueprint: DirectoryBlueprint,
    raw_listings: list[Mapping[str, Any]],
) -> IngestionResult:
    """Runs the Directory Ingestion engine against ``blueprint`` and ``raw_listings``."""
    repository = DirectoryIngestionRepository(conn)
    repository.ensure_schema()

    service = DirectoryIngestionService(repository)
    blueprint_input = _blueprint_to_ingestion_input(blueprint)
    listings = _raw_listings_from_business_rows(raw_listings)

    return service.run_ingestion(blueprint_input, listings)


# ---------------------------------------------------------------------------
# Stage 3: launch kit
# ---------------------------------------------------------------------------

def _blueprint_to_launch_kit_dict(blueprint: DirectoryBlueprint) -> dict[str, Any]:
    """
    Flattens the Blueprint engine's rich, nested ``DirectoryBlueprint``
    into the flat shape the Directory Builder's own ``Blueprint`` model
    requires (``project_name``, ``project_slug``, ``niche``, ``domain``,
    ``description``, ``target_audience``).

    This mapping is necessary, not cosmetic: ``LaunchPackageRepository.
    load()`` parses ``blueprint.json`` straight into that flat model, and
    ``DirectoryBlueprint`` nests everything under ``project_profile``
    instead. Only fields with a genuine 1:1 source are populated
    (``target_audience`` <- ``target_customer``); ``description`` has no
    natural source in ``DirectoryBlueprint`` and is left blank rather
    than repurposing an unrelated field.
    """
    profile = blueprint.project_profile
    return {
        "project_name": profile.project_name,
        "project_slug": profile.project_slug,
        "niche": profile.business_type,
        "domain": profile.suggested_domains[0] if profile.suggested_domains else "",
        "description": "",
        "target_audience": profile.target_customer,
    }


def _seed_package_to_launch_kit_listings(package: SeedPackage) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Flattens ``SeedPackage.businesses`` (``NormalizedListing``, with
    ``TaggedValue``-wrapped fields and a tuple of categories) into the
    flat, plain-string listing dicts the Launch Kit engine's
    ``seed_businesses.json`` extractor expects.

    Per explicit product decision:
      - Uses the listing's first category exactly as ingestion produced
        it (no alphabetizing, no "best category" inference). A listing
        with zero categories is skipped and warned about.
      - A listing whose ``city`` or ``state`` is tagged
        ``Provenance.UNKNOWN`` is skipped and warned about, rather than
        writing an empty string that would misrepresent honest-unknown
        data as a real, if blank, value.
    """
    listings: list[dict[str, Any]] = []
    warnings: list[str] = []

    for business in package.businesses:
        if not business.categories:
            warnings.append(
                f"Skipped listing {business.listing_id!r}: no categories assigned."
            )
            continue

        if business.city.provenance == Provenance.UNKNOWN or business.state.provenance == Provenance.UNKNOWN:
            warnings.append(
                f"Skipped listing {business.listing_id!r}: city or state is unknown."
            )
            continue

        listings.append(
            {
                "name": business.business_name,
                "category": business.categories[0],
                "city": business.city.value,
                "state": business.state.value,
                "website": business.website.value or "",
                "phone": business.phone.value or "",
            }
        )

    return listings, warnings


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _unique_locations_from_listings(listings: list[dict[str, Any]]) -> list[dict[str, str]]:
    """
    Builds explicit ``city``-keyed location entries from the already
    honest-vetted (non-UNKNOWN) city/state values on ``listings``, so
    the Launch Kit engine's own ``name``-keyed derivation path — which
    is incompatible with Directory Builder's ``LocationDef`` model —
    is never triggered (see module docstring).
    """
    seen: set[tuple[str, str]] = set()
    locations: list[dict[str, str]] = []
    for listing in listings:
        pair = (listing["city"], listing["state"])
        if pair in seen:
            continue
        seen.add(pair)
        city, state = pair
        locations.append(
            {
                "city": city,
                "state": state,
                "slug": _slugify(f"{city}-{state}" if state else city),
            }
        )
    return locations


def launch_kit_stage(
    blueprint: DirectoryBlueprint,
    ingestion_result: IngestionResult,
    project_slug: str,
    launch_kit_output_root: str,
) -> dict[str, Any]:
    """
    Generates and exports a launch kit for ``blueprint``/``ingestion_result``.

    The ``blueprint`` side is flattened via ``_blueprint_to_launch_kit_dict``;
    the seed package's businesses are flattened via
    ``_seed_package_to_launch_kit_listings`` (both described above).
    Categories/locations from ``SeedPackage`` pass straight through
    unmodified — only the per-business listing shape needs translation.

    ``launch_kit_output_root`` must be supplied explicitly (rather than
    relying on the exporter's relative ``launch_packages/`` default) so
    every pipeline run — test or production — writes to a caller-chosen
    location instead of the repository working directory.

    Returns a dict with ``package_dir`` (the exported launch package
    path) and ``warnings`` (listings skipped during flattening) so
    downstream stages/callers can inspect data-quality notes without
    the orchestrator's context needing a dedicated warnings channel.
    """
    package = ingestion_result.package
    listings, warnings = _seed_package_to_launch_kit_listings(package)

    seed_package_dict = {
        "listings": listings,
        "categories": [{"name": node.name, "slug": node.slug} for node in package.categories],
        # Explicit, city-keyed entries derived from the already-flattened
        # listings — see _unique_locations_from_listings and the module
        # docstring for why this avoids the Launch Kit engine's own,
        # incompatible name-keyed location derivation.
        "locations": _unique_locations_from_listings(listings),
    }

    _kit, package_dir = LaunchKitService().generate_and_export(
        project_slug,
        _blueprint_to_launch_kit_dict(blueprint),
        seed_package_dict,
        output_root=launch_kit_output_root,
    )
    _patch_url_map_csv_column(package_dir)
    return {"package_dir": package_dir, "warnings": warnings}


def _patch_url_map_csv_column(package_dir: Path) -> None:
    """
    Renames the ``url`` column to ``path`` in the exported
    ``url_map.csv``. See the module docstring: the Launch Kit engine
    hardcodes ``url`` in both its URL-map code paths, while Directory
    Builder's ``UrlMapEntry`` model requires ``path``. Fixed at the
    file level rather than by editing either frozen engine.
    """
    csv_path = package_dir / "url_map.csv"
    if not csv_path.is_file():
        return

    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        rows = list(reader)

    if not fieldnames or "url" not in fieldnames:
        return

    renamed_fieldnames = ["path" if name == "url" else name for name in fieldnames]
    renamed_rows = [
        {("path" if key == "url" else key): value for key, value in row.items()}
        for row in rows
    ]

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=renamed_fieldnames)
        writer.writeheader()
        writer.writerows(renamed_rows)


# ---------------------------------------------------------------------------
# Stage 4: build
# ---------------------------------------------------------------------------

def build_stage(launch_kit_result: dict[str, Any], projects_root: str) -> BuildResult:
    """Builds the directory project from the exported launch package."""
    package_dir = launch_kit_result["package_dir"]
    builder = DirectoryBuilderService(
        LaunchPackageRepository(),
        ProjectAssemblyRepository(projects_root),
    )
    return builder.build_project(str(package_dir))


# ---------------------------------------------------------------------------
# Stage 5: preview (optional)
# ---------------------------------------------------------------------------

def preview_stage(build_result: BuildResult, preview_root: str) -> PreviewBuild:
    """
    Builds a local static-site preview of the completed assembly.

    ``preview_root`` must be supplied explicitly (rather than relying
    on ``PreviewService``'s relative ``previews/`` default) for the
    same reason as ``launch_kit_output_root`` above.
    """
    return PreviewService().build_preview(build_result.assembly, preview_root=preview_root)
