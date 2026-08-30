# -*- coding: utf-8 -*-
"""PTF-CINCINNATI-INDEPENDENT-FREE-PROBE-009 -- observations and corrections.

Observed 2026-08-30 in attended Chrome. No provider, no spend, no authority.

THE METHOD DEFECT THIS PASS FOUND IN ITS OWN PREDECESSOR
--------------------------------------------------------
The Warehouse Hotel's pet policy is in its page's DOM and not in its
``innerText``: 149,578 characters of textContent against 2,419 visible. Every
prior Cincinnati sweep, PROBE-008 included, read ``innerText``.

So this order re-read every row it had just called silent using
``textContent`` -- and four more policies appeared, including on a template
PROBE-008 had declared settled. Drury publishes a full pet policy inside an
embedded JSON payload:

    "Dogs and cats accepted. Rooms with pets will be charged a daily fee of
     $50 per room plus tax. Service animals are free of charge. Limit of two
     pets per room with a combined weight of 80 pounds."

while the same page's JSON-LD says ``petsAllowed: http://schema.org/False``.
PROBE-008 read the flag, found no prose in innerText, and recorded
POLICY_NOT_FOUND for Drury Mason -- concluding in its own commit message that
this "settles the shape for all four" Cincinnati Drury properties. It settled
it wrongly, and all four are pet-friendly.

That is a correction to my own work, and the four superseded PROBE-008 rows are
carried here explicitly rather than left to rot in a committed artifact.

A second, smaller lesson: substring matching on "pet" hits "com-pet-ition" and
"ap-pet-ite". Both appeared in this cohort. Every scan here uses word
boundaries.
"""

from __future__ import annotations

from collections import Counter, OrderedDict

from scripts.pettripfinder.cincinnati_free_brand_probe_005 import load, render
from scripts.pettripfinder.cincinnati_free_lane_scale_006 import PARTITION, RESOLVED, ROUTING
from scripts.pettripfinder.cincinnati_independent_probe_008 import (
    RESULTS as PROBE008_RESULTS)
from scripts.pettripfinder.cincinnati_independent_probe_009 import (
    CAPTURE_METHOD, COHORT, MARKET_ID, MEASUREMENT, OBSERVED_ON, PENDING,
    REPRICE, RESULTS, WORK_ORDER, final_recommendation, measure)


def _o(**kw):
    return kw


#: The Drury pet policy, identical on all four Cincinnati property pages. It
#: lives in an embedded JSON payload, so the surface digest is shared and the
#: PAGE digest is what binds it to a property -- the same rule SCALE-006
#: established for Choice's shared refusal block.
DRURY_QUOTE = ("Pet Policy: Dogs and cats accepted. Rooms with pets will be "
               "charged a daily fee of $50 per room plus tax. Service animals "
               "are free of charge. Limit of two pets per room with a combined "
               "weight of 80 pounds.")

DRURY_FACTS = {
    "pets_allowed": True,
    "pet_fee": {"amount_cents": 5000, "basis": "per_night",
                "scope": "per_room", "tax_relationship": "plus_tax"},
    "pet_count_limit": 2,
    "combined_weight_limit": {"value": 80, "unit": "lb", "operator": "lte"},
    "species": {"dogs": "accepted", "cats": "accepted"},
}

DRURY_QUESTION = (
    "The property page states a complete pet policy in an embedded JSON "
    "payload -- dogs and cats, $50 per room per night plus tax, two pets, 80 "
    "pounds combined -- while the SAME page's JSON-LD states petsAllowed: "
    "false. One of the two is wrong and the page does not say which. The "
    "prose is specific and the flag is a boolean, and APPLICATION-004's Great "
    "Wolf ruling already held that a bare flag is not evidence in this market, "
    "which argues for the prose. Publish on the prose and record the flag as "
    "SOURCE_CONTRADICTORY? This one ruling settles all four Cincinnati Drury "
    "properties.")

DRURY_NOTE = (
    "Found only by reading textContent; innerText shows none of it. "
    "'a daily fee of $50 per room' is per_night and per_room -- not per pet -- "
    "and 'combined weight of 80 pounds' is an explicit COMBINED limit, so it "
    "publishes as combined_weight_limit and never as a per-pet weight_limit.")


