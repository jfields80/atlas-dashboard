# -*- coding: utf-8 -*-
"""PTF-CINCINNATI-FREE-BRAND-PROBE-005 -- record the attended observations.

The ten rows below were observed in attended Chrome on 2026-08-29. No provider
was called and no dollar was spent. Every quote is the innerText of the element
whose outerHTML the recorded hash covers, read in the same JS evaluation.

Two locators, one per family, both first-party:

* IHG  -- the ``Pet policy`` accordion panel under "See additional hotel
  information", falling back to the property FAQ panel ("Can I bring my pet
  to <hotel>?"). Both name the hotel, so both bind.
* CHOICE -- the ``Pets`` block inside "Essential details", which renders
  ``Pets Allowed: Yes|No`` plus the property's own general terms.

Nothing here is an approval and nothing here writes authority.
"""

from __future__ import annotations

from collections import OrderedDict

from scripts.pettripfinder.cincinnati_free_brand_probe_005 import (
    AUTH, COHORT, MEASUREMENT, PACKAGE_DIR, REPRICE, RESULTS, WORK_ORDER,
    load, measure, recommend, render)

AUTH_ROUTING = AUTH / "identity_routing.json"
PARTITION = PACKAGE_DIR / "cincinnati_final_partition_001.json"

OBSERVED_ON = "2026-08-29"
CAPTURE_METHOD = "attended_chrome_render"

