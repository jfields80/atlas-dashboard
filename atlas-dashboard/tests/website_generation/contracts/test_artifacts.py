"""Artifact contract tests (AES-WEB-001 Phase 1).

Covers: all 12 kinds registered at v1.0.0, frozen behavior, canonical
serialization stability, hash identity/change, unsupported schema
rejection, and mandatory header enforcement.
"""

from __future__ import annotations

import json

import pytest

from engines.website_generation import (
    SCHEMA_VERSIONS,
    ArtifactKind,
    BrandPackage,
    BuildManifest,
    BuildState,
    BusinessSpec,
    ComponentManifest,
    ContentCandidate,
    ContentPackage,
    ContrastEvidence,
    LayoutPlan,
    QualityReport,
    RenderedPageSet,
    SEOPackage,
    SchemaRegistrationError,
    SelectionCandidate,
    SelectionScoreComponent,
    SelectionTrace,
    SiteArchitecture,
    SiteBundle,
    SlotSelectionTrace,
    UnsupportedSchemaVersionError,
    artifact_sha256,
    canonical_artifact_json,
    canonical_json,
    registered_artifact_model,
    registered_schema_versions,
)
from engines.website_generation.contracts.artifacts import (
    ArtifactCanonicalizationError,
    BrandPackageV1,
    ComponentManifestV1,
    model_to_dict,
)
from engines.website_generation.contracts.versions import (
    register_artifact_model,
)

ALL_KINDS = list(ArtifactKind)


def _make_spec(**overrides) -> BusinessSpec:
    fields = dict(
        schema_version="1.0.0",
        artifact_kind=ArtifactKind.BUSINESS_SPEC,
        source_hashes={"external:project": "a" * 64},
        business_name="Pet Trip Finder",
        niche="pet travel",
        audience="pet owners",
        value_proposition="verified pet-friendly stays",
        directory_taxonomy=("hotels", "parks"),
    )
    fields.update(overrides)
    return BusinessSpec(**fields)


class TestCatalogRegistration:
    def test_exactly_twelve_artifact_kinds(self):
        assert len(ALL_KINDS) == 12

    def test_all_twelve_kinds_registered_at_v1(self):
        for kind in ALL_KINDS:
            model_cls = registered_artifact_model(kind, "1.0.0")
            assert model_cls is not None

    def test_schema_versions_map_covers_every_kind(self):
        # Amendment A1: ComponentManifest current schema is 1.1.0.
        # AES-WEB-002J.2 (AES-WEB-001 §5.2/Part 2): BrandPackage current
        # schema is likewise 1.1.0 (additive radius_scale/extended_tokens/
        # contrast_evidence). Every other kind remains 1.0.0.
        assert set(SCHEMA_VERSIONS) == set(ALL_KINDS)
        assert SCHEMA_VERSIONS[ArtifactKind.COMPONENT_MANIFEST] == "1.1.0"
        assert SCHEMA_VERSIONS[ArtifactKind.BRAND_PACKAGE] == "1.1.0"
        _minor_bumped = (ArtifactKind.COMPONENT_MANIFEST, ArtifactKind.BRAND_PACKAGE)
        for kind in ALL_KINDS:
            if kind in _minor_bumped:
                continue
            assert SCHEMA_VERSIONS[kind] == "1.0.0"

    def test_registered_schema_versions_projection(self):
        versions = registered_schema_versions()
        assert set(versions) == set(ALL_KINDS)
        _minor_bumped = (ArtifactKind.COMPONENT_MANIFEST, ArtifactKind.BRAND_PACKAGE)
        for kind in ALL_KINDS:
            if kind in _minor_bumped:
                # A1 / AES-WEB-002J.2: both 1.0.0 (field-less) and 1.1.0
                # stay registered.
                assert versions[kind] == ("1.0.0", "1.1.0")
            else:
                assert versions[kind] == ("1.0.0",)

    def test_unsupported_schema_version_rejected(self):
        with pytest.raises(UnsupportedSchemaVersionError):
            registered_artifact_model(ArtifactKind.BUSINESS_SPEC, "9.9.9")

    def test_duplicate_registration_rejected(self):
        with pytest.raises(SchemaRegistrationError):
            register_artifact_model(
                ArtifactKind.BUSINESS_SPEC, "1.0.0", SiteBundle
            )

    def test_no_thirteenth_artifact_kind(self):
        # A1 embeds the trace in ComponentManifest — no new artifact kind and
        # no independent SelectionTrace artifact (AES-WEB-002 §14.3).
        assert len(ALL_KINDS) == 12
        assert not any(
            "SELECTION" in kind.name or "TRACE" in kind.name
            for kind in ALL_KINDS
        )


