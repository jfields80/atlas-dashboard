"""A modal trigger reports success the same way an accordion button does.

Three Wyndham hotels reported POLICY_NOT_FOUND in the verification run while
their "Hotel Policies" lightbox sat closed with the pet policy inside it. The
click really was dispatched -- ``performed: True`` -- and the preserved DOM
shows ``<div class="modal fade" id="hotelPoliciesLightbox">``: Bootstrap's
HIDDEN state, no ``show``/``in`` class, no ``modal-backdrop``, no ``modal-open``
on ``<body>``.

That is the Expo Center defect in a second dialect. The existing verification
only read ``aria-expanded`` on the control, a Bootstrap trigger carries none, so
``_expanded_state`` returned ``None``, ``None`` means "not observable", and the
check was skipped entirely.

What must NOT change: the hidden text is still worthless. A page that will not
open stays POLICY_NOT_FOUND, because a capture whose screenshot cannot show what
its text claims is worse than no capture at all.
"""

from __future__ import annotations

import json
import pathlib
from typing import Dict, List, Optional

from services.research_workers.capture_automation.queue import CaptureQueue, QueueEntry
from services.research_workers.capture_automation.runner import (
    CaptureRunner, RunnerConfig,
)

from .conftest import FakeBrowserSession

URL = ("https://www.wyndhamhotels.com/hawthorn-extended-stay/columbus-ohio/"
       "hawthorn-extended-stay-columbus-north/overview")

#: Verbatim from the preserved failure diagnostic of the real run.
PET_POLICY = ("Pet & Service Animal Policy A maximum of 2 pets are allowed for a "
              "non-refundable charge of 35.00 USD per pet for the first night and "
              "15.00 USD per pet for each additional night per stay. ADA-defined "
              "service animals are also welcome at this hotel.")

BASE_TEXT = ("Hawthorn Extended Stay by Wyndham Columbus North\n"
             "1289 E Dublin Granville Rd\nColumbus, OH 43229\n614-846-0300\n"
             "Hotel Policies\nCheck In 3:00 p.m.\nCheck Out 11:00 a.m.\n")

#: The modal is in the HTML in BOTH states -- that is the whole point. Only its
#: shown-ness, and therefore its presence in innerText, differs.
MODAL_HTML = (
    '<a data-target="#hotelPoliciesLightbox" href="#">Hotel Policies</a>'
    '<div class="modal fade" id="hotelPoliciesLightbox" tabindex="-1" '
    'role="dialog"><div class="modal-body">%s</div></div>' % PET_POLICY)


def _payload(*, opened: bool) -> dict:
    """One Wyndham page, modelled honestly.

    ``text`` is ``document.body.innerText``: a hidden dialog does not appear in
    it. ``html`` carries the policy either way, because it really is in the DOM.
    """
    return {
        "schema": "ptf-official-capture/1.0",
        "captured_at": "2026-08-03T21:00:00-04:00",
        "final_url": URL,
        "title": "Hawthorn Extended Stay by Wyndham Columbus North",
        "html": MODAL_HTML,
        "text": BASE_TEXT + (PET_POLICY if opened else ""),
        "jsonld": [{"@type": "Hotel",
                    "name": "Hawthorn Extended Stay by Wyndham Columbus North",
                    "telephone": "614-846-0300",
                    "address": {"@type": "PostalAddress",
                                "streetAddress": "1289 E Dublin Granville Rd",
                                "addressLocality": "Columbus",
                                "addressRegion": "OH", "postalCode": "43229"}}],
        "extension_version": "1.0.0",
    }


def _entry() -> QueueEntry:
    return QueueEntry(
        hotel_id="hawthorn-extended-stay-columbus-north",
        listing_key="hawthorn extended stay by wyndham columbus north",
        hotel_name="Hawthorn Extended Stay by Wyndham Columbus North",
        brand="wyndham", official_url=URL,
        expected_address="1289 E Dublin Granville Rd", expected_city="Columbus",
        expected_state="OH", expected_postal_code="43229",
        expected_phone="614-846-0300")


class ModalSession(FakeBrowserSession):
    """A lightbox that opens on the Nth click -- or never.

    ``click_text`` always returns True, exactly as the real driver did: it found
    the anchor and dispatched the click. Whether the dialog opened is a separate
    question, and answering it is the point of the fix.
    """

    def __init__(self, *, opens_on_click: int):
        super().__init__({URL: _payload(opened=False)})
        self._opens_on = opens_on_click
        self.click_text_calls: List[str] = []
        self.is_open = False
        self.evaluations: List[str] = []

    def click_text(self, selector: str, text: str) -> bool:
        self.click_text_calls.append(text)
        if self._opens_on and len(self.click_text_calls) >= self._opens_on:
            self.is_open = True
            self.pages[URL] = _payload(opened=True)
        return True

    def evaluate(self, expression: str, timeout: float = 60.0):
        self.evaluations.append(expression)
        if "scrollTo" in expression:
            return 0
        # The real expression asks the browser about the TARGET's rendered
        # state. Offline, the session answers for it.
        if "data-bs-target" in expression or "aria-expanded" in expression:
            return self.is_open
        return None


