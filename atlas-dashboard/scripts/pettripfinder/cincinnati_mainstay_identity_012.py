# -*- coding: utf-8 -*-
"""PTF-CINCINNATI-MAINSTAY-IDENTITY-012 -- settle the held Choice identity.

    python -m scripts.pettripfinder.cincinnati_mainstay_identity_012
    python -m scripts.pettripfinder.cincinnati_mainstay_identity_012 --write

WHAT THE EVIDENCE SHOWS
-----------------------
The census row "Comfort Suites Mainstay Hotel" does not name one hotel that was
renamed. It names TWO, and Choice's own listing proves it: at 2347 Reading Road
there are two separate properties with two property codes, two buildings, two
phones and two review counts.

    oh720  Comfort Suites Cincinnati University - Downtown
           2347 Reading Road, Building A, Cincinnati OH 45202, (513) 743-7508
    oh721  MainStay Suites Cincinnati University - Uptown
           2347 Reading Road, Building B, Cincinnati OH 45202, (513) 202-3971

The census row carries neither phone -- it states (513) 394-6073 -- and a postal
code, 45219, that neither property uses. Its name pairs two Choice BRANDS,
which is the shape of a directory row that collapsed a dual-brand campus into
one entry. So this is not a rename and not a near-miss: it is one census
identity standing where two hotels are.

WHY NO POLICY IS PUBLISHED, EVEN THOUGH BOTH REFUSE PETS
--------------------------------------------------------
Both properties state "Pets Allowed: No", so it is tempting to register the
refusal and move on. That would be wrong. An exclusion record carries a
canonical name, a street, a postal code, a phone and an official URL, and its
normalized_name must derive from its canonical name. Registering one record for
two hotels would publish a refusal that is wrong about the building, wrong
about the phone and wrong about the URL for whichever of the two a reader
happened to want -- and it would put the market's identity authority on record
as believing two hotels are one.

The right repair is a SPLIT: retire the conflated row and add oh720 and oh721
as their own identities. That is a census mutation, and this order is
explicitly forbidden from adding census identities. So the finding is recorded,
the row stays unresolved, its route stays active because it still needs
working, and the split is handed to its own order.

THE ROUTING RECORD ALSO OVERSTATED ITS BINDING
----------------------------------------------
Its identity_signals_matched claimed binding:postal_code and binding:phone, and
neither holds -- the same record's own note says the page states 45202 against
the census's 45219, and the phones differ. The recovery artifact that produced
it recorded verdict BRAND_PROPERTY_URL_FOUND_2OF3 while listing six signals, so
the list was a template rather than a measurement. It is corrected here to what
actually matches. That is an identity-only repair: no policy, no counts, no
identity key.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import market_authority as MA               # noqa: E402

WORK_ORDER = "PTF-CINCINNATI-MAINSTAY-IDENTITY-012"
MARKET_ID = "cincinnati-oh"
AS_OF = "2026-08-31"
KEY = "comfort suites mainstay hotel"

PKG = _REPO_ROOT / "launch_packages" / "pettripfinder"
CENSUS = PKG / "identity_census" / "cincinnati-oh.json"
PARTITION = PKG / "cincinnati_final_partition_001.json"
FINDING = PKG / "markets" / "reports" / "cincinnati_mainstay_identity_012.json"

CLASSIFICATION = "SEPARATE_BUILDING_IDENTITY"

#: What Choice's own first-party pages state, observed attended at zero cost.
OBSERVED = OrderedDict((
    ("oh720", OrderedDict((
        ("property_code", "oh720"),
        ("name", "Comfort Suites Cincinnati University - Downtown"),
        ("street", "2347 Reading Road, Building A"),
        ("city", "Cincinnati"), ("state", "OH"), ("postal_code", "45202"),
        ("phone", "5137437508"),
        ("official_property_url",
         "https://www.choicehotels.com/ohio/cincinnati/comfort-suites-hotels/oh720"),
        ("reviews", 436),
        ("pets", "Pets Allowed: No General: Only service animals are "
                 "permitted, free of charge."),
        ("sha256_page",
         "b1ca728d-e49ecbc6-266d5553-61873a90-eb515bad-17a3a5ba-4dc9e6ae-2c0a725f"),
        ("in_census", False)))),
    ("oh721", OrderedDict((
        ("property_code", "oh721"),
        ("name", "MainStay Suites Cincinnati University - Uptown"),
        ("street", "2347 Reading Road, Building B"),
        ("city", "Cincinnati"), ("state", "OH"), ("postal_code", "45202"),
        ("phone", "5132023971"),
        ("official_property_url",
         "https://www.choicehotels.com/ohio/cincinnati/mainstay-hotels/oh721"),
        ("reviews", 144),
        ("pets", "Pets Allowed: No General: Only service animals are "
                 "permitted, free of charge."),
        ("sha256_page",
         "ade36a79-9fe351ce-130d945d-8464e8e9-a82e651c-26dce47b-32b5d7b9-6f24a5a1"),
        ("in_census", False)))),
))

#: The signals that actually hold between the census row and oh721. The shard
#: claimed six; four survive contact with the pages.
TRUE_SIGNALS = ["binding:street_number", "binding:street_name",
                "binding:city", "binding:state", "binding:property_code"]

ROUTE_NOTE = (
    "%s: IDENTITY CONFLATION. Choice's own listing shows TWO properties at "
    "2347 Reading Road -- oh720 Comfort Suites Cincinnati University - "
    "Downtown in Building A ((513) 743-7508) and oh721 MainStay Suites "
    "Cincinnati University - Uptown in Building B ((513) 202-3971). This "
    "census row's name pairs both Choice brands and its phone (513) 394-6073 "
    "matches neither, while its postal code 45219 matches neither page (both "
    "state 45202). The route points at oh721 only, so it binds ONE of the two "
    "hotels this identity denotes. identity_signals_matched previously claimed "
    "binding:postal_code and binding:phone; neither holds and both are "
    "removed. The route stays ACTIVE because the row is unresolved and still "
    "needs working. Resolution requires splitting the census row into oh720 "
    "and oh721, which is a census-add order and is NOT done here."
    % WORK_ORDER)

IDENTITY_REVIEW = OrderedDict((
    ("classification", CLASSIFICATION),
    ("reviewed_by", WORK_ORDER),
    ("reviewed_on", AS_OF),
    ("finding",
     "This row denotes two distinct Choice properties sharing one street "
     "address in separate buildings: oh720 (Comfort Suites, Building A) and "
     "oh721 (MainStay Suites, Building B). Its canonical name pairs both "
     "brands, its phone matches neither property, and its postal code matches "
     "neither page."),
    ("not_a_rename",
     "A rename supersedes one identity with one identity. There is no single "
     "hotel this row could be renamed to without silently discarding the "
     "other."),
    ("not_merged_with", "mainstay suites cincinnati blue ash"),
    ("not_merged_because",
     "A separate MainStay property in the Blue Ash corridor at postal code "
     "45242, itself still AWAITING_IDENTITY_RESOLUTION. Brand similarity is "
     "not identity."),
    ("policy_withheld",
     "Both properties refuse pets, but an exclusion record carries one "
     "canonical name, street, postal code, phone and URL, and its "
     "normalized_name must derive from its canonical name. One record for two "
     "hotels would be wrong about the building, the phone and the URL, and "
     "would put identity authority on record as believing two hotels are one."),
    ("resolution_requires",
     "A census split: retire this row and add oh720 and oh721 as their own "
     "identities. That is a census-add work order and was not performed here."),
))


class IdentityError(RuntimeError):
    pass


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def build():
    census = _load(CENSUS)
    row = next((h for h in census["hotels"] if h["identity_key"] == KEY), None)
    if row is None:
        raise IdentityError("%s is not in the census" % KEY)
    if row.get("identity_review"):
        raise IdentityError("%s already carries an identity_review" % KEY)

    doc = MA.load_market_routing_document(MARKET_ID)
    route = next((r for r in doc["routes"]
                  if r["hotel_ref"]["identity_key"] == KEY), None)
    if route is None:
        raise IdentityError("%s has no route; the founder ordered it kept"
                            % KEY)
    if route["status"] != "ROUTING_CONFIRMED":
        raise IdentityError("%s route is %s, not confirmed"
                            % (KEY, route["status"]))

    # The claim this order disproves, asserted before it is corrected.
    claimed = list(route.get("identity_signals_matched") or [])
    for stale in ("binding:postal_code", "binding:phone"):
        if stale not in claimed:
            raise IdentityError(
                "the route no longer claims %s, so this correction has "
                "already been made or the record changed" % stale)

    before = OrderedDict((
        ("census_name", row["canonical_name"]),
        ("census_street", row["address"]),
        ("census_postal_code", row["postal_code"]),
        ("census_phone", row["phone"]),
        ("route_property_code", route.get("property_code", "")),
        ("route_url", route["official_property_url"]),
        ("route_signals_claimed", claimed),
        ("route_status", route["status"]),
    ))
    return census, row, doc, route, before


def apply_changes(row, route):
    row["identity_review"] = IDENTITY_REVIEW
    route["identity_signals_matched"] = list(TRUE_SIGNALS)
    route["notes"] = ROUTE_NOTE
    route["verified_at"] = AS_OF


def repoint_partition(partition):
    """The blocker is identity, not observation. Say so.

    The row stays UNRESOLVED either way, so no count moves; what changes is
    which queue it truthfully sits in.
    """
    item = next(i for i in partition["items"] if i["identity_key"] == KEY)
    was = item["final_state"]
    item["final_state"] = "AWAITING_IDENTITY_RESOLUTION"
    item["resolved"] = False
    item["determined_by"] = WORK_ORDER
    item["updated_at"] = AS_OF
    item["state_override_reason"] = (
        "%s: this census row denotes TWO Choice properties at 2347 Reading "
        "Road -- oh720 (Comfort Suites, Building A) and oh721 (MainStay, "
        "Building B). It cannot be renamed to either and no policy may bind "
        "to it. Resolution requires a census split." % WORK_ORDER)
    from collections import Counter
    counts = Counter(i["final_state"] for i in partition["items"])
    partition["final_state_counts"] = OrderedDict(sorted(counts.items()))
    return was, item["final_state"]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        census, row, doc, route, before = build()
    except IdentityError as exc:
        print("REFUSED: %s" % exc)
        return 2

    print("classification         : %s" % CLASSIFICATION)
    print("census name            : %s" % before["census_name"])
    print("census postal / phone  : %s / %s"
          % (before["census_postal_code"], before["census_phone"]))
    for code, prop in OBSERVED.items():
        print("  %-6s %-52s %s %s"
              % (code, prop["name"][:52], prop["postal_code"], prop["phone"]))
    print("signals claimed        : %s" % ", ".join(before["route_signals_claimed"]))
    print("signals that hold      : %s" % ", ".join(TRUE_SIGNALS))
    print("policy applied         : none -- identity is not settled")
    print("route                  : stays ACTIVE (row still needs working)")
    if not args.write:
        print("(check only -- pass --write)")
        return 0

    apply_changes(row, route)
    CENSUS.write_text(json.dumps(census, indent=1, ensure_ascii=False) + "\n",
                      encoding="utf-8", newline="\n")
    print("WROTE %s (identity_review recorded, identity unchanged)"
          % CENSUS.name)

    shard = MA.build_routing_shard(MARKET_ID, doc["routes"],
                                   doc.get("source_batches") or ())
    MA.routing_shard_path(MARKET_ID).write_text(
        MA.render_json(shard), encoding="utf-8", newline="\n")
    print("WROTE routing shard (signals corrected, %d routes)"
          % len(doc["routes"]))

    partition = _load(PARTITION)
    was, now = repoint_partition(partition)
    partition["as_of"] = AS_OF
    PARTITION.write_text(json.dumps(partition, indent=1, ensure_ascii=False)
                         + "\n", encoding="utf-8", newline="\n")
    print("WROTE partition (%s -> %s, still unresolved)" % (was, now))

    finding = OrderedDict((
        ("schema", "ptf-market-identity-determination/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("as_of", AS_OF),
        ("identity_key", KEY),
        ("classification", CLASSIFICATION),
        ("provider_calls", 0),
        ("paid_spend_usd", 0.0),
        ("capture_method", "attended_chrome_render"),
        ("census_before", before),
        ("observed_first_party", OBSERVED),
        ("conflicting_evidence", [
            "name: the census pairs two Choice brands ('Comfort Suites' and "
            "'Mainstay'); each real property carries one",
            "postal_code: census 45219; both pages state 45202",
            "phone: census 5133946073; oh720 states 5137437508 and oh721 "
            "states 5132023971 -- the census phone matches neither",
            "building: oh720 is Building A and oh721 is Building B at the "
            "same street number, which is identity-significant",
        ]),
        ("why_the_stronger_signals_win",
         "Two distinct Choice property codes with two distinct phones, two "
         "buildings and two independent review counts are the strongest "
         "identity evidence available, and they are first-party. A shared "
         "street NUMBER is the weakest signal in the set and is the only one "
         "the census row has in common with either page."),
        ("policy_may_bind", False),
        ("route_remains_active", True),
        ("other_identities_affected", [OrderedDict((
            ("identity_key", "mainstay suites cincinnati blue ash"),
            ("effect", "none -- a different MainStay in the Blue Ash corridor "
                       "at 45242, itself still AWAITING_IDENTITY_RESOLUTION")))]),
        ("authority_change", "none"),
        ("routing_signal_correction", OrderedDict((
            ("claimed", before["route_signals_claimed"]),
            ("actually_hold", TRUE_SIGNALS),
            ("removed", ["binding:postal_code", "binding:phone"]),
            ("why", "PTF-CINCINNATI-URL-ROUTING-RECOVERY-001 recorded verdict "
                    "BRAND_PROPERTY_URL_FOUND_2OF3 for this row while listing "
                    "six binding signals, so the list was a template rather "
                    "than a measurement. Both removed signals are "
                    "contradicted by the record's own note.")))),
        ("follow_up_required", OrderedDict((
            ("work_order", "PTF-CINCINNATI-MAINSTAY-CENSUS-SPLIT-013"),
            ("what", "Retire the conflated row and add oh720 and oh721 as "
                     "their own census identities, then bind each property's "
                     "own refusal to its own identity."),
            ("why_not_here", "This order is forbidden from adding census "
                             "identities."),
            ("evidence_already_owned",
             "Both property pages were captured attended at zero cost and "
             "their digests are recorded above; the split needs no new "
             "acquisition."),
        ))),
    ))
    FINDING.write_text(json.dumps(finding, indent=1, ensure_ascii=False) + "\n",
                       encoding="utf-8", newline="\n")
    print("WROTE %s" % FINDING.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
