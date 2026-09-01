"""PTF-CLEVELAND-WORK-BROWSER-INTEGRATION-001 -- targeted tests.

Two halves, deliberately separated by what they need:

* The LEDGER tests read only tracked files
  (``cleveland_work_browser_pass_001.json``, the census, the routing authority,
  the policy facts, the exclusions). They run in every clone, including one with
  no ``data/`` directory, because the ledger is committed authority.
* The INPUT tests re-derive the adjudication from the untracked operator
  package. They declare that package as a precondition and skip with the path
  named -- the pattern ``ed53d5b``/``441498d`` established after a worktree with
  no ``data/`` reported nine phantom failures. The guard calls the module's own
  ``input_present()`` rather than testing for a directory, so it cannot skip a
  real regression away.

The most important assertions here are negative: that this batch published no
pet fact, wrote no exclusion, and left Columbus and Dayton untouched. A
transcription is research, not evidence, and these tests are what stops the
next integrator from quietly deciding otherwise.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder import integrate_cleveland_work_browser_001 as WB
from scripts.pettripfinder.identity_routing import (
    BINDING_PAGE_RENDERED,
    ROUTING_CONFIRMED,
    validate_record,
)

_ROOT = Path(__file__).resolve().parents[2]
LEDGER_PATH = (_ROOT / "launch_packages" / "pettripfinder"
               / "cleveland_work_browser_pass_001.json")
CENSUS_PATH = (_ROOT / "launch_packages" / "pettripfinder" / "identity_census"
               / "cleveland-akron-canton-oh.json")
P2_PACKET_PATH = (_ROOT / "launch_packages" / "pettripfinder"
                  / "cleveland_pass2_founder_review_packet.json")
ROUTING_PATH = (_ROOT / "launch_packages" / "pettripfinder" / "identity_routing.json")
CLEVELAND_FACTS_PATH = (_ROOT / "launch_packages" / "pettripfinder"
                        / "hotel_policy_facts_cleveland-akron-canton-oh.json")
COLUMBUS_FACTS_PATH = (_ROOT / "launch_packages" / "pettripfinder"
                       / "hotel_policy_facts.json")
DAYTON_FACTS_PATH = (_ROOT / "launch_packages" / "pettripfinder"
                     / "hotel_policy_facts_dayton-oh.json")
EXCLUSIONS_PATH = (_ROOT / "launch_packages" / "pettripfinder" / "hotel_exclusions.json")


def _json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def ledger():
    return _json(LEDGER_PATH)


@pytest.fixture(scope="module")
def census():
    return _json(CENSUS_PATH)


_INPUT = WB.input_present()
_NEEDS_INPUT = pytest.mark.skipif(
    not _INPUT,
    reason="operator package absent (gitignored): %s" % WB.INPUT_DIR)


# --------------------------------------------------------------------------- #
# The ledger. Tracked, so these run everywhere.
# --------------------------------------------------------------------------- #

class TestLedgerShape:

    def test_schema_and_scope(self, ledger):
        assert ledger["schema"] == WB.SCHEMA
        assert ledger["market_id"] == WB.MARKET
        assert ledger["work_order"] == WB.WORK_ORDER

    def test_every_queued_property_appears_exactly_once(self, ledger):
        slugs = [i["slug"] for i in ledger["items"]]
        assert len(slugs) == WB.EXPECTED_QUEUE_SIZE
        assert len(set(slugs)) == WB.EXPECTED_QUEUE_SIZE

    def test_no_property_is_silently_dropped(self, ledger):
        """Every item carries an outcome from the closed vocabulary, and the
        outcome counts sum to the queue size. A property with no outcome, or an
        outcome outside the vocabulary, is a dropped property."""
        for item in ledger["items"]:
            assert item["outcome"] in WB.OUTCOMES, item["slug"]
        assert sum(ledger["outcome_counts"].values()) == WB.EXPECTED_QUEUE_SIZE

    def test_every_unresolved_property_carries_exactly_one_next_action(self, ledger):
        for item in ledger["items"]:
            if item["outcome"] in WB.RESOLVING_OUTCOMES:
                continue
            action = item["next_action"]
            assert action and action.strip(), item["slug"]
            # One action, not a list of options dressed as a sentence.
            assert " or else " not in action.lower(), item["slug"]

    def test_the_partition_matches_the_declared_input_partition(self, ledger):
        assert ledger["reconciliation"]["partition"] == WB.EXPECTED_PARTITION
        assert ledger["reconciliation"]["duplicates"] == 0
        assert ledger["reconciliation"]["omissions"] == 0

    def test_the_rollup_shortfall_is_recorded_not_hidden(self, ledger):
        """The rolled-up CSV carries 131 rows, not 135: its own manifest says
        batch 2 was reviewed earlier and deliberately not repeated. Reconciling
        against the roll-up alone would drop four properties, so the ledger
        names them."""
        assert ledger["reconciliation"]["rollup_rows"] == 131
        assert len(ledger["reconciliation"]["batch_2_not_in_rollup"]) == 4

    def test_every_item_binds_to_a_cleveland_census_identity(self, ledger, census):
        from scripts.pettripfinder.cleveland_final_partition_002 import (
            IDENTITY_RENAMES,
        )
        known = {h["slug"]: h for h in census["hotels"]}
        for item in ledger["items"]:
            # Two identities were renamed on founder authorization after this
            # transcript was written; the ledger keeps what it saw, so the
            # binding follows the alias rather than rewriting history.
            if item["normalized_name"] in IDENTITY_RENAMES:
                current = IDENTITY_RENAMES[item["normalized_name"]]
                assert any(h["normalized_name"] == current
                           for h in census["hotels"]), current
                continue
            # Three identities the founder ruled non-lodging (ruling C) left
            # the census with the PTF-CLEVELAND-AKRON-CANTON-HARDENED-
            # APPLICATION-005 promotion; the ledger keeps what it saw, and the
            # binding asserts their ABSENCE rather than rewriting history.
            if item["normalized_name"] in {"cleveland house hotels",
                                           "inn the doghouse",
                                           "the rowley inn"}:
                assert item["slug"] not in known, item["slug"]
                continue
            # The 005 promotion also renamed the Studio 6 row to its
            # founder-ruled successor (ruling B); the binding follows the
            # supersession the census records rather than rewriting the ledger.
            if item["normalized_name"] == "studio 6 extended stay hotel mentor":
                assert any(h["normalized_name"] ==
                           "suburban studios mentor cleveland northeast"
                           for h in census["hotels"])
                continue
            assert item["slug"] in known, item["slug"]
            assert item["normalized_name"] == known[item["slug"]]["normalized_name"]
            assert item["market_id"] == WB.MARKET


class TestNothingPublished:
    """The batch's whole outcome, asserted from more than one direction."""

    def test_no_property_reached_a_resolving_outcome(self, ledger):
        assert ledger["outcome_counts"][WB.OUT_PUBLISHED] == 0
        assert ledger["outcome_counts"][WB.OUT_VERIFIED_NO_PETS] == 0

    def test_published_and_no_pets_totals_are_unchanged(self, ledger):
        totals = ledger["market_totals"]
        assert totals["published_pet_friendly_before"] == totals["published_pet_friendly_after"]
        assert totals["verified_no_pets_before"] == totals["verified_no_pets_after"]
        assert totals["resolved_before"] == totals["resolved_after"]
        assert totals["unresolved_before"] == totals["unresolved_after"]

    def test_the_ledger_totals_equal_the_authorities_they_describe(self, ledger):
        """A stated total that no longer matches its source is worse than none."""
        totals = ledger["market_totals"]
        # The ledger's "after" figures describe the authorities as pass 001
        # left them. PTF-CLEVELAND-PASS2-FOUNDER-DECISIONS-001 later published
        # twenty and excluded twenty-three by founder decision, so the live
        # authorities equal the stated totals plus exactly those deltas.
        packet = _json(P2_PACKET_PATH)
        pass3 = _json(P2_PACKET_PATH.parent
                      / "cleveland_pass3_founder_review_packet.json")
        pass4 = _json(P2_PACKET_PATH.parent
                      / "cleveland_pass4_founder_review_packet.json")
        # PTF-CLEVELAND-AKRON-CANTON-HARDENED-APPLICATION-005 later applied
        # 21 more records and 11 more exclusions under founder authorization;
        # the deltas are read from its committed promotion report, so the
        # arithmetic still names every publication since this ledger closed.
        applied_005 = _json(P2_PACKET_PATH.parent
                            / "cleveland_akron_canton_oh_promotion_report_005.json")["summary"]
        published_later = (len(packet["positive_candidates"])
                           + len(pass3["positive_candidates"])
                           + len(pass4["positive_candidates"])
                           + len(pass4["rename_candidates"])
                           + len(applied_005["records_applied"]))
        assert totals["published_pet_friendly_after"] + published_later == len(
            _json(CLEVELAND_FACTS_PATH)["hotels"])
        exclusions = _json(EXCLUSIONS_PATH)
        records = exclusions["exclusions"] if isinstance(exclusions, dict) else exclusions
        excluded_later = (len(packet["negative_candidates"])
                          + len(pass3["negative_candidates"])
                          + len(pass4["negative_candidates"])
                          + len(applied_005["exclusions_applied"]))
        assert totals["verified_no_pets_after"] + excluded_later == len(
            [r for r in records if r.get("market_id") == WB.MARKET])
        # The ledger described the 188-identity census; the 005 promotion
        # moved the census to 220 (32 admissions, 3 retirements) and records
        # it in the census's own promotion block, which is asserted instead
        # of pretending the ledger described a census it never saw.
        assert totals["confirmed_identities"] == 188
        census_doc = _json(CENSUS_PATH)
        assert census_doc["count"] == 220
        assert census_doc["promotion"]["from_count"] == 188

    def test_no_reviewed_slug_entered_the_cleveland_policy_facts(self, ledger):
        """None of the 135 acquired a policy record from the TRANSCRIPTION.
        The rows published since got there through the Pass-2 hash-bound
        attended captures, each named in the committed founder packet."""
        published = {h["key"] for h in _json(CLEVELAND_FACTS_PATH)["hotels"]}
        packet = _json(P2_PACKET_PATH)
        decided = {c["hotel_id"] for c in packet["positive_candidates"]}
        for later in ("cleveland_pass3_founder_review_packet.json",
                      "cleveland_pass4_founder_review_packet.json"):
            pk = _json(P2_PACKET_PATH.parent / later)
            for group in ("positive_candidates", "rename_candidates"):
                decided |= {c["identity_key"] for c in pk.get(group, [])}
        for item in ledger["items"]:
            if not item["published_before"]:
                assert (item["normalized_name"] not in published
                        or item["normalized_name"] in decided), item["slug"]

    def test_no_reviewed_slug_entered_the_exclusion_authority(self, ledger):
        """Sixteen properties transcribed a refusal. A refusal is guarded at the
        same bar as a permission -- hotel_exclusions requires source_hash -- so
        none of them published either."""
        exclusions = _json(EXCLUSIONS_PATH)
        records = exclusions["exclusions"] if isinstance(exclusions, dict) else exclusions
        excluded = {r["normalized_name"] for r in records}
        reviewed = {i["normalized_name"] for i in ledger["items"]}
        packet = _json(P2_PACKET_PATH)
        decided = {c["hotel_id"] for c in packet["negative_candidates"]}
        for later in ("cleveland_pass3_founder_review_packet.json",
                      "cleveland_pass4_founder_review_packet.json"):
            pk = _json(P2_PACKET_PATH.parent / later)
            decided |= {c["identity_key"] for c in pk["negative_candidates"]}
        # The 11 refusals PTF-CLEVELAND-AKRON-CANTON-HARDENED-APPLICATION-005
        # applied were each founder-authorized against a hash-bound first-party
        # capture; the promotion report names them, exactly as the packets do.
        decided |= set(_json(P2_PACKET_PATH.parent
                             / "cleveland_akron_canton_oh_promotion_report_005.json")
                       ["summary"]["exclusions_applied"])
        assert not (reviewed & excluded) - decided - {
            r["normalized_name"] for r in records
            if r.get("observed_at", "") < WB.AS_OF}


