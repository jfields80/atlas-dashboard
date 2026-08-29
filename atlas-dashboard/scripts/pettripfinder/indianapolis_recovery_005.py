# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-50-PLUS-PET-FRIENDLY-RECOVERY-005 -- what is left to recover, and what it costs.

The work order asks for +26 pet-friendly profiles (24 -> 50) and asks that they
be found, in order, from: reusable paid evidence we already own, routing repairs
that cost nothing, and zero-cost URL recovery -- before any money is discussed.

This module answers that question from saved documents only. It fetches nothing,
spends nothing and changes no authority. It writes two artifacts:

    indianapolis_in_recovery_audit_005.json      phases 1-3
    indianapolis_in_recovery_cost_plan_005.json  phase 5 (a projection, NOT an
                                                 authorization)

THE ONE THING TO UNDERSTAND ABOUT THE 54 "REUSABLE EVIDENCE" ROWS
The cross-run ledger reports 54 Indianapolis identities as
SUPPRESSED_EVIDENCE_REUSABLE. That decision means "we already own the answer to
this page", and for 48 of them the answer is already spent: they ARE the current
authority -- 24 promoted pet-friendly and 24 signed VERIFIED_NO_PETS. Reusable
is not the same as untapped. Only 6 are unsigned, and 5 of those never produced
an artifact at all.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import paid_attempt_ledger as PAL  # noqa: E402
from scripts.pettripfinder.acquisition import registry as REGISTRY        # noqa: E402
from scripts.pettripfinder.brightdata import corpus as CORPUS             # noqa: E402

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
PRIOR_CENSUS = (_REPO_ROOT / "data" / "prior_evidence" / "indianapolis_001"
                / "git_cbb9863" / "launch_packages" / "pettripfinder"
                / "identity_census" / "indianapolis-in.json")

SCHEMA = "ptf-market-recovery-audit/1.0"
PLAN_SCHEMA = "ptf-market-recovery-cost-plan/1.0"
WORK_ORDER = "PTF-INDIANAPOLIS-50-PLUS-PET-FRIENDLY-RECOVERY-005"
MARKET = "indianapolis-in"
TARGET_PET_FRIENDLY = 50

# Phase-1 classifications.
ALREADY_PROMOTED = "ALREADY_PROMOTED_PET_FRIENDLY"
ALREADY_NO_PETS = "ALREADY_SIGNED_VERIFIED_NO_PETS"
READY_REVIEW = "READY_FOR_FOUNDER_REVIEW"
READY_NO_PETS = "READY_VERIFIED_NO_PETS"
NEEDS_REPARSE = "NEEDS_POLICY_REPARSE"
NEEDS_IDENTITY = "NEEDS_IDENTITY_REPAIR"
STALE = "STALE_EVIDENCE"
NOT_GRADE = "NOT_PUBLICATION_GRADE"

# Phase-2 routing verdicts.
ROUTE_REPAIRED = "ROUTE_REPAIRED_ZERO_COST"
ROUTE_CORRECT_RULE = "ROUTE_CORRECT_IDENTITY_RULE_TOO_STRICT"
ROUTE_CORRECT_ADDR = "ROUTE_CORRECT_CENSUS_ADDRESS_DISPUTED"
NEEDS_ADJUDICATION = "NEEDS_FOUNDER_ADJUDICATION"


def _load(name):
    return json.loads((LP / name).read_text(encoding="utf-8"))


def _artifact_files(path: str) -> List[str]:
    if not path or not os.path.isdir(path):
        return []
    return sorted(os.listdir(path))


def _policy_text(path: str) -> str:
    block = Path(path) / "policy-block.txt" if path else None
    if block and block.is_file():
        return block.read_text(encoding="utf-8", errors="replace").strip()
    return ""


