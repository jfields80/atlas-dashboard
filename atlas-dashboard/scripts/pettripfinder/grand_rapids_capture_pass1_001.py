"""Durable, capture-only recorder for Grand Rapids–Holland Pass 1.

This writer deliberately does not touch policy authority.  It records only
attended first-party observations, their hash-bound local artifacts, and the
founder-review proposal material required for later adjudication.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.pettripfinder.contracts.policy_schema import validate_facts

ROOT = Path(__file__).resolve().parents[2]
LP = ROOT / "launch_packages" / "pettripfinder"
QUEUE = LP / "grand_rapids_holland_claude_capture_batch_001.json"
EVIDENCE = ROOT / "data" / "operator_evidence" / "grand-rapids-holland-claude-capture-pass1-001" / "incoming"
PROGRESS = LP / "grand_rapids_holland_capture_pass1_001_progress.json"
OUTPUT = LP / "grand_rapids_holland_capture_pass1_001.json"
PACKET = LP / "grand_rapids_holland_capture_pass1_founder_review_packet.json"
INDEX = LP / "grand_rapids_holland_capture_pass1_artifact_index.json"

# This is populated only from the attended official property pages, in queue
# order.  ``raw`` is the identity/policy excerpt stored in the gitignored
# operator-evidence artifact; every proposed fact is intentionally conservative.
CAPTURES = {
    "ac hotel grand rapids downtown": {
        "captured_at": "2026-08-17T00:00:00Z", "final_url": "https://www.marriott.com/en-us/hotels/grrar-ac-hotel-grand-rapids-downtown/overview/",
        "identity": "AC Hotel Grand Rapids Downtown | 50 Monroe Avenue NW, Grand Rapids, Michigan, USA, 49503 | +1 616-776-3200",
        "quote": "Pets Welcome\n\nDog Friendly, 1-6 nights $75 cleaning fee, call hotel for 7+ and weight limits\n\nMaximum Pet Weight: 75.0lbs\n\nMaximum Number of Pets in Room: 2",
        "facts": {"pets_allowed": True, "maximum_pet_weight_lbs": 75.0, "maximum_pets_per_room": 2},
        "withheld": ["species", "fee_basis", "fee_scope", "weight_scope", "reservation_requirement"],
    },
    "avid hotel zeeland": {
        "captured_at": "2026-08-17T00:00:00Z", "final_url": "https://www.ihg.com/avidhotels/hotels/us/en/zeeland/grrav/hoteldetail",
        "identity": "avid hotel Zeeland - Holland | 8225 Westpark Way, Zeeland, MI, 49464 | 1-616-9533900 | IHG grrav",
        "quote": "Pets allowed\nService animals allowed\nPet walking area onsite",
        "facts": {"pets_allowed": True}, "withheld": ["species", "pet_count", "fee_amount", "fee_basis", "weight_limit", "reservation_requirement"],
    },
    "candlewood suites grand rapids airport": {
        "captured_at": "2026-08-17T00:00:00Z", "final_url": "https://www.ihg.com/candlewood/hotels/us/en/grand-rapids/grres/hoteldetail",
        "identity": "Candlewood Suites Grand Rapids Airport | 5401 28th Street Court Southeast, Grand Rapids, MI 49546 | 1-616-9408100 | IHG grres",
        "quote": "Pets are allowed for a fee of 12.50 USD per night, a maximum of 150.00 USD. A signed pet policy must be on file. Weight limit 40lbs per pet.",
        "facts": {"pets_allowed": True, "pet_fee_usd": 12.50, "fee_basis": "per_night", "maximum_fee_usd": 150.00, "maximum_pet_weight_lbs": 40.0, "weight_limit_scope": "per_pet"},
        "withheld": ["species", "pet_count", "fee_scope", "weight_scope", "reservation_requirement"],
    },
    "clarion inn and suites airport": {
        "captured_at": "2026-08-17T00:00:00Z", "final_url": "https://www.choicehotels.com/en-ca/michigan/grand-rapids/clarion-hotels/mi355",
        "identity": "Clarion Inn & Suites Grand Rapids Airport | 4981 28th Street SE, Grand Rapids, MI, 49512, US | (616) 258-6706 | Choice mi355",
        "quote": "Pets Allowed: Yes\nGeneral: Pet accommodation: 30.00 USD per night per pet. Maximum of 2 pets per room.. Service animals are permitted, without charge.",
        "facts": {"pets_allowed": True, "pet_fee_usd": 30.00, "fee_basis": "per_night", "fee_scope": "per_pet", "maximum_pets_per_room": 2},
        "withheld": ["species", "weight_limit", "reservation_requirement"],
    },
    "comfort inn grand rapids airport": {
        "captured_at": "2026-08-17T00:00:00Z", "final_url": "https://www.choicehotels.com/en-ca/michigan/grand-rapids/comfort-inn-hotels/mi121",
        "identity": "Comfort Inn Grand Rapids Airport | 4155 28th St., S.E., Grand Rapids, MI, 49512, US | (616) 219-0991 | Choice mi121",
        "quote": "Pets Allowed: Yes\nGeneral: Pets are allowed. Dogs Only. 25.00 USD Per Night Per Pet. Refundable Deposit of 100.00 USD. Limit size of the pet is 30 pounds.. Service animals are permitted, without charge.",
        "facts": {"pets_allowed": True, "species_allowed": ["dogs"], "pet_fee_usd": 25.00, "fee_basis": "per_night", "fee_scope": "per_pet", "refundable_pet_deposit_usd": 100.00, "maximum_pet_weight_lbs": 30.0},
        "withheld": ["pet_count", "weight_scope", "reservation_requirement"],
    },
    "comfort suites grand rapids north": {
        "captured_at": "2026-08-17T00:00:00Z", "final_url": "https://www.choicehotels.com/en-ca/michigan/comstock-park/comfort-suites-hotels/mi235",
        "identity": "Comfort Suites Grand Rapids North | 350 Dodge Street, Comstock Park, MI, 49321, US | (616) 330-6062 | Choice mi235",
        "quote": "Pets Allowed: No\nGeneral: Only service animals are permitted, free of charge.",
        "facts": {"pets_allowed": False}, "withheld": ["species", "fee_amount", "fee_basis", "weight_limit"], "outcome": "VERIFIED_NO_PETS_CANDIDATE",
    },
    "comfort suites grand rapids south": {
        "captured_at": "2026-08-17T00:00:00Z", "final_url": "https://www.choicehotels.com/en-ca/michigan/grand-rapids/comfort-suites-hotels/mi231",
        "identity": "Comfort Suites Grand Rapids South | 7644 Caterpillar Court, Grand Rapids, MI, 49548, US | (616) 301-2255 | Choice mi231",
        "quote": "The Hotel has a limited number of Dog Friendly Rooms. Please refer to the guest room description when booking, you will note Pet Friendly in the description. Limit one pet per room, 40 lbs. maximum.. Service animals are permitted, without charge.",
        "facts": {"pets_allowed": True, "species_allowed": ["dogs"], "maximum_pets_per_room": 1, "maximum_pet_weight_lbs": 40.0}, "withheld": ["fee_amount", "fee_basis", "fee_scope", "reservation_requirement"],
    },
    "comfort suites grandville grand rapids sw": {
        "captured_at": "2026-08-17T00:00:00Z", "final_url": "https://www.choicehotels.com/en-ca/michigan/grandville/comfort-suites-hotels/mi169",
        "identity": "Comfort Suites Grandville - Grand Rapids SW | 4520 Kenowa Ave SW, Grandville, MI, 49418, US | (616) 667-0733 | Choice mi169",
        "quote": "Pets Allowed: No\nGeneral: Only service animals are permitted, free of charge.",
        "facts": {"pets_allowed": False}, "withheld": ["species", "fee_amount", "fee_basis", "weight_limit"], "outcome": "VERIFIED_NO_PETS_CANDIDATE",
    },
    "country inn and suites by radisson grandville grand rapids west": {
        "captured_at": "2026-08-17T00:00:00Z", "final_url": "https://www.choicehotels.com/en-ca/michigan/grandville/country-inn-suites-hotels/mi612",
        "identity": "Country Inn & Suites by Radisson, Grandville-Grand Rapids West, MI | 3825 28th Street SW, Grandville, MI, 49418, US | (616) 500-0881 | Choice mi612",
        "quote": "Pets Allowed: No\nGeneral: Only service animals are permitted, free of charge.",
        "facts": {"pets_allowed": False}, "withheld": ["species", "fee_amount", "fee_basis", "weight_limit"], "outcome": "VERIFIED_NO_PETS_CANDIDATE",
    },
    "country inn and suites by radisson holland": {
        "captured_at": "2026-08-17T00:00:00Z", "final_url": "https://www.choicehotels.com/en-ca/michigan/holland/country-inn-suites-hotels/mi444",
        "identity": "Country Inn & Suites by Radisson, Holland, MI | 12260 James Street, Holland, MI, 49424, US | (616) 215-0980 | Choice mi444",
        "quote": "Pets Allowed: Yes\nGeneral: Pets Allowed. Pet Charge 25.00 USD Per Pet, Per Night.. Service animals are permitted, without charge.",
        "facts": {"pets_allowed": True, "pet_fee_usd": 25.0, "fee_basis": "per_night", "fee_scope": "per_pet"}, "withheld": ["species", "pet_count", "weight_limit", "reservation_requirement"],
    },
    "country inn and suites grand rapids airport": {
        "captured_at": "2026-08-17T00:00:00Z", "final_url": "https://www.choicehotels.com/en-ca/michigan/grand-rapids/country-inn-suites-hotels/mi611",
        "identity": "Country Inn & Suites by Radisson, Grand Rapids Airport, MI | 5399 28th Street Court SE, Grand Rapids, MI, 49546, US | (616) 500-0222 | Choice mi611",
        "quote": "Pets Allowed: Yes\nGeneral: Pets Allowed. Pet Charge 25 USD Per Pet, Per Night. Pet limit 2 Pet Per Room.. Service animals are permitted, without charge.",
        "facts": {"pets_allowed": True, "pet_fee_usd": 25.0, "fee_basis": "per_night", "fee_scope": "per_pet", "maximum_pets_per_room": 2}, "withheld": ["species", "weight_limit", "reservation_requirement"],
    },
    "country inn and suites grand rapids east": {
        "captured_at": "2026-08-17T00:00:00Z", "final_url": "https://www.choicehotels.com/en-ca/michigan/grand-rapids/country-inn-suites-hotels/mi607",
        "identity": "Country Inn & Suites by Radisson, Grand Rapids East, MI | 3251 Deposit Drive NE, Grand Rapids, MI, 49546, US | (616) 320-5946 | Choice mi607",
        "quote": "Pets Allowed: No\nGeneral: Only service animals are permitted, free of charge.",
        "facts": {"pets_allowed": False}, "withheld": ["species", "fee_amount", "fee_basis", "weight_limit"], "outcome": "VERIFIED_NO_PETS_CANDIDATE",
    },
    "courtyard by marriott grand rapids airport": {
        "captured_at": "2026-08-17T00:00:00Z", "final_url": "https://www.marriott.com/en-us/hotels/grrcy-courtyard-grand-rapids-airport/overview/",
        "identity": "Courtyard by Marriott Grand Rapids Airport | 4741 28th Street SE, Grand Rapids, Michigan, USA, 49512 | +1 616-954-0500 | Marriott grrcy",
        "quote": "Pet Policy\nPets Not Allowed", "facts": {"pets_allowed": False}, "withheld": ["species", "fee_amount", "fee_basis", "weight_limit"], "outcome": "VERIFIED_NO_PETS_CANDIDATE",
    },
    "courtyard by marriott grand rapids downtown": {
        "captured_at": "2026-08-17T00:00:00Z", "final_url": "https://www.marriott.com/en-us/hotels/grrdt-courtyard-grand-rapids-downtown/overview/",
        "identity": "Courtyard by Marriott Grand Rapids Downtown | 11 Monroe Avenue NW, Grand Rapids, Michigan, USA, 49503 | +1 616-242-6000 | Marriott grrdt",
        "quote": "Pet Policy\nPets Not Allowed\nNo pets", "facts": {"pets_allowed": False}, "withheld": ["species", "fee_amount", "fee_basis", "weight_limit"], "outcome": "VERIFIED_NO_PETS_CANDIDATE",
    },
    "courtyard by marriott holland downtown": {
        "captured_at": "2026-08-17T00:00:00Z", "final_url": "https://www.marriott.com/en-us/hotels/grrch-courtyard-holland-downtown/overview/",
        "identity": "Courtyard by Marriott Holland Downtown | 121 East 8th Street, Holland, Michigan, USA, 49423 | +1 616-582-8500 | Marriott grrch",
        "quote": "Pet Policy\nPets Not Allowed", "facts": {"pets_allowed": False}, "withheld": ["species", "fee_amount", "fee_basis", "weight_limit"], "outcome": "VERIFIED_NO_PETS_CANDIDATE",
    },
    "econo lodge grand rapids airport": {
        "captured_at": "2026-08-17T00:00:00Z", "final_url": "https://www.choicehotels.com/en-ca/michigan/grand-rapids/econo-lodge-hotels/mi294",
        "identity": "Econo Lodge & Suites Grand Rapids Airport | 2985 Kraft Avenue Southeast, Grand Rapids, MI, 49512, US | (616) 940-1777 | Choice mi294",
        "quote": "Pets Allowed: No\nGeneral: Only service animals are permitted, free of charge.", "facts": {"pets_allowed": False}, "withheld": ["species", "fee_amount", "fee_basis", "weight_limit"], "outcome": "VERIFIED_NO_PETS_CANDIDATE",
    },
    "fairfield inn and suites grand rapids": {
        "captured_at": "2026-08-17T00:00:00Z", "final_url": "https://www.marriott.com/en-us/hotels/grrpa-fairfield-inn-and-suites-grand-rapids-airport/overview/",
        "identity": "Fairfield by Marriott Inn & Suites Grand Rapids Airport | 3930 Stahl Drive SE, Grand Rapids, Michigan, USA, 49546 | +1 616-940-2700 | Marriott grrpa",
        "quote": "Pet Policy\nPets Not Allowed", "facts": {"pets_allowed": False}, "withheld": ["species", "fee_amount", "fee_basis", "weight_limit"], "outcome": "VERIFIED_NO_PETS_CANDIDATE",
    },
    "fairfield inn and suites grand rapids north": {
        "captured_at": "2026-08-17T00:00:00Z", "final_url": "https://www.marriott.com/en-us/hotels/grrfn-fairfield-inn-and-suites-grand-rapids-north/overview/",
        "identity": "Fairfield by Marriott Inn & Suites Grand Rapids North | 620 Center Drive NW, Walker, Michigan, USA, 49544 | +1 616-647-0600 | Marriott grrfn",
        "quote": "Pet Policy\nPets Not Allowed\nNo pets allowed - Service animals only", "facts": {"pets_allowed": False}, "withheld": ["species", "fee_amount", "fee_basis", "weight_limit"], "outcome": "VERIFIED_NO_PETS_CANDIDATE",
    },
    "fairfield inn and suites grand rapids wyoming": {
        "captured_at": "2026-08-17T00:00:00Z", "final_url": "https://www.marriott.com/en-us/hotels/grrfw-fairfield-inn-and-suites-grand-rapids-wyoming/overview/",
        "identity": "Fairfield by Marriott Inn & Suites Grand Rapids Wyoming | 5970 Metro Way S.W., Wyoming, Michigan, USA, 49519 | +1 616-249-3000 | Marriott grrfw",
        "quote": "Pet Policy\nPets Not Allowed", "facts": {"pets_allowed": False}, "withheld": ["species", "fee_amount", "fee_basis", "weight_limit"], "outcome": "VERIFIED_NO_PETS_CANDIDATE",
    },
    "holiday inn express and suites grand rapids airport north": {
        "captured_at": "2026-08-17T00:00:00Z", "final_url": "https://www.ihg.com/holidayinnexpress/hotels/us/en/grand-rapids/grret/hoteldetail",
        "identity": "Holiday Inn Express & Suites Grand Rapids - Airport North | 5405 28th St Court SE, Grand Rapids, MI 49546 | 1-616-2653333 | IHG grret",
        "quote": "Pet-friendly", "facts": {}, "withheld": ["pets_allowed", "species", "pet_count", "fee_amount", "fee_basis", "fee_scope", "weight_limit", "reservation_requirement"], "outcome": "POLICY_NOT_FOUND",
    },
    "holiday inn express and suites grand rapids airport south": {
        "captured_at": "2026-08-17T00:00:00Z", "final_url": "https://www.ihg.com/holidayinnexpress/hotels/us/en/grand-rapids/grrse/hoteldetail",
        "identity": "Holiday Inn Express & Suites Grand Rapids Airport - South | 4888 Town Center Drive SE, Grand Rapids, MI 49512 | IHG grrse",
        "quote": "No, pets are not allowed at Holiday Inn Express & Suites Grand Rapids Airport - South.", "facts": {"pets_allowed": False}, "withheld": ["species", "fee_amount", "fee_basis", "weight_limit"], "outcome": "VERIFIED_NO_PETS_CANDIDATE",
    },
    "holiday inn express and suites grand rapids north": {
        "captured_at": "2026-08-17T00:00:00Z", "final_url": "https://www.ihg.com/holidayinnexpress/hotels/us/en/walker/grrds/hoteldetail",
        "identity": "Holiday Inn Express & Suites Grand Rapids-North | 358 River Ridge Dr. NW, Walker, MI 49544 | IHG grrds",
        "quote": "No, pets are not allowed at Holiday Inn Express & Suites Grand Rapids-North.", "facts": {"pets_allowed": False}, "withheld": ["species", "fee_amount", "fee_basis", "weight_limit"], "outcome": "VERIFIED_NO_PETS_CANDIDATE",
    },
    "holiday inn express and suites grand rapids south wyoming": {
        "captured_at": "2026-08-17T00:00:00Z", "final_url": "https://www.ihg.com/holidayinnexpress/hotels/us/en/wyoming-mi/grrym/hoteldetail",
        "identity": "Holiday Inn Express & Suites Grand Rapids South - Wyoming | 5870 Clyde Park Ave SW, Wyoming, MI 49509 | IHG grrym",
        "quote": "No, pets are not allowed at Holiday Inn Express & Suites Grand Rapids South - Wyoming.", "facts": {"pets_allowed": False}, "withheld": ["species", "fee_amount", "fee_basis", "weight_limit"], "outcome": "VERIFIED_NO_PETS_CANDIDATE",
    },
    "holiday inn express grand rapids sw": {
        "captured_at": "2026-08-17T00:00:00Z", "final_url": "https://www.ihg.com/holidayinnexpress/hotels/us/en/grandville/gdvmi/hoteldetail",
        "identity": "Holiday Inn Express Grand Rapids SW | 4651 36th Street, Grandville, MI 49418 | IHG gdvmi",
        "quote": "Pets are welcome at Holiday Inn Express Grand Rapids SW. Pet policy description. Pet owner assumes all responsibility and liability for the pet. Pet must be on leash or in carrier when in public area. Pet not allowed in breakfast, pool or fitness area. Additional cleaning and damage fees may apply. Pet fee per night: 75 USD Pet weight limit: 75 2 pets allowed Pets allowed: Only dogs and cats allowed",
        "facts": {"pets_allowed": True, "species_allowed": ["dogs", "cats"], "pet_fee_usd": 75.0, "fee_basis": "per_night", "maximum_pets_per_room": 2}, "withheld": ["fee_scope", "weight_limit", "weight_unit", "weight_scope", "reservation_requirement"],
    },
    "holiday inn express holland": {
        "captured_at": "2026-08-17T00:00:00Z", "final_url": "https://www.ihg.com/holidayinnexpress/hotels/us/en/holland/hldfe/hoteldetail",
        "identity": "Holiday Inn Express Holland | 12381 Felch Street, Holland, MI 49424 | IHG hldfe",
        "quote": "No, pets are not allowed at Holiday Inn Express Holland.", "facts": {"pets_allowed": False}, "withheld": ["species", "fee_amount", "fee_basis", "weight_limit"], "outcome": "VERIFIED_NO_PETS_CANDIDATE",
    },
}

def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def schema_proposal(raw: dict, quote: str) -> list[dict]:
    """Translate capture shorthand to Schema 1.2 fields before serialization."""
    facts = {}
    if "pets_allowed" in raw:
        facts["pets_allowed"] = raw["pets_allowed"]
    if raw.get("species_allowed"):
        facts["species"] = {name: "accepted" for name in raw["species_allowed"]}
    if "pet_fee_usd" in raw:
        fee = {"amount_cents": int(round(raw["pet_fee_usd"] * 100)), "currency": "USD"}
        for key, source_key in (("basis", "fee_basis"), ("scope", "fee_scope")):
            if raw.get(source_key):
                fee[key] = raw[source_key]
        facts["pet_fee"] = fee
    if "maximum_pets_per_room" in raw:
        facts["pet_count_limit"] = raw["maximum_pets_per_room"]
        facts["pet_count_scope"] = "per_room"
    if raw.get("weight_limit_scope"):
        facts["weight_limit"] = {
            "value": raw["maximum_pet_weight_lbs"], "unit": "lb",
            "operator": "lte", "scope": raw["weight_limit_scope"],
        }
    issues = validate_facts(facts)
    if issues:
        raise ValueError("invalid capture proposal: %s" % "; ".join(map(str, issues)))
    return [{"field": field, "value": value, "quote": quote,
             "quote_contiguous_in_artifact": True}
            for field, value in facts.items()]

def main() -> None:
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))["items"]
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    rows, artifacts = [], []
    for number, item in enumerate(queue, 1):
        result = CAPTURES.get(item["identity_key"])
        if not result:
            continue
        raw = "IDENTITY\n%s\n\nPOLICY\n%s\n" % (result["identity"], result["quote"])
        rel = Path("data/operator_evidence/grand-rapids-holland-claude-capture-pass1-001/incoming/%02d-%s.txt" % (number, item["identity_key"].replace(" ", "-")))
        path = ROOT / rel
        path.write_text(raw, encoding="utf-8")
        sha = "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()
        row = {"queue_position": number, **item, "terminal_outcome": result.get("outcome", "PUBLICATION_CANDIDATE"), "source_grade": "FIRST_PARTY_PROPERTY_PAGE", "artifact_kind": "RENDERED_PAGE", "artifact_class": "TRANSCRIPTION_ONLY", "capture_method": "ATTENDED_CLAUDE_BROWSER", "captured_at": result["captured_at"], "source_url": item["official_url"], "final_url": result["final_url"], "artifact_path": str(rel).replace("\\", "/"), "artifact_sha256": sha, "identity_binding": result["identity"], "exact_contiguous_quote": result["quote"], "proposed_schema_1_2_facts": schema_proposal(result["facts"], result["quote"]), "withheld_fields": result["withheld"], "ambiguity_notes": "Capture-only proposal; no founder approval or policy authority application."}
        rows.append(row)
        artifacts.append({"queue_position": number, "identity_key": item["identity_key"], "path": row["artifact_path"], "sha256": sha, "quote_contiguous": " ".join(result["quote"].split()) in " ".join(raw.split())})
    progress = {"schema": "ptf-market-capture-progress/1.0", "market_id": "grand-rapids-holland-mi", "work_order": "PTF-GRAND-RAPIDS-HOLLAND-CLAUDE-CAPTURE-PASS1-001", "queue_total": len(queue), "processed": len(rows), "remaining": len(queue)-len(rows), "terminal_rows": rows}
    write_json(PROGRESS, progress)
    # Main outputs are intentionally emitted only when all fixed queue rows are terminal.
    if len(rows) == len(queue):
        write_json(OUTPUT, {**progress, "schema": "ptf-market-capture-pass/1.0"})
        write_json(INDEX, {"schema": "ptf-artifact-index/1.0", "market_id": "grand-rapids-holland-mi", "artifacts": artifacts})
        candidate_rows = [r for r in rows if r["terminal_outcome"] in ("PUBLICATION_CANDIDATE", "VERIFIED_NO_PETS_CANDIDATE")]
        write_json(PACKET, {"schema": "ptf-founder-review-packet/1.0", "market_id": "grand-rapids-holland-mi", "approval_status": "NOT_REQUESTED", "decisions": [{"decision_id": "GRH-P1-%03d" % r["queue_position"], "identity_key": r["identity_key"], "hotel": r["canonical_name"], "exact_route": r["final_url"], "identity_signals": r["identity_binding"], "artifact_sha256": r["artifact_sha256"], "exact_quotes": [r["exact_contiguous_quote"]], "proposed_schema_1_2_facts": r["proposed_schema_1_2_facts"], "withheld_fields": r["withheld_fields"], "ambiguity_notes": r["ambiguity_notes"], "recommended_founder_decision": "REVIEW_CAPTURE_ONLY"} for r in candidate_rows]})

if __name__ == "__main__":
    main()
