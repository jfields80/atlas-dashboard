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
# "Pet & Service Animal Policy" is a heading in its own right, and the one
# Wyndham uses. Without it a block whose only other cue is "Dogs Allowed"
# is never found at all -- the bare word "Pets" never appears on the
# West-Hilliard page.
#
# A species-led row -- "Dogs Allowed - 2 dogs max." -- opens the same Wyndham
# table, on a page where the word "Pets" never appears. It is admitted ONLY when
# a dash or colon follows, i.e. when it is the label of a table row rather than
# prose. Without that guard "Only dogs and cats allowed", which appears mid
# sentence inside other properties' blocks, would open a new block and could
# change which block those pages already select.
_BLOCK_START = re.compile(
    r"(?:Pet\s+Policy"
    r"|Pet\s*(?:&|and)\s*Service\s+Animal(?:\s+Policy)?"
    r"|Dogs?\s*(?:&|and)\s*Cats?\s+Allowed(?=\s*[-–—:])"
    r"|Dogs?\s+Allowed(?=\s*[-–—:])"
    r"|Cats?\s+Allowed(?=\s*[-–—:])"
    r"|(?<![A-Za-z])Pets(?![A-Za-z]))", re.I)
# Headings that close it. The block ends at whichever appears first -- this is
# what keeps a checkout or parking fee from being read as a pet fee.
#
# Every entry here is a HEADING. "Front Desk" needs the extra guard because it
# is also ordinary prose inside a policy card -- "Please ask front desk for any
# questions." -- and closing the block there cut a property off immediately
# before its own "Pet fee per night: 30 USD". The lookbehind admits the heading
# (preceded by a boundary) and rejects the phrase (preceded by a word).
_BLOCK_END = re.compile(
    r"(?:Our\s+policies|Parking|Amenities|Property\s+Amenities|Cancellation|"
    r"Check-in/Check-out|Airport\s+shuttle|Kids\s+services|Breakfast|"
    r"Smoke[- ]free|(?<![a-z]\s)Front\s+Desk)", re.I)
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
    if best is not None:
        return (best[0], best[1])

    # PTF-PROMOTE. No block carries a labelled field. Before refusing, look for
    # one stating its policy in prose -- "Up to two friendly pups under 80 lbs
    # are welcome" is every bit as official as a table cell, and until now was
    # unreachable, so such a hotel could not be published at all.
    #
    # This pass runs ONLY when the labelled pass found nothing anywhere in the
    # page. A page with any labelled block keeps exactly the block it had, so
    # no already-published hotel can have its selection changed by this.
    from scripts.pettripfinder.prose_facts import (
        extract_pet_count, extract_pets_allowed, extract_species,
        extract_weight_limit,
    )
    from scripts.pettripfinder.prose_fee_ladder import has_prose_fee_schedule
    for m in _BLOCK_START.finditer(text or ""):
        window = text[m.start():m.start() + MAX_BLOCK_CHARS]
        end = _BLOCK_END.search(window, m.end() - m.start())
        block = window[:end.start()] if end else window
        score = sum(1 for fn in (extract_pet_count, extract_weight_limit,
                                 extract_species)
                    if fn(block) is not None)
        # PTF-FEES-PROSE. A stated pet PRICE is policy content, and a property
        # that publishes one has said pets are accepted -- nobody prices an
        # animal they refuse. A card reading only "Pets ... are allowed for a
        # non-refundable fee of 45 USD for the 1st night and 10 USD for each
        # additional night" satisfies neither the labelled patterns nor the
        # count/weight/species readers, so it was unreachable and the property
        # could not be published at all.
        priced = has_prose_fee_schedule(block)
        if priced:
            score += 1
        if score and (priced or extract_pets_allowed(block) is not None):
            if best is None or score > best[2]:
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

    # PTF-FEES-ORDINAL. Two shapes must be settled BEFORE any scalar is read,
    # because on these blocks a labelled scalar is present and wrong.
    #
    #   * a per-ANIMAL ladder -- "$80 for first pet and $50 for second pet" --
    #     where a single number cannot describe a two-pet stay;
    #   * a nightly fee stated beside an unrelated per-stay fee, which price the
    #     same stay differently and cannot both be true.
    from scripts.pettripfinder.fee_forms import (
        nightly_versus_per_stay_conflict, ordinal_pet_fees,
    )
    ordinal = None if tiers else ordinal_pet_fees(block)
    stay_clash = None if tiers else nightly_versus_per_stay_conflict(block)
    if stay_clash is not None:
        facts["fee_conflict"] = {
            "reason": "conflicting_fee_terms_in_official_source",
            "detail": [stay_clash.detail],
            "quotes": [stay_clash.ladder_quote, stay_clash.rate_quote],
            "evidence_quote": "%s | %s" % (stay_clash.ladder_quote,
                                           stay_clash.rate_quote),
        }
        for quote in (stay_clash.ladder_quote, stay_clash.rate_quote):
            evidence.append({"field": "fee_conflict",
                             "value": "withheld_conflicting_terms", "quote": quote})
    elif ordinal is not None:
        facts["fee_pet_schedule"] = ordinal.to_dict()
        for name, fee in ordinal.fees:
            evidence.append({"field": "fee_pet_schedule",
                             "value": "%s $%s" % (name, fee.amount),
                             "quote": fee.quote})

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
    # A per-animal ladder or a contradicted fee suppresses the scalar entirely.
    # On both of these blocks a labelled scalar IS present and IS wrong: it is
    # the first pet's price standing in for two, or one side of a contradiction
    # standing in for the source.
    if fees and ordinal is None and stay_clash is None:
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

    # PTF-FEES-CAP. A stated ceiling travels with the rate it caps. "$50 per
    # night up to $150" costs $150 for a week, not $350 -- publishing the rate
    # without its ceiling overstates a long stay, the mirror image of tier
    # flattening.
    from services.research_workers.fee_terms import detect_fee_cap
    cap_amount, cap_quote = detect_fee_cap(block)
    if cap_amount and facts.get("pet_fee"):
        facts["fee_cap"] = {"amount": cap_amount, "currency": "USD",
                            "evidence_quote": cap_quote}
        evidence.append({"field": "fee_cap", "value": "$%s" % cap_amount,
                         "quote": cap_quote})

    # PTF-PROMOTE. Fill ONLY the gaps the labelled patterns left. A labelled
    # value always wins, so every hotel already publishing keeps exactly the
    # fields it had; prose can add, never overwrite.
    from scripts.pettripfinder.prose_facts import (
        UNREPRESENTABLE_FEE_RANGE, WEIGHT_OP_LT,
        detect_unrepresentable_fee_range, extract_fee_cap,
        extract_fee_with_basis, extract_pet_count, extract_pets_allowed,
        extract_species, extract_weight_limit,
    )

    if "weight_limit" not in facts:
        got = extract_weight_limit(block)
        if got:
            facts["weight_limit"] = got.value
            evidence.append({"field": "weight_limit", "value": got.value,
                             "quote": got.quote})
            # Only recorded when the source EXCLUDES the stated figure. Absent
            # means inclusive, which is what every labelled "Maximum Pet
            # Weight: N" has always meant -- so no existing record changes.
            if got.operator == WEIGHT_OP_LT:
                facts["weight_limit_operator"] = WEIGHT_OP_LT
                evidence.append({"field": "weight_limit_operator",
                                 "value": WEIGHT_OP_LT, "quote": got.quote})

    if "pet_count_limit" not in facts:
        got = extract_pet_count(block)
        if got:
            facts["pet_count_limit"] = got.value
            evidence.append({"field": "pet_count_limit", "value": got.value,
                             "quote": got.quote})

    if "species_allowed" not in facts:
        got = extract_species(block)
        if got:
            facts["species_allowed"] = got.value
            evidence.append({"field": "species_allowed", "value": got.value,
                             "quote": got.quote})

    # PTF-FEES-PROSE. A fee with more than one DIMENSION -- a nightly rate under
    # a stay-length ceiling, or a first night priced apart from every night
    # after it -- is read as a schedule, with the dimensions kept apart.
    #
    # This runs BEFORE the scalar prose reader, and suppresses it, because on a
    # staged fee the scalar reader is not merely blind but wrong: given "45 USD
    # for the 1st night and 10 USD for each additional night" it returns $45,
    # and $45 is the price of exactly one night. Reading the first number of a
    # schedule as the whole fee understates every longer stay.
    #
    # Gap-filling only, like every prose reader here: a labelled amount or a
    # parsed tier ladder still wins, so no hotel publishing today can have its
    # fee changed by this.
    from scripts.pettripfinder.prose_fee_ladder import parse_prose_fee_schedule
    schedule = None
    if (not facts.get("pet_fee") and not facts.get("fee_tiers")
            and not facts.get("fee_conflict")
            and not facts.get("fee_pet_schedule")):
        schedule = parse_prose_fee_schedule(block)
    if schedule is not None:
        if schedule.is_staged:
            # No single number is "the fee", so none is published as one. The
            # two stages travel together or not at all.
            facts["fee_schedule"] = {
                "first_night": schedule.first_night.to_dict(),
                "additional_night": schedule.additional_night.to_dict(),
                "evidence_quote": schedule.quote,
            }
            evidence.append({"field": "fee_schedule",
                             "value": "$%s first night, $%s each additional night"
                                      % (schedule.first_night.amount,
                                         schedule.additional_night.amount),
                             "quote": schedule.first_night.quote})
        else:
            facts["pet_fee"] = "$%s" % schedule.rate.amount
            evidence.append({"field": "pet_fee", "value": facts["pet_fee"],
                             "quote": schedule.rate.quote})
            if schedule.rate.basis:
                facts["fee_basis"] = schedule.rate.basis
                evidence.append({"field": "fee_basis", "value": schedule.rate.basis,
                                 "quote": schedule.rate.quote})
        if schedule.cap and not facts.get("fee_cap"):
            facts["fee_cap"] = schedule.cap.to_dict()
            evidence.append({"field": "fee_cap", "value": "$%s" % schedule.cap.amount,
                             "quote": schedule.cap.quote})
        # A ceiling that itself varies with stay length is NOT a fee ladder and
        # must never be published as one: at this property a single night costs
        # the $25 rate, not the $75 six-night ceiling.
        if schedule.cap_tiers:
            facts["fee_cap_tiers"] = [t.to_dict() for t in schedule.cap_tiers]
            for t in schedule.cap_tiers:
                evidence.append({"field": "fee_cap_tiers", "value": "$%s" % t.amount,
                                 "quote": t.quote})

    # PTF-FEES-FORMS. Two fee wordings the labelled patterns cannot reach --
    # the amount written before its label ("$50 USD pet fee will apply per pet
    # per night") and the basis written inside it ("Pet fee per night: 30 USD").
    # Gap-filling only, and deliberately AFTER the tier and schedule readers, so
    # a property whose ladder is already understood keeps it.
    #
    # Before either may speak, the block is checked for a contradiction: one
    # property states a stay-length ladder AND a flat nightly rate, which price
    # the same stay differently. Neither is published. Both quotations are kept
    # and the fee is withheld, which is what the source actually supports.
    from scripts.pettripfinder.fee_forms import fee_contradiction, stated_fee
    if not facts.get("pet_fee") and not facts.get("fee_tiers") \
            and not facts.get("fee_schedule") \
            and not facts.get("fee_conflict") \
            and not facts.get("fee_pet_schedule"):
        clash = fee_contradiction(block)
        if clash is not None:
            facts["fee_conflict"] = {
                "reason": "conflicting_fee_terms_in_official_source",
                "detail": [clash.detail],
                "quotes": [clash.ladder_quote, clash.rate_quote],
                "evidence_quote": "%s | %s" % (clash.ladder_quote, clash.rate_quote),
            }
            for quote in (clash.ladder_quote, clash.rate_quote):
                evidence.append({"field": "fee_conflict",
                                 "value": "withheld_conflicting_terms",
                                 "quote": quote})
        else:
            got = stated_fee(block)
            if got is not None:
                facts["pet_fee"] = "$%s" % got.amount
                evidence.append({"field": "pet_fee", "value": facts["pet_fee"],
                                 "quote": got.quote})
                # Never defaulted. "$150 non-refundable fee" states an amount and
                # no recurrence, and calling it per-stay would invent the term.
                if got.basis:
                    facts["fee_basis"] = got.basis
                    evidence.append({"field": "fee_basis", "value": got.basis,
                                     "quote": got.quote})
                cap = extract_fee_cap(block)
                if cap and not facts.get("fee_cap"):
                    facts["fee_cap"] = {"amount": cap.value.lstrip("$"),
                                        "currency": "USD",
                                        "evidence_quote": cap.quote}
                    evidence.append({"field": "fee_cap", "value": cap.value,
                                     "quote": cap.quote})

    # A fee stated as a RANGE is two numbers and a condition. Publishing either
    # end is wrong -- the high overstates a short stay, the low understates a
    # long one -- and the thresholds that would separate them are not stated,
    # so no ladder can be built either. Withhold the number, keep the sentence.
    #
    # Only when no scalar and no ladder were found: a labelled amount is a
    # statement of fact and outranks a range read out of prose.
    if (not facts.get("pet_fee") and not facts.get("fee_tiers")
            and not facts.get("fee_schedule") and not facts.get("fee_conflict")
            and not facts.get("fee_pet_schedule")):
        fee_range = detect_unrepresentable_fee_range(block)
        if fee_range:
            facts["fee_withheld"] = {
                "reason": UNREPRESENTABLE_FEE_RANGE,
                "detail": ["fee_range_%s_to_%s" % (fee_range.low, fee_range.high)],
                "evidence_quote": fee_range.quote,
            }
            evidence.append({"field": "fee_withheld",
                             "value": "withheld_unrepresentable_range",
                             "quote": fee_range.quote})

    # PTF-CAPTURE-004B. A fee written without a dollar sign -- "25 USD per pet
    # per night" -- is still a stated fee, and the labelled patterns only ever
    # recognised "$25". The BASIS travels with the amount and is never
    # defaulted: "per pet per night" and "per night for up to 2 pets" are the
    # same number and different policies, and a second dog doubles only one of
    # them.
    #
    # Runs AFTER the range check, and only when no range was withheld. Ordered
    # the other way round it read "Pet fee per pet is 75 to 150 dollars" as a
    # $150 fee -- the high end of a range published as the price, which is the
    # error the withholding exists to prevent. Gap-filling only: a labelled
    # amount or a tier ladder still outranks prose, so no hotel publishing
    # today can have its fee changed by this.
    if (not facts.get("pet_fee") and not facts.get("fee_tiers")
            and not facts.get("fee_withheld") and not facts.get("fee_schedule")
            and not facts.get("fee_conflict")
            and not facts.get("fee_pet_schedule")):
        got = extract_fee_with_basis(block)
        if got:
            facts["pet_fee"] = got.value
            evidence.append({"field": "pet_fee", "value": got.value,
                             "quote": got.quote})
            if got.operator:
                facts["fee_basis"] = got.operator
                evidence.append({"field": "fee_basis", "value": got.operator,
                                 "quote": got.quote})
            cap = extract_fee_cap(block)
            if cap and not facts.get("fee_cap"):
                facts["fee_cap"] = {"amount": cap.value.lstrip("$"),
                                    "currency": "USD",
                                    "evidence_quote": cap.quote}
                evidence.append({"field": "fee_cap", "value": cap.value,
                                 "quote": cap.quote})

    welcome = _WELCOME.search(block)
    if welcome or facts.get("pet_fee") or facts.get("fee_schedule"):
        facts["pets_allowed"] = "true"
        # A staged fee carries its own sentence, which states the permission far
        # better than whichever fact happened to be recorded first.
        stated = (welcome.group(0) if welcome
                  else facts["fee_schedule"]["evidence_quote"]
                  if facts.get("fee_schedule") else evidence[0]["quote"])
        evidence.append({"field": "pets_allowed", "value": "true",
                         "quote": " ".join(stated.split())})

    if welcome or facts.get("fee_tiers"):
        facts.setdefault("pets_allowed", "true")

    if "pets_allowed" not in facts:
        stated = extract_pets_allowed(block)
        if stated is not None:
            facts["pets_allowed"] = stated.value
            evidence.append({"field": "pets_allowed", "value": stated.value,
                             "quote": stated.quote})

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

    # PTF-FEES-CONFLICT. The attestation already records when the SAME official
    # source states incompatible fee terms -- "$50 per night" beside
    # "Per Stay: $50.00", or "per pet" beside "Per Stay". Until now that list
    # was carried as provenance and never read, so a record with a recorded
    # conflict still published one of the two readings as fact. A four-night
    # stay at Courtyard Columbus Easton is $150 under one sentence and $50
    # under the other; choosing silently is not a rounding error.
    #
    # The hotel stays published -- the rest of its policy is sound -- but the
    # fee is withheld and the conflict stated plainly, with both quotations
    # preserved for a reader and a reviewer.
    #
    # PTF-APPROVAL-RESOLUTION. A human may dispose of specific markers on this
    # exact attestation, and only then is the fee carried. The detector is
    # untouched: it still reports what it saw, the markers stay on the record,
    # and anything unresolved still withholds. An approval with no structured
    # resolution -- however emphatic its prose -- changes nothing here.
    from services.research_workers.approval_resolution import (
        FAMILY_FEE_BASIS, authorizing_resolution, family_fully_resolved,
    )

    conflicts = [c for c in (attestation.get("contradictions") or [])
                 if c.startswith("conflicting_fee_basis")]
    fee_resolution = {}
    if conflicts and family_fully_resolved(attestation, FAMILY_FEE_BASIS):
        fee_resolution = authorizing_resolution(attestation, FAMILY_FEE_BASIS)
        if fee_resolution:
            conflicts = []

    if conflicts:
        for field in ("pet_fee", "fee_basis", "fee_cap"):
            facts.pop(field, None)
        evidence = [e for e in evidence
                    if e["field"] not in ("pet_fee", "fee_cap")]
        facts["fee_conflict"] = {
            "reason": "conflicting_fee_terms_in_official_source",
            "detail": sorted(conflicts),
            "evidence_quote": " ".join(block.split())[:400],
        }
        evidence.append({"field": "fee_conflict",
                         "value": "withheld_pending_resolution",
                         "quote": " ".join(block.split())[:400]})

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
            # The audit trail: what the detector said, and what a named human
            # decided about it. Both, always -- the markers above are never
            # edited away, and this says who overrode which of them and why.
            "resolved_contradictions": (
                {"family": fee_resolution.get("marker_family"),
                 "markers": list(fee_resolution.get("markers") or []),
                 "disposition": fee_resolution.get("disposition"),
                 "approval_record_id": fee_resolution.get("approval_record_id"),
                 "approver_id": fee_resolution.get("approver_id"),
                 "attestation_hash": fee_resolution.get("attestation_hash"),
                 "resolved_at": fee_resolution.get("resolved_at"),
                 "rationale": fee_resolution.get("rationale")}
                if fee_resolution else None),
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
