"""PTF-GENERIC-CROSS-RUN-PAID-ATTEMPT-LEDGER-001 -- pay once per page, ever.

WHAT THE EXISTING GUARDS ALREADY DO, AND WHERE THEY STOP
--------------------------------------------------------
Three guards already stand between the factory and a wasted dollar, and each
one is correct inside its own frame:

  ``retry_policy``          a prior FAILURE may not be re-bought on the lane
                            that already failed. Scope: one market, one prior
                            report, matched BY IDENTITY KEY.
  ``derive_cohort``         a prior ANSWER settles the property, so it never
                            enters the cohort. Scope: one market, one prior
                            report, matched BY IDENTITY KEY.
  ``identity_dedup``        two rows of ONE proposed census that name one page
                            collapse before the money. Scope: one census, one
                            run.

Every one of them is keyed on the identity key, inside a single market pass,
against a single named prior document. That is precisely the frame in which
the money leaks, because the identity key is not the property:

  * A RE-CENSUS renames. Indianapolis went 153 -> 265 and Pittsburgh rebuilt
    30 cells; a hotel that was ``holiday inn express indianapolis`` in one
    census is ``holiday inn express indianapolis downtown`` in the next. Same
    building, same URL, same page -- and to every guard above, a new property
    with no history, so the factory buys it again.
  * A RENAME by the brand does the same thing with no re-census at all.
  * A LATER WORK ORDER passes a different ``--prior`` document. What pass 1
    paid for is invisible to pass 3 unless somebody remembered to chain the
    reports, and "somebody remembered" is not a guard.
  * TWIN ROWS that the census dedup marked DUPLICATE_REVIEW_REQUIRED rather
    than SAFE_MERGE stay distinct on purpose -- and then both get bought.

THE MISSING NOUN
----------------
None of those guards has a durable memory of *what we have ever paid to
fetch*. This module is that memory. It records one row per
``(run, identity, lane)`` paid attempt, forever, keyed on the PAGE rather than
on the name we happened to give the building that month, and every future cost
plan consults it before a property may enter a paid cohort.

THE CORE INVARIANT
------------------
    Same property + same page + same lane + materially unchanged state:
    NEVER PAY AGAIN.

A repeat purchase is permitted only when one of five things is affirmatively
true, and the ledger makes the decision RECORD which one:

    ESCALATION_PERMITTED           the retry policy allows a DIFFERENT lane and
                                   the prior outcome is one a different lane
                                   could actually change.
    URL_CHANGED                    the page we would fetch is not the page we
                                   fetched.
    PROVIDER_CAPABILITY_CHANGED    the lane or reader gained a capability that
                                   post-dates the prior attempt.
    ROUTING_REPAIR                 a documented repair changed WHICH PROPERTY
                                   this row fetches.
    OPERATOR_OVERRIDE              a named human, with a durable reason.

Anything else is ``SUPPRESSED_ALREADY_PAID``, and the suppression names the
matched historical attempt so the decision can be argued with.

WHAT THIS MODULE REFUSES TO DO
------------------------------
It will not collapse two hotels because they share a building, a switchboard,
a brand, or a street. That mistake costs coverage rather than money, and it is
the more expensive one: a suppressed hotel is a hotel that never gets a policy.
Two DIFFERENT first-party property pages, or two different brand property
codes, are affirmative evidence of two properties -- on the brand's own
authority -- and outrank every proximity signal. The premises signals here can
only ever CONFIRM a match that page evidence already proposed; they can never
make one on their own.

And a suppressed row is never dropped. It moves to a named suppression list
that the coverage and closure ledgers still count, because a property we
already know the answer for is covered, not missing.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.brightdata import outcomes as O          # noqa: E402
from scripts.pettripfinder.discovery import identity_dedup as DEDUP  # noqa: E402

SCHEMA = "ptf-paid-attempt-ledger/1.0"

WHAT_THIS_IS = (
    "Every paid acquisition attempt this project has ever made, keyed on the "
    "page that was fetched rather than on the name the census gave the "
    "building. A cost plan consults it before a property may enter a paid "
    "cohort, so a re-census, a rename, a twin row or a later work order "
    "cannot buy an answer we already own.")


# --------------------------------------------------------------------------- #
# The match hierarchy
# --------------------------------------------------------------------------- #

#: Match keys in STRENGTH ORDER, strongest first. The rank is not decorative:
#: a weaker key may never override a stronger one's verdict, which is what
#: keeps a shared address from collapsing two real hotels that carry two
#: different property pages.
MATCH_CANONICAL_URL = "CANONICAL_URL"
MATCH_PROPERTY_CODE = "PROPERTY_CODE"
MATCH_PROPERTY_IDENTITY = "PROPERTY_IDENTITY"
MATCH_PREMISES_EVIDENCE = "PREMISES_EVIDENCE"

MATCH_PRIORITY: Tuple[str, ...] = (
    MATCH_CANONICAL_URL, MATCH_PROPERTY_CODE, MATCH_PROPERTY_IDENTITY,
    MATCH_PREMISES_EVIDENCE,
)

#: The two keys that name a PAGE. A match on either means one fetch answers
#: both rows, which is the whole question the money asks.
PAGE_MATCH_KEYS: Tuple[str, ...] = (MATCH_CANONICAL_URL, MATCH_PROPERTY_CODE)

#: The keys that may NOT stand alone. Sharing a street and a postal code -- with
#: or without a shared brand -- makes two rows CANDIDATES for one property; it
#: takes a compatible name to confirm, and two disagreeing brand property codes
#: refute it outright. A shared telephone is recorded and never decides -- see
#: LedgerIndex._premises_confirmed.
#:
#: Both premises keys are here, and the reason is a dual-brand building. A
#: Hampton Inn and a Homewood Suites share one address, one switchboard and one
#: BRAND -- so brand-plus-address alone would have collapsed them into a single
#: purchase and left one of the two hotels with no policy for ever. Losing a
#: hotel is a worse outcome than paying for it twice, so these keys propose and
#: never decide.
CONFIRMATION_REQUIRED_KEYS: Tuple[str, ...] = (MATCH_PROPERTY_IDENTITY,
                                               MATCH_PREMISES_EVIDENCE)


# --------------------------------------------------------------------------- #
# Outcome semantics: what a prior attempt is still worth
# --------------------------------------------------------------------------- #

#: Prior outcomes whose EVIDENCE is reusable: we own the answer, and buying it
#: again buys the same answer. ``VALID`` is the evidence-bearing outcome;
#: ``POLICY_NOT_FOUND`` is a finding -- the page rendered and said nothing --
#: which is exactly as durable as a finding that said something.
REUSABLE_OUTCOMES = frozenset({O.VALID, O.POLICY_NOT_FOUND})

#: Prior outcomes that are TERMINAL for the factory -- no further automatic
#: paid attempt -- but whose evidence is NOT reusable. An identity mismatch
#: answered a question we did not ask: it proved the route is wrong, and the
#: fix is a routing repair, not a second identical purchase.
TERMINAL_NOT_REUSABLE = frozenset({O.IDENTITY_MISMATCH})

#: Everything terminal, reusable or not. These close a property to automatic
#: paid acquisition. This is deliberately the same set ``outcomes`` already
#: calls NO_RETRY plus VALID, so the ledger and the router cannot drift apart
#: about what "answered" means.
TERMINAL_OUTCOMES = REUSABLE_OUTCOMES | TERMINAL_NOT_REUSABLE

#: Failures that say something about the CHANNEL rather than the page, so a
#: different lane could plausibly return a different answer. These are the only
#: outcomes an escalation is allowed to be built on.
ESCALATABLE_OUTCOMES = frozenset({
    O.ACCESS_DENIED, O.BLANK_PAGE, O.UNHYDRATED, O.NAVIGATION_FAILED,
    O.CAPTURE_FAILED, O.UNEXPECTED_PAGE,
})


# --------------------------------------------------------------------------- #
# Decisions
# --------------------------------------------------------------------------- #

#: No prior paid attempt matched. Buy it.
FIRST_PAID_ATTEMPT = "FIRST_PAID_ATTEMPT"

#: A prior paid attempt matched and nothing material changed. Do not buy.
SUPPRESSED_ALREADY_PAID = "SUPPRESSED_ALREADY_PAID"

#: A prior paid attempt matched, it is terminal, and its evidence answers the
#: property. Do not buy, and the property is COVERED.
SUPPRESSED_EVIDENCE_REUSABLE = "SUPPRESSED_EVIDENCE_REUSABLE"

#: A prior attempt fetched the WRONG property. Do not buy: a repair, not a
#: purchase, is what changes this answer.
SUPPRESSED_ROUTING_REPAIR_REQUIRED = "SUPPRESSED_ROUTING_REPAIR_REQUIRED"

#: Every permitted lane has already been spent on this page.
SUPPRESSED_ESCALATION_EXHAUSTED = "SUPPRESSED_ESCALATION_EXHAUSTED"

ALLOWED_ESCALATION = "ALLOWED_ESCALATION"
ALLOWED_URL_CHANGED = "ALLOWED_URL_CHANGED"
ALLOWED_CAPABILITY_CHANGED = "ALLOWED_CAPABILITY_CHANGED"
ALLOWED_ROUTING_REPAIRED = "ALLOWED_ROUTING_REPAIRED"
ALLOWED_OPERATOR_OVERRIDE = "ALLOWED_OPERATOR_OVERRIDE"

ALLOWED_DECISIONS: Tuple[str, ...] = (
    FIRST_PAID_ATTEMPT, ALLOWED_ESCALATION, ALLOWED_URL_CHANGED,
    ALLOWED_CAPABILITY_CHANGED, ALLOWED_ROUTING_REPAIRED,
    ALLOWED_OPERATOR_OVERRIDE,
)
SUPPRESSED_DECISIONS: Tuple[str, ...] = (
    SUPPRESSED_ALREADY_PAID, SUPPRESSED_EVIDENCE_REUSABLE,
    SUPPRESSED_ROUTING_REPAIR_REQUIRED, SUPPRESSED_ESCALATION_EXHAUSTED,
)
DECISIONS: Tuple[str, ...] = ALLOWED_DECISIONS + SUPPRESSED_DECISIONS

#: Material-change reasons a caller may assert to unlock a repeat purchase.
#: Each must arrive with a reason string; an assertion with no reason is
#: rejected rather than believed, for the same reason the retry policy rejects
#: an unreasoned override.
MATERIAL_URL_CHANGED = "URL_CHANGED"
MATERIAL_CAPABILITY_CHANGED = "PROVIDER_CAPABILITY_CHANGED"
MATERIAL_ROUTING_REPAIR = "ROUTING_REPAIR"
MATERIAL_OPERATOR_OVERRIDE = "OPERATOR_OVERRIDE"

MATERIAL_CHANGES: Tuple[str, ...] = (
    MATERIAL_URL_CHANGED, MATERIAL_CAPABILITY_CHANGED,
    MATERIAL_ROUTING_REPAIR, MATERIAL_OPERATOR_OVERRIDE,
)

_MATERIAL_TO_DECISION = {
    MATERIAL_URL_CHANGED: ALLOWED_URL_CHANGED,
    MATERIAL_CAPABILITY_CHANGED: ALLOWED_CAPABILITY_CHANGED,
    MATERIAL_ROUTING_REPAIR: ALLOWED_ROUTING_REPAIRED,
    MATERIAL_OPERATOR_OVERRIDE: ALLOWED_OPERATOR_OVERRIDE,
}


class PaidLedgerError(ValueError):
    """A material-change assertion with no reason, or an unknown kind."""


# --------------------------------------------------------------------------- #
# Normalisation
# --------------------------------------------------------------------------- #

_WS = re.compile(r"\s+")
_NOT_ALNUM = re.compile(r"[^a-z0-9]+")

#: Street suffixes and directionals, so "601 W Washington St" and
#: "601 West Washington Street" are one street. Deliberately small: this key
#: only ever CONFIRMS a page match, so an imperfect normalisation costs a
#: confirmation, never a wrong merge.
_STREET_WORDS = {
    "street": "st", "avenue": "ave", "boulevard": "blvd", "road": "rd",
    "drive": "dr", "lane": "ln", "court": "ct", "place": "pl", "parkway": "pkwy",
    "highway": "hwy", "circle": "cir", "terrace": "ter", "square": "sq",
    "north": "n", "south": "s", "east": "e", "west": "w",
    "northeast": "ne", "northwest": "nw", "southeast": "se", "southwest": "sw",
    "suite": "ste",
}


def _url_row(row: Mapping) -> Dict[str, str]:
    """Adapt any row shape to the one ``identity_dedup`` reads.

    A census row names its page ``official_url``; an acquisition RESULT row
    names it ``source_url``; a routed cohort row names it ``source_url`` too.
    They are the same field and the ledger must not care which document it is
    reading, or a match would depend on provenance instead of on the page.
    """
    for field in ("official_url", "source_url", "url", "canonical_url"):
        value = row.get(field)
        if value:
            return {"official_url": str(value)}
    return {"official_url": ""}


def canonical_url(row: Mapping) -> str:
    """The comparison form of whichever URL field this row carries."""
    return DEDUP.canonical_url(_url_row(row))


def property_code(row: Mapping) -> str:
    """The brand's own key for the building, or ``""``."""
    return DEDUP.property_code(_url_row(row))


