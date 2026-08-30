# -*- coding: utf-8 -*-
"""PTF-CINCINNATI-FREE-LANE-SCALE-006 -- the 32 attended observations.

Observed 2026-08-29 in attended Chrome. No provider, no spend, no authority.

One lane-level finding shapes half the exceptions below and is worth stating
once rather than thirty-two times: IHG's structured pet-policy field is always
labelled **"Pet fee per night: <X> USD"** regardless of what the property's own
prose says the basis is. Holiday Inn Cincinnati Airport states "75.00 USD per
stay" in prose and "Pet fee per night: 75 USD" in the structured field, in the
same panel. Candlewood Erlanger states a 1-6 night tier in prose and the same
number as a nightly rate in the field. Holiday Inn Express Mason states 75/125
stay-length tiers and the field reports 125 as the nightly rate.

So the structured field's BASIS is template boilerplate and may not be read.
Its AMOUNT is corroborative; only the prose states the basis. Where the two
disagree the row is a founder exception, on the PTF-...-APPLICATION-004
Homewood Mason precedent: a page that says two things publishes neither until
a founder rules.

The one row where the field and the prose agree -- Holiday Inn Cincinnati
Riverfront, "a flat nonrefundable fee of 25 USD per night" -- is clean, which
is what makes this a real finding rather than a blanket suspicion of the field.
"""

from __future__ import annotations

import re
from collections import OrderedDict

from scripts.pettripfinder.cincinnati_free_lane_scale_006 import (
    CAPTURE_METHOD, CLEAN_NP, CLEAN_PF, COHORT, LANE, MARKET_ID, OBSERVED_ON,
    PACKET, REPRICE, RESULTS, WORK_ORDER, build_final_measurement,
    build_reprice, measure)
from scripts.pettripfinder.cincinnati_free_brand_probe_005 import load, render
from scripts.pettripfinder.cincinnati_free_lane_scale_006 import PROBE_RESULTS

STRUCTURED_FIELD_BASIS_IS_BOILERPLATE = (
    "IHG's structured 'Pet fee per night' label is emitted regardless of the "
    "basis the property's prose states. The amount corroborates; the basis "
    "does not. Where field and prose disagree the row is a founder exception.")


def _o(**kw):
    return kw


