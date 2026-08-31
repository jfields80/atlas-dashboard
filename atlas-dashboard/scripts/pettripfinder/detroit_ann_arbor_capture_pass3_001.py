# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-CLAUDE-CAPTURE-PASS3-001.

Executes the prepared 30-row EVIDENCE_READY Claude Capture queue from
ROUTING-EXPANSION-004. Real Claude attended-browser capture of each
property's own official page (30/30 processed, no substitutions, the 2
ROUTING_UNRESOLVED rows and the retired duplicate were never in the
queue and were not touched).

CAPTURE ONLY. No founder decision is recorded here; no policy authority,
exclusion authority, seed authority, or partition terminal state is
touched. published=7 and verified_no_pets=7 are asserted unchanged by
this script (it makes no attempt to write them).

Screenshot capture was unavailable this session (the extension's
viewport/clip subsystem errored on every attempt, before and after
resize). Durable evidence uses a text-artifact class instead: the exact
policy-bearing text block extracted from each official page, persisted
verbatim under
data/worker_runs/pettripfinder/detroit-ann-arbor-capture-pass3-001/raw/
(gitignored, same as every prior pass's screenshots) with its SHA-256
computed both in-browser (crypto.subtle.digest) and independently via a
second hash of the persisted file, cross-verified to match. This is the
same "compute the hash in-page, persist the artifact, never round-trip
raw bytes through the tool's own guardrails" discipline this corpus's
memory already documents for hex-string transfer -- applied here because
the artifact itself, not just its hash, needed a path around a broken
screenshot pipeline.

Two genuinely-inconclusive rows (Atheneum Suite Hotel, Daxton Hotel):
every page on each site was checked (homepage, amenities/rooms/guide
pages, and the full page-sitemap.xml) with zero pet mentions anywhere.
SOURCE SILENCE IS ABSENCE, not a negative claim -- POLICY_NOT_FOUND, not
VERIFIED_NO_PETS_CANDIDATE.

Two compound/ambiguous fee cases handled per Section 8:
  * Delta Hotels by Marriott Detroit Novi -- prose ties the $80 charge to
    "per 7 day stay", a period the schema's basis enum (per_night/
    per_day/per_stay) cannot represent; the structured field's flat
    "per stay" claim does not preserve that qualification. pet_fee
    withheld, reason SCHEMA_CANNOT_REPRESENT.
  * Detroit Foundation Hotel -- the $75 fee is stated with no basis word
    at all (not "per night", not "per stay"). pet_fee withheld, reason
    ARTIFACT_INSUFFICIENT.
Two compound-but-NOT-ambiguous fee cases (Courtyard Detroit Dearborn,
Courtyard Detroit Troy): a $20/night charge stated ADDITIVELY alongside
a $100/stay nonrefundable "clean fee" ("Pet fee $20/day WITH $100/stay
nonrefundable clean fee") -- both proposed as separate facts, neither
withheld, because the prose itself resolves how they combine.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-CLAUDE-CAPTURE-PASS3-001"
AS_OF = "2026-08-17"
PRIOR_COMMIT = "a4559fc"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
CENSUS_PATH = LP / "identity_census" / ("%s.json" % MARKET)
RESULTS_PATH = LP / "detroit_ann_arbor_capture_pass3_001.json"
PACKET_PATH = LP / "detroit_ann_arbor_capture_pass3_founder_review_packet.json"
MANIFEST_PATH = LP / "detroit_ann_arbor_capture_pass3_001_evidence_manifest.json"
RAW_DIR = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
          / "detroit-ann-arbor-capture-pass3-001" / "raw")

# routing_id prefix matches the shard's routing_id convention.
CORRIDOR_BY_KEY = {
    "ac hotel ann arbor downtown": "detroit-ann-arbor-mi__ann-arbor",
    "americas best value inn livonia detroit": "detroit-ann-arbor-mi__livonia-plymouth-northville",
    "ann arbor marriott ypsilanti at eagle crest": "detroit-ann-arbor-mi__ypsilanti",
    "ann arbor regent hotel and suites": "detroit-ann-arbor-mi__ann-arbor",
    "atheneum suite hotel": "detroit-ann-arbor-mi__downtown-detroit",
    "auburn hills marriott pontiac": "detroit-ann-arbor-mi__birmingham-royal-oak-rochester",
    "best western detroit livonia": "detroit-ann-arbor-mi__livonia-plymouth-northville",
    "best western greenfield inn": "detroit-ann-arbor-mi__dearborn",
    "cambria hotel detroit downtown": "detroit-ann-arbor-mi__downtown-detroit",
    "courtyard by marriott detroit dearborn": "detroit-ann-arbor-mi__dearborn",
    "courtyard by marriott detroit downtown": "detroit-ann-arbor-mi__downtown-detroit",
    "courtyard by marriott detroit southfield": "detroit-ann-arbor-mi__southfield",
    "courtyard by marriott detroit troy": "detroit-ann-arbor-mi__troy-auburn-hills",
    "daxton hotel": "detroit-ann-arbor-mi__birmingham-royal-oak-rochester",
    "dearborn inn autograph collection": "detroit-ann-arbor-mi__dearborn",
    "delta hotels by marriott detroit novi": "detroit-ann-arbor-mi__farmington-hills",
    "detroit foundation hotel": "detroit-ann-arbor-mi__downtown-detroit",
    "detroit marriott livonia": "detroit-ann-arbor-mi__livonia-plymouth-northville",
    "detroit marriott southfield": "detroit-ann-arbor-mi__southfield",
    "detroit marriott troy": "detroit-ann-arbor-mi__troy-auburn-hills",
    "detroit metro airport marriott": "detroit-ann-arbor-mi__dtw-airport",
    "el moore lodge": "detroit-ann-arbor-mi__downtown-detroit",
    "element detroit at the metropolitan": "detroit-ann-arbor-mi__downtown-detroit",
    "extended stay america detroit ann arbor university south": "detroit-ann-arbor-mi__ann-arbor",
    "fairfield inn and suites ann arbor ypsilanti": "detroit-ann-arbor-mi__ypsilanti",
    "fairfield inn and suites detroit farmington hills": "detroit-ann-arbor-mi__farmington-hills",
    "fairfield inn and suites detroit troy": "detroit-ann-arbor-mi__troy-auburn-hills",
    "fairfield inn and suites by marriott detroit livonia": "detroit-ann-arbor-mi__livonia-plymouth-northville",
    "fairfield inn ann arbor": "detroit-ann-arbor-mi__ann-arbor",
    "four points by sheraton detroit novi": "detroit-ann-arbor-mi__novi-wixom",
}

