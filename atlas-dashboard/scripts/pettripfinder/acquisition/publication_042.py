"""PTF-MILWAUKEE-PUBLICATION-042 -- flip one flag, and prove it was the only one.

Milwaukee has been founder-approved since 040 and normalized since 041. This
admits it to live inventory in SOURCE. It does not deploy: no bundle leaves the
repository, no hosting is touched, and the published package says so.

WHAT PUBLICATION ACTUALLY IS HERE
----------------------------------
``published: false`` makes ``site_data.load_published_hotel_policy_facts``
return nothing, so the assembler builds no profile for the market however many
records the package holds. Flipping it to true is the whole transition. The
records do not change -- same facts, same evidence, same approvals, same
hashes -- and that is asserted byte for byte rather than assumed.

The seed inventory is written at the same time, because a policy record with
no display row fails the assembler closed. Both are derived from the committed
authority; neither is authored here.

NOTHING IS TAKEN ON TRUST FROM 041
-----------------------------------
041 measured 73 and 27 in a simulation. This re-derives both from the
committed authority and validates every row on its own terms -- schema,
approval, binding, lineage, and that it is not held, excluded, superseded or
unresolved -- before anything is written. A count that was true yesterday is
not evidence about today's repository.

THE MECHANISM IS THE SHARED ONE
--------------------------------
The flip goes through ``publication_037.write``, which is the repository's
publication path, parameterised to name the work order that actually performs
it. A Milwaukee-specific publisher would be a second answer to a settled
question and the first market to diverge from it would do so silently.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder import approval_binding as AB                     # noqa: E402
from scripts.pettripfinder import hotel_exclusions as EX                     # noqa: E402
from scripts.pettripfinder import market_authority as MA                     # noqa: E402
from scripts.pettripfinder import release_contracts as RC                    # noqa: E402
from scripts.pettripfinder.acquisition import approval_rebinding_039 as R39  # noqa: E402
from scripts.pettripfinder.acquisition import authority_build_036 as A36     # noqa: E402
from scripts.pettripfinder.acquisition import closure_038 as C38             # noqa: E402
from scripts.pettripfinder.acquisition import founder_decisions_040 as D40   # noqa: E402
from scripts.pettripfinder.acquisition import founder_review_036 as F36      # noqa: E402
from scripts.pettripfinder.acquisition import normalization_041 as N41       # noqa: E402
from scripts.pettripfinder.acquisition import publication_037 as P37         # noqa: E402
from scripts.pettripfinder.contracts import enums                            # noqa: E402
from scripts.pettripfinder.contracts import policy_schema as SCHEMA          # noqa: E402

WORK_ORDER = "PTF-MILWAUKEE-PUBLICATION-042"
MARKET = "milwaukee-wi"

PKG = F36.PKG / "milwaukee_publication_042"
REPORT = PKG / "milwaukee-publication-042.json"
LIVE_CONTRACT = RC.RELEASE_CONTRACTS_DIR / ("%s.json" % MARKET)

NEWLINE = chr(10)

EXPECTED_PET_FRIENDLY = 73
EXPECTED_NO_PETS = 27

#: Dispositions that must never own a pet-friendly profile. Named rather than
#: derived by subtraction: subtraction quietly admits any bucket added later.
FORBIDDEN_DISPOSITIONS = (
    C38.SCHEMA_UNREPRESENTABLE, C38.INSUFFICIENT_EVIDENCE,
    C38.ACCESS_UNRESOLVED, C38.POLICY_NOT_FOUND, C38.HELD_REVIEW,
    C38.IDENTITY_UNRESOLVED, C38.SOURCE_CONFLICT,
)


#: The two strings the repository uses for "a founder approved this".
#:
#: 036 writes APPROVED_AFTER_CURRENT_REVIEW and 040 writes APPROVED -- the same
#: act, spelled two ways, because 040 did not reuse 036's constant. Read from
#: the modules rather than retyped, so this check cannot drift from either.
#: Harmless today and worth fixing in a work order that is allowed to touch
#: approval blocks; this one is not, and a publication pass that quietly
#: rewrote founder approvals to tidy a string would be a worse defect than the
#: string. Recorded as carried debt in the run report.
APPROVAL_MARKERS = (A36.APPROVAL_DECISION, "APPROVED")


class PublicationError(RuntimeError):
    """Raised rather than publishing something that did not check out."""


def _authority() -> Dict:
    return json.loads(A36.AUTHORITY.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# Phase 1 -- the start state, mechanically.
# --------------------------------------------------------------------------- #

def start_state() -> Dict:
    authority = _authority()
    exclusions = MA.load_market_exclusions(MARKET)
    recon = C38.reconciliation()
    projection = N41.projection_summary()
    ledger = json.loads(C38.LEDGER.read_text(encoding="utf-8"))
    prepared = json.loads(N41.FRESH_CONTRACT.read_text(encoding="utf-8"))
    return {
        "branch": F36._git("rev-parse", "--abbrev-ref", "HEAD"),
        "head": F36._git("rev-parse", "HEAD"),
        "working_tree_entries": [line for line in
                                 F36._git("status", "--porcelain").splitlines()
                                 if line.strip()],
        "pet_friendly": len(authority["hotels"]),
        "verified_no_pets": len(exclusions),
        "total_authority": len(authority["hotels"]) + len(exclusions),
        "active_eligible": recon["active_eligible"],
        "census_total": recon["census_total"],
        "closure_problems": recon["problems"],
        "pending_projection": sum(
            count for name, count in projection["by_classification"].items()
            if name != N41.SEMANTICS_IDENTICAL),
        "requires_founder_review": projection["requires_founder_review"],
        "published": authority["published"],
        "deployed": bool(ledger["deployed"]),
        "stale_037_refused": _stale_contract_is_refused(),
        "prepared_041_status": prepared["status"],
        "prepared_041_grants_deployment":
            prepared["deployment_authorization"]["grants_deployment"],
    }


def _stale_contract_is_refused() -> bool:
    """Whether 037's package still cannot be loaded, even if placed live."""
    staging = Path(tempfile.mkdtemp(prefix="ptf-042-stale-"))
    real = RC.RELEASE_CONTRACTS_DIR
    try:
        shutil.copy2(P37.PREPARED_CONTRACT, staging / ("%s.json" % MARKET))
        RC.RELEASE_CONTRACTS_DIR = staging
        RC.load_contract(MARKET)
        return False
    except RC.ReleaseContractError:
        return True
    finally:
        RC.RELEASE_CONTRACTS_DIR = real
        shutil.rmtree(staging, ignore_errors=True)


