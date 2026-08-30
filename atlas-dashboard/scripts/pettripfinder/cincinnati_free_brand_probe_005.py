# -*- coding: utf-8 -*-
"""PTF-CINCINNATI-FREE-BRAND-PROBE-005 -- cohort builder and reporter.

Capture Pass 3 showed that attended Chrome renders IHG and Choice property
pages. It did not show at what RATE those pages then yield publication-grade
policy evidence, because Pass 3's IHG/Choice rows were not a sample drawn to
answer that question -- they were whatever the cohort happened to contain.

This module draws a fresh 10-row sample, stratified 5/5 across the two
families and diversified across sub-brand, city and URL shape, and reports the
result per family with a Wilson interval. The two families are measured and
recommended SEPARATELY: a shared "IHG/Choice render attended" observation is
about access, and access is not extraction.

Nothing here writes authority. The probe proposes; a later order disposes.
"""

from __future__ import annotations

import io
import json
import math
import re
from collections import Counter, OrderedDict
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parents[2] / "launch_packages" / "pettripfinder"
AUTH = PACKAGE_DIR / "markets" / "authority" / "cincinnati-oh"
REPORTS = PACKAGE_DIR / "markets" / "reports"

WORK_ORDER = "PTF-CINCINNATI-FREE-BRAND-PROBE-005"
MARKET_ID = "cincinnati-oh"
FAMILIES = ("IHG", "CHOICE")
COHORT_CAP = 10
PER_FAMILY = 5

OUTCOMES = ("PUBLICATION_CANDIDATE", "VERIFIED_NO_PETS", "POLICY_NOT_FOUND",
            "ACCESS_BLOCKED", "ROUTING_REPAIR_REQUIRED", "IDENTITY_MISMATCH",
            "HOLD")
TRIAGES = ("CLEAN_PET_FRIENDLY_CANDIDATE", "CLEAN_VERIFIED_NO_PETS_CANDIDATE",
           "FOUNDER_EXCEPTION", "NO_FOUNDER_ACTION")

#: An outcome is publication-grade when the page yielded evidence a founder
#: could rule on. POLICY_NOT_FOUND is a real, honest observation -- and it is
#: not publication-grade, because it publishes nothing.
PUBLICATION_GRADE = ("PUBLICATION_CANDIDATE", "VERIFIED_NO_PETS")

COHORT = REPORTS / "cincinnati_probe005_cohort.json"
RESULTS = REPORTS / "cincinnati_probe005_results.json"
MEASUREMENT = REPORTS / "cincinnati_probe005_measurement.json"
REPRICE = REPORTS / "cincinnati_probe005_reprice.json"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def render(path, payload):
    io.open(path, "w", encoding="utf-8", newline="\n").write(
        json.dumps(payload, indent=1, ensure_ascii=False) + "\n")


# ------------------------------------------------------------------ eligibility

def _published_keys():
    package = load(PACKAGE_DIR / ("hotel_policy_facts_%s.json" % MARKET_ID))
    return {h["identity_key"] for h in package["hotels"]}


def _excluded_keys():
    blob = load(AUTH / "hotel_exclusions.json")
    return {e["normalized_name"] for e in blob["exclusions"]}


def _previously_captured():
    """Every identity a prior Cincinnati attended pass actually reached.

    'Fresh' has to mean fresh for the QUESTION, not merely absent from the
    latest artifact. A row Pass 1 rendered and Pass 3 skipped is still a row
    whose page we have already seen, and including it would measure our own
    prior selection rather than the lane.
    """
    seen = set()
    for name, field in (("cincinnati_capture_pass1_001_results.json", "rows"),
                        ("cincinnati_capture_pass3_001_results.json", "rows"),
                        ("cincinnati_21c_recapture_001_results.json", "rows")):
        path = REPORTS / name
        if not path.exists():
            continue
        for row in load(path).get(field) or []:
            seen.add(row["identity_key"])
    return seen


def _identity_conflicted():
    """Rows whose identity is itself the open question.

    A probe of a policy surface cannot report cleanly on a row where we do not
    yet agree which building it is.
    """
    partition = load(PACKAGE_DIR / "cincinnati_final_partition_001.json")
    return {i["identity_key"] for i in partition["items"]
            if i["final_state"] == "AWAITING_IDENTITY_RESOLUTION"}


