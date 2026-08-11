"""PTF-CLEVELAND-POLICY-CAPTURE-WORKER-003 -- policy observations from the
deterministic fetch pass (``cleveland_capture_003_fetch.py``).

Every quote below is asserted to be a literal substring of the raw capture
stored under
``data/worker_runs/pettripfinder/cleveland-policy-capture-003/raw/<n>-<slug>.json``
(gitignored) before the observation is allowed into the batch -- the same
discipline PTF-DAYTON-RECOVERY-WORKER-002 applied after the original
Cleveland/Dayton worker integration found stitched, non-literal quotes.

Produces validated ``ptf-policy-observation/1.0`` records and runs them
through ``policy_membrane`` + ``readiness``. Output is PROPOSED authority
only, at
``launch_packages/pettripfinder/identity_census/cleveland-policy-capture-003-proposed-authority.json``
-- this module does not write ``hotel_policy_facts_cleveland-akron-canton-oh.json``,
``seed_businesses.csv``, or ``hotel_exclusions.json``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.policy import policy_membrane as MB   # noqa: E402
from scripts.pettripfinder.policy import policy_observation as PO  # noqa: E402
from scripts.pettripfinder.policy import readiness as RD          # noqa: E402
from scripts.pettripfinder import cleveland_capture_003_closeout as CO  # noqa: E402

MARKET = "cleveland-akron-canton-oh"
RUN_ID = "cleveland-policy-capture-003"
AS_OF = "2026-08-11"
RAW_DIR = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder" / RUN_ID / "raw")
OUT_MANIFEST = (_REPO_ROOT / "launch_packages" / "pettripfinder" / "identity_census"
                / "cleveland-policy-capture-003-proposed-authority.json")
OUT_OBSERVATIONS = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder" / RUN_ID
                     / "observations.json")

CENSUS = {h["slug"]: h for h in json.loads(
    (_REPO_ROOT / "launch_packages" / "pettripfinder" / "identity_census"
     / "cleveland-akron-canton-oh.json").read_text(encoding="utf-8"))["hotels"]}
_BY_NORM = {h["normalized_name"]: h for h in CENSUS.values()}


def _norm(text: str) -> str:
    return " ".join((text or "").split())


def _load_raw(filename: str) -> Dict:
    doc = json.loads((RAW_DIR / filename).read_text(encoding="utf-8"))
    return doc


def _quote_in(raw: Dict, quote: str) -> bool:
    return _norm(quote) in _norm(raw["text"])


def _hotel_ref(census_row: Dict) -> Dict:
    ref = {
        "market_id": MARKET,
        "canonical_name": census_row["canonical_name"],
        "normalized_name": census_row["normalized_name"],
    }
    if census_row.get("street_identity"):
        ref["street_identity"] = census_row["street_identity"]
    return ref


def _obs(*, obs_id: str, census_row: Dict, source_url: str, source_type: str,
         name_on_page: str, address_on_page: str = "", phone_on_page: str = "",
         evidence: List[Dict], extraction: Dict, flags: List[Dict] = None,
         raw: Dict = None) -> Dict:
    check = {"name_on_page": name_on_page}
    if address_on_page:
        check["address_on_page"] = address_on_page
    if phone_on_page:
        check["phone_on_page"] = phone_on_page
    record = {
        "obs_id": obs_id,
        "contract_version": PO.CONTRACT_VERSION,
        "hotel_ref": _hotel_ref(census_row),
        "identity_check": check,
        "source_url": source_url,
        "source_type": source_type,
        "authority_tier": PO.SOURCE_TYPE_MAX_TIER[source_type],
        "observed_at": AS_OF,
        "retrieved_at": AS_OF + "T00:00:00Z",
        "capture_method": "deterministic_fetch",
        "evidence": evidence,
        "extraction": extraction,
        "extraction_confidence": "EXACT_QUOTE",
        "flags": flags or [],
    }
    if raw is not None and (raw.get("html_sha256") or raw.get("text_sha256")):
        record["capture_artifacts"] = {
            k: raw[k] for k in ("html_sha256", "text_sha256") if raw.get(k)
        }
    return record


def build_batch() -> List[Dict]:
    batch = []

    # -- Drury Plaza Hotel -- full formal pet policy ------------------------ #
    raw = _load_raw("10-drury-plaza-hotel.json")
    census_row = CENSUS["drury-plaza-hotel"]
    q = ("Pet Policy Dogs and cats accepted. Rooms with pets will be charged "
         "a daily fee of $50 per room plus tax. Service animals are free of "
         "charge. Limit of two pets per room with a combined weight of 80 "
         "pounds.")
    assert _quote_in(raw, q), "drury-plaza-hotel quote not found"
    batch.append(_obs(
        obs_id="drury-plaza-hotel-001", census_row=census_row, raw=raw,
        source_url=raw["final_url"], source_type="official_property_page",
        name_on_page="Drury Plaza Hotel Cleveland Downtown",
        address_on_page="1380 East 6th Street, Cleveland, OH 44114",
        phone_on_page="216-357-3100",
        evidence=[{"quote": q, "location": "Hotel Policies section",
                   "field_refs": ["pets_allowed", "species_allowed", "pet_fee",
                                  "fee_currency", "fee_basis", "fee_scope",
                                  "pet_count_limit", "pet_count_scope",
                                  "weight_limit_combined",
                                  "weight_limit_combined_operator",
                                  "service_animal_exception"]}],
        extraction={"pets_allowed": "true", "species_allowed": "dogs_and_cats",
                    "pet_fee": 5000, "fee_currency": "USD",
                    "fee_basis": "per_night", "fee_scope": "per_room",
                    "pet_count_limit": 2, "pet_count_scope": "room",
                    "weight_limit_combined": 80,
                    "weight_limit_combined_operator": "max",
                    "service_animal_exception": "true"},
    ))

    # -- Drury Inn & Suites Beachwood -- identical Drury standard policy ---- #
    raw = _load_raw("15-drury-inn-and-suites-beachwood.json")
    census_row = CENSUS["drury-inn-suites-beachwood"]
    assert _quote_in(raw, q), "drury-inn-suites-beachwood quote not found"
    batch.append(_obs(
        obs_id="drury-inn-suites-beachwood-001", census_row=census_row, raw=raw,
        source_url=raw["final_url"], source_type="official_property_page",
        name_on_page="Drury Inn & Suites Cleveland Beachwood",
        address_on_page="4100 Orange Place, Orange Village, OH 44122",
        phone_on_page="216-292-9980",
        evidence=[{"quote": q, "location": "Hotel Policies section",
                   "field_refs": ["pets_allowed", "species_allowed", "pet_fee",
                                  "fee_currency", "fee_basis", "fee_scope",
                                  "pet_count_limit", "pet_count_scope",
                                  "weight_limit_combined",
                                  "weight_limit_combined_operator",
                                  "service_animal_exception"]}],
        extraction={"pets_allowed": "true", "species_allowed": "dogs_and_cats",
                    "pet_fee": 5000, "fee_currency": "USD",
                    "fee_basis": "per_night", "fee_scope": "per_room",
                    "pet_count_limit": 2, "pet_count_scope": "room",
                    "weight_limit_combined": 80,
                    "weight_limit_combined_operator": "max",
                    "service_animal_exception": "true"},
    ))

    # -- La Quinta Independence -- marketing-only affirmation --------------- #
    raw = _load_raw("22-la-quinta-inn-cleveland-independence.json")
    census_row = CENSUS["la-quinta-inn-cleveland-independence"]
    q = "our pet-friendly hotel offers easy access to the city"
    assert _quote_in(raw, q), "la-quinta-independence quote not found"
    batch.append(_obs(
        obs_id="la-quinta-inn-cleveland-independence-001", census_row=census_row, raw=raw,
        source_url=raw["final_url"], source_type="official_structured_data",
        name_on_page="La Quinta Inn by Wyndham Cleveland Independence",
        address_on_page="6161 Quarry Ln., Independence, OH 44131",
        phone_on_page="+1-216-447-1133",
        evidence=[{"quote": q, "location": "local-area marketing copy",
                   "field_refs": ["pets_allowed"]}],
        extraction={"pets_allowed": "true"},
        flags=[{"code": "FLAG_MARKETING_ONLY",
                "detail": "affirms the hotel is pet-friendly in marketing copy "
                          "but the page's own Pet & Service Animal Policy "
                          "accordion (fee/species/weight detail) did not "
                          "render server-side; no numeric fields asserted"}],
    ))

    # -- La Quinta Airport North -- marketing-only affirmation -------------- #
    raw = _load_raw("24-la-quinta-inn-and-suites-cleveland-airport-north.json")
    census_row = CENSUS["la-quinta-inn-suites-cleveland-airport-north"]
    q = "Our pet-friendly hotel is just steps from the Puritas Rapid Transit Station"
    assert _quote_in(raw, q), "la-quinta-airport-north quote not found"
    batch.append(_obs(
        obs_id="la-quinta-inn-suites-cleveland-airport-north-001", census_row=census_row, raw=raw,
        source_url=raw["final_url"], source_type="official_structured_data",
        name_on_page="La Quinta Inn & Suites by Wyndham Cleveland - Airport North",
        address_on_page="4222 W 150 St., Cleveland, OH 44135",
        phone_on_page="+1-216-251-8500",
        evidence=[{"quote": q, "location": "local-area marketing copy",
                   "field_refs": ["pets_allowed"]}],
        extraction={"pets_allowed": "true"},
        flags=[{"code": "FLAG_MARKETING_ONLY",
                "detail": "affirms the hotel is pet-friendly in marketing copy "
                          "but the page's own Pet & Service Animal Policy "
                          "accordion (fee/species/weight detail) did not "
                          "render server-side; no numeric fields asserted"}],
    ))

    # -- Super 8 Richfield/Cleveland -- marketing-only affirmation ---------- #
    raw = _load_raw("38-super-8-by-wyndham-richfield-cleveland.json")
    census_row = CENSUS["super-8-by-wyndham-richfield-cleveland"]
    q = "Accessible rooms are available at our pet-friendly, non-smoking hotel."
    assert _quote_in(raw, q), "super-8-richfield quote not found"
    batch.append(_obs(
        obs_id="super-8-by-wyndham-richfield-cleveland-001", census_row=census_row, raw=raw,
        source_url=raw["final_url"], source_type="official_structured_data",
        name_on_page="Super 8 by Wyndham Richfield/Cleveland",
        address_on_page="4845 Brecksville Rd, Richfield, OH 44286-9621",
        phone_on_page="+1-330-344-9040",
        evidence=[{"quote": q, "location": "local-area marketing copy",
                   "field_refs": ["pets_allowed"]}],
        extraction={"pets_allowed": "true"},
        flags=[{"code": "FLAG_MARKETING_ONLY",
                "detail": "affirms the hotel is pet-friendly in marketing copy "
                          "but the page's own Pet Policy accordion did not "
                          "render server-side; no numeric fields asserted. "
                          "The page's own phone (+1-330-344-9040) differs from "
                          "the CVB-sourced census phone ((330) 659-6888); name "
                          "and address/postal code independently agree, so "
                          "identity rests on those two keys, not phone"}],
    ))

    # -- Super 8 Akron South/Green/Uniontown -- name-token mismatch --------- #
    # PTF-CLEVELAND-POLICY-CAPTURE-WORKER-003: Wyndham's own JSON-LD abbreviates
    # "South" to "S" ("Super 8 by Wyndham Akron S/Green/Uniontown OH"), which the
    # membrane's M10 name-token check treats as a DIFFERENT token from the
    # census's "south" -- so this observation is built, quote-verified and
    # submitted honestly, and is EXPECTED to be REJECT_WRONG_PROPERTY. Address
    # (1605 Corporate Woods Pkwy / Parkway, 44685) and phone
    # ((330) 776-5350 / +1-330-776-5350) both match the census exactly, so a
    # human reviewer can see this is very likely the right property -- but the
    # mechanical identity gate is not overridden here, and this record is
    # retained rejected, not silently forced through.
    raw = _load_raw("60-super-8-by-wyndham-akron-south-green-uniontown.json")
    census_row = CENSUS["super-8-by-wyndham-akron-south-green-uniontown"]
    q = "Our pet-friendly hotel also offers non-smoking and accessible rooms."
    assert _quote_in(raw, q), "super-8-uniontown quote not found"
    batch.append(_obs(
        obs_id="super-8-by-wyndham-akron-south-green-uniontown-001", census_row=census_row, raw=raw,
        source_url=raw["final_url"], source_type="official_structured_data",
        name_on_page="Super 8 by Wyndham Akron S/Green/Uniontown OH",
        address_on_page="1605 Corporate Woods Parkway, Uniontown, OH 44685-7891",
        phone_on_page="+1-330-776-5350",
        evidence=[{"quote": q, "location": "local-area marketing copy",
                   "field_refs": ["pets_allowed"]}],
        extraction={"pets_allowed": "true"},
        flags=[{"code": "FLAG_MARKETING_ONLY",
                "detail": "affirms the hotel is pet-friendly in marketing copy "
                          "but the page's own Pet Policy accordion did not "
                          "render server-side; no numeric fields asserted"}],
    ))

    return batch


def main() -> int:
    batch = build_batch()
    validated = PO.validate_emission_batch(batch)
    print("validated %d observations" % len(validated))

    by_hotel: Dict[str, List[Dict]] = {}
    for obs in validated:
        by_hotel.setdefault(obs["hotel_ref"]["normalized_name"], []).append(obs)

    candidates = []
    membrane_rejections = []
    for name, obs_list in sorted(by_hotel.items()):
        result = RD.derive(obs_list, all_surfaces_reached=True)
        slug = next(s for s, h in CENSUS.items() if h["normalized_name"] == name)
        row = {
            "slug": slug,
            "canonical_name": obs_list[0]["hotel_ref"]["canonical_name"],
            "state": result.state,
            "reasons": list(result.reasons),
            "establishing_fields": sorted(set().union(
                *[PO.establishing_fields(o["extraction"]) for o in obs_list])) if result.establishing_observations else [],
            "observations": [o["obs_id"] for o in obs_list],
            "source_urls": sorted({o["source_url"] for o in obs_list}),
            "source_hashes": [o["capture_artifacts"] for o in obs_list
                              if o.get("capture_artifacts")],
            "rejected_observations": list(result.rejected_observations),
        }
        candidates.append(row)
        if result.rejected_observations:
            membrane_rejections.append(row)

    manifest = {
        "_schema": "ptf-cleveland-policy-capture-003-proposed-authority/1.0",
        "market_id": MARKET,
        "generated_at": AS_OF,
        "run_id": RUN_ID,
        "base_authority_commit": "ec2c6f6",
        "note": ("Proposed candidates only. Does NOT modify "
                 "hotel_policy_facts_cleveland-akron-canton-oh.json, "
                 "seed_businesses.csv, or hotel_exclusions.json -- those stay "
                 "at the PTF-CLEVELAND-OVERNIGHT-AUTHORITY-001 authority "
                 "(188 census / 19 published / 8 verified no-pets) pending "
                 "explicit integration review."),
        "reproduction": {
            "fetch_command": "python scripts/pettripfinder/cleveland_capture_003_fetch.py",
            "observations_command": "python scripts/pettripfinder/cleveland_capture_003_observations.py",
            "closeout_command": "python scripts/pettripfinder/cleveland_capture_003_closeout.py",
            "raw_capture_location": "data/worker_runs/pettripfinder/cleveland-policy-capture-003/raw/ "
                                    "(gitignored; regenerate via fetch_command)",
        },
        "candidates": candidates,
        "remaining_unresolved": CO.build_report(),
    }
    OUT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    OUT_MANIFEST.write_bytes(json.dumps(manifest, indent=2).encode("utf-8"))
    print("wrote", OUT_MANIFEST)

    OUT_OBSERVATIONS.parent.mkdir(parents=True, exist_ok=True)
    OUT_OBSERVATIONS.write_bytes(json.dumps(validated, indent=2).encode("utf-8"))
    print("wrote", OUT_OBSERVATIONS)

    for row in candidates:
        print(row["slug"], "->", row["state"], row["reasons"])
    if membrane_rejections:
        print("\nmembrane-rejected (retained, not published):")
        for row in membrane_rejections:
            print(" ", row["slug"], [r["verdict"] for r in row["rejected_observations"]])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
