# -*- coding: utf-8 -*-
"""PTF-GENERIC-EXACT-AUTHORIZED-COHORT-001 -- an authorisation is an allowlist, not a quota.

Indianapolis authorised 51 identities at a cap costed over those 51, and the
runner correctly derived an eligible queue of 74. The 23 extra were real work
nobody had priced. Spending anyway would have bought a set nobody costed and
chosen the losers by queue order.

The rule these tests protect is one sentence: if an authorised row turns out to
be unpayable, the run gets SMALLER. It never reaches into the backlog for a
replacement, because a budget approved for 51 named hotels is not a budget for
any 51 hotels.
"""
from __future__ import annotations

import json

import pytest

from scripts.pettripfinder.acquisition import authorized_cohort as AUTH
from scripts.pettripfinder.acquisition import cohort_cost_plan as CP
from scripts.pettripfinder.acquisition import paid_attempt_ledger as PAL

MARKET = "indianapolis-in"


def row(key, provider="brightdata_browser", url="", phone="", postal="46204"):
    return {"identity_key": key, "canonical_name": key.title(),
            "source_url": url or "https://www.example-hotel.com/%s" % key.replace(" ", "-"),
            "provider": provider, "brand": "INDEP:example-hotel.com",
            "family": "INDEPENDENT", "street": "1 Test Street",
            "postal_code": postal, "telephone": phone}


def queue_of(n_auth=51, n_backlog=23):
    authorised = [row("authorised hotel %02d" % i) for i in range(n_auth)]
    backlog = [row("backlog hotel %02d" % i) for i in range(n_backlog)]
    return authorised, backlog, authorised + backlog


def authorization(keys, *, market=MARKET, cap=700, credits=20, **kw):
    return AUTH.build(keys, market_id=market, work_order="WO-012",
                      run_id="run-012", cap_usd_minor=cap,
                      plan_credit_cap=credits, **kw)


class TestOnlyTheAuthorizedCanSpend:

    def test_a_74_row_queue_and_a_51_row_authorization_spend_51(self):
        """1. The failure this whole module exists for."""
        authorised, _backlog, queue = queue_of()
        assert len(queue) == 74
        doc = authorization([r["identity_key"] for r in authorised])
        payable, report = AUTH.gate(queue, doc, market_id=MARKET,
                                    cap_usd_minor=700, plan_credit_cap=20)
        assert len(payable) == 51
        assert report["unauthorized_backlog"] == 23

    def test_not_one_backlog_identity_can_enter(self):
        """2."""
        authorised, backlog, queue = queue_of()
        doc = authorization([r["identity_key"] for r in authorised])
        payable, _report = AUTH.gate(queue, doc, market_id=MARKET)
        chosen = {r["identity_key"] for r in payable}
        assert chosen & {r["identity_key"] for r in backlog} == set()
        assert chosen == {r["identity_key"] for r in authorised}

    def test_the_backlog_is_named_not_silently_dropped(self):
        """13. Coverage has to be able to tell "nobody approved this" from
        "the budget ran out"."""
        authorised, _backlog, queue = queue_of()
        doc = authorization([r["identity_key"] for r in authorised])
        _payable, report = AUTH.gate(queue, doc, market_id=MARKET)
        assert len(report["backlog_rows"]) == 23
        for entry in report["backlog_rows"]:
            assert entry["state"] == AUTH.NOT_AUTHORIZED
            assert "its own cost plan" in entry["why"]


class TestAnAllowlistIsNotAQuota:

    def test_a_suppressed_authorized_row_shrinks_the_run(self):
        """3. And no replacement is promoted."""
        authorised, backlog, queue = queue_of()
        doc = authorization([r["identity_key"] for r in authorised])
        settled = authorised[0]
        ledger = PAL.merge(PAL.new_ledger(), [PAL.build_attempt(
            dict(settled, outcome="VALID", providers_tried=["brightdata_browser"],
                 final_state="ACQUIRED_PUBLICATION_GRADE", publication_grade=True),
            market_id=MARKET, work_order="WO-EARLIER", run_id="earlier")])
        payable, report = AUTH.gate(queue, doc, market_id=MARKET, ledger=ledger)
        assert len(payable) == 50
        assert report["suppressed_by_paid_history"] == 1
        chosen = {r["identity_key"] for r in payable}
        assert chosen & {r["identity_key"] for r in backlog} == set()
        assert "SHRINKS this run" in report["no_substitution"]

    def test_an_authorized_identity_the_runner_no_longer_offers_is_reported(self):
        authorised, _backlog, queue = queue_of()
        keys = [r["identity_key"] for r in authorised] + ["a hotel long settled"]
        doc = authorization(keys)
        payable, report = AUTH.gate(queue, doc, market_id=MARKET)
        assert len(payable) == 51
        assert report["authorised_but_not_eligible"] == ["a hotel long settled"]

    def test_an_unknown_identity_in_the_allowlist_cannot_spend(self):
        """8."""
        _authorised, _backlog, queue = queue_of(n_auth=2, n_backlog=1)
        doc = authorization(["authorised hotel 00", "a hotel that does not exist"])
        payable, report = AUTH.gate(queue, doc, market_id=MARKET)
        assert {r["identity_key"] for r in payable} == {"authorised hotel 00"}
        assert "a hotel that does not exist" in report["authorised_but_not_eligible"]


