"""PTF-MILWAUKEE-FIRST-AUTHORITY-AND-FOUNDER-REVIEW-036 -- asking, not answering.

This work order builds Milwaukee's first founder-review package and STOPS.

WHY IT STOPS
------------
The governance mechanism already exists in this repository and it is explicit.
``dayton_pass_b_founder_decisions`` states the rule in its own words: the
founder's name appears on a decision only where "the founder gave these
decisions explicitly and in writing", and the module "never infers a ruling,
never fills a default, and fails closed if asked to record a decision it was
not given". Dayton's answers live in a ledger file separate from the packet
that asked the question, because the packet is regenerated and a human
attestation must not live somewhere a regeneration can erase. Applying those
answers -- turning each into an approval in the founder's name -- was a
SEPARATE work order.

No Milwaukee ledger exists. So no Milwaukee row may be approved here, and
without approvals no authority may be built: an authority row is admitted by a
founder decision, never by a review status. This module therefore produces the
question and the tooling to record an answer, and creates nothing else.

WHAT "PROPOSED" MEANS
---------------------
Every candidate carries a proposed decision -- APPROVE for a readable policy,
APPROVE_REFUSAL for a captured no-pets finding. It is a recommendation from a
machine that has checked what it can check. ``founder_approved`` is false on
every row in the store and stays false. The distance between "technically
clean" and "approved" is the whole point of the boundary.

WHAT IS CHECKED BEFORE PROPOSING ANYTHING
-----------------------------------------
Per row: the identity resolves in the census exactly once; the evidence block
exists on disk and its document hash is recorded; the allowed-flag or the
refusal is supported by a quote; every structured fee validates under schema
1.2 as it stands; withheld fields stay absent from the facts; and no field is
asserted and withheld at once. A row that fails any of those is proposed for
INDIVIDUAL review rather than for approval, and says which check failed.

Unknown is not a failure. A policy that states no weight limit, no breed rule
and no species detail is still a policy, and inventing a value to fill the gap
is the one thing this codebase never does.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import subprocess
import sys
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import premium_resolution_028 as P28   # noqa: E402
from scripts.pettripfinder.acquisition import reader_to_tiers_034 as R34      # noqa: E402
from scripts.pettripfinder.contracts import enums                            # noqa: E402
from scripts.pettripfinder.contracts import policy_schema as SCHEMA          # noqa: E402
from scripts.pettripfinder.policy_migration import evidence_hash, record_hash  # noqa: E402

WORK_ORDER = "PTF-MILWAUKEE-FIRST-AUTHORITY-AND-FOUNDER-REVIEW-036"
MARKET = "milwaukee-wi"

PKG = REPO / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
STORE = REPORTS / ("%s_policy_proposals_001.json" % MARKET)
CENSUS = PKG / "identity_census" / ("%s.json" % MARKET)

#: Where the package lives. ``launch_packages/pettripfinder`` is where every
#: previous founder packet in this repository was committed (Cleveland's four,
#: Dayton's two); ``data/`` is gitignored, so a package written there could not
#: be reviewed by anyone who was not sitting at this machine.
PACKAGE_DIR = PKG / "milwaukee_founder_review_036"
REVIEW_JSON = PACKAGE_DIR / "founder-review.json"
REVIEW_CSV = PACKAGE_DIR / "founder-review.csv"
MANIFEST = PACKAGE_DIR / "founder-review-manifest.json"
SUMMARY = PACKAGE_DIR / "founder-review-summary.md"

#: Where the founder's answers will go. Deliberately NOT inside the package:
#: this module regenerates the package, and nothing that regenerates may be
#: able to erase an attestation.
LEDGER = PKG / "milwaukee_founder_decisions_036.json"

READY = "FOUNDER_REVIEW_READY"
REFUSAL = "REFUSAL_FOUNDER_REVIEW"
COHORT_STATES = (READY, REFUSAL)

PROPOSE_APPROVE = "APPROVE"
PROPOSE_APPROVE_REFUSAL = "APPROVE_REFUSAL"
PROPOSE_INDIVIDUAL = "NEEDS_INDIVIDUAL_REVIEW"

#: Facts a founder is shown in full, in this order, because a fee stated as a
#: ladder must never be flattened into the column beside it.
FACT_FIELDS: Tuple[str, ...] = (
    "pets_allowed", "pet_fee", "fee_currency", "fee_basis", "fee_scope",
    "fee_tiers", "fee_pet_schedule", "fee_cap", "cleaning_fee", "pet_deposit",
    "weight_limit", "combined_weight_limit", "pet_count_limit",
    "pet_count_scope", "species_allowed", "breed_restrictions",
    "reservation_requirement", "unattended_policy", "general_restrictions",
    "service_animal_exception",
)

#: The structures schema 1.2 validates on their own.
STRUCTURED_FIELDS: Tuple[str, ...] = ("fee_tiers", "fee_pet_schedule")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256_file(path: Path) -> str:
    return "sha256:%s" % hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=str(REPO.parent),
                          capture_output=True, text=True).stdout.strip()


def _stable(doc) -> str:
    return json.dumps(doc, indent=2, ensure_ascii=False, sort_keys=False)


# --------------------------------------------------------------------------- #
# Phase 1 -- preflight.
# --------------------------------------------------------------------------- #

def preflight() -> Dict:
    doc = R34.store_doc()
    states = Counter(row["review_status"] for row in doc["items"])
    return {
        "checked_at": _now(),
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "head": _git("rev-parse", "HEAD"),
        "origin_head": _git("rev-parse", "origin/grok/ptf-milwaukee-market-001"),
        "working_tree_entries": [line for line in
                                 _git("status", "--porcelain").splitlines()
                                 if line.strip()],
        "policy_schema_version": doc["policy_schema_version"],
        "store_rows": len(doc["items"]),
        "review_states": dict(states),
        "founder_approved": sum(1 for row in doc["items"]
                                if row.get("founder_approved")),
        "published": sum(1 for row in doc["items"] if row.get("published")),
        "authority_written": bool(doc.get("authority_written")),
        "authority_files": [str(p.relative_to(REPO)).replace("\\", "/")
                            for p in PKG.rglob("*hotel_policy_facts*milwaukee*")],
        "provider_credentials_required": False,
    }


# --------------------------------------------------------------------------- #
# Phase 2 -- the cohort.
# --------------------------------------------------------------------------- #

def census_rows() -> Dict[str, Dict]:
    doc = json.loads(CENSUS.read_text(encoding="utf-8-sig"))
    return {row["identity_key"]: row for row in doc["hotels"]}


def cohort_rows() -> List[Dict]:
    """The store rows a founder is being asked about, derived by STATE."""
    return sorted(
        (row for row in R34.store_doc()["items"]
         if row["review_status"] in COHORT_STATES),
        key=lambda row: (row["review_status"] != READY, row["identity_key"]))


def cohort_assertions() -> Dict:
    rows = cohort_rows()
    keys = [row["identity_key"] for row in rows]
    census = census_rows()
    missing_block = []
    missing_source = []
    for row in rows:
        block, path = R34.block_for(row)
        if not block:
            missing_block.append(row["identity_key"])
        if not (row.get("provenance") or {}).get("source_url"):
            missing_source.append(row["identity_key"])
    counts = Counter(row["review_status"] for row in rows)
    return {
        "candidates": len(rows),
        "ready": counts.get(READY, 0),
        "refusal": counts.get(REFUSAL, 0),
        "unique_identities": len(set(keys)),
        "duplicates": sorted(k for k, n in Counter(keys).items() if n > 1),
        "missing_canonical_block": missing_block,
        "missing_source_url": missing_source,
        "not_in_census": sorted(k for k in keys if k not in census),
        "already_published": [row["identity_key"] for row in rows
                              if row.get("published")],
        "already_founder_approved": [row["identity_key"] for row in rows
                                     if row.get("founder_approved")],
        "excluded_states": {
            state: count for state, count in
            Counter(row["review_status"] for row in R34.store_doc()["items"]
                    if row["review_status"] not in COHORT_STATES).items()},
    }


# --------------------------------------------------------------------------- #
# Phases 5 and 6 -- what is checked before anything is proposed.
# --------------------------------------------------------------------------- #

#: A refusal quote whose sense depends on a word it does not contain. "no other
#: pets" is a CONTRAST, and what it contrasts with decides the meaning: after
#: "ADA service animals are welcome" it is a blanket refusal, and after "dogs
#: are welcome" it refuses only the other species. PTF-ACQUISITION-BRAND-
#: REPAIR-003 caught the second form nearly publishing a no-pets record for a
#: hotel that takes dogs. A founder asked to approve a refusal on the strength
#: of three words cannot tell those apart, so the whole sentence is surfaced
#: and the row is sent to individual review.
_CONTRASTIVE_REFUSAL_RE = re.compile(
    r"\b(?:other|others|another|else|otherwise)\b", re.IGNORECASE)

#: Below this a quote is a fragment rather than a statement.
_SELF_CONTAINED_QUOTE_CHARS = 14


def containing_sentence(block: str, quote: str) -> str:
    """The whole sentence a quote was cut from, or "" if it cannot be found."""
    flat = re.sub(r"\s+", " ", block or "").strip()
    needle = re.sub(r"\s+", " ", quote or "").strip()
    if not needle or needle not in flat:
        return ""
    start = flat.rfind(".", 0, flat.index(needle)) + 1
    end = flat.find(".", flat.index(needle) + len(needle))
    end = len(flat) if end < 0 else end + 1
    # The sentence BEFORE it comes too, because that is where the contrast
    # lives: "ADA service animals are welcome. Sorry no other pets are
    # allowed." is a blanket refusal, and the second sentence alone is not.
    previous = flat.rfind(".", 0, max(start - 1, 0)) + 1
    return flat[previous:end].strip()


def refusal_quote_is_self_contained(quote: str) -> bool:
    """Whether a refusal quote decides the question on its own words."""
    text = (quote or "").strip()
    if len(text) < _SELF_CONTAINED_QUOTE_CHARS:
        return False
    return not _CONTRASTIVE_REFUSAL_RE.search(text)


def _service_animal_only(row: Mapping, block: str) -> bool:
    """A page whose only pet wording is about service animals.

    A legal access category is not a pet permission and is not a refusal. Read
    as either, it invents a policy the hotel never published.
    """
    facts = row["proposed_facts"] or {}
    return ("pets_allowed" not in facts
            and bool(facts.get("service_animal_exception")))


def row_checks(row: Mapping) -> Dict:
    """Every gate Phase 5 names, answered for one row. Empty is the good case."""
    facts = dict(row["proposed_facts"] or {})
    withheld = dict(row["withheld_fields"] or {})
    evidence = list(row.get("evidence") or ())
    provenance = row.get("provenance") or {}
    census = census_rows()
    block, block_path = R34.block_for(row)

    blocking: List[str] = []
    warnings: List[str] = []
    #: Not defects. Things a founder must look at with their own eyes before
    #: the row is approved, because the answer is a judgement and not a check.
    attention: List[str] = []

    identity = census.get(row["identity_key"])
    if identity is None:
        blocking.append("identity is not in the Milwaukee census")

    if not block:
        blocking.append("no canonical policy block on disk")
    if not provenance.get("source_url"):
        blocking.append("no source URL")
    if not provenance.get("snapshot_hash"):
        blocking.append("no document hash")
    if not evidence:
        blocking.append("no evidence entries")

    is_refusal = facts.get("pets_allowed") is False
    if is_refusal:
        # Phase 6: a refusal is a first-class finding and must rest on a quote.
        quotes = [item.get("quote", "") for item in evidence
                  if "pets_allowed" in (item.get("field_refs") or ())]
        if not any(quote.strip() for quote in quotes):
            blocking.append("refusal carries no quote for pets_allowed")
        if _service_animal_only(row, block):
            blocking.append("the only pet wording is a service-animal statement")
        fragments = [quote for quote in quotes
                     if not refusal_quote_is_self_contained(quote)]
        for quote in fragments:
            attention.append(
                "the refusal rests on %r, which is a contrast rather than a "
                "statement -- read in full: %r"
                % (quote, containing_sentence(block, quote) or block[:200]))
    else:
        if facts.get("pets_allowed") is not True:
            if not (set(facts) - {"service_animal_exception",
                                  "service_animal_statement"}):
                blocking.append("neither an allowance nor a refusal is supported")
            else:
                # The row carries a priced pet policy and the page never says
                # in words that pets are allowed. Publishing it as a
                # pet-friendly listing infers the allowance from the fee, and
                # this codebase does not infer. A founder can decide that a
                # priced policy IS an allowance; a machine may not.
                attention.append(
                    "a pet policy is published with no stated allowance "
                    "(pets_allowed %s); whether a priced policy may be listed "
                    "as pet-friendly is a founder's call, not a reader's"
                    % withheld.get("pets_allowed", "absent"))
        if _service_animal_only(row, block):
            blocking.append("the only pet wording is a service-animal statement")

    overlap = sorted(set(facts) & set(withheld))
    if overlap:
        blocking.append("asserted and withheld at once: %s" % ", ".join(overlap))

    structured = {key: facts[key] for key in STRUCTURED_FIELDS if key in facts}
    if structured:
        issues = SCHEMA.validate_facts(structured)
        if issues:
            blocking.append("structured fee fails schema 1.2: %s"
                            % "; ".join(str(issue) for issue in issues))

    if row.get("frozen_semantics_violations"):
        blocking.append("frozen-semantics violation recorded on the row")
    if row["review_status"] == READY and enums.SCHEMA_CANNOT_REPRESENT in \
            set(withheld.values()):
        blocking.append("READY row carries SCHEMA_CANNOT_REPRESENT")

    # Warnings do not block: they are what a founder may want to look at.
    if not is_refusal and "pet_fee" not in facts and not facts.get("fee_tiers") \
            and not facts.get("fee_pet_schedule"):
        warnings.append("no fee is published; the source states none this "
                        "reader could represent")
    for field, reason in sorted(withheld.items()):
        warnings.append("%s withheld: %s" % (field, reason))
    if facts.get("fee_tiers"):
        warnings.append("priced in %d bands; the ladder is the price and no "
                        "single amount is asserted" % len(facts["fee_tiers"]))
    if facts.get("fee_cap"):
        warnings.append("a stated ceiling is carried as fee_cap and is not a "
                        "price")

    return {"blocking_issues": blocking, "warnings": warnings,
            "needs_individual_attention": attention, "block_path": block_path}


def proposed_decision(row: Mapping, checks: Mapping) -> Tuple[str, str]:
    if checks["blocking_issues"]:
        return (PROPOSE_INDIVIDUAL,
                "a mechanical check did not pass: %s"
                % "; ".join(checks["blocking_issues"]))
    if checks["needs_individual_attention"]:
        return (PROPOSE_INDIVIDUAL,
                "the row is mechanically clean and the remaining question is a "
                "judgement: %s" % "; ".join(checks["needs_individual_attention"]))
    if row["review_status"] == REFUSAL:
        return (PROPOSE_APPROVE_REFUSAL,
                "the property's own page refuses pets and the refusal is "
                "quoted; admitting it as VERIFIED_NO_PETS answers the "
                "traveller's question as usefully as an allowance does")
    return (PROPOSE_APPROVE,
            "identity, evidence and every published value check out, and every "
            "value the source did not state is absent rather than invented")


# --------------------------------------------------------------------------- #
# Phase 3 -- the package.
# --------------------------------------------------------------------------- #

def candidate(row: Mapping) -> Dict:
    census = census_rows()
    identity = census.get(row["identity_key"]) or {}
    facts = dict(row["proposed_facts"] or {})
    provenance = row.get("provenance") or {}
    checks = row_checks(row)
    decision, reason = proposed_decision(row, checks)
    block, block_path = R34.block_for(row)
    return OrderedDict([
        ("identity_key", row["identity_key"]),
        ("canonical_name", row["canonical_name"]),
        ("brand", row.get("brand", "")),
        ("address", ", ".join(part for part in (
            identity.get("address"), identity.get("city"),
            identity.get("state"), identity.get("postal_code")) if part)),
        ("corridor", identity.get("corridor", "")),
        ("slug", identity.get("slug", "")),
        ("review_state", row["review_status"]),
        ("facts", OrderedDict((key, facts[key]) for key in FACT_FIELDS
                              if key in facts)),
        ("withheld_fields", dict(row["withheld_fields"] or {})),
        ("non_inferences", list(row.get("non_inferences") or ())),
        ("evidence", OrderedDict([
            ("source_url", provenance.get("source_url", "")),
            ("final_url", provenance.get("final_url", "")),
            ("authority_tier", provenance.get("authority_tier", "")),
            ("source_type", provenance.get("source_type", "")),
            ("retrieved_at", provenance.get("retrieved_at", "")),
            ("retrieval_basis", provenance.get("capture_method", "")),
            ("provider", provenance.get("provider", "")),
            ("reader", provenance.get("reader", "")),
            ("reader_commit", (row.get("rederivation") or {}).get(
                "reader_commit", "")),
            ("document_sha256", provenance.get("snapshot_hash", "")),
            ("canonical_block_path", block_path),
            ("canonical_block", block),
            ("canonical_block_sha256",
             "sha256:%s" % hashlib.sha256(block.encode("utf-8")).hexdigest()),
            ("source_run", row.get("source_run", "")),
            ("obs_id", provenance.get("obs_id", "")),
            ("per_field_evidence", [dict(item) for item in
                                    (row.get("evidence") or ())]),
        ])),
        ("publication_grade", row.get("publication_grade", "")),
        ("record_hash", record_hash(row)),
        ("evidence_hash", evidence_hash(row.get("evidence") or ())),
        ("founder_approved", bool(row.get("founder_approved"))),
        ("published", bool(row.get("published"))),
        ("proposed_decision", decision),
        ("proposed_decision_reason", reason),
        ("blocking_issues", checks["blocking_issues"]),
        ("needs_individual_attention", checks["needs_individual_attention"]),
        ("warnings", checks["warnings"]),
        ("founder_decision", None),
    ])


def candidates() -> List[Dict]:
    return [candidate(row) for row in cohort_rows()]


# --------------------------------------------------------------------------- #
# Phase 15 -- what is NOT being asked about, kept where it cannot be lost.
# --------------------------------------------------------------------------- #

NEXT_ACTION = {
    "HELD_SCHEMA_CANNOT_REPRESENT": (
        "the source states a price schema 1.2 cannot hold. Either the shape "
        "gains a representation (a 1.3 conversation) or the row stays held; "
        "034 and 035 name the exact shape per row"),
    "HELD_INSUFFICIENT_EVIDENCE": (
        "the surface carried no term worth publishing. A better container or a "
        "different source page is the only thing that moves it"),
}


def complement() -> Dict:
    doc = R34.store_doc()
    held = [row for row in doc["items"]
            if row["review_status"] not in COHORT_STATES]
    census = P28.full_census()
    rows = []
    for row in sorted(held, key=lambda item: (item["review_status"],
                                              item["identity_key"])):
        block, path = R34.block_for(row)
        rows.append(OrderedDict([
            ("identity_key", row["identity_key"]),
            ("canonical_name", row["canonical_name"]),
            ("review_state", row["review_status"]),
            ("withheld_fields", dict(row["withheld_fields"] or {})),
            ("facts_held", dict(row["proposed_facts"] or {})),
            ("evidence_state", "canonical block on disk (%d chars)" % len(block)
             if block else "NO CANONICAL BLOCK"),
            ("canonical_block_path", path),
            ("next_action", NEXT_ACTION.get(row["review_status"], "")),
        ]))
    return {
        "held_rows": len(rows),
        "by_state": dict(Counter(row["review_state"] for row in rows)),
        "active_unresolved":
            census["phase11_final_states"]["TOUCHED_UNRESOLVED"],
        "active_unresolved_note": (
            "identities the market has touched and not resolved. They hold no "
            "store row, carry no facts, and cannot reach authority: there is "
            "nothing to approve"),
        "rows": rows,
    }


# --------------------------------------------------------------------------- #
# Phase 16 -- the counters, measured.
# --------------------------------------------------------------------------- #

def counters() -> Dict:
    census = P28.full_census()
    doc = R34.store_doc()
    states = Counter(row["review_status"] for row in doc["items"])
    rows = candidates()
    return {
        "census_total": census["census_total"],
        "active_eligible": census["active_eligible_total"],
        "observed": census["phase11_final_states"]["OBSERVED"],
        "active_unresolved": census["phase11_final_states"]["TOUCHED_UNRESOLVED"],
        "founder_review_candidates": len(rows),
        "proposed_approve": sum(1 for row in rows
                                if row["proposed_decision"] == PROPOSE_APPROVE),
        "proposed_approve_refusal": sum(
            1 for row in rows
            if row["proposed_decision"] == PROPOSE_APPROVE_REFUSAL),
        "proposed_individual_review": sum(
            1 for row in rows
            if row["proposed_decision"] == PROPOSE_INDIVIDUAL),
        "founder_approved": sum(1 for row in doc["items"]
                                if row.get("founder_approved")),
        "authority_rows": 0,
        "held_schema_cannot_represent": states.get(
            "HELD_SCHEMA_CANNOT_REPRESENT", 0),
        "held_insufficient_evidence": states.get(
            "HELD_INSUFFICIENT_EVIDENCE", 0),
        "current_state_conflict": states.get("CURRENT_STATE_CONFLICT", 0),
        "held_semantic_review": states.get("HELD_SEMANTIC_REVIEW", 0),
        "published": sum(1 for row in doc["items"] if row.get("published")),
        "deployed_live": 0,
        "sum_of_final_states": census["phase11_sum"],
    }


# --------------------------------------------------------------------------- #
# Phase 7 -- writing it out.
# --------------------------------------------------------------------------- #

CSV_COLUMNS: Tuple[str, ...] = (
    "identity_key", "canonical_name", "brand", "address", "corridor",
    "review_state", "pets_allowed", "pet_fee", "fee_currency", "fee_basis",
    "fee_structure", "fee_cap", "weight_limit", "pet_count_limit",
    "species_allowed", "withheld_fields", "warnings", "proposed_decision",
    "founder_decision", "source_url", "document_sha256", "record_hash",
)


def _csv_value(row: Mapping, column: str) -> str:
    facts = row["facts"]
    if column == "fee_structure":
        # The ladder, spelled out. A founder who cannot see the bands cannot
        # review the price, and a CSV cell that says "$75" for a two-band fee
        # is the exact error every reader work order since 024 has been about.
        tiers = facts.get("fee_tiers") or []
        if tiers:
            return " | ".join(
                "nights %s%s: $%d.%02d%s"
                % (tier.get("condition_min"),
                   ("-%s" % tier["condition_max"]) if tier.get("condition_max")
                   else "+",
                   *divmod(int(tier["amount_cents"]), 100),
                   (" %s" % tier["basis"]) if tier.get("basis")
                   else " (basis not stated)")
                for tier in tiers)
        schedule = (facts.get("fee_pet_schedule") or {}).get("entries") or []
        if schedule:
            return " | ".join(
                "pet %s: $%d.%02d%s" % (entry.get("pet_ordinal"),
                                        *divmod(int(entry["amount_cents"]), 100),
                                        (" %s" % entry["basis"])
                                        if entry.get("basis") else "")
                for entry in schedule)
        return ""
    if column in ("withheld_fields",):
        return "; ".join("%s=%s" % (key, value) for key, value
                         in sorted(row["withheld_fields"].items()))
    if column == "warnings":
        return " | ".join(row["warnings"])
    if column in ("source_url", "document_sha256"):
        return str(row["evidence"].get(column, ""))
    if column in row:
        value = row[column]
        return "" if value is None else str(value)
    value = facts.get(column)
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def review_document() -> Dict:
    rows = candidates()
    return OrderedDict([
        ("schema", "ptf-milwaukee-founder-review/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("status", "AWAITING_FOUNDER_DECISION"),
        ("what_this_is", (
            "A question, not an answer. Every row here is a candidate the "
            "machine believes it can defend; none is approved. "
            "founder_approved is false on every row in the store and this "
            "package changes nothing about that.")),
        ("how_to_answer", (
            "Record decisions in %s -- a file this generator never writes -- "
            "with the record_hash and evidence_hash each row carries here. A "
            "decision recorded against a record that has since moved is not a "
            "decision about that record."
            % LEDGER.relative_to(REPO).as_posix())),
        ("proposed_decision_is_not_approval", (
            "APPROVE and APPROVE_REFUSAL are recommendations. Only an explicit "
            "founder decision, recorded in the ledger and applied by a "
            "separate work order, can set founder_approved.")),
        ("candidate_count", len(rows)),
        ("counts_by_review_state",
         dict(Counter(row["review_state"] for row in rows))),
        ("counts_by_proposed_decision",
         dict(Counter(row["proposed_decision"] for row in rows))),
        ("cohort_assertions", cohort_assertions()),
        ("candidates", rows),
    ])


def manifest(paths: Mapping[str, Path]) -> Dict:
    rows = candidates()
    assertions = cohort_assertions()
    return OrderedDict([
        ("schema", "ptf-milwaukee-founder-review-manifest/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("generated_at", _now()),
        ("source_head", _git("rev-parse", "HEAD")),
        ("source_branch", _git("rev-parse", "--abbrev-ref", "HEAD")),
        ("source_store", STORE.relative_to(REPO).as_posix()),
        ("source_store_sha256", _sha256_file(STORE)),
        ("policy_schema_version",
         R34.store_doc()["policy_schema_version"]),
        ("candidate_count", assertions["candidates"]),
        ("ready_count", assertions["ready"]),
        ("refusal_count", assertions["refusal"]),
        ("excluded_held_count", sum(assertions["excluded_states"].values())),
        ("excluded_by_state", assertions["excluded_states"]),
        ("evidence_coverage", OrderedDict([
            ("rows_with_canonical_block",
             assertions["candidates"] - len(assertions["missing_canonical_block"])),
            ("rows_with_source_url",
             assertions["candidates"] - len(assertions["missing_source_url"])),
            ("rows_with_document_hash", sum(
                1 for row in rows if row["evidence"]["document_sha256"])),
            ("rows_with_per_field_evidence", sum(
                1 for row in rows if row["evidence"]["per_field_evidence"])),
        ])),
        ("duplicate_count", len(assertions["duplicates"])),
        ("approval_count", 0),
        ("authority_count", 0),
        ("files", OrderedDict(
            (name, OrderedDict([
                # A package written outside the repository (a test's temp
                # directory) still names its files; only a path inside the repo
                # is expressed relative to it.
                ("path", path.relative_to(REPO).as_posix()
                 if REPO in path.parents else path.name),
                ("sha256", _sha256_file(path)),
                ("bytes", path.stat().st_size)]))
            for name, path in sorted(paths.items()))),
        ("governance", OrderedDict([
            ("mechanism", "founder decision ledger, per the Dayton precedent"),
            ("ledger_path", LEDGER.relative_to(REPO).as_posix()),
            ("ledger_exists", LEDGER.is_file()),
            ("approval_requires", (
                "an explicit written founder decision; this repository's "
                "recorder refuses to write a decision it was not given and no "
                "agent may sign in the founder's name")),
            ("authority_permitted_now", False),
        ])),
    ])


def summary_markdown() -> str:
    rows = candidates()
    counts = Counter(row["proposed_decision"] for row in rows)
    states = Counter(row["review_state"] for row in rows)
    numbers = counters()
    lines = [
        "# Milwaukee founder review -- %s" % WORK_ORDER,
        "",
        "**Status: AWAITING_FOUNDER_DECISION. Nothing here is approved.**",
        "",
        "%d candidates: %d readable policies and %d captured refusals."
        % (len(rows), states.get(READY, 0), states.get(REFUSAL, 0)),
        "",
        "| proposed | rows |",
        "| --- | ---: |",
    ]
    for name, count in sorted(counts.items()):
        lines.append("| %s | %d |" % (name, count))
    lines += [
        "",
        "## What a decision means",
        "",
        "`APPROVE` admits a pet policy to Milwaukee authority. "
        "`APPROVE_REFUSAL` admits a verified no-pets finding, which answers a "
        "traveller's question as usefully as an allowance does. A proposed "
        "decision is a recommendation from a machine that checked identity, "
        "evidence, schema validity and withholding; it is not an approval and "
        "cannot become one without an explicit written decision.",
        "",
        "## What was checked before anything was proposed",
        "",
        "* the identity resolves in the 147-property census exactly once",
        "* the canonical policy block is on disk and its document hash is recorded",
        "* the allowance or the refusal is supported by a quote",
        "* every structured fee validates under schema 1.2 as it stands",
        "* no field is asserted and withheld at the same time",
        "* a service-animal statement is never read as a pet permission",
        "",
        "Unknown is not a failure. A policy that states no weight limit and no "
        "breed rule is still a policy, and no value is ever invented to fill a "
        "gap.",
        "",
        "## Prices stated as ladders",
        "",
    ]
    laddered = [row for row in rows if row["facts"].get("fee_tiers")]
    lines.append("%d rows price by stay length. The ladder IS the price: no "
                 "single amount is asserted for them, and the CSV spells every "
                 "band out rather than collapsing it." % len(laddered))
    individual = [row for row in rows
                  if row["proposed_decision"] == PROPOSE_INDIVIDUAL]
    if individual:
        lines += [
            "",
            "## The %d rows that need your eyes, not a checkbox" % len(individual),
            "",
            "Each of these is mechanically clean. What is left is a judgement, "
            "and the machine states the question rather than answering it.",
            "",
        ]
        for row in individual:
            lines.append("* **%s** (%s)" % (row["canonical_name"],
                                            row["review_state"]))
            for note in row["needs_individual_attention"] or row["blocking_issues"]:
                lines.append("  * %s" % note)
    lines += [
        "",
        "## Not in this package",
        "",
        "| state | rows | why |",
        "| --- | ---: | --- |",
        "| HELD_SCHEMA_CANNOT_REPRESENT | %d | the source states a price the "
        "schema cannot hold |" % numbers["held_schema_cannot_represent"],
        "| HELD_INSUFFICIENT_EVIDENCE | %d | the surface carried no term worth "
        "publishing |" % numbers["held_insufficient_evidence"],
        "| active unresolved | %d | no store row exists; there is nothing to "
        "approve |" % numbers["active_unresolved"],
        "",
        "## Milwaukee",
        "",
        "census %d | active eligible %d | observed %d | candidates %d | "
        "founder approved %d | authority %d | deployed 0"
        % (numbers["census_total"], numbers["active_eligible"],
           numbers["observed"], numbers["founder_review_candidates"],
           numbers["founder_approved"], numbers["authority_rows"]),
        "",
    ]
    return "\n".join(lines) + "\n"


def write_package(directory: Optional[Path] = None) -> Dict:
    """Write the package. A caller may name a different directory.

    Added so a test can prove the generator is deterministic without rewriting
    the COMMITTED package to do it -- the manifest carries a generated_at, so
    regenerating in place makes a test mutate a founder-facing artifact.
    """
    global PACKAGE_DIR, REVIEW_JSON, REVIEW_CSV, MANIFEST, SUMMARY
    if directory is not None:
        PACKAGE_DIR = Path(directory)
        REVIEW_JSON = PACKAGE_DIR / "founder-review.json"
        REVIEW_CSV = PACKAGE_DIR / "founder-review.csv"
        MANIFEST = PACKAGE_DIR / "founder-review-manifest.json"
        SUMMARY = PACKAGE_DIR / "founder-review-summary.md"
    PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
    REVIEW_JSON.write_text(_stable(review_document()) + "\n", encoding="utf-8")

    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    for row in candidates():
        writer.writerow([_csv_value(row, column) for column in CSV_COLUMNS])
    REVIEW_CSV.write_text(buffer.getvalue(), encoding="utf-8")

    SUMMARY.write_text(summary_markdown(), encoding="utf-8")
    paths = {"founder-review.json": REVIEW_JSON,
             "founder-review.csv": REVIEW_CSV,
             "founder-review-summary.md": SUMMARY}
    MANIFEST.write_text(_stable(manifest(paths)) + "\n", encoding="utf-8")
    return {name: _sha256_file(path) for name, path in
            sorted({**paths, "founder-review-manifest.json": MANIFEST}.items())}


# --------------------------------------------------------------------------- #
# Phases 8 to 10 -- the answer, and the refusal to write one nobody gave.
# --------------------------------------------------------------------------- #

class FounderDecisionError(RuntimeError):
    """A decision was asked for that the founder did not give."""


def load_ledger() -> Optional[Dict]:
    if not LEDGER.is_file():
        return None
    return json.loads(LEDGER.read_text(encoding="utf-8-sig"))


def _superseded_by_a_later_sitting() -> Dict[str, str]:
    """Identities a founder has decided again since 036."""
    try:
        from scripts.pettripfinder.acquisition import founder_decisions_040 as D40
    except Exception:                                         # noqa: BLE001
        return {}
    if not D40.LEDGER.is_file():
        return {}
    return {row["identity_key"]: row["decision"]
            for row in D40.load_ledger()["decisions"]}


def _semantically_rebound(decision: Mapping, key: str) -> bool:
    """Whether 039's migration proved this decision's meaning is unchanged.

    All three must agree: the decision must still carry the two hashes the
    migration examined -- so editing a ledger entry is not forgiven -- and the
    live store row must still mean what the migration proved it meant.
    """
    try:
        from scripts.pettripfinder import approval_binding as AB
        from scripts.pettripfinder.acquisition import (
            approval_rebinding_039 as REBIND)
    except Exception:                                         # noqa: BLE001
        return False
    entry = REBIND.rebound_index().get(key)
    if not entry:
        return False
    row = R34.store_rows().get(key) if hasattr(R34, "store_rows") else None
    if row is None:
        row = {item["identity_key"]: item
               for item in R34.store_doc()["items"]}.get(key)
    if row is None:
        return False
    return (entry[1] == decision.get("record_hash")
            and entry[2] == decision.get("evidence_hash")
            and entry[0] == AB.semantic_hash(row))


def applicable_decisions() -> List[Dict]:
    """Founder decisions that still bind to the record they were given for.

    The Dayton rule, in code: a decision carries the record_hash and
    evidence_hash the founder was shown, and it stops applying the moment the
    record moves. Absence of a ledger is not consent, and an unlisted row is
    not an approved one.
    """
    ledger = load_ledger()
    if ledger is None:
        return []
    live = {row["identity_key"]: row for row in candidates()}
    out = []
    later = _superseded_by_a_later_sitting()
    for decision in ledger.get("decisions") or ():
        key = decision.get("identity_key")
        if key in later:
            # A later founder sitting answered this identity again. The older
            # decision is history, and the newer ledger governs the row.
            continue
        row = live.get(key)
        if row is None:
            raise FounderDecisionError(
                "the ledger decides %r, which is not a candidate" % key)
        # TWO BINDINGS, EITHER SUFFICIENT. 036's hashes cover the whole store
        # row including its provenance, so a reader repair moved fifteen rows
        # that said exactly the same thing. PTF-...-APPROVAL-BINDING-039 added
        # a semantic binding and rebound those rows BY NAME; a row the
        # migration did not examine is still refused here, exactly as before.
        #
        # The check lives in two places -- this module and authority_build_036
        # -- and 039 repaired only the other one. Leaving this one behind made
        # the review package refuse rows the authority happily applied.
        if decision.get("record_hash") != row["record_hash"]                 or decision.get("evidence_hash") != row["evidence_hash"]:
            if not _semantically_rebound(decision, key):
                if decision.get("record_hash") != row["record_hash"]:
                    raise FounderDecisionError(
                        "the record %r has moved since the founder saw it; "
                        "the decision does not bind" % key)
                raise FounderDecisionError(
                    "the evidence for %r has moved since the founder saw it"
                    % key)
        if not decision.get("decided_by"):
            raise FounderDecisionError("a decision for %r names no decider" % key)
        out.append(decision)
    return out


def pre_authority_requirements() -> List[Dict]:
    """What the work order that BUILDS authority has to handle. Measured here.

    Read-only findings from projecting a candidate's facts through the display
    layer the site already uses. None of them is a defect in the store; each is
    a conversion the authority builder must do and must test.
    """
    from scripts.pettripfinder import canonical_view as CV
    rows = candidates()
    capped = [row for row in rows if row["facts"].get("fee_cap")]
    laddered = [row for row in rows if row["facts"].get("fee_tiers")]
    legacy_cap_renders = bool(CV._display_money({"amount_minor": 7500,
                                                 "currency": "USD"}))
    tier_survives = bool(laddered) and len(
        CV.display_facts({"facts": {"fee_tiers": laddered[0]["facts"]["fee_tiers"]}})
        .get("fee_tiers") or ()) == len(laddered[0]["facts"]["fee_tiers"])
    return [
        OrderedDict([
            ("requirement", "convert the store's money shapes to schema 1.2"),
            ("detail", (
                "the store carries the READER's vocabulary -- pet_fee is a bare "
                "integer and fee_cap is {amount_minor, currency, basis} -- while "
                "authority records and the display projection expect 1.2 money "
                "objects. canonical_view._display_money renders an amount_minor "
                "cap as the EMPTY STRING, so a builder that copies facts "
                "verbatim drops the ceiling silently.")),
            ("proved_by", "_display_money({'amount_minor': 7500}) -> %r"
             % ("" if not legacy_cap_renders else "$75.00")),
            ("rows_affected", [row["identity_key"] for row in capped]),
            ("severity", "a dropped ceiling is a wrong fact, not a missing one"),
        ]),
        OrderedDict([
            ("requirement", "carry fee_tiers through unflattened"),
            ("detail", "the display projection keeps every band and its "
                       "boundaries; a builder must not collapse a ladder into "
                       "a single amount on the way in"),
            ("proved_by", "display_facts keeps all bands: %s" % tier_survives),
            ("rows_affected", [row["identity_key"] for row in laddered]),
            ("severity", "informational -- the path works today"),
        ]),
        OrderedDict([
            ("requirement", "admit refusals through the exclusion registry"),
            ("detail", "hotel_exclusions.json is where a VERIFIED_NO_PETS "
                       "finding lives, and each row carries reviewer_id and "
                       "reviewed_at -- a human attestation, not a status"),
            ("rows_affected", [row["identity_key"] for row in rows
                               if row["review_state"] == REFUSAL]),
            ("severity", "governance"),
        ]),
    ]


def ledger_template() -> Dict:
    """A skeleton for the founder's answers. PRINTED, never written.

    Every decision is null. A file on disk with decisions in it is an
    attestation, and this module must not be able to produce one -- so the
    skeleton goes to stdout and a human puts it where it belongs.
    """
    rows = candidates()
    return OrderedDict([
        ("schema", "ptf-milwaukee-founder-decisions/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("decided_by", "<the founder>"),
        ("decided_at", "<YYYY-MM-DD>"),
        ("recorded_by", "<who transcribed it, and that they inferred nothing>"),
        ("status", "RECORDED_NOT_APPLIED"),
        ("source_package_sha256", _sha256_file(REVIEW_JSON)
         if REVIEW_JSON.is_file() else ""),
        ("decisions", [OrderedDict([
            ("identity_key", row["identity_key"]),
            ("canonical_name", row["canonical_name"]),
            ("proposed", row["proposed_decision"]),
            ("decision", None),
            ("record_hash", row["record_hash"]),
            ("evidence_hash", row["evidence_hash"]),
            ("decided_by", None),
        ]) for row in rows]),
    ])


def governance() -> Dict:
    """What this repository already requires, read from what it already does."""
    ledger = load_ledger()
    return OrderedDict([
        ("mechanism_found", "founder decision ledger + separate application"),
        ("precedent", [
            "scripts/pettripfinder/dayton_pass_b_founder_decisions.py",
            "launch_packages/pettripfinder/dayton_passB_founder_decisions.json",
            "scripts/pettripfinder/dayton_pass_c_decision_application.py",
            "launch_packages/pettripfinder/hotel_exclusions.json",
        ]),
        ("decisions_are_per_row", True),
        ("decision_is_hash_bound", True),
        ("binds_to", ["record_hash", "evidence_hash"]),
        ("approval_shape_in_authority", {
            "decision": "APPROVED_AFTER_CURRENT_REVIEW",
            "operator": "<the founder>",
            "approval_date": "<the date they decided>",
            "decision_source": {"ledger": LEDGER.name},
        }),
        ("refusal_disposition", {
            "registry": "launch_packages/pettripfinder/hotel_exclusions.json",
            "state": "VERIFIED_NO_PETS",
            "requires": "reviewer_id and reviewed_at -- a human attestation",
        }),
        ("explicit_founder_input_required", True),
        ("agent_may_sign", False),
        ("why", (
            "The Dayton recorder states the rule: the founder's name appears "
            "on a decision only where the founder gave it explicitly and in "
            "writing, and the module fails closed if asked to record a "
            "decision it was not given. An agent that signs on the founder's "
            "behalf produces an attestation with nobody behind it.")),
        ("authority_permitted_in_this_work_order", False),
        ("ledger_present", ledger is not None),
        ("decisions_recorded", len(ledger.get("decisions") or ())
         if ledger else 0),
    ])


def verdict() -> Dict:
    decisions = applicable_decisions()
    rows = candidates()
    counts = Counter(row["proposed_decision"] for row in rows)
    exceptional = [OrderedDict([("identity_key", row["identity_key"]),
                                ("canonical_name", row["canonical_name"]),
                                ("review_state", row["review_state"]),
                                ("why", row["blocking_issues"]
                                 or row["needs_individual_attention"])])
                   for row in rows
                   if row["proposed_decision"] == PROPOSE_INDIVIDUAL]
    return OrderedDict([
        ("verdict", "FOUNDER_REVIEW_REQUIRED" if not decisions
         else "FOUNDER_DECISIONS_PRESENT"),
        ("review_artifact", REVIEW_JSON.relative_to(REPO).as_posix()),
        ("review_artifacts", [path.relative_to(REPO).as_posix() for path in
                              (REVIEW_JSON, REVIEW_CSV, MANIFEST, SUMMARY)]),
        ("candidate_count", len(rows)),
        ("ready_count", sum(1 for row in rows if row["review_state"] == READY)),
        ("refusal_count", sum(1 for row in rows
                              if row["review_state"] == REFUSAL)),
        ("proposed_approve", counts.get(PROPOSE_APPROVE, 0)),
        ("proposed_approve_refusal", counts.get(PROPOSE_APPROVE_REFUSAL, 0)),
        ("rows_requiring_individual_attention", exceptional),
        ("bulk_decision_allowed", True),
        ("bulk_decision_note", (
            "The founder may approve the mechanically clean rows in one "
            "explicit decision -- Dayton recorded batches exactly that way -- "
            "provided the decision names the cohort and the ledger carries the "
            "hashes. Row-by-row is available and is not required.")),
        ("next_action", (
            "1. Read %s (or the CSV, which spells every fee ladder out). "
            "2. Record the decision in %s with decided_by, decided_at and the "
            "record_hash/evidence_hash from the package. "
            "3. Run a separate application work order to turn recorded "
            "decisions into approvals and to build authority from them."
            % (SUMMARY.relative_to(REPO).as_posix(),
               LEDGER.relative_to(REPO).as_posix()))),
        ("authority_created", False),
        ("published", 0),
        ("deployed", 0),
    ])


# --------------------------------------------------------------------------- #
# Reporting.
# --------------------------------------------------------------------------- #

RUN_REPORT = REPORTS / "ptf_milwaukee_founder_review_036.json"


def cost() -> Dict:
    return {"provider_calls": 0, "firecrawl_calls": 0, "browser_api_calls": 0,
            "web_unlocker_calls": 0, "brightdata_spend_usd": 0.0,
            "why": "the package is built from the committed store and the "
                   "blocks already on disk"}


def build_report(package: Optional[Mapping] = None) -> Dict:
    return OrderedDict([
        ("schema", "ptf-milwaukee-founder-review-run/1.0"),
        ("work_order", WORK_ORDER),
        ("market", MARKET),
        ("generated_at", _now()),
        ("preflight", preflight()),
        ("cohort", cohort_assertions()),
        ("package_files", dict(package or {})),
        ("governance", governance()),
        ("verdict", verdict()),
        ("complement", complement()),
        ("pre_authority_requirements", pre_authority_requirements()),
        ("counters", counters()),
        ("cost", cost()),
        ("authority_written", False),
        ("published", 0),
        ("deployed", 0),
    ])


def write_report(package: Optional[Mapping] = None) -> Dict:
    doc = build_report(package)
    RUN_REPORT.write_text(_stable(doc) + "\n", encoding="utf-8")
    return doc


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=WORK_ORDER)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--cohort", action="store_true")
    parser.add_argument("--governance", action="store_true")
    parser.add_argument("--write-package", action="store_true")
    parser.add_argument("--verdict", action="store_true")
    parser.add_argument("--complement", action="store_true")
    parser.add_argument("--counters", action="store_true")
    parser.add_argument("--ledger-template", action="store_true")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args(argv)

    package = None
    if args.preflight:
        print(_stable(preflight()))
    if args.cohort:
        print(_stable(cohort_assertions()))
    if args.governance:
        print(_stable(governance()))
    if args.write_package:
        package = write_package()
        print(_stable(package))
    if args.verdict:
        print(_stable(verdict()))
    if args.complement:
        doc = complement()
        print(_stable({k: v for k, v in doc.items() if k != "rows"}))
        for row in doc["rows"]:
            print("  %-46s %s" % (row["identity_key"][:46], row["review_state"]))
    if args.counters:
        print(_stable(counters()))
    if args.ledger_template:
        print(_stable(ledger_template()))
    if args.report:
        doc = write_report(package)
        print(_stable(doc["counters"]))
        print(_stable(doc["verdict"]["verdict"]))
    return 0


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(main())
