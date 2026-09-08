"""ATLAS-THROUGHPUT-003 -- the first-party evidence gate (H2).

A direct, machine-checkable gate from an authority record to its evidence.
For every proposed CLEAN_PET_FRIENDLY (policy) or CLEAN_VERIFIED_NO_PETS
(exclusion) record it checks eight things, each against the module that owns
the rule:

    PROPERTY IDENTITY   the record, its evidence references and the page's own
                        brand-scoped property code name ONE identity
                        (hotel_exclusions.brand_scoped_property_identity)
    SOURCE CLASS        publication-grade, first-party (contracts.evidence,
                        contracts.enums.FIRST_PARTY_GRADES); a competitor or
                        third-party source is LEAD ONLY and never qualifies
    SOURCE URL          a first-party endpoint, never a NEVER_OFFICIAL domain
                        (identity_routing.NEVER_OFFICIAL_DOMAINS), on the
                        identity's own domain or brand family
    CAPTURE HASH        every entry hashes the PAGE and the hash is bound to
                        the identity through the package's evidence references
    TIMESTAMP           an ISO date or datetime the capture was made at
    OPERATIVE QUOTE     the quoted words state the policy the record claims:
                        an acceptance for a pet-friendly record, a refusal for
                        a no-pets record -- read by the owning reader
                        (brightdata.policy_reading.parse); a fee, a count, a
                        weight, an amenity chip or a service-animal sentence
                        alone establishes nothing
    PARSED FACTS        every published fact is cited (contracts.evidence
                        .unevidenced_facts) and no cited quote contradicts the
                        fact it is cited for
    AUTHORITY STATUS    the record carries a publishable status and a review

The verdict for a record is ELIGIBLE only when every check passes. A record
that fails is named with the check and the reason; the classification names
the failure class the adversarial matrix tests (wrong property, lead only,
fee only, service animals only, amenity chip only, structured no-pets with
insufficient context, ...).
"""

from __future__ import annotations

import re
from collections import OrderedDict
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from scripts.pettripfinder import hotel_exclusions as HE
from scripts.pettripfinder import identity_routing as IR
from scripts.pettripfinder import sealed_market_package as SMP
from scripts.pettripfinder.brightdata import policy_reading as READER
from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts import evidence as EVIDENCE
from scripts.pettripfinder.contracts import service_animal as SERVICE_ANIMAL
from scripts.pettripfinder.contracts.identity_key import IdentityKeyError, ptf_identity_key

# Verdict classes.
ELIGIBLE = "ELIGIBLE"
CLASS_WRONG_PROPERTY = "WRONG_PROPERTY"
CLASS_LEAD_ONLY = "LEAD_ONLY"
CLASS_NOT_FIRST_PARTY_URL = "NOT_FIRST_PARTY_URL"
CLASS_IDENTITY_UNBOUND = "IDENTITY_UNBOUND"
CLASS_NO_CAPTURE_HASH = "NO_CAPTURE_HASH"
CLASS_NO_TIMESTAMP = "NO_TIMESTAMP"
CLASS_NO_QUOTE = "NO_QUOTE"
CLASS_FEE_ONLY = "FEE_ONLY"
CLASS_SERVICE_ANIMAL_ONLY = "SERVICE_ANIMAL_ONLY"
CLASS_AMENITY_CHIP_ONLY = "AMENITY_CHIP_ONLY"
CLASS_STRUCTURED_NO_PETS_INSUFFICIENT = "STRUCTURED_NO_PETS_INSUFFICIENT"
CLASS_QUOTE_CONTRADICTS = "QUOTE_CONTRADICTS_CLAIM"
CLASS_QUOTE_NOT_OPERATIVE = "QUOTE_NOT_OPERATIVE"
CLASS_FACT_UNCITED = "FACT_UNCITED"
CLASS_FACT_CONTRADICTED = "FACT_CONTRADICTED"
CLASS_STATUS_INVALID = "STATUS_INVALID"

CHECKS = ("PROPERTY_IDENTITY", "SOURCE_CLASS", "SOURCE_URL", "CAPTURE_HASH",
          "TIMESTAMP", "OPERATIVE_QUOTE", "PARSED_FACTS", "AUTHORITY_STATUS")

KIND_PET_FRIENDLY = "pet_friendly"
KIND_NO_PETS = "no_pets"

PUBLISHABLE_POLICY_STATUSES = frozenset({"VERIFIED_PET_FRIENDLY"})