def assert_start_state(*, expect_published: bool = False) -> Dict:
    state = start_state()
    problems = []
    if state["pet_friendly"] != EXPECTED_PET_FRIENDLY:
        problems.append("authority holds %d pet-friendly records, expected %d"
                        % (state["pet_friendly"], EXPECTED_PET_FRIENDLY))
    if state["verified_no_pets"] != EXPECTED_NO_PETS:
        problems.append("exclusions hold %d rows, expected %d"
                        % (state["verified_no_pets"], EXPECTED_NO_PETS))
    if state["active_eligible"] != 133 or state["census_total"] != 147:
        problems.append("closure is %d/%d, expected 133/147"
                        % (state["active_eligible"], state["census_total"]))
    if state["closure_problems"]:
        problems.append("; ".join(state["closure_problems"]))
    if state["pending_projection"]:
        problems.append("%d row(s) still pending projection"
                        % state["pending_projection"])
    if state["requires_founder_review"]:
        problems.append("rows await founder re-review: %s"
                        % state["requires_founder_review"])
    if state["published"] is not expect_published:
        problems.append("published is %s, expected %s"
                        % (state["published"], expect_published))
    if state["deployed"]:
        problems.append("the market reports itself deployed")
    if not state["stale_037_refused"]:
        problems.append("037's superseded package can still be loaded")
    if problems:
        raise PublicationError("START STATE: " + "; ".join(problems))
    return state


# --------------------------------------------------------------------------- #
# Phase 2 -- re-derive and validate every publishable row.
# --------------------------------------------------------------------------- #

