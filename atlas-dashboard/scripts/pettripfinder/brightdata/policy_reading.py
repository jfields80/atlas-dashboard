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
from typing import (Dict, List, Mapping, NamedTuple, Optional, Sequence,
                    Tuple)

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.brightdata import marriott_surface as MS  # noqa: E402
from scripts.pettripfinder.contracts import enums                    # noqa: E402

collapse = MS.collapse

_BASIS_BY_WORD = {"stay": enums.BASIS_PER_STAY, "night": enums.BASIS_PER_NIGHT,
                  "nightly": enums.BASIS_PER_NIGHT, "day": enums.BASIS_PER_DAY,
                  "daily": enums.BASIS_PER_DAY}

#: A named species in a CHARGE is a scope word: "$25 per dog per night" prices
#: one animal, exactly as "$25 per pet per night" does. The published scope
#: vocabulary has ``per_pet`` and ``per_room`` and no per-species member, and a
#: dog is a pet, so both map to ``per_pet`` -- which is transcription, not an
#: inference about which species the property accepts. That question is
#: answered by the species fields and never by a price.
#:
#: This map is consulted ONLY inside the charge patterns. "dog" is not a scope
#: token anywhere else: ``pet_count_scope`` still reads room / reservation /
#: suite alone, so "2 dogs per room" keeps its room scope.
_SCOPE_BY_WORD = {"pet": enums.SCOPE_PER_PET, "animal": enums.SCOPE_PER_PET,
                  "dog": enums.SCOPE_PER_PET, "dogs": enums.SCOPE_PER_PET,
                  "cat": enums.SCOPE_PER_PET, "cats": enums.SCOPE_PER_PET,
                  "room": enums.SCOPE_PER_ROOM, "reservation": enums.SCOPE_PER_ROOM}

#: The species words the charge patterns accept as a scope. Kept beside the map
#: so the two cannot drift: a word in the alternation with no entry above would
#: silently parse as "no scope stated".
_CHARGE_SCOPE_SPECIES = r"dogs?|cats?"

#: An amount with its own scope and basis words attached, in either order:
#: "$25 per pet per night", "$25 per night per pet", "$25 per pet, per night".
_SCOPED_CHARGE_RE = re.compile(
    r"\$\s*(?P<amount>[\d,]+(?:\.\d{1,2})?)\s*"
    r"(?:(?:per|/|a)\s*(?P<first>pet|animal|" + _CHARGE_SCOPE_SPECIES +
    r"|room|reservation|night|day|stay|nightly|daily)\b[\s,]*)"
    r"(?:(?:per|/|a)\s*(?P<second>pet|animal|" + _CHARGE_SCOPE_SPECIES +
    r"|room|reservation|night|day|stay|nightly|daily)\b)?",
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
    r"(?:(?:per|/|a)\s*)?(?P<first>pet|animal|" + _CHARGE_SCOPE_SPECIES +
    r"|room|reservation|night|day|stay|nightly|daily)\b[\s,.]*"
    r"(?:(?:per|/|a)\s*)?(?P<second>pet|animal|" + _CHARGE_SCOPE_SPECIES +
    r"|room|reservation|night|day|stay|nightly|daily)?\b",
    re.IGNORECASE)

#: The label states the BASIS and the amount follows it: "Pet fee per night: 75
#: USD", "Pet charge per stay $50". Every other charge pattern here reads the
#: amount first and looks rightwards for its terms, so a surface that puts them
#: in the other order was read as stating no charge at all -- not as an
#: ambiguous one, as none.
#:
#: The pet word is REQUIRED in the label. Without it "Rate per night: 189 USD"
#: is the same shape, and this pattern would read a room rate as a pet fee --
#: the guest-room-card mistake in yet another costume.
_BASIS_FIRST_CHARGE_RE = re.compile(
    r"\b(?:pets?|dogs?|cats?|animals?)\s+(?:fee|fees|charge|charges|rate)\s*"
    r"(?:per|/|a)\s*(?P<basis>night|day|stay|nightly|daily)\s*:?\s*"
    r"(?:\$\s*(?P<dollars>[\d,]+(?:\.\d{1,2})?)"
    r"|(?P<usd>[\d,]+(?:\.\d{1,2})?)\s*USD\b)",
    re.IGNORECASE)

#: A charge the surface NAMES as the pet's: "The Pet Friendly rate is 35.00 USD
#: per day", "Pet fee is $25 per night", "Dog charge: 40.00 USD".
#:
#: WHY THIS EXISTS AS ITS OWN PATTERN
#: ----------------------------------
#: ``_SCOPED_CHARGE_USD_RE`` already matched "35.00 USD per day" perfectly. The
#: amount was thrown away by ``_pet_context``, which asks what stands between
#: the nearest pet word and the figure and finds the word "rate" -- the very
#: marker that exists to stop a nightly ROOM rate being published as a pet fee.
#: Best Western calls its pet charge "the Pet Friendly rate", so the guard fired
#: on a genuine pet fee.
#:
#: The guard is NOT relaxed. Instead the pet word must appear INSIDE the match,
#: bound to the charge noun as its modifier -- which is the same argument
#: ``_BASIS_FIRST_CHARGE_RE`` already makes for requiring the pet word in its
#: label. A charge named "the pet rate" is bound to pets by its own name and
#: does not need proximity adjudicated.
#:
#: At most ONE adjective may stand between, and it may not be a word that closes
#: the pet clause. That is what keeps the room-rate hole shut: in "No Pets
#: Allowed Discounted rate: $160" the word after "Pets" is "Allowed", which ends
#: the pet statement and begins a separate noun phrase about the room.
_CLAUSE_CLOSING_WORDS = r"allowed|permitted|welcome|welcomed|accepted|not|are|is"
_PET_NAMED_CHARGE_RE = re.compile(
    r"\b(?:pets?|dogs?|cats?|animals?)[\s-]+"
    r"(?!(?:" + _CLAUSE_CLOSING_WORDS + r")\b)"
    r"(?:[a-z]+[\s-]+)?"
    # ``price`` and ``cost`` are charge nouns exactly as ``fee`` and ``rate``
    # are. "Pet Fees Price : $40 / NIGHT" was read as nothing, because the word
    # PRICE is also a room-rate marker and ``_pet_context`` therefore refused
    # the amount -- the same collision 029 found with "the Pet Friendly rate",
    # and the same answer: the pet word is INSIDE the label, so the label binds
    # the charge and no proximity is left to adjudicate.
    r"(?:fee|fees|charge|charges|rate|rates|price|prices|cost|costs)\b\s*"
    r"(?:is|are|of|:|=)?\s*"
    r"(?:\$\s*(?P<dollars>[\d,]+(?:\.\d{1,2})?)"
    r"|(?P<usd>[\d,]+(?:\.\d{1,2})?)\s*USD\b)"
    r"(?:\s*(?:per|/|a)\s*(?P<basis>night|day|stay|nightly|daily)\b)?",
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

#: The same two species named as an ACCEPTANCE rather than as an exclusivity:
#: "Dogs and cats allowed", "Cats and dogs are welcome". The pattern above
#: required the word "only", so a property that named both species and did not
#: claim exclusivity recorded no species at all -- the most explicit statement
#: a surface can make about species, dropped for want of one word.
#:
#: A refusal cannot reach this: "Dogs and cats are not allowed" puts "not"
#: where the verb has to be, so the alternation simply does not match.
_BOTH_SPECIES_ACCEPTED_RE = re.compile(
    r"\b(?:dogs?|cats?)\s*(?:and|&|/|or)\s*(?:dogs?|cats?)\s+"
    r"(?:are\s+)?(?:allowed|welcome|permitted|accepted)\b",
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
    # "allow up to two dogs", "maximum 2 dogs", "no more than three pets".
    # A ceiling with the species named and NO scope stated.
    #
    # Every existing form here needs one of three things the wording above does
    # not have: the literal word "pet", the number in figures, or a "per room"
    # scope. Two of those are already optional elsewhere in this tuple -- the
    # "2 dogs max" form names a species and states no scope -- so the only
    # thing that was really required was the word "max" standing AFTER the
    # number rather than a "up to" standing before it.
    #
    # No scope is recorded. The surface has said how many animals it accepts
    # and has not said whether that is per room or per reservation, and
    # ``pet_count_scope`` is not emitted unless the source states it.
    re.compile(r"(?:up\s+to|maximum(?:\s+of)?|max\.?|no\s+more\s+than)\s+"
               r"(?:(?P<count>\d+)|(?P<word>one|two|three|four|five))\s+"
               r"(?:pets?|dogs?|cats?)\b", re.IGNORECASE),
    # "Maximum number of pets is 2", "Maximum number of pets : 3".
    #
    # A LABEL and a VALUE, with the number after the noun instead of before it.
    # Every form above puts the figure first, so a table that states the same
    # fact as a row read as nothing at all.
    #
    # The animal is REQUIRED in the label. Without it "Maximum number of guests
    # is 4" and "Maximum occupancy : 4" are the same shape, and a room's
    # occupancy is not a pet limit. No scope is recorded: the surface stated a
    # ceiling and did not say per room.
    re.compile(r"max(?:imum)?\s+(?:number\s+of\s+|no\.?\s+of\s+)?"
               r"(?:pets?|dogs?|cats?)\s*(?:allowed\s*)?"
               r"(?:\b(?:is|are)\b|:|=)\s*"
               r"(?:(?P<count>\d+)|(?P<word>one|two|three|four|five))\b",
               re.IGNORECASE),
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
    # "The size limit for any one dog shall be 80 pounds."
    #
    # A limit NOUN carrying its value after a copula, rather than a maximum
    # word carrying it directly. Every pattern above needs "weight" as the noun
    # or a lead-in immediately before the figure; this shape has a different
    # noun ("size limit") and puts several words between it and the number.
    #
    # The gap is bounded and may not cross a full stop, so the noun and the
    # figure must be in one sentence -- otherwise a limit in one statement
    # would collect a number from the next.
    # ``\b`` was guarding the whole alternation, and a colon is not a word --
    # so a word boundary in front of it could never match one. "Individual pet
    # weight limit : 150 Pounds" therefore failed on a rule written to accept
    # exactly that shape. The boundary now guards the WORD copulas alone.
    # Found by PTF-LABEL-VALUE-POLICY-READER-HARDENING-033.
    re.compile(r"\b(?:size|weight)\s+(?:limit|restriction)\b[^.]{0,48}?"
               r"(?:\b(?:is|are|shall\s+be|will\s+be|of)\b|:)\s*"
               r"(?P<value>[\d,]+(?:\.\d+)?)\s*"
               r"(?P<unit>lbs?|pounds?|kgs?)\b", re.IGNORECASE),
)

#: Language that makes a stated weight a figure for SEVERAL animals together.
#: An individual limit may not be inferred from it: "up to two dogs, combined
#: weight not to exceed 100 pounds" says nothing about how heavy one dog may
#: be, and publishing 100 lb as the pet weight limit would invite a guest to
#: arrive with a 100 lb dog the property never agreed to.
#:
#: Found by this work order's corpus rather than by a capture -- the reader was
#: reading combined weights as individual ones and no case had asked it to.
_COMBINED_WEIGHT_RE = re.compile(
    r"\b(?:combined|total|aggregate|together)\b", re.IGNORECASE)

#: How far in front of a weight figure the combining word may sit and still be
#: understood as qualifying it. One clause, not one block.
_COMBINED_WEIGHT_LOOKBACK_CHARS = 40


def _weight_is_combined(text: str, match) -> bool:
    """Whether this weight is stated for several animals at once."""
    start = max(0, match.start() - _COMBINED_WEIGHT_LOOKBACK_CHARS)
    return bool(_COMBINED_WEIGHT_RE.search(text[start:match.end()]))

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
    r"|\bin\s+(?:suites?|studios?|villas?|cabins?|cottages?)\b"
    # ---- duration bands stated WITHOUT a preposition ---------------------- #
    # Added by PTF-GENERIC-READER-BANDED-FEE-AND-HILTON-CONTAINER-HARDENING-024.
    # Every pattern above needs "for" ("for stays of", "for 2-4 nights"). Some
    # chains state the same fact without a preposition, and five properties in
    # one market asserted an understated fee because of it:
    #
    #     $50(1-4 nights),$125(5+ nights)     parenthesised range, open band
    #     $75/stay 1-4 nights, $125/stay 5+   bare range, bare open band
    #     $75 for the first four nights       the count spelled as a word
    #
    # Same semantic fact as the forms above -- one pet, two prices, chosen by
    # how long the guest stays -- and the schema holds one amount and one basis.
    #
    # Safe to add because a tier still requires MORE THAN ONE DISTINCT PRICE.
    # A capped fee ("25 USD nightly, max 75 USD per stay") has two prices and
    # no duration band; a single-priced policy that mentions a night range has
    # a band and one price. Neither becomes a tier.
    r"|\(\s*\d+\s*(?:-|to|–)\s*\d+\s*nights?\s*\)"
    r"|\(\s*\d+\s*\+\s*nights?\s*\)"
    r"|\b\d+\s*\+\s*nights?\b"
    r"|\bfor\s+\d+\s*\+"
    r"|\b\d+\s*(?:-|to|–)\s*\d+\s*nights?\b"
    r"|\bfirst\s+(?:one|two|three|four|five|six|seven|\d+)\s+nights?\b",
    re.IGNORECASE)

