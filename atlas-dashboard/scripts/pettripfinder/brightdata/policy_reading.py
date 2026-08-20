"""Reading a policy block written by someone other than Marriott.

``marriott_surface`` reads one brand's labelled rows and is frozen: the
committed PTF-BRIGHTDATA-MARRIOTT-PILOT-001 report was produced by it and must
stay reproducible. This module is its generalisation, and it IMPORTS that
module's patterns rather than restating them, so the Marriott shapes have one
definition and the cross-brand pilot cannot drift away from the run it is
being compared against.

WHAT GENERALISES AND WHAT DOES NOT
----------------------------------
Across this corpus the chains say the same things in different word orders:

    Non-Refundable Pet Fee Per Stay: $150.00      (Marriott, labelled row)
    $75 non-refundable fee per stay              (Hilton, prose)
    $25 per pet, per night                       (Choice / Wyndham)
    2 pets per room, up to 75 lbs each           (La Quinta)
    Maximum 2 pets per room                      (IHG)

So the patterns below are ADDITIVE and every one of them is anchored on words
the source actually wrote. What does not generalise is interpretation, and none
is attempted: this module still emits no weight comparison operator, still
treats a generic "pets welcome" as naming no species, and still refuses to pick
between two bases stated for one amount.

ONE THING THIS READS THAT MARRIOTT'S DOES NOT
---------------------------------------------
``fee_scope``. Marriott's rows never state it, so the Marriott reader was right
to leave it absent. Several other brands write "per pet" or "per room" INTO the
charge itself, and where the source says it, recording it is transcription
rather than inference. Where the source is silent it stays absent, which is the
same rule as before applied to a page that says more.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.brightdata import marriott_surface as MS  # noqa: E402
from scripts.pettripfinder.contracts import enums                    # noqa: E402

collapse = MS.collapse

_BASIS_BY_WORD = {"stay": enums.BASIS_PER_STAY, "night": enums.BASIS_PER_NIGHT,
                  "nightly": enums.BASIS_PER_NIGHT, "day": enums.BASIS_PER_DAY,
                  "daily": enums.BASIS_PER_DAY}

_SCOPE_BY_WORD = {"pet": enums.SCOPE_PER_PET, "animal": enums.SCOPE_PER_PET,
                  "room": enums.SCOPE_PER_ROOM, "reservation": enums.SCOPE_PER_ROOM}

#: An amount with its own scope and basis words attached, in either order:
#: "$25 per pet per night", "$25 per night per pet", "$25 per pet, per night".
_SCOPED_CHARGE_RE = re.compile(
    r"\$\s*(?P<amount>[\d,]+(?:\.\d{1,2})?)\s*"
    r"(?:(?:per|/|a)\s*(?P<first>pet|animal|room|reservation|night|day|stay|"
    r"nightly|daily)\b[\s,]*)"
    r"(?:(?:per|/|a)\s*(?P<second>pet|animal|room|reservation|night|day|stay|"
    r"nightly|daily)\b)?",
    re.IGNORECASE)

#: An amount whose basis words sit a few words later: "$75 non-refundable fee
#: per stay", "$50 pet fee per night". Bounded to four intervening words and
#: forbidden from crossing a full stop or another amount, so it cannot pair a
#: price in one sentence with a basis in the next.
_LOOSE_CHARGE_RE = re.compile(
    r"\$\s*(?P<amount>[\d,]+(?:\.\d{1,2})?)\s*"
    r"(?P<gap>(?:[A-Za-z][\w-]*\s+){0,4})"
    r"(?:per|/|a)\s*(?P<basis>night|day|stay|nightly|daily)\b",
    re.IGNORECASE)

#: The same charge written without a dollar sign. Wyndham writes "25 USD per
#: pet per night" and "Non-refundable 15 USD nightly per pet"; the basis and the
#: scope words can arrive in either order, exactly as in the dollar form.
_SCOPED_CHARGE_USD_RE = re.compile(
    r"(?P<amount>[\d,]+(?:\.\d{1,2})?)\s*USD\b[\s,]*"
    r"(?:(?:per|/|a)\s*)?(?P<first>pet|animal|room|reservation|night|day|stay|"
    r"nightly|daily)\b[\s,.]*"
    r"(?:(?:per|/|a)\s*)?(?P<second>pet|animal|room|reservation|night|day|stay|"
    r"nightly|daily)?\b",
    re.IGNORECASE)

#: A bare decimal amount with a basis: Choice writes "50.00 per stay". Explicit
#: cents are REQUIRED -- without them "2 per room" and "50 pounds" would read as
#: prices, which is the room-rate mistake in a cheaper costume.
_BARE_CHARGE_RE = re.compile(
    r"(?P<amount>[\d,]+\.\d{2})\s*(?:per|/|a)\s*"
    r"(?P<basis>night|day|stay|nightly|daily)\b",
    re.IGNORECASE)

#: An amount a brand labels a fee or deposit WITHOUT stating a basis. Hilton's
#: structured row reads "Deposit Yes. $75.00 Non-refundable Fee" and says
#: nothing about per-night or per-stay. The amount is a fact; the basis is not,
#: and is left absent rather than guessed.
#: ``of`` added by PTF-GENERIC-READER-HARDENING-AND-SOURCE-WIRING-016. "A
#: one-time pet fee of $150 is non-refundable" states the amount as plainly as
#: "Pet Fee: $150" does, and the only thing standing between them was the
#: connector word. An optional token cannot change what already matched.
_LABELLED_AMOUNT_RE = re.compile(
    r"(?:(?P<pre>fee|deposit|charge)\s*(?:of\s+)?:?\s*)?"
    r"(?:\$\s*(?P<dollars>[\d,]+(?:\.\d{1,2})?)|"
    r"(?P<usd>[\d,]+(?:\.\d{1,2})?)\s*USD\b)"
    r"(?:\s*(?P<post>[a-z-]*\s*(?:fee|deposit|charge)))?",
    re.IGNORECASE)

#: A stated ceiling: "Max 75 USD per stay". Recorded as ``fee_cap``, never as
#: the price -- the founder rule is CEILING != PRICE.
_FEE_CAP_RE = re.compile(
    # "not to exceed 7 nights or $105 per pet per stay" states two ceilings in
    # one breath -- a length and a price -- and the money one is the fee cap.
    # The length clause is stepped over rather than read: the published
    # vocabulary has a ``fee_cap`` and no field for a maximum number of nights,
    # and inventing one here would be this layer deciding what the schema holds.
    r"\b(?:max(?:imum)?|not\s+to\s+exceed)\s*(?:of\s*)?"
    r"(?:\d+\s+(?:nights?|days?)\s+or\s+)?"
    r"(?:\$\s*(?P<dollars>[\d,]+(?:\.\d{1,2})?)|"
    r"(?P<usd>[\d,]+(?:\.\d{1,2})?)\s*USD\b)"
    # "not to exceed ... $105 per pet per stay" states the ceiling's SCOPE
    # before its basis. The scope word is stepped over rather than read: a cap
    # is recorded with the basis the surface gives it, and inventing a scope
    # for it is not this layer's job.
    r"\s*(?:(?:per|/|a)\s*(?:pet|animal|room|reservation)\s*,?\s*)?"
    r"(?:per|/|a)\s*(?P<basis>night|day|stay)\b",
    re.IGNORECASE)

#: Word numbers, only where a pet count is being named.
_WORD_NUMBERS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}

#: "dogs and cats only", "dog or cat only", "dogs/cats only", "dogs & cats
#: only", "Cats and dogs only". Every one names BOTH species, which is what
#: distinguishes it from a generic "pets welcome" that names none.
#: A species-labelled acceptance row: "Dogs Allowed - 2 dogs max." Names the
#: species as surely as "Dogs Only" does, without the exclusivity.
_DOGS_LABELLED_RE = re.compile(
    r"\b(?:dogs?|cats?)\s+(?:are\s+)?(?:allowed|welcome|permitted)\b",
    re.IGNORECASE)

_BOTH_SPECIES_RE = re.compile(
    r"\b(?:dogs?|cats?)\s*(?:and|&|/|or)\s*(?:dogs?|cats?)\s+only\b",
    re.IGNORECASE)

#: The same two species named as a parenthetical gloss on the word "pet": "a
#: maximum of 2 pets (dogs or cats) per room", "one domestic pet (cat or dog)".
#: The parenthesis is the property saying which animals its word "pet" covers,
#: which is the same transcription as "dogs and cats only" and not an inference
#: from silence. Three measured surfaces write it this way and none of them
#: uses the word "only", which is the only thing the pattern above required.
_SPECIES_PAIR_RE = re.compile(
    r"\b(?:pets?|animals?)\s*\(\s*(?:dogs?|cats?)\s*(?:and|&|/|or)\s*"
    r"(?:dogs?|cats?)\s*\)", re.IGNORECASE)

#: "non-refundable ... $75" or "$75 ... non-refundable", within one statement.
_NONREFUNDABLE_RE = re.compile(r"non-?\s?refundable", re.IGNORECASE)
_REFUNDABLE_RE = re.compile(r"(?<!non-)(?<!non )\brefundable\b", re.IGNORECASE)

#: Counts. Every form here names pets explicitly; a bare number is never read.
_COUNT_RES: Tuple[re.Pattern, ...] = (
    MS._COUNT_RE,
    re.compile(r"(?:up\s+to|maximum(?:\s+of)?|max\.?|no\s+more\s+than)\s+"
               r"(?P<count>\d+)\s+pets?\b", re.IGNORECASE),
    re.compile(r"(?P<count>\d+)\s+pets?\s+(?:are\s+)?(?:allowed\s+)?per\s+"
               r"(?P<scope>room|reservation|suite)\b", re.IGNORECASE),
    re.compile(r"limit\s+(?:of\s+)?(?P<count>\d+)\s+pets?\b", re.IGNORECASE),
    re.compile(r"(?:one|1)\s+(?:well-behaved\s+)?(?:family\s+)?pet\s+per\s+"
               r"(?P<scope>room)\b", re.IGNORECASE),
    # Hilton and Wyndham both put the number first: "2 pets max", "2pets Max",
    # "2 dogs max", "Two pets max per room".
    re.compile(r"\b(?P<count>\d+)\s*(?:pets?|dogs?|cats?)\s+max(?:imum)?\b"
               r"(?:\s+per\s+(?P<scope>room|reservation|suite))?",
               re.IGNORECASE),
    re.compile(r"\b(?P<word>one|two|three|four|five)\s+pets?\s+max(?:imum)?\b"
               r"(?:\s+per\s+(?P<scope>room|reservation|suite))?",
               re.IGNORECASE),
    # Choice: "Maximum of two pets per room".
    re.compile(r"max(?:imum)?\s+of\s+(?P<word>one|two|three|four|five)\s+"
               r"pets?\s+per\s+(?P<scope>room|reservation|suite)\b",
               re.IGNORECASE),
    re.compile(r"max(?:imum)?\s+(?:of\s+)?(?P<count>\d+)\s+pets?\s+per\s+"
               r"(?P<scope>room|reservation|suite)\b", re.IGNORECASE),
    # "a maximum of two (2) dogs per room policy". Two additions, each of which
    # the reader already accepts elsewhere: the species may be named instead of
    # the word "pet" -- ``_DOGS_LABELLED_RE`` treats "Dogs Allowed" as an
    # acceptance for exactly that reason -- and a property that writes the
    # number twice, as a word and then in figures, has still stated it once.
    re.compile(r"max(?:imum)?\s+of\s+(?P<word>one|two|three|four|five)\s*"
               r"(?:\(\s*\d+\s*\)\s*)?(?:pets?|dogs?|cats?)\s+per\s+"
               r"(?P<scope>room|reservation|suite)\b", re.IGNORECASE),
    re.compile(r"max(?:imum)?\s+of\s+(?P<count>\d+)\s*"
               r"(?:pets?|dogs?|cats?)\s+per\s+"
               r"(?P<scope>room|reservation|suite)\b", re.IGNORECASE),
)

#: Weights. "up to", "under", "or less" and "maximum" are all recorded as a
#: VALUE and never as a comparison operator -- the corpus rule is unchanged.
_WEIGHT_RES: Tuple[re.Pattern, ...] = (
    MS._WEIGHT_RE,
    # Hilton's table row. Listed before the loose forms because "75 lbs Max" in
    # "Max weight 75 lbs Max size Medium" otherwise matched by accident, taking
    # the right number for the wrong reason.
    # ``of`` added by PTF-POLICY-READER-TIERED-FEE-HARDENING-010. Surfaces
    # writing "a maximum weight of 40lbs" or "a max weight of 50 lbs" were
    # missed, and the only thing between those and this pattern was the
    # connector word. An optional token cannot change what already matched.
    re.compile(r"max(?:imum)?\s+(?:pet\s+)?weight\s+(?:of\s+)?:?\s*"
               r"(?P<value>[\d,]+(?:\.\d+)?)\s*(?P<unit>lbs?|pounds?|kgs?)\b",
               re.IGNORECASE),
    # Choice: "Maximum 50 pounds each".
    re.compile(r"max(?:imum)?\s+(?:of\s+)?(?P<value>[\d,]+(?:\.\d+)?)\s*"
               r"(?P<unit>lbs?|pounds?|kgs?)\s+each\b", re.IGNORECASE),
    re.compile(r"(?:up\s+to|under|less\s+than|maximum(?:\s+of)?|max\.?)\s+"
               r"(?P<value>[\d,]+(?:\.\d+)?)\s*(?P<unit>lbs?|pounds?|kgs?)\b",
               re.IGNORECASE),
    re.compile(r"(?P<value>[\d,]+(?:\.\d+)?)\s*(?P<unit>lbs?|pounds?|kgs?)\s+"
               r"(?:or\s+less|maximum|max\.?|and\s+under)\b", re.IGNORECASE),
    re.compile(r"pets?\s+(?:weighing\s+)?(?:up\s+to\s+)?"
               r"(?P<value>[\d,]+(?:\.\d+)?)\s*(?P<unit>lbs?|pounds?|kgs?)\b",
               re.IGNORECASE),
    # "Pet not to exceed 80 pounds." A ceiling written as a prohibition rather
    # than as a maximum. Recorded as a VALUE like every other form here: the
    # comparison operator is still never inferred.
    re.compile(r"(?:not\s+to\s+exceed|cannot\s+exceed|may\s+not\s+exceed|"
               r"no\s+more\s+than)\s+(?P<value>[\d,]+(?:\.\d+)?)\s*"
               r"(?P<unit>lbs?|pounds?|kgs?)\b", re.IGNORECASE),
)

_PETS_WELCOME_RES: Tuple[re.Pattern, ...] = (
    MS._PETS_WELCOME_RE,
    re.compile(r"\bpets?\s+(?:are\s+)?(?:welcome|allowed|permitted)\b",
               re.IGNORECASE),
    re.compile(r"\bwe\s+welcome\s+pets?\b", re.IGNORECASE),
    # "pet friendly", and the species-named forms of the same claim. A
    # measured surface calls itself "a dog friendly hotel" and prices dogs in
    # the next sentence; the reader accepted the phrase only when the word was
    # "pet".
    re.compile(r"\b(?:pet|dog|cat)[\s-]friendly\b", re.IGNORECASE),
    re.compile(r"\bwe\s+accept\s+(?:all\s+)?(?:pets?|dogs?|cats?)\b",
               re.IGNORECASE),
    # "A maximum of 2 pets (dogs or cats) per room are allowed at this
    # hotel." The subject and its verb are separated by the property's own
    # qualifiers, exactly as in the "is welcome" form above. The gap is bounded
    # AND may not contain a negation: ``_is_negated`` only looks BACK from the
    # match, so "pets ... are not allowed" would otherwise read as acceptance.
    re.compile(r"\bpets?\s+(?:(?!\bnot\b|\bnever\b|\bno\b)[\w(),&/-]+\s+){0,5}"
               r"(?:is|are)\s+(?:allowed|permitted|welcome)\b", re.IGNORECASE),
    # "One well-behaved family pet per room is welcome" (Red Roof). The subject
    # and the verb are separated by whatever qualifiers the property wrote, so
    # the gap is bounded rather than forbidden.
    re.compile(r"\bpets?\s+(?:[a-z][\w-]*\s+){0,4}(?:is|are)\s+welcome\b",
               re.IGNORECASE),
    # Wyndham labels the row by species: "Dogs Allowed - 2 dogs max." A
    # brand that says which animal it takes has said that it takes animals.
    _DOGS_LABELLED_RE,
    # "... welcomes dogs only." The reader already accepts "we
    # welcome pets"; a property that welcomes an ANIMAL BY NAME has said the
    # same thing, and the negation guard still governs this like every other
    # acceptance here.
    re.compile(r"\bwelcomes?\s+(?:only\s+)?(?:pets?|dogs?|cats?)\b",
               re.IGNORECASE),
)

#: Continuations that turn a refusal into a HOUSE RULE rather than a refusal of
#: pets. Hotel Indigo Pittsburgh writes "Pets are not allowed to be left alone
#: in room" on a page that also says "Pets are welcome"; without this the reader
#: saw a blanket refusal, called the surface self-contradictory, and withheld
#: everything. The conservative outcome was safe -- it published nothing wrong --
#: but it lost a whole capture to a sentence about unattended animals.
_REFUSAL_QUALIFIER = (
    r"(?!\s+(?:to\s+be\s+left|to\s+remain|unattended|alone|"
    r"in\s+(?:the\s+)?(?:room|rooms|lobby|restaurant|pool|dining|fitness|spa|"
    r"breakfast|elevator|bar|kitchen|suite)|"
    r"on\s+(?:the\s+)?(?:bed|beds|furniture|balcony))\b)")

_PETS_REFUSED_RES: Tuple[re.Pattern, ...] = (
    # The Marriott alternation, reused as SOURCE rather than restated, with the
    # house-rule qualifier appended. Rebuilding it from ``.pattern`` keeps one
    # definition of the refusal wordings while letting the general reader be
    # stricter than the frozen one about what follows them.
    re.compile(MS._PETS_REFUSED_RE.pattern + _REFUSAL_QUALIFIER, re.IGNORECASE),
    re.compile(r"\bpets?\s*:?\s*(?:are\s+)?not\s+(?:allowed|permitted|accepted)\b"
               + _REFUSAL_QUALIFIER, re.IGNORECASE),
    re.compile(r"\bno\s+(?:other\s+|additional\s+|further\s+)?pets?\b"
               r"(?!\s+(?:allowed\s+)?fee)", re.IGNORECASE),
    re.compile(r"\bpets?\s+allowed\s*:?\s*no\b", re.IGNORECASE),
)

#: A condition attached to a charge that schema 1.2 has no field for: a fee
#: that applies only to pets above a weight, or only in some circumstance. The
#: amount is real and its APPLICABILITY is not representable, so publishing the
#: amount alone would assert a charge for every pet.
_CONDITIONAL_FEE_RE = re.compile(
    r"\d+\s*(?:lbs?|pounds?|kgs?)\s+(?:or|and)\s+(?:over|more|above|up|greater)"
    r"|\bfor\s+pets?\s+(?:over|above|under|below)\b"
    r"|\bif\s+(?:the\s+)?pets?\b"
    r"|\bpets?\s+(?:over|above)\s+\d+\s*(?:lbs?|pounds?)"
    # A PENALTY, not a price. "Unauthorized pets incur a $250 cleaning fee" on
    # a surface that accepts no pets at all states what happens when the rule
    # is broken; publishing it as the pet fee would tell a guest that this
    # hotel charges $250 to bring a dog, which is not what it says. The amount
    # is real and its applicability -- only to a violation -- has no field.
    r"|\b(?:unauthori[sz]ed|unregistered|undeclared|undisclosed)\s+pets?\b",
    re.IGNORECASE)

#: How far from the charge the condition may sit and still govern it.
_CONDITION_WINDOW_CHARS = 60

#: A price that applies only to SOME stays, or SOME pet counts, with a
#: different price for the rest. Added by
#: PTF-POLICY-READER-TIERED-FEE-HARDENING-010.
#:
#: Deliberately narrow. A bare mention of a pet count is NOT a tier: a surface
#: reading "Non-refundable 25 USD nightly for up to 2 pets. Max 75 USD per
#: stay" is a capped per-night fee this vocabulary already holds correctly, and
#: a loose count pattern would withhold it for nothing. So the count form
#: requires a PRICE adjacent to the count ("25USD 2 dogs") rather than any
#: reference to a number of pets.
_TIERED_FEE_RE = re.compile(
    r"\bfor\s+(?:a\s+)?stays?\s+(?:of\s+)?\d+\s*(?:to|-|through)\s*\d+"
    r"|\bfor\s+stays?\s+(?:of\s+)?(?:over|above|more\s+than|under|less\s+than)\s+\d+"
    r"|\bfor\s+a\s+\d+\s*(?:to|-)\s*\d+\s*night"
    r"|\bfor\s+\d+\s*(?:to|-)\s*\d+\s*nights?\b"
    r"|\b\d+\s*(?:to|-)\s*\d+\s*nights?\s+the\s+fee\b"
    r"|\b\d+\s*or\s+more\s+will\s+be\b"
    r"|\b\d+\s*(?:usd|dollars?)\s+\d+\s+(?:dogs?|cats?|pets?)\b"
    r"|\b(?:weekly|monthly)\s+\d+\s*(?:usd|dollars?)?\s*\d*\s*(?:dogs?|pets?)\b"
    # Priced by WHICH pet: "One domestic pet stays free. Second pet $15 per
    # night." The published vocabulary holds one amount with one scope, and
    # neither "$15 per pet" nor "$0 per pet" is what this surface says.
    r"|\b(?:second|2nd|third|3rd|each\s+additional|additional)\s+"
    r"(?:pets?|dogs?|cats?)\b"
    # Priced by ROOM CLASS: "$20 per dog per night ($30/dog/night in Suites)".
    # The same defect family as pricing by stay length -- one pet, two prices,
    # and the schema has nowhere to say which room the guest booked.
    r"|\bin\s+(?:suites?|studios?|villas?|cabins?|cottages?)\b",
    re.IGNORECASE)

#: Two or more DISTINCT prices on the surface. A tier needs both this and the
#: qualifier above: a cap has two prices and no qualifier, and a single-priced
#: policy that mentions a night range has a qualifier and one price. Neither is
#: a tier, and withholding either would lose a fact the schema can hold.
_PRICE_RE = re.compile(
    r"\$\s*\d+(?:[.,]\d{2})?|\b\d+(?:[.,]\d{2})?\s*(?:usd|dollars?)\b",
    re.IGNORECASE)


def _fee_is_tiered(block_text: str) -> bool:
    """Does this surface price the same pet differently by stay or by count?"""
    if not _TIERED_FEE_RE.search(block_text):
        return False
    prices = {re.sub(r"[^\d.]", "", m.group(0))
              for m in _PRICE_RE.finditer(block_text)}
    return len({p for p in prices if p}) > 1

#: Chain-wide phrasing. A sentence about every hotel in the brand is not this
#: property's policy; membrane rule M3 keeps the two apart and this is how a
#: reading says which one it is holding.
_BRAND_GENERIC_RE = re.compile(
    r"\ball\s+(?:of\s+)?our\s+(?:hotels|properties|locations)\b"
    r"|\ball\s+locations\b|\bmost\s+of\s+our\b"
    r"|\bvaries\s+by\s+(?:hotel|location|property)\b"
    r"|\bat\s+all\s+\w{0,12}\s?hotels\b", re.IGNORECASE)

_UNIT_CANON = {"lb": enums.UNIT_LB, "lbs": enums.UNIT_LB,
               "pound": enums.UNIT_LB, "pounds": enums.UNIT_LB,
               "kg": enums.UNIT_KG, "kgs": enums.UNIT_KG}


#: How far from an amount pet wording may sit and still be about that amount.
#: Wide enough for "Non-Refundable Pet Fee Per Stay: $150.00" and for "$25 per
#: night, per pet"; far too narrow to reach from a guest-room rate to the pet
#: line further down the same card.
_PET_CONTEXT_CHARS = 70

_PET_CONTEXT_RE = re.compile(r"\bpets?\b|\banimals?\b|\bdogs?\b|\bcats?\b",
                             re.IGNORECASE)

#: The longest a service-animal statement may be before it stops being a
#: sentence and starts being a page section.
_MAX_SERVICE_ANIMAL_CHARS = 300


def _amount_minor(text: str) -> int:
    return int(round(float(text.replace(",", "")) * 100))


#: Words that introduce a price belonging to something other than a pet. If one
#: of these stands between the nearest pet word and the amount, the amount was
#: introduced by the rate, not by the pet policy.
_RATE_MARKER_RE = re.compile(
    r"\b(?:rate|rates|price|prices|total|subtotal|avg|average|starting|"
    r"from|nightly\s+rate|room\s+rate|member\s+rate|discounted)\b",
    re.IGNORECASE)

#: A charge whose own sentence names a purpose that is not a pet. "for
#: incidentals", "for all guests" -- the surface has said who pays it, and it
#: is everyone.
_NON_PET_PURPOSE_RE = re.compile(
    r"\bincidental(?:s)?\b|\bfor\s+all\s+guests\b|\ball\s+guests\b",
    re.IGNORECASE)


def _pet_context(text: str, start: int, end: int) -> bool:
    """Whether an amount BELONGS to the pet statement, not merely sits near it.

    A price on a hotel page is a room rate until the page associates it with an
    animal. Choice's guest-room card proved the point twice: it carries "No
    Pets Allowed" and "$160 USD /night" in one container, so proximity alone
    accepted the nightly ROOM RATE as the pet fee.

    So proximity is necessary and not sufficient. The nearest pet word is
    found, and if a rate marker stands between it and the amount, the amount
    belongs to the rate.
    """
    window_start = max(0, start - _PET_CONTEXT_CHARS)
    window = text[window_start:end + _PET_CONTEXT_CHARS]
    if not _PET_CONTEXT_RE.search(window):
        return False

    # The nearest pet word on either side, measured in the full text.
    nearest = None
    for match in _PET_CONTEXT_RE.finditer(text, window_start,
                                          end + _PET_CONTEXT_CHARS):
        distance = (start - match.end()) if match.end() <= start else (match.start() - end)
        if distance < 0:
            distance = 0
        if nearest is None or distance < nearest[0]:
            nearest = (distance, match)
    if nearest is None:
        return False

    match = nearest[1]
    if match.end() <= start:
        between = text[match.end():start]
    elif match.start() >= end:
        between = text[end:match.start()]
    else:
        between = ""
    if _RATE_MARKER_RE.search(between):
        return False

    # The amount may also say, in its own sentence, that it is about something
    # other than a pet. Red Roof's block ends "Deposit Policy: A $50 refundable
    # deposit for incidentals is required at check-in for all guests" -- one
    # sentence away from the words "Pet Policy", close enough for the window
    # above, and a deposit every guest pays whether or not they bring a dog.
    # Published as a pet deposit it invents a charge for bringing an animal.
    #
    # The amount may also say, in its own sentence, what it is for -- and if
    # that is not a pet, it is not a pet charge however close the word "pet"
    # happens to sit. The test is the same shape as the rate-marker test above:
    # NEAREST WINS. The stated purpose competes with the pet wording, and the
    # one standing closer to the amount is the one the amount is about.
    #
    #   "Read Full Pet Policy Deposit Policy: A $50 refundable deposit for
    #    incidentals is required at check-in for all guests."
    #        -- "incidentals" is four characters away and "Pet" is a link label
    #           a sentence back. Published as a pet deposit, this invents a
    #           charge for bringing an animal that every guest already pays.
    #
    #   "A $75 pet fee applies for all guests travelling with pets."
    #        -- "pet fee" is part of the amount's own phrase. It wins, and the
    #           charge survives.
    #
    # Hilton writes "Deposit Yes. $75.00 Non-refundable Fee" and states no
    # purpose at all, so this never looks at it.
    segment_start = max(0, text.rfind(".", 0, start) + 1)
    segment_end = text.find(".", end)
    segment_end = len(text) if segment_end < 0 else segment_end + 1
    purpose_distance = None
    for purpose in _NON_PET_PURPOSE_RE.finditer(text, segment_start, segment_end):
        gap = (purpose.start() - end if purpose.start() >= end
               else start - purpose.end() if purpose.end() <= start else 0)
        gap = max(gap, 0)
        if purpose_distance is None or gap < purpose_distance:
            purpose_distance = gap
    return purpose_distance is None or nearest[0] <= purpose_distance


@dataclass(frozen=True)
class Charge:
    """A money statement, with whatever scope the source attached to it.

    Deliberately a superset of ``marriott_surface.Charge`` rather than a
    subclass: that type is frozen with the committed pilot-001 report and
    gaining a field would change what that pilot's manifests mean.
    """

    amount_minor: int
    basis: str
    scope: str
    origin: str
    refundable: Optional[bool]
    quote: str
    label: str = ""
    cleaning_labelled: bool = False
    #: "fee" or "deposit". A deposit is money the guest may get back and is
    #: never the price of bringing an animal, so the two must not share a pool.
    kind: str = "fee"

    def to_dict(self) -> Dict:
        return {"amount_minor": self.amount_minor, "basis": self.basis,
                "scope": self.scope, "origin": self.origin,
                "refundable": self.refundable, "quote": self.quote,
                "label": self.label, "kind": self.kind,
                "cleaning_labelled": self.cleaning_labelled}


@dataclass(frozen=True)
class Reading:
    """Everything a policy block says, brand-agnostically."""

    found: bool
    block_text: str
    strategy: str = ""
    pets_allowed: Optional[bool] = None
    pets_allowed_quote: str = ""
    charges: Tuple[Charge, ...] = ()
    weight_value: Optional[float] = None
    weight_unit: str = ""
    weight_quote: str = ""
    pet_count_limit: Optional[int] = None
    pet_count_scope: str = ""
    pet_count_quote: str = ""
    dogs_only_quote: str = ""
    cats_refused_quote: str = ""
    both_species_quote: str = ""
    fee_cap: Optional[Dict] = None
    fee_cap_quote: str = ""
    service_animal_quote: str = ""
    contradictions: Tuple[Dict, ...] = ()
    parser_notes: Tuple[str, ...] = ()
    patterns_fired: Tuple[str, ...] = ()
    brand_generic: bool = False

    def to_dict(self) -> Dict:
        return {"found": self.found, "block_text": self.block_text,
                "strategy": self.strategy, "pets_allowed": self.pets_allowed,
                "pets_allowed_quote": self.pets_allowed_quote,
                "charges": [c.to_dict() for c in self.charges],
                "weight_value": self.weight_value,
                "weight_unit": self.weight_unit,
                "weight_quote": self.weight_quote,
                "pet_count_limit": self.pet_count_limit,
                "pet_count_scope": self.pet_count_scope,
                "pet_count_quote": self.pet_count_quote,
                "dogs_only_quote": self.dogs_only_quote,
                "cats_refused_quote": self.cats_refused_quote,
                "both_species_quote": self.both_species_quote,
                "fee_cap": self.fee_cap,
                "fee_cap_quote": self.fee_cap_quote,
                "service_animal_quote": self.service_animal_quote,
                "contradictions": [dict(c) for c in self.contradictions],
                "parser_notes": list(self.parser_notes),
                "patterns_fired": list(self.patterns_fired),
                "brand_generic": self.brand_generic}


def _fee_is_conditional(block_text: str, charge) -> bool:
    """Whether a condition the schema cannot express governs this charge."""
    index = block_text.find(charge.quote)
    if index < 0:
        return bool(_CONDITIONAL_FEE_RE.search(block_text))
    start = max(0, index - _CONDITION_WINDOW_CHARS)
    end = index + len(charge.quote) + _CONDITION_WINDOW_CHARS
    return bool(_CONDITIONAL_FEE_RE.search(block_text[start:end]))


def _service_animal_quote(text: str, match) -> str:
    """The service-animal statement, bounded to a sentence-sized span.

    ``_segment_containing`` splits on punctuation and labelled rows, and an
    amenity list has neither -- Wyndham's returned the whole thousand-character
    block. When the segment is too long to be a statement, a bounded window
    around the phrase is taken instead. Both are contiguous substrings of the
    block, so either survives the evidence contract's contiguity check.
    """
    if not match:
        return ""
    segment = MS._segment_containing(text, match.start())
    if segment and len(segment) <= _MAX_SERVICE_ANIMAL_CHARS:
        return segment
    start = max(0, match.start() - 100)
    end = min(len(text), match.end() + 140)
    return text[start:end].strip()


def _service_animal_span(text: str, match,
                         charges: Sequence["Charge"] = ()) -> Optional[Tuple[int, int]]:
    """The words a limit must sit in to be a limit ON service animals.

    It begins at the service-animal PHRASE and ends where the published quote
    ends. The quote's own start is deliberately not used: ``_segment_containing``
    splits on punctuation, and Choice writes "... Max 65 Pounds Service animals
    are permitted, without charge." with no full stop before "Service". That
    segment therefore opens well before the phrase and swallows a genuine PET
    weight limit stated ahead of it.

    A limit written BEFORE the words "service animals" cannot be a limit on
    service animals, so the span starts at the phrase.

    IT ALSO ENDS WHERE A PRICE BEGINS
    ---------------------------------
    ``_segment_containing`` splits on punctuation, and a chip list has none.
    One measured surface publishes its whole policy as four labels run
    together -- "Service Animals Welcome Pet-Friendly Non-refundable fee: $100
    per reservation Pet limit: A maximum of 2 pets (dogs or cats) per room are
    allowed" -- so the segment was the entire block, the phrase sat at
    character zero, and every ordinary-pet term in the property's policy was
    discarded as a limit on service animals. The reader returned the label and
    nothing else.

    A service-animal exception does not carry a price: an exception exists to
    say the charge does NOT apply. So the span stops where the first charge
    after the phrase begins. This is deliberately narrower than "stops at the
    next pet word" -- "Only service animals are permitted, maximum 2 pets per
    room" caps service animals, states no amount, and must keep behaving as it
    does today.
    """
    quote = _service_animal_quote(text, match)
    if not quote or match is None:
        return None
    start = text.find(quote)
    if start < 0:
        return None
    end = start + len(quote)
    for charge in charges:
        at = text.find(charge.quote) if charge.quote else -1
        if match.start() < at < end:
            end = at
    return (match.start(), end) if match.start() < end else None


def _span_of(text: str, match, quote: str) -> Optional[Tuple[int, int]]:
    """A term's position, from its match when there is one and its quote when
    there is not. Every quote in this reader is a contiguous substring of the
    block, which is what makes the fallback exact rather than approximate."""
    if match is not None:
        return (match.start(), match.end())
    if not quote:
        return None
    start = text.find(quote)
    return None if start < 0 else (start, start + len(quote))


def _within(outer: Optional[Tuple[int, int]],
            inner: Optional[Tuple[int, int]]) -> bool:
    """Whether ``inner`` lies wholly inside ``outer``."""
    if outer is None or inner is None:
        return False
    return outer[0] <= inner[0] and inner[1] <= outer[1]


#: Words that void an acceptance a few tokens later. "Sorry no other pets are
#: allowed" contains "pets are allowed" and means its opposite.
_NEGATION_RE = re.compile(r"\b(?:no|not|never|sorry|except|excluding)\b",
                          re.IGNORECASE)

#: How far back a negation may sit and still govern the acceptance.
_NEGATION_LOOKBACK_CHARS = 24


def _is_negated(text: str, match) -> bool:
    """Whether an acceptance match is governed by an earlier negation."""
    start = max(0, match.start() - _NEGATION_LOOKBACK_CHARS)
    return bool(_NEGATION_RE.search(text[start:match.start()]))


#: The refusal wordings that are only a refusal when nothing was accepted
#: first. "No pets" refuses pets. "No OTHER pets" answers a question the
#: sentence before it asked, and the answer depends on what that sentence said.
_QUALIFIED_REFUSAL_RE = re.compile(
    r"\bno\s+(?:other|additional|further)\s+pets?\b", re.IGNORECASE)


def _is_species_restriction(text: str, refused, dogs_only, both_species,
                            service) -> bool:
    """Whether "no other pets" restricts the SPECIES rather than refusing pets.

    Both readings exist and they are opposite, so the antecedent decides:

      "Service animals are welcome. No other pets are allowed."
          -- the only thing accepted is a service animal, which is not a pet.
             This refuses pets, and reading it any other way would publish a
             no-pets hotel as pet-friendly. It was very nearly published.

      "... welcomes dogs only. No other pets are allowed on property. ...
       A $40 pet fee per night, per dog (up to 2 dogs max)."
          -- the property has just said which animal it takes and then priced
             it. This restricts the species. Read as a refusal it made the
             surface self-contradictory and the reader withheld the fee, the
             count, the species and the acceptance: four facts, all stated.

    So a qualified refusal is a species restriction when a SPECIES acceptance
    stands before it, and that acceptance is not the service-animal sentence.
    """
    if not _QUALIFIED_REFUSAL_RE.match(text, refused.start()):
        return False
    accepted = [m for m in (dogs_only, both_species) if m is not None]
    if not accepted:
        return False
    service_span = _service_animal_span(text, service)
    return any(m.end() <= refused.start()
               and not _within(service_span, (m.start(), m.end()))
               for m in accepted)


def _contains(outer, inner) -> bool:
    """Whether one match's span wholly contains another's."""
    return outer.start() <= inner.start() and outer.end() >= inner.end()


def _first_acceptance(text: str):
    """The first acceptance a negation does NOT govern, and the ones it did.

    ``_first_match`` stops at the first PATTERN that matches anywhere, so one
    negated phrase used to end the search for the whole block. A measured
    surface writes "... welcomes dogs only. No other pets are allowed on
    property." -- the negated fragment "pets are allowed" matched an
    early pattern, was correctly discarded, and took the property's actual
    acceptance down with it two sentences earlier.

    A negation governs a MATCH, never a document, so a discarded match is
    stepped over and the search continues.
    """
    negated = []
    for index, pattern in enumerate(_PETS_WELCOME_RES):
        for match in pattern.finditer(text):
            if _is_negated(text, match):
                negated.append(text[match.start():match.end()])
                continue
            return match, "welcome[%d]" % index, negated
    return None, "", negated


def _first_match(text: str, patterns: Sequence[re.Pattern], label: str):
    for index, pattern in enumerate(patterns):
        match = pattern.search(text)
        if match:
            return match, "%s[%d]" % (label, index)
    return None, ""


def parse(block_text: str, *, strategy: str = "") -> Reading:
    """Read a bounded policy block. Labels and stated words only."""
    text = collapse(block_text)
    if not text:
        return Reading(found=False, block_text="", strategy=strategy,
                       parser_notes=("the policy container was empty",))

    fired: List[str] = []
    notes: List[str] = []
    charges: List[Charge] = []

    cleaning_amounts = {_amount_minor(m.group("amount"))
                        for m in MS._PROSE_CLEANING_RE.finditer(text)}

    # --- labelled rows (Marriott's shape, reused verbatim) ---------------- #
    for match in MS._LABELLED_CHARGE_RE.finditer(text):
        label = collapse(match.group("label"))
        lowered = label.lower().replace("-", "")
        refundable = (False if "nonrefundable" in lowered
                      else True if lowered.startswith("refundable") else None)
        amount = _amount_minor(match.group("amount"))
        charges.append(Charge(
            amount_minor=amount,
            basis=_BASIS_BY_WORD[match.group("basis").lower()], scope="",
            origin="labelled_row", refundable=refundable,
            quote=text[match.start():match.end()], label=label,
            cleaning_labelled=amount in cleaning_amounts))
        fired.append("labelled_row")

    # --- scoped prose charges ("$25 per pet per night") ------------------- #
    for match in _SCOPED_CHARGE_RE.finditer(text):
        words = [w for w in (match.group("first"), match.group("second")) if w]
        basis = ""
        scope = ""
        for word in words:
            lowered = word.lower()
            if lowered in _BASIS_BY_WORD and not basis:
                basis = _BASIS_BY_WORD[lowered]
            elif lowered in _SCOPE_BY_WORD and not scope:
                scope = _SCOPE_BY_WORD[lowered]
        if not basis:
            continue                      # "$25 per pet" alone states no basis
        if not _pet_context(text, match.start(), match.end()):
            notes.append("ignored the amount %r: no pet wording within %d "
                         "characters, so it is a price the page states for "
                         "something else"
                         % (text[match.start():match.end()], _PET_CONTEXT_CHARS))
            continue
        amount = _amount_minor(match.group("amount"))
        window = text[max(0, match.start() - 60):match.end() + 40]
        refundable = (False if _NONREFUNDABLE_RE.search(window)
                      else True if _REFUNDABLE_RE.search(window) else None)
        charges.append(Charge(
            amount_minor=amount, basis=basis, scope=scope, origin="prose",
            refundable=refundable, quote=text[match.start():match.end()],
            cleaning_labelled=amount in cleaning_amounts))
        fired.append("scoped_prose_charge")

    # --- the same charge written without a dollar sign --------------------- #
    for pattern, label in ((_SCOPED_CHARGE_USD_RE, "usd_charge"),
                           (_BARE_CHARGE_RE, "bare_decimal_charge")):
        for match in pattern.finditer(text):
            groups = match.groupdict()
            words = [w for w in (groups.get("first"), groups.get("second"),
                                 groups.get("basis")) if w]
            basis = ""
            scope = ""
            for word in words:
                lowered = word.lower()
                if lowered in _BASIS_BY_WORD and not basis:
                    basis = _BASIS_BY_WORD[lowered]
                elif lowered in _SCOPE_BY_WORD and not scope:
                    scope = _SCOPE_BY_WORD[lowered]
            if not basis:
                continue
            if not _pet_context(text, match.start(), match.end()):
                notes.append("ignored the amount %r: no pet wording within %d "
                             "characters"
                             % (text[match.start():match.end()],
                                _PET_CONTEXT_CHARS))
                continue
            amount = _amount_minor(match.group("amount"))
            window = text[max(0, match.start() - 60):match.end() + 40]
            refundable = (False if _NONREFUNDABLE_RE.search(window)
                          else True if _REFUNDABLE_RE.search(window) else None)
            charges.append(Charge(
                amount_minor=amount, basis=basis, scope=scope, origin="prose",
                refundable=refundable, quote=text[match.start():match.end()],
                cleaning_labelled=amount in cleaning_amounts))
            fired.append(label)

    # --- loose prose charges, only for amounts nothing else explained ----- #
    #
    # Runs last and only fills gaps: a brand that states its charge in a
    # structured row or with its own scope words has already been read, and
    # re-reading the same amount here would manufacture a contradiction out of
    # two views of one sentence.
    explained = {c.amount_minor for c in charges}
    for match in _LOOSE_CHARGE_RE.finditer(text):
        amount = _amount_minor(match.group("amount"))
        if amount in explained:
            continue
        gap = match.group("gap") or ""
        if "$" in gap or "." in gap:
            continue
        if not _pet_context(text, match.start(), match.end()):
            notes.append("ignored the amount %r: no pet wording within %d "
                         "characters"
                         % (text[match.start():match.end()], _PET_CONTEXT_CHARS))
            continue
        window = text[max(0, match.start() - 60):match.end() + 40]
        refundable = (False if _NONREFUNDABLE_RE.search(window)
                      else True if _REFUNDABLE_RE.search(window) else None)
        charges.append(Charge(
            amount_minor=amount,
            basis=_BASIS_BY_WORD[match.group("basis").lower()], scope="",
            origin="prose", refundable=refundable,
            quote=text[match.start():match.end()],
            cleaning_labelled=amount in cleaning_amounts))
        explained.add(amount)
        fired.append("loose_prose_charge")

    # --- a stated ceiling ---------------------------------------------------- #
    #
    # CEILING != PRICE is a founder rule. "Max 75 USD per stay" is recorded as
    # fee_cap and is excluded from the charge list entirely, so it can never be
    # mistaken for what the guest pays.
    fee_cap = None
    fee_cap_quote = ""
    cap_match = _FEE_CAP_RE.search(text)
    if cap_match and _pet_context(text, cap_match.start(), cap_match.end()):
        raw = cap_match.group("dollars") or cap_match.group("usd")
        fee_cap = {"amount_minor": _amount_minor(raw), "currency": "USD",
                   "basis": _BASIS_BY_WORD[cap_match.group("basis").lower()]}
        fee_cap_quote = text[cap_match.start():cap_match.end()]
        capped = _amount_minor(raw)
        charges = [c for c in charges if not (c.amount_minor == capped
                                              and c.origin == "prose")]
        fired.append("fee_cap")

    # --- an amount a brand labels a fee, with no basis stated ---------------- #
    #
    # Hilton's structured row is "Deposit Yes. $75.00 Non-refundable Fee". The
    # amount is a fact and the basis is not, so the amount is recorded with an
    # EMPTY basis and the basis is withheld rather than guessed. Runs last and
    # only for amounts nothing else has already explained.
    explained_amounts = {c.amount_minor for c in charges}
    if fee_cap:
        explained_amounts.add(fee_cap["amount_minor"])
    for match in _LABELLED_AMOUNT_RE.finditer(text):
        if not (match.group("pre") or match.group("post")):
            continue
        raw = match.group("dollars") or match.group("usd")
        if not raw:
            continue
        amount = _amount_minor(raw)
        if amount in explained_amounts:
            continue
        if not _pet_context(text, match.start(), match.end()):
            continue
        window = text[max(0, match.start() - 60):match.end() + 40]
        refundable = (False if _NONREFUNDABLE_RE.search(window)
                      else True if _REFUNDABLE_RE.search(window) else None)
        label_word = (match.group("pre") or match.group("post") or "").lower()
        charges.append(Charge(
            amount_minor=amount, basis="", scope="", origin="labelled_amount",
            refundable=refundable, quote=text[match.start():match.end()],
            cleaning_labelled=amount in cleaning_amounts,
            kind="deposit" if "deposit" in label_word else "fee"))
        explained_amounts.add(amount)
        fired.append("labelled_amount_no_basis")

    # --- contradiction: one amount, two bases ----------------------------- #
    by_amount: Dict[int, List[Charge]] = {}
    for charge in charges:
        by_amount.setdefault(charge.amount_minor, []).append(charge)
    contradictions: List[Dict] = []
    for amount, group in sorted(by_amount.items()):
        bases = sorted({c.basis for c in group if c.basis})
        if len(bases) > 1:
            contradictions.append({
                "amount_minor": amount, "field": "fee_basis",
                "bases_stated": bases,
                "withholding_reason": enums.SOURCE_CONTRADICTORY,
                "quotes": [c.quote for c in group],
                "note": ("the same amount is stated on two different bases on "
                         "one first-party surface; per_day and per_night are "
                         "distinct under the frozen schema and this layer does "
                         "not select a winner")})
        scopes = sorted({c.scope for c in group if c.scope})
        if len(scopes) > 1:
            contradictions.append({
                "amount_minor": amount, "field": "fee_scope",
                "bases_stated": scopes,
                "withholding_reason": enums.SOURCE_CONTRADICTORY,
                "quotes": [c.quote for c in group],
                "note": ("the same amount is stated per pet and per room; for "
                         "two animals those are different prices")})

    # --- weight ------------------------------------------------------------ #
    weight_match, weight_pattern = _first_match(text, _WEIGHT_RES, "weight")
    weight_value = weight_unit = weight_quote = None
    if weight_match:
        weight_value = float(weight_match.group("value").replace(",", ""))
        weight_unit = _UNIT_CANON.get(
            weight_match.group("unit").lower().rstrip("."), "")
        weight_quote = text[weight_match.start():weight_match.end()]
        fired.append(weight_pattern)
        distinct = {float(m.group("value").replace(",", ""))
                    for pattern in _WEIGHT_RES for m in pattern.finditer(text)}
        if len(distinct) > 1:
            notes.append("the block states more than one pet weight (%s); the "
                         "first recognised statement was taken and the "
                         "disagreement is recorded here" % sorted(distinct))

    # --- count -------------------------------------------------------------- #
    count_match, count_pattern = _first_match(text, _COUNT_RES, "count")
    pet_count = pet_count_scope = pet_count_quote = None
    if count_match:
        groups = count_match.groupdict()
        if groups.get("count"):
            pet_count = int(groups["count"])
        elif groups.get("word"):
            pet_count = _WORD_NUMBERS[groups["word"].lower()]
        else:
            pet_count = 1
        raw_scope = (groups.get("scope") or "").lower()
        # "in Room" / "per room" is the label's own word, not an inference.
        pet_count_scope = (enums.SCOPE_PER_ROOM
                           if raw_scope in ("room", "reservation", "suite")
                           or "room" in count_match.group(0).lower() else "")
        pet_count_quote = text[count_match.start():count_match.end()]
        fired.append(count_pattern)

    # --- allowed / refused --------------------------------------------------- #
    dogs_only = (MS._DOGS_ONLY_RE.search(text)
                 or re.search(r"\bdogs?\s+(?:are\s+)?(?:allowed|welcome|"
                              r"permitted)\b", text, re.IGNORECASE))
    cats_refused = MS._CATS_REFUSED_RE.search(text)
    both_species = _BOTH_SPECIES_RE.search(text) or _SPECIES_PAIR_RE.search(text)
    service = MS._SERVICE_ANIMAL_RE.search(text)

    refused, refused_pattern = _first_match(text, _PETS_REFUSED_RES, "refused")
    if refused and _is_species_restriction(text, refused, dogs_only,
                                           both_species, service):
        notes.append(
            "read %r as a restriction to the species this surface names and "
            "not as a refusal of pets: the property states which animals it "
            "accepts before it says there are no others"
            % text[refused.start():refused.end()])
        refused, refused_pattern = None, ""
    welcome, welcome_pattern, negated = _first_acceptance(text)
    for quote in negated:
        notes.append("ignored the acceptance %r: a negation governs it" % quote)
    pets_allowed = None
    pets_allowed_quote = ""
    if refused and welcome and _contains(refused, welcome):
        # "Pets Allowed: No" contains "Pets Allowed". The longer, more specific
        # statement is the one the property made; treating the fragment inside
        # it as a competing claim would invent a contradiction out of one
        # sentence.
        welcome = None
    elif refused and welcome and _contains(welcome, refused):
        refused = None

    if refused and welcome:
        notes.append("the block says both that pets are welcome and that they "
                     "are not allowed; neither is taken")
        contradictions.append({
            "amount_minor": None, "field": "pets_allowed", "bases_stated": [],
            "withholding_reason": enums.SOURCE_CONTRADICTORY,
            "quotes": [text[refused.start():refused.end()],
                       text[welcome.start():welcome.end()]],
            "note": "the surface asserts and denies pet acceptance"})
    elif refused:
        pets_allowed = False
        pets_allowed_quote = text[refused.start():refused.end()]
        fired.append(refused_pattern)
    elif welcome:
        pets_allowed = True
        pets_allowed_quote = text[welcome.start():welcome.end()]
        fired.append(welcome_pattern)

    # --- a refusal may not arrive carrying ordinary-pet terms ---------------- #
    #
    # Two different faults produce the same shape, and they need different
    # answers, so they are separated before either is acted on.
    #
    # 1. The term sits INSIDE the service-animal statement. "Only service
    #    animals are permitted, maximum 2 per room" caps SERVICE ANIMALS. A
    #    service-animal limit must never be republished as a pet limit, so the
    #    term is dropped. That is a mis-attribution, not a contradiction: the
    #    source said one coherent thing and the reader misread which subject it
    #    was about.
    #
    # 2. The term is an ordinary-pet term standing outside that statement, and
    #    the block also refuses pets. Then the SOURCE contradicts itself, and
    #    the corpus rule is to publish neither side rather than pick one.
    #
    # This is a general rule about wording. It is deliberately not keyed to any
    # property, brand or URL.
    service_span = _service_animal_span(text, service, charges)
    pet_terms = [
        ("weight_limit", _span_of(text, weight_match, weight_quote), weight_quote),
        ("pet_count_limit", _span_of(text, count_match, pet_count_quote),
         pet_count_quote),
    ]
    pet_terms += [("species_allowed", (m.start(), m.end()),
                   text[m.start():m.end()])
                  for m in (dogs_only, both_species) if m]
    # ``Charge`` is frozen with the committed pilot manifests and carries no
    # match object. Its quote is a contiguous substring of the block by
    # contract, so its position is recoverable without changing that type.
    pet_terms += [("pet_fee", _span_of(text, None, c.quote), c.quote)
                  for c in charges]

    def _drop(field: str) -> None:
        nonlocal weight_value, weight_unit, weight_quote
        nonlocal pet_count, pet_count_scope, pet_count_quote
        nonlocal dogs_only, both_species, charges
        if field == "weight_limit":
            weight_value = weight_unit = weight_quote = None
        elif field == "pet_count_limit":
            pet_count = pet_count_scope = pet_count_quote = None
        elif field == "species_allowed":
            dogs_only = both_species = None
        elif field == "pet_fee":
            charges = []

    inside_service = [(f, q) for f, span, q in pet_terms
                      if span is not None and _within(service_span, span)]
    for field, quote in inside_service:
        notes.append("dropped %s %r: it stands inside the service-animal "
                     "statement, so it limits service animals and not pets"
                     % (field, quote))
        _drop(field)

    handled = {f for f, _q in inside_service}
    ordinary = [(f, q) for f, span, q in pet_terms
                if span is not None and f not in handled
                and not _within(service_span, span)]
    if pets_allowed is False and ordinary:
        quotes = [pets_allowed_quote] + [q for _f, q in ordinary]
        notes.append("the block refuses pets and states ordinary-pet terms "
                     "(%s) in the same breath; neither is taken"
                     % ", ".join(sorted({f for f, _q in ordinary})))
        contradictions.append({
            "amount_minor": None, "field": "pets_allowed", "bases_stated": [],
            "withholding_reason": enums.SOURCE_CONTRADICTORY,
            "quotes": [q for q in quotes if q],
            "contradicted_fields": sorted({f for f, _q in ordinary}),
            "note": ("the surface denies pet acceptance and states pet terms "
                     "that only apply if pets are accepted")})
        pets_allowed, pets_allowed_quote = None, ""
        for field, _quote in ordinary:
            _drop(field)

    return Reading(
        found=True, block_text=text, strategy=strategy,
        pets_allowed=pets_allowed, pets_allowed_quote=pets_allowed_quote,
        charges=tuple(charges), weight_value=weight_value,
        weight_unit=weight_unit or "", weight_quote=weight_quote or "",
        pet_count_limit=pet_count, pet_count_scope=pet_count_scope or "",
        pet_count_quote=pet_count_quote or "",
        dogs_only_quote=(text[dogs_only.start():dogs_only.end()]
                         if dogs_only else ""),
        cats_refused_quote=(text[cats_refused.start():cats_refused.end()]
                            if cats_refused else ""),
        service_animal_quote=_service_animal_quote(text, service),
        both_species_quote=(text[both_species.start():both_species.end()]
                            if both_species else ""),
        fee_cap=fee_cap, fee_cap_quote=fee_cap_quote,
        contradictions=tuple(contradictions), parser_notes=tuple(notes),
        patterns_fired=tuple(sorted(set(fired))),
        brand_generic=bool(_BRAND_GENERIC_RE.search(text)))


#: Sentence punctuation. A statement has some; a chip in an amenity list has
#: none, which is one of the differences this guard turns on.
_SENTENCE_PUNCTUATION_RE = re.compile(r"[.!?]")

#: Any wording a pet POLICY uses and an amenity LABEL does not: a number, a
#: price, a charge word, a physical limit, a named species, a house rule.
#:
#: This is asked of the SURFACE, never of what the parser managed to read. The
#: first version of the guard asked the parser, and that is a different and much
#: worse question: five surfaces stating a real fee -- "Pet fee per night: 75
#: USD Pet weight limit: 75 2 pets allowed", "Dog Friendly: $25/dog per night"
#: -- have wordings this reader still does not parse, and the guard turned each
#: of those parser gaps into a published claim that the page carried nothing but
#: an amenity chip. A reader that cannot read a policy must say so, not report
#: that there was none.
_POLICY_VOCABULARY_RE = re.compile(
    r"\d|\$|\bfee\b|\bfees\b|\bcharge\b|\bdeposit\b|\bpolicy\b|\bpolicies\b"
    r"|\bweight\b|\blimit\b|\blbs?\b|\bpounds?\b|\bkgs?\b|\bbreed\b"
    r"|\bleash\b|\bkennel\b|\bcrate\b|\bunattended\b|\brefundable\b"
    r"|\bservice\s+animals?\b|\bdogs?\b|\bcats?\b|\bper\s+(?:night|stay|day)\b",
    re.IGNORECASE)


def _is_amenity_label_only(reading: Reading) -> bool:
    """Whether the surface carries a LABEL where a policy would be.

    A brand that lists its facilities as chips had one of them read as a
    policy:
    "Pets Allowed Coin Laundry" satisfied an acceptance pattern and produced
    ``pets_allowed: true`` for two properties. That is a real signal about the
    hotel and it is not a policy -- it states no fee, no count, no weight, no
    species and no condition, and a guest who reads "pets allowed" on a hotel
    page has been told nothing they can plan a trip around.

    Four conditions, all required, and NONE of them is a length rule -- a short
    policy is still a policy:

      * the signal is an ACCEPTANCE. A refusal is never an amenity chip: no
        facilities list advertises "no pets", so "Sorry, no pets allowed."
        stays a policy and stays meaningful.
      * the reader found no term -- no charge, no cap, no count, no weight, no
        species, no service-animal exception, nothing contradicted.
      * and NEITHER DID THE SURFACE: no price, no number, no charge word, no
        physical limit, no named species anywhere in the block. This is the
        condition that matters, because the one above is a statement about the
        parser and this one is a statement about the page.
      * the wording is a LABEL rather than a STATEMENT: no sentence punctuation
        anywhere in the block. "Pets are welcome." is a sentence and survives;
        "Pets Allowed Coin Laundry" is two chips in a row.
    """
    if reading.pets_allowed is not True:
        return False
    if (reading.charges or reading.fee_cap or reading.weight_value is not None
            or reading.pet_count_limit is not None
            or reading.dogs_only_quote or reading.both_species_quote
            or reading.cats_refused_quote or reading.service_animal_quote
            or reading.contradictions):
        return False
    if _POLICY_VOCABULARY_RE.search(reading.block_text):
        return False
    return not _SENTENCE_PUNCTUATION_RE.search(reading.block_text)


def to_extraction(reading: Reading, *, location: str) -> MS.ExtractionResult:
    """Map a reading onto the frozen ``ptf-policy-observation/1.0`` vocabulary.

    Same rules as the Marriott reader, plus one: ``fee_scope`` is emitted when
    and only when the chosen charge's own words state it.
    """
    extraction: Dict = {}
    evidence: List[Dict] = []
    flags: List[Dict] = []
    withheld: Dict[str, str] = {}
    non_inferences: List[str] = [
        "weight_limit.operator: 'maximum' / 'up to' / 'under' are recorded as "
        "a value only; defaulting a comparison is a guest-visible error in "
        "both directions",
        "weight_limit.scope: not emitted unless the source states it",
    ]

    def cite(quote: str, fields: Sequence[str]) -> None:
        evidence.append({"quote": quote, "location": location,
                         "field_refs": list(fields)})

    amenity_only = _is_amenity_label_only(reading)
    if amenity_only:
        withheld["pets_allowed"] = enums.ARTIFACT_INSUFFICIENT
        flags.append({
            "code": "FLAG_AMENITY_LABEL_ONLY",
            "detail": "the only pet wording on this surface is an amenity "
                      "label (%r) -- a chip in a list, stating no term and "
                      "making no statement; it is not a pet policy and is not "
                      "recorded as one" % reading.block_text[:120]})
    elif reading.pets_allowed is not None:
        extraction["pets_allowed"] = reading.pets_allowed
        cite(reading.pets_allowed_quote, ["pets_allowed"])
    else:
        withheld["pets_allowed"] = (enums.SOURCE_CONTRADICTORY
                                    if reading.contradictions
                                    else enums.SOURCE_SILENT)

    # A brand that writes "$75.00 Non-refundable Fee" has LABELLED the
    # amount even though it stated no basis. Excluding it from the pool is
    # what made four Hilton properties report SOURCE_SILENT for a fee
    # printed on the page.
    deposits = [c for c in reading.charges if c.kind == "deposit"]
    if deposits:
        extraction["pet_deposit"] = deposits[0].amount_minor
        cite(deposits[0].quote, ["pet_deposit"])

    labelled = [c for c in reading.charges
                if c.origin in ("labelled_row", "labelled_amount")
                and c.kind != "deposit"]
    prose = [c for c in reading.charges
             if c.origin == "prose" and c.kind != "deposit"]
    contradicted = {c["amount_minor"] for c in reading.contradictions
                    if c.get("amount_minor") is not None}
    contradicted_fields = {c["field"] for c in reading.contradictions}

    cleaning = [c for c in reading.charges if c.cleaning_labelled]
    pool = [c for c in labelled if not c.cleaning_labelled]

    # A charge that states its basis is a better answer than one that does not.
    # Without this, "100.00 USD refundable deposit" outranked "25.00 USD Per Pet
    # per night" purely because it was matched by an earlier pass.
    with_basis = [c for c in reading.charges
                  if c.basis and c.kind != "deposit" and not c.cleaning_labelled]
    distinct_amounts = {c.amount_minor for c in with_basis}
    if len(distinct_amounts) == 1:
        # One charge the surface stated more than once -- a labelled row and
        # the prose that repeats it are the same money, not two fees. The
        # labelled row is preferred for its quote; if the two disagree about
        # the BASIS, the contradiction machinery has already recorded it and
        # the basis is withheld below.
        pool = [next((c for c in with_basis if c.origin == "labelled_row"),
                     with_basis[0])]
    elif with_basis:
        pool = with_basis
    if not pool:
        distinct = {(c.amount_minor, c.basis) for c in prose
                    if not c.cleaning_labelled}
        if len(distinct) == 1:
            pool = [c for c in prose if not c.cleaning_labelled][:1]
        elif len(distinct) > 1:
            flags.append({"code": "FLAG_MULTI_POLICY_BLOCKS",
                          "detail": "the surface states several unlabelled "
                                    "charges and no structured row; no fee is "
                                    "taken from prose alone"})

    if cleaning:
        extraction["cleaning_fee"] = cleaning[0].amount_minor
        cite(cleaning[0].quote, ["cleaning_fee"])

    if len(pool) == 1 and _fee_is_conditional(reading.block_text, pool[0]):
        withheld["pet_fee"] = enums.SCHEMA_CANNOT_REPRESENT
        withheld["fee_basis"] = enums.SCHEMA_CANNOT_REPRESENT
        flags.append({
            "code": "FLAG_AMBIGUOUS_SCOPE",
            "detail": "the charge is qualified by a condition the published "
                      "fee vocabulary has no field for (%r); publishing the "
                      "amount alone would assert a charge for every pet"
                      % pool[0].quote})
        pool = []

    # A tiered price is withheld for the same reason and through the same
    # machinery: the published vocabulary holds ONE amount and the surface
    # stated several. Publishing whichever one happened to parse is not a
    # partial answer, it is a wrong one. The case that forced this: a surface
    # pricing 1-6 nights at 50 USD and 7+ nights at 150 USD, from which the
    # reader published 50 -- understating a week by 100 USD.
    if pool and _fee_is_tiered(reading.block_text):
        withheld["pet_fee"] = enums.SCHEMA_CANNOT_REPRESENT
        withheld["fee_basis"] = enums.SCHEMA_CANNOT_REPRESENT
        flags.append({
            "code": "FLAG_TIERED_FEE",
            "detail": "the surface prices this pet differently by stay length "
                      "or by pet count, and the published fee vocabulary holds "
                      "a single amount; the tiers survive in the evidence "
                      "quote and no single amount is asserted"})
        pool = []

    if len(pool) == 1:
        charge = pool[0]
        extraction["pet_fee"] = charge.amount_minor
        extraction["fee_currency"] = "USD"
        cite(charge.quote, ["pet_fee", "fee_currency"])
        if not charge.basis:
            withheld["fee_basis"] = enums.SOURCE_SILENT
        elif charge.amount_minor in contradicted and "fee_basis" in contradicted_fields:
            withheld["fee_basis"] = enums.SOURCE_CONTRADICTORY
            flags.append({"code": "FLAG_AMBIGUOUS_BASIS",
                          "detail": "the $%.2f charge is stated on more than "
                                    "one basis on this surface; per_day and "
                                    "per_night are distinct and this layer "
                                    "does not choose"
                                    % (charge.amount_minor / 100.0)})
        else:
            extraction["fee_basis"] = charge.basis
            cite(charge.quote, ["fee_basis"])
        if charge.scope:
            if charge.amount_minor in contradicted and \
                    "fee_scope" in contradicted_fields:
                withheld["fee_scope"] = enums.SOURCE_CONTRADICTORY
                flags.append({"code": "FLAG_AMBIGUOUS_SCOPE",
                              "detail": "the same amount is stated per pet and "
                                        "per room on this surface"})
            else:
                extraction["fee_scope"] = charge.scope
                cite(charge.quote, ["fee_scope"])
        else:
            non_inferences.append(
                "fee_scope: this surface does not say whether the charge is "
                "per pet or per room; unknown is absence")
    elif len(pool) > 1:
        withheld["pet_fee"] = enums.SOURCE_AMBIGUOUS
        withheld["fee_basis"] = enums.SOURCE_AMBIGUOUS
        flags.append({"code": "FLAG_MULTI_POLICY_BLOCKS",
                      "detail": "the surface carries %d distinct pet charges "
                                "(%s) and does not say which is the pet fee"
                                % (len(pool),
                                   ", ".join(sorted(c.quote for c in pool)))})
    elif reading.pets_allowed:
        # A reason already recorded is more specific than silence. The
        # conditional-fee branch above empties the pool deliberately, and its
        # SCHEMA_CANNOT_REPRESENT must not be overwritten by "the page said
        # nothing" -- the page said something the schema cannot hold.
        withheld.setdefault("pet_fee", enums.SOURCE_SILENT)

    if reading.fee_cap:
        extraction["fee_cap"] = dict(reading.fee_cap)
        cite(reading.fee_cap_quote, ["fee_cap"])

    if reading.weight_value is not None and reading.weight_unit:
        extraction["weight_limit"] = {"value": reading.weight_value,
                                      "unit": reading.weight_unit}
        cite(reading.weight_quote, ["weight_limit"])

    if reading.pet_count_limit is not None:
        extraction["pet_count_limit"] = reading.pet_count_limit
        if reading.pet_count_scope:
            extraction["pet_count_scope"] = reading.pet_count_scope
            cite(reading.pet_count_quote,
                 ["pet_count_limit", "pet_count_scope"])
        else:
            cite(reading.pet_count_quote, ["pet_count_limit"])

    if reading.both_species_quote:
        # "dogs and cats only" names BOTH, which a generic "pets welcome"
        # never does. Recording two named species is transcription; inferring
        # them from silence is what the corpus rule forbids.
        extraction["species_allowed"] = ["cat", "dog"]
        cite(reading.both_species_quote, ["species_allowed"])
    elif reading.dogs_only_quote:
        extraction["species_allowed"] = ["dog"]
        cite(reading.dogs_only_quote, ["species_allowed"])
    if reading.cats_refused_quote:
        extraction["cats_allowed"] = False
        cite(reading.cats_refused_quote, ["cats_allowed"])
    if not (reading.dogs_only_quote or reading.cats_refused_quote
            or reading.both_species_quote):
        non_inferences.append(
            "species: a generic 'pets welcome' is not dogs+cats; the species "
            "map stays empty unless the surface names a species")

    if reading.service_animal_quote:
        extraction["service_animal_exception"] = reading.service_animal_quote
        cite(reading.service_animal_quote, ["service_animal_exception"])

    if reading.brand_generic:
        flags.append({
            "code": "FLAG_BRAND_GENERIC",
            "detail": "the located block states a policy for the chain rather "
                      "than for this property; brand policy may corroborate a "
                      "property-specific statement but never populate one "
                      "(membrane rule M3)"})

    for contradiction in reading.contradictions:
        if contradiction.get("field") == "pets_allowed":
            flags.append({"code": "FLAG_CONTRADICTS_OFFICIAL",
                          "detail": contradiction["note"]})

    return MS.ExtractionResult(
        extraction=extraction, evidence=tuple(evidence), flags=tuple(flags),
        withheld=withheld, non_inferences=tuple(non_inferences),
        parser_warnings=tuple(reading.parser_notes))


__all__ = ["collapse", "Charge", "Reading", "parse", "to_extraction"]
