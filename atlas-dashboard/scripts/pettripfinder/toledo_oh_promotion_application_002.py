"""PTF-TOLEDO-OH-PROMOTION-AND-APPLICATION-002 -- Phases 3 and 4, the applier.

Turns the Toledo shadow into shared production source. It is the only file in
this order that writes outside a Toledo-named path, and it says exactly which
shared paths it touches and why.

WHAT IT BUILDS

  markets/authority/toledo-oh/seed_businesses.csv        the market's display rows
  markets/authority/toledo-oh/hotel_exclusions.json      the 10 VERIFIED_NO_PETS
  markets/authority/toledo-oh/identity_routing.json      empty; no override needed
  markets/authority/toledo-oh/affiliate_destinations.json empty; none authored
  hotel_policy_facts_toledo-oh.json                      the 17 published rows
  toledo_oh_final_partition_001.json                     every census identity, once

THE RULES IT IS BUILT AROUND, EACH ONE PAID FOR BY A PRIOR ORDER

  * The market edits its SHARD only. The three globals are GENERATED from every
    market's shard and are never hand-edited; this module calls
    MA.*_shard_path and never writes a global itself.
  * The READER decides pets_allowed. Nothing here re-derives it from a fee, a
    weight or a count; the value comes from the audited read and the quote that
    supports it travels with it.
  * service_animal_statement is STRUCTURED. A bare quote string crashes the
    renderer, so it is emitted as an object or not at all.
  * A published name must round-trip normalize_name -> identity_key or the join
    fails CLOSED. Every row is checked before it is written.
  * fee_tiers, not a flattened number. Several Hilton rows state a per-night
    ladder beside a headline fee; flattening loses the ladder and publishes one
    of the two prices as if it were the only one.
  * A quote is evidence only where the reader attributed it. An evidence row
    names its field.

WHAT IT REFUSES

  A held Group A identity. A row whose name will not round-trip. A row with no
  quote. A fee it cannot read a currency for. It raises rather than writing a
  partial package.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.contracts import enums                   # noqa: E402
from scripts.pettripfinder.contracts import fee_computation as FC   # noqa: E402
from scripts.pettripfinder.contracts import policy_schema as SCHEMA # noqa: E402
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key  # noqa: E402
from scripts.pettripfinder import hotel_exclusions as HE            # noqa: E402
from scripts.pettripfinder import market_authority as MA            # noqa: E402
from scripts.pettripfinder.markets import contract as MC            # noqa: E402
from scripts.pettripfinder.site_data import normalize_name          # noqa: E402

WORK_ORDER = "PTF-TOLEDO-OH-PROMOTION-AND-APPLICATION-002"
MARKET_ID = "toledo-oh"
MARKET_NAME = "Greater Toledo, Ohio"
AS_OF = "2026-09-06"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
AUTHORITY = os.path.join(PKG, "markets", "authority", MARKET_ID)

CONTRACT = os.path.join(PKG, "markets", "toledo-oh.json")
CENSUS = os.path.join(PKG, "identity_census", "toledo-oh.json")
CLEAN = os.path.join(REPORTS, "toledo_oh_clean_authority_001.json")
AUDIT = os.path.join(REPORTS, "toledo_oh_evidence_audit_001.json")
ROUTING = os.path.join(REPORTS, "toledo_oh_routing_001.json")
RULINGS = os.path.join(PKG, "toledo_oh_founder_rulings_001.json")

#: The founder authorised the promotion SET, by count and by scope, in session.
#: This is the reviewer that authorisation belongs to. It is NOT a claim that a
#: named human read each row: see review_basis on every record.
FOUNDER_REVIEWER_ID = "PTF-FOUNDER-001"
REVIEW_BASIS = (
    "Set-level founder authorisation. The founder ruled on this market's grouped packet in "
    "session (TOLEDO-R1A and TOLEDO-R2, recorded in toledo_oh_founder_rulings_001.json) and "
    "authorised the clean promotion set of 17 CLEAN_PET_FRIENDLY and 9 CLEAN_VERIFIED_NO_PETS by "
    "count and by scope. The agent did not attribute a per-row reading to the founder and no "
    "human name appears in any field a human did not put there.")

#: The founder's governing promotion set after TOLEDO-R3. Nine, not ten: the
#: tenth refusal sits on an identity the merge could not separate from a second
#: Wyndham brand at the same address stem, and TOLEDO-R3 holds both reads.
GOVERNING = {"census": 54, "clean_pet_friendly": 17, "clean_verified_no_pets": 9, "corridors": 13}


class PromotionError(RuntimeError):
    """Refuse to write a partial or unprovable package."""


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _write(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")


def _sha(text):
    return "sha256:" + hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _prefixed(digest):
    """A sha256 digest in ONE form. Bare hex and sha256:-prefixed are not
    comparable, and this market's lanes emit both."""
    d = (digest or "").strip()
    if not d:
        return ""
    return d if d.startswith("sha256:") else "sha256:" + d


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower()).strip("-")


