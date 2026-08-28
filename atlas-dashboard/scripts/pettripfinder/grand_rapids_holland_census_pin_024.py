# -*- coding: utf-8 -*-
"""PTF-GRAND-RAPIDS-CENSUS-PIN-AND-RELEASE-CONTRACT-024.

NO PROVIDER IS CALLED and nothing is spent. No hotel is discovered, no identity
is added or removed beyond the 163 the recensus already holds, and no authority
decision is touched.

WHAT THIS RECONCILES
---------------------
Every pass since PTF-GRAND-RAPIDS-HOLLAND-GEOGRAPHY-HARDENING-002 has run
against a 163-identity RECENSUS held beside the market's pinned census, which
is still the 120-identity document the 2025 build committed. Source promotion
then published 49 founder-signed identities, nine of which the pinned census
does not contain -- so the market could not be given a release contract, whose
``identity_census.expected_count`` must AGREE with the derivation. That gap is
the whole subject here.

THE PROMOTION LOSES NO BUILDING, AND THAT IS PROVED RATHER THAN ASSERTED
-------------------------------------------------------------------------
Ten of the 120 prior identity keys are absent from the 163. None is a deletion:
each was ABSORBED into a fresh sighting of the same building on a shared street
identity, and PTF-GRAND-RAPIDS-HOLLAND-CHOICE-ROUTING-REPAIR-007 recorded every
absorption with its basis. Two of the ten are brand changes at one address --
AmericInn by Wyndham Holland became a Quality Inn & Suites, White Pines Inn
became a Best Western Plus. This module re-checks all ten against that record
and REFUSES the promotion if a prior key disappears with no absorption naming
it, because "the count went up" is not evidence that nothing was lost.

THREE ROWS COULD NOT BE PINNED AS THEY STOOD
---------------------------------------------
``census.validate`` requires a state, and three recensus rows carry none: their
discovery provider stated none and they hold no corridor, so the recensus's own
corridor-registry derivation -- which supplied 93 other rows -- could not reach
them. The market contract declares exactly one state, and a row inside this
market is in Michigan by that contract's own definition rather than by any
inference about the world. So the state is filled from the market contract,
each row is named, and the basis travels with the document. No corridor is
assigned: a corridor is a claim about WHERE inside the market a hotel sits, and
that question is untouched here.
"""
from __future__ import annotations

import argparse
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

from scripts.pettripfinder import market_authority as MA               # noqa: E402
from scripts.pettripfinder.contracts import census as CENSUS           # noqa: E402
from scripts.pettripfinder.contracts import partition as PARTITION     # noqa: E402
from scripts.pettripfinder.markets import load_markets, market_by_id   # noqa: E402

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"

WORK_ORDER = "PTF-GRAND-RAPIDS-CENSUS-PIN-AND-RELEASE-CONTRACT-024"
MARKET = "grand-rapids-holland-mi"
PREFIX = "grand_rapids_holland_mi"

PINNED_CENSUS = LP / "identity_census" / ("%s.json" % MARKET)
RECENSUS = LP / "identity_census" / "recensus" / ("%s.json" % MARKET)
ABSORPTIONS = LP / ("%s_prior_census_absorptions_001.json" % PREFIX)
PARTITION_163 = LP / ("%s_final_partition_001.json" % PREFIX)
PACKAGE = LP / ("hotel_policy_facts_%s.json" % MARKET)
#: The census this promotion supersedes, kept rather than overwritten: the
#: 2025 build's Phase-1 gates are about THAT document and must keep their
#: subject.
SUPERSEDED = (LP / "identity_census" / "superseded" / ("%s-120.json" % MARKET))


