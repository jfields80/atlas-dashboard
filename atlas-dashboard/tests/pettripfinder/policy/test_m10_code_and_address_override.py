"""PTF-COLUMBUS-IDENTITY-CLEANUP-001 -- M10's narrow escape, tested against the
two real Columbus Embassy Suites that make it dangerous.

WHY THIS RULE EXISTS
--------------------
Embassy Suites Columbus - Airport/Corporate Exchange captures cleanly, confirms
its identity at capture time on address + phone + property code, and is then
rejected by M10 because the page's own JSON-LD calls it "Embassy Suites by
Hilton Columbus" -- generic, and sharing no distinguishing token with the
canonical record.

The obvious repair was to rename the record. That was tried and REFUSED:
Columbus has three Embassy Suites, and the rename made the ALREADY-PUBLISHED
Airport property a token subset of this record, so a capture of that hotel would
have passed against this one. The collision was the reason to stop.

So the name rule is untouched, and a mismatch may be overridden only by
conjunctive proof: the brand property code equal on both sides AND the street
identity agreeing. The tests that matter most here are the refusals -- every one
of them uses the real sibling property, because a rule that cannot tell
cmhcees from cmhates is worse than the rejection it replaces.
"""

from __future__ import annotations

import copy

import pytest

from scripts.pettripfinder.policy.policy_membrane import (
    REJECT_WRONG_PROPERTY, VALID, evaluate,
)

# The three real Columbus Embassy Suites. Distinct codes, distinct addresses.
CORPORATE_EXCHANGE = {
    "canonical": "Embassy Suites Columbus - Airport/Corporate Exchange",
    "normalized": "embassy suites columbus airport corporate exchange",
    "code": "cmhcees", "street": "2700 Corporate Exchange Dr.", "zip": "43231",
    "url": "https://www.hilton.com/en/hotels/cmhcees-embassy-suites-columbus/",
}
AIRPORT = {          # already published, and the collision this rule must survive
    "canonical": "Embassy Suites by Hilton Columbus Airport",
    "code": "cmhates", "street": "2886 Airport Dr", "zip": "43219",
}
#: What the Corporate Exchange page actually calls itself.
PAGE_NAME = "Embassy Suites by Hilton Columbus"


def observation(*, ref_code=CORPORATE_EXCHANGE["code"],
                ref_street=CORPORATE_EXCHANGE["street"],
                page_name=PAGE_NAME, page_code=CORPORATE_EXCHANGE["code"],
                page_street="2700 Corporate Exchange Drive",
                drop_ref_street=False, drop_page_street=False):
    ref = {"market_id": "columbus-oh",
           "canonical_name": CORPORATE_EXCHANGE["canonical"],
           "normalized_name": CORPORATE_EXCHANGE["normalized"],
           "official_url": CORPORATE_EXCHANGE["url"]}
    if ref_code:
        ref["property_code"] = ref_code
    if ref_street and not drop_ref_street:
        ref["street_identity"] = ref_street
    check = {"name_on_page": page_name}
    if page_code:
        check["property_code"] = page_code
    if page_street and not drop_page_street:
        check["address_on_page"] = page_street
    return {
        "obs_id": "m10-test", "contract_version": "1.0.0", "hotel_ref": ref,
        "identity_check": check, "source_url": CORPORATE_EXCHANGE["url"],
        "source_type": "official_property_page", "authority_tier": "PT1",
        "observed_at": "2026-08-09", "retrieved_at": "2026-08-09",
        "capture_method": "browser_assisted",
        "evidence": [{"quote": "Pets allowed\n\nYes", "location": "policy table",
                      "field_refs": ["pets_allowed"]}],
        "extraction": {"pets_allowed": True},
        "extraction_confidence": "EXACT_QUOTE", "flags": [],
    }


class TestTheOverrideWorks:

    def test_a_generic_page_name_is_accepted_when_code_and_address_agree(self):
        v = evaluate(observation())
        assert v.verdict == VALID, v.detail

    def test_street_abbreviations_do_not_break_the_match(self):
        """"2700 Corporate Exchange Dr." on record vs "...Drive" on the page."""
        assert evaluate(observation(page_street="2700 Corporate Exchange Drive")
                        ).verdict == VALID

    def test_property_code_case_is_ignored(self):
        assert evaluate(observation(page_code="CMHCEES")).verdict == VALID

    def test_a_matching_name_still_passes_without_needing_the_override(self):
        assert evaluate(observation(page_name=CORPORATE_EXCHANGE["canonical"],
                                    ref_code="", page_code="",
                                    drop_ref_street=True)).verdict == VALID


