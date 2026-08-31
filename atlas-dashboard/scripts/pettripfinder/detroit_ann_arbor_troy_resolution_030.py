# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-TROY-IDENTITY-AND-BUNDLE-030, Phases 2 to 4.

Records the founder's SAME_CAMPUS_DISTINCT_ENTITY ruling on 575 W Big Beaver
Rd, Troy, so both IHG hotels there keep their listings.

NO SHARED CODE CHANGES. The mechanism already exists and already works: the
listing dataset builder dedupes by street address, and ``_run_base_chain``
already hands it ``publication_guard.distinct_entity_groups()`` -- the reviewed
exceptions a human recorded. Detroit's pair was simply never recorded, so the
dedup did what it is supposed to do to an UNREVIEWED shared address: it kept
one listing. The renderer then warned "missing hotel profile file for Hotel
Indigo Detroit North Troy" and three pages linked to a page that was never
written.

THAT IS WHY THIS IS A CONFIGURATION FIX AND NOT A CODE FIX. Widening the
builder to allow any shared address through would hand duplicate publication
rights to every unreviewed collision in every market -- the precise failure the
dedup exists to prevent. The exception stays exactly as wide as the founder's
ruling: two named identities at one address key.

THE RESOLUTION ASSERTS NOTHING ABOUT EITHER PROPERTY'S POLICY. It is an
identity decision and authorises no publication; both records were already
published on their own evidence.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import OrderedDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import publication_guard as PG            # noqa: E402

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-TROY-IDENTITY-AND-BUNDLE-030"
FOUNDER = "jfields80"
REVIEWED_AT = "2026-08-31T09:00:00-04:00"
RESOLUTION_ID = "res-detroit-big-beaver-dual-brand"
ADDRESS_KEY = "575|beaver|48084"

PATH = _REPO_ROOT / "launch_packages" / "pettripfinder" / "identity_resolutions.json"

IDENTITIES = [
    OrderedDict([
        ("canonical_name", "EVEN Hotel Detroit North Troy"),
        ("category", "pet-friendly-hotels"),
        ("slug", "even-hotel-detroit-north-troy"),
        ("official_url",
         "https://www.ihg.com/evenhotels/hotels/us/en/troy/dttry/hoteldetail"),
        ("booking_destination",
         "https://www.ihg.com/evenhotels/hotels/us/en/troy/dttry/hoteldetail"),
        ("property_code", "DTTRY"),
        ("building", "575 W Big Beaver Rd, Building 1"),
    ]),
    OrderedDict([
        ("canonical_name", "Hotel Indigo Detroit North Troy"),
        ("category", "pet-friendly-hotels"),
        ("slug", "hotel-indigo-detroit-north-troy"),
        ("official_url",
         "https://www.ihg.com/hotelindigo/hotels/us/en/troy/dttoy/hoteldetail"),
        ("booking_destination",
         "https://www.ihg.com/hotelindigo/hotels/us/en/troy/dttoy/hoteldetail"),
        ("property_code", "DTTOY"),
        ("building", "575 W Big Beaver Rd, Building 2"),
    ]),
]


def run():
    doc = json.loads(PATH.read_text(encoding="utf-8-sig"))
    existing = {r["resolution_id"] for r in doc["resolutions"]}
    if RESOLUTION_ID in existing:
        raise SystemExit("STOP: %s is already recorded" % RESOLUTION_ID)

    resolution = OrderedDict([
        ("resolution_id", RESOLUTION_ID),
        ("resolution_type", PG.SAME_CAMPUS),
        ("address_key", ADDRESS_KEY),
        ("identities", IDENTITIES),
        ("evidence",
         "IHG publishes these as two properties with two property codes "
         "(DTTRY, DTTOY) on two current first-party pages, each stating its "
         "own pet policy, in two buildings on one campus at 575 W Big Beaver "
         "Rd, Troy MI 48084. Both are in Detroit's identity census and both "
         "already carry published authority on their own evidence. They also "
         "share a switchboard telephone number, which is what a single campus "
         "reception looks like and is NOT evidence that they are one hotel -- "
         "this market has ruled before that a shared street does not make one "
         "building, and a shared phone does not either."),
        ("distinct_reason",
         "a two-building campus operated as two hotels under two IHG brands, "
         "each with its own property code, its own first-party page, its own "
         "front-desk inventory and its own pet policy. The founder's ruling "
         "states both are DISTINCT CURRENT IHG HOTEL IDENTITIES: do not merge, "
         "do not retire either, do not treat one as a rebrand of the other."),
        ("market_id", MARKET),
        ("decision_source", OrderedDict([
            ("work_order", WORK_ORDER),
            ("kind", "FOUNDER_IDENTITY_DECISION"),
            ("scope", "identity only; authorises no publication"),
            ("prepared_by",
             "PTF-DETROIT-ANN-ARBOR-HARDENED-SYNC-029, whose dry-run assembly "
             "surfaced three broken links to a profile the address dedup had "
             "silently collapsed"),
        ])),
        ("reviewer_id", FOUNDER),
        ("reviewed_at", REVIEWED_AT),
    ])
    # THE CONTRACT'S OWN DERIVATION, not one invented here. The first run of
    # this module hashed a hand-rolled digest and validate_resolutions refused
    # it -- correctly. A resolution hash that only its author can reproduce
    # proves nothing about the resolution.
    resolution["resolution_hash"] = PG.resolution_hash(resolution)

    doc["resolutions"].append(resolution)
    PATH.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")

    groups = PG.distinct_entity_groups()
    names = tuple(sorted(i["canonical_name"] for i in IDENTITIES))
    print("=== Phase 2: same-campus resolution recorded ===")
    print("   id           :", RESOLUTION_ID)
    print("   address_key  :", ADDRESS_KEY)
    for identity in IDENTITIES:
        print("   %-32s %s  %s" % (identity["canonical_name"],
                                   identity["property_code"],
                                   identity["building"]))
    print()
    print("=== Phase 4: the builder now sees the exception ===")
    print("   distinct_entity_groups:", len(groups), "reviewed groups")
    print("   this pair present     :", names in groups)
    if names not in groups:
        raise SystemExit("STOP: the builder would still collapse this pair")


if __name__ == "__main__":
    run()
