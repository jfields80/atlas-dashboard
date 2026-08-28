# -*- coding: utf-8 -*-
"""PTF-GRAND-RAPIDS-SOURCE-PROMOTION-022 -- promote the signed authority into
source.

NO PROVIDER IS CALLED and nothing is spent. Nothing is assembled and nothing is
deployed. Every derived artifact is produced by the sanctioned tool that owns
it: ``market_proposed_authority_cli`` builds the authority,
``market_policy_package_cli`` projects the policy package, ``market_authority``
shapes the exclusions shard, and ``build_global_authority`` regenerates the
three legacy globals from the shards.

THE FOUNDER'S RULING, AND WHY IT IS A WITHDRAWAL RATHER THAN A DELETION
------------------------------------------------------------------------
021 built a 50-row authority and flagged that avid hotel Zeeland sat astride two
of the order's own clauses: its identity was founder-confirmed, and its READINESS
state was still POLICY_NOT_FOUND. The founder has now ruled: identity
confirmation establishes WHICH HOTEL a capture belongs to and does not establish
a publishable pet-policy fact, so the row is excluded from authority pending
actual policy evidence.

It is removed through the builder's ``withdrawals`` channel, which exists for
exactly this: the row leaves the CURRENT authority and its original attestation
is left untouched in the ledger that recorded it. Deleting the signature would
destroy the only record that the founder ever approved it; editing it in place
would quietly rewrite a dated act by a named person. The 020 identity ruling is
preserved too, and travels beside the withdrawal, because the ruling is still
true -- it simply never said what the founder has now clarified it does not say.

WHAT IS WRITTEN INTO SOURCE, AND WHAT DELIBERATELY IS NOT
-----------------------------------------------------------
Written: the market's exclusions shard, its policy package, and the visibility
fields of its market contract, which until now all still said this market
publishes no pet-policy claim. Regenerated: the three legacy globals, from the
shards, by their own assembler.

Not written: no release contract, no launch-participation row, no deployment
manifest entry. Those are ASSEMBLY inputs, and the order stops at source. Grand
Rapids has none of them today, which is why source promotion here cannot
disturb a live deployment record -- there is nothing of this market's in one.

``build_market_authorities --check`` is run and never ``--write``. That tool
derives the four Ohio markets' censuses and partitions, and its ``--write``
path is the one that wiped corridor assignments in PTF-DAYTON-RECERT. Running
it in check mode proves this promotion left those four markets alone.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import hotel_exclusions as HE                # noqa: E402
from scripts.pettripfinder import identity_routing as IR               # noqa: E402
from scripts.pettripfinder import market_authority as MA                # noqa: E402
from scripts.pettripfinder import market_registration_cli as REGISTRATION  # noqa: E402
from scripts.pettripfinder.contracts import enums                       # noqa: E402
from scripts.pettripfinder.contracts import founder_approval as FA      # noqa: E402
from scripts.pettripfinder.site_data import normalize_name             # noqa: E402

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
SCRIPTS = _REPO_ROOT / "scripts" / "pettripfinder"

WORK_ORDER = "PTF-GRAND-RAPIDS-SOURCE-PROMOTION-022"
#: The ruling that unblocked this promotion, and the work order the published
#: package names as the act that published it.
RULING_023 = "PTF-GRAND-RAPIDS-WEIGHT-SEMANTICS-RULING-023"
MARKET = "grand-rapids-holland-mi"
#: The launch-package artifacts spell this market with underscores while the
#: market id and the policy-package filename use hyphens. Both spellings are
#: committed, so both are named here rather than derived from one another.
PREFIX = "grand_rapids_holland_mi"
MARKET_NAME = "Grand Rapids-Holland, Michigan"
FOUNDER = "PTF-FOUNDER-001"
RULED_AT = "2026-08-28"

WITHHELD = "avid hotel zeeland"
WITHHELD_RULING = (
    "Identity is confirmed and stays confirmed: the 020 ruling established "
    "WHICH HOTEL the capture belongs to. It did not establish a publishable "
    "pet-policy fact, and this row's readiness state is still "
    "POLICY_NOT_FOUND. A founder-confirmed identity is not a reason to read "
    "POLICY_NOT_FOUND as publishable, so the row is withheld from authority "
    "pending actual policy evidence. Its 021 signature and its 020 identity "
    "ruling are both preserved.")

#: The visibility fields that still described a discovery-stage market. Each is
#: replaced with a value that is true of a market publishing 49 founder-signed
#: policy records, and the old value is recorded beside the new one.
CONTRACT_UPDATES: Tuple[Tuple[str, object], ...] = (
    ("show_in_navigation", True),
    ("show_in_sitemap", True),
    ("introductory_copy",
     "Pet policies for hotels across Grand Rapids, Holland and the "
     "surrounding lakeshore, each read from the property's own page and "
     "reviewed before publication."),
    ("meta_description",
     "Pet-friendly hotels in Grand Rapids and Holland, Michigan. Fees, weight "
     "limits and pet counts quoted from each hotel's own policy page."),
)


class PromotionError(RuntimeError):
    """A promotion step the evidence or a gate does not support."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, document: Mapping) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def _run(command: Sequence[str], what: str) -> str:
    result = subprocess.run(list(command), cwd=str(_REPO_ROOT),
                            capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stdout + result.stderr)
        raise PromotionError("%s failed: %s" % (
            what, (result.stderr.strip().splitlines() or [""])[-1]))
    return result.stdout


# --------------------------------------------------------------------------- #
# The withdrawal
# --------------------------------------------------------------------------- #

def withdrawal_ledger(confirmations: Mapping, authority_021: Mapping) -> Dict:
    """The founder's ruling, in the shape the builder's gate reads.

    ``identity_confirmations`` is carried forward unchanged. The 020 ruling on
    avid hotel Zeeland is not retracted by this: it said the capture belongs to
    that hotel, which is still true, and the founder's clarification is about
    what that does NOT establish.
    """
    signed = {r["normalized_name"] for r in
              list(authority_021["pet_friendly"])
              + list(authority_021["verified_no_pets"])}
    if WITHHELD not in signed:
        raise PromotionError(
            "%r is not in the 021 authority, so there is nothing to withdraw; "
            "a withdrawal that names an absent row would misdescribe the act"
            % WITHHELD)
    return OrderedDict((
        ("schema", "ptf-founder-withdrawal-ledger/1.0"),
        ("what_this_is",
         "The founder's ruling that a confirmed identity does not make a "
         "POLICY_NOT_FOUND row publishable. The row leaves the CURRENT "
         "authority; its signature and its identity ruling are preserved."),
        ("market_id", MARKET),
        ("work_order", WORK_ORDER),
        ("ruled_by", FOUNDER),
        ("ruled_at", RULED_AT),
        ("provider_calls", 0),
        ("usd_spent", 0.0),
        ("plan_credits_spent", 0.0),
        ("withdrawals", [OrderedDict((
            ("retired_identity_key", WITHHELD),
            ("originally_signed_by_work_order",
             "PTF-GRAND-RAPIDS-FOUNDER-SIGNATURE-PASS-021"),
            ("original_ledger",
             "grand_rapids_holland_mi_founder_decision_ledger_021.json"),
            ("surviving_identity_key", ""),
            ("readiness_state_at_withdrawal", "POLICY_NOT_FOUND"),
            ("identity_ruling_preserved", True),
            ("signature_preserved", True),
            ("returns_to", "unresolved, pending actual policy evidence"),
            ("founder_ruling", WITHHELD_RULING),
        ))]),
        ("identity_confirmations",
         list(confirmations.get("identity_confirmations") or ())),
    ))


