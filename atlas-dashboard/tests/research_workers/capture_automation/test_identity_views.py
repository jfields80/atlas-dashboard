"""PTF-CAPTURE-003E -- planning and attaching additional views.

The live half drives Chrome and is exercised by hand; everything decidable
without a browser is decided here: which strings would prove a missing field,
which scroll offset brings the most of them into one frame, and whether
attaching a view leaves the capture it belongs to ingestible.
"""

from __future__ import annotations

import hashlib
import json
import pathlib

import pytest

from services.research_workers.capture_automation.evidence_completeness import (
    FIELD_CITY, FIELD_HOTEL_NAME, FIELD_POSTAL_CODE, FIELD_PROPERTY_PHONE,
    FIELD_STATE, FIELD_STREET, assess_evidence,
)
from services.research_workers.capture_automation.identity_views import (
    ADDITIONAL_VIEWS_KEY, ViewAttachError, attach_view_to_capture, choose_frame,
    load_views_for_capture, observation_from_hit, observations_from_sidecar,
    plan_needles, probe_script,
)

from .conftest import make_png

OFFICIAL = ("https://www.marriott.com/en-us/hotels/"
            "cmhco-aloft-columbus-university-district/overview/")

EXPECTED = {
    FIELD_HOTEL_NAME: "Aloft Columbus University District",
    FIELD_STREET: "1295 Olentangy River Rd",
    FIELD_CITY: "Columbus",
    FIELD_STATE: "OH",
    FIELD_POSTAL_CODE: "43212",
    FIELD_PROPERTY_PHONE: "614-294-7500",
}


# --------------------------------------------------------------------------- #
# Needle planning.
# --------------------------------------------------------------------------- #

def test_street_plan_includes_the_spelled_out_suffix():
    """The seed abbreviates, the brand page spells it out. Hunting only the
    seed's form found nothing and reported a visible address as missing."""
    plan = plan_needles([FIELD_STREET], EXPECTED)
    assert "1295 Olentangy River Rd" in plan[FIELD_STREET]
    assert "1295 Olentangy River Road" in plan[FIELD_STREET]


def test_state_plan_expands_the_postal_code_to_the_rendered_name():
    """Marriott renders "Ohio". A bare "OH" needle would also match inside
    "OHIO" and inside unrelated words, so the expansion is explicit."""
    plan = plan_needles([FIELD_STATE], EXPECTED)
    assert plan[FIELD_STATE][0] == "Ohio"
    assert "OH" in plan[FIELD_STATE]


def test_phone_plan_covers_the_renderings_a_brand_page_uses():
    plan = plan_needles([FIELD_PROPERTY_PHONE], EXPECTED)
    for form in ("614-294-7500", "+1 614-294-7500", "(614) 294-7500"):
        assert form in plan[FIELD_PROPERTY_PHONE]


def test_name_plan_keeps_a_tail_needle_for_brand_line_insertion():
    """The page says "Aloft BY MARRIOTT Columbus University District", so the
    full seed string never appears verbatim beside the address."""
    plan = plan_needles([FIELD_HOTEL_NAME], EXPECTED)
    assert "Aloft Columbus University District" in plan[FIELD_HOTEL_NAME]
    assert "Columbus University District" in plan[FIELD_HOTEL_NAME]


def test_a_field_with_no_expected_value_is_not_hunted():
    """An empty needle matches everything, which would prove a field by
    accident -- the exact failure mode this module exists to prevent."""
    plan = plan_needles([FIELD_STREET, FIELD_CITY], {FIELD_CITY: "Columbus"})
    assert FIELD_STREET not in plan
    assert plan[FIELD_CITY] == ("Columbus",)


def test_probe_script_embeds_the_plan_as_json():
    js = probe_script(plan_needles([FIELD_CITY], EXPECTED))
    assert '"city": ["Columbus"]' in js.replace("'", '"')
    assert "display === 'none'" in js          # hidden text excluded at source


# --------------------------------------------------------------------------- #
# Framing.
# --------------------------------------------------------------------------- #

def test_choose_frame_covers_the_most_fields_it_can():
    hits = {
        FIELD_STREET: [{"pageTop": 5000, "pageBottom": 5048}],
        FIELD_CITY: [{"pageTop": 5000, "pageBottom": 5048}],
        FIELD_PROPERTY_PHONE: [{"pageTop": 5100, "pageBottom": 5140}],
        FIELD_HOTEL_NAME: [{"pageTop": 970, "pageBottom": 1037}],
    }
    top, covered = choose_frame(hits, viewport_h=1005)
    assert set(covered) == {FIELD_STREET, FIELD_CITY, FIELD_PROPERTY_PHONE}
    assert 4700 <= top <= 5000


