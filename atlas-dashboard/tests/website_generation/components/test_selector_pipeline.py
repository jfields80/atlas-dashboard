"""Production selection-pipeline tests (AES-WEB-002D; AES-WEB-002 §14.2).

Covers every §14.2 step against synthetic registries (candidate/slot-
signature filtering, compatibility filtering, lifecycle filtering under
build flags, commercial-purpose matching with the fallback bypass, additive
scoring incl. the documented brand-affinity no-op, deterministic
tie-breaking, variant selection, fallback/failure), determinism, trace
compression (§14.3), and — the direct AES-WEB-002D acceptance-criterion
proof — real home (§26.1) and category (§26.2) recipe resolution against
the actual registered catalog (Waves 1-3 + the A4 provisional listing card),
not a hand-pinned manifest.
"""

from __future__ import annotations

import pytest

from engines.website_generation.contracts.artifacts import (
    SelectionCandidate,
    SelectionTrace,
    canonical_json,
    model_to_dict,
)
from engines.website_generation.contracts.components import (
    AnalyticsContract,
    MonetizationContract,
    RenderingContract,
)
from engines.website_generation.contracts.enums import (
    AssetRole,
    CommercialPurpose,
    ComponentFamily,
    LifecycleStatus,
    PageRole,
    RegionKind,
)
from engines.website_generation.contracts.errors import ComponentResolutionError
from engines.website_generation.components.registry import ComponentRegistry
from engines.website_generation.components.selection import (
    ComponentSelector,
    LifecycleBuildFlags,
    SlotSelectionRequest,
)
from engines.website_generation.components.selection.trace import (
    compress_candidates,
)
from engines.website_generation.constants.components import (
    CATEGORY_RECIPE_SLOTS,
    HOME_RECIPE_SLOTS,
    SELECTION_FILTER_REQUIRED_CAPABILITY,
)

from . import make_definition

_COMPAT_OK = {"renderer": "1.0.0", "token_schema": "1.0.0", "registry_schema": "1.0.0"}
_FLAGS_ALLOW_PROPOSED = LifecycleBuildFlags(allow_proposed=True)
_FLAGS_STRICT = LifecycleBuildFlags()


def _request(**overrides) -> SlotSelectionRequest:
    fields = dict(slot_id="s", page_role=PageRole.HOME)
    fields.update(overrides)
    return SlotSelectionRequest(**fields)


def _fallback_fixture(**overrides):
    """A synthetic ``layout.section.container``-shaped fallback definition.

    ``make_definition()`` defaults to ``component_id="hero.split.value-
    proposition"`` with a matching family/rendering/analytics contract; this
    helper overrides all four consistently so the definition passes
    ``validate_definition`` (family-segment agreement, §5) and never
    collides with another fixture's ``emitter_key``/``impression_id``
    (§20.1, enforced at registration).
    """
    fields = dict(
        component_id="layout.section.container",
        component_family=ComponentFamily.LAYOUT,
        rendering_contract=RenderingContract(
            emitter_key="layout.section.container@1", class_prefix="ac-layout"
        ),
        analytics_contract=AnalyticsContract(
            impression_id="layout-section-container"
        ),
    )
    fields.update(overrides)
    return make_definition(**fields)


def _select_one(registry, request, **kwargs):
    kwargs.setdefault("compatibility_versions", _COMPAT_OK)
    kwargs.setdefault("lifecycle_flags", _FLAGS_ALLOW_PROPOSED)
    trace = ComponentSelector().select(registry, [request], **kwargs)
    return trace.slots[0]