class TestEvidenceDetermination:

    def test_the_artifact_class_is_recorded_and_refused_for_publication(self, ledger):
        determination = ledger["evidence_determination"]
        assert determination["artifact_class"] == WB.ARTIFACT_CLASS
        assert determination["accepted_for_publication"] is False
        assert determination["accepted_for_evidence_completion_queue"] is True

    def test_the_screenshot_tree_is_reported_as_empty(self, ledger):
        """The work order asked that Batch 2 screenshots be bound where present.
        They are not present: 135 directories, zero files. Recording the count
        is what makes 'none were bound' checkable rather than asserted."""
        screenshots = ledger["evidence_determination"]["screenshots"]
        assert screenshots["files"] == 0
        assert screenshots["directories"] == WB.EXPECTED_QUEUE_SIZE

    def test_all_twenty_seven_input_hashes_are_preserved(self, ledger):
        hashes = ledger["input_package"]["sha256"]
        assert set(hashes) == set(WB.EXPECTED_FILES)
        assert len(hashes) == 27
        for name, digest in hashes.items():
            assert digest.startswith("sha256:") and len(digest) == 71, name

    def test_hashing_the_transcription_did_not_make_it_publishable(self, ledger):
        """The hashes exist and the batch still published nothing. Stated as a
        test because the tempting error is to read a preserved hash as
        provenance for the words it covers."""
        assert ledger["input_package"]["sha256"]
        assert ledger["input_package"]["tracked"] is False
        assert ledger["outcome_counts"][WB.OUT_PUBLISHED] == 0

    def test_every_evidence_candidate_states_what_it_is_waiting_for(self, ledger):
        candidates = [i for i in ledger["items"]
                      if i["outcome"] == WB.OUT_EVIDENCE_CANDIDATE]
        assert candidates
        for item in candidates:
            assert "NO_ARTIFACT" in item["reason_code"] or "ESTABLISHES_NOTHING" in \
                item["reason_code"], item["slug"]
            assert "apture" in item["next_action"] or "creenshot" in item["next_action"]

    def test_the_transcribed_wording_is_preserved_verbatim(self, ledger):
        """A held candidate is only useful later if the words survive intact."""
        stated = [i for i in ledger["items"]
                  if i["partition"] == "visible_policy"]
        assert len(stated) == WB.EXPECTED_PARTITION["visible_policy"]
        assert all(i["transcribed_policy_wording"].strip() for i in stated)


