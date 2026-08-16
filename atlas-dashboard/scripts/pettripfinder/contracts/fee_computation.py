"""When a structured fee may safely be turned into a number.

The distinction this module exists to make
------------------------------------------
"A structured fee exists" is NOT "safe to calculate". A record can carry a
perfectly well-formed ``pet_fee`` of $50 and still be unable to answer "what
will two dogs cost for four nights?" -- because the source never said whether
the $50 was per pet or per room, or whether a stay-length band was a nightly
rate or a total. Publishing a total derived from data that cannot support one
is worse than publishing no total: the guest cannot see the guess.

The classifier below is a PURE FUNCTION of a 1.2 facts block. It reads no
evidence prose, makes no inference, and never consults a market. Its output is
persisted on the record AND recomputed by a release gate, so that a schema
change which silently reclassifies published records fails the build instead of
shipping.

Both halves are necessary. A hand-set class drifts the moment a fact is
corrected, and a wrong class authorises arithmetic the data cannot support.
Derivation alone would be a gate that recomputes its own expectation and
therefore proves nothing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Mapping, Optional, Sequence, Tuple

from scripts.pettripfinder.contracts import enums


@dataclass(frozen=True)
class Classification:
    """The class, and the rule that produced it.

    ``reason`` is not decoration. A reviewer looking at a hotel that dropped out
    of a fee filter needs to know WHICH rule excluded it, because the remedy
    differs: an unstated scope is a capture problem, an unstated tier basis is
    a source problem, and a missing role is a migration problem.
    """

    computation_class: str
    reason: str
    rule: str

    @property
    def is_safe_for_one_pet(self) -> bool:
        return self.computation_class in enums.COMPUTABLE_FOR_ONE_PET

    @property
    def is_safe_for_many_pets(self) -> bool:
        return self.computation_class in enums.COMPUTABLE_FOR_MANY_PETS


def _result(cls: str, rule: str, reason: str) -> Classification:
    return Classification(computation_class=cls, reason=reason, rule=rule)


def _all_caps(facts: Mapping) -> List[Tuple[str, Mapping]]:
    """Every cap in the record, wherever it hangs.

    A cap can sit at fact level or nested on a pet-schedule rung. Both bound
    real money, so both must satisfy the same qualifier rules -- checking only
    the fact-level one is how a $105 second-pet ceiling ends up applied to a
    first pet that stays free.
    """
    caps: List[Tuple[str, Mapping]] = []
    cap = facts.get("fee_cap")
    if isinstance(cap, Mapping):
        caps.append(("fee_cap", cap))
    schedule = facts.get("fee_pet_schedule")
    if isinstance(schedule, Mapping):
        for index, entry in enumerate(schedule.get("entries") or []):
            if isinstance(entry, Mapping) and isinstance(entry.get("cap"), Mapping):
                caps.append(("fee_pet_schedule.entries[%d].cap" % index, entry["cap"]))
    return caps


def _tier_ranges_contiguous(tiers: Sequence[Mapping]) -> bool:
    """True when stay-length bands tile a range with no gap and no overlap.

    A gap means some stay length has no price; an overlap means two prices.
    Either way there is no single correct answer to compute, and picking one
    invents the difference.
    """
    bands: List[Tuple[int, Optional[int]]] = []
    for tier in tiers:
        lo = tier.get("condition_min")
        hi = tier.get("condition_max")
        if not isinstance(lo, int) or isinstance(lo, bool):
            return False
        if hi is not None and (not isinstance(hi, int) or isinstance(hi, bool)):
            return False
        bands.append((lo, hi))
    bands.sort(key=lambda b: b[0])
    open_ended = [b for b in bands if b[1] is None]
    if len(open_ended) > 1:
        return False
    for earlier, later in zip(bands, bands[1:]):
        if earlier[1] is None:
            return False            # an open band must be the last one
        if later[0] != earlier[1] + 1:
            return False            # gap or overlap
    return True


def classify(facts: Mapping) -> Classification:
    """Derive the computation class of a 1.2 facts block.

    The steps are ordered so that the most disqualifying condition wins: a
    record with both an unknown tier basis and an unscoped cap is reported
    against whichever rule a reviewer must fix first.
    """
    if not isinstance(facts, Mapping):
        return _result(enums.NOT_COMPUTABLE, "step0",
                       "no facts block to compute from")

    fee = facts.get("pet_fee") if isinstance(facts.get("pet_fee"), Mapping) else None
    tiers = [t for t in (facts.get("fee_tiers") or []) if isinstance(t, Mapping)]
    schedule = facts.get("fee_pet_schedule") \
        if isinstance(facts.get("fee_pet_schedule"), Mapping) else None

    # 0. Nothing to compute. A property that states no charge at all is not
    #    "free" -- it is silent, and silence is not a number.
    if fee is None and not tiers and schedule is None:
        return _result(enums.NOT_COMPUTABLE, "step0",
                       "the record states no pet fee, tiers or schedule")

    # 1. A withheld or contradicted fee is never computable. The withholding
    #    decision already said the amount cannot be published; deriving a total
    #    from it would republish it through arithmetic.
    withheld = facts.get("_withheld_fee_paths") or ()
    if any(p == "pet_fee" or p.startswith("pet_fee.") for p in withheld):
        return _result(enums.NOT_COMPUTABLE, "step1",
                       "the fee is withheld, so no total may be derived from it")

    # 3. Tiers must be role-resolved and tile their range. (Checked before the
    #    scalar rules because a laddered fee has no single amount to scope.)
    if tiers:
        if any(t.get("role") not in enums.TIER_ROLES for t in tiers):
            return _result(enums.NOT_COMPUTABLE, "step3",
                           "a tier has no role, so replacement and additional "
                           "charges cannot be told apart")
        replacements = [t for t in tiers
                        if t.get("role") == enums.ROLE_REPLACEMENT_PRICE]
        if len(replacements) > 1 and not _tier_ranges_contiguous(replacements):
            return _result(enums.NOT_COMPUTABLE, "step3",
                           "replacement tiers leave a gap or overlap, so some "
                           "stay length has no single price")
        if any(t.get("basis_stated") is not True for t in tiers):
            # 2. A band stating "$50 for 1-4 nights" without saying whether
            #    that is nightly or total is the single commonest shape in the
            #    corpus, and the difference is the price of the trip.
            return _result(enums.CONDITIONALLY_SAFE, "step3",
                           "a tier's basis is not stated, so the amount may be "
                           "nightly or total")

    # 2. A scalar amount with no stated basis is genuinely ambiguous.
    if fee is not None and not tiers and not enums.is_member(
            fee.get("basis") or "", enums.FEE_BASES):
        return _result(enums.CONDITIONALLY_SAFE, "step2",
                       "the fee states an amount with no basis, so it may be "
                       "per night or for the whole stay")

    # 4. Cap integrity. A cap whose scope is unknown bounds nothing knowable:
    #    $150 might cap the room or cap each animal, and for two pets those are
    #    $150 and $300.
    for path, cap in _all_caps(facts):
        if not enums.is_member(cap.get("scope") or "", enums.FEE_SCOPES):
            return _result(enums.COMPUTATION_SAFE_ONE_PET_ONLY, "step4",
                           "%s states no scope, so it cannot bound more than "
                           "one pet" % path)
        if cap.get("qualifier_stated") is not True:
            return _result(enums.COMPUTATION_SAFE_ONE_PET_ONLY, "step4",
                           "%s carries unstated qualifiers" % path)

    limit = facts.get("pet_count_limit")
    has_limit = isinstance(limit, int) and not isinstance(limit, bool) and limit >= 1

    # 7. Multi-rung schedules price each animal separately.
    if schedule is not None:
        entries = [e for e in (schedule.get("entries") or []) if isinstance(e, Mapping)]
        if any(not isinstance(e.get("additive"), bool) for e in entries):
            return _result(enums.NOT_COMPUTABLE, "step7",
                           "a rung does not say whether it is additive, so "
                           "rungs cannot be summed or replaced")
        ordinals = sorted(e.get("pet_ordinal") for e in entries
                          if isinstance(e.get("pet_ordinal"), int)
                          and not isinstance(e.get("pet_ordinal"), bool))
        if has_limit and ordinals == list(range(1, limit + 1)):
            return _result(enums.COMPUTATION_SAFE_ARBITRARY_ALLOWED_PET_COUNT,
                           "step7",
                           "every allowed pet ordinal is priced")
        return _result(enums.COMPUTATION_SAFE_ONE_PET_ONLY, "step7",
                       "the schedule does not price every allowed pet")

    # 5/6. Scope resolution for a scalar or laddered charge.
    scope = (fee or {}).get("scope") if fee is not None else None
    if scope is None and tiers:
        scopes = {t.get("scope") for t in tiers if t.get("scope")}
        scope = scopes.pop() if len(scopes) == 1 else None

    if scope == enums.SCOPE_PER_PET:
        # Price scales with the count, so the count must be bounded or the
        # total is unbounded.
        if has_limit:
            return _result(enums.COMPUTATION_SAFE_ARBITRARY_ALLOWED_PET_COUNT,
                           "step5", "per-pet charge with a stated pet limit")
        return _result(enums.COMPUTATION_SAFE_ONE_PET_ONLY, "step5",
                       "per-pet charge with no stated pet limit")

    if scope == enums.SCOPE_PER_ROOM:
        allowance = (fee or {}).get("scope_pet_allowance")
        if (isinstance(allowance, int) and not isinstance(allowance, bool)
                and has_limit and allowance < limit):
            # "covers up to 2 pets" on a property allowing 3 leaves the third
            # animal unpriced -- the room rate is not the whole answer.
            return _result(enums.CONDITIONALLY_SAFE, "step5",
                           "the room charge covers %d pets but %d are allowed, "
                           "so the remainder is unpriced" % (allowance, limit))
        return _result(enums.COMPUTATION_SAFE_ARBITRARY_ALLOWED_PET_COUNT,
                       "step5", "room-scoped charge covers the allowed pets")

    # 6. Scope absent. The one case where the ambiguity cannot matter is a
    #    single-pet property: at exactly one animal, per-pet and per-room are
    #    the same arithmetic, so nothing a guest sees can change.
    if has_limit and limit == 1:
        return _result(enums.COMPUTATION_SAFE_ARBITRARY_ALLOWED_PET_COUNT,
                       "step6",
                       "one pet allowed, so per-pet and per-room are "
                       "arithmetically identical")
    return _result(enums.COMPUTATION_SAFE_ONE_PET_ONLY, "step6",
                   "the fee states no scope, so a multi-pet total cannot be "
                   "derived")


def classification_disagreements(record: Mapping) -> Tuple[str, ...]:
    """Report a stored ``computation_class`` that recomputation contradicts.

    This is the release-gate half of the persist-and-derive design. A record
    with no stored class is not a disagreement -- it simply has not been
    migrated yet.
    """
    stored = record.get("computation_class")
    if stored is None:
        return ()
    derived = classify(record.get("facts") or {})
    if stored == derived.computation_class:
        return ()
    return ("computation_class stored as %r but recomputes to %r (%s: %s)"
            % (stored, derived.computation_class, derived.rule, derived.reason),)
