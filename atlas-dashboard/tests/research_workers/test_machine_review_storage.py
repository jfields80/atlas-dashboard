"""PTF-MACHINE-REVIEW storage -- where each part of a review lives, and why.

The rule these tests defend is one line: **track what cannot be recomputed,
ignore what can.**

A PENDING record is reproducible, so it stays in the gitignored tree. A human
decision is not reproducible -- nobody can recompute a judgement from evidence --
so it is tracked, append-only, with git history for attribution. Raw evidence
never enters git at all: captured pages are verbatim third-party HTML, and a scan
of this corpus found 67 Google API keys embedded by the brands themselves.

Offline: no network, no browser, no production write.
"""

from __future__ import annotations

import copy
import hashlib
import json
import pathlib

import pytest

from services.research_workers import machine_review_storage as S
from services.research_workers import machine_capture_review as MR

REPO = pathlib.Path(__file__).resolve().parents[2]


# --------------------------------------------------------------------------- #
# Fixtures: a small repo-shaped tree with one batch of evidence.
# --------------------------------------------------------------------------- #

TEXT = "Home Rooms Pet Policy Pets Welcome Non-Refundable Pet Fee Per Stay: $100.00 Contact"
HTML = "<html><body>%s</body></html>" % TEXT


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@pytest.fixture
def repo(tmp_path):
    """A scratch repository root holding one capture batch."""
    batch = tmp_path / "data/worker_runs/pettripfinder/20260803T235532-remaining-batch"
    caps = batch / "captures"
    caps.mkdir(parents=True)
    payload = {
        "schema": "ptf-official-capture/1.0", "final_url": "https://h.example/x/",
        "text": TEXT, "text_sha256": _sha(TEXT),
        "html": HTML, "html_sha256": _sha(HTML),
        "automation": {"policy": {"text_start": 11, "text_end": 74}},
    }
    (caps / "prop.json").write_text(json.dumps(payload), encoding="utf-8")
    (caps / "prop.png").write_bytes(b"\x89PNG\r\n\x1a\npixels")
    (caps / "prop.view.json").write_text(json.dumps({"viewport_width": 1424}),
                                         encoding="utf-8")
    (batch / "journal.jsonl").write_text('{"event":"done"}\n', encoding="utf-8")
    # Browser scratch that must never be manifested: it holds session credentials.
    prof = batch / ".chrome-profile" / "Default"
    prof.mkdir(parents=True)
    (prof / "Cookies").write_bytes(b"SQLite format 3\x00secret-session")
    (prof / "Login Data").write_bytes(b"SQLite format 3\x00creds")
    return tmp_path


def _record(repo, **kw):
    """A record dict shaped exactly like MachineCaptureReview.to_dict()."""
    batch = "data/worker_runs/pettripfinder/20260803T235532-remaining-batch"
    cap = "%s/captures/prop.json" % batch
    rec = {
        "schema": MR.SCHEMA, "hotel_id": "discovery-test-property",
        "listing_key": "test property", "hotel_name": "Test Property",
        "brand": "testbrand",
        "normalized_url": "https://h.example/x/", "source_url": "https://h.example/x/",
        "capture_path": cap, "screenshot_path": "%s/captures/prop.png" % batch,
        "view_path": "%s/captures/prop.view.json" % batch,
        "capture_sha256": S._sha256_file(repo / cap)[0],
        "rendered_text_sha256": _sha(TEXT), "html_sha256": _sha(HTML),
        "screenshot_sha256": S._sha256_file(repo / ("%s/captures/prop.png" % batch))[0],
        "view_sha256": S._sha256_file(repo / ("%s/captures/prop.view.json" % batch))[0],
        "identity_outcome": "IDENTITY_CONFIRMED",
        "identity_key_groups": ["address", "phone"],
        "identity_authoritative_basis": ["structured_metadata"],
        "identity_evidence": [{"key": "normalized_street_address", "group": "address",
                               "basis": "structured_metadata", "authoritative": True,
                               "expected": "1 Test St", "observed": "1 Test St"}],
        "policy_excerpt": "Pet Policy Pets Welcome",
        "policy_offsets": {"text_start": 11, "text_end": 74},
        "evidence_quotes": [{"field": "pet_fee", "value": "$100.00", "quote": "q"}],
        "facts": {"pets_allowed": "true", "pet_fee": "$100.00"},
        "extraction_result_hash": "sha256:" + "a" * 64,
        "bridge_verified": ["identity_confirmed"], "published_overlap": "NONE",
        "capture_commit": "507534a", "status": MR.STATUS_PENDING_REVIEW,
        "publishable": False,
    }
    rec.update(kw)
    rec["created_at"] = "2026-08-04T12:00:00Z"
    rec["record_hash"] = S.rederive_record_hash(rec)
    return rec


