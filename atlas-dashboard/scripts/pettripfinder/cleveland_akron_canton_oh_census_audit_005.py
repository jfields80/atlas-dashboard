"""PTF-CLEVELAND-AKRON-CANTON-HARDENED-REVALIDATION-001 -- Phase 5.

Independent audit of the pinned 188-row Cleveland-Akron-Canton census through
the canonical dedup helpers plus the physical-signal checks the order names:
duplicate hotels, shortened chain-name identities, shared property code / URL
/ street / phone, rename or rebrand traces, non-lodging rows, closed or
converted rows, and policy/exclusion overlap.

Offline. Reads committed authority only. Writes ONE report under
markets/reports/. It never edits the census, and every finding is a PROPOSED
disposition (SAFE_MERGE / IDENTITY_SUPERSESSION / ADDRESS_SUPERSESSION /
ROUTING_HELD / CLOSED_OR_CONVERTED / FOUNDER_IDENTITY_REVIEW) -- nothing is
applied by this script.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import Counter, OrderedDict, defaultdict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.discovery import identity_dedup as DEDUP  # noqa: E402
from scripts.pettripfinder.discovery import census_duplicate_scan as SCAN  # noqa: E402
from scripts.pettripfinder.discovery.duplicates import normalize_phone, normalize_street  # noqa: E402
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key  # noqa: E402

WORK_ORDER = "PTF-CLEVELAND-AKRON-CANTON-HARDENED-REVALIDATION-001"
MARKET_ID = "cleveland-akron-canton-oh"
SCHEMA = "ptf-market-census-audit/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
AUTH = os.path.join(PKG, "markets", "authority", MARKET_ID)
REPORTS = os.path.join(PKG, "markets", "reports")

NON_LODGING_HINTS = re.compile(r"\b(restaurant|winery|brewery|golf|country club|banquet|catering|tavern|grill|"
                               r"campground|rv park|apartments?|conference center|event center)\b", re.I)
LODGING_HINTS = re.compile(r"\b(inn|hotel|suites?|lodge|motel|resort|bed and breakfast|b and b|guest ?house|"
                           r"cabins?|extended stay|residence|studio)\b", re.I)

CHAIN_TOKENS = ("marriott", "hilton", "hampton", "holiday inn", "comfort", "quality inn", "sleep inn", "days inn",
                "super 8", "best western", "la quinta", "red roof", "motel 6", "courtyard", "residence inn",
                "fairfield", "springhill", "towneplace", "homewood", "home2", "hyatt", "doubletree", "embassy",
                "drury", "candlewood", "staybridge", "extended stay america", "econo lodge", "baymont", "wyndham",
                "ramada", "travelodge", "microtel", "aloft", "sonesta", "tru by", "wingate", "hawthorn", "clarion",
                "cambria", "mainstay", "suburban", "rodeway", "woodspring", "intown", "my place", "americinn",
                "country inn", "radisson", "crowne plaza", "sheraton", "westin", "renaissance", "kimpton",
                "even hotel", "avid", "hotel indigo", "ac hotel", "element", "moxy", "tapestry", "curio")


def read_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def host_of(url: str) -> str:
    m = re.match(r"https?://([^/]+)", url or "")
    return m.group(1).lower().replace("www.", "") if m else ""


def property_code_of(url: str) -> str:
    return DEDUP.property_code({"official_url": url}) if url else ""


def brand_family(name: str) -> str:
    n = name.lower()
    for tok in CHAIN_TOKENS:
        if tok in n:
            return tok
    return ""


def locality_tokens(name: str) -> set:
    return set(re.findall(r"[a-z0-9]+", name.lower()))


def build() -> OrderedDict:
    census = read_json(os.path.join(PKG, "identity_census", f"{MARKET_ID}.json"))
    rows = census["hotels"]
    policy = read_json(os.path.join(PKG, f"hotel_policy_facts_{MARKET_ID}.json"))["hotels"]
    exclusions = read_json(os.path.join(AUTH, "hotel_exclusions.json"))["exclusions"]
    routing = read_json(os.path.join(AUTH, "identity_routing.json"))["routes"]
    partition = read_json(os.path.join(PKG, "cleveland_final_partition_002.json"))
    unresolved = read_json(os.path.join(PKG, "cleveland_unresolved_manifest.json"))
    rr = read_json(os.path.join(PKG, "cleveland_routing_repair_001_results.json"))
    pass4 = read_json(os.path.join(PKG, "cleveland_pass4_capture_results.json"))
    with open(os.path.join(AUTH, "seed_businesses.csv"), "r", encoding="utf-8", newline="") as fh:
        seed = list(csv.DictReader(fh))

    by_key = {r["identity_key"]: r for r in rows}
    pf_keys = {p["identity_key"] for p in policy}
    excl_names = {e["normalized_name"] for e in exclusions}
    excl_keys = {ptf_identity_key(e["canonical_name"]) for e in exclusions}
    partition_state = {}
    for it in partition["items"]:
        k = it.get("identity_key") or ptf_identity_key(it.get("canonical_name", "") or it.get("normalized_name", ""))
        partition_state[k] = it.get("final_state") or it.get("state") or it.get("partition")
    unresolved_keys = {ptf_identity_key(i["canonical_name"]) for i in unresolved["items"]}

    findings = []

    def finding(kind, keys, evidence, proposed, why, severity="REVIEW"):
        findings.append(OrderedDict([
            ("kind", kind), ("identity_keys", sorted(set(keys))), ("evidence", evidence),
            ("proposed_disposition", proposed), ("why", why), ("severity", severity),
            ("live_state", OrderedDict((k, "PET_FRIENDLY_LIVE" if k in pf_keys else
                                        "VERIFIED_NO_PETS_LIVE" if k in excl_keys else
                                        "UNRESOLVED" if k in unresolved_keys else
                                        partition_state.get(k, "UNKNOWN")) for k in sorted(set(keys)))),
        ]))

    # 1. identity-key contract: every key must be the canonical key of its name
    for r in rows:
        if ptf_identity_key(r["canonical_name"]) != r["identity_key"]:
            finding("IDENTITY_KEY_NOT_CANONICAL", [r["identity_key"]],
                    {"canonical_name": r["canonical_name"], "expected": ptf_identity_key(r["canonical_name"])},
                    "IDENTITY_SUPERSESSION", "identity_key must equal ptf_identity_key(canonical_name)", "DEFECT")

    # 2. canonical dedup helpers over the pinned rows
    dedup = DEDUP.analyse(rows)
    scan_groups = SCAN.scan(rows)
    for g in dedup.get("groups", []):
        if g.get("verdict") in (DEDUP.MERGE, DEDUP.REVIEW):
            finding("DEDUP_" + g["verdict"], g.get("identity_keys") or g.get("keys") or [],
                    g, "SAFE_MERGE" if g["verdict"] == DEDUP.MERGE else "FOUNDER_IDENTITY_REVIEW",
                    "canonical identity_dedup verdict on a shared page or premises signal",
                    "DEFECT" if g["verdict"] == DEDUP.MERGE else "REVIEW")

    # 3. own physical-signal buckets (URL host+path, phone, street+postal, property code)
    buckets = {"SHARED_OFFICIAL_URL": defaultdict(list), "SHARED_PHONE": defaultdict(list),
               "SHARED_STREET_AND_POSTAL": defaultdict(list), "SHARED_PROPERTY_CODE": defaultdict(list)}
    for r in rows:
        url = (r.get("official_url") or "").strip().lower().rstrip("/")
        if url:
            buckets["SHARED_OFFICIAL_URL"][url].append(r["identity_key"])
        ph = normalize_phone(r.get("phone") or "")
        if ph:
            buckets["SHARED_PHONE"][ph].append(r["identity_key"])
        st = normalize_street(r.get("address") or "")
        if st and r.get("postal_code"):
            buckets["SHARED_STREET_AND_POSTAL"][st + "|" + r["postal_code"][:5]].append(r["identity_key"])
        code = property_code_of(r.get("official_url") or "")
        if code:
            buckets["SHARED_PROPERTY_CODE"][code].append(r["identity_key"])
    for kind, b in buckets.items():
        for value, keys in sorted(b.items()):
            if len(keys) < 2:
                continue
            names = [by_key[k]["canonical_name"] for k in keys]
            fams = {brand_family(n) for n in names}
            compatible = any(DEDUP.names_compatible(a, b2) for a in names for b2 in names if a != b2)
            if kind in ("SHARED_OFFICIAL_URL", "SHARED_PROPERTY_CODE"):
                proposed = "SAFE_MERGE" if compatible else "FOUNDER_IDENTITY_REVIEW"
                sev = "DEFECT"
            else:
                # premises signals propose, never decide: a dual-brand building is two hotels
                proposed = "FOUNDER_IDENTITY_REVIEW" if (compatible or len(fams) == 1) else "SAME_CAMPUS_DISTINCT_ENTITY_CANDIDATE"
                sev = "REVIEW"
            finding(kind, keys, {"value": value, "names": names, "brand_families": sorted(fams), "names_compatible": compatible},
                    proposed, "two census rows share a physical/page signal", sev)

    # 4. shortened chain-name identities: a chain row whose name has no locality token beyond the brand
    for r in rows:
        fam = brand_family(r["canonical_name"])
        if not fam:
            continue
        rest = locality_tokens(r["canonical_name"]) - locality_tokens(fam) - {"by", "and", "the", "hotel", "hotels", "inn", "suites", "an", "ihg", "marriott", "hilton", "wyndham", "of"}
        if not rest:
            finding("SHORTENED_CHAIN_NAME", [r["identity_key"]], {"canonical_name": r["canonical_name"], "city": r.get("city")},
                    "FOUNDER_IDENTITY_REVIEW", "name is only the brand; the identity key cannot distinguish this row from a sibling", "REVIEW")

    # 5. non-lodging rows
    for r in rows:
        n = r["canonical_name"]
        if NON_LODGING_HINTS.search(n) and not LODGING_HINTS.search(n):
            finding("POSSIBLE_NON_LODGING", [r["identity_key"]], {"canonical_name": n, "lodging_state": r.get("lodging_state")},
                    "FOUNDER_IDENTITY_REVIEW", "name reads as a venue rather than a place to sleep", "REVIEW")
        elif r.get("lodging_state") == "NEEDS_REVIEW":
            finding("LODGING_NEEDS_REVIEW", [r["identity_key"]], {"canonical_name": n},
                    "FOUNDER_IDENTITY_REVIEW", "census itself flags lodging_state NEEDS_REVIEW", "REVIEW")

    # 6. rename / rebrand / conversion traces already recorded by prior passes
    for res in rr.get("results", []):
        if res.get("rename_proposal") or res.get("census_review_candidate") or res.get("census_hygiene"):
            finding("PRIOR_RENAME_OR_REVIEW_TRACE", [res["identity_key"]],
                    {k: res.get(k) for k in ("verdict", "old_url", "new_candidate_url", "final_url", "rename_proposal", "census_hygiene", "census_review_candidate", "source_relationship")},
                    "IDENTITY_SUPERSESSION" if res.get("rename_proposal") else "FOUNDER_IDENTITY_REVIEW",
                    "routing repair 001 recorded a rename proposal or census-review candidate that the pinned census still carries", "REVIEW")
    for res in pass4.get("results", []):
        conv = res.get("conversion_note")
        if conv or res.get("outcome") == "POLICY_CAPTURED_PENDING_IDENTITY_RENAME":
            finding("CONVERSION_OR_RENAME_PENDING", [res["identity_key"]],
                    {"outcome": res.get("outcome"), "final_url": res.get("final_url"), "conversion_note": conv, "hotel": res.get("hotel")},
                    "IDENTITY_SUPERSESSION", "pass 4 captured a page whose brand differs from the census identity (successor question)", "REVIEW")

    # 7. routing rows that are held / retired / lapsed
    for rt in routing:
        if rt["status"] != "ROUTING_CONFIRMED":
            finding("ROUTING_" + rt["status"], [rt["hotel_ref"]["identity_key"]],
                    {"url": rt["official_property_url"], "notes": rt.get("notes"), "binding_method": rt.get("binding_method")},
                    "ROUTING_HELD", "routing shard already holds or retired this route; preserve the record, never queue it", "INFO")

    # 8. authority overlap and orphan checks
    overlap = sorted(pf_keys & excl_keys)
    orphan_pf = sorted(pf_keys - set(by_key))
    orphan_ex = sorted(excl_keys - set(by_key))
    seed_names = {ptf_identity_key(s["name"]) for s in seed}
    seed_vs_pf = OrderedDict([("seed_not_in_policy", sorted(seed_names - pf_keys)), ("policy_not_in_seed", sorted(pf_keys - seed_names))])
    if overlap:
        finding("POLICY_EXCLUSION_OVERLAP", overlap, {}, "FOUNDER_IDENTITY_REVIEW", "a hotel cannot be both published pet-friendly and verified no-pets", "DEFECT")

    # 9. stale/suspicious addresses: missing street number, PO box, or postal outside OH 44xxx
    for r in rows:
        addr = r.get("address") or ""
        pc = (r.get("postal_code") or "")[:5]
        issues = []
        if not re.match(r"^\s*\d", addr):
            issues.append("no leading street number")
        if re.search(r"\bp\.?o\.? box\b", addr, re.I):
            issues.append("PO box")
        if not re.match(r"^44\d{3}$", pc):
            issues.append("postal outside 44xxx")
        if issues:
            finding("ADDRESS_QUALITY", [r["identity_key"]], {"address": addr, "postal_code": pc, "issues": issues},
                    "ADDRESS_SUPERSESSION" if "no leading street number" in issues else "FOUNDER_IDENTITY_REVIEW",
                    "address cannot bind a page by street number", "REVIEW")

    kinds = Counter(f["kind"] for f in findings)
    dispositions = Counter(f["proposed_disposition"] for f in findings)
    report = OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER), ("phase", "5 -- audit the existing 188-row census"),
        ("market_id", MARKET_ID), ("as_of", "2026-09-01"),
        ("what_this_is", "Independent inspection of the pinned census through the canonical dedup helpers and the physical-signal checks the order names. Every finding is a PROPOSAL; the pinned census is not edited and no row is deleted. Premises signals (street+postal, phone) propose and never decide -- a dual-brand building is two hotels."),
        ("inputs", OrderedDict([("census_rows", len(rows)), ("policy_rows", len(policy)), ("exclusion_rows", len(exclusions)), ("routing_rows", len(routing))])),
        ("canonical_dedup", OrderedDict([("schema", dedup.get("schema")), ("groups", len(dedup.get("groups", []))),
                                         ("verdicts", OrderedDict(sorted(Counter(g.get("verdict") for g in dedup.get("groups", [])).items()))),
                                         ("suppressed_keys", sorted(set(dedup.get("suppressed_keys") or dedup.get("not_payable") or [])))])),
        ("duplicate_scan", OrderedDict([("groups", len(scan_groups)), ("by_signal", OrderedDict(sorted(Counter(g["signal"] for g in scan_groups).items()))), ("groups_detail", scan_groups)])),
        ("authority_consistency", OrderedDict([("policy_exclusion_overlap", overlap), ("policy_keys_not_in_census", orphan_pf),
                                                ("exclusion_keys_not_in_census", orphan_ex), ("seed_vs_policy", seed_vs_pf),
                                                ("pf_live", len(pf_keys)), ("no_pets_live", len(excl_keys)), ("unresolved_manifest", len(unresolved_keys)),
                                                ("sum", len(pf_keys) + len(excl_keys) + len(unresolved_keys))])),
        ("finding_counts_by_kind", OrderedDict(sorted(kinds.items()))),
        ("proposed_disposition_counts", OrderedDict(sorted(dispositions.items()))),
        ("findings", findings),
    ])
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPORTS, f"{MARKET_ID.replace('-', '_')}_census_audit_005.json"))
    args = ap.parse_args(argv)
    rep = build()
    with open(args.out, "wb") as fh:
        fh.write((json.dumps(rep, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    print("written", os.path.relpath(args.out, _DASH))
    print("findings by kind:", dict(rep["finding_counts_by_kind"]))
    print("dispositions:", dict(rep["proposed_disposition_counts"]))
    print("authority:", json.dumps({k: v for k, v in rep["authority_consistency"].items() if k not in ("seed_vs_policy",)}))
    print("seed_vs_policy:", json.dumps(rep["authority_consistency"]["seed_vs_policy"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
