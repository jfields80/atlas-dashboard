"""PTF-INDIANAPOLIS-HILTON-FRESH-SESSION-001.

Drives the six Hilton-family rows in a brand-new Chrome profile.
No Marriott/IHG/Choice pages. Conservative same-brand spacing.
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
    / "indianapolis_hilton_fresh_session_001.json"
)
BATCH_DIR = (
    _REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
    / "indianapolis-hilton-fresh-session-001"
)
WORK_ORDER = "PTF-INDIANAPOLIS-HILTON-FRESH-SESSION-001"
BATCH_ID = "indianapolis-hilton-fresh-001"
HILTON = "hilton"


def build_queue() -> CaptureQueue:
    full = load_queue(QUEUE_PATH, known_brands=known_brands())
    if len(full.entries) != 6:
        raise SystemExit("expected 6 Hilton hotels, got %d" % len(full.entries))
    if any(e.brand != HILTON for e in full.entries):
        raise SystemExit("non-Hilton hotel leaked into the Hilton fresh session")
    return CaptureQueue(
        batch_id=BATCH_ID, entries=full.entries,
        created_at="2026-08-17", schema=full.schema)


def main() -> int:
    queue = build_queue()
    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    started = time.time()
    (BATCH_DIR / "run_started.json").write_text(json.dumps({
        "work_order": WORK_ORDER, "batch_id": BATCH_ID,
        "started_unix": started, "count": len(queue),
        "fresh_profile": True,
        "no_prior_hilton_page_load": True,
    }, indent=2) + "\n", encoding="utf-8")

    # Conservative same-brand spacing. New profile: never reuse Pass 1/2/3A.
    config = RunnerConfig(batch_dir=BATCH_DIR, min_pace=60.0, max_pace=90.0)
    profile_dir = BATCH_DIR / ".chrome-profile-fresh"
    if profile_dir.exists():
        raise SystemExit("fresh profile directory already exists: %s" % profile_dir)
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
    (BATCH_DIR / "hilton_runner_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