class TestCandidateAndSlotSignatureFiltering:
    def test_region_mismatch_eliminates_candidate(self):
        d = make_definition(allowed_parent_regions=(RegionKind.BODY,))
        registry = ComponentRegistry([d])
        slot = _select_one(
            registry, _request(required_region=RegionKind.HERO, required=False)
        )
        assert slot.chosen_component_id == ""
        assert slot.candidates[0].eliminated_by == "candidate_role"

    def test_region_match_survives(self):
        d = make_definition(allowed_parent_regions=(RegionKind.HERO,))
        registry = ComponentRegistry([d])
        slot = _select_one(registry, _request(required_region=RegionKind.HERO))
        assert slot.chosen_component_id == d.component_id

    def test_missing_required_prop_eliminates_candidate(self):
        d = make_definition()  # no props declared
        registry = ComponentRegistry([d])
        slot = _select_one(
            registry, _request(required_prop_names=("action_route",), required=False)
        )
        assert slot.chosen_component_id == ""
        assert slot.candidates[0].eliminated_by == "candidate_role"

    def test_missing_required_slot_eliminates_candidate(self):
        d = make_definition()  # no content slots declared
        registry = ComponentRegistry([d])
        slot = _select_one(
            registry, _request(required_slot_names=("h1",), required=False)
        )
        assert slot.chosen_component_id == ""

    def test_fallback_bypasses_signature_check(self):
        # A generic Wave 1/2-style fallback declares none of the slot's
        # specific props/slots, yet must still be selectable as fallback.
        fallback = _fallback_fixture()
        registry = ComponentRegistry([fallback])
        slot = _select_one(
            registry,
            _request(
                required_slot_names=("h1",),
                fallback_component_id="layout.section.container",
            ),
        )
        assert slot.chosen_component_id == "layout.section.container"


class TestCompatibilityFiltering:
    def test_incompatible_version_eliminates_candidate(self):
        d = make_definition(compatibility_range={"renderer": ">=2.0.0"})
        registry = ComponentRegistry([d])
        slot = _select_one(registry, _request(required=False))
        assert slot.chosen_component_id == ""
        assert slot.candidates[0].eliminated_by == "compatibility"

    def test_fallback_does_not_bypass_compatibility(self):
        # Unlike the signature check, a genuinely version-incompatible
        # fallback is still incompatible — compatibility is a hard
        # constraint, not a shape mismatch.
        fallback = _fallback_fixture(compatibility_range={"renderer": ">=9.0.0"})
        registry = ComponentRegistry([fallback])
        with pytest.raises(ComponentResolutionError):
            _select_one(
                registry,
                _request(fallback_component_id="layout.section.container"),
            )

    def test_compatible_version_survives(self):
        d = make_definition(compatibility_range={"renderer": ">=1.0.0,<2.0.0"})
        registry = ComponentRegistry([d])
        slot = _select_one(registry, _request())
        assert slot.chosen_component_id == d.component_id


class TestLifecycleFiltering:
    @pytest.mark.parametrize(
        "status,flag_name",
        [
            (LifecycleStatus.PROPOSED, "allow_proposed"),
            (LifecycleStatus.EXPERIMENTAL, "allow_experimental"),
        ],
    )
    def test_gated_status_requires_matching_flag(self, status, flag_name):
        d = make_definition(lifecycle_status=status)
        registry = ComponentRegistry([d])
        strict = _select_one(registry, _request(required=False), lifecycle_flags=_FLAGS_STRICT)
        assert strict.chosen_component_id == ""
        assert strict.candidates[0].eliminated_by == "lifecycle"

        permissive = _select_one(
            registry,
            _request(),
            lifecycle_flags=LifecycleBuildFlags(**{flag_name: True}),
        )
        assert permissive.chosen_component_id == d.component_id

    def test_deprecated_requires_flag(self):
        d = make_definition(
            lifecycle_status=LifecycleStatus.DEPRECATED,
            replacement_component_id="hero.split.value-proposition",
        )
        registry = ComponentRegistry([d])
        strict = _select_one(registry, _request(required=False), lifecycle_flags=_FLAGS_STRICT)
        assert strict.chosen_component_id == ""
        permissive = _select_one(
            registry, _request(), lifecycle_flags=LifecycleBuildFlags(allow_deprecated=True)
        )
        assert permissive.chosen_component_id == d.component_id

    def test_active_and_preferred_always_eligible(self):
        for status in (LifecycleStatus.ACTIVE, LifecycleStatus.PREFERRED):
            d = make_definition(lifecycle_status=status)
            registry = ComponentRegistry([d])
            slot = _select_one(registry, _request(), lifecycle_flags=_FLAGS_STRICT)
            assert slot.chosen_component_id == d.component_id

    def test_blocked_never_eligible_regardless_of_flags(self):
        d = make_definition(lifecycle_status=LifecycleStatus.BLOCKED)
        registry = ComponentRegistry([d])
        permissive_flags = LifecycleBuildFlags(
            allow_proposed=True, allow_experimental=True, allow_deprecated=True
        )
        slot = _select_one(registry, _request(required=False), lifecycle_flags=permissive_flags)
        assert slot.chosen_component_id == ""
        assert slot.candidates[0].eliminated_by == "lifecycle"

    def test_retired_never_eligible_regardless_of_flags(self):
        d = make_definition(lifecycle_status=LifecycleStatus.RETIRED)
        registry = ComponentRegistry([d])
        permissive_flags = LifecycleBuildFlags(
            allow_proposed=True, allow_experimental=True, allow_deprecated=True
        )
        slot = _select_one(registry, _request(required=False), lifecycle_flags=permissive_flags)
        assert slot.chosen_component_id == ""


