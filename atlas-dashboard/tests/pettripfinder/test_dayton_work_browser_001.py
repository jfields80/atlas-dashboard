"""PTF-DAYTON-WORK-BROWSER-INTEGRATION-001 -- the Dayton Work-browser pass.

What these defend is what a transcription tempts an integrator to do, and what
this batch specifically nearly did:

  * publish a pet policy from typed prose with no artifact of the page
  * treat a brand-invariant JSON-LD flag as evidence about one property
  * bind a routing record on the operator's word for a page nobody could read
  * leave four newly answered properties sitting in an "unresolved" list

Most of them read the COMMITTED ledger and the COMMITTED authority, so they run
on a machine with no ``data/``. The ones that must re-derive a hash from the
operator package or from a stored capture declare that as a precondition and
skip with the path named -- the pattern ``ed53d5b``/``441498d`` established
after a worktree with no ``data/`` reported nine phantom failures.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from pettripfinder import epochs
from pettripfinder.market_state import current
from scripts.pettripfinder import integrate_dayton_work_browser_001 as WB
from scripts.pettripfinder.hotel_exclusions import load_exclusions
from scripts.pettripfinder.site_data import normalize_name, published_facts_path

_ROOT = Path(__file__).resolve().parents[2]
DAYTON = "dayton-oh"

#: What this order left true (its ledger says so forever). The LIVE package
#: and registry are held to the current pin.
EPOCH = epochs.HistoricalEpoch(
    "PTF-DAYTON-WORK-BROWSER-INTEGRATION-001", DAYTON,
    facts={"census": 129, "pet_friendly": 47, "verified_no_pets": 8,
           "resolved": 55, "unresolved_or_held": 74},
    superseded_by=("PTF-DAYTON-OH-HARDENED-APPLICATION-002",))
NOW = current(DAYTON)
#: Recovery-002 candidates no later order has read (the Wingate).
STILL_PROPOSED = 1

#: What the pass published, and the shape of each. Named here so a change to
#: the table in the integrator has to be a deliberate change here too.
PUBLISHED = {
    # normalize_name spells "&" as "and"; the key is derived, never typed.
    "best western plus miamisburg dayton suites banquets and hotel",
    "best western wapakoneta inn",
    "extended stay america select suites dayton miamisburg",
}
EXCLUDED = {"best western celina"}


@pytest.fixture(scope="module")
def ledger():
    return json.loads(WB.LEDGER_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def facts():
    return json.loads(published_facts_path(DAYTON).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def captures():
    if not WB.captures_present():
        pytest.skip("data/ is gitignored; capture runs absent from this worktree")
    return WB.load_captures()


# --------------------------------------------------------------------------- #
# The handback reconciles, and it reconciles against the batches.
# --------------------------------------------------------------------------- #

class TestThePackageReconciles:

    def test_the_ledger_accounts_for_all_ninety_exactly_once(self, ledger):
        slugs = [i["slug"] for i in ledger["items"]]
        assert len(slugs) == WB.EXPECTED_QUEUE_SIZE == 90
        assert len(set(slugs)) == 90
        assert ledger["reconciliation"]["duplicates"] == 0
        assert ledger["reconciliation"]["omissions"] == 0

    def test_the_two_headline_numbers_overlap_and_are_never_summed(self, ledger):
        """41 "visible policy" and 14 "routing corrections" are not disjoint.

        Twelve rows are both, so 41 + 14 counts twelve properties twice. The
        classification partition is the thing that adds to 90, and it is derived
        from the rows rather than read off the manifest."""
        rec = ledger["reconciliation"]
        assert rec["rows_carrying_policy_wording"] == 41
        assert len(rec["policy_wording_rows_also_routing_proposals"]) == 12
        assert sum(rec["classifications"].values()) == 90
        assert rec["classifications"]["ROUTING_CORRECTION_PROPOSED"] == 14
        assert rec["classifications"]["BROWSER_VERIFIED_POLICY_VISIBLE"] == 29

    def test_every_property_gets_one_outcome_and_one_next_action(self, ledger):
        for item in ledger["items"]:
            assert item["outcome"] in WB.OUTCOMES, item["slug"]
            assert item["next_action"].strip(), item["slug"]
            assert item["reason_code"].strip(), item["slug"]
        assert sum(ledger["outcome_counts"].values()) == 90

    def test_the_queue_baseline_drift_is_recorded_rather_than_absorbed(self, ledger):
        """The 90 rows are the complement of a 33/6 partition the market has
        since left behind. Twelve of them were answered by
        PTF-DAYTON-CANDIDATE-PROMOTION-001 before this pass was adjudicated, and
        they are reconciled as ALREADY_RESOLVED rather than re-decided from a
        transcription that never saw the evidence that resolved them."""
        assert ledger["queue_baseline"]["published_pet_friendly"] == 33
        assert ledger["queue_baseline"]["verified_no_pets"] == 6
        drift = ledger["baseline_drift"]
        assert len(drift["rows_already_published"]) == 11
        assert len(drift["rows_already_excluded"]) == 1
        assert ledger["outcome_counts"]["ALREADY_RESOLVED_BEFORE_THIS_PASS"] == 12

    def test_the_input_inventory_is_exactly_twenty_one_files(self, ledger):
        assert ledger["input_package"]["file_count"] == 21
        assert len(ledger["input_package"]["sha256"]) == 21
        assert set(ledger["input_package"]["sha256"]) == set(WB.EXPECTED_FILES)
        assert ledger["input_package"]["tracked"] is False

    def test_the_recorded_hashes_are_the_files_on_disk(self):
        if not WB.input_present():
            pytest.skip("operator package absent: %s" % WB.INPUT_DIR)
        ledger = json.loads(WB.LEDGER_PATH.read_text(encoding="utf-8"))
        assert dict(WB.input_hashes()) == ledger["input_package"]["sha256"]

    def test_a_missing_or_extra_file_is_a_gate_failure(self, tmp_path):
        (tmp_path / WB.EXPECTED_FILES[0]).write_text("x", encoding="utf-8")
        with pytest.raises(WB.WorkBrowserInputError):
            WB.input_hashes(tmp_path)


# --------------------------------------------------------------------------- #
# Nothing publishes from the transcription.
# --------------------------------------------------------------------------- #

class TestTheTranscriptionIsNotAnArtifactClass:

    def test_the_verdict_is_recorded_and_publication_is_refused(self, ledger):
        d = ledger["evidence_determination"]
        assert d["artifact_class"] == "OPERATOR_TRANSCRIBED_BROWSER_REVIEW"
        assert d["accepted_for_publication"] is False
        assert d["screenshots_declared_by_the_package"] is False
        assert d["screenshot_tree_on_disk"] is False
        assert "NOT_A_PUBLICATION_GRADE_ARTIFACT_CLASS" in d["verdict"]

    def test_no_screenshot_tree_exists_under_the_dayton_evidence_directory(self):
        base = (_ROOT / "data" / "operator_evidence" / "dayton-founder-review-001")
        if not base.is_dir():
            pytest.skip("data/ is gitignored; operator evidence absent")
        assert not (base / "screenshots").exists()

    def test_the_pass_published_exactly_what_the_ledger_says(self, ledger, facts):
        assert set(ledger["published_by_this_pass"]) == PUBLISHED
        assert set(ledger["verified_no_pets_by_this_pass"]) == EXCLUDED
        keys = {h["key"] for h in facts["hotels"]}
        assert PUBLISHED <= keys
        registry = {normalize_name(e["canonical_name"]) for e in load_exclusions()
                    if e.get("market_id") == DAYTON}
        assert EXCLUDED <= registry

    def test_every_published_quote_is_contiguous_in_its_own_capture(self, facts, captures):
        """The standard, applied to exactly the records this pass added.

        Not "the words appear somewhere on the page" -- PTF-DAYTON-CANDIDATE-
        PROMOTION-001 caught three records whose quote was two verbatim halves
        ~9,000 characters apart. Each quote must be one span of the capture's
        RAW HTML, and the capture's hash must re-derive from that HTML."""
        by_key = {h["key"]: h for h in facts["hotels"]}
        for key in sorted(PUBLISHED):
            record = by_key[key]
            cap = WB.capture_for(record["source_url"], captures)
            assert cap is not None, key
            assert hashlib.sha256(cap["html"].encode("utf-8")).hexdigest() \
                == record["worker_result_hash"], key
            for item in record["evidence"]:
                assert " ".join(item["quote"].split()) in cap["body"], (key, item["field"])
                assert item["source_url"] == record["source_url"], key

    def test_the_exclusion_quote_is_in_its_own_capture(self, captures):
        rec = next(e for e in load_exclusions()
                   if normalize_name(e["canonical_name"]) == "best western celina")
        cap = WB.capture_for(rec["source_url"], captures)
        assert cap is not None
        assert hashlib.sha256(cap["html"].encode("utf-8")).hexdigest() == rec["source_hash"]
        assert " ".join(rec["evidence_quote"].split()) in cap["body"]

    def test_the_corroboration_measurement_is_reported_not_assumed(self, ledger):
        """Sixteen of the forty-one transcribed quotes are literal substrings of
        a hash-verified capture this repository already holds. That number is
        the whole value of the handback: it is a pointer, and this is the
        measurement that says where it points."""
        assert ledger["evidence_determination"][
            "transcribed_quotes_found_in_a_stored_capture"] == 16
        assert ledger["evidence_determination"][
            "accepted_as_a_pointer_to_stored_captures"] is True