def validate_pet_friendly() -> Tuple[List[Dict], List[Dict]]:
    """(valid, rejected). Every check on its own row, none inferred."""
    authority = _authority()
    store = R39.store_rows()
    closure = {row["identity_key"]: row for row in C38.active_rows()}
    exclusions = {row["normalized_name"]
                  for row in MA.load_market_exclusions(MARKET)}
    held = set(P37.held_identities())
    decided = dict(P37.founder_decisions())
    rebound = R39.rebound_index()

    valid: List[Dict] = []
    rejected: List[Dict] = []
    for record in authority["hotels"]:
        key = record["identity_key"]
        why: List[str] = []

        issues = SCHEMA.validate_record(record)
        if issues:
            why.append("schema 1.2: %s" % "; ".join(str(i) for i in issues))
        if record.get("schema_version") != enums.POLICY_SCHEMA_VERSION:
            why.append("schema_version is %r" % record.get("schema_version"))

        approval = record.get("approval") or {}
        if not approval.get("operator"):
            why.append("no founder approval")
        if approval.get("decision") not in APPROVAL_MARKERS:
            why.append("approval decision is %r" % approval.get("decision"))
        if decided.get(key) != "APPROVE":
            why.append("no APPROVE in any founder ledger (%s)"
                       % decided.get(key, "no decision"))

        # The binding, under the contract 039 introduced. A record approved in
        # 040 carries its own semantic hash; a 036 record binds through the
        # store row, either by its original hashes or by 039's rebinding.
        contract = approval.get("binding_contract")
        if contract == AB.BINDING_CONTRACT_VERSION:
            if approval.get("semantic_hash") != \
                    approval.get("reviewed_semantic_hash"):
                why.append("semantic hash does not match the reviewed one")
        else:
            row = store.get(key)
            if row is None:
                why.append("no store row to bind the 036 approval to")
            else:
                original = (approval.get("reviewed_record_hash")
                            == P37.record_hash(row)
                            if hasattr(P37, "record_hash") else None)
                entry = rebound.get(key)
                semantic_ok = bool(entry) and entry[0] == AB.semantic_hash(row)
                if original is False and not semantic_ok:
                    why.append("neither binding holds for this record")

        if not record.get("evidence"):
            why.append("no evidence entries")
        if not record.get("source_url"):
            why.append("no source URL")
        if not record.get("verified_at"):
            why.append("no observed_at/verified_at")

        if key in held:
            why.append("the founder holds this identity")
        if EX.normalize_name(record["name"]) in exclusions:
            why.append("this identity is in the exclusion registry")
        disposition = (closure.get(key) or {}).get("disposition")
        if disposition != C38.AUTHORITY_PET_FRIENDLY:
            why.append("closure calls this %s" % disposition)

        (rejected if why else valid).append(
            {"identity_key": key, "name": record["name"], "why": why})
    return valid, rejected


def validate_exclusions() -> Tuple[List[Dict], List[Dict]]:
    """Every refusal stays a refusal and can never own a profile."""
    published = {record["identity_key"] for record in _authority()["hotels"]}
    names = {record["name"] for record in _authority()["hotels"]}
    valid: List[Dict] = []
    rejected: List[Dict] = []
    for row in MA.load_market_exclusions(MARKET):
        why: List[str] = []
        if row.get("exclusion_state") != "VERIFIED_NO_PETS":
            why.append("exclusion_state is %r" % row.get("exclusion_state"))
        if not row.get("evidence_quote", "").strip():
            why.append("no quoted refusal")
        if not row.get("reviewer_id"):
            why.append("no reviewer")
        if row["canonical_name"] in names:
            why.append("this refusal also holds a pet-friendly record")
        if row["normalized_name"] in {EX.normalize_name(name)
                                      for name in names}:
            why.append("a pet-friendly record normalizes to the same name")
        if row.get("market_id") != MARKET:
            why.append("belongs to %r" % row.get("market_id"))
        (rejected if why else valid).append(
            {"canonical_name": row["canonical_name"], "why": why})
    return valid, rejected