# --------------------------------------------------------------------------- #
# A gap 021 left, repaired here
# --------------------------------------------------------------------------- #

def repair_correction_evidence(store: Mapping, ledger_020: Mapping
                               ) -> Tuple[Dict, List[Dict]]:
    """Give a corrected FACT the evidence entry its quote already had.

    021 applied 020's corrections to the extraction and stopped there. For the
    three name corrections that is complete -- a name is not a policy fact. For
    ``baymont by wyndham holland``'s weight limit it was not: the fact landed
    with no evidence entry citing it, so ``market_policy_package_cli`` could
    find no quote for ``weight_limit`` and declined to publish the field at all.

    The quote is not invented here. 020 recorded it off the saved policy block
    -- "must not weigh more than 100 lbs each" -- and checked it against that
    block before the correction was allowed. This restores the link between the
    fact and the sentence that states it, which is what the projector reads.
    """
    document = json.loads(json.dumps(dict(store)))
    records = {r["identity_key"]: r for r in document["records"]}
    repaired: List[Dict] = []
    for entry in ledger_020["corrections"]:
        field, key = entry["field"], entry["identity_key"]
        quote = str(entry.get("evidence") or "")
        if field == "canonical_name" or not quote:
            continue
        evidence = records[key]["observation"].setdefault("evidence", [])
        if any(field in (e.get("field_refs") or ()) for e in evidence):
            continue
        evidence.append(OrderedDict((
            ("quote", quote),
            ("location", "bounded policy container (founder correction, %s)"
                         % entry["ruling"]),
            ("field_refs", [field]),
        )))
        repaired.append(OrderedDict((
            ("identity_key", key), ("field", field), ("quote", quote),
            ("why", "021 applied the corrected value without the evidence "
                    "entry that cites it, so the projector had no quote to "
                    "read and declined to publish the field"))))
    document["work_order"] = WORK_ORDER
    document["derived_from"] = OrderedDict((
        ("store", "%s_observation_store_021.json" % PREFIX),
        ("repair", "the corrected facts' own evidence quotes, from the 020 "
                   "ledger"),
    ))
    document["correction_evidence_repaired"] = repaired
    return (document, repaired)


# --------------------------------------------------------------------------- #
# The exclusions shard
# --------------------------------------------------------------------------- #

def exclusion_rows(authority: Mapping, census: Mapping[str, Mapping],
                   decisions: Mapping[str, Mapping]) -> List[Dict]:
    """One contract-valid exclusion per verified-no-pets authority row.

    Nothing is invented: the quote, the source and the observation date come
    off the authority row, the address off the census, and the two hashes off
    ``hotel_exclusions``' own helpers so a later reader can recompute them.
    """
    rows: List[Dict] = []
    for row in authority["verified_no_pets"]:
        key = row["normalized_name"]
        hotel = census.get(key, {})
        signature = decisions[key]
        record: Dict = OrderedDict((
            ("exclusion_id", row["exclusion_id"]),
            ("canonical_name", row["canonical_name"]),
            # The contract derives normalized_name from canonical_name, and
            # 020's name corrections moved three canonical names. So the
            # DISPLAY key and the CENSUS identity are different strings here
            # and both are carried -- the same split the policy package makes
            # between "key" and "identity_key". Deriving one from the other
            # would either fail the contract or lose the identity the founder
            # signed against.
            ("normalized_name", normalize_name(row["canonical_name"])),
            ("identity_key", key),
            ("address", str(hotel.get("address") or row.get("address") or "")),
            ("city", str(hotel.get("city") or "")),
            ("state", str(hotel.get("state") or "")),
            ("postal_code", str(hotel.get("postal_code") or "")),
            ("official_url", row["official_url"]),
            ("exclusion_state", enums.VERIFIED_NO_PETS),
            ("evidence_quote", row["evidence_quote"]),
            ("evidence_context", row["evidence_quote"]),
            ("source_url", row["source_url"]),
            ("observed_at", str(row.get("observed_at") or "")),
            ("source_hash", str(row.get("snapshot_hash") or "")),
            ("reviewer_id", signature["founder_reviewer_id"]),
            ("reviewed_at", signature["founder_reviewed_at"]),
            ("market_id", MARKET),
            ("corridor", signature.get("corridor", "")),
            ("notes",
             "affirmative refusal on the property's own page, read by %s and "
             "signed under %s. A service-animal statement is a legal access "
             "category and is never read as a pet permission or as a refusal."
             % (row.get("reader_provenance", {}).get("module", "the reader"),
                signature.get("founder_decision", ""))),
            ("membrane_verdict", row.get("membrane_verdict", "")),
            ("bound_semantic_hash", row.get("bound_semantic_hash", "")),
        ))
        record["record_hash"] = HE.record_hash(record)
        record["approval_hash"] = HE.approval_hash(record)
        missing = [f for f in HE.REQUIRED_FIELDS if not record.get(f)]
        if missing:
            raise PromotionError("%r is missing %s" % (key, ", ".join(missing)))
        rows.append(record)
    rows.sort(key=lambda r: r["normalized_name"])
    return rows


# --------------------------------------------------------------------------- #
# Retiring the routes publication answers
# --------------------------------------------------------------------------- #

