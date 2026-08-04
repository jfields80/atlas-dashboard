"""Ask any one brand less often, and never ask it a different way.

Hilton refused 11 candidates and Marriott 6 in a single 79-hotel batch, both
after a long unbroken run of requests to that one brand -- the queue sorts by
``(queue_priority, hotel_id)`` and hotel ids begin with the brand's own naming,
so the sort GROUPS brands. The real queue contained a run of eleven consecutive
IHG requests and a run of ten Hilton.

Two changes, and deliberately only two:

  * round-robin ordering, a pure function of the existing sort;
  * a per-brand minimum gap, drawn per request from 45-75s, which unrelated
    brands' work counts toward -- so an interleaved queue usually owes nothing
    and the wall clock barely moves.

What is NOT here, and what a test below asserts stays absent: proxy or IP
rotation, user-agent spoofing, CAPTCHA handling, cookie or session
manipulation, header forgery, brand-specific bypass. A block is a request to
stop. Pacing is complying more politely, not evading -- the challenge limit
stays at 3 and stays fail-closed.
"""

from __future__ import annotations

import json
import random

import pytest

from services.research_workers.capture_automation.doctrine import (
    CONSECUTIVE_CHALLENGE_LIMIT, SAME_BRAND_FLOOR_MAX_SECONDS,
    SAME_BRAND_FLOOR_MIN_SECONDS,
)
from services.research_workers.capture_automation.queue import (
    CaptureQueue, QueueEntry, round_robin_by_brand,
)
from services.research_workers.capture_automation.runner import (
    CaptureRunner, RunnerConfig,
)
from services.research_workers.capture_automation.state_machine import EXCEPTION

from .conftest import FakeBrowserSession, entry_for, load_fixture, pages_from

GOOD = "marriott-cmham.json"


def entry(hotel_id: str, brand: str, priority: int = 0) -> QueueEntry:
    return QueueEntry(hotel_id=hotel_id, listing_key=hotel_id, hotel_name=hotel_id,
                      brand=brand, official_url="https://www.%s.com/x/%s" % (brand, hotel_id),
                      queue_priority=priority)


def brands(entries):
    return [e.brand for e in entries]


# --------------------------------------------------------------------------- #
# 1-5. Ordering.
# --------------------------------------------------------------------------- #

