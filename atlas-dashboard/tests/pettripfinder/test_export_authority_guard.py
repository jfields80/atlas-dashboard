"""PTF-EXPORT -- the legacy export writer may never regress the committed authority.

Records approved through machine review are promoted by a separately reviewed
process and are absent from this exporter's candidate corpus. Rebuilding from
that corpus alone therefore produces a SMALLER package which, written blindly,
deletes published hotels. The guard converts that silent overwrite into a
fail-closed error at the write itself.

The synthetic cases below exercise the generic comparison without touching the
market corpus; the Columbus cases prove the real 70 -> 38 refusal and skip
cleanly wherever the gitignored operational corpus is absent.
"""

from __future__ import annotations

import hashlib
import json
import pathlib

import pytest

from scripts.pettripfinder.export_hotel_policy_facts import (
    AuthorityRegressionError,
    authority_delta,
    build_package,
    build_preview,
    is_destructive,
    serialize,
    write_package,
)
from scripts.pettripfinder.site_data import PUBLISHED_FACTS_PATH

_REPO = pathlib.Path(__file__).resolve().parents[2]


def _pkg(*keys, **overrides):
    """A minimal synthetic authority keyed by stable hotel identity."""
    return {"schema_version": "1.1", "hotels": [
        {"key": k, "facts": overrides.get(k, {"pets_allowed": "true"})} for k in keys]}


def _text(pkg):
    return serialize(pkg)


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------- #
# Generic guard, synthetic authorities.
# --------------------------------------------------------------------------- #

class TestGenericGuard:
    def test_identical_rebuild_is_not_destructive(self):
        d = authority_delta(_text(_pkg("a", "b")), _text(_pkg("a", "b")))
        assert d["identical"] and not is_destructive(d)
        assert d["removal_count"] == 0 and d["unintended_update_count"] == 0

    def test_pure_addition_is_allowed(self):
        d = authority_delta(_text(_pkg("a")), _text(_pkg("a", "b")))
        assert not is_destructive(d)
        assert d["additions"] == ["b"] and d["removals"] == []

    def test_removal_is_destructive_and_named(self):
        d = authority_delta(_text(_pkg("a", "b")), _text(_pkg("a")))
        assert is_destructive(d)
        assert d["removals"] == ["b"] and d["removal_count"] == 1
        assert d["count_regression"] is True
        assert d["unrepresented_existing"] == ["b"]

    def test_changed_record_is_an_unintended_update(self):
        d = authority_delta(_text(_pkg("a", "b")),
                            _text(_pkg("a", "b", b={"pets_allowed": "false"})))
        assert is_destructive(d)
        assert d["unintended_updates"] == ["b"]

    def test_duplicate_identities_fail_closed(self):
        dup = {"schema_version": "1.1", "hotels": [{"key": "a"}, {"key": "a"}]}
        d = authority_delta(_text(_pkg("a")), _text(dup))
        assert d["duplicate_identities"] == ["a"]
        assert is_destructive(d)

    def test_hashes_and_counts_are_reported(self):
        old, new = _text(_pkg("a", "b")), _text(_pkg("a"))
        d = authority_delta(old, new)
        assert d["existing_count"] == 2 and d["proposed_count"] == 1
        assert d["existing_sha256"] == hashlib.sha256(old.encode("utf-8")).hexdigest()
        assert d["proposed_sha256"] == hashlib.sha256(new.encode("utf-8")).hexdigest()

    def test_report_is_deterministic_and_bounded(self):
        many = _pkg(*["h%02d" % i for i in range(40)])
        d = authority_delta(_text(many), _text(_pkg("h00")))
        msg = AuthorityRegressionError(d).args[0]
        assert msg == AuthorityRegressionError(d).args[0]      # deterministic
        listed = [l for l in msg.splitlines() if l.strip().startswith("- h")]
        assert len(listed) == 20                                # bounded
        assert "and 19 more" in msg
        assert "corpus is INCOMPLETE" in msg


# --------------------------------------------------------------------------- #
# The writer itself, against a temporary authority file.
# --------------------------------------------------------------------------- #