# --------------------------------------------------------------------------- #
# Best Western's structured flag.
# --------------------------------------------------------------------------- #

class TestTheBrandFlagIsNotEvidence:

    def test_every_best_western_capture_reads_false(self, ledger):
        survey = ledger["best_western_structured_flag"]["survey"]
        assert len(survey) == 5
        assert {row["jsonld_pets_allowed"] for row in survey} == {"false"}

    def test_four_of_the_five_state_a_priced_pet_friendly_policy(self, ledger):
        """A flag with one value across a hotel that refuses pets and four that
        charge 20, 25 and 40 USD a day for them discriminates nothing. That is
        the whole argument for not authoring it as an establishing observation,
        and it is a count rather than an opinion."""
        survey = ledger["best_western_structured_flag"]["survey"]
        priced = [r for r in survey if re.search(r"\d+(\.\d+)? USD per day",
                                                 r["visible_pet_policy_block"])]
        refusing = [r for r in survey
                    if "not accepted" in r["visible_pet_policy_block"].lower()]
        assert len(priced) == 4
        assert len(refusing) == 1
        assert len(priced) + len(refusing) == len(survey)

    def test_the_survey_re_derives_from_the_captures_on_disk(self, ledger):
        if not WB.captures_present():
            pytest.skip("data/ is gitignored; capture runs absent from this worktree")
        assert WB.best_western_pets_allowed_survey(
            WB.load_captures(WB.BW_SURVEY_DIRS)) == [
                dict(row) for row in ledger["best_western_structured_flag"]["survey"]]

    def test_celina_is_excluded_on_its_visible_sentence_not_the_flag(self):
        rec = next(e for e in load_exclusions()
                   if normalize_name(e["canonical_name"]) == "best western celina")
        assert rec["evidence_quote"] == "Pets are not accepted."
        assert "petsAllowed" not in rec["evidence_quote"]
        assert "brand boilerplate" in rec["notes"] or "discriminates nothing" in rec["notes"]

    def test_the_columbus_contradiction_is_reported_and_not_acted_on(self, ledger):
        """Two Columbus exclusions rest on this flag while their own retained
        captures state a priced pet-friendly policy. Columbus is frozen and is
        not this work order's to change, so the finding is carried with an exact
        next action and no Columbus file is touched."""
        findings = ledger["cross_market_findings"]
        assert len(findings) == 1
        finding = findings[0]
        assert finding["market_id"] == "columbus-oh"
        assert set(finding["affected_exclusion_ids"]) == {
            "excl-best-western-canal-winchester-inn-columbus-south-east",
            "excl-best-western-executive-inn"}
        assert finding["next_action"].strip()
        columbus = [e for e in load_exclusions() if e.get("market_id") == "columbus-oh"
                    and e["exclusion_state"] == "VERIFIED_NO_PETS"]
        assert len(columbus) == 14


