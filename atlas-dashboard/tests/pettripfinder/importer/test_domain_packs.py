"""AES-DATA-003A -- domain-pack foundation: contract validation, the
registry, category_templates/policy_compose delegation parity, additive
CandidateListing fields, legacy-safe serialization, pack-aware job
fingerprinting, and byte-identical golden regression proof for the three
existing categories (Drury, Scioto Audubon, Land-Grant). Static fixtures
only -- no network, no live provider calls."""

from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer import policy_compose
from scripts.pettripfinder.importer.batch import BatchJob, compute_job_fingerprint
from scripts.pettripfinder.importer.candidate import candidate_from_dict, dumps_candidate
from scripts.pettripfinder.importer.category_templates import (
    allowed_field_order,
    allowed_fields,
)
from scripts.pettripfinder.importer.domain_packs.base import (
    Capability,
    CapabilityState,
    CategoryDetail,
    DomainPack,
    DomainPackError,
    DuplicateCategoryRegistrationError,
    SourceRoleSpec,
    UnknownCategoryError,
)
from scripts.pettripfinder.importer.domain_packs.capabilities import (
    CAPABILITY_SCHEMA_VERSION,
    CAPABILITY_SLUGS,
    HIGH_RISK_CAPABILITY_SLUGS,
)
from scripts.pettripfinder.importer.domain_packs.registry import (
    DomainPackRegistry,
    default_registry,
)
from scripts.pettripfinder.importer.models import CandidateListing

_REPO_ROOT = Path(__file__).resolve().parents[3]
_GOLDEN_DIR = Path(__file__).parent / "fixtures" / "golden"
_SEED_CSV = _REPO_ROOT / "launch_packages" / "pettripfinder" / "seed_businesses.csv"

# --------------------------------------------------------------------------- #
# The pre-refactor field tuples, captured verbatim from category_templates.py
# before AES-DATA-003A -- an independent regression guard that does not rely
# on the registry to check itself.
# --------------------------------------------------------------------------- #

_EXPECTED_HOTEL_FIELDS = (
    "name", "address", "phone",
    "pets_allowed", "species_allowed", "pet_fee", "fee_basis", "weight_limit",
    "pet_count_limit", "unattended_policy", "breed_restrictions",
    "general_restrictions",
)
_EXPECTED_PARK_FIELDS = (
    "name", "address", "phone",
    "pets_allowed", "off_leash", "off_leash_area_description", "fenced",
    "leash_rule", "small_dog_area", "large_dog_area", "water_available",
    "trails",
)
_EXPECTED_RESTAURANT_FIELDS = (
    "name", "address", "phone",
    "pets_allowed", "patio_or_outdoor_only", "permitted_area",
    "indoor_prohibited", "seasonal_or_weather_caveat", "water_or_treats",
    "dog_menu",
)


def _sample_pack(**overrides) -> DomainPack:
    kwargs = dict(
        pack_id="test-pack", category_ids=("widgets",),
        allowed_fields=frozenset({"name", "address"}), field_order=("name", "address"),
        field_normalizers=(("name", "whitespace"),))
    kwargs.update(overrides)
    return DomainPack(**kwargs)


# --------------------------------------------------------------------------- #
# 1-4. Registry: exact categories, deterministic order, lookup, unknown.
# --------------------------------------------------------------------------- #

class TestRegistryLookup:
    def test_1_registry_contains_exactly_the_three_existing_categories(self):
        # AES-DATA-003B added "veterinary"; AES-DATA-003C adds "boarding",
        # "grooming", "pet_store" -- seven categories total.
        assert set(default_registry.category_ids()) == {
            "hotels", "parks", "restaurants", "veterinary",
            "boarding", "grooming", "pet_store"}

    def test_2_deterministic_category_ids_ordering(self):
        assert default_registry.category_ids() == (
            "hotels", "parks", "restaurants", "veterinary",
            "boarding", "grooming", "pet_store")
        # Stable across repeated calls (pure function of registration order).
        assert default_registry.category_ids() == default_registry.category_ids()

    def test_3_lookup_by_each_valid_category(self):
        for cat in ("hotels", "parks", "restaurants", "veterinary",
                    "boarding", "grooming", "pet_store"):
            pack = default_registry.for_category(cat)
            assert cat in pack.category_ids

    def test_4_unknown_category_raises_typed_error(self):
        with pytest.raises(UnknownCategoryError):
            # "daycare" is a boarding CAPABILITY (doctrine #12), never its
            # own category -- genuinely unregistered.
            default_registry.for_category("daycare")


