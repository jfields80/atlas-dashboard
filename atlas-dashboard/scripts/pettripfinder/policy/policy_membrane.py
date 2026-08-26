"""PTF-POLICY-P0-001 -- the POLICY face of the Membrane (M1..M12).

``discovery/membrane.py`` enforces one direction: a discovery record may not
declare a pet-policy field. This module enforces the other, and it is the
harder direction, because the failure mode is not a smuggled field name but
quiet erosion -- an OTA line that looks official enough, a brand FAQ applied to
a property that never said it, a fee read off a truncated search snippet. Each
of those produces a page that tells someone their dog is welcome, and they find
out at the front desk at 11pm.

So every rule here has three parts: the rule, the point that enforces it, and
an explicit failing state. A rule without a failing state is a convention, and
conventions do not survive contact with a batch of 200 hotels.

WHAT THIS MODULE DOES NOT DO
----------------------------
It does not adjudicate. It does not choose between contradicting sources, and
it never writes a policy fact. ``evaluate()`` returns a verdict; the caller
records it. A rejection is not a deletion -- rejected observations are retained
with their state, the same honesty pattern the routing airlock already uses for
REVIEW/REJECTED.

RELATIONSHIP TO EXISTING PRODUCTION GATES
-----------------------------------------
Several of these rules already exist in production in another form, and this
module deliberately mirrors rather than replaces them:

* M9 (no field without a quote) is the portable pre-handback form of the
  production exact-evidence gate (``routing.MODEL_OVERCLAIM`` /
  ``EXACT_EVIDENCE_MISMATCH`` / ``INCOMPLETE_EXTRACTION``).
* M10 (wrong property) serializes the existing capture-time identity gate
  (``capture_automation.identity_check``, reason ``IDENTITY_MISMATCH``).
* M8 (contradiction) hands off to the existing approval-resolution mechanism;
  it records the conflict and refuses to pick a winner.
* M12 (negative facts) routes to the existing exclusion authority
  (``hotel_exclusions``, ``VERIFIED_NO_PETS``).

Pure and deterministic: no network, no clock, no file reads.
"""

from __future__ import annotations

import html
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.discovery.property_identity import (  # noqa: E402
    street_identity,
)
from scripts.pettripfinder.policy.policy_observation import (  # noqa: E402
    ARCHIVE_SOURCE_TYPE,
    ESTABLISHING_TIERS,
    NON_ESTABLISHING_FIELDS,
    PT1_OFFICIAL_PROPERTY,
    PT2_BRAND_GENERIC,
    PT4_NON_AUTHORITATIVE,
    SNIPPET_SOURCE_TYPE,
    SOURCE_TYPE_MAX_TIER,
    PolicyObservationError,
    asserted_fields,
    establishing_fields,
    quoted_fields,
    validate_observation,
)

# --------------------------------------------------------------------------- #
# Verdicts. Closed vocabulary.
# --------------------------------------------------------------------------- #

VALID = "VALID"
VALID_HINT_ONLY = "VALID_HINT_ONLY"

REJECT_MALFORMED_OBSERVATION = "REJECT_MALFORMED_OBSERVATION"
REJECT_TIER_FORBIDS_ESTABLISH = "REJECT_TIER_FORBIDS_ESTABLISH"
REJECT_BRAND_GENERIC_AS_PROPERTY = "REJECT_BRAND_GENERIC_AS_PROPERTY"
REJECT_SNIPPET_EXTRACTION = "REJECT_SNIPPET_EXTRACTION"
REJECT_STALE_SOLE_BASIS = "REJECT_STALE_SOLE_BASIS"
REJECT_FIELD_WITHOUT_EVIDENCE = "REJECT_FIELD_WITHOUT_EVIDENCE"
REJECT_WRONG_PROPERTY = "REJECT_WRONG_PROPERTY"
REJECT_POLICY_AS_IDENTITY = "REJECT_POLICY_AS_IDENTITY"

VERDICTS = (VALID, VALID_HINT_ONLY, REJECT_MALFORMED_OBSERVATION,
            REJECT_TIER_FORBIDS_ESTABLISH, REJECT_BRAND_GENERIC_AS_PROPERTY,
            REJECT_SNIPPET_EXTRACTION, REJECT_STALE_SOLE_BASIS,
            REJECT_FIELD_WITHOUT_EVIDENCE, REJECT_WRONG_PROPERTY,
            REJECT_POLICY_AS_IDENTITY)

