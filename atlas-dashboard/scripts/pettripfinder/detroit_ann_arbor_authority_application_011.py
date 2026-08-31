# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-FOUNDER-REVIEW-AND-AUTHORITY-011, Phases 3 and 4.

Signs the founder's decision on the gated candidates and applies it to Detroit's
authority.

FACTS ARE PROJECTED, NEVER AUTHORED. Every published fact comes from
``policy_reading.to_extraction`` -- the committed reader-to-schema projection --
run over the block that was persisted at capture. This run chooses nothing about
a price: where a surface states a charge on two bases the projection WITHHOLDS
the basis, and that withholding is carried through to the record rather than
resolved into whichever reading looks tidier.

WHAT IS VERIFIED BEFORE ANYTHING IS SIGNED, per row:
  * the persisted block is on disk and its sha256 reproduces from those bytes;
  * the source document is on disk and its sha256 reproduces;
  * every quote the projection cites appears VERBATIM AND CONTIGUOUSLY in the
    persisted block -- the check a hash cannot perform, because a hash proves
    the file is unaltered, not that the quotation came out of it;
  * the record passes the policy schema and the evidence contract.

ANY FAILURE STOPS THE WHOLE RUN. A partial authority write is worse than none.

The two HOLD rows are never touched. The founder authorised approval of what
passes the deterministic gates and explicitly withheld those two, so they are
emitted as an exception packet and nothing else.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import hotel_exclusions as EX          # noqa: E402
from scripts.pettripfinder import market_authority as MA          # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR  # noqa: E402
from scripts.pettripfinder.contracts import enums                 # noqa: E402
from scripts.pettripfinder.contracts import evidence as evidence_contract  # noqa: E402
from scripts.pettripfinder.contracts import policy_schema         # noqa: E402

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-FOUNDER-REVIEW-AND-AUTHORITY-011"
DECISION_DATE = "2026-08-29"
FOUNDER = "jfields80"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
CANDIDATES = LP / "detroit_ann_arbor_reconciled_candidates_011.json"
FACTS_PATH = LP / ("hotel_policy_facts_%s.json" % MARKET)
EXCLUSIONS_PATH = MA.exclusions_shard_path(MARKET)
DECISIONS_PATH = LP / "detroit_ann_arbor_founder_decisions_011.json"

#: The founder's authorisation, quoted from the work order. A blanket approval
#: of what the deterministic gates pass, labelled as such -- it is not a
#: per-row note written at a review desk and must not read like one.
AUTHORISATION_CLAUSE = (
    "APPROVE all candidates that pass the deterministic clean-candidate gates. "
    "Do NOT approve the two HOLD rows.")

#: Brand domains. FIRST_PARTY_GRADES admits PT2_BRAND, and every candidate here
#: was read off the brand's own property page rather than the property's own
#: independent domain -- which is what PT2_BRAND means and what prior Detroit
#: records already carry.
SOURCE_GRADE = enums.GRADE_PT2_BRAND
ARTIFACT_KIND = enums.ARTIFACT_RENDERED_HTML
CAPTURE_METHOD = "rendered_fetch"


#: "free of charge", "at no charge", "no additional charge" -- the property
#: saying service animals cost nothing. Anything less explicit stays
#: ``not_addressed``.
_FREE_OF_CHARGE_RE = re.compile(
    r"(?:free\s+of\s+charge|at\s+no\s+(?:additional\s+)?(?:charge|cost)"
    r"|no\s+(?:additional\s+)?(?:charge|fee)s?)", re.I)


class Stop(Exception):
    """Any failure stops the whole run."""


def load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_lf(path: Path, doc) -> None:
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


def verify_artifacts(candidate: Dict) -> Tuple[str, str, str]:
    """(block_text, block_sha, document_sha), re-derived from the bytes."""
    reading = candidate["reading"]
    block_path = _REPO_ROOT / reading["block_artifact"]
    document_path = _REPO_ROOT / reading["document_artifact"]
    if not block_path.is_file():
        raise Stop("%s: the persisted block is gone" % candidate["identity_key"])
    if not document_path.is_file():
        raise Stop("%s: the source document is gone"
                   % candidate["identity_key"])
    block_sha = hashlib.sha256(block_path.read_bytes()).hexdigest()
    document_sha = hashlib.sha256(document_path.read_bytes()).hexdigest()
    if reading.get("block_sha256") and block_sha != reading["block_sha256"]:
        raise Stop("%s: the block sha256 does not reproduce"
                   % candidate["identity_key"])
    if reading.get("document_sha256") and document_sha != reading["document_sha256"]:
        raise Stop("%s: the document sha256 does not reproduce"
                   % candidate["identity_key"])
    return (block_path.read_text(encoding="utf-8-sig"), block_sha, document_sha)


