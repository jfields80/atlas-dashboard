"""``ptf-market-final-partition/1.1`` -- the disposition of every identity.

Cleveland's 1.0 is the strongest artifact in the repository and is adopted
almost unchanged: 188 identities, each present exactly once, twelve states each
with a written meaning, and 159 unresolved rows each carrying exactly one
blocker plus a next action and the pass that determined it.

1.1 adds two states -- ``OUT_OF_CURRENT_CATEGORY`` (already a real disposition
in the exclusion registry, and where Cleveland's two non-lodging routing
orphans belong) and ``AWAITING_IDENTITY_RESOLUTION`` (sized by Cincinnati's 33
unresolved plus 14 provisional identities) -- normalises the blocker
vocabulary, and requires ``determined_by`` and ``updated_at``.

Membership is tested, never subtracted
--------------------------------------
The manifest currently derives ``unresolved = confirmed - published - no_pets``.
That arithmetic is correct for every WRONG membership: swap a published
identity for one absent from the census and the total does not move. A pinned
count cannot catch wrong membership; only a set comparison can.

So ``reconcile`` compares sets and derives counts FROM the partition. There is
no code path here that infers a bucket by subtracting other buckets.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Sequence, Set, Tuple

from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts.identity_key import (
    IdentityKeyError, is_canonical_key, ptf_identity_key,
)
from scripts.pettripfinder.contracts.policy_schema import Issue

SCHEMA = enums.PARTITION_SCHEMA

#: The written meaning of every state. Kept in the contract rather than in a
#: market's document so four markets cannot drift into four definitions of
#: "awaiting policy artifact".
STATE_MEANINGS: Dict[str, str] = {
    enums.PUBLISHED_PET_FRIENDLY:
        "A pet policy passed the membrane and the publication guard on this "
        "property's own captured page, and the hotel has a public route.",
    enums.VERIFIED_NO_PETS:
        "A refusal was captured with a citable artifact and source hash; the "
        "property is excluded and generates no route.",
    enums.OUT_OF_CURRENT_CATEGORY:
        "A confirmed identity that is not lodging in our current category -- a "
        "restaurant, a bed-and-breakfast, a guesthouse. Not a refusal.",
    enums.AWAITING_OFFICIAL_URL:
        "No official URL has ever been found for this identity. The census "
        "confirms the property exists; nothing says where its page is.",
    enums.AWAITING_PROPERTY_LEVEL_URL:
        "Only a brand index, brand-locator or city-level URL is bound. Such a "
        "URL is property-specific for nobody and cannot back a policy fact.",
    enums.AWAITING_ROUTING_REVIEW:
        "A routing proposal exists whose destination cannot be confirmed "
        "first-party because the brand is bot-walled. It is HELD: neither "
        "accepted on a transcription's word nor discarded.",
    enums.AWAITING_ROUTING_REPLACEMENT:
        "The URL on record is provably not this property's page -- dead, a "
        "different business, or a brand surface that refused to serve it. "
        "Policy work cannot start until the route is replaced.",
    enums.AWAITING_POLICY_OBSERVATION:
        "The route is sound and the page served its content, but no pet policy "
        "has ever been observed on it. UNKNOWN, never a refusal.",
    enums.AWAITING_POLICY_ARTIFACT:
        "The policy WORDING is known but no artifact of the surface it was "
        "read from exists. A hash of a transcription binds the typing, not the "
        "page.",
    enums.AWAITING_ATTENDED_CAPTURE:
        "The policy exists on the property's own surface but behind a click, "
        "an accordion, a modal, or client-side rendering that a static fetch "
        "cannot reach. An attended browser is the lawful route, not a bypass.",
    enums.AWAITING_CONTRADICTION_RESOLUTION:
        "The evidence conflicts with itself or with another authority, and no "
        "side may be chosen silently.",
    enums.AWAITING_CENSUS_REVIEW:
        "The identity's presence or category in the census is itself in "
        "question.",
    enums.AWAITING_IDENTITY_RESOLUTION:
        "Identity is provisional or unresolved, so policy work cannot safely "
        "bind to this record.",
    enums.AWAITING_FOUNDER_DECISION:
        "A publication-grade observation exists on this property's own "
        "surface, its identity is confirmed and its evidence rederives. "
        "Nothing further is owed by the machine; the outstanding step is a "
        "founder decision, and no amount of re-capturing produces one.",
    enums.ACCESS_BLOCKED:
        "The surface refused to serve us. Records the FETCH OUTCOME only: a "
        "fabricated property code returns the same 403 as a real one, so a "
        "refusal proves nothing about the property.",
}

#: Legacy classifications from the four markets, folded onto the normalised
#: blocker set. Compatibility only -- deleted when the window closes.
LEGACY_BLOCKER_ALIASES: Dict[str, str] = {
    "NO_OFFICIAL_URL": enums.AWAITING_OFFICIAL_URL,
    "URL_SHAPE_NOT_PROPERTY": enums.AWAITING_PROPERTY_LEVEL_URL,
    "OFFICIAL_URL_RETURNS_404": enums.AWAITING_ROUTING_REPLACEMENT,
    "ROUTED_URL_RESOLVES_TO_A_DIFFERENT_BUSINESS": enums.AWAITING_ROUTING_REPLACEMENT,
    "ROUTING_DESTINATION_REFUSED_TO_RENDER": enums.AWAITING_ROUTING_REPLACEMENT,
    "ROUTING_CORRECTION_REJECTED_NO_VALID_REPLACEMENT": enums.AWAITING_ROUTING_REVIEW,
    "ROUTING_CORRECTION_ACCEPTED": enums.AWAITING_ROUTING_REVIEW,
    "PAGE_RENDERED_NO_PET_POLICY_STATED": enums.AWAITING_POLICY_OBSERVATION,
    "AFFIRMATIVE_POLICY_TRANSCRIBED_NO_ARTIFACT": enums.AWAITING_POLICY_ARTIFACT,
    "NEGATIVE_POLICY_TRANSCRIBED_NO_ARTIFACT": enums.AWAITING_POLICY_ARTIFACT,
    "ROUTED_AWAITING_CAPTURE": enums.AWAITING_POLICY_ARTIFACT,
    "SELECTOR_OR_SURFACE_GAP": enums.AWAITING_ATTENDED_CAPTURE,
    "POLICY_MODAL_BLANK": enums.AWAITING_ATTENDED_CAPTURE,
    "JS_RENDERED_BLANK_CONTENT": enums.AWAITING_ATTENDED_CAPTURE,
    "FAQ_QUESTION_RENDERED_WITHOUT_ITS_ANSWER": enums.AWAITING_ATTENDED_CAPTURE,
    "PAGE_STATES_BOTH_PET_FRIENDLY_AND_NO_PETS": enums.AWAITING_CONTRADICTION_RESOLUTION,
    "CLASSIFICATION_CONTRADICTS_TRANSCRIPTION": enums.AWAITING_CONTRADICTION_RESOLUTION,
    "QUEUED_IDENTITY_IS_NOT_LODGING": enums.AWAITING_CENSUS_REVIEW,
    "IDENTITY_SOURCE_RECOVERY": enums.AWAITING_IDENTITY_RESOLUTION,
    "ADR_ACCESS_BLOCKED": enums.ACCESS_BLOCKED,
    "ANTI_BOT_CHALLENGE": enums.ACCESS_BLOCKED,
    "SOURCE_BLOCKED": enums.ACCESS_BLOCKED,
    "ADAPTER_GAP_INDEPENDENT": enums.ACCESS_BLOCKED,
    "ROUTED_NO_BRAND_ADAPTER": enums.ACCESS_BLOCKED,
}


@dataclass(frozen=True)
class Reconciliation:
    """Set-based agreement between a census and its partition.

    Every count here is derived from the partition's own rows. None is obtained
    by subtracting one bucket from another.
    """

    market_id: str
    census_count: int
    partition_count: int
    missing_from_partition: Tuple[str, ...]
    missing_from_census: Tuple[str, ...]
    duplicated_in_partition: Tuple[str, ...]
    counts_by_state: Mapping[str, int]

    @property
    def published(self) -> int:
        return self.counts_by_state.get(enums.PUBLISHED_PET_FRIENDLY, 0)

    @property
    def verified_no_pets(self) -> int:
        return self.counts_by_state.get(enums.VERIFIED_NO_PETS, 0)

    @property
    def out_of_category(self) -> int:
        return self.counts_by_state.get(enums.OUT_OF_CURRENT_CATEGORY, 0)

    @property
    def resolved(self) -> int:
        return sum(self.counts_by_state.get(s, 0) for s in enums.TERMINAL_STATES)

    @property
    def unresolved(self) -> int:
        return sum(self.counts_by_state.get(s, 0) for s in enums.BLOCKER_STATES)

    @property
    def agrees(self) -> bool:
        return not (self.missing_from_partition or self.missing_from_census
                    or self.duplicated_in_partition
                    or self.census_count != self.partition_count)


def normalise_blocker(value: str) -> str:
    """Fold a legacy classification onto the normalised blocker set.

    Returns the input unchanged when it is already canonical or unrecognised;
    ``validate`` reports the unrecognised case rather than this function
    guessing.
    """
    if value in enums.PARTITION_STATES:
        return value
    return LEGACY_BLOCKER_ALIASES.get(value, value)


def identity_keys(document: Mapping) -> Set[str]:
    keys: Set[str] = set()
    for item in document.get("items") or ():
        if not isinstance(item, Mapping):
            continue
        key = item.get("identity_key")
        if not key and item.get("canonical_name"):
            try:
                key = ptf_identity_key(item["canonical_name"])
            except IdentityKeyError:
                key = ""
        if key:
            keys.add(key)
    return keys


def reconcile(census_keys: Set[str], document: Mapping, *,
              market_id: str = "") -> Reconciliation:
    """Compare a partition against its census by SET, and count by state."""
    counts: Dict[str, int] = {}
    seen: Dict[str, int] = {}
    for item in document.get("items") or ():
        if not isinstance(item, Mapping):
            continue
        state = normalise_blocker(item.get("final_state") or "")
        counts[state] = counts.get(state, 0) + 1
        key = item.get("identity_key") or ""
        if not key and item.get("canonical_name"):
            try:
                key = ptf_identity_key(item["canonical_name"])
            except IdentityKeyError:
                key = ""
        if key:
            seen[key] = seen.get(key, 0) + 1

    partition_keys = set(seen)
    return Reconciliation(
        market_id=market_id or str(document.get("market_id") or ""),
        census_count=len(census_keys),
        partition_count=sum(1 for i in (document.get("items") or ())
                            if isinstance(i, Mapping)),
        missing_from_partition=tuple(sorted(census_keys - partition_keys)),
        missing_from_census=tuple(sorted(partition_keys - census_keys)),
        duplicated_in_partition=tuple(sorted(k for k, n in seen.items() if n > 1)),
        counts_by_state=counts,
    )


def validate(document: Mapping) -> Tuple[Issue, ...]:
    """Validate a partition document at 1.1."""
    out: List[Issue] = []
    if not isinstance(document, Mapping):
        return (Issue("partition", "NOT_OBJECT", "partition must be an object"),)

    if document.get("schema") not in (SCHEMA, "ptf-market-final-partition/1.0"):
        out.append(Issue("schema", "BAD_SCHEMA",
                         "expected %r, got %r" % (SCHEMA, document.get("schema"))))
    if not document.get("market_id"):
        out.append(Issue("market_id", "MISSING_REQUIRED", "market_id is required"))

    items = document.get("items")
    if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
        out.append(Issue("items", "NOT_LIST", "items must be a list"))
        return tuple(out)

    for index, item in enumerate(items):
        path = "items[%d]" % index
        if not isinstance(item, Mapping):
            out.append(Issue(path, "NOT_OBJECT", "a partition row must be an object"))
            continue

        key = item.get("identity_key")
        if not key:
            out.append(Issue(path + ".identity_key", "MISSING_REQUIRED",
                             "identity_key is the join key for every layer"))
        elif not is_canonical_key(key):
            out.append(Issue(path + ".identity_key", "NOT_CANONICAL",
                             "%r is not the output of ptf_identity_key/1.0" % key))

        raw_state = item.get("final_state") or ""
        state = normalise_blocker(raw_state)
        if not enums.is_member(state, enums.PARTITION_STATES):
            out.append(Issue(path + ".final_state", "BAD_ENUM",
                             "%r is not a partition state" % raw_state))
            continue

        terminal = state in enums.TERMINAL_STATES
        next_action = (item.get("next_action") or "").strip()

        if terminal:
            # A published hotel with outstanding work is a contradiction the
            # partition must be able to reject.
            if next_action:
                out.append(Issue(path + ".next_action", "TERMINAL_WITH_ACTION",
                                 "%s is terminal but carries a next action"
                                 % state))
            if item.get("resolved") is not True:
                out.append(Issue(path + ".resolved", "TERMINAL_NOT_RESOLVED",
                                 "%s must be marked resolved" % state))
        else:
            if not next_action:
                out.append(Issue(path + ".next_action", "MISSING_REQUIRED",
                                 "an unresolved identity needs exactly one "
                                 "next action"))
            if not (item.get("next_action_source") or "").strip():
                out.append(Issue(path + ".next_action_source", "MISSING_REQUIRED",
                                 "record which pass determined this"))
            if not (item.get("determined_by") or "").strip():
                out.append(Issue(path + ".determined_by", "MISSING_REQUIRED",
                                 "record the work order that set this state"))
            if item.get("resolved") is True:
                out.append(Issue(path + ".resolved", "BLOCKER_MARKED_RESOLVED",
                                 "%s is a blocker but the row claims resolved"
                                 % state))
    return tuple(out)


def reconciliation_issues(rec: Reconciliation) -> Tuple[Issue, ...]:
    """Turn a set comparison into reportable issues."""
    out: List[Issue] = []
    if rec.census_count != rec.partition_count:
        out.append(Issue("partition", "COUNT_MISMATCH",
                         "census declares %d identities, partition carries %d"
                         % (rec.census_count, rec.partition_count)))
    for key in rec.missing_from_partition:
        out.append(Issue("partition[%s]" % key, "MISSING_FROM_PARTITION",
                         "census identity has no partition row"))
    for key in rec.missing_from_census:
        out.append(Issue("partition[%s]" % key, "MISSING_FROM_CENSUS",
                         "partition row has no census identity"))
    for key in rec.duplicated_in_partition:
        out.append(Issue("partition[%s]" % key, "DUPLICATE_ROW",
                         "identity appears more than once"))
    return tuple(out)


def routing_subset_violations(routes: Sequence[Mapping], census_keys: Set[str],
                              *, market_id: str) -> Tuple[Issue, ...]:
    """Accommodation routes whose identity is absent from the market census.

    The frozen invariant, with no exceptions for accommodation. A route binding
    an official URL to an identity the census does not carry means either the
    census is incomplete or the route belongs to something we do not sell --
    both census questions, resolved by adding the row or retiring the route.

    Cross-category routing belongs in a separate authority under its own
    census, never in an exception clause here.
    """
    out: List[Issue] = []
    for route in routes:
        if not isinstance(route, Mapping):
            continue
        if route.get("market_id") != market_id:
            continue
        if route.get("status") == enums.ROUTING_RETIRED:
            continue
        category = route.get("category", enums.CATEGORY_ACCOMMODATION)
        if category != enums.CATEGORY_ACCOMMODATION:
            continue
        ref = route.get("hotel_ref") or {}
        key = ref.get("identity_key") or ""
        if not key and ref.get("canonical_name"):
            try:
                key = ptf_identity_key(ref["canonical_name"])
            except IdentityKeyError:
                key = ""
        if key and key not in census_keys:
            out.append(Issue("identity_routing[%s]" % (route.get("routing_id") or key),
                             "ROUTE_NOT_IN_CENSUS",
                             "%r holds an accommodation route but is absent "
                             "from %s's census"
                             % (ref.get("canonical_name") or key, market_id)))
    return tuple(out)