# --------------------------------------------------------------------------- #
# 5-10. Pack/registry construction validation.
# --------------------------------------------------------------------------- #

class TestValidation:
    def test_5_duplicate_registration_rejected(self):
        registry = DomainPackRegistry()
        registry.register(_sample_pack(pack_id="pack-a", category_ids=("widgets",)))
        with pytest.raises(DuplicateCategoryRegistrationError):
            registry.register(_sample_pack(pack_id="pack-b", category_ids=("widgets",)))

    def test_6_invalid_pack_id_rejected(self):
        with pytest.raises(DomainPackError):
            _sample_pack(pack_id="Not A Safe ID!")

    def test_7_empty_category_ids_rejected(self):
        with pytest.raises(DomainPackError):
            _sample_pack(category_ids=())

    def test_8_duplicate_field_order_entry_rejected(self):
        with pytest.raises(DomainPackError):
            _sample_pack(
                allowed_fields=frozenset({"name"}), field_order=("name", "name"),
                field_normalizers=())

    def test_9_field_order_field_outside_allowed_fields_rejected(self):
        with pytest.raises(DomainPackError):
            _sample_pack(
                allowed_fields=frozenset({"name"}), field_order=("name", "phone"),
                field_normalizers=())

    def test_10_source_role_duplicate_rejected(self):
        with pytest.raises(DomainPackError):
            _sample_pack(source_roles=(
                SourceRoleSpec(role_id="location"), SourceRoleSpec(role_id="location")))

    def test_duplicate_category_ids_within_one_pack_rejected(self):
        with pytest.raises(DomainPackError):
            _sample_pack(category_ids=("widgets", "widgets"))

    def test_field_normalizer_outside_allowed_fields_rejected(self):
        with pytest.raises(DomainPackError):
            _sample_pack(
                allowed_fields=frozenset({"name"}), field_order=("name",),
                field_normalizers=(("phone", "phone"),))

    def test_invalid_pack_version_rejected(self):
        with pytest.raises(DomainPackError):
            _sample_pack(pack_version="not-a-version")


# --------------------------------------------------------------------------- #
# 11. Pack immutability.
# --------------------------------------------------------------------------- #

class TestImmutability:
    def test_11_pack_immutability(self):
        pack = _sample_pack()
        with pytest.raises(FrozenInstanceError):
            pack.pack_id = "changed"
        with pytest.raises((TypeError, AttributeError)):
            pack.allowed_fields.add("new_field")

    def test_capability_immutability(self):
        cap = Capability(capability_id="pets_allowed", state=CapabilityState.UNKNOWN.value)
        with pytest.raises(FrozenInstanceError):
            cap.state = CapabilityState.SUPPORTED.value


# --------------------------------------------------------------------------- #
# 12-14. Capability taxonomy skeleton.
# --------------------------------------------------------------------------- #