#: Projection fields this run maps into schema 1.2 EXACTLY, and nothing else.
#: The projection speaks a flat, legacy-shaped vocabulary in MINOR units; the
#: schema wants structured objects. Anything whose mapping is not exact is
#: WITHHELD with a reason and reported, never guessed at -- a published price or
#: species that is subtly wrong is worse than one the record does not carry.
#:
#: ``compat_readers`` is deliberately NOT used for this. It migrates LEGACY
#: records, where money was stored in dollars, so it multiplies a bare number by
#: a hundred: the projection's 1500 (meaning $15.00) becomes $1500.00. It is the
#: right adapter for the wrong input.
_SCHEMA_CANNOT_CARRY = {
    # stated on the surface, but the schema shape needs more than the
    # projection supplies, so the fact is withheld rather than approximated
    "species_allowed": "species requires a per-species state map AND a "
                       "species_source_grade for each entry; the projection "
                       "supplies neither",
    "cats_allowed": "same as species_allowed",
    "pet_deposit": "a deposit belongs in other_charges with a kind and a "
                   "basis; the projection supplies a bare amount",
    "fee_cap": "a cap carries its own basis and scope, and never inherits "
               "them from the fee it caps",
}


def to_schema_facts(raw: Dict) -> Tuple[Dict, Dict]:
    """(schema 1.2 facts, withheld). Exact mappings only."""
    facts: "OrderedDict[str, object]" = OrderedDict()
    withheld: Dict[str, str] = {}

    if raw.get("pets_allowed") is True:
        facts["pets_allowed"] = True

    # money stays in the MINOR units the projection already speaks
    amount = raw.get("pet_fee")
    basis = raw.get("fee_basis")
    if isinstance(amount, int) and not isinstance(amount, bool):
        if basis in enums.FEE_BASES:
            fee = OrderedDict([("amount_cents", amount),
                               ("currency", raw.get("fee_currency") or "USD"),
                               ("basis", basis)])
            scope = raw.get("fee_scope")
            if scope in enums.FEE_SCOPES:
                fee["scope"] = scope
            facts["pet_fee"] = fee
        else:
            withheld["pet_fee"] = enums.SCHEMA_CANNOT_REPRESENT

    if isinstance(raw.get("pet_count_limit"), int):
        facts["pet_count_limit"] = raw["pet_count_limit"]
    if raw.get("pet_count_scope"):
        facts["pet_count_scope"] = raw["pet_count_scope"]
    limit = raw.get("weight_limit")
    if isinstance(limit, dict):
        # The schema REQUIRES an operator and a scope. "75lbs or less per pet"
        # plainly means lte/per_pet, but the projection returns only a value and
        # a unit, and reading the qualifier back out of the prose here would be
        # this run authoring a fact. Complete limits pass; the rest are withheld.
        if (limit.get("operator") in ("lt", "lte")
                and limit.get("scope")):
            facts["weight_limit"] = OrderedDict(limit)
        else:
            withheld["weight_limit"] = (
                "the schema requires an operator (lt/lte) and a scope; the "
                "projection supplies only a value and a unit, and inferring "
                "the qualifier here would be authoring the fact")
    if raw.get("fee_tiers"):
        facts["fee_tiers"] = raw["fee_tiers"]

    for field, reason in _SCHEMA_CANNOT_CARRY.items():
        if raw.get(field) not in (None, "", [], {}):
            withheld[field] = reason
    return (facts, withheld)