#: identity_key -> observation, in cohort order.
OBS = {

# ---------------------------------------------------------------- CHOICE (13)

"comfort inn and suites greendale": _o(
  outcome="PUBLICATION_CANDIDATE", triage="CLEAN_PET_FRIENDLY_CANDIDATE",
  surface="ESSENTIAL_DETAILS_PETS_BLOCK",
  name="Comfort Inn & Suites Lawrenceburg", street="1610 Flossie Drive",
  city="Lawrenceburg", state="IN", postal="47025", tel="8125393600",
  sha="da513f2b-e4b0bc2f-488cbb2d-de453a9c-41766b5e-e95c8b46-62597021-24f62e4a",
  shap="4c8e7cf3-1fc6c7d8-bc66bf23-5ddab2a0-9102dff7-c7e942c9-632e79b3-1fb0a2ef",
  quote=("Pets Allowed: Yes General: Pet Accommodation: 25.00 USD per night "
         "per pet. Pet Limit: up to 20 lbs. 2 Pets per room and not more than "
         "5 days at a time, we do not allow pets in our Kitchenette suite or "
         "our 2 room suite.. Service animals are permitted, without charge."),
  sa="Service animals are permitted, without charge.",
  facts={"pets_allowed": True,
         "pet_fee": {"amount_cents": 2500, "basis": "per_night",
                     "scope": "per_pet"},
         "weight_limit": {"value": 20, "unit": "lb", "operator": "lte",
                          "scope": "per_pet"},
         "pet_count_limit": 2},
  diffs=["name: page states 'Comfort Inn & Suites Lawrenceburg', census "
         "states 'Comfort Inn & Suites Greendale'"],
  diff_kind="rename_or_naming",
  notes=("Street, postal and phone bind exactly. Greendale and Lawrenceburg "
         "are adjacent Indiana towns and the property has taken the larger "
         "one's name. The max-5-day stay limit and the room-type exclusions "
         "are carried verbatim rather than dropped -- the Days Inn Florence "
         "ruling in APPLICATION-004 is the precedent for carrying a stay cap "
         "in the property's own words.")),

"comfort inn and suites west chester": _o(
  outcome="VERIFIED_NO_PETS", triage="CLEAN_VERIFIED_NO_PETS_CANDIDATE",
  surface="ESSENTIAL_DETAILS_PETS_BLOCK",
  name="Comfort Inn & Suites West Chester - North Cincinnati",
  street="5944 West Chester Rd.", city="West Chester", state="OH",
  postal="45069", tel="5137950061",
  sha="ede4ede9-fbe37a4f-b8cf273b-37215e88-baee23af-ce1fe2f7-ec52e303-3ce07b81",
  shap="6a548c8a-62b181e3-a889ab58-9f426d63-a4995f68-1664b9d5-2b34861e-514146b0",
  quote=("Pets Allowed: No General: Only service animals are permitted, free "
         "of charge."),
  sa="Only service animals are permitted, free of charge.",
  facts={"pets_allowed": False}, diffs=[], diff_kind="",
  notes="Street and postal bind exactly; the census carries no phone."),

"comfort inn and suites wilder": _o(
  outcome="VERIFIED_NO_PETS", triage="CLEAN_VERIFIED_NO_PETS_CANDIDATE",
  surface="ESSENTIAL_DETAILS_PETS_BLOCK",
  name="Comfort Inn & Suites Northern Kentucky", street="10 Country Drive",
  city="Wilder", state="KY", postal="41076", tel="8594413707",
  sha="ede4ede9-fbe37a4f-b8cf273b-37215e88-baee23af-ce1fe2f7-ec52e303-3ce07b81",
  shap="27093c3e-bf2dd340-af5e46c6-9bf42712-dcd38143-e3fe1a9c-64b1faad-fd9d5332",
  quote=("Pets Allowed: No General: Only service animals are permitted, free "
         "of charge."),
  sa="Only service animals are permitted, free of charge.",
  facts={"pets_allowed": False},
  diffs=["name: page states 'Comfort Inn & Suites Northern Kentucky', census "
         "states 'Comfort Inn & Suites Wilder'"],
  diff_kind="rename_or_naming",
  notes="Street, postal and phone bind exactly. The property has taken a "
        "regional name in place of its town name."),

"comfort inn blue ash": _o(
  outcome="VERIFIED_NO_PETS", triage="CLEAN_VERIFIED_NO_PETS_CANDIDATE",
  surface="ESSENTIAL_DETAILS_PETS_BLOCK",
  name="Comfort Inn Blue Ash North", street="4640 Creek Road", city="Blue Ash",
  state="OH", postal="45242", tel="5137131966",
  sha="ede4ede9-fbe37a4f-b8cf273b-37215e88-baee23af-ce1fe2f7-ec52e303-3ce07b81",
  shap="20826c7f-368e6355-48ba0537-9cff931c-5e6c077b-1b9099eb-af51f39d-9b25bd4b",
  quote=("Pets Allowed: No General: Only service animals are permitted, free "
         "of charge."),
  sa="Only service animals are permitted, free of charge.",
  facts={"pets_allowed": False},
  diffs=["phone: page states 5137131966, census states 5137913156"],
  diff_kind="stale_census",
  notes=("Street and postal bind exactly and the page name is the census name "
         "plus 'North'. Recorded, not corrected.")),

"comfort inn northeast": _o(
  outcome="VERIFIED_NO_PETS", triage="CLEAN_VERIFIED_NO_PETS_CANDIDATE",
  surface="ESSENTIAL_DETAILS_PETS_BLOCK",
  name="Comfort Inn Cincinnati Northeast", street="9011 Fields Ertel Rd.",
  city="Cincinnati", state="OH", postal="45249", tel="5136839700",
  sha="ede4ede9-fbe37a4f-b8cf273b-37215e88-baee23af-ce1fe2f7-ec52e303-3ce07b81",
  shap="76a0a402-c68c15f4-ec52c841-17eee845-c88fd8ad-b4c98de3-7ebddf21-970fe42a",
  quote=("Pets Allowed: No General: Only service animals are permitted, free "
         "of charge."),
  sa="Only service animals are permitted, free of charge.",
  facts={"pets_allowed": False}, diffs=[], diff_kind="",
  notes="Street, postal and phone all bind exactly."),

"comfort inn oxford": _o(
  outcome="VERIFIED_NO_PETS", triage="CLEAN_VERIFIED_NO_PETS_CANDIDATE",
  surface="ESSENTIAL_DETAILS_PETS_BLOCK",
  name="Comfort Inn Oxford - University Area",
  street="5056 College Corner Pike", city="Oxford", state="OH",
  postal="45056", tel="5135240114",
  sha="ede4ede9-fbe37a4f-b8cf273b-37215e88-baee23af-ce1fe2f7-ec52e303-3ce07b81",
  shap="850df6b8-cbbe8c08-b5d9b40f-2f895699-fcc2f96a-07f9db7a-4a898c89-41425922",
  quote=("Pets Allowed: No General: Only service animals are permitted, free "
         "of charge."),
  sa="Only service animals are permitted, free of charge.",
  facts={"pets_allowed": False}, diffs=[], diff_kind="",
  notes=("Street and postal bind exactly. Sleep Inn & Suites Oxford sits at "
         "5190 on the same road and is a separate identity in this cohort; "
         "neither was normalised toward the other.")),

"comfort suites mainstay hotel": _o(
  outcome="VERIFIED_NO_PETS", triage="FOUNDER_EXCEPTION",
  surface="ESSENTIAL_DETAILS_PETS_BLOCK",
  name="MainStay Suites Cincinnati University - Uptown",
  street="2347 Reading Road, Building B", city="Cincinnati", state="OH",
  postal="45202", tel="5132023971",
  sha="ede4ede9-fbe37a4f-b8cf273b-37215e88-baee23af-ce1fe2f7-ec52e303-3ce07b81",
  shap="17ca81a9-f25db4aa-7564470c-050203c6-aac976bd-47c74bdc-9b550706-6009d257",
  quote=("Pets Allowed: No General: Only service animals are permitted, free "
         "of charge."),
  sa="Only service animals are permitted, free of charge.",
  facts={"pets_allowed": False},
  diffs=["name: page states 'MainStay Suites Cincinnati University - Uptown', "
         "census states 'Comfort Suites Mainstay Hotel'",
         "postal_code: page states 45202, census states 45219",
         "phone: page states 5132023971, census states 5133946073"],
  diff_kind="unresolved",
  question=("Three of four identity signals disagree: the name, the postal "
            "code (45202 vs 45219) and the phone. Only the street number "
            "matches, and the page qualifies it as 'Building B'. Reading Road "
            "runs through both ZIPs, so this is either one property that was "
            "rebranded and re-addressed, or two buildings on the same road. "
            "Is this the same identity? A refusal registered against the "
            "wrong building is a public statement about a hotel that never "
            "made it."),
  notes=("The policy reading is clean and unambiguous; the identity is not. "
         "The census name pairs two Choice brands -- 'Comfort Suites' and "
         "'Mainstay' -- which is itself a sign the census row was never "
         "cleanly resolved.")),

"quality inn and suites florence": _o(
  outcome="PUBLICATION_CANDIDATE", triage="CLEAN_PET_FRIENDLY_CANDIDATE",
  surface="ESSENTIAL_DETAILS_PETS_BLOCK",
  name="Quality Inn & Suites Florence - Cincinnati South",
  street="30 Cavalier Blvd.", city="Florence", state="KY", postal="41042",
  tel="8593710081",
  sha="8f057a06-a90145b1-c8c4f699-5265a6f3-2d430197-990b1769-abfdf82c-4c2a4f3e",
  shap="c907c21b-b53bccea-2187d465-68263ce9-1df28f76-5cb22f90-a55b6c77-4e757ecc",
  quote=("Pets Allowed: Yes General: Pets allowed. 25.00 USD per pet, per "
         "night and a maximum of 20 pounds per pet.. Service animals are "
         "permitted, without charge."),
  sa="Service animals are permitted, without charge.",
  facts={"pets_allowed": True,
         "pet_fee": {"amount_cents": 2500, "basis": "per_night",
                     "scope": "per_pet"},
         "weight_limit": {"value": 20, "unit": "lb", "operator": "lte",
                          "scope": "per_pet"}},
  diffs=["street: page states 30 Cavalier Blvd., census states "
         "30 Cavalier Court"],
  diff_kind="stale_census",
  notes=("Phone and postal bind exactly and the route's property code ky203 "
         "is the page served. The street TYPE differs; the number does not. "
         "Recorded rather than corrected -- Detroit 012 turned on a phone "
         "separating two brands at one address, and here the phone is the "
         "signal that agrees.")),

"quality inn and suites lawrenceburg": _o(
  outcome="PUBLICATION_CANDIDATE", triage="CLEAN_PET_FRIENDLY_CANDIDATE",
  surface="ESSENTIAL_DETAILS_PETS_BLOCK",
  name="Quality Inn & Suites Lawrenceburg", street="765 E Eads Parkway",
  city="Lawrenceburg", state="IN", postal="47025", tel="8122211018",
  sha="8a22b6f9-eec5bf49-690a9db5-d79d391d-30dc3826-ba72f382-9113af0e-ca0da880",
  shap="79d2d83b-e718bb36-74c4f4bd-d7a62d30-8627a512-d643a440-2c1dbfd2-7991dda9",
  quote=("Pets Allowed: Yes General: Only dogs under 25lbs are accepted. "
         "25.00 USD per pet, per night. A limit of 2 pets per room.. Service "
         "animals are permitted, without charge."),
  sa="Service animals are permitted, without charge.",
  facts={"pets_allowed": True,
         "pet_fee": {"amount_cents": 2500, "basis": "per_night",
                     "scope": "per_pet"},
         "weight_limit": {"value": 25, "unit": "lb", "operator": "lt",
                          "scope": "per_pet"},
         "pet_count_limit": 2,
         "species": {"dogs": "accepted", "cats": "prohibited"}},
  diffs=["phone: page states 8122211018, census states 8125372552"],
  diff_kind="stale_census",
  notes=("'under 25lbs' is a STRICT bound -- operator lt, not lte. A 25lb dog "
         "does not qualify and must not be told it does. 'Only dogs' is an "
         "affirmative exclusion of cats.")),

"quality inn and suites middletown": _o(
  outcome="PUBLICATION_CANDIDATE", triage="CLEAN_PET_FRIENDLY_CANDIDATE",
  surface="ESSENTIAL_DETAILS_PETS_BLOCK",
  name="Quality Inn & Suites Middletown - Franklin",
  street="6475 Culbertson Road", city="Franklin", state="OH", postal="45005",
  tel="5134243551",
  sha="910c3027-9004d34f-283aca39-41938fdf-db71ec46-42093b30-b355086f-85d33068",
  shap="2fff65bf-e9f82525-ef4f375f-46d25a87-0f818531-72fa52ad-39436a2c-95bde259",
  quote=("Pets Allowed: Yes General: Pets are allowed. The pet accommodation "
         "is 25.00 USD per night per pet. A maximum size limit of 20 pounds "
         "per pet with a maximum limit of 2 pets per room.. Service animals "
         "are permitted, without charge."),
  sa="Service animals are permitted, without charge.",
  facts={"pets_allowed": True,
         "pet_fee": {"amount_cents": 2500, "basis": "per_night",
                     "scope": "per_pet"},
         "weight_limit": {"value": 20, "unit": "lb", "operator": "lte",
                          "scope": "per_pet"},
         "pet_count_limit": 2},
  diffs=[], diff_kind="",
  notes="Street and postal bind exactly; the census carries no phone."),

"rodeway inn florence": _o(
  outcome="VERIFIED_NO_PETS", triage="CLEAN_VERIFIED_NO_PETS_CANDIDATE",
  surface="ESSENTIAL_DETAILS_PETS_BLOCK",
  name="Rodeway Inn Florence - Cincinnati South", street="7928 Dream Street",
  city="Florence", state="KY", postal="41042", tel="8592831221",
  sha="ede4ede9-fbe37a4f-b8cf273b-37215e88-baee23af-ce1fe2f7-ec52e303-3ce07b81",
  shap="68838bee-94845b1f-e0fac949-5e2974f8-4535520f-fd6a6b51-2721e89b-256e54fe",
  quote=("Pets Allowed: No General: Only service animals are permitted, free "
         "of charge."),
  sa="Only service animals are permitted, free of charge.",
  facts={"pets_allowed": False}, diffs=[], diff_kind="",
  notes="Street, postal and phone all bind exactly."),

"sleep inn and suites oxford": _o(
  outcome="VERIFIED_NO_PETS", triage="CLEAN_VERIFIED_NO_PETS_CANDIDATE",
  surface="ESSENTIAL_DETAILS_PETS_BLOCK",
  name="Sleep Inn & Suites - Oxford - University Area",
  street="5190 College Corner Pike", city="Oxford", state="OH",
  postal="45056", tel="5132024652",
  sha="536fb2bb-14e17806-e8f776d6-5d656cdd-40f9efd9-b0a35894-723f6219-4959c693",
  shap="683317d5-55c0e663-dd8cde44-31da46e4-869017fd-6344dca4-9041b752-fb324615",
  quote="Pets Allowed: No.",
  sa="Only service animals are permitted, free of charge.",
  facts={"pets_allowed": False}, diffs=[], diff_kind="",
  notes=("This page renders the refusal in a tighter node than its siblings, "
         "so its surface digest does not collide with theirs. The property's "
         "own hotel alert repeats it in full: 'Pets Allowed: No. Only service "
         "animals are permitted, free of charge.'")),

"the blu hotel ascend hotel collection": _o(
  outcome="VERIFIED_NO_PETS", triage="CLEAN_VERIFIED_NO_PETS_CANDIDATE",
  surface="ESSENTIAL_DETAILS_PETS_BLOCK",
  name="The Blu Hotel Blue Ash Cincinnati, an Ascend Collection Hotel",
  street="11349 Reed Hartman Hwy.", city="Blue Ash", state="OH",
  postal="45241", tel="5135305999",
  sha="ede4ede9-fbe37a4f-b8cf273b-37215e88-baee23af-ce1fe2f7-ec52e303-3ce07b81",
  shap="11410ab7-7d4e0c90-45102460-4d9bc5ee-bd6e6919-48f9cda8-188127ae-0c0ed52a",
  quote=("Pets Allowed: No General: Only service animals are permitted, free "
         "of charge."),
  sa="Only service animals are permitted, free of charge.",
  facts={"pets_allowed": False}, diffs=[], diff_kind="",
  notes="Street, postal and phone all bind exactly."),

# ------------------------------------------------------------------- IHG (19)

"candlewood suites erlanger south cincinnati": _o(
  outcome="PUBLICATION_CANDIDATE", triage="FOUNDER_EXCEPTION",
  surface="PROPERTY_FAQ_PANEL",
  name="Candlewood Suites Erlanger - South Cincinnati",
  street="602 Atlas Air Way", city="Erlanger", state="KY", postal="41018",
  tel="18599009500",
  sha="081bf818-c287cc9b-b91257ca-405bfe17-d058fd33-3aa63bfc-2e66f947-2b1877ab",
  shap="08a6c23d-96620806-b2303fd9-7b1e8375-c4512173-219e920f-d1b02f7b-fe8553f1",
  quote=("Pets are welcome at Candlewood Suites Erlanger - South Cincinnati. "
         "Pet policy description. A nonrefundable pet fee applies. 75 USD for "
         "one to six nights, 150 USD for seven or more nights. Up to two pets "
         "no more than 80 pounds. A pet agreement must be signed at check in. "
         "Pets allowed are dogs only. Pet fee per night: 75 USD Pet weight "
         "limit: 80 2 pets allowed Pets allowed: Only dogs allowed"),
  sa="", facts={"pets_allowed": True}, diffs=[], diff_kind="",
  question=("The prose states stay-length tiers -- 75 USD for one to six "
            "nights, 150 USD for seven or more -- while the structured field "
            "on the same panel reports 'Pet fee per night: 75 USD'. Publish "
            "75 as a stay-length tier headline with the 150 tier beside it, "
            "and withhold the nightly reading? On the Homewood Mason "
            "precedent a page that says two things publishes neither until "
            "you rule."),
  notes="Street, postal and phone bind exactly. Dogs only, 2 pets, 80 lb."),

"holiday inn cincinnati airport": _o(
  outcome="PUBLICATION_CANDIDATE", triage="FOUNDER_EXCEPTION",
  surface="PROPERTY_FAQ_PANEL", name="Holiday Inn Cincinnati Airport",
  street="1717 Airport Exchange Blvd.", city="Erlanger", state="KY",
  postal="41018", tel="18593712233",
  sha="369ae58a-7ffdb541-d5fdc232-43ca6407-df129575-4979d654-d29d3ad4-1b654115",
  shap="a02edf74-9f0bc756-7d175293-7572a4dc-a4131564-81fad421-8e55bd81-59f45fd8",
  quote=("Pets are welcome at Holiday Inn Cincinnati Airport. Pet policy "
         "description. Pets are welcome at our hotel for a 75.00 USD per stay "
         "in addition to the regular guest room rate. Only 2 total pets are "
         "allowed per room. Pet fee per night: 75 USD Pet weight limit: 75 "
         "2 pets allowed Pets allowed: Only dogs and cats allowed"),
  sa="", facts={"pets_allowed": True}, diffs=[], diff_kind="",
  question=("The sharpest instance of the template defect: the prose says "
            "'75.00 USD per STAY' and the structured field on the same panel "
            "says 'Pet fee per NIGHT: 75 USD'. Same amount, opposite basis. "
            "For a seven-night stay these differ by 450 USD. Publish 75 USD "
            "per stay on the prose, or withhold the fee entirely?"),
  notes="Street, postal and phone bind exactly. 2 pets, 75 lb, dogs and cats."),

"holiday inn cincinnati north west chester": _o(
  outcome="VERIFIED_NO_PETS", triage="CLEAN_VERIFIED_NO_PETS_CANDIDATE",
  surface="PROPERTY_FAQ_PANEL", name="Holiday Inn Cincinnati N - West Chester",
  street="5800 Muhlhauser Road", city="West Chester", state="OH",
  postal="45069", tel="15138742744",
  sha="c9998cde-847582e9-2abcb8a2-782d935a-93a1c509-57810f93-817762a8-f8586331",
  shap="2d9b3738-772c086f-e8c18b0f-2ef9a7e2-2a8d14b8-a1171767-07797450-2937183d",
  quote="No, pets are not allowed at Holiday Inn Cincinnati N - West Chester.",
  sa="", facts={"pets_allowed": False}, diffs=[], diff_kind="",
  notes="Affirmative refusal naming the hotel. Street and postal bind exactly."),

"holiday inn cincinnati riverfront": _o(
  outcome="PUBLICATION_CANDIDATE", triage="CLEAN_PET_FRIENDLY_CANDIDATE",
  surface="PROPERTY_FAQ_PANEL", name="Holiday Inn Cincinnati-Riverfront",
  street="600 W Third Street", city="Covington", state="KY", postal="41011",
  tel="18592914300",
  sha="6f969033-3735eda8-98e3edab-f1ddab4d-5b23468b-5e53c3f0-0f88362e-3f5f8bbf",
  shap="23f85ded-f3da7af4-75ce0309-c9b4c97a-82c478f2-54c8477f-933e77b7-9161450f",
  quote=("Pets are welcome at Holiday Inn Cincinnati-Riverfront. Pet policy "
         "description. The hotel allows up to 2 pets in the room for a flat "
         "nonrefundable fee of 25 USD per night. No fees for service animals "
         "for the disabled. Pet must be kenneled when left unattended. Pet "
         "fee per night: 25 USD Pet weight limit: 75 2 pets allowed Pets "
         "allowed: Only dogs and cats allowed"),
  sa="No fees for service animals for the disabled.",
  facts={"pets_allowed": True,
         "pet_fee": {"amount_cents": 2500, "basis": "per_night",
                     "scope": "per_room", "refundable_stated": False},
         "weight_limit": {"value": 75, "unit": "lb", "operator": "lte",
                          "scope": "per_pet"},
         "pet_count_limit": 2,
         "species": {"dogs": "accepted", "cats": "accepted"},
         "unattended_policy": "Pet must be kenneled when left unattended."},
  diffs=[], diff_kind="",
  notes=("The one row in this cohort where the structured field and the prose "
         "AGREE on the basis -- both say per night -- which is what makes the "
         "template finding a real observation rather than a blanket "
         "suspicion. 'a flat ... fee ... for up to 2 pets in the room' is "
         "per_room, not per_pet.")),

"holiday inn express and suites cincinnati ne red bank road": _o(
  outcome="VERIFIED_NO_PETS", triage="CLEAN_VERIFIED_NO_PETS_CANDIDATE",
  surface="PROPERTY_FAQ_PANEL",
  name="Holiday Inn Express & Suites Cincinnati NE - Redbank Road",
  street="5311 Hetzell Street", city="Cincinnati", state="OH", postal="45227",
  tel="15138349191",
  sha="4c7300e5-245d8586-a1b32c59-aba36aea-f3ca9616-32a0efec-a0acf3d2-1eb8c47d",
  shap="e7cf98b4-558006cd-366d6f0f-43c442ac-6ec21672-306d115b-39fcff25-a6c7dd9a",
  quote=("No, pets are not allowed at Holiday Inn Express & Suites "
         "Cincinnati NE - Redbank Road."),
  sa="", facts={"pets_allowed": False},
  diffs=["street: page states 5311 Hetzell Street, census states "
         "5311 Hetzell Rd."],
  diff_kind="stale_census",
  notes=("Number, postal and phone bind exactly; the street TYPE differs and "
         "the property's own page is the authority for it. Caught by the "
         "no-difference check rather than by eye -- which is the point of "
         "asserting that 'no difference recorded' actually means the two "
         "agree, not merely that nobody looked.")),

"holiday inn express and suites cincinnati northeast milford": _o(
  outcome="VERIFIED_NO_PETS", triage="CLEAN_VERIFIED_NO_PETS_CANDIDATE",
  surface="PROPERTY_FAQ_PANEL",
  name="Holiday Inn Express & Suites Cincinnati Northeast-Milford",
  street="301 Old Bank Road", city="Milford", state="OH", postal="45150",
  tel="15138317829",
  sha="4ee6e5c7-0784c9f5-36d4a2a8-f48c9d6c-38d35209-1d056155-2d0f7cec-8fa1b17f",
  shap="8a60d6d1-98ab5c22-96fb65fb-d6940f42-f4bdf389-8fce5c25-e219dc0e-282eb9f9",
  quote=("No, pets are not allowed at Holiday Inn Express & Suites Cincinnati "
         "Northeast-Milford."),
  sa="", facts={"pets_allowed": False}, diffs=[], diff_kind="",
  notes=("Street and postal bind exactly. Staybridge Suites Cincinnati East - "
         "Milford is a separate identity in this same cohort at 401 Chamber "
         "Drive; the two were not conflated.")),

"holiday inn express and suites cincinnati riverfront": _o(
  outcome="VERIFIED_NO_PETS", triage="CLEAN_VERIFIED_NO_PETS_CANDIDATE",
  surface="PROPERTY_FAQ_PANEL",
  name="Holiday Inn Express & Suites Cincinnati Riverfront",
  street="200 Crescent Avenue", city="Covington", state="KY", postal="41011",
  tel="18595817800",
  sha="fb6d966d-75523a8c-4a7c6e87-ea7d9432-204955fe-c4825459-7e43ca92-4588718e",
  shap="ee5012f7-45d04f3b-64380fc3-87b32904-53103370-cc9fc3ed-b2245c20-444af3c8",
  quote=("No, pets are not allowed at Holiday Inn Express & Suites Cincinnati "
         "Riverfront."),
  sa="", facts={"pets_allowed": False}, diffs=[], diff_kind="",
  notes=("Street, postal and phone bind exactly. Holiday Inn Cincinnati-"
         "Riverfront is a DIFFERENT identity in this cohort, at 600 W Third "
         "Street, and it does allow pets -- a near-identical name with an "
         "opposite policy, which is exactly why neither was read from the "
         "other.")),

"holiday inn express and suites cincinnati south wilder": _o(
  outcome="VERIFIED_NO_PETS", triage="CLEAN_VERIFIED_NO_PETS_CANDIDATE",
  surface="PROPERTY_FAQ_PANEL",
  name="Holiday Inn Express & Suites Cincinnati South - Wilder",
  street="8 Hampton Lane", city="Wilder", state="KY", postal="41076",
  tel="18598158855",
  sha="e0edd88f-7538a8a0-55fe1b65-efde1dcd-46502fae-ca260c5b-00078aac-6a16fe54",
  shap="f465a467-300a9597-dc01fa0c-6909b230-23d805f5-4c5a5372-a17a41bc-d7eb4ae1",
  quote=("No, pets are not allowed at Holiday Inn Express & Suites Cincinnati "
         "South - Wilder."),
  sa="", facts={"pets_allowed": False}, diffs=[], diff_kind="",
  notes="Street, postal and phone bind exactly."),

"holiday inn express and suites florence cincinnati airport": _o(
  outcome="VERIFIED_NO_PETS", triage="CLEAN_VERIFIED_NO_PETS_CANDIDATE",
  surface="PROPERTY_FAQ_PANEL",
  name="Holiday Inn Express & Suites Florence - Cincinnati Airport",
  street="1055 Vandercar Way", city="Florence", state="KY", postal="41042",
  tel="18598170337",
  sha="e488c3cf-67db31d1-6cae6080-9146a992-493e9cbf-49ca1598-8e1fc172-d12785b9",
  shap="911c3cf5-0497cd08-9d9885ef-a05a3f7a-4ea9794b-0204f2c7-742ea3a7-18aab08e",
  quote=("No, pets are not allowed at Holiday Inn Express & Suites Florence - "
         "Cincinnati Airport."),
  sa="", facts={"pets_allowed": False}, diffs=[], diff_kind="",
  notes="Street, postal and phone bind exactly."),

"holiday inn express cincinnati airport": _o(
  outcome="VERIFIED_NO_PETS", triage="CLEAN_VERIFIED_NO_PETS_CANDIDATE",
  surface="PROPERTY_FAQ_PANEL",
  name="Holiday Inn Express & Suites Hebron - Cincinnati Airport",
  street="775 Petersburg Road", city="Hebron", state="KY", postal="41048",
  tel="18599800555",
  sha="b66ac3da-34b45bd8-f31c3e9e-aa75d8ac-2ee78179-134e1be5-94f1b006-9c331da9",
  shap="e6d26620-4cd3ce34-49c8146a-fad382cb-aa5b037e-a1e7c0a7-079d2586-ebc4443b",
  quote=("No, pets are not allowed at Holiday Inn Express & Suites Hebron - "
         "Cincinnati Airport."),
  sa="", facts={"pets_allowed": False},
  diffs=["name: page states 'Hebron - Cincinnati Airport', census states "
         "'Holiday Inn Express Cincinnati Airport'"],
  diff_kind="formatting",
  notes=("Street, postal and phone bind exactly and the census name is a "
         "SUBSET of the page name -- the town was prefixed, not substituted. "
         "That is why this is not the Bellevue case from PROBE-005, where the "
         "place name itself changed.")),

"holiday inn express cincinnati west": _o(
  outcome="PUBLICATION_CANDIDATE", triage="FOUNDER_EXCEPTION",
  surface="PROPERTY_FAQ_PANEL", name="Holiday Inn Express Cincinnati West",
  street="5505 Rybolt Road", city="Cincinnati", state="OH", postal="45248",
  tel="15135746000",
  sha="1253e586-0a1c184f-3109d986-46e564db-a7a01b57-3dfe4517-af520e9c-17316b2b",
  shap="60aa1621-8ecc5643-f4accf4c-1ecb0696-f2f1ba74-b5884cba-87228301-7a7cd63d",
  quote=("Pets are welcome at Holiday Inn Express Cincinnati West. Pet policy "
         "description. Pets under 40 pounds are permitted. 1 to 3 nights 75 "
         "USD, 4 to 7 nights 125 USD. 8 plus nights requires a 500 USD "
         "deposit. Pet deposit is nonrefundable. Please contact hotel "
         "directly for further information. Pet damage deposit: 75 USD Pet "
         "weight limit: 40 2 pets allowed Pets allowed: Only dogs and cats "
         "allowed"),
  sa="", facts={"pets_allowed": True}, diffs=[], diff_kind="",
  question=("Three problems in one panel. (1) The prose gives two stay-length "
            "tiers -- 75 USD for 1-3 nights, 125 USD for 4-7 -- plus a 500 "
            "USD requirement at 8+ nights. (2) It calls the 500 a DEPOSIT and "
            "then says 'Pet deposit is nonrefundable', which is a fee wearing "
            "a deposit's name. (3) The structured field reports a separate "
            "'Pet damage deposit: 75 USD' that duplicates the tier-1 amount. "
            "Which of these three numbers, if any, is the headline, and does "
            "the 500 publish as a fee or a deposit?"),
  notes=("'Pets UNDER 40 pounds' is a strict bound -- operator lt. Nothing "
         "here was collapsed into a single headline fee.")),

"holiday inn express franklin": _o(
  outcome="VERIFIED_NO_PETS", triage="CLEAN_VERIFIED_NO_PETS_CANDIDATE",
  surface="PROPERTY_FAQ_PANEL",
  name="Holiday Inn Express & Suites Dayton South Franklin",
  street="851 Commerce Center Drive", city="Franklin", state="OH",
  postal="45005", tel="19377461094",
  sha="68afacde-c28b973d-656d94d6-7c1e4c50-02d4ea10-ff17b21f-e212222b-320abdec",
  shap="878818ca-56c2f043-fad037ea-0733e093-cd8c0a4d-008bc292-7b6ac262-cba6f0a2",
  quote=("No, pets are not allowed at Holiday Inn Express & Suites Dayton "
         "South Franklin."),
  sa="", facts={"pets_allowed": False},
  diffs=["name: page states 'Dayton South Franklin', census states 'Holiday "
         "Inn Express Franklin'"],
  diff_kind="rename_or_naming",
  notes=("Street and postal bind exactly. The property brands itself to the "
         "Dayton metro while sitting in a Cincinnati census row. Market "
         "membership is decided by corridor postal code, not by the brand "
         "string, so this does not move the row -- but it is recorded, "
         "because a name is what a reader sees.")),

"holiday inn express hotel and suites cincinnati blue ash": _o(
  outcome="VERIFIED_NO_PETS", triage="CLEAN_VERIFIED_NO_PETS_CANDIDATE",
  surface="PROPERTY_FAQ_PANEL",
  name="Holiday Inn Express & Suites Cincinnati-Blue Ash",
  street="4660 Creek Road", city="Blue Ash", state="OH", postal="45242",
  tel="15139859035",
  sha="8157c777-2b63d45a-9b7f7bc4-33c6e4ce-c0f4f5af-3342f5ac-c9b5c313-7de6a440",
  shap="6dda0520-cd0f56a0-40e30392-8f73c001-951a7039-74caeccb-bf8844da-e0974914",
  quote=("No, pets are not allowed at Holiday Inn Express & Suites Cincinnati-"
         "Blue Ash."),
  sa="", facts={"pets_allowed": False}, diffs=[], diff_kind="",
  notes=("Street, postal and phone bind exactly. Comfort Inn Blue Ash North "
         "is at 4640 Creek Road -- twenty numbers away and a separate "
         "identity in this cohort. Neither address was normalised toward the "
         "other.")),

"holiday inn express hotel and suites mason": _o(
  outcome="PUBLICATION_CANDIDATE", triage="FOUNDER_EXCEPTION",
  surface="PROPERTY_FAQ_PANEL",
  name="Holiday Inn Express & Suites Cincinnati - Mason",
  street="5100 Natorp Blvd.", city="Mason", state="OH", postal="45040",
  tel="15133876000",
  sha="89af4f5b-f8e8ebc6-81c6cb15-27bbcd41-a74cda76-976388ca-c640ab02-481fb943",
  shap="ef73f18d-f6d30ec5-f408a1b4-103b2a62-0ffd6ce7-22d9567b-9a1f1627-9e6d0b0e",
  quote=("Pets are welcome at Holiday Inn Express & Suites Cincinnati - "
         "Mason. Pet policy description. Both pets and service animals are "
         "welcome. 75 Pet Fee: 1 to 4 Nights 125 Pet Fee: 5 or more Nights "
         "Pet fee per night: 125 USD Pet damage deposit: 75 USD Pet weight "
         "limit: No weight limit per pet 2 pets allowed Pets allowed: Only "
         "dogs and cats allowed"),
  sa="", facts={"pets_allowed": True}, diffs=[], diff_kind="",
  question=("The prose gives stay-length tiers of 75 (1-4 nights) and 125 (5+ "
            "nights). The structured field then reports 125 as the PER NIGHT "
            "rate and 75 as a PET DAMAGE DEPOSIT -- reusing both tier amounts "
            "as different kinds of charge. Publish the two tiers and withhold "
            "both structured readings?"),
  notes=("'No weight limit per pet' is an affirmative statement that there is "
         "no limit, not silence -- but it is not a weight_limit value either, "
         "so nothing is published in that field. Candlewood Suites Cincinnati "
         "Northeast-Mason is at 5070 Natorp Blvd, thirty numbers away, and is "
         "a separate identity carried in PROBE-005.")),

"holiday inn express richwood": _o(
  outcome="VERIFIED_NO_PETS", triage="CLEAN_VERIFIED_NO_PETS_CANDIDATE",
  surface="PROPERTY_FAQ_PANEL",
  name="Holiday Inn Express & Suites Richwood - Cincinnati South",
  street="12928 Frogtown Connector Rd.", city="Walton", state="KY",
  postal="41094", tel="18594930900",
  sha="4ee7e2ab-b12baec6-00bc7f02-736294bd-875b00b9-3ec59d2f-a630b973-cf805e67",
  shap="f55816f7-f7886aa7-d3c77cf3-0ee4c39a-5944f8cb-edc2dc89-22b727d0-bc589ed7",
  quote=("No, pets are not allowed at Holiday Inn Express & Suites Richwood - "
         "Cincinnati South."),
  sa="", facts={"pets_allowed": False},
  diffs=["city: page states Walton, census states Richwood"],
  diff_kind="formatting",
  notes=("Street, postal and phone bind exactly. Richwood is an unincorporated "
         "community with a Walton mailing address, so both names describe the "
         "same place.")),

"holiday inn florence": _o(
  outcome="VERIFIED_NO_PETS", triage="CLEAN_VERIFIED_NO_PETS_CANDIDATE",
  surface="PROPERTY_FAQ_PANEL", name="Holiday Inn Florence",
  street="7905 Freedom Way", city="Florence", state="KY", postal="41042",
  tel="18599801700",
  sha="7c6d6808-a013ab77-e555848b-13c9ce6c-52b8c1cf-68678ad1-ef1f9bdc-e6e0e656",
  shap="4106cca0-629b1c25-569c96e3-7ecbe524-e2e10fa3-f5ca3d84-73698697-0dfee153",
  quote="No, pets are not allowed at Holiday Inn Florence.",
  sa="", facts={"pets_allowed": False}, diffs=[], diff_kind="",
  notes="Street, postal and phone bind exactly."),

"staybridge suites florence": _o(
  outcome="PUBLICATION_CANDIDATE", triage="FOUNDER_EXCEPTION",
  surface="PROPERTY_FAQ_PANEL",
  name="Staybridge Suites Florence - Cincinnati South",
  street="3255 Ted Bushelman Blvd", city="Florence", state="KY",
  postal="41042", tel="18596893800",
  sha="2f7fad4f-f485108d-2766554a-c60e9984-3c6eb0e3-7b37210d-8688d5e9-6e7627f3",
  shap="afac2653-949bdf19-716b4c05-bee95149-31d4dc6e-7621581c-67a3e4eb-7f062245",
  quote=("Pets are welcome at Staybridge Suites Florence - Cincinnati South. "
         "Our Pet Policy: Max 1 dog permitted up to 40lbs with a "
         "nonrefundable fee of 75 for stays between 1 to 6 days, 150 between "
         "7 to 29 days, and 250 of 30 days. Pet Policy must be signed upon "
         "arrival. No fee for service animals. Emotion support animals do not "
         "qualify.No cats."),
  sa="No fee for service animals. Emotion support animals do not qualify.",
  facts={"pets_allowed": True}, diffs=[], diff_kind="",
  question=("Three stay-length tiers -- 75 for 1-6, 150 for 7-29, 250 at 30 "
            "-- but the boundaries are stated in DAYS, and the schema's tier "
            "boundary units are nights or pets. Reading days as nights is an "
            "inference, not a reading. Also, the third clause is garbled in "
            "the source itself ('and 250 of 30 days'). Publish the tiers "
            "reading days as nights, or withhold the fee and publish the "
            "species, count and weight limit only?"),
  notes=("Max 1 dog, 40 lb, no cats, service animals free and emotional "
         "support animals explicitly excluded. The species and count "
         "restrictions are unambiguous whatever you decide about the tiers.")),

"staybridge suites milford": _o(
  outcome="PUBLICATION_CANDIDATE", triage="FOUNDER_EXCEPTION",
  surface="PROPERTY_FAQ_PANEL",
  name="Staybridge Suites Cincinnati East - Milford", street="401 Chamber Drive",
  city="Milford", state="OH", postal="45150", tel="15137814700",
  sha="ec7797d4-1e19092c-efa4e2e1-9fe033d5-93882436-1223b378-bd565ec0-c2d51973",
  shap="8d3857ab-75c42edb-63b53af6-d70f3e5b-f0dac43c-925cbd57-97ce55f8-3fcc3aba",
  quote=("Pets are welcome at Staybridge Suites Cincinnati East - Milford. "
         "Our Pet Policy: Guests must have a crate to put their animal in "
         "when leaving the premises. All pets must be up to date on mandatory "
         "vaccinations. We have a nonrefundable pet fee of 50 dollars per "
         "week. Minimum Fee is 50 dollars. Pet agreement must be signed at "
         "check in."),
  sa="", facts={"pets_allowed": True}, diffs=[], diff_kind="",
  question=("The SECOND per-week fee in this market -- Staybridge Suites "
            "Cincinnati North in PROBE-005 was the first, at the same 50 USD "
            "per week. The schema's fee bases are per_night, per_day and "
            "per_stay; there is no per_week. One ruling can settle both rows: "
            "withhold the amount as SCHEMA_CANNOT_REPRESENT and publish "
            "pets_allowed, or extend the basis vocabulary in its own order?"),
  notes=("Street and postal bind exactly. 50/7 is a number this hotel never "
         "stated, so no conversion was made.")),

"voco the clair cincinnati downtown": _o(
  outcome="VERIFIED_NO_PETS", triage="CLEAN_VERIFIED_NO_PETS_CANDIDATE",
  surface="PROPERTY_FAQ_PANEL", name="voco The Clair Cincinnati Downtown",
  street="701 Broadway Street", city="Cincinnati", state="OH", postal="45202",
  tel="15133815025",
  sha="2077504f-3bec6880-d2566140-2a952704-719e8015-3d13b9aa-80f1dd5c-4bb9157e",
  shap="cb081e00-58433188-57ee356b-4431f714-462110e7-3785196f-75b7536a-477ce5cf",
  quote="No, pets are not allowed at voco The Clair Cincinnati Downtown.",
  sa="", facts={"pets_allowed": False}, diffs=[], diff_kind="",
  notes="Street and postal bind exactly."),
}