def assert_publication_input() -> Dict:
    valid, rejected = validate_pet_friendly()
    ex_valid, ex_rejected = validate_exclusions()
    problems = []
    if rejected:
        problems.append("pet-friendly rows failed validation: %s"
                        % "; ".join("%s (%s)" % (row["name"],
                                                 ", ".join(row["why"]))
                                    for row in rejected))
    if ex_rejected:
        problems.append("exclusion rows failed validation: %s"
                        % "; ".join(row["canonical_name"]
                                    for row in ex_rejected))
    if len(valid) != EXPECTED_PET_FRIENDLY:
        problems.append("%d valid pet-friendly rows, expected %d"
                        % (len(valid), EXPECTED_PET_FRIENDLY))
    if len(ex_valid) != EXPECTED_NO_PETS:
        problems.append("%d valid exclusions, expected %d"
                        % (len(ex_valid), EXPECTED_NO_PETS))
    if problems:
        raise PublicationError("PUBLICATION INPUT: " + "; ".join(problems))
    return {"pet_friendly_valid": len(valid),
            "verified_no_pets_valid": len(ex_valid),
            "pet_friendly_rejected": rejected,
            "exclusions_rejected": ex_rejected}


# --------------------------------------------------------------------------- #
# Phase 3 -- what must never reach publication.
# --------------------------------------------------------------------------- #

def leakage_report() -> Dict:
    published = {record["identity_key"] for record in _authority()["hotels"]}
    closure = C38.active_rows()
    held = set(P37.held_identities())
    by_disposition: Dict[str, List[str]] = {}
    for row in closure:
        if row["disposition"] in FORBIDDEN_DISPOSITIONS \
                and row["identity_key"] in published:
            by_disposition.setdefault(row["disposition"], []).append(
                row["identity_key"])
    return {
        "held_identities": sorted(held),
        "held_in_publication": sorted(held & published),
        "forbidden_disposition_leaks": by_disposition,
        "exclusion_leaks": sorted(
            {row["normalized_name"]
             for row in MA.load_market_exclusions(MARKET)}
            & {EX.normalize_name(record["name"])
               for record in _authority()["hotels"]}),
    }


def assert_no_leakage() -> Dict:
    report = leakage_report()
    problems = []
    if report["held_in_publication"]:
        problems.append("held identities in publication: %s"
                        % report["held_in_publication"])
    if report["forbidden_disposition_leaks"]:
        problems.append("non-authority dispositions in publication: %s"
                        % report["forbidden_disposition_leaks"])
    if report["exclusion_leaks"]:
        problems.append("refusals in publication: %s"
                        % report["exclusion_leaks"])
    if problems:
        raise PublicationError("LEAKAGE: " + "; ".join(problems))
    return report


# --------------------------------------------------------------------------- #
# Phases 4 and 5 -- the two rows this market learned the most from.
# --------------------------------------------------------------------------- #

SAINT_KATE = "saint kate the arts hotel"
JEFFERSON_PAIR = ("Home2 Suites by Hilton Milwaukee Downtown",
                  "Tru by Hilton Milwaukee Downtown")


def saint_kate_report() -> Dict:
    record = next((r for r in _authority()["hotels"]
                   if r["identity_key"] == SAINT_KATE), None)
    if record is None:
        raise PublicationError("Saint Kate is not in the authority")
    facts = record["facts"]
    block = R39.store_rows()[SAINT_KATE]
    return {
        "in_authority": True,
        "pets_allowed": facts.get("pets_allowed"),
        "pet_fee": facts.get("pet_fee"),
        "pet_count_limit": facts.get("pet_count_limit"),
        "weight_limit_absent": "weight_limit" not in facts,
        "species_absent": "species" not in facts,
        "is_refusal": bool(block.get("is_refusal")),
        "withheld_fields": block.get("withheld_fields"),
        "approval_contract": record["approval"].get("binding_contract"),
        "approved_by": record["approval"].get("operator"),
        "approving_work_order":
            record["approval"]["decision_source"]["work_order"],
        # The place restriction is a fact about WHERE, and the reader must
        # still refuse to read it as a refusal of whether.
        "place_restriction_still_reads_as_a_place":
            _place_restriction_holds(),
    }


