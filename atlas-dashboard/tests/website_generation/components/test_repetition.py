"""Listing repetition and collection composition (AES-WEB-002J.20;
ADR-WEB-CONTENT-BINDING-MAP) -- unit coverage for the declarative
``composition_rules`` table and the repetition step
``ComponentEngine.compile`` now runs between Phase A selection and Phase B
binding.

Distinct from ``test_component_engine.py`` (golden/general engine behavior)
and ``test_component_engine_binding.py`` (the J.19 Phase-B binding matrix):
this file is the dedicated home for repetition-specific proofs -- rule-table
correctness, listing matching/ordering, N-instance expansion, listing-aware
slot ids, selection-trace invariance under expansion, min/max enforcement,
and the v1 scope boundary. End-to-end P1/P2 proofs through the full
Renderer/Assembly/Gate/Repository chain live in the dedicated
``test_listing_collection_chain.py`` integration test instead.
"""

from __future__ import annotations

import pytest

from engines.website_generation.brand.brand_engine import BrandEngine
from engines.website_generation.components import ComponentEngine, build_default_registry
from engines.website_generation.components.composition_rules import (
    COMPOSITION_RULES,
    COMPOSITION_RULES_BY_KEY,
    COMPOSITION_RULES_VERSION,
    RepetitionOrdering,
    RepetitionRule,
    RepetitionSource,
    repetition_rule_for,
)
from engines.website_generation.constants.components import RECIPE_SLOTS_BY_PAGE_ROLE
from engines.website_generation.contracts.artifacts import (
    BusinessSpec,
    ContentBlock,
    ContentPackage,
    ListingCategory,
    ListingDataset,
    ListingRecord,
    PagePlan,
    SiteArchitecture,
    canonical_artifact_json,
)
from engines.website_generation.contracts.enums import ArtifactKind
from engines.website_generation.contracts.errors import ComponentResolutionError
from engines.website_generation.contracts.versions import ENGINE_VERSIONS, SCHEMA_VERSIONS

_REGISTRY = build_default_registry()


# --------------------------------------------------------------------------- #
# Fixtures / helpers (self-contained -- mirrors the sibling test files'
# established pattern of not sharing fixtures across test modules)
# --------------------------------------------------------------------------- #

def _sa(pages):
    return SiteArchitecture(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.SITE_ARCHITECTURE],
        artifact_kind=ArtifactKind.SITE_ARCHITECTURE, source_hashes={},
        pages=tuple(pages), nav_routes=(), sitemap_routes=tuple(p.route for p in pages),
    )


# AES-WEB-002K.1: nav.header.standard/legal.footer.directory are now
# categorically bindable (RENDER_DATA), so Phase A always selects them once
# eligible (region + nav_tree signature) regardless of the site_header/
# site_footer recipe slot's own optional status -- Phase B then requires
# real footer_legal/disclosures content for legal.footer.directory's two
# required content slots. _cp() below unconditionally supplies both for
# _PROFILE_PAGE's route (the only route this file's bare _cp() calls ever
# compile without _category_page_blocks) -- harmless, unused extra blocks
# for any test not compiling that route.
_FOOTER_LEGAL_TEXT = "(c) 2026 Test Directory. All rights reserved."
_FOOTER_DISCLOSURES_TEXT = "Some listings may be sponsored placements, clearly labeled."
_PROFILE_ROUTE_FOR_FOOTER = "/vets/first-clinic/"


def _cp(blocks=()):
    footer_blocks = [
        ContentBlock(page_route=_PROFILE_ROUTE_FOR_FOOTER, slot_id="footer_legal", text=_FOOTER_LEGAL_TEXT),
        ContentBlock(page_route=_PROFILE_ROUTE_FOR_FOOTER, slot_id="disclosures", text=_FOOTER_DISCLOSURES_TEXT),
    ]
    return ContentPackage(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.CONTENT_PACKAGE],
        artifact_kind=ArtifactKind.CONTENT_PACKAGE, source_hashes={},
        blocks=tuple(blocks) + tuple(footer_blocks),
    )


def _brand():
    spec = BusinessSpec(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.BUSINESS_SPEC],
        artifact_kind=ArtifactKind.BUSINESS_SPEC, source_hashes={},
        business_name="Test Directory", niche="y", audience="z", value_proposition="w",
    )
    return BrandEngine().resolve(spec)