def build() -> Dict:
    ledger = _load("ptf_paid_attempt_ledger_001.json")
    census = _load("identity_census/indianapolis-in.json")
    package = _load("hotel_policy_facts_indianapolis-in.json")
    exclusions = _load("markets/authority/indianapolis-in/hotel_exclusions.json")
    merged = _load("indianapolis_in_acquisition_merged_promotion_003.json")
    pass1 = _load("indianapolis_in_market_acquisition_pass1_002.json")

    key_map = census["promotion"]["key_map"]
    promoted = {h["identity_key"] for h in package["hotels"]}
    no_pets = {e["normalized_name"] for e in exclusions["exclusions"]}
    signed = promoted | no_pets
    census_by_key = {h["identity_key"]: h for h in census["hotels"]}
    pass1_by_key = {r["identity_key"]: r for r in pass1["results"]}

    def promoted_key(k):
        return key_map.get(k, k)

    _payable, suppressed = PAL.suppress(merged["results"], ledger)
    attempted = {promoted_key(r["identity_key"]) for r in merged["results"]}

    # ---------------------------------------------------------------- phase 1
    reusable = [r for r in suppressed
                if r["paid_history"]["decision"] == PAL.SUPPRESSED_EVIDENCE_REUSABLE]
    phase1: List[Dict] = []
    for row in reusable:
        key = row["identity_key"]
        pkey = promoted_key(key)
        history = row["paid_history"]
        artifact = history.get("prior_artifact") or ""
        files = _artifact_files(artifact)
        block = _policy_text(artifact)

        if pkey in promoted:
            verdict, why = ALREADY_PROMOTED, ("this row IS one of the 24 promoted "
                                              "profiles; its evidence is already spent")
        elif pkey in no_pets:
            verdict, why = ALREADY_NO_PETS, ("this row IS one of the 24 signed "
                                             "VERIFIED_NO_PETS rows; already spent")
        elif not files:
            verdict, why = NOT_GRADE, ("the attempt ended %s and saved no artifact, so "
                                       "there is nothing to re-read; only a new fetch "
                                       "could answer it" % row.get("outcome"))
        elif block:
            verdict, why = NEEDS_REPARSE, ("an artifact with a policy block survives and "
                                           "can be re-read with no fetch")
        else:
            verdict, why = NOT_GRADE, "an artifact survives but carries no policy block"

        phase1.append(OrderedDict((
            ("identity_key", key), ("promoted_key", pkey),
            ("canonical_name", row.get("canonical_name") or ""),
            ("prior_outcome", history.get("prior_outcome")),
            ("final_state", row.get("final_state")),
            ("publication_grade", bool(row.get("publication_grade"))),
            ("artifact", artifact), ("artifact_files", files),
            ("policy_block", block), ("classification", verdict), ("why", why),
        )))

    # ---------------------------------------------------------------- phase 2
    repair_rows = [r for r in suppressed
                   if r["paid_history"]["routing_repair_required"]]
    # Diagnoses read out of the pass-1 identity detail; every one of them is a
    # statement the saved run already made, not a new inference of ours.
    diagnoses = {
        "delta hotels by marriott indianapolis airport": (
            ROUTE_REPAIRED,
            "the census URL is a legacy marriott.com/hotels/travel/... shape and the "
            "page returned a 404. The property code indde is known and every other "
            "Marriott row in this market routes through the short marriott.com/<code> "
            "form, which resolves to the modern /en-us/hotels/<code>-.../overview/ "
            "page. Repair is deterministic and costs nothing.",
            "https://www.marriott.com/indde"),
        "courtyard by marriott indianapolis northwest": (
            ROUTE_CORRECT_RULE,
            "the page is the right hotel -- title and property code indnw both agree -- "
            "and the only disagreement is that the page writes the street as "
            "'7226 Woodland Drive at 71st Street' where the census holds "
            "'7226 Woodland Drive'. The census street is a prefix of the page street. "
            "The route needs no repair; the identity comparison is too strict.", ""),
        "days inn by wyndham plainfield": (
            ROUTE_CORRECT_RULE,
            "the page writes '2245 East Perry Road' where the census holds "
            "'2245 Perry Road' -- the same address with the directional restored. The "
            "page also prints a second property's telephone because one Wyndham page "
            "lists several properties, which is a known shape and not evidence of a "
            "wrong route.", ""),
        "residence inn indianapolis airport": (
            ROUTE_CORRECT_ADDR,
            "title and property code indap both agree; the page states "
            "'5224 West Southern Avenue' and the census holds '5228'. One of the two "
            "street numbers is wrong and the first-party page is the better authority, "
            "but correcting a census address is a founder-visible change, not a "
            "silent one.", ""),
        "comfort suites indianapolis airport": (
            NEEDS_ADJUDICATION,
            "the page at choicehotels in293 states '2750 Fortune Circle West'; the "
            "census kept '2181 West Southern Avenue' for this key AND records a "
            "held-for-review candidate at 2750 Fortune Circle West. Either the census "
            "kept the wrong address for this key, or Indianapolis has two Comfort "
            "Suites and this URL belongs to the held one. The census's own collision "
            "record is the evidence; the founder decides which.", ""),
        "baymont by wyndham plainfield indianapolis airport area": (
            NEEDS_ADJUDICATION,
            "the page name matches THIS row exactly but the page street "
            "'6010 Gateway Drive' is the OTHER Baymont row's census address. Two census "
            "identities point at one Wyndham page.", ""),
        "baymont inn and suites plainfield indianapolis airport": (
            NEEDS_ADJUDICATION,
            "the page names 'Baymont by Wyndham Plainfield/ Indianapolis Arpt Area', "
            "which is the other row's name, and prints both properties' telephones. "
            "These two rows are very likely one hotel carried under its old and new "
            "brand names -- but brand plus address may propose a match and never "
            "decide one, so this is the founder's call.", ""),
        "towneplace suites": (
            NEEDS_ADJUDICATION,
            "the census key is a bare brand name with no city, holding "
            "'708 South Meridian Street', while the indtd page states "
            "'629 Russell Avenue'. An under-named row cannot settle which building it "
            "means.", ""),
    }
    phase2: List[Dict] = []
    for row in repair_rows:
        key = row["identity_key"]
        verdict, why, repaired = diagnoses[key]
        p1 = pass1_by_key.get(key, {})
        cen = census_by_key.get(promoted_key(key), {})
        phase2.append(OrderedDict((
            ("identity_key", key),
            ("census_url", (cen.get("official_url") or "")),
            ("requested_url", row.get("source_url") or ""),
            ("page_title", p1.get("title") or ""),
            ("mismatch_detail", p1.get("detail") or ""),
            ("census_address", cen.get("address") or ""),
            ("census_postal_code", cen.get("postal_code") or ""),
            ("census_phone", cen.get("phone") or ""),
            ("saved_policy_evidence", bool(_policy_text(
                row["paid_history"].get("prior_artifact") or ""))),
            ("verdict", verdict), ("why", why),
            ("repaired_url", repaired),
        )))

    # ---------------------------------------------------------------- phase 3
    never = [h for h in census["hotels"]
             if h["identity_key"] not in signed and h["identity_key"] not in attempted]
    with_url = [h for h in never if (h.get("official_url") or "").strip()]
    without_url = [h for h in never if not (h.get("official_url") or "").strip()]

    prior_urls: Dict[str, str] = {}
    if PRIOR_CENSUS.is_file():
        prior = json.loads(PRIOR_CENSUS.read_text(encoding="utf-8"))
        prior_urls = {h["identity_key"]: h["official_url"]
                      for h in prior.get("hotels", [])
                      if (h.get("official_url") or "").strip()}
    recovered: List[Dict] = []
    for hotel in without_url:
        for alias in [hotel["identity_key"]] + list(
                hotel.get("prior_census_identity_keys") or ()):
            if alias in prior_urls:
                recovered.append(OrderedDict((
                    ("identity_key", hotel["identity_key"]),
                    ("recovered_from_prior_census_key", alias),
                    ("official_url", prior_urls[alias]),
                    ("address", hotel.get("address") or ""),
                    ("postal_code", hotel.get("postal_code") or ""),
                )))
                break

    # ---------------------------------------------------------------- phase 5
    # Only rows whose route is established may enter a paid cohort.
    payable_seed: List[Dict] = []
    for hotel in with_url:
        payable_seed.append((hotel, hotel["official_url"], "never_attempted"))
    for rec in recovered:
        hotel = census_by_key[rec["identity_key"]]
        payable_seed.append((hotel, rec["official_url"], "url_recovered_zero_cost"))
    for entry in phase2:
        if entry["verdict"] == ROUTE_REPAIRED and entry["repaired_url"]:
            hotel = census_by_key.get(promoted_key(entry["identity_key"]))
            if hotel:
                payable_seed.append((hotel, entry["repaired_url"], "routing_repaired"))

    cohort: List[Dict] = []
    for hotel, url, basis in payable_seed:
        brand = CORPUS.brand_of(url) or ""
        route = REGISTRY.resolve(brand=brand, url=url,
                                 identity_key=hotel["identity_key"])
        cohort.append(OrderedDict((
            ("identity_key", hotel["identity_key"]),
            ("canonical_name", hotel.get("canonical_name") or ""),
            ("source_url", url), ("brand", brand),
            ("provider", route.provider), ("basis", basis),
            ("street", hotel.get("address") or ""),
            ("postal_code", hotel.get("postal_code") or ""),
            ("telephone", hotel.get("phone") or ""),
        )))

    material = {e["identity_key"]: {"reason": PAL.MATERIAL_ROUTING_REPAIR,
                                   "detail": e["why"]}
                for e in phase2 if e["verdict"] == ROUTE_REPAIRED}
    payable, suppressed_cohort = PAL.suppress(cohort, ledger,
                                              material_changes=material)

    return OrderedDict((
        ("schema", SCHEMA), ("market_id", MARKET), ("work_order", WORK_ORDER),
        ("nothing_was_fetched", True), ("usd_spent", 0.0), ("network_calls", 0),
        ("current", OrderedDict((
            ("census", census["count"]), ("promoted_pet_friendly", len(promoted)),
            ("verified_no_pets", len(no_pets)), ("founder_signed", len(signed)),
            ("unresolved", census["count"] - len(signed)),
        ))),
        ("phase_1_reusable_evidence", OrderedDict((
            ("audited", len(phase1)),
            ("by_classification", OrderedDict(sorted(
                Counter(r["classification"] for r in phase1).items()))),
            ("new_pet_friendly_recoverable", 0),
            ("new_no_pets_recoverable", sum(
                1 for r in phase1 if r["classification"] == NEEDS_REPARSE)),
            ("rows", phase1),
        ))),
        ("phase_2_routing_repair", OrderedDict((
            ("rows", len(phase2)),
            ("by_verdict", OrderedDict(sorted(
                Counter(r["verdict"] for r in phase2).items()))),
            ("repaired_zero_cost", sum(1 for r in phase2
                                       if r["verdict"] == ROUTE_REPAIRED)),
            ("carry_saved_policy_evidence", sum(
                1 for r in phase2 if r["saved_policy_evidence"])),
            ("detail", phase2),
        ))),
        ("phase_3_zero_cost_recovery", OrderedDict((
            ("never_attempted", len(never)),
            ("already_routable", len(with_url)),
            ("without_a_url", len(without_url)),
            ("urls_recovered_from_prior_census", len(recovered)),
            ("still_without_a_url", len(without_url) - len(recovered)),
            ("recoveries", recovered),
        ))),
        ("phase_5_payable", OrderedDict((
            ("cohort", len(cohort)), ("payable", len(payable)),
            ("suppressed_by_ledger", len(suppressed_cohort)),
            ("by_provider", OrderedDict(sorted(
                Counter(r["provider"] for r in payable).items()))),
            ("by_basis", OrderedDict(sorted(
                Counter(r["basis"] for r in payable).items()))),
            ("rows", payable),
        ))),
    ))


