"""PTF-SAVANNAH-GA-REGISTER-RESEAL-AND-AUTHORIZATION-PREP-002 -- Savannah's same-campus rulings.

The source-ready order held pet-friendly records at shared address keys:

  * 190 Pioneer Way, 31324     -- Courtyard by Marriott Richmond Hill (Marriott savrc) and Residence Inn by Marriott
                                  Richmond Hill (Marriott savrr): a dual-brand building, both pet-friendly;
  * 100 Half Moon Way, 31322   -- TownePlace Suites by Marriott Savannah Pooler (Marriott savtp, pet-friendly) and
                                  Fairfield by Marriott Inn & Suites Savannah Pooler (Marriott savfp, verified no pets);
  * 201 E. / 201 West Bay St   -- Hampton Inn (Hilton savdthx) and Hotel Indigo (IHG savid), and
  * 11 Gateway Blvd E / 11 W   -- Holiday Inn Savannah S - I-95 Gateway (IHG savgb) and TownePlace Suites Savannah South
                                  (Marriott savps): two buildings on opposite street directionals that the shared
                                  address key cannot tell apart.

A ruling is DATA under the existing publication-guard contract (same_campus_distinct_entity: one address key,
distinct entities), the shape Charlotte, Raleigh, Atlanta, Richmond and Charleston recorded. No code, schema or rule
changes.

STREET-DIRECTIONAL COLLISIONS ARE NEVER RULED HERE
-------------------------------------------------
By founder order (PTF-SAVANNAH-GA-REGISTER-RESEAL-AND-AUTHORIZATION-PREP-002, Phase 4) every profile affected by the
shared address key's dropped directional stays HELD. A group whose two stated streets carry opposite directionals is
reported as HELD_STREET_DIRECTIONAL_COLLISION and no row is written for it, whatever the distinct-hotel proof says.

THE PROOF, NOT AN OVERRIDE
--------------------------
A ruling is written only for a group of exactly two first-party reads at one address key that the source-ready clean
set held (CO_LOCATION_RULING_REQUIRED) or a recorded ruling has since released, and only where:

  * both records bind to ADMITTED census identities with distinct identity keys;
  * both first-party pages state street identities with the SAME address key (the key the guard uses) and the same
    premises (no opposite directionals);
  * `hotel_exclusions.co_located_distinct` returns DISTINCT: distinct canonical first-party URLs and distinct
    brand-scoped property codes read from BOTH official URLs;
  * the census's own official URL for each identity equals the page that was read.

Nothing merges by display name, phone or row order. A ruling waives the STREET-IDENTITY match and nothing else and
asserts nothing about either property's policy.

Output: launch_packages/pettripfinder/identity_resolutions.json  (rows appended, --write)
        launch_packages/pettripfinder/markets/reports/savannah_ga_co_location_003.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import hotel_exclusions as HE          # noqa: E402
from scripts.pettripfinder import publication_guard as PG         # noqa: E402
from scripts.pettripfinder.site_data import normalize_name        # noqa: E402
from scripts.pettripfinder.savannah_ga_census_reconciliation_001 import directional_conflict  # noqa: E402

WORK_ORDER = "PTF-SAVANNAH-GA-REGISTER-RESEAL-AND-AUTHORIZATION-PREP-002"
MARKET_ID = "savannah-ga"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CLEAN = os.path.join(REPORTS, "savannah_ga_clean_authority_001.json")
CENSUS = os.path.join(PKG, "identity_census", "savannah-ga.json")
RESOLUTIONS = os.path.join(PKG, "identity_resolutions.json")
OUT = os.path.join(REPORTS, "savannah_ga_co_location_003.json")
REVIEWED_AT = "2026-09-15"


def _load(p):
    with open(p, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _slug(name):
    return normalize_name(name).replace(" ", "-")


def build():
    clean = _load(CLEAN)
    census = {h["identity_key"]: h for h in _load(CENSUS)["hotels"]}
    # Every pet-friendly read at a shared street identity: the records still HELD for a ruling, and
    # the records a recorded ruling has already released into the clean set -- so a rerun after the
    # rulings exist derives the same rulings rather than an empty set.
    held = [r for r in clean["rejected"]
            if r["classification"] in ("CO_LOCATION_RULING_REQUIRED", "ADDRESS_KEY_DIRECTIONAL_COLLISION")]
    by_street = OrderedDict()
    pf_keys = set()
    for r in sorted(held + list(clean["clean_pet_friendly"]) + list(clean["clean_verified_no_pets"]),
                    key=lambda x: x["identity_key"]):
        sig = r["identity_signals"]
        key = HE.address_key(sig.get("address_on_page") or "", (sig.get("postal_code") or "")[:5])
        by_street.setdefault(key, []).append(r)
        if r in held or r in clean["clean_pet_friendly"]:
            pf_keys.add(key)
    # a shared key matters only where a pet-friendly record stands on it (two refusals publish nothing to collide)
    by_street = OrderedDict((k, v) for k, v in by_street.items() if len(v) > 1 and k in pf_keys)

    rows, refused = [], []
    for key, recs in by_street.items():
        problems = []
        if not key.strip("|") or len(recs) != 2:
            problems.append("expected exactly two first-party reads at a readable address key, got %d" % len(recs))
        idents = []
        for r in recs:
            h = census.get(r["identity_key"])
            if h is None or h.get("classification") != "TRUE_HOTEL_IDENTITY":
                problems.append("%s is not an admitted census identity" % r["identity_key"])
                continue
            url = r.get("final_url") or r.get("source_url") or ""
            if HE.canonical_url(h.get("official_url") or "") != HE.canonical_url(url):
                problems.append("%s: the census official URL differs from the page read" % h["canonical_name"])
            census_key = HE.address_key(h.get("street") or "", (h.get("postal_code") or "")[:5])
            if census_key != key:
                problems.append("%s: census street key %s differs from the page's %s" % (h["canonical_name"], census_key, key))
            if h.get("slug") and h["slug"] != _slug(h["canonical_name"]):
                problems.append("%s: census slug %r is not the derived slug" % (h["canonical_name"], h["slug"]))
            idents.append((h, url, HE.brand_scoped_property_identity(url)))
        verdict, why = (None, None)
        if len(idents) == 2:
            (ha, ua, _ca), (hb, ub, _cb) = idents
            if ha["identity_key"] == hb["identity_key"]:
                problems.append("one identity key")
            verdict, why = HE.co_located_distinct(
                {"canonical_name": ha["canonical_name"], "official_url": ua},
                {"canonical_name": hb["canonical_name"], "official_url": ub})
            if verdict != HE.CO_LOCATED_DISTINCT:
                problems.append("co_located_distinct: %s (%s)" % (verdict, why))
        _streets = [r["identity_signals"].get("address_on_page") or "" for r in recs]
        if any(directional_conflict(x, y) for x in _streets for y in _streets):
            problems.append("HELD_STREET_DIRECTIONAL_COLLISION: the stated streets %r carry opposite directionals; "
                            "by founder order no ruling is written and both profiles stay held" % _streets)
        if problems:
            refused.append(OrderedDict((("address_key", key), ("records", [r["identity_key"] for r in recs]),
                                        ("problems", problems))))
            continue
        (ha, ua, (fa, ca)), (hb, ub, (fb, cb)) = idents
        sa = next(r["identity_signals"].get("address_on_page") for r in recs if r["identity_key"] == ha["identity_key"])
        sb = next(r["identity_signals"].get("address_on_page") for r in recs if r["identity_key"] == hb["identity_key"])
        row = OrderedDict((
            ("resolution_id", ("res-%s-%s" % (MARKET_ID, _slug(ha["canonical_name"])))[:96]),
            ("market_id", MARKET_ID),
            ("resolution_type", PG.SAME_CAMPUS),
            ("address_key", key),
            ("identities", [
                OrderedDict((("canonical_name", h["canonical_name"]), ("category", "pet-friendly-hotels"),
                             ("slug", _slug(h["canonical_name"])), ("official_url", u)))
                for h, u in ((ha, ua), (hb, ub))]),
            ("evidence",
             "Two separately bookable hotels at address key %s. The operator pages state the street identities %r "
             "(%s) and %r (%s), each published under its own brand property code at its own canonical first-party URL "
             "(%s and %s), which is the exclusion contract's co_located_distinct proof. %s The pair was held by "
             "PTF-SAVANNAH-GA-PARALLEL-SOURCE-READY-001 for a registration-order ruling; this resolution waives the "
             "STREET-IDENTITY match and nothing else, and asserts nothing about either property's pet policy."
             % (key, sa, ha["canonical_name"], sb, hb["canonical_name"], ua, ub,
                ("The two stated streets carry OPPOSITE directionals (%s vs %s): two buildings on either side of one "
                 "street, which the shared address key cannot tell apart." % (sa, sb))
                if directional_conflict(sa, sb) else "The two pages state one building.")),
            ("distinct_reason",
             "Two hotels, not one property under two names: %s is %s property code %s and %s is %s property code "
             "%s -- %s, each with its own canonical first-party URL and its own separately stated pet policy. The "
             "exclusion contract's co_located_distinct proof returns DISTINCT: %s."
             % (ha["canonical_name"], fa, ca, hb["canonical_name"], fb, cb,
                "distinct codes inside one brand family" if fa == fb else "codes in two different brand families",
                why)),
            ("reviewer_id", WORK_ORDER),
            ("reviewed_at", REVIEWED_AT),
        ))
        row["resolution_hash"] = PG.resolution_hash(row)
        rows.append(row)
    return rows, refused


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    rows, refused = build()
    print("co-located pairs proved DISTINCT :", len(rows))
    for r in rows:
        print("   ", r["address_key"], "::", " | ".join(i["canonical_name"] for i in r["identities"]))
    print("pairs NOT proved distinct (left held):", len(refused))
    for r in refused:
        print("   ", r["address_key"], "::", r["problems"])

    doc = _load(RESOLUTIONS)
    existing = {r["resolution_id"] for r in doc["resolutions"]}
    fresh = [r for r in rows if r["resolution_id"] not in existing]
    doc["resolutions"] = doc["resolutions"] + fresh
    try:
        validated = PG.validate_resolutions(doc)
    except Exception as exc:                                        # noqa: BLE001
        print("contract REFUSED                 :", exc)
        print("NOT WRITTEN")
        return 1
    print("contract validated resolutions   :", len(validated))
    if not args.write:
        print("(dry run; pass --write)")
        return 0
    if fresh:
        with open(RESOLUTIONS, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(doc, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
    report = OrderedDict((
        ("schema", "ptf-co-location-rulings/1.0"), ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID), ("as_of", REVIEWED_AT),
        ("resolutions_added", len(rows)),
        ("pairs_left_held", len(refused)),
        ("waives", "a STREET-IDENTITY match only; a name or alias match is never waived"),
        ("resolutions", rows), ("not_proved_distinct", refused),
    ))
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("written                          :", os.path.relpath(OUT, _DASH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
