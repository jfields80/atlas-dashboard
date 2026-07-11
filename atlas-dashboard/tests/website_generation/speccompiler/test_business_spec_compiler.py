"""BusinessSpecCompiler tests (AES-WEB-001 §5.1).

Covers: valid compile, deterministic output, batch missing-field
diagnostics, and no mutation of input.
"""

from __future__ import annotations

import pytest

from engines.website_generation import (
    ArtifactKind,
    BusinessSpecCompiler,
    SpecCompilationError,
    SpecCompilerInput,
    artifact_sha256,
    canonical_artifact_json,
)


class TestValidCompile:
    def test_compiles_golden_input(self, golden_compiler_input):
        spec = BusinessSpecCompiler().compile(golden_compiler_input)
        assert spec.artifact_kind == ArtifactKind.BUSINESS_SPEC
        assert spec.schema_version == "1.0.0"
        assert spec.business_name == "Pet Trip Finder"
        assert spec.niche == "pet-friendly travel"

    def test_source_hashes_carried_from_upstream(self, golden_compiler_input):
        spec = BusinessSpecCompiler().compile(golden_compiler_input)
        assert spec.source_hashes == dict(
            golden_compiler_input.upstream_hashes
        )

    def test_whitespace_is_normalized(self):
        spec = BusinessSpecCompiler().compile(
            SpecCompilerInput(
                business_name="  Pet   Trip  Finder ",
                niche=" travel ",
                audience=" owners ",
                value_proposition=" stays\n fast ",
            )
        )
        assert spec.business_name == "Pet Trip Finder"
        assert spec.value_proposition == "stays fast"

    def test_taxonomy_is_stable_sorted(self, golden_compiler_input):
        spec = BusinessSpecCompiler().compile(golden_compiler_input)
        assert spec.directory_taxonomy == ("hotels", "parks", "restaurants")

    def test_legal_footer_order_preserved(self, golden_compiler_input):
        spec = BusinessSpecCompiler().compile(golden_compiler_input)
        assert spec.legal_footer_facts == (
            "Operated by Atlas Holdings",
            "Listings verified quarterly",
        )


class TestDeterminism:
    def test_same_input_same_output_hash(self, golden_compiler_input):
        compiler = BusinessSpecCompiler()
        first = compiler.compile(golden_compiler_input)
        second = compiler.compile(golden_compiler_input)
        assert canonical_artifact_json(first) == canonical_artifact_json(
            second
        )
        assert artifact_sha256(first) == artifact_sha256(second)

    def test_fresh_compiler_instance_same_hash(self, golden_compiler_input):
        first = BusinessSpecCompiler().compile(golden_compiler_input)
        second = BusinessSpecCompiler().compile(golden_compiler_input)
        assert artifact_sha256(first) == artifact_sha256(second)


class TestBatchMissingFieldDiagnostics:
    def test_all_missing_fields_reported_at_once(self):
        with pytest.raises(SpecCompilationError) as excinfo:
            BusinessSpecCompiler().compile(SpecCompilerInput())
        missing = excinfo.value.missing_fields
        assert set(missing) == {
            "business_name",
            "niche",
            "audience",
            "value_proposition",
        }

    def test_whitespace_only_counts_as_missing(self):
        with pytest.raises(SpecCompilationError) as excinfo:
            BusinessSpecCompiler().compile(
                SpecCompilerInput(
                    business_name="   ",
                    niche="travel",
                    audience="owners",
                    value_proposition="stays",
                )
            )
        assert excinfo.value.missing_fields == ("business_name",)

    def test_error_is_terminal_not_retryable(self):
        with pytest.raises(SpecCompilationError) as excinfo:
            BusinessSpecCompiler().compile(SpecCompilerInput())
        assert excinfo.value.retryable is False
        assert excinfo.value.stage == "spec_compilation"

    def test_non_contract_input_rejected(self):
        with pytest.raises(SpecCompilationError):
            BusinessSpecCompiler().compile({"business_name": "x"})


class TestNoInputMutation:
    def test_input_is_unchanged_after_compile(self, golden_compiler_input):
        before = canonical_artifact_json(golden_compiler_input)
        BusinessSpecCompiler().compile(golden_compiler_input)
        after = canonical_artifact_json(golden_compiler_input)
        assert before == after

    def test_input_contract_is_frozen(self, golden_compiler_input):
        with pytest.raises(Exception):
            golden_compiler_input.business_name = "Mutated"
