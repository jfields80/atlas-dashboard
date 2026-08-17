"""PTF-DAYTON-RECERTIFICATION-001 Pass B -- policy corrections + founder packet.

Pass A bound all 47 published Dayton records to their page artifacts. This pass
applies the thirteen deterministic corrections the recertification audit found,
and presents them to the founder against their FINAL hashes. It writes no
approval.

The one rule Group A exists to enforce
--------------------------------------
A field cannot be withheld as contradictory or ambiguous while the same
conflicting monetary claim reaches the reader anyway through
``general_restrictions``. Four Dayton records did exactly that -- SpringHill
Troy withholds ``pet_fee``, ``fee_basis`` AND ``fee_tiers`` as
SOURCE_CONTRADICTORY and then printed the whole priced ladder as prose, so the
public page carried a withheld-charge notice directly above the numbers it was
withholding. The withholding decision had no effect on what anyone saw.

So the monetary prose goes, and nothing else does: the exact source sentence
stays in the evidence array, the withholding stays exactly as recorded, and no
clean fee is manufactured from a contradiction. Where the same prose also
carried a genuine behavioural restriction ("Dogs only, no cats"), that survives.

What Group B is careful about
-----------------------------
Deleting prose must not delete a FACT. Two records stated something real inside
their monetary sentence -- Staybridge that its fee is nonrefundable, Courtyard
that its $75 is quoted before a 17.25% tax -- and schema 1.2 can carry both
(``pet_fee.refundable``, ``pet_fee.tax_relationship``). Those move into the
canonical fields where they belong instead of being lost with the prose. What
does NOT move is Courtyard's "($87.94)": that is the source's own arithmetic on
a figure already published, and minting it as a second amount would invent a
charge the property never listed separately.

The ESA ceiling alignment
-------------------------
Dayton's four Extended Stay America records already refuse to publish a price,
which is correct -- but they record the refusal as SOURCE_AMBIGUOUS, and the
source is not ambiguous. It is perfectly clear: it states a CEILING. Cleveland
settled this under founder decision D09 with ``SCHEMA_CANNOT_REPRESENT`` and the
exact ceiling sentence retained in the evidence array. Dayton retained neither
sentence, so a charge the page states appears nowhere in the record. Both are
aligned here, on the same four records -- no fourteenth record is opened.

Why a policy pass touched the renderer
--------------------------------------
Removing the leak was a REGRESSION until it did. Home2 Suites Dayton Beavercreek
withholds its fee ladder and publishes a $75 scalar, and the reader was warned
that "$75 is not the whole charge" only because the withheld ladder had ALSO
leaked into its restriction text -- so cleaning up the leak took the warning
with it. The warning now rests on the withholding decision itself, and
``second_amount_note`` is given the record's withholding decisions instead of
building its view from facts alone. Three further records that never had a leak
to lean on gained the same warning: they had been printing a ladder's first rung
as the fee. Four records gain a caveat, none loses anything, no market's
authority moved.

Governance
----------
Pass B changes facts and evidence, so record_hash AND evidence_hash both move.
No approval is written. Every corrected record stays
MACHINE_REVIEWED_PENDING_OPERATOR, and the approval preserved under
``supersedes`` remains the FOUNDER's -- never Pass A's machine block, which
would put an agent's name where a reader looks for the last human decision.

Run:
  python -m scripts.pettripfinder.dayton_pass_b_policy_corrections \
      --data-root C:/Atlas/atlas-dashboard/data [--apply]
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.contracts import enums                            # noqa: E402
from scripts.pettripfinder.contracts import evidence as evidence_contract    # noqa: E402
from scripts.pettripfinder.contracts import policy_schema                    # noqa: E402
from scripts.pettripfinder.dayton_pass_a_artifact_verification import (      # noqa: E402
    CAPTURE_RUNS, RUN_ROOT, alias_covered_facts, index_captures,
)
from scripts.pettripfinder.policy_migration import (                         # noqa: E402
    evidence_hash, evidence_ref_for, record_hash,
)

MARKET = "dayton-oh"
WORK_ORDER = "PTF-DAYTON-RECERTIFICATION-001"
PASS_NAME = "Pass B"
PASS_DATE = "2026-08-16"
AGENT_IDENTITY = "claude-opus-5 (%s %s, agent)" % (WORK_ORDER, PASS_NAME)
PASS_A_IDENTITY = "claude-opus-5 (%s Pass A, agent)" % WORK_ORDER

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
FACTS_PATH = LP / ("hotel_policy_facts_%s.json" % MARKET)
PACKET_PATH = LP / "dayton_passB_founder_review_packet.json"
PASS_A_REPORT = LP / "dayton_artifact_verification_001.json"
CONTRACT_PATH = (_REPO_ROOT / "deploy" / "netlify" / "release_contracts"
                 / ("%s.json" % MARKET))

APPROVE = "APPROVE_CORRECTED_RECORD"
HOLD = "HOLD"


# --------------------------------------------------------------------------- #
# The corrections, declared.
# --------------------------------------------------------------------------- #

def _gr(text: Optional[str]) -> Dict:
    """Set general_restrictions to ``text``, or drop the field when None."""
    return {"general_restrictions": text}


#: identity_key -> the correction. Declarative so the diff a founder reviews is
#: the same object the code applies; nothing is computed behind their back.
CORRECTIONS: "OrderedDict[str, Dict]" = OrderedDict([

    # ---------------- GROUP A: withholding defeated by prose ---------------- #
    ("springhill suites troy dayton", {
        "decision_id": "DAY-B01",
        "group": "A_MONETARY_LEAK",
        "facts": _gr("Dogs only, no cats."),
        "rationale":
            "pet_fee, fee_basis and fee_tiers are all withheld "
            "SOURCE_CONTRADICTORY, and general_restrictions then published the "
            "entire priced ladder -- $75 / $150 / $250 by stay length -- so the "
            "profile showed a withheld-charge notice directly above the numbers "
            "being withheld. The ladder is removed. 'Dogs only, no cats' is a "
            "genuine behavioural restriction and survives verbatim.",
        "public_change":
            "The priced ladder disappears from Other restrictions. The withheld "
            "pet-charge notice now stands alone, which is what the record "
            "always decided.",
    }),
    ("towneplace suites by marriott dayton beavercreek", {
        "decision_id": "DAY-B02",
        "group": "A_MONETARY_LEAK",
        "facts": _gr(None),
        "rationale":
            "pet_fee is withheld SOURCE_AMBIGUOUS and fee_basis "
            "SOURCE_CONTRADICTORY because the page lists a per-stay amount and "
            "a per-night amount without saying which governs. "
            "general_restrictions published BOTH, adjacent and unqualified, "
            "which a reader takes as $100 plus $20 a night. The sentence is "
            "wholly monetary, so the field is dropped rather than trimmed. No "
            "amount is chosen between the two; the source wording is retained "
            "in evidence.",
        "public_change":
            "Other restrictions disappears. Both withheld-charge notices remain.",
    }),
    ("hilton garden inn dayton beavercreek", {
        "decision_id": "DAY-B03",
        "group": "A_MONETARY_LEAK",
        "facts": _gr("dogs & cats only. Two pets max per room."),
        "rationale":
            "fee_tiers is withheld SOURCE_AMBIGUOUS because the page calls the "
            "second amount 'additional' without saying what it is added to -- "
            "and general_restrictions published that exact unresolved phrasing, "
            "'$75(1-5 nights) additional $75(5+ night)'. The monetary clause is "
            "removed; the species and pet-count clauses are genuine "
            "restrictions and are kept in the source's own words.",
        "public_change":
            "The two $75 amounts disappear from Other restrictions; the species "
            "and two-pet clauses remain.",
    }),
    ("home2 suites by hilton dayton beavercreek", {
        "decision_id": "DAY-B04",
        "group": "A_MONETARY_LEAK",
        "facts": _gr(None),
        "rationale":
            "fee_tiers is withheld because the page truncates the first band's "
            "amount, and species_allowed is withheld because the same line "
            "truncates mid-phrase -- yet general_restrictions published the "
            "truncation raw: '75.00(1-4n),$125(5+n) 2petsMax,dog/cat on'. Every "
            "clause in it is either the withheld money or the withheld "
            "truncation, so nothing survives trimming and the field is dropped. "
            "pet_count_limit 2 is already canonical and unaffected.",
        "public_change":
            "Other restrictions disappears, and with it the mangled 'dog/cat on' "
            "fragment. Both withheld notices remain.",
    }),

    # ------------- GROUP B: duplicated / tax-inclusive prose ---------------- #
    ("staybridge suites miamisburg", {
        "decision_id": "DAY-B05",
        "group": "B_DUPLICATED_PROSE",
        "facts": {
            "general_restrictions": None,
            "pet_fee.refundable": False,
        },
        "rationale":
            "general_restrictions duplicated the two-rung ladder already "
            "carried canonically in fee_tiers ($50 per pet for nights 1-6, $150 "
            "per pet for 7+), so the same charge was published twice in two "
            "shapes. The duplicate prose is removed and the canonical ladder is "
            "untouched. The sentence also stated 'Fee is nonrefundable', which "
            "is a real fact and would have been lost with the prose -- schema "
            "1.2 carries it as pet_fee.refundable, so it moves there rather "
            "than disappearing.",
        "public_change":
            "The duplicated ladder leaves Other restrictions; the fee ladder "
            "and its longer-stay notice are unchanged. Non-refundability is now "
            "a structured field rather than a sentence.",
    }),
    ("courtyard by marriott springfield downtown", {
        "decision_id": "DAY-B06",
        "group": "B_DUPLICATED_PROSE",
        "facts": {
            "general_restrictions": None,
            "pet_fee.refundable": False,
            "pet_fee.tax_relationship": enums.TAX_PLUS,
        },
        "rationale":
            "general_restrictions carried 'Pets allowed with USD 75 + 17.25% "
            "tax, non-refundable fee per stay ($87.94)' -- a priced charge in a "
            "restrictions field. The $75 per-stay fee is already canonical. Two "
            "further facts in that sentence are representable and move to the "
            "fields that exist for them: the charge is quoted before tax "
            "(tax_relationship plus_tax) and it is non-refundable "
            "(refundable false). The '($87.94)' does NOT become a second "
            "amount: it is the source's own arithmetic on the figure already "
            "published, and minting it would invent a charge the property never "
            "listed separately. The exact sentence stays in evidence.",
        "public_change":
            "Other restrictions disappears. The fee reads as $75 per stay plus "
            "tax, non-refundable, instead of as a sentence containing a total.",
    }),

    # ---------------- GROUP C: service-animal statements -------------------- #
    ("days inn by wyndham sidney", {
        "decision_id": "DAY-B07",
        "group": "C_SERVICE_ANIMAL",
        "service_animal_statement": {"stated": True, "charges_stated":
                                     enums.SERVICE_ANIMAL_NO_CHARGE},
        "add_evidence": [{
            "field": "service_animal_exception",
            "quote": "Service Animals - ADA-defined service animals are welcome "
                     "free of charge.",
            "value": "true",
        }],
        "rationale":
            "The property's page carries the Wyndham service-animal block and "
            "the record did not record it -- while both Dayton La Quintas, on "
            "the identical surface with the identical sentence, do. Same brand, "
            "same wording, opposite treatment. Mapped conservatively: stated "
            "true, charges_stated no_charge, because the sentence says 'free of "
            "charge' in those words and nothing broader is claimed.",
        "public_change":
            "A service-animal row appears on the profile, as it already does on "
            "the two La Quintas.",
    }),

    # ---------------- GROUP C + ESA ceiling alignment ----------------------- #
    ("extended stay america suites dayton fairborn",
     {"decision_id": "DAY-B08", "group": "C_SERVICE_ANIMAL_AND_ESA_CEILING"}),
    ("extended stay america suites dayton south",
     {"decision_id": "DAY-B09", "group": "C_SERVICE_ANIMAL_AND_ESA_CEILING"}),
    ("extended stay america suites dayton north",
     {"decision_id": "DAY-B10", "group": "C_SERVICE_ANIMAL_AND_ESA_CEILING"}),
    ("extended stay america select suites dayton miamisburg",
     {"decision_id": "DAY-B11", "group": "C_SERVICE_ANIMAL_AND_ESA_CEILING"}),

    # ---------------- GROUP D: fee-scope pointer repairs -------------------- #
    ("la quinta inn and suites by wyndham fairborn wright patterson",
     {"decision_id": "DAY-B12", "group": "D_POINTER_REPAIR"}),
    ("la quinta inn and suites by wyndham miamisburg dayton south",
     {"decision_id": "DAY-B13", "group": "D_POINTER_REPAIR"}),
])

#: The four ESA records take an identical correction, so it is written once.
#: Their pages are byte-different (different properties) but the pet-policy
#: block is the chain's standard wording, verified contiguous on each capture
#: before anything is written.
ESA_CEILING_FIRST_SIX = (
    "Pet fees: Not to exceed a $25.00 per day cleaning fee plus tax, for the "
    "first six (6) nights, per pet.")
ESA_CEILING_THEREAFTER = (
    "Each day thereafter there is a pet cleaning fee not to exceed a $15.00 "
    "per day plus tax, per pet.")
ESA_SERVICE_ANIMAL = "Service animals will be exempt from this charge."

ESA_CORRECTION: Dict = {
    "service_animal_statement": {"stated": True, "charges_stated":
                                 enums.SERVICE_ANIMAL_NO_CHARGE},
    "add_evidence": [
        {"field": "service_animal_exception", "quote": ESA_SERVICE_ANIMAL,
         "value": "true"},
        {"field": "cleaning_fee", "quote": ESA_CEILING_FIRST_SIX,
         "value": "CEILING_25_PER_DAY_PER_PET_NIGHTS_1_6"},
        {"field": "cleaning_fee", "quote": ESA_CEILING_THEREAFTER,
         "value": "CEILING_15_PER_DAY_PER_PET_NIGHTS_7_PLUS"},
    ],
    "withheld": {
        "pet_fee": {
            "reason_code": enums.SCHEMA_CANNOT_REPRESENT,
            "reason":
                "The property states its charge only as a ceiling -- 'Not to "
                "exceed a $25.00 per day cleaning fee plus tax' for the first "
                "six nights, and 'not to exceed a $15.00 per day' thereafter. "
                "CEILING != PRICE: schema 1.2 fee fields carry exact prices "
                "and no ceiling qualifier, so publishing either figure would "
                "assert a charge the page does not state. Both exact sentences "
                "are retained in the evidence array.",
        },
        "cleaning_fee": {
            "reason_code": enums.SCHEMA_CANNOT_REPRESENT,
            "reason":
                "The page names this charge a cleaning fee, states it plus "
                "tax, per pet, and changes its ceiling after the sixth night. "
                "Every amount it gives is a ceiling rather than a price, so no "
                "cleaning fee publishes. Recorded under the name the property "
                "uses, so a reader looking for a cleaning fee is answered "
                "rather than told nothing.",
        },
    },
    "rationale":
        "Two corrections on one record. (1) The page states 'Service animals "
        "will be exempt from this charge' and the record did not carry it. "
        "(2) The ceiling refusal was already correct in substance -- no price "
        "is published -- but was recorded as SOURCE_AMBIGUOUS, and this source "
        "is not ambiguous: it is entirely clear that it states a ceiling. "
        "Cleveland settled this under founder decision D09 as "
        "SCHEMA_CANNOT_REPRESENT with the exact ceiling sentence retained in "
        "evidence; Dayton retained neither sentence, so a charge the page "
        "states appeared nowhere in the record. Both are aligned to the "
        "Cleveland interpretation. No fee becomes publishable and no fact "
        "changes.",
    "public_change":
        "A service-animal row appears. The pet-charge notice changes from an "
        "ambiguity notice to a schema/ceiling notice, and a cleaning-fee row "
        "appears carrying the same, so the reader is told a ceiling exists "
        "instead of being told nothing.",
}

#: Both La Quintas: the scope is stated in wording already inside the record on
#: the pet_fee entry, and no fee_scope pointer cites it.
LA_QUINTA_QUOTE = ("Fees - Non-refundable 25 USD nightly for up to 2 pets. "
                   "Max 75 USD per stay.")
LA_QUINTA_CORRECTION: Dict = {
    "add_evidence": [{
        "field": "fee_scope",
        "quote": LA_QUINTA_QUOTE,
        "value": "per room, covering up to 2 pets",
    }],
    "rationale":
        "pet_fee.scope is per_room with scope_pet_allowance 2, which the source "
        "states in the words 'nightly for up to 2 pets' -- one charge covering "
        "two animals. That wording is already in the record on the pet_fee "
        "entry, but no fee_scope pointer cited it, so the published scope had "
        "no citation of its own. A pointer is added. The fact is not touched, "
        "no source text is invented, and the quote is the property's own "
        "sentence verified contiguous in the captured page.",
    "public_change":
        "None. Scope already rendered as Per room; this adds the citation "
        "behind it.",
}

for _key, _entry in CORRECTIONS.items():
    if _entry["group"] == "C_SERVICE_ANIMAL_AND_ESA_CEILING":
        _entry.update(copy.deepcopy(ESA_CORRECTION))
    elif _entry["group"] == "D_POINTER_REPAIR":
        _entry.update(copy.deepcopy(LA_QUINTA_CORRECTION))


# --------------------------------------------------------------------------- #
# Application.
# --------------------------------------------------------------------------- #

def _bare(sha: str) -> str:
    return sha[7:] if sha.startswith("sha256:") else sha


def load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _set_fact(hotel: Dict, path: str, value) -> Tuple[str, object, object]:
    """Apply one declared fact edit; ``None`` deletes. Returns before/after."""
    facts = hotel["facts"]
    if "." in path:
        head, tail = path.split(".", 1)
        node = facts.get(head)
        if not isinstance(node, dict):
            raise AssertionError("%s: %s is not an object" % (
                hotel["identity_key"], head))
        before = node.get(tail, "<absent>")
        if value is None:
            node.pop(tail, None)
        else:
            node[tail] = value
        return path, before, ("<absent>" if value is None else value)
    before = facts.get(path, "<absent>")
    if value is None:
        facts.pop(path, None)
    else:
        facts[path] = value
    return path, before, ("<absent>" if value is None else value)


def apply_correction(hotel: Dict, correction: Dict, page_text: str,
                     artifact_sha: str, captured_at: str,
                     capture_method: str) -> Dict:
    """Apply one record's correction and return its before/after ledger."""
    changes: List[Dict] = []

    for path, value in (correction.get("facts") or {}).items():
        field, before, after = _set_fact(hotel, path, value)
        changes.append(OrderedDict([
            ("kind", "FACT"), ("field", "facts." + field),
            ("before", before), ("after", after)]))

    if "service_animal_statement" in correction:
        before = hotel.get("service_animal_statement", "<absent>")
        hotel["service_animal_statement"] = copy.deepcopy(
            correction["service_animal_statement"])
        changes.append(OrderedDict([
            ("kind", "FACT"), ("field", "service_animal_statement"),
            ("before", before), ("after", hotel["service_animal_statement"])]))

    for spec in correction.get("add_evidence") or ():
        # A quote may only enter the record if the captured page actually
        # contains it, contiguously. This is the same standard Pass A held the
        # existing quotes to, applied before anything new is written.
        if not evidence_contract.quote_is_contiguous(spec["quote"], page_text):
            raise AssertionError(
                "%s: proposed %s quote is not contiguous in the captured page "
                "text: %r" % (hotel["identity_key"], spec["field"],
                              spec["quote"][:90]))
        entry = OrderedDict([
            ("field", spec["field"]),
            ("quote", spec["quote"]),
            ("source_url", hotel["source_url"]),
            ("value", spec["value"]),
            ("evidence_ref", ""),
            ("artifact_class", enums.PUBLICATION_GRADE_EVIDENCE),
            ("artifact_sha256", "sha256:%s" % artifact_sha),
            ("artifact_kind", enums.ARTIFACT_RENDERED_HTML),
            ("captured_at", captured_at),
            ("capture_method", capture_method),
            ("source_grade", enums.GRADE_PT1_FIRST_PARTY),
            # Declared, greppable, and stronger than the check it stands in
            # for: the legacy ``evidence_quote`` summary is a stitched subset
            # of the page, so a sentence genuinely on the page can be absent
            # from it. This quote was asserted contiguous in the ARTIFACT --
            # the captured bytes named by artifact_sha256 -- which is the page
            # itself rather than a summary of it.
            ("contiguity_verified", True),
            ("provenance_note",
             "%s %s: quote asserted contiguous in the captured page text of "
             "artifact sha256:%s before this entry was written. Verified "
             "against the artifact bytes, not against the record's legacy "
             "evidence_quote summary." % (WORK_ORDER, PASS_NAME, artifact_sha)),
        ])
        entry["evidence_ref"] = evidence_ref_for(entry)
        existing = next((e for e in hotel["evidence"]
                         if e["evidence_ref"] == entry["evidence_ref"]), None)
        if existing is not None:
            # Idempotent by design. A corrections pass that explodes on its
            # second run is a pass nobody can safely re-run after amending the
            # correction table -- and re-running is exactly how Pass A's
            # approval-nesting defect was caught. The ref derives from
            # field+quote+url, so an identical ref IS this same pointer;
            # refreshing it in place keeps the array a set rather than growing
            # a duplicate.
            existing.update(entry)
        else:
            hotel["evidence"].append(entry)
        # Recorded either way: the ledger describes the correction this record
        # carries, not whether this particular run was the one that wrote it.
        # Skipping it on a re-run emptied the ledger for the two pointer-only
        # records and left their founder rows with nothing to review.
        changes.append(OrderedDict([
            ("kind", "EVIDENCE_ADDED"), ("field", spec["field"]),
            ("before", "<absent>"), ("after", entry["evidence_ref"]),
            ("quote", spec["quote"])]))

    for field, decision in (correction.get("withheld") or {}).items():
        block = hotel.setdefault("withheld_fields", {})
        before = copy.deepcopy(block.get(field, "<absent>"))
        refs = sorted({e["evidence_ref"] for e in hotel["evidence"]})
        block[field] = OrderedDict([
            ("reason_code", decision["reason_code"]),
            ("reason", decision["reason"]),
            ("evidence_refs", refs),
        ])
        changes.append(OrderedDict([
            ("kind", "WITHHOLDING"), ("field", "withheld_fields." + field),
            ("before", before.get("reason_code") if isinstance(before, dict)
             else before),
            ("after", decision["reason_code"])]))

    return OrderedDict([("changes", changes)])