# Each row: (n, identity_key, hotel, final_url, outcome, artifact_file(or None),
#            sha256(or None), identity_binding_fields, quote, facts, withheld,
#            general_note)
ROWS: List[Dict] = [
    dict(n=1, key="ac hotel ann arbor downtown", hotel="AC Hotel Ann Arbor Downtown",
        url="https://www.marriott.com/en-us/hotels/dtwad-ac-hotel-ann-arbor-downtown/overview/",
        outcome="PUBLICATION_CANDIDATE",
        artifact="P3-01-ac-hotel-ann-arbor-downtown.txt",
        sha="e5d9633bd55e2e947f391fed119a7bf3419829dab99a06ef9c37471eecd48d5a",
        phone="+17342496200",
        quote="Pet Policy\n\nPets Welcome\n\nPet Fee Per Stay $150 Maximum Pet Weight 50lbs Maximum Number of Pets in Room 1\n\nNon-Refundable Pet Fee Per Stay: $150.00\n\nMaximum Pet Weight: 50.0lbs\n\nMaximum Number of Pets in Room: 1",
        facts=[
            dict(field="pets_allowed", value=True, quote="Pets Welcome"),
            dict(field="pet_fee", value=dict(amount_cents=15000, currency="USD", basis="per_stay", refundable=False),
                quote="Non-Refundable Pet Fee Per Stay: $150.00"),
            dict(field="weight_limit", value=dict(value=50, unit="lb", operator="lte", scope="per_pet"),
                quote="Maximum Pet Weight: 50.0lbs"),
            dict(field="pet_count_limit", value=1, quote="Maximum Number of Pets in Room: 1"),
            dict(field="pet_count_scope", value="room", quote="Maximum Number of Pets in Room: 1"),
        ], withheld=[],
        note="Structured 'Pet Policy' field, no prose, no contradiction."),
    dict(n=2, key="americas best value inn livonia detroit",
        hotel="Americas Best Value Inn Livonia Detroit",
        url="https://www.sonesta.com/americas-best-value-inn/mi/livonia/americas-best-value-inn-livonia-detroit",
        outcome="VERIFIED_NO_PETS_CANDIDATE",
        artifact="P3-02-americas-best-value-inn-livonia.txt",
        sha="70a49a286868fd0aad3b122204e45ab81593dcc69664aa607a3aaec6b372110c",
        quote="Sorry, no pets allowed.",
        facts=[dict(field="pets_allowed", value=False, quote="Sorry, no pets allowed.")], withheld=[],
        note="Property amenities list on sonesta.com's own property page."),
    dict(n=3, key="ann arbor marriott ypsilanti at eagle crest",
        hotel="Ann Arbor Marriott Ypsilanti at Eagle Crest",
        url="https://www.marriott.com/en-us/hotels/dtwys-ann-arbor-marriott-ypsilanti-at-eagle-crest/overview/",
        outcome="VERIFIED_NO_PETS_CANDIDATE",
        artifact="P3-03-ann-arbor-marriott-ypsilanti-eagle-crest.txt",
        sha="4fbe56421047e51fa0038708dfd1378445ee89f7487b220b660b9580a0057b34",
        phone="+17344872000",
        quote="petsAllowed: Only trained service animals permitted",
        facts=[dict(field="pets_allowed", value=False, quote="petsAllowed: Only trained service animals permitted")],
        withheld=[],
        service_animal=dict(stated=True, charges_stated="not_addressed",
                            quote="Only trained service animals permitted"),
        note="No 'Pet Policy' amenity heading rendered on this property; found in the "
             "page's own JSON-LD structured data (schema.org Hotel.petsAllowed)."),
    dict(n=4, key="ann arbor regent hotel and suites", hotel="Ann Arbor Regent Hotel & Suites",
        url="https://annarborregent.com/faqs/",
        outcome="VERIFIED_NO_PETS_CANDIDATE",
        artifact="P3-04-ann-arbor-regent.txt",
        sha="4601818832c9b627f287d35d78a87e24cbed04324266200770a14e589a9c501a",
        phone="734-973-6100",
        quote="ARE PETS ALLOWED?\n\nWe only allow service animals, not emotional support animals.",
        facts=[dict(field="pets_allowed", value=False, quote="We only allow service animals, not emotional support animals.")],
        withheld=[],
        service_animal=dict(stated=True, charges_stated="not_addressed",
                            quote="We only allow service animals, not emotional support animals."),
        note="Property's own FAQ page. Explicitly distinguishes ADA service animals "
             "from emotional support animals -- the ESA exclusion is a real, distinct "
             "statement, not paraphrased."),
    dict(n=5, key="atheneum suite hotel", hotel="Atheneum Suite Hotel",
        url="https://www.atheneumsuites.com", outcome="POLICY_NOT_FOUND",
        artifact=None, sha=None, quote=None, facts=[], withheld=[],
        note="Checked: homepage, /detroit-mi-hotel-amenities, "
             "/detroit-hotel-reservations, and the site's full page-sitemap.xml "
             "(no faq/policy/pet page listed at all). Zero pet mentions anywhere. "
             "SOURCE SILENCE IS ABSENCE -- not treated as a negative claim."),
    dict(n=6, key="auburn hills marriott pontiac", hotel="Auburn Hills Marriott Pontiac",
        url="https://www.marriott.com/en-us/hotels/dtwpo-auburn-hills-marriott-pontiac/overview/",
        outcome="VERIFIED_NO_PETS_CANDIDATE",
        artifact="P3-06-auburn-hills-marriott-pontiac.txt",
        sha="bc8c4dbff48db63f778042f1cc579c513e5985ecf942846a42a8ef95cf6bbc0b",
        phone="+12482539800",
        quote="Pet Policy\n\nPets Not Allowed\n\nNone",
        facts=[dict(field="pets_allowed", value=False, quote="Pets Not Allowed")], withheld=[],
        note="Structured 'Pet Policy' field."),
    dict(n=7, key="best western detroit livonia", hotel="Best Western Detroit Livonia",
        url="https://www.bestwestern.com/en_US/book/hotel-details.23120.html",
        outcome="VERIFIED_NO_PETS_CANDIDATE",
        artifact="P3-07-best-western-detroit-livonia.txt",
        sha="7a82b7a25d328751b61b7ff1615e190d04cab5bf51b6d749defc0ec4c7b5c6ff",
        phone="+1 (734) 464-0050",
        quote="PET POLICY\nPets are not accepted.",
        facts=[dict(field="pets_allowed", value=False, quote="Pets are not accepted.")], withheld=[],
        note="Structured 'PET POLICY' field on bestwestern.com's own property page."),
    dict(n=8, key="best western greenfield inn", hotel="Best Western Greenfield Inn",
        url="https://www.bestwestern.com/en_US/book/hotels-in-allen-park/best-western-greenfield-inn/propertyCode.23089.html",
        outcome="VERIFIED_NO_PETS_CANDIDATE",
        artifact="P3-08-best-western-greenfield-inn.txt",
        sha="7a82b7a25d328751b61b7ff1615e190d04cab5bf51b6d749defc0ec4c7b5c6ff",
        quote="PET POLICY\nPets are not accepted.",
        facts=[dict(field="pets_allowed", value=False, quote="Pets are not accepted.")], withheld=[],
        note="Same Best Western boilerplate text as Best Western Detroit Livonia "
             "(#7) -- identical hash is expected and correct; the two are "
             "confirmed-distinct properties by address (16999 S Laurel Park Dr, "
             "Livonia vs 3000 Enterprise Dr, Allen Park)."),
    dict(n=9, key="cambria hotel detroit downtown", hotel="Cambria Hotel Detroit Downtown",
        url="https://cambriadetroit.com/", outcome="VERIFIED_NO_PETS_CANDIDATE",
        artifact="P3-09-cambria-hotel-detroit-downtown.txt",
        sha="fcccced4dd763dc6576fce4901ec69f9a7660268dedddf567119d7d74ebe1f6f",
        quote="No Pets Allowed",
        facts=[dict(field="pets_allowed", value=False, quote="No Pets Allowed")], withheld=[],
        note="Amenities list on the property's own homepage."),
    dict(n=10, key="courtyard by marriott detroit dearborn",
        hotel="Courtyard by Marriott Detroit Dearborn",
        url="https://www.marriott.com/en-us/hotels/dttdb-courtyard-detroit-dearborn/overview/",
        outcome="PUBLICATION_CANDIDATE",
        artifact="P3-10-courtyard-detroit-dearborn.txt",
        sha="47361ef5a45e058321d0c26185dc027b57dcf8e6e7c422a81ba038b74ab5eae0",
        phone="+13132711400",
        quote="Pet Policy\n\nPets Welcome\n\nPet fee $20/day with $100/stay nonrefundable clean fee excludes Service Animals\n\nNon-Refundable Pet Fee Per Stay: $100.00\n\nNon-Refundable Pet Fee Per Night: $20.00\n\nMaximum Pet Weight: 35.0lbs\n\nMaximum Number of Pets in Room: 2",
        facts=[
            dict(field="pets_allowed", value=True, quote="Pets Welcome"),
            dict(field="pet_fee", value=dict(amount_cents=2000, currency="USD", basis="per_night", refundable=False),
                quote="Non-Refundable Pet Fee Per Night: $20.00"),
            dict(field="other_charges", value=[dict(kind="cleaning_fee", amount_cents=10000, currency="USD",
                                                    basis="per_stay", refundable=False)],
                quote="Pet fee $20/day with $100/stay nonrefundable clean fee"),
            dict(field="weight_limit", value=dict(value=35, unit="lb", operator="lte", scope="per_pet"),
                quote="Maximum Pet Weight: 35.0lbs"),
            dict(field="pet_count_limit", value=2, quote="Maximum Number of Pets in Room: 2"),
            dict(field="pet_count_scope", value="room", quote="Maximum Number of Pets in Room: 2"),
        ], withheld=[],
        service_animal=dict(stated=True, charges_stated="no_charge",
                            quote="excludes Service Animals"),
        note="Two charges stated ADDITIVELY, not contradictorily: a per-night fee "
             "PLUS a one-time nonrefundable clean fee ('$20/day WITH $100/stay "
             "nonrefundable clean fee'). Both proposed as separate facts."),
    dict(n=11, key="courtyard by marriott detroit downtown",
        hotel="Courtyard by Marriott Detroit Downtown",
        url="https://www.marriott.com/en-us/hotels/dtwdc-courtyard-detroit-downtown/overview/",
        outcome="VERIFIED_NO_PETS_CANDIDATE",
        artifact="P3-11-courtyard-detroit-downtown.txt",
        sha="98573258de37306d44b8c786e73518598223ac639257ff6a95ded84bb407d4bb",
        quote="Pet Policy\n\nPets Not Allowed",
        facts=[dict(field="pets_allowed", value=False, quote="Pets Not Allowed")], withheld=[],
        note="Structured 'Pet Policy' field."),
    dict(n=12, key="courtyard by marriott detroit southfield",
        hotel="Courtyard by Marriott Detroit Southfield",
        url="https://www.marriott.com/en-us/hotels/dtwsf-courtyard-detroit-southfield/overview/",
        outcome="VERIFIED_NO_PETS_CANDIDATE",
        artifact="P3-12-courtyard-detroit-southfield.txt",
        sha="6b3c3531ee10d1ae208ad93f754007add9950439699ab9c9f633c333fb27b75c",
        quote="Pet Policy\n\nPets Not Allowed\n\nNo pets allowed except aiding the disabled",
        facts=[dict(field="pets_allowed", value=False, quote="Pets Not Allowed")], withheld=[],
        service_animal=dict(stated=True, charges_stated="not_addressed",
                            quote="No pets allowed except aiding the disabled"),
        note="Structured 'Pet Policy' field with an explicit ADA service-animal carve-out."),
    dict(n=13, key="courtyard by marriott detroit troy", hotel="Courtyard by Marriott Detroit Troy",
        url="https://www.marriott.com/en-us/hotels/dtttr-courtyard-detroit-troy/overview/",
        outcome="PUBLICATION_CANDIDATE",
        artifact="P3-13-courtyard-detroit-troy.txt",
        sha="2f567d6cbd77ad2415182cd187f429d76bb2db998f4bcffa1a057430475caaf4",
        quote="Pet Policy\n\nPets Welcome\n\nPet fee $20/day with $100/stay nonrefundable clean fee excludes Service Animals\n\nNon-Refundable Pet Fee Per Stay: $100.00\n\nNon-Refundable Pet Fee Per Night: $20.00\n\nMaximum Pet Weight: 30.0lbs\n\nMaximum Number of Pets in Room: 2",
        facts=[
            dict(field="pets_allowed", value=True, quote="Pets Welcome"),
            dict(field="pet_fee", value=dict(amount_cents=2000, currency="USD", basis="per_night", refundable=False),
                quote="Non-Refundable Pet Fee Per Night: $20.00"),
            dict(field="other_charges", value=[dict(kind="cleaning_fee", amount_cents=10000, currency="USD",
                                                    basis="per_stay", refundable=False)],
                quote="Pet fee $20/day with $100/stay nonrefundable clean fee"),
            dict(field="weight_limit", value=dict(value=30, unit="lb", operator="lte", scope="per_pet"),
                quote="Maximum Pet Weight: 30.0lbs"),
            dict(field="pet_count_limit", value=2, quote="Maximum Number of Pets in Room: 2"),
            dict(field="pet_count_scope", value="room", quote="Maximum Number of Pets in Room: 2"),
        ], withheld=[],
        service_animal=dict(stated=True, charges_stated="no_charge", quote="excludes Service Animals"),
        note="Same Courtyard franchise-standard fee shape as Detroit Dearborn "
             "(#10); weight limit differs (30lbs vs 35lbs), confirming these are "
             "real per-property values, not copy-paste."),
    dict(n=14, key="daxton hotel", hotel="Daxton Hotel", url="https://daxtonhotel.com/",
        outcome="POLICY_NOT_FOUND", artifact=None, sha=None, quote=None, facts=[], withheld=[],
        note="Checked: homepage, /daxton-guide/, /rooms/, and the site's full "
             "page-sitemap.xml (no faq/policy/pet page listed). Zero pet mentions "
             "anywhere. SOURCE SILENCE IS ABSENCE."),
    dict(n=15, key="dearborn inn autograph collection", hotel="Dearborn Inn, Autograph Collection",
        url="https://www.marriott.com/en-us/hotels/dtwdk-dearborn-inn-autograph-collection/overview/",
        outcome="VERIFIED_NO_PETS_CANDIDATE",
        artifact="P3-15-dearborn-inn-autograph-collection.txt",
        sha="ce5093b05cffcd6eb4246d357cfb67ca0683337d5a8ddb4bc157441bf02fb92a",
        quote="Does Dearborn Inn, Autograph Collection allow pets?\n\nNo, pets are not allowed at Dearborn Inn, Autograph Collection.",
        facts=[dict(field="pets_allowed", value=False,
                   quote="No, pets are not allowed at Dearborn Inn, Autograph Collection.")],
        withheld=[],
        note="No 'Pet Policy' amenity field rendered for this property; the FAQ "
             "accordion answer ('Does ... allow pets?') required an attended "
             "click to expand -- confirmed by JS .click() dispatch."),
    dict(n=16, key="delta hotels by marriott detroit novi", hotel="Delta Hotels by Marriott Detroit Novi",
        url="https://www.marriott.com/en-us/hotels/dtwdf-delta-hotels-detroit-novi/overview/",
        outcome="PUBLICATION_CANDIDATE",
        artifact="P3-16-delta-hotels-detroit-novi.txt",
        sha="8c40c1032178ecdbf8a5409c7fb36f9dd7a17078f5b9cb1dbda09e7aac6e4c9d",
        quote="Pet Policy\n\nPets Welcome\n\nNon-refundable $80 pet fee per 7 day stay.\n\nNon-Refundable Pet Fee Per Stay: $80.00\n\nMaximum Pet Weight: 50.0lbs\n\nMaximum Number of Pets in Room: 2",
        facts=[
            dict(field="pets_allowed", value=True, quote="Pets Welcome"),
            dict(field="weight_limit", value=dict(value=50, unit="lb", operator="lte", scope="per_pet"),
                quote="Maximum Pet Weight: 50.0lbs"),
            dict(field="pet_count_limit", value=2, quote="Maximum Number of Pets in Room: 2"),
            dict(field="pet_count_scope", value="room", quote="Maximum Number of Pets in Room: 2"),
        ],
        withheld=[dict(field="pet_fee", reason_code="SCHEMA_CANNOT_REPRESENT",
                       reason="Prose ties the $80 charge to a specific 'per 7 day "
                              "stay' period that the schema's fee basis enum "
                              "(per_night/per_day/per_stay) cannot represent; the "
                              "structured field's flat 'Per Stay: $80.00' claim "
                              "does not preserve that qualification.",
                       quotes=["Non-refundable $80 pet fee per 7 day stay.",
                              "Non-Refundable Pet Fee Per Stay: $80.00"])],
        note="Property page title shortens to 'Delta Hotels Detroit Novi' but "
             "address/postal match the census identity exactly (Farmington "
             "Hills city, per the corrected identity from ROUTING-REPAIR-001)."),
    dict(n=17, key="detroit foundation hotel", hotel="Detroit Foundation Hotel",
        url="https://detroitfoundationhotel.com/", outcome="PUBLICATION_CANDIDATE",
        artifact="P3-17-detroit-foundation-hotel.txt",
        sha="b5b07f9fa9023be5224c67e157821e6ccfdc9a942678aad9405488cfd656970e",
        quote="PET-FRIENDLY HOTELS IN DETROIT: WHERE YOUR FURRY FRIENDS ARE WELCOME!\n\nEnjoy a Detroit hotel where every bark and wag is welcomed. At Foundation Hotel, we cherish our pups just as much as you do, and we're rolling out the red carpet for our four-legged guests, because they deserve nothing but the very best.\n\nPAMPER YOUR PUP\n\nWhy travel and leave your best friend at home? Our dog-friendly hotel loves to pamper your pooch! Our Pet Add-On includes:\n\nDog Treats made on-property by our professional pastry-chef\nFire Hydrant Chew Toy\nWaste Bags\nOur $75 Pet Fee\nRooms will also be equipped with a doggie bed, food and water bowls (these are not to be removed from the room)\n\nPlease notify the Front Desk if you have more than one animal prior to your arrival.",
        facts=[
            dict(field="pets_allowed", value=True,
                quote="At Foundation Hotel, we cherish our pups just as much as you do"),
            dict(field="species", value=dict(dogs="accepted"),
                quote="Our dog-friendly hotel loves to pamper your pooch!"),
        ],
        withheld=[dict(field="pet_fee", reason_code="ARTIFACT_INSUFFICIENT",
                       reason="The $75 fee is stated with no basis word at all "
                              "(not 'per night', not 'per stay') anywhere on the "
                              "dedicated pets page.",
                       quotes=["Our $75 Pet Fee"])],
        note="Dedicated /experience/pets/ page, reached via a 'LEARN MORE' link "
             "from the amenities page. A 'Barkside Dog Bar in Kansas City' "
             "mention on the same page is marketing content about a SIBLING "
             "property in a different city -- not used as evidence for this "
             "property's own policy. Only dogs are mentioned throughout; cats "
             "are not addressed (species left silent for cats, not marked "
             "prohibited)."),
    dict(n=18, key="detroit marriott livonia", hotel="Detroit Marriott Livonia",
        url="https://www.marriott.com/en-us/hotels/dtwli-detroit-marriott-livonia/overview/",
        outcome="PUBLICATION_CANDIDATE",
        artifact="P3-18-detroit-marriott-livonia.txt",
        sha="ca79395cfff183744f4589eb0a159c0d9a48f68a9edb62dd770cfd671d08fe43",
        quote="Pet Policy\n\nPets Welcome\n\nDogs Only. Cats are not permitted\n\nNon-Refundable Pet Fee Per Stay: $150.00\n\nMaximum Pet Weight: 50.0lbs\n\nMaximum Number of Pets in Room: 2",
        facts=[
            dict(field="pets_allowed", value=True, quote="Pets Welcome"),
            dict(field="species", value=dict(dogs="accepted", cats="prohibited"),
                quote="Dogs Only. Cats are not permitted"),
            dict(field="pet_fee", value=dict(amount_cents=15000, currency="USD", basis="per_stay", refundable=False),
                quote="Non-Refundable Pet Fee Per Stay: $150.00"),
            dict(field="weight_limit", value=dict(value=50, unit="lb", operator="lte", scope="per_pet"),
                quote="Maximum Pet Weight: 50.0lbs"),
            dict(field="pet_count_limit", value=2, quote="Maximum Number of Pets in Room: 2"),
            dict(field="pet_count_scope", value="room", quote="Maximum Number of Pets in Room: 2"),
        ], withheld=[],
        note="Explicit species restriction stated directly ('Dogs Only. Cats are "
             "not permitted'), not inferred."),
    dict(n=19, key="detroit marriott southfield", hotel="Detroit Marriott Southfield",
        url="https://www.marriott.com/en-us/hotels/dtwsl-detroit-marriott-southfield/overview/",
        outcome="VERIFIED_NO_PETS_CANDIDATE",
        artifact="P3-19-detroit-marriott-southfield.txt",
        sha="98573258de37306d44b8c786e73518598223ac639257ff6a95ded84bb407d4bb",
        quote="Pet Policy\n\nPets Not Allowed",
        facts=[dict(field="pets_allowed", value=False, quote="Pets Not Allowed")], withheld=[],
        note="Structured 'Pet Policy' field."),
    dict(n=20, key="detroit marriott troy", hotel="Detroit Marriott Troy",
        url="https://www.marriott.com/en-us/hotels/dtttt-detroit-marriott-troy/overview/",
        outcome="VERIFIED_NO_PETS_CANDIDATE",
        artifact="P3-20-detroit-marriott-troy.txt",
        sha="98573258de37306d44b8c786e73518598223ac639257ff6a95ded84bb407d4bb",
        quote="Pet Policy\n\nPets Not Allowed",
        facts=[dict(field="pets_allowed", value=False, quote="Pets Not Allowed")], withheld=[],
        note="Structured 'Pet Policy' field."),
    dict(n=21, key="detroit metro airport marriott", hotel="Detroit Metro Airport Marriott",
        url="https://www.marriott.com/en-us/hotels/dtwrm-detroit-metro-airport-marriott/overview/",
        outcome="PUBLICATION_CANDIDATE",
        artifact="P3-21-detroit-metro-airport-marriott.txt",
        sha="d8059a175ef77a5c4619e987776b3cc165fb5eaa272f8f9582502d7b57f35430",
        quote="Pet Policy\n\nPets Welcome\n\nNon-Refundable Pet Fee Per Stay: $50.00\n\nMaximum Pet Weight: 45.0lbs\n\nMaximum Number of Pets in Room: 2",
        facts=[
            dict(field="pets_allowed", value=True, quote="Pets Welcome"),
            dict(field="pet_fee", value=dict(amount_cents=5000, currency="USD", basis="per_stay", refundable=False),
                quote="Non-Refundable Pet Fee Per Stay: $50.00"),
            dict(field="weight_limit", value=dict(value=45, unit="lb", operator="lte", scope="per_pet"),
                quote="Maximum Pet Weight: 45.0lbs"),
            dict(field="pet_count_limit", value=2, quote="Maximum Number of Pets in Room: 2"),
            dict(field="pet_count_scope", value="room", quote="Maximum Number of Pets in Room: 2"),
        ], withheld=[],
        note="Structured 'Pet Policy' field, no prose, no contradiction."),
    dict(n=22, key="el moore lodge", hotel="El Moore Lodge", url="https://elmoore.com/lodge/",
        outcome="VERIFIED_NO_PETS_CANDIDATE",
        artifact="P3-22-el-moore-lodge.txt",
        sha="f8153b53b97935e6a1dbfe68ecd59cd872f526ce1afe367e9494cec6b9f11186",
        phone="313-924-4374",
        quote="PETS\n\nWhile we love animals, we unfortunately cannot accommodate any pets at the Lodge, with the exception of service animals. We are very lucky to have a wonderful dog daycare, Canine to Five, within a few blocks of our Lodge. They may be a great option for you if you are traveling with a pet.",
        facts=[dict(field="pets_allowed", value=False,
                   quote="we unfortunately cannot accommodate any pets at the Lodge, with the exception of service animals")],
        withheld=[],
        service_animal=dict(stated=True, charges_stated="not_addressed",
                            quote="with the exception of service animals"),
        note="Elementor accordion tab ('PETS') on the property's own /lodge/ "
             "page; required a JS .click() on the tab title to expand. The "
             "mention of a nearby third-party dog daycare is a courtesy referral, "
             "not part of this property's own pet policy."),
    dict(n=23, key="element detroit at the metropolitan", hotel="Element Detroit at the Metropolitan",
        url="https://www.marriott.com/en-us/hotels/dtwel-element-detroit-at-the-metropolitan/overview/",
        outcome="PUBLICATION_CANDIDATE",
        artifact="P3-23-element-detroit-metropolitan.txt",
        sha="a4f3b517016081ebd18751dc6412a4a826c088cb3631f2ba3414b2e93151e852",
        quote="Pet Policy\n\nPets Welcome\n\nPets Welcome - 1 animal per room. Pet Policy to be signed upon arrival.\n\nMaximum Pet Weight: 40.0lbs\n\nMaximum Number of Pets in Room: 1",
        facts=[
            dict(field="pets_allowed", value=True, quote="Pets Welcome"),
            dict(field="weight_limit", value=dict(value=40, unit="lb", operator="lte", scope="per_pet"),
                quote="Maximum Pet Weight: 40.0lbs"),
            dict(field="pet_count_limit", value=1, quote="Maximum Number of Pets in Room: 1"),
            dict(field="pet_count_scope", value="room", quote="Maximum Number of Pets in Room: 1"),
        ], withheld=[],
        note="No fee amount is stated anywhere on the page (only 'Pet Policy to "
             "be signed upon arrival') -- pet_fee is simply absent from the "
             "proposed facts, not withheld with a reason, since there is nothing "
             "to withhold."),
    dict(n=24, key="extended stay america detroit ann arbor university south",
        hotel="Extended Stay America Detroit Ann Arbor University South",
        url="https://www.extendedstayamerica.com/hotels/mi/detroit/ann-arbor-university-south",
        outcome="PUBLICATION_CANDIDATE",
        artifact="P3-24-extended-stay-america-ann-arbor-university-south.txt",
        sha="657cf6ece88ec716cad040977fdc18bea068a0f3e76aec032d8f749efae883ef",
        phone="1-734-997-7623",
        quote="Is Extended Stay America Detroit - Ann Arbor - University South pet friendly?\n\nYes. Extended Stay America Detroit - Ann Arbor - University South offers pet-friendly rooms, so you can bring your furry companion along for your stay.",
        facts=[dict(field="pets_allowed", value=True,
                   quote="Yes. Extended Stay America Detroit - Ann Arbor - University South offers pet-friendly rooms, so you can bring your furry companion along for your stay.")],
        withheld=[],
        note="FAQ accordion (Bootstrap 'card-header'/'collapse' pair, id "
             "propertyFaqHeading4/propertyFaqCollapse4) whose answer text is "
             "present in the DOM but not exposed by a plain element .click() -- "
             "read directly from the sibling '.collapse' element's textContent "
             "instead of relying on the click to reveal it visually. No fee, "
             "weight, or count information exists anywhere on the page."),
    dict(n=25, key="fairfield inn and suites ann arbor ypsilanti",
        hotel="Fairfield Inn & Suites Ann Arbor Ypsilanti",
        url="https://www.marriott.com/en-us/hotels/arbfy-fairfield-inn-and-suites-ann-arbor-ypsilanti/overview/",
        outcome="VERIFIED_NO_PETS_CANDIDATE",
        artifact="P3-25-fairfield-ann-arbor-ypsilanti.txt",
        sha="a2129edc9e640afa035620702d00e4e9fc5fc70d5938bb64b1a588822a438504",
        quote="Pet Policy\n\nPets Not Allowed\n\nPets not allowed-Service animals only",
        facts=[dict(field="pets_allowed", value=False, quote="Pets Not Allowed")], withheld=[],
        service_animal=dict(stated=True, charges_stated="not_addressed",
                            quote="Pets not allowed-Service animals only"),
        note="Structured 'Pet Policy' field."),
    dict(n=26, key="fairfield inn and suites detroit farmington hills",
        hotel="Fairfield Inn & Suites Detroit Farmington Hills",
        url="https://www.marriott.com/en-us/hotels/dtwfh-fairfield-inn-and-suites-detroit-farmington-hills/overview/",
        outcome="PUBLICATION_CANDIDATE",
        artifact="P3-26-fairfield-detroit-farmington-hills.txt",
        sha="f4a18bc60118453785bafa32f80c545ac5eb82e705fa7f4eac06b1b343df8eae",
        quote="Pet Policy\n\nPets Welcome\n\nPet friendly hotel. $150 flat fee. Nonrefundable.\n\nMaximum Pet Weight: 50.0lbs\n\nMaximum Number of Pets in Room: 2",
        facts=[
            dict(field="pets_allowed", value=True, quote="Pets Welcome"),
            dict(field="pet_fee", value=dict(amount_cents=15000, currency="USD", basis="per_stay", refundable=False),
                quote="Pet friendly hotel. $150 flat fee. Nonrefundable."),
            dict(field="weight_limit", value=dict(value=50, unit="lb", operator="lte", scope="per_pet"),
                quote="Maximum Pet Weight: 50.0lbs"),
            dict(field="pet_count_limit", value=2, quote="Maximum Number of Pets in Room: 2"),
            dict(field="pet_count_scope", value="room", quote="Maximum Number of Pets in Room: 2"),
        ], withheld=[],
        note="'Flat fee' is treated as basis=per_stay directly, not an inference "
             "-- 'flat' is the source's own word for a single, non-prorated "
             "charge, which is what per_stay means."),
    dict(n=27, key="fairfield inn and suites detroit troy", hotel="Fairfield Inn & Suites Detroit Troy",
        url="https://www.marriott.com/en-us/hotels/dtwft-fairfield-inn-and-suites-detroit-troy/overview/",
        outcome="VERIFIED_NO_PETS_CANDIDATE",
        artifact="P3-27-fairfield-detroit-troy.txt",
        sha="8601a3d7773723bb892438578840e926b7ef59e507ad7f552950fb8063241739",
        quote="Pet Policy\n\nPets Not Allowed\n\nNo pets allowed-service animals only",
        facts=[dict(field="pets_allowed", value=False, quote="Pets Not Allowed")], withheld=[],
        service_animal=dict(stated=True, charges_stated="not_addressed",
                            quote="No pets allowed-service animals only"),
        note="Structured 'Pet Policy' field."),
    dict(n=28, key="fairfield inn and suites by marriott detroit livonia",
        hotel="Fairfield Inn & Suites by Marriott Detroit Livonia",
        url="https://www.marriott.com/en-us/hotels/dtwfl-fairfield-inn-and-suites-detroit-livonia/overview/",
        outcome="VERIFIED_NO_PETS_CANDIDATE",
        artifact="P3-28-fairfield-detroit-livonia.txt",
        sha="98573258de37306d44b8c786e73518598223ac639257ff6a95ded84bb407d4bb",
        quote="Pet Policy\n\nPets Not Allowed",
        facts=[dict(field="pets_allowed", value=False, quote="Pets Not Allowed")], withheld=[],
        note="Structured 'Pet Policy' field."),
    dict(n=29, key="fairfield inn ann arbor", hotel="Fairfield Inn Ann Arbor",
        url="https://www.marriott.com/en-us/hotels/arbfi-fairfield-inn-ann-arbor/overview/",
        outcome="VERIFIED_NO_PETS_CANDIDATE",
        artifact="P3-29-fairfield-inn-ann-arbor.txt",
        sha="8601a3d7773723bb892438578840e926b7ef59e507ad7f552950fb8063241739",
        quote="Pet Policy\n\nPets Not Allowed\n\nNo pets allowed-service animals only",
        facts=[dict(field="pets_allowed", value=False, quote="Pets Not Allowed")], withheld=[],
        service_animal=dict(stated=True, charges_stated="not_addressed",
                            quote="No pets allowed-service animals only"),
        note="Structured 'Pet Policy' field, identical text to Fairfield Detroit "
             "Troy (#27)."),
    dict(n=30, key="four points by sheraton detroit novi", hotel="Four Points by Sheraton Detroit Novi",
        url="https://www.marriott.com/en-us/hotels/dtwfn-four-points-detroit-novi/overview/",
        outcome="VERIFIED_NO_PETS_CANDIDATE",
        artifact="P3-30-four-points-detroit-novi.txt",
        sha="98573258de37306d44b8c786e73518598223ac639257ff6a95ded84bb407d4bb",
        quote="Pet Policy\n\nPets Not Allowed",
        facts=[dict(field="pets_allowed", value=False, quote="Pets Not Allowed")], withheld=[],
        note="Structured 'Pet Policy' field."),
]


