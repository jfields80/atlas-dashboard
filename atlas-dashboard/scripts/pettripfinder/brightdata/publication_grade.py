"""Does a Bright Data capture satisfy the evidence contract AS IT STANDS?

This is the pilot's most important question and the easiest one to answer
dishonestly. The dishonest answer is to widen the contract until the new thing
fits and then report that the new thing fits. So:

* nothing in this module edits ``contracts/evidence``, ``contracts/enums`` or
  ``policy_observation``. It imports them and asks;
* where the contract has no vocabulary for something a managed-browser capture
  produces, that is reported as a CONTRACT INTEGRATION GAP and the vocabulary
  is NOT extended here;
* the verdict is stricter than the contract in one place, deliberately. The
  contract requires an ``artifact_sha256``; this module also recomputes it from
  the file on disk, and requires every quote to appear CONTIGUOUSLY in the
  saved page text. A hash nobody rederived is a string, and a stitched quote
  passed a naive substring check once already with its halves nine thousand
  characters apart.

Pure and deterministic apart from reading the artifact files it was asked to
verify.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.brightdata import browser_capture as BC   # noqa: E402
from scripts.pettripfinder.contracts import enums                    # noqa: E402
from scripts.pettripfinder.contracts import evidence as EV           # noqa: E402
from scripts.pettripfinder.policy import policy_observation as PO    # noqa: E402

CONFIRMED = "PUBLICATION_GRADE_CONFIRMED"
REJECTED = "PUBLICATION_GRADE_REJECTED"

#: The artifact this pilot offers as the page witness. ``rendered_html`` is a
#: member of ``enums.ARTIFACT_KINDS`` and needs no new vocabulary.
PRIMARY_ARTIFACT = "rendered.html"
PRIMARY_ARTIFACT_KIND = enums.ARTIFACT_RENDERED_HTML

#: A property page on the brand's own domain is the property's own surface.
#: The same call ``policy_observation`` makes: ``official_property_page`` is a
#: PT1 source type there, and PT1 maps to ``GRADE_PT1_FIRST_PARTY`` here.
SOURCE_GRADE = enums.GRADE_PT1_FIRST_PARTY

#: The closest member of the frozen capture-method vocabulary. See GAP-02: it
#: is not an accurate name for an unattended managed browser, and the pilot
#: reports that rather than inventing a better one.
CAPTURE_METHOD = "browser_assisted"


@dataclass(frozen=True)
class Gap:
    """Something the current contract cannot express about this capture."""

    code: str
    summary: str
    detail: str
    contract: str
    blocks_publication: bool

    def to_dict(self) -> Dict:
        return {"code": self.code, "summary": self.summary,
                "detail": self.detail, "contract": self.contract,
                "blocks_publication": self.blocks_publication}


def detect_gaps() -> Tuple[Gap, ...]:
    """Gaps found by INSPECTING the live contract, not by remembering it.

    Each check reads the vocabulary it is talking about, so the day a
    vocabulary gains the missing member the corresponding gap stops being
    reported without anyone editing this list.
    """
    gaps: List[Gap] = []

    screenshot_kinds = [k for k in enums.ARTIFACT_KINDS if "screenshot" in k]
    machine_kinds = [k for k in screenshot_kinds
                     if any(word in k for word in
                            ("automat", "machine", "managed", "agent", "browser"))]
    if screenshot_kinds and not machine_kinds:
        gaps.append(Gap(
            code="GAP-01-NO-MACHINE-SCREENSHOT-KIND",
            summary="a machine-captured screenshot has no lawful artifact_kind",
            detail=(
                "enums.ARTIFACT_KINDS offers %s. The only screenshot member is "
                "%r, whose meaning in this repository is an image a human took "
                "of a page they were looking at. A Bright Data screenshot is "
                "of the same page and by a different witness, and calling it "
                "an operator screenshot would misstate who took it. So this "
                "pilot files NO screenshot as evidence: full-page.png and "
                "policy-section.png are persisted, hashed and referenced, but "
                "they carry no artifact_class and back no fact."
                % (list(enums.ARTIFACT_KINDS), enums.ARTIFACT_OPERATOR_SCREENSHOT)),
            contract="scripts/pettripfinder/contracts/enums.py ARTIFACT_KINDS",
            blocks_publication=False))

    managed = [m for m in PO.CAPTURE_METHODS
               if any(word in m for word in ("managed", "remote", "proxy",
                                             "unattended", "api"))]
    if not managed:
        gaps.append(Gap(
            code="GAP-02-NO-MANAGED-BROWSER-CAPTURE-METHOD",
            summary="the capture-method vocabulary has no term for an "
                    "unattended managed browser",
            detail=(
                "policy_observation.CAPTURE_METHODS is %s. This pilot records "
                "%r because it is the nearest member, but the plain meaning of "
                "that term in this repository is an OPERATOR driving a browser "
                "-- the attended-capture path several markets depend on. A "
                "third-party managed browser has different failure modes (a "
                "silently rotated exit IP, a session that renders a shell) and "
                "a reviewer cannot currently tell the two apart from a "
                "committed record."
                % (list(PO.CAPTURE_METHODS), CAPTURE_METHOD)),
            contract="scripts/pettripfinder/policy/policy_observation.py "
                     "CAPTURE_METHODS",
            blocks_publication=False))

    if "capture_engine" not in EV.PUBLICATION_GRADE_REQUIRED and not any(
            "engine" in f for f in EV.PUBLICATION_GRADE_REQUIRED):
        gaps.append(Gap(
            code="GAP-03-NO-CAPTURE-ENGINE-BINDING",
            summary="an evidence entry does not record what fetched the page",
            detail=(
                "evidence.PUBLICATION_GRADE_REQUIRED is %s. It binds the "
                "SOURCE and the ARTIFACT and never the ACQUISITION PATH, so a "
                "record cannot say whether its page witness came from an "
                "operator's own browser, a deterministic fetch, or a "
                "third-party managed browser. That distinction is exactly what "
                "this pilot exists to evaluate, and today it survives only in "
                "the free-text capture_method field, which nothing validates."
                % (list(EV.PUBLICATION_GRADE_REQUIRED))),
            contract="scripts/pettripfinder/contracts/evidence.py "
                     "PUBLICATION_GRADE_REQUIRED",
            blocks_publication=False))

    return tuple(gaps)


@dataclass(frozen=True)
class PublicationGradeVerdict:
    verdict: str
    reasons: Tuple[str, ...]
    schema_issues: Tuple[Dict, ...]
    blockers: Tuple[str, ...]
    hash_rederived: bool
    quotes_contiguous: bool
    entries: Tuple[Dict, ...]
    gaps: Tuple[Dict, ...]
    quote_sources: Dict[str, str] = field(default_factory=dict)

    @property
    def confirmed(self) -> bool:
        return self.verdict == CONFIRMED

    def to_dict(self) -> Dict:
        return {"verdict": self.verdict, "reasons": list(self.reasons),
                "schema_issues": [dict(i) for i in self.schema_issues],
                "blockers": list(self.blockers),
                "hash_rederived": self.hash_rederived,
                "quotes_contiguous": self.quotes_contiguous,
                "quote_sources": dict(self.quote_sources),
                "evidence_entries": [dict(e) for e in self.entries],
                "contract_integration_gaps": [dict(g) for g in self.gaps]}


def build_evidence_entries(*, evidence_items: Sequence[Mapping],
                           source_url: str, artifact_sha256: str,
                           captured_at: str, ref_prefix: str) -> Tuple[Dict, ...]:
    """One evidence entry per (quote, field), in the frozen entry shape.

    Per-field rather than one blanket citation per record, because
    ``PUBLICATION_GRADE_REQUIRED`` names ``field`` for exactly that reason: a
    record that cites its whole policy once cannot say which sentence supports
    the weight limit.
    """
    entries: List[Dict] = []
    for index, item in enumerate(evidence_items):
        quote = str(item.get("quote") or "")
        for field_name in item.get("field_refs") or ():
            entries.append({
                "evidence_ref": "%s::%s::%d" % (ref_prefix, field_name, index),
                "field": field_name,
                "quote": quote,
                "source_url": source_url,
                "source_grade": SOURCE_GRADE,
                "artifact_class": enums.PUBLICATION_GRADE_EVIDENCE,
                "artifact_sha256": artifact_sha256,
                "artifact_kind": PRIMARY_ARTIFACT_KIND,
                "captured_at": captured_at,
                "capture_method": CAPTURE_METHOD,
            })
    return tuple(entries)


def assess(*, evidence_items: Sequence[Mapping], extraction: Mapping,
           source_url: str, captured_at: str, ref_prefix: str,
           artifact_path: Optional[Path], recorded_sha256: str,
           page_text_path: Optional[Path],
           identity_confirmed: bool) -> PublicationGradeVerdict:
    """Run one finished capture through the contract exactly as it stands."""
    reasons: List[str] = []
    gaps = detect_gaps()

    # --- the hash must rederive from the bytes on disk -------------------- #
    hash_rederived = False
    if artifact_path is not None and artifact_path.exists():
        actual = BC.sha256_file(artifact_path)
        hash_rederived = bool(recorded_sha256) and actual == recorded_sha256
        if not hash_rederived:
            reasons.append("the recorded %s hash does not rederive from the "
                           "file on disk" % PRIMARY_ARTIFACT)
    else:
        reasons.append("the page artifact %s is missing; there is nothing to "
                       "hash" % PRIMARY_ARTIFACT)

    entries = build_evidence_entries(
        evidence_items=evidence_items, source_url=source_url,
        artifact_sha256=recorded_sha256, captured_at=captured_at,
        ref_prefix=ref_prefix)

    # --- every quote must be contiguous in the ARTIFACT IT CITES ---------- #
    #
    # The evidence entry attests ``rendered.html``, so that is what the quote
    # must be found in. Checking only the displayed text was a proxy, and it
    # failed five Wyndham captures whose policy lives in an element the page
    # never paints -- words that are in the hashed artifact, and were never in
    # the derived convenience file.
    haystacks: List[Tuple[str, str]] = []
    if page_text_path is not None and page_text_path.exists():
        haystacks.append(("page-text.txt",
                          page_text_path.read_text(encoding="utf-8",
                                                   errors="replace")))
    if artifact_path is not None and artifact_path.exists():
        from scripts.pettripfinder.brightdata import unlocker_capture as _UC
        haystacks.append((PRIMARY_ARTIFACT, _UC.html_to_text(
            artifact_path.read_text(encoding="utf-8", errors="replace"))))

    quotes_contiguous = True
    quote_sources: Dict[str, str] = {}
    if not haystacks:
        quotes_contiguous = False
        reasons.append("no artifact text; quote contiguity is unverifiable")
    for entry in entries:
        found_in = next((name for name, text in haystacks
                         if EV.quote_is_contiguous(entry["quote"], text)), "")
        if found_in:
            quote_sources[entry["field"]] = found_in
        else:
            quotes_contiguous = False
            reasons.append("quote for %r is not contiguous in %s"
                           % (entry["field"],
                              " or ".join(n for n, _ in haystacks)))

    # --- the contract's own verdict, unmodified --------------------------- #
    record = {
        "facts": {name: extraction[name] for name in sorted(extraction)},
        "evidence": list(entries),
    }
    schema_issues = tuple({"path": i.path, "code": i.code, "message": i.message}
                          for i in EV.validate(record))
    blockers = tuple(EV.publication_blockers(record))

    if not entries:
        reasons.append("the capture produced no evidence entry to evaluate")
    if schema_issues:
        reasons.append("the evidence array fails %d contract check(s)"
                       % len(schema_issues))
    if blockers:
        reasons.extend(blockers)
    if not identity_confirmed:
        reasons.append("identity was not confirmed; evidence cannot bind to a "
                       "property the capture did not establish")

    ok = (bool(entries) and hash_rederived and quotes_contiguous
          and not schema_issues and not blockers and identity_confirmed)
    if ok:
        reasons.append(
            "the rendered-DOM artifact, its rederived hash, the contiguous "
            "per-field quotes, the first-party source URL, the captured_at "
            "stamp and the confirmed identity together satisfy "
            "evidence.PUBLICATION_GRADE_REQUIRED with no change to the "
            "contract")

    return PublicationGradeVerdict(
        verdict=CONFIRMED if ok else REJECTED,
        reasons=tuple(reasons), schema_issues=schema_issues,
        blockers=blockers, hash_rederived=hash_rederived,
        quotes_contiguous=quotes_contiguous, entries=entries,
        gaps=tuple(g.to_dict() for g in gaps), quote_sources=quote_sources)


__all__ = ["CONFIRMED", "REJECTED", "PRIMARY_ARTIFACT", "PRIMARY_ARTIFACT_KIND",
           "SOURCE_GRADE", "CAPTURE_METHOD", "Gap", "detect_gaps",
           "PublicationGradeVerdict", "build_evidence_entries", "assess"]
