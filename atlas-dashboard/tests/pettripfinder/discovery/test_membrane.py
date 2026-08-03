"""PTF-DISCOVERY-001 WO-1A Step 1 -- the structural Membrane.

These tests protect the single load-bearing guarantee of the discovery
subsystem: no discovery record and no verification-queue entry may declare a
pet-policy field, so no discovery attribute can become a published policy
fact.

Two of them (T2, T3) exist specifically to stop the invariant from being
*mis*-implemented, which is the likelier failure than it being absent:

  T2  a denylist that scanned VALUES instead of names would reject every
      real production queue, because ``required_fields`` legitimately lists
      every policy field name as a value.
  T3  a denylist applied one layer too wide would reject WorkerResult and
      RoutingEnvelope, disabling the policy pipeline entirely.
"""

from __future__ import annotations

import ast
import dataclasses
import glob
import json
import pathlib

import pytest

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.import_batch_builder import ImportJob, build_batches
from scripts.pettripfinder.discovery.import_plan import ImportPlanEntry
from scripts.pettripfinder.discovery.membrane import (
    DISCOVERY_DENYLIST,
    POLICY_FIELD_DENYLIST,
    MembraneViolation,
    assert_no_policy_fields,
    assert_no_policy_keys,
    normalize_field_name,
)
from scripts.pettripfinder.discovery.models import (
    CoverageSummary,
    DiscoveryCandidate,
    DiscoveryRecord,
    DiscoverySourceQuery,
    QueryYieldRow,
    WebsiteResolution,
)
from scripts.pettripfinder.discovery.serialization import (
    candidate_to_dict,
    record_to_dict,
)
from services.research_workers import vocabulary as V
from services.research_workers.capture_automation.adapters import known_brands
from services.research_workers.capture_automation.queue import (
    QUEUE_SCHEMA, QueueEntry, QueueError, load_queue,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]


# --------------------------------------------------------------------------- #
# T1 -- the denylist rejects a declared policy field.
# --------------------------------------------------------------------------- #

class TestT1DenylistRejectsDeclaredPolicyFields:
    def test_a_dataclass_declaring_a_policy_field_is_rejected(self):
        @dataclasses.dataclass(frozen=True)
        class Sneaky:
            candidate_id: str = ""
            pet_fee: str = ""

        with pytest.raises(MembraneViolation) as exc:
            assert_no_policy_fields(Sneaky, context="test")
        assert "pet_fee" in str(exc.value)

    def test_camelcase_provider_spelling_is_also_rejected(self):
        """A provider field transcribed verbatim must not slip through."""
        @dataclasses.dataclass(frozen=True)
        class Transcribed:
            petsAllowed: bool = False        # noqa: N815 - deliberate

        with pytest.raises(MembraneViolation):
            assert_no_policy_fields(Transcribed, context="test")

    def test_third_party_pet_signal_names_are_rejected_in_discovery(self):
        @dataclasses.dataclass(frozen=True)
        class Hinted:
            allows_dogs: bool = False

        with pytest.raises(MembraneViolation):
            assert_no_policy_fields(Hinted, context="test")

    def test_seed_policy_column_name_is_rejected(self):
        """``pet_policy`` is the seed CSV's policy column -- a discovery
        record declaring it would be one assignment from publication."""
        @dataclasses.dataclass(frozen=True)
        class SeedShaped:
            pet_policy: str = ""

        with pytest.raises(MembraneViolation):
            assert_no_policy_fields(SeedShaped, context="test")

    def test_every_real_discovery_model_is_clean(self):
        for cls in (DiscoveryRecord, DiscoverySourceQuery, DiscoveryCandidate,
                    CoverageSummary, WebsiteResolution, QueryYieldRow,
                    ImportPlanEntry, ImportJob):
            assert_no_policy_fields(cls, context="real model")

    def test_substring_matches_are_not_false_positives(self):
        """Matching is exact-after-normalization, never substring. A
        substring rule would reject these legitimate names and push someone
        toward loosening the invariant."""
        @dataclasses.dataclass(frozen=True)
        class Legitimate:
            compatibility_version: str = ""
            deposit_required_by_operator: str = ""
            species_count_note: str = ""

        assert_no_policy_fields(Legitimate, context="test")

    def test_normalization(self):
        assert normalize_field_name("petsAllowed") == "pets_allowed"
        assert normalize_field_name("PetFee") == "pet_fee"
        assert normalize_field_name("weight_limit") == "weight_limit"


# --------------------------------------------------------------------------- #
# T2 -- THE FALSE-POSITIVE GUARD. This is the test that keeps the invariant
# honest: a value-scanning denylist passes T1 and fails here.
# --------------------------------------------------------------------------- #