def test_choose_frame_reports_only_what_actually_fits():
    """Two fields 4,000px apart cannot share a 1005px frame; claiming both
    would be the false confidence the gate is meant to remove."""
    hits = {
        FIELD_HOTEL_NAME: [{"pageTop": 970, "pageBottom": 1037}],
        FIELD_STREET: [{"pageTop": 5000, "pageBottom": 5048}],
    }
    top, covered = choose_frame(hits, viewport_h=1005)
    assert len(covered) == 1


def test_choose_frame_on_nothing_found():
    assert choose_frame({}, viewport_h=1005) == (0, ())


def test_observation_in_frame_follows_the_captured_viewport():
    inside = observation_from_hit(FIELD_STREET,
                                  {"needle": "1295 Olentangy River Road",
                                   "top": 390, "bottom": 438, "left": 127,
                                   "width": 460, "height": 48}, 1005)
    assert inside.in_frame is True and inside.visible is True
    outside = observation_from_hit(FIELD_STREET,
                                   {"needle": "1295 Olentangy River Road",
                                    "top": 1200, "bottom": 1248, "left": 127,
                                    "width": 460, "height": 48}, 1005)
    assert outside.in_frame is False
    assert outside.readable is False


# --------------------------------------------------------------------------- #
# Attachment.
# --------------------------------------------------------------------------- #

def _capture(tmp_path, name="capture.json"):
    payload = {
        "schema": "ptf-official-capture/1.0",
        "extension_version": "ptf-capture-003/1.0.0",
        "final_url": OFFICIAL, "requested_url": OFFICIAL,
        "title": "Aloft Columbus University District | Modern Hotel",
        "html": "<html><body>Pet Policy Pets Welcome</body></html>",
        "text": "Pet Policy Pets Welcome",
        "captured_at": "2026-08-01T14:16:19.949Z",
        "html_sha256": "a" * 64, "text_sha256": "b" * 64,
        "automation": {"controller_version": "x"},
    }
    p = tmp_path / name
    p.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    return p


def _sidecar(tmp_path, png_name="identity.png", url=OFFICIAL, proves=()):
    data = make_png(1408, 1005)
    (tmp_path / png_name).write_bytes(data)
    return {
        "png_file": png_name,
        "png_sha256": hashlib.sha256(data).hexdigest(),
        "png_bytes": len(data), "png_width": 1408, "png_height": 1005,
        "final_url": url, "captured_at": "2026-08-01T21:15:04.664Z",
        "proves_fields": list(proves),
        "field_observations": [
            {"field": FIELD_STREET, "text": "1295 Olentangy River Road",
             "visible": True, "in_frame": True,
             "box": {"x": 127, "y": 390, "width": 460, "height": 48}},
        ],
    }


def test_attaching_a_view_is_additive_and_leaves_the_capture_ingestible(tmp_path):
    from services.research_workers.operator_capture import validate_capture

    cap = _capture(tmp_path)
    before = json.loads(cap.read_text("utf-8"))
    # The invariant only means something if the capture ingested to begin with.
    assert validate_capture(before)[0] is True
    attach_view_to_capture(cap, _sidecar(tmp_path))
    after = json.loads(cap.read_text("utf-8"))

    for key in ("html", "text", "html_sha256", "text_sha256", "final_url",
                "captured_at"):
        assert after[key] == before[key], key
    assert len(after["automation"][ADDITIONAL_VIEWS_KEY]) == 1
    assert validate_capture(after)[0] is True


def test_attaching_the_same_view_twice_is_a_no_op(tmp_path):
    cap = _capture(tmp_path)
    side = _sidecar(tmp_path)
    attach_view_to_capture(cap, side)
    attach_view_to_capture(cap, side)
    payload = json.loads(cap.read_text("utf-8"))
    assert len(payload["automation"][ADDITIONAL_VIEWS_KEY]) == 1


def test_a_view_of_another_page_cannot_be_attached(tmp_path):
    cap = _capture(tmp_path)
    other = _sidecar(tmp_path, url="https://www.marriott.com/en-us/hotels/"
                                   "cmhea-aloft-columbus-easton/overview/")
    with pytest.raises(ViewAttachError) as exc:
        attach_view_to_capture(cap, other)
    assert "view_page_differs_from_capture" in str(exc.value)


