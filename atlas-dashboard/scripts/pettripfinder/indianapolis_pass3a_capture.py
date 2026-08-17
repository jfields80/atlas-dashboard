"""PTF-INDIANAPOLIS-ATTENDED-CAPTURE-PASS3A-001.

Drives the two remaining NON-HILTON rows from
``indianapolis_capture_ready_queue_003.json``. Hilton stays out.
Does not attest, approve, publish, or write Indianapolis policy authority.
"""

from __future__ import annotations

import json
import sys
import time
from collections import OrderedDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from services.research_workers.browser_control import chrome_launcher
from services.research_workers.browser_control.cdp_client import CdpConnection
from services.research_workers.browser_control.live_session import LiveBrowserSession
from services.research_workers.capture_automation.queue import load_queue, CaptureQueue
from services.research_workers.capture_automation.adapters import known_brands
from services.research_workers.capture_automation.runner import CaptureRunner, RunnerConfig

QUEUE_PATH = (
    _REPO_ROOT / "launch_packages" / "pettripfinder"
    / "indianapolis_capture_ready_queue_003.json"
)
BATCH_DIR = (
    _REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
    / "indianapolis-attended-capture-003a"
)
WORK_ORDER = "PTF-INDIANAPOLIS-ATTENDED-CAPTURE-PASS3A-001"
BATCH_ID = "indianapolis-pass3a-001"

SELECTED = (
    "residence inn by marriott indianapolis airport",
    "staybridge suites indianapolis airport plainfield",
)
HILTON = frozenset({"hilton"})


def build_queue() -> CaptureQueue:
    full = load_queue(QUEUE_PATH, known_brands=known_brands())
    by_id = {e.hotel_id: e for e in full.entries}
    missing = [k for k in SELECTED if k not in by_id]
    if missing:
        raise SystemExit("selected hotels missing from queue 003: %s" % missing)
    chosen = [by_id[k] for k in SELECTED]
    if any(e.brand in HILTON for e in chosen):
        raise SystemExit("Hilton hotel leaked into the Pass-3A selection")
    if len(chosen) != 2:
        raise SystemExit("expected 2 selected hotels, got %d" % len(chosen))
    return CaptureQueue(
        batch_id=BATCH_ID, entries=tuple(chosen),
        created_at="2026-08-16", schema=full.schema)


def main() -> int:
    queue = build_queue()
    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    started = time.time()
    (BATCH_DIR / "run_started.json").write_text(json.dumps({
        "work_order": WORK_ORDER, "batch_id": BATCH_ID,
        "started_unix": started, "count": len(queue),
        "selected": list(SELECTED),
    }, indent=2) + "\n", encoding="utf-8")

    config = RunnerConfig(batch_dir=BATCH_DIR)
    profile_dir = BATCH_DIR / ".chrome-profile"
    chrome = chrome_launcher.launch(user_data_dir=profile_dir, window_size="1440,1000")
    print("chrome up on port %d" % chrome.port)
    session = None
    try:
        session = LiveBrowserSession(
            CdpConnection(chrome_launcher.page_websocket_url(chrome.port)))
        result = CaptureRunner(session, config).run(queue)
    finally:
        if session is not None:
            session.close()
        chrome.stop()

    elapsed = time.time() - started
    summary = OrderedDict((
        ("work_order", WORK_ORDER),
        ("batch_id", BATCH_ID),
        ("elapsed_seconds", round(elapsed, 2)),
        ("aborted_reason", result.aborted_reason),
        ("manifest_path", str(result.manifest_path) if result.manifest_path else ""),
        ("counts", result.manifest.get("counts") if result.manifest else {}),
        ("outcomes", [
            {"hotel_id": o.hotel_id, "state": o.state, "reason": o.reason,
             "elapsed_seconds": o.elapsed_seconds}
            for o in result.outcomes
        ]),
    ))
    (BATCH_DIR / "pass3a_runner_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
