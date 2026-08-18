"""Do not trust the summary. Reconcile it.

A benchmark's summary is computed by the same code that ran the benchmark, so
it can only ever confirm its own arithmetic. This module checks the claims
against the things they are claims ABOUT: the sample, the journal, the bytes on
disk, and the frozen contracts.

Every check answers a question that has previously been answered wrongly
somewhere in this repository's history:

* Does the artifact exist at all? Cleveland's screenshot census found 135
  directories holding zero images.
* Does the hash rederive? A hash nobody recomputed is a string.
* Is the quote contiguous? A stitched quote passed a naive substring test with
  its halves nine thousand characters apart.
* Is the screenshot an image or a blank rectangle? Run 1 of the Marriott pilot
  counted a uniform white crop as a policy screenshot.
* Did we accept a brand homepage or a locale redirect? An unpinned exit served
  ``marriott.com/es/default.mi`` and only the property-code gate caught it.
* Did anything infer? A weight operator, a fee scope or a species map that the
  source never stated is a guest-visible error.
* Did a contradiction survive as a contradiction?

Read-only. It reads reports, the journal and raw artifacts, and writes nothing.
"""

from __future__ import annotations

import collections
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.brightdata import browser_capture as BC   # noqa: E402
from scripts.pettripfinder.brightdata import client                  # noqa: E402
from scripts.pettripfinder.brightdata import corpus as CORPUS        # noqa: E402
from scripts.pettripfinder.brightdata import cross_brand_pilot_002 as PILOT  # noqa: E402
from scripts.pettripfinder.brightdata import marriott_surface as MS  # noqa: E402
from scripts.pettripfinder.brightdata import outcomes as O           # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR    # noqa: E402
from scripts.pettripfinder.brightdata import policy_surface as PS    # noqa: E402
from scripts.pettripfinder.brightdata import publication_grade as PG  # noqa: E402
from scripts.pettripfinder.contracts import enums                    # noqa: E402
from scripts.pettripfinder.contracts import evidence as EV           # noqa: E402
from scripts.pettripfinder.policy import policy_observation as PO    # noqa: E402

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

#: Credential shapes that must not appear in anything committed, checked by
#: SHAPE as well as by the live secret so the guard still bites where the
#: environment variable is unset.
CREDENTIAL_SHAPES = ("brd-customer", "superproxy", "wss://",
                     "BRIGHTDATA_BROWSER_AUTH=")


@dataclass
class Check:
    name: str
    passed: bool
    detail: str = ""
    failures: Tuple[str, ...] = ()

    def to_dict(self) -> Dict:
        return {"name": self.name, "passed": self.passed,
                "detail": self.detail, "failures": list(self.failures)}


def _check(name: str, failures: Sequence[str], detail: str = "") -> Check:
    return Check(name=name, passed=not failures, detail=detail,
                 failures=tuple(failures[:12]))


# --------------------------------------------------------------------------- #
# A. Journal integrity.
# --------------------------------------------------------------------------- #

def reconcile_journal(sample, journal: Mapping) -> List[Check]:
    checks: List[Check] = []
    slugs = [PILOT.target_for(r).slug for r in sample]

    checks.append(_check(
        "sample is exactly %d" % PILOT.PILOT_SIZE,
        [] if len(sample) == PILOT.PILOT_SIZE
        else ["sample holds %d" % len(sample)],
        "%d properties" % len(sample)))

    checks.append(_check(
        "journal holds exactly %d unique properties" % PILOT.PILOT_SIZE,
        [] if len(journal) == PILOT.PILOT_SIZE
        else ["journal holds %d" % len(journal)],
        "%d journalled" % len(journal)))

    missing = [s for s in slugs if s not in journal]
    checks.append(_check("no sample property missing from the journal", missing))

    extra = [s for s in journal if s not in set(slugs)]
    checks.append(_check("no journal row outside the sample", extra))

    keys = [journal[s].get("identity_key") for s in slugs if s in journal]
    dupes = [k for k, n in collections.Counter(keys).items() if k and n > 1]
    checks.append(_check("no duplicate identity_key", dupes))

    urls = [journal[s].get("requested_url", "").rstrip("/").lower()
            for s in slugs if s in journal]
    dupe_urls = [u for u, n in collections.Counter(urls).items() if n > 1]
    checks.append(_check("no duplicate source URL", dupe_urls))

    counts = collections.Counter(journal[s]["bucket"] for s in slugs
                                 if s in journal)
    wrong = ["%s=%d" % (b, counts.get(b, 0)) for b in CORPUS.BUCKETS
             if counts.get(b, 0) != PILOT.PER_BUCKET]
    checks.append(_check("exactly %d per bucket" % PILOT.PER_BUCKET, wrong,
                         str(dict(counts))))

    banned = [journal[s]["hotel"] for s in slugs if s in journal
              and journal[s].get("brand") in CORPUS.EXCLUDED_BRANDS]
    banned += [journal[s]["hotel"] for s in slugs if s in journal
               and re.search(r"hyatt\.com|bestwestern\.com",
                             journal[s].get("requested_url", ""), re.I)]
    checks.append(_check("Hyatt = 0 and Best Western = 0", banned))

    return checks


