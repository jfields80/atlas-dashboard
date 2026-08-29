"""How a page is UNDERSTOOD. Nothing here knows how it was fetched.

A reader is two things: which policy container to look for, and how to read the
words in it. Both are provider-independent by construction -- the Choice reader
below serves the Web Unlocker today and will serve anything that returns that
page tomorrow, because it takes text, not a session.

WHY THE LOCATOR HINT IS A HINT
------------------------------
``locator_brand`` names a brand's own container in
``policy_surface.BRAND_LOCATORS``. It does NOT mean "use this and stop". The
Hilton lesson is enforced one layer down: a brand container competes with the
generic walk on policy features and the richest bounded block wins. A brand
selector that matched a two-word label once dropped Hilton's recall from 56% to
33% by pre-empting the walk it should have been competing with.

So a reader that names a container is expressing a preference the evidence has
to justify, not issuing an instruction.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.brightdata import policy_reading as PR  # noqa: E402
from scripts.pettripfinder.brightdata import policy_surface as PS  # noqa: E402


@dataclass(frozen=True)
class Reader:
    """One way of understanding a policy page.

    ``locator_brand`` is the key into ``policy_surface.BRAND_LOCATORS``, or ""
    for readers that rely on the generic walk alone. ``parse`` and
    ``to_extraction`` are the pure functions the pilots measured; every reader
    currently shares them, which is the point -- one reader covering six brands
    is the finding, and per-brand parsing is what has to earn its place.
    """

    reader_id: str
    locator_brand: str
    description: str
    parse: Callable = PR.parse
    to_extraction: Callable = PR.to_extraction

    def to_dict(self) -> Dict:
        return {"reader_id": self.reader_id,
                "locator_brand": self.locator_brand,
                "description": self.description}


#: Every reader the router can select. Adding one is a row here plus, where it
#: needs its own container, a row in ``policy_surface.BRAND_LOCATORS``.
READERS: Dict[str, Reader] = {
    "generic": Reader(
        reader_id="generic", locator_brand="",
        description="the bounded signal-phrase walk that carried five of six "
                    "brands in pilot-002"),
    "marriott": Reader(
        reader_id="marriott", locator_brand="MARRIOTT",
        description="structural heading-parent locator; 100% precision and "
                    "recall across three pilots"),
    "hilton_competing": Reader(
        reader_id="hilton_competing", locator_brand="HILTON",
        description="brand container COMPETING with the generic walk; the "
                    "generic walk usually wins and must be allowed to"),
    "wyndham": Reader(
        reader_id="wyndham", locator_brand="WYNDHAM",
        description="div.policy-items.pet-policy, read via textContent because "
                    "the page never paints it"),
    "choice_static": Reader(
        reader_id="choice_static", locator_brand="CHOICE",
        description="bounded walk over static HTML, for pages fetched without "
                    "a browser"),
    "ihg": Reader(
        reader_id="ihg", locator_brand="IHG",
        description="generic walk over the FAQ accordion; recall is the known "
                    "gap at 62%"),
}

DEFAULT_READER = "generic"


class ReaderError(KeyError):
    """No such reader."""


def get(reader_id: str) -> Reader:
    try:
        return READERS[reader_id or DEFAULT_READER]
    except KeyError:
        raise ReaderError(
            "unknown reader %r; known readers are %s. A reader is a row in "
            "READERS, not a string a route may invent."
            % (reader_id, sorted(READERS)))


def locator_brand_for(reader_id: str) -> str:
    """The brand key a reader prefers, or "" for the generic walk."""
    return get(reader_id).locator_brand


def brand_locator_exists(reader_id: str) -> bool:
    """Whether the reader's preferred container is actually registered.

    A reader may name a brand that has no container yet; that is not an error,
    it just means the generic walk does the work. Reported rather than assumed.
    """
    brand = locator_brand_for(reader_id)
    return bool(brand) and brand in PS.BRAND_LOCATORS


__all__ = ["Reader", "READERS", "DEFAULT_READER", "ReaderError", "get",
           "locator_brand_for", "brand_locator_exists"]
