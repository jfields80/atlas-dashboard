"""Writing a capture, and validating what was written.

The validators read back from disk rather than trusting what the writer
believed it wrote, so these tests corrupt real files and assert the corruption
is caught.
"""

from __future__ import annotations

import hashlib
import json
import pathlib

import pytest

from services.research_workers.capture_automation.capture_writer import (
    AUTOMATION_VERSION, CaptureWriteError, build_payload, capture_stem,
    decode_screenshot, png_dimensions, png_is_complete, sha256_hex,
    write_capture,
)
from services.research_workers.capture_automation.contracts import (
    BoxModel, PolicyLocation,
)
from services.research_workers.capture_automation.policy_locator import locate_policy
from services.research_workers.capture_automation.validators import (
    policy_in_frame, validate_written_capture, visible_fraction,
)
from services.research_workers.operator_capture import CAPTURE_SCHEMA

from .conftest import load_fixture, make_png, snapshot_for


def _write(tmp_path, name="marriott-cmham.json", **kw):
    dom = snapshot_for(name)
    loc = locate_policy(dom)
    payload = build_payload(dom, captured_at="2026-07-31T12:00:00.000Z",
                            requested_url=dom.final_url, policy=loc,
                            policy_box=kw.get("box"),
                            viewport=kw.get("viewport", (1440, 1000)))
    png = kw.get("png", make_png(320, 200))
    stem = capture_stem(dom.final_url, "2026-07-31T12:00:00.000Z")
    return write_capture(payload, png, output_dir=tmp_path / "captures", stem=stem)


class TestPayloadShape:
    def test_matches_the_ingestion_contract(self):
        dom = snapshot_for("marriott-cmham.json")
        payload = build_payload(dom, captured_at="2026-07-31T12:00:00.000Z",
                                requested_url=dom.final_url)
        assert payload["schema"] == CAPTURE_SCHEMA
        for field in ("captured_at", "final_url", "title", "html", "text",
                      "extension_version"):
            assert field in payload

    def test_hashes_are_of_the_content_carried(self):
        dom = snapshot_for("marriott-cmhaw.json")
        payload = build_payload(dom, captured_at="t", requested_url="u")
        assert payload["html_sha256"] == sha256_hex(payload["html"])
        assert payload["text_sha256"] == sha256_hex(payload["text"])

    def test_it_carries_no_forbidden_key(self):
        from services.research_workers.operator_capture import validate_capture
        dom = snapshot_for("hilton-cmhaphx.json")
        payload = build_payload(dom, captured_at="2026-07-31T12:00:00.000Z",
                                requested_url=dom.final_url)
        ok, reason = validate_capture(payload)
        assert ok, reason

    def test_automation_block_never_carries_an_affirmation(self):
        """The load-bearing boundary: a machine may not vouch for what it
        gathered."""
        dom = snapshot_for("marriott-cmham.json")
        payload = build_payload(dom, captured_at="t", requested_url="u")
        assert payload["automation"]["affirmation"] is None
        blob = json.dumps(payload)
        for field in ("address_confirmed", "phone_confirmed", "operator_id",
                      "attested_at"):
            assert field not in blob

    def test_provenance_says_it_was_a_controller(self):
        dom = snapshot_for("marriott-cmham.json")
        payload = build_payload(dom, captured_at="t", requested_url="u")
        assert payload["extension_version"] == AUTOMATION_VERSION
        assert "controller" in payload["capture_note"].lower()
        assert "not an operator affirmation" in payload["capture_note"].lower()


class TestPng:
    def test_dimensions_are_read_from_ihdr(self):
        assert png_dimensions(make_png(640, 480)) == (640, 480)

    def test_non_png_is_refused(self):
        with pytest.raises(CaptureWriteError, match="not_a_png"):
            png_dimensions(b"GIF89a" + b"\x00" * 40)

    def test_truncated_header_is_refused(self):
        with pytest.raises(CaptureWriteError):
            png_dimensions(make_png(10, 10)[:12])

    def test_complete_png_has_iend(self):
        assert png_is_complete(make_png(8, 8))
        assert not png_is_complete(make_png(8, 8)[:-20])

    def test_base64_and_data_url_both_decode(self):
        import base64
        raw = make_png(4, 4)
        b64 = base64.b64encode(raw).decode()
        assert decode_screenshot(b64) == raw
        assert decode_screenshot("data:image/png;base64," + b64) == raw