def _run(tmp_path, session) -> dict:
    class Clock:
        t = 1_781_000_000.0

        def __call__(self):
            Clock.t += 0.5
            return Clock.t

    runner = CaptureRunner(session, RunnerConfig(batch_dir=tmp_path / "batch"),
                           clock=Clock(), sleep=lambda s: None,
                           jitter=lambda a, b: a)
    return runner.run(CaptureQueue(batch_id="modal", entries=(_entry(),))).manifest


def _interaction_log(batch_dir: pathlib.Path) -> List[dict]:
    for path in sorted((batch_dir / "captures").glob("*.json")):
        if path.name.endswith(".view.json"):
            continue
        payload = json.loads(path.read_text("utf-8"))
        return (payload.get("automation") or {}).get("interaction_log") or []
    return []


# --------------------------------------------------------------------------- #
# The four required behaviours.
# --------------------------------------------------------------------------- #

class TestModalVerification:
    def test_modal_opens_on_first_click(self, tmp_path):
        session = ModalSession(opens_on_click=1)
        manifest = _run(tmp_path, session)
        assert manifest["counts"]["captured"] == 1
        assert len(session.click_text_calls) == 1, "no re-click when it opened"
        log = _interaction_log(tmp_path / "batch")
        clicks = [s for s in log if s.get("action") == "click_text"]
        assert clicks and clicks[0]["expanded"] is True
        assert not clicks[0].get("reclicked")

    def test_first_click_reports_success_but_modal_stays_closed_second_opens(self, tmp_path):
        """The exact Wyndham shape: performed=True, dialog still hidden."""
        session = ModalSession(opens_on_click=2)
        manifest = _run(tmp_path, session)
        assert manifest["counts"]["captured"] == 1
        assert len(session.click_text_calls) == 2, "exactly one re-click"
        log = _interaction_log(tmp_path / "batch")
        clicks = [s for s in log if s.get("action") == "click_text"]
        assert clicks[0]["reclicked"] is True
        assert clicks[0]["expanded"] is True

    def test_both_clicks_fail_and_policy_not_found_is_preserved(self, tmp_path):
        session = ModalSession(opens_on_click=0)          # never opens
        manifest = _run(tmp_path, session)
        assert manifest["counts"]["captured"] == 0
        assert [e["reason"] for e in manifest["exceptions"]] == ["POLICY_NOT_FOUND"]
        assert len(session.click_text_calls) == 2, "never more than one re-click"

    def test_hidden_modal_text_is_never_accepted_as_evidence(self, tmp_path):
        """The policy is in the HTML the whole time. It must not be read."""
        session = ModalSession(opens_on_click=0)
        manifest = _run(tmp_path, session)
        assert manifest["counts"]["captured"] == 0
        assert manifest["successful_captures"] == []
        # And it did not slip out as a confirmed absence either -- the page
        # never affirmatively refused pets, it just never opened.
        assert manifest["counts"].get("confirmed_policy_absence", 0) == 0
        assert PET_POLICY in session.pages[URL]["html"], "precondition: text was there"
        assert PET_POLICY not in session.pages[URL]["text"], "and never rendered"


class TestTheReclickOnlyFiresWhereItIsNeeded:
    """La Quinta is why this condition exists.

    Its expansion state reads false -- the Wyndham lightbox does not open under
    automation on any of its properties -- but its policy is rendered on the
    page regardless. Re-clicking a page that did not need it turned a working
    capture into POLICY_NOT_FOUND, measured: the positive-regression set fell
    from 5/5 to 4/5. The remedy now only runs where there is something to remedy.
    """

    class VisiblePolicySession(ModalSession):
        """Expansion never confirms, and the policy is visible anyway."""

        def __init__(self):
            super().__init__(opens_on_click=0)
            self.pages[URL] = _payload(opened=True)     # policy in innerText

    def test_la_quinta_no_reclick_and_the_capture_succeeds(self, tmp_path):
        session = self.VisiblePolicySession()
        manifest = _run(tmp_path, session)
        assert manifest["counts"]["captured"] == 1, "the working capture survives"
        assert len(session.click_text_calls) == 1, "exactly one click, no remedy"
        log = _interaction_log(tmp_path / "batch")
        clicks = [s for s in log if s.get("action") == "click_text"]
        assert clicks[0]["expanded"] is False, "state stays honestly unconfirmed"
        assert not clicks[0].get("reclicked")

    def test_the_unconfirmed_state_is_still_recorded(self, tmp_path):
        """'We could not prove it opened, and it did not matter' is worth
        reading -- the finding is not silently discarded."""
        session = self.VisiblePolicySession()
        _run(tmp_path, session)
        clicks = [s for s in _interaction_log(tmp_path / "batch")
                  if s.get("action") == "click_text"]
        assert clicks[0]["policy_visible_without_expansion"] is True

    def test_the_hidden_modal_still_gets_its_one_reclick(self, tmp_path):
        """The other side of the condition: nothing visible, so remedy fires."""
        session = ModalSession(opens_on_click=0)        # policy only in HTML
        manifest = _run(tmp_path, session)
        assert manifest["counts"]["captured"] == 0
        assert [e["reason"] for e in manifest["exceptions"]] == ["POLICY_NOT_FOUND"]
        assert len(session.click_text_calls) == 2, "one bounded re-click"

    def test_a_reclick_that_reveals_the_policy_is_recorded(self, tmp_path):
        session = ModalSession(opens_on_click=2)
        _run(tmp_path, session)
        clicks = [s for s in _interaction_log(tmp_path / "batch")
                  if s.get("action") == "click_text"]
        assert clicks[0]["reclicked"] is True
        assert clicks[0]["policy_visible_after_reclick"] is True

    def test_visibility_is_the_ordinary_locator_on_rendered_text(self, tmp_path):
        """Hidden text can never satisfy the condition, because the locator
        reads innerText and a display:none dialog is not in it."""
        session = ModalSession(opens_on_click=0)
        _run(tmp_path, session)
        page = session.pages[URL]
        assert PET_POLICY in page["html"], "the policy really is in the DOM"
        assert PET_POLICY not in page["text"], "and never rendered"
        # Which is why the remedy fired rather than the capture proceeding.
        assert len(session.click_text_calls) == 2