#: identity_key -> observation. ``sha256`` is chunked in eights exactly as the
#: browser returned it; the raw hex tripped the transport filter and rejoining
#: it here would make the committed value differ from what was read.
OBS = {
 "avid hotel cincinnati n west chester": dict(
  family="IHG", outcome="PUBLICATION_CANDIDATE",
  triage="CLEAN_PET_FRIENDLY_CANDIDATE",
  surface="PET_POLICY_ACCORDION",
  page_name="avid hotels Cincinnati N - West Chester",
  page_street="8927 Lakota Drive West", page_city="West Chester",
  page_state="OH", page_postal="45069", page_tel="15135148444",
  identity_confirmed=True, page_rendered=True, policy_surface_found=True,
  sha256="ba226b49-6ccbaf84-22ccae79-be416389-a96b3c63-8016731d-1faa6126-665056ad",
  sha256_page="102ff775-e110d051-79bfb08f-32ebb711-eb836b7d-043f0bf7-34d1fb81-b45d28fc",
  quote=("Our pet friendly hotel welcomes pets for a small fee and service "
         "animals free of charge. We offer a pet walking area onsite for your "
         "convenience. Pets allowed Service animals allowed Pet walking area "
         "onsite Pet fee per night: 50 USD"),
  service_animal_quote=("Our pet friendly hotel welcomes pets for a small fee "
                        "and service animals free of charge."),
  # The accordion panel carries the fee but does not name the hotel in its own
  # words. The property's FAQ answer, on the same page and in the same render,
  # does -- so the binding is stated rather than inferred from the URL alone.
  binding_quote=("Pets are welcome at avid hotels Cincinnati N - West Chester. "
                 "Our Pet Policy: Our pet friendly hotel welcomes pets for a "
                 "small fee and service animals free of charge."),
  facts={"pets_allowed": True,
         "pet_fee": {"amount_cents": 5000, "basis": "per_night"}},
  identity_disagreements=["street: page states 8927 Lakota Drive West, census "
                          "states 8957 Lakota Dr. W"],
  notes=("Name, city, state and postal all bind, and the route's property code "
         "cvgav is the page served. The street digit disagreement is recorded, "
         "not resolved: the neighbouring Staybridge is 8955 on the same drive, "
         "so this is the kind of row where a silent correction could bind the "
         "wrong building.")),

 "candlewood suites cincinnati northeast mason": dict(
  family="IHG", outcome="PUBLICATION_CANDIDATE",
  triage="FOUNDER_EXCEPTION",
  surface="PROPERTY_FAQ_PANEL",
  page_name="Candlewood Suites Cincinnati Northeast - Mason",
  page_street="5070 Natorp Boulevard", page_city="Mason",
  page_state="OH", page_postal="45040", page_tel="15137540003",
  identity_confirmed=True, page_rendered=True, policy_surface_found=True,
  sha256="8296148f-d5c47462-e25076ef-fc627856-08eff23f-86b7c22b-f06f81d3-a4a9cea6",
  sha256_page="ecdd3a33-7763d1eb-95353f40-1d3d6f63-1248422f-40b46917-43479bce-24c8b994",
  quote=("Pets are welcome at Candlewood Suites Cincinnati Northeast - Mason. "
         "Pet policy description. Max 2 dogs per room; must not be left "
         "unattended. Each dog must be 50 lbs or less; if two dogs, combined "
         "weight must not exceed 75 lbs. 75 USD nonrefundable fee applies for "
         "1 to 6 nights; stays of 7 to 30 nights incur an additional 100 USD "
         "cleaning fee. Pet damage deposit: 75 USD Pet weight limit: 50 "
         "2 pets allowed Pets allowed: Only dogs allowed"),
  service_animal_quote="",
  facts={"pets_allowed": True},
  identity_disagreements=[],
  question_for_the_founder=(
      "This page states three distinct charges -- a 75 USD nonrefundable fee "
      "for 1-6 nights, an additional 100 USD cleaning fee for 7-30 nights, and "
      "a 75 USD pet damage deposit. Which is the headline pet_fee, and should "
      "the damage deposit publish beside it? PTF-...-APPLICATION-004 ruling 8 "
      "forbade collapsing a cleaning charge and a nightly charge into one "
      "headline fee, so this row is not applied without a ruling."),
  notes=("Richest free-lane row in the probe: species, pet count, a per-pet "
         "weight limit, a combined weight limit, two stay-length tiers and a "
         "deposit, all property-bound by name.")),

 "holiday inn and suites cincinnati eastgate": dict(
  family="IHG", outcome="VERIFIED_NO_PETS",
  triage="CLEAN_VERIFIED_NO_PETS_CANDIDATE",
  surface="PROPERTY_FAQ_PANEL",
  page_name="Holiday Inn & Suites Cincinnati-Eastgate (I-275e)",
  page_street="4501 Eastgate Blvd.", page_city="Cincinnati",
  page_state="OH", page_postal="45245", page_tel="15137524400",
  identity_confirmed=True, page_rendered=True, policy_surface_found=True,
  sha256="b6836bcd-f6203dfa-48e22eb1-b33096b6-0f3f94f4-a5fbaf8c-8eb126cc-217585d3",
  sha256_page="9fae00e2-1f620ee8-ab5e6cdb-12e5cb1e-6a080c26-56799774-241e4294-9fc1be5e",
  quote="No, pets are not allowed at Holiday Inn & Suites Cincinnati-Eastgate (I-275e).",
  service_animal_quote="",
  facts={"pets_allowed": False},
  identity_disagreements=[],
  notes="Affirmative refusal, hotel named in the sentence. Street and postal bind exactly."),

 "holiday inn express and suites bellevue": dict(
  family="IHG", outcome="VERIFIED_NO_PETS",
  triage="FOUNDER_EXCEPTION",
  surface="PROPERTY_FAQ_PANEL",
  page_name="Holiday Inn Express & Suites Cincinnati SE Newport",
  page_street="110 Landmark Drive", page_city="Bellevue",
  page_state="KY", page_postal="41073", page_tel="18599572320",
  identity_confirmed=True, page_rendered=True, policy_surface_found=True,
  sha256="5f15e608-a866b813-4d08cad0-ffda724d-bb274fc5-52037291-6e928123-62af3a6f",
  sha256_page="1fce93c7-07174551-7671b8e0-e4c8a41e-608ca5fa-d752239d-9ffd580e-fd46f958",
  quote="No, pets are not allowed at Holiday Inn Express & Suites Cincinnati SE Newport.",
  service_animal_quote="",
  facts={"pets_allowed": False},
  identity_disagreements=["name: page states 'Cincinnati SE Newport', census "
                          "states 'Bellevue'"],
  question_for_the_founder=(
      "Street, postal code and phone all bind exactly, so this is the same "
      "building under a new brand string: census 'Holiday Inn Express & Suites "
      "Bellevue' vs page 'Holiday Inn Express & Suites Cincinnati SE Newport'. "
      "Do you RENAME the census identity before this refusal is registered? "
      "Registering it under the old name would put a public refusal on a name "
      "the operator no longer uses."),
  notes=("The policy evidence is clean; only the identity needs a ruling. "
         "Ruling 1 of PTF-...-APPLICATION-004 set the precedent that a rename "
         "is a founder decision and supersedes rather than overwrites.")),

 "staybridge suites cincinnati north": dict(
  family="IHG", outcome="PUBLICATION_CANDIDATE",
  triage="FOUNDER_EXCEPTION",
  surface="PROPERTY_FAQ_PANEL",
  page_name="Staybridge Suites Cincinnati North",
  page_street="8955 Lakota Drive West", page_city="West Chester",
  page_state="OH", page_postal="45069", page_tel="15138741900",
  identity_confirmed=True, page_rendered=True, policy_surface_found=True,
  sha256="e24d123f-3bee66c3-7e142129-e2640036-20e65fd5-df46ff5f-57235906-a138f1a2",
  sha256_page="a7bc50bf-d512192b-e0402f7f-595a0445-f9d1ab9b-a3bbb317-8bc196d6-9db9bf95",
  quote=("Pets are welcome at Staybridge Suites Cincinnati North. Our Pet "
         "Policy: Pets allowed. We have a non refundable pet fee of 50 dollars "
         "per week. Pet agreement must be signed at check in. Call hotel for "
         "details. Record of complete and up to date vaccinations required."),
  service_animal_quote="",
  facts={"pets_allowed": True},
  identity_disagreements=[],
  question_for_the_founder=(
      "The fee is stated unambiguously as 50 USD per WEEK. The schema's fee "
      "basis vocabulary is per_night / per_day / per_stay -- there is no "
      "per_week. Do you want the amount withheld as SCHEMA_CANNOT_REPRESENT "
      "with pets_allowed published, or the basis vocabulary extended in its "
      "own work order? I did not convert it to a nightly rate: 50/7 is a "
      "number this hotel never stated."),
  notes=("Street, city and postal bind exactly. This is a schema-reach "
         "question, not an evidence question.")),

 "comfort inn and suites eastgate": dict(
  family="CHOICE", outcome="VERIFIED_NO_PETS",
  triage="CLEAN_VERIFIED_NO_PETS_CANDIDATE",
  surface="ESSENTIAL_DETAILS_PETS_BLOCK",
  page_name="Comfort Inn & Suites Cincinnati Eastgate",
  page_street="4421 Aicholtz Rd", page_city="Cincinnati",
  page_state="OH", page_postal="45245", page_tel="5139470100",
  identity_confirmed=True, page_rendered=True, policy_surface_found=True,
  sha256="ede4ede9-fbe37a4f-b8cf273b-37215e88-baee23af-ce1fe2f7-ec52e303-3ce07b81",
  sha256_page="892ad111-35ce8c9c-ba8cf9f3-43460749-dc0d2093-4e11e2fe-d1dd4d89-9e0ac9bf",
  quote=("Pets Allowed: No General: Only service animals are permitted, free "
         "of charge."),
  service_animal_quote="Only service animals are permitted, free of charge.",
  facts={"pets_allowed": False},
  identity_disagreements=[],
  corroboration=("The property's own hotel alert states that bringing pets "
                 "'will result in a $250 cleaning fee and immediate eviction', "
                 "which is a second first-party statement of the same refusal."),
  notes="Street and postal bind exactly."),

 "comfort suites florence": dict(
  family="CHOICE", outcome="PUBLICATION_CANDIDATE",
  triage="CLEAN_PET_FRIENDLY_CANDIDATE",
  surface="ESSENTIAL_DETAILS_PETS_BLOCK",
  page_name="Comfort Suites Florence - Cincinnati South",
  page_street="5905 Merchants Street", page_city="Florence",
  page_state="KY", page_postal="41042", page_tel="8594881708",
  identity_confirmed=True, page_rendered=True, policy_surface_found=True,
  sha256="e47e0fad-a0c1e5cd-920fe2a5-a82c3eff-8cec2070-344b60ea-50f05227-c135f266",
  sha256_page="7d4bea57-1a1b881c-926065eb-3f49cd26-1ad7e348-d6884fd0-ff6a9c1a-b762e224",
  quote=("Pets Allowed: Yes General: Dogs only. Pet fee of $35. Per night Per "
         "Pet. Limit of 40 pounds. maximum of 1 Pet Per room.. Service animals "
         "are permitted, without charge."),
  service_animal_quote="Service animals are permitted, without charge.",
  facts={"pets_allowed": True,
         "pet_fee": {"amount_cents": 3500, "basis": "per_night",
                     "scope": "per_pet"},
         "weight_limit": {"value": 40, "unit": "lb", "operator": "lte",
                          "scope": "per_pet"},
         "pet_count_limit": 1,
         "species": {"dogs": "accepted", "cats": "prohibited"}},
  identity_disagreements=[],
  notes=("Street, postal and phone all bind exactly. 'Dogs only' is an "
         "affirmative exclusion of cats, not silence about them.")),

 "econo lodge erlanger": dict(
  family="CHOICE", outcome="PUBLICATION_CANDIDATE",
  triage="CLEAN_PET_FRIENDLY_CANDIDATE",
  surface="ESSENTIAL_DETAILS_PETS_BLOCK",
  page_name="Econo Lodge Erlanger - Cincinnati Airport",
  page_street="633 Donaldson Rd.", page_city="Erlanger",
  page_state="KY", page_postal="41018", page_tel="8593425500",
  identity_confirmed=True, page_rendered=True, policy_surface_found=True,
  sha256="45c194bd-fb804b5c-32a10bc1-08a44899-0923d830-6114327f-344eb4f2-44f6fc6e",
  sha256_page="9cbe5715-3da1c867-0fbed20b-0266f3bb-3bcec295-8a223178-1c9cab72-c8a3b715",
  quote=("Pets Allowed: Yes General: Pet accommodation: 15.00 USD per night, "
         "per pet. Maximum 2 pets per room.. Service animals are permitted, "
         "without charge."),
  service_animal_quote="Service animals are permitted, without charge.",
  facts={"pets_allowed": True,
         "pet_fee": {"amount_cents": 1500, "basis": "per_night",
                     "scope": "per_pet"},
         "pet_count_limit": 2},
  identity_disagreements=[],
  notes="Street, postal and phone all bind exactly. No species restriction stated."),

 "quality hotel cincinnati blue ash": dict(
  family="CHOICE", outcome="PUBLICATION_CANDIDATE",
  triage="CLEAN_PET_FRIENDLY_CANDIDATE",
  surface="ESSENTIAL_DETAILS_PETS_BLOCK",
  page_name="Quality Hotel Conference Center Cincinnati Blue Ash",
  page_street="5901 Pfeiffer Road", page_city="Cincinnati",
  page_state="OH", page_postal="45242", page_tel="5136552567",
  identity_confirmed=True, page_rendered=True, policy_surface_found=True,
  sha256="989148f6-31c9cf45-144f8ab5-2836c060-0deda356-ac649e50-cfcc28ae-8e249fd7",
  sha256_page="2645d689-6b9c6368-9ffb9ec0-edc5dd9b-275d1111-8f645a78-5ec4d139-667b796e",
  quote=("Pets Allowed: Yes General: Pets allowed 25.00 USD per night. Max 50 "
         "lbs, 1 pet per room. Kennel available 1 mile away.. Service animals "
         "are permitted, without charge."),
  service_animal_quote="Service animals are permitted, without charge.",
  facts={"pets_allowed": True,
         "pet_fee": {"amount_cents": 2500, "basis": "per_night"},
         "weight_limit": {"value": 50, "unit": "lb", "operator": "lte",
                          "scope": "per_pet"},
         "pet_count_limit": 1},
  identity_disagreements=["phone: page states 5136552567, census states "
                          "5137934500"],
  notes=("Street, postal and the property code oh228 all bind, and the page "
         "name is the census name plus 'Conference Center'. The phone "
         "disagreement is recorded rather than corrected -- a phone is the "
         "signal Detroit 012 used to separate two brands at one address, so "
         "it is not a field to overwrite quietly. 'Max 50 lbs' is read as "
         "per_pet only because the same sentence caps the room at one pet.")),

 "quality inn and suites cincinnati": dict(
  family="CHOICE", outcome="VERIFIED_NO_PETS",
  triage="CLEAN_VERIFIED_NO_PETS_CANDIDATE",
  surface="ESSENTIAL_DETAILS_PETS_BLOCK",
  page_name="Quality Inn & Suites Cincinnati Uptown Norwood",
  page_street="5410 Ridge Avenue", page_city="Cincinnati",
  page_state="OH", page_postal="45213", page_tel="2832208436",
  identity_confirmed=True, page_rendered=True, policy_surface_found=True,
  sha256="ede4ede9-fbe37a4f-b8cf273b-37215e88-baee23af-ce1fe2f7-ec52e303-3ce07b81",
  sha256_page="4059caf2-b301eef7-bbaabe73-e3a0afa8-d415bd71-a64c9197-0f9cfdcb-61acc866",
  quote=("Pets Allowed: No General: Only service animals are permitted, free "
         "of charge."),
  service_animal_quote="Only service animals are permitted, free of charge.",
  facts={"pets_allowed": False},
  identity_disagreements=["phone: page states 2832208436, census states "
                          "5136318500"],
  notes=("Street and postal bind exactly and the page name is the census name "
         "plus 'Uptown Norwood'. 283 is a valid overlay for the 513 area, so "
         "the phone disagreement is plausible drift, recorded not corrected.")),
}

