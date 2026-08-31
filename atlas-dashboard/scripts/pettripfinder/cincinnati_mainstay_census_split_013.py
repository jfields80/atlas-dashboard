# -*- coding: utf-8 -*-
"""PTF-CINCINNATI-MAINSTAY-CENSUS-SPLIT-013 -- one legacy row, two real hotels.

    python -m scripts.pettripfinder.cincinnati_mainstay_census_split_013
    python -m scripts.pettripfinder.cincinnati_mainstay_census_split_013 --write

PTF-CINCINNATI-MAINSTAY-IDENTITY-012 established that "Comfort Suites Mainstay
Hotel" denotes two Choice properties at 2347 Reading Road -- oh720 in Building
A and oh721 in Building B -- with two phones, two property codes and two review
counts, and a census phone and postal code that match neither. This order
replaces the one legacy row with the two real identities.

THE CENSUS'S OWN DOCTRINE
-------------------------
The census header already says it: "Shared street addresses are recorded, never
merged: two hotel brands in one building are two identities." The conflated row
was a standing violation of the market's own stated rule. This is not a new
policy; it is the census being made to obey itself.

WHY THE LEGACY ROW IS REMOVED RATHER THAN FLAGGED
-------------------------------------------------
``enums.IDENTITY_STATES`` is CONFIRMED / PROVISIONAL / UNRESOLVED. There is no
retired or superseded state, and ``contracts.partition.reconcile`` requires the
partition's keys to equal the census's exactly -- so a row left in ``hotels``
remains a live identity that must hold a final state. Leaving it would make the
market carry three hotels where two exist, which is the thing this order was
called to end. So the row is physically removed and its lineage is preserved
where lineage belongs: on the two successors.

Both new rows carry ``prior_identity_key`` and a ``split`` block naming the old
key, the old name, the old address and the reason. That satisfies the rule
PTF-CINCINNATI-CENSUS-PIN-024 set -- a census change must ACCOUNT for every
prior identity and SUPERSEDE it, never overwrite it.

CENSUS ARITHMETIC IS EXPLICIT
-----------------------------
256 - 1 + 2 = 257. Every count that derives from the census moves with it, and
unresolved is derived, never assumed: 257 - resolved.

NO EVIDENCE IS SHARED BETWEEN THE TWO
-------------------------------------
Each identity gets its own route to its own property page, and its own
exclusion record carrying its own canonical name, street with building, postal
code, phone, property code, source URL and page digest. Publishing one combined
refusal for two hotels is the error PTF-...-IDENTITY-012 refused to make, and
splitting the row does not make it safe -- it makes it unnecessary.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import hotel_exclusions as EX               # noqa: E402
from scripts.pettripfinder import market_authority as MA               # noqa: E402
from scripts.pettripfinder.contracts import enums                      # noqa: E402
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key  # noqa: E402

WORK_ORDER = "PTF-CINCINNATI-MAINSTAY-CENSUS-SPLIT-013"
PARENT = "PTF-CINCINNATI-MAINSTAY-IDENTITY-012"
MARKET_ID = "cincinnati-oh"
OPERATOR = "jfields80"
AS_OF = "2026-08-31"
OBSERVED_AT = "2026-08-31"

LEGACY = "comfort suites mainstay hotel"
REASON = "CONFLATED_DUAL_PROPERTY_DIRECTORY_IDENTITY"
NL = chr(10)

PKG = _REPO_ROOT / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
CENSUS = PKG / "identity_census" / "cincinnati-oh.json"
PARTITION = PKG / "cincinnati_final_partition_001.json"
DETERMINATION = REPORTS / "cincinnati_mainstay_identity_012.json"
LEDGER = REPORTS / "cincinnati_mainstay_census_split_013.json"

#: The affirmative-refusal gate, as PTF-...-APPLICATION-010 left it.
REFUSAL_PHRASES = ("not allowed", "pets allowed: no", "do not allow",
                   "no pets", "prohibited", "not permitted")


class SplitError(RuntimeError):
    pass


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _corridor_for(postal_code, legacy):
    from scripts.pettripfinder.discovery.census_projection import corridor_zips
    from scripts.pettripfinder.markets import load_markets, market_by_id
    zips = corridor_zips(market_by_id(load_markets(), MARKET_ID))
    corridor = zips.get(postal_code, "")
    if not corridor:
        raise SplitError("no corridor claims postal code %s; the successor "
                         "would be unassigned" % postal_code)
    return corridor


def _successor(prop, legacy):
    """One census row for one real hotel, carrying its own lineage."""
    key = ptf_identity_key(prop["name"])
    return OrderedDict((
        ("identity_key", key),
        ("canonical_name", prop["name"]),
        ("display_name", prop["name"]),
        ("slug", key.replace(" ", "-")),
        ("market_id", MARKET_ID),
        ("address", prop["street"]),
        ("city", prop["city"]),
        ("state", prop["state"]),
        ("postal_code", prop["postal_code"]),
        ("phone", prop["phone"]),
        # No official_url. Routing authority lives in identity_routing.json,
        # and test_census_carries_no_new_official_url exists to keep the two
        # files from drifting into two copies of the same fact.
        ("official_url", ""),
        ("property_code", prop["property_code"]),
        ("identity_state", enums.IDENTITY_CONFIRMED),
        ("lodging_state", "LODGING_CONFIRMED"),
        ("policy_state", "POLICY_NOT_VERIFIED"),
        # The contract's vocabulary, not an invented one: two hotels at one
        # street address is SHARED_ADDRESS. The building letter that
        # separates them lives in the address itself.
        ("collision_state", "SHARED_ADDRESS"),
        # DERIVED from this property's own postal code through the single
        # assignment authority, not inherited from the legacy row. It lands on
        # the same corridor here, but inheriting would have been luck.
        ("corridor", _corridor_for(prop["postal_code"], legacy)),
        ("assignment_basis", "postal_code"),
        ("assignment_value", prop["postal_code"]),
        ("source", "choice_first_party_property_page"),
        ("observed_at", OBSERVED_AT),
        ("provenance", WORK_ORDER),
        ("prior_identity_key", LEGACY),
        ("split", OrderedDict((
            ("reason", REASON),
            ("from_identity_key", LEGACY),
            ("from_canonical_name", legacy["canonical_name"]),
            ("from_address", legacy["address"]),
            ("from_postal_code", legacy["postal_code"]),
            ("from_phone", legacy["phone"]),
            ("determined_by", PARENT),
            ("split_by", WORK_ORDER),
            ("split_on", AS_OF),
            ("operator", OPERATOR),
            ("sibling_identity_key", ""),      # filled in once both exist
            ("not_merged_because",
             "Two Choice property codes, two buildings at one street number, "
             "two phones and two independent review counts. The census's own "
             "collision_audit already states the rule: shared street "
             "addresses are recorded, never merged."),
            ("evidence_url", prop["official_property_url"]),
            ("evidence_sha256_page", prop["sha256_page"]),
        ))),
    ))


def build():
    determination = _load(DETERMINATION)
    if determination["classification"] != "SEPARATE_BUILDING_IDENTITY":
        raise SplitError("the parent determination is %s, not a split"
                         % determination["classification"])
    observed = determination["observed_first_party"]
    if set(observed) != {"oh720", "oh721"}:
        raise SplitError("the determination does not name exactly two codes")

    # ---- Phase 1 gates, on the evidence itself.
    codes, urls, phones, digests, streets = set(), set(), set(), set(), set()
    for code, prop in observed.items():
        if prop["property_code"] != code:
            raise SplitError("%s: property_code disagrees" % code)
        if not prop["official_property_url"].startswith("https://"):
            raise SplitError("%s: no first-party URL" % code)
        if not prop["sha256_page"]:
            raise SplitError("%s: no evidence digest" % code)
        if not any(p in prop["pets"].lower() for p in REFUSAL_PHRASES):
            raise SplitError("%s: its refusal is not affirmative" % code)
        codes.add(code); urls.add(prop["official_property_url"])
        phones.add(prop["phone"]); digests.add(prop["sha256_page"])
        streets.add(prop["street"])
    if not (len(codes) == len(urls) == len(phones) == len(digests) == 2):
        raise SplitError("the two properties share evidence; that is "
                         "cross-contamination, not a split")
    if not any("Building A" in s for s in streets) or \
            not any("Building B" in s for s in streets):
        raise SplitError("the building designations were not preserved")

    census = _load(CENSUS)
    rows = census["hotels"]
    legacy = next((h for h in rows if h["identity_key"] == LEGACY), None)
    if legacy is None:
        raise SplitError("%s is not in the census; the split already ran"
                         % LEGACY)

    successors = [_successor(observed[c], legacy) for c in ("oh720", "oh721")]
    keys = {s["identity_key"] for s in successors}
    existing = {h["identity_key"] for h in rows}
    collided = keys & existing
    if collided:
        raise SplitError("successor key already in the census: %s" % collided)
    if len(keys) != 2:
        raise SplitError("both successors normalise to one key")
    successors[0]["split"]["sibling_identity_key"] = successors[1]["identity_key"]
    successors[1]["split"]["sibling_identity_key"] = successors[0]["identity_key"]

    # Blue Ash must be untouched and must not be one of the successors.
    blue = "mainstay suites cincinnati blue ash"
    if blue in keys:
        raise SplitError("the Blue Ash MainStay was swept into the split")
    if blue not in existing:
        raise SplitError("the Blue Ash MainStay vanished")

    kept = [h for h in rows if h["identity_key"] != LEGACY]
    census["hotels"] = sorted(kept + successors,
                              key=lambda h: h["identity_key"])
    census["count"] = len(census["hotels"])
    census["identity_state_counts"] = OrderedDict(sorted(Counter(
        h["identity_state"] for h in census["hotels"]).items()))
    census["lodging_state_counts"] = OrderedDict(sorted(Counter(
        h["lodging_state"] for h in census["hotels"]).items()))
    census["collision_audit"] = OrderedDict((
        ("shared_address_identities", _shared_address_count(census["hotels"])),
        ("note", "Shared street addresses are recorded, never merged: two "
                 "hotel brands in one building are two identities. %s applied "
                 "that rule to a row that had violated it, replacing the "
                 "conflated 'Comfort Suites Mainstay Hotel' with oh720 and "
                 "oh721." % WORK_ORDER),
    ))
    assigned = sum(1 for h in census["hotels"] if h.get("corridor"))
    census["geography"] = OrderedDict((
        ("assigned", assigned),
        ("unassigned", census["count"] - assigned),
        ("ambiguous", 0),
        ("note", "Corridors come from scripts.pettripfinder.markets."
                 "assignment, the single assignment authority. An unassigned "
                 "identity is a reported result, not a failure: it publishes "
                 "normally and simply has no corridor page yet."),
    ))
    census["split_history"] = census.get("split_history") or []
    census["split_history"].append(OrderedDict((
        ("work_order", WORK_ORDER), ("as_of", AS_OF), ("reason", REASON),
        ("retired_identity_key", LEGACY),
        ("successor_identity_keys", sorted(keys)),
        ("count_before", len(rows)), ("count_after", census["count"]),
        ("why_removed_not_flagged",
         "enums.IDENTITY_STATES has no retired or superseded value, and "
         "partition.reconcile requires the partition's keys to equal the "
         "census's, so a row left in place would remain a live third hotel."),
    )))
    return census, legacy, successors, observed


def _shared_address_count(rows):
    seen = Counter((h.get("address", "").strip().lower(),
                    h.get("postal_code", "")) for h in rows
                   if h.get("address"))
    return sum(n for n in seen.values() if n > 1)


def build_route(successor, prop, legacy_route):
    key = successor["identity_key"]
    return OrderedDict((
        ("routing_id", "route-%s-%s" % (MARKET_ID, key.replace(" ", "-"))),
        ("schema_version", "1.0.0"),
        ("hotel_ref", OrderedDict((
            ("market_id", MARKET_ID),
            ("canonical_name", successor["canonical_name"]),
            ("normalized_name", key),
            ("identity_key", key)))),
        ("market_id", MARKET_ID),
        ("official_property_url", prop["official_property_url"]),
        ("official_domain", "choicehotels.com"),
        ("property_code", prop["property_code"]),
        ("brand", "CHOICE"),
        # BRAND_INDEX_BINDING, not PAGE_RENDERED: choicehotels.com is on the
        # bot-walled list, and test_every_committed_record_preserves_index_
        # binding holds that a brand which walls us can never be the source of
        # a rendered-page binding. The evidence WAS rendered attended -- that
        # is recorded on the exclusion, where the digest belongs -- but the
        # route's binding_method describes the source, and this market's other
        # Choice routes all say the same thing.
        ("binding_method", "BRAND_INDEX_BINDING"),
        ("binding_sources", ["BRAND_PROPERTY_PAGE"]),
        ("identity_signals_matched", ["binding:street", "binding:building",
                                      "binding:postal_code", "binding:phone",
                                      "binding:property_code",
                                      "binding:city", "binding:state"]),
        ("identity_context", OrderedDict((
            ("address", prop["street"]), ("city", prop["city"]),
            ("state", prop["state"]), ("postal_code", prop["postal_code"]),
            ("phone", prop["phone"])))),
        ("observed_at", OBSERVED_AT),
        ("verified_at", AS_OF),
        ("status", "ROUTING_CONFIRMED"),
        ("notes", "%s: created by the census split of %r. This route binds "
                  "ONE property -- %s in %s -- and shares no URL, phone or "
                  "evidence with its sibling %s. Every signal here was read "
                  "from this property's own page; the retired route claimed "
                  "postal_code and phone against a census row that matched "
                  "neither hotel."
                  % (WORK_ORDER, legacy_route["hotel_ref"]["canonical_name"],
                     prop["property_code"],
                     prop["street"].split(", ")[-1],
                     successor["split"]["sibling_identity_key"])),
        ("category", "accommodation"),
    ))


def build_exclusion(successor, prop):
    key = successor["identity_key"]
    record = OrderedDict((
        ("exclusion_id", "cin-" + key.replace(" ", "-")),
        ("canonical_name", successor["canonical_name"]),
        ("normalized_name", key),
        ("address", prop["street"]),
        ("city", prop["city"]),
        ("state", prop["state"]),
        ("postal_code", prop["postal_code"]),
        ("phone", prop["phone"]),
        ("official_url", prop["official_property_url"]),
        ("exclusion_state", "VERIFIED_NO_PETS"),
        ("evidence_quote", prop["pets"]),
        ("source_url", prop["official_property_url"]),
        ("observed_at", OBSERVED_AT),
        ("source_hash", "sha256:%s" % prop["sha256_page"].replace("-", "")),
        ("reviewer_id", OPERATOR),
        ("reviewed_at", AS_OF),
        ("notes", "%s: affirmative, property-specific refusal on this "
                  "property's own Choice page (%s, %s), captured attended at "
                  "zero cost by %s. This identity was created by splitting "
                  "the conflated census row %r, which denoted this hotel AND "
                  "its sibling %s; no combined exclusion was ever registered "
                  "for the two."
                  % (WORK_ORDER, prop["property_code"],
                     prop["street"].split(", ")[-1], PARENT, LEGACY,
                     successor["split"]["sibling_identity_key"])),
        ("market_id", MARKET_ID),
    ))
    record["record_hash"] = EX.record_hash(record)
    record["approval_hash"] = EX.approval_hash(record)
    return record


# ------------------------------------------------------------------ main

def rebuild_partition(census, exclusions):
    partition = _load(PARTITION)
    prior = {i["identity_key"]: i for i in partition["items"]}
    excluded = {e["normalized_name"] for e in exclusions}
    keys = {h["identity_key"] for h in census["hotels"]}

    items = []
    for row in census["hotels"]:
        key = row["identity_key"]
        was = prior.get(key)
        if key in excluded:
            state, resolved = "VERIFIED_NO_PETS", True
            determined, reason = WORK_ORDER, ""
        elif was:
            state, resolved = was["final_state"], was["resolved"]
            determined = was.get("determined_by", "")
            reason = was.get("state_override_reason", "")
        else:
            raise SplitError("%s is in the census with no partition history "
                             "and no exclusion" % key)
        items.append(OrderedDict((
            ("identity_key", key),
            ("canonical_name", row.get("canonical_name", "")),
            ("slug", row.get("slug", key.replace(" ", "-"))),
            ("city", row.get("city", "")),
            ("state", row.get("state", "")),
            ("postal_code", row.get("postal_code", "")),
            ("final_state", state),
            ("resolved", resolved),
            ("next_action", "" if resolved
             else (was or {}).get("next_action", "")),
            ("next_action_source", "" if resolved
             else (was or {}).get("next_action_source", "")),
            ("determined_by", determined),
            ("updated_at", AS_OF if not was or was["final_state"] != state
             else was.get("updated_at", AS_OF)),
            ("official_url", row.get("official_url", "")
             or (was or {}).get("official_url", "")),
            ("state_override_reason", reason),
        )))

    if LEGACY in {i["identity_key"] for i in items}:
        raise SplitError("the retired identity is still in the partition")
    counts = Counter(i["final_state"] for i in items)
    partition["work_order"] = WORK_ORDER
    partition["as_of"] = AS_OF
    partition["count"] = len(items)
    partition["final_state_counts"] = OrderedDict(sorted(counts.items()))
    partition["items"] = items
    if {i["identity_key"] for i in items} != keys:
        raise SplitError("the partition does not reconcile to the census")
    return partition, counts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        census, legacy, successors, observed = build()
    except SplitError as exc:
        print("REFUSED: %s" % exc)
        return 2

    doc = MA.load_market_routing_document(MARKET_ID)
    legacy_route = next((r for r in doc["routes"]
                         if r["hotel_ref"]["identity_key"] == LEGACY), None)
    if legacy_route is None:
        print("REFUSED: the legacy route is gone")
        return 2
    codes = ("oh720", "oh721")
    routes = [build_route(s, observed[c], legacy_route)
              for s, c in zip(successors, codes)]
    exclusions = [build_exclusion(s, observed[c])
                  for s, c in zip(successors, codes)]

    if len({r["official_property_url"] for r in routes}) != 2:
        print("REFUSED: the two routes share a URL")
        return 2
    if len({e["source_hash"] for e in exclusions}) != 2:
        print("REFUSED: the two exclusions share an evidence digest")
        return 2

    kept = [r for r in doc["routes"]
            if r["hotel_ref"]["identity_key"] != LEGACY] + routes
    try:
        partition, counts = rebuild_partition(census, exclusions)
    except SplitError as exc:
        print("REFUSED: %s" % exc)
        return 2

    resolved = sum(counts[s] for s in ("PUBLISHED_PET_FRIENDLY",
                                       "VERIFIED_NO_PETS",
                                       "OUT_OF_CURRENT_CATEGORY"))
    print("census            : %d -> %d  (-1 conflated, +2 real)"
          % (len(_load(CENSUS)["hotels"]), census["count"]))
    for s in successors:
        print("  + %-46s %s %s"
              % (s["identity_key"][:46], s["postal_code"],
                 s["property_code"]))
    print("  - %-46s RETIRED (%s)" % (LEGACY, REASON))
    print("routes            : %d -> %d" % (len(doc["routes"]), len(kept)))
    print("new exclusions    : %d" % len(exclusions))
    print("pet-friendly      : %d" % counts["PUBLISHED_PET_FRIENDLY"])
    print("verified no-pets  : %d" % counts["VERIFIED_NO_PETS"])
    print("resolved          : %d" % resolved)
    print("unresolved        : %d  (= %d census - %d resolved)"
          % (census["count"] - resolved, census["count"], resolved))
    if not args.write:
        print("(check only -- pass --write)")
        return 0

    CENSUS.write_text(json.dumps(census, indent=1, ensure_ascii=False) + NL,
                      encoding="utf-8", newline=NL)
    print("WROTE %s (%d identities)" % (CENSUS.name, census["count"]))

    shard = MA.build_routing_shard(MARKET_ID, kept,
                                   doc.get("source_batches") or ())
    MA.routing_shard_path(MARKET_ID).write_text(
        MA.render_json(shard), encoding="utf-8", newline=NL)
    print("WROTE routing shard (%d routes)" % len(kept))

    ex_doc = MA.load_market_exclusions_document(MARKET_ID)
    ex_doc["exclusions"] = ex_doc["exclusions"] + exclusions
    ex_doc["count"] = len(ex_doc["exclusions"])
    MA.exclusions_shard_path(MARKET_ID).write_text(
        MA.render_json(ex_doc), encoding="utf-8", newline=NL)
    print("WROTE exclusions shard (%d rows)" % ex_doc["count"])

    PARTITION.write_text(json.dumps(partition, indent=1, ensure_ascii=False)
                         + NL, encoding="utf-8", newline=NL)
    print("WROTE %s" % PARTITION.name)

    ledger = OrderedDict((
        ("schema", "ptf-market-census-split/1.0"),
        ("work_order", WORK_ORDER),
        ("parent_work_order", PARENT),
        ("market_id", MARKET_ID), ("as_of", AS_OF), ("operator", OPERATOR),
        ("reason", REASON),
        ("provider_calls", 0), ("paid_spend_usd", 0.0),
        ("retired_identity", OrderedDict((
            ("identity_key", LEGACY),
            ("canonical_name", legacy["canonical_name"]),
            ("address", legacy["address"]),
            ("postal_code", legacy["postal_code"]),
            ("phone", legacy["phone"]),
            ("resolved_by", "CENSUS_SPLIT"),
            ("superseded_by", sorted(s["identity_key"] for s in successors)),
            ("evidence_source", PARENT),
            ("policy_outcome_applied_to_old_row", False),
            ("why_removed_not_flagged",
             "enums.IDENTITY_STATES has no retired value and "
             "partition.reconcile requires census and partition keys to be "
             "equal, so a flagged row would have stayed a live third hotel."),
            ("route_retired", legacy_route)))),
        ("retired_identity_census_row", legacy),
        ("successors", [OrderedDict((
            ("identity_key", s["identity_key"]),
            ("canonical_name", s["canonical_name"]),
            ("property_code", s["property_code"]),
            ("address", s["address"]),
            ("postal_code", s["postal_code"]),
            ("phone", s["phone"]),
            ("official_url", s["official_url"]),
            ("evidence_sha256_page", s["split"]["evidence_sha256_page"]),
            ("sibling_identity_key", s["split"]["sibling_identity_key"]),
            ("policy_outcome", "VERIFIED_NO_PETS"))) for s in successors]),
        ("census_arithmetic", OrderedDict((
            ("before", 256), ("retired", 1), ("added", 2),
            ("after", census["count"]),
            ("semantics", "Physical removal. The census carries no retired "
                          "state, so a superseded row cannot remain in it.")))),
        ("authority_after", OrderedDict((
            ("published_pet_friendly", counts["PUBLISHED_PET_FRIENDLY"]),
            ("verified_no_pets", counts["VERIFIED_NO_PETS"]),
            ("out_of_current_category", counts["OUT_OF_CURRENT_CATEGORY"]),
            ("resolved", resolved),
            ("unresolved", census["count"] - resolved),
            ("derivation",
             "unresolved = census - resolved, computed, never assumed")))),
    ))
    LEDGER.write_text(json.dumps(ledger, indent=1, ensure_ascii=False) + NL,
                      encoding="utf-8", newline=NL)
    print("WROTE %s" % LEDGER.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