#: A quote that is a machine key/value -- ``petsAllowed: false`` -- states
#: nothing a guest reads; the doctrine requires operative words for a refusal
#: (or an acceptance) unless the package proves the structured field is the
#: page's own policy surface, which a bare key/value cannot.
_STRUCTURED_KV = re.compile(
    r"^\s*[\"']?(?:[a-z]+(?:[A-Z][a-z0-9]*)+|[a-z0-9]+(?:[._][a-z0-9]+)+)[\"']?\s*[:=]\s*"
    r"[\"']?(?:true|false|yes|no|0|1|null)[\"']?\s*,?\s*$")

_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?$")

_FEE_FIELDS = ("pet_fee", "fee_tiers", "fee_pet_schedule", "fee_cap", "other_charges")


class Verdict(OrderedDict):
    """``eligible``, ``classification``, ``checks`` (name -> {pass, why})."""

    @property
    def eligible(self) -> bool:
        return bool(self["eligible"])


def parse_timestamp(value: str) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text or not _ISO.match(text):
        return None
    try:
        if len(text) == 10:
            return datetime.strptime(text, "%Y-%m-%d")
        text = text.replace("Z", "+00:00").replace(" ", "T")
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def classify_quote(quote: str, *, kind: str, context: str = "") -> Tuple[str, str]:
    """``(class, why)`` for one cited quote against the claim ``kind`` makes.

    ``ELIGIBLE`` when the quote is an operative statement of that claim.
    ``context`` is every other quote cited from the SAME page: the reader's
    amenity-chip rule judges a policy BLOCK ("states no fee, no count, no
    weight, no species and no condition"), and a record's citations split
    that block per field -- "Pets Welcome" beside "USD 50 nightly fee per
    pet" is a policy, alone on a facilities list it is a chip.
    """
    text = " ".join(str(quote or "").split())
    if not text:
        return CLASS_NO_QUOTE, "no quoted words"
    if _STRUCTURED_KV.match(text):
        return CLASS_STRUCTURED_NO_PETS_INSUFFICIENT if kind == KIND_NO_PETS else CLASS_QUOTE_NOT_OPERATIVE, \
            "a bare machine field (%r) is not the page's operative policy text" % text
    reading = READER.parse(text)
    animal = SERVICE_ANIMAL.classify(text)
    if kind == KIND_PET_FRIENDLY:
        accepts = reading.pets_allowed is True or bool(reading.both_species_quote) \
            or bool(reading.dogs_only_quote)
        if accepts and reading.pets_allowed is not False:
            block = " ".join(str(context or "").split())
            block_reading = READER.parse((text + " " + block).strip()) if block else reading
            if READER._is_amenity_label_only(reading) and (
                    block_reading.pets_allowed is not True or READER._is_amenity_label_only(block_reading)):
                return CLASS_AMENITY_CHIP_ONLY, "an amenity label states no policy: %r" % text
            return ELIGIBLE, "acceptance stated: %r" % (reading.pets_allowed_quote or reading.both_species_quote
                                                      or reading.dogs_only_quote)
        if reading.pets_allowed is False:
            return CLASS_QUOTE_CONTRADICTS, "the quote refuses pets: %r" % text
        if animal.interpretation != SERVICE_ANIMAL.SOURCE_SILENT or reading.service_animal_quote:
            return CLASS_SERVICE_ANIMAL_ONLY, ("a service-animal statement is a legal access category, "
                                               "never a pet acceptance: %r" % text)
        if reading.charges or reading.weight_value is not None or reading.pet_count_limit is not None:
            return CLASS_FEE_ONLY, "a fee, count or weight alone does not establish acceptance: %r" % text
        return CLASS_QUOTE_NOT_OPERATIVE, "no acceptance the reader will interpret: %r" % text
    # kind == KIND_NO_PETS
    if reading.pets_allowed is False:
        return ELIGIBLE, "refusal stated: %r" % text
    if reading.pets_allowed is True:
        return CLASS_QUOTE_CONTRADICTS, "the quote accepts pets: %r" % text
    if animal.interpretation != SERVICE_ANIMAL.SOURCE_SILENT or reading.service_animal_quote:
        # "Service animals only" IS the refusal form Hilton renders; the reader
        # owns that judgement. When it does not read a refusal, neither do we.
        return CLASS_SERVICE_ANIMAL_ONLY, ("a service-animal sentence is not a refusal unless the "
                                           "reader reads one: %r" % text)
    return CLASS_QUOTE_NOT_OPERATIVE, "no refusal the reader will interpret: %r" % text