REJECTING_VERDICTS = frozenset(v for v in VERDICTS if v.startswith("REJECT_"))

#: Rule id -> one-line statement, for diagnostics that a person can read.
RULES = {
    "M1": "an identity-grade source never establishes policy; it may hint only",
    "M2": "OTA/aggregator text never overwrites an official policy",
    "M3": "brand-generic policy never auto-becomes property-specific",
    "M4": "a search snippet can never establish a numeric field",
    "M5": "archive/cached evidence can never be the sole basis of a current fact",
    "M6": "service-animal language is never a pet policy",
    "M7": "INFERRED extraction never publishes",
    "M8": "contradictory official sources adjudicate, never auto-select",
    "M9": "no field without a quote",
    "M10": "wrong property means no evidence, whatever the text says",
    "M11": "policy observations never establish identity",
    "M12": "negative facts are first-class and equally guarded",
}


@dataclass(frozen=True)
class MembraneVerdict:
    """The result of putting one observation through the membrane.

    ``verdict`` is closed; ``rule`` names which rule decided it; ``hint_only``
    says the observation survives but may contribute nothing establishing.
    """

    verdict: str
    rule: str = ""
    detail: str = ""
    hint_only: bool = False
    stripped_fields: Tuple[str, ...] = ()
    flags_raised: Tuple[str, ...] = ()

    @property
    def rejected(self) -> bool:
        return self.verdict in REJECTING_VERDICTS

    @property
    def may_establish(self) -> bool:
        """True only when this observation may contribute a publishable field."""
        return self.verdict == VALID and not self.hint_only

    def to_dict(self) -> Dict:
        return {"verdict": self.verdict, "rule": self.rule, "detail": self.detail,
                "hint_only": self.hint_only,
                "stripped_fields": list(self.stripped_fields),
                "flags_raised": list(self.flags_raised),
                "rule_statement": RULES.get(self.rule, "")}


# --------------------------------------------------------------------------- #
# Helpers.
# --------------------------------------------------------------------------- #

def _tokens(name: str) -> frozenset:
    """Comparable tokens for a hotel name, accents folded.

    PTF-COLUMBUS-SELECTOR-CLOSEOUT-001. Marriott's page calls the hotel "Le
    Méridien Columbus, The Joseph" and the record calls it "Le Meridien
    Columbus, The Joseph". Without folding, the split on ``[^a-z0-9]+`` treats
    the accented character as a SEPARATOR, so "méridien" arrives as two tokens,
    "m" and "ridien". The page's set was then neither a subset nor a superset of
    the record's and M10 rejected a capture whose identity gate had already
    CONFIRMED it on property code and address.

    Folding is the conservative direction, not the permissive one. It can only
    equate names that differ by a diacritic -- which are the same name to any
    reader -- while what it removes is a real hazard: a shattered "m" is a
    one-character token free to appear inside unrelated hotels' names, and the
    subset test is exactly where such fragments do damage. No other part of the
    identity rule moves; a genuine name mismatch still fails, and the
    conjunctive code-plus-address override remains the only way past it.
    """
    # HTML entities are decoded FIRST. A page that serves "Holiday Inn Express
    # &amp; Suites" and a record that holds "&" are the same eight characters
    # once decoded; left encoded, the "&" fires the ampersand rule and leaves a
    # stray "amp" token in one set and not the other. Seven IHG properties in
    # one market were refused as the wrong hotel over that token.
    # Purely corrective: unescaping cannot introduce a token that the decoded
    # name does not actually contain.
    text = html.unescape(name or "").lower().replace("&", " and ")
    text = "".join(c for c in unicodedata.normalize("NFKD", text)
                   if not unicodedata.combining(c))
    return frozenset(t for t in re.split(r"[^a-z0-9]+", text) if t)


#: Qualifiers that name an OWNER or a soft brand, never a building. Stripped
#: only inside the street-plus-name override below, never from the M10 name rule
#: itself.
_CHAIN_QUALIFIER_RE = re.compile(
    r"\b(?:by|at)\s+(?:ihg|wyndham|marriott|hilton|choice|radisson|sonesta|"
    r"hyatt|best\s+western)\b|"
    r"\b(?:tapestry|autograph|curio|tribute|signature)\s+collection\b",
    re.IGNORECASE)

