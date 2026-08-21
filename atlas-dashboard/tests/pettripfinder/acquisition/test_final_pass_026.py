"""PTF-MILWAUKEE-FINAL-ACQUISITION-PASS-026.

The last sixteen Milwaukee properties, on the committed architecture. After
this, touched is 127 and never-touched is 0.

WHAT THESE TESTS GUARD
----------------------
That the subject set was exactly the sixteen never-touched properties and
nothing already acquired was touched again.

That source selection did its job without inventing anything: the eight
independents with a validated discovered URL were fetched at that URL, and the
three recorded NO_POLICY_URL_FOUND fell back to the census page rather than a
guessed ``/pets``.

And that acquiring a page is not the same as learning a policy. Three Motel 6
captures asserted "pets allowed" from a block of page chrome and one Red Roof
capture carried nothing but a service-animal sentence; all four would have been
handed to a founder as ready. A bare allowed-flag is now held, and the change
caught three pre-existing rows as well.
"""

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder import milwaukee_policy_proposals_001 as PROP     # noqa: E402
from scripts.pettripfinder.acquisition import final_pass_026 as F            # noqa: E402
from scripts.pettripfinder.acquisition import hilton_decision_023 as H       # noqa: E402
from scripts.pettripfinder.acquisition import providers as PROVIDERS         # noqa: E402
from scripts.pettripfinder.acquisition import registry as REGISTRY           # noqa: E402
from scripts.pettripfinder.acquisition import source_selection as SS         # noqa: E402
from scripts.pettripfinder.acquisition import store_integration_025 as S     # noqa: E402
from scripts.pettripfinder.brightdata import policy_locator as PL            # noqa: E402
from pettripfinder.acquisition import locator_freeze as LOCATOR_FREEZE
from pettripfinder.acquisition import reader_freeze as READER_FREEZE


def run_report():
    return json.loads(F.RUN_REPORT.read_text(encoding="utf-8-sig"))


def store():
    return json.loads(F.STORE.read_text(encoding="utf-8-sig"))


# --------------------------------------------------------------------------- #
# 1-2. The subject set.
# --------------------------------------------------------------------------- #

def test_the_run_covered_exactly_sixteen_subjects():
    doc = run_report()
    assert doc["subject_count"] == 16 == F.EXPECTED_SUBJECTS
    assert doc["processed"] == 16
    assert doc["run_complete"] is True
    assert doc["assertions"]["subject_count_is_16"] is True


def test_the_class_split_is_four_eleven_one():
    doc = run_report()
    classes = Counter(r["class"] for r in doc["rows"])
    assert dict(classes) == F.EXPECTED_CLASSES == {"MOTEL6": 4,
                                                   "INDEPENDENT": 11,
                                                   "RED_ROOF": 1}


def test_no_already_touched_property_was_acquired():
    """The cohort was the never-touched set; every subject was new."""
    doc = run_report()
    subjects = {r["identity_key"] for r in doc["rows"]}
    # Runs BEFORE 026 only. 027 later re-acquired several of these subjects,
    # which is a fact about 027 and says nothing about whether 026's cohort
    # had been touched when 026 chose it.
    before_026 = S.RUN_ORDER[:S.RUN_ORDER.index(F.RUN_ID)]
    prior = set()
    for run, journal, _root in S.SOURCES:
        if run not in before_026:
            continue
        path = S.DATA / journal
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                prior.add(json.loads(line)["identity_key"])
    assert not subjects & prior


def test_the_cohort_is_now_empty():
    """Nothing routable remains untouched."""
    assert F.cohort() == []


# --------------------------------------------------------------------------- #
# 3-4. Source selection: overlay consumed, nothing invented.
# --------------------------------------------------------------------------- #

def test_all_eight_discovered_urls_were_consumed():
    doc = run_report()
    overlay_rows = [r for r in doc["rows"]
                    if r.get("source_origin") == SS.FROM_DISCOVERY]
    assert len(overlay_rows) == 8
    for row in overlay_rows:
        assert row["source_url"] != row["census_url"], row["canonical_name"]
        assert row["overlay_status"] == "POLICY_URL_FOUND"


def test_the_three_without_a_discovered_url_were_not_given_one():
    doc = run_report()
    fallback = [r for r in doc["rows"]
                if r.get("overlay_status") == "NO_POLICY_URL_FOUND"]
    assert len(fallback) == 3
    for row in fallback:
        assert row["source_url"] == row["census_url"], row["canonical_name"]
        assert row["source_url_guessed"] is False


def test_no_url_was_guessed_anywhere():
    doc = run_report()
    assert doc["source_selection"]["guessed_urls"] == 0
    for row in doc["rows"]:
        for invented in ("/pets", "/faq", "/policy", "/pet-policy"):
            if row["source_url"].endswith(invented):
                # Only legitimate if the overlay actually supplied it.
                assert row["source_origin"] == SS.FROM_DISCOVERY, row["canonical_name"]