def _norm_street(value):
    """Compare street strings without letting punctuation invent a difference."""
    text = (value or "").lower().replace(".", " ")
    text = re.sub(r"\b(road)\b", "rd", text)
    text = re.sub(r"\b(street)\b", "st", text)
    text = re.sub(r"\b(drive)\b", "dr", text)
    text = re.sub(r"\b(boulevard)\b", "blvd", text)
    text = re.sub(r"\b(avenue)\b", "ave", text)
    text = re.sub(r"\b(parkway)\b", "pkwy", text)
    text = re.sub(r"\b(west)\b", "w", text)
    text = re.sub(r"\b(east)\b", "e", text)
    text = re.sub(r"\b(third)\b", "3rd", text)
    return re.sub(r"\s+", " ", text).strip()


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
            ("official_property_url", row["official_property_url"]),
            ("observed_at", OBSERVED_ON),
            ("capture_method", CAPTURE_METHOD),
            ("provider_calls", 0),
            ("cost_usd", 0.0),
            ("page_rendered", True),
            ("identity_confirmed", o["diff_kind"] != "unresolved"),
            ("policy_surface_found", True),
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
            ("difference_kind", o["diff_kind"]),
            ("street_agrees_after_formatting",
             _norm_street(o["street"]).startswith(_norm_street(row["address"]))
             or _norm_street(row["address"]).startswith(_norm_street(o["street"]))),
            ("quote", o["quote"]),
            ("sha256_policy_surface", o["sha"]),
            ("sha256_page", o["shap"]),
            ("facts", o["facts"]),
            ("notes", o["notes"]),
        ))
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
        ("locators", OrderedDict((
            ("IHG", "Pet policy accordion panel; fallback the property FAQ "
                    "panel 'Can I bring my pet to <hotel>?', which names the "
                    "hotel in its own sentence"),
            ("CHOICE", "Pets block inside Essential details")))),
        ("lane_finding_ihg_structured_field",
         STRUCTURED_FIELD_BASIS_IS_BOILERPLATE),
        ("surface_hash_is_not_property_unique", ["CHOICE"]),
        ("rows", rows),
    ))