#: Tokens that appear in thousands of hotel names and distinguish none of them.
#: A reference name made ONLY of these is a bare chain word, and the override
#: below refuses it however well the address agrees.
_GENERIC_NAME_TOKENS = frozenset({
    "inn", "hotel", "hotels", "suites", "suite", "motel", "lodge", "resort",
    "and", "by", "at", "the", "of", "a", "an", "stay", "extended", "select",
    "express", "plaza", "house", "place", "collection", "hampton", "courtyard",
    "doubletree", "wingate", "hilton", "marriott", "wyndham", "ihg", "choice",
    "radisson", "sonesta", "hyatt", "best", "western", "days", "super", "8",
    "6", "travelodge", "baymont", "microtel", "comfort", "quality", "sleep",
    "econo", "red", "roof", "la", "quinta", "holiday", "candlewood",
    "residence", "springhill", "fairfield", "garden", "woodspring", "drury",
    "sheraton", "westin", "aloft", "element", "tru", "home2", "avid",
    "staybridge", "embassy", "hyatt", "america", "americas", "value", "budget",
})


def _has_distinguishing_token(name: str) -> bool:
    """Does this name say WHICH building, not just which chain?

    The override below is allowed to equate names that differ by a chain
    qualifier. That is safe for "Holiday Inn Express & Suites Edwardsville by
    IHG" and catastrophic for "Hampton": every Hampton Inn in the market is a
    superset of the token {hampton}, so a bare chain word plus a matching street
    would let ANY page of that chain establish a fact against a record that
    names no building at all. St. Louis carries five such census rows.

    So the override requires the REFERENCE name to retain at least one token
    that is not a chain word, a lodging word or a filler word.
    """
    return bool(_tokens(_CHAIN_QUALIFIER_RE.sub(" ", name or ""))
                - _GENERIC_NAME_TOKENS)


def _street_agrees(reference, page) -> bool:
    """Do a stored street identity and a street printed on a page agree?

    ``street_identity`` returns ``"<street>|<postal>"``, and a hotel page prints
    its street in the page furniture while very often omitting the postal code.
    Comparing the two composites therefore fails on rows whose street matches
    character for character: ``"1320 thornton st|63069"`` against
    ``"1320 thornton st|"``.

    So the halves are compared separately. The STREET must agree and is never
    optional. The POSTAL code is checked only when BOTH sides carry one -- an
    absent postal is a silent page, not a disagreement, and treating silence as
    disagreement is the same mistake this codebase names everywhere else.

    A street alone is weaker than a street plus a postal, which is exactly why
    every caller here uses it as one half of a CONJUNCTIVE test and never on its
    own.
    """
    left = street_identity(str(reference or "").split("|")[0])
    right = street_identity(str(page or "").split("|")[0])
    left_street, _, left_postal = left.partition("|")
    right_street, _, right_postal = right.partition("|")
    if not left_street or not right_street:
        return False
    if left_street != right_street:
        return False
    if left_postal and right_postal and left_postal != right_postal:
        return False
    # Guard against a degenerate "street" that is really just a number.
    return len(left_street.split()) >= 2