def reseal(hotel: Dict) -> Dict:
    """Recompute the hashes and keep the FOUNDER's approval as the preserved one.

    Pass A already left a machine block in place whose ``supersedes`` holds the
    founder's approval. Superseding that block would bury the human one level
    deeper and put an agent's name where a reader looks for the last human
    decision, so the founder's approval is carried straight through.
    """
    prior = hotel.get("approval") or {}
    if (prior.get("decision") == enums.MACHINE_REVIEWED_PENDING_OPERATOR
            and prior.get("operator") in (AGENT_IDENTITY, PASS_A_IDENTITY)):
        prior = prior.get("supersedes") or {}
    signed = {k: v for k, v in hotel.items() if k != "approval"}
    new_record = record_hash(signed)
    new_evidence = evidence_hash(hotel.get("evidence", []))
    hotel["approval"] = OrderedDict([
        ("decision", enums.MACHINE_REVIEWED_PENDING_OPERATOR),
        ("operator", AGENT_IDENTITY),
        ("approval_date", PASS_DATE),
        ("supersedes", copy.deepcopy(dict(prior))),
        ("caveats", [
            "%s %s. This record carries a deterministic policy correction "
            "prepared for founder review and NOT yet approved. Facts and/or "
            "evidence changed, so record_hash and evidence_hash both moved. "
            "The approval under 'supersedes' is the founder's and was given "
            "for the record before Pass A's artifact bindings and before this "
            "correction; it is preserved verbatim and no longer binds. A "
            "founder decision against the record_hash below is required before "
            "this record may publish as approved."
            % (WORK_ORDER, PASS_NAME),
        ]),
        ("record_hash", new_record),
        ("evidence_hash", new_evidence),
    ])
    return hotel["approval"]