class TestCapabilityTaxonomy:
    def test_12_capability_state_enum_values_exact(self):
        assert {s.value for s in CapabilityState} == {
            "SUPPORTED", "EXPLICITLY_ABSENT", "UNKNOWN", "CONFLICTED"}

    def test_13_capability_taxonomy_contains_all_declared_initial_slugs(self):
        # AES-DATA-003A slugs (unchanged -- still all present).
        aes_003a = {
            "pets_allowed", "appointment_required", "walk_ins_accepted", "open_24h",
            "emergency_service", "urgent_care", "species_served", "mobile_service",
            "service_area", "boarding_offered", "daycare_offered", "grooming_offered",
            "retail_products", "pharmacy", "prescription_fulfillment", "self_wash",
            "vaccination_clinic", "delivery", "curbside_pickup", "existing_clients_only",
            "online_ordering", "booking_url",
        }
        # AES-DATA-003B veterinary additions.
        aes_003b = {
            "general_practice", "preventive_care", "wellness_exams", "vaccinations",
            "diagnostics", "surgery", "dentistry", "specialty_care", "critical_care",
            "after_hours_instructions",
        }
        # AES-DATA-003C boarding/grooming/pet-store additions.
        aes_003c = {
            "dog_boarding", "cat_boarding", "other_species_boarding",
            "reservation_required", "same_day_availability", "vaccination_requirements",
            "temperament_evaluation", "medication_administration",
            "pickup_dropoff_windows", "live_camera", "pricing_available",
            "dog_grooming", "cat_grooming", "bathing", "nail_trimming", "deshedding",
            "breed_restrictions", "size_restrictions", "pet_food", "pet_supplies",
            "prescription_food", "live_animals",
        }
        assert set(CAPABILITY_SLUGS) == aes_003a | aes_003b | aes_003c

    def test_14_high_risk_subset_exact(self):
        # AES-DATA-003B adds species_served to the high-risk subset (exotic/
        # specialty-species claims carry the same no-inference risk as an
        # emergency claim; per-instance Capability.high_risk stays False for
        # a plain "dogs and cats" value -- see domain_packs/veterinary.py).
        # AES-DATA-003C adds 9 more: same_day_availability/live_animals/
        # prescription_fulfillment/vaccination_clinic/other_species_boarding/
        # cat_boarding/medication_administration/mobile_service/service_area.
        # "prescription_fulfillment" was already a veterinary field (003B) --
        # this is a disclosed, regression-safe strengthening of veterinary's
        # own evidence discipline (no existing veterinary fixture exercises
        # it, so no golden/scenario byte changes), not new vet scope.
        assert set(HIGH_RISK_CAPABILITY_SLUGS) == {
            "open_24h", "emergency_service", "urgent_care", "walk_ins_accepted",
            "existing_clients_only", "species_served",
            "same_day_availability", "live_animals", "prescription_fulfillment",
            "vaccination_clinic", "other_species_boarding", "cat_boarding",
            "medication_administration", "mobile_service", "service_area"}
        assert set(HIGH_RISK_CAPABILITY_SLUGS) <= set(CAPABILITY_SLUGS)

    def test_capability_schema_version_declared(self):
        assert CAPABILITY_SCHEMA_VERSION == "1.0.0"

    def test_capability_construction_rejects_unknown_state(self):
        with pytest.raises(DomainPackError):
            Capability(capability_id="pets_allowed", state="MAYBE")

    def test_non_unknown_capability_requires_evidence_index(self):
        with pytest.raises(DomainPackError):
            Capability(capability_id="pets_allowed", state=CapabilityState.SUPPORTED.value,
                      evidence_index=-1)


# --------------------------------------------------------------------------- #
# 15-16. Legacy pack field sets match pre-refactor values exactly.
# --------------------------------------------------------------------------- #

class TestLegacyPackFieldParity:
    def test_15_lodging_allowed_fields_matches_pre_refactor(self):
        pack = default_registry.for_category("hotels")
        assert pack.allowed_fields == frozenset(_EXPECTED_HOTEL_FIELDS)

    def test_15_parks_allowed_fields_matches_pre_refactor(self):
        pack = default_registry.for_category("parks")
        assert pack.allowed_fields == frozenset(_EXPECTED_PARK_FIELDS)

    def test_15_dining_allowed_fields_matches_pre_refactor(self):
        pack = default_registry.for_category("restaurants")
        assert pack.allowed_fields == frozenset(_EXPECTED_RESTAURANT_FIELDS)

    def test_16_lodging_field_order_matches_pre_refactor(self):
        pack = default_registry.for_category("hotels")
        assert pack.field_order == _EXPECTED_HOTEL_FIELDS

    def test_16_parks_field_order_matches_pre_refactor(self):
        pack = default_registry.for_category("parks")
        assert pack.field_order == _EXPECTED_PARK_FIELDS

    def test_16_dining_field_order_matches_pre_refactor(self):
        pack = default_registry.for_category("restaurants")
        assert pack.field_order == _EXPECTED_RESTAURANT_FIELDS


# --------------------------------------------------------------------------- #
# 17-18. category_templates.py delegation.
# --------------------------------------------------------------------------- #