def _property_binding(source_url: str, identity: Mapping) -> Tuple[bool, str]:
    """Does this page belong to THIS identity?"""
    domain = IR.registrable_domain(source_url)
    if not domain:
        return False, "no source URL"
    if domain in IR.NEVER_OFFICIAL_DOMAINS:
        return False, "%s is never a first-party source" % domain
    family, code = HE.brand_scoped_property_identity(source_url)
    own_url = str(identity.get("official_url") or "")
    own_domain = IR.registrable_domain(own_url)
    own_family, own_code = HE.brand_scoped_property_identity(own_url)
    declared_code = str(identity.get("property_code") or "").strip().lower()
    declared_family = str(identity.get("brand_family") or "").strip().upper().replace(" ", "_")
    expected_code = declared_code or own_code
    if family and code:
        if expected_code and family in (own_family, declared_family) and code != expected_code:
            return False, ("page carries %s property code %r, the identity is %r"
                           % (family, code, expected_code))
        if own_domain and own_domain != domain and family not in (own_family, declared_family):
            return False, "page is %s (%s), the identity is bound to %s" % (domain, family, own_domain)
        return True, "%s property code %r agrees" % (family, code) if expected_code else \
            "%s page, identity carries no code to compare" % family
    if own_domain:
        if own_domain == domain:
            return True, "the identity's own domain %s" % domain
        if family and family in (own_family, declared_family):
            return True, "brand family %s page without a code; family agrees" % family
        return False, "page is %s, the identity is bound to %s" % (domain, own_domain)
    if family and declared_family and family != declared_family:
        return False, "page is a %s page, the identity is %s" % (family, declared_family)
    return True, "first-party domain %s (identity binds no official URL to compare)" % domain


def _fact_contradictions(record: Mapping) -> List[str]:
    """Cited quotes the owning reader reads as a DIFFERENT value."""
    facts = record.get("facts") if isinstance(record.get("facts"), Mapping) else {}
    out: List[str] = []
    for entry in record.get("evidence") or ():
        if not isinstance(entry, Mapping):
            continue
        field = str(entry.get("field") or "")
        quote = " ".join(str(entry.get("quote") or "").split())
        if not quote:
            continue
        reading = READER.parse(quote)
        if field == "pet_fee" and isinstance(facts.get("pet_fee"), Mapping):
            stated = facts["pet_fee"].get("amount_cents")
            amounts = [c.amount_minor for c in reading.charges]
            if amounts and isinstance(stated, int) and stated not in amounts:
                out.append("pet_fee %r cents, cited quote reads %r: %r" % (stated, amounts, quote))
        elif field == "weight_limit" and isinstance(facts.get("weight_limit"), Mapping):
            stated = facts["weight_limit"].get("value")
            if reading.weight_value is not None and stated is not None \
                    and float(reading.weight_value) != float(stated):
                out.append("weight_limit %r, cited quote reads %r: %r" % (stated, reading.weight_value, quote))
        elif field == "pet_count_limit":
            stated = facts.get("pet_count_limit")
            if reading.pet_count_limit is not None and stated is not None \
                    and int(reading.pet_count_limit) != int(stated):
                out.append("pet_count_limit %r, cited quote reads %r: %r" % (stated, reading.pet_count_limit, quote))
        elif field == "pets_allowed" and reading.pets_allowed is not None \
                and facts.get("pets_allowed") is not None and reading.pets_allowed != facts.get("pets_allowed"):
            out.append("pets_allowed %r, cited quote reads %r: %r" % (facts.get("pets_allowed"), reading.pets_allowed, quote))
    return out


