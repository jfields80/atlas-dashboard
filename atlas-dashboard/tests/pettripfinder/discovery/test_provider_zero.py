"""WO-1A -- the Provider Zero checkpoint.

Provider Zero must prove three things at once: that the pipeline runs end to
end on real data, that it makes no network call and no spend doing so, and
that the governance layer refuses anything it cannot honestly hand off.

The corpus lives under gitignored ``data/``, so the real-data tests skip in a
clean clone; the posture tests below always run.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from scripts.pettripfinder.discovery import provider_zero as PZ
from scripts.pettripfinder.discovery import terms_registry as TR
from scripts.pettripfinder.discovery import url_record as U
from scripts.pettripfinder.discovery.queue_seam import PROJECTED, SKIPPED_URL_REVALIDATION

EFFECTIVE = "2026-08-03"
HAS_CORPUS = (PZ.DEFAULT_ROOT / "resolution" / "resolved_candidates.json").exists()
needs_corpus = pytest.mark.skipif(not HAS_CORPUS, reason="discovery corpus is gitignored")


@pytest.fixture(scope="module")
def run():
    if not HAS_CORPUS:
        pytest.skip("discovery corpus is gitignored")
    return PZ.run_checkpoint(run_id="provider-zero-test", effective_time=EFFECTIVE)


# --------------------------------------------------------------------------- #
# Posture -- these must hold with or without the corpus.
# --------------------------------------------------------------------------- #

class TestProviderZeroPosture:
    def test_it_constructs_no_provider_client(self):
        """Structural: the module must not import a live provider client."""
        src = pathlib.Path(PZ.__file__).read_text(encoding="utf-8")
        for forbidden in ("GooglePlacesClient", "OverpassClient", "FoursquareClient",
                          "requests", "urlopen", "RequestsPageFetcher"):
            assert forbidden not in src, "Provider Zero must not reference %s" % forbidden

    def test_robots_is_always_invoked_without_a_fetcher(self):
        """Zero network calls: every robots check passes robots_fetcher=None,
        which has no code path to a socket."""
        tree = ast.parse(pathlib.Path(PZ.__file__).read_text(encoding="utf-8"))
        calls = [n for n in ast.walk(tree)
                 if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Attribute) and n.func.attr == "check_url"]
        assert calls, "expected the checkpoint to exercise the robots gate"
        for call in calls:
            kw = {k.arg: k.value for k in call.keywords}
            assert "robots_fetcher" in kw
            assert isinstance(kw["robots_fetcher"], ast.Constant)
            assert kw["robots_fetcher"].value is None

    def test_provider_zero_is_permitted_while_every_live_provider_is_not(self):
        registry = TR.load_registry()
        TR.assert_live_use_permitted(TR.PROVIDER_ZERO, registry=registry, as_of=EFFECTIVE)
        for name in ("GOOGLE_PLACES", "OPENSTREETMAP", "FOURSQUARE"):
            with pytest.raises(TR.TermsRegistryError):
                TR.assert_live_use_permitted(name, registry=registry, as_of=EFFECTIVE)

    def test_it_never_writes_verified_policy_or_promotion_paths(self):
        src = pathlib.Path(PZ.__file__).read_text(encoding="utf-8")
        for forbidden in ("hotel_policy_facts", "seed_businesses.csv",
                          "hotel_worker_approvals", "promote_", "assemble_",
                          "write_text", "mkdir"):
            assert forbidden not in src, "Provider Zero must not touch %s" % forbidden

    def test_an_unfetched_url_is_never_treated_as_validated(self):
        rec = PZ.build_url_record("https://example.test/hotel", {}, is_confirmed=False)
        assert rec.last_validated_at == ""
        assert rec.property_identity_check == U.IDENTITY_UNCHECKED
        assert not U.evaluate_handoff(rec, as_of=EFFECTIVE).allowed


# --------------------------------------------------------------------------- #
# Real-corpus behaviour.
# --------------------------------------------------------------------------- #

@needs_corpus
class TestProviderZeroOnTheRealCorpus:
    def test_it_reports_zero_network_and_zero_spend(self, run):
        report, _payload, _results = run
        assert report.network_calls == 0
        assert report.spend_usd == 0.0

    def test_it_loads_the_real_corpus(self, run):
        report, _payload, _results = run
        assert report.candidates_loaded > 300
        assert report.resolutions_loaded > 300

    def test_duplicates_were_prevented(self, run):
        report, _payload, _results = run
        assert report.duplicates_prevented > 0
        assert report.provider_records > report.candidates_loaded

    def test_merge_evidence_exists_for_every_merged_candidate(self, run):
        report, _payload, _results = run
        assert report.merge_records > 0

    def test_identity_conflicts_are_surfaced_not_hidden(self, run):
        report, _payload, _results = run
        assert report.identity_conflicts > 0

    def test_robots_is_fail_closed_for_every_host(self, run):
        """Cache-only: no host has a cached robots decision, so every one is
        INDETERMINATE -- which blocks. Silence would have been the failure."""
        report, _payload, _results = run
        assert report.robots_hosts > 0
        assert report.robots.get("ROBOTS_ALLOWED", 0) == 0
        assert report.robots.get("ROBOTS_INDETERMINATE", 0) == report.robots_hosts

    def test_no_candidate_crossed_the_membrane(self, run):
        """Every projected entry passed the denylist at construction; the run
        completing at all means no discovery record declared a policy field."""
        report, _payload, _results = run
        assert report.membrane_violations == 0

    def test_the_unvalidated_corpus_is_refused_rather_than_queued(self, run):
        """THE finding. The existing corpus reports 228
        READY_FOR_PET_POLICY_IMPORT, but not one URL was ever identity-
        confirmed, so FD-5 blocks every handoff. A queue of zero is the
        correct, safe answer here -- and it is the whole reason this
        checkpoint exists rather than a batch of 228 unverified jobs."""
        report, _payload, _results = run
        assert report.urls_blocked_by_revalidation > 200
        assert report.seam[SKIPPED_URL_REVALIDATION] > 200
        assert report.queued == 0

    def test_the_queue_payload_is_consistent_with_the_count(self, run):
        report, payload, _results = run
        assert len(payload["hotels"]) == report.queued

    def test_every_candidate_is_accounted_for(self, run):
        """No silent drops: the seam summary totals the whole corpus."""
        report, _payload, results = run
        assert sum(report.seam.values()) == len(results) == report.candidates_loaded