def _place_restriction_holds() -> bool:
    from scripts.pettripfinder.brightdata import policy_reading as PR
    welcome = PR.to_extraction(PR.parse(
        "Yes, this is a pet-friendly hotel, with a maximum of two pets "
        "allowed. Pets are not allowed in the shopping galleria.",
        strategy=WORK_ORDER), location=WORK_ORDER)
    room = PR.to_extraction(PR.parse(
        "Pets are not allowed in guest rooms.", strategy=WORK_ORDER),
        location=WORK_ORDER)
    return (welcome.extraction.get("pets_allowed") is True
            and room.extraction.get("pets_allowed") is False)


def jefferson_report() -> Dict:
    from scripts.pettripfinder import publication_guard as PG
    from scripts.pettripfinder.hotel_exclusions import address_key
    records = {r["name"]: r for r in _authority()["hotels"]}
    present = [name for name in JEFFERSON_PAIR if name in records]
    keys = {address_key(records[name]["address"], records[name]["postal_code"])
            for name in present}
    reviewed = {tuple(sorted(group)) for group in PG.distinct_entity_groups()}
    return {
        "both_in_authority": sorted(present) == sorted(JEFFERSON_PAIR),
        "shared_address_key": sorted(keys),
        "resolution_reviewed": tuple(sorted(JEFFERSON_PAIR)) in reviewed,
        "distinct_identity_keys": sorted(
            records[name]["identity_key"] for name in present),
    }


# --------------------------------------------------------------------------- #
# Phases 6 and 7 -- the live contract and the flip.
# --------------------------------------------------------------------------- #

def prepared_matches_current() -> Tuple[bool, List[str]]:
    """Whether 041's prepared contract still describes today's repository."""
    prepared = json.loads(N41.FRESH_CONTRACT.read_text(encoding="utf-8"))
    current = N41.fresh_contract()
    drift = [key for key in ("policy_package", "public_surface", "routes",
                             "reconciliation")
             if json.dumps(prepared.get(key), sort_keys=True, default=str)
             != json.dumps(current.get(key), sort_keys=True, default=str)]
    return (not drift), drift


def records_are_unchanged_since_041() -> bool:
    """Whether the RECORDS 041 prepared against are byte-identical to today's.

    The contract's ``expected_sha256`` covers the whole published document,
    which includes a publication block naming the work order that flips the
    flag -- so 042 changing that block moves the hash without touching a
    single approved record. That is a difference worth stating precisely
    rather than waving at, and this is the check that separates the two.
    """
    current, _a = P37.published_document(
        work_order=WORK_ORDER, ledgers=[F36.LEDGER.name, D40.LEDGER.name])
    prepared, _b = P37.published_document()
    return json.dumps(current["hotels"], sort_keys=True, ensure_ascii=False)         == json.dumps(prepared["hotels"], sort_keys=True, ensure_ascii=False)