def load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=OrderedDict)


def write_lf(path: Path, doc) -> None:
    text = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text.replace("\r\n", "\n"), encoding="utf-8", newline="\n")


def verify_artifacts() -> None:
    """Every claimed artifact file must exist and its committed sha256 must
    match the file's actual bytes."""
    for row in ROWS:
        if row["artifact"] is None:
            continue
        p = RAW_DIR / row["artifact"]
        if not p.is_file():
            raise SystemExit("STOP: missing artifact file %s" % p)
        actual = hashlib.sha256(p.read_bytes()).hexdigest()
        if actual != row["sha"]:
            raise SystemExit("STOP: hash mismatch for %s: committed=%s actual=%s"
                             % (row["artifact"], row["sha"], actual))


def build_results() -> Dict:
    results = []
    for row in ROWS:
        entry = OrderedDict([
            ("queue_id", "DTW-P3-%02d" % row["n"]),
            ("identity_key", row["key"]),
            ("hotel", row["hotel"]),
            ("final_url", row["url"]),
            ("outcome", row["outcome"]),
        ])
        if row["artifact"]:
            entry["artifact_file"] = row["artifact"]
            entry["artifact_kind"] = "text_extract"
            entry["artifact_sha256"] = row["sha"]
        results.append(entry)
    return OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-capture-pass3-results/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("prior_commit", PRIOR_COMMIT),
        ("note", "Claude attended-browser capture of the prepared 30-row "
                 "EVIDENCE_READY queue from ROUTING-EXPANSION-004. No GPT/Grok "
                 "browser capture used. No founder decision recorded here, no "
                 "authority applied. published=7 and verified_no_pets=7 "
                 "unchanged. Screenshot capture was unavailable this session; "
                 "artifacts are exact text extracts (artifact_kind=text_extract) "
                 "instead of operator_screenshot."),
        ("count", len(results)), ("results", results),
    ])


