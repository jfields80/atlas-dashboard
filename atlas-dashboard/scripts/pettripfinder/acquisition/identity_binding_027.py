"""PTF-CODELESS-INDEPENDENT-IDENTITY-BINDING-027 -- binding a hotel with no code.

Milwaukee finished 026 with twenty unresolved properties, half of them refused
by our own identity gate rather than by any site. Eight independents were
fetched successfully -- thirty to sixty-eight second real navigations -- and
thrown away because the code-less binding asked a question their pages could
not answer.

WHAT THE GATE ACTUALLY REQUIRED
-------------------------------
Two things had to be true and both were about URLs:

1. ``path_identity`` ignores any path with fewer than two segments, so it
   deliberately returns nothing for ``/`` and for ``/faq``. That rule exists to
   stop a brand homepage binding, and it is right about brand homepages. On a
   one-property site it also erases the only path there is.
2. The census address and telephone number -- which the queue has held all
   along -- were never handed to the capture. ``target_for`` said identity was
   "taken from the committed authority" while taking the name and the URL and
   nothing else, so the ZIP branch of the gate could never fire either.

Together those meant a code-less property could confirm only when its canonical
URL had two or more path segments AND equalled the URL we asked for.
``staycobblestone.com/wi/waukesha/`` satisfies that. An independent hotel whose
FAQ lives at ``/faq`` cannot, no matter how clearly the page identifies itself.

WHAT REPLACES IT
----------------
Nothing is removed. The path-and-name rule stands unchanged and everything it
confirmed it still confirms. Beside it sits a second, independent route: a page
binds when it agrees with the census on something PHYSICAL -- the street
identity, or the telephone line the property publishes -- and on a name whose
agreement survives deleting the words every hotel in the market shares.

Both halves are required. The street alone cannot separate the Motel 6 and the
Studio 6 that share one address in Brookfield. The name alone cannot separate
the Wildwood Lodge in Pewaukee from the Wildwood Lodge in Clive, Iowa. Neither
same-domain nor a related-looking URL is a signal here at all.

WHY THE REPLAY CANNOT PRODUCE THE POLICY
-----------------------------------------
The gate runs BEFORE artifacts are written, so a refused capture left no
policy block, no page text and no locator record. What the architecture did
retain is the rendered HTML the discovery run fetched from the same first-party
URLs, and that is enough to settle IDENTITY offline for six of the ten without
a single provider call.

It is not enough to settle POLICY. Under the canonical locator contract a
policy block is located once, at capture time, on the live page, and replayed
against a recorded boundary; a discovery artifact carries no such record and
cannot acquire one after the fact. So identity is proved from disk for free and
the policy is acquired once, on the committed route, only for the properties
whose identity the disk already confirmed.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
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
from scripts.pettripfinder.acquisition import identity_corpus_027 as CORPUS027  # noqa: E402
from scripts.pettripfinder.acquisition import registry as REGISTRY          # noqa: E402
from scripts.pettripfinder.acquisition import router as ROUTER              # noqa: E402
from scripts.pettripfinder.acquisition import source_selection as SS        # noqa: E402
from scripts.pettripfinder.acquisition import store_integration_025 as S    # noqa: E402
from scripts.pettripfinder.brightdata import corpus as CORPUS               # noqa: E402
from scripts.pettripfinder.brightdata import cross_brand_pilot_002 as P2    # noqa: E402
from scripts.pettripfinder.brightdata import marriott_surface as MS         # noqa: E402
from scripts.pettripfinder.brightdata import policy_locator as PL           # noqa: E402
from scripts.pettripfinder.brightdata import policy_surface as PS           # noqa: E402

WORK_ORDER = "PTF-CODELESS-INDEPENDENT-IDENTITY-BINDING-027"
MARKET = "milwaukee-wi"

REPORTS = REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
QUEUE_PATH = REPORTS / ("%s_policy_acquisition_queue_001.json" % MARKET)
COUNTS_026 = REPORTS / ("%s_counts_026.json" % MARKET)
STORE = REPORTS / ("%s_policy_proposals_001.json" % MARKET)
RUN_REPORT = REPORTS / "ptf_identity_binding_027.json"
COUNTS_REPORT = REPORTS / ("%s_counts_027.json" % MARKET)

RUN_ID = "milwaukee-identity-027"
RUN_ROOT = REPO / "data" / "acquisition" / RUN_ID
RUN_DIR = RUN_ROOT / RUN_ID
JOURNAL = RUN_ROOT / "journal.jsonl"

DATA = REPO / "data" / "acquisition"
DISCOVERY_014 = DATA / "independent-url-discovery-014" / "url-discovery-014"
DISCOVERY_REPORT = REPORTS / "ptf_independent_url_discovery_014.json"

EXPECTED_COHORT = 10
BILLABLE_ZONES = ("scraping_browser1", "mcp_unlocker", "cli_unlocker")

#: Why a page could not be replayed from disk.
PAGE_FETCHED_IDENTITY_REJECTED = "PAGE_FETCHED_IDENTITY_REJECTED"
NO_USABLE_CAPTURE_ARTIFACT = "NO_USABLE_CAPTURE_ARTIFACT"
REACQUISITION_REQUIRED = "REACQUISITION_REQUIRED"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")


# --------------------------------------------------------------------------- #
# Phase 1 -- the cohort, derived from the committed 026 counters.
# --------------------------------------------------------------------------- #

def census() -> Dict[str, Dict]:
    doc = json.loads(QUEUE_PATH.read_text(encoding="utf-8-sig"))
    return {row["identity_key"]: row for row in doc["items"]}


def cohort() -> List[str]:
    """The identities 026 recorded as IDENTITY_FAILURE, read from its counters.

    Derived, never listed: the queue in the committed counters report is the
    only place this cohort is defined, and a different reason there produces a
    different cohort here.
    """
    doc = json.loads(COUNTS_026.read_text(encoding="utf-8"))
    queue = doc["acquisition_unresolved"]["queue"]
    return sorted(row["identity_key"] for row in queue
                  if row["reason"] == "IDENTITY_FAILURE")


def assert_cohort() -> List[str]:
    keys = cohort()
    if len(keys) != EXPECTED_COHORT:
        raise SystemExit("ABORT: IDENTITY_FAILURE cohort is %d, expected %d"
                         % (len(keys), EXPECTED_COHORT))
    return keys


def preflight() -> Dict:
    store = json.loads(STORE.read_text(encoding="utf-8-sig"))
    counts = json.loads(COUNTS_026.read_text(encoding="utf-8"))
    keys = cohort()
    return {
        "checked_at": _now(),
        "store_rows": len(store["items"]),
        "published": sum(1 for row in store["items"] if row.get("published")),
        "authority_written": bool(store.get("authority_written")),
        "unresolved": counts["unresolved"],
        "unresolved_by_reason": dict(
            counts["acquisition_unresolved"]["by_reason"]),
        "identity_failure_cohort": keys,
        "assertions": {
            "cohort_is_10": len(keys) == EXPECTED_COHORT,
            "store_is_107": len(store["items"]) == 107,
            "unresolved_is_20": counts["unresolved"] == 20,
            "nothing_published": all(not row.get("published")
                                     for row in store["items"]),
        },
    }


# --------------------------------------------------------------------------- #
# Phase 2 -- what the failed attempts actually recorded.
# --------------------------------------------------------------------------- #

#: Runs whose journal can answer "what did we ask for, and what came back".
FAILURE_JOURNALS: Tuple[Tuple[str, str], ...] = (
    ("milwaukee-router-001",
     "milwaukee-router-001/milwaukee-router-001/journal.jsonl"),
    ("milwaukee-final-026", "milwaukee-final-026/journal.jsonl"),
)


def failure_rows() -> Dict[str, Dict]:
    """The newest journal row for every identity, across the failing runs."""
    rows: Dict[str, Dict] = {}
    for run_id, journal in FAILURE_JOURNALS:
        path = DATA / journal
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            entry["source_run"] = run_id
            rows[entry["identity_key"]] = entry
    return rows


def _requested_url(entry: Mapping, row: Mapping) -> str:
    return (entry.get("source_url") or entry.get("official_url")
            or row.get("official_url") or "")


def _final_url(entry: Mapping) -> str:
    attempts = ((entry.get("result") or {}).get("attempts")
                or entry.get("attempts"))
    if isinstance(attempts, list):
        for attempt in reversed(attempts):
            if isinstance(attempt, Mapping) and attempt.get("final_url"):
                return str(attempt["final_url"])
    return ""


def _page_title(entry: Mapping) -> str:
    attempts = ((entry.get("result") or {}).get("attempts")
                or entry.get("attempts"))
    if isinstance(attempts, list):
        for attempt in reversed(attempts):
            if isinstance(attempt, Mapping) and attempt.get("title"):
                return str(attempt["title"])
    return ""


DIAGNOSTIC_013 = DATA / "generic-reader-diagnostic-013" / "generic-diagnostic-013"
DIAGNOSTIC_REPORT = REPORTS / "ptf_generic_reader_diagnostic_013.json"


def diagnostic_artifacts() -> Dict[Tuple[str, str], Path]:
    """Retained diagnostic captures, keyed by (identity, the URL fetched).

    013 read every one of these properties at its CENSUS url -- which is the
    production source url for any property whose discovery overlay found no
    policy page. Those captures are as much a record of what the site says
    about itself as 014's are.
    """
    out: Dict[Tuple[str, str], Path] = {}
    if not DIAGNOSTIC_REPORT.is_file():
        return out
    doc = json.loads(DIAGNOSTIC_REPORT.read_text(encoding="utf-8"))
    for prop in doc.get("properties", []):
        html = DIAGNOSTIC_013 / _slug(prop["identity_key"]) / "rendered.html"
        if html.is_file() and prop.get("url"):
            out[(prop["identity_key"], prop["url"])] = html
    return out


def retained_captures() -> Dict[Tuple[str, str], Path]:
    """Every retained capture of a first-party page, by identity and URL.

    A refused capture writes nothing, so the only surviving record of these
    pages is what earlier read-only runs kept. Both are indexed by the URL that
    was actually fetched: a capture of a DIFFERENT page of the same site is
    evidence about that page, not this one, and is not substituted for it.
    """
    index = dict(discovery_artifacts())
    index.update(diagnostic_artifacts())
    return index


def discovery_artifacts() -> Dict[Tuple[str, str], Path]:
    """Retained discovery captures, keyed by (identity, the URL fetched).

    014 kept the rendered HTML of every first-party candidate it considered.
    Those are the only surviving captures of the pages the identity gate
    refused, because the gate runs before the production capture persists
    anything.
    """
    out: Dict[Tuple[str, str], Path] = {}
    if not DISCOVERY_REPORT.is_file():
        return out
    doc = json.loads(DISCOVERY_REPORT.read_text(encoding="utf-8"))
    for prop in doc.get("properties", []):
        key = prop["identity_key"]
        for candidate in prop.get("candidates_tried", []):
            url = candidate["url"]
            path = re.sub(r"^https?://[^/]+", "", url)
            folder = DISCOVERY_014 / ("%s--%s" % (_slug(key), _slug(path)))
            html = folder / "rendered.html"
            if html.is_file():
                out[(key, url)] = html
    return out


def evidence(key: str) -> Dict:
    """Everything on disk about one refused property, and what it proves.

    Separates a page we HAVE from a page we merely attempted. The distinction
    decides whether the repaired gate can be replayed for free.
    """
    row = census()[key]
    entry = failure_rows().get(key, {})
    requested = _requested_url(entry, row)
    artifact = retained_captures().get((key, requested))
    signals = None
    if artifact is not None:
        html = artifact.read_text(encoding="utf-8", errors="replace")
        signals = PS.read_identity(html, final_url=requested, title="",
                                   brand=row["brand"])
    return {
        "identity_key": key,
        "census_name": row["canonical_name"],
        "census_address": row["address"],
        "census_city": row["city"],
        "census_state": row["state"],
        "census_postal_code": row["postal_code"],
        "census_phone": row["phone"],
        "census_official_url": row["official_url"],
        "brand": row["brand"],
        "source_run": entry.get("source_run", ""),
        "selected_source_url": requested,
        "discovered_policy_url": (requested
                                  if entry.get("source_origin")
                                  == "DISCOVERED_POLICY_URL" else ""),
        "overlay_status": entry.get("overlay_status", ""),
        "fetched_document_url": _final_url(entry),
        "page_title": _page_title(entry),
        "old_failure": entry.get("failure", ""),
        "old_failure_class": entry.get("failure_class", ""),
        "old_final_state": entry.get("final_state", ""),
        "evidence_class": (PAGE_FETCHED_IDENTITY_REJECTED if artifact
                           else NO_USABLE_CAPTURE_ARTIFACT),
        "artifact": _rel(artifact) if artifact else "",
        "page_canonical_url": signals.canonical_url if signals else "",
        "page_name": signals.name_on_page if signals else "",
        "page_street": signals.address_on_page if signals else "",
        "page_postal_code": signals.postal_code if signals else "",
        "page_structured_phone": signals.phone_on_page if signals else "",
        "page_printed_phones": list(signals.phones_on_page) if signals else [],
        "page_structured_identity": bool(signals.jsonld_present) if signals
                                    else False,
        "same_registrable_domain": _registrable(requested) ==
                                   _registrable(row["official_url"]),
        "old_gate_reason": ("the code-less rule needed the page's canonical "
                            "PATH to equal the requested path and the census "
                            "street, ZIP and telephone were never passed to "
                            "the gate"),
    }


def _registrable(url: str) -> str:
    host = re.sub(r"^https?://", "", url or "").split("/")[0].lower()
    labels = [label for label in host.split(".") if label]
    return ".".join(labels[-2:]) if len(labels) >= 2 else host


# --------------------------------------------------------------------------- #
# Phase 4 / 12 -- the gate as it was, so a change can be measured.
# --------------------------------------------------------------------------- #

_LEGACY_SOURCE_PATH = "atlas-dashboard/scripts/pettripfinder/brightdata/policy_surface.py"


_LEGACY_CACHE: Dict[str, object] = {}


def legacy_assess():
    """``assess_identity`` exactly as committed at HEAD, as a callable.

    Cached, and deliberately so: reading it costs a ``git show``, and a replay
    that must prove it contacted no provider is measured with subprocess
    launches denied. Warming this once, before the proof, keeps a repository
    read from being mistaken for a network call.

    Read out of git rather than reimplemented: a hand-copied "old rule" is a
    second implementation that can disagree with the one that actually ran, and
    then the before/after numbers measure the copy.
    """
    if "assess" in _LEGACY_CACHE:
        return _LEGACY_CACHE["assess"]
    blob = subprocess.run(
        ["git", "show", "HEAD:%s" % _LEGACY_SOURCE_PATH],
        cwd=str(REPO), capture_output=True, text=True, encoding="utf-8",
        check=True).stdout
    start = blob.index("def assess_identity(")
    end = blob.index("def path_identity(", start)
    namespace: Dict = {"MS": MS, "List": List,
                       "path_identity": PS.path_identity}
    exec(compile(blob[start:end], "<policy_surface@HEAD>", "exec"), namespace)
    _LEGACY_CACHE["assess"] = namespace["assess_identity"]
    return _LEGACY_CACHE["assess"]


def read_signals(html: str, *, url: str, brand: str) -> MS.IdentitySignals:
    return PS.read_identity(html, final_url=url, title="", brand=brand)


def decide(signals: MS.IdentitySignals, expected: Mapping, *,
           assess=None) -> Dict:
    """One explainable identity decision."""
    assess = assess or PS.assess_identity
    kwargs = dict(expected_name=expected["name"],
                  expected_property_code=expected.get("property_code", ""),
                  expected_url=expected["url"],
                  expected_postal_code=expected.get("postal_code", ""))
    if assess is PS.assess_identity:
        kwargs.update(expected_street=expected.get("street", ""),
                      expected_phone=expected.get("phone", ""),
                      expected_locality=expected.get("locality", ""))
    result = assess(signals, **kwargs)
    return {
        "verdict": "PASS" if result.confirmed else "FAIL",
        "binding_method": getattr(result, "binding_method", ""),
        "matched": list(result.signals_matched),
        "conflicting": list(result.signals_conflicting),
        "reasons": list(result.reasons),
    }


def expected_from(row: Mapping, *, url: str = "") -> Dict:
    return {
        "name": row["canonical_name"],
        "property_code": (row.get("property_code") or "").lower(),
        "url": url or row["official_url"],
        "street": row.get("address", ""),
        "postal_code": row.get("postal_code", ""),
        "phone": row.get("phone", ""),
        "locality": "%s %s" % (row.get("city", ""), row.get("state", "")),
    }


def evaluate_case(case, *, assess=None) -> Dict:
    """One corpus case through the gate, exactly as production would ask it."""
    row = census()[case.identity_key]
    requested = case.requested_url or row["official_url"]
    signals = read_signals(case.load(),
                           url=case.fetched_url or requested,
                           brand=row["brand"])
    result = decide(signals, expected_from(row, url=requested), assess=assess)
    return {
        "case_id": case.case_id,
        "kind": case.kind,
        "scenario": case.scenario,
        "identity_key": case.identity_key,
        "expect": case.expect,
        "verdict": result["verdict"],
        "agrees": result["verdict"] == case.expect,
        "binding_method": result["binding_method"],
        "matched": result["matched"],
        "conflicting": result["conflicting"],
        "reasons": result["reasons"],
        "why": case.why,
    }


def evaluate_corpus(*, assess=None) -> List[Dict]:
    return [evaluate_case(case, assess=assess) for case in CORPUS027.available()]


def corpus_summary(*, assess=None) -> Dict:
    rows = evaluate_corpus(assess=assess)
    return {
        "cases": len(rows),
        "missing_artifacts": CORPUS027.missing(),
        "positives": sum(1 for r in rows if r["kind"] == CORPUS027.POSITIVE),
        "adversarial": sum(1 for r in rows
                           if r["kind"] == CORPUS027.ADVERSARIAL),
        "agreeing": sum(1 for r in rows if r["agrees"]),
        "disagreeing": [r for r in rows if not r["agrees"]],
        "rows": rows,
    }


# --------------------------------------------------------------------------- #
# Phase 7 -- offline replay.
# --------------------------------------------------------------------------- #

def replay(key: str) -> Dict:
    """The repaired gate against the persisted capture, with no provider call.

    A PASS here is decisive: the page on disk demonstrably identifies this
    property. A FAIL is not, when the artifact is a static discovery capture
    and the production lane renders -- structured data that appears only after
    hydration is absent from the file through no fault of the property. Those
    are classified for re-acquisition rather than declared to have failed.
    """
    ev = evidence(key)
    row = census()[key]
    out = dict(ev)
    out["previous_verdict"] = "FAIL"
    out["previous_reason"] = ev["old_failure"] or "IDENTITY_MISMATCH"
    if not ev["artifact"]:
        out.update(new_verdict="UNDETERMINED", binding_method="",
                   matched=[], conflicting=[], reasons=[],
                   policy_block_on_disk=False, policy_requires_capture=True,
                   disposition=REACQUISITION_REQUIRED,
                   disposition_why="the gate refused this page before any "
                                   "artifact was written and no retained "
                                   "capture of the same URL exists")
        return out

    html = (REPO / ev["artifact"]).read_text(encoding="utf-8", errors="replace")
    signals = read_signals(html, url=ev["selected_source_url"],
                           brand=row["brand"])
    expected = expected_from(row, url=ev["selected_source_url"])
    new = decide(signals, expected)
    old = decide(signals, expected, assess=legacy_assess())
    out.update(new_verdict=new["verdict"], binding_method=new["binding_method"],
               matched=new["matched"], conflicting=new["conflicting"],
               reasons=new["reasons"],
               old_gate_on_this_artifact=old["verdict"],
               old_gate_reasons=old["reasons"])
    if new["verdict"] == "PASS":
        out.update(disposition="IDENTITY_CONFIRMED_OFFLINE",
                   disposition_why="the retained capture of the page we "
                                   "fetched binds to this census row on %s"
                                   % new["binding_method"])
    else:
        out.update(disposition=REACQUISITION_REQUIRED,
                   disposition_why="the retained capture is a static fetch and "
                                   "publishes no signal that binds it; a "
                                   "rendered capture may carry structured "
                                   "identity the file does not")
    # No artifact in this corpus carries a canonical locator record, so none of
    # them can yield a policy block under the 019 contract, however clearly it
    # identifies the property.
    out["policy_block_on_disk"] = False
    out["policy_requires_capture"] = True
    return out


def replay_all() -> List[Dict]:
    return [replay(key) for key in assert_cohort()]


# --------------------------------------------------------------------------- #
# Phase 8 -- acquisition, on the committed route, only where required.
# --------------------------------------------------------------------------- #

def _record_for(row: Mapping) -> CORPUS.BenchmarkRecord:
    """A benchmark record carrying the census identity, and no policy value.

    The address, ZIP and telephone are the repair: they are what the identity
    gate needs and what ``target_for`` has always claimed to be passing.
    """
    return CORPUS.BenchmarkRecord(
        identity_key=row["identity_key"], name=row["canonical_name"],
        market_id=MARKET, brand=row["brand"],
        bucket=CORPUS.bucket_of(row["brand"]), source_url=row["official_url"],
        pets_allowed=None, facts={}, quotes=(), withheld_fields={},
        service_animal_statement="", categories=frozenset(), origin="census",
        street=row.get("address", ""), postal_code=row.get("postal_code", ""),
        phone=row.get("phone", ""),
        locality="%s %s" % (row.get("city", ""), row.get("state", "")))


def source_for(row: Mapping) -> Dict:
    selection = SS.select(row["identity_key"], row["official_url"],
                          market_id=MARKET)
    return {
        "census_url": row["official_url"],
        "selected_url": selection.selected_url,
        "source": selection.source,
        "overlay_status": selection.overlay_status,
        "changed": selection.selected_url != row["official_url"],
        "route_url": row["official_url"],
    }


#: Capture outcomes that can only be reached AFTER the identity gate has
#: confirmed. A page that got as far as "no policy block here" is a page the
#: gate accepted, and reading identity only off a successful DOCUMENT reports
#: those as identity failures -- which is the mistake this work order exists to
#: correct, made one layer up.
IDENTITY_PASSED_OUTCOMES = ("VALID", "POLICY_NOT_FOUND")
IDENTITY_REFUSED_OUTCOME = "IDENTITY_MISMATCH"


def identity_verdict(attempt_records, identity) -> str:
    """PASS / FAIL / NOT_REACHED for one routed acquisition.

    NOT_REACHED is a real third answer and not a soft FAIL: a provider that
    refused to navigate never showed the gate a page, and recording that as an
    identity failure would blame the binding for an access decision.
    """
    if identity.get("confirmed"):
        return "PASS"
    for record in reversed(list(attempt_records or ())):
        outcome = record.get("outcome", "")
        if outcome in IDENTITY_PASSED_OUTCOMES:
            return "PASS"
        if outcome == IDENTITY_REFUSED_OUTCOME:
            return "FAIL"
    return "NOT_REACHED"


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
    # A SUCCESSFUL capture carries its identity block on the document. A
    # REFUSED one does not: the router's ``ProviderAttempt`` has no field for
    # it, so the signals a refusal was based on never leave the capture.
    #
    # What does survive is the capture's own ``detail``, which is the joined
    # list of the assessment's reasons. That is recorded here verbatim, along
    # with every attempt, so a refusal in this run can be explained without
    # widening the router's envelope on the way past.
    identity: Dict = dict((document.identity or {})
                          if document is not None else {})
    attempt_records = [attempt.to_dict() for attempt in (result.attempts or ())]
    refusal_reason = ""
    for attempt in reversed(result.attempts or ()):
        if attempt.outcome == "IDENTITY_MISMATCH" and attempt.detail:
            refusal_reason = attempt.detail
            break
    verdict = assess_usable(document, identity_confirmed=bool(
        identity.get("confirmed", document is not None)))
    return {
        "identity_key": row["identity_key"],
        "canonical_name": row["canonical_name"],
        "brand": row["brand"],
        "source_url": source["selected_url"],
        "census_url": source["census_url"],
        "source_origin": source["source"],
        "overlay_status": source["overlay_status"],
        "provider_primary": (result.route or {}).get("provider", ""),
        "provider_used": (result.attempts[-1].provider
                          if result.attempts else ""),
        "providers_tried": list(result.providers_tried),
        "attempts": len(result.attempts),
        "final_state": result.state,
        "acquisition_status": ("ACQUIRED" if document is not None
                               else "NOT_ACQUIRED"),
        "identity_verdict": identity_verdict(attempt_records, identity),
        "identity_confirmed": identity_verdict(attempt_records,
                                               identity) == "PASS",
        "identity_binding_method": identity.get("binding_method", ""),
        "identity_matched": list(identity.get("matched", [])),
        "identity_conflicting": list(identity.get("conflicting", [])),
        "identity_reasons": list(identity.get("reasons", []))
                            or ([refusal_reason] if refusal_reason else []),
        "identity_signals": dict(identity.get("signals", {})),
        "attempt_records": attempt_records,
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
        "elapsed_seconds": round(time.monotonic() - began, 3),
        "estimated_bytes": result.cost.estimated_bytes,
        "completed_at": _now(),
    }


#: ``states_a_refusal`` is a REGEX over the block, and it reads "Pets are not
#: allowed in the Milwaukee Center Galleria" -- one room of a pet-friendly
#: hotel -- as a refusal of the whole property. The reader is not fooled: it
#: withholds ``pets_allowed`` as SOURCE_CONTRADICTORY and the store records no
#: refusal. Only the run report's WORDING was wrong, so only the wording is
#: corrected here. Widening the qualifier list is a reader change with its own
#: corpus and its own work order; nothing in this one depends on it.
def _reader_called_it_a_refusal(document) -> Optional[bool]:
    if document is None:
        return None
    extraction = dict((document.observation or {}).get("extraction") or {})
    if "pets_allowed" in extraction:
        return extraction["pets_allowed"] is False
    return None


def assess_usable(document, *, identity_confirmed: bool) -> Dict:
    """023's usable-policy bar, with identity taken from the router's own gate.

    ``usable_policy`` binds identity by comparing a brand property CODE. These
    properties have none, so that check answers "no" for every one of them and
    reports zero usable policies where there are real ones -- the same defect
    026 hit and corrected mid-run.

    The check is answered here from the gate that actually ran, and the verdict
    is then recomputed from the FULL check set rather than patched: a row that
    fails some other check must keep failing.
    """
    verdict = dict(H.usable_policy(document, expected_code=""))
    if document is None:
        return verdict
    checks = dict(verdict.get("checks") or {})
    checks["identity_bound_to_this_property"] = bool(identity_confirmed)
    failed = sorted(name for name, passed in checks.items() if not passed)
    read_as_refusal = _reader_called_it_a_refusal(document)
    refusal = (bool(verdict.get("states_a_refusal")) if read_as_refusal is None
               else read_as_refusal)
    verdict["block_matches_a_refusal_pattern"] = bool(
        verdict.get("states_a_refusal"))
    verdict["reader_read_it_as_a_refusal"] = read_as_refusal
    verdict["checks"] = checks
    verdict["verdict"] = H.USABLE if not failed else H.NOT_USABLE
    verdict["reason"] = (
        "property-bound refusal located and read" if refusal and not failed
        else "property-bound policy located and read" if not failed
        else "failed: %s" % ", ".join(failed))
    verdict["identity_bound_by"] = ("the router's identity gate, which binds "
                                    "this code-less property on its own "
                                    "signals")
    return verdict


def canonical_artifacts(slug: str) -> Dict:
    base = RUN_DIR / slug
    attempt = None
    if base.is_dir():
        for candidate in sorted(base.glob("attempt-*"), reverse=True):
            if (candidate / PL.BLOCK_ARTIFACT).is_file():
                attempt = candidate
                break
    if attempt is None:
        return {"present": False}
    replayed = PL.replay(attempt)
    return {
        "present": True,
        "attempt_dir": _rel(attempt),
        "policy_block": (attempt / PL.BLOCK_ARTIFACT).is_file(),
        "locator_json": (attempt / PL.LOCATOR_ARTIFACT).is_file(),
        "replay_status": replayed.status,
        "block_sha256": replayed.block_sha256,
        "canonical": replayed.canonical,
    }


def run(*, limit: int = 0, only: Sequence[str] = ()) -> List[Dict]:
    """Acquire the properties the replay says need a capture, resumably."""
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    done: Dict[str, Dict] = {}
    if JOURNAL.is_file():
        for line in JOURNAL.read_text(encoding="utf-8").splitlines():
            if line.strip():
                entry = json.loads(line)
                done[entry["identity_key"]] = entry

    rows = census()
    plan = [item for item in replay_all()
            if item["disposition"] in (REACQUISITION_REQUIRED,
                                       "IDENTITY_CONFIRMED_OFFLINE")]
    if only:
        plan = [item for item in plan if item["identity_key"] in set(only)]
    todo = [item for item in plan if item["identity_key"] not in done]
    if limit:
        todo = todo[:limit]

    for item in todo:
        result = asyncio.run(acquire(rows[item["identity_key"]]))
        with JOURNAL.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")
        done[result["identity_key"]] = result
    return [done[item["identity_key"]] for item in plan
            if item["identity_key"] in done]


def _rescore_usable(detail: Mapping, identity_confirmed: bool,
                    withheld: Sequence[str] = ()) -> Dict:
    """The same recomputation ``assess_usable`` does, applied to a stored row.

    Kept beside it deliberately: a verdict recorded by an earlier version of
    this run must never be authoritative for its own meaning, and re-running a
    provider to correct a LABEL would be paying for arithmetic.
    """
    out = dict(detail)
    checks = dict(out.get("checks") or {})
    # Only a FULL check set may be rescored. A row with no document carries no
    # checks worth the name, and flipping the one identity flag on it would
    # turn "nothing was acquired" into "a policy was located and read".
    if "policy_block_present" not in checks:
        return out
    checks["identity_bound_to_this_property"] = bool(identity_confirmed)
    failed = sorted(name for name, passed in checks.items() if not passed)
    read_as_refusal = out.get("reader_read_it_as_a_refusal")
    if read_as_refusal is None and "pets_allowed" in set(withheld or ()):
        # The reader withheld the allowed flag, so it asserted no refusal --
        # whatever a regex over the block matched.
        read_as_refusal = False
    refusal = (bool(out.get("states_a_refusal")) if read_as_refusal is None
               else bool(read_as_refusal))
    out["reader_read_it_as_a_refusal"] = read_as_refusal
    out["checks"] = checks
    out["verdict"] = H.USABLE if not failed else H.NOT_USABLE
    out["reason"] = (
        "property-bound refusal located and read" if refusal and not failed
        else "property-bound policy located and read" if not failed
        else "failed: %s" % ", ".join(failed))
    return out


def journal_rows() -> List[Dict]:
    """Journalled acquisitions, with every verdict re-derived on load.

    A row records what the capture DID; it is never trusted for what that
    means. 026 shipped two labels that were wrong in exactly that way, so the
    interpretation is recomputed here from the attempts every time.
    """
    if not JOURNAL.is_file():
        return []
    rows = [json.loads(line) for line in
            JOURNAL.read_text(encoding="utf-8").splitlines() if line.strip()]
    latest: Dict[str, Dict] = {}
    for row in rows:
        # Derived from the ATTEMPTS alone. The row's own identity block is
        # deliberately not consulted: a VALID or POLICY_NOT_FOUND outcome
        # already means the gate let the page through, and the block is empty
        # on exactly the rows whose verdict is in question.
        verdict = identity_verdict(row.get("attempt_records"),
                                   {"confirmed": False})
        row["identity_verdict"] = verdict
        row["identity_confirmed"] = verdict == "PASS"
        row["usable_policy_detail"] = _rescore_usable(
            row.get("usable_policy_detail") or {}, verdict == "PASS",
            withheld=row.get("reader_withheld") or ())
        row["usable_policy"] = row["usable_policy_detail"].get(
            "verdict", row.get("usable_policy", ""))
        latest[row["identity_key"]] = row
    return list(latest.values())


# --------------------------------------------------------------------------- #
# Phase 12 -- blast radius across every historical capture.
# --------------------------------------------------------------------------- #

def historical_captures() -> List[Dict]:
    """Every retained rendered capture whose expected identity is recoverable.

    Keyed back to the census by the capture directory's slug, which is how the
    capture named itself. A directory that no census row claims is skipped
    rather than guessed at.
    """
    by_slug: Dict[str, Dict] = {}
    for row in census().values():
        by_slug[_slug(row["canonical_name"])[:80]] = row
    out: List[Dict] = []
    for html in sorted(DATA.rglob("rendered.html")):
        parts = html.relative_to(DATA).parts
        slug = ""
        for part in parts:
            candidate = part.split("--")[0]
            if candidate in by_slug:
                slug = candidate
                break
        if not slug:
            continue
        out.append({"artifact": _rel(html), "slug": slug,
                    "identity_key": by_slug[slug]["identity_key"]})
    return out


def blast_radius() -> Dict:
    """Old gate against new gate on every historical capture, measured twice.

    TWO ARMS, BECAUSE TWO THINGS CHANGED
    ------------------------------------
    The repair is a rule AND a wiring fix, and conflating them would credit one
    for the other's effect. So both are measured:

    ``rule_only`` feeds both gates the SAME (new) inputs and isolates what the
    rule change does on its own.

    ``as_production_ran`` compares the old gate with the inputs production
    actually supplied it -- no street, no telephone, and an empty ZIP, because
    ``target_for`` never filled one -- against the new gate with the census
    behind it. That arm is what changes going forward.
    """
    legacy = legacy_assess()
    rows = census()
    rule_only = Counter()
    production = Counter()
    changed: List[Dict] = []
    tested = 0
    for item in historical_captures():
        row = rows[item["identity_key"]]
        html = (REPO / item["artifact"]).read_text(encoding="utf-8",
                                                   errors="replace")
        url = row["official_url"]
        signals = read_signals(html, url=url, brand=row["brand"])
        expected = expected_from(row, url=url)
        as_shipped = dict(expected, street="", phone="", postal_code="")
        old_same_inputs = decide(signals, expected, assess=legacy)
        old_as_ran = decide(signals, as_shipped, assess=legacy)
        new = decide(signals, expected)
        tested += 1
        rule_only["%s->%s" % (old_same_inputs["verdict"], new["verdict"])] += 1
        production["%s->%s" % (old_as_ran["verdict"], new["verdict"])] += 1
        if old_as_ran["verdict"] != new["verdict"]                 or old_same_inputs["verdict"] != new["verdict"]:
            changed.append({
                "identity_key": item["identity_key"],
                "artifact": item["artifact"],
                "old_as_production_ran": old_as_ran["verdict"],
                "old_same_inputs": old_same_inputs["verdict"],
                "new": new["verdict"],
                "binding_method": new["binding_method"],
                "matched": new["matched"],
                "conflicting": new["conflicting"],
                "why": new["reasons"][-1] if new["reasons"] else "",
            })
    def _arm(counter: Counter) -> Dict:
        return {
            "transitions": dict(counter),
            "pass_to_pass": counter["PASS->PASS"],
            "fail_to_fail": counter["FAIL->FAIL"],
            "fail_to_pass": counter["FAIL->PASS"],
            "pass_to_fail": counter["PASS->FAIL"],
        }
    return {
        "captures_tested": tested,
        "rule_only": _arm(rule_only),
        "as_production_ran": _arm(production),
        "changed": changed,
    }


# --------------------------------------------------------------------------- #
# Reporting.
# --------------------------------------------------------------------------- #

def read_spend(label: str) -> Dict:
    """026's meter reader, reused verbatim so two runs' costs are comparable."""
    from scripts.pettripfinder.acquisition import final_pass_026 as F26
    return F26.read_spend(label)


def spend_delta(before: Mapping, after: Mapping) -> Dict:
    from scripts.pettripfinder.acquisition import final_pass_026 as F26
    return F26.spend_delta(before, after)


COST_PATH = RUN_ROOT / "cost.json"


def record_spend(label: str) -> Dict:
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    ledger = {}
    if COST_PATH.is_file():
        ledger = json.loads(COST_PATH.read_text(encoding="utf-8"))
    ledger[label] = read_spend(label)
    if "before" in ledger and "after" in ledger:
        ledger["delta"] = spend_delta(ledger["before"], ledger["after"])
    COST_PATH.write_text(json.dumps(ledger, indent=2), encoding="utf-8")
    return ledger


def build_report(*, with_cost: bool = False) -> Dict:
    replays = replay_all()
    acquired = {row["identity_key"]: row for row in journal_rows()}
    for item in replays:
        row = acquired.get(item["identity_key"])
        item["provider_call_made"] = bool(row)
        item["final_identity_verdict"] = (
            "PASS" if (row or {}).get("identity_confirmed")
            else ("PASS" if item["new_verdict"] == "PASS" and not row
                  else "FAIL"))
        # The router does not forward the identity block on an attempt that
        # did not produce a document, so a property whose identity passed and
        # whose POLICY was absent has no method recorded on its row. The
        # offline replay of the same page does, and it is the same decision.
        item["final_binding_method"] = ((row or {}).get(
            "identity_binding_method") or item.get("binding_method", ""))
        item["policy_result"] = (row or {}).get("usable_policy",
                                                "NOT_ACQUIRED")
        item["publication_grade"] = bool((row or {}).get("publication_grade"))
    recovered = [item for item in replays
                 if item["final_identity_verdict"] == "PASS"]
    doc = {
        "schema": "ptf-identity-binding/1.0",
        "work_order": WORK_ORDER,
        "market": MARKET,
        "run_id": RUN_ID,
        "generated_at": _now(),
        "preflight": preflight(),
        "cohort_size": len(replays),
        "evidence_classes": dict(Counter(item["evidence_class"]
                                         for item in replays)),
        "dispositions": dict(Counter(item["disposition"] for item in replays)),
        "identity_recovered": len(recovered),
        "identity_still_failed": len(replays) - len(recovered),
        "binding_methods": dict(Counter(
            item["final_binding_method"] for item in recovered)),
        "usable_policy_recovered": sum(
            1 for item in replays if item["policy_result"] == H.USABLE),
        "publication_grade_recovered": sum(
            1 for item in replays if item["publication_grade"]),
        "provider_calls": sum(1 for item in replays
                              if item["provider_call_made"]),
        "offline_replays": sum(1 for item in replays if item["artifact"]),
        "blast_radius": blast_radius(),
        "authority_written": False,
        "published": 0,
        "rows": replays,
        "acquisition_rows": list(acquired.values()),
    }
    if with_cost and COST_PATH.is_file():
        doc["cost"] = json.loads(COST_PATH.read_text(encoding="utf-8"))
    return doc


def write_report(doc: Mapping) -> None:
    RUN_REPORT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")


# --------------------------------------------------------------------------- #
# Counters -- the same five predicates 025 and 026 use, recomputed.
# --------------------------------------------------------------------------- #

def touched_identities() -> set:
    """Every identity a production journal has an attempt for.

    Reads 025's own source list, so a run registered there is counted here
    without editing this file -- which is how 027 becomes "touched" the moment
    it is a production source.
    """
    from scripts.pettripfinder.acquisition import final_pass_026 as F26
    return F26.touched_identities()


def prior_reasons() -> Dict[str, Dict]:
    """What 026's committed counters said about each unresolved identity."""
    doc = json.loads(COUNTS_026.read_text(encoding="utf-8"))
    return {row["identity_key"]: row
            for row in doc["acquisition_unresolved"]["queue"]}


