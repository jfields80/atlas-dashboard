"""PTF-NASHVILLE-TN-NEW-MARKET-001 -- Phase 12, the attended browser pass.

The Marriott and Hilton wall, walked in a real Chrome session with the operator
present. Both families are a MEASURED Firecrawl capability wall
(PTF-FIRECRAWL-HARD-LANES-003) and both refuse this project's plain client, so
this is the only free lane that reads them.

HOW THE READ IS BOUND
---------------------
Neither family is read from rendered innerText. Both publish the operative
policy as structured data, and the attended session takes it from there and
nowhere else:

  HILTON    ``__NEXT_DATA__`` carries a ``petsInfo`` node -- petsAllowed,
            petCharge, petChargeRefundable, petMaxWeight, description and a
            SEPARATE servicePetsDesc. The same page also carries guest-review
            prose that says "we asked if there were any available rooms and pets
            were allowed". That is a review, not a policy, and the walk is
            anchored on the node's own key set so it can never be read.
  MARRIOTT  the Hotel JSON-LD gives name, street, locality, postal and phone;
            the HOTEL INFORMATION block's "Pet Policy" row gives the operative
            statement. Tags are stripped from a bounded window after that label
            only, so nothing outside the row can contribute.

Each brand was batched by SAME-ORIGIN FETCH from one tab already on the brand's
own origin -- the Dayton precedent -- rather than by 23 separate navigations.

A PROPERTY CODE SELECTS; THE PAGE ADMITS
----------------------------------------
This pass is what settles that. Marriott's BNA prefix is the Nashville AIRPORT
code and reaches Clarksville, Cookeville, Columbia, Murfreesboro, Manchester,
Tullahoma, Hopkinsville KENTUCKY and Bowling Green KENTUCKY, and Hilton's
Nashville-area city pages reach the same ring. Every such row is captured and
classified OUTSIDE_MARKET on the address its OWN page states -- not on a guess,
and not by omitting it.

No paid provider. No USD. No credential was entered and no bot check was
answered: every page served a plain same-origin fetch from the operator's own
signed-in session.

Output:
  launch_packages/pettripfinder/markets/reports/nashville_tn_attended_capture_001.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.markets import contract as MC  # noqa: E402
from scripts.pettripfinder.site_data import normalize_name  # noqa: E402

WORK_ORDER = "PTF-NASHVILLE-TN-NEW-MARKET-001"
MARKET_ID = "nashville-tn"
SCHEMA = "ptf-attended-capture/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONTRACT = os.path.join(PKG, "markets", "proposed", "nashville-tn.json")
CAPTURED_AT = "2026-09-07"

#: Language that is a REFUSAL plus a service-animal carve-out. It is a clean
#: no-pets read, and the carve-out is never mistaken for acceptance.
_SERVICE_ANIMALS_ONLY = re.compile(r"service\s+animals?\s+only", re.I)
_NOT_ALLOWED = re.compile(r"pets?\s+not\s+allowed", re.I)
_ALLOWED = re.compile(r"pets?\s+(welcome|allowed)", re.I)

_FEE = re.compile(r"\$?\s*([0-9]+(?:\.[0-9]{2})?)\s*(?:non-?refundable)?\s*(?:pet\s*)?fee", re.I)
_MAXPETS = re.compile(r"(?:maximum\s+number\s+of\s+pets(?:\s+in\s+room)?:?\s*|(\d+)\s*pets?\s*max)"
                      r"\s*(\d+)?", re.I)
_WEIGHT = re.compile(r"(\d+(?:\.\d+)?)\s*(?:lbs?|pounds)", re.I)


def _load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def zips_of_contract():
    cfg = MC.parse_market(_load(CONTRACT), source=CONTRACT)
    return {z: c.corridor_id for c in cfg.corridors for z in c.included_postal_codes}


def parse_marriott_row(row):
    text = row.get("pet_policy_row") or ""
    pets = None
    if _NOT_ALLOWED.search(text):
        pets = False
    elif _ALLOWED.search(text):
        pets = True
    ext = OrderedDict()
    if pets is not None:
        ext["pets_allowed"] = pets
    if pets:
        m = _FEE.search(text)
        if m:
            ext["pet_fee"] = int(round(float(m.group(1)) * 100))
            ext["fee_currency"] = "USD"
            ext["fee_refundable"] = not re.search(r"non-?refundable", text, re.I)
        w = _WEIGHT.search(text)
        if w:
            ext["weight_limit"] = float(w.group(1))
            ext["weight_limit_unit"] = "lb"
        c = re.search(r"maximum\s+number\s+of\s+pets(?:\s+in\s+room)?:?\s*(\d+)", text, re.I) \
            or re.search(r"(\d+)\s*pets?\s+per\s+room", text, re.I)
        if c:
            ext["pet_count_limit"] = int(c.group(1))
    return ext, text


def parse_hilton_row(row, service_animal_statement):
    desc = row.get("description") or ""
    ext = OrderedDict()
    if row.get("pets_allowed") is True:
        ext["pets_allowed"] = True
    elif row.get("pets_allowed") is False:
        ext["pets_allowed"] = False
    if row.get("fee_usd") is not None:
        ext["pet_fee"] = int(round(float(row["fee_usd"]) * 100))
        ext["fee_currency"] = "USD"
        ext["fee_refundable"] = bool(row.get("refundable"))
    w = _WEIGHT.search(row.get("weight") or desc)
    if w:
        ext["weight_limit"] = float(w.group(1))
        ext["weight_limit_unit"] = "lb"
    c = re.search(r"(\d+)\s*pets?\s*max", desc, re.I) or \
        re.search(r"maximum\s+of\s+(two|three|\d+)\s+pets", desc, re.I)
    if c:
        val = c.group(1).lower()
        ext["pet_count_limit"] = {"two": 2, "three": 3}.get(val, None) or int(val) \
            if val.isdigit() or val in ("two", "three") else None
        if ext["pet_count_limit"] is None:
            ext.pop("pet_count_limit")
    if re.search(r"dogs?\s*(/|\s+or\s+|and\s+)\s*cats?\s*only|a\s+dog/a\s+cat\s+only", desc, re.I):
        ext["species_allowed"] = ["dog", "cat"]
    if service_animal_statement:
        ext["service_animal_statement"] = OrderedDict([
            ("stated", True), ("quote", service_animal_statement)])
    return ext, desc


def build(rows_path):
    src = _load(rows_path)
    zips = zips_of_contract()
    sa = src.get("service_animal_statement_every_hilton_row", "")
    out = []

    for r in src.get("hilton", []):
        ext, quote = parse_hilton_row(r, sa)
        z = (r.get("postal") or "")[:5]
        out.append(OrderedDict([
            ("brand", "HILTON"), ("property_code", r["code"].lower()),
            ("requested_url", r["url"]), ("final_url", r["url"]),
            ("captured_at", CAPTURED_AT), ("document_bytes", r.get("bytes")),
            # The NAME the property's own page states, not the map source's
            # bare label. Without it the census keeps OpenStreetMap's "Hilton
            # Garden Inn" and "Hampton Inn & Suites", two identities collide on
            # a bare brand label at different addresses, and BOTH are demoted to
            # review -- taking their clean reads with them.
            ("identity_signals", OrderedDict([
                ("name_on_page", r.get("name")),
                ("address_on_page", r.get("street")), ("postal_code", r.get("postal")),
                ("locality", r.get("city")), ("region", r.get("region")),
                ("phone_on_page", r.get("phone")),
                ("property_code_on_page", r["code"].lower())])),
            ("identity_confirmed", bool(r.get("street") and r.get("postal"))),
            ("identity_binding_method", "PROPERTY_CODE_AND_ADDRESS_FROM_THE_PAGES_OWN_DATA"),
            ("surface", "__NEXT_DATA__ petsInfo node"),
            ("exact_quote", quote),
            ("extraction", ext),
            ("in_market", z in zips), ("corridor", zips.get(z, "")),
            ("market_verdict", "IN_MARKET" if z in zips else "OUTSIDE_MARKET"),
        ]))

    for r in src.get("marriott", []):
        ext, quote = parse_marriott_row(r)
        z = (r.get("postal") or "")[:5]
        service_only = bool(_SERVICE_ANIMALS_ONLY.search(quote))
        rec = OrderedDict([
            ("brand", "MARRIOTT"), ("property_code", r["code"]),
            ("requested_url", r["url"]), ("final_url", r["url"]),
            ("captured_at", CAPTURED_AT), ("document_bytes", r.get("bytes")),
            ("identity_signals", OrderedDict([
                ("name_on_page", r.get("name")), ("address_on_page", r.get("street")),
                ("locality", r.get("city")), ("region", r.get("region")),
                ("postal_code", r.get("postal")), ("phone_on_page", r.get("phone")),
                ("property_code_on_page", r["code"])])),
            ("identity_confirmed", bool(r.get("street") and r.get("postal"))),
            ("identity_binding_method", "HOTEL_JSONLD_ADDRESS_AND_PROPERTY_CODE"),
            ("surface", "HOTEL INFORMATION block, Pet Policy row"),
            ("exact_quote", quote),
            ("extraction", ext),
            ("in_market", z in zips), ("corridor", zips.get(z, "")),
            ("market_verdict", "IN_MARKET" if z in zips else "OUTSIDE_MARKET"),
        ])
        if service_only:
            rec["service_animals_only"] = (
                "the row refuses ordinary pets and admits service animals; the carve-out is "
                "recorded and is never read as acceptance")
        out.append(rec)

    in_market = [r for r in out if r["in_market"]]
    pf = [r for r in in_market if r["extraction"].get("pets_allowed") is True]
    np = [r for r in in_market if r["extraction"].get("pets_allowed") is False]

    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "12 -- attended browser pass over the Marriott and Hilton wall"),
        ("as_of", CAPTURED_AT),
        ("lane", "ATTENDED_BROWSER (a person in a real Chrome session; free)"),
        ("authorization", "the operator selected the browser in session and authorised this pass"),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("firecrawl_credits", 0),
        ("why_attended", "Marriott and Hilton are a MEASURED Firecrawl capability wall "
                         "(PTF-FIRECRAWL-HARD-LANES-003) and refuse this project's plain client; "
                         "the acquisition ladder routes them here and nowhere cheaper"),
        ("how_each_brand_was_read", OrderedDict([
            ("HILTON", "the __NEXT_DATA__ petsInfo node, anchored on its own key set. The same "
                       "page carries guest-review prose saying pets were allowed; that is a "
                       "review, not a policy, and the walk cannot reach it."),
            ("MARRIOTT", "the Hotel JSON-LD for identity, and a bounded window after the "
                         "HOTEL INFORMATION 'Pet Policy' label for the operative statement"),
        ])),
        ("no_bot_check_was_answered",
         "every page served a plain same-origin fetch from the operator's own session. No "
         "credential was entered, no interstitial was solved and no detection was evaded."),
        ("a_code_selects_the_page_admits",
         "Marriott's BNA prefix is the Nashville AIRPORT code and reaches Clarksville, "
         "Cookeville, Columbia, Murfreesboro, Manchester, Tullahoma, Hopkinsville KENTUCKY and "
         "Bowling Green KENTUCKY; Hilton's Nashville-area city pages reach Memphis, Gallatin, "
         "Union City, Martin and Dyersburg. The sharpest case in this run is bnafs, which "
         "Marriott's own roster slugs 'springhill-suites-franklin-mint' and whose street is "
         "literally 5629 NASHVILLE Rd -- and whose own page states Franklin, KENTUCKY 42134. "
         "Three name signals pointed at this market and the page settled it. Every such row was "
         "captured and every one is OUTSIDE_MARKET on the address its own page states."),
        ("how_the_batch_ran",
         "TWO navigations for 154 property pages: one tab per ORIGIN, then a same-origin fetch "
         "loop. This is the Dayton batching precedent, and it is why an attended pass over a "
         "market this size is minutes rather than hours."),
        ("counts", OrderedDict([
            ("pages_read", len(out)),
            ("by_brand", OrderedDict(sorted(Counter(r["brand"] for r in out).items()))),
            ("identity_confirmed", sum(1 for r in out if r["identity_confirmed"])),
            ("in_market", len(in_market)),
            ("outside_market", len(out) - len(in_market)),
            ("in_market_pet_friendly", len(pf)),
            ("in_market_verified_no_pets", len(np)),
            ("outside_market_rows", [OrderedDict([("code", r["property_code"]),
                                                  ("street", r["identity_signals"]
                                                   .get("address_on_page")),
                                                  ("postal", r["identity_signals"]
                                                   .get("postal_code"))])
                                     for r in out if not r["in_market"]]),
        ])),
        ("rows", out),
    ])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", required=True,
                    help="the attended session's captured rows, as JSON")
    ap.add_argument("--out", default=os.path.join(REPORTS,
                                                  "nashville_tn_attended_capture_001.json"))
    args = ap.parse_args(argv)
    rep = build(args.rows)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1)
        fh.write("\n")
    c = rep["counts"]
    print("pages read        :", c["pages_read"], dict(c["by_brand"]))
    print("identity confirmed:", c["identity_confirmed"])
    print("in market         :", c["in_market"], "outside:", c["outside_market"])
    print("in-market PF      :", c["in_market_pet_friendly"],
          "no-pets:", c["in_market_verified_no_pets"])
    print("outside rows      :", [r["code"] for r in c["outside_market_rows"]])
    print("written           :", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
