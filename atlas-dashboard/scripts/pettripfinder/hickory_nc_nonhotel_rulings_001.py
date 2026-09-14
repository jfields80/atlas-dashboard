"""PTF-HICKORY-NC-PARALLEL-SOURCE-READY-001 -- the apartment / corporate-housing / rental filter, by name.

Every row here is a refusal DECISION with its reason, matched on the full
normalised name (``site_data.normalize_name``) of a census candidate. A name is
added only after the evidence for that row was read: the map tag, the tourism
organisation's own category, or the property's own site.

Nothing here fetches and nothing here admits.
"""
from __future__ import annotations

#: Rows whose LODGING category cannot be settled from the evidence. Held as
#: IDENTITY_REVIEW_REQUIRED (never admitted, never refused as non-hotel by guesswork).
LODGING_UNCONFIRMED = {
    "the lodge at rock barn":
        "lodging at Rock Barn Country Club & Spa (3791 Clubhouse Drive, Conover 28613), a membership club; the bureau "
        "lists it under Hotel / Bed and Breakfast, but the club's own lodging page (rockbarn.com/Amenities/Lodging) "
        "now answers 404 and its home page presents membership, so whether the lodge sells public nightly rooms "
        "under the lodging contract is unconfirmed",
    "henry river mill village":
        "a historic mill-village attraction and event venue (4255 Henry River Road, 28602) whose own home page "
        "offers 'overnight accommodations' and 'Book your stay' but lists no rooms, no lodging page and no front "
        "desk; whether its overnight inventory is a qualifying lodging establishment or a whole-house rental is "
        "unconfirmed",
}

NOT_LODGING_WHY = {
    "flying squirrel cottages":
        "the operator's own site (flyingsquirrelcottages.com) is a North Carolina cottage / cabin / house / villa "
        "rental portfolio across cities, lakes and mountains; a property-management vacation-rental company, not a "
        "lodging establishment; refused under the order's short-term-rental rule",
    "catholic conference center":
        "the centre's own site (catholicconference.org, 1551 Trinity Lane, Hickory) offers retreat, workshop and "
        "conference programmes for groups, with lodging rooms as part of a retreat booking and a retreat house "
        "rented to small groups; a religious retreat / conference facility, not a hotel selling public nightly "
        "rooms; refused",
    "rock barn country club and spa":
        "a membership country club and spa (the bureau files it under golf, wellness, wedding and shopping, never "
        "Hotel); its lodging is listed separately as The Lodge at Rock Barn; the club listing is not a lodging "
        "identity",
    "the townhomes at rock barn":
        "townhome units at a private country club, listed beside the club lodge at the same street; individually "
        "rented residential units, never a hotel identity; refused under the order's apartment / residential rule",
    "mimosa gardens":
        "an apartment community the map tags tourism=apartment; ordinary residential inventory, refused",
    "ardmore at aclove":
        "an apartment community the map tags tourism=apartment; ordinary residential inventory, refused",
}