def unresolved_reason(key: str) -> Tuple[str, Dict]:
    """Why one identity still has no publication-grade observation.

    027 reclassifies ONLY what 027 re-acquired. Everything else keeps the
    reason the run that measured it recorded, because those journals do not all
    carry the fields this classifier reads -- and defaulting a missing field
    turns "the page published an amenity chip" into "the page published
    nothing", which is a different finding about a real hotel.
    """
    fresh = {row["identity_key"]: row for row in journal_rows()}
    if key in fresh:
        row = dict(fresh[key])
        reason = F026().classify_unresolved(
            row, {"overlay_status": row.get("overlay_status", "")})
        return reason or "", {"source_run": RUN_ID,
                              "final_state": row.get("final_state", ""),
                              "failure": row.get("failure", "")}
    prior = prior_reasons().get(key)
    if prior:
        return prior["reason"], {"source_run": prior.get("source_run", ""),
                                 "final_state": prior.get("final_state", ""),
                                 "failure": ""}
    return "INSUFFICIENT_EVIDENCE", {"source_run": "", "final_state": ""}


def F026():
    from scripts.pettripfinder.acquisition import final_pass_026 as module
    return module


def counters() -> Dict:
    """The five Milwaukee numbers, recomputed from the store and the journals."""
    rows = {key: row for key, row in census().items()
            if not row["brand_excluded"]}
    store = json.loads(STORE.read_text(encoding="utf-8-sig"))
    observed = {item["identity_key"] for item in store["items"]}
    touched = touched_identities() & set(rows)
    unresolved = sorted(set(rows) - observed)
    queue: List[Dict] = []
    for key in unresolved:
        reason, detail = unresolved_reason(key)
        queue.append({
            "identity_key": key,
            "canonical_name": rows[key]["canonical_name"],
            "brand": rows[key]["brand"],
            "source_run": detail.get("source_run", ""),
            "final_state": detail.get("final_state", ""),
            "reason": reason or "INSUFFICIENT_EVIDENCE",
        })
    return {
        "schema": "ptf-milwaukee-counts/1.2",
        "work_order": WORK_ORDER,
        "market": MARKET,
        "generated_at": _now(),
        "routable": len(rows),
        "touched": len(touched),
        "publication_grade": len(observed),
        "observed": len(observed),
        "unresolved": len(unresolved),
        "never_touched": len(set(rows) - touched),
        "published": sum(1 for item in store["items"]
                         if item.get("published")),
        "founder_approved": sum(1 for item in store["items"]
                                if item.get("founder_approved")),
        "invariant_observed_plus_unresolved": len(observed) + len(unresolved),
        "review_states": dict(Counter(item["review_status"]
                                      for item in store["items"])),
        "rows_by_run": dict(Counter(item["source_run"]
                                    for item in store["items"])),
        "milwaukee_policy_authority_files": len(list(
            (REPO / "launch_packages" / "pettripfinder")
            .rglob("*hotel_policy_facts*milwaukee*"))),
        "acquisition_unresolved": {
            "definition": ("touched but with no publication-grade observation; "
                           "these have NO current-state row"),
            "count": len(queue),
            "by_reason": dict(Counter(row["reason"] for row in queue)),
            "queue": queue,
        },
    }


