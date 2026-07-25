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