def _listing(listing_id, category_id, **overrides):
    fields = dict(
        listing_id=listing_id, business_name=listing_id.replace("-", " ").title(),
        slug=listing_id, category_id=category_id,
    )
    fields.update(overrides)
    return ListingRecord(**fields)


def _category_dataset(category_id, slug, listings, extra_categories=()):
    category = ListingCategory(category_id=category_id, label=slug.title(), slug=slug)
    return ListingDataset(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.LISTING_DATASET],
        artifact_kind=ArtifactKind.LISTING_DATASET, source_hashes={},
        listings=tuple(listings), categories=(category,) + tuple(extra_categories),
        locations=(),
    )


def _category_page_blocks(route):
    return [
        ContentBlock(page_route=route, slot_id="hero_h1", text="Pet-friendly vets"),
        ContentBlock(page_route=route, slot_id="intro", text="Vets that welcome your pets warmly."),
        ContentBlock(page_route=route, slot_id="footer_legal", text=_FOOTER_LEGAL_TEXT),
        ContentBlock(page_route=route, slot_id="disclosures", text=_FOOTER_DISCLOSURES_TEXT),
    ]


_CATEGORY_PAGE = PagePlan(route="/vets/", page_type="category", title="Vets")
_PROFILE_PAGE = PagePlan(route="/vets/first-clinic/", page_type="business-profile", title="")


def _full_listing(listing_id, category_id, **overrides):
    from engines.website_generation.contracts.artifacts import ListingContact, ListingHoursEntry
    from engines.website_generation.contracts.enums import Weekday

    fields = dict(
        listing_id=listing_id, business_name=listing_id.replace("-", " ").title(),
        slug=listing_id, category_id=category_id,
        description="A full-service clinic.",
        contact=ListingContact(phone="555-0100", email="hi@example.com"),
        hours=(ListingHoursEntry(day=Weekday.MONDAY, opens="08:00", closes="18:00"),),
        credentials=("Licensed operator",),
    )
    fields.update(overrides)
    return ListingRecord(**fields)


# --------------------------------------------------------------------------- #
# A. composition_rules.py rule-table correctness
# --------------------------------------------------------------------------- #

class TestCompositionRulesTable:
    def test_version_constant(self):
        assert COMPOSITION_RULES_VERSION == "1.0.0"

    def test_business_profile_related_listings_rule(self):
        rule = repetition_rule_for("business-profile", "related_listings")
        assert rule == RepetitionRule(
            page_role="business-profile",
            recipe_slot_id="related_listings",
            source=RepetitionSource.LISTING_CATEGORY_MATCH,
            min_items=0,
            max_items=None,
            ordering=RepetitionOrdering.DATASET_ORDER,
            exclude_self=True,
        )

    def test_category_listing_cards_rule(self):
        rule = repetition_rule_for("category", "listing_cards")
        assert rule == RepetitionRule(
            page_role="category",
            recipe_slot_id="listing_cards",
            source=RepetitionSource.LISTING_CATEGORY_MATCH,
            min_items=1,
            max_items=None,
            ordering=RepetitionOrdering.DATASET_ORDER,
            exclude_self=False,
        )

    def test_unknown_page_role_returns_none(self):
        assert repetition_rule_for("home", "related_listings") is None

    def test_unknown_slot_id_returns_none(self):
        assert repetition_rule_for("business-profile", "profile_header") is None

    def test_by_key_dict_matches_tuple_contents(self):
        assert COMPOSITION_RULES_BY_KEY == {
            (r.page_role, r.recipe_slot_id): r for r in COMPOSITION_RULES
        }

    def test_rules_are_immutable(self):
        rule = repetition_rule_for("category", "listing_cards")
        with pytest.raises(Exception):
            rule.min_items = 5

    def test_v1_scope_is_exactly_two_rules(self):
        # AES-WEB-002J.20 operator decision #7: v1 repetition scope is
        # listing collections only -- no universal composition for
        # reviews/galleries/faqs/statistics/navigation/tiles. Every recipe
        # slot across every registered page role is checked; only the two
        # authorized (page_role, slot_id) keys may resolve to a rule.
        authorized = {("business-profile", "related_listings"), ("category", "listing_cards")}
        assert set(COMPOSITION_RULES_BY_KEY.keys()) == authorized
        for page_role, slots in RECIPE_SLOTS_BY_PAGE_ROLE.items():
            for slot in slots:
                rule = repetition_rule_for(page_role, slot["slot_id"])
                if rule is not None:
                    assert (page_role, slot["slot_id"]) in authorized