# --------------------------------------------------------------------------- #
# B. Every successful capture.
# --------------------------------------------------------------------------- #

def reconcile_captures(sample, journal: Mapping) -> List[Check]:
    by_slug = {PILOT.target_for(r).slug: r for r in sample}
    ok = [(s, e) for s, e in journal.items() if e.get("successful_attempt")]

    missing_files: List[str] = []
    bad_hashes: List[str] = []
    blank_images: List[str] = []
    absent_paths = 0
    stitched: List[str] = []
    unconfirmed: List[str] = []
    bad_landing: List[str] = []
    inferred: List[str] = []
    false_no_pets: List[str] = []
    vocab: List[str] = []
    contradiction_lost: List[str] = []
    benchmark_leak: List[str] = []
    failure_artifacts: List[str] = []

    for slug, entry in ok:
        record = by_slug.get(slug)
        files = (entry.get("artifacts") or {}).get("files") or {}
        for required in ("rendered.html", "page-text.txt", "policy-block.txt",
                         "full-page.png"):
            if required not in files:
                missing_files.append("%s: no %s" % (slug, required))

        for name, meta in files.items():
            if not isinstance(meta, dict) or "sha256" not in meta:
                continue
            if not _SHA256_RE.match(meta["sha256"]):
                bad_hashes.append("%s/%s: malformed hash" % (slug, name))
                continue
            path = Path(meta["path"])
            if not path.exists():
                absent_paths += 1
                continue
            if BC.sha256_file(path) != meta["sha256"]:
                bad_hashes.append("%s/%s: hash does not rederive" % (slug, name))
            if int(meta.get("bytes") or 0) != path.stat().st_size:
                bad_hashes.append("%s/%s: byte count disagrees" % (slug, name))
            if name.endswith(".png") and BC.image_is_blank(path) is True:
                blank_images.append("%s/%s is a flat colour" % (slug, name))

        # Quotes must be contiguous in the persisted block AND in the page text.
        block = entry.get("policy_block_quote") or ""
        for item in (entry.get("observation") or {}).get("evidence") or ():
            if not EV.quote_is_contiguous(item.get("quote", ""), block):
                stitched.append("%s: %r not contiguous in the block"
                                % (slug, item.get("quote", "")[:50]))
        text_meta = files.get("page-text.txt") or {}
        text_path = Path(text_meta["path"]) if text_meta.get("path") else None
        if text_path and text_path.exists():
            page_text = text_path.read_text(encoding="utf-8", errors="replace")
            for item in (entry.get("observation") or {}).get("evidence") or ():
                if not EV.quote_is_contiguous(item.get("quote", ""), page_text):
                    stitched.append("%s: %r not contiguous in page-text.txt"
                                    % (slug, item.get("quote", "")[:50]))

        valid = next((a for a in entry["attempts"] if a["outcome"] == O.VALID),
                     None)
        identity = (valid or {}).get("identity") or {}
        if not identity.get("confirmed"):
            unconfirmed.append("%s: identity not confirmed" % slug)

        # Not a brand homepage, not a locale redirect.
        final_url = (valid or {}).get("final_url") or ""
        requested = entry.get("requested_url") or ""
        code = entry.get("property_code") or ""
        if code:
            if PS.property_code(final_url, entry.get("brand", "")) != code:
                bad_landing.append("%s: final URL lacks the property code" % slug)
        else:
            want = PS.path_identity(requested)
            if want and PS.path_identity(final_url) != want:
                bad_landing.append("%s: final URL is not the property path (%s)"
                                   % (slug, final_url[:70]))
        if re.search(r"/(es|fr|de|pt|it|ja|zh|ko)/(default|index)",
                     final_url, re.I):
            bad_landing.append("%s: localized landing page %s" % (slug, final_url))

        extraction = (entry.get("observation") or {}).get("extraction") or {}

        # Unsupported inference: a comparison the source never made, a scope it
        # never stated, a species it never named.
        limit = extraction.get("weight_limit") or {}
        if isinstance(limit, dict):
            if "operator" in limit:
                inferred.append("%s: weight_limit carries an operator" % slug)
            if "scope" in limit:
                inferred.append("%s: weight_limit carries a scope" % slug)
        quoted = " ".join(item.get("quote", "") for item
                          in (entry.get("observation") or {}).get("evidence") or ())
        if extraction.get("fee_scope") and not re.search(
                r"per\s*(pet|animal|room|reservation)", quoted, re.I):
            inferred.append("%s: fee_scope with no 'per pet/room' in any quote"
                            % slug)
        if extraction.get("species_allowed") and not re.search(
                r"\bdogs?\b|\bcats?\b", quoted, re.I):
            inferred.append("%s: species_allowed with no species named in a quote"
                            % slug)

        # Every asserted field must be covered by a quote (M9, checked here too).
        covered = set()
        for item in (entry.get("observation") or {}).get("evidence") or ():
            covered.update(item.get("field_refs") or ())
        uncovered = sorted(set(extraction) - covered)
        if uncovered:
            inferred.append("%s: field(s) %s asserted with no quote"
                            % (slug, uncovered))

        if set(extraction) - PO.EXTRACTION_FIELDS:
            vocab.append("%s: %s" % (slug, sorted(set(extraction)
                                                  - PO.EXTRACTION_FIELDS)))

        if entry.get("disposition") == PILOT.VERIFIED_NO_PETS_CANDIDATE:
            if extraction.get("pets_allowed") is not False:
                false_no_pets.append("%s: candidate without a captured false"
                                     % slug)
            elif not re.search(r"not allowed|no pets|not permitted",
                               block, re.I):
                false_no_pets.append("%s: candidate whose block never refuses"
                                     % slug)

        comparison = entry.get("benchmark_comparison") or {}
        if comparison.get("contradiction_preserved") is False:
            contradiction_lost.append(
                "%s: the corpus withheld a field this capture produced" % slug)

        # The benchmark must not have travelled into the capture: every quote
        # has to come from the page's own persisted block.
        if record is not None:
            for quote in record.quotes:
                if quote and quote not in block and any(
                        quote == item.get("quote")
                        for item in (entry.get("observation") or {}).get(
                            "evidence") or ()):
                    benchmark_leak.append(
                        "%s: an evidence quote equals a benchmark quote that is "
                        "not in the captured block" % slug)

    for slug, entry in journal.items():
        if entry.get("successful_attempt"):
            continue
        if entry.get("artifacts") or entry.get("observation"):
            failure_artifacts.append("%s: a failed property carries artifacts"
                                     % slug)
        if entry.get("disposition") != PILOT.CLAUDE_FALLBACK_REQUIRED:
            failure_artifacts.append("%s: failed property disposition is %r"
                                     % (slug, entry.get("disposition")))

    return [
        _check("every capture wrote its required artifacts", missing_files),
        _check("every artifact hash rederives from bytes on disk", bad_hashes,
               "%d artifact paths were absent from this machine" % absent_paths),
        _check("no screenshot is a flat colour", blank_images),
        _check("every evidence quote is contiguous", stitched),
        _check("every capture passed the identity gate", unconfirmed),
        _check("no brand homepage or locale redirect was accepted", bad_landing),
        _check("unsupported inference = 0", inferred),
        _check("extraction stays inside the frozen vocabulary", vocab),
        _check("false VERIFIED_NO_PETS = 0", false_no_pets),
        _check("contradictions remain contradictions", contradiction_lost),
        _check("no benchmark value reached a capture", benchmark_leak),
        _check("a failed property carries no artifacts and no candidate state",
               failure_artifacts),
    ]


