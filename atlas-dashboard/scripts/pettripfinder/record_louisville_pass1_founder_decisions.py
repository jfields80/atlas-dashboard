"""Record D001-D006 in the Louisville Pass 1 founder review packet.

Does not apply partition, census, exclusion, or production-policy authority.
Does not execute the next capture batch.

    python -m scripts.pettripfinder.record_louisville_pass1_founder_decisions
"""
from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path

from scripts.pettripfinder.census_partition_builder import write_json

REPO = Path(__file__).resolve().parents[2]
PKG = REPO / "launch_packages" / "pettripfinder"
PACKET_PATH = PKG / "markets" / "reports" / "louisville_pass1_founder_review_packet.json"
BATCH_PATH = PKG / "markets" / "reports" / "louisville_pass2_capture_batch_prepared.json"
CENSUS_PATH = PKG / "identity_census" / "louisville-ky.json"
PARTITION_PATH = PKG / "louisville_final_partition_001.json"
WORK = "PTF-LOUISVILLE-PASS1-FOUNDER-DECISIONS-001"
AS_OF = "2026-08-16"

DECISIONS = [
    OrderedDict((
        ("decision_id", "D001"),
        ("packet_id", "LVL-P1-001"),
        ("identity_key", "21c museum hotel louisville"),
        ("hotel", "21c Museum Hotel Louisville"),
        ("decision", "HOLD_PARTIAL_AFFIRMATIVE"),
        ("class", "HOLD"),
        ("authority_applied", True),
        ("publish", False),
        ("verbatim",
         "DECISION:\n\nHOLD_PARTIAL_AFFIRMATIVE\n\n"
         "Preserve the captured artifact, exact quotes, identity binding, "
         "and captured partial facts.\n"
         "Do NOT publish yet.\n"
         "Keep the property on the unresolved queue with the exact next "
         "action required to close the missing policy fields/evidence."),
    )),
    OrderedDict((
        ("decision_id", "D002"),
        ("packet_id", "LVL-P1-002"),
        ("identity_key", "bellwether hotel"),
        ("hotel", "Bellwether Hotel"),
        ("decision", "APPROVE_AFFIRMATIVE_STRUCTURED"),
        ("class", "APPROVAL_POSITIVE"),
        ("authority_applied", True),
        ("publish", False),
        ("verbatim",
         "DECISION:\n\nAPPROVE_AFFIRMATIVE_STRUCTURED\n\n"
         "Approve only the source-supported facts contained in the founder "
         "review packet.\n\n"
         "Standing rules apply:\n\n"
         "SOURCE SILENCE = ABSENCE.\n\n"
         "Do not infer:\n\n"
         "- species\n"
         "- fee basis\n"
         "- fee scope\n"
         "- refundability\n"
         "- pet count\n"
         "- weight\n"
         "- restrictions\n\n"
         "unless explicitly supported by the captured first-party artifact."),
    )),
    OrderedDict((
        ("decision_id", "D003"),
        ("packet_id", "LVL-P1-003"),
        ("identity_key", "econo lodge downtown"),
        ("hotel", "Econo Lodge Downtown"),
        ("decision", "APPROVE_VERIFIED_NO_PETS"),
        ("class", "VERIFIED_NO_PETS"),
        ("authority_applied", True),
        ("publish", False),
        ("verbatim",
         "DECISION:\n\nAPPROVE_VERIFIED_NO_PETS\n\n"
         "The explicit first-party refusal wording is approved as "
         "VERIFIED_NO_PETS.\n\n"
         "Service-animal access does not make the property pet-friendly.\n\n"
         "Bind the exclusion to the captured property-specific artifact."),
    )),
    OrderedDict((
        ("decision_id", "D004"),
        ("packet_id", "LVL-P1-004"),
        ("identity_key", "galt house hotel"),
        ("hotel", "Galt House Hotel"),
        ("decision", "APPROVE_AFFIRMATIVE_STRUCTURED"),
        ("class", "APPROVAL_POSITIVE"),
        ("authority_applied", False),
        ("publish", False),
        ("verbatim",
         "DECISION:\n\nAPPROVE_AFFIRMATIVE_STRUCTURED\n\n"
         "Approve only the explicitly supported Schema 1.2 facts in the "
         "founder packet.\n\n"
         "SOURCE SILENCE = ABSENCE.\n\n"
         "No unstated qualifier may be inferred or withheld merely because "
         "it is absent."),
    )),
    OrderedDict((
        ("decision_id", "D005"),
        ("packet_id", "LVL-P1-006"),
        ("identity_key", "hotel louisville downtown"),
        ("hotel", "Hotel Louisville Downtown"),
        ("decision", "APPROVE_VERIFIED_NO_PETS"),
        ("class", "VERIFIED_NO_PETS"),
        ("authority_applied", False),
        ("publish", False),
        ("verbatim",
         "DECISION:\n\nAPPROVE_VERIFIED_NO_PETS\n\n"
         "The first-party public hotel-room policy is approved as applying "
         "to the public Hotel Louisville lodging operation.\n\n"
         "The captured wording establishes that Hotel Louisville is not "
         "pet-friendly and only service animals are welcome.\n\n"
         "Important:\n\n"
         "- this decision applies to the public transient hotel operation\n"
         "- do not generalize the policy to unrelated Wayside Christian "
         "Mission services\n"
         "- do not merge Hotel Louisville with the separate Hospital "
         "Hospitality House identity\n"
         "- service-animal access does not convert this to pet-friendly\n\n"
         "Bind the exclusion to the captured hotel-page artifact."),
    )),
    OrderedDict((
        ("decision_id", "D006"),
        ("packet_id", "LVL-P1-007"),
        ("identity_key", "the brown hotel"),
        ("hotel", "The Brown Hotel"),
        ("decision", "APPROVE_VERIFIED_NO_PETS"),
        ("class", "VERIFIED_NO_PETS"),
        ("authority_applied", False),
        ("publish", False),
        ("verbatim",
         "DECISION:\n\nAPPROVE_VERIFIED_NO_PETS\n\n"
         "Approve the explicit first-party refusal wording as "
         "VERIFIED_NO_PETS.\n\n"
         "Bind the exclusion to the property-specific artifact.\n\n"
         "Service-animal access does not make the property pet-friendly."),
    )),
]