OBS = OrderedDict((

("budget host town center motel", _o(
  outcome="POLICY_NOT_FOUND", triage="NO_FOUNDER_ACTION", surface="",
  platform="INDEPENDENT", name="Budget Host Town Center Motel",
  sha="", shap="f0a6adee-527c686a-f1980bce-0eb674c7-1baac641-efba781c-92296b11-88c13e82",
  quote="", sa="", facts={},
  notes=("Re-read with textContent: 3,961 characters of DOM, zero pet terms "
         "under word-boundary matching. The only policy links are corporate "
         "About/Privacy/Franchise pages the property page never binds. Pass 1 "
         "had recorded ACCESS_BLOCKED; the page renders fine now, so the "
         "constraint is absent content, not access."))),

("chester inn and suites", _o(
  outcome="POLICY_NOT_FOUND", triage="NO_FOUNDER_ACTION", surface="",
  platform="INDEPENDENT", name="Chester Inn & Suites",
  sha="", shap="4c7c19a2-be30db1e-de7d28ab-19269a64-64f55ca0-f309b4c5-b6ddbb81-86dcdd20",
  quote="", sa="", facts={},
  notes=("Re-read with textContent: 4,305 characters of DOM, zero pet terms, "
         "and the site carries no policy or terms navigation at all."))),

("cincinnati s fidelity hotel", _o(
  outcome="HOLD", triage="NO_FOUNDER_ACTION", surface="",
  platform="INDEPENDENT", name="Fidelity Hotel Cincinnati",
  sha="", shap="b0fd89ed-f3b8a445-d38528cf-dc3e7c26-599bb5b7-b05a4d63-d1d6551d-6bdcf877",
  quote="OPENING SUMMER 2026", sa="", facts={},
  hold_reason="PRE_OPENING",
  notes=("The property has not opened -- its own site says 'OPENING SUMMER "
         "2026'. A hotel with no guests has no pet policy to publish, so this "
         "is not a capture failure and should not sit in an acquisition queue "
         "as though it were one. 10,083 characters of DOM, zero pet terms."))),

("drury inn and suites cincinnati sharonville", _o(
  outcome="PUBLICATION_CANDIDATE", triage="FOUNDER_EXCEPTION",
  surface="EMBEDDED_JSON_PAYLOAD", platform="INDEPENDENT",
  name="Drury Inn & Suites Cincinnati Sharonville",
  sha="", shap="9c1408c5-2fab2673-c6915014-03d3187e-d50190c0-970e8bbb-ba98f23e-79f1f57d",
  quote=DRURY_QUOTE, sa="Service animals are free of charge.",
  facts=DRURY_FACTS, structured_flag="petsAllowed: http://schema.org/False",
  question=DRURY_QUESTION, notes=DRURY_NOTE)),

("drury inn and suites middletown franklin", _o(
  outcome="PUBLICATION_CANDIDATE", triage="FOUNDER_EXCEPTION",
  surface="EMBEDDED_JSON_PAYLOAD", platform="INDEPENDENT",
  name="Drury Inn & Suites Middletown Franklin",
  sha="", shap="d655dae2-d7f3083e-52522e23-8000d429-df7da68f-d2165857-3d7e379e-f61187c1",
  quote=DRURY_QUOTE, sa="Service animals are free of charge.",
  facts=DRURY_FACTS, structured_flag="petsAllowed: http://schema.org/False",
  question=DRURY_QUESTION, notes=DRURY_NOTE)),

("drury plaza hotel cincinnati florence", _o(
  outcome="PUBLICATION_CANDIDATE", triage="FOUNDER_EXCEPTION",
  surface="EMBEDDED_JSON_PAYLOAD", platform="INDEPENDENT",
  name="Drury Plaza Hotel Cincinnati Florence",
  sha="", shap="c594db29-47301cc0-798b2639-c8b11eb1-06977504-8d680a27-4aa05b38-7c246450",
  quote=DRURY_QUOTE, sa="Service animals are free of charge.",
  facts=DRURY_FACTS, structured_flag="petsAllowed: http://schema.org/False",
  question=DRURY_QUESTION, notes=DRURY_NOTE)),

("great wolf lodge cincinnati mason", _o(
  outcome="VERIFIED_NO_PETS", triage="CLEAN_VERIFIED_NO_PETS_CANDIDATE",
  surface="PROPERTY_FAQ_ACCORDION", platform="INDEPENDENT",
  name="Great Wolf Lodge Cincinnati/Mason",
  sha="afbef24c-8848bb71-bae2a1ca-5d1d7b14-4ad1e20a-d867b10f-5f5197b5-cae27d48",
  shap="71ff1c18-53b0ee43-cdd6773d-e95f47c1-a30c82d5-ba584d2b-ab942663-1924aa43",
  quote=("Are pets allowed? Service animals? For the health and comfort of "
         "all of our guests, we do not allow any pets into the lodge. If you "
         "would like information on a full service kennel in the Mason area, "
         "select the links below. Service animals as defined by the ADA are "
         "allowed in all areas of the resort. For the health and safety of "
         "our guests, service animals are not allowed in the pools and "
         "attractions of the water park."),
  sa=("Service animals as defined by the ADA are allowed in all areas of the "
      "resort. For the health and safety of our guests, service animals are "
      "not allowed in the pools and attractions of the water park."),
  facts={"pets_allowed": False},
  satisfies_hold=("PTF-CINCINNATI-FOUNDER-REVIEW-AND-APPLICATION-004 ruling "
                  "#2 HELD this row pending 'a property-specific prose "
                  "statement or equivalently clear first-party policy "
                  "surface'. This is that statement."),
  notes=("The founder declined a bare JSON-LD flag here and named the "
         "condition that would lift the hold. The condition is now met: the "
         "property's own /mason/faq answers the question in prose and refers "
         "guests to kennels in the Mason area, which binds it to this "
         "property. The page's JSON-LD, by contrast, carries a CORPORATE "
         "address in Chicago -- weaker than what was already refused, and not "
         "what this rests on. Applying it is a later order's decision; this "
         "pass only reports that the stated condition is satisfied."))),

("hillcrest motel", _o(
  outcome="POLICY_NOT_FOUND", triage="NO_FOUNDER_ACTION", surface="",
  platform="INDEPENDENT", name="Hillcrest Motel",
  sha="", shap="53d87124-5df8715c-3d04301c-50a162ca-cab53a52-c681ca38-1dd8dc12-f4b194d7",
  quote="", sa="", facts={},
  notes=("Homepage and /aboutus.php both read via textContent, 5,646 "
         "characters, zero pet terms. An earlier substring scan appeared to "
         "hit 'pet' here -- inside 'Com-pet-ition Racing Indoor Karting'. "
         "Word-boundary matching removes it."))),

("hollywood casino lawrenceburg", _o(
  outcome="VERIFIED_NO_PETS", triage="CLEAN_VERIFIED_NO_PETS_CANDIDATE",
  surface="HOUSE_RULES", platform="INDEPENDENT",
  name="Hollywood Casino Lawrenceburg Hotel",
  sha="7db4965e-900bad28-b07530b2-9d24b536-170e4084-0ea3473c-02603e5b-9b9dca69",
  shap="3ed62c28-8548e90e-5c1be38a-d6053856-f06ef570-384354d5-52689bb4-d319bd88",
  quote=("No pets are allowed except for service animals as defined by the "
         "Americans with Disabilities Act."),
  sa=("No pets are allowed except for service animals as defined by the "
      "Americans with Disabilities Act."),
  facts={"pets_allowed": False},
  notes=("In the hotel's own Hotel Policies block on its property page. This "
         "row is capturable only because APPLICATION-004 repointed its route "
         "to pennentertainment.com -- the earlier URL no longer resolved to "
         "the property."))),

("indigo pass", _o(
  outcome="POLICY_NOT_FOUND", triage="NO_FOUNDER_ACTION", surface="",
  platform="INDEPENDENT", name="Indigo Pass",
  sha="", shap="bea2e0a5-e5bb7226-b26fdffc-d28056e9-2bf5c24d-8c043bdd-7ec4956b-571b76c8",
  quote="", sa="", facts={},
  notes=("Homepage, /amenities/ and /about/ all read via textContent -- 9,187 "
         "characters at the deepest -- and none mentions pets."))),

("marcum hotel and conference center at miami university", _o(
  outcome="VERIFIED_NO_PETS", triage="CLEAN_VERIFIED_NO_PETS_CANDIDATE",
  surface="AMENITIES_LIST_HIDDEN_IN_DOM", platform="INDEPENDENT",
  name="The Marcum Hotel and Conference Center",
  sha="0cf7835a-592d0266-135972c6-b2a3c78f-0268b51d-e1ef353d-aca41098-d50d5962",
  shap="0128f4dc-f8d596fe-e836722d-b7e5f32a-3f21a599-47671a5d-e5c0ed49-c6eb785e",
  quote=("Only service animals as defined by the ADA are permitted, all other "
         "animals are prohibited"),
  sa=("Only service animals as defined by the ADA are permitted, all other "
      "animals are prohibited"),
  facts={"pets_allowed": False},
  notes=("In the property's own amenities list, present in the DOM but not in "
         "innerText -- 17,964 characters against 3,105 visible. The "
         "university's policy-library links in the footer are INSTITUTIONAL "
         "and were not read as this hotel's policy."))),

("the elms hotel", _o(
  outcome="VERIFIED_NO_PETS", triage="CLEAN_VERIFIED_NO_PETS_CANDIDATE",
  surface="AMENITIES_PAGE_MORE_INFO", platform="INDEPENDENT",
  name="The Elms Hotel", street="", city="Oxford",
  sha="a79133e4-b2914f2a-222d181b-42e17d2c-db9f0550-554469a0-637ffc90-b782ece6",
  shap="70436920-39a38064-70afa22b-74a58572-83e16b7f-058fc1d0-262b4cd9-2644845e",
  quote="No pets allowed except for service animals.",
  sa="No pets allowed except for service animals.",
  facts={"pets_allowed": False},
  notes=("On /amenities-oxford-ohio-elms-hotel, a page the routing URL does "
         "not point at -- the homepage says nothing about pets. Same locator "
         "shape as The Summit in PROBE-008."))),

("the warehouse hotel at champion mill", _o(
  outcome="PUBLICATION_CANDIDATE", triage="FOUNDER_EXCEPTION",
  surface="STAY_FAQ_HIDDEN_IN_DOM", platform="INDEPENDENT",
  name="The Warehouse Hotel at Champion Mill",
  sha="58da38ef-2bcbf4a1-06c80004-25a05241-5d844ff1-4633f3f2-b560860f-de254ecd",
  shap="6cc257a6-83d090db-41519454-a9617fa3-9bb671fb-e4f57d3b-b36ba789-fd70478f",
  quote=("DO YOU HAVE ANY PET-FRIENDLY ROOMS? Yes, we are now a pet-friendly "
         "hotel! A huge thank you to our sponsor at PetSuites for helping us "
         "stay a pet-friendly hotel. Cats & Dogs ONLY - 2 pets max, 60 lb "
         "weight limit. Limited to Standard Room types (King Sofa & 2 Queen "
         "Bed) There will be a fee of $50 per stay, any stay longer than 3 "
         "nights will require an additional $10/night."),
  sa="",
  facts={"pets_allowed": True,
         "pet_count_limit": 2,
         "species": {"dogs": "accepted", "cats": "accepted"}},
  question=("Three things need a ruling. (1) The base charge is $50 per STAY "
            "and a further $10 per NIGHT applies beyond three nights -- two "
            "charges with different bases, which APPLICATION-004 ruling 8 "
            "forbids collapsing. (2) Pets are 'Limited to Standard Room types "
            "(King Sofa & 2 Queen Bed)', and the schema's tier conditions are "
            "stay_length_range and pet_count_range only, so a room-type limit "
            "has nowhere to live -- the same problem as The Summit in "
            "PROBE-008. (3) '2 pets max, 60 lb weight limit' does not say "
            "whether 60 lb is per pet or combined, so the weight is withheld "
            "under the APPLICATION-004 unstated-scope rule. Species and pet "
            "count are unambiguous whatever you decide."),
  notes=("The row that exposed the method defect: this policy is in the DOM "
         "and not in innerText -- 149,578 characters against 2,419 visible."))),

("the well house hotel", _o(
  outcome="BRAND_CLASSIFICATION_STALE", triage="NO_FOUNDER_ACTION",
  surface="", platform="HILTON_PLATFORM",
  name="The Well House Hamilton, Tapestry Collection by Hilton",
  sha="", shap="22355d8c-6fe6f488-91a8f3a1-34308ca4-5f9e0230-e35de930-012a2c14-7b6c9522",
  quote="", sa="", facts={},
  brand_correction=OrderedDict((
    ("census_family", "INDEPENDENT"),
    ("observed_family", "HILTON"),
    ("first_party_evidence",
     "The property page's own h1 reads 'THE WELL HOUSE HAMILTON, TAPESTRY "
     "COLLECTION BY HILTON' and the page is served from hilton.com."),
    ("canonical_property_url",
     "https://www.hilton.com/en/hotels/lukmaup-the-well-house-hamilton/"),
    ("not_rewritten_here",
     "The family label is reported, not changed. A capture order does not "
     "edit identity authority."))),
  notes=("Belongs to the Hilton lane and its Bright Data pricing, not to the "
         "independent measurement. The routing URL also redirected from "
         "-the-well-house-hotel/ to -the-well-house-hamilton/. The only pet "
         "text on the page is a corporate 'Pet-Friendly Stays' footer link."))),
))