def _same_property_by_street_and_qualified_name(ref, check) -> bool:
    """M10's second narrow escape: the STREET agrees and the names differ only
    by an owner qualifier.

    The first escape needs a brand property code, and only Marriott and Hilton
    put one on the page. IHG, Wyndham and Choice put a street address and a
    telephone and nothing else, so twelve St. Louis captures whose identity the
    capture gate had already confirmed were refused here -- eight of them over
    the single token "amp", the rest over "by IHG".

    This stays CONJUNCTIVE and stays narrower than the name rule it overrides:

      * the STREET IDENTITY must be present on both sides and agree. An address
        is per-building; it is the same key the first escape already trusts.
      * the names must agree ONCE OWNER QUALIFIERS ARE REMOVED. "... Edwardsville
        by IHG" and "... Edwardsville" are one hotel; "by IHG" says who owns it.
      * the reference name must still NAME A BUILDING after that removal. A bare
        chain word is refused outright -- see ``_has_distinguishing_token``.

    All three, or nothing. Dropping the third turns this into exactly the hole
    PTF-COLUMBUS-IDENTITY-CLEANUP-001 refused to open.
    """
    if not _street_agrees(ref.get("street_identity"),
                          check.get("address_on_page")):
        return False

    reference = str(ref.get("canonical_name") or "")
    if not _has_distinguishing_token(reference):
        return False

    # A property code present on BOTH sides and DISAGREEING is positive proof of
    # a different hotel, and nothing below may override it. cmhcees and cmhates
    # are two Columbus Embassy Suites; a disagreeing code is a disagreement, not
    # the silence an absent code represents.
    ref_code = str(ref.get("property_code") or "").strip().lower()
    page_code = str(check.get("property_code") or "").strip().lower()
    if ref_code and page_code and ref_code != page_code:
        return False

    known = (_tokens(_CHAIN_QUALIFIER_RE.sub(" ", reference))
             | _tokens(_CHAIN_QUALIFIER_RE.sub(
                 " ", str(ref.get("normalized_name") or ""))))
    page = _tokens(_CHAIN_QUALIFIER_RE.sub(
        " ", str(check.get("name_on_page") or "")))
    if not known or not page:
        return False
    # ONE DIRECTION ONLY: the page must name AT LEAST what the record names.
    #
    # The symmetric test looks natural and is the hole PTF-COLUMBUS-IDENTITY-
    # CLEANUP-001 refused to open. Embassy Suites Columbus - Airport/Corporate
    # Exchange sits on Corporate Exchange Drive and its page calls itself
    # "Embassy Suites by Hilton Columbus" -- a name the AIRPORT sibling answers
    # to just as well. A page that names LESS than the record cannot tell the
    # record's hotel from a sibling that shares the shorter name, so the street
    # is doing all the work and the street alone was never enough.
    #
    # Requiring the page to be the superset costs three St. Louis rows whose
    # pages drop a real token ("& Suites", "Airport"). Those go back to a human,
    # which is the right side to be wrong on.
    return known <= page


def _same_property_by_code_and_address(ref, check) -> bool:
    """M10's narrow escape: a NAME mismatch alone is not a wrong property when
    two stronger, independent keys both say otherwise.

    PTF-COLUMBUS-IDENTITY-CLEANUP-001. Embassy Suites Columbus -
    Airport/Corporate Exchange is captured cleanly, identity-CONFIRMED at
    capture time on address + phone + property code, and rejected here because
    its own JSON-LD calls it "Embassy Suites by Hilton Columbus" -- a generic
    name sharing no distinguishing token with the canonical record. The obvious
    repair, renaming the record to match, was tested and REFUSED: Columbus has
    three Embassy Suites and the rename made the already-published Airport
    property a token subset of this one, so a capture of THAT hotel would have
    passed against THIS record.

    So the name rule is not relaxed. Instead a mismatch may be overridden ONLY
    by CONJUNCTIVE proof that is immune to that collision:

      * the brand's own property code, present on both sides and exactly equal
        -- cmhcees, cmhates and cmheses are three different hotels and no two
        share a code; and
      * the street identity, present on both sides and agreeing.

    Both, or nothing. Either one alone is weaker than the name check it would
    be overriding: a code with no address cannot prove the page is the building
    on record, and an address with no code cannot tell two businesses at one
    campus apart. Requiring both is what makes this narrower than M10, not
    wider.
    """
    ref_code = str(ref.get("property_code") or "").strip().lower()
    page_code = str(check.get("property_code") or "").strip().lower()
    if not ref_code or not page_code or ref_code != page_code:
        return False

    return _street_agrees(ref.get("street_identity"),
                          check.get("address_on_page"))


def registrable_domain(url: str) -> str:
    """Last two labels of the host. Deliberately simple: this is used only to
    catch a booking-mirror claiming to be the property's own site, where the
    difference is never subtle (``h-rez.com`` vs ``druryhotels.com``)."""
    host = re.sub(r"^https?://", "", url or "").split("/")[0].lower()
    labels = [l for l in host.split(".") if l]
    return ".".join(labels[-2:]) if len(labels) >= 2 else host


def _flag_codes(observation: Mapping) -> Tuple[str, ...]:
    return tuple(f.get("code", "") for f in observation.get("flags") or ())


# --------------------------------------------------------------------------- #
# The membrane.
# --------------------------------------------------------------------------- #