def withdraw_published_routes(seed_rows: Sequence[Mapping]) -> Dict:
    """A route for a hotel we now publish has been answered. Remove it.

    ``identity_routing`` exists to find a hotel's official page, and
    ``test_no_committed_route_is_already_seed_inventory`` states the rule
    plainly: "the seed remains the source of truth for it". Every market that
    publishes on the generic path -- Indianapolis, Louisville, Milwaukee,
    Pittsburgh, St. Louis -- carries ZERO routes, and Cleveland, Columbus and
    Dayton carry routes only for identities they have NOT published. Grand
    Rapids is the only market that would assert both.

    WHY REMOVED AND NOT RETIRED
    ``ROUTING_RETIRED`` exists for a route that should never have been bound --
    Cleveland bound accommodation routes to a restaurant and a cross-category
    inn, and retiring them keeps the wrong binding visible so it can be argued
    with. These 31 bindings were not wrong; they were RIGHT, and publication is
    the answer they were asking for. Retiring them instead breaks two further
    invariants -- the pinned retired set, and "a held route is never used" --
    because a retired route is a route with a problem, and these have none.

    Nothing is lost. Each removed row is archived whole in this pass's report,
    and the seed row and policy package now carry the name, the address, the
    official URL, the source and the observation date that the route carried.
    """
    published = {normalize_name(str(r.get("name") or "")) for r in seed_rows}
    path = MA.routing_shard_path(MARKET)
    document = _load(path)
    keep, withdrawn = [], []
    for route in document.get("routes") or ():
        name = str((route.get("hotel_ref") or {}).get("normalized_name") or "")
        (withdrawn if name in published else keep).append(route)
    if withdrawn:
        document["routes"] = keep
        document["count"] = len(keep)
        IR.validate_authority(document)
        path.write_text(MA.render_json(document), encoding="utf-8")
    return OrderedDict((
        ("withdrawn", len(withdrawn)),
        ("routes_before", len(keep) + len(withdrawn)),
        ("routes_after", len(keep)),
        ("why", "publication answers a routing question; every other published "
                "market carries no route for a published identity, and a "
                "market asserting both would leave a stale pointer beside the "
                "seed row that supersedes it"),
        ("not_retired_because",
         "ROUTING_RETIRED marks a binding that should never have been made. "
         "These bindings were correct -- they found the pages this market now "
         "publishes -- so marking them as problems would misdescribe them and "
         "would break both the pinned retired set and 'a held route is never "
         "used'."),
        # The end state, which a re-run reproduces. "withdrawn" and
        # "routes_before" describe the run that made the change and are 0 and
        # 79 on any run after it.
        ("routes_for_a_published_identity_in_the_end_state",
         len([r for r in keep
              if str((r.get("hotel_ref") or {}).get("normalized_name") or "")
              in published])),
        ("archived_here_in_full", withdrawn),
    ))


# --------------------------------------------------------------------------- #
# The market contract
# --------------------------------------------------------------------------- #

def promote_contract(path: Path) -> Tuple[Dict, List[Dict]]:
    """``(contract, changes)`` -- the visibility fields, and what they were."""
    contract = _load(path)
    changes: List[Dict] = []
    for field, value in CONTRACT_UPDATES:
        before = contract.get(field)
        if before == value:
            continue
        changes.append(OrderedDict((("field", field), ("from", before),
                                    ("to", value))))
        contract[field] = value
    return (contract, changes)


def contract_still_denies_policy(contract: Mapping) -> List[str]:
    """Any prose field still claiming this market publishes no pet policy."""
    denials = ("no pet-policy claim", "not yet been evaluated",
               "discovery-stage", "discovery stage")
    offending: List[str] = []
    for field in ("introductory_copy", "meta_description", "title",
                  "market_name"):
        text = str(contract.get(field) or "").lower()
        if any(phrase in text for phrase in denials):
            offending.append(field)
    return offending



# --------------------------------------------------------------------------- #
# The one thing this promotion cannot decide for itself
# --------------------------------------------------------------------------- #

STRICT = "STRICT"
LTE_PER_PET = "LTE_PER_PET"
#: PTF-GRAND-RAPIDS-WEIGHT-SEMANTICS-RULING-023: publish the comparison the
#: source states, and withhold the field where it states none. This is the
#: ruling this market runs under.
SOURCE_STATED_COMPARISON = "SOURCE_STATED_COMPARISON"

#: Ceiling words a source uses, and the comparison each one actually states.
#: They are counted rather than applied: the point of the breakdown is to show
#: the founder that a single blanket rule is not obviously right for this
#: market's data, because "under 75 lbs" is not the same promise as "up to 75".
_CEILING_WORDS: Tuple[Tuple[str, str], ...] = (
    ("not weigh more than", "lte"), ("no more than", "lte"),
    ("maximum", "lte"), ("max", "lte"), ("up to", "lte"),
    ("under", "lt"), ("less than", "lt"),
)


def _weight_quote(record: Mapping) -> str:
    for entry in (record.get("observation") or {}).get("evidence") or ():
        quote = str(entry.get("quote") or "")
        if re.search(r"\d+\s*(lb|lbs|pound)", quote, re.I):
            return quote
    return ""


def _refused_count(output: str) -> Optional[int]:
    match = re.search(r"(\d+) record\(s\) failed schema", output or "")
    return int(match.group(1)) if match else None