def normalized_host(row: Mapping) -> str:
    url = canonical_url(row)
    return url.split("/", 1)[0].split(":", 1)[0] if url else ""


def normalized_path(row: Mapping) -> str:
    url = canonical_url(row)
    if not url:
        return ""
    host = url.split("/", 1)[0].split(":", 1)[0]
    return url[len(host):] or "/"


def normalized_street(row: Mapping) -> str:
    """``601 W Washington St`` and ``601 West Washington Street`` compare equal."""
    raw = (row.get("street") or row.get("address") or
           row.get("street_address") or "")
    raw = _WS.sub(" ", str(raw).strip().lower())
    if not raw:
        return ""
    raw = raw.split(",", 1)[0]
    words = [_NOT_ALNUM.sub("", w) for w in raw.split(" ")]
    return " ".join(_STREET_WORDS.get(w, w) for w in words if w)


def normalized_phone(row: Mapping) -> str:
    """US telephone as ten digits, or ``""``. A leading 1 is not a digit of
    the number, and two rows that differ only by it are one switchboard."""
    raw = re.sub(r"[^0-9]", "", str(row.get("telephone") or row.get("phone") or ""))
    if len(raw) == 11 and raw.startswith("1"):
        raw = raw[1:]
    return raw if len(raw) == 10 else ""


