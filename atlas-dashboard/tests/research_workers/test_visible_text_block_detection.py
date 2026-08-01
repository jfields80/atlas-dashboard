"""PTF-CAPTURE-003D -- a wall is what a reader is shown.

Block detection used to run over the NORMALIZED HTML, which includes markup no
visitor ever sees. IHG ships a dormant sign-in widget in every page's chrome --
"your session has expired. please sign in to your profile" -- so the Staybridge
Suites Columbus-Dublin property page was rejected as ``login_required_page``
while its pet policy, address and phone were all plainly rendered and
photographed. The string was in the document; it was never on the screen.

The change is deliberately narrow: no marker was removed, no threshold
loosened, and there is no brand-specific exemption. Only the QUESTION changed,
from "does this string appear anywhere in the markup" to "was this shown to the
reader" -- and only when the capture carries rendered text to answer it with.

Offline: no network, no browser.
"""

from __future__ import annotations

import io
import json
import pathlib

import pytest

from services.research_workers.operator_capture import (
    CAPTURE_ACCEPTED, CAPTURE_REJECTED, CaptureJob,
    MIN_VISIBLE_TEXT_BYTES_FOR_BLOCK_CHECK, _CHALLENGE_MARKERS,
    _DENIED_MARKERS, _LOGIN_MARKERS, _page_block_reason, ingest_capture,
    page_block_reason_for_capture,
)

FIXTURE = (pathlib.Path(__file__).resolve().parents[1] / "research_workers"
           / "capture_automation" / "fixtures" / "ihg-cmhtc.json")

# The dormant fragment IHG ships to anonymous visitors, verbatim from the real
# normalized text. Never rendered.
DORMANT_SIGNIN = (
    "join for free sign in join for free sign in sign in user first name "
    "sign out user first name user points pts your session has expired. "
    "please sign in to your profile sign in / join for free")

PUBLIC_BODY = (
    "Staybridge Suites Columbus-Dublin. 6095 Emerald Parkway Dublin, OH 43016 "
    "United States. Contact Front Desk: +1-614-7349882. "
    "Can I bring my pet to Staybridge Suites Columbus-Dublin? "
    "Pets are welcome at Staybridge Suites Columbus-Dublin. Our Pet Policy: "
    "This is a dog only hotel. Up to two friendly pups under 80 lbs are "
    "welcome. Pet fee per pet is 75 to 150 dollars depending on length of "
    "stay of reservation. Guests are responsible for any damages or extra "
    "cleaning needs billed post departure.")


# --------------------------------------------------------------------------- #
# A. The exact IHG false positive.
# --------------------------------------------------------------------------- #

class TestTheIhgFalsePositive:
    def test_dormant_signin_markup_no_longer_rejects_a_public_page(self):
        normalized = PUBLIC_BODY + " " + DORMANT_SIGNIN
        reason, source = page_block_reason_for_capture(PUBLIC_BODY, normalized)
        assert reason == ""
        assert source == "visible_text"

    def test_the_old_behaviour_really_did_reject_it(self):
        """Pins what changed: the normalized text alone still reads as a wall,
        which is exactly why the question had to move."""
        normalized = PUBLIC_BODY + " " + DORMANT_SIGNIN
        assert _page_block_reason(normalized) == "login_required_page"
        assert _page_block_reason(PUBLIC_BODY) == ""

    def test_the_marker_is_untouched(self):
        assert "please sign in" in _LOGIN_MARKERS


# --------------------------------------------------------------------------- #
# B. A genuine, visible login wall still rejects.
# --------------------------------------------------------------------------- #

#: Filler so a wall's visible text clears the usability floor. A real wall page
#: is never three words long; padding here keeps these tests about the MARKER
#: rather than about length.
_PAD = ("This page is part of the hotel booking website and the remainder of "
        "the document contains the usual navigation, footer links, legal "
        "notices and contact details that every page on this domain carries. ")


def _wall(sentence: str) -> str:
    visible = sentence + " " + _PAD
    assert len(visible.encode("utf-8")) >= MIN_VISIBLE_TEXT_BYTES_FOR_BLOCK_CHECK
    return visible