# --------------------------------------------------------------------------- #
# B. Listing matching, ordering, and self-exclusion (via the real engine)
# --------------------------------------------------------------------------- #

class TestListingMatchingAndOrdering:
    def test_category_route_matches_only_same_category_listings(self):
        dataset = _category_dataset(
            "cat-vets", "vets",
            [
                _listing("clinic-a", "cat-vets"),
                _listing("clinic-b", "cat-other"),  # unrelated category
                _listing("clinic-c", "cat-vets"),
            ],
            extra_categories=(ListingCategory(category_id="cat-other", label="Other", slug="other"),),
        )
        result = ComponentEngine().compile(
            _sa([_CATEGORY_PAGE]), _cp(_category_page_blocks("/vets/")),
            listing_dataset=dataset, brand_package=_brand(),
        )
        page = result.component_manifest.pages[0]
        cards = [i for i in page.components if i.component_id == "listing.card.standard"]
        assert len(cards) == 2
        bound_ids = {c.props["listing_ref"].split(".")[-1] for c in cards}
        assert bound_ids == {"clinic-a", "clinic-c"}

    def test_dataset_order_preserved_never_sorted(self):
        # Deliberately non-alphabetical insertion order -- the output must
        # mirror it exactly, never re-sort by name/id (§7 ADR-WEB-LISTING-
        # DATASET "producers sort, artifacts preserve" doctrine).
        dataset = _category_dataset(
            "cat-vets", "vets",
            [
                _listing("zephyr-clinic", "cat-vets"),
                _listing("acorn-clinic", "cat-vets"),
                _listing("mid-clinic", "cat-vets"),
            ],
        )
        result = ComponentEngine().compile(
            _sa([_CATEGORY_PAGE]), _cp(_category_page_blocks("/vets/")),
            listing_dataset=dataset, brand_package=_brand(),
        )
        page = result.component_manifest.pages[0]
        cards = [i for i in page.components if i.component_id == "listing.card.standard"]
        bound_ids = [c.props["listing_ref"].split(".")[-1] for c in cards]
        assert bound_ids == ["zephyr-clinic", "acorn-clinic", "mid-clinic"]

    def test_exclude_self_true_drops_hosting_listing(self):
        dataset = _category_dataset(
            "cat-vets", "vets",
            [
                _full_listing("first-clinic", "cat-vets"),  # matches _PROFILE_PAGE's own route
                _full_listing("second-clinic", "cat-vets"),
                _full_listing("third-clinic", "cat-vets"),
            ],
        )
        result = ComponentEngine().compile(
            _sa([_PROFILE_PAGE]), _cp(), listing_dataset=dataset, brand_package=_brand(),
        )
        page = result.component_manifest.pages[0]
        cards = [i for i in page.components if i.component_id == "listing.card.standard"]
        bound_ids = [c.props["listing_ref"].split(".")[-1] for c in cards]
        assert "first-clinic" not in bound_ids
        assert bound_ids == ["second-clinic", "third-clinic"]

    def test_zero_matches_business_profile_is_legal_empty(self):
        # related_listings has min_items=0 -- a single-listing dataset
        # (the page's own, excluded as self) legally yields zero instances,
        # not a compile failure.
        dataset = _category_dataset("cat-vets", "vets", [_full_listing("first-clinic", "cat-vets")])
        result = ComponentEngine().compile(
            _sa([_PROFILE_PAGE]), _cp(), listing_dataset=dataset, brand_package=_brand(),
        )
        page = result.component_manifest.pages[0]
        cards = [i for i in page.components if i.component_id == "listing.card.standard"]
        assert cards == []

    def test_zero_matches_category_page_fails_min_items(self):
        # listing_cards has min_items=1 -- a category with zero listings is
        # an honest compile failure (no_matching_items), never a silently
        # empty page.
        dataset = _category_dataset("cat-vets", "vets", [])
        with pytest.raises(ComponentResolutionError) as exc:
            ComponentEngine().compile(
                _sa([_CATEGORY_PAGE]), _cp(_category_page_blocks("/vets/")),
                listing_dataset=dataset, brand_package=_brand(),
            )
        failures = exc.value.diagnostics["repetition_failures"]
        entry = next(f for f in failures if f["recipe_slot_id"] == "listing_cards")
        assert entry["route"] == "/vets/"
        assert "no_matching_items" in entry["reason"]
        assert "0 matched, minimum 1 required" in entry["reason"]

    def test_repeat_scope_unresolved_when_no_dataset_supplied(self):
        with pytest.raises(ComponentResolutionError) as exc:
            ComponentEngine().compile(
                _sa([_CATEGORY_PAGE]), _cp(_category_page_blocks("/vets/")),
                listing_dataset=None, brand_package=_brand(),
            )
        failures = exc.value.diagnostics["repetition_failures"]
        entry = next(f for f in failures if f["recipe_slot_id"] == "listing_cards")
        assert "repeat_scope_unresolved" in entry["reason"]

    def test_repeat_scope_unresolved_when_route_names_no_category(self):
        dataset = _category_dataset("cat-vets", "vets", [_listing("clinic-a", "cat-vets")])
        mismatched_page = PagePlan(route="/no-such-category/", page_type="category", title="")
        with pytest.raises(ComponentResolutionError) as exc:
            ComponentEngine().compile(
                _sa([mismatched_page]), _cp(_category_page_blocks("/no-such-category/")),
                listing_dataset=dataset, brand_package=_brand(),
            )
        failures = exc.value.diagnostics["repetition_failures"]
        entry = next(f for f in failures if f["recipe_slot_id"] == "listing_cards")
        assert "repeat_scope_unresolved" in entry["reason"]


