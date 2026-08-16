"""PTF-CLEVELAND-WORK-BROWSER-INTEGRATION-002 -- the Cleveland final partition.

What these defend is the guarantee ``test_cleveland_authority``'s pinned
``(188, 21, 8, 29, 159)`` cannot give. ``build_market_manifest.build_package``
derives ``unresolved`` by SUBTRACTION, so that tuple stays green even if the
unresolved manifest enumerates the wrong 159 hotels. Here the MEMBERSHIP is
asserted: every census identity in exactly one final state, every unresolved
one carrying exactly one next action, and the unresolved manifest agreeing with
routing authority on every URL -- the drift this work order found and fixed.

Everything in this module reads committed authority under ``launch_packages/``,
so it all runs in a clone with no ``data/`` directory. Two tests need the
gitignored operator screenshot tree, and both skip honestly when it is absent
rather than reporting zero because they could not look -- the ed53d5b/441498d
pattern. In a data-less clone that is 41 passed and 2 skipped.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder.cleveland_final_partition_002 import (
    ACCESS_BLOCKED, AUTHORED_HERE, AWAITING_ATTENDED_CAPTURE, AWAITING_CENSUS_REVIEW,
    AWAITING_CONTRADICTION_RESOLUTION, AWAITING_OFFICIAL_URL,
    AWAITING_POLICY_ARTIFACT, AWAITING_POLICY_OBSERVATION,
    AWAITING_PROPERTY_LEVEL_URL, AWAITING_ROUTING_REPLACEMENT,
    AWAITING_ROUTING_REVIEW, FINAL_STATES, MARKET, PARTITION_PATH,
    PUBLISHED_PET_FRIENDLY, SCREENSHOT_DIR, STATE_MEANINGS, TERMINAL_STATES,
    UNRESOLVED_STATES, VERIFIED_NO_PETS, build_partition, collision_audit,
)

_ROOT = Path(__file__).resolve().parents[2]
_LP = _ROOT / "launch_packages" / "pettripfinder"
CENSUS_PATH = _LP / "identity_census" / ("%s.json" % MARKET)
ROUTING_PATH = _LP / "identity_routing.json"
UNRESOLVED_PATH = _LP / "cleveland_unresolved_manifest.json"
WORK_BROWSER_PATH = _LP / "cleveland_work_browser_pass_001.json"


def _json(path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def committed():
    """The partition as committed, not as recomputed."""
    return _json(PARTITION_PATH)


@pytest.fixture(scope="module")
def rebuilt():
    """The partition recomputed from authority. Must equal the committed one."""
    return build_partition()


def _without_screenshot_census(doc):
    """The one field a rebuild cannot reproduce without the gitignored operator
    tree. Everything else in the ledger is derived from committed authority."""
    doc = json.loads(json.dumps(doc))
    doc["evidence_determination"].pop("screenshot_census", None)
    return doc


class TestTheCommittedLedgerIsWhatTheCodeProduces:

    def test_rebuilding_reproduces_the_committed_partition(self, committed, rebuilt):
        """A hand-edited ledger is not authority. If someone changes a state by
        editing JSON, this fails.

        The screenshot census is compared separately, because it reads the
        gitignored operator tree and a clone without ``data/`` can only report
        "not scanned" -- which is the honest answer there, not a mismatch."""
        assert _without_screenshot_census(rebuilt) == _without_screenshot_census(committed)

    def test_the_screenshot_census_also_reproduces_when_the_tree_is_present(
            self, committed, rebuilt):
        if not SCREENSHOT_DIR.exists():
            pytest.skip("operator screenshot tree is gitignored and absent here")
        assert (rebuilt["evidence_determination"]["screenshot_census"]
                == committed["evidence_determination"]["screenshot_census"])

    def test_it_declares_its_market_and_schema(self, committed):
        assert committed["market_id"] == MARKET
        # PTF-CENSUS-PARTITION-NORMALIZATION-001 upgraded the schema to 1.1.
        # The upgrade is strictly ADDITIVE -- every item gained a canonical
        # identity_key and its determined_by/updated_at provenance, and this
        # document's evidence determination, crosswalk, authority-agreement and
        # collision-audit blocks are untouched. Membership did not move.
        assert committed["schema"] == "ptf-market-final-partition/1.1"


class TestItIsActuallyAPartition:

    def test_every_census_identity_appears_exactly_once(self, committed):
        census = _json(CENSUS_PATH)
        keys = [i["normalized_name"] for i in committed["items"]]
        assert len(keys) == len(set(keys)) == census["count"] == 188
        assert set(keys) == {h["normalized_name"] for h in census["hotels"]}

    def test_every_state_is_from_the_closed_set(self, committed):
        assert {i["final_state"] for i in committed["items"]} <= set(FINAL_STATES)

    def test_every_state_in_the_closed_set_is_explained(self):
        assert set(STATE_MEANINGS) == set(FINAL_STATES)
        assert all(len(STATE_MEANINGS[s]) > 40 for s in FINAL_STATES)

    def test_the_states_sum_to_the_census(self, committed):
        counts = committed["final_state_counts"]
        assert sum(counts.values()) == 188
        assert sum(counts[s] for s in TERMINAL_STATES) == 29
        assert sum(counts[s] for s in UNRESOLVED_STATES) == 159

    def test_the_reconciliation_matches_the_market_authority(self, committed):
        from scripts.pettripfinder.build_market_manifest import build_package

        rec = committed["reconciliation"]
        assert (rec["confirmed_identities"], rec["published_pet_friendly"],
                rec["verified_no_pets"], rec["resolved"],
                rec["unresolved"]) == (188, 21, 8, 29, 159)
        assert build_package(MARKET).reconciliation() == (188, 21, 8, 29, 159)

    def test_published_and_excluded_states_match_the_publication_authority(
            self, committed):
        """The two terminal states are not asserted here -- they are read from
        the packages that own them, and this checks the join did not drift."""
        from scripts.pettripfinder.hotel_exclusions import load_exclusions
        from scripts.pettripfinder.site_data import (
            normalize_name, published_facts_path,
        )

        published = {h["key"] for h in
                     _json(published_facts_path(MARKET))["hotels"]}
        no_pets = {normalize_name(e["canonical_name"]) for e in load_exclusions()
                   if e.get("market_id") == MARKET
                   and e["exclusion_state"] == "VERIFIED_NO_PETS"}
        by_state = {}
        for item in committed["items"]:
            by_state.setdefault(item["final_state"], set()).add(item["normalized_name"])
        assert by_state[PUBLISHED_PET_FRIENDLY] == published
        assert by_state[VERIFIED_NO_PETS] == no_pets

    def test_the_unresolved_set_is_census_minus_resolved_by_membership(self, committed):
        """The guarantee the pinned tuple cannot give: build_package derives
        unresolved by subtraction, so it would pass with the wrong 159 hotels."""
        unresolved_here = {i["normalized_name"] for i in committed["items"]
                           if not i["resolved"]}
        assert unresolved_here == {i["normalized_name"]
                                   for i in _json(UNRESOLVED_PATH)["items"]}
        assert len(unresolved_here) == 159


class TestExactlyOneNextAction:

    def test_every_unresolved_identity_has_one_and_only_one(self, committed):
        for item in committed["items"]:
            if item["resolved"]:
                continue
            action = item["next_action"]
            assert action.strip(), item["normalized_name"]
            assert item["next_action_source"] in (
                "cleveland_work_browser_pass_001", "cleveland_unresolved_manifest",
                AUTHORED_HERE)

    def test_a_terminal_identity_carries_none(self, committed):
        for item in committed["items"]:
            if item["resolved"]:
                assert item["next_action"] == "", item["normalized_name"]

    def test_the_next_action_is_carried_verbatim_from_its_source(self, committed):
        """This layer copies actions; it does not rewrite them. The identities
        the Work-browser pass examined take that pass's action; the ones it never
        saw keep the unresolved manifest's."""
        wb = {i["normalized_name"]: i["next_action"]
              for i in _json(WORK_BROWSER_PATH)["items"]}
        un = {i["normalized_name"]: i["next_action"]
              for i in _json(UNRESOLVED_PATH)["items"]}
        for item in committed["items"]:
            if item["resolved"] or item["next_action_source"] == AUTHORED_HERE:
                continue
            key = item["normalized_name"]
            if item["next_action_source"] == "cleveland_work_browser_pass_001":
                assert item["next_action"] == wb[key]
            else:
                assert item["next_action"] == un[key]
                assert key not in wb, "%s was reviewed; use that action" % key

    def test_the_governing_source_is_the_most_recent_examiner(self, committed):
        """Recency of EXAMINATION, not a preference between files. The rows the
        2026-08-12 pass reviewed take its action over the 08-11 manifest's, and
        the ones it never reached keep the manifest's."""
        reviewed = {i["normalized_name"] for i in _json(WORK_BROWSER_PATH)["items"]}
        for item in committed["items"]:
            if item["resolved"] or item["next_action_source"] == AUTHORED_HERE:
                continue
            expected = ("cleveland_work_browser_pass_001"
                        if item["normalized_name"] in reviewed
                        else "cleveland_unresolved_manifest")
            assert item["next_action_source"] == expected, item["normalized_name"]

    def test_exactly_one_action_is_authored_by_this_work_order(self, committed):
        """The exception, and the reason it has to exist: 001 wrote a POLICY
        action for Hyatt Place Westlake because it adjudicated the row's policy
        and never saw its routing proposal. Carrying that forward would point a
        routing-blocked identity at a capture of a bot-walled brand."""
        authored = [i for i in committed["items"]
                    if i["next_action_source"] == AUTHORED_HERE]
        assert len(authored) == 1
        item = authored[0]
        assert item["slug"] == "hyatt-place-cleveland-westlake-crocker-park"
        assert item["final_state"] == AWAITING_ROUTING_REVIEW
        assert "screenshot" in item["next_action"].lower()
        assert "must not be automated" in item["next_action"]

    def test_the_authored_action_replaced_a_mismatched_one(self, committed):
        """Proof the exception is load-bearing rather than decorative: the
        action it replaced is still in 001's ledger and still speaks about a
        policy capture, not about routing."""
        wb = {i["slug"]: i["next_action"] for i in _json(WORK_BROWSER_PATH)["items"]}
        carried = wb["hyatt-place-cleveland-westlake-crocker-park"]
        assert "pet-policy block" in carried
        item = next(i for i in committed["items"]
                    if i["slug"] == "hyatt-place-cleveland-westlake-crocker-park")
        assert item["next_action"] != carried


