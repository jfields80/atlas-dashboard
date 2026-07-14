"""Phase-B value-binding unit tests (AES-WEB-002J.19;
ADR-WEB-CONTENT-BINDING-MAP): ``value_binding.py`` (literal props) and
``content_projection.py`` (content slots, ref props, listing/derived
projections, route scope, generated slot ids, collision detection).

Exercises the real J.18 ``BindingRule``s and real registry ``PropSpec``s
wherever practical -- these are unit tests of the binding primitives
themselves, not of ``ComponentEngine.compile()`` (see
``test_component_engine_binding.py`` for the integrated Phase-B behavior).
"""

from __future__ import annotations

import pytest

from engines.website_generation.brand.brand_engine import BrandEngine
from engines.website_generation.components.binding_rules import BINDING_RULES_BY_KEY
from engines.website_generation.components.registry import build_default_registry
from engines.website_generation.components import content_projection as cproj
from engines.website_generation.components import value_binding as vb
from engines.website_generation.contracts.artifacts import (
    BusinessSpec,
    ContentBlock,
    ListingAddress,
    ListingCategory,
    ListingContact,
    ListingDataset,
    ListingHoursEntry,
    ListingRating,
    ListingRecord,
    ListingSponsorship,
    PagePlan,
    SiteArchitecture,
)
from engines.website_generation.contracts.enums import ArtifactKind, ListingKind, PageRole, Weekday
from engines.website_generation.contracts.versions import SCHEMA_VERSIONS

_REGISTRY = build_default_registry()


def _rule(component_id, field_kind, field_name):
    return BINDING_RULES_BY_KEY[(component_id, field_kind, field_name)]


def _spec(component_id, field_name, *, required=True):
    d = _REGISTRY.get(component_id)
    table = d.required_props if required else d.optional_props
    return table[field_name]


def _sa(routes=("/",)):
    pages = tuple(PagePlan(route=r, page_type="home", title="") for r in routes)
    return SiteArchitecture(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.SITE_ARCHITECTURE],
        artifact_kind=ArtifactKind.SITE_ARCHITECTURE,
        source_hashes={}, pages=pages, nav_routes=(), sitemap_routes=routes,
    )


def _brand():
    spec = BusinessSpec(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.BUSINESS_SPEC],
        artifact_kind=ArtifactKind.BUSINESS_SPEC, source_hashes={},
        business_name="X", niche="y", audience="z", value_proposition="w",
    )
    return BrandEngine().resolve(spec)


def _category(cid="cat-hotels", slug="hotels"):
    return ListingCategory(category_id=cid, label="Hotels", slug=slug)


def _listing(**overrides):
    fields = dict(
        listing_id="lakeview-lodge", business_name="Lakeview Lodge",
        slug="lakeview-lodge", category_id="cat-hotels",
    )
    fields.update(overrides)
    return ListingRecord(**fields)


def _dataset(listings=(), categories=(_category(),), locations=()):
    return ListingDataset(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.LISTING_DATASET],
        artifact_kind=ArtifactKind.LISTING_DATASET, source_hashes={},
        listings=listings, categories=categories, locations=locations,
    )


# --------------------------------------------------------------------------- #
# A. Literal prop binding (value_binding.py)
# --------------------------------------------------------------------------- #

