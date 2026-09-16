"""PTF-TAMPA-FL-V2-TERMINAL-HOLD-CLOSURE-003 -- FAST rule G
(CROSS_MARKET_IDENTITY_COLLISION) caught a bare, generic census name --
"Staybridge Suites" (DBPR's own record has no city qualifier) -- colliding
with an existing Louisville, KY identity of the same bare name. Same root
cause and fix as the source-ready build's own rule-G fix for "TownePlace
Suites by Marriott" (commit e66579ab): the building's own page states its
full name ("Staybridge Suites St. Petersburg Downtown", confirmed via this
pass's supported-browser read at property code piesb), so the census row is
renamed to that stated name -- never a truncation -- and its
identity_key/slug/aliases are re-derived from it.
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.contracts.identity_key import ptf_identity_key  # noqa: E402

PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
TARGETS = [
    os.path.join(PKG, "identity_census_proposed", "tampa-fl.json"),
    os.path.join(PKG, "markets", "staging", "tampa-fl", "launch_package", "identity_census", "tampa-fl.json"),
]

OLD_KEY = "staybridge suites"
NEW_NAME = "Staybridge Suites St. Petersburg Downtown"
NEW_KEY = ptf_identity_key(NEW_NAME)
NEW_SLUG = re.sub(r"[^a-z0-9]+", "-", NEW_NAME.lower()).strip("-")
PROPERTY_CODE = "piesb"
OFFICIAL_URL = "https://www.ihg.com/staybridge/hotels/us/en/st-petersburg/piesb/hoteldetail"


def main():
    for path in TARGETS:
        census = json.load(open(path, encoding="utf-8"))
        changed = 0
        for h in census["hotels"]:
            if h["identity_key"] != OLD_KEY:
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
        print(path, "renamed", changed, "row(s) ->", NEW_KEY)


if __name__ == "__main__":
    main()