class TestCategoryTemplatesDelegation:
    def test_17_allowed_fields_delegates_correctly(self):
        for cat, expected in (
            ("hotels", _EXPECTED_HOTEL_FIELDS), ("parks", _EXPECTED_PARK_FIELDS),
            ("restaurants", _EXPECTED_RESTAURANT_FIELDS),
        ):
            assert allowed_fields(cat) == frozenset(expected)
        assert allowed_fields("unknown-category") == frozenset()

    def test_18_allowed_field_order_delegates_correctly(self):
        for cat, expected in (
            ("hotels", _EXPECTED_HOTEL_FIELDS), ("parks", _EXPECTED_PARK_FIELDS),
            ("restaurants", _EXPECTED_RESTAURANT_FIELDS),
        ):
            assert allowed_field_order(cat) == expected
        assert allowed_field_order("unknown-category") == ()


# --------------------------------------------------------------------------- #
# 19-21. Policy-composition parity: the pack's compose_summary is a thin,
# verified-equivalent wrapper around the REAL, unmodified policy_compose.py.
# --------------------------------------------------------------------------- #

class TestPolicyCompositionParity:
    _HOTEL_FACTS = {"pets_allowed": "true", "species_allowed": "dogs,cats",
                    "pet_fee": "$50", "fee_basis": "per stay"}
    _PARK_FACTS = {"pets_allowed": "true", "off_leash": "true",
                   "off_leash_area_description": "fenced 2-acre area"}
    _RESTAURANT_FACTS = {"pets_allowed": "true", "patio_or_outdoor_only": "true"}

    def test_19_lodging_policy_composition_byte_identical(self):
        pack = default_registry.for_category("hotels")
        assert pack.compose_summary(self._HOTEL_FACTS) == policy_compose.compose_pet_policy(
            self._HOTEL_FACTS, C.CATEGORY_HOTELS)

    def test_20_parks_policy_composition_byte_identical(self):
        pack = default_registry.for_category("parks")
        assert pack.compose_summary(self._PARK_FACTS) == policy_compose.compose_pet_policy(
            self._PARK_FACTS, C.CATEGORY_PARKS)

    def test_21_dining_policy_composition_byte_identical(self):
        pack = default_registry.for_category("restaurants")
        assert pack.compose_summary(self._RESTAURANT_FACTS) == policy_compose.compose_pet_policy(
            self._RESTAURANT_FACTS, C.CATEGORY_RESTAURANTS)

    def test_empty_facts_composition_byte_identical_for_all_three(self):
        for cat_id, cat_const in (
            ("hotels", C.CATEGORY_HOTELS), ("parks", C.CATEGORY_PARKS),
            ("restaurants", C.CATEGORY_RESTAURANTS),
        ):
            pack = default_registry.for_category(cat_id)
            assert pack.compose_summary({}) == policy_compose.compose_pet_policy({}, cat_const)


# --------------------------------------------------------------------------- #
# 22-28. Additive model fields + legacy-safe serialization.
# --------------------------------------------------------------------------- #

def _minimal_legacy_dict() -> dict:
    """The exact pre-AES-DATA-003A CandidateListing JSON shape (no
    capabilities/category_detail/pack_id/pack_version/
    capability_schema_version keys at all -- a real legacy candidate)."""
    return json.loads((_GOLDEN_DIR / "golden_drury.json").read_text(encoding="utf-8"))