def postal_code(row: Mapping) -> str:
    raw = re.sub(r"[^0-9]", "", str(row.get("postal_code") or row.get("zip") or ""))
    return raw[:5] if len(raw) >= 5 else ""


def property_identity(row: Mapping) -> str:
    """A deterministic identity for the building, independent of the page.

    Brand plus normalised street plus postal code. This is the third-strength
    key: it survives a rename (which changes the identity key) and a URL move
    (which changes the page keys), and it is still specific enough that it
    cannot match across two cities.

    It requires a BRAND. Without one there is no property identity here that
    the premises key does not already carry, and returning a brandless
    ``|street|zip`` would simply be the fourth key wearing the third key's rank
    -- which would let it decide questions the fourth key is not trusted with.
    """
    street, zipc = normalized_street(row), postal_code(row)
    brand = _NOT_ALNUM.sub("", str(row.get("brand") or "").lower())
    if not (street and zipc and brand):
        return ""
    return "%s|%s|%s" % (brand, street, zipc)


def _name(row: Mapping) -> str:
    return str(row.get("canonical_name") or row.get("name") or "")


# --------------------------------------------------------------------------- #
# One attempt record
# --------------------------------------------------------------------------- #

#: Every field a paid attempt must carry to be arguable with later. Written out
#: rather than inferred, because an exhaustive field list is what stops the
#: next schema from quietly losing the field that mattered.
ATTEMPT_FIELDS: Tuple[str, ...] = (
    "attempt_id", "market_id", "work_order", "run_id", "identity_key",
    "canonical_name", "brand", "property_code", "canonical_url",
    "normalized_host", "normalized_path", "normalized_street", "postal_code",
    "telephone", "property_identity", "lane", "lanes_tried", "reader",
    "attempted_at", "outcome", "final_state", "publication_grade", "settled",
    "terminal", "reusable_evidence", "artifact_path", "artifact_hash",
    "cost_usd_minor", "firecrawl_credits", "escalation_eligible",
    "predecessor_attempt_id", "material_change_reason",
)


def attempt_id(market_id: str, run_id: str, identity_key: str, lane: str) -> str:
    """A stable id for one paid attempt, so ingesting a run twice is a no-op."""
    raw = "|".join((market_id or "", run_id or "", identity_key or "", lane or ""))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _is_terminal(outcome: str) -> bool:
    return outcome in TERMINAL_OUTCOMES


def _grade(row: Mapping) -> bool:
    """Publication grade, from whichever of the two spellings the row uses."""
    value = row.get("publication_grade")
    if isinstance(value, bool):
        return value
    return str(row.get("final_state") or "") == "ACQUIRED_PUBLICATION_GRADE"