def test_a_view_without_a_digest_cannot_be_attached(tmp_path):
    cap = _capture(tmp_path)
    side = _sidecar(tmp_path)
    side["png_sha256"] = "not-a-digest"
    with pytest.raises(ViewAttachError):
        attach_view_to_capture(cap, side)


def test_attached_views_load_back_as_assessable_evidence(tmp_path):
    cap = _capture(tmp_path)
    side = _sidecar(tmp_path, proves=[FIELD_STREET])
    (tmp_path / "identity.view.json").write_text(json.dumps(side), encoding="utf-8")
    attach_view_to_capture(cap, side)

    views = load_views_for_capture(cap)
    assert len(views) == 1
    assert views[0].observations[0].field == FIELD_STREET
    report = assess_evidence(views, official_url=OFFICIAL)
    # one view proves one field; the gate still refuses the rest
    assert report.proven[FIELD_STREET][1] == "1295 Olentangy River Road"
    assert report.complete is False


def test_observations_from_sidecar_defaults_to_visible_in_frame():
    obs = observations_from_sidecar({"field_observations": [
        {"field": FIELD_CITY, "text": "Columbus"}]})
    assert obs[0].visible is True and obs[0].in_frame is True
    assert obs[0].readable is True


# --------------------------------------------------------------------------- #
# The sweep loop, driven by a fake page.
# --------------------------------------------------------------------------- #

class FakePage:
    """A page with fields at known page-y offsets, some of which never paint.

    Mimics the two behaviours that broke real runs: sections that do not exist
    until scrolled to, and text that is in the DOM but invisible.
    """

    #: What each field actually paints. Must agree with what the queue expects,
    #: because a value that contradicts the queue is correctly refused as
    #: evidence -- a fake emitting placeholder strings would test nothing.
    RENDERS = {
        "hotel_name": "Aloft by Marriott Columbus University District",
        "street_address": "1295 Olentangy River Road",
        "city": "Columbus", "state": "Ohio", "postal_code": "43212",
        "property_phone": "614-294-7500",
        "pet_policy_text": "Pet Policy Pets Welcome",
    }

    def __init__(self, layout, viewport=(1408, 1005), materialise_at=0):
        self.layout = layout            # field -> (pageTop, height) or None
        self._vw, self._vh = viewport
        self.materialise_at = materialise_at
        self.scroll_y = 0
        self.shots = 0
        # Lazy sections LATCH: once a page has rendered one, scrolling back up
        # does not un-render it. Modelling it as a live threshold instead made
        # the fake de-render content no real page de-renders.
        self.materialised = materialise_at <= 0

    def viewport(self):
        return (self._vw, self._vh)

    def screenshot_png(self):
        # Distinct bytes per shot. Two frames of a real page never come out
        # byte-identical, and identical fakes made the sha-dedup (correctly)
        # treat the second view as a re-attachment of the first.
        self.shots += 1
        return make_png(self._vw, self._vh - self.shots)

    def evaluate(self, script):
        if script.startswith("window.scrollTo"):
            self.scroll_y = int(script.split(",")[1].strip(" )"))
            if self.scroll_y >= self.materialise_at:
                self.materialised = True
            return None
        out = {"_viewportH": self._vh, "_viewportW": self._vw,
               "_scrollY": self.scroll_y}
        for field, spec in self.layout.items():
            if field not in script or spec is None:
                out.setdefault(field, [])
                continue
            if not self.materialised:
                out[field] = []             # section not rendered yet
                continue
            top, height = spec
            rendered = self.RENDERS[field]
            out[field] = [{
                "needle": rendered, "text": rendered,
                "context": "", "top": top - self.scroll_y,
                "bottom": top + height - self.scroll_y, "left": 100,
                "width": 400, "height": height,
                "pageTop": top, "pageBottom": top + height}]
        return out


def _writer(tmp_path, url=OFFICIAL):
    written = []

    def write_view(png, observations, scroll_y, viewport):
        from services.research_workers.capture_automation.capture_writer import (
            png_dimensions,
        )
        name = "sweep-%d.png" % (len(written) + 1)
        (tmp_path / name).write_bytes(png)
        w, h = png_dimensions(png)          # record what was written, not what was asked
        side = {"png_file": name, "png_sha256": hashlib.sha256(png).hexdigest(),
                "png_bytes": len(png), "png_width": w,
                "png_height": h, "final_url": url,
                "captured_at": "2026-08-01T21:%02d:00.000Z" % len(written),
                "scroll_y": scroll_y,
                "field_observations": [o.to_dict() for o in observations],
                "proves_fields": sorted({o.field for o in observations
                                         if o.readable})}
        written.append(side)
        (tmp_path / (name[:-4] + ".view.json")).write_text(
            json.dumps(side), encoding="utf-8")
        return side

    return write_view, written


