"""PTF-CINCINNATI-PARALLEL-REVALIDATION-002 -- Phases 15, 16 and 18.

One grouped founder packet, the paid-readiness read, and the promotion call.

Groups A-F are the standing vocabulary. Every item names the evidence, the
recommendation, what it moves, whether it is reversible, and whether it blocks
promotion. No founder ruling is invented here: an item is a question put to a
person, and until that person answers it, the row it concerns stays outside
the clean inventory.

Phase 16 READS the shared ledgers and mutates nothing.
"""
from __future__ import annotations

import json
import os
from collections import Counter, OrderedDict
from datetime import datetime, timezone

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
OUT = os.path.join(REPORTS, "cincinnati_oh_founder_packet_002.json")

WORK_ORDER = "PTF-CINCINNATI-PARALLEL-REVALIDATION-002"
MARKET_ID = "cincinnati-oh"


def load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def item(ident, subject, evidence, recommendation, census, authority, routing,
         reversible, blocker, **extra):
    row = OrderedDict([
        ("id", ident),
        ("subject", subject),
        ("evidence", evidence),
        ("recommendation", recommendation),
        ("census_effect", census),
        ("authority_effect", authority),
        ("routing_effect", routing),
        ("reversibility", reversible),
        ("promotion_blocker", blocker),
    ])
    row.update(extra)
    return row


