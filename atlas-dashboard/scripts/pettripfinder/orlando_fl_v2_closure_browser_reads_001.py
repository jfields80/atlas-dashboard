"""PTF-ORLANDO-FL-V2-TARGETED-COVERAGE-CLOSURE-002 -- supported-browser transcriptions for targeted non-brand hotels.

The attended browser rung (navigate + the accessibility tree `find` / `get_page_text`; no page script, no relay, no bot
check) was used only for targets whose own page refused a plain client or rendered its policy client-side. Each entry
below is a verbatim transcription; its TRANSCRIPTION_SHA256 is the sha256 of the entry's canonical JSON. A row is
emitted as a read only when the transcription binds to the census identity by the street and postal code a first-party
page states; otherwise it is recorded in `not_read` with the exact reason (it stays a hold).

Output: launch_packages/pettripfinder/markets/staging/orlando-fl/raw_captures/closure_browser_rows.json
"""
from __future__ import annotations

import hashlib
import json
import os
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
CENSUS = os.path.join(PKG, "identity_census", "orlando-fl.json")
OUT = os.path.join(PKG, "markets", "staging", "orlando-fl", "raw_captures", "closure_browser_rows.json")

TRANSCRIPTIONS = [
    OrderedDict([
        ("identity_key", "hard rock hotel at universal orlando"), ("brand", "LOEWS"),
        ("policy_url", "https://www.universalorlando.com/web/en/us/places-to-stay/hard-rock-hotel"),
        ("policy_title", "Hard Rock Hotel®: Live Like a Star"),
        ("policy_text", ["Pet Policy",
                         "Pets are permitted for a $150††† fee in a pet-friendly room category (if you book a non-pet room, "
                         "you’ll be re-assigned one upon arrival) with no more than two pets in any one guest room."]),
        ("policy_tool", "get_page_text (Hotel Policies article)"),
        ("address_url", "https://www.loewshotels.com/hard-rock-hotel"), ("address_title", "Hard Rock Hotel | Universal Orlando Resort"),
        ("address_text", "5800 Universal Boulevard, Orlando, 32819"), ("address_tool", "find ref_237"),
        ("address_street", "5800 Universal Boulevard"), ("address_postal", "32819"),
        ("page_name", "Hard Rock Hotel at Universal Orlando"),
        ("extraction", OrderedDict([("pets_allowed", True), ("pet_count_limit", 2)])),
        ("cohorts", ["BRINGFIDO"]), ("captured_at", "2026-09-15"),
    ]),
    OrderedDict([
        # the plain client read this page 200 twice during probing, then 403 twice in the lane: the browser rung
        ("identity_key", "omni championsgate resort hotel lp"), ("brand", "OMNI"),
        ("policy_url", "https://www.omnihotels.com/hotels/orlando-championsgate/property-details/policies"),
        ("policy_title", "Orlando Florida Hotels | Policies of Omni Orlando Resort"),
        ("policy_text", ["Pet Policy",
                         "Pets under 50 lbs. are allowed on the second floor of the main resort building, deluxe rooms only. E"]),
        ("policy_tool", "find ref_2685 heading + ref_2686 paragraph (text node truncated by the reader)"),
        ("address_url", "https://www.omnihotels.com/hotels/orlando-championsgate/property-details/policies"),
        ("address_title", "Orlando Florida Hotels | Policies of Omni Orlando Resort"),
        ("address_text", "1500 Masters Boulevard ChampionsGate Florida 33896"), ("address_tool", "find ref_2709"),
        ("address_street", "1500 Masters Boulevard"), ("address_postal", "33896"),
        ("extraction", OrderedDict([("pets_allowed", True), ("weight_limit", 50), ("weight_limit_unit", "lb")])),
        ("page_name", "Omni Orlando Resort at ChampionsGate"),
        ("cohorts", ["CORRIDOR_CRITICAL:four-corners-davenport"]), ("captured_at", "2026-09-15"),
    ]),
    OrderedDict([
        ("identity_key", "red roof inn orlando south florida mall"), ("brand", "RED_ROOF"),
        ("policy_url", "https://www.redroof.com/property/fl/orlando/rri766"),
        ("policy_title", "Cheap Hotel Near Florida Mall in South Orlando | Red Roof"),
        ("policy_text", ["One, well-behaved domestic pet (cat or dog) Stays Free! Pets must be declared at check-in. Up to 2 p"]),
        ("policy_tool", "find ref_227 (text node truncated by the reader)"),
        ("address_url", "https://www.redroof.com/property/fl/orlando/rri766"), ("address_title", ""),
        ("address_text", "8296 S Orange Blossom Trl, Orlando FL"), ("address_tool", "find ref_88; no element on the page states 32809"),
        ("address_street", "8296 S Orange Blossom Trl"), ("address_postal", ""), ("page_name", "Red Roof Inn Orlando South - Florida Mall"),
        ("extraction", OrderedDict([("pets_allowed", True)])),
        ("cohorts", ["BRINGFIDO"]), ("captured_at", "2026-09-15"),
    ]),
]


def _census_building(census, t):
    """The census building this transcription names: its key, a key alias, or -- because the census renames a building
    to the name its own page states once this read joins -- the one building at the stated house number and postal
    code. Used ONLY to check the binding; nothing is copied from the census into the read (the read must be the same
    whichever census state it is rebuilt against)."""
    for h in census:
        if h["identity_key"] == t["identity_key"] or t["identity_key"] in (h.get("identity_key_aliases") or []):
            return h
    num, z = t["address_street"].split()[0], t["address_postal"]
    hits = [h for h in census if (h.get("street") or "").split()[:1] == [num] and (h.get("postal_code") or "")[:5] == z]
    return hits[0] if len(hits) == 1 else None


def main():
    census = json.load(open(CENSUS, encoding="utf-8"))["hotels"]
    rows, not_read = [], []
    for t in TRANSCRIPTIONS:
        sha = hashlib.sha256(json.dumps(t, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        h = _census_building(census, t)
        street, z = t["address_street"], t["address_postal"]
        num = street.split()[0] if street else ""
        bound = bool(h and z and t["address_text"].startswith(num + " ") and z in t["address_text"]
                     and (h.get("street") or "").split()[:1] == [num] and (h.get("postal_code") or "")[:5] == z)
        if not bound:
            not_read.append(OrderedDict([("identity_key", t["identity_key"]), ("transcription_sha256", sha),
                                         ("why", "NO_FIRST_PARTY_PAGE_STATES_THE_CENSUS_STREET_AND_POSTAL_CODE"),
                                         ("address_text", t["address_text"]), ("policy_text", t["policy_text"])]))
            continue
        rows.append(OrderedDict([
            ("identity_key", t["identity_key"]), ("brand", t["brand"]), ("n", t["page_name"]),
            ("u", t["policy_url"]),
            ("final_url", t["policy_url"]), ("st", street), ("z", z), ("ph", ""), ("h", sha),
            ("b", len(json.dumps(t, ensure_ascii=False).encode("utf-8"))), ("q", " ".join(t["policy_text"])),
            ("extraction", t["extraction"]), ("binding", "ADDRESS_ON_THE_OPERATOR_PROPERTY_PAGE_PLUS_POLICY_ON_THE_OPERATOR_HOTEL_PAGE"),
            ("sha_kind", "TRANSCRIPTION_SHA256"), ("cohorts", t["cohorts"]), ("transcription", t),
        ]))
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(OrderedDict([("rows", rows), ("not_read", not_read)]), fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("browser reads", len(rows), "not read", [x["identity_key"] for x in not_read])


if __name__ == "__main__":
    main()