def _url_shape(url):
    """A coarse template signature, used only to spread the sample.

    IHG serves /hotels/us/en/<city>/<code>/hoteldetail and Choice serves
    /<brand>/<state>/<city>/<code>-hotel; a sample that lands entirely on one
    template measures that template, which is exactly the trap Detroit 014
    fell into when Marriott scored 0/2 on a legacy path and 11/11 on the
    current one.
    """
    path = re.sub(r"^https?://[^/]+", "", url or "")
    segments = [s for s in path.split("/") if s]
    return "/".join(segments[:2]) or "/"


def _sub_brand(name):
    lowered = (name or "").lower()
    for token in ("holiday inn express", "holiday inn", "candlewood",
                  "staybridge", "even hotel", "avid", "atwell", "intercontinental",
                  "kimpton", "hotel indigo", "crowne plaza",
                  "comfort suites", "comfort inn", "quality inn", "sleep inn",
                  "clarion pointe", "clarion", "econo lodge", "rodeway",
                  "mainstay", "suburban", "woodspring", "cambria",
                  "ascend", "everhome"):
        if token in lowered:
            return token
    return lowered.split(" cincinnati")[0][:24]


def build_cohort():
    """Draw the probe cohort. Reports its own exclusions, so the sample can be
    argued with rather than taken on trust."""
    routes = load(AUTH / "identity_routing.json")["routes"]
    published, excluded = _published_keys(), _excluded_keys()
    captured, conflicted = _previously_captured(), _identity_conflicted()

    rejected = Counter()
    eligible = []
    seen_urls, seen_keys = set(), set()

    for route in routes:
        key = route["hotel_ref"]["identity_key"]
        family = route.get("brand", "")
        url = route.get("official_property_url") or ""

        if family not in FAMILIES:
            continue
        if key in published:
            rejected["already_published"] += 1
            continue
        if key in excluded:
            rejected["already_excluded"] += 1
            continue
        if key in conflicted:
            rejected["identity_conflict_open"] += 1
            continue
        if key in captured:
            rejected["previously_captured"] += 1
            continue
        if route.get("status") != "ROUTING_CONFIRMED":
            rejected["route_not_confirmed"] += 1
            continue
        if not url.startswith("https://"):
            rejected["no_first_party_url"] += 1
            continue
        if key in seen_keys:
            rejected["duplicate_identity"] += 1
            continue
        if url in seen_urls:
            rejected["duplicate_canonical_url"] += 1
            continue
        seen_keys.add(key)
        seen_urls.add(url)

        eligible.append(OrderedDict((
            ("identity_key", key),
            ("canonical_name", route["hotel_ref"]["canonical_name"]),
            ("family", family),
            ("sub_brand", _sub_brand(route["hotel_ref"]["canonical_name"])),
            ("official_property_url", url),
            ("official_domain", route.get("official_domain", "")),
            ("url_shape", _url_shape(url)),
            ("city", route["identity_context"].get("city", "")),
            ("postal_code", route["identity_context"].get("postal_code", "")),
            ("address", route["identity_context"].get("address", "")),
            ("phone", route["identity_context"].get("phone", "")),
            ("routing_status", route.get("status", "")),
        )))

    selected = []
    for family in FAMILIES:
        pool = [r for r in eligible if r["family"] == family]
        selected.extend(_diversify(pool, PER_FAMILY))

    payload = OrderedDict((
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("cap", COHORT_CAP),
        ("per_family_target", PER_FAMILY),
        ("provider_calls", 0),
        ("paid_spend_usd", 0.0),
        ("eligible_by_family", {f: sum(1 for r in eligible if r["family"] == f)
                                for f in FAMILIES}),
        ("rejected_reasons", OrderedDict(sorted(rejected.items()))),
        ("substitution_rule",
         "If a family has fewer than %d eligible rows the cohort runs short. "
         "No other brand is substituted to reach %d." % (PER_FAMILY, COHORT_CAP)),
        ("count", len(selected)),
        ("rows", selected),
    ))
    return payload, eligible


def _diversify(pool, want):
    """Round-robin over sub-brand, then URL shape, then city.

    Deterministic: the pool arrives in shard order and ties break on identity
    key, so the cohort is reproducible from the committed authority alone.
    """
    pool = sorted(pool, key=lambda r: r["identity_key"])
    chosen, used_brand, used_shape, used_city = [], set(), set(), set()
    for axis in ("sub_brand", "url_shape", "city", None):
        for row in pool:
            if len(chosen) >= want:
                break
            if row in chosen:
                continue
            if axis == "sub_brand" and row["sub_brand"] in used_brand:
                continue
            if axis == "url_shape" and row["url_shape"] in used_shape:
                continue
            if axis == "city" and row["city"] in used_city:
                continue
            chosen.append(row)
            used_brand.add(row["sub_brand"])
            used_shape.add(row["url_shape"])
            used_city.add(row["city"])
    return chosen[:want]


