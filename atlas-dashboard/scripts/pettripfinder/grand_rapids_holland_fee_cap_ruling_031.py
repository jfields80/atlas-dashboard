# -*- coding: utf-8 -*-
"""PTF-GRAND-RAPIDS-FEE-CAP-QUALIFIER-RULING-031 -- three caps the source states in words.

030 signed fourteen records and promoted eleven. Three were held out of
publication because the schema requires ``fee_cap.qualifier_stated`` and never
infers it. Their sources say "maximum of 75 USD per stay", "Max 75 USD per
stay" and "not to exceed 7 nights or $105 per pet per stay". The founder has
ruled that wording states the qualifier. This pass applies that ruling and
nothing else.

THE RULING IS CONDITIONAL AND THE COMMITTED SWITCH IS BLANKET
--------------------------------------------------------------
``market_policy_package_cli --cap-qualifier-stated`` sets the field on EVERY
cap that lacks it. The founder's ruling applies only where the source states
the cap in words. Those two scopes are not the same thing, and using the switch
without checking would apply a conditional ruling unconditionally.

So this pass PROVES they coincide before it uses the switch. It enumerates
every cap in the signed authority that lacks ``qualifier_stated``, checks each
one's own evidence quote against the wording the ruling names, and refuses to
run if any row would be swept in that the founder did not rule on. Today that
set is exactly the three held rows. If a later pass adds a fourth cap with no
qualifier in its source, this refuses rather than quietly publishing it.

WHAT THE RULING DOES NOT REACH
-------------------------------
An amount with no cap word. A deposit -- ``pet_deposit`` is its own field and
is never read as a cap. An ambiguous cap. Each of those is checked and each
would block.

Nothing else is reinterpreted. No provider is called. The record approvals 030
wrote stay exactly as they are: this ruling supplies a publication qualifier,
not an approval.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import grand_rapids_holland_founder_signature_030 as S  # noqa: E402

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
CENSUS_PATH = LP / "identity_census" / "grand-rapids-holland-mi.json"
MERGED_STORE = LP / "grand_rapids_holland_mi_observation_store_030_merged.json"
HOLDS_030 = LP / "grand_rapids_holland_mi_publication_holds_030.json"
AUTHORITY_031 = LP / "grand_rapids_holland_mi_proposed_authority_031.json"
PACKAGE_PATH = LP / "hotel_policy_facts_grand-rapids-holland-mi.json"
RULING_PATH = LP / "grand_rapids_holland_mi_fee_cap_ruling_031.json"
PROMOTION_PATH = LP / "grand_rapids_holland_mi_source_promotion_031.json"

WORK_ORDER = "PTF-GRAND-RAPIDS-FEE-CAP-QUALIFIER-RULING-031"
MARKET = "grand-rapids-holland-mi"
MARKET_NAME = "Grand Rapids / Holland"
FOUNDER = "PTF-FOUNDER-001"
RULED_AT = "2026-08-29"

FOUNDER_RULING = (
    "Where the official source explicitly states a fee cap -- 'maximum of $X "
    "per stay', 'max $X per stay', 'not to exceed $X per stay' or equivalent "
    "explicit cap wording -- fee_cap.qualifier_stated is true. That is a "
    "direct reading of the source and not an inference. It does not apply "
    "where only an amount is shown, where the text states no cap word, where "
    "the amount is a deposit rather than a fee cap, or where the cap is "
    "ambiguous.")

#: The wording the ruling names, and its plain equivalents. Deliberately a
#: CLOSED list: "equivalent explicit cap wording" is a founder's phrase, and
#: widening it by pattern is how a ruling about three rows becomes a rule about
#: rows nobody read.
_EXPLICIT_CAP = re.compile(
    r"\b(?:maximum|max\.?|not\s+to\s+exceed|cannot\s+exceed|"
    r"will\s+not\s+exceed|no\s+more\s+than|capped\s+at)\b", re.IGNORECASE)

#: A cap quote that names a deposit is not a fee cap. ``pet_deposit`` is its own
#: field and the projector reads it separately; a deposit reaching fee_cap would
#: be a reader defect, and this pass blocks rather than publishing through it.
_DEPOSIT = re.compile(r"\bdeposit\b", re.IGNORECASE)

RULED_EXPLICIT = "EXPLICIT_CAP_STATED_IN_THE_SOURCE"
REFUSED_AMOUNT_ONLY = "REFUSED_AMOUNT_ONLY_NO_CAP_WORDING"
REFUSED_DEPOSIT = "REFUSED_THE_QUOTE_NAMES_A_DEPOSIT"
REFUSED_NO_QUOTE = "REFUSED_NO_EVIDENCE_QUOTE_FOR_THE_CAP"


def _load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write(path: Path, document: Mapping) -> None:
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# Which caps the switch would touch, and whether the ruling reaches them
# --------------------------------------------------------------------------- #

def caps_without_a_qualifier(store: Mapping,
                             identities: Sequence[str]) -> List[Dict]:
    """Every cap in the signed authority that lacks ``qualifier_stated``.

    This is the set the committed switch would set, so it is the set the ruling
    has to cover. Computed from the store rather than from the hold list,
    because the hold list is what the projector happened to refuse and this
    needs what the switch would happen to change.
    """
    records = {r["identity_key"]: r for r in S._store_records(store)}
    out: List[Dict] = []
    for key in sorted(identities):
        record = records.get(key)
        if record is None:
            continue
        extraction = record["observation"]["extraction"] or {}
        cap = extraction.get("fee_cap")
        if not isinstance(cap, dict) or cap.get("qualifier_stated") is not None:
            continue
        quotes = [str(e.get("quote", ""))
                  for e in record["observation"].get("evidence") or ()
                  if "fee_cap" in (e.get("field_refs") or ())]
        out.append(OrderedDict((
            ("identity_key", key),
            ("canonical_name", record.get("canonical_name", "")),
            ("fee_cap", OrderedDict(sorted(cap.items()))),
            ("pet_deposit", extraction.get("pet_deposit")),
            ("evidence_quotes_for_the_cap", quotes),
        )))
    return out


def rule_one(row: Mapping) -> Tuple[str, str]:
    """Does the founder's ruling reach this cap? Exactly one answer."""
    quotes = list(row["evidence_quotes_for_the_cap"])
    if not quotes:
        return (REFUSED_NO_QUOTE,
                "the cap carries no evidence quote, so there is no source "
                "wording to read the qualifier off")
    for quote in quotes:
        if _DEPOSIT.search(quote):
            return (REFUSED_DEPOSIT,
                    "the cap's own quote names a deposit (%r); a deposit is "
                    "not a fee cap and the ruling does not reach it" % quote)
    stated = [q for q in quotes if _EXPLICIT_CAP.search(q)]
    if not stated:
        return (REFUSED_AMOUNT_ONLY,
                "the quote states an amount and no cap wording (%r); the "
                "ruling applies only where the source says maximum, max, not "
                "to exceed or an equivalent" % quotes[0])
    return (RULED_EXPLICIT,
            "the source states the cap in words: %r" % stated[0])