class TestOrdering:
    def test_1_ordering_is_deterministic(self):
        es = [entry("h%02d" % i, ["hilton", "marriott", "ihg", "wyndham"][i % 4])
              for i in range(40)]
        first = round_robin_by_brand(es)
        for _ in range(5):
            shuffled = list(es)
            random.Random(7).shuffle(shuffled)
            assert [e.hotel_id for e in round_robin_by_brand(shuffled)] == \
                   [e.hotel_id for e in first], "input order must not matter"

    def test_2_within_brand_order_is_preserved(self):
        es = [entry("hilton-c", "hilton"), entry("marriott-a", "marriott"),
              entry("hilton-a", "hilton"), entry("hilton-b", "hilton")]
        out = round_robin_by_brand(es)
        hiltons = [e.hotel_id for e in out if e.brand == "hilton"]
        assert hiltons == ["hilton-a", "hilton-b", "hilton-c"], \
            "still (queue_priority, hotel_id) within a brand"

    def test_3_queue_priority_still_decides_within_a_brand(self):
        es = [entry("hilton-z", "hilton", priority=0),
              entry("hilton-a", "hilton", priority=9),
              entry("marriott-a", "marriott", priority=0)]
        out = round_robin_by_brand(es)
        hiltons = [e.hotel_id for e in out if e.brand == "hilton"]
        assert hiltons == ["hilton-z", "hilton-a"], "priority 0 before priority 9"

    def test_3b_priority_does_not_decide_which_brand_goes_first(self):
        """Bucket order is first appearance in the sorted input -- priority
        orders candidates, not brands. Stated because it is the one thing a
        reader might expect to change and must not."""
        es = [entry("aaa", "ihg", priority=0), entry("bbb", "hilton", priority=0)]
        assert brands(round_robin_by_brand(es)) == ["ihg", "hilton"]

    def test_4_output_matches_the_documented_algorithm(self):
        es = ([entry("h%d" % i, "hilton") for i in range(3)]
              + [entry("m%d" % i, "marriott") for i in range(3)]
              + [entry("i%d" % i, "ihg") for i in range(3)])
        out = [e.hotel_id for e in round_robin_by_brand(es)]
        assert out == ["h0", "i0", "m0", "h1", "i1", "m1", "h2", "i2", "m2"]

    def test_5_skewed_buckets_drain_correctly(self):
        """When the small buckets empty, the remainder is the tail of the big
        one. That is arithmetic, not a defect -- and it is what the same-brand
        floor exists to cover."""
        es = ([entry("h%02d" % i, "hilton") for i in range(5)]
              + [entry("w0", "wyndham")])
        out = brands(round_robin_by_brand(es))
        assert out == ["hilton", "wyndham", "hilton", "hilton", "hilton", "hilton"]

    def test_5b_no_candidate_is_lost_or_duplicated(self):
        es = [entry("h%02d" % i, ["hilton", "marriott", "ihg"][i % 3]) for i in range(31)]
        out = round_robin_by_brand(es)
        assert len(out) == len(es)
        assert {e.hotel_id for e in out} == {e.hotel_id for e in es}

    def test_5c_empty_and_single_inputs(self):
        assert round_robin_by_brand([]) == ()
        assert len(round_robin_by_brand([entry("a", "hilton")])) == 1

    def test_5d_it_shortens_same_brand_runs_on_the_real_queue(self):
        """The measurement that motivated this, against the real 79 entries."""
        import itertools
        import pathlib

        p = pathlib.Path("data/worker_runs/pettripfinder/capture_batches/"
                         "20260803T235532-remaining-batch-queue.json")
        if not p.exists():
            pytest.skip("the real batch queue is gitignored in this checkout")
        raw = json.loads(p.read_text("utf-8"))["hotels"]
        es = [entry(h["hotel_id"], h["brand"], h.get("queue_priority", 0)) for h in raw]
        longest = lambda seq: max(len(list(g)) for _, g in itertools.groupby(seq))
        before = longest(brands(sorted(es, key=lambda e: (e.queue_priority, e.hotel_id))))
        after = longest(brands(round_robin_by_brand(es)))
        assert before >= 10, before
        assert after <= 2, after


# --------------------------------------------------------------------------- #
# 6-8. The same-brand floor.
# --------------------------------------------------------------------------- #

class FakeClock:
    def __init__(self):
        self.t = 1_000.0

    def __call__(self):
        return self.t

    def advance(self, s):
        self.t += s


def runner_with(tmp_path, *, jitter=None, clock=None, sleep=None):
    clock = clock or FakeClock()
    slept = []

    def _sleep(s):
        slept.append(s)
        clock.advance(s)

    return CaptureRunner(FakeBrowserSession(pages_from(GOOD)),
                         RunnerConfig(batch_dir=tmp_path / "batch"),
                         clock=clock, sleep=sleep or _sleep,
                         jitter=jitter or (lambda a, b: a)), clock, slept


