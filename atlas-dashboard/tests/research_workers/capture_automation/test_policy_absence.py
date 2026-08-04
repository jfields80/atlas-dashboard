"""Confirmed policy absence: only an affirmative refusal, never silence.

The rule these tests exist to hold: ``POLICY_ABSENT_CONFIRMED`` may be produced
ONLY by an affirmative, property-level statement on the official page. Every
form of silence -- no anchor, no pet text, no structured data, a missing
amenity, an absent fee, a brand default -- must leave POLICY_NOT_FOUND alone.
"""

import copy

from services.research_workers.capture_automation.manifest import Journal
from services.research_workers.capture_automation.policy_absence import (
    EVIDENCE_STRUCTURED_FALSE, EVIDENCE_VISIBLE_NO_PETS,
    EVIDENCE_VISIBLE_SERVICE_ANIMALS_ONLY, POLICY_ABSENT_CONFIRMED,
    assess_absence,
)
from services.research_workers.capture_automation.reasons import (
    EXCEPTION_REASONS, RETRY_NEVER, retry_for,
)


# -- affirmative refusals: these DO confirm ------------------------------- #

def test_structured_pets_allowed_false_confirms():
    v = assess_absence(jsonld=({"@type": "Hotel", "petsAllowed": False},))
    assert v.confirmed is True
    assert EVIDENCE_STRUCTURED_FALSE in v.evidence


def test_structured_false_inside_graph_confirms():
    v = assess_absence(jsonld=({"@graph": [{"@type": "Hotel", "petsAllowed": "false"}]},))
    assert v.confirmed is True


def test_visible_no_pets_allowed_confirms():
    v = assess_absence(visible_text="Hotel policies. No pets allowed. Check-in 3pm.")
    assert v.confirmed is True
    assert EVIDENCE_VISIBLE_NO_PETS in v.evidence
    assert v.quotes and "no pets allowed" in v.quotes[0].lower()


def test_visible_pets_are_not_permitted_confirms():
    v = assess_absence(visible_text="Please note that pets are not permitted at this hotel.")
    assert v.confirmed is True


def test_service_animals_only_confirms_absence_of_ordinary_pets():
    """"Service animals only" says ordinary pets are refused. It is never
    evidence that pets are accepted."""
    v = assess_absence(visible_text="Service animals only. We regret we cannot host pets.")
    assert v.confirmed is True
    assert EVIDENCE_VISIBLE_SERVICE_ANIMALS_ONLY in v.evidence


# -- silence: these must NEVER confirm ------------------------------------ #

def test_empty_page_never_confirms():
    v = assess_absence()
    assert v.confirmed is False
    assert "silence" in v.explanation


def test_no_pet_mention_anywhere_never_confirms():
    v = assess_absence(
        jsonld=({"@type": "Hotel", "name": "Somewhere Inn"},),
        visible_text="Rooms, dining, meetings, parking. Check-in 3pm, check-out 11am.")
    assert v.confirmed is False


def test_missing_pets_allowed_key_is_silence_not_refusal():
    v = assess_absence(jsonld=({"@type": "Hotel", "amenityFeature": ["Pool", "Gym"]},))
    assert v.confirmed is False


def test_absent_fee_is_not_a_refusal():
    v = assess_absence(visible_text="Resort fee: none. Parking: $20 per night.")
    assert v.confirmed is False


def test_unparseable_structured_value_is_silence():
    v = assess_absence(jsonld=({"@type": "Hotel", "petsAllowed": "call the hotel"},))
    assert v.confirmed is False


# -- ambiguity: the page contradicts itself, so nothing is confirmed ------ #

def test_pet_friendly_page_with_area_restriction_never_confirms():
    """"Pets are not allowed in the pool area" describes a pet-friendly hotel."""
    v = assess_absence(
        visible_text="We are pet friendly! Pets are not allowed in the pool area.")
    assert v.confirmed is False
    assert "ambiguous" in v.explanation


def test_structured_true_outranks_negative_prose():
    v = assess_absence(jsonld=({"@type": "Hotel", "petsAllowed": True},),
                       visible_text="No pets allowed in the restaurant.")
    assert v.confirmed is False
    assert "petsAllowed: true" in v.explanation


# -- the reason is registered and terminal -------------------------------- #

def test_reason_is_registered_as_never_retry():
    assert POLICY_ABSENT_CONFIRMED in EXCEPTION_REASONS
    assert retry_for(POLICY_ABSENT_CONFIRMED) == RETRY_NEVER


def test_verdict_carries_non_authoritative_labels():
    """A classification is not a policy fact, and says so on its face."""
    d = assess_absence(visible_text="No pets allowed.").to_dict()
    assert d["non_authoritative"] is True
    assert d["not_for_extraction"] is True


# -- through the runner, end to end --------------------------------------- #

FIXTURE = "marriott-cmham.json"
#: The fixture's real pet block, which the no-pets pages below replace.
PET_BLOCK = ("Pet Policy\n\nPets Welcome\n\nWe love pets and welcome them, just "
             "as we welcome you.\n\nNon-Refundable Pet Fee Per Stay: $75.00\n\n"
             "Maximum Number of Pets in Room: 2\n")


