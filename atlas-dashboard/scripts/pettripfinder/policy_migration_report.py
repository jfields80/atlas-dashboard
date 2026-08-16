"""PTF-POLICY-SCHEMA-MIGRATION-001 -- what the migration did, per record.

Three reports, because Phase F has to answer three different questions and a
single number answers none of them:

  * the RECORD log (section 28) -- what changed in each authority record, and
    under which of the four permitted transformation kinds;
  * the AUTHORITY diff (section 42) -- every changed field, classified;
  * the RENDERED diff (section 30) -- what a reader sees differently, which is
    the only one that can hurt anybody.

The rendered diff needs a BEFORE, and the before is a render of the
pre-migration authority. That is taken from a git worktree at the pre-Phase-F
commit rather than reconstructed here: a "before" derived from the same code
that produced the "after" would agree with itself by construction.

    python -m scripts.pettripfinder.policy_migration_report --before <dir>
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.contracts.review_queue import POLICY_PACKAGES     # noqa: E402
from scripts.pettripfinder.policy_migration import (                        # noqa: E402
    load_decisions, load_package, migrate_package,
)

# --------------------------------------------------------------------------- #
# Authority diff (section 42).
# --------------------------------------------------------------------------- #

EXPECTED_SCHEMA = "EXPECTED_SCHEMA_NORMALIZATION"
EXPECTED_TYPED = "EXPECTED_TYPED_VALUE_CONVERSION"
EXPECTED_POLICY = "EXPECTED_REVIEWED_POLICY_NORMALIZATION"
EXPECTED_WITHHOLDING = "EXPECTED_WITHHOLDING_NORMALIZATION"
EXPECTED_APPROVAL = "EXPECTED_APPROVAL_NORMALIZATION"
EXPECTED_COMPUTATION = "EXPECTED_COMPUTATION_METADATA"
UNEXPECTED_AUTHORITY = "UNEXPECTED_AUTHORITY_CHANGE"

#: Which classification a changed record key falls under. Anything not named
#: here is UNEXPECTED, which is the point: the list is the set of changes this
#: phase is allowed to make, and a change outside it must be seen.
_KEY_CLASS = {
    "schema_version": EXPECTED_SCHEMA,
    "identity_key": EXPECTED_SCHEMA,
    "market_id": EXPECTED_SCHEMA,
    "evidence": EXPECTED_SCHEMA,
    "facts": EXPECTED_TYPED,
    "withheld_fields": EXPECTED_WITHHOLDING,
    "service_animal_statement": EXPECTED_POLICY,
    "approval": EXPECTED_APPROVAL,
    "computation_class": EXPECTED_COMPUTATION,
}


def classify_authority_diff(before: Mapping, after: Mapping) -> "OrderedDict[str, List[str]]":
    """Every record key that moved, grouped by classification."""
    out: "OrderedDict[str, List[str]]" = OrderedDict(
        (name, []) for name in (EXPECTED_SCHEMA, EXPECTED_TYPED, EXPECTED_POLICY,
                                EXPECTED_WITHHOLDING, EXPECTED_APPROVAL,
                                EXPECTED_COMPUTATION, UNEXPECTED_AUTHORITY))
    old = {r.get("key"): r for r in before.get("hotels") or ()}
    for record in after.get("hotels") or ():
        key = record.get("key")
        was = old.get(key) or {}
        for name in sorted(set(record) | set(was)):
            if record.get(name) == was.get(name):
                continue
            out[_KEY_CLASS.get(name, UNEXPECTED_AUTHORITY)].append(
                "%s.%s" % (key, name))
    return out


# --------------------------------------------------------------------------- #
# Rendered diff (section 30).
# --------------------------------------------------------------------------- #

MECHANICAL_FORMAT = "MECHANICAL_FORMAT_ONLY"
ACCURACY = "INTENDED_ACCURACY_IMPROVEMENT"
WITHHOLDING_CLARIFICATION = "INTENDED_WITHHOLDING_CLARIFICATION"
STRUCTURED_DETAIL = "INTENDED_STRUCTURED_DETAIL_ADDITION"
APPROVAL_METADATA = "APPROVAL_METADATA_ONLY"
UNEXPECTED_SEMANTIC = "UNEXPECTED_SEMANTIC_CHANGE"

#: Phrases whose appearance identifies what KIND of change a rendered edit is.
#: Matched against the text that was added and the text that was removed, so a
#: classification is always grounded in words that actually moved on the page.
_WITHHOLDING_MARKERS = ("The hotel's wording is unclear",
                        "The hotel's own page states conflicting terms",
                        "The hotel states terms we cannot",
                        "Official source gives a pet-fee range")
_STRUCTURED_MARKERS = ("Property statement on service animals",
                       "Combined weight limit", "Individual weight limit",
                       "Pet charge, 1", "Pet charge, 7", "for up to 2 pets",
                       "up to a maximum of")
#: Pure spelling: the same fact written differently.
#: The exact sentences the renderer prints for a field the source never
#: addressed. A removal drawn from one of these is a silence being replaced.
SILENCE_COPY = ("Not stated by the reviewed source", "Not stated")

#: The rows a SPARSE profile shows in place of facts. A record that stops being
#: sparse loses all three, and their disappearance is the same event as the
#: silence copy's: the page now states something where it previously stated
#: nothing. Listed explicitly, from ``hotel_profile._verified_details``, rather
#: than inferred -- a classifier that guesses which removals are safe is how a
#: fact leaves a page unnoticed.
SPARSE_PRESENTATION = ("Pets welcome (species not specified)",
                       "Fee, pet limit, weight limit",
                       "Breed / unattended rules",
                       "“Not stated” means the reviewed source did not address the "
                       "field — not that the answer is no. Confirm specifics with the "
                       "property before booking.")

_FORMAT_PAIRS = ((" and", ","), (".0", ""), ("0.", ""), ("lb", "pounds"),
                 (" per stay", ""), ("per stay ", ""))


#: Rendered changes reviewed individually and accepted, with the reason. A
#: record is listed here ONLY after its before/after was read in full; the
#: table exists so "zero unexpected changes" is a claim backed by a named
#: review rather than by a classifier that was widened until it agreed.
REVIEWED_RENDER_EXCEPTIONS: Dict[str, Tuple[str, str]] = {
    "Candlewood Suites Columbus North - Polaris by IHG": (
        "INTENDED_WITHHOLDING_CLARIFICATION",
        "The property caps its charge at $75 for stays of 1-6 nights and at $150 "
        "for 7 or more. Schema 1.2 carries ONE cap per record, so the two "
        "ceilings cannot both be stated; publishing either alone would price "
        "most stays wrongly. The cap is withheld with SCHEMA_CANNOT_REPRESENT "
        "and the page says so. This is the single place in the corpus where "
        "canonical 1.2 is less expressive than the legacy record, and it is "
        "recorded as a schema-amendment candidate rather than resolved by "
        "picking a number."),
    "Courtyard Columbus Easton": (
        "INTENDED_WITHHOLDING_CLARIFICATION",
        "Founder decision, PTF-POLICY-SCHEMA-MIGRATION-001A batch 1. The fee "
        "stays withheld; what changed is the sentence. The generic copy said "
        "only that the source conflicts, which is true of every contradiction "
        "in the corpus. The page now names the conflict a guest can actually "
        "put to the hotel -- the same $50 is stated once per night and once "
        "per stay."),
    "Sheraton Suites Columbus Worthington": (
        "INTENDED_WITHHOLDING_CLARIFICATION",
        "Founder decision, PTF-POLICY-SCHEMA-MIGRATION-001A batch 5 and A2. Two "
        "changes, both directed. The fee sentence now names the per-pet versus "
        "per-stay conflict, which is invisible for one animal and $75 apart for "
        "two. And the weight limit is WITHHELD rather than resolved: the page "
        "sets 50 lb but disagrees with itself about whether a pet weighing "
        "exactly 50 lb qualifies, and choosing the permissive reading would "
        "publish an answer the property never gave."),
    "Sonesta Columbus Downtown": (
        "INTENDED_ACCURACY_IMPROVEMENT",
        "Founder decision, PTF-POLICY-SCHEMA-MIGRATION-001A evidence sweep. Two "
        "rows leave the page, both because the property never wrote them. "
        "\"Breed restrictions: No breed restrictions\" appears nowhere in the "
        "captured page and reverts to silence. \"Other restrictions: Guests must "
        "be 21 years of age or older to check into the hotel\" is a general "
        "check-in rule; this was the only record in 156 publishing it as a pet "
        "restriction, and it remains visible in the verbatim quote where its "
        "three sibling Wyndham records keep it."),
}


def _visible(html: str) -> str:
    body = re.sub(r"<script.*?</script>", "", html, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body))


def classify_render_diff(before: str, after: str, name: str = "") -> str:
    """The single strongest classification for one profile's edits."""
    if before == after:
        return ""
    if name in REVIEWED_RENDER_EXCEPTIONS:
        return REVIEWED_RENDER_EXCEPTIONS[name][0]
    b, a = _visible(before), _visible(after)
    matcher = difflib.SequenceMatcher(None, b, a, autojunk=False)
    edits = [(b[i1:i2], a[j1:j2]) for tag, i1, i2, j1, j2
             in matcher.get_opcodes() if tag != "equal"]
    added = " ".join(y for _, y in edits)
    removed = " ".join(x for x, _ in edits)

    if any(m in added for m in _WITHHOLDING_MARKERS):
        return WITHHOLDING_CLARIFICATION
    if any(m in added for m in _STRUCTURED_MARKERS):
        return STRUCTURED_DETAIL
    # A removal that is not matched by an addition, and is not one of the known
    # spelling normalisations, is a fact leaving the page. That is the one thing
    # this phase must never do by accident.
    for x, y in edits:
        if x.strip() and not y.strip() and len(x.strip()) > 12:
            if not any(x.strip().startswith(p[0].strip() or p[0]) for p in _FORMAT_PAIRS):
                # A removal that takes the SILENCE copy off the page is an
                # accuracy improvement by definition: the record now states
                # something where it previously said nothing.
                #
                # Tested by asking whether the removed text is PART OF the
                # silence sentence, not by searching for the sentence inside
                # the removal. The differ splits mid-word when the replacement
                # is shorter -- "Not stated by the reviewed source" becoming
                # "Dogs" leaves the fragment "tated by the reviewed source",
                # which contains no searchable landmark of its own.
                # Punctuation is trimmed from both ends before the containment
                # test. The differ splits wherever the two strings stop
                # agreeing, which routinely puts a leading ". " or a trailing
                # half-word on the fragment -- "in copy" then fails on text
                # that plainly IS part of the copy, and a wholly additive
                # change reads as a fact leaving the page.
                fragment = x.strip().strip(".,;:—-“”\"' ")
                silence = any(fragment and fragment in copy
                              for copy in SILENCE_COPY + SPARSE_PRESENTATION)
                return ACCURACY if silence else UNEXPECTED_SEMANTIC
    if any(a_ in added or b_ in removed for a_, b_ in _FORMAT_PAIRS):
        return MECHANICAL_FORMAT
    return ACCURACY


