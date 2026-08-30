# -*- coding: utf-8 -*-
"""PTF-CINCINNATI-INDEPENDENT-FREE-PROBE-009 -- the last independent pass.

A SECOND ARITHMETIC CORRECTION, SAME SHAPE AS THE FIRST
-------------------------------------------------------
PROBE-008 reported 17 rows still unobserved. There are 14. Its counter took the
24 labelled Independent/ESA rows and subtracted only the SEVEN it measured as
Independent/ESA, ignoring the three Choice-platform rows it also observed --
a remaining-count computed against a subset denominator. PROBE-008 itself
opened by correcting exactly that kind of slip in APPLICATION-007, which is why
this order rebuilds the cohort from current state rather than trusting the
number in the order.

WHAT THE 14 CONTAIN
-------------------
* one row on hilton.com -- The Well House Hotel is a Hilton property carrying a
  stale INDEPENDENT label. It is classified BRAND_CLASSIFICATION_STALE, kept
  out of the independent measurement, and NOT rewritten here;
* three more druryhotels.com rows. PROBE-008 settled that template: bare
  JSON-LD petsAllowed and no prose. They are observed rather than assumed, but
  one domain cannot contribute four times to a diversity count, so the domain
  is counted once;
* Great Wolf Lodge, which ruling #2 of APPLICATION-004 HELD pending "a
  property-specific prose statement or equivalently clear first-party policy
  surface". Looking for that surface is precisely what the founder asked for,
  so it is admitted;
* nine genuinely unobserved independent domains.

WHAT PROBE-008 TAUGHT THIS ONE TO DO DIFFERENTLY
------------------------------------------------
No shallow homepage sweep. Both of 008's successes were surfaces a sweep
misses: a ``<label>``-driven accordion that answers to neither aria-expanded
nor <details>, and a dedicated /about-us/hotel-policies page the routing URL
never mentions. So every site here gets a first-party surface sweep --
navigation links matching pet/policy/rules/FAQ/terms are followed before any
row is allowed to be called POLICY_NOT_FOUND.
"""

from __future__ import annotations

from collections import Counter, OrderedDict

from scripts.pettripfinder.cincinnati_free_brand_probe_005 import (
    OUTCOMES, PUBLICATION_GRADE, TRIAGES, load, render, wilson)
from scripts.pettripfinder.cincinnati_free_lane_scale_006 import (
    PARTITION, REPORTS, RESOLVED, ROUTING)
from scripts.pettripfinder.cincinnati_independent_probe_008 import (
    RESULTS as PROBE008)

WORK_ORDER = "PTF-CINCINNATI-INDEPENDENT-FREE-PROBE-009"
MARKET_ID = "cincinnati-oh"
OBSERVED_ON = "2026-08-30"
CAPTURE_METHOD = "attended_chrome_render"

COHORT = REPORTS / "cincinnati_probe009_cohort.json"
RESULTS = REPORTS / "cincinnati_probe009_results.json"
MEASUREMENT = REPORTS / "cincinnati_independent_lane_final.json"
PENDING = REPORTS / "cincinnati_free_lane_pending_application.json"
REPRICE = REPORTS / "cincinnati_probe009_reprice.json"

#: Domains that prove a row belongs to a known family whatever the shard says.
KNOWN_FAMILY_DOMAINS = OrderedDict((
    ("choicehotels.com", "CHOICE"),
    ("ihg.com", "IHG"),
    ("hilton.com", "HILTON"),
    ("marriott.com", "MARRIOTT"),
    ("hyatt.com", "HYATT"),
    ("motel6.com", "ESA"),
    ("wyndhamhotels.com", "WYNDHAM"),
    ("bestwestern.com", "BESTWESTERN"),
    ("extendedstayamerica.com", "ESA"),
))

OUTCOMES_009 = tuple(OUTCOMES) + ("BRAND_CLASSIFICATION_STALE",)


def observed_family(domain):
    for suffix, family in KNOWN_FAMILY_DOMAINS.items():
        if (domain or "").endswith(suffix):
            return family
    return ""


def build_cohort():
    routes = {r["hotel_ref"]["identity_key"]: r for r in load(ROUTING)["routes"]}
    state = {i["identity_key"]: i["final_state"] for i in load(PARTITION)["items"]}
    probe008 = {r["identity_key"] for r in load(PROBE008)["rows"]}

    audit = Counter()
    rows = []
    seen_keys, seen_urls = set(), set()

    for key, route in sorted(routes.items()):
        if route.get("brand") not in ("INDEPENDENT", "ESA"):
            continue
        audit["labelled_independent_or_esa"] += 1
        url = route.get("official_property_url") or ""
        domain = route.get("official_domain", "")
        if state.get(key) in RESOLVED:
            audit["suppressed_already_resolved"] += 1
            continue
        if key in probe008:
            audit["suppressed_observed_by_probe_008"] += 1
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
        seen_keys.add(key)
        seen_urls.add(url)
        audit["admitted"] += 1

        family = observed_family(domain)
        if family:
            audit["admitted_but_domain_shows_known_family"] += 1
        rows.append(OrderedDict((
            ("identity_key", key),
            ("canonical_name", route["hotel_ref"]["canonical_name"]),
            ("census_family", route.get("brand")),
            ("domain_implies_family", family),
            ("official_property_url", url),
            ("official_domain", domain),
            ("city", route["identity_context"].get("city", "")),
            ("postal_code", route["identity_context"].get("postal_code", "")),
            ("address", route["identity_context"].get("address", "")),
            ("phone", route["identity_context"].get("phone", "")),
        )))

    return OrderedDict((
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("provider_calls", 0),
        ("paid_spend_usd", 0.0),
        ("correction",
         "PROBE-008 reported 17 rows still unobserved. There are 14. Its "
         "counter subtracted only the seven rows it measured as "
         "Independent/ESA from the 24 labelled ones, ignoring the three "
         "Choice-platform rows it also observed -- a remaining-count computed "
         "against a subset denominator, which is the same shape of slip "
         "PROBE-008 itself corrected in APPLICATION-007."),
        ("audit", OrderedDict(sorted(audit.items()))),
        ("count", len(rows)),
        ("rows", rows),
    ))