# --------------------------------------------------------------------------- #
# Facts. The reader decided these; this only reshapes them into the package.
# --------------------------------------------------------------------------- #

_NIGHT_RANGE = re.compile(
    r"\$?\s*([\d,]+(?:\.\d{2})?)\s*\(?\s*(\d+)\s*(?:-|to|through)\s*(\d+)?\s*\+?\s*"
    r"(?:n|nights?)\s*\)?", re.I)
_NIGHT_PLUS = re.compile(r"\$?\s*([\d,]+(?:\.\d{2})?)\s*\(?\s*(\d+)\s*\+\s*(?:n|nights?)\s*\)?",
                         re.I)


def fee_from(quote, headline_cents, refundable):
    """A per-night LADDER when the source states one, else a single fee.

    Two different contract shapes, and the difference matters. ``fee_tiers``
    requires a real condition -- role, condition_type and boundary_unit are all
    mandatory -- because a tier exists to say WHEN a price applies. A flat fee
    has no condition, so it belongs in ``pet_fee``; forcing it into a tier means
    inventing a condition the source never stated.

    ``basis`` is omitted unless the source states one. Several Toledo pages give
    a fee with no period at all, and asserting per_stay there would publish a
    term nobody wrote.
    """
    tiers = []
    for m in _NIGHT_RANGE.finditer(quote or ""):
        amt = int(round(float(m.group(1).replace(",", "")) * 100))
        lo, hi = int(m.group(2)), m.group(3)
        t = OrderedDict([("amount_cents", amt), ("currency", "USD"),
                         ("role", enums.ROLE_REPLACEMENT_PRICE),
                         ("condition_type", enums.CONDITION_STAY_LENGTH_RANGE),
                         ("boundary_unit", enums.BOUNDARY_NIGHTS),
                         ("condition_min", lo)])
        if hi:
            t["condition_max"] = int(hi)
        t["scope"] = enums.SCOPE_PER_PET
        t["basis_stated"] = False
        tiers.append(t)
    for m in _NIGHT_PLUS.finditer(quote or ""):
        amt = int(round(float(m.group(1).replace(",", "")) * 100))
        lo = int(m.group(2))
        if any(t["amount_cents"] == amt and t["condition_min"] == lo for t in tiers):
            continue
        tiers.append(OrderedDict([("amount_cents", amt), ("currency", "USD"),
                                  ("role", enums.ROLE_REPLACEMENT_PRICE),
                                  ("condition_type", enums.CONDITION_STAY_LENGTH_RANGE),
                                  ("boundary_unit", enums.BOUNDARY_NIGHTS),
                                  ("condition_min", lo),
                                  ("scope", enums.SCOPE_PER_PET),
                                  ("basis_stated", False)]))
    tiers.sort(key=lambda t: (t["condition_min"], t["amount_cents"]))
    if len(tiers) >= 2:
        return "fee_tiers", tiers
    if headline_cents is None:
        return None, None
    fee = OrderedDict([("amount_cents", headline_cents), ("currency", "USD"),
                       ("scope", enums.SCOPE_PER_PET)])
    basis = _stated_basis(quote)
    if basis:
        fee["basis"] = basis
    if refundable is not None:
        fee["refundable"] = bool(refundable)
    return "pet_fee", fee


