"""The reader's PROTECTIONS, pinned by value rather than by file.

Several work orders froze ``policy_reading.py`` whole as a cheap way of saying
"the reader's safeguards did not move". That reading held while nothing in the
file was meant to change.

PTF-GENERIC-READER-BEST-WESTERN-HARDENING-029 was commissioned to change it:
two Best Western surfaces state a count, a weight and a daily rate and the
reader represented none of them. A whole-file freeze cannot tell a repair from
a regression, so it would have to be either deleted or defeated.

It is narrowed instead. What those freezes were actually protecting -- the
withholding rules, the room-rate guard, the non-pet purpose rule, and the
published basis vocabulary -- is pinned here by value and by behaviour. That is
more precise than the file check for the safeguards and strictly less coverage
for the rest of the file, which is said plainly rather than glossed: a pattern
added to the count or weight lists no longer trips these freezes.
"""

import hashlib
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.brightdata import policy_reading as PR
from scripts.pettripfinder.contracts import enums

#: sha256 of the patterns the safeguards are made of.
TIERED_FEE_SHA = "f86f8190be00e97e7eabefd616e2487d"
RATE_MARKER_SHA = "13567602e891334286e1c64938404a5f"

#: The non-pet purposes, pinned as MEMBERSHIP rather than as a hash of the
#: whole pattern. A hash says "this guard is exactly what it was", which reads
#: a STRENGTHENING as a breach: 033 added parking, smoking, resort fees and
#: valet to it, having found the reader publishing a resort fee and a smoking
#: fee as the pet fee. What the freeze is for is that nothing is ever taken
#: OUT, so that is what it now checks -- every frozen alternative must still
#: be there, and each still refuses in behaviour below.
FROZEN_NON_PET_PURPOSES = (
    r"\bincidental(?:s)?\b", r"\bfor\s+all\s+guests\b",
    r"\ball\s+guests\b", r"\bsecurity\s+deposit\b",
    r"\bdamage\s+deposit\b",
)


#: What 033 added, pinned the same way so a later work order cannot quietly
#: drop it either.
NON_PET_PURPOSES_ADDED_BY_033 = (
    r"\bparking\b", r"\bsmoking\b", r"\bresort\s+fee\b", r"\bvalet\b",
)


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]


def assert_reader_protections_unchanged():
    """Every rule that exists to stop the reader saying too much."""
    # The published basis vocabulary, and per_day still distinct from per_night.
    assert PR._BASIS_BY_WORD == {
        "stay": enums.BASIS_PER_STAY, "night": enums.BASIS_PER_NIGHT,
        "nightly": enums.BASIS_PER_NIGHT, "day": enums.BASIS_PER_DAY,
        "daily": enums.BASIS_PER_DAY}
    assert enums.BASIS_PER_DAY != enums.BASIS_PER_NIGHT

    # The guards, by pattern.
    assert _sha(PR._TIERED_FEE_RE.pattern) == TIERED_FEE_SHA
    assert _sha(PR._RATE_MARKER_RE.pattern) == RATE_MARKER_SHA
    for alternative in FROZEN_NON_PET_PURPOSES + NON_PET_PURPOSES_ADDED_BY_033:
        assert alternative in PR._NON_PET_PURPOSE_RE.pattern, alternative
    assert PR._PET_CONTEXT_CHARS == 70
    assert PR._PURPOSE_QUALIFIER_CHARS == 16

    # And by behaviour, which is what actually matters.
    tiered = PR.to_extraction(
        PR.parse("Pets welcome. $75 for the first night, $25 per night "
                 "thereafter."), location="freeze")
    assert "pet_fee" not in tiered.extraction
    assert "pet_fee" in tiered.withheld

    banded = PR.to_extraction(
        PR.parse("Pets welcome. Pet fee: $50 (1-4 nights), $100 (5+ nights)."),
        location="freeze")
    assert "pet_fee" not in banded.extraction

    multi = PR.to_extraction(
        PR.parse("Pets welcome. A $125 non-refundable pet deposit and a $20 "
                 "daily pet fee apply."), location="freeze")
    assert "pet_fee" not in multi.extraction

    for block in ("1 King Bed 4 Guests No Pets Allowed "
                  "Discounted rate: $160 USD /night",
                  "No Pets Allowed Member Rate 160.00 per night",
                  "No Pets Allowed Strikethrough Rate: $172 "
                  "Discounted rate: $160 /night"):
        room_rate = PR.to_extraction(PR.parse(block), location="freeze")
        assert "pet_fee" not in room_rate.extraction, block

    amenity = PR.to_extraction(PR.parse("Pet Friendly"), location="freeze")
    assert amenity.extraction.get("pets_allowed") is None

    service = PR.to_extraction(PR.parse("Service Animals are Welcome"),
                               location="freeze")
    assert "pets_allowed" not in service.extraction

    # A charge every guest pays is not the price of bringing an animal, however
    # near the word "pet" it is printed. Added by 033, which found the reader
    # publishing the first two of these as ``pet_fee``.
    for block in ("Pets welcome. Resort fee : $29 per night.",
                  "Pets welcome. Smoking fee : $250 per stay.",
                  "Pets allowed. Self-parking $35 per night.",
                  "Pets allowed. Valet parking : $45 per night."):
        other = PR.to_extraction(PR.parse(block), location="freeze")
        assert "pet_fee" not in other.extraction, block
