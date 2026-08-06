"""PTF-EXCLUSIONS -- an identity answered by evidence must stay answered.

The distinction these tests defend: a capture that FAILED is not an exclusion.
"We could not read the policy" is temporary and must remain capture-eligible;
"their own page says No Pets Allowed" is durable. Collapsing the two would
either strand real hotels forever or re-queue answered ones every sweep.
"""

from __future__ import annotations

import json

import pytest

from scripts.pettripfinder.hotel_exclusions import (
    EXCLUSION_STATES,
    FORBIDDEN_STATES,
    OUT_OF_CURRENT_CATEGORY,
    SCHEMA,
    VERIFIED_NO_PETS,
    ExclusionContractError,
    address_key,
    approval_hash,
    excluded_names,
    exclusion_for,
    is_excluded,
    load_exclusions,
    record_hash,
    supersede,
    validate,
    assert_not_excluded_for_publication,
)
from scripts.pettripfinder.site_data import normalize_name

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


def _finish(rec):
    r = dict(rec)
    r["exclusion_id"] = "excl-" + normalize_name(r["canonical_name"]).replace(" ", "-")
    r["normalized_name"] = normalize_name(r["canonical_name"])
    r["source_hash"] = "sha256:seed"
    r["record_hash"] = record_hash(r)
    r["approval_hash"] = approval_hash(r)
    return r


def _doc(*records):
    return {"schema": SCHEMA, "exclusions": [_finish(r) for r in records]}


@pytest.fixture
def comfort_doc():
    return _doc(COMFORT)


# --------------------------------------------------------------------------- #
# Contract shape.
# --------------------------------------------------------------------------- #

class TestContract:
    def test_a_valid_document_validates(self, comfort_doc):
        recs = validate(comfort_doc)
        assert len(recs) == 1
        assert recs[0]["exclusion_state"] == VERIFIED_NO_PETS

    def test_hashes_must_re_derive(self, comfort_doc):
        comfort_doc["exclusions"][0]["record_hash"] = "sha256:wrong"
        with pytest.raises(ExclusionContractError, match="record_hash"):
            validate(comfort_doc)

    def test_approval_hash_must_re_derive(self, comfort_doc):
        comfort_doc["exclusions"][0]["approval_hash"] = "sha256:wrong"
        with pytest.raises(ExclusionContractError, match="approval_hash"):
            validate(comfort_doc)

    def test_schema_version_is_enforced(self, comfort_doc):
        comfort_doc["schema"] = "ptf-hotel-exclusions/2.0"
        with pytest.raises(ExclusionContractError, match="schema"):
            validate(comfort_doc)

    @pytest.mark.parametrize("state", FORBIDDEN_STATES)
    def test_a_failed_capture_is_never_an_exclusion(self, state):
        """POINT 6: policy-not-verified holds are not permanent exclusions."""
        rec = dict(COMFORT); rec["exclusion_state"] = state
        with pytest.raises(ExclusionContractError, match="temporary hold"):
            validate(_doc(rec))

    def test_evidence_backed_states_require_a_quote(self):
        rec = dict(COMFORT); rec["evidence_quote"] = ""
        with pytest.raises(ExclusionContractError):
            validate(_doc(rec))

    def test_duplicate_exclusion_ids_fail_closed(self, comfort_doc):
        """POINT 8."""
        comfort_doc["exclusions"].append(dict(comfort_doc["exclusions"][0]))
        with pytest.raises(ExclusionContractError, match="duplicate"):
            validate(comfort_doc)

    def test_conflicting_exclusion_states_fail_closed(self):
        """POINT 9: one identity may not be two different kinds of excluded."""
        a = _finish(COMFORT)
        b = _finish(dict(COMFORT, exclusion_state="PERMANENTLY_CLOSED",
                         evidence_quote="Permanently closed"))
        b["exclusion_id"] = a["exclusion_id"] + "-2"
        with pytest.raises(ExclusionContractError, match="conflicting exclusion states"):
            validate({"schema": SCHEMA, "exclusions": [a, b]})

    def test_two_exclusions_may_not_share_one_street_identity(self):
        a = _finish(COMFORT)
        b = _finish(dict(COMFORT, canonical_name="Some Other Hotel"))
        b["exclusion_id"] = "excl-other"
        with pytest.raises(ExclusionContractError, match="street identity"):
            validate({"schema": SCHEMA, "exclusions": [a, b]})

    def test_duplicate_state_requires_a_related_identity(self):
        rec = dict(COMFORT, exclusion_state="DUPLICATE_IDENTITY")
        with pytest.raises(ExclusionContractError, match="related_identity"):
            validate(_doc(rec))

    def test_street_number_alone_is_not_identity(self):
        assert address_key("50 W Broad St", "43215") != address_key("50 N 3rd St", "43215")

    def test_absent_authority_is_empty_not_an_error(self, tmp_path):
        assert load_exclusions(tmp_path / "nope.json") == []


