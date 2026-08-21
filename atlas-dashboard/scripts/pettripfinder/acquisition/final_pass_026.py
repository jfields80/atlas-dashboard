"""PTF-MILWAUKEE-FINAL-ACQUISITION-PASS-026 -- the last sixteen.

Milwaukee has 127 routable properties and 111 have been touched. This acquires
the remaining sixteen on the committed architecture: current routes, the
committed discovery overlay, the canonical locator contract, the reader at
HEAD, and 025's store integration. It is not a benchmark and it changes no
route to improve a completion percentage.

THE COHORT IS DERIVED, NOT LISTED
----------------------------------
Sixteen identities in the routable queue that no production journal has
touched: four Motel 6, eleven independents, one Red Roof. The count and the
class split are asserted before a single provider call, and a mismatch aborts.

SOURCE SELECTION IS NOT PROVIDER SELECTION
-------------------------------------------
Eight of the eleven independents have a validated discovered policy URL, and
those are fetched instead of the homepage -- the census URL stays canonical
and unedited, and the router is still keyed on it, so choosing a better PAGE
never moves a property to a different LANE.

The other three are recorded ``NO_POLICY_URL_FOUND``. Nothing here invents
``/pets`` or ``/faq`` for them: the contract falls back to the census URL, the
capture reads whatever that page says, and the result is classified honestly.
A site that publishes no first-party policy is a fact about the site, not a
failure of the discovery layer.

WHAT COUNTS AS A POLICY
------------------------
Publication grade says the EVIDENCE is sound. It does not say a guest learned
anything. An amenity chip reading "Pets Allowed" with no terms is not a policy,
and neither is brand boilerplate with nothing binding it to this property. A
refusal is: "no pets allowed", property-bound, settles the question outright.

The reader at HEAD keeps every safeguard 010, 017, 021 and 024 added -- banded
fees, multi-component fees, contradictory bases and amenity chips are withheld
rather than flattened, and a policy the schema cannot carry is held rather than
reduced to whichever number parsed first.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import hilton_decision_023 as H      # noqa: E402
from scripts.pettripfinder.acquisition import marriott_decision_020 as D    # noqa: E402
from scripts.pettripfinder.acquisition import providers as PROVIDERS        # noqa: E402
from scripts.pettripfinder.acquisition import registry as REGISTRY          # noqa: E402
from scripts.pettripfinder.acquisition import router as ROUTER              # noqa: E402
from scripts.pettripfinder.acquisition import source_selection as SS        # noqa: E402
from scripts.pettripfinder.acquisition import store_integration_025 as S    # noqa: E402
from scripts.pettripfinder.brightdata import client as CLIENT               # noqa: E402
from scripts.pettripfinder.brightdata import corpus as CORPUS               # noqa: E402
from scripts.pettripfinder.brightdata import cross_brand_pilot_002 as P2    # noqa: E402
from scripts.pettripfinder.brightdata import policy_locator as PL           # noqa: E402

WORK_ORDER = "PTF-MILWAUKEE-FINAL-ACQUISITION-PASS-026"
MARKET = "milwaukee-wi"

REPORTS = REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
RUN_REPORT = REPORTS / "ptf_milwaukee_final_pass_026.json"
COUNTS_REPORT = REPORTS / "milwaukee-wi_counts_026.json"
STORE = REPORTS / ("%s_policy_proposals_001.json" % MARKET)

RUN_ID = "milwaukee-final-026"
RUN_ROOT = REPO / "data" / "acquisition" / RUN_ID
RUN_DIR = RUN_ROOT / RUN_ID
JOURNAL = RUN_ROOT / "journal.jsonl"

EXPECTED_SUBJECTS = 16
EXPECTED_CLASSES = {"MOTEL6": 4, "INDEPENDENT": 11, "RED_ROOF": 1}

BILLABLE_ZONES = ("scraping_browser1", "mcp_unlocker", "cli_unlocker")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def property_class(brand: str) -> str:
    if brand == "MOTEL6":
        return "MOTEL6"
    if brand == "RED_ROOF":
        return "RED_ROOF"
    return "INDEPENDENT"


# --------------------------------------------------------------------------- #
# Phase 1 -- the cohort.
# --------------------------------------------------------------------------- #

def touched_identities() -> set:
    """Every identity a production journal has an attempt for.

    Uses 025's own source list, so "touched" here means exactly what it means
    in the counters, and a run added there is counted here without editing this
    file.
    """
    touched = set()
    for _run, journal, _root in S.SOURCES:
        path = S.DATA / journal
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                touched.add(json.loads(line)["identity_key"])
    if JOURNAL.is_file():
        for line in JOURNAL.read_text(encoding="utf-8").splitlines():
            if line.strip():
                touched.add(json.loads(line)["identity_key"])
    return touched


def routable() -> Dict[str, Dict]:
    doc = json.loads(D.QUEUE_PATH.read_text(encoding="utf-8-sig"))
    return {r["identity_key"]: r for r in doc["items"] if not r["brand_excluded"]}


def cohort(*, include_done: bool = False) -> List[Dict]:
    """The never-touched sixteen, sorted for a stable run order."""
    rows = routable()
    done = set() if include_done else touched_identities()
    out = [r for k, r in rows.items() if k not in done]
    return sorted(out, key=lambda r: (property_class(r["brand"]),
                                      r["canonical_name"]))


def preflight() -> Dict:
    subjects = cohort()
    classes = Counter(property_class(r["brand"]) for r in subjects)
    store = json.loads(STORE.read_text(encoding="utf-8-sig"))
    rows = routable()
    return {
        "checked_at": _now(),
        "routable": len(rows),
        "touched": len(touched_identities() & set(rows)),
        "store_rows": len(store["items"]),
        "published": sum(1 for i in store["items"] if i.get("published")),
        "subject_count": len(subjects),
        "classes": dict(classes),
        "assertions": {
            "subject_count_is_16": len(subjects) == EXPECTED_SUBJECTS,
            "classes_match": {k: classes.get(k, 0) == v
                              for k, v in EXPECTED_CLASSES.items()},
        },
        "authority_files": len(list(
            (REPO / "launch_packages" / "pettripfinder")
            .rglob("*hotel_policy_facts*milwaukee*"))),
        "subjects": [{"identity_key": r["identity_key"],
                      "canonical_name": r["canonical_name"],
                      "brand": r["brand"],
                      "class": property_class(r["brand"]),
                      "official_url": r["official_url"]} for r in subjects],
    }


def assert_cohort() -> List[Dict]:
    checks = preflight()
    if not checks["assertions"]["subject_count_is_16"]:
        raise SystemExit("ABORT: cohort is %d, expected %d"
                         % (checks["subject_count"], EXPECTED_SUBJECTS))
    if not all(checks["assertions"]["classes_match"].values()):
        raise SystemExit("ABORT: class split is %s, expected %s"
                         % (checks["classes"], EXPECTED_CLASSES))
    return cohort()


# --------------------------------------------------------------------------- #
# Phase 2 -- source selection, through the committed seam.
# --------------------------------------------------------------------------- #

def source_for(row: Mapping) -> Dict:
    """Which page this property is read from, and where that came from.

    ``SourceSelection`` is read through its real fields -- ``selected_url`` and
    ``source`` -- and the ROUTE is resolved from the census URL, because
    ``registry.resolve`` keys on the host and a discovered URL on another host
    would otherwise move the property to a different provider.
    """
    selection = SS.select(row["identity_key"], row["official_url"],
                          market_id=MARKET)
    return {
        "census_url": row["official_url"],
        "selected_url": selection.selected_url,
        "source": selection.source,
        "overlay_present": selection.overlay_present,
        "overlay_status": selection.overlay_status,
        "provenance": dict(selection.provenance or {}),
        "changed": selection.selected_url != row["official_url"],
        "route_url": row["official_url"],
        "guessed": False,
    }


# --------------------------------------------------------------------------- #
# Phase 3-6 -- acquisition on the committed route.
# --------------------------------------------------------------------------- #

def _record_for(row: Mapping) -> "CORPUS.BenchmarkRecord":
    return CORPUS.BenchmarkRecord(
        identity_key=row["identity_key"], name=row["canonical_name"],
        market_id=MARKET, brand=row["brand"],
        bucket=CORPUS.bucket_of(row["brand"]), source_url=row["official_url"],
        pets_allowed=None, facts={}, quotes=(), withheld_fields={},
        service_animal_statement="", categories=frozenset(), origin="census")


def _attempt_dir(slug: str) -> Optional[Path]:
    base = RUN_DIR / slug
    if not base.is_dir():
        return None
    for attempt in sorted(base.glob("attempt-*"), reverse=True):
        if (attempt / PL.BLOCK_ARTIFACT).is_file():
            return attempt
    return None


def canonical_artifacts(slug: str) -> Dict:
    """What the canonical locator contract persisted for this capture."""
    attempt = _attempt_dir(slug)
    if attempt is None:
        return {"present": False}
    block = attempt / PL.BLOCK_ARTIFACT
    record = attempt / PL.LOCATOR_ARTIFACT
    replayed = PL.replay(attempt)
    return {
        "present": True,
        "attempt_dir": str(attempt.relative_to(REPO)).replace("\\", "/"),
        "policy_block": block.is_file(),
        "locator_json": record.is_file(),
        "rendered_artifact": (attempt / "rendered.html").is_file(),
        "replay_status": replayed.status,
        "block_sha256": replayed.block_sha256,
        "document_sha256": (replayed.record or {}).get("document_sha256", ""),
        "canonical": replayed.canonical,
    }


async def acquire(row: Mapping) -> Dict:
    source = source_for(row)
    record = _record_for(row)
    target = P2.target_for(record)
    if source["changed"]:
        target = SS._retargeted(target, source["selected_url"])

    began = time.monotonic()
    result = await ROUTER.route_property(
        record, target, run_dir=RUN_DIR, run_id=RUN_ID,
        registry=REGISTRY.load(), route_url=source["route_url"])
    document = result.document
    verdict = H.usable_policy(document, expected_code="")
    # Identity is confirmed by the router's own gate; the Hilton helper's
    # property-code check is brand-specific and does not apply off that brand.
    identity = bool((document.identity or {}).get("confirmed", True)) \
        if document is not None else False

    out = {
        "identity_key": row["identity_key"],
        "canonical_name": row["canonical_name"],
        "brand": row["brand"],
        "class": property_class(row["brand"]),
        "source_url": source["selected_url"],
        "census_url": source["census_url"],
        "source_origin": source["source"],
        "overlay_status": source["overlay_status"],
        "source_url_guessed": source["guessed"],
        "provider_primary": (result.route or {}).get("provider", ""),
        "provider_used": (result.attempts[-1].provider
                          if result.attempts else ""),
        "providers_tried": list(result.providers_tried),
        "attempts": len(result.attempts),
        "fallback_invoked": bool(result.cost.fallback_invoked),
        "final_state": result.state,
        "acquisition_status": ("ACQUIRED" if document is not None
                               else "NOT_ACQUIRED"),
        "identity_confirmed": identity,
        "policy_locator": (document.policy_locator if document else ""),
        "policy_block": verdict.get("block_text", ""),
        "policy_block_chars": verdict.get("block_chars", 0),
        "reader": (result.route or {}).get("reader", ""),
        "reader_fields": verdict.get("substantive_fields", []),
        "reader_withheld": verdict.get("withheld_fields", []),
        "states_a_refusal": verdict.get("states_a_refusal", False),
        "publication_grade": result.state == "ACQUIRED_PUBLICATION_GRADE",
        "usable_policy": verdict["verdict"],
        "usable_policy_detail": verdict,
        "canonical_artifacts": canonical_artifacts(target.slug),
        "failure": result.failure,
        "failure_class": result.failure_class,
        "escalation_stopped_because": result.escalation_stopped_because,
        "elapsed_seconds": round(time.monotonic() - began, 3),
        "estimated_bytes": result.cost.estimated_bytes,
        "reported_credits": result.cost.reported_credits,
    }
    out["unresolved_reason"] = classify_unresolved(out, source)
    return out


def assess_usable(document, *, identity_confirmed: bool) -> Dict:
    """Whether this capture yielded meaningful property-bound pet policy.

    ``hilton_decision_023.usable_policy`` binds identity through a Hilton
    property CODE, which most of this cohort does not have -- an independent
    hotel has no code in its URL and the code-less binding lives in the
    router's own identity gate instead. So identity is taken from the gate that
    actually ran: the router returns a document only when identity confirmed,
    because IDENTITY_MISMATCH is terminal and yields none.

    Everything else is the shared bar: a block, not a shell, not
    service-animal-only, and terms or a refusal that the reader either
    represents or withholds honestly.
    """
    if document is None:
        return {"verdict": H.NOT_USABLE, "reason": "no document was acquired",
                "checks": {}}
    observation = dict(document.observation or {})
    extraction = dict(observation.get("extraction") or {})
    withheld = dict(document.withheld_fields or {})
    block = (document.policy_text or "").strip()
    substantive = sorted(set(extraction) & H.SUBSTANTIVE_FIELDS)
    refusal = D.states_a_refusal(block)
    substantive_or_refusal = bool(substantive) or refusal

    checks = {
        "identity_confirmed": bool(identity_confirmed),
        "policy_block_present": bool(block),
        "block_is_not_a_shell": refusal or len(block) >= 40,
        "not_service_animal_only": not H.service_animal_only(block),
        "states_terms_or_a_refusal": substantive_or_refusal or bool(withheld),
        "not_a_bare_allowed_flag": substantive_or_refusal,
    }
    failed = sorted(k for k, v in checks.items() if not v)
    return {
        "verdict": H.USABLE if not failed else H.NOT_USABLE,
        "reason": ("property-bound policy located and read" if not failed
                   else "failed: %s" % ", ".join(failed)),
        "checks": checks, "states_a_refusal": refusal,
        "substantive_fields": substantive,
        "withheld_fields": sorted(withheld),
        "block_chars": len(block), "block_text": block,
        "policy_locator": document.policy_locator,
    }


def reassess_row(row: Mapping) -> Dict:
    """Recompute a journalled row's verdict from what it persisted.

    The block, the reader's fields and its withholdings are all in the journal,
    so the verdict is a function of them and can be corrected without touching
    a provider. This work order corrected that function mid-run -- it had been
    binding identity through a Hilton property code that this cohort does not
    have -- and a journal row must not be authoritative for its own label.
    """
    if row.get("acquisition_status") != "ACQUIRED":
        return dict(row.get("usable_policy_detail") or {})
    block = (row.get("policy_block") or "").strip()
    substantive = sorted(row.get("reader_fields") or [])
    withheld = sorted(row.get("reader_withheld") or [])
    refusal = D.states_a_refusal(block)
    substantive_or_refusal = bool(substantive) or refusal
    checks = {
        "identity_confirmed": True,          # the router returned a document
        "policy_block_present": bool(block),
        "block_is_not_a_shell": refusal or len(block) >= 40,
        "not_service_animal_only": not H.service_animal_only(block),
        "states_terms_or_a_refusal": substantive_or_refusal or bool(withheld),
        "not_a_bare_allowed_flag": substantive_or_refusal,
    }
    failed = sorted(k for k, v in checks.items() if not v)
    return {
        "verdict": H.USABLE if not failed else H.NOT_USABLE,
        "reason": ("property-bound policy located and read" if not failed
                   else "failed: %s" % ", ".join(failed)),
        "checks": checks, "states_a_refusal": refusal,
        "substantive_fields": substantive, "withheld_fields": withheld,
        "block_chars": len(block), "block_text": block,
        "policy_locator": row.get("policy_locator", ""),
    }


# --------------------------------------------------------------------------- #
# Phase 12 -- the exception taxonomy.
# --------------------------------------------------------------------------- #

POLICY_NOT_PRESENT = "POLICY_NOT_PRESENT"
AMENITY_ONLY = "AMENITY_ONLY"
ACCESS_FAILURE = "ACCESS_FAILURE"
IDENTITY_FAILURE = "IDENTITY_FAILURE"
SOURCE_NOT_FOUND = "SOURCE_NOT_FOUND"
INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


def classify_unresolved(row: Mapping, source: Mapping) -> str:
    """One reason a property has no usable policy. Empty when it has one."""
    if row["usable_policy"] == H.USABLE:
        return ""
    if row["acquisition_status"] != "ACQUIRED":
        # The router's own failure code decides. A page that arrived and was
        # refused by the identity gate is not an access failure, and calling it
        # one would blame the provider for a binding decision it never made.
        failure = (row.get("failure") or "").upper()
        if "IDENTITY" in failure:
            return IDENTITY_FAILURE
        if failure in ("POLICY_NOT_FOUND",):
            return POLICY_NOT_PRESENT
        return ACCESS_FAILURE
    if not row["identity_confirmed"]:
        return IDENTITY_FAILURE
    block = (row.get("policy_block") or "").strip()
    if not block:
        # The page arrived and said nothing about pets. Where the overlay also
        # found no policy URL, the honest reading is that the site publishes
        # none -- not that discovery failed.
        return (SOURCE_NOT_FOUND
                if source.get("overlay_status") == "NO_POLICY_URL_FOUND"
                else POLICY_NOT_PRESENT)
    if not row["reader_fields"] and not row["reader_withheld"] \
            and not row["states_a_refusal"]:
        return AMENITY_ONLY
    return INSUFFICIENT_EVIDENCE


# --------------------------------------------------------------------------- #
# Cost.
# --------------------------------------------------------------------------- #

def read_spend(label: str) -> Dict:
    zones = {}
    for zone in BILLABLE_ZONES:
        zones[zone] = CLIENT.read_usage("%s:%s" % (label, zone),
                                        zone=zone).cost_month_usd_minor
    try:
        from scripts.pettripfinder.acquisition import firecrawl_capture as FC
        credits = FC.credits_remaining()
    except Exception:                                            # noqa: BLE001
        credits = None
    return {"label": label, "read_at": _now(),
            "brightdata_zone_cost_month_usd_minor": zones,
            "firecrawl_credits_remaining": credits}


def spend_delta(before: Mapping, after: Mapping) -> Dict:
    zones, total = {}, 0
    for zone in BILLABLE_ZONES:
        a = before["brightdata_zone_cost_month_usd_minor"].get(zone)
        b = after["brightdata_zone_cost_month_usd_minor"].get(zone)
        if a is None or b is None:
            zones[zone], total = None, None
            continue
        zones[zone] = max(0, b - a)
        if total is not None:
            total += zones[zone]
    ca = before.get("firecrawl_credits_remaining")
    cb = after.get("firecrawl_credits_remaining")
    return {
        "brightdata_usd_minor_by_zone": zones,
        "brightdata_usd_minor_total": total,
        "brightdata_measurement_status": ("MEASURED" if total
                                          else "UNSETTLED_AT_READ_TIME"),
        "firecrawl_credits_consumed": ((ca - cb) if (ca is not None
                                                     and cb is not None) else None),
        "note": ("Bright Data bills dollars and Firecrawl plan credits; the two "
                 "are never summed. The zone meter settles behind the traffic "
                 "that moved it, so a zero over a short window is unsettled "
                 "rather than free."),
    }


# --------------------------------------------------------------------------- #
# The run.
# --------------------------------------------------------------------------- #

async def run(limit: Optional[int] = None) -> Dict:
    subjects = assert_cohort() if not JOURNAL.is_file() else None
    if subjects is None:
        # Resuming: the cohort is the original sixteen, so already-journalled
        # identities must not be filtered out of it by their own journal.
        done_here = {json.loads(l)["identity_key"]
                     for l in JOURNAL.read_text(encoding="utf-8").splitlines()
                     if l.strip()}
        rows = routable()
        others = touched_identities() - done_here
        subjects = sorted([r for k, r in rows.items() if k not in others],
                          key=lambda r: (property_class(r["brand"]),
                                         r["canonical_name"]))
        if len(subjects) != EXPECTED_SUBJECTS:
            raise SystemExit("ABORT: resumed cohort is %d, expected %d"
                             % (len(subjects), EXPECTED_SUBJECTS))

    RUN_DIR.mkdir(parents=True, exist_ok=True)
    done: Dict[str, Dict] = {}
    if JOURNAL.is_file():
        for line in JOURNAL.read_text(encoding="utf-8").splitlines():
            if line.strip():
                entry = json.loads(line)
                done[entry["identity_key"]] = entry

    before = read_spend("026:before")
    out: List[Dict] = []
    fresh = 0
    for row in subjects:
        key = row["identity_key"]
        if key in done:
            entry = dict(done[key])
            # Re-derived rather than trusted: both the verdict and the label
            # are functions of what the row persisted, and this work order
            # corrected both mid-run.
            verdict = reassess_row(entry)
            entry["usable_policy_detail"] = verdict
            entry["usable_policy"] = verdict.get(
                "verdict", entry.get("usable_policy"))
            entry["states_a_refusal"] = verdict.get("states_a_refusal", False)
            entry["unresolved_reason"] = classify_unresolved(
                entry, source_for(row))
            out.append(entry)
            continue
        if limit is not None and fresh >= limit:
            continue
        try:
            result = await acquire(row)
        except Exception as exc:                                  # noqa: BLE001
            result = {"identity_key": key, "canonical_name": row["canonical_name"],
                      "brand": row["brand"], "class": property_class(row["brand"]),
                      "acquisition_status": "NOT_ACQUIRED", "final_state": "EXCEPTION",
                      "usable_policy": H.NOT_USABLE, "publication_grade": False,
                      "policy_block": "", "policy_block_chars": 0,
                      "reader_fields": [], "reader_withheld": [],
                      "providers_tried": [], "attempts": 0,
                      "canonical_artifacts": {"present": False},
                      "unresolved_reason": ACCESS_FAILURE,
                      "failure": repr(exc)[:200]}
        with JOURNAL.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")
        out.append(result)
        fresh += 1
    after = read_spend("026:after")

    complete = len(out) == len(subjects)
    acquired = [r for r in out if r["acquisition_status"] == "ACQUIRED"]
    usable = [r for r in out if r["usable_policy"] == H.USABLE]
    graded = [r for r in out if r.get("publication_grade")]
    unresolved = [r for r in out if r["usable_policy"] != H.USABLE]

    return {
        "schema": "ptf-milwaukee-final-pass/1.0",
        "work_order": WORK_ORDER,
        "market": MARKET,
        "run_id": RUN_ID,
        "generated_at": _now(),
        "subject_count": len(subjects),
        "processed": len(out),
        "run_complete": complete,
        "assertions": {"subject_count_is_16": len(subjects) == EXPECTED_SUBJECTS},
        "acquired": len(acquired),
        "usable_policy": len(usable),
        "publication_grade": len(graded),
        "unresolved": len(unresolved),
        "by_class": {cls: {
            "attempted": sum(1 for r in out if r["class"] == cls),
            "acquired": sum(1 for r in acquired if r["class"] == cls),
            "usable": sum(1 for r in usable if r["class"] == cls),
            "publication_grade": sum(1 for r in graded if r["class"] == cls),
            "unresolved": sum(1 for r in unresolved if r["class"] == cls),
        } for cls in sorted(EXPECTED_CLASSES)},
        "provider_mix": dict(Counter(r.get("provider_used", "") for r in acquired)),
        "fallback_uses": sum(1 for r in out if r.get("fallback_invoked")),
        "source_selection": {
            "overlay_backed": sum(1 for r in out
                                  if r.get("source_origin") == SS.FROM_DISCOVERY),
            "census_fallback": sum(1 for r in out
                                   if r.get("source_origin") == SS.FROM_CENSUS),
            "no_policy_url_found": sum(
                1 for r in out if r.get("overlay_status") == "NO_POLICY_URL_FOUND"),
            "guessed_urls": sum(1 for r in out if r.get("source_url_guessed")),
        },
        "canonical_locator": {
            "captures_with_block": sum(1 for r in out
                                       if (r.get("canonical_artifacts") or {})
                                       .get("policy_block")),
            "captures_with_locator_record": sum(
                1 for r in out if (r.get("canonical_artifacts") or {})
                .get("locator_json")),
            "replayed_canonically": sum(
                1 for r in out if (r.get("canonical_artifacts") or {})
                .get("canonical")),
        },
        "unresolved_reasons": dict(Counter(r["unresolved_reason"]
                                           for r in unresolved)),
        "cost": {"delta": spend_delta(before, after),
                 "readings": [before, after]},
        "authority_written": False,
        "published": False,
        "rows": out,
    }


def summarise(doc: Mapping) -> str:
    lines = ["%s" % doc["work_order"],
             "subjects %d | processed %d | complete %s"
             % (doc["subject_count"], doc["processed"], doc["run_complete"]), ""]
    for row in doc["rows"]:
        lines.append("%-12s %-44s %-9s %-7s %-22s %s"
                     % (row["class"], row["canonical_name"][:44],
                        row["acquisition_status"][:9],
                        "USABLE" if row["usable_policy"] == H.USABLE else "NO",
                        (row.get("policy_locator") or "-")[:22],
                        row.get("unresolved_reason") or ""))
    lines += ["", "acquired %d | usable %d | publication-grade %d | unresolved %d"
              % (doc["acquired"], doc["usable_policy"], doc["publication_grade"],
                 doc["unresolved"]),
              "by class: %s" % json.dumps(doc["by_class"]),
              "providers: %s | fallbacks %s"
              % (doc["provider_mix"], doc["fallback_uses"]),
              "source: %s" % json.dumps(doc["source_selection"]),
              "locator: %s" % json.dumps(doc["canonical_locator"]),
              "unresolved reasons: %s" % doc["unresolved_reasons"],
              "cost: brightdata %s (%s) | firecrawl %s credits"
              % (doc["cost"]["delta"]["brightdata_usd_minor_total"],
                 doc["cost"]["delta"]["brightdata_measurement_status"],
                 doc["cost"]["delta"]["firecrawl_credits_consumed"])]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args(argv)

    if args.preflight:
        print(json.dumps(preflight(), indent=1))
        return 0
    if args.run:
        doc = asyncio.run(run(limit=args.limit))
        print(summarise(doc))
        if args.write_report and doc["run_complete"]:
            RUN_REPORT.write_bytes(
                (json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
                .encode("utf-8"))
            print("\nreport: %s" % RUN_REPORT)
        return 0
    parser.error("choose --preflight or --run")


__all__ = ["WORK_ORDER", "RUN_ID", "RUN_DIR", "JOURNAL", "EXPECTED_SUBJECTS",
           "EXPECTED_CLASSES", "property_class", "cohort", "preflight",
           "assert_cohort", "source_for", "acquire", "classify_unresolved",
           "canonical_artifacts", "run", "touched_identities", "routable",
           "POLICY_NOT_PRESENT", "AMENITY_ONLY", "ACCESS_FAILURE",
           "IDENTITY_FAILURE", "SOURCE_NOT_FOUND", "INSUFFICIENT_EVIDENCE"]


if __name__ == "__main__":
    raise SystemExit(main())
