"""PTF-CAPTURE -- the batch runner must leave a capture ATTESTABLE.

sweep_missing_views was written and tested and had no production caller, so
every batch capture arrived one screenshot short: the policy proven, the
identity not. The attestation gate then refused the package for showing none
of the seven fields a human is asked to affirm -- a capture that cost an
operator a browser session and could never be used.

These tests pin the wiring and, more importantly, what it must never become:
a view is only ever written for a value the page actually PAINTS, so queue
metadata alone can never satisfy the gate.

Offline: the browser session is a fake. No network, no Chrome, no writes
outside tmp_path.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import struct
import zlib

import pytest

from services.research_workers.capture_automation import runner as R
from services.research_workers.capture_automation.evidence_completeness import (
    FIELD_CITY, FIELD_HOTEL_NAME, FIELD_POLICY_TEXT, FIELD_POSTAL_CODE,
    FIELD_PROPERTY_PHONE, FIELD_STATE, FIELD_STREET, REQUIRED_FIELDS,
)
from services.research_workers.capture_automation.identity_views import (
    ADDITIONAL_VIEWS_KEY, load_views_for_capture, sweep_missing_views,
)
from services.research_workers.capture_automation.queue import QueueEntry

OFFICIAL = ("https://www.wyndhamhotels.com/baymont/columbus-ohio/"
            "baymont-inn-and-suites-columbus-rickenbacker/overview")

#: Baymont, exactly as the validated queue entry carries it.
ENTRY = QueueEntry(
    hotel_id="baymont-by-wyndham-columbus-rickenbacker",
    listing_key="baymont by wyndham columbus rickenbacker",
    hotel_name="Baymont by Wyndham Columbus/Rickenbacker",
    brand="wyndham", official_url=OFFICIAL,
    expected_address="2323 Rickenbacker Parkway West",
    expected_city="Columbus", expected_state="Ohio",
    expected_postal_code="43217", expected_phone="614-491-4400",
)


def _png(width=1424, height=905, salt=b"a"):
    """A real, decodable PNG -- the writer records its true dimensions."""
    raw = b"".join(b"\x00" + bytes([salt[0]]) * (width * 3) for _ in range(height))

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b""))


class FakeSession(object):
    """Only what the sweep needs: viewport, evaluate, screenshot_png."""

    def __init__(self, painted):
        #: field -> the text the page paints for it (absent = not shown)
        self.painted = dict(painted)
        self.scroll_y = 0
        self.shots = 0

    def viewport(self):
        return (1424, 905)

    def screenshot_png(self):
        self.shots += 1
        return _png(salt=bytes([97 + (self.shots % 5)]))

    #: Where each field sits on the page, in document coordinates. All within
    #: one viewport, so a single frame can cover them -- which is what the
    #: real Baymont page does with its identity block.
    PAGE_TOP = {FIELD_HOTEL_NAME: 200, FIELD_STREET: 240, FIELD_CITY: 280,
                FIELD_STATE: 320, FIELD_POSTAL_CODE: 360,
                FIELD_PROPERTY_PHONE: 400, FIELD_POLICY_TEXT: 440}

    def evaluate(self, script):
        if script.startswith("window.scrollTo"):
            self.scroll_y = int(script.split(",")[1].strip(" )"))
            return None
        out = {"_scrollY": self.scroll_y, "_occludedTop": 0}
        for field, needles in _plan_from(script).items():
            text = self.painted.get(field)
            if text is None:
                continue
            page_top = self.PAGE_TOP.get(field, 300)
            top = page_top - self.scroll_y          # viewport-relative
            for n in needles:
                if n.lower() in text.lower():
                    out.setdefault(field, []).append(
                        {"needle": n, "text": text,
                         "top": top, "bottom": top + 30,
                         "pageTop": page_top, "pageBottom": page_top + 30,
                         "left": 10, "width": 400, "height": 30,
                         "context": "fake"})
                    break
        return out


def _plan_from(script):
    """Recover the probe plan the sweep embedded in its JS."""
    start = script.index("const want = ") + len("const want = ")
    end = script.index(";", start)
    return json.loads(script[start:end])


def _write_capture(tmp_path, final_url=OFFICIAL):
    path = tmp_path / "cap.json"
    path.write_text(json.dumps({
        "schema": "ptf-official-capture/1.0", "final_url": final_url,
        "requested_url": final_url, "text": "policy text", "html": "<html></html>",
        "text_sha256": "0" * 64, "html_sha256": "1" * 64,
        "automation": {"controller_version": "test"},
    }), encoding="utf-8")
    return path


#: The policy as the LOCATOR reports it: normalised text, block boundaries
#: flattened to " / ". This exact shape is what a real Wyndham capture carries.
POLICY_EXCERPT = ("Service Animals - ADA-defined service animals are welcome "
                  "free of charge. / Dogs Allowed - 2 dogs max. 50lbs or less "
                  "per pet. / Fees - 25 USD per pet per night.")

#: The same policy as the BROWSER paints it. No " / " anywhere -- which is why
#: the raw excerpt is unfindable and a separator-free run is not.
POLICY_PAINTED = POLICY_EXCERPT.replace(" / ", "\n")

ALL_PAINTED = {
    FIELD_HOTEL_NAME: "Baymont by Wyndham Columbus/Rickenbacker",
    FIELD_STREET: "2323 Rickenbacker Parkway West",
    FIELD_CITY: "Columbus",
    FIELD_STATE: "Ohio",
    FIELD_POSTAL_CODE: "43217",
    FIELD_PROPERTY_PHONE: "+1-614-491-4400",
    FIELD_POLICY_TEXT: POLICY_PAINTED,
}


def _sweep(tmp_path, painted, entry=ENTRY, policy_text=POLICY_EXCERPT):
    cap = _write_capture(tmp_path)
    runner = R.CaptureRunner.__new__(R.CaptureRunner)      # writer only; no browser
    runner._clock = lambda: 1754170000.0
    session = FakeSession(painted)
    result = sweep_missing_views(
        session, capture_path=cap, official_url=OFFICIAL,
        expected=R._expected_identity(entry, policy_text),
        write_view=runner._view_writer(cap, OFFICIAL))
    return cap, result, session


# --------------------------------------------------------------------------- #
# A / B / G. The wiring produces real, sidecar-backed views.
# --------------------------------------------------------------------------- #

class TestSweepProducesViews:
    def test_a_all_required_identity_fields_are_proven(self, tmp_path):
        cap, result, _s = _sweep(tmp_path, ALL_PAINTED)
        assert result.complete, result.notes
        proven = set()
        for v in load_views_for_capture(cap):
            proven |= {o.field for o in v.observations if o.readable}
        assert set(REQUIRED_FIELDS) <= proven

    def test_b_every_view_has_a_matching_sidecar_on_disk(self, tmp_path):
        cap, _r, _s = _sweep(tmp_path, ALL_PAINTED)
        payload = json.loads(cap.read_text(encoding="utf-8"))
        views = payload["automation"][ADDITIONAL_VIEWS_KEY]
        assert views
        for v in views:
            side = cap.parent / (v["png_file"][:-4] + ".view.json")
            png = cap.parent / v["png_file"]
            assert side.exists() and png.exists()
            sc = json.loads(side.read_text(encoding="utf-8"))
            assert sc["png_sha256"] == hashlib.sha256(png.read_bytes()).hexdigest()
            assert sc["png_sha256"] == v["png_sha256"]
            assert sc["field_observations"]
            assert sc["final_url"] == OFFICIAL

    def test_g_the_policy_needle_survives_the_locator_s_normalisation(self, tmp_path):
        """The seventh field is hunted with a phrase the DOM can contain.

        The excerpt the locator hands over is normalised text; the browser
        paints newlines. Hunting the excerpt verbatim finds nothing, so the
        capture that HAS a policy on screen would be filed as not showing one.
        """
        assert POLICY_EXCERPT not in POLICY_PAINTED       # the whole problem
        needle = R._policy_needle(POLICY_EXCERPT)
        assert needle == ("Service Animals - ADA-defined service animals are "
                          "welcome")
        assert needle in POLICY_PAINTED
        # Trimmed to whole words at the planner's own limit: the needle the
        # probe hunts and the needle it reports back must be one string, or
        # every policy observation reads as contradicting itself.
        assert len(needle) <= R.POLICY_NEEDLE_MAX and not needle.endswith(" ")

        cap, result, _s = _sweep(tmp_path, ALL_PAINTED)
        proven = set()
        for v in load_views_for_capture(cap):
            proven |= {o.field for o in v.observations if o.readable}
        assert FIELD_POLICY_TEXT in proven
        assert result.complete, result.notes

    def test_g_an_unlocated_policy_is_never_invented(self, tmp_path):
        """No excerpt means no needle -- not a needle made up from the queue."""
        assert R._policy_needle("") == ""
        cap, result, session = _sweep(tmp_path, ALL_PAINTED, policy_text="")
        assert not result.complete
        assert FIELD_POLICY_TEXT in result.report.missing
        proven = set()
        for v in load_views_for_capture(cap):
            proven |= {o.field for o in v.observations if o.readable}
        assert FIELD_POLICY_TEXT not in proven

    def test_h_repeating_the_sweep_does_not_duplicate_views(self, tmp_path):
        cap, _r, _s = _sweep(tmp_path, ALL_PAINTED)
        first = len(json.loads(cap.read_text(encoding="utf-8"))
                    ["automation"][ADDITIONAL_VIEWS_KEY])
        runner = R.CaptureRunner.__new__(R.CaptureRunner)
        runner._clock = lambda: 1754170000.0
        sweep_missing_views(FakeSession(ALL_PAINTED), capture_path=cap,
                            official_url=OFFICIAL,
                            expected=R._expected_identity(ENTRY, POLICY_EXCERPT),
                            write_view=runner._view_writer(cap, OFFICIAL))
        second = len(json.loads(cap.read_text(encoding="utf-8"))
                     ["automation"][ADDITIONAL_VIEWS_KEY])
        assert second == first          # complete already: nothing re-taken


# --------------------------------------------------------------------------- #
# C / D. It fails closed, and metadata alone proves nothing.
# --------------------------------------------------------------------------- #

class TestFailsClosed:
    def test_c_an_unpainted_required_field_leaves_the_package_incomplete(self, tmp_path):
        painted = {k: v for k, v in ALL_PAINTED.items() if k != FIELD_PROPERTY_PHONE}
        cap, result, _s = _sweep(tmp_path, painted)
        assert not result.complete
        assert FIELD_PROPERTY_PHONE in result.report.missing
        proven = set()
        for v in load_views_for_capture(cap):
            proven |= {o.field for o in v.observations if o.readable}
        assert FIELD_PROPERTY_PHONE not in proven

    def test_d_queue_metadata_alone_creates_no_passing_view(self, tmp_path):
        """The entry knows every value; the page paints none of them."""
        cap, result, session = _sweep(tmp_path, {})
        assert not result.complete
        assert json.loads(cap.read_text(encoding="utf-8")
                          )["automation"].get(ADDITIONAL_VIEWS_KEY, []) == []
        assert session.shots == 0        # nothing painted -> nothing photographed
        assert set(result.report.missing) == set(REQUIRED_FIELDS)

    def test_a_view_is_never_written_for_an_unreadable_hit(self, tmp_path):
        """A value painted BELOW the fold is in the page and not in the frame."""
        class Below(FakeSession):
            def evaluate(self, script):
                out = super().evaluate(script)
                if not isinstance(out, dict):
                    return out                       # scrollTo returns nothing
                for v in out.values():
                    if isinstance(v, list):
                        for hit in v:
                            hit["top"], hit["bottom"] = 5000, 5030
                return out

        cap = _write_capture(tmp_path)
        runner = R.CaptureRunner.__new__(R.CaptureRunner)
        runner._clock = lambda: 1754170000.0
        result = sweep_missing_views(
            Below(ALL_PAINTED), capture_path=cap, official_url=OFFICIAL,
            expected=R._expected_identity(ENTRY, POLICY_EXCERPT),
            write_view=runner._view_writer(cap, OFFICIAL))
        assert not result.complete


# --------------------------------------------------------------------------- #
# E / F. Nothing that already worked changed.
# --------------------------------------------------------------------------- #

class TestNothingElseMoved:
    def test_e_the_capture_payload_is_untouched_by_attachment(self, tmp_path):
        """A capture ingests identically before and after views are attached --
        html, text and their hashes are never rewritten."""
        cap = _write_capture(tmp_path)
        before = json.loads(cap.read_text(encoding="utf-8"))
        _c, _r, _s = None, None, None
        runner = R.CaptureRunner.__new__(R.CaptureRunner)
        runner._clock = lambda: 1754170000.0
        sweep_missing_views(FakeSession(ALL_PAINTED), capture_path=cap,
                            official_url=OFFICIAL,
                            expected=R._expected_identity(ENTRY, POLICY_EXCERPT),
                            write_view=runner._view_writer(cap, OFFICIAL))
        after = json.loads(cap.read_text(encoding="utf-8"))
        for k in ("schema", "final_url", "text", "html", "text_sha256", "html_sha256"):
            assert after[k] == before[k], k

    def test_f_expected_identity_reads_only_the_validated_queue_entry(self):
        exp = R._expected_identity(ENTRY, POLICY_EXCERPT)
        assert exp[FIELD_HOTEL_NAME] == ENTRY.hotel_name
        assert exp[FIELD_STREET] == ENTRY.expected_address
        assert exp[FIELD_PROPERTY_PHONE] == ENTRY.expected_phone
        assert set(exp) == set(REQUIRED_FIELDS)
        # The six identity needles come from the entry; the seventh comes from
        # THIS capture's own located policy -- never from either the other way.
        assert exp[FIELD_POLICY_TEXT] in POLICY_EXCERPT
        assert all(v not in POLICY_EXCERPT
                   for k, v in exp.items() if k != FIELD_POLICY_TEXT)

    def test_the_sweep_now_has_a_production_caller(self):
        """The defect this fixes: the function existed, was tested, and was
        called from nowhere."""
        import inspect
        src = inspect.getsource(R)
        assert "sweep_missing_views(" in src
        assert "from .identity_views import sweep_missing_views" in src
