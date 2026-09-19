"""pytest plugin (loaded with -p det_probe from outside the checkout; nothing in the
checkout is modified). Writes a line-flushed JSONL of phase timings per test, and at
session end the list of release-factory modules (the 6 the repair changed) that were
ever imported in the test process.

Output path: env DET_PROBE_OUT.
"""
import json
import os
import sys
import time

import pytest

_OUT = os.environ.get("DET_PROBE_OUT")
_CHANGED = {"assemble_production_site", "registration_data_only", "registration_release_lane",
            "regression_delta", "release_coordinator", "release_index"}


def _emit(**row):
    if not _OUT:
        return
    row["t"] = round(time.time(), 3)
    row["at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(_OUT, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_setup(item):
    _emit(event="SETUP_START", node=item.nodeid)
    yield
    _emit(event="SETUP_END", node=item.nodeid)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    _emit(event="CALL_START", node=item.nodeid)
    yield
    _emit(event="CALL_END", node=item.nodeid)


def pytest_runtest_logreport(report):
    _emit(event="REPORT", node=report.nodeid, when=report.when, outcome=report.outcome,
          duration=round(report.duration, 3),
          longrepr_head=(str(report.longrepr).splitlines()[-1][:300] if report.longrepr else None))


def pytest_sessionfinish(session, exitstatus):
    hit = sorted(m for m in sys.modules if m.split(".")[-1] in _CHANGED)
    _emit(event="SESSION_END", exitstatus=int(exitstatus), changed_modules_imported=hit)
