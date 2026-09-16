"""PTF-ORLANDO-FL-HARDENED-V2-SOURCE-READY-001 -- Phase 12G (read): the independents' own policy / FAQ / pet pages.

orlando_fl_v2_policy_pages_lane_001 persisted each independent site and copied every sentence naming pets or dogs. This
table is the READ: for each identity whose own site answers the pet question, the exact sentences (verbatim, in page
order) that state the policy and the facts they state explicitly. Nothing is inferred:

  * a row is emitted only when the site BOUND to the census identity (house number and postal code, or phone, on the
    site's own page) -- a name never binds;
  * every quoted sentence must be present, character for character, in the persisted sentences of one page of that
    site; a sentence that is not found drops the whole row (fail closed, recorded in `dropped`);
  * a fact is written only when a quoted sentence states it (a count, a weight, dogs only) -- amenity words such as
    "Pet Getaway" or a dog-park chip are not a policy and are never quoted here;
  * negation-bearing answers ("we do not allow pets", "service animals but not pets") are refusals, not allowances.

Identities whose site did not answer (Caribe Royale, Pestana, The Alfond Inn's dining guide, Saratoga's apartment
leasing page, ...) have no row here and keep their partition disposition. A site whose own name differs from the
census name at the same address (Baymont by Wyndham -> "The Floridian Hotel") is not read here: that is an identity
question, not a policy read.

Output: launch_packages/pettripfinder/markets/staging/orlando-fl/raw_captures/independent_rows.json
"""
from __future__ import annotations

import json
import os
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
RAW = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "staging", "orlando-fl", "raw_captures")
LANE = os.path.join(RAW, "policy_pages_rows.json")
OUT = os.path.join(RAW, "independent_rows.json")

