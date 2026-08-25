"""PTF-MILWAUKEE-SERVICE-ANIMAL-CORRECTION-011 -- unsay a false statement.

WHAT WAS WRONG
--------------
Four LIVE Milwaukee profiles published

    "The property states that service animals are welcome and that a charge
     applies."

from sources that said the opposite:

    avid hotels Oak Creek  "We charge 50.00 per pet, per night, except ADA
                            Service Animals."
    ESA Waukesha           "Service animals will be exempt from this charge."
    ESA Wauwatosa          "Service animals will be exempt from this charge."
    The Pfister Hotel      "Service animals are allowed, with no pet fee
                            required for service animals."

``authority_build_036.service_animal_statement`` classified the charge state
with a two-branch fallback whose second branch asked only whether the WORD
"fee" or "charge" occurred anywhere in the sentence. An exemption has to name
the thing it exempts you from, so every one of these sentences tripped it.
The rule now lives in ``contracts.service_animal``: exemption and negation are
tested first and win, and a charge is concluded only when the source binds one
to the animal itself.

WHAT THIS WORK ORDER DOES
-------------------------
Re-derives ``service_animal_statement.charges_stated`` for every record in
every committed market package from THAT RECORD'S OWN QUOTE, through the
corrected shared contract -- the same function ``authority_build_036`` now
calls. It re-derives nothing else. A fee, a weight limit, a species, a count,
a refusal, an approval decision, a participation flag: all are read, hashed
and asserted unchanged, per record, before anything is written.

WHY THE RECORD IS RE-DERIVED AND NOT HAND-PATCHED
--------------------------------------------------
Patching four profiles would leave the defect in the code that produced them
and in every market built after today. The correction is applied by running
the fixed generic rule over the committed authority, so a record only moves
if the rule says the source means something different from what was
published, and the same rule now governs every future build.

A RECORD WITH NO QUOTE IS NOT TOUCHED
--------------------------------------
Forty-nine live records carry a ``service_animal_statement`` whose ``quote``
is empty: they were set by an explicit founder decision in a market's own
pass, not read off a sentence. There is nothing for a text rule to interpret,
and overwriting a founder's decision with a classification of the empty
string would be the same class of error this work order exists to fix. They
are counted, reported, and left exactly as they are.

GOV-01 APPLIES, AND IS FLAGGED RATHER THAN ASSUMED AWAY
--------------------------------------------------------
Founder ruling GOV-01 (``contracts/evidence.py``) holds that a repair
requires founder re-attestation when it changes a record's final
``record_hash``. This one does, for the corrected records. The founder's
decision fields -- operator, decision, decision_source, and the
``reviewed_*`` hashes that bind the decision to the store row the founder
actually read -- are NEVER rewritten here; only the derived ``record_hash``
is recomputed, because a stored hash that no longer describes its record is a
silent integrity break. Every corrected record carries a conversion note
naming this work order, the value that was published, the value now derived,
and the hash that was superseded. Deployment stops until the founder
authorizes it.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder import release_contracts as RC              # noqa: E402
from scripts.pettripfinder import site_data as SD                      # noqa: E402
from scripts.pettripfinder.contracts import policy_schema as SCHEMA    # noqa: E402
from scripts.pettripfinder.contracts import service_animal as SA       # noqa: E402
from scripts.pettripfinder.markets import load_markets                 # noqa: E402
from scripts.pettripfinder.policy_migration import record_hash         # noqa: E402

WORK_ORDER = "PTF-MILWAUKEE-SERVICE-ANIMAL-CORRECTION-011"

PKG_DIR = REPO / "launch_packages" / "pettripfinder"
REPORT = PKG_DIR / "service_animal_correction_011" / \
    "service-animal-correction-011.json"

#: The only two keys this work order is permitted to write. Named, so the
#: unchanged-assertion below can be exhaustive rather than approximate.
CORRECTED_RECORD_FIELD = "service_animal_statement"
CORRECTED_STATEMENT_KEY = "charges_stated"

#: Every document this work order writes is pinned to eol=lf by
#: ``.gitattributes`` AND hashed by a release contract, so the newline is
#: spelled explicitly rather than left to the platform. Written as a constant
#: for the same reason ``global_deployment`` does it: a CRLF write moves every
#: package sha256 without moving a single fact.
LF = chr(10)


class CorrectionError(RuntimeError):
    """The correction cannot be applied safely, and no guess replaces it."""


# --------------------------------------------------------------------------- #
# Reading.
# --------------------------------------------------------------------------- #

def market_ids() -> Tuple[str, ...]:
    """Every registered market, whether or not it is published."""
    return tuple(sorted(m.market_id for m in load_markets()))


def package_path(market_id: str) -> Path:
    return SD.published_facts_path(market_id)


def load_package(market_id: str) -> Dict:
    path = package_path(market_id)
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _statement(record: Mapping) -> Optional[Mapping]:
    statement = record.get(CORRECTED_RECORD_FIELD)
    return statement if isinstance(statement, Mapping) else None


# --------------------------------------------------------------------------- #
# The finding, per record.
# --------------------------------------------------------------------------- #

#: A record whose statement carries a quote the corrected rule reads
#: differently from what is published.
CORRECTED = "CORRECTED"
#: The corrected rule agrees with what is published.
AGREES = "AGREES"
#: A statement with no quote: a founder decision, not a reading. Left alone.
NO_QUOTE = "NO_QUOTE_NOT_TOUCHED"
#: The record makes no service-animal statement at all.
NO_STATEMENT = "NO_STATEMENT"


def finding(market_id: str, record: Mapping) -> Dict:
    """One record's before/after, with the rule that produced the after."""
    statement = _statement(record)
    if statement is None:
        return OrderedDict([("market_id", market_id),
                            ("identity_key", record.get("identity_key")),
                            ("name", record.get("name")),
                            ("verdict", NO_STATEMENT)])

    quote = str(statement.get("quote") or "").strip()
    published = str(statement.get(CORRECTED_STATEMENT_KEY) or "")
    row = OrderedDict([
        ("market_id", market_id),
        ("identity_key", record.get("identity_key")),
        ("name", record.get("name")),
        ("source_url", record.get("source_url")),
        ("quote", quote),
        ("published_charges_stated", published),
    ])
    if not quote:
        row["verdict"] = NO_QUOTE
        row["why"] = ("the statement carries no quote: it was set by an "
                      "explicit founder decision, and a text rule has nothing "
                      "to interpret")
        return row

    reading = SA.classify(quote)
    row["interpretation"] = reading.interpretation
    row["interpretation_reason"] = reading.reason
    row["derived_charges_stated"] = reading.charges_stated
    row["verdict"] = AGREES if reading.charges_stated == published else CORRECTED
    if row["verdict"] == CORRECTED:
        row["rendered_before"] = rendered_copy(record, published)
        row["rendered_after"] = rendered_copy(record, reading.charges_stated)
    return row


