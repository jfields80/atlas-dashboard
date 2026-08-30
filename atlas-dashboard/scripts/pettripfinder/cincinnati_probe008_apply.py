# -*- coding: utf-8 -*-
"""PTF-CINCINNATI-INDEPENDENT-FREE-PROBE-008 -- the ten attended observations.

Observed 2026-08-30 in attended Chrome. No provider, no spend, no authority.

THE RESULT STRATUM B WAS BUILT TO FIND
--------------------------------------
Two of the six previously-POLICY_NOT_FOUND independents DID have a policy, and
both were reachable free. InTown Suites hides its answer behind a ``<label>``
accordion that a throughput sweep never opened; The Summit publishes a complete
policy on a dedicated /about-us/hotel-policies page that the routing shard does
not point at. So a third of the "empty" independents were locator misses rather
than absences.

The other four are genuinely silent, and one of those matters on its own:
Drury's page carries ``petsAllowed: http://schema.org/False`` in JSON-LD and
not one occurrence of the word "pet" in 10,045 characters of expanded prose.
Ruling #2 of PTF-CINCINNATI-FOUNDER-REVIEW-AND-APPLICATION-004 -- the Great
Wolf hold -- refused exactly that shape, so the flag is recorded as evidence
and the row stays POLICY_NOT_FOUND. Four Cincinnati Drury properties share that
template, so this settles the shape for all four.

WHAT THE FRESH STRATUM IS ACTUALLY MEASURING
--------------------------------------------
Three of the four fresh rows are served from choicehotels.com. Country Inn &
Suites and Radisson are Choice brands, so those pages sit on the locator
SCALE-006 already closed and they say nothing about independent capturability.
They are reported, and they are reported apart from the independents.
"""

from __future__ import annotations

from collections import Counter, OrderedDict

from scripts.pettripfinder.cincinnati_free_brand_probe_005 import load, render
from scripts.pettripfinder.cincinnati_independent_probe_008 import (
    CAPTURE_METHOD, COHORT, MARKET_ID, MEASUREMENT, OBSERVED_ON, REPRICE,
    RESULTS, WORK_ORDER, build_reprice, measure, recommend_independents)


def _o(**kw):
    return kw