class TestNothingPublishedFromATranscription:

    def test_no_work_browser_row_reached_a_terminal_state(self, committed):
        """The package is a transcription with no artifact of any source
        surface. 001 published nothing from it and 002 publishes nothing from
        it; every one of the 135 is still unresolved."""
        reviewed = [i for i in committed["items"]
                    if i["reviewed_in_work_browser_pass_001"]]
        assert len(reviewed) == 135
        assert not [i for i in reviewed if i["resolved"]]

    def test_the_fifteen_transcribed_refusals_are_not_exclusions(self, committed):
        """Fifteen rows the input counted as 'policy visible' state pets are NOT
        allowed. A refusal is guarded at the same bar as a permission, so none
        of them became a VERIFIED_NO_PETS record on typed prose."""
        negative = [i for i in committed["items"]
                    if i["work_browser_reason_code"]
                    == "NEGATIVE_POLICY_TRANSCRIBED_NO_ARTIFACT"]
        assert len(negative) == 15
        assert {i["final_state"] for i in negative} == {AWAITING_POLICY_ARTIFACT}

    def test_the_evidence_determination_is_recorded_not_assumed(self, committed):
        det = committed["evidence_determination"]
        assert det["publishable_without_a_page_artifact"] is False
        assert det["work_browser_package_artifact_class"] == (
            "OPERATOR_TRANSCRIBED_BROWSER_REVIEW")

    def test_no_screenshot_is_claimed_without_image_bytes(self, committed):
        """Image BYTES, never a directory count -- all 135 screenshot
        directories exist and all 135 are empty, and an empty directory is not
        an artifact. Skipped rather than assumed where the tree is absent: this
        must never be able to report zero because it could not look."""
        if not SCREENSHOT_DIR.exists():
            pytest.skip("operator screenshot tree is gitignored and absent here")
        census = committed["evidence_determination"]["screenshot_census"]
        assert census["scanned"] is True
        assert census["image_files"] == 0, (
            "image bytes appeared: the partition must be rebuilt, because a "
            "transcription-only determination no longer describes this package")