class TestPolicyWordingShapes:
    """What the pages said, independent of whether it may publish. This is the
    ranking a later capture pass needs: a marketing sentence lands on
    POLICY_PARTIAL even with a perfect capture, so the structured ones are worth
    capturing first."""

    def test_shapes_partition_the_visible_policy_rows(self, ledger):
        shapes = ledger["visible_policy_wording_shapes"]
        assert sum(shapes.values()) == WB.EXPECTED_PARTITION["visible_policy"]

    def test_marketing_only_rows_are_identified_as_such(self, ledger):
        """integrate_cleveland_capture_003 already refused three Wyndham
        properties on exactly this wording. The count is recorded so the same
        finding is not rediscovered a third time."""
        assert ledger["visible_policy_wording_shapes"]["AFFIRMATIVE_MARKETING_ONLY"] > 0

    def test_a_refusal_is_never_scored_as_a_permission(self, ledger):
        """Fifteen rows the input manifest counted as 'policy visible' state
        that pets are NOT accepted. Classifying them as affirmative would have
        queued fifteen no-pets hotels for publication as pet-friendly."""
        negative = [i for i in ledger["items"]
                    if i["policy_wording_shape"] == "NEGATIVE"
                    and i["partition"] == "visible_policy"]
        assert len(negative) == 15
        for item in negative:
            assert item["reason_code"] == "NEGATIVE_POLICY_TRANSCRIBED_NO_ARTIFACT"

    def test_the_one_self_contradicting_row_is_recorded_not_resolved(self, ledger):
        """A row classified HTTP_404 also transcribes a rendered Marriott page
        with address, phone and 'Pets Not Allowed'. A 404 produces none of
        that. Preferring either half silently would either discard a refusal or
        publish off a page the reviewer called missing, so the row is held and
        the inconsistency is named."""
        flagged = [i for i in ledger["items"]
                   if i["reason_code"] == "CLASSIFICATION_CONTRADICTS_TRANSCRIPTION"]
        assert len(flagged) == 1
        item = flagged[0]
        assert item["browser_classification"] == "HTTP_404"
        assert item["policy_wording_shape"] == "NEGATIVE"
        assert item["outcome"] == WB.OUT_MANUAL
        assert "HTTP_404" in item["next_action"]

    def test_a_faq_question_is_not_its_own_answer(self, ledger):
        """Six IHG/Crowne Plaza pages rendered 'Can I bring my pet to X?' and
        nothing beneath it -- the accordion is client-side. Reading the question
        as evidence of a policy is the exact shape of a fabricated fact."""
        question_only = [i for i in ledger["items"]
                         if i["policy_wording_shape"] == "QUESTION_ONLY"]
        assert question_only
        for item in question_only:
            assert item["outcome"] == WB.OUT_SURFACE_GAP

    def test_contradictions_are_held_and_never_adjudicated_here(self, ledger):
        conflicted = [i for i in ledger["items"]
                      if i["outcome"] == WB.OUT_CONTRADICTION]
        assert conflicted
        for item in conflicted:
            assert item["policy_wording_shape"] == "CONTRADICTORY"


