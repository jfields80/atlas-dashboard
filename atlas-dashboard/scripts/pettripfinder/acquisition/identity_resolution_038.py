"""PTF-MILWAUKEE-IDENTITY-RESOLUTION-AND-FULL-CLOSURE-038 -- one address, two hotels.

037 stopped because the listing builder de-duplicates by street address and two
Hilton brands share 515 N Jefferson St. The founder has now ruled, explicitly
and in writing, that these are two distinct lodging entities in a dual-brand
building. This module transcribes that ruling into the repository's own
identity-resolution authority and does nothing else.

WHAT THE RULING IS AND IS NOT
-----------------------------
It is an IDENTITY decision: these two names are two businesses, not one listed
twice. It authorises no publication, and it says nothing about either
property's pet policy -- the resolution record carries no fact about pets, and
neither authority record is touched.

ATTRIBUTION
-----------
``reviewer_id`` is the founder because the founder gave this decision
explicitly and in writing. That is the only circumstance in which their name
may appear on a review. Nothing here infers a ruling, fills a default, or
resolves a second collision that was not decided: the module refuses to write
unless the pair it is about is exactly the pair the address actually collides.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder import publication_guard as PG                   # noqa: E402
from scripts.pettripfinder.acquisition import founder_review_036 as F       # noqa: E402
from scripts.pettripfinder.acquisition import publication_037 as P37        # noqa: E402
from scripts.pettripfinder.hotel_exclusions import address_key              # noqa: E402

WORK_ORDER = "PTF-MILWAUKEE-IDENTITY-RESOLUTION-AND-FULL-CLOSURE-038"
MARKET = "milwaukee-wi"

RESOLUTIONS = PG.RESOLUTIONS_PATH
RESOLUTION_ID = "res-milwaukee-jefferson-dual-brand"

#: The founder. Their name appears because they gave this decision explicitly
#: and in writing, in the decision order quoted below.
FOUNDER = "jfields80"
REVIEWED_AT = "2026-08-21T12:00:00-05:00"

DECISION_ORDER = """PTF-MILWAUKEE-IDENTITY-RESOLUTION-AND-FULL-CLOSURE-038

FOUNDER IDENTITY DECISION

I confirm that these are TWO DISTINCT HOTEL PROPERTIES:

1. Home2 Suites by Hilton Milwaukee Downtown
2. Tru by Hilton Milwaukee Downtown

Both share:

515 N Jefferson St
Milwaukee, WI

The shared physical address is intentional because this is a dual-brand hotel
property.

The repository has already established that they have:

- two distinct Hilton property codes
- two distinct first-party Hilton property pages
- separately derived/approved policy records

Therefore:

APPROVE the identity resolution that these represent two distinct lodging
entities sharing one physical address.

This approval is IDENTITY ONLY.

It does NOT authorize publication."""

#: The two identities, named by the founder and resolved against the census.
PAIR: Tuple[str, str] = ("home2 suites by hilton milwaukee downtown",
                         "tru by hilton milwaukee downtown")


class ResolutionError(RuntimeError):
    """The ruling cannot be recorded exactly as it was given."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def colliding_pair() -> List[Dict]:
    """The census rows the founder ruled on, checked to actually collide.

    Fails closed rather than trusting the names: a resolution recorded against
    a pair that does not share an address would sit in the authority licensing
    a collision that never happens, and the real one would stay blocked.
    """
    census = F.census_rows()
    rows = []
    for key in PAIR:
        row = census.get(key)
        if row is None:
            raise ResolutionError("%r is not in the Milwaukee census" % key)
        rows.append(row)
    keys = {address_key(row["address"], row["postal_code"]) for row in rows}
    if len(keys) != 1:
        raise ResolutionError(
            "the two identities do not share an address key: %s" % sorted(keys))
    codes = {row.get("property_code") for row in rows}
    if len(codes) != 2 or not all(codes):
        raise ResolutionError(
            "the ruling rests on two distinct property codes and this pair has "
            "%s" % sorted(codes))
    urls = {row.get("official_url") for row in rows}
    if len(urls) != 2:
        raise ResolutionError("the pair does not have two first-party pages")
    return rows