# --------------------------------------------------------------------------- #
# C. N-instance expansion and per-instance binding
# --------------------------------------------------------------------------- #

class TestExpansionAndBinding:
    @pytest.mark.parametrize("n", [1, 5, 50])
    def test_n_instances_created_for_n_matches(self, n):
        listings = [_listing("clinic-%03d" % i, "cat-vets") for i in range(n)]
        dataset = _category_dataset("cat-vets", "vets", listings)
        result = ComponentEngine().compile(
            _sa([_CATEGORY_PAGE]), _cp(_category_page_blocks("/vets/")),
            listing_dataset=dataset, brand_package=_brand(),
        )
        page = result.component_manifest.pages[0]
        cards = [i for i in page.components if i.component_id == "listing.card.standard"]
        assert len(cards) == n
        bound_ids = [c.props["listing_ref"].split(".")[-1] for c in cards]
        assert bound_ids == [l.listing_id for l in listings]

    def test_no_artificial_max_items_cap(self):
        # AES-WEB-002J.20 operator decision #9: render ALL matching
        # listings -- no cap, no pagination semantics invented.
        listings = [_listing("clinic-%03d" % i, "cat-vets") for i in range(37)]
        dataset = _category_dataset("cat-vets", "vets", listings)
        result = ComponentEngine().compile(
            _sa([_CATEGORY_PAGE]), _cp(_category_page_blocks("/vets/")),
            listing_dataset=dataset, brand_package=_brand(),
        )
        page = result.component_manifest.pages[0]
        cards = [i for i in page.components if i.component_id == "listing.card.standard"]
        assert len(cards) == 37

    def test_positional_identity_no_instance_id_field(self):
        # AES-WEB-002J.20 operator decision #17: no instance_id field is
        # added to ComponentInstance -- identity stays purely positional.
        listings = [_listing("clinic-%d" % i, "cat-vets") for i in range(3)]
        dataset = _category_dataset("cat-vets", "vets", listings)
        result = ComponentEngine().compile(
            _sa([_CATEGORY_PAGE]), _cp(_category_page_blocks("/vets/")),
            listing_dataset=dataset, brand_package=_brand(),
        )
        page = result.component_manifest.pages[0]
        for instance in page.components:
            assert "instance_id" not in instance.__fields__

    def test_each_instance_content_binds_only_its_own_listing(self):
        listings = [
            _full_listing("alpha-clinic", "cat-vets", description="Alpha's own description."),
            _full_listing("beta-clinic", "cat-vets", description="Beta's own description."),
        ]
        dataset = _category_dataset("cat-vets", "vets", listings)
        result = ComponentEngine().compile(
            _sa([_CATEGORY_PAGE]), _cp(_category_page_blocks("/vets/")),
            listing_dataset=dataset, brand_package=_brand(),
        )
        page = result.component_manifest.pages[0]
        cards = [i for i in page.components if i.component_id == "listing.card.standard"]
        by_block = {b.slot_id: b.text for b in result.content_package.blocks}
        alpha_ref = cards[0].props["listing_ref"]
        beta_ref = cards[1].props["listing_ref"]
        assert by_block[alpha_ref] == "Alpha Clinic"
        assert by_block[beta_ref] == "Beta Clinic"
        assert alpha_ref != beta_ref