#: Recurring wording stated as an adjective. The charge patterns need "per
#: day"; "$20 daily pet fee" states the same recurring charge in a form none of
#: them match. Used only to detect a component the charges did not capture.
#:
#: REPAIRED by work order 035. The two boundaries here were literal BACKSPACE
#: characters (U+0008), not word boundaries -- a heredoc mangled them when the
#: rule was written -- so the pattern could only ever match a control character
#: no scraped page contains, and this detection had never fired once. 034 found
#: it, measured the consequence and deliberately left it alone rather than
#: demote a row while doing something else; 035 was commissioned to close it.
#:
#: The repair is the two characters and nothing else. The guard around the
#: search is unchanged: it fires only where NO charge already carries a
#: nightly or daily basis, and only where the word stands in pet context, so
#: a parking charge billed daily and a fee already read as per_day are both
#: untouched.
_RECURRING_WORD_RE = re.compile(r"\b(?:daily|nightly)\b", re.IGNORECASE)

#: Two or more DISTINCT prices on the surface. A tier needs both this and the
#: qualifier above: a cap has two prices and no qualifier, and a single-priced
#: policy that mentions a night range has a qualifier and one price. Neither is
#: a tier, and withholding either would lose a fact the schema can hold.
_PRICE_RE = re.compile(
    r"\$\s*\d+(?:[.,]\d{2})?|\b\d+(?:[.,]\d{2})?\s*(?:usd|dollars?)\b",
    re.IGNORECASE)


#: A tier priced at nothing. "One pet stays free. Second pet $15 per night" has
#: two prices, and one of them is zero -- but zero is written in words, so the
#: two-distinct-prices test saw a single price and let $15 through as THE pet
#: fee. A guest with one dog would have been quoted $15 a night to bring an
#: animal this hotel takes for nothing.
_FREE_TIER_RE = re.compile(
    r"\b(?:stays?|stay|is|are)\s+free\b|\bfree\s+of\s+charge\b"
    r"|\bat\s+no\s+(?:charge|cost|fee)\b|\bno\s+(?:charge|fee)\s+for\b",
    re.IGNORECASE)


def _fee_is_tiered(block_text: str) -> bool:
    """Does this surface price the same pet differently by stay or by count?

    A tier needs a qualifier AND more than one price. A stated FREE is a price:
    it is what the surface charges for that pet, and counting only the numbers
    made a two-tier policy look like a one-price one.
    """
    if not _TIERED_FEE_RE.search(block_text):
        return False
    prices = {re.sub(r"[^\d.]", "", m.group(0))
              for m in _PRICE_RE.finditer(block_text)}
    distinct = {p for p in prices if p}
    if _FREE_TIER_RE.search(block_text):
        distinct.add("0")
    return len(distinct) > 1

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

#: How far in front of a stated purpose a pet word may sit and still be
#: understood as qualifying it. Short on purpose: "pet security deposit" is one
#: noun phrase; "pets welcome, and a security deposit" is two clauses.
_PURPOSE_QUALIFIER_CHARS = 16