class TestNoDerivedPropertyCode:
    """Rule 3 of the work order: never derive a property code from a URL."""

    def test_no_item_claims_a_property_code_the_page_did_not_display(self, ledger):
        for item in ledger["items"]:
            check = item["identity_check"]
            if check["property_code_from_page_only"]:
                assert item["displayed_property_code"].strip(), item["slug"]
            else:
                assert not item["displayed_property_code"].strip(), item["slug"]

    def test_this_batch_displayed_no_property_codes_at_all(self, ledger):
        """Every row's own record says WITHHELD_NOT_DISPLAYED or leaves the
        column empty. Worth asserting: several source URLs contain a brand code
        (``cleaa``, ``cakct``, ``oh082``) and lifting one out of the path would
        be indistinguishable from reading it off the page."""
        assert all(not i["displayed_property_code"].strip() for i in ledger["items"])


class TestRoutingAdjudication:

    def test_every_proposal_is_adjudicated_exactly_once(self, ledger):
        adjudicated = [r["slug"] for r in ledger["routing_adjudication"]]
        assert len(adjudicated) == WB.EXPECTED_PARTITION["routing_correction_proposed"]
        assert len(set(adjudicated)) == len(adjudicated)

    def test_accepted_and_rejected_are_recorded_separately_with_reasons(self, ledger):
        assert ledger["routing_accepted"] + ledger["routing_rejected"] == 15
        for record in ledger["routing_adjudication"]:
            assert record["decision"] in (WB.ACCEPTED, WB.REJECTED)
            assert len(record["reason"]) > 40, record["slug"]
            assert record["next_action"].strip(), record["slug"]

    def test_the_accepted_route_finished_its_job_and_was_retired(self):
        """The accepted correction (Sonesta ES -> Simply Suites) is exactly
        where the Pass-3 attended capture read the policy that published
        this identity. Published identities hold no routes, so the record
        was retired on publication and the corrected URL now lives on the
        published record itself."""
        routing = _json(ROUTING_PATH)
        assert not any(r["routing_id"] == WB.ACCEPTED_ROUTE_ID
                       for r in routing["routes"])
        record = next(h for h in _json(CLEVELAND_FACTS_PATH)["hotels"]
                      if h["identity_key"]
                      == "sonesta es suites cleveland airport")
        assert record["source_url"] == WB.ACCEPTED_ROUTE_URL

    def test_routing_did_not_grow_or_shrink(self):
        """This pass CORRECTED one record in place; it added and retired none.

        Scoped to the two markets that existed when it ran, because that is what
        it can honestly claim. PTF-DAYTON-WORK-BROWSER-INTEGRATION-001 has since
        opened Dayton routing and taken the file to 174 -- asserting the global
        total here would make this test fail for something the Cleveland pass
        did not do."""
        routing = _json(ROUTING_PATH)
        assert routing["count"] == len(routing["routes"])
        by_market = {}
        for record in routing["routes"]:
            by_market[record["market_id"]] = by_market.get(record["market_id"], 0) + 1
        # 145 when this pass closed; 102 after Pass 2 retired the routes
        # of the 43 founder-decided identities; 58 after Pass 3
        # retired 44 more; 61 after PTF-CLEVELAND-ROUTING-REPAIR-001
        # created three; 37 after PTF-CLEVELAND-AKRON-CANTON-HARDENED-
        # APPLICATION-005 moved the published successor's route to
        # cleveland_route_retirement_005_ledger.json.
        assert by_market["cleveland-akron-canton-oh"] == 37
        assert by_market["columbus-oh"] == 20

    def test_no_two_identities_own_one_official_url(self):
        """The collision audit, as a standing assertion rather than a one-off
        check: a corrected URL that another identity already holds would route
        two hotels at one page."""
        seen = {}
        for record in _json(ROUTING_PATH)["routes"]:
            key = record["official_property_url"].rstrip("/").lower()
            owner = record["hotel_ref"]["normalized_name"]
            if key in seen:
                assert seen[key] == owner, key
            seen[key] = owner

    def test_a_rejected_proposal_never_reached_authority(self, ledger):
        rejected = {r["slug"] for r in ledger["routing_adjudication"]
                    if r["decision"] == WB.REJECTED}
        assert len(rejected) == 14
        urls = {r["official_property_url"] for r in _json(ROUTING_PATH)["routes"]}
        # The two proposals that were genuinely different endpoints and were
        # still refused: a brand SEARCH page and a Sonesta CITY page.
        assert "https://www.wyndhamhotels.com/hotels/richfield-ohio?brand_id=DI" not in urls
        assert "https://www.sonesta.com/locations/us/ohio/westlake" not in urls

    def test_no_session_artifact_entered_authority(self):
        """Two proposals carried a Cloudflare challenge token and a checkout-date
        parameter. Both are per-visit and would rot immediately."""
        for record in _json(ROUTING_PATH)["routes"]:
            url = record["official_property_url"]
            assert "__cf_chl" not in url, record["routing_id"]
            assert "checkOutDate" not in url, record["routing_id"]

    def test_routing_carries_no_pet_fact(self):
        """Routing says where a property speaks, never what it said. The
        contract enforces this on field NAMES; this checks no surviving
        Cleveland record's free text has smuggled a policy in as prose.
        (The accepted record itself was retired when its identity
        published.)"""
        for record in _json(ROUTING_PATH)["routes"]:
            if record.get("market_id") != "cleveland-akron-canton-oh":
                continue
            blob = json.dumps(record).lower()
            for token in ("pet fee", "pets allowed", "weight limit",
                          "per night"):
                assert token not in blob, (record["routing_id"], token)


