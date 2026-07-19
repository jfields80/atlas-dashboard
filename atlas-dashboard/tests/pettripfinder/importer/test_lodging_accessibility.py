"""AES-DATA-004G (Task 6) -- accessibility classifier and planner tests.
No network; the planner is exercised against the real repository manifests
and production CSV (both static repo/operational files) plus synthetic URLs.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from scripts.pettripfinder.importer.lodging_accessibility import (
    ACCESS_ACCESSIBLE_CONFIRMED,
    ACCESS_ACCESSIBLE_PROBABLE,
    ACCESS_CHAIN_POLICY_ONLY,
    ACCESS_DEFER,
    ACCESS_MANUAL_REVIEW,
    ACCESS_MISSING_OFFICIAL_SOURCE,
    ACCESS_TIMEOUT_RETRY_ELIGIBLE,
    ACCESS_WAF_BLOCKED,
    DOMAIN_REGISTRY_VERSION,
    EXECUTABLE_STATES,
    classify_url_accessibility,
    executable_sort_key,
)

# --------------------------------------------------------------------------- #
# Classifier unit tests.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("url", [
    "https://www.hilton.com/en/hotels/cmhaphx-hampton-columbus-airport/",
    "https://www.marriott.com/en-us/hotels/cmhtn-x/overview/",
    "https://www.ihg.com/holidayinnexpress/hotels/us/en/x/cmhpr/hoteldetail",
    "https://www.hyatt.com/hyatt-regency/en-US/cmhrc-x",
    "https://www.redroof.com/property/OH/Columbus/RRI123",
    "https://www.radissonhotels.com/en-us/hotels/country-inn-x",
])
def test_known_waf_domains_blocked_without_live_request(url):
    state, reason = classify_url_accessibility(url)
    assert state == ACCESS_WAF_BLOCKED
    assert reason == "live_2026_07_403"


@pytest.mark.parametrize("url", [
    "https://www.sonesta.com/sonesta-hotels-resorts/oh/columbus/x",
    "https://www.intownsuites.com/extended-stay-hotels/ohio/columbus/x/",
    "https://www.druryhotels.com/locations/columbus-oh/x",
])
def test_known_accessible_domains_confirmed(url):
    state, reason = classify_url_accessibility(url)
    assert state == ACCESS_ACCESSIBLE_CONFIRMED
    assert reason == "live_2026_07_ok"


def test_timeout_domain_retry_eligible():
    state, reason = classify_url_accessibility(
        "https://www.choicehotels.com/ohio/columbus/quality-inn-hotels/oh123")
    assert state == ACCESS_TIMEOUT_RETRY_ELIGIBLE
    assert reason == "live_2026_07_timeout"


def test_unknown_domain_remains_conservative_probable_never_confirmed():
    state, reason = classify_url_accessibility("https://www.some-new-hotel.test/rooms")
    assert state == ACCESS_ACCESSIBLE_PROBABLE
    assert reason == "unobserved_independent_domain"


def test_untested_major_chain_deferred():
    state, _ = classify_url_accessibility("https://www.bestwestern.com/en_US/book/x.html")
    assert state == ACCESS_DEFER


def test_operator_flagged_non_lodging_domain_manual_review():
    state, reason = classify_url_accessibility("https://www.ohiohealth.com/locations/x")
    assert state == ACCESS_MANUAL_REVIEW
    assert reason == "operator_flagged_non_lodging_website"


def test_chain_root_url_is_chain_policy_only():
    state, _ = classify_url_accessibility("https://www.sonesta.com/")
    assert state == ACCESS_CHAIN_POLICY_ONLY


def test_missing_url():
    assert classify_url_accessibility("")[0] == ACCESS_MISSING_OFFICIAL_SOURCE


def test_registry_is_versioned():
    assert re.match(r"^\d{4}\.\d{2}\.\d{2}-\d+$", DOMAIN_REGISTRY_VERSION)


def test_no_property_name_exceptions_in_module_source():
    # The classifier must never special-case an individual hotel by name --
    # its source must not contain property-name strings (spot-check the
    # names most likely to have been hardcoded from live evidence).
    src = (Path(__file__).resolve().parents[3] / "scripts" / "pettripfinder"
           / "importer" / "lodging_accessibility.py").read_text(encoding="utf-8")
    for banned in ("Sonesta Columbus Downtown", "Hampton Inn", "Drury Inn",
                   "InTown Suites Extended Stay", "Quality Inn"):
        assert banned not in src


def test_classifier_is_deterministic():
    url = "https://www.wyndhamhotels.com/laquinta/x/overview"
    assert classify_url_accessibility(url) == classify_url_accessibility(url)


def test_ranking_orders_states_then_source_class():
    confirmed = executable_sort_key(ACCESS_ACCESSIBLE_CONFIRMED, "live_2026_07_ok", "dc_b")
    independent = executable_sort_key(ACCESS_ACCESSIBLE_PROBABLE, "unobserved_independent_domain", "dc_a")
    historical = executable_sort_key(ACCESS_ACCESSIBLE_PROBABLE, "production_import_ok_historical", "dc_a")
    timeout = executable_sort_key(ACCESS_TIMEOUT_RETRY_ELIGIBLE, "live_2026_07_timeout", "dc_a")
    assert confirmed < independent < historical < timeout


# --------------------------------------------------------------------------- #
# Planner tests over the real repository data (still no network).
# --------------------------------------------------------------------------- #

from scripts.pettripfinder.lodging_accessibility_plan import build_plan  # noqa: E402


@pytest.fixture(scope="module")
def plan():
    return build_plan(max_jobs=20, max_timeout_jobs=1, max_per_domain=4)


def test_all_jobs_classified(plan):
    assert plan["report"]["total_jobs"] == 228
    assert sum(plan["report"]["counts_by_state"].values()) == 228


def test_batch_max_20_jobs(plan):
    assert len(plan["batch"]["jobs"]) <= 20


def test_timeout_jobs_capped(plan):
    timeout_domains = {"choicehotels.com", "columbusgrandhotel.com"}
    n = sum(1 for j in plan["batch"]["jobs"]
            if any(d in j["urls"][0] for d in timeout_domains))
    assert n <= 3
    assert n <= 1   # this run's explicit probe budget


def test_no_blocked_job_enters_batch(plan):
    for j in plan["batch"]["jobs"]:
        state, _ = classify_url_accessibility(j["urls"][0])
        assert state in EXECUTABLE_STATES


def test_no_manual_review_or_defer_job_enters_batch(plan):
    for j in plan["batch"]["jobs"]:
        state, _ = classify_url_accessibility(j["urls"][0])
        assert state not in (ACCESS_MANUAL_REVIEW, ACCESS_DEFER,
                             ACCESS_WAF_BLOCKED, ACCESS_CHAIN_POLICY_ONLY)


def test_production_duplicates_excluded_from_batch(plan):
    dup_ids = {d["job_id"] for d in plan["report"]["production_duplicates"]}
    batch_ids = {j["job_id"] for j in plan["batch"]["jobs"]}
    assert not (dup_ids & batch_ids)


def test_prior_wave_jobs_excluded_from_batch(plan):
    attempted = set(plan["report"]["already_attempted_prior_wave"])
    batch_ids = {j["job_id"] for j in plan["batch"]["jobs"]}
    assert not (attempted & batch_ids)


def test_no_duplicate_urls_inside_batch(plan):
    urls = [j["urls"][0] for j in plan["batch"]["jobs"]]
    assert len(urls) == len(set(urls))


def test_batch_output_is_deterministic():
    a = build_plan(max_jobs=20, max_timeout_jobs=1, max_per_domain=4)
    b = build_plan(max_jobs=20, max_timeout_jobs=1, max_per_domain=4)
    assert json.dumps(a["batch"], sort_keys=True) == json.dumps(b["batch"], sort_keys=True)
    assert json.dumps(a["report"], sort_keys=True) == json.dumps(b["report"], sort_keys=True)


def test_stable_job_ids_reused_from_source_manifests(plan):
    # Job IDs must be the original dc_ ids, never re-generated.
    for j in plan["batch"]["jobs"]:
        assert re.match(r"^dc_[0-9a-f]{16}$", j["job_id"])


# --------------------------------------------------------------------------- #
# AES-DATA-004G live defect: locality-tail address stripping must handle a
# spelled-out state name and a trailing country token -- both observed live
# (Plaza Hotel Columbus "Ohio 43215"; La Quinta Reynoldsburg "OH 43068-3455
# US") producing false address conflicts and spurious REVIEW.
# --------------------------------------------------------------------------- #

from scripts.pettripfinder.importer.normalize import normalize_address  # noqa: E402


@pytest.mark.parametrize("raw,city,state,expected", [
    ("2447 Brice Road, Reynoldsburg, OH 43068-3455 US", "Reynoldsburg", "OH", "2447 Brice Road"),
    ("75 East State Street, Columbus, Ohio 43215", "Columbus", "OH", "75 East State Street"),
    ("1 Main St, Columbus, Ohio 43215 USA", "Columbus", "OH", "1 Main St"),
    ("1 Main St, Columbus, OH 43215", "Columbus", "OH", "1 Main St"),
])
def test_address_locality_tail_variants_stripped(raw, city, state, expected):
    assert normalize_address(raw, city, state) == expected


def test_address_zip_never_blindly_stripped_without_locality_tail():
    assert normalize_address("1 Main St 43215", "", "") == "1 Main St 43215"


def test_batch_schema_compatible_with_real_importer(plan, tmp_path):
    from scripts.pettripfinder.importer.batch import load_manifest, validate_manifest
    p = tmp_path / "batch.json"
    p.write_text(json.dumps(plan["batch"], sort_keys=True), encoding="utf-8")
    m = load_manifest(str(p))
    errors = validate_manifest(m, extractor="anthropic", repo_root=tmp_path)
    assert not errors
    assert len(m.jobs) == len(plan["batch"]["jobs"])
