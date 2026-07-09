"""
atlas/tests/test_opportunity_v2_bootstrap.py

Focused tests for the AES-008A fix: services/opportunity_v2/bootstrap.py
defines initialize_memory_system() itself (it previously imported a
function of that name from persistence.py, which never existed there
and never could, without introducing a circular import between
persistence.py and learning_memory.py).

Isolation:
  - persistence._STORAGE_FILE is monkeypatched to a tmp_path file so
    tests never read/write the real atlas_learning_memory.json in the
    repo working directory.
  - learning_memory._global_memory is monkeypatched to a fresh
    LearningMemory() per test so tests never see state left behind by
    another test or a prior real boot_atlas() call.
"""

from __future__ import annotations

import json

import services.opportunity_v2.learning_memory as learning_memory_module
import services.opportunity_v2.persistence as persistence_module
from services.opportunity_v2.bootstrap import initialize_memory_system
from services.opportunity_v2.learning_memory import LearningMemory, get_memory


def _isolate_memory(monkeypatch, tmp_path, storage_filename="atlas_learning_memory.json"):
    monkeypatch.setattr(persistence_module, "_STORAGE_FILE", str(tmp_path / storage_filename))
    monkeypatch.setattr(learning_memory_module, "_global_memory", LearningMemory())


def test_initialize_memory_system_with_no_persisted_file_returns_empty_memory(monkeypatch, tmp_path):
    _isolate_memory(monkeypatch, tmp_path)

    memory = initialize_memory_system()

    assert memory.outcomes == []
    assert get_memory().outcomes == []


def test_initialize_memory_system_loads_persisted_outcomes_into_global_memory(monkeypatch, tmp_path):
    _isolate_memory(monkeypatch, tmp_path)

    storage_path = tmp_path / "atlas_learning_memory.json"
    storage_path.write_text(
        json.dumps(
            {
                "outcomes": [
                    {
                        "niche_name": "pet-friendly-travel",
                        "predicted_score": 72.5,
                        "actual_outcome_score": 68.0,
                        "recommendation": "BUILD",
                        "success": True,
                    }
                ]
            }
        )
    )

    memory = initialize_memory_system()

    assert len(memory.outcomes) == 1
    outcome = memory.outcomes[0]
    assert outcome.niche_name == "pet-friendly-travel"
    assert outcome.predicted_score == 72.5
    assert outcome.actual_outcome_score == 68.0
    assert outcome.recommendation == "BUILD"
    assert outcome.success is True

    # get_memory() returns the same live singleton initialize_memory_system populated.
    assert get_memory() is memory


def test_bootstrap_module_imports_successfully():
    """
    Regression guard for the AES-008A symptom: bootstrap.py used to
    import a nonexistent `initialize_memory_system` from persistence.py
    at module load time, so merely importing services.opportunity_v2.
    bootstrap (and therefore app.py) raised ImportError before any
    code ran. This import succeeding is the fix's actual contract.

    Does NOT assert boot_atlas() itself completes without raising —
    boot_atlas() calls memory.success_rate()/average_error(), which do
    not exist on LearningMemory. That is a separate, pre-existing bug
    (tracked as AES-008B) in learning_memory.py, out of scope for this
    fix (which must not modify learning_memory.py).
    """
    import services.opportunity_v2.bootstrap as bootstrap_module

    assert callable(bootstrap_module.boot_atlas)
    assert callable(bootstrap_module.initialize_memory_system)