def evaluate_policy_record(record: Mapping, identity: Mapping,
                           references: Mapping[Tuple[str, str], Mapping]) -> Verdict:
    """The gate for one pet-friendly policy record."""
    checks: "OrderedDict[str, OrderedDict]" = OrderedDict()
    classes: List[str] = []

    def check(name: str, passed: bool, why: str, cls: str = "") -> None:
        checks[name] = OrderedDict((("pass", bool(passed)), ("why", why)))
        if not passed and cls:
            classes.append(cls)

    key = str(record.get("identity_key") or "")
    name = str(record.get("name") or "")
    entries = [e for e in (record.get("evidence") or ()) if isinstance(e, Mapping)]
    publication = [e for e in entries if e.get("artifact_class") == enums.PUBLICATION_GRADE_EVIDENCE]

    # PROPERTY IDENTITY
    problems: List[str] = []
    if not key or key != str(identity.get("identity_key") or ""):
        problems.append("record identity %r is not the census identity %r" % (key, identity.get("identity_key")))
    try:
        derived = ptf_identity_key(str(identity.get("canonical_name") or name))
    except IdentityKeyError:
        derived = ""
    if derived and key and derived != key:
        problems.append("identity key %r is not the key of %r (%r)" % (key, identity.get("canonical_name"), derived))
    for entry in publication:
        digest = SMP.normalise_sha256(str(entry.get("artifact_sha256") or ""))
        ref = references.get((key, digest))
        if digest and ref is None:
            others = [r for (k, h), r in references.items() if h == digest and k != key]
            if others:
                problems.append("artifact %s is bound to %r" % (digest[:23], others[0].get("identity_key")))
        bound, why = _property_binding(str(entry.get("source_url") or ""), identity)
        if not bound:
            problems.append(why)
    check("PROPERTY_IDENTITY", not problems, "; ".join(problems) or "one identity across record, references and page",
          CLASS_WRONG_PROPERTY if any("property code" in p or "bound to" in p or "page is" in p for p in problems)
          else CLASS_IDENTITY_UNBOUND)

    # SOURCE CLASS
    grades = [EVIDENCE.canonical_source_grade(str(e.get("source_grade") or "")) for e in publication]
    lead_only = [g for g in grades if g not in enums.FIRST_PARTY_GRADES]
    check("SOURCE_CLASS", bool(publication) and not lead_only,
          ("no publication-grade evidence" if not publication else
           "non-first-party grade(s) %s are LEAD ONLY" % sorted(set(lead_only)) if lead_only else
           "publication-grade, first-party (%s)" % sorted(set(grades))),
          CLASS_LEAD_ONLY)

    # SOURCE URL
    bad_urls = [str(e.get("source_url") or "") for e in publication
                if not IR.registrable_domain(str(e.get("source_url") or ""))
                or IR.registrable_domain(str(e.get("source_url") or "")) in IR.NEVER_OFFICIAL_DOMAINS]
    check("SOURCE_URL", bool(publication) and not bad_urls,
          "not a first-party endpoint: %s" % bad_urls[:3] if bad_urls else "first-party endpoint(s)",
          CLASS_NOT_FIRST_PARTY_URL)

    # CAPTURE HASH
    unhashed = [e.get("evidence_ref") for e in publication
                if not SMP.is_sha256(SMP.normalise_sha256(str(e.get("artifact_sha256") or "")))]
    unbound = [e.get("evidence_ref") for e in publication
               if SMP.is_sha256(SMP.normalise_sha256(str(e.get("artifact_sha256") or "")))
               and (key, SMP.normalise_sha256(str(e.get("artifact_sha256") or ""))) not in references]
    check("CAPTURE_HASH", bool(publication) and not unhashed and not unbound,
          ("no page hash on %s" % unhashed[:3] if unhashed else
           "hash not bound to this identity in the package references: %s" % unbound[:3] if unbound else
           "every entry hashes the page and the hash is bound to the identity"),
          CLASS_NO_CAPTURE_HASH)

    # TIMESTAMP
    undated = [e.get("evidence_ref") for e in publication if parse_timestamp(str(e.get("captured_at") or "")) is None]
    check("TIMESTAMP", bool(publication) and not undated,
          "no capture timestamp on %s" % undated[:3] if undated else "every entry is dated",
          CLASS_NO_TIMESTAMP)

    # OPERATIVE QUOTE: the acceptance must be cited by an operative quote.
    acceptance = [e for e in publication if str(e.get("field") or "") in EVIDENCE.coverage_names("pets_allowed")]

    def _context(entry: Mapping) -> str:
        same_page = [str(e.get("quote") or "") for e in publication
                     if e is not entry and e.get("artifact_sha256") == entry.get("artifact_sha256")]
        return " ".join(dict.fromkeys(same_page))

    verdicts = [classify_quote(str(e.get("quote") or ""), kind=KIND_PET_FRIENDLY, context=_context(e))
                for e in acceptance]
    operative = [v for v in verdicts if v[0] == ELIGIBLE]
    if not acceptance:
        check("OPERATIVE_QUOTE", False, "no evidence entry cites pets_allowed", CLASS_NO_QUOTE)
    elif operative:
        check("OPERATIVE_QUOTE", True, operative[0][1])
    else:
        cls, why = verdicts[0]
        check("OPERATIVE_QUOTE", False, why, cls)

    # PARSED FACTS
    uncited = EVIDENCE.unevidenced_facts(record)
    contradictions = _fact_contradictions(record)
    check("PARSED_FACTS", not uncited and not contradictions,
          ("uncited fact(s) %s" % list(uncited) if uncited else
           "; ".join(contradictions) if contradictions else "every fact cited; no cited quote contradicts it"),
          CLASS_FACT_UNCITED if uncited else CLASS_FACT_CONTRADICTED)

    # AUTHORITY STATUS
    status = record.get("verification_state")
    facts = record.get("facts") if isinstance(record.get("facts"), Mapping) else {}
    approval = record.get("approval") if isinstance(record.get("approval"), Mapping) else {}
    reviewed = bool(approval.get("decision") or approval.get("operator")) or bool(record.get("reviewer_id"))
    status_ok = (status is None or status in PUBLISHABLE_POLICY_STATUSES) and facts.get("pets_allowed") is True
    check("AUTHORITY_STATUS", status_ok and reviewed,
          ("status %r is not publishable" % status if not status_ok else
           "no review recorded (approval or reviewer_id)" if not reviewed else
           "publishable status, reviewed"),
          CLASS_STATUS_INVALID)

    eligible = all(c["pass"] for c in checks.values())
    return Verdict((("identity_key", key), ("kind", KIND_PET_FRIENDLY), ("eligible", eligible),
                    ("classification", ELIGIBLE if eligible else classes[0]),
                    ("failed_checks", [n for n, c in checks.items() if not c["pass"]]),
                    ("checks", checks)))


