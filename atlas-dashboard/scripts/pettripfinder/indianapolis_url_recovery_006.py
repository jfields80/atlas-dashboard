# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-OFFICIAL-URL-RECOVERY-006 -- can the 143 unroutable rows be routed?

A market's payable pool is capped by how many identities have a first-party URL
at all. Indianapolis holds 257 confirmed identities and 143 of them name no
website, so no lane can be pointed at them and no amount of acquisition budget
reaches them. This module asks what can be routed from evidence already on
disk, and answers it with the repo's own recovery machinery rather than by
guessing a URL shape.

IT FETCHES NOTHING AND SPENDS NOTHING.

WHAT IT FOUND, IN ONE LINE
--------------------------
Zero net new routes. Every zero-cost avenue is genuinely exhausted, and the
evidence for that is in ``phase_2_evidence_consulted``: the discovery cache
holds OpenStreetMap and nothing else, the prior build's URLs were already
mined, and the 63 saved acquisition artifacts carry only each page's OWN URL
plus a Las Vegas promotional carousel. The one binding the recovery did make is
not a route -- it is a DUPLICATE, two census rows for one Plainfield Hampton
Inn sharing a telephone number.

Two things it did recover are worth more than a URL:

  * a WRONG route already sitting in the payable cohort -- a bare "Comfort
    Suites" row pointed at an Econo Lodge city-search page in Shelbyville.
    Buying that would have fetched another brand's building.
  * two rows that were never mis-routed at all, freed by the street-agreement
    fix in ``policy_surface.streets_agree``.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import indianapolis_recovery_005 as R005          # noqa: E402
from scripts.pettripfinder.acquisition import paid_attempt_ledger as PAL     # noqa: E402
from scripts.pettripfinder.acquisition import registry as REGISTRY           # noqa: E402
from scripts.pettripfinder.acquisition.market_paid_acquisition import family_of  # noqa: E402
from scripts.pettripfinder.brightdata import corpus as CORPUS                # noqa: E402
from scripts.pettripfinder.cincinnati_url_routing_progress_001 import brand_of  # noqa: E402
from scripts.pettripfinder.discovery import census_url_recovery as URC       # noqa: E402

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
SCHEMA = "ptf-market-url-recovery-report/1.0"
WORK_ORDER = "PTF-INDIANAPOLIS-OFFICIAL-URL-RECOVERY-006"
MARKET = "indianapolis-in"
TARGET = 50

#: Rows the street-agreement fix un-blocks. Their route was always correct; what
#: changed is that the identity gate can now read the two spellings as one
#: address. That is a reader capability that post-dates the prior attempt, which
#: is one of the five reasons the paid ledger permits a second purchase.
FREED_BY_STREET_RULE = {
    "courtyard by marriott indianapolis northwest":
        "the page wrote '7226 Woodland Drive at 71st Street' and the census "
        "holds '7226 Woodland Drive'; policy_surface.streets_agree now reads a "
        "cross street after a complete address as the same building",
    "days inn by wyndham plainfield":
        "the page wrote '2245 East Perry Road' and the census holds "
        "'2245 Perry Road'; a directional stated on one side and omitted on "
        "the other is no longer a conflict",
}


def _load(name):
    return json.loads((LP / name).read_text(encoding="utf-8"))


def _host(url: str) -> str:
    return re.sub(r"^https?://(www\.)?", "", url or "").split("/")[0].lower()