class TestAStaleOrWrongAuthorizationStopsBeforeSpend:

    def test_a_mismatched_fingerprint_stops(self):
        """5."""
        authorised, _b, queue = queue_of(n_auth=3, n_backlog=1)
        doc = authorization([r["identity_key"] for r in authorised])
        doc["identity_keys"] = doc["identity_keys"] + ["smuggled in later"]
        with pytest.raises(AUTH.AuthorizedCohortError) as excinfo:
            AUTH.gate(queue, doc, market_id=MARKET)
        assert "fingerprint_matches_its_own_keys" in str(excinfo.value)

    def test_a_wrong_market_stops(self):
        """6."""
        authorised, _b, queue = queue_of(n_auth=3, n_backlog=1)
        doc = authorization([r["identity_key"] for r in authorised],
                            market="louisville-ky")
        with pytest.raises(AUTH.AuthorizedCohortError) as excinfo:
            AUTH.gate(queue, doc, market_id=MARKET)
        assert "market_matches_the_run" in str(excinfo.value)

    def test_a_duplicate_identity_is_rejected_at_build_time(self):
        """7."""
        with pytest.raises(AUTH.AuthorizedCohortError) as excinfo:
            authorization(["one hotel", "one hotel"])
        assert "same identity twice" in str(excinfo.value)

    def test_a_duplicate_smuggled_into_a_document_is_rejected_at_the_gate(self):
        authorised, _b, queue = queue_of(n_auth=2, n_backlog=1)
        doc = authorization([r["identity_key"] for r in authorised])
        doc["identity_keys"] = ["authorised hotel 00", "authorised hotel 00"]
        doc["cohort_count"] = 2
        doc["cohort_keys_sha256"] = AUTH.fingerprint(doc["identity_keys"])
        with pytest.raises(AUTH.AuthorizedCohortError) as excinfo:
            AUTH.gate(queue, doc, market_id=MARKET)
        assert "no_duplicate_identity" in str(excinfo.value)

    def test_a_declared_count_that_lies_stops(self):
        authorised, _b, queue = queue_of(n_auth=3, n_backlog=1)
        doc = authorization([r["identity_key"] for r in authorised])
        doc["cohort_count"] = 99
        with pytest.raises(AUTH.AuthorizedCohortError):
            AUTH.gate(queue, doc, market_id=MARKET)

    def test_an_empty_allowlist_is_refused_rather_than_run(self):
        with pytest.raises(AUTH.AuthorizedCohortError):
            authorization([])


class TestTheCapsRemainCeilings:

    def test_a_run_cap_above_the_authorized_cap_stops(self):
        """11."""
        authorised, _b, queue = queue_of(n_auth=3, n_backlog=1)
        doc = authorization([r["identity_key"] for r in authorised], cap=700)
        with pytest.raises(AUTH.AuthorizedCohortError) as excinfo:
            AUTH.gate(queue, doc, market_id=MARKET, cap_usd_minor=900)
        assert "run_cap_within_the_authorised_cap" in str(excinfo.value)

    def test_a_run_cap_below_the_authorized_cap_is_allowed(self):
        authorised, _b, queue = queue_of(n_auth=3, n_backlog=1)
        doc = authorization([r["identity_key"] for r in authorised], cap=700)
        payable, _report = AUTH.gate(queue, doc, market_id=MARKET,
                                     cap_usd_minor=500)
        assert len(payable) == 3

    def test_a_credit_cap_above_the_authorized_one_stops(self):
        """12."""
        authorised, _b, queue = queue_of(n_auth=3, n_backlog=1)
        doc = authorization([r["identity_key"] for r in authorised], credits=20)
        with pytest.raises(AUTH.AuthorizedCohortError) as excinfo:
            AUTH.gate(queue, doc, market_id=MARKET, cap_usd_minor=700,
                      plan_credit_cap=40)
        assert "run_credit_cap_within_the_authorised_cap" in str(excinfo.value)