def evaluate_exclusion_record(record: Mapping, identity: Mapping,
                              references: Mapping[Tuple[str, str], Mapping]) -> Verdict:
    """The gate for one verified-no-pets exclusion record."""
    checks: "OrderedDict[str, OrderedDict]" = OrderedDict()
    classes: List[str] = []

    def check(name: str, passed: bool, why: str, cls: str = "") -> None:
        checks[name] = OrderedDict((("pass", bool(passed)), ("why", why)))
        if not passed and cls:
            classes.append(cls)

    name = str(record.get("canonical_name") or "")
    try:
        key = ptf_identity_key(name)
    except IdentityKeyError:
        key = ""
    source_url = str(record.get("source_url") or "")
    digest = SMP.normalise_sha256(str(record.get("source_hash") or ""))

    problems: List[str] = []
    if not key or key != str(identity.get("identity_key") or ""):
        problems.append("exclusion identity %r is not the census identity %r" % (key, identity.get("identity_key")))
    bound, why = _property_binding(source_url, identity)
    if not bound:
        problems.append(why)
    check("PROPERTY_IDENTITY", not problems, "; ".join(problems) or "one identity across record and page",
          CLASS_WRONG_PROPERTY if any("property code" in p or "bound to" in p or "page is" in p for p in problems)
          else CLASS_IDENTITY_UNBOUND)
    grade = EVIDENCE.canonical_source_grade(str(record.get("source_grade") or enums.GRADE_PT1_FIRST_PARTY))
    check("SOURCE_CLASS", grade in enums.FIRST_PARTY_GRADES,
          "grade %r is LEAD ONLY" % grade if grade not in enums.FIRST_PARTY_GRADES else "first-party (%s)" % grade,
          CLASS_LEAD_ONLY)
    domain = IR.registrable_domain(source_url)
    check("SOURCE_URL", bool(domain) and domain not in IR.NEVER_OFFICIAL_DOMAINS,
          "not a first-party endpoint: %r" % source_url if not domain or domain in IR.NEVER_OFFICIAL_DOMAINS
          else "first-party endpoint", CLASS_NOT_FIRST_PARTY_URL)
    check("CAPTURE_HASH", SMP.is_sha256(digest) and (key, digest) in references,
          "no page hash" if not SMP.is_sha256(digest) else
          "hash not bound to this identity in the package references" if (key, digest) not in references
          else "page hashed and bound", CLASS_NO_CAPTURE_HASH)
    check("TIMESTAMP", parse_timestamp(str(record.get("observed_at") or "")) is not None,
          "observed_at %r is not a date" % record.get("observed_at")
          if parse_timestamp(str(record.get("observed_at") or "")) is None else "dated", CLASS_NO_TIMESTAMP)
    cls, why = classify_quote(str(record.get("evidence_quote") or ""), kind=KIND_NO_PETS)
    check("OPERATIVE_QUOTE", cls == ELIGIBLE, why, cls)
    check("PARSED_FACTS", record.get("exclusion_state") == HE.VERIFIED_NO_PETS,
          "exclusion_state %r is not %s" % (record.get("exclusion_state"), HE.VERIFIED_NO_PETS)
          if record.get("exclusion_state") != HE.VERIFIED_NO_PETS else "the record states a refusal",
          CLASS_STATUS_INVALID)
    reviewed = bool(record.get("reviewer_id")) and bool(record.get("reviewed_at"))
    hashes_ok = True
    try:
        hashes_ok = HE.record_hash(record) == record.get("record_hash") \
            and HE.approval_hash(record) == record.get("approval_hash")
    except Exception:
        hashes_ok = False
    check("AUTHORITY_STATUS", reviewed and hashes_ok,
          "no review recorded" if not reviewed else
          "record_hash/approval_hash do not re-derive" if not hashes_ok else "reviewed; hashes re-derive",
          CLASS_STATUS_INVALID)
    eligible = all(c["pass"] for c in checks.values())
    return Verdict((("identity_key", key), ("kind", KIND_NO_PETS), ("eligible", eligible),
                    ("classification", ELIGIBLE if eligible else classes[0]),
                    ("failed_checks", [n for n, c in checks.items() if not c["pass"]]),
                    ("checks", checks)))