class TestLiteralPropBinding:
    def test_str_enum_role_typed_binds_to_hosting_role(self):
        rule = _rule("hero.local.standard", "PROP_LITERAL", "context_role")
        spec = _spec("hero.local.standard", "context_role")
        value = vb.bind_literal_prop(
            rule, spec, role=PageRole.CATEGORY, route="/c/vets", site_architecture=_sa(), brand_package=None,
        )
        assert value == "category"

    def test_str_enum_role_typed_raises_on_mismatch(self):
        rule = _rule("hero.local.standard", "PROP_LITERAL", "context_role")
        spec = _spec("hero.local.standard", "context_role")
        with pytest.raises(vb.UnboundLiteralProp) as exc:
            vb.bind_literal_prop(
                rule, spec, role=PageRole.HOME, route="/", site_architecture=_sa(), brand_package=None,
            )
        assert "invalid_prop_value" in exc.value.reason

    def test_str_enum_non_role_typed_defaults_to_first_enum_value(self):
        rule = _rule("listing.card.standard", "PROP_LITERAL", "density")
        spec = _spec("listing.card.standard", "density")
        value = vb.bind_literal_prop(
            rule, spec, role=PageRole.CATEGORY, route="/c/vets", site_architecture=_sa(), brand_package=None,
        )
        assert value == spec.enum_values[0]

    def test_int_bounded_binds_within_range(self):
        rule = _rule("directory.categories.grid", "PROP_LITERAL", "columns")
        spec = _spec("directory.categories.grid", "columns")
        value = vb.bind_literal_prop(
            rule, spec, role=PageRole.HOME, route="/", site_architecture=_sa(), brand_package=None,
        )
        parsed = int(value)
        if spec.int_min is not None:
            assert parsed >= spec.int_min
        if spec.int_max is not None:
            assert parsed <= spec.int_max

    def test_bool_binds_to_default(self):
        rule = _rule("atom.field.select", "PROP_LITERAL", "required")
        spec = _spec("atom.field.select", "required")
        value = vb.bind_literal_prop(
            rule, spec, role=PageRole.HOME, route="/", site_architecture=_sa(), brand_package=None,
        )
        assert value in ("true", "false")

    def test_route_ref_binds_to_a_real_site_architecture_route(self):
        rule = _rule("cta.claim.listing", "PROP_LITERAL", "target_route")
        spec = _spec("cta.claim.listing", "target_route")
        sa = _sa(("/", "/hotels/"))
        value = vb.bind_literal_prop(
            rule, spec, role=PageRole.HOME, route="/", site_architecture=sa, brand_package=None,
        )
        assert value in {p.route for p in sa.pages}

    def test_route_ref_fails_honestly_with_no_routes(self):
        rule = _rule("cta.claim.listing", "PROP_LITERAL", "target_route")
        spec = _spec("cta.claim.listing", "target_route")
        with pytest.raises(vb.UnboundLiteralProp) as exc:
            vb.bind_literal_prop(
                rule, spec, role=PageRole.HOME, route="/", site_architecture=_sa(()), brand_package=None,
            )
        assert "missing_source_artifact" in exc.value.reason

    def test_token_ref_binds_from_brand_package(self):
        rule = _rule("layout.grid.standard", "PROP_LITERAL", "gap")
        spec = _spec("layout.grid.standard", "gap")
        brand = _brand()
        value = vb.bind_literal_prop(
            rule, spec, role=PageRole.HOME, route="/", site_architecture=_sa(), brand_package=brand,
        )
        tokens = {}
        tokens.update(brand.palette); tokens.update(brand.type_scale)
        tokens.update(brand.spacing_scale); tokens.update(brand.radius_scale)
        tokens.update(brand.extended_tokens)
        assert value in tokens

    def test_token_ref_fails_honestly_without_brand_package(self):
        rule = _rule("layout.grid.standard", "PROP_LITERAL", "gap")
        spec = _spec("layout.grid.standard", "gap")
        with pytest.raises(vb.UnboundLiteralProp) as exc:
            vb.bind_literal_prop(
                rule, spec, role=PageRole.HOME, route="/", site_architecture=_sa(), brand_package=None,
            )
        assert "missing_source_artifact" in exc.value.reason

    def test_asset_ref_is_honestly_unavailable(self):
        rule = _rule("nav.header.standard", "PROP_LITERAL", "logo")
        spec = _spec("nav.header.standard", "logo")
        with pytest.raises(vb.UnboundLiteralProp) as exc:
            vb.bind_literal_prop(
                rule, spec, role=PageRole.HOME, route="/", site_architecture=_sa(), brand_package=_brand(),
            )
        assert "unavailable_source" in exc.value.reason

    def test_a11y_label_binds_to_a_deterministic_nonempty_literal(self):
        rule = _rule("directory.search.primary", "PROP_LITERAL", "input_label")
        spec = _spec("directory.search.primary", "input_label")
        value = vb.bind_literal_prop(
            rule, spec, role=PageRole.HOME, route="/", site_architecture=_sa(), brand_package=None,
        )
        assert value.strip()
        again = vb.bind_literal_prop(
            rule, spec, role=PageRole.HOME, route="/", site_architecture=_sa(), brand_package=None,
        )
        assert value == again  # deterministic


