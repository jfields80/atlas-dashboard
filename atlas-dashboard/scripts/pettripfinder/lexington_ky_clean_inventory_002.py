"""PTF-LEXINGTON-KY-POLICY-ACQUISITION-002 -- clean pending authority.

Consolidates every policy observation this order produced into ONE clean
inventory, with exactly one classification per identity, and recomputes the
shadow market and PROMOTION_READY.

Two lanes fed it:

  FIRECRAWL         10 authorized calls, 10 plan credits, 8 publication grade
  ATTENDED_BROWSER  37 rows bound, including the whole Marriott/Hilton
                    capability wall the previous order could not read

An identity read by BOTH lanes is not counted twice. Where the two lanes agree
that is corroboration and is recorded as such; where they would disagree the
row is demoted to a hold rather than resolved by preferring a lane.

Every clean row carries: identity_key, canonical URL, capture lane,
document/content hash, timestamp, identity signals, the exact quote, the
parsed facts and any withheld facts with reasons.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-LEXINGTON-KY-POLICY-ACQUISITION-002"
MARKET_ID = "lexington-ky"
REPORTS = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports")
ROUTING = os.path.join(REPORTS, "lexington_ky_routing_and_static_capture_001.json")
FIRECRAWL = os.path.join(REPORTS, "lexington_ky_firecrawl_pass_002.json")
ATTENDED = os.path.join(REPORTS, "lexington_ky_attended_policy_pass_002.json")
RECON = os.path.join(REPORTS, "lexington_ky_census_reconciliation_001.json")

CLEAN_PF = "CLEAN_PET_FRIENDLY"
CLEAN_NP = "CLEAN_VERIFIED_NO_PETS"


def rj(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def sha256_artifact(artifact_dir):
    """The sha256 of the rendered document a lane actually kept on disk.

    The Firecrawl provenance block records a content hash per call, but the
    clean inventory must be able to re-derive it from the artifact itself, so
    a reviewer can check the hash against the bytes rather than against a
    number this order wrote down.
    """
    if not artifact_dir:
        return ""
    p = os.path.join(_DASH, artifact_dir.replace("/", os.sep), "rendered.html")
    if not os.path.isfile(p):
        return ""
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def money(v):
    """Firecrawl reports fees in cents; render as USD without inventing a basis."""
    if v is None:
        return None
    try:
        return round(float(v) / 100.0, 2)
    except Exception:  # noqa: BLE001
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", required=True)
    args = ap.parse_args()

    census = {r["identity_key"]: r for r in rj(ROUTING)["identities"]}
    fc = rj(FIRECRAWL)
    att = rj(ATTENDED)
    recon = rj(RECON)

    observations = {}
    conflicts = []

    for r in fc["rows"]:
        pc = r.get("policy_class")
        if pc not in (CLEAN_PF, CLEAN_NP):
            continue
        key = r["identity_key"]
        obs = (r.get("observation") or {})
        ext = obs.get("extraction") or {}
        sig = ((r.get("identity_assessment") or {}).get("signals") or {})
        observations.setdefault(key, []).append(OrderedDict([
            ("lane", "FIRECRAWL"),
            ("policy_class", pc),
            ("canonical_url", r.get("final_url") or r.get("requested_url")),
            ("requested_url", r.get("requested_url")),
            ("content_sha256", sha256_artifact(r.get("artifact_dir"))),
            ("captured_at", fc.get("as_of")),
            ("identity_signals", OrderedDict([
                ("name_on_page", sig.get("name_on_page")),
                ("address_on_page", sig.get("address_on_page")),
                ("postal_code", sig.get("postal_code")),
                ("phone_on_page", sig.get("phone_on_page")),
                ("property_code_on_page", sig.get("property_code_on_page")),
            ])),
            ("exact_quote", " | ".join(
                str((e or {}).get("quote") or (e or {}).get("text") or "")
                for e in (obs.get("evidence") or [])
                if isinstance(e, dict))[:400]),
            ("parsed_facts", OrderedDict([
                ("pets_allowed", ext.get("pets_allowed")),
                ("pet_fee_usd", money(ext.get("pet_fee"))),
                ("max_weight", ext.get("max_weight")),
                ("max_pets", ext.get("max_pets")),
            ])),
            ("withheld_facts", obs.get("withheld_fields") or {}),
            ("publication_grade", obs.get("publication_grade")),
        ]))

    for r in att["bound_rows"]:
        pc = r.get("policy_class")
        if pc not in (CLEAN_PF, CLEAN_NP):
            continue
        key = r["identity_key"]
        observations.setdefault(key, []).append(OrderedDict([
            ("lane", "ATTENDED_BROWSER"),
            ("policy_class", pc),
            ("canonical_url", r["requested_url"]),
            ("requested_url", r["requested_url"]),
            ("content_sha256", r.get("content_sha256") or ""),
            ("captured_at", r.get("captured_at")),
            ("identity_signals", r.get("identity_signals")),
            ("exact_quote", r.get("exact_quote")),
            ("parsed_facts", OrderedDict([
                ("pets_allowed", pc == CLEAN_PF),
                ("pet_fee_usd", None),
                ("max_weight", None),
                ("max_pets", None),
            ])),
            ("withheld_facts", OrderedDict([
                ("pet_fee", "NOT_PARSED_BY_THIS_ORDER -- the quote often states a fee, but "
                            "this order publishes acceptance/refusal only and leaves fee "
                            "parsing to the reader that owns the schema"),
            ])),
            ("publication_grade", OrderedDict([
                ("verdict", "OPERATOR_PROSE_CONFIRMED"),
                ("why", r.get("policy_why")),
            ])),
        ]))

    clean = []
    for key, obs in sorted(observations.items()):
        classes = {o["policy_class"] for o in obs}
        row = census.get(key, {})
        if len(classes) > 1:
            conflicts.append(OrderedDict([
                ("identity_key", key), ("name", row.get("name")),
                ("classes", sorted(classes)),
                ("lanes", [o["lane"] for o in obs]),
                ("resolution", "HELD -- two lanes disagree and this order will not resolve a "
                               "policy conflict by preferring a lane"),
            ]))
            continue
        primary = sorted(obs, key=lambda o: 0 if o["lane"] == "ATTENDED_BROWSER" else 1)[0]
        clean.append(OrderedDict([
            ("identity_key", key),
            ("canonical_name", row.get("name")),
            ("address", row.get("address_line")),
            ("postal_code", row.get("postal_code")),
            ("corridor", row.get("cell_id")),
            ("county", row.get("county")),
            ("brand", row.get("brand")),
            ("policy_class", primary["policy_class"]),
            ("lanes", [o["lane"] for o in obs]),
            ("corroborated_by_second_lane", len(obs) > 1),
            ("evidence", primary),
            ("all_observations", obs if len(obs) > 1 else None),
        ]))

    pf = [c for c in clean if c["policy_class"] == CLEAN_PF]
    npets = [c for c in clean if c["policy_class"] == CLEAN_NP]
    resolved = {c["identity_key"] for c in clean}
    unresolved = [k for k in census if k not in resolved]
    corridors = Counter(c["corridor"] for c in clean)

    by_class = Counter(r["classification"] for r in recon["records"])

    inventory = OrderedDict([
        ("schema", "ptf-clean-pending-authority/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("as_of", args.as_of),
        ("nothing_promoted", True),
        ("excluded_from_this_inventory", [
            "identity holds and unnamed OSM elements",
            "rows outside the market by county polygon",
            "SOURCE_SILENT rows (21c Museum Hotel states nothing about pets on five surfaces)",
            "identity-only and competitor-only evidence",
            "the three Choice properties this order found that the census does not contain",
        ]),
        ("totals", OrderedDict([
            ("clean_pet_friendly", len(pf)),
            ("clean_verified_no_pets", len(npets)),
            ("clean_total", len(clean)),
            ("corroborated_by_two_lanes", len([c for c in clean if c["corroborated_by_second_lane"]])),
            ("cross_lane_conflicts", len(conflicts)),
            ("corridors_covered", len([c for c in corridors if c])),
        ])),
        ("conflicts", conflicts),
        ("clean_rows", clean),
    ])
    with open(os.path.join(REPORTS, "lexington_ky_clean_inventory_002.json"), "w",
              encoding="utf-8") as fh:
        json.dump(inventory, fh, indent=1)
        fh.write("\n")

    shadow = OrderedDict([
        ("schema", "ptf-shadow-market/2.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("as_of", args.as_of),
        ("supersedes", "lexington_ky_shadow_market_001.json"),
        ("nothing_entered_production_source", True),
        ("census", OrderedDict([
            ("candidates_discovered", len(recon["records"])),
            ("confirmed_active_identities", by_class.get("EXACT_UNIQUE_IDENTITY", 0)),
            ("classifications", OrderedDict(sorted(by_class.items()))),
        ])),
        ("policy", OrderedDict([
            ("clean_pet_friendly", len(pf)),
            ("clean_verified_no_pets", len(npets)),
            ("resolved", len(clean)),
            ("unresolved", len(unresolved)),
        ])),
        ("profiles_projected", len(pf)),
        ("corridors", OrderedDict([
            ("count", len([c for c in corridors if c])),
            ("assignment", OrderedDict(sorted(corridors.items()))),
        ])),
        ("unresolved_queue", [OrderedDict([
            ("identity_key", k),
            ("name", census[k].get("name")),
            ("route_class", census[k].get("route_class")),
            ("static_outcome", (census[k].get("static") or {}).get("outcome", "")),
        ]) for k in sorted(unresolved)]),
    ])
    with open(os.path.join(REPORTS, "lexington_ky_shadow_market_002.json"), "w",
              encoding="utf-8") as fh:
        json.dump(shadow, fh, indent=1)
        fh.write("\n")

    print(json.dumps(inventory["totals"], indent=1))
    print("census", by_class.get("EXACT_UNIQUE_IDENTITY", 0),
          "| PF", len(pf), "| no-pets", len(npets),
          "| resolved", len(clean), "| unresolved", len(unresolved))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