class TestAdditiveFieldsAndSerialization:
    def test_22_candidate_listing_new_fields_default_correctly(self):
        import dataclasses
        field_defaults = {f.name: f.default for f in dataclasses.fields(CandidateListing)}
        assert field_defaults["capabilities"] == ()
        assert field_defaults["category_detail"] is None
        assert field_defaults["pack_id"] == ""
        assert field_defaults["pack_version"] == ""
        assert field_defaults["capability_schema_version"] == ""

    def test_23_legacy_candidate_json_loads_without_new_keys(self):
        legacy = _minimal_legacy_dict()
        assert "capabilities" not in legacy
        assert "category_detail" not in legacy
        assert "pack_id" not in legacy
        candidate = candidate_from_dict(legacy)
        assert candidate.capabilities == ()
        assert candidate.category_detail is None
        assert candidate.pack_id == ""
        assert candidate.pack_version == ""
        assert candidate.capability_schema_version == ""

    def test_24_populated_capability_round_trips(self):
        import dataclasses
        legacy = _minimal_legacy_dict()
        candidate = candidate_from_dict(legacy)
        evidenced = dataclasses.replace(candidate, capabilities=(
            Capability(capability_id="pets_allowed", state=CapabilityState.SUPPORTED.value,
                      value="true", evidence_index=0, source_url="https://a.test"),
        ))
        d = json.loads(dumps_candidate(evidenced))
        assert d["capabilities"] == [{
            "capability_id": "pets_allowed", "state": "SUPPORTED", "value": "true",
            "high_risk": False, "evidence_index": 0, "source_url": "https://a.test",
        }]
        reloaded = candidate_from_dict(d)
        assert reloaded.capabilities == evidenced.capabilities

    def test_25_populated_category_detail_round_trips(self):
        legacy = _minimal_legacy_dict()
        candidate = candidate_from_dict(legacy)
        detail = CategoryDetail(
            detail_type="veterinary", detail_schema_version="1.0.0",
            fields=(("after_hours_instructions", "call the emergency line"),))
        import dataclasses
        with_detail = dataclasses.replace(candidate, category_detail=detail)
        d = json.loads(dumps_candidate(with_detail))
        assert d["category_detail"] == {
            "detail_type": "veterinary", "detail_schema_version": "1.0.0",
            "fields": [["after_hours_instructions", "call the emergency line"]],
        }
        reloaded = candidate_from_dict(d)
        assert reloaded.category_detail == detail

    def test_26_malformed_capability_state_rejected(self):
        legacy = _minimal_legacy_dict()
        legacy["capabilities"] = [{
            "capability_id": "pets_allowed", "state": "MAYBE_SORT_OF",
        }]
        with pytest.raises(DomainPackError):
            candidate_from_dict(legacy)

    def test_27_empty_new_fields_omitted_from_serialization(self):
        legacy = _minimal_legacy_dict()
        candidate = candidate_from_dict(legacy)
        d = json.loads(dumps_candidate(candidate))
        assert "capabilities" not in d
        assert "category_detail" not in d
        assert "pack_id" not in d
        assert "pack_version" not in d
        assert "capability_schema_version" not in d

    def test_28_legacy_serialized_candidate_bytes_unchanged(self):
        legacy_text = (_GOLDEN_DIR / "golden_drury.json").read_text(encoding="utf-8")
        candidate = candidate_from_dict(json.loads(legacy_text))
        assert dumps_candidate(candidate) + "\n" == legacy_text


# --------------------------------------------------------------------------- #
# 29-32. Pack-aware job fingerprinting.
# --------------------------------------------------------------------------- #

def _job(category: str, job_id: str = "j1") -> BatchJob:
    return BatchJob(
        job_id=job_id, candidate_name="X", category=category,
        expected_city="c", expected_state="OH", urls=("https://a.test",))


