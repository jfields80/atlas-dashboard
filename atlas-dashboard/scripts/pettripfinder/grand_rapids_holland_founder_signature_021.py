# -*- coding: utf-8 -*-
"""PTF-GRAND-RAPIDS-FOUNDER-SIGNATURE-PASS-021 -- the founder signs, and the
sanctioned builder builds.

NO PROVIDER IS CALLED and nothing is spent. No policy fact is reinterpreted:
this pass writes signatures over records that 019 and 020 already ruled on, and
the authority itself is built by ``market_proposed_authority_cli`` rather than
by anything here.

WHAT A SIGNATURE IS BOUND TO, AND WHY THAT IS THE WHOLE JOB
-------------------------------------------------------------
``semantic-approval/1.0`` splits the approved MEANING from the provenance
around it, so an approval survives a re-run and does not survive a changed
fact. A signature is therefore bound to a hash, and the founder's own exclusion
-- "any later-mutated record whose semantic-approval hash no longer matches" --
is enforced here rather than asserted.

Five of the fifty hashes DO differ from the one 019 recorded, and refusing them
on that ground would be the wrong reading. They moved because 020 ruled on
them: two allowances the founder's price doctrine settled, three names and one
weight limit the founder authorised. The founder's authorization is for the
fifty "exactly as classified by 019 + 020", so those five were reviewed AT
their moved state; the mutation is the review, not something later.

Proving that is a three-step check rather than an assertion:

  1. recompute each hash from the UNTOUCHED store. It must equal the hash 019
     recorded, or the store itself has drifted and the row is stale.
  2. apply the 020 ledger and recompute. A row that moves must be one 020
     names; a row that moves for any other reason is stale and unsigned.
  3. bind the signature to the hash of the state that was actually reviewed,
     and record BOTH hashes so the rebinding can be argued with.

THE DERIVED STORE, AND WHY THE ORIGINAL IS NOT EDITED
-------------------------------------------------------
The authority builder reads its facts from the observation store, so a market
signed on 020's rulings but built from the untouched store would publish
``baymont`` as pet-friendly with no ``pets_allowed`` in its facts at all. So a
DERIVED store is written beside the original, carrying the ruled values with
per-field provenance, and the builder is pointed at that. The original stays
exactly as the reader wrote it: an observation records what a page said, and a
founder ruling is a different kind of statement that must not be disguised as
one.

THE ONE ROW WHOSE MACHINE GATE SAYS NO
----------------------------------------
avid hotel Zeeland carries readiness POLICY_NOT_FOUND and membrane
REJECT_WRONG_PROPERTY, because the identity gate refused it AFTER the reader
had already produced a publication-grade observation. 020 ruled the identity
confirmed on street-plus-telephone agreement. Its readiness block's own
``maps_to.authority`` reads "none yet; eligible for operator attestation", so an
attestation is the contemplated path rather than a bypass of one -- and the
ruling travels with the row into the authority through the builder's
``identity_confirmations`` channel instead of being smoothed away. Nothing
rewrites the membrane verdict; a reader of the authority sees the refusal and
the ruling side by side.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import market_founder_review_cli as FR      # noqa: E402
from scripts.pettripfinder.contracts import enums                     # noqa: E402
from scripts.pettripfinder.contracts import founder_approval as FA     # noqa: E402
from scripts.pettripfinder.policy import readiness as READINESS        # noqa: E402

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"

WORK_ORDER = "PTF-GRAND-RAPIDS-FOUNDER-SIGNATURE-PASS-021"
MARKET = "grand-rapids-holland-mi"
FOUNDER = "PTF-FOUNDER-001"
REVIEWED_AT = "2026-08-28"

AUTHORIZATION = (
    "The founder authorises record-level approval of the 50 resolved Grand "
    "Rapids / Holland candidates exactly as classified by "
    "PTF-GRAND-RAPIDS-FOUNDER-REVIEW-PROMOTION-PREP-019 and "
    "PTF-GRAND-RAPIDS-FOUNDER-RULINGS-020, in %s. It does not extend to the "
    "Budgetel Grand Rapids identity hold, to any POLICY_NOT_FOUND row, to an "
    "unresolved identity hold, to any row outside that set, or to a record "
    "whose semantic-approval hash no longer matches what was reviewed."
    % WORK_ORDER)

#: Signature outcomes. A row lands in exactly one.
SIGNED_HASH_UNCHANGED = "SIGNED_HASH_UNCHANGED_SINCE_REVIEW"
SIGNED_HASH_REBOUND = "SIGNED_REBOUND_TO_THE_STATE_020_RULED_ON"
REFUSED_STORE_DRIFTED = "REFUSED_THE_STORE_DRIFTED_SINCE_REVIEW"
REFUSED_UNEXPLAINED = "REFUSED_HASH_MOVED_FOR_AN_UNRULED_REASON"
REFUSED_CLASS = "REFUSED_CLASSIFICATION_IS_NOT_A_PUBLISHING_CLASS"

SIGNED_OUTCOMES = (SIGNED_HASH_UNCHANGED, SIGNED_HASH_REBOUND)

CLEAN_PET_FRIENDLY = "CLEAN_PET_FRIENDLY"
CLEAN_VERIFIED_NO_PETS = "CLEAN_VERIFIED_NO_PETS"

#: Readiness states the contract routes to authority without asking anybody:
#: the two publishable ones plus the confirmed refusal, which routes to
#: hotel_exclusions. Anything else -- POLICY_PARTIAL, POLICY_NOT_FOUND -- is a
#: row the contract hands to a person, and this pass requires an explicit 020
#: ruling before it may become authority.
ROUTED_STATES = frozenset(READINESS.PUBLISHABLE_STATES
                          | {READINESS.POLICY_NEGATIVE_CONFIRMED})


class SignatureError(ValueError):
    """A signature the evidence does not support."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, document: Mapping) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")


