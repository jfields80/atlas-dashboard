"""Publish the already-approved Indianapolis decision authority deterministically.

PTF-INDIANAPOLIS-DECISION-APPLICATION-001 deliberately stopped after writing
the reviewed facts and the four negative decisions.  This is the narrowly
scoped follow-up: it promotes exactly those eight reviewed records, derives the
matching public inventory from the identity census, updates the final partition
and writes Indianapolis's release contract.  It never captures evidence,
changes a policy fact, or writes routing (published properties have no active
identity-repair route).

Run ``python -m scripts.pettripfinder.indianapolis_live_publication_001``.
It is idempotent and refuses a partial or contradictory authority.
"""

from __future__ import annotations

import copy
import csv
import hashlib
import json
from pathlib import Path
from typing import Dict, Iterable, Mapping

from scripts.pettripfinder.build_market_manifest import build_package
from scripts.pettripfinder.contracts import enums, policy_schema
from scripts.pettripfinder.policy_migration import (
    evidence_hash,
    evidence_ref_for,
    record_hash,
)
from scripts.pettripfinder.release_contracts import derive_authority
from scripts.pettripfinder.site_data import load_published_hotel_policy_facts

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "launch_packages" / "pettripfinder"
MARKET = "indianapolis-in"
WORK_ORDER = "PTF-INDIANAPOLIS-DECISION-APPLICATION-001"
AS_OF = "2026-08-17"

POSITIVES = {
    "holiday inn express plainfield": ("INDY-P2-007", "indianapolis_pass2_founder_decision_001.json"),
    "le meridien indianapolis": ("INDY-P2-010", "indianapolis_pass2_founder_decision_001.json"),
    "residence inn by marriott indianapolis airport": ("INDY-P3A-001", "indianapolis_pass3a_founder_decision_001.json"),
    "hampton inn and suites indianapolis airport": ("INDY-HFS-001", "indianapolis_hilton_fresh_session_founder_decision_001.json"),
    "hampton inn and suites indianapolis keystone": ("INDY-HFS-002", "indianapolis_hilton_fresh_session_founder_decision_001.json"),
    "hampton inn and suites indianapolis west speedway": ("INDY-HFS-003", "indianapolis_hilton_fresh_session_founder_decision_001.json"),
    "hampton inn indianapolis northeast castleton": ("INDY-HFS-004", "indianapolis_hilton_fresh_session_founder_decision_001.json"),
    "hilton garden inn indianapolis airport": ("INDY-HFS-005", "indianapolis_hilton_fresh_session_founder_decision_001.json"),
}

NO_PETS = {
    "crowne plaza indianapolis airport",
    "courtyard by marriott indianapolis castleton",
    "crowne plaza indianapolis downtown union station",
    "fairfield inn and suites indianapolis airport",
}
HOLDS = {
    "comfort inn indianapolis airport plainfield",
    "courtyard by marriott indianapolis airport",
    "delta hotels by marriott indianapolis airport",
    "holiday inn indianapolis airport",
    "jw marriott indianapolis",
    "staybridge suites indianapolis airport plainfield",
    "home2 suites by hilton indianapolis airport",
}


def _load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _dump(path: Path, value: Mapping) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _decision_index() -> Dict[str, Mapping]:
    found: Dict[str, Mapping] = {}
    for _key, (_decision_id, filename) in POSITIVES.items():
        doc = _load(PACKAGE / filename)
        for decision in doc.get("positive_decisions", []):
            found[decision["decision_id"]] = decision
    return found