def rendered_copy(record: Mapping, charges: str) -> str:
    """The sentence ``hotel_profile.service_animal_rows`` publishes.

    Rendered from THIS record with only the charge state substituted, and
    through the renderer itself rather than a restatement of its copy, so a
    before/after in this report cannot drift from the page a reader sees.
    """
    from scripts.pettripfinder import hotel_profile as HP
    probe = dict(record)
    statement = dict(probe.get(CORRECTED_RECORD_FIELD) or {})
    statement[CORRECTED_STATEMENT_KEY] = charges
    probe[CORRECTED_RECORD_FIELD] = statement
    rows = HP.service_animal_rows(probe)
    return rows[0][1] if rows else ""


def findings(markets: Optional[Sequence[str]] = None) -> List[Dict]:
    out: List[Dict] = []
    for market_id in (markets or market_ids()):
        if not package_path(market_id).is_file():
            continue
        package = load_package(market_id)
        for record in package.get("hotels") or []:
            row = finding(market_id, record)
            if row["verdict"] != NO_STATEMENT:
                out.append(row)
    return out


def corrections(markets: Optional[Sequence[str]] = None) -> List[Dict]:
    return [row for row in findings(markets) if row["verdict"] == CORRECTED]


# --------------------------------------------------------------------------- #
# Proof that the correction is the canonical pipeline's own answer.
# --------------------------------------------------------------------------- #