class TestOtherMarketsUntouched:

    def test_no_cleveland_record_crossed_into_another_market(self, ledger):
        reviewed = {i["normalized_name"] for i in ledger["items"]}
        for path in (COLUMBUS_FACTS_PATH, DAYTON_FACTS_PATH):
            other = {h["key"] for h in _json(path)["hotels"]}
            assert not (reviewed & other), path.name

    def test_no_routing_record_changed_market(self):
        for record in _json(ROUTING_PATH)["routes"]:
            assert record["market_id"] == record["hotel_ref"]["market_id"]

    def test_columbus_and_dayton_route_counts_are_unchanged(self):
        routes = _json(ROUTING_PATH)["routes"]
        by_market = {}
        for record in routes:
            by_market[record["market_id"]] = by_market.get(record["market_id"], 0) + 1
        assert by_market["columbus-oh"] == 20
        assert by_market["cleveland-akron-canton-oh"] == 37  # 38 after routing-repair creations; 37 after the 005 successor-route ledgering


# --------------------------------------------------------------------------- #
# Re-derivation from the untracked operator package.
# --------------------------------------------------------------------------- #

@_NEEDS_INPUT
class TestInputInventoryGate:

    def test_the_package_holds_exactly_twenty_seven_expected_files(self):
        hashes = WB.input_hashes()
        assert len(hashes) == 27
        assert list(hashes) == list(WB.EXPECTED_FILES)

    def test_an_extra_or_missing_file_fails_the_gate(self, tmp_path):
        for name in WB.EXPECTED_FILES[:-1]:
            (tmp_path / name).write_text("x", encoding="utf-8")
        with pytest.raises(WB.WorkBrowserInputError):
            WB.input_hashes(tmp_path)

    def test_the_preserved_hashes_re_derive(self, ledger):
        assert WB.input_hashes() == ledger["input_package"]["sha256"] or \
            dict(WB.input_hashes()) == ledger["input_package"]["sha256"]