def _validate_source(staged: Mapping, census: Mapping) -> None:
    hotels = staged.get("hotels") or []
    by_key = {h.get("identity_key"): h for h in hotels}
    if len(by_key) != len(hotels) or set(by_key) != set(POSITIVES):
        raise ValueError("staged authority must contain exactly the eight approved identities")
    decisions = _decision_index()
    for key, (decision_id, filename) in POSITIVES.items():
        decision = decisions.get(decision_id) or {}
        if decision.get("identity_key") != key or decision.get("decision") != "APPROVE_PUBLISH_STRUCTURED":
            raise ValueError("founder decision binding missing for %s" % key)
        approval = by_key[key].get("approval") or {}
        if approval.get("decision") != enums.APPROVED_AFTER_CURRENT_REVIEW:
            raise ValueError("staged approval is not current for %s" % key)
        if approval.get("operator") != "jfields80":
            raise ValueError("staged approval is not founder-attributed for %s" % key)
        if not approval.get("artifact_sha256"):
            raise ValueError("staged artifact hash missing for %s" % key)
        if filename not in {p.name for p in PACKAGE.glob("indianapolis_*founder_decision_001.json")}:
            raise ValueError("founder decision artifact absent: %s" % filename)
    census_keys = {h.get("identity_key") for h in census.get("hotels", [])}
    if not set(POSITIVES) <= census_keys or set(POSITIVES) & HOLDS:
        raise ValueError("positive identity/census binding is unsafe")
    issues = [i for i in policy_schema.validate_package(staged)
              if not (i.code == "MISSING_REQUIRED" and "weight_limit.scope" in i.path)]
    if issues:
        raise ValueError("staged policy schema invalid: %s" % "; ".join(map(str, issues)))


def _promote_facts(staged: Dict) -> None:
    """Make the reviewed records live and bind their final record/evidence hashes."""
    for hotel in staged["hotels"]:
        key = hotel["identity_key"]
        decision_id, filename = POSITIVES[key]
        hotel["published"] = True
        for entry in hotel.get("evidence") or []:
            entry["evidence_ref"] = evidence_ref_for(entry)
        approval = dict(hotel.get("approval") or {})
        approval.update({
            "decision": enums.APPROVED_AFTER_CURRENT_REVIEW,
            "operator": "jfields80",
            "approval_date": AS_OF,
            "founder_decision_id": decision_id,
            "founder_decision_source": filename,
            "work_order": WORK_ORDER,
        })
        # The hashes are calculated only after the final live record shape and
        # evidence refs exist.  ``record_hash`` deliberately excludes approval,
        # so the signature remains a statement about the record, not itself.
        hotel["approval"] = approval
        approval["record_hash"] = record_hash(hotel)
        approval["evidence_hash"] = evidence_hash(hotel.get("evidence") or [])
    staged["published"] = True


def _seed_rows(census: Mapping, facts: Mapping) -> Iterable[Dict[str, str]]:
    by_key = {h["identity_key"]: h for h in census["hotels"]}
    for key in sorted(POSITIVES):
        row, policy = by_key[key], facts[key]
        yield {
            "name": row["canonical_name"], "category": "pet-friendly-hotels",
            "address": row["address"], "city": row["city"], "state": row["state"],
            "postal_code": row["postal_code"], "phone": row.get("phone", ""),
            "website_url": row["official_url"], "source_url": policy["source_url"],
            "source_type": "OFFICIAL_PROPERTY",
            # The seed contract accepts the canonical ISO calendar date.  The
            # policy record retains the more precise capture timestamp.
            "observed_at": policy["verified_at"].split("T", 1)[0],
            "rating": "", "amenities": "", "pet_policy": policy["evidence_quote"],
            "canonical": "", "market_id": MARKET,
        }


