"""PTF-PITTSBURGH-PASS4-CLAUDE-CAPTURE-001 capture-only report writer.

It records the twelve committed queue observations.  It deliberately never
writes policy authority, seeds, exclusions, or founder approvals.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LP = ROOT / "launch_packages" / "pettripfinder"
REPORTS = LP / "markets" / "reports"
EVIDENCE = ROOT / "data" / "operator_evidence" / "pittsburgh-pass4-claude-capture-001"
MARKET = "pittsburgh-pa"
WORK_ORDER = "PTF-PITTSBURGH-PASS4-CLAUDE-CAPTURE-001"
AS_OF = "2026-08-17"
QUEUE_PATH = REPORTS / "pittsburgh_pass4_claude_capture_queue.json"
RESULTS_PATH = REPORTS / "pittsburgh_pass4_claude_capture_results.json"
PACKET_PATH = REPORTS / "pittsburgh_pass4_claude_founder_review_packet.json"
MANIFEST_PATH = REPORTS / "pittsburgh_pass4_claude_capture_manifest.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=OrderedDict)


def dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def artifact(identity_key: str) -> dict:
    slug = identity_key.replace(" ", "-")
    path = EVIDENCE / (slug + ".txt")
    assert path.is_file(), "durable capture artifact missing: %s" % path
    return OrderedDict([
        ("artifact_file", "data/operator_evidence/pittsburgh-pass4-claude-capture-001/" + path.name),
        ("artifact_kind", "official_page_rendered_text"),
        ("artifact_sha256", digest(path)),
        ("captured_at", AS_OF),
        ("capture_method", "attended_claude_browser"),
        ("source_grade", "OFFICIAL_PROPERTY"),
    ])


def quote(text: str) -> dict:
    return OrderedDict([("quote", text), ("verification", "CONTIGUOUS_IN_DURABLE_ARTIFACT")])


def item(row: dict, outcome: str, *, binding: str, quotes: list[str],
         facts: dict | None = None, withheld: list[dict] | None = None,
         notes: list[str] | None = None, publication_grade: bool = False,
         review_required: bool = False) -> dict:
    record = OrderedDict([
        ("capture_id", "PGH-P4-C%03d" % row["row_number"]),
        ("row_number", row["row_number"]),
        ("hotel", row["canonical_name"]),
        ("identity_key", row["identity_key"]),
        ("official_candidate_url", row["official_property_url"]),
        ("final_url", row["final_url"]),
        ("identity_binding", binding),
        ("outcome", outcome),
        ("publication_grade", publication_grade),
        ("artifacts", [artifact(row["identity_key"])]),
        ("quotes", [quote(value) for value in quotes]),
        ("proposed_schema_1_2_facts", facts or OrderedDict()),
        ("withheld_fields", withheld or []),
        ("contradiction_or_ambiguity_notes", notes or []),
        ("founder_review_required", review_required),
    ])
    return record


def queue_rows() -> list[dict]:
    queue = load(QUEUE_PATH)
    assert queue["market_id"] == MARKET and queue["count"] == 12
    assert [row["row_number"] for row in queue["items"]] == list(range(1, 13))
    return queue["items"]


def authority_snapshot() -> dict:
    facts = load(LP / "hotel_policy_facts_pittsburgh-pa.json")
    exclusions = load(LP / "markets" / "authority" / MARKET / "hotel_exclusions.json")
    seeds = (LP / "markets" / "authority" / MARKET / "seed_businesses.csv").read_bytes()
    partition = load(LP / "pittsburgh_final_partition_001.json")
    states = Counter(row["final_state"] for row in partition["items"])
    snapshot = OrderedDict([
        ("published", len(facts["hotels"])),
        ("verified_no_pets", sum(1 for row in exclusions["exclusions"]
                                  if row["exclusion_state"] == "VERIFIED_NO_PETS")),
        ("out_of_category", sum(1 for row in exclusions["exclusions"]
                                 if row["exclusion_state"] == "OUT_OF_CURRENT_CATEGORY")),
        ("unresolved", sum(count for state, count in states.items() if state.startswith("AWAITING_"))),
        ("policy_facts_sha256", digest(LP / "hotel_policy_facts_pittsburgh-pa.json")),
        ("exclusions_sha256", digest(LP / "markets" / "authority" / MARKET / "hotel_exclusions.json")),
        ("seed_sha256", "sha256:" + hashlib.sha256(seeds).hexdigest()),
    ])
    assert {key: snapshot[key] for key in ("published", "verified_no_pets", "out_of_category", "unresolved")} == {
        "published": 29, "verified_no_pets": 6, "out_of_category": 3, "unresolved": 58}
    return snapshot


def build() -> tuple[dict, dict, dict]:
    rows = queue_rows()
    final_urls = {
        "hyatt house pittsburgh bloomfield shadyside": "https://www.hyatt.com/hyatt-house/en-US/pitxp-hyatt-house-pittsburgh-bloomfield-shadyside",
        "hyatt place pittsburgh airport": "https://www.hyatt.com/hyatt-place/en-US/pitza-hyatt-place-pittsburgh-airport-robinson-mall",
        "hyatt place pittsburgh north shore": "https://www.hyatt.com/hyatt-place/en-US/pitzn-hyatt-place-pittsburgh-north-shore",
        "hyatt regency pittsburgh international airport": "https://www.hyatt.com/hyatt-regency/en-US/pitap-hyatt-regency-pittsburgh-international-airport",
        "joinery hotel pittsburgh": "https://www.joineryhotel.com/faqs",
        "mansions on fifth": "https://mansionsonfifth.com/amenities-services.php",
    }
    by_key = {row["identity_key"]: dict(row, final_url=final_urls.get(
        row["identity_key"], row["official_property_url"])) for row in rows}
    assert "sunnyledge boutique hotel" not in by_key
    before = authority_snapshot()
    candidates = [
        item(by_key["courtyard by marriott pittsburgh airport"], "VERIFIED_NO_PETS_CANDIDATE",
             binding="Courtyard by Marriott Pittsburgh Airport | 450 Cherrington Parkway, Coraopolis, PA 15108 | +1 412-264-5000 | Marriott property code PITCA",
             quotes=["Pet Policy", "Pets Not Allowed"], publication_grade=True, review_required=True),
        item(by_key["courtyard by marriott pittsburgh airport settlers ridge"], "VERIFIED_NO_PETS_CANDIDATE",
             binding="Courtyard by Marriott Pittsburgh Airport Settlers Ridge | 5100 Campbells Run Road, Pittsburgh, PA 15205 | +1 412-788-4404 | Marriott property code PITSR",
             quotes=["Pet Policy", "Pets Not Allowed"], publication_grade=True, review_required=True),
        item(by_key["motel 6 pittsburgh"], "PUBLICATION_CANDIDATE",
             binding="Motel 6 Pittsburgh, PA - Crafton | 211 Beecham Drive, Pittsburgh, PA 15205 | 4129229400",
             quotes=["This pet-friendly motel welcomes your four-legged companions, so you can travel with peace of mind knowing your pets are part of the journey.", "Pets Allowed"],
             facts={"pets_allowed": True}, publication_grade=True, review_required=True),
        item(by_key["sonesta simply suites pittsburgh airport"], "PUBLICATION_CANDIDATE",
             binding="Sonesta Simply Suites Pittsburgh Airport | 100 Chauvet Drive, Pittsburgh, PA 15275 | +1 412-787-7770",
             quotes=["Sonesta Simply Suites Pittsburg Airport is pet-friendly and welcomes well-mannered pets, with no breed or weight restrictions. Up to two pets are permitted per suite.", "$75 fee applies for stays up to 7 nights; $150 for all longer stays."],
             facts={"pets_allowed": True, "pet_count_limit": 2,
                    "fee_tiers": [{"amount_cents": 7500, "currency": "USD", "stay_nights": {"min": 1, "max": 7}},
                                  {"amount_cents": 15000, "currency": "USD", "stay_nights": {"min": 8, "max": None}}]},
             withheld=[{"field": "fee_basis", "reason_code": "SOURCE_AMBIGUOUS"},
                        {"field": "pet_count_scope", "reason_code": "SCHEMA_CANNOT_REPRESENT"}],
             notes=["The source says ‘per suite’; no room scope was inferred. The duration tiers do not state a fee basis."], publication_grade=True, review_required=True),
        item(by_key["springhill suites pittsburgh airport"], "PUBLICATION_CANDIDATE",
             binding="SpringHill Suites Pittsburgh Airport | 2500 Market Place Boulevard, Coraopolis, PA 15108 | Marriott property code PITHA",
             quotes=["Pets Welcome", "Non-Refundable Pet Fee Per Stay: $150.00"],
             facts={"pets_allowed": True, "pet_fee": {"amount_cents": 15000, "currency": "USD", "basis": "per_stay", "refundable": False}},
             publication_grade=True, review_required=True),
        item(by_key["towneplace suites pittsburgh airport robinson township"], "PUBLICATION_CANDIDATE",
             binding="TownePlace Suites Pittsburgh Airport/Robinson Township | 1006 Sutherland Drive, Robinson Township, PA 15205 | +1 412-494-4000 | Marriott property code PITTW",
             quotes=["Pets Welcome", "2 pets 75 pounds or less with USD 75 non-refundable fee per pet per stay", "Non-Refundable Pet Fee Per Stay: $75.00", "Maximum Pet Weight: 75.0lbs", "Maximum Number of Pets in Room: 2"],
             facts={"pets_allowed": True, "pet_fee": {"amount_cents": 7500, "currency": "USD", "basis": "per_stay", "scope": "per_pet", "refundable": False},
                    "weight_limit": {"value": 75, "unit": "lb", "operator": "lte", "scope": "per_pet"}, "pet_count_limit": 2, "pet_count_scope": "room"},
             publication_grade=True, review_required=True),
        item(by_key["hyatt house pittsburgh bloomfield shadyside"], "PUBLICATION_CANDIDATE",
             binding="Hyatt House Pittsburgh/Bloomfield/Shadyside | 5335 Baum Boulevard, Pittsburgh, PA 15224 | +1 412 621 9900 | Hyatt property code PITXP",
             quotes=["Our hotel is designed to bring home comfort to every guest—even the ones with four legs. Relax with up to two of your furry friends in a spacious, suite-inspired room.", "1-6 nights:", "$75", "7-30 nights (includes cleaning fee):", "$275", "Individual pet weight limit: 25 Pounds", "Combined pets weight limit: 50 Pounds", "Maximum number of pets is 2."],
             facts={"pets_allowed": True, "pet_count_limit": 2,
                    "weight_limits": [{"value": 25, "unit": "lb", "operator": "lte", "scope": "per_pet"}, {"value": 50, "unit": "lb", "operator": "lte", "scope": "combined"}],
                    "fee_tiers": [{"amount_cents": 7500, "currency": "USD", "basis": "per_stay", "stay_nights": {"min": 1, "max": 6}}, {"amount_cents": 27500, "currency": "USD", "basis": "per_stay", "stay_nights": {"min": 7, "max": 30}}]},
             notes=["The $275 tier says it includes a cleaning fee; no separate cleaning-fee amount was invented."], publication_grade=True, review_required=True),
        item(by_key["hyatt place pittsburgh airport"], "PUBLICATION_CANDIDATE",
             binding="Hyatt Place Pittsburgh Airport / Robinson Mall | 6011 Campbells Run Road, Pittsburgh, PA 15205 | +1 412 494 0202 | Hyatt property code PITZA",
             quotes=["Our hotel is pet friendly for up to two housebroken dogs. Please call ahead at +1 412 494 0202 to let us know you'll be bringing canine company.", "1–6 nights:", "$100", "7–30 nights + additional cleaning fee:", "$200", "Individual pet weight limit: 50 Pounds", "Combined pets weight limit: 75 Pounds", "Maximum number of pets is 2."],
             facts={"pets_allowed": True, "species": {"dogs": "accepted"}, "pet_count_limit": 2,
                    "weight_limits": [{"value": 50, "unit": "lb", "operator": "lte", "scope": "per_pet"}, {"value": 75, "unit": "lb", "operator": "lte", "scope": "combined"}], "reservation_notice": "Please call ahead at +1 412 494 0202 to let us know you'll be bringing canine company."},
             withheld=[{"field": "pet_fee", "reason_code": "SOURCE_AMBIGUOUS"}],
             notes=["The seven-to-thirty-night line combines a $200 stay charge with an unspecified ‘additional cleaning fee’; no monetary schedule was synthesized."], publication_grade=True, review_required=True),
        item(by_key["hyatt place pittsburgh north shore"], "PUBLICATION_CANDIDATE",
             binding="Hyatt Place Pittsburgh-North Shore | 260 North Shore Drive, Pittsburgh, PA 15212 | +1 412 321 3000 | Hyatt property code PITZN",
             quotes=["We welcome a maximum of two canine companions. Please call us at +1 412 321 3000 prior to your arrival to let us know you’ll be bringing your dog(s), which must be housebroken.", "1 - 6 nights:", "$75", "7 - 30 nights :", "+ $100", "Cleaning fee", "Individual pet weight limit: 50 Pounds", "Combined pets weight limit: 75 Pounds", "Maximum number of pets is 2."],
             facts={"pets_allowed": True, "species": {"dogs": "accepted"}, "pet_fee": {"amount_cents": 7500, "currency": "USD", "basis": "per_stay"}, "other_charges": [{"kind": "cleaning_fee", "amount_cents": 10000, "currency": "USD", "conditional": True, "trigger": "7 - 30 nights"}], "pet_count_limit": 2,
                    "weight_limits": [{"value": 50, "unit": "lb", "operator": "lte", "scope": "per_pet"}, {"value": 75, "unit": "lb", "operator": "lte", "scope": "combined"}], "reservation_notice": "Please call us at +1 412 321 3000 prior to your arrival to let us know you’ll be bringing your dog(s), which must be housebroken."},
             notes=["Refundability is absent for both the pet fee and the cleaning fee."], publication_grade=True, review_required=True),
        item(by_key["hyatt regency pittsburgh international airport"], "IDENTITY_UNCERTAIN",
             binding="Queued identity: Hyatt Regency Pittsburgh International Airport | 1111 Airport Boulevard, Pittsburgh, PA 15231 | 724-899-1234. Current official page instead states Hyatt Regency Pittsburgh International Airport | 710 Aviation Avenue, Pittsburgh, PA 15231 | +1 412 329 7700.",
             quotes=["Hyatt Regency Pittsburgh International Airport 710 Aviation Avenue, Pittsburgh, PA 15231, United States of America", "+1 412 329 7700"],
             notes=["The exact property name and ZIP match, but the current official address and telephone differ materially from the queued census identity. No policy candidate was created."], publication_grade=False),
        item(by_key["joinery hotel pittsburgh"], "PUBLICATION_CANDIDATE",
             binding="Joinery Hotel Pittsburgh | 453 Boulevard of the Allies, Pittsburgh, PA 15219 | 412-339-1870",
             quotes=["Yes. Pet Fee applies $50.", "Yes, $50 Pet Fee per night up to 2 pets.", "No."],
             facts={"pets_allowed": True, "pet_count_limit": 2},
             withheld=[{"field": "pet_fee", "reason_code": "SOURCE_CONTRADICTORY"}],
             notes=["The exact property FAQ simultaneously says a $50 pet fee applies, says it is per night, and answers ‘No’ to whether there are pet fees or weight restrictions. The monetary field is withheld rather than reconciled."], publication_grade=True, review_required=True),
        item(by_key["mansions on fifth"], "POLICY_NOT_FOUND",
             binding="Mansions on Fifth | 5105 Fifth Avenue, Pittsburgh, PA 15232",
             quotes=[], notes=["The first-party home and distinct amenities surfaces were reviewed. Neither exposed pet-policy wording; silence was not treated as a refusal."], publication_grade=False),
    ]
    assert [record["identity_key"] for record in candidates] == [row["identity_key"] for row in rows]
    for record in candidates:
        for cited in record["quotes"]:
            artifact_path = ROOT / record["artifacts"][0]["artifact_file"]
            assert cited["quote"] in artifact_path.read_text(encoding="utf-8"), (record["identity_key"], cited)
    counts = Counter(record["outcome"] for record in candidates)
    assert counts == {"PUBLICATION_CANDIDATE": 8, "VERIFIED_NO_PETS_CANDIDATE": 2,
                      "IDENTITY_UNCERTAIN": 1, "POLICY_NOT_FOUND": 1}
    after = authority_snapshot()
    assert after == before
    results = OrderedDict([
        ("schema", "ptf-pittsburgh-pass4-claude-capture-results/1.0"), ("work_order", WORK_ORDER),
        ("market_id", MARKET), ("as_of", AS_OF), ("queue_count", 12),
        ("no_authority_applied", True), ("authority_before_and_after", before),
        ("counts", OrderedDict((key, counts.get(key, 0)) for key in ("PUBLICATION_CANDIDATE", "VERIFIED_NO_PETS_CANDIDATE", "POLICY_NOT_FOUND", "ACCESS_BLOCKED", "IDENTITY_UNCERTAIN", "CAPTURE_FAILED", "SOURCE_AMBIGUOUS"))),
        ("items", candidates),
    ])
    review = [record for record in candidates if record["founder_review_required"]]
    packet = OrderedDict([
        ("schema", "ptf-pittsburgh-pass4-claude-founder-review-packet/1.0"), ("work_order", WORK_ORDER),
        ("market_id", MARKET), ("as_of", AS_OF), ("count", len(review)),
        ("status", "FOUNDER_REVIEW_REQUIRED"),
        ("note", "Capture-only packet. It records no founder decisions, approvals, publications, exclusions, or authority changes."),
        ("entries", review),
    ])
    manifest = OrderedDict([
        ("schema", "ptf-pittsburgh-pass4-claude-capture-manifest/1.0"), ("work_order", WORK_ORDER),
        ("market_id", MARKET), ("count", 12),
        ("artifacts", [OrderedDict([("capture_id", record["capture_id"]), ("identity_key", record["identity_key"]), ("outcome", record["outcome"]), ("publication_grade", record["publication_grade"]), ("artifact", record["artifacts"][0])]) for record in candidates]),
    ])
    return results, packet, manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    results, packet, manifest = build()
    if args.apply:
        dump(RESULTS_PATH, results)
        dump(PACKET_PATH, packet)
        dump(MANIFEST_PATH, manifest)
        print("Pass 4 capture: 12 processed, 10 publication-grade, authority unchanged")
    else:
        print(json.dumps({"processed": len(results["items"]), "counts": results["counts"], "founder_review_rows": packet["count"]}, indent=1))


if __name__ == "__main__":
    main()
