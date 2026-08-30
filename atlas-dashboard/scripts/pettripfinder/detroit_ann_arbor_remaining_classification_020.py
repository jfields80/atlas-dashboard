# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-FREE-ATTENDED-PASS-020, Phase 10.

Rebuilds the classification of everything Detroit still has not resolved, and
breaks the paid-lane remainder down BY FAMILY so a free probe can be
recommended where a family has now succeeded on attended Chrome.

THE CLASSIFICATION IS RE-DERIVED FROM CURRENT STATE, NOT CARRIED FORWARD.
Order 019 produced its counts while it was applying authority; this pass has
since resolved nothing but has proved a lane, and a stale label would recommend
paying for pages a free tool can now open.

A FAMILY THAT HAS NEVER BEEN FREE-TESTED IS NOT 'PAID-QUALIFIED'. It is
UNMEASURED. The distinction matters: this market's whole 013-018 sequence was
justified by families that genuinely refuse anonymous fetches, which is a
finding, not a default.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from urllib.parse import urlsplit

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-FREE-ATTENDED-PASS-020"
AS_OF = "2026-08-30"
BD_USD_PER_ATTEMPT = 0.0871

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
OUT = LP / "detroit_ann_arbor_remaining_classification_020.json"

#: Families this market has PROVED refuse an anonymous fetch, by spending on
#: them across orders 008-018. A remaining row on one of these is genuinely
#: paid-qualified.
PROVEN_PAID_ONLY = {
    "marriott.com": "Marriott", "hilton.com": "Hilton", "ihg.com": "IHG",
    "choicehotels.com": "Choice", "wyndhamhotels.com": "Wyndham",
}

#: Families attended Chrome has now opened successfully in this market.
PROVEN_FREE = set()


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_lf(path, doc):
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