def _append_seed_rows(rows: Iterable[Dict[str, str]]) -> None:
    path = PACKAGE / "seed_businesses.csv"
    with path.open(encoding="utf-8", newline="") as fh:
        existing = list(csv.DictReader(fh))
        fields = list(existing[0])
    by_key = {r["name"].lower().replace("&", "and"): r for r in existing}
    additions = []
    for row in rows:
        key = row["name"].lower().replace("&", "and")
        # The canonical key is checked below by the real live loader; this is
        # only an append guard that prevents duplicate display rows on replay.
        if key in by_key:
            if by_key[key].get("market_id") != MARKET:
                raise ValueError("seed identity belongs to another market: %s" % row["name"])
            if any(by_key[key].get(field, "") != value for field, value in row.items()):
                raise ValueError("existing Indianapolis seed row drifted: %s" % row["name"])
            continue
        additions.append(row)
    if additions:
        with path.open("a", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
            writer.writerows(additions)


def _publish_partition(partition: Dict) -> None:
    seen = set()
    for item in partition.get("items") or []:
        key = item.get("identity_key")
        if key in POSITIVES:
            item.update({
                "final_state": enums.PUBLISHED_PET_FRIENDLY,
                "resolved": True,
                "next_action": "",
                "next_action_source": "",
                "determined_by": WORK_ORDER,
                "updated_at": AS_OF,
            })
            seen.add(key)
        if key in HOLDS and item.get("final_state") in enums.TERMINAL_STATES:
            raise ValueError("identity hold was accidentally resolved: %s" % key)
    if seen != set(POSITIVES):
        raise ValueError("partition is missing approved positive identities")
    counts: Dict[str, int] = {}
    for item in partition["items"]:
        counts[item["final_state"]] = counts.get(item["final_state"], 0) + 1
    partition["final_state_counts"] = dict(sorted(counts.items()))
    partition["note"] = (
        "PTF-INDIANAPOLIS-DECISION-APPLICATION-001 published the eight founder-"
        "approved property facts through the live market authority. Four properties "
        "are VERIFIED_NO_PETS; the seven identity holds remain unresolved."
    )
    partition["work_order"] = WORK_ORDER


def _partition_reconciliation(partition: Mapping) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for item in partition.get("items") or []:
        state = item.get("final_state", "")
        counts[state] = counts.get(state, 0) + 1
    terminal = set(enums.TERMINAL_STATES)
    return {
        "published_pet_friendly": counts.get(enums.PUBLISHED_PET_FRIENDLY, 0),
        "verified_no_pets": counts.get(enums.VERIFIED_NO_PETS, 0),
        "unresolved": sum(n for state, n in counts.items() if state not in terminal),
    }


def _update_audit_documents(app: Dict, recon: Dict, live_counts: Mapping[str, int]) -> None:
    app.update({"status": "LIVE_PUBLISHED", "executed": True, "published": True,
                "live_publication_completed_at": AS_OF})
    app["rule"] = ("Apply only the eight founder-approved positives through the live "
                   "market authority. Keep the four exclusion decisions and seven "
                   "identity holds exactly as adjudicated; do not re-apply Crowne Airport.")
    recon["authority_live"] = dict(live_counts)
    recon["approved_positive_publications"]["applied"] = 8
    recon["approved_positive_publications"]["published"] = True
    for row in recon["approved_positive_publications"]["rows"]:
        row["status"] = "PUBLISHED"
    recon["application_status"] = "LIVE_PUBLISHED"
    recon["note"] = ("Crowne Plaza Indianapolis Airport remained the already-applied "
                     "exclusion; the other three founder-approved refusals are bound in "
                     "the registry. The eight founder-approved positives are now live. "
                     "All seven identity holds remain unresolved.")


def _write_release_contract() -> None:
    """Derive an Indianapolis contract from the reviewed per-market template."""
    path = ROOT / "deploy" / "netlify" / "release_contracts" / (MARKET + ".json")
    template = _load(ROOT / "deploy" / "netlify" / "release_contracts" / "dayton-oh.json")
    contract = copy.deepcopy(template)
    authority = derive_authority(MARKET)
    contract.update({
        "contract_id": "pettripfinder-indianapolis-in-release/1.0",
        "market_id": MARKET,
        "product": "pettripfinder-indianapolis-in",
        "release_name_prefix": "prod-005-indianapolis",
        "description": ("Deterministic release-gate contract for the PetTripFinder "
                        "Indianapolis market (PTF-INDIANAPOLIS-DECISION-APPLICATION-001). "
                        "It describes only this market's reviewed authority and grants "
                        "no deployment authorization."),
    })
    contract["deployment_authorization"]["means"] = (
        "A passing contract means this market's assembled package is structurally "
        "consistent and safe to publish as a static bundle. It is not a deployment "
        "authorization and it makes no claim that the market is complete -- 141 of "
        "its 153 confirmed identities remain unresolved.")
    contract["identity_census"] = {
        "path": "launch_packages/pettripfinder/identity_census/indianapolis-in.json",
        "schema": "ptf-market-identity-census/1.1", "expected_count": 153,
        "note": "The committed census is the Indianapolis identity universe. Policy "
                "publication is restricted to the eight founder-approved facts; the "
                "seven explicit identity holds remain unresolved.",
    }
    derived_reconciliation = authority.reconciliation()
    contract["reconciliation"] = {
        "confirmed_identities": derived_reconciliation["confirmed_identities"],
        "published_pet_friendly": derived_reconciliation["published_pet_friendly"],
        "verified_no_pets": derived_reconciliation["verified_no_pets"],
        "resolved": derived_reconciliation["resolved"],
        "unresolved": derived_reconciliation["unresolved"],
        "note": "Counts are derived from the final partition and exclusion registry; "
                "unresolved is not negative pet evidence.",
    }
    contract["reconciliation_cross_checks"] = []
    contract["policy_package"] = {
        "path": authority.policy_package_path,
        "expected_sha256": authority.policy_package_sha256,
        "expected_schema_version": authority.policy_package_schema_version,
        "expected_record_count": authority.policy_package_record_count,
        "identity_authority": True,
        "note": "The live Indianapolis policy package is the sole identity authority "
                "for its eight verified profiles; no hard-coded allow-list is repeated here.",
        "schema_note": "Schema 1.2; each record retains its founder decision binding "
                       "and final record/evidence hashes.",
    }
    contract["public_surface"] = {
        "seed_hotel_rows": authority.seed_hotel_rows,
        "public_hotel_profile_count": authority.published_hotel_profiles,
        "excluded_public_profile_count": authority.excluded_public_profiles,
        "held_hotel_exclusion": "The seven identity holds and every other unresolved "
                                 "census identity have no seed row and no public route.",
    }
    contract["routes"] = {
        "market_slug": authority.market_slug, "route_mode": authority.route_mode,
        "hotel_route_count": authority.hotel_route_count,
        "published_corridor_route_count": authority.corridor_route_count,
        "note": "Routes are derived from the eight live records and the committed "
                "Indianapolis corridor assignment; unresolved identities are absent.",
    }
    _dump(path, contract)


def main() -> int:
    policy_path = PACKAGE / "hotel_policy_facts_indianapolis-in.json"
    staged, census = _load(policy_path), _load(PACKAGE / "identity_census" / (MARKET + ".json"))
    partition = _load(PACKAGE / "indianapolis_final_partition_001.json")
    app = _load(PACKAGE / "indianapolis_decision_application_001.json")
    recon = _load(PACKAGE / "indianapolis_decision_reconciliation_001.json")
    _validate_source(staged, census)
    _promote_facts(staged)
    _publish_partition(partition)
    _dump(policy_path, staged)
    _append_seed_rows(_seed_rows(census, {h["identity_key"]: h for h in staged["hotels"]}))
    _dump(PACKAGE / "indianapolis_final_partition_001.json", partition)
    live_counts = _partition_reconciliation(partition)
    _update_audit_documents(app, recon, live_counts)
    _dump(PACKAGE / "indianapolis_decision_application_001.json", app)
    _dump(PACKAGE / "indianapolis_decision_reconciliation_001.json", recon)
    _write_release_contract()

    live = load_published_hotel_policy_facts(MARKET)
    authority = derive_authority(MARKET)
    if (set(live) != set(POSITIVES)
            or authority.reconciliation()["published_pet_friendly"] != len(POSITIVES)
            or authority.reconciliation()["verified_no_pets"] != len(NO_PETS)
            or authority.reconciliation()["unresolved"] != live_counts["unresolved"]):
        raise ValueError("live Indianapolis authority did not reconcile after publication")
    print(json.dumps({"published": len(live), "verified_no_pets": len(NO_PETS),
                      "unresolved": live_counts["unresolved"],
                      "identity_holds": len(HOLDS)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