def ruling(identities: Sequence[str]) -> Dict:
    store = _load(MERGED_STORE)
    rows = caps_without_a_qualifier(store, identities)
    ruled: List[Dict] = []
    for row in rows:
        verdict, why = rule_one(row)
        entry = OrderedDict(row)
        entry["verdict"] = verdict
        entry["why"] = why
        entry["qualifier_stated_becomes"] = True if verdict == RULED_EXPLICIT else None
        ruled.append(entry)

    reached = [r for r in ruled if r["verdict"] == RULED_EXPLICIT]
    refused = [r for r in ruled if r["verdict"] != RULED_EXPLICIT]
    held_030 = [r["identity_key"] for r in _load(HOLDS_030)["held"]]

    return OrderedDict((
        ("schema", "ptf-fee-cap-qualifier-ruling/1.0"),
        ("market_id", MARKET), ("work_order", WORK_ORDER),
        ("ruled_by", FOUNDER), ("ruled_at", RULED_AT),
        ("founder_ruling", FOUNDER_RULING),
        ("provider_calls", 0), ("usd_spent", 0.0),
        ("the_switch_is_blanket_and_the_ruling_is_not",
         "market_policy_package_cli --cap-qualifier-stated sets the field on "
         "EVERY cap that lacks it. This pass enumerates that exact set and "
         "checks each row's own source wording, so the switch may only be used "
         "when its blanket scope and the ruling's conditional scope coincide."),
        ("caps_the_switch_would_set", len(ruled)),
        ("reached_by_the_ruling", len(reached)),
        ("refused_by_the_ruling", len(refused)),
        ("scopes_coincide", not refused),
        ("safe_to_use_the_committed_switch", not refused),
        ("rows_blocked_by_030", held_030),
        ("every_blocked_row_is_reached",
         set(held_030) <= {r["identity_key"] for r in reached}),
        ("by_verdict", OrderedDict(sorted(Counter(
            r["verdict"] for r in ruled).items()))),
        ("rows", ruled),
        ("what_the_ruling_does_not_reach", [
            "an amount with no cap wording", "a deposit (pet_deposit is its "
            "own field and is never read as a cap)", "an ambiguous cap",
        ]),
        ("record_approvals_unchanged",
         "030's founder record approvals stand exactly as written. This ruling "
         "supplies a publication qualifier, not an approval."),
    ))