def _make_selection_trace(**overrides) -> SelectionTrace:
    slot = SlotSelectionTrace(
        slot_id=overrides.get("slot_id", "hero"),
        candidates=(
            SelectionCandidate(
                component_id="hero.split.value-proposition",
                component_version="1.0.0",
                score=overrides.get("score", 150),
                score_components=(
                    SelectionScoreComponent(factor="preferred", points=100),
                    SelectionScoreComponent(factor="exact_intent", points=50),
                ),
            ),
            SelectionCandidate(
                component_id="hero.centered.standard",
                eliminated_by=overrides.get("eliminated_by", "commercial_purpose"),
            ),
        ),
        elimination_counts=overrides.get("elimination_counts", {"lifecycle": 3}),
        tie_break_basis=overrides.get("tie_break_basis", "score"),
        chosen_component_id="hero.split.value-proposition",
        chosen_component_version="1.0.0",
        chosen_variant=overrides.get("chosen_variant", "image-right"),
    )
    return SelectionTrace(slots=(slot,))


def _make_manifest(schema_version="1.1.0", selection_trace=None) -> ComponentManifest:
    return ComponentManifest(
        schema_version=schema_version,
        artifact_kind=ArtifactKind.COMPONENT_MANIFEST,
        source_hashes={},
        selection_trace=selection_trace,
    )


class TestComponentManifestSelectionTrace:
    """Amendment A1 — schema-versioned selection_trace (AES-WEB-002 §14.3)."""

    def test_schema_1_0_0_still_supported_and_field_less(self):
        model_cls = registered_artifact_model(
            ArtifactKind.COMPONENT_MANIFEST, "1.0.0"
        )
        assert model_cls is ComponentManifestV1
        legacy = ComponentManifestV1(
            schema_version="1.0.0",
            artifact_kind=ArtifactKind.COMPONENT_MANIFEST,
            source_hashes={},
        )
        # 1.0.0 serialization is byte-identical to the pre-amendment shape:
        # no selection_trace key at all (the canonical serializer emits None
        # as null, so a field-less 1.0.0 model is required for replay).
        assert "selection_trace" not in canonical_artifact_json(legacy)

    def test_schema_1_1_0_is_registered(self):
        model_cls = registered_artifact_model(
            ArtifactKind.COMPONENT_MANIFEST, "1.1.0"
        )
        assert model_cls is ComponentManifest

    def test_selection_trace_is_optional(self):
        manifest = _make_manifest(selection_trace=None)
        assert manifest.selection_trace is None
        # Optional but explicit: absence serializes as null, never dropped.
        assert '"selection_trace":null' in canonical_artifact_json(manifest)

    def test_valid_typed_trace_serializes_deterministically(self):
        a = _make_manifest(selection_trace=_make_selection_trace())
        b = _make_manifest(selection_trace=_make_selection_trace())
        assert canonical_artifact_json(a) == canonical_artifact_json(b)
        assert '"selection_trace"' in canonical_artifact_json(a)

    def test_same_trace_same_hash(self):
        a = _make_manifest(selection_trace=_make_selection_trace())
        b = _make_manifest(selection_trace=_make_selection_trace())
        assert artifact_sha256(a) == artifact_sha256(b)

    def test_changed_filtering_changes_hash(self):
        base = artifact_sha256(_make_manifest(selection_trace=_make_selection_trace()))
        changed = artifact_sha256(
            _make_manifest(
                selection_trace=_make_selection_trace(
                    elimination_counts={"lifecycle": 4}
                )
            )
        )
        assert base != changed

    def test_changed_scoring_changes_hash(self):
        base = artifact_sha256(_make_manifest(selection_trace=_make_selection_trace()))
        changed = artifact_sha256(
            _make_manifest(selection_trace=_make_selection_trace(score=140))
        )
        assert base != changed

    def test_changed_tiebreak_changes_hash(self):
        base = artifact_sha256(_make_manifest(selection_trace=_make_selection_trace()))
        changed = artifact_sha256(
            _make_manifest(
                selection_trace=_make_selection_trace(tie_break_basis="component_id")
            )
        )
        assert base != changed

    def test_unsupported_manifest_version_fails(self):
        with pytest.raises(UnsupportedSchemaVersionError):
            registered_artifact_model(
                ArtifactKind.COMPONENT_MANIFEST, "2.0.0"
            )

    def test_trace_rejects_arbitrary_fields(self):
        # extra="forbid" on every frozen model — no untyped fields (A1 #12).
        with pytest.raises(Exception):
            SelectionTrace(slots=(), bogus=1)
        with pytest.raises(Exception):
            SlotSelectionTrace(slot_id="x", bogus="nope")
        with pytest.raises(Exception):
            _make_manifest(selection_trace={"bogus": 1})

    def test_trace_models_are_frozen(self):
        trace = _make_selection_trace()
        with pytest.raises(Exception):
            trace.schema_version = "9.9.9"
        with pytest.raises(Exception):
            trace.slots[0].slot_id = "changed"

    def test_no_floats_in_scores(self):
        # Integer scoring only (§14.2 step 6); floats are rejected by the
        # canonical serializer.
        component = SelectionScoreComponent(factor="preferred", points=100)
        assert isinstance(component.points, int)


