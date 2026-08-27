"""PTF-GENERIC-CROSS-RUN-PAID-ATTEMPT-LEDGER-001 -- what the leak actually cost.

Reads saved acquisition artifacts and answers one question per market: how many
times did we pay to fetch the same page, and which of those repeats were
justified?

OFFLINE BY CONSTRUCTION. It opens committed JSON documents and nothing else --
no provider, no network, no re-acquisition. It never writes a historical
artifact; the ledger it emits is a NEW document derived from them.

HOW A REPEAT IS COUNTED
-----------------------
An ENTITY is a page: the brand's property code where one exists, else the
canonical URL. That is the unit the money is spent on, and it is deliberately
NOT the identity key -- the whole finding this audit exists to produce is that
one page gets bought under several identity keys.

A repeat is any attempt on an entity after its first. Each repeat is then
classified against the state the entity was in when it happened:

    JUSTIFIED_ESCALATION   the previous attempt failed on the CHANNEL and this
                           attempt used a lane that entity had never paid for.
                           This is the spend the retry policy is designed to
                           permit, and it is not waste.
    SAME_LANE_REPEAT       a lane this entity had already paid for, again.
    REPEAT_AFTER_TERMINAL  the entity had already been ANSWERED -- VALID,
                           POLICY_NOT_FOUND, or IDENTITY_MISMATCH -- and was
                           bought anyway.
    UNJUSTIFIED_REPEAT     a new lane, but the previous outcome was not one a
                           different lane could change.

Only ``JUSTIFIED_ESCALATION`` is excluded from the waste figure.

ON THE MONEY
------------
The vendor meters a zone over a session, not a property, so no per-property
price was ever recorded. Every dollar figure here is the run total apportioned
evenly over that run's attempts, and it is labelled ``estimated``. It is the
right order of magnitude and the wrong number to invoice anybody for.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import paid_attempt_ledger as PAL  # noqa: E402

SCHEMA = "ptf-paid-attempt-audit/1.0"

JUSTIFIED_ESCALATION = "JUSTIFIED_ESCALATION"
SAME_LANE_REPEAT = "SAME_LANE_REPEAT"
REPEAT_AFTER_TERMINAL = "REPEAT_AFTER_TERMINAL"
UNJUSTIFIED_REPEAT = "UNJUSTIFIED_REPEAT"

WASTEFUL = (SAME_LANE_REPEAT, REPEAT_AFTER_TERMINAL, UNJUSTIFIED_REPEAT)


def entity_of(record: Mapping) -> str:
    """The page a paid attempt bought. Property code first, then URL.

    The code outranks the URL because a brand spells one property's URL several
    ways -- ``/hotels/travel/SDFLM-...`` and ``/en-us/hotels/SDFLM-...`` are one
    page -- and the code is the brand's own primary key for the building.
    """
    code = str(record.get("property_code") or "")
    if code:
        return "PROPERTY_CODE:%s" % code
    url = str(record.get("canonical_url") or "")
    return ("CANONICAL_URL:%s" % url) if url else ""


def _sort_key(record: Mapping) -> Tuple:
    return (str(record.get("attempted_at") or ""),
            str(record.get("run_id") or ""),
            str(record.get("attempt_id") or ""))


def classify_repeats(attempts: Sequence[Mapping]) -> List[Dict]:
    """One verdict per attempt on one entity, in chronological order.

    The first attempt is never a repeat. Every later one is judged against
    what the entity's history looked like immediately before it, which is why
    this walks forward accumulating rather than reading the final state: an
    attempt made before the terminal answer arrived was not a repeat after a
    terminal answer.
    """
    ordered = sorted(attempts, key=_sort_key)
    lanes_paid: List[str] = []
    terminal_seen = ""
    last_outcome = ""
    # Whether the attempt immediately before this one left the page in a state
    # a DIFFERENT lane could plausibly change. Read off the record rather than
    # re-derived from its outcome, because a run's intermediate ladder step has
    # no outcome of its own to re-derive from: the router moved to the next
    # lane precisely BECAUSE that step failed on the channel, and treating the
    # missing outcome as "not escalatable" would score the retry policy's own
    # sanctioned behaviour as waste.
    last_escalatable = False
    out: List[Dict] = []
    for index, record in enumerate(ordered):
        lane = str(record.get("lane") or "")
        outcome = str(record.get("outcome") or "")
        verdict = ""
        why = ""
        if index == 0:
            verdict = "FIRST_ATTEMPT"
            why = "the first time this page was paid for"
        elif terminal_seen:
            verdict = REPEAT_AFTER_TERMINAL
            why = ("this page had already been answered %s; the answer was "
                   "bought again" % terminal_seen)
        elif lane in lanes_paid:
            verdict = SAME_LANE_REPEAT
            why = ("lane %r had already been paid to fetch this page and was "
                   "paid again" % lane)
        elif last_escalatable:
            verdict = JUSTIFIED_ESCALATION
            why = ("the previous attempt ended %s -- a channel failure -- and "
                   "%s had never been paid for this page"
                   % (last_outcome or "on an un-recorded ladder step", lane))
        else:
            _, reason = PAL.escalation_eligible(last_outcome)
            verdict = UNJUSTIFIED_REPEAT
            why = "a new lane, but %s" % reason
        row = OrderedDict(record)
        row["repeat_verdict"] = verdict
        row["repeat_why"] = why
        out.append(row)
        if lane and lane not in lanes_paid:
            lanes_paid.append(lane)
        if outcome:
            last_outcome = outcome
        last_escalatable = bool(record.get("escalation_eligible"))
        if record.get("terminal") and not terminal_seen:
            terminal_seen = outcome
    return out


def audit_market(market_id: str, ledger: Mapping) -> Dict:
    """The historical paid-attempt audit for one market."""
    attempts = [a for a in (ledger.get("attempts") or ())
                if str(a.get("market_id") or "") == market_id]
    by_entity: Dict[str, List[Dict]] = OrderedDict()
    unkeyed = 0
    for record in attempts:
        entity = entity_of(record)
        if not entity:
            unkeyed += 1
            continue
        by_entity.setdefault(entity, []).append(dict(record))

    classified: Dict[str, List[Dict]] = OrderedDict()
    for entity, records in by_entity.items():
        classified[entity] = classify_repeats(records)

    verdicts = Counter(r["repeat_verdict"] for rows in classified.values()
                       for r in rows)
    distribution = Counter(len(rows) for rows in classified.values())
    wasted_usd = 0.0
    wasted_credits = 0.0
    for rows in classified.values():
        for row in rows:
            if row["repeat_verdict"] in WASTEFUL:
                wasted_usd += float(row.get("cost_usd_minor") or 0.0)
                wasted_credits += float(row.get("firecrawl_credits") or 0.0)

    worst = sorted(((len(rows), entity, rows) for entity, rows in classified.items()),
                   key=lambda t: (-t[0], t[1]))
    heavy = [_entity_report(entity, rows) for count, entity, rows in worst
             if count >= 3]

    identity_keys = {str(a.get("identity_key") or "") for a in attempts}
    repeated_entities = sum(1 for rows in classified.values() if len(rows) > 1)

    out = OrderedDict()
    out["market_id"] = market_id
    out["total_paid_attempts"] = len(attempts)
    out["attempts_without_a_page_key"] = unkeyed
    out["unique_identity_keys"] = len(identity_keys)
    out["unique_page_entities"] = len(classified)
    out["entities_bought_more_than_once"] = repeated_entities
    out["repeated_paid_attempts"] = len(attempts) - unkeyed - len(classified)
    out["same_lane_repeats"] = verdicts.get(SAME_LANE_REPEAT, 0)
    out["justified_cross_lane_escalations"] = verdicts.get(JUSTIFIED_ESCALATION, 0)
    out["repeats_after_a_terminal_answer"] = verdicts.get(REPEAT_AFTER_TERMINAL, 0)
    out["unjustified_repeats"] = sum(verdicts.get(v, 0) for v in WASTEFUL)
    out["repeat_distribution"] = OrderedDict(
        ("%d attempt%s" % (n, "" if n == 1 else "s"), distribution[n])
        for n in sorted(distribution))
    out["max_attempts_on_one_page"] = max(distribution) if distribution else 0
    out["estimated_wasted_usd_minor"] = round(wasted_usd, 2)
    out["estimated_wasted_firecrawl_credits"] = round(wasted_credits, 2)
    out["rows_the_ledger_would_have_suppressed"] = out["unjustified_repeats"]
    out["pages_bought_three_or_more_times"] = heavy
    return out


def _entity_report(entity: str, rows: Sequence[Mapping]) -> Dict:
    out = OrderedDict()
    out["entity"] = entity
    out["attempts"] = len(rows)
    out["identity_keys"] = sorted({str(r.get("identity_key") or "") for r in rows})
    out["names"] = sorted({str(r.get("canonical_name") or "") for r in rows})
    out["runs"] = [str(r.get("run_id") or "") for r in rows]
    out["lanes"] = [str(r.get("lane") or "") for r in rows]
    out["outcomes"] = [str(r.get("outcome") or "") for r in rows]
    out["verdicts"] = [r["repeat_verdict"] for r in rows]
    out["why"] = [r["repeat_why"] for r in rows]
    return out


def build(ledger: Mapping, markets: Sequence[str] = ()) -> Dict:
    present = []
    for record in (ledger.get("attempts") or ()):
        market = str(record.get("market_id") or "")
        if market and market not in present:
            present.append(market)
    markets = list(markets) or sorted(present)
    out = OrderedDict()
    out["schema"] = SCHEMA
    out["what_this_is"] = (
        "An offline audit of every saved paid acquisition attempt, asking how "
        "often one page was bought more than once and which of those repeats "
        "the hardened retry policy would have permitted. No network calls; no "
        "historical artifact was modified.")
    out["markets"] = [audit_market(m, ledger) for m in markets]
    out["totals"] = _totals(out["markets"])
    return out


def _totals(reports: Sequence[Mapping]) -> Dict:
    fields = ("total_paid_attempts", "unique_page_entities",
              "repeated_paid_attempts", "same_lane_repeats",
              "justified_cross_lane_escalations",
              "repeats_after_a_terminal_answer", "unjustified_repeats",
              "rows_the_ledger_would_have_suppressed")
    out = OrderedDict((f, sum(int(r.get(f) or 0) for r in reports)) for f in fields)
    out["estimated_wasted_usd_minor"] = round(
        sum(float(r.get("estimated_wasted_usd_minor") or 0) for r in reports), 2)
    out["estimated_wasted_firecrawl_credits"] = round(
        sum(float(r.get("estimated_wasted_firecrawl_credits") or 0) for r in reports), 2)
    out["max_attempts_on_one_page"] = max(
        [int(r.get("max_attempts_on_one_page") or 0) for r in reports] or [0])
    return out


def ingest_provenance_rows(rows: Sequence[Mapping], *, market_id: str,
                           work_order: str = "", default_run: str = "") -> List[Dict]:
    """Paid attempts recovered from rows that carry a PROVENANCE block.

    Milwaukee ran before ``ptf-market-paid-acquisition/1.0`` existed, so it has
    no per-attempt document at all -- only aggregate run reports and a
    proposals document whose rows each name the provider, reader, run and
    snapshot hash that produced them. That is one attempt per row, recorded
    after the fact, and it is enough to answer the double-buy question for that
    market: if two identity keys carry provenance pointing at ONE page, the
    project paid twice for one fetch.

    What it CANNOT show is the failures. A proposals row exists because the
    fetch succeeded, so a Milwaukee property that was attempted three times and
    read once appears here once. Every number this adapter feeds is therefore a
    FLOOR on that market's repeat count, never a ceiling, and the audit says so
    rather than presenting a floor as a total.
    """
    records: List[Dict] = []
    for row in rows:
        prov = row.get("provenance") or {}
        merged = dict(row)
        merged["source_url"] = prov.get("source_url") or row.get("official_url") or ""
        merged["provider"] = prov.get("provider") or ""
        merged["reader"] = prov.get("reader") or ""
        merged["completed_at"] = prov.get("retrieved_at") or ""
        merged["content_hash"] = prov.get("snapshot_hash") or ""
        merged["artifact_dir"] = prov.get("raw_pointer") or ""
        merged["outcome"] = (PAL.O.VALID if row.get("publication_grade")
                             else PAL.O.POLICY_NOT_FOUND)
        merged["final_state"] = ("ACQUIRED_PUBLICATION_GRADE"
                                 if row.get("publication_grade") else "")
        merged["providers_tried"] = [merged["provider"]] if merged["provider"] else []
        records.append(PAL.build_attempt(
            merged, market_id=market_id, work_order=work_order,
            run_id=str(row.get("source_run") or default_run)))
    return records


def ledger_from_documents(paths: Sequence[Path], *, census: Optional[Mapping] = None
                          ) -> Dict:
    """Ingest saved paid passes into one ledger. Dry runs contribute nothing."""
    ledger = PAL.new_ledger()
    for path in paths:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
        if document.get("schema") != "ptf-market-paid-acquisition/1.0":
            continue
        rows = (census or {}).get(str(document.get("market_id") or ""), ())
        ledger = PAL.merge(ledger, PAL.ingest_run(document, census=rows))
    return ledger


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--document", action="append", default=[],
                        help="a saved ptf-market-paid-acquisition document; "
                             "repeatable. Dry runs are ignored: a plan is not "
                             "a purchase")
    parser.add_argument("--census", action="append", default=[],
                        help="market_id=path to an identity census, to supply "
                             "the address and telephone the acquisition report "
                             "does not carry; optional and additive")
    parser.add_argument("--market", action="append", default=[],
                        help="restrict the report to these markets")
    parser.add_argument("--ledger-out", default="",
                        help="write the derived paid-attempt ledger here")
    parser.add_argument("--out", default="", help="write the audit here")
    args = parser.parse_args(argv)

    censuses: Dict[str, List[Mapping]] = {}
    for pair in args.census:
        market, _, path = pair.partition("=")
        censuses[market] = json.loads(
            Path(path).read_text(encoding="utf-8")).get("hotels") or []

    ledger = ledger_from_documents([Path(p) for p in args.document],
                                   census=censuses)
    report = build(ledger, args.market)
    if args.ledger_out:
        PAL.save(args.ledger_out, ledger)
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2) + "\n",
                                  encoding="utf-8")
    print(json.dumps(report["totals"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
