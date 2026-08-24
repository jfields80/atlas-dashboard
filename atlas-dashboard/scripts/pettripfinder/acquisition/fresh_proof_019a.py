"""PTF-CANONICAL-POLICY-LOCATOR-FRESH-PROOF-019A -- the proof 019 could not run.

019 established the contract: a capture RECORDS the boundary its own locator
chose (``locator.json`` beside ``policy-block.txt``) and a replay reads the
block and verifies it, rather than locating again. It proved that offline,
through the production persist function, across 143 already-persisted captures.

What it could not do was prove it end to end on a FRESH acquisition, because no
provider credential was set in that environment. 019 recorded that honestly as
``BLOCKED_NO_PROVIDER_CREDENTIAL`` instead of downgrading it to something that
passed. This module is the outstanding half, and nothing else:

    live production capture
      -> persist policy-block.txt
      -> persist locator.json
      -> offline replay from disk
      -> byte-identical policy block
      -> block hash and document hash verified
      -> zero provider calls during the replay
      -> a temporarily tampered COPY returns HASH_MISMATCH

WHAT THIS DELIBERATELY DOES NOT DO
----------------------------------
It changes no route, no reader and no locator. It publishes nothing and writes
no market authority. It re-acquires four properties that were already acquired
at publication grade, because the point is the ARTIFACT CONTRACT and not the
facts -- re-measuring facts that three pilots already settled would learn
nothing and would spend money to learn it.

THE COHORT IS PINNED, NOT SELECTED
----------------------------------
Four properties, one per lane in service, named literally below. They are
cross-checked against the committed Milwaukee acquisition queue before a single
call is made: if the queue's URL or brand for one of them has moved, this run
STOPS rather than quietly proving the contract against a different page. A
proof whose subject can drift is not a proof.

    CHOICE                Cambria Hotel Milwaukee Downtown            firecrawl
    WYNDHAM               Ambassador Hotel Milwaukee, Trademark ...   firecrawl
    IHG                   avid hotels Milwaukee West - Waukesha       firecrawl
    GENERIC/INDEPENDENT   Cobblestone Hotel & Suites - Waukesha/...   browser

Three of the four take the Firecrawl lane and one takes the Bright Data Browser
API. That is what the registry says today and this module asserts it rather
than choosing it, so a route edit fails this proof instead of passing it.

HOW "ZERO PROVIDER CALLS DURING REPLAY" IS ESTABLISHED
------------------------------------------------------
Not by inspection. The replay runs inside a guard that makes an outbound socket
connection, a subprocess launch, and every capture module's entry point raise.
A replay that reached a provider would fail loudly rather than be described as
not having done so. Vendor-side billing telemetry is read BEFORE and AFTER that
window -- never inside it -- and is reported as corroboration.

COST
----
Bright Data is billed as month-to-date cost summed over every billable zone,
which is monotonic and immune to a top-up; the account balance is not a cost
meter and is not used as one. Firecrawl is billed in plan credits and reports
no unit price, so credits are reported as credits. The two are never summed:
there is no honest exchange rate between them.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import hashlib
import json
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import firecrawl_capture as FC   # noqa: E402
from scripts.pettripfinder.acquisition import providers as PROVIDERS    # noqa: E402
from scripts.pettripfinder.acquisition import registry as REGISTRY      # noqa: E402
from scripts.pettripfinder.acquisition import router as ROUTER          # noqa: E402
from scripts.pettripfinder.brightdata import client as CLIENT           # noqa: E402
from scripts.pettripfinder.brightdata import corpus as CORPUS           # noqa: E402
from scripts.pettripfinder.brightdata import cross_brand_capture as CBC  # noqa: E402
from scripts.pettripfinder.brightdata import cross_brand_pilot_002 as P2  # noqa: E402
from scripts.pettripfinder.brightdata import policy_locator as PL       # noqa: E402
from scripts.pettripfinder.brightdata import unlocker_capture as UC     # noqa: E402

WORK_ORDER = "PTF-CANONICAL-POLICY-LOCATOR-FRESH-PROOF-019A"
RUN_ID = "locator-fresh-proof-019a"
MARKET = "milwaukee-wi"

PKG = REPO / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
QUEUE_PATH = REPORTS / ("%s_policy_acquisition_queue_001.json" % MARKET)
REPORT = REPORTS / "ptf_locator_fresh_proof_019a.json"

#: Captures land under the gitignored data tree, as every capture does. They
#: carry provider responses and must not enter version control.
RUN_ROOT = REPO / "data" / "acquisition" / RUN_ID

#: Bright Data bills per zone. All three are read because spend on any of them
#: is spend on this work order.
BILLABLE_ZONES = ("scraping_browser1", "mcp_unlocker", "cli_unlocker")

DOCUMENT = "rendered.html"


# --------------------------------------------------------------------------- #
# The cohort. Named, not chosen.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class CohortProperty:
    """One pinned subject of the proof, and the lane it must take.

    ``expected_provider`` is asserted rather than read back from the registry,
    for the same reason the router smoke test asserts its routes: a registry
    edit that silently moves Choice into the Browser API should fail a proof,
    not pass one.
    """

    lane: str
    identity_key: str
    canonical_name: str
    brand: str
    official_url: str
    expected_provider: str
    expected_reader: str


COHORT: Tuple[CohortProperty, ...] = (
    CohortProperty(
        lane="CHOICE",
        identity_key="cambria hotel milwaukee downtown",
        canonical_name="Cambria Hotel Milwaukee Downtown",
        brand="CHOICE",
        official_url="https://www.choicehotels.com/wisconsin/milwaukee/"
                     "cambria-hotels/wi297",
        expected_provider=PROVIDERS.FIRECRAWL,
        expected_reader="choice_static"),
    CohortProperty(
        lane="WYNDHAM",
        identity_key="ambassador hotel milwaukee trademark collection by wyndham",
        canonical_name="Ambassador Hotel Milwaukee, Trademark Collection by Wyndham",
        brand="WYNDHAM",
        official_url="https://www.wyndhamhotels.com/trademark/"
                     "milwaukee-wisconsin/ambassador-hotel-trademark-collection/"
                     "overview",
        expected_provider=PROVIDERS.FIRECRAWL,
        expected_reader="wyndham"),
    CohortProperty(
        lane="IHG",
        identity_key="avid hotels milwaukee west waukesha",
        canonical_name="avid hotels Milwaukee West - Waukesha",
        brand="IHG",
        official_url="https://www.ihg.com/avidhotels/hotels/us/en/waukesha/"
                     "mkeav/hoteldetail",
        expected_provider=PROVIDERS.FIRECRAWL,
        expected_reader="ihg"),
    CohortProperty(
        lane="GENERIC_INDEPENDENT",
        identity_key="cobblestone hotel and suites waukesha west milwaukee",
        canonical_name="Cobblestone Hotel & Suites - Waukesha/West Milwaukee",
        brand="INDEP:staycobblestone.com",
        official_url="https://staycobblestone.com/wi/waukesha/",
        expected_provider=PROVIDERS.BRIGHTDATA_BROWSER,
        expected_reader="generic"),
)

PASS_BAR = len(COHORT)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _repo_relative(path: Path) -> str:
    """A path as the report should name it: repo-relative, forward slashes.

    Falls back to the absolute path rather than raising, so a caller pointing
    at a directory outside the repository still gets a readable row.
    """
    resolved = Path(path).resolve()
    try:
        return str(resolved.relative_to(REPO)).replace("\\", "/")
    except ValueError:
        return str(resolved).replace("\\", "/")


# --------------------------------------------------------------------------- #
# Preflight: the subject, the lane, and the credential -- in that order.
# --------------------------------------------------------------------------- #

def provider_health() -> Dict:
    """What each lane reports about itself. No credential value is read here.

    ``describe`` returns the health DETAIL, which names the environment
    variable and the pinned exit geography and never the secret behind them.
    """
    described = PROVIDERS.describe()
    return {pid: {"product": info["product"],
                  "implemented": info["implemented"],
                  "available": info["health"]["available"],
                  "detail": info["health"]["detail"]}
            for pid, info in described.items()}


def queue_rows() -> Dict[str, Dict]:
    doc = json.loads(QUEUE_PATH.read_text(encoding="utf-8-sig"))
    return {row["identity_key"]: row for row in doc["items"]}


def verify_cohort() -> Dict:
    """The pinned cohort still IS what the committed queue says it is.

    Checked before anything is fetched. A property that has been re-URLed or
    re-branded since the cohort was fixed is a different subject, and proving
    the contract against a different subject is not completing this proof.
    """
    rows = queue_rows()
    checks: List[Dict] = []
    for prop in COHORT:
        row = rows.get(prop.identity_key)
        problems: List[str] = []
        if row is None:
            problems.append("not present in the committed acquisition queue")
        else:
            if row["canonical_name"] != prop.canonical_name:
                problems.append("queue names it %r" % row["canonical_name"])
            if row["brand"] != prop.brand:
                problems.append("queue brands it %r" % row["brand"])
            if row["official_url"] != prop.official_url:
                problems.append("queue URL is %r" % row["official_url"])
            if row.get("brand_excluded"):
                problems.append("the queue marks this brand excluded")
        checks.append({"lane": prop.lane, "identity_key": prop.identity_key,
                       "matches_committed_queue": not problems,
                       "problems": problems})
    return {"cohort_size": len(COHORT),
            "all_match_committed_queue": all(c["matches_committed_queue"]
                                             for c in checks),
            "checks": checks}


def verify_routes() -> Dict:
    """Every lane resolves where the registry left it. Asserted, never chosen."""
    checks: List[Dict] = []
    for prop in COHORT:
        route = REGISTRY.resolve(brand=prop.brand, url=prop.official_url,
                                 identity_key=prop.identity_key)
        ok = (route.provider == prop.expected_provider
              and route.reader == prop.expected_reader)
        checks.append({
            "lane": prop.lane,
            "expected_provider": prop.expected_provider,
            "resolved_provider": route.provider,
            "expected_reader": prop.expected_reader,
            "resolved_reader": route.reader,
            "ladder": list(route.ladder),
            "forbidden_providers": sorted(getattr(route, "forbidden_providers",
                                                  ()) or ()),
            "as_registered": ok})
    return {"all_routes_as_registered": all(c["as_registered"] for c in checks),
            "checks": checks}


def preflight() -> Dict:
    """Everything that must hold before a cent is spent."""
    health = provider_health()
    cohort = verify_cohort()
    routes = verify_routes()
    needed = sorted({p.expected_provider for p in COHORT})
    lanes_up = {pid: health[pid]["available"] for pid in needed}
    return {
        "checked_at": _now(),
        "provider_health": health,
        "providers_this_proof_needs": needed,
        "needed_lanes_available": lanes_up,
        "cohort": cohort,
        "routes": routes,
        "runnable": (all(lanes_up.values())
                     and cohort["all_match_committed_queue"]
                     and routes["all_routes_as_registered"]),
    }


# --------------------------------------------------------------------------- #
# Vendor-side spend. Read outside the replay window, never inside it.
# --------------------------------------------------------------------------- #

def read_spend(label: str) -> Dict:
    """Month-to-date cost per billable zone, plus the Firecrawl credit balance.

    Deliberately NOT the account balance: it lags, and it RISES on a top-up, so
    a balance delta can report a spend of zero or a negative spend for a run
    that cost money. Per-zone month-to-date cost only moves one way.
    """
    zones: Dict[str, Optional[int]] = {}
    for zone in BILLABLE_ZONES:
        snap = CLIENT.read_usage("%s:%s" % (label, zone), zone=zone)
        zones[zone] = snap.cost_month_usd_minor
    try:
        credits = FC.credits_remaining()
    except Exception:                                            # noqa: BLE001
        credits = None
    return {"label": label, "read_at": _now(),
            "brightdata_zone_cost_month_usd_minor": zones,
            "firecrawl_credits_remaining": credits}


def spend_delta(before: Dict, after: Dict) -> Dict:
    """What this run added. Two currencies, never mixed into one number.

    A ZERO HERE IS NOT AUTOMATICALLY A ZERO SPEND. Bright Data's month-to-date
    cost is an aggregate that settles behind the traffic that produced it; over
    a run that lasts a minute it can report the same figure before and after a
    session that plainly moved megabytes. So the delta is reported alongside
    ``brightdata_meter_moved``, and a caller that needs the real figure re-reads
    the meter later (``--cost-followup``) rather than banking the zero.
    """
    zones: Dict[str, Optional[int]] = {}
    total: Optional[int] = 0
    for zone in BILLABLE_ZONES:
        a = before["brightdata_zone_cost_month_usd_minor"].get(zone)
        b = after["brightdata_zone_cost_month_usd_minor"].get(zone)
        if a is None or b is None:
            zones[zone] = None
            total = None                # unknown is not zero, ever
            continue
        zones[zone] = max(0, b - a)
        if total is not None:
            total += zones[zone]
    ca = before.get("firecrawl_credits_remaining")
    cb = after.get("firecrawl_credits_remaining")
    credits = (ca - cb) if (ca is not None and cb is not None) else None
    return {
        "brightdata_usd_minor_by_zone": zones,
        "brightdata_usd_minor_total": total,
        "brightdata_meter_moved": bool(total),
        "firecrawl_credits_consumed": credits,
        "window_seconds": _window_seconds(before, after),
        "note": ("Bright Data bills dollars and Firecrawl bills plan credits. "
                 "The Firecrawl plan endpoint reports an allowance and not a "
                 "unit price, so the two are reported side by side and never "
                 "summed. A None is an unreadable meter and must not be read "
                 "as a zero, and a zero over a short window is an unsettled "
                 "meter rather than a measured absence of spend."),
    }


def _window_seconds(before: Dict, after: Dict) -> Optional[float]:
    try:
        a = datetime.fromisoformat(before["read_at"])
        b = datetime.fromisoformat(after["read_at"])
    except (KeyError, TypeError, ValueError):
        return None
    return round((b - a).total_seconds(), 1)


def lane_rate_estimate(rows: List[Dict]) -> Dict:
    """What the Bright Data lane cost, from its own MEASURED per-property rate.

    Offered because the month-to-date meter has not settled by the time a
    four-property run ends, and a run that reports no figure at all is less
    useful than one that reports a prior measurement and says plainly that it
    is a prior measurement. This is an ESTIMATE from
    PTF-ACQUISITION-BRAND-REPAIR-003, not a reading of this run's bill.
    """
    cost = PROVIDERS.get(PROVIDERS.BRIGHTDATA_BROWSER).cost_metadata()
    browser_rows = [r for r in rows
                    if r.get("provider_used") == PROVIDERS.BRIGHTDATA_BROWSER]
    rate = cost.usd_minor_per_property
    return {
        "brightdata_browser_properties": len(browser_rows),
        "measured_usd_minor_per_property": rate,
        "estimated_usd_minor": (round(rate * len(browser_rows), 2)
                                if rate is not None else None),
        "bytes_moved": sum(int(r.get("estimated_bytes") or 0)
                           for r in browser_rows),
        "basis": cost.basis,
        "measured_by": cost.measured_by,
        "is_an_estimate": True,
    }


# --------------------------------------------------------------------------- #
# Phase 1 -- live production capture through the routed lane.
# --------------------------------------------------------------------------- #

def _record_for(prop: CohortProperty) -> "CORPUS.BenchmarkRecord":
    """A capture record carrying identity only.

    ``facts``, ``quotes`` and ``withheld_fields`` stay empty for the same
    reason the market run leaves them empty: an empty benchmark cannot leak an
    expected answer into a capture, and this proof is about the artifact
    contract rather than about the facts.
    """
    return CORPUS.BenchmarkRecord(
        identity_key=prop.identity_key, name=prop.canonical_name,
        market_id=MARKET, brand=prop.brand,
        bucket=CORPUS.bucket_of(prop.brand), source_url=prop.official_url,
        pets_allowed=None, facts={}, quotes=(), withheld_fields={},
        service_animal_statement="", categories=frozenset(), origin="census")


def _successful_attempt_dir(run_dir: Path, slug: str, result) -> Optional[Path]:
    """The directory the successful attempt wrote, from the attempt number.

    Derived from the attempt record rather than by globbing for whichever
    directory happens to hold a block: on a lane that retried, the wrong
    directory would be a different capture of the same property.
    """
    valid = [a for a in result.attempts if a.outcome == "VALID"]
    if not valid:
        return None
    candidate = run_dir / slug / ("attempt-%02d" % valid[-1].attempt)
    return candidate if candidate.is_dir() else None


async def capture_phase(run_dir: Path, run_id: str) -> List[Dict]:
    """Acquire each property through the lane the registry resolves for it."""
    rows: List[Dict] = []
    for prop in COHORT:
        record = _record_for(prop)
        target = P2.target_for(record)
        began = time.monotonic()
        result = await ROUTER.route_property(record, target, run_dir=run_dir,
                                             run_id=run_id)
        attempt_dir = _successful_attempt_dir(run_dir, target.slug, result)
        rows.append({
            "lane": prop.lane,
            "identity_key": prop.identity_key,
            "canonical_name": prop.canonical_name,
            "requested_url": prop.official_url,
            "slug": target.slug,
            "final_state": result.state,
            "provider_used": (result.attempts[-1].provider
                              if result.attempts else ""),
            "providers_tried": list(result.providers_tried),
            "attempts": len(result.attempts),
            "took_the_registered_lane":
                bool(result.attempts)
                and result.attempts[0].provider == prop.expected_provider,
            "fallback_invoked": bool(result.cost.fallback_invoked),
            "failure": result.failure,
            "escalation_stopped_because": result.escalation_stopped_because,
            "captured": attempt_dir is not None,
            "attempt_dir": (_repo_relative(attempt_dir)
                            if attempt_dir else ""),
            "estimated_bytes": result.cost.estimated_bytes,
            "reported_credits": result.cost.reported_credits,
            "elapsed_seconds": round(time.monotonic() - began, 3),
        })
    return rows


# --------------------------------------------------------------------------- #
# The replay guard: a provider call during a replay is a failure, not a note.
# --------------------------------------------------------------------------- #

class ProviderCallDuringReplay(RuntimeError):
    """A replay tried to reach a provider. It is supposed to read files."""


@contextlib.contextmanager
def no_provider_calls():
    """Make every route to a provider raise for the duration of the block.

    Three layers, because one is not a proof:

      socket        catches urllib (Firecrawl) and the CDP websocket (Browser)
      subprocess    catches the Bright Data CLI, whose sockets are its own
      capture entry catches a lane that found some fourth way out

    The counter is returned so the caller can report the number it observed
    rather than asserting one it assumed.
    """
    seen: List[str] = []

    def deny(kind):
        def _raise(*args, **kwargs):
            seen.append(kind)
            raise ProviderCallDuringReplay(
                "a replay attempted %s; a replay reads persisted artifacts and "
                "never contacts a provider" % kind)
        return _raise

    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_run = subprocess.run
    real_popen = subprocess.Popen
    patched = [(FC, "capture_property"), (FC, "fetch"),
               (UC, "capture_property"), (UC, "_run_scrape"),
               (CBC, "capture_property")]
    originals = [(mod, name, getattr(mod, name)) for mod, name in patched]
    try:
        socket.socket.connect = deny("an outbound socket connection")
        socket.socket.connect_ex = deny("an outbound socket connection")
        subprocess.run = deny("a subprocess launch")
        subprocess.Popen = deny("a subprocess launch")
        for mod, name, _ in originals:
            setattr(mod, name, deny("%s.%s" % (mod.__name__.rsplit(".", 1)[-1],
                                               name)))
        yield seen
    finally:
        socket.socket.connect = real_connect
        socket.socket.connect_ex = real_connect_ex
        subprocess.run = real_run
        subprocess.Popen = real_popen
        for mod, name, original in originals:
            setattr(mod, name, original)


# --------------------------------------------------------------------------- #
# Phase 2 -- offline replay, hash verification, and the tamper control.
# --------------------------------------------------------------------------- #

def tamper_control(attempt_dir: Path) -> Dict:
    """A tampered COPY must be refused. The real artifact is never touched.

    The copy is made outside the capture tree, mutated by a single character,
    replayed, and deleted. The original's hash is taken before and after so the
    report can state -- from the bytes, not from intent -- that the control did
    not damage the evidence it was controlling.
    """
    block_path = attempt_dir / PL.BLOCK_ARTIFACT
    before = sha256_bytes(block_path.read_bytes())
    scratch = Path(tempfile.mkdtemp(prefix="ptf-019a-tamper-"))
    try:
        copy = scratch / "attempt"
        shutil.copytree(attempt_dir, copy)
        tampered_path = copy / PL.BLOCK_ARTIFACT
        original = tampered_path.read_text(encoding="utf-8")
        # One character. A tamper proof that mangles the whole file proves only
        # that a different file is a different file.
        tampered_path.write_text(original + "x", encoding="utf-8")
        replayed = PL.replay(copy)
        after = sha256_bytes(block_path.read_bytes())
        return {
            "tampered_copy_status": replayed.status,
            "returned_hash_mismatch": replayed.status == PL.HASH_MISMATCH,
            "mutation": "one character appended to the copied policy block",
            "original_block_sha256_before": before,
            "original_block_sha256_after": after,
            "original_block_unchanged": before == after,
            "copy_removed": True,
        }
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def replay_one(attempt_dir: Path) -> Dict:
    """Replay one capture from disk and check it against its own record."""
    block_path = attempt_dir / PL.BLOCK_ARTIFACT
    record_path = attempt_dir / PL.LOCATOR_ARTIFACT
    document_path = attempt_dir / DOCUMENT

    on_disk = block_path.read_bytes() if block_path.is_file() else b""
    with no_provider_calls() as seen:
        replayed = PL.replay(attempt_dir)
        replayed_bytes = replayed.text.encode("utf-8")

    record = dict(replayed.record or {})
    document_sha = (sha256_bytes(document_path.read_bytes())
                    if document_path.is_file() else "")
    return {
        "attempt_dir": _repo_relative(attempt_dir),
        "block_persisted": block_path.is_file(),
        "locator_persisted": record_path.is_file(),
        "locator_contract": record.get("contract", ""),
        "walk": record.get("walk", ""),
        "strategy": record.get("strategy", ""),
        "selector": record.get("selector", ""),
        "matched_phrase": record.get("matched_phrase", ""),
        "visibility_filtered": record.get("visibility_filtered"),
        "replay_status": replayed.status,
        "canonical": replayed.canonical,
        "block_bytes": len(on_disk),
        "byte_identical_to_disk": replayed_bytes == on_disk,
        "block_sha256_on_disk": sha256_bytes(on_disk),
        "block_sha256_in_record": record.get("block_sha256", ""),
        "block_hash_verified": bool(record.get("block_sha256"))
                               and record["block_sha256"] == replayed.block_sha256,
        "document_sha256_on_disk": document_sha,
        "document_sha256_in_record": record.get("document_sha256", ""),
        "document_hash_verified": bool(record.get("document_sha256"))
                                  and record["document_sha256"] == document_sha,
        "provider_calls_during_replay": len(seen),
        "provider_calls_detail": seen,
    }


#: Every gate a property must clear. Named so a partial pass reports WHICH
#: half of the proof held, instead of collapsing to a single boolean.
GATES: Tuple[Tuple[str, str], ...] = (
    ("live_capture", "the routed lane returned a valid capture"),
    ("block_persisted", "policy-block.txt is on disk"),
    ("locator_persisted", "locator.json is on disk under the contract"),
    ("replayed_canonically", "the replay status is REPLAYED, not BLOCK_ONLY"),
    ("byte_identical", "the replayed block is byte-identical to the persisted one"),
    ("block_hash_verified", "the block hashes to what its record says"),
    ("document_hash_verified", "rendered.html hashes to what its record says"),
    ("zero_provider_calls", "the replay reached no provider"),
    ("tamper_refused", "a tampered copy returns HASH_MISMATCH"),
)


def assess(capture_row: Dict, replay_row: Optional[Dict],
           tamper_row: Optional[Dict]) -> Dict:
    replay_row = replay_row or {}
    tamper_row = tamper_row or {}
    gates = {
        "live_capture": bool(capture_row.get("captured")),
        "block_persisted": bool(replay_row.get("block_persisted")),
        "locator_persisted": bool(replay_row.get("locator_persisted"))
                             and replay_row.get("locator_contract") == PL.CONTRACT,
        "replayed_canonically": replay_row.get("replay_status") == PL.REPLAYED,
        "byte_identical": bool(replay_row.get("byte_identical_to_disk")),
        "block_hash_verified": bool(replay_row.get("block_hash_verified")),
        "document_hash_verified": bool(replay_row.get("document_hash_verified")),
        "zero_provider_calls": replay_row.get("provider_calls_during_replay") == 0,
        "tamper_refused": bool(tamper_row.get("returned_hash_mismatch"))
                          and bool(tamper_row.get("original_block_unchanged")),
    }
    return {"gates": gates,
            "failed_gates": sorted(k for k, v in gates.items() if not v),
            "passed": all(gates.values())}


# --------------------------------------------------------------------------- #
# The run.
# --------------------------------------------------------------------------- #

async def run(*, run_id: str = RUN_ID, run_root: Optional[Path] = None) -> Dict:
    run_root = run_root or RUN_ROOT
    run_dir = run_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    checks = preflight()
    doc: Dict = {
        "schema": "ptf-locator-fresh-proof/1.0",
        "work_order": WORK_ORDER,
        "completes": "the Phase 9 fresh proof recorded BLOCKED_NO_PROVIDER_"
                     "CREDENTIAL by PTF-CANONICAL-POLICY-LOCATOR-PARITY-019",
        "run_id": run_id,
        "started_at": _now(),
        "market": MARKET,
        "pass_bar": PASS_BAR,
        "gates": {name: why for name, why in GATES},
        "preflight": checks,
        "routes_changed": False,
        "readers_changed": False,
        "authority_written": False,
        "observations_updated": False,
        "published": False,
    }
    if not checks["runnable"]:
        doc["status"] = "BLOCKED_PREFLIGHT"
        doc["properties_passed"] = 0
        doc["finished_at"] = _now()
        return doc

    spend_before = read_spend("019a:before")
    captures = await capture_phase(run_dir, run_id)
    spend_after_capture = read_spend("019a:after-capture")

    rows: List[Dict] = []
    for capture_row in captures:
        replay_row: Optional[Dict] = None
        tamper_row: Optional[Dict] = None
        if capture_row["captured"]:
            attempt_dir = REPO / capture_row["attempt_dir"]
            replay_row = replay_one(attempt_dir)
            if replay_row["block_persisted"]:
                tamper_row = tamper_control(attempt_dir)
        verdict = assess(capture_row, replay_row, tamper_row)
        rows.append({**capture_row, "replay": replay_row,
                     "tamper_control": tamper_row, **verdict})

    # Read AFTER the replay window, so the delta across it is evidence rather
    # than an assertion. A replay that reached a provider would move a meter.
    spend_after_replay = read_spend("019a:after-replay")
    replay_spend = spend_delta(spend_after_capture, spend_after_replay)

    passed = sum(1 for r in rows if r["passed"])
    doc.update({
        "finished_at": _now(),
        "status": "PASS" if passed == PASS_BAR else "FAIL",
        "properties_attempted": len(rows),
        "properties_passed": passed,
        "pass_bar_met": passed == PASS_BAR,
        "provider_usage": {
            "providers_called": sorted({r["provider_used"] for r in rows
                                        if r["provider_used"]}),
            "calls_by_lane": {r["lane"]: {"provider": r["provider_used"],
                                          "attempts": r["attempts"],
                                          "fallback_invoked": r["fallback_invoked"]}
                              for r in rows},
            "every_property_took_its_registered_lane":
                all(r["took_the_registered_lane"] for r in rows),
            "provider_calls_during_replay":
                sum((r["replay"] or {}).get("provider_calls_during_replay", 0)
                    for r in rows),
        },
        "incremental_cost": {
            "acquisition": spend_delta(spend_before, spend_after_capture),
            "replay": replay_spend,
            "brightdata_lane_estimate": lane_rate_estimate(rows),
            # The Firecrawl credit balance updates within the run, so a zero
            # credit delta across the replay window IS evidence. The Bright
            # Data meter does not settle that fast, so its zero is NOT offered
            # as corroboration of anything -- the guard is what proves the
            # replay reached no provider, and a meter too coarse to move in six
            # seconds cannot confirm or deny that.
            "replay_consumed_no_firecrawl_credits":
                replay_spend["firecrawl_credits_consumed"] == 0,
            "brightdata_meter_is_not_evidence_over_this_window": True,
            "readings": [spend_before, spend_after_capture, spend_after_replay],
        },
        "rows": rows,
    })
    return doc


#: The cold replay, as a program. Deliberately tiny and deliberately importing
#: only the locator contract: if replaying needed a capture module, a provider
#: client or a credential, this would fail to run.
_COLD_REPLAY = """
import hashlib, json, os, sys
sys.path.insert(0, sys.argv[1])
from scripts.pettripfinder.brightdata import policy_locator as PL
from pathlib import Path
directory = Path(sys.argv[2])
replayed = PL.replay(directory)
raw = (directory / PL.BLOCK_ARTIFACT).read_bytes()
print(json.dumps({
    "status": replayed.status,
    "canonical": replayed.canonical,
    "block_sha256": replayed.block_sha256,
    "byte_identical_to_disk": replayed.text.encode("utf-8") == raw,
    "credentials_visible": sorted(k for k in os.environ
                                  if "FIRECRAWL" in k or "BRIGHTDATA" in k),
}))
"""


def cold_replay(attempt_dir: Path) -> Dict:
    """Replay in a FRESH process with every provider credential stripped.

    The in-process replay runs inside a guard that proves it made no provider
    call. This proves something the guard cannot: that the replay does not
    depend on the capture session at all -- not on a warm client, not on a
    cached response, and not on a credential. The environment handed to the
    child has every Firecrawl and Bright Data variable removed, so a replay
    that secretly needed one could not have it.
    """
    env = {k: v for k, v in __import__("os").environ.items()
           if "FIRECRAWL" not in k and "BRIGHTDATA" not in k}
    completed = subprocess.run(
        [sys.executable, "-c", _COLD_REPLAY, str(REPO), str(attempt_dir)],
        capture_output=True, text=True, env=env, timeout=120)
    if completed.returncode != 0:
        return {"ran": False, "returncode": completed.returncode,
                "stderr": completed.stderr[-800:]}
    result = json.loads(completed.stdout)
    return {"ran": True, "credentials_stripped_from_child": True, **result}


def cold_replay_followup(report_path: Optional[Path] = None) -> Dict:
    """Run the cold replay over the captures the live run already persisted.

    Appended to the report rather than folded into the run, for the same reason
    the cost follow-up is: it is a check OVER persisted artifacts, and a replay
    that could not be repeated later from the same directory would not be a
    replay. Makes no capture call.
    """
    path = report_path or REPORT
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    rows: List[Dict] = []
    for row in doc["rows"]:
        replay = row.get("replay") or {}
        if not replay.get("attempt_dir"):
            continue
        directory = REPO / replay["attempt_dir"]
        cold = cold_replay(directory)
        rows.append({
            "lane": row["lane"],
            "attempt_dir": replay["attempt_dir"],
            **cold,
            # The bar: a cold process with no credentials reproduces the SAME
            # bytes the capturing process recorded.
            "agrees_with_the_in_process_replay":
                bool(cold.get("ran"))
                and cold.get("block_sha256") == replay.get("block_sha256_in_record")
                and bool(cold.get("byte_identical_to_disk")),
        })
    summary = {
        "checked_at": _now(),
        "captures_replayed_cold": len(rows),
        "all_agree": bool(rows) and all(r["agrees_with_the_in_process_replay"]
                                        for r in rows),
        "no_child_saw_a_provider_credential":
            all(not r.get("credentials_visible") for r in rows),
        "rows": rows,
    }
    doc["cold_replay"] = summary
    path.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False)
                      + "\n").encode("utf-8"))
    return summary


def cost_followup(report_path: Optional[Path] = None) -> Dict:
    """Re-read the meters after they have had time to settle, and record it.

    Separate from :func:`run` and deliberately so. The Bright Data figure a run
    can observe is the one available while it is still running, which is the
    one that has not settled yet; re-running the ACQUISITION to get a better
    cost reading would spend more money to measure money. This re-reads the
    meter only, makes no capture call, and appends the reading to the report it
    is correcting rather than overwriting the original numbers.
    """
    path = report_path or REPORT
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    readings = doc["incremental_cost"]["readings"]
    before = readings[0]
    now = read_spend("019a:settled-followup")
    delta = spend_delta(before, now)
    followup = {
        "read_at": now["read_at"],
        "seconds_after_run_started": _window_seconds(before, now),
        "delta_since_before_reading": delta,
        "status": ("MEASURED" if delta["brightdata_meter_moved"]
                   else "BRIGHTDATA_METER_STILL_UNSETTLED"),
        "note": ("The whole-run delta measured from the same baseline the run "
                 "used. Firecrawl credits settle immediately and are already "
                 "final in the run's own figure; this exists for the Bright "
                 "Data zone cost, which does not."),
        "attribution_caveat": (
            "The settling that makes this figure necessary also limits it. If "
            "an EARLIER Bright Data session had not yet settled when this "
            "run's baseline was read, its cost lands inside this delta and "
            "cannot be separated out from here. So this is an upper bound on "
            "the run and an exact figure only when no other session preceded "
            "it within the settling window. Attributing it precisely would "
            "need a baseline taken after the previous session settled, which "
            "is a scheduling property of the meter and not something a run "
            "can assert about itself."),
        "reading": now,
    }
    doc["incremental_cost"]["settled_followup"] = followup
    doc["incremental_cost"]["readings"] = readings + [now]
    path.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False)
                      + "\n").encode("utf-8"))
    return followup


def summarise(doc: Dict) -> str:
    lines = [
        "%s  %s" % (doc["work_order"], doc.get("status", "?")),
        "properties passed: %s of %s" % (doc.get("properties_passed", 0),
                                         doc["pass_bar"]),
        "",
    ]
    for row in doc.get("rows", []):
        lines.append("%-20s %-24s %-8s %s"
                     % (row["lane"], row["provider_used"] or "-",
                        "PASS" if row["passed"] else "FAIL",
                        row["final_state"]))
        if row["failed_gates"]:
            lines.append("     failed gates: %s" % ", ".join(row["failed_gates"]))
        replay = row.get("replay") or {}
        if replay:
            lines.append("     replay=%s  bytes=%s  provider_calls=%s  tamper=%s"
                         % (replay.get("replay_status"), replay.get("block_bytes"),
                            replay.get("provider_calls_during_replay"),
                            (row.get("tamper_control") or {})
                            .get("tampered_copy_status")))
    cost = doc.get("incremental_cost", {})
    if cost:
        acquisition, replay = cost["acquisition"], cost["replay"]
        estimate = cost.get("brightdata_lane_estimate", {})
        lines += [
            "",
            "acquisition: firecrawl=%s credits   brightdata zone delta=%s "
            "usd_minor over %ss"
            % (acquisition["firecrawl_credits_consumed"],
               acquisition["brightdata_usd_minor_total"],
               acquisition["window_seconds"]),
            "replay:      firecrawl=%s credits   (the guard, not the meter, is "
            "what proves zero provider calls)"
            % replay["firecrawl_credits_consumed"],
        ]
        if not acquisition["brightdata_meter_moved"]:
            lines.append(
                "  NOTE: the Bright Data month-to-date meter did not move "
                "within the run. That is an UNSETTLED meter, not a zero "
                "spend; re-read it with --cost-followup.")
        if estimate.get("estimated_usd_minor") is not None:
            lines.append(
                "  estimate from the measured lane rate: %s usd_minor for %s "
                "browser propert%s (%s)"
                % (estimate["estimated_usd_minor"],
                   estimate["brightdata_browser_properties"],
                   "y" if estimate["brightdata_browser_properties"] == 1
                   else "ies", estimate["measured_by"]))
    followup = cost.get("settled_followup")
    if followup:
        lines.append("  settled follow-up (%ss later): %s"
                     % (followup["seconds_after_run_started"],
                        followup["status"]))
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight-only", action="store_true",
                        help="report provider health, cohort and routes, and "
                             "make no provider call")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--run-id", default=RUN_ID)
    parser.add_argument("--cold-replay", action="store_true",
                        help="replay the run's captures in a fresh process "
                             "with every provider credential stripped, and "
                             "append the result to the report; makes no "
                             "capture call")
    parser.add_argument("--cost-followup", action="store_true",
                        help="re-read the billing meters and append the "
                             "settled figure to an existing report; makes no "
                             "capture call")
    args = parser.parse_args(argv)

    if args.preflight_only:
        print(json.dumps(preflight(), indent=1))
        return 0

    if args.cost_followup:
        print(json.dumps(cost_followup(), indent=1))
        return 0

    if args.cold_replay:
        summary = cold_replay_followup()
        print(json.dumps(summary, indent=1))
        return 0 if summary["all_agree"] else 1

    doc = asyncio.run(run(run_id=args.run_id))
    print(summarise(doc))
    if args.write_report:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False)
                            + "\n").encode("utf-8"))
        print("\nreport written: %s" % REPORT)
    return 0 if doc.get("pass_bar_met") else 1


if __name__ == "__main__":
    raise SystemExit(main())
