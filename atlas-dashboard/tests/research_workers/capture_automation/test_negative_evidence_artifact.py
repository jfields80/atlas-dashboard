"""PTF-NEGATIVE-EVIDENCE-P0-001 -- an affirmative no-pets page must leave a
citable artifact, exactly like a page that says yes.

THE DEFECT THESE TESTS PIN
--------------------------
``POLICY_ABSENT_CONFIRMED`` is a correct, valuable answer: the official page
says this hotel does not take pets. But the runner returned it while writing no
files at all, so the only surviving trace was a journal string. ``hotel_exclusions``
requires a ``source_hash`` for every evidence-backed state, and a claim about a
page cannot be hashed into a citation of it -- so five Columbus hotels holding
affirmative denials could not be applied.

The fix persists the page the way the positive path does. What it must NOT do is
make the classification any easier to reach, and most of the tests below are
about that: silence, a brand page, a wrong property, and a challenge page must
all still produce nothing.

The outcome is deliberately unchanged. These records stay EXCEPTION /
POLICY_ABSENT_CONFIRMED, non-authoritative and not-for-extraction. The change is
in what is RETAINED, not in what is DECIDED.
"""

from __future__ import annotations

import copy
import json
import pathlib

import pytest

from services.research_workers.capture_automation.policy_absence import (
    POLICY_ABSENT_CONFIRMED,
)

from .conftest import FakeBrowserSession, entry_for, load_fixture

FIXTURE = "marriott-cmham.json"
PET_BLOCK = ("Pet Policy\n\nPets Welcome\n\nWe love pets and welcome them, just "
             "as we welcome you.\n\nNon-Refundable Pet Fee Per Stay: $75.00\n\n"
             "Maximum Number of Pets in Room: 2\n")


def _page(replacement: str, *, pets_allowed=None) -> dict:
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


def _run(tmp_path, payload, *, entry_overrides=None, session_kwargs=None):
    from services.research_workers.capture_automation.queue import CaptureQueue
    from services.research_workers.capture_automation.runner import (
        CaptureRunner, RunnerConfig,
    )

    class Clock:
        t = 1_781_000_000.0

        def __call__(self):
            Clock.t += 0.5
            return Clock.t

    session = FakeBrowserSession({payload["final_url"]: payload},
                                 **(session_kwargs or {}))
    runner = CaptureRunner(session, RunnerConfig(batch_dir=tmp_path / "batch"),
                           clock=Clock(), sleep=lambda s: None,
                           jitter=lambda a, b: a)
    entry = entry_for(FIXTURE, **(entry_overrides or {}))
    result = runner.run(CaptureQueue(batch_id="neg", entries=(entry,)))
    return result.manifest, result.outcomes[0]


def _absence_artifacts(outcome):
    assert outcome.reason == POLICY_ABSENT_CONFIRMED, outcome.reason
    assert outcome.artifacts, "no artifacts persisted for a confirmed absence"
    return outcome.artifacts


# --------------------------------------------------------------------------- #
# A / B -- the affirmative cases now produce citable evidence.
# --------------------------------------------------------------------------- #