# --------------------------------------------------------------------------- #
# C. The publication-grade contract, re-run.
# --------------------------------------------------------------------------- #

def recheck_publication_grade(journal: Mapping) -> List[Check]:
    """Re-run the CURRENT contract over every valid capture, unmodified."""
    disagreements: List[str] = []
    confirmed = 0
    valid = 0
    for slug, entry in journal.items():
        if not entry.get("successful_attempt"):
            continue
        valid += 1
        observation = entry.get("observation") or {}
        files = (entry.get("artifacts") or {}).get("files") or {}
        html = files.get(PG.PRIMARY_ARTIFACT) or {}
        text = files.get("page-text.txt") or {}
        attempt = next(a for a in entry["attempts"] if a["outcome"] == O.VALID)
        verdict = PG.assess(
            evidence_items=observation.get("evidence") or (),
            extraction=observation.get("extraction") or {},
            source_url=observation.get("source_url", ""),
            captured_at=attempt.get("started_at", ""),
            ref_prefix="recheck::%s" % slug,
            artifact_path=Path(html["path"]) if html.get("path") else None,
            recorded_sha256=str(html.get("sha256") or ""),
            page_text_path=Path(text["path"]) if text.get("path") else None,
            identity_confirmed=bool((attempt.get("identity") or {}).get(
                "confirmed")))
        if verdict.confirmed:
            confirmed += 1
        recorded = (entry.get("publication_grade") or {}).get("verdict")
        if verdict.verdict != recorded:
            disagreements.append("%s: recorded %s, recheck says %s (%s)"
                                 % (slug, recorded, verdict.verdict,
                                    "; ".join(verdict.reasons[:2])))
    return [_check("the recorded publication grade reproduces", disagreements,
                   "%d of %d valid captures confirm under the current contract"
                   % (confirmed, valid))]


