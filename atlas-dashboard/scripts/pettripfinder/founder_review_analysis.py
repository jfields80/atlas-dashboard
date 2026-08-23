"""Review every founder-review candidate individually, and propose one disposition each.

    python scripts/pettripfinder/founder_review_analysis.py \
      --packet launch_packages/pettripfinder/st_louis_mo_founder_review_packet_002.json \
      --census launch_packages/pettripfinder/identity_census/st-louis-mo.json \
      --reviewer "Claude (operator)" --out <analysis.json>

WHAT THIS IS, AND WHAT IT IS NOT
--------------------------------
It is a REVIEW: every candidate is put through the same battery of checks, and
each comes out with exactly one proposed disposition, the findings behind it,
and -- where the disposition needs one -- a required correction or a next action.

It is NOT an approval, and it does not write one. ``founder_decision``,
``founder_reviewer_id`` and ``founder_reviewed_at`` stay empty in the packet.
The packet's own instructions say to set the reviewer id to "your own identifier
-- never an operator's on their behalf", and PTF-POLICY-SCHEMA-MIGRATION-001's
Phase F is the reason that sentence is there: twenty-six approvals were once
written under a founder's name for rows the founder had never seen. An
attestation needs the human, not the field. So this module proposes; a person
disposes, and the proposal is attributed to whoever ran it.

THE DISPOSITION LADDER, IN ORDER
--------------------------------
Rungs are tried top-down and the first that fires wins, because a row can trip
several and the most cautious answer has to survive.

1. HOLD -- the record cannot safely enter authority AT ALL. Reserved for our own
   gates refusing it: a membrane verdict that is not VALID means the observation
   is about the wrong property or is malformed, and no amount of correcting the
   facts changes that.
2. HOLD -- the allowance itself is unstated. A source that prices a pet without
   ever saying pets are welcome leaves ``pets_allowed`` withheld as SOURCE_SILENT.
   Reading an allowance out of a price is an inference, and this codebase does
   not make it; a founder may, once, as policy.
3. APPROVE_WITH_CHANGE -- the facts stand but something in the record would
   mislead a guest if published as it is.
4. APPROVE_VERIFIED_NO_PETS / APPROVE_PET_FRIENDLY -- nothing to correct.

WHAT A "CHANGE" IS ALLOWED TO BE
--------------------------------
A correction may only REMOVE something unsupported or REPLACE a value with one
the evidence already states. It may never add a fact the source does not carry.
The two classes this found in St. Louis are both removals:

* a service-animal sentence that has swallowed the pet terms preceding it, so
  the record states that service animals cost $40 a night and are capped at 20
  pounds. PTF-CHOICE-READER-AND-ROUTE-CLOSURE-005 established the rule -- a term
  INSIDE the service-animal statement caps SERVICE ANIMALS -- and publishing one
  of these is a guest-visible, ADA-adjacent misstatement.
* a canonical name that is a bare brand word ("Hampton", "Courtyard"), which the
  census admits as a valid identity key and which would put a directory entry
  called "Hampton" in front of a reader. The property's own page states the full
  name, so the replacement is quoted, not invented.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import market_routing as MR  # noqa: E402

SCHEMA = "ptf-founder-review-analysis/1.0"

APPROVE_PET_FRIENDLY = "APPROVE_PET_FRIENDLY"
APPROVE_VERIFIED_NO_PETS = "APPROVE_VERIFIED_NO_PETS"
APPROVE_WITH_CHANGE = "APPROVE_WITH_CHANGE"
HOLD = "HOLD"

DISPOSITIONS: Tuple[str, ...] = (APPROVE_PET_FRIENDLY, APPROVE_VERIFIED_NO_PETS,
                                 APPROVE_WITH_CHANGE, HOLD)

#: A service-animal sentence should say what happens to SERVICE ANIMALS. These
#: patterns are pet terms that have no business inside one; when they appear
#: BEFORE the sentence's own opening they are text the locator swallowed.
_PET_TERM = re.compile(
    r"\b(\d+\s*(?:lb|lbs|pound|pounds)|per\s+night|per\s+pet|per\s+room|"
    r"limit\s+of|\d+\.\d\d\s*USD|\$\s*\d|breed)", re.IGNORECASE)
_SERVICE_OPENER = re.compile(r"(service|assistance)\s+animal", re.IGNORECASE)

#: Names that identify a chain rather than a building.
_BARE_BRAND = re.compile(
    r"^(hampton|courtyard|days inn|doubletree|wingate at wyndham|comfort inn|"
    r"radisson|super 8|motel 6|holiday inn|quality inn|sleep inn|econo lodge|"
    r"red roof inn|la quinta|travelodge|baymont|microtel|candlewood suites|"
    r"residence inn|springhill suites|fairfield inn|hilton garden inn)$",
    re.IGNORECASE)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def _digits(value: str) -> str:
    only = re.sub(r"\D", "", value or "")
    return only[-10:] if len(only) >= 10 else ""


def _street_number(value: str) -> str:
    match = re.match(r"\s*(\d+)", value or "")
    return match.group(1) if match else ""


# --------------------------------------------------------------------------- #
# Findings
# --------------------------------------------------------------------------- #

def _finding(code: str, detail: str, *, severity: str) -> Dict:
    return OrderedDict((("code", code), ("severity", severity),
                        ("detail", detail)))


#: Chain qualifiers a census name or a page title may carry that say nothing
#: about WHICH building this is. Stripped before names are compared.
_CHAIN_SUFFIX = re.compile(
    r"\b(by|at)\s+(ihg|wyndham|marriott|hilton|choice|radisson|sonesta)\b|"
    r"\b(tapestry|autograph|curio|tribute|signature)\s+collection\b",
    re.IGNORECASE)


def names_agree(census_name: str, page_name: str) -> bool:
    """Do these two strings name the same building?

    Three normalisations, each earned by a row in this market:

    * HTML ENTITIES are decoded. Seven IHG rows were refused as the wrong
      property because the page said ``Holiday Inn Express &amp; Suites`` and
      the census said ``&``. That is an encoding difference, not a hotel.
    * CHAIN SUFFIXES are stripped. ``... Edwardsville by IHG`` and
      ``... Edwardsville`` are one hotel; "by IHG" identifies an owner.
    * CONTAINMENT counts, not just equality, because the page name is often a
      document title: ``Extended Stay Hotel in Arnold, MO | WoodSpring Suites
      St Louis Arnold`` contains the census name exactly.

    This does NOT re-open the membrane's M10 decision. M10 refuses a row
    outright and this function cannot un-refuse it; it exists so a reviewer can
    see whether the NAME agrees when the address and telephone are unavailable,
    which is the WoodSpring case -- no address on the page, no telephone, and a
    title that states the property in full.
    """
    import html as _html
    left = set(_norm(_CHAIN_SUFFIX.sub(" ", _html.unescape(census_name or ""))).split())
    right = set(_norm(_CHAIN_SUFFIX.sub(" ", _html.unescape(page_name or ""))).split())
    if not left or not right:
        return False
    return left <= right or right <= left


def corroborating_identity(candidate: Mapping, census_row: Optional[Mapping]
                           ) -> Dict:
    """What binds this page to this building, across every available signal.

    Three signals, and the question asked of them is "does ANY of you agree",
    not "do all of you". A page carries what it carries: Marriott prints a
    property code, Wyndham prints a telephone, WoodSpring prints neither and
    states the property in its title. Demanding a fixed pair would hold rows
    whose identity is not actually in doubt -- which is what a first version of
    this rule did to four of them.

    Zero agreeing signals is the blocking case, and it is the honest one: if
    nothing on the page ties it to this census row, nobody should publish a fact
    from it under this hotel's name.
    """
    check = candidate.get("semantic_approval", {}).get("projection", {}).get(
        "identity_check", {}) or {}
    census_row = census_row or {}
    page_phone, census_phone = (_digits(check.get("phone_on_page", "")),
                                _digits(census_row.get("phone", "")))
    page_street = _street_number(check.get("address_on_page", ""))
    census_street = _street_number(census_row.get("address", ""))
    phone_ok = bool(page_phone and page_phone == census_phone)
    street_ok = bool(page_street and page_street == census_street)
    name_ok = names_agree(census_row.get("canonical_name", "")
                          or candidate.get("canonical_name", ""),
                          check.get("name_on_page", ""))
    return OrderedDict((
        ("name_on_page", check.get("name_on_page", "")),
        ("address_on_page", check.get("address_on_page", "")),
        ("name_agrees", name_ok),
        ("phone_matches", phone_ok),
        ("street_number_matches", street_ok),
        ("property_code_on_page", check.get("property_code", "")),
        ("signals_agreeing", sum([name_ok, phone_ok, street_ok])),
        ("signals_available",
         sum([bool(check.get("name_on_page")),
              bool(page_phone and census_phone),
              bool(page_street and census_street)])),
    ))


def service_animal_contamination(text: str) -> str:
    """The pet terms a service-animal sentence has swallowed, or "".

    Only text BEFORE the sentence's own opening counts. A statement that says
    "service animals are exempt from the $40 fee" legitimately names a fee and
    must not be flagged; one that reads "$40 per night, 20 pounds max Service
    animals are permitted" has had the property's pet terms glued onto its front.
    """
    if not text:
        return ""
    opener = _SERVICE_OPENER.search(text)
    if not opener or opener.start() == 0:
        return ""
    prefix = text[:opener.start()]
    return prefix.strip() if _PET_TERM.search(prefix) else ""


def service_animal_correction(text: str) -> str:
    """The same sentence with the swallowed prefix removed."""
    opener = _SERVICE_OPENER.search(text or "")
    return text[opener.start():].strip() if opener else (text or "")


def examine(candidate: Mapping, census_row: Optional[Mapping]) -> Dict:
    """Every check, run over one candidate. Returns findings and corrections."""
    findings: List[Dict] = []
    changes: List[Dict] = []
    facts = candidate.get("proposed_facts") or {}
    withheld = candidate.get("withheld_fields") or {}
    membrane = candidate.get("membrane") or {}
    readiness = candidate.get("readiness") or {}
    grade = candidate.get("publication_grade") or {}
    identity = corroborating_identity(candidate, census_row)

    # -- gates our own contracts already ran --------------------------------
    if grade.get("verdict") != "PUBLICATION_GRADE_CONFIRMED":
        findings.append(_finding(
            "NOT_PUBLICATION_GRADE",
            "the evidence contract refuses this capture: %s"
            % "; ".join(grade.get("reasons") or ["no reason recorded"]),
            severity="BLOCKING"))
    if membrane.get("verdict") != "VALID":
        findings.append(_finding(
            "MEMBRANE_REFUSED",
            "%s (%s): %s" % (membrane.get("verdict"), membrane.get("rule") or "-",
                             (membrane.get("detail") or "")[:400]),
            severity="BLOCKING"))

    # -- identity ------------------------------------------------------------
    agreeing = identity["signals_agreeing"]
    which = ", ".join(k for k, v in (("name", identity["name_agrees"]),
                                     ("street number", identity["street_number_matches"]),
                                     ("telephone", identity["phone_matches"])) if v)
    if agreeing >= 2:
        findings.append(_finding(
            "IDENTITY_CORROBORATED",
            "%d independent signals on the page match the census row: %s"
            % (agreeing, which), severity="INFO"))
    elif agreeing == 1:
        findings.append(_finding(
            "IDENTITY_SINGLY_CORROBORATED",
            "one signal on the page matches the census row (%s); %d of 3 were "
            "available at all" % (which, identity["signals_available"]),
            severity="WARN"))
    else:
        findings.append(_finding(
            "IDENTITY_UNCORROBORATED",
            "nothing on the page ties it to this census row: name, street "
            "number and telephone all fail to agree",
            severity="BLOCKING"))

    if _BARE_BRAND.match((candidate.get("canonical_name") or "").strip()):
        page_name = identity["name_on_page"]
        if page_name:
            changes.append(OrderedDict((
                ("field", "canonical_name"),
                ("from", candidate.get("canonical_name")),
                ("to", page_name),
                ("why", "the census name is a bare chain word and would publish "
                        "a directory entry that names no building; the "
                        "property's own page states the full name"),
                ("evidence", "identity_check.name_on_page"))))
        else:
            findings.append(_finding(
                "BARE_BRAND_NAME_NO_REPLACEMENT",
                "the canonical name is a bare chain word and the page offers no "
                "replacement", severity="BLOCKING"))

    # -- source binding ------------------------------------------------------
    shape = MR.classify_url_shape(candidate.get("source_url", ""))
    if shape not in MR.ROUTABLE_SHAPES:
        findings.append(_finding(
            "SOURCE_NOT_PROPERTY_SPECIFIC",
            "the source URL classifies as %s; a policy fact may only be read "
            "from a page about this one property" % shape,
            severity="BLOCKING"))

    # -- the allowance itself -----------------------------------------------
    pets_allowed = facts.get("pets_allowed")
    if "pets_allowed" not in facts:
        findings.append(_finding(
            "ALLOWANCE_NOT_STATED",
            "pets_allowed is withheld as %s: the source prices or limits a pet "
            "without ever stating that pets are accepted. Reading an allowance "
            "out of a price is an inference this codebase does not make."
            % withheld.get("pets_allowed", "unstated"),
            severity="BLOCKING"))

    # -- service-animal contamination ---------------------------------------
    statement = facts.get("service_animal_exception") or ""
    swallowed = service_animal_contamination(statement)
    if swallowed:
        changes.append(OrderedDict((
            ("field", "service_animal_exception"),
            ("from", statement),
            ("to", service_animal_correction(statement)),
            ("why", "the property's pet terms have been glued onto the front of "
                    "the service-animal sentence. Published as it stands the "
                    "record states that SERVICE ANIMALS carry these terms, "
                    "which is a guest-visible and ADA-adjacent misstatement. "
                    "Removal only -- the pet terms remain on their own fields."),
            ("removed_text", swallowed))))

    # -- fact-level coherence ------------------------------------------------
    if pets_allowed is False:
        for field in ("pet_fee", "fee_basis", "fee_tiers", "weight_limit",
                      "pet_count_limit", "species_allowed", "pet_deposit"):
            if field in facts:
                findings.append(_finding(
                    "NO_PETS_ROW_CARRIES_PET_TERM",
                    "pets_allowed is false yet %s is present (%r); the source "
                    "contradicts itself or the reader merged two blocks"
                    % (field, facts[field]), severity="BLOCKING"))
    if pets_allowed is True:
        if "pet_fee" in facts and "fee_currency" not in facts:
            findings.append(_finding(
                "FEE_WITHOUT_CURRENCY",
                "a fee amount with no currency cannot be published",
                severity="BLOCKING"))
        if "pet_fee" in facts and "fee_basis" not in facts:
            findings.append(_finding(
                "FEE_BASIS_WITHHELD" if "fee_basis" in withheld
                else "FEE_BASIS_MISSING",
                "the fee has no stated basis; it is %s"
                % ("correctly withheld as %s and renders as 'Not stated'"
                   % withheld.get("fee_basis")
                   if "fee_basis" in withheld else
                   "absent from both the facts and the withheld register"),
                severity="INFO" if "fee_basis" in withheld else "BLOCKING"))
        if "pet_deposit" in facts and "pet_fee" in facts:
            findings.append(_finding(
                "DEPOSIT_AND_FEE",
                "the record carries both a deposit and a fee; each is cited to "
                "its own quote and they are distinct charges",
                severity="INFO"))
        if "fee_tiers" in facts and "pet_fee" in facts:
            findings.append(_finding(
                "TIERS_AND_FLAT_FEE",
                "the record carries both a tiered schedule and a flat fee; one "
                "of them is a misread", severity="BLOCKING"))

    for field, reason in sorted(withheld.items()):
        findings.append(_finding(
            "WITHHELD_%s" % field.upper(),
            "%s is withheld (%s) and must render as 'Not stated'"
            % (field, reason), severity="INFO"))

    return OrderedDict((("findings", findings), ("changes", changes),
                        ("identity", identity)))


# --------------------------------------------------------------------------- #
# Disposition
# --------------------------------------------------------------------------- #

def dispose(candidate: Mapping, review: Mapping) -> Tuple[str, List[str], str]:
    """``(disposition, reasons, next_action)`` -- exactly one, first rung wins."""
    facts = candidate.get("proposed_facts") or {}
    findings = review["findings"]
    changes = review["changes"]
    codes = {f["code"] for f in findings}
    blocking = [f for f in findings if f["severity"] == "BLOCKING"]

    if "MEMBRANE_REFUSED" in codes:
        membrane = candidate.get("membrane") or {}
        corroborated = review["identity"]["signals_agreeing"] >= 2
        if membrane.get("verdict") == "REJECT_WRONG_PROPERTY":
            return (HOLD,
                    ["the membrane refuses this observation as being about "
                     "another property (M10)",
                     "independent signals agreeing with the census row: %d of 3"
                     % review["identity"]["signals_agreeing"]],
                    ("decode HTML entities and strip chain suffixes in the M10 "
                     "name comparison, then re-derive this observation offline "
                     "from its persisted block; the binding is already "
                     "corroborated on street number and telephone"
                     if corroborated else
                     "resolve the identity by hand: the name, street number and "
                     "telephone do not agree, so which building this page "
                     "describes is genuinely unsettled"))
        return (HOLD,
                ["the membrane refuses this observation as malformed: %s"
                 % (membrane.get("detail") or "")[:200]],
                "amend the closed FLAG_CODES vocabulary in "
                "policy/policy_observation.py to carry the structured-pricing "
                "codes the reader emits, as a versioned contract change, then "
                "re-derive; the pricing evidence itself is intact")

    if "ALLOWANCE_NOT_STATED" in codes:
        return (HOLD,
                ["the source prices or limits a pet but never states that pets "
                 "are accepted; pets_allowed is withheld as SOURCE_SILENT",
                 "the machine will not read an allowance out of a price"],
                "a single founder policy decision covering every row in this "
                "class: does a stated per-pet price constitute a stated "
                "allowance? If yes, these rows can be approved from their "
                "existing quotes with no re-fetch")

    if blocking:
        return (HOLD,
                [f["detail"] for f in blocking],
                "resolve the blocking finding above before this row is "
                "considered again")

    if changes:
        kinds = sorted({c["field"] for c in changes})
        return (APPROVE_WITH_CHANGE,
                ["the facts are supported by the cited evidence",
                 "the record requires a correction to: %s" % ", ".join(kinds)],
                "")

    if facts.get("pets_allowed") is False:
        return (APPROVE_VERIFIED_NO_PETS,
                ["the property's own page states pets are not accepted",
                 "identity corroborated; publication-grade confirmed"],
                "")
    return (APPROVE_PET_FRIENDLY,
            ["the property's own page states pets are accepted",
             "identity corroborated; publication-grade confirmed"],
            "")


def review_all(packet: Mapping, census: Mapping, *, reviewer: str) -> Dict:
    rows = {h["identity_key"]: h for h in census.get("hotels") or ()}
    reviewed: List[Dict] = []
    for candidate in packet.get("candidates") or ():
        detail = examine(candidate, rows.get(candidate["identity_key"]))
        disposition, reasons, next_action = dispose(candidate, detail)
        reviewed.append(OrderedDict((
            ("identity_key", candidate["identity_key"]),
            ("canonical_name", candidate["canonical_name"]),
            ("brand", candidate.get("brand", "")),
            ("corridor", candidate.get("corridor", "")),
            ("source_url", candidate.get("source_url", "")),
            ("machine_recommendation", candidate.get("recommendation", "")),
            ("proposed_disposition", disposition),
            ("agrees_with_machine",
             (disposition == APPROVE_PET_FRIENDLY
              and candidate.get("recommendation") == "RECOMMEND_AUTHORITY_PET_FRIENDLY")
             or (disposition == APPROVE_VERIFIED_NO_PETS
                 and candidate.get("recommendation") == "RECOMMEND_AUTHORITY_VERIFIED_NO_PETS")),
            ("reasons", reasons),
            ("required_changes", detail["changes"]),
            ("next_action", next_action),
            ("identity_corroboration", detail["identity"]),
            ("findings", detail["findings"]),
            ("proposed_facts", candidate.get("proposed_facts") or {}),
            ("withheld_fields", candidate.get("withheld_fields") or {}),
            ("readiness_state", (candidate.get("readiness") or {}).get("state", "")),
            ("membrane_verdict", (candidate.get("membrane") or {}).get("verdict", "")),
            ("semantic_hash",
             (candidate.get("semantic_approval") or {}).get("semantic_hash", "")),
            ("reviewed_by", reviewer),
            ("review_is_not_an_approval",
             "A proposed disposition is a review, not an attestation. Only a "
             "founder decision creates authority; founder_decision, "
             "founder_reviewer_id and founder_reviewed_at remain empty in the "
             "packet this was derived from."),
        )))
    reviewed.sort(key=lambda r: r["identity_key"])
    counts = Counter(r["proposed_disposition"] for r in reviewed)
    return OrderedDict((
        ("schema", SCHEMA),
        ("what_this_is",
         "Every founder-review candidate examined individually and given one "
         "proposed disposition. Nothing here is an approval and nothing here "
         "creates authority."),
        ("market_id", packet.get("market_id", "")),
        ("work_order", "PTF-ST-LOUIS-FOUNDER-REVIEW-003"),
        ("derived_from", packet.get("work_order", "")),
        ("reviewed_by", reviewer),
        ("reviewed_at", _now()),
        ("approval_vocabulary", packet.get("approval_vocabulary", "")),
        ("candidates_in_packet", packet.get("count", 0)),
        ("reviewed", len(reviewed)),
        ("each_reviewed_exactly_once",
         len({r["identity_key"] for r in reviewed}) == len(reviewed)
         == packet.get("count", 0)),
        ("disposition_counts", OrderedDict(sorted(counts.items()))),
        ("changes_required",
         sum(1 for r in reviewed if r["required_changes"])),
        ("disagreements_with_the_machine",
         [r["identity_key"] for r in reviewed
          if not r["agrees_with_machine"]]),
        ("rows", reviewed),
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--packet", required=True)
    parser.add_argument("--census", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--reviewer", required=True,
                        help="who ran this review -- never a founder's "
                             "identifier on their behalf")
    args = parser.parse_args(argv)

    packet = json.loads(Path(args.packet).read_text(encoding="utf-8"))
    census = json.loads(Path(args.census).read_text(encoding="utf-8"))
    document = review_all(packet, census, reviewer=args.reviewer)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print("reviewed        : %d of %d" % (document["reviewed"],
                                          document["candidates_in_packet"]))
    print("each exactly once: %s" % document["each_reviewed_exactly_once"])
    print("dispositions    : %s" % dict(document["disposition_counts"]))
    print("changes required: %d" % document["changes_required"])
    print("written         : %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
