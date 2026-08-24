"""PTF-MARRIOTT-ACCORDION-LOCATOR-HARDENING-021 -- two templates, one locator.

020 acquired all seventeen remaining Milwaukee Marriott properties and found,
on the way, that one of them stored a policy that understates what a guest
pays. This module explains why, measures how far it reaches, and proves the
corrected locator over the captures already on disk.

THE ROOT CAUSE
--------------
Marriott serves two property-page templates and the Marriott locator list saw
one of them.

    icon container   <span class="icon-pet-friendly">
                     <div class="pb-2 t-font-s">Pet Policy</div>
                     ...wording...

    accordion        <div class="accordion-content ...">
                     <b class="d-block t-font-m ...">Pet Policy</b>
                     <p>...wording...</p>

Three of the seventeen use the accordion form and carry NO ``icon-pet`` span at
all. The old list held three selectors: one requiring a ``div`` heading and two
requiring the icon. All three miss the accordion, so the generic signal walk
ran in their place -- and on Marriott the generic walk tends to land on the
FAQ, which answers the same question in different words and not always with the
same completeness.

Twice that was harmless. On The Trade it was not: the FAQ says "A
non-refundable pet fee of $125.00 per stay applies" and the property's own Pet
Policy panel says "Pet deposit starts at $125 (may increase for suites) + $20
daily pet fee. Non-Refundable Pet Fee Per Stay: $125.00". Same hotel, same
page, one surface missing a recurring charge.

WHY THE OTHER FOURTEEN WERE NEVER AT RISK
-----------------------------------------
They carry the ``<div>Pet Policy</div>`` heading, so the first locator matched
and returned before anything else was tried. Nothing about their handling
changes here, and the differential below is what proves that rather than
asserting it.

WHAT AN OFFLINE DIFFERENTIAL CAN AND CANNOT SAY
-----------------------------------------------
The live walk runs Playwright selectors against a rendered page and reads
``innerText``. This module evaluates the SAME expressions with lxml against the
persisted document and reads ``text_content``. Those are different text
extractors -- PTF-CANONICAL-POLICY-LOCATOR-PARITY-019 is the whole argument
that a DOM walk and a static walk are not required to agree -- so what is
proved here is WHICH CONTAINER each selector binds, and what that container
holds, not a byte-identical prediction of the next live capture.

That is the right question for this work order. The failure being fixed is a
container that was never selected at all.

NOTHING HERE MUTATES A RECORD
-----------------------------
It reads captures, compares, and writes a queue. No observation is rewritten,
no persisted ``policy-block.txt`` is edited to pretend the old locator chose
something else, and nothing is published.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from lxml import html as LH                                          # noqa: E402

from scripts.pettripfinder.acquisition import marriott_decision_020 as D  # noqa: E402
from scripts.pettripfinder.brightdata import marriott_surface as MS   # noqa: E402
from scripts.pettripfinder.brightdata import policy_surface as PS     # noqa: E402

WORK_ORDER = "PTF-MARRIOTT-ACCORDION-LOCATOR-HARDENING-021"
MARKET = "milwaukee-wi"

REPORTS = REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
REPORT = REPORTS / "ptf_marriott_template_021.json"
QUEUE = REPORTS / "ptf_marriott_rederivation_queue_021.json"

RUN_ROOT = D.RUN_ROOT / D.PRODUCTION_RUN_ID / D.PRODUCTION_RUN_ID

# --------------------------------------------------------------------------- #
# Phase 2 -- template classes.
# --------------------------------------------------------------------------- #

TEMPLATE_ICON = "TEMPLATE_ICON_CONTAINER"
TEMPLATE_ACCORDION = "TEMPLATE_ACCORDION"
TEMPLATE_OTHER = "OTHER"

#: The i18n dictionary entry that names the same words inside a <script>. Its
#: only role here is to be COUNTED, so a test can show the locator ignores a
#: decoy that is present on almost every page.
I18N_DECOY = "hws.petPolicy"


def _text(node) -> str:
    return MS.collapse(node.text_content())


@dataclass(frozen=True)
class TemplateFinding:
    """What one persisted Marriott document renders, and where."""

    canonical_name: str
    template: str
    heading_evidence: str
    icon_spans: int
    div_headings: int
    b_headings: int
    i18n_decoys: int


def classify_document(name: str, html: str) -> TemplateFinding:
    """Which template this page uses, from its own markup.

    Read from the elements rather than from a text search: the words "Pet
    Policy" appear on nearly every Marriott page inside a JavaScript
    dictionary, and a classifier that counted those would call every page
    policy-bearing.
    """
    doc = LH.fromstring(html)
    divs = doc.xpath(MS.HEADING_PARENT_XPATH) if hasattr(MS, "HEADING_PARENT_XPATH") \
        else doc.xpath("//div[normalize-space(text())='Pet Policy']/parent::*")
    bolds = doc.xpath("//b[normalize-space(text())='Pet Policy']/parent::*")
    icons = len(doc.xpath("//*[contains(@class,'icon-pet')]"))

    if divs:
        template, evidence = TEMPLATE_ICON, "<div>Pet Policy</div> heading"
    elif bolds:
        template, evidence = TEMPLATE_ACCORDION, "<b>Pet Policy</b> accordion heading"
    else:
        template, evidence = TEMPLATE_OTHER, "no exact 'Pet Policy' heading element"

    return TemplateFinding(
        canonical_name=name, template=template, heading_evidence=evidence,
        icon_spans=icons, div_headings=len(divs), b_headings=len(bolds),
        i18n_decoys=html.count(I18N_DECOY))


# --------------------------------------------------------------------------- #
# The locator, evaluated offline.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class OfflineHit:
    found: bool
    strategy: str = ""
    text: str = ""
    chars: int = 0
    features: int = 0


def locate_offline(html: str, xpaths: Sequence[Tuple[str, str]]) -> OfflineHit:
    """Evaluate the structural locators in order, first in-bounds match wins.

    The same order and the same size bounds the live walk applies, so a
    difference between old and new here is a difference of SELECTOR COVERAGE
    and not of policy.
    """
    doc = LH.fromstring(html)
    for locator_id, xpath in xpaths:
        for node in doc.xpath(xpath):
            text = _text(node)
            if PS.MIN_BLOCK_CHARS <= len(text) <= PS.MAX_BLOCK_CHARS:
                return OfflineHit(found=True, strategy=locator_id, text=text,
                                  chars=len(text),
                                  features=PS.policy_features(text))
    return OfflineHit(found=False)


#: The locator list as it stood before this work order. Kept explicitly so the
#: differential compares against what actually shipped, rather than against a
#: reconstruction of it.
OLD_STRUCTURAL_XPATHS: Tuple[Tuple[str, str], ...] = (
    ("pet_policy_heading_parent",
     "//div[normalize-space(text())='Pet Policy']/parent::*"),
)

NEW_STRUCTURAL_XPATHS: Tuple[Tuple[str, str], ...] = MS.STRUCTURAL_XPATHS


# --------------------------------------------------------------------------- #
# Phases 6 and 7 -- the differential and the material-difference queue.
# --------------------------------------------------------------------------- #

UNCHANGED = "UNCHANGED"
EXPANDED = "EXPANDED"
CHANGED = "CHANGED"
NEWLY_LOCATED = "NEWLY_LOCATED"
STILL_UNRESOLVED = "STILL_UNRESOLVED"

FEE_UNDERSTATED = "FEE_UNDERSTATED"
FEE_OVERSTATED = "FEE_OVERSTATED"
FEE_COMPONENT_MISSING = "FEE_COMPONENT_MISSING"
WEIGHT_MISSING = "WEIGHT_MISSING"
PET_COUNT_MISSING = "PET_COUNT_MISSING"
SPECIES_MISSING = "SPECIES_MISSING"
REFUSAL_MISREAD = "REFUSAL_MISREAD"
NO_MATERIAL_CHANGE = "NO_MATERIAL_CHANGE"

_MONEY = re.compile(r"\$\s?\d[\d,]*(?:\.\d{2})?")
_RECURRING = re.compile(r"\b(?:daily|per\s+night|per\s+day|nightly)\b", re.I)
_DEPOSIT = re.compile(r"\bdeposit\b", re.I)
_WEIGHT = re.compile(r"\d+(?:\.\d+)?\s*(?:lbs?|pounds?)\b", re.I)
_COUNT = re.compile(r"\b(?:limit|maximum number of pets)\b", re.I)


def read_block(text: str) -> Dict:
    """The Marriott reader over a block, all the way to the extraction.

    Carried through to ``to_extraction`` rather than stopping at the raw
    reading, because the question this work order asks is what a RECORD would
    say -- and the fee a record asserts, or declines to assert, is decided
    there.
    """
    if not (text or "").strip():
        return {"facts": {}, "withheld": {}, "charges": [],
                "extraction": {}, "unrepresented": []}
    reading = MS.parse_policy_block(text, locator_id="marriott_template_021")
    result = MS.to_extraction(reading, location="marriott_template_021")
    data = reading.to_dict()
    return {
        "facts": {k: v for k, v in data.items()
                  if k not in ("charges", "withheld", "notes", "locator_id",
                               "unrepresented")
                  and v not in (None, "", [], {})},
        "extraction": dict(result.extraction),
        "withheld": dict(result.withheld or {}),
        "charges": data.get("charges") or [],
        "unrepresented": [dict(u) for u in reading.unrepresented],
    }


def classify_change(old_text: str, new_hit: OfflineHit) -> str:
    if not new_hit.found:
        return STILL_UNRESOLVED
    old = MS.collapse(old_text or "")
    new = MS.collapse(new_hit.text)
    if not old:
        return NEWLY_LOCATED
    if old == new:
        return UNCHANGED
    squash = lambda s: re.sub(r"[^a-z0-9]+", "", s.lower())
    if squash(old) in squash(new):
        return EXPANDED
    return CHANGED


def material_issue(old_block: str, new_block: str,
                   old_read: Mapping, new_read: Mapping,
                   stored_fields: Sequence[str] = ()) -> Tuple[str, str]:
    """Whether the corrected block changes what a guest would be told.

    Ordered by how badly a reader could be misled. Money first, because a
    charge a guest does not expect is the failure this work order exists to
    stop; a missing weight or count withholds information but does not
    misstate a price.
    """
    old_money = set(_MONEY.findall(old_block or ""))
    new_money = set(_MONEY.findall(new_block or ""))
    old_recurring = bool(_RECURRING.search(old_block or ""))
    new_recurring = bool(_RECURRING.search(new_block or ""))
    old_deposit = bool(_DEPOSIT.search(old_block or ""))
    new_deposit = bool(_DEPOSIT.search(new_block or ""))

    if new_recurring and not old_recurring and new_money:
        return (FEE_UNDERSTATED,
                "the corrected block states a recurring charge the stored one "
                "does not; the stored reading understates what a stay costs")
    if new_deposit and not old_deposit:
        return (FEE_COMPONENT_MISSING,
                "the corrected block states a deposit the stored one omits")
    if new_money - old_money:
        return (FEE_COMPONENT_MISSING,
                "the corrected block states amounts the stored one omits: %s"
                % ", ".join(sorted(new_money - old_money)))

    # The block may be UNCHANGED and the stored record still wrong. Where the
    # corrected reader declines to assert a fee because the surface states
    # components the schema cannot carry, a stored record that asserts one is
    # unsafe even though no text moved. Compared against what the 020 record
    # actually asserts, not against a recomputation of it: recomputing puts the
    # corrected reader on both sides of the comparison and hides exactly this.
    withheld_now = (new_read.get("withheld") or {}).get("pet_fee")
    if withheld_now == "SCHEMA_CANNOT_REPRESENT" and "pet_fee" in set(stored_fields):
        return (FEE_COMPONENT_MISSING,
                "the stored record asserts a single pet fee while the block "
                "states components the schema cannot carry together (%s); the "
                "corrected reader withholds it"
                % "; ".join(sorted(u["quote"] for u in
                                   new_read.get("unrepresented") or [])))
    if old_money - new_money:
        return (FEE_OVERSTATED,
                "the stored block states amounts the property's own policy "
                "panel does not: %s" % ", ".join(sorted(old_money - new_money)))

    old_refusal = D.states_a_refusal(old_block or "")
    new_refusal = D.states_a_refusal(new_block or "")
    if old_refusal != new_refusal:
        return (REFUSAL_MISREAD,
                "the two blocks disagree about whether pets are refused")

    if _WEIGHT.search(new_block or "") and not _WEIGHT.search(old_block or ""):
        return (WEIGHT_MISSING, "the corrected block states a weight limit the "
                                "stored one omits")
    if _COUNT.search(new_block or "") and not _COUNT.search(old_block or ""):
        return (PET_COUNT_MISSING, "the corrected block states a pet count the "
                                   "stored one omits")
    added = sorted(set(new_read.get("facts") or {}) - set(old_read.get("facts") or {}))
    if "species_allowed" in added:
        return (SPECIES_MISSING, "the corrected block names species the stored "
                                 "one does not")
    return (NO_MATERIAL_CHANGE, "both blocks state the same terms")


def examine(name: str, attempt_dir: Path, stored: Mapping) -> Dict:
    html = (attempt_dir / "rendered.html").read_text(encoding="utf-8",
                                                     errors="replace")
    finding = classify_document(name, html)
    old_hit = locate_offline(html, OLD_STRUCTURAL_XPATHS)
    new_hit = locate_offline(html, NEW_STRUCTURAL_XPATHS)

    stored_block = (stored.get("usable_policy_detail") or {}).get("block_text") or ""
    stored_locator = (stored.get("usable_policy_detail") or {}).get(
        "policy_locator") or ""

    old_read = read_block(stored_block)
    new_read = read_block(new_hit.text if new_hit.found else "")
    change = classify_change(stored_block, new_hit)
    stored_fields = (stored.get("usable_policy_detail") or {}).get(
        "substantive_fields") or []
    issue, why = material_issue(stored_block, new_hit.text if new_hit.found else "",
                                old_read, new_read, stored_fields)

    old_facts = old_read["extraction"]
    new_facts = new_read["extraction"]
    return {
        "canonical_name": name,
        "sub_brand": stored.get("sub_brand", ""),
        "template": finding.template,
        "heading_evidence": finding.heading_evidence,
        "icon_spans": finding.icon_spans,
        "i18n_decoys": finding.i18n_decoys,
        "stored_policy_locator": stored_locator,
        "stored_record_fields": sorted(stored_fields),
        "stored_block_source": ("brand structural locator"
                                if stored_locator in
                                {i for i, _ in MS.STRUCTURAL_XPATHS}
                                else stored_locator or "none"),
        "old_locator_found": old_hit.found,
        "old_locator_strategy": old_hit.strategy,
        "new_locator_found": new_hit.found,
        "new_locator_strategy": new_hit.strategy,
        "change_class": change,
        "stored_block": stored_block,
        "corrected_block": new_hit.text if new_hit.found else "",
        "stored_block_chars": len(stored_block),
        "corrected_block_chars": new_hit.chars,
        "reader_before": old_facts,
        "reader_after": new_facts,
        "fields_added": sorted(set(new_facts) - set(old_facts)),
        "fields_removed": sorted(set(old_facts) - set(new_facts)),
        "fields_withheld_before": sorted(old_read["withheld"]),
        "withheld_after_detail": new_read["withheld"],
        "unrepresented_components": new_read["unrepresented"],
        "fields_withheld_after": sorted(new_read["withheld"]),
        "charges_before": old_read["charges"],
        "charges_after": new_read["charges"],
        "material_issue": issue,
        "material_reason": why,
    }


def scan() -> Dict:
    run = json.loads(D.RUN_REPORT.read_text(encoding="utf-8-sig"))
    rows: List[Dict] = []
    for stored in run["rows"]:
        name = stored["canonical_name"]
        attempt = D._attempt_dir_for(RUN_ROOT, D._slug_of(name))
        if attempt is None:
            continue
        rows.append(examine(name, attempt, stored))

    templates: Dict[str, int] = {}
    changes: Dict[str, int] = {}
    issues: Dict[str, int] = {}
    for row in rows:
        templates[row["template"]] = templates.get(row["template"], 0) + 1
        changes[row["change_class"]] = changes.get(row["change_class"], 0) + 1
        issues[row["material_issue"]] = issues.get(row["material_issue"], 0) + 1

    queue = [r for r in rows if r["material_issue"] != NO_MATERIAL_CHANGE]
    return {
        "schema": "ptf-marriott-template/1.0",
        "work_order": WORK_ORDER,
        "market": MARKET,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "captures_scanned": len(rows),
        "templates": templates,
        "properties_by_template": {
            t: [r["canonical_name"] for r in rows if r["template"] == t]
            for t in sorted(templates)},
        "old_locator_successes": sum(1 for r in rows if r["old_locator_found"]),
        "new_locator_successes": sum(1 for r in rows if r["new_locator_found"]),
        "change_classes": changes,
        "material_issues": issues,
        "review_queue_size": len(queue),
        "review_queue": [r["canonical_name"] for r in queue],
        "routes_changed": False,
        "readers_changed": False,
        "authority_written": False,
        "observations_updated": False,
        "published": False,
        "rows": rows,
    }


def build_queue(doc: Mapping) -> Dict:
    """The scoped re-derivation queue.

    A queue and not a mutation. The repository's supersession convention
    (GOV-01, and the 018 re-derivation precedent) requires re-derived
    observations to be authored and attested in their own work order; this one
    hardens a locator and states precisely which records that leaves wrong.
    """
    rows = [r for r in doc["rows"] if r["material_issue"] != NO_MATERIAL_CHANGE]
    return {
        "schema": "ptf-marriott-rederivation-queue/1.0",
        "work_order": WORK_ORDER,
        "market": MARKET,
        "generated_at": doc["generated_at"],
        "note": ("Marriott observations whose stored reading materially "
                 "disagrees with the corrected locator's block. Nothing here "
                 "is applied: re-deriving an observation changes what a record "
                 "is ABOUT and needs its own work order and its own "
                 "attestation."),
        "requires_reacquisition": False,
        "reacquisition_note": (
            "The corrected block is already present in the persisted document, "
            "so a re-derivation reads it from disk. No provider call is needed "
            "and no capture is superseded."),
        "published": False,
        "founder_approved": False,
        "items": [{
            "canonical_name": r["canonical_name"],
            "template": r["template"],
            "material_issue": r["material_issue"],
            "reason": r["material_reason"],
            "stored_block": r["stored_block"],
            "corrected_block": r["corrected_block"],
            "corrected_locator": r["new_locator_strategy"],
            "reader_before": r["reader_before"],
            "reader_after": r["reader_after"],
            "fields_added": r["fields_added"],
            "fields_withheld_after": r["fields_withheld_after"],
        } for r in rows],
        "count": len(rows),
    }


def summarise(doc: Dict) -> str:
    lines = ["%s" % doc["work_order"],
             "captures %d | old locator %d | new locator %d | queue %d"
             % (doc["captures_scanned"], doc["old_locator_successes"],
                doc["new_locator_successes"], doc["review_queue_size"]),
             "templates: %s" % doc["templates"], ""]
    for row in doc["rows"]:
        if row["change_class"] == UNCHANGED and \
                row["material_issue"] == NO_MATERIAL_CHANGE:
            continue
        lines.append("%-46s %-22s %-14s %s"
                     % (row["canonical_name"][:46], row["template"][:22],
                        row["change_class"], row["material_issue"]))
        lines.append("     old(%4d): %r" % (row["stored_block_chars"],
                                            row["stored_block"][:110]))
        lines.append("     new(%4d): %r" % (row["corrected_block_chars"],
                                            row["corrected_block"][:110]))
        if row["fields_added"] or row["fields_removed"]:
            lines.append("     fields +%s -%s" % (row["fields_added"],
                                                  row["fields_removed"]))
    lines += ["", "change classes: %s" % doc["change_classes"],
              "material issues: %s" % doc["material_issues"]]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args(argv)
    doc = scan()
    print(summarise(doc))
    if args.write_report:
        REPORT.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False)
                            + "\n").encode("utf-8"))
        queue = build_queue(doc)
        QUEUE.write_bytes((json.dumps(queue, indent=1, ensure_ascii=False)
                           + "\n").encode("utf-8"))
        print("\nreport: %s\nqueue:  %s" % (REPORT, QUEUE))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