# ---------------------------------------------------------------- the packet

def build_packet(scale_rows):
    """One consolidated packet -- PROBE-005's exceptions and SCALE-006's.

    Clean rows are not in here. A founder who has already authorised a clean
    lane should be asked only the questions the lane could not answer.
    """
    entries = []
    for source, rows in (("PTF-CINCINNATI-FREE-BRAND-PROBE-005",
                          load(PROBE_RESULTS)["rows"]),
                         (WORK_ORDER, scale_rows)):
        for row in rows:
            if row["triage"] != "FOUNDER_EXCEPTION":
                continue
            entries.append(OrderedDict((
                ("property", row["canonical_name"]),
                ("identity_key", row["identity_key"]),
                ("family", row["family"]),
                ("observed_by", source),
                ("official_property_url", row["official_property_url"]),
                ("issue", row.get("question_for_the_founder", "")),
                ("evidence_quote", row["quote"]),
                ("evidence_sha256_policy_surface",
                 row["sha256_policy_surface"]),
                ("evidence_sha256_page", row["sha256_page"]),
                ("safe_fields", _safe_fields(row)),
                ("withheld_fields", _withheld_fields(row)),
                ("recommended_disposition", _RECOMMENDED[row["identity_key"]][0]),
                ("reason", _RECOMMENDED[row["identity_key"]][1]),
                ("founder_decision", ""),
                ("founder_reviewer_id", ""),
                ("founder_note", ""),
            )))
    return OrderedDict((
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("sources", ["PTF-CINCINNATI-FREE-BRAND-PROBE-005", WORK_ORDER]),
        ("note", "Genuine exceptions only. Clean rows need no review, and no "
                 "decision field is pre-filled."),
        ("count", len(entries)),
        ("rows", entries),
    ))


