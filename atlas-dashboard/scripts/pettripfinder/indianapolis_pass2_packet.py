"""Build Indianapolis Pass 2 capture-results and founder-review packets."""

from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
LP = _REPO / "launch_packages" / "pettripfinder"
CENSUS = LP / "identity_census" / "indianapolis-in.json"
WORK_ORDER = "PTF-INDIANAPOLIS-ATTENDED-CAPTURE-PASS2-001"

# Artifact hashes from the gitignored worker tree (re-derived).
ART = {
    "crowne plaza indianapolis downtown union station": {
        "file": "www-ihg-com-crowneplaza-hotels-us-en-indianapolis-inddt-hoteldetail-2026-08-16T23-34-26-159Z.json",
        "html": "sha256:04a917429e58067512df65a39b783edfdeb7115c9b9412c72d450d849bdb53b0",
        "text": "sha256:fe16dbf33d84a65cda4e2845cf4efc4b98308ad99a67a3fa2c27abf5f5a0053e",
        "png": "sha256:b28a4ae6080b7a61ee651bae112650a5b03dcb56324e5a2b9d8c14bef2331ff6",
        "bundle": "sha256:05751c62dd039478ff947a9e1e694a392905314a8e47c0720499ff546ba90ab0",
        "at": "2026-08-16T23:34:26.159Z",
        "url": "https://www.ihg.com/crowneplaza/hotels/us/en/indianapolis/inddt/hoteldetail",
    },
    "holiday inn express plainfield": {
        "file": "www-ihg-com-holidayinnexpress-hotels-us-en-plainfield-indsw-hoteldetail-2026-08-16T23-40-10-365Z.json",
        "html": "sha256:78724d7f36d53f35103bc99808ae47644ec9ebf7b715d8af65fc53878dad6e2d",
        "text": "sha256:db757296db075816c05083082c1af0698267e83195bfc59e33a8d6fa369313cc",
        "png": "sha256:82013404120bfb9bcaa16fa48b46b5bc55c4f11d338b0045de01ef2a0863cb31",
        "bundle": "sha256:f8484b20286538b6b143d0fc6e0fb965b8f258e5495f818cee472b778dad97ee",
        "at": "2026-08-16T23:40:10.365Z",
        "url": "https://www.ihg.com/holidayinnexpress/hotels/us/en/plainfield/indsw/hoteldetail",
    },
    "courtyard by marriott indianapolis castleton": {
        "file": "www-marriott-com-en-us-hotels-indcs-courtyard-indianapolis-castleton-overview-2026-08-16T23-36-05-052Z.json",
        "html": "sha256:b11b710af01cdbb6d4784319f6a9dd31dacd66d0d25934c728b2b7fdc7d0ad36",
        "text": "sha256:2871aa5f74f475db3133c50346a8859625d8a0200b203a24440fe59907268392",
        "png": "sha256:3509147773a035d52ae24f6c02ee5cf0e4ca3ba0f6abaaf374753db658815f50",
        "bundle": "sha256:f2d929d7891c4bcc54f8d3be109b4d63c07fa44add351f2fc4ea181a2dfb908f",
        "at": "2026-08-16T23:36:05.052Z",
        "url": "https://www.marriott.com/en-us/hotels/indcs-courtyard-indianapolis-castleton/overview/",
    },
    "fairfield inn and suites indianapolis airport": {
        "file": "www-marriott-com-en-us-hotels-indfa-fairfield-inn-and-suites-indianapolis-airpor-2026-08-16T23-45-47-536Z.json",
        "html": "sha256:1a703848d019546e7ed5d1e74e0d5537e8f6c136a0c4995fc7f9252d2916ed27",
        "text": "sha256:604a256c06bd74c6fd120e13f498775ccb7fd6f3a0a83186816c14c298b82992",
        "png": "sha256:29acb8c85a9a86b9b6bae61ed169090e2711203533ffa503d508fb7b661350db",
        "bundle": "sha256:c33fc38e7116345a81dd0aea7663225ab07b2f3fc7c2bb2cccbda091c4291b6d",
        "at": "2026-08-16T23:45:47.536Z",
        "url": "https://www.marriott.com/en-us/hotels/indfa-fairfield-inn-and-suites-indianapolis-airport/overview/",
    },
    "jw marriott indianapolis": {
        "file": "www-marriott-com-en-us-hotels-indjw-jw-marriott-indianapolis-overview-2026-08-16T23-48-15-887Z.json",
        "html": "sha256:2eabcbe4f504d9ad50167262366df63e3198f76a41aa12f727b446ecc3272ba9",
        "text": "sha256:6d86ea285f2bb5cc3060030746f713dc966aad4e51047841dbc799cefee87a31",
        "png": "sha256:cd76cd865903e8dd88872ecc602e10630b4d3613f0daab690ce6a036a6f5f14e",
        "bundle": "sha256:bc9f681e4d12a32e6c19f1bb57a2de4fcc971dacea8e81d8508d9f5222baf3e4",
        "at": "2026-08-16T23:48:15.887Z",
        "url": "https://www.marriott.com/en-us/hotels/indjw-jw-marriott-indianapolis/overview/",
    },
    "le meridien indianapolis": {
        "file": "www-marriott-com-en-us-hotels-indmd-le-meridien-indianapolis-overview-2026-08-16T23-50-11-789Z.json",
        "html": "sha256:60dd50d47a9337aa7108e85765c8e79eb21ad165c07a7f1a044fe868530d3b28",
        "text": "sha256:5b9707a8ad4dccefa83d6fa72ca1003da296b85e4ac444a7a5784d1906f72824",
        "png": "sha256:949562524b6048763f6980b8759dfd27fe8bc658d43319dc9ed50d229ae9f09b",
        "bundle": "sha256:5b5baa74d4fd555eb15622b971ca03336dc477c133e3e240fd46e8e9246401a7",
        "at": "2026-08-16T23:50:11.789Z",
        "url": "https://www.marriott.com/en-us/hotels/indmd-le-meridien-indianapolis/overview/",
    },
}


