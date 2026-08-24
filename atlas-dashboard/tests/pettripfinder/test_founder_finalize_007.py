"""PTF-ST-LOUIS-FOUNDER-FINALIZE-007 -- a second signature pass over one market.

The property that matters here is that a market's signature ACCUMULATES without
ever duplicating. Each pass signs its own delta, earlier ledgers are carried
rather than rewritten, and the authority is built from their union. Getting that
wrong in either direction is silent: sign the union again and one attestation
becomes two dated acts over the same row; build from the newest ledger alone and
every row signed before it disappears from the authority.
"""

from __future__ import annotations

import json

import pytest

from scripts.pettripfinder import market_founder_signature_cli as SIG
from scripts.pettripfinder import market_proposed_authority_cli as AUTH
from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts import founder_approval as FA

PKG = "launch_packages/pettripfinder/"


def _load(name):
    with open(PKG + name, encoding="utf-8") as handle:
        return json.load(handle)


def candidate(key):
    return {"identity_key": key, "canonical_name": key.title(), "brand": "B",
            "corridor": "c", "source_url": "https://x/y", "snapshot_hash": "s",
            "founder_decision": "", "founder_reviewer_id": "",
            "founder_reviewed_at": "",
            "semantic_approval": {"semantic_hash": "sha256:" + key}}


def reviewed(key, disposition="APPROVE_PET_FRIENDLY"):
    return {"identity_key": key, "proposed_disposition": disposition,
            "next_action": "", "required_changes": []}


def run(candidates, rows, already=()):
    return SIG.sign({"candidates": candidates, "market_id": "m"},
                    {"rows": rows}, decided_by="f", decided_at="d",
                    authorization="a", work_order="WO",
                    recorded_by="agent", already_signed=already)


class TestTheDeltaOnly:
    def test_a_row_an_earlier_ledger_signed_is_carried_not_re_signed(self):
        earlier = {"work_order": "WO-1", "signed": [
            {"identity_key": "a", "founder_reviewed_at": "d1",
             "proposes_authority": enums.PUBLISHED_PET_FRIENDLY}]}
        ledger = run([candidate("a"), candidate("b")],
                     [reviewed("a"), reviewed("b")], already=[earlier])
        assert [r["identity_key"] for r in ledger["signed"]] == ["b"]
        assert ledger["already_signed_elsewhere"] == 1
        assert ledger["already_signed_rows"][0]["signed_by_work_order"] == "WO-1"

    def test_the_market_total_is_the_union(self):
        earlier = {"work_order": "WO-1", "signed": [{"identity_key": "a"}]}
        ledger = run([candidate("a"), candidate("b")],
                     [reviewed("a"), reviewed("b")], already=[earlier])
        assert ledger["signed_count"] == 1
        assert ledger["market_signature_total"] == 2

    def test_with_no_earlier_ledger_everything_clean_is_signed(self):
        ledger = run([candidate("a")], [reviewed("a")])
        assert ledger["signed_count"] == 1
        assert ledger["already_signed_elsewhere"] == 0

    def test_a_carried_row_is_not_reported_as_withheld(self):
        earlier = {"work_order": "WO-1", "signed": [{"identity_key": "a"}]}
        ledger = run([candidate("a")], [reviewed("a")], already=[earlier])
        assert ledger["withheld"] == []
        assert ledger["signed"] == []

    def test_a_held_row_is_still_never_signed_on_a_later_pass(self):
        ledger = run([candidate("a")], [reviewed("a", "HOLD")])
        assert ledger["signed"] == []
        assert ledger["withheld_count"] == 1


