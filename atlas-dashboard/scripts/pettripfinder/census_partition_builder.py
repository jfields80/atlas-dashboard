"""PTF-CENSUS-PARTITION-NORMALIZATION-001 -- deterministic census and partition.

What this module is for
-----------------------
Until now the system could not say which identities a market contains. Columbus
had no committed census at all and its unresolved count was derived by
subtracting published and excluded from a number that lived only in a work-order
report. That arithmetic is right for every WRONG membership: swap a published
identity for one absent from the universe and the total does not move.

This builder replaces that with a set. It derives, from committed authority
only, a ``ptf-market-identity-census/1.1`` and a
``ptf-market-final-partition/1.1`` for each market, and records for every
identity the authority it came from.

Determinism
-----------
Same inputs, same bytes. Every collection is sorted by canonical identity key,
no timestamps are read from the clock, and nothing here fetches, guesses, or
infers a fact a source did not state. A blocker that cannot be derived from
committed evidence is an error, not a default.

What it deliberately does NOT do
--------------------------------
No policy fact is read for its content, no corridor is reassigned (Phase D owns
geography), no route is re-researched, and no identity is resolved. The
partition states what each identity is waiting on; it does not wait less.
"""

from __future__ import annotations

import csv
import json
from collections import OrderedDict
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts.identity_key import (
    IDENTITY_KEY_CONTRACT, ptf_identity_key,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_DIR = REPO_ROOT / "launch_packages" / "pettripfinder"
from scripts.pettripfinder import census_location as CENSUS_LOCATION  # noqa: E402
CENSUS_DIR = CENSUS_LOCATION.identity_census_dir()  # committed, or $PTF_IDENTITY_CENSUS_DIR during a rebuild
WORK_ORDER = "PTF-CENSUS-PARTITION-NORMALIZATION-001"


class BuilderError(ValueError):
    """Committed evidence does not support a deterministic answer (fail closed)."""


# --------------------------------------------------------------------------
# blocker derivation
# --------------------------------------------------------------------------

#: Dayton's Work-browser outcome vocabulary, folded onto the canonical blockers.
#:
#: This ledger is a HUMAN adjudication: a reviewer looked at the property and
#: recorded what has to happen next. It therefore outranks the recovery pass's
#: fetch-failure label for the same identity -- "hilton.com 403" is why an
#: earlier attempt failed, not what anyone should do now.
WORK_BROWSER_OUTCOME_BLOCKERS: Dict[str, str] = {
    "IDENTITY_ONLY": enums.AWAITING_POLICY_OBSERVATION,
    "IDENTITY_BLOCKED": enums.AWAITING_OFFICIAL_URL,
    "EVIDENCE_CANDIDATE_AWAITING_ACCEPTED_ARTIFACT": enums.AWAITING_POLICY_ARTIFACT,
    "ROUTING_REVIEW_REQUIRED": enums.AWAITING_ROUTING_REVIEW,
    "MANUAL_VERIFICATION_REQUIRED": enums.AWAITING_CENSUS_REVIEW,
    "ACCESS_BLOCKED": enums.ACCESS_BLOCKED,
    "POLICY_PARTIAL_HELD_BY_READINESS": enums.AWAITING_POLICY_ARTIFACT,
    "CLOSURE_OR_REBRAND_REVIEW": enums.AWAITING_CENSUS_REVIEW,
    "IDENTITY_OR_ROUTING_CORRECTED_POLICY_UNRESOLVED": enums.AWAITING_POLICY_OBSERVATION,
    "SELECTOR_OR_SURFACE_GAP": enums.AWAITING_ATTENDED_CAPTURE,
    "CONTRADICTION": enums.AWAITING_CONTRADICTION_RESOLUTION,
    "OTHER_UNRESOLVED": enums.AWAITING_CENSUS_REVIEW,
}

#: Reason codes that refine an outcome. Checked FIRST where present, because a
#: reason names the specific obstacle and an outcome names its class.
WORK_BROWSER_REASON_BLOCKERS: Dict[str, str] = {
    "PAGE_RENDERED_NO_PET_POLICY_STATED": enums.AWAITING_POLICY_OBSERVATION,
    "NO_FIRST_PARTY_URL_ON_RECORD": enums.AWAITING_OFFICIAL_URL,
    "AFFIRMATIVE_POLICY_TRANSCRIBED_NO_ARTIFACT": enums.AWAITING_POLICY_ARTIFACT,
    "NEGATIVE_POLICY_TRANSCRIBED_NO_ARTIFACT": enums.AWAITING_POLICY_ARTIFACT,
    "ROUTE_RECORDED_HELD_DESTINATION_UNREADABLE": enums.AWAITING_ROUTING_REVIEW,
    "ROUTING_PROPOSAL_REJECTED": enums.AWAITING_ROUTING_REPLACEMENT,
    "OFFICIAL_URL_RETURNS_404": enums.AWAITING_ROUTING_REPLACEMENT,
    "BRAND_PLATFORM_REFUSED_THE_BROWSER": enums.ACCESS_BLOCKED,
    "ANTI_BOT_CHALLENGE": enums.ACCESS_BLOCKED,
    "JS_RENDERED_BLANK_CONTENT": enums.AWAITING_ATTENDED_CAPTURE,
    "POLICY_MODAL_BLANK": enums.AWAITING_ATTENDED_CAPTURE,
    "FAQ_QUESTION_RENDERED_WITHOUT_ITS_ANSWER": enums.AWAITING_ATTENDED_CAPTURE,
    "ROUTED_URL_RESOLVES_TO_A_DIFFERENT_BUSINESS": enums.AWAITING_ROUTING_REPLACEMENT,
    "PAGE_STATES_BOTH_PET_FRIENDLY_AND_NO_PETS": enums.AWAITING_CONTRADICTION_RESOLUTION,
    "CLASSIFICATION_CONTRADICTS_TRANSCRIPTION": enums.AWAITING_CONTRADICTION_RESOLUTION,
    "QUEUED_IDENTITY_IS_NOT_LODGING": enums.AWAITING_CENSUS_REVIEW,
}

#: The recovery pass's fetch-outcome vocabulary. Lower precedence: it records
#: why a machine could not read a page, which is a fact about our attempt
#: rather than about the property.
RECOVERY_CATEGORY_BLOCKERS: Dict[str, str] = {
    "ACCESS_BLOCKED": enums.ACCESS_BLOCKED,
    "NO_FIRST_PARTY_URL_ON_RECORD": enums.AWAITING_OFFICIAL_URL,
    "JS_RENDERED_NO_STATIC_CONTENT": enums.AWAITING_ATTENDED_CAPTURE,
    "IDENTITY_UNCERTAIN_PHANTOM_SUSPECT": enums.AWAITING_IDENTITY_RESOLUTION,
    "UNREACHABLE_DOMAIN": enums.AWAITING_ROUTING_REPLACEMENT,
    "IDENTITY_RECOVERED_POLICY_STILL_NEEDED": enums.AWAITING_POLICY_OBSERVATION,
    "ROUTED_AWAITING_CAPTURE": enums.AWAITING_POLICY_ARTIFACT,
    "ADAPTER_GAP_INDEPENDENT": enums.ACCESS_BLOCKED,
    "ROUTED_NO_BRAND_ADAPTER": enums.ACCESS_BLOCKED,
    "ADR_ACCESS_BLOCKED": enums.ACCESS_BLOCKED,
    "SELECTOR_OR_SURFACE_GAP": enums.AWAITING_ATTENDED_CAPTURE,
    "URL_SHAPE_NOT_PROPERTY": enums.AWAITING_PROPERTY_LEVEL_URL,
    "IDENTITY_SOURCE_RECOVERY": enums.AWAITING_IDENTITY_RESOLUTION,
}

#: The one next action each blocker demands. Operational by construction --
#: "TBD" and "review later" are not actions, and the contract rejects them.
BLOCKER_NEXT_ACTIONS: Dict[str, str] = {
    enums.AWAITING_OFFICIAL_URL:
        "Find and bind this property's own official page, then record a routing "
        "record with its identity signals.",
    enums.AWAITING_PROPERTY_LEVEL_URL:
        "Replace the brand index or city-level URL with the property's own page.",
    enums.AWAITING_ROUTING_REVIEW:
        "Confirm the held routing destination first-party, or reject it and "
        "record a replacement.",
    enums.AWAITING_ROUTING_REPLACEMENT:
        "Replace the bound URL: the destination on record is not this "
        "property's page.",
    enums.AWAITING_POLICY_OBSERVATION:
        "Capture the property's pet-policy surface on its own official page.",
    enums.AWAITING_POLICY_ARTIFACT:
        "Capture a citable artifact of the surface the policy wording was read "
        "from; a transcription binds the typing, not the page.",
    enums.AWAITING_ATTENDED_CAPTURE:
        "Run an attended browser capture: the policy sits behind a click, an "
        "accordion, a modal or client-side rendering.",
    enums.AWAITING_CONTRADICTION_RESOLUTION:
        "Adjudicate the conflicting evidence and record which reading the "
        "source supports.",
    enums.AWAITING_CENSUS_REVIEW:
        "Review this identity's presence and category in the market census.",
    enums.AWAITING_IDENTITY_RESOLUTION:
        "Resolve the property's identity before binding any policy evidence "
        "to it.",
    enums.AWAITING_FOUNDER_DECISION:
        "Put this candidate in front of the founder: approve the policy, "
        "approve the refusal, or hold it with a reason.",
    enums.ACCESS_BLOCKED:
        "Attempt an attended or authenticated capture, or a direct operator "
        "call: the surface refused automated access.",
}


def next_action_for(blocker: str) -> str:
    action = BLOCKER_NEXT_ACTIONS.get(blocker)
    if not action:
        raise BuilderError("no next action defined for blocker %r" % blocker)
    return action


# --------------------------------------------------------------------------
# document assembly
# --------------------------------------------------------------------------

def census_row(*, identity_key: str, canonical_name: str, slug: str,
               market_id: str, city: str, state: str, postal_code: str,
               identity_state: str, lodging_state: str, policy_state: str,
               source: str, source_id: str = "", display_name: str = "",
               address: str = "", phone: str = "", corridor: str = "",
               assignment_basis: str = "", assignment_value: str = "",
               collision_state: str = enums.COLLISION_NONE,
               observed_at: str = "", provenance: str = "",
               official_url: str = "",
               carried: Optional[Mapping] = None) -> "OrderedDict":
    """One canonical census row.

    ``provenance`` names the committed authority this identity came from. It is
    what makes the reconstruction auditable rather than asserted: a reviewer can
    take any row and find the file it was derived from.

    ``carried`` is every field the source row had that 1.1 does not name. It is
    appended verbatim, and the reason is not tidiness: an upgrade that emits
    only the fields it knows about silently DELETES the rest. Dropping
    ``normalized_name`` alone broke Cleveland's partition generator, which
    joins on it -- and the identities it would have failed to find were real.
    An additive upgrade adds; it does not quietly replace.
    """
    row = OrderedDict((
        ("identity_key", identity_key),
        ("canonical_name", canonical_name),
        ("display_name", display_name or canonical_name),
        ("slug", slug),
        ("market_id", market_id),
        ("address", address),
        ("city", city),
        ("state", state),
        ("postal_code", postal_code),
        ("phone", phone),
        ("identity_state", identity_state),
        ("lodging_state", lodging_state),
        ("policy_state", policy_state),
        ("collision_state", collision_state),
        # The property's own page, where an authority records one. Carried on
        # the census rather than left in a private "_official_url" key so the
        # partition can find it on a rebuild -- dropping it made a
        # deterministic builder produce two different partitions.
        ("official_url", official_url),
        ("corridor", corridor),
        ("assignment_basis", assignment_basis),
        ("assignment_value", assignment_value),
        ("source", source),
        ("source_id", source_id),
        ("observed_at", observed_at),
        ("provenance", provenance),
    ))
    for key, value in sorted((carried or {}).items()):
        if key not in row:
            row[key] = value
    return row


def census_document(market_id: str, rows: Sequence[Mapping], *,
                    captured_at: str, note: str,
                    source_authorities: Sequence[str],
                    carried: Optional[Mapping] = None) -> "OrderedDict":
    """A canonical census document.

    ``carried`` preserves every top-level block the source document had that
    1.1 does not name -- worker provenance, collision audits, the seed-removal
    ledger, the rollup counts. The same rule as the rows: an upgrade that emits
    only what it knows about DELETES the rest, and Dayton's document carries
    several blocks whose loss broke the tests that read them.
    """
    ordered = sorted(rows, key=lambda r: r["identity_key"])
    keys = [r["identity_key"] for r in ordered]
    duplicates = sorted({k for k in keys if keys.count(k) > 1})
    if duplicates:
        raise BuilderError("duplicate identity keys in %s census: %s"
                           % (market_id, duplicates))
    document = OrderedDict((
        ("schema", enums.CENSUS_SCHEMA),
        ("market_id", market_id),
        ("identity_key_contract", IDENTITY_KEY_CONTRACT),
        ("identity_contract", "ptf-identity-evidence/1.0"),
        ("work_order", WORK_ORDER),
        ("captured_at", captured_at),
        ("note", note),
        ("source_authorities", list(source_authorities)),
        ("count", len(ordered)),
    ))
    for key, value in sorted((carried or {}).items()):
        if key not in document and key != "hotels":
            document[key] = value
    document["hotels"] = ordered
    return document


def partition_item(*, identity_key: str, canonical_name: str, slug: str,
                   city: str, state: str, postal_code: str, final_state: str,
                   next_action_source: str, determined_by: str,
                   updated_at: str, official_url: str = "",
                   state_override_reason: str = "") -> "OrderedDict":
    terminal = final_state in enums.TERMINAL_STATES
    return OrderedDict((
        ("identity_key", identity_key),
        ("canonical_name", canonical_name),
        ("slug", slug),
        ("city", city),
        ("state", state),
        ("postal_code", postal_code),
        ("final_state", final_state),
        ("resolved", terminal),
        # A terminal identity has nothing outstanding. A blocked one has
        # exactly one thing outstanding. There is no third shape.
        ("next_action", "" if terminal else next_action_for(final_state)),
        ("next_action_source", "" if terminal else next_action_source),
        ("determined_by", "" if terminal else determined_by),
        ("updated_at", updated_at),
        ("official_url", official_url),
        ("state_override_reason", state_override_reason),
    ))


def partition_document(market_id: str, items: Sequence[Mapping], *,
                       as_of: str, note: str,
                       source_authorities: Sequence[str],
                       state_meanings: Optional[Mapping] = None) -> "OrderedDict":
    from scripts.pettripfinder.contracts.partition import STATE_MEANINGS

    ordered = sorted(items, key=lambda i: i["identity_key"])
    counts: "OrderedDict[str, int]" = OrderedDict()
    for state in enums.PARTITION_STATES:
        n = sum(1 for i in ordered if i["final_state"] == state)
        if n:
            counts[state] = n
    present = {i["final_state"] for i in ordered}
    return OrderedDict((
        ("schema", enums.PARTITION_SCHEMA),
        ("work_order", WORK_ORDER),
        ("market_id", market_id),
        ("as_of", as_of),
        ("note", note),
        ("source_authorities", list(source_authorities)),
        ("count", len(ordered)),
        ("final_state_counts", counts),
        ("final_state_meanings",
         OrderedDict((s, (state_meanings or STATE_MEANINGS)[s])
                     for s in enums.PARTITION_STATES if s in present)),
        ("items", ordered),
    ))


def write_json(path: Path, document: Mapping) -> str:
    """Write a document deterministically and return its sha256.

    ``newline="\\n"`` because the repository normalises line endings and a
    document written with platform newlines hashes differently on the next
    machine to open it.
    """
    import hashlib

    text = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# shared committed-authority readers
# --------------------------------------------------------------------------

def load(name: str) -> Mapping:
    return json.loads((PACKAGE_DIR / name).read_text(encoding="utf-8-sig"))


def seed_rows(market_id: str) -> List[Dict]:
    with (PACKAGE_DIR / "seed_businesses.csv").open(encoding="utf-8-sig") as fh:
        return [r for r in csv.DictReader(fh)
                if r.get("category") == "pet-friendly-hotels"
                and r.get("market_id") == market_id]


def published_keys(policy_file: str) -> Dict[str, Dict]:
    return {ptf_identity_key(h["name"]): h
            for h in load(policy_file)["hotels"]}


def exclusions_for(market_id: str) -> List[Dict]:
    return [e for e in load("hotel_exclusions.json")["exclusions"]
            if e.get("market_id") == market_id]


def routes_for(market_id: str) -> List[Dict]:
    return [r for r in load("identity_routing.json")["routes"]
            if r.get("market_id") == market_id]


def slugify(name: str) -> str:
    """The slug convention the committed censuses already use."""
    key = ptf_identity_key(name)
    return "-".join(key.split())


def exclusion_final_state(exclusion: Mapping) -> str:
    state = exclusion.get("exclusion_state")
    if state == enums.VERIFIED_NO_PETS:
        return enums.VERIFIED_NO_PETS
    if state == enums.OUT_OF_CURRENT_CATEGORY:
        return enums.OUT_OF_CURRENT_CATEGORY
    raise BuilderError("unknown exclusion_state %r for %r"
                       % (state, exclusion.get("canonical_name")))


def lodging_state_for_exclusion(exclusion: Mapping) -> str:
    """A category exit is NOT lodging; a no-pets hotel still is.

    The distinction matters because counting the two together would overstate
    negative evidence -- a bed-and-breakfast we do not cover has said nothing
    about pets.
    """
    if exclusion.get("exclusion_state") == enums.OUT_OF_CURRENT_CATEGORY:
        return enums.NOT_LODGING
    return enums.LODGING_CONFIRMED
