"""PTF-MILWAUKEE-OBSERVATION-REDERIVATION-018 -- Phase 9.

The re-derivation, the supersession history, and the freezes. Nothing here
fetches, and every assertion is checkable from committed artifacts.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import registry as REGISTRY          # noqa: E402
from scripts.pettripfinder.acquisition import source_discovery as SD        # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR           # noqa: E402

REPORTS = REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
REDERIVATION = REPORTS / "ptf_milwaukee_observation_rederivation_018.json"
PROPOSALS = REPORTS / "milwaukee-wi_policy_proposals_001.json"
QUEUE_SOURCE = REPORTS / "ptf_reader_corpus_dry_run_017.json"

WORK_ORDER = "PTF-MILWAUKEE-OBSERVATION-REDERIVATION-018"


def rederivation():
    return json.loads(REDERIVATION.read_text(encoding="utf-8-sig"))


def proposals():
    return json.loads(PROPOSALS.read_text(encoding="utf-8-sig"))


def rows():
    return {i["identity_key"]: i for i in proposals()["items"]}


# --------------------------------------------------------------------------- #
# 1-2. the queue, and exactly which properties changed
# --------------------------------------------------------------------------- #

def test_the_queue_is_the_committed_one_and_has_not_moved():
    queued = json.loads(QUEUE_SOURCE.read_text(encoding="utf-8"))
    documents = sorted(queued["re_derivation_queue"]["documents"])
    assert len(documents) == 23
    assert len({d.split("/")[2] for d in documents}) == 9
    doc = rederivation()
    assert doc["queued_documents"] == 23
    assert doc["affected_properties"] == 9


def test_every_queued_document_is_accounted_for_against_a_property():
    """The queue is DOCUMENTS; an observation is a property. Every document
    must land somewhere, or the re-derivation silently skipped evidence."""
    queued = json.loads(QUEUE_SOURCE.read_text(encoding="utf-8"))
    documents = set(queued["re_derivation_queue"]["documents"])
    doc = rederivation()
    mapped = {d for group in doc["documents_by_property"].values() for d in group}
    assert mapped == documents


def test_every_affected_property_produced_a_record_or_a_blocked_row():
    doc = rederivation()
    accounted = ({r["property_slug"] for r in doc["records"]}
                 | {b["property_slug"] for b in doc["blocked"]})
    assert accounted == set(doc["documents_by_property"])
    assert len(accounted) == 9


def test_exactly_the_expected_rows_changed_in_the_observation_store():
    check = rederivation()["observation_store_differential"]
    assert check["clean"] is True
    assert not check["unexpected_rows"]
    assert set(check["rows_that_differ"]) <= set(check["expected_rows"])


def test_no_unqueued_property_changed_by_this_work_order():
    """018 changed only what it queued.

    The store has since been reconciled across every production run and later
    work orders have re-derived records of their own, so a row outside 018's
    queue may legitimately carry someone else's supersession. What must never
    appear on such a row is 018's name.
    """
    changed = {r["identity_key"] for r in rederivation()["records"]}
    for key, row in rows().items():
        if key in changed:
            continue
        marker = row["rederivation"]
        assert marker is None or marker["superseded_by"] != WORK_ORDER, key


# --------------------------------------------------------------------------- #
# 3-4. no provider, and values from persisted evidence
# --------------------------------------------------------------------------- #

def test_no_provider_was_invoked():
    doc = rederivation()
    assert doc["network_requests"] == 0
    assert doc["provider_calls"] == 0
    assert doc["firecrawl_credits"] == 0
    assert doc["brightdata_usd_minor"] == 0


def test_the_module_cannot_reach_a_provider():
    """Checked by parsing its imports rather than by searching its prose."""
    import ast
    from scripts.pettripfinder.acquisition import observation_rederivation_018 as M
    tree = ast.parse(Path(M.__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    forbidden = ("requests", "urllib.request", "httpx", "aiohttp", "socket")
    assert not [m for m in imported if m and m.startswith(forbidden)], imported
    for name in ("firecrawl_capture", "unlocker", "browser_capture",
                 "spider_capture", "providers", "router"):
        assert not any(name in m for m in imported), name


@pytest.mark.parametrize("record", rederivation()["records"],
                         ids=lambda r: r["property_slug"])
def test_every_new_value_reproduces_from_the_persisted_evidence_block(record):
    """No value may be hand-entered. Parse the stored block again here and
    require the same answer, from the file the record names."""
    block = (REPO / record["evidence_block_path"]).read_text(
        encoding="utf-8", errors="replace").strip()
    reading = PR.parse(block, strategy="verify_018")
    result = PR.to_extraction(reading, location="")
    assert dict(result.extraction) == record["new_extraction"]
    assert dict(result.withheld or {}) == record["new_withheld"]


@pytest.mark.parametrize("record", rederivation()["records"],
                         ids=lambda r: r["property_slug"])
def test_every_quote_is_contiguous_within_the_block_it_cites(record):
    block = (REPO / record["evidence_block_path"]).read_text(
        encoding="utf-8", errors="replace")
    for quote in record["evidence_quotes"]:
        assert quote in block, (record["property_slug"], quote)
    assert record["evidence_quotes_contiguous"] is True


# --------------------------------------------------------------------------- #
# 5. supersession history is preserved
# --------------------------------------------------------------------------- #

def test_the_previous_reading_survives_on_every_re_derived_record():
    for record in rederivation()["records"]:
        assert "old_extraction" in record
        assert "old_withheld" in record
        assert record["reader_at_capture"], record["property_slug"]


def test_the_observation_store_carries_the_supersession_on_every_row_it_changed():
    store = rows()
    for record in rederivation()["records"]:
        row = store.get(record["identity_key"])
        if row is None:
            continue
        # 018 could only change rows the store held when it ran, and the store
        # then projected the router run alone. Rows that entered later are new
        # readings, not supersessions of anything 018 wrote.
        if row.get("source_run", "milwaukee-router-001") != "milwaukee-router-001":
            continue
        marker = row["rederivation"]
        assert marker is not None, record["identity_key"]
        # A later work order re-deriving the same record wins, and says so.
        # What 018 guarantees is that the row carries A supersession with the
        # evidence it rests on -- not that 018 is forever the last word.
        assert marker["superseded_by"], record["identity_key"]
        assert marker["reader_commit"]
        assert marker["evidence_block_sha256"]
        if marker["superseded_by"] == WORK_ORDER:
            assert marker["previous_facts"] == record["old_extraction"]
            assert marker["previous_withheld_fields"] == record["old_withheld"]


def test_the_historical_run_reports_were_not_edited():
    """A re-derivation supersedes; it does not rewrite what a run measured."""
    prefix = subprocess.run(["git", "rev-parse", "--show-prefix"], cwd=REPO,
                            capture_output=True, check=True).stdout.decode().strip()
    for name in ("ptf_ihg_live_run_009.json",
                 "ptf_ihg_recertification_011.json",
                 "ptf_milwaukee_provider_utilization_007.json",
                 "ptf_ihg_firecrawl_decision_009.json"):
        rel = "launch_packages/pettripfinder/markets/reports/%s" % name
        before = subprocess.run(
            ["git", "rev-parse", "--verify", "-q", "1537625:%s%s" % (prefix, rel)],
            cwd=REPO, capture_output=True)
        assert before.returncode == 0, name
        now = subprocess.run(["git", "hash-object", rel], cwd=REPO,
                             capture_output=True, check=True).stdout
        assert before.stdout.decode().strip() == now.decode().strip(), name


# --------------------------------------------------------------------------- #
# 6-8. the specific safety checks
# --------------------------------------------------------------------------- #

def test_brookfield_conflicting_fee_basis_stays_withheld():
    """The surface says "15 USD a day" AND "Pet fee per night: 15 USD".
    per_day is not per_night, and this layer does not pick a winner."""
    row = rows()["holiday inn brookfield milwaukee"]
    assert "fee_basis" not in row["proposed_facts"]
    assert row["withheld_fields"]["fee_basis"] == "SOURCE_CONTRADICTORY"
    assert row["proposed_facts"]["pet_fee"] == 1500


def test_brown_deer_tiered_fee_stays_withheld():
    row = rows()["candlewood suites milwaukee brown deer"]
    assert "pet_fee" not in row["proposed_facts"]
    assert row["withheld_fields"]["pet_fee"] == "SCHEMA_CANNOT_REPRESENT"


def test_crowne_plaza_states_the_same_amount_on_two_bases_and_is_withheld():
    """Reported rather than resolved: the block says "the pet fee is 75.00 USD
    per stay" and "Pet fee per night: 75 USD"."""
    row = rows()["crowne plaza milwaukee airport"]
    assert "pet_fee" not in row["proposed_facts"]
    assert row["withheld_fields"]["pet_fee"] == "SCHEMA_CANNOT_REPRESENT"
    assert row["proposed_facts"]["species_allowed"] == ["cat", "dog"]