class TestWriterRefusal:
    def test_refusal_leaves_the_target_byte_identical(self, tmp_path, monkeypatch):
        target = tmp_path / "hotel_policy_facts.json"
        # An existing authority holding a record the corpus cannot rebuild.
        existing = _text(_pkg("only-in-authority"))
        target.write_text(existing, encoding="utf-8", newline="\n")
        before = target.read_bytes()
        monkeypatch.setattr(
            "scripts.pettripfinder.export_hotel_policy_facts.build_package",
            lambda: _pkg("something-else"))
        with pytest.raises(AuthorityRegressionError) as exc:
            write_package(target)
        assert "only-in-authority" in str(exc.value)
        assert target.read_bytes() == before

    def test_refusal_leaves_no_temporary_file(self, tmp_path, monkeypatch):
        target = tmp_path / "hotel_policy_facts.json"
        target.write_text(_text(_pkg("a", "b")), encoding="utf-8", newline="\n")
        monkeypatch.setattr(
            "scripts.pettripfinder.export_hotel_policy_facts.build_package",
            lambda: _pkg("a"))
        with pytest.raises(AuthorityRegressionError):
            write_package(target)
        assert sorted(p.name for p in tmp_path.iterdir()) == ["hotel_policy_facts.json"]

    def test_byte_identical_rebuild_is_permitted(self, tmp_path, monkeypatch):
        target = tmp_path / "hotel_policy_facts.json"
        pkg = _pkg("a", "b")
        target.write_text(_text(pkg), encoding="utf-8", newline="\n")
        before = target.read_bytes()
        monkeypatch.setattr(
            "scripts.pettripfinder.export_hotel_policy_facts.build_package", lambda: pkg)
        assert write_package(target) == 0
        assert target.read_bytes() == before

    def test_additive_write_is_permitted(self, tmp_path, monkeypatch):
        target = tmp_path / "hotel_policy_facts.json"
        target.write_text(_text(_pkg("a")), encoding="utf-8", newline="\n")
        monkeypatch.setattr(
            "scripts.pettripfinder.export_hotel_policy_facts.build_package",
            lambda: _pkg("a", "b"))
        assert write_package(target) == 0
        assert {h["key"] for h in json.loads(target.read_text(encoding="utf-8"))["hotels"]} == {"a", "b"}

    def test_first_write_to_an_absent_authority_is_permitted(self, tmp_path, monkeypatch):
        target = tmp_path / "hotel_policy_facts.json"
        monkeypatch.setattr(
            "scripts.pettripfinder.export_hotel_policy_facts.build_package",
            lambda: _pkg("a"))
        assert write_package(target) == 0

    def test_authorization_must_name_the_exact_delta(self, tmp_path, monkeypatch):
        target = tmp_path / "hotel_policy_facts.json"
        target.write_text(_text(_pkg("a", "b", "c")), encoding="utf-8", newline="\n")
        monkeypatch.setattr(
            "scripts.pettripfinder.export_hotel_policy_facts.build_package",
            lambda: _pkg("a"))
        # Naming only part of the delta is not authorisation.
        with pytest.raises(AuthorityRegressionError):
            write_package(target, authorized_delta={"removals": ["b"]})
        # Naming it exactly is.
        assert write_package(target, authorized_delta={
            "removals": ["b", "c"], "unintended_updates": []}) == 0

    def test_authorization_cannot_wave_through_duplicates(self, tmp_path, monkeypatch):
        target = tmp_path / "hotel_policy_facts.json"
        target.write_text(_text(_pkg("a")), encoding="utf-8", newline="\n")
        monkeypatch.setattr(
            "scripts.pettripfinder.export_hotel_policy_facts.build_package",
            lambda: {"schema_version": "1.1", "hotels": [{"key": "a"}, {"key": "a"}]})
        with pytest.raises(AuthorityRegressionError):
            write_package(target, authorized_delta={"removals": [], "unintended_updates": []})

    def test_no_force_flag_exists(self):
        """No command-line escape hatch. Prose may mention the absent flag; an
        argparse argument declaring it is what must not exist."""
        from scripts.pettripfinder import export_hotel_policy_facts as EX
        src = (_REPO / "scripts" / "pettripfinder" /
               "export_hotel_policy_facts.py").read_text(encoding="utf-8")
        for spelling in ('add_argument("--force', "add_argument('--force",
                         'add_argument("--overwrite', 'add_argument("--yes'):
            assert spelling not in src
        with pytest.raises(SystemExit):
            EX.main(["--force"])