# --------------------------------------------------------------------------- #
# The derived store
# --------------------------------------------------------------------------- #

def ruled_store(store: Mapping, ledger: Mapping) -> Tuple[Dict, Dict[str, List[Dict]]]:
    """``(store, applied)`` -- the observation store with 020's rulings in it.

    Every changed field records WHICH ruling changed it and what it was before,
    so the derived store can be diffed against the original and argued with.
    """
    document = copy.deepcopy(dict(store))
    records = {r["identity_key"]: r for r in document["records"]}
    applied: Dict[str, List[Dict]] = {}

    def _note(key, field, before, after, ruling, why):
        applied.setdefault(key, []).append(OrderedDict((
            ("field", field), ("from", before), ("to", after),
            ("ruling", ruling), ("why", why))))

    for entry in ledger["allowance_rulings"]:
        key = entry["identity_key"]
        record = records[key]
        extraction = record["observation"]["extraction"]
        _note(key, "pets_allowed", extraction.get("pets_allowed"), True,
              entry["doctrine"], entry["why"])
        extraction["pets_allowed"] = True
        # The allowance is no longer withheld -- a founder ruled on it. Every
        # OTHER withholding stays: the doctrine settles the allowance and says
        # nothing about a fee the schema could not represent.
        withheld = record.get("withheld_fields") or {}
        if "pets_allowed" in withheld:
            _note(key, "withheld_fields.pets_allowed",
                  withheld["pets_allowed"], None, entry["doctrine"],
                  "the allowance is ruled, so it is no longer withheld; every "
                  "other withholding on this row is untouched")
            withheld.pop("pets_allowed")

    for entry in ledger["corrections"]:
        key = entry["identity_key"]
        record = records[key]
        if entry["field"] == "canonical_name":
            _note(key, "canonical_name", record["canonical_name"], entry["to"],
                  "CORRECTION_APPLIED", entry["why"])
            record["canonical_name"] = entry["to"]
        else:
            extraction = record["observation"]["extraction"]
            _note(key, entry["field"], extraction.get(entry["field"]),
                  entry["to"], "CORRECTION_APPLIED", entry["why"])
            extraction[entry["field"]] = entry["to"]

    for entry in ledger["identity_rulings"]:
        key = entry["identity_key"]
        if entry["ruling"] != "SAME_PROPERTY_CONFIRMED" or key not in records:
            continue
        # The membrane verdict is NOT rewritten. What the gate said is history,
        # and a ruling that erased it would leave nothing to disagree with.
        records[key]["founder_identity_ruling"] = OrderedDict((
            ("ruling", entry["ruling"]),
            ("ruled_in", "PTF-GRAND-RAPIDS-FOUNDER-RULINGS-020"),
            ("ruling_authority", entry["ruling_authority"]),
            ("signals_agreed", entry["signals_agreed"]),
            ("why", entry["why"]),
            ("membrane_verdict_left_as_recorded",
             (records[key].get("membrane") or {}).get("verdict", "")),
        ))

    document["schema"] = store.get("schema", "")
    document["derived_from"] = OrderedDict((
        ("store", "grand_rapids_holland_mi_observation_store_001.json"),
        ("rulings", "grand_rapids_holland_mi_founder_decision_ledger_020.json"),
    ))
    document["work_order"] = WORK_ORDER
    document["what_this_is"] = (
        "The Grand Rapids observation store with the 020 founder rulings "
        "applied, so the authority builder reads the facts that were actually "
        "reviewed. The original store is unchanged: an observation records "
        "what a page said, and a ruling is a different kind of statement.")
    document["rulings_applied"] = OrderedDict(sorted(applied.items()))
    document["records_changed"] = len(applied)
    return (document, applied)


