"""PTF-MILWAUKEE-FOUNDER-DECISION-036 -- apply the decisions, build authority.

Turns the founder's recorded decisions into Milwaukee's first policy authority.
Two outputs, one for each kind of answer a traveller needs:

* ``hotel_policy_facts_milwaukee-wi.json`` -- the approved pet policies,
  written with ``published: false``. That flag is not decoration:
  ``site_data.load_published_hotel_policy_facts`` returns {} for a package that
  carries it, so this is RECORDED AUTHORITY and not live inventory. Nothing
  reaches a page until a later work order flips it deliberately.
* ``hotel_exclusions.json`` -- the approved refusals, as VERIFIED_NO_PETS rows
  beside the four markets already there. A hotel that refuses pets answers the
  question as usefully as one that takes them.

THE CONVERSION IS THE DANGEROUS PART
------------------------------------
The store speaks the READER's vocabulary and an authority record speaks schema
1.2. They disagree about units, field names and where a fact lives, and the
obvious shortcut is catastrophic: ``compat_readers.read_record`` -- the
repository's legacy converter -- reads the store's ``pet_fee: 5000`` as FIVE
THOUSAND DOLLARS, because a bare number in a 1.0 record meant dollars and in
this store it means cents. It also drops the basis. That converter is for
legacy PUBLISHED records and is not used here.

So every field is converted explicitly, and every conversion is derived from
what the source itself said:

* ``pet_fee`` is already minor units. It is copied, never scaled.
* ``weight_limit`` needs an operator and a scope that 1.2 requires and the
  reader deliberately refuses to invent. The operator is taken from the row's
  OWN quote -- "maximum", "up to", "or less" is ``lte``, "under" or "less than"
  is ``lt`` -- and a row whose quote states neither is REFUSED rather than
  defaulted. The scope is ``per_pet`` because the reader never puts a combined
  figure in this field; a combined weight has its own.
* ``service_animal_exception`` moves OUT of facts. 1.2 rejects it there on
  purpose: a legal access category beside a weight limit invites something to
  apply one to the other.
* a deposit becomes an ``other_charges`` entry only when the source states its
  refundability in words, because that flag is mandatory and never inferred.
* ``pet_count_scope`` is translated to the word the committed corpus already
  uses (``room``), not the reader's ``per_room``.

FAIL CLOSED, PER RECORD
-----------------------
Every record is validated under schema 1.2 before it is admitted, its
``computation_class`` is DERIVED rather than asserted, and its approval is
re-bound to hashes recomputed from the live row -- checked equal to the hashes
the founder was shown. A record that fails any of that is refused
individually, reported by name, and left out. It is never folded into the
cohort it no longer belongs to.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import founder_decisions_036 as D    # noqa: E402
from scripts.pettripfinder.acquisition import founder_review_036 as F       # noqa: E402
from scripts.pettripfinder.acquisition import reader_to_tiers_034 as R34    # noqa: E402
from scripts.pettripfinder.contracts import enums                           # noqa: E402
from scripts.pettripfinder.contracts import fee_computation                 # noqa: E402
from scripts.pettripfinder.contracts import policy_schema as SCHEMA         # noqa: E402
from scripts.pettripfinder import hotel_exclusions as EX                    # noqa: E402
from scripts.pettripfinder import market_authority as MA                    # noqa: E402
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key   # noqa: E402
from scripts.pettripfinder import approval_binding as AB
from scripts.pettripfinder.acquisition import approval_rebinding_039 as REBIND
from scripts.pettripfinder.policy_migration import evidence_hash, record_hash  # noqa: E402

WORK_ORDER = D.WORK_ORDER
MARKET = F.MARKET
MARKET_NAME = "Greater Milwaukee"

PKG = F.PKG
AUTHORITY = PKG / ("hotel_policy_facts_%s.json" % MARKET)
#: The exclusion authority is SHARDED (PTF-MARKET-AUTHORITY-SHARDING-001):
#: market work writes its own shard and the global file is generated from every
#: market's. Both paths come from ``market_authority`` rather than being spelled
#: here -- a module that composes the global path itself is exactly what the
#: write-discipline test looks for, and hand-writing that file broke the site
#: assembler for five other markets before this was corrected.
EXCLUSION_SHARD = MA.exclusions_shard_path(MARKET)
RUN_REPORT = F.REPORTS / "ptf_milwaukee_authority_build_036.json"

APPROVE = D.APPROVE
APPROVE_REFUSAL = D.APPROVE_REFUSAL
HOLD = D.HOLD

VERIFIED_PET_FRIENDLY = "VERIFIED_PET_FRIENDLY"
VERIFIED_NO_PETS = "VERIFIED_NO_PETS"
APPROVAL_DECISION = "APPROVED_AFTER_CURRENT_REVIEW"

#: The operator a weight limit carries, taken from the source's own words.
_LTE_WORDS = re.compile(
    r"\b(?:max|maximum|up\s+to|no\s+more\s+than|or\s+less|not\s+to\s+exceed"
    r"|limit|limits)\b", re.IGNORECASE)
_LT_WORDS = re.compile(r"\b(?:under|less\s+than|below)\b", re.IGNORECASE)

#: The reader's word for a per-room count, and the corpus's committed word.
_COUNT_SCOPE = {"per_room": "room", "per_pet": "pet", "room": "room"}

#: Reader species names to the authority's plural state map.
_SPECIES_NAMES = {"dog": "dogs", "cat": "cats", "bird": "birds",
                  "fish": "fish", "other": "other"}

#: Refundability, stated in the source's own words or not written at all.
_REFUNDABLE_RE = re.compile(r"\brefundable\b", re.IGNORECASE)
_NON_REFUNDABLE_RE = re.compile(r"\bnon[-\s]?refundable\b", re.IGNORECASE)


class AuthorityError(RuntimeError):
    """A record cannot be admitted, and no guess will be made instead."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha(text: str) -> str:
    return "sha256:%s" % hashlib.sha256((text or "").encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# The decisions, re-bound at application time.
# --------------------------------------------------------------------------- #

def ledger() -> Dict:
    doc = F.load_ledger()
    if doc is None:
        raise AuthorityError(
            "no founder decision ledger exists at %s; authority is admitted by "
            "a decision, never by a review status"
            % F.LEDGER.relative_to(REPO).as_posix())
    return doc


def bound_decisions() -> Tuple[List[Dict], List[Dict]]:
    """(applicable, refused) decisions, each re-checked against the live row.

    Dayton's rule, kept: an approval is a statement about a specific record, so
    the hashes are recomputed from the row as it stands NOW and compared with
    the hashes the founder was shown. A record that has moved since is refused
    by name rather than approved on the strength of an older reading.

    TWO BINDINGS, EITHER SUFFICIENT, NEITHER LOOSE
    -----------------------------------------------
    036's hashes covered the whole store row, provenance included, so a reader
    repair withdrew fifteen approvals whose facts and evidence were
    byte-identical. PTF-...-APPROVAL-BINDING-039 added a versioned SEMANTIC
    binding over what the founder actually approved, and a decision applies if
    either binding holds.

    The semantic route is not a fallback for anything: it only admits a row the
    039 migration examined and proved unchanged, by name. A row whose meaning
    moved is absent from that index and is refused here exactly as before.
    """
    live = {row["identity_key"]: row for row in F.cohort_rows()}
    applicable: List[Dict] = []
    refused: List[Dict] = []
    for decision in ledger()["decisions"]:
        key = decision["identity_key"]
        row = live.get(key)
        if row is None:
            refused.append(dict(decision, refusal_reason=(
                "the identity is no longer a review candidate")))
            continue
        current_record = record_hash(row)
        current_evidence = evidence_hash(row.get("evidence") or ())
        if (current_record == decision["record_hash"]
                and current_evidence == decision["evidence_hash"]):
            applicable.append(dict(decision, _row=row,
                                   _bound_by="record_hash+evidence_hash (036)"))
            continue
        rebound = REBIND.rebound_index().get(key)
        # All three must agree: the decision must still be the one 039
        # examined (its own two hashes, unaltered in the ledger) AND the live
        # row must still mean what that migration proved it meant. A tampered
        # ledger entry matches neither route and is refused by name, exactly
        # as it was before the semantic binding existed.
        if (rebound
                and rebound[1] == decision["record_hash"]
                and rebound[2] == decision["evidence_hash"]
                and rebound[0] == AB.semantic_hash(row)):
            applicable.append(dict(
                decision, _row=row,
                _bound_by=AB.BINDING_CONTRACT_VERSION,
                _rebinding_note=(
                    "the 036 hashes no longer match because implementation "
                    "provenance moved; 039 proved the approved meaning is "
                    "unchanged and rebound this decision by name")))
            continue
        if current_record != decision["record_hash"]:
            refused.append(dict(decision, refusal_reason=(
                "the record has moved since the founder saw it (%s -> %s)"
                % (decision["record_hash"][:23], current_record[:23]))))
            continue
        refused.append(dict(decision, refusal_reason=(
            "the evidence has moved since the founder saw it")))
    return applicable, refused


# --------------------------------------------------------------------------- #
# Store vocabulary -> schema 1.2.
# --------------------------------------------------------------------------- #

def _quotes_for(row: Mapping, field: str) -> str:
    return " ".join(item.get("quote", "") for item in (row.get("evidence") or ())
                    if field in (item.get("field_refs") or ()))


def weight_operator(row: Mapping) -> str:
    """The comparison the SOURCE states, or "" when it states none."""
    quote = _quotes_for(row, "weight_limit")
    if _LT_WORDS.search(quote):
        return enums.OPERATOR_LT if hasattr(enums, "OPERATOR_LT") else "lt"
    if _LTE_WORDS.search(quote):
        return enums.OPERATOR_LTE if hasattr(enums, "OPERATOR_LTE") else "lte"
    return ""


def service_animal_statement(row: Mapping) -> Optional[Dict]:
    """The legal access category, outside the commercial-terms namespace."""
    facts = row["proposed_facts"] or {}
    statement = facts.get("service_animal_exception")
    if not statement:
        return None
    lowered = str(statement).lower()
    if re.search(r"without\s+charge|no\s+charge|free\s+of\s+charge", lowered):
        charges = "no_charge"
    elif re.search(r"\bfee\b|\bcharge\b", lowered):
        charges = "charge_stated"
    else:
        charges = "not_addressed"
    return {"stated": True, "charges_stated": charges,
            "quote": str(statement)}


def to_facts(row: Mapping) -> Tuple[Dict, List[str]]:
    """One store row's facts as schema 1.2, and every conversion note."""
    legacy = dict(row["proposed_facts"] or {})
    facts: Dict = OrderedDict()
    notes: List[str] = []

    if "pets_allowed" in legacy:
        facts["pets_allowed"] = bool(legacy["pets_allowed"])

    if "pet_fee" in legacy:
        # ALREADY minor units. Copied, never scaled: the legacy converter reads
        # a bare number as dollars and would publish $50.00 as $5,000.00.
        fee: Dict = OrderedDict([("amount_cents", int(legacy["pet_fee"])),
                                 ("currency", legacy.get("fee_currency", "USD"))])
        if legacy.get("fee_basis"):
            fee["basis"] = legacy["fee_basis"]
        if legacy.get("fee_scope"):
            fee["scope"] = legacy["fee_scope"]
        facts["pet_fee"] = fee
        notes.append("pet_fee copied in minor units (%d cents)"
                     % fee["amount_cents"])

    for key in ("fee_tiers", "fee_pet_schedule"):
        if legacy.get(key):
            facts[key] = legacy[key]           # already written in 1.2 by 034
            notes.append("%s carried through unchanged" % key)

    if legacy.get("fee_cap"):
        cap = legacy["fee_cap"]
        facts["fee_cap"] = OrderedDict([
            ("amount_cents", int(cap["amount_minor"])),
            ("currency", cap.get("currency", "USD")),
            ("basis", cap.get("basis")),
            # The source states a ceiling and no qualifier for it -- no pet
            # count, no ordinal, no trigger. Recorded as false rather than
            # omitted, because the field's whole job is to say which happened.
            ("qualifier_stated", False),
        ])
        if facts["fee_cap"]["basis"] is None:
            facts["fee_cap"].pop("basis")
        notes.append("fee_cap converted from amount_minor to amount_cents")

    if legacy.get("weight_limit"):
        operator = weight_operator(row)
        if not operator:
            raise AuthorityError(
                "the weight limit states no comparison in its own quote (%r); "
                "1.2 requires one and this layer does not default it"
                % _quotes_for(row, "weight_limit")[:120])
        weight = dict(legacy["weight_limit"])
        facts["weight_limit"] = OrderedDict([
            ("value", float(weight["value"])),
            ("unit", weight.get("unit", "lb")),
            ("operator", operator),
            # The reader never puts a combined figure here -- a combined weight
            # has its own field -- so this is a per-animal limit by
            # construction, not by inference.
            ("scope", "per_pet"),
        ])
        notes.append("weight_limit operator %r read from the source's own "
                     "words" % operator)

    if legacy.get("combined_weight_limit"):
        combined = dict(legacy["combined_weight_limit"])
        facts["combined_weight_limit"] = OrderedDict([
            ("value", float(combined["value"])),
            ("unit", combined.get("unit", "lb")),
        ])

    if legacy.get("pet_count_limit") is not None:
        facts["pet_count_limit"] = int(legacy["pet_count_limit"])
    if legacy.get("pet_count_scope"):
        scope = _COUNT_SCOPE.get(legacy["pet_count_scope"])
        if scope is None:
            raise AuthorityError("unknown pet_count_scope %r"
                                 % legacy["pet_count_scope"])
        facts["pet_count_scope"] = scope

    if legacy.get("species_allowed"):
        species: Dict = OrderedDict()
        grades: Dict = OrderedDict()
        for name in legacy["species_allowed"]:
            mapped = _SPECIES_NAMES.get(str(name).lower())
            if mapped is None:
                raise AuthorityError("unknown species %r" % name)
            species[mapped] = enums.SPECIES_ACCEPTED
            grades[mapped] = "PT1_FIRST_PARTY"
        facts["species"] = species
        facts["species_source_grade"] = grades
        notes.append("species_allowed is an affirmative-mention list: a "
                     "species the page does not name is NOT prohibited, it is "
                     "simply not stated, and none is written here")

    charges: List[Dict] = []
    if legacy.get("pet_deposit") is not None:
        # The SENTENCE, not the clipped quote. One property states "Refundable
        # deposit of 100 USD is required Per Stay" and the reader's quote keeps
        # only "deposit of 100 USD" -- refusing the record for a word the page
        # prints two characters earlier would lose a real policy to a
        # formatting artefact. The same rule the review package applies to a
        # contrastive refusal: read the whole statement.
        quote = _quotes_for(row, "pet_deposit")
        block, _path = R34.block_for(row)
        sentence = F.containing_sentence(block, quote)
        quote = sentence or quote
        if _NON_REFUNDABLE_RE.search(quote):
            kind, refundable = enums.CHARGE_NON_REFUNDABLE_FEE, False
        elif _REFUNDABLE_RE.search(quote):
            kind, refundable = enums.CHARGE_REFUNDABLE_DEPOSIT, True
        else:
            raise AuthorityError(
                "the deposit's own quote (%r) does not state refundability, "
                "and 1.2 requires it and never infers it" % quote[:120])
        charges.append(OrderedDict([
            ("kind", kind),
            ("amount_cents", int(legacy["pet_deposit"])),
            ("currency", "USD"),
            ("refundable", refundable),
        ]))
        notes.append("pet_deposit written as other_charges[%s] with "
                     "refundable=%s, read from the source's own words"
                     % (kind, refundable))
    if legacy.get("cleaning_fee") is not None:
        raise AuthorityError(
            "a cleaning fee needs a stated refundability and a basis this "
            "layer will not invent")
    if charges:
        facts["other_charges"] = charges

    for key in ("breed_restrictions", "reservation_requirement",
                "unattended_policy", "general_restrictions",
                "weight_limit_stated_none", "breed_restrictions_stated_none"):
        if legacy.get(key) is not None:
            facts[key] = legacy[key]

    return facts, notes


# --------------------------------------------------------------------------- #
# The record.
# --------------------------------------------------------------------------- #

def _evidence_entries(row: Mapping, facts: Mapping) -> List[Dict]:
    """Per-field evidence, bound to the document it was read from."""
    provenance = row.get("provenance") or {}
    document = provenance.get("snapshot_hash", "")
    if document and not document.startswith("sha256:"):
        document = "sha256:%s" % document
    out: List[Dict] = []
    for item in row.get("evidence") or ():
        quote = item.get("quote", "")
        for field in item.get("field_refs") or ():
            out.append(OrderedDict([
                ("field", field),
                ("quote", quote),
                ("source_url", provenance.get("source_url", "")),
                ("evidence_ref", "ev:%s" % hashlib.sha256(
                    ("%s|%s|%s" % (field, quote, provenance.get("source_url", "")))
                    .encode("utf-8")).hexdigest()[:16]),
                ("artifact_class", "PUBLICATION_GRADE_EVIDENCE"),
                ("artifact_sha256", document),
                ("artifact_kind", "rendered_html"),
                ("captured_at", provenance.get("retrieved_at", "")),
                ("capture_method", provenance.get("capture_method", "")),
                ("source_grade", "PT1_FIRST_PARTY"),
            ]))
    return out


def authority_record(decision: Mapping) -> Dict:
    """One approved row as a schema-1.2 authority record, or an error."""
    row = decision["_row"]
    facts, notes = to_facts(row)
    provenance = row.get("provenance") or {}
    identity = F.census_rows().get(row["identity_key"]) or {}
    key = ptf_identity_key(row["canonical_name"])
    if key != row["identity_key"]:
        raise AuthorityError(
            "the canonical name keys to %r and the store row is %r"
            % (key, row["identity_key"]))

    record: Dict = OrderedDict([
        ("key", row["identity_key"]),
        ("identity_key", row["identity_key"]),
        ("name", row["canonical_name"]),
        ("market_id", MARKET),
        ("schema_version", enums.POLICY_SCHEMA_VERSION),
        ("facts", facts),
    ])

    statement = service_animal_statement(row)
    if statement:
        record["service_animal_statement"] = statement

    record["computation_class"] = fee_computation.classify(facts).computation_class

    evidence = _evidence_entries(row, facts)
    record["evidence"] = evidence
    record["evidence_count"] = len(evidence)
    record["evidence_quote"] = re.sub(
        r"\s+", " ", (row.get("evidence") or [{}])[0].get("quote", "")).strip()
    record["source_url"] = provenance.get("source_url", "")
    record["source_type"] = "EXACT_ENTITY_DOMAIN"
    record["verification_state"] = VERIFIED_PET_FRIENDLY
    record["verification_date"] = decision["decided_at"]
    record["verified_at"] = provenance.get("retrieved_at", "")
    record["address"] = identity.get("address", "")
    record["city"] = identity.get("city", "")
    record["state"] = identity.get("state", "")
    record["postal_code"] = identity.get("postal_code", "")

    issues = SCHEMA.validate_record(record)
    if issues:
        raise AuthorityError("schema 1.2: %s"
                             % "; ".join(str(issue) for issue in issues))
    disagreements = fee_computation.classification_disagreements(record)
    if disagreements:
        raise AuthorityError("; ".join(disagreements))

    # The approval signs the record, so it is attached AFTER the record is
    # final and binds the hashes recomputed from it.
    record["approval"] = OrderedDict([
        ("decision", APPROVAL_DECISION),
        ("operator", decision["decided_by"]),
        ("approval_date", decision["decided_at"]),
        ("decision_source", OrderedDict([
            ("kind", "FOUNDER_DECISION"),
            ("work_order", WORK_ORDER),
            ("review_work_order", F.WORK_ORDER),
            ("ledger", F.LEDGER.name),
            ("decision_basis", decision["decision_basis"]),
            ("reason", decision["reason"]),
            ("decided_by", decision["decided_by"]),
            ("decided_at", decision["decided_at"]),
        ])),
        ("record_hash", record_hash(record)),
        ("evidence_hash", evidence_hash(evidence)),
        ("reviewed_record_hash", decision["record_hash"]),
        ("reviewed_evidence_hash", decision["evidence_hash"]),
        ("conversion_notes", notes),
    ])
    return record


def build_records() -> Tuple[List[Dict], List[Dict]]:
    """(admitted, refused) -- fail closed, per record."""
    applicable, refused = bound_decisions()
    admitted: List[Dict] = []
    for decision in applicable:
        if decision["decision"] != APPROVE:
            continue
        try:
            admitted.append(authority_record(decision))
        except (AuthorityError, Exception) as error:   # noqa: BLE001
            refused.append({"identity_key": decision["identity_key"],
                            "canonical_name": decision["canonical_name"],
                            "decision": decision["decision"],
                            "refusal_reason": str(error)})
    admitted.sort(key=lambda record: record["identity_key"])
    return admitted, refused


# --------------------------------------------------------------------------- #
# The refusals.
# --------------------------------------------------------------------------- #

def exclusion_rows() -> Tuple[List[Dict], List[Dict]]:
    """The approved refusals as registry rows, built to the registry's contract.

    ``hotel_exclusions`` owns this shape and validates it: seventeen required
    fields, a ``normalized_name`` that must re-derive from the canonical name,
    and two hashes that must re-derive from the row. They are computed with the
    registry's OWN functions rather than reproduced here -- a second
    implementation of a hash is a second answer to the same question.

    A row missing anything the contract requires is REFUSED by name. This
    registry is four other markets' committed attestations, and a malformed
    Milwaukee row does not fail Milwaukee: it fails every market that reads the
    file, which is how this defect was found.
    """
    applicable, _ = bound_decisions()
    identity = F.census_rows()
    rows: List[Dict] = []
    refused: List[Dict] = []
    for decision in applicable:
        if decision["decision"] != APPROVE_REFUSAL:
            continue
        row = decision["_row"]
        facts = row["proposed_facts"] or {}
        provenance = row.get("provenance") or {}
        census = identity.get(row["identity_key"]) or {}
        quote = _quotes_for(row, "pets_allowed").strip()
        if facts.get("pets_allowed") is not False or not quote:
            refused.append({"identity_key": row["identity_key"],
                            "refusal_reason": "no quoted refusal on the row"})
            continue
        block, _path = R34.block_for(row)
        document = provenance.get("snapshot_hash", "")
        if document and not document.startswith("sha256:"):
            document = "sha256:%s" % document
        record = OrderedDict([
            ("exclusion_id", "mke-%s" % (census.get("slug")
                                         or row["identity_key"].replace(" ", "-"))),
            ("canonical_name", row["canonical_name"]),
            ("normalized_name", EX.normalize_name(row["canonical_name"])),
            ("address", census.get("address", "")),
            ("city", census.get("city", "")),
            ("state", census.get("state", "")),
            ("postal_code", census.get("postal_code", "")),
            ("official_url", census.get("official_url", "")
             or provenance.get("source_url", "")),
            ("exclusion_state", VERIFIED_NO_PETS),
            ("evidence_quote", quote),
            # The whole statement, because three words are not a decision: the
            # founder ruled on these using the full context and the registry
            # keeps what they read.
            ("evidence_context", re.sub(r"\s+", " ", block).strip()[:400]),
            ("source_url", provenance.get("source_url", "")),
            ("observed_at", (provenance.get("retrieved_at", "") or "")[:10]),
            ("source_hash", document),
            ("reviewer_id", decision["decided_by"]),
            ("reviewed_at", decision["decided_at"]),
            ("notes", "affirmative refusal on the property's own page; "
                      "service-animal language is a legal access category and "
                      "is never read as a pet permission or as a refusal on "
                      "its own"),
            ("market_id", MARKET),
            ("decision_source", OrderedDict([
                ("work_order", WORK_ORDER),
                ("ledger", F.LEDGER.name),
                ("decision_basis", decision["decision_basis"]),
            ])),
        ])
        record["record_hash"] = EX.record_hash(record)
        record["approval_hash"] = EX.approval_hash(record)

        missing = [field for field in EX.REQUIRED_FIELDS
                   if not str(record.get(field, "")).strip()]
        if missing:
            refused.append({"identity_key": row["identity_key"],
                            "refusal_reason": "the registry requires %s and "
                                              "this row states none"
                                              % ", ".join(missing)})
            continue
        if record["normalized_name"] != EX.normalize_name(record["canonical_name"]):
            refused.append({"identity_key": row["identity_key"],
                            "refusal_reason": "normalized_name does not derive "
                                              "from the canonical name"})
            continue
        rows.append(record)
    rows.sort(key=lambda item: item["exclusion_id"])
    return rows, refused


# --------------------------------------------------------------------------- #
# Writing.
# --------------------------------------------------------------------------- #

def authority_document() -> Dict:
    records, refused = build_records()
    return OrderedDict([
        ("schema_version", enums.POLICY_SCHEMA_VERSION),
        ("market", MARKET_NAME),
        ("market_id", MARKET),
        # RECORDED AUTHORITY, NOT LIVE INVENTORY. site_data's loader returns {}
        # for a package carrying this flag, so nothing here reaches a page
        # until a later work order flips it deliberately.
        ("published", False),
        ("published_note", (
            "published=false means this package is recorded authority and is "
            "NOT live inventory: site_data.load_published_hotel_policy_facts "
            "returns nothing for it. Founder approval admits a record to "
            "authority; publication is a separate, later decision.")),
        ("provenance", OrderedDict([
            ("work_order", WORK_ORDER),
            ("review_work_order", F.WORK_ORDER),
            ("decision_ledger", F.LEDGER.name),
            ("decided_by", ledger()["decided_by"]),
            ("decided_at", ledger()["decided_at"]),
            # The founder's decision date, not the clock. A timestamp here
            # makes every rebuild a diff and makes the package's sha256
            # unpinnable -- which is what PTF-MILWAUKEE-PUBLICATION-037
            # hit when its release contract tried to pin one.
            ("built_for_decision_dated", ledger()["decided_at"]),
            ("source_store", F.STORE.relative_to(REPO).as_posix()),
            ("source_store_sha256", F._sha256_file(F.STORE)),
        ])),
        ("hotels", records),
        ("refused_records", refused),
    ])


def exclusions_document() -> Tuple[Dict, List[Dict], List[Dict]]:
    """Milwaukee's SHARD of the exclusion authority, plus what it refused.

    The shard is this market's slice and the only file a market work order may
    write; the global registry is regenerated from every market's shard. The
    whole assembled registry is still validated here, because a malformed
    Milwaukee row does not fail Milwaukee -- it fails every market that reads
    the generated file.
    """
    shard = json.loads(EXCLUSION_SHARD.read_text(encoding="utf-8-sig"))
    existing = list(shard.get("exclusions") or ())
    keys = {row.get("normalized_name") for row in existing}
    added, refused = exclusion_rows()
    fresh = [row for row in added if row["normalized_name"] not in keys]
    shard["exclusions"] = existing + fresh
    shard["count"] = len(shard["exclusions"])
    return shard, fresh, refused


def assembled_registry(shard: Mapping) -> Dict:
    """The global registry as the shards produce it, for validation only."""
    doc = MA.assemble_exclusions_document()
    others = [row for row in doc.get("exclusions") or ()
              if row.get("market_id") != MARKET]
    doc["exclusions"] = others + list(shard.get("exclusions") or ())
    EX.validate(doc)
    return doc


def write(apply: bool = False) -> Dict:
    records, refused = build_records()
    authority = authority_document()
    shard, fresh, refused_exclusions = exclusions_document()
    registry = assembled_registry(shard)
    generated = ""
    if apply:
        AUTHORITY.write_text(
            json.dumps(authority, indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8")
        EXCLUSION_SHARD.write_text(
            json.dumps(shard, indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8")
        # The globals are GENERATED from the shards, by their own builder.
        # Writing them here by hand is the thing the sharding work order
        # forbids, and the builder is deterministic.
        from scripts.pettripfinder import build_global_authority as GLOBALS
        GLOBALS.main(["--write"])
        generated = "build_global_authority --write"
    return {
        "applied": apply,
        "authority_rows": len(records),
        "authority_refused": refused,
        "exclusion_shard_rows_added": len(fresh),
        "exclusion_shard_total": len(shard["exclusions"]),
        "exclusion_rows_refused": refused_exclusions,
        "registry_total_after_assembly": len(registry["exclusions"]),
        "globals_regenerated_by": generated,
        "authority_path": AUTHORITY.relative_to(REPO).as_posix(),
        "exclusion_shard_path": EXCLUSION_SHARD.relative_to(REPO).as_posix(),
    }


# --------------------------------------------------------------------------- #
# Reporting.
# --------------------------------------------------------------------------- #

def counters() -> Dict:
    numbers = dict(F.counters())
    applicable, refused = bound_decisions()
    approved = [d for d in applicable if d["decision"] in (APPROVE,
                                                           APPROVE_REFUSAL)]
    records, record_refusals = build_records()
    shard, fresh, _ = exclusions_document()
    numbers.update({
        "founder_approved": len(approved),
        "approved_pet_friendly": sum(1 for d in applicable
                                     if d["decision"] == APPROVE),
        "approved_refusal": sum(1 for d in applicable
                                if d["decision"] == APPROVE_REFUSAL),
        "held_by_founder": sum(1 for d in applicable if d["decision"] == HOLD),
        "decisions_refused_at_application": len(refused),
        "authority_rows": len(records),
        "authority_records_refused": len(record_refusals),
        "exclusion_rows_added": len(fresh),
        "deployed_live": 0,
    })
    return numbers


def build_report() -> Dict:
    records, refused = build_records()
    shard, fresh, refused_exclusions = exclusions_document()
    registry = assembled_registry(shard)
    applicable, decision_refusals = bound_decisions()
    return OrderedDict([
        ("schema", "ptf-milwaukee-authority-build/1.0"),
        ("work_order", WORK_ORDER),
        ("market", MARKET),
        ("generated_at", _now()),
        ("ledger", OrderedDict([
            ("path", F.LEDGER.relative_to(REPO).as_posix()),
            ("sha256", F._sha256_file(F.LEDGER)),
            ("decided_by", ledger()["decided_by"]),
            ("decided_at", ledger()["decided_at"]),
            ("counts", ledger()["counts"]),
        ])),
        ("decisions_applied", len(applicable)),
        ("decisions_refused_at_application", decision_refusals),
        ("authority", OrderedDict([
            ("path", AUTHORITY.relative_to(REPO).as_posix()),
            ("rows", len(records)),
            ("published", False),
            ("refused", refused),
            ("schema_validated", True),
        ])),
        ("exclusions", OrderedDict([
            ("shard_path", EXCLUSION_SHARD.relative_to(REPO).as_posix()),
            ("global_path", "launch_packages/pettripfinder/"
                            "hotel_exclusions.json (generated)"),
            ("global_is_generated_from_shards", True),
            ("added", len(fresh)),
            ("market_total", len(shard["exclusions"])),
            ("registry_total", len(registry["exclusions"])),
            ("refused", refused_exclusions),
        ])),
        ("held_by_founder", [d["identity_key"] for d in applicable
                             if d["decision"] == HOLD]),
        ("counters", counters()),
        ("cost", F.cost()),
        ("deployed", 0),
    ])


def write_report() -> Dict:
    doc = build_report()
    RUN_REPORT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")
    return doc


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=WORK_ORDER)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args(argv)

    if args.dry_run or args.apply:
        result = write(apply=args.apply)
        print(json.dumps(result, indent=2)[:4000])
    if args.report:
        doc = write_report()
        print(json.dumps(doc["counters"], indent=2))
    return 0


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(main())