class TestAuthorityFromManyLedgers:
    def _store(self, *keys):
        return {"records": [{"identity_key": k, "observation": {
            "snapshot_hash": "", "evidence": [{"quote": "q"}]}} for k in keys]}

    def _ledger(self, work_order, *keys):
        return {"market_id": "m", "work_order": work_order, "signed": [
            {"identity_key": k, "canonical_name": k, "corridor": "c",
             "founder_decision": FA.CANONICAL_APPROVED,
             "founder_reviewer_id": "f", "founder_reviewed_at": "d",
             "proposes_authority": enums.PUBLISHED_PET_FRIENDLY,
             "bound_semantic_hash": "", "bound_snapshot_hash": ""}
            for k in keys]}

    def test_authority_is_the_union_of_every_ledger(self):
        built = AUTH.build([self._ledger("WO-1", "a", "b"),
                            self._ledger("WO-2", "c")],
                           self._store("a", "b", "c"), {"hotels": []})
        assert built["authority_total"] == 3
        assert built["built_from"]["source_ledgers"] == ["WO-1", "WO-2"]

    def test_a_single_ledger_still_works_unchanged(self):
        built = AUTH.build(self._ledger("WO-1", "a"), self._store("a"),
                           {"hotels": []})
        assert built["authority_total"] == 1

    def test_two_ledgers_signing_one_row_is_refused(self):
        # An attestation is a dated act. Two of them over one row is either a
        # duplicate or a silent restatement under a new date.
        with pytest.raises(AUTH.ProposedAuthorityError):
            AUTH.build([self._ledger("WO-1", "a"), self._ledger("WO-2", "a")],
                       self._store("a"), {"hotels": []})