# --------------------------------------------------------------------------- #
# 5-6. Production routes and canonical locator.
# --------------------------------------------------------------------------- #

def test_the_committed_routes_were_used_without_override():
    doc = run_report()
    for row in doc["rows"]:
        if not row.get("provider_primary"):
            continue
        expected = REGISTRY.resolve(brand=row["brand"],
                                    url=row["census_url"],
                                    identity_key=row["identity_key"])
        assert row["provider_primary"] == expected.provider, row["canonical_name"]


def test_every_successful_capture_persisted_the_canonical_contract():
    doc = run_report()
    locator = doc["canonical_locator"]
    acquired = [r for r in doc["rows"] if r["acquisition_status"] == "ACQUIRED"]
    assert locator["captures_with_block"] == len(acquired)
    assert locator["captures_with_locator_record"] == len(acquired)
    assert locator["replayed_canonically"] == len(acquired)
    for row in acquired:
        art = row["canonical_artifacts"]
        assert art["policy_block"] and art["locator_json"]
        assert art["replay_status"] == PL.REPLAYED
        assert art["block_sha256"] and art["document_sha256"]


# --------------------------------------------------------------------------- #
# 7. An amenity chip is not a policy.
# --------------------------------------------------------------------------- #

def test_a_bare_allowed_flag_is_held_not_promoted():
    """Three Motel 6 rows and one Red Roof row would have been ready."""
    rows = [i for i in store()["items"]
            if i.get("source_run") == F.RUN_ID]
    for row in rows:
        substantive = set(row["proposed_facts"]) - {
            "pets_allowed", "pets_allowed_quote", "service_animal_exception",
            "service_animal_statement"}
        if not substantive:
            assert row["review_status"] == PROP.HELD_INSUFFICIENT, \
                row["canonical_name"]


def test_a_service_animal_sentence_is_not_a_pet_policy():
    rows = {i["canonical_name"]: i for i in store()["items"]}
    red = rows.get("Red Roof Inn Milwaukee - Airport/ Oak Creek")
    assert red is not None
    assert red["review_status"] == PROP.HELD_INSUFFICIENT
    assert "pet_fee" not in red["proposed_facts"]


def test_the_usable_bar_rejects_service_animal_only_text():
    verdict = F.reassess_row({
        "acquisition_status": "ACQUIRED",
        "policy_block": "Service Animals are Welcome",
        "reader_fields": ["service_animal_exception"], "reader_withheld": []})
    assert verdict["verdict"] == H.NOT_USABLE
    assert "not_service_animal_only" in verdict["reason"]


def test_a_real_policy_still_passes_the_bar():
    verdict = F.reassess_row({
        "acquisition_status": "ACQUIRED",
        "policy_block": ("A maximum of 2 pets (dogs or cats) per room are "
                         "allowed. A one-time pet fee of $150 is "
                         "non-refundable."),
        "reader_fields": ["pet_fee", "pet_count_limit", "species_allowed"],
        "reader_withheld": ["fee_basis"]})
    assert verdict["verdict"] == H.USABLE


def test_an_identity_refusal_is_not_called_an_access_failure():
    """The label this work order corrected mid-run."""
    reason = F.classify_unresolved(
        {"usable_policy": H.NOT_USABLE, "acquisition_status": "NOT_ACQUIRED",
         "failure": "IDENTITY_MISMATCH"}, {"overlay_status": ""})
    assert reason == F.IDENTITY_FAILURE


# --------------------------------------------------------------------------- #
# 8-9. Store integration through 025.
# --------------------------------------------------------------------------- #

def test_the_store_integration_used_025_semantics():
    assert F.RUN_ID in {s[0] for s in S.SOURCES}
    assert S.RUN_KINDS[F.RUN_ID][0] == S.CURRENT_PRODUCTION
    assert F.RUN_ID in S.RUN_ORDER


def test_one_identity_cannot_produce_duplicate_rows():
    counts = Counter(i["identity_key"] for i in store()["items"])
    assert not [k for k, n in counts.items() if n > 1]


def test_only_publication_grade_rows_entered():
    doc = run_report()
    graded = {r["identity_key"] for r in doc["rows"] if r["publication_grade"]}
    in_store = {i["identity_key"] for i in store()["items"]
                if i.get("source_run") == F.RUN_ID}
    assert in_store == graded
    assert len(in_store) == 6


def test_unresolved_properties_did_not_receive_invented_rows():
    """Nothing 026 failed to acquire got a row OUT OF 026.

    A later work order may legitimately acquire one of them -- 027 did, for
    four -- so the store row must be checked for which run produced it rather
    than merely for existing. The thing that would be wrong is a row 026 could
    not have evidence for.
    """
    doc = run_report()
    unacquired = {r["identity_key"] for r in doc["rows"]
                  if r["acquisition_status"] != "ACQUIRED"}
    from_026 = {i["identity_key"] for i in store()["items"]
                if i.get("source_run") == F.RUN_ID}
    assert not unacquired & from_026


