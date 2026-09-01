# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-FOUNDER-RULINGS-013 -- apply the seven founder rulings from
indianapolis_in_founder_packet_012.json to the Indianapolis SHADOW census.

SHADOW ONLY. The pinned census, the live policy package, the release contract,
the final partition, the deployment manifest, the ledgers and launch
participation are not read for writing and not written. $0, no provider.

Every ruling is applied FROM THE PACKET AND THE ROW, never from prose: each
action asserts the identity key, the current address/phone/route and the
recorded evidence before it writes. Retired rows are MOVED, not deleted -- the
whole row travels into ``retired_013`` with its ruling, so lineage, provenance
and every earlier supersession block survive. Renamed rows keep the old key in
``prior_census_identity_keys`` and the old name in ``supersession.was``, the
WoodSpring -> ESA Plainfield precedent (FOUNDER RULING 1, order 005).
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

WORK_ORDER = "PTF-INDIANAPOLIS-FOUNDER-RULINGS-013"
MARKET = "indianapolis-in"
DECIDED_BY = "founder"
DECIDED_ON = "2026-09-01"
BOUND_AT = "2026-09-01T04:00:00Z"
PKG = _REPO_ROOT / "launch_packages" / "pettripfinder"
SHADOW = PKG / "identity_census_admission" / "indianapolis-in.json"
REGISTER = PKG / "indianapolis_in_identity_review_register_002.json"
PACKET = PKG / "indianapolis_in_founder_packet_012.json"
COHORT_012 = PKG / "indianapolis_in_unrouted_cohort_012.json"
OUT_RECORD = PKG / "indianapolis_in_founder_rulings_013.json"
OUT_COHORT = PKG / "indianapolis_in_unrouted_cohort_013.json"


def _load(path):
    text = path.read_text(encoding="utf-8-sig")
    doc = json.loads(text, object_pairs_hook=OrderedDict)
    fmt = None
    for indent in (1, 2, 4):
        for ea in (True, False):
            for nl in ("\n", ""):
                if json.dumps(doc, indent=indent, ensure_ascii=ea) + nl == text:
                    fmt = (indent, ea, nl)
    return doc, fmt or (1, False, "\n")


