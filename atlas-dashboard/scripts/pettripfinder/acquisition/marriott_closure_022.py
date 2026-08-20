"""PTF-MARRIOTT-OBSERVATION-CLOSURE-022 -- close the three Marriott records.

021 hardened the Marriott locator and deliberately touched no record. It left a
queue of three whose stored reading materially disagrees with what the corrected
locator and reader produce. This work order proves the corrected locator on one
fresh live capture and supersedes exactly those three.

THREE RECORDS, THREE DIFFERENT KINDS OF CHANGE
-----------------------------------------------
Treating them alike would be wrong, and the difference is what 018 established:
re-parsing a stored block is a RE-DERIVATION, while selecting a different block
changes what the record is ABOUT and is a re-acquisition.

  The Trade         LOCATOR + READER. The old observation read the FAQ; the
                    corrected locator selects the property's own Pet Policy
                    accordion. Different evidence subject, confirmed by a fresh
                    live capture under the 021 locator.

  Poplar Creek      LOCATOR + READER. Its stored block came from the Web
                    Unlocker's static walk and is a strict sub-span of what the
                    brand locator selects from the same persisted document. The
                    subject widens, so it is a locator supersession -- but the
                    evidence is already on disk and no provider is called.

  Sheraton          READER ONLY. Its block did not change at all. It is
                    superseded because the corrected reader declines to assert
                    a fee the block cannot support. Relocating it merely
                    because a new locator exists would be exactly the error 018
                    named.

WHERE THE CURRENT-STATE OBSERVATION LIVES, AND WHY THESE THREE ARE NOT IN IT
-----------------------------------------------------------------------------
``milwaukee-wi_policy_proposals_001.json`` is the committed current-state
observation store, and it is a projection of ONE journal:
``milwaukee-router-001``. All three of these properties were acquired by
``marriott-milwaukee-020``, a different run, so none of them has a row in that
store today -- 11 Marriott rows are there, and they are the eleven the router
run acquired.

So the corrected readings are written as a SUPERSESSION ARTIFACT carrying both
readings and the full lineage, and the store is regenerated through its own
builder to prove that regeneration is a no-op for rows it does not hold. What
this work order does NOT do is widen the store's journal to take the 020 run:
that would add seventeen rows, fourteen of which this work order never examined
and for which it has no differential, and Phase 6's bar is that unexpected rows
are zero. Integrating the 020 run into the store is a separate work order and
is reported as one.

NOTHING IS PUBLISHED
--------------------
No policy authority is created, ``published`` and ``founder_approved`` stay
false on every record, and no historical report, journal or persisted block is
edited.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import marriott_decision_020 as D    # noqa: E402
from scripts.pettripfinder.acquisition import marriott_template_021 as T    # noqa: E402
from scripts.pettripfinder.acquisition import providers as PROVIDERS        # noqa: E402
from scripts.pettripfinder.acquisition import registry as REGISTRY          # noqa: E402
from scripts.pettripfinder.brightdata import client as CLIENT               # noqa: E402
from scripts.pettripfinder.brightdata import marriott_surface as MS         # noqa: E402
from scripts.pettripfinder.brightdata import policy_locator as PL           # noqa: E402

WORK_ORDER = "PTF-MARRIOTT-OBSERVATION-CLOSURE-022"
MARKET = "milwaukee-wi"

REPORTS = REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
CONFIRMATION = REPORTS / "ptf_marriott_live_confirmation_022.json"
SUPERSESSION = REPORTS / "ptf_marriott_supersession_022.json"
COUNTS = REPORTS / "milwaukee-wi_counts_022.json"

FRESH_RUN_ID = "marriott-closure-022"
FRESH_RUN_DIR = D.RUN_ROOT / FRESH_RUN_ID / FRESH_RUN_ID

#: The one property re-captured live, and the only one. Poplar Creek and
#: Sheraton have sufficient persisted evidence, so re-acquiring them would
#: spend money to learn nothing.
LIVE_SUBJECT = "The Trade, Autograph Collection"

#: The queue this work order closes, and its expected size.
EXPECTED_QUEUE = 3

#: How each record is superseded. Stated here rather than inferred at runtime,
#: so a record cannot silently change category.
LOCATOR_AND_READER = "LOCATOR_AND_READER_SUPERSESSION"
READER_ONLY = "READER_ONLY_SUPERSESSION"

UPDATE_KIND: Dict[str, str] = {
    "The Trade, Autograph Collection": LOCATOR_AND_READER,
    "Residence Inn by Marriott Milwaukee Brookfield at Poplar Creek":
        LOCATOR_AND_READER,
    "Sheraton Milwaukee Brookfield Hotel": READER_ONLY,
}

BILLABLE_ZONES = ("scraping_browser1", "mcp_unlocker", "cli_unlocker")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _relative(path: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(REPO)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def reader_commit() -> str:
    """The commit that last changed the Marriott reader. Stamped on every
    superseding record, so a reading can be tied to the code that produced it."""
    out = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--",
         "atlas-dashboard/scripts/pettripfinder/brightdata/marriott_surface.py"],
        cwd=str(REPO.parent), capture_output=True, text=True).stdout.strip()
    return out


# --------------------------------------------------------------------------- #
# Phase 1 -- preflight.
# --------------------------------------------------------------------------- #

def queue_items() -> List[Dict]:
    doc = json.loads(T.QUEUE.read_text(encoding="utf-8-sig"))
    return list(doc["items"])


def stored_020_rows() -> Dict[str, Dict]:
    run = json.loads(D.RUN_REPORT.read_text(encoding="utf-8-sig"))
    return {r["canonical_name"]: r for r in run["rows"]}


def preflight() -> Dict:
    items = queue_items()
    names = sorted(i["canonical_name"] for i in items)
    stored = stored_020_rows()
    route = REGISTRY.resolve(
        brand="MARRIOTT",
        url="https://www.marriott.com/en-us/hotels/mkedd-x/overview/")
    return {
        "checked_at": _now(),
        "queue_count": len(items),
        "queue_assertion_holds": len(items) == EXPECTED_QUEUE,
        "queue": names,
        "update_kinds": {n: UPDATE_KIND.get(n, "") for n in names},
        "all_kinds_declared": all(n in UPDATE_KIND for n in names),
        "marriott_route": {"provider": route.provider,
                           "ladder": list(route.ladder),
                           "reader": route.reader},
        "route_unchanged": (route.provider == PROVIDERS.BRIGHTDATA_BROWSER
                            and route.ladder == (PROVIDERS.BRIGHTDATA_BROWSER,
                                                 PROVIDERS.BRIGHTDATA_WEB_UNLOCKER)
                            and route.reader == "marriott"),
        "locator_contract": PL.CONTRACT,
        "marriott_locator_ids": [i for i, _ in MS.POLICY_LOCATORS],
        "reader_commit": reader_commit(),
        "stored_observations_present": {n: n in stored for n in names},
        "milwaukee_policy_authority_files": len(list(
            (REPO / "launch_packages" / "pettripfinder")
            .rglob("*hotel_policy_facts*milwaukee*"))),
    }


# --------------------------------------------------------------------------- #
# Phase 2 -- the fresh live confirmation.
# --------------------------------------------------------------------------- #

def read_spend(label: str) -> Dict:
    zones: Dict[str, Optional[int]] = {}
    for zone in BILLABLE_ZONES:
        snap = CLIENT.read_usage("%s:%s" % (label, zone), zone=zone)
        zones[zone] = snap.cost_month_usd_minor
    return {"label": label, "read_at": _now(),
            "brightdata_zone_cost_month_usd_minor": zones}


def spend_delta(before: Mapping, after: Mapping) -> Dict:
    zones: Dict[str, Optional[int]] = {}
    total: Optional[int] = 0
    for zone in BILLABLE_ZONES:
        a = before["brightdata_zone_cost_month_usd_minor"].get(zone)
        b = after["brightdata_zone_cost_month_usd_minor"].get(zone)
        if a is None or b is None:
            zones[zone], total = None, None
            continue
        zones[zone] = max(0, b - a)
        if total is not None:
            total += zones[zone]
    return {"brightdata_usd_minor_by_zone": zones,
            "brightdata_usd_minor_total": total,
            "meter_moved": bool(total),
            "measurement_status": ("MEASURED" if total
                                   else "UNSETTLED_AT_READ_TIME"),
            "note": ("The Bright Data month-to-date meter settles behind the "
                     "traffic that moved it (measured in 019A: a session that "
                     "moved 9.3 MB left the meter flat for over a minute). An "
                     "unmoved meter here is unsettled, not free.")}


#: What the live capture has to show. Each is a separate claim and each is
#: checked from the artifact rather than from the run's own summary.
LIVE_GATES: Tuple[Tuple[str, str], ...] = (
    ("acquired", "the routed lane returned a document"),
    ("identity_confirmed", "the page is this property"),
    ("structural_locator_used", "a Marriott structural locator selected the block"),
    ("accordion_locator_used", "specifically the accordion locator"),
    ("block_is_the_pet_policy_panel", "the block is the Pet Policy panel"),
    ("has_deposit_component", "the block states the deposit"),
    ("has_recurring_component", "the block states the recurring daily fee"),
    ("has_weight_or_count", "weight and count terms survive where present"),
    ("block_persisted", "policy-block.txt was written"),
    ("locator_record_persisted", "locator.json was written"),
    ("replay_reproduces_the_block", "an offline replay returns the same bytes"),
)


def assess_live(row: Mapping, attempt_dir: Optional[Path]) -> Dict:
    detail = dict(row.get("usable_policy_detail") or {})
    block = detail.get("block_text") or ""
    locator = detail.get("policy_locator") or ""
    lowered = block.lower()

    replay_status, replay_identical = "", False
    if attempt_dir is not None:
        replayed = PL.replay(attempt_dir)
        replay_status = replayed.status
        on_disk = (attempt_dir / PL.BLOCK_ARTIFACT).read_bytes() \
            if (attempt_dir / PL.BLOCK_ARTIFACT).is_file() else b""
        replay_identical = replayed.text.encode("utf-8") == on_disk

    gates = {
        "acquired": row.get("acquisition_status") == "ACQUIRED",
        "identity_confirmed": bool(row.get("identity_confirmed")),
        "structural_locator_used": locator in {i for i, _ in MS.STRUCTURAL_XPATHS},
        "accordion_locator_used": locator == "pet_policy_accordion_panel",
        "block_is_the_pet_policy_panel": block.startswith("Pet Policy"),
        "has_deposit_component": "deposit" in lowered,
        "has_recurring_component": ("daily" in lowered or "per night" in lowered
                                    or "per day" in lowered),
        "has_weight_or_count": ("weight" in lowered or "number of pets" in lowered),
        "block_persisted": attempt_dir is not None
                           and (attempt_dir / PL.BLOCK_ARTIFACT).is_file(),
        "locator_record_persisted": attempt_dir is not None
                                    and (attempt_dir / PL.LOCATOR_ARTIFACT).is_file(),
        "replay_reproduces_the_block": replay_identical,
    }
    return {
        "gates": gates,
        "failed_gates": sorted(k for k, v in gates.items() if not v),
        "passed": all(gates.values()),
        "policy_locator": locator,
        "block_text": block,
        "block_sha256": sha256_text(block),
        "replay_status": replay_status,
        "attempt_dir": _relative(attempt_dir) if attempt_dir else "",
    }


async def live_confirmation() -> Dict:
    """One fresh capture of The Trade through its registered production route.

    Not a re-measurement of the provider: 020 already established that lane.
    What is being confirmed is that the LIVE Marriott walk -- which no offline
    differential can exercise, because it needs a browser -- now binds the
    accordion container that 021 taught it about.
    """
    rows = D.remaining_cohort()
    subject = next((r for r in rows if r["canonical_name"] == LIVE_SUBJECT), None)
    if subject is None:
        run = json.loads(D.RUN_REPORT.read_text(encoding="utf-8-sig"))
        stored = next(r for r in run["rows"]
                      if r["canonical_name"] == LIVE_SUBJECT)
        subject = {"identity_key": stored["identity_key"],
                   "canonical_name": stored["canonical_name"],
                   "brand": "MARRIOTT", "market_id": MARKET,
                   "official_url": stored["requested_url"]}

    source = D.source_audit(subject)
    FRESH_RUN_DIR.mkdir(parents=True, exist_ok=True)
    before = read_spend("022:before")
    # The registry on disk decides the lane. No override.
    row = await D.acquire(subject, registry=REGISTRY.load(),
                          run_dir=FRESH_RUN_DIR, run_id=FRESH_RUN_ID,
                          source=source)
    after = read_spend("022:after")

    attempt_dir = D._attempt_dir_for(FRESH_RUN_DIR, D._slug_of(LIVE_SUBJECT))
    verdict = assess_live(row, attempt_dir)
    return {
        "schema": "ptf-marriott-live-confirmation/1.0",
        "work_order": WORK_ORDER,
        "market": MARKET,
        "generated_at": _now(),
        "subject": LIVE_SUBJECT,
        "route_used": {"provider": row.get("provider_used"),
                       "providers_tried": row.get("providers_tried"),
                       "attempts": row.get("attempts")},
        "routing_overridden": False,
        "gates": {name: why for name, why in LIVE_GATES},
        "verdict": verdict,
        "passed": verdict["passed"],
        "final_state": row.get("final_state"),
        "publication_grade": row.get("publication_grade"),
        "estimated_bytes": row.get("estimated_bytes"),
        "cost": {"delta": spend_delta(before, after),
                 "readings": [before, after]},
        "capture_row": row,
        "authority_written": False,
        "published": False,
    }


def summarise_live(doc: Mapping) -> str:
    verdict = doc["verdict"]
    lines = ["%s -- live accordion confirmation" % doc["work_order"],
             "subject: %s" % doc["subject"],
             "route:   %s (tried %s, %s attempts)"
             % (doc["route_used"]["provider"],
                doc["route_used"]["providers_tried"],
                doc["route_used"]["attempts"]),
             "locator: %s" % verdict["policy_locator"],
             "replay:  %s" % verdict["replay_status"],
             "",
             "PASS" if verdict["passed"] else "FAIL: %s"
             % ", ".join(verdict["failed_gates"]),
             "",
             "block: %r" % verdict["block_text"][:300]]
    cost = doc["cost"]["delta"]
    lines += ["", "brightdata %s usd_minor (%s), bytes %s"
              % (cost["brightdata_usd_minor_total"],
                 cost["measurement_status"], doc["estimated_bytes"])]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Phases 3-8 -- the supersession.
# --------------------------------------------------------------------------- #

#: Where each record's NEW evidence comes from. Named per record rather than
#: derived, because "which document is this record about" is precisely the
#: thing that must not move silently.
FRESH_LIVE_CAPTURE = "FRESH_022_LIVE_CAPTURE"
PERSISTED_020_DOCUMENT = "RELOCATED_IN_PERSISTED_020_DOCUMENT"
PERSISTED_020_BLOCK = "PERSISTED_020_BLOCK_UNCHANGED"

EVIDENCE_SOURCE: Dict[str, str] = {
    "The Trade, Autograph Collection": FRESH_LIVE_CAPTURE,
    "Residence Inn by Marriott Milwaukee Brookfield at Poplar Creek":
        PERSISTED_020_DOCUMENT,
    "Sheraton Milwaukee Brookfield Hotel": PERSISTED_020_BLOCK,
}


def _read(block: str) -> Dict:
    """The current Marriott reader, all the way to the extraction."""
    if not (block or "").strip():
        return {"extraction": {}, "withheld": {}, "evidence": [],
                "non_inferences": [], "unrepresented": []}
    reading = MS.parse_policy_block(block, locator_id="marriott_closure_022")
    result = MS.to_extraction(reading, location="policy-block.txt")
    return {
        "extraction": dict(result.extraction),
        "withheld": dict(result.withheld or {}),
        "evidence": [dict(e) for e in result.evidence],
        "non_inferences": list(result.non_inferences),
        "unrepresented": [dict(u) for u in reading.unrepresented],
    }


def _new_evidence(name: str, live: Optional[Mapping]) -> Dict:
    """The block this record will now be about, and where it came from."""
    source = EVIDENCE_SOURCE[name]
    stored = stored_020_rows()[name]
    stored_attempt = D._attempt_dir_for(T.RUN_ROOT, D._slug_of(name))

    if source == FRESH_LIVE_CAPTURE:
        verdict = live["verdict"]
        return {
            "evidence_source": source,
            "block": verdict["block_text"],
            "locator": verdict["policy_locator"],
            "attempt_dir": verdict["attempt_dir"],
            "run_id": FRESH_RUN_ID,
            "derivation": ("captured live under the 021 locator contract and "
                           "selected in the page by the accordion locator; the "
                           "block and its locator record are persisted and "
                           "replay byte-identically"),
        }

    if source == PERSISTED_020_BLOCK:
        block_path = stored_attempt / PL.BLOCK_ARTIFACT
        return {
            "evidence_source": source,
            "block": block_path.read_text(encoding="utf-8",
                                          errors="replace").strip(),
            "locator": (stored.get("usable_policy_detail") or {}).get(
                "policy_locator", ""),
            "attempt_dir": _relative(stored_attempt),
            "run_id": D.PRODUCTION_RUN_ID,
            "derivation": ("the persisted block, unchanged. This is a re-parse "
                           "and not a re-location: the corrected locator would "
                           "select the same container, and relocating merely "
                           "because a new locator exists would move what the "
                           "record is about for no reason"),
        }

    html = (stored_attempt / "rendered.html").read_text(encoding="utf-8",
                                                        errors="replace")
    hit = T.locate_offline(html, T.NEW_STRUCTURAL_XPATHS)
    return {
        "evidence_source": source,
        "block": hit.text,
        "locator": hit.strategy,
        "attempt_dir": _relative(stored_attempt),
        "run_id": D.PRODUCTION_RUN_ID,
        "derivation": (
            "re-located inside the ALREADY PERSISTED 020 document by the "
            "corrected structural locator, evaluated offline. This changes the "
            "evidence subject and is a re-location, not a re-parse: the stored "
            "block came from the Web Unlocker's static walk and is a strict "
            "sub-span of the container the brand locator binds. No provider was "
            "called, and the offline evaluation reads text_content where a live "
            "walk would read innerText, so whitespace may differ from a future "
            "live capture even though the container is the same"),
    }


def supersede_one(name: str, live: Optional[Mapping]) -> Dict:
    """One superseding current-state observation, with its whole history."""
    stored = stored_020_rows()[name]
    detail = dict(stored.get("usable_policy_detail") or {})
    old_block = detail.get("block_text") or ""
    old_read = _read(old_block)
    new = _new_evidence(name, live)
    new_read = _read(new["block"])

    # WHAT 020 ACTUALLY ASSERTED, which is not the same as what the current
    # reader makes of 020's block. Sheraton is the case that proves the
    # difference: its block never changed, so recomputing it with today's
    # reader shows no change at all -- and hides that the stored record asserts
    # a pet_fee this reader now refuses. The run report's field list is the
    # authoritative record of what that observation claimed, so it is what the
    # supersession is measured against.
    asserted_at_020 = sorted(detail.get("substantive_fields") or [])
    old_fields = set(asserted_at_020)
    new_fields = set(new_read["extraction"])
    return {
        "canonical_name": name,
        "identity_key": stored["identity_key"],
        "market_id": MARKET,
        "brand": "MARRIOTT",
        "update_kind": UPDATE_KIND[name],
        "material_issue": next(i["material_issue"] for i in queue_items()
                               if i["canonical_name"] == name),

        # ---- what it used to be about, preserved verbatim ---------------- #
        "superseded": {
            "work_order": D.WORK_ORDER,
            "run_id": D.PRODUCTION_RUN_ID,
            "policy_locator": detail.get("policy_locator", ""),
            "policy_block": old_block,
            "policy_block_sha256": sha256_text(old_block),
            "attempt_dir": _relative(
                D._attempt_dir_for(T.RUN_ROOT, D._slug_of(name))),
            # The fields that observation claimed, from the 020 run report.
            "fields_asserted": asserted_at_020,
            "fields_withheld": sorted(detail.get("withheld_fields") or []),
            # And what today's reader makes of the same block, kept separate so
            # the two are never confused for one another.
            "extraction_recomputed_with_current_reader": old_read["extraction"],
            "withheld_recomputed_with_current_reader": old_read["withheld"],
            "provider": stored.get("provider_used", ""),
            "identity_confirmed": bool(stored.get("identity_confirmed")),
        },

        # ---- what it is about now ---------------------------------------- #
        "current": {
            "work_order": WORK_ORDER,
            "run_id": new["run_id"],
            "evidence_source": new["evidence_source"],
            "derivation": new["derivation"],
            "policy_locator": new["locator"],
            "policy_block": new["block"],
            "policy_block_sha256": sha256_text(new["block"]),
            "attempt_dir": new["attempt_dir"],
            "reader_commit": reader_commit(),
            "locator_contract": PL.CONTRACT,
            "extraction": new_read["extraction"],
            "withheld": new_read["withheld"],
            "evidence": new_read["evidence"],
            "non_inferences": new_read["non_inferences"],
            "unrepresented_charge_components": new_read["unrepresented"],
        },

        "fields_added": sorted(new_fields - old_fields),
        "fields_removed": sorted(old_fields - new_fields),
        "fields_withheld_now": sorted(new_read["withheld"]),
        "block_changed": old_block.strip() != new["block"].strip(),
        "identity_unchanged": True,

        # Never automatically ready. A record whose fee is withheld because the
        # surface states components the schema cannot carry is a record a human
        # has to look at, and saying so is the point of the queue.
        "published": False,
        "founder_approved": False,
        "review_status": ("HELD_SCHEMA_CANNOT_REPRESENT"
                          if new_read["withheld"].get("pet_fee")
                          == "SCHEMA_CANNOT_REPRESENT"
                          else "NEEDS_REVIEW"),

        # ---- Phase 8 lineage, mechanically inspectable ------------------- #
        "lineage": [
            {"work_order": D.WORK_ORDER, "event": "observed",
             "detail": "acquired on the registered Marriott route; the reading "
                       "came from the block the locator of the day selected",
             "policy_locator": detail.get("policy_locator", ""),
             "policy_block_sha256": sha256_text(old_block)},
            {"work_order": T.WORK_ORDER, "event": "locator_defect_proved",
             "detail": "Marriott serves two templates and the locator list saw "
                       "one; the accordion pages fell through to the generic "
                       "walk",
             "policy_locator": "", "policy_block_sha256": ""},
            {"work_order": WORK_ORDER, "event": "corrected_locator_confirmed_live",
             "detail": ("a fresh capture of %s bound the accordion container "
                        "through the live walk" % LIVE_SUBJECT),
             "policy_locator": "pet_policy_accordion_panel",
             "policy_block_sha256": (live["verdict"]["block_sha256"]
                                     if live else "")},
            {"work_order": WORK_ORDER, "event": "superseded",
             "detail": "current-state observation replaced under %s"
                       % UPDATE_KIND[name],
             "policy_locator": new["locator"],
             "policy_block_sha256": sha256_text(new["block"])},
        ],
    }


def build_supersession(live: Optional[Mapping] = None) -> Dict:
    items = queue_items()
    if len(items) != EXPECTED_QUEUE:
        raise AssertionError("queue is %d, expected %d"
                             % (len(items), EXPECTED_QUEUE))
    if live is None and CONFIRMATION.is_file():
        live = json.loads(CONFIRMATION.read_text(encoding="utf-8-sig"))
    if not live or not live.get("passed"):
        raise SystemExit("ABORT: the live accordion confirmation has not "
                         "passed; no observation may be superseded")

    records = [supersede_one(i["canonical_name"], live)
               for i in sorted(items, key=lambda x: x["canonical_name"])]
    return {
        "schema": "ptf-marriott-supersession/1.0",
        "work_order": WORK_ORDER,
        "market": MARKET,
        "generated_at": _now(),
        "live_confirmation": {
            "subject": live["subject"],
            "passed": live["passed"],
            "policy_locator": live["verdict"]["policy_locator"],
            "block_sha256": live["verdict"]["block_sha256"],
            "replay_status": live["verdict"]["replay_status"],
        },
        "records_superseded": len(records),
        "update_kinds": {r["canonical_name"]: r["update_kind"] for r in records},
        "reader_commit": reader_commit(),
        "locator_contract": PL.CONTRACT,
        "provider_calls": 1,
        "provider_calls_note": ("one, for the live confirmation. Poplar Creek "
                                "and Sheraton had sufficient persisted "
                                "evidence and were not re-acquired"),
        "authority_written": False,
        "published": False,
        "founder_approved": False,
        "records": records,
    }


# --------------------------------------------------------------------------- #
# Phase 6 -- the differential, and Phase 7's no-op proof.
# --------------------------------------------------------------------------- #

def differential(doc: Mapping) -> Dict:
    """What must differ, what must not, and whether the store even holds it.

    The last part is the finding: the current-state observation store projects
    ONE journal, and these three properties were acquired by a different run,
    so regenerating it changes nothing for them. That is reported rather than
    fixed by widening the store's input, which would add fourteen rows this
    work order never examined.
    """
    from scripts.pettripfinder import milwaukee_policy_proposals_001 as PROP

    expected = sorted(r["canonical_name"] for r in doc["records"])
    changed = sorted(r["canonical_name"] for r in doc["records"]
                     if r["fields_added"] or r["fields_removed"]
                     or r["block_changed"]
                     or r["fields_withheld_now"])
    unexpected = sorted(set(changed) - set(expected))

    proposals_path = PROP.REPORTS / ("%s_policy_proposals_001.json" % MARKET)
    before = json.loads(proposals_path.read_text(encoding="utf-8-sig"))
    overlay = {r["identity_key"]: {
        "work_order": WORK_ORDER,
        "reader_commit": doc["reader_commit"],
        "evidence_block_path": r["current"]["attempt_dir"] + "/"
                               + PL.BLOCK_ARTIFACT,
        "evidence_block_sha256": r["current"]["policy_block_sha256"],
        "extraction": r["current"]["extraction"],
        "withheld": r["current"]["withheld"],
        "non_inferences": r["current"]["non_inferences"],
        "evidence": r["current"]["evidence"],
    } for r in doc["records"]}
    rebuilt = PROP.build(rederived=overlay, write=False)

    store_keys = {i["identity_key"] for i in before["items"]}
    in_store = sorted(k for k in overlay if k in store_keys)
    return {
        "expected_rows": expected,
        "rows_that_differ": changed,
        "unexpected_rows": unexpected,
        "clean": not unexpected and set(changed) == set(expected),
        "identity_unchanged": all(r["identity_unchanged"] for r in doc["records"]),
        "publication_unchanged": all(not r["published"] for r in doc["records"]),
        "founder_approval_unchanged": all(not r["founder_approved"]
                                          for r in doc["records"]),
        "marriott_rows_in_store": sum(1 for i in before["items"]
                                      if i.get("brand") == "MARRIOTT"),
        "superseded_rows_present_in_store": in_store,
        "store_rows_before": len(before["items"]),
        "store_rows_after_regeneration": len(rebuilt["items"]),
        "store_regeneration_is_a_no_op": len(before["items"]) == len(rebuilt["items"])
                                         and not in_store,
        "why": ("the current-state store projects the milwaukee-router-001 "
                "journal only; all three of these properties were acquired by "
                "marriott-milwaukee-020, so the store holds no row for them and "
                "regenerating it is a no-op. Integrating the 020 run into the "
                "store would add seventeen rows, fourteen of them unexamined by "
                "this work order, and is a separate work order"),
        "fourth_marriott_record_changed": False,
    }


def cost_followup() -> Dict:
    """Re-read the Bright Data meter after it has had time to settle.

    Separate from the capture for the reason 019A established: the figure a run
    can observe is the one that has not settled yet, and re-running the capture
    to get a better cost reading would spend money to measure money. This reads
    the meter only and appends the result to the confirmation report.
    """
    doc = json.loads(CONFIRMATION.read_text(encoding="utf-8-sig"))
    before = doc["cost"]["readings"][0]
    now = read_spend("022:settled-followup")
    delta = spend_delta(before, now)
    followup = {
        "read_at": now["read_at"],
        "delta_since_before_reading": delta,
        "status": ("MEASURED" if delta["meter_moved"]
                   else "BRIGHTDATA_METER_STILL_UNSETTLED"),
        "attribution_caveat": (
            "An earlier session still settling when this run's baseline was "
            "read lands inside this delta and cannot be separated out, so this "
            "is an upper bound on the one capture rather than an exact figure."),
        "reading": now,
    }
    doc["cost"]["settled_followup"] = followup
    doc["cost"]["readings"] = doc["cost"]["readings"] + [now]
    CONFIRMATION.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False)
                              + "\n").encode("utf-8"))
    return followup


# --------------------------------------------------------------------------- #
# Phase 11 -- the counters, each with the predicate that produces it.
# --------------------------------------------------------------------------- #

def milwaukee_counts() -> Dict:
    """Every Milwaukee counter, with the exact question it answers.

    The bookkeeping confusion 020 exposed is not an arithmetic error. It is
    four different predicates sharing three words -- "acquired", "completed",
    "done" -- and each producing a different number from the same data:

        touched            we made an acquisition attempt and journalled it
        publication-grade  that attempt produced evidence good enough to cite
        observed           a current-state observation row exists for it
        published          it is live on the site

    They are legitimately different and they will never converge. A property
    can be touched and not publication-grade (the fetch failed), publication-
    grade and not observed (its run does not feed the store), and observed and
    not published (nothing is published at all). Reporting one of them under
    another's name is what makes a market look finished when it is not.
    """
    from collections import Counter
    from scripts.pettripfinder import milwaukee_policy_proposals_001 as PROP

    queue = json.loads(D.QUEUE_PATH.read_text(encoding="utf-8-sig"))
    routable = [r for r in queue["items"] if not r["brand_excluded"]]
    routable_keys = {r["identity_key"] for r in routable}

    router = PROP.read_journal()
    router_keys = {e["identity_key"] for e in router}
    router_grade = {e["identity_key"] for e in router
                    if e["final_state"] == "ACQUIRED_PUBLICATION_GRADE"}

    run020 = json.loads(D.RUN_REPORT.read_text(encoding="utf-8-sig"))["rows"]
    keys020 = {r["identity_key"] for r in run020}
    grade020 = {r["identity_key"] for r in run020 if r.get("publication_grade")}

    proposals_path = PROP.REPORTS / ("%s_policy_proposals_001.json" % MARKET)
    store = json.loads(proposals_path.read_text(encoding="utf-8-sig"))

    touched = router_keys | keys020
    graded = router_grade | grade020
    remaining = routable_keys - touched
    by_brand = Counter(r["brand"] for r in routable
                       if r["identity_key"] in remaining)

    return {
        "schema": "ptf-milwaukee-counts/1.0",
        "work_order": WORK_ORDER,
        "market": MARKET,
        "generated_at": _now(),
        "definitions": {
            "queue_total": "every row in the committed acquisition queue",
            "brand_excluded": "rows whose brand is excluded on cost "
                              "(HYATT, BEST_WESTERN)",
            "routable_total": "queue_total minus brand_excluded; the "
                              "denominator for every figure below",
            "touched": "an acquisition attempt was made and journalled, "
                       "whatever its outcome",
            "publication_grade": "the attempt produced evidence satisfying "
                                 "PUBLICATION_GRADE_REQUIRED",
            "observed": "a current-state observation row exists in "
                        "milwaukee-wi_policy_proposals_001.json",
            "unresolved": "touched but not publication grade",
            "remaining": "routable and never touched",
            "published": "live on the site",
        },
        "queue_total": len(queue["items"]),
        "brand_excluded": len(queue["items"]) - len(routable),
        "routable_total": len(routable),
        "touched": len(touched),
        "touched_by_run": {"milwaukee-router-001": len(router_keys),
                           D.PRODUCTION_RUN_ID: len(keys020),
                           "overlap": len(router_keys & keys020)},
        "publication_grade": len(graded),
        "publication_grade_by_run": {"milwaukee-router-001": len(router_grade),
                                     D.PRODUCTION_RUN_ID: len(grade020)},
        "observed_current_state": len(store["items"]),
        "observed_note": ("the store projects the milwaukee-router-001 journal "
                          "only, so the 17 properties acquired by %s have no "
                          "row in it. That is the gap 022 reports and does not "
                          "close: widening the store's input would add 17 rows, "
                          "14 of them unexamined by this work order"
                          % D.PRODUCTION_RUN_ID),
        "unresolved_acquisition": len(touched - graded),
        "unresolved_states": dict(Counter(
            e["final_state"] for e in router
            if e["final_state"] != "ACQUIRED_PUBLICATION_GRADE")),
        "remaining_production_queue": len(remaining),
        "remaining_by_brand": dict(by_brand.most_common()),
        "published_policy_count": sum(1 for i in store["items"]
                                      if i.get("published")),
        "founder_approved_count": sum(1 for i in store["items"]
                                      if i.get("founder_approved")),
        "milwaukee_policy_authority_files": len(list(
            (REPO / "launch_packages" / "pettripfinder")
            .rglob("*hotel_policy_facts*milwaukee*"))),
        "reconciliation": {
            "the_two_figures": "83 completed / 44 remaining versus 84 acquired "
                               "/ 43 remaining",
            "derivable_today": "84 touched / 43 remaining, from 67 router rows "
                               "plus 17 from %s with zero overlap against a "
                               "routable total of 127" % D.PRODUCTION_RUN_ID,
            "where_83_comes_from": (
                "no committed artifact in this repository carries 83 or 44, so "
                "the pair cannot be sourced from data. The 020 run journals one "
                "row per property as it completes, so any count taken while it "
                "was in flight -- at 16 of 17 -- yields exactly 83 touched and "
                "44 remaining. That is the only mechanically consistent "
                "explanation available, and it is offered as such rather than "
                "asserted."),
            "the_larger_point": (
                "the two figures differ by one, but the counters differ by "
                "far more: touched is 84, publication-grade is 75, observed is "
                "58 and published is 0. Reporting any of those as 'completed' "
                "makes the market look further along than it is."),
            "nothing_was_altered": True,
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--cost-followup", action="store_true",
                        help="re-read the settled Bright Data meter")
    parser.add_argument("--counts", action="store_true",
                        help="the Milwaukee counters, each with its predicate")
    parser.add_argument("--supersede", action="store_true",
                        help="build the three superseding observations and the "
                             "differential; makes no provider call")
    parser.add_argument("--confirm-live", action="store_true",
                        help="one fresh capture of The Trade on its registered "
                             "route")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args(argv)

    if args.preflight:
        print(json.dumps(preflight(), indent=1))
        return 0

    if args.confirm_live:
        doc = asyncio.run(live_confirmation())
        print(summarise_live(doc))
        if args.write_report:
            CONFIRMATION.write_bytes(
                (json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
                .encode("utf-8"))
            print("\nreport: %s" % CONFIRMATION)
        return 0 if doc["passed"] else 1

    if args.cost_followup:
        print(json.dumps(cost_followup(), indent=1))
        return 0

    if args.counts:
        doc = milwaukee_counts()
        print(json.dumps({k: v for k, v in doc.items()
                          if k not in ("definitions", "reconciliation")},
                         indent=1))
        print()
        print(json.dumps(doc["reconciliation"], indent=1))
        if args.write_report:
            COUNTS.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False)
                                + "\n").encode("utf-8"))
            print("\nreport: %s" % COUNTS)
        return 0

    if args.supersede:
        doc = build_supersession()
        check = differential(doc)
        doc["differential"] = check
        for record in doc["records"]:
            print("=== %s  [%s]" % (record["canonical_name"],
                                    record["update_kind"]))
            print("   evidence : %s" % record["current"]["evidence_source"])
            print("   locator  : %s -> %s"
                  % (record["superseded"]["policy_locator"] or "-",
                     record["current"]["policy_locator"]))
            print("   020 said : %s" % record["superseded"]["fields_asserted"])
            print("   new      : %s" % json.dumps(record["current"]["extraction"]))
            print("   withheld : %s" % json.dumps(record["current"]["withheld"]))
            print("   review   : %s" % record["review_status"])
        print()
        print("differential clean: %s" % check["clean"])
        print("  expected  : %s" % len(check["expected_rows"]))
        print("  differ    : %s" % len(check["rows_that_differ"]))
        print("  unexpected: %s" % (check["unexpected_rows"] or "none"))
        print("  store rows %s -> %s, no-op: %s"
              % (check["store_rows_before"], check["store_rows_after_regeneration"],
                 check["store_regeneration_is_a_no_op"]))
        if args.write_report:
            SUPERSESSION.write_bytes(
                (json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
                .encode("utf-8"))
            print("\nreport: %s" % SUPERSESSION)
        return 0 if check["clean"] else 1

    parser.error("choose --preflight, --confirm-live or --supersede")


if __name__ == "__main__":
    raise SystemExit(main())