# --------------------------------------------------------------------------- #
# Routing.
# --------------------------------------------------------------------------- #

class TestRouting:

    def test_the_fourteen_proposals_are_each_decided_once(self, ledger):
        rows = ledger["routing_adjudication"]
        assert len(rows) == 14
        assert len({r["slug"] for r in rows}) == 14
        for row in rows:
            assert row["decision"] in (WB.ACCEPTED, WB.HELD, WB.REJECTED), row["slug"]
            assert row["reason"].strip() and row["next_action"].strip(), row["slug"]
        assert (ledger["routing_accepted"], ledger["routing_held"],
                ledger["routing_rejected"]) == (2, 8, 4)

    def test_only_a_first_party_read_confirms_a_route(self, ledger):
        """Dayton held no routes at all before this pass, so all fourteen are
        first-time bindings and none gets the benefit of "it was nearly right".
        The two CONFIRMED are the two whose destination answered a plain GET and
        served an identity key; the eight HELD are recorded, visible and not a
        work instruction, because Choice answered nothing and IHG and Red Roof
        answered 403."""
        accepted = {r["slug"] for r in ledger["routing_adjudication"]
                    if r["decision"] == WB.ACCEPTED}
        assert accepted == {"extended-stay-america-select-suites-dayton-miamisburg",
                            "golden-inn-new-paris"}

    def test_no_route_is_written_for_an_identity_that_became_inventory(self, ledger):
        """Extended Stay America Select Suites Dayton - Miamisburg is ACCEPTED
        and has NO routing record. Verifying its URL is what let its policy
        publish; publishing makes the seed the authority for it, and a surviving
        route would be a second, competing one."""
        written = set(ledger["routing_records_written"])
        assert len(written) == 9
        assert ("route-dayton-oh-extended-stay-america-select-suites-dayton-miamisburg"
                not in written)
        routes = json.loads(WB.ROUTING_PATH.read_text(encoding="utf-8"))["routes"]
        dayton = [r for r in routes if r["market_id"] == DAYTON]
        assert len(dayton) == 9
        assert {r["routing_id"] for r in dayton} == written

    def test_a_bot_walled_brand_never_carries_a_rendered_page_binding(self):
        routes = json.loads(WB.ROUTING_PATH.read_text(encoding="utf-8"))["routes"]
        dayton = [r for r in routes if r["market_id"] == DAYTON]
        rendered = [r for r in dayton if r["binding_method"] == "PAGE_RENDERED"]
        assert {r["hotel_ref"]["normalized_name"] for r in rendered} == {
            "golden inn new paris"}
        for r in dayton:
            if r["binding_method"] == "PAGE_RENDERED":
                continue
            assert r["status"] == "ROUTING_HELD", r["routing_id"]
            assert r["binding_method"] == "BRAND_INDEX_BINDING", r["routing_id"]

    def test_a_rebrand_and_a_wrong_city_are_rejected_not_merged(self, ledger):
        """The two proposals whose page named a different business. An address
        is a place and a name is a business; one building can change hands, and
        M10 is the rule that refuses to let the address decide."""
        by_slug = {r["slug"]: r for r in ledger["routing_adjudication"]}
        for slug in ("hotel-piqua-east-ash", "comfort-inn-washington-court-house"):
            assert by_slug[slug]["decision"] == WB.REJECTED
            assert by_slug[slug]["routing_status"] == ""
        items = {i["slug"]: i for i in ledger["items"]}
        assert items["hotel-piqua-east-ash"]["outcome"] == WB.OUT_CLOSURE_OR_REBRAND