def cost_plan(audit: Dict) -> Dict:
    """The projection for the payable cohort. A projection, never an authorization.

    ``authorised_cap_usd`` is deliberately 0.0: this work order is forbidden to
    authorize spend, and passing a real ceiling here would look like one.
    """
    from scripts.pettripfinder.acquisition import cohort_cost_plan as CP
    from scripts.pettripfinder.acquisition.market_paid_acquisition import family_of

    ledger = _load("ptf_paid_attempt_ledger_001.json")
    prior = _load("indianapolis_in_market_acquisition_pass1_002.json")
    cohort = [{k: v for k, v in row.items() if k != "paid_history"}
              for row in audit["phase_5_payable"]["rows"]]
    for row in cohort:
        row["family"] = family_of(row["brand"])

    plan = CP.build({"cohort": cohort}, prior, authorised_cap_usd=0.0,
                    paid_ledger=ledger,
                    available_lanes=("brightdata_browser",
                                     "brightdata_web_unlocker", "firecrawl"))

    # What the cohort can actually be worth, at this market's own measured rates.
    merged = _load("indianapolis_in_acquisition_merged_promotion_003.json")
    attempted = len({r["identity_key"] for r in merged["results"]})
    promoted = audit["current"]["promoted_pet_friendly"]
    signed_no_pets = audit["current"]["verified_no_pets"]
    pf_rate = promoted / attempted if attempted else 0.0
    resolve_rate = (promoted + signed_no_pets) / attempted if attempted else 0.0
    payable = audit["phase_5_payable"]["payable"]
    needed = TARGET_PET_FRIENDLY - promoted

    return OrderedDict((
        ("schema", PLAN_SCHEMA), ("market_id", MARKET), ("work_order", WORK_ORDER),
        ("this_is_not_an_authorization", True),
        ("authorised_cap_usd_minor", 0),
        ("cohort_size", plan["cohort_size"]),
        ("cohort_by_provider", plan["cohort_by_provider"]),
        ("cohort_by_family", plan["cohort_by_family"]),
        ("dollar_billed_properties", plan["dollar_billed_properties"]),
        ("credit_billed_properties", plan["credit_billed_properties"]),
        ("measured_unit_usd_minor", plan["measured_unit_usd_minor"]),
        ("lanes", plan["lanes"]),
        ("expected_firecrawl_credits", plan["expected_firecrawl_credits"]),
        ("expected_brightdata_usd_minor", plan["expected_brightdata_usd_minor"]),
        ("projection", plan["projection"]),
        ("safe_cap_usd_minor", int(plan["projection"]["worst_case_usd_minor"]) + 15),
        ("safe_cap_why", "the worst case with a fallback attempt on every "
                         "dollar-billed property, rounded up; nothing is authorised here"),
        ("yield_projection", OrderedDict((
            ("basis", "this market's own pass-1/pass-2 record: %d identities attempted, "
                      "%d became promoted pet-friendly and %d became signed no-pets"
                      % (attempted, promoted, signed_no_pets)),
            ("observed_pet_friendly_rate", round(pf_rate, 4)),
            ("observed_resolution_rate", round(resolve_rate, 4)),
            ("payable_cohort", payable),
            ("expected_new_pet_friendly", int(round(payable * pf_rate))),
            ("expected_total_pet_friendly",
             promoted + int(round(payable * pf_rate))),
            ("target", TARGET_PET_FRIENDLY),
            ("still_needed_after_spending_the_whole_cohort",
             max(0, TARGET_PET_FRIENDLY - promoted - int(round(payable * pf_rate)))),
            ("payable_properties_required_to_reach_target_at_this_rate",
             int(round(needed / pf_rate)) if pf_rate else None),
            ("verdict",
             "REACHABLE" if promoted + int(round(payable * pf_rate)) >= TARGET_PET_FRIENDLY
             else "NOT_REACHABLE_FROM_THE_CURRENT_PAYABLE_POOL"),
        ))),
    ))