#: PROBE-008 rows this pass overturns or confirms. Carried explicitly so a
#: reader of the committed 008 artifact is not left with a wrong answer.
PROBE008_CORRECTIONS = OrderedDict((
 ("drury inn and suites cincinnati northeast mason", OrderedDict((
   ("was", "POLICY_NOT_FOUND"), ("now", "PUBLICATION_CANDIDATE"),
   ("triage", "FOUNDER_EXCEPTION"),
   ("why", "PROBE-008 read innerText and found no prose, then recorded the "
           "bare JSON-LD petsAllowed flag and stopped. The full policy is in "
           "an embedded JSON payload in the same page, readable via "
           "textContent. PROBE-008's commit claimed this 'settles the shape "
           "for all four' Cincinnati Drury properties; it did, but in the "
           "opposite direction -- all four are pet-friendly."),
   ("quote", DRURY_QUOTE),
   ("sha256_page",
    "48b3cbd2-3afafab5-4bc9ea1d-8bd2d1c0-a61a9661-c3ee4bbd-5e3bd155-e5ae4322"),
   ("sha256_policy_surface",
    "77b1317c-65011726-dd48162d-e9e58ce5-9ded8c0e-31a9c698-00828c42-e6dadc5e"),
   ("facts", DRURY_FACTS)))),
 ("wildwood inn", OrderedDict((
   ("was", "POLICY_NOT_FOUND"), ("now", "PUBLICATION_CANDIDATE"),
   ("triage", "FOUNDER_EXCEPTION"),
   ("why", "Same method defect. The statement is in the DOM and not in "
           "innerText -- 2,832 characters against 694 visible."),
   ("quote", "Explore the world at the Wildwood Inn! With African Safari "
             "style huts, 13 uniquely themed suites (including the Grand "
             "Canyon, Treehouse, Rome, and our Vintage Cars suites), 14 "
             "family style suites and an assortment of pet friendly rooms, "
             "you can experience something new every time."),
   ("sha256_page",
    "5c56e00d-169407ec-5133a1ad-cbd76e5c-4d1c3aaf-0e1d95e1-76290bc4-b842857b"),
   ("sha256_policy_surface",
    "206982d5-3af004f9-e0cff69e-615f57b9-267a4087-8fb77934-8fa872fd-7aa0a082"),
   ("facts", {"pets_allowed": True}),
   ("question_for_the_founder",
    "'an assortment of pet friendly rooms' states that pets are accepted and "
    "that only SOME rooms take them. It carries no fee, count, weight or "
    "species, and the room-type limit is the same thing the schema cannot "
    "express for The Summit and The Warehouse. Publish pets_allowed alone, or "
    "hold until the property states terms?")))),
 ("golden lamb", OrderedDict((
   ("was", "POLICY_NOT_FOUND"), ("now", "POLICY_NOT_FOUND"),
   ("why", "Re-read via textContent: 3,509 characters, still nothing. "
           "PROBE-008's answer was right, and is now right for a better "
           "reason.")))),
 ("symphony hotel and restaurant", OrderedDict((
   ("was", "POLICY_NOT_FOUND"), ("now", "POLICY_NOT_FOUND"),
   ("why", "Re-read via textContent: 5,416 characters, still nothing.")))),
))

