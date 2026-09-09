"""PTF-NASHVILLE-TN-EVIDENCE-RECOVERY-003 -- the exact recovery cohort.

Names the Nashville rows whose ONLY blocker is that the legacy capture is not
durable under the modern first-party evidence contract, and separates every
other hold so nothing unrelated is re-fetched.

WHAT MAKES A ROW RECOVERABLE

PTF-NASHVILLE-TN-NEW-MARKET-001's attended browser lane preserved the exact
first-party URL, the operative quote, the parsed facts and the page's byte
LENGTH -- and no document hash. The acquisition directories it named are
gitignored and empty on disk, so nothing committed can supply one after the
fact. ``first_party_binding`` refuses those rows on CAPTURE_HASH, correctly.

A row is in the recovery cohort when re-reading the SAME first-party page it
already names would produce evidence the modern contract accepts. That is a
statement about the EVIDENCE, not about the property, the identity, the route or
the policy -- and it is why the cohort is built from the hold's gate
classification rather than from a lane name.

WHAT IS DELIBERATELY OUT

  CROSS_MARKET_COLLISION      another market already publishes the identity key.
                              Re-fetching the page cannot change that, and both
                              rows were already unresolved.
  CONTRACT_MIGRATION_ERROR    the registered census requires a city and no
                              committed source states one. Its EVIDENCE is fine
                              -- hashed, dated, first-party. Listed as an
                              ADJUNCT, not as recovery: one free re-read of the
                              page it already names may state the locality, and
                              that is reported apart from the cohort so the
                              recovery accounting stays exact.

Every hold appears in exactly one bucket and the buckets sum to the hold file.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-NASHVILLE-TN-EVIDENCE-RECOVERY-003"
MARKET_ID = "nashville-tn"

PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
HOLDS = os.path.join(PKG, "nashville_tn_identity_holds_002.json")
CENSUS = os.path.join(PKG, "identity_census", "%s.json" % MARKET_ID)
PROPOSED_CENSUS = os.path.join(PKG, "identity_census_proposed", "%s.json" % MARKET_ID)
CLEAN = os.path.join(REPORTS, "nashville_tn_clean_authority_001.json")
ROUTING = os.path.join(REPORTS, "nashville_tn_routing_001.json")
ATTENDED = os.path.join(REPORTS, "nashville_tn_attended_capture_001.json")
OUT = os.path.join(REPORTS, "nashville_tn_recovery_cohort_003.json")

#: Gate classifications whose remedy is "re-read the same page durably".
RECOVERABLE = {
    "NO_CAPTURE_HASH": "the lane recorded a byte LENGTH and no document hash, and "
                       "the acquisition directory it named is gitignored and empty",
    "NO_TIMESTAMP": "the lane recorded no capture timestamp, so the evidence "
                    "contract's mandatory captured_at and the freshness rule have "
                    "nothing to read",
}


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def build():
    holds = _load(HOLDS)
    census = {h["identity_key"]: h for h in _load(CENSUS)["hotels"]}
    # A row HELD OUT of the registered census still has shadow lineage, and a
    # recovery row with no lineage cannot be identity-checked against anything.
    # The proposed census carries all 181, so it supplies the fallback.
    proposed = {h["identity_key"]: h for h in _load(PROPOSED_CENSUS)["hotels"]}
    for key, row in proposed.items():
        census.setdefault(key, row)
    clean_doc = _load(CLEAN)
    routing = {r["identity_key"]: r for r in _load(ROUTING)["routes"]}
    attended = {}
    for row in _load(ATTENDED).get("rows") or ():
        url = str(row.get("final_url") or row.get("requested_url") or "")
        if url:
            attended.setdefault(url, row)

    # The shadow's clean rows, resolved onto the registered identity the same
    # way the applier resolved them: by key, then by the census alias table.
    alias = {}
    for key, row in census.items():
        alias[key] = key
        for a in row.get("identity_key_aliases") or ():
            alias.setdefault(a, key)
    clean_of = {}
    for policy_class, rows in (("CLEAN_PET_FRIENDLY", clean_doc["clean_pet_friendly"]),
                               ("CLEAN_VERIFIED_NO_PETS", clean_doc["clean_verified_no_pets"])):
        for row in rows:
            key = alias.get(row["identity_key"])
            if key:
                clean_of[key] = (policy_class, row)

    cohort, other, adjunct = [], [], []
    for hold in holds["holds"]:
        key = hold["identity_key_proposed"]
        gate = hold["gate_classification"]
        crow = census.get(key)
        clean = clean_of.get(key)
        record = OrderedDict((
            ("identity_key", key),
            ("canonical_name", hold["canonical_name"]),
            ("address", hold["address"]),
            ("city", (crow or {}).get("city", "")),
            ("postal_code", (crow or {}).get("postal_code", "")),
            ("brand", (crow or {}).get("brand", "")),
            ("property_code", (crow or {}).get("property_code", "")),
            ("phone", (crow or {}).get("phone", "")),
            ("corridor", hold["corridor"]),
            ("hold_class", hold["classification"]),
            ("gate_classification", gate),
            ("old_capture_lane", hold.get("capture_lane") or ""),
            ("old_shadow_class", hold.get("shadow_policy_class") or ""),
        ))
        if clean is not None:
            row = clean[1]
            url = row.get("final_url") or row.get("source_url") or ""
            record["official_url"] = url
            record["source_url"] = row.get("source_url") or ""
            record["old_operative_quote"] = next(
                (str(e.get("quote") or "").strip() for e in (row.get("evidence") or [])
                 if "pets_allowed" in (e.get("field_refs") or [])), "")
            record["old_parsed_facts"] = row.get("extraction") or {}
            record["old_document_sha256"] = row.get("document_sha256") or ""
            record["old_captured_at"] = row.get("captured_at") or ""
            record["old_identity_signals"] = row.get("identity_signals") or {}
            record["old_byte_length"] = (attended.get(url) or {}).get("document_bytes")
        else:
            record["official_url"] = (crow or {}).get("official_url") or \
                (routing.get(key, {}) or {}).get("url", "")
            record["source_url"] = record["official_url"]
            record["old_operative_quote"] = ""
            record["old_parsed_facts"] = {}
            record["old_document_sha256"] = ""
            record["old_captured_at"] = ""
            record["old_identity_signals"] = {}
            record["old_byte_length"] = None

        if gate in RECOVERABLE:
            record["why_recoverable"] = RECOVERABLE[gate]
            if not record["official_url"]:
                record["why_recoverable"] = ""
                record["excluded_because"] = ("the row names no first-party URL, so there is "
                                              "nothing to re-read")
                other.append(record)
            else:
                cohort.append(record)
        elif hold["classification"] == "CONTRACT_MIGRATION_ERROR":
            record["adjunct_because"] = (
                "its evidence is durable -- hashed, dated and first-party. What blocks it is "
                "that no committed source states a city. One free re-read of the page it "
                "already names may state the locality, so it is fetched alongside the cohort "
                "and accounted for APART from it.")
            adjunct.append(record)
        else:
            record["excluded_because"] = (
                "re-fetching the page cannot change this blocker: %s" % hold["why"][:180])
            other.append(record)

    cohort.sort(key=lambda r: r["identity_key"])
    other.sort(key=lambda r: r["identity_key"])
    adjunct.sort(key=lambda r: r["identity_key"])

    doc = OrderedDict((
        ("schema", "ptf-evidence-recovery-cohort/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("what_this_is",
         "the Nashville rows whose ONLY blocker is that the legacy capture is not durable under "
         "the modern first-party evidence contract, and every other hold separated so nothing "
         "unrelated is re-fetched. A row is recoverable when re-reading the SAME first-party "
         "page it already names would produce evidence the contract accepts."),
        ("source_holds", "launch_packages/pettripfinder/nashville_tn_identity_holds_002.json"),
        ("total_holds", holds["count"]),
        ("counts", OrderedDict((
            ("recovery_cohort", len(cohort)),
            ("adjunct", len(adjunct)),
            ("other_holds", len(other)),
            ("sums_to_total_holds", len(cohort) + len(adjunct) + len(other) == holds["count"]),
        ))),
        ("cohort_by_gate_classification",
         OrderedDict(sorted(Counter(r["gate_classification"] for r in cohort).items()))),
        ("cohort_by_old_shadow_class",
         OrderedDict(sorted(Counter(r["old_shadow_class"] for r in cohort).items()))),
        ("cohort_by_old_lane",
         OrderedDict(sorted(Counter(r["old_capture_lane"] for r in cohort).items()))),
        ("cohort_by_brand",
         OrderedDict(sorted(Counter(r["brand"] or "(none)" for r in cohort).items()))),
        ("cohort_by_host", OrderedDict(sorted(Counter(
            (r["official_url"].split("/")[2] if r["official_url"].startswith("http") else "(none)")
            for r in cohort).items()))),
        ("rows_with_a_first_party_url", sum(1 for r in cohort if r["official_url"])),
        ("recovery_cohort", cohort),
        ("adjunct", adjunct),
        ("other_holds", other),
    ))
    return doc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)
    doc = build()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("total holds     :", doc["total_holds"])
    print("recovery cohort :", doc["counts"]["recovery_cohort"],
          dict(doc["cohort_by_gate_classification"]))
    print("  by old class  :", dict(doc["cohort_by_old_shadow_class"]))
    print("  by host       :", dict(doc["cohort_by_host"]))
    print("adjunct         :", doc["counts"]["adjunct"])
    print("other holds     :", doc["counts"]["other_holds"])
    print("sums to total   :", doc["counts"]["sums_to_total_holds"])
    print("written         :", os.path.relpath(args.out, _DASH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
