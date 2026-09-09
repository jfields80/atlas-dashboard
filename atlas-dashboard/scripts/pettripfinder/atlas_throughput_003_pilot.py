"""ATLAS-THROUGHPUT-003 -- the representative market package pilot.

Frozen, non-production copies of real market material are sealed by the
typed writer and run through the FAST_DATA_ONLY_RELEASE lane; every measure
the order asks for is recorded. Nothing here edits, promotes or deploys a
market: the pilot reads committed authority (Dayton, this tree), git bytes of
two frozen branches (Nashville 4f3dd7b, Toledo d335c50) and writes only under
the market-owned ``markets/packages/<market>/`` and ``markets/receipts/<market>/``
directories plus the throughput report location.

Pilot packages
--------------
P1  dayton-oh FROZEN_COPY, zero delta   the live authority as a package
P2  dayton-oh FROZEN_COPY, withdrawal   P1 minus the records the first-party
                                        gate refuses, with the delta declared
P3  nashville-tn SHADOW                 the shadow branch's clean authority
P4  toledo-oh FROZEN_COPY               the launched authority at d335c50

The helpers are shared with ``tests/pettripfinder/test_atlas_throughput_003.py``
so the adversarial matrix mutates exactly the inputs the pilot sealed.
"""

from __future__ import annotations

import argparse
import collections
import csv
import io
import json
import shutil
import subprocess
import sys
import tempfile
import time
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from scripts.pettripfinder import fast_release_lane as FL
from scripts.pettripfinder import hotel_exclusions as HE
from scripts.pettripfinder import market_package_writer as W
from scripts.pettripfinder import release_index as RI
from scripts.pettripfinder import sealed_market_package as SMP
from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts import partition as PARTITION
from scripts.pettripfinder.contracts import service_animal as SERVICE_ANIMAL
from scripts.pettripfinder.contracts.identity_key import IdentityKeyError, ptf_identity_key
from scripts.pettripfinder.market_authority import SEED_COLUMNS
from scripts.pettripfinder.markets.contract import parse_market, slugify
from scripts.pettripfinder.site_data import normalize_name

REPO_ROOT = SMP.REPO_ROOT
REPORTS = SMP.LAUNCH_PACKAGE / "reports"
NASHVILLE_REV = "4f3dd7b"
TOLEDO_REV = "d335c50"

#: The Dayton records the first-party gate refuses on the live authority
#: (found by the pilot's P1 run; see atlas_throughput_003_fast_lane_report).
DAYTON_WITHDRAW_PET_FRIENDLY: Tuple[str, ...] = (
    "staybridge suites miamisburg",
    "the hotel at dayton south",
    "holiday inn express and suites dayton huber heights",
    "holiday inn express and suites washington court house",
)
DAYTON_WITHDRAW_NO_PETS: Tuple[str, ...] = ("hotel versailles",)
PILOT_RULING = "ATLAS-THROUGHPUT-003 pilot withdrawal (frozen copy, never promoted)"
PILOT_REASON = ("five records fail the first-party gate under the owning reader: three bare "
                "acceptance labels, one fee sentence cited as the acceptance, one bare machine "
                "field cited as the refusal")


# --------------------------------------------------------------------------- #
# Shared helpers.
# --------------------------------------------------------------------------- #

def zero_delta(market_id: str) -> "OrderedDict[str, Any]":
    return OrderedDict((("market_id", market_id), ("add_property_ids", []), ("update_property_ids", []),
                        ("remove_property_ids", []), ("add_routes", []), ("change_routes", []),
                        ("remove_routes", []), ("expected_profile_delta", 0),
                        ("expected_market_count_delta", 0), ("expected_participation_delta", [])))


def parent_from_live(live: Tuple[RI.ReleaseIndex, RI.LiveState, List[str]]) -> "OrderedDict[str, Any]":
    idx, state, _problems = live
    doc = state.to_dict()
    parent = OrderedDict((k, doc[k]) for k in ("live_deploy_id", "rollback_target", "source_commit",
                                               "participating_markets", "profile_counts",
                                               "total_profiles", "sitemap_route_count"))
    parent["live_index_digest"] = idx.digest()
    return parent