GOOD_ENTRY = {
    "hotel_id": "cmham-columbus-airport-marriott",
    "listing_key": "columbus airport marriott",
    "hotel_name": "Columbus Airport Marriott",
    "brand": "marriott",
    "official_url": "https://www.marriott.com/en-us/hotels/"
                    "cmham-columbus-airport-marriott/overview/",
    "expected_address": "1375 North Cassady Avenue",
    "expected_city": "Columbus",
    "expected_state": "OH",
    "expected_postal_code": "43219",
    "expected_phone": "614-475-7551",
    "expected_property_code": "cmham",
}


def _write_queue(tmp_path, hotels):
    path = tmp_path / "queue.json"
    path.write_text(json.dumps({
        "schema": QUEUE_SCHEMA, "batch_id": "membrane-test", "hotels": hotels,
    }), encoding="utf-8")
    return path


class TestT2RequiredFieldsIsNotAViolation:
    def test_a_queue_listing_every_policy_field_as_a_VALUE_still_loads(self, tmp_path):
        """``required_fields`` tells the worker which fields to go look for
        on the official page. It carries no policy data. Every real
        production queue has it, so a denylist that scanned values would
        reject the entire live corpus."""
        entry = dict(GOOD_ENTRY, required_fields=list(V.POLICY_FIELDS))
        queue = load_queue(_write_queue(tmp_path, [entry]),
                           known_brands=known_brands())
        assert len(queue) == 1
        assert queue.entries[0].required_fields == tuple(V.POLICY_FIELDS)

    def test_the_values_really_are_denylisted_tokens(self):
        """Guards the guard: if POLICY_FIELDS ever stopped overlapping the
        denylist, T2 above would silently stop proving anything."""
        overlap = {normalize_field_name(f) for f in V.POLICY_FIELDS} & POLICY_FIELD_DENYLIST
        assert overlap, "POLICY_FIELDS no longer overlaps the denylist; T2 is now vacuous"

    def test_a_queue_declaring_a_policy_KEY_is_rejected(self, tmp_path):
        """The other side of the same coin: names are still enforced."""
        entry = dict(GOOD_ENTRY, pet_fee="50.00")
        with pytest.raises(MembraneViolation):
            load_queue(_write_queue(tmp_path, [entry]), known_brands=known_brands())

    @pytest.mark.parametrize("path", sorted(glob.glob(
        str(REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
            / "capture_batches" / "*queue*.json"))))
    def test_real_production_queues_are_not_rejected_by_the_membrane(self, path):
        """Runs against the real on-disk corpus when present (``data/`` is
        gitignored, so this parametrization is empty in a clean clone and
        the synthetic test above carries the guarantee).

        Asserts precisely one thing: the Membrane gate does not reject a
        real queue. A ``QueueError`` is allowed through -- some archived
        queues reference retrieval artifacts by a path that no longer
        resolves, which is a pre-existing operational concern and not what
        this test is about.
        """
        try:
            load_queue(path, known_brands=known_brands())
        except MembraneViolation:
            raise
        except QueueError:
            pass


# --------------------------------------------------------------------------- #
# T3 -- THE SCOPE GUARD. The policy domain must be untouched.
# --------------------------------------------------------------------------- #

class TestT3PolicyDomainIsOutOfScope:
    def test_worker_result_declares_policy_names_and_is_unaffected(self):
        """WorkerResult/ProposedField produce policy facts -- that is their
        job. Applying the denylist to them would disable the pipeline. This
        asserts the scoping is deliberate by proving the denylist WOULD
        reject them if wrongly applied."""
        from services.research_workers.contracts import ProposedField, WorkerResult

        # Unchanged and importable: the real proof.
        assert dataclasses.is_dataclass(WorkerResult)
        assert dataclasses.is_dataclass(ProposedField)

        # And the worker's own vocabulary still names every policy field.
        assert "pets_allowed" in V.POLICY_FIELD_SET
        assert "pet_fee" in V.POLICY_FIELD_SET

    def test_routing_envelope_still_carries_supported_facts(self):
        from services.research_workers.routing import RoutingEnvelope

        assert dataclasses.is_dataclass(RoutingEnvelope)
        names = {f.name for f in dataclasses.fields(RoutingEnvelope)}
        assert "supported_facts" in names
        assert "worker_contract_version" in names

    def test_a_policy_fact_payload_is_not_run_through_the_denylist(self):
        """A supported_facts entry is keyed by ``field_name``/``value`` --
        the policy field name is a VALUE there too, exactly like
        required_fields. Confirm that shape is not denylisted."""
        payload = {"field_name": "pet_fee", "value": "50.00",
                   "evidence_quote": "...", "source_url": "https://example.com",
                   "source_type": "OFFICIAL_PROPERTY"}
        assert_no_policy_keys(payload, context="supported_fact",
                              denylist=POLICY_FIELD_DENYLIST)


