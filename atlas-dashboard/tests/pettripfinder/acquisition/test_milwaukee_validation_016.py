"""PTF-GENERIC-READER-HARDENING-AND-SOURCE-WIRING-016 -- Phases 9 and 12.

The validation run, and the freezes. Nothing here fetches.
"""


import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import registry as REGISTRY       # noqa: E402
from scripts.pettripfinder.acquisition import source_discovery as SD     # noqa: E402
from scripts.pettripfinder.acquisition import source_selection as SS     # noqa: E402

MARKET = "milwaukee-wi"
REPORTS = REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
VALIDATION = REPORTS / "ptf_milwaukee_source_validation_016.json"
DRY_RUN = REPORTS / "ptf_reader_corpus_dry_run_016.json"


def validation():
    return json.loads(VALIDATION.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# 1. overlay source resolution is actually consumed by the run
# --------------------------------------------------------------------------- #

def test_the_validation_run_used_the_discovered_url_for_every_found_row():
    doc = validation()
    overlay = SD.load_overlay(REPO, MARKET)
    for row in doc["results"]:
        expected = overlay.get(row["identity_key"], {})
        if expected.get("status") == SD.POLICY_URL_FOUND:
            assert row["source"]["selected_source_url"] == expected["discovered_url"], \
                row["identity_key"]
            assert row["source"]["source"] == SS.FROM_DISCOVERY


def test_the_validation_run_covered_exactly_nine_subjects():
    doc = validation()
    assert doc["subjects"] == 9
    assert len(doc["results"]) == 9
    assert doc["source_wiring"]["overlay_selections_used"] == 8
    assert doc["source_wiring"]["census_fallbacks_used"] == 1


def test_the_validation_run_processed_no_forbidden_brand():
    """Marriott, Hilton, Motel 6 and the unresolved independents were out of
    scope and must not appear."""
    doc = validation()
    brands = {r["brand"] for r in doc["results"]}
    # An independent's brand key is "INDEP:<domain>" -- it has no chain to
    # name, so its own host stands in for one.
    assert all(b == "RED_ROOF" or b.startswith("INDEP:") for b in brands), brands
    overlay = SD.load_overlay(REPO, MARKET)
    unresolved = {k for k, r in overlay.items()
                  if r.get("status") != SD.POLICY_URL_FOUND}
    assert not (unresolved & {r["identity_key"] for r in doc["results"]})


# --------------------------------------------------------------------------- #
# 2. the census fallback is intact, and 10. routes are unchanged
# --------------------------------------------------------------------------- #

def test_every_route_was_resolved_from_the_census_url():
    doc = validation()
    assert doc["source_wiring"]["routes_resolved_from_census_url"] == 9
    for row in doc["results"]:
        assert row["route"]["resolved_from_url"] == \
            row["source"]["census_official_url"], row["identity_key"]


def test_the_recorded_route_still_matches_the_live_registry():
    doc = validation()
    for row in doc["results"]:
        route = REGISTRY.resolve(brand=row["brand"],
                                 url=row["source"]["census_official_url"],
                                 identity_key=row["identity_key"])
        assert route.provider == row["route"]["provider"], row["identity_key"]
        assert route.reader == row["route"]["reader"], row["identity_key"]


def test_the_run_spent_nothing():
    doc = validation()
    assert doc["cost"]["fresh_requests"] == 0
    assert doc["cost"]["firecrawl_credits"] == 0
    assert doc["cost"]["brightdata_usd_minor"] == 0
    assert all(r["provider_invoked"] is False for r in doc["results"])


def test_the_evidence_integrity_claim_is_specific_about_what_was_checked():
    """A cached re-read may claim what it verified and nothing more."""
    integrity = validation()["evidence_integrity"]
    assert integrity["hash_rederived"] == 9
    assert integrity["quotes_contiguous"] == 9
    assert integrity["publication_grade_granted"] == 0
    assert integrity["rejected_only_for_missing_captured_at"] == 9


# --------------------------------------------------------------------------- #
# 11 and 12. no authority, no publication, and the freezes.
# --------------------------------------------------------------------------- #

def test_no_milwaukee_policy_authority_exists():
    for pattern in ("hotel_policy_facts_milwaukee*.json",
                    "*milwaukee*policy_facts*.json"):
        found = list((REPO / "launch_packages" / "pettripfinder").rglob(pattern))
        assert not found, found


def test_neither_016_report_claims_to_have_written_authority():
    assert validation()["authority_written"] is False
    assert validation()["published"] is False
    dry_run = json.loads(DRY_RUN.read_text(encoding="utf-8"))
    assert dry_run["authority_written"] is False
    assert dry_run["observations_updated"] is False


def test_the_corpus_dry_run_produced_a_queue_rather_than_a_rewrite():
    """Historical records whose reading changed become a QUEUE. This work
    order is not authorised to re-derive them and does not."""
    dry_run = json.loads(DRY_RUN.read_text(encoding="utf-8"))
    queue = dry_run["re_derivation_queue"]
    assert queue["count"] == len(queue["documents"])
    assert queue["count"] == dry_run["counts"]["changed"]


FROZEN = (
    "scripts/pettripfinder/acquisition/routes.json",
    "scripts/pettripfinder/acquisition/providers.py",
    "scripts/pettripfinder/acquisition/registry.py",
    "scripts/pettripfinder/acquisition/failures.py",
    "scripts/pettripfinder/acquisition/readers.py",
    "scripts/pettripfinder/acquisition/source_discovery.py",
    "launch_packages/pettripfinder/markets/discovered_policy_urls/milwaukee-wi.json",
    "launch_packages/pettripfinder/markets/reports/milwaukee-wi_policy_acquisition_queue_001.json",
    "launch_packages/pettripfinder/markets/reports/ptf_independent_url_discovery_014.json",
    "launch_packages/pettripfinder/markets/reports/ptf_generic_reader_diagnostic_013.json",
)

#: The commit this work order started from. The freeze is checked against the
#: repository rather than asserted in prose, and it is checked with git's own
#: BLOB OID rather than a hash of the bytes on disk: this repository normalises
#: line endings, so a raw sha256 of a checked-out file disagrees with a raw
#: sha256 of the blob for files that never changed. Comparing OIDs asks git the
#: question git can answer.
BASELINE_COMMIT = "8a584095ffc6d033e7679be105770500b33abd76"


def _git_prefix():
    """This checkout may sit below the repository root; git paths are rooted
    at the repository, not at the working directory."""
    try:
        out = subprocess.run(["git", "rev-parse", "--show-prefix"], cwd=REPO,
                             capture_output=True, check=True).stdout
        return out.decode("utf-8").strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _blob_at(commit, path):
    try:
        return subprocess.run(
            ["git", "show", "%s:%s%s" % (commit, _git_prefix(), path)],
            cwd=REPO, capture_output=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _oid_at(commit, path):
    try:
        out = subprocess.run(
            ["git", "rev-parse", "%s:%s%s" % (commit, _git_prefix(), path)],
            cwd=REPO, capture_output=True, check=True).stdout
        return out.decode("utf-8").strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _oid_now(path):
    try:
        out = subprocess.run(["git", "hash-object", path], cwd=REPO,
                             capture_output=True, check=True).stdout
        return out.decode("utf-8").strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def test_the_frozen_files_are_unchanged_since_the_baseline_commit():
    missing = []
    for path in FROZEN:
        before = _oid_at(BASELINE_COMMIT, path)
        if before is None:
            missing.append(path)
            continue
        assert before == _oid_now(path), path
    assert not missing, "could not read from git: %s" % missing


def test_the_router_change_is_additive_only():
    """``route_property`` gained one optional keyword. Any caller that does
    not pass it must behave exactly as it did."""
    before = _blob_at(BASELINE_COMMIT,
                      "scripts/pettripfinder/acquisition/router.py")
    assert before is not None
    old = before.decode("utf-8")
    new = (REPO / "scripts/pettripfinder/acquisition/router.py").read_text(
        encoding="utf-8")
    # the only behavioural line that moved
    assert "url=target.requested_url," in old
    assert "url=route_url or target.requested_url," in new
