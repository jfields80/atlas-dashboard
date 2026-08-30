# -*- coding: utf-8 -*-
"""PTF-CINCINNATI-INDEPENDENT-FREE-PROBE-008 -- can independents be had free?

WHAT PHASE 1 FOUND, AND A CORRECTION
------------------------------------
PTF-CINCINNATI-FREE-LANE-APPLICATION-007's Phase 10 reported "24 rows suitable
for a zero-cost attended-Chrome probe". That was wrong, and it was my error:
the filter behind it took routed + unresolved and never asked whether the row
had already been captured. Twenty of the twenty-four had been, and seventeen of
those returned POLICY_NOT_FOUND. Only FOUR Independent/ESA rows in this market
have never been looked at.

Three of those four are served from choicehotels.com. Country Inn & Suites and
Radisson are Choice brands, so the routing shard's INDEPENDENT label is stale
for them and their pages sit on the locator PTF-CINCINNATI-FREE-LANE-SCALE-006
already closed. Probing only the fresh four would therefore measure the Choice
lane a second time and say almost nothing about independents.

SO THE COHORT IS TWO STRATA, MEASURED SEPARATELY
------------------------------------------------
  A  FRESH (4)     -- never captured. 3 Choice-platform + the renamed Studio 6.
  B  RE-EXAMINE (6) -- previously POLICY_NOT_FOUND on six distinct genuinely
                       independent domains, re-read with deliberate per-site
                       locator work rather than a throughput sweep.

Stratum B is a judgment call and it is flagged as one. The founder's question
is whether independents are capturable at $0, and every genuinely independent
domain in this market is in the previously-empty pool; Phase 3 of the order --
"Independent sites will not share one locator ... record which locator/surface
worked" -- only has meaning against sites where careful locator work has not
yet been done. A POLICY_NOT_FOUND is also not a successful capture: it is a
page that rendered and yielded nothing, which is exactly the case Cincinnati
precedent allows re-reading.

The two rates are never blended. Publishing one number over both would let a
re-read of known-empty pages drag down a fresh rate, or a fresh success flatter
the re-reads.

Nothing here writes authority, and no reader is generalised from one or two
examples -- this probe measures CAPTURABILITY, not reader design.
"""

from __future__ import annotations

import json
from collections import Counter, OrderedDict

from scripts.pettripfinder.cincinnati_free_brand_probe_005 import (
    OUTCOMES, PUBLICATION_GRADE, TRIAGES, load, render, wilson)
from scripts.pettripfinder.cincinnati_free_lane_scale_006 import (
    PARTITION, REPORTS, RESOLVED, ROUTING, _previously_captured)

WORK_ORDER = "PTF-CINCINNATI-INDEPENDENT-FREE-PROBE-008"
MARKET_ID = "cincinnati-oh"
OBSERVED_ON = "2026-08-30"
CAPTURE_METHOD = "attended_chrome_render"
COHORT_CAP = 10

FAMILIES = ("INDEPENDENT", "ESA")

COHORT = REPORTS / "cincinnati_probe008_cohort.json"
RESULTS = REPORTS / "cincinnati_probe008_results.json"
MEASUREMENT = REPORTS / "cincinnati_probe008_measurement.json"
REPRICE = REPORTS / "cincinnati_probe008_reprice.json"

PASS1 = REPORTS / "cincinnati_capture_pass1_001_results.json"
PASS3 = REPORTS / "cincinnati_capture_pass3_001_results.json"

#: Stratum B, chosen for maximum spread across domain, platform and hotel type
#: rather than for likelihood of success. Four Drury properties share one
#: domain; only one is admitted, because a cohort that took all four would be
#: measuring druryhotels.com and calling it "independents".
RE_EXAMINE = OrderedDict((
    ("drury inn and suites cincinnati northeast mason",
     "druryhotels.com -- a multi-property independent chain; four Cincinnati "
     "rows share this domain, so one page settles the shape for all four"),
    ("golden lamb",
     "goldenlamb.com -- a historic inn on a small bespoke site"),
    ("symphony hotel and restaurant",
     "symphonyhotel.com -- a boutique guesthouse, likely prose-only"),
    ("the summit hotel",
     "thesummithotel.com -- a full-service boutique with a modern CMS"),
    ("intown suites cincinnati north",
     "intownsuites.com -- an extended-stay chain, the shape closest to ESA"),
    ("wildwood inn",
     "wildwoodinnky.com -- a themed motel on an older hand-built site"),
))