def write_counters() -> Dict:
    doc = counters()
    COUNTS_REPORT.write_text(json.dumps(doc, indent=2, ensure_ascii=False),
                             encoding="utf-8")
    return doc


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=WORK_ORDER)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--replay", action="store_true")
    parser.add_argument("--blast-radius", action="store_true")
    parser.add_argument("--acquire", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--only", nargs="*", default=())
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--cost", action="store_true")
    parser.add_argument("--meter", choices=("before", "after"))
    parser.add_argument("--counters", action="store_true")
    args = parser.parse_args(argv)

    if args.meter:
        print(json.dumps(record_spend(args.meter), indent=2))
    if args.preflight:
        print(json.dumps(preflight(), indent=2))
    if args.replay:
        for item in replay_all():
            print("%-46s %s -> %-13s %-26s %s"
                  % (item["identity_key"], item["previous_verdict"],
                     item["new_verdict"], item["binding_method"] or "-",
                     item["disposition"]))
    if args.blast_radius:
        print(json.dumps(blast_radius(), indent=2)[:8000])
    if args.acquire:
        rows = run(limit=args.limit, only=args.only)
        for row in rows:
            print("%-46s %-28s %s" % (row["identity_key"], row["final_state"],
                                      row["usable_policy"]))
    if args.counters:
        doc = write_counters()
        print(json.dumps({k: v for k, v in doc.items()
                          if k != "acquisition_unresolved"}, indent=2))
        print(json.dumps(doc["acquisition_unresolved"]["by_reason"], indent=2))
    if args.report:
        doc = build_report(with_cost=args.cost)
        write_report(doc)
        print(json.dumps({k: v for k, v in doc.items()
                          if k not in ("rows", "acquisition_rows",
                                       "blast_radius", "preflight")},
                         indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