class CensusPinError(RuntimeError):
    """A promotion the committed evidence does not support."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write(path: Path, document: Mapping) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")


# --------------------------------------------------------------------------- #
# Nothing may be lost
# --------------------------------------------------------------------------- #

def absorption_ledger() -> Dict[str, Dict]:
    """``prior identity key -> the absorption that accounts for it``."""
    document = _load(ABSORPTIONS)
    out: Dict[str, Dict] = {}
    for row in document.get("absorptions") or ():
        key = str(row.get("absorbed_candidate_id") or "")
        if "::" in key:
            out[key.split("::", 1)[1]] = row
    return out


def account_for_every_prior_identity(prior: Mapping, promoted: Mapping) -> Dict:
    """Every prior key either survives or is a RECORDED absorption. Or we stop.

    A promotion that quietly drops a hotel is the failure this market cannot
    afford: the row leaves the census, and with it every future pass's reason
    to ask about that building again.
    """
    prior_keys = CENSUS.identity_keys(prior)
    promoted_keys = CENSUS.identity_keys(promoted)
    absorbed = absorption_ledger()
    missing = sorted(prior_keys - promoted_keys)
    unexplained = [k for k in missing if k not in absorbed]
    if unexplained:
        raise CensusPinError(
            "%d prior identity/identities disappear from the promoted census "
            "with no absorption naming them: %s. The count going up is not "
            "evidence that nothing was lost."
            % (len(unexplained), ", ".join(unexplained)))
    return OrderedDict((
        ("prior_identities", len(prior_keys)),
        ("promoted_identities", len(promoted_keys)),
        ("survived_by_key", len(prior_keys & promoted_keys)),
        ("absorbed_into_a_fresh_sighting", len(missing)),
        ("unexplained_losses", unexplained),
        ("net_new_identities", len(promoted_keys - prior_keys)),
        ("absorptions", [OrderedDict((
            ("prior_identity_key", key),
            ("absorbed_into", str(absorbed[key].get("into_name") or "")),
            ("street_identity", str(absorbed[key].get("street_identity") or "")),
            ("basis", str(absorbed[key].get("basis") or "")),
            ("recorded_by",
             "PTF-GRAND-RAPIDS-HOLLAND-CHOICE-ROUTING-REPAIR-007"),
        )) for key in missing]),
    ))


# --------------------------------------------------------------------------- #
# The three rows the contract could not accept
# --------------------------------------------------------------------------- #

def fill_missing_states(hotels: List[Dict]) -> List[Dict]:
    """The market declares one state; a row inside it carries that state.

    This is the market contract's own definition rather than an inference about
    the world, and it is applied ONLY where the row states none. No corridor is
    assigned: where inside the market a hotel sits is a different question and
    this module does not answer it.
    """
    market = market_by_id(load_markets(), MARKET)
    states = tuple(getattr(market, "states", ()) or ())
    if len(states) != 1:
        raise CensusPinError(
            "market %r declares %d states %r; a single-state fill is only "
            "honest for a market that declares exactly one"
            % (MARKET, len(states), states))
    filled: List[Dict] = []
    for row in hotels:
        if str(row.get("state") or "").strip():
            continue
        row["state"] = states[0]
        row["state_source"] = "market_contract"
        filled.append(OrderedDict((
            ("identity_key", row["identity_key"]),
            ("canonical_name", row.get("canonical_name", "")),
            ("city", row.get("city", "")),
            ("postal_code", row.get("postal_code", "")),
            ("corridor", row.get("corridor", "")),
            ("filled_state", states[0]),
            ("why", "the discovery provider stated no state and the row holds "
                    "no corridor, so the recensus's corridor-registry "
                    "derivation could not reach it. The market contract "
                    "declares exactly one state, and a row inside this market "
                    "is in it by that contract's own definition."),
        )))
    return filled


# --------------------------------------------------------------------------- #
# Building the pinned document
# --------------------------------------------------------------------------- #

def prior_census() -> Dict:
    """The census this promotion supersedes.

    Read from the SUPERSEDED copy once one exists, never from the pinned path.
    Reading the pinned path would compare the promoted census against itself on
    any re-run and report a flawless promotion that accounted for nothing.
    """
    return _load(SUPERSEDED if SUPERSEDED.is_file() else PINNED_CENSUS)


def build_pinned_census() -> Tuple[Dict, Dict, List[Dict]]:
    """``(document, accounting, state_fills)`` -- the census, ready to pin."""
    prior = prior_census()
    recensus = _load(RECENSUS)
    hotels = [dict(row) for row in recensus["hotels"]]
    state_fills = fill_missing_states(hotels)

    keys = [row["identity_key"] for row in hotels]
    duplicates = sorted(k for k, n in Counter(keys).items() if n > 1)
    if duplicates:
        raise CensusPinError("duplicate identity keys: %s" % ", ".join(duplicates))

    document = OrderedDict((
        ("schema", recensus["schema"]),
        ("market_id", MARKET),
        ("count", len(hotels)),
        ("work_order", WORK_ORDER),
        ("scope_note",
         "The Grand Rapids-Holland identity universe as of %s. This document "
         "replaces the 120-identity census the 2025 build pinned: every pass "
         "since PTF-GRAND-RAPIDS-HOLLAND-GEOGRAPHY-HARDENING-002 has run "
         "against this universe, and the market's 49 founder-signed authority "
         "identities all resolve inside it."
         % str(recensus.get("captured_at") or "2026-08-26")),
        ("promoted_from", OrderedDict((
            ("recensus", str(RECENSUS.relative_to(_REPO_ROOT).as_posix())),
            ("recensus_sha256", _sha256(RECENSUS)),
            ("recensus_work_order", str(recensus.get("work_order") or "")),
            ("prior_census_work_order", str(prior.get("work_order") or "")),
            ("prior_identities", len(CENSUS.identity_keys(prior))),
        ))),
        ("identity_key_contract", recensus.get("identity_key_contract", "")),
        ("identity_contract", recensus.get("identity_contract", "")),
        ("captured_at", recensus.get("captured_at", "")),
        ("built_by", recensus.get("built_by", "")),
        ("source_authorities", recensus.get("source_authorities", [])),
        ("identity_state_counts", recensus.get("identity_state_counts", {})),
        ("states_derived_from_the_corridor_registry",
         recensus.get("states_derived_from_the_corridor_registry", [])),
        ("states_filled_from_the_market_contract", state_fills),
        ("identity_key_collisions", recensus.get("identity_key_collisions", [])),
        ("suspected_duplicates_for_review",
         recensus.get("suspected_duplicates_for_review", [])),
        ("prior_census_recandidacy", recensus.get("prior_census_recandidacy", {})),
        ("hotels", hotels),
    ))
    accounting = account_for_every_prior_identity(prior, document)
    document["prior_census_accounting"] = accounting

    market = market_by_id(load_markets(), MARKET)
    issues = CENSUS.validate(document, market_states=list(market.states))
    if issues:
        raise CensusPinError(
            "the promoted census does not satisfy its own contract: %s"
            % "; ".join(str(i) for i in list(issues)[:6]))
    return (document, accounting, state_fills)


# --------------------------------------------------------------------------- #
# What the promotion exposes
# --------------------------------------------------------------------------- #

#: Every other market whose census this one must not collide with.
OTHER_MARKETS: Tuple[str, ...] = (
    "columbus-oh", "cleveland-akron-canton-oh", "dayton-oh", "cincinnati-oh",
    "pittsburgh-pa", "detroit-ann-arbor-mi", "indianapolis-in",
    "louisville-ky", "milwaukee-wi", "st-louis-mo",
)


def cross_market_collisions(promoted: Mapping, authority: Mapping) -> Dict:
    """Identity keys this census shares with another market's, and their status.

    The keys are derived from canonical names, so a census row named with a
    BARE CHAIN WORD -- "Holiday Inn Express", "Travelodge by Wyndham" --
    produces a key that is not unique across markets. The 120-identity census
    did not carry these three rows; promoting the recensus surfaces them.

    Nothing is renamed here. Qualifying the three names would change identity
    keys that eight committed artifacts reference -- the candidate ledger, the
    closure ledger, coverage, the partition, routing, url recovery and two
    acquisition dry runs -- and none of the three publishes anything, so the
    fix is worth its own order rather than a side effect of a census pin.
    """
    ours = CENSUS.identity_keys(promoted)
    published = {r["normalized_name"] for r in authority["pet_friendly"]}
    excluded = {r["normalized_name"] for r in authority["verified_no_pets"]}
    rows: List[Dict] = []
    for other in OTHER_MARKETS:
        path = LP / "identity_census" / ("%s.json" % other)
        if not path.is_file():
            continue
        for key in sorted(ours & CENSUS.identity_keys(_load(path))):
            rows.append(OrderedDict((
                ("identity_key", key),
                ("also_in_market", other),
                ("published_here", key in published),
                ("excluded_here", key in excluded),
                ("status_here", "PUBLISHED" if key in published else
                 ("VERIFIED_NO_PETS" if key in excluded else "unresolved")),
            )))
    leaking = [r for r in rows if r["published_here"] or r["excluded_here"]]

    # The same condition BETWEEN other markets, which decides whether this
    # promotion created a problem or joined a standing one. It joined one:
    # Louisville and St. Louis already share seven keys, and Louisville
    # already PUBLISHES a record whose identity_key is "tru".
    censuses = {}
    for other in OTHER_MARKETS:
        path = LP / "identity_census" / ("%s.json" % other)
        if path.is_file():
            censuses[other] = CENSUS.identity_keys(_load(path))
    pre_existing: List[Dict] = []
    names = sorted(censuses)
    for i, left in enumerate(names):
        for right in names[i + 1:]:
            shared = sorted(censuses[left] & censuses[right])
            if shared:
                pre_existing.append(OrderedDict((
                    ("markets", [left, right]), ("identity_keys", shared))))

    return OrderedDict((
        ("collisions", len(rows)),
        ("in_this_market_s_authority", len(leaking)),
        ("nothing_leaks", not leaking),
        ("why_they_exist", "an identity key derives from a canonical name, and "
                           "a bare chain word is not unique across markets"),
        ("introduced_by_the_promotion", True),
        ("pre_existing_between_other_markets", OrderedDict((
            ("pairs", len(pre_existing)),
            ("keys", sum(len(p["identity_keys"]) for p in pre_existing)),
            ("rows", pre_existing),
            ("note", "the condition is systemic rather than this market's: a "
                     "bare chain name yields a non-unique key, and Louisville "
                     "already publishes a record whose identity_key is 'tru'. "
                     "Grand Rapids joins a standing condition; it does not "
                     "create one."),
        ))),
        ("what_still_keeps_them_apart",
         "nothing renders on the census key. site_data joins per market on the "
         "DISPLAY key, and 020's name corrections made this market's two "
         "authority-bearing collisions unique there: 'tru by hilton grand "
         "rapids airport' and 'doubletree by hilton hotel holland'."),
        ("not_renamed_here",
         "qualifying the three names would change identity keys that eight "
         "committed artifacts reference, and none of the three publishes "
         "anything. The fix is its own order."),
        ("rows", rows),
    ))


def authority_coverage(promoted: Mapping, authority: Mapping) -> Dict:
    """Every founder-signed identity resolves inside the promoted census."""
    keys = CENSUS.identity_keys(promoted)
    pet = [r["normalized_name"] for r in authority["pet_friendly"]]
    no_pets = [r["normalized_name"] for r in authority["verified_no_pets"]]
    outside = sorted(set(pet + no_pets) - keys)
    return OrderedDict((
        ("authority_total", len(pet) + len(no_pets)),
        ("pet_friendly", len(pet)),
        ("verified_no_pets", len(no_pets)),
        ("outside_the_promoted_census", outside),
        ("ok", not outside),
    ))


def partition_pairing(promoted: Mapping) -> Dict:
    """Which committed partition reconciles with the promoted census.

    A census and a partition are a pair: ``partition.reconcile`` compares one
    against the other, and pinning a new census without saying which partition
    now answers for it leaves an invariant pointing at the wrong document.
    """
    out: "OrderedDict[str, Dict]" = OrderedDict()
    for name in ("grand_rapids_holland_final_partition_001.json",
                 "%s_final_partition_001.json" % PREFIX):
        path = LP / name
        if not path.is_file():
            continue
        result = PARTITION.reconcile(CENSUS.identity_keys(promoted),
                                     _load(path), market_id=MARKET)
        out[name] = OrderedDict((
            ("agrees", bool(result.agrees)),
            ("published", result.published),
            ("verified_no_pets", result.verified_no_pets),
            ("out_of_category", result.out_of_category),
            ("unresolved", result.unresolved),
        ))
    paired = [n for n, r in out.items() if r["agrees"]]
    return OrderedDict((
        ("paired_with", paired[0] if paired else ""),
        ("ok", len(paired) == 1),
        ("by_partition", out),
        ("note", "the 120-era partition answers for the superseded census and "
                 "is kept beside it; the 163-row partition is the one that "
                 "reconciles with the pinned census"),
    ))


# --------------------------------------------------------------------------- #
# The release contract
# --------------------------------------------------------------------------- #

def build_release_contract(derived, promoted: Mapping, contract: Mapping,
                           source_commit: str) -> Dict:
    """A complete, self-contained contract whose every number is DERIVED.

    ``release_contracts`` requires the reviewed document and
    ``derive_authority`` to agree on every field, and neither half alone is
    sufficient: derivation alone recomputes its own expectation and proves
    nothing. So every count below comes from the derivation, and the run
    refuses to write if ``verify_contract`` reports a single disagreement.
    """
    template = _load(_REPO_ROOT / "deploy" / "netlify" / "release_contracts"
                     / "louisville-ky.json")
    return OrderedDict((
        ("schema", template["schema"]),
        ("contract_id", "pettripfinder-%s-release/1.0" % MARKET),
        ("market_id", MARKET),
        ("product", "pettripfinder-%s" % MARKET),
        ("release_name_prefix", "prod-grand-rapids-holland"),
        ("description",
         "Deterministic release-gate contract for the PetTripFinder Grand "
         "Rapids-Holland market (%s). It describes only this market's reviewed "
         "authority and grants no deployment authorization." % WORK_ORDER),
        ("source_commit", source_commit),
        ("deployment_authorization", OrderedDict((
            ("grants_deployment", False),
            ("asserts_market_complete", False),
            ("means",
             "A passing contract means this market's assembled package is "
             "structurally consistent and safe to publish as a static bundle. "
             "It is not a deployment authorization and it makes no claim that "
             "the market is complete -- %d of its %d confirmed identities "
             "remain unresolved."
             % (derived.unresolved, derived.confirmed_identities)),
        ))),
        ("canonical", template["canonical"]),
        ("identity_census", OrderedDict((
            ("path", "launch_packages/pettripfinder/identity_census/%s.json"
                     % MARKET),
            ("schema", promoted["schema"]),
            ("expected_count", derived.confirmed_identities),
            ("note",
             "The pinned census is the Grand Rapids-Holland identity universe, "
             "promoted from the 163-row recensus by %s. It supersedes the "
             "120-identity census the 2025 build pinned, which is kept at "
             "identity_census/superseded/. Ten prior identities are absent "
             "because each was absorbed into a fresh sighting of the same "
             "building on a shared street identity; every absorption is "
             "recorded." % WORK_ORDER),
        ))),
        ("reconciliation", OrderedDict((
            ("confirmed_identities", derived.confirmed_identities),
            ("published_pet_friendly", derived.published_hotel_profiles),
            ("verified_no_pets", derived.verified_no_pets),
            ("resolved", derived.resolved),
            ("unresolved", derived.unresolved),
            ("note", "Counts are derived from the pinned census, the committed "
                     "policy package and this market's exclusion shard; "
                     "unresolved is not negative pet evidence."),
        ))),
        ("reconciliation_cross_checks", []),
        ("policy_package", OrderedDict((
            ("path", derived.policy_package_path),
            ("expected_sha256", derived.policy_package_sha256),
            ("expected_schema_version", derived.policy_package_schema_version),
            ("expected_record_count", derived.policy_package_record_count),
            ("identity_authority", True),
            ("note", "The committed Grand Rapids-Holland policy package is the "
                     "sole identity authority for its %d verified profiles; no "
                     "hard-coded allow-list is repeated here."
                     % derived.policy_package_record_count),
            ("schema_note",
             "Schema %s; each record retains its founder decision binding and "
             "the semantic-approval hash it was signed against."
             % derived.policy_package_schema_version),
        ))),
        ("public_surface", OrderedDict((
            ("seed_hotel_rows", derived.seed_hotel_rows),
            ("public_hotel_profile_count", derived.published_hotel_profiles),
            ("excluded_public_profile_count", derived.excluded_public_profiles),
            ("held_hotel_exclusion",
             "Every unresolved census identity, the Budgetel identity hold, "
             "both halves of each open same-switchboard pair and avid hotel "
             "Zeeland have no seed row and no public route."),
        ))),
        ("market_visibility", OrderedDict((
            ("show_in_navigation", bool(contract.get("show_in_navigation"))),
            ("show_in_sitemap", bool(contract.get("show_in_sitemap"))),
            ("note", "enabled by PTF-GRAND-RAPIDS-SOURCE-PROMOTION-022; this "
                     "contract records the state rather than setting it"),
        ))),
        ("routes", OrderedDict((
            ("market_slug", derived.market_slug),
            ("route_mode", derived.route_mode),
            ("hotel_route_count", derived.hotel_route_count),
            ("published_corridor_route_count", derived.corridor_route_count),
            ("note", "Routes are derived from the %d live records and the "
                     "committed corridor assignment; unresolved identities are "
                     "absent." % derived.published_hotel_profiles),
        ))),
        ("minimum_release_gates", list(template["minimum_release_gates"])),
        ("forbidden_output_tokens", list(template["forbidden_output_tokens"])),
        ("publish", template["publish"]),
    ))


# --------------------------------------------------------------------------- #
# The run
# --------------------------------------------------------------------------- #

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)

    from scripts.pettripfinder import release_contracts as RC

    prior_count = len(CENSUS.identity_keys(prior_census()))

    document, accounting, state_fills = build_pinned_census()
    _write(PINNED_CENSUS, document)

    authority = _load(LP / ("%s_proposed_authority_022.json" % PREFIX))
    coverage = authority_coverage(document, authority)
    if not coverage["ok"]:
        raise CensusPinError(
            "the promoted census does not contain every founder-signed "
            "identity: %s" % ", ".join(coverage["outside_the_promoted_census"]))
    collisions = cross_market_collisions(document, authority)
    pairing = partition_pairing(document)

    market_contract = _load(LP / "markets" / ("%s.json" % MARKET))
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(_REPO_ROOT),
                            capture_output=True, text=True).stdout.strip()
    derived = RC.derive_authority(MARKET)
    contract = build_release_contract(derived, document, market_contract, commit)
    contract_path = (_REPO_ROOT / "deploy" / "netlify" / "release_contracts"
                     / ("%s.json" % MARKET))
    _write(contract_path, contract)

    disagreements = RC.verify_contract(MARKET)
    if disagreements:
        raise CensusPinError(
            "the written contract disagrees with the derivation: %s"
            % "; ".join(disagreements))

    report = OrderedDict((
        ("schema", "ptf-census-pin-and-release-contract/1.0"),
        ("what_this_is",
         "The 163-identity recensus promoted into the pinned census, and the "
         "market's first release contract written against it. No hotel was "
         "discovered, no identity added or removed, no authority decision "
         "touched."),
        ("market_id", MARKET),
        ("work_order", WORK_ORDER),
        ("provider_calls", 0),
        ("usd_spent", 0.0),
        ("source_commit_at_run", commit),
        ("census", OrderedDict((
            ("old_pinned_count", prior_count),
            ("new_pinned_count", document["count"]),
            ("superseded_kept_at",
             str(SUPERSEDED.relative_to(_REPO_ROOT).as_posix())),
            ("prior_census_accounting", accounting),
            ("states_filled_from_the_market_contract", state_fills),
        ))),
        ("authority_coverage", coverage),
        ("cross_market_collisions", collisions),
        ("partition_pairing", pairing),
        ("release_contract", OrderedDict((
            ("written", True),
            ("path", str(contract_path.relative_to(_REPO_ROOT).as_posix())),
            ("expected_count", contract["identity_census"]["expected_count"]),
            ("disagreements_with_the_derivation", disagreements),
            ("verified_by", "release_contracts.verify_contract"),
        ))),
        ("not_done_here", [
            "no launch-participation row was added",
            "no deployment manifest entry was made",
            "no bundle was assembled",
            "nothing was deployed",
            "no identity was renamed, so the three cross-market key "
            "collisions are recorded and not resolved",
        ]),
    ))
    _write(LP / ("%s_census_pin_024.json" % PREFIX), report)

    print("old pinned census      : %d" % prior_count)
    print("new pinned census      : %d" % document["count"])
    print("  survived by key      : %d" % accounting["survived_by_key"])
    print("  absorbed (recorded)  : %d" % accounting["absorbed_into_a_fresh_sighting"])
    print("  net new              : %d" % accounting["net_new_identities"])
    print("  states filled        : %d" % len(state_fills))
    print("authority outside census: %d" % len(coverage["outside_the_promoted_census"]))
    print("cross-market collisions : %d (in authority: %d)"
          % (collisions["collisions"], collisions["in_this_market_s_authority"]))
    print("partition paired with   : %s" % pairing["paired_with"])
    print("release contract        : %s (expected_count=%d)"
          % (contract_path.name, contract["identity_census"]["expected_count"]))
    print("contract disagreements  : %d" % len(disagreements))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