class TestTheAuthoritiesAgree:

    def test_the_unresolved_manifest_matches_routing_on_every_url(self, committed):
        """The defect this work order fixed. 6f9ba1d corrected Sonesta ES Suites
        Cleveland Airport to the Simply Suites path in identity_routing.json and
        the manifest -- which the release contract calls this market's
        reconciliation of record -- kept the dead ES Suites URL."""
        drift = committed["authority_agreement"][
            "unresolved_manifest_vs_identity_routing_url_drift"]
        assert drift == []

    def test_the_sonesta_correction_reached_both_files(self):
        routes = {r["hotel_ref"]["normalized_name"]: r
                  for r in _json(ROUTING_PATH)["routes"]
                  if r.get("market_id") == MARKET}
        key = "sonesta es suites cleveland airport"
        routed = routes[key]["official_property_url"]
        assert "sonesta-simply-suites" in routed
        item = next(i for i in _json(UNRESOLVED_PATH)["items"]
                    if i["normalized_name"] == key)
        assert item["official_url"] == routed
        # The rebrand corrected a URL, not an identity or a state.
        assert item["canonical_name"] == "Sonesta ES Suites Cleveland Airport"
        assert item["classification"] == "ADAPTER_GAP_INDEPENDENT"

    def test_the_partition_url_is_the_routing_url(self, committed):
        """One place to read where a property's page is."""
        routes = {r["hotel_ref"]["normalized_name"]: r["official_property_url"]
                  for r in _json(ROUTING_PATH)["routes"]
                  if r.get("market_id") == MARKET}
        for item in committed["items"]:
            key = item["normalized_name"]
            assert item["official_url"] == routes.get(key, ""), key

    def test_the_manifest_counts_did_not_move(self):
        doc = _json(UNRESOLVED_PATH)
        assert (doc["confirmed_identities"], doc["resolved"],
                doc["published_pet_friendly"], doc["verified_no_pets"],
                doc["unresolved"]) == (188, 29, 21, 8, 159)
        assert len(doc["items"]) == 159