def test_sweep_captures_until_the_package_is_complete(tmp_path):
    from services.research_workers.capture_automation.identity_views import (
        sweep_missing_views,
    )
    cap = _capture(tmp_path)
    # policy sits 4,000px from the identity block: one frame cannot hold both,
    # so a complete package REQUIRES more than one view.
    page = FakePage({
        "hotel_name": (5000, 40), "street_address": (5050, 40),
        "city": (5050, 40), "state": (5050, 40), "postal_code": (5050, 40),
        "property_phone": (5120, 30),
        "pet_policy_text": (1000, 60),
    })
    write_view, written = _writer(tmp_path)
    expected = dict(EXPECTED, pet_policy_text="Pet Policy Pets Welcome")
    result = sweep_missing_views(page, capture_path=cap, official_url=OFFICIAL,
                                 expected=expected, write_view=write_view)

    assert result.complete is True
    assert len(written) >= 2                     # could not be done in one frame
    assert page.shots == len(written)


def test_sweep_stops_when_the_page_simply_does_not_show_a_field(tmp_path):
    """Not every property page publishes a phone. The sweep must stop and say
    so rather than loop taking screenshots of a brand site forever."""
    from services.research_workers.capture_automation.identity_views import (
        sweep_missing_views,
    )
    cap = _capture(tmp_path)
    page = FakePage({
        "hotel_name": (5000, 40), "street_address": (5050, 40),
        "city": (5050, 40), "state": (5050, 40), "postal_code": (5050, 40),
        "property_phone": None,                  # never rendered
        "pet_policy_text": (5100, 60),
    })
    write_view, written = _writer(tmp_path)
    expected = dict(EXPECTED, pet_policy_text="Pet Policy Pets Welcome")
    result = sweep_missing_views(page, capture_path=cap, official_url=OFFICIAL,
                                 expected=expected, write_view=write_view)

    assert result.complete is False
    assert "property_phone" in result.report.missing
    assert any("page_does_not_show" in n for n in result.notes)
    assert len(written) <= 6


def test_sweep_scrolls_to_materialise_a_lazy_section(tmp_path):
    """The Aloft location block does not exist in the DOM at scroll 0. A sweep
    that trusted the first probe would report a visible address as missing."""
    from services.research_workers.capture_automation.identity_views import (
        sweep_missing_views,
    )
    cap = _capture(tmp_path)
    page = FakePage({
        "hotel_name": (5000, 40), "street_address": (5050, 40),
        "city": (5050, 40), "state": (5050, 40), "postal_code": (5050, 40),
        "property_phone": (5120, 30), "pet_policy_text": (1000, 60),
    }, materialise_at=2100)
    write_view, written = _writer(tmp_path)
    expected = dict(EXPECTED, pet_policy_text="Pet Policy Pets Welcome")
    result = sweep_missing_views(page, capture_path=cap, official_url=OFFICIAL,
                                 expected=expected, write_view=write_view)
    assert result.complete is True


def test_sweep_is_bounded(tmp_path):
    from services.research_workers.capture_automation.identity_views import (
        sweep_missing_views,
    )
    cap = _capture(tmp_path)
    # every field paints, but each is 3,000px from the next, so no small number
    # of frames can ever cover them all
    layout = {f: (i * 3000, 40) for i, f in enumerate(
        ("hotel_name", "street_address", "city", "state", "postal_code",
         "property_phone", "pet_policy_text"))}
    page = FakePage(layout)
    write_view, written = _writer(tmp_path)
    expected = dict(EXPECTED, pet_policy_text="Pet Policy Pets Welcome")
    result = sweep_missing_views(page, capture_path=cap, official_url=OFFICIAL,
                                 expected=expected, write_view=write_view,
                                 max_views=3)
    assert result.complete is False
    assert len(written) <= 3


# --------------------------------------------------------------------------- #
# Occlusion: inside the viewport is not the same as inside the picture.
# --------------------------------------------------------------------------- #

