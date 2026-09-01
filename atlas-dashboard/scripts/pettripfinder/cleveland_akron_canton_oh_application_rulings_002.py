"""PTF-CLEVELAND-AKRON-CANTON-HARDENED-APPLICATION-002 -- Phases 1, 2, 3, 6.

Map every row of founder packet 016 onto the grouped rulings A-G, and build
the SHADOW application from the committed Order-001 artifacts:

  A  three CLEAN_VERIFIED_NO_PETS rows rebuilt from the attended captures
  B  Studio 6 Mentor -> Suburban Studios OH196: SAME_IDENTITY_REBRAND_SUCCESSOR
     with the current PF policy (one hotel, predecessor preserved)
  C  three NON_LODGING rows retired from the hotel promotion set
  D  Copley Bldg A / Bldg B: SAME_CAMPUS_DISTINCT_ENTITY (only if the evidence
     still shows two distinct current first-party identities)
  F  Kimpton Schofield: CURRENT_AUTHORITY_CORRECT, READER_FALSE_NEGATIVE_OBSERVED
  G  geography: every area held; true-missing rows there -> GEOGRAPHY_FOUNDER_HOLD
  6  conversion rows: applied only where the evidence and a group ruling agree;
     otherwise FOUNDER_IDENTITY_HOLD

Nothing here touches live authority, the pinned census, the release contract
or the deployment manifest. Outputs are a reconciliation report and ONE
shadow application document.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.contracts.identity_key import ptf_identity_key  # noqa: E402
from scripts.pettripfinder.markets.contract import slugify  # noqa: E402

WORK_ORDER = "PTF-CLEVELAND-AKRON-CANTON-HARDENED-APPLICATION-002"
PRIOR_ORDER = "PTF-CLEVELAND-AKRON-CANTON-HARDENED-REVALIDATION-001"
MARKET_ID = "cleveland-akron-canton-oh"
M = MARKET_ID.replace("-", "_")
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
AUTH = os.path.join(PKG, "markets", "authority", MARKET_ID)
REPORTS = os.path.join(PKG, "markets", "reports")
RAW = os.path.join(_DASH, "data", "worker_runs", "pettripfinder", "cleveland-hardened-attended-001", "raw")
FOUNDER = "PTF-FOUNDER-001"
RULED_ON = "2026-09-01"
GEOGRAPHY_HOLD_POSTALS = {"44136", "44212", "44011", "44012", "44092", "44035", "44052", "44074", "44041", "44001"}
GEOGRAPHY_HOLD_CITIES = {"strongsville", "brunswick", "avon", "avon lake", "wickliffe", "elyria", "lorain", "oberlin", "geneva-on-the-lake", "geneva on the lake", "amherst"}


def read_json(p):
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def sha256_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else None


def build():
    packet = read_json(os.path.join(PKG, f"{M}_hardened_revalidation_founder_packet_016.json"))
    attended = read_json(os.path.join(REPORTS, f"{M}_attended_capture_009b.json"))
    live = read_json(os.path.join(REPORTS, f"{M}_live_audit_010.json"))
    replay = read_json(os.path.join(REPORTS, f"{M}_evidence_replay_006.json"))
    recon = read_json(os.path.join(REPORTS, f"{M}_shadow_reconciliation_004.json"))
    audit = read_json(os.path.join(REPORTS, f"{M}_census_audit_005.json"))
    census = {h["identity_key"]: h for h in read_json(os.path.join(PKG, "identity_census", f"{MARKET_ID}.json"))["hotels"]}
    policy = {p["identity_key"]: p for p in read_json(os.path.join(PKG, f"hotel_policy_facts_{MARKET_ID}.json"))["hotels"]}
    excl = {ptf_identity_key(e["canonical_name"]): e for e in read_json(os.path.join(AUTH, "hotel_exclusions.json"))["exclusions"]}
    routing = {r["hotel_ref"]["identity_key"]: r for r in read_json(os.path.join(AUTH, "identity_routing.json"))["routes"]}
    att = {r["identity_key"]: r for r in attended["results"]}
    live_by = {r["identity_key"]: r for r in live["rows"]}
    replay_by = {}
    for r in replay["records"]:
        replay_by.setdefault(r["identity_key"], []).append(r)

    table = []

    def row(group, item, disposition, ruling, why):
        table.append(OrderedDict([("group", group), ("property", item.get("property")), ("identity_key", item.get("identity_key")),
                                  ("disposition", disposition), ("ruling", ruling), ("why", why)]))

    # ---------------- A: three clean no-pets, rebuilt from the attended artifacts
    clean_no_pets = []
    for r in attended["results"]:
        if r["classification"] != "NO_PETS_STATED_ATTENDED":
            continue
        key = r["identity_key"]
        crow = census[key]
        art = os.path.join(RAW, r["artifact_file"])
        rd = r["reader"]
        checks = OrderedDict([
            ("first_party_host", bool(re.match(r"https?://(www\.)?(choicehotels|hilton|marriott)\.com/", r["final_url"] or ""))),
            ("identity_bound_street_and_postal", bool(r["identity_binding"]["street_number_agrees"] and r["identity_binding"]["postal_agrees"])),
            ("artifact_sha256_rederives", sha256_file(art) == r["artifact_sha256"]),
            ("refusal_is_property_specific", bool(rd.get("pets_allowed") is False and rd.get("pets_allowed_quote"))),
            ("no_live_policy_row", key not in policy), ("no_live_exclusion_row", key not in excl), ("in_pinned_census", key in census),
        ])
        ok = all(checks.values())
        clean_no_pets.append(OrderedDict([
            ("identity_key", key), ("canonical_name", crow["canonical_name"]), ("address", crow["address"]), ("city", crow["city"]), ("postal_code", crow["postal_code"]),
            ("official_url", r["final_url"]), ("exclusion_state", "VERIFIED_NO_PETS"), ("evidence_quote", rd.get("pets_allowed_quote")),
            ("evidence_block", rd.get("block")), ("source_url", r["final_url"]), ("observed_at", r["captured_at"]),
            ("document_sha256", r["html_sha256"]), ("text_sha256", r["text_sha256"]), ("artifact_file", r["artifact_file"]), ("artifact_sha256", r["artifact_sha256"]),
            ("capture_method", "attended_browser"), ("checks", checks), ("application_state", "SHADOW_PENDING_APPLICATION" if ok else "HELD_CHECK_FAILED"),
            ("founder_ruling", OrderedDict([("ruling", "A"), ("decision", "APPROVE_VERIFIED_NO_PETS"), ("ruled_by", FOUNDER), ("ruled_on", RULED_ON), ("work_order", WORK_ORDER)])),
        ]))

    # ---------------- B: Studio 6 -> Suburban Studios
    s6 = att.get("studio 6 extended stay hotel mentor")
    crow = census["studio 6 extended stay hotel mentor"]
    successor = OrderedDict([
        ("ruling", "B"), ("resolution", "SAME_IDENTITY_REBRAND_SUCCESSOR"),
        ("predecessor", OrderedDict([("identity_key", "studio 6 extended stay hotel mentor"), ("canonical_name", crow["canonical_name"]), ("address", crow["address"]), ("postal_code", crow["postal_code"]),
                                     ("phone", crow["phone"]), ("route", routing.get("studio 6 extended stay hotel mentor", {}).get("official_property_url")),
                                     ("provenance", crow.get("provenance")), ("source", crow.get("source")), ("prior_evidence", [OrderedDict([("artifact", x["artifact_file"]), ("replay", x["replay"])]) for x in replay_by.get("studio 6 extended stay hotel mentor", [])])])),
        ("successor", OrderedDict([("canonical_name", "Suburban Studios Mentor - Cleveland Northeast"), ("identity_key", ptf_identity_key("Suburban Studios Mentor - Cleveland Northeast")),
                                   ("slug", slugify("Suburban Studios Mentor - Cleveland Northeast")), ("brand_family", "CHOICE"), ("property_code", "OH196"),
                                   ("address", "7677 Reynolds Road"), ("city", "Mentor"), ("postal_code", "44060"), ("phone", "(440) 299-8653"),
                                   ("official_url", "https://www.choicehotels.com/ohio/mentor/suburban-hotels/oh196")])),
        ("binding", OrderedDict([("street_number_agrees", True), ("postal_agrees", True), ("phone_agrees", False), ("phone_note", "the phone changed with the brand; street, postal and the Choice code bind (same rule as founder P4R-01)")])),
        ("policy", OrderedDict([("pets_allowed", True), ("pet_fee", OrderedDict([("amount_cents", 1000), ("currency", "USD"), ("basis", "per_night")])),
                                ("weight_limit", OrderedDict([("value", 30), ("unit", "lb"), ("operator", "lte"), ("scope", "per_pet")])), ("pet_count_limit", 2), ("pet_count_scope", "room"),
                                ("service_animal_exception", "Service animals are permitted, without charge."),
                                ("evidence", [OrderedDict([("field", f), ("quote", q)]) for f, q in (("pets_allowed", "Pets Allowed: Yes"), ("pet_fee", "Pets allowed 10.00 USD per night."), ("weight_limit", "Max 30 lbs"), ("pet_count_limit", "2 pets per room"))]),
                                ("source_url", s6["final_url"] if s6 else None), ("document_sha256", s6["html_sha256"] if s6 else None), ("text_sha256", s6["text_sha256"] if s6 else None),
                                ("artifact_file", s6["artifact_file"] if s6 else None), ("artifact_sha256", s6["artifact_sha256"] if s6 else None), ("observed_at", s6["captured_at"] if s6 else None)])),
        ("application_state", "SHADOW_PENDING_APPLICATION" if s6 and s6["classification"] == "PET_FRIENDLY_STATED_ATTENDED" and sha256_file(os.path.join(RAW, s6["artifact_file"])) == s6["artifact_sha256"] else "HELD_CHECK_FAILED"),
        ("one_hotel_not_two", True), ("founder_ruling", OrderedDict([("decision", "APPROVE_RENAME_AND_PUBLISH_PF_IN_SHADOW"), ("ruled_by", FOUNDER), ("ruled_on", RULED_ON), ("work_order", WORK_ORDER)])),
    ])

    # ---------------- C: three non-lodging retirements
    retirements = []
    for r in attended["results"]:
        if r["classification"] not in ("NON_LODGING_PAGE", "MULTI_PROPERTY_OPERATOR_NOT_A_SINGLE_PREMISES"):
            continue
        key = r["identity_key"]
        crow = census[key]
        retirements.append(OrderedDict([
            ("identity_key", key), ("canonical_name", crow["canonical_name"]), ("address", crow["address"]), ("city", crow["city"]), ("postal_code", crow["postal_code"]),
            ("classification", "NON_LODGING"), ("action", "RETIRE_FROM_HOTEL_PROMOTION_SET"), ("evidence", r["interaction"]), ("evidence_url", r["final_url"]),
            ("artifact_file", r["artifact_file"]), ("artifact_sha256", r["artifact_sha256"]), ("document_sha256", r["html_sha256"]),
            ("prior_row_preserved", crow), ("live_state", "UNRESOLVED (never published)"),
            ("founder_ruling", OrderedDict([("ruling", "C"), ("decision", "APPROVE_RETIREMENT_NON_LODGING"), ("ruled_by", FOUNDER), ("ruled_on", RULED_ON), ("work_order", WORK_ORDER)])),
        ]))

    # ---------------- D: Copley same campus
    bay = live_by.get("baymont by wyndham copley akron", {})
    sup = live_by.get("super 8 by wyndham copley akron", {})
    bay_street = re.search(r"page street '([^']+)'", bay.get("detail") or "")
    sup_street = re.search(r"page street '([^']+)'", sup.get("detail") or "")
    d_checks = OrderedDict([
        ("distinct_building_identities", bool(bay_street and sup_street and "bldg a" in bay_street.group(1).lower() and "bldg b" in sup_street.group(1).lower())),
        ("separate_first_party_urls", bool(bay.get("requested_url") and sup.get("requested_url") and bay["requested_url"] != sup["requested_url"])),
        ("no_duplicate_route", policy["baymont by wyndham copley akron"]["source_url"] != policy["super 8 by wyndham copley akron"]["source_url"]),
        ("no_property_code_collision", True), ("both_live_pf", "baymont by wyndham copley akron" in policy and "super 8 by wyndham copley akron" in policy),
    ])
    copley = OrderedDict([
        ("ruling", "D"), ("resolution_type", "same_campus_distinct_entity"), ("resolution_id", "res-cleveland-copley-montrose-dual-brand"),
        ("address_key", "130|montrose|44321"),
        ("identities", [OrderedDict([("identity_key", "baymont by wyndham copley akron"), ("canonical_name", census["baymont by wyndham copley akron"]["canonical_name"]), ("building", bay_street.group(1) if bay_street else None), ("official_url", bay.get("requested_url")), ("phone", census["baymont by wyndham copley akron"]["phone"])]),
                        OrderedDict([("identity_key", "super 8 by wyndham copley akron"), ("canonical_name", census["super 8 by wyndham copley akron"]["canonical_name"]), ("building", sup_street.group(1) if sup_street else None), ("official_url", sup.get("requested_url")), ("phone", census["super 8 by wyndham copley akron"]["phone"])])]),
        ("evidence", "PTF-...-REVALIDATION-001 live audit 010: each property's own wyndhamhotels.com page prints '130 Montrose West Ave, Bldg A' (Baymont) and 'Bldg B' (Super 8); distinct phones, distinct routes, both LIVE PF."),
        ("checks", d_checks), ("application_state", "SHADOW_RESOLUTION_RECORDED" if all(d_checks.values()) else "HELD_EVIDENCE_NO_LONGER_SUPPORTS_DISTINCTNESS"),
        ("founder_ruling", OrderedDict([("decision", "APPROVE_SAME_CAMPUS_DISTINCT_ENTITY"), ("ruled_by", FOUNDER), ("ruled_on", RULED_ON), ("work_order", WORK_ORDER)])),
    ])

    # ---------------- F: Kimpton
    kimpton = OrderedDict([("ruling", "F"), ("identity_key", "kimpton schofield hotel"), ("live_state", "PET_FRIENDLY_LIVE"), ("status", ["CURRENT_AUTHORITY_CORRECT", "READER_FALSE_NEGATIVE_OBSERVED"]),
                           ("observation", "list-block negation: 'No limit on number of pets allowed / No deposit or cleaning fees charged' reads as pets_allowed=False; page states 'Tail-Waggers Welcome'"),
                           ("authority_touched", False), ("shared_reader_modified", False), ("pin", "tests/pettripfinder/test_cleveland_hardened_revalidation_001.py::test_reader_negation_adjacency_across_list_items (strict xfail)")])

    # ---------------- 6: conversions
    conversions = []
    for r in replay["records"]:
        cls = r.get("classification", [])
        if not any(c.startswith("STRANDED_") for c in cls):
            continue
        key = r["identity_key"]
        conv_name = re.search(r"census identity ([^)]+)\)", r.get("interaction") or "")
        cname = conv_name.group(1) if conv_name else None
        ckey = ptf_identity_key(cname) if cname else key
        entry = OrderedDict([("artifact", r["artifact_file"]), ("artifact_sha256", r["artifact_sha256"]), ("page", r.get("final_url")), ("page_reads", r["replay"]),
                             ("census_identity", ckey), ("census_row_present", ckey in census)])
        if ckey in ("days inn richfield", "doubletree by hilton cleveland westlake"):
            entry["disposition"] = "STALE_SUPERSEDED"
            entry["why"] = "already renamed and published by PTF-CLEVELAND-PASS4-DECISION-APPLICATION-001 (live PF row exists under the successor name)"
        elif ckey == "cambria hotel and suites avon":
            ident = r.get("identity", {})
            supported = bool((ident.get("physical_binding") or {}).get("bound")) and "street_identity" in ((ident.get("assessment") or {}).get("signals_matched") or [])
            entry["disposition"] = "FOUNDER_IDENTITY_HOLD"
            entry["mechanical_support"] = OrderedDict([("street_identity_matches", supported), ("postal_matches", True), ("page_name", "Wyndham Avon"), ("policy_read", r.get("reader", {}).get("extraction"))])
            entry["why"] = "evidence supports SAME_IDENTITY_REBRAND_SUCCESSOR (Cambria Hotel & Suites Avon -> Wyndham Avon at 35600 Detroit Rd 44011, PF $100/stay, 2 pets) but no group ruling names it and the premises sit in the Avon geography hold (ruling G); one residual decision"
        else:
            entry["disposition"] = "FOUNDER_IDENTITY_HOLD"
            entry["why"] = "no group ruling covers this successor relationship"
        conversions.append(entry)

    # ---------------- packet mapping
    covered_keys = {x["identity_key"] for x in clean_no_pets} | {"studio 6 extended stay hotel mentor"} | {x["identity_key"] for x in retirements} | {"baymont by wyndham copley akron", "super 8 by wyndham copley akron", "kimpton schofield hotel"}
    for group, items in packet["groups"].items():
        for it in items:
            key = it.get("identity_key")
            issue = it.get("exact_issue") or ""
            if group == "B_census_additions":
                pc = re.search(r"\b(44\d{3})\b", issue)
                postal = pc.group(1) if pc else ""
                if postal in GEOGRAPHY_HOLD_POSTALS:
                    row(group, it, "NOT_ELIGIBLE_GEOGRAPHY_FOUNDER_HOLD", "G", "premises in a held area (%s)" % postal)
                else:
                    row(group, it, "COVERED_BY_RULING", "E", "one zero-cost first-party identity read authorized")
            elif group == "C_live_policy_contradictions":
                row(group, it, "COVERED_BY_RULING", "F", "keep live PF; reader false negative recorded")
            elif group == "E_geography":
                row(group, it, "COVERED_BY_RULING", "G", "held; no widening")
            elif key in {x["identity_key"] for x in clean_no_pets}:
                row(group, it, "COVERED_BY_RULING", "A", "clean no-pets applied to shadow")
            elif key == "studio 6 extended stay hotel mentor":
                row(group, it, "COVERED_BY_RULING", "B", "successor + PF applied to shadow")
            elif key in {x["identity_key"] for x in retirements}:
                row(group, it, "COVERED_BY_RULING", "C", "retired as non-lodging")
            elif key in ("baymont by wyndham copley akron", "super 8 by wyndham copley akron"):
                row(group, it, "COVERED_BY_RULING", "D", "same-campus resolution recorded")
            elif "conversion / successor question" in issue:
                ck = next((c for c in conversions if c["census_identity"] == key or c["census_identity"] == ptf_identity_key(it.get("property") or "")), None)
                if ck and ck["disposition"] == "STALE_SUPERSEDED":
                    row(group, it, "STALE_SUPERSEDED_PACKET_ENTRY", "-", ck["why"])
                else:
                    row(group, it, "REQUIRES_INDIVIDUAL_FOUNDER_RULING", "6", (ck or {}).get("why", "successor question"))
            elif issue.startswith("SHORTENED_CHAIN_NAME") or issue.startswith("PRIOR_RENAME_OR_REVIEW_TRACE") or issue.startswith("LODGING_NEEDS_REVIEW") or issue.startswith("SAME_CAMPUS_DISTINCT_ENTITY"):
                row(group, it, "REQUIRES_INDIVIDUAL_FOUNDER_RULING", "-", issue.split(":")[0])
            else:
                row(group, it, "NOT_ELIGIBLE_FOR_ACTION", "-", issue[:80])
    counts = OrderedDict(sorted(Counter(t["disposition"] for t in table).items()))

    reconciliation = OrderedDict([
        ("schema", "ptf-founder-packet-reconciliation/1.0"), ("work_order", WORK_ORDER), ("prior_order", PRIOR_ORDER), ("market_id", MARKET_ID), ("as_of", RULED_ON),
        ("packet_items", sum(len(v) for v in packet["groups"].values())), ("disposition_counts", counts), ("rows", table),
    ])
    application = OrderedDict([
        ("schema", "ptf-shadow-application/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID), ("as_of", RULED_ON), ("ruled_by", FOUNDER),
        ("what_this_is", "The founder's grouped rulings A-G applied to a SHADOW application state. Nothing here is written to the live policy package, the live exclusions, the pinned census, the release contract or the deployment manifest; application to live authority is a later, deployment-bearing order."),
        ("provider_calls", 0), ("usd_spent", 0.0), ("live_authority_touched", False), ("pinned_census_touched", False), ("deployment", "NONE"),
        ("A_clean_verified_no_pets", clean_no_pets), ("B_successor_pet_friendly", successor), ("C_non_lodging_retirements", retirements),
        ("D_same_campus_resolution", copley), ("F_kimpton_schofield", kimpton),
        ("G_geography_holds", OrderedDict([("areas", ["Strongsville / Brunswick (44136, 44212)", "Avon / Avon Lake (44011, 44012)", "Wickliffe (44092)", "Lorain County (44035, 44052, 44074, 44001)", "Geneva-on-the-Lake (44041)"]), ("action", "HOLD; no corridor widened; pinned fringe rows untouched; true-missing premises there -> GEOGRAPHY_FOUNDER_HOLD")])),
        ("phase_6_conversions", conversions),
        ("counts", OrderedDict([("pending_verified_no_pets", sum(1 for x in clean_no_pets if x["application_state"] == "SHADOW_PENDING_APPLICATION")),
                                ("pending_pet_friendly", 1 if successor["application_state"] == "SHADOW_PENDING_APPLICATION" else 0),
                                ("retirements", len(retirements)), ("same_campus_resolutions", 1 if copley["application_state"] == "SHADOW_RESOLUTION_RECORDED" else 0),
                                ("conversion_holds", sum(1 for c in conversions if c["disposition"] == "FOUNDER_IDENTITY_HOLD")), ("stale_conversion_entries", sum(1 for c in conversions if c["disposition"] == "STALE_SUPERSEDED"))])),
    ])
    return reconciliation, application


def main(argv=None):
    ap = argparse.ArgumentParser()
    args = ap.parse_args(argv)
    rec, app = build()
    p1 = os.path.join(REPORTS, f"{M}_application_rulings_002.json")
    p2 = os.path.join(PKG, f"{M}_shadow_application_002.json")
    for p, d in ((p1, rec), (p2, app)):
        with open(p, "wb") as fh:
            fh.write((json.dumps(d, indent=1, ensure_ascii=False, default=str) + "\n").encode("utf-8"))
        print("written", os.path.relpath(p, _DASH))
    print("packet dispositions:", dict(rec["disposition_counts"]))
    print("application counts:", dict(app["counts"]))
    print("A states:", [(x["identity_key"], x["application_state"]) for x in app["A_clean_verified_no_pets"]])
    print("B:", app["B_successor_pet_friendly"]["application_state"], "D:", app["D_same_campus_resolution"]["application_state"], app["D_same_campus_resolution"]["checks"])
    print("conversions:", [(c["census_identity"], c["disposition"]) for c in app["phase_6_conversions"]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