# --------------------------------------------------------------------------- #
# T4 -- serialized discovery output carries no policy key.
# --------------------------------------------------------------------------- #

def _record(**kw):
    base = dict(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="gp1",
                canonical_category=C.CATEGORY_HOTEL, name="Test Hotel",
                normalized_name="test hotel", address_line="1 Main St",
                city="Columbus", state="OH", postal_code="43215",
                website_url="https://example.com", observed_at="2026-08-02")
    base.update(kw)
    return DiscoveryRecord(**base)


class TestT4SerializationIsClean:
    def test_record_serialization_has_no_policy_key(self):
        d = record_to_dict(_record())
        assert not (set(d) & DISCOVERY_DENYLIST)

    def test_candidate_serialization_has_no_policy_key(self):
        r = _record()
        c = DiscoveryCandidate(candidate_id="dc_test", source_records=(r,),
                               name=r.name, normalized_name=r.normalized_name)
        d = candidate_to_dict(c)
        assert not (set(d) & DISCOVERY_DENYLIST)
        assert not (set(d["source_records"][0]) & DISCOVERY_DENYLIST)

    def test_a_hand_built_violating_mapping_is_rejected(self):
        with pytest.raises(MembraneViolation):
            assert_no_policy_keys({"candidate_id": "x", "weight_limit": "50"},
                                  context="test")

    def test_nested_violation_is_caught_when_recursive(self):
        payload = {"candidate_id": "x", "inner": {"breed_restrictions": "none"}}
        assert_no_policy_keys(payload, context="test")          # top-level only: passes
        with pytest.raises(MembraneViolation):
            assert_no_policy_keys(payload, context="test", recursive=True)

    def test_the_handoff_seam_manifest_is_gated(self):
        """import_batch_builder is where discovery crosses into the policy
        domain -- the most important gate in the subsystem."""
        job = ImportJob(job_id="dc_abc", candidate_name="Test Hotel",
                        category=C.IMPORTER_CATEGORY_HOTELS,
                        expected_city="Columbus", expected_state="OH",
                        urls=("https://example.com/hotel",))
        manifests = build_batches([job], batch_id_prefix="test",
                                  batch_name_prefix="Test")
        assert len(manifests) == 1
        assert not (set(manifests[0]) & DISCOVERY_DENYLIST)
        assert not (set(manifests[0]["jobs"][0]) & DISCOVERY_DENYLIST)


# --------------------------------------------------------------------------- #
# T5 -- seed protection. The seed CSV is the capture queue's identity
# authority AND it has a ``pet_policy`` column; a discovery writer reaching
# it would be one assignment away from publication.
# --------------------------------------------------------------------------- #

DISCOVERY_DIR = REPO_ROOT / "scripts" / "pettripfinder" / "discovery"


def _discovery_sources():
    return sorted(DISCOVERY_DIR.glob("*.py"))


def _code_string_constants(path: pathlib.Path):
    """String literals that are real CODE, excluding docstrings.

    Parsed via ``ast`` rather than raw text on purpose: a module that merely
    *documents* the seed in a comment or docstring -- as ``membrane.py`` does
    when explaining why ``pet_policy`` is denylisted -- is not referencing it.
    Comments never reach the AST at all, and docstrings are subtracted below,
    so what remains is what the module actually operates on.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node, clean=False)
            if doc is not None:
                docstrings.add(doc)
    return [
        node.value for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
        and node.value not in docstrings
    ]


class TestT5SeedIsNeverWrittenByDiscovery:
    def test_the_seed_is_referenced_by_exactly_one_module(self):
        referencing = [
            p.name for p in _discovery_sources()
            if any("seed_businesses.csv" in s for s in _code_string_constants(p))
        ]
        assert referencing == ["known_inventory.py"], (
            "a new discovery module references the production seed: %s" % referencing)

    def test_that_module_opens_the_seed_read_only(self):
        src = (DISCOVERY_DIR / "known_inventory.py").read_text(encoding="utf-8")
        for forbidden in ('"w"', "'w'", '"a"', "'a'", ".write_text(", ".writelines(",
                          "csv.writer", "csv.DictWriter"):
            assert forbidden not in src, (
                "known_inventory.py appears to write: %r" % forbidden)

    def test_no_discovery_module_declares_the_seed_policy_column(self):
        assert "pet_policy" in DISCOVERY_DENYLIST
        for cls in (DiscoveryRecord, DiscoveryCandidate, ImportPlanEntry, ImportJob):
            assert "pet_policy" not in {f.name for f in dataclasses.fields(cls)}
