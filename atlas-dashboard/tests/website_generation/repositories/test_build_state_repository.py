"""Build-state repository tests (AES-WEB-001 §9.2, §6.4-§6.5, §6.8).

Covers: build creation, append-only transitions, latest checkpoint,
deterministic stored collections, persistence across repository reload,
and the cancellation/escalation/override foundation. Temp SQLite files
only.
"""

from __future__ import annotations

import pytest

from repositories.build_state_repository import BuildStateRepository

BUILD_ID = "d" * 64
SPEC_HASH = "e" * 64
T0 = "2026-07-11T00:00:00Z"
T1 = "2026-07-11T00:00:01Z"
T2 = "2026-07-11T00:00:02Z"


@pytest.fixture
def repo(tmp_path):
    repository = BuildStateRepository(tmp_path / "wge_builds.sqlite3")
    yield repository
    repository.close()


def _create(repo) -> dict:
    return repo.create_build(
        build_id=BUILD_ID,
        spec_hash=SPEC_HASH,
        pipeline_version="1.0.0",
        initial_state="INITIALIZED",
        created_at=T0,
    )


class TestBuilds:
    def test_create_build(self, repo):
        build = _create(repo)
        assert build["build_id"] == BUILD_ID
        assert build["current_state"] == "INITIALIZED"
        assert build["attempt"] == 1
        assert build["cancelled"] == 0

    def test_get_missing_build_returns_none(self, repo):
        assert repo.get_build("missing") is None

    def test_set_current_state(self, repo):
        _create(repo)
        repo.set_current_state(BUILD_ID, "SPEC_COMPILED", attempt=1)
        assert repo.get_build(BUILD_ID)["current_state"] == "SPEC_COMPILED"


class TestTransitions:
    def test_append_and_list_in_order(self, repo):
        _create(repo)
        repo.append_transition(
            BUILD_ID, "INITIALIZED", "SPEC_COMPILED", "SUCCESS", 1, T1
        )
        repo.append_transition(
            BUILD_ID, "SPEC_COMPILED", "BRAND_RESOLVED", "SUCCESS", 1, T2
        )
        rows = repo.list_transitions(BUILD_ID)
        assert [(r["from_state"], r["to_state"]) for r in rows] == [
            ("INITIALIZED", "SPEC_COMPILED"),
            ("SPEC_COMPILED", "BRAND_RESOLVED"),
        ]

    def test_transition_history_is_append_only(self, repo):
        # The repository exposes no update/delete for transitions; new
        # appends never disturb earlier rows or their identifiers.
        _create(repo)
        first_id = repo.append_transition(
            BUILD_ID, "INITIALIZED", "SPEC_COMPILED", "SUCCESS", 1, T1
        )
        before = repo.list_transitions(BUILD_ID)
        repo.append_transition(
            BUILD_ID, "SPEC_COMPILED", "BRAND_RESOLVED", "SUCCESS", 1, T2
        )
        after = repo.list_transitions(BUILD_ID)
        assert after[0] == before[0]
        assert after[0]["transition_id"] == first_id
        assert len(after) == len(before) + 1
        assert not hasattr(repo, "update_transition")
        assert not hasattr(repo, "delete_transition")


class TestCheckpoints:
    def test_latest_checkpoint(self, repo):
        _create(repo)
        repo.record_checkpoint(
            BUILD_ID, "SPEC_COMPILED", 1, {"business_spec": SPEC_HASH},
            {"business_spec_compiler": "1.0.0"}, T1,
        )
        repo.record_checkpoint(
            BUILD_ID, "BRAND_RESOLVED", 1,
            {"business_spec": SPEC_HASH, "brand_package": "f" * 64},
            {"business_spec_compiler": "1.0.0", "brand_engine": "1.0.0"}, T2,
        )
        checkpoint = repo.latest_checkpoint(BUILD_ID)
        assert checkpoint["state"] == "BRAND_RESOLVED"
        assert checkpoint["artifact_hashes"] == {
            "business_spec": SPEC_HASH,
            "brand_package": "f" * 64,
        }
        assert checkpoint["engine_versions"]["brand_engine"] == "1.0.0"

    def test_latest_checkpoint_none_when_empty(self, repo):
        _create(repo)
        assert repo.latest_checkpoint(BUILD_ID) is None

    def test_stored_collections_are_deterministic(self, repo, tmp_path):
        # Same collections in different insertion orders serialize to
        # identical stored JSON (canonical sorted-key serialization).
        _create(repo)
        repo.record_checkpoint(
            BUILD_ID, "SPEC_COMPILED", 1,
            {"b": "2" * 64, "a": "1" * 64}, {"y": "1.0.0", "x": "2.0.0"}, T1,
        )
        repo.record_checkpoint(
            BUILD_ID, "SPEC_COMPILED", 1,
            {"a": "1" * 64, "b": "2" * 64}, {"x": "2.0.0", "y": "1.0.0"}, T1,
        )
        import sqlite3

        conn = sqlite3.connect(str(tmp_path / "wge_builds.sqlite3"))
        rows = conn.execute(
            "SELECT artifact_hashes_json, engine_versions_json "
            "FROM wge_checkpoints ORDER BY checkpoint_id"
        ).fetchall()
        conn.close()
        assert rows[0] == rows[1]


class TestPersistence:
    def test_state_survives_repository_reload(self, tmp_path):
        db_path = tmp_path / "wge_builds.sqlite3"
        first = BuildStateRepository(db_path)
        first.create_build(BUILD_ID, SPEC_HASH, "1.0.0", "INITIALIZED", T0)
        first.append_transition(
            BUILD_ID, "INITIALIZED", "SPEC_COMPILED", "SUCCESS", 1, T1
        )
        first.record_checkpoint(
            BUILD_ID, "SPEC_COMPILED", 1, {"business_spec": SPEC_HASH},
            {"business_spec_compiler": "1.0.0"}, T1,
        )
        first.close()

        reloaded = BuildStateRepository(db_path)
        try:
            assert reloaded.get_build(BUILD_ID)["spec_hash"] == SPEC_HASH
            assert len(reloaded.list_transitions(BUILD_ID)) == 1
            assert (
                reloaded.latest_checkpoint(BUILD_ID)["state"]
                == "SPEC_COMPILED"
            )
        finally:
            reloaded.close()


class TestCancellationAndEscalation:
    def test_mark_cancelled(self, repo):
        _create(repo)
        repo.mark_cancelled(BUILD_ID, "operator request")
        build = repo.get_build(BUILD_ID)
        assert build["cancelled"] == 1
        assert build["cancel_reason"] == "operator request"

    def test_escalation_foundation(self, repo):
        _create(repo)
        escalation_id = repo.record_escalation(
            BUILD_ID, "content_drafting", "slots unfilled",
            {"slots": ["hero"]}, T1,
        )
        rows = repo.list_escalations(BUILD_ID)
        assert len(rows) == 1
        assert rows[0]["escalation_id"] == escalation_id
        assert rows[0]["resolved"] == 0

    def test_override_foundation(self, repo):
        _create(repo)
        escalation_id = repo.record_escalation(
            BUILD_ID, "gating", "warning override", {}, T1
        )
        repo.record_override(
            BUILD_ID, escalation_id, "operator accepted warning", T2
        )
        rows = repo.list_overrides(BUILD_ID)
        assert len(rows) == 1
        assert rows[0]["escalation_id"] == escalation_id
        assert rows[0]["justification"] == "operator accepted warning"
