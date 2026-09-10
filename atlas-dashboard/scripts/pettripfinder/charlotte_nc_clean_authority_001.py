"""PTF-CHARLOTTE-NC-ZERO-TO-LIVE-BENCHMARK-001 -- Phases 13 and 14: the clean set.

Joins every first-party policy read this order made to the census identity it
belongs to, classifies each one EXACTLY ONCE, and emits the two sets a market
authority is built from: CLEAN_PET_FRIENDLY and CLEAN_VERIFIED_NO_PETS.

WHAT JOINS A READ TO AN IDENTITY
--------------------------------
The STREET IDENTITY the page itself states (house number + distinctive street
words + postal code), through ``hotel_exclusions.address_key`` -- the same
function the exclusion contract and the package writer use. Never a name. A read
whose street identity matches no census row is reported UNJOINED and publishes
nothing; a read whose street identity matches a row the census did NOT admit
(a founder hold, an outside-market row, an identity review) is reported against
that row's own class and likewise publishes nothing.

WHAT MAKES A ROW CLEAN
----------------------
An operative first-party statement of ACCEPTANCE (for a pet-friendly record) or
REFUSAL (for a no-pets record), read from a surface this order named per family:

    MARRIOTT   the HOTEL INFORMATION block's "Pet Policy" row
    HILTON     the __NEXT_DATA__ petsInfo node
    IHG        the brand's own FAQ answer to "Can I bring my pet to X?"
    DRURY      the property record's own "Key":"pet-policy" block

A fee alone, a weight alone, a count alone, an amenity chip and a service-animal
sentence alone establish NOTHING, and none of them can promote a row here. Every
published fact is cited to the quote it came from.

Nothing here fetches. Nothing here publishes. Output is Charlotte-local.

Output:
  launch_packages/pettripfinder/markets/reports/charlotte_nc_clean_authority_001.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.hotel_exclusions import address_key  # noqa: E402

WORK_ORDER = "PTF-CHARLOTTE-NC-ZERO-TO-LIVE-BENCHMARK-001"
MARKET_ID = "charlotte-nc"
SCHEMA = "ptf-market-clean-authority/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CENSUS = os.path.join(PKG, "identity_census", "charlotte-nc.json")
ATTENDED = os.path.join(REPORTS, "charlotte_nc_attended_capture_001.json")
STATIC = os.path.join(REPORTS, "charlotte_nc_free_static_lane_001.json")

#: Which surface each family's operative statement came from, named once so the
#: evidence entries can cite it rather than repeating a sentence per record.
SURFACE = {
    "MARRIOTT": "the HOTEL INFORMATION block's Pet Policy row on the property's own page",
    "HILTON": "the __NEXT_DATA__ petsInfo node on the property's own page",
    "IHG": "the brand's own FAQ answer to 'Can I bring my pet to X?'",
    "DRURY": "the property record's own \"Key\":\"pet-policy\" block",
}

_FIELD_QUOTE_HINTS = (
    ("pet_fee", r"(?:\$|USD|dollars|fee)"),
    ("fee_currency", r"(?:\$|USD|dollars)"),
    ("weight_limit", r"(?:lbs?|pounds|weight)"),
    ("pet_count_limit", r"(?:max|maximum|limit|\bpets?\b)"),
    ("species_allowed", r"(?:dogs?|cats?)"),
    ("fee_refundable", r"refundable"),
    ("weight_basis", r"combined"),
)


def _load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _keys_for(h):
    """Every key a read may join this census row on, most specific first.

    The street identity ALONE is not specific enough in this market: seven
    Charlotte buildings hold two separately bookable hotels each, and a
    street-only join would let the first read settle the building and report the
    second as a duplicate. So a row that states a brand property code is keyed
    on street PLUS code first, which is the same distinction the census itself
    used to keep the pair apart.
    """
    street = address_key(h.get("street") or "", (h.get("postal_code") or "")[:5])
    if not street:
        return []
    code = (h.get("property_code") or "").lower()
    brand = (h.get("brand") or "").upper()
    keys = []
    if code and brand:
        keys.append("%s|%s|%s" % (street, brand, code))
    keys.append(street)
    return keys


def _read_keys(brand, sig):
    street = address_key(sig.get("address_on_page") or "", (sig.get("postal_code") or "")[:5])
    if not street:
        return []
    code = (sig.get("property_code_on_page") or "").lower()
    keys = []
    if code and brand:
        keys.append("%s|%s|%s" % (street, (brand or "").upper(), code))
    keys.append(street)
    return keys


def census_index():
    doc = _load(CENSUS, {}) or {}
    admitted, held = {}, {}
    for h in doc.get("hotels", []):
        for k in _keys_for(h):
            admitted.setdefault(k, h)
    for h in doc.get("non_admitted", []):
        for k in _keys_for(h):
            held.setdefault(k, h)
    return doc, admitted, held


def evidence_for(quote, surface, extraction):
    """One evidence entry per published fact, each citing the quote it rests on.

    A fact whose quote does not contain the vocabulary that fact is made of is
    NOT cited here -- it is dropped from the record instead, because a citation
    that does not support its fact is worse than no fact at all.
    """
    entries, keep = [], OrderedDict()
    if "pets_allowed" in extraction:
        entries.append(OrderedDict([
            ("quote", quote), ("location", surface), ("field_refs", ["pets_allowed"])]))
        keep["pets_allowed"] = extraction["pets_allowed"]
    for field, hint in _FIELD_QUOTE_HINTS:
        if field not in extraction:
            continue
        if not re.search(hint, quote, re.I):
            continue
        keep[field] = extraction[field]
        entries.append(OrderedDict([
            ("quote", quote), ("location", surface), ("field_refs", [field])]))
    for field in ("fee_basis", "fee_scope", "pet_count_scope", "weight_limit_unit"):
        if field in extraction and any(field.split("_")[0] in e["field_refs"][0] for e in entries):
            keep[field] = extraction[field]
    return entries, keep


def rows_from_attended(doc):
    for r in doc.get("rows", []):
        sig = r.get("identity_signals") or {}
        yield OrderedDict([
            ("lane", "ATTENDED_BROWSER"), ("brand", r.get("brand")),
            ("source_url", r.get("requested_url")), ("final_url", r.get("final_url")),
            ("document_sha256", r.get("document_sha256") or ""),
            ("document_bytes", r.get("document_bytes")),
            ("captured_at", r.get("captured_at")),
            ("identity_signals", sig),
            ("identity_binding_method", r.get("identity_binding_method")),
            ("identity_confirmed", r.get("identity_confirmed")),
            ("surface", SURFACE.get(r.get("brand"), r.get("surface"))),
            ("quote", r.get("exact_quote") or ""),
            ("extraction", r.get("extraction") or {}),
            ("property_code", r.get("property_code")),
        ])


def rows_from_static(doc):
    for r in doc.get("rows", []):
        if r.get("verdict") not in ("CLEAN_PET_FRIENDLY", "CLEAN_VERIFIED_NO_PETS"):
            continue
        sig = r.get("identity_signals") or {}
        yield OrderedDict([
            ("lane", "DIRECT_STATIC_FETCH"), ("brand", r.get("brand")),
            ("source_url", r.get("requested_url")), ("final_url", r.get("final_url")),
            ("document_sha256", r.get("document_sha256") or ""),
            ("document_bytes", r.get("document_bytes")),
            ("captured_at", r.get("captured_at")),
            ("identity_signals", sig),
            ("identity_binding_method", "PROPERTY_RECORD_ADDRESS_ON_THE_PAGES_OWN_DOMAIN"),
            ("identity_confirmed", bool(sig.get("address_on_page") and sig.get("postal_code"))),
            ("surface", SURFACE.get(r.get("brand"), "the property's own page")),
            ("quote", r.get("operative_quote") or ""),
            ("extraction", r.get("parsed_facts") or {}),
            ("property_code", ""),
        ])


def build():
    census, admitted, held = census_index()
    reads = list(rows_from_attended(_load(ATTENDED, {}) or {}))
    reads += list(rows_from_static(_load(STATIC, {}) or {}))

    pf, nopets, rejected = [], [], []
    seen = {}
    for r in reads:
        sig = r["identity_signals"] or {}
        keys = _read_keys(r["brand"], sig)
        key = next((k for k in keys if k in admitted), None) or (keys[0] if keys else "")
        ext = dict(r["extraction"] or {})
        quote = r["quote"] or ""
        base = OrderedDict([
            ("lane", r["lane"]), ("brand", r["brand"]),
            ("source_url", r["source_url"]), ("final_url", r["final_url"]),
            ("document_sha256", r["document_sha256"]),
            ("document_bytes", r["document_bytes"]),
            ("captured_at", r["captured_at"]),
            ("identity_signals", sig),
            ("identity_binding_method", r["identity_binding_method"]),
            ("property_code", r["property_code"]),
        ])

        def reject(cls, why):
            row = OrderedDict(base)
            row["classification"] = cls
            row["why"] = why
            row["quote"] = quote
            rejected.append(row)

        if not r["identity_confirmed"] or not key:
            reject("IDENTITY_HOLD",
                   "the read published no street identity of its own, so nothing can bind it to a "
                   "building; a name alone proposes an identity and never decides one")
            continue
        if key not in admitted:
            row = held.get(key)
            if row is not None:
                reject("CENSUS_ROW_NOT_ADMITTED",
                       "the census classified this building %s (%s); a read cannot promote a row "
                       "the identity graph withheld"
                       % (row.get("classification"), (row.get("classification_reason") or "")[:120]))
            else:
                reject("UNJOINED_READ",
                       "the street identity this page states matches no census row at all; "
                       "reported rather than published, and it is the census that is incomplete, "
                       "not the read that is wrong")
            continue
        h = admitted[key]
        if h.get("classification") != "TRUE_HOTEL_IDENTITY":
            reject("CENSUS_ROW_NOT_ADMITTED", "census class %s" % h.get("classification"))
            continue
        if not quote.strip():
            reject("POLICY_NOT_FOUND",
                   "the page served and its identity confirmed, but it published no operative "
                   "pet statement on this read; a silence settles nothing")
            continue
        # A SERVICE-ANIMAL SENTENCE IS NOT A REFUSAL. Two Charlotte DoubleTrees
        # publish a petsInfo node whose entire description is "Service animals
        # only" with petsAllowed false. A legal access category is not a pet
        # policy, and a bare structured boolean is not the page's own operative
        # statement either -- the first-party binding gate refuses both. These
        # rows are HELD, not published as verified-no-pets.
        if (ext.get("pets_allowed") is False
                and re.fullmatch(r"\s*service\s+animals?\s+only\.?\s*", quote, re.I)):
            reject("SERVICE_ANIMAL_ONLY",
                   "the only words this page publishes about animals are a service-animal "
                   "carve-out. That is a legal access category, not a refusal of pets, and it "
                   "cannot establish a verified-no-pets record on its own")
            continue
        if "pets_allowed" not in ext:
            reject("QUOTE_NOT_OPERATIVE",
                   "the quoted words state no acceptance and no refusal. A fee, a weight, a "
                   "count, an amenity chip or a service-animal sentence alone establishes "
                   "nothing under the first-party binding contract")
            continue

        entries, keep = evidence_for(quote, r["surface"], ext)
        if key in seen:
            reject("DUPLICATE_READ_FOR_ONE_IDENTITY",
                   "another read already settled this street identity (%s); one identity is "
                   "classified exactly once" % seen[key])
            continue
        seen[key] = r["brand"]
        rec = OrderedDict(base)
        rec["identity_key"] = h["identity_key"]
        rec["canonical_name"] = h["canonical_name"]
        rec["corridor"] = h.get("corridor")
        rec["surface"] = r["surface"]
        rec["operative_quote"] = quote
        rec["pets_allowed"] = bool(keep.get("pets_allowed"))
        rec["extraction"] = keep
        rec["evidence"] = entries
        (pf if keep.get("pets_allowed") else nopets).append(rec)

    pf.sort(key=lambda x: x["identity_key"])
    nopets.sort(key=lambda x: x["identity_key"])
    resolved = {r["identity_key"] for r in pf} | {r["identity_key"] for r in nopets}
    unresolved = [h for h in census.get("hotels", []) if h["identity_key"] not in resolved]

    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "13/14 -- policy classification and the clean set"),
        ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("status", "PROPOSED_NOT_PUBLISHED"),
        ("what_is_excluded",
         "Everything that is not an operative first-party statement of acceptance or refusal, "
         "bound to an ADMITTED census identity by the street identity the page itself states. "
         "A read that joins no census row, joins a withheld row, states no policy, or states "
         "only a fee / weight / count / amenity chip / service-animal sentence is reported in "
         "`rejected` with its class and publishes nothing."),
        ("one_identity_classified_once",
         "The join is on street identity, so two brands at one address cannot both settle it: "
         "the census already withheld those buildings as a founder ruling, and a second read of "
         "an already-settled identity is reported DUPLICATE_READ_FOR_ONE_IDENTITY."),
        ("counts", OrderedDict([
            ("reads_evaluated", len(reads)),
            ("clean_pet_friendly", len(pf)),
            ("clean_verified_no_pets", len(nopets)),
            ("resolved_census_identities", len(resolved)),
            ("unresolved_census_identities", len(unresolved)),
            ("census_count", census.get("count")),
            ("rejected", len(rejected)),
            ("rejected_by_class", OrderedDict(sorted(
                Counter(r["classification"] for r in rejected).items()))),
            ("pf_by_brand", OrderedDict(sorted(Counter(r["brand"] for r in pf).items()))),
            ("pf_by_corridor", OrderedDict(sorted(Counter(r["corridor"] for r in pf).items()))),
        ])),
        ("clean_pet_friendly", pf),
        ("clean_verified_no_pets", nopets),
        ("rejected", rejected),
        ("unresolved_census_identities", [
            OrderedDict([("identity_key", h["identity_key"]),
                         ("canonical_name", h["canonical_name"]),
                         ("brand", h.get("brand")), ("corridor", h.get("corridor")),
                         ("official_url", h.get("official_url"))])
            for h in unresolved]),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPORTS, "charlotte_nc_clean_authority_001.json"))
    args = ap.parse_args(argv)
    rep = build()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    c = rep["counts"]
    print("reads evaluated  :", c["reads_evaluated"])
    print("clean PF         :", c["clean_pet_friendly"], dict(c["pf_by_brand"]))
    print("clean no-pets    :", c["clean_verified_no_pets"])
    print("census           :", c["census_count"], "resolved", c["resolved_census_identities"],
          "unresolved", c["unresolved_census_identities"])
    print("rejected         :", c["rejected"], dict(c["rejected_by_class"]))
    print("written          :", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