def build_attempt(row: Mapping, *, market_id: str, work_order: str,
                  run_id: str, lane: str = "",
                  cost_usd_minor: Optional[float] = None,
                  firecrawl_credits: Optional[float] = None,
                  predecessor_attempt_id: str = "",
                  material_change_reason: str = "") -> Dict:
    """One ledger row from one acquisition result.

    ``lane`` defaults to the row's chosen provider. Where a row records several
    ``providers_tried``, the caller emits one record per lane -- because the
    question the ledger answers is "have we already paid THIS lane to fetch
    THIS page?", and a lane that was tried was a lane that was paid for.
    """
    outcome = str(row.get("outcome") or "")
    lane = lane or str(row.get("provider") or "")
    key = str(row.get("identity_key") or "")
    terminal = _is_terminal(outcome)
    escalatable, _ = escalation_eligible(outcome)
    record = OrderedDict()
    record["attempt_id"] = attempt_id(market_id, run_id, key, lane)
    record["market_id"] = market_id
    record["work_order"] = work_order
    record["run_id"] = run_id
    record["identity_key"] = key
    record["canonical_name"] = _name(row)
    record["brand"] = str(row.get("brand") or "")
    record["property_code"] = property_code(row)
    record["canonical_url"] = canonical_url(row)
    record["normalized_host"] = normalized_host(row)
    record["normalized_path"] = normalized_path(row)
    record["normalized_street"] = normalized_street(row)
    record["postal_code"] = postal_code(row)
    record["telephone"] = normalized_phone(row)
    record["property_identity"] = property_identity(row)
    record["lane"] = lane
    record["lanes_tried"] = [str(p) for p in (row.get("providers_tried") or ())
                             if p] or ([lane] if lane else [])
    record["reader"] = str(row.get("reader") or "")
    record["attempted_at"] = str(row.get("completed_at") or
                                 row.get("attempted_at") or "")
    record["outcome"] = outcome
    record["final_state"] = str(row.get("final_state") or "")
    record["publication_grade"] = _grade(row)
    record["settled"] = terminal
    record["terminal"] = terminal
    record["reusable_evidence"] = outcome in REUSABLE_OUTCOMES
    record["artifact_path"] = str(row.get("artifact_dir") or
                                  row.get("artifact_path") or "")
    record["artifact_hash"] = str(row.get("content_hash") or "")
    record["cost_usd_minor"] = cost_usd_minor
    record["firecrawl_credits"] = firecrawl_credits
    record["escalation_eligible"] = escalatable
    record["predecessor_attempt_id"] = predecessor_attempt_id
    record["material_change_reason"] = material_change_reason
    return record


def escalation_eligible(outcome: str) -> Tuple[bool, str]:
    """``(eligible, why)`` -- may this outcome justify ONE dearer lane?

    Terminal outcomes may not: a second purchase buys the same answer. Channel
    failures may: the page never arrived, and a different channel might deliver
    it. Anything unrecognised may not, because an unknown outcome is not
    evidence that a retry would help.
    """
    if outcome in TERMINAL_OUTCOMES:
        return (False, "%s is terminal: the property was answered, and a "
                       "second purchase would buy the same answer" % outcome)
    if outcome in ESCALATABLE_OUTCOMES:
        return (True, "%s is a statement about the channel, not the page, so a "
                      "different lane may return a different answer" % outcome)
    return (False, "%s is not on the approved escalation list"
                   % (outcome or "(none)"))


# --------------------------------------------------------------------------- #
# Ingesting a saved paid pass
# --------------------------------------------------------------------------- #

def _cost_per_attempt(document: Mapping, attempts: int
                      ) -> Tuple[Optional[float], Optional[float]]:
    """``(usd_minor, credits)`` apportioned evenly over a run's attempts.

    The vendor meters a ZONE over a session, not a property, so no per-property
    price exists to read. An even split is the honest reconstruction and it is
    labelled as one: the run total is exact, the per-row figure is an estimate,
    and the audit reports the total rather than summing the estimates back up.
    """
    if attempts <= 0:
        return (None, None)
    spend = document.get("spend") or {}
    usd = spend.get("binding_usd_minor")
    if usd is None:
        usd = spend.get("measured_usd_minor")
    if usd is None:
        usd = spend.get("estimated_usd_minor")
    credits = spend.get("estimated_plan_credits")
    return ((float(usd) / attempts) if usd is not None else None,
            (float(credits) / attempts) if credits is not None else None)


def ingest_run(document: Mapping, *, market_id: str = "",
               census: Sequence[Mapping] = ()) -> List[Dict]:
    """Every paid attempt in one ``ptf-market-paid-acquisition`` document.

    A run with ``dry_run`` true spent NOTHING and contributes nothing: a plan
    is not a purchase, and recording one would suppress a property we never
    actually bought an answer for.

    ``census`` optionally supplies the address and telephone the acquisition
    report does not carry, so the weaker match keys are populated. Its absence
    costs the premises key and nothing else -- the page keys, which are the
    ones that decide, come off the URL the report already records.
    """
    if document.get("dry_run"):
        return []
    market_id = market_id or str(document.get("market_id") or "")
    work_order = str(document.get("work_order") or "")
    run_id = str(document.get("run_id") or "")
    results = list(document.get("results") or ())
    by_key = {}
    for row in census:
        key = str(row.get("identity_key") or "")
        if key:
            by_key[key] = row

    lane_attempts = sum(len(r.get("providers_tried") or [r.get("provider")])
                        for r in results) or len(results)
    usd, credits = _cost_per_attempt(document, lane_attempts)

    records: List[Dict] = []
    for row in results:
        enriched = dict(row)
        extra = by_key.get(str(row.get("identity_key") or ""))
        if extra:
            for field in ("street", "address", "street_address", "postal_code",
                          "zip", "telephone", "phone"):
                if extra.get(field) and not enriched.get(field):
                    enriched[field] = extra[field]
        lanes = [str(p) for p in (row.get("providers_tried") or ()) if p]
        if not lanes:
            lanes = [str(row.get("provider") or "")]
        previous = ""
        for index, lane in enumerate(lanes):
            record = build_attempt(
                enriched, market_id=market_id, work_order=work_order,
                run_id=run_id, lane=lane, cost_usd_minor=usd,
                firecrawl_credits=credits,
                predecessor_attempt_id=previous,
                material_change_reason=(
                    "" if index == 0 else
                    "in-run escalation from %s after a channel failure" % lanes[index - 1]))
            # Only the LAST lane in the ladder produced the row's outcome; the
            # earlier ones are, by construction, the failures that justified
            # escalating. Recording the run's final outcome against all of them
            # would make a failed Firecrawl attempt look like it had answered.
            if index < len(lanes) - 1:
                record["outcome"] = ""
                record["final_state"] = ""
                record["publication_grade"] = False
                record["settled"] = False
                record["terminal"] = False
                record["reusable_evidence"] = False
                record["escalation_eligible"] = True
            records.append(record)
            previous = record["attempt_id"]
    return records