def frozen_inputs(market_id: str, live, *, launch_package: Optional[Path] = None,
                  zone: str = SMP.ZONE_FROZEN_COPY, source_sha: Optional[str] = None,
                  delta: Optional[Mapping] = None) -> W.PackageInputs:
    return W.inputs_from_committed_market(
        market_id, execution_zone=zone, intended_delta=delta or zero_delta(market_id),
        parent_live_state=parent_from_live(live), launch_package=launch_package, source_sha=source_sha)


def withdrawal_inputs(live, *, withdraw_pf: Sequence[str] = DAYTON_WITHDRAW_PET_FRIENDLY,
                      withdraw_np: Sequence[str] = DAYTON_WITHDRAW_NO_PETS,
                      ruling_ref: str = PILOT_RULING, reason: str = PILOT_REASON,
                      declare_corridor_routes: bool = True) -> W.PackageInputs:
    """P2: Dayton minus the refused records, every consequence declared."""
    from scripts.pettripfinder.markets.assignment import assign_hotels
    from scripts.pettripfinder.markets.routes import corridor_route, hotel_route

    idx = live[0]
    inp = frozen_inputs("dayton-oh", live)
    market = parse_market(dict(inp.market))
    removed_routes = [hotel_route(market, r["name"]) for r in inp.pet_friendly_records
                      if r["identity_key"] in withdraw_pf]
    inp.pet_friendly_records = [r for r in inp.pet_friendly_records if r["identity_key"] not in withdraw_pf]
    inp.verified_no_pets_records = [r for r in inp.verified_no_pets_records
                                    if r["normalized_name"] not in withdraw_np]
    if declare_corridor_routes:
        names = {r["name"] for r in inp.pet_friendly_records}
        kept = [dict(s) for s in inp.seed_rows if s.get("name") in names]
        published = assign_hotels(market, kept, fail_closed=False).published
        after = {corridor_route(market, market.corridor_by_id(c)) for c in published}
        removed_routes += sorted(set(idx.markets["dayton-oh"].corridor_routes) - after)
    partition = json.loads(json.dumps(inp.partition), object_pairs_hook=OrderedDict)
    for item in partition["items"]:
        if item.get("identity_key") in tuple(withdraw_pf) + tuple(withdraw_np):
            item["final_state"] = "AWAITING_POLICY_ARTIFACT"
            item["resolved"] = False
            item["next_action"] = ("re-capture the operative policy text; the cited quote is a bare "
                                   "label, a fee sentence or a machine field")
            item["next_action_source"] = "ATLAS-THROUGHPUT-003 first-party gate"
            item["determined_by"] = ruling_ref or PILOT_RULING
    counts: Dict[str, int] = {}
    for item in partition["items"]:
        counts[item["final_state"]] = counts.get(item["final_state"], 0) + 1
    partition["final_state_counts"] = counts
    inp.partition = partition
    delta = zero_delta("dayton-oh")
    delta["remove_property_ids"] = list(withdraw_pf)
    delta["remove_routes"] = sorted(removed_routes)
    delta["expected_profile_delta"] = -len(withdraw_pf)
    delta["expected_verified_no_pets_delta"] = -len(withdraw_np)
    if ruling_ref or reason:
        delta["removal_authority"] = OrderedDict((("ruling_ref", ruling_ref), ("reason", reason)))
    inp.intended_delta = delta
    return inp


def seal(inputs: W.PackageInputs, sealed_at: str = "2026-09-08T00:00:00Z") -> "OrderedDict[str, Any]":
    return W.build_sealed_package(inputs, sealed_at=sealed_at)


