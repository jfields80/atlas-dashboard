"""Project a market's signed authority into a schema-1.2 policy package.

    python scripts/pettripfinder/market_policy_package_cli.py \
      --authority <proposed_authority.json> \
      --out launch_packages/pettripfinder/hotel_policy_facts_<market_id>.json

WHY THIS EXISTS
---------------
``site_data.verified_public_hotels`` reads a committed policy package and treats
it as THE authority: a seed row absent from it is not published, and a package
record with no seed row FAILS CLOSED. Every release contract points at one by
path, sha256, schema version and record count. Five markets have one; a market
built on the generic path had no way to produce it.

THE PROJECTION IS PROVED, NOT TRUSTED
--------------------------------------
Reshaping facts is where a wrong number gets published. So every record this
module builds is run through ``contracts.policy_schema.validate_facts`` -- the
repository's own 1.2 validator -- and the run REFUSES TO WRITE if any record
raises a single issue. A projection that cannot pass the schema it claims to
target is not a projection, it is a guess.

WHAT THE RESHAPING MAY AND MAY NOT DO
--------------------------------------
It may only re-express what the reader already extracted. Three rules, each one
a thing this corpus learned the expensive way:

* ``species_allowed`` is an AFFIRMATIVE-MENTION LIST, not an allow-list
  (PTF-POLICY-PARSER-SEMANTIC-HARDENING-017 retracted the opposite reading).
  ``["dog"]`` becomes ``{"dogs": "accepted"}`` and says NOTHING about cats. An
  absent species stays absent, because every consumer renders that as "Not
  stated"; writing ``{"cats": "prohibited"}`` there would invent a refusal.
* ``weight_limit`` keeps whatever the source stated and nothing else. The
  operator and the scope are emitted ONLY when the reader emitted them --
  defaulting "up to" to ``lte`` is a guest-visible error in both directions, and
  the reader's own non_inferences say so.
* A withheld field is not carried across as a value. It stays withheld, and the
  package's record simply lacks it, which is what renders as "Not stated".

Nothing here publishes. The package carries ``published: false``; flipping that
is a separate act by a publication work order, exactly as PTF-MILWAUKEE-
PUBLICATION-042 did for its market.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.contracts import enums  # noqa: E402
from scripts.pettripfinder.contracts import policy_schema as PS  # noqa: E402
from scripts.pettripfinder.site_data import normalize_name  # noqa: E402

SCHEMA_VERSION = enums.POLICY_SCHEMA_VERSION

#: reader species token -> package species key. Only these two are recognised;
#: an unknown token is reported rather than guessed at.
_SPECIES_KEY = {"dog": "dogs", "cat": "cats"}


class PolicyPackageError(RuntimeError):
    pass



#: Wording that unambiguously states an UPPER bound on one animal's weight.
_MAXIMAL_RE = re.compile(
    r"\b(max(?:imum)?\.?|up\s+to|under|less\s+than|no\s+more\s+than|"
    r"or\s+less|not\s+exceed|weight\s+limit|limit\s+of)\b", re.IGNORECASE)

#: Wording that describes a weight shared ACROSS pets. Founder condition 3 and 4:
#: a combined or per-room total is a different fact and is never normalised to
#: per_pet.
_COMBINED_RE = re.compile(
    r"\b(combined|total|together|aggregate|both\s+pets|all\s+pets)\b",
    re.IGNORECASE)

_REFUNDABLE_RE = re.compile(r"\brefundable\b", re.IGNORECASE)
_NON_REFUNDABLE_RE = re.compile(r"\bnon[-\s]?refundable\b", re.IGNORECASE)


def weight_normalisation_eligible(source: Mapping,
                                  quotes: Sequence[str]) -> Tuple[bool, str]:
    """Founder decision 1's five conditions, each tested against the evidence.

    The rule is a PUBLICATION rule, not a reader change: it says that a
    property-specific source stating an unqualified blanket maximum may be
    published as ``lte`` / ``per_pet``. It is deliberately narrow, and anything
    it cannot verify it declines.
    """
    if not quotes:
        return (False, "no quote cites the weight limit, so nothing can be read")
    joined = " || ".join(quotes)
    if _COMBINED_RE.search(joined):
        return (False, "the source describes a combined or shared weight: %r"
                       % joined[:120])
    if source.get("combined_weight_limit") is not None:
        return (False, "the record carries a separate combined_weight_limit")
    if (source.get("weight_limit") or {}).get("scope"):
        return (False, "a scope is already stated and is not overridden")
    if not _MAXIMAL_RE.search(joined):
        return (False, "the wording does not clearly state a maximum: %r"
                       % joined[:120])
    return (True, "")


def deposit_refundability(quotes: Sequence[str]) -> Optional[bool]:
    """``True`` / ``False`` / ``None`` -- and ``None`` means UNSTATED.

    Never inferred from the word "deposit". A source that says only
    "deposit of 50.00 USD" has not said whether it comes back.
    """
    joined = " ".join(quotes)
    if _NON_REFUNDABLE_RE.search(joined):
        return False
    if _REFUNDABLE_RE.search(joined):
        return True
    return None


def project_facts(source: Mapping, evidence: Sequence[Mapping] = (), *,
                  normalize_weight: bool = False,
                  cap_qualifier_stated: Optional[bool] = None
                  ) -> Tuple[Dict, List[str]]:
    """``(facts, notes)`` -- the publication fact block for one authority row.

    ``normalize_weight`` and ``cap_qualifier_stated`` are OFF by default. Each
    switches on one founder publication decision, so the projector's default
    behaviour remains the strict one and a caller has to say which ruling it is
    applying.
    """
    facts: Dict = OrderedDict()
    notes: List[str] = []

    def quotes_for(field: str) -> List[str]:
        return [str(e.get("quote", "")) for e in evidence
                if field in (e.get("field_refs") or ())]

    quotes = quotes_for("weight_limit")

    if "pets_allowed" in source:
        facts["pets_allowed"] = bool(source["pets_allowed"])

    species: Dict[str, str] = OrderedDict()
    for token in source.get("species_allowed") or ():
        key = _SPECIES_KEY.get(str(token).lower())
        if key is None:
            notes.append("unrecognised species token %r; not projected" % token)
            continue
        species[key] = enums.SPECIES_ACCEPTED
    # An explicit refusal is a fact and is carried; an ABSENT species is not.
    if source.get("cats_allowed") is False:
        species["cats"] = enums.SPECIES_PROHIBITED
    if species:
        facts["species"] = OrderedDict(sorted(species.items()))

    weight = source.get("weight_limit")
    if isinstance(weight, Mapping) and weight.get("value") is not None:
        node = OrderedDict((("value", weight["value"]),
                            ("unit", weight.get("unit", "lb"))))
        for optional in ("operator", "scope"):
            if weight.get(optional):
                node[optional] = weight[optional]
        if ("operator" not in node or "scope" not in node) and normalize_weight:
            eligible, why = weight_normalisation_eligible(source, quotes)
            if eligible:
                node.setdefault("operator", "lte")
                node.setdefault("scope", enums.WEIGHT_SCOPE_PER_PET)
                notes.append(
                    "weight_limit.operator=lte and scope=per_pet were "
                    "FOUNDER-NORMALISED for publication under PTF-ST-LOUIS-"
                    "PUBLICATION-SCHEMA-DECISIONS-010; the source states an "
                    "unqualified blanket maximum and the reader records a "
                    "value only. Source text preserved: %s" % (" || ".join(quotes) or "(no weight quote)"))
            else:
                notes.append("weight_limit NOT normalised: %s" % why)
        facts["weight_limit"] = node

    if source.get("fee_tiers"):
        facts["fee_tiers"] = [dict(t) for t in source["fee_tiers"]]
    elif source.get("pet_fee") is not None:
        fee = OrderedDict((("amount_cents", source["pet_fee"]),
                           ("currency", source.get("fee_currency", "USD"))))
        for key, target in (("fee_basis", "basis"), ("fee_scope", "scope")):
            if source.get(key):
                fee[target] = source[key]
        facts["pet_fee"] = fee

    if source.get("fee_cap") is not None:
        cap = source["fee_cap"]
        if isinstance(cap, Mapping):
            # The reader spells the amount ``amount_minor``; schema 1.2 spells
            # it ``amount_cents``. Same integer, same unit -- a rename, not a
            # conversion. ``qualifier_stated`` is REQUIRED by the schema and is
            # deliberately NOT filled in here: it is a claim about whether the
            # source named a pet count or an ordinal, and _check_cap exists
            # because a cap whose quote named one and whose structure lost it
            # published a ceiling the hotel never quoted.
            node = OrderedDict()
            if cap.get("amount_minor") is not None:
                node["amount_cents"] = cap["amount_minor"]
            elif cap.get("amount_cents") is not None:
                node["amount_cents"] = cap["amount_cents"]
            node["currency"] = cap.get("currency", "USD")
            for optional in ("basis", "scope"):
                if cap.get(optional):
                    node[optional] = cap[optional]
            if cap.get("qualifier_stated") is not None:
                node["qualifier_stated"] = bool(cap["qualifier_stated"])
            elif cap_qualifier_stated is not None:
                # FOUNDER DECISION 3. false means "the source states the cap and
                # does NOT state an additional qualifier". It does NOT mean "no
                # qualifier exists" -- the distinction is the whole point of the
                # field, and inventing a qualifier is the failure _check_cap was
                # written against.
                node["qualifier_stated"] = bool(cap_qualifier_stated)
                notes.append(
                    "fee_cap.qualifier_stated=%s recorded under founder "
                    "decision 3: the source states the cap and states no "
                    "further qualifier. This asserts what the SOURCE said, "
                    "never that no qualifier exists."
                    % bool(cap_qualifier_stated))
            facts["fee_cap"] = node
        else:
            facts["fee_cap"] = OrderedDict(
                (("amount_cents", cap),
                 ("currency", source.get("fee_currency", "USD"))))
    if source.get("pet_deposit") is not None:
        # FOUNDER DECISION 4. A deposit is a DISTINCT charge and is never merged
        # into the pet fee -- a hotel may levy both, and this corpus contains
        # hotels that do. Refundability is read from the deposit's own quote and
        # is never inferred from the word "deposit": PTF saw a heading reading
        # "Deposit Yes" over a body reading "Non-refundable Fee", and only the
        # body was true.
        refundable = deposit_refundability(quotes_for("pet_deposit"))
        charge = OrderedDict((
            ("kind", ("refundable_deposit"
                      if refundable is True
                      else "incidental_deposit")),
            ("description", "pet deposit"),
            ("amount_cents", source["pet_deposit"]),
            ("currency", source.get("fee_currency", "USD")),
        ))
        if source.get("deposit_basis"):
            charge["basis"] = source["deposit_basis"]
        if refundable is None:
            charge["refundable_stated"] = False
            notes.append(
                "pet_deposit projected to other_charges with "
                "refundable_stated=false: the source states the deposit and "
                "does not state whether it is refundable. Schema 1.3 carries "
                "that as an explicit non-statement rather than forcing a "
                "writer to invent one.")
        else:
            charge["refundable"] = refundable
            charge["refundable_stated"] = True
        facts.setdefault("other_charges", []).append(charge)

    if source.get("pet_count_limit") is not None:
        facts["pet_count_limit"] = source["pet_count_limit"]
    if source.get("pet_count_scope"):
        facts["pet_count_scope"] = source["pet_count_scope"]
    return (facts, notes)


#: Charge language read from the service-animal sentence ITSELF.
#:
#: Founder Decision 2 forbids inferring service-animal terms from pet-policy
#: terms; it does not forbid reading the statement the property actually wrote.
#: Only these two outcomes are ever produced -- a stated absence of charge, or
#: "the statement does not address charges". ``charge_stated`` is deliberately
#: unreachable here: asserting that a property charges for a service animal is a
#: claim no projection should make from prose.
_NO_CHARGE_PHRASES = (
    "without charge", "free of charge", "no additional charge",
    "no charge", "exempt from this charge", "at no charge",
)


def project_service_animal_statement(source: Mapping) -> Optional[Dict]:
    """FOUNDER DECISION 2 -- the statement, in the namespace it belongs to.

    010's first draft put this prose in ``facts.service_animal_exception``,
    which ``policy_schema.validate_record`` has always rejected: a legal access
    category must not sit in the commercial-terms namespace, because a weight
    limit beside it invites something to apply one to the other. That is the
    founder's own constraint, already enforced by the contract. The statement
    goes on the record envelope instead, carrying the property's exact words.
    """
    quote = (source.get("service_animal_exception") or "").strip()
    if not quote:
        return None
    lowered = quote.lower()
    charges = (enums.SERVICE_ANIMAL_NO_CHARGE
               if any(phrase in lowered for phrase in _NO_CHARGE_PHRASES)
               else enums.SERVICE_ANIMAL_NOT_ADDRESSED)
    return OrderedDict((
        ("stated", True),
        ("charges_stated", charges),
        ("quote", quote),
    ))


# --------------------------------------------------------------------------- #
# The observation store: evidence references and withholding prose.
#
# The signed authority carries a withholding decision as a BARE REASON CODE and
# its evidence items carry no reference. Neither is enough for the contract the
# live markets satisfy: contracts.withholding requires a reason SENTENCE and at
# least one evidence_ref, and site_data / the profile renderer read
# ``withheld_fields`` as a MAP OF DECISIONS, not of strings. Both of the missing
# halves already exist, verbatim, in the committed observation store -- reading
# it re-derives nothing.
# --------------------------------------------------------------------------- #

def observation_index(store: Optional[Mapping]) -> Dict[str, Dict]:
    return {r["identity_key"]: r for r in (store or {}).get("records") or ()}


def evidence_reference(observation: Mapping, field: str, quote: str) -> str:
    """The store's own evidence_ref for one (field, quote), or ``""``."""
    for entry in (observation.get("publication_grade") or {}).get(
            "evidence_entries") or ():
        if entry.get("field") == field and entry.get("quote") == quote:
            return str(entry.get("evidence_ref") or "")
    return ""