def _page(replacement: str, *, pets_allowed=None) -> dict:
    """One real property page with its pet block swapped for ``replacement``.

    This models the production shape exactly: a hotel that takes no pets has no
    pet policy on the page to find, so the locator returns nothing and the
    affirmative refusal lives in the structured data or in a plain sentence.
    """
    from .conftest import load_fixture
    payload = copy.deepcopy(load_fixture(FIXTURE))
    assert PET_BLOCK in payload["text"], "fixture drifted; update PET_BLOCK"
    payload["text"] = payload["text"].replace(PET_BLOCK, replacement)
    if pets_allowed is not None:
        blocks = [copy.deepcopy(b) for b in payload["jsonld"]]
        for block in blocks:
            if str(block.get("@type", "")).lower() in ("hotel", "lodgingbusiness"):
                block["petsAllowed"] = pets_allowed
                break
        payload["jsonld"] = blocks
    return payload


def _run(tmp_path, payload) -> dict:
    from services.research_workers.capture_automation.queue import CaptureQueue
    from services.research_workers.capture_automation.runner import (
        CaptureRunner, RunnerConfig,
    )
    from .conftest import FakeBrowserSession, entry_for

    class Clock:
        t = 1_781_000_000.0

        def __call__(self):
            Clock.t += 0.5
            return Clock.t

    session = FakeBrowserSession({payload["final_url"]: payload})
    runner = CaptureRunner(session, RunnerConfig(batch_dir=tmp_path / "batch"),
                           clock=Clock(), sleep=lambda s: None,
                           jitter=lambda a, b: a)
    return runner.run(CaptureQueue(batch_id="absence",
                                   entries=(entry_for(FIXTURE),))).manifest


def test_runner_reports_absence_instead_of_not_found(tmp_path):
    """The production shape: no pet block on the page, petsAllowed false."""
    manifest = _run(tmp_path, _page("Front Desk\n\nOpen 24 hours.\n",
                                    pets_allowed=False))
    assert [e["reason"] for e in manifest["exceptions"]] == [POLICY_ABSENT_CONFIRMED]
    assert manifest["counts"]["confirmed_policy_absence"] == 1


def test_a_locatable_negative_statement_is_still_captured(tmp_path):
    """Classification never displaces a capture.

    When the page DOES carry a findable pet-policy block -- even one that says
    no -- the locator finds it and the runner photographs it, exactly as
    before. Absence is only ever consulted where a capture was impossible.
    """
    manifest = _run(tmp_path, _page("Pet Policy\n\nNo pets allowed.\n",
                                    pets_allowed=False))
    assert manifest["counts"]["captured"] == 1
    assert manifest["counts"]["confirmed_policy_absence"] == 0


def test_runner_keeps_policy_not_found_when_nothing_affirms(tmp_path):
    """A page that simply says nothing about pets is still a miss."""
    manifest = _run(tmp_path, _page("Front Desk\n\nOpen 24 hours.\n"))
    assert [e["reason"] for e in manifest["exceptions"]] == ["POLICY_NOT_FOUND"]
    assert manifest["counts"]["confirmed_policy_absence"] == 0


def test_absence_produces_no_capture_and_no_policy_fact(tmp_path):
    """It is a classification of a failure, not evidence of anything."""
    manifest = _run(tmp_path, _page("Front Desk\n\nOpen 24 hours.\n",
                                    pets_allowed=False))
    assert manifest["counts"]["captured"] == 0
    assert manifest["successful_captures"] == []
    entry = manifest["confirmed_policy_absence"][0]
    assert entry["non_authoritative"] is True
    assert entry["not_for_extraction"] is True
    assert any(d.startswith("absence_evidence:") for d in entry["detail"])


def test_absence_is_reported_separately_from_ordinary_failures(tmp_path):
    """The count exists so nine correct results stop reading as nine defects."""
    manifest = _run(tmp_path, _page("Front Desk\n\nOpen 24 hours.\n",
                                    pets_allowed=False))
    counts = manifest["counts"]
    # A subset of exceptions, not a fourth total -- no capture was produced.
    assert counts["exceptions"] == 1
    assert counts["confirmed_policy_absence"] == 1
    assert "POLICY_NOT_FOUND" not in manifest["exceptions_by_reason"]


def test_a_confirmed_absence_is_never_skipped_on_resume(tmp_path):
    """No capture exists, so the hotel is re-attempted like any other failure.

    Classification tells the operator what happened; it never grants a hotel
    the standing of a completed capture.
    """
    _run(tmp_path, _page("Front Desk\n\nOpen 24 hours.\n", pets_allowed=False))
    journal = Journal.open(tmp_path / "batch")
    absent = journal.confirmed_absent_ids()
    assert absent == ("marriott-cmham",)
    assert absent[0] not in journal.completed_capture_ids()
    assert absent[0] in journal.incomplete_hotel_ids()