def _prior_outcomes():
    out = {}
    for path in (PASS1, PASS3):
        if path.exists():
            for row in load(path)["rows"]:
                out[row["identity_key"]] = (path.name.split("_")[2], row)
    return out


def build_cohort():
    routes = {r["hotel_ref"]["identity_key"]: r for r in load(ROUTING)["routes"]}
    state = {i["identity_key"]: i["final_state"] for i in load(PARTITION)["items"]}
    captured = _previously_captured()
    priors = _prior_outcomes()

    audit = Counter()
    fresh, reexamine = [], []
    seen_keys, seen_urls = set(), set()

    for key, route in sorted(routes.items()):
        family = route.get("brand")
        if family not in FAMILIES:
            continue
        audit["routed_total"] += 1
        url = route.get("official_property_url") or ""
        if state.get(key) in RESOLVED:
            audit["suppressed_already_resolved"] += 1
            continue
        if route.get("status") != "ROUTING_CONFIRMED":
            audit["suppressed_route_not_confirmed"] += 1
            continue
        if not url.startswith("https://"):
            audit["suppressed_no_first_party_url"] += 1
            continue
        if key in seen_keys:
            audit["suppressed_duplicate_identity"] += 1
            continue
        if url in seen_urls:
            audit["suppressed_duplicate_canonical_url"] += 1
            continue

        row = OrderedDict((
            ("identity_key", key),
            ("canonical_name", route["hotel_ref"]["canonical_name"]),
            ("family", family),
            ("official_property_url", url),
            ("official_domain", route.get("official_domain", "")),
            ("city", route["identity_context"].get("city", "")),
            ("postal_code", route["identity_context"].get("postal_code", "")),
            ("address", route["identity_context"].get("address", "")),
            ("phone", route["identity_context"].get("phone", "")),
        ))
        if key not in captured:
            row["stratum"] = "A_FRESH"
            row["never_captured"] = True
            fresh.append(row)
            audit["admitted_fresh"] += 1
        elif key in RE_EXAMINE:
            source, prior = priors.get(key, ("", {}))
            row["stratum"] = "B_RE_EXAMINE"
            row["never_captured"] = False
            row["prior_outcome"] = prior.get("outcome", "")
            row["prior_pass"] = source
            row["chosen_because"] = RE_EXAMINE[key]
            reexamine.append(row)
            audit["admitted_re_examine"] += 1
        else:
            audit["suppressed_previously_captured"] += 1
        seen_keys.add(key)
        seen_urls.add(url)

    rows = fresh + reexamine
    if len(rows) > COHORT_CAP:
        raise RuntimeError("cohort exceeds the cap")
    missing = set(RE_EXAMINE) - {r["identity_key"] for r in reexamine}
    if missing:
        raise RuntimeError("re-examine rows not found: %s" % sorted(missing))

    return OrderedDict((
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("cap", COHORT_CAP),
        ("provider_calls", 0),
        ("paid_spend_usd", 0.0),
        ("correction",
         "PTF-CINCINNATI-FREE-LANE-APPLICATION-007 Phase 10 reported 24 rows "
         "suitable for a free probe. The filter behind that number took routed "
         "+ unresolved and never asked whether the row had already been "
         "captured. Twenty of the twenty-four had been, seventeen of them "
         "returning POLICY_NOT_FOUND. Only four have never been looked at."),
        ("audit", OrderedDict(sorted(audit.items()))),
        ("strata", OrderedDict((
            ("A_FRESH", OrderedDict((
                ("count", len(fresh)),
                ("what", "Never captured. Three are served from "
                         "choicehotels.com -- Country Inn & Suites and "
                         "Radisson are Choice brands, so the shard's "
                         "INDEPENDENT label is stale and these pages sit on "
                         "the locator SCALE-006 already closed. The fourth is "
                         "the Studio 6 identity renamed by APPLICATION-004, "
                         "whose policy that order deferred to the next clean "
                         "pass.")))),
            ("B_RE_EXAMINE", OrderedDict((
                ("count", len(reexamine)),
                ("what", "Previously POLICY_NOT_FOUND on six distinct "
                         "genuinely independent domains, re-read with "
                         "deliberate per-site locator work rather than a "
                         "throughput sweep."),
                ("judgment_call",
                 "The order admits rows 'not previously successfully "
                 "captured'. A POLICY_NOT_FOUND rendered a page and yielded "
                 "nothing, which is not a successful capture of a policy. "
                 "Every genuinely independent domain in this market is in "
                 "that pool, so a probe without this stratum would measure "
                 "the Choice lane again and say nothing about independents."))))))),
        ("rates_are_never_blended",
         "A rate over both strata would let re-reads of known-empty pages drag "
         "down a fresh rate, or a fresh success flatter the re-reads."),
        ("count", len(rows)),
        ("rows", rows),
    ))


