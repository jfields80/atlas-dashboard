"""ContentEngine — (SiteArchitecture, ContentCandidates, BusinessSpec) ->
ContentPackage (AES-WEB-001 §5.4 / Part 2).

Internal sequencing label: AES-WEB-002J.4. The determinism airlock: the
Content Engine validates supplied ``ContentCandidate`` records against the
routes and declared content slots of a ``SiteArchitecture``, enforces the
banned-phrase and placeholder-marker policy and per-slot length bounds
(constants/content.py), and -- only when every candidate and every required
slot passes -- assembles the validated, ordered ``ContentPackage``.

Deterministic, pure, serializable, byte-stable: the same
``(SiteArchitecture, candidates, BusinessSpec)`` triple always produces the
same ``ContentPackage`` (or the same batch of diagnostics). No network
access, no filesystem access, no model calls, no randomness, no
clock-dependent behavior. Not wired into pipeline execution --
``content_drafting`` and ``content_validation`` both remain ``NOT_EXECUTED``
in the ``BuildManifest`` (``PHASE1_EXECUTED_STAGES`` is unchanged by this
module).

Scope boundary (Decision A1, binding for this delivery): this module is a
validation airlock, not a copy-generation engine. It never authors,
generates, rewrites, summarizes, expands, or varies candidate text -- every
accepted ``ContentBlock.text`` is byte-identical to the ``ContentCandidate
.body`` that produced it. There is no phrase library, no sentence template,
no stable-hash phrase selection, no runtime model call, and no network or
filesystem access anywhere in this package. ``BrandPackage`` is not an
input and is never read; voice is not inferred from design tokens here.
Copy authorship belongs to an operator or a future authorized cognition
phase (AES-WEB-001 §7).
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

from engines.website_generation.content.content_validators import (
    CandidateClassification,
    classify_candidates,
    duplicate_binding_keys,
    find_banned_phrases,
    find_placeholder_markers,
    missing_required_bindings,
    page_slot_map,
    slot_length_violation,
    unique_bindings_only,
)
from engines.website_generation.contracts.artifacts import (
    BusinessSpec,
    ContentBlock,
    ContentCandidate,
    ContentPackage,
    PagePlan,
    SiteArchitecture,
    artifact_sha256,
)
from engines.website_generation.contracts.enums import ArtifactKind
from engines.website_generation.contracts.errors import ContentValidationError
from engines.website_generation.contracts.interfaces import ContentEngineInterface
from engines.website_generation.contracts.versions import (
    ENGINE_VERSIONS,
    SCHEMA_VERSIONS,
)

# Structural bucket -> diagnostics key (§8). Order fixed and documented so
# diagnostics dict key insertion order (irrelevant to output, but useful for
# readability when debugging) stays predictable.
_STRUCTURAL_BUCKET_KEYS: Tuple[Tuple[str, str], ...] = (
    ("unknown_route", "unknown_route_candidates"),
    ("unsupported_slot", "unsupported_slot_candidates"),
    ("undeclared_slot", "undeclared_slot_candidates"),
)


def _candidate_ref(candidate: ContentCandidate) -> Dict[str, str]:
    return {"page_route": candidate.page_route, "slot_id": candidate.slot_id}


class ContentEngine(ContentEngineInterface):
    """Validate ``ContentCandidate`` records into a deterministic
    ``ContentPackage``."""

    version = ENGINE_VERSIONS["content_engine"]

    def validate(
        self,
        site_architecture: SiteArchitecture,
        candidates: Sequence[ContentCandidate],
        business_spec: BusinessSpec,
    ) -> ContentPackage:
        """Total function over structurally valid inputs; batch-fails otherwise.

        Deterministic guarantees: none of the three inputs are mutated (all
        are frozen); classification, policy checks, and output block order
        are pure functions of ``site_architecture``'s declared page/slot
        order and each candidate's own fields -- never of ``candidates``'
        input order (AES-WEB-001 §1.1 replayability contract).
        """
        slot_map = page_slot_map(site_architecture.pages)
        classification = classify_candidates(candidates, slot_map)
        unique = unique_bindings_only(classification.bindings)
        duplicate_keys = duplicate_binding_keys(classification.bindings)

        diagnostics: Dict[str, Any] = {}
        diagnostics.update(
            self._structural_diagnostics(classification, duplicate_keys)
        )
        diagnostics.update(
            self._coverage_diagnostics(slot_map, classification.bindings)
        )
        diagnostics.update(self._content_diagnostics(unique))

        if diagnostics:
            raise ContentValidationError(
                "ContentPackage validation failed; see diagnostics",
                diagnostics=diagnostics,
            )

        blocks = self._build_blocks(site_architecture.pages, slot_map, unique)
        source_hashes = self._build_source_hashes(
            site_architecture, business_spec, unique
        )

        return ContentPackage(
            schema_version=SCHEMA_VERSIONS[ArtifactKind.CONTENT_PACKAGE],
            artifact_kind=ArtifactKind.CONTENT_PACKAGE,
            source_hashes=source_hashes,
            blocks=blocks,
        )

    @staticmethod
    def _structural_diagnostics(
        classification: CandidateClassification,
        duplicate_keys: Tuple[Tuple[str, str], ...],
    ) -> Dict[str, Any]:
        """Route/slot-membership and duplicate-binding diagnostics (§8)."""
        diagnostics: Dict[str, Any] = {}

        for attr, key in _STRUCTURAL_BUCKET_KEYS:
            bucket = getattr(classification, attr)
            if bucket:
                diagnostics[key] = [_candidate_ref(c) for c in bucket]

        if duplicate_keys:
            diagnostics["duplicate_bindings"] = [
                {
                    "page_route": route,
                    "slot_id": slot_id,
                    "candidate_count": len(classification.bindings[(route, slot_id)]),
                }
                for route, slot_id in duplicate_keys
            ]

        return diagnostics

    @staticmethod
    def _coverage_diagnostics(
        slot_map: Dict[str, Tuple[str, ...]],
        bindings: Dict[Tuple[str, str], Tuple[ContentCandidate, ...]],
    ) -> Dict[str, Any]:
        """Required-slot-coverage diagnostics (§8): zero candidates at all.

        A slot with a duplicate binding is "covered" (>=1 candidate present)
        and is reported only via ``duplicate_bindings``, never here too --
        this checks presence in the full (possibly-ambiguous) ``bindings``,
        not the unique-only view.
        """
        missing = missing_required_bindings(slot_map, bindings)
        if not missing:
            return {}
        return {
            "missing_required_slots": [
                {"page_route": route, "slot_id": slot_id}
                for route, slot_id in missing
            ]
        }

    @staticmethod
    def _content_diagnostics(
        unique: Dict[Tuple[str, str], ContentCandidate],
    ) -> Dict[str, Any]:
        """Banned-phrase, placeholder-marker, and length diagnostics (§10).

        Evaluated only over ``unique`` -- bindings already filtered to
        exactly one candidate. An ambiguous duplicate binding is reported
        once, structurally, by :meth:`_structural_diagnostics`; resolving
        the duplicate is a prerequisite to evaluating its content, so no
        content-quality check runs against either copy.
        """
        banned: List[Dict[str, Any]] = []
        placeholders: List[Dict[str, Any]] = []
        lengths: List[Dict[str, Any]] = []

        for route, slot_id in sorted(unique):
            body = unique[(route, slot_id)].body

            phrases = find_banned_phrases(body)
            if phrases:
                banned.append(
                    {
                        "page_route": route,
                        "slot_id": slot_id,
                        "phrases": list(phrases),
                    }
                )

            markers = find_placeholder_markers(body)
            if markers:
                placeholders.append(
                    {
                        "page_route": route,
                        "slot_id": slot_id,
                        "markers": list(markers),
                    }
                )

            violation = slot_length_violation(slot_id, body)
            if violation is not None:
                entry: Dict[str, Any] = {"page_route": route, "slot_id": slot_id}
                entry.update(violation)
                lengths.append(entry)

        diagnostics: Dict[str, Any] = {}
        if banned:
            diagnostics["banned_phrase_violations"] = banned
        if placeholders:
            diagnostics["placeholder_violations"] = placeholders
        if lengths:
            diagnostics["length_violations"] = lengths
        return diagnostics

    @staticmethod
    def _build_blocks(
        pages: Sequence[PagePlan],
        slot_map: Dict[str, Tuple[str, ...]],
        unique: Dict[Tuple[str, str], ContentCandidate],
    ) -> Tuple[ContentBlock, ...]:
        """Validated blocks in SiteArchitecture's page order and each page's
        declared slot order -- never independently re-sorted (§8).

        Walks each distinct route exactly once (by first occurrence in
        ``pages``) and reads its slots from ``slot_map`` -- the same
        resolved, deduplicated view ``classify_candidates`` and
        ``missing_required_bindings`` validated against -- rather than
        re-reading each ``PagePlan.content_slots`` directly. A
        ``SiteArchitecture`` with a duplicate route is trusted upstream
        input, not repaired here (§13), but this guarantees every
        ``(route, slot_id)`` looked up here was already proven present in
        ``unique`` by the coverage check above, so this can never raise
        ``KeyError`` and can never double-emit a block for a route that
        appears more than once in ``pages``.
        """
        blocks: List[ContentBlock] = []
        seen_routes: set = set()
        for page in pages:
            if page.route in seen_routes:
                continue
            seen_routes.add(page.route)
            for slot_id in slot_map[page.route]:
                candidate = unique[(page.route, slot_id)]
                blocks.append(
                    ContentBlock(
                        page_route=page.route,
                        slot_id=slot_id,
                        text=candidate.body,
                    )
                )
        return tuple(blocks)

    @staticmethod
    def _build_source_hashes(
        site_architecture: SiteArchitecture,
        business_spec: BusinessSpec,
        unique: Dict[Tuple[str, str], ContentCandidate],
    ) -> Dict[str, str]:
        """Provenance over every input artifact that produced this package
        (§4.1): the SiteArchitecture, the BusinessSpec, and every accepted
        candidate, keyed so the map never depends on candidate input order
        (canonical serialization sorts keys regardless -- §4.3)."""
        source_hashes = {
            "site_architecture": artifact_sha256(site_architecture),
            "business_spec": artifact_sha256(business_spec),
        }
        for (route, slot_id), candidate in unique.items():
            key = "content_candidate:%s:%s" % (route, slot_id)
            source_hashes[key] = artifact_sha256(candidate)
        return source_hashes
