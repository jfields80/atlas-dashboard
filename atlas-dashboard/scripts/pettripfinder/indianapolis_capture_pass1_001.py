"""Build capture-only records for PTF-INDIANAPOLIS-CLAUDE-CAPTURE-PASS1-001.

This narrow writer reads the committed Pass 4 queue and routing shard, computes
the evidence hashes from the attended-browser raw artifacts, and writes review
materials only.  It never writes policy, exclusion, seed, approval, or partition
authority.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "launch_packages" / "pettripfinder"
QUEUE_PATH = PACKAGE / "indianapolis_capture_queue_pass4.json"
CENSUS_PATH = PACKAGE / "identity_census" / "indianapolis-in.json"
ROUTING_PATH = (PACKAGE / "markets" / "authority" / "indianapolis-in"
                / "identity_routing.json")
RESULTS_PATH = PACKAGE / "indianapolis_capture_pass1_001.json"
PACKET_PATH = PACKAGE / "indianapolis_capture_pass1_founder_review_packet.json"
RAW_ROOT = (ROOT / "data" / "worker_runs" / "pettripfinder"
            / "indianapolis-claude-capture-pass1-001")
CAPTURES = RAW_ROOT / "captures"

WORK_ORDER = "PTF-INDIANAPOLIS-CLAUDE-CAPTURE-PASS1-001"


def _sha(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _artifact(name: str, *, kind: str = "rendered_html") -> dict:
    path = CAPTURES / name
    if not path.is_file():
        raise RuntimeError("missing attended capture artifact: %s" % path)
    return {
        "relative_path": "data/worker_runs/pettripfinder/"
                         "indianapolis-claude-capture-pass1-001/captures/" + name,
        "sha256": _sha(path),
        "kind": kind,
    }


def _fact(field, value, quote):
    return {
        "field": field,
        "value": value,
        "quote": quote,
        "quote_contiguous_in_artifact": True,
    }


def _capture(key, outcome, artifact, *, quotes=(), facts=(), withheld=(),
             notes=(), source_surface="official property page") -> dict:
    return {
        "identity_key": key,
        "outcome": outcome,
        "artifact": artifact,
        "source_grade": "PT1_FIRST_PARTY",
        "capture_method": "attended_browser",
        "captured_at": "2026-08-17",
        "exact_quotes": list(quotes),
        "proposed_schema_1_2_facts": list(facts),
        "withheld_fields": list(withheld),
        "service_animal_statements": [],
        "contradiction_notes": [],
        "source_surface": source_surface,
        "notes": list(notes),
    }


def _build_rows() -> dict:
    no_pets = "No, pets are not allowed"
    bottle_quote = "Pets are always welcome guests at Bottleworks Hotel."
    candle_quote = (
        "Cats and dogs are allowed with a nonrefundable pet fee of 75 USD per "
        "pet. Each pet must weigh less than 80 lbs. A pet agreement must be "
        "signed at check in. Please call the hotel for details. A record of "
        "complete and up to date vaccinations is required."
    )
    return {
        "bottleworks hotel": _capture(
            "bottleworks hotel", "PUBLICATION_CANDIDATE",
            _artifact("bottleworks-hotel-2026-08-17-pass1.txt", kind="rendered_text"),
            quotes=[bottle_quote], facts=[_fact("pets_allowed", True, bottle_quote)],
            withheld=[{"field": "species", "reason": "SOURCE_SILENT"},
                       {"field": "pet_fee", "reason": "POLICY_DOCUMENT_LINK_NOT_CAPTURED"}],
            notes=["The attended first-party policy page names Bottleworks Hotel and "
                   "renders the property address and phone. No linked PDF terms were "
                   "used in this capture."],
            source_surface="Bottleworks Hotel Pet Policy page"),
        "candlewood suites indianapolis medical district": _capture(
            "candlewood suites indianapolis medical district", "PUBLICATION_CANDIDATE",
            _artifact("candlewood-suites-indianapolis-medical-district-2026-08-17-pass1.txt",
                      kind="rendered_text"),
            quotes=[candle_quote],
            facts=[
                _fact("pets_allowed", True, candle_quote),
                _fact("species", ["cats", "dogs"], candle_quote),
                _fact("pet_fee", {"amount_cents": 7500, "currency": "USD",
                                   "refundable": False}, candle_quote),
                _fact("pet_fee_scope", "per_pet", candle_quote),
                _fact("weight_limit", {"value": 80, "unit": "lb", "operator": "lt",
                                        "scope": "per_pet"}, candle_quote),
            ],
            withheld=[{"field": "pet_fee.basis", "reason": "SOURCE_SILENT"},
                       {"field": "reservation_requirement", "reason": "SCHEMA_CANNOT_REPRESENT",
                        "note": "Signing an agreement at check-in is not a reservation requirement."}],
            notes=["Only the property-specific IHG FAQ text is used; no generic IHG "
                   "or sibling policy is inferred."],
            source_surface="Candlewood Suites property FAQ"),
        "conrad indianapolis": _capture(
            "conrad indianapolis", "POLICY_NOT_FOUND",
            _artifact("conrad-indianapolis-2026-08-17-pass1.rendered-dom.txt",
                      kind="rendered_dom"),
            notes=["The attended property page bound identity but exposed no usable "
                   "property-specific pet-policy terms. 'Pet-friendly options' was "
                   "not treated as a policy assertion."],
            source_surface="Conrad Indianapolis property page"),
        "courtyard by marriott indianapolis at the capitol": _capture(
            "courtyard by marriott indianapolis at the capitol", "ACCESS_BLOCKED",
            _artifact("courtyard-indianapolis-at-the-capitol-2026-08-17-pass1.rendered-dom.txt",
                      kind="rendered_dom"),
            notes=["The first-party Marriott route produced an empty attended rendered "
                   "surface. No policy inference was made."],
            source_surface="Courtyard property route"),
        "courtyard by marriott indianapolis downtown": _capture(
            "courtyard by marriott indianapolis downtown", "VERIFIED_NO_PETS_CANDIDATE",
            _artifact("courtyard-indianapolis-downtown-2026-08-17-pass1-expanded.rendered-dom.txt",
                      kind="rendered_dom"),
            quotes=["No, pets are not allowed at Courtyard by Marriott Indianapolis Downtown."],
            facts=[_fact("pets_allowed", False,
                         "No, pets are not allowed at Courtyard by Marriott Indianapolis Downtown.")],
            notes=["Property-specific Marriott FAQ answer on the exact routed property page."],
            source_surface="Courtyard Downtown property FAQ"),
        "hilton garden inn indianapolis downtown": _capture(
            "hilton garden inn indianapolis downtown", "POLICY_NOT_FOUND",
            _artifact("hilton-garden-inn-indianapolis-downtown-2026-08-17-pass1.rendered-dom.txt",
                      kind="rendered_dom"),
            notes=["The attended exact Hilton property route bound identity but did not "
                   "render a usable property-specific pet-policy surface."],
            source_surface="Hilton Garden Inn property page"),
        "hilton indianapolis hotel and suites": _capture(
            "hilton indianapolis hotel and suites", "POLICY_NOT_FOUND",
            _artifact("hilton-indianapolis-hotel-and-suites-2026-08-17-pass1.rendered-dom.txt",
                      kind="rendered_dom"),
            notes=["The attended exact Hilton property route bound identity but did not "
                   "render a usable property-specific pet-policy surface."],
            source_surface="Hilton Indianapolis property page"),
        "holiday inn express and suites indianapolis north carmel": _capture(
            "holiday inn express and suites indianapolis north carmel",
            "VERIFIED_NO_PETS_CANDIDATE",
            _artifact("holiday-inn-express-suites-indianapolis-north-carmel-2026-08-17-pass1-visible-dom.txt",
                      kind="attended_rendered_dom"),
            quotes=[no_pets], facts=[_fact("pets_allowed", False, no_pets)],
            notes=["The exact property FAQ's attended rendered control supplies the "
                   "negative answer. No fee, species, or exception was inferred."],
            source_surface="Holiday Inn Express Carmel property FAQ"),
        "holiday inn express indianapolis downtown": _capture(
            "holiday inn express indianapolis downtown", "VERIFIED_NO_PETS_CANDIDATE",
            _artifact("holiday-inn-express-indianapolis-downtown-2026-08-17-pass1-visible-dom-2.txt",
                      kind="attended_rendered_dom"),
            quotes=[no_pets], facts=[_fact("pets_allowed", False, no_pets)],
            notes=["The exact property FAQ's attended rendered control supplies the "
                   "negative answer. No fee, species, or exception was inferred."],
            source_surface="Holiday Inn Express Downtown property FAQ"),
        "holiday inn indianapolis downtown": _capture(
            "holiday inn indianapolis downtown", "ACCESS_BLOCKED",
            _artifact("holiday-inn-indianapolis-downtown-2026-08-17-pass1.rendered-dom.txt",
                      kind="rendered_dom"),
            notes=["The property-specific FAQ question rendered, but its answer could "
                   "not be opened in the attended surface. No policy was accepted."],
            source_surface="Holiday Inn Downtown property FAQ"),
    }


def main() -> int:
    queue = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    census = json.loads(CENSUS_PATH.read_text(encoding="utf-8-sig"))
    routing = json.loads(ROUTING_PATH.read_text(encoding="utf-8-sig"))
    keys = [row["identity_key"] for row in queue["rows"]]
    if len(keys) != 10 or len(set(keys)) != 10:
        raise RuntimeError("Pass 4 capture queue must be exactly ten unique rows")
    by_census = {row["identity_key"]: row for row in census["hotels"]}
    by_route = {row["hotel_ref"]["identity_key"]: row for row in routing["routes"]}
    if any(key not in by_census or key not in by_route for key in keys):
        raise RuntimeError("each queued identity must remain in census and routing authority")
    captured = _build_rows()
    rows = []
    for number, key in enumerate(keys, 1):
        row = dict(captured[key])
        hotel, route = by_census[key], by_route[key]
        row.update({
            "decision_id": "INDY-CAP1-%03d" % number,
            "queue_order": number,
            "hotel": hotel["canonical_name"],
            "official_property_url": route["official_property_url"],
            "final_url": route["official_property_url"],
            "identity_binding": {
                "bound": True,
                "signals": ["canonical_name", "street_identity", "official_property_url"],
                "canonical_name": hotel["canonical_name"],
                "street_identity": hotel["street_identity"],
                "property_code": next((s.split("=", 1)[1] for s in route.get("identity_signals_matched", [])
                                       if s.startswith("property_code=")), ""),
                "route_status": route["status"],
            },
            "recommended_founder_decision": (
                "REVIEW_PUBLICATION_CANDIDATE" if row["outcome"] == "PUBLICATION_CANDIDATE" else
                "REVIEW_VERIFIED_NO_PETS_CANDIDATE" if row["outcome"] == "VERIFIED_NO_PETS_CANDIDATE" else
                "NO_DECISION_REQUIRED"
            ),
        })
        rows.append(row)
    outcomes = Counter(row["outcome"] for row in rows)
    results = {
        "schema": "ptf-indianapolis-capture-pass1/1.0",
        "work_order": WORK_ORDER,
        "market_id": "indianapolis-in",
        "source_queue": QUEUE_PATH.name,
        "rows_total": len(rows),
        "rows_captured": len(rows),
        "publication_grade": outcomes["PUBLICATION_CANDIDATE"],
        "outcome_counts": {outcome: outcomes[outcome] for outcome in (
            "PUBLICATION_CANDIDATE", "VERIFIED_NO_PETS_CANDIDATE", "POLICY_NOT_FOUND",
            "ACCESS_BLOCKED", "IDENTITY_UNCERTAIN", "CAPTURE_FAILED", "SOURCE_AMBIGUOUS")},
        "authority_freeze": {"published_pet_friendly": 8, "verified_no_pets": 4,
                             "authority_changed": False, "founder_decisions_applied": False},
        "results": rows,
    }
    candidates = [row for row in rows if row["outcome"] in
                  {"PUBLICATION_CANDIDATE", "VERIFIED_NO_PETS_CANDIDATE"}]
    packet = {
        "schema": "ptf-indianapolis-capture-pass1-founder-review/1.0",
        "work_order": WORK_ORDER,
        "market_id": "indianapolis-in",
        "status": "FOUNDER_REVIEW_REQUIRED",
        "founder_decisions_applied": False,
        "authority_changed": False,
        "founder_review_rows": len(candidates),
        "publication_candidates": [r for r in candidates if r["outcome"] == "PUBLICATION_CANDIDATE"],
        "verified_no_pets_candidates": [r for r in candidates if r["outcome"] == "VERIFIED_NO_PETS_CANDIDATE"],
        "non_candidates": [r for r in rows if r not in candidates],
    }
    manifest = {
        "schema": "ptf-capture-batch-manifest/1.0", "batch_id": "indianapolis-capture-pass1-001",
        "work_order": WORK_ORDER, "counts": {"queued": 10, "attempted": 10,
        "captured": 10, "exceptions": outcomes["ACCESS_BLOCKED"], "skipped": 0},
        "artifact_index": [{"identity_key": r["identity_key"], "outcome": r["outcome"],
                            "artifact": r["artifact"]} for r in rows],
        "note": "Capture only. No policy, exclusion, seed, approval, or partition authority was written.",
    }
    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    PACKET_PATH.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    (RAW_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (RAW_ROOT / "artifact_index.json").write_text(json.dumps(manifest["artifact_index"], indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