def test_the_kimpton_zero_value_outcome_is_recorded_exactly_as_produced():
    """A zero fee is read and the zero deposit drops, because the amount-keyed
    dedup collides on 0. Reported, not silently fixed."""
    record = next(r for r in rederivation()["records"]
                  if r["property_slug"] == "kimpton-journeyman-hotel")
    assert record["new_extraction"]["pet_fee"] == 0
    assert record["new_extraction"]["fee_basis"] == "per_night"
    assert "pet_deposit" in record["fields_removed"]


def test_a_positive_species_mention_is_not_turned_into_an_exclusion():
    for record in rederivation()["records"]:
        species = record["new_extraction"].get("species_allowed")
        if not species:
            continue
        # naming a species never asserts the others are refused
        assert "cats_allowed" not in record["new_extraction"] or \
            record["new_extraction"]["cats_allowed"] is False and \
            "cat" not in species


def test_species_survived_where_the_block_states_an_explicit_restriction():
    row = rows()["avid hotels oak creek"]
    assert row["proposed_facts"]["species_allowed"] == ["dog"]


# --------------------------------------------------------------------------- #
# 9-12. nothing outside the observation layer moved
# --------------------------------------------------------------------------- #

BASELINE_COMMIT = "1537625"

FROZEN = (
    "scripts/pettripfinder/acquisition/routes.json",
    "scripts/pettripfinder/acquisition/providers.py",
    "scripts/pettripfinder/acquisition/registry.py",
    "scripts/pettripfinder/acquisition/router.py",
    "scripts/pettripfinder/acquisition/failures.py",
    "scripts/pettripfinder/acquisition/source_discovery.py",
    "scripts/pettripfinder/acquisition/source_selection.py",
    # policy_reading.py was REMOVED from this freeze by
    # PTF-GENERIC-READER-BANDED-FEE-AND-HILTON-CONTAINER-HARDENING-024,
    # which changed the generic reader deliberately: banded fees were
    # collapsing to one understated amount. This work order still changed
    # nothing there, and what it relied on is pinned by its own
    # behavioural tests rather than by a hash of a file another work
    # order is entitled to fix.
    "launch_packages/pettripfinder/markets/discovered_policy_urls/milwaukee-wi.json",
)