@_NEEDS_INPUT
class TestReconciliationIsDerivedNotTrusted:

    def test_the_batches_carry_all_one_hundred_and_thirty_five(self):
        rows = WB.load_rows()
        assert len(rows) == WB.EXPECTED_QUEUE_SIZE
        assert len({r["slug"] for r in rows}) == WB.EXPECTED_QUEUE_SIZE

    def test_a_short_handback_is_refused(self):
        rows = WB.load_rows()[:-1]
        census = [h["slug"] for h in _json(CENSUS_PATH)["hotels"]]
        with pytest.raises(WB.WorkBrowserInputError):
            WB.reconcile(rows, WB.load_rollup_slugs(), census)

    def test_a_duplicate_reconciliation_is_refused(self):
        rows = WB.load_rows()
        rows[1] = dict(rows[0])
        census = [h["slug"] for h in _json(CENSUS_PATH)["hotels"]]
        with pytest.raises(WB.WorkBrowserInputError):
            WB.reconcile(rows, WB.load_rollup_slugs(), census)

    def test_a_row_outside_the_cleveland_census_is_refused(self):
        rows = WB.load_rows()
        rows[0] = dict(rows[0], slug="not-a-cleveland-hotel")
        census = [h["slug"] for h in _json(CENSUS_PATH)["hotels"]]
        with pytest.raises(WB.WorkBrowserInputError):
            WB.reconcile(rows, WB.load_rollup_slugs(), census)

    def test_the_declared_partition_is_verified_not_accepted(self):
        """The work order supplied 80/28/15/12 as EXPECTED input. It is checked
        against the batches, and a batch whose classifications disagree fails."""
        rows = WB.load_rows()
        rows[0] = dict(rows[0], classification=WB.IDENTITY_ONLY_CLASSIFICATION)
        census = [h["slug"] for h in _json(CENSUS_PATH)["hotels"]]
        with pytest.raises(WB.WorkBrowserInputError):
            WB.reconcile(rows, WB.load_rollup_slugs(), census)