class TestGenuineWallsStillReject:
    @pytest.mark.parametrize("marker", _LOGIN_MARKERS)
    def test_every_login_marker_still_rejects_when_visible(self, marker):
        reason, source = page_block_reason_for_capture(
            _wall("Members only area. %s to view this property's details."
                  % marker.capitalize()), "")
        assert reason == "login_required_page"
        assert source == "visible_text"

    @pytest.mark.parametrize("marker", _CHALLENGE_MARKERS)
    def test_every_challenge_marker_still_rejects_when_visible(self, marker):
        assert page_block_reason_for_capture(
            _wall("Before you continue: %s." % marker), "")[0] \
            == "captcha_or_challenge_page"

    @pytest.mark.parametrize("marker", _DENIED_MARKERS)
    def test_every_denied_marker_still_rejects_when_visible(self, marker):
        assert page_block_reason_for_capture(
            _wall("%s. You are not authorised to view this resource." % marker), "")[0] \
            == "access_denied_page"

    def test_a_visible_session_expired_wall_rejects(self):
        """The very phrase IHG ships dormant -- rejected when actually shown."""
        assert page_block_reason_for_capture(
            _wall("Your session has expired. Please sign in to your profile "
                  "to continue."), "")[0] == "login_required_page"

    def test_challenge_outranks_login_as_before(self):
        assert page_block_reason_for_capture(
            _wall("Please sign in. Also complete the captcha below."), "")[0] \
            == "captcha_or_challenge_page"


# --------------------------------------------------------------------------- #
# C + D. Fallback when there is no usable rendered text.
# --------------------------------------------------------------------------- #

class TestFallback:
    WALL = ("Please sign in to continue. This content is available to members "
            "only and requires an account before it can be displayed to you.")

    def test_missing_visible_text_falls_back_and_rejects(self):
        reason, source = page_block_reason_for_capture("", self.WALL)
        assert reason == "login_required_page"
        assert source == "normalized_html_fallback"

    @pytest.mark.parametrize("visible", ["", "   ", "\n\t  \n", None])
    def test_empty_or_whitespace_visible_text_falls_back(self, visible):
        reason, source = page_block_reason_for_capture(visible, self.WALL)
        assert source == "normalized_html_fallback"
        assert reason == "login_required_page"

    def test_a_too_short_visible_field_falls_back(self):
        """A handful of characters is not a rendered page; below the floor the
        normalized HTML is the only evidence there is."""
        stub = "Loading"
        assert len(stub) < MIN_VISIBLE_TEXT_BYTES_FOR_BLOCK_CHECK
        reason, source = page_block_reason_for_capture(stub, self.WALL)
        assert source == "normalized_html_fallback"
        assert reason == "login_required_page"

    def test_fallback_still_passes_a_clean_page(self):
        reason, source = page_block_reason_for_capture("", PUBLIC_BODY)
        assert reason == ""
        assert source == "normalized_html_fallback"

    def test_the_threshold_is_a_floor_not_a_gate(self):
        """Just over the floor, the visible text decides."""
        visible = PUBLIC_BODY[:MIN_VISIBLE_TEXT_BYTES_FOR_BLOCK_CHECK + 20]
        assert page_block_reason_for_capture(visible, self.WALL)[1] == "visible_text"


# --------------------------------------------------------------------------- #
# E. The gate is not weakened.
# --------------------------------------------------------------------------- #

class TestTheGateIsNotWeakened:
    def test_no_marker_was_removed(self):
        assert len(_LOGIN_MARKERS) == 6
        assert len(_CHALLENGE_MARKERS) == 8
        assert len(_DENIED_MARKERS) == 5

    def test_the_underlying_detector_is_unchanged(self):
        """_page_block_reason itself behaves exactly as before; only the choice
        of WHICH text to hand it moved."""
        assert _page_block_reason("please sign in") == "login_required_page"
        assert _page_block_reason("access denied") == "access_denied_page"
        assert _page_block_reason("recaptcha") == "captcha_or_challenge_page"
        assert _page_block_reason("a perfectly ordinary hotel page") == ""

    def test_there_is_no_brand_specific_exemption(self):
        """Executable code only. The function's docstring necessarily names IHG
        to explain the defect it fixes; a raw text scan would flag the
        explanation as the offence."""
        import ast

        import services.research_workers.operator_capture as mod
        tree = ast.parse(pathlib.Path(mod.__file__).read_text("utf-8"))
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef)
                  and n.name == "page_block_reason_for_capture")
        body = list(fn.body)
        if (body and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)):
            body = body[1:]                     # drop the docstring
        code = "\n".join(ast.unparse(n) for n in body).lower()
        assert code.strip(), "the function body must not be empty"
        for brand in ("ihg", "staybridge", "marriott", "hilton", "hyatt", "cmhtc"):
            assert brand not in code, brand

    def test_a_wall_with_no_visible_text_at_all_still_rejects(self):
        """The Kasada case: nothing rendered. Fallback is what catches it."""
        assert page_block_reason_for_capture("", "unusual traffic detected")[0] \
            == "captcha_or_challenge_page"