def evaluate_package(package: Mapping) -> "OrderedDict[str, Any]":
    """Run the gate over every clean record of a sealed package."""
    identities = {str(r.get("identity_key")): r for r in package.get("identity_records") or ()}
    references = {(str(r.get("identity_key")), str(r.get("artifact_sha256"))): r
                  for r in package.get("evidence_references") or ()}
    verdicts: List[Verdict] = []
    for record in package.get("pet_friendly_records") or ():
        key = str(record.get("identity_key") or "")
        verdicts.append(evaluate_policy_record(record, identities.get(key, {"identity_key": ""}), references))
    for record in package.get("verified_no_pets_records") or ():
        if record.get("exclusion_state") != HE.VERIFIED_NO_PETS:
            continue
        try:
            key = ptf_identity_key(str(record.get("canonical_name") or ""))
        except IdentityKeyError:
            key = ""
        verdicts.append(evaluate_exclusion_record(record, identities.get(key, {"identity_key": ""}), references))
    failed = [v for v in verdicts if not v["eligible"]]
    classes: "OrderedDict[str, int]" = OrderedDict()
    for v in failed:
        classes[v["classification"]] = classes.get(v["classification"], 0) + 1
    return OrderedDict((
        ("records_evaluated", len(verdicts)),
        ("eligible", len(verdicts) - len(failed)),
        ("ineligible", len(failed)),
        ("classes", classes),
        ("passed", not failed),
        ("failures", [OrderedDict((("identity_key", v["identity_key"]), ("kind", v["kind"]),
                                   ("classification", v["classification"]),
                                   ("failed_checks", v["failed_checks"]),
                                   ("why", "; ".join(v["checks"][c]["why"] for c in v["failed_checks"]))))
                      for v in failed]),
    ))


__all__ = [
    "ELIGIBLE", "CHECKS", "KIND_PET_FRIENDLY", "KIND_NO_PETS", "Verdict", "classify_quote",
    "parse_timestamp", "evaluate_policy_record", "evaluate_exclusion_record", "evaluate_package",
    "CLASS_WRONG_PROPERTY", "CLASS_LEAD_ONLY", "CLASS_NOT_FIRST_PARTY_URL", "CLASS_IDENTITY_UNBOUND",
    "CLASS_NO_CAPTURE_HASH", "CLASS_NO_TIMESTAMP", "CLASS_NO_QUOTE", "CLASS_FEE_ONLY",
    "CLASS_SERVICE_ANIMAL_ONLY", "CLASS_AMENITY_CHIP_ONLY", "CLASS_STRUCTURED_NO_PETS_INSUFFICIENT",
    "CLASS_QUOTE_CONTRADICTS", "CLASS_QUOTE_NOT_OPERATIVE", "CLASS_FACT_UNCITED",
    "CLASS_FACT_CONTRADICTED", "CLASS_STATUS_INVALID",
]