def _safe_fields(row):
    """What this row could publish today without a ruling."""
    return sorted(k for k in row["facts"])


def _withheld_fields(row):
    """What the exception is actually holding back, and why."""
    return _WITHHELD.get(row["identity_key"], [])


_WITHHELD = {
 "candlewood suites cincinnati northeast mason": [
   "pet_fee -- three distinct charges stated (SOURCE_AMBIGUOUS)",
   "other_charges -- cleaning fee and damage deposit await a ruling"],
 "staybridge suites cincinnati north": [
   "pet_fee -- stated per week (SCHEMA_CANNOT_REPRESENT)"],
 "holiday inn express and suites bellevue": [
   "identity -- the property name has changed (IDENTITY_NOT_CONFIRMED)"],
 "candlewood suites erlanger south cincinnati": [
   "pet_fee -- prose tiers contradict the structured nightly field "
   "(SOURCE_CONTRADICTORY)",
   "fee_tiers -- await the headline ruling"],
 "holiday inn cincinnati airport": [
   "pet_fee -- prose says per stay, structured field says per night "
   "(SOURCE_CONTRADICTORY)"],
 "holiday inn express cincinnati west": [
   "pet_fee -- two tiers plus a nonrefundable 'deposit' (SOURCE_AMBIGUOUS)",
   "other_charges -- the 500 USD charge and the 75 USD structured deposit"],
 "holiday inn express hotel and suites mason": [
   "pet_fee -- both tier amounts reused as other charge kinds "
   "(SOURCE_CONTRADICTORY)",
   "fee_tiers -- await the headline ruling"],
 "staybridge suites florence": [
   "pet_fee -- tier boundaries stated in days (SCHEMA_CANNOT_REPRESENT)",
   "fee_tiers -- same"],
 "staybridge suites milford": [
   "pet_fee -- stated per week (SCHEMA_CANNOT_REPRESENT)"],
 "comfort suites mainstay hotel": [
   "everything -- the identity is unresolved (IDENTITY_NOT_CONFIRMED)"],
}

