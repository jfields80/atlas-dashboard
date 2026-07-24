"""PETTRIPFINDER-PROD-003 Gate 2 (Stage E) -- promotion-root read-path tests.

Proves the isolated worker-promotion corpus root is wired into the operational
hotel-policy reader (load_hotel_policy_facts, which feeds the exporter only) as a
final, lowest-precedence, additive-only root: it may add a NEW hotel but never
overrides an existing importer record, tolerates absence, never creates a
directory by reading, and never becomes site-generation authority (site
generation still reads only the committed launch package). No test writes to the
real data/import or the committed package.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder import site_data as SD

_REPO = Path(SD.__file__).resolve().parents[2]
_COMMITTED_PACKAGE = _REPO / "launch_packages" / "pettripfinder" / "hotel_policy_facts.json"


def _write_candidate(root: Path, filename: str, name: str, *, recommendation="READY",
                     facts=None, pet_policy="", source_rel="EXACT_ENTITY_DOMAIN") -> None:
    cdir = root / "candidates"
    cdir.mkdir(parents=True, exist_ok=True)
    payload = {
        "candidate_id": filename,
        "recommendation": recommendation,
        "source_relationship": source_rel,
        "proposed_fields": [["name", name], ["source_url", "https://ex/" + filename],
                            ["pet_policy", pet_policy]],
        "pet_facts": sorted((facts or {}).items()),
        "evidence": [{"field": "pets_allowed", "value": "true", "quote": "Pets welcome",
                      "source_url": "https://ex/" + filename}],
        "snapshot": {"observed_at": "2026-07-15"},
    }
    (cdir / (filename + ".json")).write_text(json.dumps(payload), encoding="utf-8")


def _use_roots(monkeypatch, roots, promo):
    monkeypatch.setattr(SD, "WORKER_PROMOTION_ROOT", promo)
    monkeypatch.setattr(SD, "CANDIDATE_ROOTS", tuple(roots))


# --------------------------------------------------------------------------- #
# Wiring shape (real constants).
# --------------------------------------------------------------------------- #

def test_promotion_root_is_final_candidate_root():
    assert SD.CANDIDATE_ROOTS[-1] == SD.WORKER_PROMOTION_ROOT
    assert SD.WORKER_PROMOTION_ROOT.name == "columbus_worker_promotion"
    assert len(SD.CANDIDATE_ROOTS) == 4


def test_promotion_root_is_operational_corpus_not_committed_authority():
    # Worker-promotion candidates live in the gitignored operational corpus tree,
    # never in the committed launch-package tree.
    assert SD.WORKER_PROMOTION_ROOT.parts[-2:] == ("import", "columbus_worker_promotion")
    assert "launch_packages" not in str(SD.WORKER_PROMOTION_ROOT)


# --------------------------------------------------------------------------- #
# Optionality + no directory creation.
# --------------------------------------------------------------------------- #

def test_absent_promotion_root_is_tolerated_and_uncreated(tmp_path, monkeypatch):
    promo = tmp_path / "promo_never"
    _use_roots(monkeypatch, (promo,), promo)
    assert SD.load_hotel_policy_facts() == {}
    assert not promo.exists()                      # reading created nothing


# --------------------------------------------------------------------------- #
# Visibility + READY gate.
# --------------------------------------------------------------------------- #

def test_ready_promotion_candidate_is_visible(tmp_path, monkeypatch):
    promo = tmp_path / "promo"
    _use_roots(monkeypatch, (promo,), promo)
    _write_candidate(promo, "worker-alpha", "Test Hotel Alpha",
                     facts={"pets_allowed": "true", "pet_fee": "$50"}, pet_policy="Pets welcome $50")
    out = SD.load_hotel_policy_facts()
    key = SD.normalize_name("Test Hotel Alpha")
    assert key in out
    assert out[key]["facts"] == {"pets_allowed": "true", "pet_fee": "$50"}
    assert out[key]["evidence_quote"] == "Pets welcome $50"


def test_non_ready_promotion_candidate_excluded(tmp_path, monkeypatch):
    promo = tmp_path / "promo"
    _use_roots(monkeypatch, (promo,), promo)
    _write_candidate(promo, "worker-review", "Held Hotel", recommendation="REVIEW",
                     facts={"pets_allowed": "true"})
    assert SD.normalize_name("Held Hotel") not in SD.load_hotel_policy_facts()


# --------------------------------------------------------------------------- #
# Precedence: additive-only, fail-closed, deterministic.
# --------------------------------------------------------------------------- #

def test_promotion_never_overrides_existing_importer_record(tmp_path, monkeypatch):
    importer, promo = tmp_path / "importer", tmp_path / "promo"
    _use_roots(monkeypatch, (importer, promo), promo)
    _write_candidate(importer, "imp", "Shared Hotel", facts={"pets_allowed": "true", "pet_fee": "$10"})
    _write_candidate(promo, "worker-shared", "Shared Hotel", facts={"pets_allowed": "true", "pet_fee": "$999"})
    out = SD.load_hotel_policy_facts()
    assert out[SD.normalize_name("Shared Hotel")]["facts"]["pet_fee"] == "$10"   # importer wins


def test_intra_promotion_duplicate_sorted_first_wins(tmp_path, monkeypatch):
    promo = tmp_path / "promo"
    _use_roots(monkeypatch, (promo,), promo)
    _write_candidate(promo, "aaa", "Dup Hotel", facts={"pets_allowed": "true", "pet_fee": "$1"})
    _write_candidate(promo, "bbb", "Dup Hotel", facts={"pets_allowed": "true", "pet_fee": "$2"})
    out = SD.load_hotel_policy_facts()
    assert out[SD.normalize_name("Dup Hotel")]["facts"]["pet_fee"] == "$1"       # deterministic first-wins


def test_existing_non_promotion_roots_keep_last_wins(tmp_path, monkeypatch):
    a, b = tmp_path / "a", tmp_path / "b"
    _use_roots(monkeypatch, (a, b), tmp_path / "promo_absent")   # neither a nor b is the promotion root
    _write_candidate(a, "a1", "Order Hotel", facts={"pets_allowed": "true", "pet_fee": "$1"})
    _write_candidate(b, "b1", "Order Hotel", facts={"pets_allowed": "true", "pet_fee": "$2"})
    out = SD.load_hotel_policy_facts()
    assert out[SD.normalize_name("Order Hotel")]["facts"]["pet_fee"] == "$2"      # last root wins (unchanged)


# --------------------------------------------------------------------------- #
# Isolation: runtime never read; committed package is the sole site authority.
# --------------------------------------------------------------------------- #

def test_site_data_never_references_worker_runs():
    src = Path(SD.__file__).read_text(encoding="utf-8")
    assert "worker_runs" not in src
    assert all("worker_runs" not in str(r) for r in SD.CANDIDATE_ROOTS)


def test_site_generation_reads_only_the_committed_package():
    gen = (_REPO / "scripts" / "generate_pettripfinder_columbus_site.py").read_text(encoding="utf-8")
    assert "load_published_hotel_policy_facts" in gen
    assert SD.PUBLISHED_FACTS_PATH == _COMMITTED_PACKAGE
    # the committed package reader is independent of the operational corpus
    assert len(SD.load_published_hotel_policy_facts()) == 5


def test_committed_package_unchanged_by_wiring_and_promotion():
    # The committed launch package is still the pre-promotion 5-record, schema-1.0
    # file: neither the read-path wiring nor the operational promotion writes it.
    pkg = json.loads(_COMMITTED_PACKAGE.read_text(encoding="utf-8"))
    assert pkg["schema_version"] == "1.0"
    assert len(pkg["hotels"]) == 5
