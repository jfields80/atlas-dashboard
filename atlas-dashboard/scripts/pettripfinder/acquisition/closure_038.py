"""PTF-MILWAUKEE-IDENTITY-RESOLUTION-AND-FULL-CLOSURE-038 -- every row, named.

The market has been counted many ways across thirty-eight work orders. This
one puts all 147 census identities, and all 133 active-eligible ones, into
exactly one terminal disposition each, derived from committed state, with no
unnamed remainder.

WHAT THE ZERO-COST PASS FOUND
-----------------------------
Two things worth the pass, both from evidence already on disk.

FIRST, a reader defect that had cost a founder decision. Saint Kate's page
opens "Yes, Saint Kate is a pet-friendly hotel" and later says "Pets are not
allowed in the Milwaukee Center Galleria" -- a place a dog may not walk into,
inside a policy that welcomes dogs. The reader read it as a refusal, produced a
SOURCE_CONTRADICTORY the source never made, and the founder held the row
because the machine told them the page contradicted itself. A refusal that
names a PLACE is now a restriction on where, not a refusal of whether, and
exactly one row in the market changes.

SECOND, three unresolved properties whose evidence was already captured -- not
by a production run, but by a provider DECISION TEST. 025 classifies those runs
out of the store on purpose ("a control capture that reads cleanly is still a
control"), which is why these three never became observations. That rule is
about which run wins an identity in the store; it does not say a founder may
never look at the evidence. So they become CANDIDATES, with the run's nature
stated on the row, and the founder decides.

WHAT IT DID NOT DO
------------------
No provider was called. Nothing was published, nothing deployed, and nothing
recovered here entered authority: a newly readable policy is a question for the
founder, and 036's approvals do not reach forward to rows they never saw.
"""

from __future__ import annotations

import argparse
import functools
import json
import re
import sys
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder import market_authority as MA                      # noqa: E402
from scripts.pettripfinder.acquisition import authority_build_036 as A36      # noqa: E402
from scripts.pettripfinder.acquisition import closure_assessment_031 as C31   # noqa: E402
from scripts.pettripfinder.acquisition import founder_decisions_036 as D36    # noqa: E402
from scripts.pettripfinder.acquisition import founder_review_036 as F36       # noqa: E402
from scripts.pettripfinder.acquisition import hilton_decision_023 as H23      # noqa: E402
from scripts.pettripfinder.acquisition import premium_resolution_028 as P28   # noqa: E402
from scripts.pettripfinder.acquisition import source_selection as SS          # noqa: E402
from scripts.pettripfinder.acquisition import store_integration_025 as S25    # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR             # noqa: E402
from scripts.pettripfinder.brightdata import policy_surface as PS             # noqa: E402
from scripts.pettripfinder.contracts import enums                             # noqa: E402

NEWLINE = chr(10)
WORK_ORDER = "PTF-MILWAUKEE-IDENTITY-RESOLUTION-AND-FULL-CLOSURE-038"
MARKET = "milwaukee-wi"

DATA = REPO / "data" / "acquisition"
CLOSURE_DIR = F36.PKG / "milwaukee_closure_038"
LEDGER = CLOSURE_DIR / "milwaukee-full-market-closure-038.json"
REPORT_MD = CLOSURE_DIR / "milwaukee-full-market-closure-038-report.md"
CANDIDATES = CLOSURE_DIR / "milwaukee-founder-review-candidates-038.json"
PENDING = CLOSURE_DIR / "milwaukee-pending-store-projection-038.json"
RUN_REPORT = F36.REPORTS / "ptf_milwaukee_closure_038.json"

# --- the terminal vocabulary, exactly as the work order states it ----------- #
AUTHORITY_PET_FRIENDLY = "AUTHORITY_PET_FRIENDLY"
AUTHORITY_VERIFIED_NO_PETS = "AUTHORITY_VERIFIED_NO_PETS"
HELD_REVIEW = "HELD_REVIEW"
IDENTITY_UNRESOLVED = "IDENTITY_UNRESOLVED"
ACCESS_UNRESOLVED = "ACCESS_UNRESOLVED"
POLICY_NOT_FOUND = "POLICY_NOT_FOUND"
INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
SCHEMA_UNREPRESENTABLE = "SCHEMA_UNREPRESENTABLE"
SOURCE_CONFLICT = "SOURCE_CONFLICT"
OTHER = "OTHER_REQUIRES_EXPLANATION"

DISPOSITIONS: Tuple[str, ...] = (
    AUTHORITY_PET_FRIENDLY, AUTHORITY_VERIFIED_NO_PETS, HELD_REVIEW,
    IDENTITY_UNRESOLVED, ACCESS_UNRESOLVED, POLICY_NOT_FOUND,
    INSUFFICIENT_EVIDENCE, SCHEMA_UNREPRESENTABLE, SOURCE_CONFLICT, OTHER,
)