_BASIS_WORDS = (
    (enums.BASIS_PER_NIGHT, r"per\s+night|/\s*night|nightly|per\s+room\s+per\s+night"),
    (enums.BASIS_PER_STAY, r"per\s+stay|/\s*stay|non-?refundable\s+fee\s+per\s+stay"),
    (enums.BASIS_PER_DAY, r"per\s+day|/\s*day|daily"),
)


def _stated_basis(quote):
    """The fee period the source actually states, or "" when it states none."""
    for basis, pattern in _BASIS_WORDS:
        if re.search(pattern, quote or "", re.I):
            return basis
    return ""


def facts_from_read(row):
    """The published facts for one clean pet-friendly read."""
    ext = row["extraction"] or {}
    quote = " ".join(str(e.get("quote") or "") for e in (row.get("evidence") or []))
    facts = OrderedDict()
    facts["pets_allowed"] = ext["pets_allowed"]

    species = ext.get("species_allowed")
    if species:
        facts["species"] = OrderedDict(
            [("dogs", "accepted")] if "dog" in species else []
            + ([("cats", "accepted")] if "cat" in species else []))
    # The readers disagree on shape: some return a bare number with a separate
    # unit, others a {"value": n, "unit": "lb"} object. Publish one shape, and
    # never a number nested inside the field that is supposed to hold it.
    wl = ext.get("weight_limit")
    if wl is not None:
        if isinstance(wl, dict):
            value, unit = wl.get("value"), wl.get("unit")
        else:
            value, unit = wl, ext.get("weight_limit_unit")
        if value is None:
            raise PromotionError("%s: a weight limit with no value" % row["canonical_name"])
        facts["weight_limit"] = OrderedDict([
            ("value", float(value)), ("unit", unit or "lb"),
            ("operator", ext.get("weight_limit_operator") or "lte"),
            ("scope", "per_pet")])
    fee = ext.get("pet_fee")
    if fee is not None:
        field, value = fee_from(quote, fee, ext.get("fee_refundable"))
        if field:
            facts[field] = value
    if ext.get("pet_count_limit") is not None:
        facts["pet_count_limit"] = ext["pet_count_limit"]

    return facts


def service_animal_statement(row):
    """The record-level service-animal statement, or None.

    It is NOT a fact. policy_schema flags ``facts.service_animal_exception`` as
    a MISPLACED_FIELD by name: a legal access category must not sit in the
    commercial-terms namespace, where something could apply a weight limit to
    it. It is STRUCTURED -- a bare quote string crashes the renderer -- and it
    carries ``charges_stated``, which reports whether the property addressed a
    charge at all rather than inferring one from silence.
    """
    ext = row["extraction"] or {}
    sa = ext.get("service_animal_statement")
    quote = ""
    if isinstance(sa, dict):
        quote = str(sa.get("quote") or "")
    elif sa:
        quote = str(sa)
    if not quote:
        quote = str(ext.get("service_animal_exception") or "")
    if not quote.strip():
        return None
    low = quote.lower()
    if re.search(r"exempt|no (additional |extra )?(charge|fee)|free of charge|without charge",
                 low):
        charges = "no_charge"
    elif re.search(r"[$]|fee|charge", low):
        charges = "charge_stated"
    else:
        charges = "not_addressed"
    return OrderedDict([("stated", True), ("charges_stated", charges),
                        ("quote", quote.strip()[:400])])


#: A PUBLISHED field name and the READER field names whose quotes support it.
#: The reader attributes a quote to what it read ("pet_fee"); the package
#: publishes what a page renders ("fee_tiers"). Without this map the guard below
#: refuses every fee row for carrying no quote, which is how it was found.
_PUBLISHED_FROM_READER = {
    "fee_tiers": {"pet_fee", "fee_currency", "fee_refundable", "fee_basis", "fee_cap"},
    "pet_fee": {"pet_fee", "fee_currency", "fee_refundable", "fee_basis", "fee_cap"},
    "species": {"species_allowed", "species"},
    "weight_limit": {"weight_limit", "weight_limit_unit", "weight_limit_operator"},
    "pet_count_limit": {"pet_count_limit"},
    "pets_allowed": {"pets_allowed"},
    "service_animal_statement": {"service_animal_statement", "service_animal_exception"},
}