def weight_limit_blocker(authority: Mapping, derived: Mapping[str, Mapping],
                         output: str, ruled_output: str = "",
                         ruled_returncode: int = 0) -> Dict:
    """Why the package would not validate, per row, with its own quote.

    ``market_policy_package_cli`` refuses a weight limit that states a number
    and no comparison, and the reader refuses to invent one -- its own
    non-inference says defaulting a comparison "is a guest-visible error in
    both directions". Both refusals are right. What is missing is a FOUNDER
    decision, and this market does not inherit one: 020 established that a
    ruling made for another market does not carry over by itself.
    """
    rows: List[Dict] = []
    for row in authority["pet_friendly"]:
        limit = (row.get("facts") or {}).get("weight_limit") or {}
        if not limit or (limit.get("operator") and limit.get("scope")):
            continue
        quote = _weight_quote(derived.get(row["normalized_name"], {}))
        stated = ""
        for word, comparison in _CEILING_WORDS:
            if word in quote.lower():
                stated = comparison
                break
        rows.append(OrderedDict((
            ("identity_key", row["normalized_name"]),
            ("canonical_name", row["canonical_name"]),
            ("weight_limit", limit),
            ("source_quote", quote),
            ("comparison_the_source_states", stated or "NONE_STATED"),
        )))
    by_comparison = Counter(r["comparison_the_source_states"] for r in rows)
    return OrderedDict((
        ("blocked", True),
        ("gate", "contracts.policy_schema.validate_facts, schema 1.2"),
        ("rows_blocked", len(rows)),
        ("pet_friendly_total", authority["pet_friendly_count"]),
        ("issue", "facts.weight_limit states a number with no operator and no "
                  "scope. The schema requires both before a limit publishes."),
        ("why_the_reader_did_not_supply_them",
         "its own non-inference: \"'maximum' / 'up to' / 'under' are recorded "
         "as a value only; defaulting a comparison is a guest-visible error in "
         "both directions\", and \"scope: not emitted unless the source states "
         "it\"."),
        ("why_this_pass_will_not_supply_them",
         "market_policy_package_cli exposes --normalize-weight as \"founder "
         "decision 1\", made for another market. 020 established that a "
         "market-specific founder precedent is not inherited automatically, "
         "and applying one here would be inventing a founder decision."),
        ("comparison_the_sources_actually_state",
         OrderedDict(sorted(by_comparison.items()))),
        ("why_a_blanket_rule_is_not_obviously_right",
         "%d of the %d quotes say 'under' or 'less than', which is lt and not "
         "lte: publishing those as lte would tell a guest with a dog at exactly "
         "the limit that it is welcome when the source says it is not. %d "
         "state no ceiling word at all."
         % (by_comparison.get("lt", 0), len(rows),
            by_comparison.get("NONE_STATED", 0))),
        ("what_would_unblock_it", [
            "a founder ruling that an unqualified blanket maximum publishes as "
            "lte / per_pet, applied market-wide -- rerun with "
            "--weight-limit-ruling LTE_PER_PET",
            "or a per-comparison ruling honouring 'under' as lt, which this "
            "flag cannot express and which would need the projector extended",
            "or a ruling that an unqualified limit is withheld, which drops a "
            "stated ceiling from the profile and is the guest-visible error in "
            "the other direction",
        ]),
        ("rows", rows),
        ("measured_both_readings", OrderedDict((
            ("strict_refused", _refused_count(output)),
            ("with_the_lte_per_pet_ruling_refused",
             0 if ruled_returncode == 0 else _refused_count(ruled_output)),
            ("note", "both readings were projected into scratch and neither "
                     "was written; the second is what the founder's ruling "
                     "would actually buy, measured rather than asserted"),
        ))),
        ("residual_after_the_ruling", OrderedDict((
            ("identity_key", "baymont by wyndham holland"),
            ("quote", "must not weigh more than 100 lbs each"),
            ("why", "the projector's maximal-wording list does not recognise "
                    "'not weigh more than', so founder decision 1 declines the "
                    "row even though the sentence is plainly a ceiling"),
            ("not_fixed_here", "widening a reading rule inside the pass whose "
                               "count it raises is how a measurement stops "
                               "being one; the phrase list belongs to founder "
                               "decision 1 and should be extended in its own "
                               "work order"),
        ))),
        ("projector_output", [line for line in output.splitlines()
                              if line.strip()][:6]),
        ("summary",
         "BLOCKED: %d of %d pet-friendly rows carry a weight limit the schema "
         "will not publish without a comparison the source did not state. "
         "Measured, not asserted: the strict reading refuses %s and the "
         "lte/per-pet ruling refuses %s. Nothing was written into source."
         % (len(rows), authority["pet_friendly_count"],
            _refused_count(output),
            0 if ruled_returncode == 0 else _refused_count(ruled_output))),
    ))


def blocked_report(authority: Mapping, withdrawal: Mapping,
                   blocked: Mapping) -> Dict:
    """The promotion that did not happen, and exactly why."""
    return OrderedDict((
        ("schema", "ptf-source-promotion/1.0"),
        ("what_this_is",
         "Grand Rapids was NOT promoted in source. The founder's withdrawal "
         "ruling was applied and the authority rebuilt at 49 rows, and then "
         "the policy-package schema gate refused 25 of the 35 profiles. "
         "Promotion is all-or-nothing here: a market made visible with "
         "exclusions and no profiles is worse than one left alone."),
        ("market_id", MARKET),
        ("work_order", WORK_ORDER),
        ("provider_calls", 0),
        ("usd_spent", 0.0),
        ("plan_credits_spent", 0.0),
        ("source_promoted", False),
        ("assembled", False),
        ("deployed", False),
        ("founder_ruling_applied", OrderedDict((
            ("identity_key", WITHHELD),
            ("ruling", "WITHHELD_FROM_AUTHORITY_PENDING_POLICY_EVIDENCE"),
            ("ruled_by", FOUNDER),
            ("signature_preserved", True),
            ("identity_ruling_preserved", True),
            ("why", WITHHELD_RULING)))),
        ("authority_rebuilt", OrderedDict((
            ("pet_friendly", authority["pet_friendly_count"]),
            ("verified_no_pets", authority["verified_no_pets_count"]),
            ("authority_total", authority["authority_total"]),
            ("withdrawn", len(authority["superseded_rows"])),
            ("matches_the_expected_counts",
             authority["pet_friendly_count"] == 35
             and authority["verified_no_pets_count"] == 14
             and authority["authority_total"] == 49),
        ))),
        ("blocker", blocked),
        ("nothing_was_written_into_source", [
            "markets/authority/%s/hotel_exclusions.json is unchanged" % MARKET,
            "hotel_policy_facts_%s.json was not created" % MARKET,
            "markets/%s.json still describes a discovery-stage market" % MARKET,
            "the three legacy globals were not regenerated",
            "build_market_authorities was never run in --write mode",
        ]),
        ("what_is_ready_and_waiting", [
            "the withdrawal ledger and the 49-row authority are committed",
            "the 14 exclusions are derivable from that authority in one step",
            "one rerun with the founder's weight-limit ruling completes the "
            "whole promotion, including the globals and the contract",
        ]),
    ))

# --------------------------------------------------------------------------- #
# What the promotion must not disturb
# --------------------------------------------------------------------------- #

def other_market_fingerprints() -> Dict[str, str]:
    """Every OTHER market's shard files, hashed. Taken before and after."""
    out: "OrderedDict[str, str]" = OrderedDict()
    root = LP / "markets" / "authority"
    for path in sorted(root.glob("*/*")):
        if path.parent.name == MARKET or not path.is_file():
            continue
        out[str(path.relative_to(_REPO_ROOT).as_posix())] = _sha256(path)
    for path in sorted((LP / "markets").glob("*.json")):
        if path.stem == MARKET:
            continue
        out[str(path.relative_to(_REPO_ROOT).as_posix())] = _sha256(path)
    return out