class TestCollisionAudits:

    def test_no_url_binds_two_identities_anywhere(self, committed):
        assert committed["collision_audit"]["url_reuse"] == {}

    def test_no_property_code_binds_two_identities_within_one_domain(self, committed):
        assert committed["collision_audit"][
            "property_code_reuse_within_domain"] == {}

    def test_a_code_shared_across_two_BRANDS_is_still_allowed(self, committed):
        """PTF-CLEVELAND-MARKET-FACTORY-001: cakfl is Holiday Inn Express Akron
        NW Fairlawn on ihg.com and Residence Inn Akron Fairlawn on
        marriott.com. Both extractions are right. A globally-scoped audit calls
        that corruption and refuses to load the authority."""
        shared = committed["collision_audit"]["property_codes_shared_across_domains"]
        assert "cakfl" in shared
        assert len(shared["cakfl"]) == 2

    def test_the_audit_is_recomputed_not_copied(self):
        assert collision_audit(_json(ROUTING_PATH)["routes"])["url_reuse"] == {}

    def test_no_other_market_leaks_into_the_partition(self, committed):
        """Columbus is frozen and Dayton is complete. Neither may appear here,
        and Cincinnati is a separate research lane this work order never reads."""
        census = {h["normalized_name"] for h in _json(CENSUS_PATH)["hotels"]}
        assert {i["normalized_name"] for i in committed["items"]} == census
        routes = _json(ROUTING_PATH)["routes"]
        foreign = {r["hotel_ref"]["normalized_name"] for r in routes
                   if r.get("market_id") != MARKET}
        assert foreign & census == set()