# --------------------------------------------------------------------------- #
# 10-11. The counters close.
# --------------------------------------------------------------------------- #

def test_touched_is_127_and_never_touched_is_zero():
    routable = F.routable()
    touched = F.touched_identities() & set(routable)
    assert len(routable) == 127
    assert len(touched) == 127
    assert len(set(routable) - touched) == 0


def test_observed_plus_unresolved_reconciles_to_routable():
    """The ROUTABLE subset reconciles -- which is not the market.

    ``observed`` is intersected with the routable set because the store is no
    longer confined to it: 028 acquired the premium-domain bucket, which was
    excluded from routable by cost and is census inventory all the same. This
    equation is about the 127 and says nothing about the 147; the full-census
    reconciliation is 028's.
    """
    routable = set(F.routable())
    observed = {i["identity_key"] for i in store()["items"]} & routable
    graded = set()
    for run, journal, _root in S.SOURCES:
        path = S.DATA / journal
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            state = row.get("final_state") or row.get("acquisition_status") or ""
            if state == "ACQUIRED_PUBLICATION_GRADE" or row.get("publication_grade"):
                graded.add(row["identity_key"])
    unresolved = (F.touched_identities() & routable) - graded
    assert len(observed) + len(unresolved) == len(routable) == 127


# --------------------------------------------------------------------------- #
# 12-14. Freezes.
# --------------------------------------------------------------------------- #

def test_no_milwaukee_policy_authority_exists():
    found = list((REPO / "launch_packages" / "pettripfinder")
                 .rglob("*hotel_policy_facts*milwaukee*"))
    assert not found, found
    assert run_report()["authority_written"] is False


def test_published_remains_zero():
    assert sum(1 for i in store()["items"] if i.get("published")) == 0
    assert sum(1 for i in store()["items"] if i.get("founder_approved")) == 0
    assert run_report()["published"] is False


def test_routes_and_providers_are_unchanged():
    for brand, provider in (("HILTON", PROVIDERS.BRIGHTDATA_BROWSER),
                            ("MARRIOTT", PROVIDERS.BRIGHTDATA_BROWSER),
                            ("CHOICE", PROVIDERS.FIRECRAWL),
                            ("WYNDHAM", PROVIDERS.FIRECRAWL),
                            ("IHG", PROVIDERS.FIRECRAWL),
                            ("MOTEL6", PROVIDERS.BRIGHTDATA_BROWSER),
                            ("RED_ROOF", PROVIDERS.BRIGHTDATA_BROWSER)):
        assert REGISTRY.resolve(brand=brand,
                                url="https://example.com/x").provider == provider
    for path in ("atlas-dashboard/scripts/pettripfinder/acquisition/routes.json",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/registry.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/router.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/providers.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/source_discovery.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/source_selection.py",
                 "atlas-dashboard/launch_packages/pettripfinder/identity_census"):
        changed = subprocess.run(["git", "status", "--porcelain", "--", path],
                                 cwd=str(REPO.parent), capture_output=True,
                                 text=True).stdout.strip()
        assert changed == "", "%s was modified by 026" % path
    LOCATOR_FREEZE.assert_locator_surface_unchanged()
    READER_FREEZE.assert_reader_protections_unchanged()

def test_historical_run_reports_are_unchanged():
    for path in ("ptf_marriott_milwaukee_run_020.json",
                 "ptf_hilton_milwaukee_run_023.json",
                 "ptf_hilton_closure_023.json",
                 "ptf_generic_reader_rederivation_queue_024.json"):
        changed = subprocess.run(
            ["git", "status", "--porcelain", "--",
             "atlas-dashboard/launch_packages/pettripfinder/markets/reports/" + path],
            cwd=str(REPO.parent), capture_output=True, text=True).stdout.strip()
        assert changed == "", "%s was modified by 026" % path


def test_existing_observations_kept_their_facts():
    """026 added rows; it did not rewrite anyone else's."""
    doc = json.loads(
        (REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
         / "ptf_milwaukee_store_integration_025.json").read_text(
            encoding="utf-8-sig"))
    # ``changed_facts`` is no longer asserted empty: 029 re-derived four
    # identities from their persisted evidence through this same shared report,
    # and none of them is 026's. What must hold is that nothing was lost.
    assert doc["removed"] == []
    assert doc["duplicates"] == []
    assert "best western germantown inn" not in doc["changed_facts"]
    # The store-integration report belongs to whichever work order last ran the
    # integration -- 027 at the time of writing. What 026 added is pinned from
    # the store itself, by source run, which no later integration can move.
    assert len({i["identity_key"] for i in store()["items"]
                if i.get("source_run") == F.RUN_ID}) == 6