class TestAffirmativeDenialProducesEvidence:

    def test_structured_pets_allowed_false_yields_a_citable_artifact(self, tmp_path):
        manifest, outcome = _run(tmp_path, _page("Front Desk\n\nOpen 24 hours.\n",
                                                 pets_allowed=False))
        art = _absence_artifacts(outcome)
        assert pathlib.Path(art["json_path"]).is_file()
        assert pathlib.Path(art["png_path"]).is_file()
        assert art["html_sha256"] and art["text_sha256"] and art["png_sha256"]
        assert art["citable_url"]
        assert art["negative_evidence"] is True

    def test_the_artifact_carries_the_exact_quote_and_its_basis(self, tmp_path):
        _, outcome = _run(tmp_path, _page(
            "Pets\n\nNo pets allowed at this hotel.\n"))
        art = _absence_artifacts(outcome)
        assert art["absence_quote"], "the affirmative sentence must be retained"
        assert "no pets allowed" in art["absence_quote"].lower()
        assert art["absence_evidence"]

    def test_the_quote_is_present_in_the_persisted_page_text(self, tmp_path):
        """Provenance: the quote must be findable IN the artifact it cites, not
        merely stored beside it."""
        _, outcome = _run(tmp_path, _page(
            "Pets\n\nNo pets allowed at this hotel.\n"))
        art = _absence_artifacts(outcome)
        payload = json.loads(pathlib.Path(art["json_path"]).read_text("utf-8"))
        assert "No pets allowed at this hotel." in payload["text"]

    def test_identity_is_recorded_on_the_artifact(self, tmp_path):
        _, outcome = _run(tmp_path, _page("Front Desk\n\nOpen 24 hours.\n",
                                          pets_allowed=False))
        art = _absence_artifacts(outcome)
        assert art["identity"]["outcome"] == "IDENTITY_CONFIRMED"

    def test_service_animals_only_is_affirmative_evidence(self, tmp_path):
        """"Service animals only" denies ordinary pets. It is accepted only
        because identity passed first -- see the wrong-property test below."""
        _, outcome = _run(tmp_path, _page(
            "Pets\n\nOnly service animals are permitted, free of charge.\n"))
        art = _absence_artifacts(outcome)
        assert art["absence_quote"]
        assert pathlib.Path(art["json_path"]).is_file()


# --------------------------------------------------------------------------- #
# C / D / E / F -- everything that must still produce NOTHING.
# --------------------------------------------------------------------------- #

class TestSilenceAndDoubtProduceNoEvidence:

    def test_a_page_with_no_pet_section_writes_no_negative_artifact(self, tmp_path):
        """Missing text is not evidence. This is the rule the whole feature
        rests on and it must never soften."""
        manifest, outcome = _run(tmp_path, _page("Front Desk\n\nOpen 24 hours.\n"))
        assert outcome.reason == "POLICY_NOT_FOUND"
        assert not (outcome.artifacts or {}).get("negative_evidence")
        assert manifest["counts"]["confirmed_policy_absence"] == 0

    def test_a_pet_friendly_page_never_produces_negative_evidence(self, tmp_path):
        manifest, outcome = _run(tmp_path, _page(
            "Pet Policy\n\nPets Welcome\n\nMaximum Number of Pets in Room: 2\n"))
        assert outcome.reason != POLICY_ABSENT_CONFIRMED

    def test_structured_true_outranks_negative_prose(self, tmp_path):
        _, outcome = _run(tmp_path, _page(
            "Front Desk\n\nNo pets allowed in the breakfast area.\n",
            pets_allowed=True))
        assert outcome.reason != POLICY_ABSENT_CONFIRMED

    def test_a_wrong_property_page_produces_no_negative_evidence(self, tmp_path):
        """Identity is classified BEFORE the policy scan and only
        IDENTITY_CONFIRMED continues, so a page about a different hotel cannot
        reach the absence branch at all."""
        _, outcome = _run(
            tmp_path, _page("Front Desk\n\nOpen 24 hours.\n", pets_allowed=False),
            entry_overrides={"expected_address": "999 Nowhere Road",
                             "expected_phone": "555-000-0000",
                             "expected_property_code": "zzzzz"})
        assert outcome.reason != POLICY_ABSENT_CONFIRMED
        assert not (outcome.artifacts or {}).get("negative_evidence")

    def test_a_challenge_page_produces_no_negative_evidence(self, tmp_path):
        """A bot wall that happens to contain a denial-shaped sentence must not
        become a hotel's pet policy."""
        payload = _page("Front Desk\n\nOpen 24 hours.\n", pets_allowed=False)
        payload["text"] = ("Access Denied\n\nYou don't have permission to access "
                           "this resource.\n" * 20)
        _, outcome = _run(tmp_path, payload)
        assert outcome.reason != POLICY_ABSENT_CONFIRMED
        assert not (outcome.artifacts or {}).get("negative_evidence")


# --------------------------------------------------------------------------- #
# G / H -- the positive path, and hash determinism.
# --------------------------------------------------------------------------- #