def main():
    attended = load(os.path.join(REPORTS, "cincinnati_oh_attended_pass_002.json"))
    shadow = load(os.path.join(REPORTS, "cincinnati_oh_shadow_reconciliation_002.json"))
    packet1 = load(os.path.join(REPORTS, "cincinnati_oh_founder_packet_001.json"))
    recensus = load(os.path.join(REPORTS, "cincinnati_oh_recensus_reconciliation_001.json"))
    competitor = load(os.path.join(REPORTS, "cincinnati_oh_competitor_census_challenge_002.json"))
    paid = load(os.path.join(PKG, "ptf_paid_attempt_ledger_001.json"))
    discovery = load(os.path.join(PKG, "ptf_discovery_attempt_ledger_001.json"))

    held = {r["canonical_name"] or "UNBOUND": r for r in shadow["phase_14_clean_pending_inventory"]["held"]}
    by_verdict = Counter(r["verdict"] for r in attended["rows"])

    groups = OrderedDict()

    groups["A -- identity / alias / successor / same-campus"] = [
        item("A1",
             "Comfort Suites Mason near Kings Island and Quality Inn Mason near Kings Island -- two Choice "
             "identities sharing postal 45040, and 001 raised both as open identity questions (its A1 and A2)",
             "This order read both first-party Choice pages in an attended session and both refuse pets in "
             "the same words: 'No Pets Allowed Only service animals are permitted, free of charge.' The "
             "Comfort Suites page declares its own street, 5457 Kings Center Drive, Mason OH 45040; the "
             "census row for that identity carries NO address at all. The Quality Inn page declared no "
             "street; the census row for it says 5589 Kings Mills Rd. So the evidence that would separate "
             "these two rows exists on one page and is missing from the other, and postal 45040 is shared.",
             "ADMIT THE ADDRESS, THEN THE POLICY. Write 5457 Kings Center Drive onto the Comfort Suites "
             "census row from its own page, which settles that identity; then re-read the Quality Inn page "
             "for its street before admitting it. Both refusals are already captured with a document hash "
             "and can be applied the moment the addresses separate the rows.",
             "no row added or removed; one census row gains the address it never had",
             "two VERIFIED_NO_PETS exclusions become admissible once the identities separate",
             "none -- both routes already resolve to the correct brand pages",
             "fully reversible: an address correction and two exclusions, each removable",
             "NO -- these two sit outside the clean inventory by construction, so promotion can proceed without them",
             carries_document_hash=True,
             supersedes="001 founder packet items A1 and A2, which asked the same question with less evidence"),
        item("A2",
             "The Well House Hotel, Hamilton OH -- routed to hilton.com/en/hotels/lukmaup-the-well-house-hamilton/",
             "The page served an operative Hilton policy record: pets allowed, $50.00 non-refundable fee, "
             "40 lbs maximum. It declared no address of its own in any structured field, so the only thing "
             "tying it to the census row at 10 S Monument Ave, Hamilton 45011 is the committed route itself. "
             "The property code prefix is LUK, which is Louisville, not CVG.",
             "CONFIRM THE IDENTITY on the property's own address or phone before admitting the policy. A "
             "route is a claim about identity, not a proof of one, and a Louisville code prefix on a "
             "Hamilton hotel is exactly the kind of thing worth one look.",
             "none",
             "one pet-friendly publication waits on the ruling",
             "none if confirmed; a re-route if not",
             "fully reversible",
             "NO"),
        item("A3",
             "DoubleTree by Hilton Lawrenceburg -- the committed route is marked ROUTING_RETIRED, and it works",
             "The committed route table carries cvgladt-doubletree-lawrenceburg with status ROUTING_RETIRED. "
             "This order fetched that exact URL in an attended session: HTTP 200, 295,650 bytes, and Hilton's "
             "own structured policy field reads 'Service animals only'. The brand still publishes the page. "
             "The page declared no address, and the census row for DoubleTree by Hilton Lawrenceburg "
             "(51 Walnut Street, Lawrenceburg IN 47025) carries no official_url at all.",
             "REVIEW THE RETIREMENT. Either the retirement was wrong and the route should be restored to the "
             "census row, or the retirement was right for a reason this order cannot see. Confirm on the "
             "page's address before restoring anything.",
             "none",
             "a verified-no-pets exclusion becomes available if the route is restored",
             "one retired route may return to service",
             "fully reversible -- retirement is a status, not a deletion",
             "NO"),
        item("A4",
             "28 OpenStreetMap candidates the census does not explain (carried forward from 001)",
             "001's free recensus read 201 OSM lodging candidates over 38 Overpass requests: 40 EXACT_EXISTING, "
             "23 ALIAS_OF_EXISTING, 110 NAME_ONLY_UNRESOLVED and 28 named-and-addressed review leads. "
             "TRUE_MISSING_IDENTITY was declared 0 and stays 0. This order's competitor pass found 0 "
             "TRUE_MISSING in its own sample and bounded the whole BringFido Cincinnati hotel directory at "
             "36 rows, which is smaller than the leads already in hand.",
             "RULE THE 28 ONE AT A TIME, or defer them. They are a coverage-expansion question, not a "
             "correctness question, and nothing in the current authority depends on them.",
             "up to 28 admissions if every lead survives review, which is unlikely",
             "none until an identity is admitted",
             "none until an identity is admitted",
             "fully reversible",
             "NO",
             carried_from="PTF-CINCINNATI-HARDENED-REVALIDATION-001 item A3"),
    ]

    groups["A -- identity / alias / successor / same-campus"].append(
        item("A5",
             "18 Cincinnati-area brand properties the census does not carry, found in the brands' own "
             "published inventories",
             "This order read Marriott's, Hilton's, Best Western's and Sonesta's official sitemaps in "
             "full: 28,779 published US properties over 564 free first-party requests, $0. Two tests had "
             "to pass before a row counted as a lead -- the slug had to name a WHOLE market city, and the "
             "brand's own property code had to carry a market prefix this market already owns (Marriott "
             "cvg/mwd, Hilton cvg/lku/luk/mwo/oxf/sgo, read back off the routes this same run matched, "
             "never invented). 5 come back TRUE_MISSING_BRAND_IDENTITY: Fairfield Inn & Suites Cincinnati "
             "Oakley (cvgfn), Hampton Suites Williamstown Ark Encounter (cvgarhx), Home2 Suites "
             "Lawrenceburg/Greendale (cvggrht), Spark Walton (cvguspe) and The Hotel Rambler Montgomery "
             "(cvgqkup). 13 more are IDENTITY_REVIEW_REQUIRED because a census identity is a close name "
             "match. The first matcher this order wrote reported 2,708 missing hotels; every sample was a "
             "Marriott in Atlanta or Austin matching on the word 'fairfield', which is a Marriott BRAND "
             "and not a city. It was tightened before any number was reported.",
             "RULE THEM ONE AT A TIME as census admissions in an identity order. Neither the OSM recensus "
             "nor the competitor directory found these five; the brand did.",
             "up to 18 admissions if every lead survives review",
             "none until an identity is admitted -- a verified new hotel is a census admission, never a "
             "clean pending row",
             "each admission would arrive with a first-party route already in hand",
             "fully reversible",
             "NO",
             brands_whose_inventory_is_closed=(
                 "IHG, Choice, Hyatt, Red Roof and Motel 6 refuse their own published sitemap to a plain "
                 "client, so this lane is SILENT about them rather than clean. Wyndham's opened on a later "
                 "probe having refused an earlier one: the wall is not stable, and a refusal is a "
                 "measurement, never a permanent fact.")))

    groups["B -- geography"] = [
        item("B1", "none", "No corridor moved, no postal code was widened and no boundary was reopened. "
             "The committed Cincinnati/Dayton boundary review still owns the Middletown, Monroe, Lebanon "
             "and northern Butler/Warren question, and this order deliberately excluded 'Dayton' from its "
             "own metro token vocabulary so no lead could be matched into the neighbouring market.",
             "nothing to decide", "none", "none", "none", "n/a", "NO"),
    ]

    groups["C -- closure / conversion / non-lodging"] = [
        item("C1",
             "Two committed Cincinnati routes now resolve to sites that are not hotels at all",
             "REST (333 e 8th st., Cincinnati 45202) is routed to iresteasy.com, which now serves unrelated "
             "Japanese-language content. The Glendalia (11 Village Square, Glendale 45246) is routed to "
             "theglendalia.com, which now serves an unrelated online-gambling site. Both returned HTTP 200 "
             "with a document hash recorded. 001's static pass saw these as TRANSPORT_FAILED and "
             "IDENTITY_NOT_CONFIRMED_STATIC; the attended pass explains why -- the domains lapsed and were "
             "repurposed.",
             "WITHDRAW BOTH ROUTES and send both identities back to routing. Do NOT infer closure of the "
             "business: a lapsed domain says the URL is dead, never that the hotel is. Both rows are already "
             "unresolved, so nothing wrong is live.",
             "none -- neither row is retired, and a retirement would MOVE the row, never delete it",
             "none -- both are unresolved today",
             "two routes withdrawn; two identities return to AWAITING_OFFICIAL_URL",
             "fully reversible",
             "NO"),
        item("C2",
             "SureStay Hotel by Best Western Florence -- the property code itself is dead",
             "Best Western publishes 3,882 US properties in its own sitemap and property code 55078 is not "
             "among them. The committed route therefore cannot resolve to a property page and does not.",
             "DO NOT INFER CLOSURE. A retired property code means the brand stopped publishing that code, "
             "which can mean a rebrand, a franchise exit or a closure, and the inventory does not say which. "
             "Re-route from the brand's current Florence KY inventory and let the page say what happened.",
             "none -- no census row moves on a dead code alone",
             "none -- the row is unresolved today",
             "one route to replace",
             "fully reversible",
             "NO"),
    ]

    groups["D -- policy ambiguity / reader exception"] = [
        item("D1",
             "Holiday Inn Express Fairfield states three different pet charges on one page",
             "The amenity chip says 'Pet-friendly (50 USD / stay)'. The policy prose on the same document "
             "says '50 dollar pet fee Per pet' and, one clause later, 'Pet fee per night: 50 USD'. Per stay, "
             "per pet and per night are three different charges and the page asserts all three. Everything "
             "else is unambiguous: no weight limit, 2 pets, dogs and cats only.",
             "PUBLISH THE POLICY WITHOUT A FEE BASIS, or hold the row. Picking one of the three would "
             "publish a price the source does not support. This row is held out of the clean inventory.",
             "none", "one pet-friendly publication waits on the ruling", "none", "fully reversible", "NO",
             carries_document_hash=True),
        item("D2",
             "Homewood Suites Cincinnati Midtown leaves nights 2 to 4 unpriced (carried from 001, re-confirmed here)",
             "Hilton's own structured field reads '$75.00(1-nights), $125.00(5+nights) 2 pets Max: dog/cat "
             "only'. Nights 2 through 4 are unstated. 001 raised this and noted the siblings cannot supply "
             "the missing tier because they disagree with each other: four use 1-4/5+ and Sharonville uses "
             "1-3/4-7. This order re-read the page and the gap is still there, in the same words.",
             "PUBLISH THE TWO STATED TIERS AND WITHHOLD THE MIDDLE, or hold the row. Borrowing a sibling's "
             "tier structure would invent a price.",
             "none", "one pet-friendly publication is affected", "none", "fully reversible", "NO",
             carried_from="PTF-CINCINNATI-HARDENED-REVALIDATION-001 open question homewood_tier_gap"),
        item("D3",
             "Three Hilton rows carry facts the schema has nowhere to put",
             "Tru by Hilton Monroe: '$75 (1-4n) $150(5+n) 2pets Max, dog/cat only. Pet fee is TAXABLE.' "
             "Tru by Hilton Sharonville: 'Non-Refundable Fee: $75/1-3nts, $125/4-7nts. 2 Pets Max, *No Cats. "
             "Fee Exempt for ADA Service Animals.' Every publication-grade Hilton row also carries the "
             "template label 'Pets allowed Yes Deposit' alongside a structured field that says the charge is "
             "NOT refundable -- a deposit and a non-refundable fee are two different things and the page "
             "shows both.",
             "RULE ON EACH. Taxability, a species exclusion that contradicts the brand template, and the "
             "deposit-versus-fee label are three separate schema questions. The rows themselves are clean "
             "and are IN the pending inventory; what needs a ruling is how much of each sentence survives "
             "into a published fact.",
             "none", "affects how three pet-friendly rows render, not whether they publish", "none",
             "fully reversible", "NO",
             carried_from="PTF-CINCINNATI-HARDENED-REVALIDATION-001 open questions fee_or_deposit, "
                          "sharonville_species, monroe_taxable"),
        item("D4",
             "Hyatt Regency Cincinnati says nothing about pets",
             "The hotel-info page served and bound to the identity on its own address (151 West Fifth Street, "
             "45202) in both the served markup and the attended render, and carries no pet sentence at all.",
             "LEAVE IT UNRESOLVED. Silence is an absence of observation and never a refusal. No ruling is "
             "needed and none should be made.",
             "none", "none", "none", "n/a", "NO"),
    ]

    groups["E -- evidence conflict"] = [
        item("E1",
             "Studio 6 Extended Stay Fairfield names two different streets for itself and offers only an "
             "amenity chip for its pet policy",
             "The page header reads 'Seward Road, Fairfield', which agrees with the census row at 9651 Seward "
             "Rd. Its own About prose reads 'Located at 3010 Lakeview Dr'. Its only pet language is an "
             "amenity card ('Pet-Friendly Accommodation / Pets welcome throughout your stay') and a "
             "site-wide footer link ('Pets Stay Free Details'). Neither is this property stating a policy.",
             "HOLD. The identity binds on the header, which agrees with Atlas, but a page that contradicts "
             "itself on its own address is not a page to publish a fee from -- and there is no fee here to "
             "publish, only a chip.",
             "none", "none -- the row stays unresolved", "none", "fully reversible", "NO"),
        item("E2",
             "SureStay Hotel by Best Western Florence -- the property URL is not a property page",
             "The committed route "
             "bestwestern.com/en_US/book/hotels-in-florence/surestay-by-best-western-florence/"
             "propertyCode.55078.html redirects to a Best Western hotel-search results page. The only pet "
             "language there is a 'Pet Friendly' search facet on a result card. 001 classified this "
             "UNEXPECTED_PAGE from a static client; the attended session reproduces it exactly.",
             "REPAIR THE ROUTE. This order then read Best Western's own published inventory in full -- 3,882 "
             "US properties -- and property code 55078 is NOT in it. That is why the URL falls through to a "
             "search page: the code is DEAD, not merely mis-routed. Re-route this identity from the brand's "
             "current Florence KY inventory. Do not read policy off a search page.",
             "none", "none -- the row stays unresolved", "one route to replace, not repair",
             "fully reversible", "NO",
             mechanically_answered_by="the Phase 7 brand inventory audit, classification DEAD_PROPERTY_CODE"),
        item("E3",
             "Three free route repairs the brands' own inventories offer, and two retired Best Western "
             "routes the brand still publishes",
             "ROUTE_REPAIR_AVAILABLE: Home2 Suites by Hilton Springdale Cincinnati -> "
             "hilton.com/en/hotels/cvgspht-home2-suites-springdale-cincinnati/ ; SpringHill Suites by "
             "Marriott Cincinnati Mason -> marriott.com/en-us/hotels/cvgms-springhill-suites-... ; Americas "
             "Best Value Inn & Suites Williamstown -> a Sonesta route. The first two are census rows sitting "
             "in AWAITING_IDENTITY_RESOLUTION with no official URL at all, and the brand publishes one for "
             "each. REBRAND_ROUTE: the committed routes for BEST WESTERN PLUS Hannaford Inn & Suites and "
             "Best Western Premier Mariemont Inn are retired, and Best Western still publishes both pages.",
             "BIND THE THREE REPAIRS on the page's own address, then re-read each for policy; review the two "
             "retirements the same way as A3. Every one of these came free from an inventory the brand "
             "publishes, not from a purchase.",
             "none", "up to five rows become routable and then readable",
             "three routes gained, two retirements reviewed", "fully reversible", "NO"),
        item("E4",
             "The Cincinnati routing shard does not describe most of the market's live routes",
             "Of the 99 live pet-friendly identities whose committed URL this order matched against the "
             "brand's own inventory as EXACT_ACTIVE_ROUTE: 47 have NO row at all in "
             "markets/authority/cincinnati-oh/identity_routing.json, 43 have a row that carries an EMPTY "
             "property_code, and only 9 agree with the brand's published code. The codes are not missing "
             "from the world -- they are sitting in the URLs the shard already stores (cvgbc, cvgci, cvgpl "
             "and so on) and in the brand inventories this order read.",
             "BACKFILL THE SHARD from the brand inventory in the serialized order. This is bookkeeping "
             "hygiene, not a correctness defect: no live route is wrong, and the audit proved that "
             "separately. But a routing table that cannot name a property code cannot detect a dead one.",
             "none", "none", "the shard gains rows and codes it should already have",
             "fully reversible", "NO"),
    ]

    groups["F -- cross-market collision"] = [
        item("F1",
             "Two Cincinnati properties carry Louisville Hilton property-code prefixes",
             "Tru by Hilton Sharonville routes to lkushru-tru-sharonville-cincinnati and The Well House "
             "Hamilton routes to lukmaup-the-well-house-hamilton. Both prefixes are LKU/LKUS (Louisville), "
             "not CVG. Sharonville's page declared 11155 Dowlin Drive, Sharonville OH 45241, which matches "
             "the census exactly, so that one is a naming curiosity and not a collision. The Well House "
             "page declared no address at all, which is why it is also item A2.",
             "NO ACTION on Sharonville: a brand's internal code prefix is not a market boundary and the "
             "address settles it. Resolve The Well House under A2.",
             "none", "none", "none", "n/a", "NO"),
    ]

    cin_paid = [a for a in paid["attempts"] if a.get("market_id") == MARKET_ID]
    cin_disc = [a for a in discovery["attempts"] if a.get("market_id") == MARKET_ID]

    phase16 = OrderedDict([
        ("ledgers_read", ["ptf_paid_attempt_ledger_001.json", "ptf_discovery_attempt_ledger_001.json"]),
        ("ledgers_mutated", "NONE -- this order is parallel-safe and may not write a shared ledger"),
        ("cincinnati_paid_history", OrderedDict([
            ("attempts_recorded", len(cin_paid)),
            ("lanes", OrderedDict(sorted(Counter(a.get("lane") for a in cin_paid).items()))),
            ("usd_spent_all_time", round(sum(int(a.get("cost_usd_minor") or 0) for a in cin_paid) / 100.0, 2)),
            ("firecrawl_credits_in_ledger", sum(int(a.get("firecrawl_credits") or 0) for a in cin_paid)),
            ("outcomes", OrderedDict(sorted(Counter(a.get("outcome") for a in cin_paid).items()))),
            ("terminal_attempts", sum(1 for a in cin_paid if a.get("terminal"))),
            ("reusable_evidence", sum(1 for a in cin_paid if a.get("reusable_evidence"))),
        ])),
        ("cincinnati_paid_discovery_history", OrderedDict([
            ("attempts_recorded", len(cin_disc)),
            ("note", "Cincinnati has never bought a places lookup. There is no double-buy risk in that lane "
                     "and no cached answer to reuse either."),
        ])),
        ("ledger_gap_to_flag", "001's Firecrawl run (7 attempts, 5 plan credits, $0 USD) is recorded in that "
                               "order's own market report but does not appear as Cincinnati rows in the "
                               "shared paid-attempt ledger on this base. A later serialized order should "
                               "reconcile it. This order must not write that ledger."),
        ("firecrawl", OrderedDict([
            ("eligible_rows_this_order", 0),
            ("why", "the attended lane answered every routed row the ladder would have escalated, at $0 and "
                    "0 credits. Buying a credit for a page a browser already read is a double buy."),
            ("standing_cost_shape", "1 credit on a successful scrape, 0 when the origin refuses every "
                                    "engine. Cap on ATTEMPTS, never on a plan's arithmetic and never on the "
                                    "account balance."),
        ])),
        ("brightdata", OrderedDict([
            ("eligible_rows_this_order", 0),
            ("why", "same reason. Cincinnati has already spent $6.24 across 39 Bright Data browser attempts; "
                    "29 produced reusable terminal evidence. Nothing in the remaining cohort needs that lane."),
        ])),
        ("places_paid_discovery", OrderedDict([
            ("qualified_rows", 16),
            ("what_they_are", "the 16 identities still in AWAITING_OFFICIAL_URL, plus the two whose routes "
                              "this order found pointing at repurposed domains"),
            ("prior_attempts", 0),
            ("recommendation", "NOT NOW. Free routing has not been exhausted for these rows: the official "
                               "brand inventories this order read are the cheaper instrument and were only "
                               "partially applied. Buy discovery after the brand-inventory route repairs, "
                               "not before."),
        ])),
        ("usd_authorized_this_order", 0.0),
        ("usd_spent_this_order", 0.0),
    ])

    p14 = shadow["phase_14_clean_pending_inventory"]
    blockers = [i["id"] for group in groups.values() for i in group if i["promotion_blocker"] == "YES"]
    phase18 = OrderedDict([
        ("PROMOTION_READY", "YES" if not blockers else "NO"),
        ("what_that_means", "the clean inventory this order assembled can be applied by a later serialized "
                            "application order without any founder ruling first. It is NOT a deployment "
                            "authorization and this order deployed nothing."),
        ("required_before_promotion", [
            "integrate the then-current deployed canonical lineage into this branch FIRST. This branch is "
            "based on d06e2eb and predates the Indianapolis deployment lineage. Market-local evidence work "
            "is safe on it; promotion is not.",
        ]),
        ("why_nothing_else_is_required", [
            "no wrong live authority: every clean row sits in an unresolved partition state, so there is "
            "nothing live for it to contradict, and 001 already checked 118 live records against every "
            "owned verdict and found 0 contradictions",
            "every promoted row is identity-bound on something the PAGE declared about itself, not on the "
            "route that led there",
            "%d clean rows carry %d distinct document hashes" % (
                p14["clean_pet_friendly"] + p14["clean_verified_no_pets"], p14["distinct_document_hashes"]),
            "no duplicate premises: each identity appears at most once across both source orders",
            "no census admission is inside the clean inventory; every recensus and competitor lead is a "
            "question in group A, not a row",
            "founder holds sit OUTSIDE the clean inventory by construction",
        ]),
        ("optional_coverage_expansion", [
            "the 28 OSM review leads (A4)",
            "the 16 AWAITING_OFFICIAL_URL identities, routed against the official brand inventories rather "
            "than bought",
            "the two route repairs in C1 and the one in E2",
        ]),
        ("promotion_blockers_open", blockers),
    ])

    report = OrderedDict()
    report["schema"] = "ptf-founder-packet/1.1"
    report["work_order"] = WORK_ORDER
    report["market_id"] = MARKET_ID
    report["as_of"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    report["authority_mutation"] = "NONE"
    report["usd_spent"] = 0.0
    report["no_founder_ruling_is_invented_here"] = (
        "Every item is a question. Where 001 left a question open, this order says whether its new evidence "
        "answers it or only sharpens it, and never answers it on the founder's behalf.")
    report["groups"] = groups
    report["item_counts"] = OrderedDict((g, len(v)) for g, v in groups.items())
    report["attended_verdicts"] = OrderedDict(sorted(by_verdict.items()))
    report["items_carried_from_001"] = [i["id"] for group in groups.values() for i in group
                                        if i.get("carried_from") or i.get("supersedes")]
    report["001_group_counts"] = OrderedDict((g, len(v)) for g, v in packet1["groups"].items())
    report["recensus_true_missing"] = recensus["true_missing_identity"]
    report["competitor_true_missing"] = competitor["reconciliation"]["TRUE_MISSING_IDENTITY"]
    report["phase_16_paid_readiness"] = phase16
    report["phase_18_promotion_readiness"] = phase18

    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print("wrote", OUT)
    print(json.dumps(report["item_counts"], indent=2))
    print("PROMOTION_READY:", phase18["PROMOTION_READY"], "| open blockers:", blockers or "none")


if __name__ == "__main__":
    main()
