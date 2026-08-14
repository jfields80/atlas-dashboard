"""PTF-RENDERER-FIDELITY-001 -- the renderer's window onto canonical policy.

Why this module exists
----------------------
Phase A froze the contracts and proved they read every committed record, but
nothing consumed them: the renderer still read legacy display strings, so
twelve of fourteen committed ``fee_scope`` values reached no public surface and
sixty-six deliberate withholding decisions rendered as generic silence.

This is the adapter that closes that gap. It takes a legacy policy record,
runs it through the Phase A compatibility reader, and exposes exactly what the
renderer needs to tell the truth about it -- canonical fee scope and basis, the
withholding decisions, the weight structure, the species states, and whether a
number may honestly be computed at all.

What it deliberately is NOT
---------------------------
It is not a second normalisation system. Every canonical value here comes from
``contracts.compat_readers``; nothing re-parses a display string that Phase A
has already canonicalised. Where Phase A refuses to guess -- species prose,
tier roles -- this module refuses too, and exposes the legacy value as a
clearly-labelled fallback rather than inventing a canonical one.

It also does not migrate anything. Committed authority stays byte-identical;
this is a read-time view.

The rule that governs every display decision here
-------------------------------------------------
A reader must never be shown a number that the source did not support. When
canonical data cannot back the display the renderer wants, this module says so
and the renderer falls back to an honest uncertainty statement.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, FrozenSet, Iterable, List, Mapping, Optional, Sequence, Tuple

from scripts.pettripfinder.contracts import enums, withholding
from scripts.pettripfinder.contracts.compat_readers import read_record
from scripts.pettripfinder.contracts.fee_computation import classify

# --------------------------------------------------------------------------
# display vocabulary
# --------------------------------------------------------------------------

#: Human wording for each canonical basis. No raw enum ever reaches a reader.
BASIS_WORDS: Dict[str, str] = {
    enums.BASIS_PER_NIGHT: "per night",
    enums.BASIS_PER_DAY: "per day",
    enums.BASIS_PER_STAY: "per stay",
}

#: Human wording for each canonical scope.
SCOPE_WORDS: Dict[str, str] = {
    enums.SCOPE_PER_ROOM: "per room",
    enums.SCOPE_PER_PET: "per pet",
}

#: The sentence a reader gets when a fee states an amount but no scope. The
#: source did not say, so neither do we -- and saying nothing at all would let
#: "$50 per night" read as a complete answer to a guest bringing two dogs.
SCOPE_UNSTATED_NOTE = ("the source does not specify whether this is charged "
                       "per pet or per room")

#: Short labels for the comparison table, where a full sentence will not fit.
#: Never "Not stated" -- that is what silence says, and a withheld field is the
#: opposite of silence.
WITHHELD_SHORT_LABELS: Dict[str, str] = {
    enums.SOURCE_AMBIGUOUS: "Wording unclear",
    enums.SOURCE_CONTRADICTORY: "Conflicting source terms",
    enums.SCHEMA_CANNOT_REPRESENT: "Terms withheld",
    enums.ARTIFACT_INSUFFICIENT: "Terms withheld",
    enums.IDENTITY_NOT_CONFIRMED: "Terms withheld",
}

#: Fallback for a withheld entry whose reason code did not survive migration.
#: Still never the silence copy.
WITHHELD_GENERIC_LABEL = "Terms withheld"
WITHHELD_GENERIC_COPY = ("The hotel's published wording could not be "
                         "summarised accurately.")

#: What a reader is told when a total cannot be defended.
UNCOMPUTABLE_NOTE = ("Exact total cannot be confirmed from the hotel's "
                     "published wording.")

#: Money in prose, used only to DETECT that a record's own wording carries a
#: second relevant amount. It never produces a published number.
#:
#: Three shapes, each requiring evidence that the number is a PRICE:
#:   $150 / 150 USD / 150 dollars    -- an explicit currency marker
#:   charged 50 / fee of 50          -- explicit charge language before it
#:   150 per pet / 50 per night      -- a fee qualifier after it
#:
#: The last two exist because the corpus states real ladders in bare numbers
#: ("Guests will be charged 50 per pet for one to six night stays and 150 per
#: pet for seven plus nights"), and a diagnostic that cannot see the second
#: amount cannot protect a reader from it. They are deliberately narrow: a pet
#: count reads "2 pets" not "2 per pet", and a weight reads "80 pounds", so
#: neither can match.
_PROSE_MONEY_RE = re.compile(
    r"(?<![\d.])(?:"
    r"\$\s*(?P<sym>\d{1,4}(?:\.\d{2})?)"
    r"|(?P<cur>\d{1,4}(?:\.\d{2})?)\s*(?:USD|dollars?)"
    r"|(?:charge[ds]?|fee)\s+(?:of\s+)?(?P<pre>\d{1,4}(?:\.\d{2})?)"
    r"|(?P<post>\d{1,4}(?:\.\d{2})?)\s+per\s+(?:pet|night|day|stay|room)"
    r")",
    re.IGNORECASE)


@dataclass(frozen=True)
class MoneyDisplay:
    """An amount ready to print, with its qualifiers."""

    cents: int
    currency: str
    basis: str = ""
    scope: str = ""
    pet_allowance: int = 0

    @property
    def amount(self) -> str:
        """``$15`` / ``$12.50`` -- trailing cents only when they are not zero.

        The legacy corpus prints ``$50.00`` everywhere; keeping the cents on a
        whole-dollar fee adds noise to every line of every table for nothing.
        """
        whole, cents = divmod(self.cents, 100)
        return "$%d" % whole if cents == 0 else "$%d.%02d" % (whole, cents)

    @property
    def qualifier(self) -> str:
        """``per pet per night`` -- scope first, because scope is what a reader
        bringing two animals needs and what the renderer used to drop."""
        parts = []
        if self.scope:
            parts.append(SCOPE_WORDS.get(self.scope, ""))
        if self.basis:
            parts.append(BASIS_WORDS.get(self.basis, ""))
        return " ".join(p for p in parts if p)

    @property
    def phrase(self) -> str:
        """``$15 per pet per night``."""
        qualifier = self.qualifier
        return "%s %s" % (self.amount, qualifier) if qualifier else self.amount

    @property
    def scope_is_unstated(self) -> bool:
        return not self.scope


def _money_display(node: Optional[Mapping]) -> Optional[MoneyDisplay]:
    if not isinstance(node, Mapping) or "amount_cents" not in node:
        return None
    return MoneyDisplay(
        cents=int(node["amount_cents"]),
        currency=str(node.get("currency") or "USD"),
        basis=str(node.get("basis") or ""),
        scope=str(node.get("scope") or ""),
        pet_allowance=int(node.get("scope_pet_allowance") or 0),
    )


def _prose_amounts(text: str) -> Tuple[Decimal, ...]:
    """Distinct money amounts appearing in prose.

    Used ONLY as a diagnostic: if a record publishes one scalar fee while its
    own restriction wording names a different amount, the scalar is not the
    whole story and must not be shown as though it were. Nothing here is ever
    published as a price.
    """
    found: List[Decimal] = []
    for match in _PROSE_MONEY_RE.finditer(text or ""):
        raw = (match.group("sym") or match.group("cur") or match.group("pre")
               or match.group("post"))
        try:
            value = Decimal(raw)
        except Exception:                                  # pragma: no cover
            continue
        if value > 0 and value not in found:
            found.append(value)
    return tuple(found)


@dataclass(frozen=True)
class CanonicalView:
    """Everything the renderer needs to describe one property honestly."""

    facts: Mapping                      # canonical 1.2 facts
    legacy_facts: Mapping               # the committed record, for fallbacks
    withheld: Mapping                   # path -> canonical withheld entry
    computation_class: str
    computation_reason: str
    service_animal: Mapping
    review_codes: FrozenSet[str]

    # ---------------------------------------------------------------- fees

    @property
    def fee(self) -> Optional[MoneyDisplay]:
        return _money_display(self.facts.get("pet_fee"))

    @property
    def tiers(self) -> Tuple[Mapping, ...]:
        return tuple(self.facts.get("fee_tiers") or ())

    @property
    def cap(self) -> Optional[Mapping]:
        cap = self.facts.get("fee_cap")
        return cap if isinstance(cap, Mapping) else None

    @property
    def pet_schedule_entries(self) -> Tuple[Mapping, ...]:
        schedule = self.facts.get("fee_pet_schedule")
        if not isinstance(schedule, Mapping):
            return ()
        return tuple(e for e in (schedule.get("entries") or ())
                     if isinstance(e, Mapping))

    @property
    def may_compute_multi_pet_total(self) -> bool:
        return self.computation_class in enums.COMPUTABLE_FOR_MANY_PETS

    @property
    def may_compute_single_pet_total(self) -> bool:
        return self.computation_class in enums.COMPUTABLE_FOR_ONE_PET

    @property
    def scalar_fee_is_complete(self) -> bool:
        """Whether a single printed amount is the whole answer.

        Two independent ways it can fail, and the corpus contains both:

        * the computation contract cannot defend a total at all -- a fee with
          no stated basis may be the night or the stay, and the difference is
          the price of the trip;
        * the record's own wording names a second, larger amount that never
          reached a structured field. Staybridge Suites Miamisburg publishes a
          $50 scalar while its restriction text says $50 per pet for one to six
          nights and $150 per pet for seven or more. Showing $50 as the fee is
          not a rounding error, it is a different product.
        """
        if self.fee is None:
            return False
        if self.computation_class in (enums.CONDITIONALLY_SAFE,
                                      enums.NOT_COMPUTABLE):
            return False
        return not self.has_undeclared_second_amount

    @property
    def fee_display_mode(self) -> str:
        """How much weight a printed scalar fee may carry.

        Three outcomes, because the corpus has three genuinely different
        problems and one response to all of them would be wrong:

        ``withhold_scalar``
            No single number may be printed as the fee, because printing one
            would be actively misleading. Either the fee is withheld, or the
            record's own wording names a LARGER amount that never reached a
            structured field. Staybridge Suites Miamisburg states $50 while its
            restriction text says $50 per pet for one to six nights and $150
            per pet for seven or more: "$50" is a different product, not a
            rounded one.
        ``qualified``
            The stated amount is true as far as it goes but is not the whole
            answer, so it is shown WITH the caveat that makes it honest -- an
            amount whose basis the source never gave, or a per-stay fee the
            source then says attracts tax.
        ``complete``
            The scalar is the whole answer.

        Note what is deliberately NOT withheld: an amount with no stated basis.
        The renderer already says "a $50 pet fee is stated; the fee basis is
        not specified", which is both honest and more useful than hiding the
        number, and fifteen committed records depend on it. Suppressing them
        would make the site less informative in the name of accuracy.
        """
        if self.fee is None or self.fee_is_withheld:
            return "withhold_scalar"
        if self.has_undeclared_second_amount:
            return "withhold_scalar"
        if self.states_tax_on_fee:
            return "qualified"
        if self.computation_class in (enums.CONDITIONALLY_SAFE,
                                      enums.NOT_COMPUTABLE):
            return "qualified"
        return "complete"

    @property
    def _fee_prose(self) -> str:
        return " ".join(str(self.legacy_facts.get(key) or "")
                        for key in ("general_restrictions", "breed_restrictions",
                                    "reservation_requirement", "unattended_policy"))

    @property
    def states_tax_on_fee(self) -> bool:
        """The record says its fee attracts tax.

        This is the canonical ``tax_relationship: plus_tax`` concept arriving
        as prose because no structured field carried it. It matters here
        because a tax-inclusive restatement is the SAME fee, not a second one:
        Courtyard Springfield's "USD 75 + 17.25% tax ($87.94)" describes one
        $75 charge, and hiding the $75 would remove a true fee to avoid an
        arithmetic a note can explain.
        """
        return "tax" in self._fee_prose.lower()

    @property
    def has_undeclared_second_amount(self) -> bool:
        """A larger, DIFFERENT amount in the prose that no structured field carries.

        Excludes the tax restatement above, which is the same fee seen after
        tax rather than another charge.
        """
        fee = self.fee
        if fee is None or self.tiers or self.pet_schedule_entries:
            return False
        if self.states_tax_on_fee:
            return False
        structured = {Decimal(fee.cents) / 100}
        cap = self.cap
        if cap and "amount_cents" in cap:
            structured.add(Decimal(int(cap["amount_cents"])) / 100)
        return any(amount not in structured and amount > max(structured)
                   for amount in _prose_amounts(self._fee_prose))

    # ------------------------------------------------------------ withheld

    def render_state(self, path: str) -> str:
        """``stated`` | ``withheld`` | ``not_stated`` for one field path."""
        return withholding.render_state(
            {"facts": self.facts, "withheld_fields": self.withheld}, path)

    def is_withheld(self, path: str) -> bool:
        return path in self.withheld

    def withheld_reason_code(self, path: str) -> str:
        entry = self.withheld.get(path) or {}
        return str(entry.get("reason_code") or "")

    def withheld_copy(self, path: str) -> str:
        """The sentence a visitor reads for a withheld field.

        Never the silence copy: "Not stated" says the hotel was silent, and a
        withheld field means the opposite -- the hotel spoke, and what it said
        could not be published accurately.
        """
        code = self.withheld_reason_code(path)
        return withholding.PUBLIC_COPY.get(code) or WITHHELD_GENERIC_COPY

    def withheld_label(self, path: str) -> str:
        """The short comparison-table label for a withheld field."""
        code = self.withheld_reason_code(path)
        return WITHHELD_SHORT_LABELS.get(code, WITHHELD_GENERIC_LABEL)

    @property
    def fee_is_withheld(self) -> bool:
        return any(p == "pet_fee" or p.startswith("pet_fee.")
                   for p in self.withheld)

    # --------------------------------------------------------------- size

    @property
    def weight_individual(self) -> Optional[Mapping]:
        limit = self.facts.get("weight_limit")
        return limit if isinstance(limit, Mapping) else None

    @property
    def weight_combined(self) -> Optional[Mapping]:
        limit = self.facts.get("combined_weight_limit")
        return limit if isinstance(limit, Mapping) else None

    @property
    def weight_stated_none(self) -> bool:
        return self.facts.get("weight_limit_stated_none") is True

    @property
    def species_weight_limits(self) -> Mapping:
        limits = self.facts.get("species_weight_limits")
        return limits if isinstance(limits, Mapping) else {}

    # ------------------------------------------------------------ species

    @property
    def cats_state(self) -> str:
        """``accepted`` | ``prohibited`` | ``""``.

        ``cats_allowed`` is a committed boolean and is mechanically safe to
        read. The prose ``species_allowed`` field is NOT parsed into a state
        here -- Phase A refuses to, because a page naming only "pets" must
        yield no species at all rather than dogs+cats -- but a prose value that
        explicitly names cats is an affirmative mention and is honoured.
        """
        explicit = self.legacy_facts.get("cats_allowed")
        if explicit == "false" or explicit is False:
            return enums.SPECIES_PROHIBITED
        if explicit == "true" or explicit is True:
            return enums.SPECIES_ACCEPTED
        if "cat" in str(self.legacy_facts.get("species_allowed") or "").lower():
            return enums.SPECIES_ACCEPTED
        return ""

    @property
    def dogs_state(self) -> str:
        if "dog" in str(self.legacy_facts.get("species_allowed") or "").lower():
            return enums.SPECIES_ACCEPTED
        return ""

    # ----------------------------------------------------- service animals

    @property
    def has_service_animal_statement(self) -> bool:
        return bool(self.service_animal.get("stated"))


def build(facts_entry: Optional[Mapping], *, market_id: str = "") -> CanonicalView:
    """Build the canonical view of one committed policy record.

    Accepts the legacy record shape the renderer already receives, so call
    sites need only pass what they already hold.
    """
    entry = facts_entry or {}
    legacy_facts = entry.get("facts") or {}
    result = read_record(entry, market_id=market_id)
    canonical = result.record.get("facts") or {}

    # The classifier needs to know the fee was withheld; the canonical record
    # carries that in withheld_fields, and this is the agreed channel for it.
    withheld = result.record.get("withheld_fields") or {}
    for_classification = dict(canonical)
    withheld_fee_paths = tuple(p for p in withheld
                               if p == "pet_fee" or p.startswith("pet_fee."))
    if withheld_fee_paths:
        for_classification["_withheld_fee_paths"] = withheld_fee_paths
    classification = classify(for_classification)

    return CanonicalView(
        facts=canonical,
        legacy_facts=legacy_facts,
        withheld=withheld,
        computation_class=classification.computation_class,
        computation_reason=classification.reason,
        service_animal=result.record.get("service_animal_statement") or {},
        review_codes=frozenset(item.code for item in result.review),
    )


def fee_phrase(view: CanonicalView) -> str:
    """The property's scalar fee as a reader should see it, or ``""``.

    Returns the empty string when a scalar must not be shown -- a laddered,
    withheld, or incompletely-stated fee is not a single number, and printing
    one anyway is the defect this whole phase exists to fix.
    """
    fee = view.fee
    if fee is None or view.fee_is_withheld:
        return ""
    return fee.phrase


def fee_scope_note(view: CanonicalView) -> str:
    """The sentence to add when a fee states an amount but no scope."""
    fee = view.fee
    if fee is None or not fee.scope_is_unstated or view.fee_is_withheld:
        return ""
    return SCOPE_UNSTATED_NOTE


def weight_sentence(limit: Mapping, *, subject: str = "Each pet") -> str:
    """``Each pet must weigh under 80 pounds`` / ``... up to 50 pounds``.

    The operator is load-bearing: "under 80 pounds" turns an eighty-pound dog
    away and "up to 80 pounds" takes it, and the corpus contains both.
    """
    value = limit.get("value")
    unit = "pounds" if limit.get("unit") == enums.UNIT_LB else "kilograms"
    number = ("%d" % value) if float(value) == int(value) else ("%s" % value)
    if limit.get("operator") == enums.OP_LT:
        return "%s must weigh under %s %s" % (subject, number, unit)
    return "%s may weigh up to %s %s" % (subject, number, unit)


def weight_display(limit: Mapping) -> str:
    """Table form: ``Under 80 lb`` / ``80 lb``."""
    value = limit.get("value")
    unit = str(limit.get("unit") or enums.UNIT_LB)
    number = ("%d" % value) if float(value) == int(value) else ("%s" % value)
    if limit.get("operator") == enums.OP_LT:
        return "Under %s %s" % (number, unit)
    return "%s %s" % (number, unit)
