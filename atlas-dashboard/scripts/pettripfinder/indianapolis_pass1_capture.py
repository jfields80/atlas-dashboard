"""PTF-INDIANAPOLIS-ATTENDED-CAPTURE-001 -- drive the official capture runner.

Builds the first 10-row Indianapolis queue from the committed census and
runs ``CaptureRunner`` through a dedicated visible Chrome. Writes captures
only under the gitignored worker tree. Does not attest, approve, publish,
or write Indianapolis policy authority.
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
from services.research_workers.capture_automation.queue import CaptureQueue, QueueEntry
from services.research_workers.capture_automation.runner import CaptureRunner, RunnerConfig
from services.research_workers import vocabulary as V

CENSUS_PATH = (_REPO_ROOT / "launch_packages" / "pettripfinder"
               / "identity_census" / "indianapolis-in.json")
BATCH_DIR = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
             / "indianapolis-attended-capture-001")
WORK_ORDER = "PTF-INDIANAPOLIS-ATTENDED-CAPTURE-001"
BATCH_ID = "indianapolis-pass1-001"

NAMES = (
    "Baymont by Wyndham Plainfield Indianapolis Airport Area",
    "Best Western Plus Indianapolis Northwest",
    "Comfort Inn Indianapolis Airport Plainfield",
    "Comfort Suites Indianapolis Airport",
    "Courtyard by Marriott Indianapolis Airport",
    "Courtyard by Marriott Indianapolis Castleton",
    "Crowne Plaza Indianapolis Airport",
    "Crowne Plaza Indianapolis Downtown Union Station",
    "Delta Hotels by Marriott Indianapolis Airport",
    "Embassy Suites by Hilton Indianapolis Downtown",
)


def build_queue() -> CaptureQueue:
    census = json.loads(CENSUS_PATH.read_text(encoding="utf-8-sig"))
    by_name = {h["canonical_name"]: h for h in census["hotels"]}
    entries = []
    for name in NAMES:
        h = by_name[name]
        entries.append(QueueEntry(
            hotel_id=h["identity_key"],
            listing_key=h["identity_key"],
            hotel_name=h["canonical_name"],
            brand=h["brand"],
            official_url=h["official_url"],
            expected_address=h.get("address") or "",
            expected_city=h["city"],
            expected_state=h["state"],
            expected_postal_code=h.get("postal_code") or "",
            expected_phone=h.get("phone") or "",
            expected_property_code=h.get("property_code") or "",
            market_id="indianapolis-in",
            supported_adapter=h["brand"],
            worker_contract_version=V.CONTRACT_VERSION,
            notes=WORK_ORDER,
        ))
    return CaptureQueue(batch_id=BATCH_ID, entries=tuple(entries),
                        created_at="2026-08-16", schema="ptf-capture-queue/1.1")


def main() -> int:
    queue = build_queue()
    if len(queue) != 10:
        sys.stderr.write("expected 10 entries, got %d\n" % len(queue))
        return 2
    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    started = time.time()
    (BATCH_DIR / "run_started.json").write_text(json.dumps({
        "work_order": WORK_ORDER, "batch_id": BATCH_ID,
        "started_unix": started, "count": len(queue),
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
    (BATCH_DIR / "pass1_runner_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