_RECOMMENDED = {
 "candlewood suites cincinnati northeast mason": (
   "APPROVE_PARTIAL",
   "Publish the two stay-length tiers with distinct roles and hold the damage "
   "deposit separately; do not let one headline absorb three charges."),
 "staybridge suites cincinnati north": (
   "APPROVE_PARTIAL",
   "Publish pets_allowed and withhold the amount as SCHEMA_CANNOT_REPRESENT "
   "until a per_week basis exists."),
 "holiday inn express and suites bellevue": (
   "RENAME",
   "Street, postal and phone bind exactly; only the brand string moved. A "
   "rename supersedes and never merges."),
 "candlewood suites erlanger south cincinnati": (
   "APPROVE_PARTIAL",
   "Take the prose tiers and withhold the structured nightly reading; the "
   "field's basis label is template boilerplate across this brand."),
 "holiday inn cincinnati airport": (
   "APPROVE_PARTIAL",
   "Take 75 USD per STAY from the prose and withhold the nightly reading. "
   "Over seven nights the two readings differ by 450 USD."),
 "holiday inn express cincinnati west": (
   "APPROVE_PARTIAL",
   "Publish the 1-3 and 4-7 night tiers and pets_allowed; withhold the 500 "
   "USD charge until it is settled whether it is a fee or a deposit."),
 "holiday inn express hotel and suites mason": (
   "APPROVE_PARTIAL",
   "Publish the 75/125 stay-length tiers and withhold both structured "
   "readings, which reuse the tier amounts as other charge kinds."),
 "staybridge suites florence": (
   "APPROVE_PARTIAL",
   "Publish species, pet count and weight limit, which are unambiguous; "
   "withhold the fee while the boundaries are stated in days."),
 "staybridge suites milford": (
   "APPROVE_PARTIAL",
   "Same disposition as Staybridge North -- one ruling can settle both."),
 "comfort suites mainstay hotel": (
   "HOLD_FOR_IDENTITY_REVIEW",
   "Three of four identity signals disagree. Registering a refusal against "
   "the wrong building is a public statement about a hotel that never made "
   "it."),
}