#: Choice renders an identical refusal block for every no-pets property, so the
#: SURFACE hash collides across hotels by design -- oh186 and oh397 produce the
#: same digest because the markup and the words are genuinely identical. The
#: surface hash therefore proves WHAT was said, never BY WHOM. The page hash and
#: the URL are what bind a Choice quote to a property, and any later application
#: must carry both.
SURFACE_HASH_IS_NOT_PROPERTY_UNIQUE = ("CHOICE",)


def build_results():
    cohort = load(COHORT)
    rows = []
    for row in cohort["rows"]:
        key = row["identity_key"]
        o = OBS[key]
        rec = OrderedDict((
            ("identity_key", key),
            ("canonical_name", row["canonical_name"]),
            ("family", o["family"]),
            ("official_property_url", row["official_property_url"]),
            ("observed_at", OBSERVED_ON),
            ("capture_method", CAPTURE_METHOD),
            ("provider_calls", 0),
            ("cost_usd", 0.0),
            ("page_rendered", o["page_rendered"]),
            ("identity_confirmed", o["identity_confirmed"]),
            ("policy_surface_found", o["policy_surface_found"]),
            ("policy_surface", o["surface"]),
            ("outcome", o["outcome"]),
            ("triage", o["triage"]),
            ("page_identity", OrderedDict((
                ("name", o["page_name"]), ("street", o["page_street"]),
                ("city", o["page_city"]), ("state", o["page_state"]),
                ("postal_code", o["page_postal"]), ("phone", o["page_tel"])))),
            ("census_identity", OrderedDict((
                ("name", row["canonical_name"]), ("street", row["address"]),
                ("city", row["city"]), ("state", ""),
                ("postal_code", row["postal_code"]), ("phone", row["phone"])))),
            ("identity_disagreements", o["identity_disagreements"]),
            ("quote", o["quote"]),
            ("sha256_policy_surface", o["sha256"]),
            ("sha256_page", o["sha256_page"]),
            ("facts", o["facts"]),
            ("notes", o["notes"]),
        ))
        if o.get("service_animal_quote"):
            rec["service_animal_statement"] = OrderedDict((
                ("quote", o["service_animal_quote"]),))
        if o.get("binding_quote"):
            rec["binding_quote"] = o["binding_quote"]
        if o.get("corroboration"):
            rec["corroboration"] = o["corroboration"]
        if o.get("question_for_the_founder"):
            rec["question_for_the_founder"] = o["question_for_the_founder"]
        rows.append(rec)

    return OrderedDict((
        ("work_order", WORK_ORDER),
        ("market_id", cohort["market_id"]),
        ("observed_at", OBSERVED_ON),
        ("capture_method", CAPTURE_METHOD),
        ("provider_calls", 0),
        ("paid_spend_usd", 0.0),
        ("authority_mutated", False),
        ("approvals_written", 0),
        ("cohort_size", cohort["count"]),
        ("processed", len(rows)),
        ("locators", OrderedDict((
            ("IHG", "Pet policy accordion panel; fallback: property FAQ panel "
                    "'Can I bring my pet to <hotel>?'"),
            ("CHOICE", "Pets block inside Essential details "
                       "('Pets Allowed: Yes|No' plus the property's own terms)")))),
        ("surface_hash_is_not_property_unique",
         list(SURFACE_HASH_IS_NOT_PROPERTY_UNIQUE)),
        ("rows", rows),
    ))