def withholding_reason(observation: Mapping) -> str:
    """The reader's own sentence for why a field was not published.

    Composed from the observation's flags, which is where the reader recorded
    it. Nothing is written here: an observation with no flag yields no sentence,
    and a withholding decision with no sentence is refused rather than published
    with prose this layer made up.
    """
    details = [str(f.get("detail") or "").strip()
               for f in observation.get("flags") or ()]
    return "; ".join(d for d in details if d)


def project_withheld(source: Mapping, observation: Optional[Mapping],
                     evidence_refs: Sequence[str]) -> Tuple[Dict, List[str], List[str]]:
    """``(withheld_fields, notes, problems)`` in the shape every reader expects.

    Two rules, both the withholding contract's own:

    * ``SOURCE_SILENT`` is DROPPED. ``withheld_fields`` means "we know something
      and are choosing not to publish it"; silence is the ABSENCE of the field,
      and an entry claiming a decision was made about a non-event would make the
      map a mixture of editorial decisions and nothing. The contract's validator
      rejects it by name.
    * Every surviving decision becomes ``{reason_code, reason, evidence_refs}``.
      A bare string is not a decision a reviewer can re-adjudicate, and the
      profile renderer reads the entry as a mapping -- a string crashes it.
    """
    out: Dict = OrderedDict()
    notes: List[str] = []
    problems: List[str] = []
    reason = withholding_reason((observation or {}).get("observation") or {})
    for field in sorted(source or {}):
        value = (source or {})[field]
        code = value if isinstance(value, str) else str(
            (value or {}).get("reason_code") or "")
        if code == enums.SOURCE_SILENT:
            notes.append(
                "%s: SOURCE_SILENT dropped from withheld_fields -- silence is "
                "the absence of a field, not a decision not to publish one"
                % field)
            continue
        if isinstance(value, Mapping):
            out[field] = OrderedDict(value)
            continue
        if not reason:
            problems.append(
                "%s is withheld as %s and no observation states why; a "
                "withholding decision without its sentence is unreviewable"
                % (field, code))
            continue
        if not evidence_refs:
            problems.append(
                "%s is withheld as %s and the record carries no evidence "
                "reference to re-adjudicate it against" % (field, code))
            continue
        out[field] = OrderedDict((
            ("reason_code", code),
            ("reason", reason),
            ("evidence_refs", list(evidence_refs)),
        ))
    return out, notes, problems