def _base(h, n, outcome, runner, rec, note, quotes=None, facts=None, withheld=None, contradictions=None):
    art = ART.get(h["identity_key"])
    row = OrderedDict((
        ("decision_id", "INDY-P2-%03d" % n),
        ("queue_id", "INDY-P2-%03d" % n),
        ("hotel", h["canonical_name"]),
        ("identity_key", h["identity_key"]),
        ("corridor", h["corridor"]),
        ("brand", h.get("brand") or ""),
        ("requested_url", h.get("official_url") or ""),
        ("final_url", (art or {}).get("url") or h.get("official_url") or ""),
        ("runner_reason", runner),
        ("outcome", outcome),
        ("identity_binding", {"bound": outcome not in (
            "IDENTITY_UNCERTAIN", "ACCESS_BLOCKED", "CAPTURE_FAILED")}),
        ("artifact_file", (art or {}).get("file")),
        ("artifact_sha256", (art or {}).get("html")),
        ("artifact_kind", "rendered_html" if art else None),
        ("text_sha256", (art or {}).get("text")),
        ("screenshot_sha256", (art or {}).get("png")),
        ("captured_at", (art or {}).get("at")),
        ("capture_method", "attended_browser" if art else "attended_browser_attempt"),
        ("source_grade", "PT1_FIRST_PARTY" if art else None),
        ("notes", [note]),
        ("exact_quotes", quotes or []),
        ("proposed_schema_1_2_facts", facts or []),
        ("withheld_fields", withheld or []),
        ("contradiction_notes", contradictions or []),
        ("recommended_founder_decision", rec),
    ))
    return row