def build(recovery_sweep: Dict) -> Dict:
    """``recovery_sweep`` is the output of ``census_url_recovery`` run over the
    current census with every evidence source this market owns."""
    audit = R005.build()
    ledger = _load("ptf_paid_attempt_ledger_001.json")
    census = _load("identity_census/indianapolis-in.json")
    package = _load("hotel_policy_facts_indianapolis-in.json")
    exclusions = _load("markets/authority/indianapolis-in/hotel_exclusions.json")
    merged = _load("indianapolis_in_acquisition_merged_promotion_003.json")

    key_map = census["promotion"]["key_map"]
    signed = ({h["identity_key"] for h in package["hotels"]}
              | {e["normalized_name"] for e in exclusions["exclusions"]})
    attempted = {key_map.get(r["identity_key"], r["identity_key"])
                 for r in merged["results"]}
    by_key = {h["identity_key"]: h for h in census["hotels"]}
    already = {r["identity_key"]
               for r in audit["phase_3_zero_cost_recovery"]["recoveries"]}

    unroutable = [h for h in census["hotels"]
                  if h["identity_key"] not in signed
                  and h["identity_key"] not in attempted
                  and not (h.get("official_url") or "").strip()
                  and h["identity_key"] not in already]

    # ------------------------------------------------------------- phase 1
    def stated(rows, field):
        return sum(1 for h in rows if (h.get(field) or "").strip())

    families = Counter(brand_of(h["canonical_name"]) for h in unroutable)
    phase1 = OrderedDict((
        ("unroutable_identities", len(unroutable)),
        ("by_family", OrderedDict(sorted(families.items(),
                                         key=lambda kv: (-kv[1], kv[0])))),
        ("identifying_data", OrderedDict((
            ("with_street", stated(unroutable, "address")),
            ("with_postal_code", stated(unroutable, "postal_code")),
            ("with_city", stated(unroutable, "city")),
            ("with_telephone", stated(unroutable, "phone")),
            ("with_a_prior_census_alias",
             sum(1 for h in unroutable if h.get("prior_census_identity_keys"))),
            ("with_a_known_property_code", 0),
        ))),
        ("deterministic_property_code_recovery_available", False),
        ("why", "a brand URL can only be BUILT from a property code, and not "
                "one of these rows carries one: every row came from "
                "OpenStreetMap with a name, a street and a postal code. Only 5 "
                "state a telephone, which is the strongest binding key. "
                "Guessing a brand slug from a name is not recovery -- it is the "
                "failure this market already produced once, a Comfort Suites "
                "row pointed at an Econo Lodge city-search page."),
        ("rows", [OrderedDict((
            ("identity_key", h["identity_key"]),
            ("canonical_name", h["canonical_name"]),
            ("family", brand_of(h["canonical_name"])),
            ("street", h.get("address") or ""), ("city", h.get("city") or ""),
            ("postal_code", h.get("postal_code") or ""),
            ("telephone", h.get("phone") or ""),
            ("prior_census_aliases", list(h.get("prior_census_identity_keys") or ())),
        )) for h in unroutable]),
    ))

    # ------------------------------------------------------------- phase 2
    new_routes, duplicates = [], []
    for rec in recovery_sweep.get("recoveries", []):
        key = rec["identity_key"]
        if key in signed or key in attempted or key in already:
            continue
        holder = next((h["identity_key"] for h in census["hotels"]
                       if h["identity_key"] != key
                       and (h.get("official_url") or "").strip()
                       and _host(h["official_url"]) == _host(rec["recovered_url"])
                       and h["official_url"].rstrip("/").lower()
                       == rec["recovered_url"].rstrip("/").lower()), "")
        if holder:
            duplicates.append(OrderedDict((
                ("identity_key", key), ("collides_with", holder),
                ("shared_url", rec["recovered_url"]),
                ("binding", rec["binding"]),
                ("why", "the recovery bound this row to a URL another census row "
                        "already holds. Two rows for one page is a duplicate "
                        "identity, not a new route."),
            )))
        else:
            new_routes.append(rec)

    phase2 = OrderedDict((
        ("evidence_consulted", OrderedDict((
            ("discovery_cache_providers", ["OPENSTREETMAP"]),
            ("prior_census_rows_with_a_url", 33),
            ("prior_build_reports_read",
             len(recovery_sweep.get("artifact_coverage", {}).get("artifacts_read", []))),
            ("saved_acquisition_artifacts_scanned", 63),
            ("first_party_urls_found_in_those_artifacts", 69),
            ("of_those_not_already_in_the_census", 17),
            ("of_those_actually_in_this_market", 7),
        ))),
        ("binding_keys_offered", recovery_sweep.get("binding_keys_offered")),
        ("binding_counts", recovery_sweep.get("binding_counts")),
        ("street_binding_added", 0),
        ("net_new_routes", len(new_routes)),
        ("duplicates_found_instead", len(duplicates)),
        ("duplicates", duplicates),
        ("new_routes", new_routes),
        ("why_nothing_more_is_available",
         "the saved acquisition artifacts carry each page's OWN url and a Las "
         "Vegas promotional carousel, not sibling Indianapolis properties; the "
         "five genuinely new IHG codes in them name a brand and a city but no "
         "street or postal code, and three to five same-brand rows sit in each "
         "of those cities. Binding on a shared name token is the one thing this "
         "market has already been burned by."),
    ))

    # ------------------------------------------------------------- phase 5
    rows_005 = audit["phase_5_payable"]["rows"]
    dropped, cohort = [], []
    for row in rows_005:
        ok, why = URC.url_names_the_property(row["canonical_name"],
                                             row["source_url"])
        host = _host(row["source_url"])
        brand_host = CORPUS.brand_of(row["source_url"])
        name_brand = brand_of(row["canonical_name"])
        wrong_brand = (name_brand == "choice" and "econo" in row["source_url"])
        if not ok and wrong_brand:
            dropped.append(OrderedDict((
                ("identity_key", row["identity_key"]),
                ("canonical_name", row["canonical_name"]),
                ("url", row["source_url"]), ("host", host),
                ("why", "the census URL is a %s city-search page for a "
                        "different brand; a paid fetch would buy another "
                        "building. %s" % (host, why)),
            )))
            continue
        cohort.append({k: v for k, v in row.items() if k != "paid_history"})

    for key, why in sorted(FREED_BY_STREET_RULE.items()):
        hotel = by_key.get(key_map.get(key, key)) or by_key.get(key)
        if not hotel:
            continue
        url = (hotel.get("official_url") or "").strip()
        if not url:
            continue
        cohort.append(OrderedDict((
            ("identity_key", key), ("canonical_name", hotel["canonical_name"]),
            ("source_url", url), ("brand", CORPUS.brand_of(url)),
            ("provider", REGISTRY.resolve(brand=CORPUS.brand_of(url), url=url,
                                          identity_key=key).provider),
            ("basis", "freed_by_street_agreement_rule"),
            ("street", hotel.get("address") or ""),
            ("postal_code", hotel.get("postal_code") or ""),
            ("telephone", hotel.get("phone") or ""),
        )))

    # Two cohort rows on one page is the failure this market has already
    # produced twice. Paying for it twice is the smaller half of the damage;
    # the larger half is publishing one building's pet policy under the other's
    # name. A row is kept only when the URL names it MORE completely than every
    # rival AND each rival carries a distinctive word the URL does not.
    shared: Dict[str, List[Dict]] = {}
    for row in cohort:
        shared.setdefault(row["source_url"].rstrip("/").lower(), []).append(row)
    keep, dropped_shared = [], []
    for url, group in shared.items():
        if len(group) == 1:
            keep.append(group[0])
            continue
        scored = []
        for row in group:
            tokens = URC.distinctive_name_tokens(row["canonical_name"])
            present = [t for t in tokens if t in url]
            scored.append((len(present), [t for t in tokens if t not in url], row))
        scored.sort(key=lambda s: -s[0])
        best, rest = scored[0], scored[1:]
        decisive = (best[0] > rest[0][0]) and all(missing for _, missing, _ in rest)
        if decisive:
            keep.append(best[2])
            for _, missing, row in rest:
                dropped_shared.append(OrderedDict((
                    ("identity_key", row["identity_key"]),
                    ("canonical_name", row["canonical_name"]),
                    ("url", row["source_url"]),
                    ("kept_instead", best[2]["identity_key"]),
                    ("why", "two census rows carry this one page. The URL names "
                            "%r and never says %s, so this row is routed to its "
                            "sibling's page."
                            % (best[2]["canonical_name"], ", ".join(repr(m) for m in missing))),
                )))
        else:
            # The distinctive-token vocabulary cannot separate them -- for the
            # Hyatt pair it treats "house" as a generic word, so the House row
            # has no token the URL lacks and nothing affirmatively says it is
            # mis-routed. The page's own slug is quoted here so the founder can
            # see the discriminating fact at a glance, but naming a sub-brand
            # winner is a ruling and this refuses to make it. Holding both is
            # the safe direction: a wrongly-kept row publishes the neighbour's
            # policy under this hotel's name.
            slug = url.rstrip("/").rsplit("/", 2)[-2] if "/" in url else url
            for _, _, row in scored:
                dropped_shared.append(OrderedDict((
                    ("identity_key", row["identity_key"]),
                    ("canonical_name", row["canonical_name"]),
                    ("url", row["source_url"]), ("kept_instead", ""),
                    ("why", "two census rows carry this one page. The page's own "
                            "slug is %r; neither row may be bought until the "
                            "founder says which hotel it is." % slug),
                )))
    cohort = keep

    for row in cohort:
        row["family"] = family_of(row["brand"])

    material = {k: {"reason": PAL.MATERIAL_CAPABILITY_CHANGED, "detail": v}
                for k, v in FREED_BY_STREET_RULE.items()}
    for row in cohort:
        if row["basis"] == "routing_repaired":
            material[row["identity_key"]] = {
                "reason": PAL.MATERIAL_ROUTING_REPAIR,
                "detail": "the dead legacy URL was replaced with the canonical "
                          "short-code form"}
    payable, suppressed = PAL.suppress(cohort, ledger, material_changes=material)

    before = audit["phase_5_payable"]["payable"]
    phase5 = OrderedDict((
        ("routing_before", before),
        ("dropped_wrong_route", len(dropped)),
        ("dropped", dropped),
        ("dropped_shared_page", len(dropped_shared)),
        ("shared_page_conflicts", dropped_shared),
        ("added_by_street_rule", len(FREED_BY_STREET_RULE)),
        ("cohort", len(cohort)),
        ("payable", len(payable)),
        ("suppressed_by_paid_history", len(suppressed)),
        ("suppressed_reasons", OrderedDict(sorted(Counter(
            r["paid_history"]["decision"] for r in suppressed).items()))),
        ("street_rule_rows_still_suppressed",
         sorted(r["identity_key"] for r in suppressed
                if r["identity_key"] in FREED_BY_STREET_RULE)),
        ("why_the_freed_rows_are_still_suppressed",
         "the ledger tests routing_repair_required BEFORE it tests a capability "
         "change, so a reader improvement cannot clear a row whose prior attempt "
         "ended IDENTITY_MISMATCH. That ordering is right in the general case -- "
         "a mismatch usually means the URL fetched somebody else's building, and "
         "re-buying the same wrong page is exactly the waste this ledger exists "
         "to stop. Here the URL was never wrong and the gate was, but only a "
         "person can assert that difference, so these two need a named "
         "OPERATOR_OVERRIDE (or a documented routing repair) before they may be "
         "re-bought. They are NOT counted as payable."),
        ("routing_after", len(payable)),
        ("by_provider", OrderedDict(sorted(
            Counter(r["provider"] for r in payable).items()))),
        ("by_basis", OrderedDict(sorted(
            Counter(r["basis"] for r in payable).items()))),
        ("rows", payable),
    ))

    return OrderedDict((
        ("schema", SCHEMA), ("market_id", MARKET), ("work_order", WORK_ORDER),
        ("nothing_was_fetched", True), ("usd_spent", 0.0), ("network_calls", 0),
        ("current", audit["current"]),
        ("phase_1_unroutable_inventory", phase1),
        ("phase_2_zero_cost_routing", phase2),
        ("phase_3_street_rule", OrderedDict((
            ("implemented_in", "scripts/pettripfinder/brightdata/policy_surface.py"
                               "::streets_agree"),
            ("shared_with", "scripts/pettripfinder/brightdata/marriott_surface.py"),
            ("widenings", ["a cross street after a complete address",
                           "a directional stated on one side and omitted on the other"]),
            ("still_refused", ["a different house number",
                               "two different directionals",
                               "a different street name",
                               "any other trailing suffix"]),
            ("rows_freed", sorted(FREED_BY_STREET_RULE)),
        ))),
        ("phase_5_routing_rerun", phase5),
    ))