def evaluate(observation: Mapping) -> MembraneVerdict:
    """Put one observation through M1..M12 in a fixed order.

    Order matters and is not arbitrary: structural validity first (a malformed
    record cannot be reasoned about), then the rules that void the observation
    outright (snippet, brand-generic, wrong property), then the rules that
    reduce it (hint-only), then the evidence rule. The strongest claim is
    tested last so a record that fails an earlier rule never gets the chance to
    look established.
    """
    try:
        observation = validate_observation(observation)
    except PolicyObservationError as exc:
        return MembraneVerdict(REJECT_MALFORMED_OBSERVATION, rule="",
                               detail=str(exc))

    tier = observation["authority_tier"]
    source_type = observation["source_type"]
    extraction = observation["extraction"]
    evidence = observation["evidence"]
    flags = _flag_codes(observation)

    # --- tier honesty: a source may not claim more than its type allows ---- #
    max_tier = SOURCE_TYPE_MAX_TIER[source_type]
    if _tier_rank(tier) > _tier_rank(max_tier):
        return MembraneVerdict(
            REJECT_TIER_FORBIDS_ESTABLISH, rule="M1",
            detail="source_type %r may claim at most %s, but the observation "
                   "claims %s" % (source_type, max_tier, tier))

    asserted = asserted_fields(extraction)
    establishing = establishing_fields(extraction)

    # --- M4: a snippet is truncated by construction ------------------------ #
    if source_type == SNIPPET_SOURCE_TYPE and extraction:
        return MembraneVerdict(
            REJECT_SNIPPET_EXTRACTION, rule="M4",
            detail="a search snippet may not carry extraction fields: "
                   "truncation invents meaning ('$25 per night' may be the "
                   "head of '$25 per night, maximum $150 per stay')")

    # --- M3: brand-generic never becomes property-specific ----------------- #
    if tier == PT2_BRAND_GENERIC and establishing:
        return MembraneVerdict(
            REJECT_BRAND_GENERIC_AS_PROPERTY, rule="M3",
            detail="a brand-generic source carries establishing field(s) %s; "
                   "brand policy may corroborate a property-specific statement "
                   "but never populate one" % sorted(establishing))

    # --- M1/M2: PT4 hints, never establishes ------------------------------- #
    if tier == PT4_NON_AUTHORITATIVE:
        if establishing:
            return MembraneVerdict(
                VALID_HINT_ONLY, rule="M2",
                detail="non-authoritative source retained as a hint; its "
                       "extraction may raise a contradiction flag for review "
                       "but may never become or overwrite an official fact",
                hint_only=True,
                stripped_fields=tuple(sorted(establishing)))
        return MembraneVerdict(VALID, rule="M2", hint_only=True)

    # --- M10: wrong property means no evidence ----------------------------- #
    ref = observation["hotel_ref"]
    check = observation["identity_check"]
    page = _tokens(check["name_on_page"])
    known = _tokens(ref["normalized_name"]) | _tokens(ref["canonical_name"])
    if not (known <= page or page <= known):
        # A FOUNDER may adjudicate an identity the automatic escapes refuse,
        # and compare_identities already routes exactly this shape to
        # NEEDS_ADJUDICATION: "one telephone number but different names and
        # streets -- adjudicate, never merge automatically". The override is
        # per-row, carries who decided it and what they saw, and can only ever
        # be placed there by a human; the machine has no path that writes one.
        adjudicated = bool((observation.get("identity_adjudication") or {})
                           .get("approved_by"))
        if not (adjudicated
                or _same_property_by_code_and_address(ref, check)
                or _same_property_by_street_and_qualified_name(ref, check)):
            return MembraneVerdict(
                REJECT_WRONG_PROPERTY, rule="M10",
                detail="identity gate: the page identifies %r, which is neither "
                       "a subset nor a superset of the referenced identity %r, "
                       "and neither an exact property-code + street-address "
                       "agreement nor a street-address + owner-qualified-name "
                       "agreement establishes it another way"
                       % (check["name_on_page"], ref["canonical_name"]))
    official = ref.get("official_url", "")
    if tier == PT1_OFFICIAL_PROPERTY and official and \
            registrable_domain(official) != registrable_domain(observation["source_url"]):
        return MembraneVerdict(
            REJECT_WRONG_PROPERTY, rule="M10",
            detail="booking-mirror rule: a PT1 capture sits on %r but the "
                   "property's official domain on record is %r"
                   % (registrable_domain(observation["source_url"]),
                      registrable_domain(official)))

    # --- M9: no field without a quote -------------------------------------- #
    uncovered = sorted(asserted - quoted_fields(evidence))
    if uncovered:
        return MembraneVerdict(
            REJECT_FIELD_WITHOUT_EVIDENCE, rule="M9",
            detail="extraction field(s) %s are asserted with no supporting "
                   "evidence quote -- a value with no quote is an overclaim"
                   % uncovered)

    return MembraneVerdict(VALID, rule="", flags_raised=flags)


