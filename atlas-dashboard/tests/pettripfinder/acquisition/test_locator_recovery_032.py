"""PTF-MILWAUKEE-HIGH-VALUE-REPAIR-WAVE-032.

WHAT THESE TESTS GUARD
----------------------
A locator that may take a DIFFERENT span of the page than the one it first
chose is a locator that can take the wrong one. The size cap and the
container-scoring rules were the only things standing between a policy block
and "the whole page", and this repair pushes directly against them.

So most of what follows is about refusal: an amenity chip, a service-animal
sentence, a room rate, a parking charge and a smoking fee must each fail to
expand a block, and each of them nearly did.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import locator_recovery_032 as R
from scripts.pettripfinder.brightdata import declined_capture as DECLINED
from scripts.pettripfinder.brightdata import policy_locator as PL
from scripts.pettripfinder.brightdata import policy_surface as PS


def store():
    return json.loads(R.STORE.read_text(encoding="utf-8-sig"))


# --------------------------------------------------------------------------- #
# 1 -- semantic, not length-based.
# --------------------------------------------------------------------------- #

#: The commit 032 made. Its freezes are claims about that commit, not about
#: everything anyone has done to these files since.
COMMIT_032 = "b21a04a"


def _touched_by(commit):
    return subprocess.run(
        ["git", "show", "--pretty=format:", "--name-only", commit],
        cwd=str(REPO), capture_output=True, text=True).stdout.split()


def test_recovery_is_driven_by_terms_and_not_by_length():
    """A longer block is not a better one.

    Wildwood's located block is a thousand characters of collapsed FAQ
    QUESTIONS and the ANSWERS beside it are shorter. A length rule prefers the
    useless one, which is why this compares actionable terms.
    """
    wildwood = next(row for row in R.recoveries()
                    if row["identity_key"] == "wildwood lodge")
    # The real case, not a fixture: the block it replaces is more than twice
    # its length and states nothing a guest can act on.
    assert wildwood["old_block_chars"] > wildwood["new_block_chars"]
    assert PS.actionable_pet_terms(wildwood["old_block"]) == frozenset()
    assert wildwood["recovery"]["terms_added"]
    # And the shorter block is the one that carries the policy.
    assert "$20 fee per dog" in wildwood["new_block"]
    assert "two (2) dogs per room" in wildwood["new_block"]


def test_a_block_that_already_states_everything_is_left_alone():
    block = "Pets welcome. Pet fee $25 per night. Maximum 2 pets per room."
    recovery = PS.recover_richer_block(block, block + " Free wifi. Free parking.")
    assert recovery.recovered is False
    assert "no actionable pet term" in recovery.reason


# --------------------------------------------------------------------------- #
# 2 / 3 / 4 -- the controls that must not expand.
# --------------------------------------------------------------------------- #

def test_no_negative_control_expands():
    expanded = [row["control"] for row in R.negative_controls()
                if row["expanded"]]
    assert expanded == [], expanded


def test_a_service_animal_sentence_cannot_pull_in_a_guest_deposit():
    """Red Roof's block, and the forty characters that nearly broke it.

    "Service Animals are Welcome. Deposit Policy: A $50 refundable deposit for
    incidentals is required at check-in for all guests." The word "Animals"
    sits beside the amount, and a service animal is not a pet.
    """
    block = "Service Animals are Welcome"
    document = (block + ". Deposit Policy: A $50 refundable deposit for "
                        "incidentals is required at check-in for all guests.")
    assert PS.actionable_pet_terms(document) == frozenset()
    assert PS.recover_richer_block(block, document).recovered is False


def test_an_amenity_chip_states_no_term_to_add():
    for block, document in (
            ("Pets allowed Yes",
             "Hotel policies Parking Pets Smoking Pets allowed Yes "
             "All Policies Free breakfast Indoor pool"),
            ("Pet Friendly",
             "Amenities Free WiFi Pet Friendly Outdoor Pool Guest Laundry")):
        assert PS.recover_richer_block(block, document).recovered is False


def test_a_room_rate_beside_a_pet_word_is_not_a_pet_term():
    document = ("Pets Welcome. 1 King Bed 4 Guests Discounted rate: "
                "$160 USD /night Strikethrough Rate: $172")
    assert PS.actionable_pet_terms(document) == frozenset()


def test_a_parking_or_smoking_charge_is_not_a_pet_term():
    document = ("Pets allowed. Self-parking $35 per night. A cleaning fee "
                "will be assessed for smoking in a non-smoking room.")
    assert PS.actionable_pet_terms(document) == frozenset()


# --------------------------------------------------------------------------- #
# 5 -- the recovered block stays property-bound and bounded.
# --------------------------------------------------------------------------- #

def test_a_recovered_block_stays_within_the_locators_own_limits():
    for row in R.recoveries():
        if not row["recovered"]:
            continue
        assert PS.MIN_BLOCK_CHARS <= row["new_block_chars"] <= PS.MAX_BLOCK_CHARS
        assert PS.policy_features(row["new_block"]) >= PS.MIN_POLICY_FEATURES


def test_recovery_only_ever_reads_the_document_it_was_given():
    """It cannot reach another property because it never leaves the page.

    The candidate is a span of the text handed in, which is the document the
    identity gate already bound to this record.
    """
    document = "Pets welcome. Pet fee $30 per night."
    recovery = PS.recover_richer_block("Pets welcome", document)
    assert recovery.recovered is True
    assert recovery.text in " ".join(document.split())


def test_a_recovered_block_drops_trailing_content_that_is_not_about_pets():
    document = ("Pet Fees Price : $40 / NIGHT Maximum number of pets is 2. "
                "Accessibility at Our Hotel We are committed to providing "
                "equal access and opportunity for individuals with "
                "disabilities.")
    recovery = PS.recover_richer_block("Pet Fees", document)
    assert recovery.recovered is True
    assert "Accessibility" not in recovery.text


# --------------------------------------------------------------------------- #
# 6 -- replay uses the recorded block, and never re-runs the search.
# --------------------------------------------------------------------------- #

def test_replay_reads_the_recorded_recovered_block():
    for entry in R.journal_rows():
        directory = REPO / "atlas-dashboard" / entry["attempt_dir"]
        replayed = PL.replay(directory)
        assert replayed.status == PL.REPLAYED
        assert replayed.canonical is True
        assert replayed.text == entry["policy_block"]
        assert replayed.record["recovery"]["recovered"] is True
        assert replayed.record["recovery"]["provider_calls"] == 0


def test_replay_does_not_re_run_the_recovery_search():
    import inspect
    source = inspect.getsource(PL.replay)
    assert "recover_richer_block" not in source
    assert "policy_surface" not in source


def test_the_locator_record_names_the_capture_it_recovered_from():
    for entry in R.journal_rows():
        directory = REPO / "atlas-dashboard" / entry["attempt_dir"]
        record = json.loads((directory / PL.LOCATOR_ARTIFACT).read_text(
            encoding="utf-8-sig"))
        recovery = record["recovery"]
        assert recovery["work_order"] == R.WORK_ORDER
        assert recovery["recovered_from_run"]
        origin = REPO / "atlas-dashboard" / recovery["recovered_from_attempt_dir"]
        assert origin.is_dir()
        # The document is the SAME one, byte for byte, so the recovered block
        # can be checked against the page that was actually served.
        original = (origin / "rendered.html").read_text(encoding="utf-8",
                                                        errors="replace")
        assert PL.sha256_text(original) == record["document_sha256"]


def test_a_record_without_a_recovery_is_still_complete():
    """The contract version did not move, so old records must still replay."""
    record = PL.build_record(
        hit=type("H", (), {"found": True, "strategy": "x", "selector": "",
                           "matched_phrase": "", "policy_features": 1,
                           "container_chars": 20,
                           "candidates_considered": 1,
                           "brand_generic": False, "rendered": True})(),
        block_text="Pets welcome.", document_sha256="abc",
        walk=PL.LIVE_DOM_WALK)
    assert record["contract"] == "ptf-policy-locator/1.0"
    assert record["recovery"] is None


# --------------------------------------------------------------------------- #
# 7 / 8 -- the three Milwaukee cases, from disk, for nothing.
# --------------------------------------------------------------------------- #

def test_the_three_subjects_are_read_from_031s_committed_report():
    rows = R.assert_subjects()
    assert len(rows) == 3
    assert sorted(row["identity_key"] for row in rows) == [
        "hyatt place milwaukee airport", "hyatt regency milwaukee",
        "wildwood lodge"]


def test_all_three_recover_a_richer_block():
    rows = R.recoveries()
    assert len(rows) == 3
    for row in rows:
        assert row["recovered"] is True, row["identity_key"]
        assert row["recovery"]["terms_added"], row["identity_key"]


def test_only_a_recovery_that_states_a_pet_fact_becomes_an_observation():
    """Hyatt Place Airport recovers a correct block and a WRONG reading.

    The reader labels the 1-6 night PET fee of $100 a cleaning fee, when the
    page puts the cleaning charge inside the $200 band. ``cleaning_fee`` is not
    in the corpus's substantive set, so the row is withheld by the same rule
    that keeps an amenity chip out -- no hand-picking required.
    """
    rows = {row["identity_key"]: row for row in R.recoveries()}

    # The GATE, which is 032's rule and holds for any reader: a recovery
    # becomes an observation exactly when the reading states a pet fact.
    for row in rows.values():
        assert row["yields_an_observation"] == bool(row["substantive_pet_fields"])

    # What 032's OWN reader made of the two Hyatts is history, and its report
    # is where that is recorded. Re-deriving it live asserts that they are
    # still unreadable -- which is precisely what 033 was commissioned to fix,
    # so the test would have failed for succeeding. It is read from the
    # committed report instead, the same repair 031's tests needed.
    historical = {row["identity_key"]: row for row in json.loads(
        R.RUN_REPORT.read_text(encoding="utf-8-sig"))["recoveries"]}
    airport = historical["hyatt place milwaukee airport"]
    assert airport["recovered"] is True
    assert airport["extraction"] == {"cleaning_fee": 10000}
    assert airport["yields_an_observation"] is False

    regency = historical["hyatt regency milwaukee"]
    assert regency["recovered"] is True
    assert regency["extraction"] == {}
    assert regency["yields_an_observation"] is False

    # And the blocks themselves are unchanged: 033 repaired the READER.
    for key in ("hyatt place milwaukee airport", "hyatt regency milwaukee"):
        assert rows[key]["new_block"] == historical[key]["new_block"]
        assert rows[key]["recovered"] is True

    wildwood = rows["wildwood lodge"]
    assert wildwood["yields_an_observation"] is True
    assert wildwood["extraction"]["pets_allowed"] is True
    assert wildwood["extraction"]["pet_count_limit"] == 2
    # The two prices are a tier and the reader still refuses to pick one.
    assert wildwood["withheld"]["pet_fee"] == "SCHEMA_CANNOT_REPRESENT"


def test_the_whole_recovery_needs_no_provider_call():
    from scripts.pettripfinder.acquisition import fresh_proof_019a as PROOF
    R.subjects()            # warms any committed-artifact read
    with PROOF.no_provider_calls() as attempts:
        rows = R.recoveries()
        controls = R.negative_controls()
    assert attempts == []
    assert len(rows) == 3
    assert controls
    assert R.build_report()["provider_calls"] == 0


# --------------------------------------------------------------------------- #
# 9 -- a declined capture keeps its evidence and its verdict.
# --------------------------------------------------------------------------- #

def test_a_declined_capture_persists_evidence_without_becoming_an_observation(tmp_path):
    record = DECLINED.keep(
        run_dir=tmp_path, slug="a-hotel", attempt=1,
        outcome="POLICY_NOT_FOUND",
        html="<html><body>No pet policy here.</body></html>",
        body_text="No pet policy here.",
        requested_url="https://example.com/", final_url="https://example.com/",
        title="A Hotel", provider="brightdata_browser",
        identity={"confirmed": True}, detail="no bounded policy container")
    assert record["persisted"] is True
    assert record["verdict"] == "DECLINED"
    directory = tmp_path / "a-hotel" / "declined-01"
    # The document survives...
    assert (directory / "rendered.html").is_file()
    assert (directory / "page-text.txt").is_file()
    # ...and the one artifact every consumer looks for does not exist, which is
    # what makes this directory unmistakable.
    assert not (directory / PL.BLOCK_ARTIFACT).is_file()
    assert not (directory / PL.LOCATOR_ARTIFACT).is_file()
    assert DECLINED.is_declined_directory(directory) is True
    assert PL.replay(directory).status == PL.INSUFFICIENT


def test_a_later_assessment_can_inspect_an_archived_decline(tmp_path):
    DECLINED.keep(
        run_dir=tmp_path, slug="a-hotel", attempt=1,
        outcome="IDENTITY_MISMATCH",
        html="<html><body>Pets are welcome. Pet fee $25 per night.</body></html>",
        body_text="Pets are welcome. Pet fee $25 per night.",
        requested_url="https://example.com/", final_url="https://example.com/",
        title="A Hotel", provider="brightdata_browser",
        identity={"confirmed": False, "reasons": ["no telephone of its own"]},
        detail="identity refused")
    manifest = DECLINED.read(tmp_path / "a-hotel" / "declined-01")
    assert manifest["outcome"] == "IDENTITY_MISMATCH"
    assert manifest["identity"]["confirmed"] is False
    assert manifest["identity"]["reasons"]
    # The question 031 could not answer is answerable from this.
    text = (tmp_path / "a-hotel" / "declined-01" / "page-text.txt").read_text(
        encoding="utf-8")
    assert PS.actionable_pet_terms(text)


def test_a_decline_with_no_document_writes_nothing(tmp_path):
    record = DECLINED.keep(
        run_dir=tmp_path, slug="a-hotel", attempt=1, outcome="ACCESS_DENIED",
        html="", body_text="", requested_url="https://example.com/",
        final_url="", title="", provider="brightdata_browser")
    assert record["persisted"] is False
    assert not (tmp_path / "a-hotel").exists()


def test_persisting_a_decline_never_raises(tmp_path):
    """A broken audit write must not turn a decline into a capture error."""
    blocker = tmp_path / "a-hotel"
    blocker.write_text("not a directory", encoding="utf-8")
    record = DECLINED.keep(
        run_dir=tmp_path, slug="a-hotel", attempt=1,
        outcome="POLICY_NOT_FOUND", html="<html></html>", body_text="x",
        requested_url="https://example.com/", final_url="", title="",
        provider="brightdata_browser")
    assert record["persisted"] is False
    assert "error" in record


def test_no_credential_reaches_a_declined_manifest(tmp_path):
    record = DECLINED.keep(
        run_dir=tmp_path, slug="a-hotel", attempt=1,
        outcome="POLICY_NOT_FOUND", html="<html></html>", body_text="x",
        requested_url="https://example.com/", final_url="", title="",
        provider="brightdata_browser")
    text = json.dumps(record).lower()
    for term in ("password", "auth", "brd-customer", "zone", "token",
                 "secret"):
        assert term not in text, term


# --------------------------------------------------------------------------- #
# 10 / 11 / 12 -- the store, authority, publication.
# --------------------------------------------------------------------------- #

def test_the_store_keeps_one_row_per_identity():
    keys = [row["identity_key"] for row in store()["items"]]
    assert len(keys) == len(set(keys))


def test_the_recovered_property_reached_the_store_with_its_lineage():
    row = next(item for item in store()["items"]
               if item["identity_key"] == "wildwood lodge")
    assert row["source_run"] == R.RUN_ID
    assert row["proposed_facts"]["pet_count_limit"] == 2
    assert row["withheld_fields"]["pet_fee"] == "SCHEMA_CANNOT_REPRESENT"


def test_the_counters_moved_by_exactly_what_recovered():
    counters = R.counters()
    assert counters["census_total"] == 147
    assert counters["active_eligible"] == 133
    assert counters["sum_of_final_states"] == 147
    assert counters["published"] == 0
    # Every observation recovered offline since 032, by the run that recovered
    # it. 033 read two blocks 032 had recovered and could not use, so its
    # journal belongs in this sum: the claim is that the counters move by
    # exactly what was recovered, not that 032 was the last work order to
    # recover anything.
    from scripts.pettripfinder.acquisition import label_value_hardening_033 as R33
    journalled = len(R.journal_rows()) + len(R33.journal_rows())
    assert counters["observed"] == 114 + journalled
    assert counters["active_unresolved"] == 19 - journalled
from . import authority_freeze as AUTHORITY_FREEZE



def test_no_milwaukee_policy_authority_exists():
    root = REPO / "atlas-dashboard" / "launch_packages" / "pettripfinder"
    # NARROWED. This claimed "locator recovery 032 created no Milwaukee authority",
    # which was true and still is -- but read against the live filesystem
    # it became "Milwaukee may never have one", and the founder approved
    # 96 records in PTF-MILWAUKEE-FOUNDER-DECISION-036. The historical
    # claim is checked against the commit; the standing claim -- that
    # authority is recorded and never live inventory -- is checked too.
    AUTHORITY_FREEZE.assert_commit_created_no_authority("b21a04a")
    AUTHORITY_FREEZE.assert_authority_is_recorded_not_live()
    assert store()["authority_written"] is False
    assert store()["founder_approvals_created"] == 0


def test_nothing_is_published():
    assert all(not row.get("published") for row in store()["items"])


def test_routing_and_source_selection_are_unchanged():
    for path in ("atlas-dashboard/scripts/pettripfinder/acquisition/routes.json",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/registry.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/router.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/providers.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/readers.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/source_discovery.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/source_selection.py",
                 "atlas-dashboard/scripts/pettripfinder/brightdata/policy_reading.py",
                 "atlas-dashboard/launch_packages/pettripfinder/identity_census",
                 "atlas-dashboard/launch_packages/pettripfinder/milwaukee_final_partition_001.json"):
        assert not any(name == path or name.startswith(path.rstrip("/") + "/")
                       for name in _touched_by(COMMIT_032)),             "%s was modified by 032" % path


def test_the_original_captures_were_not_rewritten():
    """Recovery writes a NEW directory; history keeps its own block."""
    for row in R.recoveries():
        origin = REPO / "atlas-dashboard" / row["source_attempt_dir"]
        block = (origin / PL.BLOCK_ARTIFACT).read_text(encoding="utf-8")
        assert block.strip() == row["old_block"].strip()
        assert block.strip() != row["new_block"].strip()