def live_contract() -> Dict:
    """Today's contract: the market's own skeleton, every number re-derived.

    The SHAPE comes from 037's prepared document -- the canonical block, the
    publish rules, the gate list, the forbidden tokens, the census pointer --
    because that shape is the release architecture's, not 037's, and every
    other market's contract has it. Every VALUE that describes the market is
    replaced from ``release_contracts.derive_authority`` reading today's
    committed state, so nothing stale survives into a live document.

    That is not reuse of the stale artifact. The stale artifact itself stays
    refused by content hash; what is borrowed is a schema, and re-typing a
    schema from memory is how a market ends up with a contract that gates the
    wrong things.
    """
    if not records_are_unchanged_since_041():
        raise PublicationError(
            "a record moved between 041's preparation and now; publication "
            "may change a flag and nothing else")

    skeleton = json.loads(P37.PREPARED_CONTRACT.read_text(encoding="utf-8"))
    derived = RC.derive_authority(MARKET)
    doc = OrderedDict(skeleton)

    doc["contract_id"] = "pettripfinder-milwaukee-wi-release/2.1"
    doc["release_name_prefix"] = "prod-042-milwaukee"
    doc["description"] = (
        "Deterministic release-gate contract for the PetTripFinder Greater "
        "Milwaukee market, derived from the committed authority at "
        "%s. Every number below is computed from this market's own state by "
        "release_contracts.derive_authority; none is inherited from the "
        "superseded 037 preparation, whose document remains refused by "
        "content hash." % WORK_ORDER)
    doc["status"] = "LIVE"
    doc["status_note"] = (
        "Live: this contract gates the assembly of a PUBLISHED market. It "
        "grants no deployment -- publication is a state of the source and "
        "deployment is a separate act nobody has performed.")

    doc["deployment_authorization"] = OrderedDict([
        ("grants_deployment", False),
        ("asserts_market_complete", False),
        ("means", "A passing contract means this market's assembled package "
                  "is STRUCTURALLY deployable: its authority files agree, its "
                  "routes match its reviewed inventory, no held identity "
                  "leaks and every gate holds. It is not a deployment "
                  "authorization, and %s deployed nothing." % WORK_ORDER),
    ])

    doc["provenance"] = OrderedDict([
        ("authority_work_orders", [A36.WORK_ORDER, D40.WORK_ORDER]),
        ("decision_ledgers", [F36.LEDGER.name, D40.LEDGER.name]),
        ("binding_contract", AB.BINDING_CONTRACT_VERSION),
        ("normalization_work_order", N41.WORK_ORDER),
        ("publication_work_order", WORK_ORDER),
        ("held_identities", sorted(P37.held_identities())),
        ("held_note",
         "Held rows reach no publication set. Hyatt Regency because a price "
         "is not permission; Knickerbocker and The Iron Horse because the "
         "identity gate declined their policy subpages and the founder would "
         "not bypass it by hand."),
        ("supersedes", OrderedDict([
            ("contract_id", skeleton.get("contract_id", "")),
            ("path", P37.PREPARED_CONTRACT.relative_to(REPO).as_posix()),
            ("note", "structure borrowed, every value re-derived; the "
                     "document itself remains refused by content hash"),
        ])),
        ("precursor", OrderedDict([
            ("path", N41.FRESH_CONTRACT.relative_to(REPO).as_posix()),
            ("reused_verbatim", prepared_matches_current()[0]),
            ("fields_that_moved", prepared_matches_current()[1]),
            ("why", "042 stamps the publishing work order and both decision "
                    "ledgers into the published document, which moves the "
                    "package hash the contract pins. No approved record "
                    "moved, and that is asserted separately."),
        ])),
    ])

    package = OrderedDict(skeleton.get("policy_package") or {})
    package["path"] = derived.policy_package_path
    package["expected_sha256"] = derived.policy_package_sha256
    package["expected_schema_version"] = derived.policy_package_schema_version
    package["expected_record_count"] = derived.policy_package_record_count
    package["identity_authority"] = True
    doc["policy_package"] = package

    surface = OrderedDict(skeleton.get("public_surface") or {})
    surface["seed_hotel_rows"] = derived.seed_hotel_rows
    surface["public_hotel_profile_count"] = derived.published_hotel_profiles
    surface["excluded_public_profile_count"] = derived.excluded_public_profiles
    doc["public_surface"] = surface

    routes = OrderedDict(skeleton.get("routes") or {})
    routes["market_slug"] = derived.market_slug
    routes["route_mode"] = derived.route_mode
    routes["hotel_route_count"] = derived.hotel_route_count
    routes["published_corridor_route_count"] = derived.corridor_route_count
    doc["routes"] = routes

    doc["reconciliation"] = OrderedDict([
        ("confirmed_identities", derived.confirmed_identities),
        ("published_pet_friendly", derived.published_hotel_profiles),
        ("verified_no_pets", derived.verified_no_pets),
        ("resolved", derived.resolved),
        ("unresolved", derived.unresolved),
        ("note", "verified_no_pets counts ONLY VERIFIED_NO_PETS records this "
                 "market owns in the generated exclusion registry. unresolved "
                 "is UNKNOWN, never negative evidence: a failed capture "
                 "answers nothing."),
    ])

    census = OrderedDict(skeleton.get("identity_census") or {})
    if census:
        census["expected_count"] = derived.confirmed_identities
        doc["identity_census"] = census

    # SHARED sections come from a market whose contract is already live, not
    # from 037's skeleton. They are shared on purpose -- the suite asserts they
    # are byte-identical across markets -- and 037's copy had drifted: its
    # publish note was an older, shorter wording. A section that is supposed to
    # be the same everywhere and quietly is not is a section nobody maintains.
    doc.update(_shared_sections())
    doc.pop("supersedes", None)
    return doc