class TestPackAwareFingerprint:
    def _kwargs(self):
        return dict(extractor="static", model="m", observed_at="2026-01-01",
                   repo_root=_REPO_ROOT)

    def test_29_fingerprint_deterministic(self):
        job = _job("hotels")
        fp1 = compute_job_fingerprint(job, **self._kwargs())
        fp2 = compute_job_fingerprint(job, **self._kwargs())
        assert fp1 == fp2

    def test_30_pack_version_change_alters_only_matching_category(self, monkeypatch):
        hotel_job = _job("hotels")
        park_job = _job("parks")
        fp_hotel_before = compute_job_fingerprint(hotel_job, **self._kwargs())
        fp_park_before = compute_job_fingerprint(park_job, **self._kwargs())

        import dataclasses
        from scripts.pettripfinder.importer.domain_packs import registry as registry_mod

        original_pack = registry_mod.default_registry.for_category("hotels")
        bumped_pack = dataclasses.replace(original_pack, pack_version="9.9.9")
        monkeypatch.setitem(
            registry_mod.default_registry._by_category, "hotels", bumped_pack)

        fp_hotel_after = compute_job_fingerprint(hotel_job, **self._kwargs())
        fp_park_after = compute_job_fingerprint(park_job, **self._kwargs())

        assert fp_hotel_after != fp_hotel_before
        assert fp_park_after == fp_park_before

    def test_unknown_category_fingerprint_fails_clearly(self):
        job = _job("daycare")   # a boarding capability, never its own category
        with pytest.raises(UnknownCategoryError):
            compute_job_fingerprint(job, **self._kwargs())

    def test_31_batch_id_unaffected_by_pack_version(self):
        from scripts.pettripfinder.importer.batch import BatchManifest, get_batch_id

        manifest = BatchManifest(
            manifest_schema_version=C.BATCH_MANIFEST_SCHEMA_VERSION, batch_id="stable-batch",
            batch_name="t", defaults={}, jobs=(_job("hotels"),))
        assert get_batch_id(manifest) == "stable-batch"
        # get_batch_id is a pure function of manifest.batch_id alone --
        # confirmed by inspection it never imports domain_packs at all.

    def test_32_manifest_hash_unaffected_by_runtime_pack_version(self, monkeypatch):
        from scripts.pettripfinder.importer.batch import BatchManifest, compute_manifest_hash

        manifest = BatchManifest(
            manifest_schema_version=C.BATCH_MANIFEST_SCHEMA_VERSION, batch_id="b1",
            batch_name="t", defaults={}, jobs=(_job("hotels"),))
        hash_before = compute_manifest_hash(manifest)

        import dataclasses
        from scripts.pettripfinder.importer.domain_packs import registry as registry_mod
        original_pack = registry_mod.default_registry.for_category("hotels")
        bumped_pack = dataclasses.replace(original_pack, pack_version="9.9.9")
        monkeypatch.setitem(
            registry_mod.default_registry._by_category, "hotels", bumped_pack)

        hash_after = compute_manifest_hash(manifest)
        assert hash_after == hash_before


# --------------------------------------------------------------------------- #
# 33-34. CLI category acceptance (via the existing IMPORTER_CATEGORIES
# constant, which batch.py/import_official_url(s).py already read directly --
# untouched in AES-DATA-003A; this proves it stays exactly registry-aligned).
# --------------------------------------------------------------------------- #

class TestCliCategoryAcceptance:
    def test_33_cli_still_accepts_the_three_existing_categories(self):
        assert set(C.IMPORTER_CATEGORIES) == set(default_registry.category_ids())
        for cat in C.IMPORTER_CATEGORIES:
            default_registry.for_category(cat)   # must not raise

    def test_34_no_split_or_service_combination_category_is_registered(self):
        # AES-DATA-003C update: "boarding"/"grooming"/"pet_store" ARE now
        # registered categories (that is this phase's whole point) -- but no
        # split-by-service-combination category is ever registered for any
        # of the four service categories (mission doctrine #1/#12): a
        # boarding business that also grooms stays category "boarding" with
        # grooming_offered=true, never a separate category.
        assert default_registry.category_ids() == (
            "hotels", "parks", "restaurants", "veterinary",
            "boarding", "grooming", "pet_store")
        for registered in ("veterinary", "boarding", "grooming", "pet_store"):
            assert registered in C.IMPORTER_CATEGORIES
        for unregistered in (
            "emergency-vet", "urgent-vet", "animal-hospital", "specialty-vet",
            "daycare", "dog_daycare", "cat_boarding", "mobile_grooming",
            "self_wash", "pet_pharmacy", "pet-store",   # hyphenated form: not the id
        ):
            assert unregistered not in C.IMPORTER_CATEGORIES
            with pytest.raises(UnknownCategoryError):
                default_registry.for_category(unregistered)


# --------------------------------------------------------------------------- #
# 35. No production CSV mutation.
# --------------------------------------------------------------------------- #

class TestNoProductionMutation:
    def test_35_no_production_csv_mutation(self):
        before = hashlib.sha256(_SEED_CSV.read_bytes()).hexdigest()
        # Exercise the registry/pack machinery -- none of it ever touches
        # the filesystem outside what the caller explicitly passes in.
        for cat in default_registry.category_ids():
            pack = default_registry.for_category(cat)
            pack.compose_summary({"pets_allowed": "true"})
        after = hashlib.sha256(_SEED_CSV.read_bytes()).hexdigest()
        assert before == after