# --------------------------------------------------------------------------- #
# B. Route scope resolution (content_projection.py)
# --------------------------------------------------------------------------- #

class TestRouteScope:
    def test_category_route_resolves(self):
        ds = _dataset()
        scope = cproj.resolve_route_scope("/hotels/", ds)
        assert scope.category is not None and scope.category.slug == "hotels"
        assert scope.listing is None

    def test_listing_route_resolves(self):
        ds = _dataset(listings=(_listing(),))
        scope = cproj.resolve_route_scope("/hotels/lakeview-lodge/", ds)
        assert scope.listing is not None and scope.listing.listing_id == "lakeview-lodge"
        assert scope.category is not None

    def test_no_match_is_all_none(self):
        ds = _dataset(listings=(_listing(),))
        scope = cproj.resolve_route_scope("/about/", ds)
        assert scope == cproj.RouteScope(None, None, None)

    def test_no_dataset_is_all_none(self):
        assert cproj.resolve_route_scope("/hotels/", None) == cproj.RouteScope(None, None, None)

    def test_exact_match_only_no_substring(self):
        ds = _dataset(listings=(_listing(),))
        # A route that merely *contains* the listing slug must not match.
        scope = cproj.resolve_route_scope("/hotels/lakeview-lodge/extra/", ds)
        assert scope.listing is None

    def test_assign_listing_for_listing_route(self):
        ds = _dataset(listings=(_listing(),))
        scope = cproj.resolve_route_scope("/hotels/lakeview-lodge/", ds)
        assert cproj.assign_listing(scope, ds).listing_id == "lakeview-lodge"

    def test_assign_listing_for_category_route_picks_first(self):
        a = _listing(listing_id="a", slug="a")
        b = _listing(listing_id="b", slug="b")
        ds = _dataset(listings=(a, b))
        scope = cproj.resolve_route_scope("/hotels/", ds)
        assert cproj.assign_listing(scope, ds).listing_id == "a"

    def test_assign_listing_none_when_category_empty(self):
        ds = _dataset(listings=())
        scope = cproj.resolve_route_scope("/hotels/", ds)
        assert cproj.assign_listing(scope, ds) is None


# --------------------------------------------------------------------------- #
# C. Generated slot-id strategy
# --------------------------------------------------------------------------- #

class TestGeneratedSlotId:
    def test_deterministic_and_stable(self):
        a = cproj.generated_slot_id("listing_name", 4)
        b = cproj.generated_slot_id("listing_name", 4)
        assert a == b == "bind.listing_name.4"

    def test_unique_per_component_index(self):
        assert cproj.generated_slot_id("listing_name", 1) != cproj.generated_slot_id("listing_name", 2)

    def test_unique_per_semantic_slot(self):
        assert cproj.generated_slot_id("listing_name", 1) != cproj.generated_slot_id("listing_rating", 1)

    def test_no_uuid_clock_or_randomness_in_output(self):
        # Called twice in the same process at different "times" -- output
        # must be byte-identical (a real UUID/clock dependency would differ).
        import time
        first = cproj.generated_slot_id("listing_name", 9)
        time.sleep(0)  # no actual delay; just proves no time-based branching
        second = cproj.generated_slot_id("listing_name", 9)
        assert first == second


# --------------------------------------------------------------------------- #
# D. Listing / derived flat projections
# --------------------------------------------------------------------------- #