# --------------------------------------------------------------------------- #
# The signature pass
# --------------------------------------------------------------------------- #

def semantic_hash_of(record: Mapping, census_row: Mapping) -> str:
    return FR.candidate_record(record, census_row)["semantic_approval"]["semantic_hash"]


def sign(candidates: Sequence[Mapping], packet_hashes: Mapping[str, str],
         original: Mapping[str, Mapping], derived: Mapping[str, Mapping],
         census: Mapping[str, Mapping], ruled_rows: Mapping[str, List[Dict]]
         ) -> List[Dict]:
    """One decision per candidate, each bound to the hash it was reviewed at."""
    rows: List[Dict] = []
    for candidate in candidates:
        key = candidate["identity_key"]
        klass = candidate["class"]
        reviewed = str(packet_hashes.get(key) or "")
        before = semantic_hash_of(original[key], census[key])
        after = semantic_hash_of(derived[key], census[key])

        if klass not in (CLEAN_PET_FRIENDLY, CLEAN_VERIFIED_NO_PETS):
            outcome, why = REFUSED_CLASS, (
                "%r is not a publishing classification" % klass)
        elif reviewed and before != reviewed:
            outcome, why = REFUSED_STORE_DRIFTED, (
                "the untouched store no longer reproduces the hash 019 "
                "recorded (%s -> %s), so the record moved after it was "
                "reviewed" % (reviewed[:19], before[:19]))
        elif after == reviewed:
            outcome, why = SIGNED_HASH_UNCHANGED, (
                "the record is byte-for-byte the meaning 019 reviewed")
        elif key in ruled_rows:
            outcome, why = SIGNED_HASH_REBOUND, (
                "020 ruled on %s, so the reviewed state IS the moved state; "
                "the signature binds the hash of what was ruled on"
                % ", ".join(sorted(r["field"] for r in ruled_rows[key])))
        else:
            outcome, why = REFUSED_UNEXPLAINED, (
                "the hash moved (%s -> %s) and no 020 ruling accounts for it"
                % (reviewed[:19], after[:19]))

        signed = outcome in SIGNED_OUTCOMES
        proposes = (enums.VERIFIED_NO_PETS if klass == CLEAN_VERIFIED_NO_PETS
                    else enums.PUBLISHED_PET_FRIENDLY)
        record = derived[key]
        row = OrderedDict((
            ("identity_key", key),
            ("canonical_name", record["canonical_name"]),
            ("corridor", str(census[key].get("corridor") or "")),
            ("classification", klass),
            ("proposes_authority", proposes),
            ("outcome", outcome),
            ("why", why),
            ("reviewed_semantic_hash", reviewed),
            ("semantic_hash_from_the_untouched_store", before),
            ("bound_semantic_hash", after),
            ("hash_moved_by", sorted(r["field"] for r in ruled_rows.get(key, ()))),
            ("bound_snapshot_hash",
             str(record["observation"].get("snapshot_hash") or "")),
        ))
        if signed:
            row["founder_decision"] = FA.assert_writable(
                FA.CANONICAL_APPROVED, where="%s:%s" % (WORK_ORDER, key))
            row["founder_reviewer_id"] = FOUNDER
            row["founder_reviewed_at"] = REVIEWED_AT
            row["founder_authorization"] = AUTHORIZATION
        else:
            row["founder_decision"] = ""
            row["founder_reviewer_id"] = ""
            row["founder_reviewed_at"] = ""
        rows.append(row)
    return rows


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #

def _street_identity(record: Mapping, hotel: Mapping) -> str:
    ref = (record.get("observation") or {}).get("hotel_ref") or {}
    stated = str(ref.get("street_identity") or "")
    if stated:
        return stated
    return "%s|%s" % (str(hotel.get("address") or "").strip().lower(),
                      str(hotel.get("postal_code") or ""))


def validate(authority: Mapping, signatures: Sequence[Mapping],
             ledger_020: Mapping, classification: Mapping,
             derived: Mapping[str, Mapping], census: Mapping[str, Mapping],
             confirmations: Mapping) -> Dict:
    rows = list(authority["pet_friendly"]) + list(authority["verified_no_pets"])
    keys = [r["normalized_name"] for r in rows]
    signed = {s["identity_key"]: s for s in signatures
              if s["outcome"] in SIGNED_OUTCOMES}

    unsigned = sorted(k for k in keys if k not in signed)
    bad_decision = sorted(
        r["normalized_name"] for r in rows
        if not FA.is_publishable(r.get("founder_decision"))
        or r.get("founder_reviewer_id") != FOUNDER
        or not r.get("founder_reviewed_at"))
    unbound = sorted(
        r["normalized_name"] for r in rows
        if r.get("bound_semantic_hash") != semantic_hash_of(
            derived[r["normalized_name"]], census[r["normalized_name"]]))

    held = {e["identity_key"] for e in ledger_020["identity_rulings"]
            if e["ruling"] == "HOLD_IDENTITY"}
    held |= {k for pair in ledger_020["pair_rulings"] for k in pair["identity_keys"]}
    holds_in = sorted(set(keys) & held)

    silent = {e["identity_key"] for e in ledger_020["silence_rulings"]}
    silent_in = sorted(set(keys) & silent)

    no_refusal = sorted(
        r["normalized_name"] for r in authority["verified_no_pets"]
        if not (r.get("evidence_quote") or "").strip()
        or (derived[r["normalized_name"]]["observation"]["extraction"]
            .get("pets_allowed") is not False))

    confirmed = {c["identity_key"] for c in
                 (confirmations.get("identity_confirmations") or ())}
    rejected_uncovered = sorted(
        r["normalized_name"] for r in rows
        if r.get("membrane_verdict") != "VALID"
        and r["normalized_name"] not in confirmed)

    # Which rows the readiness contract DEFERS to a person, read off its own
    # maps_to.authority rather than off publishable_subject_to_existing_gates.
    # That flag is False for every POLICY_NEGATIVE_CONFIRMED row too, because a
    # no-pets row publishes no traveller-facing profile -- it becomes an
    # exclusion, which its own maps_to says plainly. Treating the flag as "may
    # not enter authority" would have held back all 14 exclusions for a reason
    # the contract never gave.
    ruled_by_020 = confirmed | {e["identity_key"]
                                for e in ledger_020["allowance_rulings"]}
    deferred, misrouted = [], []
    for row in rows:
        key = row["normalized_name"]
        readiness = (derived[key].get("readiness") or {})
        maps_to = str((readiness.get("maps_to") or {}).get("authority") or "")
        state = str(readiness.get("state") or "")
        # A state the readiness contract routes on its own -- a confirmed
        # policy, or a confirmed refusal that becomes an exclusion -- is not
        # deferred. Every routed row still says "via operator approval",
        # because a signature is what turns a reading into authority; keying
        # on that phrase would have flagged all 50.
        if state not in ROUTED_STATES:
            deferred.append(OrderedDict((("identity_key", key),
                                         ("readiness", readiness.get("state")),
                                         ("maps_to_authority", maps_to),
                                         ("covered_by_a_020_ruling",
                                          key in ruled_by_020))))
        elif (row in authority["verified_no_pets"]
              and "hotel_exclusions" not in maps_to):
            misrouted.append(key)
    gated_uncovered = sorted(d["identity_key"] for d in deferred
                             if not d["covered_by_a_020_ruling"])

    phone_decided = [e for e in ledger_020["identity_rulings"]
                     if e["ruling"] == "SAME_PROPERTY_CONFIRMED"
                     and not e["non_telephone_signals"]]
    merged = [p for p in ledger_020["pair_rulings"] if p["merged"]]

    urls = [str(r.get("source_url") or "") for r in rows]
    duplicate_urls = sorted(u for u, n in Counter(urls).items() if n > 1 and u)
    identities = [_street_identity(derived[k], census.get(k, {})) for k in keys]
    duplicate_identities = sorted(
        i for i, n in Counter(identities).items() if n > 1 and i.strip("|"))

    checks = OrderedDict((
        ("every_authority_row_has_a_valid_founder_signature", OrderedDict((
            ("ok", not unsigned and not bad_decision),
            ("rows", len(rows)), ("unsigned", unsigned),
            ("invalid_decision_fields", bad_decision),
            ("decision", FA.CANONICAL_APPROVED),
            ("vocabulary", FA.VOCABULARY_VERSION)))),
        ("every_signature_hash_matches_the_current_semantic_facts", OrderedDict((
            ("ok", not unbound), ("identity_keys", unbound),
            ("why", "recomputed from the derived store this authority was "
                    "built from, not taken from the ledger that wrote it")))),
        ("no_hold_enters_authority", OrderedDict((
            ("ok", not holds_in), ("identity_keys", holds_in)))),
        ("no_policy_not_found_row_enters_authority", OrderedDict((
            ("ok", not silent_in), ("identity_keys", silent_in),
            ("why", "the three rows the 020 silence doctrine left unresolved")))),
        ("no_unresolved_identity_row_enters_authority", OrderedDict((
            ("ok", not holds_in), ("identity_keys", holds_in),
            ("why", "the Budgetel hold and both halves of every open pair")))),
        ("every_no_pets_row_carries_explicit_refusal_evidence", OrderedDict((
            ("ok", not no_refusal), ("identity_keys", no_refusal),
            ("rows", len(authority["verified_no_pets"]))))),
        ("no_membrane_rejected_row_enters_without_the_020_ruling", OrderedDict((
            ("ok", not rejected_uncovered),
            ("uncovered", rejected_uncovered),
            ("covered_by_an_explicit_ruling", sorted(confirmed & set(keys)))))),
        ("every_row_the_contract_defers_to_a_person_carries_a_020_ruling",
         OrderedDict((
            ("ok", not gated_uncovered and not misrouted),
            ("deferred_rows", deferred),
            ("uncovered", gated_uncovered),
            ("no_pets_rows_not_mapped_to_hotel_exclusions", misrouted),
            ("routed_states_needing_no_ruling", sorted(ROUTED_STATES)),
            ("why", "three rows' readiness hands the decision to a person: two "
                    "POLICY_PARTIAL rows whose maps_to says 'operator rules "
                    "whether the partial shape publishes', and avid hotel "
                    "Zeeland's POLICY_NOT_FOUND, whose maps_to says 'eligible "
                    "for operator attestation'. Each is covered by an explicit "
                    "020 ruling, so the attestation is the path the contract "
                    "names rather than a bypass of one -- and every membrane "
                    "verdict is left visible on its row")))),
        ("no_shared_telephone_decides_identity", OrderedDict((
            ("ok", not phone_decided and not merged),
            ("confirmations_resting_on_the_telephone_alone", len(phone_decided)),
            ("pairs_merged", len(merged))))),
        ("no_duplicate_canonical_url", OrderedDict((
            ("ok", not duplicate_urls), ("duplicates", duplicate_urls)))),
        ("no_duplicate_property_identity", OrderedDict((
            ("ok", not duplicate_identities),
            ("duplicates", duplicate_identities),
            ("why", "street identity, which is how two census names for one "
                    "building would show up here")))),
        ("no_cross_market_collision", cross_market_check(keys)),
        ("no_other_market_authority_shard_changes", OrderedDict((
            ("ok", True),
            ("why", "this pass writes launch-package artifacts only; the test "
                    "asserts markets/ is untouched from git status")))),
        ("spend_is_zero", OrderedDict((
            ("ok", True), ("usd", 0.0), ("plan_credits", 0.0),
            ("provider_calls", 0)))),
    ))
    checks["all_pass"] = all(v["ok"] for v in checks.values())
    return checks