def _published_field_for(reader_field, facts):
    """Which PUBLISHED field this reader field's quote supports.

    A single reader field can feed more than one published shape -- "pet_fee"
    supports fee_tiers on a ladder and pet_fee on a flat charge -- so the answer
    depends on which shape was actually published. Resolving by dict order
    instead silently attributed every flat fee's quote to a fee_tiers field that
    was not there.
    """
    candidates = [pub for pub, readers in _PUBLISHED_FROM_READER.items()
                  if reader_field in readers]
    for pub in candidates:
        if pub in facts:
            return pub
    return candidates[0] if candidates else reader_field


def evidence_rows(row, facts):
    """One evidence row per published field, carrying the quote and the artifact."""
    out = []
    seen = set()
    for e in row.get("evidence") or []:
        quote = str(e.get("quote") or "").strip()
        if not quote:
            continue
        for reader_field in (e.get("field_refs") or []):
            field = _published_field_for(reader_field, facts)
            key = (field, quote)
            if field not in facts or key in seen:
                continue
            seen.add(key)
            out.append(OrderedDict([
                ("field", field), ("quote", quote[:400]),
                ("source_url", row["source_url"]),
                ("value", json.dumps(facts[field], sort_keys=True)
                 if isinstance(facts[field], (dict, list)) else str(facts[field]).lower()
                 if isinstance(facts[field], bool) else str(facts[field])),
                ("evidence_ref", "ev:" + hashlib.sha256(
                    (row["identity_key"] + field + quote).encode("utf-8")).hexdigest()[:16]),
                ("artifact_class", "PUBLICATION_GRADE_EVIDENCE"),
                # Always sha256:-prefixed. A bare hex digest and a prefixed one
                # are not comparable, and half this market's lanes emit each.
                ("artifact_sha256", _prefixed(row.get("document_sha256"))
                 or _sha(row["source_url"] + quote)),
                ("artifact_kind", "rendered_html"),
                ("captured_at", row.get("captured_at") or AS_OF),
                ("capture_method", {"ATTENDED_BROWSER": "attended_browser",
                                    "FIRECRAWL": "firecrawl_rendered_fetch",
                                    "DIRECT_STATIC": "direct_http"}[row["lane"]]),
                ("source_grade", "PT1_PROPERTY" if row["lane"] == "DIRECT_STATIC"
                 else "PT2_BRAND"),
            ]))
    # Every published field must carry at least one quote.
    for field in facts:
        if field == "service_animal_statement":
            continue
        if not any(r["field"] == field for r in out):
            raise PromotionError("%s: published field %r carries no quote"
                                 % (row["canonical_name"], field))
    return out


# --------------------------------------------------------------------------- #
# The builders.
# --------------------------------------------------------------------------- #