class TestSameBrandFloor:
    def test_6_a_repeat_brand_waits_the_remaining_time(self, tmp_path):
        r, clock, slept = runner_with(tmp_path, jitter=lambda a, b: 60.0)
        assert r._await_brand_floor("hilton") == 0.0, "first request never waits"
        clock.advance(10.0)
        waited = r._await_brand_floor("hilton")
        assert waited == pytest.approx(50.0), "60s floor minus 10s already elapsed"
        assert slept == [50.0]

    def test_6b_a_brand_that_already_waited_long_enough_owes_nothing(self, tmp_path):
        r, clock, slept = runner_with(tmp_path, jitter=lambda a, b: 45.0)
        r._await_brand_floor("hilton")
        clock.advance(200.0)
        assert r._await_brand_floor("hilton") == 0.0
        assert slept == []

    def test_7_jitter_never_leaves_the_authorized_band(self, tmp_path):
        """Even a misbehaving jitter callable cannot widen the band."""
        for bad in (0.0, 5.0, 300.0, -10.0):
            r, clock, _ = runner_with(tmp_path, jitter=lambda a, b, v=bad: v)
            r._await_brand_floor("hilton")
            waited = r._await_brand_floor("hilton")   # zero elapsed => waits the floor
            assert SAME_BRAND_FLOOR_MIN_SECONDS <= waited <= SAME_BRAND_FLOOR_MAX_SECONDS

    def test_7b_the_band_is_45_to_75(self):
        assert (SAME_BRAND_FLOOR_MIN_SECONDS, SAME_BRAND_FLOOR_MAX_SECONDS) == (45.0, 75.0)

    def test_7c_a_real_random_jitter_stays_inside_the_band(self, tmp_path):
        rng = random.Random(11)
        r, clock, _ = runner_with(tmp_path, jitter=lambda a, b: rng.uniform(a, b))
        for _ in range(50):
            r._brand_last_start.clear()
            r._await_brand_floor("hilton")
            w = r._await_brand_floor("hilton")
            assert 45.0 <= w <= 75.0, w

    def test_8_a_different_brand_is_never_delayed(self, tmp_path):
        r, clock, slept = runner_with(tmp_path, jitter=lambda a, b: 75.0)
        r._await_brand_floor("hilton")
        assert r._await_brand_floor("marriott") == 0.0
        assert r._await_brand_floor("ihg") == 0.0
        assert slept == [], "unrelated brands add no wait at all"

    def test_8b_unrelated_work_counts_toward_the_gap(self, tmp_path):
        """The reason this costs almost no wall clock on an interleaved queue."""
        r, clock, slept = runner_with(tmp_path, jitter=lambda a, b: 45.0)
        r._await_brand_floor("hilton")
        for other in ("marriott", "ihg", "wyndham"):
            clock.advance(20.0)              # real work on another brand
            r._await_brand_floor(other)
        assert r._await_brand_floor("hilton") == 0.0, "60s of other work covered it"
        assert slept == []

    def test_8c_no_extra_global_delay_was_added(self):
        """The inter-hotel pace is untouched."""
        import inspect

        from services.research_workers.capture_automation import doctrine, runner

        assert doctrine.MIN_SECONDS_BETWEEN_HOTELS == 20.0
        assert doctrine.MAX_SECONDS_BETWEEN_HOTELS == 40.0
        src = inspect.getsource(runner.CaptureRunner._pace)
        assert "SAME_BRAND" not in src, "_pace must not have grown a brand notion"


# --------------------------------------------------------------------------- #
# 9-12. Doctrine that must not move.
# --------------------------------------------------------------------------- #

def _blocked_pages():
    pages = dict(pages_from(GOOD))
    for url in list(pages):
        p = dict(pages[url])
        p["title"] = "Hilton Page Reference Code"
        p["text"] = "Reference: 0.a1b2c3"
        pages[url] = p
    return pages