LOCATORS = OrderedDict((
    ("druryhotels.com", "Embedded JSON payload in the page body -- and its "
                        "own JSON-LD contradicts it"),
    ("greatwolf.com", "Property FAQ accordion at /<property>/faq, readable "
                      "from the DOM without clicking"),
    ("pennentertainment.com", "Hotel Policies block on the property page"),
    ("miamioh.edu", "Property amenities list, present in DOM only"),
    ("theelmsoxford.com", "A separate /amenities page the routing URL misses"),
    ("warehousehotel.com", "A separate /stay-faq page, present in DOM only"),
    ("wildwoodinnky.com", "Homepage prose, present in DOM only"),
    ("budgethost.com", "Nothing"),
    ("chesterinnandsuites.com", "Nothing"),
    ("fidelityhotelcin.com", "Nothing -- the hotel has not opened"),
    ("hillcrestmotelaurora.com", "Nothing"),
    ("indigopasshotel.com", "Nothing"),
    ("hilton.com", "Not an independent; belongs to the Hilton lane"),
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
            ("census_family", row["census_family"]),
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
            ("quote", o["quote"]),
            ("sha256_policy_surface", o["sha"]),
            ("sha256_page", o["shap"]),
            ("facts", o["facts"]),
            ("notes", o["notes"]),
        ))
        for extra in ("structured_flag", "hold_reason", "satisfies_hold",
                      "brand_correction"):
            if o.get(extra):
                rec[extra] = o[extra]
        if o.get("sa"):
            rec["service_animal_statement"] = OrderedDict((("quote", o["sa"]),))
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
        ("method_defect_found",
         "Every prior Cincinnati sweep read innerText. The Warehouse Hotel's "
         "policy is in the DOM and not in innerText (149,578 characters "
         "against 2,419 visible), so this order re-read every row it had just "
         "called silent using textContent. Four more policies appeared, "
         "including on a template PROBE-008 declared settled. Substring "
         "matching on 'pet' also hits 'competition' and 'appetite'; every "
         "scan here uses word boundaries."),
        ("locators_by_domain", LOCATORS),
        ("probe_008_corrections", PROBE008_CORRECTIONS),
        ("rows", rows),
    ))