def build_evidence(entries, block_text: str, source_url: str,
                   document_sha: str, key: str) -> List[Dict]:
    evidence: List[Dict] = []
    for entry in entries:
        quote = entry["quote"]
        if not evidence_contract.quote_is_contiguous(quote, block_text):
            raise Stop("%s: the cited quote %r is not verbatim and contiguous "
                       "in the persisted block" % (key, quote[:60]))
        for field in entry["field_refs"]:
            evidence.append(OrderedDict([
                ("field", field),
                ("quote", quote),
                ("source_url", source_url),
                ("value", ""),
                ("evidence_ref", "ev:%s" % hashlib.sha256(
                    ("%s|%s|%s" % (key, field, quote)).encode("utf-8")
                ).hexdigest()[:16]),
                ("artifact_class", "PUBLICATION_GRADE_EVIDENCE"),
                ("artifact_sha256", "sha256:%s" % document_sha),
                ("artifact_kind", ARTIFACT_KIND),
                ("captured_at", DECISION_DATE),
                ("capture_method", CAPTURE_METHOD),
                ("source_grade", SOURCE_GRADE),
            ]))
    return evidence


def record_hash(record: Dict) -> str:
    payload = {k: v for k, v in record.items() if k != "approval"}
    return "sha256:%s" % hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False)
        .encode("utf-8")).hexdigest()


def evidence_hash(evidence: List[Dict]) -> str:
    return "sha256:%s" % hashlib.sha256(
        json.dumps(evidence, sort_keys=True, ensure_ascii=False)
        .encode("utf-8")).hexdigest()


def build_publication_record(candidate: Dict, census_row: Dict,
                             source_url: str) -> Dict:
    key = candidate["identity_key"]
    block_text, _block_sha, document_sha = verify_artifacts(candidate)

    reading = PR.parse(block_text)
    projection = PR.to_extraction(reading, location=source_url)
    raw_facts = dict(projection.extraction)
    withheld = dict(projection.withheld or {})
    raw_facts, extra_withheld = to_schema_facts(raw_facts)
    withheld.update(extra_withheld)

    # Only schema 1.2 fact fields may be published. The projection returns a
    # richer intermediate shape -- fee_basis, fee_currency and
    # service_animal_exception all live outside ``facts`` in the schema.
    facts = OrderedDict(
        (field, value) for field, value in raw_facts.items()
        if field in policy_schema.KNOWN_FACT_FIELDS)
    if facts.get("pets_allowed") is not True:
        raise Stop("%s: the projection does not affirm pets_allowed" % key)

    evidence = build_evidence(projection.evidence, block_text, source_url,
                              document_sha, key)
    if not evidence:
        raise Stop("%s: the projection cited no evidence" % key)

    quotes: List[str] = []
    for entry in evidence:
        if entry["quote"] not in quotes:
            quotes.append(entry["quote"])

    record = OrderedDict([
        ("key", key), ("name", census_row["canonical_name"]),
        ("facts", facts), ("evidence", evidence),
        ("evidence_count", len(evidence)),
        ("evidence_quote", " […] ".join(quotes)),
        ("source_url", source_url),
        ("source_type", "EXACT_ENTITY_DOMAIN"),
        ("verification_state", "VERIFIED_PET_FRIENDLY"),
        ("verification_date", DECISION_DATE), ("verified_at", DECISION_DATE),
        ("worker_model_id", ""), ("worker_prompt_version", ""),
        ("worker_result_hash", document_sha), ("worker_routing_version", ""),
        ("worker_validator_version", ""), ("schema_version", "1.2"),
        ("identity_key", key), ("market_id", MARKET),
    ])
    if reading.service_animal_quote:
        # An OBJECT, not the quote: the schema holds whether a statement was
        # made and what it said about charges. ``no_charge`` is claimed only
        # where the property's own verbatim words say so -- the compat reader
        # warns against asserting it from a bare boolean, and the reason that
        # warning exists is that the quote is the only thing that can support
        # the claim. The quote itself travels in the evidence.
        quote = reading.service_animal_quote
        free = bool(_FREE_OF_CHARGE_RE.search(quote))
        record["service_animal_statement"] = OrderedDict([
            ("stated", True),
            ("charges_stated", enums.SERVICE_ANIMAL_NO_CHARGE if free
             else enums.SERVICE_ANIMAL_NOT_ADDRESSED),
        ])

    from scripts.pettripfinder import canonical_view
    record["computation_class"] = (
        canonical_view.classify(facts).computation_class
        if hasattr(canonical_view, "classify") else "DIRECT")

    issues = (list(policy_schema.validate_record(record))
              + list(evidence_contract.validate(record)))
    if issues:
        raise Stop("%s: contract issues %s" % (key, issues[:4]))

    caveats = [
        "Founder approval under %s: %s. Evidence is the property's own policy "
        "surface, fetched and rendered by the Firecrawl lane and persisted at "
        "capture; the document sha256 was re-verified from disk at approval "
        "time (%s) and every cited quote checked to appear verbatim and "
        "contiguously in the persisted block."
        % (WORK_ORDER, AUTHORISATION_CLAUSE, document_sha[:23]),
        "Facts are PROJECTED by the committed reader-to-schema path, never "
        "authored here. Founder global rule applied: SOURCE SILENCE IS "
        "ABSENCE -- unstated optional facts are absent, never withheld.",
    ]
    if withheld:
        caveats.append(
            "The projection WITHHELD %s. A charge whose basis the surface "
            "states two ways is not resolved into the tidier reading; it is "
            "carried as withheld so a reviewer sees the ambiguity."
            % ", ".join("%s (%s)" % (field, reason)
                        for field, reason in sorted(withheld.items())))
    if projection.flags:
        caveats.append("Reader flags: %s"
                       % "; ".join(flag["code"] for flag in projection.flags))

    record["approval"] = OrderedDict([
        ("decision", enums.APPROVED_AFTER_CURRENT_REVIEW),
        ("operator", FOUNDER),
        ("approval_date", DECISION_DATE),
        ("authorisation", OrderedDict([
            ("instrument", WORK_ORDER),
            ("clause", AUTHORISATION_CLAUSE),
            ("basis", "The operator authorised approval of every candidate "
                      "passing the deterministic gates, in writing in the work "
                      "order named above. It is a blanket authorisation of the "
                      "gate outcome, not a per-row review note, and is "
                      "labelled that way deliberately."),
            ("source_pass", candidate["source_pass"]),
            ("attempt_id", candidate["attempt_id"]),
        ])),
        ("caveats", caveats),
        ("record_hash", record_hash(record)),
        ("evidence_hash", evidence_hash(evidence)),
    ])
    return record