class TestCommercialPurposeMatching:
    def test_mismatched_purpose_eliminates_candidate(self):
        d = make_definition(commercial_purpose=CommercialPurpose.ORIENT)
        registry = ComponentRegistry([d])
        slot = _select_one(
            registry,
            _request(purpose=CommercialPurpose.SUPPORT_DISCOVERY, required=False),
        )
        assert slot.chosen_component_id == ""
        assert slot.candidates[0].eliminated_by == "commercial_purpose"

    def test_secondary_purpose_match_survives_without_exact_bonus(self):
        d = make_definition(
            commercial_purpose=CommercialPurpose.ORIENT,
            secondary_purposes=(CommercialPurpose.SUPPORT_DISCOVERY,),
        )
        registry = ComponentRegistry([d])
        slot = _select_one(
            registry, _request(purpose=CommercialPurpose.SUPPORT_DISCOVERY)
        )
        assert slot.chosen_component_id == d.component_id
        assert slot.candidates[0].score == 0

    def test_fallback_bypasses_purpose_matching(self):
        fallback = _fallback_fixture(commercial_purpose=CommercialPurpose.ORIENT)
        registry = ComponentRegistry([fallback])
        slot = _select_one(
            registry,
            _request(
                purpose=CommercialPurpose.SUPPORT_DISCOVERY,
                fallback_component_id="layout.section.container",
            ),
        )
        assert slot.chosen_component_id == "layout.section.container"

    def test_unconstrained_purpose_matches_everyone(self):
        d = make_definition(commercial_purpose=CommercialPurpose.ORIENT)
        registry = ComponentRegistry([d])
        slot = _select_one(registry, _request(purpose=None))
        assert slot.chosen_component_id == d.component_id