class TestListingProjection:
    def test_name_and_description(self):
        listing = _listing(description="A lakeside lodge that welcomes pets.")
        assert cproj.project_listing_value("listing_name", listing) == "Lakeview Lodge"
        assert cproj.project_listing_value("listing_description", listing) == "A lakeside lodge that welcomes pets."

    def test_contact_nap_join(self):
        listing = _listing(
            contact=ListingContact(phone="555-0100", email="stay@lakeview.example"),
            address=ListingAddress(city="Austin", state="TX"),
        )
        text = cproj.project_listing_value("listing_contact", listing)
        assert "Austin" in text and "TX" in text and "555-0100" in text and "stay@lakeview.example" in text

    def test_contact_missing_is_none(self):
        listing = _listing()
        assert cproj.project_listing_value("listing_contact", listing) is None

    def test_hours_stable_weekday_ordering(self):
        listing = _listing(hours=(
            ListingHoursEntry(day=Weekday.SUNDAY, closed=True),
            ListingHoursEntry(day=Weekday.MONDAY, opens="08:00", closes="20:00"),
        ))
        text = cproj.project_listing_value("listing_hours", listing)
        assert text.index("Mon") < text.index("Sun")  # Monday-first regardless of input order
        assert "Closed" in text

    def test_rating_integer_formatting_no_float(self):
        listing = _listing(rating=ListingRating(rating_hundredths=450, review_count=27))
        text = cproj.project_listing_value("listing_rating", listing)
        assert text == "4.50 (27 reviews)"

    def test_rating_singular_review(self):
        listing = _listing(rating=ListingRating(rating_hundredths=500, review_count=1))
        assert cproj.project_listing_value("listing_rating", listing) == "5.00 (1 review)"

    def test_rating_missing_is_none(self):
        assert cproj.project_listing_value("listing_rating", _listing()) is None

    def test_credentials_join(self):
        listing = _listing(credentials=("Licensed", "Insured"))
        assert cproj.project_listing_value("listing_credentials", listing) == "Licensed; Insured"

    def test_disclosure_requires_nonempty_text(self):
        listing = _listing(sponsorship=ListingSponsorship(kind=ListingKind.SPONSORED, disclosure_text=""))
        assert cproj.project_listing_value("listing_disclosure", listing) is None
        listing2 = _listing(sponsorship=ListingSponsorship(kind=ListingKind.SPONSORED, disclosure_text="Sponsored placement"))
        assert cproj.project_listing_value("listing_disclosure", listing2) == "Sponsored placement"

    def test_disclosure_never_fabricates_a_default(self):
        # No existing authority-defined disclosure default exists (verified
        # in the J.19 preflight) -- an empty/absent sponsorship must yield
        # None, never an invented commercial string.
        assert cproj.project_listing_value("listing_disclosure", _listing()) is None

    def test_unknown_semantic_slot_yields_none(self):
        assert cproj.project_listing_value("not_a_real_slot", _listing()) is None

    def test_result_summary_real_count(self):
        ds = _dataset(listings=(_listing(listing_id="a", slug="a"), _listing(listing_id="b", slug="b")))
        scope = cproj.resolve_route_scope("/hotels/", ds)
        assert cproj.project_derived_value("result_summary", scope, ds) == "Showing 2 listings"

    def test_result_summary_singular(self):
        ds = _dataset(listings=(_listing(),))
        scope = cproj.resolve_route_scope("/hotels/", ds)
        assert cproj.project_derived_value("result_summary", scope, ds) == "Showing 1 listing"

    def test_result_summary_zero_never_fabricated(self):
        ds = _dataset(listings=())
        scope = cproj.resolve_route_scope("/hotels/", ds)
        assert cproj.project_derived_value("result_summary", scope, ds) == "No listings found"

    def test_result_summary_no_category_scope_is_none(self):
        ds = _dataset(listings=(_listing(),))
        scope = cproj.RouteScope(None, None, None)
        assert cproj.project_derived_value("result_summary", scope, ds) is None


# --------------------------------------------------------------------------- #
# E. Existing-ContentPackage resolution
# --------------------------------------------------------------------------- #

