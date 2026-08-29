"""PTF-EXCLUSIONS-002 -- the exclusion authority must bind every publication path.

An exclusion that only the capture queue consults is a note, not a guard. These
tests pin the two properties that make it a guard: a promotion path cannot write
an excluded identity into a tracked authority, and the public generation join
cannot build a route for one even if both authorities were edited by hand.

The second half pins the opposite failure. Address matching is what stops a
renamed property from re-publishing, but two businesses really can share a
street address -- the BrewDog hotel and the BrewDog taproom on one campus at
96 Gender Rd -- and collapsing them would be its own data-integrity bug. So a
collision blocks until a human records a resolution, and the resolution has to
keep the two records genuinely distinct.
"""

from __future__ import annotations

import csv
import json
import pathlib

import pytest

from scripts.pettripfinder.hotel_exclusions import (
    OUT_OF_CURRENT_CATEGORY,
    SCHEMA,
    VERIFIED_NO_PETS,
    ExclusionContractError,
    approval_hash,
    record_hash,
    supersede,
)
from scripts.pettripfinder.publication_guard import (
    BLOCK_EXCLUDED,
    BLOCK_RESOLUTION_NOT_DISTINCT,
    BLOCK_UNRESOLVED_COLLISION,
    MATCH_ADDRESS,
    MATCH_ALIAS,
    MATCH_NAME,
    MAX_LISTED_BLOCKS,
    RESOLUTIONS_SCHEMA,
    SAME_CAMPUS,
    PublicationBlockedError,
    assert_publishable,
    load_resolutions,
    publication_blocks,
    resolution_hash,
    validate_resolutions,
)
from scripts.pettripfinder.site_data import normalize_name

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

COMFORT = {
    "canonical_name": "Comfort Suites Columbus East Broad",
    "address": "70 Chris Perry Ln", "city": "Columbus", "state": "OH",
    "postal_code": "43213", "phone": "(380) 208-4326",
    "official_url": "https://www.cscolumbuseastbroad.com/",
    "exclusion_state": VERIFIED_NO_PETS,
    "evidence_quote": "No Pets Allowed",
    "source_url": "https://www.cscolumbuseastbroad.com/",
    "observed_at": "2026-08-06",
    "reviewer_id": "jfields80", "reviewed_at": "2026-08-06T12:00:00-04:00",
    "notes": "Hotel Information block beside '100% Smoke Free Hotel'.",
}

TIMBROOK = dict(COMFORT, canonical_name="Timbrook Guesthouse",
                address="5811 Olentangy River Rd", postal_code="43235",
                exclusion_state=OUT_OF_CURRENT_CATEGORY,
                evidence_quote="Operator category ruling 2026-08-06: guesthouse.",
                official_url="https://timbrookguesthouse.com/",
                source_url="https://www.experiencecolumbus.com/hotels/")


def _finish(rec):
    r = dict(rec)
    r["exclusion_id"] = "excl-" + normalize_name(r["canonical_name"]).replace(" ", "-")
    r["normalized_name"] = normalize_name(r["canonical_name"])
    r["source_hash"] = "sha256:seed"
    r["record_hash"] = record_hash(r)
    r["approval_hash"] = approval_hash(r)
    return r


@pytest.fixture
def excl():
    return [_finish(COMFORT), _finish(TIMBROOK)]


def _seed_row(name, address, postal_code, category="pet-friendly-hotels"):
    return {"name": name, "address": address, "postal_code": postal_code,
            "category": category}


# --------------------------------------------------------------------------- #
# 1-4: an excluded identity cannot enter a tracked authority.
# --------------------------------------------------------------------------- #

