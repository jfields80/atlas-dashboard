"""PTF-DISCOVERY-001 WO-1A Step 9 -- OfficialUrlRecord and pre-handoff revalidation.

Amendment v1.1 §A8/§B4 and ``INV-URL-REVALIDATE``, with FD-5's parameters:

  * default revalidation cadence: **30 days**;
  * immediate revalidation on a changed redirect destination, a changed
    provider record, a proposed rebrand/rename, an identity conflict, or a
    queued URL older than its allowed validation age;
  * **"same property identity" requires at least two independent stable keys**;
  * name alone NEVER establishes same-property identity;
  * a redirect whose destination fails that check **blocks the handoff**.

The inputs already exist and are projected here rather than re-fetched:
``importer/fetch.py`` captures the full per-hop ``redirect_chain`` with per-hop
re-validation, ``website_fetcher`` persists it, and
``website_resolution.validate_fetched_identity`` already produces the PASS/FAIL
identity signal. This module gives that evidence a durable shape and a rule.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, FrozenSet, Optional, Sequence, Tuple

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.membrane import assert_dataclasses_clean

# --------------------------------------------------------------------------- #
# FD-5 parameters.
# --------------------------------------------------------------------------- #

DEFAULT_REVALIDATION_CADENCE_DAYS = 30

#: Independent stable keys that may establish same-property identity (FD-5).
#: Deliberately excludes name: a name is not a stable key, and two independent
#: keys of the same kind are not independent.
KEY_NORMALIZED_STREET_ADDRESS = "normalized_street_address"
KEY_POSTAL_PLUS_STREET_NUMBER = "postal_code_plus_street_number"
KEY_OFFICIAL_PROPERTY_ID = "official_property_id"
KEY_PROPERTY_PHONE = "property_phone"
KEY_VERIFIED_COORDINATES = "verified_coordinates"
KEY_STABLE_CHAIN_IDENTIFIER = "stable_chain_property_identifier"

STABLE_IDENTITY_KEYS: FrozenSet[str] = frozenset({
    KEY_NORMALIZED_STREET_ADDRESS, KEY_POSTAL_PLUS_STREET_NUMBER,
    KEY_OFFICIAL_PROPERTY_ID, KEY_PROPERTY_PHONE, KEY_VERIFIED_COORDINATES,
    KEY_STABLE_CHAIN_IDENTIFIER,
})

MINIMUM_STABLE_KEYS = 2

#: Never sufficient, alone or in combination with nothing else.
NON_IDENTITY_SIGNALS = frozenset({"name", "normalized_name", "brand", "page_title"})

# property_identity_check values (amendment §B4).
IDENTITY_PASS = "PASS"
IDENTITY_FAIL = "FAIL"
IDENTITY_UNCHECKED = "UNCHECKED"
IDENTITY_CHECK_VALUES = frozenset({IDENTITY_PASS, IDENTITY_FAIL, IDENTITY_UNCHECKED})

# Immediate-revalidation triggers (FD-5).
TRIGGER_REDIRECT_CHANGED = "REDIRECT_DESTINATION_CHANGED"
TRIGGER_PROVIDER_RECORD_CHANGED = "PROVIDER_RECORD_CHANGED"
TRIGGER_REBRAND_OR_RENAME_PROPOSED = "REBRAND_OR_RENAME_PROPOSED"
TRIGGER_IDENTITY_CONFLICT = "PROPERTY_IDENTITY_CONFLICT"
TRIGGER_STALE = "VALIDATION_AGE_EXCEEDED"
TRIGGER_NEVER_VALIDATED = "NEVER_VALIDATED"

REVALIDATION_TRIGGERS = frozenset({
    TRIGGER_REDIRECT_CHANGED, TRIGGER_PROVIDER_RECORD_CHANGED,
    TRIGGER_REBRAND_OR_RENAME_PROPOSED, TRIGGER_IDENTITY_CONFLICT,
    TRIGGER_STALE, TRIGGER_NEVER_VALIDATED,
})


class UrlRecordError(ValueError):
    """Raised when a URL record is malformed."""


# --------------------------------------------------------------------------- #
# Identity determination (FD-5).
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class IdentityKeyAgreement:
    """Which stable keys agreed between the queued URL's property and the
    redirect destination's property."""

    agreeing_keys: Tuple[str, ...] = ()
    conflicting_keys: Tuple[str, ...] = ()
    non_identity_signals_seen: Tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "agreeing_keys": list(self.agreeing_keys),
            "conflicting_keys": list(self.conflicting_keys),
            "non_identity_signals_seen": list(self.non_identity_signals_seen),
        }