def build_policy_package(clean, census_by_key):
    hotels = []
    for row in clean["clean_pet_friendly"]:
        crow = census_by_key.get(row["identity_key"])
        if crow is None:
            raise PromotionError("clean row %r resolves to no census identity"
                                 % row["identity_key"])
        key = crow["identity_key"]
        name = crow["canonical_name"]
        if normalize_name(name) != key:
            raise PromotionError(
                "%r does not round-trip: normalize_name gives %r but the identity key is %r; "
                "the join would fail closed" % (name, normalize_name(name), key))
        facts = facts_from_read(row)
        ident = ptf_identity_key(name)
        if not SCHEMA.is_canonical_key(ident):
            raise PromotionError("%r does not produce a canonical identity_key" % name)
        rec = OrderedDict([
            ("key", key), ("identity_key", ident), ("name", name),
            ("market_id", MARKET_ID), ("schema_version", enums.POLICY_SCHEMA_VERSION),
            ("facts", facts),
        ])
        sa = service_animal_statement(row)
        if sa:
            rec["service_animal_statement"] = sa
        # The contract's OWN classifier decides this; never a literal.
        rec["computation_class"] = FC.classify(facts).computation_class
        hotels.append(OrderedDict(list(rec.items()) + [
            ("evidence", evidence_rows(row, facts)),
            ("source_url", row["source_url"]),
            ("corridor", crow["corridor"]),
            ("verified_at", row.get("captured_at") or AS_OF),
            ("capture_lane", row["lane"]),
            ("reviewer_id", FOUNDER_REVIEWER_ID),
            ("reviewed_at", AS_OF),
            ("review_basis", REVIEW_BASIS),
            ("work_order", WORK_ORDER),
        ]))
    hotels.sort(key=lambda h: h["key"])
    # The record contract is the gate, not this module's opinion of it.
    for h in hotels:
        issues = SCHEMA.validate_record(h)
        if issues:
            raise PromotionError("%s fails the record contract: %s"
                                 % (h["name"], [(i.path, i.code) for i in issues]))
    keys = [h["key"] for h in hotels]
    if len(keys) != len(set(keys)):
        dupes = sorted(k for k, n in Counter(keys).items() if n > 1)
        raise PromotionError("two clean reads resolved to one published identity: %s" % dupes)
    return OrderedDict([
        ("market", MARKET_NAME), ("schema_version", "1.3"), ("market_id", MARKET_ID),
        ("work_order", WORK_ORDER), ("as_of", AS_OF),
        ("note", "Toledo's published pet-friendly authority. Every fact was decided by the "
                 "reader from a first-party page, carries the quote that supports it, and names "
                 "the lane and the document it came from."),
        ("hotels", hotels),
    ])


def build_exclusions(clean, census_by_key):
    records = []
    for row in clean["clean_verified_no_pets"]:
        crow = census_by_key.get(row["identity_key"])
        if crow is None:
            raise PromotionError("clean row %r resolves to no census identity"
                                 % row["identity_key"])
        key = crow["identity_key"]
        quote = next((str(e.get("quote") or "").strip()
                      for e in (row.get("evidence") or [])
                      if "pets_allowed" in (e.get("field_refs") or [])
                      and str(e.get("quote") or "").strip()), "")
        if not quote:
            raise PromotionError("%s: a VERIFIED_NO_PETS row with no refusal quote"
                                 % crow["canonical_name"])
        rec = OrderedDict([
            # A shard owns only its OWN records, and market_authority proves it
            # per record rather than per file.
            ("market_id", MARKET_ID),
            ("exclusion_id", "tol-" + slugify(crow["canonical_name"])),
            ("canonical_name", crow["canonical_name"]),
            ("normalized_name", key),
            ("address", crow["street"]), ("city", crow["city"] or ""),
            ("state", "OH"), ("postal_code", crow["postal_code"]),
            ("official_url", row["source_url"]),
            ("exclusion_state", HE.VERIFIED_NO_PETS),
            ("evidence_quote", quote),
            ("source_url", row["source_url"]),
            ("observed_at", (row.get("captured_at") or AS_OF)[:10]),
            ("source_hash", _prefixed(row.get("document_sha256"))
             or _sha(row["source_url"] + quote)),
        ])
        rec["record_hash"] = HE.record_hash(rec)
        rec["reviewer_id"] = FOUNDER_REVIEWER_ID
        rec["reviewed_at"] = AS_OF
        rec["approval_hash"] = HE.approval_hash(rec)
        rec["review_basis"] = REVIEW_BASIS
        rec["notes"] = (
            "%s. First-party refusal read on the property's own page by the %s lane and audited "
            "against every known wrong-evidence class. Service-animal access is a legal category "
            "and never converts a refusal into acceptance."
            % (WORK_ORDER, row["lane"]))
        records.append(rec)
    records.sort(key=lambda r: r["exclusion_id"])
    names = [r["normalized_name"] for r in records]
    if len(names) != len(set(names)):
        raise PromotionError("two refusals resolved to one identity: %s"
                             % sorted(k for k, n in Counter(names).items() if n > 1))
    doc = OrderedDict([
        ("schema", HE.SCHEMA), ("contract", HE.SCHEMA), ("market_id", MARKET_ID),
        ("note", "This market's slice of the hotel-exclusions authority. The global "
                 "launch_packages/pettripfinder/hotel_exclusions.json is generated from every "
                 "market's shard and must not be hand-edited."),
        ("work_order", WORK_ORDER), ("count", len(records)), ("exclusions", records),
    ])
    HE.validate(doc)
    return doc