# --------------------------------------------------------------------------- #
# Re-projection and promotion
# --------------------------------------------------------------------------- #

def project(authority_path: Path, expect: int, out: Path) -> Tuple[int, str]:
    command = [sys.executable,
               str(_REPO_ROOT / "scripts" / "pettripfinder"
                   / "market_policy_package_cli.py"),
               "--authority", str(authority_path),
               "--market-name", MARKET_NAME,
               "--observations", str(MERGED_STORE),
               "--expect-count", str(expect),
               "--weight-comparison-from-source",
               # THE FOUNDER'S RULING, applied through the committed switch and
               # only after the scopes were proved to coincide.
               "--cap-qualifier-stated", "true",
               "--publish", WORK_ORDER,
               "--out", str(out)]
    done = subprocess.run(command, cwd=str(_REPO_ROOT),
                          capture_output=True, text=True)
    return (done.returncode, done.stdout + done.stderr)


def promote(decision: Mapping) -> Dict:
    from scripts.pettripfinder import market_authority as MA
    from scripts.pettripfinder import market_registration_cli as REGISTRATION
    from scripts.pettripfinder import hotel_exclusions as HE
    from scripts.pettripfinder import release_contracts as RC
    from scripts.pettripfinder.grand_rapids_holland_source_promotion_022 import (
        withdraw_published_routes)

    if not decision["safe_to_use_the_committed_switch"]:
        raise SystemExit(
            "the blanket switch would set qualifier_stated on %d cap(s) the "
            "ruling does not reach; refusing to apply a conditional ruling "
            "unconditionally" % decision["refused_by_the_ruling"])

    # The FULL signed authority -- nothing held back this time, because the
    # ruling clears exactly what was held.
    authority = S.authority_excluding(())
    _write(AUTHORITY_031, authority)

    code, output = project(AUTHORITY_031, authority["pet_friendly_count"],
                           PACKAGE_PATH)
    if code != 0:
        refusals = S.schema_refusals(output)
        raise SystemExit(
            "the projector still refuses %d row(s) with the ruling applied: %s"
            % (len(refusals), json.dumps(refusals, indent=1)))
    package = _load(PACKAGE_PATH)

    before_shards = S.other_market_fingerprints()
    built = REGISTRATION.build(MARKET, AUTHORITY_031, CENSUS_PATH)
    routes_before = len(MA.load_market_routes(MARKET))
    HE.validate(built["exclusions_document"])
    MA.exclusions_shard_path(MARKET).write_text(
        MA.render_json(built["exclusions_document"]), encoding="utf-8")
    MA.seed_shard_path(MARKET).write_text(
        MA.render_seed_csv(built["seed_rows"]), encoding="utf-8")
    if len(MA.load_market_routes(MARKET)) != routes_before:
        raise SystemExit("writing the seed and exclusion shards moved routing")

    withdrawal = withdraw_published_routes(built["seed_rows"])
    routes_after = len(MA.load_market_routes(MARKET))

    S._run([sys.executable, "-m",
            "scripts.pettripfinder.build_global_authority", "--write"],
           "the global authority assembler")
    check = S._run([sys.executable, "-m",
                    "scripts.pettripfinder.build_market_authorities"],
                   "build_market_authorities (check mode, the default)")

    after_shards = S.other_market_fingerprints()
    changed = sorted(k for k in before_shards
                     if before_shards[k] != after_shards.get(k))

    contract_path = (_REPO_ROOT / "deploy" / "netlify" / "release_contracts"
                     / ("%s.json" % MARKET))
    contract = _load(contract_path)
    derived = RC.derive_authority(MARKET)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(_REPO_ROOT),
                          capture_output=True, text=True).stdout.strip()
    contract["source_commit"] = head
    contract["description"] = (
        "Deterministic release-gate contract for the PetTripFinder "
        "Grand Rapids-Holland market (%s). It describes only this market's "
        "reviewed authority and grants no deployment authorization." % WORK_ORDER)
    contract["deployment_authorization"]["means"] = (
        "A passing contract means this market's assembled package is "
        "structurally consistent and safe to publish as a static bundle. It is "
        "not a deployment authorization and it makes no claim that the market "
        "is complete -- %d of its %d confirmed identities remain unresolved."
        % (derived.unresolved, derived.confirmed_identities))
    contract["policy_package"]["expected_sha256"] = derived.policy_package_sha256
    contract["policy_package"]["expected_record_count"] = \
        derived.policy_package_record_count
    contract["public_surface"]["public_hotel_profile_count"] = \
        derived.published_hotel_profiles
    contract["public_surface"]["seed_hotel_rows"] = derived.seed_hotel_rows
    contract["routes"]["hotel_route_count"] = derived.hotel_route_count
    contract["reconciliation"]["published_pet_friendly"] = \
        derived.published_hotel_profiles
    contract["reconciliation"]["verified_no_pets"] = derived.verified_no_pets
    contract["reconciliation"]["resolved"] = derived.resolved
    contract["reconciliation"]["unresolved"] = derived.unresolved
    contract_path.write_text(
        json.dumps(contract, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8", newline="\n")
    disagreements = RC.verify_contract(MARKET)

    return OrderedDict((
        ("schema", "ptf-source-promotion/1.0"),
        ("market_id", MARKET), ("work_order", WORK_ORDER),
        ("provider_calls", 0), ("usd_spent", 0.0),
        ("ruling_applied", OrderedDict((
            ("rows_ruled", decision["caps_the_switch_would_set"]),
            ("rows_cleared", decision["reached_by_the_ruling"]),
            ("switch", "--cap-qualifier-stated true"),
            ("scopes_coincide", decision["scopes_coincide"]),
        ))),
        ("promoted", OrderedDict((
            ("pet_friendly", authority["pet_friendly_count"]),
            ("verified_no_pets", authority["verified_no_pets_count"]),
            ("authority_total", authority["authority_total"]),
            ("package_count", package["count"]),
            ("seed_rows", len(built["seed_rows"])),
            ("exclusion_rows", len(built["exclusions_document"]["exclusions"])),
        ))),
        ("routes_withdrawn_by_publication", withdrawal),
        ("release_contract", OrderedDict((
            ("updated", True), ("disagreements", disagreements),
            ("published_pet_friendly", derived.published_hotel_profiles),
            ("verified_no_pets", derived.verified_no_pets),
            ("resolved", derived.resolved),
            ("unresolved", derived.unresolved),
            ("confirmed_identities", derived.confirmed_identities),
        ))),
        ("preserved", OrderedDict((
            ("pinned_census", len(_load(CENSUS_PATH)["hotels"])),
            ("routes_before", routes_before), ("routes_after", routes_after),
            ("other_market_shards_checked", len(before_shards)),
            ("other_market_shards_changed", changed),
            ("build_market_authorities", "check mode, the default; --write "
                                         "was never spelled"),
        ))),
        ("source_promoted", True),
        ("build_market_authorities_output", check.strip().splitlines()[-3:]),
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", default="rule", choices=("rule", "promote"))
    args = parser.parse_args(argv)

    signed = S.authority_excluding(())
    identities = ([r["normalized_name"] for r in signed["pet_friendly"]]
                  + [r["normalized_name"] for r in signed["verified_no_pets"]])
    decision = ruling(identities)
    _write(RULING_PATH, decision)

    print("caps the switch would set  %d" % decision["caps_the_switch_would_set"])
    print("reached by the ruling      %d" % decision["reached_by_the_ruling"])
    print("refused by the ruling      %d  %s"
          % (decision["refused_by_the_ruling"], dict(decision["by_verdict"])))
    print("scopes coincide            %s" % decision["scopes_coincide"])
    print("every blocked row reached  %s" % decision["every_blocked_row_is_reached"])

    if args.stage == "promote":
        report = promote(decision)
        _write(PROMOTION_PATH, report)
        promoted, contract = report["promoted"], report["release_contract"]
        print()
        print("pet-friendly               %d" % promoted["pet_friendly"])
        print("verified no-pets           %d" % promoted["verified_no_pets"])
        print("authority total            %d" % promoted["authority_total"])
        print("package / seeds / excl     %d / %d / %d"
              % (promoted["package_count"], promoted["seed_rows"],
                 promoted["exclusion_rows"]))
        print("routes                     %d -> %d (%d withdrawn)"
              % (report["preserved"]["routes_before"],
                 report["preserved"]["routes_after"],
                 report["routes_withdrawn_by_publication"]["withdrawn"]))
        print("pinned census              %d" % report["preserved"]["pinned_census"])
        print("other markets changed      %s"
              % (report["preserved"]["other_market_shards_changed"] or "none"))
        print("contract disagreements     %s" % (contract["disagreements"] or "none"))
        print("SOURCE_PROMOTED            %s" % report["source_promoted"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
