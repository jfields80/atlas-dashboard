"""Brand token coverage against the live component registry (AES-WEB-001 §5.2).

The required token set is the union of every registered component's
``design_token_dependencies`` — derived live from ``REGISTERED_COMPONENTS``,
never hardcoded, so a future catalog wave that adds a new token dependency
is caught here automatically rather than silently under-covered.
"""

from __future__ import annotations

from engines.website_generation.components import REGISTERED_COMPONENTS
from engines.website_generation.constants.brand import (
    TOKEN_PREFIX_COLOR,
    TOKEN_PREFIX_RADIUS,
    TOKEN_PREFIX_SPACING,
    TOKEN_PREFIX_TYPOGRAPHY,
    FAMILY_ORDER,
)
from engines.website_generation.brand.token_resolver import (
    build_extended_tokens,
    build_palette_tokens,
    build_radius_tokens,
    build_spacing_tokens,
    build_type_scale_tokens,
)


def _required_token_ids():
    required = set()
    for definition in REGISTERED_COMPONENTS:
        required.update(definition.design_token_dependencies)
    return required


def _resolved_fields(family: str):
    return {
        "palette": build_palette_tokens(family),
        "type_scale": build_type_scale_tokens(family),
        "spacing_scale": build_spacing_tokens(),
        "radius_scale": build_radius_tokens(family),
        "extended_tokens": build_extended_tokens(family),
    }


class TestRequiredTokenSet:
    def test_registry_derived_total_is_54(self):
        # Not hardcoded as the source of truth — recomputed live from the
        # registry every run; 54 is the expected, independently verified
        # count for the current 72-component catalog.
        assert len(_required_token_ids()) == 54

    def test_required_set_is_non_empty_and_stable_across_calls(self):
        first = _required_token_ids()
        second = _required_token_ids()
        assert first == second
        assert first


class TestCoveragePerFamily:
    def test_every_family_resolves_every_required_token(self):
        required = _required_token_ids()
        for family in FAMILY_ORDER:
            fields = _resolved_fields(family)
            resolved = set()
            for group in fields.values():
                resolved.update(group.keys())
            missing = required - resolved
            assert not missing, "%s missing tokens: %s" % (family, sorted(missing))

    def test_every_family_resolves_to_exactly_the_required_set(self):
        # No under-coverage AND no accidental drift into unrequired ids.
        required = _required_token_ids()
        for family in FAMILY_ORDER:
            fields = _resolved_fields(family)
            resolved = set()
            for group in fields.values():
                resolved.update(group.keys())
            assert resolved == required, family

    def test_no_token_id_resolves_in_more_than_one_field(self):
        for family in FAMILY_ORDER:
            fields = _resolved_fields(family)
            seen = {}
            for field_name, group in fields.items():
                for token_id in group:
                    assert token_id not in seen, (
                        "%s resolved in both %s and %s (%s)"
                        % (token_id, seen.get(token_id), field_name, family)
                    )
                    seen[token_id] = field_name

    def test_token_prefix_routes_to_the_declared_field(self):
        # §5.2 mapping: color.* -> palette, typography.* -> type_scale,
        # spacing.* -> spacing_scale, radius.* -> radius_scale, everything
        # else -> extended_tokens.
        for family in FAMILY_ORDER:
            fields = _resolved_fields(family)
            for token_id in fields["palette"]:
                assert token_id.startswith(TOKEN_PREFIX_COLOR)
            for token_id in fields["type_scale"]:
                assert token_id.startswith(TOKEN_PREFIX_TYPOGRAPHY)
            for token_id in fields["spacing_scale"]:
                assert token_id.startswith(TOKEN_PREFIX_SPACING)
            for token_id in fields["radius_scale"]:
                assert token_id.startswith(TOKEN_PREFIX_RADIUS)
            for token_id in fields["extended_tokens"]:
                assert not token_id.startswith(TOKEN_PREFIX_COLOR)
                assert not token_id.startswith(TOKEN_PREFIX_TYPOGRAPHY)
                assert not token_id.startswith(TOKEN_PREFIX_SPACING)
                assert not token_id.startswith(TOKEN_PREFIX_RADIUS)