def founder_packet(audit: Dict) -> Dict:
    """Exception-only. Nothing here is auto-accepted, because nothing qualifies.

    Auto-acceptance requires a clean consensus row: identity passes, first-party
    publication-grade evidence exists, no duplicate, no fact loss, no correction.
    Phase 1 recovered no such row, so the packet is exceptions and nothing else.
    """
    exceptions: List[Dict] = []
    for row in audit["phase_1_reusable_evidence"]["rows"]:
        if row["classification"] != NEEDS_REPARSE:
            continue
        exceptions.append(OrderedDict((
            ("identity_key", row["identity_key"]),
            ("kind", "RETIRED_ROW_WITH_SURVIVING_EVIDENCE"),
            ("proposes", "VERIFIED_NO_PETS"),
            ("evidence", row["policy_block"]),
            ("artifact", row["artifact"]),
            ("why_it_is_an_exception",
             "PTF-INDIANAPOLIS-FOUNDER-PROMOTION-004 retired this exclusion for lack of "
             "fresh evidence, and the saved pass-1 artifact contradicts that: the page's "
             "own FAQ states 'No, pets are not allowed'. The block also carries a $100 "
             "non-refundable cleaning fee beside the refusal, which is why the run "
             "recorded SOURCE_CONTRADICTORY. Re-instating a row the founder retired is "
             "the founder's call, never the machine's."),
        )))
    for row in audit["phase_2_routing_repair"]["detail"]:
        if row["verdict"] in (ROUTE_REPAIRED, ROUTE_CORRECT_RULE):
            continue
        exceptions.append(OrderedDict((
            ("identity_key", row["identity_key"]),
            ("kind", "DUPLICATE_OR_IDENTITY_CONFLICT"
                     if row["verdict"] == NEEDS_ADJUDICATION
                     else "CENSUS_ADDRESS_DISPUTED"),
            ("proposes", "NO_CHANGE_WITHOUT_A_RULING"),
            ("evidence", row["mismatch_detail"]),
            ("artifact", ""),
            ("why_it_is_an_exception", row["why"]),
        )))
    return OrderedDict((
        ("schema", "ptf-founder-review-packet/1.0"), ("market_id", MARKET),
        ("work_order", WORK_ORDER), ("status", "EXCEPTIONS_ONLY"),
        ("nothing_is_published_by_this_file",
         "This packet proposes. It registers no market, signs no row and "
         "publishes nothing."),
        ("auto_accepted", 0),
        ("auto_accept_rule",
         "a row is auto-accepted only on identity pass + first-party "
         "publication-grade evidence + no duplicate + no guest-visible fact loss "
         "+ no correction required; no recovered row met it"),
        ("new_pet_friendly_proposed", 0),
        ("new_verified_no_pets_proposed",
         sum(1 for e in exceptions if e["proposes"] == "VERIFIED_NO_PETS")),
        ("exceptions", len(exceptions)),
        ("rows", exceptions),
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="")
    parser.add_argument("--plan-out", default="")
    parser.add_argument("--packet-out", default="")
    args = parser.parse_args(argv)
    result = build()
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    if args.plan_out:
        Path(args.plan_out).write_text(json.dumps(cost_plan(result), indent=2),
                                       encoding="utf-8")
    if args.packet_out:
        Path(args.packet_out).write_text(json.dumps(founder_packet(result), indent=2),
                                         encoding="utf-8")
    c = result["current"]
    print("current: census %d, pet-friendly %d, no-pets %d, unresolved %d"
          % (c["census"], c["promoted_pet_friendly"], c["verified_no_pets"],
             c["unresolved"]))
    for phase in ("phase_1_reusable_evidence", "phase_2_routing_repair",
                  "phase_3_zero_cost_recovery", "phase_5_payable"):
        print("\n%s" % phase)
        for k, v in result[phase].items():
            if k in ("rows", "detail", "recoveries"):
                continue
            print("   %-38s %s" % (k, v))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