class TestTheCostPlanIsPricedOverWhatWillActuallyBeBought:

    def test_the_fingerprint_is_recomputed_over_the_payable_restricted_cohort(self):
        """4. Not over the authorisation, and not over the runner's queue."""
        authorised, _backlog, queue = queue_of()
        doc = authorization([r["identity_key"] for r in authorised])
        settled = authorised[0]
        ledger = PAL.merge(PAL.new_ledger(), [PAL.build_attempt(
            dict(settled, outcome="VALID", providers_tried=["brightdata_browser"],
                 final_state="ACQUIRED_PUBLICATION_GRADE", publication_grade=True),
            market_id=MARKET, work_order="WO-EARLIER", run_id="earlier")])
        payable, report = AUTH.gate(queue, doc, market_id=MARKET, ledger=ledger)
        expected = CP.cohort_fingerprint([r["identity_key"] for r in payable])
        assert report["cohort_keys_sha256"] == expected
        assert report["cohort_keys_sha256"] != doc["cohort_keys_sha256"]
        assert report["cohort_keys_sha256"] != CP.cohort_fingerprint(
            [r["identity_key"] for r in queue])

    def test_the_two_fingerprint_functions_agree(self):
        keys = ["b hotel", "a hotel", "c hotel"]
        assert AUTH.fingerprint(keys) == CP.cohort_fingerprint(keys)


class TestTheRestrictionIsStableAndConfined:

    def test_it_survives_a_resume(self):
        """9. The same authorisation over the same queue restricts identically,
        so a killed run that restarts buys the same set."""
        authorised, _b, queue = queue_of()
        doc = authorization([r["identity_key"] for r in authorised])
        first, report_a = AUTH.gate(queue, doc, market_id=MARKET)
        second, report_b = AUTH.gate(queue, doc, market_id=MARKET)
        assert [r["identity_key"] for r in first] == \
            [r["identity_key"] for r in second]
        assert report_a["cohort_keys_sha256"] == report_b["cohort_keys_sha256"]

    def test_reordering_the_queue_does_not_change_the_authorized_set(self):
        authorised, _b, queue = queue_of()
        doc = authorization([r["identity_key"] for r in authorised])
        forward, _ = AUTH.gate(queue, doc, market_id=MARKET)
        backward, _ = AUTH.gate(list(reversed(queue)), doc, market_id=MARKET)
        assert {r["identity_key"] for r in forward} == \
            {r["identity_key"] for r in backward}

    def test_an_escalation_stays_inside_an_authorized_identity(self):
        """10. A cross-lane escalation is a second attempt on the SAME hotel.
        It can never introduce a key the allowlist does not carry."""
        authorised, _backlog, queue = queue_of()
        doc = authorization([r["identity_key"] for r in authorised])
        payable, _report = AUTH.gate(queue, doc, market_id=MARKET)
        escalated = [dict(r, provider="brightdata_web_unlocker") for r in payable]
        again, report = AUTH.gate(escalated, doc, market_id=MARKET)
        assert len(again) == len(payable)
        assert report["unauthorized_backlog"] == 0
        assert {r["identity_key"] for r in again} <= set(doc["identity_keys"])


class TestLegacyRunsAreUnaffected:

    def test_no_authorization_means_the_old_behaviour(self):
        """14. The flag is opt-in; a run without one is the run this codebase
        has always made."""
        import inspect
        from scripts.pettripfinder.acquisition import market_paid_acquisition as MPA
        source = inspect.getsource(MPA.main)
        assert 'if args.only_cohort:' in source
        assert 'authorized_report: Dict = OrderedDict((("only_cohort", ""),))' in source

    def test_the_flag_and_its_ledger_companion_exist(self):
        import inspect
        from scripts.pettripfinder.acquisition import market_paid_acquisition as MPA
        source = inspect.getsource(MPA.main)
        assert '"--only-cohort"' in source
        assert '"--paid-ledger"' in source


class TestTheArtifactBindsWhatItMustBind:

    def test_it_carries_every_required_field(self):
        doc = authorization(["a hotel", "b hotel"],
                            cost_plan_path="plan.json",
                            cost_plan_fingerprint="deadbeef",
                            generated_at="2026-08-27T00:00:00Z",
                            provenance={"derived_from": "012 cost plan"})
        for field in ("schema", "market_id", "work_order", "run_id",
                      "authorization", "cost_plan", "cohort_count",
                      "identity_keys", "cohort_keys_sha256", "generated_at",
                      "provenance"):
            assert field in doc, field
        assert doc["authorization"]["cap_usd_minor"] == 700
        assert doc["authorization"]["plan_credit_cap"] == 20
        assert doc["cost_plan"]["path"] == "plan.json"

    def test_the_keys_are_canonical_and_hashed(self):
        doc = authorization(["b hotel", "a hotel"])
        assert doc["identity_keys"] == ["a hotel", "b hotel"]
        assert doc["cohort_keys_sha256"] == AUTH.fingerprint(doc["identity_keys"])

    def test_load_refuses_a_document_of_another_schema(self, tmp_path):
        path = tmp_path / "not-an-authorization.json"
        path.write_text(json.dumps({"schema": "something-else"}), encoding="utf-8")
        with pytest.raises(AUTH.AuthorizedCohortError):
            AUTH.load(path)
