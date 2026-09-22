"""PTF-WEST-PALM-BEACH-FL-HARDENED-SOURCE-READY-001 -- Phase 2: reuse the South Florida DISCOVERY intelligence.

TWO prior markets looked into Palm Beach County deliberately and refused every row they found:

  * miami-fl (market #31, live) drew its observation box wide enough to classify the county's southern edge.
  * fort-lauderdale-fl (market #32, live) ran an explicit Palm Beach boundary audit: its DBPR lane counted
    222 Palm Beach County hotel-rank licences and its graph refused 192 Palm Beach nodes by place, naming
    `west-palm-beach-fl` as a FUTURE STANDALONE market in the process.

Every one of those rows is classified OUTSIDE_MARKET in its own market's committed graph, which is exactly why
their identity intelligence is safe to reuse and their policy is not there to reuse at all.

WHAT IS REUSED, AND WHAT IS NOT
--------------------------------
REUSED (identity and routing intelligence, revalidated here):
  * the identity key, canonical name and every alias the prior hard-key merge proved
  * the premises as those markets recorded it: street, city, ZIP, phone
  * brand property codes and official routes those markets' brand lanes bound
  * map pins (OSM), competitor leads and destination-roster associations
  * the lane history: which lanes had already SEEN this identity, and each market's own ruling on it

NOT REUSED (never imported as authority):
  * MEMBERSHIP. Every row is re-classified here by THIS market's corridor registry over the property's own
    postal code. A prior "OUTSIDE_MARKET" ruling is recorded as provenance, never as an admission or a refusal.
  * PET POLICY. No policy fact, quote, evidence row or capture is imported from either market. Both published
    nothing for any Palm Beach row -- every one is POLICY_NOT_VERIFIED there -- which this helper ASSERTS
    rather than assumes, and fails loudly if it is ever untrue.
  * LODGING QUALIFICATION. Prior IDENTITY_REVIEW / NON_LODGING rulings are carried as PRIOR RULINGS for this
    market's reconciliation to consider on its own evidence; they decide nothing here.

The census lanes run independently and in full: this index is a cross-check and a provenance source, never a
substitute for discovery. A row that only a prior market saw is a LEAD that this market's own lanes must still
confirm.

Outputs:
  launch_packages/pettripfinder/markets/reports/west_palm_beach_fl_south_florida_reuse_001.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import west_palm_beach_fl_geography_001 as GEO  # noqa: E402

WORK_ORDER = "PTF-WEST-PALM-BEACH-FL-HARDENED-SOURCE-READY-001"
MARKET_ID = "west-palm-beach-fl"
REPORTS = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports")
OUT = os.path.join(REPORTS, "west_palm_beach_fl_south_florida_reuse_001.json")

#: (report file, source market id, source work order, human label)
SOURCES = [
    ("miami_fl_census_reconciliation_001.json", "miami-fl", "PTF-MIAMI-FL-HARDENED-SOURCE-READY-001", "MIAMI"),
    ("fort_lauderdale_fl_census_reconciliation_001.json", "fort-lauderdale-fl",
     "PTF-FORT-LAUDERDALE-FL-HARDENED-SOURCE-READY-001", "FORT_LAUDERDALE"),
]

#: Policy states a refused row is allowed to carry. Anything else means a prior market DID verify a policy for a
#: Palm Beach premises, and this helper must stop rather than silently inherit it.
ALLOWED_POLICY_STATES = {"", "POLICY_NOT_VERIFIED", "UNKNOWN", "NOT_VERIFIED", None}


def _s(v):
    return " ".join(str(v or "").split())


def _zip5(v):
    return "".join(ch for ch in _s(v) if ch.isdigit())[:5]


def _street_key(street):
    return " ".join(_s(street).lower().replace(".", " ").replace(",", " ").split())


def build():
    admitted = set()
    for c in GEO.CORRIDORS:
        admitted.update(c[5])

    per_source = OrderedDict()
    index = OrderedDict()          # identity_key -> merged lead
    policy_violations = []
    for fname, src_market, src_order, label in SOURCES:
        path = os.path.join(REPORTS, fname)
        doc = json.load(open(path, encoding="utf-8"))
        if doc.get("market_id") != src_market:
            raise SystemExit("%s does not belong to %s" % (fname, src_market))
        rows = doc.get("rows") or []
        hits, rulings = [], Counter()
        for r in rows:
            z = _zip5(r.get("postal_code"))
            if z not in admitted:
                continue
            ps = r.get("policy_state")
            if ps not in ALLOWED_POLICY_STATES:
                policy_violations.append(OrderedDict([
                    ("source_market", src_market), ("identity_key", r.get("identity_key")),
                    ("postal_code", z), ("policy_state", ps)]))
            rulings[_s(r.get("classification")) or "UNCLASSIFIED"] += 1
            hits.append(r)
            key = _s(r.get("identity_key")).lower()
            lead = index.get(key)
            if lead is None:
                lead = OrderedDict([
                    ("identity_key", r.get("identity_key")),
                    ("canonical_name", r.get("canonical_name")),
                    ("aliases", []),
                    ("street", r.get("street")), ("city", r.get("city")), ("state", r.get("state")),
                    ("postal_code", z), ("phone", r.get("phone")),
                    ("brand", r.get("brand")), ("brand_property_code", r.get("property_code")),
                    ("official_url", r.get("official_url")),
                    ("latitude", r.get("latitude")), ("longitude", r.get("longitude")),
                    ("prior_lanes", []), ("prior_rulings", []), ("seen_by", []),
                ]
                )
                index[key] = lead
            for a in (r.get("identity_key_aliases") or []):
                if a and a not in lead["aliases"]:
                    lead["aliases"].append(a)
            for fld, val in (("street", r.get("street")), ("city", r.get("city")), ("phone", r.get("phone")),
                             ("brand", r.get("brand")), ("brand_property_code", r.get("property_code")),
                             ("official_url", r.get("official_url")), ("latitude", r.get("latitude")),
                             ("longitude", r.get("longitude"))):
                if not lead.get(fld) and val:
                    lead[fld] = val
            for ln in (r.get("lanes") or []):
                if ln not in lead["prior_lanes"]:
                    lead["prior_lanes"].append(ln)
            lead["prior_rulings"].append(OrderedDict([
                ("source_market", src_market), ("classification", r.get("classification")),
                ("classification_reason", r.get("classification_reason")),
                ("policy_state", r.get("policy_state")),
            ]))
            if label not in lead["seen_by"]:
                lead["seen_by"].append(label)

        per_source[src_market] = OrderedDict([
            ("source_work_order", src_order),
            ("source_report", fname),
            ("source_graph_nodes", len(rows)),
            ("nodes_in_west_palm_beach_admitted_postal_codes", len(hits)),
            ("their_rulings_on_those_nodes", OrderedDict(rulings.most_common())),
            ("policy_rows_importable", 0),
        ])

    if policy_violations:
        raise SystemExit("a prior market carries a VERIFIED policy for a Palm Beach premises; reuse refused:\n%s"
                         % json.dumps(policy_violations[:10], indent=1))

    leads = list(index.values())
    for lead in leads:
        klass, slug, why = GEO.classify_postal(lead["postal_code"], lead.get("city") or "")
        lead["this_market_corridor"] = slug
        lead["this_market_class"] = klass
        lead["this_market_reason"] = why
        lead["membership_decided_here"] = True

    by_corridor = Counter(l["this_market_corridor"] for l in leads if l["this_market_corridor"])
    both = [l for l in leads if len(l["seen_by"]) > 1]
    report = OrderedDict([
        ("schema", "ptf-prior-discovery-reuse/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("phase", "2 -- reuse the retained South Florida discovery intelligence from the two LIVE markets that "
                  "looked into Palm Beach County and refused it"),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", 0),
        ("what_is_reused",
         "Identity and routing intelligence only: identity keys and aliases, the premises as a prior market "
         "recorded it, brand property codes, official routes, map pins and lane history."),
        ("what_is_never_reused",
         "Membership (re-decided here by this market's corridor registry over the property's own postal code), "
         "pet policy (none exists to import -- asserted below), and lodging qualification."),
        ("policy_import_assertion", OrderedDict([
            ("assertion", "No prior-market row inside a West Palm Beach admitted postal code carries a verified "
                          "pet policy. Checked row by row; the helper aborts if it is ever untrue."),
            ("violations_found", 0),
            ("policy_rows_imported", 0),
        ])),
        ("membership_assertion",
         "Every reused lead was re-classified by GEO.classify_postal on its OWN postal code. A prior market's "
         "OUTSIDE_MARKET ruling is provenance and never an admission."),
        ("per_source", per_source),
        ("deduped_south_florida_identities_reused", len(leads)),
        ("seen_by_both_markets", len(both)),
        ("with_a_brand_property_code", sum(1 for l in leads if l.get("brand_property_code"))),
        ("with_an_official_url", sum(1 for l in leads if l.get("official_url"))),
        ("with_coordinates", sum(1 for l in leads if l.get("latitude"))),
        ("with_a_phone", sum(1 for l in leads if l.get("phone"))),
        ("by_this_market_corridor", OrderedDict(sorted(by_corridor.items()))),
        ("by_this_market_class", OrderedDict(Counter(l["this_market_class"] for l in leads).most_common())),
        ("leads", leads),
    ])
    return report


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    report = build()
    if args.write:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(report, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        print("WROTE", os.path.relpath(OUT, _DASH))
    print("reused=%d  seen_by_both=%d  brand_codes=%d  urls=%d  coords=%d  policy_imported=%d" % (
        report["deduped_south_florida_identities_reused"], report["seen_by_both_markets"],
        report["with_a_brand_property_code"], report["with_an_official_url"], report["with_coordinates"],
        report["policy_import_assertion"]["policy_rows_imported"]))
    for mid, blk in report["per_source"].items():
        print("  %-20s %d nodes -> %d in admitted codes" % (
            mid, blk["source_graph_nodes"], blk["nodes_in_west_palm_beach_admitted_postal_codes"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
