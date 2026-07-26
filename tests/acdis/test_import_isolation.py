import builtins
import importlib
import socket
import sys

import pytest


def test_acdis_import_is_side_effect_free(monkeypatch):
    def fail_open(*args, **kwargs):
        raise AssertionError("unexpected file write during import")

    def fail_network(*args, **kwargs):
        raise AssertionError("unexpected network activity during import")

    monkeypatch.setattr(builtins, "open", fail_open)
    monkeypatch.setattr(socket, "create_connection", fail_network)

    sys.modules.pop("acdis", None)
    module = importlib.import_module("acdis")

    assert module is not None
    assert "pettripfinder" not in sys.modules
    assert "atlas_dashboard" not in sys.modules
    assert "deploy" not in sys.modules
    assert "launch_packages" not in sys.modules


def test_review_import_is_side_effect_free_and_does_not_import_restricted_modules(monkeypatch):
    def fail_open(*args, **kwargs):
        raise AssertionError("unexpected file write during import")

    def fail_network(*args, **kwargs):
        raise AssertionError("unexpected network activity during import")

    monkeypatch.setattr(builtins, "open", fail_open)
    monkeypatch.setattr(socket, "create_connection", fail_network)

    before_import = set(sys.modules)

    for module_name in ["acdis.review", "acdis.review.builder", "acdis.review.validation", "acdis.review.markdown"]:
        sys.modules.pop(module_name, None)

    review_module = importlib.import_module("acdis.review")
    assert review_module is not None

    after_import = set(sys.modules)
    newly_loaded = after_import - before_import

    restricted_prefixes = [
        "sqlite3",
        "requests",
        "urllib3",
        "playwright",
        "selenium",
        "openai",
        "anthropic",
        "google.generativeai",
        "pettripfinder",
        "atlas_dashboard",
        "deploy",
    ]
    for prefix in restricted_prefixes:
        assert not any(name == prefix or name.startswith(prefix + ".") for name in newly_loaded)
