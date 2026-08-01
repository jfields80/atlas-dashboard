"""PTF-CAPTURE-003E -- go and get the missing evidence instead of asking a
human to imagine it.

``evidence_completeness`` decides a package is short of, say, the property
phone. This module turns that verdict into action: work out what strings would
prove the missing fields, take one or more additional views of the SAME
official page until they are visibly in frame, validate each image, and attach
it to the capture that already exists.

Two rules shape the design:

  * an additional view is never an independent capture. It carries no policy
    text of its own and it cannot introduce a second source -- it is another
    photograph of the page already captured, and it is recorded against that
    capture's file so the two can never drift apart;
  * what the prober reports is what the screenshot can show. Boxes are read
    AFTER the scroll that produced the image, and an element that does not
    paint is never reported as visible -- otherwise this module would
    manufacture exactly the false confidence the gate exists to remove.

The planning half is pure and tested. The capturing half drives a visible
browser under the same doctrine as every other capture: no stealth, no UA
spoofing, no cookie-banner dismissal, no credentialed browsing.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
from typing import Dict, Mapping, Optional, Sequence, Tuple

from .evidence_completeness import (
    FIELD_CITY, FIELD_HOTEL_NAME, FIELD_POLICY_TEXT, FIELD_POSTAL_CODE,
    FIELD_PROPERTY_PHONE, FIELD_STATE, FIELD_STREET, EvidenceView,
    FieldObservation, name_variants, national_digits, phone_variants,
    state_variants, street_variants,
)



def plan_needles(fields: Sequence[str],
                 expected: Mapping[str, str]) -> Dict[str, Tuple[str, ...]]:
    """Field -> the strings whose presence on screen would prove it.

    Returns only fields it can actually hunt: a field the queue has no expected
    value for is left out rather than hunted with an empty needle, which would
    match everything.
    """
    plan: Dict[str, Tuple[str, ...]] = {}
    for f in fields:
        if f == FIELD_HOTEL_NAME:
            name = (expected.get(FIELD_HOTEL_NAME) or "").strip()
            if name:
                # Brands insert their own line ("Aloft BY MARRIOTT Columbus
                # ..."), so the distinctive tail is a better needle than the
                # full seed string, which the page may never render verbatim.
                plan[f] = name_variants(name)
        elif f == FIELD_STREET:
            v = street_variants(expected.get(FIELD_STREET) or "")
            if v:
                plan[f] = v
        elif f == FIELD_STATE:
            vals = state_variants(expected.get(FIELD_STATE) or "")
            if vals:
                plan[f] = vals
        elif f == FIELD_PROPERTY_PHONE:
            v = phone_variants(expected.get(FIELD_PROPERTY_PHONE) or "")
            if v:
                plan[f] = v
        elif f in (FIELD_CITY, FIELD_POSTAL_CODE):
            v = (expected.get(f) or "").strip()
            if v:
                plan[f] = (v,)
        elif f == FIELD_POLICY_TEXT:
            v = (expected.get(FIELD_POLICY_TEXT) or "").strip()
            if v:
                plan[f] = (v[:60],)
    return plan


# --------------------------------------------------------------------------- #
# Attaching a view to the capture it belongs to.
# --------------------------------------------------------------------------- #

ADDITIONAL_VIEWS_KEY = "additional_views"


class ViewAttachError(RuntimeError):
    """The view cannot be attached to that capture."""


def attach_view_to_capture(capture_path, sidecar: Mapping,
                           *, write=True) -> dict:
    """Record an additional view against its capture JSON, additively.

    Additive by design: the capture's html, text and their hashes are never
    touched, so a capture that ingested before attachment ingests identically
    after it. Attaching the same image twice is a no-op rather than a
    duplicate, because a re-run of the completeness sweep is normal.
    """
    path = pathlib.Path(capture_path)
    payload = json.loads(path.read_text("utf-8"))

    final_url = str(payload.get("final_url") or "")
    view_url = str(sidecar.get("final_url") or sidecar.get("page_url") or "")
    if final_url.rstrip("/") != view_url.rstrip("/"):
        raise ViewAttachError("view_page_differs_from_capture:%s" % view_url)
    sha = str(sidecar.get("png_sha256") or "")
    if not re.fullmatch(r"[0-9a-f]{64}", sha):
        raise ViewAttachError("view_sha256_not_a_digest")

    automation = payload.setdefault("automation", {})
    views = automation.setdefault(ADDITIONAL_VIEWS_KEY, [])
    if any(str(v.get("png_sha256")) == sha for v in views):
        return payload                       # already attached; nothing to do

    views.append({
        "png_file": sidecar.get("png_file"),
        "png_sha256": sha,
        "png_bytes": sidecar.get("png_bytes"),
        "png_width": sidecar.get("png_width"),
        "png_height": sidecar.get("png_height"),
        "captured_at": sidecar.get("captured_at"),
        "final_url": view_url,
        "proves_fields": list(sidecar.get("proves_fields") or []),
        "note": ("An additional VIEW of this same page. Not an independent "
                 "capture and never a second source of policy text."),
    })
    if write:
        path.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    return payload


def observations_from_sidecar(sidecar: Mapping) -> Tuple[FieldObservation, ...]:
    """Rebuild the field observations a view recorded."""
    out = []
    for raw in sidecar.get("field_observations") or []:
        out.append(FieldObservation(
            field=str(raw.get("field") or ""),
            text=str(raw.get("text") or ""),
            visible=bool(raw.get("visible", True)),
            in_frame=bool(raw.get("in_frame", True)),
            context=str(raw.get("context") or ""),
            box=dict(raw.get("box") or {}),
        ))
    return tuple(out)


def load_views_for_capture(capture_path) -> Tuple[EvidenceView, ...]:
    """Every attached view of a capture, as evidence the gate can assess."""
    path = pathlib.Path(capture_path)
    payload = json.loads(path.read_text("utf-8"))
    directory = path.parent
    out = []
    for v in (payload.get("automation") or {}).get(ADDITIONAL_VIEWS_KEY) or []:
        side_path = directory / (str(v.get("png_file") or "")[:-4] + ".view.json")
        sidecar = json.loads(side_path.read_text("utf-8")) if side_path.exists() else dict(v)
        out.append(EvidenceView(
            png_path=str(directory / str(v.get("png_file") or "")),
            png_sha256=str(v.get("png_sha256") or ""),
            png_bytes=int(v.get("png_bytes") or 0),
            png_width=int(v.get("png_width") or 0),
            png_height=int(v.get("png_height") or 0),
            page_url=str(v.get("final_url") or ""),
            captured_at=str(v.get("captured_at") or ""),
            observations=observations_from_sidecar(sidecar),
        ))
    return tuple(out)


# --------------------------------------------------------------------------- #
# The DOM probe. Shared by the live capturer and by tests through a fake.
# --------------------------------------------------------------------------- #

#: Returns, for each needle, every element that PAINTS it -- deepest painter
#: only, zero-area and display:none excluded at source. An element that does
#: not paint is simply absent from the result; it is never returned with
#: visible=false, because "we looked and there was nothing to see" and "there
#: is text here the human cannot read" are different findings and only the
#: latter belongs in a rejection list.
PROBE_JS = """
(() => {
  const want = %s;
  const out = {};
  for (const [field, needles] of Object.entries(want)) {
    const hits = [];
    for (const needle of needles) {
      const w = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
      while (w.nextNode()) {
        const el = w.currentNode;
        const t = el.innerText || '';
        if (t.indexOf(needle) === -1) continue;
        let deeper = false;
        for (const c of el.children) {
          if ((c.innerText || '').indexOf(needle) !== -1) { deeper = true; break; }
        }
        if (deeper) continue;
        const style = window.getComputedStyle(el);
        if (style.display === 'none' || style.visibility === 'hidden'
            || parseFloat(style.opacity || '1') === 0) continue;
        const r = el.getBoundingClientRect();
        if (r.width <= 0 || r.height <= 0) continue;
        const parent = el.parentElement;
        hits.push({needle: needle, text: t.trim().slice(0, 200),
                   context: ((parent && parent.innerText) || '').trim().slice(0, 200),
                   top: Math.round(r.top), bottom: Math.round(r.bottom),
                   left: Math.round(r.left), width: Math.round(r.width),
                   height: Math.round(r.height),
                   pageTop: Math.round(r.top + window.scrollY),
                   pageBottom: Math.round(r.bottom + window.scrollY)});
      }
    }
    hits.sort((a, b) => a.pageTop - b.pageTop);
    out[field] = hits;
  }
  // How much of the top of the viewport an opaque sticky/fixed bar covers.
  // Text under it is inside the viewport RECTANGLE and invisible in the
  // SCREENSHOT -- the Aloft address sat at client-y 60 behind a 165px header
  // and the gate called it proven. Occluded is hidden.
  let occluded = 0;
  for (const el of document.body.querySelectorAll('*')) {
    const st = window.getComputedStyle(el);
    if (st.position !== 'fixed' && st.position !== 'sticky') continue;
    if (st.visibility === 'hidden' || st.display === 'none') continue;
    const r = el.getBoundingClientRect();
    if (r.top > 4 || r.bottom <= 0) continue;          // not pinned to the top
    if (r.width < window.innerWidth * 0.6) continue;   // not a full-width bar
    occluded = Math.max(occluded, Math.round(r.bottom));
  }
  out._occludedTop = occluded;
  out._viewportH = window.innerHeight;
  out._viewportW = window.innerWidth;
  out._scrollY = Math.round(window.scrollY);
  return out;
})()
"""


def probe_script(plan: Mapping[str, Sequence[str]]) -> str:
    return PROBE_JS % json.dumps({k: list(v) for k, v in plan.items()})


def observation_from_hit(field: str, hit: Mapping, viewport_h: int,
                         occluded_top: int = 0) -> FieldObservation:
    """One probe hit, as evidence -- in_frame decided by the captured viewport.

    ``occluded_top`` is the height of any sticky bar pinned over the top of
    the frame. Text beneath it is in the viewport and absent from the picture,
    so it is not in frame.
    """
    return FieldObservation(
        field=field,
        text=str(hit.get("needle") or hit.get("text") or ""),
        visible=True,                       # the probe only returns painters
        in_frame=bool(hit.get("top", -1) >= max(0, occluded_top)
                      and hit.get("bottom", viewport_h + 1) <= viewport_h),
        context=str(hit.get("context") or ""),
        box={"x": hit.get("left", 0), "y": hit.get("top", 0),
             "width": hit.get("width", 0), "height": hit.get("height", 0)},
    )


def frame_shortfall(probe_result: Mapping, fields: Sequence[str],
                    occluded_top: int, margin: int = 20) -> int:
    """Pixels the frame must scroll UP so nothing sits under the sticky bar.

    Marriott's header is 49px at rest and 169px once the page is scrolled, so
    an offset computed from the resting height puts the address under the
    expanded bar. Measuring after the move and correcting is the only honest
    way round it -- the occlusion is not knowable before the scroll happens.
    """
    highest = None
    for f in fields:
        for hit in probe_result.get(f) or []:
            top = hit.get("top")
            if top is None or top < 0:
                continue                    # above the frame entirely
            if highest is None or top < highest:
                highest = top
    if highest is None:
        return 0
    return max(0, int(occluded_top) + margin - int(highest))


def choose_frame(hits_by_field: Mapping[str, Sequence[Mapping]],
                 viewport_h: int, occluded_top: int = 0) -> Tuple[int, Tuple[str, ...]]:
    """Pick one scroll offset that brings as many missing fields into frame as
    possible, and say which those are.

    Greedy on purpose: start from the topmost occurrence of each field and keep
    the window that covers the most of them. Fields it cannot cover are left
    for the next view, which is why the caller loops.
    """
    candidates = []
    for field, hits in hits_by_field.items():
        for h in hits:
            candidates.append((h["pageTop"], field))
    if not candidates:
        return (0, ())

    best = (0, ())
    clearance = max(120, occluded_top + 40)
    for start, _ in sorted(candidates):
        top = max(0, start - clearance)
        covered = []
        for field, hits in hits_by_field.items():
            for h in hits:
                # usable band starts BELOW the sticky bar, not at the top of
                # the viewport
                if (h["pageTop"] >= top + occluded_top
                        and h["pageBottom"] <= top + viewport_h):
                    covered.append(field)
                    break
        if len(covered) > len(best[1]):
            best = (top, tuple(sorted(set(covered))))
    return best


# --------------------------------------------------------------------------- #
# The sweep: keep taking views until the package is complete or stops improving.
# --------------------------------------------------------------------------- #

#: A page whose lazily-rendered sections only exist once scrolled to. Walking
#: the page in steps materialises them; without this the probe reports a
#: present address as absent, which would send the sweep hunting forever.
_MATERIALISE_STEP = 700

#: Ceiling on views per sweep. Bounded because "take another screenshot" must
#: never become an unbounded loop against a live brand site.
MAX_VIEWS_PER_SWEEP = 6


class ViewSweepResult(object):
    """What one sweep captured, and what it still could not prove."""

    def __init__(self, views, report, notes):
        self.views = tuple(views)
        self.report = report
        self.notes = tuple(notes)

    @property
    def complete(self) -> bool:
        return bool(self.report and self.report.complete)


def sweep_missing_views(session, *, capture_path, official_url,
                        expected: Mapping[str, str], write_view,
                        max_views: int = MAX_VIEWS_PER_SWEEP,
                        settle=None) -> "ViewSweepResult":
    """Capture additional views until every required field is visibly proven.

    ``session`` needs only ``viewport()``, ``evaluate()`` and
    ``screenshot_png()``. ``write_view(png_bytes, observations, scroll_y,
    viewport)`` persists one image plus its sidecar and returns the sidecar
    dict; the observations are handed to it rather than bolted on afterwards,
    because the sidecar ON DISK is what a later assessment reads -- patching
    the returned dict left every persisted view claiming to prove nothing.
    Both are injected so the loop can be driven by a fake in tests: deciding
    when evidence is sufficient must not require a live brand site to verify.

    Stops when the package is complete, when a view proves nothing new (the
    page simply does not show that field), or at ``max_views``.
    """
    from .evidence_completeness import assess_evidence, fields_to_recapture

    notes = []
    captured = []
    settle = settle or (lambda: None)

    for _ in range(max(1, max_views)):
        existing = load_views_for_capture(capture_path)
        report = assess_evidence(list(existing) + captured,
                                 official_url=official_url, expected=expected)
        wanted = fields_to_recapture(report)
        if not wanted:
            return ViewSweepResult(captured, report, notes)

        plan = plan_needles(wanted, expected)
        unhuntable = [f for f in wanted if f not in plan]
        if unhuntable:
            notes.append("no_expected_value_to_hunt:%s" % ",".join(unhuntable))
        if not plan:
            return ViewSweepResult(captured, report, notes)

        vw, vh = session.viewport()
        hits = session.evaluate(probe_script(plan))
        step = 0
        while not any(hits.get(f) for f in plan) and step < 12:
            step += 1
            session.evaluate("window.scrollTo(0, %d)" % (step * _MATERIALISE_STEP))
            settle()
            hits = session.evaluate(probe_script(plan))
        found = {f: hits.get(f) or [] for f in plan if hits.get(f)}
        if not found:
            notes.append("page_does_not_show:%s" % ",".join(sorted(plan)))
            return ViewSweepResult(captured, report, notes)

        occluded = int(hits.get("_occludedTop") or 0)
        top, covered = choose_frame(found, vh, occluded)
        if not covered:
            notes.append("no_frame_covers:%s" % ",".join(sorted(found)))
            return ViewSweepResult(captured, report, notes)

        session.evaluate("window.scrollTo(0, %d)" % top)
        settle()
        after = session.evaluate(probe_script(plan))

        # The sticky bar may be taller now than when the frame was chosen.
        # Correct against what is on screen, bounded, then take the picture.
        for _ in range(2):
            occluded_now = int(after.get("_occludedTop") or 0)
            shortfall = frame_shortfall(after, list(plan), occluded_now)
            if shortfall <= 0:
                break
            top = max(0, top - shortfall)
            session.evaluate("window.scrollTo(0, %d)" % top)
            settle()
            after = session.evaluate(probe_script(plan))

        png = session.screenshot_png()

        occluded_after = int(after.get("_occludedTop") or occluded)
        observations = []
        for f in plan:
            for hit in after.get(f) or []:
                observations.append(
                    observation_from_hit(f, hit, vh, occluded_after))
        proved = sorted({o.field for o in observations if o.readable})
        if not proved:
            # The frame that was measured is not the frame that rendered --
            # a page that drops a section on scroll-back, say. Writing the
            # image anyway would add an attachment proving nothing.
            notes.append("frame_rendered_nothing:%s" % ",".join(sorted(plan)))
            break
        sidecar = write_view(png, tuple(observations),
                             after.get("_scrollY", top), (vw, vh))
        attach_view_to_capture(capture_path, sidecar)
        captured.append(EvidenceView(
            png_path=str(pathlib.Path(capture_path).parent / sidecar["png_file"]),
            png_sha256=sidecar["png_sha256"], png_bytes=sidecar["png_bytes"],
            png_width=sidecar["png_width"], png_height=sidecar["png_height"],
            page_url=str(sidecar.get("final_url") or official_url),
            captured_at=str(sidecar.get("captured_at") or ""),
            observations=tuple(observations)))
        # A view that does not shrink the missing set means the framing cannot
        # reach what is left -- keep going and this loops against a live brand
        # site taking the same photograph until max_views.
        after_report = assess_evidence(list(load_views_for_capture(capture_path)),
                                       official_url=official_url, expected=expected)
        if set(after_report.proven) <= set(report.proven):
            notes.append("view_proved_nothing_new:%s" % ",".join(sorted(wanted)))
            break

    final = assess_evidence(list(load_views_for_capture(capture_path)),
                            official_url=official_url, expected=expected)
    return ViewSweepResult(captured, final, notes)