def measure(rows):
    outcomes = Counter(r["outcome"] for r in rows)
    triage = Counter(r["triage"] for r in rows)
    n = len(rows)
    grade = sum(outcomes[o] for o in PUBLICATION_GRADE)
    point, lo, hi = wilson(grade, n)
    return OrderedDict((
        ("attempted", n),
        ("rendered", sum(1 for r in rows if r["page_rendered"])),
        ("identity_confirmed", sum(1 for r in rows if r["identity_confirmed"])),
        ("policy_surface_found",
         sum(1 for r in rows if r["policy_surface_found"])),
        ("publication_grade", grade),
        ("pet_friendly", outcomes["PUBLICATION_CANDIDATE"]),
        ("verified_no_pets", outcomes["VERIFIED_NO_PETS"]),
        ("policy_not_found", outcomes["POLICY_NOT_FOUND"]),
        ("access_blocked", outcomes["ACCESS_BLOCKED"]),
        ("routing_repair_required", outcomes["ROUTING_REPAIR_REQUIRED"]),
        ("identity_mismatch", outcomes["IDENTITY_MISMATCH"]),
        ("hold", outcomes["HOLD"]),
        ("founder_exception", triage["FOUNDER_EXCEPTION"]),
        ("clean_pet_friendly", triage["CLEAN_PET_FRIENDLY_CANDIDATE"]),
        ("clean_verified_no_pets", triage["CLEAN_VERIFIED_NO_PETS_CANDIDATE"]),
        ("publication_grade_point_rate", point),
        ("wilson_95_lower", lo),
        ("wilson_95_upper", hi),
    ))


def recommend_independents(stats, distinct_domains_with_yield):
    """One recommendation, and it refuses to over-generalise a clustered win.

    The order is explicit: if success is clustered on one or two site
    templates, MORE_FREE_PROBE_NEEDED beats FREE_LANE_SCALE. Independents share
    no platform, so a yield concentrated on a couple of domains is a fact about
    those domains.
    """
    n = stats["attempted"]
    if n == 0:
        return "MORE_FREE_PROBE_NEEDED", "no rows were drawn"
    if stats["access_blocked"] > n / 3.0:
        return "PAID_LANE_REQUIRED", (
            "attended Chrome was blocked on %d of %d rows, which is an access "
            "problem a locator cannot fix"
            % (stats["access_blocked"], n))
    if stats["identity_confirmed"] < n:
        return "MORE_FREE_PROBE_NEEDED", (
            "identity binding failed on %d of %d rows"
            % (n - stats["identity_confirmed"], n))
    if stats["publication_grade"] == 0:
        return "MORE_FREE_PROBE_NEEDED", (
            "every page rendered and none stated a pet policy; that is an "
            "absence of published policy, not an access failure, and no paid "
            "lane fixes it")
    if distinct_domains_with_yield < 3:
        return "MORE_FREE_PROBE_NEEDED", (
            "publication-grade yield is %d of %d but it is clustered on %d "
            "distinct domain(s); independents share no platform, so that is a "
            "fact about those sites rather than about the family"
            % (stats["publication_grade"], n, distinct_domains_with_yield))
    if stats["wilson_95_lower"] >= 0.5:
        return "FREE_LANE_SCALE", (
            "rendered %d/%d, identity %d/%d, publication-grade %d/%d across %d "
            "distinct domains (Wilson lower %.2f)"
            % (stats["rendered"], n, stats["identity_confirmed"], n,
               stats["publication_grade"], n, distinct_domains_with_yield,
               stats["wilson_95_lower"]))
    return "MORE_FREE_PROBE_NEEDED", (
        "publication-grade yield is %d of %d (Wilson lower %.2f), too thin to "
        "size a scale run" % (stats["publication_grade"], n,
                              stats["wilson_95_lower"]))


# ------------------------------------------------------------- Phase 8 reprice

BRIGHTDATA_USD_PER_ATTEMPT = 0.197

LANE_OF_FAMILY = {
    "MARRIOTT": "BRIGHT_DATA",
    "HILTON": "BRIGHT_DATA",
    "IHG": "ATTENDED_CHROME_FREE_CLOSED",
    "CHOICE": "ATTENDED_CHROME_FREE_CLOSED",
    "HYATT": "BLOCKED_BY_ADR",
    "INDEPENDENT": "FREE_LANE_PARTIAL",
    "ESA": "FREE_LANE_PARTIAL",
}