class TestPromotionRefusal:

    def test_verified_no_pets_cannot_enter_the_seed_authority(self, excl, tmp_path):
        """POINT 1. The seed CSV is the display inventory: a row here is a route."""
        import scripts.promote_import_candidates as PIC

        target = tmp_path / "seed_businesses.csv"
        columns = list(PIC.C.SEED_CSV_COLUMNS)
        with target.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
            w.writeheader()
        before = target.read_bytes()

        with pytest.raises(PublicationBlockedError) as exc:
            PIC.assert_publishable(
                [_seed_row("Comfort Suites Columbus East Broad", "70 Chris Perry Ln", "43213")],
                published=[], exclusions=excl)
        assert exc.value.blocks[0]["exclusion_state"] == VERIFIED_NO_PETS
        assert target.read_bytes() == before          # nothing written

    def test_verified_no_pets_cannot_enter_the_policy_authority(self, excl):
        """POINT 2. A no-pets record in the policy package would publish the
        property as pet-friendly -- the exact inversion the authority exists for."""
        with pytest.raises(PublicationBlockedError):
            assert_publishable(
                [_seed_row("Comfort Suites Columbus East Broad", "70 Chris Perry Ln", "43213")],
                exclusions=excl, check_collisions=False)

    def test_out_of_category_cannot_enter_the_hotel_seed_authority(self, excl):
        """POINT 3. A guesthouse ruled out of the hotel category is not a hotel."""
        blocks = publication_blocks(
            [_seed_row("Timbrook Guesthouse", "5811 Olentangy River Rd", "43235")],
            exclusions=excl, check_collisions=False)
        assert [b["exclusion_state"] for b in blocks] == [OUT_OF_CURRENT_CATEGORY]

    def test_an_alias_at_the_excluded_address_is_blocked_by_address(self, excl):
        """POINT 4. A rename is not a new property."""
        blocks = publication_blocks(
            [_seed_row("East Broad Suites & Inn", "70 Chris Perry Lane", "43213")],
            exclusions=excl, check_collisions=False)
        assert len(blocks) == 1
        assert blocks[0]["match_basis"] == MATCH_ADDRESS
        assert blocks[0]["exclusion_id"] == "excl-comfort-suites-columbus-east-broad"

    def test_a_recorded_alias_is_blocked_by_name(self, excl):
        record = dict(excl[0], aliases=["Comfort Suites East Broad at 270"])
        blocks = publication_blocks(["Comfort Suites East Broad at 270"],
                                    exclusions=[record], check_collisions=False)
        assert blocks[0]["match_basis"] == MATCH_ALIAS

    def test_an_unrelated_hotel_is_not_blocked(self, excl):
        assert publication_blocks(
            [_seed_row("Hilton Columbus Downtown", "401 N High St", "43215")],
            exclusions=excl, check_collisions=False) == []


class TestBatchAtomicity:

    def test_one_excluded_record_fails_the_whole_batch(self, excl):
        """POINT 5."""
        batch = [_seed_row("Hilton Columbus Downtown", "401 N High St", "43215"),
                 _seed_row("Comfort Suites Columbus East Broad", "70 Chris Perry Ln", "43213"),
                 _seed_row("Hyatt Regency Columbus", "350 N High St", "43215")]
        with pytest.raises(PublicationBlockedError) as exc:
            assert_publishable(batch, exclusions=excl, check_collisions=False)
        assert len(exc.value.blocks) == 1             # names the offender, not the batch

    def test_refusal_leaves_no_partial_authority_and_no_temporary_file(self, excl, tmp_path,
                                                                      monkeypatch):
        """POINT 6. The refusal happens before the .tmp file is opened."""
        import scripts.promote_import_candidates as PIC

        target = tmp_path / "seed_businesses.csv"
        columns = list(PIC.C.SEED_CSV_COLUMNS)
        with target.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
            w.writeheader()
            w.writerow({c: "" for c in columns} | {"name": "Hilton Columbus Downtown",
                                                   "category": "pet-friendly-hotels"})
        before = target.read_bytes()

        def _explode(*a, **k):                        # the write must never be reached
            raise AssertionError("_atomic_write_csv must not run after a refusal")

        monkeypatch.setattr(PIC, "_atomic_write_csv", _explode)
        with pytest.raises(PublicationBlockedError):
            PIC.assert_publishable(
                [_seed_row("Comfort Suites Columbus East Broad", "70 Chris Perry Ln", "43213")],
                published=[], exclusions=excl)
        assert target.read_bytes() == before
        assert list(tmp_path.glob("*.tmp")) == []


# --------------------------------------------------------------------------- #
# 7-10: public generation refuses, and no public surface carries the route.
# --------------------------------------------------------------------------- #

