"""PTF-DISCOVERY-P0-001 -- read-only advisory coverage audit over a market.

Answers one question an inventory can never ask itself: "does this market's
identity data LOOK incomplete in a way a human should go check?" It reads
the market's identity census (or, for Columbus, the published inventory --
the only census-like view that market has), computes structural metrics,
and reports anomalies. Adopted from PTF-PARALLEL-RESEARCH-002
``coverage_audit_mvp.md`` under FD-R1 item 1, ADAPTED to Atlas's actual
data: zones are the market's own corridors (city/ZIP membership via the
existing assignment authority), not lat/lon-radius circles -- the census
carries no coordinates, and inventing a second zone geometry when the
corridor contracts already define market structure would be a defect
factory.

ADVISORY ONLY (FD-R6, enforced by construction): this module reads
committed data and writes one report file under ``markets/reports/``. It
imports neither the publication guard nor anything that writes census,
seed, policy, or site state; no anomaly can alter identity status, remove
or create a property, block publication, or touch pet-policy authority.
Anomalies are instructions for a human to LOOK -- never target counts, and
never a completeness percentage (that doctrine is
``discovery/coverage.py``'s, and it applies here unchanged).

Thresholds all live in the per-market coverage config
(``launch_packages/pettripfinder/markets/coverage/<market_id>.json``) --
uncalibrated priors adopted as configurable defaults under FD-R6, never
hardcoded. Where the data cannot support a check (Columbus predates
source-family tracking), the check reports a data gap instead of guessing.

Deterministic: same census + config => byte-identical report. ``as_of``
comes from the census's own dates, never from a clock.
"""

from __future__ import annotations

import json
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.discovery.source_families import (  # noqa: E402
    SOURCE_FAMILIES,
    collapse_families,
    family_of,
    validate_non_independent_pairs,
)
from scripts.pettripfinder.markets import (  # noqa: E402
    MARKETS_DIR,
    MarketConfig,
    assign_hotels,
)
from scripts.pettripfinder.market_context import resolve_market  # noqa: E402

SCHEMA = "ptf-coverage-audit/1.0"
CONFIG_SCHEMA = "ptf-coverage-config/1.0"

COVERAGE_CONFIG_DIR = MARKETS_DIR / "coverage"
IDENTITY_CENSUS_DIR = (_REPO_ROOT / "launch_packages" / "pettripfinder"
                       / "identity_census")

CENSUS_KIND_IDENTITY = "identity_census"
CENSUS_KIND_PUBLISHED = "published_inventory"
CENSUS_KINDS = (CENSUS_KIND_IDENTITY, CENSUS_KIND_PUBLISHED)

SEVERITY_HIGH = "HIGH"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_LOW = "LOW"

CA_EMPTY_EXPECTED_ZONE = "CA_EMPTY_EXPECTED_ZONE"
CA_ZONE_BELOW_MIN = "CA_ZONE_BELOW_MIN"
CA_DENSITY_LOW = "CA_DENSITY_LOW"
CA_DENSITY_HIGH = "CA_DENSITY_HIGH"
CA_SOURCE_FRAGILITY = "CA_SOURCE_FRAGILITY"
CA_SINGLE_FAMILY_SHARE_HIGH = "CA_SINGLE_FAMILY_SHARE_HIGH"
CA_BRAND_FAMILY_GAP = "CA_BRAND_FAMILY_GAP"

ANOMALY_CODES = frozenset({
    CA_EMPTY_EXPECTED_ZONE, CA_ZONE_BELOW_MIN, CA_DENSITY_LOW,
    CA_DENSITY_HIGH, CA_SOURCE_FRAGILITY, CA_SINGLE_FAMILY_SHARE_HIGH,
    CA_BRAND_FAMILY_GAP,
})

#: FD-R6 configurable defaults (the research prototype's uncalibrated
#: priors). A market's coverage config may override any of them; nothing
#: reads these except through the config merge.
DEFAULT_THRESHOLDS = OrderedDict([
    ("density_floor_per_10k", 0.8),
    ("density_ceiling_per_10k", 8.0),
    ("min_families", 3),
    ("single_family_ceiling", 0.40),
    ("brand_floor", 6),
    ("brand_pop_floor", 250000),
])

