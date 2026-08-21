"""The locator surface, pinned by VALUE rather than by file.

Six work orders froze ``policy_surface.py`` and ``marriott_surface.py`` whole,
as a cheap way of saying "the policy LOCATOR did not move". That reading held
while nothing else lived in those files.

PTF-CODELESS-INDEPENDENT-IDENTITY-BINDING-027 repaired the code-less IDENTITY
binding, which lives in ``policy_surface.py`` beside the locator and has
nothing to do with it. A whole-file freeze cannot tell those two apart, so it
would have to be either deleted or defeated.

It is narrowed instead: everything the locator actually is -- its bounds, its
signal vocabulary, its feature set, its brand selectors and the three browser
scripts that do the walking -- is pinned here by value. That is strictly more
precise than the file check for the locator, and strictly less coverage for the
rest of those two files, which is stated plainly rather than glossed: an
unrelated edit to the identity gate no longer trips these freezes.
"""

import hashlib
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.brightdata import marriott_surface as MS
from scripts.pettripfinder.brightdata import policy_surface as PS

#: sha256 of the three scripts the locator injects into the page.
LOCATE_SCRIPT_SHA = ("157437c4c6376a888454a7e25da644e267c7ec916bf88e76d7937"
                     "1b9fc835c4e")
EXPAND_SCRIPT_SHA = ("a67806df217545195277b702277d78b8c987cbbd80fa434b7672e"
                     "2b0b0ba6360")
BRAND_READ_SCRIPT_SHA = ("9fa3f133fc9139d6749c148ddd0e313e31f83b84c0ed23294"
                         "752131a13d884dd")


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def assert_locator_surface_unchanged():
    """Everything the generic and brand locators are, unchanged."""
    assert (PS.MIN_BLOCK_CHARS, PS.MAX_BLOCK_CHARS, PS.MIN_POLICY_FEATURES,
            PS.MIN_PET_MENTIONS_SHORT, PS.MIN_PET_MENTIONS_LONG,
            PS.LONG_BLOCK_CHARS) == (16, 1500, 1, 1, 2, 300)
    assert len(PS.SIGNAL_PHRASES) == 31
    assert len(PS.POLICY_FEATURE_RES) == 10
    assert sorted(PS.BRAND_LOCATORS) == ["CHOICE", "HILTON", "WYNDHAM"]
    assert _sha(PS._LOCATE_SCRIPT) == LOCATE_SCRIPT_SHA
    assert _sha(PS._EXPAND_SCRIPT) == EXPAND_SCRIPT_SHA
    assert _sha(PS._BRAND_READ_SCRIPT) == BRAND_READ_SCRIPT_SHA
    assert [label for label, _ in MS.POLICY_LOCATORS] == [
        "pet_policy_heading_parent", "pet_policy_accordion_panel",
        "hotel_info_pet_icon_block", "any_pet_icon_block"]
