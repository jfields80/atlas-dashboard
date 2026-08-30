# -*- coding: utf-8 -*-
"""PTF-PITTSBURGH-HARDENED-SYNC-004 Phase 9 -- the Marriott legacy-template repair.

    python -m scripts.pettripfinder.pittsburgh_marriott_route_repair_004 --write

THE DEFECT
-----------
Pittsburgh's acquisition split cleanly on Marriott URL SHAPE:

    /en-us/hotels/...      10 / 10  VALID
    /hotels/travel/...      0 / 16  FAILED

which is the Detroit finding (PTF-DETROIT-BRIGHTDATA-PILOT-014: 0/2 on the
legacy template, 11/11 on the current one) repeated in another market. It is a
routing defect, not a lane failure, and it costs nothing to repair.

THE REWRITE IS DERIVED, NOT GUESSED
-------------------------------------
Both halves of the modern path are already inside the committed legacy URL:

    https://www.marriott.com/hotels/travel/pitar-ac-hotel-pittsburgh-downtown/
                                           ^^^^^ ^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                           code  slug
    -> https://www.marriott.com/en-us/hotels/pitar-ac-hotel-pittsburgh-downtown/overview/

So no name is parsed, no property is looked up, and no network call is made. The
target shape is not assumed either: it is the shape of all ten Marriott URLs
this market's census already holds in the modern template and all twelve that
its published policy records were successfully acquired from -- every one of
them ``/en-us/hotels/<code>-<slug>/overview/``. Pittsburgh Airport Marriott
(pitmc) proves the mapping end to end: the legacy census URL and the modern URL
this market separately owns for that identity are the same property under the
two templates.

WHAT IS CHECKED BEFORE A ROW IS REWRITTEN
-------------------------------------------
Per row, and any failure leaves it ROUTING_REPAIR_REQUIRED rather than guessed:

  * the host is exactly ``www.marriott.com``
  * the path matches the legacy template exactly
  * the property code is 5-6 lowercase alphanumerics
  * the slug is non-empty and contains the code nowhere else
  * the rewritten URL is claimed by NO other Pittsburgh identity
  * the property code is claimed by NO other Pittsburgh identity

WHAT THIS DELIBERATELY DOES NOT TOUCH
---------------------------------------
Three PUBLISHED policy records carry a legacy URL in ``source_url``. That field
is EVIDENCE PROVENANCE -- it records where a hash-bound artifact was actually
fetched from, and the founder's approval binds it. Rewriting it would falsify
the provenance of evidence nobody re-fetched, and would move a record_hash an
approval names. Those stay exactly as they are; only the acquisition-addressable
``official_url`` on the census identity is repaired.

This is ROUTING REPAIR ONLY. No acquisition, no provider call, no spend.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.contracts import census as CENSUS_CONTRACT   # noqa: E402
from scripts.pettripfinder.pittsburgh_hardened_sync_004 import (        # noqa: E402
    AS_OF, CENSUS, MARKET_ID, REPORTS, WORK_ORDER, _load, _write,
    property_codes)

LEDGER = REPORTS / "pittsburgh_hardened_sync_004_marriott_route_repair.json"

LEGACY = re.compile(
    r"^https://www\.marriott\.com/hotels/travel/([a-z0-9]{5,6})-([a-z0-9][a-z0-9-]*[a-z0-9])/?$")
MODERN = "https://www.marriott.com/en-us/hotels/%s-%s/overview/"


class RepairError(RuntimeError):
    pass


def plan() -> Tuple[Dict, List[Dict], List[Dict]]:
    census = _load(CENSUS)
    hotels = census["hotels"]

    # Every URL and property code this market already claims, so a rewrite can
    # never land on another identity's page.
    claimed_urls, claimed_codes = {}, {}
    for hotel in hotels:
        url = (hotel.get("official_url") or "").strip().rstrip("/")
        if url:
            claimed_urls.setdefault(url, hotel["identity_key"])
        for code in property_codes(hotel.get("official_url")):
            claimed_codes.setdefault(code, hotel["identity_key"])

    repaired, refused = [], []
    for hotel in hotels:
        url = (hotel.get("official_url") or "").strip()
        if "/hotels/travel/" not in url:
            continue
        key = hotel["identity_key"]
        found = LEGACY.match(url)
        if not found:
            refused.append(OrderedDict((
                ("identity_key", key), ("official_url", url),
                ("state", "ROUTING_REPAIR_REQUIRED"),
                ("why", "the URL does not match the legacy Marriott template "
                        "exactly, so no code and slug can be derived from it"))))
            continue
        code, slug = found.group(1), found.group(2)
        if code in slug:
            refused.append(OrderedDict((
                ("identity_key", key), ("official_url", url),
                ("state", "ROUTING_REPAIR_REQUIRED"),
                ("why", "the property code %r also appears inside the slug, so "
                        "the split is ambiguous" % code))))
            continue
        rewritten = MODERN % (code, slug)
        owner = claimed_urls.get(rewritten.rstrip("/"))
        if owner is not None and owner != key:
            refused.append(OrderedDict((
                ("identity_key", key), ("official_url", url),
                ("state", "ROUTING_REPAIR_REQUIRED"),
                ("why", "the rewritten URL is already claimed by %r" % owner))))
            continue
        code_owner = claimed_codes.get("marriott:%s" % code)
        if code_owner is not None and code_owner != key:
            refused.append(OrderedDict((
                ("identity_key", key), ("official_url", url),
                ("state", "ROUTING_REPAIR_REQUIRED"),
                ("why", "property code %r is already claimed by %r"
                        % (code, code_owner)))))
            continue
        repaired.append(OrderedDict((
            ("identity_key", key),
            ("canonical_name", hotel.get("canonical_name")),
            ("property_code", code),
            ("slug", slug),
            ("host", "www.marriott.com"),
            ("legacy_url", url),
            ("repaired_url", rewritten),
        )))
    return census, repaired, refused


def apply_repairs(census: Dict, repaired: List[Dict]) -> Dict:
    by_key = {r["identity_key"]: r for r in repaired}
    out = json.loads(json.dumps(census))
    for hotel in out["hotels"]:
        row = by_key.get(hotel["identity_key"])
        if row is None:
            continue
        if (hotel.get("official_url") or "").strip() != row["legacy_url"]:
            raise RepairError("%s moved under the repair" % hotel["identity_key"])
        hotel["official_url"] = row["repaired_url"]
    return out


def run(write: bool) -> int:
    census, repaired, refused = plan()
    print("census rows              : %d" % len(census["hotels"]))
    print("legacy Marriott routes   : %d" % (len(repaired) + len(refused)))
    print("deterministically repaired: %d" % len(repaired))
    print("ROUTING_REPAIR_REQUIRED  : %d" % len(refused))
    for row in repaired:
        print("   %-46s %s -> /en-us/.../overview/"
              % (row["identity_key"][:45], row["property_code"]))
    for row in refused:
        print("   REFUSED %-40s %s" % (row["identity_key"][:39], row["why"]))

    fixed = apply_repairs(census, repaired)
    if len(fixed["hotels"]) != len(census["hotels"]):
        raise RepairError("the census row count moved")
    urls = [h.get("official_url") for h in fixed["hotels"] if h.get("official_url")]
    if len(set(urls)) != len(urls):
        raise RepairError("the repair created a duplicate canonical URL")
    issues = CENSUS_CONTRACT.validate(fixed)
    if issues:
        raise RepairError("the repaired census does not validate: %s"
                          % list(issues)[:5])
    print("duplicate canonical URLs : 0")
    print("census contract issues   : %d" % len(issues))
    if not write:
        print("(check only -- pass --write)")
        return 0

    _write(CENSUS, fixed)
    print("WROTE %s" % CENSUS.name)
    _write(LEDGER, OrderedDict((
        ("schema", "ptf-market-routing-repair/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("as_of", AS_OF),
        ("defect", "Marriott legacy template: /en-us/hotels/ 10/10 VALID, "
                   "/hotels/travel/ 0/16 in Pittsburgh acquisition"),
        ("rewrite", "https://www.marriott.com/hotels/travel/<code>-<slug>/ -> "
                    "https://www.marriott.com/en-us/hotels/<code>-<slug>/overview/"),
        ("derivation",
         "Both the property code and the slug are taken from the committed "
         "legacy URL itself. No name is parsed, no property looked up, and no "
         "network call made. The target shape is the shape of all ten modern "
         "Marriott URLs this census already held and all twelve its published "
         "records were acquired from."),
        ("not_touched",
         "Three published policy records carry a legacy URL in source_url. "
         "That field is evidence provenance for a hash-bound artifact and the "
         "founder's approval binds it, so it is left exactly as committed."),
        ("acquisition_performed", "none -- routing repair only, $0.00"),
        ("repaired_count", len(repaired)),
        ("refused_count", len(refused)),
        ("repaired", repaired),
        ("routing_repair_required", refused),
    )))
    print("WROTE %s" % LEDGER.name)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        return run(args.write)
    except RepairError as exc:
        print("REFUSED: %s" % exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
