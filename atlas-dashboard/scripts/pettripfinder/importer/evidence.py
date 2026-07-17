"""AES-DATA-001 importer -- evidence-span validation (mission section 11).

The anti-hallucination wall: every LLM-proposed field must carry a quote
found *verbatim* in the exact normalized snapshot text the model was given.
A field whose quote cannot be relocated is marked UNSUPPORTED and never
published. Structured-metadata facts (JSON-LD/microdata/etc.) are evidenced
by their parsed source, not by visible text, and are recorded separately.

Pure and deterministic: no I/O, no network.
"""

from __future__ import annotations

import re
from typing import List, Tuple

from scripts.pettripfinder.importer.constants import (
    EVIDENCE_QUOTE_CAP,
    METHOD_LLM_TEXT,
    REASON_EVIDENCE_MISMATCH,
    SUPPORT_AMBIGUOUS,
    SUPPORT_SUPPORTED,
    SUPPORT_UNSUPPORTED,
)
from scripts.pettripfinder.importer.models import ExtractedEvidence, ProposedFact
from scripts.pettripfinder.importer.normalize import normalize_whitespace


def cap_quote(quote: str) -> Tuple[str, bool]:
    """Cap to the 300-char evidence limit. Returns (capped, truncated)."""
    if quote is None:
        return "", False
    if len(quote) <= EVIDENCE_QUOTE_CAP:
        return quote, False
    return quote[:EVIDENCE_QUOTE_CAP], True


def locate_quote(normalized_text: str, quote: str) -> Tuple[int, int]:
    """Deterministically relocate ``quote`` inside the already-normalized
    snapshot text. Both sides go through the identical whitespace/Unicode
    normalization so smart quotes, NBSPs, and whitespace runs never cause a
    spurious miss. Returns ``(start, end)`` char offsets into
    ``normalized_text``, or ``(-1, -1)`` when absent.

    Note: offsets index the normalized text (the exact string hashed into the
    snapshot and shown to the model), so they are stable and replayable."""
    if not quote or not normalized_text:
        return (-1, -1)
    needle = normalize_whitespace(quote)
    if not needle:
        return (-1, -1)
    idx = normalized_text.find(needle)
    if idx < 0:
        return (-1, -1)
    return (idx, idx + len(needle))


# --------------------------------------------------------------------------- #
# Canonical, content-preserving relocation (AES-DATA-001 live defect).
#
# ``locate_quote`` already tolerates smart quotes, NBSPs, and repeated
# whitespace (both sides run through ``normalize_whitespace``). It does NOT
# tolerate whitespace *around commas* or a comma-vs-line-break difference
# between address components, so "Dublin , OH" fails to match "Dublin, OH".
#
# The canonical form below collapses every run of commas-and-whitespace to a
# single space on BOTH sides, so "Dublin , OH" / "Dublin,OH" / "Dublin, OH"
# and a component split across a line break all compare equal. This unifies
# only separators -- every meaningful alphanumeric token and its order are
# preserved, so a changed number/street/city/ZIP, a missing word, or a
# paraphrase still fails to match. Matches are token-boundary anchored to
# avoid partial-token hits, and the ORIGINAL snapshot span/wording is
# recovered via an index map so evidence still points at real source text.
# --------------------------------------------------------------------------- #

_SEP = ", \t\n\r ​"


def _canonical_needle(quote: str) -> str:
    """Canonical comparison form of the (untrusted) LLM quote: normalize
    Unicode/smart-quotes/NBSP/whitespace, then unify comma+whitespace
    separators to single spaces. Lower-cased for case-insensitive location."""
    s = normalize_whitespace(quote)
    s = re.sub(r"[,\s]+", " ", s).strip()
    return s.lower()


def _canonical_haystack(text: str) -> Tuple[str, List[Tuple[int, int]]]:
    """Canonical form of the already-normalized snapshot text, plus a
    per-canonical-char ``(orig_start, orig_end)`` span map back into
    ``text``. Runs of commas/whitespace collapse to one space mapped to the
    whole original run."""
    canon: List[str] = []
    spans: List[Tuple[int, int]] = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch in _SEP:
            j = i
            while j < n and text[j] in _SEP:
                j += 1
            canon.append(" ")
            spans.append((i, j))
            i = j
        else:
            canon.append(ch.lower())
            spans.append((i, i + 1))
            i += 1
    return "".join(canon), spans


def _find_token_bounded(haystack: str, needle: str) -> int:
    """First occurrence of ``needle`` in ``haystack`` that sits on token
    boundaries (preceded by start/space, followed by end/space)."""
    start = 0
    while True:
        idx = haystack.find(needle, start)
        if idx < 0:
            return -1
        before_ok = idx == 0 or haystack[idx - 1] == " "
        after = idx + len(needle)
        after_ok = after == len(haystack) or haystack[after] == " "
        if before_ok and after_ok:
            return idx
        start = idx + 1