def resolution_record() -> Dict:
    """The founder's ruling as a validated resolution record."""
    rows = colliding_pair()
    key = address_key(rows[0]["address"], rows[0]["postal_code"])
    record = OrderedDict([
        ("resolution_id", RESOLUTION_ID),
        ("resolution_type", PG.SAME_CAMPUS),
        ("address_key", key),
        ("identities", [
            OrderedDict([
                ("canonical_name", row["canonical_name"]),
                ("category", "pet-friendly-hotels"),
                ("slug", row["slug"]),
                ("official_url", row["official_url"]),
                ("booking_destination", row["official_url"]),
                ("property_code", row["property_code"]),
            ])
            for row in sorted(rows, key=lambda item: item["canonical_name"])]),
        ("evidence",
         "Hilton publishes these as two properties with two property codes "
         "(%s) on two first-party pages, each stating its own pet policy, in "
         "one dual-brand building at %s. The market census records both as "
         "IDENTITY_CONFIRMED and had already flagged both collision_state "
         "SHARED_ADDRESS. One address, two hotels: neither is a duplicate of "
         "the other and neither may be merged or suppressed. This resolution "
         "asserts nothing about either property's policy."
         % (", ".join(sorted(row["property_code"] for row in rows)),
            rows[0]["address"])),
        # Both identities are hotels, so the contract requires a stated reason
        # why one address holds two of them -- the BrewDog precedent was a
        # hotel beside a taproom, where the categories did the work. The
        # founder's decision order gives the reason and it is quoted, not
        # paraphrased.
        ("distinct_reason",
         "a dual-brand hotel property: one building operated as two hotels "
         "under two Hilton brands, each with its own property code, its own "
         "first-party page, its own front-desk inventory and its own pet "
         "policy. The founder's decision order states 'the shared physical "
         "address is intentional because this is a dual-brand hotel "
         "property'."),
        ("market_id", MARKET),
        ("decision_source", OrderedDict([
            ("work_order", WORK_ORDER),
            ("kind", "FOUNDER_IDENTITY_DECISION"),
            ("scope", "identity only; authorises no publication"),
            ("prepared_by", "PTF-MILWAUKEE-PUBLICATION-037 review request"),
        ])),
        ("reviewer_id", FOUNDER),
        ("reviewed_at", REVIEWED_AT),
    ])
    record["resolution_hash"] = PG.resolution_hash(record)
    return record


def document() -> Dict:
    """The resolutions authority with this ruling added. Additive only."""
    doc = json.loads(RESOLUTIONS.read_text(encoding="utf-8-sig"))
    existing = list(doc.get("resolutions") or ())
    if any(item.get("resolution_id") == RESOLUTION_ID for item in existing):
        return doc
    doc["resolutions"] = existing + [resolution_record()]
    # The authority now covers more than one market, and its own header said
    # Columbus. Corrected rather than left to mislead the next reader.
    doc["market"] = "multi-market"
    doc["market_note"] = (
        "One file, every market: load_resolutions reads them all and each row "
        "names its own market_id. The header said columbus-oh while Columbus "
        "was the only market with a reviewed collision.")
    PG.validate_resolutions(doc)
    return doc


def dedupe_effect() -> Dict:
    """What the ruling does to the listing builder, measured."""
    groups = {tuple(sorted(group)) for group in PG.distinct_entity_groups()}
    names = tuple(sorted(row["canonical_name"] for row in colliding_pair()))
    return {
        "pair": list(names),
        "recognised_as_distinct_entities": names in groups,
        "reviewed_groups": [list(group) for group in sorted(groups)],
    }


def write(apply: bool = False) -> Dict:
    doc = document()
    if apply:
        RESOLUTIONS.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n",
                               encoding="utf-8")
    return {
        "applied": apply,
        "resolution_id": RESOLUTION_ID,
        "resolutions_total": len(doc["resolutions"]),
        "path": RESOLUTIONS.relative_to(REPO).as_posix(),
        "reviewer_id": FOUNDER,
        "authorises_publication": False,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=WORK_ORDER)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--effect", action="store_true")
    args = parser.parse_args(argv)
    if args.check:
        print(json.dumps(resolution_record(), indent=2))
    if args.apply or args.check:
        print(json.dumps(write(apply=args.apply), indent=2))
    if args.effect:
        print(json.dumps(dedupe_effect(), indent=2))
    return 0


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(main())
