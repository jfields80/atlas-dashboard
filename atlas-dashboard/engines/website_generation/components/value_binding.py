"""Phase-B literal-prop value binding (AES-WEB-002J.19;
ADR-WEB-CONTENT-BINDING-MAP; AES-WEB-001 §5.5).

Binds every ``PROP_LITERAL``-kind :class:`BindingRule` (STR_ENUM,
INT_BOUNDED, BOOL, ROUTE_REF, TOKEN_REF, ASSET_REF, A11Y_LABEL) to a literal
string value, following the J.18 rule's declared source -- never generic
"first value" guessing. Reference props (CONTENT_BLOCK_REF/LISTING_REF) are
resolved by :mod:`content_projection`, not here (their value is a slot id,
not a literal).

Pure: no I/O, no clock, no randomness, no AI. Every function either returns
a bound string or raises :class:`UnboundLiteralProp` (an internal signal
caught by the Component Engine's batch collector -- never escapes this
module boundary uncaught in normal operation, mirroring
``component_engine._UnbindableRoleProp``'s existing convention).
"""

from __future__ import annotations

from typing import Optional

from engines.website_generation.contracts.artifacts import BrandPackage, SiteArchitecture
from engines.website_generation.contracts.components import PropSpec
from engines.website_generation.contracts.enums import PageRole, PropType
from engines.website_generation.components.binding_rules import BindingRule

# Every PageRole value, precomputed once (mirrors the pre-J.19
# component_engine._PAGE_ROLE_VALUES precedent). A STR_ENUM prop whose enum
# is a subset of these is "role-typed": it specifically encodes the hosting
# page's role, so a mismatch is a genuine §5.5 compile-time contradiction
# (hard failure), never a silent default -- unlike an ordinary STR_ENUM
# (density, severity, ...), where the first declared value is a safe default.
_PAGE_ROLE_VALUES = frozenset(role.value for role in PageRole)


class UnboundLiteralProp(Exception):
    """Internal: a PROP_LITERAL rule could not be bound. Never escapes the
    Component Engine's batch collector uncaught."""

    def __init__(self, field_name: str, reason: str) -> None:
        super().__init__(field_name, reason)
        self.field_name = field_name
        self.reason = reason


def bind_literal_prop(
    rule: BindingRule,
    prop_spec: PropSpec,
    *,
    role: PageRole,
    route: str,
    site_architecture: SiteArchitecture,
    brand_package: Optional[BrandPackage],
) -> str:
    """Bind one literal prop to its value per the J.18 rule's source, then
    validate it against the component's own ``PropSpec`` contract.

    Raises :class:`UnboundLiteralProp` naming exactly why (missing source
    artifact, no valid value, out-of-contract value) -- never silently
    substitutes a placeholder.
    """
    prop_type = prop_spec.prop_type

    if prop_type is PropType.STR_ENUM:
        value = _bind_str_enum(rule, prop_spec, role=role)
    elif prop_type is PropType.INT_BOUNDED:
        value = _bind_int_bounded(rule, prop_spec)
    elif prop_type is PropType.BOOL:
        value = _bind_bool(rule, prop_spec)
    elif prop_type is PropType.ROUTE_REF:
        value = _bind_route_ref(rule, site_architecture)
    elif prop_type is PropType.TOKEN_REF:
        value = _bind_token_ref(rule, brand_package)
    elif prop_type is PropType.ASSET_REF:
        value = _bind_asset_ref(rule, brand_package)
    elif prop_type is PropType.A11Y_LABEL:
        value = _bind_a11y_label(rule, route=route)
    else:
        raise UnboundLiteralProp(
            rule.field_name, "prop_type %r is not a literal binding" % prop_type.value
        )

    return value


def _bind_str_enum(rule: BindingRule, prop_spec: PropSpec, *, role: PageRole) -> str:
    if not prop_spec.enum_values:
        raise UnboundLiteralProp(rule.field_name, "invalid_source_field: no enum_values declared")
    is_role_typed = set(prop_spec.enum_values) <= _PAGE_ROLE_VALUES
    if is_role_typed:
        # The pre-J.19 §5.5 convention, preserved exactly: a role-typed prop
        # whose enum excludes the hosting role is a compile-time
        # contradiction -- never silently defaulted to another role's value.
        if role.value not in prop_spec.enum_values:
            raise UnboundLiteralProp(
                rule.field_name,
                "invalid_prop_value: hosting role %r not in role-typed enum %r"
                % (role.value, prop_spec.enum_values),
            )
        return role.value
    return prop_spec.enum_values[0]


def _bind_int_bounded(rule: BindingRule, prop_spec: PropSpec) -> str:
    if prop_spec.default is not None:
        value = prop_spec.default
    elif prop_spec.int_min is not None:
        value = str(prop_spec.int_min)
    else:
        raise UnboundLiteralProp(
            rule.field_name, "invalid_source_field: no default or int_min declared"
        )
    try:
        parsed = int(value)
    except ValueError:
        raise UnboundLiteralProp(rule.field_name, "invalid_prop_value: %r not an int" % value)
    lo, hi = prop_spec.int_min, prop_spec.int_max
    if (lo is not None and parsed < lo) or (hi is not None and parsed > hi):
        raise UnboundLiteralProp(
            rule.field_name, "invalid_prop_value: %d outside [%r, %r]" % (parsed, lo, hi)
        )
    return str(parsed)


def _bind_bool(rule: BindingRule, prop_spec: PropSpec) -> str:
    default = prop_spec.default if prop_spec.default is not None else "false"
    if default not in ("true", "false"):
        raise UnboundLiteralProp(
            rule.field_name, "invalid_prop_value: %r is not a bool literal" % default
        )
    return default


def _bind_route_ref(rule: BindingRule, site_architecture: SiteArchitecture) -> str:
    routes = {p.route for p in site_architecture.pages}
    if not routes:
        raise UnboundLiteralProp(rule.field_name, "missing_source_artifact: no SiteArchitecture routes")
    # Deterministic choice: the first route in the architecture's declared
    # (stable) page order.
    return site_architecture.pages[0].route


def _bind_token_ref(rule: BindingRule, brand_package: Optional[BrandPackage]) -> str:
    if brand_package is None:
        raise UnboundLiteralProp(rule.field_name, "missing_source_artifact: brand_package not supplied")
    tokens = {}
    tokens.update(brand_package.palette)
    tokens.update(brand_package.type_scale)
    tokens.update(brand_package.spacing_scale)
    tokens.update(brand_package.radius_scale)
    tokens.update(brand_package.extended_tokens)
    if not tokens:
        raise UnboundLiteralProp(rule.field_name, "missing_source_artifact: brand_package has no tokens")
    # Deterministic choice: the lexicographically first declared token id.
    return sorted(tokens)[0]


def _bind_asset_ref(rule: BindingRule, brand_package: Optional[BrandPackage]) -> str:
    if brand_package is None or not brand_package.asset_hashes:
        raise UnboundLiteralProp(rule.field_name, "unavailable_source: no asset store available")
    return sorted(brand_package.asset_hashes.values())[0]


def _bind_a11y_label(rule: BindingRule, *, route: str) -> str:
    # Deterministic, non-empty, route-derived literal label -- never a
    # business-fact fabrication (a11y labels are structural, not editorial).
    return "%s label" % rule.field_name.replace("_", " ")