# --------------------------------------------------------------------------- #
# The ledger document
# --------------------------------------------------------------------------- #

def new_ledger() -> Dict:
    return OrderedDict((("schema", SCHEMA), ("what_this_is", WHAT_THIS_IS),
                        ("attempts", [])))


def load(path) -> Dict:
    path = Path(path)
    if not path.is_file():
        return new_ledger()
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema") != SCHEMA:
        raise PaidLedgerError("not a %s document: %r"
                              % (SCHEMA, document.get("schema")))
    document.setdefault("attempts", [])
    return document


def save(path, ledger: Mapping) -> None:
    Path(path).write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")


def merge(ledger: Mapping, records: Sequence[Mapping]) -> Dict:
    """Add attempts to a ledger, idempotently.

    Re-ingesting a run must be a no-op, or an audit that runs twice would
    invent a double-buy that never happened. ``attempt_id`` is a hash of
    (market, run, identity, lane), so the same attempt from the same document
    lands on the same row every time.
    """
    out = OrderedDict(ledger)
    existing = list(out.get("attempts") or ())
    seen = {r.get("attempt_id") for r in existing}
    for record in records:
        if record.get("attempt_id") in seen:
            continue
        seen.add(record.get("attempt_id"))
        existing.append(dict(record))
    out["attempts"] = existing
    return out


# --------------------------------------------------------------------------- #
# Looking a property up
# --------------------------------------------------------------------------- #

class LedgerIndex:
    """Every recorded attempt, indexed by each match key it carries.

    Built once per cost plan rather than scanned per row, because the cohort is
    hundreds of rows and the ledger grows without bound across markets.
    """

    def __init__(self, ledger: Mapping):
        self.attempts: List[Dict] = [dict(a) for a in (ledger.get("attempts") or ())]
        self._by: Dict[str, Dict[str, List[Dict]]] = {k: {} for k in MATCH_PRIORITY}
        for record in self.attempts:
            for kind, value in self._keys_of(record):
                self._by[kind].setdefault(value, []).append(record)

    @staticmethod
    def _keys_of(record: Mapping) -> List[Tuple[str, str]]:
        keys: List[Tuple[str, str]] = []
        if record.get("canonical_url"):
            keys.append((MATCH_CANONICAL_URL, str(record["canonical_url"])))
        if record.get("property_code"):
            keys.append((MATCH_PROPERTY_CODE, str(record["property_code"])))
        if record.get("property_identity"):
            keys.append((MATCH_PROPERTY_IDENTITY, str(record["property_identity"])))
        street, zipc = record.get("normalized_street"), record.get("postal_code")
        if street and zipc:
            keys.append((MATCH_PREMISES_EVIDENCE, "%s|%s" % (street, zipc)))
        return keys

    def lookup(self, row: Mapping) -> Tuple[str, str, List[Dict]]:
        """``(match_key, value, attempts)`` -- the STRONGEST evidence that this
        row's page has been paid for before, or ``("", "", [])``.

        The hierarchy is walked in strength order and STOPS at the first key
        that matches -- except that a key requiring confirmation which fails to
        get it does NOT stop the walk, it falls through to the next key.

        Only the two PAGE keys decide on their own. The two premises keys must
        prove themselves: they group genuinely distinct hotels, so each must be
        confirmed by a compatible name or a shared telephone, and each is
        refuted outright by two disagreeing brand property codes.
        """
        candidates = {
            MATCH_CANONICAL_URL: canonical_url(row),
            MATCH_PROPERTY_CODE: property_code(row),
            MATCH_PROPERTY_IDENTITY: property_identity(row),
            MATCH_PREMISES_EVIDENCE: "%s|%s" % (normalized_street(row),
                                                postal_code(row)),
        }
        row_code = candidates[MATCH_PROPERTY_CODE]
        for kind in MATCH_PRIORITY:
            value = candidates[kind]
            if not value or value.strip("|") == "":
                continue
            found = self._by[kind].get(value) or []
            if not found:
                continue
            if kind in CONFIRMATION_REQUIRED_KEYS:
                found = [a for a in found if self._premises_confirmed(row, a, row_code)]
                if not found:
                    continue
            return (kind, value, found)
        return ("", "", [])

    @staticmethod
    def _premises_confirmed(row: Mapping, record: Mapping, row_code: str) -> bool:
        """Whether a shared street and postal code is the SAME property.

        Two different brand property codes at one address are two hotels on the
        brand's own authority -- a dual-brand building, which is common and
        which this guard must never collapse. Otherwise the match needs
        positive confirmation, and the ONLY thing that confirms it is a name
        the census dedup already calls compatible.

        A SHARED SWITCHBOARD IS NOT A SHARED HOTEL
        -------------------------------------------
        A shared telephone used to confirm on its own, and
        PTF-GRAND-RAPIDS-CROSS-RUN-LEDGER-SYNC-018 found what that costs. Grand
        Rapids carries two open identity questions, and both are exactly this
        shape: a Comfort Inn and a prior-census Comfort Suites at 4520 Kenowa
        Ave SW sharing 616-667-0733, and a Sleep Inn and Suites and a Spark by
        Hilton at 4284 29th St SE sharing 616-975-9000. The pre-acquisition
        dedup gate looked at those same two signals and ruled both pairs
        DISTINCT_PROPERTIES, because the names are not containment-compatible
        and Choice publishes no property code this project extracts. Phone-alone
        confirmation made this module rule the opposite way on the same
        evidence, and its ruling is the one that spends nothing and leaves a
        hotel with no policy for ever.

        The two cases a shared switchboard actually covers are a dual-brand
        building and a rebrand, and in both the answer is a person, not a
        purchase. Where a rename merely lengthened the name, ``names_compatible``
        already confirms it. So the telephone stays a signal on the record and
        stops being a decider: losing a hotel is worse than paying for it twice,
        which is this module's own stated order of preference.
        """
        record_code = str(record.get("property_code") or "")
        if row_code and record_code and row_code != record_code:
            return False
        return DEDUP.names_compatible(_name(row),
                                      str(record.get("canonical_name") or ""))