class TestExistingContentResolution:
    def test_exact_key_resolves(self):
        rule = _rule("hero.local.standard", "CONTENT_SLOT", "intro")
        index = {("/", "intro"): ("Real intro text.",)}
        assert cproj.resolve_existing_content(rule, "/", index) == "Real intro text."

    def test_alias_key_resolves(self):
        rule = _rule("hero.local.standard", "CONTENT_SLOT", "h1")
        index = {("/", "hero_h1"): ("Real headline.",)}
        assert cproj.resolve_existing_content(rule, "/", index) == "Real headline."

    def test_missing_block_fails_honestly(self):
        rule = _rule("hero.local.standard", "CONTENT_SLOT", "h1")
        with pytest.raises(cproj.UnboundContentField) as exc:
            cproj.resolve_existing_content(rule, "/", {})
        assert "missing_source_artifact" in exc.value.reason

    def test_ambiguous_conflicting_blocks_fail(self):
        rule = _rule("hero.local.standard", "CONTENT_SLOT", "h1")
        index = {("/", "hero_h1"): ("Text A", "Text B")}
        with pytest.raises(cproj.UnboundContentField) as exc:
            cproj.resolve_existing_content(rule, "/", index)
        assert "content_alias_ambiguity" in exc.value.reason

    def test_duplicate_identical_blocks_not_ambiguous(self):
        rule = _rule("hero.local.standard", "CONTENT_SLOT", "h1")
        index = {("/", "hero_h1"): ("Same text", "Same text")}
        assert cproj.resolve_existing_content(rule, "/", index) == "Same text"


# --------------------------------------------------------------------------- #
# F. Projection accumulator (collision detection)
# --------------------------------------------------------------------------- #

class TestProjectionAccumulator:
    def test_add_and_retrieve(self):
        acc = cproj.ProjectionAccumulator()
        acc.add("/", "bind.listing_name.0", "Lakeview Lodge")
        blocks = acc.blocks()
        assert len(blocks) == 1
        assert blocks[0].page_route == "/" and blocks[0].slot_id == "bind.listing_name.0"
        assert blocks[0].text == "Lakeview Lodge"

    def test_idempotent_reprojection_same_text(self):
        acc = cproj.ProjectionAccumulator()
        acc.add("/", "name", "Lakeview Lodge")
        acc.add("/", "name", "Lakeview Lodge")  # identical -- no error
        assert len(acc.blocks()) == 1

    def test_conflicting_text_at_same_key_raises(self):
        acc = cproj.ProjectionAccumulator()
        acc.add("/", "name", "Lakeview Lodge")
        with pytest.raises(cproj.ProjectedSlotCollision) as exc:
            acc.add("/", "name", "Different Name")
        assert exc.value.route == "/" and exc.value.slot_id == "name"

    def test_same_slot_id_different_route_no_collision(self):
        acc = cproj.ProjectionAccumulator()
        acc.add("/a/", "name", "A")
        acc.add("/b/", "name", "B")
        assert len(acc.blocks()) == 2

    def test_blocks_preserve_insertion_order(self):
        acc = cproj.ProjectionAccumulator()
        acc.add("/", "z", "1")
        acc.add("/", "a", "2")
        assert [b.slot_id for b in acc.blocks()] == ["z", "a"]


# --------------------------------------------------------------------------- #
# G. Orchestration: bind_content_slot / bind_ref_prop
# --------------------------------------------------------------------------- #