def build_packet(census_by_key: Dict[str, Dict]) -> Dict:
    candidates = []
    for row in ROWS:
        crow = census_by_key[row["key"]]
        identity_binding = OrderedDict([("name", True)])
        if row.get("artifact"):
            identity_binding["street"] = True
            identity_binding["zip"] = True
        if row.get("phone"):
            identity_binding["phone"] = True
        identity_binding["bound"] = row["outcome"] != "POLICY_NOT_FOUND"

        entry = OrderedDict([
            ("decision_id", "DTW-P3-%02d" % row["n"]),
            ("queue_id", "DTW-P3-%02d" % row["n"]),
            ("hotel", row["hotel"]), ("identity_key", row["key"]),
            ("corridor", CORRIDOR_BY_KEY[row["key"]]),
            ("address", crow["address"]), ("city", crow["city"]),
            ("state", crow["state"]), ("postal_code", crow["postal_code"]),
            ("phone", row.get("phone") or crow["phone"]),
            ("official_url", crow["official_url"]), ("final_url", row["url"]),
            ("identity_binding", identity_binding),
        ])
        if row["artifact"]:
            entry["artifact_sha256"] = row["sha"]
            entry["artifact_file"] = row["artifact"]
            entry["artifact_kind"] = "text_extract"
            entry["source_grade"] = "GRADE_PT1_FIRST_PARTY"
        entry["exact_quote"] = row["quote"] or ""
        entry["proposed_schema_1_2_facts"] = row["facts"]
        if row.get("service_animal"):
            entry["service_animal_statement"] = row["service_animal"]
        entry["withheld_fields"] = row["withheld"]
        entry["general_note"] = row["note"]
        entry["outcome"] = row["outcome"]
        recommended = {
            "PUBLICATION_CANDIDATE": "APPROVE_PUBLISH",
            "VERIFIED_NO_PETS_CANDIDATE": "APPROVE_VERIFIED_NO_PETS",
            "POLICY_NOT_FOUND": "HOLD_FOR_FURTHER_RESEARCH",
        }[row["outcome"]]
        entry["recommended_founder_decision"] = recommended
        candidates.append(entry)

    return OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-capture-pass3-founder-review-packet/1.0"),
        ("work_order", WORK_ORDER), ("as_of", AS_OF), ("market_id", MARKET),
        ("note", "PROPOSED facts for founder review only. No founder decision is "
                 "recorded in this pass; no hotel_policy_facts_detroit-ann-arbor-"
                 "mi.json or hotel_exclusions.json entries were written. "
                 "published=7 and verified_no_pets=7 remain unchanged."),
        ("count", len(candidates)), ("candidates", candidates),
        ("status", "AWAITING_FOUNDER_REVIEW"),
    ])


