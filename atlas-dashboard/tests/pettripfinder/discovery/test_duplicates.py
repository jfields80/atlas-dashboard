"""Cross-slug duplicate detection.

The consolidated 78-candidate run queued one hotel twice:

    le-m-ridien-columbus-the-joseph   /   le-meridien-columbus-the-joseph

Same property code ``cmhdm``, same phone, same street, different slug -- the
accented "é" survives in one and is dropped in the other. The slug guard could
not see it, so both were captured and both failed independently.

These tests hold the fix to its stated shape: decide on identity evidence, hold
rather than merge, and never let a name alone decide.
"""

from __future__ import annotations

import pytest

from scripts.pettripfinder.discovery import duplicates as D

MERIDIEN_A = D.DuplicateCandidate(
    record_id="le-m-ridien-columbus-the-joseph",
    name="Le Méridien Columbus, The Joseph",
    property_code="cmhdm", phone="614-227-0100",
    street="620 N High St, Columbus, OH 43215, USA",
    canonical_url="https://www.marriott.com/en-us/hotels/cmhdm-le-meridien-columbus-the-joseph/overview/",
    source_ids=("provider:GOOGLE_PLACES:gpA",), aliases=("le meridien columbus the joseph",))

MERIDIEN_B = D.DuplicateCandidate(
    record_id="le-meridien-columbus-the-joseph",
    name="Le Meridien Columbus, The Joseph",
    property_code="", phone="614-227-0100", street="620 North High Street",
    canonical_url="https://www.marriott.com/hotels/travel/cmhdm-le-meridien-columbus-the-joseph",
    source_ids=("provider:OPENSTREETMAP:osmB",), aliases=("le meridien columbus the joseph",))


def _c(rid, **kw):
    base = dict(record_id=rid, name="Some Hotel", property_code="", phone="",
                street="", canonical_url="")
    base.update(kw)
    return D.DuplicateCandidate(**base)


# --------------------------------------------------------------------------- #
# The case that motivated this.
# --------------------------------------------------------------------------- #

class TestLeMeridien:
    def test_the_pair_is_detected_despite_different_slugs(self):
        rel = D.compare(MERIDIEN_A, MERIDIEN_B)
        assert rel is not None, "the duplicate must be found"
        assert rel.outcome == D.DUPLICATE_HOLD

    def test_it_is_caught_by_phone_and_street_not_by_the_slug(self):
        """A carries a property code and B does not (legacy /hotels/travel/
        URL), so rule 1 cannot fire. Rule 2 is what sees it."""
        rel = D.compare(MERIDIEN_A, MERIDIEN_B)
        assert rel.rule == D.RULE_PHONE_AND_STREET
        assert any(e.startswith("phone:") for e in rel.evidence)
        assert any(e.startswith("street:") for e in rel.evidence)

    def test_the_differently_formatted_streets_normalise_together(self):
        assert (D.normalize_street("620 N High St, Columbus, OH 43215, USA")
                == D.normalize_street("620 North High Street"))

    def test_nothing_is_merged_and_both_survive(self):
        rel = D.compare(MERIDIEN_A, MERIDIEN_B)
        assert rel.to_dict()["merged"] is False
        assert rel.left_id and rel.right_id and rel.left_id != rel.right_id

    def test_source_ids_and_aliases_are_preserved(self):
        rel = D.compare(MERIDIEN_A, MERIDIEN_B)
        assert "provider:GOOGLE_PLACES:gpA" in rel.preserved_source_ids
        assert "provider:OPENSTREETMAP:osmB" in rel.preserved_source_ids
        assert rel.preserved_aliases

    def test_the_relation_is_auditable(self):
        d = D.compare(MERIDIEN_A, MERIDIEN_B).to_dict()
        for key in ("left_id", "right_id", "outcome", "rule", "evidence", "merged"):
            assert key in d

    def test_both_records_are_held_not_one(self):
        held = D.held_record_ids([D.compare(MERIDIEN_A, MERIDIEN_B)])
        assert set(held) == {MERIDIEN_A.record_id, MERIDIEN_B.record_id}