def _make_brand_package(schema_version="1.1.0", **overrides) -> BrandPackage:
    fields = dict(
        schema_version=schema_version,
        artifact_kind=ArtifactKind.BRAND_PACKAGE,
        source_hashes={},
        palette={"color.text.default": "#23312a"},
        type_scale={"typography.body.default": "400 16px/1.5 sans-serif"},
        spacing_scale={"spacing.stack.default": "16px"},
        voice_profile="deterministic voice",
        asset_hashes={},
        radius_scale={"radius.card": "10px"},
        extended_tokens={"breakpoint.sm": "640px"},
        contrast_evidence=(
            ContrastEvidence(
                foreground_token="color.text.default",
                background_token="color.surface.page",
                contrast_ratio_hundredths=1271,
                required_hundredths=450,
                passed=True,
            ),
        ),
    )
    fields.update(overrides)
    return BrandPackage(**fields)


class TestBrandPackageSchema:
    """AES-WEB-002J.2 — additive-minor BrandPackage schema (AES-WEB-001 §5.2)."""

    def test_schema_1_0_0_still_supported_and_field_less(self):
        model_cls = registered_artifact_model(ArtifactKind.BRAND_PACKAGE, "1.0.0")
        assert model_cls is BrandPackageV1
        legacy = BrandPackageV1(
            schema_version="1.0.0",
            artifact_kind=ArtifactKind.BRAND_PACKAGE,
            source_hashes={},
        )
        # 1.0.0 serialization is byte-identical to the pre-Phase-2 shape:
        # none of the Phase 2 keys exist at all (the canonical serializer
        # emits None as null, so a field-less 1.0.0 model is required for
        # replay — same reasoning as ComponentManifestV1).
        text = canonical_artifact_json(legacy)
        assert "radius_scale" not in text
        assert "extended_tokens" not in text
        assert "contrast_evidence" not in text

    def test_schema_1_1_0_is_registered(self):
        model_cls = registered_artifact_model(ArtifactKind.BRAND_PACKAGE, "1.1.0")
        assert model_cls is BrandPackage

    def test_new_fields_default_empty(self):
        package = BrandPackage(
            schema_version="1.1.0",
            artifact_kind=ArtifactKind.BRAND_PACKAGE,
            source_hashes={},
        )
        assert package.radius_scale == {}
        assert package.extended_tokens == {}
        assert package.contrast_evidence == ()

    def test_canonical_round_trip_is_stable(self):
        a = _make_brand_package()
        b = _make_brand_package()
        assert canonical_artifact_json(a) == canonical_artifact_json(b)
        assert artifact_sha256(a) == artifact_sha256(b)

    def test_changed_contrast_evidence_changes_hash(self):
        base = artifact_sha256(_make_brand_package())
        changed = artifact_sha256(
            _make_brand_package(
                contrast_evidence=(
                    ContrastEvidence(
                        foreground_token="color.text.default",
                        background_token="color.surface.page",
                        contrast_ratio_hundredths=999,
                        required_hundredths=450,
                        passed=True,
                    ),
                )
            )
        )
        assert base != changed

    def test_unsupported_brand_package_version_fails(self):
        with pytest.raises(UnsupportedSchemaVersionError):
            registered_artifact_model(ArtifactKind.BRAND_PACKAGE, "2.0.0")

    def test_brand_package_is_frozen(self):
        package = _make_brand_package()
        with pytest.raises(Exception):
            package.voice_profile = "changed"
        with pytest.raises(Exception):
            package.contrast_evidence[0].passed = False

    def test_contrast_evidence_rejects_arbitrary_fields(self):
        # extra="forbid" on every frozen model (§4.4).
        with pytest.raises(Exception):
            ContrastEvidence(
                foreground_token="color.text.default",
                background_token="color.surface.page",
                contrast_ratio_hundredths=1271,
                required_hundredths=450,
                passed=True,
                bogus=1,
            )

    def test_no_floats_reach_canonical_brand_artifact(self):
        # The shared canonicalizer (contracts/artifacts.py) actively rejects
        # floats anywhere in the payload, including the new Phase 2 fields —
        # not merely "happens not to contain one" (mirrors
        # TestComponentContracts.test_no_floats_present's injection style).
        payload = model_to_dict(_make_brand_package())
        payload["extended_tokens"]["breakpoint.sm"] = 640.0
        with pytest.raises(ArtifactCanonicalizationError):
            canonical_json(payload)