# --------------------------------------------------------------------------- #
# The decision
# --------------------------------------------------------------------------- #

def _ladder_position(record: Mapping) -> int:
    """Where this attempt sits in its own run's lane ladder.

    ``ingest_run`` writes every lane of one in-run escalation with ONE
    ``attempted_at`` -- the run records a single timestamp per property, not one
    per lane -- so a sort on the timestamp alone leaves the ladder in a tie, and
    tie-breaking on ``attempt_id`` orders it by a hash. That is how a Motel 6
    whose browser attempt escalated to the Web Unlocker and came back
    UNEXPECTED_PAGE reported its PREDECESSOR as the last word: the suppression
    was still correct, but its stated reason said the prior outcome was
    unrecorded when the ledger plainly recorded it. A suppression nobody can
    argue with is not a control, so the ladder is ordered by the position the
    record already carries.
    """
    lanes = [str(lane) for lane in (record.get("lanes_tried") or ()) if lane]
    lane = str(record.get("lane") or "")
    return lanes.index(lane) if lane in lanes else 0


def _attempt_order(record: Mapping) -> Tuple[str, int, str]:
    return (str(record.get("attempted_at") or ""), _ladder_position(record),
            str(record.get("attempt_id") or ""))


def _terminal_attempt(attempts: Sequence[Mapping]) -> Optional[Mapping]:
    for record in attempts:
        if record.get("terminal"):
            return record
    return None


def _lanes_paid(attempts: Sequence[Mapping]) -> List[str]:
    lanes: List[str] = []
    for record in attempts:
        for lane in (record.get("lanes_tried") or []) or [record.get("lane")]:
            if lane and lane not in lanes:
                lanes.append(str(lane))
    return lanes


def _escalations_since_decision(attempts: Sequence[Mapping]) -> int:
    """How many repeat purchases the current material-change decision has bought.

    An escalation is a decision to spend once more, not a licence to keep
    spending. Counting attempts that carry a predecessor but no NEW
    material-change reason of their own is what stops attempt 1 -> 2 -> 3 -> 4
    from walking the whole ladder on one justification.
    """
    return sum(1 for a in attempts
               if a.get("predecessor_attempt_id")
               and not a.get("material_change_reason", "").startswith("operator:"))


def load_material_changes(path) -> Dict[str, Dict[str, str]]:
    """``identity_key -> {kind: reason}`` from a ptf-material-changes document.

    A material change is how a paid row that the ledger would otherwise
    suppress becomes payable again -- a re-buy of a page we have already paid
    for. That is precisely the decision that must never be implicit, so this
    refuses three ways: an unknown ``kind`` (the vocabulary is closed), a
    missing reason (an override nobody has to justify is not a control), and a
    second assertion of the same kind for one identity (two reasons for one
    re-buy means nobody knows which one is operative).

    Loading is separate from applying: the caller still passes the result to
    ``suppress``/``decide``, which decide whether the asserted change actually
    licenses THIS row.
    """
    if not path:
        return {}
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    out: Dict[str, Dict[str, str]] = OrderedDict()
    for row in document.get("changes") or ():
        key = str(row.get("identity_key") or "").strip()
        if not key:
            raise PaidLedgerError("a material change names no identity_key")
        kind = str(row.get("kind") or "").strip()
        if kind not in MATERIAL_CHANGES:
            raise PaidLedgerError(
                "material change for %r names kind %r, which is not one of "
                "%s. The vocabulary is closed because a repeat purchase must "
                "cite a reason the ledger already understands."
                % (key, kind, ", ".join(MATERIAL_CHANGES)))
        reason = str(row.get("reason") or "").strip()
        if not reason:
            raise PaidLedgerError(
                "material change %r for %r gives no reason; a repeat purchase "
                "must record WHY it is allowed" % (kind, key))
        bucket = out.setdefault(key, OrderedDict())
        if kind in bucket:
            raise PaidLedgerError(
                "%r asserts %r twice; two reasons for one re-buy means nobody "
                "knows which is operative" % (key, kind))
        bucket[kind] = reason
    return out


def _material(assertions: Optional[Mapping[str, str]], kind: str) -> str:
    """The reason string for an asserted material change, validated.

    An assertion with no reason is an error rather than a permission. This is
    the same refusal the retry policy makes about an unreasoned override, and
    for the same reason: an override nobody has to justify is not a control.
    """
    if not assertions:
        return ""
    if kind not in assertions:
        return ""
    reason = str(assertions.get(kind) or "").strip()
    if not reason:
        raise PaidLedgerError(
            "material change %r was asserted with no reason; a repeat purchase "
            "must record WHY it is allowed, or it is not a control" % kind)
    return reason


