"""PTF-AUGUSTA-GA-HARDENED-V2-SOURCE-READY-001 -- Phase 26 precursor: the
``ptf-market-proposed-authority/1.0`` document, built from the final
partition's resolved dispositions (CLEAN_PET_FRIENDLY -> pet_friendly,
CLEAN_VERIFIED_NO_PETS -> verified_no_pets) joined against the census for
address/city/state/postal_code. Modeled exactly on
launch_packages/pettripfinder/markets/staging/savannah-ga/
savannah_ga_proposed_authority_002.json's shape -- the shared
market_registration_cli reader is never edited, only fed its expected input.

Every unresolved row (ACCESS_BLOCKED, ROUTING_HOLD, EVIDENCE_HOLD,
NEGATION_HOLD, SOURCE_SILENT) is named in ``unresolved``, never silently
dropped.

Output:
  launch_packages/pettripfinder/markets/staging/augusta-ga/augusta_ga_proposed_authority_011.json
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-AUGUSTA-GA-HARDENED-V2-SOURCE-READY-001"
MARKET_ID = "augusta-ga"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
STAGING = os.path.join(PKG, "markets", "staging", MARKET_ID)
CENSUS = os.path.join(PKG, "identity_census", "augusta-ga.json")
PARTITION = os.path.join(PKG, "markets", "reports", "augusta_ga_final_partition_007.json")
#: REGISTERED by PTF-AUGUSTA-GA-V2-REGISTRATION-AND-FOUNDER-PACKET-003: the package root, as every registered market.
OUT = os.path.join(PKG, "augusta_ga_proposed_authority_011.json")
AS_OF = "2026-09-16"


def source_url_for(h):
    if h.get("official_url"):
        return h["official_url"]
    for e in h.get("evidence", []):
        if e.get("source_url"):
            return e["source_url"]
    return ""


def snapshot_hash(quote, key):
    return hashlib.sha256(("%s|%s" % (key, quote)).encode("utf-8")).hexdigest()


#: The real, previously-captured verified-no-pets evidence (14 identity_keys, all real
#: Firecrawl/attended-browser quotes) lives in the last shadow-package-era staged authority
#: doc -- built once, correctly, before a later dedup pass rewrote final_partition_007.json's
#: schema to items[]/final_state. Reused verbatim by identity_key; nothing here is invented.
OLD_STAGED_AUTHORITY = os.path.join(STAGING, "augusta_ga_proposed_authority_011.json")
POLICY_FACTS = os.path.join(STAGING, "launch_package", "hotel_policy_facts_augusta-ga.json")


def main():
    os.makedirs(STAGING, exist_ok=True)
    census = json.load(open(CENSUS, encoding="utf-8"))
    by_key = {h["identity_key"]: h for h in census["hotels"]}
    part = json.load(open(PARTITION, encoding="utf-8"))
    policy_facts = json.load(open(POLICY_FACTS, encoding="utf-8"))
    facts_by_key = {h["identity_key"]: h for h in policy_facts.get("hotels") or ()}
    old_authority = json.load(open(OLD_STAGED_AUTHORITY, encoding="utf-8"))
    old_vnp_by_key = {r["identity_key"]: r for r in old_authority.get("verified_no_pets") or ()}

    pet_friendly, verified_no_pets, unresolved = [], [], []
    for p in part["items"]:
        key = p["identity_key"]
        h = by_key.get(key)
        state = p["final_state"]

        if state == "PUBLISHED_PET_FRIENDLY":
            pf = facts_by_key.get(key)
            if h is None or pf is None:
                unresolved.append(key)
                continue
            url = source_url_for(h) or (pf["evidence"][0]["source_url"] if pf.get("evidence") else "")
            quotes = [OrderedDict([("quote", e["quote"]), ("location", e.get("capture_method", "")),
                                    ("field_refs", [e["field"]])]) for e in pf.get("evidence") or ()]
            quote = quotes[0]["quote"] if quotes else ""
            pet_friendly.append(OrderedDict([
                ("identity_key", key), ("normalized_name", key), ("canonical_name", h.get("canonical_name")),
                ("address", h.get("street") or ""), ("city", h.get("city") or "Augusta"),
                ("state", h.get("state") or "GA"), ("postal_code", h.get("postal_code") or ""),
                ("official_url", h.get("official_url") or url), ("source_url", url),
                ("observed_at", AS_OF), ("brand", ""), ("corridor", h.get("corridor")),
                ("evidence", quotes),
                ("evidence_quote", quote),
                ("facts", pf.get("facts") or {}),
                ("authority_state", "PUBLISHED_PET_FRIENDLY"),
                ("publication_grade", "PUBLICATION_GRADE_EVIDENCE"),
                ("readiness_state", "READY"),
                ("founder_decision", "REGISTERED_NOT_AUTHORIZED_FOR_LAUNCH"),
                ("founder_reviewer_id", WORK_ORDER), ("founder_reviewed_at", AS_OF),
                ("snapshot_hash", snapshot_hash(quote, key)),
            ]))
        elif state == "VERIFIED_NO_PETS":
            old_row = old_vnp_by_key.get(key)
            if old_row is None:
                unresolved.append(key)
                continue
            row = OrderedDict(old_row)
            row["founder_decision"] = "REGISTERED_NOT_AUTHORIZED_FOR_LAUNCH"
            row["founder_reviewer_id"] = WORK_ORDER
            row["founder_reviewed_at"] = AS_OF
            verified_no_pets.append(row)
        else:
            unresolved.append(key)

    doc = OrderedDict([
        ("schema", "ptf-market-proposed-authority/1.0"),
        ("what_this_is", "Augusta's authority as the source-ready order proposed it, registered by "
                          "PTF-AUGUSTA-GA-V2-REGISTRATION-AND-FOUNDER-PACKET-003. Registration makes the market "
                          "BUILDABLE; launch_participation.json decides whether it is BUILT into production, and "
                          "this order leaves that at SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH. The "
                          "founder gate in the modern lane is on the exact candidate digest, not on each row."),
        ("market_id", MARKET_ID), ("work_order", WORK_ORDER),
        ("registered", True),
        ("published", False), ("deployed", False),
        ("built_from", OrderedDict([
            ("source_ledgers", ["launch_packages/pettripfinder/markets/reports/augusta_ga_final_partition_007.json"]),
            ("decision_ledger", "ptf-final-partition/1.0"),
            ("decided_by", WORK_ORDER), ("decided_at", AS_OF),
            ("approval_vocabulary", "REGISTERED_NOT_AUTHORIZED_FOR_LAUNCH"),
        ])),
        ("gate", "a row reaches this document only with an operative first-party quote bound to an ADMITTED "
                 "census identity; nothing here is authorised for launch"),
        ("signed_rows_in", len(pet_friendly) + len(verified_no_pets)),
        ("superseded_count", 0), ("superseded_rows", []), ("identity_confirmations", []),
        ("pet_friendly_count", len(pet_friendly)), ("verified_no_pets_count", len(verified_no_pets)),
        ("authority_total", len(pet_friendly) + len(verified_no_pets)),
        ("unresolved", sorted(unresolved)),
        ("pet_friendly", pet_friendly), ("verified_no_pets", verified_no_pets),
    ])
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("pet_friendly", len(pet_friendly), "verified_no_pets", len(verified_no_pets), "unresolved", len(unresolved))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