def same_property_identity(agreement: IdentityKeyAgreement) -> Tuple[str, str]:
    """Return ``(property_identity_check, explanation)``.

    FD-5: at least two INDEPENDENT stable keys must agree, and any conflicting
    stable key fails outright -- a stable key that disagrees is evidence of a
    different property, not noise to be outvoted.
    """
    unknown = [k for k in agreement.agreeing_keys if k not in STABLE_IDENTITY_KEYS]
    if unknown:
        raise UrlRecordError("not a recognized stable identity key: %s" % (sorted(unknown),))

    if agreement.conflicting_keys:
        return (IDENTITY_FAIL,
                "stable key(s) disagree: %s" % ", ".join(sorted(agreement.conflicting_keys)))

    distinct = set(agreement.agreeing_keys)
    if len(distinct) >= MINIMUM_STABLE_KEYS:
        return (IDENTITY_PASS,
                "%d independent stable keys agree: %s"
                % (len(distinct), ", ".join(sorted(distinct))))

    if len(distinct) == 1:
        return (IDENTITY_FAIL,
                "only one stable key agrees (%s); FD-5 requires at least %d"
                % (next(iter(distinct)), MINIMUM_STABLE_KEYS))

    if agreement.non_identity_signals_seen:
        return (IDENTITY_FAIL,
                "only non-identity signals matched (%s); name alone never "
                "establishes same-property identity"
                % ", ".join(sorted(agreement.non_identity_signals_seen)))

    return (IDENTITY_FAIL, "no stable identity keys agreed")


# --------------------------------------------------------------------------- #
# OfficialUrlRecord (amendment §B4).
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class RedirectHop:
    from_url: str
    to_url: str

    def to_dict(self) -> dict:
        return {"from_url": self.from_url, "to_url": self.to_url}


@dataclass(frozen=True)
class OfficialUrlRecord:
    url: str
    status: str                                     # constants.WEBSITE_RES_* / OfficialUrlStatus
    last_validated_at: str = ""                     # ISO date; "" == never
    redirect_history: Tuple[RedirectHop, ...] = ()
    canonical_destination: str = ""
    property_identity_check: str = IDENTITY_UNCHECKED
    identity_explanation: str = ""
    revalidation_cadence_days: int = DEFAULT_REVALIDATION_CADENCE_DAYS
    confidence_signals: Tuple[str, ...] = ()

    def validate(self) -> None:
        if self.property_identity_check not in IDENTITY_CHECK_VALUES:
            raise UrlRecordError("unknown property_identity_check: %r"
                                 % self.property_identity_check)
        if self.revalidation_cadence_days <= 0:
            raise UrlRecordError("revalidation cadence must be positive")

    def to_dict(self) -> dict:
        return {
            "url": self.url, "status": self.status,
            "last_validated_at": self.last_validated_at,
            "redirect_history": [h.to_dict() for h in self.redirect_history],
            "canonical_destination": self.canonical_destination,
            "property_identity_check": self.property_identity_check,
            "identity_explanation": self.identity_explanation,
            "revalidation_cadence_days": self.revalidation_cadence_days,
            "confidence_signals": list(self.confidence_signals),
        }

    @property
    def redirects(self) -> bool:
        return bool(self.canonical_destination and self.canonical_destination != self.url)


