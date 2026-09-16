"""PTF-TAMPA-FL-V2-REGISTRATION-AND-FOUNDER-PACKET-004 -- build_global_authority
caught a bare, generic exclusion name -- "Fairfield Inn & Suites" (DBPR/brand
route named only the flag, no city qualifier) -- colliding with an existing
Lexington, KY identity of the same bare name in
launch_packages/pettripfinder/markets/authority/lexington-ky/hotel_exclusions.json.
Same root cause and fix as the two prior Tampa collisions (TownePlace Suites /
Cleveland, commit e66579ab; Staybridge Suites / Louisville, commit 2ef48b64):
the building's own page states its full name ("Fairfield Inn & Suites St.
Petersburg North", property code tpasn,
https://www.marriott.com/en-us/hotels/tpasn-fairfield-inn-and-suites-st-petersburg-north/overview/),
so the row is renamed to that stated name -- never a truncation -- and its
identity_key/normalized_name/exclusion_id are re-derived from it. Lexington's
own file is never touched.
"""
from __future__ import annotations

import json
import os
import sys

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.contracts.identity_key import ptf_identity_key  # noqa: E402

PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")

OLD_KEY = "fairfield inn and suites"
NEW_NAME = "Fairfield Inn & Suites St. Petersburg North"
NEW_KEY = ptf_identity_key(NEW_NAME)
NEW_NORMALIZED = NEW_NAME.lower().replace("&", "and").replace(".", "")
NEW_SLUG = NEW_NORMALIZED.replace(" ", "-")
PROPERTY_CODE = "tpasn"
OFFICIAL_URL = "https://www.marriott.com/en-us/hotels/tpasn-fairfield-inn-and-suites-st-petersburg-north/overview/"


def fix_census() -> int:
    total = 0
    for path in (
        os.path.join(PKG, "identity_census", "tampa-fl.json"),
        os.path.join(PKG, "identity_census_proposed", "tampa-fl.json"),
        os.path.join(PKG, "markets", "staging", "tampa-fl", "launch_package", "identity_census", "tampa-fl.json"),
    ):
        if not os.path.exists(path):
            print(path, "MISSING, skipped")
            continue
        census = json.load(open(path, encoding="utf-8"))
        changed = 0
        for h in census["hotels"]:
            if h.get("identity_key") != OLD_KEY:
                continue
            h["canonical_name"] = NEW_NAME
            h["identity_key"] = NEW_KEY
            h["slug"] = NEW_SLUG
            h["property_code"] = PROPERTY_CODE
            h["official_url"] = OFFICIAL_URL
            aliases = set(h.get("identity_key_aliases") or [])
            aliases.add(OLD_KEY)
            aliases.add(NEW_KEY)
            h["identity_key_aliases"] = sorted(aliases)
            changed += 1
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(census, f, indent=1, sort_keys=False, ensure_ascii=False)
            f.write("\n")
        print(path, "census renamed", changed, "row(s) ->", NEW_KEY)
        total += changed
    return total


def fix_authority() -> int:
    total = 0
    for path in (
        os.path.join(PKG, "tampa_fl_proposed_authority_004.json"),
        os.path.join(PKG, "markets", "staging", "tampa-fl", "tampa_fl_v2_proposed_authority_001.json"),
    ):
        if not os.path.exists(path):
            print(path, "MISSING, skipped")
            continue
        doc = json.load(open(path, encoding="utf-8"))
        changed = 0
        for key in ("pet_friendly", "verified_no_pets", "records", "unresolved"):
            records = doc.get(key)
            if not isinstance(records, list):
                continue
            for r in records:
                if not isinstance(r, dict) or r.get("identity_key") != OLD_KEY:
                    continue
                r["identity_key"] = NEW_KEY
                r["normalized_name"] = NEW_NORMALIZED
                r["canonical_name"] = NEW_NAME
                if "exclusion_id" in r:
                    r["exclusion_id"] = "tampa-fl--" + NEW_SLUG
                changed += 1
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(doc, f, indent=1, sort_keys=False, ensure_ascii=False)
            f.write("\n")
        print(path, "authority renamed", changed, "row(s) ->", NEW_KEY)
        total += changed
    return total


def fix_partition() -> int:
    total = 0
    for path in (
        os.path.join(PKG, "tampa_fl_final_partition_v2_001.json"),
        os.path.join(PKG, "markets", "staging", "tampa-fl", "launch_package", "tampa_fl_final_partition_v2_001.json"),
    ):
        if not os.path.exists(path):
            print(path, "MISSING, skipped")
            continue
        doc = json.load(open(path, encoding="utf-8"))
        changed = 0
        for it in doc.get("items", []):
            if not isinstance(it, dict) or it.get("identity_key") != OLD_KEY:
                continue
            it["identity_key"] = NEW_KEY
            it["canonical_name"] = NEW_NAME
            changed += 1
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(doc, f, indent=1, sort_keys=False, ensure_ascii=False)
            f.write("\n")
        print(path, "partition renamed", changed, "row(s) ->", NEW_KEY)
        total += changed
    return total


def main():
    total = fix_census() + fix_authority() + fix_partition()
    print("TOTAL ROWS CHANGED:", total)


if __name__ == "__main__":
    main()