def main() -> int:
    census = json.loads(CENSUS.read_text(encoding="utf-8-sig"))
    by = {r["identity_key"]: r for r in census["hotels"]}
    rows = []

    rows.append(_base(
        by["comfort inn indianapolis airport plainfield"], 1,
        "IDENTITY_UNCERTAIN", "IDENTITY_UNVERIFIABLE", "HOLD_RETRY_IDENTITY",
        "Choice page produced no identity-bearing snapshot in 21.0s (hydration timeout). Not a refusal."))
    rows.append(_base(
        by["courtyard by marriott indianapolis airport"], 2,
        "IDENTITY_UNCERTAIN", "IDENTITY_FAILED", "HOLD_RETRY_IDENTITY",
        "Name, city, phone and URL property identifier matched, but the capture-time gate still returned IDENTITY_FAILED. No policy extracted. Sibling Marriott policy not inherited."))
    rows.append(_base(
        by["courtyard by marriott indianapolis castleton"], 3,
        "NEGATIVE", "CAPTURED", "APPROVE_VERIFIED_NO_PETS",
        "Official Marriott Pet Policy block states Pets Not Allowed. Service animals only is a legal access category, not a guest-pet permission.",
        quotes=["Pets Not Allowed", "Service animals only"],
        facts=[{"field": "pets_allowed", "value": False,
                "quote": "Pets Not Allowed", "quote_contiguous_in_artifact": True}],
        withheld=[],
        contradictions=["Service animals only sits beside the refusal and is not read as a pet permission."]))
    rows[-1]["identity_binding"] = {
        "bound": True,
        "notes": "Capture proceeded after address + URL property code indcs.",
    }
    rows.append(_base(
        by["crowne plaza indianapolis downtown union station"], 4,
        "NEGATIVE", "POLICY_ABSENT_CONFIRMED", "APPROVE_VERIFIED_NO_PETS",
        "Property-specific IHG FAQ refusal. Independent of Crowne Plaza Airport. No service-animal sentence.",
        quotes=["No, pets are not allowed at Crowne Plaza Indianapolis-Dwtn-Union Stn."],
        facts=[{"field": "pets_allowed", "value": False,
                "quote": "No, pets are not allowed at Crowne Plaza Indianapolis-Dwtn-Union Stn.",
                "quote_contiguous_in_artifact": True}]))
    rows[-1]["identity_binding"] = {
        "bound": True,
        "notes": "Identity CONFIRMED on address + property identifier inddt.",
    }
    rows.append(_base(
        by["delta hotels by marriott indianapolis airport"], 5,
        "IDENTITY_UNCERTAIN", "IDENTITY_FAILED", "HOLD_RETRY_IDENTITY",
        "Name, city, phone and URL property identifier matched; gate still IDENTITY_FAILED. No policy extracted. Sibling Marriott policy not inherited."))
    rows.append(_base(
        by["fairfield inn and suites indianapolis airport"], 6,
        "NEGATIVE", "CAPTURED", "APPROVE_VERIFIED_NO_PETS",
        "Official Marriott Pet Policy block states Pets Not Allowed. A non-refundable $100 cleaning fee sits in the same block and is withheld as ambiguous.",
        quotes=["Pets Not Allowed",
                "Non Refundable Cleaning Fee of $100.00 due at check-in."],
        facts=[{"field": "pets_allowed", "value": False,
                "quote": "Pets Not Allowed", "quote_contiguous_in_artifact": True}],
        withheld=[{"field": "other_charges.cleaning_fee",
                   "reason": "SOURCE_AMBIGUOUS",
                   "quote": "Non Refundable Cleaning Fee of $100.00 due at check-in.",
                   "note": "Appears in the Pet Policy block beside a no-pets statement; not bound as a pet charge."}]))
    rows[-1]["identity_binding"] = {"bound": True, "notes": "Capture proceeded with identity_evidence_incomplete warning."}
    rows.append(_base(
        by["holiday inn express plainfield"], 7,
        "AFFIRMATIVE_STRUCTURED", "CAPTURED", "APPROVE_PUBLISH_STRUCTURED",
        "Official IHG pet widget is property-specific. Fee scope and pet-count scope are not stated and are withheld.",
        quotes=[
            "Pets are welcome at Holiday Inn Express Indianapolis Airport.",
            "Dogs permitted with a nominal nonrefundable fee each night.",
            "Pet fee per night: 25 USD",
            "Pet weight limit: No weight limit per pet",
            "2 pets allowed",
            "Pets allowed: Only dogs allowed",
        ],
        facts=[
            {"field": "pets_allowed", "value": True,
             "quote": "Pets are welcome at Holiday Inn Express Indianapolis Airport.",
             "quote_contiguous_in_artifact": True},
            {"field": "species", "value": {"dogs": "allowed"},
             "quote": "Pets allowed: Only dogs allowed",
             "quote_contiguous_in_artifact": True},
            {"field": "pet_fee", "value": {"amount_cents": 2500, "currency": "USD", "basis": "per_night"},
             "quote": "Pet fee per night: 25 USD",
             "quote_contiguous_in_artifact": True},
            {"field": "weight_limit_stated_none", "value": True,
             "quote": "Pet weight limit: No weight limit per pet",
             "quote_contiguous_in_artifact": True},
            {"field": "pet_count_limit", "value": 2,
             "quote": "2 pets allowed",
             "quote_contiguous_in_artifact": True},
        ],
        withheld=[
            {"field": "pet_fee.scope", "reason": "SOURCE_SILENT",
             "note": "per night is stated; per_pet vs per_room is not."},
            {"field": "pet_count_scope", "reason": "SOURCE_SILENT",
             "note": "2 pets allowed does not say per room or per stay."},
        ]))
    rows[-1]["identity_binding"] = {"bound": True, "notes": "Capture proceeded with identity_evidence_incomplete warning."}
    rows.append(_base(
        by["holiday inn indianapolis airport"], 8,
        "IDENTITY_UNCERTAIN", "IDENTITY_UNVERIFIABLE", "HOLD_RETRY_IDENTITY",
        "IHG page produced no identity-bearing snapshot in 20.9s (hydration timeout). Not a refusal. Crowne Airport refusal not inherited."))
    rows.append(_base(
        by["jw marriott indianapolis"], 9,
        "NEGATIVE", "CAPTURED", "APPROVE_VERIFIED_NO_PETS",
        "Official Marriott Pet Policy block states Pets Not Allowed. FAQ lists the question with no answer; the policy block is the evidence.",
        quotes=["Pets Not Allowed"],
        facts=[{"field": "pets_allowed", "value": False,
                "quote": "Pets Not Allowed", "quote_contiguous_in_artifact": True}]))
    rows[-1]["identity_binding"] = {"bound": True, "notes": "Capture proceeded with identity_evidence_incomplete warning."}
    rows.append(_base(
        by["le meridien indianapolis"], 10,
        "AFFIRMATIVE_STRUCTURED", "CAPTURED", "APPROVE_PUBLISH_STRUCTURED",
        "Official Marriott Pet Policy: Pets Welcome, no pet fee, 40 lb maximum with no stated scope. Generic pets is not dogs+cats.",
        quotes=["Pets Welcome", "Pets are welcome. No pet fee.", "Maximum Pet Weight: 40.0lbs"],
        facts=[
            {"field": "pets_allowed", "value": True,
             "quote": "Pets are welcome. No pet fee.",
             "quote_contiguous_in_artifact": True},
            {"field": "weight_limit",
             "value": {"value": 40.0, "unit": "lb", "operator": "lte"},
             "quote": "Maximum Pet Weight: 40.0lbs",
             "quote_contiguous_in_artifact": True},
        ],
        withheld=[
            {"field": "weight_limit.scope", "reason": "SOURCE_SILENT",
             "note": "40.0lbs is stated without per-pet or combined."},
            {"field": "species", "reason": "SOURCE_SILENT",
             "note": "Generic pets is not dogs+cats."},
        ]))
    rows[-1]["identity_binding"] = {"bound": True, "notes": "Capture proceeded with identity_evidence_incomplete warning."}

    counts = OrderedDict((
        ("AFFIRMATIVE_STRUCTURED", 2),
        ("AFFIRMATIVE_PARTIAL", 0),
        ("NEGATIVE", 4),
        ("POLICY_NOT_FOUND", 0),
        ("IDENTITY_UNCERTAIN", 4),
        ("ROUTING_PROBLEM", 0),
        ("ACCESS_BLOCKED", 0),
        ("CAPTURE_FAILED", 0),
    ))
    results = OrderedDict((
        ("schema", "ptf-indianapolis-pass2-capture-results/1.0"),
        ("work_order", WORK_ORDER),
        ("as_of", "2026-08-16"),
        ("market_id", "indianapolis-in"),
        ("captured_by", "grok-4.6 (PTF-INDIANAPOLIS-ATTENDED-CAPTURE-PASS2-001, agent)"),
        ("capture_method",
         "attended browser (dedicated visible Chrome via official CaptureRunner); "
         "raw HTML/PNG only in gitignored "
         "data/worker_runs/pettripfinder/indianapolis-attended-capture-002/"),
        ("source_queue", "indianapolis_capture_ready_queue_002.json"),
        ("rows_total", 10),
        ("rows_captured", 6),
        ("rows_with_publication_grade_artifact", 6),
        ("hilton_rows_driven", 0),
        ("outcome_counts", counts),
        ("rule",
         "Only the recommended 10 non-Hilton ready-queue rows were driven. "
         "Crowne Downtown refusal is independent of Crowne Airport. "
         "No sibling Marriott policy was inherited. No authority was written."),
        ("speed_benchmark", OrderedDict((
            ("batch_total", 10),
            ("started_at", "2026-08-16T23:31:29.696Z"),
            ("finished_at", "2026-08-16T23:50:53.080Z"),
            ("elapsed_seconds", 1179.09),
            ("captures_completed", 10),
            ("successful_artifacts", 6),
            ("median_inter_capture_gap_seconds", 106.0),
            ("captures_per_hour", 30.5),
            ("positive_rate", 0.2),
            ("negative_rate", 0.4),
            ("policy_not_found_rate", 0.0),
            ("identity_uncertain_rate", 0.4),
        ))),
        ("results", rows),
    ))
    positives = [r for r in rows if r["outcome"].startswith("AFFIRMATIVE")]
    negatives = [r for r in rows if r["outcome"] == "NEGATIVE"]
    packet = OrderedDict((
        ("schema", "ptf-indianapolis-pass2-founder-review-packet/1.0"),
        ("work_order", WORK_ORDER),
        ("as_of", "2026-08-16"),
        ("prepared_by", "grok-4.6 (PTF-INDIANAPOLIS-ATTENDED-CAPTURE-PASS2-001, agent)"),
        ("status", "FOUNDER_REVIEW_REQUIRED"),
        ("rule",
         "Nothing here is published. Approving a negative writes an exclusion "
         "later. Approving a positive writes schema 1.2 facts later. "
         "Identity-uncertain rows stay unresolved."),
        ("positive_candidates", positives),
        ("negative_candidates", negatives),
        ("identity_uncertain",
         [r for r in rows if r["outcome"] == "IDENTITY_UNCERTAIN"]),
        ("founder_decisions_required", 10),
        ("authority_changed", False),
    ))
    (LP / "indianapolis_pass2_capture_results.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8")
    (LP / "indianapolis_pass2_founder_review_packet.json").write_text(
        json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