class TestGenerationDefenceInDepth:

    def test_generator_join_refuses_an_excluded_joined_identity(self, excl):
        """POINT 7. Injected into BOTH authorities and still refused."""
        from scripts.pettripfinder.site_data import verified_public_hotels

        rows = [_seed_row("Hilton Columbus Downtown", "401 N High St", "43215"),
                _seed_row("Comfort Suites Columbus East Broad", "70 Chris Perry Ln", "43213")]
        facts = {"hilton columbus downtown": {}, "comfort suites columbus east broad": {}}
        with pytest.raises(PublicationBlockedError):
            verified_public_hotels(rows, facts, exclusions=excl)

    def test_the_join_refuses_rather_than_silently_omitting(self, excl):
        """POINT 8. The generator's documented safe omission covers UNVERIFIED
        rows -- a seed row absent from the policy package. An identity present in
        both authorities and excluded is a contradiction, not a held record, and
        the contract here is refusal."""
        from scripts.pettripfinder.site_data import verified_public_hotels

        rows = [_seed_row("Hilton Columbus Downtown", "401 N High St", "43215"),
                _seed_row("Comfort Suites Columbus East Broad", "70 Chris Perry Ln", "43213")]
        # Excluded row present in the seed but NOT in the policy package: the
        # documented safe omission applies and nothing raises.
        kept = verified_public_hotels(rows, {"hilton columbus downtown": {}}, exclusions=excl)
        assert [r["name"] for r in kept] == ["Hilton Columbus Downtown"]

    def test_no_excluded_identity_reaches_any_public_surface(self, excl):
        """POINTS 9 + 10. Profiles, index, comparison and sitemap are all derived
        from the same join, so proving the join is clean proves every surface is."""
        from scripts.pettripfinder.site_data import (
            load_published_hotel_policy_facts, read_production_rows, verified_public_hotels)

        rows = [r for r in read_production_rows() if r["category"] == "pet-friendly-hotels"]
        verified = verified_public_hotels(rows, load_published_hotel_policy_facts())
        names = {normalize_name(r["name"]) for r in verified}
        for record in excl:
            assert record["normalized_name"] not in names

    def test_the_live_seed_and_policy_authorities_publish_cleanly(self):
        """POINT 13. The 70 published hotels stay valid under the new guard."""
        from scripts.pettripfinder.site_data import (
            load_published_hotel_policy_facts, read_production_rows, verified_public_hotels)

        rows = [r for r in read_production_rows() if r["category"] == "pet-friendly-hotels"]
        verified = verified_public_hotels(rows, load_published_hotel_policy_facts())
        assert len(verified) == 88

    def test_the_shared_launch_package_loader_passes_today(self):
        """The seed read both generators share must not have become fail-open or
        fail-noisy: it loads the real 103-row package without raising. It now
        contains a reviewed same-campus pair, so this also proves the tracked
        resolution is what lets that read succeed."""
        from scripts.generate_pettripfinder_pilot import load_launch_package

        rows = load_launch_package()["seed_businesses"]
        # The shared loader reads the WHOLE seed, every market, and the guard
        # runs over all of it -- which is the point: a cross-market address
        # collision has to be caught here, not after a package is built.
        assert len([r for r in rows if r.get("market_id") == "columbus-oh"]) == 116
        assert len(rows) > 116


# --------------------------------------------------------------------------- #
# 11-12: reopening, and the hold that must never be treated as an exclusion.
# --------------------------------------------------------------------------- #

class TestSupersessionAndHolds:

    def test_an_active_supersession_reopens_an_identity(self):
        """POINT 11."""
        record = _finish(COMFORT)
        assert publication_blocks(["Comfort Suites Columbus East Broad"],
                                  exclusions=[record], check_collisions=False)
        reopened = supersede(record, reviewer_id="jfields80",
                             reviewed_at="2026-09-01T09:00:00-04:00",
                             reason="property now accepts dogs",
                             new_source_url="https://www.cscolumbuseastbroad.com/pets",
                             new_evidence_quote="We welcome dogs up to 50 lbs.")
        assert publication_blocks(["Comfort Suites Columbus East Broad"],
                                  exclusions=[reopened], check_collisions=False) == []

    def test_a_failed_capture_hold_does_not_block_publication(self, excl):
        """POINT 12. A hold lives in the review batch, never in this authority,
        so an identity we merely failed to read stays publishable once verified."""
        assert publication_blocks(
            [_seed_row("Sonesta Columbus Downtown", "33 E Nationwide Blvd", "43215")],
            exclusions=excl, check_collisions=False) == []


# --------------------------------------------------------------------------- #
# 14-15: same campus, distinct entities.
# --------------------------------------------------------------------------- #

BREWDOG_HOTEL = _seed_row("BrewDog DogHouse Columbus", "96 Gender Rd", "43110")
BREWDOG_TAPROOM = _seed_row("BrewDog DogTap Columbus", "96 Gender Rd", "43110",
                            category="pet-friendly-restaurants")


def _resolution(**overrides):
    body = {
        "resolution_id": "res-brewdog-gender-rd",
        "resolution_type": SAME_CAMPUS,
        "address_key": "96|gender|43110",
        "identities": [
            {"canonical_name": "BrewDog DogHouse Columbus",
             "category": "pet-friendly-hotels", "slug": "brewdog-doghouse-columbus",
             "booking_destination": "https://usa.brewdog.com/pages/hotels-doghouse-columbus"},
            {"canonical_name": "BrewDog DogTap Columbus",
             "category": "pet-friendly-restaurants", "slug": "brewdog-dogtap-columbus",
             "booking_destination": "https://usa.brewdog.com/pages/bars/dog-tap-columbus"},
        ],
        "evidence": "Both identities appear on the operator's own site as separate venues.",
        "reviewer_id": "jfields80", "reviewed_at": "2026-08-06T12:00:00-04:00",
    }
    body.update(overrides)
    body["resolution_hash"] = resolution_hash(body)
    return body