OBS = {

# ------------------------------------------------------- STRATUM A -- FRESH (4)

"country inn and suites airport": _o(
  outcome="VERIFIED_NO_PETS", triage="CLEAN_VERIFIED_NO_PETS_CANDIDATE",
  platform="CHOICE_PLATFORM", surface="ESSENTIAL_DETAILS_PETS_BLOCK",
  name="Country Inn & Suites by Radisson, Cincinnati Airport, KY",
  street="759 Petersburg Rd", city="Hebron", state="KY", postal="41048",
  tel="8596812558",
  sha="ede4ede9-fbe37a4f-b8cf273b-37215e88-baee23af-ce1fe2f7-ec52e303-3ce07b81",
  shap="10c032c9-dafd40fe-aadaf0ef-92532d0e-1cfd5b48-385f4244-8ee70a52-d7c00490",
  quote=("Pets Allowed: No General: Only service animals are permitted, free "
         "of charge."),
  sa="Only service animals are permitted, free of charge.",
  facts={"pets_allowed": False}, diffs=[],
  corroboration=("The property's own hotel alert repeats the refusal in its "
                 "own words: 'No pets allowed.'"),
  notes=("Routed as INDEPENDENT but served from choicehotels.com -- Country "
         "Inn & Suites is a Choice brand, so the shard's family label is "
         "stale. Street, postal and phone bind exactly.")),

"country inn and suites erlanger": _o(
  outcome="PUBLICATION_CANDIDATE", triage="CLEAN_PET_FRIENDLY_CANDIDATE",
  platform="CHOICE_PLATFORM", surface="ESSENTIAL_DETAILS_PETS_BLOCK",
  name="Country Inn & Suites by Radisson, Erlanger - Cincinnati South",
  street="630 Donaldson Highway", city="Erlanger", state="KY", postal="41018",
  tel="8597393002",
  sha="dc7ebe6b-d75c494f-8ee5c81a-4187b329-5ed2e3bf-419a9ecf-c1c483c1-71437be1",
  shap="49055320-6c6dc99a-fe236a30-d3f420eb-e3bc929d-3c8203b7-e3437f75-674fe2ae",
  quote=("Pets Allowed: Yes General: Pets Allowed. Pet Charge 25.00 USD Per "
         "Pet, Per Night. Refundable deposit of 100.00 USD is required Per "
         "Stay. Pet limit 2 Pet Per Room. No Pets in Suites and the pet should "
         "not be unattended at any time.. Service animals are permitted, "
         "without charge."),
  sa="Service animals are permitted, without charge.",
  facts={"pets_allowed": True,
         "pet_fee": {"amount_cents": 2500, "basis": "per_night",
                     "scope": "per_pet"},
         "pet_count_limit": 2,
         "other_charges": [{"kind": "refundable_deposit",
                            "amount_cents": 10000, "basis": "per_stay"}],
         "unattended_policy": "The pet should not be left unattended at any time.",
         "general_restrictions": "No pets in suites."},
  diffs=[],
  notes=("A fee and a deposit, and the source labels them as such -- the "
         "charge is per pet per night and the 100 USD is explicitly "
         "REFUNDABLE and per stay. They publish as two charges, not one "
         "headline: PTF-LOUISVILLE-SIGNED-AUTHORITY-006 is the precedent that "
         "a fee and a deposit are two different things. Nothing here is "
         "contradictory, so this is clean rather than an exception.")),

"radisson hotel cincinnati riverfront": _o(
  outcome="VERIFIED_NO_PETS", triage="CLEAN_VERIFIED_NO_PETS_CANDIDATE",
  platform="CHOICE_PLATFORM", surface="ESSENTIAL_DETAILS_PETS_BLOCK",
  name="Radisson Hotel Cincinnati Riverfront", street="668 W. 5th St.",
  city="Covington", state="KY", postal="41011", tel="8597770008",
  sha="ede4ede9-fbe37a4f-b8cf273b-37215e88-baee23af-ce1fe2f7-ec52e303-3ce07b81",
  shap="8e56be7f-bf93e814-104478b6-72c09596-4ce97577-efa5fc60-106c4d4f-658ebc5e",
  quote=("Pets Allowed: No General: Only service animals are permitted, free "
         "of charge."),
  sa="Only service animals are permitted, free of charge.",
  facts={"pets_allowed": False}, diffs=[],
  notes=("Also a Choice-platform page despite the INDEPENDENT label. Street, "
         "postal and phone bind exactly.")),

"studio 6 extended stay fairfield oh cincinnati": _o(
  outcome="PUBLICATION_CANDIDATE", triage="FOUNDER_EXCEPTION",
  platform="MOTEL6_PLATFORM", surface="AMENITY_TILE",
  name="Studio 6 Extended stay Fairfield, OH - Cincinnati",
  street="Seward Road", city="Fairfield", state="OH", postal="",
  tel="5132689128",
  sha="aeb545c1-68420a7e-8cfba929-1fde92f6-7c7dc405-54e09810-b38c9e6a-38d4ecce",
  shap="2916f2b9-4949e595-dc3b5fe7-b0ca27db-a100696c-886f6850-268d2c81-5f708e10",
  quote="Pet-Friendly Accommodation. Pets welcome throughout your stay.",
  sa="",
  facts={"pets_allowed": True}, diffs=[
    "street: the page contradicts ITSELF -- JSON-LD and the header state "
    "'Seward Road', matching the census, while the About prose states "
    "'Located at 3010 Lakeview Dr'"],
  question=("This is the identity APPLICATION-004 renamed, whose policy that "
            "order deliberately deferred to 'the next clean recapture'. Two "
            "problems remain. (1) The page states two different street "
            "addresses -- JSON-LD and the header say Seward Road, which "
            "matches the census; the About paragraph says 3010 Lakeview Dr. "
            "(2) The only fee-relevant statement is a footer link, 'Pets Stay "
            "Free Details', pointing at motel6.com/pages/policies/"
            "reservation-policies/ -- a chain-wide page this property page "
            "never binds to itself. Publish pets_allowed alone on the amenity "
            "statement, or hold the row until the property states its own "
            "terms?"),
  notes=("The pet evidence is a property-page amenity tile in prose, not a "
         "bare structured flag, so it is stronger than the shape ruling #2 of "
         "APPLICATION-004 refused -- but it carries no fee, count, weight or "
         "species. The corporate 'Pets Stay Free' claim was NOT read as this "
         "property's policy.")),

# -------------------------------------------------- STRATUM B -- RE-EXAMINE (6)

"drury inn and suites cincinnati northeast mason": _o(
  outcome="POLICY_NOT_FOUND", triage="NO_FOUNDER_ACTION",
  platform="INDEPENDENT_CHAIN", surface="",
  name="Drury Inn & Suites Cincinnati Northeast Mason",
  street="9956 Escort Drive", city="Mason", state="OH", postal="45040",
  tel="15133360108",
  sha="", shap="9021885a-a4c0d043-315277fe-4429ddd4-01e54136-33f2075d-ed5feb7d-5a932af5",
  quote="", sa="", facts={}, diffs=[],
  structured_flag="petsAllowed: http://schema.org/False (JSON-LD)",
  notes=("Every accordion expanded, taking the page from 4,112 to 10,045 "
         "characters, and the word 'pet' appears ZERO times in the prose. The "
         "only pet datum on the page is a bare JSON-LD petsAllowed flag -- "
         "precisely the shape ruling #2 of APPLICATION-004 refused for Great "
         "Wolf Lodge, where the founder declined to lower this market's "
         "no-pets evidentiary standard. So the flag is recorded and the row "
         "stays POLICY_NOT_FOUND. The site's /content/faqs is a CORPORATE "
         "page and the property page never binds it, so it was not read as "
         "this hotel's policy. Four Cincinnati Drury properties share this "
         "template; this settles the shape for all four.")),

"golden lamb": _o(
  outcome="POLICY_NOT_FOUND", triage="NO_FOUNDER_ACTION",
  platform="INDEPENDENT_BESPOKE", surface="",
  name="Golden Lamb", street="", city="Lebanon", state="OH", postal="",
  tel="",
  sha="", shap="ea982cc8-1e4ee307-f9c0e347-6af0b008-6de23638-6d21939a-c98ea576-4d653711",
  quote="", sa="", facts={}, diffs=[],
  notes=("Three first-party surfaces read: the homepage, /about-us/faqs/ and "
         "/stay/hotel-and-room-information/. Zero pet mentions on any of "
         "them. A genuine silence, not a locator miss.")),

"intown suites cincinnati north": _o(
  outcome="VERIFIED_NO_PETS", triage="CLEAN_VERIFIED_NO_PETS_CANDIDATE",
  platform="INDEPENDENT_CHAIN", surface="PROPERTY_FAQ_ACCORDION_LABEL",
  name="InTown Suites Extended Stay Cincinnati OH - Fairfield",
  street="", city="Fairfield", state="OH", postal="", tel="",
  sha="271c4b0b-565d97a1-16f19960-8565c80c-04f6ee26-be129eef-939ad797-1b47b1d0",
  shap="81274d2a-a751c028-4bf4a9d2-1215aeed-7253199d-c348fdb4-6842ff38-79c4f71a",
  quote=("ARE PETS ALLOWED AT INTOWN SUITES CINCINNATI OH - FAIRFIELD? NO "
         "PETS ALLOWED AT INTOWN SUITES CINCINNATI OH - FAIRFIELD"),
  sa="", facts={"pets_allowed": False}, diffs=[],
  recovered_from="POLICY_NOT_FOUND (Capture Pass 3)",
  notes=("RECOVERED. The answer sits inside a <label>-driven accordion that "
         "responds to neither aria-expanded nor <details>, so a generic "
         "expander misses it and Pass 3 recorded POLICY_NOT_FOUND. Both "
         "question and answer name this hotel, so the refusal is "
         "property-bound in its own words. The page's only phone number is a "
         "corporate reservations line, so identity rests on the page's own "
         "property name and its URL slug rather than on a phone match.")),

"symphony hotel and restaurant": _o(
  outcome="POLICY_NOT_FOUND", triage="NO_FOUNDER_ACTION",
  platform="INDEPENDENT_BESPOKE", surface="",
  name="The Symphony Hotel", street="", city="Cincinnati", state="OH",
  postal="", tel="",
  sha="", shap="a98e39bf-4c0698e2-858bd6e8-7f28c0ca-06a61865-a882a157-c2907805-9d6dd97f",
  quote="", sa="", facts={}, diffs=[],
  notes=("Homepage and /rooms both read. No pet mention and no policy "
         "language of any kind -- the site carries no terms surface at all. "
         "A nine-room boutique that simply does not publish policy.")),

"the summit hotel": _o(
  outcome="PUBLICATION_CANDIDATE", triage="FOUNDER_EXCEPTION",
  platform="INDEPENDENT_CMS", surface="HOTEL_POLICIES_PAGE",
  name="The Summit Hotel", street="5345 Medpace Way", city="Cincinnati",
  state="OH", postal="45227", tel="5135279900",
  sha="2eebcd0c-b6d081d2-254d6535-3cf39822-b4481782-30315839-44831cd8-34876dbe",
  shap="004a01ae-ccdf8e92-387d7627-5c504e79-79397ac3-193a92b3-7da05c85-00ede1a2",
  quote=("DOG-FRIENDLY The Summit welcomes dogs under 50 pounds. Pets must be "
         "declared upon check-in. Maximum (2) dogs per room. A non-refundable "
         "$50 fee applies. An additional $50 fee applies for One Bedroom "
         "Suites and the Presidential Suite. Fees do not apply for ADA "
         "service animals. Please note we do not accept pets other than dogs."),
  sa="Fees do not apply for ADA service animals.",
  facts={"pets_allowed": True,
         "pet_fee": {"amount_cents": 5000, "basis": "per_stay",
                     "refundable_stated": False},
         "pet_count_limit": 2,
         "weight_limit": {"value": 50, "unit": "lb", "operator": "lt",
                          "scope": "per_pet"},
         "species": {"dogs": "accepted", "cats": "prohibited"}},
  diffs=[],
  recovered_from="POLICY_NOT_FOUND (Capture Pass 3)",
  question=("RECOVERED, and one clause needs a ruling. The headline is clean: "
            "dogs UNDER 50 pounds (operator lt), maximum 2 per room, a "
            "non-refundable $50 fee, no species but dogs, and no charge for "
            "ADA service animals. But 'An additional $50 fee applies for One "
            "Bedroom Suites and the Presidential Suite' is conditional on ROOM "
            "TYPE, and the schema's tier condition types are stay_length_range "
            "and pet_count_range only. Publish the $50 headline and withhold "
            "the room-type surcharge, or withhold the fee entirely until the "
            "schema can express a room-type condition?"),
  notes=("The policy lives at /about-us/hotel-policies, which the routing "
         "shard does not point at -- the route is the homepage, and the "
         "homepage says nothing about pets. That is a locator depth finding, "
         "not a routing repair: same property, same domain.")),

"wildwood inn": _o(
  outcome="POLICY_NOT_FOUND", triage="NO_FOUNDER_ACTION",
  platform="INDEPENDENT_LEGACY", surface="",
  name="Wildwood Inn", street="", city="Florence", state="KY", postal="",
  tel="",
  sha="", shap="edf5a496-5c588cfb-2fedb3ed-9aff5d48-49879ea3-80587824-943cf0e8-5094f86d",
  quote="", sa="", facts={}, diffs=[],
  notes=("Homepage and rooms page total under 1,500 characters between them. "
         "No pet mention, no policy language. A hand-built legacy site with "
         "no terms surface to find.")),
}

