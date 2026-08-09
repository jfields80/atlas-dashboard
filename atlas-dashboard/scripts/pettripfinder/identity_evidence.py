"""PTF-DISCOVERY-AUTHORITY-001 -- identity evidence is not policy evidence.

Until now one standard governed both questions: does this hotel exist, and what
is its pet policy. Both required the property's own official page. That is right
for the policy and wrong for the identity, and the cost is measurable -- the
Northeast Ohio census carries a zero for the Independence/Rockside business-hotel
cluster, not because it has no hotels but because every source that would name
them refuses an identified agent.

So this module splits the two:

  IDENTITY   may be established from trustworthy non-property sources, in tiers,
             with cross-source agreement required as the tier weakens.
  PET POLICY is untouched. It still comes only from the property's own official
             source, and ``assert_no_policy_from_identity_evidence`` exists to
             make an accidental crossing of that line a loud failure rather than
             a quiet one.

The asymmetry is deliberate. Getting an identity slightly wrong produces a page
about a hotel that turns out to be named differently. Getting a policy wrong
tells someone their dog is welcome when it is not, and they find out at the
front desk at 11pm. Those failures are not comparable, so their evidence bars
are not either.

Pure and deterministic: no network, no clock, no file reads. The caller supplies
evidence records; this module only judges them.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.hotel_exclusions import address_key  # noqa: E402
from scripts.pettripfinder.site_data import normalize_name      # noqa: E402

SCHEMA = "ptf-identity-evidence/1.0"

# --------------------------------------------------------------------------- #
# Evidence tiers, strongest first.
# --------------------------------------------------------------------------- #

TIER_1_OFFICIAL_PROPERTY = 1      #: the hotel's own page, or its chain's locator
TIER_2_OFFICIAL_DESTINATION = 2   #: CVB, tourism bureau, airport, city/county body
TIER_3_BUSINESS_LISTING = 3       #: established business/map listing with exact identity
TIER_4_OTA_DIRECTORY = 4          #: major OTA or property directory listing
TIER_5_CORROBORATED = 5           #: no single source; several weaker ones agreeing

TIERS = (TIER_1_OFFICIAL_PROPERTY, TIER_2_OFFICIAL_DESTINATION, TIER_3_BUSINESS_LISTING,
         TIER_4_OTA_DIRECTORY, TIER_5_CORROBORATED)

TIER_NAMES = {
    TIER_1_OFFICIAL_PROPERTY: "official property or chain locator",
    TIER_2_OFFICIAL_DESTINATION: "official destination, tourism or government body",
    TIER_3_BUSINESS_LISTING: "established business or map listing",
    TIER_4_OTA_DIRECTORY: "major OTA or property directory",
    TIER_5_CORROBORATED: "corroboration across weaker sources",
}

#: The ONLY tier a pet-policy fact may ever come from. This is not a default a
#: caller can widen -- see assert_no_policy_from_identity_evidence.
POLICY_ELIGIBLE_TIERS = (TIER_1_OFFICIAL_PROPERTY,)

#: Every pet-policy field name in the production vocabulary, plus the additive
#: names PTF-POLICY-PRECISION-001 introduced. An identity record carrying any of
#: these is a contract violation, not a richer record.
POLICY_FIELD_NAMES = frozenset({
    "pets_allowed", "species_allowed", "cats_allowed", "pet_fee", "fee_basis",
    "fee_tiers", "fee_cap", "fee_conflict", "fee_withheld", "fee_scope",
    "pet_count_limit", "pet_count_scope", "weight_limit", "weight_limit_operator",
    "weight_limit_combined", "weight_limit_combined_operator",
    "weight_limit_stated_none", "breed_restrictions", "breed_restrictions_stated_none",
    "pet_deposit", "unattended_policy", "general_restrictions", "refundability",
    "species_weight_limits", "fee_pet_schedule", "pet_room_restriction",
    "eligible_room_types", "reservation_requirement",
})

# --------------------------------------------------------------------------- #
# Outcomes.
# --------------------------------------------------------------------------- #

IDENTITY_CONFIRMED = "IDENTITY_CONFIRMED"
IDENTITY_PROVISIONAL = "IDENTITY_PROVISIONAL"
IDENTITY_CONFLICT = "IDENTITY_CONFLICT"
POSSIBLE_REBRAND = "POSSIBLE_REBRAND"
POSSIBLE_CLOSURE = "POSSIBLE_CLOSURE"

OUTCOMES = (IDENTITY_CONFIRMED, IDENTITY_PROVISIONAL, IDENTITY_CONFLICT,
            POSSIBLE_REBRAND, POSSIBLE_CLOSURE)

#: Wording that marks a source as reporting the property gone or renamed. Matched
#: against a source's own status note, never against free prose.
CLOSURE_MARKERS = ("permanently closed", "closed permanently", "no longer operating",
                   "ceased operations")
REBRAND_MARKERS = ("formerly", "now known as", "rebranded", "renamed", "was the",
                   "converted to")


class IdentityEvidenceError(ValueError):
    """An evidence record is malformed, or policy has been smuggled into it."""


REQUIRED_EVIDENCE_FIELDS = ("tier", "source_family", "source_url", "observed_at", "name")


def validate_evidence(record: Mapping) -> Dict:
    """Fail closed on a malformed record, and on any policy field."""
    missing = [f for f in REQUIRED_EVIDENCE_FIELDS if not str(record.get(f, "")).strip()]
    if missing:
        raise IdentityEvidenceError("evidence missing required field(s) %s" % missing)
    if record["tier"] not in TIERS:
        raise IdentityEvidenceError("unknown tier %r" % (record["tier"],))
    leaked = sorted(POLICY_FIELD_NAMES & set(record))
    if leaked:
        raise IdentityEvidenceError(
            "identity evidence may not carry pet-policy field(s) %s -- identity and policy are "
            "separate contracts and only an official property source may establish a policy"
            % leaked)
    return dict(record)


def assert_no_policy_from_identity_evidence(evidence: Iterable[Mapping],
                                            facts: Mapping = None) -> None:
    """Raise if a caller is about to derive policy facts from identity evidence.

    Call this at the boundary where an identity record would become a policy
    record. It refuses on two grounds: the evidence carrying policy fields, and
    a proposed fact set backed by anything other than Tier 1.
    """
    records = [validate_evidence(e) for e in evidence]
    if not facts:
        return
    offered = sorted(POLICY_FIELD_NAMES & set(facts))
    if not offered:
        return
    tiers = {r["tier"] for r in records}
    if not tiers <= set(POLICY_ELIGIBLE_TIERS):
        raise IdentityEvidenceError(
            "refusing to derive pet-policy field(s) %s from tier %s evidence. Only an official "
            "property source (tier 1) may establish a pet policy; a business listing, map entry, "
            "OTA page or search result never can, however many of them agree."
            % (offered, sorted(tiers - set(POLICY_ELIGIBLE_TIERS))))


# --------------------------------------------------------------------------- #
# Agreement.
# --------------------------------------------------------------------------- #

def _street(record: Mapping) -> str:
    return address_key(record.get("address", ""), record.get("postal_code", ""))


def _has_address(record: Mapping) -> bool:
    return bool(str(record.get("address", "")).strip()
                and str(record.get("postal_code", "")).strip())


def independent(a: Mapping, b: Mapping) -> bool:
    """Two records are independent when they come from different source families.

    Two pages of one directory are one source, not two -- otherwise a single
    publisher's mistake could confirm itself.
    """
    return (a.get("source_family") or "").lower() != (b.get("source_family") or "").lower()


def agree(a: Mapping, b: Mapping) -> bool:
    """Same normalized name AND same street identity."""
    return (normalize_name(a.get("name", "")) == normalize_name(b.get("name", ""))
            and _has_address(a) and _has_address(b) and _street(a) == _street(b))


def adjudicate(evidence: Sequence[Mapping]) -> Dict:
    """Judge one candidate identity from its evidence. Deterministic.

    The rules, in order:

      * a source reporting the property permanently closed  -> POSSIBLE_CLOSURE
      * a source reporting a rename, or two names at one
        street identity                                     -> POSSIBLE_REBRAND
      * sources disagreeing on street identity for one name  -> IDENTITY_CONFLICT
      * one tier-1 or tier-2 source carrying a full address  -> IDENTITY_CONFIRMED
      * two INDEPENDENT sources of tier 4 or better agreeing
        on name and street identity                         -> IDENTITY_CONFIRMED
      * anything else                                        -> IDENTITY_PROVISIONAL

    A blocked chain page therefore costs nothing: a CVB listing alone confirms,
    and so does a business listing plus an independent OTA that agree.
    """
    records = [validate_evidence(e) for e in evidence]
    if not records:
        return {"outcome": IDENTITY_PROVISIONAL, "reason": "no evidence supplied",
                "tiers": [], "sources": []}

    tiers = sorted({r["tier"] for r in records})
    sources = sorted({r["source_family"] for r in records})
    base = {"tiers": tiers, "sources": sources,
            "evidence_count": len(records),
            "best_tier": min(tiers)}

    closed = [r for r in records
              if any(m in str(r.get("status_note", "")).lower() for m in CLOSURE_MARKERS)]
    if closed:
        return {**base, "outcome": POSSIBLE_CLOSURE,
                "reason": "a source reports the property permanently closed: %r"
                          % closed[0]["source_family"]}

    renamed = [r for r in records
               if any(m in str(r.get("status_note", "")).lower() for m in REBRAND_MARKERS)]
    addressed = [r for r in records if _has_address(r)]
    names = {normalize_name(r["name"]) for r in records}
    streets = {_street(r) for r in addressed}
    if renamed:
        return {**base, "outcome": POSSIBLE_REBRAND,
                "reason": "a source reports a rename: %r" % renamed[0]["source_family"]}
    if len(streets) > 1 and len(names) == 1:
        return {**base, "outcome": IDENTITY_CONFLICT,
                "reason": "one name, %d different street identities: %s"
                          % (len(streets), sorted(streets))}
    if len(names) > 1 and len(streets) == 1 and streets:
        # Two names at one address. Never merged here: it is either a rebrand or a
        # genuine same-campus pair, and both need a human.
        return {**base, "outcome": POSSIBLE_REBRAND,
                "reason": "%d names share one street identity %s -- rebrand or same-campus pair, "
                          "not merged" % (len(names), sorted(streets)[0])}

    official = [r for r in addressed
                if r["tier"] in (TIER_1_OFFICIAL_PROPERTY, TIER_2_OFFICIAL_DESTINATION)]
    if official:
        return {**base, "outcome": IDENTITY_CONFIRMED,
                "reason": "tier-%d source (%s) carries the full identity"
                          % (official[0]["tier"], official[0]["source_family"])}

    for i, a in enumerate(addressed):
        for b in addressed[i + 1:]:
            if a["tier"] <= TIER_4_OTA_DIRECTORY and b["tier"] <= TIER_4_OTA_DIRECTORY \
                    and independent(a, b) and agree(a, b):
                return {**base, "outcome": IDENTITY_CONFIRMED,
                        "reason": "independent tier-%d and tier-%d sources (%s, %s) agree on name "
                                  "and street identity"
                                  % (a["tier"], b["tier"], a["source_family"], b["source_family"])}

    if not addressed:
        return {**base, "outcome": IDENTITY_PROVISIONAL,
                "reason": "no source supplied a street address and postal code"}
    return {**base, "outcome": IDENTITY_PROVISIONAL,
            "reason": "only %d source(s) below tier 2, without independent agreement"
                      % len(addressed)}


def identity_record(name: str, evidence: Sequence[Mapping], **extra) -> Dict:
    """A judged identity, carrying its provenance. Never carries policy."""
    verdict = adjudicate(evidence)
    rec = {"schema": SCHEMA, "name": name, "normalized_name": normalize_name(name),
           "identity_outcome": verdict["outcome"], "identity_reason": verdict["reason"],
           "identity_tiers": verdict["tiers"], "identity_sources": verdict["sources"],
           "policy_state": "POLICY_NOT_VERIFIED",
           "policy_note": ("Identity evidence never establishes a pet policy. This record is "
                           "policy-unverified until an official property source is read."),
           "evidence": [validate_evidence(e) for e in evidence]}
    for k, v in extra.items():
        if k in POLICY_FIELD_NAMES:
            raise IdentityEvidenceError(
                "%r is a pet-policy field and may not be attached to an identity record" % k)
        rec[k] = v
    return rec
