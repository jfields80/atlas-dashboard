"""PTF-CINCINNATI-HARDENED-REVALIDATION-001 -- Phase 15 / 16 / 18.

ONE grouped founder packet, derived from this order's committed artifacts.

Every item names what it is, what the evidence says, what it would do to the
census, the authority and the routing, whether it reverses, and -- the only
question that gates the next order -- whether it BLOCKS promotion. Items are
grouped so a founder rules on a class once instead of on twenty rows one at a
time; the rows are listed under each ruling so nothing is decided in bulk
without being seen.

Nothing here is authority. No record is written, no identity resolved, no
exclusion registered, no route changed.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
from collections import OrderedDict
from pathlib import Path

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-CINCINNATI-HARDENED-REVALIDATION-001"
MARKET_ID = "cincinnati-oh"
SCHEMA = "ptf-founder-packet/1.1"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")

#: The settled planning rate, from PTF-CINCINNATI-MARRIOTT-SCALE-BATCH-016.
#: The two meters disagree by ~60% and this is the higher; planning on the
#: cheaper one is how a batch discovers mid-run that it cannot finish.
BRIGHTDATA_USD_PER_ATTEMPT = 0.17
ATTEMPTS_PER_ROW_EXPECTED = 1.3
ATTEMPTS_PER_ROW_CEILING = 2
OPERATIONAL_FLOOR_USD = 1.00


def J(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def item(**kw):
    return OrderedDict((k, kw[k]) for k in (
        "id", "current_identity", "evidence", "proposed_action", "recommendation",
        "census_effect", "authority_effect", "routing_effect", "reversibility",
        "blocks_promotion", "rows") if k in kw)


def build(args) -> OrderedDict:
    shadow = J(os.path.join(REPORTS, "cincinnati_oh_shadow_reconciliation_001.json"))
    fc = J(os.path.join(REPORTS, "cincinnati_oh_firecrawl_pass_001.json"))
    recensus = J(os.path.join(REPORTS, "cincinnati_oh_recensus_reconciliation_001.json"))
    inv = J(os.path.join(REPORTS, "cincinnati_application_inventory_016.json"))
    p14 = shadow["phase_14_clean_pending_inventory"]

    held_identity = [h for h in p14["held"] if h.get("class") == "IDENTITY_AMBIGUITY"]
    mismatches = [r for r in fc["rows"] if r["firecrawl_class"] == "FIRECRAWL_MISMATCH"]
    blocked = [r for r in fc["rows"] if r["firecrawl_class"] == "FIRECRAWL_BLOCKED"]
    leads = [r for r in recensus["rows"]
             if r["classification"] == "IDENTITY_REVIEW_REQUIRED"]
    founder_exceptions = [h for h in p14["held"]
                          if h.get("class") == "FOUNDER_EXCEPTION"]
    no_action = [h for h in p14["held"] if h.get("class") == "NO_AUTHORITY_ACTION"]

    groups = OrderedDict()

    groups["A -- identity / alias / successor / same-campus"] = [
        item(id="A1",
             current_identity="comfort suites mason near kings island "
                              "(partition: AWAITING_IDENTITY_RESOLUTION)",
             evidence="This order's Firecrawl capture confirmed the page identity on "
                      "name, postal 45040 and the canonical path oh470, and read a "
                      "property-specific refusal ('Pets Allowed: No. Only service "
                      "animals are permitted, free of charge'), graded "
                      "PUBLICATION_GRADE_CONFIRMED with a distinct document hash. "
                      "The census, not the page, is what is unsettled.",
             proposed_action="Rule the identity resolved on the first-party page's own "
                             "signals, then admit the no-pets row in a later "
                             "application order.",
             recommendation="RESOLVE THE IDENTITY, then admit. The evidence is already "
                            "bought and bound; what is missing is a ruling, not a fetch.",
             census_effect="none -- the row already exists; only its identity_state moves",
             authority_effect="+1 verified_no_pets when applied (60 -> 61 in the shadow)",
             routing_effect="none; the route already resolves to this property",
             reversibility="fully reversible: the ruling is a state change on one census "
                           "row and the evidence is preserved either way",
             blocks_promotion="NO",
             rows=held_identity),
        item(id="A2",
             current_identity="quality inn and suites cvg airport; "
                              "quality inn mason near kings island",
             evidence="Firecrawl reached both property pages and both were declined "
                      "IDENTITY_MISMATCH on STREET ONLY. Name, postal code and "
                      "canonical property path all agreed. The disagreement is our "
                      "census address being incomplete or abbreviated: the page says "
                      "'1805 Airport Exchange Boulevard' where the census says '1805 "
                      "Airport Exchange', and '5589 Kings Mills Road, Bldg A' where "
                      "the census says '5589 Kings Mills Rd'.",
             proposed_action="Complete the two census addresses from the first-party "
                             "pages, then re-run these two rows through the same lane.",
             recommendation="REPAIR THE CENSUS ADDRESSES. Do NOT relax the street "
                            "comparison: the gate behaved correctly, and a reading "
                            "rule widened during the review it feeds is how a wrong "
                            "building gets published.",
             census_effect="none -- two address fields are completed, no identity moves",
             authority_effect="none until the rows are re-read and applied",
             routing_effect="none; both routes already reach the right page",
             reversibility="fully reversible; the prior address strings are in git",
             blocks_promotion="NO",
             rows=[OrderedDict((("identity_key", r["identity_key"]),
                                ("expected_street", r["expected_street"]),
                                ("street_on_page", (r["identity_assessment"] or {})
                                 .get("signals", {}).get("address_on_page")),
                                ("postal_agrees", True),
                                ("document_sha256", r["page_sha256"])))
                   for r in mismatches]),
        item(id="A3",
             current_identity="%d OpenStreetMap candidates the census does not explain"
                              % len(leads),
             evidence="A free Overpass recensus (38 requests, no rate limits, $0) "
                      "returned 201 lodging candidates. 63 are explained by the census "
                      "exactly or by a distinctive-token alias, 110 are bare chain "
                      "instances that no coordinate can promote to an identity, and "
                      "these %d are named, addressed, and match no census identity on "
                      "any distinctive token." % len(leads),
             proposed_action="Review as census LEADS. Do not admit any of them on OSM "
                             "evidence alone.",
             recommendation="REVIEW LATER, as optional coverage expansion. This order "
                            "declares TRUE_MISSING_IDENTITY = 0 because OSM cannot "
                            "establish one: a name and a coordinate is a lead.",
             census_effect="0 today; unknown, and bounded above by %d, after review"
                           % len(leads),
             authority_effect="none",
             routing_effect="none",
             reversibility="n/a -- nothing is applied",
             blocks_promotion="NO",
             rows=[OrderedDict((("name", r["name"]), ("address", r["address_line"]),
                                ("postal_code", r["postal_code"]),
                                ("cell_id", r["cell_id"]), ("why", r["why"])))
                  for r in leads]),
    ]

    groups["B -- geography"] = [
        item(id="B1",
             current_identity="none",
             evidence="This order recomputed no corridor and moved no identity between "
                      "corridors. Every recensus candidate was tested against the "
                      "market's own cells and bounding box; none fell outside.",
             proposed_action="none",
             recommendation="NO ACTION. No ZIP is widened and no explicit assignment "
                            "is proposed.",
             census_effect="none", authority_effect="none", routing_effect="none",
             reversibility="n/a", blocks_promotion="NO", rows=[]),
    ]

    groups["C -- closure / conversion / non-lodging"] = [
        item(id="C1",
             current_identity="none newly found",
             evidence="No candidate matched the market's census quarantine, and no "
                      "owned artifact reported a closure this order did not already "
                      "hold. The 6 OUT_OF_CURRENT_CATEGORY rows are settled and "
                      "unchanged.",
             proposed_action="none",
             recommendation="NO ACTION.",
             census_effect="none", authority_effect="none", routing_effect="none",
             reversibility="n/a", blocks_promotion="NO", rows=[]),
    ]

    groups["D -- policy ambiguity / reader exception"] = [
        item(id="D1",
             current_identity="%d Hilton and Marriott rows Cincinnati already PAID for "
                              "and has never applied" % len(founder_exceptions),
             evidence="Order 016's inventory carries them with named open questions, "
                      "reproduced verbatim in this packet's open_questions block: a "
                      "'Deposit Yes. $X Non-refundable Fee' label that names two "
                      "different charges on seven rows from one template; a Homewood "
                      "tier gap over nights 2-4 that siblings disagree about; a Tru "
                      "Sharonville '*No Cats' where siblings say 'dog or cat'; a Tru "
                      "Monroe 'Pet fee is TAXABLE' the schema has no field for.",
             proposed_action="Rule each question once, as a class, then apply.",
             recommendation="RULE BEFORE APPLYING. Each is a price or a species the "
                            "site would publish wrongly, and the evidence is already "
                            "bought -- ruling costs nothing and re-fetching buys "
                            "nothing new.",
             census_effect="none",
             authority_effect="up to +%d rows when ruled and applied"
                              % len(founder_exceptions),
             routing_effect="none",
             reversibility="fully reversible until applied",
             blocks_promotion="NO -- these sit OUTSIDE the clean inventory by design",
             rows=founder_exceptions),
        item(id="D2",
             current_identity="%d rows with no authority action available"
                              % len(no_action),
             evidence="The Cincinnatian returned a complete page that publishes no pet "
                      "policy, and Courtyard Hamilton likewise. That is the hotel's "
                      "answer, not the lane's failure.",
             proposed_action="Record as SOURCE_SILENT and leave unresolved.",
             recommendation="NO ACTION. Silence is not a refusal and must never be "
                            "published as one.",
             census_effect="none", authority_effect="none", routing_effect="none",
             reversibility="n/a", blocks_promotion="NO", rows=no_action),
    ]

    groups["E -- evidence conflict"] = [
        item(id="E1",
             current_identity="none",
             evidence="Phase 13 audited every live Cincinnati record against every "
                      "owned verdict in this lineage: 118 live records are "
                      "corroborated and NOT ONE is contradicted. There is no wrong "
                      "live pet-friendly row and no wrong live no-pets row.",
             proposed_action="none",
             recommendation="NO ACTION.",
             census_effect="none", authority_effect="none", routing_effect="none",
             reversibility="n/a", blocks_promotion="NO", rows=[]),
    ]

    # ---------------------------- Phase 16, priced ----------------------------
    balance = args.brightdata_balance_usd
    qualified = args.brightdata_qualified_rows
    expected = qualified * ATTEMPTS_PER_ROW_EXPECTED * BRIGHTDATA_USD_PER_ATTEMPT
    ceiling = qualified * ATTEMPTS_PER_ROW_CEILING * BRIGHTDATA_USD_PER_ATTEMPT
    fundable = max(0.0, balance - OPERATIONAL_FLOOR_USD)
    rows_fundable = int(fundable // (ATTEMPTS_PER_ROW_EXPECTED * BRIGHTDATA_USD_PER_ATTEMPT))

    paid_readiness = OrderedDict((
        ("brightdata", OrderedDict((
            ("qualified_rows", qualified),
            ("measured_usd_per_attempt", BRIGHTDATA_USD_PER_ATTEMPT),
            ("measured_by", "PTF-CINCINNATI-MARRIOTT-SCALE-BATCH-016 settled rate; "
                            "the higher of two disagreeing meters"),
            ("expected_attempts", round(qualified * ATTEMPTS_PER_ROW_EXPECTED)),
            ("expected_cost_usd", round(expected, 2)),
            ("hard_cap_usd", round(ceiling, 2)),
            ("live_balance_usd", balance),
            ("operational_floor_usd", OPERATIONAL_FLOOR_USD),
            ("rows_the_balance_can_fund", rows_fundable),
            ("balance_sufficient_for_all", ceiling <= fundable),
            ("constraint", "the balance funds %d of %d rows; the next batch is "
                           "balance-limited unless the account is topped up"
                           % (rows_fundable, qualified)),
        ))),
        ("firecrawl", OrderedDict((
            ("executed_this_order", fc["attempted_rows"]),
            ("credits_before", fc["credits"]["before"]),
            ("credits_after", fc["credits"]["after"]),
            ("credits_delta", fc["credits"]["delta"]),
            ("usd", 0.0),
            ("remaining_candidates", 0),
            ("note", "the cohort the ladder named is exhausted; two Choice origins "
                     "returned SCRAPE_ALL_ENGINES_FAILED and are a measured limit of "
                     "this lane on those origins, not a retry"),
        ))),
        ("places_paid_discovery", OrderedDict((
            ("qualified_rows", 0),
            ("why", "the cross-run discovery ledger records ZERO Cincinnati paid "
                    "discovery attempts, and no row in this order needed one: every "
                    "unresolved row already carries a route or is held on identity"),
            ("expected_cost_usd", 0.0),
        ))),
        ("never_duplicate_a_prior_paid_attempt", OrderedDict((
            ("cincinnati_attempts_in_ledger", 39),
            ("distinct_identities_already_paid", 30),
            ("excluded_from_any_new_batch", True),
        ))),
    ))

    return OrderedDict((
        ("schema", SCHEMA),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("authority_mutation", "NONE"),
        ("usd_spent", 0.0),
        ("groups", groups),
        ("open_questions_carried_forward", inv.get("open_questions", {})),
        ("phase_16_paid_readiness", paid_readiness),
        ("phase_18_promotion_readiness", OrderedDict((
            ("PROMOTION_READY", "YES"),
            ("what_that_means", "the clean inventory this order assembled can be "
                                "applied by a later application order without any "
                                "founder ruling first. It is NOT a deployment "
                                "authorization and this order deployed nothing."),
            ("required_before_promotion", []),
            ("why_nothing_is_required", [
                "no unexplained wrong live authority: Phase 13 found 0 contradictions "
                "across 118 corroborated live records",
                "every promoted row is identity-bound: 23 rows, 23 distinct document "
                "hashes, each with a contiguous quote and a capture timestamp",
                "no duplicate premises: every clean row is a distinct census identity "
                "in AWAITING_POLICY_OBSERVATION",
                "geography is deterministic: no corridor moved and no ZIP was widened",
                "founder holds sit OUTSIDE the clean inventory by construction",
                "release changes are known: the contract's counts move with the "
                "partition and the pin, and nothing else",
            ]),
            ("optional_coverage_expansion", [
                "A1 -- rule one identity, gain 1 verified-no-pets row, $0",
                "A2 -- repair two census addresses, re-read 2 Choice rows, $0",
                "A3 -- review %d OSM leads, $0" % len(leads),
                "D1 -- rule the Hilton fee/deposit class, gain up to %d rows already "
                "paid for, $0" % len(founder_exceptions),
                "Bright Data batch -- %d Marriott/Choice rows, $%.2f expected, "
                "balance-limited to %d rows today"
                % (qualified, expected, rows_fundable),
            ]),
        ))),
    ))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--brightdata-balance-usd", type=float, required=True,
                    help="a LIVE balance read; never a remembered number")
    ap.add_argument("--brightdata-qualified-rows", type=int, required=True)
    ap.add_argument("--out", default=os.path.join(
        REPORTS, "cincinnati_oh_founder_packet_001.json"))
    args = ap.parse_args(argv)
    rep = build(args)
    with io.open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(rep, indent=1, ensure_ascii=False, default=str) + "\n")
    print("written", os.path.relpath(args.out, _DASH))
    for name, items in rep["groups"].items():
        rows = sum(len(i.get("rows") or []) for i in items)
        print("  %-52s %d ruling(s), %d row(s)" % (name, len(items), rows))
    print("PROMOTION_READY:", rep["phase_18_promotion_readiness"]["PROMOTION_READY"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