def locate_quote_canonical(normalized_text: str, quote: str) -> Tuple[int, int]:
    """Relocate a quote that differs from the snapshot only by comma/
    whitespace presentation. Returns ORIGINAL ``(start, end)`` offsets into
    ``normalized_text`` (so the stored evidence is real source wording), or
    ``(-1, -1)`` when no content-equivalent, token-aligned match exists."""
    if not quote or not normalized_text:
        return (-1, -1)
    needle = _canonical_needle(quote)
    if not needle:
        return (-1, -1)
    hay, spans = _canonical_haystack(normalized_text)
    idx = _find_token_bounded(hay, needle)
    if idx < 0:
        return (-1, -1)
    end_k = idx + len(needle)
    orig_start = spans[idx][0]
    orig_end = spans[end_k - 1][1]
    return (orig_start, orig_end)


def build_llm_evidence(
    fact: ProposedFact, normalized_text: str, source_url: str,
) -> ExtractedEvidence:
    """Validate one LLM-proposed fact against the snapshot. A quote that is
    not found verbatim yields ``UNSUPPORTED`` + an ``evidence_mismatch``
    warning -- the field will not be published (mission section 11)."""
    warnings = []
    capped, truncated = cap_quote(fact.quote or "")
    if truncated:
        warnings.append("quote_truncated_to_%d" % EVIDENCE_QUOTE_CAP)

    start, end = locate_quote(normalized_text, capped)
    if start < 0:
        # Try the model-supplied offsets as a last resort (still must match).
        if (
            0 <= fact.char_start < fact.char_end <= len(normalized_text)
            and normalize_whitespace(normalized_text[fact.char_start:fact.char_end])
            == normalize_whitespace(capped)
        ):
            start, end = fact.char_start, fact.char_end

    canonical_relocation = False
    if start < 0:
        # Content-preserving relocation: tolerate only comma/whitespace/
        # line-break presentation differences (defect repair).
        start, end = locate_quote_canonical(normalized_text, capped)
        canonical_relocation = start >= 0
        if canonical_relocation:
            warnings.append("canonical_whitespace_relocation")

    if start < 0:
        warnings.append(REASON_EVIDENCE_MISMATCH)
        return ExtractedEvidence(
            field_name=fact.field_name,
            proposed_value=fact.proposed_value,
            source_wording=capped,
            source_url=source_url,
            snapshot_quote=capped,
            char_start=-1,
            char_end=-1,
            extraction_method=METHOD_LLM_TEXT,
            support_state=SUPPORT_UNSUPPORTED,
            warnings=tuple(warnings),
        )

    support = SUPPORT_AMBIGUOUS if fact.ambiguous else SUPPORT_SUPPORTED
    if fact.warning:
        warnings.append(fact.warning)
    # The verbatim slice actually present in the snapshot is the source wording.
    verbatim = normalized_text[start:end]
    return ExtractedEvidence(
        field_name=fact.field_name,
        proposed_value=fact.proposed_value,
        source_wording=verbatim,
        source_url=source_url,
        snapshot_quote=verbatim,
        char_start=start,
        char_end=end,
        extraction_method=METHOD_LLM_TEXT,
        support_state=support,
        warnings=tuple(warnings),
    )


def build_structured_evidence(
    field_name: str,
    proposed_value: str,
    quote: str,
    source_url: str,
    method: str,
) -> ExtractedEvidence:
    """Evidence for a deterministically-extracted structured-metadata fact.
    These are SUPPORTED by their parsed source (JSON-LD/microdata/tel/etc.),
    which need not appear in the visible normalized text; offsets are ``-1``
    because the value lives in markup, not prose."""
    capped, _ = cap_quote(quote or proposed_value or "")
    return ExtractedEvidence(
        field_name=field_name,
        proposed_value=proposed_value,
        source_wording=quote or proposed_value or "",
        source_url=source_url,
        snapshot_quote=capped,
        char_start=-1,
        char_end=-1,
        extraction_method=method,
        support_state=SUPPORT_SUPPORTED,
        warnings=(),
    )


def is_published(evidence: ExtractedEvidence) -> bool:
    """A field may be published only when its evidence is SUPPORTED or
    AMBIGUOUS (AMBIGUOUS surfaces to REVIEW but is still shown); UNSUPPORTED
    is dropped entirely."""
    return evidence.support_state in (SUPPORT_SUPPORTED, SUPPORT_AMBIGUOUS)
