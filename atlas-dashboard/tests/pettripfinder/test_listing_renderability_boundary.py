"""PTF-INVENTORY-001 -- the PetTripFinder -> Website Generation Engine
renderability boundary.

The seed CSV is the single authoritative inventory and carries listings in two
evidence states: rows backed by retrieved official policy evidence, and rows
still pending official-source attestation. Only the former may be handed to the
WGE; a pending row has no policy text to bind, so letting it reach
ComponentManifest compilation raises ComponentResolutionError -- and, worse,
would publish a hotel we cannot substantiate.

These tests pin the boundary itself: the filter is pure, it decides on state
and contract semantics only (never on hotel names, brands, or hard-coded
listing ids), it fails closed on states it does not recognise, and it leaves
the authoritative seed untouched.

All offline: no network, no model call, no production write.
"""

from __future__ import annotations

import csv
import pathlib
import re

import pytest

from scripts.generate_pettripfinder_pilot import (
    LAUNCH_PACKAGE_DIR,
    load_launch_package,
    read_seed_businesses_csv,
)
from scripts.pettripfinder.listing_dataset_builder import (
    EVIDENCE_FIELD,
    KNOWN_READINESS_STATES,
    LISTING_PENDING_EVIDENCE,
    LISTING_RENDERABLE,
    LISTING_UNRECOGNIZED,
    READINESS_FIELD,
    RENDERABLE_STATES,
    build_listing_dataset,
    listing_readiness,
    partition_by_renderability,
)
from scripts.pettripfinder.publication_guard import distinct_entity_groups

_SEED_CSV = pathlib.Path(LAUNCH_PACKAGE_DIR) / "seed_businesses.csv"

# Named here as an *expected outcome* to assert against -- never as filter input.
#
# Hotels still awaiting attestation. Nine hotels attested and approved on
# 2026-07-29 are deliberately ABSENT: their seed rows now carry the attested
# policy text and they publish. A hotel leaving this set is the intended
# lifecycle -- pending is a state hotels pass through, not one they sit in.
# What must stay true is that whatever IS pending never reaches the engine.
# EMPTY as of 2026-07-30: every seeded hotel is now evidence-backed. Pending is
# a state hotels pass through, not one they sit in, so an empty set is the
# healthy end state rather than a disabled test. The boundary MECHANISM stays
# fully exercised by the synthetic cases in TestListingReadiness and
# TestPartition above; what the real-seed tests below now assert is that the
# published inventory has nothing left to withhold.
_PENDING_NAMES = frozenset()


def _record(**over):
    base = {
        "name": "Sample Hotel",
        "category": "pet-friendly-hotels",
        "address": "1 Main St",
        "city": "Columbus",
        "state": "OH",
        "website_url": "https://example.invalid/",
        "source_url": "https://example.invalid/pets",
        "source_type": "OFFICIAL_PROPERTY",
        "observed_at": "2026-07-15",
        EVIDENCE_FIELD: "Pets are welcome for a $50 fee per stay.",
    }
    base.update(over)
    return base


@pytest.fixture(scope="module")
def package():
    return load_launch_package()


# --------------------------------------------------------------------------- #
# 1. Per-record state classification.
# --------------------------------------------------------------------------- #