# --------------------------------------------------------------------------- #
# The ladder.
# --------------------------------------------------------------------------- #

class TestLadder:
    def test_same_property_code_different_slugs_holds(self):
        a = _c("alpha-slug", property_code="cmhdm", name="Alpha")
        b = _c("totally-different-slug", property_code="CMHDM", name="Beta")
        rel = D.compare(a, b)
        assert rel.outcome == D.DUPLICATE_HOLD
        assert rel.rule == D.RULE_PROPERTY_CODE

    def test_same_phone_and_street_different_names_holds(self):
        a = _c("a", name="The Joseph", phone="614-227-0100", street="620 N High St")
        b = _c("b", name="Le Meridien", phone="(614) 227 0100", street="620 North High Street")
        rel = D.compare(a, b)
        assert rel.outcome == D.DUPLICATE_HOLD
        assert rel.rule == D.RULE_PHONE_AND_STREET

    def test_same_canonical_url_holds_despite_tracking_params(self):
        a = _c("a", canonical_url="https://www.ihg.com/x/cmhav/hoteldetail?cm_mmc=GoogleMaps")
        b = _c("b", canonical_url="https://ihg.com/x/cmhav/hoteldetail/")
        rel = D.compare(a, b)
        assert rel.outcome == D.DUPLICATE_HOLD
        assert rel.rule == D.RULE_CANONICAL_URL

    def test_one_identifier_plus_name_is_manual_review_not_a_hold(self):
        a = _c("a", name="Hampton Inn Columbus Dublin", phone="614-555-0000")
        b = _c("b", name="Hampton Inn Columbus Dublin", phone="614-555-0000", street="")
        rel = D.compare(a, b)
        assert rel is not None
        assert rel.outcome == D.MANUAL_REVIEW
        assert rel.rule == D.RULE_IDENTIFIER_PLUS_NAME


# --------------------------------------------------------------------------- #
# What must NOT be collapsed.
# --------------------------------------------------------------------------- #

class TestDistinctHotelsAreNotCollapsed:
    def test_similar_name_different_address_is_not_a_duplicate(self):
        a = _c("a", name="Hampton Inn Columbus", phone="614-111-1111",
               street="100 First St")
        b = _c("b", name="Hampton Inn Columbus", phone="614-222-2222",
               street="900 Ninth Ave")
        assert D.compare(a, b) is None

    def test_chain_hotels_with_similar_names_in_one_city_stay_distinct(self):
        """Three real Grove City 'Hampton Inn Columbus South' candidates were
        withheld by the slug guard. They must not now be auto-merged."""
        a = _c("a", name="Hampton Inn Columbus South", street="1 A Rd", phone="614-000-0001")
        b = _c("b", name="Hampton Inn Columbus South", street="2 B Rd", phone="614-000-0002")
        c = _c("c", name="Hampton Inn Columbus South", street="3 C Rd", phone="614-000-0003")
        rels = D.find_duplicates([a, b, c])
        assert all(r.outcome != D.DUPLICATE_HOLD for r in rels)

    def test_a_name_match_alone_never_produces_any_relation(self):
        a = _c("a", name="Courtyard by Marriott Columbus Downtown")
        b = _c("b", name="Courtyard by Marriott Columbus Downtown")
        assert D.compare(a, b) is None, "name alone must decide nothing"

    def test_noise_words_do_not_create_similarity(self):
        a = _c("a", name="Hampton Inn", phone="614-000-0001")
        b = _c("b", name="Holiday Inn", phone="614-000-0001")
        rel = D.compare(a, b)
        assert rel is None or rel.outcome != D.DUPLICATE_HOLD

    def test_missing_property_code_does_not_match_another_missing_one(self):
        """Two blanks are not an agreement."""
        a = _c("a", property_code="", name="Alpha")
        b = _c("b", property_code="", name="Beta")
        assert D.compare(a, b) is None

    def test_missing_phone_or_street_cannot_satisfy_rule_two(self):
        a = _c("a", phone="614-000-0001", street="")
        b = _c("b", phone="614-000-0001", street="")
        rel = D.compare(a, b)
        assert rel is None or rel.outcome != D.DUPLICATE_HOLD