# --------------------------------- Phase 7: the consolidated independent lane

#: PROBE-008 rows that are NOT genuine independents and must never enter the
#: family measurement: three Choice-platform pages and the single ESA row.
NOT_INDEPENDENT_008 = ("country inn and suites airport",
                       "country inn and suites erlanger",
                       "radisson hotel cincinnati riverfront",
                       "studio 6 extended stay fairfield oh cincinnati")


def _genuine_independents(rows009):
    """Every genuine independent from PROBE-008 and PROBE-009, once each.

    PROBE-008's superseded rows carry their CORRECTED outcome -- measuring the
    lane on a reading this order proved wrong would understate it by two.
    """
    out = []
    for row in load(PROBE008_RESULTS)["rows"]:
        if row["identity_key"] in NOT_INDEPENDENT_008:
            continue
        row = OrderedDict(row)
        fix = PROBE008_CORRECTIONS.get(row["identity_key"])
        if fix and fix["now"] != fix["was"]:
            row["outcome"] = fix["now"]
            row["triage"] = fix["triage"]
            row["policy_surface_found"] = True
            row["quote"] = fix["quote"]
            row["facts"] = fix["facts"]
            row["superseded_by"] = WORK_ORDER
        row["source"] = "PTF-CINCINNATI-INDEPENDENT-FREE-PROBE-008"
        out.append(row)
    for row in rows009:
        if row["outcome"] == "BRAND_CLASSIFICATION_STALE":
            continue
        row = OrderedDict(row)
        row["source"] = WORK_ORDER
        out.append(row)
    keys = [r["identity_key"] for r in out]
    if len(keys) != len(set(keys)):
        raise RuntimeError("a row was counted twice in the lane measurement")
    return out