def rejection_summary(exc: W.PackageWriteError) -> "OrderedDict[str, Any]":
    counts = collections.Counter(i.code for i in exc.issues)
    return OrderedDict((("rejected", True), ("issue_count", len(exc.issues)),
                        ("codes", OrderedDict(sorted(counts.items()))),
                        ("examples", [str(i)[:200] for i in exc.issues[:8]])))


# --------------------------------------------------------------------------- #
# Frozen branch bytes.
# --------------------------------------------------------------------------- #

def git_bytes(rev: str, relpath: str) -> bytes:
    return subprocess.run(["git", "show", "%s:atlas-dashboard/%s" % (rev, relpath)],
                          cwd=str(REPO_ROOT), capture_output=True, check=True).stdout


def git_json(rev: str, relpath: str) -> Any:
    return json.loads(git_bytes(rev, relpath).decode("utf-8-sig"), object_pairs_hook=OrderedDict)


def has_commit(rev: str) -> bool:
    return subprocess.run(["git", "cat-file", "-e", rev + "^{commit}"], cwd=str(REPO_ROOT),
                          capture_output=True).returncode == 0


def toledo_launch_package(rev: str, target: Path) -> Path:
    """Extract Toledo's committed authority at ``rev`` into a launch-package-shaped tree."""
    target = Path(target)
    files = ("markets/toledo-oh.json", "identity_census/toledo-oh.json", "hotel_policy_facts_toledo-oh.json",
             "markets/authority/toledo-oh/hotel_exclusions.json", "markets/authority/toledo-oh/identity_routing.json",
             "markets/authority/toledo-oh/seed_businesses.csv", "markets/authority/toledo-oh/affiliate_destinations.json",
             "toledo_oh_final_partition_001.json")
    for rel in files:
        path = target / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(git_bytes(rev, "launch_packages/pettripfinder/" + rel))
    return target


_FIELD_MAP = {
    "pets_allowed": "pets_allowed", "pet_fee": "pet_fee", "fee_currency": "pet_fee",
    "fee_basis": "pet_fee", "fee_scope": "pet_fee", "fee_refundable": "pet_fee",
    "pet_count_limit": "pet_count_limit", "pet_count_scope": "pet_count_scope",
    "species_allowed": "species", "cats_allowed": "species", "weight_limit": "weight_limit",
    "weight_limit_unit": "weight_limit", "service_animal_statement": "service_animal_statement",
    "service_animal_exception": "service_animal_statement", "pet_deposit": "other_charges",
    "fee_cap": "fee_cap",
}


def _facts_from_extraction(ext: Mapping) -> "OrderedDict[str, Any]":
    facts: "OrderedDict[str, Any]" = OrderedDict()
    facts["pets_allowed"] = bool(ext.get("pets_allowed"))
    species: "OrderedDict[str, str]" = OrderedDict()
    for s in ext.get("species_allowed") or ():
        species[("dogs" if s == "dog" else "cats" if s == "cat" else s)] = enums.SPECIES_ACCEPTED
    if ext.get("cats_allowed") is False:
        species["cats"] = enums.SPECIES_PROHIBITED
    if species:
        facts["species"] = species
    if isinstance(ext.get("pet_fee"), int):
        fee: "OrderedDict[str, Any]" = OrderedDict((("amount_cents", int(ext["pet_fee"])),
                                                   ("currency", str(ext.get("fee_currency") or "USD"))))
        if ext.get("fee_basis"):
            fee["basis"] = ext["fee_basis"]
        if ext.get("fee_scope"):
            fee["scope"] = ext["fee_scope"]
        if ext.get("fee_refundable") is not None:
            fee["refundable"] = bool(ext["fee_refundable"])
        facts["pet_fee"] = fee
    if isinstance(ext.get("pet_deposit"), int):
        facts["other_charges"] = [OrderedDict((("kind", enums.CHARGE_REFUNDABLE_DEPOSIT),
                                               ("amount_cents", int(ext["pet_deposit"])),
                                               ("currency", str(ext.get("fee_currency") or "USD")),
                                               ("refundable_stated", True), ("refundable", True)))]
    cap = ext.get("fee_cap")
    if isinstance(cap, Mapping) and isinstance(cap.get("amount_minor"), int):
        facts["fee_cap"] = OrderedDict((("amount_cents", int(cap["amount_minor"])),
                                        ("currency", str(cap.get("currency") or "USD")),
                                        ("basis", str(cap.get("basis") or enums.BASIS_PER_STAY))))
    weight = ext.get("weight_limit")
    if isinstance(weight, Mapping) and weight.get("value") is not None:
        facts["weight_limit"] = OrderedDict((("value", float(weight["value"])),
                                             ("unit", str(weight.get("unit") or ext.get("weight_limit_unit") or "lb")),
                                             ("operator", enums.OP_LTE), ("scope", enums.WEIGHT_SCOPE_PER_PET)))
    elif isinstance(weight, (int, float)):
        facts["weight_limit"] = OrderedDict((("value", float(weight)),
                                             ("unit", str(ext.get("weight_limit_unit") or "lb")),
                                             ("operator", enums.OP_LTE), ("scope", enums.WEIGHT_SCOPE_PER_PET)))
    if isinstance(ext.get("pet_count_limit"), int):
        facts["pet_count_limit"] = int(ext["pet_count_limit"])
        if ext.get("pet_count_scope"):
            facts["pet_count_scope"] = ext["pet_count_scope"]
    return facts