def registrable(url):
    host = (urlsplit(url or "").hostname or "").lower()
    parts = [part for part in host.split(".") if part]
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def run():
    census = {row["identity_key"]: row for row in
              load(LP / "identity_census" / ("%s.json" % MARKET))["hotels"]}
    routing = load(LP / "markets" / "authority" / MARKET
                   / "identity_routing.json")["routes"]
    routes = {route["hotel_ref"]["identity_key"]: route for route in routing}
    published = {row["identity_key"] for row in
                 load(LP / ("hotel_policy_facts_%s.json" % MARKET))["hotels"]}
    excluded = {row["normalized_name"] for row in
                load(LP / "markets" / "authority" / MARKET
                     / "hotel_exclusions.json")["exclusions"]}
    ledger = load(LP / "ptf_paid_attempt_ledger_001.json")
    paid_attempted = {attempt["identity_key"] for attempt in ledger["attempts"]
                      if attempt.get("market_id") == MARKET}

    triage = load(LP / "detroit_ann_arbor_attended_triage_020.json")
    free_worked, free_succeeded = {}, {}
    for row in triage["results"]:
        free_worked[row["identity_key"]] = row["outcome"]
        if row["outcome"] != "IDENTITY_MISMATCH":
            PROVEN_FREE.add(row["host"])
        if row["triage"].startswith("CLEAN_"):
            free_succeeded[row["identity_key"]] = row["host"]
    embassy_key = triage["recapture"]["identity_key"]
    free_worked[embassy_key] = "PUBLICATION_CANDIDATE_PENDING_FOUNDER"
    PROVEN_FREE.add("hilton.com")

    unresolved = sorted(set(census) - published - excluded)
    rows = []
    for key in unresolved:
        crow = census[key]
        route = routes.get(key)
        confirmed = bool(route) and route["status"] == "ROUTING_CONFIRMED"
        url = (route or {}).get("official_property_url") or ""
        host = registrable(url)
        placeable = bool((crow.get("address") or "").strip())

        if key in free_worked and free_worked[key] in (
                "PUBLICATION_CANDIDATE", "PUBLICATION_CANDIDATE_PENDING_FOUNDER",
                "HOLD"):
            cls, why = ("AWAITING_FOUNDER_RULING",
                        "worked free this pass; sits in the packet")
        elif free_worked.get(key) == "IDENTITY_MISMATCH":
            cls, why = ("ROUTING_REPAIR_FIRST",
                        "the routed domain no longer serves this hotel")
        elif free_worked.get(key) == "POLICY_NOT_FOUND":
            cls, why = ("SOURCE_SILENT",
                        "reached and swept at $0; the site publishes no pet "
                        "policy. No provider can buy a policy that was never "
                        "written.")
        elif not confirmed:
            cls, why = ("ROUTING_REPAIR_FIRST", "no confirmed route")
        elif not placeable:
            cls, why = ("IDENTITY_REVIEW_FIRST",
                        "the census cannot place this property")
        elif host in PROVEN_PAID_ONLY:
            cls, why = ("BRIGHTDATA_QUALIFIED",
                        "%s -- this market has PROVEN this family refuses an "
                        "anonymous fetch" % PROVEN_PAID_ONLY[host])
        elif host in PROVEN_FREE:
            cls, why = ("FREE_ATTENDED_QUALIFIED",
                        "attended Chrome has already opened this host in this "
                        "market at $0")
        elif host:
            cls, why = ("FREE_ATTENDED_UNTESTED",
                        "first-party domain, never free-tested and never paid "
                        "for -- probe free before costing it")
        else:
            cls, why = ("UNPROVEN", "no usable first-party URL")

        rows.append(OrderedDict([
            ("identity_key", key),
            ("canonical_name", crow.get("canonical_name") or ""),
            ("city", crow.get("city") or ""),
            ("host", host),
            ("classification", cls),
            ("why", why),
            ("previously_paid_attempted", key in paid_attempted),
            ("worked_free_this_pass", key in free_worked),
        ]))

    counts = Counter(row["classification"] for row in rows)
    families = OrderedDict()
    for row in rows:
        if row["classification"] not in ("BRIGHTDATA_QUALIFIED",
                                         "FREE_ATTENDED_QUALIFIED",
                                         "FREE_ATTENDED_UNTESTED"):
            continue
        fam = families.setdefault(row["host"] or "(none)", OrderedDict([
            ("host", row["host"] or "(none)"), ("rows", 0),
            ("classification", row["classification"]),
            ("free_success_in_this_market", row["host"] in PROVEN_FREE),
            ("recommendation", ""), ("basis", ""),
        ]))
        fam["rows"] += 1

    for fam in families.values():
        if fam["classification"] == "BRIGHTDATA_QUALIFIED":
            fam["recommendation"] = "PAID_LANE"
            fam["basis"] = ("this market spent on this family and established "
                            "it does not answer an anonymous fetch")
        elif fam["free_success_in_this_market"]:
            fam["recommendation"] = "FREE_PROBE"
            fam["basis"] = ("attended Chrome has already succeeded on this "
                            "host here")
        else:
            fam["recommendation"] = "FREE_PROBE"
            fam["basis"] = ("never free-tested and never paid for. This pass "
                            "opened every independent it tried at $0, so the "
                            "default should be a free probe, not a purchase.")

    free_probe = [fam for fam in families.values()
                  if fam["recommendation"] == "FREE_PROBE"]
    paid = [fam for fam in families.values()
            if fam["recommendation"] == "PAID_LANE"]
    paid_rows = sum(fam["rows"] for fam in paid)

    write_lf(OUT, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-remaining-classification/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("provider_calls", 0), ("spend_usd", 0.0),
        ("rebuilt_from_current_state", True),
        ("unresolved_total", len(rows)),
        ("counts", OrderedDict(sorted(counts.items()))),
        ("family_breakdown", list(families.values())),
        ("recommendation", OrderedDict([
            ("free_probe_first", OrderedDict([
                ("families", len(free_probe)),
                ("rows", sum(fam["rows"] for fam in free_probe)),
                ("cost", 0.0),
            ])),
            ("genuinely_paid_qualified", OrderedDict([
                ("families", len(paid)),
                ("rows", paid_rows),
                ("estimated_usd", round(paid_rows * BD_USD_PER_ATTEMPT, 2)),
                ("basis", "the balance-derived Bright Data rate from 013-018"),
            ])),
            ("do_not_buy", OrderedDict([
                ("source_silent", counts.get("SOURCE_SILENT", 0)),
                ("routing_repair_first", counts.get("ROUTING_REPAIR_FIRST", 0)),
                ("identity_review_first",
                 counts.get("IDENTITY_REVIEW_FIRST", 0)),
                ("why", "a paid fetch cannot fix a missing policy, a dead "
                        "domain or an unplaceable identity"),
            ])),
        ])),
        ("rows", rows),
    ]))

    print("=== Phase 10: remaining unresolved, re-classified ===")
    print("  unresolved:", len(rows))
    for name, n in sorted(counts.items()):
        print("   %-30s %d" % (name, n))
    print()
    print("  FAMILY BREAKDOWN of the still-acquirable remainder:")
    for fam in sorted(families.values(),
                      key=lambda f: (-f["rows"], f["host"])):
        print("   %-24s %2d rows  %-12s %s"
              % (fam["host"], fam["rows"], fam["recommendation"],
                 "free success here" if fam["free_success_in_this_market"]
                 else ""))
    print()
    print("  FREE probe first : %d rows across %d families, $0"
          % (sum(f["rows"] for f in free_probe), len(free_probe)))
    print("  Genuinely paid   : %d rows, about $%.2f"
          % (paid_rows, paid_rows * BD_USD_PER_ATTEMPT))
    print("wrote", OUT.name)


if __name__ == "__main__":
    run()