@_NEEDS_INPUT
class TestLedgerReDerives:

    def test_building_again_reproduces_the_committed_ledger(self, ledger):
        """Deterministic: same package in, same ledger out.

        The live-derived fields (per-item published_after and the market
        totals' *_after figures) legitimately moved when the Pass-2 founder
        decisions published and excluded reviewed identities; the committed
        ledger keeps the values pass 001 stated. Everything the PACKAGE
        determines must still reproduce byte-for-byte."""
        def _frozen(doc):
            doc = json.loads(json.dumps(doc))
            doc.pop("market_totals", None)
            for item in doc.get("items", []):
                item.pop("published_before", None)
                item.pop("published_after", None)
            return doc
        assert _frozen(json.loads(WB.serialize(WB.build()))) == _frozen(ledger)

    def test_the_build_is_pure_with_respect_to_authority(self):
        before = ROUTING_PATH.read_bytes(), CLEVELAND_FACTS_PATH.read_bytes()
        WB.build()
        assert (ROUTING_PATH.read_bytes(), CLEVELAND_FACTS_PATH.read_bytes()) == before


@_NEEDS_INPUT
class TestPolicyShapeClassifier:
    """The classifier decides which held candidate is worth capturing first, so
    its edge cases are worth pinning."""

    def test_service_animal_only_language_is_not_a_permission(self):
        assert WB.policy_shape(
            "Pets | Pets Allowed: No | General: Only service animals are "
            "permitted, free of charge.") == "NEGATIVE"

    def test_free_of_charge_in_a_refusal_is_not_a_pet_fee(self):
        """'free of charge' contains a fee-shaped phrase and appears inside the
        refusal sentence. An earlier pass scored six Choice refusals as
        fee-bearing permissions on exactly this."""
        assert WB.policy_shape(
            "Pets Allowed: No General: Only service animals are permitted, "
            "free of charge.") != "AFFIRMATIVE_STRUCTURED"

    def test_marketing_copy_is_separated_from_a_stated_policy(self):
        assert WB.policy_shape(
            "Our pet-friendly hotel is just steps from the Rapid Transit "
            "Station.") == "AFFIRMATIVE_MARKETING_ONLY"
        assert WB.policy_shape(
            "Pets Welcome | Dogs are allowed with a non-refundable fee of USD "
            "75 per room per stay | Maximum Pet Weight: 50.0lbs"
        ) == "AFFIRMATIVE_STRUCTURED"

    def test_a_bare_faq_question_establishes_nothing(self):
        assert WB.policy_shape(
            "Can I bring my pet to Holiday Inn Express & Suites Alliance?"
        ) == "QUESTION_ONLY"

    def test_both_statements_on_one_page_are_a_contradiction(self):
        assert WB.policy_shape(
            "Pet Friendly | PET FRIENDLY | Pets | Pets Allowed: No"
        ) == "CONTRADICTORY"

    def test_empty_wording_is_not_a_policy(self):
        assert WB.policy_shape("") == "NONE"
        assert WB.policy_shape("   ") == "NONE"