def main():
    results = build_results()
    render(RESULTS, results)

    stats = measure(results["rows"])
    out = OrderedDict((("work_order", WORK_ORDER), ("families", stats),
                       ("recommendations", OrderedDict())))
    for family in ("IHG", "CHOICE"):
        verdict, why = recommend(stats[family])
        out["recommendations"][family] = OrderedDict(
            (("recommendation", verdict), ("because", why)))
    render(MEASUREMENT, out)
    reprice = build_reprice()
    render(REPRICE, reprice)
    return results, out, reprice


if __name__ == "__main__":
    main()


# --------------------------------------------------------------- Phase 6 reprice

#: The repo's own established Bright Data unit, used by
#: ``firecrawl_hard_lanes_003`` and ``choice_coverage_matrix_005``.
BRIGHTDATA_USD_PER_ATTEMPT = 0.197

RESOLVED = ("PUBLISHED_PET_FRIENDLY", "VERIFIED_NO_PETS",
            "OUT_OF_CURRENT_CATEGORY")

#: Which lane each remaining family belongs to, and the evidence that put it
#: there. None of this is re-derived here -- it is prior work, cited.
LANE_EVIDENCE = {
    "MARRIOTT": ("BRIGHT_DATA",
                 "PTF-DETROIT-MARRIOTT-SCALE-015 closed Marriott at 26/30 "
                 "publication-grade on the current /en-us/hotels/ template; "
                 "PTF-FIRECRAWL-HARD-LANES-003 could not reach Marriott."),
    "HILTON": ("BRIGHT_DATA",
               "PTF-DETROIT-HILTON-DIAGNOSTIC-016 returned 10/10 clean and "
               "closed the family at SCALE; Firecrawl cannot reach Hilton, and "
               "Hilton throttles attended Chrome after roughly 40 hits "
               "(PTF-CINCINNATI-ZERO-COST-CAPTURE-003)."),
    "IHG": ("ATTENDED_CHROME_FREE",
            "this work order: 5/5 rendered, 5/5 identity-confirmed, 5/5 "
            "publication-grade."),
    "CHOICE": ("ATTENDED_CHROME_FREE",
               "this work order: 5/5 rendered, 5/5 identity-confirmed, 5/5 "
               "publication-grade."),
    "HYATT": ("BLOCKED_BY_ADR",
              "Hyatt is ADR-forbidden (PTF-COLUMBUS-UNRESOLVED-CAPTURE-003). "
              "No lane may be costed for these rows."),
    "INDEPENDENT": ("UNPROVEN",
                    "no family-level probe exists for Cincinnati independents. "
                    "They are not costed here; sizing them needs its own free "
                    "probe first."),
    "ESA": ("UNPROVEN", "single row; too few to constitute a lane."),
    "BESTWESTERN": ("UNPROVEN", "no routed unresolved rows remain."),
    "WYNDHAM": ("UNPROVEN",
                "Wyndham's policy lives in the markup rather than innerText "
                "(PTF-CINCINNATI-ZERO-COST-CAPTURE-003); no routed unresolved "
                "rows remain."),
}


