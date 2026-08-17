"""Build Indianapolis Hilton fresh-session capture packets."""

from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
LP = _REPO / "launch_packages" / "pettripfinder"
CENSUS = LP / "identity_census" / "indianapolis-in.json"
WORK_ORDER = "PTF-INDIANAPOLIS-HILTON-FRESH-SESSION-001"
GATE = "STRICT_TWO_INDEPENDENT_NON_URL_KEYS"

ART = {
    "hampton inn and suites indianapolis airport": {
        "file": "www-hilton-com-en-hotels-indarhx-hampton-suites-indianapolis-airport-2026-08-17T01-18-47-690Z.json",
        "html": "sha256:03f00e314f1fa726f23cc8f0da870ab823d475ef2e7b75a9c3708644b237a76d",
        "text": "sha256:4b3b2eda797a7d86776bfb673e0b31297e9229f7f373b953ab15902c25260550",
        "png": "sha256:1afacaf0328e08271219d79a822e89a618b5b1b7af3e097e84978e9b2064e9b7",
        "at": "2026-08-17T01:18:47.690Z",
        "url": "https://www.hilton.com/en/hotels/indarhx-hampton-suites-indianapolis-airport/",
    },
    "hampton inn and suites indianapolis keystone": {
        "file": "www-hilton-com-en-hotels-indkehx-hampton-suites-indianapolis-keystone-2026-08-17T01-22-28-053Z.json",
        "html": "sha256:997311c6ba5fb44985d4ca821c59999d8fbbc0401ab005556739e4b110d60534",
        "text": "sha256:440dc2b57c7a246c56cc743a91a7a2aacf303d28cfb26606f3047450de54d7a5",
        "png": "sha256:0a35e30cfac6ed87ec8830811ca22c703c369c70732e2ed21f7bd2e19bf14c82",
        "at": "2026-08-17T01:22:28.053Z",
        "url": "https://www.hilton.com/en/hotels/indkehx-hampton-suites-indianapolis-keystone/",
    },
    "hampton inn and suites indianapolis west speedway": {
        "file": "www-hilton-com-en-hotels-indswhx-hampton-suites-indianapolis-west-speedway-2026-08-17T01-24-57-392Z.json",
        "html": "sha256:bb0c4d98ee49d6fa7439165e32e9e6696d3816e83832a49a7933d9f5954bc8d0",
        "text": "sha256:be03148b060d3e5ba0fbbd2014bb559f7a5a683f65ba2e2d30dd8d0728bec462",
        "png": "sha256:ee6b43695eea76e774ca760646be93c73d82373af6a18ae39a41b6fc5211e9a2",
        "at": "2026-08-17T01:24:57.392Z",
        "url": "https://www.hilton.com/en/hotels/indswhx-hampton-suites-indianapolis-west-speedway/",
    },
    "hampton inn indianapolis northeast castleton": {
        "file": "www-hilton-com-en-hotels-indnehx-hampton-indianapolis-ne-castleton-2026-08-17T01-27-21-822Z.json",
        "html": "sha256:9b9cb04c1871e8ad4c7206881bd64b62973f39abfa6bd91526cef60edc216aca",
        "text": "sha256:0e5049dc691957877cb62118ec27a6e4d99c27d79646a2e6585f666183df9467",
        "png": "sha256:449ca2122654efe431992a00fe25af6caaec2e12d1f2746359ad8eb6f7490636",
        "at": "2026-08-17T01:27:21.822Z",
        "url": "https://www.hilton.com/en/hotels/indnehx-hampton-indianapolis-ne-castleton/",
    },
    "hilton garden inn indianapolis airport": {
        "file": "www-hilton-com-en-hotels-indaggi-hilton-garden-inn-indianapolis-airport-2026-08-17T01-29-58-873Z.json",
        "html": "sha256:69bb9e2c1ffcc4ecb546257653949d55b8dfa2fb29aabaac814ea28bdfbd5cac",
        "text": "sha256:295f0d396d4064ae854be83acce0f8b30bca07a646a759f75d1042aae1df2635",
        "png": "sha256:4d168786f0300f9faf1dfd446c9b15b7886036d2cb19403dc543715701abce38",
        "at": "2026-08-17T01:29:58.873Z",
        "url": "https://www.hilton.com/en/hotels/indaggi-hilton-garden-inn-indianapolis-airport/",
    },
}