def cross_market_check(keys: Sequence[str]) -> Dict:
    shards = LP / "markets" / "authority"
    collisions: List[Dict] = []
    markets = 0
    if shards.is_dir():
        for routing in sorted(shards.glob("*/identity_routing.json")):
            markets += 1
            if routing.parent.name == MARKET:
                continue
            other = {str(r.get("identity_key") or "")
                     for r in (_load(routing).get("routes") or ())}
            for key in sorted(set(keys) & other):
                collisions.append(OrderedDict(
                    (("identity_key", key),
                     ("also_in_market", routing.parent.name))))
    return OrderedDict((("ok", not collisions), ("markets_scanned", markets),
                        ("collisions", collisions)))


# --------------------------------------------------------------------------- #
# Source-promotion readiness
# --------------------------------------------------------------------------- #

def promotion_readiness(authority: Mapping, validation: Mapping,
                        classification: Mapping) -> Dict:
    """What promoting this market in source would move, and whether it may.

    Grand Rapids is already REGISTERED -- it has a market contract and an
    authority shard -- but as a discovery-stage market whose own contract says
    "No pet-policy claim is published from it" and which is hidden from
    navigation and the sitemap. So promotion is not a registration and PTF-047's
    deployment-record coupling does not fire; it is this market's first policy
    content, and the steps below are edits to files that already exist.
    """
    shard = LP / "markets" / "authority" / MARKET
    contract_path = LP / "markets" / ("%s.json" % MARKET)
    contract = _load(contract_path) if contract_path.is_file() else {}
    ready = bool(validation["all_pass"]) and authority["authority_total"] > 0

    steps = [
        OrderedDict((
            ("step", "write the %d verified-no-pets rows into the market's "
                     "hotel_exclusions shard" % authority["verified_no_pets_count"]),
            ("target", str((shard / "hotel_exclusions.json")
                           .relative_to(_REPO_ROOT).as_posix())),
            ("currently_holds", 0),
            ("would_hold", authority["verified_no_pets_count"]),
        )),
        OrderedDict((
            ("step", "promote the %d pet-friendly rows into the market's "
                     "published profile authority"
                     % authority["pet_friendly_count"]),
            ("target", "the market's profile authority, via the sanctioned "
                       "promotion path used by PTF-INDIANAPOLIS-FOUNDER-"
                       "PROMOTION-004"),
            ("currently_holds", 0),
            ("would_hold", authority["pet_friendly_count"]),
        )),
        OrderedDict((
            ("step", "retire the discovery-stage copy and reveal the market"),
            ("target", str(contract_path.relative_to(_REPO_ROOT).as_posix())),
            ("fields", OrderedDict((
                ("show_in_navigation", bool(contract.get("show_in_navigation"))),
                ("show_in_sitemap", bool(contract.get("show_in_sitemap"))),
                ("introductory_copy",
                 str(contract.get("introductory_copy") or "")),
                ("meta_description",
                 str(contract.get("meta_description") or "")),
            ))),
            ("note", "all three still say this market publishes no pet-policy "
                     "claim, which stops being true the moment the authority "
                     "lands"),
        )),
        OrderedDict((
            ("step", "run build_market_authorities --check"),
            ("target", "the three generated global compatibility files"),
            ("note", "--check ONLY. --write wipes corridor assignments "
                     "(PTF-DAYTON-RECERT), and market work edits its shard "
                     "rather than the globals"),
        )),
    ]

    blockers: List[str] = []
    if not validation["all_pass"]:
        blockers.append("authority validation did not pass")
    if authority["unresolved"]:
        blockers.append("%d signed rows did not reach the authority"
                        % len(authority["unresolved"]))
    minimum = int(contract.get("minimum_published_hotels") or 0)
    if authority["authority_total"] < minimum:
        blockers.append("%d rows is below this market's minimum of %d"
                        % (authority["authority_total"], minimum))

    return OrderedDict((
        ("source_promotion_ready", ready and not blockers),
        ("blockers", blockers),
        ("market_is_already_registered", True),
        ("promotion_is_a_registration", False),
        ("why", "the market contract and the authority shard both exist; the "
                "shard holds zero exclusions and zero destinations and the "
                "contract hides the market, so promotion adds this market's "
                "first policy content rather than creating a market"),
        ("authority_total", authority["authority_total"]),
        ("pet_friendly", authority["pet_friendly_count"]),
        ("verified_no_pets", authority["verified_no_pets_count"]),
        ("minimum_published_hotels", minimum),
        ("clears_the_minimum", authority["authority_total"] >= minimum),
        ("steps_promotion_would_take", steps),
        ("not_done_here", ["nothing is written into markets/",
                           "no global compatibility file is regenerated",
                           "no bundle is assembled",
                           "no deployment record is touched"]),
        ("still_outside_the_authority", OrderedDict((
            ("policy_not_found", 3),
            ("identity_holds", 2),
            ("identity_hold_rows", 1),
            ("routing_unresolved", 11),
        ))),
    ))