# --------------------------------------------------------------------------- #
# D. Listing-aware generated slot ids
# --------------------------------------------------------------------------- #

class TestListingAwareSlotIds:
    def test_slot_ids_keyed_by_listing_id_not_by_index(self):
        listings = [_listing("clinic-alpha", "cat-vets"), _listing("clinic-beta", "cat-vets")]
        dataset = _category_dataset("cat-vets", "vets", listings)
        result = ComponentEngine().compile(
            _sa([_CATEGORY_PAGE]), _cp(_category_page_blocks("/vets/")),
            listing_dataset=dataset, brand_package=_brand(),
        )
        page = result.component_manifest.pages[0]
        cards = [i for i in page.components if i.component_id == "listing.card.standard"]
        refs = {c.props["listing_ref"] for c in cards}
        assert refs == {"bind.listing_name.clinic-alpha", "bind.listing_name.clinic-beta"}
        # Never the J.19 positional form (bind.listing_name.0/1) -- would
        # collide once N > 1 shares the same route.
        assert "bind.listing_name.0" not in refs
        assert "bind.listing_name.1" not in refs

    def test_no_projected_slot_collisions_across_instances(self):
        # Two distinct listings must never collide at the same generated
        # slot id -- proving the listing-aware strategy actually prevents
        # the exact collision the J.19 index-based/route-wide form would
        # otherwise risk once expansion produces >1 instance per route.
        listings = [_listing("clinic-%d" % i, "cat-vets") for i in range(10)]
        dataset = _category_dataset("cat-vets", "vets", listings)
        result = ComponentEngine().compile(
            _sa([_CATEGORY_PAGE]), _cp(_category_page_blocks("/vets/")),
            listing_dataset=dataset, brand_package=_brand(),
        )
        slot_ids = [b.slot_id for b in result.content_package.blocks if b.slot_id.startswith("bind.")]
        assert len(slot_ids) == len(set(slot_ids))


# --------------------------------------------------------------------------- #
# E. Selection trace is unaffected by expansion (records the decision, not
# the instances)
# --------------------------------------------------------------------------- #

class TestSelectionTraceInvariantUnderExpansion:
    @pytest.mark.parametrize("n", [1, 5, 50])
    def test_one_trace_entry_regardless_of_instance_count(self, n):
        listings = [_listing("clinic-%03d" % i, "cat-vets") for i in range(n)]
        dataset = _category_dataset("cat-vets", "vets", listings)
        result = ComponentEngine().compile(
            _sa([_CATEGORY_PAGE]), _cp(_category_page_blocks("/vets/")),
            listing_dataset=dataset, brand_package=_brand(),
        )
        matching_slots = [
            s for s in result.component_manifest.selection_trace.slots
            if s.slot_id == "/vets/#listing_cards"
        ]
        assert len(matching_slots) == 1
        assert matching_slots[0].chosen_component_id == "listing.card.standard"


# --------------------------------------------------------------------------- #
# F. max_items enforcement (repeat_limit_exceeded) -- exercised via a
# monkeypatched rule since no v1 production rule declares a cap (operator
# decision #9: render all matches, no artificial cap). This proves the
# engine's enforcement branch works without inventing a cap in the real
# COMPOSITION_RULES table.
# --------------------------------------------------------------------------- #

class TestMaxItemsEnforcement:
    def test_repeat_limit_exceeded_when_matches_exceed_a_declared_cap(self, monkeypatch):
        import engines.website_generation.components.component_engine as ce_module

        capped_rule = RepetitionRule(
            page_role="category", recipe_slot_id="listing_cards",
            source=RepetitionSource.LISTING_CATEGORY_MATCH,
            min_items=1, max_items=2, ordering=RepetitionOrdering.DATASET_ORDER,
            exclude_self=False,
        )

        def fake_repetition_rule_for(page_role, recipe_slot_id):
            if (page_role, recipe_slot_id) == ("category", "listing_cards"):
                return capped_rule
            return None

        monkeypatch.setattr(ce_module, "repetition_rule_for", fake_repetition_rule_for)

        dataset = _category_dataset(
            "cat-vets", "vets", [_listing("clinic-%d" % i, "cat-vets") for i in range(3)]
        )
        with pytest.raises(ComponentResolutionError) as exc:
            ComponentEngine().compile(
                _sa([_CATEGORY_PAGE]), _cp(_category_page_blocks("/vets/")),
                listing_dataset=dataset, brand_package=_brand(),
            )
        failures = exc.value.diagnostics["repetition_failures"]
        entry = next(f for f in failures if f["recipe_slot_id"] == "listing_cards")
        assert "repeat_limit_exceeded" in entry["reason"]
        assert "3 matched, maximum 2 allowed" in entry["reason"]


