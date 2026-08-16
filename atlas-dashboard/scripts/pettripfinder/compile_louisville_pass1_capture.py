"""PTF-LOUISVILLE-ATTENDED-CAPTURE-PASS1-001 -- compile the 7-row batch.

Reads gitignored captured HTML, verifies quote contiguity and identity
signals, and writes the two committed reports. Does not write policy
authority or founder approvals.

    python -m scripts.pettripfinder.compile_louisville_pass1_capture
"""
from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from pathlib import Path

from scripts.pettripfinder.census_partition_builder import write_json
from scripts.pettripfinder.contracts import enums

REPO = Path(__file__).resolve().parents[2]
PKG = REPO / "launch_packages" / "pettripfinder"
ART = REPO / "data" / "operator_evidence" / "louisville-pass1-capture-001"
RAW = ART / "raw"
RESULTS = PKG / "markets" / "reports" / "louisville_pass1_capture_results.json"
PACKET = PKG / "markets" / "reports" / "louisville_pass1_founder_review_packet.json"
CENSUS = PKG / "identity_census" / "louisville-ky.json"
WORK = "PTF-LOUISVILLE-ATTENDED-CAPTURE-PASS1-001"
AS_OF = "2026-08-16"

BATCH = [
    "21c museum hotel louisville",
    "bellwether hotel",
    "econo lodge downtown",
    "galt house hotel",
    "hotel genevieve",
    "hotel louisville downtown",
    "the brown hotel",
]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _assert_contiguous(html: str, quote: str) -> None:
    if quote not in html:
        raise SystemExit("quote not contiguous in artifact: %r" % quote[:80])