# --------------------------------------------------------------------------- #
# F. The real archived capture, pinned end to end.
# --------------------------------------------------------------------------- #

def _job() -> CaptureJob:
    return CaptureJob(
        assignment_id="attest-staybridge-cmhtc",
        listing_key="staybridge suites columbus dublin",
        listing_name="Staybridge Suites Columbus Dublin",
        expected_address="6095 Emerald Parkway", expected_city="Dublin",
        expected_state="OH", expected_postal_code="43016",
        expected_phone="614-734-9882",
        official_url="https://www.ihg.com/staybridge/hotels/us/en/dublin/"
                     "cmhtc/hoteldetail")


@pytest.mark.skipif(not FIXTURE.exists(), reason="IHG fixture absent")
class TestTheArchivedStaybridgeCapture:
    @pytest.fixture(scope="class")
    @classmethod
    def payload(cls):
        return json.loads(io.open(FIXTURE, encoding="utf-8").read())

    def test_the_rendered_text_carries_no_login_marker(self, payload):
        """The committed fixture is redacted to head-only HTML, so it cannot
        carry the dormant widget itself -- TestTheIhgFalsePositive pins that
        against the verbatim fragment, and TestTheUnredactedArchivedCapture
        against the real page. What this fixture proves is the other half: the
        page a reader saw contains no wall at all."""
        for marker in _LOGIN_MARKERS:
            assert marker not in payload["text"].lower()

    def test_the_visible_text_clears_the_block_check(self, payload):
        assert page_block_reason_for_capture(payload["text"], "")[0] == ""

    def test_the_policy_wording_is_present_and_intact(self, payload):
        for needle in ("dog only hotel", "under 80 lbs",
                       "75 to 150 dollars", "length of stay"):
            assert needle in payload["text"], needle

    def test_the_capture_url_is_the_property_page(self, payload):
        assert "cmhtc" in payload["final_url"]
        assert "?" not in payload["final_url"]


# The un-redacted archived capture, when the operational corpus is present.
# It is the only artefact that carries IHG's dormant widget in full, so it is
# the only one that can demonstrate the original rejection end to end. Skipped
# in a clean clone, where data/ does not exist.
_ARCHIVED = (pathlib.Path(__file__).resolve().parents[2] / "data" / "worker_runs"
             / "pettripfinder" / "attestation_batch_005" / "captures"
             / ("www-ihg-com-staybridge-hotels-us-en-dublin-cmhtc-hoteldetail-"
                "2026-08-01T15-34-46-037Z.json"))


@pytest.mark.skipif(not _ARCHIVED.exists(),
                    reason="operational corpus absent (gitignored)")
class TestTheUnredactedArchivedCapture:
    @pytest.fixture(scope="class")
    @classmethod
    def payload(cls):
        return json.loads(io.open(_ARCHIVED, encoding="utf-8").read())

    def test_the_dormant_widget_is_really_in_the_markup(self, payload):
        """If IHG stops shipping it, this stops proving anything -- and says so
        loudly rather than passing quietly."""
        assert "session has expired" in payload["html"].lower()

    def test_the_marker_is_manufactured_by_flattening(self, payload):
        """"please sign in" is not even a contiguous string in the document.
        It only exists once normalisation joins separate elements' text, which
        is about as far from "shown to a reader" as a phrase can get."""
        from scripts.pettripfinder.importer.source_snapshot import (
            normalize_html_to_text,
        )
        assert "please sign in" not in payload["html"].lower()
        normalized, _ = normalize_html_to_text(payload["html"])
        assert "please sign in" in normalized.lower()

    def test_but_never_in_the_rendered_text(self, payload):
        assert "please sign in" not in payload["text"].lower()
        assert "session has expired" not in payload["text"].lower()

    def test_the_old_rule_rejected_it_and_the_new_one_does_not(self, payload):
        from scripts.pettripfinder.importer.source_snapshot import (
            normalize_html_to_text,
        )
        normalized, _ = normalize_html_to_text(payload["html"])
        assert _page_block_reason(normalized) == "login_required_page"
        assert page_block_reason_for_capture(payload["text"], normalized) \
            == ("", "visible_text")

    def test_it_now_ingests_cleanly(self, payload):
        outcome = ingest_capture(payload, _job(), observed_at="2026-08-01T15:34:46Z")
        assert outcome.status == CAPTURE_ACCEPTED, outcome.failure_reason
        assert outcome.policy_applicable