class TestModalStateLogicIsObservableOnly:
    """The verification may consult rendered STATE, never the target's text."""

    def _expression(self, tmp_path) -> str:
        session = ModalSession(opens_on_click=1)
        _run(tmp_path, session)
        state = [e for e in session.evaluations if "data-bs-target" in e]
        assert state, "the modal branch must be reached"
        return state[0]

    def test_it_reads_both_target_attributes(self, tmp_path):
        expr = self._expression(tmp_path)
        assert "data-bs-target" in expr and "data-target" in expr

    def test_it_accepts_only_observable_shown_state(self, tmp_path):
        expr = self._expression(tmp_path)
        for token in ("' show '", "' in '", "modal-open", "modal-backdrop",
                      "aria-hidden", "getComputedStyle", "getBoundingClientRect"):
            assert token in expr, token

    def test_hidden_is_decided_before_any_page_wide_signal(self, tmp_path):
        """A page-wide signal must never outvote the target being hidden.

        ``modal-open`` and ``.modal-backdrop`` say SOME dialog is open. On a
        Wyndham page carrying fourteen, that is not evidence about this one --
        and on the first live re-run it reported ``expanded: True`` for a
        lightbox that was still ``class="modal fade"``, so the bounded re-click
        never fired.
        """
        expr = self._expression(tmp_path)
        # Positions of the EXECUTABLE forms; both names also appear earlier in
        # the explanatory comment, which is not what is being asserted.
        hidden = expr.index("display === 'none'")
        assert hidden < expr.index("document.body && (' '")
        assert hidden < expr.index("querySelector('.modal-backdrop')")

    def test_a_zero_opacity_target_is_closed(self, tmp_path):
        """Bootstrap's ``.fade`` can hand back a non-zero box mid-transition."""
        assert "opacity" in self._expression(tmp_path)

    def test_it_never_reads_the_targets_text(self, tmp_path):
        """innerText/textContent are read on the CONTROL to find it by label --
        never on the target to decide whether it opened."""
        expr = self._expression(tmp_path)
        target_half = expr.split("var target")[1]
        assert "innerText" not in target_half
        assert "textContent" not in target_half

    def test_aria_expanded_still_wins_when_present(self, tmp_path):
        """Accordions are unchanged: the control's own state is read first."""
        expr = self._expression(tmp_path)
        assert expr.index("aria-expanded") < expr.index("data-bs-target")


class TestAccordionBehaviourUnchanged:
    def test_a_session_without_evaluate_is_unaffected(self, tmp_path):
        class NoEval(FakeBrowserSession):
            pass

        session = NoEval({URL: _payload(opened=True)})
        assert not hasattr(session, "evaluate")
        manifest = _run(tmp_path, session)
        assert manifest["counts"]["captured"] == 1

    def test_a_control_with_neither_signal_is_unknown_not_failed(self, tmp_path):
        """No aria-expanded and no data-target => None => never a failure."""
        class Unknown(ModalSession):
            def evaluate(self, expression, timeout: float = 60.0):
                self.evaluations.append(expression)
                if "scrollTo" in expression:
                    return 0
                return None                      # the browser says "unknown"

        session = Unknown(opens_on_click=1)
        manifest = _run(tmp_path, session)
        assert manifest["counts"]["captured"] == 1
        assert len(session.click_text_calls) == 1, "unknown never triggers a re-click"