def _save(path, doc, fmt):
    path.write_text(json.dumps(doc, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8", newline="\n")


def _new(path, doc):
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def _slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# --------------------------------------------------------------------------- #

def snapshot(h):
    return OrderedDict((k, h.get(k, "")) for k in (
        "identity_key", "canonical_name", "display_name", "slug", "address", "postal_code",
        "official_url", "phone", "provenance", "source", "source_id", "observed_at", "corridor"))


def rename(h, *, new_key, new_name, address, phone, url, ruling, evidence, why, review_id):
    was = snapshot(h)
    h["prior_census_identity_keys"] = list(h.get("prior_census_identity_keys", [])) + [was["identity_key"]]
    h["identity_key"] = new_key
    h["canonical_name"] = new_name
    h["display_name"] = new_name
    h["slug"] = _slug(new_name)
    if address:
        h["address"] = address
    if phone:
        h["phone"] = phone
    prior_url = h.get("official_url", "")
    h["official_url"] = url
    h["website_state"] = "OFFICIAL_WEBSITE_PRESENT"
    h["supersession"] = OrderedDict([
        ("work_order", WORK_ORDER), ("ruling", "%s -- SAME_IDENTITY_REBRAND_SUCCESSOR" % review_id),
        ("decided_by", DECIDED_BY), ("decided_on", DECIDED_ON), ("verdict", "SAME_IDENTITY_REBRAND_SUCCESSOR"),
        ("was", was), ("why", why), ("evidence", evidence),
        ("lineage_preserved", True), ("second_identity_created", False), ("policy_published", False),
    ])
    h.setdefault("routing_history", []).append(OrderedDict([
        ("work_order", WORK_ORDER), ("prior_official_url", prior_url), ("bound_url", url),
        ("bound_on", ruling), ("method", "founder_ruling_over_attended_first_party_read"),
        ("page_address", address or h["address"]), ("page_telephone", phone or h.get("phone", "")),
        ("census_address", was["address"]), ("cost", "$0"), ("bound_at", BOUND_AT),
    ]))


def retire(shadow, h, *, review_id, verdict, merged_into, evidence, note):
    shadow["hotels"].remove(h)
    entry = OrderedDict([
        ("work_order", WORK_ORDER), ("review_id", review_id), ("decided_by", DECIDED_BY),
        ("decided_on", DECIDED_ON), ("verdict", verdict), ("routing", "ROUTING_RETIRED"),
        ("merged_into", merged_into), ("note", note), ("evidence", evidence),
        ("lineage_preserved", True), ("second_identity_created", False), ("row", h),
    ])
    shadow.setdefault("retired_013", []).append(entry)
    return entry


def main():
    shadow, sfmt = _load(SHADOW)
    reg, rfmt = _load(REGISTER)
    packet, _ = _load(PACKET)
    items = {p["review_id"]: p for p in packet["decisions_requested"]}
    by = {h["identity_key"]: h for h in shadow["hotels"]}
    start = len(shadow["hotels"])
    assert start == shadow["count"] == 268
    applied = []

    # ---- RULING 1: IDR-007-001 la quinta inn -> Baymont NW -------------------
    h = by["la quinta inn"]
    assert h["address"] == "3871 West 92nd Street" and h["postal_code"] == "46268" and not h.get("phone")
    assert "baymont by wyndham indianapolis northwest" not in by
    ev = items["IDR-007-001"]["evidence"]
    assert any("3871 W 92nd St" in e and "426-0215" in e for e in ev)
    rename(h, new_key="baymont by wyndham indianapolis northwest",
           new_name="Baymont by Wyndham Indianapolis Northwest",
           address="3871 W 92nd St", phone="3174260215",
           url="https://www.wyndhamhotels.com/baymont/indianapolis-indiana/baymont-inn-and-suites-indianapolis-northwest/overview",
           ruling="founder ruling IDR-007-001: street and postal agree exactly; the only first-party property at the address is Baymont NW",
           evidence=ev, review_id="IDR-007-001",
           why="a bare-brand OpenStreetMap tag with no telephone or website at a building Wyndham sells as Baymont by Wyndham Indianapolis Northwest; the founder ruled the OSM row a stale name for the same building, not a second hotel")
    applied.append(("IDR-007-001", "SAME_IDENTITY_REBRAND_SUCCESSOR", "la quinta inn -> baymont by wyndham indianapolis northwest"))

    # ---- RULING 2: IDR-012-001 Quality Inn & Suites Noblesville -> IN338 -----
    h = by["quality inn and suites noblesville indianapolis"]
    keep = by["quality inn noblesville indianapolis"]
    assert h["address"] == "16025 Promise Road" and keep["official_url"].endswith("/in338")
    assert keep["address"] == "17070 Dragonfly Lane"
    retire(shadow, h, review_id="IDR-012-001", verdict="DUPLICATE_OF_EXISTING / SAFE_MERGE",
           merged_into="quality inn noblesville indianapolis",
           evidence=items["IDR-012-001"]["evidence"],
           note="Choice lists exactly one Noblesville property (IN338); the surviving row is bound to it. 16025 Promise Road preserved here in lineage.")
    keep["merged_in_013"] = ["quality inn and suites noblesville indianapolis"]
    applied.append(("IDR-012-001", "DUPLICATE_OF_EXISTING / SAFE_MERGE", "quality inn and suites noblesville indianapolis -> merged into quality inn noblesville indianapolis (IN338)"))

    # ---- RULING 3: IDR-012-002 Quality Inn Brownsburg -> IN441 ---------------
    h = by["quality inn brownsburg indianapolis west"]
    keep = by["quality inn and suites brownsburg indianapolis west"]
    assert h["address"] == "31 Brownsburg Place" and keep["address"] == "31 Maplehurst Drive"
    url441 = "https://www.choicehotels.com/indiana/brownsburg/quality-inn-hotels/in441"
    prior_url = keep.get("official_url", "")
    keep["official_url"] = url441
    keep["property_code"] = "IN441"
    keep["website_state"] = "OFFICIAL_WEBSITE_PRESENT"
    keep.setdefault("routing_history", []).append(OrderedDict([
        ("work_order", WORK_ORDER), ("prior_official_url", prior_url), ("bound_url", url441),
        ("bound_on", "founder ruling IDR-012-002: Choice's only Brownsburg Quality Inn is IN441 at 31 Maplehurst Drive, the row's own street"),
        ("method", "founder_ruling_over_attended_first_party_listing"),
        ("page_address", "31 Maplehurst Drive"), ("page_telephone", ""), ("census_address", "31 Maplehurst Drive"),
        ("cost", "$0"), ("bound_at", BOUND_AT)]))
    keep["merged_in_013"] = ["quality inn brownsburg indianapolis west"]
    retire(shadow, h, review_id="IDR-012-002", verdict="DUPLICATE_OF_EXISTING / SAFE_MERGE",
           merged_into="quality inn and suites brownsburg indianapolis west",
           evidence=items["IDR-012-002"]["evidence"],
           note="31 Brownsburg Place was never confirmed by any source; the surviving OSM row carries Choice's own street and is now bound to IN441.")
    applied.append(("IDR-012-002", "DUPLICATE_OF_EXISTING / SAFE_MERGE", "quality inn brownsburg indianapolis west -> merged into quality inn and suites brownsburg indianapolis west (IN441 bound)"))

    # ---- RULING 4: IDR-012-006 Wyndham West -> Wyndham Indianapolis Airport --
    h = by["wyndham indianapolis west"]
    assert h["phone"] == "3172482481" and h["official_url"].endswith("/wyndham-indianapolis-airport/overview")
    assert h["address"] == "2544 Executive Drive"
    was = snapshot(h)
    h["canonical_name"] = "Wyndham Indianapolis Airport"
    h["display_name"] = "Wyndham Indianapolis Airport"
    h["slug"] = _slug("Wyndham Indianapolis Airport")
    h["name_correction_013"] = OrderedDict([
        ("work_order", WORK_ORDER), ("ruling", "IDR-012-006 -- SAME_IDENTITY_REBRAND_SUCCESSOR (display name)"),
        ("decided_by", DECIDED_BY), ("decided_on", DECIDED_ON), ("was", was),
        ("identity_key_unchanged", True),
        ("why", "same brand, street, postal and telephone; Wyndham retitled the page. The identity key stays 'wyndham indianapolis west' as the packet recorded, so every artifact that names it still resolves."),
        ("evidence", items["IDR-012-006"]["evidence"]),
        ("lineage_preserved", True), ("second_identity_created", False), ("policy_published", False),
    ])
    applied.append(("IDR-012-006", "SAME_IDENTITY_REBRAND_SUCCESSOR (display name)", "Wyndham Indianapolis West -> Wyndham Indianapolis Airport; key unchanged"))

    # ---- RULING 5: IDR-012-004 AmericInn Fishers -> retired, converted -------
    h = by["americinn by wyndham fishers indianapolis"]
    assert h["address"] == "9780 North by Northeast Boulevard"
    assert "comfort inn fishers indianapolis" in by
    retire(shadow, h, review_id="IDR-012-004", verdict="PROPERTY_CONVERTED / RETIRE",
           merged_into="comfort inn fishers indianapolis (successor already registered; no new row)",
           evidence=items["IDR-012-004"]["evidence"],
           note="Places CLOSED_PERMANENTLY; AmericInn absent from Wyndham's inventory; Choice lists Comfort Inn & Suites Fishers at the same street, already a census row.")
    applied.append(("IDR-012-004", "PROPERTY_CONVERTED / RETIRE", "americinn by wyndham fishers indianapolis retired; successor comfort inn fishers indianapolis already registered"))

    # ---- RULING 6: IDR-012-005 Ramada Airport -> retired, no successor -------
    h = by["ramada indianapolis airport"]
    assert h["address"] == "5601 Fortune Circle West"
    retire(shadow, h, review_id="IDR-012-005", verdict="PROPERTY_CLOSED_OR_CONVERTED / RETIRE",
           merged_into="",
           evidence=items["IDR-012-005"]["evidence"],
           note="Ramada absent from Wyndham's inventory and the route soft-404s; no successor proven, none invented.")
    applied.append(("IDR-012-005", "PROPERTY_CLOSED_OR_CONVERTED / RETIRE", "ramada indianapolis airport retired; no successor bound"))

    # ---- RULING 7: IDR-012-003 ECHO Suites stub -> retired, merged -----------
    p7 = items["IDR-012-003"]
    assert p7["recommended_ruling"].startswith("DUPLICATE_OF_EXISTING")
    h = by["echo suites extended stay by wyndham"]
    keep = by["echo suites extended stay by wyndham indianapolis ameriplex"]
    # evidence still matches: the stub's street number is the surviving row's
    assert h["address"].strip() == "5831" and h["postal_code"] == "46241"
    assert keep["address"] == "5831 Alta Lake Drive" and keep["phone"] == "3172839434"
    assert keep["official_url"].endswith("/echo-suites-extended-stay-indianapolis-ameriplex/overview")
    retire(shadow, h, review_id="IDR-012-003", verdict="DUPLICATE_OF_EXISTING / SAFE_MERGE",
           merged_into="echo suites extended stay by wyndham indianapolis ameriplex",
           evidence=p7["evidence"],
           note="an OSM stub with a truncated street at the surviving row's own street number; Wyndham's inventory holds exactly one ECHO Suites.")
    keep["merged_in_013"] = ["echo suites extended stay by wyndham"]
    applied.append(("IDR-012-003", "DUPLICATE_OF_EXISTING / SAFE_MERGE", "echo suites extended stay by wyndham (stub) -> merged into ...ameriplex"))

    # ---- reconcile ------------------------------------------------------------
    keys = [h["identity_key"] for h in shadow["hotels"]]
    assert len(keys) == len(set(keys))
    shadow["count"] = len(shadow["hotels"])
    shadow["identity_state_counts"] = OrderedDict(sorted(Counter(h["identity_state"] for h in shadow["hotels"]).items()))
    shadow["founder_rulings_013"] = OrderedDict([
        ("work_order", WORK_ORDER), ("decided_by", DECIDED_BY), ("decided_on", DECIDED_ON),
        ("source_packet", PACKET.name),
        ("applied", [OrderedDict([("review_id", a), ("verdict", b), ("action", c)]) for a, b, c in applied]),
        ("shadow_before", start), ("shadow_after", shadow["count"]),
        ("renamed", 1), ("name_corrected", 1), ("retired", len(shadow["retired_013"])),
        ("pinned_census_touched", False), ("policy_published", False),
    ])
    _save(SHADOW, shadow, sfmt)

    # ---- register ---------------------------------------------------------
    verdicts = {a: (b, c) for a, b, c in applied}
    for r in reg["reviews"]:
        if r["review_id"] in verdicts:
            r["review_state"] = "RULED_AND_APPLIED"
            r["verdict"] = verdicts[r["review_id"]][0]
            r["applied"] = True
            r["applied_by"] = WORK_ORDER
            r["applied_to"] = "SHADOW admission census only; the pinned production census is untouched"
            r["applied_action"] = verdicts[r["review_id"]][1]
            r["acted_on"] = True
            r["decided_by"] = DECIDED_BY
            r["decided_on"] = DECIDED_ON
    _save(REGISTER, reg, rfmt)

    # ---- cohort -----------------------------------------------------------
    c12 = json.loads(COHORT_012.read_text(encoding="utf-8-sig"))
    live_keys = set(keys)
    removed = [k for k in c12["identity_keys"] if k not in live_keys]          # retired or renamed away
    kept = [k for k in c12["identity_keys"] if k in live_keys]
    by = {h["identity_key"]: h for h in shadow["hotels"]}
    kept = [k for k in kept if not by[k].get("official_url")]                      # routed rows leave
    import importlib.util
    spec = importlib.util.spec_from_file_location("cp", str(_REPO_ROOT / "scripts" / "pettripfinder" / "indianapolis_routing_cost_plan_003.py"))
    cp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cp)
    r7 = json.loads((PKG / "indianapolis_in_routing_results_007.json").read_text(encoding="utf-8-sig"))["classifications"]
    seg = Counter()
    for k in kept:
        if r7.get(k) == "ROUTE_NOT_FOUND" or cp.brand_of(k) in cp.FREE_ROUTING_PROVEN:
            s = "FREE_LANE_EXHAUSTED_THIS_RUN"
        elif cp.brand_of(k) in cp.FREE_ROUTING_REFUSED:
            s = "ROUTING_REPAIR_FIRST_PAID_DISCOVERY"
        else:
            s = "ROUTING_REPAIR_FIRST_INDEPENDENT"
        seg[s] += 1
    for s in ("IDENTITY_REVIEW_FIRST", "CLOSED_OR_CONVERTED"):
        seg.setdefault(s, 0)
    cohort = OrderedDict([
        ("schema", c12["schema"]),
        ("what_this_is", "the Indianapolis unrouted cohort after the seven founder rulings of 013: 012's cohort minus the rows retired (5) and the row renamed and routed (la quinta inn -> Baymont NW). No identity is under review and no row is held as closed; every remaining row is a routing-repair candidate."),
        ("market_id", MARKET), ("supersedes", COHORT_012.name), ("source_work_order", WORK_ORDER),
        ("scopes", OrderedDict([("audit_measured", len(kept)), ("whole_shadow_census", len(kept)),
                                ("how_whole_shadow_is_counted", c12["scopes"]["how_whole_shadow_is_counted"])])),
        ("removed_by_013", removed), ("segments", OrderedDict(sorted(seg.items(), key=lambda kv: -kv[1]))),
        ("segment_rule", c12["segment_rule"]), ("count", len(kept)), ("identity_keys", kept), ("whole_shadow_identity_keys", kept),
    ])
    _new(OUT_COHORT, cohort)

    record = OrderedDict([
        ("schema", "ptf-founder-rulings-applied/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET),
        ("decided_by", DECIDED_BY), ("decided_on", DECIDED_ON), ("source_packet", PACKET.name),
        ("shadow_only", True), ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("rulings", shadow["founder_rulings_013"]["applied"]),
        ("shadow", OrderedDict([("before", start), ("after", shadow["count"]), ("deduplicated", len(set(keys))),
                                ("retired", [e["row"]["identity_key"] for e in shadow["retired_013"]]),
                                ("renamed", ["la quinta inn -> baymont by wyndham indianapolis northwest"]),
                                ("name_corrected", ["wyndham indianapolis west -> 'Wyndham Indianapolis Airport' (key unchanged)"]),
                                ("pinned", 257)])),
        ("cohort", OrderedDict([("before", c12["count"]), ("after", cohort["count"]), ("segments", cohort["segments"]),
                                ("removed_by_013", removed)])),
        ("pending_policy_rebinding", "none required: no pending record binds to a renamed or retired key"),
        ("untouched", ["identity_census/indianapolis-in.json (257)", "hotel_policy_facts_indianapolis-in.json (56)",
                       "deploy/netlify/release_contracts/indianapolis-in.json", "indianapolis_in_final_partition_004.json",
                       "deploy/netlify/global_deployment_manifest.json", "both cross-run ledgers", "launch participation",
                       "markets/authority/indianapolis-in/* (live routing and exclusions)"]),
    ])
    _new(OUT_RECORD, record)
    print("shadow", start, "->", shadow["count"], "| retired", len(shadow["retired_013"]))
    print("cohort", c12["count"], "->", cohort["count"], dict(cohort["segments"]))
    print("removed_by_013:", removed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