class TestFrozenBehavior:
    def test_artifacts_are_frozen(self):
        spec = _make_spec()
        with pytest.raises(Exception):
            spec.business_name = "Changed"

    def test_header_fields_are_mandatory(self):
        with pytest.raises(Exception):
            BusinessSpec(  # no header fields supplied
                business_name="x",
                niche="y",
                audience="z",
                value_proposition="w",
            )

    def test_extra_fields_are_forbidden(self):
        with pytest.raises(Exception):
            _make_spec(unexpected_field="nope")

    def test_every_kind_constructs_with_minimal_payload(self):
        constructors = {
            ArtifactKind.BUSINESS_SPEC: lambda h: _make_spec(),
            ArtifactKind.BRAND_PACKAGE: lambda h: BrandPackage(**h),
            ArtifactKind.SITE_ARCHITECTURE: lambda h: SiteArchitecture(**h),
            ArtifactKind.CONTENT_CANDIDATE: lambda h: ContentCandidate(
                page_route="/", slot_id="hero", body="text", **h
            ),
            ArtifactKind.CONTENT_PACKAGE: lambda h: ContentPackage(**h),
            ArtifactKind.COMPONENT_MANIFEST: lambda h: ComponentManifest(**h),
            ArtifactKind.LAYOUT_PLAN: lambda h: LayoutPlan(**h),
            ArtifactKind.RENDERED_PAGE_SET: lambda h: RenderedPageSet(**h),
            ArtifactKind.SEO_PACKAGE: lambda h: SEOPackage(**h),
            ArtifactKind.SITE_BUNDLE: lambda h: SiteBundle(**h),
            ArtifactKind.QUALITY_REPORT: lambda h: QualityReport(**h),
            ArtifactKind.BUILD_MANIFEST: lambda h: BuildManifest(
                build_id="b" * 64,
                pipeline_version="1.0.0",
                final_state=BuildState.SPEC_COMPILED,
                **h,
            ),
        }
        for kind in ALL_KINDS:
            header = dict(
                schema_version="1.0.0",
                artifact_kind=kind,
                source_hashes={},
            )
            artifact = constructors[kind](header)
            assert artifact.artifact_kind == kind
            assert artifact.schema_version == "1.0.0"
            assert isinstance(artifact.source_hashes, dict)


class TestCanonicalSerialization:
    def test_sorted_keys_no_insignificant_whitespace(self):
        text = canonical_json({"b": 1, "a": {"z": None, "y": 2}})
        assert text == '{"a":{"y":2,"z":null},"b":1}'

    def test_null_handling_is_explicit(self):
        record = json.loads(canonical_artifact_json(
            QualityReport(
                schema_version="1.0.0",
                artifact_kind=ArtifactKind.QUALITY_REPORT,
                source_hashes={},
            )
        ))
        assert record["certificate"] is None  # never silently dropped

    def test_serialization_stable_across_construction_order(self):
        spec_a = _make_spec()
        spec_b = BusinessSpec(
            value_proposition="verified pet-friendly stays",
            business_name="Pet Trip Finder",
            source_hashes={"external:project": "a" * 64},
            artifact_kind=ArtifactKind.BUSINESS_SPEC,
            schema_version="1.0.0",
            niche="pet travel",
            audience="pet owners",
            directory_taxonomy=("hotels", "parks"),
        )
        assert canonical_artifact_json(spec_a) == canonical_artifact_json(
            spec_b
        )

    def test_enum_values_serialize_as_strings(self):
        payload = json.loads(canonical_artifact_json(_make_spec()))
        assert payload["artifact_kind"] == "BUSINESS_SPEC"


class TestContentIdentity:
    def test_identical_artifacts_yield_identical_hashes(self):
        assert artifact_sha256(_make_spec()) == artifact_sha256(_make_spec())

    def test_changed_payload_yields_changed_hash(self):
        base = artifact_sha256(_make_spec())
        changed = artifact_sha256(_make_spec(niche="dog travel"))
        assert base != changed

    def test_hash_is_sha256_hex(self):
        digest = artifact_sha256(_make_spec())
        assert len(digest) == 64
        int(digest, 16)  # parses as hex