def corrected_names(overlay: Optional[Mapping]) -> Dict[str, str]:
    """``identity_key -> the name the property's own captured page states``.

    The census records what DISCOVERY observed; where that is a bare chain word
    the evidence-cited overlay under ``markets/name_corrections/`` supplies the
    name the property states for itself. The overlay is normally applied when
    the observation store is built, so for an already-signed authority it is
    IDEMPOTENT -- every row it names already carries the corrected name. It is
    re-applied here because an authority signed before a correction was
    authorised would otherwise publish the bare word, and a bare chain word is
    not an identity: two markets can hold one, and then no directory can list
    both.
    """
    return {r["identity_key"]: r["corrected_canonical_name"]
            for r in (overlay or {}).get("records") or ()}


def build(authority: Mapping, *, market_name: str,
          normalize_weight: bool = False,
          cap_qualifier_stated: Optional[bool] = None,
          name_corrections: Optional[Mapping] = None,
          observations: Optional[Mapping] = None) -> Dict:
    market_id = authority.get("market_id", "")
    names = corrected_names(name_corrections)
    observed = observation_index(observations)
    hotels: List[Dict] = []
    refusals: List[Dict] = []

    for row in authority.get("pet_friendly") or ():
        observation = observed.get(row["normalized_name"]) or {}
        facts, notes = project_facts(
            row.get("facts") or {}, row.get("evidence") or (),
            normalize_weight=normalize_weight,
            cap_qualifier_stated=cap_qualifier_stated)
        issues = PS.validate_facts(facts)
        if issues:
            refusals.append(OrderedDict((
                ("identity_key", row["normalized_name"]),
                ("issues", [("%s: %s -- %s" % (i.path, i.code, i.detail))
                            for i in issues]))))
            continue
        record = OrderedDict((
            # ``key`` is the DISPLAY join key: site_data.verified_public_hotels
            # matches it against normalize_name(seed_row["name"]), and
            # load_published_hotel_policy_facts looks the seed row up by it. So
            # it must derive from the name the record actually publishes, not
            # from the census identity. The two coincide on every live market's
            # 333 records and differ only where a founder-authorised name
            # correction replaced a bare chain word ("courtyard") with the
            # building the page names -- and on exactly those records the join
            # would otherwise FAIL CLOSED, because no seed row can be both the
            # published name and the census word.
            ("key", normalize_name(
                names.get(row["normalized_name"], row["canonical_name"]))),
            # The IDENTITY key, which is a different question: it is the census
            # identity the founder signed against and the key affiliate rows and
            # approval bindings resolve through. validate_record requires it and
            # every live market's records carry it; 010's first draft emitted
            # only "key", so all 82 records failed the record contract while
            # passing the facts contract.
            ("identity_key", row["normalized_name"]),
            ("schema_version", SCHEMA_VERSION),
            ("name", names.get(row["normalized_name"], row["canonical_name"])),
            ("facts", facts),
            ("evidence", [OrderedDict((
                ("field", (item.get("field_refs") or [""])[0]),
                ("quote", item.get("quote", "")),
                ("source_url", row.get("source_url", "")),
                # The store's own reference. The authority does not carry one,
                # and a withholding decision with no reference cannot be
                # re-adjudicated when a better capture arrives.
                ("evidence_ref", item.get("evidence_ref")
                 or evidence_reference(observation,
                                       (item.get("field_refs") or [""])[0],
                                       item.get("quote", ""))),
                ("artifact_class", "PUBLICATION_GRADE_EVIDENCE"),
                ("artifact_sha256", "sha256:%s" % row.get("snapshot_hash", "")),
                ("artifact_kind", "rendered_html"),
                ("captured_at", row.get("observed_at", "")),
                ("capture_method", row.get("capture_method", "")),
                ("source_grade", "PT1_FIRST_PARTY"),
            )) for item in (row.get("evidence") or ())]),
            ("withheld_fields", {}),   # replaced below, once refs are known
            ("non_inferences", list(row.get("non_inferences") or ())),
            ("founder_decision", row.get("founder_decision", "")),
            ("founder_reviewer_id", row.get("founder_reviewer_id", "")),
            ("founder_reviewed_at", row.get("founder_reviewed_at", "")),
        ))
        refs = [e["evidence_ref"] for e in record["evidence"] if e.get("evidence_ref")]
        withheld, withheld_notes, withheld_problems = project_withheld(
            row.get("withheld_fields") or {}, observation, refs)
        if withheld_problems:
            refusals.append(OrderedDict((
                ("identity_key", row["normalized_name"]),
                ("issues", withheld_problems))))
            continue
        record["withheld_fields"] = withheld
        notes.extend(withheld_notes)

        statement = project_service_animal_statement(row.get("facts") or {})
        if statement is not None:
            record["service_animal_statement"] = statement
        if notes:
            record["projection_notes"] = notes

        # The record contract, not just the fact contract. A package whose
        # records fail validate_record is not the same artifact the live
        # markets committed, however clean its fact blocks are.
        record_issues = PS.validate_record(record)
        if record_issues:
            refusals.append(OrderedDict((
                ("identity_key", row["normalized_name"]),
                ("issues", [("%s: %s -- %s" % (i.path, i.code, i.detail))
                            for i in record_issues]))))
            continue
        hotels.append(record)

    hotels.sort(key=lambda r: r["key"])
    return OrderedDict((
        ("market", market_name),
        ("schema_version", SCHEMA_VERSION),
        ("market_id", market_id),
        ("what_this_is",
         "The publishable pet-policy facts for this market, projected from its "
         "founder-signed authority. Every record's fact block passed "
         "contracts.policy_schema.validate_facts before this file was written."),
        ("published", False),
        ("publication_note",
         "published:false -- this package is pre-publication. Flipping the flag "
         "is a separate act by a publication work order."),
        ("derived_from", OrderedDict((
            ("authority", authority.get("schema", "")),
            ("source_ledgers", (authority.get("built_from") or {}).get(
                "source_ledgers", [])),
            ("decided_by", (authority.get("built_from") or {}).get(
                "decided_by", "")),
            # The founder's decision date, carried so publication can be dated
            # from the DECISION and never from the clock: a timestamp would make
            # every rebuild a different file and break the sha256 the release
            # contract pins.
            ("decided_at", (authority.get("built_from") or {}).get(
                "decided_at", "")),
        ))),
        ("count", len(hotels)),
        ("refusals", refusals),
        ("hotels", hotels),
    ))