# --------------------------------------------------------------------------- #
# The market, after.
# --------------------------------------------------------------------------- #

class TestDaytonStillReconciles:

    def test_the_129_partition_closes(self, ledger):
        rec = ledger["market_reconciliation"]
        assert rec["census"] == 129
        assert rec["published_pet_friendly"] == 47
        assert rec["verified_no_pets"] == 8
        assert rec["resolved"] == 55
        assert rec["unresolved_or_held"] == 74
        assert (rec["published_pet_friendly"] + rec["verified_no_pets"]
                + rec["unresolved_or_held"]) == 129

    def test_the_ledger_agrees_with_the_committed_authority(self, ledger, facts):
        """The ledger describes the market as this work order left it: 47 / 8.

        PTF-DAYTON-OH-HARDENED-APPLICATION-002 has since published seven more
        records and excluded sixteen more, so the live authority is 54 / 24. The
        ledger is a historical record and is NOT rewritten; what must still hold
        is that it is a SUBSET of the live authority -- nothing it counted has
        since disappeared.
        """
        rec = ledger["market_reconciliation"]
        assert rec["published_pet_friendly"] == EPOCH.fact("pet_friendly")
        assert rec["verified_no_pets"] == EPOCH.fact("verified_no_pets")
        assert len(facts["hotels"]) == NOW.pet_friendly
        registry = [e for e in load_exclusions() if e.get("market_id") == DAYTON
                    and e["exclusion_state"] == "VERIFIED_NO_PETS"]
        assert len(registry) == NOW.verified_no_pets
        assert len(facts["hotels"]) >= rec["published_pet_friendly"]
        assert len(registry) >= rec["verified_no_pets"]

    def test_no_published_identity_is_also_excluded(self, facts):
        keys = {h["key"] for h in facts["hotels"]}
        registry = {normalize_name(e["canonical_name"]) for e in load_exclusions()
                    if e.get("market_id") == DAYTON}
        assert not (keys & registry)

    def test_the_four_answered_properties_left_the_unresolved_list(self):
        """They were all categorised ACCESS_BLOCKED by a static fetch while an
        attended capture of each either sat on disk or was one GET away. Leaving
        them in remaining_unresolved would have them counted twice by the
        release contract's partition cross-check."""
        manifest = json.loads(
            (_ROOT / "launch_packages" / "pettripfinder" / "identity_census"
             / "dayton-recovery-002-proposed-authority.json").read_text(encoding="utf-8"))
        remaining = {r["slug"] for r in manifest["remaining_unresolved"]}
        # 72 when this work order ran. The list is a DERIVED view, subtracted
        # by every order that resolves an identity, so it is what the pin
        # leaves unresolved minus the recovery candidate still proposed.
        assert len(remaining) == NOW.unresolved - STILL_PROPOSED
        for slug in ("best-western-celina", "best-western-plus-miamisburg-dayton",
                     "best-western-wapakoneta-inn",
                     "extended-stay-america-select-suites-dayton-miamisburg"):
            assert slug not in remaining, slug

    def test_the_two_marketing_only_wyndhams_were_held_by_this_pass(self, ledger, facts):
        """Both were POLICY_PARTIAL_HELD here, and this ledger still says so.

        The Baymont has since published, but not on this evidence:
        PTF-DAYTON-OH-HARDENED-REVALIDATION-001 opened the property's own Hotel
        Policies dialog and read a stated policy with a fee, a weight limit and
        a count. What this pass decided about the marketing blurb is unchanged
        and is asserted below; the Wingate, which has had no such read, must
        still be absent from the package.
        """
        keys = {h["key"] for h in facts["hotels"]}
        items = {i["slug"]: i for i in ledger["items"]}
        for slug in ("baymont-by-wyndham-dayton-north",
                     "wingate-by-wyndham-dayton-north"):
            assert items[slug]["outcome"] == WB.OUT_POLICY_PARTIAL_HELD
        assert normalize_name("Wingate by Wyndham Dayton North") not in keys

    def test_a_provisional_identity_never_carries_a_published_policy(self, ledger, facts):
        """Golden Inn New Paris states a $15 pet fee on its own site and does not
        publish: its census identity is still IDENTITY_PROVISIONAL. The route
        binds -- that is where to look -- and the policy waits for the identity."""
        item = next(i for i in ledger["items"] if i["slug"] == "golden-inn-new-paris")
        assert item["identity_state"] == "IDENTITY_PROVISIONAL"
        assert item["published_after"] is False
        assert normalize_name("Golden Inn New Paris") not in {
            h["key"] for h in facts["hotels"]}


# --------------------------------------------------------------------------- #
# Determinism.
# --------------------------------------------------------------------------- #

class TestTheLedgerIsDerived:

    def test_rebuilding_reproduces_the_committed_ledger(self, ledger):
        if not (WB.input_present() and WB.captures_present()):
            pytest.skip("data/ is gitignored; operator package or captures absent")
        assert WB.build() == json.loads(WB.serialize(ledger))