# --------------------------------------------------------------------------- #
# Golden byte-identity proof (Task 11): Drury / Scioto Audubon / Land-Grant,
# generated from checked-in static fixtures with fixed inputs, compared
# against the pre-refactor golden files captured before any AES-DATA-003A
# implementation change. No network, no live directory dependency.
# --------------------------------------------------------------------------- #

_OBSERVED_AT = "2026-07-17"
_CREATED_AT = "1970-01-01T00:00:00"


class TestGoldenByteIdentity:
    def test_17_drury_byte_identical(self, tmp_path):
        from scripts.import_official_url import _build_static, import_url
        from scripts.pettripfinder.importer.models import ImportContext

        url = "https://www.druryhotels.test/polaris"
        fixture = str(_REPO_ROOT / "tests/pettripfinder/importer/fixtures/hotel_01_strong.json")
        ctx = ImportContext(
            category="hotels", candidate_name="Drury Inn & Suites Columbus Dublin",
            expected_city="Columbus", expected_state="OH",
            source_relationship_hint="EXACT_ENTITY_DOMAIN")
        fetcher, extractor = _build_static(url, fixture)
        candidate, _json_path, _report_path = import_url(
            url, ctx, fetcher=fetcher, extractor=extractor, output_root=str(tmp_path),
            observed_at=_OBSERVED_AT, created_at=_CREATED_AT)

        expected = (_GOLDEN_DIR / "golden_drury.json").read_text(encoding="utf-8")
        assert dumps_candidate(candidate) + "\n" == expected
        assert candidate.sources == ()
        assert candidate.aggregation_version == ""
        assert candidate.recommendation == C.RECOMMEND_READY

    def test_18_scioto_byte_identical(self, tmp_path):
        from scripts.import_official_url import _build_static, import_url
        from scripts.pettripfinder.importer.models import ImportContext

        url = "https://www.metroparks.test/scioto"
        fixture = str(_REPO_ROOT / "tests/pettripfinder/importer/fixtures/park_01_offleash.json")
        ctx = ImportContext(
            category="parks", candidate_name="Scioto Audubon",
            expected_city="Columbus", expected_state="OH",
            source_relationship_hint="EXACT_ENTITY_DOMAIN")
        fetcher, extractor = _build_static(url, fixture)
        candidate, _json_path, _report_path = import_url(
            url, ctx, fetcher=fetcher, extractor=extractor, output_root=str(tmp_path),
            observed_at=_OBSERVED_AT, created_at=_CREATED_AT)

        expected = (_GOLDEN_DIR / "golden_scioto.json").read_text(encoding="utf-8")
        assert dumps_candidate(candidate) + "\n" == expected
        assert candidate.sources == ()
        assert candidate.aggregation_version == ""
        assert candidate.recommendation == C.RECOMMEND_READY

    def test_19_landgrant_byte_identical(self, tmp_path):
        from scripts.import_official_urls import _build_static_multi, import_urls
        from scripts.pettripfinder.importer.models import ImportContext

        faq_url = "https://landgrantbrewing.com/faq/"
        contact_url = "https://landgrantbrewing.com/contact/"
        faq_fixture = str(
            _REPO_ROOT / "tests/pettripfinder/importer/fixtures/aggregate_landgrant_faq.json")
        contact_fixture = str(
            _REPO_ROOT / "tests/pettripfinder/importer/fixtures/aggregate_landgrant_contact.json")
        ctx = ImportContext(
            category="restaurants", expected_city="Columbus", expected_state="OH",
            candidate_name="Land-Grant Brewing Columbus",
            source_relationship_hint="EXACT_ENTITY_DOMAIN")
        fetcher, extractor = _build_static_multi(
            [faq_url, contact_url], [faq_fixture, contact_fixture])
        candidate, _json_path, _report_path = import_urls(
            [faq_url, contact_url], ctx, fetcher=fetcher, extractor=extractor,
            output_root=str(tmp_path), observed_at=_OBSERVED_AT, created_at=_CREATED_AT)

        expected = (_GOLDEN_DIR / "golden_landgrant.json").read_text(encoding="utf-8")
        assert dumps_candidate(candidate) + "\n" == expected
        assert len(candidate.sources) == 2
        assert [s.source_id for s in candidate.sources] == ["S1", "S2"]
        assert candidate.aggregation_version == "1.0.0"
        assert candidate.recommendation == C.RECOMMEND_READY