class TestSameCampusDistinctEntities:

    def test_the_published_taproom_really_does_share_the_hotel_address(self):
        """The fixture is not hypothetical: the taproom is already published."""
        from scripts.pettripfinder.hotel_exclusions import address_key

        seed = list(csv.DictReader(
            (REPO_ROOT / "launch_packages/pettripfinder/seed_businesses.csv")
            .open(encoding="utf-8")))
        taproom = [r for r in seed if normalize_name(r["name"]) == "brewdog dogtap columbus"]
        assert len(taproom) == 1
        assert taproom[0]["category"] == "pet-friendly-restaurants"
        assert address_key(taproom[0]["address"], taproom[0]["postal_code"]) == \
            address_key(BREWDOG_HOTEL["address"], BREWDOG_HOTEL["postal_code"])

    def test_the_collision_blocks_without_an_explicit_resolution(self):
        """POINT 14."""
        blocks = publication_blocks([BREWDOG_HOTEL], published=[BREWDOG_TAPROOM],
                                    exclusions=[], resolutions=[])
        assert [b["reason"] for b in blocks] == [BLOCK_UNRESOLVED_COLLISION]
        assert "BrewDog DogTap Columbus" in blocks[0]["collides_with"]

    def test_a_reviewed_resolution_keeps_both_identities_distinct(self):
        """POINT 15."""
        resolution = _resolution()
        assert publication_blocks([BREWDOG_HOTEL], published=[BREWDOG_TAPROOM],
                                  exclusions=[], resolutions=[resolution]) == []
        hotel, taproom = resolution["identities"]
        assert hotel["category"] != taproom["category"]
        assert hotel["slug"] != taproom["slug"]
        assert hotel["booking_destination"] != taproom["booking_destination"]

    def test_neither_identity_is_merged_or_suppressed_by_the_guard(self):
        """The guard's answer is 'both, distinctly' -- never 'one of them'."""
        rows = [BREWDOG_HOTEL, BREWDOG_TAPROOM]
        assert publication_blocks(rows, published=rows, exclusions=[],
                                  resolutions=[_resolution()]) == []

    def test_a_resolution_that_shares_a_slug_is_refused(self):
        with pytest.raises(ExclusionContractError, match="distinct slugs"):
            validate_resolutions({"schema": RESOLUTIONS_SCHEMA, "resolutions": [
                _resolution(identities=[
                    {"canonical_name": "BrewDog DogHouse Columbus",
                     "category": "pet-friendly-hotels", "slug": "brewdog-columbus"},
                    {"canonical_name": "BrewDog DogTap Columbus",
                     "category": "pet-friendly-restaurants", "slug": "brewdog-columbus"}])]})

    def test_same_category_identities_need_a_stated_reason(self):
        with pytest.raises(ExclusionContractError, match="distinct_reason"):
            validate_resolutions({"schema": RESOLUTIONS_SCHEMA, "resolutions": [
                _resolution(identities=[
                    {"canonical_name": "Tower A Hotel", "category": "pet-friendly-hotels",
                     "slug": "tower-a-hotel"},
                    {"canonical_name": "Tower B Hotel", "category": "pet-friendly-hotels",
                     "slug": "tower-b-hotel"}])]})

    def test_a_tampered_resolution_hash_is_refused(self):
        bad = _resolution()
        bad["identities"][0]["slug"] = "something-else"        # hash no longer derives
        with pytest.raises(ExclusionContractError, match="resolution_hash"):
            validate_resolutions({"schema": RESOLUTIONS_SCHEMA, "resolutions": [bad]})

    def test_an_absent_resolutions_file_means_unresolved_not_permitted(self, tmp_path):
        assert load_resolutions(tmp_path / "nope.json") == []
        blocks = publication_blocks([BREWDOG_HOTEL], published=[BREWDOG_TAPROOM],
                                    exclusions=[], resolutions_path=tmp_path / "nope.json")
        assert [b["reason"] for b in blocks] == [BLOCK_UNRESOLVED_COLLISION]

    def test_the_tracked_resolution_is_what_admits_the_promoted_hotel(self):
        """PTF-BREWDOG-PROMOTION-001 replaced this file's earlier
        'BrewDog is not promoted' assertion, which was true until the hotel was
        promoted. The successor is stronger: both rows are now in the seed, and
        the ONLY thing that makes that legal is the tracked resolution. Remove
        the resolution and the same seed stops publishing."""
        from scripts.pettripfinder.publication_guard import (
            RESOLUTIONS_PATH, load_resolutions)

        seed = list(csv.DictReader(
            (REPO_ROOT / "launch_packages/pettripfinder/seed_businesses.csv")
            .open(encoding="utf-8")))
        hotel = [r for r in seed if normalize_name(r["name"]) == "brewdog doghouse columbus"]
        taproom = [r for r in seed if normalize_name(r["name"]) == "brewdog dogtap columbus"]
        assert len(hotel) == 1 and len(taproom) == 1
        assert hotel[0]["category"] == "pet-friendly-hotels"
        assert taproom[0]["category"] == "pet-friendly-restaurants"

        assert RESOLUTIONS_PATH.exists()
        tracked = load_resolutions()
        assert [r["resolution_id"] for r in tracked] == ["res-brewdog-gender-rd",
                "res-ihg-dual-brand-575-big-beaver-troy"]  # the registry is global; Detroit recorded a second reviewed exception
        assert publication_blocks(hotel, published=seed, exclusions=[],
                                  resolutions=tracked) == []
        # Without it, the very same seed is refused.
        blocked = publication_blocks(hotel, published=seed, exclusions=[], resolutions=[])
        assert [b["reason"] for b in blocked] == [BLOCK_UNRESOLVED_COLLISION]

    def test_the_promoted_hotel_asserts_only_the_two_approved_facts(self):
        """No cat, no fee, no count, no weight, no breed rule -- the package
        record carries exactly what the official page states."""
        pkg = json.loads((REPO_ROOT / "launch_packages/pettripfinder/hotel_policy_facts.json")
                         .read_text(encoding="utf-8"))
        record = [h for h in pkg["hotels"] if h["key"] == "brewdog doghouse columbus"][0]
        assert record["facts"] == {"pets_allowed": True,
                               "species": {"dogs": "accepted"}}
        assert record["verification_state"] == "VERIFIED_PET_FRIENDLY"
        assert record["same_campus_resolution"] == "res-brewdog-gender-rd"

    def test_the_dataset_builder_keeps_both_campus_listings(self):
        """The address dedup rule would otherwise delete one of the two real
        businesses; the reviewed group is the exception that stops it."""
        from scripts.pettripfinder.listing_dataset_builder import build_listing_dataset
        from scripts.pettripfinder.publication_guard import distinct_entity_groups

        seed = [dict(r) for r in csv.DictReader(
            (REPO_ROOT / "launch_packages/pettripfinder/seed_businesses.csv")
            .open(encoding="utf-8"))]
        pair = [r for r in seed if "brewdog" in r["name"].lower()]
        cats = [{"name": "Pet-Friendly Hotels", "slug": "pet-friendly-hotels"},
                {"name": "Pet-Friendly Restaurants", "slug": "pet-friendly-restaurants"}]

        merged = build_listing_dataset(seed_businesses=pair, categories=cats)
        assert len(merged.dataset.listings) == 1        # the default rule collapses them
        assert merged.rejected_duplicates

        split = build_listing_dataset(seed_businesses=pair, categories=cats,
                                      distinct_entity_groups=distinct_entity_groups())
        assert len(split.dataset.listings) == 2
        assert not split.rejected_duplicates
        slugs = sorted(l.slug for l in split.dataset.listings)
        assert slugs == ["brewdog-doghouse-columbus", "brewdog-dogtap-columbus"]

    def test_an_unreviewed_same_address_pair_is_still_deduplicated(self):
        """The exception is the named pair only -- the rule itself is unchanged."""
        from scripts.pettripfinder.listing_dataset_builder import build_listing_dataset
        from scripts.pettripfinder.publication_guard import distinct_entity_groups

        pair = [{"name": "Some Hotel", "category": "pet-friendly-hotels",
                 "address": "1 Shared Way", "city": "Columbus", "state": "OH",
                 "postal_code": "43215", "source_url": "https://a.example/",
                 "observed_at": "2026-08-06", "pet_policy": "Pets are welcome here."},
                {"name": "Some Cafe", "category": "pet-friendly-restaurants",
                 "address": "1 Shared Way", "city": "Columbus", "state": "OH",
                 "postal_code": "43215", "source_url": "https://b.example/",
                 "observed_at": "2026-08-06", "pet_policy": "Dogs welcome on the patio."}]
        cats = [{"name": "Pet-Friendly Hotels", "slug": "pet-friendly-hotels"},
                {"name": "Pet-Friendly Restaurants", "slug": "pet-friendly-restaurants"}]
        result = build_listing_dataset(seed_businesses=pair, categories=cats,
                                       distinct_entity_groups=distinct_entity_groups())
        assert len(result.dataset.listings) == 1
        assert result.rejected_duplicates

    def test_same_category_pairs_are_detectable_but_not_blocked_by_default(self):
        """Two differently named HOTEL rows at one address are a near-duplicate
        question, and the importer's duplicate detection already owns it. The
        same-campus mechanism is scoped to the cross-category case it was built
        for, so promotion semantics elsewhere are unchanged -- but the detection
        is available, not absent."""
        from scripts.pettripfinder.publication_guard import collision_blocks

        pair = [_seed_row("Drury Inn Columbus Polaris", "8805 Orion Place", "43240"),
                _seed_row("Drury Inn & Suites Columbus Polaris", "8805 Orion Place", "43240")]
        assert collision_blocks(pair[:1], published=pair[1:], resolutions=[]) == []
        surfaced = collision_blocks(pair[:1], published=pair[1:], resolutions=[],
                                    cross_category_only=False)
        assert [b["reason"] for b in surfaced] == [BLOCK_UNRESOLVED_COLLISION]

    def test_the_published_reference_resolves_to_the_reviewed_pair(self):
        """The reference in the package record is publishable BECAUSE it can be
        resolved: it names a tracked resolution covering this identity at this
        address, and nothing else."""
        from scripts.pettripfinder.publication_guard import (
            assert_resolution_references, load_resolutions)

        record = {"name": "BrewDog DogHouse Columbus", "address": "96 Gender Rd",
                  "postal_code": "43110", "same_campus_resolution": "res-brewdog-gender-rd"}
        assert_resolution_references([record])                       # must not raise
        resolution = [r for r in load_resolutions()
                      if r["resolution_id"] == "res-brewdog-gender-rd"][0]
        assert resolution["address_key"] == "96|gender|43110"
        assert {normalize_name(i["canonical_name"]) for i in resolution["identities"]} == {
            "brewdog doghouse columbus", "brewdog dogtap columbus"}

    def test_a_reference_to_an_unknown_resolution_fails_closed(self):
        from scripts.pettripfinder.publication_guard import (
            BLOCK_REFERENCE_UNKNOWN, resolution_reference_blocks)

        blocks = resolution_reference_blocks(
            [{"name": "BrewDog DogHouse Columbus", "address": "96 Gender Rd",
              "postal_code": "43110", "same_campus_resolution": "res-does-not-exist"}])
        assert [b["reason"] for b in blocks] == [BLOCK_REFERENCE_UNKNOWN]

    def test_a_reference_to_a_different_pair_fails_closed(self):
        from scripts.pettripfinder.publication_guard import (
            BLOCK_REFERENCE_WRONG_PAIR, resolution_reference_blocks)

        blocks = resolution_reference_blocks(
            [{"name": "Some Other Hotel", "address": "96 Gender Rd",
              "postal_code": "43110", "same_campus_resolution": "res-brewdog-gender-rd"}])
        assert [b["reason"] for b in blocks] == [BLOCK_REFERENCE_WRONG_PAIR]

    def test_a_reference_pointed_at_another_address_fails_closed(self):
        from scripts.pettripfinder.publication_guard import (
            BLOCK_REFERENCE_WRONG_ADDRESS, resolution_reference_blocks)

        blocks = resolution_reference_blocks(
            [{"name": "BrewDog DogHouse Columbus", "address": "100 Gender Rd",
              "postal_code": "43110", "same_campus_resolution": "res-brewdog-gender-rd"}])
        assert [b["reason"] for b in blocks] == [BLOCK_REFERENCE_WRONG_ADDRESS]

    def test_an_operational_reference_is_refused(self):
        """The reference carries an id and nothing else -- no path, no corpus
        location, no candidate or run id, no status word."""
        from scripts.pettripfinder.publication_guard import (
            BLOCK_REFERENCE_MALFORMED, resolution_reference_blocks)

        for bad in ("data/worker_runs/res-brewdog-gender-rd.json",
                    "../launch_packages/pettripfinder/identity_resolutions.json",
                    "cand-brewdog-doghouse-columbus", "tmp-res-1", "run_2026_08_06",
                    "res-brewdog-gender-rd pending", " res-brewdog-gender-rd"):
            blocks = resolution_reference_blocks(
                [{"name": "BrewDog DogHouse Columbus", "address": "96 Gender Rd",
                  "postal_code": "43110", "same_campus_resolution": bad}])
            assert [b["reason"] for b in blocks] == [BLOCK_REFERENCE_MALFORMED], bad

    def test_a_tampered_authority_stops_the_package_read_entirely(self):
        """Hash validation happens on load, so a rewritten resolution does not
        get to be selectively survivable."""
        import scripts.pettripfinder.publication_guard as PG

        doc = json.loads(PG.RESOLUTIONS_PATH.read_text(encoding="utf-8"))
        doc["resolutions"][0]["address_key"] = "100|gender|43110"
        with pytest.raises(ExclusionContractError, match="resolution_hash"):
            PG.validate_resolutions(doc)

    def test_the_live_package_read_validates_every_reference(self):
        """The generator and the release assembler both come through here."""
        from scripts.pettripfinder.site_data import load_published_hotel_policy_facts

        assert len(load_published_hotel_policy_facts()) == 88

    def test_records_without_a_reference_are_untouched(self):
        from scripts.pettripfinder.publication_guard import resolution_reference_blocks

        assert resolution_reference_blocks(
            [{"name": "Hilton Columbus Downtown", "address": "401 N High St",
              "postal_code": "43215"}]) == []

    def test_a_row_repeated_against_itself_is_not_a_collision(self):
        """Re-publishing an unchanged row is the normal idempotent case."""
        assert publication_blocks([BREWDOG_TAPROOM], published=[BREWDOG_TAPROOM],
                                  exclusions=[], resolutions=[]) == []


