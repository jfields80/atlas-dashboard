"""PTF-CLEVELAND-ATTENDED-ARTIFACT-QUEUE-001 -- targeted tests.

Two halves, separated by what they need:

* The AUTHORITY tests read only tracked files -- the final partition, the
  census, the Cleveland policy facts, the exclusions. They run in every clone,
  including one with no ``data/`` directory, because queue MEMBERSHIP is derived
  from committed authority and nothing else. If the four queue sizes ever stop
  being 17/15/14/1, either the partition moved or a rule did, and this half says
  which.
* The PACKAGE tests build the real package into a temporary directory from the
  untracked operator handback. They declare that package as a precondition and
  skip with the path named -- the ``ed53d5b``/``441498d`` pattern established
  after a worktree with no ``data/`` reported nine phantom failures.

The load-bearing assertions here are the ones that refuse things: that no
published or excluded hotel can be requeued, that Queue B cannot be entered by
silence, that Queue D never asks for pet-policy evidence, and that
``evidence_status`` cannot claim a screenshot that is not readable image bytes.
A queue that quietly manufactures a row is worse than no queue.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from scripts.pettripfinder import cleveland_attended_artifact_queue_001 as Q
from scripts.pettripfinder import integrate_cleveland_work_browser_001 as WB

#: What the work order stated as expected. Pinned so a drift is a failure with a
#: number in it rather than a silently different package.
EXPECTED_SIZES = {"A": 17, "B": 15, "C": 14, "D": 1}


def _json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def partition():
    return _json(Q.PARTITION_PATH)


@pytest.fixture(scope="module")
def census():
    return _json(Q.CENSUS_PATH)


def _package_or_skip():
    if not Q.input_present():
        pytest.skip("operator browser package absent: %s" % Q.PACKAGE_DIR)


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    _package_or_skip()
    out = tmp_path_factory.mktemp("attended-artifact")
    return Q.write(output_dir=out)


# --------------------------------------------------------------------------- #
# Authority half -- tracked inputs only.
# --------------------------------------------------------------------------- #

def test_queue_membership_is_a_partition_of_four_final_states(partition):
    classes = [Q.queue_class_of(item) for item in partition["items"]]
    assert set(c for c in classes if c) == set(Q.QUEUE_ORDER)
    for item in partition["items"]:
        klass = Q.queue_class_of(item)
        if klass:
            assert item["final_state"] in (
                "AWAITING_POLICY_ARTIFACT", "AWAITING_ATTENDED_CAPTURE",
                "AWAITING_ROUTING_REVIEW")


def test_queue_sizes_derive_from_the_committed_partition(partition):
    sizes = {k: sum(1 for i in partition["items"] if Q.queue_class_of(i) == k)
             for k in Q.QUEUE_ORDER}
    assert sizes == EXPECTED_SIZES


def test_queue_c_and_d_are_exactly_their_final_states(partition):
    counts = partition["final_state_counts"]
    assert (sum(1 for i in partition["items"] if Q.queue_class_of(i) == Q.QUEUE_C)
            == counts["AWAITING_ATTENDED_CAPTURE"])
    assert (sum(1 for i in partition["items"] if Q.queue_class_of(i) == Q.QUEUE_D)
            == counts["AWAITING_ROUTING_REVIEW"])


def test_published_and_excluded_identities_can_never_be_queued(partition):
    for item in partition["items"]:
        if item["final_state"] in ("PUBLISHED_PET_FRIENDLY", "VERIFIED_NO_PETS"):
            assert Q.queue_class_of(item) == ""


def test_marketing_only_wording_is_not_queued(partition):
    marketing = [i for i in partition["items"]
                 if i["final_state"] == "AWAITING_POLICY_ARTIFACT"
                 and i["policy_wording_shape"] == "AFFIRMATIVE_MARKETING_ONLY"]
    assert marketing, "the exclusion is only meaningful if the class is populated"
    assert all(Q.queue_class_of(i) == "" for i in marketing)


def test_every_census_identity_is_queued_or_explained(partition, census):
    grouped = Q.not_queued(partition)
    explained = sum(len(v) for v in grouped.values())
    queued = sum(1 for i in partition["items"] if Q.queue_class_of(i))
    assert queued + explained == len(partition["items"]) == census["count"] == 188


def test_every_not_queued_group_names_its_reason(partition):
    for key in Q.not_queued(partition):
        assert Q.NOT_QUEUED_REASONS.get(key), "unexplained exclusion group: %s" % key


def test_the_queue_contract_columns_are_present():
    required = (
        "queue_id", "queue_class", "priority", "market_id", "hotel_id",
        "hotel_slug", "exact_hotel_name", "brand", "official_url",
        "browser_final_url", "property_code", "address", "city", "state", "zip",
        "phone", "browser_batch", "browser_row_id", "source_status",
        "exact_visible_policy_quote", "supported_candidate_facts",
        "withheld_facts", "routing_correction_status",
        "required_identity_screenshot", "required_policy_screenshot",
        "expected_identity_filename", "expected_policy_filename",
        "destination_folder", "one_next_action", "evidence_status")
    assert set(required) <= set(Q.QUEUE_COLUMNS)
    assert set(Q.FOUNDER_COLUMNS) <= set(Q.QUEUE_COLUMNS)


def test_screenshot_filenames_are_fixed():
    assert Q.IDENTITY_FILENAME == "01-identity.png"
    assert Q.POLICY_FILENAME == "02-pet-policy.png"


def test_market_key_ignores_punctuation_and_case():
    assert Q.market_key("Comfort Inn & Suites") == "comfortinnsuites"
    assert Q.market_key("Hyatt Place -- Westlake") == "hyattplacewestlake"
    assert Q.market_key("Fairfield Inn & Suites — Canton South") \
        == Q.market_key("fairfield inn suites canton south")


# --------------------------------------------------------------------------- #
# Package half -- needs the untracked operator handback.
# --------------------------------------------------------------------------- #

def test_every_validation_check_passes(built):
    failed = [c for c in built["checks"] if not c["passed"]]
    assert not failed, "\n".join("%s: %s" % (c["check"], c["detail"]) for c in failed)


def test_the_package_writes_exactly_the_declared_files(built):
    out = built["output_dir"]
    for name in ("cleveland-attended-artifact-queue.csv",
                 "work-browser-targeted-queue.csv", "manifest.json", "README.txt"):
        assert (out / name).is_file(), name
    folders = sorted(p.name for p in (out / "screenshots").iterdir() if p.is_dir())
    assert len(folders) == len(built["rows"]) == sum(EXPECTED_SIZES.values())
    assert folders == sorted(r["hotel_slug"] for r in built["rows"])


def test_no_screenshot_is_claimed_because_none_exists(built):
    out = built["output_dir"]
    assert not [p for p in (out / "screenshots").rglob("*") if p.is_file()]
    assert all(r["evidence_status"] == "AWAITING_ARTIFACT" for r in built["rows"])
    assert built["manifest"]["evidence_determination"][
        "screenshots_claimed_by_this_package"] == 0


def test_both_csvs_carry_the_same_rows_in_the_same_order(built):
    out = built["output_dir"]
    with (out / "cleveland-attended-artifact-queue.csv").open(
            encoding="utf-8", newline="") as handle:
        machine = list(csv.DictReader(handle))
    with (out / "work-browser-targeted-queue.csv").open(
            encoding="utf-8", newline="") as handle:
        founder = list(csv.DictReader(handle))
    assert [r["queue_id"] for r in machine] == [r["queue_id"] for r in founder]
    assert [r["priority"] for r in machine] == [str(i) for i in
                                                range(1, len(machine) + 1)]


def test_queue_totals_equal_manifest_totals(built):
    totals = built["manifest"]["queue_totals"]
    for klass, expected in EXPECTED_SIZES.items():
        assert totals[klass] == expected
        assert sum(1 for r in built["rows"] if r["queue_class"] == klass) == expected
    assert totals["total"] == len(built["rows"])


def test_queue_a_and_b_wording_re_derives_with_the_pass_001_classifier(built):
    for row in built["rows"]:
        if row["queue_class"] == Q.QUEUE_A:
            assert WB.policy_shape(row["exact_visible_policy_quote"]) \
                == "AFFIRMATIVE_STRUCTURED", row["hotel_slug"]
        if row["queue_class"] == Q.QUEUE_B:
            assert WB.policy_shape(row["exact_visible_policy_quote"]) == "NEGATIVE", \
                row["hotel_slug"]
            assert row["exact_visible_policy_quote"].strip(), row["hotel_slug"]


def test_queue_d_asks_for_identity_evidence_only(built):
    d_rows = [r for r in built["rows"] if r["queue_class"] == Q.QUEUE_D]
    assert len(d_rows) == 1
    row = d_rows[0]
    assert row["hotel_slug"] == "hyatt-place-cleveland-westlake-crocker-park"
    assert row["required_policy_screenshot"] == "NO"
    assert row["expected_policy_filename"] == ""
    assert row["required_identity_screenshot"] == "YES"
    # The recorded URL is dead, so the capture target is the proposal under
    # review -- and the proposal must not be presented as accepted authority.
    assert row["capture_url"] == row["proposed_replacement_url"]
    assert row["capture_url"] != row["official_url"]
    assert row["routing_correction_status"] == "ROUTING_REVIEW_NEEDED_NOT_AUTHORITY"
    assert "not pet-policy publication evidence" in row["one_next_action"]


def test_no_other_queue_redirects_to_a_routing_proposal(built):
    for row in built["rows"]:
        if row["queue_class"] != Q.QUEUE_D:
            assert row["capture_url"] == row["official_url"], row["hotel_slug"]


def test_every_row_has_exactly_one_next_action_and_one_folder(built):
    seen = set()
    for row in built["rows"]:
        assert row["one_next_action"].strip()
        assert "\n" not in row["one_next_action"]
        assert row["destination_folder"] not in seen
        seen.add(row["destination_folder"])
        assert Path(row["destination_folder"]).is_dir()
        assert Path(row["destination_folder"]).name == row["hotel_slug"]


def test_no_property_code_is_inferred_from_a_url(built):
    for row in built["rows"]:
        if row["property_code"]:
            assert row["property_code_status"] == "DISPLAYED", row["hotel_slug"]
        else:
            assert row["property_code_status"] == "NOT_DISPLAYED"
    # Every capture URL in this package carries a brand code in its path and no
    # page displayed one; reading a code out of the path would be inference.
    assert all(r["property_code"] == "" for r in built["rows"])


def test_every_input_file_is_hashed(built):
    hashes = built["manifest"]["input_files_sha256"]
    assert len(hashes) == len(WB.EXPECTED_FILES) + len(Q.AUTHORITY_INPUTS)
    assert all(v.startswith("sha256:") and len(v) == 71 for v in hashes.values())
    for name in WB.EXPECTED_FILES:
        assert any(key.endswith("/" + name) for key in hashes), name


def test_readme_prints_the_exact_evidence_root(built):
    text = (built["output_dir"] / "README.txt").read_text(encoding="utf-8")
    assert str(built["output_dir"]) in text
    assert Q.IDENTITY_FILENAME in text and Q.POLICY_FILENAME in text
    assert "Queue D is identity evidence" in text


def test_evidence_status_needs_readable_image_bytes(built, tmp_path):
    """A placeholder must not be able to claim an artifact."""
    folder = tmp_path / "shots"
    folder.mkdir()
    assert Q.existing_artifacts(folder) == []
    (folder / Q.IDENTITY_FILENAME).write_bytes(b"")
    assert Q.existing_artifacts(folder) == []
    (folder / Q.IDENTITY_FILENAME).write_bytes(b"not a png at all")
    assert Q.existing_artifacts(folder) == []
    (folder / Q.IDENTITY_FILENAME).write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)
    assert Q.existing_artifacts(folder) == [Q.IDENTITY_FILENAME]


def test_no_columbus_or_dayton_hotel_reaches_the_queue(built):
    checks = {c["check"]: c for c in built["checks"]}
    assert checks["no_columbus_or_dayton_property_queued"]["passed"]
    assert checks["no_published_hotel_requeued"]["passed"]
    assert checks["no_verified_no_pets_hotel_requeued"]["passed"]


def test_validate_on_disk_agrees_with_the_package_it_wrote(built):
    result = Q.validate_on_disk(built["output_dir"])
    failed = [c for c in result["checks"] if not c["passed"]]
    assert not failed, "\n".join("%s: %s" % (c["check"], c["detail"]) for c in failed)
    assert len(result["rows"]) == sum(EXPECTED_SIZES.values())


def test_rebuilding_is_deterministic(built, tmp_path):
    """Same inputs, same package -- modulo the root it was asked to write into.

    The evidence root is the one thing that legitimately differs between two
    output locations, and it appears inside ``destination_folder`` and inside
    every ``one_next_action``. Rewriting it to a placeholder on both sides keeps
    this a determinism test rather than a path test.
    """
    second_root = tmp_path / "again"
    Q.write(output_dir=second_root)

    def normalised(root, name):
        text = (root / name).read_text(encoding="utf-8")
        # JSON escapes the backslashes in a Windows path, so the placeholder is
        # applied in both spellings rather than only the raw one.
        return (text.replace(json.dumps(str(root))[1:-1], "<ROOT>")
                    .replace(str(root), "<ROOT>"))

    for name in ("cleveland-attended-artifact-queue.csv",
                 "work-browser-targeted-queue.csv", "README.txt"):
        assert normalised(built["output_dir"], name) == \
            normalised(second_root, name), name
    assert json.loads(normalised(built["output_dir"], "manifest.json")) == \
        json.loads(normalised(second_root, "manifest.json"))
