"""Component selection (AES-WEB-002A skeleton + AES-WEB-002D production
pipeline; AES-WEB-002 §14, §31).

This module carries two selectors, kept side by side deliberately:

* :class:`SelectionSkeleton` — the original AES-WEB-002A **interface/
  skeleton proof only**, unchanged since 002A. It satisfies the §31 002A
  acceptance criterion ("selection returns deterministic results + traces on
  [an empty/]synthetic registry") without production filtering, scoring, or
  tie-breaking: for each requested slot it reads the registry's page-role
  index (``candidates_for``) and, when at least one candidate exists, picks
  the first in the registry's existing lexicographic order. Its own tests
  (``tests/website_generation/components/test_selection_skeleton.py``)
  pin this behavior; it is retained for that historical/interface-proof
  role, not because anything still calls it in preference to
  :class:`ComponentSelector`.
* :class:`ComponentSelector` — the AES-WEB-002D production §14.2 pipeline:
  candidate filtering, compatibility filtering, lifecycle filtering,
  required-capability matching (documented no-op — see its section below),
  commercial-purpose matching, additive integer scoring, deterministic
  tie-breaking, variant selection, and fallback/failure handling. Pure and
  deterministic throughout: no clock/UUID/randomness/AI/IO/network.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple

from engines.website_generation.contracts.artifacts import (
    FrozenModel,
    SelectionCandidate,
    SelectionScoreComponent,
    SelectionTrace,
    SlotSelectionTrace,
)
from engines.website_generation.contracts.enums import (
    AssetRole,
    CommercialPurpose,
    LifecycleStatus,
    PageRole,
    RegionKind,
)
from engines.website_generation.contracts.errors import (
    ComponentNotFoundError,
    ComponentResolutionError,
)
from engines.website_generation.contracts.interfaces import (
    ComponentRegistryView,
)
from engines.website_generation.constants.components import (
    SELECTION_FACTOR_EXACT_INTENT_MATCH,
    SELECTION_FACTOR_MONETIZATION_ALIGNMENT,
    SELECTION_FACTOR_OPTIONAL_ASSET_AVAILABILITY,
    SELECTION_FACTOR_PREFERRED_LIFECYCLE,
    SELECTION_FILTER_CANDIDATE_ROLE,
    SELECTION_FILTER_COMMERCIAL_PURPOSE,
    SELECTION_FILTER_COMPATIBILITY,
    SELECTION_FILTER_LIFECYCLE,
    SELECTION_SCORE_EXACT_INTENT_MATCH,
    SELECTION_SCORE_MONETIZATION_ALIGNMENT,
    SELECTION_SCORE_OPTIONAL_ASSET_AVAILABILITY,
    SELECTION_SCORE_PREFERRED_LIFECYCLE,
    SELECTION_TIE_BREAK_BASIS,
    SELECTION_TRACE_NAMED_CANDIDATE_LIMIT,
)
from engines.website_generation.components.compatibility.ranges import (
    evaluate_compatibility,
    parse_version,
)
from engines.website_generation.components.selection.trace import (
    compress_candidates,
)


class SlotRequest(FrozenModel):
    """A typed request to fill one page slot (skeleton input).

    Minimal by design: the production selector consumes richer slot-need
    signatures (recipe capabilities, conversion objective, etc.) in a later
    wave. Here a request is just the slot id and the page role to index by.
    """

    slot_id: str
    page_role: PageRole


class SelectionSkeleton:
    """Deterministic, pure selection-skeleton proof (see module docstring)."""

    version = "0.0.0-skeleton"

    def select(
        self,
        registry: ComponentRegistryView,
        slot_requests: Iterable[SlotRequest],
    ) -> SelectionTrace:
        """Return a deterministic :class:`SelectionTrace` over ``registry``.

        Pure function of ``(registry contents, slot_requests)`` — identical
        inputs always yield an identical trace. Never raises for an empty
        result; an unfillable slot simply records no chosen component.
        """
        slots: List[SlotSelectionTrace] = []
        for request in slot_requests:
            candidates = registry.candidates_for(request.page_role)
            traced = tuple(
                SelectionCandidate(
                    component_id=definition.component_id,
                    component_version=definition.component_version,
                )
                for definition in candidates
            )
            if candidates:
                chosen = candidates[0]  # first of the registry's lexicographic
                # index — a placeholder, NOT §14.2 scoring/tie-breaking.
                slots.append(
                    SlotSelectionTrace(
                        slot_id=request.slot_id,
                        candidates=traced,
                        chosen_component_id=chosen.component_id,
                        chosen_component_version=chosen.component_version,
                    )
                )
            else:
                slots.append(
                    SlotSelectionTrace(
                        slot_id=request.slot_id,
                        candidates=(),
                    )
                )
        return SelectionTrace(slots=tuple(slots))


# =============================================================================
# Production selection pipeline (AES-WEB-002D; AES-WEB-002 §14.2)
#
# Implements every §14.2 step in normative order, using only fields that
# already exist on ComponentDefinition/registry — no invented metadata, no
# new registry concepts (per the AES-WEB-002D scope decisions). Two steps
# are explicit, documented pass-through/no-op stages because the current
# contracts carry no corresponding metadata:
#
#   * step 4 (required-capability matching) — ComponentDefinition declares
#     no "capabilities" field; the stage runs (so the 9-step structure stays
#     legible and testable) and returns its input unchanged.
#   * step 6's brand-profile-affinity scoring factor — the registry declares
#     no brand-profile tags; the factor is reserved in constants but never
#     awarded (contributes 0 always), rather than guessed at.
#
# The lifecycle filter (step 3) is gated by an explicit, caller-supplied
# LifecycleBuildFlags value — never a global/mutable flag — so PROPOSED
# components may participate in deterministic composition during this
# implementation phase without changing any component's registered
# lifecycle_status or certification semantics (§23 promotion is untouched).
# =============================================================================


class SlotSelectionRequest(FrozenModel):
    """A typed request to fill one recipe slot (§14.1, §26).

    ``purpose`` is the recipe's declared commercial-purpose intent for this
    slot (§14.2 step 5), or ``None`` when the slot is purpose-unconstrained.
    Purpose alone frequently under-determines a slot: several Wave 3
    components legitimately share a primary ``commercial_purpose`` (e.g.
    every ``directory.*`` discovery component). Since no capability metadata
    exists to disambiguate them (decision: no invented registry concepts),
    step 1's "slot signature satisfiable" check (§14.2) is realized here
    using three already-existing, per-definition signals instead:
    ``required_region`` (the region the candidate must declare in
    ``allowed_parent_regions``, §9.1), and ``required_prop_names`` /
    ``required_slot_names`` (specific prop/content-slot dictionary keys the
    candidate must declare — real fields already on every
    ``ComponentDefinition``, just checked by name rather than by type).

    ``fallback_component_id`` is the slot's guaranteed-satisfiable Wave 1/2
    primitive (§14.2 step 9); empty when the slot's real candidate already
    resolves within the currently registered waves. ``required`` follows the
    §26 rule: an unfillable *required* slot is a
    :class:`~engines.website_generation.contracts.errors.ComponentResolutionError`;
    an unfillable *optional* slot is dropped and traced.
    """

    slot_id: str
    page_role: PageRole
    required_region: Optional[RegionKind] = None
    required_prop_names: Tuple[str, ...] = ()
    required_slot_names: Tuple[str, ...] = ()
    purpose: Optional[CommercialPurpose] = None
    monetization_eligible: bool = False
    fallback_component_id: str = ""
    required: bool = True


class LifecycleBuildFlags(FrozenModel):
    """Implementation-phase capability flags from constants (§14.1).

    Data, not global state — every :meth:`ComponentSelector.select` call
    takes an explicit value. Defaults are the conservative (all-``False``)
    posture; callers typically pass
    ``constants.components.DEFAULT_LIFECYCLE_ALLOW_*`` explicitly.
    """

    allow_proposed: bool = False
    allow_experimental: bool = False
    allow_deprecated: bool = False


class _CandidateState:
    """Internal, mutable bookkeeping for one candidate's pipeline journey.

    Never serialized directly and never part of any public contract — the
    typed :class:`SelectionCandidate` view is assembled only at the end, in
    :meth:`ComponentSelector._select_slot`.
    """

    __slots__ = (
        "definition",
        "is_fallback",
        "eliminated_by",
        "score",
        "score_components",
    )

    def __init__(self, definition, is_fallback: bool = False) -> None:
        self.definition = definition
        self.is_fallback = is_fallback
        self.eliminated_by = ""
        self.score: Optional[int] = None
        self.score_components: List[SelectionScoreComponent] = []

    def eliminate(self, filter_id: str) -> None:
        if not self.eliminated_by:
            self.eliminated_by = filter_id

    @property
    def alive(self) -> bool:
        return not self.eliminated_by


def _matches_slot_signature(definition, request: "SlotSelectionRequest") -> bool:
    """Step 1's slot-signature check (§14.2): region membership plus named
    prop/content-slot declarations, per :class:`SlotSelectionRequest`."""
    if (
        request.required_region is not None
        and request.required_region not in definition.allowed_parent_regions
    ):
        return False
    if request.required_prop_names:
        declared_props = set(definition.required_props) | set(definition.optional_props)
        if not set(request.required_prop_names) <= declared_props:
            return False
    if request.required_slot_names:
        declared_slots = set(definition.required_content_slots) | set(
            definition.optional_content_slots
        )
        if not set(request.required_slot_names) <= declared_slots:
            return False
    return True


class ComponentSelector:
    """The deterministic §14.2 selection pipeline. Pure: identical inputs
    (registry contents, slot requests, compatibility versions, lifecycle
    flags, available asset roles) always yield an identical
    :class:`SelectionTrace`. No randomness, clock, UUID, network, or I/O."""

    version = "1.0.0"

    def select(
        self,
        registry: ComponentRegistryView,
        slot_requests: Iterable[SlotSelectionRequest],
        *,
        compatibility_versions: Dict[str, str],
        lifecycle_flags: LifecycleBuildFlags,
        available_asset_roles: Tuple[AssetRole, ...] = (),
    ) -> SelectionTrace:
        slots: List[SlotSelectionTrace] = []
        for request in slot_requests:
            slots.append(
                self._select_slot(
                    registry,
                    request,
                    compatibility_versions,
                    lifecycle_flags,
                    available_asset_roles,
                )
            )
        return SelectionTrace(slots=tuple(slots))

    def _select_slot(
        self,
        registry: ComponentRegistryView,
        request: SlotSelectionRequest,
        compatibility_versions: Dict[str, str],
        lifecycle_flags: LifecycleBuildFlags,
        available_asset_roles: Tuple[AssetRole, ...],
    ) -> SlotSelectionTrace:
        # -- assemble the initial pool: role-eligible candidates plus the
        # declared fallback, injected unconditionally so "guaranteed
        # satisfiable" does not depend on it happening to appear in the
        # role index (§14.2 step 9).
        pool: List[_CandidateState] = [
            _CandidateState(d) for d in registry.candidates_for(request.page_role)
        ]
        known_ids = {s.definition.component_id for s in pool}
        if request.fallback_component_id and request.fallback_component_id not in known_ids:
            try:
                pool.append(
                    _CandidateState(
                        registry.get(request.fallback_component_id),
                        is_fallback=True,
                    )
                )
            except ComponentNotFoundError:
                pass
        for state in pool:
            if state.definition.component_id == request.fallback_component_id:
                state.is_fallback = True

        # Step 1: candidate filtering (role already guaranteed by the index
        # lookup above; the slot-signature sub-check runs here). The
        # declared fallback bypasses this check for the same reason it
        # bypasses step 5 below: a generic Wave 1/2 structural primitive is
        # not expected to match a specific slot's shape, only to be a safe
        # last resort.
        for state in pool:
            if state.is_fallback:
                continue
            if not _matches_slot_signature(state.definition, request):
                state.eliminate(SELECTION_FILTER_CANDIDATE_ROLE)

        # Step 2: compatibility filtering.
        for state in pool:
            if not state.alive:
                continue
            compatible, _failing = evaluate_compatibility(
                state.definition.compatibility_range, compatibility_versions
            )
            if not compatible:
                state.eliminate(SELECTION_FILTER_COMPATIBILITY)

        # Step 3: lifecycle filtering.
        for state in pool:
            if not state.alive:
                continue
            status = state.definition.lifecycle_status
            if status in (LifecycleStatus.ACTIVE, LifecycleStatus.PREFERRED):
                continue
            if status is LifecycleStatus.PROPOSED and lifecycle_flags.allow_proposed:
                continue
            if (
                status is LifecycleStatus.EXPERIMENTAL
                and lifecycle_flags.allow_experimental
            ):
                continue
            if (
                status is LifecycleStatus.DEPRECATED
                and lifecycle_flags.allow_deprecated
            ):
                continue
            state.eliminate(SELECTION_FILTER_LIFECYCLE)

        # Step 4: required-capability matching — explicit no-op/pass-through
        # (see module docstring: no capability metadata exists to filter on).

        # Step 5: commercial-purpose matching. The declared fallback bypasses
        # this step: a "guaranteed-satisfiable Wave 1/2 primitive" carries no
        # commercial purpose beyond ORIENT/IMPROVE_ACCESSIBILITY (§5.16) and
        # would otherwise never match a discovery/inventory/trust-purposed
        # slot, which would make the fallback doctrine incoherent.
        if request.purpose is not None:
            for state in pool:
                if not state.alive or state.is_fallback:
                    continue
                candidate_purposes = (
                    state.definition.commercial_purpose,
                ) + state.definition.secondary_purposes
                if request.purpose not in candidate_purposes:
                    state.eliminate(SELECTION_FILTER_COMMERCIAL_PURPOSE)

        # Step 6: stable scoring (additive integers, static tables only).
        for state in pool:
            if not state.alive:
                continue
            factors: List[Tuple[str, int]] = []
            if state.definition.lifecycle_status is LifecycleStatus.PREFERRED:
                factors.append(
                    (SELECTION_FACTOR_PREFERRED_LIFECYCLE, SELECTION_SCORE_PREFERRED_LIFECYCLE)
                )
            if (
                request.purpose is not None
                and state.definition.commercial_purpose == request.purpose
            ):
                factors.append(
                    (SELECTION_FACTOR_EXACT_INTENT_MATCH, SELECTION_SCORE_EXACT_INTENT_MATCH)
                )
            if (
                request.monetization_eligible
                and state.definition.monetization_contract is not None
            ):
                factors.append(
                    (
                        SELECTION_FACTOR_MONETIZATION_ALIGNMENT,
                        SELECTION_SCORE_MONETIZATION_ALIGNMENT,
                    )
                )
            # Brand-profile affinity (§14.2 step 6, +20): reserved, never
            # awarded — no brand-profile-tag metadata exists on
            # ComponentDefinition (documented no-op; see module docstring).
            if available_asset_roles and set(
                state.definition.supported_asset_roles
            ) & set(available_asset_roles):
                factors.append(
                    (
                        SELECTION_FACTOR_OPTIONAL_ASSET_AVAILABILITY,
                        SELECTION_SCORE_OPTIONAL_ASSET_AVAILABILITY,
                    )
                )
            state.score = sum(points for _factor, points in factors)
            state.score_components = [
                SelectionScoreComponent(factor=factor, points=points)
                for factor, points in factors
            ]

        # Step 7: deterministic tie-breaking. Fallbacks are last-resort
        # candidates (§14.2 step 9), never peers: every non-fallback
        # survivor ranks ahead of every fallback survivor regardless of
        # score, so a fallback can win only when no non-fallback candidate
        # survives (audit remediation W-2 — without the class key, a
        # 0-scored fallback could lexicographically beat a real candidate
        # that matched the slot's purpose only via secondary_purposes).
        # Within a class, the §14.2 order is unchanged: highest score, then
        # lexicographic component_id, then highest version.
        survivors = [s for s in pool if s.alive]
        survivors.sort(
            key=lambda s: (
                s.is_fallback,
                -s.score,
                s.definition.component_id,
                tuple(-part for part in parse_version(s.definition.component_version)),
            )
        )
        tie_break_basis = SELECTION_TIE_BREAK_BASIS if survivors else ""

        # Step 8: variant selection — resolves to default_variant (§14.2
        # step 8's terminal fallback); recipe-declared variant guidance is
        # deferred until recipes carry that metadata (kept out of scope per
        # the "no invented metadata" decision).
        chosen_component_id = ""
        chosen_component_version = ""
        chosen_variant = ""
        if survivors:
            winner = survivors[0]
            chosen_component_id = winner.definition.component_id
            chosen_component_version = winner.definition.component_version
            chosen_variant = winner.definition.default_variant

        # Step 9: fallback and failure. A required slot with no surviving
        # candidate (even after the fallback injection above) is a hard
        # failure naming every candidate and its eliminating filter. An
        # optional slot with no surviving candidate is dropped, silently but
        # traced (§26 fallback rule).
        if not survivors and request.required:
            raise ComponentResolutionError(
                "no component resolved required slot %r for page role %r"
                % (request.slot_id, request.page_role.value),
                stage="component_selection",
                diagnostics={
                    "slot_id": request.slot_id,
                    "page_role": request.page_role.value,
                    "candidates": [
                        {
                            "component_id": s.definition.component_id,
                            "component_version": s.definition.component_version,
                            "eliminated_by": s.eliminated_by,
                        }
                        for s in pool
                    ],
                },
            )

        # Assemble the size-bounded trace (§14.3): named top-N candidates
        # plus per-filter elimination counts for the remainder. Ordering
        # (audit remediation W-1): surviving candidates first, in the final
        # step-7 ranking — so the chosen winner is always candidates[0]
        # with its score and score_components visible in the trace —
        # followed by eliminated candidates in the pool's deterministic
        # registry-index order (lexicographic component_id, §15.2).
        ordered_for_trace = [
            SelectionCandidate(
                component_id=s.definition.component_id,
                component_version=s.definition.component_version,
                eliminated_by=s.eliminated_by,
                score=s.score,
                score_components=tuple(s.score_components),
            )
            for s in survivors + [s for s in pool if not s.alive]
        ]
        named, elimination_counts = compress_candidates(
            ordered_for_trace, SELECTION_TRACE_NAMED_CANDIDATE_LIMIT
        )

        return SlotSelectionTrace(
            slot_id=request.slot_id,
            candidates=named,
            elimination_counts=elimination_counts,
            tie_break_basis=tie_break_basis,
            chosen_component_id=chosen_component_id,
            chosen_component_version=chosen_component_version,
            chosen_variant=chosen_variant,
        )
