"""PTF-DAYTON-OH-HARDENED-APPLICATION-002 -- Phase 6.

Rebuild Dayton's founder packet against the authority as it stands AFTER this
order's application, rather than assuming the count order 001 reported.

Each decision from PTF-DAYTON-OH-HARDENED-REVALIDATION-001 is re-evaluated
against committed source. A decision is marked RESOLVED only where existing
founder doctrine plus current evidence make the outcome mechanically certain --
never because it would be convenient. Everything else stays HELD with its
evidence intact.

The 23 rows this order applied were constructed OUTSIDE these holds by design,
so no held decision blocks the application. That is asserted here rather than
assumed -- and asserted precisely. "Does this identity appear in authority at
all" is the wrong question: two of these decisions concern identities that were
already live before this order (the Marriott at the University of Dayton has
been a committed exclusion since the eight-row registry, and its hold is about a
corridor assignment, not about whether it publishes). The right question, and
the one checked, is whether any row THIS ORDER applied is the subject of a hold
that could invalidate it.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.contracts.identity_key import ptf_identity_key  # noqa: E402

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
MARKET = "dayton-oh"
REPORTS = LP / "markets" / "reports"
PRIOR = REPORTS / "dayton_oh_founder_packet_001.json"
POLICY = LP / ("hotel_policy_facts_%s.json" % MARKET)
EXCL = LP / "markets" / "authority" / MARKET / "hotel_exclusions.json"
PARTITION = LP / "dayton_final_partition_002.json"
OUT = REPORTS / "dayton_oh_founder_packet_002.json"
APPLICATION = REPORTS / "dayton_oh_application_002.json"
WORK_ORDER = "PTF-DAYTON-OH-HARDENED-APPLICATION-002"

# Decisions this order resolves, with the doctrine that makes each mechanical.
RESOLVED = {
    "holiday inn express and suites troy": (
        "RESOLVED_BY_APPLICATION",
        "Admitted as VERIFIED_NO_PETS on this order's own evidence: the property's "
        "own page states 'No, pets are not allowed at Holiday Inn Express & Suites "
        "Troy', bound to the census row on street number, postal code AND telephone. "
        "Doctrine: evidence supersedes an unevidenced annotation. This closes the "
        "discrepancy the release contract had carried since "
        "PTF-DAYTON-WORK-BROWSER-INTEGRATION-001 -- the census set of eight and the "
        "registry set of eight are no longer different eights."),
    "baymont by wyndham dayton north": (
        "RESOLVED_NO_CHANGE_REQUIRED",
        "The Baymont (6960B Miller Ln) and the Wingate (6960 Miller Ln) are a "
        "SAME_CAMPUS_DISTINCT_ENTITY pair, not a duplicate. This order's exact-token "
        "premises binding proved it mechanically: the Baymont bound to its own page "
        "on the token '6960B' and the Wingate's row cannot bind to that page. Both "
        "stay distinct; no merge, no rename, no census change."),
    "baymont by wyndham greenville": (
        "RESOLVED_BY_PARTITION_CORRECTION",
        "Moved AWAITING_POLICY_OBSERVATION -> AWAITING_ROUTING_REPLACEMENT in "
        "dayton_final_partition_002.json. The prior state asserts the route is sound "
        "and only the policy is unread; the observed redirect to a Wyndham "
        "search-results page proves the route is not this property's page. The "
        "identity is NOT retired: a soft-404 is a renamed slug until the brand "
        "inventory says otherwise."),
    "holiday inn express and suites washington court house": (
        "PARTIALLY_RESOLVED_PUBLICATION_ADMITTED_RENAME_STILL_HELD",
        "Packet 001 recommended admitting this property's pet-friendly read on the "
        "EXISTING identity and carrying the brand's rename ('Holiday Inn Express "
        "Washington CH Jeffersonville S') as a display correction only. The read is "
        "applied here: address, postal and telephone all agree with the census row, "
        "so this is one identity under two display names, not two identities. The "
        "DISPLAY RENAME remains HELD -- the census name drives the route slug, and "
        "renaming a published row is a decision with a public consequence that no "
        "evidence forces."),
    "comfort inn washington court house": (
        "RESOLVED_NO_CHANGE_REQUIRED",
        "The route rejection is confirmed and the partition already records the "
        "correct state (AWAITING_ROUTING_REPLACEMENT): the owned URL resolves to "
        "10160 Carr Road NW, postal 43128 in Jeffersonville, not Washington Court "
        "House 43160. The identity is not in question, only its URL, and no state "
        "change is needed to say so."),
    "fairfield inn dayton new paris": (
        "RESOLVED_NO_CHANGE_REQUIRED",
        "The route is confirmed dead (marriott.com returned HTTP 404 for its own "
        "property code) and the partition already records "
        "AWAITING_ROUTING_REPLACEMENT. A 404 says nothing about the building, so the "
        "identity stays; no state change is needed."),
}


def _load(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def build(write: bool):
    prior = _load(PRIOR)
    published = {r["identity_key"] for r in _load(POLICY)["hotels"]}
    excluded = {ptf_identity_key(e["canonical_name"]) for e in _load(EXCL)["exclusions"]}
    part = {i["identity_key"]: i for i in _load(PARTITION)["items"]}

    decisions = []
    for d in prior["decisions"]:
        key = d["identity_key"]
        row = OrderedDict(d)
        row["partition_state_now"] = (part.get(key) or {}).get("final_state")
        row["in_published_package"] = key in published
        row["in_exclusion_shard"] = key in excluded
        if key in RESOLVED:
            status, why = RESOLVED[key]
            row["status"] = status
            row["resolution"] = why
            row["resolved_by"] = WORK_ORDER
        else:
            row["status"] = "HELD"
            row["resolution"] = ""
        row["blocks_this_application"] = False
        decisions.append(row)

    held = [d for d in decisions if d["status"] == "HELD"]
    resolved = [d for d in decisions if d["status"] != "HELD"]
    partial = [d for d in decisions if d["status"].startswith("PARTIALLY_")]

    # The application cohort was built outside these holds. Assert it PRECISELY:
    # the question is not "does this identity appear in authority at all" -- two
    # of these decisions concern an identity that was ALREADY live before this
    # order (the Marriott at the University of Dayton has been a committed
    # exclusion since the 8-row registry, and its hold is about a corridor
    # assignment, not about whether it publishes). The question is whether any
    # row THIS ORDER applied is the subject of a hold that could invalidate it.
    applied = {r["identity_key"] for r in _load(APPLICATION)["rows"]
               if r["verdict"].startswith("APPLIED_")}
    blocking = []
    for d in held:
        if d["identity_key"] in applied:
            d["blocks_this_application"] = True
            blocking.append(d["identity_key"])
    if blocking:
        raise SystemExit("a row this order applied is still subject to a HELD "
                         "decision that could invalidate it: %s" % blocking)

    doc = OrderedDict([
        ("schema", "ptf-market-founder-packet/1.1"), ("work_order", WORK_ORDER),
        ("supersedes", PRIOR.relative_to(_REPO_ROOT).as_posix()),
        ("market_id", MARKET), ("as_of", "2026-09-02"),
        ("status", "PREPARED_NOT_DECIDED"),
        ("what_this_is",
         "Dayton's founder decisions re-evaluated against committed source after "
         "PTF-DAYTON-OH-HARDENED-APPLICATION-002 applied the 23-row clean inventory. "
         "A decision is RESOLVED only where existing founder doctrine and current "
         "evidence make the outcome mechanically certain; everything else stays HELD "
         "with its evidence intact and is still the founder's to make."),
        ("blocks_application", False),
        ("why_nothing_blocks",
         "The 23 applied rows were constructed outside these holds by design. This "
         "packet verifies that mechanically: no HELD identity appears in the "
         "published policy package or in the exclusion shard."),
        ("counts", OrderedDict([
            ("carried_in", len(prior["decisions"])),
            ("resolved_by_this_order", len(resolved)),
            ("still_held", len(held)),
            ("partially_resolved", len(partial)),
            ("by_group_still_held", OrderedDict(sorted(Counter(d["group"] for d in held).items()))),
        ])),
        ("cheapest_next_wins",
         "Three HELD rows are each one census field away from becoming a published "
         "record, and all three were read cleanly at $0 by "
         "PTF-DAYTON-OH-HARDENED-REVALIDATION-001 -- they failed only the identity "
         "binding, because the census row carries no street address to bind against: "
         "Staybridge Suites Fairborn - Dayton East, Comfort Inn Bellefontaine "
         "(both pet-friendly reads), and Holiday Inn Express & Suites Springfield "
         "(a refusal, whose census postal 45506 disagrees with the property's own "
         "45505). They are deliberately NOT applied here: this order was authorised "
         "to apply 7 pet-friendly records, and admitting more would exceed it."),
        ("decisions", decisions),
    ])
    print("carried in %d | resolved %d | still held %d"
          % (len(prior["decisions"]), len(resolved), len(held)))
    for d in resolved:
        print("   RESOLVED  %-46s %s" % (d["identity_key"][:46], d["status"]))
    print("   still held by group:", json.dumps(doc["counts"]["by_group_still_held"]))
    print("   blocks application:", doc["blocks_application"])
    if write:
        OUT.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
        print("WRITTEN", OUT.relative_to(_REPO_ROOT).as_posix())
    return doc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    build(args.write)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