def cost_plan(report: Dict) -> Dict:
    from scripts.pettripfinder.acquisition import cohort_cost_plan as CP
    ledger = _load("ptf_paid_attempt_ledger_001.json")
    prior = _load("indianapolis_in_market_acquisition_pass1_002.json")
    cohort = [{k: v for k, v in r.items() if k != "paid_history"}
              for r in report["phase_5_routing_rerun"]["rows"]]
    plan = CP.build({"cohort": cohort}, prior, authorised_cap_usd=0.0,
                    paid_ledger=ledger,
                    available_lanes=("brightdata_browser",
                                     "brightdata_web_unlocker", "firecrawl"))
    merged = _load("indianapolis_in_acquisition_merged_promotion_003.json")
    attempted = len({r["identity_key"] for r in merged["results"]})
    promoted = report["current"]["promoted_pet_friendly"]
    pf_rate = promoted / attempted if attempted else 0.0
    payable = report["phase_5_routing_rerun"]["payable"]
    expected = int(round(payable * pf_rate))
    return OrderedDict((
        ("schema", "ptf-market-recovery-cost-plan/1.0"), ("market_id", MARKET),
        ("work_order", WORK_ORDER), ("this_is_not_an_authorization", True),
        ("authorised_cap_usd_minor", 0),
        ("cohort_size", plan["cohort_size"]),
        ("cohort_by_provider", plan["cohort_by_provider"]),
        ("cohort_by_family", plan["cohort_by_family"]),
        ("dollar_billed_properties", plan["dollar_billed_properties"]),
        ("credit_billed_properties", plan["credit_billed_properties"]),
        ("measured_unit_usd_minor", plan["measured_unit_usd_minor"]),
        ("lanes", plan["lanes"]),
        ("expected_firecrawl_credits", plan["expected_firecrawl_credits"]),
        ("expected_brightdata_usd_minor", plan["expected_brightdata_usd_minor"]),
        ("projection", plan["projection"]),
        ("safe_cap_usd_minor", int(plan["projection"]["worst_case_usd_minor"]) + 15),
        ("yield_projection", OrderedDict((
            ("observed_pet_friendly_rate", round(pf_rate, 4)),
            ("payable_cohort", payable),
            ("expected_new_pet_friendly", expected),
            ("expected_total_pet_friendly", promoted + expected),
            ("target", TARGET),
            ("still_needed", max(0, TARGET - promoted - expected)),
            ("payable_properties_required_at_this_rate",
             int(round((TARGET - promoted) / pf_rate)) if pf_rate else None),
            ("verdict", "REACHABLE" if promoted + expected >= TARGET
                        else "NOT_REACHABLE_FROM_THE_CURRENT_PAYABLE_POOL"),
            ("what_would_change_it",
             "routing the %d identities that still name no website. That is a "
             "discovery purchase (a places/details lookup per row), not a "
             "policy-acquisition purchase, and it is the only lever that moves "
             "this number."
             % report["phase_1_unroutable_inventory"]["unroutable_identities"]),
        ))),
    ))


