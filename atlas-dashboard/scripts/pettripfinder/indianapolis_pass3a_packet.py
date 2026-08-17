"""Build Indianapolis Pass 3A capture-results and founder-review packets."""

from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
LP = _REPO / "launch_packages" / "pettripfinder"
CENSUS = LP / "identity_census" / "indianapolis-in.json"
WORK_ORDER = "PTF-INDIANAPOLIS-ATTENDED-CAPTURE-PASS3A-001"
GATE = "STRICT_TWO_INDEPENDENT_NON_URL_KEYS"

ART = {
    "residence inn by marriott indianapolis airport": {
        "file": "www-marriott-com-en-us-hotels-indap-residence-inn-indianapolis-airport-overview-2026-08-17T01-05-26-993Z.json",
        "html": "sha256:b5aeb913d0318c6edcaf2932bfd240c0455b3888cfae1aaf1ddf5620c4dce9ad",
        "text": "sha256:f8ef8b72ed114bb93ef8d3da92cbe9e442f5a7c631a98e3cbc9c5afb30fce172",
        "png": "sha256:e2ff28a1c1f05ee3ed40a6db796f4e8d763e986e1c1aa178594cf5b222a7315d",
        "at": "2026-08-17T01:05:26.993Z",
        "url": "https://www.marriott.com/en-us/hotels/indap-residence-inn-indianapolis-airport/overview/",
    },
}


def _intended(h):
    return OrderedDict((
        ("canonical_name", h["canonical_name"]),
        ("first_party_url", h.get("official_url") or ""),
        ("street", h.get("address") or ""),
        ("city", h.get("city") or ""),
        ("state", h.get("state") or ""),
        ("postal_code", h.get("postal_code") or ""),
        ("phone", h.get("phone") or ""),
        ("property_code", h.get("property_code") or ""),
    ))


def _rendered(**kwargs):
    return OrderedDict((
        ("page_name", kwargs.get("page_name") or ""),
        ("final_url", kwargs.get("final_url") or ""),
        ("street", kwargs.get("street") or ""),
        ("city", kwargs.get("city") or ""),
        ("state", kwargs.get("state") or ""),
        ("postal_code", kwargs.get("postal_code") or ""),
        ("phone", kwargs.get("phone") or ""),
        ("property_code", kwargs.get("property_code") or ""),
        ("source", kwargs.get("source") or ""),
    ))


def _binding(*, bound, intended, rendered, keys, notes):
    return OrderedDict((
        ("bound", bound),
        ("clean_bind", bound),
        ("gate", GATE),
        ("intended", intended),
        ("rendered", rendered),
        ("independent_non_url_keys", list(keys)),
        ("url_identifier_used_as_bind", False),
        ("conflicts", []),
        ("notes", notes),
    ))


def _signals(bind):
    intended = bind.get("intended") or {}
    rendered = bind.get("rendered") or {}
    return OrderedDict((
        ("bound", bool(bind.get("bound"))),
        ("clean_bind", bool(bind.get("clean_bind"))),
        ("intended_street", intended.get("street") or ""),
        ("rendered_street", rendered.get("street") or ""),
        ("intended_city_zip", ("%s %s" % (
            intended.get("city") or "", intended.get("postal_code") or "")).strip()),
        ("rendered_city_zip", ("%s %s" % (
            rendered.get("city") or "", rendered.get("postal_code") or "")).strip()),
        ("intended_phone", intended.get("phone") or ""),
        ("rendered_phone", rendered.get("phone") or ""),
        ("property_code", rendered.get("property_code") or intended.get("property_code") or ""),
        ("independent_non_url_keys", list(bind.get("independent_non_url_keys") or [])),
    ))


def _base(h, n, outcome, runner, rec, note, quotes=None, facts=None,
          withheld=None, binding=None, policy_source=None, art=None):
    row = OrderedDict((
        ("decision_id", "INDY-P3A-%03d" % n),
        ("queue_id", "INDY-P3A-%03d" % n),
        ("hotel", h["canonical_name"]),
        ("identity_key", h["identity_key"]),
        ("corridor", h["corridor"]),
        ("brand", h.get("brand") or ""),
        ("official_url", h.get("official_url") or ""),
        ("requested_url", h.get("official_url") or ""),
        ("final_url", (art or {}).get("url") or h.get("official_url") or ""),
        ("runner_reason", runner),
        ("outcome", outcome),
        ("identity_binding", binding),
        ("identity_signals", _signals(binding or {})),
        ("policy_source", policy_source),
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
        ("service_animal_statements", []),
        ("contradiction_notes", []),
        ("recommended_founder_decision", rec),
    ))
    return row