class TestPositivePathAndHashes:

    def test_a_locatable_policy_is_still_an_ordinary_capture(self, tmp_path):
        """Unchanged: a findable block -- even one that says no -- is captured
        and framed exactly as before, and is NOT a negative-evidence record."""
        manifest, outcome = _run(tmp_path, _page("Pet Policy\n\nNo pets allowed.\n",
                                                 pets_allowed=False))
        assert manifest["counts"]["captured"] == 1
        assert manifest["counts"]["confirmed_policy_absence"] == 0
        assert not (outcome.artifacts or {}).get("negative_evidence")

    def test_source_hash_is_deterministic_over_the_persisted_artifact(self, tmp_path):
        import hashlib
        _, outcome = _run(tmp_path, _page("Front Desk\n\nOpen 24 hours.\n",
                                          pets_allowed=False))
        art = _absence_artifacts(outcome)
        payload = json.loads(pathlib.Path(art["json_path"]).read_text("utf-8"))
        assert art["text_sha256"] == hashlib.sha256(
            payload["text"].encode("utf-8")).hexdigest()
        assert art["html_sha256"] == hashlib.sha256(
            payload["html"].encode("utf-8")).hexdigest()

    def test_the_record_stays_non_authoritative(self, tmp_path):
        """Retaining a page is not promoting it. The exclusion authority still
        decides, and a human still approves."""
        manifest, outcome = _run(tmp_path, _page("Front Desk\n\nOpen 24 hours.\n",
                                                 pets_allowed=False))
        assert outcome.state == "EXCEPTION"
        assert manifest["counts"]["captured"] == 0
        assert manifest["successful_captures"] == []
        entry = manifest["confirmed_policy_absence"][0]
        assert entry["non_authoritative"] is True
        assert entry["not_for_extraction"] is True


# --------------------------------------------------------------------------- #
# I -- the exclusion contract accepts it, and only on its own terms.
# --------------------------------------------------------------------------- #

class TestExclusionContractAcceptance:

    def _record(self, art):
        from scripts.pettripfinder import hotel_exclusions as HE
        rec = {
            "canonical_name": "Test Hotel Columbus", "address": "1 Test St",
            "city": "Columbus", "state": "OH", "postal_code": "43215",
            "phone": "614-555-0100", "official_url": art["citable_url"],
            "exclusion_state": HE.VERIFIED_NO_PETS,
            "evidence_quote": art["absence_quote"],
            "source_url": art["citable_url"], "observed_at": "2026-08-09",
            "reviewer_id": "tester", "reviewed_at": "2026-08-09T12:00:00-04:00",
            "exclusion_id": "excl-test-hotel-columbus",
            "normalized_name": "test hotel columbus",
            "source_hash": "sha256:%s" % art["html_sha256"],
        }
        rec["record_hash"] = HE.record_hash(rec)
        rec["approval_hash"] = HE.approval_hash(rec)
        return rec

    def test_the_artifact_satisfies_every_required_exclusion_field(self, tmp_path):
        from scripts.pettripfinder import hotel_exclusions as HE
        _, outcome = _run(tmp_path, _page(
            "Pets\n\nNo pets allowed at this hotel.\n"))
        rec = self._record(_absence_artifacts(outcome))
        assert [f for f in HE.REQUIRED_FIELDS if not rec.get(f)] == []
        HE.validate({"schema": HE.SCHEMA, "contract": HE.SCHEMA,
                     "market": "columbus-oh", "note": "t", "exclusions": [rec]})

    def test_a_record_without_the_source_hash_is_still_refused(self, tmp_path):
        """The exact failure this work order exists to remove -- it must remain
        a failure for anything that genuinely lacks the artifact."""
        from scripts.pettripfinder import hotel_exclusions as HE
        _, outcome = _run(tmp_path, _page(
            "Pets\n\nNo pets allowed at this hotel.\n"))
        rec = self._record(_absence_artifacts(outcome))
        rec["source_hash"] = ""
        with pytest.raises(HE.ExclusionContractError):
            HE.validate({"schema": HE.SCHEMA, "contract": HE.SCHEMA,
                         "market": "columbus-oh", "note": "t", "exclusions": [rec]})