# identity_key -> (page-url fragment, [verbatim sentences], extraction)
READS = OrderedDict([
    ("avanti international resort", ("avantiresort.com", [
        "Q: Is Avanti Resort pet-friendly?", "A: Yes, we are a dog-friendly resort."],
        {"pets_allowed": True, "species_allowed": ["dog"]})),
    ("celebration suites", ("celebrationsuitesfl.com/en/faq", [
        "Does the hotel accept pets?", "Up to 2 pets per room (maximum 35 pounds each) are allowed for US$35 + 13."],
        {"pets_allowed": True, "pet_count_limit": 2, "weight_limit": 35, "weight_limit_unit": "lb"})),
    ("floridays resort orlando", ("floridaysresortorlando.com", [
        "Q: Is Floridays resort pet friendly?", "A: Yes, we welcome dogs under 75 pounds."],
        {"pets_allowed": True, "species_allowed": ["dog"], "weight_limit": 75, "weight_limit_unit": "lb"})),
    ("grand hotel universal", ("grandhotelorlando.com/faq", [
        "SERVICE ANIMALS With the exception of Service Animals, Pets are not allowed at The Grand Hotel Orlando at "
        "Universal Blvd."],
        {"pets_allowed": False})),
    ("holiday inn orlando disney springs area", ("hiorlando.com/frequently-asked-questions", [
        "Do you allow pets?", "No, we do not allow pets."],
        {"pets_allowed": False})),
    ("margaritaville resort orlando", ("margaritaville-resort-orlando/faq", [
        "Do you allow pets?", "Yes, we are a pet-friendly resort."],
        {"pets_allowed": True})),
    ("ramada plaza resort and suites international drive orlando", ("ramadaorlando.com/faq", [
        "Are pets permitted in the hotel?",
        "Unfortunately, pets are not permitted at the hotel except for service animals with proper credentials."],
        {"pets_allowed": False})),
    ("rosen centre hotel", ("rosencentre.com/accommodations/dog-friendly-hotel", [
        "At Rosen Centre ® , we consider dogs to be part of the family which is why we are a dog friendly hotel.",
        "Rosen Hotels & Resorts Dog Policy At Rosen Hotels & Resorts, we recognize that dogs are family and are proud "
        "to welcome up to one canine guests per room."],
        {"pets_allowed": True, "species_allowed": ["dog"], "pet_count_limit": 1})),
    ("rosen plaza hotel", ("rosenplaza.com/accommodations/dog-friendly-hotel", [
        "At Rosen Plaza, we consider dogs to be part of the family which is we are a dog friendly hotel.",
        "Rosen Hotels & Resorts Dog Policy At Rosen Hotels & Resorts, we recognize that dogs are family and are proud "
        "to welcome up to one canine guests per room."],
        {"pets_allowed": True, "species_allowed": ["dog"], "pet_count_limit": 1})),
    ("rosen shingle creek", ("rosenshinglecreek.com/accommodations/dog-friendly-hotel", [
        "Stay at the luxurious Rosen Shingle Creek and you won’t have to leave your dog friend behind.",
        "Rosen Hotels & Resorts Dog Policy At Rosen Hotels & Resorts, we recognize that dogs are family and are proud "
        "to welcome up to one canine guests per room."],
        {"pets_allowed": True, "species_allowed": ["dog"], "pet_count_limit": 1})),
    ("rosen inn at pointe orlando", ("roseninn9000.com", [
        "Are you a dog-friendly hotel?", "Yes, dogs are welcome!"],
        {"pets_allowed": True, "species_allowed": ["dog"]})),
    ("rosen inn closest to universal", ("roseninn6327.com", [
        "Are dogs allowed at Rosen Inn?", "Yes, Rosen Inn closest to Universal is a proud dog-friendly hotel.",
        "Up to 2 dogs are allowed per room, and proof of vaccinations is required."],
        {"pets_allowed": True, "species_allowed": ["dog"], "pet_count_limit": 2})),
    ("rosen inn international", ("roseninn7600.com", [
        "Are you a dog-friendly hotel?", "Yes, dogs are welcome!"],
        {"pets_allowed": True, "species_allowed": ["dog"]})),
    ("rosen inn lake buena vista", ("rosenlbv.com", [
        "Are dogs allowed at Rosen Inn Lake Buena Vista?", "Yes, Rosen Inn Lake Buena Vista is a proud dog-friendly hotel.",
        "Up to 2 dogs are allowed per room, and proof of vaccinations is required."],
        {"pets_allowed": True, "species_allowed": ["dog"], "pet_count_limit": 2})),
    ("the florida hotel and conference center", ("thefloridahotelorlando.com", [
        "four What Makes Us Special Furry Friends Welcome As one of the most convenient pet-friendly hotels in Orlando, "
        "The Florida Hotel & Conference Center is pleased to welcome your special animal companions!"],
        {"pets_allowed": True})),
    ("the grove resort and water park orlando", ("groveresortorlando.com/faq", [
        "Q: Is the resort pet friendly?", "A: The resort welcomes service animals but not pets."],
        {"pets_allowed": False})),
    ("the inn at celebration", ("theinnatcelebration.com/faq", [
        "Does The Inn at Celebration allow pets?", "Yes, pets are welcome!"],
        {"pets_allowed": True})),
    ("the point hotel and suites", ("thepointorlando.com/faq", [
        "Are pets allowed?", "To maintain a comfortable environment for all guests, we do not allow pets."],
        {"pets_allowed": False})),
    ("vacation village at parkway", ("vacation_village_parkway/faq.html", [
        "Is Vacation Village at Parkway pet-friendly?",
        "Dogs must be less than 35 pounds, and the resort must approve before arrival."],
        {"pets_allowed": True, "species_allowed": ["dog"], "weight_limit": 35, "weight_limit_unit": "lb"})),
])


def main():
    lane = json.load(open(LANE, encoding="utf-8"))
    by_key = {r["identity_key"]: r for r in lane["rows"]}
    rows, dropped = [], []
    for key, (frag, sentences, ext) in READS.items():
        r = by_key.get(key)
        if not r or not r.get("bound"):
            dropped.append(OrderedDict([("identity_key", key), ("why", "SITE_NOT_BOUND_TO_THE_CENSUS_IDENTITY")]))
            continue
        page = next((p for p in r["pages"] if frag in p["url"] and all(s in p["pet_sentences"] for s in sentences)), None)
        if page is None:
            dropped.append(OrderedDict([("identity_key", key), ("why", "QUOTED_SENTENCE_NOT_FOUND_ON_THE_PERSISTED_PAGE")]))
            continue
        rows.append(OrderedDict([
            ("identity_key", key), ("n", r["name"]), ("u", page["url"]), ("final_url", page["url"]),
            ("st", r["street"]), ("z", (r["postal"] or "")[:5]), ("ph", r.get("phone")),
            ("h", page["sha256"]), ("b", page["bytes"]), ("q", " ".join(sentences)), ("extraction", ext),
            ("binding", "HOUSE_NUMBER_AND_POSTAL_CODE_OR_PHONE_ON_THE_SITES_OWN_PAGES"),
        ]))
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(OrderedDict([("rows", rows), ("dropped", dropped)]), fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("independent reads", len(rows), "dropped", dropped)


if __name__ == "__main__":
    main()