# --------------------------------------------------------------------------- #
# Run.
# --------------------------------------------------------------------------- #

def run(data_root: Path, apply: bool) -> Dict:
    facts = load_json(FACTS_PATH)
    captures = index_captures(data_root)
    by_key = {hotel["identity_key"]: hotel for hotel in facts["hotels"]}

    missing = [key for key in CORRECTIONS if key not in by_key]
    if missing:
        raise AssertionError("corrections name records not in the package: %s"
                             % missing)

    before_state = {hotel["identity_key"]: copy.deepcopy(hotel)
                    for hotel in facts["hotels"]}

    decisions: List[Dict] = []
    for key, correction in CORRECTIONS.items():
        hotel = by_key[key]
        indexed = captures.get(_bare(hotel["worker_result_hash"]))
        if indexed is None:
            raise AssertionError("%s: no artifact on disk to verify a new "
                                 "quote against" % key)
        capture = indexed["capture"]
        sample = hotel["evidence"][0]
        ledger = apply_correction(
            hotel, correction, capture.get("text") or "",
            _bare(hotel["worker_result_hash"]),
            sample["captured_at"], sample["capture_method"])

        issues = policy_schema.validate_record(hotel)
        if issues:
            raise AssertionError("%s: corrected record fails the policy "
                                 "schema: %s" % (key, issues))
        issues = evidence_contract.validate(hotel)
        if issues:
            raise AssertionError("%s: corrected record fails the evidence "
                                 "contract: %s" % (key, issues))
        blockers = evidence_contract.publication_blockers(hotel)
        if blockers:
            raise AssertionError("%s: corrected record carries publication "
                                 "blockers: %s" % (key, blockers))
        alias_covered_facts(hotel)

        approval = reseal(hotel)
        decisions.append(OrderedDict([
            ("decision_id", correction["decision_id"]),
            ("group", correction["group"]),
            ("hotel", hotel["name"]),
            ("identity_key", key),
            ("approval_history", OrderedDict([
                ("founder_approval_preserved", approval["supersedes"]),
                ("live_state", approval["decision"]),
                ("live_state_operator", approval["operator"]),
                ("bound_by_a_human", False),
            ])),
            ("changes", ledger["changes"]),
            ("supporting_quotes", sorted({
                c["quote"] for c in ledger["changes"] if c.get("quote")}
                or {e["quote"] for e in hotel["evidence"]
                    if e["field"] in ("general_restrictions", "pet_fee")})),
            ("artifact_sha256", "sha256:%s" % hotel["worker_result_hash"]),
            ("evidence_grade", OrderedDict([
                ("artifact_class", enums.PUBLICATION_GRADE_EVIDENCE),
                ("source_grade", enums.GRADE_PT1_FIRST_PARTY),
                ("artifact_kind", enums.ARTIFACT_RENDERED_HTML),
                ("entries", len(hotel["evidence"])),
            ])),
            ("public_rendering_changes",
             correction["public_change"] != "None. Scope already rendered as "
             "Per room; this adds the citation behind it."),
            ("public_rendering_note", correction["public_change"]),
            ("rationale", correction["rationale"]),
            ("final_record_hash", approval["record_hash"]),
            ("final_evidence_hash", approval["evidence_hash"]),
            ("recommendation", APPROVE),
        ]))

    # Everything not corrected carries Pass A's binding and nothing else.
    artifact_only = []
    for hotel in facts["hotels"]:
        key = hotel["identity_key"]
        if key in CORRECTIONS:
            continue
        prior = before_state[key]
        if record_hash(hotel) != prior["approval"]["record_hash"]:
            raise AssertionError("%s: an uncorrected record moved" % key)
        artifact_only.append(OrderedDict([
            ("identity_key", key),
            ("hotel", hotel["name"]),
            ("final_record_hash", hotel["approval"]["record_hash"]),
            ("final_evidence_hash", hotel["approval"]["evidence_hash"]),
        ]))

    packet = OrderedDict([
        ("schema", "ptf-dayton-passB-founder-review-packet/1.0"),
        ("work_order", WORK_ORDER),
        ("pass", PASS_NAME),
        ("as_of", PASS_DATE),
        ("market_id", MARKET),
        ("prepared_by", AGENT_IDENTITY),
        ("note",
         "Nothing here is an approval. Every record below is live at "
         "MACHINE_REVIEWED_PENDING_OPERATOR attributed to the agent, with the "
         "founder's own prior approval preserved verbatim under supersedes and "
         "provably unbound. A decision binds only against the final hashes "
         "recorded on each row."),
        ("reconciliation", OrderedDict([
            ("published_records", len(facts["hotels"])),
            ("policy_decisions_required", len(decisions)),
            ("artifact_binding_only_reattestations", len(artifact_only)),
            ("total_founder_actions", len(decisions) + len(artifact_only)),
        ])),
        ("batches", OrderedDict([
            ("A_monetary", [d["decision_id"] for d in decisions
                            if d["group"].startswith(("A_", "B_"))]),
            ("B_service_animal_and_esa", [d["decision_id"] for d in decisions
                                          if d["group"].startswith("C_")]),
            ("C_pointer_repair", [d["decision_id"] for d in decisions
                                  if d["group"].startswith("D_")]),
        ])),
        ("census_hygiene_tracked_separately", OrderedDict([
            ("status", "PROPOSED_NOT_APPLIED"),
            ("is_a_policy_decision", False),
            ("summary",
             "Best Western Celina is VERIFIED_NO_PETS in both the exclusion "
             "registry and the final partition, but its census row still reads "
             "POLICY_NOT_VERIFIED and the advisory rollup still says 7. The "
             "exact proposed edit (policy_state POLICY_NOT_VERIFIED -> "
             "VERIFIED_NO_PETS, no_pets_count 7 -> 8) is recorded in "
             "dayton_artifact_verification_001.json under census_hygiene."),
            ("why_not_here",
             "contracts/census.py states policy_state is ADVISORY and that no "
             "gate may read it, and nothing that publishes depends on it -- the "
             "exclusion registry is what suppresses a route and already carries "
             "all eight. Hand-editing a census in a policy pass would also be "
             "the wrong writer. This belongs to a census-scoped work order that "
             "rebuilds the file mechanically."),
            ("founder_action_required", False),
        ])),
        ("renderer_findings", OrderedDict([
            ("why_a_policy_pass_touched_the_renderer",
             "Removing the leaked prose exposed a gap the leak had been "
             "covering, and the gap made the removal a REGRESSION. Home2 "
             "Suites Dayton Beavercreek withholds its fee ladder and publishes "
             "a $75 scalar; the reader was warned that '$75 is not the whole "
             "charge' only because the withheld ladder had ALSO leaked into "
             "its restriction text. Cleaning up the leak took the warning with "
             "it. So the warning was moved onto the withholding decision, "
             "where it belongs, and three further records that never had a "
             "leak to rely on gained the warning they should always have "
             "carried."),
            ("REND-02", OrderedDict([
                ("status", "FIXED"),
                ("was",
                 "canonical_view.has_undeclared_second_amount inferred a "
                 "partial scalar from PROSE naming a larger amount, and "
                 "hotel_profile.second_amount_note built its view from "
                 "{'facts': f} with no withholding context -- so a record that "
                 "had decided it could not publish its ladder looked, from "
                 "inside the notice, like a record with no ladder at all."),
                ("now",
                 "a withheld fee_tiers/fee_schedule marks the scalar partial, "
                 "and the notice is built with the record's withholding "
                 "decisions attached."),
                ("public_effect",
                 "4 records GAIN the 'not the whole charge' caveat; 0 records "
                 "lose anything; Columbus unaffected."),
                ("records", [
                    "cleveland-akron-canton-oh / home2 suites by hilton cleveland beachwood ($50)",
                    "dayton-oh / hilton garden inn dayton beavercreek ($75)",
                    "dayton-oh / home2 suites by hilton dayton beavercreek ($75, retained)",
                    "dayton-oh / homewood suites by hilton south dayton miamisburg ($75)",
                ]),
                ("no_market_authority_changed",
                 "Only dayton-oh's policy package changed on disk. The "
                 "Cleveland record renders more honestly because the shared "
                 "renderer was corrected; its record_hash and evidence_hash "
                 "are untouched."),
            ])),
            ("REND-01", OrderedDict([
                ("status", "REPORTED_NOT_FIXED"),
                ("finding",
                 "pet_fee.tax_relationship is never rendered. "
                 "canonical_view.states_tax_on_fee tests the restriction PROSE "
                 "for the word 'tax' and never reads the canonical field, "
                 "whose existence its own docstring calls hypothetical. Drury "
                 "Inn & Suites Dayton North carries tax_relationship plus_tax "
                 "and its profile reads '$50 fee applies per room per night' "
                 "with no mention of tax."),
                ("why_not_fixed_here",
                 "Unlike REND-02 this is not a regression Pass B would cause: "
                 "the field has never rendered, on any market, and correcting "
                 "it means writing new fee prose rather than routing an "
                 "existing sentence. That is renderer work with its own "
                 "before/after, not a policy correction. Courtyard Springfield "
                 "Downtown's tax term is recorded canonically here so the fix "
                 "has somewhere to land."),
                ("records_carrying_the_field", [
                    "columbus-oh / towneplace suites columbus airport gahanna",
                    "cleveland-akron-canton-oh / drury inn and suites beachwood",
                    "cleveland-akron-canton-oh / drury plaza hotel",
                    "dayton-oh / drury inn and suites dayton north",
                    "dayton-oh / courtyard by marriott springfield downtown",
                ]),
                ("pre_existing", True),
            ])),
        ])),
        ("policy_decisions", decisions),
        ("artifact_binding_only_reattestation", OrderedDict([
            ("cohort_size", len(artifact_only)),
            ("what_changed",
             "Publication-grade artifact metadata only: artifact_sha256, "
             "artifact_kind, captured_at, capture_method and source_grade were "
             "added to each evidence entry by Pass A. No fact, quote, source "
             "URL or withholding decision changed on any record in this "
             "cohort, and evidence_hash is identical to the value the founder's "
             "own approval recorded. record_hash moved solely because the "
             "record now carries the bindings."),
            ("decide_as", "one block, not %d policy decisions" % len(artifact_only)),
            ("records", artifact_only),
        ])),
    ])

    if apply:
        payload = (json.dumps(facts, indent=2, ensure_ascii=False) + "\n") \
            .encode("utf-8")
        FACTS_PATH.write_bytes(payload)
        new_sha = hashlib.sha256(payload).hexdigest()
        contract = load_json(CONTRACT_PATH)
        packet["facts_sha256_before"] = \
            contract["policy_package"]["expected_sha256"]
        contract["policy_package"]["expected_sha256"] = new_sha
        CONTRACT_PATH.write_bytes(
            (json.dumps(contract, indent=2, ensure_ascii=False) + "\n")
            .encode("utf-8"))
        packet["facts_sha256_after"] = new_sha
        PACKET_PATH.write_bytes(
            (json.dumps(packet, indent=2, ensure_ascii=False) + "\n")
            .encode("utf-8"))
    return packet


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=_REPO_ROOT / "data")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    packet = run(args.data_root, args.apply)
    rec = packet["reconciliation"]
    print("policy decisions required      : %d" % rec["policy_decisions_required"])
    print("artifact-binding-only cohort   : %d"
          % rec["artifact_binding_only_reattestations"])
    print("total founder actions          : %d" % rec["total_founder_actions"])
    for decision in packet["policy_decisions"]:
        print("  %-8s %-46s %d change(s)"
              % (decision["decision_id"], decision["hotel"][:46],
                 len(decision["changes"])))
    if not args.apply:
        print("dry run: nothing written (pass --apply to commit)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