# ------------------------------------------------------------------ measurement

def measure(rows):
    outcomes = Counter(r["outcome"] for r in rows)
    triage = Counter(r["triage"] for r in rows)
    n = len(rows)
    grade = sum(outcomes[o] for o in PUBLICATION_GRADE)
    point, lo, hi = wilson(grade, n)
    pf_point, pf_lo, pf_hi = wilson(outcomes["PUBLICATION_CANDIDATE"], n)
    np_point, np_lo, np_hi = wilson(outcomes["VERIFIED_NO_PETS"], n)
    return OrderedDict((
        ("n", n),
        ("rendered", sum(1 for r in rows if r["page_rendered"])),
        ("identity_confirmed", sum(1 for r in rows if r["identity_confirmed"])),
        ("usable_policy_surface",
         sum(1 for r in rows if r["policy_surface_found"])),
        ("publication_grade", grade),
        ("pet_friendly", outcomes["PUBLICATION_CANDIDATE"]),
        ("verified_no_pets", outcomes["VERIFIED_NO_PETS"]),
        ("policy_not_found", outcomes["POLICY_NOT_FOUND"]),
        ("access_blocked", outcomes["ACCESS_BLOCKED"]),
        ("routing_repair_required", outcomes["ROUTING_REPAIR_REQUIRED"]),
        ("identity_mismatch", outcomes["IDENTITY_MISMATCH"]),
        ("brand_classification_stale", outcomes["BRAND_CLASSIFICATION_STALE"]),
        ("hold", outcomes["HOLD"]),
        ("founder_exception", triage["FOUNDER_EXCEPTION"]),
        ("clean_pet_friendly", triage["CLEAN_PET_FRIENDLY_CANDIDATE"]),
        ("clean_verified_no_pets", triage["CLEAN_VERIFIED_NO_PETS_CANDIDATE"]),
        ("distinct_domains", len({r["official_domain"] for r in rows})),
        ("distinct_domains_yielding",
         len({r["official_domain"] for r in rows if r["policy_surface_found"]})),
        ("publication_grade_point_rate", point),
        ("wilson_95_lower", lo),
        ("wilson_95_upper", hi),
        ("pet_friendly_rate", pf_point),
        ("pet_friendly_wilson_95", [pf_lo, pf_hi]),
        ("verified_no_pets_rate", np_point),
        ("verified_no_pets_wilson_95", [np_lo, np_hi]),
    ))


def final_recommendation(stats):
    """One of three, and no fourth probe is available as an answer.

    The order forbids recommending another probe, which is right: two passes
    over the same family is where measurement stops being cheap and starts
    being avoidance.

    The decisive question is WHY a row failed. Silence is not an access
    problem, and a paid provider cannot fetch text a hotel never wrote -- so a
    family that renders cleanly and simply does not publish can never be
    PAID_LANE_REQUIRED, however low its yield.
    """
    n = stats["n"]
    if n == 0:
        return "SITE_BY_SITE_FREE_ONLY", "no rows were measured"

    access_failed = stats["access_blocked"] + (n - stats["rendered"])
    if access_failed > n / 3.0:
        return "PAID_LANE_REQUIRED", (
            "free access is the material blocker: %d of %d rows could not be "
            "reached or rendered" % (access_failed, n))

    if stats["wilson_95_lower"] >= 0.5 and stats["distinct_domains_yielding"] >= 5:
        return "FREE_LANE_SCALE", (
            "publication-grade %d/%d across %d distinct yielding domains "
            "(Wilson lower %.2f) -- broad enough to treat attended Chrome as a "
            "family-level lane"
            % (stats["publication_grade"], n,
               stats["distinct_domains_yielding"], stats["wilson_95_lower"]))

    return "SITE_BY_SITE_FREE_ONLY", (
        "access is consistently easy -- %d of %d rendered and %d of %d "
        "identities bound -- and %d of %d rows across %d of %d domains yield "
        "publication-grade evidence. The failures are SILENCE, not access, and "
        "no provider can fetch policy a hotel never published. So the lane is "
        "free and real but site-by-site: a family-wide rate over %d unrelated "
        "websites describes none of them."
        % (stats["rendered"], n, stats["identity_confirmed"], n,
           stats["publication_grade"], n, stats["distinct_domains_yielding"],
           stats["distinct_domains"], stats["distinct_domains"]))
