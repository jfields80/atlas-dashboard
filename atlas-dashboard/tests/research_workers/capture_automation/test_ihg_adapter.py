"""PTF-CAPTURE-2A -- the IHG adapter, and the Hyatt refusal.

Everything asserted here was derived from a supervised discovery session
against the real Staybridge Suites Columbus-Dublin page, then frozen as a
redacted fixture. Nothing is guessed.

The Hyatt half of this file records a decision rather than an implementation:
hyatt.com serves a Kasada interstitial, and the correct response is to classify
it, route the hotel to a human, and build nothing.

Offline: no browser, no network.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from services.research_workers.capture_automation.adapters import (
    adapter_for, known_brands,
)
from services.research_workers.capture_automation.adapters.ihg import IhgAdapter
from services.research_workers.capture_automation.contracts import (
    CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, DomSnapshot,
)
from services.research_workers.capture_automation.hydration import (
    CHALLENGE_SHELL_MAX_HTML_BYTES, looks_like_challenge_shell,
)
from services.research_workers.capture_automation.identity_check import (
    verify_identity,
)
from services.research_workers.capture_automation.queue import CaptureQueue
from services.research_workers.capture_automation.reasons import retry_for
from services.research_workers.capture_automation.runner import (
    CaptureRunner, RunnerConfig,
)
from services.research_workers.source_retrieval import (
    URL_SHAPE_PROPERTY, classify_url_shape, extract_property_code_from_url,
)

from .conftest import (
    FakeBrowserSession, entry_for, load_fixture, pages_from, snapshot_for,
)

IHG = "ihg-cmhtc.json"
IHG_URL = "https://www.ihg.com/staybridge/hotels/us/en/dublin/cmhtc/hoteldetail"

# The real Kasada shell hyatt.com served, trimmed. Reproduced so the classifier
# is tested against what the brand actually sends, not an invented stand-in.
KASADA_SHELL = (
    '<html><head></head><body><script>window.KPSDK={};KPSDK.now=typeof '
    'performance!==\'undefined\'&&performance.now?performance.now.bind('
    'performance):Date.now.bind(Date);KPSDK.start=KPSDK.now();</script>'
    '<script src="/149e9513-01fa-4fb0-aad4-566afd725d1b/ips.js?tkrm_alpekz'
    '=abc&amp;x-kpsdk-im=AAL_NdXg"></script>'
    '<iframe src="javascript:;" style="display: none;"></iframe></body></html>')


# --------------------------------------------------------------------------- #
# 1. IHG identity.
# --------------------------------------------------------------------------- #

class TestIhgIdentity:
    def test_the_brand_is_registered(self):
        assert "ihg" in known_brands()
        assert adapter_for("ihg").brand == "ihg"

    def test_the_property_code_extracts_from_the_bare_path_segment(self):
        """IHG puts the code in its own segment before /hoteldetail; the
        existing extractor already handles it, so Phase 2A adds nothing to a
        fail-closed identity function it does not need to touch."""
        assert extract_property_code_from_url(IHG_URL) == "cmhtc"

    def test_the_url_is_property_shaped(self):
        assert classify_url_shape(IHG_URL) == URL_SHAPE_PROPERTY
        assert IhgAdapter().url_is_property_page(IHG_URL)

    def test_jsonld_carries_full_identity(self):
        observed = IhgAdapter().extract_identity(snapshot_for(IHG),
                                                 known_codes=["cmhtc"])
        assert observed.name == "Staybridge Suites Columbus-Dublin"
        assert observed.phone
        assert observed.street
        assert observed.property_code == "cmhtc"

    def test_the_real_seed_entry_verifies_exact_match(self):
        """The seed says "Columbus Dublin"; the page says "Columbus-Dublin".
        The shared assessor must still reach EXACT_MATCH."""
        verdict = verify_identity(snapshot_for(IHG), entry_for(IHG),
                                  observed_at="2026-08-01T00:00:00Z")
        assert verdict.ok
        assert verdict.classification == "EXACT_MATCH"

    def test_a_different_property_code_is_still_refused(self):
        wrong = entry_for(IHG, expected_property_code="cmhzz")
        verdict = verify_identity(snapshot_for(IHG), wrong)
        assert not verdict.ok
        assert verdict.reason == "PROPERTY_CODE_MISMATCH"


# --------------------------------------------------------------------------- #
# 2. IHG policy location.
# --------------------------------------------------------------------------- #

class TestIhgPolicy:
    def test_the_policy_is_located(self):
        loc = adapter_for("ihg").locate_policy(snapshot_for(IHG))
        assert loc is not None
        assert loc.confidence in (CONFIDENCE_HIGH, CONFIDENCE_MEDIUM)

    @pytest.mark.parametrize("needle", [
        "This is a dog only hotel",
        "Up to two friendly pups under 80 lbs",
        "Pet fee per pet is 75 to 150 dollars",
        "depending on length of stay",
    ])
    def test_the_real_terms_survive(self, needle):
        loc = adapter_for("ihg").locate_policy(snapshot_for(IHG))
        assert needle in loc.text_excerpt

    def test_the_block_is_verbatim_from_the_page(self):
        dom = snapshot_for(IHG)
        loc = adapter_for("ihg").locate_policy(dom)
        assert loc.text_excerpt in dom.text

    def test_the_block_stops_at_the_faq_controls(self):
        """Without the FAQ terminators the answer runs on into the page's own
        navigation furniture."""
        loc = adapter_for("ihg").locate_policy(snapshot_for(IHG))
        for tail in ("READ FEWER FAQS", "Was anything missing", "READ MORE FAQS"):
            assert tail not in loc.text_excerpt

    def test_prose_amounts_without_a_dollar_sign_still_score(self):
        """IHG writes "75 to 150 dollars", so the money pattern never fires;
        the brand anchors are what carry the block over LOW."""
        loc = adapter_for("ihg").locate_policy(snapshot_for(IHG))
        assert "$" not in loc.text_excerpt
        assert loc.confidence != "LOW"
        assert any(a in loc.matched_anchors
                   for a in ("Our Pet Policy", "Pet fee per pet", "dog only hotel"))


# --------------------------------------------------------------------------- #
# 3. IHG interaction plan -- the two-click reveal.
# --------------------------------------------------------------------------- #

class TestIhgInteraction:
    def test_two_expanders_are_planned_in_order(self):
        """The FAQ list must be expanded before the pet question is laid out
        at all: items 4-11 have zero geometry until then."""
        adapter = adapter_for("ihg")
        controls = list(adapter.expand_text_controls)
        assert controls[0][1] == "FAQ"
        assert controls[1][1] == "bring my pet"

    def test_the_plan_emits_click_text_for_both(self):
        adapter = adapter_for("ihg")
        html = ('<a class="cmp-faq__action">READ MORE FAQS</a>'
                '<button class="cmp-accordion__button">Can I bring my pet to X?</button>')
        dom = DomSnapshot(final_url=IHG_URL, html=html, text="Pet Policy")
        steps = adapter.interaction_plan(dom, None)
        actions = [(s.action, s.text) for s in steps if s.action == "click_text"]
        assert ("click_text", "FAQ") in actions
        assert ("click_text", "bring my pet") in actions

    def test_no_click_is_planned_for_controls_the_page_lacks(self):
        dom = DomSnapshot(final_url=IHG_URL, html="<html></html>", text="Pet Policy")
        assert not [s for s in adapter_for("ihg").interaction_plan(dom, None)
                    if s.action == "click_text"]

    def test_consent_is_still_never_auto_dismissed(self):
        assert adapter_for("ihg").consent_selectors() == ()

    def test_no_container_selector_is_offered(self):
        """IHG's eleven FAQ panels share one class, so any container selector
        resolves to the first of them -- a collapsed parking answer with zero
        height. Offering one made the live pilot fail POLICY_OFF_SCREEN at
        0.00 visible while the pet policy sat open further down the page."""
        assert adapter_for("ihg").container_selectors == ()

    def test_the_policy_is_addressed_by_text_not_by_selector(self):
        from services.research_workers.capture_automation.runner import (
            _policy_handle,
        )
        dom = snapshot_for(IHG)
        loc = adapter_for("ihg").locate_policy(dom)
        assert loc.selector == ""
        kind, value = _policy_handle(loc, FakeBrowserSession(pages_from(IHG)))
        assert kind == "text"
        assert value and value in dom.text

    def test_the_adapter_cannot_widen_the_url_gate(self):
        assert not adapter_for("ihg").url_is_property_page(
            "https://www.ihg.com/hotels/us/en/find-hotels?destination=Dublin")


# --------------------------------------------------------------------------- #
# 4. IHG through the runner.
# --------------------------------------------------------------------------- #

#: The one test below that leaves the fixtures and asks the REAL generator what
#: it selects depends on ``retr-<id>.json`` retrieval artifacts under
#: ``data/worker_runs/pettripfinder/``, which is gitignored. With none on disk
#: ``build_queue`` excludes every hotel for want of a demonstrated automated
#: failure, selects nothing, and the assertion reads as an adapter regression
#: when the adapter was never reached. Same precondition, same wording and same
#: reasoning as ``tests/pettripfinder/test_build_capture_queue.py``; calling
#: ``retrieval_artifacts()`` itself, rather than testing for the directory,
#: keeps a real selection regression failing instead of skipping.
_ARTIFACT_REASON = (
    "no retrieval artifacts on disk: data/worker_runs/pettripfinder/retr-*.json "
    "is gitignored, so build_queue() excludes every hotel for want of a "
    "demonstrated automated failure and selects nothing. Run in a checkout that "
    "carries data/.")


@pytest.fixture(scope="module")
def real_retrieval_artifacts():
    """Skip, with the reason named, when no hotel can be selected at all."""
    from scripts.pettripfinder.build_capture_queue import retrieval_artifacts

    if not retrieval_artifacts():
        pytest.skip(_ARTIFACT_REASON)


class TestIhgThroughTheRunner:
    def test_a_staybridge_page_captures(self, tmp_path):
        # Fixture-driven and self-contained: this one exercises the adapter
        # itself and stands alone in any checkout, so it is NOT gated.
        session = FakeBrowserSession(pages_from(IHG))
        runner = CaptureRunner(session, RunnerConfig(batch_dir=tmp_path / "b"),
                               clock=_clock(), sleep=lambda s: None,
                               jitter=lambda a, b: a)
        result = runner.run(CaptureQueue(batch_id="b", entries=(entry_for(IHG),)))
        assert result.manifest["counts"]["captured"] == 1
        cap = result.manifest["successful_captures"][0]
        assert "cmhtc" in cap["citable_url"]

    def test_the_queue_generator_selects_the_real_staybridge(
            self, real_retrieval_artifacts):
        from scripts.pettripfinder.build_capture_queue import build_queue
        result = build_queue(batch_id="c", brands=["ihg"])
        assert result.counts["selected"] == 1
        entry = result.selected[0]
        assert entry["hotel_id"] == "staybridge-suites-columbus-dublin"
        assert entry["expected_property_code"] == "cmhtc"
        assert entry["retrieval_artifact"]


def _clock():
    class C:
        t = 1_781_000_000.0

        def __call__(self):
            C.t += 0.5
            return C.t
    return C()


# --------------------------------------------------------------------------- #
# 5. Hyatt: classified, refused, routed to a human. No adapter.
# --------------------------------------------------------------------------- #

class TestHyattIsRefusedNotDefeated:
    """hyatt.com serves a Kasada interstitial to our visible Chrome: an
    811-byte body holding window.KPSDK and an ips.js challenge loader, which
    never resolves (unchanged across 15s, readyState complete, page blank).

    The decision recorded here is to classify it and stop. Defeating it would
    mean satisfying a bot-defence challenge, which ADR-PTF-AUTOMATED-BROWSING
    forbids by name.
    """

    def test_no_hyatt_adapter_is_registered(self):
        assert "hyatt" not in known_brands()
        assert adapter_for("hyatt") is None

    def test_the_kasada_shell_is_classified_as_a_challenge(self):
        dom = DomSnapshot(final_url="https://www.hyatt.com/x", html=KASADA_SHELL, text="")
        assert looks_like_challenge_shell(dom) == "captcha_or_challenge_page"

    def test_a_challenged_hotel_routes_to_manual_capture(self):
        """Manual official-source capture through ordinary human browsing is
        the only permitted route."""
        assert retry_for("CAPTCHA_OR_CHALLENGE") == "manual"
        assert retry_for("ACCESS_BLOCKED") == "manual"

    def test_the_runner_reports_a_challenge_not_an_identity_failure(self, tmp_path):
        """Before this, a textless wall timed out as IDENTITY_UNVERIFIABLE --
        "we could not tell who this is" rather than "this brand refused us"."""
        payload = dict(load_fixture(IHG), html=KASADA_SHELL, text="", jsonld=[])
        url = payload["final_url"]
        session = FakeBrowserSession({url: payload})
        runner = CaptureRunner(session, RunnerConfig(batch_dir=tmp_path / "b"),
                               clock=_clock(), sleep=lambda s: None,
                               jitter=lambda a, b: a)
        result = runner.run(CaptureQueue(batch_id="b", entries=(entry_for(IHG),)))
        exc = result.manifest["exceptions"][0]
        assert exc["reason"] == "CAPTCHA_OR_CHALLENGE"
        assert exc["retry"] == "manual"

    def test_a_real_page_is_never_mistaken_for_a_shell(self):
        """The classifier must not fire on a page that simply has lots of
        script: it requires a tiny body AND no rendered text."""
        assert looks_like_challenge_shell(snapshot_for(IHG)) == ""
        assert looks_like_challenge_shell(snapshot_for("marriott-cmham.json")) == ""

    def test_a_shell_with_text_is_not_classified_by_this_rule(self):
        dom = DomSnapshot(final_url="https://x/y", html=KASADA_SHELL,
                          text="Welcome to the hotel")
        assert looks_like_challenge_shell(dom) == ""

    def test_a_large_body_is_not_classified_by_this_rule(self):
        dom = DomSnapshot(final_url="https://x/y",
                          html=KASADA_SHELL + ("<div>x</div>" * 2000), text="")
        assert len(dom.html) > CHALLENGE_SHELL_MAX_HTML_BYTES
        assert looks_like_challenge_shell(dom) == ""

    def test_no_challenge_defeating_technique_is_present(self):
        """Named so a future change cannot quietly add one.

        Scans EXECUTABLE code only, with comments and docstrings stripped: the
        detector and its rationale necessarily name Kasada's artefacts in order
        to recognise and explain them, and a raw text scan would flag the
        explanation as the offence.
        """
        import io
        import tokenize

        import services.research_workers.capture_automation as pkg

        def code_only(path: pathlib.Path) -> str:
            out, prev_type = [], tokenize.INDENT
            src = path.read_text("utf-8")
            try:
                toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
            except tokenize.TokenError:            # pragma: no cover - defensive
                return src.lower()
            for tok in toks:
                if tok.type == tokenize.COMMENT:
                    continue
                # A bare string statement is a docstring, not code.
                if tok.type == tokenize.STRING and prev_type in (
                        tokenize.INDENT, tokenize.NEWLINE, tokenize.NL,
                        tokenize.DEDENT):
                    prev_type = tok.type
                    continue
                out.append(tok.string)
                if tok.type not in (tokenize.NL,):
                    prev_type = tok.type
            return " ".join(out).lower()

        banned = ("x-kpsdk", "ips.js", "solve_captcha", "captcha_token",
                  "setuseragentoverride", "fingerprint", "token_replay",
                  "kpsdk.start", "kpsdk.now")
        root = pathlib.Path(pkg.__file__).parent
        scanned = 0
        for path in sorted(root.rglob("*.py")):
            # doctrine.py is the single declared home for banned-technique
            # NAMES -- it lists them so the boundary scan can ban them. The
            # existing TestNoStealth excludes it for the same reason.
            if path.name == "doctrine.py":
                continue
            code = code_only(path)
            scanned += 1
            for marker in banned:
                assert marker not in code, "%s executes %s" % (path.name, marker)
        assert scanned >= 10, "the scan must actually have read the package"

    def test_the_detector_recognises_but_does_not_execute_kasada(self):
        """`KPSDK` appears in the marker list -- as a string to match against,
        never as something invoked."""
        import services.research_workers.capture_automation.hydration as hyd
        assert "KPSDK" in hyd._CHALLENGE_SHELL_MARKERS
        assert not hasattr(hyd, "KPSDK")