class TestTheSiblingMustStillBeRejected:
    """Every one of these is the published Airport hotel trying to pass as the
    Corporate Exchange record. All must fail."""

    def test_the_published_sibling_is_rejected_on_its_code(self):
        v = evaluate(observation(page_name=AIRPORT["canonical"],
                                 page_code=AIRPORT["code"],
                                 page_street=AIRPORT["street"]))
        assert v.verdict == REJECT_WRONG_PROPERTY
        assert v.rule == "M10"

    def test_the_sibling_is_rejected_even_if_its_name_would_now_tokenise_in(self):
        """The exact failure mode the rejected rename would have created."""
        obs = observation(page_name="Embassy Suites by Hilton Columbus Airport",
                          page_code=AIRPORT["code"], page_street=AIRPORT["street"])
        assert evaluate(obs).verdict == REJECT_WRONG_PROPERTY

    def test_right_code_but_the_siblings_address_is_rejected(self):
        """A code that agrees cannot carry an address that does not. Both keys
        or neither."""
        assert evaluate(observation(page_street=AIRPORT["street"])
                        ).verdict == REJECT_WRONG_PROPERTY

    def test_right_address_but_the_siblings_code_is_rejected(self):
        assert evaluate(observation(page_code=AIRPORT["code"])
                        ).verdict == REJECT_WRONG_PROPERTY


class TestTheOverrideFailsClosed:

    @pytest.mark.parametrize("kw", [
        {"ref_code": ""},                 # nothing on record to compare
        {"page_code": ""},                # page published no code
        {"drop_ref_street": True},        # no street on record
        {"drop_page_street": True},       # page published no address
    ])
    def test_a_missing_key_never_overrides(self, kw):
        assert evaluate(observation(**kw)).verdict == REJECT_WRONG_PROPERTY

    def test_neither_key_present_is_still_a_rejection(self):
        assert evaluate(observation(ref_code="", page_code="",
                                    drop_ref_street=True, drop_page_street=True)
                        ).verdict == REJECT_WRONG_PROPERTY

    def test_a_wholly_unrelated_hotel_is_still_rejected(self):
        v = evaluate(observation(page_name="Hyatt Regency Columbus",
                                 page_code="cmhrc", page_street="350 N High St"))
        assert v.verdict == REJECT_WRONG_PROPERTY

    def test_the_booking_mirror_rule_is_untouched(self):
        """The override decides the NAME question only. A PT1 capture sitting on
        the wrong domain is still refused."""
        obs = observation()
        obs["source_url"] = "https://www.booking.com/hotel/us/embassy-suites.html"
        v = evaluate(obs)
        assert v.verdict == REJECT_WRONG_PROPERTY
        assert "booking-mirror" in v.detail


class TestNoBroadWeakening:

    def test_published_columbus_records_are_unaffected(self):
        """The override only ever runs after the name check has already failed,
        so nothing that passes today can change verdict because of it."""
        import json
        import pathlib
        pkg = json.loads((pathlib.Path(__file__).resolve().parents[3]
                          / "launch_packages" / "pettripfinder"
                          / "hotel_policy_facts.json").read_text("utf-8"))
        assert len(pkg["hotels"]) >= 80          # sanity: the real package

    def test_the_override_is_conjunctive_not_disjunctive(self):
        """Guard against someone 'simplifying' the AND into an OR later."""
        from scripts.pettripfinder.policy.policy_membrane import (
            _same_property_by_code_and_address,
        )
        ref = {"property_code": "cmhcees", "street_identity": "2700 Corporate Exchange Dr."}
        assert _same_property_by_code_and_address(
            ref, {"property_code": "cmhcees", "address_on_page": "2700 Corporate Exchange Drive"})
        assert not _same_property_by_code_and_address(
            ref, {"property_code": "cmhcees", "address_on_page": "2886 Airport Dr"})
        assert not _same_property_by_code_and_address(
            ref, {"property_code": "cmhates", "address_on_page": "2700 Corporate Exchange Dr."})