class TestTheSixteenthRoutingProposal:
    """The package's manifest counts routing proposals by CLASSIFICATION and
    reports fourteen (+1 in batch 2). Sixteen rows carry a populated proposed
    replacement URL. The sixteenth was never adjudicated."""

    def test_the_counts_are_recorded_honestly(self, committed):
        prop = committed["routing_proposals_in_package"]
        assert prop["rows_carrying_a_proposed_replacement_url"] == 16
        assert prop["adjudicated_by_001"] == 15
        assert prop["accepted_by_001"] == 1 and prop["rejected_by_001"] == 14
        assert prop["missed_by_001_and_held_here"] == 1
        assert prop["accepted_by_002"] == 0

    def test_the_hyatt_proposal_is_held_not_accepted(self, committed):
        item = next(i for i in committed["items"]
                    if i["slug"] == "hyatt-place-cleveland-westlake-crocker-park")
        assert item["final_state"] == AWAITING_ROUTING_REVIEW
        assert not item["resolved"]
        assert "clezc" in item["state_override_reason"]

    def test_routing_authority_was_not_changed_for_it(self):
        """A held proposal writes no routing record. The record still routes to
        the CVB-supplied vanity domain, and hyatt.com was never probed."""
        route = next(r for r in _json(ROUTING_PATH)["routes"]
                     if r["hotel_ref"]["normalized_name"]
                     == "hyatt place cleveland westlake crocker park")
        assert route["official_property_url"] == "https://hyattplaceclevelandwestlake.com"
        assert route["binding_method"] == "BRAND_INDEX_BINDING"

    def test_cleveland_routing_record_count_is_unchanged(self):
        routes = [r for r in _json(ROUTING_PATH)["routes"]
                  if r.get("market_id") == MARKET]
        assert len(routes) == 145


