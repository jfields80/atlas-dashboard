# -*- coding: utf-8 -*-
"""PTF-CLEVELAND-AKRON-CANTON-HARDENED-APPLICATION-005 -- promote the reviewed
Cleveland shadow into the pinned source state, apply the pending policy
inventory, re-author the release contract. Deployment-bearing; deploys nothing.

    python -m scripts.pettripfinder.cleveland_akron_canton_oh_promotion_and_assembly_005
    python -m scripts.pettripfinder.cleveland_akron_canton_oh_promotion_and_assembly_005 --write
    python -m scripts.pettripfinder.build_global_authority --write
    python -m scripts.pettripfinder.cleveland_akron_canton_oh_promotion_and_assembly_005 --finish
    ... assemble ...
    python -m scripts.pettripfinder.cleveland_akron_canton_oh_promotion_and_assembly_005 --packet <bundle_manifest>

FOUNDER AUTHORIZATION (this order): promote the shadow census (188 -> 220),
apply the pending 21 CLEAN_PET_FRIENDLY records and 11 CLEAN_VERIFIED_NO_PETS
exclusions, apply the deterministic Oakwood explicit assignment, rebuild the
Cleveland release artifacts, assemble a dry-run candidate. NOT authorized:
deploy, consume a deployment authorization, apply held founder items, spend.

EVERY NUMBER IS DERIVED. The shadow is promoted whole with its lineage blocks
(admission, admission_003, admission_004, retired_non_lodging_002,
supersessions_002, every overlay marker); nothing is re-derived by hand.

EVERY FACT IS RE-READ BY THE CANONICAL READER AT APPLICATION TIME, from the
same first-party text the capture bound, and published only where the reader
represents the source:

  * the Extended Stay America blocks state TWO CEILINGS ("up to a $25 (+ tax)
    per day ... for the first six (6) nights" then "not to exceed $15 ... per
    day"), and CEILING != PRICE is a founder rule (established for the same
    brand wording by PTF-INDIANAPOLIS-PROMOTION-AND-ASSEMBLY-014): pet_fee is
    withheld SOURCE_AMBIGUOUS; pets_allowed and the two-pet limit publish.
    Their 36-inch size rule is withheld SCHEMA_CANNOT_REPRESENT, wording kept.
  * Red Roof Akron prices the FIRST pet free and the second at $15/night
    capped at $105/stay -- a per-additional-pet schedule the canonical reader
    does not produce; pet_fee is withheld SCHEMA_CANNOT_REPRESENT with the
    wording, while pets_allowed, the 3-pet limit, the 80 lb limit and the
    species publish.
  * a fee stated without a basis never publishes as a fee.

The held founder items (Cambria/Wyndham Avon, Motel 6 / HIE Richfield,
WoodSpring / ESA Select, Harbor Inn, Hopp Inn, Villa Croatia, the three
reader exceptions) are NOT applied: their rows stay unresolved under their
current keys.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import census_partition_builder as CPB       # noqa: E402
from scripts.pettripfinder import hotel_exclusions as EX               # noqa: E402
from scripts.pettripfinder import market_authority as MA               # noqa: E402
from scripts.pettripfinder import policy_migration as PM               # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR      # noqa: E402
from scripts.pettripfinder.brightdata import unlocker_capture as UC    # noqa: E402
from scripts.pettripfinder.contracts import census as CENSUS           # noqa: E402
from scripts.pettripfinder.contracts import enums                      # noqa: E402
from scripts.pettripfinder.contracts.fee_computation import classify   # noqa: E402
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key  # noqa: E402
from scripts.pettripfinder.release_contracts import (                  # noqa: E402
    contract_disagreements, derive_authority)

WORK_ORDER = "PTF-CLEVELAND-AKRON-CANTON-HARDENED-APPLICATION-005"
MARKET_ID = "cleveland-akron-canton-oh"
M = MARKET_ID.replace("-", "_")
OPERATOR = "jfields80"
REVIEWER = "PTF-FOUNDER-001"
AS_OF = "2026-09-01"

PKG = _REPO_ROOT / "launch_packages" / "pettripfinder"
PINNED = PKG / "identity_census" / f"{MARKET_ID}.json"
SHADOW = PKG / "identity_census_admission" / f"{MARKET_ID}.json"
MARKET_CONTRACT = PKG / "markets" / f"{MARKET_ID}.json"
PACKAGE = PKG / f"hotel_policy_facts_{MARKET_ID}.json"
STATE_004 = PKG / "markets" / "reports" / f"{M}_policy_state_004.json"
READS_004 = PKG / "markets" / "reports" / f"{M}_policy_reads_004.json"
READS_003 = PKG / "markets" / "reports" / f"{M}_policy_reads_003.json"
APP_002 = PKG / f"{M}_shadow_application_002.json"
PARTITION_002 = PKG / "cleveland_final_partition_002.json"
PARTITION_005 = PKG / "cleveland_final_partition_005.json"
UNRESOLVED = PKG / "cleveland_unresolved_manifest.json"
CONTRACT = _REPO_ROOT / "deploy" / "netlify" / "release_contracts" / f"{MARKET_ID}.json"
PARTICIPATION = _REPO_ROOT / "deploy" / "netlify" / "launch_participation.json"
REPORT = PKG / f"{M}_promotion_report_005.json"
PACKET = PKG / f"{M}_deployment_packet_005.json"
RAW_004 = _REPO_ROOT / "data" / "worker_runs" / "pettripfinder" / "cleveland-hardened-policy-004" / "raw"
RAW_003 = _REPO_ROOT / "data" / "worker_runs" / "pettripfinder" / "cleveland-hardened-policy-003" / "raw"
RAW_001 = _REPO_ROOT / "data" / "worker_runs" / "pettripfinder" / "cleveland-hardened-attended-001" / "raw"
ACQ_004 = _REPO_ROOT / "data" / "acquisition" / f"{M}_policy_reads_004"
OAKWOOD_KEYS = ("hampton inn and suites oakwood village cleveland",
                "quality inn and suites oakwood village cleveland south")
EAST = f"{MARKET_ID}__cleveland-east-beachwood"
ESA_HOST = "extendedstayamerica.com"


class PromotionError(RuntimeError):
    pass


def _load(path):
    text = Path(path).read_text(encoding="utf-8-sig")
    doc = json.loads(text, object_pairs_hook=OrderedDict)
    fmt = None
    for indent in (1, 2, 4):
        for ea in (True, False):
            for nl in ("\n", ""):
                if json.dumps(doc, indent=indent, ensure_ascii=ea) + nl == text:
                    fmt = (indent, ea, nl)
    return doc, (fmt or (1, False, "\n"))


def _dump(path, doc, fmt):
    Path(path).write_text(json.dumps(doc, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2],
                          encoding="utf-8", newline="\n")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _digits(v) -> str:
    return re.sub(r"\D", "", str(v or ""))


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# --------------------------------------------------------------------------- #
# Phase 2 -- promote the shadow census (whole, with lineage)
# --------------------------------------------------------------------------- #

def promote_census(shadow, pinned, market, route_repairs):
    new = json.loads(json.dumps(shadow), object_pairs_hook=OrderedDict)
    keys = [h["identity_key"] for h in new["hotels"]]
    if len(keys) != len(set(keys)):
        raise PromotionError("shadow carries duplicate identity keys")
    if new["count"] != len(keys):
        raise PromotionError("shadow count %s != rows %d" % (new["count"], len(keys)))
    retired = {e["identity_key"] for e in new.get("retired_non_lodging_002", [])}
    if retired & set(keys):
        raise PromotionError("a retired row is still active: %s" % sorted(retired & set(keys)))
    superseded = {s["from"]: s["to"] for s in new.get("supersessions_002", [])}
    pinned_keys = {h["identity_key"] for h in pinned["hotels"]}
    unaccounted = pinned_keys - set(keys) - retired - set(superseded)
    if unaccounted:
        raise PromotionError("pinned identities with no lineage in the shadow: %s" % sorted(unaccounted))
    for h in new["hotels"]:
        if ptf_identity_key(h["canonical_name"]) != h["identity_key"]:
            raise PromotionError("%s: canonical_name does not derive its identity_key" % h["identity_key"])
    # first-party route repairs proven by Order 004's bound reads (property page
    # whose own premises bind to the row); recorded on the row, never silent
    by_key = {h["identity_key"]: h for h in new["hotels"]}
    for key, (url, how, sha) in route_repairs.items():
        h = by_key[key]
        if h.get("official_url") != url:
            h["route_binding_005"] = OrderedDict([
                ("from", h.get("official_url") or ""), ("to", url), ("located_by", how),
                ("document_sha256", sha),
                ("why", "Order 004 read this row's policy on the property's own page and bound the row's "
                        "premises on that page's own address block; the census route is set to the page that "
                        "was actually read (%s)" % WORK_ORDER)])
            h["official_url"] = url
            h["has_official_link"] = True
    # no NEW duplicate physical address versus the pinned census
    def akey(h):
        return (re.sub(r"[^a-z0-9]+", " ", (h.get("address") or "").lower()).strip(), str(h.get("postal_code") or ""))
    dup_new = {k for k, n in Counter(akey(h) for h in new["hotels"]).items() if n > 1 and k[0]}
    dup_old = {k for k, n in Counter(akey(h) for h in pinned["hotels"]).items() if n > 1 and k[0]}
    if dup_new - dup_old:
        raise PromotionError("new duplicate physical address introduced: %s" % sorted(dup_new - dup_old))
    issues = [i for i in CENSUS.validate(new, market_states=tuple(getattr(market, "states", ()) or ()) or ("OH",))]
    if issues:
        raise PromotionError("promoted census does not validate: %s" % issues[:5])

    history = list(pinned.get("promotion_history") or [])
    if pinned.get("promotion"):
        history.append(pinned["promotion"])
    new["work_order"] = WORK_ORDER
    new["note"] = ("The PINNED Cleveland-Akron-Canton identity census, promoted whole from the reviewed "
                   "shadow admission census by %s. Every admission block (002/003/004), the three "
                   "non-lodging retirements, the Studio 6 -> Suburban Studios supersession, the display "
                   "overlays and the same-campus record travelled with it; nothing was re-derived. "
                   "The held founder items stay unresolved under their current keys. %s"
                   % (WORK_ORDER, shadow.get("note", "")))
    if history:
        new["promotion_history"] = history
    new["promotion"] = OrderedDict([
        ("what_this_is", "the founder-authorised promotion of the reviewed shadow census into the pinned production source census"),
        ("plan_work_order", WORK_ORDER), ("decided_by", "founder"), ("decided_on", AS_OF),
        ("from_count", len(pinned_keys)), ("to_count", len(keys)),
        ("source", "launch_packages/pettripfinder/identity_census_admission/%s.json" % MARKET_ID),
        ("source_sha256", _sha(json.dumps(shadow, ensure_ascii=False, sort_keys=True))),
        ("retired", sorted(retired)), ("renamed_from", sorted(superseded)),
        ("key_map", OrderedDict(sorted(superseded.items()))),
        ("route_repairs_005", sorted(route_repairs)),
        ("held_not_applied", list((shadow.get("admission_004") or {}).get("held_not_applied") or [])),
        ("orders_carried", ["PTF-CLEVELAND-AKRON-CANTON-HARDENED-REVALIDATION-001",
                            "PTF-CLEVELAND-AKRON-CANTON-HARDENED-APPLICATION-002",
                            "PTF-CLEVELAND-AKRON-CANTON-HARDENED-POLICY-003",
                            "PTF-CLEVELAND-AKRON-CANTON-HARDENED-POLICY-004"]),
        ("pinned_census_touched", True), ("deployment", "none; a separate founder authorization is required"),
    ])
    return new, sorted(retired), sorted(superseded)


# --------------------------------------------------------------------------- #
# Phase 3 -- Oakwood Village explicit assignment
# --------------------------------------------------------------------------- #

def apply_oakwood(contract, census_rows):
    east = next(c for c in contract["corridors"] if c["corridor_id"] == EAST)
    for key in OAKWOOD_KEYS:
        row = census_rows[key]
        if row["postal_code"] != "44146" or row.get("assignment_basis") != "explicit" or row.get("corridor") != EAST:
            raise PromotionError("%s is not in the ruled 003 state: %s / %s / %s"
                                 % (key, row["postal_code"], row.get("assignment_basis"), row.get("corridor")))
        if "44146" in east["included_postal_codes"]:
            raise PromotionError("ZIP 44146 must not be widened")
        if key not in east["explicit_hotel_ids"]:
            east["explicit_hotel_ids"].append(key)
        if key in east.get("excluded_hotel_ids", []):
            raise PromotionError("%s is excluded from its own corridor" % key)
    sentence = (" %s: the founder's Oakwood Village ruling (CLEARLY_WITHIN_EXISTING_MARKET_INTENT, "
                "PTF-CLEVELAND-AKRON-CANTON-HARDENED-POLICY-003 group C) is applied with the promotion "
                "that moved the rows: the two first-party-confirmed Oakwood Village hotels at 23300 and "
                "23303 Oakwood Commons Drive, 44146, are assigned EXPLICITLY to the cleveland-east-beachwood "
                "corridor. ZIP 44146 is NOT widened; no other hotel is admitted by this line; no corridor "
                "is created." % WORK_ORDER)
    note = contract.get("_boundary_note") or ""
    if WORK_ORDER not in note:
        contract["_boundary_note"] = (note + sentence).strip()
    return contract


# --------------------------------------------------------------------------- #
# Phase 4 -- pending evidence resolution (route, sha, text, lane per row)
# --------------------------------------------------------------------------- #

def artifact_windows(path):
    art = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    windows = [w for w in (art.get("pet_windows") or []) if w]
    return art, "\n".join(windows)


def pending_sources(state4, reads4, reads3, app2):
    """identity_key -> OrderedDict(evidence source facts) for every pending row."""
    out = OrderedDict()
    r4 = {r["identity_key"]: r for r in reads4["rows"]}
    r3 = {r["identity_key"]: r for r in reads3["rows"]}

    def attended(row, raw_dir):
        art, joined = artifact_windows(raw_dir / row["artifact_file"])
        hit = UC.locate_policy_in_text(joined)
        if not hit.found:
            raise PromotionError("%s: the bound windows no longer locate a policy block" % row["identity_key"])
        return OrderedDict([
            ("canonical_url", (row.get("final_url") or row.get("requested_url") or "").split("?")[0]),
            ("document_sha256", row["document_sha256"]), ("captured_at", row["captured_at"]),
            ("text", hit.text), ("kind", enums.ARTIFACT_TEXT_EXTRACT), ("method", "attended_chrome_render"),
            ("capture_order", row.get("source_artifact") and "pass-3 owned artifact (2026-08-16), reused by PTF-...-POLICY-004"
             or art.get("work_order")), ("artifact", str(Path(raw_dir.name) / row["artifact_file"]))])

    # --- 21 pet-friendly
    pend = state4["phase_10_pending_application"]["PENDING_SHADOW"]
    for key in pend["pet_friendly"]:
        if key == "suburban studios mentor cleveland northeast":
            b = app2["B_successor_pet_friendly"]
            art, joined = artifact_windows(RAW_001 / b["policy"]["artifact_file"])
            hit = UC.locate_policy_in_text(joined)
            if not hit.found:
                raise PromotionError("suburban studios: HA-001 windows no longer locate a policy block")
            out[key] = OrderedDict([
                ("canonical_url", b["successor"]["official_url"]), ("document_sha256", b["policy"]["document_sha256"]),
                ("captured_at", b["policy"]["observed_at"]), ("text", hit.text), ("kind", enums.ARTIFACT_TEXT_EXTRACT),
                ("method", "attended_chrome_render"), ("capture_order", "PTF-CLEVELAND-AKRON-CANTON-HARDENED-REVALIDATION-001 (HA-001)"),
                ("artifact", "cleveland-hardened-attended-001/raw/" + b["policy"]["artifact_file"]),
                ("founder_ruling", b["founder_ruling"])])
        elif key in r4 and r4[key]["lane"] == "STATIC":
            row = r4[key]
            block = Path(_REPO_ROOT / row["artifact_dir"] / "policy-block.txt").read_text(encoding="utf-8-sig").strip()
            out[key] = OrderedDict([
                ("canonical_url", row["requested_url"]), ("document_sha256", row["document_sha256"]),
                ("captured_at", row["captured_at"]), ("text", block), ("kind", enums.ARTIFACT_RENDERED_HTML),
                ("method", "deterministic_fetch"), ("capture_order", reads4["work_order"]),
                ("artifact", row["artifact_dir"])])
        elif key in r4:
            out[key] = attended(r4[key], RAW_004)
        elif key in r3:
            out[key] = attended(r3[key], RAW_003)
        else:
            raise PromotionError("no evidence source for pending PF row %s" % key)

    # --- 11 verified no-pets
    np_sources = OrderedDict()
    a2 = {r["identity_key"]: r for r in app2["A_clean_verified_no_pets"]}
    for key in pend["verified_no_pets"]:
        if key in a2:
            row = a2[key]
            np_sources[key] = OrderedDict([
                ("canonical_url", row["official_url"]), ("document_sha256", row["document_sha256"]),
                ("captured_at", row["observed_at"]), ("quote", row["evidence_quote"]),
                ("context", row["evidence_block"]), ("capture_order", "PTF-CLEVELAND-AKRON-CANTON-HARDENED-REVALIDATION-001 (%s)" % row["artifact_file"])])
        elif key in r4:
            row = r4[key]
            art, joined = artifact_windows(RAW_004 / row["artifact_file"])
            np_sources[key] = OrderedDict([
                ("canonical_url", (row.get("requested_url") or "").split("?")[0]), ("document_sha256", row["document_sha256"]),
                ("captured_at", row["captured_at"]), ("quote", (row.get("reader") or {}).get("block") or joined),
                ("context", joined), ("capture_order", reads4["work_order"])])
        elif key in r3:
            row = r3[key]
            art, joined = artifact_windows(RAW_003 / row["artifact_file"])
            np_sources[key] = OrderedDict([
                ("canonical_url", (row.get("requested_url") or row.get("final_url") or "").split("?")[0]),
                ("document_sha256", row["document_sha256"]), ("captured_at", row["captured_at"]),
                ("quote", (row.get("reader") or {}).get("block") or joined), ("context", joined),
                ("capture_order", reads3["work_order"])])
        else:
            raise PromotionError("no evidence source for pending no-pets row %s" % key)
    return out, np_sources


# --------------------------------------------------------------------------- #
# Phase 4 -- one pet-friendly record, facts re-read by the canonical reader
# --------------------------------------------------------------------------- #

def project_facts(key, text):
    rd = PR.parse(text)
    res = PR.to_extraction(rd, location=MARKET_ID)
    ext = res.extraction
    if ext.get("pets_allowed") is not True:
        raise PromotionError("%s: reader does not read pets_allowed True (%r)" % (key, ext.get("pets_allowed")))
    facts = OrderedDict([("pets_allowed", True)])
    withheld = OrderedDict()
    notes = []
    is_esa = "extended stay america" in key
    if is_esa:
        if "up to a $25" not in text or "$15" not in text:
            raise PromotionError("%s: the ESA two-ceiling wording is not on this page; re-review" % key)
        withheld["pet_fee"] = (enums.SOURCE_AMBIGUOUS,
            "the block states two CEILINGS, not a price: 'up to a $25 (+ tax) per day non-refundable "
            "cleaning fee for the first six (6) nights, per pet' and thereafter 'not to exceed $15 "
            "non-refundable fee (+tax) per day, per pet'. CEILING != PRICE is a founder rule "
            "(PTF-INDIANAPOLIS-PROMOTION-AND-ASSEMBLY-014, same brand wording); the canonical reader "
            "reads a single $15 line, which would publish the lower rung as the nightly fee. Withheld "
            "rather than published wrong; the wording is preserved here.")
        withheld["dimension_constraints"] = (enums.SCHEMA_CANNOT_REPRESENT,
            "'pets can be no longer than 36 inches and no taller than 36 inches' -- a size rule the "
            "canonical reader does not produce; preserved in wording.")
    elif key == "red roof inn akron":
        if "Stays Free" not in text:
            raise PromotionError("red roof: expected the first-pet-free wording")
        withheld["pet_fee"] = (enums.SCHEMA_CANNOT_REPRESENT,
            "'One, well-behaved domestic pet (cat or dog) Stays Free! ... Second pet $15/ night, not to "
            "exceed 7 nights or $105 per pet per stay.' -- a per-additional-pet schedule; the canonical "
            "reader produces no per-pet-ordinal pricing, so no single fee can be published without "
            "overcharging the first pet or hiding the second's. Withheld with the wording.")
    elif ext.get("pet_fee") is not None:
        basis = ext.get("fee_basis")
        if basis in ("per_night", "per_day"):
            charge = next((c for c in rd.charges if c.amount_minor == ext["pet_fee"]), None)
            fee = OrderedDict([("amount_cents", int(ext["pet_fee"])), ("currency", ext.get("fee_currency") or "USD"),
                               ("basis", "per_night")])
            if ext.get("fee_scope") == "per_pet":
                fee["scope"] = "per_pet"
            if charge is not None and charge.refundable is False:
                fee["refundable"] = False
            facts["pet_fee"] = fee
        elif basis == "per_stay":
            fee = OrderedDict([("amount_cents", int(ext["pet_fee"])), ("currency", ext.get("fee_currency") or "USD"),
                               ("basis", "per_stay")])
            if ext.get("fee_scope") == "per_pet":
                fee["scope"] = "per_pet"
            facts["pet_fee"] = fee
        else:
            withheld["pet_fee"] = (enums.SOURCE_SILENT,
                "a fee amount is stated but the page states no basis for it; a fee without its basis "
                "is not publishable (%r)" % basis)
    cap = ext.get("fee_cap")
    if cap and "pet_fee" in facts:
        if not getattr(rd, "fee_cap_quote", ""):
            raise PromotionError("%s: a fee cap without its stated qualifier sentence" % key)
        facts["fee_cap"] = OrderedDict([("amount_cents", int(cap["amount_minor"])), ("currency", cap.get("currency") or "USD"),
                                        ("basis", cap.get("basis") or "per_stay"),
                                        ("qualifier_stated", True)])
    if ext.get("pet_count_limit") is not None:
        facts["pet_count_limit"] = int(ext["pet_count_limit"])
        scope = str(rd.pet_count_scope or "").replace("per_", "").replace("per ", "").strip()
        if scope in ("room", "suite"):
            facts["pet_count_scope"] = "room" if scope == "room" else "suite"
    if ext.get("weight_limit"):
        facts["weight_limit"] = OrderedDict([("value", float(ext["weight_limit"]["value"])), ("unit", "lb"),
                                             ("operator", "lte"), ("scope", "per_pet")])
    species = OrderedDict()
    allowed = ext.get("species_allowed") or []
    if rd.cats_refused_quote:
        species["cats"] = enums.SPECIES_PROHIBITED
    elif "cat" in allowed:
        species["cats"] = enums.SPECIES_ACCEPTED
    if "dog" in allowed:
        species["dogs"] = enums.SPECIES_ACCEPTED
    if species:
        facts["species"] = species
    if getattr(rd, "contradictions", None):
        raise PromotionError("%s: reader reports contradictions: %s" % (key, list(rd.contradictions)))
    return facts, withheld, notes, rd


def _evidence(fields, quote, url, sha, kind, method, captured_at):
    entries = []
    for field in fields:
        entry = OrderedDict([
            ("field", field), ("quote", quote), ("source_url", url)])
        if field == "pets_allowed":
            entry["value"] = "true"
        entry.update(OrderedDict([
            ("evidence_ref", ""), ("artifact_class", "PUBLICATION_GRADE_EVIDENCE"),
            ("artifact_sha256", "sha256:%s" % sha), ("artifact_kind", kind),
            ("captured_at", captured_at), ("capture_method", method),
            ("source_grade", "PT1_FIRST_PARTY")]))
        entry["evidence_ref"] = PM.evidence_ref_for(entry)
        entries.append(entry)
    return entries


def build_record(key, src, census_row):
    facts, withheld, notes, rd = project_facts(key, src["text"])
    fields = ["pets_allowed"]
    if "pet_fee" in facts:
        fields += ["pet_fee", "fee_basis"]
        if "scope" in facts["pet_fee"]:
            fields.append("fee_scope")
    if "fee_cap" in facts:
        fields.append("fee_cap")
    for f in ("pet_count_limit", "weight_limit", "species"):
        if f in facts:
            fields.append(f)
    captured_at = src["captured_at"][:10]
    entries = _evidence(fields, src["text"], src["canonical_url"], src["document_sha256"], src["kind"], src["method"], captured_at)
    record = OrderedDict([
        ("key", key), ("name", census_row["canonical_name"]),
        ("facts", facts), ("evidence", entries), ("evidence_count", len(entries)),
        ("evidence_quote", src["text"]), ("source_url", src["canonical_url"]),
        ("source_type", "EXACT_ENTITY_DOMAIN"),
        ("verification_state", "VERIFIED_PET_FRIENDLY"),
        ("verification_date", captured_at), ("verified_at", captured_at),
        ("worker_model_id", ""), ("worker_prompt_version", ""),
        ("worker_result_hash", src["document_sha256"]),
        ("worker_routing_version", ""), ("worker_validator_version", ""),
        ("schema_version", "1.2"),
        ("identity_key", key), ("market_id", MARKET_ID),
        ("computation_class", classify(facts).computation_class),
    ])
    if withheld:
        record["withheld_fields"] = OrderedDict(
            (field, OrderedDict([("reason_code", code), ("reason", why), ("evidence_refs", [entries[0]["evidence_ref"]])]))
            for field, (code, why) in withheld.items())
    caveats = [
        "FOUNDER AUTHORIZATION (%s): apply the pending Cleveland CLEAN_PET_FRIENDLY inventory bound by "
        "orders 002/003/004 (the founder authorized these 21 records by this work order)." % WORK_ORDER,
        "Every fact was re-read by the canonical reader (policy_reading.parse / to_extraction) from the "
        "captured first-party text at application time; fields the reader cannot represent are withheld "
        "with a reason, never inferred.",
        ("Deterministic free HTTP fetch, $0: the artifact digest is the SHA256 of the served page (%s)."
         if src["kind"] == enums.ARTIFACT_RENDERED_HTML else
         "Attended Chrome render, $0: the artifact records the page's own address block, JSON-LD and the "
         "operative policy text with the page hashes (%s).") % src["capture_order"],
    ] + notes
    record["approval"] = OrderedDict([
        ("decision", enums.APPROVED_AFTER_CURRENT_REVIEW), ("operator", OPERATOR),
        ("approval_date", AS_OF), ("caveats", caveats),
        ("record_hash", PM.record_hash(record)), ("evidence_hash", PM.evidence_hash(entries)),
    ])
    return record


REFUSALS = ("not allowed", "not accepted", "no other pets", "no pets", "prohibited", "not permitted", "do not allow", "pets allowed: no")


def build_exclusion(key, src, census_row):
    quote = src["quote"]
    if not any(p in quote.lower() for p in REFUSALS):
        raise PromotionError("%s: refusal is not affirmative: %r" % (key, quote))
    rd = PR.parse(src.get("context") or quote)
    if rd.pets_allowed is not False:
        rd = PR.parse(quote)
        if rd.pets_allowed is not False:
            raise PromotionError("%s: reader does not read the refusal (%r)" % (key, rd.pets_allowed))
    record = OrderedDict([
        ("exclusion_id", "cle-" + key.replace(" ", "-")),
        ("canonical_name", census_row["canonical_name"]), ("normalized_name", key),
        ("address", census_row.get("address", "")), ("city", census_row.get("city", "")),
        ("state", census_row.get("state", "")), ("postal_code", census_row.get("postal_code", "")),
        ("official_url", src["canonical_url"]),
        ("exclusion_state", "VERIFIED_NO_PETS"),
        ("evidence_quote", quote),
        ("source_url", src["canonical_url"]), ("observed_at", src["captured_at"][:10]),
        ("source_hash", "sha256:%s" % src["document_sha256"]),
        ("reviewer_id", REVIEWER), ("reviewed_at", AS_OF),
        ("notes", "affirmative, property-specific refusal in the property's own rendered policy; the "
                  "service-animal sentence beside it is a legal access category and is never read as a pet "
                  "permission or as the refusal itself. Captured at $0 by %s; applied by %s under the "
                  "founder authorization this work order carries." % (src["capture_order"], WORK_ORDER)),
        ("market_id", MARKET_ID),
    ])
    record["record_hash"] = EX.record_hash(record)
    record["approval_hash"] = EX.approval_hash(record)
    return record


# --------------------------------------------------------------------------- #
# Phase 7 -- partition + unresolved manifest + contract
# --------------------------------------------------------------------------- #

def build_partition(census, published, excluded, prior):
    items = []
    for h in census["hotels"]:
        k = h["identity_key"]
        if k in published:
            state = "PUBLISHED_PET_FRIENDLY"
        elif k in excluded:
            state = "VERIFIED_NO_PETS"
        elif k in prior and prior[k]["final_state"] not in enums.TERMINAL_STATES:
            state = prior[k]["final_state"]
        else:
            state = enums.AWAITING_POLICY_OBSERVATION if h.get("official_url") else enums.AWAITING_OFFICIAL_URL
        items.append(CPB.partition_item(
            identity_key=k, canonical_name=h["canonical_name"], slug=h.get("slug") or _slug(h["canonical_name"]),
            city=h.get("city", ""), state=h.get("state", ""), postal_code=h.get("postal_code", ""),
            final_state=state,
            next_action_source=(prior.get(k, {}).get("next_action_source") or "carried from the promoted census by %s" % WORK_ORDER),
            determined_by=WORK_ORDER, updated_at=AS_OF, official_url=h.get("official_url", "")))
    return CPB.partition_document(
        MARKET_ID, items, as_of=AS_OF,
        note=("The Cleveland-Akron-Canton final partition over the 220-identity census promoted by %s: "
              "120 published, the verified-no-pets registry as the refusal authority, every other identity "
              "carrying the blocker state the 002 partition recorded or, for identities admitted since, the "
              "state its own row implies. The held founder items (successors, same-campus, non-lodging, "
              "reader exceptions) are blocked rows here, never authority. build_market_manifest maps this "
              "market to THIS document; unresolved is COUNTED from it." % WORK_ORDER),
        source_authorities=["identity_census/%s.json" % MARKET_ID, "hotel_policy_facts_%s.json" % MARKET_ID,
                            "markets/authority/%s/hotel_exclusions.json" % MARKET_ID, PARTITION_002.name])


def rebuild_unresolved_manifest(partition, old):
    prior_items = {i["normalized_name"]: i for i in old.get("items", [])}
    items = []
    for it in partition["items"]:
        if it["final_state"] in enums.TERMINAL_STATES:
            continue
        prev = prior_items.get(it["identity_key"])
        row = OrderedDict(prev) if prev else OrderedDict([
            ("normalized_name", it["identity_key"]), ("canonical_name", it["canonical_name"]),
            ("city", it["city"]), ("postal_code", it["postal_code"]), ("phone", ""),
            ("official_url", it.get("official_url", "")),
            ("classification", it["final_state"]),
        ])
        row["official_url"] = it.get("official_url", "") or row.get("official_url", "")
        items.append(row)
    counts = partition["final_state_counts"]
    published = counts.get("PUBLISHED_PET_FRIENDLY", 0)
    no_pets = counts.get("VERIFIED_NO_PETS", 0)
    old["as_of"] = AS_OF
    old["confirmed_identities"] = partition["count"]
    old["published_pet_friendly"] = published
    old["verified_no_pets"] = no_pets
    old["resolved"] = published + no_pets
    old["unresolved"] = len(items)
    old["classification_counts"] = OrderedDict(sorted(Counter(i["classification"] for i in items).items()))
    old["items"] = items
    old["application_005_update"] = OrderedDict([
        ("work_order", WORK_ORDER), ("as_of", AS_OF),
        ("what_changed", "census promoted 188 -> %d; 21 pet-friendly records and 11 verified-no-pets "
                         "exclusions applied from the hardened orders' bound artifacts; the unresolved set "
                         "is re-counted from cleveland_final_partition_005.json. A row admitted since the "
                         "2026-08-17 manifest carries its partition state as its classification." % partition["count"]),
    ])
    return old


def reauthor_contract(contract):
    derived = derive_authority(MARKET_ID)
    recon = dict(derived.reconciliation())
    contract["description"] = (
        "Deterministic release-gate contract for the PetTripFinder Cleveland-Akron-Canton market through %s. "
        "Calibrated to THIS market's committed authority; every number is derived from the authority files, "
        "none is typed." % WORK_ORDER)
    contract["deployment_authorization"] = OrderedDict([
        ("grants_deployment", False), ("asserts_market_complete", False),
        ("means", "A passing contract means this market's assembled package is STRUCTURALLY deployable: "
                  "its authority files agree, its routes match its reviewed inventory, no held identity "
                  "leaks, and every publish gate holds. It is not a deployment authorization: %s promoted "
                  "the census and applied the pending policy inventory and deployed nothing; the "
                  "authorization that put the previous 99-profile Cleveland live was signed against the "
                  "contract this one replaces and cannot authorise this state. %d of %d confirmed "
                  "identities remain unresolved." % (WORK_ORDER, recon["unresolved"], recon["confirmed_identities"])),
    ])
    pkg = contract["policy_package"]
    pkg["expected_sha256"] = derived.policy_package_sha256
    pkg["expected_schema_version"] = derived.policy_package_schema_version
    pkg["expected_record_count"] = derived.policy_package_record_count
    surface = contract["public_surface"]
    surface["seed_hotel_rows"] = derived.seed_hotel_rows
    surface["public_hotel_profile_count"] = derived.published_hotel_profiles
    surface["excluded_public_profile_count"] = derived.excluded_public_profiles
    routes = contract["routes"]
    routes["hotel_route_count"] = derived.hotel_route_count
    routes["published_corridor_route_count"] = derived.corridor_route_count
    recon_note = contract["reconciliation"].get("note", "")
    contract["reconciliation"] = OrderedDict(
        [(f, recon[f]) for f in ("confirmed_identities", "published_pet_friendly", "verified_no_pets", "resolved", "unresolved")]
        + [("note", "%s: census promoted 188 -> %d (three non-lodging retirements and the Studio 6 -> Suburban "
                    "Studios rebrand-successor rename with lineage), 21 pending pet-friendly records and 11 "
                    "verified-no-pets exclusions applied from the hardened orders' zero-cost captures. "
                    "resolved = published + verified_no_pets; unresolved is COUNTED from "
                    "cleveland_final_partition_005.json. | prior note: %s"
                    % (WORK_ORDER, recon["confirmed_identities"], recon_note))])
    contract["identity_census"]["expected_count"] = derived.confirmed_identities
    problems = contract_disagreements(contract, derived)
    return contract, derived, problems


# --------------------------------------------------------------------------- #

def route_repairs_from_reads(state4, reads4, shadow):
    """Rows applied this order whose verified 004 property route differs from the census route."""
    pend = state4["phase_10_pending_application"]["PENDING_SHADOW"]
    applied = set(pend["pet_friendly"]) | set(pend["verified_no_pets"])
    c4 = {c["identity_key"]: c for c in reads4["classification"]}
    by = {h["identity_key"]: h for h in shadow["hotels"]}
    repairs = OrderedDict()
    for key in sorted(applied):
        c = c4.get(key)
        if not c:
            continue
        url = (c.get("route") or "").split("?")[0]
        cur = (by.get(key) or {}).get("official_url") or ""
        if url and cur != url:
            e = c.get("evidence") or {}
            repairs[key] = (url, c.get("starting_lane", "") + "; " + (c.get("why") or ""), e.get("document_sha256") or "")
    return repairs


def finish():
    census, _ = _load(PINNED)
    package, _ = _load(PACKAGE)
    if len(census["hotels"]) != 220 or len(package["hotels"]) != 120:
        raise PromotionError("finish expects the written state (220 / 120), found %d / %d"
                             % (len(census["hotels"]), len(package["hotels"])))
    shard = MA.load_market_exclusions_document(MARKET_ID)
    published = {h["identity_key"] for h in package["hotels"]}
    excluded = {e["normalized_name"] for e in shard["exclusions"] if e.get("exclusion_state") == "VERIFIED_NO_PETS"}
    prior = {i["identity_key"]: i for i in _load(PARTITION_002)[0]["items"]}
    partition = build_partition(census, published, excluded, prior)
    CPB.write_json(PARTITION_005, partition)
    um, ufmt = _load(UNRESOLVED)
    um = rebuild_unresolved_manifest(partition, um)
    _dump(UNRESOLVED, um, ufmt)
    contract, cfmt = _load(CONTRACT)
    contract, derived, problems = reauthor_contract(contract)
    print("release-contract disagreements : %d" % len(problems))
    for p in problems:
        print("   ", p)
    if problems:
        raise PromotionError("re-authored contract still disagrees")
    _dump(CONTRACT, contract, cfmt)
    # participation: factual source-state note only; the launch status does not move
    part, pfmt = _load(PARTICIPATION)
    for m in part["markets"]:
        if m["market_id"] == MARKET_ID:
            if m["launch_status"] != "FOUNDER_AUTHORIZED_FOR_LAUNCH":
                raise PromotionError("Cleveland participation is %r; this order must not move it" % m["launch_status"])
            m["note"] = ("%d founder-authorized pet-friendly profiles and %d verified-no-pets exclusions over a "
                         "%d-identity census; contract re-authored by %s. The status is unchanged: Cleveland has "
                         "been live since PTF-047 and this line only restates the source package (188/99/40 -> "
                         "%d/%d/%d)." % (derived.published_hotel_profiles, derived.verified_no_pets,
                                         derived.confirmed_identities, WORK_ORDER, derived.confirmed_identities,
                                         derived.published_hotel_profiles, derived.verified_no_pets))
    _dump(PARTICIPATION, part, pfmt)
    report, _ = _load(REPORT)
    report["summary"]["partition_counts"] = partition["final_state_counts"]
    report["summary"]["reconciliation"] = dict(derived.reconciliation())
    report["summary"]["policy_package_sha256"] = derived.policy_package_sha256
    report["summary"]["release_contract_sha256"] = _sha(CONTRACT.read_text(encoding="utf-8"))
    report["summary"]["hotel_routes"] = derived.hotel_route_count
    report["summary"]["corridor_routes"] = derived.corridor_route_count
    Path(REPORT).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("WROTE partition 005, unresolved manifest, release contract, participation note, report")
    print(json.dumps(dict(derived.reconciliation()), ensure_ascii=False))
    return 0


def build_packet(manifest_path):
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8-sig"))
    report, _ = _load(REPORT)
    contract_sha = _sha(CONTRACT.read_text(encoding="utf-8"))
    deploy = json.loads((_REPO_ROOT / "deploy" / "netlify" / "deployment_records"
                         / "ptf-deploy-015-6a9713fcb727114045fa091e.json").read_text(encoding="utf-8-sig"))
    live_counts = deploy["profile_counts"]
    frags = manifest["fragments"]
    per_market = OrderedDict()
    for mid in sorted(set(live_counts) | set(frags)):
        live = live_counts.get(mid, 0)
        cand = frags.get(mid, {}).get("published_count", 0)
        per_market[mid] = OrderedDict([("live", live), ("candidate", cand), ("delta", cand - live)])
    nonzero = [mid for mid, d in per_market.items() if d["delta"] != 0]
    recon = report["summary"]["reconciliation"]
    packet = OrderedDict([
        ("schema", "ptf-deployment-packet/1.0"),
        ("what_this_is", "The exact deployment-authorization packet for the promoted Cleveland source state. "
                         "Prepared by %s, which is NOT a deployment authorization and consumed none: a separate "
                         "founder work order must authorize THIS source commit and THIS bundle sha256, and "
                         "nothing else." % WORK_ORDER),
        ("work_order", WORK_ORDER), ("market_id", MARKET_ID), ("as_of", AS_OF),
        ("schema_version", "1.2"),
        ("promoted_census_count", recon["confirmed_identities"]),
        ("pet_friendly_profiles", recon["published_pet_friendly"]),
        ("verified_no_pets", recon["verified_no_pets"]),
        ("resolved", recon["resolved"]), ("unresolved", recon["unresolved"]),
        ("policy_package_sha256", report["summary"]["policy_package_sha256"]),
        ("release_contract_sha256", contract_sha),
        ("candidate_bundle_sha256", manifest["bundle_sha256"]),
        ("candidate_sitemap_sha256", manifest["sitemap_sha256"]),
        ("candidate_source_commit", "TREE_AT_ASSEMBLY; re-assemble at the committed HEAD and compare (the 014 precedent: identical)"),
        ("candidate_assembled_from", "the working tree carrying the promoted Cleveland authority"),
        ("production_baseline_deploy_id", deploy["deployment_id"]),
        ("production_baseline_source_commit", deploy["source_commit"]),
        ("rollback_deploy_id_for_the_next_deployment", deploy["deployment_id"]),
        ("live_markets_before", len(live_counts)), ("live_markets_after", len(frags)),
        ("production_profiles_before", deploy["total_profiles"]),
        ("production_profiles_after", sum(f["published_count"] for f in frags.values())),
        ("sitemap_routes_before", deploy["sitemap_route_count"]),
        ("sitemap_routes_after", manifest["sitemap_route_count"]),
        ("html_pages_after", manifest["total_html_pages"]),
        ("gates", OrderedDict([("broken_links", manifest["broken_links"]), ("collisions", manifest["collision_count"]),
                               ("global_shadowing", manifest["global_shadowing_count"]),
                               ("canonical_violations", manifest["canonical_violations"])])),
        ("per_market_delta", per_market),
        ("markets_with_nonzero_delta", nonzero),
        ("unannounced_delta_check", "every non-zero market above is announced here before any authorization; "
                                    "the only expected non-zero market is cleveland-akron-canton-oh"),
        ("deployment_authorized", False), ("deployment_performed", False), ("authorization_consumed", False),
    ])
    Path(PACKET).write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("WROTE deployment packet:", PACKET.name)
    print(json.dumps(OrderedDict([("bundle", manifest["bundle_sha256"][:16]), ("per_market_nonzero", nonzero),
                                  ("profiles", "%s -> %s" % (packet["production_profiles_before"], packet["production_profiles_after"])),
                                  ("sitemap", "%s -> %s" % (packet["sitemap_routes_before"], packet["sitemap_routes_after"]))])))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--finish", action="store_true")
    parser.add_argument("--packet", default="", help="path to the assembled bundle_manifest.json")
    args = parser.parse_args(argv)
    from scripts.pettripfinder.markets import load_markets, market_by_id
    market = market_by_id(load_markets(), MARKET_ID)
    if args.finish:
        return finish()
    if args.packet:
        return build_packet(args.packet)

    shadow, sfmt = _load(SHADOW)
    pinned, pfmt = _load(PINNED)
    mcontract, mfmt = _load(MARKET_CONTRACT)
    package, kfmt = _load(PACKAGE)
    state4, _ = _load(STATE_004)
    reads4, _ = _load(READS_004)
    reads3, _ = _load(READS_003)
    app2, _ = _load(APP_002)
    if len(pinned["hotels"]) != 188 or len(shadow["hotels"]) != 220:
        raise PromotionError("starting state is not 188 pinned / 220 shadow")
    pend = state4["phase_10_pending_application"]["PENDING_SHADOW"]
    if len(pend["pet_friendly"]) != 21 or len(pend["verified_no_pets"]) != 11:
        raise PromotionError("pending inventory is %d/%d" % (len(pend["pet_friendly"]), len(pend["verified_no_pets"])))
    held = set(pend["held_with_evidence"]) | set(pend["founder_exceptions"])
    if held & (set(pend["pet_friendly"]) | set(pend["verified_no_pets"])):
        raise PromotionError("a held identity is in the pending application set")

    # Phase 4/5 evidence sources first: every applied row's route is the page its
    # policy was actually read from, and a differing census route is repaired on
    # the promoted row with the evidence digest (Phase 2 records it).
    pf_src, np_src = pending_sources(state4, reads4, reads3, app2)
    by_shadow = {h["identity_key"]: h for h in shadow["hotels"]}
    repairs = OrderedDict()
    for key, src in list(pf_src.items()) + list(np_src.items()):
        url = src["canonical_url"]
        cur = (by_shadow.get(key) or {}).get("official_url") or ""
        if url and EX.canonical_url(cur) != EX.canonical_url(url):
            repairs[key] = (url, "policy read bound on the page's own premises by %s" % src["capture_order"],
                            src["document_sha256"])

    # Phase 2
    census, retired, renamed_from = promote_census(shadow, pinned, market, repairs)
    rows = {h["identity_key"]: h for h in census["hotels"]}
    # Phase 3
    mcontract = apply_oakwood(mcontract, rows)

    # Phase 4/5
    published = {h["identity_key"] for h in package["hotels"]}
    shard = MA.load_market_exclusions_document(MARKET_ID)
    excluded = {e["normalized_name"] for e in shard["exclusions"] if e.get("exclusion_state") == "VERIFIED_NO_PETS"}
    records, exclusions = [], []
    for key, src in pf_src.items():
        if key not in rows:
            raise PromotionError("%s not in the promoted census" % key)
        if key in published or key in excluded:
            raise PromotionError("%s already in authority" % key)
        row = rows[key]
        if not row.get("official_url") or EX.canonical_url(row["official_url"]) != EX.canonical_url(src["canonical_url"]):
            raise PromotionError("%s: census route %r != evidence %r" % (key, row.get("official_url"), src["canonical_url"]))
        records.append(build_record(key, src, row))
    for key, src in np_src.items():
        if key not in rows or key in published or key in excluded:
            raise PromotionError("%s: not applicable as an exclusion" % key)
        row = rows[key]
        if not row.get("official_url") or EX.canonical_url(row["official_url"]) != EX.canonical_url(src["canonical_url"]):
            raise PromotionError("%s: census route %r != evidence %r" % (key, row.get("official_url"), src["canonical_url"]))
        exclusions.append(build_exclusion(key, src, row))
    keys = [r["identity_key"] for r in records]
    if len(set(keys)) != 21 or len(exclusions) != 11 or set(keys) & {e["normalized_name"] for e in exclusions}:
        raise PromotionError("duplicate or overlapping identities in the applied set")
    slugs = Counter(_slug(h["name"]) for h in package["hotels"] + records)
    if any(n > 1 for n in slugs.values()):
        raise PromotionError("duplicate profile route slug: %s" % [s for s, n in slugs.items() if n > 1])

    package["hotels"] = package["hotels"] + records
    if "count" in package:
        package["count"] = len(package["hotels"])
    from scripts.pettripfinder.contracts import policy_schema as PS
    gate_issues = list(PS.validate_package(package))
    if gate_issues:
        raise PromotionError("package fails the schema gate: %s" % gate_issues[:10])
    only_new = OrderedDict(package)
    only_new["hotels"] = records
    problems = PM.validate_migrated(only_new)
    if problems:
        raise PromotionError("new records do not validate: %s" % problems[:10])
    # Cleveland's committed shard order is historical (not globally sorted); the
    # prior rows keep their exact order and the new rows are appended sorted.
    shard["exclusions"] = list(shard["exclusions"]) + sorted(exclusions, key=lambda e: e["normalized_name"])
    shard["count"] = len(shard["exclusions"])
    validated = EX.validate(shard)
    if len(validated) != shard["count"]:
        raise PromotionError("exclusion shard validated %d of %d rows" % (len(validated), shard["count"]))

    seed_rows = MA.load_market_seed_rows(MARKET_ID)
    seed_names = {r["name"] for r in seed_rows}
    for r in records:
        h = rows[r["identity_key"]]
        if h["canonical_name"] in seed_names:
            raise PromotionError("seed row already present for %s" % h["canonical_name"])
        seed_rows.append(OrderedDict([
            ("name", h["canonical_name"]), ("category", "pet-friendly-hotels"),
            ("address", h.get("address", "")), ("city", h.get("city", "")), ("state", h.get("state", "")),
            ("postal_code", h.get("postal_code", "")), ("phone", _digits(h.get("phone"))),
            ("website_url", h["official_url"]), ("source_url", h["official_url"]),
            ("source_type", "OFFICIAL_PROPERTY"), ("observed_at", r["verified_at"]),
            ("rating", ""), ("amenities", ""), ("pet_policy", "pets allowed"), ("canonical", ""),
            ("market_id", MARKET_ID)]))

    summary = OrderedDict([
        ("pinned_before", 188), ("pinned_after", len(census["hotels"])),
        ("retired", retired), ("renamed_from", renamed_from),
        ("route_repairs", sorted(repairs)),
        ("oakwood_explicit", list(OAKWOOD_KEYS)),
        ("records_applied", keys), ("exclusions_applied", [e["normalized_name"] for e in exclusions]),
        ("withheld", OrderedDict((r["identity_key"], list((r.get("withheld_fields") or {}).keys()))
                                 for r in records if r.get("withheld_fields"))),
        ("package_count", len(package["hotels"])), ("exclusion_count", shard["count"]), ("seed_rows", len(seed_rows)),
    ])
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    if not args.write:
        print("(check only -- pass --write)")
        return 0

    _dump(PINNED, census, pfmt)
    shadow["promoted_into_pinned"] = OrderedDict([("work_order", WORK_ORDER), ("at", AS_OF), ("count", len(census["hotels"]))])
    _dump(SHADOW, shadow, sfmt)
    _dump(MARKET_CONTRACT, mcontract, mfmt)
    _dump(PACKAGE, package, kfmt)
    MA.exclusions_shard_path(MARKET_ID).write_text(MA.render_json(shard), encoding="utf-8", newline="\n")
    MA.seed_shard_path(MARKET_ID).write_text(MA.render_seed_csv(seed_rows), encoding="utf-8", newline="")
    Path(REPORT).write_text(json.dumps(OrderedDict([("schema", "ptf-promotion-report/1.0"), ("work_order", WORK_ORDER),
                                                    ("market_id", MARKET_ID), ("as_of", AS_OF), ("decided_by", "founder"),
                                                    ("paid_provider_calls", 0), ("usd_spent", 0.0), ("deployment_performed", False),
                                                    ("summary", summary)]), ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8", newline="\n")
    print("WROTE census, shadow marker, market contract, package, exclusions shard, seed shard, report")
    print("NEXT: build_global_authority --write, then --finish")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
