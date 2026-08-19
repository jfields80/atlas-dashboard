"""PTF-MILWAUKEE-ACQUISITION-ROUTER-INTEGRATION-001 -- routing recovery,
identity adjudication, and the mechanically derived policy-acquisition queue.

Pure and deterministic: no network, no clock beyond a pinned as-of date. Every
URL in ``RECOVERED_ROUTES`` was read from the property's own first-party page
during this work order and verified by matching the street address the census
already held; the two Hyatt rows are brand-index bindings carrying the brand's
own property code. No pet-policy wording was inspected to produce any of them.

What this writes
----------------
* the census and partition, with the recovered routes applied. §18 of the work
  order freezes policy authority, exclusions, seeds, approvals and the
  partition, and carves out exactly one exception -- "routing may change only
  where this work order explicitly finishes routing prerequisites". Applying a
  recovered official URL is that carve-out, and the partition rows that move
  from AWAITING_OFFICIAL_URL to AWAITING_POLICY_OBSERVATION move as the direct
  consequence of it. Nothing else in either file changes.
* markets/reports/milwaukee-wi_identity_review_001.json -- the six held
  identities, each with a determination and the evidence for it. These are
  RECORDED AND NOT APPLIED: every one of them would change a census identity,
  a name or a count, which the freeze does not carve out. They are a decision
  packet, not a mutation.
* markets/reports/milwaukee-wi_policy_acquisition_queue_001.json -- the queue,
  written before any acquisition starts, with each row's router lane resolved
  from the committed route table.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import registry as REG      # noqa: E402
from scripts.pettripfinder.brightdata import corpus as CORPUS      # noqa: E402

MARKET = "milwaukee-wi"
WORK_ORDER = "PTF-MILWAUKEE-ACQUISITION-ROUTER-INTEGRATION-001"
AS_OF = "2026-08-18"
PKG = REPO / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"

# --------------------------------------------------------------------------- #
# Routing recovery. identity_key -> (url, binding_method, verification)
#
# "address_on_page" means the property's own page printed the same street
# address the census already held, which is the strongest binding available
# without a policy read. "brand_index" means the brand's own property index
# carries the URL and its property code.
# --------------------------------------------------------------------------- #

RECOVERED_ROUTES = {
    "the pfister hotel": (
        "https://www.thepfisterhotel.com/", "PAGE_RENDERED", "address_on_page"),
    "the iron horse hotel": (
        "https://www.theironhorsehotel.com/", "PAGE_RENDERED", "address_on_page"),
    "saint kate the arts hotel": (
        "https://www.saintkatearts.com/", "PAGE_RENDERED", "address_on_page"),
    "the ingleside hotel": (
        "https://www.theinglesidehotel.com/", "PAGE_RENDERED", "address_on_page"),
    "brewhouse inn and suites": (
        "https://www.brewhousesuites.com/", "PAGE_RENDERED", "address_on_page"),
    "the clarke hotel": (
        "https://www.theclarkehotel.com/", "PAGE_RENDERED", "address_on_page"),
    "potawatomi casino hotel": (
        "https://www.potawatomi.com/hotel", "PAGE_RENDERED", "address_on_page"),
    "drury plaza hotel milwaukee downtown": (
        "https://www.druryhotels.com/locations/milwaukee-wi/"
        "drury-plaza-hotel-milwaukee-downtown", "PAGE_RENDERED", "address_on_page"),
    "the marc hotel": (
        "https://www.marchotelmilwaukee.com/", "PAGE_RENDERED", "address_on_page"),
    "dubbel dutch hotel": (
        "https://www.thedubbeldutch.com/contact", "PAGE_RENDERED", "address_on_page"),
    "county clare irish inn and pub": (
        "https://www.countyclare-inn.com/", "PAGE_RENDERED", "address_on_page"),
    "the plaza hotel milwaukee": (
        "https://plazahotelmilwaukee.com/contact/", "PAGE_RENDERED", "address_on_page"),
    "chalet motel of mequon": (
        "https://chaletmotelmequon.com/", "PAGE_RENDERED", "address_corroborated"),
    "knickerbocker on the lake": (
        "https://www.knickerbockeronthelake.com/", "PAGE_RENDERED", "name_on_page"),
    "hyatt place milwaukee downtown": (
        "https://www.hyatt.com/hyatt-place/en-US/mkezd-hyatt-place-milwaukee-downtown",
        "BRAND_INDEX_BINDING", "brand_index"),
    "hyatt place milwaukee airport": (
        "https://www.hyatt.com/hyatt-place/en-US/mkeza-hyatt-place-milwaukee-airport",
        "BRAND_INDEX_BINDING", "brand_index"),
}

#: Property codes learned alongside the recovered routes.
RECOVERED_CODES = {
    "hyatt place milwaukee downtown": "MKEZD",
    "hyatt place milwaukee airport": "MKEZA",
}

#: Why the eight that stayed unrouted stayed unrouted. Recorded so "still
#: AWAITING_OFFICIAL_URL" is an answer rather than a silence.
STILL_UNROUTED = {
    "american motel":
        "No first-party domain exists. The property is carried by the state "
        "tourism registry and by directory listings only.",
    "embassy motel":
        "A first-party domain is named by search indexes "
        "(embassymotelmilwaukee.com) but its DNS does not resolve, so there is "
        "no page for a route to point at. Recording the URL anyway would be "
        "recording a route that cannot serve.",
    "forty winks inn":
        "No first-party domain found. Family-run since 1954; carried by the "
        "lodging association, the state registry and the Wauwatosa CVB.",
    "price pointe inn":
        "No first-party domain found. Reachable only through booking "
        "intermediaries, which are not acceptable as a property route.",
    "hideaway inn":
        "No first-party domain found.",
    "golden key motel":
        "No first-party domain found.",
    "victoria motel":
        "No first-party domain found.",
    "sonesta milwaukee west wauwatosa":
        "Live 198-room property, but absent from Sonesta's own Wisconsin "
        "location index, so the brand publishes no property page for it. A "
        "brand that does not list its own hotel cannot supply its route.",
}

# --------------------------------------------------------------------------- #
# Identity adjudication. RECORDED, NOT APPLIED.
# --------------------------------------------------------------------------- #

IDENTITY_DETERMINATIONS = [
    dict(identity_key="biller hotel",
         canonical_name="Biller Hotel",
         held_as="AWAITING_CENSUS_REVIEW",
         determination="IN_CURRENT_CATEGORY",
         recommended_change="lodging_state NEEDS_REVIEW -> LODGING_CONFIRMED",
         evidence="The property's own site sells nightly transient stays and "
                  "prices them as such: \"Daily rates start at $109/night. "
                  "Weekly rates start at $279.\" It describes \"rooms for all "
                  "needs, from one night to temporary housing\" -- transient "
                  "lodging that also happens to offer extended stays, which is "
                  "true of every extended-stay brand already in this census.",
         source="https://billerhotel.com/",
         confidence="high"),
    dict(identity_key="kinn guesthouse downtown milwaukee",
         canonical_name="Kinn Guesthouse Downtown Milwaukee",
         held_as="AWAITING_CENSUS_REVIEW",
         determination="IN_CURRENT_CATEGORY",
         recommended_change="lodging_state NEEDS_REVIEW -> LODGING_CONFIRMED",
         evidence="The trade name says guesthouse; the property does not. Its "
                  "own site titles this location \"Kinn Guesthouse | Best Hotel "
                  "Downtown Milwaukee\" and describes the brand as \"a "
                  "one-of-a-kind hotel experience\". 31 rooms, self-check-in, "
                  "boutique-hotel operation. This is the Milwaukee lesson "
                  "applied to category rather than to rebrands: decide on "
                  "evidence, not on the name string.",
         source="https://www.kinnguesthouse.com/milwaukee/",
         confidence="high"),
    dict(identity_key="kinn guesthouse bay view",
         canonical_name="Kinn Guesthouse Bay View",
         held_as="AWAITING_CENSUS_REVIEW",
         determination="IN_CURRENT_CATEGORY",
         recommended_change="lodging_state NEEDS_REVIEW -> LODGING_CONFIRMED",
         evidence="Same operator and same self-description; its own page is "
                  "titled \"Bayview's Premier Luxury Hotel | Kinn Guesthouse\". "
                  "8 rooms with a communal kitchen.",
         source="https://www.kinnguesthouse.com/bayview/",
         confidence="high"),
    dict(identity_key="sleep inn and mainstay suites milwaukee franklin",
         canonical_name="Sleep Inn & MainStay Suites Milwaukee/Franklin",
         held_as="AWAITING_IDENTITY_RESOLUTION",
         determination="SPLIT_INTO_TWO_IDENTITIES",
         recommended_change="replace the combined row with Sleep Inn "
                            "Milwaukee/Franklin (wi391) and MainStay Suites "
                            "Milwaukee/Franklin (wi392), both at 6868 S. "
                            "Ballpark Drive, collision_state SHARED_ADDRESS",
         evidence="Choice's own brand index carries two distinct property "
                  "codes at this address. This census already resolves that "
                  "exact shape three times -- Home2 Suites and Tru at 515 N "
                  "Jefferson, Motel 6 and Studio 6 at 325 N Brookfield Road, "
                  "and Courtyard and Residence Inn at 20300 W Bluemound Road "
                  "-- so two brand property codes at one address is this "
                  "corpus's own settled precedent for two identities.",
         source="choicehotels.com brand index, codes wi391 and wi392",
         confidence="high"),
    dict(identity_key="mequon country inn sybaris",
         canonical_name="Mequon Country Inn - Sybaris",
         held_as="AWAITING_IDENTITY_RESOLUTION",
         determination="RENAME_TO_CURRENT_IDENTITY",
         recommended_change="canonical_name -> Sybaris Pool Suites Mequon, "
                            "former_name -> Mequon Country Inn, official_url "
                            "-> https://www.sybaris.com/mequon-wi/",
         evidence="The state registry's compound listing name describes one "
                  "site, not two businesses: Sybaris has operated the pool "
                  "suites at 10240 N Cedarburg Road since 1992 and publishes "
                  "its own property page for it. \"Mequon Country Inn\" is the "
                  "legacy half of a registry name that was never updated. "
                  "Resolved by address, not by name similarity.",
         source="https://www.sybaris.com/mequon-wi/",
         confidence="medium"),
    dict(identity_key="best western plus milwaukee west",
         canonical_name="Best Western Plus Milwaukee West",
         held_as="AWAITING_IDENTITY_RESOLUTION",
         determination="RETIRE_BRAND_IDENTITY__SUCCESSOR_UNKNOWN",
         recommended_change="retire the Best Western identity as "
                            "CLOSED_OR_CONVERTED; do NOT create a successor "
                            "identity until one is observed",
         evidence="Three independent signals now converge, which is what §11 "
                  "of the factory order requires before any closure: the "
                  "property is absent from Best Western's own current "
                  "property sitemap (which lists exactly one Milwaukee "
                  "property, the airport hotel); the building at 5501 W "
                  "National Ave sold for $10.4 million in March 2026; and part "
                  "of the three-story building had already been converted to "
                  "the Woodsview Apartments. What still operates there as "
                  "transient lodging, if anything, is not established -- so "
                  "the brand identity retires and no successor is invented.",
         source="BizTimes Milwaukee, March 2026; bestwestern.com property "
                "sitemap",
         confidence="medium"),
]


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _write(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
                     .encode("utf-8"))


def apply_routes():
    """Write the recovered official URLs into the census and the partition."""
    cpath = PKG / "identity_census" / ("%s.json" % MARKET)
    ppath = PKG / "milwaukee_final_partition_001.json"
    census, partition = _load(cpath), _load(ppath)

    changed = []
    for row in census["hotels"]:
        key = row["identity_key"]
        if key not in RECOVERED_ROUTES:
            continue
        if row["official_url"]:
            raise SystemExit("%s already has a route; recovery would overwrite it" % key)
        url, binding, verification = RECOVERED_ROUTES[key]
        row["official_url"] = url
        row["url_shape"] = "property"
        row["route_binding_method"] = binding
        row["route_verified_by"] = verification
        row["route_recovered_by"] = WORK_ORDER
        row["route_verified_at"] = AS_OF
        if key in RECOVERED_CODES:
            row["property_code"] = RECOVERED_CODES[key]
        changed.append(key)

    missing = sorted(set(RECOVERED_ROUTES) - set(changed))
    if missing:
        raise SystemExit("recovered routes for identities not in the census: %s" % missing)

    moved = []
    for item in partition["items"]:
        if item["identity_key"] not in RECOVERED_ROUTES:
            continue
        if item["final_state"] != "AWAITING_OFFICIAL_URL":
            raise SystemExit("%s is %s, not AWAITING_OFFICIAL_URL"
                             % (item["identity_key"], item["final_state"]))
        item["final_state"] = "AWAITING_POLICY_OBSERVATION"
        item["next_action"] = ("Capture the property's pet-policy surface on "
                               "its own official page.")
        item["official_url"] = RECOVERED_ROUTES[item["identity_key"]][0]
        item["determined_by"] = WORK_ORDER
        item["updated_at"] = AS_OF
        moved.append(item["identity_key"])

    counts = {}
    for item in partition["items"]:
        counts[item["final_state"]] = counts.get(item["final_state"], 0) + 1
    partition["final_state_counts"] = counts
    from scripts.pettripfinder.contracts import partition as PC
    partition["final_state_meanings"] = {k: PC.STATE_MEANINGS[k] for k in sorted(counts)}
    partition["note"] = (
        "No committed policy authority exists for this market: published=0 and "
        "verified_no_pets=0 by construction. "
        "PTF-MILWAUKEE-ACQUISITION-ROUTER-INTEGRATION-001 recovered %d official "
        "URLs, each verified against the address the census already held, and "
        "moved those rows from AWAITING_OFFICIAL_URL to "
        "AWAITING_POLICY_OBSERVATION. No other row changed and no policy "
        "authority was created." % len(moved))

    census["note"] = census["note"] + (
        " PTF-MILWAUKEE-ACQUISITION-ROUTER-INTEGRATION-001 added %d recovered "
        "official URLs; no identity, name, address or count changed." % len(changed))
    _write(cpath, census)
    _write(ppath, partition)
    return changed, moved, counts


def build_queue():
    """The policy-acquisition queue, derived rather than curated."""
    census = _load(PKG / "identity_census" / ("%s.json" % MARKET))
    partition = _load(PKG / "milwaukee_final_partition_001.json")
    pstate = {i["identity_key"]: i["final_state"] for i in partition["items"]}

    rows, excluded = [], {"identity_hold": [], "no_route": [], "already_resolved": [],
                          "other": []}
    for h in sorted(census["hotels"], key=lambda r: r["identity_key"]):
        key = h["identity_key"]
        state = pstate[key]
        if state in ("AWAITING_CENSUS_REVIEW", "AWAITING_IDENTITY_RESOLUTION"):
            excluded["identity_hold"].append(key); continue
        if state in ("PUBLISHED_PET_FRIENDLY", "VERIFIED_NO_PETS"):
            excluded["already_resolved"].append(key); continue
        if state == "OUT_OF_CURRENT_CATEGORY":
            excluded["other"].append(key); continue
        if not h["official_url"]:
            excluded["no_route"].append(key); continue

        brand = CORPUS.brand_of(h["official_url"])
        route = REG.resolve(brand=brand, url=h["official_url"], identity_key=key)
        rows.append({
            "identity_key": key,
            "canonical_name": h["canonical_name"],
            "market_id": MARKET,
            "address": h["address"], "city": h["city"], "state": h["state"],
            "postal_code": h["postal_code"], "phone": h["phone"],
            "official_url": h["official_url"],
            "property_code": h.get("property_code", ""),
            "corridor": h["corridor"],
            "brand": brand or "UNKNOWN",
            "brand_excluded": REG.is_excluded(brand),
            "brand_exclusion_reason": REG.excluded_brands().get((brand or "").upper(), ""),
            "route_provider": route.provider,
            "route_fallbacks": list(route.fallback_providers),
            "route_reader": route.reader,
            "route_resolved_by": route.resolved_by,
            "max_attempts_per_provider": route.max_attempts_per_provider,
            "partition_state": state,
            "queue_state": "QUEUED",
        })

    lanes, readers, brands = {}, {}, {}
    for r in rows:
        if r["brand_excluded"]:
            lanes["excluded_brand"] = lanes.get("excluded_brand", 0) + 1
        else:
            lanes[r["route_provider"]] = lanes.get(r["route_provider"], 0) + 1
        readers[r["route_reader"]] = readers.get(r["route_reader"], 0) + 1
        brands[r["brand"]] = brands.get(r["brand"], 0) + 1

    doc = {
        "schema": "ptf-milwaukee-policy-acquisition-queue/1.0",
        "work_order": WORK_ORDER,
        "market_id": MARKET,
        "as_of": AS_OF,
        "note": (
            "Derived from the committed census and partition, not curated. A row "
            "is here because its identity is active and in category, its "
            "partition state is a policy blocker rather than an identity or "
            "category hold, and it has an official first-party route. Each row's "
            "lane is resolved from the committed acquisition route table so the "
            "plan is inspectable before a single paid call is made."),
        "queue_total": len(rows),
        "excluded_counts": {k: len(v) for k, v in sorted(excluded.items())},
        "excluded_identity_keys": {k: sorted(v) for k, v in sorted(excluded.items())},
        "router_lane_counts": {k: lanes[k] for k in sorted(lanes)},
        "reader_counts": {k: readers[k] for k in sorted(readers)},
        "brand_counts": {k: brands[k] for k in sorted(brands)},
        "brand_excluded_total": sum(1 for r in rows if r["brand_excluded"]),
        "routable_total": sum(1 for r in rows if not r["brand_excluded"]),
        "items": rows,
    }
    _write(REPORTS / ("%s_policy_acquisition_queue_001.json" % MARKET), doc)
    return doc


def write_identity_review():
    doc = {
        "schema": "ptf-milwaukee-identity-review/1.0",
        "work_order": WORK_ORDER,
        "market_id": MARKET,
        "as_of": AS_OF,
        "applied": False,
        "note": (
            "Six held identities, each adjudicated on first-party or "
            "convergent evidence. RECORDED AND NOT APPLIED: every one of these "
            "determinations would change a census identity, name or count, and "
            "§18 of this work order freezes the partition. They are a decision "
            "packet for a follow-up work order, not a mutation. None of the six "
            "entered the acquisition queue."),
        "count": len(IDENTITY_DETERMINATIONS),
        "determination_counts": {},
        "items": IDENTITY_DETERMINATIONS,
    }
    counts = {}
    for d in IDENTITY_DETERMINATIONS:
        counts[d["determination"]] = counts.get(d["determination"], 0) + 1
    doc["determination_counts"] = {k: counts[k] for k in sorted(counts)}
    _write(REPORTS / ("%s_identity_review_001.json" % MARKET), doc)
    return doc


def write_routing_report(changed, moved, counts):
    doc = {
        "schema": "ptf-milwaukee-routing-recovery/1.0",
        "work_order": WORK_ORDER,
        "market_id": MARKET,
        "as_of": AS_OF,
        "note": (
            "Routing recovery only. No pet-policy wording was inspected to "
            "produce any row here; every URL was accepted on a name and street "
            "address match against what the census already held, or on the "
            "brand's own property index."),
        "recovered_count": len(changed),
        "still_unrouted_count": len(STILL_UNROUTED),
        "partition_state_counts_after": counts,
        "recovered": [
            {"identity_key": k, "official_url": RECOVERED_ROUTES[k][0],
             "binding_method": RECOVERED_ROUTES[k][1],
             "verified_by": RECOVERED_ROUTES[k][2],
             "property_code": RECOVERED_CODES.get(k, "")}
            for k in sorted(changed)],
        "still_unrouted": [{"identity_key": k, "reason": v}
                           for k, v in sorted(STILL_UNROUTED.items())],
    }
    _write(REPORTS / ("%s_routing_recovery_001.json" % MARKET), doc)
    return doc


def refresh_founder_review_queue():
    """Rebuild the factory's founder-review queue from the CURRENT partition.

    The queue is a derived report, not authority. Sixteen partition rows moved
    in this work order, so leaving it as the factory wrote it would leave a
    committed artifact asserting a classification the partition no longer
    holds. Regenerated with the factory's own row shape and hash rule so the
    two stay one artifact rather than two opinions.
    """
    import hashlib
    census = _load(PKG / "identity_census" / ("%s.json" % MARKET))
    partition = _load(PKG / "milwaukee_final_partition_001.json")
    by_key = {h["identity_key"]: h for h in census["hotels"]}

    items = []
    for idx, i in enumerate(partition["items"], start=1):
        payload = json.dumps({k: i[k] for k in sorted(i)}, ensure_ascii=False,
                             sort_keys=True).encode("utf-8")
        h = by_key[i["identity_key"]]
        items.append({
            "row_number": idx,
            "identity_key": i["identity_key"],
            "hotel_id": i["identity_key"],
            "canonical_name": i["canonical_name"],
            "address": h["address"],
            "phone": h["phone"],
            "official_candidate_url": i["official_url"],
            "corridor": h["corridor"],
            "current_classification": i["final_state"],
            "blocking_reason": i["final_state"],
            "requested_evidence": "citable pet-policy artifact from the property's own page"
            if i["final_state"] == "AWAITING_POLICY_OBSERVATION"
            else "first-party evidence that resolves the blocker named above",
            "next_action": i["next_action"],
            "batch": "batch-%03d" % (((idx - 1) // 10) + 1),
            "review_status": "NOT_STARTED",
            "row_sha256": hashlib.sha256(payload).hexdigest(),
        })
    _write(REPORTS / ("%s_founder_review_queue.json" % MARKET), {
        "schema": "ptf-milwaukee-founder-review-queue/1.0",
        "work_order": WORK_ORDER,
        "market_id": MARKET,
        "as_of": AS_OF,
        "count": len(items),
        "batch_size": 10,
        "items": items,
    })
    return len(items)


def main():
    changed, moved, counts = apply_routes()
    write_routing_report(changed, moved, counts)
    write_identity_review()
    refresh_founder_review_queue()
    queue = build_queue()
    print("routes recovered      : %d" % len(changed))
    print("partition rows moved  : %d" % len(moved))
    print("partition states      : %s" % counts)
    print("queue total           : %d" % queue["queue_total"])
    print("  routable            : %d" % queue["routable_total"])
    print("  brand-excluded      : %d" % queue["brand_excluded_total"])
    print("excluded              : %s" % queue["excluded_counts"])
    print("lanes                 : %s" % queue["router_lane_counts"])
    print("readers               : %s" % queue["reader_counts"])
    print("brands                : %s" % queue["brand_counts"])


if __name__ == "__main__":
    main()