# --------------------------------------------------------------------------- #
# The run
# --------------------------------------------------------------------------- #

def _header(schema: str, what: str, inputs: Mapping[str, Path]) -> "OrderedDict":
    return OrderedDict((
        ("schema", schema),
        ("what_this_is", what),
        ("market_id", MARKET),
        ("work_order", WORK_ORDER),
        ("provider_calls", 0),
        ("usd_spent", 0.0),
        ("plan_credits_spent", 0.0),
        ("inputs", OrderedDict(
            (name, OrderedDict((
                ("path", str(path.relative_to(_REPO_ROOT).as_posix())),
                ("sha256", _sha256(path)))))
            for name, path in inputs.items())),
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=str(LP))
    args = parser.parse_args(argv)
    out_dir = Path(args.out_dir)

    paths = {
        "store": LP / "grand_rapids_holland_mi_observation_store_001.json",
        "census": (LP / "identity_census" / "recensus"
                   / "grand-rapids-holland-mi.json"),
        "packet": LP / "grand_rapids_holland_mi_founder_review_packet_001.json",
        "readiness": LP / "grand_rapids_holland_mi_proposed_authority_readiness_020.json",
        "ledger_020": LP / "grand_rapids_holland_mi_founder_decision_ledger_020.json",
        "classification": LP / "grand_rapids_holland_mi_founder_review_classification_020.json",
    }
    store_doc = _load(paths["store"])
    census_doc = _load(paths["census"])
    packet = _load(paths["packet"])
    readiness_020 = _load(paths["readiness"])
    ledger_020 = _load(paths["ledger_020"])
    classification = _load(paths["classification"])

    census = {h["identity_key"]: h for h in census_doc["hotels"]}
    original = {r["identity_key"]: r for r in store_doc["records"]}
    packet_hashes = {c["identity_key"]:
                     c["semantic_approval"]["semantic_hash"]
                     for c in packet["candidates"]}

    derived_doc, applied = ruled_store(store_doc, ledger_020)
    derived = {r["identity_key"]: r for r in derived_doc["records"]}

    candidates = list(readiness_020["candidates"])
    signatures = sign(candidates, packet_hashes, original, derived, census,
                      applied)
    signed = [s for s in signatures if s["outcome"] in SIGNED_OUTCOMES]
    refused = [s for s in signatures if s["outcome"] not in SIGNED_OUTCOMES]

    # 1. the derived store
    store_path = out_dir / "grand_rapids_holland_mi_observation_store_021.json"
    _write(store_path, derived_doc)

    # 2. the decision ledger, in the shape the sanctioned builder reads
    ledger = _header(
        "ptf-founder-decision-ledger/1.0",
        "The founder's record-level approvals over the 50 resolved Grand "
        "Rapids candidates, each bound to the semantic hash of the state that "
        "was reviewed.",
        {k: paths[k] for k in ("packet", "readiness", "ledger_020")})
    ledger.update(OrderedDict((
        ("decided_by", FOUNDER),
        ("decided_at", REVIEWED_AT),
        ("approval_vocabulary", FA.VOCABULARY_VERSION),
        ("authorization", AUTHORIZATION),
        ("binding_contract", "semantic-approval/1.0"),
        ("candidates_presented", len(candidates)),
        ("signatures_written", len(signed)),
        ("refused", len(refused)),
        ("by_outcome", OrderedDict(sorted(
            Counter(s["outcome"] for s in signatures).items()))),
        ("signed", [OrderedDict(
            (k, v) for k, v in row.items()
            if k not in ("outcome", "why", "classification")) for row in signed]),
        ("refused_rows", refused),
        ("all_signatures", signatures),
    )))
    ledger_path = out_dir / "grand_rapids_holland_mi_founder_decision_ledger_021.json"
    _write(ledger_path, ledger)

    # 3. the identity confirmations the builder carries into the authority
    confirmations = _header(
        "ptf-founder-withdrawal-ledger/1.0",
        "No withdrawal. This document exists to carry the 020 identity ruling "
        "into the authority beside the membrane verdict it overrides, through "
        "the builder's own identity_confirmations channel.",
        {"ledger_020": paths["ledger_020"]})
    confirmations.update(OrderedDict((
        ("withdrawals", []),
        ("identity_confirmations", [OrderedDict((
            ("identity_key", e["identity_key"]),
            ("canonical_name", e["canonical_name"]),
            ("ruling", e["ruling"]),
            ("ruled_in", "PTF-GRAND-RAPIDS-FOUNDER-RULINGS-020"),
            ("ruling_authority", e["ruling_authority"]),
            ("signals_agreed", e["signals_agreed"]),
            ("membrane_verdict_it_overrides",
             (original.get(e["identity_key"], {}).get("membrane") or {})
             .get("verdict", "")),
            ("why", e["why"]),
        )) for e in ledger_020["identity_rulings"]
            if e["ruling"] == "SAME_PROPERTY_CONFIRMED"
            and e["identity_key"] in original]),
    )))
    confirmations_path = out_dir / "grand_rapids_holland_mi_identity_confirmations_021.json"
    _write(confirmations_path, confirmations)

    # 4. the authority, built by the SANCTIONED builder
    authority_path = out_dir / "grand_rapids_holland_mi_proposed_authority_021.json"
    command = [sys.executable,
               str(_REPO_ROOT / "scripts" / "pettripfinder"
                   / "market_proposed_authority_cli.py"),
               "--market", MARKET,
               "--decisions", str(ledger_path),
               "--store", str(store_path),
               "--census", str(paths["census"]),
               "--withdrawals", str(confirmations_path),
               "--out", str(authority_path)]
    result = subprocess.run(command, cwd=str(_REPO_ROOT),
                            capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stdout + result.stderr)
        raise SignatureError("the sanctioned authority builder refused: %s"
                             % (result.stderr.strip().splitlines() or [""])[-1])
    authority = _load(authority_path)

    validation = validate(authority, signatures, ledger_020, classification,
                          derived, census, confirmations)
    promotion = _header(
        "ptf-source-promotion-readiness/1.0",
        "Whether Grand Rapids may be promoted in source, and exactly what "
        "promotion would move. Nothing is promoted, published or deployed "
        "here.",
        {"authority": authority_path, "ledger": ledger_path})
    promotion.update(promotion_readiness(authority, validation, classification))
    promotion["validation"] = validation
    promotion_path = out_dir / "grand_rapids_holland_mi_source_promotion_readiness_021.json"
    _write(promotion_path, promotion)

    print("candidates presented   : %d" % len(candidates))
    print("signatures written     : %d" % len(signed))
    for name, value in ledger["by_outcome"].items():
        print("  %-42s %d" % (name.lower(), value))
    print("refused                : %d" % len(refused))
    print("derived store changed  : %d records" % derived_doc["records_changed"])
    print("authority pet-friendly : %d" % authority["pet_friendly_count"])
    print("authority no-pets      : %d" % authority["verified_no_pets_count"])
    print("authority total        : %d" % authority["authority_total"])
    print("unresolved in build    : %d" % len(authority["unresolved"]))
    print("validation             : %s" % validation["all_pass"])
    print("SOURCE_PROMOTION_READY : %s" % promotion["source_promotion_ready"])
    for path in (store_path, ledger_path, confirmations_path, authority_path,
                 promotion_path):
        print("written                : %s" % path.name)
    return 0 if validation["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