def _tier(cents, lo, hi, quote):
    tier = OrderedDict((
        ("amount_cents", cents),
        ("currency", "USD"),
        ("role", "REPLACEMENT_PRICE"),
        ("condition_type", "stay_length_range"),
        ("boundary_unit", "nights"),
        ("condition_min", lo),
        ("basis_stated", True),
        ("refundable", False),
    ))
    if hi is not None:
        tier["condition_max"] = hi
    return {"field": "fee_tiers", "value": tier, "quote": quote,
            "quote_contiguous_in_artifact": True}


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
    return OrderedDict((k, kwargs.get(k) or "") for k in (
        "page_name", "final_url", "street", "city", "state", "postal_code",
        "phone", "property_code", "source"))


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
        ("decision_id", "INDY-HFS-%03d" % n),
        ("queue_id", "INDY-HFS-%03d" % n),
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


def _hilton_source(name):
    return OrderedDict((
        ("kind", "official_brand_property_page"),
        ("surface", "Hilton property Pets policy panel on %s" % name),
        ("first_party", True),
        ("sibling_or_brand_generic", False),
    ))


def main() -> int:
    census = json.loads(CENSUS.read_text(encoding="utf-8-sig"))
    by = {r["identity_key"]: r for r in census["hotels"]}
    rows = []

    air = by["hampton inn and suites indianapolis airport"]
    q_air = "1-4 night stay $75; 5+ night stay $125; 2 pets max; dog or cat only"
    rows.append(_base(
        air, 1, "AFFIRMATIVE_STRUCTURED", "CAPTURED", "APPROVE_PUBLISH_STRUCTURED",
        "Hilton Pets panel on the official Hampton Airport page. Street 9020 "
        "Hatfield Drive + phone 317-856-1000 bind. Stay-length ladder kept as "
        "tiers, not a single price. Deposit heading is not a refundable deposit.",
        quotes=["Pets allowed", "Yes", "Yes. $75.00 Non-refundable Fee", q_air],
        facts=[
            {"field": "pets_allowed", "value": True, "quote": "Pets allowed",
             "quote_contiguous_in_artifact": True},
            {"field": "species", "value": {"dogs": "allowed", "cats": "allowed"},
             "quote": "dog or cat only", "quote_contiguous_in_artifact": True},
            {"field": "pet_count_limit", "value": 2, "quote": "2 pets max",
             "quote_contiguous_in_artifact": True},
            _tier(7500, 1, 4, "1-4 night stay $75"),
            _tier(12500, 5, None, "5+ night stay $125"),
        ],
        withheld=[
            {"field": "pet_fee.scope", "reason": "SOURCE_SILENT",
             "note": "Ladder is stay-length; per_pet vs per_room is not stated."},
            {"field": "pet_count_scope", "reason": "SOURCE_SILENT",
             "note": "2 pets max does not say per room or per stay."},
            {"field": "weight_limit", "reason": "SOURCE_SILENT",
             "note": "No weight stated on this property panel."},
        ],
        policy_source=_hilton_source("Hampton Airport"),
        binding=_binding(
            bound=True, intended=_intended(air),
            rendered=_rendered(
                page_name="Hampton Inn & Suites Indianapolis-Airport",
                final_url=ART["hampton inn and suites indianapolis airport"]["url"],
                street="9020 Hatfield Drive", city="Indianapolis", state="IN",
                postal_code="46241", phone="+1 317-856-1000",
                property_code="indarhx", source="jsonld"),
            keys=["address@structured_metadata", "phone@structured_metadata"],
            notes="Street and phone match. URL code discarded as a bind."),
        art=ART["hampton inn and suites indianapolis airport"]))

    key = by["hampton inn and suites indianapolis keystone"]
    q_key = "$75(1-4n),$125(5+n) 2petsMax,dog/cat only"
    rows.append(_base(
        key, 2, "AFFIRMATIVE_STRUCTURED", "CAPTURED", "APPROVE_PUBLISH_STRUCTURED",
        "Hilton Pets panel. Street 8980 River Crossing Boulevard binds. Census "
        "phone empty; page phone +1 317-706-7500 does not conflict. URL discarded.",
        quotes=["Pets allowed", "Yes", "Yes. $75.00 Non-refundable Fee",
                "Max weight", "75 lbs", q_key],
        facts=[
            {"field": "pets_allowed", "value": True, "quote": "Pets allowed",
             "quote_contiguous_in_artifact": True},
            {"field": "species", "value": {"dogs": "allowed", "cats": "allowed"},
             "quote": "dog/cat only", "quote_contiguous_in_artifact": True},
            {"field": "pet_count_limit", "value": 2, "quote": "2petsMax",
             "quote_contiguous_in_artifact": True},
            {"field": "weight_limit",
             "value": {"value": 75.0, "unit": "lb", "operator": "lte"},
             "quote": "75 lbs", "quote_contiguous_in_artifact": True},
            _tier(7500, 1, 4, "$75(1-4n)"),
            _tier(12500, 5, None, "$125(5+n)"),
        ],
        withheld=[
            {"field": "pet_fee.scope", "reason": "SOURCE_SILENT",
             "note": "Stay-length ladder; per_pet vs per_room silent."},
            {"field": "weight_limit.scope", "reason": "SOURCE_SILENT",
             "note": "75 lbs has no per-pet or combined wording."},
            {"field": "pet_count_scope", "reason": "SOURCE_SILENT",
             "note": "2petsMax has no room/stay scope."},
        ],
        policy_source=_hilton_source("Hampton Keystone"),
        binding=_binding(
            bound=True, intended=_intended(key),
            rendered=_rendered(
                page_name="Hampton Inn & Suites Indianapolis-Keystone",
                final_url=ART["hampton inn and suites indianapolis keystone"]["url"],
                street="8980 River Crossing Boulevard", city="Indianapolis",
                state="IN", postal_code="46240", phone="+1 317-706-7500",
                property_code="indkehx", source="jsonld"),
            keys=["address@structured_metadata", "phone@structured_metadata"],
            notes="Street matches. Page phone has no census phone to conflict."),
        art=ART["hampton inn and suites indianapolis keystone"]))

    west = by["hampton inn and suites indianapolis west speedway"]
    q_west = "$93.20(1-4n),$155.30(5+n) 2petsMax,dog/cat only"
    rows.append(_base(
        west, 3, "AFFIRMATIVE_STRUCTURED", "CAPTURED", "APPROVE_PUBLISH_STRUCTURED",
        "Hilton Pets panel. Street 2608 Founders Square Drive binds. Page phone "
        "+1 317-969-8321. Max size Large is not a weight and is withheld.",
        quotes=["Pets allowed", "Yes", "Yes. $93.20 Non-refundable Fee",
                "Max weight", "75 lbs", "Max size", "Large", q_west],
        facts=[
            {"field": "pets_allowed", "value": True, "quote": "Pets allowed",
             "quote_contiguous_in_artifact": True},
            {"field": "species", "value": {"dogs": "allowed", "cats": "allowed"},
             "quote": "dog/cat only", "quote_contiguous_in_artifact": True},
            {"field": "pet_count_limit", "value": 2, "quote": "2petsMax",
             "quote_contiguous_in_artifact": True},
            {"field": "weight_limit",
             "value": {"value": 75.0, "unit": "lb", "operator": "lte"},
             "quote": "75 lbs", "quote_contiguous_in_artifact": True},
            _tier(9320, 1, 4, "$93.20(1-4n)"),
            _tier(15530, 5, None, "$155.30(5+n)"),
        ],
        withheld=[
            {"field": "pet_fee.scope", "reason": "SOURCE_SILENT",
             "note": "Stay-length ladder; per_pet vs per_room silent."},
            {"field": "weight_limit.scope", "reason": "SOURCE_SILENT",
             "note": "75 lbs has no per-pet or combined wording."},
            {"field": "pet_count_scope", "reason": "SOURCE_SILENT",
             "note": "2petsMax has no room/stay scope."},
            {"field": "general_restrictions", "reason": "SOURCE_AMBIGUOUS",
             "quote": "Max size Large",
             "note": "Large is not a measured limit and is not parked as a fee."},
        ],
        policy_source=_hilton_source("Hampton West Speedway"),
        binding=_binding(
            bound=True, intended=_intended(west),
            rendered=_rendered(
                page_name="Hampton Inn and Suites Indianapolis West Speedway",
                final_url=ART["hampton inn and suites indianapolis west speedway"]["url"],
                street="2608 Founders Square Drive", city="Indianapolis",
                state="IN", postal_code="46224", phone="+1 317-969-8321",
                property_code="indswhx", source="jsonld"),
            keys=["address@structured_metadata", "phone@structured_metadata"],
            notes="Street matches. Page phone has no census phone to conflict."),
        art=ART["hampton inn and suites indianapolis west speedway"]))

    cas = by["hampton inn indianapolis northeast castleton"]
    q_cas = "1-4 night stay $50; 5+ night stay $75; 2 pets max; dog or cat only"
    rows.append(_base(
        cas, 4, "AFFIRMATIVE_STRUCTURED", "CAPTURED", "APPROVE_PUBLISH_STRUCTURED",
        "Hilton Pets panel. Structured street 6817 E. 82nd Street matches "
        "6817 East 82nd Street. Page phone +1 317-576-0220. No weight stated.",
        quotes=["Pets allowed", "Yes", "Yes. $50.00 Non-refundable Fee", q_cas],
        facts=[
            {"field": "pets_allowed", "value": True, "quote": "Pets allowed",
             "quote_contiguous_in_artifact": True},
            {"field": "species", "value": {"dogs": "allowed", "cats": "allowed"},
             "quote": "dog or cat only", "quote_contiguous_in_artifact": True},
            {"field": "pet_count_limit", "value": 2, "quote": "2 pets max",
             "quote_contiguous_in_artifact": True},
            _tier(5000, 1, 4, "1-4 night stay $50"),
            _tier(7500, 5, None, "5+ night stay $75"),
        ],
        withheld=[
            {"field": "pet_fee.scope", "reason": "SOURCE_SILENT",
             "note": "Stay-length ladder; per_pet vs per_room silent."},
            {"field": "pet_count_scope", "reason": "SOURCE_SILENT",
             "note": "2 pets max has no room/stay scope."},
            {"field": "weight_limit", "reason": "SOURCE_SILENT",
             "note": "No weight stated on this property panel."},
        ],
        policy_source=_hilton_source("Hampton NE Castleton"),
        binding=_binding(
            bound=True, intended=_intended(cas),
            rendered=_rendered(
                page_name="Hampton Inn Indianapolis-Ne/Castleton",
                final_url=ART["hampton inn indianapolis northeast castleton"]["url"],
                street="6817 E. 82nd Street", city="Indianapolis", state="IN",
                postal_code="46250", phone="+1 317-576-0220",
                property_code="indnehx", source="jsonld"),
            keys=["address@structured_metadata", "phone@structured_metadata"],
            notes="E. 82nd Street matches East 82nd Street. URL discarded."),
        art=ART["hampton inn indianapolis northeast castleton"]))

    hgi = by["hilton garden inn indianapolis airport"]
    q_hgi = "$75(1-4 nights), $100(5+nights), 2 pets max"
    rows.append(_base(
        hgi, 5, "AFFIRMATIVE_STRUCTURED", "CAPTURED", "APPROVE_PUBLISH_STRUCTURED",
        "Hilton Pets panel. Street 8910 Hatfield Dr. matches 8910 Hatfield Drive. "
        "Phone 317-856-9100. Species not named; not inferred as dogs+cats.",
        quotes=["Pets allowed", "Yes", "Yes. $75.00 Non-refundable Fee",
                "Max weight", "75 lbs", q_hgi],
        facts=[
            {"field": "pets_allowed", "value": True, "quote": "Pets allowed",
             "quote_contiguous_in_artifact": True},
            {"field": "pet_count_limit", "value": 2, "quote": "2 pets max",
             "quote_contiguous_in_artifact": True},
            {"field": "weight_limit",
             "value": {"value": 75.0, "unit": "lb", "operator": "lte"},
             "quote": "75 lbs", "quote_contiguous_in_artifact": True},
            _tier(7500, 1, 4, "$75(1-4 nights)"),
            _tier(10000, 5, None, "$100(5+nights)"),
        ],
        withheld=[
            {"field": "species", "reason": "SOURCE_SILENT",
             "note": "No dog/cat wording on this panel. Generic pets is not dogs+cats."},
            {"field": "pet_fee.scope", "reason": "SOURCE_SILENT",
             "note": "Stay-length ladder; per_pet vs per_room silent."},
            {"field": "weight_limit.scope", "reason": "SOURCE_SILENT",
             "note": "75 lbs has no per-pet or combined wording."},
            {"field": "pet_count_scope", "reason": "SOURCE_SILENT",
             "note": "2 pets max has no room/stay scope."},
        ],
        policy_source=_hilton_source("Hilton Garden Inn Airport"),
        binding=_binding(
            bound=True, intended=_intended(hgi),
            rendered=_rendered(
                page_name="Hilton Garden Inn Indianapolis Airport",
                final_url=ART["hilton garden inn indianapolis airport"]["url"],
                street="8910 Hatfield Dr.", city="Indianapolis", state="IN",
                postal_code="46241", phone="+1 317-856-9100",
                property_code="indaggi", source="jsonld"),
            keys=["address@structured_metadata", "phone@structured_metadata"],
            notes="Street and phone match. Distinct from Hampton at 9020 Hatfield."),
        art=ART["hilton garden inn indianapolis airport"]))

    home = by["home2 suites by hilton indianapolis airport"]
    rows.append(_base(
        home, 6, "IDENTITY_UNCERTAIN", "IDENTITY_FAILED", "HOLD_RETRY_IDENTITY",
        "Phone and URL identifier agreed; structured street did not. "
        "IDENTITY_FAILED is a key contradiction. No policy extracted. "
        "Challenge page was not used. Not a refusal.",
        binding=_binding(
            bound=False, intended=_intended(home),
            rendered=_rendered(
                page_name="Home2 Suites by Hilton Indianapolis, IN",
                final_url=home["official_url"],
                property_code="indcbht", source="diagnostic_only"),
            keys=["phone@structured_metadata"],
            notes="Phone is not enough. Street 9025 Hatfield Drive did not agree. "
                  "Sibling Hampton/Garden Inn policy not inherited.")))

    counts = OrderedDict((
        ("AFFIRMATIVE_STRUCTURED", 5),
        ("AFFIRMATIVE_PARTIAL", 0),
        ("NEGATIVE", 0),
        ("POLICY_NOT_FOUND", 0),
        ("IDENTITY_UNCERTAIN", 1),
        ("ROUTING_PROBLEM", 0),
        ("ACCESS_BLOCKED", 0),
        ("CAPTURE_FAILED", 0),
    ))
    results = OrderedDict((
        ("schema", "ptf-indianapolis-hilton-fresh-session-results/1.0"),
        ("work_order", WORK_ORDER),
        ("as_of", "2026-08-17"),
        ("market_id", "indianapolis-in"),
        ("captured_by", "grok-4.6 (PTF-INDIANAPOLIS-HILTON-FRESH-SESSION-001, agent)"),
        ("capture_method",
         "fresh visible Chrome profile (no prior Hilton page); official "
         "CaptureRunner; raw HTML/PNG gitignored under "
         "data/worker_runs/pettripfinder/indianapolis-hilton-fresh-session-001/"),
        ("source_queue", "indianapolis_hilton_fresh_session_001.json"),
        ("rows_total", 6),
        ("rows_captured", 5),
        ("rows_with_publication_grade_artifact", 5),
        ("non_hilton_rows_driven", 0),
        ("founder_decisions_applied", False),
        ("fresh_session", True),
        ("authority_freeze", OrderedDict((
            ("capture_only", True),
            ("published_pet_friendly", 0),
            ("verified_no_pets", 1),
            ("pass2_decisions_applied", False),
            ("pass3a_decisions_applied", False),
            ("indianapolis_policy_facts_written", False),
            ("exclusion_authority_altered", False),
        ))),
        ("outcome_counts", counts),
        ("rule",
         "Only the six Hilton-family rows were driven in a new Chrome profile. "
         "No Marriott/IHG/Choice pages. Stay-length ladders are tiers, not a "
         "single price. No founder decision applied. No authority written."),
        ("speed_benchmark", OrderedDict((
            ("total_elapsed_seconds", 880.92),
            ("rows_attempted", 6),
            ("usable_artifacts", 5),
            ("positive_candidates", 5),
            ("negative_candidates", 0),
            ("identity_failures", 1),
            ("policy_not_found", 0),
            ("access_blocked", 0),
            ("captures_per_hour", 24.5),
            ("useful_artifact_yield", 5 / 6),
        ))),
        ("results", rows),
    ))
    packet = OrderedDict((
        ("schema", "ptf-indianapolis-hilton-fresh-session-review/1.0"),
        ("work_order", WORK_ORDER),
        ("as_of", "2026-08-17"),
        ("prepared_by", "grok-4.6 (PTF-INDIANAPOLIS-HILTON-FRESH-SESSION-001, agent)"),
        ("status", "FOUNDER_REVIEW_REQUIRED"),
        ("founder_decisions_applied", False),
        ("authority_changed", False),
        ("authority_freeze", results["authority_freeze"]),
        ("rule",
         "Nothing published. Pass 2 and Pass 3A decisions remain "
         "RECORDED_NOT_APPLIED. Approving a positive writes facts later."),
        ("positive_candidates",
         [r for r in rows if r["outcome"].startswith("AFFIRMATIVE")]),
        ("negative_candidates", []),
        ("identity_uncertain",
         [r for r in rows if r["outcome"] == "IDENTITY_UNCERTAIN"]),
        ("founder_decisions_required", 6),
    ))
    (LP / "indianapolis_hilton_fresh_session_results.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8")
    (LP / "indianapolis_hilton_fresh_session_review_packet.json").write_text(
        json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