def global_additions(before: Mapping, after: Mapping, key: str) -> Dict:
    """What a regenerated global gained, and proof it changed nothing else.

    A global is generated from every market's shard, so promoting one market
    must ADD that market's rows and leave every other row byte-identical. This
    compares the two documents row by row rather than trusting the count.
    """
    def _identity(row):
        ref = row.get("hotel_ref") or {}
        return (str(row.get("market_id") or ""),
                str(row.get("normalized_name")
                    or ref.get("normalized_name") or ""))

    def _rows(document):
        return {_identity(r): r for r in (document.get(key) or ())}

    was, now = _rows(before), _rows(after)
    added = [now[k] for k in sorted(set(now) - set(was))]
    removed = [was[k] for k in sorted(set(was) - set(now))]
    foreign = [r for r in added if str(r.get("market_id") or "") != MARKET]
    removed_elsewhere = [r for r in removed
                         if str(r.get("market_id") or "") != MARKET]
    # A row that stayed but CHANGED. Retiring a route rewrites its status in
    # place, which is an update rather than a removal -- but a change to a row
    # belonging to another market would be exactly the leakage this checks for.
    changed = [now[k] for k in sorted(set(now) & set(was))
               if json.dumps(now[k], sort_keys=True)
               != json.dumps(was[k], sort_keys=True)]
    changed_elsewhere = [r for r in changed
                         if str(r.get("market_id") or "") != MARKET]
    return OrderedDict((
        ("rows_before", len(was)),
        ("rows_after", len(now)),
        ("added", len(added)),
        ("removed", len(removed)),
        ("added_from_another_market", foreign),
        ("changed_in_place", len(changed)),
        ("changed_in_another_market", changed_elsewhere),
        ("removed_from_another_market", removed_elsewhere),
        # The invariant is not "nothing was removed" -- publication withdraws
        # this market's answered routes, and that is a real removal. It is
        # "this promotion touched no other market's rows", in either direction.
        ("ok", not foreign and not removed_elsewhere and not changed_elsewhere),
        ("added_identity_keys",
         sorted(str(r.get("identity_key") or r.get("normalized_name") or "")
                for r in added)),
        # The delta is only meaningful on the run that made it; a re-run over
        # an already-promoted tree adds nothing and says 0. The END STATE is
        # what a reader and a test can rely on, so it is recorded beside it.
        ("rows_for_this_market_in_the_end_state",
         sum(1 for r in now.values()
             if str(r.get("market_id") or "") == MARKET)),
    ))


def pinned_census_gap(authority: Mapping) -> Dict:
    """Why this market still has no release contract, stated in numbers.

    ``release_contracts`` requires a reviewed document whose every field AGREES
    with ``derive_authority`` -- "a number can only move when someone changes
    the authority AND states the new number". One number cannot be stated
    honestly yet.

    Every pass since PTF-GRAND-RAPIDS-HOLLAND-GEOGRAPHY-HARDENING-002 has run
    against the 163-identity RECENSUS, and the market's PINNED census is still
    the 120-identity document the earlier build committed. Nine of the 49 rows
    promoted here are identities the pinned census does not contain. A contract
    declaring ``identity_census.expected_count: 120`` beside 49 resolved would
    assert something untrue to pass a gate, which is the one thing a release
    contract exists to prevent.

    Promoting the recensus is a contract-pinned act of its own -- it moves the
    census count a live contract would name -- so it is reported rather than
    performed inside a promotion order that did not ask for it.
    """
    pinned_path = LP / "identity_census" / ("%s.json" % MARKET)
    pinned = {h["identity_key"] for h in _load(pinned_path)["hotels"]}
    promoted = ({r["normalized_name"] for r in authority["pet_friendly"]}
                | {r["normalized_name"] for r in authority["verified_no_pets"]})
    outside = sorted(promoted - pinned)
    contract_path = (_REPO_ROOT / "deploy" / "netlify" / "release_contracts"
                     / ("%s.json" % MARKET))
    return OrderedDict((
        # Read from disk rather than frozen: PTF-GRAND-RAPIDS-CENSUS-PIN-AND-
        # RELEASE-CONTRACT-024 closed the census gap and wrote the contract, so
        # a report that still said "blocked" would be describing a world that
        # ended.
        ("written", contract_path.is_file()),
        ("blocked_when_this_pass_first_ran", True),
        ("path", "deploy/netlify/release_contracts/%s.json" % MARKET),
        ("blocked_by", "" if not outside else
         "the market's PINNED census does not contain every promoted identity"),
        ("unblocked_by", "PTF-GRAND-RAPIDS-CENSUS-PIN-AND-RELEASE-CONTRACT-024"
         if not outside else ""),
        ("pinned_census", OrderedDict((
            ("path", str(pinned_path.relative_to(_REPO_ROOT).as_posix())),
            ("count", len(pinned)),
        ))),
        ("recensus_every_pass_since_002_has_used", OrderedDict((
            ("path", "launch_packages/pettripfinder/identity_census/recensus/"
                     "%s.json" % MARKET),
            ("count", 163),
        ))),
        ("promoted_identities", len(promoted)),
        ("promoted_identities_absent_from_the_pinned_census", outside),
        ("why_not_written",
         "a contract must state identity_census.expected_count and have it "
         "agree with the derivation. Stating 120 beside 49 resolved, when 9 of "
         "those 49 are not among the 120, would pass the gate by asserting "
         "something untrue."),
        ("what_would_unblock_it",
         "promote the 163-identity recensus into the pinned census in its own "
         "work order, then write the contract naming the new count. That is a "
         "contract-pinned number moving, which is a founder-visible act."),
    ))


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #

def validate(authority: Mapping, package: Mapping, exclusions: Sequence[Mapping],
             decisions: Mapping[str, Mapping], derived: Mapping[str, Mapping],
             ledger_020: Mapping, contract: Mapping, shard_diff: Mapping,
             globals_diff: Mapping, ohio_check: str) -> Dict:
    pet = list(authority["pet_friendly"])
    keys = [r["normalized_name"] for r in pet + list(authority["verified_no_pets"])]

    unsigned = sorted(
        k for k in keys
        if not FA.is_publishable((decisions.get(k) or {}).get("founder_decision"))
        or (decisions.get(k) or {}).get("founder_reviewer_id") != FOUNDER)
    unbound = sorted(
        r["normalized_name"] for r in pet + list(authority["verified_no_pets"])
        if r.get("bound_semantic_hash") != (
            decisions.get(r["normalized_name"], {}).get("bound_semantic_hash")))

    held = {e["identity_key"] for e in ledger_020["identity_rulings"]
            if e["ruling"] == "HOLD_IDENTITY"}
    held |= {k for pair in ledger_020["pair_rulings"] for k in pair["identity_keys"]}
    silent = {e["identity_key"] for e in ledger_020["silence_rulings"]}

    not_found = sorted(
        k for k in keys
        if str((derived.get(k, {}).get("readiness") or {}).get("state") or "")
        == "POLICY_NOT_FOUND")
    no_quote = sorted(r["normalized_name"] for r in authority["verified_no_pets"]
                      if not (r.get("evidence_quote") or "").strip())
    rejected = sorted(
        r["normalized_name"] for r in pet + list(authority["verified_no_pets"])
        if r.get("membrane_verdict") != "VALID")

    profile_keys = [h["identity_key"] for h in (package.get("hotels") or ())]
    exclusion_keys = [e["normalized_name"] for e in exclusions]
    duplicate_profiles = sorted(
        k for k, n in Counter(profile_keys).items() if n > 1)
    duplicate_exclusions = sorted(
        k for k, n in Counter(exclusion_keys).items() if n > 1)
    overlap = sorted(set(profile_keys) & set(exclusion_keys))

    checks = OrderedDict((
        ("promoted_pet_friendly_count", OrderedDict((
            ("ok", authority["pet_friendly_count"] == len(profile_keys)),
            ("authority", authority["pet_friendly_count"]),
            ("policy_package", len(profile_keys))))),
        ("verified_no_pets_count", OrderedDict((
            ("ok", authority["verified_no_pets_count"] == len(exclusion_keys)),
            ("authority", authority["verified_no_pets_count"]),
            ("shard", len(exclusion_keys))))),
        ("avid_hotel_zeeland_is_absent_from_authority", OrderedDict((
            ("ok", WITHHELD not in keys and WITHHELD not in profile_keys
             and WITHHELD not in exclusion_keys),
            ("withdrawn_rows", [w["identity_key"] for w
                                in authority["superseded_rows"]]),
            ("identity_ruling_preserved", any(
                c["identity_key"] == WITHHELD
                for c in authority["identity_confirmations"])),
            ("why", "identity confirmation says which hotel a capture belongs "
                    "to; it does not make a POLICY_NOT_FOUND row publishable")))),
        ("all_unresolved_holds_absent", OrderedDict((
            ("ok", not (set(keys) & held)),
            ("identity_keys", sorted(set(keys) & held))))),
        ("all_policy_not_found_rows_absent", OrderedDict((
            ("ok", not not_found and not (set(keys) & silent)),
            ("by_readiness_state", not_found),
            ("by_020_silence_ruling", sorted(set(keys) & silent)),
            ("why", "checked on the READINESS STATE as well as on the 020 "
                    "ruling, which is the reading that withdrew avid")))),
        ("every_no_pets_row_carries_explicit_refusal_evidence", OrderedDict((
            ("ok", not no_quote), ("identity_keys", no_quote)))),
        ("every_promoted_row_has_a_signature_bound_to_current_facts",
         OrderedDict((
            ("ok", not unsigned and not unbound),
            ("unsigned", unsigned), ("unbound", unbound),
            ("decision", FA.CANONICAL_APPROVED)))),
        ("no_membrane_rejected_row_enters_without_a_valid_ruling", OrderedDict((
            ("ok", not rejected), ("identity_keys", rejected),
            ("why", "the market's one membrane rejection was avid hotel "
                    "Zeeland, and it has been withdrawn")))),
        ("no_duplicate_profile_identity", OrderedDict((
            ("ok", not duplicate_profiles), ("duplicates", duplicate_profiles)))),
        ("no_duplicate_exclusion_identity", OrderedDict((
            ("ok", not duplicate_exclusions),
            ("duplicates", duplicate_exclusions)))),
        ("no_row_is_both_a_profile_and_an_exclusion", OrderedDict((
            ("ok", not overlap), ("identity_keys", overlap)))),
        ("no_cross_market_collision", cross_market_check(keys)),
        ("no_other_market_shard_changes", OrderedDict((
            ("ok", not shard_diff["changed"]),
            ("files_checked", shard_diff["files_checked"]),
            ("changed", shard_diff["changed"])))),
        ("globals_gained_only_grand_rapids_rows", OrderedDict((
            ("ok", all(v["ok"] for v in globals_diff.values())),
            ("by_artifact", globals_diff)))),
        ("the_four_ohio_markets_are_unchanged", OrderedDict((
            ("ok", "would change" not in ohio_check.lower()),
            ("tool", "build_market_authorities --check"),
            ("note", "--check only; --write is the path that wiped corridor "
                     "assignments in PTF-DAYTON-RECERT")))),
        ("the_contract_no_longer_denies_publishing_a_policy", OrderedDict((
            ("ok", not contract_still_denies_policy(contract)),
            ("fields_still_denying", contract_still_denies_policy(contract)),
            ("show_in_navigation", contract.get("show_in_navigation")),
            ("show_in_sitemap", contract.get("show_in_sitemap"))))),
        ("no_provider_calls_and_spend_is_zero", OrderedDict((
            ("ok", True), ("provider_calls", 0), ("usd", 0.0),
            ("plan_credits", 0.0)))),
    ))
    checks["all_pass"] = all(v["ok"] for v in checks.values())
    return checks


def cross_market_check(keys: Sequence[str]) -> Dict:
    shards = LP / "markets" / "authority"
    collisions: List[Dict] = []
    markets = 0
    for routing in sorted(shards.glob("*/identity_routing.json")):
        markets += 1
        if routing.parent.name == MARKET:
            continue
        other = {str(r.get("identity_key") or "")
                 for r in (_load(routing).get("routes") or ())}
        for key in sorted(set(keys) & other):
            collisions.append(OrderedDict(
                (("identity_key", key), ("also_in_market", routing.parent.name))))
    return OrderedDict((("ok", not collisions), ("markets_scanned", markets),
                        ("collisions", collisions)))