#: A charge whose own sentence names a purpose that is not a pet. "for
#: incidentals", "for all guests" -- the surface has said who pays it, and it
#: is everyone.
#: ``security deposit`` and ``damage deposit`` name a purpose every guest pays
#: for, and they beat a pet word that merely sits in the same sentence. Under
#: the nearest-wins rule below they cost a genuine "pet security deposit"
#: nothing: there the pet word is adjacent to the amount and wins the tie.
#: ``parking``, ``smoking``, ``resort fee`` and ``valet`` were added by
#: PTF-LABEL-VALUE-POLICY-READER-HARDENING-033, which caught this reader
#: publishing "Resort fee : $29 per night" and "Smoking fee : $250 per stay" as
#: the PET fee, because a pet word stood in the same block. The LOCATOR has
#: refused those four since 032 and the reader had never been told; two layers
#: that disagree about whose charge an amount is will always publish the more
#: permissive answer.
_NON_PET_PURPOSE_RE = re.compile(
    r"\bincidental(?:s)?\b|\bfor\s+all\s+guests\b|\ball\s+guests\b"
    r"|\bsecurity\s+deposit\b|\bdamage\s+deposit\b"
    r"|\bparking\b|\bsmoking\b|\bresort\s+fee\b|\bvalet\b",
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
        # A purpose the pet wording itself QUALIFIES is not a rival: "pet
        # security deposit" is a security deposit for a pet, and the pet word
        # modifies the phrase rather than merely sitting near it. Without this
        # the phrase always won, because it overlaps the amount's own label and
        # so scores a distance of zero that no adjacent word can beat.
        # ...within the SAME statement. A pet word on the other side of a full
        # stop qualifies nothing: "Pets welcome. Resort fee : $29 per night."
        # exempted the resort fee because the word "Pets" stood fourteen
        # characters back, and the reader then published a charge every guest
        # pays as the price of bringing an animal.
        # Found by PTF-LABEL-VALUE-POLICY-READER-HARDENING-033.
        if _pet_qualifies(text, purpose.start()):
            continue
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
    #: Whether the species wording claimed EXCLUSIVITY ("Dogs only") or merely
    #: named a species the property takes ("All dogs are welcome"). Both are
    #: recorded as species evidence and neither is read as a prohibition, but
    #: they are not the same statement and the reading says which one it holds.
    species_exclusive: bool = False
    fee_cap: Optional[Dict] = None
    fee_cap_quote: str = ""
    #: Charge components the surface states that no charge carries.
    unrepresented: Tuple[Dict, ...] = ()
    #: Amounts the surface states that were attributed to a purpose OTHER than
    #: a pet, and so were not read as a pet charge. Kept apart from
    #: ``unrepresented`` deliberately: an unrepresented component means the
    #: charge we produced is incomplete and the fee must be withheld, whereas
    #: this means the surface itself said the money is for something else. The
    #: first is our failure to represent; the second is the page's own
    #: statement, and recording it as a non-inference is what stops it
    #: vanishing without trace.
    excluded_amounts: Tuple[Dict, ...] = ()
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
                "unrepresented": [dict(u) for u in self.unrepresented],
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
        return _drop_swallowed_pet_terms(text, segment, match)
    start = max(0, match.start() - 100)
    end = min(len(text), match.end() + 140)
    return _drop_swallowed_pet_terms(text, text[start:end].strip(), match)


#: Terms that price or cap an ORDINARY pet. A service-animal exception exists to
#: say a charge does NOT apply, so one of these standing AHEAD of the phrase is
#: the property's pet policy, not a term on service animals.
_PET_TERM_BEFORE_SERVICE_RE = re.compile(
    r"\b(?:\d+\s*(?:lb|lbs|pound|pounds)|per\s+night|per\s+pet|per\s+room|"
    r"limit\s+of|\d+\.\d\d\s*USD|USD\s*\d|\$\s*\d|max(?:imum)?\s+\d)",
    re.IGNORECASE)


def _drop_swallowed_pet_terms(text: str, quote: str, match) -> str:
    """Trim a published service-animal quote back to the phrase when the words
    in front of it are the property's PET terms.

    ``_service_animal_span`` already refuses to read a limit stated before the
    phrase as a limit on service animals, and says why: "A limit written BEFORE
    the words 'service animals' cannot be a limit on service animals, so the
    span starts at the phrase." That reasoning governed which limits were
    ATTRIBUTED and never the quote that was PUBLISHED, so the two disagreed.

    Choice writes "... with a 40.00 USD, per night, Limit of one pet per room,
    and 20 pounds max Service animals are permitted, without charge." with no
    full stop before "Service". ``_segment_containing`` therefore opens the
    segment well ahead of the phrase, and the published record stated that
    SERVICE ANIMALS cost $40 a night and were capped at 20 pounds -- a
    guest-visible, ADA-adjacent misstatement. PTF-ST-LOUIS-FOUNDER-REVIEW-003
    found two of them in one market.

    The trim is deliberately conditional. Only a prefix carrying a price, a
    weight or a count is removed, so "Only service animals are permitted" keeps
    its "Only" -- that word changes the meaning of the sentence and nothing
    about it belongs to the pet policy. The result stays a contiguous substring
    of the block, so the evidence contract's contiguity check is unaffected.
    """
    if not quote or match is None:
        return quote
    offset = text.find(quote)
    if offset < 0 or match.start() <= offset:
        return quote
    prefix = text[offset:match.start()]
    if not _PET_TERM_BEFORE_SERVICE_RE.search(prefix):
        return quote
    return text[match.start():offset + len(quote)].strip()


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


#: A refusal that names WHERE, not whether. "Pets are not allowed in the
#: shopping galleria", "dogs are not permitted in the pool area", "no pets in
#: the restaurant" -- a pet-friendly hotel telling a guest which room their dog
#: may not walk into. (Named after no property on purpose: the rule is about
#: the shape of the sentence, and a reader that recognises a hotel is a reader
#: that has stopped reading.)
#:
#: Read as a refusal it does two wrong things at once: it denies an acceptance
#: the same page states in its first sentence, and it produces a
#: SOURCE_CONTRADICTORY the source never made. One property was HELD out of
#: publication by a founder for exactly that reason -- the machine told them
#: the page contradicted itself, and the page does not.
#: GUEST ACCOMMODATION IS NOT ONE OF THESE PLACES. "Pets are not allowed
#: in guest rooms" is a refusal at a hotel, not a restriction, and the
#: first draft of this pattern listed room, suite, floor and balcony and
#: quietly turned that refusal into silence. Only shared and public
#: spaces belong here.
#: Found by PTF-...-IDENTITY-RESOLUTION-AND-FULL-CLOSURE-038 (the market name
#: is left out on purpose: this test suite forbids a reader that knows one).
_PLACE_QUALIFIED_REFUSAL_RE = re.compile(
    r"\b(?:in|inside|on|within|near|around|at)\s+"
    r"(?:the|our|any|all|either)?\s*"
    r"(?:[a-z][\w'-]*\s+){0,3}?"
    r"(?:area|areas|lobby|pool|spa|gym|fitness|restaurant|bar|"
    r"dining|patio|deck|terrace|galleria|mall|garden|elevator|"
    r"breakfast|lounge|club|beach|"
    r"playground|centre|center|shop|store|market|hall|space|spaces)\b",
    re.IGNORECASE)

#: How far past the refusal the place may sit. One clause: "not allowed in the
#: pool area" and not "not allowed. Our pool area is open until ten".
_PLACE_QUALIFIER_CHARS = 44


def _refusal_names_a_place(text: str, match) -> bool:
    """Whether a refusal is about WHERE a pet may go rather than whether."""
    window = text[match.end():match.end() + _PLACE_QUALIFIER_CHARS]
    stop = re.search(r"[.;]", window)
    if stop:
        window = window[:stop.start()]
    return bool(_PLACE_QUALIFIED_REFUSAL_RE.match(window.strip())
                or _PLACE_QUALIFIED_REFUSAL_RE.match(window.lstrip()))


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


def _pet_qualifies(text: str, position: int) -> bool:
    """Whether a pet word stands on the noun beginning at ``position``.

    One rule, two callers: a purpose the pet wording QUALIFIES is not a rival
    purpose, and a cleaning noun the pet wording qualifies is not a separate
    cleaning charge. The lead never crosses a full stop, because a pet word in
    the previous sentence qualifies nothing.
    """
    lead = text[max(0, position - _PURPOSE_QUALIFIER_CHARS):position]
    lead = lead[lead.rfind(".") + 1:]
    return bool(_PET_CONTEXT_RE.search(lead))


#: A cleaning charge whose LABEL comes first: "Cleaning fee : $75 per stay".
#: ``_PROSE_CLEANING_RE`` reads the other order -- amount, then the word -- so a
#: table that puts the label in front of the value stated a cleaning charge the
#: reader could not see, and the amount then competed with the pet fee as a
#: second unexplained charge.
_LABEL_FIRST_CLEANING_RE = re.compile(
    r"\bclean(?:ing)?\b[^.$]{0,24}?"
    r"(?:\$\s*(?P<dollars>[\d,]+(?:\.\d{1,2})?)"
    r"|(?P<usd>[\d,]+(?:\.\d{1,2})?)\s*USD\b)",
    re.IGNORECASE)

#: How far past a cleaning word an amount may sit and still be ITS amount.
_CLEANING_LABELS_FORWARD_CHARS = 24


def _cleaning_amounts(text: str) -> set:
    """Amounts the surface itself calls a cleaning charge.

    TWO ORDERS, AND ONE TRAP
    ------------------------
    A property may write "$75 per stay cleaning fee" or "Cleaning fee : $75",
    and both are the same statement. Only the first was read.

    The trap is what the first pattern does when a cleaning word labels the
    NEXT amount rather than the last one. Hyatt Place Airport's block reads::

        Pet Fees 1-6 nights : $100 / STAY 7-30 nights + additional cleaning
        fee : $200 / STAY

    and the backward rule attached "cleaning" to $100 -- the FIRST band of the
    pet fee, twenty-five characters earlier. The row then published
    ``cleaning_fee: $100``, which is not a cleaning fee and is not $100 of
    anything a guest pays for cleaning.

    So a cleaning word that is plainly the label of a FOLLOWING amount does not
    also claim a preceding one. Found by
    PTF-LABEL-VALUE-POLICY-READER-HARDENING-033.
    """
    text = text or ""
    labelled_forward = set()
    for match in _LABEL_FIRST_CLEANING_RE.finditer(text):
        raw = match.group("dollars") or match.group("usd")
        if not raw:
            continue
        if _pet_qualifies(text, match.start()):
            # "There is a pet cleaning fee of $100 per stay" is the charge for
            # bringing an animal, whatever the property files it under, and the
            # reader has always read it as the pet fee. A pet word standing on
            # the noun makes the charge a PET charge -- the same rule
            # ``_pet_context`` applies to "pet security deposit" -- so this
            # pass does not take it away and turn a stated pet price into a
            # cleaning line with no pet price beside it.
            continue
        labelled_forward.add(_amount_minor(raw))

    amounts = set(labelled_forward)
    for match in MS._PROSE_CLEANING_RE.finditer(text):
        word = re.search(r"\bclean(?:ing)?\b", match.group(0), re.IGNORECASE)
        if word is not None:
            after = text[match.start() + word.end():
                         match.start() + word.end()
                         + _CLEANING_LABELS_FORWARD_CHARS]
            if _LABEL_FIRST_CLEANING_RE.search(
                    match.group(0)[word.start():] + after):
                # The word labels the amount that FOLLOWS it, so it does not
                # also label the one behind it.
                continue
        amounts.add(_amount_minor(match.group("amount")))
    return amounts


def _cleaning_is_inside_a_band(reading, charge) -> bool:
    """Whether a cleaning amount is one price of a banded pet fee.

    A real cleaning fee stands beside the pet fee: "Pet fee $50 per stay.
    Cleaning fee : $75 per stay" is two charges and both are publishable. A
    banded one stands INSIDE it, as the second half of a duration ladder, and
    then the amount is not separable from the price it bands.

    The test is not the cleaning wording -- that is what mislabels these -- but
    whether the surface prices its pets in bands at all, and whether this
    amount is one of the prices in that structure.
    """
    if not _fee_is_tiered(reading.block_text):
        return False
    others = {c.amount_minor for c in reading.charges
              if c is not charge and c.kind != "deposit"}
    return bool(others) and charge.amount_minor not in others


def _first_match(text: str, patterns: Sequence[re.Pattern], label: str,
                 accept=None):
    for index, pattern in enumerate(patterns):
        match = next((m for m in pattern.finditer(text)
                      if accept is None or accept(m)), None)
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

    cleaning_amounts = _cleaning_amounts(text)

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

    # --- the label states the basis and the amount follows ----------------- #
    #
    # Runs before the amount-first passes so the basis its own label carries is
    # the one recorded, rather than whatever a later loose match finds to the
    # right of the number.
    for match in _BASIS_FIRST_CHARGE_RE.finditer(text):
        raw = match.group("dollars") or match.group("usd")
        if not raw:
            continue
        if not _pet_context(text, match.start(), match.end()):
            notes.append("ignored the amount %r: no pet wording within %d "
                         "characters"
                         % (text[match.start():match.end()], _PET_CONTEXT_CHARS))
            continue
        amount = _amount_minor(raw)
        window = text[max(0, match.start() - 60):match.end() + 40]
        refundable = (False if _NONREFUNDABLE_RE.search(window)
                      else True if _REFUNDABLE_RE.search(window) else None)
        charges.append(Charge(
            amount_minor=amount,
            basis=_BASIS_BY_WORD[match.group("basis").lower()], scope="",
            origin="prose", refundable=refundable,
            quote=text[match.start():match.end()],
            cleaning_labelled=amount in cleaning_amounts))
        fired.append("basis_first_charge")

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

    # --- a charge the surface names as the pet's --------------------------- #
    #
    # Runs LAST and only fills gaps, exactly as the loose pass above does. An
    # amount another pass already turned into a charge is left where it is:
    # claiming it here would move it from the LABELLED lane into the prose
    # lane, and the two mean different things downstream. WoodSpring states two
    # labelled pet fees and no basis, which is SOURCE_AMBIGUOUS -- "the surface
    # names two charges and does not say which is the fee". Re-homing them
    # turned that into SOURCE_SILENT, which claims the surface stated nothing,
    # and the surface stated two.
    #
    # It runs WITHOUT ``_pet_context``. The pet word is INSIDE the match, bound
    # to the charge noun, so there is no proximity left to adjudicate -- the
    # same argument ``_BASIS_FIRST_CHARGE_RE`` makes for requiring the pet word
    # in its label. See ``_PET_NAMED_CHARGE_RE``.
    for match in _PET_NAMED_CHARGE_RE.finditer(text):
        raw = match.group("dollars") or match.group("usd")
        if not raw:
            continue
        amount = _amount_minor(raw)
        if amount in explained:
            continue
        basis_word = match.group("basis")
        window = text[max(0, match.start() - 60):match.end() + 40]
        refundable = (False if _NONREFUNDABLE_RE.search(window)
                      else True if _REFUNDABLE_RE.search(window) else None)
        charges.append(Charge(
            amount_minor=amount,
            basis=_BASIS_BY_WORD[basis_word.lower()] if basis_word else "",
            scope="", origin="labelled_amount", refundable=refundable,
            quote=text[match.start():match.end()],
            cleaning_labelled=amount in cleaning_amounts))
        explained.add(amount)
        fired.append("pet_named_charge")

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

    # --- charge components nothing above explained ------------------------- #
    #
    # Added by PTF-GENERIC-READER-BANDED-FEE-AND-HILTON-CONTAINER-HARDENING-024,
    # generalising the rule PTF-MARRIOTT-ACCORDION-LOCATOR-HARDENING-021 proved
    # inside marriott_surface. The semantic fact is domain-independent: when a
    # surface states money this reader did not turn into a charge, the charge it
    # DID produce is not the whole price.
    #
    #     $75 per pet (dogs, fish, or birds) Non-Refundable Pet Fee Per Stay:
    #     $150.00
    #
    # left $75 unexplained and published $150 as the pet fee. A guest with one
    # pet is quoted the wrong number, and it looks complete.
    #
    # ``explained_amounts`` already carries every charge and the fee cap, so a
    # ceiling is not an unexplained amount and a capped fee stays structured --
    # the founder rule CEILING != PRICE is preserved rather than re-litigated.
    # ``_pet_context`` keeps room rates and parking charges out.
    unexplained: List[Dict] = []
    excluded: List[Dict] = []
    for match in _PRICE_RE.finditer(text):
        raw = re.sub(r"[^\d.]", "", match.group(0))
        if not raw:
            continue
        amount = _amount_minor(raw)
        if amount in explained_amounts:
            continue
        if not _pet_context(text, match.start(), match.end()):
            excluded.append({
                "amount_minor": amount,
                "quote": text[max(0, match.start() - 60):match.end() + 20],
                "note": ("the surface states this amount for a purpose it "
                         "does not name as a pet's, so it is not read as a "
                         "pet charge"),
            })
            continue
        unexplained.append({
            "kind": "amount_not_represented",
            "amount_minor": amount,
            "quote": text[match.start():match.end()],
            "note": ("the surface states this amount and no charge read from "
                     "it carries the figure"),
        })
        explained_amounts.add(amount)

    # A recurring charge stated as an ADJECTIVE: "$20 daily pet fee". The
    # charge patterns need "per day"; the fact is the same and a per-stay
    # figure alone understates what a stay costs.
    if _RECURRING_WORD_RE.search(text) and not any(
            c.basis in (enums.BASIS_PER_NIGHT, enums.BASIS_PER_DAY)
            for c in charges):
        recurring = _RECURRING_WORD_RE.search(text)
        if _pet_context(text, recurring.start(), recurring.end()):
            unexplained.append({
                "kind": "recurring_charge_not_represented",
                "amount_minor": None,
                "quote": text[max(0, recurring.start() - 30):recurring.end() + 30],
                "note": ("the surface states a recurring charge and every "
                         "charge read from it is one-off"),
            })

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
    if weight_match is not None and _weight_is_combined(text, weight_match):
        # The winning match is a COMBINED weight while the same surface also
        # states an individual one. Pattern precedence, not position, decides
        # which match wins, so a loose bare-number pattern reading "150 Pounds
        # Maximum" out of the COMBINED row beat the explicit "Individual pet
        # weight limit : 150 Pounds" that a later pattern read.
        #
        # Dropping it there lost a weight the surface states plainly -- both
        # Hyatt blocks print the individual limit first and the combined one
        # second, and both published no weight at all. So an individual
        # statement is preferred to a combined one wherever the surface makes
        # both; only a surface that states nothing BUT a combined weight falls
        # through to the note below.
        # Found by PTF-LABEL-VALUE-POLICY-READER-HARDENING-033.
        individual = _first_match(
            text, _WEIGHT_RES, "weight",
            accept=lambda m: not _weight_is_combined(text, m))
        if individual[0] is not None:
            weight_match, weight_pattern = individual

    weight_value = weight_unit = weight_quote = None
    if weight_match and _weight_is_combined(text, weight_match):
        # The figure is for several animals together. Recorded as a note and
        # not as a limit: no individual weight is inferred from a combined one.
        notes.append("ignored the weight %r: the surface states it for the "
                     "animals combined, and an individual limit cannot be "
                     "inferred from a combined one"
                     % text[weight_match.start():weight_match.end()])
        weight_match = None
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
    # Exclusive wordings first, then the merely affirmative ones. Which kind
    # matched is remembered: "Dogs only" says something about cats and "All
    # dogs are welcome" does not, and a reading that cannot tell them apart
    # cannot be asked the difference later.
    dogs_exclusive = MS._DOGS_ONLY_RE.search(text)
    dogs_mentioned = re.search(r"\bdogs?\s+(?:are\s+)?(?:allowed|welcome|"
                               r"permitted)\b", text, re.IGNORECASE)
    dogs_only = dogs_exclusive or dogs_mentioned
    cats_refused = MS._CATS_REFUSED_RE.search(text)
    both_exclusive = _BOTH_SPECIES_RE.search(text)
    both_species = (both_exclusive or _BOTH_SPECIES_ACCEPTED_RE.search(text)
                    or _SPECIES_PAIR_RE.search(text))
    species_exclusive = bool(both_exclusive
                             or (dogs_exclusive and not both_species))
    service = MS._SERVICE_ANIMAL_RE.search(text)

    refused, refused_pattern = _first_match(text, _PETS_REFUSED_RES, "refused")
    if refused and _refusal_names_a_place(text, refused):
        # A place, not a policy. Recorded as a note so the sentence is not
        # lost, and skipped as a refusal: the next candidate refusal, if the
        # surface makes one, is still found below.
        notes.append(
            "read %r as a restriction on WHERE a pet may go and not as a "
            "refusal of pets: the sentence names a place"
            % text[refused.start():min(len(text), refused.end() + 40)])
        remaining, remaining_pattern = _first_match(
            text, _PETS_REFUSED_RES, "refused",
            accept=lambda m: (m.start() > refused.start()
                              and not _refusal_names_a_place(text, m)))
        refused, refused_pattern = remaining, remaining_pattern
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
        species_exclusive=species_exclusive,
        fee_cap=fee_cap, fee_cap_quote=fee_cap_quote,
        unrepresented=tuple(unexplained),
        excluded_amounts=tuple(excluded),
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


# --------------------------------------------------------------------------- #
# Structured fees: the schema-1.2 shapes this reader used to refuse to build.
# --------------------------------------------------------------------------- #
#
# Work order 034, reader-to-tiers.
#
# Schema 1.2 has held ``fee_tiers[]`` and ``fee_pet_schedule`` since the policy
# migration, and Cleveland's founder adjudications wrote them by hand. The
# automated reader never emitted either: it detected a band, said the
# vocabulary holds one amount, and withheld the price as
# SCHEMA_CANNOT_REPRESENT. Twenty-nine rows in one market sat there.
#
# The withholding was right about the SIMPLE field and wrong about the schema.
# What follows reads the band structure itself, and it emits only when the
# source fully determines the rule -- because a half-read ladder is a worse
# answer than a held one.

#: Numbers a policy spells rather than prints. "the first four nights".
_BAND_WORD_NUMBERS: Dict[str, int] = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}