# --------------------------------------------------------------------------- #
# The real Columbus divergence.
# --------------------------------------------------------------------------- #

def _corpus_present():
    try:
        return len(build_package()["hotels"]) > 0
    except Exception:                                    # pragma: no cover
        return False


_CORPUS = _corpus_present()
_SKIP = pytest.mark.skipif(not _CORPUS, reason="operational export corpus absent (gitignored)")


@_SKIP
class TestColumbusDivergence:
    def test_preview_remains_available_and_read_only(self):
        before = PUBLISHED_FACTS_PATH.read_bytes()
        report = build_preview()["report"]
        assert report["old_count"] == 81
        assert report["new_count"] == 38
        assert PUBLISHED_FACTS_PATH.read_bytes() == before

    def test_export_refuses_the_destructive_replacement(self):
        delta = authority_delta(PUBLISHED_FACTS_PATH.read_text(encoding="utf-8"),
                                serialize(build_package()))
        assert is_destructive(delta)
        assert delta["existing_count"] == 81 and delta["proposed_count"] == 38

    def test_every_removal_identity_is_reported(self):
        delta = authority_delta(PUBLISHED_FACTS_PATH.read_text(encoding="utf-8"),
                                serialize(build_package()))
        assert delta["removal_count"] == 43
        assert len(delta["removals"]) == 43
        published = {h["key"] for h in json.loads(
            PUBLISHED_FACTS_PATH.read_text(encoding="utf-8"))["hotels"]}
        assert set(delta["removals"]) <= published

    def test_every_unintended_update_is_reported(self):
        delta = authority_delta(PUBLISHED_FACTS_PATH.read_text(encoding="utf-8"),
                                serialize(build_package()))
        assert delta["unintended_update_count"] == 10
        assert len(delta["unintended_updates"]) == 10

    def test_the_committed_authority_survives_a_refused_write(self):
        before = PUBLISHED_FACTS_PATH.read_bytes()
        with pytest.raises(AuthorityRegressionError):
            write_package()
        assert PUBLISHED_FACTS_PATH.read_bytes() == before

    def test_the_cli_refuses_without_writing(self, capsys):
        from scripts.pettripfinder import export_hotel_policy_facts as EX
        before = PUBLISHED_FACTS_PATH.read_bytes()
        assert EX.main([]) == 2
        assert PUBLISHED_FACTS_PATH.read_bytes() == before
        assert "REFUSED" in capsys.readouterr().err

    def test_the_machine_review_path_remains_separate_and_intact(self):
        """The promoted records live in the authority and are NOT reachable
        through the export corpus -- which is precisely why the guard exists."""
        published = {h["key"] for h in json.loads(
            PUBLISHED_FACTS_PATH.read_text(encoding="utf-8"))["hotels"]}
        corpus = {h["key"] for h in build_package()["hotels"]}
        promoted_only = published - corpus
        assert len(promoted_only) == 43
        # Every promoted record still carries auditable provenance. There are
        # now two ways in that the export corpus cannot reach, and each is
        # recorded as what it actually was: the machine-review approvals, and
        # the PTF-COLUMBUS-AUTHORITY-APPLY-002 records promoted from attended
        # browser-assisted captures. Accepting either is the point -- stamping
        # a machine_review block on a record no machine reviewed would make
        # this assertion pass by lying about how the hotel got here.
        by_key = {h["key"]: h for h in json.loads(
            PUBLISHED_FACTS_PATH.read_text(encoding="utf-8"))["hotels"]}
        for key in promoted_only:
            record = by_key[key]
            provenance = (record.get("machine_review", {}).get("approval_hash")
                          or record.get("attended_capture", {}).get("html_sha256"))
            assert provenance and provenance.startswith("sha256:"), key