def build_measurement(rows009):
    lane = _genuine_independents(rows009)
    stats = measure(lane)
    verdict, why = final_recommendation(stats)
    domains = Counter(r["official_domain"] for r in lane)
    yielding = sorted({r["official_domain"] for r in lane
                       if r["policy_surface_found"]})
    return OrderedDict((
        ("work_order", WORK_ORDER),
        ("what", "Genuine independent-domain properties only, from PROBE-008 "
                 "and PROBE-009 combined, each counted once. Excludes the "
                 "three Choice-platform rows and the ESA row PROBE-008 "
                 "measured, and the Hilton row PROBE-009 found."),
        ("excluded_from_the_lane", OrderedDict((
            ("choice_platform_mislabelled", 3),
            ("esa", 1),
            ("brand_classification_stale_hilton", 1)))),
        ("corrections_applied",
         "Two PROBE-008 rows carry their corrected outcome here. Measuring "
         "the lane on readings this order proved wrong would understate it."),
        ("stats", stats),
        ("distinct_domains", len(domains)),
        ("rows_per_domain", OrderedDict(sorted(domains.items()))),
        ("domains_yielding_publication_grade", yielding),
        ("FINAL_RECOMMENDATION", verdict),
        ("because", why),
        ("no_further_probe",
         "This order was instructed not to recommend another probe, and does "
         "not. Two passes over one family is where measurement stops being "
         "cheap and starts being avoidance."),
        ("rows", lane),
    ))