def milwaukee_pipeline_agreement() -> Dict:
    """Re-derive Milwaukee's statements from the STORE, through 036 itself.

    The correction above re-reads each published record's own quote. This
    asks the builder that originally produced those records to derive them
    again from the store row the founder approved, and checks the two answers
    are the same. If they were not, the correction would be a second answer
    to the question rather than the pipeline's own.
    """
    from scripts.pettripfinder.acquisition import approval_rebinding_039 as R39
    from scripts.pettripfinder.acquisition import authority_build_036 as A36

    try:
        store = R39.store_rows()
    except Exception as error:                        # pragma: no cover
        return OrderedDict([("available", False),
                            ("why", "%s: %s" % (type(error).__name__, error))])

    package = load_package("milwaukee-wi")
    checked = 0
    disagreements: List[Dict] = []
    absent: List[str] = []
    for record in package.get("hotels") or []:
        statement = _statement(record)
        if statement is None or not str(statement.get("quote") or "").strip():
            continue
        row = store.get(record["identity_key"])
        if row is None:
            absent.append(record["identity_key"])
            continue
        checked += 1
        rebuilt = A36.service_animal_statement(row) or {}
        expected = SA.charges_stated(str(statement.get("quote")))
        if rebuilt.get(CORRECTED_STATEMENT_KEY) != expected:
            disagreements.append({
                "identity_key": record["identity_key"],
                "from_store_via_036": rebuilt.get(CORRECTED_STATEMENT_KEY),
                "from_published_quote": expected})
    return OrderedDict([
        ("available", True),
        ("records_checked", checked),
        ("identities_absent_from_store", sorted(absent)),
        ("disagreements", disagreements),
        ("agrees", not disagreements),
    ])


# --------------------------------------------------------------------------- #
# Applying it.
# --------------------------------------------------------------------------- #

def _material(record: Mapping) -> str:
    """Everything in a record EXCEPT the two things this may write.

    ``approval`` is excluded because a corrected record's ``record_hash`` is
    recomputed and its ``conversion_notes`` gain a line; the founder decision
    fields inside it are asserted separately and by name.
    """
    material = {k: v for k, v in record.items()
                if k not in (CORRECTED_RECORD_FIELD, "approval")}
    return json.dumps(material, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), default=str)


#: The approval fields that record WHO decided WHAT, and what they read. None
#: of them may move. ``record_hash`` is deliberately absent: it is a checksum
#: of the record, not a statement by the founder.
FROZEN_APPROVAL_FIELDS: Tuple[str, ...] = (
    "decision", "operator", "approval_date", "decision_source",
    "evidence_hash", "reviewed_record_hash", "reviewed_evidence_hash",
    "binding_contract", "semantic_hash", "reviewed_semantic_hash",
)