GENEVIEVE_NOTE = OrderedDict((
    ("identity_key", "hotel genevieve"),
    ("hotel", "Hotel Genevieve"),
    ("packet_id", "LVL-P1-005"),
    ("founder_policy_decision", "NONE"),
    ("decision_id", None),
    ("class", "NO_DECISION_BLOCKED"),
    ("keep_unresolved", True),
    ("recommended_next_state", "AWAITING_ATTENDED_CAPTURE"),
    ("lane", "HYATT_MANUAL"),
    ("verbatim",
     "NO FOUNDER POLICY DECISION.\n\n"
     "The property redirected into a Hyatt/JDV surface and the "
     "attended/automated attempt was blocked.\n\n"
     "No third-party policy wording may be substituted.\n\n"
     "Keep unresolved.\n\n"
     "Recommended next state:\n\n"
     "AWAITING_ATTENDED_CAPTURE\n\n"
     "or the current canonical equivalent.\n\n"
     "Prepare it for the Hyatt/manual lane if appropriate."),
))

NEXT_BATCH = [
    OrderedDict((
        ("order", 1),
        ("requested_name", "Omni Louisville"),
        ("identity_key", "omni louisville hotel"),
        ("canonical_name", "Omni Louisville Hotel"),
        ("official_url", "https://www.omnihotels.com/hotels/louisville"),
        ("url_grade", "brand_property"),
        ("url_class", "brand_property_url"),
        ("identity_state", "IDENTITY_CONFIRMED"),
        ("identity_binding", "URL_BOUND"),
        ("binding_notes",
         "Census and capture-ready queue bind the property-level Omni "
         "Louisville page. No Hilton/Hyatt/Marriott URL."),
        ("capture_ready", True),
        ("executed", False),
    )),
    OrderedDict((
        ("order", 2),
        ("requested_name", "Drury Inn & Suites Louisville East"),
        ("identity_key", "drury inn and suites louisville"),
        ("canonical_name", "Drury Inn and Suites Louisville"),
        ("official_url",
         "https://www.druryhotels.com/locations/louisville-ky/"
         "drury-inn-and-suites-louisville-east"),
        ("url_grade", "brand_property"),
        ("url_class", "EXACT_PROPERTY_URL_FOUND"),
        ("property_code", "0105"),
        ("identity_state", "IDENTITY_CORRECTION_REQUIRED"),
        ("identity_binding", "URL_BOUND_IDENTITY_CORRECTION_OPEN"),
        ("binding_notes",
         "Official Drury East page is bound (code 0105). Desk pass still "
         "flags IDENTITY_CORRECTION_REQUIRED: official name is Drury Inn "
         "& Suites Louisville East at 9501 Blairwood (census 9502). Phone "
         "matches. Not a Hilton/Hyatt/Marriott URL."),
        ("capture_ready", True),
        ("executed", False),
    )),
    OrderedDict((
        ("order", 3),
        ("requested_name", "Drury Inn & Suites Louisville North"),
        ("identity_key", "drury inn and suites louisville north"),
        ("canonical_name", "Drury Inn and Suites Louisville North"),
        ("official_url",
         "https://www.druryhotels.com/locations/louisville-ky/"
         "drury-inn-and-suites-louisville-north"),
        ("url_grade", "brand_property"),
        ("url_class", "EXACT_PROPERTY_URL_FOUND"),
        ("property_code", "0149"),
        ("identity_state", "IDENTITY_CONFIRMED"),
        ("identity_binding", "BOUND"),
        ("binding_notes",
         "Desk pass bound Drury North property page code 0149. Not a "
         "Hilton/Hyatt/Marriott URL."),
        ("capture_ready", True),
        ("executed", False),
    )),
    OrderedDict((
        ("order", 4),
        ("requested_name", "Best Western Green Tree Inn"),
        ("identity_key", "best western greentree inn"),
        ("canonical_name", "Best Western Greentree Inn"),
        ("official_url",
         "https://www.bestwestern.com/en_US/book/hotels-in-clarksville/"
         "best-western-green-tree-inn/propertyCode.18028.html"),
        ("url_grade", "brand_property"),
        ("url_class", "EXACT_PROPERTY_URL_FOUND"),
        ("property_code", "18028"),
        ("identity_state", "IDENTITY_CONFIRMED"),
        ("identity_binding", "BOUND"),
        ("binding_notes",
         "Desk pass bound Best Western property code 18028. Clarksville, "
         "IN. Not a Hilton/Hyatt/Marriott URL."),
        ("capture_ready", True),
        ("executed", False),
    )),
    OrderedDict((
        ("order", 5),
        ("requested_name", "Radisson Hotel Louisville North"),
        ("identity_key", "radisson hotel louisville north"),
        ("canonical_name", "Radisson Hotel Louisville North"),
        ("official_url",
         "https://www.choicehotels.com/indiana/clarksville/radisson-hotels/in043"),
        ("url_grade", "brand_property"),
        ("url_class", "BRAND_PROPERTY_URL_FOUND"),
        ("property_code", "in043"),
        ("identity_state", "IDENTITY_CONFIRMED"),
        ("identity_binding", "BOUND"),
        ("binding_notes",
         "Desk pass bound Choice/Radisson property code in043. Not a "
         "Hilton/Hyatt/Marriott URL."),
        ("capture_ready", True),
        ("executed", False),
    )),
]