# -------------------------------- Phase 9: the consolidated pending inventory

def build_pending(rows009):
    """Everything PROBE-008 and PROBE-009 found, waiting on an application.

    Nothing here is approved. It exists so that two orders' worth of free
    evidence is not stranded in artifacts nobody reads.
    """
    buckets = OrderedDict((("CLEAN_PET_FRIENDLY", []),
                           ("CLEAN_VERIFIED_NO_PETS", []),
                           ("FOUNDER_EXCEPTION", []),
                           ("NO_AUTHORITY_ACTION", [])))
    lane = {"CLEAN_PET_FRIENDLY_CANDIDATE": "CLEAN_PET_FRIENDLY",
            "CLEAN_VERIFIED_NO_PETS_CANDIDATE": "CLEAN_VERIFIED_NO_PETS",
            "FOUNDER_EXCEPTION": "FOUNDER_EXCEPTION",
            "NO_FOUNDER_ACTION": "NO_AUTHORITY_ACTION"}

    def add(row, source):
        fix = PROBE008_CORRECTIONS.get(row["identity_key"])
        corrected = source.endswith("008") and fix and fix["now"] != fix["was"]
        triage = fix["triage"] if corrected else row["triage"]
        entry = OrderedDict((
            ("identity_key", row["identity_key"]),
            ("property", row.get("canonical_name", "")),
            ("source", source),
            ("outcome", fix["now"] if (source.endswith("008") and fix)
             else row["outcome"]),
            ("official_property_url", row["official_property_url"]),
            ("quote", fix["quote"] if corrected else row["quote"]),
            ("sha256_page", row["sha256_page"]),
            ("founder_decision", ""), ("founder_reviewer_id", ""),
        ))
        if corrected:
            entry["supersedes"] = "%s recorded %s" % (source, fix["was"])
        if row.get("question_for_the_founder"):
            entry["issue"] = row["question_for_the_founder"]
        elif corrected and fix.get("question_for_the_founder"):
            entry["issue"] = fix["question_for_the_founder"]
        elif corrected:
            entry["issue"] = DRURY_QUESTION
        if row.get("satisfies_hold"):
            entry["satisfies_prior_hold"] = row["satisfies_hold"]
        buckets[lane[triage]].append(entry)

    for row in load(PROBE008_RESULTS)["rows"]:
        add(row, "PTF-CINCINNATI-INDEPENDENT-FREE-PROBE-008")
    for row in rows009:
        add(row, WORK_ORDER)

    return OrderedDict((
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("note", "Proposed only. No approval field is set and no authority "
                 "was touched. Carried forward so PROBE-008's work is not "
                 "stranded."),
        ("counts", OrderedDict((k, len(v)) for k, v in buckets.items())),
        ("buckets", buckets),
    ))


# --------------------------------------------------------- Phase 10: reprice

BRIGHTDATA_USD_PER_ATTEMPT = 0.197

LANE_OF_FAMILY = {
    "MARRIOTT": "BRIGHT_DATA",
    "HILTON": "BRIGHT_DATA",
    "IHG": "ATTENDED_CHROME_FREE_CLOSED",
    "CHOICE": "ATTENDED_CHROME_FREE_CLOSED",
    "HYATT": "BLOCKED_BY_ADR",
    "INDEPENDENT": "FREE_SITE_BY_SITE",
    "ESA": "FREE_SITE_BY_SITE",
}