def main() -> None:
    census = json.loads(CENSUS.read_text(encoding="utf-8-sig"))
    hotels = {h["identity_key"]: h for h in census["hotels"]}
    for key in BATCH:
        if key not in hotels:
            raise SystemExit("missing census row %s" % key)

    a21 = RAW / "21c-museum-hotel-louisville__faq-chrome.html"
    a_bell = RAW / "bellwether-hotel__faqs.html"
    a_econo = RAW / "econo-lodge-downtown__amenities.html"
    a_galt = RAW / "galt-house-hotel__faq.html"
    a_hl = RAW / "hotel-louisville-downtown__rooms.html"
    a_brown = RAW / "the-brown-hotel__faq.html"
    for path in (a21, a_bell, a_econo, a_galt, a_hl, a_brown):
        if not path.is_file() or path.stat().st_size < 1000:
            raise SystemExit("missing artifact %s" % path.name)

    q21 = (
        "Pets are always welcome at\u00a021c. The pet fee is $40 and a pet "
        "waiver form must be completed and signed at check-in."
    )
    q_bell = (
        "The Bellwether Hotel allows dogs only with the following restrictions: "
        "Dogs are only allowed in first floor rooms. We allow up to two dogs to "
        "stay as long as their combined weight is not over 50 pounds, or one dog "
        "not over 50 pounds. A $35 pet fee will be required at time of booking."
    )
    q_econo = "No Pets Allowed"
    q_galt = (
        "The hotel allows up to two dogs (45 lbs or less) per room for a fee "
        "of $50 per dog. You must request to have your room cleaned and "
        "accompany your dog while the room is being cleaned."
    )
    q_hl = "Is Hotel Louisville pet-friendly?</span><br />No, only service animals are welcome at the property."
    q_hl_display = (
        "Is Hotel Louisville pet-friendly? No, only service animals are "
        "welcome at the property."
    )
    q_brown = "Pets not allowed (service animals are welcome, and are exempt from fees)."

    _assert_contiguous(_text(a21), q21)
    _assert_contiguous(_text(a_bell), q_bell)
    _assert_contiguous(_text(a_econo), q_econo)
    _assert_contiguous(_text(a_galt), q_galt)
    _assert_contiguous(_text(a_hl), q_hl)
    _assert_contiguous(_text(a_brown), q_brown)
    _assert_contiguous(_text(a21), "502.217.6300")
    _assert_contiguous(_text(a_bell), "1300 Bardstown Road")
    _assert_contiguous(_text(a_econo), "401 South 2nd St")
    _assert_contiguous(_text(a_galt), "140 N Fourth St")
    _assert_contiguous(_text(a_hl), "120 West Broadway")
    _assert_contiguous(_text(a_brown), "335 West Broadway")

    captured_at = "2026-08-16"
    rows = []

    def ev(field, quote, url, sha, kind="rendered_html"):
        return OrderedDict((
            ("field", field),
            ("quote", quote),
            ("source_url", url),
            ("source_grade", enums.GRADE_PT1_FIRST_PARTY),
            ("artifact_class", enums.PUBLICATION_GRADE_EVIDENCE),
            ("artifact_sha256", "sha256:%s" % sha),
            ("artifact_kind", kind),
            ("captured_at", captured_at),
            ("capture_method", "https_get_official_page"),
        ))

    rows.append(OrderedDict((
        ("decision_id", "LVL-P1-001"),
        ("hotel", "21c Museum Hotel Louisville"),
        ("identity_key", "21c museum hotel louisville"),
        ("queued_url", hotels["21c museum hotel louisville"]["official_url"]),
        ("final_url", "https://21cmuseumhotels.com/louisville/faq/"),
        ("identity_binding", "BOUND"),
        ("identity_signals", ["21c Museum Hotel Louisville", "502.217.6300", "Louisville FAQ"]),
        ("outcome", "AFFIRMATIVE_PARTIAL"),
        ("source_grade", enums.GRADE_PT1_FIRST_PARTY),
        ("artifact_relpath", "raw/21c-museum-hotel-louisville__faq-chrome.html"),
        ("artifact_sha256", _sha(a21)),
        ("artifact_bytes", a21.stat().st_size),
        ("quotes", [q21]),
        ("proposed_facts", OrderedDict((
            ("pets_allowed", True),
        ))),
        ("withheld_fields", OrderedDict((
            ("species", "SOURCE_AMBIGUOUS: page says pets, not dogs or cats"),
            ("pet_fee.basis", "SOURCE_AMBIGUOUS: $40 stated without stay/night basis"),
            ("pet_fee.scope", "SOURCE_AMBIGUOUS: $40 stated without per-pet/per-room scope"),
        ))),
        ("notes", "Waiver required at check-in. Fee amount $40 is stated but not structured."),
        ("recommended_founder_decision", "HOLD_PARTIAL_AFFIRMATIVE"),
    )))
    rows.append(OrderedDict((
        ("decision_id", "LVL-P1-002"),
        ("hotel", "Bellwether Hotel"),
        ("identity_key", "bellwether hotel"),
        ("queued_url", hotels["bellwether hotel"]["official_url"]),
        ("final_url", "https://www.thebellwetherhotel.com/faqs"),
        ("identity_binding", "BOUND"),
        ("identity_signals", ["The Bellwether Hotel", "1300 Bardstown Road", "40204"]),
        ("outcome", "AFFIRMATIVE_STRUCTURED"),
        ("source_grade", enums.GRADE_PT1_FIRST_PARTY),
        ("artifact_relpath", "raw/bellwether-hotel__faqs.html"),
        ("artifact_sha256", _sha(a_bell)),
        ("artifact_bytes", a_bell.stat().st_size),
        ("quotes", [q_bell]),
        ("proposed_facts", OrderedDict((
            ("pets_allowed", True),
            ("species", ["dog"]),
            ("pet_count_limit", 2),
            ("combined_weight_limit", {"value": 50, "unit": "lb", "scope": "combined"}),
            ("pet_room_restriction", "Dogs are only allowed in first floor rooms."),
            ("unattended_policy",
             "Pets must not be left unattended in room, or anywhere else on hotel property unless crated."),
            ("reservation_requirement",
             "Please notify us at time of booking if a dog will be staying."),
        ))),
        ("withheld_fields", OrderedDict((
            ("pet_fee.basis", "SOURCE_AMBIGUOUS: $35 required at booking; payment timing is not fee basis"),
            ("pet_fee.scope", "SOURCE_AMBIGUOUS: $35 pet fee does not say per pet or per stay"),
        ))),
        ("notes", "ESA not permitted. $200 cleaning if pet evidence in second-floor rooms is a conditional other charge, not a general restriction."),
        ("recommended_founder_decision", "APPROVE_AFFIRMATIVE_STRUCTURED"),
    )))
    rows.append(OrderedDict((
        ("decision_id", "LVL-P1-003"),
        ("hotel", "Econo Lodge Downtown"),
        ("identity_key", "econo lodge downtown"),
        ("queued_url", hotels["econo lodge downtown"]["official_url"]),
        ("final_url", "http://www.econodowntown.com/louisville-ky-hotel-amenities.html"),
        ("identity_binding", "BOUND"),
        ("identity_signals", ["Econo Lodge Downtown", "401 South 2nd St.", "502-583-2841"]),
        ("outcome", "NEGATIVE"),
        ("source_grade", enums.GRADE_PT1_FIRST_PARTY),
        ("artifact_relpath", "raw/econo-lodge-downtown__amenities.html"),
        ("artifact_sha256", _sha(a_econo)),
        ("artifact_bytes", a_econo.stat().st_size),
        ("quotes", [q_econo]),
        ("proposed_facts", OrderedDict((("pets_allowed", False),))),
        ("withheld_fields", OrderedDict()),
        ("notes", "Amenities list states No Pets Allowed."),
        ("recommended_founder_decision", "APPROVE_VERIFIED_NO_PETS"),
    )))
    rows.append(OrderedDict((
        ("decision_id", "LVL-P1-004"),
        ("hotel", "Galt House Hotel"),
        ("identity_key", "galt house hotel"),
        ("queued_url", hotels["galt house hotel"]["official_url"]),
        ("final_url", "https://galthouse.com/hotel-faq/"),
        ("identity_binding", "BOUND"),
        ("identity_signals", ["Galt House Hotel", "140 N Fourth St", "502-589-5200"]),
        ("outcome", "AFFIRMATIVE_STRUCTURED"),
        ("source_grade", enums.GRADE_PT1_FIRST_PARTY),
        ("artifact_relpath", "raw/galt-house-hotel__faq.html"),
        ("artifact_sha256", _sha(a_galt)),
        ("artifact_bytes", a_galt.stat().st_size),
        ("quotes", [q_galt]),
        ("proposed_facts", OrderedDict((
            ("pets_allowed", True),
            ("species", ["dog"]),
            ("pet_count_limit", 2),
            ("pet_count_scope", "per_room"),
            ("weight_limit", {"value": 45, "unit": "lb", "scope": "per_pet",
                              "operator": "lte"}),
            ("pet_fee", {"amount_cents": 5000, "currency": "USD",
                         "basis": "per_stay", "scope": "per_pet"}),
            ("unattended_policy",
             "You must request to have your room cleaned and accompany your dog while the room is being cleaned."),
        ))),
        ("withheld_fields", OrderedDict()),
        ("notes", "Rooms page also states Cost for stay: $50 (DOGS ONLY). Fee treated as per stay per dog."),
        ("recommended_founder_decision", "APPROVE_AFFIRMATIVE_STRUCTURED"),
    )))
    rows.append(OrderedDict((
        ("decision_id", "LVL-P1-005"),
        ("hotel", "Hotel Genevieve"),
        ("identity_key", "hotel genevieve"),
        ("queued_url", hotels["hotel genevieve"]["official_url"]),
        ("final_url", "https://www.hyatt.com/jdv-by-hyatt/en-US/sdfkk-hotel-genevieve"),
        ("identity_binding", "NOT_BOUND"),
        ("identity_signals", []),
        ("outcome", "ACCESS_BLOCKED"),
        ("source_grade", ""),
        ("artifact_relpath", ""),
        ("artifact_sha256", ""),
        ("artifact_bytes", 0),
        ("quotes", []),
        ("proposed_facts", OrderedDict()),
        ("withheld_fields", OrderedDict()),
        ("notes",
         "bunkhousehotels.com/hotel-genevieve now redirects to Hyatt JDV sdfkk. "
         "Automated HTTPS GET received 403 on Bunkhouse and Hyatt E6020 on the "
         "policies page. No publication-grade artifact retained. Third-party "
         "summaries were not used."),
        ("recommended_founder_decision", "HOLD_ACCESS_BLOCKED"),
    )))
    rows.append(OrderedDict((
        ("decision_id", "LVL-P1-006"),
        ("hotel", "Hotel Louisville Downtown"),
        ("identity_key", "hotel louisville downtown"),
        ("queued_url", hotels["hotel louisville downtown"]["official_url"]),
        ("final_url", "https://www.hotellouisville.org/rooms"),
        ("identity_binding", "BOUND"),
        ("identity_signals", [
            "Hotel Louisville", "120 West Broadway", "40202", "502-582-2241",
        ]),
        ("outcome", "NEGATIVE"),
        ("source_grade", enums.GRADE_PT1_FIRST_PARTY),
        ("artifact_relpath", "raw/hotel-louisville-downtown__rooms.html"),
        ("artifact_sha256", _sha(a_hl)),
        ("artifact_bytes", a_hl.stat().st_size),
        ("quotes", [q_hl_display]),
        ("proposed_facts", OrderedDict((("pets_allowed", False),))),
        ("withheld_fields", OrderedDict()),
        ("notes",
         "FAQ is on the public Hotel Louisville rooms page, not a mission-campus "
         "page. Service animals only. Not inferred from Wayside campus use. "
         "Hospital Hospitality House remains a separate non-census identity."),
        ("recommended_founder_decision", "APPROVE_VERIFIED_NO_PETS"),
    )))
    rows.append(OrderedDict((
        ("decision_id", "LVL-P1-007"),
        ("hotel", "The Brown Hotel"),
        ("identity_key", "the brown hotel"),
        ("queued_url", hotels["the brown hotel"]["official_url"]),
        ("final_url", "https://www.brownhotel.com/frequently-asked-questions"),
        ("identity_binding", "BOUND"),
        ("identity_signals", ["The Brown Hotel", "335 West Broadway", "502-583-1234"]),
        ("outcome", "NEGATIVE"),
        ("source_grade", enums.GRADE_PT1_FIRST_PARTY),
        ("artifact_relpath", "raw/the-brown-hotel__faq.html"),
        ("artifact_sha256", _sha(a_brown)),
        ("artifact_bytes", a_brown.stat().st_size),
        ("quotes", [q_brown]),
        ("proposed_facts", OrderedDict((("pets_allowed", False),))),
        ("withheld_fields", OrderedDict()),
        ("notes", "Explicit Pets not allowed. Service-animal access is not pet-friendly."),
        ("recommended_founder_decision", "APPROVE_VERIFIED_NO_PETS"),
    )))

    counts = OrderedDict()
    for name in (
        "AFFIRMATIVE_STRUCTURED", "AFFIRMATIVE_PARTIAL", "NEGATIVE",
        "POLICY_NOT_FOUND", "IDENTITY_UNCERTAIN", "POLICY_SCOPE_AMBIGUOUS",
        "ROUTING_PROBLEM", "ACCESS_BLOCKED", "CAPTURE_FAILED",
    ):
        counts[name] = sum(1 for r in rows if r["outcome"] == name)

    results = OrderedDict((
        ("schema", "ptf-louisville-pass1-capture-results/1.0"),
        ("work_order", WORK),
        ("market_id", "louisville-ky"),
        ("as_of", AS_OF),
        ("note",
         "Seven-row PT1 independent attended capture. Raw HTML is gitignored "
         "under data/operator_evidence/louisville-pass1-capture-001/raw. "
         "No policy authority and no founder approvals were written."),
        ("batch_total", 7),
        ("outcome_counts", counts),
        ("publication_grade_artifacts",
         sum(1 for r in rows if r["artifact_sha256"])),
        ("positive_candidates",
         sum(1 for r in rows if r["outcome"].startswith("AFFIRMATIVE"))),
        ("negative_candidates", counts["NEGATIVE"]),
        ("founder_decisions_required",
         sum(1 for r in rows if r["outcome"] != "ACCESS_BLOCKED")),
        ("authority_changed", False),
        ("rows", rows),
    ))
    write_json(RESULTS, results)

    packet_rows = []
    for row in rows:
        packet_rows.append(OrderedDict((
            ("decision_id", row["decision_id"]),
            ("hotel", row["hotel"]),
            ("identity_key", row["identity_key"]),
            ("url", row["queued_url"]),
            ("final_url", row["final_url"]),
            ("identity_binding", row["identity_binding"]),
            ("exact_quotes", row["quotes"]),
            ("artifact_sha256", row["artifact_sha256"]),
            ("source_grade", row["source_grade"]),
            ("proposed_schema_1_2_facts", row["proposed_facts"]),
            ("withheld_fields", row["withheld_fields"]),
            ("ambiguity_or_contradiction", row["notes"]),
            ("recommended_founder_decision", row["recommended_founder_decision"]),
            ("outcome", row["outcome"]),
        )))
    packet = OrderedDict((
        ("schema", "ptf-louisville-pass1-founder-review-packet/1.0"),
        ("work_order", WORK),
        ("market_id", "louisville-ky"),
        ("as_of", AS_OF),
        ("note",
         "Founder review packet only. Does not approve, publish, or change "
         "hotel_policy_facts. Six rows need a founder decision; Hotel "
         "Genevieve is ACCESS_BLOCKED with no proposed facts."),
        ("founder_approvals_written", False),
        ("decision_count", 6),
        ("rows", packet_rows),
    ))
    write_json(PACKET, packet)
    print("wrote", RESULTS.name, PACKET.name)
    print("outcomes", dict(counts))


if __name__ == "__main__":
    main()