# --------------------------------------------------------------------------- #
# Behaviour.
# --------------------------------------------------------------------------- #

class TestBehaviour:
    def test_excluded_by_name(self, comfort_doc):
        recs = validate(comfort_doc)
        assert is_excluded("Comfort Suites Columbus East Broad", records=recs)

    def test_excluded_by_street_identity_even_under_a_new_name(self, comfort_doc):
        """A rebrand at the same address does not escape the exclusion."""
        recs = validate(comfort_doc)
        assert is_excluded("Comfort Suites East Broad at 270", "70 Chris Perry Ln",
                           "43213", records=recs)

    def test_an_unrelated_hotel_is_not_excluded(self, comfort_doc):
        recs = validate(comfort_doc)
        assert not is_excluded("Hilton Columbus Downtown", "401 N High St", "43215",
                               records=recs)

    def test_publication_gate_refuses_an_excluded_identity(self, comfort_doc):
        """POINT 3."""
        recs = validate(comfort_doc)
        with pytest.raises(ExclusionContractError, match="refusing to publish"):
            assert_not_excluded_for_publication(
                [("Comfort Suites Columbus East Broad", "70 Chris Perry Ln", "43213")],
                records=recs)

    def test_publication_gate_allows_everything_else(self, comfort_doc):
        recs = validate(comfort_doc)
        assert_not_excluded_for_publication(
            [("BrewDog DogHouse Columbus", "96 Gender Rd", "43110")], records=recs)

    def test_out_of_category_is_preserved_but_nonpublic(self):
        """POINT 7: B&Bs stay on the books for a future category, not published."""
        rec = _finish(dict(COMFORT, canonical_name="50 Lincoln Short North Bed and Breakfast",
                           address="50 E Lincoln St", postal_code="43215",
                           exclusion_state=OUT_OF_CURRENT_CATEGORY,
                           evidence_quote="Operator category ruling 2026-08-06"))
        recs = validate({"schema": SCHEMA, "exclusions": [rec]})
        assert recs[0]["canonical_name"] in [r["canonical_name"] for r in recs]
        with pytest.raises(ExclusionContractError):
            assert_not_excluded_for_publication(
                [("50 Lincoln Short North Bed and Breakfast", "50 E Lincoln St", "43215")],
                records=recs)

    def test_an_exclusion_needs_no_seed_row_and_no_policy_record(self, comfort_doc):
        """POINT 5: the authority is standalone by construction."""
        import csv as _csv, pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        seed = list(_csv.DictReader((root / "launch_packages/pettripfinder/seed_businesses.csv")
                                    .open(encoding="utf-8")))
        pkg = json.loads((root / "launch_packages/pettripfinder/hotel_policy_facts.json")
                         .read_text(encoding="utf-8-sig"))
        for r in validate(comfort_doc):
            assert r["normalized_name"] not in {normalize_name(x["name"]) for x in seed}
            assert r["normalized_name"] not in {h["key"] for h in pkg["hotels"]}


# --------------------------------------------------------------------------- #
# Supersession.
# --------------------------------------------------------------------------- #

class TestSupersession:
    def test_reopening_requires_new_official_evidence(self, comfort_doc):
        rec = validate(comfort_doc)[0]
        with pytest.raises(ExclusionContractError, match="never reopens implicitly"):
            supersede(rec, reviewer_id="jfields80", reviewed_at="2027-01-01",
                      reason="", new_source_url="", new_evidence_quote="")

    def test_a_reviewed_supersession_reopens_the_identity(self, comfort_doc):
        """POINT 10."""
        rec = validate(comfort_doc)[0]
        reopened = supersede(rec, reviewer_id="jfields80", reviewed_at="2027-01-01",
                             reason="property changed its policy",
                             new_source_url="https://www.cscolumbuseastbroad.com/",
                             new_evidence_quote="Pets Welcome")
        assert not is_excluded("Comfort Suites Columbus East Broad", records=[reopened])
        # the original evidence and lineage survive
        assert reopened["evidence_quote"] == "No Pets Allowed"
        assert reopened["supersession"]["supersedes_record_hash"] == rec["record_hash"]

    def test_reopening_does_not_delete_history(self, comfort_doc):
        rec = validate(comfort_doc)[0]
        reopened = supersede(rec, reviewer_id="r", reviewed_at="2027-01-01", reason="x",
                             new_source_url="https://x/", new_evidence_quote="Pets Welcome")
        assert reopened["source_url"] == rec["source_url"]
        assert reopened["record_hash"] == rec["record_hash"]


# --------------------------------------------------------------------------- #
# Capture-queue suppression.
# --------------------------------------------------------------------------- #