def _decision(record, **kw):
    payload = {
        "reviewer_id": "reviewer1", "reviewed_at": "2026-08-04T13:00:00Z",
        "decision": MR.DECISION_APPROVED, "field_decisions": {},
        "overlap_approved": False, "notes": "",
        "source_record_hash": record["record_hash"],
    }
    payload.update(kw)
    payload["approval_hash"] = "sha256:" + hashlib.sha256(
        S._canonical(payload).encode("utf-8")).hexdigest()
    return payload


def _store(repo, record, **kw):
    S.write_pending_records([_Rec(record)], "20260803T235532-remaining-batch", repo)
    store = S.append_decision(S.empty_decisions(), listing_key=record["listing_key"],
                              hotel_id=record["hotel_id"],
                              decision=_decision(record, **kw))
    return store


class _Rec:
    """Minimal stand-in with the two attributes the writer touches."""
    def __init__(self, d):
        self._d = d
        self.hotel_id = d["hotel_id"]
        self.status = d["status"]

    def to_dict(self):
        return self._d


# --------------------------------------------------------------------------- #
# A. Evidence manifests.
# --------------------------------------------------------------------------- #

def test_the_manifest_carries_metadata_only(repo):
    batch = repo / "data/worker_runs/pettripfinder/20260803T235532-remaining-batch"
    man = S.build_evidence_manifest(batch, repo)
    assert man["schema"] == "ptf-machine-review-evidence-manifest/1.0"
    assert set(man["files"][0]) == {"relative_path", "byte_size", "sha256",
                                    "artifact_class", "captured_at"}
    body = json.dumps(man)
    assert TEXT not in body and HTML not in body       # no page content
    assert "secret-session" not in body                # no cookie bytes
    assert not any(e["relative_path"].startswith(("C:", "/")) for e in man["files"])


def test_browser_profile_credentials_never_enter_a_manifest(repo):
    """.chrome-profile holds Cookies and Login Data. It is not evidence."""
    batch = repo / "data/worker_runs/pettripfinder/20260803T235532-remaining-batch"
    paths = [e["relative_path"] for e in S.build_evidence_manifest(batch, repo)["files"]]
    assert not any(".chrome-profile" in p for p in paths)
    assert not any(p.endswith(("Cookies", "Login Data")) for p in paths)
    assert sorted(pathlib.Path(p).name for p in paths) == [
        "journal.jsonl", "prop.json", "prop.png", "prop.view.json"]


def test_the_manifest_is_deterministic(repo):
    batch = repo / "data/worker_runs/pettripfinder/20260803T235532-remaining-batch"
    assert S.build_evidence_manifest(batch, repo) == S.build_evidence_manifest(batch, repo)


def test_a_completed_manifest_is_immutable(repo):
    batch = repo / "data/worker_runs/pettripfinder/20260803T235532-remaining-batch"
    man = S.build_evidence_manifest(batch, repo)
    _path, digest = S.write_evidence_manifest(man, batch)
    _again, digest2 = S.write_evidence_manifest(man, batch)     # identical: allowed
    assert digest == digest2
    changed = copy.deepcopy(man)
    changed["files"][0]["sha256"] = "0" * 64
    with pytest.raises(S.StorageError, match="evidence_manifest_is_immutable"):
        S.write_evidence_manifest(changed, batch)


def test_missing_evidence_fails_closed(repo):
    batch = repo / "data/worker_runs/pettripfinder/20260803T235532-remaining-batch"
    S.write_evidence_manifest(S.build_evidence_manifest(batch, repo), batch)
    assert S.verify_evidence_manifest(batch, repo) == []
    (batch / "captures/prop.png").unlink()
    problems = S.verify_evidence_manifest(batch, repo)
    assert any(p.startswith("missing_evidence:") for p in problems)


def test_changed_evidence_is_detected(repo):
    batch = repo / "data/worker_runs/pettripfinder/20260803T235532-remaining-batch"
    S.write_evidence_manifest(S.build_evidence_manifest(batch, repo), batch)
    (batch / "captures/prop.png").write_bytes(b"\x89PNG\r\n\x1a\ndifferent")
    assert any(p.startswith("changed_evidence:")
               for p in S.verify_evidence_manifest(batch, repo))


# --------------------------------------------------------------------------- #
# B. PENDING records.
# --------------------------------------------------------------------------- #

