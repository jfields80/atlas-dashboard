"""The Phase F review queue, derived from committed authority.

What this is for
----------------
The contract freeze estimated how much of the migration a machine could do and
how much needed a person. Estimates from a document are worth less than counts
from the corpus, so this module derives the queue: every record that cannot
reach schema 1.2 mechanically, grouped by the decision a reviewer has to make.

Strictly read-only. It opens committed authority, reports, and writes nothing
unless an operator names an output path -- and even then it refuses to write
inside ``launch_packages`` or ``deploy``, because a report that can overwrite
the authority it describes is one typo away from being the authority.

Usage
-----
    python -m scripts.pettripfinder.contracts.review_queue
    python -m scripts.pettripfinder.contracts.review_queue --out <path>.json
    python -m scripts.pettripfinder.contracts.review_queue --market dayton-oh
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from scripts.pettripfinder.contracts import census, enums, partition
from scripts.pettripfinder.contracts import policy_schema as ps
from scripts.pettripfinder.contracts.compat_readers import ReviewItem, read_package

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_DIR = REPO_ROOT / "launch_packages" / "pettripfinder"

#: Committed policy packages, market id -> filename.
POLICY_PACKAGES: "OrderedDict[str, str]" = OrderedDict((
    ("columbus-oh", "hotel_policy_facts.json"),
    ("cleveland-akron-canton-oh",
     "hotel_policy_facts_cleveland-akron-canton-oh.json"),
    ("dayton-oh", "hotel_policy_facts_dayton-oh.json"),
))

#: What a reviewer actually has to decide, per review code. Ordered by how much
#: judgement each demands, so the queue reads as a work plan rather than a
#: tally.
DECISIONS: "OrderedDict[str, str]" = OrderedDict((
    ("NO_APPROVAL_DECISION",
     "Re-review the record and record LEGACY_BASELINE_REVIEWED with today's "
     "date. Never back-date an approval nobody gave."),
    ("COMBINED_IN_OPERATOR_SLOT",
     "The weight moved to combined_weight_limit; read the evidence quote and "
     "choose lt or lte. No default is safe."),
    ("CAP_QUALIFIERS_INCOMPLETE",
     "Read the cap's quote for scope, pet count and any night trigger. A cap "
     "never inherits scope from the fee it caps."),
    ("TIER_ROLE_UNSET",
     "Decide per tier: replacement price, additional charge, or incremental "
     "unit price."),
    ("ADDITIVE_UNRECORDED",
     "Confirm from the quote whether each schedule rung is charged in addition "
     "to lower ordinals."),
    ("WITHHELD_PROSE",
     "Assign a reason code, or DROP the entry where it merely restates "
     "silence. Silence is absence, not a withholding decision."),
    ("SPECIES_PROSE",
     "Convert prose to a species state map. Generic \"pets\" yields an EMPTY "
     "map, never dogs+cats."),
    ("LEGACY_FEE_WITHHOLDING",
     "Attach evidence_refs to the migrated withheld_fields entry."),
    ("SERVICE_ANIMAL_MOVED",
     "Recover the property's own quote before claiming no_charge."),
    ("DEPOSIT_SHAPE",
     "Confirm refundability from the quote. \"Deposit Yes. $75 Non-refundable "
     "Fee\" is a non-refundable fee."),
    ("CLEANING_FEE_SHAPE",
     "Write an other_charges entry with an explicit refundable flag."),
    ("UNKNOWN_SCOPE",
     "Fee scope value is outside the legacy vocabulary; read the source."),
    ("UNKNOWN_BASIS",
     "Fee basis string is not in the decomposition table; read the source."),
    ("UNPARSEABLE_MONEY",
     "The stored amount is not readable as money; read the source."),
    ("UNPARSEABLE_WEIGHT",
     "The stored weight is not readable; read the source."),
    ("UNKNOWN_DECISION",
     "Approval decision string is outside the legacy map."),
    ("NO_IDENTITY_KEY",
     "The record's name does not produce an identity key."),
))


def _load(path: Path) -> Optional[dict]:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def collect_policy_review(market_ids: Sequence[str]) -> Tuple[
        List[ReviewItem], Dict[str, int], List[str]]:
    """Review items and record counts from the committed policy packages."""
    review: List[ReviewItem] = []
    counts: Dict[str, int] = {}
    absent: List[str] = []
    for market_id in market_ids:
        filename = POLICY_PACKAGES.get(market_id)
        if filename is None:
            continue
        package = _load(PACKAGE_DIR / filename)
        if package is None:
            absent.append("%s (%s)" % (market_id, filename))
            continue
        document, items = read_package(package)
        counts[market_id] = len(document["hotels"])
        review.extend(items)
    return review, counts, absent


def collect_structural_gaps(market_ids: Sequence[str]) -> Dict[str, Dict[str, int]]:
    """Schema gaps that survive compatibility reading, by market and code.

    These should only ever be the two things a machine genuinely cannot decide.
    Anything else appearing here means the reader stopped short of a
    transformation it should have made.
    """
    out: Dict[str, Dict[str, int]] = {}
    for market_id in market_ids:
        filename = POLICY_PACKAGES.get(market_id)
        package = _load(PACKAGE_DIR / filename) if filename else None
        if package is None:
            continue
        document, _ = read_package(package)
        by_code: Dict[str, int] = defaultdict(int)
        for issue in ps.validate_package(document):
            by_code[issue.code] += 1
        if by_code:
            out[market_id] = dict(by_code)
    return out


def collect_identity_findings(market_ids: Sequence[str]) -> Dict[str, object]:
    """Census, partition and routing findings across committed authority."""
    routing = _load(PACKAGE_DIR / "identity_routing.json") or {}
    routes = routing.get("routes") or []
    findings: Dict[str, object] = OrderedDict()

    for market_id in market_ids:
        entry: Dict[str, object] = OrderedDict()
        census_doc = _load(PACKAGE_DIR / "identity_census" / ("%s.json" % market_id))

        if census_doc is None:
            entry["census"] = "ABSENT -- no committed census for this market"
            entry["census_issues"] = []
            keys = set()
        else:
            keys = census.identity_keys(census_doc)
            entry["census"] = census_doc.get("count")
            by_code: Dict[str, int] = defaultdict(int)
            for issue in census.validate(census_doc):
                by_code[issue.code] += 1
            entry["census_issues"] = dict(by_code)

        market_routes = [r for r in routes if r.get("market_id") == market_id]
        entry["routing_records"] = len(market_routes)
        if census_doc is None:
            entry["routing_subset_of_census"] = "UNEVALUABLE -- no census"
        else:
            violations = partition.routing_subset_violations(
                routes, keys, market_id=market_id)
            entry["routing_violations"] = [i.detail for i in violations]

        findings[market_id] = entry

    # The one committed partition, reconciled by set rather than by subtraction.
    partition_doc = _load(PACKAGE_DIR / "cleveland_final_partition_002.json")
    cleveland = _load(PACKAGE_DIR / "identity_census"
                      / "cleveland-akron-canton-oh.json")
    if partition_doc and cleveland:
        rec = partition.reconcile(census.identity_keys(cleveland), partition_doc,
                                  market_id="cleveland-akron-canton-oh")
        findings["_partition_cleveland"] = OrderedDict((
            ("census_count", rec.census_count),
            ("partition_count", rec.partition_count),
            ("agrees", rec.agrees),
            ("published", rec.published),
            ("verified_no_pets", rec.verified_no_pets),
            ("resolved", rec.resolved),
            ("unresolved", rec.unresolved),
            ("missing_from_partition", list(rec.missing_from_partition)),
            ("missing_from_census", list(rec.missing_from_census)),
        ))
    markets_without_partition = [
        m for m in market_ids if m != "cleveland-akron-canton-oh"]
    findings["_markets_without_partition"] = markets_without_partition
    return findings


def build_report(market_ids: Sequence[str]) -> "OrderedDict[str, object]":
    review, counts, absent = collect_policy_review(market_ids)

    by_code: Dict[str, List[ReviewItem]] = defaultdict(list)
    for item in review:
        by_code[item.code].append(item)

    queue: "OrderedDict[str, object]" = OrderedDict()
    # Known decisions first, in the order a reviewer should work them.
    ordered = [c for c in DECISIONS if c in by_code]
    ordered += sorted(c for c in by_code if c not in DECISIONS)
    for code in ordered:
        items = by_code[code]
        per_market: Dict[str, int] = defaultdict(int)
        for item in items:
            per_market[item.market_id or "<unknown>"] += 1
        queue[code] = OrderedDict((
            ("decision", DECISIONS.get(code, "UNCLASSIFIED -- triage required")),
            ("items", len(items)),
            ("records", len({i.identity_key for i in items})),
            ("by_market", dict(per_market)),
        ))

    return OrderedDict((
        ("work_order", "PTF-CONTRACT-FOUNDATION-001"),
        ("phase", "A"),
        ("note", "Read-only survey of committed authority. Nothing here has "
                 "been migrated; these are the decisions Phase F requires."),
        ("policy_records_read", counts),
        ("policy_records_total", sum(counts.values())),
        ("packages_absent", absent),
        ("review_items_total", len(review)),
        ("review_records_total", len({i.identity_key for i in review})),
        ("queue", queue),
        ("structural_gaps_after_compat_read", collect_structural_gaps(market_ids)),
        ("identity_findings", collect_identity_findings(market_ids)),
    ))


def _print(report: Mapping) -> None:
    out = sys.stdout.write
    out("\n%s -- Phase F review queue\n" % report["work_order"])
    out("=" * 66 + "\n\n")

    out("Policy records read\n")
    for market_id, count in (report["policy_records_read"] or {}).items():
        out("  %-30s %4d\n" % (market_id, count))
    out("  %-30s %4d\n" % ("TOTAL", report["policy_records_total"]))
    for missing in report["packages_absent"]:
        out("  ABSENT: %s\n" % missing)

    out("\nReview queue -- %d items across %d records\n"
        % (report["review_items_total"], report["review_records_total"]))
    out("-" * 66 + "\n")
    for code, entry in report["queue"].items():
        out("  %-28s %4d items  %4d records\n"
            % (code, entry["items"], entry["records"]))
        out("      %s\n" % entry["decision"])

    gaps = report["structural_gaps_after_compat_read"]
    out("\nStructural gaps surviving compatibility reading\n")
    out("-" * 66 + "\n")
    if not gaps:
        out("  none\n")
    for market_id, by_code in gaps.items():
        for code, count in sorted(by_code.items()):
            out("  %-30s %-22s %4d\n" % (market_id, code, count))

    out("\nIdentity findings\n")
    out("-" * 66 + "\n")
    for market_id, entry in report["identity_findings"].items():
        if market_id.startswith("_"):
            continue
        out("  %s\n" % market_id)
        out("    census                : %s\n" % entry["census"])
        out("    routing records       : %s\n" % entry["routing_records"])
        if "routing_violations" in entry:
            violations = entry["routing_violations"]
            out("    routing subset census : %s\n"
                % ("OK" if not violations else "%d VIOLATION(S)" % len(violations)))
            for detail in violations:
                out("        %s\n" % detail)
        else:
            out("    routing subset census : %s\n"
                % entry["routing_subset_of_census"])
        issues = entry.get("census_issues") or {}
        if issues:
            for code, count in sorted(issues.items()):
                out("    census issue          : %-24s %d\n" % (code, count))

    cleveland = report["identity_findings"].get("_partition_cleveland")
    if cleveland:
        out("\n  Cleveland partition (the only committed one)\n")
        for key, value in cleveland.items():
            out("    %-24s %s\n" % (key, value))
    without = report["identity_findings"].get("_markets_without_partition") or []
    if without:
        out("\n  Markets with NO final partition: %s\n" % ", ".join(without))
    out("\n")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Derive the Phase F review queue from committed authority "
                    "(read-only).")
    parser.add_argument("--market", action="append", dest="markets",
                        help="restrict to a market id (repeatable)")
    parser.add_argument("--out", type=Path,
                        help="write the report as JSON to this path")
    parser.add_argument("--json", action="store_true",
                        help="print JSON instead of the text summary")
    args = parser.parse_args(argv)

    market_ids = args.markets or list(POLICY_PACKAGES)
    unknown = [m for m in market_ids if m not in POLICY_PACKAGES]
    if unknown:
        parser.error("unknown market(s): %s" % ", ".join(unknown))

    report = build_report(market_ids)

    if args.out:
        destination = args.out.resolve()
        # A report that can overwrite the authority it describes is one typo
        # away from becoming the authority.
        for protected in (PACKAGE_DIR.resolve(), (REPO_ROOT / "deploy").resolve()):
            if protected in destination.parents or destination == protected:
                parser.error("refusing to write inside %s" % protected)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2) + "\n",
                               encoding="utf-8")
        sys.stdout.write("wrote %s\n" % destination)

    if args.json:
        sys.stdout.write(json.dumps(report, indent=2) + "\n")
    else:
        _print(report)
    return 0


if __name__ == "__main__":                                # pragma: no cover
    raise SystemExit(main())