def build_reprice():
    from collections import Counter
    routes = load(AUTH_ROUTING)["routes"]
    partition = load(PARTITION)
    state = {i["identity_key"]: i["final_state"] for i in partition["items"]}
    routed = {r["hotel_ref"]["identity_key"] for r in routes}

    by_family = Counter()
    for route in routes:
        key = route["hotel_ref"]["identity_key"]
        if state.get(key) in RESOLVED:
            continue
        by_family[route.get("brand", "") or "UNKNOWN"] += 1

    unrouted = sorted(k for k, v in state.items()
                      if v not in RESOLVED and k not in routed)

    free, paid_bd, blocked, unproven = [], [], [], []
    for family, n in by_family.items():
        lane = LANE_EVIDENCE.get(family, ("UNPROVEN", "no evidence on file"))[0]
        target = {"ATTENDED_CHROME_FREE": free, "BRIGHT_DATA": paid_bd,
                  "BLOCKED_BY_ADR": blocked}.get(lane, unproven)
        target.append((family, n))

    free_n = sum(n for _f, n in free)
    bd_n = sum(n for _f, n in paid_bd)

    return OrderedDict((
        ("work_order", WORK_ORDER),
        ("basis", "the 135-route shard and the 256-row partition at 800e74f"),
        ("unresolved_total", sum(1 for v in state.values() if v not in RESOLVED)),
        ("unresolved_routed", sum(by_family.values())),
        ("unresolved_unrouted", len(unrouted)),
        ("by_family", OrderedDict(sorted(by_family.items()))),
        ("lanes", OrderedDict((
            ("attended_chrome_free", OrderedDict((
                ("families", OrderedDict(sorted(free))), ("rows", free_n),
                ("usd", 0.0)))),
            ("bright_data", OrderedDict((
                ("families", OrderedDict(sorted(paid_bd))), ("rows", bd_n),
                ("usd_per_attempt", BRIGHTDATA_USD_PER_ATTEMPT),
                ("usd", round(bd_n * BRIGHTDATA_USD_PER_ATTEMPT, 2))))),
            ("firecrawl", OrderedDict((
                ("families", {}), ("rows", 0), ("usd", 0.0),
                ("why", "Firecrawl's Cincinnati case was IHG and Choice. This "
                        "probe moved both to the free lane, and Firecrawl "
                        "cannot reach Marriott or Hilton "
                        "(PTF-FIRECRAWL-HARD-LANES-003), so no row in the "
                        "current unresolved set genuinely requires it.")))),
            ("blocked", OrderedDict((
                ("families", OrderedDict(sorted(blocked))),
                ("rows", sum(n for _f, n in blocked)),
                ("why", "ADR-forbidden; not costable")))),
            ("unproven", OrderedDict((
                ("families", OrderedDict(sorted(unproven))),
                ("rows", sum(n for _f, n in unproven)),
                ("why", "needs its own free probe before any lane is costed")))),
        ))),
        ("lane_evidence", OrderedDict(
            (f, OrderedDict((("lane", v[0]), ("because", v[1]))))
            for f, v in sorted(LANE_EVIDENCE.items()))),
        ("spend_before_this_probe", OrderedDict((
            ("ihg_and_choice_rows", free_n),
            ("usd_if_bought", round(free_n * BRIGHTDATA_USD_PER_ATTEMPT, 2)))),),
        ("spend_after_this_probe", OrderedDict((
            ("rows", bd_n),
            ("usd", round(bd_n * BRIGHTDATA_USD_PER_ATTEMPT, 2))))),
        ("avoided_usd", round(free_n * BRIGHTDATA_USD_PER_ATTEMPT, 2)),
        ("note", "An estimate, not an authorization. Nothing here spends."),
    ))