def correct_record(record: Dict, derived: str) -> Dict:
    """Apply one correction in place, and prove it was the only change."""
    before_material = _material(record)
    before_approval = {k: json.dumps((record.get("approval") or {}).get(k),
                                     sort_keys=True, default=str)
                       for k in FROZEN_APPROVAL_FIELDS}
    statement = dict(record[CORRECTED_RECORD_FIELD])
    published = statement.get(CORRECTED_STATEMENT_KEY)
    before_statement = dict(statement)

    statement[CORRECTED_STATEMENT_KEY] = derived
    record[CORRECTED_RECORD_FIELD] = statement

    moved = sorted(k for k in set(before_statement) | set(statement)
                   if before_statement.get(k) != statement.get(k))
    if moved != [CORRECTED_STATEMENT_KEY]:
        raise CorrectionError(
            "%s: the statement changed in %s, and only %s may change"
            % (record.get("identity_key"), moved, CORRECTED_STATEMENT_KEY))
    if _material(record) != before_material:
        raise CorrectionError(
            "%s: something outside the service-animal statement moved"
            % record.get("identity_key"))

    approval = record.get("approval")
    if isinstance(approval, dict):
        superseded = approval.get("record_hash")
        approval["record_hash"] = record_hash(record)
        notes = list(approval.get("conversion_notes") or [])
        notes.append(
            "%s: service_animal_statement.charges_stated re-derived %r -> %r "
            "from the source's own words (%r). The published value came from a "
            "token match on the word \"fee\"/\"charge\", which an exemption "
            "sentence always contains; exemption and negation now win. No "
            "fact, evidence entry, approval decision or hash the founder read "
            "was altered. record_hash superseded %s. Founder ruling GOV-01 "
            "applies: this changes the final record_hash, so the record "
            "requires founder re-attestation before deployment."
            % (WORK_ORDER, published, derived,
               str(statement.get("quote") or ""), superseded))
        approval["conversion_notes"] = notes
        for key in FROZEN_APPROVAL_FIELDS:
            now = json.dumps(approval.get(key), sort_keys=True, default=str)
            if now != before_approval[key]:
                raise CorrectionError(
                    "%s: approval.%s moved; a founder decision is never "
                    "rewritten here" % (record.get("identity_key"), key))
    return record


def apply_market(market_id: str, apply: bool = False) -> Dict:
    """Correct one market's package. Returns what moved, whether or not written."""
    package = load_package(market_id)
    envelope_before = json.dumps(
        {k: v for k, v in package.items() if k != "hotels"},
        sort_keys=True, ensure_ascii=False, default=str)
    rows = [finding(market_id, r) for r in package.get("hotels") or []]
    wanted = {r["identity_key"]: r for r in rows if r["verdict"] == CORRECTED}
    path = package_path(market_id)
    before_bytes = path.read_bytes()

    result = OrderedDict([
        ("market_id", market_id),
        ("path", path.relative_to(REPO).as_posix()),
        ("records", len(package.get("hotels") or [])),
        ("statements", len([r for r in rows if r["verdict"] != NO_STATEMENT])),
        ("corrected", len(wanted)),
        ("agrees", len([r for r in rows if r["verdict"] == AGREES])),
        ("untouched_no_quote", len([r for r in rows if r["verdict"] == NO_QUOTE])),
        ("sha256_before", _package_sha256(before_bytes)),
    ])
    if not wanted:
        result["sha256_after"] = result["sha256_before"]
        result["written"] = False
        return result

    for record in package["hotels"]:
        row = wanted.get(record.get("identity_key"))
        if row:
            correct_record(record, row["derived_charges_stated"])
            issues = SCHEMA.validate_record(record)
            if issues:
                raise CorrectionError(
                    "%s no longer validates under schema %s: %s"
                    % (record["identity_key"], record.get("schema_version"),
                       "; ".join(str(i) for i in issues)))

    envelope_after = json.dumps(
        {k: v for k, v in package.items() if k != "hotels"},
        sort_keys=True, ensure_ascii=False, default=str)
    # Everything a package says ABOUT ITSELF rather than about a hotel.
    # ``published`` is the flag that admits a market to live inventory and
    # ``publication`` names the work order that flipped it: a correction that
    # moved either would publish or unpublish a market as a side effect.
    if envelope_after != envelope_before:
        raise CorrectionError(
            "%s: the package envelope moved -- published, publication, "
            "provenance, refused_records and schema_version are frozen here"
            % market_id)
    if len(package["hotels"]) != result["records"]:
        raise CorrectionError("%s: the record count moved" % market_id)

    text = json.dumps(package, indent=1, ensure_ascii=False) + LF
    result["sha256_after"] = _package_sha256(text.encode("utf-8"))
    result["corrections"] = [wanted[k] for k in sorted(wanted)]
    if apply:
        # An explicit LF newline, so the committed bytes do not depend on the
        # platform that wrote them: .gitattributes pins these documents to
        # eol=lf, and the release contract pins a sha256 OVER THOSE BYTES. A
        # CRLF write moves every package hash without moving a single fact.
        path.write_text(text, encoding="utf-8", newline=LF)
    result["written"] = bool(apply)
    return result