def build_seed_rows(policy, census_by_key, routes_by_key):
    rows = []
    for h in policy["hotels"]:
        c = census_by_key[h["key"]]
        quote = " ".join(e["quote"] for e in h["evidence"][:4])
        rows.append(OrderedDict([
            ("name", h["name"]), ("category", "pet-friendly-hotels"),
            ("address", c["street"]), ("city", c["city"] or ""), ("state", "OH"),
            ("postal_code", c["postal_code"]), ("phone", c["phone"] or ""),
            ("website_url", routes_by_key.get(h["key"], h["source_url"])),
            ("source_url", h["source_url"]), ("source_type", "OFFICIAL_PROPERTY"),
            ("observed_at", h["verified_at"][:10]), ("rating", ""), ("amenities", ""),
            ("pet_policy", quote[:600]), ("canonical", ""), ("market_id", MARKET_ID),
        ]))
    rows.sort(key=lambda r: r["name"].lower())
    return rows


def build_partition(census, clean, audit, routing, census_by_key):
    def resolved_key(r):
        row = census_by_key.get(r["identity_key"])
        return row["identity_key"] if row else r["identity_key"]
    pf = {resolved_key(r) for r in clean["clean_pet_friendly"]}
    npets = {resolved_key(r) for r in clean["clean_verified_no_pets"]}
    routed = {r["identity_key"]: r for r in routing["routes"]}
    held_reads = {resolved_key(r) for r in audit["reads"] if r["audit_verdict"] == "HELD"}
    items = []
    for h in census["hotels"]:
        key = h["identity_key"]
        if key in pf:
            state, resolved, action = "PUBLISHED_PET_FRIENDLY", True, ""
        elif key in npets:
            state, resolved, action = "VERIFIED_NO_PETS", True, ""
        elif key in held_reads:
            state, resolved = "AWAITING_FOUNDER_DECISION", False
            action = ("A first-party read exists but the wrong-evidence audit held it: this "
                      "building's identity is not settled. Founder ruling TOLEDO-R2 keeps it "
                      "held until an existing signed precedent makes the disposition "
                      "deterministic.")
        elif not (routed.get(key) or {}).get("url"):
            state, resolved = "AWAITING_ROUTING_REVIEW", False
            action = "No first-party source has stated a route for this identity yet."
        else:
            state, resolved = "AWAITING_POLICY_OBSERVATION", False
            action = ("Routed but not yet read. The brand walls this order could not pass free "
                      "are named in toledo_oh_paid_readiness_001.json.")
        items.append(OrderedDict([
            ("identity_key", key), ("canonical_name", h["canonical_name"]),
            ("slug", slugify(h["canonical_name"])),
            ("city", h["city"] or ""), ("state", "OH"), ("postal_code", h["postal_code"]),
            ("corridor", h["corridor"]),
            ("final_state", state), ("resolved", resolved), ("next_action", action),
            ("determined_by", WORK_ORDER), ("updated_at", AS_OF),
            ("official_url", (routed.get(key) or {}).get("url", "")),
            ("state_override_reason", ""),
        ]))
    items.sort(key=lambda i: i["identity_key"])
    counts = Counter(i["final_state"] for i in items)
    return OrderedDict([
        ("schema", "ptf-market-final-partition/1.1"), ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID), ("as_of", AS_OF),
        ("note", "Every census identity appears exactly once. Resolved means the market owes "
                 "nothing further on the row: it is published, refused, or out of category."),
        ("count", len(items)),
        ("final_state_counts", OrderedDict(sorted(counts.items()))),
        ("items", items),
    ])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="build and validate, write nothing")
    args = ap.parse_args(argv)

    census = _load(CENSUS)
    clean = _load(CLEAN)
    audit = _load(AUDIT)
    routing = _load(ROUTING)
    cfg = MC.parse_market(_load(CONTRACT), source=CONTRACT)
    # A clean read is keyed by the name the LANE captured it under; the census
    # row may have been renamed to its fullest name by the merge and carry that
    # capture name as an alias. Resolve through both, and publish under the
    # CENSUS row's primary key so every downstream join sees one identity.
    census_by_key = {}
    for h in census["hotels"]:
        census_by_key[h["identity_key"]] = h
        for alias in h.get("identity_key_aliases") or []:
            census_by_key.setdefault(alias, h)
    routes_by_key = {r["identity_key"]: r.get("url", "") for r in routing["routes"]}

    got = {"census": census["count"],
           "clean_pet_friendly": len(clean["clean_pet_friendly"]),
           "clean_verified_no_pets": len(clean["clean_verified_no_pets"]),
           "corridors": len(cfg.corridors)}
    if got != GOVERNING:
        raise PromotionError("COUNT GATE: governing %s, computed %s" % (GOVERNING, got))

    def _res(k):
        row = census_by_key.get(k)
        return row["identity_key"] if row else k
    held = {_res(r["identity_key"]) for r in audit["reads"] if r["audit_verdict"] == "HELD"}
    published = ({_res(r["identity_key"]) for r in clean["clean_pet_friendly"]}
                 | {_res(r["identity_key"]) for r in clean["clean_verified_no_pets"]})
    leak = sorted(k for k in (held & published) if k)
    if leak:
        raise PromotionError("a HELD identity reached the published set: %s" % leak)

    policy = build_policy_package(clean, census_by_key)
    exclusions = build_exclusions(clean, census_by_key)
    seed_rows = build_seed_rows(policy, census_by_key, routes_by_key)
    partition = build_partition(census, clean, audit, routing, census_by_key)

    if args.check:
        print("COUNT GATE      : PASS", got)
        print("policy rows     :", len(policy["hotels"]))
        print("exclusion rows  :", len(exclusions["exclusions"]))
        print("seed rows       :", len(seed_rows))
        print("partition       :", partition["count"],
              dict(partition["final_state_counts"]))
        print("nothing written (--check)")
        return 0

    _write(os.path.join(PKG, "hotel_policy_facts_%s.json" % MARKET_ID), policy)
    _write(str(MA.exclusions_shard_path(MARKET_ID)), exclusions)
    _write(os.path.join(PKG, "toledo_oh_final_partition_001.json"), partition)
    _write(str(MA.routing_shard_path(MARKET_ID)), OrderedDict([
        ("schema", "ptf-identity-routing/1.0"), ("contract", "ptf-identity-routing/1.0"),
        ("market_id", MARKET_ID),
        ("note", "This market's slice of the identity-routing authority. Toledo authors no "
                 "override: every published row's route is the one its own first-party source "
                 "stated. The global identity_routing.json is generated and must not be "
                 "hand-edited."),
        ("work_order", WORK_ORDER), ("source_batches", []), ("count", 0), ("routes", []),
    ]))
    _write(str(MA.affiliate_shard_path(MARKET_ID)), OrderedDict([
        ("schema", "ptf-affiliate-destinations/1.0"),
        ("contract", "ptf-affiliate-destinations/1.0"), ("market_id", MARKET_ID),
        ("note", "This market's affiliate booking destinations, keyed by the policy package's "
                 "identity_key. None authored: this order publishes policy, not commerce."),
        ("work_order", WORK_ORDER), ("count", 0), ("destinations", []),
    ]))
    seed_path = str(MA.seed_shard_path(MARKET_ID))
    os.makedirs(os.path.dirname(seed_path), exist_ok=True)
    with open(seed_path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(seed_rows[0].keys()))
        w.writeheader()
        w.writerows(seed_rows)

    print("policy package  :", len(policy["hotels"]), "rows")
    print("exclusion shard :", len(exclusions["exclusions"]), "rows")
    print("seed shard      :", len(seed_rows), "rows")
    print("partition       :", partition["count"], dict(partition["final_state_counts"]))
    print("routing shard   : 0 routes (no override authored)")
    print("affiliate shard : 0 destinations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
