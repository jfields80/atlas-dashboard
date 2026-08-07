"""PTF-CORRIDORS-002 -- market assignment review + route-migration reports.

Deterministic, read-only report generator for one configured market:

1. ``<market_id>_assignment_review.json`` (Part F): per-corridor assigned
   hotels, explicit assignments, exclusions, unassigned hotels, multi-match
   conflicts, below-minimum corridors, and suppressed routes -- over BOTH
   the currently PUBLISHED inventory (seed rows joined to the committed
   policy package) and the PROPOSED inventory (published + approved
   net-new display-review rows).
2. ``<market_id>_route_migration.md`` (Parts A10/I): how every current
   route would map to the target market-prefixed architecture, with
   redirect/canonical/sitemap/internal-link impact, ranking-loss risk, and
   a recommended migration order. REPORT ONLY -- nothing here performs a
   migration, writes a redirect, or changes a canonical.

Reads committed launch-package data and the committed market config; writes
only the two report files under ``launch_packages/pettripfinder/markets/``.
No network. Deterministic output (no timestamps, no environment state).
"""

from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from scripts.pettripfinder.markets import (
    MARKETS_DIR,
    CorridorAssignment,
    MarketConfig,
    assign_hotels,
    corridor_route,
    hotel_route,
    market_route,
)
from scripts.pettripfinder.market_context import resolve_market
from scripts.pettripfinder.site_data import (
    load_published_hotel_policy_facts,
    normalize_name,
    read_production_rows,
    verified_public_hotels,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DISPLAY_DECISIONS_PATH = (REPO_ROOT / "launch_packages" / "pettripfinder"
                          / "display_review_decisions.json")


def published_hotel_rows() -> List[Dict]:
    """The verified public inventory (the rows the generator publishes)."""
    rows = [r for r in read_production_rows() if r["category"] == "pet-friendly-hotels"]
    return verified_public_hotels(rows, load_published_hotel_policy_facts())


def proposed_hotel_rows() -> List[Dict]:
    """Published inventory plus the APPROVED net-new display-review rows
    (append-only decision file: the LAST decision per hotel_id wins). Read
    only -- the promotion-review artifact is never modified."""
    rows = list(published_hotel_rows())
    have = {normalize_name(r["name"]) for r in rows}
    if DISPLAY_DECISIONS_PATH.exists():
        decisions = json.loads(DISPLAY_DECISIONS_PATH.read_text(encoding="utf-8"))
        latest: "OrderedDict[str, Dict]" = OrderedDict()
        for d in decisions.get("decisions", []):
            latest[d["hotel_id"]] = d
        for d in latest.values():
            if d.get("decision") != "APPROVED":
                continue
            row = d["row"]
            if normalize_name(row.get("name", "")) not in have:
                rows.append(row)
                have.add(normalize_name(row.get("name", "")))
    return rows


def _corridor_section(market: MarketConfig, assignment: CorridorAssignment) -> List[Dict]:
    published = set(assignment.published)
    out = []
    for corridor in sorted(market.corridors, key=lambda c: (c.display_order, c.slug)):
        members = assignment.members_of(corridor.corridor_id)
        out.append(OrderedDict([
            ("corridor_id", corridor.corridor_id),
            ("name", corridor.name),
            ("slug", corridor.slug),
            ("published", corridor.corridor_id in published),
            ("minimum_hotel_count", corridor.minimum_hotel_count),
            ("member_count", len(members)),
            ("members", [r["name"] for r in members]),
            ("explicitly_assigned",
             list(assignment.explicit_members.get(corridor.corridor_id, ()))),
            ("excluded",
             list(assignment.excluded_members.get(corridor.corridor_id, ()))),
        ]))
    return out


def _inventory_view(market: MarketConfig, rows: Sequence[Dict], label: str) -> Dict:
    assignment = assign_hotels(market, rows, fail_closed=False)
    suppressed_routes = [
        corridor_route(market, market.corridor_by_id(s["corridor_id"]))
        for s in assignment.suppressed]
    return OrderedDict([
        ("inventory", label),
        ("hotel_count", len(rows)),
        ("corridors", _corridor_section(market, assignment)),
        ("unassigned_hotels", sorted(r["name"] for r in assignment.unassigned)),
        ("multi_match_conflicts", [
            OrderedDict([("hotel", c["hotel"]), ("tier", c["tier"]),
                         ("corridor_ids", list(c["corridor_ids"]))])
            for c in assignment.conflicts]),
        ("below_minimum_corridors", [
            OrderedDict([("corridor", market.corridor_by_id(s["corridor_id"]).name),
                         ("reason", s["reason"]),
                         ("member_count", s["member_count"])])
            for s in assignment.suppressed]),
        ("suppressed_routes", sorted(suppressed_routes)),
    ])


def build_assignment_review(market: MarketConfig) -> Dict:
    return OrderedDict([
        ("schema", "ptf-market-assignment-review/1.0"),
        ("market_id", market.market_id),
        ("market_schema", "ptf-market/1.0"),
        ("note", (
            "Deterministic assignment review generated by "
            "scripts/pettripfinder/market_reports.py. The 'published' view is "
            "the live verified inventory; the 'proposed' view adds the approved "
            "net-new display-review rows still moving through promotion review. "
            "Unassigned hotels remain published and are listed here, never "
            "dropped. Regenerate after any config or inventory change.")),
        ("views", [
            _inventory_view(market, published_hotel_rows(), "published"),
            _inventory_view(market, proposed_hotel_rows(), "proposed"),
        ]),
    ])


# --------------------------------------------------------------------------- #
# Route-migration report (Parts A10 / I). Report only.
# --------------------------------------------------------------------------- #

def _prefixed(market: MarketConfig) -> MarketConfig:
    """The same market viewed under the target (market-prefixed) routes."""
    return MarketConfig(**dict(
        market_id=market.market_id, market_name=market.market_name,
        market_slug=market.market_slug, state_name=market.state_name,
        state_code=market.state_code, primary_city=market.primary_city,
        country_code=market.country_code, title=market.title,
        meta_description=market.meta_description,
        introductory_copy=market.introductory_copy,
        navigation_label=market.navigation_label,
        show_in_navigation=market.show_in_navigation,
        show_in_sitemap=market.show_in_sitemap,
        minimum_published_hotels=market.minimum_published_hotels,
        route_mode="market_prefixed", corridors=market.corridors))


def build_route_migration_md(market: MarketConfig) -> str:
    rows = published_hotel_rows()
    assignment = assign_hotels(market, rows)
    target = _prefixed(market)

    pairs: List[Tuple[str, str, str]] = [
        ("market hub", market_route(market), market_route(target)),
        ("policy comparison", market_route(market) + "policy-comparison/",
         market_route(target) + "policy-comparison/"),
    ]
    for corridor in sorted(assignment.published_corridors(),
                           key=lambda c: (c.display_order, c.slug)):
        pairs.append(("corridor: %s" % corridor.name,
                      corridor_route(market, corridor),
                      corridor_route(target, corridor)))
    for r in sorted(rows, key=lambda r: normalize_name(r["name"])):
        pairs.append(("hotel: %s" % r["name"],
                      hotel_route(market, r["name"]),
                      hotel_route(target, r["name"])))

    lines = [
        "# %s route migration report (ptf-market/1.0)" % market.market_id,
        "",
        "**Report only (PTF-CORRIDORS-002 Parts A10/I).** No redirect, canonical,",
        "sitemap, or internal-link change is performed by this branch. The market",
        "runs in `%s` mode until this migration is explicitly approved." % market.route_mode,
        "",
        "## Route mapping (current -> proposed market-prefixed)",
        "",
        "For every row: redirect needed = **301 permanent**; canonical change =",
        "**yes** (self-canonical moves with the route); sitemap change = **yes**",
        "(new URL replaces old); internal-link change = **yes** (all internal",
        "hrefs are generated, so they follow automatically on regeneration).",
        "",
        "| Page | Current route | Proposed route |",
        "|---|---|---|",
    ]
    for label, current, proposed in pairs:
        marker = " (unchanged)" if current == proposed else ""
        lines.append("| %s | `%s` | `%s`%s |" % (label, current, proposed, marker))
    lines += [
        "",
        "## Risk of ranking loss",
        "",
        "- The site is young (live since 2026-07-25) with a small backlink",
        "  profile, so consolidated-signal loss from a 301 migration is LOW but",
        "  not zero; hotel profiles carry the indexed long-tail queries.",
        "- Every legacy route must 301 to its exact new counterpart (never the",
        "  hub), and the old sitemap URLs must be dropped in the same deploy the",
        "  new ones appear -- a mixed state risks duplicate-content dilution.",
        "- Canonicals, breadcrumb JSON-LD, and LodgingBusiness JSON-LD are all",
        "  generated from the route, so a single regeneration keeps them",
        "  consistent; no hand edits.",
        "",
        "## Recommended migration order",
        "",
        "1. Approve the target routes (this report) and freeze inventory churn",
        "   for the migration window.",
        "2. Regenerate the site in `market_prefixed` mode in a preview deploy;",
        "   verify route inventory, canonicals, and internal links against the",
        "   release-contract gates.",
        "3. Ship the production deploy with the full legacy->new 301 map in",
        "   `_redirects` (one rule per route, no wildcards that could shadow",
        "   real pages).",
        "4. Submit the new sitemap; monitor coverage and top hotel queries for",
        "   two weeks before removing any legacy rule.",
        "",
    ]
    return "\n".join(lines)


def write_reports(market: MarketConfig = None) -> Tuple[Path, Path]:
    market = resolve_market(market)
    # reports/ subdirectory: the market LOADER fail-closed-parses every
    # *.json directly in MARKETS_DIR, so report artifacts live one level
    # down where they can never be mistaken for a market document.
    reports_dir = MARKETS_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    review_path = reports_dir / ("%s_assignment_review.json" % market.market_id)
    migration_path = reports_dir / ("%s_route_migration.md" % market.market_id)
    review_path.write_text(
        json.dumps(build_assignment_review(market), indent=2) + "\n",
        encoding="utf-8", newline="\n")
    migration_path.write_text(build_route_migration_md(market),
                              encoding="utf-8", newline="\n")
    return review_path, migration_path


if __name__ == "__main__":
    for path in write_reports():
        print("wrote %s" % path)