#: Major-brand-family detection vocabulary: exact sub-brand phrases (the
#: same bounded-phrase discipline as ``property_identity.LODGING_BRANDS`` --
#: word-boundary matches, never fragments), grouped by parent family. Used
#: only to count DISTINCT families present in a market for the advisory
#: brand-gap check; never to classify, merge, or exclude a property.
BRAND_FAMILY_PHRASES = OrderedDict([
    ("MARRIOTT", ("marriott", "sheraton", "westin", "four points",
                  "residence inn", "courtyard by marriott", "springhill",
                  "towneplace", "fairfield", "ac hotel", "aloft", "element",
                  "moxy")),
    ("HILTON", ("hilton", "doubletree", "embassy suites", "homewood",
                "home2", "hampton", "tru by hilton")),
    ("HYATT", ("hyatt",)),
    ("IHG", ("holiday inn", "crowne plaza", "staybridge", "candlewood",
             "avid", "kimpton", "intercontinental", "even hotel")),
    ("WYNDHAM", ("wyndham", "ramada", "days inn", "super 8", "baymont",
                 "microtel", "travelodge", "la quinta")),
    ("CHOICE", ("choice hotels", "comfort inn", "comfort suites",
                "quality inn", "sleep inn", "clarion", "cambria",
                "econo lodge", "rodeway", "mainstay", "woodspring")),
    ("BEST_WESTERN", ("best western",)),
    ("RADISSON", ("radisson", "country inn", "park inn")),
    ("RED_ROOF", ("red roof",)),
    ("EXTENDED_STAY", ("extended stay",)),
    ("SONESTA", ("sonesta",)),
    ("G6", ("motel 6", "studio 6")),
    ("DRURY", ("drury",)),
    ("GREAT_WOLF", ("great wolf lodge",)),
])


class CoverageAuditError(ValueError):
    """A malformed coverage config or an unusable census (fail closed)."""


# --------------------------------------------------------------------------- #
# Config.
# --------------------------------------------------------------------------- #

def load_coverage_config(market_id: str, path: Path = None) -> Dict:
    p = Path(path) if path else (COVERAGE_CONFIG_DIR / ("%s.json" % market_id))
    if not p.exists():
        raise CoverageAuditError(
            "no coverage config for market %r (expected %s)" % (market_id, p))
    config = json.loads(p.read_text(encoding="utf-8"))
    if config.get("schema") != CONFIG_SCHEMA:
        raise CoverageAuditError(
            "%s: schema must be %r, got %r"
            % (p, CONFIG_SCHEMA, config.get("schema")))
    if config.get("market_id") != market_id:
        raise CoverageAuditError(
            "%s: market_id %r does not match requested %r"
            % (p, config.get("market_id"), market_id))
    if config.get("census_kind") not in CENSUS_KINDS:
        raise CoverageAuditError(
            "%s: census_kind must be one of %s" % (p, list(CENSUS_KINDS)))
    population = config.get("population")
    if not isinstance(population, int) or population <= 0:
        raise CoverageAuditError(
            "%s: population must be a positive integer" % p)
    thresholds = OrderedDict(DEFAULT_THRESHOLDS)
    for key, value in (config.get("thresholds") or {}).items():
        if key not in DEFAULT_THRESHOLDS:
            raise CoverageAuditError("%s: unknown threshold %r" % (p, key))
        thresholds[key] = value
    config["thresholds"] = thresholds
    validate_non_independent_pairs(config.get("non_independent_family_pairs") or ())
    for overridden in (config.get("source_family_overrides") or {}).values():
        if overridden not in SOURCE_FAMILIES:
            raise CoverageAuditError(
                "%s: source_family_overrides maps to unknown family %r"
                % (p, overridden))
    for gap in config.get("accepted_gaps") or ():
        if gap.get("anomaly_code") not in ANOMALY_CODES:
            raise CoverageAuditError(
                "%s: accepted_gaps entry names unknown anomaly code %r"
                % (p, gap.get("anomaly_code")))
        if not str(gap.get("note", "")).strip():
            raise CoverageAuditError(
                "%s: an accepted gap must say WHY it is accepted" % p)
    return config


# --------------------------------------------------------------------------- #
# Census views. Both produce the same normalized record shape:
#   {name, city, postal_code, zone_id ('' when unzoned), family ('' when
#    untracked)} -- read-only over committed artifacts.
# --------------------------------------------------------------------------- #

def _identity_census_view(market_id: str, config: Dict) -> Tuple[List[Dict], str, List[str]]:
    path = IDENTITY_CENSUS_DIR / ("%s.json" % market_id)
    if not path.exists():
        raise CoverageAuditError("no identity census at %s" % path)
    census = json.loads(path.read_text(encoding="utf-8"))
    overrides = config.get("source_family_overrides") or {}
    records, gaps = [], []
    unmapped = set()
    for hotel in census.get("hotels", ()):
        family = family_of(hotel.get("source", ""), overrides)
        if not family and hotel.get("source"):
            unmapped.add(hotel["source"])
        records.append({
            "name": hotel.get("canonical_name") or hotel.get("display_name", ""),
            "city": hotel.get("city", ""),
            "postal_code": hotel.get("postal_code", ""),
            "zone_id": hotel.get("corridor") or "",
            "family": family,
        })
    if unmapped:
        gaps.append("source(s) with no family mapping (add to "
                    "source_family_overrides or source_families.py): %s"
                    % sorted(unmapped))
    return records, str(census.get("captured_at", "")), gaps