# --------------------------------------------------------------------------- #
# Report.
# --------------------------------------------------------------------------- #

def package_at(ref: str, market_id: str) -> Dict[str, Any]:
    """A policy package as it stood at ``ref``.

    The log describes a TRANSITION, so it has to be computed against the
    pre-migration authority. Reading the working tree instead would take the
    migration's idempotence path -- correctly reporting that an already-1.2
    record needs no changes -- and produce a log saying nothing happened.
    """
    import subprocess
    path = "atlas-dashboard/launch_packages/pettripfinder/%s" % POLICY_PACKAGES[market_id]
    blob = subprocess.run(["git", "show", "%s:%s" % (ref, path)],
                          cwd=str(_REPO_ROOT), capture_output=True,
                          check=True).stdout
    return json.loads(blob.decode("utf-8-sig"))


def record_log(baseline_ref: str = "") -> List[Dict[str, Any]]:
    """The section 28 log for the migration of ``baseline_ref`` into 1.2."""
    decisions = load_decisions()
    rows: List[Dict[str, Any]] = []
    for market_id in POLICY_PACKAGES:
        document = (package_at(baseline_ref, market_id) if baseline_ref
                    else load_package(market_id))
        _, results = migrate_package(document, market_id, decisions)
        rows.extend(dict(r.as_log_row()) for r in results)
    return rows


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", default="",
                        help="directory of <tag>_before.json rendered baselines")
    parser.add_argument("--baseline-ref", default="HEAD",
                        help="git ref holding the pre-migration authority")
    parser.add_argument("--output", default="")
    args = parser.parse_args(argv)

    log = record_log(args.baseline_ref)
    counts: "OrderedDict[str, int]" = OrderedDict()
    classes: "OrderedDict[str, int]" = OrderedDict()
    for row in log:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
        classes[row["computation_class"]] = classes.get(row["computation_class"], 0) + 1

    print("=== RECORD LOG: %d records" % len(log))
    for status, count in counts.items():
        print("  %-30s %d" % (status, count))
    print("  computation class distribution")
    for name, count in sorted(classes.items()):
        print("    %-46s %d" % (name, count))
    print("  silence markers removed :",
          sum(len(r["silence_markers_removed"]) for r in log))
    print("  withheld fields kept    :", sum(len(r["withheld_fields"]) for r in log))
    print("  evidence refs added     :", sum(r["evidence_refs_added"] for r in log))
    print("  unowned fields preserved:",
          min(len(r["unowned_fields_kept"]) for r in log), "-",
          max(len(r["unowned_fields_kept"]) for r in log), "per record")

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps({"records": log}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8", newline="\n")
        print("  written:", args.output)
    return 0


if __name__ == "__main__":                            # pragma: no cover
    raise SystemExit(main())