def published_document(package: Mapping, *, work_order: str,
                       decision_ledgers: Sequence[str] = ()) -> Tuple[Dict, List[str]]:
    """``(published package, changes)`` -- the flag flipped and nothing else.

    Publication is a state of the PACKAGE, never a property of a record. So the
    records are compared byte for byte across the flip and any movement is
    reported rather than published: PTF-MILWAUKEE-PUBLICATION-042 asserted the
    same thing about its market and this is that assertion with no market in it.

    The publication block is dated from the FOUNDER'S DECISION, never from the
    clock. A timestamp here would make every rebuild a different file and would
    break the sha256 the release contract pins.
    """
    doc = OrderedDict(package)
    before = json.dumps(doc.get("hotels") or [], sort_keys=True, ensure_ascii=False)
    doc["published"] = True
    doc["publication_note"] = (
        "published=true admits this market's records to live inventory: "
        "site_data.load_published_hotel_policy_facts returns them and the "
        "assembler builds a profile for each. The records themselves are "
        "unchanged from the day the founder approved them -- same facts, same "
        "approvals, same evidence -- and the publishing work order asserts that "
        "byte for byte. Publication is still not deployment: nothing is live "
        "until a bundle is deployed.")
    doc["publication"] = OrderedDict((
        ("work_order", work_order),
        ("published_for_decision_dated",
         (package.get("derived_from") or {}).get("decided_at", "")),
        ("decision_ledgers", list(decision_ledgers)),
        ("deployed", False),
        ("note", "build-ready in source; no deployment performed"),
    ))
    after = json.dumps(doc.get("hotels") or [], sort_keys=True, ensure_ascii=False)
    changes = [] if before == after else ["a record changed while publishing"]
    return doc, changes


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--authority", required=True)
    parser.add_argument("--market-name", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--expect-count", type=int, default=None)
    parser.add_argument("--normalize-weight", action="store_true",
                        help="apply founder decision 1: a property-specific "
                             "unqualified blanket maximum publishes as lte / "
                             "per_pet. Off by default; the strict reading is "
                             "the default and a caller must name the ruling.")
    parser.add_argument("--cap-qualifier-stated", choices=("true", "false"),
                        default=None,
                        help="apply founder decision 3 to caps whose source "
                             "states no further qualifier")
    parser.add_argument("--name-corrections", default=None,
                        help="the market's evidence-cited canonical-name "
                             "overlay; idempotent where the observation store "
                             "already applied it")
    parser.add_argument("--observations", default=None,
                        help="the market's committed observation store, read "
                             "for evidence references and the reader's own "
                             "withholding sentences; nothing is re-derived")
    parser.add_argument("--publish", metavar="WORK_ORDER", default=None,
                        help="flip published to true, naming the work order "
                             "that performs the act. The records are asserted "
                             "byte-identical across the flip.")
    args = parser.parse_args(argv)

    authority = json.loads(Path(args.authority).read_text(encoding="utf-8"))
    overlay = (json.loads(Path(args.name_corrections).read_text(encoding="utf-8"))
               if args.name_corrections else None)
    store = (json.loads(Path(args.observations).read_text(encoding="utf-8"))
             if args.observations else None)
    document = build(authority, market_name=args.market_name,
                     normalize_weight=args.normalize_weight,
                     cap_qualifier_stated=(
                         None if args.cap_qualifier_stated is None
                         else args.cap_qualifier_stated == "true"),
                     name_corrections=overlay,
                     observations=store)

    if document["refusals"]:
        raise PolicyPackageError(
            "%d record(s) failed schema 1.2 validation and the package was NOT "
            "written: %s" % (len(document["refusals"]),
                             json.dumps(document["refusals"][:3], indent=1)))
    if args.expect_count is not None and document["count"] != args.expect_count:
        raise PolicyPackageError(
            "expected %d records and projected %d"
            % (args.expect_count, document["count"]))

    if args.publish:
        document, changes = published_document(
            document, work_order=args.publish,
            decision_ledgers=(authority.get("built_from") or {}).get(
                "source_ledgers") or ())
        if changes:
            raise PolicyPackageError("; ".join(changes))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(document, indent=1, ensure_ascii=False) + "\n"
    out.write_text(payload, encoding="utf-8", newline="\n")
    print("records projected : %d" % document["count"])
    print("schema validated  : every record, 0 issues")
    print("published flag    : %s" % document["published"])
    print("sha256            : %s" % hashlib.sha256(
        out.read_bytes()).hexdigest())
    print("written           : %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