class TestScoring:
    def test_preferred_lifecycle_scores_100(self):
        d = make_definition(lifecycle_status=LifecycleStatus.PREFERRED)
        registry = ComponentRegistry([d])
        slot = _select_one(registry, _request(), lifecycle_flags=_FLAGS_STRICT)
        assert slot.candidates[0].score == 100
        assert slot.candidates[0].score_components[0].factor == "preferred_lifecycle"
        assert slot.candidates[0].score_components[0].points == 100

    def test_exact_intent_match_scores_50(self):
        d = make_definition(commercial_purpose=CommercialPurpose.SUPPORT_DISCOVERY)
        registry = ComponentRegistry([d])
        slot = _select_one(
            registry, _request(purpose=CommercialPurpose.SUPPORT_DISCOVERY)
        )
        assert slot.candidates[0].score == 50

    def test_monetization_alignment_scores_30(self):
        d = make_definition(
            monetization_contract=MonetizationContract(
                requires_visible_disclosure=True, disclosure_kind="sponsored",
            )
        )
        registry = ComponentRegistry([d])
        slot = _select_one(registry, _request(monetization_eligible=True))
        assert slot.candidates[0].score == 30

    def test_monetization_alignment_zero_without_contract(self):
        d = make_definition()
        registry = ComponentRegistry([d])
        slot = _select_one(registry, _request(monetization_eligible=True))
        assert slot.candidates[0].score == 0

    def test_optional_asset_availability_scores_10(self):
        d = make_definition(supported_asset_roles=(AssetRole.HERO_IMAGE,))
        registry = ComponentRegistry([d])
        slot = _select_one(
            registry, _request(), available_asset_roles=(AssetRole.HERO_IMAGE,)
        )
        assert slot.candidates[0].score == 10

    def test_asset_availability_zero_without_overlap(self):
        d = make_definition(supported_asset_roles=(AssetRole.LOGO,))
        registry = ComponentRegistry([d])
        slot = _select_one(
            registry, _request(), available_asset_roles=(AssetRole.HERO_IMAGE,)
        )
        assert slot.candidates[0].score == 0

    def test_brand_affinity_never_contributes(self):
        # Documented no-op (decision: no brand-profile-tag metadata exists).
        # A maximally-favorable candidate scores exactly 100+50+30+10=190,
        # never +20 more for brand affinity.
        d = make_definition(
            lifecycle_status=LifecycleStatus.PREFERRED,
            commercial_purpose=CommercialPurpose.SUPPORT_DISCOVERY,
            supported_asset_roles=(AssetRole.HERO_IMAGE,),
            monetization_contract=MonetizationContract(requires_visible_disclosure=True),
        )
        registry = ComponentRegistry([d])
        slot = _select_one(
            registry,
            _request(
                purpose=CommercialPurpose.SUPPORT_DISCOVERY,
                monetization_eligible=True,
            ),
            available_asset_roles=(AssetRole.HERO_IMAGE,),
        )
        assert slot.candidates[0].score == 190
        factors = {c.factor for c in slot.candidates[0].score_components}
        assert "brand_profile_affinity" not in factors

    def test_required_capability_filter_id_never_used_by_real_registry(self):
        # Step 4 is a documented no-op; the constant is reserved, not fired.
        from engines.website_generation.components import build_default_registry

        registry = build_default_registry()
        slot = _select_one(
            registry, _request(page_role=PageRole.HOME, required=False)
        )
        assert all(
            c.eliminated_by != SELECTION_FILTER_REQUIRED_CAPABILITY
            for c in slot.candidates
        )


class TestTieBreaking:
    def test_highest_score_wins(self):
        low = make_definition(component_id="hero.split.value-proposition")
        high = make_definition(
            component_id="hero.centered.standard",
            lifecycle_status=LifecycleStatus.PREFERRED,
            rendering_contract=RenderingContract(
                emitter_key="hero.centered.standard@1", class_prefix="ac-hero"
            ),
            analytics_contract=AnalyticsContract(impression_id="hero-centered-standard"),
        )
        registry = ComponentRegistry([low, high])
        slot = _select_one(registry, _request())
        assert slot.chosen_component_id == "hero.centered.standard"

    def test_score_tie_breaks_lexicographic_component_id(self):
        a = make_definition(
            component_id="hero.centered.standard",
            rendering_contract=RenderingContract(
                emitter_key="hero.centered.standard@1", class_prefix="ac-hero"
            ),
            analytics_contract=AnalyticsContract(impression_id="hero-centered-standard"),
        )
        b = make_definition()  # default id "hero.split.value-proposition"
        registry = ComponentRegistry([b, a])  # insertion order reversed
        slot = _select_one(registry, _request())
        assert slot.chosen_component_id == "hero.centered.standard"

    def test_id_tie_breaks_highest_version(self):
        v1 = make_definition(component_version="1.0.0")
        v2 = make_definition(component_version="1.2.0")
        registry = ComponentRegistry([v1, v2])
        slot = _select_one(registry, _request())
        assert slot.chosen_component_version == "1.2.0"

    def test_tie_break_basis_recorded(self):
        d = make_definition()
        registry = ComponentRegistry([d])
        slot = _select_one(registry, _request())
        assert slot.tie_break_basis == (
            "non_fallback_first,score_desc,component_id_asc,version_desc"
        )

    def test_tie_break_basis_empty_when_nothing_survives(self):
        registry = ComponentRegistry([])
        slot = _select_one(registry, _request(required=False))
        assert slot.tie_break_basis == ""