def build_exclusion_record(candidate: Dict, census_row: Dict,
                           source_url: str) -> Dict:
    key = candidate["identity_key"]
    block_text, _block_sha, document_sha = verify_artifacts(candidate)
    quote = (candidate["reading"].get("block_text") or "").strip()
    if not evidence_contract.quote_is_contiguous(quote, block_text):
        raise Stop("%s: the refusal quote is not verbatim in the artifact" % key)

    record = OrderedDict([
        ("exclusion_id", "dtw-%s" % census_row["slug"]),
        ("canonical_name", census_row["canonical_name"]),
        ("normalized_name", key),
        ("address", census_row.get("address") or ""),
        ("city", census_row.get("city") or ""),
        ("state", census_row.get("state") or ""),
        ("postal_code", census_row.get("postal_code") or ""),
        ("official_url", source_url),
        ("exclusion_state", EX.VERIFIED_NO_PETS),
        ("evidence_quote", quote),
        ("source_url", source_url),
        ("observed_at", DECISION_DATE), ("source_hash", document_sha),
        ("reviewer_id", FOUNDER), ("reviewed_at", DECISION_DATE),
        ("notes",
         "Founder approval under %s: %s. Affirmative first-party refusal in "
         "the property's own words, read off its own policy surface and "
         "persisted at capture; the document sha256 was re-verified from disk "
         "at approval time and the refusal quote checked verbatim against the "
         "persisted block. Service-animal access is a legal category and never "
         "converts a no-pets policy into pet-friendly. Source pass %s, attempt "
         "%s." % (WORK_ORDER, AUTHORISATION_CLAUSE, candidate["source_pass"],
                  candidate["attempt_id"])),
        ("market_id", MARKET),
    ])
    record["record_hash"] = EX.record_hash(record)
    record["approval_hash"] = EX.approval_hash(record)
    return record


