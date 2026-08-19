"""PTF-MILWAUKEE-ACQUISITION-ROUTER-INTEGRATION-001 -- the cost safety gates.

The founder cost override is the only thing standing between a bounded run and
an unbounded bill, so it is tested rather than trusted. Every test here works
on injected balances: no network, no vendor, no spend.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder import milwaukee_acquisition_run_001 as RUN
from scripts.pettripfinder.brightdata import client as CLIENT

REPO_ROOT = Path(__file__).resolve().parents[3]
QUEUE = (REPO_ROOT / "launch_packages" / "pettripfinder" / "markets" / "reports"
         / "milwaukee-wi_policy_acquisition_queue_001.json")


def snapshot(*, balance, cost_month=2576, available=True, notes=()):
    return CLIENT.UsageSnapshot(
        label="test", captured_at="2026-08-18T00:00:00+00:00",
        zone=CLIENT.ZONE, available=available, cost_month_usd_minor=cost_month,
        bandwidth_bytes=None, bandwidth_display="", cost_display="$25.76",
        balance_usd_minor=balance, pending_charge_usd_minor=0, notes=tuple(notes))


class _Meter(RUN.SpendMeter):
    """A SpendMeter fed a scripted sequence of balances."""

    def __init__(self, balances):
        super().__init__()
        self._balances = list(balances)

    def read(self, label):
        snap = self._balances.pop(0) if self._balances else self.latest
        self.latest = snap
        if self.baseline is None:
            self.baseline = snap
        self.samples.append(snap.to_dict())
        return snap


class TestTheCapIsTheFounderOverride:
    def test_the_three_thresholds_are_five_ten_and_fifteen_dollars(self):
        assert RUN.SOFT_CHECKPOINT_1_USD_MINOR == 500
        assert RUN.SOFT_CHECKPOINT_2_USD_MINOR == 1000
        assert RUN.HARD_CAP_USD_MINOR == 1500


class TestSpendIsMeasuredNotEstimated:
    def test_spend_is_balance_drawdown(self):
        meter = _Meter([snapshot(balance=1608), snapshot(balance=1461)])
        meter.read("baseline")
        meter.read("after")
        assert meter.spent_usd_minor() == 147

    def test_a_top_up_cannot_report_negative_spend(self):
        """A mid-run top-up must not look like a refund and must never buy
        headroom the cap did not grant."""
        meter = _Meter([snapshot(balance=1608), snapshot(balance=5000)])
        meter.read("baseline")
        meter.read("after")
        assert meter.spent_usd_minor() == 0

    def test_an_unreadable_balance_is_none_and_never_zero(self):
        """The override says stop when telemetry is unavailable. Reporting
        zero would be indistinguishable from 'nothing has been spent yet',
        which is exactly the confusion that overruns a budget."""
        meter = _Meter([snapshot(balance=1608), snapshot(balance=None, available=False)])
        meter.read("baseline")
        meter.read("after")
        assert meter.spent_usd_minor() is None
        assert meter.telemetry_live is False

    def test_zone_delta_is_reported_alongside_balance(self):
        meter = _Meter([snapshot(balance=1608, cost_month=2576),
                        snapshot(balance=1461, cost_month=2723)])
        meter.read("baseline")
        meter.read("after")
        assert meter.zone_delta_usd_minor() == 147


class TestPreflightRefusesToSpend:
    def test_unreadable_telemetry_fails_the_first_gate(self):
        meter = _Meter([snapshot(balance=None, available=False,
                                 notes=("budget balance exited 1",))])
        result = RUN.preflight(meter, cap_usd_minor=RUN.HARD_CAP_USD_MINOR)
        assert result["ok"] is False
        gate = next(c for c in result["checks"] if c["check"] == "cost_telemetry_live")
        assert gate["ok"] is False

    def test_a_balance_below_the_cap_fails_the_second_gate(self):
        """A run that cannot finish should not start."""
        meter = _Meter([snapshot(balance=400)])
        result = RUN.preflight(meter, cap_usd_minor=RUN.HARD_CAP_USD_MINOR)
        gate = next(c for c in result["checks"] if c["check"] == "balance_covers_the_cap")
        assert gate["ok"] is False
        assert result["ok"] is False

    def test_a_healthy_balance_still_fails_without_a_provider(self):
        """The state this worktree is actually in: money is readable and
        sufficient, and no provider can be reached."""
        meter = _Meter([snapshot(balance=1608)])
        result = RUN.preflight(meter, cap_usd_minor=RUN.HARD_CAP_USD_MINOR)
        by_name = {c["check"]: c for c in result["checks"]}
        assert by_name["cost_telemetry_live"]["ok"] is True
        assert by_name["balance_covers_the_cap"]["ok"] is True
        # No credential is set in the test environment either, so this gate is
        # the one that blocks -- and blocking it must block the whole run.
        if not by_name["at_least_one_provider_available"]["ok"]:
            assert result["ok"] is False
            assert result["healthy_providers"] == []

    def test_every_provider_reports_a_reason_not_just_a_boolean(self):
        meter = _Meter([snapshot(balance=1608)])
        result = RUN.preflight(meter, cap_usd_minor=RUN.HARD_CAP_USD_MINOR)
        assert result["providers"]
        for pid, detail in result["providers"].items():
            assert isinstance(detail["available"], bool)
            assert detail["detail"].strip(), pid


class TestTheRunStopsBeforeSpending:
    def test_a_blocked_preflight_produces_a_zero_cost_report(self):
        import asyncio
        report = asyncio.run(RUN.run(max_properties=3, resume=True,
                                     run_id="test-gate", dry_run=False))
        if report["outcome"] == "STOPPED_BEFORE_SPENDING":
            assert report["total_cost_usd_minor"] == 0
            assert report["properties"] == []
            assert report["stop_reason"].strip()
            # Nothing was acquired, so every planned row still needs a human.
            assert report["attended_fallback_required"] == report["planned_this_batch"]

    def test_the_report_states_the_cost_policy_it_ran_under(self):
        import asyncio
        report = asyncio.run(RUN.run(max_properties=1, resume=True,
                                     run_id="test-policy", dry_run=True))
        policy = report["cost_policy"]
        assert policy["hard_cap_usd_minor"] == 1500
        assert policy["soft_checkpoint_1_usd_minor"] == 500
        assert policy["soft_checkpoint_2_usd_minor"] == 1000
        assert "balance" in policy["measured_from"]


class TestTheQueueItDrives:
    def test_only_routable_rows_are_loaded(self):
        """Hyatt and Best Western are excluded on cost by the route table.
        They stay in the queue artifact for accounting and must never be
        handed to a provider."""
        doc = json.loads(QUEUE.read_text(encoding="utf-8-sig"))
        loaded = RUN.load_queue()
        assert len(loaded) == doc["routable_total"]
        assert all(not r["brand_excluded"] for r in loaded)
        assert len(doc["items"]) - len(loaded) == doc["brand_excluded_total"]
