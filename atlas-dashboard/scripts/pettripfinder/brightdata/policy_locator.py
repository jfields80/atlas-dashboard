"""The canonical policy-locator contract: locate once, replay exactly.

WHY THIS EXISTS
---------------
Two locators were in service. One ran INSIDE the page and walked DOM ancestors
of a visible element carrying a signal phrase; the other runs over saved HTML
and grows a run of adjacent text LINES. They share the phrase list, the size
bounds, the mention floors and the feature vocabulary, and they still disagree
on roughly a quarter of captures, because a DOM ancestor is not a run of lines.

The measurement that decided this design (PTF-CANONICAL-POLICY-LOCATOR-PARITY-019,
143 persisted captures):

    108  the two agree
     29  CONTAINER_BOUNDARY_DIFFERENCE -- same content, different extent
      5  SELECTOR_DIFFERENCE           -- different regions of the same page
      1  the static walk selected nothing at all
      0  DYNAMIC_RENDERING_DIFFERENCE

That last figure is the important one. **Every block the live locator selected
is present in the saved artifact.** Nothing was lost to hydration, so the
persisted HTML does hold the evidence -- what it cannot hold is WHICH BOUNDARY
the live walk chose, because recovering that would mean reimplementing a DOM
walk over parsed HTML and hoping the two agree. They do not have to.

THE CONTRACT
------------
So the boundary is not recomputed. It is RECORDED.

  input          the located block text, and the artifact it came from
  normalization  whitespace collapsed to single spaces, ends stripped; this is
                 the normalization both locators already applied, and it is
                 what the block file holds
  signal         a phrase from ``policy_surface.SIGNAL_PHRASES``
  boundary       whatever the locator that RAN chose; recorded, never re-derived
  container      the locator's own selector or strategy, recorded verbatim
  tie-breaking   most policy features, then the shorter block -- unchanged, and
                 applied only at capture time
  identity       untouched by this module; identity gates run where they ran
  visibility     the live walk skips hidden elements, the static walk has no
                 notion of visibility. Recorded per capture rather than
                 reconciled, so a reader of the artifact knows which applied
  provenance     ``locator.json`` beside the block, naming the contract, the
                 strategy, the selector, the block hash and the document hash
  replay         read the block, verify its hash, return it. A replay NEVER
                 relocates: relocating changes which text the record is about,
                 which is a re-acquisition and not a replay

WHAT THIS IS NOT
----------------
It is not a third locator. It adds no rule about where a policy lives; it makes
the answer already computed durable and checkable. The static walk remains, and
remains the right tool for a document that was never captured through this
contract -- that case is named ``LEGACY_ARTIFACT_INSUFFICIENT`` rather than
silently re-located.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Mapping, Optional

CONTRACT = "ptf-policy-locator/1.0"

#: The block itself, and the record describing how it was chosen.
BLOCK_ARTIFACT = "policy-block.txt"
LOCATOR_ARTIFACT = "locator.json"

#: Which walk produced a block. Recorded rather than inferred: the two see
#: visibility differently and a replay is entitled to know which one ran.
LIVE_DOM_WALK = "live_dom_walk"
STATIC_TEXT_WALK = "static_text_walk"

#: Replay outcomes.
REPLAYED = "REPLAYED_FROM_CANONICAL_ARTIFACT"
BLOCK_ONLY = "REPLAYED_FROM_BLOCK_WITHOUT_LOCATOR_RECORD"
INSUFFICIENT = "LEGACY_ARTIFACT_INSUFFICIENT"
HASH_MISMATCH = "BLOCK_HASH_DOES_NOT_MATCH_ITS_RECORD"


def sha256_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CanonicalBlock:
    """A policy block recovered from disk, and how much is known about it."""

    status: str
    text: str = ""
    block_sha256: str = ""
    record: Mapping = field(default_factory=dict)

    @property
    def replayable(self) -> bool:
        return self.status in (REPLAYED, BLOCK_ONLY)

    @property
    def canonical(self) -> bool:
        """Replayed against a locator record that vouches for the bytes."""
        return self.status == REPLAYED

    def to_dict(self) -> Dict:
        return {"status": self.status, "block_sha256": self.block_sha256,
                "block_chars": len(self.text), "record": dict(self.record)}


def build_record(*, hit, block_text: str, document_sha256: str,
                 walk: str) -> Dict:
    """The locator record for one capture.

    ``hit`` is the ``SurfaceHit`` the locator that actually ran produced. Every
    field is copied from it; none is recomputed, because recomputing is the
    thing this contract exists to stop.
    """
    return {
        "contract": CONTRACT,
        "walk": walk,
        "found": bool(getattr(hit, "found", False)),
        "strategy": getattr(hit, "strategy", "") or "",
        "selector": getattr(hit, "selector", "") or "",
        "matched_phrase": getattr(hit, "matched_phrase", "") or "",
        "policy_features": int(getattr(hit, "policy_features", 0) or 0),
        "container_chars": int(getattr(hit, "container_chars", 0) or 0),
        "candidates_considered": int(getattr(hit, "candidates_considered", 0) or 0),
        "brand_generic": bool(getattr(hit, "brand_generic", False)),
        # The live walk skips hidden elements; the static walk cannot see
        # visibility at all. Stated, so a replay knows which rule produced this.
        "visibility_filtered": walk == LIVE_DOM_WALK,
        "rendered": bool(getattr(hit, "rendered", True)),
        "block_sha256": sha256_text(block_text),
        "block_chars": len(block_text or ""),
        "document_sha256": document_sha256,
    }


def persist(attempt_dir: Path, record: Mapping) -> Path:
    """Write the locator record beside the block it describes."""
    path = Path(attempt_dir) / LOCATOR_ARTIFACT
    path.write_bytes((json.dumps(dict(record), indent=1, ensure_ascii=False)
                      + "\n").encode("utf-8"))
    return path


def replay(attempt_dir: Path) -> CanonicalBlock:
    """The block this capture located, recovered without a browser.

    Four outcomes, and the difference between them matters:

      REPLAYED       the block and a locator record that vouches for its bytes
      BLOCK_ONLY     the block, from a capture predating the record. Exact, but
                     nothing attests to how the boundary was chosen
      HASH_MISMATCH  the record and the block disagree. Never silently
                     preferred one over the other; the caller decides
      INSUFFICIENT   no block on disk. A static re-walk would answer a
                     DIFFERENT question and is not performed here
    """
    directory = Path(attempt_dir)
    block_path = directory / BLOCK_ARTIFACT
    record_path = directory / LOCATOR_ARTIFACT

    if not block_path.is_file():
        return CanonicalBlock(status=INSUFFICIENT)
    text = block_path.read_text(encoding="utf-8", errors="replace")
    digest = sha256_text(text)

    if not record_path.is_file():
        return CanonicalBlock(status=BLOCK_ONLY, text=text, block_sha256=digest)

    record = json.loads(record_path.read_text(encoding="utf-8-sig"))
    if record.get("block_sha256") and record["block_sha256"] != digest:
        return CanonicalBlock(status=HASH_MISMATCH, text=text,
                              block_sha256=digest, record=record)
    return CanonicalBlock(status=REPLAYED, text=text, block_sha256=digest,
                          record=record)


def parity(captured_block: str, replayed: CanonicalBlock) -> Dict:
    """Whether a replay reproduced what the capture located.

    Byte equality on the persisted text is the bar. It is achievable because
    the boundary is recorded rather than recomputed, and it is the only bar
    worth having: a normalized-equivalence bar would hide exactly the
    boundary differences this contract exists to eliminate.
    """
    return {
        "captured_sha256": sha256_text(captured_block),
        "replayed_sha256": replayed.block_sha256,
        "identical": sha256_text(captured_block) == replayed.block_sha256,
        "replay_status": replayed.status,
        "canonical": replayed.canonical,
    }


__all__ = ["CONTRACT", "BLOCK_ARTIFACT", "LOCATOR_ARTIFACT", "LIVE_DOM_WALK",
           "STATIC_TEXT_WALK", "REPLAYED", "BLOCK_ONLY", "INSUFFICIENT",
           "HASH_MISMATCH", "CanonicalBlock", "build_record", "persist",
           "replay", "parity", "sha256_text"]