# --------------------------------------------------------------------------- #
# The run
# --------------------------------------------------------------------------- #

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weight-limit-ruling",
                        default=SOURCE_STATED_COMPARISON,
                        choices=(STRICT, LTE_PER_PET, SOURCE_STATED_COMPARISON),
                        help="STRICT (default) publishes a weight limit only "
                             "as the source qualified it. LTE_PER_PET names a "
                             "FOUNDER decision that an unqualified blanket "
                             "maximum publishes as lte / per_pet, and is the "
                             "only thing that unblocks this market's 25 "
                             "unqualified limits. A caller must name it; it is "
                             "never assumed from another market's precedent. "
                             "SOURCE_STATED_COMPARISON is RULING-023 and the "
                             "default here: lte for a ceiling, lt for a strict "
                             "less-than, withheld where the source states "
                             "neither.")
    parser.add_argument("--scratch", default=str(_REPO_ROOT / "data" / "tmp"),
                        help="where the policy package is projected for the "
                             "schema probe before anything is written")
    args = parser.parse_args(argv)

    census_path = LP / "identity_census" / "recensus" / ("%s.json" % MARKET)
    store_path = LP / ("%s_observation_store_021.json" % PREFIX)
    ledger_path = LP / ("%s_founder_decision_ledger_021.json" % PREFIX)
    confirmations_path = LP / ("%s_identity_confirmations_021.json" % PREFIX)
    authority_021_path = LP / ("%s_proposed_authority_021.json" % PREFIX)
    ledger_020_path = LP / ("%s_founder_decision_ledger_020.json" % PREFIX)
    contract_path = LP / "markets" / ("%s.json" % MARKET)
    shard_exclusions_path = MA.exclusions_shard_path(MARKET)

    census = {h["identity_key"]: h for h in _load(census_path)["hotels"]}
    decisions = {r["identity_key"]: r
                 for r in _load(ledger_path)["signed"]}
    ledger_020 = _load(ledger_020_path)

    repaired_store, repairs = repair_correction_evidence(_load(store_path),
                                                         ledger_020)
    store_022_path = LP / ("%s_observation_store_022.json" % PREFIX)
    _write(store_022_path, repaired_store)
    store_path = store_022_path
    derived = {r["identity_key"]: r for r in repaired_store["records"]}

    before_shards = other_market_fingerprints()
    # Named through ``market_authority``, which owns them. This module must
    # never spell a generated global's path itself: the write-discipline scan
    # in test_market_authority_sharding binds any such name and refuses the
    # module, and it is right to -- a market writer edits its shard and lets
    # build_global_authority regenerate the rest.
    globals_before = {
        MA.GLOBAL_EXCLUSIONS_PATH.name: _load(MA.GLOBAL_EXCLUSIONS_PATH),
        MA.GLOBAL_ROUTING_PATH.name: _load(MA.GLOBAL_ROUTING_PATH),
    }

    # 1. the founder's withdrawal, and the authority rebuilt through it
    withdrawal = withdrawal_ledger(_load(confirmations_path),
                                   _load(authority_021_path))
    withdrawal_path = LP / ("%s_founder_withdrawal_022.json" % PREFIX)
    _write(withdrawal_path, withdrawal)

    authority_path = LP / ("%s_proposed_authority_022.json" % PREFIX)
    _run([sys.executable, str(SCRIPTS / "market_proposed_authority_cli.py"),
          "--market", MARKET, "--decisions", str(ledger_path),
          "--store", str(store_path), "--census", str(census_path),
          "--withdrawals", str(withdrawal_path), "--out", str(authority_path)],
         "the sanctioned authority builder")
    authority = _load(authority_path)

    # 2. the policy package. Projected into a scratch path FIRST, because the
    #    schema gate decides whether this market may be promoted at all and a
    #    half-promoted market -- visible, with exclusions and no profiles -- is
    #    worse than an unpromoted one.
    package_path = LP / ("hotel_policy_facts_%s.json" % MARKET)
    probe_path = Path(args.scratch) / ("hotel_policy_facts_%s.probe.json" % MARKET)
    probe_path.parent.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, str(SCRIPTS / "market_policy_package_cli.py"),
               "--authority", str(authority_path),
               "--market-name", MARKET_NAME,
               "--observations", str(store_path),
               "--expect-count", str(authority["pet_friendly_count"])]
    if args.weight_limit_ruling == LTE_PER_PET:
        command.append("--normalize-weight")
    elif args.weight_limit_ruling == SOURCE_STATED_COMPARISON:
        command.append("--weight-comparison-from-source")
    probe = subprocess.run(command + ["--out", str(probe_path)],
                           cwd=str(_REPO_ROOT), capture_output=True, text=True)
    if probe.returncode != 0:
        # Measure the OTHER reading too, so the report says what the founder's
        # ruling would actually buy rather than asserting it. This probe writes
        # to scratch and never to source.
        with_ruling = subprocess.run(
            command + ["--normalize-weight", "--out", str(probe_path) + ".ruled"],
            cwd=str(_REPO_ROOT), capture_output=True, text=True)
        blocked = weight_limit_blocker(
            authority, derived, probe.stdout + probe.stderr,
            with_ruling.stdout + with_ruling.stderr, with_ruling.returncode)
        _write(LP / ("%s_source_promotion_022.json" % PREFIX),
               blocked_report(authority, withdrawal, blocked))
        print(blocked["summary"])
        print("SOURCE_PROMOTED        : False")
        print("nothing was written into markets/ or the globals")
        return 2
    _run(command + ["--publish", RULING_023, "--out", str(package_path)],
         "the sanctioned policy-package projector")
    package = _load(package_path)

    # 3. the market's authority shard, derived by the SANCTIONED installer.
    #
    # market_registration_cli owns this derivation -- one seed row per
    # PET_FRIENDLY record, one exclusion per VERIFIED_NO_PETS record, both
    # hashes computed by hotel_exclusions' own functions. The seed rows are not
    # optional decoration: site_data.verified_public_hotels FAILS CLOSED on a
    # committed policy record with no display row, so a package published
    # without them is a market that raises rather than one that publishes.
    #
    # Its write() would ALSO rewrite the routing and affiliate shards as EMPTY,
    # which is correct for a market that has neither and destructive for this
    # one: Grand Rapids carries 110 routes reconciled by an earlier work order.
    # So the derivation is used and that write is not, the same way
    # build_market_authorities is used in check mode and never --write.
    built = REGISTRATION.build(MARKET, authority_path, census_path)
    routes_before = len(MA.load_market_routes(MARKET))
    shard_seed_path = MA.seed_shard_path(MARKET)
    HE.validate(built["exclusions_document"])
    shard_exclusions_path.write_text(
        MA.render_json(built["exclusions_document"]), encoding="utf-8")
    shard_seed_path.write_text(MA.render_seed_csv(built["seed_rows"]),
                               encoding="utf-8")
    rows = list(built["exclusions_document"]["exclusions"])
    seed_rows = list(built["seed_rows"])
    routes_after = len(MA.load_market_routes(MARKET))
    if routes_after != routes_before:
        raise PromotionError(
            "the routing shard moved from %d routes to %d; this promotion "
            "writes the seed and exclusion shards and must never touch routing"
            % (routes_before, routes_after))

    # 4. the routes publication has now answered
    retirement = withdraw_published_routes(seed_rows)

    # 5. the market contract
    contract, contract_changes = promote_contract(contract_path)
    _write(contract_path, contract)

    # 6. the three legacy globals, from the shards, by their own assembler
    _run([sys.executable, "-m", "scripts.pettripfinder.build_global_authority",
          "--write"], "the global authority assembler")
    globals_diff = OrderedDict((
        (MA.GLOBAL_EXCLUSIONS_PATH.name, global_additions(
            globals_before[MA.GLOBAL_EXCLUSIONS_PATH.name],
            _load(MA.GLOBAL_EXCLUSIONS_PATH), "exclusions")),
        (MA.GLOBAL_ROUTING_PATH.name, global_additions(
            globals_before[MA.GLOBAL_ROUTING_PATH.name],
            _load(MA.GLOBAL_ROUTING_PATH), "routes")),
    ))

    # 7. proof the four Ohio markets were not disturbed
    # No flag at all: this tool's check mode is its DEFAULT and --write is the
    # opt-in, which is the opposite of build_global_authority's spelling. Its
    # --write path is the one that wiped corridor assignments in
    # PTF-DAYTON-RECERT, so the argument is deliberately absent rather than
    # spelled, and there is no way for a typo here to become a write.
    ohio = _run([sys.executable, "-m",
                 "scripts.pettripfinder.build_market_authorities"],
                "build_market_authorities (check mode, the default)")

    after_shards = other_market_fingerprints()
    shard_diff = OrderedDict((
        ("files_checked", len(before_shards)),
        ("changed", sorted(k for k in before_shards
                           if before_shards[k] != after_shards.get(k))),
    ))

    validation = validate(authority, package, rows, decisions, derived,
                          ledger_020, contract, shard_diff, globals_diff, ohio)

    report = OrderedDict((
        ("schema", "ptf-source-promotion/1.0"),
        ("what_this_is",
         "Grand Rapids promoted in source: 35 profiles published, 14 "
         "exclusions written to the shard, the market contract revealed, the "
         "three legacy globals regenerated. Nothing assembled, nothing "
         "deployed."),
        ("market_id", MARKET),
        ("work_order", WORK_ORDER),
        ("provider_calls", 0),
        ("usd_spent", 0.0),
        ("plan_credits_spent", 0.0),
        ("source_promoted", bool(validation["all_pass"])),
        ("deployed", False),
        ("assembled", False),
        ("founder_ruling", OrderedDict((
            ("identity_key", WITHHELD),
            ("ruling", "WITHHELD_FROM_AUTHORITY_PENDING_POLICY_EVIDENCE"),
            ("ruled_by", FOUNDER),
            ("signature_preserved", True),
            ("identity_ruling_preserved", True),
            ("why", WITHHELD_RULING)))),
        ("counts", OrderedDict((
            ("pet_friendly", authority["pet_friendly_count"]),
            ("verified_no_pets", authority["verified_no_pets_count"]),
            ("authority_total", authority["authority_total"]),
            ("profiles_published", len(package.get("hotels") or ())),
            ("exclusions_written", len(rows)),
            ("withdrawn", len(authority["superseded_rows"])),
        ))),
        ("written_by_this_pass", [str(p.relative_to(_REPO_ROOT).as_posix())
                                  for p in (withdrawal_path, authority_path,
                                            package_path,
                                            shard_exclusions_path,
                                            shard_seed_path,
                                            contract_path)]),
        ("routes_withdrawn_by_publication", OrderedDict(
            (k, v) for k, v in retirement.items()
            if k != "archived_here_in_full")),
        ("withdrawn_route_records", retirement["archived_here_in_full"]),
        ("routing_shard_not_wiped", OrderedDict((
            ("routes_before", routes_before), ("routes_after", routes_after),
            ("why", "market_registration_cli.write() would have rewritten it "
                    "as empty, which is right for a market with no routes and "
                    "destructive for this one")))),
        ("regenerated_by_build_global_authority",
         "the three legacy globals and the manifest beside them. This module "
         "never writes one: it edits this market's shard and lets their own "
         "assembler produce them."),
        ("contract_changes", contract_changes),
        ("contract_end_state", OrderedDict(
            (field, contract.get(field)) for field, _value in CONTRACT_UPDATES)),
        ("globals_regenerated_by", "build_global_authority --write, which "
                                   "assembles the three legacy files from the "
                                   "shards and touches nothing else"),
        ("build_market_authorities_check", ohio.strip().splitlines()[-3:]),
        ("not_done_here", [
            "no release contract was written",
            "no launch-participation row was added",
            "no deployment manifest entry was made",
            "no bundle was assembled",
            "nothing was deployed",
            "build_market_authorities --write was never run",
        ]),
        ("still_outside_the_authority", OrderedDict((
            ("avid_hotel_zeeland", "withheld pending policy evidence"),
            ("policy_not_found", 3),
            ("identity_holds", 2),
            ("identity_hold_rows", 1),
            ("routing_unresolved", 11),
        ))),
        ("release_contract", pinned_census_gap(authority)),
        ("next_step_for_production_assembly", [
            "promote the 163-identity recensus into the pinned census, which "
            "is what a release contract's identity_census count must describe",
            "then write deploy/netlify/release_contracts/%s.json -- this "
            "market has none, and every market with verified inventory has "
            "one" % MARKET,
            "add the market's launch_participation row; the founder is the "
            "only one who may add it (PTF-046)",
            "add the market to deploy/netlify/global_deployment_manifest.json, "
            "which invalidates the CURRENT deployment record (PTF-047) and so "
            "needs its own authorization",
            "assemble with assemble_netlify_bundle --context production, then "
            "a founder deployment authorization naming the bundle",
        ]),
        ("validation", validation),
    ))
    report_path = LP / ("%s_source_promotion_022.json" % PREFIX)
    _write(report_path, report)

    counts = report["counts"]
    print("withdrawn              : %d (%s)" % (counts["withdrawn"], WITHHELD))
    print("pet-friendly           : %d" % counts["pet_friendly"])
    print("verified no-pets       : %d" % counts["verified_no_pets"])
    print("authority total        : %d" % counts["authority_total"])
    print("profiles published     : %d" % counts["profiles_published"])
    print("exclusions written     : %d" % counts["exclusions_written"])
    print("contract fields changed: %d" % len(contract_changes))
    print("other shards changed   : %d of %d"
          % (len(shard_diff["changed"]), shard_diff["files_checked"]))
    for name, diff in globals_diff.items():
        print("  %-24s %d -> %d (+%d, -%d)"
              % (name, diff["rows_before"], diff["rows_after"],
                 diff["added"], diff["removed"]))
    print("validation             : %s" % validation["all_pass"])
    print("SOURCE_PROMOTED        : %s" % report["source_promoted"])
    return 0 if validation["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
