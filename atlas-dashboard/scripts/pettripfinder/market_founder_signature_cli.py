"""Record a founder's signature over a reviewed candidate set, and nothing else.

    python scripts/pettripfinder/market_founder_signature_cli.py \
      --market st-louis-mo \
      --packet <founder_review_packet.json> --analysis <review_analysis.json> \
      --decided-by jfields80 --decided-at 2026-08-23 \
      --authorization "<the founder's own words>" \
      --work-order PTF-ST-LOUIS-FOUNDER-SIGNATURE-005 \
      --out <founder_decisions.json>

THE ATTESTATION DOES NOT LIVE IN THE PACKET
-------------------------------------------
PTF-DAYTON-RECERTIFICATION-001 wrote the rule and it is the reason this is a
separate file: "The review packet is emitted by an idempotent generator, so
re-running it would overwrite anything written into it. A human attestation must
not live somewhere a regeneration can erase."

So the packet stays regenerable and stays unsigned. This ledger is the signature,
and it binds each row to the SEMANTIC HASH the founder was shown. If a record
changes afterwards, its hash stops matching and the signature visibly no longer
covers it -- which is what a binding is for.

WHO DECIDED AND WHO TYPED ARE TWO DIFFERENT FIELDS
---------------------------------------------------
``decided_by`` is the founder. ``recorded_by`` is the agent that transcribed the
ruling, and it says so in words. PTF-POLICY-SCHEMA-MIGRATION-001 Phase F is why:
twenty-six approvals were once written under a founder's name for records the
founder had never seen, every fact source-backed and every hash verified, and
the defect was purely the signature -- exactly the kind that survives every
technical gate, because no gate checks who a name belongs to.

This module cannot tell whether a human authorised anything. What it CAN do is
refuse to invent the parts of an attestation that are not handed to it, and
record precisely what it was told, including the authorisation in the founder's
own words. Both are required arguments with no defaults for that reason.

WHAT IT REFUSES TO SIGN
-----------------------
Only rows whose reviewed disposition is in ``--sign`` are signed, and the run
fails if a requested row is not in that set. A signature pass is authorised over
a NAMED population; silently widening it to whatever happened to be reviewable
is how a scoped approval becomes a blanket one. Every unsigned row is carried in
the ledger with the reason it was withheld, so the file states its own scope.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.contracts import enums  # noqa: E402
from scripts.pettripfinder.contracts import founder_approval as FA  # noqa: E402

SCHEMA = "ptf-founder-decision-ledger/1.0"

#: Reviewed dispositions a signature pass may cover by default. Both are
#: "nothing left to correct"; APPROVE_WITH_CHANGE and HOLD are deliberately
#: absent, because each names outstanding work and a signature is not it.
DEFAULT_SIGNABLE: Tuple[str, ...] = ("APPROVE_PET_FRIENDLY",
                                     "APPROVE_VERIFIED_NO_PETS")

#: Reviewed disposition -> the authority a signed row proposes.
AUTHORITY_FOR = {
    "APPROVE_PET_FRIENDLY": enums.PUBLISHED_PET_FRIENDLY,
    "APPROVE_VERIFIED_NO_PETS": enums.VERIFIED_NO_PETS,
}


class SignatureError(RuntimeError):
    """Raised rather than signing something the caller did not authorise."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sign(packet: Mapping, analysis: Mapping, *, decided_by: str,
         decided_at: str, authorization: str, work_order: str,
         recorded_by: str,
         signable: Sequence[str] = DEFAULT_SIGNABLE) -> Dict:
    """The ledger. Signs exactly the rows whose review says they are ready."""
    if not decided_by or not decided_at or not authorization:
        raise SignatureError(
            "decided_by, decided_at and authorization are required and have no "
            "defaults: an attestation the agent completed for itself is the "
            "defect this contract exists to prevent")

    reviewed = {r["identity_key"]: r for r in analysis.get("rows") or ()}
    candidates = {c["identity_key"]: c for c in packet.get("candidates") or ()}
    missing = sorted(set(candidates) - set(reviewed))
    if missing:
        raise SignatureError(
            "%d candidate(s) carry no reviewed disposition: %s -- every row must "
            "be reviewed before any row is signed"
            % (len(missing), missing[:5]))

    signable_set = frozenset(signable)
    signed: List[Dict] = []
    withheld: List[Dict] = []

    for key in sorted(candidates):
        candidate = candidates[key]
        row = reviewed[key]
        disposition = row["proposed_disposition"]
        existing = (candidate.get("founder_decision")
                    or candidate.get("founder_reviewer_id")
                    or candidate.get("founder_reviewed_at"))
        if existing:
            raise SignatureError(
                "%s already carries an attestation in the packet; a second "
                "signature over a signed row would overwrite somebody's "
                "ruling" % key)

        if disposition not in signable_set:
            withheld.append(OrderedDict((
                ("identity_key", key),
                ("canonical_name", candidate.get("canonical_name", "")),
                ("reviewed_disposition", disposition),
                ("withheld_because", "outside the authorised signature scope"),
                ("outstanding", row.get("next_action")
                 or "; ".join(c["why"] for c in row.get("required_changes") or ())
                 or "see the review analysis"),
            )))
            continue

        signed.append(OrderedDict((
            ("identity_key", key),
            ("canonical_name", candidate.get("canonical_name", "")),
            ("brand", candidate.get("brand", "")),
            ("corridor", candidate.get("corridor", "")),
            # The founder's ruling, in the repository's canonical vocabulary.
            ("founder_decision", FA.assert_writable(FA.CANONICAL_APPROVED)),
            ("founder_reviewer_id", decided_by),
            ("founder_reviewed_at", decided_at),
            ("founder_note", ""),
            ("reviewed_disposition", disposition),
            ("proposes_authority", AUTHORITY_FOR[disposition]),
            # What the ruling is BOUND to. A record that changes after this
            # point stops matching, and the signature visibly stops covering it.
            ("bound_semantic_hash",
             (candidate.get("semantic_approval") or {}).get("semantic_hash", "")),
            ("bound_snapshot_hash", candidate.get("snapshot_hash", "")),
            ("bound_source_url", candidate.get("source_url", "")),
        )))

    by_authority = Counter(r["proposes_authority"] for r in signed)
    return OrderedDict((
        ("schema", SCHEMA),
        ("what_this_is",
         "A founder's signature over a reviewed candidate set, kept apart from "
         "the review packet because the packet is regenerated by an idempotent "
         "builder and an attestation must not live where a rebuild can erase "
         "it."),
        ("market_id", packet.get("market_id", "")),
        ("work_order", work_order),
        ("approval_vocabulary", FA.VOCABULARY_VERSION),
        ("decided_by", decided_by),
        ("decided_at", decided_at),
        ("authorization", authorization),
        ("recorded_by", recorded_by),
        ("who_decided_and_who_typed",
         "decided_by is the founder; recorded_by is the agent that transcribed "
         "the ruling. No disposition here was inferred, defaulted or completed "
         "by the agent: each is the reviewed disposition the founder authorised "
         "by name and scope."),
        ("status", "RECORDED"),
        ("authorised_scope", list(signable)),
        ("candidates_reviewed", len(candidates)),
        ("signed_count", len(signed)),
        ("withheld_count", len(withheld)),
        ("signed_by_authority", OrderedDict(sorted(by_authority.items()))),
        ("withheld_by_disposition", OrderedDict(sorted(
            Counter(r["reviewed_disposition"] for r in withheld).items()))),
        ("nothing_is_published_by_this_file",
         "This ledger records a decision. It registers no market, publishes no "
         "page and deploys nothing."),
        ("signed", signed),
        ("withheld", withheld),
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--market", required=True)
    parser.add_argument("--packet", required=True)
    parser.add_argument("--analysis", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--work-order", required=True)
    parser.add_argument("--decided-by", required=True,
                        help="the FOUNDER's identifier -- never the agent's")
    parser.add_argument("--decided-at", required=True)
    parser.add_argument("--authorization", required=True,
                        help="the founder's authorisation, in their own words")
    parser.add_argument("--recorded-by", required=True,
                        help="who transcribed the ruling")
    parser.add_argument("--sign", action="append", default=None,
                        help="reviewed dispositions in scope; repeatable")
    parser.add_argument("--expect-signed", type=int, default=None,
                        help="fail unless exactly this many rows are signed")
    args = parser.parse_args(argv)

    packet = json.loads(Path(args.packet).read_text(encoding="utf-8"))
    analysis = json.loads(Path(args.analysis).read_text(encoding="utf-8"))
    ledger = sign(packet, analysis, decided_by=args.decided_by,
                  decided_at=args.decided_at,
                  authorization=args.authorization,
                  work_order=args.work_order,
                  recorded_by=args.recorded_by,
                  signable=tuple(args.sign or DEFAULT_SIGNABLE))

    if args.expect_signed is not None and ledger["signed_count"] != args.expect_signed:
        raise SignatureError(
            "expected to sign %d rows and signed %d -- a signature pass whose "
            "population does not match what was authorised is stopped, not "
            "reconciled afterwards"
            % (args.expect_signed, ledger["signed_count"]))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(ledger, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print("signed   : %d" % ledger["signed_count"])
    print("by author: %s" % dict(ledger["signed_by_authority"]))
    print("withheld : %d %s" % (ledger["withheld_count"],
                                dict(ledger["withheld_by_disposition"])))
    print("decided  : %s on %s" % (ledger["decided_by"], ledger["decided_at"]))
    print("written  : %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