def build_manifest() -> Dict:
    items = []
    for row in ROWS:
        if not row["artifact"]:
            continue
        items.append(OrderedDict([
            ("queue_id", "DTW-P3-%02d" % row["n"]),
            ("identity_key", row["key"]),
            ("artifact_file", "raw/%s" % row["artifact"]),
            ("artifact_sha256", row["sha"]),
            ("artifact_kind", "text_extract"),
            ("source_url", row["url"]),
            ("captured_at", AS_OF),
            ("capture_method", "attended_browser"),
        ]))
    return OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-capture-pass3-evidence-manifest/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("raw_evidence_location",
         "data/worker_runs/pettripfinder/detroit-ann-arbor-capture-pass3-001/raw/ "
         "(gitignored; this manifest is the committed index)"),
        ("count", len(items)), ("items", items),
    ])


def run() -> None:
    verify_artifacts()
    census_doc = load_json(CENSUS_PATH)
    census_by_key = {r["identity_key"]: r for r in census_doc["hotels"]}
    for row in ROWS:
        if row["key"] not in census_by_key:
            raise SystemExit("STOP: %r not in committed census" % row["key"])

    results_doc = build_results()
    packet_doc = build_packet(census_by_key)
    manifest_doc = build_manifest()

    write_lf(RESULTS_PATH, results_doc)
    write_lf(PACKET_PATH, packet_doc)
    write_lf(MANIFEST_PATH, manifest_doc)

    outcomes: Dict[str, int] = {}
    for row in ROWS:
        outcomes[row["outcome"]] = outcomes.get(row["outcome"], 0) + 1
    print("DETROIT_CAPTURE_PASS3_TOTAL: 30")
    print("CAPTURED: 30")
    print("PUBLICATION_GRADE: %d" % sum(1 for r in ROWS if r["artifact"]))
    print("PUBLICATION_CANDIDATES: %d" % outcomes.get("PUBLICATION_CANDIDATE", 0))
    print("VERIFIED_NO_PETS_CANDIDATES: %d" % outcomes.get("VERIFIED_NO_PETS_CANDIDATE", 0))
    print("POLICY_NOT_FOUND: %d" % outcomes.get("POLICY_NOT_FOUND", 0))
    print("ACCESS_BLOCKED: %d" % outcomes.get("ACCESS_BLOCKED", 0))
    print("IDENTITY_UNCERTAIN: %d" % outcomes.get("IDENTITY_UNCERTAIN", 0))
    print("CAPTURE_FAILED: %d" % outcomes.get("CAPTURE_FAILED", 0))
    print("SOURCE_AMBIGUOUS: %d" % outcomes.get("SOURCE_AMBIGUOUS", 0))
    print("FOUNDER_REVIEW_ROWS: 30")
    print("\nWROTE: %s, %s, %s" % (RESULTS_PATH.name, PACKET_PATH.name, MANIFEST_PATH.name))


if __name__ == "__main__":
    run()
