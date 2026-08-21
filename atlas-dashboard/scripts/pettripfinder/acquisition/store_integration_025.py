"""PTF-MILWAUKEE-OBSERVATION-STORE-INTEGRATION-025 -- one current-state store.

The Milwaukee observation store was a projection of ONE journal,
``milwaukee-router-001``. Every work order since has said so and left it alone,
because widening it inside an acquisition or reader work order would have added
rows nobody had measured. This work order is the one authorised to widen it.

WHAT WAS OUTSIDE THE STORE, AND WHY THE NUMBER IS BIGGER THAN EXPECTED
----------------------------------------------------------------------
The brief named two runs: Marriott (020, 17 rows) and Hilton (023, 11 rows).
Enumerating every run on disk found three more that hold Milwaukee production
observations at publication grade, for identities in neither the store nor the
router journal:

    milwaukee-resume-007      4    Choice and independents
    milwaukee-wyndham-008    11    Wyndham
    milwaukee-ihg-009         5    IHG

Sixteen of those twenty are routable identities that 022 and 023 both counted
as NEVER TOUCHED. They were not: they were acquired at publication grade by
earlier runs, and the "touched" figure those work orders reported -- 95 -- was
computed from router-001 plus 020 plus 023 and missed them. The corrected
figures are touched 111 and never-touched 16, and the sixteen brands line up
exactly with the ones 023 listed as untouched: Wyndham 7, IHG 5, Choice 4.

That is a correction to this programme's own bookkeeping, and the runs are
included here because they meet the stated criterion -- eligible production
observations from completed Milwaukee runs -- not because the count was
expected.

ONE ROW PER IDENTITY, AND NEVER A SYNTHETIC ONE
------------------------------------------------
Selection order: an explicit supersession lineage wins; otherwise the newest
eligible production observation wins. Fields are never merged across
observations, because a row assembled from two captures describes no page that
ever existed. Two production observations that disagree with no supersession
metadata are held as CURRENT_STATE_CONFLICT rather than resolved by guess.

Decision tests, controls, benchmarks, diagnostics and replays are excluded by
name and by kind. A control capture must never outrank a production one.

WHERE THE FACTS COME FROM
--------------------------
Only the router run journalled a full observation. The other sources journalled
identity and outcome, so their facts are re-derived from the persisted policy
block with the reader at HEAD -- which is also how the sixteen records queued
by 024 are corrected. Nothing is re-fetched and nothing is re-located: the
block a capture chose is the block its record is about, which is the rule 018
established and 022 applied.

The rows are written through the store's own builder, which owns the shaping,
the frozen-semantics gate and the review status, so every row -- old or new --
is gated by one code path. Nothing here publishes, approves, or writes
authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder import milwaukee_policy_proposals_001 as PROP    # noqa: E402
from scripts.pettripfinder.acquisition import generic_reader_024 as G       # noqa: E402
from scripts.pettripfinder.acquisition import hilton_decision_023 as H      # noqa: E402
from scripts.pettripfinder.acquisition import marriott_closure_022 as C     # noqa: E402
from scripts.pettripfinder.acquisition import marriott_decision_020 as D    # noqa: E402
from scripts.pettripfinder.brightdata import marriott_surface as MS         # noqa: E402
from scripts.pettripfinder.brightdata import policy_locator as PL           # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR           # noqa: E402

WORK_ORDER = "PTF-MILWAUKEE-OBSERVATION-STORE-INTEGRATION-025"
MARKET = "milwaukee-wi"

REPORTS = REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
STORE = REPORTS / ("%s_policy_proposals_001.json" % MARKET)
INTEGRATION_REPORT = REPORTS / "ptf_milwaukee_store_integration_025.json"
DATA = REPO / "data" / "acquisition"

PUBLICATION_GRADE = "ACQUIRED_PUBLICATION_GRADE"

# --------------------------------------------------------------------------- #
# Phase 2 -- every run, classified.
# --------------------------------------------------------------------------- #

CURRENT_PRODUCTION = "CURRENT_PRODUCTION_SOURCE"
SUPERSEDING = "SUPERSEDING_OBSERVATION"
DECISION_TEST = "DECISION_TEST_ONLY"
CONTROL = "CONTROL_ONLY"
BENCHMARK = "BENCHMARK_ONLY"
DIAGNOSTIC = "DIAGNOSTIC_ONLY"
REPLAY = "REPLAY_ONLY"

#: Every run directory on disk, and what it is. Classified by what the run WAS
#: -- its work order's purpose -- not by whether its captures happen to look
#: usable. A control capture that reads cleanly is still a control.
RUN_KINDS: Dict[str, Tuple[str, str]] = {
    "milwaukee-router-001": (CURRENT_PRODUCTION,
                             "the Milwaukee market acquisition run"),
    "milwaukee-resume-007": (CURRENT_PRODUCTION,
                             "the market run resumed after the cost checkpoint"),
    "milwaukee-wyndham-008": (CURRENT_PRODUCTION,
                              "the Wyndham production lane, journalled under "
                              "the resume-007 tree"),
    "milwaukee-ihg-009": (CURRENT_PRODUCTION, "the IHG production lane"),
    "marriott-milwaukee-020": (CURRENT_PRODUCTION,
                               "the Marriott production run"),
    "hilton-milwaukee-023": (CURRENT_PRODUCTION, "the Hilton production run"),
    "milwaukee-final-026": (CURRENT_PRODUCTION,
                            "the final pass over the sixteen never-touched "
                            "properties"),
    # Added by PTF-CODELESS-INDEPENDENT-IDENTITY-BINDING-027: the identity
    # failures re-acquired once the code-less binding could see the census
    # street and telephone.
    "milwaukee-identity-027": (CURRENT_PRODUCTION,
                               "the code-less identity repair's re-acquisition"),
    # Added by PTF-HYATT-BEST-WESTERN-PREMIUM-RESOLUTION-028: the premium-domain
    # bucket, acquirable once the Bright Data plan covered Hyatt and Best
    # Western.
    "milwaukee-premium-028": (CURRENT_PRODUCTION,
                              "the Hyatt and Best Western premium-domain run"),
    # Added by PTF-MILWAUKEE-HIGH-VALUE-REPAIR-WAVE-032: blocks recovered
    # offline from documents earlier runs already persisted. No provider was
    # contacted; the document sha256 matches the capture it came from.
    "milwaukee-locator-032": (CURRENT_PRODUCTION,
                              "the offline richer-block recovery"),
    "marriott-closure-022": (SUPERSEDING,
                             "one fresh capture confirming the corrected "
                             "Marriott locator; supersedes The Trade"),
    "marriott-decision-020": (DECISION_TEST, "Firecrawl decision test"),
    "marriott-decision-020-control": (CONTROL, "Browser API control"),
    "hilton-decision-023": (DECISION_TEST, "Firecrawl decision test"),
    "hilton-decision-023-control": (CONTROL, "Browser API control"),
    "firecrawl-benchmark-002": (BENCHMARK, "provider benchmark"),
    "spider-benchmark-001": (BENCHMARK, "provider benchmark"),
    "firecrawl-hard-lanes-003": (DECISION_TEST, "hard-lane capability test"),
    "firecrawl-choice-validation-004": (DECISION_TEST, "Choice lane validation"),
    "choice-failure-retry-005": (DECISION_TEST, "Choice retry measurement"),
    "choice-route-proof-006": (DECISION_TEST, "Choice route proof"),
    "wyndham-firecrawl-decision-008": (DECISION_TEST, "Wyndham lane decision"),
    "ihg-firecrawl-decision-009": (DECISION_TEST, "IHG lane decision"),
    "motel6-firecrawl-decision-012": (DECISION_TEST, "Motel6 lane decision"),
    "reader-differential-010": (DIAGNOSTIC, "reader differential"),
    "generic-reader-diagnostic-013": (DIAGNOSTIC, "reader diagnostic"),
    "independent-url-discovery-014": (DIAGNOSTIC, "policy-URL discovery"),
    "source-discovery-replay-015": (REPLAY, "discovery replay"),
    "locator-fresh-proof-019a": (REPLAY, "canonical locator fresh proof"),
    "firecrawl-countryinn-addendum": (DECISION_TEST,
                                      "Country Inn addendum to the Choice "
                                      "validation; no policy blocks persisted"),
}

#: Where each eligible production run's journal lives, and the capture root its
#: persisted blocks sit under. Explicit, because "find every journal" would
#: sweep controls and benchmarks in with the rest.
SOURCES: Tuple[Tuple[str, str, str], ...] = (
    ("milwaukee-router-001",
     "milwaukee-router-001/milwaukee-router-001/journal.jsonl",
     "milwaukee-router-001/milwaukee-router-001"),
    ("milwaukee-resume-007",
     "milwaukee-resume-007/milwaukee-resume-007/journal.jsonl",
     "milwaukee-resume-007/milwaukee-resume-007"),
    ("milwaukee-wyndham-008",
     "milwaukee-resume-007/milwaukee-wyndham-008/journal.jsonl",
     "milwaukee-resume-007/milwaukee-wyndham-008"),
    ("milwaukee-ihg-009",
     "milwaukee-ihg-009/milwaukee-ihg-009/journal.jsonl",
     "milwaukee-ihg-009/milwaukee-ihg-009"),
    ("marriott-milwaukee-020",
     "marriott-milwaukee-020/marriott-milwaukee-020/journal.jsonl",
     "marriott-milwaukee-020/marriott-milwaukee-020"),
    ("hilton-milwaukee-023",
     "hilton-milwaukee-023/journal.jsonl",
     "hilton-milwaukee-023/hilton-milwaukee-023"),
    # Added by PTF-MILWAUKEE-FINAL-ACQUISITION-PASS-026, the last sixteen.
    ("milwaukee-final-026",
     "milwaukee-final-026/journal.jsonl",
     "milwaukee-final-026/milwaukee-final-026"),
    # Added by PTF-CODELESS-INDEPENDENT-IDENTITY-BINDING-027.
    ("milwaukee-identity-027",
     "milwaukee-identity-027/journal.jsonl",
     "milwaukee-identity-027/milwaukee-identity-027"),
    # Added by PTF-HYATT-BEST-WESTERN-PREMIUM-RESOLUTION-028.
    ("milwaukee-premium-028",
     "milwaukee-premium-028/journal.jsonl",
     "milwaukee-premium-028/milwaukee-premium-028"),
    # Added by PTF-MILWAUKEE-HIGH-VALUE-REPAIR-WAVE-032.
    ("milwaukee-locator-032",
     "milwaukee-locator-032/journal.jsonl",
     "milwaukee-locator-032/milwaukee-locator-032"),
)

#: Newer wins where no supersession says otherwise. Ordered oldest to newest by
#: the work order that produced each run, not by file mtime -- a re-run of an
#: old work order must not outrank a newer one.
RUN_ORDER: Tuple[str, ...] = (
    "milwaukee-router-001", "milwaukee-resume-007", "milwaukee-wyndham-008",
    "milwaukee-ihg-009", "marriott-milwaukee-020", "hilton-milwaukee-023",
    "milwaukee-final-026", "milwaukee-identity-027",
    "milwaukee-premium-028", "milwaukee-locator-032",
)


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
    return subprocess.run(
        ["git", "log", "-1", "--format=%H", "--",
         "atlas-dashboard/scripts/pettripfinder/brightdata/policy_reading.py"],
        cwd=str(REPO.parent), capture_output=True, text=True).stdout.strip()


# --------------------------------------------------------------------------- #
# Reading one production observation from persisted evidence.
# --------------------------------------------------------------------------- #

_QUEUE_BRANDS: Dict[str, str] = {}

#: A run report's completion time, where the run has one. These runs journalled
#: no per-capture timestamp, so this is the honest granularity available and the
#: provenance says so rather than implying a per-page retrieval time.
_RUN_REPORTS: Dict[str, Path] = {
    "marriott-milwaukee-020": REPORTS / "ptf_marriott_milwaukee_run_020.json",
    "hilton-milwaukee-023": REPORTS / "ptf_hilton_milwaukee_run_023.json",
    "milwaukee-final-026": REPORTS / "ptf_milwaukee_final_pass_026.json",
    "milwaukee-identity-027": REPORTS / "ptf_identity_binding_027.json",
    "milwaukee-premium-028": REPORTS / "ptf_premium_resolution_028.json",
    "milwaukee-locator-032": REPORTS / "ptf_milwaukee_locator_recovery_032.json",
}
_RUN_TIMES: Dict[str, str] = {}


def retrieved_at(run_id: str, block_path: Path) -> Tuple[str, str]:
    """When this observation was captured, and on what evidence.

    None of these runs journalled a per-capture timestamp. The run report's
    completion time is a run-level fact and is used where one exists; otherwise
    the capture artifact's own mtime is used. Both are labelled, because a file
    timestamp is not a vendor-reported retrieval time and must never be read as
    one.
    """
    if run_id in _RUN_TIMES:
        return _RUN_TIMES[run_id], "run_report_generated_at"
    path = _RUN_REPORTS.get(run_id)
    if path is not None and path.is_file():
        stamp = json.loads(path.read_text(encoding="utf-8-sig")).get(
            "generated_at", "")
        if stamp:
            _RUN_TIMES[run_id] = stamp
            return stamp, "run_report_generated_at"
    try:
        stamp = datetime.fromtimestamp(
            block_path.stat().st_mtime, tz=timezone.utc).isoformat(
            timespec="seconds")
    except OSError:
        return "", "unavailable"
    return stamp, "capture_artifact_mtime"


def brand_for(identity_key: str, fallback: str = "") -> str:
    """The brand the committed acquisition queue gives this identity.

    Some run journals record a sub-brand and some record nothing, so the queue
    is the authority: it is what the routing decision was made against, and a
    store row whose brand disagreed with it would be unfilterable.
    """
    global _QUEUE_BRANDS
    if not _QUEUE_BRANDS:
        doc = json.loads(D.QUEUE_PATH.read_text(encoding="utf-8-sig"))
        _QUEUE_BRANDS = {r["identity_key"]: r["brand"] for r in doc["items"]}
    return _QUEUE_BRANDS.get(identity_key) or fallback


def _slug(value: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")[:80]


def _attempt_dir(capture_root: Path, name: str) -> Optional[Path]:
    base = capture_root / _slug(name)
    if not base.is_dir():
        return None
    for attempt in sorted(base.glob("attempt-*"), reverse=True):
        if (attempt / PL.BLOCK_ARTIFACT).is_file():
            return attempt
    return None


def _read_block(block: str, brand: str) -> Dict:
    """The reader at HEAD over a persisted block.

    Marriott records go through the Marriott reader because that is the reader
    their route selects; everything else goes through the generic one. Using
    the wrong reader would change what the record says for reasons that have
    nothing to do with the page.
    """
    if brand == "MARRIOTT":
        reading = MS.parse_policy_block(block, locator_id="store_integration_025")
        result = MS.to_extraction(reading, location=PL.BLOCK_ARTIFACT)
    else:
        reading = PR.parse(block, strategy="store_integration_025")
        result = PR.to_extraction(reading, location=PL.BLOCK_ARTIFACT)
    return {"extraction": dict(result.extraction),
            "withheld": dict(result.withheld or {}),
            "evidence": [dict(e) for e in result.evidence],
            "non_inferences": list(result.non_inferences)}


def entry_from_evidence(row: Mapping, *, run_id: str,
                        capture_root: Path) -> Optional[Dict]:
    """One journal row turned into the entry shape the store builder reads.

    The facts come from re-reading the persisted block with the reader at HEAD.
    That is a re-derivation, not a re-acquisition: the block is the one the
    capture selected, and no page is fetched and no boundary is recomputed.
    """
    name = row.get("canonical_name") or ""
    attempt = _attempt_dir(capture_root, name)
    if attempt is None:
        return None
    block = (attempt / PL.BLOCK_ARTIFACT).read_text(
        encoding="utf-8", errors="replace").strip()
    if not block:
        return None
    brand = brand_for(row["identity_key"], row.get("brand", ""))
    stamp, basis = retrieved_at(run_id, attempt / PL.BLOCK_ARTIFACT)
    read = _read_block(block, brand)
    return {
        "identity_key": row["identity_key"],
        "canonical_name": name,
        "brand": brand,
        "final_state": PUBLICATION_GRADE,
        "source_run": run_id,
        "result": {"document": {
            "source_url": (row.get("source_url") or row.get("official_url")
                           or row.get("requested_url", "")),
            "final_url": (row.get("source_url") or row.get("official_url")
                          or row.get("requested_url", "")),
            "capture_method": "browser_assisted",
            "provider": row.get("provider") or row.get("provider_used", ""),
            "reader": row.get("reader", ""),
            "publication_grade": {"verdict": "PUBLICATION_GRADE_CONFIRMED"},
            "withheld_fields": read["withheld"],
            "non_inferences": read["non_inferences"],
            "observation": {
                "extraction": read["extraction"],
                "evidence": read["evidence"],
                "authority_tier": "PT1",
                "source_type": "official_property_page",
                "retrieved_at": stamp,
                "retrieved_at_basis": basis,
                "obs_id": "%s::%s" % (run_id, row["identity_key"]),
                "raw_pointer": _relative(attempt),
                "snapshot_hash": sha256_text(block),
                "identity_check": {},
            },
        }},
        "_evidence_block_path": _relative(attempt / PL.BLOCK_ARTIFACT),
        "_evidence_block_sha256": sha256_text(block),
        "_block": block,
    }


def load_source(run_id: str, journal: str, capture_root: str) -> List[Dict]:
    path = DATA / journal
    if not path.is_file():
        return []
    rows = [json.loads(line) for line in
            path.read_text(encoding="utf-8").splitlines() if line.strip()]
    out: List[Dict] = []
    for row in rows:
        state = row.get("final_state") or row.get("acquisition_status") or ""
        if state != PUBLICATION_GRADE and not row.get("publication_grade"):
            continue
        if run_id == "milwaukee-router-001":
            entry = dict(row)
            entry["source_run"] = run_id
            attempt = _attempt_dir(DATA / capture_root,
                                   row.get("canonical_name", ""))
            entry["_evidence_block_path"] = (
                _relative(attempt / PL.BLOCK_ARTIFACT) if attempt else "")
            entry["_block"] = ((attempt / PL.BLOCK_ARTIFACT).read_text(
                encoding="utf-8", errors="replace").strip() if attempt else "")
            entry["_evidence_block_sha256"] = sha256_text(entry["_block"])
            out.append(entry)
            continue
        entry = entry_from_evidence(row, run_id=run_id,
                                    capture_root=DATA / capture_root)
        if entry is not None:
            out.append(entry)
    return out


# --------------------------------------------------------------------------- #
# Phase 3 -- one current row per identity.
# --------------------------------------------------------------------------- #

CONFLICT = "CURRENT_STATE_CONFLICT"


def marriott_supersessions() -> Dict[str, Dict]:
    """The three current-state observations 022 authored, keyed by identity."""
    if not C.SUPERSESSION.is_file():
        return {}
    doc = json.loads(C.SUPERSESSION.read_text(encoding="utf-8-sig"))
    return {r["identity_key"]: r for r in doc["records"]}


def select_current(entries: Sequence[Dict],
                   superseded: Mapping) -> Tuple[List[Dict], List[Dict]]:
    """One row per identity. Never a merge, never a guess."""
    order = {run: i for i, run in enumerate(RUN_ORDER)}
    by_identity: Dict[str, List[Dict]] = {}
    for entry in entries:
        by_identity.setdefault(entry["identity_key"], []).append(entry)

    chosen: List[Dict] = []
    conflicts: List[Dict] = []
    for identity, candidates in sorted(by_identity.items()):
        if len(candidates) == 1:
            chosen.append(candidates[0])
            continue
        ranked = sorted(candidates,
                        key=lambda e: order.get(e.get("source_run", ""), -1))
        winner = ranked[-1]
        # Two production observations, no supersession metadata, and they
        # disagree about the block they are about. Held, not resolved.
        blocks = {e.get("_evidence_block_sha256", "") for e in candidates}
        if identity not in superseded and len(blocks) > 1:
            winner = dict(winner)
            winner["_conflict"] = {
                "runs": sorted(e.get("source_run", "") for e in candidates),
                "blocks": sorted(blocks),
                "why": ("two production observations describe different blocks "
                        "and nothing says which supersedes which"),
            }
            conflicts.append(winner)
        chosen.append(winner)
    return chosen, conflicts


# --------------------------------------------------------------------------- #
# Phase 4 -- the 024 re-derivations, from persisted evidence.
# --------------------------------------------------------------------------- #

def queued_identities() -> Dict[str, Dict]:
    doc = json.loads(G.QUEUE_REPORT.read_text(encoding="utf-8-sig"))
    return {item["canonical_name"]: item for item in doc["items"]}


#: The work order that made the current-state projection universal. Stamped on
#: every row the projection moves, because lineage must name the authority for
#: the derivation and not merely the module the code happens to live in.
CURRENT_STATE_WORK_ORDER = "PTF-MILWAUKEE-STORE-READER-SYNC-030"

#: What that stamp means, carried onto the row so a reader of the store does
#: not have to know a work-order number to understand it.
CURRENT_STATE_DERIVATION = (
    "current-state projection: this row's facts are the CURRENT reader over "
    "the exact persisted policy block this observation was based on. The "
    "acquisition run's own reading is preserved beside it and is what that run "
    "actually reported at capture time.")


def historical_reading(entry: Mapping) -> Dict:
    """What this entry's own record says the reader made of it AT THE TIME.

    For a router-001 entry that is the capture-time reading, carried verbatim
    in the journal. For an entry this module built from evidence it is already
    the current reading, so such a row can never be stale and never acquires a
    re-derivation marker -- which is correct: nothing about it changed.
    """
    doc = (entry.get("result") or {}).get("document") or {}
    obs = doc.get("observation") or {}
    return {"extraction": dict(obs.get("extraction") or {}),
            "withheld": dict(doc.get("withheld_fields") or {})}


def same_reading(left: Mapping, right: Mapping) -> bool:
    return (dict(left.get("extraction") or {})
            == dict(right.get("extraction") or {})
            and dict(left.get("withheld") or {})
            == dict(right.get("withheld") or {}))


def current_state_projection(entries: Sequence[Dict]) -> Dict[str, Dict]:
    """The current reader over every selected observation's own block.

    THE ASYMMETRY THIS REPLACES
    ---------------------------
    This used to be scoped to ``queued_identities()`` -- fifteen names from one
    work order's review queue. Every OTHER production run reaches the store as
    an entry built by re-reading its evidence, so those rows track the reader
    automatically; router-001 rows are projected from that run's journal, which
    holds what its reader said in August. A router-001 row could therefore only
    receive a later reader by being named in an overlay, and four identities sat
    correct on disk and stale in the store because nobody had named them.

    Now every selected observation is read the same way: resolve the block the
    observation is ABOUT, run the reader that observation's route selects, and
    hand the result to the store builder's existing seam. Selection is not
    touched -- this runs after it and changes only what the winning observation
    is read to say.

    An entry whose current reading equals its historical one produces NO entry
    here. There is nothing to supersede and no lineage to record, and emitting
    one would claim the reader changed its mind when it did not.
    """
    commit = reader_commit()
    out: Dict[str, Dict] = {}
    for entry in entries:
        block = entry.get("_block") or ""
        if not block:
            continue
        read = _read_block(block, entry.get("brand", ""))
        historical = historical_reading(entry)
        if same_reading(historical, read):
            continue
        out[entry["identity_key"]] = {
            "work_order": CURRENT_STATE_WORK_ORDER,
            "derivation": CURRENT_STATE_DERIVATION,
            "reader_commit": commit,
            "evidence_block_path": entry.get("_evidence_block_path", ""),
            "evidence_block_sha256": entry.get("_evidence_block_sha256", ""),
            "extraction": read["extraction"],
            "withheld": read["withheld"],
            "non_inferences": read["non_inferences"],
            "evidence": read["evidence"],
        }
    return out


def rederivations(entries: Sequence[Dict]) -> Dict[str, Dict]:
    """Kept as the name earlier work orders call; now the whole projection.

    PTF-MILWAUKEE-STORE-READER-SYNC-030 removed the named-overlay scope. The
    function is left in place because it is the seam 025's own tests and
    reports refer to, and it now returns what it always should have: every
    selected observation whose current reading differs from its historical one.
    """
    return current_state_projection(entries)


REDERIVATION_018 = REPORTS / "ptf_milwaukee_observation_rederivation_018.json"


def overlay_018() -> Dict[str, Dict]:
    """The re-derivations 018 already applied to this store.

    Rebuilding from the journal would otherwise DROP them: the journal holds
    what each capture's reader said at the time, and 018's corrections live
    only in the store row it wrote. Re-reading every row from scratch is not
    the answer either -- 018 deliberately re-parsed only the documents it
    queued, and re-reading the rest would change records nobody examined, which
    its own test forbids.

    So its committed report is replayed through ITS OWN overlay function: one
    implementation of that mapping, owned by the work order that authored it.
    """
    if not REDERIVATION_018.is_file():
        return {}
    from scripts.pettripfinder.acquisition import observation_rederivation_018 as OBS
    doc = json.loads(REDERIVATION_018.read_text(encoding="utf-8-sig"))
    # Scoped to the router run on purpose. 018 also re-derived two records
    # whose run had no store row at the time; those rows exist now, but they
    # are built by re-reading their persisted block with the reader at HEAD --
    # which is a NEWER reading than 018's, not an older one it should override.
    # A row entering the store for the first time supersedes nothing, and
    # stamping it with an earlier work order's marker would claim a "previous"
    # reading the store never held.
    return dict(OBS.overlay(doc))


def marriott_overlay(superseded: Mapping) -> Dict[str, Dict]:
    """022's corrected Marriott readings, as the builder's overlay."""
    out: Dict[str, Dict] = {}
    for identity, record in superseded.items():
        current = record["current"]
        out[identity] = {
            "work_order": record["current"]["work_order"],
            "reader_commit": current.get("reader_commit", ""),
            "evidence_block_path": current.get("attempt_dir", "") + "/"
                                   + PL.BLOCK_ARTIFACT,
            "evidence_block_sha256": current.get("policy_block_sha256", ""),
            "extraction": current.get("extraction") or {},
            "withheld": current.get("withheld") or {},
            "non_inferences": current.get("non_inferences") or [],
            "evidence": current.get("evidence") or [],
        }
    return out


# --------------------------------------------------------------------------- #
# Phases 7 and 10 -- the differential and the arithmetic.
# --------------------------------------------------------------------------- #

def integrate(write: bool = False) -> Dict:
    before = json.loads(STORE.read_text(encoding="utf-8-sig"))
    before_rows = {i["identity_key"]: i for i in before["items"]}

    entries: List[Dict] = []
    per_source: Dict[str, int] = {}
    for run_id, journal, capture_root in SOURCES:
        rows = load_source(run_id, journal, capture_root)
        per_source[run_id] = len(rows)
        entries.extend(rows)

    superseded = marriott_supersessions()
    chosen, conflicts = select_current(entries, superseded)

    # Order matters, and each step earns its place.
    #
    # 018's corrections first, because they are a record of what that work
    # order examined and decided. Then the current-state projection, which is
    # entitled to win: it reads the same persisted blocks with a newer reader.
    # Where the two AGREE the earlier attribution is kept -- the reading did
    # not change, so claiming a newer work order changed it would be false.
    #
    # 022's Marriott supersessions last, and deliberately. Those rows rest on a
    # mechanical determination as well as a reading, and one of them reads
    # LESS from its block than the determination concluded. A projection that
    # overrode it would silently discard an adjudication.
    overlay = overlay_018()
    projection = current_state_projection(chosen)
    projected_rows, kept_earlier = [], []
    for identity, reading in projection.items():
        prior = overlay.get(identity)
        if prior and same_reading(prior, reading):
            kept_earlier.append(identity)
            continue
        overlay[identity] = reading
        projected_rows.append(identity)
    overlay.update(marriott_overlay(superseded))

    extra = [e for e in chosen if e.get("source_run") != "milwaukee-router-001"]
    doc = PROP.build(rederived=overlay, write=write, extra_entries=extra)

    after_rows = {i["identity_key"]: i for i in doc["items"]}
    added = sorted(set(after_rows) - set(before_rows))
    removed = sorted(set(before_rows) - set(after_rows))
    changed = sorted(k for k in set(after_rows) & set(before_rows)
                     if after_rows[k]["proposed_facts"]
                     != before_rows[k]["proposed_facts"])
    duplicates = [k for k, n in Counter(i["identity_key"]
                                        for i in doc["items"]).items() if n > 1]

    return {
        "schema": "ptf-milwaukee-store-integration/1.0",
        "work_order": WORK_ORDER,
        "market": MARKET,
        "generated_at": _now(),
        "run_classification": {run: {"kind": kind, "why": why}
                               for run, (kind, why) in sorted(RUN_KINDS.items())},
        "eligible_sources": [s[0] for s in SOURCES],
        "excluded_runs": sorted(r for r, (k, _) in RUN_KINDS.items()
                                if k not in (CURRENT_PRODUCTION, SUPERSEDING)),
        "observations_per_source": per_source,
        "identities_seen": len({e["identity_key"] for e in entries}),
        "rows_before": len(before["items"]),
        "rows_after": len(doc["items"]),
        "added": added,
        "removed": removed,
        "changed_facts": changed,
        "unchanged": len(set(after_rows) & set(before_rows)) - len(changed),
        "duplicates": duplicates,
        "conflicts": [{"identity_key": c["identity_key"],
                       "canonical_name": c["canonical_name"],
                       **c["_conflict"]} for c in conflicts],
        "rederivations_applied": sorted(overlay),
        "current_state_projection": {
            "observations_read": len(chosen),
            "readings_that_changed": sorted(projection),
            "applied": sorted(projected_rows),
            "earlier_attribution_kept": sorted(kept_earlier),
            "superseded_and_left_alone": sorted(
                set(projection) & set(superseded)),
        },
        "marriott_supersessions": sorted(superseded),
        "published_after": sum(1 for i in doc["items"] if i.get("published")),
        "founder_approved_after": sum(1 for i in doc["items"]
                                      if i.get("founder_approved")),
        "review_status_counts": dict(Counter(i["review_status"]
                                             for i in doc["items"])),
        "rows_by_brand": dict(Counter(i.get("brand", "") for i in doc["items"])),
        "rows_by_source_run": dict(Counter(i.get("source_run", "")
                                           for i in doc["items"])),
        "authority_written": doc["authority_written"],
        "store_written": write,
    }


def clean(result: Mapping) -> Tuple[bool, List[str]]:
    problems: List[str] = []
    if result["duplicates"]:
        problems.append("duplicate identities: %s" % result["duplicates"])
    if result["removed"]:
        problems.append("identities removed: %s" % result["removed"])
    if result["published_after"]:
        problems.append("published is no longer zero")
    if result["founder_approved_after"]:
        problems.append("founder_approved is no longer zero")
    if result["authority_written"]:
        problems.append("policy authority was written")
    return (not problems), problems


def summarise(result: Mapping) -> str:
    lines = ["%s" % result["work_order"],
             "sources: %s" % result["observations_per_source"],
             "rows %d -> %d | added %d | changed %d | unchanged %d"
             % (result["rows_before"], result["rows_after"],
                len(result["added"]), len(result["changed_facts"]),
                result["unchanged"]),
             "duplicates %d | removed %d | conflicts %d"
             % (len(result["duplicates"]), len(result["removed"]),
                len(result["conflicts"])),
             "review: %s" % result["review_status_counts"],
             "by brand: %s" % result["rows_by_brand"],
             "by run: %s" % result["rows_by_source_run"],
             "published %d | founder_approved %d | authority %s"
             % (result["published_after"], result["founder_approved_after"],
                result["authority_written"])]
    ok, problems = clean(result)
    lines.append("differential clean: %s%s"
                 % (ok, "" if ok else " -- " + "; ".join(problems)))
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="write the reconciled store, after the "
                             "differential passes")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args(argv)

    result = integrate(write=False)
    print(summarise(result))
    ok, problems = clean(result)
    if args.apply:
        if not ok:
            print("\nABORT: %s" % "; ".join(problems))
            return 1
        result = integrate(write=True)
        print("\nstore written: %s" % STORE)
    if args.write_report:
        INTEGRATION_REPORT.write_bytes(
            (json.dumps(result, indent=1, ensure_ascii=False) + "\n")
            .encode("utf-8"))
        print("report: %s" % INTEGRATION_REPORT)
    return 0 if ok else 1


__all__ = ["WORK_ORDER", "RUN_KINDS", "SOURCES", "RUN_ORDER", "load_source",
           "select_current", "rederivations", "marriott_overlay", "integrate",
           "clean", "CURRENT_PRODUCTION", "SUPERSEDING", "DECISION_TEST",
           "CONTROL", "BENCHMARK", "DIAGNOSTIC", "REPLAY", "CONFLICT"]


if __name__ == "__main__":
    raise SystemExit(main())