def test_text_behind_a_sticky_header_is_not_in_frame():
    """The real failure this guard exists for: the Aloft address sat at
    client-y 60 under a 165px sticky bar. Its rect was inside the viewport and
    the pixels were not in the screenshot, and the gate called it proven."""
    hit = {"needle": "1295 Olentangy River Road", "top": 60, "bottom": 108,
           "left": 127, "width": 460, "height": 48}
    assert observation_from_hit(FIELD_STREET, hit, 1005, 0).in_frame is True
    occluded = observation_from_hit(FIELD_STREET, hit, 1005, 165)
    assert occluded.in_frame is False
    assert occluded.readable is False


def test_choose_frame_leaves_room_for_the_sticky_bar():
    hits = {FIELD_STREET: [{"pageTop": 5000, "pageBottom": 5048}]}
    plain, _ = choose_frame(hits, 1005, 0)
    shifted, covered = choose_frame(hits, 1005, 165)
    assert shifted < plain                       # scrolls further up
    assert covered == (FIELD_STREET,)
    # and the field genuinely clears the bar in the chosen frame
    assert 5000 - shifted >= 165


def test_sweep_frames_below_an_occluding_header(tmp_path):
    """With a sticky bar declared, the sweep must still land a frame in which
    every field is genuinely visible."""
    from services.research_workers.capture_automation.identity_views import (
        sweep_missing_views,
    )

    class StickyPage(FakePage):
        OCCLUDED = 165

        def evaluate(self, script):
            out = super().evaluate(script)
            if isinstance(out, dict):
                out["_occludedTop"] = self.OCCLUDED
            return out

    cap = _capture(tmp_path)
    page = StickyPage({
        "hotel_name": (5000, 40), "street_address": (5050, 40),
        "city": (5050, 40), "state": (5050, 40), "postal_code": (5050, 40),
        "property_phone": (5120, 30), "pet_policy_text": (1000, 60),
    })
    write_view, written = _writer(tmp_path)
    expected = dict(EXPECTED, pet_policy_text="Pet Policy Pets Welcome")
    result = sweep_missing_views(page, capture_path=cap, official_url=OFFICIAL,
                                 expected=expected, write_view=write_view)
    assert result.complete is True
    for side in written:
        for obs in side["field_observations"]:
            if obs["in_frame"]:
                assert obs["box"]["y"] >= StickyPage.OCCLUDED, obs


def test_frame_shortfall_measures_against_the_expanded_bar():
    """Marriott's header is 49px at rest and 169px scrolled. A frame aimed
    with the resting height leaves the address under the expanded bar."""
    from services.research_workers.capture_automation.identity_views import (
        frame_shortfall,
    )
    probe = {FIELD_STREET: [{"top": 44, "bottom": 92}],
             FIELD_CITY: [{"top": 44, "bottom": 92}]}
    assert frame_shortfall(probe, [FIELD_STREET, FIELD_CITY], 169) == 145
    # already clear of the bar
    clear = {FIELD_STREET: [{"top": 400, "bottom": 448}]}
    assert frame_shortfall(clear, [FIELD_STREET], 169) == 0


def test_frame_shortfall_ignores_hits_above_the_frame():
    """A field scrolled off the top is not the one to correct against; doing
    so would chase it upward forever."""
    from services.research_workers.capture_automation.identity_views import (
        frame_shortfall,
    )
    probe = {FIELD_STREET: [{"top": -3900, "bottom": -3850},
                            {"top": 300, "bottom": 348}]}
    assert frame_shortfall(probe, [FIELD_STREET], 169) == 0


def test_sweep_corrects_for_a_header_that_grows_after_scrolling(tmp_path):
    from services.research_workers.capture_automation.identity_views import (
        sweep_missing_views,
    )

    class GrowingHeaderPage(FakePage):
        """49px at the top of the page, 169px once scrolled -- the real one."""

        def evaluate(self, script):
            out = super().evaluate(script)
            if isinstance(out, dict):
                out["_occludedTop"] = 49 if self.scroll_y == 0 else 169
            return out

    cap = _capture(tmp_path)
    page = GrowingHeaderPage({
        "hotel_name": (5000, 40), "street_address": (5050, 40),
        "city": (5050, 40), "state": (5050, 40), "postal_code": (5050, 40),
        "property_phone": (5120, 30), "pet_policy_text": (1000, 60),
    })
    write_view, written = _writer(tmp_path)
    expected = dict(EXPECTED, pet_policy_text="Pet Policy Pets Welcome")
    result = sweep_missing_views(page, capture_path=cap, official_url=OFFICIAL,
                                 expected=expected, write_view=write_view)
    assert result.complete is True
    for side in written:
        for obs in side["field_observations"]:
            if obs["in_frame"]:
                assert obs["box"]["y"] >= 169, obs
