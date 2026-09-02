"""PTF-DAYTON-OH-HARDENED-REVALIDATION-001 -- Phase 8.

Replay Dayton's OWNED policy evidence against the identities and reads this
order produced.

The owned evidence is the transcribed policy wording carried by
``dayton_work_browser_pass_001.json`` (PTF-DAYTON-WORK-BROWSER-INTEGRATION-001).
Forty-one of its rows carry wording; most were never corroborated by a stored
capture, which is precisely why the committed final partition parks thirteen
identities at AWAITING_POLICY_ARTIFACT -- the wording is known, the artifact of
the surface it was read from is not. A hash of a transcription binds the typing,
not the page.

This pass asks one question per row: does the fresh, identity-bound, artifact-
backed read agree with what the repo already believed? A disagreement would be
the serious finding. Agreement means the owned wording was right all along and
can now be published on evidence rather than on a transcription.

Nothing is written to authority.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-DAYTON-OH-HARDENED-REVALIDATION-001"
MARKET_ID = "dayton-oh"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")

NEGATIVE_SHAPES = ("NEGATIVE", "CONTRADICTORY", "NEGATIVE_WITH_SERVICE_ANIMAL_EXCEPTION")


def read_json(p, d=None):
    if not os.path.exists(p):
        return d
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def owned_stance(shape):
    """What the owned transcription asserts, or None when its shape does not
    assert anything either way (NONE / marketing-only wording that names no
    permission)."""
    if shape in NEGATIVE_SHAPES:
        return False
    if shape and shape.startswith("AFFIRMATIVE_STRUCTURED"):
        return True
    return None


def build() -> OrderedDict:
    census = {h["identity_key"]: h for h in read_json(os.path.join(PKG, "identity_census", MARKET_ID + ".json"))["hotels"]}
    slug_to_key = {h.get("slug"): k for k, h in census.items()}
    wb = read_json(os.path.join(PKG, "dayton_work_browser_pass_001.json"))
    owned = {}
    for it in wb["items"]:
        key = slug_to_key.get(it["slug"])
        if key and it.get("transcribed_policy_wording"):
            owned[key] = it
    attended = {r["identity_key"]: r for r in
                read_json(os.path.join(REPORTS, "dayton_oh_attended_capture_001.json"), {"results": []})["results"]}

    rows = []
    for key, r in sorted(attended.items()):
        it = owned.get(key)
        rd = r.get("reader") or {}
        fresh = rd.get("pets_allowed")
        bound = bool((r.get("identity_binding") or {}).get("bound"))
        row = OrderedDict([
            ("identity_key", key), ("canonical_name", r.get("hotel")), ("brand", r.get("brand")),
            ("fresh_pets_allowed", fresh), ("fresh_identity_bound", bound),
            ("fresh_document_sha256", "sha256:" + (r.get("html_sha256") or "")),
            ("fresh_quote", rd.get("pets_allowed_quote")),
            ("owned_wording", (it or {}).get("transcribed_policy_wording")),
            ("owned_shape", (it or {}).get("policy_wording_shape")),
            ("owned_was_corroborated_by_a_stored_capture",
             (it or {}).get("transcription_corroborated_by_a_stored_capture")),
        ])
        if it is None:
            row["classification"] = "NEWLY_READABLE_PF" if fresh is True else \
                "NEWLY_READABLE_NO_PETS" if fresh is False else "SOURCE_SILENT"
            row["note"] = "the repo owned no transcription for this identity; this read is new evidence, not a replay"
        elif fresh is None:
            row["classification"] = "CAPTURE_FAILED"
        elif not bound:
            row["classification"] = "IDENTITY_MISMATCH"
            row["note"] = "the fresh read did not bind to this census row, so it cannot confirm or contradict the owned wording"
        else:
            stance = owned_stance(it.get("policy_wording_shape"))
            if stance is None:
                row["classification"] = "OWNED_WORDING_ASSERTS_NOTHING"
            elif stance == fresh:
                row["classification"] = "AGREES_LIVE_PF" if fresh else "AGREES_LIVE_NO_PETS"
                row["note"] = ("the owned wording was correct and is now bound to an artifact of the page it came from"
                               if not it.get("transcription_corroborated_by_a_stored_capture")
                               else "the owned wording was already corroborated and remains correct")
            else:
                row["classification"] = "SOURCE_CONFLICT"
                row["note"] = "the fresh read of the property's own page contradicts the owned transcription -- founder review required"

        rows.append(row)

    counts = Counter(r["classification"] for r in rows)
    conflicts = [r for r in rows if r["classification"] == "SOURCE_CONFLICT"]
    newly_artifact_bound = [r for r in rows
                            if r["classification"] in ("AGREES_LIVE_PF", "AGREES_LIVE_NO_PETS")
                            and r["owned_was_corroborated_by_a_stored_capture"] is False]
    return OrderedDict([
        ("schema", "ptf-owned-evidence-replay/1.0"), ("work_order", WORK_ORDER),
        ("phase", "8 -- owned policy evidence replay"), ("market_id", MARKET_ID),
        ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("owned_transcriptions_available", len(owned)),
        ("owned_transcriptions_replayed", sum(1 for r in rows if r["owned_wording"])),
        ("classification_counts", OrderedDict(sorted(counts.items()))),
        ("source_conflicts", len(conflicts)),
        ("previously_uncorroborated_now_artifact_bound", len(newly_artifact_bound)),
        ("headline",
         "%d owned transcriptions were replayed against a fresh identity-bound read of the "
         "property's own page. %d disagreed. %d of them had never been corroborated by a "
         "stored capture and are now bound to one, which is exactly the gap that parked them "
         "at AWAITING_POLICY_ARTIFACT."
         % (sum(1 for r in rows if r["owned_wording"]), len(conflicts), len(newly_artifact_bound))),
        ("rows", rows),
    ])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPORTS, "dayton_oh_owned_evidence_replay_001.json"))
    args = ap.parse_args(argv)
    rep = build()
    with open(args.out, "wb") as fh:
        fh.write((json.dumps(rep, indent=1, ensure_ascii=False, default=str) + "\n").encode("utf-8"))
    print("written", os.path.relpath(args.out, _DASH))
    print(json.dumps(rep["classification_counts"]))
    print(rep["headline"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
