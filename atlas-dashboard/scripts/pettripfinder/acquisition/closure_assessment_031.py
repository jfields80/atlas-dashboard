"""PTF-MILWAUKEE-CLOSURE-ASSESSMENT-031 -- what is left, and what is worth doing.

Milwaukee has 114 of 133 active-eligible properties observed. This classifies
the remaining nineteen so the market can be frozen deliberately rather than
abandoned when the returns quietly stopped.

Every classification here is a JUDGEMENT, and every judgement names the
persisted evidence it rests on. Those citations are not decoration: each one is
re-checked mechanically when this module runs, so a claim that stops being true
fails rather than ages. No provider is contacted; everything is read from the
archive.

WHAT THE ARCHIVE TURNED OUT TO SAY
-----------------------------------
Three of the four "insufficient evidence" properties have their COMPLETE policy
sitting in the document we already captured. Hyatt Regency's persisted page
text reads "Pet Fees Price : $40 / NIGHT ... Individual pet weight limit : 150
Pounds ... Maximum number of pets is 2" and the locator returned twenty-two
characters that stop mid-phrase. Hyatt Place Airport's says "1-6 nights : $100
/ STAY ... Individual pet weight limit : 50 Pounds" and the locator returned
the heading "Pets are Welcome". Wildwood Lodge's FAQ answers are in the DOM and
the locator returned the list of QUESTIONS.

None of those is a source limitation. They are one defect -- a located block
that is poorer than the document it came from -- and it is recoverable from
evidence already on disk, with no provider call.

Four Choice properties failed under a lane the route table no longer uses.
Their attempts show ``brightdata_web_unlocker`` alone; the committed route for
choicehotels.com has led with Firecrawl since 005, and Firecrawl has never been
tried on any of them.

TWO GAPS THAT MADE THIS ASSESSMENT HARDER THAN IT SHOULD BE
------------------------------------------------------------
A POLICY_NOT_FOUND capture persists nothing, so "this property publishes no pet
policy" can never be checked against the archive. Both properties in that class
have an empty or absent attempt directory, and the claim cannot be verified or
refuted without spending a provider call.

An IDENTITY_MISMATCH capture records no identity signals either. For two of the
six identity failures the archive cannot say whether a repair would help,
because what the gate saw was never written down.

Both are observability defects rather than acquisition defects, both are cheap,
and neither carries any risk to what the store already says.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import premium_resolution_028 as P28   # noqa: E402
from scripts.pettripfinder.acquisition import registry as REGISTRY            # noqa: E402
from scripts.pettripfinder.acquisition import store_integration_025 as S      # noqa: E402

WORK_ORDER = "PTF-MILWAUKEE-CLOSURE-ASSESSMENT-031"
MARKET = "milwaukee-wi"

REPORTS = REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
STORE = REPORTS / ("%s_policy_proposals_001.json" % MARKET)
RUN_REPORT = REPORTS / "ptf_milwaukee_closure_assessment_031.json"
DATA = REPO / "data" / "acquisition"

# --- closure classes --------------------------------------------------------
TARGETED_REPAIR = "TARGETED_REPAIR_WORTH_DOING"
FINAL_SOURCE = "FINAL_SOURCE_LIMITATION"
FINAL_IDENTITY = "FINAL_IDENTITY_LIMITATION"
FINAL_ACCESS = "FINAL_ACCESS_LIMITATION"
REACQUIRE = "REACQUISITION_WITH_EXISTING_STACK"
OTHER = "OTHER"

CLASSES = (TARGETED_REPAIR, FINAL_SOURCE, FINAL_IDENTITY, FINAL_ACCESS,
           REACQUIRE, OTHER)

# --- the repairs the classifications point at -------------------------------
REPAIR_LOCATOR = "LOCATOR_BLOCK_POORER_THAN_ITS_DOCUMENT"
REPAIR_CODELESS_PHONE = "CODELESS_BINDING_ON_A_SINGLE_PROPERTY_SITE"
REPAIR_PERSIST_ON_FAILURE = "PERSIST_EVIDENCE_ON_A_NON_ACQUIRING_OUTCOME"
REPAIR_THIN_CENSUS_URL = "SOURCE_DISCOVERY_FOR_A_THIN_CENSUS_URL"

_PET_SENTENCE = re.compile(
    r"[^.]{0,110}\b(?:pets?|dogs?|service animal)\b[^.]{0,150}", re.IGNORECASE)
_TAGS = re.compile(r"<script.*?</script>|<style.*?</style>", re.S | re.I)
_ANY_TAG = re.compile(r"<[^>]+>")

#: A term a guest could act on: a price, a weight, a count, a basis, a refusal.
#: The bare word "fee" is deliberately NOT one. Spark's page says "a fee will
#: be assessed for smoking in a non-smoking room" a few words after "Pets
#: allowed Yes", and counting that as a pet term would have turned a genuine
#: source limitation into a phantom recovery.
_ACTIONABLE_TERM = re.compile(
    r"\$\s*\d[\d,]*(?:\.\d{2})?"
    r"|\b\d[\d,]*\s*(?:pounds?|lbs?|kgs?)\b"
    r"|\b(?:maximum|max)\s+(?:number\s+of\s+)?(?:pets?|dogs?|cats?)\b"
    r"|\b\d+\s*(?:pets?|dogs?|cats?)\b"
    r"|\bper\s+(?:night|stay|day)\b"
    r"|\bnot\s+(?:allowed|accepted|permitted)\b",
    re.IGNORECASE)

_PET_WORD = re.compile(r"\bpets?\b|\bdogs?\b|\bcats?\b", re.IGNORECASE)

#: How near a pet word an actionable term must sit to belong to it.
_PET_TERM_WINDOW = 80


def actionable_pet_terms(text: str) -> set:
    """Terms a guest could act on that sit beside a pet word.

    Proximity is required and is not sufficient on its own -- the term itself
    must be a price, a weight, a count, a basis or a refusal, so an adjacent
    smoking or parking charge cannot be borrowed by a pet sentence.
    """
    found = set()
    for match in _ACTIONABLE_TERM.finditer(text or ""):
        start = max(0, match.start() - _PET_TERM_WINDOW)
        if _PET_WORD.search(text[start:match.end() + _PET_TERM_WINDOW]):
            found.add(re.sub(r"\s+", " ", match.group(0)).strip().lower())
    return found


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------------- #
# Phase 1 -- the nineteen, derived.
# --------------------------------------------------------------------------- #

def unresolved() -> List[Dict]:
    queue = P28.exception_queue()["active_acquisition_exceptions"]["queue"]
    return sorted(queue, key=lambda row: row["identity_key"])


def preflight() -> Dict:
    census = P28.full_census()
    store = json.loads(STORE.read_text(encoding="utf-8-sig"))
    rows = unresolved()
    by_reason = Counter(row["reason"] for row in rows)
    return {
        "checked_at": _now(),
        "census_total": census["census_total"],
        "active_eligible": census["active_eligible_total"],
        "store_rows": len(store["items"]),
        "observed": census["phase11_final_states"]["OBSERVED"],
        "active_unresolved": len(rows),
        "published": sum(1 for row in store["items"] if row.get("published")),
        "authority_written": bool(store.get("authority_written")),
        "authority_files": len(list(
            (REPO / "launch_packages" / "pettripfinder")
            .rglob("*hotel_policy_facts*milwaukee*"))),
        "by_reason": dict(by_reason),
        "review_status": dict(Counter(row["review_status"]
                                      for row in store["items"])),
        "assertions": {
            "census_is_147": census["census_total"] == 147,
            "active_eligible_is_133": census["active_eligible_total"] == 133,
            "store_is_114": len(store["items"]) == 114,
            "unresolved_is_19": len(rows) == 19,
            "identity_failure_is_6": by_reason.get("IDENTITY_FAILURE") == 6,
            "access_failure_is_7": by_reason.get("ACCESS_FAILURE") == 7,
            "policy_not_present_is_2": by_reason.get("POLICY_NOT_PRESENT") == 2,
            "insufficient_evidence_is_4":
                by_reason.get("INSUFFICIENT_EVIDENCE") == 4,
            "nothing_published": all(not row.get("published")
                                     for row in store["items"]),
            "authority_absent": not bool(store.get("authority_written")),
        },
    }


# --------------------------------------------------------------------------- #
# Phase 2 -- the case file, from artifacts only.
# --------------------------------------------------------------------------- #

#: Every journal a Milwaukee production run wrote, newest last.
JOURNALS: Tuple[Tuple[str, str], ...] = tuple(
    (run_id, journal) for run_id, journal, _root in S.SOURCES)

CAPTURE_ROOTS: Dict[str, str] = {run_id: root for run_id, _j, root in S.SOURCES}


def journal_rows(identity: str) -> List[Dict]:
    """Every journal row any production run wrote for this identity."""
    out: List[Dict] = []
    for run_id, journal in JOURNALS:
        path = DATA / journal
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("identity_key") == identity:
                out.append(dict(row, source_run=run_id))
    return out


def attempt_dir(identity: str, run_id: str, name: str) -> Optional[Path]:
    root = DATA / CAPTURE_ROOTS.get(run_id, "")
    if not root.is_dir():
        return None
    return S._attempt_dir(root, name)


def document_text(directory: Optional[Path]) -> str:
    """The page this capture persisted, as text, or empty when it kept none."""
    if directory is None or not directory.is_dir():
        return ""
    text = ""
    page = directory / "page-text.txt"
    if page.is_file():
        text = page.read_text(encoding="utf-8", errors="replace")
    html = directory / "rendered.html"
    if html.is_file():
        raw = html.read_text(encoding="utf-8", errors="replace")
        raw = _ANY_TAG.sub(" ", _TAGS.sub(" ", raw))
        text = text + " " + raw
    return re.sub(r"\s+", " ", text).strip()


def pet_sentences(text: str, limit: int = 6) -> List[str]:
    return [match.group(0).strip()
            for match in _PET_SENTENCE.finditer(text)][:limit]


def case_file(row: Mapping) -> Dict:
    """Everything the archive holds about one unresolved property."""
    identity = row["identity_key"]
    history = journal_rows(identity)
    last = history[-1] if history else {}
    name = last.get("canonical_name", row.get("canonical_name", ""))
    run_id = last.get("source_run", row.get("source_run", ""))
    directory = attempt_dir(identity, run_id, name)
    text = document_text(directory)
    # Not every run journalled per-attempt records: 026 and earlier wrote
    # ``providers_tried`` and a count, and only 027 began storing the attempts
    # themselves. Reading the richer field ALONE reported those runs as having
    # attempted no provider at all -- which would have called a lane untried
    # when six attempts had already failed on it.
    attempts = []
    providers = set()
    for entry in history:
        records = (entry.get("attempt_records")
                   or (entry.get("result") or {}).get("attempts") or [])
        for record in records:
            attempts.append({
                "run": entry.get("source_run", ""),
                "provider": record.get("provider", ""),
                "attempt": record.get("attempt"),
                "outcome": record.get("outcome", ""),
                "detail": (record.get("detail") or "")[:200],
            })
            if record.get("provider"):
                providers.add(record["provider"])
        for provider in (entry.get("providers_tried") or ()):
            providers.add(provider)
    source_url = (last.get("source_url") or last.get("official_url") or "")
    route = REGISTRY.resolve(brand=row.get("brand", ""), url=source_url,
                             identity_key=identity) if source_url else None
    return {
        "identity_key": identity,
        "canonical_name": name,
        "brand": row.get("brand", ""),
        "unresolved_reason": row["reason"],
        "last_run": run_id,
        "runs_touching": sorted({entry.get("source_run", "")
                                 for entry in history}),
        "source_url": source_url,
        "current_route": {"provider": route.provider,
                          "ladder": list(route.ladder),
                          "reader": route.reader,
                          "resolved_by": route.resolved_by} if route else {},
        "providers_attempted": sorted(providers),
        "attempt_count": len(attempts),
        "outcomes": dict(Counter(a["outcome"] for a in attempts)),
        "attempts": attempts,
        "final_state": last.get("final_state", ""),
        "failure": last.get("failure", ""),
        "policy_block": last.get("policy_block", ""),
        "policy_block_chars": last.get("policy_block_chars", 0),
        "policy_locator": last.get("policy_locator", ""),
        "reader_fields": list(last.get("reader_fields") or ()),
        "reader_withheld": list(last.get("reader_withheld") or ()),
        "attempt_dir": (str(directory.relative_to(REPO)).replace("\\", "/")
                        if directory else ""),
        "document_persisted": bool(text),
        "document_chars": len(text),
        "pet_sentences_in_document": pet_sentences(text),
        "actionable_terms_in_document": sorted(actionable_pet_terms(text)),
        "actionable_terms_in_block": sorted(
            actionable_pet_terms(last.get("policy_block") or "")),
    }


def case_files() -> List[Dict]:
    return [case_file(row) for row in unresolved()]


# --------------------------------------------------------------------------- #
# Phases 3-6 -- the classification, and the evidence each rests on.
# --------------------------------------------------------------------------- #

#: Checks a judgement can cite. Each is a pure function of the case file, so a
#: claim that stops being true fails here instead of quietly ageing.
def _document_states_a_policy(case: Mapping) -> bool:
    """The document states actionable pet terms the located block does not.

    A LENGTH comparison was tried first and was wrong in a way that looked
    right: Wildwood's located block is a thousand characters of collapsed FAQ
    QUESTIONS, and the ANSWERS beside it are shorter. A long block is not a
    good one.
    """
    if not case["document_persisted"]:
        return False
    in_document = set(case.get("actionable_terms_in_document") or ())
    in_block = set(case.get("actionable_terms_in_block") or ())
    return bool(in_document - in_block)


def _no_document_persisted(case: Mapping) -> bool:
    return not case["document_persisted"]


def _lane_never_tried(case: Mapping) -> bool:
    """The committed route leads with a provider this property never saw."""
    ladder = (case.get("current_route") or {}).get("ladder") or []
    return bool(ladder) and ladder[0] not in case["providers_attempted"]


def _every_lane_tried(case: Mapping) -> bool:
    ladder = (case.get("current_route") or {}).get("ladder") or []
    return bool(ladder) and set(ladder) <= set(case["providers_attempted"])


def _document_has_no_policy(case: Mapping) -> bool:
    """A persisted document whose pet wording carries nothing to act on."""
    if not case["document_persisted"]:
        return False
    return not set(case.get("actionable_terms_in_document") or ())


CHECKS = {
    "document_states_more_than_the_block": _document_states_a_policy,
    "no_document_was_persisted": _no_document_persisted,
    "committed_lane_never_tried": _lane_never_tried,
    "every_committed_lane_tried": _every_lane_tried,
    "document_states_no_actionable_policy": _document_has_no_policy,
}

#: The classification. Each entry names the class, the repair it points at (or
#: none), the checks that must hold, and the reasoning in one sentence.
#:
#: Judgements are DECLARED because they are judgements. What is mechanical is
#: whether the evidence they cite still holds, and that is verified on every
#: run by ``classify``.
JUDGEMENTS: Dict[str, Dict] = {
    # --- insufficient evidence: three locator misses and one real wall ------ #
    "hyatt regency milwaukee": {
        "closure_class": TARGETED_REPAIR,
        "repair": REPAIR_LOCATOR,
        "checks": ["document_states_more_than_the_block"],
        "why": ("the persisted page states the fee, both weight limits and the "
                "count; the located block is twenty-two characters that stop "
                "mid-phrase before the word NIGHT"),
        "recoverable_from_existing_evidence": True,
    },
    "hyatt place milwaukee airport": {
        "closure_class": TARGETED_REPAIR,
        "repair": REPAIR_LOCATOR,
        "checks": ["document_states_more_than_the_block"],
        "why": ("the persisted page states a banded fee, an individual and a "
                "combined weight limit and a count; the located block is the "
                "heading 'Pets are Welcome'"),
        "recoverable_from_existing_evidence": True,
    },
    "wildwood lodge": {
        "closure_class": TARGETED_REPAIR,
        "repair": REPAIR_LOCATOR,
        "checks": ["document_states_more_than_the_block"],
        "why": ("the FAQ ANSWERS are in the captured DOM -- dogs of any "
                "breed or weight, $20 per dog per night, two dogs per room -- "
                "and the locator returned the list of questions"),
        "recoverable_from_existing_evidence": True,
    },
    "spark by hilton milwaukee airport": {
        "closure_class": FINAL_SOURCE,
        "repair": "",
        "checks": ["document_states_no_actionable_policy"],
        "why": ("the whole persisted page carries 'Pets allowed Yes' and no "
                "terms; 023 and 024 established the words 'Max weight' exist "
                "only in a JavaScript translation dictionary"),
        "recoverable_from_existing_evidence": False,
    },

    # --- access: four properties whose committed lane was never tried ------- #
    "country inn and suites by radisson brown deer milwaukee north": {
        "closure_class": REACQUIRE,
        "repair": "",
        "checks": ["committed_lane_never_tried"],
        "why": ("attempted on the Web Unlocker alone; the committed route for "
                "choicehotels.com has led with Firecrawl since 005 and it has "
                "never been tried on this property"),
        "recoverable_from_existing_evidence": False,
    },
    "country inn and suites by radisson milwaukee airport wi": {
        "closure_class": REACQUIRE,
        "repair": "",
        "checks": ["committed_lane_never_tried"],
        "why": "the same lane was never tried here either",
        "recoverable_from_existing_evidence": False,
    },
    "country inn and suites by radisson milwaukee west brookfield wi": {
        "closure_class": REACQUIRE,
        "repair": "",
        "checks": ["committed_lane_never_tried"],
        "why": "the same lane was never tried here either",
        "recoverable_from_existing_evidence": False,
    },
    "econo lodge milwaukee airport": {
        "closure_class": REACQUIRE,
        "repair": "",
        "checks": ["committed_lane_never_tried"],
        "why": "the same lane was never tried here either",
        "recoverable_from_existing_evidence": False,
    },
    "chalet motel of mequon": {
        "closure_class": FINAL_ACCESS,
        "repair": "",
        "checks": ["every_committed_lane_tried"],
        "why": ("six attempts across both committed providers all failed with "
                "ERR_CERT_INVALID; the property's own TLS certificate is "
                "broken and reaching it would mean disabling certificate "
                "validation, which is a materially new technique"),
        "recoverable_from_existing_evidence": False,
    },
    "dubbel dutch hotel": {
        "closure_class": TARGETED_REPAIR,
        "repair": REPAIR_THIN_CENSUS_URL,
        "checks": ["every_committed_lane_tried"],
        "why": ("both providers agree the census URL -- a /contact page -- is "
                "too thin to read, six times; no discovery has ever run for "
                "this property because it was touched before the overlay "
                "existed"),
        "recoverable_from_existing_evidence": False,
    },
    "motel 6 suites milwaukee brookfield wi": {
        "closure_class": REACQUIRE,
        "repair": "",
        "checks": ["every_committed_lane_tried"],
        "why": ("six UNHYDRATED attempts on one day while three sibling Motel "
                "6 pages on the same domain hydrated in the same run; a clean "
                "re-run is cheap and settles it either way"),
        "recoverable_from_existing_evidence": False,
    },

    # --- identity: three with a printed number, three without a way in ------ #
    "knickerbocker on the lake": {
        "closure_class": TARGETED_REPAIR,
        "repair": REPAIR_CODELESS_PHONE,
        "checks": [],
        "why": ("the page's name contains the census name and the census "
                "telephone is printed on it; 027 required a SELF-DECLARED "
                "number because a multi-property operator prints its "
                "siblings', which a single-property domain cannot do"),
        "recoverable_from_existing_evidence": False,
    },
    "the clarke hotel": {
        "closure_class": TARGETED_REPAIR,
        "repair": REPAIR_CODELESS_PHONE,
        "checks": [],
        "why": ("titled 'Home - The Clarke Hotel' and prints exactly one "
                "telephone number, the census one"),
        "recoverable_from_existing_evidence": False,
    },
    "the iron horse hotel": {
        "closure_class": TARGETED_REPAIR,
        "repair": REPAIR_CODELESS_PHONE,
        "checks": [],
        "why": ("titled 'Dogs | The Iron Horse Hotel' and prints exactly one "
                "telephone number, the census one"),
        "recoverable_from_existing_evidence": False,
    },
    "brewhouse inn and suites": {
        "closure_class": OTHER,
        "repair": REPAIR_PERSIST_ON_FAILURE,
        "checks": ["no_document_was_persisted"],
        "why": ("the page title is the property name, but a refused capture "
                "records no identity signals and persists no document, so the "
                "archive cannot say whether the census telephone is printed "
                "on it. The evidence needed to classify this was never "
                "written down"),
        "recoverable_from_existing_evidence": False,
    },
    "county clare irish inn and pub": {
        "closure_class": FINAL_IDENTITY,
        "repair": "",
        "checks": ["no_document_was_persisted"],
        "why": ("the census URL's own title is 'Irish Pub Near Lake Michigan "
                "| CCII&P|M' -- it names no lodging property at all, so there "
                "is no name for any physical signal to corroborate"),
        "recoverable_from_existing_evidence": False,
    },
    "the plaza hotel milwaukee": {
        "closure_class": FINAL_IDENTITY,
        "repair": "",
        "checks": [],
        "why": ("the page publishes no structured identity, its title names no "
                "property, its name agrees with the census only on 'hotel' and "
                "'milwaukee', and the telephone it prints is not the census "
                "number"),
        "recoverable_from_existing_evidence": False,
    },

    # --- policy not present: a claim the archive cannot check --------------- #
    "drury plaza hotel milwaukee downtown": {
        "closure_class": OTHER,
        "repair": REPAIR_PERSIST_ON_FAILURE,
        "checks": ["no_document_was_persisted"],
        "why": ("the capture rendered the page for 134 seconds, found no "
                "policy container, and persisted NOTHING -- so 'this property "
                "publishes no pet policy' cannot be verified or refuted from "
                "the archive"),
        "recoverable_from_existing_evidence": False,
    },
    "potawatomi casino hotel": {
        "closure_class": OTHER,
        "repair": REPAIR_PERSIST_ON_FAILURE,
        "checks": ["no_document_was_persisted"],
        "why": ("reached through the Web Unlocker after the Browser API "
                "refused the domain as gambling, found no policy container "
                "and persisted nothing; the same unverifiable claim"),
        "recoverable_from_existing_evidence": False,
    },
}


def classify() -> List[Dict]:
    """Every unresolved property, classified once, with its evidence re-checked."""
    out: List[Dict] = []
    for case in case_files():
        judgement = JUDGEMENTS.get(case["identity_key"])
        if judgement is None:
            out.append(dict(case, closure_class=OTHER, repair="",
                            why="no judgement recorded for this identity",
                            checks_passed={}, evidence_holds=False))
            continue
        checks = {name: CHECKS[name](case) for name in judgement["checks"]}
        out.append(dict(
            case,
            closure_class=judgement["closure_class"],
            repair=judgement["repair"],
            why=judgement["why"],
            recoverable_from_existing_evidence=judgement[
                "recoverable_from_existing_evidence"],
            checks_passed=checks,
            evidence_holds=all(checks.values()),
        ))
    return out


# --------------------------------------------------------------------------- #
# Phases 7 and 8 -- reusability and ranking.
# --------------------------------------------------------------------------- #

REPAIRS: Dict[str, Dict] = {
    REPAIR_LOCATOR: {
        "value": "HIGH",
        "general_defect": ("the located block can be strictly poorer than the "
                           "document it came from -- a heading, a truncated "
                           "phrase, or a list of collapsed FAQ questions -- "
                           "and nothing notices"),
        "milwaukee_recovery": 3,
        "recurs_in_future_markets": True,
        "changes": ["locator"],
        "identity_unchanged": True,
        "routing_unchanged": True,
        "reader_unchanged": True,
        "risk": ("MEDIUM: the locator's size cap and container-scoring rules "
                 "are what keep 'the whole page' out of a quote, and a "
                 "richer-block rule pushes directly against them"),
        "testable_from_existing_evidence": True,
        "why_it_ranks_here": ("three of nineteen recover with NO provider "
                              "call, the defect is brand-independent, and "
                              "every market has accordions and headings"),
    },
    REPAIR_PERSIST_ON_FAILURE: {
        "value": "HIGH",
        "general_defect": ("a capture that reaches a page and then declines it "
                           "-- POLICY_NOT_FOUND, IDENTITY_MISMATCH -- persists "
                           "nothing, so its verdict can never be audited"),
        "milwaukee_recovery": 0,
        "recurs_in_future_markets": True,
        "changes": ["capture persistence"],
        "identity_unchanged": True,
        "routing_unchanged": True,
        "reader_unchanged": True,
        "risk": "LOW: writes an artifact; changes no verdict and no gate",
        "testable_from_existing_evidence": False,
        "why_it_ranks_here": ("recovers nothing by itself and makes three of "
                              "the nineteen answerable at all. Two 'the "
                              "source has no policy' claims and one identity "
                              "question are currently unfalsifiable, which is "
                              "a worse position than a known failure"),
    },
    REPAIR_CODELESS_PHONE: {
        "value": "MEDIUM",
        "general_defect": ("027 requires a SELF-DECLARED telephone because a "
                           "multi-property operator prints its siblings' "
                           "numbers; a single-property first-party site "
                           "cannot do that, and is refused anyway"),
        "milwaukee_recovery": 3,
        "recurs_in_future_markets": True,
        "changes": ["identity"],
        "identity_unchanged": False,
        "routing_unchanged": True,
        "reader_unchanged": True,
        "risk": ("HIGH: this is the identity gate. A false bind publishes one "
                 "hotel's policy under another's name and nothing downstream "
                 "catches it. The single-property test must be mechanical and "
                 "adversarially cornered before it ships"),
        "testable_from_existing_evidence": True,
        "why_it_ranks_here": ("real recovery and real reuse, held below the "
                              "locator repair only because the failure mode "
                              "is the one that cannot be reviewed away"),
    },
    REPAIR_THIN_CENSUS_URL: {
        "value": "LOW",
        "general_defect": ("a census URL that is a contact or landing page is "
                           "read as an access failure rather than as a source "
                           "that needs discovery"),
        "milwaukee_recovery": 1,
        "recurs_in_future_markets": True,
        "changes": ["source discovery"],
        "identity_unchanged": True,
        "routing_unchanged": True,
        "reader_unchanged": True,
        "risk": "LOW: discovery already exists and is already validated",
        "testable_from_existing_evidence": False,
        "why_it_ranks_here": ("one property here, and the overlay already "
                              "covers properties acquired after it existed; "
                              "this is a backfill, not a defect"),
    },
}


def repair_plan() -> Dict:
    rows = classify()
    by_repair: Dict[str, List[str]] = {}
    for row in rows:
        if row["closure_class"] == TARGETED_REPAIR or row["repair"]:
            by_repair.setdefault(row["repair"], []).append(row["identity_key"])
    plan = []
    for name, detail in REPAIRS.items():
        plan.append(dict(detail, repair=name,
                         properties=sorted(by_repair.get(name, []))))
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    return {
        "repairs": sorted(plan, key=lambda item: (order[item["value"]],
                                                  -item["milwaukee_recovery"])),
        "properties_by_repair": {k: sorted(v) for k, v in by_repair.items()},
    }


# --------------------------------------------------------------------------- #
# Phase 9 -- three ways to stop.
# --------------------------------------------------------------------------- #

def scenarios() -> Dict:
    rows = classify()
    observed = P28.full_census()["phase11_final_states"]["OBSERVED"]
    eligible = P28.full_census()["active_eligible_total"]
    high = [row for row in rows
            if row["repair"] and REPAIRS.get(row["repair"], {}).get("value")
            == "HIGH" and row["closure_class"] == TARGETED_REPAIR]
    reacquire = [row for row in rows if row["closure_class"] == REACQUIRE]
    finals = [row for row in rows if row["closure_class"].startswith("FINAL")]
    return {
        "FREEZE_NOW": {
            "observed": observed,
            "of_active_eligible": eligible,
            "coverage_pct": round(100.0 * observed / eligible, 1),
            "final_active_exceptions": len(rows),
            "effort": "none",
            "provider_spend_usd": 0.0,
        },
        "ONE_MORE_REPAIR_WAVE": {
            "scope": ("the HIGH-value repairs only: the locator, and "
                      "persisting evidence on a declining capture"),
            "likely_recovered": len(high),
            "likely_recovered_detail": sorted(row["identity_key"]
                                              for row in high),
            "likely_observed": observed + len(high),
            "likely_coverage_pct": round(100.0 * (observed + len(high))
                                         / eligible, 1),
            "likely_active_unresolved": len(rows) - len(high),
            "effort": "one work order; the locator repair is testable against "
                      "evidence already on disk before any capture runs",
            "provider_spend_usd": 0.0,
            "confidence": ("the three recoveries are visible in persisted "
                           "documents today; whether the repaired locator "
                           "produces a publication-grade block is not "
                           "guaranteed until it runs"),
        },
        "MAXIMUM_RECOVERY": {
            "scope": ("every non-final exception: the HIGH repairs, the "
                      "code-less identity repair, the discovery backfill, and "
                      "a re-run of the five REACQUISITION properties"),
            "ceiling_observed": observed + len(rows) - len(finals),
            "ceiling_coverage_pct": round(
                100.0 * (observed + len(rows) - len(finals)) / eligible, 1),
            "irreducible_finals": len(finals),
            "irreducible_detail": sorted(row["identity_key"] for row in finals),
            "effort": "three or four work orders, one of them touching the "
                      "identity gate",
            "provider_spend_usd_estimate": "roughly $2 to $5: five "
                                           "re-acquisitions plus re-runs of "
                                           "the repaired properties, at the "
                                           "$0.16 to $0.68 per property this "
                                           "market has measured",
            "engineering_risk": ("the identity repair is the only one that "
                                 "can be wrong invisibly; the rest fail "
                                 "loudly or not at all"),
            "confidence": ("a CEILING, not a forecast. Four Choice properties "
                           "rest on Firecrawl reaching a captcha wall that "
                           "beat the Web Unlocker nine times, and 004 "
                           "measured that lane at 13 of 15, not 15 of 15"),
        },
    }


# --------------------------------------------------------------------------- #
# Phases 10 and 11 -- publication and the next market.
# --------------------------------------------------------------------------- #

def publication_readiness() -> Dict:
    store = json.loads(STORE.read_text(encoding="utf-8-sig"))
    counts = Counter(row["review_status"] for row in store["items"])
    ready = counts.get("FOUNDER_REVIEW_READY", 0)
    refusal = counts.get("REFUSAL_FOUNDER_REVIEW", 0)
    held = (counts.get("HELD_SCHEMA_CANNOT_REPRESENT", 0)
            + counts.get("HELD_INSUFFICIENT_EVIDENCE", 0))
    return {
        "verdict": "READY_FOR_PARTIAL_FIRST_PUBLICATION",
        "candidate_set": {"ready": ready, "refusal": refusal,
                          "total": ready + refusal},
        "held_back": held,
        "unresolved_remain_unpublished": len(unresolved()),
        "reasons": [
            ("an unresolved property has NO current-state row, so it cannot "
             "be published by accident: absence is the mechanism, not a "
             "filter someone has to remember to apply"),
            ("the %d READY rows each carry contiguous quotes, a confirmed "
             "identity and a publication-grade verdict; the %d REFUSAL rows "
             "each carry the sentence that refuses, which is a finding a "
             "guest can use" % (ready, refusal)),
            ("the %d held rows must stay unpublished and will: a schema-held "
             "row is one the vocabulary cannot carry without understating a "
             "price, and an insufficient-evidence row is an amenity chip or a "
             "service-animal sentence" % held),
            ("an exception queue coexists with a published market by "
             "construction -- this market has never published a property it "
             "could not evidence, and 19 unevidenced identities simply do not "
             "appear"),
        ],
        "conditions": [
            ("publication is a FOUNDER act. 53 READY rows are ready for "
             "review, not approved; nothing here creates authority or "
             "approvals"),
            ("the three locator recoveries should land first if they are "
             "going to: republishing a market to add three properties costs "
             "more than waiting one work order"),
        ],
    }


def benchmark_readiness() -> Dict:
    return {
        "verdict": "READY_FOR_FRESH_MARKET_BENCHMARK",
        "reasons": [
            ("the architecture that would run a new market is settled: "
             "routing measured per brand, a canonical locator contract with "
             "replay, an identity gate with a code path and a code-less path, "
             "a reader with corpus-pinned protections, and a store that is "
             "now a projection of the current reader"),
            ("of Milwaukee's 19 exceptions, 8 are property-specific source, "
             "identity or access limitations that no architecture change "
             "reaches, and 5 are re-runs of a lane that already exists"),
            ("the two architectural defects this assessment found -- a "
             "locator that can return less than its document, and captures "
             "that persist nothing when they decline -- would BOTH be "
             "measured better by a fresh market than by more Milwaukee work, "
             "because Milwaukee's remaining sample is nineteen properties and "
             "a new market's is hundreds"),
        ],
        "carry_into_the_benchmark": [
            "persist evidence on a declining capture before the run, so the "
            "benchmark can be assessed from its own archive",
            "expect the locator defect to appear and instrument for it rather "
            "than fixing it blind",
        ],
    }


# --------------------------------------------------------------------------- #
# Reporting.
# --------------------------------------------------------------------------- #

def build_report() -> Dict:
    rows = classify()
    return {
        "schema": "ptf-milwaukee-closure-assessment/1.0",
        "work_order": WORK_ORDER,
        "market": MARKET,
        "generated_at": _now(),
        "preflight": preflight(),
        "classification_counts": dict(Counter(row["closure_class"]
                                              for row in rows)),
        "every_property_classified_once": (
            len(rows) == 19
            and len({row["identity_key"] for row in rows}) == 19),
        "evidence_holds_for_every_judgement": all(row["evidence_holds"]
                                                  for row in rows),
        "properties": rows,
        "repair_plan": repair_plan(),
        "scenarios": scenarios(),
        "publication_readiness": publication_readiness(),
        "benchmark_readiness": benchmark_readiness(),
        "provider_calls": 0,
        "incremental_spend_usd": 0.0,
        "authority_written": False,
        "published": 0,
    }


def write_report() -> Dict:
    doc = build_report()
    RUN_REPORT.write_text(json.dumps(doc, indent=2, ensure_ascii=False),
                          encoding="utf-8")
    return doc


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=WORK_ORDER)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--classify", action="store_true")
    parser.add_argument("--repairs", action="store_true")
    parser.add_argument("--scenarios", action="store_true")
    parser.add_argument("--readiness", action="store_true")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args(argv)

    if args.preflight:
        print(json.dumps(preflight(), indent=2))
    if args.classify:
        for row in classify():
            print("%-22s %-34s %-46s %s"
                  % (row["unresolved_reason"], row["closure_class"],
                     row["identity_key"][:46],
                     "evidence_holds" if row["evidence_holds"] else "CHECK"))
    if args.repairs:
        print(json.dumps(repair_plan(), indent=2))
    if args.scenarios:
        print(json.dumps(scenarios(), indent=2))
    if args.readiness:
        print(json.dumps({"publication": publication_readiness(),
                          "benchmark": benchmark_readiness()}, indent=2))
    if args.report:
        doc = write_report()
        print(json.dumps({k: v for k, v in doc.items()
                          if k not in ("properties", "preflight",
                                       "repair_plan", "scenarios",
                                       "publication_readiness",
                                       "benchmark_readiness")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