class TestListingReadiness:
    def test_evidence_present_is_renderable(self):
        state, reason = listing_readiness(_record())
        assert state == LISTING_RENDERABLE
        assert reason == "evidence_present"

    def test_blank_evidence_is_pending(self):
        state, reason = listing_readiness(_record(**{EVIDENCE_FIELD: ""}))
        assert state == LISTING_PENDING_EVIDENCE
        assert reason == "missing_evidence"

    def test_whitespace_only_evidence_is_pending(self):
        """A cell holding only spaces is blank evidence, not evidence."""
        state, _ = listing_readiness(_record(**{EVIDENCE_FIELD: "   \t "}))
        assert state == LISTING_PENDING_EVIDENCE

    def test_absent_evidence_field_is_renderable(self):
        """A record whose schema has no evidence concept at all is not a
        PetTripFinder seed row -- it is a caller with a different contract
        (a synthetic WGE fixture). It must not be swept up by this filter."""
        rec = _record()
        del rec[EVIDENCE_FIELD]
        state, reason = listing_readiness(rec)
        assert state == LISTING_RENDERABLE
        assert reason == "evidence_field_absent_from_schema"

    def test_declared_state_wins_over_inference(self):
        """An explicit declaration is authoritative: a row may be held back
        even while carrying evidence text."""
        rec = _record(**{READINESS_FIELD: LISTING_PENDING_EVIDENCE})
        state, reason = listing_readiness(rec)
        assert state == LISTING_PENDING_EVIDENCE
        assert reason == "declared_state"

    def test_unrecognized_declared_state_fails_closed(self):
        """A state this module cannot interpret is not a state it may publish."""
        rec = _record(**{READINESS_FIELD: "SOMEDAY_MAYBE"})
        state, reason = listing_readiness(rec)
        assert state == LISTING_UNRECOGNIZED
        assert "SOMEDAY_MAYBE" in reason
        assert state not in RENDERABLE_STATES
        assert state not in KNOWN_READINESS_STATES


# --------------------------------------------------------------------------- #
# 2. Partition semantics.
# --------------------------------------------------------------------------- #

class TestPartition:
    def test_splits_and_reports_every_exclusion(self):
        rows = [_record(name="Keep A"), _record(name="Drop B", **{EVIDENCE_FIELD: ""}),
                _record(name="Keep C")]
        renderable, excluded = partition_by_renderability(rows)
        assert [r["name"] for r in renderable] == ["Keep A", "Keep C"]
        assert len(excluded) == 1
        assert "Drop B" in excluded[0] and "missing_evidence" in excluded[0]

    def test_is_non_mutating(self):
        """A pending listing is never rewritten to look ready."""
        pending = _record(name="Pending", **{EVIDENCE_FIELD: ""})
        before = dict(pending)
        partition_by_renderability([pending, _record()])
        assert pending == before

    def test_decides_on_state_not_identity(self):
        """The same hotel flips sides purely on its evidence state -- the name,
        brand, and url are identical across both cases. Nothing about a
        listing's identity may influence the decision."""
        name, url = "Hilton Columbus at Easton", "https://hilton.invalid/easton"
        pending = _record(name=name, website_url=url, **{EVIDENCE_FIELD: ""})
        backed = _record(name=name, website_url=url,
                         **{EVIDENCE_FIELD: "Pets welcome, $75 per stay."})

        assert partition_by_renderability([pending])[0] == []
        assert [r["name"] for r in partition_by_renderability([backed])[0]] == [name]

    def test_no_brand_or_id_literals_in_the_filter(self):
        """Guard against a future 'quick fix' that hard-codes a hotel out.
        The boundary module must contain no brand/property literals."""
        src = pathlib.Path(
            "scripts/pettripfinder/listing_dataset_builder.py"
        ).read_text(encoding="utf-8")
        for brand in ("Hilton", "Home2", "TownePlace", "Aloft", "Hampton", "Marriott"):
            assert brand not in src, brand


# --------------------------------------------------------------------------- #
# 3. The real seed, end to end.
# --------------------------------------------------------------------------- #