def run() -> None:
    doc = load(CANDIDATES)
    clean = doc["clean_candidates"]
    holds = doc["holds"]
    census = {row["identity_key"]: row for row in
              load(LP / "identity_census" / ("%s.json" % MARKET))["hotels"]}
    # THE ROUTED URL, not the ledger's canonical one. The ledger stores a
    # normalized comparison form -- host and path, no scheme -- and a record
    # published with that fails the /go/ destination gate, which refuses a
    # destination it cannot prove is an absolute first-party URL. The routing
    # shard is the authority for where a property is read.
    routed = {route["hotel_ref"]["identity_key"]:
              (route.get("official_property_url") or "")
              for route in load(LP / "markets" / "authority" / MARKET
                                / "identity_routing.json")["routes"]}

    facts_doc = load(FACTS_PATH)
    exclusions_doc = load(EXCLUSIONS_PATH)
    existing_published = {row["identity_key"] for row in facts_doc["hotels"]}
    existing_excluded = {row["normalized_name"]
                         for row in exclusions_doc["exclusions"]}
    before = (len(facts_doc["hotels"]), len(exclusions_doc["exclusions"]))

    publications, exclusions, decisions = [], [], []
    for candidate in clean:
        key = candidate["identity_key"]
        census_row = census.get(key)
        if census_row is None:
            raise Stop("%s: no census row" % key)
        if key in existing_published or key in existing_excluded:
            raise Stop("%s: already carries authority; this run would create a "
                       "duplicate record" % key)
        source_url = routed.get(key) or ""
        if not source_url.lower().startswith("https://"):
            raise Stop("%s: no absolute routed URL; refusing to publish a "
                       "destination the /go/ gate cannot verify" % key)
        if candidate["class"] == "PET_FRIENDLY":
            publications.append(
                build_publication_record(candidate, census_row, source_url))
            state = "APPROVE_PUBLISH"
        else:
            exclusions.append(
                build_exclusion_record(candidate, census_row, source_url))
            state = "APPROVE_VERIFIED_NO_PETS"
        decisions.append(OrderedDict([
            ("identity_key", key),
            ("canonical_name", candidate["canonical_name"]),
            ("decision", state),
            ("decided_by", FOUNDER),
            ("decided_at", DECISION_DATE),
            ("authorisation", WORK_ORDER),
            ("clause", AUTHORISATION_CLAUSE),
            ("source_pass", candidate["source_pass"]),
            ("attempt_id", candidate["attempt_id"]),
        ]))

    for hold in holds:
        decisions.append(OrderedDict([
            ("identity_key", hold["identity_key"]),
            ("canonical_name", hold["canonical_name"]),
            ("decision", "HOLD_FOR_FURTHER_RESEARCH"),
            ("decided_by", ""),
            ("decided_at", ""),
            ("authorisation", WORK_ORDER),
            ("clause", "the founder explicitly withheld approval of the two "
                       "HOLD rows; they are NOT decided by this order"),
        ]))

    # Nothing is written until every record has been built and validated.
    facts_doc["hotels"] = list(facts_doc["hotels"]) + publications
    exclusions_doc["exclusions"] = (list(exclusions_doc["exclusions"])
                                    + exclusions)
    exclusions_doc["count"] = len(exclusions_doc["exclusions"])
    write_lf(FACTS_PATH, facts_doc)
    write_lf(EXCLUSIONS_PATH, exclusions_doc)

    write_lf(DECISIONS_PATH, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-founder-decisions/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET),
        ("decided_at", DECISION_DATE), ("decided_by", FOUNDER),
        ("authorisation", OrderedDict([
            ("instrument", WORK_ORDER),
            ("clause", AUTHORISATION_CLAUSE),
            ("scope", "a blanket approval of the deterministic gate outcome, "
                      "not a per-row review"),
        ])),
        ("provider_calls", 0), ("spend_usd", 0.0),
        ("approved_publish", len(publications)),
        ("approved_verified_no_pets", len(exclusions)),
        ("held_not_decided", len(holds)),
        ("decisions", decisions),
    ]))

    after = (len(facts_doc["hotels"]), len(exclusions_doc["exclusions"]))
    print("=== Phase 3/4: founder decisions applied ===")
    print("  pet-friendly     : %d -> %d  (+%d)"
          % (before[0], after[0], len(publications)))
    print("  verified no-pets : %d -> %d  (+%d)"
          % (before[1], after[1], len(exclusions)))
    print("  held, not decided:", len(holds))
    print("  total resolved   :", after[0] + after[1])
    print("wrote", FACTS_PATH.name, EXCLUSIONS_PATH.name, DECISIONS_PATH.name)


if __name__ == "__main__":
    try:
        run()
    except Stop as stop:
        raise SystemExit("STOP: %s" % stop)