class TestVariantSelection:
    def test_resolves_to_default_variant(self):
        from engines.website_generation.contracts.components import VariantSpec

        d = make_definition(
            supported_variants={"a": VariantSpec(), "b": VariantSpec()},
            default_variant="b",
        )
        registry = ComponentRegistry([d])
        slot = _select_one(registry, _request())
        assert slot.chosen_variant == "b"

    def test_empty_when_no_variants(self):
        d = make_definition()
        registry = ComponentRegistry([d])
        slot = _select_one(registry, _request())
        assert slot.chosen_variant == ""


class TestFallbackAndFailure:
    def test_required_slot_no_candidate_no_fallback_raises(self):
        registry = ComponentRegistry([])
        with pytest.raises(ComponentResolutionError) as excinfo:
            _select_one(registry, _request(required=True))
        assert excinfo.value.diagnostics["slot_id"] == "s"
        assert excinfo.value.diagnostics["page_role"] == "home"
        assert excinfo.value.diagnostics["candidates"] == []

    def test_required_slot_names_every_candidate_and_eliminating_filter(self):
        d = make_definition(commercial_purpose=CommercialPurpose.ORIENT)
        registry = ComponentRegistry([d])
        with pytest.raises(ComponentResolutionError) as excinfo:
            _select_one(
                registry,
                _request(purpose=CommercialPurpose.SUPPORT_DISCOVERY, required=True),
            )
        candidates = excinfo.value.diagnostics["candidates"]
        assert len(candidates) == 1
        assert candidates[0]["component_id"] == d.component_id
        assert candidates[0]["eliminated_by"] == "commercial_purpose"

    def test_required_slot_with_unfindable_fallback_still_raises(self):
        registry = ComponentRegistry([])
        with pytest.raises(ComponentResolutionError):
            _select_one(
                registry,
                _request(required=True, fallback_component_id="nonexistent.component.id"),
            )

    def test_optional_slot_no_candidate_drops_silently(self):
        registry = ComponentRegistry([])
        slot = _select_one(registry, _request(required=False))
        assert slot.chosen_component_id == ""
        assert slot.candidates == ()

    def test_fallback_resolves_a_required_slot(self):
        fallback = _fallback_fixture()
        registry = ComponentRegistry([fallback])
        slot = _select_one(
            registry,
            _request(
                required=True,
                required_slot_names=("h1",),  # no real candidate has this
                fallback_component_id="layout.section.container",
            ),
        )
        assert slot.chosen_component_id == "layout.section.container"


