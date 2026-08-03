"""PTF-DISCOVERY-001 WO-1A Step 2 -- DiscoveryRunContext and replay hashing.

Proves ``INV-DET-EFFECTIVE-TIME``: identical inputs under an identical run
context hash identically, and varying only a network retrieval timestamp does
not perturb the hash. Also proves the additive ``run_context_ref`` field did
not break loading of candidates serialized before it existed.
"""

from __future__ import annotations

import dataclasses
import json

import pytest

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.models import (
    DiscoveryCandidate, DiscoveryRecord, WebsiteResolution,
)
from scripts.pettripfinder.discovery.run_context import (
    VOLATILE_HASH_FIELDS,
    DiscoveryRunContext,
    candidate_content_hash,
    candidates_content_hash,
    content_hash_for,
    strip_volatile,
)
from scripts.pettripfinder.discovery.serialization import (
    candidate_from_dict, candidate_to_dict, dumps_candidates, loads_candidates,
)

EFFECTIVE = "2026-08-02"


def _context(**kw):
    base = dict(run_id="run-columbus-001", effective_time=EFFECTIVE)
    base.update(kw)
    return DiscoveryRunContext(**base)


def _record(**kw):
    base = dict(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="gp1",
                canonical_category=C.CATEGORY_HOTEL, name="Test Hotel",
                normalized_name="test hotel", address_line="1 Main St",
                city="Columbus", state="OH", postal_code="43215",
                website_url="https://example.com", observed_at=EFFECTIVE)
    base.update(kw)
    return DiscoveryRecord(**base)


def _candidate(**kw):
    r = kw.pop("record", None) or _record()
    base = dict(candidate_id="dc_test0001", source_records=(r,),
                name=r.name, normalized_name=r.normalized_name,
                city=r.city, state=r.state, address_line=r.address_line)
    base.update(kw)
    return DiscoveryCandidate(**base)


class TestContextIdentity:
    def test_is_immutable(self):
        ctx = _context()
        with pytest.raises(dataclasses.FrozenInstanceError):
            ctx.effective_time = "2026-01-01"          # type: ignore[misc]

    def test_carries_every_amendment_field(self):
        names = {f.name for f in dataclasses.fields(DiscoveryRunContext)}
        assert names == {
            "run_id", "effective_time", "market_registry_version",
            "provider_terms_registry_version", "scoring_version",
            "normalizer_version", "deduplication_version",
            "official_url_resolver_version", "adapter_registry_version",
            "software_version",
        }

    def test_round_trips(self):
        ctx = _context()
        assert DiscoveryRunContext.from_dict(ctx.to_dict()) == ctx

    def test_hash_is_stable_and_version_sensitive(self):
        a = _context()
        assert a.content_hash() == _context().content_hash()
        assert a.content_hash() != _context(normalizer_version="normalizer-v2").content_hash()

    def test_ref_is_the_run_id(self):
        assert _context().ref() == "run-columbus-001"


class TestReplayDeterminism:
    def test_same_inputs_same_context_same_hash(self):
        ctx = _context()
        assert candidate_content_hash(_candidate(), context=ctx) == \
               candidate_content_hash(_candidate(), context=ctx)

    def test_effective_time_is_included(self):
        """effective_time is a canonical input, not an operational stamp."""
        c = _candidate()
        assert candidate_content_hash(c, context=_context()) != \
               candidate_content_hash(c, context=_context(effective_time="2026-01-01"))

    def test_a_version_change_changes_the_hash(self):
        c = _candidate()
        assert candidate_content_hash(c, context=_context()) != \
               candidate_content_hash(c, context=_context(deduplication_version="dedup-v2"))

    def test_network_retrieval_timestamp_does_not_change_the_hash(self):
        """The core INV-DET-EFFECTIVE-TIME claim. ``WebsiteResolution``
        carries the network timestamp; two payloads differing only there must
        hash identically."""
        early = WebsiteResolution(
            candidate_id="dc_test0001", source_provider=C.PROVIDER_GOOGLE_PLACES,
            original_url="https://example.com", normalized_url="https://example.com",
            registrable_domain="example.com", resolution_state=C.WEBSITE_RES_PROPERTY_URL_PROBABLE,
            retrieved_at="2026-08-02T01:00:00Z", cache_reference="/tmp/a.json")
        late = dataclasses.replace(
            early, retrieved_at="2026-08-02T23:59:59Z", cache_reference="/tmp/b.json")
        ctx = _context()
        assert content_hash_for(dataclasses.asdict(early), context=ctx) == \
               content_hash_for(dataclasses.asdict(late), context=ctx)

    def test_a_real_field_change_still_changes_the_hash(self):
        """Guards the guard: the exclusion must not be so broad that real
        differences stop registering."""
        early = WebsiteResolution(
            candidate_id="dc_test0001", source_provider=C.PROVIDER_GOOGLE_PLACES,
            original_url="https://example.com", normalized_url="https://example.com",
            registrable_domain="example.com", resolution_state=C.WEBSITE_RES_PROPERTY_URL_PROBABLE,
            retrieved_at="2026-08-02T01:00:00Z")
        changed = dataclasses.replace(early, resolution_state=C.WEBSITE_RES_CHAIN_HOMEPAGE_ONLY)
        ctx = _context()
        assert content_hash_for(dataclasses.asdict(early), context=ctx) != \
               content_hash_for(dataclasses.asdict(changed), context=ctx)

    def test_run_context_ref_does_not_feed_its_own_hash(self):
        ctx = _context()
        assert candidate_content_hash(_candidate(), context=ctx) == \
               candidate_content_hash(_candidate(run_context_ref=ctx.ref()), context=ctx)

    def test_candidate_ordering_is_part_of_run_identity(self):
        ctx = _context()
        a = _candidate(candidate_id="dc_aaa")
        b = _candidate(candidate_id="dc_bbb")
        assert candidates_content_hash([a, b], context=ctx) != \
               candidates_content_hash([b, a], context=ctx)

    def test_strip_volatile_removes_exactly_the_named_fields(self):
        payload = {"keep": 1, "retrieved_at": "x", "cache_reference": "y",
                   "run_context_ref": "z", "nested": {"retrieved_at": "x", "keep": 2}}
        assert strip_volatile(payload) == {"keep": 1, "nested": {"keep": 2}}
        assert VOLATILE_HASH_FIELDS == {"retrieved_at", "cache_reference", "run_context_ref"}


class TestAdditiveFieldIsBackwardCompatible:
    def test_run_context_ref_defaults_empty(self):
        assert _candidate().run_context_ref == ""

    def test_a_candidate_serialized_before_the_field_existed_still_loads(self):
        """The real backward-compatibility case: a dict with no
        ``run_context_ref`` key at all."""
        d = candidate_to_dict(_candidate())
        d.pop("run_context_ref")
        restored = candidate_from_dict(d)
        assert restored.run_context_ref == ""
        assert restored.candidate_id == "dc_test0001"

    def test_round_trip_still_byte_stable(self):
        cands = (_candidate(),)
        blob = dumps_candidates(cands)
        assert dumps_candidates(loads_candidates(blob)) == blob

    def test_the_field_is_carried_when_set(self):
        ctx = _context()
        c = _candidate(run_context_ref=ctx.ref())
        assert candidate_from_dict(candidate_to_dict(c)).run_context_ref == "run-columbus-001"