def exceptions(report: Dict) -> Dict:
    """Carried forward from 005, plus what 006 found. Rulings are the founder's."""
    rows = list(_load("indianapolis_in_recovery_founder_packet_005.json")["rows"])
    for dup in report["phase_2_zero_cost_routing"]["duplicates"]:
        rows.append(OrderedDict((
            ("identity_key", dup["identity_key"]),
            ("kind", "DUPLICATE_OR_IDENTITY_CONFLICT"),
            ("proposes", "NO_CHANGE_WITHOUT_A_RULING"),
            ("evidence", "shares %s with %r; bound on %s"
                         % (dup["shared_url"], dup["collides_with"], dup["binding"])),
            ("artifact", ""),
            ("why_it_is_an_exception", dup["why"]),
        )))
    for bad in report["phase_5_routing_rerun"]["dropped"]:
        rows.append(OrderedDict((
            ("identity_key", bad["identity_key"]),
            ("kind", "WRONG_ROUTE_IN_THE_CENSUS"),
            ("proposes", "CLEAR_THE_URL_AND_LEAVE_THE_ROW_UNROUTED"),
            ("evidence", bad["url"]), ("artifact", ""),
            ("why_it_is_an_exception", bad["why"]),
        )))
    rows.append(OrderedDict((
        ("identity_key", "hyatt house indianapolis downtown"),
        ("kind", "DUPLICATE_OR_IDENTITY_CONFLICT"),
        ("proposes", "NO_CHANGE_WITHOUT_A_RULING"),
        ("evidence", "shares hyatt.com/.../indzi with 'hyatt place indianapolis "
                     "downtown' at 130 South Pennsylvania Street, same telephone"),
        ("artifact", ""),
        ("why_it_is_an_exception",
         "indzi is the Hyatt PLACE code. Two hotels share one building and one "
         "switchboard, and the census gave both the Place's URL, so the House "
         "has no route of its own. A dual-brand building is exactly where a "
         "shared address must not decide identity."),
    )))
    return OrderedDict((
        ("schema", "ptf-founder-review-packet/1.0"), ("market_id", MARKET),
        ("work_order", WORK_ORDER), ("status", "EXCEPTIONS_ONLY"),
        ("nothing_is_published_by_this_file",
         "This packet proposes. It signs no row and publishes nothing."),
        ("auto_accepted", 0), ("exceptions", len(rows)),
        ("by_kind", OrderedDict(sorted(Counter(r["kind"] for r in rows).items()))),
        ("rows", rows),
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sweep", required=True,
                        help="census_url_recovery output over the current census")
    parser.add_argument("--out", default="")
    parser.add_argument("--plan-out", default="")
    parser.add_argument("--packet-out", default="")
    args = parser.parse_args(argv)
    sweep = json.loads(Path(args.sweep).read_text(encoding="utf-8"))
    report = build(sweep)
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.plan_out:
        Path(args.plan_out).write_text(json.dumps(cost_plan(report), indent=2),
                                       encoding="utf-8")
    if args.packet_out:
        Path(args.packet_out).write_text(json.dumps(exceptions(report), indent=2),
                                         encoding="utf-8")
    p1 = report["phase_1_unroutable_inventory"]
    p2 = report["phase_2_zero_cost_routing"]
    p5 = report["phase_5_routing_rerun"]
    print("unroutable            %d" % p1["unroutable_identities"])
    print("net new routes        %d" % p2["net_new_routes"])
    print("duplicates found      %d" % p2["duplicates_found_instead"])
    print("routing before        %d" % p5["routing_before"])
    print("dropped wrong route   %d" % p5["dropped_wrong_route"])
    print("added by street rule  %d" % p5["added_by_street_rule"])
    print("routing after         %d" % p5["routing_after"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
