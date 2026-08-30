# -*- coding: utf-8 -*-
"""PTF-CINCINNATI-FREE-LANE-SCALE-006 -- run the qualified free lane out.

PROBE-005 measured the attended-Chrome lane on ten fresh rows and returned
FREE_LANE_SCALE for IHG and for Choice separately. This order is the scale run,
not another probe: every remaining eligible row is processed, and the lane's
performance is reported over probe plus scale together.

The cohort is rebuilt mechanically from current state rather than taken from
005's implied remainder. A remaining-row count is a fact about the shard at a
moment, and the shard has moved twice since the number that produced it.

Nothing here writes authority, and no row is decided in flight -- the genuine
exceptions from 005 and 006 are consolidated into one founder packet at the
end.
"""

from __future__ import annotations

from collections import Counter, OrderedDict

from scripts.pettripfinder.cincinnati_free_brand_probe_005 import (
    AUTH, FAMILIES, OUTCOMES, PACKAGE_DIR, PUBLICATION_GRADE, REPORTS, TRIAGES,
    _excluded_keys, _identity_conflicted, _previously_captured,
    _published_keys, _sub_brand, _url_shape, load, render, wilson)

WORK_ORDER = "PTF-CINCINNATI-FREE-LANE-SCALE-006"
MARKET_ID = "cincinnati-oh"
OBSERVED_ON = "2026-08-29"
CAPTURE_METHOD = "attended_chrome_render"

PROBE_RESULTS = REPORTS / "cincinnati_probe005_results.json"
ROUTING = AUTH / "identity_routing.json"
PARTITION = PACKAGE_DIR / "cincinnati_final_partition_001.json"

COHORT = REPORTS / "cincinnati_scale006_cohort.json"
RESULTS = REPORTS / "cincinnati_scale006_results.json"
CLEAN_PF = REPORTS / "cincinnati_scale006_clean_pet_friendly.json"
CLEAN_NP = REPORTS / "cincinnati_scale006_clean_verified_no_pets.json"
PACKET = REPORTS / "cincinnati_free_lane_founder_packet.json"
LANE = REPORTS / "cincinnati_free_lane_final_measurement.json"
REPRICE = REPORTS / "cincinnati_scale006_reprice.json"

RESOLVED = ("PUBLISHED_PET_FRIENDLY", "VERIFIED_NO_PETS",
            "OUT_OF_CURRENT_CATEGORY")


def _probe_keys():
    return {r["identity_key"] for r in load(PROBE_RESULTS)["rows"]}


def build_cohort():
    """Every remaining eligible IHG/Choice row, with its own suppression audit.

    The suppression counters are reported per family so the cohort can be
    argued with: a row that vanished should be traceable to the rule that
    removed it, not to an unexplained shortfall.
    """
    routes = load(ROUTING)["routes"]
    published, excluded = _published_keys(), _excluded_keys()
    captured, conflicted = _previously_captured(), _identity_conflicted()
    probed = _probe_keys()

    audit, rows = OrderedDict(), []
    seen_keys, seen_urls = set(), set()

    for family in FAMILIES:
        counters = Counter()
        family_routes = [r for r in routes if r.get("brand") == family]
        counters["routed_total"] = len(family_routes)
        for route in family_routes:
            key = route["hotel_ref"]["identity_key"]
            url = route.get("official_property_url") or ""
            if key in published:
                counters["suppressed_already_published"] += 1
            elif key in excluded:
                counters["suppressed_already_excluded"] += 1
            elif key in conflicted:
                counters["suppressed_identity_conflict_open"] += 1
            elif key in captured:
                counters["suppressed_previously_captured"] += 1
            elif key in probed:
                counters["suppressed_answered_by_probe_005"] += 1
            elif route.get("status") != "ROUTING_CONFIRMED":
                counters["suppressed_route_not_confirmed"] += 1
            elif not url.startswith("https://"):
                counters["suppressed_no_first_party_url"] += 1
            elif key in seen_keys:
                counters["suppressed_duplicate_identity"] += 1
            elif url in seen_urls:
                counters["suppressed_duplicate_canonical_url"] += 1
            else:
                seen_keys.add(key)
                seen_urls.add(url)
                counters["admitted"] += 1
                rows.append(OrderedDict((
                    ("identity_key", key),
                    ("canonical_name", route["hotel_ref"]["canonical_name"]),
                    ("family", family),
                    ("sub_brand", _sub_brand(route["hotel_ref"]["canonical_name"])),
                    ("official_property_url", url),
                    ("url_shape", _url_shape(url)),
                    ("city", route["identity_context"].get("city", "")),
                    ("postal_code", route["identity_context"].get("postal_code", "")),
                    ("address", route["identity_context"].get("address", "")),
                    ("phone", route["identity_context"].get("phone", "")),
                )))
        counters["unresolved_routed"] = (
            counters["routed_total"] - counters["suppressed_already_published"]
            - counters["suppressed_already_excluded"])
        counters["already_captured"] = (
            counters["suppressed_previously_captured"]
            + counters["suppressed_answered_by_probe_005"])
        audit[family] = OrderedDict(sorted(counters.items()))

    rows.sort(key=lambda r: (r["family"], r["identity_key"]))
    return OrderedDict((
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("basis", "rebuilt from the current census, routing shard, authority, "
                  "Capture Pass 003, Probe 005 and the founder-review state; "
                  "no historical remaining-row count was trusted"),
        ("provider_calls", 0),
        ("paid_spend_usd", 0.0),
        ("audit_by_family", audit),
        ("count", len(rows)),
        ("rows", rows),
    ))