#: What actually worked, per domain. Recorded rather than generalised: six
#: independent domains produced five different answers, which is the whole
#: reason this probe does not propose a shared independent reader.
LOCATORS = OrderedDict((
    ("choicehotels.com", "Pets block inside Essential details -- the locator "
                         "PTF-CINCINNATI-FREE-LANE-SCALE-006 already closed"),
    ("motel6.com", "Amenity tile on the property page; the fee claim is a "
                   "corporate footer link and was NOT read as property policy"),
    ("druryhotels.com", "Nothing. Bare JSON-LD petsAllowed flag only, which "
                        "this market does not accept as evidence"),
    ("goldenlamb.com", "Nothing across homepage, /about-us/faqs/ and "
                       "/stay/hotel-and-room-information/"),
    ("intownsuites.com", "Property FAQ behind a <label>-driven accordion -- "
                         "opens to neither aria-expanded nor <details>"),
    ("symphonyhotel.com", "Nothing; the site carries no terms surface"),
    ("thesummithotel.com", "A dedicated /about-us/hotel-policies page the "
                           "routing shard does not point at"),
    ("wildwoodinnky.com", "Nothing; a legacy site under 1,500 characters"),
))


def build_results():
    cohort = load(COHORT)
    rows = []
    for row in cohort["rows"]:
        key = row["identity_key"]
        o = OBS[key]
        rec = OrderedDict((
            ("identity_key", key),
            ("canonical_name", row["canonical_name"]),
            ("family", row["family"]),
            ("stratum", row["stratum"]),
            ("platform", o["platform"]),
            ("official_property_url", row["official_property_url"]),
            ("official_domain", row["official_domain"]),
            ("observed_at", OBSERVED_ON),
            ("capture_method", CAPTURE_METHOD),
            ("provider_calls", 0),
            ("cost_usd", 0.0),
            ("page_rendered", True),
            ("identity_confirmed", True),
            ("policy_surface_found", bool(o["surface"])),
            ("policy_surface", o["surface"]),
            ("outcome", o["outcome"]),
            ("triage", o["triage"]),
            ("page_identity", OrderedDict((
                ("name", o["name"]), ("street", o["street"]),
                ("city", o["city"]), ("state", o["state"]),
                ("postal_code", o["postal"]), ("phone", o["tel"])))),
            ("census_identity", OrderedDict((
                ("name", row["canonical_name"]), ("street", row["address"]),
                ("city", row["city"]), ("state", ""),
                ("postal_code", row["postal_code"]), ("phone", row["phone"])))),
            ("identity_disagreements", o["diffs"]),
            ("quote", o["quote"]),
            ("sha256_policy_surface", o["sha"]),
            ("sha256_page", o["shap"]),
            ("facts", o["facts"]),
            ("notes", o["notes"]),
        ))
        if row["stratum"] == "B_RE_EXAMINE":
            rec["prior_outcome"] = row["prior_outcome"]
        if o.get("recovered_from"):
            rec["recovered_from"] = o["recovered_from"]
        if o.get("structured_flag"):
            rec["structured_flag_recorded_not_published"] = o["structured_flag"]
        if o.get("sa"):
            rec["service_animal_statement"] = OrderedDict((("quote", o["sa"]),))
        if o.get("corroboration"):
            rec["corroboration"] = o["corroboration"]
        if o.get("question"):
            rec["question_for_the_founder"] = o["question"]
        rows.append(rec)

    return OrderedDict((
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("observed_at", OBSERVED_ON),
        ("capture_method", CAPTURE_METHOD),
        ("provider_calls", 0),
        ("paid_spend_usd", 0.0),
        ("authority_mutated", False),
        ("approvals_written", 0),
        ("cohort_size", cohort["count"]),
        ("processed", len(rows)),
        ("locators_by_domain", LOCATORS),
        ("no_shared_independent_reader_is_proposed",
         "Six independent domains produced five different answers. A reader "
         "built from two successes would be a reader built from two websites; "
         "this probe measures capturability, not reader design."),
        ("rows", rows),
    ))