#: The unit a stay-length band counts in. ``n`` and ``nt`` are here because
#: Hilton's own field abbreviates: "$75(1-4n), $125(5+n)".
_BAND_UNIT = r"(?:nights?|nites?|nts?|n|days?)"

#: Every way this corpus states a range of nights, in one alternation so that
#: two readings of the same characters cannot both match. Order matters:
#: "first four nights" must be read before "four nights", and "up to 5 nights"
#: before the bare closed range.
_STAY_RANGE_RE = re.compile(
    r"first\s+(?P<first_hi>\d{1,3}|one|two|three|four|five|six|seven|eight|nine|ten)"
    r"\s*" + _BAND_UNIT + r"\b"
    r"|up\s+to\s+(?P<upto_hi>\d{1,3})\s*" + _BAND_UNIT + r"\b"
    r"|(?:over|above|more\s+than)\s+(?P<over_lo>\d{1,3})\s*" + _BAND_UNIT + r"\b"
    r"|(?P<ormore_lo>\d{1,3})\s+or\s+more\s*(?:" + _BAND_UNIT + r"\b)?"
    r"|(?P<closed_lo>\d{1,3})\s*(?:-|–|to|through)\s*(?P<closed_hi>\d{1,3})"
    r"\s*" + _BAND_UNIT + r"\b"
    r"|(?P<plus_lo>\d{1,3})\s*\+\s*(?P<plus_unit>" + _BAND_UNIT + r"\b)?"
    # A single night, including the abbreviated unit a chain packs into its
    # own field: one chain writes
    # "$50(1n),$75(2-4n),$125(5+n)". Reading only the last two rungs made a
    # three-rung ladder look like one that starts at night two -- a refusal --
    # and that row was already publishing no fee at all while its page
    # printed three.
    r"|(?P<single_n>\d{1,3})\s*(?:night|nite|nt|n|day)\b(?!s)",
    re.IGNORECASE)