class TestTheCommittedFinalisation:
    def test_the_second_pass_signed_exactly_seven(self):
        ledger = _load("st_louis_mo_founder_decisions_007.json")
        assert ledger["signed_count"] == 7
        assert ledger["already_signed_elsewhere"] == 114
        assert ledger["market_signature_total"] == 121

    def test_the_two_ledgers_share_no_row(self):
        five = {r["identity_key"]
                for r in _load("st_louis_mo_founder_decisions_005.json")["signed"]}
        seven = {r["identity_key"]
                 for r in _load("st_louis_mo_founder_decisions_007.json")["signed"]}
        assert five & seven == set()
        assert len(five | seven) == 121

    def test_the_seven_are_the_six_plus_wingate(self):
        seven = {r["identity_key"]
                 for r in _load("st_louis_mo_founder_decisions_007.json")["signed"]}
        assert seven == {
            "comfort inn collinsville near st louis",
            "comfort inn pacific st louis",
            "hampton",
            "sonesta es suites st louis chesterfield",
            "super 8 by wyndham troy il st louis area",
            "travelodge st louis airport",
            "wingate at wyndham"}

    def test_the_final_authority_is_121_split_83_and_38(self):
        authority = _load("st_louis_mo_proposed_authority_007.json")
        assert authority["authority_total"] == 121
        assert authority["pet_friendly_count"] == 83
        assert authority["verified_no_pets_count"] == 38
        assert authority["unresolved"] == []

    def test_the_authority_is_exactly_the_union_of_both_ledgers(self):
        signed = set()
        for name in ("st_louis_mo_founder_decisions_005.json",
                     "st_louis_mo_founder_decisions_007.json"):
            signed |= {r["identity_key"] for r in _load(name)["signed"]}
        authority = _load("st_louis_mo_proposed_authority_007.json")
        built = ({r["normalized_name"] for r in authority["pet_friendly"]}
                 | {r["normalized_name"] for r in authority["verified_no_pets"]})
        assert built == signed

    def test_wingate_carries_its_corrected_name_and_its_adjudication(self):
        store = {r["identity_key"]: r
                 for r in _load("st_louis_mo_observation_store_007.json")["records"]}
        row = store["wingate at wyndham"]
        assert row["observation"]["hotel_ref"]["canonical_name"] == \
            "Wingate by Wyndham St. Louis/Fenton Route 66"
        # The census reading is kept beside it, never overwritten.
        assert row["census_canonical_name"] == "Wingate At Wyndham"
        adjudication = row["observation"]["identity_adjudication"]
        assert adjudication["approved_by"] == "jfields80"
        assert adjudication["signals_agreeing"] >= 2
        assert row["membrane"]["verdict"] == "VALID"

    def test_the_census_still_says_wingate_at_wyndham(self):
        census = _load("identity_census/st-louis-mo.json")
        names = {h["identity_key"]: h["canonical_name"] for h in census["hotels"]}
        assert names["wingate at wyndham"] == "Wingate At Wyndham"

    def test_every_name_correction_is_quoted_from_its_page(self):
        import html as _html

        overlay = _load("markets/name_corrections/st-louis-mo.json")
        analysis = _load("st_louis_mo_founder_review_analysis_007.json")
        # ``name_on_page`` is the raw page string, entities and all. What a
        # correction publishes is what a READER sees, so the comparison
        # unescapes -- and only unescapes: no other transformation is allowed,
        # which is what keeps "quoted from its page" a real constraint. Every
        # other IHG property in this market already publishes an unescaped "&".
        pages = {r["identity_key"]:
                 _html.unescape(r["identity_corroboration"]["name_on_page"])
                 for r in analysis["rows"]}
        # PTF-ST-LOUIS-REGISTER-PUBLISH-011 added the sixth: the Wentzville
        # Holiday Inn Express, whose bare census name collided with a LIVE
        # Cleveland identity. Same standing ruling, same evidence field.
        assert len(overlay["records"]) == 6
        for record in overlay["records"]:
            assert record["corrected_canonical_name"] == \
                pages[record["identity_key"]]

    def test_days_inn_is_the_only_row_left_and_is_still_refused(self):
        ledger = _load("st_louis_mo_founder_decisions_007.json")
        assert ledger["withheld_count"] == 1
        assert ledger["withheld"][0]["identity_key"] == \
            "days inn and suites pontoon beach"
        store = {r["identity_key"]: r
                 for r in _load("st_louis_mo_observation_store_007.json")["records"]}
        row = store["days inn and suites pontoon beach"]
        assert row["membrane"]["verdict"] == "REJECT_WRONG_PROPERTY"
        assert not row["observation"].get("identity_adjudication")

    def test_the_two_strong_signal_rule_was_not_weakened(self):
        # Days Inn has one agreeing signal and one contradicting one. The
        # overlay records it as refused, and no adjudication was written.
        overlay = _load("markets/founder_overrides/st-louis-mo.json")
        refused = overlay["identity_overrides"]["refused"]
        assert len(refused) == 1
        assert refused[0]["signals_agreeing"] == 1
        for approved in overlay["identity_overrides"]["records"]:
            assert approved["signals_agreeing"] >= 2

    def test_all_121_signatures_bind_to_the_current_records(self):
        packet = {c["identity_key"]: c
                  for c in _load("st_louis_mo_founder_review_packet_007.json")["candidates"]}
        for name in ("st_louis_mo_founder_decisions_005.json",
                     "st_louis_mo_founder_decisions_007.json"):
            for row in _load(name)["signed"]:
                current = packet[row["identity_key"]]["semantic_approval"]["semantic_hash"]
                assert current == row["bound_semantic_hash"], row["identity_key"]

    def test_no_packet_row_carries_an_attestation(self):
        packet = _load("st_louis_mo_founder_review_packet_007.json")
        for row in packet["candidates"]:
            assert row["founder_decision"] == ""
            assert row["founder_reviewer_id"] == ""
            assert row["founder_reviewed_at"] == ""

    def test_everything_reconciles_to_357(self):
        closure = _load("st_louis_mo_closure_ledger_007.json")
        assert closure["count"] == closure["active_denominator"] == 357
        assert closure["reconciliation"]["missing"] == []
        assert closure["reconciliation"]["foreign"] == []
        assert closure["reconciliation"]["duplicate"] == []
        assert closure["disposition_counts"]["HELD_REVIEW"] == 122  # 121 + 1

    def test_this_work_order_registered_nothing(self):
        """These work orders registered NOTHING, and that record stands.

        PTF-ST-LOUIS-REGISTER-PUBLISH-011 took the registration step, and did not
        go back and rewrite the ledgers that say a signature pass registered
        nothing -- doing so would erase the fact they record. Where the market
        stands NOW is read from the registry, which is the only thing that can
        answer it. What each of these signature ledgers asserted about ITSELF is
        what is checked here.
        """
        authority = _load("st_louis_mo_proposed_authority_007.json")
        assert authority["registered"] is False
        assert authority["published"] is False
        assert authority["deployed"] is False
