"""Bounded static URL revalidation tooling.

Every test here is OFFLINE. Fetchers are injected; the live path is exercised
only through fakes, and one test asserts structurally that ``live=False``
cannot reach the network at all.

What these lock down, in the order they matter:

  1. robots stays fail-closed -- DENIED *and* INDETERMINATE block;
  2. accounting stays budget-authoritative -- the 40-cap is enforced against
     the budget that gates each request, not against what a fetcher chose to
     report, and a divergence is surfaced as an anomaly;
  3. the safeguards inherited from ``importer.fetch`` stay in the path;
  4. FD-5 identity is not weakened -- two INDEPENDENT keys, name never counts,
     and the two address-derived keys can never both be counted;
  5. no provider API is reachable from this module.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery import revalidate as RV
from scripts.pettripfinder.discovery import robots as R
from scripts.pettripfinder.discovery import url_record as U
from scripts.pettripfinder.discovery.models import DiscoveryCandidate, DiscoveryRecord
from scripts.pettripfinder.importer.models import FetchResult

EFFECTIVE = "2026-08-03"

#: The revalidation runner reads its candidate corpus from
#: ``data/discovery/columbus_wave1_lodging/``, which is GITIGNORED. In a fresh
#: ``git worktree`` that directory does not exist, ``run_revalidation`` finds no
#: eligible candidate, and every assertion about what the run DID becomes a
#: statement about an empty run: the loud ones fail ("assert [] == page.calls"),
#: and the quiet ones -- "identity_pass == 0", "anomalies == []" -- pass while
#: proving nothing. Both readings are dishonest, and the failing form has
#: already cost one integration a wrong diagnosis: worker 003 reported these as
#: pre-existing product failures when they are an absent-input artifact that
#: reproduces at every commit.
#:
#: So the corpus is a declared precondition. The check below is deliberately the
#: SAME expression ``run_revalidation`` uses to build its eligible set, not a
#: looser proxy: if it counts one candidate the runner has work to do, so a
#: genuine regression can never be skipped away.
_CORPUS_REASON = (
    "the revalidation candidate corpus is absent: "
    "data/discovery/columbus_wave1_lodging/{hotel,motel}/candidates/ and "
    "resolution/resolved_candidates.json are gitignored, so these runner tests "
    "have no input to exercise. Run in a checkout that carries data/.")


def _eligible_candidate_count() -> int:
    from scripts.pettripfinder.discovery.provider_zero import (
        load_candidates, load_resolutions,
    )

    resolutions = load_resolutions()
    return sum(
        1 for candidate in load_candidates()
        if resolutions.get(candidate.candidate_id, {}).get("resolution_outcome")
        in C.RESOLUTION_ELIGIBLE_FOR_BATCH
        and resolutions.get(candidate.candidate_id, {}).get("resolved_url"))


@pytest.fixture(scope="module")
def real_candidate_corpus():
    """Skip, with the reason named, when the runner has no candidates to read."""
    if _eligible_candidate_count() == 0:
        pytest.skip(_CORPUS_REASON)

LDJSON = b"""<html><head><title>H</title>
<script type="application/ld+json">
{"@type":"Hotel","name":"Columbus Airport Marriott","telephone":"614-475-7551",
 "address":{"@type":"PostalAddress","streetAddress":"1375 North Cassady Avenue",
            "postalCode":"43219"}}