def _tier_rank(tier: str) -> int:
    """PT1 strongest. Used only to catch a source claiming above its type."""
    return {"PT1": 4, "PT3": 3, "PT2": 2, "PT4": 1}.get(tier, 0)


def evaluate_batch(batch: Sequence[Mapping]) -> List[MembraneVerdict]:
    """Every observation judged independently. A rejection never aborts the
    batch -- the caller keeps the rejected record with its state."""
    return [evaluate(o) for o in batch]


# --------------------------------------------------------------------------- #
# Cross-observation rules (M5, M8) -- these need the SET, not one record.
# --------------------------------------------------------------------------- #

def archive_only(observations: Sequence[Mapping]) -> bool:
    """M5: true when every surviving observation is an archive snapshot.

    An archive can corroborate a current fact and can carry history, but it can
    never be the only thing a live claim rests on -- what a page said in 2023
    is not what it says now.
    """
    if not observations:
        return False
    return all(o.get("source_type") == ARCHIVE_SOURCE_TYPE for o in observations)


def contradicting_pairs(observations: Sequence[Mapping]) -> List[Dict]:
    """M8: official observations that assert different values for one field.

    Returns the pairs; it does NOT choose. Supersession is a recorded decision
    in the existing approval-resolution mechanism, and 'latest wins' applied
    silently is exactly the failure this rule exists to prevent.
    """
    establishing = [o for o in observations
                    if o.get("authority_tier") in ESTABLISHING_TIERS]
    out: List[Dict] = []
    for i, a in enumerate(establishing):
        for b in establishing[i + 1:]:
            shared = (asserted_fields(a.get("extraction") or {})
                      & asserted_fields(b.get("extraction") or {}))
            for field_name in sorted(shared):
                if field_name in NON_ESTABLISHING_FIELDS:
                    continue
                if a["extraction"][field_name] != b["extraction"][field_name]:
                    out.append({
                        "field": field_name,
                        "obs_a": a.get("obs_id", ""),
                        "obs_b": b.get("obs_id", ""),
                        "value_a": a["extraction"][field_name],
                        "value_b": b["extraction"][field_name],
                        "rule": "M8",
                        "resolution": "adjudication required; this layer never "
                                      "selects a winner",
                    })
    return out


def service_animal_only(observation: Mapping) -> bool:
    """M6: the observation says something about service animals and nothing
    about ordinary pets. ADA access is a legal category, never a pet policy."""
    extraction = observation.get("extraction") or {}
    asserted = asserted_fields(extraction)
    if not asserted:
        return False
    return asserted <= NON_ESTABLISHING_FIELDS


def infers_without_publishing(observation: Mapping) -> bool:
    """M7: INFERRED extraction may be recorded, never published."""
    return observation.get("extraction_confidence") == "INFERRED"


__all__ = [
    "VALID", "VALID_HINT_ONLY", "VERDICTS", "REJECTING_VERDICTS", "RULES",
    "REJECT_MALFORMED_OBSERVATION", "REJECT_TIER_FORBIDS_ESTABLISH",
    "REJECT_BRAND_GENERIC_AS_PROPERTY", "REJECT_SNIPPET_EXTRACTION",
    "REJECT_STALE_SOLE_BASIS", "REJECT_FIELD_WITHOUT_EVIDENCE",
    "REJECT_WRONG_PROPERTY", "REJECT_POLICY_AS_IDENTITY",
    "MembraneVerdict", "evaluate", "evaluate_batch",
    "archive_only", "contradicting_pairs", "service_animal_only",
    "infers_without_publishing", "registrable_domain",
]