#: Sections every market's contract must state identically.
SHARED_SECTIONS = ("publish", "canonical", "forbidden_output_tokens",
                   "minimum_release_gates")


def _shared_sections() -> Dict:
    reference = next((market for market in RC.available_market_ids()
                      if market != MARKET), "")
    if not reference:
        raise PublicationError(
            "no other market has a live contract to take the shared sections "
            "from; they may not be authored here")
    other = json.loads(
        RC.contract_path(reference).read_text(encoding="utf-8-sig"))
    return {name: other[name] for name in SHARED_SECTIONS if name in other}


def assert_contract_agrees(contract: Optional[Mapping] = None) -> List[str]:
    """The repository's own cross-check, run before the document is written."""
    contract = dict(contract or live_contract())
    disagreements = RC.contract_disagreements(
        contract, RC.derive_authority(MARKET))
    if disagreements:
        raise PublicationError("RELEASE CONTRACT: " + "; ".join(disagreements))
    return disagreements


def publish(apply: bool = False) -> Dict:
    """The one authorized state transition, with everything checked first."""
    assert_start_state(expect_published=False)
    assert_publication_input()
    assert_no_leakage()
    if not records_are_unchanged_since_041():
        raise PublicationError(
            "a record moved since 041 prepared this market; publication may "
            "change a flag and nothing else")

    result = P37.write(apply=apply, work_order=WORK_ORDER,
                       ledgers=[F36.LEDGER.name, D40.LEDGER.name])
    if apply:
        # Written only after the repository's own checker agrees with it. A
        # contract placed live and THEN found wrong has already gated a build.
        contract = live_contract()
        assert_contract_agrees(contract)
        LIVE_CONTRACT.parent.mkdir(parents=True, exist_ok=True)
        LIVE_CONTRACT.write_text(
            json.dumps(contract, indent=1, ensure_ascii=False) + NEWLINE,
            encoding="utf-8")
        result["live_contract"] = LIVE_CONTRACT.relative_to(REPO).as_posix()
        result["contract_disagreements"] = RC.verify_contract(MARKET)
    return result


def contract_verification() -> Dict:
    """The repository's own contract checker, over every market."""
    return {market: RC.verify_contract(market)
            for market in RC.available_market_ids()}


# --------------------------------------------------------------------------- #
# Phase 8 and 11 -- the real build, twice.
# --------------------------------------------------------------------------- #

def build_site(times: int = 2, root: str = "") -> Dict:
    """The production assembler over the COMMITTED published state.

    No substitution and no in-memory inventory: whatever is on disk is what
    builds. That is the difference between this and 041's simulation, and it
    is the only reason the numbers here can be believed.
    """
    from scripts.pettripfinder.assemble_production_site import assemble

    base = Path(root) if root else Path(chr(67) + ":/t/ptf042")
    shutil.rmtree(base, ignore_errors=True)
    base.mkdir(parents=True, exist_ok=True)
    try:
        runs = [assemble(output=str(base / ("run%d" % index)))
                for index in range(times)]
        first = runs[0]
        return OrderedDict([
            ("markets", list(first["market_fragments_included"])),
            ("milwaukee_included", MARKET in first["market_fragments_included"]),
            ("total_html_pages", first["total_html_pages"]),
            ("total_files", first["total_files"]),
            ("sitemap_route_count", first["sitemap_route_count"]),
            ("broken_links", first["broken_links"]),
            ("collision_count", first["collision_count"]),
            ("global_shadowing_count", first["global_shadowing_count"]),
            ("canonical_violations", first["canonical_violations"]),
            ("bundle_sha256_each", [run["bundle_sha256"] for run in runs]),
            ("deterministic",
             len({run["bundle_sha256"] for run in runs}) == 1),
            ("gates", OrderedDict((name, gate["pass"])
                                  for name, gate in first["gates"].items())),
            ("gates_failing", [name for name, gate in first["gates"].items()
                               if not gate["pass"]]),
            ("all_gates_pass", first["all_gates_pass"]),
            ("deployment_authorized", first["deployment_authorized"]),
        ])
    finally:
        shutil.rmtree(base, ignore_errors=True)