def main():
    results = build_results()
    render(RESULTS, results)
    rows = results["rows"]

    independents = [r for r in rows if r["platform"].startswith("INDEPENDENT")]
    choice_platform = [r for r in rows if r["platform"] == "CHOICE_PLATFORM"]
    esa = [r for r in rows if r["family"] == "ESA"]
    fresh = [r for r in rows if r["stratum"] == "A_FRESH"]
    reexamine = [r for r in rows if r["stratum"] == "B_RE_EXAMINE"]

    yielding_domains = {r["official_domain"] for r in independents
                        if r["policy_surface_found"]}
    verdict, why = recommend_independents(measure(independents),
                                          len(yielding_domains))

    out = OrderedDict((
        ("work_order", WORK_ORDER),
        ("rates_are_never_blended", True),
        ("INDEPENDENT", OrderedDict((
            ("what", "The six genuinely independent domains. This is the "
                     "number the free-lane decision rests on."),
            ("stats", measure(independents)),
            ("distinct_domains_with_yield", len(yielding_domains)),
            ("recovered_from_previously_empty",
             sum(1 for r in independents if r.get("recovered_from"))),
            ("recommendation", verdict), ("because", why)))),
        ("CHOICE_PLATFORM_MISLABELLED", OrderedDict((
            ("what", "Routed INDEPENDENT but served from choicehotels.com. "
                     "Reported apart, because counting them as independents "
                     "would credit the independent lane with a result the "
                     "Choice lane produced."),
            ("stats", measure(choice_platform))))),
        ("ESA", OrderedDict((
            ("what", "One row, and it is reported as one row."),
            ("included", bool(esa)),
            ("stats", measure(esa) if esa else None),
            ("do_not_generalise",
             "A single property cannot carry a family rate. Cincinnati holds "
             "no other unresolved ESA row, so there is nothing to extrapolate "
             "to even if it were sound."),
            ("free_capturable", bool(esa) and esa[0]["policy_surface_found"])))),
        ("BY_STRATUM", OrderedDict((
            ("A_FRESH", measure(fresh)),
            ("B_RE_EXAMINE", measure(reexamine))))),
    ))
    render(MEASUREMENT, out)
    render(REPRICE, build_reprice(rows))
    return results, out


if __name__ == "__main__":
    main()