def main():
    results = build_results()
    render(RESULTS, results)
    rows = results["rows"]

    render(CLEAN_PF, OrderedDict((
        ("work_order", WORK_ORDER), ("triage", "CLEAN_PET_FRIENDLY_CANDIDATE"),
        ("note", "Proposed, not approved. No approval field is set."),
        ("count", sum(1 for r in rows
                      if r["triage"] == "CLEAN_PET_FRIENDLY_CANDIDATE")),
        ("rows", [r for r in rows
                  if r["triage"] == "CLEAN_PET_FRIENDLY_CANDIDATE"]))))
    render(CLEAN_NP, OrderedDict((
        ("work_order", WORK_ORDER),
        ("triage", "CLEAN_VERIFIED_NO_PETS_CANDIDATE"),
        ("note", "Proposed, not approved. No approval field is set."),
        ("count", sum(1 for r in rows
                      if r["triage"] == "CLEAN_VERIFIED_NO_PETS_CANDIDATE")),
        ("rows", [r for r in rows
                  if r["triage"] == "CLEAN_VERIFIED_NO_PETS_CANDIDATE"]))))

    render(PACKET, build_packet(rows))
    render(LANE, build_final_measurement(rows))
    render(REPRICE, build_reprice(rows))
    return results


if __name__ == "__main__":
    main()