#: An amount, wherever it is written. Shares its vocabulary with ``_PRICE_RE``
#: but keeps the digits in a group so the value can be read off.
_BAND_AMOUNT_RE = re.compile(
    r"\$\s*(?P<dollars>\d[\d,]*(?:\.\d{2})?)"
    r"|(?P<usd>\d[\d,]*(?:\.\d{2})?)\s*(?:USD|dollars?)\b",
    re.IGNORECASE)

#: The basis a band states for ITSELF: "$75/stay 1-4 nights", "$100 / STAY".
_BAND_BASIS_RE = re.compile(
    r"/\s*(?P<slash>stay|night|nite|day)s?\b"
    r"|per\s+(?P<per>stay|night|day)\b"
    r"|\b(?P<adverb>nightly|daily)\b",
    re.IGNORECASE)

#: The scope a band states for itself. Never inferred, per the frozen rules.
_BAND_SCOPE_RE = re.compile(r"per\s+(?P<what>pet|dog|cat|room|unit)\b",
                            re.IGNORECASE)

#: A ceiling standing in front of an amount. "Up to 75 dollars", "not to
#: exceed $15", "maximum of $150". CEILING != PRICE is a founder rule, and a
#: band ladder whose rungs are ceilings prices nothing.
_BAND_CEILING_RE = re.compile(
    r"(?:up\s+to|not\s+to\s+exceed|maximum\s+of|max(?:imum)?)\s*"
    r"(?:\$\s*\d|\d[\d,]*(?:\.\d{2})?\s*(?:USD|dollars?))",
    re.IGNORECASE)

#: A recurrence the published vocabulary does not have. FEE_BASES holds
#: per_night, per_day and per_stay and nothing else, so "$75 weekly" and "$75
#: per 7 day stay" can be neither recorded nor mapped onto a neighbour --
#: per_day is deliberately not per_night and a week is not either of them.
#:
#: Emitting the amount with ``basis_stated: false`` would be worse than
#: withholding: it says the source named no recurrence when the source named
#: one this schema cannot hold. So the ladder is refused and the words survive
#: in the evidence quote.
_BAND_UNSUPPORTED_BASIS_RE = re.compile(
    r"\b(?:weekly|monthly|biweekly|fortnightly)\b"
    r"|per\s+\d+\s*(?:day|night|week)s?\b"
    r"|per\s+(?:week|month)\b",
    re.IGNORECASE)

#: A qualifier on the PRICE that a tier has nowhere to put. ``pet_fee`` carries
#: ``tax_relationship``; a tier does not, so a band stated "plus applicable
#: taxes" would publish a number the guest does not pay.
_BAND_TAX_RE = re.compile(
    r"plus\s+(?:applicable\s+)?tax(?:es)?\b|\+\s*tax\b|before\s+tax(?:es)?\b",
    re.IGNORECASE)

#: Conditions schema 1.2 has no condition_type for. Each one makes the ladder
#: unrepresentable rather than merely incomplete.
_BAND_ROOM_TYPE_RE = re.compile(
    r"\bin\s+(?:the\s+)?(?:suites?|studios?|villas?|cabins?|cottages?|"
    r"penthouses?)\b", re.IGNORECASE)
_BAND_SPECIES_PRICED_RE = re.compile(
    r"\bdogs?\b[^.]{0,30}?(?:\$\s*\d|\d[\d,]*\s*USD)[^.]{0,60}?"
    r"\bcats?\b[^.]{0,30}?(?:\$\s*\d|\d[\d,]*\s*USD)"
    r"|\bcats?\b[^.]{0,30}?(?:\$\s*\d|\d[\d,]*\s*USD)[^.]{0,60}?"
    r"\bdogs?\b[^.]{0,30}?(?:\$\s*\d|\d[\d,]*\s*USD)",
    re.IGNORECASE)
#: TWO prices, each with its own weight qualifier. One weight beside one price
#: is a weight LIMIT printed next to a fee -- Hilton ends its field
#: "(2max under 75lbs)" -- and reading that as weight-conditioned pricing held
#: two readable ladders for a condition neither surface states.
_BAND_WEIGHT_PRICED_RE = re.compile(
    r"(?:\$\s*\d[\d,]*|\d[\d,]*\s*USD)[^.]{0,20}?"
    r"(?:under|over|below|above)\s*\d{1,3}\s*(?:lbs?|pounds?|kgs?)"
    r"[^.]{0,60}?(?:\$\s*\d[\d,]*|\d[\d,]*\s*USD)[^.]{0,20}?"
    r"(?:under|over|below|above)\s*\d{1,3}\s*(?:lbs?|pounds?|kgs?)"
    r"|(?:under|over|below|above)\s*\d{1,3}\s*(?:lbs?|pounds?|kgs?)"
    r"[^.]{0,20}?(?:\$\s*\d[\d,]*|\d[\d,]*\s*USD)"
    r"[^.]{0,60}?(?:under|over|below|above)\s*\d{1,3}\s*(?:lbs?|pounds?|kgs?)"
    r"[^.]{0,20}?(?:\$\s*\d[\d,]*|\d[\d,]*\s*USD)",
    re.IGNORECASE)

#: Wording that makes a rung an ADDITION to its sibling rather than a
#: replacement for it. A ladder that mixes the two has no single role, and
#: Hyatt Place Airport is the case: "7-30 nights + additional cleaning fee :
#: $200 / STAY" is either the long-stay price or a separate charge, and the
#: page does not say which.
_BAND_ADDITIVE_RE = re.compile(
    r"\badditional\b|\bin\s+addition\b|\bplus\s+a\b|\bon\s+top\s+of\b"
    r"|\bas\s+well\s+as\b", re.IGNORECASE)