def _published_inventory_view(market: MarketConfig) -> Tuple[List[Dict], str, List[str]]:
    # Imported here, not at module top: market_reports pulls in the site-data
    # stack, which the identity-census path does not need.
    from scripts.pettripfinder.market_reports import published_hotel_rows
    rows = published_hotel_rows()
    assignment = assign_hotels(market, rows, fail_closed=False)
    records = []
    for row in rows:
        from scripts.pettripfinder.site_data import normalize_name
        corridor_ids = assignment.corridor_of.get(normalize_name(row["name"]), ())
        zone_id = ""
        if corridor_ids:
            zone_id = market.corridor_by_id(corridor_ids[0]).slug
        records.append({
            "name": row.get("name", ""),
            "city": row.get("city", ""),
            "postal_code": row.get("postal_code", ""),
            "zone_id": zone_id,
            "family": "",
        })
    as_of = max((str(r.get("observed_at", "")) for r in rows), default="")
    gaps = ["published inventory predates per-property source-family "
            "tracking; source-family checks are not evaluable for this market"]
    return records, as_of, gaps


def build_census_view(market: MarketConfig, config: Dict) -> Tuple[List[Dict], str, List[str]]:
    if config["census_kind"] == CENSUS_KIND_IDENTITY:
        return _identity_census_view(market.market_id, config)
    return _published_inventory_view(market)


# --------------------------------------------------------------------------- #
# The audit (pure over the normalized view).
# --------------------------------------------------------------------------- #

def _brand_families_present(names: Sequence[str]) -> List[str]:
    present = []
    lowered = [(name or "").lower() for name in names]
    for family, phrases in BRAND_FAMILY_PHRASES.items():
        patterns = [re.compile(r"\b%s\b" % re.escape(p)) for p in phrases]
        if any(pat.search(name) for name in lowered for pat in patterns):
            present.append(family)
    return present


def _anomaly(code: str, severity: str, detail: str, zone_id: str = "") -> OrderedDict:
    entry = OrderedDict([("code", code), ("severity", severity)])
    if zone_id:
        entry["zone_id"] = zone_id
    entry["detail"] = detail
    return entry