# --------------------------------------------------------------------------- #
# D. Committed artefacts carry no credential.
# --------------------------------------------------------------------------- #

def reconcile_committed_files() -> List[Check]:
    leaks: List[str] = []
    for path in (PILOT.SUMMARY_REPORT, PILOT.PROPERTY_REPORT,
                 PILOT.BRAND_REPORT, PILOT.SAMPLE_REPORT):
        if not path.exists():
            leaks.append("%s is missing" % path.name)
            continue
        text = path.read_text(encoding="utf-8")
        if client.contains_credential(text):
            leaks.append("%s carries the live credential" % path.name)
        for shape in CREDENTIAL_SHAPES:
            if shape in text:
                leaks.append("%s contains %r" % (path.name, shape))
    return [_check("committed reports carry no credential", leaks)]


# --------------------------------------------------------------------------- #
# Entry point.
# --------------------------------------------------------------------------- #

def run() -> Dict:
    sample = PILOT.build_sample()
    journal = PILOT.read_journal()
    checks: List[Check] = []
    checks += reconcile_journal(sample, journal)
    checks += reconcile_captures(sample, journal)
    checks += recheck_publication_grade(journal)
    checks += reconcile_committed_files()
    return {"checks": [c.to_dict() for c in checks],
            "passed": all(c.passed for c in checks),
            "journalled": len(journal), "sample": len(sample)}


def main(argv: Optional[Sequence[str]] = None) -> int:
    result = run()
    width = max(len(c["name"]) for c in result["checks"])
    for check in result["checks"]:
        print("%s  %-*s  %s" % ("PASS" if check["passed"] else "FAIL",
                                width, check["name"], check["detail"]))
        for failure in check["failures"]:
            print("        - %s" % failure)
    print()
    print("JOURNAL_RECONCILIATION: %s" % ("PASS" if result["passed"] else "FAIL"))
    return 0 if result["passed"] else 1


__all__ = ["Check", "reconcile_journal", "reconcile_captures",
           "recheck_publication_grade", "reconcile_committed_files", "run",
           "main"]


if __name__ == "__main__":
    raise SystemExit(main())