class TestCaptureQueueSuppression:
    def _seed(self, tmp_path, name, addr, zipc, url):
        import csv as _csv
        p = tmp_path / "seed.csv"
        cols = ["name","category","address","city","state","postal_code","phone",
                "website_url","source_url","source_type","observed_at","rating",
                "amenities","pet_policy","canonical"]
        with p.open("w", newline="", encoding="utf-8") as f:
            w = _csv.DictWriter(f, fieldnames=cols); w.writeheader()
            w.writerow({c: "" for c in cols} | {
                "name": name, "category": "pet-friendly-hotels", "address": addr,
                "city": "Columbus", "state": "OH", "postal_code": zipc,
                "website_url": url, "source_url": url, "source_type": "OFFICIAL",
                "observed_at": "2026-08-06", "pet_policy": "x"})
        return p

    def _excl_file(self, tmp_path, doc):
        p = tmp_path / "hotel_exclusions.json"
        p.write_text(json.dumps(doc, indent=1), encoding="utf-8")
        return p

    def test_an_excluded_identity_is_suppressed_from_the_queue(self, tmp_path, comfort_doc):
        """POINTS 1 and 2."""
        from scripts.pettripfinder.build_capture_queue import build_queue
        seed = self._seed(tmp_path, "Comfort Suites Columbus East Broad",
                          "70 Chris Perry Ln", "43213",
                          "https://www.choicehotels.com/ohio/columbus/comfort-suites-hotels/oh504")
        ex = self._excl_file(tmp_path, comfort_doc)
        r = build_queue(batch_id="t", created_at="2026-01-01T00:00:00Z", seed_csv=seed,
                        package_path=tmp_path / "none.json", retrieval_root=tmp_path,
                        require_retrieval_artifact=False, exclusions_path=ex,
                        include_filtered_in_report=True)
        reasons = [e.reason for e in r.excluded]
        assert any(x.startswith("excluded_identity:VERIFIED_NO_PETS") for x in reasons), reasons
        assert r.counts["selected"] == 0

    def test_explicit_revalidation_reopens_it_for_capture(self, tmp_path, comfort_doc):
        from scripts.pettripfinder.build_capture_queue import build_queue
        seed = self._seed(tmp_path, "Comfort Suites Columbus East Broad",
                          "70 Chris Perry Ln", "43213",
                          "https://www.choicehotels.com/ohio/columbus/comfort-suites-hotels/oh504")
        ex = self._excl_file(tmp_path, comfort_doc)
        r = build_queue(batch_id="t", created_at="2026-01-01T00:00:00Z", seed_csv=seed,
                        package_path=tmp_path / "none.json", retrieval_root=tmp_path,
                        require_retrieval_artifact=False, exclusions_path=ex,
                        revalidate_excluded=True, include_filtered_in_report=True)
        assert not any(e.reason.startswith("excluded_identity") for e in r.excluded)

    def test_brewdog_is_unaffected_by_the_exclusion_authority(self, tmp_path, comfort_doc):
        """POINT 12."""
        recs = validate(comfort_doc)
        assert not is_excluded("BrewDog DogHouse Columbus", "96 Gender Rd", "43110",
                               records=recs)

    def test_the_committed_authority_validates_and_holds_only_reviewed_records(self):
        """The real tracked authority, not a fixture.

        It must parse, re-derive every hash, and contain no temporary hold. It
        must also stay disjoint from the two publication authorities: an
        exclusion that appeared in the seed or the policy package would mean a
        published hotel had been quietly disqualified.
        """
        import csv as _csv
        import pathlib

        root = pathlib.Path(__file__).resolve().parents[2]
        recs = load_exclusions()
        assert recs, "the committed exclusion authority should not be empty"
        assert all(r["exclusion_state"] in EXCLUSION_STATES for r in recs)
        assert not [r for r in recs if r["exclusion_state"] in FORBIDDEN_STATES]

        seed = {normalize_name(r["name"]) for r in
                _csv.DictReader((root / "launch_packages/pettripfinder/seed_businesses.csv")
                                .open(encoding="utf-8"))}
        pkg = {h["key"] for h in json.loads(
            (root / "launch_packages/pettripfinder/hotel_policy_facts.json")
            .read_text(encoding="utf-8-sig"))["hotels"]}
        for r in recs:
            assert r["normalized_name"] not in seed, r["canonical_name"]
            assert r["normalized_name"] not in pkg, r["canonical_name"]
        assert excluded_names() == frozenset(r["normalized_name"] for r in recs)

    def test_out_of_category_records_assert_no_pet_policy(self):
        """A category ruling is not a policy finding. These records exist to
        preserve an identity, not to claim anything about pets."""
        for r in load_exclusions():
            if r["exclusion_state"] == OUT_OF_CURRENT_CATEGORY:
                assert "pets allowed" not in r["evidence_quote"].lower()
                assert "no pets" not in r["evidence_quote"].lower()