def _package_sha256(payload: bytes) -> str:
    """The hash the release contract pins, computed by the assembler's own rule."""
    from scripts.pettripfinder.assemble_netlify_bundle import content_sha256
    return content_sha256(payload)


# --------------------------------------------------------------------------- #
# The release contract pins the package hash, so it moves with it.
# --------------------------------------------------------------------------- #

def restamp_contract(market_id: str, apply: bool = False) -> Dict:
    """Re-pin ``policy_package.expected_sha256`` for a corrected market."""
    path = RC.contract_path(market_id) if hasattr(RC, "contract_path") \
        else RC.RELEASE_CONTRACTS_DIR / ("%s.json" % market_id)
    if not path.is_file():
        return OrderedDict([("market_id", market_id), ("contract", None),
                            ("why", "this market registers no release contract")])
    contract = json.loads(path.read_text(encoding="utf-8-sig"))
    stated = (contract.get("policy_package") or {}).get("expected_sha256")
    derived = RC.derive_authority(market_id).policy_package_sha256
    result = OrderedDict([
        ("market_id", market_id),
        ("contract", path.relative_to(REPO).as_posix()),
        ("expected_sha256_before", stated),
        ("expected_sha256_after", derived),
        ("moved", stated != derived),
    ])
    if stated != derived and apply:
        contract["policy_package"]["expected_sha256"] = derived
        path.write_text(json.dumps(contract, indent=1, ensure_ascii=False) + LF,
                        encoding="utf-8", newline=LF)
        result["written"] = True
    else:
        result["written"] = False
    return result


# --------------------------------------------------------------------------- #
# Reporting.
# --------------------------------------------------------------------------- #

def report(apply: bool = False) -> Dict:
    before = findings()
    markets = sorted({row["market_id"] for row in before
                      if row["verdict"] == CORRECTED})
    applied = [apply_market(mid, apply=apply) for mid in market_ids()
               if package_path(mid).is_file()]
    contracts = [restamp_contract(mid, apply=apply) for mid in markets]
    after = findings() if apply else []
    return OrderedDict([
        ("schema", "ptf-service-animal-correction/1.0"),
        ("work_order", WORK_ORDER),
        ("applied", apply),
        ("markets_corrected", markets),
        ("totals", OrderedDict([
            ("statements", len(before)),
            ("corrected", len([r for r in before if r["verdict"] == CORRECTED])),
            ("agrees", len([r for r in before if r["verdict"] == AGREES])),
            ("untouched_no_quote",
             len([r for r in before if r["verdict"] == NO_QUOTE])),
        ])),
        ("corrections", [r for r in before if r["verdict"] == CORRECTED]),
        ("per_market", applied),
        ("release_contracts", contracts),
        ("milwaukee_pipeline_agreement", milwaukee_pipeline_agreement()),
        ("residual_corrections_after_apply",
         [r for r in after if r["verdict"] == CORRECTED]),
    ])


def write_report(doc: Mapping) -> Path:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + LF,
                      encoding="utf-8", newline=LF)
    return REPORT


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=WORK_ORDER)
    parser.add_argument("--apply", action="store_true",
                        help="write the corrected packages and re-pin the "
                             "release contracts they moved")
    parser.add_argument("--report", action="store_true",
                        help="write the run report")
    args = parser.parse_args(argv)

    doc = report(apply=args.apply)
    if args.report:
        write_report(doc)
    print(json.dumps({k: v for k, v in doc.items()
                      if k not in ("corrections",)}, indent=2,
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":                            # pragma: no cover
    raise SystemExit(main())
