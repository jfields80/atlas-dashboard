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
    LayoutPlan,
    QualityReport,
    RenderedPageSet,
    SEOPackage,
    SchemaRegistrationError,
    SiteArchitecture,
    SiteBundle,
    UnsupportedSchemaVersionError,
    artifact_sha256,
    canonical_artifact_json,
    canonical_json,
    registered_artifact_model,
    registered_schema_versions,
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

    def test_schema_versions_map_covers_every_kind_at_v1(self):
        assert set(SCHEMA_VERSIONS) == set(ALL_KINDS)
        assert all(v == "1.0.0" for v in SCHEMA_VERSIONS.values())

    def test_registered_schema_versions_projection(self):
        versions = registered_schema_versions()
        assert set(versions) == set(ALL_KINDS)
        for kind in ALL_KINDS:
            assert versions[kind] == ("1.0.0",)

    def test_unsupported_schema_version_rejected(self):
        with pytest.raises(UnsupportedSchemaVersionError):
            registered_artifact_model(ArtifactKind.BUSINESS_SPEC, "9.9.9")

    def test_duplicate_registration_rejected(self):
        with pytest.raises(SchemaRegistrationError):
            register_artifact_model(
                ArtifactKind.BUSINESS_SPEC, "1.0.0", SiteBundle
            )

    def test_component_manifest_remains_v1_with_no_selection_trace(self):
        # AES-WEB-002A is explicitly deferred: schema 1.0.0, no trace field.
        assert SCHEMA_VERSIONS[ArtifactKind.COMPONENT_MANIFEST] == "1.0.0"
        manifest = ComponentManifest(
            schema_version="1.0.0",
            artifact_kind=ArtifactKind.COMPONENT_MANIFEST,
            source_hashes={},
        )
        assert "selection_trace" not in canonical_artifact_json(manifest)
        with pytest.raises(Exception):
            ComponentManifest(
                schema_version="1.0.0",
                artifact_kind=ArtifactKind.COMPONENT_MANIFEST,
                source_hashes={},
                selection_trace={},
            )


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
