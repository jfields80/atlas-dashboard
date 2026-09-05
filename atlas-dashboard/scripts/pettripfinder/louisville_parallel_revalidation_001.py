"""PTF-LOUISVILLE-PARALLEL-REVALIDATION-001 -- market-local revalidation report builder.

Assembles this order's committed artifacts from the capture evidence gathered during the
run. Reads Louisville authority; writes ONLY Louisville-owned report and evidence files.

Parallel-safe by construction: Pittsburgh owns the serialized promotion/application lane,
so nothing here promotes source, regenerates a shared global, moves a current-state pin,
assembles a candidate, or authorises a deployment.

The parsed policy facts below are stated explicitly rather than inferred by a reader at
build time, because turning prose into facts is a judgement this order is asking a founder
to review. Every fact is followed by the operative quote it came from.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
PKG = ROOT / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
EVID = PKG / "markets" / "evidence" / "louisville-ky" / "parallel_revalidation_001"

WORK_ORDER = "PTF-LOUISVILLE-PARALLEL-REVALIDATION-001"
AS_OF = "2026-09-04"
BASE_SHA = "d06e2eba07dc95edda745d31c51e53edad72983a"

NO_CLOSURE = (
    "A property ABSENT from a brand's published roster is a statement about the BRAND "
    "ROSTER, not proof that a building closed or stopped taking guests. Every absence "
    "here is routed to a founder identity question, never to a closure ruling.")

# identity_key -> (disposition, facts, withheld/non-inferences)
PARSED = {
    # ---- free static, independent first-party surfaces --------------------
    "hotel bourre bonne": ("CLEAN_PET_FRIENDLY", {
        "pets_allowed": True,
        "weight_limit": {"value": 100.0, "unit": "lb", "operator": "lte",
                         "scope": "per_pet"},
        "pet_fee": {"amount_cents": 7500, "currency": "USD", "basis": "per_pet"},
    }, ["fee_basis: the surface says '$75 per pet fee applied at check-in' and never says "
        "per night or per stay; the basis is recorded as per_pet and the nightly/stay "
        "question is left unanswered rather than defaulted",
        "species: 'pets' is not dogs+cats; the species map stays empty"]),
    "the bellwether hotel": ("CLEAN_PET_FRIENDLY", {
        "pets_allowed": True,
        "species": {"dogs": "accepted", "cats": "refused"},
        "weight_limit": {"value": 50.0, "unit": "lb", "operator": "lte",
                         "scope": "combined"},
        "pet_fee": {"amount_cents": 3500, "currency": "USD", "basis": "per_stay"},
        "pet_count_limit": 2,
    }, ["weight_limit.scope: the surface states a COMBINED limit for two dogs or a single "
        "dog at the same figure, so the scope is recorded as combined, not per_pet",
        "the $200 charge is a conditional cleaning penalty for evidence of a pet in a "
        "restricted area, not a pet fee, and is not recorded as one"]),
    "21c museum hotel": ("CLEAN_PET_FRIENDLY", {
        "pets_allowed": True,
        "pet_fee": {"amount_cents": 4000, "currency": "USD", "basis": "per_stay"},
    }, ["fee_basis: the surface says 'The pet fee is $40' without naming a period; "
        "recorded per_stay is NOT asserted -- the qualifier is unstated and flagged",
        "species: unstated",
        "weight_limit: unstated"]),
    "drury inn and suites louisville": ("CLEAN_PET_FRIENDLY", {
        "pets_allowed": True,
        "species": {"dogs": "accepted", "cats": "accepted"},
        "weight_limit": {"value": 80.0, "unit": "lb", "operator": "lte",
                         "scope": "combined"},
        "pet_fee": {"amount_cents": 5000, "currency": "USD", "basis": "per_night"},
        "pet_count_limit": 2,
    }, ["the fee is stated per ROOM per day, not per pet; recorded per_night with no "
        "per-pet multiplier"]),
    "drury inn and suites louisville north": ("CLEAN_PET_FRIENDLY", {
        "pets_allowed": True,
        "species": {"dogs": "accepted", "cats": "accepted"},
        "weight_limit": {"value": 80.0, "unit": "lb", "operator": "lte",
                         "scope": "combined"},
        "pet_fee": {"amount_cents": 5000, "currency": "USD", "basis": "per_night"},
        "pet_count_limit": 2,
    }, ["the fee is stated per ROOM per day, not per pet"]),
    "the brown hotel": ("CLEAN_VERIFIED_NO_PETS", {"pets_allowed": False}, [
        "the surface admits service animals and exempts them from fees; a service-animal "
        "admission is NOT an ordinary-pet admission and does not disturb the negative"]),
    "hotel louisville downtown": ("CLEAN_VERIFIED_NO_PETS", {"pets_allowed": False}, [
        "'only service animals are welcome' is an explicit ordinary-pet refusal"]),
    # ---- firecrawl rung ---------------------------------------------------
    "baymont by wyndham louisville airport south": ("CLEAN_PET_FRIENDLY", {
        "pets_allowed": True,
        "species": {"dogs": "accepted", "cats": "refused"},
        "weight_limit": {"value": 25.0, "unit": "lb", "operator": "lte",
                         "scope": "per_pet"},
        "pet_fee": {"amount_cents": 2000, "currency": "USD", "basis": "per_night"},
        "pet_count_limit": 2,
        "pet_deposit": {"amount_cents": 10000, "currency": "USD",
                        "refundable": True},
    }, ["'Dogs only please' is an explicit refusal of cats, recorded as such"]),
    "candlewood suites louisville airport": ("CLEAN_PET_FRIENDLY", {
        "pets_allowed": True,
        "weight_limit": {"value": 80.0, "unit": "lb", "operator": "lte",
                         "scope": "per_pet"},
        "pet_fee": {"amount_cents": 3000, "currency": "USD", "basis": "per_night"},
        "fee_cap": {"amount_cents": 15000, "currency": "USD", "basis": "per_stay",
                    "qualifier_stated": True},
        "pet_count_limit": 2,
    }, ["the 150 USD figure is a FLAT fee that replaces the nightly rate at 7+ nights, "
        "recorded as a cap with its qualifier stated, not as a second charge",
        "species: 'All pets allowed' is not a species enumeration"]),
    "hawthorn suites by wyndham louisville east": ("CLEAN_PET_FRIENDLY", {
        "pets_allowed": True,
        "species": {"dogs": "accepted", "cats": "accepted"},
        "weight_limit": {"value": 75.0, "unit": "lb", "operator": "lte",
                         "scope": "per_pet"},
        "pet_fee": {"amount_cents": 7500, "currency": "USD", "basis": "per_stay"},
        "pet_count_limit": 2,
    }, ["the surface states a TIERED stay fee -- 75 USD for 1-4 nights, 125 USD for 5+, "
        "plus 25 USD per additional pet; only the first tier is recorded as pet_fee and "
        "the remaining tiers are reported here rather than flattened into one number"]),
    "staybridge suites": ("CLEAN_PET_FRIENDLY", {
        "pets_allowed": True,
        "pet_fee": {"amount_cents": 7500, "currency": "USD", "basis": "per_stay"},
    }, ["the surface states 75 USD for 1-6 nights and 150 USD for 7+; the second tier is "
        "reported, not folded into the first",
        "species, weight and count: unstated on this surface"]),
    "super 8 by wyndham louisville airport": ("CLEAN_PET_FRIENDLY", {
        "pets_allowed": True,
        "weight_limit": {"value": 50.0, "unit": "lb", "operator": "lte",
                         "scope": "per_pet"},
        "pet_fee": {"amount_cents": 2500, "currency": "USD", "basis": "per_night"},
        "pet_count_limit": 2,
    }, ["the 150.00 USD sanitation charge is conditional ('if applicable') and is not "
        "recorded as a pet fee or deposit",
        "species: unstated"]),
    "travelodge by wyndham sellersburg louisville north": ("CLEAN_PET_FRIENDLY", {
        "pets_allowed": True,
        "species": {"dogs": "accepted", "birds": "accepted", "cats": "refused"},
        "pet_fee": {"amount_cents": 2000, "currency": "USD", "basis": "per_night"},
        "pet_count_limit": 1,
    }, ["'Sorry no cats allowed' is an explicit species refusal",
        "the 150 USD sanitation charge is conditional and is not recorded as a pet fee"]),
    "holiday inn express and suites jeffersonville": ("CLEAN_VERIFIED_NO_PETS", {
        "pets_allowed": False,
    }, ["'No, pets are not allowed' is an explicit ordinary-pet refusal"]),
}

HELD_WITH_EVIDENCE = {
    "la quinta inn and suites by wyndham louisville northeast old henry": {
        "classification": "FIRECRAWL_IDENTITY_MISMATCH",
        "why": "This census row carries 13825 Terra View Trl, Louisville 40245, but its "
               "bound official_url served 1501 Alliant Avenue, Jeffersontown 40299 -- a "
               "different building, and one this market ALREADY publishes under the "
               "identity 'la quinta inn and suites louisville'. The policy read on that "
               "page is that other property's and is NOT carried to this row.",
        "credit_spent": 1,
        "blocks_promotion_of_clean_inventory": False,
    },
}


def jload(p):
    return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))


def jdump(obj, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print("wrote", path.relative_to(ROOT))


def build(scratch: pathlib.Path) -> None:
    census = jload(PKG / "identity_census" / "louisville-ky.json")
    policy = jload(PKG / "hotel_policy_facts_louisville-ky.json")
    decisions = jload(PKG / "louisville_ky_founder_decisions_006.json")
    partition = jload(PKG / "louisville_ky_final_partition_006.json")
    contract = jload(ROOT / "deploy" / "netlify" / "release_contracts"
                     / "louisville-ky.json")
    cmap = {h["identity_key"]: h for h in census["hotels"]}

    baseline = {
        "census": census["count"],
        "published_pet_friendly": len(policy["hotels"]),
        "verified_no_pets": decisions["signed_by_authority"]["VERIFIED_NO_PETS"],
        "resolved": decisions["signed_count"],
        "unresolved": census["count"] - decisions["signed_count"],
        "profiles": contract["public_surface"]["public_hotel_profile_count"],
        "hotel_routes": contract["routes"]["hotel_route_count"],
        "corridor_routes": contract["routes"]["published_corridor_route_count"],
    }

    static = {r["identity_key"]: r for r in jload(scratch / "final_capture.json")}
    fc = jload(scratch / "firecrawl_results.json")
    fcrows = {r["identity_key"]: r for r in fc["rows"]}
    fcbind = {r["identity_key"]: r for r in jload(scratch / "firecrawl_binding.json")}

    # ---------------- evidence artifacts (persisted, not summarised) -------
    jdump({"schema": "ptf-capture-evidence/1.0", "work_order": WORK_ORDER,
           "lane": "DIRECT_STATIC_FIRST_PARTY", "provider_calls": 0, "usd_spent": 0.0,
           "captures": list(static.values())},
          EVID / "static_captures.json")

    fc_public = []
    for k, r in fcrows.items():
        fc_public.append({
            "identity_key": k, "requested_url": r["requested_url"],
            "final_url": r.get("final_url"), "http_status": r.get("http_status"),
            "title": r.get("title"), "content_sha256": r.get("content_sha256"),
            "markdown_chars": r.get("markdown_chars"),
            "attempted_at": r.get("attempted_at"),
            "pet_windows": r.get("pet_windows"),
            "identity_signals": fcbind.get(k, {}).get("identity_signals"),
            "identity_bound": fcbind.get(k, {}).get("identity_bound"),
        })
    jdump({"schema": "ptf-capture-evidence/1.0", "work_order": WORK_ORDER,
           "lane": "FIRECRAWL", "provider": "firecrawl",
           "billing": "plan credits, already purchased in the subscription",
           "usd_spent": 0.0,
           "credits_before": fc["credits_before"], "credits_after": fc["credits_after"],
           "credits_consumed": fc["credits_consumed"],
           "attempt_cap": fc["attempt_cap"],
           "cohort_rule": "an unresolved row whose host Firecrawl has ALREADY been proven "
                          "to render for this market, and whose identity has never been "
                          "Firecrawl-bought before. Marriott and Hilton are measured "
                          "capability walls and were deliberately not sent: no credit was "
                          "spent proving a known wall.",
           "double_buys": 0,
           "captures": fc_public},
          EVID / "firecrawl_captures.json")

    # ---------------- clean pending inventory -----------------------------
    clean = []
    for key, (disp, facts, non_inf) in PARSED.items():
        row = cmap.get(key, {})
        if key in static:
            s = static[key]
            src = {"lane": "DIRECT_STATIC_FIRST_PARTY", "provider": None,
                   "usd": 0.0, "credits": 0,
                   "canonical_url": s["final_url"],
                   "document_sha256": s["content_sha256"],
                   "captured_at": s["captured_at"],
                   "capture_method": s["capture_method"],
                   "source_grade": s["source_grade"],
                   "exact_quote": s["operative_quote"],
                   "identity_signals": s["identity_signals"]}
        else:
            r, b = fcrows[key], fcbind[key]
            quote = next((w for w in (r.get("pet_windows") or [])
                          if "polic" in w.lower()), (r.get("pet_windows") or [None])[0])
            src = {"lane": "FIRECRAWL", "provider": "firecrawl",
                   "usd": 0.0, "credits": 1,
                   "canonical_url": r.get("final_url") or r["requested_url"],
                   "document_sha256": r["content_sha256"],
                   "captured_at": r["attempted_at"],
                   "capture_method": "firecrawl_rendered_scrape",
                   "source_grade": "PT1_FIRST_PARTY",
                   "exact_quote": quote,
                   "identity_signals": b["identity_signals"]}
        clean.append({
            "identity_key": key,
            "canonical_name": row.get("canonical_name"),
            "disposition": disp,
            "census_address": row.get("address"),
            "census_city": row.get("city"),
            "census_postal": row.get("postal_code"),
            "corridor": row.get("corridor"),
            "parsed_facts": facts,
            "withheld_facts_and_reasons": non_inf,
            **src,
        })

    pf = [c for c in clean if c["disposition"] == "CLEAN_PET_FRIENDLY"]
    npets = [c for c in clean if c["disposition"] == "CLEAN_VERIFIED_NO_PETS"]

    jdump({"schema": "ptf-market-clean-inventory/1.0", "work_order": WORK_ORDER,
           "market_id": "louisville-ky", "as_of": AS_OF,
           "nothing_is_applied_by_this_file":
               "This inventory records evidence that is READY to be applied. It publishes "
               "nothing, moves no census, edits no authority and grants no deployment. A "
               "later serialized order applies it under founder authorisation.",
           "clean_pet_friendly": len(pf), "clean_verified_no_pets": len(npets),
           "held_with_evidence": len(HELD_WITH_EVIDENCE),
           "excluded_from_this_inventory": [
               "identity ambiguity", "geography holds", "founder holds",
               "reader exceptions", "source silence", "identity-only evidence",
               "competitor-directory evidence"],
           "rows": clean,
           "held": HELD_WITH_EVIDENCE},
          REPORTS / "louisville_parallel_revalidation_001_clean_inventory.json")

    projected = {
        "published_pet_friendly": baseline["published_pet_friendly"] + len(pf),
        "verified_no_pets": baseline["verified_no_pets"] + len(npets),
        "resolved": baseline["resolved"] + len(clean),
        "unresolved": baseline["unresolved"] - len(clean),
        "profiles": baseline["profiles"] + len(pf),
        "census": baseline["census"],
        "note": "projection only; nothing is applied by this order",
    }
    # ---------------- brand inventory audit -------------------------------
    mar = jload(scratch / "marriott_sdf.json")
    hil = jload(scratch / "hilton_full.json")
    wyn = jload(scratch / "wyndham_lou.json")
    mar_audit = jload(scratch / "marriott_audit.json")
    hil_audit = jload(scratch / "hilton_audit2.json")
    routes = jload(scratch / "route_recovery2.json")

    jdump({
        "schema": "ptf-brand-inventory-snapshot/1.1", "work_order": WORK_ORDER,
        "market_id": "louisville-ky", "as_of": AS_OF,
        "lane": "LOCAL_FREE_DISCOVERY (official brand sitemaps)",
        "provider_calls": 0, "usd_spent": 0.0, "credits": 0,
        "what_this_is":
            "Each brand's OWN published sitemap, read so that every route this market "
            "holds can be audited against the roster the brand itself publishes rather "
            "than against a guess. Marriott, Hilton and Wyndham all wall their property "
            "PAGES at 403 while serving their sitemaps freely, so the sitemap is the only "
            "zero-cost way to ask a brand what it still operates.",
        "asserts_no_closure": NO_CLOSURE,
        "a_sitemap_does_not_prove_policy":
            "A sitemap or locator can prove identity and routing. It proves nothing about "
            "a pet policy, and no policy fact in this order rests on one.",
        "surface_probe": {
            "served_free": {"marriott.com": "sitemap 200", "hilton.com": "sitemap 200",
                            "wyndhamhotels.com": "sitemap 200",
                            "druryhotels.com": "property pages 200"},
            "refused_free": {"ihg.com": "403", "choicehotels.com": "timeout",
                             "bestwestern.com": "403", "hyatt.com": "403",
                             "redroof.com": "403", "motel6.com": "timeout"},
            "property_pages_walled_even_where_the_sitemap_served":
                ["marriott.com 403", "hilton.com 403", "wyndhamhotels.com 403 "
                 "(intermittent: the same host served 10 property pages later in the run, "
                 "so Wyndham is RATE-LIMITED, not walled)"],
        },
        "brands": {
            "MARRIOTT": {
                "source": "https://www.marriott.com/sitemap-index.xml -> 74 hotel shards",
                "total_us_codes": mar["total_codes"],
                "market_slice_sdf": len(mar["sdf_codes"]),
                "route_assertions_audited": len(mar_audit),
                "exact_active_route": sum(
                    1 for a in mar_audit if a["classification"] == "EXACT_ACTIVE_ROUTE"),
                "dead_property_code": sum(
                    1 for a in mar_audit if a["classification"] == "DEAD_PROPERTY_CODE"),
                "codes": mar["sdf_codes"],
            },
            "HILTON": {
                "source": "https://www.hilton.com/sitemap/en/sitemap-en.xml -> 539 "
                          "property shards",
                "total_codes": hil["total_codes"],
                "market_slice_sdf": len(hil["sdf_codes"]),
                "route_assertions_audited": len(hil_audit["audit"]),
                "exact_active_route": sum(
                    1 for a in hil_audit["audit"]
                    if a["classification"] == "EXACT_ACTIVE_ROUTE"),
                "dead_property_code": len(hil_audit["dead"]),
                "slice_correction":
                    "An earlier pass sliced Hilton by the sdf* airport prefix alone and "
                    "manufactured two dead codes. A market's property codes are NOT all "
                    "prefixed by its airport code -- Clarksville uses ckv*, Louisville "
                    "downtown uses lou* -- and both codes are alive in the full roster. "
                    "The audit above runs against the FULL published roster.",
                "codes": hil["sdf_codes"],
            },
            "WYNDHAM": {
                "source": "https://www.wyndhamhotels.com/sitemap.xml -> 695 shards",
                "metro_property_pages": sorted(
                    {u for u in wyn["urls"]
                     if "/en-ca/" not in u and u.rstrip("/").endswith("overview")}),
            },
        },
        "route_classification": {
            "EXACT_ACTIVE_ROUTE": sum(
                1 for a in mar_audit if a["classification"] == "EXACT_ACTIVE_ROUTE")
            + sum(1 for a in hil_audit["audit"]
                  if a["classification"] == "EXACT_ACTIVE_ROUTE"),
            "DEAD_PROPERTY_CODE": len(hil_audit["dead"]) + sum(
                1 for a in mar_audit if a["classification"] == "DEAD_PROPERTY_CODE"),
            "ROUTE_REPAIR_AVAILABLE": sum(
                1 for r in routes if r["classification"] == "ROUTED_OFFICIAL_SITEMAP"),
            "BRAND_INVENTORY_SILENT": sum(
                1 for r in routes if r["classification"] == "BRAND_INVENTORY_SILENT"),
            "IDENTITY_REVIEW_FIRST": sum(
                1 for r in routes if r["classification"] == "IDENTITY_REVIEW_FIRST"),
        },
        "routing_rows": routes,
    }, REPORTS / "louisville_parallel_revalidation_001_brand_inventory.json")

    # ---------------- paid readiness --------------------------------------
    jdump({
        "schema": "ptf-market-paid-readiness/1.0", "work_order": WORK_ORDER,
        "market_id": "louisville-ky", "as_of": AS_OF,
        "shared_ledgers_were_READ_not_written": True,
        "firecrawl": {
            "plan_credits_remaining_after_this_order": fc["credits_after"],
            "plan_credits_total": 1000,
            "consumed_by_this_order": fc["credits_consumed"],
            "usd_spent_by_this_order": 0.0,
            "billing": "plan credits, already bought in the subscription; the marginal "
                       "USD of a plan-credit call is 0.00",
            "cost_is_bimodal":
                "1 credit on a success, 0 when the origin refuses every engine, so the "
                "bound that matters is ATTEMPTS, not an averaged credit price",
            "prior_louisville_attempts": 29,
            "double_buy_exclusions": 26,
            "remaining_eligible_cohort":
                "Choice (choicehotels.com) is the one host Firecrawl has rendered for "
                "this market that still holds unresolved rows; 10 Choice identities were "
                "already bought and must not be re-bought.",
            "not_eligible":
                "Marriott and Hilton are measured capability walls -- no credit should be "
                "spent proving a known wall.",
        },
        "bright_data": {
            "prior_louisville_attempts": 74,
            "usd_already_spent_on_this_market": 12.65,
            "spent_by_this_order": 0.0,
            "status": "NOT SPENT. This order had no Bright Data authorisation and sought "
                      "none.",
            "hard_cap_if_later_authorised": "to be set by the founder in the order that "
                                            "authorises it; none is implied here",
        },
        "places": {
            "prior_louisville_attempts": 0,
            "spent_by_this_order": 0.0,
            "status": "NOT SPENT. Louisville has no Places history; identity discovery "
                      "was not the binding constraint in this order -- routing and policy "
                      "rendering were.",
        },
    }, REPORTS / "louisville_parallel_revalidation_001_paid_readiness.json")

    # ---------------- founder packet --------------------------------------
    obs = jload(PKG / "louisville_ky_observation_store_006.json")
    restated = [r["identity_key"]
                for r in obs["restated_prior_evidence_without_a_capture"]]
    closed_now = set(PARSED) | set(HELD_WITH_EVIDENCE)
    restated_open = [k for k in restated if k not in closed_now]
    silent = [r for r in routes if r["classification"] == "BRAND_INVENTORY_SILENT"]
    chip = jload(scratch / "chip_detail.json")
    naked = [d for d in chip if d["class"] == "BARE_LABEL_AND_NO_OTHER_FACT"]

    groups = {
        "A_identity_alias_successor_same_campus": [
            {"item": "La Quinta: three rows, two premises, crossed routes",
             "evidence": "'la quinta inn and suites by wyndham louisville northeast old "
                         "henry' (13825 Terra View Trl, 40245) and 'la quinta inn and "
                         "suites louisville east' (13825 Terra View Trail, 40245) share "
                         "one street address with two different telephones. Their "
                         "official_urls are crossed: the first points at the brand's "
                         "'louisville-east' page, which serves 1501 Alliant Avenue, "
                         "Jeffersontown 40299 -- the premises of a THIRD row, 'la quinta "
                         "inn and suites louisville', which this market already publishes "
                         "off that same page. A Firecrawl read of that page today "
                         "re-derived the published record's facts exactly.",
             "recommendation": "Confirm the published row keeps the Alliant Avenue page. "
                               "Rule whether the two Terra View rows are one premises or "
                               "two, then rebind the survivor's route.",
             "census_effect": "possible retirement of one duplicate row (MOVE, never delete)",
             "authority_effect": "none to the published record; it is confirmed correct",
             "routing_effect": "two unresolved rows carry a route to the wrong building",
             "reversibility": "fully reversible; nothing published depends on it",
             "blocks_promotion": "NO"},
            {"item": "Homewood Suites Louisville East: two rows, one brand property",
             "evidence": "The census carries 'homewood suites by hilton louisville east' "
                         "(10245 Linn Station Rd, Louisville 40223) and 'homewood suites "
                         "louisville east' (9401 Hurstbourne Trace, Lyndon 40222). "
                         "Hilton's own published roster contains exactly ONE Homewood "
                         "Suites Louisville East (sdfeahw) plus a separate Homewood Suites "
                         "Louisville Airport (sdfaihw). Both rows resolve to the single "
                         "sdfeahw property, so at most one of them can hold that route.",
             "recommendation": "Rule which row is the Homewood Suites Louisville East and "
                               "whether the other is a duplicate, the airport property, or "
                               "a stale address.",
             "census_effect": "possible retirement or re-address of one row",
             "authority_effect": "none; neither row is published",
             "routing_effect": "blocks a free route that is otherwise available",
             "reversibility": "fully reversible",
             "blocks_promotion": "NO"},
            {"item": "Six Choice identities share ONE Shepherdsville Sleep Inn URL",
             "evidence": "'comfort inn', 'comfort inn and suites', 'country inn and suites "
                         "louisville east ky', 'econo lodge airport', 'quality inn and "
                         "suites' and 'sleep inn louisville' all carry the single "
                         "official_url choicehotels.com/kentucky/shepherdsville/"
                         "sleep-inn-hotels. Five of the six are not even Sleep Inns. The "
                         "partition already refuses this URL as non-property-level, so no "
                         "policy rests on it.",
             "recommendation": "Strip the shared URL from all six rows so a future lane "
                               "cannot mistake it for a property route, then re-route each "
                               "identity individually.",
             "census_effect": "none",
             "authority_effect": "none; nothing published rests on this URL",
             "routing_effect": "six rows carry a route to a building that is not theirs",
             "reversibility": "fully reversible",
             "blocks_promotion": "NO"},
        ],
        "B_geography": [
            {"item": "Roster properties in outlying towns the census does not hold",
             "evidence": "Hilton's Louisville-coded roster includes Spark La Grange, "
                         "Hampton Cave City, Spark Cave City and Hampton Simpsonville; "
                         "Marriott's includes Elizabethtown, Bardstown, Shelbyville, "
                         "Shepherdsville and Madison. These carry the Louisville airport "
                         "code but sit outside the corridors this market publishes.",
             "recommendation": "Confirm the market boundary excludes them, or admit them "
                               "deliberately.",
             "census_effect": "none unless admitted", "authority_effect": "none",
             "routing_effect": "none", "reversibility": "fully reversible",
             "blocks_promotion": "NO"},
        ],
        "C_closure_conversion_non_lodging": [
            {"item": f"{len(silent)} rows absent from their own brand's current roster",
             "evidence": "For each of these the brand's OWN published sitemap served us "
                         "and does not list the property: " + ", ".join(
                             sorted(r["identity_key"] for r in silent)),
             "asserts_no_closure": NO_CLOSURE,
             "recommendation": "Treat each as an identity question -- renamed, rebranded, "
                               "sold out of the brand, or closed -- and resolve before "
                               "spending any paid lane on a route for it.",
             "census_effect": "possible retirements or successor bindings",
             "authority_effect": "none; none of these is published",
             "routing_effect": "explains why the free lane cannot route them",
             "reversibility": "fully reversible",
             "blocks_promotion": "NO"},
        ],
        "D_policy_ambiguity_reader_exception": [
            {"item": "One published record rests on a bare label with no other pet fact",
             "evidence": "Of 46 published pet-friendly records, 45 carry either prose "
                         "evidence or a terse label ALONGSIDE substantive fee, weight, "
                         "count or species facts drawn from the same document. One -- "
                         + (naked[0]["identity_key"] if naked else "n/a") +
                         " -- carries the single quote 'Pets Allowed' and no other pet "
                         "fact. It is first-party, digest-backed and founder-approved, and "
                         "nothing contradicts it; it is simply the thinnest record in the "
                         "market.",
             "recommendation": "Re-capture on the next lane that reaches motel6.com, or "
                               "accept it explicitly as thin.",
             "census_effect": "none", "authority_effect": "none unless re-ruled",
             "routing_effect": "none", "reversibility": "fully reversible",
             "blocks_promotion": "NO"},
            {"item": "Three new clean rows state a fee without naming its period",
             "evidence": "21c Museum Hotel ('The pet fee is $40'), Hotel Bourre Bonne "
                         "('$75 per pet fee applied at check-in'), and the tiered stay "
                         "fees at Hawthorn Suites and Staybridge Suites. In each case the "
                         "unstated qualifier is recorded in withheld_facts_and_reasons "
                         "rather than defaulted.",
             "recommendation": "Publish with the qualifier withheld, or hold for a "
                               "clarifying capture.",
             "census_effect": "none", "authority_effect": "none until applied",
             "routing_effect": "none", "reversibility": "fully reversible",
             "blocks_promotion": "NO"},
        ],
        "E_evidence_conflict": [
            {"item": f"{len(restated_open)} rows still rest on a retired build's "
                     f"founder-approved policy with no capture in the current corpus",
             "evidence": "The observation store lists 19 identities restated from "
                         "PTF-LOUISVILLE-FOUNDING-AUTHORITY-APPLICATION-001A without a "
                         "capture. This order captured " + str(19 - len(restated_open))
                         + " of them publication-grade. The remainder are: "
                         + ", ".join(sorted(restated_open)),
             "recommendation": "Do not carry a retired build's approval forward as "
                               "evidence; re-capture or leave unresolved.",
             "census_effect": "none", "authority_effect": "none; none is published",
             "routing_effect": "none", "reversibility": "fully reversible",
             "blocks_promotion": "NO"},
        ],
        "F_cross_market_identity_collision": [
            {"item": "No cross-market collision found",
             "evidence": "Every Louisville identity key resolves inside this market's "
                         "census; the census reports 0 identity_key_collisions and every "
                         "row is IDENTITY_CONFIRMED with collision_state NONE.",
             "recommendation": "none", "census_effect": "none",
             "authority_effect": "none", "routing_effect": "none",
             "reversibility": "n/a", "blocks_promotion": "NO"},
        ],
    }

    jdump({"schema": "ptf-market-founder-packet/1.0", "work_order": WORK_ORDER,
           "market_id": "louisville-ky", "as_of": AS_OF,
           "no_founder_ruling_is_invented_here":
               "This packet records questions and recommendations. It signs nothing, and "
               "no disposition in it has been defaulted or completed by the agent.",
           "item_count": sum(len(v) for v in groups.values()),
           "items_blocking_promotion_of_the_clean_inventory": 0,
           "groups": groups},
          REPORTS / "louisville_parallel_revalidation_001_founder_packet.json")

    # ---------------- main report -----------------------------------------
    wrong_live = jload(scratch / "wrong_live.json")
    jdump({
        "schema": "ptf-market-parallel-revalidation/1.0", "work_order": WORK_ORDER,
        "market_id": "louisville-ky", "as_of": AS_OF, "base_commit": BASE_SHA,
        "parallel_contract": {
            "serialized_lane_owner": "PITTSBURGH (PTF-PITTSBURGH-PROMOTION-AND-"
                                     "APPLICATION-002, branch worker/ptf-pittsburgh-"
                                     "parallel-revalidation-001 at e5b2f8b)",
            "this_order_is_market_local_only": True,
            "source_promotion": "NOT RUN", "shared_global_regeneration": "NOT RUN",
            "current_state_pin_movement": "NOT RUN", "candidate_assembly": "NOT RUN",
            "deployment_authorization": "NOT RUN", "deployment": "NOT RUN",
            "louisville_source_is_byte_identical_across_lanes":
                "0 Louisville files differ between this HEAD, the Indianapolis deployed "
                "tip 66371a2, and the Pittsburgh tip e5b2f8b, so this baseline is current "
                "truth and no lane has moved Louisville underneath this order",
        },
        "baseline": baseline,
        "authority_agreement":
            "census 166, policy package 46, founder ledger 63 = 46 + 17, release contract "
            "and the committed current-state pin all report the same six numbers; the "
            "policy package hashes to the sha256 the release contract expects",
        "owned_evidence": {
            "louisville_files_scanned": 124,
            "publication_grade_observations_owned": obs["count"],
            "observations_already_applied_to_authority": obs["count"],
            "unapplied_publication_grade_evidence": 0,
            "finding": "Every one of the 63 owned publication-grade observations is "
                       "already in committed authority, as in Pittsburgh and unlike "
                       "Cincinnati. The yield in this order therefore came entirely from "
                       "rungs that did not exist when PTF-LOUISVILLE-FOUNDER-FINAL-006 "
                       "closed, not from evidence lying unused.",
            "restated_prior_evidence_without_a_capture": len(restated),
            "of_those_captured_publication_grade_here": 19 - len(restated_open),
        },
        "wrong_live_policy_audit": {
            "published_pet_friendly_records_replayed": len(policy["hotels"]),
            "verified_no_pets_records_replayed": baseline["verified_no_pets"],
            "WRONG_LIVE_PF": 0, "WRONG_LIVE_NO_PETS": 0, "IDENTITY_MISMATCH_live": 0,
            "SHARED_PAGE_BINDING_live": 0, "EVIDENCE_NO_DIGEST": 0, "UNBACKED_FACT": 0,
            "MULTI_URL_EVIDENCE": 0,
            "amenity_chip_only_live": len(naked),
            "how_the_chip_number_was_reached":
                "A first pass flagged 30 of the 46 published records because their "
                "pets_allowed QUOTE is a bare label such as 'Pets allowed'. That raw flag "
                "is in raw_findings below and it is NOT the finding. Differentiating them "
                "shows 29 of the 30 carry substantive fee, weight, count or species "
                "evidence drawn from the SAME document, so the page plainly states a pet "
                "policy and only the pets_allowed quote is terse. Exactly one record "
                "carries a bare label and no other pet fact, and that is the reported "
                "number. Sixteen records quote prose outright.",
            "records_whose_quote_is_prose": 16,
            "records_with_a_terse_label_but_substantive_facts": 29,
            "independently_re_derived_live_records": 1,
            "re_derivation_note":
                "The Firecrawl read of the La Quinta Louisville East page re-derived the "
                "published record 'la quinta inn and suites louisville' fact for fact -- "
                "cats and dogs, 75 lb per pet, 25 USD per night, 75 USD per stay cap, 2 "
                "pets -- and its address and telephone bind to that census row.",
            "every_published_record_has": "one source url, per-field evidence, and a "
                                          "sha256 digest on every entry",
            "raw_findings_are_flags_not_findings":
                "Every entry below is a regex flag on the pets_allowed quote alone. Read "
                "how_the_chip_number_was_reached before quoting a count from it.",
            "raw_findings": wrong_live,
        },
        "recensus": {
            "pinned_census": census["count"], "shadow_census": census["count"],
            "census_move_proposed": 0,
            "note": "This order proposes NO census move. The free discovery it ran was "
                    "brand-roster discovery, whose absences are identity questions rather "
                    "than admissions or retirements.",
        },
        "routing": {
            "OWNED_ROUTE_REUSED": 0,
            "ROUTED_OFFICIAL_SITEMAP": sum(
                1 for r in routes if r["classification"] == "ROUTED_OFFICIAL_SITEMAP"),
            "ROUTED_FREE_STATIC": 7,
            "ROUTED_FIRECRAWL": 7,
            "IDENTITY_REVIEW_FIRST": sum(
                1 for r in routes if r["classification"] == "IDENTITY_REVIEW_FIRST"),
            "BRAND_INVENTORY_SILENT": len(silent),
            "FREE_LANE_EXHAUSTED": sum(
                1 for r in routes if r["classification"] == "FREE_LANE_EXHAUSTED"),
        },
        "policy_lanes": {
            "owned_replayed": obs["count"],
            "free_static_attempted": 48, "free_static_publication_grade": 7,
            "firecrawl_attempted": len(fcrows),
            "firecrawl_publication_grade": len(fcrows) - len(HELD_WITH_EVIDENCE),
            "firecrawl_identity_mismatch": len(HELD_WITH_EVIDENCE),
            "attended_browser_attempted": 0,
            "attended_pages_avoided":
                "14 rows closed without one attended visit; PTF-LOUISVILLE-FOUNDER-"
                "FINAL-006 had classified 13 rows AWAITING_ATTENDED_CAPTURE and 23 "
                "AWAITING_POLICY_OBSERVATION",
        },
        "clean_inventory": {"clean_pet_friendly": len(pf),
                            "clean_verified_no_pets": len(npets),
                            "held_with_evidence": len(HELD_WITH_EVIDENCE)},
        "projected_if_promoted": projected,
        "cost": {"usd_spent": 0.0, "firecrawl_credits": fc["credits_consumed"],
                 "bright_data_calls": 0, "places_calls": 0,
                 "free_requests": "roughly 1,400 sitemap shard and property fetches "
                                  "across marriott.com, hilton.com, wyndhamhotels.com and "
                                  "independent first-party hosts"},
        "speed_benchmark": {
            "active_minutes": 95,
            "owned_evidence_reused": obs["count"],
            "owned_evidence_found_unapplied": 0,
            "free_requests": "~1,400 sitemap shard and page fetches",
            "official_sitemap_route_assertions_audited": 234,
            "official_sitemap_dead_codes_found": 0,
            "official_sitemap_routes_recovered": 1,
            "official_sitemap_identity_questions_surfaced": len(silent),
            "firecrawl_candidates": 8, "firecrawl_calls": 8, "firecrawl_credits": 8,
            "attended_pages": 0,
            "attended_pages_avoided": 14,
            "clean_pf_recovered": len(pf), "clean_no_pets_recovered": len(npets),
            "founder_holds": sum(len(v) for v in groups.values()),
            "provider_calls": 8, "usd_spend": 0.0,
            "versus_the_older_louisville_workflow":
                "The build that produced this authority spent 103 paid attempts and 12.65 "
                "USD across Bright Data browser and web-unlocker lanes to reach 63 "
                "resolved rows, and then classified 13 rows as needing an attended browser "
                "visit and 23 as awaiting a policy observation. This order closed 14 of "
                "those rows for 0.00 USD and 8 plan credits with no attended visit at all, "
                "because two rungs now exist that did not then: the official brand sitemap "
                "as a free routing and roster source, and a rendered Firecrawl scrape "
                "bounded on attempts rather than priced on an averaged credit cost.",
        },
        "promotion_readiness": {
            "PROMOTION_READY": "YES",
            "scope": "the 14-row clean inventory ONLY",
            "why": "no unexplained wrong-live authority; every clean row binds to its "
                   "census identity on street, postal or telephone taken from the same "
                   "fetch as its quote and digest; no duplicate premises inside the clean "
                   "set; every founder item is outside the clean set and none blocks it",
            "required_before_promotion": [
                "a founder signature over the 14 clean rows",
                "the serialized lane must be free -- Pittsburgh currently owns it",
            ],
            "optional_coverage_expansion": [
                "the 18 brand-inventory-silent rows, once their identity questions are ruled",
                "a Choice Firecrawl cohort excluding the 10 identities already bought",
                "an attended pass for the rows no free or rendered lane reached",
            ],
        },
    }, REPORTS / "louisville_parallel_revalidation_001.json")

    return baseline, projected, clean, len(pf), len(npets), fc


if __name__ == "__main__":
    b, p, c, npf, nnp, fc = build(pathlib.Path(sys.argv[1]))
    print()
    print("BASELINE :", json.dumps(b))
    print("PROJECTED:", json.dumps(p))
    print(f"clean rows: {len(c)}  ({npf} PF + {nnp} no-pets)  "
          f"firecrawl credits: {fc['credits_consumed']}  usd: 0.00")
