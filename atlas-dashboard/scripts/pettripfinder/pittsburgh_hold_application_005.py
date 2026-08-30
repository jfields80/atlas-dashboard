# -*- coding: utf-8 -*-
"""PTF-PITTSBURGH-FOUNDER-HOLD-RESOLUTION-005 Phase 5 -- apply the founder's rulings.

    python -m scripts.pettripfinder.pittsburgh_hold_application_005
    python -m scripts.pettripfinder.pittsburgh_hold_application_005 --write

WHY THIS DOES NOT REUSE SYNC 004's ENTRY POINT
------------------------------------------------
``pittsburgh_hardened_sync_004`` refuses to run against a census that is not
exactly 96 rows. That assertion was TRUE and CORRECT for that order, which was
forbidden to add identities, and it is not weakened here: rewriting a completed
order's guard to admit work it legitimately refused would make its own record
dishonest. This order carries its own guard instead -- the census must be the
96 it inherited PLUS exactly the identities its own census-add ledger names,
with all 96 preserved. Sync 004's record-building code is reused unchanged.

WHAT THE FOUNDER RULED
-----------------------
Six signed rows became applicable the moment their identities existed; they
carry their ORIGINAL 2026-08-26 signatures and are applied unchanged.

Three holds were ruled here, and their approval cites THIS order, not the
August signature, because the August packet withheld them:

  la quinta inn and suites pittsburgh airport   publish, full facts
  hampton inn and suites pittsburgh waterfront  publish, pet_fee WITHHELD
  courtyard  ->  courtyard by marriott pittsburgh monroeville   refuse

Two rows are corrections to authority that is already live:

  hilton garden inn pittsburgh university place  overlapping fee bands
  springhill suites pittsburgh airport           WITHDRAWN

THE WITHDRAWAL IS THE POINT OF THIS ORDER
-------------------------------------------
SpringHill Suites Pittsburgh Airport publishes as pet-friendly at $150 per
stay, cited from "Pets Welcome" captured 2026-08-17. The page captured
2026-08-23 -- same property, hash-bound, six days later -- says "Pets are not
allowed. Only service animals are welcome." alongside the same $150 line. The
current reader withholds ``pets_allowed`` as SOURCE_CONTRADICTORY and raises
FLAG_CONTRADICTS_OFFICIAL; it is not a parser defect, the surface really does
say both.

The founder ruled WITHDRAW pending re-capture: we stop asserting pet-friendly
on a page that denies it, and we do not assert the opposite from a surface that
contradicts itself either. The record is removed from the package and preserved
verbatim in the withdrawal ledger, which is what a later reader consults on
finding no profile. This is the one change here that REMOVES a live profile.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import hotel_exclusions as HE                  # noqa: E402
from scripts.pettripfinder import market_authority as MA                  # noqa: E402
from scripts.pettripfinder import policy_migration as PM                  # noqa: E402
from scripts.pettripfinder.contracts.fee_computation import classify   # noqa: E402
from scripts.pettripfinder.market_policy_package_cli import corrected_names  # noqa: E402
from scripts.pettripfinder.pittsburgh_hardened_sync_004 import (          # noqa: E402
    CENSUS, MARKET_ID, OBSERVATIONS, OVERLAY, PACKAGE, PUBLISH, REPORTS,
    Registry, SyncError, _load, _observations, _write, build_exclusion,
    build_record, signed_decisions)
from scripts.pettripfinder.pittsburgh_census_add_005 import LEDGER as ADD_LEDGER

WORK_ORDER = "PTF-PITTSBURGH-FOUNDER-HOLD-RESOLUTION-005"
AS_OF = "2026-08-30"
REVIEWER = "PTF-FOUNDER-001"
OPERATOR = "jfields80"
APPLICATION = REPORTS / "pittsburgh_hold_resolution_005_application.json"
WITHDRAWALS = REPORTS / "pittsburgh_hold_resolution_005_withdrawn_authority.json"

#: The holds the founder ruled PUBLISHABLE in this order. Each names the
#: REGISTERED identity the evidence binds to, and the basis for that binding.
HOLD_RULINGS = OrderedDict((
    ("la quinta inn and suites pittsburgh airport", OrderedDict((
        ("target", "la quinta inn and suites pittsburgh airport"),
        ("proposes_authority", "PUBLISHED_PET_FRIENDLY"),
        ("basis", "OFFICIAL_URL"),
        ("ruling",
         "APPROVE. The M10 membrane rejected on NAME alone -- the page states "
         "'La Quinta Inn by Wyndham Pittsburgh Airport', the census says 'La "
         "Quinta Inn & Suites Pittsburgh Airport'. But the registered census "
         "row's own official_url IS this exact page, so the census itself binds "
         "this identity to it, and the row carries no address or phone that "
         "could contradict. Re-located against the owned page under this order: "
         "no contradictions, no flags."),
    ))),
    ("hampton inn and suites pittsburgh waterfront", OrderedDict((
        ("target", "hampton inn and suites pittsburgh waterfront"),
        ("proposes_authority", "PUBLISHED_PET_FRIENDLY"),
        ("basis", "DIRECT"),
        ("ruling",
         "APPROVE the supported facts with the fee WITHHELD. The page shows "
         "$125 and $75 in a structure the reader will not bind to a pet "
         "(FLAG_TIER_STRUCTURE_REFUSED, FLAG_MULTI_POLICY_BLOCKS, "
         "FLAG_PET_AMOUNT_NOT_BOUND), so pet_fee stays withheld rather than "
         "quoting a price the source does not bind. A guest still learns pets "
         "are welcome, 40lb, 2 maximum. This market already publishes EVEN "
         "Hotel, The Westin and Hotel Indigo on exactly that basis."),
    ))),
    ("courtyard", OrderedDict((
        ("target", "courtyard by marriott pittsburgh monroeville"),
        ("proposes_authority", "VERIFIED_NO_PETS"),
        ("basis", "EXACT_CANONICAL_NAME+POSTAL"),
        ("ruling",
         "APPROVE as a refusal bound to the REGISTERED Monroeville identity, "
         "and retire the bare 'courtyard' recensus alias. The founder held this "
         "because renaming the bare key would collide with an existing "
         "canonical name; that is correct, and the answer is not to rename but "
         "to bind the evidence to the identity that already carries the name. "
         "The page is pitmr = Courtyard by Marriott Pittsburgh Monroeville, "
         "3962 William Penn Highway, postal 15146, and reads pets_allowed=false. "
         "RECORDED LIMITATION: the registered row is a bare stub with no URL, "
         "address or phone, so this binding rests on exact canonical-name "
         "equality plus postal agreement, not on a hard signal."),
    ))),
))

#: Holds closed without an authority change.
RECORDS_ONLY = OrderedDict((
    ("hilton garden inn",
     "SAFE_MERGE confirmed by hard proof: the held page IS pitfagi, the same "
     "official URL the published Hilton Garden Inn Pittsburgh Downtown record "
     "already cites. The merge target is already published with the same facts, "
     "so this retires a degraded recensus alias and changes no profile."),
    ("courtyard by marriott pittsburgh university center",
     "RETIRED_STALE_TWIN, already superseded: the registered identity of this "
     "name was published by PTF-PITTSBURGH-HARDENED-SYNC-004 via its qualified "
     "successor. Records only; it matters at the next census promotion."),
    ("hampton inn university center",
     "RETIRED_STALE_TWIN, already superseded by 'hampton inn pittsburgh "
     "university medical center', applied by Sync 004. Records only."),
    ("intown suites extended stay pittsburgh pa",
     "DEFERRED by founder ruling. The identity re-located cleanly -- the policy "
     "block itself states 'No pets allowed at InTown Suites Pittsburgh PA', so "
     "the generic page title that tripped M10 is not the property's own name -- "
     "but it carries no prior founder signature on a Pittsburgh identity, so "
     "adding it would be a new candidate rather than signed work."),
))

#: The one live profile this order removes.
WITHDRAWN = "springhill suites pittsburgh airport"

#: The one live profile this order corrects, and the band that replaces the
#: overlapping one. Read from the owned 2026-08-23 capture of the same page.
BAND_FIX = OrderedDict((
    ("identity_key", "hilton garden inn pittsburgh university place"),
    ("replace_index", 1),
    ("condition_min", 5),
    ("why",
     "The published tiers were 1..4 nights at $75 and 4..inf at $125, so a "
     "four-night stay carried two different published prices -- the only "
     "overlapping bands among the published records. The owned 2026-08-23 "
     "capture of the same page reads the second band as starting at 5 nights. "
     "Only condition_min moves; both amounts, both bases and the first band are "
     "untouched."),
))


class ApplicationError(RuntimeError):
    pass


def _hold_signature(key: str, ruling: Mapping, observation: Mapping) -> Dict:
    """A signature block for a row THIS order's founder ruled, not August's."""
    source = observation["observation"]
    return OrderedDict((
        ("identity_key", key),
        ("reviewed_disposition",
         "APPROVE_PET_FRIENDLY" if ruling["proposes_authority"] == PUBLISH
         else "APPROVE_VERIFIED_NO_PETS"),
        ("founder_decision", "APPROVED_AFTER_CURRENT_REVIEW"),
        ("founder_reviewer_id", REVIEWER),
        ("founder_reviewed_at", AS_OF),
        ("signed_by_work_order", WORK_ORDER),
        ("proposes_authority", ruling["proposes_authority"]),
        ("bound_source_url", source.get("source_url")),
        ("bound_snapshot_hash", source.get("snapshot_hash")),
        ("canonical_name", observation.get("canonical_name")),
        ("brand", observation.get("brand")),
    ))


def _withhold_unstated_cap(record: Dict, observation: Mapping) -> Dict:
    """A fee cap the schema cannot publish without a flag the source never wrote.

    ``fee_cap.qualifier_stated`` is REQUIRED and is never inferred, because
    ``_check_cap`` exists after a cap whose quote named a pet count and whose
    structure lost it published a ceiling the hotel never quoted. La Quinta's
    page reads "Non-refundable 25 USD nightly for up to 2 pets. Max 75 USD per
    stay." -- and whether "for up to 2 pets" qualifies the CAP as well as the
    nightly rate is exactly the ambiguity the flag refuses to guess.

    Setting it false would be applying PTF-ST-LOUIS-PUBLICATION-SCHEMA-
    DECISIONS-010's Founder Decision 3, which is ANOTHER market's publication
    ruling. So the cap is withheld and the nightly fee publishes.

    This is deliberately the CONSERVATIVE error and it is not free: a guest sees
    $25 per night and not the $75 ceiling, so the cost reads HIGHER than it is.
    That is recorded here and raised in the report as a founder question rather
    than silently resolved either way.
    """
    facts = record.get("facts") or {}
    if "fee_cap" not in facts:
        return record
    refs = [e["evidence_ref"] for e in record["evidence"]
            if e.get("field") in ("fee_cap", "pet_fee")]
    if not refs:
        raise ApplicationError("%s: no evidence backs the withheld cap"
                               % record["identity_key"])
    rebuilt = OrderedDict((k, v) for k, v in record.items() if k != "approval")
    rebuilt["facts"] = OrderedDict((k, v) for k, v in facts.items()
                                   if k != "fee_cap")
    withheld = OrderedDict(record.get("withheld_fields") or {})
    withheld["fee_cap"] = OrderedDict((
        ("reason_code", "SCHEMA_CANNOT_REPRESENT"),
        ("reason",
         "The page states 'Max 75 USD per stay' beside a nightly rate quoted "
         "'for up to 2 pets'. fee_cap requires an explicit qualifier_stated "
         "boolean that is never inferred, and whether the pet count qualifies "
         "the cap as well as the rate is not settled by the source. The cap is "
         "withheld rather than published with an invented flag; the nightly "
         "fee publishes unchanged."),
        ("evidence_refs", refs[:1]),
    ))
    rebuilt["withheld_fields"] = withheld
    rebuilt["computation_class"] = classify(rebuilt["facts"]).computation_class
    out = OrderedDict(rebuilt)
    approval = OrderedDict(record["approval"])
    approval["caveats"] = list(approval.get("caveats") or []) + [
        "FEE CAP WITHHELD: the $75 per-stay ceiling this page states is not "
        "published, because fee_cap.qualifier_stated is required and never "
        "inferred. A guest therefore sees the $25 nightly rate without the "
        "ceiling, which reads HIGHER than the true cost. Raised for founder "
        "ruling in %s." % WORK_ORDER]
    approval["record_hash"] = PM.record_hash(out)
    approval["evidence_hash"] = PM.evidence_hash(out["evidence"])
    out["approval"] = approval
    return out


def _row(key: str, target: str, basis: str, disposition: str) -> Dict:
    return OrderedDict((("signed_identity_key", key),
                        ("registered_identity_key", target),
                        ("basis", basis),
                        ("proposes_authority", disposition),
                        ("retires_stale_twin", None)))


def _added_identities() -> Tuple[str, ...]:
    if not ADD_LEDGER.is_file():
        return ()
    return tuple(a["identity_key"] for a in _load(ADD_LEDGER)["adds"])


def build():
    census_doc = _load(CENSUS)
    census = {h["identity_key"]: h for h in census_doc["hotels"]}
    added = _added_identities()
    # This order's own guard: the 96 Sync 004 left, plus exactly the identities
    # this order's census-add ledger names, with every one of the 96 preserved.
    if len(census) != 96 + len(added):
        raise ApplicationError(
            "census is %d rows; expected the inherited 96 plus %d recorded adds"
            % (len(census), len(added)))
    for key in added:
        if key not in census:
            raise ApplicationError("%s was added but is not in the census" % key)

    registry = Registry(census_doc["hotels"])
    corrected = corrected_names(_load(OVERLAY) if OVERLAY.is_file() else None)
    obs = _observations()
    signed = signed_decisions()
    package = _load(PACKAGE)
    published = {h["identity_key"] for h in package["hotels"]}
    shard = MA.load_market_exclusions_document(MARKET_ID)
    excluded = {e["normalized_name"] for e in shard["exclusions"]}

    records: List[Dict] = []
    exclusions: List[Dict] = []
    applied: List[Dict] = []

    # -- the six August signatures, now that their identities exist ---------- #
    for key in added:
        decision = signed[key]
        row = _row(key, key, "DIRECT", decision["proposes_authority"])
        observation = obs[key]
        if decision["proposes_authority"] == PUBLISH:
            records.append(build_record(row, decision, observation,
                                        census[key], corrected))
        else:
            exclusions.append(build_exclusion(row, decision, observation,
                                              census[key], corrected))
        applied.append(OrderedDict((
            ("identity_key", key), ("outcome", "APPLIED_CENSUS_ADD"),
            ("disposition", decision["proposes_authority"]),
            ("authority", decision["signed_by_work_order"]))))

    # -- the three holds the founder ruled publishable here ------------------ #
    for key, ruling in HOLD_RULINGS.items():
        target = ruling["target"]
        if target not in census:
            raise ApplicationError("%s is not a registered identity" % target)
        observation = obs.get(key)
        if observation is None:
            raise ApplicationError("%s has no owned observation" % key)
        signature = _hold_signature(key, ruling, observation)
        signature["founder_note"] = ruling["ruling"]
        row = _row(key, target, ruling["basis"], ruling["proposes_authority"])
        if ruling["proposes_authority"] == PUBLISH:
            record = build_record(row, signature, observation,
                                  census[target], corrected)
            record = _withhold_unstated_cap(record, observation)
            records.append(record)
        else:
            exclusions.append(build_exclusion(row, signature, observation,
                                              census[target], corrected))
        applied.append(OrderedDict((
            ("identity_key", target), ("from_held_row", key),
            ("outcome", "APPLIED_FOUNDER_HOLD_RULING"),
            ("disposition", ruling["proposes_authority"]),
            ("basis", ruling["basis"]), ("authority", WORK_ORDER))))

    keys = [r["identity_key"] for r in records]
    ex_keys = [e["normalized_name"] for e in exclusions]
    if len(set(keys)) != len(keys) or len(set(ex_keys)) != len(ex_keys):
        raise ApplicationError("this order would write one identity twice")
    if set(keys) & set(ex_keys):
        raise ApplicationError("an identity would be published AND excluded")
    if set(keys) & published or set(ex_keys) & excluded:
        raise ApplicationError("this order would re-apply an existing decision")

    # -- the correction and the withdrawal ----------------------------------- #
    hotels = [copy.deepcopy(h) for h in package["hotels"]]
    withdrawn = [h for h in hotels if h["identity_key"] == WITHDRAWN]
    if len(withdrawn) != 1:
        raise ApplicationError("%s is not published; nothing to withdraw"
                               % WITHDRAWN)
    hotels = [h for h in hotels if h["identity_key"] != WITHDRAWN]

    fixed = None
    for hotel in hotels:
        if hotel["identity_key"] != BAND_FIX["identity_key"]:
            continue
        tiers = hotel["facts"].get("fee_tiers") or []
        index = BAND_FIX["replace_index"]
        if len(tiers) <= index:
            raise ApplicationError("%s has no band %d"
                                   % (hotel["identity_key"], index))
        before_min = tiers[index].get("condition_min")
        first_max = tiers[index - 1].get("condition_max")
        if first_max is None or before_min is None or before_min > first_max:
            raise ApplicationError(
                "%s bands no longer overlap; this correction was written "
                "against an overlap and must not run blind"
                % hotel["identity_key"])
        prior_hash = hotel["approval"]["record_hash"]
        prior_evidence = hotel["approval"]["evidence_hash"]
        tiers[index]["condition_min"] = BAND_FIX["condition_min"]
        # Removing the overlap changes what the fee schedule computes to --
        # overlapping bands are NOT_COMPUTABLE by construction. The stored
        # class must follow the facts or validate_migrated refuses.
        prior_class = hotel.get("computation_class")
        hotel["computation_class"] = classify(hotel["facts"]).computation_class
        if PM.evidence_hash(hotel["evidence"]) != prior_evidence:
            raise ApplicationError("the band fix moved an evidence hash")
        hotel["approval"]["record_hash"] = PM.record_hash(
            {k: v for k, v in hotel.items() if k != "approval"})
        hotel["approval"]["rebinding"] = OrderedDict((
            ("work_order", WORK_ORDER),
            ("changed", ["facts.fee_tiers[%d].condition_min" % index,
                         "computation_class"]),
            ("from_computation_class", prior_class),
            ("to_computation_class", hotel["computation_class"]),
            ("from_condition_min", before_min),
            ("to_condition_min", BAND_FIX["condition_min"]),
            ("prior_record_hash", prior_hash),
            ("evidence_hash_unchanged", True),
            ("note", BAND_FIX["why"]),
        ))
        fixed = OrderedDict((("identity_key", hotel["identity_key"]),
                             ("from_condition_min", before_min),
                             ("to_condition_min", BAND_FIX["condition_min"]),
                             ("prior_record_hash", prior_hash)))
    if fixed is None:
        raise ApplicationError("%s is not published; nothing to correct"
                               % BAND_FIX["identity_key"])

    package["hotels"] = hotels + records
    problems = PM.validate_migrated(package)
    if problems:
        raise ApplicationError("the package does not validate: %s" % problems[:6])
    shard["exclusions"] = list(shard["exclusions"]) + exclusions
    shard["count"] = len(shard["exclusions"])
    HE.validate(shard)

    report = OrderedDict((
        ("schema", "ptf-market-founder-decisions/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("as_of", AS_OF),
        ("operator", OPERATOR),
        ("provider_calls", 0),
        ("usd_spent", 0.0),
        ("census_adds_applied", len(added)),
        ("holds_ruled_publishable", len(HOLD_RULINGS)),
        ("holds_closed_records_only", len(RECORDS_ONLY)),
        ("records_added", len(records)),
        ("exclusions_added", len(exclusions)),
        ("records_withdrawn", 1),
        ("records_corrected", 1),
        ("applied", applied),
        ("records_only", [OrderedDict((("identity_key", k), ("why", v)))
                          for k, v in RECORDS_ONLY.items()]),
        ("band_correction", fixed),
        ("withdrawal", OrderedDict((
            ("identity_key", WITHDRAWN),
            ("why", "The published record asserted pets_allowed=true from the "
                    "quote 'Pets Welcome' captured 2026-08-17. The owned "
                    "2026-08-23 capture of the same property page states 'Pets "
                    "are not allowed. Only service animals are welcome.' beside "
                    "the same $150 fee line. The current reader withholds "
                    "pets_allowed as SOURCE_CONTRADICTORY. Founder ruling: "
                    "WITHDRAW pending re-capture -- we stop asserting "
                    "pet-friendly on a page that denies it, and do not assert "
                    "the opposite from a self-contradictory surface."),
        ))),
    ))
    return package, shard, records, exclusions, withdrawn[0], report


def run(write: bool) -> int:
    package, shard, records, exclusions, withdrawn, report = build()
    print("census adds applied      : %d" % report["census_adds_applied"])
    print("holds ruled publishable  : %d" % report["holds_ruled_publishable"])
    print("holds closed records-only: %d" % report["holds_closed_records_only"])
    print("policy records added     : %d" % len(records))
    print("exclusions added         : %d" % len(exclusions))
    print("published record WITHDRAWN: %s" % withdrawn["identity_key"])
    print("published record corrected: %s" % report["band_correction"]["identity_key"])
    print("policy package after     : %d" % len(package["hotels"]))
    print("exclusion shard after    : %d" % shard["count"])
    if not write:
        print("(check only -- pass --write)")
        return 0

    _write(PACKAGE, package)
    print("WROTE %s (%d records)" % (PACKAGE.name, len(package["hotels"])))
    MA.exclusions_shard_path(MARKET_ID).write_text(
        MA.render_json(shard), encoding="utf-8", newline="\n")
    print("WROTE exclusions shard (%d rows)" % shard["count"])
    _write(WITHDRAWALS, OrderedDict((
        ("schema", "ptf-market-authority-withdrawal/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("as_of", AS_OF),
        ("why", report["withdrawal"]["why"]),
        ("what_is_preserved",
         "The withdrawn record verbatim, including its founder approval, its "
         "evidence array and both hashes. This is the artifact a later reader "
         "consults on finding no profile for this identity."),
        ("count", 1),
        ("withdrawn_records", [withdrawn]),
    )))
    print("WROTE %s" % WITHDRAWALS.name)
    _write(APPLICATION, report)
    print("WROTE %s" % APPLICATION.name)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        return run(args.write)
    except (ApplicationError, SyncError) as exc:
        print("REFUSED: %s" % exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
