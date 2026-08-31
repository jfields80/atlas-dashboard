"""PTF-PITTSBURGH-PASS4-DECISION-APPLICATION-001 final authority gates."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.pettripfinder.policy_migration import evidence_hash, record_hash


ROOT = Path(__file__).resolve().parents[2]
LP = ROOT / "launch_packages" / "pettripfinder"
REPORTS = LP / "markets" / "reports"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


#: The ten identities PTF-PITTSBURGH-PASS4-DECISION-APPLICATION-001 decided,
#: and the three it explicitly left unresolved. These are what this module's
#: gates are about; the market's running totals are not.
#: The order these gates are about.
WORK_ORDER = "PTF-PITTSBURGH-PASS4-DECISION-APPLICATION-001"

PASS4_PUBLISHED = (
    "motel 6 pittsburgh",
    "sonesta simply suites pittsburgh airport",
    "towneplace suites pittsburgh airport robinson township",
    "hyatt house pittsburgh bloomfield shadyside",
    "hyatt place pittsburgh airport",
    "hyatt place pittsburgh north shore",
    "joinery hotel pittsburgh",
)

#: Pass 4 published this, and PTF-PITTSBURGH-FOUNDER-HOLD-RESOLUTION-005
#: WITHDREW it on a founder ruling. The Pass 4 record asserted pets_allowed
#: from the quote "Pets Welcome" captured 2026-08-17; the page this market owns
#: from 2026-08-23 states "Pets are not allowed. Only service animals are
#: welcome." beside the same $150 fee line, and the current reader withholds
#: pets_allowed as SOURCE_CONTRADICTORY.
#:
#: Asserted as ABSENT rather than quietly dropped from the list above: a later
#: order silently un-publishing one of Pass 4's rows is exactly what this gate
#: should catch, so the withdrawal is named and its ledger is required to
#: explain it.
PASS4_WITHDRAWN = "springhill suites pittsburgh airport"
PASS4_REFUSED = (
    "courtyard by marriott pittsburgh airport",
    "courtyard by marriott pittsburgh airport settlers ridge",
)
PASS4_HELD = (
    "hyatt regency pittsburgh international airport",
    "mansions on fifth",
    "sunnyledge boutique hotel",
)


def test_final_partition_derives_the_ten_decision_transitions():
    partition = load(LP / "pittsburgh_final_partition_001.json")
    # The partition tracks the census, which a later ADD-ONLY promotion may
    # legitimately grow (96 -> 102 at PTF-PITTSBURGH-FOUNDER-HOLD-RESOLUTION-005).
    # What must hold is that it accounts for every identity exactly once.
    assert partition["count"] == len(partition["items"])
    assert len({i["identity_key"] for i in partition["items"]}) == partition["count"]
    # This gate protects PASS 4's OWN ten transitions, not the market's running
    # totals: later application orders move those legitimately, and freezing a
    # global snapshot here would make every one of them look like a regression.
    # (PTF-PITTSBURGH-HARDENED-SYNC-004 Phase 14.)
    assert sum(partition["final_state_counts"].values()) == partition["count"]
    states = {item["identity_key"]: item for item in partition["items"]}
    for key in PASS4_PUBLISHED:
        assert states[key]["final_state"] == "PUBLISHED_PET_FRIENDLY"
        assert states[key]["resolved"] is True
    # The withdrawn row's full history, which is the point of naming it:
    # Pass 4 published it as pet-friendly; PTF-PITTSBURGH-FOUNDER-HOLD-
    # RESOLUTION-005 WITHDREW it once the owned page was found to contradict
    # the record; PTF-PITTSBURGH-IDENTITY-AND-RECAPTURE-006 settled it as a
    # REFUSAL after a free attended re-capture proved the "Pets Welcome"
    # evidence Pass 4 cited was a Marriott UI label (hws.petsAllowed), not a
    # statement by the property.
    #
    # So it must NOT be published, and it must be resolved-as-refused or else
    # unresolved-with-a-next-action. What is forbidden is the state in between:
    # unpublished, unresolved, and with nobody told what to do about it.
    withdrawn = states[PASS4_WITHDRAWN]
    assert withdrawn["final_state"] != "PUBLISHED_PET_FRIENDLY"
    if withdrawn["resolved"]:
        assert withdrawn["final_state"] == "VERIFIED_NO_PETS"
    else:
        assert withdrawn["next_action"].strip()
    for key in PASS4_REFUSED:
        assert states[key]["final_state"] == "VERIFIED_NO_PETS"
        assert states[key]["resolved"] is True
    # The three rows Pass 4 explicitly did NOT resolve are not attributed to it.
    # A LATER order may legitimately settle one -- PTF-PITTSBURGH-IDENTITY-
    # CLOSE-007 published Hyatt Regency Airport from a free attended capture --
    # and asserting they stay unresolved forever would make that progress look
    # like a regression. What must hold is that Pass 4 never claims credit for
    # a row it left open.
    for key in PASS4_HELD:
        if states[key]["resolved"]:
            assert states[key]["determined_by"] != WORK_ORDER, key
    states = {row["identity_key"]: row for row in partition["items"]}
    assert states["courtyard by marriott pittsburgh airport"]["final_state"] == "VERIFIED_NO_PETS"
    assert states["courtyard by marriott pittsburgh airport settlers ridge"]["final_state"] == "VERIFIED_NO_PETS"
    for key in ("hyatt regency pittsburgh international airport",
                "mansions on fifth", "sunnyledge boutique hotel"):
        if states[key]["resolved"]:
            assert states[key]["determined_by"] != WORK_ORDER, key


def test_final_records_preserve_the_special_founder_semantics_and_governance():
    facts = {row["identity_key"]: row for row in load(LP / "hotel_policy_facts_pittsburgh-pa.json")["hotels"]}
    # A SUBSET check, not a size check: this gate exists to prove Pass 4's rows
    # were not evicted, and the package legitimately grows with later orders.
    assert set(PASS4_PUBLISHED) <= set(facts)
    # ... and the one row a later founder ruling removed is genuinely gone,
    # with a withdrawal ledger that says why.
    assert PASS4_WITHDRAWN not in facts
    ledger = load(LP / "markets" / "reports"
                  / "pittsburgh_hold_resolution_005_withdrawn_authority.json")
    assert [r["identity_key"] for r in ledger["withdrawn_records"]] == [PASS4_WITHDRAWN]
    assert ledger["why"].strip()
    # It is now a registered REFUSAL, so it must never reappear as a profile.
    exclusions = load(LP / "markets" / "authority" / "pittsburgh-pa"
                      / "hotel_exclusions.json")["exclusions"]
    refused = {e["normalized_name"] for e in exclusions
               if e["exclusion_state"] == "VERIFIED_NO_PETS"}
    assert PASS4_WITHDRAWN in refused
    sonesta = facts["sonesta simply suites pittsburgh airport"]
    assert sonesta["facts"]["weight_limit_stated_none"] is True
    assert sonesta["facts"]["breed_restrictions_stated_none"] is True
    assert "species" not in sonesta["facts"]
    assert "basis" not in sonesta["facts"]["fee_tiers"][0]
    airport = facts["hyatt place pittsburgh airport"]
    assert "pet_fee" not in airport["facts"]
    assert airport["withheld_fields"]["pet_fee"]["reason_code"] == "SOURCE_AMBIGUOUS"
    north = facts["hyatt place pittsburgh north shore"]
    # refundable_stated added by PTF-PITTSBURGH-HARDENED-SYNC-004 Phase 5: the
    # source states the tier and the words "Cleaning fee" and never addresses
    # refundability. The assertion below still holds and is the point -- no
    # `refundable` boolean was invented.
    assert north["facts"]["other_charges"] == [{
        "kind": "cleaning_fee", "amount_cents": 10000, "currency": "USD",
        "conditional": True, "trigger": "7 - 30 nights",
        "refundable_stated": False}]
    assert "refundable" not in north["facts"]["other_charges"][0]
    joinery = facts["joinery hotel pittsburgh"]
    assert "pet_fee" not in joinery["facts"]
    assert joinery["withheld_fields"]["pet_fee"]["reason_code"] == "SOURCE_CONTRADICTORY"
    for key in PASS4_PUBLISHED:
        approval = facts[key]["approval"]
        assert approval["operator"] == "jfields80"
        assert approval["decision"] == "APPROVED_AFTER_CURRENT_REVIEW"
        assert approval["record_hash"] == record_hash(facts[key])
        assert approval["evidence_hash"] == evidence_hash(facts[key]["evidence"])


def test_application_report_and_packet_bind_exactly_ten_decisions():
    report = load(REPORTS / "pittsburgh_pass4_application_001_report.json")
    packet = load(REPORTS / "pittsburgh_pass4_claude_founder_review_packet.json")
    assert report["authority_before"] == {
        "published": 29, "verified_no_pets": 6, "out_of_category": 3, "unresolved": 58}
    assert report["authority_after"] == {
        "published": 37, "verified_no_pets": 8, "out_of_category": 3, "unresolved": 48}
    assert len(report["published_decisions"]) == 8
    assert len(report["exclusion_decisions"]) == 2
    assert packet["decisions_recorded"] == packet["decisions_applied"] == 10
    assert all(row["authority_application_status"] == "APPLIED" for row in packet["entries"])