class TestRealSeedBoundary:
    def test_real_build_excludes_exactly_the_pending_rows(self, package):
        result = build_listing_dataset(
            seed_businesses=package["seed_businesses"],
            categories=package["categories"],
            locations=package["locations"],
            distinct_entity_groups=distinct_entity_groups(),
        )
        assert result.ok
        assert result.errors == ()
        assert len(package["seed_businesses"]) == 103
        assert len(result.dataset.listings) == 103
        assert result.excluded_pending_count == 0

    def test_every_exclusion_names_a_pending_hotel_and_its_reason(self, package):
        result = build_listing_dataset(
            seed_businesses=package["seed_businesses"],
            categories=package["categories"],
            locations=package["locations"],
            distinct_entity_groups=distinct_entity_groups(),
        )
        excluded = result.excluded_pending
        assert len(excluded) == len(_PENDING_NAMES)
        # Whatever IS excluded must name a pending hotel and give its reason.
        # Vacuous while the inventory is fully backed, and load-bearing again
        # the moment a new hotel is seeded ahead of its evidence.
        for entry in excluded:
            assert "PENDING_EVIDENCE=missing_evidence" in entry
            assert any(n in entry for n in _PENDING_NAMES), entry
        for name in _PENDING_NAMES:
            assert any(name in e for e in excluded), name

    def test_every_seeded_hotel_is_now_evidence_backed(self, package):
        """The inventory reached zero pending. Any row losing its evidence must
        fail here rather than quietly disappearing from the public site."""
        hotels = [r for r in package["seed_businesses"]
                  if r.get("category") == "pet-friendly-hotels"]
        assert len(hotels) == 76
        assert [r["name"] for r in hotels
                if not str(r.get(EVIDENCE_FIELD, "")).strip()] == []

    def test_no_pending_listing_reaches_the_engine(self, package):
        """The load-bearing assertion: nothing pending is in the dataset the
        WGE compiles, by name or by slug."""
        result = build_listing_dataset(
            seed_businesses=package["seed_businesses"],
            categories=package["categories"],
            locations=package["locations"],
            distinct_entity_groups=distinct_entity_groups(),
        )
        names = {l.business_name for l in result.dataset.listings}
        assert not (names & _PENDING_NAMES)
        # Also by slug, so a pending hotel cannot slip through under a
        # differently-spelled display name. Slugified the same way the builder
        # does, rather than by substring guesswork.
        slugs = {l.listing_id for l in result.dataset.listings}
        for name in _PENDING_NAMES:
            pending_slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
            assert pending_slug not in slugs, name

    def test_every_delivered_listing_carries_evidence(self, package):
        """Positive form of the same guarantee: no listing is published
        without policy evidence behind it."""
        result = build_listing_dataset(
            seed_businesses=package["seed_businesses"],
            categories=package["categories"],
            locations=package["locations"],
            distinct_entity_groups=distinct_entity_groups(),
        )
        by_name = {r["name"]: r for r in package["seed_businesses"]}
        for listing in result.dataset.listings:
            row = by_name.get(listing.business_name)
            if row is not None and EVIDENCE_FIELD in row:
                assert str(row[EVIDENCE_FIELD]).strip(), listing.business_name

    def test_seed_remains_the_authoritative_inventory(self):
        """The boundary filters what is *rendered*, never what is *recorded*.
        All 33 hotel rows, pending included, stay in the one seed file."""
        with _SEED_CSV.open("r", encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        assert len(rows) == 103
        hotels = [r for r in rows if r["category"] == "pet-friendly-hotels"]
        assert len(hotels) == 76
        present = {r["name"] for r in hotels}
        assert _PENDING_NAMES <= present
        # And they are retained as real rows, not tombstones: identity intact.
        for row in hotels:
            if row["name"] in _PENDING_NAMES:
                assert row["website_url"].strip() and row["address"].strip()

    def test_both_seed_readers_agree(self, package):
        """generate_pettripfinder_pilot and promote_import_candidates each read
        the seed; if they disagree about blank-vs-absent evidence, the same row
        resolves to different readiness through the two paths."""
        from scripts.promote_import_candidates import _read_seed_rows

        direct = read_seed_businesses_csv(_SEED_CSV)
        importer = _read_seed_rows(_SEED_CSV)
        assert len(direct) == len(importer) == len(package["seed_businesses"])
        assert ([listing_readiness(r)[0] for r in direct]
                == [listing_readiness(r)[0] for r in importer])
        assert sum(1 for r in direct
                   if listing_readiness(r)[0] == LISTING_PENDING_EVIDENCE) == 0

    def test_build_is_deterministic(self, package):
        a = build_listing_dataset(seed_businesses=package["seed_businesses"],
                                  categories=package["categories"],
                                  locations=package["locations"],
                                  distinct_entity_groups=distinct_entity_groups())
        b = build_listing_dataset(seed_businesses=package["seed_businesses"],
                                  categories=package["categories"],
                                  locations=package["locations"],
                                  distinct_entity_groups=distinct_entity_groups())
        assert a.excluded_pending == b.excluded_pending
        assert ([l.listing_id for l in a.dataset.listings]
                == [l.listing_id for l in b.dataset.listings])