def main() -> None:
    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8-sig"))
    by_decision = {d["identity_key"]: d for d in DECISIONS}
    for row in packet["rows"]:
        recorded = by_decision.get(row["identity_key"])
        if recorded:
            row["founder_decision_id"] = recorded["decision_id"]
            row["founder_decision"] = recorded["decision"]
            row["founder_decision_recorded"] = True
            row["authority_applied"] = recorded["authority_applied"]
            continue
        if row["identity_key"] == "hotel genevieve":
            row["founder_decision_id"] = None
            row["founder_decision"] = "NO_FOUNDER_POLICY_DECISION"
            row["founder_decision_recorded"] = False
            row["authority_applied"] = False
            row["recommended_next_state"] = "AWAITING_ATTENDED_CAPTURE"
            row["lane"] = "HYATT_MANUAL"

    packet["note"] = (
        "D001-D006 recorded verbatim. Hotel Genevieve has no founder "
        "policy decision. Authority applied only for prior D001-D003. "
        "D004-D006 are recorded and not applied. No production policy "
        "file. No publish, merge, or deploy."
    )
    packet["founder_approvals_written"] = True
    packet["founder_decisions_recorded"] = True
    packet["authority_applied_for"] = ["D001", "D002", "D003"]
    packet["authority_not_applied_for"] = ["D004", "D005", "D006"]
    packet["decision_count"] = 6
    packet["recorded_decision_count"] = 6
    packet["recorded_summary"] = OrderedDict((
        ("decisions_recorded", 6),
        ("approvals_positive", 2),
        ("verified_no_pets", 3),
        ("holds", 1),
        ("no_decision_blocked_rows", 1),
    ))
    packet["founder_decisions"] = DECISIONS
    packet["no_founder_policy_decision"] = [GENEVIEVE_NOTE]
    packet["applied_work_order"] = WORK
    packet["publish"] = False
    write_json(PACKET_PATH, packet)

    hotels = {h["identity_key"]: h
              for h in json.loads(CENSUS_PATH.read_text(encoding="utf-8-sig"))["hotels"]}
    items = {i["identity_key"]: i
             for i in json.loads(PARTITION_PATH.read_text(encoding="utf-8-sig"))["items"]}
    for row in NEXT_BATCH:
        hotel = hotels[row["identity_key"]]
        item = items[row["identity_key"]]
        row["census_official_url"] = hotel["official_url"]
        row["partition_official_url"] = item["official_url"]
        row["partition_final_state"] = item["final_state"]
        row["census_identity_state"] = hotel["identity_state"]
        assert hotel["official_url"] == row["official_url"]
        assert item["official_url"] == row["official_url"]
        host = row["official_url"].split("/")[2]
        assert host not in {"www.hilton.com", "www.hyatt.com", "www.marriott.com"}

    write_json(BATCH_PATH, OrderedDict((
        ("schema", "ptf-louisville-pass2-capture-batch-prepared/1.0"),
        ("work_order", WORK),
        ("market_id", "louisville-ky"),
        ("as_of", AS_OF),
        ("executed", False),
        ("note",
         "Next five-property Louisville capture batch prepared only. "
         "Not executed. Hilton, Hyatt, and Marriott excluded."),
        ("excluded_brands", ["hilton", "hyatt", "marriott"]),
        ("items", NEXT_BATCH),
    )))
    print("recorded", 6)
    print("approvals", 2, "no_pets", 3, "holds", 1, "no_decision", 1)
    print("authority_applied", ["D001", "D002", "D003"])
    print("next_batch_executed", False)


if __name__ == "__main__":
    main()