def _prefix():
    return subprocess.run(["git", "rev-parse", "--show-prefix"], cwd=REPO,
                          capture_output=True, check=True).stdout.decode().strip()


def test_routes_reader_and_discovery_are_untouched():
    for path in FROZEN:
        before = subprocess.run(
            ["git", "rev-parse", "--verify", "-q",
             "%s:%s%s" % (BASELINE_COMMIT, _prefix(), path)],
            cwd=REPO, capture_output=True)
        assert before.returncode == 0, path
        now = subprocess.run(["git", "hash-object", path], cwd=REPO,
                             capture_output=True, check=True).stdout
        assert before.stdout.decode().strip() == now.decode().strip(), path


def test_the_registry_still_routes_every_brand_where_016_left_it():
    expected = {"CHOICE": "firecrawl", "WYNDHAM": "firecrawl",
                "IHG": "firecrawl", "MOTEL6": "brightdata_browser",
                "RED_ROOF": "brightdata_browser"}
    for brand, provider in expected.items():
        assert REGISTRY.resolve(brand=brand,
                                url="https://example.test/").provider == provider


def test_the_discovery_overlay_still_resolves_eight_policy_urls():
    overlay = SD.load_overlay(REPO, "milwaukee-wi")
    found = [r for r in overlay.values() if r["status"] == SD.POLICY_URL_FOUND]
    assert len(found) == 8


def test_no_milwaukee_policy_authority_exists():
    found = list((REPO / "launch_packages" / "pettripfinder")
                 .rglob("*hotel_policy_facts*milwaukee*"))
    assert not found, found


def test_nothing_was_published_and_nothing_was_approved():
    doc = rederivation()
    assert doc["authority_written"] is False
    assert doc["published"] is False
    assert doc["founder_approvals_created"] == 0
    for record in doc["records"]:
        assert record["published"] is False
        assert record["founder_approved"] is False

    store = proposals()
    assert store["authority_written"] is False
    assert store["founder_approvals_created"] == 0
    assert all(i["published"] is False for i in store["items"])
    assert all(i["founder_approved"] is False for i in store["items"])


def test_a_better_reading_did_not_promote_any_record():
    """Publication status is independent of observation correctness. Six rows
    gained a fee; none of them gained a publication."""
    for row in proposals()["items"]:
        if row["rederivation"] is None:
            continue
        assert row["published"] is False
        assert row["founder_approved"] is False


def test_the_proposals_builder_is_a_no_op_without_a_re_derivation():
    """The seam added to the observation store must change nothing by itself."""
    from scripts.pettripfinder import milwaukee_policy_proposals_001 as PROP
    rebuilt = PROP.build(write=False)
    assert all(i["rederivation"] is None for i in rebuilt["items"])