#: What a surface says about getting the money back, quoted rather than parsed.
_REFUNDABILITY_PHRASE_RE = re.compile(
    r"\bnon[-\s]?refundable(?:\s+fee)?|\brefundable(?:\s+fee|\s+deposit)?",
    re.IGNORECASE)

#: How far apart an amount and the range it prices may stand. Wide enough for
#: "50 USD nonrefundable fee, per pet, for stays 1 to 6 nights", where the
#: qualifiers between the price and its band are the reason the gap is large.
_BAND_PAIR_CHARS = 48

#: What separates one rung from the next. A price and the band it prices are
#: written together; a comma, a semicolon or a full stop between them means the
#: price belongs to the OTHER rung. Without this, "$50/stay for 1 night,
#: $75/stay for 2-4 nights" reads the second price onto the first band -- the
#: following amount is two characters away and the owning one is ten.
_BAND_SEPARATOR_RE = re.compile(r"[,;.]|\bor\b|\band\b", re.IGNORECASE)


class StayBand(NamedTuple):
    """One rung of a stay-length ladder, exactly as the source states it."""

    amount_minor: int
    currency: str
    min_nights: int
    max_nights: Optional[int]
    basis: str
    basis_stated: bool
    scope: str
    quote: str


class BandReading(NamedTuple):
    """What the surface's ladder is, and every reason it may not be published."""

    bands: Tuple[StayBand, ...]
    problems: Tuple[str, ...]

    @property
    def usable(self) -> bool:
        return bool(self.bands) and not self.problems


def _band_number(raw: str) -> Optional[int]:
    raw = (raw or "").strip().lower()
    if raw.isdigit():
        return int(raw)
    return _BAND_WORD_NUMBERS.get(raw)


def _stay_ranges(text: str) -> List[Tuple[int, Optional[int], int, int, bool]]:
    """(min, max, start, end, unit_stated) for every night range in the text."""
    found = []
    for match in _STAY_RANGE_RE.finditer(text):
        group = match.groupdict()
        low = high = None
        unit_stated = True
        if group.get("first_hi"):
            low, high = 1, _band_number(group["first_hi"])
        elif group.get("upto_hi"):
            low, high = 1, _band_number(group["upto_hi"])
        elif group.get("over_lo"):
            # "over 7 nights" starts at 8. The source has said nothing about
            # night 7, which the contiguity check below is what catches.
            value = _band_number(group["over_lo"])
            low, high = (value + 1 if value is not None else None), None
        elif group.get("ormore_lo"):
            low, high = _band_number(group["ormore_lo"]), None
        elif group.get("closed_lo"):
            low, high = (_band_number(group["closed_lo"]),
                         _band_number(group["closed_hi"]))
        elif group.get("plus_lo"):
            low, high = _band_number(group["plus_lo"]), None
            unit_stated = bool(group.get("plus_unit"))
        elif group.get("single_n"):
            value = _band_number(group["single_n"])
            low, high = value, value
        if low is None:
            continue
        # A source may write "0-5 nights"; night zero is not a stay. The
        # boundary is normalised for arithmetic and the OVERLAP check still
        # sees what the source actually said.
        low = max(low, 1)
        found.append((low, high, match.start(), match.end(), unit_stated))
    return found


def _band_amounts(text: str) -> List[Tuple[int, int, int]]:
    """(amount_minor, start, end) for every amount in the text."""
    out = []
    for match in _BAND_AMOUNT_RE.finditer(text):
        raw = match.group("dollars") or match.group("usd")
        if raw:
            out.append((_amount_minor(raw), match.start(), match.end()))
    return out


def _band_qualifier(text: str, left: int, right: int, pattern) -> str:
    """The first qualifier stated between an amount and its own range."""
    window = text[max(0, left - 12):right + 12]
    match = pattern.search(window)
    if not match:
        return ""
    return match.group(0)


def parse_stay_bands(text: str) -> BandReading:
    """Read a stay-length ladder, and every reason it may not be published.

    Deliberately conservative. A ladder is published only when the source
    determines it completely: contiguous ranges, one role, one basis story, no
    unexplained money, and no condition schema 1.2 cannot express. Anything
    else comes back with problems, and the caller withholds exactly as before.
    """
    text = text or ""
    problems: List[str] = []
    ranges = _stay_ranges(text)
    amounts = _band_amounts(text)
    if len(ranges) < 2:
        return BandReading((), ("FEWER_THAN_TWO_BANDS",))

    # Pair each range with the amount that prices it. Done as one assignment
    # rather than range by range: a greedy nearest-first walk gives the second
    # rung's price to the first rung wherever the ladder is written
    # "$50/stay for 1 night, $75/stay for 2-4 nights", and then the last rung
    # has nothing left and a readable ladder reports itself unreadable.
    #
    # So every feasible pairing is scored and the best COMPLETE assignment
    # wins: most rungs priced first, then fewest clause boundaries crossed,
    # then shortest total distance.
    if len(ranges) > 6 or len(amounts) > 12:
        return BandReading((), ("TOO_MANY_CANDIDATES_TO_PAIR",))

    feasible: List[List[Tuple[Tuple[int, int], int]]] = []
    for low, high, r_start, r_end, unit_stated in ranges:
        options: List[Tuple[Tuple[int, int], int]] = []
        for index, (value, a_start, a_end) in enumerate(amounts):
            if a_end <= r_start:
                gap, between = r_start - a_end, text[a_end:r_start]
            elif a_start >= r_end:
                gap, between = a_start - r_end, text[r_end:a_start]
            else:
                continue
            if gap > _BAND_PAIR_CHARS:
                continue
            # An amount or a range standing in between belongs to another
            # rung, and reaching across it would price this band with a
            # neighbour's money.
            if _BAND_AMOUNT_RE.search(between) or _STAY_RANGE_RE.search(between):
                continue
            crossings = 1 if _BAND_SEPARATOR_RE.search(between) else 0
            options.append(((crossings, gap), index))
        options.sort()
        feasible.append(options)

    best_assignment: Optional[Tuple[Tuple[int, int, int], List[int]]] = None

    def _assign(position: int, taken: set, chosen: List[int],
                crossings: int, distance: int) -> None:
        nonlocal best_assignment
        if position == len(feasible):
            priced = sum(1 for index in chosen if index >= 0)
            score = (-priced, crossings, distance)
            if best_assignment is None or score < best_assignment[0]:
                best_assignment = (score, list(chosen))
            return
        for (cross, gap), index in feasible[position]:
            if index in taken:
                continue
            taken.add(index)
            chosen.append(index)
            _assign(position + 1, taken, chosen, crossings + cross,
                    distance + gap)
            chosen.pop()
            taken.discard(index)
        # This rung may also go unpriced, which is itself a finding.
        chosen.append(-1)
        _assign(position + 1, taken, chosen, crossings, distance)
        chosen.pop()

    _assign(0, set(), [], 0, 0)
    assignment = best_assignment[1] if best_assignment else []

    used: set = set()
    paired: List[Tuple[Tuple, Tuple]] = []
    for position, index in enumerate(assignment):
        if index < 0:
            problems.append("BAND_WITHOUT_A_PRICE")
            continue
        used.add(index)
        paired.append((ranges[position], amounts[index]))

    if len(paired) < 2:
        return BandReading((), tuple(problems or ("FEWER_THAN_TWO_BANDS",)))

    priced = {value for _, (value, _, _) in paired}
    for index, (value, _, _) in enumerate(amounts):
        if index not in used and value not in priced:
            # Money the ladder does not explain. Hilton restates its first
            # rung as a headline ("Deposit Yes. $75.00 Non-refundable Fee")
            # and that is the same money; a THIRD number is a component this
            # structure is not carrying.
            problems.append("UNEXPLAINED_AMOUNT")
            break

    bands: List[StayBand] = []
    bases = set()
    for (low, high, r_start, r_end, unit_stated), (value, a_start, a_end) in paired:
        basis_word = _band_qualifier(text, a_start, a_end, _BAND_BASIS_RE)
        basis = ""
        if basis_word:
            word = re.sub(r"[^a-z]", "", basis_word.lower())
            for key, mapped in (("stay", enums.BASIS_PER_STAY),
                                ("night", enums.BASIS_PER_NIGHT),
                                ("nightly", enums.BASIS_PER_NIGHT),
                                ("day", enums.BASIS_PER_DAY),
                                ("daily", enums.BASIS_PER_DAY)):
                if key in word:
                    basis = mapped
                    break
        scope_word = _band_qualifier(text, a_start, a_end, _BAND_SCOPE_RE)
        scope = ""
        if scope_word:
            lowered = scope_word.lower()
            scope = (enums.SCOPE_PER_ROOM if "room" in lowered or "unit" in lowered
                     else enums.SCOPE_PER_PET)
        if basis:
            bases.add(basis)
        left, right = min(a_start, r_start), max(a_end, r_end)
        bands.append(StayBand(
            amount_minor=value, currency="USD", min_nights=low,
            max_nights=high, basis=basis, basis_stated=bool(basis),
            scope=scope, quote=text[left:right]))

    bands.sort(key=lambda band: (band.min_nights,
                                 band.max_nights or 10 ** 6))
    for first, second in zip(bands, bands[1:]):
        if first.max_nights is None:
            problems.append("OVERLAPPING_BANDS")
        elif second.min_nights <= first.max_nights:
            # "0-5 nights $75 5+ $150" prices night five twice, and choosing
            # a winner would quote a price the hotel did not.
            problems.append("OVERLAPPING_BANDS")
        elif second.min_nights > first.max_nights + 1:
            # "1 to 6 nights ... over 7 nights" says nothing about night 7.
            problems.append("GAP_BETWEEN_BANDS")
    if bands[0].min_nights != 1:
        problems.append("LADDER_DOES_NOT_START_AT_ONE")
    if len({band.amount_minor for band in bands}) < 2:
        problems.append("BANDS_STATE_ONE_PRICE")
    if len(bases) > 1:
        problems.append("CONTRADICTORY_BASIS")
    if not any(unit for *_, unit in ranges):
        problems.append("NO_BAND_STATES_ITS_UNIT")

    if _BAND_CEILING_RE.search(text):
        problems.append("CEILING_NOT_PRICE")
    if _BAND_TAX_RE.search(text):
        problems.append("TAX_QUALIFIER_NOT_REPRESENTABLE")
    if _BAND_UNSUPPORTED_BASIS_RE.search(text):
        problems.append("UNSUPPORTED_BASIS")
    if _BAND_ROOM_TYPE_RE.search(text):
        problems.append("ROOM_TYPE_CONDITION")
    if _BAND_SPECIES_PRICED_RE.search(text):
        problems.append("SPECIES_CONDITIONED_PRICE")
    if _BAND_WEIGHT_PRICED_RE.search(text):
        problems.append("WEIGHT_CONDITIONED_PRICE")
    for band in bands:
        if _BAND_ADDITIVE_RE.search(band.quote):
            problems.append("AMBIGUOUS_ROLE")
            break
    return BandReading(tuple(bands), tuple(sorted(set(problems))))