def market_routes() -> Dict:
    """Milwaukee's own routes, from the manifest builder."""
    from scripts.pettripfinder.build_market_manifest import build_package
    package = build_package(MARKET)
    return {
        "published_pet_friendly": package.published_pet_friendly_count,
        "hotel_routes": len(package.hotel_routes),
        "corridor_routes": len(package.corridor_routes),
        "corridor_unassigned": list(package.corridor_unassigned_hotels),
        "verified_no_pets": package.verified_no_pets_count,
        "unresolved": package.unresolved_count,
    }


# --------------------------------------------------------------------------- #
# Reporting.
# --------------------------------------------------------------------------- #

def report(build: Optional[Mapping] = None) -> Dict:
    authority = _authority()
    recon = C38.reconciliation()
    return OrderedDict([
        ("schema", "ptf-milwaukee-publication/2.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("published_in_source", authority["published"]),
        ("deployed", False),
        ("deployment_note",
         "No bundle left the repository. Publication is a state of the "
         "source; deployment is a separate act and nobody performed it."),
        ("provider_calls", 0),
        ("cost_usd", 0.0),
        ("carried_debt", OrderedDict([
            ("approval_decision_vocabulary",
             "036 stamps APPROVED_AFTER_CURRENT_REVIEW and 040 stamps "
             "APPROVED for the same act. Both are accepted here and neither "
             "is rewritten: a publication pass that edited founder approval "
             "blocks to tidy a string would be a worse defect than the "
             "string. A later work order that may touch approvals should "
             "settle on one constant."),
        ])),
        ("authority", OrderedDict([
            ("pet_friendly", len(authority["hotels"])),
            ("verified_no_pets", len(MA.load_market_exclusions(MARKET))),
            ("binding_contract", AB.BINDING_CONTRACT_VERSION),
            ("decision_ledgers",
             authority.get("publication", {}).get("decision_ledgers")),
        ])),
        ("input_validation", assert_publication_input()),
        ("leakage", leakage_report()),
        ("saint_kate", saint_kate_report()),
        ("jefferson_dual_brand", jefferson_report()),
        ("routes", market_routes()),
        ("closure", OrderedDict([
            ("active_eligible", recon["active_eligible"]),
            ("census_total", recon["census_total"]),
            ("by_disposition", recon["by_disposition"]),
            ("problems", recon["problems"]),
        ])),
        ("live_contract", LIVE_CONTRACT.relative_to(REPO).as_posix()),
        ("prepared_041_precursor_reused_verbatim",
         prepared_matches_current()[0]),
        ("prepared_041_fields_that_moved", prepared_matches_current()[1]),
        ("records_unchanged_since_041", records_are_unchanged_since_041()),
        ("contract_verification", contract_verification()),
        ("build", dict(build) if build else None),
    ])


def write_report(build: Optional[Mapping] = None) -> Dict:
    PKG.mkdir(parents=True, exist_ok=True)
    doc = report(build)
    REPORT.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + NEWLINE,
                      encoding="utf-8")
    return doc


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=WORK_ORDER)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args(argv)
    if args.preflight:
        print(json.dumps(assert_start_state(), indent=2, default=str))
    if args.validate:
        print(json.dumps({"input": assert_publication_input(),
                          "leakage": assert_no_leakage(),
                          "saint_kate": saint_kate_report(),
                          "jefferson": jefferson_report()},
                         indent=2, default=str))
    if args.dry_run:
        print(json.dumps(publish(apply=False), indent=2, default=str))
    if args.apply:
        print(json.dumps(publish(apply=True), indent=2, default=str))
    if args.build:
        print(json.dumps(build_site(), indent=2, default=str))
    if args.report:
        print(json.dumps(write_report(build_site())["authority"], indent=2,
                         default=str))
    return 0


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(main())