# --- the recovery vocabulary ------------------------------------------------ #
RECOVERABLE_NO_PROVIDER_CALL = "RECOVERABLE_NO_PROVIDER_CALL"
RECOVERABLE_LOW_COST = "RECOVERABLE_LOW_COST"
RECOVERABLE_HIGH_RISK = "RECOVERABLE_HIGH_RISK"
FINAL_SOURCE_LIMITATION = "FINAL_SOURCE_LIMITATION"
FINAL_ACCESS_LIMITATION = "FINAL_ACCESS_LIMITATION"
FINAL_IDENTITY_LIMITATION = "FINAL_IDENTITY_LIMITATION"
FINAL_SCHEMA_LIMITATION = "FINAL_SCHEMA_LIMITATION"
FINAL_OTHER = "FINAL_OTHER"

SUBSTANTIVE = H23.SUBSTANTIVE_FIELDS

#: Runs whose captures were never production observations. 025 classifies them
#: out of the store deliberately; the classification travels with any evidence
#: taken from them so a founder is never shown a control as though it were a
#: production capture.
NON_PRODUCTION_RUNS = {
    run: kind for run, (kind, _why) in S25.RUN_KINDS.items()
    if kind != S25.CURRENT_PRODUCTION
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")[:80]


# --------------------------------------------------------------------------- #
# The evidence a property actually has on disk.
# --------------------------------------------------------------------------- #

@functools.lru_cache(maxsize=None)
def capture_attempts(canonical_name: str) -> List[Path]:
    """Every capture directory on disk for a property, by slug.

    Walked rather than read from an earlier report's ``attempt_dir``: 031
    recorded that field empty for thirteen properties whose captures are on
    disk, and trusting it made a zero-cost pass look impossible.
    """
    out: List[Path] = []
    for base in sorted({p for p in DATA.rglob(_slug(canonical_name))
                        if p.is_dir()}):
        attempts = sorted(p for p in base.rglob("attempt-*") if p.is_dir())
        # A DECLINED capture persists its evidence too. 032 made that true on
        # purpose: a page the router refused to trust is still a page, and
        # throwing the document away makes the refusal unfalsifiable.
        attempts += sorted(p for p in base.rglob("declined-*") if p.is_dir())
        out.extend(attempts or [base])
    return out


@functools.lru_cache(maxsize=None)
def best_replay(canonical_name: str) -> Optional[Dict]:
    """The richest reading the CURRENT reader gets from persisted evidence."""
    best = None
    for attempt in capture_attempts(canonical_name):
        text = C31.document_text(attempt)
        block_path = attempt / "policy-block.txt"
        block = (block_path.read_text(encoding="utf-8", errors="replace")
                 if block_path.is_file() else "")
        if not text and not block:
            continue
        recovery = PS.recover_richer_block(block, text or block)
        candidate = recovery.text if recovery.recovered else block
        reading = PR.parse(candidate, strategy=WORK_ORDER) if candidate else None
        result = (PR.to_extraction(reading, location=WORK_ORDER)
                  if reading is not None else None)
        extraction = dict(result.extraction) if result is not None else {}
        fields = (set(extraction) & SUBSTANTIVE) | (
            {"pets_allowed"} if "pets_allowed" in extraction else set())
        run = attempt.relative_to(DATA).parts[0]
        declined = attempt / "declined.json"
        identity: Dict = {}
        if declined.is_file():
            identity = (json.loads(declined.read_text(encoding="utf-8"))
                        .get("identity") or {})
        record = {
            "attempt_dir": str(attempt.relative_to(REPO)).replace("\\", "/"),
            "run_id": run,
            "run_kind": NON_PRODUCTION_RUNS.get(run, S25.CURRENT_PRODUCTION),
            "document_chars": len(text),
            "block_chars": len(candidate),
            "block": _flat(candidate)[:600],
            "block_recovered": recovery.recovered,
            "extraction": extraction,
            "withheld": dict((result.withheld or {}) if result is not None
                             else {}),
            "contradictions": [dict(item) for item in reading.contradictions]
                              if reading is not None else [],
            "actionable_terms": sorted(PS.actionable_pet_terms(text or "")),
            "substantive_fields": sorted(fields),
            "declined": bool(identity) and not identity.get("confirmed", True),
            "identity_confirmed": (identity.get("confirmed", True)
                                   if identity else True),
            "identity_matched": list(identity.get("matched") or ()),
            "identity_reasons": list(identity.get("reasons") or ()),
            "final_url": (json.loads(declined.read_text(encoding="utf-8"))
                          .get("final_url", "") if declined.is_file() else ""),
        }
        rank = (len(record["substantive_fields"]), record["block_chars"],
                record["document_chars"])
        if best is None or rank > (len(best["substantive_fields"]),
                                   best["block_chars"],
                                   best["document_chars"]):
            best = record
    return best


# --------------------------------------------------------------------------- #
# The 133, each in exactly one bucket.
# --------------------------------------------------------------------------- #

def unfetched_policy_url(identity: Mapping) -> str:
    """A discovered first-party policy page this property has never been read
    from. Source selection is not provider selection: the census URL stays
    canonical and the route stays keyed on it, so naming a better PAGE is the
    cheapest thing left to try and it moves nothing else."""
    selection = SS.select(identity["identity_key"],
                          identity.get("official_url", ""), market_id=MARKET)
    if selection.source != SS.FROM_DISCOVERY:
        return ""
    target = selection.selected_url
    if not target or target == identity.get("official_url", ""):
        return ""
    for attempt in capture_attempts(identity["canonical_name"]):
        journal = attempt / "attempt.json"
        if journal.is_file() and target in journal.read_text(
                encoding="utf-8", errors="replace"):
            return ""
    return target


def _prior_031() -> Dict[str, Dict]:
    path = (F36.REPORTS / "ptf_milwaukee_closure_assessment_031.json")
    if not path.is_file():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    return {row["identity_key"]: row for row in doc.get("properties") or ()}


def _store_rows() -> Dict[str, Dict]:
    return {row["identity_key"]: row for row in F36.R34.store_doc()["items"]}


def _authority_keys() -> Tuple[set, set]:
    doc = json.loads(A36.AUTHORITY.read_text(encoding="utf-8"))
    friendly = {record["identity_key"] for record in doc["hotels"]}
    refusals = {row["normalized_name"]
                for row in MA.load_market_exclusions(MARKET)}
    return friendly, refusals


def _held_keys() -> set:
    return {row["identity_key"] for row in A36.ledger()["decisions"]
            if row["decision"] == D36.HOLD}


def classify(identity: Mapping, *, friendly: set, refusals: set, held: set,
             store: Mapping, prior: Mapping) -> Dict:
    """One active-eligible property's terminal disposition, derived."""
    key = identity["identity_key"]
    row = store.get(key)
    earlier = prior.get(key, {})
    base = OrderedDict([
        ("identity_key", key),
        ("canonical_name", identity["canonical_name"]),
        ("brand", identity.get("brand", "")),
        ("census_final_state", identity["final_state"]),
        ("authority_status", "NONE"),
        ("founder_review_status", "NOT_REVIEWED"),
        ("evidence_status", ""),
        ("disposition", ""),
        ("recovery_class", ""),
        ("reason", ""),
        ("lineage", OrderedDict()),
        ("last_work_order", earlier.get("last_work_order", "")
         or (row or {}).get("source_run", "")),
    ])

    if key in friendly:
        base.update({
            "authority_status": "IN_AUTHORITY",
            "founder_review_status": "APPROVED_BY_FOUNDER",
            "evidence_status": "PUBLICATION_GRADE",
            "disposition": AUTHORITY_PET_FRIENDLY,
            "recovery_class": "",
            "reason": "approved by the founder in PTF-MILWAUKEE-FOUNDER-"
                      "DECISION-036 and admitted to the market's policy "
                      "authority",
            "last_work_order": "PTF-MILWAUKEE-FOUNDER-DECISION-036",
        })
        base["lineage"] = OrderedDict([
            ("policy_package", A36.AUTHORITY.relative_to(REPO).as_posix()),
            ("decision_ledger", F36.LEDGER.name)])
        return base

    if key in refusals:
        base.update({
            "authority_status": "IN_EXCLUSION_REGISTRY",
            "founder_review_status": "APPROVED_BY_FOUNDER",
            "evidence_status": "QUOTED_REFUSAL",
            "disposition": AUTHORITY_VERIFIED_NO_PETS,
            "reason": "the property's own page refuses pets; approved as a "
                      "verified no-pets record in PTF-MILWAUKEE-FOUNDER-"
                      "DECISION-036",
            "last_work_order": "PTF-MILWAUKEE-FOUNDER-DECISION-036",
        })
        base["lineage"] = OrderedDict([
            ("exclusion_shard",
             MA.exclusions_shard_path(MARKET).relative_to(REPO).as_posix()),
            ("decision_ledger", F36.LEDGER.name)])
        return base

    replay = best_replay(identity["canonical_name"])
    contradicted = bool(replay and replay["contradictions"])
    declined = bool(replay and replay.get("declined")
                    and replay.get("actionable_terms"))
    # A reading is candidate material only if it says WHETHER pets are allowed.
    # A price is not an allowance -- that founder rule is the whole reason two
    # rows are held, and re-offering a priced page that still never grants
    # anything would be asking the founder the same question twice.
    recoverable = bool(replay and not contradicted
                       and "pets_allowed" in replay["extraction"])

    if key in held:
        base.update({
            "authority_status": "NONE",
            "founder_review_status": ("AWAITING_FOUNDER_DECISION (038 candidate)"
                                      if recoverable else "HELD_BY_FOUNDER"),
            "evidence_status": "PUBLICATION_GRADE" if recoverable
                               else "ON_DISK_NOT_SUFFICIENT",
            "disposition": HELD_REVIEW,
            "recovery_class": (RECOVERABLE_NO_PROVIDER_CALL if recoverable
                               else FINAL_SOURCE_LIMITATION),
            "reason": ("the founder held this row because the page prices a "
                       "pet policy without stating that pets are allowed. "
                       + ("The reader's place-restriction repair in 038 "
                          "removes a contradiction the source never made, so "
                          "the row is offered to the founder again as a NEW "
                          "candidate -- it is not approved."
                          if recoverable else
                          "Nothing in the repository has changed that, and no "
                          "allowance may be inferred from a price.")),
            "last_work_order": WORK_ORDER if recoverable
                               else "PTF-MILWAUKEE-FOUNDER-DECISION-036",
        })
        if replay:
            base["lineage"] = OrderedDict([
                ("attempt_dir", replay["attempt_dir"]),
                ("run_id", replay["run_id"]),
                ("run_kind", replay["run_kind"])])
        return base

    if row is not None:
        reasons = set((row["withheld_fields"] or {}).values())
        status = row["review_status"]
        base["evidence_status"] = "OBSERVED_NOT_PUBLISHABLE"
        base["founder_review_status"] = "NOT_A_036_CANDIDATE"
        base["last_work_order"] = row.get("source_run", "")
        base["lineage"] = OrderedDict([
            ("store_row", "milwaukee-wi_policy_proposals_001.json"),
            ("raw_pointer", (row.get("provenance") or {}).get("raw_pointer", "")),
        ])
        if enums.SCHEMA_CANNOT_REPRESENT in reasons:
            base.update({
                "disposition": SCHEMA_UNREPRESENTABLE,
                "recovery_class": FINAL_SCHEMA_LIMITATION,
                "reason": "the source states a price schema 1.2 cannot hold; "
                          "034 structured every shape it could and this one "
                          "remains (%s)" % ", ".join(sorted(
                              field for field, why in
                              (row["withheld_fields"] or {}).items()
                              if why == enums.SCHEMA_CANNOT_REPRESENT)),
            })
            return base
        base.update({
            "disposition": INSUFFICIENT_EVIDENCE,
            "recovery_class": FINAL_SOURCE_LIMITATION,
            "reason": "the surface carried no term worth publishing: %s"
                      % (status or "held"),
        })
        return base

    # Never observed: touched and unresolved.
    base["founder_review_status"] = "NOT_A_036_CANDIDATE"
    base["last_work_order"] = earlier.get("last_run", "") or "PTF-MILWAUKEE-CLOSURE-ASSESSMENT-031"
    if replay:
        base["lineage"] = OrderedDict([
            ("attempt_dir", replay["attempt_dir"]),
            ("run_id", replay["run_id"]),
            ("run_kind", replay["run_kind"])])
    prior_class = earlier.get("closure_class", "")

    if declined:
        base.update({
            "evidence_status": "DECLINED_ON_IDENTITY",
            "founder_review_status": "AWAITING_FOUNDER_DECISION (038 candidate)",
            "disposition": HELD_REVIEW,
            "recovery_class": FINAL_IDENTITY_LIMITATION,
            "reason": "the property's own policy page was fetched and states "
                      "pet terms (%s), but the router declined it: a /faq or "
                      "/dogs SUBPAGE carries the hotel's NAME and nothing "
                      "physical -- no address, no telephone, no JSON-LD -- so "
                      "the identity gate cannot bind it (%s). 038 did not "
                      "weaken that gate. The evidence is persisted, the "
                      "decline is stated, and the founder decides."
                      % (", ".join(replay["actionable_terms"][:4]),
                         "; ".join(replay["identity_reasons"])[:120]),
            "last_work_order": WORK_ORDER,
        })
        base["lineage"] = OrderedDict([
            ("attempt_dir", replay["attempt_dir"]),
            ("run_id", replay["run_id"]),
            ("final_url", replay["final_url"]),
            ("identity_confirmed", False),
            ("identity_matched", replay["identity_matched"])])
        return base

    if contradicted:
        base.update({
            "evidence_status": "ON_DISK_SELF_CONTRADICTORY",
            "disposition": SOURCE_CONFLICT,
            "recovery_class": FINAL_SOURCE_LIMITATION,
            "reason": "the persisted page states priced pet terms AND that the "
                      "property does not allow pets (%s). The reader refuses "
                      "to choose between them and so does this ledger: a "
                      "source that contradicts itself is not evidence for "
                      "either reading."
                      % ", ".join(sorted({item.get("field", "?")
                                          for item in replay["contradictions"]})),
        })
        return base

    if recoverable:
        base.update({
            "evidence_status": "PUBLICATION_GRADE_FROM_PERSISTED_EVIDENCE",
            "founder_review_status": "AWAITING_FOUNDER_DECISION (038 candidate)",
            "disposition": HELD_REVIEW,
            "recovery_class": RECOVERABLE_NO_PROVIDER_CALL,
            "reason": ("the policy is readable from evidence already on disk, "
                       "captured by a %s run rather than a production one -- "
                       "which is why it never became an observation. Offered "
                       "to the founder as a NEW candidate; not approved."
                       % replay["run_kind"]),
            "last_work_order": WORK_ORDER,
        })
        return base

    if prior_class == "FINAL_IDENTITY_LIMITATION":
        base.update({
            "evidence_status": "NO_BOUND_IDENTITY",
            "disposition": IDENTITY_UNRESOLVED,
            "recovery_class": FINAL_IDENTITY_LIMITATION,
            "reason": "031 could not bind this identity to a first-party page: "
                      "%s" % (earlier.get("judgement") or
                              earlier.get("why") or "no code-less binding"),
        })
        return base

    if replay and replay["document_chars"]:
        unfetched = unfetched_policy_url(identity)
        base.update({
            "evidence_status": "DOCUMENT_ON_DISK_NO_PET_TERMS",
            "disposition": POLICY_NOT_FOUND,
            "recovery_class": (RECOVERABLE_LOW_COST if unfetched
                               else FINAL_SOURCE_LIMITATION),
            "reason": "a document is persisted (%d chars) and states no "
                      "actionable pet term; a page that says nothing about "
                      "pets is not evidence that pets are refused. %s"
                      % (replay["document_chars"],
                         ("The page on disk is not the policy page: discovery "
                          "found %s and no capture has ever fetched it, so one "
                          "bounded read on the committed route would answer "
                          "this. 038 called no provider." % unfetched)
                         if unfetched else
                         "Discovery found no policy page on this site, and "
                         "nothing here invents one."),
        })
        if unfetched:
            base["lineage"]["unfetched_policy_url"] = unfetched
        return base

    base.update({
        "evidence_status": "NO_READABLE_DOCUMENT_PERSISTED",
        "disposition": ACCESS_UNRESOLVED,
        "recovery_class": (FINAL_ACCESS_LIMITATION
                           if prior_class == "FINAL_ACCESS_LIMITATION"
                           else RECOVERABLE_LOW_COST),
        "reason": ("no capture on disk carries a readable document (%d attempt "
                   "directories). 031 classified this %s. A bounded "
                   "reacquisition on the route this brand already uses is the "
                   "only thing that would answer it, and 038 called no provider."
                   % (len(capture_attempts(identity["canonical_name"])),
                      prior_class or "unclassified")),
    })
    return base


@functools.lru_cache(maxsize=None)
def active_rows() -> List[Dict]:
    census = P28.full_census()
    friendly, refusals = _authority_keys()
    held = _held_keys()
    store = _store_rows()
    prior = _prior_031()
    rows = [classify(identity, friendly=friendly, refusals=refusals, held=held,
                     store=store, prior=prior)
            for identity in census["rows"] if identity["active_eligible"]]
    return sorted(rows, key=lambda row: (row["disposition"],
                                         row["identity_key"]))


@functools.lru_cache(maxsize=None)
def non_active_rows() -> List[Dict]:
    """The 14 census identities outside the active-eligible universe."""
    census = P28.full_census()
    reasons = {
        "NO_OFFICIAL_URL": ("no first-party page has been bound to this "
                            "identity, so there is nothing to read"),
        "IDENTITY_UNRESOLVED": ("the identity itself is unsettled -- the "
                                "census cannot say which property this is"),
        "CENSUS_REVIEW": ("the census flagged this row for review: it may not "
                          "be a lodging property in this market at all"),
    }
    return sorted(
        (OrderedDict([
            ("identity_key", row["identity_key"]),
            ("canonical_name", row["canonical_name"]),
            ("census_final_state", row["final_state"]),
            ("reason", reasons.get(row["final_state"], "")),
        ]) for row in census["rows"] if not row["active_eligible"]),
        key=lambda row: (row["census_final_state"], row["identity_key"]))


# --------------------------------------------------------------------------- #
# The arithmetic, asserted rather than reported.
# --------------------------------------------------------------------------- #

def reconciliation() -> Dict:
    active = active_rows()
    other = non_active_rows()
    counts = Counter(row["disposition"] for row in active)
    keys = [row["identity_key"] for row in active]
    problems = []
    if sum(counts.values()) != 133:
        problems.append("active dispositions sum to %d, not 133"
                        % sum(counts.values()))
    if len(set(keys)) != len(keys):
        problems.append("an active identity appears twice")
    if len(active) + len(other) != 147:
        problems.append("census reconciles to %d, not 147"
                        % (len(active) + len(other)))
    unknown = sorted({row["disposition"] for row in active} - set(DISPOSITIONS))
    if unknown:
        problems.append("dispositions outside the contract: %s" % unknown)
    missing = [row["identity_key"] for row in active
               if row["disposition"] == OTHER and not row["reason"].strip()]
    if missing:
        problems.append("OTHER_REQUIRES_EXPLANATION with no reason: %s" % missing)
    return {
        "active_eligible": len(active),
        "by_disposition": {name: counts[name] for name in DISPOSITIONS
                           if counts[name]},
        "non_active_eligible": len(other),
        "by_census_state": dict(Counter(row["census_final_state"]
                                        for row in other)),
        "census_total": len(active) + len(other),
        "problems": problems,
    }


# --------------------------------------------------------------------------- #
# Phase 11 -- new candidates, never authority.
# --------------------------------------------------------------------------- #

def new_candidates() -> List[Dict]:
    """Every property 038 made reviewable, with the lineage a founder needs."""
    out: List[Dict] = []
    for row in active_rows():
        if "038 candidate" not in row["founder_review_status"]:
            continue
        replay = best_replay(row["canonical_name"])
        census = F36.census_rows().get(row["identity_key"]) or {}
        out.append(OrderedDict([
            ("identity_key", row["identity_key"]),
            ("canonical_name", row["canonical_name"]),
            ("brand", row["brand"]),
            ("address", ", ".join(part for part in (
                census.get("address"), census.get("city"), census.get("state"),
                census.get("postal_code")) if part)),
            ("identity_confirmed", replay["identity_confirmed"]),
            ("proposed_facts", {} if replay.get("declined")
                               else replay["extraction"]),
            ("reader_reading", replay["extraction"]),
            ("reader_reading_trustworthy", not replay.get("declined")),
            ("reader_caveat",
             "The router did not bind this page to this property, so nothing "
             "downstream should treat the reading above as facts. Read the "
             "block: on a page like this the located block can begin BELOW the "
             "sentence that grants or refuses permission, and a penalty for an "
             "UNAUTHORISED pet is not a pet fee. The quote is the evidence; "
             "the parse is a convenience." if replay.get("declined") else ""),
            ("withheld_fields", replay["withheld"]),
            # The page actually read, not the census homepage it was
            # resolved from -- a founder reviewing a quote needs the URL the
            # quote came off.
            ("source_url", replay.get("final_url")
                           or census.get("official_url", "")),
            ("census_url", census.get("official_url", "")),
            ("evidence_block", replay["block"]),
            ("evidence_block_chars", replay["block_chars"]),
            ("attempt_dir", replay["attempt_dir"]),
            ("run_id", replay["run_id"]),
            ("run_kind", replay["run_kind"]),
            ("acquisition_lineage",
             "captured by %s, a run 025 classifies %s and therefore excludes "
             "from the production store. The evidence is real and the capture "
             "is on disk; what it is NOT is a production observation, and that "
             "is stated here rather than smoothed over."
             % (replay["run_id"], replay["run_kind"])
             if replay["run_kind"] != S25.CURRENT_PRODUCTION else
             "captured by the production run %s" % replay["run_id"]),
            ("locator_lineage", "block %s from the persisted document by the "
                                "current locator%s"
             % (replay["block_chars"],
                " after a richer-block recovery" if replay["block_recovered"]
                else "")),
            ("why_reviewable_now", row["reason"]),
            ("status", "AWAITING_FOUNDER_DECISION"),
            ("founder_approved", False),
            ("note", "036's approvals do not reach this row: the founder never "
                     "saw it. Nothing here is in authority and nothing here is "
                     "published."),
        ]))
    return out


# --------------------------------------------------------------------------- #
# The divergence this work order chose not to close.
# --------------------------------------------------------------------------- #

#: 030 made the store a PROJECTION of the reader: every row is the current
#: reader over that row's own persisted block. 038 changed the reader, so one
#: row -- and only one -- now disagrees with the store.
#:
#: Re-projecting is the obvious fix and it is refused here, because it does
#: something the arithmetic hides: 16 of the founder's 98 decisions stop
#: binding. FIFTEEN of those sixteen change no fact whatever. Their record
#: hash covers the row's ``reader_commit`` provenance stamp, which the
#: projection re-derives on every run, so committing a reader change withdraws
#: approvals over a field that records WHEN a row was read rather than WHAT it
#: says.
#:
#: That is a governance defect, not a closure task: the founder re-attests
#: under GOV-01, or the hash is narrowed to the facts. 038 names it and leaves
#: the store alone.
PENDING_PROJECTION = OrderedDict([
    ("saint kate the arts hotel", OrderedDict([
        ("why", "038 stopped reading a place-qualified refusal as a refusal, "
                "so this row gains pets_allowed=true and loses a "
                "SOURCE_CONTRADICTORY the source never made"),
        ("store_says", "pets_allowed withheld as SOURCE_CONTRADICTORY"),
        ("reader_says", "pets_allowed true"),
        ("blocked_by", "re-projecting the store withdraws 16 of 98 founder "
                       "decisions, 15 of them over a provenance stamp alone"),
        ("resolved_by", "a founder-facing re-attestation work order, or "
                        "narrowing the record hash to the facts it is about"),
    ])),
])


def pending_projection_document() -> Dict:
    return OrderedDict([
        ("schema", "ptf-pending-store-projection/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("what_this_is", "Rows where the committed store and the reader at "
                         "HEAD disagree, and why 038 did not close the gap. "
                         "An entry here is a debt that is written down, not a "
                         "drift that is unnoticed."),
        ("rows", PENDING_PROJECTION),
        ("store_rows_total", 117),
        ("rows_pending", len(PENDING_PROJECTION)),
    ])


# --------------------------------------------------------------------------- #
# Artifacts.
# --------------------------------------------------------------------------- #

def ledger_document() -> Dict:
    return OrderedDict([
        ("schema", "ptf-milwaukee-full-market-closure/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("note", "Every active-eligible identity in exactly one terminal "
                 "disposition, derived from committed state. No unnamed "
                 "remainder and no arithmetic gap."),
        ("reconciliation", reconciliation()),
        ("active_eligible", active_rows()),
        ("non_active_eligible", non_active_rows()),
        ("new_founder_review_candidates",
         [row["identity_key"] for row in new_candidates()]),
        ("published", 0),
        ("deployed", 0),
    ])


def candidates_document() -> Dict:
    rows = new_candidates()
    return OrderedDict([
        ("schema", "ptf-milwaukee-founder-review-candidates/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("status", "AWAITING_FOUNDER_DECISION"),
        ("what_this_is", "Properties 038 made reviewable at zero provider "
                         "cost. None is approved, none is in authority, and "
                         "036's decisions do not apply to them."),
        ("candidate_count", len(rows)),
        ("candidates", rows),
    ])


def report_markdown() -> str:
    recon = reconciliation()
    active = active_rows()
    lines = [
        "# Milwaukee full-market closure -- %s" % WORK_ORDER,
        "",
        "Every one of the market's %d active-eligible properties sits in "
        "exactly one terminal disposition below, and the whole %d-property "
        "census reconciles beneath that. Nothing was published, nothing was "
        "deployed, and no provider was called."
        % (recon["active_eligible"], recon["census_total"]),
        "",
        "## Active-eligible dispositions",
        "",
        "| disposition | rows |",
        "| --- | ---: |",
    ]
    for name, count in recon["by_disposition"].items():
        lines.append("| %s | %d |" % (name, count))
    lines += [
        "| **total** | **%d** |" % recon["active_eligible"],
        "",
        "## The rest of the census",
        "",
        "| census state | rows | why |",
        "| --- | ---: | --- |",
    ]
    for state, count in recon["by_census_state"].items():
        reason = next(r["reason"] for r in non_active_rows()
                      if r["census_final_state"] == state)
        lines.append("| %s | %d | %s |" % (state, count, reason))
    lines += [
        "| **total** | **%d** | |" % recon["non_active_eligible"],
        "",
        "%d active eligible + %d other = **%d**."
        % (recon["active_eligible"], recon["non_active_eligible"],
           recon["census_total"]),
        "",
        "## Outside authority",
        "",
        "| property | disposition | recovery class |",
        "| --- | --- | --- |",
    ]
    for row in active:
        if row["disposition"] in (AUTHORITY_PET_FRIENDLY,
                                  AUTHORITY_VERIFIED_NO_PETS):
            continue
        lines.append("| %s | %s | %s |" % (row["canonical_name"],
                                           row["disposition"],
                                           row["recovery_class"] or "--"))
    candidates = new_candidates()
    lines += [
        "",
        "## New founder-review candidates (%d)" % len(candidates),
        "",
        "Recovered at zero provider cost and **not approved**. 036's decisions "
        "do not reach a row the founder never saw.",
        "",
    ]
    for row in candidates:
        lines.append("* **%s** -- %s"
                     % (row["canonical_name"],
                        json.dumps(row["proposed_facts"], default=str)[:150]
                        if row["proposed_facts"] else
                        "no proposed facts: the router declined the page on "
                        "identity, so the founder reviews the quote itself "
                        "(see below)"))
        lines.append("  * %s" % row["acquisition_lineage"])
    declined = [row for row in candidates if not row["identity_confirmed"]]
    if declined:
        lines += [
            "",
            "## The identity gate cannot bind a policy SUBPAGE",
            "",
            "Two properties published their pet policy on their own site -- a "
            "`/faq` and a `/dogs/` page that discovery had found and no run "
            "had ever fetched. Both fetched cleanly. Both were declined.",
            "",
            "A subpage carries the hotel's NAME in its title and nothing "
            "physical: no address, no telephone, no JSON-LD. The identity gate "
            "exists because a capture can land on the wrong property, and it "
            "asks for a physical agreement it cannot get from `/dogs/`. So a "
            "page on the registrable domain the census itself names -- the "
            "strongest binding an independent hotel has -- is refused for "
            "lacking a weaker one.",
            "",
            "038 did not touch the gate. Weakening an identity rule inside a "
            "closure work order is how a market ends up publishing the wrong "
            "hotel, and the founder can bind an identity where a rule cannot. "
            "Both rows are candidates, both disclose the decline, and neither "
            "carries proposed facts:",
            "",
        ]
        for row in declined:
            lines.append("* **%s** -- `%s`: %s"
                         % (row["canonical_name"], row["source_url"],
                            row["evidence_block"][:120]))
        lines += ["",
                  "Repairing the gate for the same-registrable-domain case is "
                  "a work order of its own, with its own controls.", ""]
    lines += [
        "",
        "## One row where the store and the reader disagree",
        "",
        "030 made the store a projection of the reader. 038 changed the "
        "reader, so `saint kate the arts hotel` now disagrees with its own "
        "store row -- and re-projecting is refused here, because it withdraws "
        "**16 of the founder's 98 decisions**, fifteen of them without "
        "changing a single fact. Their record hash covers a `reader_commit` "
        "stamp the projection re-derives on every run, so committing a reader "
        "change silently un-approves rows over a field that records when a "
        "page was read rather than what it says.",
        "",
        "That is a governance defect and it belongs to the founder, not to a "
        "closure task. It is written down in "
        "`milwaukee-pending-store-projection-038.json` and a test refuses any "
        "stale row that is not named there.",
        "",
        "## State", "",
              "published 0 | deployed 0 | authority 70 pet-friendly + 26 "
              "verified no-pets, unchanged.", ""]
    return "\n".join(lines) + "\n"


def assert_derivation_is_sane() -> None:
    """Refuse to write a ledger derived from a half-written repository.

    A ledger written from a polluted read once claimed fifteen founder-approved
    Hilton properties were insufficient evidence. The derivation must agree
    with the committed authority before it is allowed onto disk.
    """
    friendly, refusals = _authority_keys()
    counts = Counter(row["disposition"] for row in active_rows())
    if counts[AUTHORITY_PET_FRIENDLY] != len(friendly):
        raise SystemExit("ABORT: %d rows dispositioned into authority but the "
                         "committed package holds %d"
                         % (counts[AUTHORITY_PET_FRIENDLY], len(friendly)))
    if counts[AUTHORITY_VERIFIED_NO_PETS] != len(refusals):
        raise SystemExit("ABORT: %d refusals dispositioned but the registry "
                         "holds %d" % (counts[AUTHORITY_VERIFIED_NO_PETS],
                                       len(refusals)))
    problems = reconciliation()["problems"]
    if problems:
        raise SystemExit("ABORT: " + "; ".join(problems))


def write(apply: bool = False) -> Dict:
    if apply:
        assert_derivation_is_sane()
        CLOSURE_DIR.mkdir(parents=True, exist_ok=True)
        LEDGER.write_text(json.dumps(ledger_document(), indent=1,
                                     ensure_ascii=False) + "\n", encoding="utf-8")
        CANDIDATES.write_text(json.dumps(candidates_document(), indent=1,
                                         ensure_ascii=False) + "\n",
                              encoding="utf-8")
        REPORT_MD.write_text(report_markdown(), encoding="utf-8")
        PENDING.write_text(
            json.dumps(pending_projection_document(), indent=1,
                       ensure_ascii=False) + NEWLINE,
            encoding="utf-8")
    recon = reconciliation()
    return {"applied": apply, "reconciliation": recon,
            "new_candidates": len(new_candidates()),
            "ledger": LEDGER.relative_to(REPO).as_posix()}


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=WORK_ORDER)
    parser.add_argument("--reconcile", action="store_true")
    parser.add_argument("--rows", action="store_true")
    parser.add_argument("--candidates", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    if args.reconcile:
        print(json.dumps(reconciliation(), indent=2))
    if args.rows:
        for row in active_rows():
            if row["disposition"] in (AUTHORITY_PET_FRIENDLY,
                                      AUTHORITY_VERIFIED_NO_PETS):
                continue
            print("%-46s %-26s %s" % (row["canonical_name"][:46],
                                      row["disposition"],
                                      row["recovery_class"]))
    if args.candidates:
        print(json.dumps(candidates_document(), indent=2, default=str)[:6000])
    if args.apply:
        print(json.dumps(write(apply=True), indent=2))
    return 0


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(main())