def decide(row: Mapping, index: "LedgerIndex", *,
           material_changes: Optional[Mapping[str, str]] = None,
           available_lanes: Sequence[str] = ()) -> Dict:
    """Whether this routed row may enter a paid cohort, and why.

    Order matters and is deliberate:

    1. No history at all -> buy. The ledger never blocks a first purchase.
    2. An OPERATOR OVERRIDE outranks everything, including a terminal answer,
       because a named human may always decide to re-buy -- but the reason is
       recorded and the override is spent on this row alone.
    3. A ROUTING REPAIR beats a terminal identity mismatch, since the repair
       changed WHICH PROPERTY the row fetches: it is not the same page.
    4. Reusable evidence closes the property. We own the answer.
    5. A terminal-but-not-reusable answer (identity mismatch) closes it too,
       and names the repair as the thing that would change it.
    6. Otherwise the prior attempts failed on the channel, and exactly one
       escalation to an untried, permitted lane is allowed.
    """
    match_key, value, attempts = index.lookup(row)
    decision = OrderedDict()
    decision["identity_key"] = str(row.get("identity_key") or "")
    decision["canonical_name"] = _name(row)
    decision["canonical_url"] = canonical_url(row)
    decision["match_key"] = match_key
    decision["match_value"] = value
    decision["matched_attempts"] = [a.get("attempt_id") for a in attempts]

    if not attempts:
        decision["decision"] = FIRST_PAID_ATTEMPT
        decision["reason"] = "no prior paid attempt matches this page"
        decision["prior_lane"] = ""
        decision["prior_outcome"] = ""
        decision["prior_artifact"] = ""
        decision["reusable_evidence"] = False
        decision["routing_repair_required"] = False
        decision["material_change_reason"] = ""
        decision["predecessor_attempt_id"] = ""
        return decision

    ordered = sorted(attempts, key=_attempt_order)
    last = ordered[-1]
    terminal = _terminal_attempt(ordered)
    lanes_paid = _lanes_paid(ordered)
    decision["prior_lane"] = str(last.get("lane") or "")
    decision["prior_lanes_paid"] = lanes_paid
    decision["prior_outcome"] = str((terminal or last).get("outcome") or "")
    decision["prior_artifact"] = str((terminal or last).get("artifact_path") or "")
    decision["prior_artifact_hash"] = str((terminal or last).get("artifact_hash") or "")
    decision["prior_run_id"] = str((terminal or last).get("run_id") or "")
    decision["prior_market_id"] = str((terminal or last).get("market_id") or "")
    decision["reusable_evidence"] = bool(terminal and terminal.get("reusable_evidence"))
    decision["routing_repair_required"] = bool(
        terminal and terminal.get("outcome") in TERMINAL_NOT_REUSABLE)
    decision["predecessor_attempt_id"] = str(last.get("attempt_id") or "")
    decision["material_change_reason"] = ""

    override = _material(material_changes, MATERIAL_OPERATOR_OVERRIDE)
    if override:
        decision["decision"] = ALLOWED_OPERATOR_OVERRIDE
        decision["material_change_reason"] = override
        decision["reason"] = ("an operator override permits this repeat "
                              "purchase: %s" % override)
        return decision

    repair = _material(material_changes, MATERIAL_ROUTING_REPAIR)
    if repair and decision["routing_repair_required"]:
        decision["decision"] = ALLOWED_ROUTING_REPAIRED
        decision["material_change_reason"] = repair
        decision["reason"] = ("a documented routing repair changed which "
                              "property this row fetches: %s" % repair)
        return decision

    changed_url = _material(material_changes, MATERIAL_URL_CHANGED)
    if changed_url and canonical_url(row) not in {
            str(a.get("canonical_url") or "") for a in ordered}:
        decision["decision"] = ALLOWED_URL_CHANGED
        decision["material_change_reason"] = changed_url
        decision["reason"] = ("the page this row would fetch is not the page "
                              "that was fetched: %s" % changed_url)
        return decision

    if decision["reusable_evidence"]:
        decision["decision"] = SUPPRESSED_EVIDENCE_REUSABLE
        decision["reason"] = (
            "a prior paid attempt (%s, run %r, lane %r) already answered this "
            "page with %s; the evidence is reusable, so a second purchase "
            "would buy an answer we already own"
            % (match_key.lower().replace("_", " "), decision["prior_run_id"],
               decision["prior_lane"], decision["prior_outcome"]))
        return decision

    if decision["routing_repair_required"]:
        decision["decision"] = SUPPRESSED_ROUTING_REPAIR_REQUIRED
        decision["reason"] = (
            "a prior paid attempt (run %r, lane %r) fetched a DIFFERENT "
            "property from this URL; what changes that answer is a routing "
            "repair, not another purchase of the same wrong page"
            % (decision["prior_run_id"], decision["prior_lane"]))
        return decision

    capability = _material(material_changes, MATERIAL_CAPABILITY_CHANGED)
    if capability:
        decision["decision"] = ALLOWED_CAPABILITY_CHANGED
        decision["material_change_reason"] = capability
        decision["reason"] = ("a provider or reader capability post-dates the "
                              "prior attempt: %s" % capability)
        return decision

    eligible, why = escalation_eligible(str(last.get("outcome") or ""))
    untried = [lane for lane in available_lanes if lane not in lanes_paid]
    if eligible and untried and _escalations_since_decision(ordered) < 1:
        decision["decision"] = ALLOWED_ESCALATION
        decision["escalate_to"] = untried[0]
        decision["material_change_reason"] = (
            "escalation permitted: %s, and %s has never been paid for this page"
            % (why, untried[0]))
        decision["reason"] = decision["material_change_reason"]
        return decision

    if eligible and not available_lanes:
        # No permitted-lane list was offered, so an UNTRIED lane cannot be
        # proven to exist. That is not evidence that one does: the retry policy
        # already refuses to read "we cannot prove it was a different lane" as
        # proof that it was, and this says the same thing about the same gap
        # rather than inventing an escalation nobody authorised.
        decision["decision"] = SUPPRESSED_ESCALATION_EXHAUSTED
        decision["reason"] = (
            "a prior paid attempt (run %r, lane %r) failed on the channel, but "
            "no permitted-lane list was supplied, so no untried lane can be "
            "proven to exist; name the approved ladder to escalate"
            % (decision["prior_run_id"], decision["prior_lane"]))
        return decision

    if eligible and not untried:
        decision["decision"] = SUPPRESSED_ESCALATION_EXHAUSTED
        decision["reason"] = (
            "every permitted lane (%s) has already been paid to fetch this "
            "page; a further purchase needs a new lane, a routing repair or a "
            "named override, not another attempt"
            % (", ".join(lanes_paid) or "none recorded"))
        return decision

    if eligible:
        decision["decision"] = SUPPRESSED_ESCALATION_EXHAUSTED
        decision["reason"] = (
            "this page has already spent its one escalation (%s); a further "
            "purchase needs a NEW material-change decision"
            % " -> ".join(lanes_paid))
        return decision

    decision["decision"] = SUPPRESSED_ALREADY_PAID
    decision["reason"] = (
        "a prior paid attempt (run %r, lane %r) ended %s and nothing material "
        "has changed since: %s"
        % (decision["prior_run_id"], decision["prior_lane"],
           decision["prior_outcome"] or "(unrecorded)", why))
    return decision