# ------------------------------------------------------------------ measurement

def measure(rows):
    """Counters plus a Wilson interval for one set of observed rows."""
    outcomes = Counter(r["outcome"] for r in rows)
    triage = Counter(r["triage"] for r in rows)
    n = len(rows)
    grade = sum(outcomes[o] for o in PUBLICATION_GRADE)
    point, lo, hi = wilson(grade, n)
    return OrderedDict((
        ("n", n),
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


def build_final_measurement(scale_rows):
    """Probe 005 and Scale 006 together -- the lane's real record.

    Reported per family and combined. The two families stay separate to the
    end: they were qualified separately and they close separately.
    """
    probe = load(PROBE_RESULTS)["rows"]
    combined = list(probe) + list(scale_rows)
    keys = [r["identity_key"] for r in combined]
    assert len(keys) == len(set(keys)), "a row was observed in both passes"

    out = OrderedDict((("work_order", WORK_ORDER),
                       ("closes", "IHG and Choice acquisition experimentation "
                                  "for Cincinnati"),
                       ("passes", ["PTF-CINCINNATI-FREE-BRAND-PROBE-005",
                                   WORK_ORDER])))
    for family in FAMILIES:
        out[family] = OrderedDict((
            ("probe_005", measure([r for r in probe if r["family"] == family])),
            ("scale_006", measure([r for r in scale_rows
                                   if r["family"] == family])),
            ("free_lane_total",
             measure([r for r in combined if r["family"] == family])),
        ))
    out["COMBINED"] = OrderedDict((
        ("probe_005", measure(probe)),
        ("scale_006", measure(scale_rows)),
        ("free_lane_total", measure(combined)),
    ))
    return out


# --------------------------------------------------------------------- reprice

BRIGHTDATA_USD_PER_ATTEMPT = 0.197

LANE_OF_FAMILY = {
    "IHG": "ATTENDED_CHROME_FREE_CLOSED",
    "CHOICE": "ATTENDED_CHROME_FREE_CLOSED",
    "MARRIOTT": "BRIGHT_DATA",
    "HILTON": "BRIGHT_DATA",
    "HYATT": "BLOCKED_BY_ADR",
    "INDEPENDENT": "FREE_LANE_UNPROVEN",
    "ESA": "FREE_LANE_UNPROVEN",
    "BESTWESTERN": "FREE_LANE_UNPROVEN",
    "WYNDHAM": "FREE_LANE_UNPROVEN",
}


def build_reprice(scale_rows):
    """What is left, by family and lane, after the free lane has been run out.

    Rows this pass answered are still UNRESOLVED in authority -- nothing has
    been applied -- so they are reported as free-lane-answered-pending-review
    rather than quietly deducted. Deducting them here would price the market as
    if a founder had already ruled.
    """
    routes = load(ROUTING)["routes"]
    state = {i["identity_key"]: i["final_state"]
             for i in load(PARTITION)["items"]}
    routed = {r["hotel_ref"]["identity_key"] for r in routes}
    answered = ({r["identity_key"] for r in scale_rows}
                | {r["identity_key"] for r in load(PROBE_RESULTS)["rows"]})

    by_family, pending = Counter(), Counter()
    for route in routes:
        key = route["hotel_ref"]["identity_key"]
        if state.get(key) in RESOLVED:
            continue
        family = route.get("brand") or "UNKNOWN"
        by_family[family] += 1
        if key in answered:
            pending[family] += 1

    unrouted = sorted(k for k, v in state.items()
                      if v not in RESOLVED and k not in routed)
    by_state = Counter(state[k] for k in unrouted)

    lanes = OrderedDict()
    for family, n in sorted(by_family.items()):
        lane = LANE_OF_FAMILY.get(family, "FREE_LANE_UNPROVEN")
        row = lanes.setdefault(lane, OrderedDict((
            ("families", OrderedDict()), ("rows", 0),
            ("answered_pending_review", 0))))
        row["families"][family] = n
        row["rows"] += n
        row["answered_pending_review"] += pending[family]

    bd = lanes.get("BRIGHT_DATA", {}).get("rows", 0)
    return OrderedDict((
        ("work_order", WORK_ORDER),
        ("basis", "the routing shard and partition at 86ffec4; no authority "
                  "was applied by this order, so answered rows remain "
                  "unresolved and are reported as pending review"),
        ("unresolved_total", sum(1 for v in state.values() if v not in RESOLVED)),
        ("unresolved_routed", sum(by_family.values())),
        ("unresolved_unrouted", len(unrouted)),
        ("unrouted_by_state", OrderedDict(sorted(by_state.items()))),
        ("by_family", OrderedDict(sorted(by_family.items()))),
        ("lanes", lanes),
        ("firecrawl", OrderedDict((
            ("rows", 0), ("usd", 0.0),
            ("why", "Firecrawl's Cincinnati case was IHG and Choice, and this "
                    "order ran both out for free. It cannot reach Marriott or "
                    "Hilton (PTF-FIRECRAWL-HARD-LANES-003), and no family in "
                    "the current unresolved set produces a new qualified need. "
                    "It is not resurrected because an older plan named it.")))),
        ("bright_data", OrderedDict((
            ("rows", bd), ("usd_per_attempt", BRIGHTDATA_USD_PER_ATTEMPT),
            ("projected_usd", round(bd * BRIGHTDATA_USD_PER_ATTEMPT, 2))))),
        ("spend_this_order_usd", 0.0),
        ("note", "An estimate, not an authorization. Nothing here spends."),
    ))