def build_reprice(rows009):
    """What is left, and what two free probes changed about how it is priced.

    Independents are now MEASURED, not unproven and not partial: 19 of 19
    reachable, 12 of 19 publishing. The seven that do not publish are silent,
    and a paid provider cannot fetch text a hotel never wrote -- so no part of
    this family belongs in a paid estimate, whatever its yield.
    """
    routes = load(ROUTING)["routes"]
    state = {i["identity_key"]: i["final_state"]
             for i in load(PARTITION)["items"]}
    routed = {r["hotel_ref"]["identity_key"] for r in routes}

    lane_rows = build_measurement(rows009)["rows"]
    answered = {r["identity_key"] for r in lane_rows
                if r["policy_surface_found"]}
    silent = {r["identity_key"] for r in lane_rows
              if r["outcome"] in ("POLICY_NOT_FOUND", "HOLD")}
    stale_brand = {r["identity_key"] for r in rows009
                   if r["outcome"] == "BRAND_CLASSIFICATION_STALE"}

    by_family, pending, empty = Counter(), Counter(), Counter()
    for route in routes:
        key = route["hotel_ref"]["identity_key"]
        if state.get(key) in RESOLVED:
            continue
        family = route.get("brand") or "UNKNOWN"
        if key in stale_brand:
            family = "HILTON"          # observed, though not rewritten
        by_family[family] += 1
        if key in answered:
            pending[family] += 1
        if key in silent:
            empty[family] += 1

    unrouted = sorted(k for k, v in state.items()
                      if v not in RESOLVED and k not in routed)
    by_state = Counter(state[k] for k in unrouted)

    lanes = OrderedDict()
    for family, n in sorted(by_family.items()):
        name = LANE_OF_FAMILY.get(family, "FREE_SITE_BY_SITE")
        row = lanes.setdefault(name, OrderedDict((
            ("families", OrderedDict()), ("rows", 0),
            ("evidence_captured_pending_application", 0),
            ("observed_silent", 0))))
        row["families"][family] = n
        row["rows"] += n
        row["evidence_captured_pending_application"] += pending[family]
        row["observed_silent"] += empty[family]

    bd = lanes.get("BRIGHT_DATA", {}).get("rows", 0)
    return OrderedDict((
        ("work_order", WORK_ORDER),
        ("basis", "the routing shard and partition at dda2239; no authority "
                  "was applied by this order"),
        ("unresolved_total", sum(1 for v in state.values()
                                 if v not in RESOLVED)),
        ("unresolved_routed", sum(by_family.values())),
        ("unresolved_unrouted", len(unrouted)),
        ("unrouted_by_state", OrderedDict(sorted(by_state.items()))),
        ("by_family_observed", OrderedDict(sorted(by_family.items()))),
        ("brand_classification_stale", OrderedDict((
            ("count", len(stale_brand)),
            ("rows", sorted(stale_brand)),
            ("note", "Counted under the family the property page proves, not "
                     "the one the shard states. The shard was NOT rewritten "
                     "-- a capture order does not edit identity authority.")))),
        ("lanes", lanes),
        ("firecrawl", OrderedDict((
            ("rows", 0), ("projected_usd", 0.0),
            ("why", "Nothing in current state produces a qualified need. IHG "
                    "and Choice closed free; Marriott and Hilton are "
                    "unreachable to Firecrawl; and the independents' "
                    "remaining problem is unpublished policy, which no "
                    "provider fixes.")))),
        ("bright_data", OrderedDict((
            ("rows", bd), ("usd_per_attempt", BRIGHTDATA_USD_PER_ATTEMPT),
            ("projected_usd", round(bd * BRIGHTDATA_USD_PER_ATTEMPT, 2)),
            ("note", "Marriott and Hilton only. The independents are not "
                     "here at any yield: their failures are silence.")))),
        ("free_attended", OrderedDict((
            ("evidence_captured_pending_application", len(answered)),
            ("observed_silent_or_pre_opening", len(silent)),
            ("remaining_site_by_site_opportunities", 0),
            ("note", "Every routed Independent/ESA row in this market has now "
                     "been observed across PROBE-008 and PROBE-009. There are "
                     "no unobserved independents left to sweep.")))),
        ("spend_this_order_usd", 0.0),
        ("note", "An estimate, not an authorization. Nothing here spends."),
    ))
