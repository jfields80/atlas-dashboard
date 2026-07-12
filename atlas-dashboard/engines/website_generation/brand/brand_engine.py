"""BrandEngine — BusinessSpec -> BrandPackage (AES-WEB-001 §5.2 / Part 2).

Deterministic, pure, serializable, byte-stable: the same ``BusinessSpec``
always produces the same ``BrandPackage``. No network access, no filesystem
access, no model calls, no randomness, no clock-dependent behavior (§5.2).
Not wired into pipeline execution — ``brand_resolution`` remains
``NOT_EXECUTED`` in the ``BuildManifest`` (``PHASE1_EXECUTED_STAGES`` is
unchanged by this module).
"""

from __future__ import annotations

from typing import List

from engines.website_generation.contracts.artifacts import (
    BrandPackage,
    BusinessSpec,
    artifact_sha256,
)
from engines.website_generation.contracts.enums import ArtifactKind
from engines.website_generation.contracts.errors import BrandResolutionError
from engines.website_generation.contracts.interfaces import BrandEngineInterface
from engines.website_generation.contracts.versions import (
    ENGINE_VERSIONS,
    SCHEMA_VERSIONS,
)

from engines.website_generation.brand.token_resolver import (
    build_contrast_evidence,
    build_extended_tokens,
    build_palette_tokens,
    build_radius_tokens,
    build_spacing_tokens,
    build_type_scale_tokens,
    build_voice_profile,
    resolve_family,
)

_REQUIRED_FIELDS = ("business_name", "niche", "audience", "value_proposition")


def _normalized(value: str) -> str:
    """Whitespace-normalized scalar text: stripped, inner runs collapsed."""
    return " ".join(str(value).split())


class BrandEngine(BrandEngineInterface):
    """Resolve a canonical ``BusinessSpec`` into a deterministic ``BrandPackage``."""

    version = ENGINE_VERSIONS["brand_engine"]

    def resolve(self, spec: BusinessSpec) -> BrandPackage:
        """Total function over valid specs; batch-fails otherwise.

        Deterministic guarantees: the input is never mutated (it is
        frozen); family classification, token resolution, and contrast
        evidence are pure functions of ``spec``'s content only.
        """
        self._validate(spec)

        family = resolve_family(spec)
        contrast_evidence = build_contrast_evidence(family)
        self._revalidate_contrast(contrast_evidence)

        return BrandPackage(
            schema_version=SCHEMA_VERSIONS[ArtifactKind.BRAND_PACKAGE],
            artifact_kind=ArtifactKind.BRAND_PACKAGE,
            source_hashes={"business_spec": artifact_sha256(spec)},
            palette=build_palette_tokens(family),
            type_scale=build_type_scale_tokens(family),
            spacing_scale=build_spacing_tokens(),
            voice_profile=build_voice_profile(spec, family),
            asset_hashes={},
            radius_scale=build_radius_tokens(family),
            extended_tokens=build_extended_tokens(family),
            contrast_evidence=contrast_evidence,
        )

    @staticmethod
    def _validate(spec: BusinessSpec) -> None:
        """Require non-empty normalized required fields (§5.2), batch-reported."""
        missing: List[str] = []
        for field_name in _REQUIRED_FIELDS:
            if not _normalized(getattr(spec, field_name, "")):
                missing.append(field_name)
        if missing:
            raise BrandResolutionError(
                "BrandPackage resolution failed; missing required fields: "
                + ", ".join(missing),
                diagnostics={"missing_fields": missing},
            )

    @staticmethod
    def _revalidate_contrast(evidence) -> None:
        """Re-verify every sanctioned pair at resolution time (§5.2).

        An internal-consistency guarantee, not a spec-input validation: a
        failure here means an authored palette regressed, not that the
        caller's spec was invalid.
        """
        failed = [record for record in evidence if not record.passed]
        if failed:
            raise BrandResolutionError(
                "sanctioned contrast pair(s) failed WCAG revalidation",
                diagnostics={
                    "failed_pairs": [
                        {
                            "foreground_token": record.foreground_token,
                            "background_token": record.background_token,
                            "contrast_ratio_hundredths": record.contrast_ratio_hundredths,
                            "required_hundredths": record.required_hundredths,
                        }
                        for record in failed
                    ]
                },
            )
