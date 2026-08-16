"""PTF-CLEVELAND-LIGHT-RECERTIFICATION-001 -- Pass 1 governance closeout.

Applies the founder's recorded decisions of 2026-08-15 to the Pass-1 state:

* Re-attests the 19 artifact-upgraded records. Pass 1 moved their record_hash
  (entry-level artifact bindings) and, per the migration rule, downgraded each
  approval to machine-reviewed-pending-operator rather than re-signing it. The
  founder has now approved exactly those records, against exactly those hashes.
  The STOP rule is mechanical: if any record's recomputed hash no longer equals
  the hash its Pass-1 pending block recorded -- the hash the founder was shown
  -- that record is NOT re-bound and the run refuses.
* Applies the two APPROVED fact additions (The Westin's leash rule, Hotel
  Indigo Cleveland-Beachwood's vaccination-records requirement), each as
  ``general_restrictions`` -- the schema's verbatim-grounded prose field --
  quoted exactly, cited to the same hash-verified capture artifact Pass 1
  bound, and re-asserted contiguous in that capture's page text when the
  worker tree is reachable.
* Records the five KEEP_AS_IS decisions and the Middleburg Heights
  census-hygiene proposal in the committed review packet. The census itself is
  NOT touched: no contract authorises a mechanical census correction, so the
  correction is prepared, evidenced, and left for census work.

The founder's approval blocks are written only because the founder gave those
decisions in this work order's instruction; nothing here invents one. The two
Drury records are untouched: their approvals never moved.

Run:
  python -m scripts.pettripfinder.cleveland_pass1_governance_closeout \
      [--data-root PATH] [--apply]
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.contracts import enums                            # noqa: E402
from scripts.pettripfinder.contracts import evidence as evidence_contract    # noqa: E402
from scripts.pettripfinder.policy_migration import (                         # noqa: E402
    evidence_hash, evidence_ref_for, record_hash,
)

MARKET = "cleveland-akron-canton-oh"
WORK_ORDER = "PTF-CLEVELAND-LIGHT-RECERTIFICATION-001"
DECISION_DATE = "2026-08-15"
FOUNDER = "jfields80"
PASS1_AGENT = "claude-fable-5 (%s, agent)" % WORK_ORDER

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
FACTS_PATH = LP / ("hotel_policy_facts_%s.json" % MARKET)
PACKET_PATH = LP / "cleveland_pass1_founder_review_packet.json"
REPORT_PATH = LP / "cleveland_artifact_verification_001.json"
DECISIONS_PATH = LP / "policy_migration_decisions.json"
CONTRACT_PATH = (_REPO_ROOT / "deploy" / "netlify" / "release_contracts"
                 / ("%s.json" % MARKET))

DRURY_KEYS = frozenset({"drury inn and suites beachwood", "drury plaza hotel"})

#: The two founder-APPROVED additions, verbatim from the review packet the
#: founder ruled on. Both sentences already sit inside the record's committed
#: evidence_quote; the entry cites the same capture artifact as every other
#: entry on the record.
APPROVED_ADDITIONS: Dict[str, str] = {
    "the westin": "Leashed or caged in public areas, fee applies",
    "hotel indigo cleveland beachwood":
        "Required vaccination records showing up to date rabies, distemper, "
        "parvovirus and bordetella",
}

#: Founder rulings for the review packet, recorded verbatim so the packet is
#: its own decision ledger.
PACKET_DECISIONS: Dict[int, Dict[str, str]] = {
    1: {"decision": "APPROVE_CHANGE"},
    2: {"decision": "APPROVE_CHANGE"},
    3: {"decision": "KEEP_AS_IS",
        "reason": "The phrase is not sufficiently clear to establish a "
                  "standalone service-animal policy statement beyond the "
                  "current species/context interpretation."},
    4: {"decision": "KEEP_AS_IS",
        "reason": "weight_limit.scope=per_pet is an interpretation convention "
                  "rather than explicitly quoted wording; kept, not "
                  "restructured to combined."},
    5: {"decision": "KEEP_AS_IS",
        "reason": "scope is convention-supported rather than explicitly "
                  "stated; no combined ceiling is inferred."},
    6: {"decision": "KEEP_AS_IS",
        "reason": "scope is convention-supported rather than explicitly "
                  "stated; no combined ceiling is inferred."},
    7: {"decision": "KEEP_AS_IS",
        "reason": "scope is convention-supported rather than explicitly "
                  "stated; no combined ceiling is inferred."},
}

CENSUS_HYGIENE = OrderedDict([
    ("classification", "CENSUS_HYGIENE_REVIEW_REQUIRED"),
    ("identity_key", "residence inn cleveland airport middleburg heights"),
    ("field", "phone"),
    ("census_value", "440.637.5856"),
    ("proposed_value", "440.638.5856"),
    ("first_party_evidence",
     "The property's own JSON-LD, read off the rendered page by the verified "
     "capture (artifact sha256:1c531a3a... per "
     "cleveland_artifact_verification_001.json), states +14406385856. "
     "Identity remains bound through street number 19149, ZIP 44130, the "
     "property name, and Marriott property code clemb in the final URL."),
    ("status", "PROPOSED_NOT_APPLIED"),
    ("why_not_applied",
     "No identity/census contract authorises a mechanical phone correction; "
     "census corrections travel through their own reviewed work order. Not a "
     "policy-recertification blocker."),
])


def load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_lf(path: Path, document) -> bytes:
    """LF bytes, exactly as the repo stores them, so sha pins stay truthful."""
    payload = (json.dumps(document, indent=2, ensure_ascii=False) + "\n") \
        .encode("utf-8")
    path.write_bytes(payload)
    return payload


def _collapsed_contains(haystack: str, needle: str) -> bool:
    return " ".join(needle.split()) in " ".join(haystack.split())


def _capture_text(identity_key: str, data_root: Path) -> Optional[str]:
    """The captured page text for one factory record, if the tree is present."""
    batch = data_root / ("worker_runs/pettripfinder/discovery/review_batches/"
                         "cleveland-factory-001")
    try:
        proposal = load_json(batch / "proposed_cleveland_authority.json")
        manifest = load_json(batch / "evidence_manifest.json")
    except (OSError, ValueError):
        return None
    hotel_id = {r["listing_key"]: r["hotel_id"]
                for r in proposal["captured_pet_friendly"]}.get(identity_key)
    row = {r["hotel_id"]: r for r in manifest["artifacts"]}.get(hotel_id)
    if row is None:
        return None
    capture = load_json(
        data_root.parent / row["capture_json"]["path"].replace("\\", "/"))
    return capture.get("text") or ""


def apply_addition(hotel: Dict, quote: str,
                   data_root: Optional[Path]) -> None:
    """One founder-approved general_restrictions addition, verbatim."""
    key = hotel["identity_key"]
    if "general_restrictions" in hotel["facts"]:
        raise AssertionError("%s: general_restrictions already present" % key)
    if not _collapsed_contains(hotel["evidence_quote"], quote):
        raise AssertionError(
            "%s: approved quote is not inside the committed evidence_quote"
            % key)
    if data_root is not None:
        text = _capture_text(key, data_root)
        if text is not None and not evidence_contract.quote_is_contiguous(
                quote, text):
            raise AssertionError(
                "%s: approved quote is not contiguous in the captured page "
                "text" % key)

    template = hotel["evidence"][0]
    for required in ("artifact_sha256", "artifact_kind", "captured_at",
                     "capture_method", "source_grade"):
        if not template.get(required):
            raise AssertionError(
                "%s: sibling entries carry no publication-grade bindings to "
                "inherit" % key)
    entry = OrderedDict([
        ("field", "general_restrictions"),
        ("quote", quote),
        ("source_url", hotel["source_url"]),
        ("value", quote),
        ("evidence_ref", ""),
        ("artifact_class", enums.PUBLICATION_GRADE_EVIDENCE),
        ("artifact_sha256", template["artifact_sha256"]),
        ("artifact_kind", template["artifact_kind"]),
        ("captured_at", template["captured_at"]),
        ("capture_method", template["capture_method"]),
        ("source_grade", template["source_grade"]),
    ])
    entry["evidence_ref"] = evidence_ref_for(entry)
    hotel["evidence"].append(entry)
    # ``evidence_count`` is deliberately NOT updated: it is a legacy field the
    # canonical contract does not own, preserved verbatim from the pre-1.2
    # baseline (test_migration_kept_every_field_it_does_not_own). Consumers
    # count the evidence array; the frozen number is provenance, not state.

    # Facts carry the property's words, never a paraphrase of them.
    facts = OrderedDict(hotel["facts"])
    facts["general_restrictions"] = quote
    hotel["facts"] = facts


def attest(hotel: Dict, addition_applied: bool) -> None:
    """The founder's approval, bound to the FINAL corrected hashes.

    The superseded block is the last REAL approval (the one Pass 1 preserved),
    not the transient pending-operator state Pass 1 wrote between them: that
    state was a state, never an approval, and its full text remains in git
    history (aaab32f) and in cleveland_artifact_verification_001.json.
    """
    pending = hotel["approval"]
    prior = copy.deepcopy(pending.get("supersedes") or {})
    if not prior or prior.get("operator") != FOUNDER:
        raise AssertionError(
            "%s: expected the Pass-1 block to preserve a founder-signed "
            "approval under supersedes" % hotel["identity_key"])
    signed = {k: v for k, v in hotel.items() if k != "approval"}
    caveats = [
        "Founder decision, %s governance closeout, %s. Re-attested against "
        "THIS record_hash after Pass 1 bound every evidence entry to its "
        "hash-verified capture artifact: facts, quotes, evidence refs and "
        "evidence_hash were unchanged by that pass, the artifact bytes were "
        "independently re-hashed against the recorded manifests, property "
        "identity and quote contiguity were re-verified, and the public "
        "bundle stayed byte-identical. The approval under 'supersedes' is the "
        "prior real approval, preserved verbatim; the transient "
        "machine-reviewed state between it and this decision is recorded in "
        "git history (aaab32f), not in this chain." % (WORK_ORDER, DECISION_DATE),
    ]
    if addition_applied:
        caveats.append(
            "This attestation also covers the founder-APPROVED addition of "
            "general_restrictions, quoted verbatim from the record's own "
            "verified capture text; evidence_hash moved with that entry and "
            "the hashes below are the corrected record's.")
    hotel["approval"] = OrderedDict([
        ("decision", enums.APPROVED_AFTER_CURRENT_REVIEW),
        ("operator", FOUNDER),
        ("approval_date", DECISION_DATE),
        ("supersedes", prior),
        ("caveats", caveats),
        ("record_hash", record_hash(signed)),
        ("evidence_hash", evidence_hash(hotel["evidence"])),
    ])


def run(data_root: Optional[Path], apply: bool) -> Dict:
    facts = load_json(FACTS_PATH)
    stopped: List[str] = []
    attested: List[str] = []

    for hotel in facts["hotels"]:
        key = hotel["identity_key"]
        approval = hotel["approval"]
        current_hash = record_hash(hotel)
        if key in DRURY_KEYS:
            # Untouched by Pass 1; their human approvals must still bind.
            if approval["record_hash"] != current_hash or \
                    approval["decision"] != enums.APPROVED_AFTER_CURRENT_REVIEW:
                stopped.append("%s: Drury record moved since its approval" % key)
            continue
        # STOP rule: the hash the founder approved is the hash Pass 1 wrote
        # into the pending block. Any drift means the founder is re-binding a
        # record they were not shown -- refuse that record outright.
        if approval.get("decision") != enums.MACHINE_REVIEWED_PENDING_OPERATOR \
                or approval.get("operator") != PASS1_AGENT:
            stopped.append("%s: not in the Pass-1 pending state" % key)
            continue
        if approval.get("record_hash") != current_hash:
            stopped.append(
                "%s: record_hash drifted since Pass 1 (%s -> %s); NOT re-bound"
                % (key, str(approval.get("record_hash"))[7:23],
                   current_hash[7:23]))
            continue

        addition = APPROVED_ADDITIONS.get(key)
        if addition:
            apply_addition(hotel, addition, data_root)
        attest(hotel, addition_applied=bool(addition))
        issues = evidence_contract.validate(hotel)
        if issues:
            raise AssertionError("%s: fails the evidence contract after "
                                 "closeout: %s" % (key, issues))
        attested.append(key)

    if stopped:
        raise SystemExit("STOP: %d record(s) refused re-attestation:\n  %s"
                         % (len(stopped), "\n  ".join(stopped)))
    if len(attested) != 19:
        raise SystemExit("STOP: expected exactly 19 re-attestations, found %d"
                         % len(attested))

    # The three Class-B decisions-file entries record the hash the founder
    # approved against; the founder approved against the corrected hashes
    # today, so the ledger follows the signature -- never the reverse.
    decisions = load_json(DECISIONS_PATH)
    by_key = {h["identity_key"]: h for h in facts["hotels"]}
    ledger_updates = 0
    for record_key, entry in (decisions.get("records") or {}).items():
        market, _, identity = record_key.partition("|")
        if market != MARKET or not entry.get("founder_attested"):
            continue
        hotel = by_key[identity]
        entry["approved_record_hash"] = hotel["approval"]["record_hash"]
        entry["approved_evidence_hash"] = hotel["approval"]["evidence_hash"]
        entry["approval"] = copy.deepcopy(dict(hotel["approval"]))
        ledger_updates += 1

    packet = load_json(PACKET_PATH)
    packet["status"] = "FOUNDER_DECIDED"
    packet["decided_at"] = DECISION_DATE
    packet["decided_by"] = FOUNDER
    packet["rule"] = (
        "Prepared 2026-08-15 for founder decision; every quote was re-asserted "
        "contiguous in the captured page text whose hashes were re-derived "
        "from the worker-tree bytes in cleveland_artifact_verification_001."
        "json. The founder ruled on every item the same day (see "
        "founder_decision per record); the two APPROVE_CHANGE items were "
        "applied by cleveland_pass1_governance_closeout.py against recomputed "
        "final hashes, and every KEEP_AS_IS item left its record untouched. "
        "Hashes named per record are the values the founder was shown "
        "(post-Pass-1, pre-closeout).")
    for row in packet["records"]:
        ruling = PACKET_DECISIONS[row["item"]]
        row["founder_decision"] = ruling["decision"]
        if "reason" in ruling:
            row["founder_decision_reason"] = ruling["reason"]
        row["outcome"] = ("APPLIED_IN_CLOSEOUT"
                          if ruling["decision"] == "APPROVE_CHANGE"
                          else "NO_AUTHORITY_CHANGE")
    packet["census_hygiene"] = CENSUS_HYGIENE

    summary = OrderedDict([
        ("re_attested", len(attested)),
        ("additions_applied", sorted(k for k in APPROVED_ADDITIONS
                                     if k in attested)),
        ("decisions_ledger_entries_updated", ledger_updates),
        ("final_hashes", {k: by_key[k]["approval"]["record_hash"]
                          for k in sorted(APPROVED_ADDITIONS)}),
    ])

    if apply:
        payload = write_lf(FACTS_PATH, facts)
        new_sha = hashlib.sha256(payload).hexdigest()
        contract = load_json(CONTRACT_PATH)
        contract["policy_package"]["expected_sha256"] = new_sha
        write_lf(CONTRACT_PATH, contract)
        write_lf(DECISIONS_PATH, decisions)
        write_lf(PACKET_PATH, packet)
        # The Pass-1 report keeps its own apply sha as history; the closeout
        # stamps the sha the release contract now pins beside it.
        report = load_json(REPORT_PATH)
        report["facts_sha256_after_closeout"] = new_sha
        write_lf(REPORT_PATH, report)
        summary["facts_sha256_after_closeout"] = new_sha
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=None,
                        help="worker-tree root, to re-assert the two approved "
                             "quotes against the captured page text")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    summary = run(args.data_root, args.apply)
    for key, value in summary.items():
        print("%s: %s" % (key, json.dumps(value) if not isinstance(value, str)
                          else value))
    if not args.apply:
        print("dry run: nothing written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