def _service_animal(ext: Mapping) -> Optional["OrderedDict[str, Any]"]:
    statement = ext.get("service_animal_statement")
    quote = ""
    if isinstance(statement, Mapping):
        quote = str(statement.get("quote") or "")
    elif isinstance(ext.get("service_animal_exception"), str):
        quote = ext["service_animal_exception"]
    if not quote.strip():
        return None
    return OrderedDict((("stated", True), ("charges_stated", SERVICE_ANIMAL.charges_stated(quote)),
                        ("quote", quote)))


def _grade_for(url: str) -> str:
    family, _code = HE.brand_scoped_property_identity(url)
    return enums.GRADE_PT2_BRAND if family else enums.GRADE_PT1_FIRST_PARTY


def nashville_inputs(live, rev: str = NASHVILLE_REV) -> W.PackageInputs:
    """The Nashville shadow branch's clean authority as package inputs.

    The proposed census is derived to the registered census shape (the same
    derivation a promotion performs: slug, market_id, identity/lodging state
    from the classification, policy state from the clean authority); the
    clean rows become schema-1.3 records with one evidence entry per cited
    field; the partition is derived from the same state. Nothing is invented:
    a row without a capture hash keeps no hash, a record nobody reviewed
    carries no reviewer.
    """
    base = "launch_packages/pettripfinder/"
    market = git_json(rev, base + "markets/proposed/nashville-tn.json")
    census_src = git_json(rev, base + "identity_census_proposed/nashville-tn.json")
    clean = git_json(rev, base + "markets/reports/nashville_tn_clean_authority_001.json")
    static = git_json(rev, base + "markets/reports/nashville_tn_free_static_capture_001.json")
    digests = OrderedDict((
        ("market", SMP.sha256_bytes(git_bytes(rev, base + "markets/proposed/nashville-tn.json"))),
        ("census", SMP.sha256_bytes(git_bytes(rev, base + "identity_census_proposed/nashville-tn.json"))),
        ("clean_authority", SMP.sha256_bytes(git_bytes(rev, base + "markets/reports/nashville_tn_clean_authority_001.json"))),
    ))
    pf_rows = {r["identity_key"]: r for r in clean["clean_pet_friendly"]}
    np_rows = {r["identity_key"]: r for r in clean["clean_verified_no_pets"]}
    as_of = str(static.get("as_of") or "")

    census_rows: List["OrderedDict[str, Any]"] = []
    for h in census_src["hotels"]:
        key = str(h["identity_key"])
        name = str(h["canonical_name"])
        policy_state = (enums.POLICY_CONFIRMED if key in pf_rows else
                        enums.VERIFIED_NO_PETS if key in np_rows else enums.POLICY_NOT_VERIFIED)
        census_rows.append(OrderedDict((
            ("identity_key", key), ("canonical_name", name), ("display_name", name),
            ("slug", slugify(name)), ("market_id", "nashville-tn"),
            ("address", str(h.get("street") or "")), ("city", str(h.get("city") or "")),
            ("state", str(h.get("state") or "")), ("postal_code", str(h.get("postal_code") or "")[:5]),
            ("phone", str(h.get("phone") or "")),
            ("identity_state", enums.IDENTITY_CONFIRMED if h.get("classification") == "TRUE_HOTEL_IDENTITY"
             else enums.IDENTITY_PROVISIONAL),
            ("lodging_state", enums.LODGING_CONFIRMED), ("policy_state", policy_state),
            ("collision_state", enums.COLLISION_NONE),
            ("official_url", str(h.get("official_url") or "")), ("corridor", str(h.get("corridor") or "")),
            ("assignment_basis", str(h.get("assignment_basis") or "")),
            ("assignment_value", str(h.get("assignment_value") or "")),
            ("brand", str(h.get("brand") or "")), ("property_code", str(h.get("property_code") or "")),
            ("identity_key_aliases", list(h.get("identity_key_aliases") or ())),
        )))
    census = OrderedDict((("schema", "ptf-market-identity-census/1.1"), ("market_id", "nashville-tn"),
                          ("identity_key_contract", "ptf_identity_key/1.0"),
                          ("work_order", "ATLAS-THROUGHPUT-003 pilot (derived from %s)" % rev),
                          ("count", len(census_rows)), ("hotels", census_rows)))
    by_key = {r["identity_key"]: r for r in census_rows}

    def evidence_entries(row: Mapping) -> List["OrderedDict[str, Any]"]:
        out: List["OrderedDict[str, Any]"] = []
        digest = SMP.normalise_sha256(str(row.get("document_sha256") or ""))
        url = str(row.get("final_url") or row.get("source_url") or "")
        captured = str(row.get("captured_at") or as_of)
        method = {"ATTENDED_BROWSER": "attended_browser", "FIRECRAWL": "firecrawl_rendered_fetch",
                  "DIRECT_STATIC": "direct_static_fetch"}.get(str(row.get("lane")), str(row.get("lane")).lower())
        seen = set()
        for e in row.get("evidence") or ():
            for ref in e.get("field_refs") or ():
                field = _FIELD_MAP.get(ref)
                if not field or (field, e["quote"]) in seen:
                    continue
                seen.add((field, e["quote"]))
                ev_ref = "ev:" + SMP.sha256_text("%s|%s|%s" % (row["identity_key"], field, e["quote"]))[7:23]
                out.append(OrderedDict((
                    ("field", field), ("quote", str(e["quote"])), ("source_url", url),
                    ("evidence_ref", ev_ref), ("artifact_class", enums.PUBLICATION_GRADE_EVIDENCE),
                    ("artifact_sha256", digest), ("artifact_kind", enums.ARTIFACT_RENDERED_HTML),
                    ("captured_at", captured), ("capture_method", method), ("source_grade", _grade_for(url)),
                )))
        return out

    records: List["OrderedDict[str, Any]"] = []
    for key, row in pf_rows.items():
        name = str(row["canonical_name"])
        record: "OrderedDict[str, Any]" = OrderedDict((
            ("key", normalize_name(name)), ("identity_key", key), ("name", name),
            ("market_id", "nashville-tn"), ("schema_version", "1.3"),
            ("facts", _facts_from_extraction(row.get("extraction") or {})),
        ))
        statement = _service_animal(row.get("extraction") or {})
        if statement:
            record["service_animal_statement"] = statement
        record["source_url"] = str(row.get("final_url") or row.get("source_url") or "")
        record["corridor"] = str(row.get("corridor") or "")
        record["verified_at"] = str(row.get("captured_at") or as_of)
        record["capture_lane"] = str(row.get("lane") or "")
        record["verification_state"] = "VERIFIED_PET_FRIENDLY"
        record["evidence"] = evidence_entries(row)
        records.append(record)

    exclusions: List["OrderedDict[str, Any]"] = []
    for key, row in np_rows.items():
        name = str(row["canonical_name"])
        c = by_key.get(key, {})
        quote = " ".join(str(e.get("quote") or "") for e in (row.get("evidence") or ())[:1])
        exclusion: "OrderedDict[str, Any]" = OrderedDict((
            ("exclusion_id", "nas-" + slugify(name)), ("canonical_name", name),
            ("normalized_name", normalize_name(name)), ("address", str(c.get("address") or "")),
            ("city", str(c.get("city") or "")), ("state", str(c.get("state") or "")),
            ("postal_code", str(c.get("postal_code") or "")),
            ("official_url", str(c.get("official_url") or row.get("final_url") or "")),
            ("exclusion_state", HE.VERIFIED_NO_PETS), ("evidence_quote", quote),
            ("source_url", str(row.get("final_url") or row.get("source_url") or "")),
            ("observed_at", str(row.get("captured_at") or as_of)[:10]),
            ("source_hash", str(row.get("document_sha256") or "")),
            ("reviewer_id", ""), ("reviewed_at", ""),
            ("notes", "NOT founder-reviewed: the shadow branch was never promoted"),
            ("market_id", "nashville-tn"),
        ))
        exclusion["record_hash"] = HE.record_hash(exclusion)
        exclusion["approval_hash"] = HE.approval_hash(exclusion)
        exclusions.append(exclusion)

    seed_rows: List["OrderedDict[str, str]"] = []
    for key, row in pf_rows.items():
        c = by_key.get(key, {})
        seed_rows.append(OrderedDict((
            ("name", str(row["canonical_name"])), ("category", "pet-friendly-hotels"),
            ("address", str(c.get("address") or "")), ("city", str(c.get("city") or "")),
            ("state", str(c.get("state") or "")), ("postal_code", str(c.get("postal_code") or "")),
            ("phone", str(c.get("phone") or "")), ("website_url", str(c.get("official_url") or "")),
            ("source_url", str(row.get("final_url") or "")), ("source_type", "OFFICIAL_PROPERTY"),
            ("observed_at", str(row.get("captured_at") or as_of)[:10]), ("rating", ""), ("amenities", ""),
            ("pet_policy", ""), ("canonical", ""), ("market_id", "nashville-tn"),
        )))

    items: List["OrderedDict[str, Any]"] = []
    for r in census_rows:
        key = r["identity_key"]
        if key in pf_rows:
            state, resolved = enums.PUBLISHED_PET_FRIENDLY, True
        elif key in np_rows:
            state, resolved = enums.VERIFIED_NO_PETS, True
        else:
            state, resolved = "AWAITING_POLICY_OBSERVATION", False
        item = OrderedDict((("identity_key", key), ("canonical_name", r["canonical_name"]), ("slug", r["slug"]),
                            ("final_state", state), ("resolved", resolved)))
        if not resolved:
            item["next_action"] = "read the property's own policy page"
            item["next_action_source"] = "nashville_tn_clean_authority_001.json"
            item["determined_by"] = "ATLAS-THROUGHPUT-003 pilot derivation"
        items.append(item)
    counts = collections.Counter(i["final_state"] for i in items)
    partition = OrderedDict((("schema", PARTITION.SCHEMA), ("market_id", "nashville-tn"),
                             ("as_of", as_of), ("count", len(items)),
                             ("final_state_counts", OrderedDict(sorted(counts.items()))), ("items", items)))
    delta = zero_delta("nashville-tn")
    delta["add_property_ids"] = sorted(pf_rows)
    delta["expected_profile_delta"] = len(pf_rows)
    delta["expected_market_count_delta"] = 1
    delta["expected_participation_delta"] = [OrderedDict((("market_id", "nashville-tn"), ("from", False), ("to", True)))]
    delta["expected_verified_no_pets_delta"] = len(np_rows)
    return W.PackageInputs(
        market_id="nashville-tn", execution_zone=SMP.ZONE_SHADOW, created_from_source_sha=rev,
        market=market, census=census, pet_friendly_records=records, verified_no_pets_records=exclusions,
        official_routes=[], seed_rows=seed_rows, partition=partition, intended_delta=delta,
        parent_live_state=parent_from_live(live), dependency_input_digests=digests,
        founder_holds=[OrderedDict((("hold_id", "nashville-tn-founder-packet-001"),
                                    ("reason", "25 founder items in nashville_tn_founder_packet_001.json; none blocks promotion"),
                                    ("blocks_promotion", False)))],
    )