class TestDeterminism:
    def test_idempotent_across_calls(self):
        d = make_definition()
        registry = ComponentRegistry([d])
        request = _request(purpose=CommercialPurpose.COMMUNICATE_VALUE)
        a = ComponentSelector().select(
            registry, [request],
            compatibility_versions=_COMPAT_OK, lifecycle_flags=_FLAGS_ALLOW_PROPOSED,
        )
        b = ComponentSelector().select(
            registry, [request],
            compatibility_versions=_COMPAT_OK, lifecycle_flags=_FLAGS_ALLOW_PROPOSED,
        )
        assert canonical_json(model_to_dict(a)) == canonical_json(model_to_dict(b))

    def test_empty_requests_yields_empty_trace(self):
        trace = ComponentSelector().select(
            ComponentRegistry([]), [],
            compatibility_versions=_COMPAT_OK, lifecycle_flags=_FLAGS_ALLOW_PROPOSED,
        )
        assert isinstance(trace, SelectionTrace)
        assert trace.slots == ()

    def test_no_randomness_clock_or_uuid_in_module(self):
        import ast
        from pathlib import Path

        path = (
            Path(__file__).resolve().parents[3]
            / "engines" / "website_generation" / "components"
            / "selection" / "selector.py"
        )
        tree = ast.parse(path.read_text(encoding="utf-8"))
        forbidden = {"random", "uuid", "time", "datetime"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = {node.module.split(".")[0]}
            else:
                continue
            assert not (names & forbidden), names & forbidden


class TestTraceCompression:
    def test_named_limited_to_five_rest_compressed(self):
        candidates = tuple(
            SelectionCandidate(
                component_id="c.%02d.x" % i,
                component_version="1.0.0",
                eliminated_by="commercial_purpose" if i % 2 else "compatibility",
            )
            for i in range(12)
        )
        named, counts = compress_candidates(candidates, limit=5)
        assert len(named) == 5
        assert named == candidates[:5]
        # 7 remaining: indices 5..11 -> filters alternate compatibility/commercial_purpose
        remaining = candidates[5:]
        expected_counts = {}
        for c in remaining:
            expected_counts[c.eliminated_by] = expected_counts.get(c.eliminated_by, 0) + 1
        assert counts == expected_counts

    def test_survivors_beyond_limit_not_counted_as_eliminations(self):
        candidates = tuple(
            SelectionCandidate(component_id="c.%02d.x" % i, component_version="1.0.0")
            for i in range(7)
        )
        named, counts = compress_candidates(candidates, limit=5)
        assert len(named) == 5
        assert counts == {}

    def test_real_registry_pool_bounds_named_candidates(self):
        from engines.website_generation.components import build_default_registry

        registry = build_default_registry()
        slot = _select_one(
            registry, _request(page_role=PageRole.HOME, required=False)
        )
        assert len(slot.candidates) <= 5


def _home_hero_request() -> SlotSelectionRequest:
    """The real §26.1 home-hero slot request — the audit-W-1 probe case,
    where the winner previously fell outside the named top-5 because the
    pool's first five lexicographic entries were all eliminated atoms."""
    return SlotSelectionRequest(
        slot_id="hero",
        page_role=PageRole.HOME,
        purpose=CommercialPurpose.SUPPORT_DISCOVERY,
        required_region=RegionKind.HERO,
        required_slot_names=("h1",),
        fallback_component_id="layout.section.container",
    )


class TestTraceWinnerVisibility:
    """Audit remediation W-1 (§14.3/ADR-14): the chosen winner and its
    score breakdown must always be preserved within the named-candidate
    limit — survivors first in final ranking, eliminated after, same
    five-entry compression bound, no trace field-shape changes."""

    def _real_registry_hero_slot(self):
        from engines.website_generation.components import build_default_registry

        return _select_one(build_default_registry(), _home_hero_request())

    def test_winner_is_first_named_candidate(self):
        slot = self._real_registry_hero_slot()
        assert slot.chosen_component_id == "hero.search.directory"
        assert slot.candidates[0].component_id == slot.chosen_component_id
        assert slot.candidates[0].component_version == (
            slot.chosen_component_version
        )

    def test_winner_score_and_components_visible(self):
        slot = self._real_registry_hero_slot()
        winner = slot.candidates[0]
        assert winner.eliminated_by == ""
        assert winner.score == 50  # exact intent match (SUPPORT_DISCOVERY)
        assert [
            (c.factor, c.points) for c in winner.score_components
        ] == [("exact_intent_match", 50)]

    def test_survivors_precede_eliminated_in_named_candidates(self):
        slot = self._real_registry_hero_slot()
        assert len(slot.candidates) == 5  # compression bound preserved
        eliminated_seen = False
        for candidate in slot.candidates:
            if candidate.eliminated_by:
                eliminated_seen = True
            else:
                assert not eliminated_seen, (
                    "survivor %s appears after an eliminated candidate"
                    % candidate.component_id
                )

    def test_eliminated_tail_in_deterministic_registry_order(self):
        slot = self._real_registry_hero_slot()
        eliminated_ids = [
            c.component_id for c in slot.candidates if c.eliminated_by
        ]
        assert eliminated_ids == sorted(eliminated_ids)

    def test_compression_remains_bounded_and_counts_only_eliminations(self):
        slot = self._real_registry_hero_slot()
        assert len(slot.candidates) <= 5
        # Every beyond-limit entry contributing to the counts is an
        # elimination; survivors never appear in elimination_counts.
        assert all(count > 0 for count in slot.elimination_counts.values())
        assert set(slot.elimination_counts) <= {
            "candidate_role", "compatibility", "lifecycle",
            "required_capability", "commercial_purpose",
        }

    def test_repeated_runs_serialize_byte_identically(self):
        from engines.website_generation.components import build_default_registry

        traces = [
            ComponentSelector().select(
                build_default_registry(),
                [_home_hero_request()],
                compatibility_versions=_COMPAT_OK,
                lifecycle_flags=_FLAGS_ALLOW_PROPOSED,
            )
            for _ in range(3)
        ]
        serialized = {canonical_json(model_to_dict(t)) for t in traces}
        assert len(serialized) == 1


class TestFallbackRankingPolicy:
    """Audit remediation W-2 (§14.2 step 9): a fallback is a true last
    resort — every non-fallback survivor ranks ahead of every fallback
    survivor regardless of score; the fallback wins only when no
    non-fallback candidate survives."""

    @staticmethod
    def _secondary_purpose_real_candidate():
        # Matches the slot purpose only via secondary_purposes -> survives
        # step 5 but earns no exact-intent bonus (score 0), and its id
        # sorts lexicographically AFTER the fallback's ("layout." <
        # "listing.") — the exact 0-0 tie the audit probe showed the
        # fallback winning before this remediation.
        return make_definition(
            component_id="listing.card.standard",
            component_family=ComponentFamily.LISTING,
            commercial_purpose=CommercialPurpose.SUPPORT_COMPARISON,
            secondary_purposes=(CommercialPurpose.EXPOSE_INVENTORY,),
            rendering_contract=RenderingContract(
                emitter_key="listing.card.standard@1", class_prefix="ac-listing"
            ),
            analytics_contract=AnalyticsContract(
                impression_id="listing-card-standard"
            ),
        )

    @staticmethod
    def _card_fallback(**overrides):
        fields = dict(
            component_id="layout.card.shell",
            component_family=ComponentFamily.LAYOUT,
            rendering_contract=RenderingContract(
                emitter_key="layout.card.shell@1", class_prefix="ac-layout"
            ),
            analytics_contract=AnalyticsContract(
                impression_id="layout-card-shell"
            ),
        )
        fields.update(overrides)
        return make_definition(**fields)

    def _cards_request(self, **overrides):
        fields = dict(
            slot_id="cards",
            page_role=PageRole.HOME,
            purpose=CommercialPurpose.EXPOSE_INVENTORY,
            fallback_component_id="layout.card.shell",
        )
        fields.update(overrides)
        return SlotSelectionRequest(**fields)

    def test_secondary_purpose_real_candidate_beats_fallback_on_zero_tie(self):
        registry = ComponentRegistry(
            [self._secondary_purpose_real_candidate(), self._card_fallback()]
        )
        slot = _select_one(registry, self._cards_request())
        assert slot.chosen_component_id == "listing.card.standard"

    def test_real_survivor_beats_even_higher_scoring_fallback(self):
        # "Regardless of a 0-0 score tie": even a PREFERRED fallback
        # (score 100) must lose to a 0-scored non-fallback survivor.
        registry = ComponentRegistry(
            [
                self._secondary_purpose_real_candidate(),
                self._card_fallback(lifecycle_status=LifecycleStatus.PREFERRED),
            ]
        )
        slot = _select_one(registry, self._cards_request())
        assert slot.chosen_component_id == "listing.card.standard"

    def test_fallback_wins_only_when_no_real_candidate_survives(self):
        # The real candidate's purposes do not match the slot at all ->
        # eliminated at step 5; the fallback (which bypasses purpose
        # matching) is the sole survivor and correctly resolves the slot.
        real = self._secondary_purpose_real_candidate()
        registry = ComponentRegistry([real, self._card_fallback()])
        slot = _select_one(
            registry,
            self._cards_request(purpose=CommercialPurpose.ESTABLISH_TRUST),
        )
        assert slot.chosen_component_id == "layout.card.shell"

    def test_optional_slot_behavior_unchanged(self):
        # No candidates, no fallback, optional -> dropped silently (traced
        # empty), exactly as before the remediation.
        slot = _select_one(
            ComponentRegistry([]),
            self._cards_request(fallback_component_id="", required=False),
        )
        assert slot.chosen_component_id == ""
        assert slot.candidates == ()

    def test_fallback_still_resolves_required_slot_with_no_real_candidates(self):
        registry = ComponentRegistry([self._card_fallback()])
        slot = _select_one(registry, self._cards_request(required=True))
        assert slot.chosen_component_id == "layout.card.shell"

    def test_fallback_policy_selection_is_deterministic(self):
        registry = ComponentRegistry(
            [self._secondary_purpose_real_candidate(), self._card_fallback()]
        )
        request = self._cards_request()
        traces = [
            ComponentSelector().select(
                registry,
                [request],
                compatibility_versions=_COMPAT_OK,
                lifecycle_flags=_FLAGS_ALLOW_PROPOSED,
            )
            for _ in range(3)
        ]
        serialized = {canonical_json(model_to_dict(t)) for t in traces}
        assert len(serialized) == 1
        assert traces[0].slots[0].chosen_component_id == "listing.card.standard"


class TestRealRecipeResolution:
    """The AES-WEB-002D acceptance-criterion proof: home (§26.1) and
    category (§26.2) recipes resolve against the real registered catalog
    (Waves 1-3 + the A4 provisional listing card) via the production
    selector — not a hand-pinned manifest."""

    @staticmethod
    def _to_request(slot: dict) -> SlotSelectionRequest:
        return SlotSelectionRequest(
            slot_id=slot["slot_id"],
            page_role=PageRole(slot["page_role"]),
            purpose=CommercialPurpose(slot["purpose"]) if slot["purpose"] else None,
            required_region=(
                RegionKind(slot["required_region"]) if slot["required_region"] else None
            ),
            required_prop_names=slot["required_prop_names"],
            required_slot_names=slot["required_slot_names"],
            monetization_eligible=slot["monetization_eligible"],
            fallback_component_id=slot["fallback_component_id"],
            required=slot["required"],
        )

    @staticmethod
    def _resolve(slots):
        from engines.website_generation.components import build_default_registry

        registry = build_default_registry()
        requests = [
            TestRealRecipeResolution._to_request(s) for s in slots
        ]
        trace = ComponentSelector().select(
            registry,
            requests,
            compatibility_versions=_COMPAT_OK,
            lifecycle_flags=_FLAGS_ALLOW_PROPOSED,
        )
        return {s.slot_id: s.chosen_component_id for s in trace.slots}

    def test_home_recipe_resolves_required_slots_to_real_components(self):
        chosen = self._resolve(HOME_RECIPE_SLOTS)
        assert chosen["utility_bar"] == "nav.utility.bar"
        assert chosen["hero"] == "hero.search.directory"
        assert chosen["categories_grid"] == "directory.categories.grid"
        assert chosen["locations_grid"] == "directory.locations.grid"

    def test_home_recipe_drops_unbuilt_optional_slots(self):
        chosen = self._resolve(HOME_RECIPE_SLOTS)
        for slot_id in (
            "featured_zone", "trust_strip", "editorial_resources",
            "claim_cta_band", "newsletter_capture",
        ):
            assert chosen[slot_id] == "", slot_id

    def test_category_recipe_resolves_required_slots_to_real_components(self):
        chosen = self._resolve(CATEGORY_RECIPE_SLOTS)
        assert chosen["hero"] == "hero.local.standard"
        assert chosen["filters"] == "directory.filters.panel"
        assert chosen["sort"] == "directory.sort.control"
        assert chosen["results_summary"] == "directory.results.summary"
        assert chosen["listing_cards"] == "listing.card.standard"
        assert chosen["pagination"] == "nav.pagination.standard"
        assert chosen["zero_results"] == "status.results.zero"

    def test_category_recipe_drops_unbuilt_optional_slots(self):
        chosen = self._resolve(CATEGORY_RECIPE_SLOTS)
        assert chosen["related_categories_cities"] == ""
        assert chosen["claim_cta_band"] == ""

    def test_recipe_resolution_is_deterministic(self):
        first = self._resolve(HOME_RECIPE_SLOTS)
        second = self._resolve(HOME_RECIPE_SLOTS)
        assert first == second

    def test_no_required_home_or_category_slot_raises(self):
        # If this raised, the recipe's required slots would have no
        # satisfiable candidate — the exact failure the fallback mechanism
        # exists to prevent.
        self._resolve(HOME_RECIPE_SLOTS)
        self._resolve(CATEGORY_RECIPE_SLOTS)