# --------------------------------------------------------------------------- #
# Normalisation details.
# --------------------------------------------------------------------------- #

class TestNormalisation:
    def test_accents_are_folded_for_names(self):
        assert D.normalize_name("Le Méridien") == D.normalize_name("Le Meridien")

    def test_accent_folding_is_not_the_duplicate_rule(self):
        """Two different hotels whose names fold together must still be
        DISTINCT without identity evidence."""
        a = _c("a", name="Café Hotel", street="1 A Rd", phone="614-000-0001")
        b = _c("b", name="Cafe Hotel", street="99 Z Rd", phone="614-000-0009")
        assert D.compare(a, b) is None

    def test_phone_matches_on_last_ten_digits(self):
        assert D.normalize_phone("+1 (614) 227-0100") == D.normalize_phone("614.227.0100")

    def test_legacy_hotels_travel_urls_normalise(self):
        legacy = "https://www.marriott.com/hotels/travel/cmhdm-le-meridien-columbus-the-joseph"
        assert D.normalize_canonical_url(legacy) == \
            "marriott.com/hotels/travel/cmhdm-le-meridien-columbus-the-joseph"

    def test_canonical_url_drops_www_query_and_trailing_slash(self):
        assert (D.normalize_canonical_url("https://WWW.Example.com/a/b/?x=1#f")
                == "example.com/a/b")

    def test_empty_urls_never_match(self):
        assert D.normalize_canonical_url("") == ""
        assert D.compare(_c("a"), _c("b")) is None


# --------------------------------------------------------------------------- #
# Set-level behaviour.
# --------------------------------------------------------------------------- #

class TestFindDuplicates:
    def test_deterministic_ordering(self):
        cands = [MERIDIEN_B, MERIDIEN_A, _c("zzz", name="Other")]
        assert D.find_duplicates(cands) == D.find_duplicates(list(reversed(cands)))

    def test_unrelated_hotels_produce_no_relations(self):
        cands = [_c("a", name="Alpha", phone="614-000-0001", street="1 A Rd",
                    property_code="aaaa"),
                 _c("b", name="Beta", phone="614-000-0002", street="2 B Rd",
                    property_code="bbbb")]
        assert D.find_duplicates(cands) == ()

    def test_summary_counts_by_outcome_and_rule(self):
        rels = D.find_duplicates([MERIDIEN_A, MERIDIEN_B])
        s = D.summarize(rels)
        assert s["relations"] == 1
        assert s[D.DUPLICATE_HOLD] == 1
        assert s["rule_%s" % D.RULE_PHONE_AND_STREET] == 1


# --------------------------------------------------------------------------- #
# Against the real run.
# --------------------------------------------------------------------------- #

class TestAgainstTheConsolidatedRun:
    def test_the_real_meridien_pair_is_held(self):
        import json
        import pathlib

        qdir = pathlib.Path(
            r"C:\Atlas\atlas-dashboard\data\worker_runs\pettripfinder\capture_batches")
        if not (qdir / "batch-2-queue.json").exists():
            pytest.skip("run corpus is gitignored")

        from services.research_workers.capture_automation.adapters import known_brands
        from services.research_workers.capture_automation.queue import validate_entry

        cands = []
        for n in (1, 2, 3):
            data = json.loads((qdir / ("batch-%d-queue.json" % n)).read_text(encoding="utf-8"))
            for i, raw in enumerate(data["hotels"]):
                e, _ = validate_entry(raw, i, known_brands=known_brands())
                if e is not None:
                    cands.append(D.DuplicateCandidate.from_queue_entry(e))

        rels = D.find_duplicates(cands)
        held = set(D.held_record_ids(rels))
        assert "le-m-ridien-columbus-the-joseph" in held
        assert "le-meridien-columbus-the-joseph" in held