class TestDoctrineUnchanged:
    def test_9_consecutive_challenge_limit_is_still_three(self):
        assert CONSECUTIVE_CHALLENGE_LIMIT == 3
        assert RunnerConfig(batch_dir="x").challenge_limit == 3

    def test_10_block_outcomes_remain_fail_closed(self, tmp_path):
        clock = FakeClock()
        runner = CaptureRunner(FakeBrowserSession(_blocked_pages()),
                               RunnerConfig(batch_dir=tmp_path / "batch"),
                               clock=clock, sleep=lambda s: clock.advance(s),
                               jitter=lambda a, b: a)
        result = runner.run(CaptureQueue(batch_id="b", entries=(entry_for(GOOD),)))
        rec = result.outcomes[0]
        assert rec.state == EXCEPTION and rec.reason == "ACCESS_DENIED"
        assert result.manifest["counts"]["captured"] == 0

    def test_10b_a_run_of_blocks_still_aborts_the_batch(self, tmp_path):
        clock = FakeClock()
        base = entry_for(GOOD)
        entries = tuple(base.__class__(**{**base.to_dict(), "hotel_id": "h%d" % i,
                                          "alternate_urls": (), "required_fields": (),
                                          "priority_reasons": (),
                                          "discovery_provenance_refs": ()})
                        for i in range(CONSECUTIVE_CHALLENGE_LIMIT + 2))
        runner = CaptureRunner(FakeBrowserSession(_blocked_pages()),
                               RunnerConfig(batch_dir=tmp_path / "batch"),
                               clock=clock, sleep=lambda s: clock.advance(s),
                               jitter=lambda a, b: a)
        result = runner.run(CaptureQueue(batch_id="k", entries=entries))
        assert result.aborted_reason.startswith("consecutive_challenges:")

    def test_10c_no_retry_happens_during_an_active_block(self, tmp_path):
        """A blocked hotel is attempted once and left alone."""
        clock = FakeClock()
        runner = CaptureRunner(FakeBrowserSession(_blocked_pages()),
                               RunnerConfig(batch_dir=tmp_path / "batch"),
                               clock=clock, sleep=lambda s: clock.advance(s),
                               jitter=lambda a, b: a)
        result = runner.run(CaptureQueue(batch_id="b", entries=(entry_for(GOOD),)))
        ids = [o.hotel_id for o in result.outcomes]
        assert len(ids) == len(set(ids)) == 1

    def test_11_no_evasion_code_path_exists(self):
        """Scoped to the modules this work order touched.

        ``doctrine`` is deliberately excluded from the string scan: it already
        contains these very terms as BANNED_AUTOMATION_MARKERS -- a denylist of
        the flags and libraries that must never appear -- which is the guard
        against evasion, not evasion. Asserting their absence there would
        require deleting the guard to pass. The next test checks that list is
        intact instead.
        """
        import inspect

        from services.research_workers.capture_automation import queue, runner

        for mod in (runner, queue):
            src = inspect.getsource(mod).lower()
            for banned in ("user-agent", "user_agent", "useragent", "proxy",
                           "rotate_ip", "ip_rotation", "stealth", "undetected",
                           "solve_captcha", "captcha_solver", "bypass",
                           "set_cookie", "setcookie", "forge", "spoof"):
                assert banned not in src, "%s in %s" % (banned, mod.__name__)

    def test_11b_the_banned_automation_denylist_is_intact(self):
        """The pacing change must not have quietly relaxed the guard."""
        from services.research_workers.capture_automation.doctrine import (
            BANNED_AUTOMATION_MARKERS,
        )

        for marker in ("playwright-stealth", "undetected-chromedriver",
                       "puppeteer-extra", "selenium-stealth", "AutomationControlled",
                       "setUserAgentOverride", "--user-agent", "--proxy-server"):
            assert marker in BANNED_AUTOMATION_MARKERS, marker

    def test_12_resume_remains_deterministic(self, tmp_path):
        """Ordering is a pure function of what REMAINS, so a resumed run orders
        the survivors identically every time."""
        es = [entry("h%02d" % i, ["hilton", "marriott", "ihg"][i % 3]) for i in range(12)]
        done = {"h00", "h03", "h07"}
        survivors = [e for e in es if e.hotel_id not in done]
        first = [e.hotel_id for e in round_robin_by_brand(survivors)]
        for _ in range(3):
            assert [e.hotel_id for e in round_robin_by_brand(list(survivors))] == first

    def test_12b_ordering_is_applied_before_the_limit(self):
        """A truncated batch is still spread across brands rather than being
        the head of one of them."""
        import inspect

        from services.research_workers.capture_automation import runner as R

        src = inspect.getsource(R.CaptureRunner.run)
        assert src.index("round_robin_by_brand") < src.index("self._config.limit")