class TestWriting:
    def test_pair_is_written(self, tmp_path):
        jp, pp, png_hash, w, h = _write(tmp_path)
        assert jp.exists() and pp.exists()
        assert jp.stem == pp.stem
        assert (w, h) == (320, 200)
        assert png_hash == hashlib.sha256(pp.read_bytes()).hexdigest()

    def test_missing_screenshot_writes_nothing(self, tmp_path):
        """The pairing rule: never a JSON with no partner."""
        with pytest.raises(CaptureWriteError, match="screenshot_missing"):
            _write(tmp_path, png=b"")
        assert not list((tmp_path / "captures").glob("*")) or \
            not list((tmp_path / "captures").glob("*.json"))

    def test_invalid_png_writes_nothing(self, tmp_path):
        with pytest.raises(CaptureWriteError):
            _write(tmp_path, png=b"not a png at all")
        assert not list((tmp_path / "captures").glob("*.json"))

    def test_refuses_to_overwrite(self, tmp_path):
        _write(tmp_path)
        with pytest.raises(CaptureWriteError, match="already_exists"):
            _write(tmp_path)

    def test_path_traversal_is_refused(self, tmp_path):
        dom = snapshot_for("marriott-cmham.json")
        payload = build_payload(dom, captured_at="t", requested_url="u")
        with pytest.raises(CaptureWriteError, match="path_escapes"):
            write_capture(payload, make_png(4, 4),
                          output_dir=tmp_path / "captures",
                          stem="../../escape")

    def test_stem_is_derived_from_the_url(self):
        stem = capture_stem("https://www.marriott.com/en-us/hotels/cmham-x/overview/",
                            "2026-07-31T12:00:00.000Z")
        assert "marriott" in stem and "cmham" in stem
        assert ":" not in stem


class TestGeometry:
    def test_fully_visible_box(self):
        box = BoxModel(x=0, y=100, width=600, height=200, scroll_y=0)
        assert visible_fraction(box, 1000) == 1.0
        assert policy_in_frame(box, 1000)

    def test_box_scrolled_off_the_top(self):
        box = BoxModel(x=0, y=0, width=600, height=200, scroll_y=500)
        assert visible_fraction(box, 1000) == 0.0
        assert not policy_in_frame(box, 1000)

    def test_box_below_the_fold(self):
        box = BoxModel(x=0, y=5000, width=600, height=200, scroll_y=0)
        assert visible_fraction(box, 1000) == 0.0
        assert not policy_in_frame(box, 1000)

    def test_half_visible_box_is_the_boundary(self):
        # 200-tall box whose top sits 900 down a 1000 viewport -> 100 visible.
        box = BoxModel(x=0, y=900, width=600, height=200, scroll_y=0)
        assert visible_fraction(box, 1000) == pytest.approx(0.5)
        assert policy_in_frame(box, 1000)

    def test_mostly_off_screen_box_is_refused(self):
        box = BoxModel(x=0, y=960, width=600, height=200, scroll_y=0)
        assert visible_fraction(box, 1000) < 0.5
        assert not policy_in_frame(box, 1000)

    def test_no_box_is_never_in_frame(self):
        assert not policy_in_frame(None, 1000)