# --------------------------------------------------------------------------- #
# G. Determinism
# --------------------------------------------------------------------------- #

class TestDeterminism:
    def test_repeat_compile_is_byte_identical(self):
        listings = [_listing("clinic-%d" % i, "cat-vets") for i in range(5)]
        dataset = _category_dataset("cat-vets", "vets", listings)
        sa, cp, brand = _sa([_CATEGORY_PAGE]), _cp(_category_page_blocks("/vets/")), _brand()
        first = ComponentEngine().compile(sa, cp, listing_dataset=dataset, brand_package=brand)
        second = ComponentEngine().compile(sa, cp, listing_dataset=dataset, brand_package=brand)
        assert canonical_artifact_json(first.component_manifest) == canonical_artifact_json(
            second.component_manifest
        )
        assert canonical_artifact_json(first.content_package) == canonical_artifact_json(
            second.content_package
        )


# --------------------------------------------------------------------------- #
# H. Component Engine version
# --------------------------------------------------------------------------- #

class TestComponentEngineVersion:
    def test_version_bumped_to_1_5_0(self):
        # AES-WEB-002K.1: 1.2.0 -> 1.3.0 (render-data production).
        # PILOT-PTF-1: 1.3.0 -> 1.4.0 (category-tile render-data, honest
        # optional-slot omission). AES-WEB-002L.1: 1.4.0 -> 1.5.0
        # (strategy-keyed recipe lookup, hero CTA render-data production).
        assert ENGINE_VERSIONS["component_engine"] == "1.5.0"
        assert ComponentEngine().version == "1.5.0"


# --------------------------------------------------------------------------- #
# I. Adversarial: duplicate-like names and missing data on one repeated item
# --------------------------------------------------------------------------- #

class TestAdversarialDataQuality:
    def test_duplicate_like_business_names_stay_distinct_by_listing_id(self):
        # Two listings share the exact same business_name (a legitimate,
        # if unusual, real-world case -- two locations of the same chain)
        # but have distinct listing_id/slug. Repetition must never
        # deduplicate or collapse them by name -- identity is listing_id,
        # never business_name.
        listings = [
            _listing("clinic-north", "cat-vets", business_name="Same Name Clinic"),
            _listing("clinic-south", "cat-vets", business_name="Same Name Clinic"),
        ]
        dataset = _category_dataset("cat-vets", "vets", listings)
        result = ComponentEngine().compile(
            _sa([_CATEGORY_PAGE]), _cp(_category_page_blocks("/vets/")),
            listing_dataset=dataset, brand_package=_brand(),
        )
        page = result.component_manifest.pages[0]
        cards = [i for i in page.components if i.component_id == "listing.card.standard"]
        assert len(cards) == 2
        refs = [c.props["listing_ref"] for c in cards]
        assert refs == ["bind.listing_name.clinic-north", "bind.listing_name.clinic-south"]
        assert refs[0] != refs[1]

    def test_missing_required_data_on_one_repeated_listing_batch_fails_honestly(self):
        # One listing among several has an empty business_name (the only
        # field listing.card.standard's listing_ref semantic slot,
        # "listing_name", actually requires). This must batch-fail the
        # whole compile with an honest unbindable_required_props entry --
        # never silently drop the bad instance, never fabricate a name.
        listings = [
            _listing("clinic-good", "cat-vets", business_name="Good Clinic"),
            _listing("clinic-blank", "cat-vets", business_name=""),
        ]
        dataset = _category_dataset("cat-vets", "vets", listings)
        with pytest.raises(ComponentResolutionError) as exc:
            ComponentEngine().compile(
                _sa([_CATEGORY_PAGE]), _cp(_category_page_blocks("/vets/")),
                listing_dataset=dataset, brand_package=_brand(),
            )
        failures = exc.value.diagnostics["unbindable_required_props"]
        entry = next(f for f in failures if f["component_id"] == "listing.card.standard")
        assert "missing_source_artifact" in entry["reason"]
        assert "listing_name" in entry["reason"]