def tiers_from_bands(bands: Sequence[StayBand]) -> List[Dict]:
    """Schema-1.2 ``fee_tiers`` for a ladder, in the shape the corpus uses.

    ``role`` is REPLACEMENT_PRICE and is asserted rather than defaulted: every
    band here states the whole price for a stay of that length, which is what
    the caller has already checked by refusing any ladder whose rungs read as
    additions. ``basis`` is absent unless the source stated it, and
    ``basis_stated`` says which of the two happened -- the same pair of facts
    Cleveland's founder adjudications recorded by hand.
    """
    tiers = []
    for band in bands:
        tier: Dict = {"amount_cents": band.amount_minor,
                      "currency": band.currency,
                      "role": enums.ROLE_REPLACEMENT_PRICE,
                      "condition_type": enums.CONDITION_STAY_LENGTH_RANGE,
                      "boundary_unit": enums.BOUNDARY_NIGHTS,
                      "condition_min": band.min_nights,
                      "basis_stated": band.basis_stated}
        if band.max_nights is not None:
            tier["condition_max"] = band.max_nights
        if band.basis:
            tier["basis"] = band.basis
        if band.scope:
            tier["scope"] = band.scope
        tiers.append(tier)
    return tiers


#: An ordinal rung: "1 pet $15 per night, 2 pets $25 per night", or the same
#: ladder written "First pet $20, second pet $10".
_PET_RUNG_RE = re.compile(
    r"(?:(?P<count>\d{1,2})\s*(?:pets?|dogs?|cats?)"
    r"|(?P<word>first|second|third|fourth)\s+(?:pet|dog|cat))"
    r"[^.$\d]{0,20}?"
    r"(?:\$\s*(?P<dollars>\d[\d,]*(?:\.\d{2})?)"
    r"|(?P<usd>\d[\d,]*(?:\.\d{2})?)\s*USD\b)",
    re.IGNORECASE)

_PET_RUNG_WORDS = {"first": 1, "second": 2, "third": 3, "fourth": 4}

#: "each additional pet" names no ordinal. It could be the second animal or
#: the fifth, and a schedule that guesses would price a rung the source never
#: stated. Detected so the ladder is refused rather than invented.
_PET_RUNG_OPEN_ENDED_RE = re.compile(
    r"\beach\s+additional\s+(?:pet|dog|cat)|\bevery\s+(?:other|additional)\s+"
    r"(?:pet|dog|cat)", re.IGNORECASE)


class PetSchedule(NamedTuple):
    entries: Tuple[Dict, ...]
    problems: Tuple[str, ...]

    @property
    def usable(self) -> bool:
        return bool(self.entries) and not self.problems