class TestValidatingWhatWasWritten:
    def test_a_good_capture_validates(self, tmp_path):
        jp, pp, *_ = _write(tmp_path)
        assert validate_written_capture(jp, pp).ok

    def test_missing_png_fails(self, tmp_path):
        jp, pp, *_ = _write(tmp_path)
        pp.unlink()
        result = validate_written_capture(jp, pp)
        assert not result.ok and "png_missing" in result.problems

    def test_tampered_text_is_caught_by_rehashing(self, tmp_path):
        jp, pp, *_ = _write(tmp_path)
        payload = json.loads(jp.read_text("utf-8"))
        payload["text"] = payload["text"] + " ...and pets are free!"
        jp.write_text(json.dumps(payload), encoding="utf-8")
        result = validate_written_capture(jp, pp)
        assert not result.ok
        assert "text_sha256_mismatch" in result.problems

    def test_truncated_png_is_caught(self, tmp_path):
        jp, pp, *_ = _write(tmp_path)
        pp.write_bytes(pp.read_bytes()[:60])
        result = validate_written_capture(jp, pp)
        assert not result.ok
        assert any("png" in p for p in result.problems)

    def test_challenge_content_is_caught(self, tmp_path):
        jp, pp, *_ = _write(tmp_path)
        payload = json.loads(jp.read_text("utf-8"))
        payload["text"] = "Please verify you are a human. Complete the CAPTCHA."
        payload["text_sha256"] = sha256_hex(payload["text"])
        jp.write_text(json.dumps(payload), encoding="utf-8")
        result = validate_written_capture(jp, pp)
        assert not result.ok
        assert result.reason == "CAPTCHA_OR_CHALLENGE"

    def test_thin_page_is_caught(self, tmp_path):
        jp, pp, *_ = _write(tmp_path)
        payload = json.loads(jp.read_text("utf-8"))
        payload["text"] = "tiny"
        payload["text_sha256"] = sha256_hex(payload["text"])
        jp.write_text(json.dumps(payload), encoding="utf-8")
        result = validate_written_capture(jp, pp)
        assert not result.ok
        assert result.reason == "INSUFFICIENT_TEXT"

    def test_forbidden_key_is_caught(self, tmp_path):
        jp, pp, *_ = _write(tmp_path)
        payload = json.loads(jp.read_text("utf-8"))
        payload["cookies"] = {"session": "secret"}
        jp.write_text(json.dumps(payload), encoding="utf-8")
        result = validate_written_capture(jp, pp)
        assert not result.ok
        assert result.reason == "FORBIDDEN_CONTENT"

    def test_policy_off_screen_is_caught(self, tmp_path):
        jp, pp, *_ = _write(tmp_path)
        result = validate_written_capture(
            jp, pp, policy_box=BoxModel(x=0, y=9000, width=600, height=300),
            viewport_height=1000.0)
        assert not result.ok
        assert result.reason == "POLICY_OFF_SCREEN"

    def test_duplicate_is_detected_by_text_hash(self, tmp_path):
        jp, pp, *_ = _write(tmp_path)
        digest = json.loads(jp.read_text("utf-8"))["text_sha256"]
        result = validate_written_capture(
            jp, pp, seen_text_hashes={digest: "an-earlier-hotel"})
        assert not result.ok
        assert result.reason == "DUPLICATE_CAPTURE"
        assert result.duplicate_of == "an-earlier-hotel"

    def test_the_real_duplicate_pair_in_the_corpus_hashes_identically(self):
        """Two captures of the same Marriott page, taken 24ms apart, really are
        the same page -- so duplicate detection has a genuine case to catch."""
        a = load_fixture("marriott-cmhap.json")
        b = load_fixture("marriott-cmhap-b.json")
        assert a["text_sha256"] == b["text_sha256"]

    def test_private_params_with_no_clean_canonical_are_refused(self, tmp_path):
        jp, pp, *_ = _write(tmp_path)
        payload = json.loads(jp.read_text("utf-8"))
        payload["final_url"] = payload["final_url"] + "?sessionToken=abc123"
        payload["canonical_url"] = ""
        jp.write_text(json.dumps(payload), encoding="utf-8")
        result = validate_written_capture(jp, pp)
        assert not result.ok
        assert result.reason == "PRIVATE_PARAMS_IN_CITATION"

    def test_private_params_are_forgiven_when_canonical_is_clean(self, tmp_path):
        """Hilton captures arrive with WT.mc_id from a marketing link; the
        page's own canonical URL is clean and is what gets cited."""
        jp, pp, *_ = _write(tmp_path, name="hilton-cmhaphx.json")
        payload = json.loads(jp.read_text("utf-8"))
        clean = payload["final_url"]
        payload["final_url"] = clean + "?WT.mc_id=zlada0ww1hi2psh3ggl"
        payload["canonical_url"] = clean
        jp.write_text(json.dumps(payload), encoding="utf-8")
        assert validate_written_capture(jp, pp).ok