def is_stale(record: OfficialUrlRecord, *, as_of: str) -> bool:
    """Age check against an EXPLICIT date -- no wall clock, so replay is stable."""
    if not record.last_validated_at:
        return True
    try:
        validated = date.fromisoformat(record.last_validated_at)
        now = date.fromisoformat(as_of)
    except ValueError:
        return True                     # unparseable: fail closed, revalidate
    return now > validated + timedelta(days=record.revalidation_cadence_days)


def revalidation_triggers(record: OfficialUrlRecord, *, as_of: str,
                          redirect_destination_changed: bool = False,
                          provider_record_changed: bool = False,
                          rebrand_or_rename_proposed: bool = False,
                          identity_conflict: bool = False) -> Tuple[str, ...]:
    """Every FD-5 reason this URL must be revalidated now. Empty means fresh."""
    triggers = []
    if not record.last_validated_at:
        triggers.append(TRIGGER_NEVER_VALIDATED)
    elif is_stale(record, as_of=as_of):
        triggers.append(TRIGGER_STALE)
    if redirect_destination_changed:
        triggers.append(TRIGGER_REDIRECT_CHANGED)
    if provider_record_changed:
        triggers.append(TRIGGER_PROVIDER_RECORD_CHANGED)
    if rebrand_or_rename_proposed:
        triggers.append(TRIGGER_REBRAND_OR_RENAME_PROPOSED)
    if identity_conflict:
        triggers.append(TRIGGER_IDENTITY_CONFLICT)
    return tuple(sorted(set(triggers)))


# --------------------------------------------------------------------------- #
# The handoff gate.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class HandoffDecision:
    allowed: bool
    reason: str
    triggers: Tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"allowed": self.allowed, "reason": self.reason,
                "triggers": list(self.triggers)}


def evaluate_handoff(record: OfficialUrlRecord, *, as_of: str,
                     redirect_destination_changed: bool = False,
                     provider_record_changed: bool = False,
                     rebrand_or_rename_proposed: bool = False,
                     identity_conflict: bool = False) -> HandoffDecision:
    """Decide whether this URL may cross into the policy worker.

    Fail-closed in three distinct ways, each with its own diagnosable reason:
    a FAILED identity check blocks outright; an UNCHECKED record on a URL that
    actually redirects blocks (we do not know where it goes); and a stale or
    trigger-hit record blocks until revalidated.
    """
    record.validate()

    if record.property_identity_check == IDENTITY_FAIL:
        return HandoffDecision(
            False,
            "property_identity_check=FAIL: %s" % (record.identity_explanation
                                                  or "redirect resolves to a different property"))

    triggers = revalidation_triggers(
        record, as_of=as_of,
        redirect_destination_changed=redirect_destination_changed,
        provider_record_changed=provider_record_changed,
        rebrand_or_rename_proposed=rebrand_or_rename_proposed,
        identity_conflict=identity_conflict)

    if record.redirects and record.property_identity_check == IDENTITY_UNCHECKED:
        return HandoffDecision(
            False, "url redirects to %s and property identity was never checked"
            % record.canonical_destination, triggers)

    if triggers:
        return HandoffDecision(
            False, "revalidation required: %s" % ", ".join(triggers), triggers)

    return HandoffDecision(True, "validated within cadence and identity confirmed")


def summarize_decisions(decisions: Sequence[HandoffDecision]) -> Dict[str, int]:
    counts = {"allowed": 0, "blocked": 0}
    for d in decisions:
        counts["allowed" if d.allowed else "blocked"] += 1
        for t in d.triggers:
            counts[t] = counts.get(t, 0) + 1
    return dict(sorted(counts.items()))


assert_dataclasses_clean(OfficialUrlRecord, RedirectHop, IdentityKeyAgreement,
                         HandoffDecision, context="discovery.url_record")