class TestOrchestration:
    def test_bind_content_slot_reuses_existing_block_verbatim(self):
        rule = _rule("hero.local.standard", "CONTENT_SLOT", "intro")
        index = {("/", "intro"): ("Real intro.",)}
        acc = cproj.ProjectionAccumulator()
        token = cproj.bind_content_slot(
            rule, "intro", "/",
            content_index=index, listing_dataset=None, route_scope=cproj.RouteScope(None, None, None),
            projection=acc,
        )
        assert token == "intro"
        assert acc.blocks() == ()  # no new projection needed -- already present

    def test_bind_content_slot_projects_alias_copy(self):
        rule = _rule("hero.local.standard", "CONTENT_SLOT", "h1")
        index = {("/", "hero_h1"): ("Real headline.",)}
        acc = cproj.ProjectionAccumulator()
        token = cproj.bind_content_slot(
            rule, "h1", "/",
            content_index=index, listing_dataset=None, route_scope=cproj.RouteScope(None, None, None),
            projection=acc,
        )
        assert token == "h1"
        assert acc.blocks() == (ContentBlock(page_route="/", slot_id="h1", text="Real headline."),)

    def test_bind_ref_prop_generates_listing_aware_slot_id(self):
        # AES-WEB-002J.20 supersedes the AES-WEB-002J.19 positional
        # bind.<semantic>.<component_index> form for LISTING_DATASET-sourced
        # refs: once a listing is actually resolved, the generated id is
        # listing-aware (stable under reordering, safely shareable across
        # components referencing the same listing) rather than index-based.
        rule = _rule("listing.card.standard", "PROP_REF", "listing_ref")
        ds = _dataset(listings=(_listing(),))
        scope = cproj.resolve_route_scope("/hotels/", ds)
        acc = cproj.ProjectionAccumulator()
        value = cproj.bind_ref_prop(
            rule, "listing_ref", "/hotels/", 3,
            content_index={}, listing_dataset=ds, route_scope=scope, projection=acc,
        )
        assert value == "bind.listing_name.lakeview-lodge"
        assert acc.blocks()[0].text == "Lakeview Lodge"

    def test_bind_ref_prop_explicit_assigned_listing_overrides_route_scope(self):
        # AES-WEB-002J.20: an explicit assigned_listing (repetition) wins
        # over the J.19 route-scope fallback -- proving each repeated
        # instance can bind its own record independent of the route's
        # implicit single-listing assignment.
        rule = _rule("listing.card.standard", "PROP_REF", "listing_ref")
        route_listing = _listing(listing_id="route-listing", slug="route-listing")
        other_listing = _listing(
            listing_id="other-listing", slug="other-listing", business_name="Other Business",
        )
        ds = _dataset(listings=(route_listing, other_listing))
        scope = cproj.resolve_route_scope("/hotels/", ds)  # resolves route_listing (first match)
        acc = cproj.ProjectionAccumulator()
        value = cproj.bind_ref_prop(
            rule, "listing_ref", "/hotels/", 0,
            content_index={}, listing_dataset=ds, route_scope=scope, projection=acc,
            assigned_listing=other_listing,
        )
        assert value == "bind.listing_name.other-listing"
        assert acc.blocks()[0].text == "Other Business"

    def test_bind_ref_prop_retains_index_based_id_for_non_listing_source(self):
        # AES-WEB-002J.20 operator decision: the listing-aware
        # bind.<semantic>.<listing_id> id form applies only to
        # LISTING_DATASET-sourced ref projections. A CONTENT_PACKAGE-sourced
        # ref prop (no registered catalog component currently has one that
        # is FULLY_BINDABLE, so a synthetic rule exercises the branch
        # directly) must still generate the J.19 positional
        # bind.<semantic>.<component_index> form -- unchanged.
        from engines.website_generation.components.binding_rules import (
            BindingRule,
            BindingState,
            FieldKind,
        )

        rule = BindingRule(
            component_id="synthetic.component", field_kind=FieldKind.PROP_REF,
            field_name="heading_ref", semantic_slot="page_h1", expected_type="CONTENT_BLOCK_REF",
            required=True, binding_state=BindingState.FULLY_BINDABLE,
            source_rule="ContentPackage:hero_h1",
        )
        index = {("/", "hero_h1"): ("Real headline.",)}
        acc = cproj.ProjectionAccumulator()
        value = cproj.bind_ref_prop(
            rule, "heading_ref", "/", 2,
            content_index=index, listing_dataset=None,
            route_scope=cproj.RouteScope(None, None, None), projection=acc,
        )
        assert value == "bind.page_h1.2"
        assert acc.blocks()[0].text == "Real headline."

    def test_bind_content_slot_missing_listing_fails_honestly(self):
        rule = _rule("profile.header.business", "CONTENT_SLOT", "name")
        acc = cproj.ProjectionAccumulator()
        with pytest.raises(cproj.UnboundContentField) as exc:
            cproj.bind_content_slot(
                rule, "name", "/nowhere/",
                content_index={}, listing_dataset=_dataset(), route_scope=cproj.RouteScope(None, None, None),
                projection=acc,
            )
        assert "missing_listing" in exc.value.reason