def audit_market(market: MarketConfig, config: Dict,
                 records: Sequence[Dict], as_of: str,
                 data_gaps: Sequence[str]) -> Dict:
    thresholds = config["thresholds"]
    population = config["population"]
    pairs = config.get("non_independent_family_pairs") or ()

    active_count = len(records)
    per_10k = round(active_count * 10000.0 / population, 4)
    unzoned = [r for r in records if not r["zone_id"]]
    families = sorted({r["family"] for r in records if r["family"]})
    family_tracked = any(r["family"] for r in records)
    brand_families = _brand_families_present([r["name"] for r in records])

    anomalies: List[OrderedDict] = []

    # -- zones: the market's own corridors, occupancy by assigned corridor -- #
    zones = []
    min_expected_override = config.get("zones_min_expected") or {}
    occupancy: Dict[str, int] = {}
    for record in records:
        if record["zone_id"]:
            occupancy[record["zone_id"]] = occupancy.get(record["zone_id"], 0) + 1
    for corridor in sorted(market.corridors, key=lambda c: c.slug):
        min_expected = int(min_expected_override.get(
            corridor.slug, corridor.minimum_hotel_count))
        count = occupancy.get(corridor.slug, 0)
        zones.append(OrderedDict([
            ("zone_id", corridor.slug), ("name", corridor.name),
            ("min_expected", min_expected), ("active_count", count),
        ]))
        if min_expected >= 1 and count == 0:
            anomalies.append(_anomaly(
                CA_EMPTY_EXPECTED_ZONE, SEVERITY_HIGH,
                "corridor %r expects >= %d active properties and has 0"
                % (corridor.slug, min_expected), corridor.slug))
        elif 0 < count < min_expected:
            anomalies.append(_anomaly(
                CA_ZONE_BELOW_MIN, SEVERITY_MEDIUM,
                "corridor %r has %d active properties, below its expected "
                "minimum of %d" % (corridor.slug, count, min_expected),
                corridor.slug))

    # -- market-level density ---------------------------------------------- #
    if per_10k < thresholds["density_floor_per_10k"]:
        anomalies.append(_anomaly(
            CA_DENSITY_LOW, SEVERITY_HIGH,
            "%d active properties over population %d is %.4f per 10k, below "
            "the floor %.2f" % (active_count, population, per_10k,
                                thresholds["density_floor_per_10k"])))
    elif per_10k > thresholds["density_ceiling_per_10k"]:
        anomalies.append(_anomaly(
            CA_DENSITY_HIGH, SEVERITY_LOW,
            "%d active properties over population %d is %.4f per 10k, above "
            "the ceiling %.2f -- usually category leakage, so review, never "
            "prune" % (active_count, population, per_10k,
                       thresholds["density_ceiling_per_10k"])))

    # -- source-family structure (only where the data can support it) ------ #
    if family_tracked:
        independent = collapse_families(families, pairs)
        if len(independent) < thresholds["min_families"]:
            anomalies.append(_anomaly(
                CA_SOURCE_FRAGILITY, SEVERITY_HIGH,
                "only %d independent source family(ies) contribute to this "
                "census (%s after collapsing declared non-independent pairs); "
                "the configured minimum is %d"
                % (len(independent), sorted(independent),
                   thresholds["min_families"])))
        single_family = sum(
            1 for r in records
            if len(collapse_families([r["family"]], pairs)) <= 1)
        share = round(single_family / active_count, 4) if active_count else 0.0
        if share > thresholds["single_family_ceiling"]:
            anomalies.append(_anomaly(
                CA_SINGLE_FAMILY_SHARE_HIGH, SEVERITY_MEDIUM,
                "%.4f of active properties rest on a single source family "
                "(ceiling %.2f): a defect or retraction in one family would "
                "hit %d of %d properties"
                % (share, thresholds["single_family_ceiling"],
                   single_family, active_count)))
    else:
        share = None

    # -- brand families ----------------------------------------------------- #
    if population >= thresholds["brand_pop_floor"] and \
            len(brand_families) < thresholds["brand_floor"]:
        anomalies.append(_anomaly(
            CA_BRAND_FAMILY_GAP, SEVERITY_MEDIUM,
            "only %d major brand families present (%s) in a market of "
            "population %d; the configured floor is %d -- a missing national "
            "family in a market this size usually means a source gap, not a "
            "real absence" % (len(brand_families), brand_families,
                              population, thresholds["brand_floor"])))

    # -- accepted-gap suppression (listed, never dropped) ------------------- #
    surfaced, suppressed = [], []
    accepted = config.get("accepted_gaps") or ()
    for anomaly in anomalies:
        match = next(
            (g for g in accepted
             if g["anomaly_code"] == anomaly["code"]
             and (g.get("zone_id") or "") == anomaly.get("zone_id", "")),
            None)
        if match:
            entry = OrderedDict(anomaly)
            entry["accepted_gap_note"] = match["note"]
            suppressed.append(entry)
        else:
            surfaced.append(anomaly)

    metrics = OrderedDict([
        ("active_count", active_count),
        ("population", population),
        ("per_10k_population", per_10k),
        ("unzoned_count", len(unzoned)),
        ("unzoned_names", sorted(r["name"] for r in unzoned)),
        ("source_family_tracked", family_tracked),
        ("families_contributing", families),
        ("single_family_share", share),
        ("brand_families_present", brand_families),
    ])
    return OrderedDict([
        ("schema", SCHEMA),
        ("market_id", market.market_id),
        ("as_of", as_of),
        ("note", (
            "ADVISORY ONLY (FD-R6). Every anomaly is an instruction for a "
            "human to look, never a target count, a completeness percentage, "
            "an identity-status change, or a publication gate. Thresholds are "
            "configurable priors from the market's coverage config, "
            "uncalibrated until multi-market ground truth exists.")),
        ("census_kind", config["census_kind"]),
        ("thresholds", config["thresholds"]),
        ("metrics", metrics),
        ("zones", zones),
        ("anomalies", surfaced),
        ("suppressed", suppressed),
        ("data_gaps", list(data_gaps)),
    ])


def run_audit(market_id: str) -> Dict:
    market = resolve_market(market_id=market_id)
    config = load_coverage_config(market.market_id)
    records, as_of, data_gaps = build_census_view(market, config)
    return audit_market(market, config, records, as_of, data_gaps)


def write_report(market_id: str) -> Path:
    report = run_audit(market_id)
    reports_dir = MARKETS_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / ("%s_coverage_audit.json" % report["market_id"])
    path.write_text(json.dumps(report, indent=2) + "\n",
                    encoding="utf-8", newline="\n")
    return path


if __name__ == "__main__":
    for requested in (sys.argv[1:] or ["columbus-oh"]):
        print("wrote %s" % write_report(requested))