# ------------------------------------------------------------------- measurement

def wilson(successes, trials, z=1.959963984540054):
    """Wilson score interval. Sized on the LOWER bound, per Indianapolis 015.

    A point rate from 5 trials is not a rate; the lower bound is what a spend
    decision may lean on.
    """
    if trials == 0:
        return (0.0, 0.0, 0.0)
    p = successes / float(trials)
    d = 1 + z * z / trials
    centre = (p + z * z / (2 * trials)) / d
    half = (z * math.sqrt(p * (1 - p) / trials
                          + z * z / (4 * trials * trials))) / d
    return (round(p, 4), round(max(0.0, centre - half), 4),
            round(min(1.0, centre + half), 4))


def measure(rows):
    """Per-family counters plus the combined row, each with its interval."""
    def block(subset):
        outcomes = Counter(r["outcome"] for r in subset)
        triage = Counter(r["triage"] for r in subset)
        n = len(subset)
        grade = sum(outcomes[o] for o in PUBLICATION_GRADE)
        point, lo, hi = wilson(grade, n)
        return OrderedDict((
            ("attempted", n),
            ("identity_confirmed", sum(1 for r in subset
                                       if r["identity_confirmed"])),
            ("page_rendered", sum(1 for r in subset if r["page_rendered"])),
            ("policy_surface_found", sum(1 for r in subset
                                         if r["policy_surface_found"])),
            ("publication_grade", grade),
            ("pet_friendly", outcomes["PUBLICATION_CANDIDATE"]),
            ("verified_no_pets", outcomes["VERIFIED_NO_PETS"]),
            ("policy_not_found", outcomes["POLICY_NOT_FOUND"]),
            ("access_blocked", outcomes["ACCESS_BLOCKED"]),
            ("routing_repair_required", outcomes["ROUTING_REPAIR_REQUIRED"]),
            ("identity_mismatch", outcomes["IDENTITY_MISMATCH"]),
            ("hold", outcomes["HOLD"]),
            ("founder_exception", triage["FOUNDER_EXCEPTION"]),
            ("publication_grade_point_rate", point),
            ("wilson_95_lower", lo),
            ("wilson_95_upper", hi),
        ))

    out = OrderedDict()
    for family in FAMILIES:
        out[family] = block([r for r in rows if r["family"] == family])
    out["COMBINED"] = block(rows)
    return out


def recommend(stats):
    """One recommendation per family, never shared.

    FREE_LANE_SCALE requires all four of the founder's conditions AND enough
    trials for the lower bound to mean anything. Five rows cannot carry a
    scale decision on their own, which is what MORE_FREE_PROBE_NEEDED is for.
    """
    n = stats["attempted"]
    if n == 0:
        return "MORE_FREE_PROBE_NEEDED", "no eligible rows were drawn"
    renders = stats["page_rendered"] == n
    identity = stats["identity_confirmed"] == n
    systemic = stats["access_blocked"] > 0
    lo = stats["wilson_95_lower"]

    if not renders or systemic:
        return "PAID_LANE_REQUIRED", (
            "attended Chrome did not reliably render the property page "
            "(%d/%d rendered, %d blocked)" % (stats["page_rendered"], n,
                                              stats["access_blocked"]))
    if not identity:
        return "MORE_FREE_PROBE_NEEDED", (
            "identity binding failed on %d of %d rows"
            % (n - stats["identity_confirmed"], n))
    if lo >= 0.5 and n >= 5:
        return "FREE_LANE_SCALE", (
            "renders %d/%d, identity %d/%d, publication-grade %d/%d "
            "(Wilson lower %.2f)" % (stats["page_rendered"], n,
                                     stats["identity_confirmed"], n,
                                     stats["publication_grade"], n, lo))
    return "MORE_FREE_PROBE_NEEDED", (
        "access and identity are clean but publication-grade yield is %d/%d "
        "(Wilson lower %.2f), too thin to size a scale run"
        % (stats["publication_grade"], n, lo))