def build_reprice(rows):
    """What is left, and what this probe changed about how it is priced.

    Independents move from FREE_LANE_UNPROVEN to FREE_LANE_PARTIAL: the family
    is reachable free -- every page rendered and every identity bound -- but
    only a third of them publish a policy at all, and no paid lane fixes a
    hotel that has not written its terms down. That is the important
    distinction. An unproven lane might be bought; this one largely cannot be.
    """
    routes = load(ROUTING)["routes"]
    state = {i["identity_key"]: i["final_state"] for i in load(PARTITION)["items"]}
    routed = {r["hotel_ref"]["identity_key"] for r in routes}
    # Only the Independent/ESA rows. The three Choice-platform rows in this
    # probe are counted by the lane that actually produced them.
    own = [r for r in rows
           if r["platform"].startswith("INDEPENDENT")
           or r["platform"] == "MOTEL6_PLATFORM"]
    answered = {r["identity_key"] for r in own if r["policy_surface_found"]}
    silent = {r["identity_key"] for r in own
              if r["outcome"] == "POLICY_NOT_FOUND"}

    by_family, pending, empty = Counter(), Counter(), Counter()
    for route in routes:
        key = route["hotel_ref"]["identity_key"]
        if state.get(key) in RESOLVED:
            continue
        family = route.get("brand") or "UNKNOWN"
        by_family[family] += 1
        if key in answered:
            pending[family] += 1
        if key in silent:
            empty[family] += 1

    unrouted = sorted(k for k, v in state.items()
                      if v not in RESOLVED and k not in routed)
    by_state = Counter(state[k] for k in unrouted)

    lanes = OrderedDict()
    for family, n in sorted(by_family.items()):
        lane = LANE_OF_FAMILY.get(family, "FREE_LANE_UNPROVEN")
        row = lanes.setdefault(lane, OrderedDict((
            ("families", OrderedDict()), ("rows", 0),
            ("answered_pending_review", 0),
            ("observed_silent", 0))))
        row["families"][family] = n
        row["rows"] += n
        row["answered_pending_review"] += pending[family]
        row["observed_silent"] += empty[family]

    bd = lanes.get("BRIGHT_DATA", {}).get("rows", 0)
    independent_total = by_family.get("INDEPENDENT", 0) + by_family.get("ESA", 0)
    return OrderedDict((
        ("work_order", WORK_ORDER),
        ("basis", "the routing shard and partition at b0fa3e2; no authority "
                  "was applied by this order"),
        ("unresolved_total", sum(1 for v in state.values() if v not in RESOLVED)),
        ("unresolved_routed", sum(by_family.values())),
        ("unresolved_unrouted", len(unrouted)),
        ("unrouted_by_state", OrderedDict(sorted(by_state.items()))),
        ("by_family", OrderedDict(sorted(by_family.items()))),
        ("lanes", lanes),
        ("independent_and_esa", OrderedDict((
            ("total_unresolved_routed", independent_total),
            ("observed_by_this_probe", len(own)),
            ("observed_and_yielding", len(answered)),
            ("observed_silent", len(silent)),
            ("still_unobserved", independent_total - len(own)),
            ("what_changed",
             "The family moves from FREE_LANE_UNPROVEN to FREE_LANE_PARTIAL. "
             "Attended Chrome reached every page and bound every identity, so "
             "access is not the constraint. Roughly a third publish a policy "
             "at all. The rest are silent, and silence is not something a paid "
             "provider can buy -- the same fetch would return the same absent "
             "policy.")))),
        ("firecrawl", OrderedDict((
            ("rows", 0), ("usd", 0.0),
            ("why", "Nothing in current state produces a qualified need. IHG "
                    "and Choice are closed free; Marriott and Hilton are "
                    "unreachable to Firecrawl (PTF-FIRECRAWL-HARD-LANES-003); "
                    "and the independents' problem is unpublished policy, "
                    "which no provider fixes.")))),
        ("bright_data", OrderedDict((
            ("rows", bd), ("usd_per_attempt", BRIGHTDATA_USD_PER_ATTEMPT),
            ("projected_usd", round(bd * BRIGHTDATA_USD_PER_ATTEMPT, 2))))),
        ("spend_this_order_usd", 0.0),
        ("note", "An estimate, not an authorization. Nothing here spends."),
    ))