</script></head><body></body></html>"""

NO_LDJSON = b"<html><head><title>Some Hotel</title></head><body>nothing</body></html>"


def _candidate(**kw):
    rec = DiscoveryRecord(
        provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="gp1",
        canonical_category=C.CATEGORY_HOTEL, name="Columbus Airport Marriott",
        normalized_name="columbus airport marriott",
        address_line="1375 North Cassady Avenue", city="Columbus", state="OH",
        postal_code="43219", phone="614-475-7551", observed_at=EFFECTIVE)
    base = dict(candidate_id="dc_a", source_records=(rec,), name=rec.name,
                normalized_name=rec.normalized_name, address_line=rec.address_line,
                city=rec.city, state=rec.state, postal_code=rec.postal_code)
    base.update(kw)
    return DiscoveryCandidate(**base)


def _found(**kw):
    base = dict(name="Columbus Airport Marriott",
                street_address="1375 North Cassady Avenue",
                postal_code="43219", telephone="614-475-7551")
    base.update(kw)
    return RV.StructuredIdentity(**base)


def _agree(cand=None, found=None, phone="614-475-7551"):
    return U.same_property_identity(
        RV.compare_identity(cand or _candidate(), found or _found(), phone))


# --------------------------------------------------------------------------- #
# 1. FD-5 is not weakened.
# --------------------------------------------------------------------------- #

class TestFD5NotWeakened:
    def test_address_plus_phone_is_a_pass(self):
        check, why = _agree()
        assert check == U.IDENTITY_PASS
        assert "2 independent" in why

    def test_address_alone_is_not_enough(self):
        assert _agree(found=_found(telephone=""), phone="")[0] == U.IDENTITY_FAIL

    def test_phone_alone_is_not_enough(self):
        assert _agree(found=_found(street_address="", postal_code=""))[0] == U.IDENTITY_FAIL

    def test_name_alone_never_confirms(self):
        check, why = _agree(found=_found(street_address="", postal_code="", telephone=""),
                            phone="")
        assert check == U.IDENTITY_FAIL
        assert "name alone never" in why

    def test_a_page_with_no_structured_data_yields_no_keys(self):
        """The dominant real-world case: 14 of 15 retrieved pages."""
        check, why = _agree(found=RV.StructuredIdentity(), phone="")
        assert check == U.IDENTITY_FAIL
        assert "no stable identity keys agreed" in why

    def test_a_conflicting_phone_fails_even_with_a_matching_address(self):
        assert _agree(found=_found(telephone="999-999-9999"))[0] == U.IDENTITY_FAIL

    def test_a_conflicting_address_fails_even_with_a_matching_phone(self):
        assert _agree(found=_found(street_address="999 Nowhere Rd",
                                   postal_code="00000"))[0] == U.IDENTITY_FAIL

    def test_the_two_address_derived_keys_are_never_both_counted(self):
        """Independence, not arithmetic. streetAddress and
        postalCode+street-number come from the same address block; counting
        both would satisfy the >=2 rule while defeating its intent."""
        agreement = RV.compare_identity(_candidate(), _found(telephone=""), "")
        assert len(agreement.agreeing_keys) == 1
        assert U.KEY_NORMALIZED_STREET_ADDRESS in agreement.agreeing_keys
        assert U.KEY_POSTAL_PLUS_STREET_NUMBER not in agreement.agreeing_keys

    def test_a_partial_street_match_still_counts(self):
        """A page's streetAddress is usually the bare street while the
        candidate carries a full formatted address."""
        cand = _candidate(address_line="1375 North Cassady Avenue, Columbus, OH 43219")
        assert _agree(cand=cand)[0] == U.IDENTITY_PASS

    def test_phone_matches_on_the_last_ten_digits(self):
        assert _agree(found=_found(telephone="+1 (614) 475-7551"))[0] == U.IDENTITY_PASS


class TestStructuredExtraction:
    def test_extracts_the_separate_address_fields(self):
        got = RV.extract_structured_identity(LDJSON)
        assert got.street_address == "1375 North Cassady Avenue"
        assert got.postal_code == "43219"
        assert got.telephone == "614-475-7551"

    def test_a_page_without_jsonld_yields_empty_fields(self):
        assert RV.extract_structured_identity(NO_LDJSON) == RV.StructuredIdentity()

    def test_malformed_jsonld_never_raises(self):
        assert RV.extract_structured_identity(
            b'<script type="application/ld+json">{not json</script>') == RV.StructuredIdentity()

    def test_non_lodging_types_are_ignored(self):
        body = (b'<script type="application/ld+json">'
                b'{"@type":"Restaurant","name":"X","telephone":"1"}</script>')
        assert RV.extract_structured_identity(body).telephone == ""


# --------------------------------------------------------------------------- #
# 2. Budget-authoritative accounting.
# --------------------------------------------------------------------------- #

class TestBudget:
    def test_the_caps_are_the_authorized_ones(self):
        assert RV.MAX_TOTAL_REQUESTS == 40
        assert RV.MAX_REQUESTS_PER_CANDIDATE == 2
        assert RV.MAX_REQUESTS_PER_DOMAIN == 4
        assert RV.MIN_DOMAIN_PACING_SECONDS == 1.0

    def test_total_cap_refuses_the_next_request(self):
        b = RV.RequestBudget(total=2)
        for i in range(2):
            assert b.may_spend("c%d" % i, "d%d" % i)[0]
            b.spend("c%d" % i, "d%d" % i)
        assert b.may_spend("c9", "d9") == (False, "total_request_cap_reached")

    def test_per_candidate_cap(self):
        b = RV.RequestBudget()
        for _ in range(RV.MAX_REQUESTS_PER_CANDIDATE):
            b.spend("c", "d")
        assert b.may_spend("c", "other")[1] == "per_candidate_cap_reached"

    def test_per_domain_cap_and_reporting(self):
        b = RV.RequestBudget()
        for i in range(RV.MAX_REQUESTS_PER_DOMAIN):
            b.spend("c%d" % i, "d")
        assert b.may_spend("cX", "d")[1] == "per_domain_cap_reached"
        assert "d" in b.domains_at_cap

    def test_pacing_waits_between_same_domain_requests(self):
        slept = []
        clock = {"t": 0.0}
        pacer = RV.DomainPacer(min_seconds=1.0, sleep_fn=slept.append,
                               now_fn=lambda: clock["t"])
        pacer.wait("d")
        pacer.wait("d")
        assert slept and slept[0] == pytest.approx(1.0)

    def test_pacing_does_not_delay_a_different_domain(self):
        slept = []
        clock = {"t": 0.0}
        pacer = RV.DomainPacer(min_seconds=1.0, sleep_fn=slept.append,
                               now_fn=lambda: clock["t"])
        pacer.wait("a")
        pacer.wait("b")
        assert slept == []


# --------------------------------------------------------------------------- #
# 3. Fail-closed robots, end to end through the runner.
# --------------------------------------------------------------------------- #

class _Page:
    def __init__(self, body=LDJSON, ok=True, status=200, reason=""):
        self.calls = []
        self._body, self._ok, self._status, self._reason = body, ok, status, reason

    def fetch(self, url):
        self.calls.append(url)
        return FetchResult(url, self._ok, final_url=url, http_status=self._status,
                           content_type="text/html", body=self._body, reason=self._reason)


def _run(robots_text=None, robots_ok=True, page=None, **kw):
    fetcher = (lambda u: R.RobotsFetchResult(
        ok=robots_ok, text=robots_text, http_status=200 if robots_ok else 403,
        retrieved_at=EFFECTIVE))
    return RV.run_revalidation(
        run_id="t", effective_time=EFFECTIVE, live=False,
        robots_fetcher=fetcher, page_fetcher=page or _Page(),
        pacer=RV.DomainPacer(min_seconds=0, sleep_fn=lambda s: None), **kw)


@pytest.mark.usefixtures("real_candidate_corpus")
class TestRobotsFailClosed:
    def test_a_disallow_blocks_the_page_fetch_entirely(self):
        page = _Page()
        rep = _run(robots_text="User-agent: *\nDisallow: /", page=page,
                   budget=RV.RequestBudget(total=8))
        assert page.calls == []
        assert rep.robots_blocked > 0
        assert rep.urls_attempted == 0
        assert rep.queue_entries == 0

    def test_unreachable_robots_denies_and_blocks(self):
        page = _Page()
        rep = _run(robots_ok=False, page=page, budget=RV.RequestBudget(total=8))
        assert page.calls == []
        assert rep.robots_blocked > 0

    def test_malformed_robots_is_indeterminate_and_blocks(self):
        page = _Page()
        rep = _run(robots_text="<html>not robots</html>", page=page,
                   budget=RV.RequestBudget(total=8))
        assert page.calls == []
        assert rep.robots_indeterminate > 0

    def test_an_allowing_robots_permits_the_fetch(self):
        page = _Page()
        rep = _run(robots_text="User-agent: *\nDisallow:", page=page,
                   budget=RV.RequestBudget(total=8))
        assert page.calls
        assert rep.robots_allowed > 0
        assert rep.urls_attempted > 0

    def test_blocked_candidates_are_counted_not_dropped(self):
        rep = _run(robots_text="User-agent: *\nDisallow: /",
                   budget=RV.RequestBudget(total=8))
        assert rep.still_blocked > 0


@pytest.mark.usefixtures("real_candidate_corpus")
class TestRunnerAccounting:
    def test_the_run_never_exceeds_the_total_cap(self):
        rep = _run(robots_text="User-agent: *\nDisallow:",
                   budget=RV.RequestBudget(total=6))
        assert rep.total_requests <= 6
        assert rep.anomalies == []

    def test_total_requests_is_budget_authoritative(self):
        """Not derived from what a fetcher chose to report -- the offline
        robots fake reports nothing, and the cap must still hold."""
        budget = RV.RequestBudget(total=6)
        rep = _run(robots_text="User-agent: *\nDisallow:", budget=budget)
        assert rep.total_requests == budget.total

    def test_a_retrieval_failure_blocks_rather_than_confirms(self):
        page = _Page(ok=False, status=403, reason="blocked_source", body=b"")
        rep = _run(robots_text="User-agent: *\nDisallow:", page=page,
                   budget=RV.RequestBudget(total=8))
        assert rep.retrieval_failure > 0
        assert rep.identity_unchecked > 0
        assert rep.queue_entries == 0

    def test_a_page_without_structured_data_never_confirms(self):
        page = _Page(body=NO_LDJSON)
        rep = _run(robots_text="User-agent: *\nDisallow:", page=page,
                   budget=RV.RequestBudget(total=8))
        assert rep.identity_pass == 0
        assert rep.queue_entries == 0

    def test_every_request_and_decision_is_recorded(self):
        rep = _run(robots_text="User-agent: *\nDisallow:",
                   budget=RV.RequestBudget(total=6))
        assert rep.decisions
        assert all("stage" in d for d in rep.decisions)

    def test_the_manifest_round_trips(self, tmp_path):
        rep = _run(robots_text="User-agent: *\nDisallow:",
                   budget=RV.RequestBudget(total=4))
        import json
        path = RV.write_manifest(rep, out_dir=tmp_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["run_id"] == "t"
        assert "requests" in data and "decisions" in data


# --------------------------------------------------------------------------- #
# 4. Structural guarantees.
# --------------------------------------------------------------------------- #

SRC = pathlib.Path(RV.__file__).read_text(encoding="utf-8")


class TestStructuralSafeguards:
    def test_no_provider_api_is_reachable(self):
        for forbidden in ("GooglePlacesClient", "OverpassClient", "FoursquareClient",
                          "places.googleapis.com", "overpass-api.de",
                          "GOOGLE_PLACES_API_KEY", "FOURSQUARE_API_KEY"):
            assert forbidden not in SRC, "revalidate must not reference %s" % forbidden

    def test_page_retrieval_goes_through_the_hardened_fetcher(self):
        """SSRF, redirect, content-type and size protections are inherited by
        using importer.fetch.RequestsPageFetcher rather than raw requests."""
        assert "RequestsPageFetcher" in SRC

    def test_the_robots_fetcher_reuses_the_ssrf_gate(self):
        """robots.txt is text/plain so it cannot go through the HTML-only
        fetcher; the host validation must be reused explicitly, not skipped."""
        assert "assert_fetchable" in SRC

    def test_no_stealth_or_bypass_machinery(self):
        tree = ast.parse(SRC)
        names = {n.name for n in ast.walk(tree)
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        for forbidden in ("rotate_user_agent", "bypass", "use_proxy", "spoof",
                          "solve_captcha", "retry_with_agent"):
            assert forbidden not in names
        for forbidden in ("proxies=", "verify=False"):
            assert forbidden not in SRC

    def test_live_is_opt_in(self):
        """``live=False`` is the default, so network access cannot happen by
        omission."""
        tree = ast.parse(SRC)
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "run_revalidation")
        idx = fn.args.kwonlyargs.index(
            next(a for a in fn.args.kwonlyargs if a.arg == "live"))
        assert fn.args.kw_defaults[idx].value is False

    def test_it_documents_that_it_is_not_the_primary_path_for_major_chains(self):
        assert "not the primary identity path" in SRC
        assert "ADR-PTF-AUTOMATED-BROWSING" in SRC

    def test_it_does_not_approve_promote_assemble_or_deploy(self):
        for forbidden in ("promote_", "assemble_", "hotel_policy_facts",
                          "hotel_worker_approvals", "seed_businesses.csv"):
            assert forbidden not in SRC