def test_a_pending_record_regenerates_identically(repo):
    rec = _record(repo)
    S.write_pending_records([_Rec(rec)], "20260803T235532-remaining-batch", repo)
    first = S.load_pending_record(rec["hotel_id"], "20260803T235532-remaining-batch", repo)
    S.write_pending_records([_Rec(rec)], "20260803T235532-remaining-batch", repo)
    second = S.load_pending_record(rec["hotel_id"], "20260803T235532-remaining-batch", repo)
    assert first == second
    assert S.rederive_record_hash(first) == rec["record_hash"]
    out = S.records_dir("20260803T235532-remaining-batch", repo)
    assert len(list(out.glob("*.json"))) == 1


def test_only_pending_records_live_in_the_regenerable_store(repo):
    rec = _record(repo, status="APPROVED")
    with pytest.raises(S.StorageError, match="only_pending_review_records"):
        S.write_pending_records([_Rec(rec)], "b", repo)


def test_the_records_location_is_gitignored():
    assert S.RECORDS_ROOT.startswith("data/worker_runs/pettripfinder/")


# --------------------------------------------------------------------------- #
# C. Decisions: tracked, append-only.
# --------------------------------------------------------------------------- #

def test_decisions_are_append_only(repo):
    rec = _record(repo)
    a = S.append_decision(S.empty_decisions(), listing_key="test property",
                          hotel_id=rec["hotel_id"], decision=_decision(rec))
    b = S.append_decision(a, listing_key="test property", hotel_id=rec["hotel_id"],
                          decision=_decision(rec, decision=MR.DECISION_REJECTED,
                                             notes="second look"))
    assert len(a["decisions"]) == 1 and len(b["decisions"]) == 2
    assert b["decisions"][0] == a["decisions"][0]      # the first is untouched
    assert a["decisions"] is not b["decisions"]


def test_a_reversal_is_a_new_entry_and_wins(repo):
    rec = _record(repo)
    store = S.append_decision(S.empty_decisions(), listing_key="test property",
                              hotel_id=rec["hotel_id"], decision=_decision(rec))
    store = S.append_decision(store, listing_key="test property",
                              hotel_id=rec["hotel_id"],
                              decision=_decision(rec, decision=MR.DECISION_REJECTED,
                                                 notes="reversed: fee illegible"))
    assert len(store["decisions"]) == 2
    assert S.latest_decision(store, "test property")["decision"] == "REJECTED"
    assert store["decisions"][0]["decision"] == "APPROVED"


def test_re_appending_the_same_decision_is_idempotent(repo):
    rec = _record(repo)
    d = _decision(rec)
    a = S.append_decision(S.empty_decisions(), listing_key="k",
                          hotel_id=rec["hotel_id"], decision=d)
    b = S.append_decision(a, listing_key="k", hotel_id=rec["hotel_id"], decision=d)
    assert len(b["decisions"]) == 1


def test_a_decision_entry_stores_no_evidence(repo):
    rec = _record(repo)
    store = S.append_decision(S.empty_decisions(), listing_key="k",
                              hotel_id=rec["hotel_id"], decision=_decision(rec))
    entry = store["decisions"][0]
    assert set(entry) == {"listing_key", "hotel_id", "reviewer_id", "reviewed_at",
                          "decision", "field_decisions", "overlap_approved",
                          "notes", "source_record_hash", "approval_hash"}
    body = json.dumps(entry)
    assert "policy_excerpt" not in body and "screenshot" not in body
    assert TEXT not in body and "C:" not in body


# --------------------------------------------------------------------------- #
# D. The tracked index and tracked-file safety.
# --------------------------------------------------------------------------- #

def test_the_index_carries_metadata_only(repo):
    idx = S.build_index([_record(repo)])
    assert idx["schema"] == "atlas-machine-review-index/1.0"
    row = idx["records"][0]
    assert set(row) <= {"hotel_id", "listing_key", "record_hash",
                        "extraction_result_hash", "capture_sha256",
                        "screenshot_sha256", "identity_outcome",
                        "published_overlap", "status", "capture_commit",
                        "normalized_url", "normalized_url_note"}
    body = json.dumps(idx)
    assert "capture_path" not in body and "policy_excerpt" not in body