def main() -> int:
    census = json.loads(CENSUS.read_text(encoding="utf-8-sig"))
    by = {r["identity_key"]: r for r in census["hotels"]}
    rows = []

    res = by["residence inn by marriott indianapolis airport"]
    rows.append(_base(
        res, 1,
        "AFFIRMATIVE_STRUCTURED", "CAPTURED", "APPROVE_PUBLISH_STRUCTURED",
        "Official Marriott Pet Policy on the Residence Inn Airport property page. "
        "Street 5224 West Southern Avenue is not Fairfield at 5220. Marriott path "
        "code indap is not IHG Crowne Airport. Fee due-at-check-in is payment "
        "timing, not a reservation requirement.",
        quotes=[
            "Pets Welcome",
            "Nonrefundable pet fee of $100.00 due at check-in.",
            "Non-Refundable Pet Fee Per Stay: $100.00",
            "Maximum Pet Weight: 75.0lbs",
            "Maximum Number of Pets in Room: 2",
        ],
        facts=[
            {"field": "pets_allowed", "value": True,
             "quote": "Pets Welcome", "quote_contiguous_in_artifact": True},
            {"field": "pet_fee",
             "value": {"amount_cents": 10000, "currency": "USD",
                       "basis": "per_stay", "refundable": False},
             "quote": "Non-Refundable Pet Fee Per Stay: $100.00",
             "refundability_quote": "Nonrefundable pet fee of $100.00 due at check-in.",
             "quote_contiguous_in_artifact": True},
            {"field": "weight_limit",
             "value": {"value": 75.0, "unit": "lb", "operator": "lte"},
             "quote": "Maximum Pet Weight: 75.0lbs",
             "quote_contiguous_in_artifact": True},
            {"field": "pet_count_limit", "value": 2,
             "quote": "Maximum Number of Pets in Room: 2",
             "quote_contiguous_in_artifact": True},
            {"field": "pet_count_scope", "value": "per_room",
             "quote": "Maximum Number of Pets in Room: 2",
             "quote_contiguous_in_artifact": True},
        ],
        withheld=[
            {"field": "pet_fee.scope", "reason": "SOURCE_SILENT",
             "note": "Per stay is stated; per_pet vs per_room is not."},
            {"field": "weight_limit.scope", "reason": "SOURCE_SILENT",
             "note": "75.0lbs is stated without per-pet or combined."},
            {"field": "species", "reason": "SOURCE_SILENT",
             "note": "Generic pets is not dogs+cats."},
        ],
        policy_source=OrderedDict((
            ("kind", "official_brand_property_page"),
            ("surface", "Marriott Residence Inn Airport overview Pet Policy block"),
            ("first_party", True),
            ("sibling_or_brand_generic", False),
        )),
        binding=_binding(
            bound=True, intended=_intended(res),
            rendered=_rendered(
                page_name="Residence Inn by Marriott Indianapolis Airport",
                final_url=ART["residence inn by marriott indianapolis airport"]["url"],
                street="5224 West Southern Avenue", city="Indianapolis",
                state="Indiana", postal_code="46241",
                phone="+13172441500", property_code="indap", source="jsonld"),
            keys=["address@structured_metadata", "phone@structured_metadata"],
            notes="Street and phone match. Distinct from Fairfield 5220 West Southern "
                  "Avenue. URL code indap discarded as a bind."),
        art=ART["residence inn by marriott indianapolis airport"]))

    stay = by["staybridge suites indianapolis airport plainfield"]
    rows.append(_base(
        stay, 2,
        "IDENTITY_UNCERTAIN", "IDENTITY_FAILED", "HOLD_RETRY_IDENTITY",
        "Phone and body-text property identifier agreed; structured street did "
        "not. IDENTITY_FAILED is a key contradiction. No policy extracted. "
        "Not Holiday Inn Express at 6296 Cambridge Way. Not a refusal.",
        binding=_binding(
            bound=False, intended=_intended(stay),
            rendered=_rendered(
                page_name="Extended Stay Hotel In Plainfield, IN | Staybridge Suites Indianapolis - Airport",
                final_url=stay["official_url"],
                property_code="indpf", source="diagnostic_only"),
            keys=["phone@structured_metadata"],
            notes="One independent non-URL key (phone). Street never agreed, so "
                  "policy is withheld. Neighbor HIE policy not inherited.")))

    counts = OrderedDict((
        ("AFFIRMATIVE_STRUCTURED", 1),
        ("AFFIRMATIVE_PARTIAL", 0),
        ("NEGATIVE", 0),
        ("POLICY_NOT_FOUND", 0),
        ("IDENTITY_UNCERTAIN", 1),
        ("ROUTING_PROBLEM", 0),
        ("ACCESS_BLOCKED", 0),
        ("CAPTURE_FAILED", 0),
    ))
    results = OrderedDict((
        ("schema", "ptf-indianapolis-pass3a-capture-results/1.0"),
        ("work_order", WORK_ORDER),
        ("as_of", "2026-08-17"),
        ("market_id", "indianapolis-in"),
        ("captured_by", "grok-4.6 (PTF-INDIANAPOLIS-ATTENDED-CAPTURE-PASS3A-001, agent)"),
        ("capture_method",
         "attended browser (dedicated visible Chrome via official CaptureRunner); "
         "raw HTML/PNG only in gitignored "
         "data/worker_runs/pettripfinder/indianapolis-attended-capture-003a/"),
        ("source_queue", "indianapolis_capture_ready_queue_003.json"),
        ("rows_total", 2),
        ("rows_captured", 1),
        ("rows_with_publication_grade_artifact", 1),
        ("hilton_rows_driven", 0),
        ("founder_decisions_applied", False),
        ("authority_freeze", OrderedDict((
            ("capture_only", True),
            ("published_pet_friendly", 0),
            ("verified_no_pets", 1),
            ("verified_no_pets_identity_key", "crowne plaza indianapolis airport"),
            ("indianapolis_policy_facts_written", False),
            ("exclusion_authority_altered", False),
            ("pass2_decisions_applied", False),
        ))),
        ("outcome_counts", counts),
        ("rule",
         "Only the two remaining non-Hilton queue-003 rows were driven. "
         "Hilton-family rows were not executed. Residence Inn is not Fairfield "
         "and not Crowne Airport. Staybridge is not Holiday Inn Express. "
         "No founder decision was applied. No authority was written."),
        ("speed_benchmark", OrderedDict((
            ("total_elapsed_seconds", 119.89),
            ("rows_attempted", 2),
            ("usable_artifacts", 1),
            ("positive_candidates", 1),
            ("negative_candidates", 0),
            ("identity_failures", 1),
            ("policy_not_found", 0),
            ("access_blocked", 0),
            ("captures_per_hour", 60.1),
            ("useful_artifact_yield", 0.5),
            ("started_at", "2026-08-17T01:04:00Z"),
            ("finished_at", "2026-08-17T01:05:59Z"),
        ))),
        ("results", rows),
    ))
    packet = OrderedDict((
        ("schema", "ptf-indianapolis-pass3a-founder-review-packet/1.0"),
        ("work_order", WORK_ORDER),
        ("as_of", "2026-08-17"),
        ("prepared_by", "grok-4.6 (PTF-INDIANAPOLIS-ATTENDED-CAPTURE-PASS3A-001, agent)"),
        ("status", "FOUNDER_REVIEW_REQUIRED"),
        ("founder_decisions_applied", False),
        ("authority_freeze", results["authority_freeze"]),
        ("rule",
         "Nothing here is published. Pass-2 decisions remain recorded-not-applied. "
         "Approving this positive would write schema 1.2 facts later. "
         "Staybridge stays unresolved."),
        ("positive_candidates", [r for r in rows if r["outcome"].startswith("AFFIRMATIVE")]),
        ("negative_candidates", []),
        ("identity_uncertain",
         [r for r in rows if r["outcome"] == "IDENTITY_UNCERTAIN"]),
        ("founder_decisions_required", 2),
        ("authority_changed", False),
        ("hilton_remaining", 6),
    ))
    (LP / "indianapolis_pass3a_capture_results.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8")
    (LP / "indianapolis_pass3a_founder_review_packet.json").write_text(
        json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