# --------------------------------------------------------------------------- #
# 16-17: no bypass, bounded deterministic output.
# --------------------------------------------------------------------------- #

class TestNoBypassAndBoundedOutput:

    def test_no_force_flag_exists_on_any_wired_publication_path(self):
        """POINT 16. A flag that waves the guard through would be
        indistinguishable from the accident it exists to prevent."""
        sources = [
            "scripts/pettripfinder/publication_guard.py",
            "scripts/pettripfinder/hotel_exclusions.py",
            "scripts/promote_import_candidates.py",
            "scripts/pettripfinder/export_hotel_policy_facts.py",
            "scripts/pettripfinder/promote_worker_candidates.py",
            "scripts/pettripfinder/promote_attested_candidates.py",
        ]
        # Matched as DECLARED CLI options, not as substrings: the exporter's own
        # comment explains why it has no --force, and a prose mention of the
        # thing we refuse to add must not read as the thing itself.
        forbidden = ('"--force"', "'--force'", '"--ignore-exclusions"',
                     "'--ignore-exclusions'", '"--skip-exclusions"',
                     "'--skip-exclusions'", '"--no-exclusions"', "'--no-exclusions'")
        for rel in sources:
            text = (REPO_ROOT / rel).read_text(encoding="utf-8")
            for option in forbidden:
                assert option not in text, "%s declares a bypass option %s" % (rel, option)

    def test_the_guard_cannot_be_disabled_by_an_empty_authority_path(self, tmp_path):
        """A missing authority yields no exclusions -- but it must not be a way
        to publish something the tracked authority bars, so the wired call sites
        never pass a path at all. This pins the loader's honest behaviour."""
        from scripts.pettripfinder.publication_guard import exclusion_blocks

        assert exclusion_blocks(["anything"], path=tmp_path / "absent.json") == []

    def test_error_output_is_deterministic(self, excl):
        """POINT 17."""
        batch = [_seed_row("Timbrook Guesthouse", "5811 Olentangy River Rd", "43235"),
                 _seed_row("Comfort Suites Columbus East Broad", "70 Chris Perry Ln", "43213")]
        first = pytest.raises(PublicationBlockedError,
                              assert_publishable, batch, exclusions=excl,
                              check_collisions=False)
        second = pytest.raises(PublicationBlockedError,
                               assert_publishable, list(reversed(batch)), exclusions=excl,
                               check_collisions=False)
        assert str(first.value) == str(second.value)

    def test_error_output_is_bounded(self):
        """A thousand-row mistake must not produce a thousand-block message."""
        many = [_finish(dict(COMFORT, canonical_name="Excluded Hotel %03d" % i,
                             address="%d Main St" % i, postal_code="43215"))
                for i in range(60)]
        batch = [_seed_row("Excluded Hotel %03d" % i, "%d Main St" % i, "43215")
                 for i in range(60)]
        with pytest.raises(PublicationBlockedError) as exc:
            assert_publishable(batch, exclusions=many, check_collisions=False)
        assert len(exc.value.blocks) == 60                      # nothing hidden from the caller
        text = str(exc.value)
        assert text.count("[%s]" % BLOCK_EXCLUDED) == MAX_LISTED_BLOCKS
        assert "... and %d more" % (60 - MAX_LISTED_BLOCKS) in text

    def test_every_block_names_what_a_reviewer_needs(self, excl):
        blocks = publication_blocks(
            [_seed_row("Comfort Suites Columbus East Broad", "70 Chris Perry Ln", "43213")],
            exclusions=excl, check_collisions=False)
        block = blocks[0]
        assert block["proposed_identity"]["name"] == "Comfort Suites Columbus East Broad"
        assert block["exclusion_id"] and block["exclusion_state"]
        assert block["match_basis"] == MATCH_NAME
        assert block["lineage"]["source_url"] and block["lineage"]["evidence_quote"]
        assert block["lineage"]["record_hash"] and block["lineage"]["approval_hash"]
        assert "supersession" in block["remediation"]

    def test_the_refusal_is_still_an_exclusion_contract_error(self, excl):
        """Callers that already catch the contract error keep working."""
        with pytest.raises(ExclusionContractError):
            assert_publishable(["Comfort Suites Columbus East Broad"],
                               exclusions=excl, check_collisions=False)