# --------------------------------------------------------------------------- #
# The pilot run.
# --------------------------------------------------------------------------- #

def _write_json(path: Path, doc: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def run_pilot(*, work_dir: Path, commit_package: bool = True, build: bool = True) -> "OrderedDict[str, Any]":
    from scripts.pettripfinder.throughput_profile import peak_working_set_mb

    started = time.perf_counter()
    work = Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    report: "OrderedDict[str, Any]" = OrderedDict((("schema", "ptf-atlas-throughput-003-pilot/1.0"),
                                                   ("started_at", datetime.now(timezone.utc).isoformat(timespec="seconds")),
                                                   ("packages", OrderedDict())))
    t = time.perf_counter()
    live = RI.live_index()
    report["live_index"] = OrderedDict((("seconds", round(time.perf_counter() - t, 3)),
                                        ("participating", list(live[0].participating)),
                                        ("total_profiles", live[0].total_profiles),
                                        ("digest", live[0].digest()), ("problems", list(live[2])),
                                        ("live_deploy_id", live[1].deploy_id),
                                        ("declared_identity_key_defects",
                                         sum(1 for m in live[0].markets.values() for p in m.profiles.values()
                                             if p.declared_identity_key and p.declared_identity_key != p.identity_key))))

    def run_one(label: str, inputs_fn, *, full: bool) -> None:
        entry: "OrderedDict[str, Any]" = OrderedDict()
        t0 = time.perf_counter()
        try:
            inputs = inputs_fn()
        except Exception as exc:
            entry["inputs_error"] = str(exc)[:300]
            report["packages"][label] = entry
            return
        entry["market_id"] = inputs.market_id
        entry["execution_zone"] = inputs.execution_zone
        entry["inputs_seconds"] = round(time.perf_counter() - t0, 3)
        t1 = time.perf_counter()
        try:
            package = seal(inputs)
        except W.PackageWriteError as exc:
            entry["package_write_seconds"] = round(time.perf_counter() - t1, 3)
            entry["writer"] = rejection_summary(exc)
            report["packages"][label] = entry
            return
        entry["package_write_seconds"] = round(time.perf_counter() - t1, 3)
        entry["writer"] = OrderedDict((("rejected", False), ("package_id", package["package_id"]),
                                       ("package_digest", package["package_digest"]),
                                       ("coverage_scorecard", package["coverage_scorecard"])))
        t2 = time.perf_counter()
        again = seal(inputs, sealed_at="2026-09-09T00:00:00Z")
        entry["writer_deterministic"] = again["package_digest"] == package["package_digest"]
        entry["second_write_seconds"] = round(time.perf_counter() - t2, 3)
        # A short work directory per package: Windows paths are limited to 260
        # characters and a generated profile route is ~90 of them.
        receipt = FL.run_fast_lane(package, work_dir=work / label.split("_", 1)[0].lower(), live=live,
                                   build=full and build, determinism=full and build)
        entry["receipt"] = OrderedDict((
            ("FAST_DATA_ONLY_RELEASE_ELIGIBLE", receipt["FAST_DATA_ONLY_RELEASE_ELIGIBLE"]),
            ("failed_rules", receipt["FAILED_RULES"]), ("unknown_rules", receipt["UNKNOWN_RULES"]),
            ("rule_status", OrderedDict((r, res["status"]) for r, res in receipt["RESULTS"].items())),
            ("per_rule_seconds", receipt["PERFORMANCE"]["per_rule_seconds"]),
            ("total_seconds", receipt["PERFORMANCE"]["total_seconds"]),
            ("determinism", receipt["DETERMINISM_RESULT"]),
            ("legacy_exceptions", receipt["LEGACY_EXCEPTIONS"]),
            ("problems", OrderedDict((r, res["problems"][:6]) for r, res in receipt["RESULTS"].items() if res["problems"])),
        ))
        entry["receipt_document"] = receipt
        entry["package_document"] = package
        report["packages"][label] = entry

    run_one("P1_dayton_frozen_zero_delta", lambda: frozen_inputs("dayton-oh", live), full=True)
    run_one("P2_dayton_withdrawal", lambda: withdrawal_inputs(live), full=True)
    if has_commit(NASHVILLE_REV):
        run_one("P3_nashville_shadow", lambda: nashville_inputs(live), full=False)
    if has_commit(TOLEDO_REV):
        tmp = work / "toledo_launch_package"
        run_one("P4_toledo_frozen", lambda: frozen_inputs("toledo-oh", live, launch_package=toledo_launch_package(TOLEDO_REV, tmp),
                                                          source_sha=TOLEDO_REV), full=False)

    # Index benchmark.
    p2 = report["packages"].get("P2_dayton_withdrawal", {})
    if p2.get("package_document"):
        package_index = RI.index_from_package(p2["package_document"], participating=True)
        report["index_benchmark"] = RI.benchmark(live[0], package_index, p2["package_document"]["intended_delta"],
                                                 sizes=(11, 25, 50, 100, 200))

    # Commit the pilot package and its receipt under the market's own directories.
    if commit_package and p2.get("package_document"):
        package = p2["package_document"]
        path = SMP.write_sealed(package)
        receipt_path = FL.write_receipt(p2["receipt_document"])
        report["committed"] = OrderedDict((("package", path.relative_to(REPO_ROOT).as_posix()),
                                           ("receipt", receipt_path.relative_to(REPO_ROOT).as_posix())))
    report["total_seconds"] = round(time.perf_counter() - started, 3)
    report["peak_working_set_mb"] = peak_working_set_mb()
    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--out", required=True, help="the fast-lane report JSON")
    parser.add_argument("--no-commit", action="store_true", help="do not write the pilot package/receipt into the tree")
    parser.add_argument("--no-build", action="store_true")
    args = parser.parse_args(argv)
    report = run_pilot(work_dir=Path(args.work_dir), commit_package=not args.no_commit, build=not args.no_build)
    slim = json.loads(json.dumps(report))
    for entry in slim["packages"].values():
        entry.pop("package_document", None)
        receipt = entry.pop("receipt_document", None)
        if receipt is not None:
            entry["receipt_digest"] = receipt.get("RECEIPT_DIGEST")
    _write_json(Path(args.out), slim)
    example = report["packages"].get("P2_dayton_withdrawal", {}).get("receipt_document")
    if example is not None:
        _write_json(Path(args.out).with_name("atlas_throughput_003_validation_receipt_example.json"), example)
    for label, entry in slim["packages"].items():
        print(label, entry.get("market_id"), "writer rejected" if entry.get("writer", {}).get("rejected") else "sealed",
              (entry.get("receipt") or {}).get("FAST_DATA_ONLY_RELEASE_ELIGIBLE"),
              (entry.get("receipt") or {}).get("failed_rules"), (entry.get("receipt") or {}).get("total_seconds"))
    print("total", slim["total_seconds"], "s; peak", slim["peak_working_set_mb"], "MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
