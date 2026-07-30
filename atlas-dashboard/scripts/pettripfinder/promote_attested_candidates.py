"""PTF-CAPTURE-003 -- promote an APPROVED official attestation into a
publishable importer candidate.

The last link in the manual-attestation chain. Capture, ingestion, attestation
and approval already exist; nothing carried an approved attestation into the
importer corpus that ``export_hotel_policy_facts`` reads, so an approved hotel
could never reach the site.

Why this is not a simple field copy
-----------------------------------
The attested page text is normalized to a single line, and a hotel page states
many amounts that are not the pet fee. Hilton Columbus at Easton alone carries
five: the $100.00 pet fee, a $100.00 early-checkout fee, a $100.00 late-checkout
fee, and $12.00/$40.00 parking. Picking the first, largest, or nearest dollar
figure would publish a wrong fee that looks entirely plausible.

So extraction is BLOCK-SCOPED and LABEL-DRIVEN:

  1. locate the property's pet-policy block by its heading;
  2. end the block at the next section heading;
  3. read only explicitly LABELLED values inside that block.

A bare dollar amount is never harvested. Hilton's "Non-refundable fee: $100.00"
is accepted because it sits inside the Pets block; the identical "$100.00" on
the early-checkout line is not, because it sits outside it. Two different pet
fees inside one block is a contradiction, not a choice, and fails closed.

Nothing here infers, averages, or prefers. A value that is not stated under a
label this module recognises is simply absent from the candidate.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.site_data import (  # noqa: E402
    WORKER_PROMOTION_ROOT, normalize_name,
)

PROMOTION_SUBDIR = "candidates"
ADAPTER_VERSION = "ptf-capture-003/1.0.0"

# Headings that open a property's pet-policy block.
_BLOCK_START = re.compile(r"(?:Pet\s+Policy|(?<![A-Za-z])Pets(?![A-Za-z]))", re.I)
# Headings that close it. The block ends at whichever appears first -- this is
# what keeps a checkout or parking fee from being read as a pet fee.
_BLOCK_END = re.compile(
    r"(?:Our\s+policies|Parking|Amenities|Property\s+Amenities|Cancellation|"
    r"Check-in/Check-out|Airport\s+shuttle|Kids\s+services|Breakfast|"
    r"Smoke[- ]free|Front\s+Desk)", re.I)
# A block longer than this is not a policy card; refuse rather than guess.
MAX_BLOCK_CHARS = 700

_MONEY = r"\$?\s*([0-9][0-9,]*(?:\.[0-9]{2})?)"

# Labelled patterns, evaluated ONLY inside the block. Each yields (value, quote).
# The colon is optional throughout: the same brand renders these fields as
# "Max weight: 75 lbs" on one page template and as bare table cells reading
# "Max weight 75 lbs" on another. Requiring the colon silently found no policy
# block at all on the table layout.
_FEE_PATTERNS = (
    # Marriott: basis is part of the label.
    (re.compile(r"Non-Refundable\s+Pet\s+Fee\s+Per\s+(Night|Stay)\s*:?\s*" + _MONEY, re.I),
     "labelled_pet_fee_with_basis"),
    # Hilton: inside the Pets card, so "fee" alone is unambiguous here.
    (re.compile(r"Non-refundable\s+fee\s*:?\s*" + _MONEY, re.I),
     "labelled_nonrefundable_fee_in_pet_block"),
    (re.compile(r"Pet\s+Fee\s*:?\s*" + _MONEY, re.I), "labelled_pet_fee"),
    # Table layout, amount BEFORE the label: "Deposit Yes. $75.00 Non-refundable Fee".
    (re.compile(r"Deposit[^$\d]{0,12}" + _MONEY + r"\s*Non-refundable\s+Fee", re.I),
     "deposit_row_amount_before_label"),
)
_WEIGHT = re.compile(r"(?:Max(?:imum)?\s+Pet\s+Weight|Max\s+weight)\s*:?\s*"
                     r"([0-9]+(?:\.[0-9]+)?)\s*(?:lbs?|pounds?)", re.I)
_COUNT = re.compile(r"(?:Maximum\s+Number\s+of\s+Pets\s+in\s+Room|Max\s+pets?)\s*:?\s*([0-9]+)",
                    re.I)
_WELCOME = re.compile(r"Pets\s+Welcome|Pets\s+allowed\s+Yes", re.I)
# The row a property uses for terms its structured fields cannot hold -- where
# a stay-length ladder is published.
_OTHER_PET_INFO_RE = re.compile(r"Other\s+pet\s+information", re.I)


class PromotionError(ValueError):
    """Refusal to build a candidate. Always carries the reason."""


def find_pet_block(text: str) -> Tuple[str, int]:
    """Return ``(block_text, start_offset)`` for the property's pet-policy card.

    Chooses the block that actually carries labelled policy content: a page may
    mention "pets" in prose long before the policy card, so candidate blocks are
    scored by whether a fee/weight/count label appears inside them.
    """
    best: Optional[Tuple[str, int, int]] = None
    for m in _BLOCK_START.finditer(text or ""):
        window = text[m.start():m.start() + MAX_BLOCK_CHARS]
        end = _BLOCK_END.search(window, m.end() - m.start())
        block = window[:end.start()] if end else window
        score = sum(1 for rx in (_WEIGHT, _COUNT) if rx.search(block))
        score += sum(1 for rx, _ in _FEE_PATTERNS if rx.search(block))
        # A stay-length ladder is policy content too -- a block carrying only
        # tiers (no weight, no count) is still the pet-policy block.
        if _OTHER_PET_INFO_RE.search(block):
            score += 1
        if score and (best is None or score > best[2]):
            best = (block, m.start(), score)
    if best is None:
        raise PromotionError("no_labelled_pet_policy_block_found")
    return (best[0], best[1])


def extract_pet_facts(text: str) -> Tuple[Dict[str, str], List[Dict[str, str]], str]:
    """Return ``(facts, evidence, block)`` from the attested page text.

    Fails closed on ambiguity: two different pet-fee values inside one block is
    a contradiction to be reviewed, never a value to be picked.
    """
    block, _ = find_pet_block(text)
    facts: Dict[str, str] = {}
    evidence: List[Dict[str, str]] = []

    # PTF-WORKERS-FEE-TERMS. A stay-length tier ladder is parsed BEFORE the
    # scalar fee, and when one is found the scalar is deliberately not emitted:
    # publishing "$75" for a policy that charges $125 from the fifth night is
    # the flattening this whole path exists to prevent.
    from services.research_workers.fee_terms import (
        basis_is_stated, parse_fee_tiers, tier_facts,
    )
    tiers, tier_problems = parse_fee_tiers(block)
    if tiers:
        facts["fee_tiers"] = tier_facts(tiers, basis_stated=basis_is_stated(block))
        for t in tiers:
            evidence.append({"field": "fee_tiers", "value": "$%s" % t.amount,
                             "quote": t.evidence_quote})
    elif tier_problems and tier_problems != ["tier_notation_unparseable"] \
            and tier_problems != ["tier_single_only"]:
        # Tier wording that is present but not understood is a review matter,
        # never something to fall back to a single number over.
        raise PromotionError("tiered_fee_not_understood:%s" % ",".join(tier_problems))

    fees: List[Tuple[str, str, str]] = []      # (amount, basis, quote)
    for rx, _label in _FEE_PATTERNS:
        for m in rx.finditer(block):
            groups = m.groups()
            if len(groups) == 2:
                basis, amount = groups[0], groups[1]
                basis = "per %s" % basis.lower()
            else:
                basis, amount = "", groups[0]
            fees.append((amount.replace(",", ""), basis, " ".join(m.group(0).split())))

    distinct = {f[0] for f in fees}
    if tiers:
        # The ladder is the fee. A Deposit row stating the first tier's amount
        # is consistent; anything else is a conflict between two rows of the
        # same source and must be reviewed with both quotations kept.
        tier_amounts = {t.amount for t in tiers}
        conflicting = {a for a in distinct
                       if a not in tier_amounts and ("%s.00" % a) not in tier_amounts}
        if conflicting:
            raise PromotionError(
                "deposit_row_conflicts_with_tiers:deposit=%s tiers=%s"
                % (",".join(sorted(conflicting)), ",".join(sorted(tier_amounts))))
        fees = []                       # never publish a scalar beside a ladder
    elif len(distinct) > 1:
        raise PromotionError("multiple_distinct_pet_fees_in_block:%s"
                             % ",".join(sorted(distinct)))
    if fees:
        amount, basis, quote = fees[0]
        facts["pet_fee"] = "$%s" % amount
        if basis:
            facts["fee_basis"] = basis
        evidence.append({"field": "pet_fee", "value": facts["pet_fee"],
                         "quote": quote})

    m = _WEIGHT.search(block)
    if m:
        facts["weight_limit"] = "%s pounds" % m.group(1)
        evidence.append({"field": "weight_limit", "value": facts["weight_limit"],
                         "quote": " ".join(m.group(0).split())})

    m = _COUNT.search(block)
    if m:
        facts["pet_count_limit"] = m.group(1)
        evidence.append({"field": "pet_count_limit", "value": m.group(1),
                         "quote": " ".join(m.group(0).split())})

    welcome = _WELCOME.search(block)
    if welcome or facts.get("pet_fee"):
        facts["pets_allowed"] = "true"
        evidence.append({
            "field": "pets_allowed", "value": "true",
            "quote": " ".join((welcome.group(0) if welcome
                               else evidence[0]["quote"]).split())})

    if welcome or facts.get("fee_tiers"):
        facts.setdefault("pets_allowed", "true")
    if "pets_allowed" not in facts:
        raise PromotionError("no_publishable_pet_facts_in_block")
    return (facts, evidence, " ".join(block.split()))


def build_candidate(attestation: Dict, page_text: str) -> Dict:
    """Turn an APPROVED attestation plus its attested text into a candidate.

    Refuses anything not approved. An attestation that has not been through the
    separate approval act is exactly the thing this must not publish.
    """
    approval = attestation.get("approval") or {}
    if approval.get("state") != "APPROVED":
        raise PromotionError("attestation_not_approved:%s" % approval.get("state"))
    if not attestation.get("publishable"):
        raise PromotionError("attestation_not_publishable")

    facts, evidence, block = extract_pet_facts(page_text)
    url = attestation["official_url"]
    for e in evidence:
        e["source_url"] = url

    key = normalize_name(attestation["listing_name"])
    slug = re.sub(r"[^a-z0-9]+", "-", key).strip("-")
    return {
        "candidate_id": "attested-promotion-%s" % slug,
        "evidence": evidence,
        "pet_facts": sorted(facts.items()),
        "proposed_fields": [
            ["name", attestation["listing_name"]],
            ["source_url", url],
            ["pet_policy", block],
        ],
        # READY is what the exporter consumes. The provenance below records how
        # this record earned it -- a human attestation plus an explicit,
        # hash-bound approval -- so no reader can mistake it for an automatic
        # model extraction that routed READY on its own.
        "recommendation": "READY",
        "snapshot": {"observed_at": attestation["observed_at"]},
        "source_relationship": "EXACT_ENTITY_DOMAIN",
        "worker_provenance": {
            "adapter_version": ADAPTER_VERSION,
            "promotion_basis": "MANUAL_OFFICIAL_ATTESTATION",
            "attestation_id": attestation["attestation_id"],
            "attestation_hash": attestation["attestation_hash"],
            "capture_method": attestation["capture_method"],
            "source_types": [attestation["source_type"]],
            "attested_by": (attestation.get("affirmation") or {}).get("operator_id", ""),
            "attested_at": (attestation.get("affirmation") or {}).get("attested_at", ""),
            "approval": {
                "state": approval.get("state"),
                "approver_id": approval.get("approver_id"),
                "approved_at": approval.get("approved_at"),
                "approval_record_id": approval.get("approval_record_id"),
            },
            "preserved_contradictions": list(attestation.get("contradictions") or []),
            "all_page_fee_amounts": list(attestation.get("fee_amounts") or []),
        },
    }


def write_candidate(candidate: Dict, root: Path = None) -> Path:
    """Write the candidate into the additive-only worker-promotion root.

    Refuses to overwrite: a second promotion of the same hotel must be a
    deliberate act, not a silent replacement of published evidence.
    """
    root = Path(root or WORKER_PROMOTION_ROOT)
    out_dir = root / PROMOTION_SUBDIR
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / ("%s.json" % candidate["candidate_id"])
    if path.exists():
        raise PromotionError("candidate_already_exists:%s" % path.name)
    path.write_text(json.dumps(candidate, indent=2, sort_keys=True,
                               ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--attestation", required=True)
    ap.add_argument("--capture", required=True,
                    help="the archived capture JSON the attestation was built from")
    ap.add_argument("--promotion-root", default=None)
    ap.add_argument("--apply", action="store_true",
                    help="write the candidate; default is a dry run")
    args = ap.parse_args(argv)

    from scripts.pettripfinder.importer.source_snapshot import normalize_html_to_text
    from services.research_workers.operator_capture import verify_attestation_record

    rec = json.loads(Path(args.attestation).read_text(encoding="utf-8"))
    ok, why = verify_attestation_record(rec)
    if not ok:
        sys.stderr.write("attestation failed hash verification: %s\n" % why)
        return 4

    html = json.loads(Path(args.capture).read_text(encoding="utf-8"))["html"]
    text, _ = normalize_html_to_text(html)
    try:
        cand = build_candidate(rec, text)
    except PromotionError as exc:
        sys.stderr.write("promotion refused: %s\n" % exc)
        return 4

    print("=== PTF-CAPTURE-003 attested-candidate promotion ===")
    print("  hotel              : %s" % rec["listing_name"])
    print("  attestation        : %s (%s)" % (rec["attestation_id"],
                                              rec["approval"]["state"]))
    print("  attestation hash   : verified")
    print("  candidate id       : %s" % cand["candidate_id"])
    print("  pet facts          :")
    for k, v in cand["pet_facts"]:
        print("      %-18s %s" % (k, v))
    print("  page fee amounts   : %s" % ", ".join(cand["worker_provenance"]
                                                  ["all_page_fee_amounts"]))
    print("  bound pet fee      : %s   <- from the labelled pet-policy block only"
          % dict(cand["pet_facts"]).get("pet_fee", "(none stated)"))
    if not args.apply:
        print("\n  DRY RUN -- nothing written. Re-run with --apply.")
        return 0
    path = write_candidate(cand, args.promotion_root)
    print("  written            : %s" % path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