def suppress(cohort: Sequence[Mapping], ledger: Mapping, *,
             material_changes: Optional[Mapping[str, Mapping[str, str]]] = None,
             available_lanes: Sequence[str] = ()) -> Tuple[List[Dict], List[Dict]]:
    """``(payable, suppressed)`` over a routed cohort. A partition, always.

    Every input row lands in exactly one list and neither list invents a row,
    so ``coverage`` can keep counting the census it already counts. A
    suppressed property is a property we have an answer for or a repair to do
    -- not a property that vanished.
    """
    index = LedgerIndex(ledger)
    payable: List[Dict] = []
    suppressed: List[Dict] = []
    for row in cohort:
        key = str(row.get("identity_key") or "")
        decision = decide(row, index,
                          material_changes=(material_changes or {}).get(key),
                          available_lanes=available_lanes)
        enriched = OrderedDict(row)
        enriched["paid_history"] = decision
        if decision["decision"] in ALLOWED_DECISIONS:
            payable.append(enriched)
        else:
            enriched["settled_because"] = decision["reason"]
            suppressed.append(enriched)
    return (payable, suppressed)


def summary(payable: Sequence[Mapping], suppressed: Sequence[Mapping]) -> Dict:
    """The paid-history section of a cost plan or a paid-pass report."""
    def _count(rows):
        return Counter(r["paid_history"]["decision"] for r in rows
                       if r.get("paid_history"))
    out = OrderedDict()
    out["schema"] = SCHEMA
    out["payable"] = len(payable)
    out["suppressed"] = len(suppressed)
    out["payable_by_decision"] = OrderedDict(sorted(_count(payable).items()))
    out["suppressed_by_decision"] = OrderedDict(sorted(_count(suppressed).items()))
    out["suppressed_by_match_key"] = OrderedDict(sorted(Counter(
        r["paid_history"]["match_key"] for r in suppressed
        if r.get("paid_history")).items()))
    out["reusable_evidence"] = sum(
        1 for r in suppressed if r.get("paid_history", {}).get("reusable_evidence"))
    out["routing_repair_required"] = sum(
        1 for r in suppressed
        if r.get("paid_history", {}).get("routing_repair_required"))
    out["accounted_for"] = len(payable) + len(suppressed)
    return out


__all__ = [
    "SCHEMA", "WHAT_THIS_IS", "PaidLedgerError",
    "MATCH_PRIORITY", "MATCH_CANONICAL_URL", "MATCH_PROPERTY_CODE",
    "MATCH_PROPERTY_IDENTITY", "MATCH_PREMISES_EVIDENCE", "PAGE_MATCH_KEYS",
    "CONFIRMATION_REQUIRED_KEYS",
    "REUSABLE_OUTCOMES", "TERMINAL_NOT_REUSABLE", "TERMINAL_OUTCOMES",
    "ESCALATABLE_OUTCOMES", "DECISIONS", "ALLOWED_DECISIONS",
    "SUPPRESSED_DECISIONS", "MATERIAL_CHANGES", "ATTEMPT_FIELDS",
    "FIRST_PAID_ATTEMPT", "SUPPRESSED_ALREADY_PAID",
    "SUPPRESSED_EVIDENCE_REUSABLE", "SUPPRESSED_ROUTING_REPAIR_REQUIRED",
    "SUPPRESSED_ESCALATION_EXHAUSTED", "ALLOWED_ESCALATION",
    "ALLOWED_URL_CHANGED", "ALLOWED_CAPABILITY_CHANGED",
    "ALLOWED_ROUTING_REPAIRED", "ALLOWED_OPERATOR_OVERRIDE",
    "MATERIAL_URL_CHANGED", "MATERIAL_CAPABILITY_CHANGED",
    "MATERIAL_ROUTING_REPAIR", "MATERIAL_OPERATOR_OVERRIDE",
    "canonical_url", "property_code", "normalized_host", "normalized_path",
    "normalized_street", "normalized_phone", "postal_code",
    "property_identity", "attempt_id", "build_attempt", "escalation_eligible",
    "ingest_run", "new_ledger", "load", "save", "merge", "LedgerIndex",
    "decide", "suppress", "summary",
]