@pytest.mark.parametrize("url, expected", [
    ("https://www.wyndhamhotels.com/x/overview?CID=LC:abc123:456&iata=0",
     "https://www.wyndhamhotels.com/x/overview"),
    ("https://www.hilton.com/en/hotels/cmhaphx-hampton/?SEO_id=GMB-AMER",
     "https://www.hilton.com/en/hotels/cmhaphx-hampton/"),
])
def test_tracking_parameters_are_stripped_from_indexed_urls(repo, url, expected):
    idx = S.build_index([_record(repo, normalized_url=url)])
    row = idx["records"][0]
    assert row["normalized_url"] == expected
    assert row["normalized_url_note"] == "tracking_query_stripped"


@pytest.mark.parametrize("url", [
    "https://user:pw@example.com/x", "http://127.0.0.1/x", "ftp://example.com/x",
    "https://example.com/x?api_key=AIzaSyA1234567890abcdefghijklmnop",
])
def test_an_unsafe_url_is_omitted_entirely(repo, url):
    row = S.build_index([_record(repo, normalized_url=url)])["records"][0]
    assert "normalized_url" not in row
    assert row["normalized_url_note"]


def test_the_written_tracked_files_pass_the_safety_scan(repo):
    S.write_index(S.build_index([_record(repo)]), repo)
    S.write_decisions(_store(repo, _record(repo)), repo)
    for rel in (S.INDEX_PATH, S.DECISIONS_PATH):
        assert S.tracked_file_problems(repo / rel) == [], rel


def test_the_real_tracked_artifacts_are_clean():
    """The artifacts actually committed, not a fixture."""
    for rel in (S.INDEX_PATH, S.DECISIONS_PATH, S.DECISION_SCHEMA_PATH):
        path = REPO / rel
        if not path.exists():
            pytest.skip("%s not yet written" % rel)
        assert S.tracked_file_problems(path) == [], rel


def test_no_evidence_bytes_or_screenshots_are_tracked():
    """No CAPTURE evidence may be in git, anywhere in the repository.

    Scoped to evidence, not to binaries in general: the launch package ships its
    own site media (``media/*-demo.png``), which is authored artwork and has
    nothing to do with a capture. What must never appear is a capture payload, a
    capture screenshot, a browser profile, or a worker-run tree.
    """
    import subprocess
    tracked = subprocess.run(["git", "ls-files"], cwd=str(REPO),
                             capture_output=True, text=True).stdout.split()
    assert tracked, "expected a tracked file list"
    for path in tracked:
        assert "captures/" not in path, path
        assert ".chrome-profile" not in path, path
        assert not path.startswith("data/worker_runs/"), path
        assert not path.startswith("data/discovery/"), path
    # And the machine-review tracked artifacts specifically carry no bytes.
    for rel in (S.INDEX_PATH, S.DECISIONS_PATH, S.DECISION_SCHEMA_PATH):
        assert not rel.endswith((".png", ".jpg", ".html"))


# --------------------------------------------------------------------------- #
# E. Promotion lookup.
# --------------------------------------------------------------------------- #

def test_promotion_uses_an_approved_decision_on_unchanged_evidence(repo):
    rec = _record(repo)
    store = _store(repo, rec)
    out = S.promotion_lookup("test property", batch_id="20260803T235532-remaining-batch",
                             repo_root=repo, decisions=store)
    assert out["facts"]["pet_fee"] == "$100.00"
    assert out["source_record_hash"] == rec["record_hash"]


def test_promotion_refuses_a_pending_record_with_no_decision(repo):
    rec = _record(repo)
    S.write_pending_records([_Rec(rec)], "20260803T235532-remaining-batch", repo)
    with pytest.raises(S.StorageError, match="no_decision_for"):
        S.promotion_lookup("test property", batch_id="20260803T235532-remaining-batch",
                           repo_root=repo, decisions=S.empty_decisions())


def test_promotion_refuses_a_rejected_decision(repo):
    rec = _record(repo)
    store = _store(repo, rec, decision=MR.DECISION_REJECTED)
    with pytest.raises(S.StorageError, match="decision=REJECTED"):
        S.promotion_lookup("test property", batch_id="20260803T235532-remaining-batch",
                           repo_root=repo, decisions=store)


def test_a_stale_approval_hash_is_refused(repo):
    """Evidence edited after approval must invalidate the approval."""
    rec = _record(repo)
    store = _store(repo, rec)
    tampered = dict(rec, facts={"pets_allowed": "true", "pet_fee": "$5.00"})
    S.write_pending_records([_Rec(tampered)], "20260803T235532-remaining-batch", repo)
    with pytest.raises(S.StorageError, match="stale_or_mismatched_source_hash"):
        S.promotion_lookup("test property", batch_id="20260803T235532-remaining-batch",
                           repo_root=repo, decisions=store)