def parse_pet_schedule(text: str) -> PetSchedule:
    """Read a price stated per ANIMAL rather than per stay length.

    ``additive`` is mandatory in the schema and is never inferred here: a rung
    is additive only where the source says the charge is on top of the one
    below it. Where the wording leaves that open the schedule is refused --
    "$15 for the second pet" charged additively or not is a different bill.
    """
    text = text or ""
    problems: List[str] = []
    rungs: Dict[int, Dict] = {}
    for match in _PET_RUNG_RE.finditer(text):
        group = match.groupdict()
        ordinal = (int(group["count"]) if group.get("count")
                   else _PET_RUNG_WORDS.get((group.get("word") or "").lower()))
        if not ordinal:
            continue
        raw = group.get("dollars") or group.get("usd")
        if not raw:
            continue
        span = text[max(0, match.start() - 12):match.end() + 16]
        basis = ""
        basis_word = _BAND_BASIS_RE.search(span)
        if basis_word:
            word = re.sub(r"[^a-z]", "", basis_word.group(0).lower())
            for key, mapped in (("stay", enums.BASIS_PER_STAY),
                                ("nightly", enums.BASIS_PER_NIGHT),
                                ("night", enums.BASIS_PER_NIGHT),
                                ("daily", enums.BASIS_PER_DAY),
                                ("day", enums.BASIS_PER_DAY)):
                if key in word:
                    basis = mapped
                    break
        entry: Dict = {"pet_ordinal": ordinal,
                       "amount_cents": _amount_minor(raw),
                       "currency": "USD",
                       # The ladders this reads state a rung's OWN price --
                       # "2 pets $25" is the bill for two animals, not $25 on
                       # top of the first. Additive rungs are named as such by
                       # wording this parser refuses outright.
                       "additive": False}
        if basis:
            entry["basis"] = basis
        scope_word = _BAND_SCOPE_RE.search(span)
        if scope_word:
            lowered = scope_word.group(0).lower()
            entry["scope"] = (enums.SCOPE_PER_ROOM
                              if "room" in lowered or "unit" in lowered
                              else enums.SCOPE_PER_PET)
        if ordinal in rungs and rungs[ordinal] != entry:
            problems.append("CONTRADICTORY_RUNG")
        rungs[ordinal] = entry
    if _PET_RUNG_OPEN_ENDED_RE.search(text):
        problems.append("OPEN_ENDED_RUNG")
    if len(rungs) < 2:
        return PetSchedule((), tuple(problems or ("FEWER_THAN_TWO_RUNGS",)))
    ordinals = sorted(rungs)
    if ordinals != list(range(1, len(ordinals) + 1)):
        problems.append("RUNGS_ARE_NOT_CONSECUTIVE_FROM_ONE")
    if len({entry["amount_cents"] for entry in rungs.values()}) < 2:
        problems.append("RUNGS_STATE_ONE_PRICE")
    if _BAND_CEILING_RE.search(text):
        problems.append("CEILING_NOT_PRICE")
    if _BAND_ROOM_TYPE_RE.search(text):
        problems.append("ROOM_TYPE_CONDITION")
    if _BAND_WEIGHT_PRICED_RE.search(text):
        problems.append("WEIGHT_CONDITIONED_PRICE")
    entries = tuple(rungs[ordinal] for ordinal in ordinals)
    return PetSchedule(entries, tuple(sorted(set(problems))))


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

    if cleaning and _cleaning_is_inside_a_band(reading, cleaning[0]):
        # The cleaning wording sits INSIDE a banded pet price, so the surface
        # has not separated the two charges. Hyatt Place Airport prints
        # "1-6 nights : $100 / STAY 7-30 nights + additional cleaning fee :
        # $200 / STAY": whether $200 is a cleaning fee, or the long-stay pet
        # price WITH cleaning in it, is exactly what the page does not say.
        # The pet fee is already withheld here as a band the schema cannot
        # hold; republishing one of its own numbers under another name would
        # state as a separate charge the thing that was withheld as
        # unrepresentable.
        # Found by PTF-LABEL-VALUE-POLICY-READER-HARDENING-033.
        withheld["cleaning_fee"] = enums.SOURCE_AMBIGUOUS
    elif cleaning and cleaning[0].basis in enums.NIGHTLY_BASES:
        # A RECURRING cleaning charge, and ``cleaning_fee`` is one bare integer
        # with nowhere to put "per day". One Marriott property states "a Daily
        # cleaning fee of $5/ day in addition to the one time non-refundable
        # pet fee": published as "$5.00" -- which is what the display
        # projection renders, having no basis to show -- a seven-night stay is
        # understated by thirty dollars.
        #
        # The amount is not dropped: it is withheld with a reason, so a
        # reviewer sees a charge the vocabulary cannot carry rather than a
        # cheaper one than the hotel charges. Added by work order 035.
        withheld["cleaning_fee"] = enums.SCHEMA_CANNOT_REPRESENT
        flags.append({
            "code": "FLAG_RECURRING_CLEANING_CHARGE",
            "detail": ("the surface states a recurring cleaning charge (%r) "
                       "and the published vocabulary holds one amount and no "
                       "basis for it" % cleaning[0].quote)})
    elif cleaning:
        extraction["cleaning_fee"] = cleaning[0].amount_minor
        cite(cleaning[0].quote, ["cleaning_fee"])

    # --- the structured price, where the source fully determines it -------- #
    #
    # Work order 034, reader-to-tiers. Everything below this block withholds
    # a price the single ``pet_fee`` field cannot hold. Schema 1.2 has held
    # ``fee_tiers`` and ``fee_pet_schedule`` since the policy migration, and
    # this reader never built either -- so twenty-nine rows in one market
    # carried SCHEMA_CANNOT_REPRESENT for a shape the schema was already
    # carrying by hand from a founder adjudication.
    #
    # It runs FIRST because it is the more specific answer. A ladder that reads
    # completely is a fact; the branches below are what to do when it does not.
    structured = False
    bands = parse_stay_bands(reading.block_text)
    schedule = parse_pet_schedule(reading.block_text)
    band_amounts = {band.amount_minor for band in bands.bands}

    # A charge the ladder does not explain is a second component, and the
    # ladder is not the whole price. A deposit or a cleaning fee whose amount
    # IS one of the rungs is worse than unexplained -- it is the same money
    # counted twice -- so either way the structure is refused.
    collides = [c for c in reading.charges
                if (c.kind == "deposit" or c.cleaning_labelled)
                and c.amount_minor in band_amounts]

    if bands.usable and schedule.entries:
        # Two ladders at once: a price by stay length AND a price by animal.
        # 1.2 can express either, and nothing says how they combine.
        flags.append({"code": "FLAG_TIERED_FEE",
                      "detail": "the surface prices by stay length and by pet "
                                "count at once, and the two ladders are not "
                                "reconciled by the source"})
    elif bands.usable and not collides:
        extraction["fee_tiers"] = tiers_from_bands(bands.bands)
        for band in bands.bands:
            cite(band.quote, ["fee_tiers"])
        # A tier has no refundability field. Where the surface states one --
        # Hilton heads every ladder "Deposit Yes. $75.00 Non-refundable Fee" --
        # the words are cited against the structure rather than dropped, so a
        # reviewer sees the term the vocabulary could not carry.
        refundability = _REFUNDABILITY_PHRASE_RE.search(reading.block_text)
        if refundability:
            cite(refundability.group(0), ["fee_tiers"])
            non_inferences.append(
                "fee_tiers[].refundable: the schema's tier carries no "
                "refundability field; the surface's own words (%r) are cited "
                "against the structure and nothing is inferred from them"
                % refundability.group(0))
        structured = True
        flags.append({
            "code": "FLAG_STRUCTURED_TIERS",
            "detail": "the price is stated as %d bands by stay length and is "
                      "carried in fee_tiers" % len(bands.bands)})
    elif schedule.usable and not collides:
        extraction["fee_pet_schedule"] = {"entries": [dict(entry)
                                                      for entry in schedule.entries]}
        cite(reading.block_text[:240], ["fee_pet_schedule"])
        structured = True
        flags.append({
            "code": "FLAG_STRUCTURED_PET_SCHEDULE",
            "detail": "the price is stated per animal and is carried in "
                      "fee_pet_schedule (%d rungs)" % len(schedule.entries)})

    if structured:
        # ONE authoritative price. A simple ``pet_fee`` beside a ladder is two
        # answers to the same question, and the renderer would have to choose.
        pool = []
        non_inferences.append(
            "pet_fee: the surface prices this pet by %s; the whole ladder is "
            "carried in %s and no single amount is asserted"
            % ("stay length" if "fee_tiers" in extraction else "pet count",
               "fee_tiers" if "fee_tiers" in extraction else "fee_pet_schedule"))
        if not any(band.basis_stated for band in bands.bands) \
                and "fee_tiers" in extraction:
            non_inferences.append(
                "fee_tiers[].basis: this surface states amounts and stay "
                "lengths and never says whether a rung is charged per night "
                "or per stay; basis_stated records that it did not")
    else:
        why = tuple(bands.problems) if bands.bands else tuple(schedule.problems)
        if why and (bands.bands or schedule.entries):
            # The surface DID state a ladder and it cannot be given to the
            # schema safely. Recorded as SCHEMA_CANNOT_REPRESENT here rather
            # than left to fall through to "the page said nothing": a block
            # priced "$75 weekly for 1-4 nights" names a recurrence FEE_BASES
            # has no member for, and reporting that as silence would tell a
            # reviewer to go looking for a fee that is printed on the page.
            withheld["pet_fee"] = enums.SCHEMA_CANNOT_REPRESENT
            withheld["fee_basis"] = enums.SCHEMA_CANNOT_REPRESENT
            flags.append({
                "code": "FLAG_TIER_STRUCTURE_REFUSED",
                "detail": "the surface prices this pet in bands the schema "
                          "cannot be given safely (%s); no structure is "
                          "emitted and no single amount is asserted"
                          % ", ".join(why)})

    # A component the surface states and no charge carries is withheld through
    # the same machinery, for the same reason: the vocabulary holds ONE amount
    # and one basis, and the surface described more than one thing. Added by
    # PTF-GENERIC-READER-BANDED-FEE-AND-HILTON-CONTAINER-HARDENING-024,
    # generalising what 021 proved for Marriott. The components are NOT summed:
    # a deposit, a nightly charge and a per-stay fee are three different things.
    #
    # Runs AFTER the tier check so the more specific reason wins where both
    # apply. A banded fee usually leaves an amount unexplained too, and
    # reporting it as "components that cannot be carried together" would bury
    # the fact that the surface prices the same pet by stay length -- which is
    # what a reviewer needs to see, and what FLAG_TIERED_FEE says.
    if (pool and not structured and reading.unrepresented
            and not _fee_is_tiered(reading.block_text)):
        withheld["pet_fee"] = enums.SCHEMA_CANNOT_REPRESENT
        withheld["fee_basis"] = enums.SCHEMA_CANNOT_REPRESENT
        flags.append({
            "code": "FLAG_MULTI_POLICY_BLOCKS",
            "detail": ("the surface states charge components this vocabulary "
                       "cannot carry together (%s); no single pet_fee is "
                       "asserted"
                       % "; ".join(sorted(u["quote"]
                                          for u in reading.unrepresented)))})
        pool = []

    if (len(pool) == 1 and not structured
            and _fee_is_conditional(reading.block_text, pool[0])):
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
    if pool and not structured and _fee_is_tiered(reading.block_text):
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
    elif reading.pets_allowed and not structured:
        # A reason already recorded is more specific than silence. The
        # conditional-fee branch above empties the pool deliberately, and its
        # SCHEMA_CANNOT_REPRESENT must not be overwritten by "the page said
        # nothing" -- the page said something the schema cannot hold.
        #
        # A STRUCTURED price is the same argument one step further: a ladder in
        # ``fee_tiers`` is the surface's price, and reporting pet_fee as
        # SOURCE_SILENT beside it would tell a reviewer the page named no fee
        # while the row carries three of them. Added by
        # Found by work order 034, reader-to-tiers.
        recurring_unread = any(
            item.get("kind") == "recurring_charge_not_represented"
            for item in (reading.unrepresented or ()))
        if recurring_unread:
            # The surface named a recurring charge and no charge pattern could
            # read it -- "$20 daily pet fee applies, up to a maximum of $100
            # per stay" states a price this reader cannot carry, and calling
            # that SILENCE tells a reviewer the page named no fee while it
            # names one in the same sentence as the ceiling. Added by work
            # order 035, alongside the repair that made this detectable at all.
            withheld.setdefault("pet_fee", enums.SCHEMA_CANNOT_REPRESENT)
            flags.append({
                "code": "FLAG_RECURRING_CHARGE_NOT_READ",
                "detail": ("the surface states a recurring pet charge that no "
                           "charge pattern could read; no amount is asserted "
                           "and the silence is not claimed")})
        else:
            withheld.setdefault("pet_fee", enums.SOURCE_SILENT)

    for excluded_amount in reading.excluded_amounts:
        non_inferences.append(
            "pet_deposit: the surface states $%.2f for a purpose it does not "
            "name as a pet's (%r); it is not recorded as a pet charge and is "
            "reported here rather than dropped"
            % (excluded_amount["amount_minor"] / 100.0,
               collapse(excluded_amount["quote"])[:120]))

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
    elif not reading.species_exclusive and not reading.cats_refused_quote:
        # ``species_allowed`` is a list of species the surface AFFIRMED, and
        # every consumer reads it that way: a species absent from it renders as
        # "Not stated" and resolves to no state at all, while a prohibition is
        # carried separately by ``cats_allowed`` and by the 1.2 species map.
        #
        # Saying so out loud anyway. "All dogs are welcome" names one animal
        # and is silent about the rest, and the distance between "silent" and
        # "refused" is the whole of the founder rule that SOURCE SILENCE IS
        # ABSENCE. A reader that leaves it implicit is one careless consumer
        # away from publishing a cat prohibition nobody wrote.
        non_inferences.append(
            "species: this surface names a species it accepts and does not "
            "say the others are refused; species_allowed lists affirmations "
            "only, and an unnamed species stays unknown rather than prohibited")

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