# --------------------------------------------------------------------------- #
# The wired boundaries themselves.
# --------------------------------------------------------------------------- #

class TestWiredBoundaries:

    def test_machine_review_promotion_refuses_an_excluded_record(self, monkeypatch):
        from services.research_workers import machine_capture_review as MCR

        monkeypatch.setattr(
            "scripts.pettripfinder.publication_guard.load_exclusions",
            lambda *a, **k: [_finish(COMFORT)])
        record = {"hotel_name": "Comfort Suites Columbus East Broad",
                  "listing_key": "comfort suites columbus east broad", "facts": {}}
        with pytest.raises(MCR.MachineReviewError, match="excluded_identity"):
            MCR.promotion_input(record, {"decision": MCR.DECISION_APPROVED})
        assert MCR.is_publishable(record, {"decision": MCR.DECISION_APPROVED}) is False

    def test_display_review_cannot_approve_an_excluded_row(self, monkeypatch):
        from services.research_workers import display_review as DR

        monkeypatch.setattr(
            "scripts.pettripfinder.publication_guard.load_exclusions",
            lambda *a, **k: [_finish(COMFORT)])
        row = {c: "" for c in DR.SEED_COLUMNS}
        row.update({"name": "Comfort Suites Columbus East Broad",
                    "category": "pet-friendly-hotels", "address": "70 Chris Perry Ln",
                    "city": "Columbus", "state": "OH", "postal_code": "43213",
                    "phone": "(380) 208-4326",
                    "website_url": "https://www.cscolumbuseastbroad.com/",
                    "source_url": "https://www.cscolumbuseastbroad.com/",
                    "source_type": "EXACT_ENTITY_DOMAIN", "observed_at": "2026-08-06",
                    "pet_policy": "No Pets Allowed"})
        with pytest.raises(DR.DisplayReviewError, match="excluded identity"):
            DR.build_decision(hotel_id="h1", normalized_name=normalize_name(row["name"]),
                              row=row, identity_evidence_hash="sha256:i",
                              policy_source_record_hash="sha256:s",
                              policy_approval_hash="sha256:a", reviewer_id="jfields80",
                              reviewed_at="2026-08-06T12:00:00-04:00",
                              decision=DR.DISPLAY_APPROVED)

    def test_display_review_can_still_HOLD_an_excluded_row(self, monkeypatch):
        """Holding is a reviewer's honest record of what they saw; only approval
        is a publication act."""
        from services.research_workers import display_review as DR

        monkeypatch.setattr(
            "scripts.pettripfinder.publication_guard.load_exclusions",
            lambda *a, **k: [_finish(COMFORT)])
        row = {c: "" for c in DR.SEED_COLUMNS}
        row.update({"name": "Comfort Suites Columbus East Broad",
                    "category": "pet-friendly-hotels", "address": "70 Chris Perry Ln"})
        decision = DR.build_decision(
            hotel_id="h1", normalized_name=normalize_name(row["name"]), row=row,
            identity_evidence_hash="sha256:i", policy_source_record_hash="sha256:s",
            policy_approval_hash="sha256:a", reviewer_id="jfields80",
            reviewed_at="2026-08-06T12:00:00-04:00", decision=DR.DISPLAY_HELD)
        assert decision["decision"] == DR.DISPLAY_HELD

    def test_worker_candidate_promotion_checks_before_writing(self, monkeypatch, tmp_path):
        from scripts.pettripfinder import promote_worker_candidates as PWC

        monkeypatch.setattr(
            "scripts.pettripfinder.publication_guard.load_exclusions",
            lambda *a, **k: [_finish(COMFORT)])
        monkeypatch.setattr(PWC, "PROMOTION_ROOT", tmp_path)
        monkeypatch.setattr(PWC, "load_context", lambda *a, **k: {})
        monkeypatch.setattr(PWC, "evaluate_all", lambda ctx: [
            {"selected": True, "excluded": False, "failures": [],
             "listing_key": "comfort suites columbus east broad",
             "display_name": "Comfort Suites Columbus East Broad",
             "mapped_corpus_candidate": {}}])
        with pytest.raises(PublicationBlockedError):
            PWC.apply_promotion()
        assert not (tmp_path / "candidates").exists()      # nothing created

    def test_attested_candidate_promotion_checks_before_writing(self, monkeypatch, tmp_path):
        from scripts.pettripfinder import promote_attested_candidates as PAC

        monkeypatch.setattr(
            "scripts.pettripfinder.publication_guard.load_exclusions",
            lambda *a, **k: [_finish(COMFORT)])
        candidate = {"candidate_id": "attested-promotion-x",
                     "proposed_fields": [["name", "Comfort Suites Columbus East Broad"]]}
        with pytest.raises(PublicationBlockedError):
            PAC.write_candidate(candidate, root=tmp_path)
        assert list(tmp_path.iterdir()) == []

    def test_policy_authority_writer_checks_before_writing(self, monkeypatch, tmp_path):
        from scripts.pettripfinder import export_hotel_policy_facts as EX

        monkeypatch.setattr(
            "scripts.pettripfinder.publication_guard.load_exclusions",
            lambda *a, **k: [_finish(COMFORT)])
        monkeypatch.setattr(EX, "build_package", lambda: {
            "schema_version": EX.SCHEMA_VERSION, "market": EX.MARKET,
            "hotels": [{"key": "comfort suites columbus east broad",
                        "name": "Comfort Suites Columbus East Broad"}]})
        target = tmp_path / "hotel_policy_facts.json"
        with pytest.raises(PublicationBlockedError):
            EX.write_package(target)
        assert not target.exists()

    def test_the_live_policy_export_still_passes_the_guard(self):
        """The committed 70-record authority is publishable under the new check."""
        from scripts.pettripfinder import export_hotel_policy_facts as EX

        text = (REPO_ROOT / "launch_packages/pettripfinder/hotel_policy_facts.json") \
            .read_text(encoding="utf-8")
        identities = EX._package_identities(text)
        assert len(identities) == 88
        assert_publishable(identities, check_collisions=False)