def test_changed_evidence_invalidates_a_decision(repo):
    rec = _record(repo)
    store = _store(repo, rec)
    (repo / rec["screenshot_path"]).write_bytes(b"\x89PNG\r\n\x1a\ntampered")
    with pytest.raises(S.StorageError, match="changed_evidence"):
        S.promotion_lookup("test property", batch_id="20260803T235532-remaining-batch",
                           repo_root=repo, decisions=store)


def test_changed_capture_text_invalidates_a_decision(repo):
    rec = _record(repo)
    store = _store(repo, rec)
    cap = repo / rec["capture_path"]
    payload = json.loads(cap.read_text(encoding="utf-8"))
    payload["text"] = TEXT + " altered"
    payload["text_sha256"] = _sha(payload["text"])
    cap.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(S.StorageError, match="changed_evidence"):
        S.promotion_lookup("test property", batch_id="20260803T235532-remaining-batch",
                           repo_root=repo, decisions=store)


def test_missing_evidence_fails_promotion_closed(repo):
    rec = _record(repo)
    store = _store(repo, rec)
    (repo / rec["view_path"]).unlink()
    with pytest.raises(S.StorageError, match="missing_evidence"):
        S.promotion_lookup("test property", batch_id="20260803T235532-remaining-batch",
                           repo_root=repo, decisions=store)


def test_compare_only_requires_overlap_approval(repo):
    rec = _record(repo, published_overlap="COMPARE_ONLY")
    plain = _store(repo, rec)
    with pytest.raises(S.StorageError, match="published_overlap_not_specifically_approved"):
        S.promotion_lookup("test property", batch_id="20260803T235532-remaining-batch",
                           repo_root=repo, decisions=plain)
    explicit = _store(repo, rec, overlap_approved=True)
    assert S.promotion_lookup("test property",
                              batch_id="20260803T235532-remaining-batch",
                              repo_root=repo,
                              decisions=explicit)["published_overlap"] == "COMPARE_ONLY"


def test_a_rejected_field_is_withheld(repo):
    rec = _record(repo)
    store = _store(repo, rec, field_decisions={"pet_fee": "REJECTED"})
    out = S.promotion_lookup("test property", batch_id="20260803T235532-remaining-batch",
                             repo_root=repo, decisions=store)
    assert "pet_fee" not in out["facts"] and out["withheld_fields"] == ["pet_fee"]


def test_promotion_never_consults_the_operator_attestation_path():
    import ast
    tree = ast.parse(pathlib.Path(S.__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    assert not any("operator_capture" in name for name in imported)
    used = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert "build_attestation" not in used and "approve_attestation" not in used


# --------------------------------------------------------------------------- #
# Portability and non-interference.
# --------------------------------------------------------------------------- #

def test_restored_evidence_works_under_a_different_repository_root(repo, tmp_path):
    """A record moved to another root resolves without any path rewriting."""
    rec = _record(repo)
    store = _store(repo, rec)
    other = tmp_path / "elsewhere" / "clone"
    import shutil
    shutil.copytree(repo / "data", other / "data")
    S.write_pending_records([_Rec(rec)], "20260803T235532-remaining-batch", other)
    out = S.promotion_lookup("test property", batch_id="20260803T235532-remaining-batch",
                             repo_root=other, decisions=store)
    assert out["source_record_hash"] == rec["record_hash"]
    for field in ("capture_path", "screenshot_path", "view_path"):
        assert not rec[field].startswith(("C:", "/"))


def test_operator_attestation_storage_is_unchanged():
    """The human path keeps its own locations, untouched by any of this."""
    assert "attestation" not in S.RECORDS_ROOT
    assert S.DECISIONS_PATH != "launch_packages/pettripfinder/hotel_worker_approvals.json"
    assert S.INDEX_PATH != "docs/pettripfinder/artifact_indexes/attestation_index.json"
    for rel in ("launch_packages/pettripfinder/hotel_worker_approvals.json",
                "docs/pettripfinder/artifact_indexes/attestation_index.json"):
        assert (REPO / rel).exists(), rel


def test_hotel_policy_facts_is_unchanged():
    package = REPO / "launch_packages/pettripfinder/hotel_policy_facts.json"
    assert len(json.loads(package.read_text(encoding="utf-8"))["hotels"]) == 70


def test_no_deployment_path_is_invoked():
    source = pathlib.Path(S.__file__).read_text(encoding="utf-8")
    for forbidden in ("netlify", "deploy", "assemble_netlify", "subprocess",
                      "requests", "urlopen"):
        assert forbidden not in source, forbidden