class TestTheCrosswalkIsAuditable:

    def test_every_reviewed_item_keeps_its_upstream_outcome(self, committed):
        wb = {i["normalized_name"]: i for i in _json(WORK_BROWSER_PATH)["items"]}
        for item in committed["items"]:
            if not item["reviewed_in_work_browser_pass_001"]:
                continue
            src = wb[item["normalized_name"]]
            assert item["work_browser_outcome"] == src["outcome"]
            assert item["work_browser_reason_code"] == src["reason_code"]

    def test_the_crosswalk_accounts_for_all_135_reviewed_rows(self, committed):
        crosswalk = committed["crosswalk_from_pass_001_outcomes"]
        assert sum(r["rows"] for r in crosswalk.values()) == 135
        for outcome, row in crosswalk.items():
            assert sum(row["final_states"].values()) == row["rows"], outcome

    def test_the_crosswalk_agrees_with_the_upstream_ledger_row_counts(self, committed):
        """Derived from the items, so it cannot drift from them -- but it must
        also match what 001 itself counted."""
        upstream = {}
        for item in _json(WORK_BROWSER_PATH)["items"]:
            upstream[item["outcome"]] = upstream.get(item["outcome"], 0) + 1
        crosswalk = committed["crosswalk_from_pass_001_outcomes"]
        assert {o: r["rows"] for o, r in crosswalk.items()} == upstream

    def test_every_outcome_that_splits_carries_a_recorded_reason(self, committed):
        """A bucket that lands on more than one blocker is a divergence from
        001, and a divergence with no stated reason is an unexplained one."""
        split = {o: r for o, r in committed["crosswalk_from_pass_001_outcomes"].items()
                 if r["splits"]}
        assert split, "the crosswalk is expected to split at least one bucket"
        for outcome, row in split.items():
            assert len(row["why"]) > 60, outcome

    def test_the_four_known_divergences_are_present(self, committed):
        crosswalk = committed["crosswalk_from_pass_001_outcomes"]
        assert {o for o, r in crosswalk.items() if r["splits"]} == {
            "ACCESS_BLOCKED", "MANUAL_VERIFICATION_REQUIRED", "OTHER_UNRESOLVED",
            "EVIDENCE_CANDIDATE_AWAITING_ACCEPTED_ARTIFACT"}
        # 001 filed four rows as ACCESS_BLOCKED; only one of them has no lawful
        # automated path -- the other three are waiting on a routing URL.
        blocked = crosswalk["ACCESS_BLOCKED"]
        assert blocked["rows"] == 4
        assert blocked["final_states"] == {ACCESS_BLOCKED: 1,
                                          AWAITING_ROUTING_REPLACEMENT: 3}

    def test_a_per_slug_override_always_carries_its_reason(self, committed):
        overridden = [i for i in committed["items"] if i["state_override_reason"]]
        assert len(overridden) == 12
        assert all(len(i["state_override_reason"]) > 40 for i in overridden)

    def test_the_blocker_distribution_is_what_the_evidence_supports(self, committed):
        counts = committed["final_state_counts"]
        assert counts[AWAITING_POLICY_ARTIFACT] == 70
        assert counts[AWAITING_POLICY_OBSERVATION] == 30
        assert counts[AWAITING_ATTENDED_CAPTURE] == 14
        assert counts[AWAITING_ROUTING_REPLACEMENT] == 13
        assert counts[AWAITING_ROUTING_REVIEW] == 1
        assert counts[AWAITING_OFFICIAL_URL] == 15
        assert counts[AWAITING_PROPERTY_LEVEL_URL] == 8
        assert counts[AWAITING_CONTRADICTION_RESOLUTION] == 3
        assert counts[AWAITING_CENSUS_REVIEW] == 3
        assert counts[ACCESS_BLOCKED] == 2

    def test_access_blocked_means_no_lawful_automated_path(self, committed):
        """Not 'a page failed to load'. Two identities qualify: an anti-bot
        challenge on the property's own site, and Hyatt Place Canton behind
        Kasada, which ADR-PTF-AUTOMATED-BROWSING forbids automating."""
        blocked = [i for i in committed["items"]
                   if i["final_state"] == ACCESS_BLOCKED]
        assert {i["slug"] for i in blocked} == {"aurora-inn", "hyatt-place-canton"}

    def test_the_twentyfour_never_reviewed_keep_manifest_classifications(
            self, committed):
        never = [i for i in committed["items"]
                 if not i["resolved"] and not i["reviewed_in_work_browser_pass_001"]]
        assert len(never) == 24
        assert committed["reconciliation"][
            "never_reviewed_by_any_browser_pass"] == 24
        assert {i["final_state"] for i in never} == {
            AWAITING_OFFICIAL_URL, AWAITING_PROPERTY_LEVEL_URL, ACCESS_BLOCKED}

    def test_a_contradiction_is_preserved_and_never_smoothed(self, committed):
        """Courtyard Akron Stow is classified HTTP_404 by the input while
        transcribing a fully rendered Marriott page. Preferring either half
        would invent a fact."""
        item = next(i for i in committed["items"]
                    if i["slug"] == "courtyard-by-marriott-akron-stow")
        assert item["final_state"] == AWAITING_CONTRADICTION_RESOLUTION
        assert item["work_browser_reason_code"] == "CLASSIFICATION_CONTRADICTS_TRANSCRIPTION"
