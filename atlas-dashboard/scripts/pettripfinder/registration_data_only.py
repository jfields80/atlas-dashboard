"""PTF-NEW-MARKET-REGISTRATION-DATA-ONLY-POLICY-001 -- the proof behind
Regression V2's NEW_MARKET_REGISTRATION_DATA_ONLY change class.

WHY
---
PTF-CHARLOTTE-CONTROLLED-REGISTRATION-REPLAY-003 proved that the ordinary
new-market registration workflow writes a market in 6.94 seconds, produces
output byte-identical to a fifteen-hour audit, and is then charged a full
broad regression by :mod:`regression_delta`, because four outputs a
registration cannot avoid widen the change:

    deploy/netlify/launch_participation.json                DEPLOYMENT_CHANGE
    deploy/netlify/release_contracts/<market>.json          DEPLOYMENT_CHANGE
    launch_packages/pettripfinder/bundle_cache_closure.json DEPLOYMENT_CHANGE
    tests/pettripfinder/pins/market_state.json              shared pin, blocker

The path classes are right: a change to any of those documents CAN change
what production serves. A registration is the one operation where the change
to all four is mechanically constrained -- one row, one contract instance,
two declared inputs, one pin block -- and where every constraint can be
checked by FIELD rather than by path. This module checks them.

WHAT IT PROVES, AND WHAT IT REFUSES TO ASSUME
--------------------------------------------
The class is granted to a WHOLE change set, never to a path, and only when
every check below passes. Anything UNKNOWN is a failure. The checks are:

  change_set          every changed path is one registration role for exactly
                      ONE previously absent market, or a narrow companion
                      (a report, prose, a baseline manifest, the market's own
                      sealed package / receipt); the only narrowing blockers
                      present are the two documents a registration owns
  participation       the record is a REISSUE adding exactly one row at
                      SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH; every
                      other row byte-identical; the writer names itself and is
                      not the founder; the chain comes forward whole and the
                      predecessor is the exact base record; the authorized set
                      is unchanged
  release_contract    a new contract instance whose behavior-bearing blocks
                      equal the single value every existing contract carries,
                      whose data fields are recognized, and whose numbers agree
                      with release_contracts.derive_authority
  build_closure       the closure gains exactly the market's two declared
                      inputs and one remeasurement note, and nothing else
  derived_globals     the committed globals are byte-identical to a
                      regeneration from the shards, and no other market's shard
                      changed, so their diff IS the new market's contribution
  sealed_package      a committed sealed package whose dependency digests are
                      exactly the head bytes of the market's authority, sealed
                      for REGISTERED_LIVE, declaring a joining delta against
                      the current live parent
  fast_receipt        a committed FAST receipt for that package: 15/15 PASS,
                      0 UNKNOWN, 0 FAILED, re-deriving digest, bound to the
                      same parent, intended delta, builder and lane versions
  expected_release    EXPECTED = trusted live parent + the sealed package;
                      ACTUAL = every registered market's committed authority;
                      compared as complete sets of markets, profile identities,
                      routes, ownership and participation -- never as totals
  identity_routes     release_index.compare over both, clean: no cross-market
                      identity collision, no duplicate route, no ownership
                      movement, no unintended change
  market_state_pin    the pin gains exactly one block whose numbers equal what
                      the sealed package independently derives; every other
                      block byte-identical; deployment_state.json untouched
  release_integrity   nothing under deployment authorizations, records,
                      manifests, activation flags or the production gate moved

The expected pin and the expected release are derived from the SEALED PACKAGE
and the TRUSTED LIVE PARENT, never from the candidate's own output, so
"candidate -> generate pin -> candidate matches pin -> pass" cannot happen
here: a pin that agrees with the tree but not with the package fails.

WHAT THE VERDICT MEANS
----------------------
ELIGIBLE = YES means the registration reaches AUTHORIZATION_READY without a
broad regression and with zero remote broad jobs. It authorizes nothing: the
founder authorization, the current-parent guard, the exact-bytes deployment
and the rollback guard are untouched and still owed by the deployment order.

THE COMPOSITE FRESH-MARKET CLASS (PTF-FINAL-FRESH-MARKET-REGISTRATION-REENGINEERING-001)
----------------------------------------------------------------------------------------
PTF-RALEIGH-NC-FINAL-FRESH-CITY-PROOF-001 built a market from zero and was
answered FULL_REGRESSION_REQUIRED = YES at this module's first gate, although
nothing shared had changed. The eleven checks above were validated on a
RE-registration, whose acquisition helpers, discovery configuration,
proposed-authority input and co-location ruling were already committed. A
TRUE FIRST registration creates them, and the gate had no bucket for any of
them: the helpers were "code", the configs were "runtime" by prefix, the
input and the ruling were UNCLASSIFIED, and the market-local proof that would
have claimed the helpers had been switched off by the registration's own
blocker before it ran.

A fresh-market branch is not one change. It is TWO independently provable
zones plus their permitted derived outputs, and the gate now PARTITIONS every
changed path into exactly one of five buckets:

    MARKET_LOCAL_ACQUISITION               the market's own helpers, discovery
                                           config and reports: each proven by
                                           market_local_isolation in
                                           REGISTRATION MODE on all five
                                           conditions (never by its name)
    NEW_MARKET_REGISTRATION_DATA_ONLY      the registration roles above, plus
                                           three typed inputs proven by field:
                                           the proposed-authority document the
                                           registration CLI reads, one additive
                                           co-location ruling, one additive
                                           OSM-extract registry row
    PERMITTED_DERIVED_REGISTRATION_OUTPUT  the regenerated globals and the
                                           narrow companions (reports, package,
                                           receipt, prose, baselines)
    SHARED_BEHAVIOR_CHANGE                 anything that changes shared
                                           behaviour, and every helper the
                                           isolation proof REJECTS -- with the
                                           condition it failed
    UNKNOWN                                a path no bucket claims

The change set narrows ONLY when SHARED_BEHAVIOR_CHANGE and UNKNOWN are both
empty, the bucket sizes sum to the changed-path count, and every remaining
check passes. When the set carries a market-local or typed-input path the
class is COMPOSITE_FRESH_MARKET_DATA_ONLY; when it is a bare re-registration
the class is NEW_MARKET_REGISTRATION_DATA_ONLY, exactly as before. Four checks
were added -- market_local_zone, discovery_config, registration_input,
identity_resolutions -- and none of the eleven was weakened.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import tempfile
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from scripts.pettripfinder import launch_participation as LP
from scripts.pettripfinder import release_contracts as RC
from scripts.pettripfinder import release_index as RI
from scripts.pettripfinder import sealed_market_package as SMP

REPO_ROOT = SMP.REPO_ROOT
WORKTREE = "WORKTREE"

SCHEMA = "ptf-registration-data-only-proof/1.0"
PROOF_VERSION = "ptf-registration-data-only/2.0"
CONTRACT_SCHEMA = "ptf-registration-data-only-contract/1.0"
CONTRACT_PATH = SMP.LAUNCH_PACKAGE / "registration_data_only_contract.json"

YES = "YES"
NO = "NO"
PASS = "PASS"
FAIL = "FAIL"
UNKNOWN = "UNKNOWN"

# --------------------------------------------------------------------------- #
# The permitted registration operation, by path role.
# --------------------------------------------------------------------------- #

PARTICIPATION_PATH = "deploy/netlify/launch_participation.json"
CLOSURE_PATH = "launch_packages/pettripfinder/bundle_cache_closure.json"
MARKET_STATE_PIN_PATH = "tests/pettripfinder/pins/market_state.json"
DEPLOYMENT_STATE_PIN_PATH = "tests/pettripfinder/pins/deployment_state.json"

#: The two narrowing blockers a registration OWNS. Their change is proven by
#: field below; any other blocker in the change set ends the narrowing.
REGISTRATION_OWNED_BLOCKERS: Tuple[str, ...] = (CLOSURE_PATH, MARKET_STATE_PIN_PATH)

ROLE_PARTICIPATION = "participation_row"
ROLE_RELEASE_CONTRACT = "release_contract"
ROLE_BUILD_CLOSURE = "build_closure"
ROLE_MARKET_STATE_PIN = "market_state_pin"
ROLE_MARKET_DOCUMENT = "market_document"
ROLE_AUTHORITY_SHARD = "authority_shard"
ROLE_IDENTITY_CENSUS = "identity_census"
ROLE_POLICY_PACKAGE = "policy_package"
ROLE_FINAL_PARTITION = "final_partition"
ROLE_DERIVED_GLOBAL = "derived_global"
ROLE_COMPANION = "companion"

#: role -> (pattern with <id>/<us>, required, allowed git statuses)
ROLE_PATTERNS: Tuple[Tuple[str, str, bool, Tuple[str, ...]], ...] = (
    (ROLE_PARTICIPATION, PARTICIPATION_PATH, True, ("M",)),
    (ROLE_RELEASE_CONTRACT, "deploy/netlify/release_contracts/<id>.json", True, ("A",)),
    (ROLE_BUILD_CLOSURE, CLOSURE_PATH, True, ("M",)),
    (ROLE_MARKET_STATE_PIN, MARKET_STATE_PIN_PATH, True, ("M",)),
    (ROLE_MARKET_DOCUMENT, "launch_packages/pettripfinder/markets/<id>.json", True, ("A",)),
    (ROLE_AUTHORITY_SHARD, "launch_packages/pettripfinder/markets/authority/<id>/*", True, ("A", "M")),
    (ROLE_IDENTITY_CENSUS, "launch_packages/pettripfinder/identity_census/<id>.json", False, ("A", "M")),
    (ROLE_POLICY_PACKAGE, "launch_packages/pettripfinder/hotel_policy_facts_<id>.json", False, ("A", "M")),
    (ROLE_FINAL_PARTITION, "launch_packages/pettripfinder/<us>_final_partition_*.json", False, ("A", "M")),
    (ROLE_DERIVED_GLOBAL, "launch_packages/pettripfinder/identity_routing.json", False, ("M",)),
    (ROLE_DERIVED_GLOBAL, "launch_packages/pettripfinder/hotel_exclusions.json", False, ("M",)),
    (ROLE_DERIVED_GLOBAL, "launch_packages/pettripfinder/seed_businesses.csv", False, ("M",)),
    (ROLE_DERIVED_GLOBAL, "launch_packages/pettripfinder/ptf_global_authority_manifest.json", False, ("M",)),
)

#: PTF-FINAL-FRESH-MARKET-REGISTRATION-REENGINEERING-001: the three typed
#: inputs a FIRST registration creates, each proven by its own field check.
#: ``(role, pattern, required, allowed statuses)`` as ROLE_PATTERNS.
ROLE_REGISTRATION_INPUT = "registration_input"
ROLE_IDENTITY_RULING = "identity_resolution_ruling"
ROLE_DISCOVERY_REGISTRY_ROW = "discovery_registry_row"
ROLE_DISCOVERY_MARKET_CONFIG = "discovery_market_config"
ROLE_MARKET_LOCAL = "market_local"
REGISTRATION_INPUT_PATTERN = "launch_packages/pettripfinder/<us>_proposed_authority_*.json"
IDENTITY_RESOLUTIONS_PATH = "launch_packages/pettripfinder/identity_resolutions.json"
OSM_EXTRACTS_PATH = "scripts/pettripfinder/discovery/config/osm_extracts.json"
DISCOVERY_CONFIG_PATTERN = "scripts/pettripfinder/discovery/config/<us>.json"
FRESH_MARKET_ROLE_PATTERNS: Tuple[Tuple[str, str, bool, Tuple[str, ...]], ...] = (
    (ROLE_REGISTRATION_INPUT, REGISTRATION_INPUT_PATTERN, False, ("A",)),
    (ROLE_IDENTITY_RULING, IDENTITY_RESOLUTIONS_PATH, False, ("M",)),
    (ROLE_DISCOVERY_REGISTRY_ROW, OSM_EXTRACTS_PATH, False, ("M",)),
    (ROLE_DISCOVERY_MARKET_CONFIG, DISCOVERY_CONFIG_PATTERN, False, ("A",)),
)

#: The five buckets every changed path lands in, exactly one each.
BUCKET_MARKET_LOCAL = "MARKET_LOCAL_ACQUISITION"
BUCKET_REGISTRATION = "NEW_MARKET_REGISTRATION_DATA_ONLY"
BUCKET_DERIVED = "PERMITTED_DERIVED_REGISTRATION_OUTPUT"
BUCKET_SHARED = "SHARED_BEHAVIOR_CHANGE"
BUCKET_UNKNOWN = "UNKNOWN"
BUCKETS: Tuple[str, ...] = (BUCKET_MARKET_LOCAL, BUCKET_REGISTRATION, BUCKET_DERIVED,
                            BUCKET_SHARED, BUCKET_UNKNOWN)
NARROW_BUCKETS = frozenset({BUCKET_MARKET_LOCAL, BUCKET_REGISTRATION, BUCKET_DERIVED})

#: The two whole-set classes this proof can grant.
CLASS_REGISTRATION = "NEW_MARKET_REGISTRATION_DATA_ONLY"
CLASS_COMPOSITE = "COMPOSITE_FRESH_MARKET_DATA_ONLY"

#: Change classes that may travel beside a registration without widening it.
#: A companion under markets/{packages,receipts,staging}/ must be the
#: registering market's own.
COMPANION_CLASSES = frozenset({"GENERATED_REPORT_ONLY", "DOCUMENTATION_ONLY",
                               "BASELINE_MANIFEST_ONLY", "MARKET_DATA_PACKAGE"})

#: The keys a new-market release contract instance may carry, and nothing else.
CONTRACT_KEYS: Tuple[str, ...] = (
    "schema", "contract_id", "market_id", "product", "release_name_prefix", "description",
    "deployment_authorization", "canonical", "identity_census", "reconciliation",
    "policy_package", "public_surface", "routes", "minimum_release_gates",
    "forbidden_output_tokens", "publish",
)
#: PTF-FINAL-ASSEMBLER-REGISTERED-MARKET-DISCOVERY-001: the one OPTIONAL
#: top-level key a registration contract may carry, and the key it follows.
#: ``final_partition`` references the market's partition of record (path +
#: content digest) so the whole-site assembler resolves it from the contract
#: instead of a table in its own source. Optional in the SHAPE check because
#: the committed fixtures of this proof predate it; the registration lane's
#: ``register`` step refuses a registering market whose partition is not
#: owned by its contract, so no registration completes without it.
CONTRACT_OPTIONAL_KEYS: "OrderedDict[str, str]" = OrderedDict((("final_partition", "policy_package"),))


def contract_key_order(present: Iterable[str]) -> List[str]:
    """The exact key order a registration contract must have, given which
    optional keys it carries."""
    expected = list(CONTRACT_KEYS)
    present = set(present)
    for optional, follows in CONTRACT_OPTIONAL_KEYS.items():
        if optional in present:
            expected.insert(expected.index(follows) + 1, optional)
    return expected
#: Behavior-bearing blocks: they must EQUAL the single value every contract at
#: the base carries. Two base values means nothing can be proven.
CONTRACT_SHARED_BLOCKS: Tuple[str, ...] = (
    "canonical", "minimum_release_gates", "forbidden_output_tokens", "publish",
)
CONTRACT_SUBKEYS: "OrderedDict[str, Tuple[Tuple[str, ...], Tuple[str, ...]]]" = OrderedDict((
    ("deployment_authorization", (("grants_deployment", "asserts_market_complete", "means"), ())),
    ("identity_census", (("path", "schema", "expected_count", "note"), ())),
    ("reconciliation", (("confirmed_identities", "published_pet_friendly", "verified_no_pets",
                         "resolved", "unresolved"), ("note", "out_of_current_category"))),
    ("policy_package", (("path", "expected_sha256", "expected_schema_version",
                         "expected_record_count", "identity_authority", "note"), ())),
    # Optional at the top level (CONTRACT_OPTIONAL_KEYS); when present it
    # carries exactly these sub-keys and its path must be the market's own
    # final_partition role file. Its digest is verified against the committed
    # file by release_contracts.final_partition_disagreements (through
    # ``verify``), so the reference is DERIVED, never typed.
    ("final_partition", (("path", "schema", "expected_sha256", "expected_count", "note"), ())),
    ("public_surface", (("seed_hotel_rows", "public_hotel_profile_count",
                         "excluded_public_profile_count", "held_hotel_exclusion"), ())),
    ("routes", (("market_slug", "route_mode", "hotel_route_count",
                 "published_corridor_route_count", "note"), ())),
))

#: The keys a registration's participation row and decision block may carry.
PARTICIPATION_ROW_KEYS = frozenset({"market_id", "launch_status", "note"})
PARTICIPATION_DECISION_KEYS = frozenset({
    "work_order", "decided_by", "decided_on", "reason", "markets_added",
    "founder_authorized_set_unchanged", "supersedes", "lineage"})

#: Paths whose change can never be registration data, whatever their class.
PROTECTED_PREFIXES: Tuple[str, ...] = (
    "deploy/netlify/deployment_authorizations/",
    "deploy/netlify/deployment_records/",
    "deploy/netlify/global_deployment_manifest.json",
    "launch_packages/pettripfinder/fast_release_activation.json",
    "launch_packages/pettripfinder/release_production_gate.json",
    DEPLOYMENT_STATE_PIN_PATH,
    "tests/pettripfinder/pins/supersessions.json",
)

CHECKS: Tuple[str, ...] = (
    "change_set",
    # PTF-FINAL-FRESH-MARKET-REGISTRATION-REENGINEERING-001: the zone proofs
    # a first registration owes, before the registration's own eleven.
    "market_local_zone", "discovery_config", "registration_input", "identity_resolutions",
    "participation", "release_contract", "build_closure", "derived_globals",
    "sealed_package", "fast_receipt", "expected_release", "identity_routes",
    "market_state_pin", "release_integrity",
)
#: The checks whose semantics predate the composite class. Kept as a set so
#: the composite class can be shown to have weakened none of them.
ORIGINAL_CHECKS: Tuple[str, ...] = (
    "change_set", "participation", "release_contract", "build_closure", "derived_globals",
    "sealed_package", "fast_receipt", "expected_release", "identity_routes",
    "market_state_pin", "release_integrity",
)


class RegistrationProofError(RuntimeError):
    """A check could not be established; the verdict is UNKNOWN, never YES."""


# --------------------------------------------------------------------------- #
# Small helpers.
# --------------------------------------------------------------------------- #

def _posix(path: str) -> str:
    return str(path).replace("\\", "/")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json(text: str) -> Any:
    return json.loads(text, object_pairs_hook=OrderedDict)


def _plain(document: Any) -> Any:
    return json.loads(json.dumps(document))


def _glob_match(pattern: str, relpath: str) -> bool:
    from scripts.pettripfinder.regression_delta import _glob_regex
    return _glob_regex(pattern).match(relpath) is not None


def _result(passed: Optional[bool], why: str, **detail: Any) -> "OrderedDict[str, Any]":
    status = PASS if passed else (UNKNOWN if passed is None else FAIL)
    return OrderedDict((("status", status), ("pass", bool(passed)), ("why", why),
                        ("detail", OrderedDict(detail))))


def _work_order_id(value: Any) -> bool:
    import re
    return isinstance(value, str) and re.match(r"^PTF-[A-Z0-9]+(?:-[A-Z0-9]+)*-\d{3}[A-Z]?$", value) is not None


def _is_founder(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return text == "founder" or text.startswith("founder ") or text.startswith("founders")


# --------------------------------------------------------------------------- #
# Reading the two sides. Module-level so a test can point them elsewhere.
# --------------------------------------------------------------------------- #

def bytes_at(rev: str, relpath: str) -> Optional[bytes]:
    from scripts.pettripfinder.regression_delta import _bytes_at
    return _bytes_at(rev, relpath)


def registered_market_ids_at(rev: str) -> Tuple[str, ...]:
    from scripts.pettripfinder.regression_delta import _registered_market_ids_at
    return _registered_market_ids_at(rev)


def release_contract_ids_at(rev: str) -> Tuple[str, ...]:
    if rev == WORKTREE:
        return RC.available_market_ids()
    from scripts.pettripfinder.regression_delta import _git, _repo_prefix
    listing = _git("ls-tree", "--name-only", rev, "%sdeploy/netlify/release_contracts/" % _repo_prefix())
    return tuple(sorted(Path(line.strip()).stem for line in listing.splitlines()
                        if line.strip().endswith(".json")))


def live_index() -> Tuple[RI.ReleaseIndex, RI.LiveState, List[str]]:
    return RI.live_index()


# --------------------------------------------------------------------------- #
# 1. The change set: exactly one registration operation.
# --------------------------------------------------------------------------- #

def role_of(relpath: str, market_id: str) -> Optional[Tuple[str, bool, Tuple[str, ...]]]:
    """``(role, required, allowed statuses)`` when ``relpath`` is one of the
    registering market's registration paths."""
    rel = _posix(relpath)
    us = market_id.replace("-", "_")
    for role, pattern, required, statuses in ROLE_PATTERNS + FRESH_MARKET_ROLE_PATTERNS:
        candidate = pattern.replace("<id>", market_id).replace("<us>", us)
        if _glob_match(candidate, rel):
            return role, required, statuses
    return None


def bucket_of_role(role: str) -> str:
    if role == ROLE_MARKET_LOCAL or role == ROLE_DISCOVERY_MARKET_CONFIG:
        return BUCKET_MARKET_LOCAL
    if role in (ROLE_DERIVED_GLOBAL, ROLE_COMPANION):
        return BUCKET_DERIVED
    return BUCKET_REGISTRATION


def classify_change_set(rows: Sequence[Mapping], *, base: str, head: str,
                        blockers: Sequence[str]) -> "OrderedDict[str, Any]":
    """Which market, if any, this change set registers -- by the registry
    delta and by every path's role. Path-level only; the field checks follow."""
    try:
        registered_base = set(registered_market_ids_at(base))
        registered_head = set(registered_market_ids_at(head))
    except Exception as exc:
        return OrderedDict((("market_id", None), ("roles", OrderedDict()),
                            ("result", _result(None, "registry unreadable: %s" % str(exc)[:160]))))
    added = sorted(registered_head - registered_base)
    removed = sorted(registered_base - registered_head)
    detail: "OrderedDict[str, Any]" = OrderedDict((
        ("registered_at_base", len(registered_base)), ("registered_at_head", len(registered_head)),
        ("markets_added", added), ("markets_removed", removed),
        ("narrowing_blockers", list(blockers)),
    ))
    if removed:
        return OrderedDict((("market_id", None), ("roles", OrderedDict()),
                            ("result", _result(False, "a registration removes no market; removed %s" % removed, **detail))))
    if len(added) != 1:
        return OrderedDict((("market_id", None), ("roles", OrderedDict()),
                            ("result", _result(False, "exactly one previously absent market must be registered; "
                                                      "the registry gained %s" % (added or "nothing"), **detail))))
    market_id = added[0]
    foreign = [b for b in blockers if _posix(b) not in REGISTRATION_OWNED_BLOCKERS]
    if foreign:
        return OrderedDict((("market_id", market_id), ("roles", OrderedDict()),
                            ("result", _result(False, "the change set touches narrowing blocker(s) a registration "
                                                      "does not own: %s" % foreign[:3], **detail))))
    # PTF-FINAL-FRESH-MARKET-REGISTRATION-REENGINEERING-001: the partition.
    # Every changed path lands in exactly one bucket; the market-local
    # candidates are proven one by one by the isolation proof in registration
    # mode, with the registration data of the SAME change set as the paths a
    # helper may have written.
    from scripts.pettripfinder import market_local_isolation as ISO
    from scripts.pettripfinder import market_local_ownership as OWN
    roles: "OrderedDict[str, str]" = OrderedDict()
    buckets: "OrderedDict[str, str]" = OrderedDict()
    reasons: "OrderedDict[str, str]" = OrderedDict()
    proofs: "OrderedDict[str, Any]" = OrderedDict()
    problems: List[str] = []
    zone = None
    registry = None
    try:
        registry = OWN.load_registry()
        zone = OWN.registration_zone(market_id, registry)
    except OWN.OwnershipError as exc:
        problems.append("no registration zone for %s: %s" % (market_id, str(exc)[:120]))
    candidates: List[Tuple[str, str]] = []
    for row in rows:
        rel = _posix(row["path"])
        status = str(row.get("status") or "")[:1]
        classes = set(row.get("classes") or ())
        if any(rel.startswith(p) for p in PROTECTED_PREFIXES):
            buckets[rel] = BUCKET_SHARED
            reasons[rel] = "protected release state"
            problems.append("%s is protected release state" % rel)
            continue
        found = role_of(rel, market_id)
        if found is not None:
            role, _required, statuses = found
            if status not in statuses:
                buckets[rel] = BUCKET_SHARED
                reasons[rel] = "status %r is not a registration write (%s)" % (status, "/".join(statuses))
                problems.append("%s: status %r is not a registration write (%s)" % (rel, status, "/".join(statuses)))
                continue
            roles[rel] = role
            buckets[rel] = bucket_of_role(role)
            reasons[rel] = "registration role %s" % role
            if role == ROLE_DISCOVERY_MARKET_CONFIG:
                candidates.append((rel, status))
            continue
        # A narrow companion (a report, prose, a baseline, the market's own
        # package / receipt) keeps the semantics the audited registration
        # class gave it; only a path that is NOT a companion and is owned by
        # the registering market's zone -- its helpers, its discovery config,
        # its own tests -- goes to the isolation proof.
        if classes and classes <= COMPANION_CLASSES:
            if "MARKET_DATA_PACKAGE" in classes and not (
                    _glob_match("launch_packages/pettripfinder/markets/packages/%s/**" % market_id, rel)
                    or _glob_match("launch_packages/pettripfinder/markets/receipts/%s/**" % market_id, rel)
                    or _glob_match("launch_packages/pettripfinder/markets/staging/%s/**" % market_id, rel)):
                buckets[rel] = BUCKET_SHARED
                reasons[rel] = "another market's package data"
                problems.append("%s is another market's package data" % rel)
                continue
            roles[rel] = ROLE_COMPANION
            buckets[rel] = BUCKET_DERIVED
            reasons[rel] = "narrow companion (%s)" % "/".join(sorted(classes))
            continue
        if zone is not None and not registry.is_never_local(rel) \
                and any(OWN._glob_match(pat, rel) for pat in zone.owned_paths):
            candidates.append((rel, status))
            continue
        if rel.startswith("tests/") or rel.endswith(".py") or rel.startswith("scripts/"):
            buckets[rel] = BUCKET_SHARED
            reasons[rel] = "code or a test expectation outside the registering market's zone"
            problems.append("%s is code or a test expectation, not registration data" % rel)
            continue
        buckets[rel] = BUCKET_UNKNOWN
        reasons[rel] = "no bucket claims this path (%s)" % ("/".join(sorted(classes)) or "no class")
        problems.append("%s is not a registration path for %s (%s)" % (rel, market_id, sorted(classes) or "no class"))
    # The paths a helper may have written: every accounted non-code path of
    # this change set (registration data, derived output, the zone's own data).
    proven_paths = sorted(set(rel for rel, b in buckets.items() if b in NARROW_BUCKETS and not rel.endswith(".py"))
                          | set(rel for rel, _s in candidates if not rel.endswith(".py")))
    context = OrderedDict((("market_id", market_id), ("proven_paths", proven_paths)))
    for rel, status in candidates:
        try:
            proof = ISO.prove(rel, base, head, status=status or "M", registry=registry, registration=context)
        except Exception as exc:                       # an unreadable helper is not local
            proof = OrderedDict((("passed", False), ("failed_conditions", ["unknown"]),
                                 ("conditions", OrderedDict((("unknown", OrderedDict((("pass", False),
                                  ("why", "%s: %s" % (type(exc).__name__, str(exc)[:160]))))),)))))
        proofs[rel] = OrderedDict((
            ("passed", bool(proof.get("passed"))),
            ("mode", proof.get("mode")), ("zone", proof.get("zone")),
            ("failed_conditions", list(proof.get("failed_conditions") or ())),
            ("conditions", OrderedDict((k, OrderedDict((("pass", v.get("pass")), ("why", str(v.get("why"))[:400]))))
                                       for k, v in (proof.get("conditions") or {}).items())),
        ))
        if proof.get("passed"):
            roles.setdefault(rel, ROLE_MARKET_LOCAL)
            buckets[rel] = BUCKET_MARKET_LOCAL
            reasons[rel] = "isolation proof passed in registration mode (zone %s)" % proof.get("zone")
        else:
            failed = ", ".join(proof.get("failed_conditions") or ["unknown"])
            why = "; ".join(str((proof.get("conditions") or {}).get(c, {}).get("why", ""))[:160]
                            for c in (proof.get("failed_conditions") or []))
            roles.pop(rel, None)
            buckets[rel] = BUCKET_SHARED
            reasons[rel] = "rejected by the isolation proof on %s: %s" % (failed, why)
            problems.append("%s is not market-local: %s failed (%s)" % (rel, failed, why[:200]))
    present = {role for role in roles.values()}
    missing = [role for role, _p, required, _s in ROLE_PATTERNS if required and role not in present]
    if missing:
        problems.append("required registration output(s) absent from the change set: %s" % sorted(set(missing)))
    counts = OrderedDict((b, sum(1 for v in buckets.values() if v == b)) for b in BUCKETS)
    total = len(rows)
    accounted = len(buckets)
    if accounted != total or sum(counts.values()) != total:
        problems.append("path accounting is incomplete: %d of %d changed paths bucketed" % (accounted, total))
    partition = OrderedDict((b, sorted(p for p, v in buckets.items() if v == b)) for b in BUCKETS)
    fresh = bool(partition[BUCKET_MARKET_LOCAL]) or any(
        roles.get(p) in (ROLE_REGISTRATION_INPUT, ROLE_IDENTITY_RULING, ROLE_DISCOVERY_REGISTRY_ROW,
                         ROLE_DISCOVERY_MARKET_CONFIG) for p in roles)
    detail["roles"] = OrderedDict(sorted(roles.items()))
    detail["buckets"] = OrderedDict(sorted(buckets.items()))
    detail["bucket_reasons"] = OrderedDict(sorted(reasons.items()))
    detail["partition"] = partition
    detail["accounting"] = OrderedDict((
        ("TOTAL_CHANGED_PATHS", total),
        ("MARKET_LOCAL_ACQUISITION_PATHS", counts[BUCKET_MARKET_LOCAL]),
        ("REGISTRATION_DATA_PATHS", counts[BUCKET_REGISTRATION]),
        ("DERIVED_PATHS", counts[BUCKET_DERIVED]),
        ("SHARED_BEHAVIOR_PATHS", counts[BUCKET_SHARED]),
        ("UNKNOWN_PATHS", counts[BUCKET_UNKNOWN]),
        ("sum_of_buckets", sum(counts.values())),
        ("sum_equals_total", sum(counts.values()) == total and accounted == total),
    ))
    detail["market_local_proofs"] = proofs
    detail["proven_paths"] = proven_paths
    detail["change_class"] = CLASS_COMPOSITE if fresh else CLASS_REGISTRATION
    detail["zone"] = OrderedDict((("market_id", zone.market_id), ("execution_zone", zone.execution_zone)))if zone else None
    if problems:
        return OrderedDict((("market_id", market_id), ("roles", roles),
                            ("result", _result(False, "; ".join(problems[:6]), problems=problems, **detail))))
    return OrderedDict((("market_id", market_id), ("roles", roles),
                        ("result", _result(True, "every one of %d changed paths is in exactly one narrow bucket for %s "
                                                 "(%d market-local, %d registration data, %d derived; 0 shared, 0 "
                                                 "unknown), and the only blockers are the two the registration owns"
                                                 % (total, market_id, counts[BUCKET_MARKET_LOCAL],
                                                    counts[BUCKET_REGISTRATION], counts[BUCKET_DERIVED]), **detail))))


# --------------------------------------------------------------------------- #
# 1a-1d. PTF-FINAL-FRESH-MARKET-REGISTRATION-REENGINEERING-001: the zone
# proofs a FIRST registration owes.
# --------------------------------------------------------------------------- #

def check_market_local_zone(gate: Mapping) -> "OrderedDict[str, Any]":
    """Every market-local candidate of the partition passed the isolation
    proof in registration mode (namespace, imports, writes, reachability,
    registration). The gate already refused the set if one failed; this check
    records the proofs so the verdict names each helper and each condition."""
    detail_in = gate.get("result", {}).get("detail") or {}
    proofs = detail_in.get("market_local_proofs") or {}
    partition = detail_in.get("partition") or {}
    local = list(partition.get(BUCKET_MARKET_LOCAL) or ())
    failed = OrderedDict((p, d) for p, d in proofs.items() if not d.get("passed"))
    detail = OrderedDict((
        ("market_local_paths", local), ("proofs_run", len(proofs)),
        ("proofs_passed", sum(1 for d in proofs.values() if d.get("passed"))),
        ("rejected", OrderedDict((p, OrderedDict((("failed_conditions", d.get("failed_conditions")),
                                                   ("why", "; ".join(str(d["conditions"][c]["why"])
                                                                     for c in d.get("failed_conditions") or ()
                                                                     if c in d.get("conditions", {}))))))
                                 for p, d in failed.items())),
        ("conditions", ["namespace", "imports", "writes", "reachability", "registration"]),
        ("mode", "registration"),
    ))
    if failed:
        return _result(False, "%d market-local candidate(s) rejected by the isolation proof: %s"
                       % (len(failed), "; ".join("%s (%s)" % (p, ", ".join(d.get("failed_conditions") or []))
                                                 for p, d in list(failed.items())[:4])), **detail)
    unproven = [p for p in local if p not in proofs]
    if unproven:
        return _result(False, "market-local path(s) carry no proof: %s" % unproven[:4], **detail)
    if not local:
        return _result(True, "no market-local path in the change set (a bare re-registration)", **detail)
    return _result(True, "every one of %d market-local path(s) passed all five isolation conditions in "
                         "registration mode" % len(local), **detail)


def _discovery_row_key(row: Mapping) -> str:
    return str(row.get("extract_id") or "")


def check_discovery_config(rows: Sequence[Mapping], base: str, head: str, market_id: str) -> "OrderedDict[str, Any]":
    """Field-level: the new market's own discovery config loads through the
    discovery reader for exactly that market; the shared OSM-extract registry
    gains exactly one row for exactly that market and every pre-existing row is
    semantically identical; no discovery code or provider configuration
    changed. A changed existing row, an unknown top-level field, or a second
    market widens."""
    from scripts.pettripfinder.discovery import market_config as MC
    from scripts.pettripfinder.discovery import osm_extract as OSM
    us = market_id.replace("-", "_")
    config_rel = DISCOVERY_CONFIG_PATTERN.replace("<us>", us)
    changed = OrderedDict((_posix(r["path"]), str(r.get("status") or "")[:1]) for r in rows)
    problems: List[str] = []
    other = [p for p in changed if p.startswith("scripts/pettripfinder/discovery/")
             and p not in (config_rel, OSM_EXTRACTS_PATH)]
    if other:
        problems.append("discovery code or provider configuration changed: %s" % other[:3])
    detail: "OrderedDict[str, Any]" = OrderedDict((("market_config", None), ("registry_row", None)))
    if config_rel in changed:
        if changed[config_rel] != "A":
            problems.append("%s: status %r is not a new-market config write" % (config_rel, changed[config_rel]))
        data = bytes_at(head, config_rel)
        if data is None:
            problems.append("%s is absent at %s" % (config_rel, head))
        else:
            try:
                with tempfile.TemporaryDirectory() as scratch:
                    (Path(scratch) / (us + ".json")).write_bytes(data)
                    cfg = MC.load_market_config(market_id, config_dir=Path(scratch))
                doc = _json(data.decode("utf-8-sig"))
                if doc.get("market_id") != market_id:
                    problems.append("discovery config market_id is %r, not %r" % (doc.get("market_id"), market_id))
                if not cfg.cells:
                    problems.append("discovery config declares no cells")
                detail["market_config"] = OrderedDict((("path", config_rel), ("market_id", doc.get("market_id")),
                                                       ("cells", len(cfg.cells)),
                                                       ("municipalities", len(cfg.included_municipalities))))
            except Exception as exc:
                problems.append("discovery config does not load through the discovery reader: %s: %s"
                                % (type(exc).__name__, str(exc)[:120]))
    if OSM_EXTRACTS_PATH in changed:
        if changed[OSM_EXTRACTS_PATH] != "M":
            problems.append("%s: status %r is not an additive registry write" % (OSM_EXTRACTS_PATH, changed[OSM_EXTRACTS_PATH]))
        base_data, head_data = bytes_at(base, OSM_EXTRACTS_PATH), bytes_at(head, OSM_EXTRACTS_PATH)
        if base_data is None or head_data is None:
            problems.append("the OSM-extract registry is unreadable at the base or the head")
        else:
            try:
                base_doc = _json(base_data.decode("utf-8-sig"))
                head_doc = _json(head_data.decode("utf-8-sig"))
                OSM.ExtractRegistry.from_document(base_doc, source="base")
                OSM.ExtractRegistry.from_document(head_doc, source="head")
            except Exception as exc:
                problems.append("the OSM-extract registry does not validate: %s: %s" % (type(exc).__name__, str(exc)[:120]))
                base_doc, head_doc = {}, {}
            for key in set(base_doc) | set(head_doc):
                if key == "extracts":
                    continue
                if _plain(base_doc.get(key)) != _plain(head_doc.get(key)):
                    problems.append("registry.%s changed (semantics; a registration adds a row and nothing else)" % key)
            base_rows = OrderedDict((_discovery_row_key(r), r) for r in base_doc.get("extracts") or ())
            head_rows = OrderedDict((_discovery_row_key(r), r) for r in head_doc.get("extracts") or ())
            for key, row in base_rows.items():
                if key not in head_rows:
                    problems.append("existing registry row %s removed" % key)
                elif _plain(head_rows[key]) != _plain(row):
                    problems.append("existing registry row %s changed: %s" % (
                        key, sorted(f for f in set(row) | set(head_rows[key]) if row.get(f) != head_rows[key].get(f))[:4]))
            new_keys = [k for k in head_rows if k not in base_rows]
            if len(new_keys) != 1:
                problems.append("the registry must gain exactly one row; it gained %s" % (new_keys or "nothing"))
            for key in new_keys:
                row = head_rows[key]
                if list(row.get("markets") or ()) != [market_id]:
                    problems.append("new registry row %s serves %s, not exactly [%s]" % (key, row.get("markets"), market_id))
                if any(r.get("index_path") == row.get("index_path") for k, r in head_rows.items() if k != key):
                    problems.append("new registry row %s reuses another row's index_path (one output root per extract per market)" % key)
                if not str(row.get("url") or "").startswith("https://"):
                    problems.append("new registry row %s url is not https" % key)
                if not str(row.get("local_pbf") or "").startswith("data/") or not str(row.get("index_path") or "").startswith("data/"):
                    problems.append("new registry row %s must keep its extract and index under data/ (gitignored)" % key)
                detail["registry_row"] = OrderedDict((("extract_id", key), ("markets", row.get("markets")),
                                                      ("index_path", row.get("index_path")),
                                                      ("existing_rows_identical", len(base_rows)),
                                                      ("head_rows", len(head_rows))))
    if problems:
        return _result(False, "; ".join(problems[:5]), problems=problems, **detail)
    if detail["market_config"] is None and detail["registry_row"] is None:
        return _result(True, "no discovery configuration in the change set", **detail)
    return _result(True, "the discovery config loads for exactly %s%s; no discovery code or provider "
                         "configuration changed" % (market_id, (" and the OSM-extract registry gains exactly one row for it "
                                                                 "with every existing row semantically identical"
                                                                 if detail["registry_row"] else "")), **detail)


def _newest_input_at(head: str, market_id: str) -> Optional[str]:
    us = market_id.replace("-", "_")
    if head == WORKTREE:
        found = sorted(SMP.LAUNCH_PACKAGE.glob("%s_proposed_authority_*.json" % us))
        return ("launch_packages/pettripfinder/" + found[-1].name) if found else None
    from scripts.pettripfinder import regression_delta as RD
    try:
        listing = RD._git("ls-tree", "--name-only", head, RD._repo_prefix() + "launch_packages/pettripfinder/")
    except Exception:
        return None
    names = sorted(Path(line.strip()).name for line in listing.splitlines()
                   if Path(line.strip()).name.startswith(us + "_proposed_authority_") and line.strip().endswith(".json"))
    return ("launch_packages/pettripfinder/" + names[-1]) if names else None


def check_registration_input(rows: Sequence[Mapping], head: str, market_id: str) -> "OrderedDict[str, Any]":
    """NEW_MARKET_REGISTRATION_INPUT: the ptf-market-proposed-authority/1.0
    document market_registration_cli reads is DATA when it belongs to exactly
    one new market, carries the schema the CLI's own loader accepts, reconciles
    its own counts, reconciles with the market's identity census, and binds
    to the written shard (the CLI's own verify). Unknown or malformed: FAIL."""
    from scripts.pettripfinder import market_registration_cli as MRC
    from scripts.pettripfinder.site_data import normalize_name
    us = market_id.replace("-", "_")
    pattern = REGISTRATION_INPUT_PATTERN.replace("<us>", us)
    in_set = [(_posix(r["path"]), str(r.get("status") or "")[:1]) for r in rows if _glob_match(pattern, _posix(r["path"]))]
    problems: List[str] = []
    if len(in_set) > 1:
        problems.append("more than one registration input in the change set: %s" % [p for p, _s in in_set])
    for rel, status in in_set:
        if status != "A":
            problems.append("%s: status %r; a registration input is created, never edited" % (rel, status))
    other_inputs = [_posix(r["path"]) for r in rows
                    if _glob_match("launch_packages/pettripfinder/*_proposed_authority_*.json", _posix(r["path"]))
                    and not _glob_match(pattern, _posix(r["path"]))]
    if other_inputs:
        problems.append("another market's registration input changed: %s" % other_inputs[:3])
    for impl in ("scripts/pettripfinder/market_registration_cli.py", "scripts/pettripfinder/market_proposed_authority_cli.py"):
        if any(_posix(r["path"]) == impl for r in rows):
            problems.append("the registration input's reader/writer changed: %s" % impl)
    rel = in_set[0][0] if in_set else _newest_input_at(head, market_id)
    detail: "OrderedDict[str, Any]" = OrderedDict((("path", rel), ("in_change_set", bool(in_set)), ("schema", None)))
    if rel is None:
        problems.append("no registration input (%s) exists at %s" % (pattern, head))
        return _result(False, "; ".join(problems), problems=problems, **detail)
    data = bytes_at(head, rel)
    if data is None:
        problems.append("%s is absent at %s" % (rel, head))
        return _result(False, "; ".join(problems), problems=problems, **detail)
    with tempfile.TemporaryDirectory() as scratch:
        path = Path(scratch) / Path(rel).name
        path.write_bytes(data)
        try:
            doc = MRC.load_authority(path)
        except Exception as exc:
            problems.append("the registration CLI's loader refuses the input: %s" % str(exc)[:160])
            return _result(False, "; ".join(problems), problems=problems, **detail)
        detail["schema"] = doc.get("schema")
        if doc.get("market_id") != market_id:
            problems.append("input market_id is %r, not %r" % (doc.get("market_id"), market_id))
        pf = list(doc.get("pet_friendly") or ())
        np_ = list(doc.get("verified_no_pets") or ())
        if doc.get("pet_friendly_count") != len(pf):
            problems.append("pet_friendly_count %r != %d rows" % (doc.get("pet_friendly_count"), len(pf)))
        if doc.get("verified_no_pets_count") != len(np_):
            problems.append("verified_no_pets_count %r != %d rows" % (doc.get("verified_no_pets_count"), len(np_)))
        if doc.get("authority_total") != len(pf) + len(np_):
            problems.append("authority_total %r != %d" % (doc.get("authority_total"), len(pf) + len(np_)))
        for kind, records in (("pet_friendly", pf), ("verified_no_pets", np_)):
            for i, rec in enumerate(records):
                for field in ("identity_key", "normalized_name", "canonical_name", "official_url", "source_url", "observed_at"):
                    if not rec.get(field):
                        problems.append("%s[%d] carries no %s" % (kind, i, field))
                        break
                if rec.get("market_id") not in (None, market_id):
                    problems.append("%s[%d] belongs to %r" % (kind, i, rec.get("market_id")))
        # source identities reconcile: every record's identity key is an
        # admitted identity of the market's committed census at the head.
        census_data = bytes_at(head, "launch_packages/pettripfinder/identity_census/%s.json" % market_id)
        if census_data is None:
            problems.append("the market's identity census is absent at %s" % head)
        else:
            try:
                census = _json(census_data.decode("utf-8-sig"))
                keys = {h.get("identity_key") for h in census.get("hotels") or ()}
                keys |= {a for h in census.get("hotels") or () for a in (h.get("identity_key_aliases") or ())}
                names = {normalize_name(str(h.get("canonical_name") or "")) for h in census.get("hotels") or ()}
                missing = [rec.get("identity_key") for rec in pf + np_
                           if rec.get("identity_key") not in keys
                           and normalize_name(str(rec.get("canonical_name") or "")) not in names]
                if missing:
                    problems.append("%d input identities are not in the census: %s" % (len(missing), missing[:3]))
                detail["census_identities"] = len(keys)
            except Exception as exc:
                problems.append("the census does not parse: %s" % str(exc)[:120])
        detail["pet_friendly"] = len(pf)
        detail["verified_no_pets"] = len(np_)
        # digest binding: the written shard states exactly this input's sets.
        if head == WORKTREE:
            try:
                shard_problems = MRC.verify(market_id, path)
            except Exception as exc:
                shard_problems = ["verify raised %s: %s" % (type(exc).__name__, str(exc)[:120])]
            if shard_problems:
                problems.append("the shard does not bind to the input: %s" % shard_problems[:2])
            detail["shard_binding"] = "verified by market_registration_cli.verify" if not shard_problems else shard_problems
        else:
            seed = bytes_at(head, "launch_packages/pettripfinder/markets/authority/%s/seed_businesses.csv" % market_id)
            excl = bytes_at(head, "launch_packages/pettripfinder/markets/authority/%s/hotel_exclusions.json" % market_id)
            if seed is None or excl is None:
                problems.append("the shard is absent at %s" % head)
            else:
                import csv
                import io
                seed_names = {normalize_name(r.get("name") or "") for r in csv.DictReader(io.StringIO(seed.decode("utf-8-sig")))}
                excl_names = {r.get("normalized_name") for r in (_json(excl.decode("utf-8-sig")).get("exclusions") or ())}
                pf_names = {r.get("normalized_name") for r in pf}
                np_names = {normalize_name(r.get("canonical_name") or "") for r in np_}
                if seed_names != pf_names:
                    problems.append("seed shard disagrees with the input's pet-friendly set: %s" % sorted(seed_names ^ pf_names)[:3])
                if excl_names != np_names:
                    problems.append("exclusion shard disagrees with the input's verified-no-pets set: %s" % sorted(excl_names ^ np_names)[:3])
                detail["shard_binding"] = "seed and exclusion shards read at %s state the input's sets" % head
    detail["input_digest"] = "sha256:" + _sha256(data)
    if problems:
        return _result(False, "; ".join(problems[:5]), problems=problems, **detail)
    return _result(True, "the registration input is a %s document for exactly %s, its counts reconcile, every "
                         "identity is in the census, and the written shard binds to it" % (detail["schema"], market_id),
                   **detail)


def check_identity_resolutions(rows: Sequence[Mapping], base: str, head: str, market_id: str) -> "OrderedDict[str, Any]":
    """Field-level: identity_resolutions.json may gain rulings for exactly the
    registering market. Every pre-existing ruling byte-identical and in place;
    every new ruling validates under the publication guard's own contract,
    names exact properties of the market's committed authority, satisfies the
    exclusion contract's co_located_distinct proof pairwise, and collides with
    no ruling's slugs or names. No ruling: PASS."""
    from scripts.pettripfinder import hotel_exclusions as HE
    from scripts.pettripfinder import publication_guard as PG
    from scripts.pettripfinder.site_data import normalize_name
    changed = OrderedDict((_posix(r["path"]), str(r.get("status") or "")[:1]) for r in rows)
    detail: "OrderedDict[str, Any]" = OrderedDict((("in_change_set", IDENTITY_RESOLUTIONS_PATH in changed),))
    if IDENTITY_RESOLUTIONS_PATH not in changed:
        return _result(True, "no identity-resolution ruling in the change set", **detail)
    problems: List[str] = []
    if changed[IDENTITY_RESOLUTIONS_PATH] != "M":
        problems.append("identity_resolutions.json status %r is not an additive ruling write" % changed[IDENTITY_RESOLUTIONS_PATH])
    base_data, head_data = bytes_at(base, IDENTITY_RESOLUTIONS_PATH), bytes_at(head, IDENTITY_RESOLUTIONS_PATH)
    if base_data is None or head_data is None:
        problems.append("identity_resolutions.json is unreadable at the base or the head")
        return _result(False, "; ".join(problems), problems=problems, **detail)
    try:
        base_doc = _json(base_data.decode("utf-8-sig"))
        head_doc = _json(head_data.decode("utf-8-sig"))
        PG.validate_resolutions(head_doc)
        PG.validate_resolutions(base_doc)
    except Exception as exc:
        problems.append("the rulings do not validate under the publication guard: %s" % str(exc)[:160])
        return _result(False, "; ".join(problems), problems=problems, **detail)
    for key in set(base_doc) | set(head_doc):
        if key == "resolutions":
            continue
        if _plain(base_doc.get(key)) != _plain(head_doc.get(key)):
            problems.append("identity_resolutions.%s changed" % key)
    base_rows = list(base_doc.get("resolutions") or ())
    head_rows = list(head_doc.get("resolutions") or ())
    if _plain(head_rows[:len(base_rows)]) != _plain(base_rows):
        problems.append("a pre-existing ruling changed or moved (the first %d rulings must be the base rulings)" % len(base_rows))
    new_rows = head_rows[len(base_rows):]
    if not new_rows:
        problems.append("no ruling was added")
    # the market's own committed identities at the head
    known: Dict[str, str] = {}
    excl = bytes_at(head, "launch_packages/pettripfinder/markets/authority/%s/hotel_exclusions.json" % market_id)
    facts = None
    try:
        from scripts.pettripfinder.site_data import published_facts_path
        facts = bytes_at(head, "launch_packages/pettripfinder/" + published_facts_path(market_id).name)
    except Exception:
        facts = None
    census = bytes_at(head, "launch_packages/pettripfinder/identity_census/%s.json" % market_id)
    records: List[Dict] = []
    if excl is not None:
        records.extend(_json(excl.decode("utf-8-sig")).get("exclusions") or ())
    if census is not None:
        records.extend(_json(census.decode("utf-8-sig")).get("hotels") or ())
    if facts is not None:
        records.extend(OrderedDict((("canonical_name", h.get("name")), ("official_url", (h.get("facts") or {}).get("official_url"))))
                       for h in _json(facts.decode("utf-8-sig")).get("hotels") or ())
    for rec in records:
        name = normalize_name(str(rec.get("canonical_name") or ""))
        if name:
            known[name] = str(rec.get("official_url") or "")
    added: List[Dict[str, Any]] = []
    for i, row in enumerate(new_rows):
        where = "new ruling %d (%s)" % (i, row.get("resolution_id"))
        if row.get("market_id") != market_id:
            problems.append("%s belongs to %r, not %r" % (where, row.get("market_id"), market_id))
        if PG.resolution_hash(row) != row.get("resolution_hash"):
            problems.append("%s: resolution_hash does not re-derive" % where)
        if row.get("resolution_type") != PG.SAME_CAMPUS:
            problems.append("%s: resolution_type %r is not the one permitted type" % (where, row.get("resolution_type")))
        idents = list(row.get("identities") or ())
        if len(idents) < 2:
            problems.append("%s names fewer than two identities" % where)
        for ident in idents:
            name = normalize_name(str(ident.get("canonical_name") or ""))
            if name not in known:
                problems.append("%s names %r, which is not an identity of %s's committed authority"
                                % (where, ident.get("canonical_name"), market_id))
            elif known[name] and ident.get("official_url") and HE.canonical_url(known[name]) != HE.canonical_url(ident["official_url"]):
                problems.append("%s: %r carries a different official URL than the committed identity"
                                % (where, ident.get("canonical_name")))
        for a_i in range(len(idents)):
            for b_i in range(a_i + 1, len(idents)):
                a, b = idents[a_i], idents[b_i]
                verdict, why = HE.co_located_distinct(
                    OrderedDict((("canonical_name", a.get("canonical_name")), ("official_url", a.get("official_url")))),
                    OrderedDict((("canonical_name", b.get("canonical_name")), ("official_url", b.get("official_url")))))
                if verdict != HE.CO_LOCATED_DISTINCT:
                    problems.append("%s: %r / %r are %s under the exclusion contract (%s)"
                                    % (where, a.get("canonical_name"), b.get("canonical_name"), verdict, why))
        added.append(OrderedDict((("resolution_id", row.get("resolution_id")), ("address_key", row.get("address_key")),
                                  ("identities", [i.get("slug") for i in idents]))))
    # global collision scan over every ruling at the head
    slug_owner: Dict[str, str] = {}
    name_owner: Dict[str, str] = {}
    for row in head_rows:
        for ident in row.get("identities") or ():
            slug, name = str(ident.get("slug") or ""), normalize_name(str(ident.get("canonical_name") or ""))
            if slug in slug_owner and slug_owner[slug] != name:
                problems.append("slug %r is claimed by two different identities across rulings" % slug)
            slug_owner.setdefault(slug, name)
            if name in name_owner and name_owner[name] != slug:
                problems.append("identity %r carries two slugs across rulings" % ident.get("canonical_name"))
            name_owner.setdefault(name, slug)
    detail.update(OrderedDict((("base_rulings", len(base_rows)), ("head_rulings", len(head_rows)),
                               ("added", added), ("committed_identities_checked", len(known)))))
    if problems:
        return _result(False, "; ".join(problems[:5]), problems=problems, **detail)
    return _result(True, "%d additive ruling(s) for %s validate under the publication guard, name exact committed "
                         "identities, are DISTINCT pairwise under the exclusion contract, and every pre-existing "
                         "ruling is byte-identical; no slug or name collides" % (len(new_rows), market_id), **detail)


# --------------------------------------------------------------------------- #
# 2. The participation row: a reissue that adds one row and decides nothing.
# --------------------------------------------------------------------------- #

def check_participation(base_bytes: bytes, head_bytes: bytes, market_id: str) -> "OrderedDict[str, Any]":
    base = _json(base_bytes.decode("utf-8-sig"))
    head = _json(head_bytes.decode("utf-8-sig"))
    problems: List[str] = []
    for key in ("schema", "what_this_is", "launch_statuses"):
        if base.get(key) != head.get(key):
            problems.append("top-level %s changed" % key)
    extra_top = set(head) - set(base)
    if extra_top:
        problems.append("unknown top-level key(s) added: %s" % sorted(extra_top))

    base_rows = OrderedDict((r["market_id"], r) for r in base.get("markets") or ())
    head_rows = OrderedDict((r["market_id"], r) for r in head.get("markets") or ())
    if set(head_rows) != set(base_rows) | {market_id}:
        problems.append("rows must be the base rows plus %s; head has %s"
                        % (market_id, sorted(set(head_rows) ^ (set(base_rows) | {market_id}))))
    if market_id in base_rows:
        problems.append("%s already had a participation row at the base" % market_id)
    for mid, row in base_rows.items():
        if head_rows.get(mid) != row:
            problems.append("existing row %s changed" % mid)
    new_row = head_rows.get(market_id) or {}
    if set(new_row) - PARTICIPATION_ROW_KEYS:
        problems.append("new row carries unknown key(s) %s" % sorted(set(new_row) - PARTICIPATION_ROW_KEYS))
    if new_row.get("launch_status") != LP.SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH:
        problems.append("new row status is %r; a registration may only write %s"
                        % (new_row.get("launch_status"), LP.SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH))
    ids = [r["market_id"] for r in head.get("markets") or ()]
    if ids != sorted(ids):
        problems.append("rows are not sorted by market_id")

    authorized_base = sorted(r["market_id"] for r in base_rows.values()
                             if r.get("launch_status") == LP.FOUNDER_AUTHORIZED_FOR_LAUNCH)
    authorized_head = sorted(r["market_id"] for r in head_rows.values()
                             if r.get("launch_status") == LP.FOUNDER_AUTHORIZED_FOR_LAUNCH)
    if authorized_base != authorized_head:
        problems.append("the founder-authorized set moved: %s -> %s" % (authorized_base, authorized_head))

    decision = head.get("decision") or {}
    if set(decision) - PARTICIPATION_DECISION_KEYS:
        problems.append("decision carries unknown key(s) %s" % sorted(set(decision) - PARTICIPATION_DECISION_KEYS))
    for key in LP.DECISION_REQUIRED:
        if not decision.get(key):
            problems.append("decision.%s is missing" % key)
    if not _work_order_id(decision.get("work_order")):
        problems.append("decision.work_order %r is not a work-order id" % decision.get("work_order"))
    if _is_founder(decision.get("decided_by")):
        problems.append("decision.decided_by names the founder; a registration writer must name itself")
    if decision.get("decided_by") != decision.get("work_order"):
        problems.append("decision.decided_by %r is not the writing work order %r"
                        % (decision.get("decided_by"), decision.get("work_order")))
    if list(decision.get("markets_added") or ()) != [market_id]:
        problems.append("decision.markets_added is %r, expected [%r]" % (decision.get("markets_added"), market_id))
    if decision.get("founder_authorized_set_unchanged") is not True:
        problems.append("decision.founder_authorized_set_unchanged is not true")

    predecessor = decision.get("supersedes") or {}
    base_sha = _sha256(base_bytes)
    if predecessor.get("sha256") != base_sha:
        problems.append("decision.supersedes names %s, the base record is %s"
                        % (str(predecessor.get("sha256"))[:12], base_sha[:12]))
    if predecessor.get("work_order") != (base.get("decision") or {}).get("work_order"):
        problems.append("decision.supersedes.work_order is not the base decision's")
    if sorted(predecessor.get("founder_authorized") or ()) != authorized_base:
        problems.append("decision.supersedes.founder_authorized is not the base authorized set")

    with tempfile.TemporaryDirectory() as scratch:
        base_path = Path(scratch) / "base.json"
        head_path = Path(scratch) / "head.json"
        base_path.write_bytes(base_bytes)
        head_path.write_bytes(head_bytes)
        try:
            base_chain = LP.decision_chain(base, base_path)["records"]
        except LP.LaunchParticipationError as exc:
            base_chain = None
            problems.append("the base record's chain is unreachable: %s" % str(exc)[:120])
        records = (decision.get("lineage") or {}).get("records") or []
        if base_chain is not None:
            expected_records = [_plain(r) for r in base_chain] + [_plain(LP.decision_record(base, base_sha))]
            if _plain(records) != expected_records:
                problems.append("decision.lineage.records is not the base chain plus the base record "
                                "(%d records, expected %d)" % (len(records), len(expected_records)))
        chain_problems = LP.decision_problems(head, path=head_path)
        problems.extend("decision chain: %s" % p for p in chain_problems)

    detail = OrderedDict((
        ("market_id", market_id), ("rows_base", len(base_rows)), ("rows_head", len(head_rows)),
        ("new_row_status", new_row.get("launch_status")),
        ("decided_by", decision.get("decided_by")), ("work_order", decision.get("work_order")),
        ("founder_authorized", authorized_head), ("founder_authorized_unchanged", authorized_base == authorized_head),
        ("lineage_records", len((decision.get("lineage") or {}).get("records") or ())),
        ("base_sha256", base_sha), ("head_sha256", _sha256(head_bytes)),
    ))
    if problems:
        return _result(False, "; ".join(problems[:5]), problems=problems, **detail)
    return _result(True, "one row added at SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH by a "
                         "non-founder writer; every other row, the authorized set and the chain are "
                         "carried forward exactly", **detail)


# --------------------------------------------------------------------------- #
# 3. The release contract instance.
# --------------------------------------------------------------------------- #

def _shared_block_values(base_contracts: Mapping[str, bytes]) -> Dict[str, List[Any]]:
    """block -> distinct values across the base contracts (plain JSON)."""
    seen: Dict[str, List[Any]] = {b: [] for b in CONTRACT_SHARED_BLOCKS}
    seen["deployment_authorization.flags"] = []
    for _mid, raw in base_contracts.items():
        doc = _json(raw.decode("utf-8-sig"))
        for block in CONTRACT_SHARED_BLOCKS:
            value = _plain(doc.get(block))
            if value not in seen[block]:
                seen[block].append(value)
        auth = doc.get("deployment_authorization") or {}
        flags = _plain([auth.get("grants_deployment"), auth.get("asserts_market_complete")])
        if flags not in seen["deployment_authorization.flags"]:
            seen["deployment_authorization.flags"].append(flags)
    return seen


def check_release_contract(head_bytes: bytes, market_id: str, base_contracts: Mapping[str, bytes],
                           *, verify: Optional[Callable[[str], List[str]]] = None) -> "OrderedDict[str, Any]":
    doc = _json(head_bytes.decode("utf-8-sig"))
    problems: List[str] = []
    expected_keys = contract_key_order(doc.keys())
    if list(doc.keys()) != expected_keys:
        unknown = sorted(set(doc) - set(expected_keys))
        missing = sorted(set(expected_keys) - set(doc))
        problems.append("contract keys are not exactly the registration shape (unknown %s, missing %s)"
                        % (unknown, missing))
    if doc.get("schema") != RC.CONTRACT_SCHEMA:
        problems.append("schema is %r" % doc.get("schema"))
    if doc.get("market_id") != market_id:
        problems.append("market_id is %r" % doc.get("market_id"))
    if doc.get("contract_id") != "pettripfinder-%s-release/1.0" % market_id:
        problems.append("contract_id is %r" % doc.get("contract_id"))
    if doc.get("product") != "pettripfinder-%s" % market_id:
        problems.append("product is %r" % doc.get("product"))
    if not isinstance(doc.get("release_name_prefix"), str) or not doc.get("release_name_prefix"):
        problems.append("release_name_prefix must be a non-empty string")
    if not isinstance(doc.get("description"), str):
        problems.append("description must be a string")
    if market_id in base_contracts:
        problems.append("%s already had a release contract at the base" % market_id)
    if not base_contracts:
        problems.append("no base contract exists to prove the shared release rules against")
    shared = _shared_block_values(base_contracts) if base_contracts else {}
    for block in CONTRACT_SHARED_BLOCKS:
        values = shared.get(block) or []
        if len(values) != 1:
            problems.append("%s: the base contracts carry %d distinct values; nothing can be proven" % (block, len(values)))
        elif _plain(doc.get(block)) != values[0]:
            problems.append("%s differs from the value every base contract carries (behavior-bearing)" % block)
    auth = doc.get("deployment_authorization") or {}
    if auth.get("grants_deployment") is not False or auth.get("asserts_market_complete") is not False:
        problems.append("deployment_authorization must state grants_deployment=false and asserts_market_complete=false")
    flags = shared.get("deployment_authorization.flags") or []
    if len(flags) != 1 or flags[0] != [False, False]:
        problems.append("the base contracts do not agree that a contract grants no deployment")
    if not isinstance((doc.get("public_surface") or {}).get("held_hotel_exclusion"), str):
        problems.append("public_surface.held_hotel_exclusion must be the rule text (a string)")
    for block, (required, optional) in CONTRACT_SUBKEYS.items():
        section = doc.get(block)
        if block in CONTRACT_OPTIONAL_KEYS and block not in doc:
            continue
        if not isinstance(section, Mapping):
            problems.append("%s is not an object" % block)
            continue
        unknown = sorted(set(section) - set(required) - set(optional))
        missing = sorted(set(required) - set(section))
        if unknown or missing:
            problems.append("%s carries unknown %s / lacks %s" % (block, unknown, missing))
    census = doc.get("identity_census") or {}
    if census.get("path") != "launch_packages/pettripfinder/identity_census/%s.json" % market_id:
        problems.append("identity_census.path is %r" % census.get("path"))
    pkg = doc.get("policy_package") or {}
    if pkg.get("path") != "launch_packages/pettripfinder/hotel_policy_facts_%s.json" % market_id:
        problems.append("policy_package.path is %r" % pkg.get("path"))
    if pkg.get("identity_authority") is not True:
        problems.append("policy_package.identity_authority must be true")
    if "final_partition" in doc:
        # The referenced file must be the registering market's own
        # final_partition role file (ROLE_PATTERNS), so the reference and the
        # partition it names are proven by the same change set.
        ref = doc.get("final_partition") or {}
        role = "launch_packages/pettripfinder/%s_final_partition_*.json" % market_id.replace("-", "_")
        if not isinstance(ref.get("path"), str) or not fnmatch.fnmatchcase(ref.get("path"), role) \
                or ref.get("path").endswith("_package.json"):
            problems.append("final_partition.path is %r, not this market's %s" % (ref.get("path"), role))
        if not isinstance(ref.get("expected_sha256"), str) or len(ref.get("expected_sha256")) != 64:
            problems.append("final_partition.expected_sha256 must be a 64-hex content digest")
    routes = doc.get("routes") or {}
    if routes.get("market_slug") != market_id:
        problems.append("routes.market_slug is %r" % routes.get("market_slug"))
    if not isinstance(routes.get("route_mode"), str):
        problems.append("routes.route_mode must be a string")
    for block in ("identity_census", "reconciliation", "policy_package", "public_surface", "routes"):
        for key, value in (doc.get(block) or {}).items():
            if key in ("note", "path", "schema", "expected_sha256", "expected_schema_version",
                       "market_slug", "route_mode", "held_hotel_exclusion", "identity_authority"):
                continue
            if not isinstance(value, int) or isinstance(value, bool):
                problems.append("%s.%s must be an integer count" % (block, key))
    disagreements: Optional[List[str]] = None
    if verify is not None:
        try:
            disagreements = list(verify(market_id))
        except Exception as exc:
            problems.append("the contract could not be verified against the derived authority: %s" % str(exc)[:160])
        else:
            problems.extend("derivation: %s" % d for d in disagreements)
    else:
        problems.append("the contract was not verified against the derived authority")
    detail = OrderedDict((
        ("market_id", market_id), ("contract_id", doc.get("contract_id")),
        ("shared_blocks_equal_base", [b for b in CONTRACT_SHARED_BLOCKS
                                      if len(shared.get(b) or []) == 1 and _plain(doc.get(b)) == shared[b][0]]),
        ("reconciliation", _plain(doc.get("reconciliation"))),
        ("derivation_disagreements", disagreements),
    ))
    if problems:
        return _result(False, "; ".join(problems[:5]), problems=problems, **detail)
    return _result(True, "a new contract instance: shared release rules identical to every base contract, "
                         "data fields recognized, numbers agree with derive_authority", **detail)


# --------------------------------------------------------------------------- #
# 4. The build closure.
# --------------------------------------------------------------------------- #

def closure_inputs_for(market_id: str) -> Tuple[str, str]:
    return ("deploy/netlify/release_contracts/%s.json" % market_id,
            "launch_packages/pettripfinder/markets/%s.json" % market_id)


def check_build_closure(base_bytes: bytes, head_bytes: bytes, market_id: str,
                        *, exists: Callable[[str], bool]) -> "OrderedDict[str, Any]":
    base = _json(base_bytes.decode("utf-8-sig"))
    head = _json(head_bytes.decode("utf-8-sig"))
    problems: List[str] = []
    wanted = closure_inputs_for(market_id)
    for key in base:
        if key in ("shared_data_inputs", "remeasured_by"):
            continue
        if _plain(base.get(key)) != _plain(head.get(key)):
            problems.append("closure.%s changed (a build control, never registration data)" % key)
    if set(head) != set(base):
        problems.append("closure keys changed: %s" % sorted(set(head) ^ set(base)))
    base_inputs = list(base.get("shared_data_inputs") or ())
    head_inputs = list(head.get("shared_data_inputs") or ())
    if any(p in base_inputs for p in wanted):
        problems.append("the market's inputs were already declared at the base")
    if head_inputs != sorted(base_inputs + list(wanted)):
        problems.append("shared_data_inputs must be the base inputs plus exactly %s, sorted" % list(wanted))
    base_notes = list(base.get("remeasured_by") or ())
    head_notes = list(head.get("remeasured_by") or ())
    if head_notes[:len(base_notes)] != base_notes or len(head_notes) != len(base_notes) + 1 \
            or not isinstance(head_notes[-1] if head_notes else None, str):
        problems.append("remeasured_by must gain exactly one note and keep the earlier ones")
    for p in wanted:
        if not exists(p):
            problems.append("declared input does not exist: %s" % p)
    try:
        from scripts.pettripfinder import bundle_cache as BC
        with tempfile.TemporaryDirectory() as scratch:
            path = Path(scratch) / "closure.json"
            path.write_bytes(head_bytes)
            BC.load_closure(path)
    except Exception as exc:
        problems.append("the head closure does not load: %s" % str(exc)[:120])
    detail = OrderedDict((
        ("inputs_added", list(wanted)), ("shared_data_inputs_base", len(base_inputs)),
        ("shared_data_inputs_head", len(head_inputs)),
        ("code_modules_unchanged", _plain(base.get("code_modules")) == _plain(head.get("code_modules"))),
        ("per_market_inputs_unchanged", _plain(base.get("per_market_data_inputs")) == _plain(head.get("per_market_data_inputs"))),
    ))
    if problems:
        return _result(False, "; ".join(problems[:5]), problems=problems, **detail)
    return _result(True, "the closure gains exactly the market's two declared inputs and one note; "
                         "code modules, per-market inputs and every build control are unchanged", **detail)


# --------------------------------------------------------------------------- #
# 5. Derived globals.
# --------------------------------------------------------------------------- #

def check_derived_globals(rows: Sequence[Mapping], market_id: str, head: str) -> "OrderedDict[str, Any]":
    from scripts.pettripfinder import market_authority as MA
    problems: List[str] = []
    if head != WORKTREE:
        return _result(None, "the derived globals can only be regenerated from the working tree")
    stale = MA.check_generated_artifacts()
    if stale:
        problems.append("committed globals are not what the shards produce: %s" % stale)
    other_shards = [r["path"] for r in rows
                    if _posix(r["path"]).startswith("launch_packages/pettripfinder/markets/authority/")
                    and not _posix(r["path"]).startswith("launch_packages/pettripfinder/markets/authority/%s/" % market_id)]
    if other_shards:
        problems.append("another market's shard changed: %s" % other_shards[:3])
    try:
        sharded = MA.sharded_market_ids()
    except Exception as exc:
        problems.append("shards unreadable: %s" % str(exc)[:120])
        sharded = ()
    if market_id not in sharded:
        problems.append("%s has no authority shard" % market_id)
    changed_globals = [r["path"] for r in rows if _posix(r["path"]) in (
        "launch_packages/pettripfinder/identity_routing.json", "launch_packages/pettripfinder/hotel_exclusions.json",
        "launch_packages/pettripfinder/seed_businesses.csv", "launch_packages/pettripfinder/ptf_global_authority_manifest.json")]
    detail = OrderedDict((("changed_globals", changed_globals), ("sharded_markets", len(sharded)),
                          ("regeneration_stale", stale)))
    if problems:
        return _result(False, "; ".join(problems[:4]), problems=problems, **detail)
    return _result(True, "the committed globals are byte-identical to a regeneration from the shards and no "
                         "other market's shard changed, so their diff is exactly %s's contribution" % market_id,
                   **detail)


# --------------------------------------------------------------------------- #
# 6. The sealed package and 7. its FAST receipt.
# --------------------------------------------------------------------------- #

def authority_digests(market_id: str, head: str) -> "OrderedDict[str, Optional[str]]":
    """The head digests of the seven files a sealed package is sealed from,
    keyed exactly as ``dependency_input_digests`` keys them."""
    from scripts.pettripfinder import market_package_writer as W
    from scripts.pettripfinder.site_data import published_facts_path
    lp = "launch_packages/pettripfinder/"
    paths: "OrderedDict[str, str]" = OrderedDict((
        ("market", lp + "markets/%s.json" % market_id),
        ("census", lp + "identity_census/%s.json" % market_id),
        ("policy_package", lp + published_facts_path(market_id).name),
        ("exclusions", lp + "markets/authority/%s/hotel_exclusions.json" % market_id),
        ("routing", lp + "markets/authority/%s/identity_routing.json" % market_id),
        ("seed", lp + "markets/authority/%s/seed_businesses.csv" % market_id),
    ))
    partition = W.committed_partition_path(market_id)
    if partition is None:
        us = market_id.replace("-", "_")
        candidates = sorted(SMP.LAUNCH_PACKAGE.glob("%s_final_partition_*.json" % us))
        partition = candidates[-1] if candidates else None
    if partition is not None:
        paths["partition"] = lp + Path(partition).name
    out: "OrderedDict[str, Optional[str]]" = OrderedDict()
    for key, rel in paths.items():
        data = bytes_at(head, rel)
        out[key] = "sha256:" + _sha256(data) if data is not None else None
    return out


def reseal_from_head(package: Mapping, market_id: str) -> str:
    """The digest a FRESH seal of the committed head authority produces under
    the package's own declared delta, parent, source sha, reservations and
    holds. A package whose sections do not re-derive from the head bytes --
    a record dropped while the declared digests were kept -- gets a different
    digest here and covers nothing."""
    from scripts.pettripfinder import market_package_writer as W
    inputs = W.inputs_from_committed_market(
        market_id, execution_zone=str(package["execution_zone"]),
        intended_delta=package["intended_delta"], parent_live_state=package["parent_live_state"],
        source_sha=str(package["created_from_source_sha"]))
    reservations: Dict[str, Mapping] = {}
    for ref in package.get("evidence_references") or ():
        if isinstance(ref, Mapping) and ref.get("paid_reservation"):
            reservations[str(ref["artifact_sha256"])] = ref["paid_reservation"]
    inputs.paid_reservations = reservations
    inputs.founder_holds = list(package.get("founder_holds") or ())
    fresh = W.build_sealed_package(inputs, sealed_at=str(package.get("sealed_at") or ""))
    return str(fresh["package_digest"])


def find_covering_package(market_id: str, head: str) -> Tuple[Optional[Mapping], "OrderedDict[str, Any]"]:
    """The committed sealed package sealed from EXACTLY the head bytes: its
    declared input digests ARE the head digests, and a fresh seal of the head
    authority under its own declaration reproduces its digest."""
    digests = authority_digests(market_id, head)
    covering: List[Mapping] = []
    seen: List[str] = []
    reseal: Dict[str, str] = {}
    for path in SMP.list_packages(market_id):
        try:
            package = SMP.read_sealed(path)
        except SMP.PackageContractError as exc:
            seen.append("%s: %s" % (path.name, str(exc)[:80]))
            continue
        declared = OrderedDict(package.get("dependency_input_digests") or {})
        if _plain(declared) != _plain(digests) or not all(v is not None for v in digests.values()):
            seen.append("%s: declared input digests are not the head bytes" % path.name)
            continue
        try:
            fresh = reseal_from_head(package, market_id)
        except Exception as exc:
            seen.append("%s: does not re-seal from the head authority: %s" % (path.name, str(exc)[:80]))
            continue
        reseal[str(package["package_id"])] = fresh
        if fresh != package["package_digest"]:
            seen.append("%s: a fresh seal of the head authority is %s, not this package" % (path.name, fresh[:23]))
            continue
        covering.append(package)
    detail = OrderedDict((("head_digests", digests), ("packages_seen", seen),
                          ("reseal_digests", reseal), ("covering", len(covering))))
    if not covering:
        return None, detail
    return covering[-1], detail


def check_sealed_package(package: Optional[Mapping], market_id: str, live_state: RI.LiveState,
                         live_idx: RI.ReleaseIndex, lookup: Mapping) -> "OrderedDict[str, Any]":
    problems: List[str] = []
    if package is None:
        return _result(False, "no committed sealed package under markets/packages/%s is sealed from the head "
                              "bytes of the market's authority" % market_id, **lookup)
    issues = SMP.validate(package)
    if issues:
        problems.append("package invalid: %s" % [str(i) for i in issues[:3]])
    if package.get("market_id") != market_id:
        problems.append("package market_id is %r" % package.get("market_id"))
    if package.get("execution_zone") != SMP.ZONE_REGISTERED_LIVE:
        problems.append("package execution_zone is %r, not %s" % (package.get("execution_zone"), SMP.ZONE_REGISTERED_LIVE))
    if package.get("builder_version") != SMP.BUILDER_VERSION:
        problems.append("package builder_version %r is not the current writer %s"
                        % (package.get("builder_version"), SMP.BUILDER_VERSION))
    delta = package.get("intended_delta") or {}
    if delta.get("expected_market_count_delta") != 1:
        problems.append("intended_delta.expected_market_count_delta is %r, a registration joins one market"
                        % delta.get("expected_market_count_delta"))
    intents = [p for p in (delta.get("expected_participation_delta") or ()) if isinstance(p, Mapping)]
    if _plain(intents) != [{"market_id": market_id, "from": False, "to": True}]:
        problems.append("intended_delta.expected_participation_delta must declare %s joining" % market_id)
    for key in ("add_property_ids", "update_property_ids", "remove_property_ids", "change_routes", "remove_routes"):
        if list(delta.get(key) or ()):
            problems.append("intended_delta.%s must be empty for a joining market" % key)
    if delta.get("expected_profile_delta") != 0:
        problems.append("intended_delta.expected_profile_delta must be 0 (a joining market adds to no live market)")
    try:
        package_index = RI.index_from_package(package, participating=True)
        surface = sorted(package_index.routes)
        if sorted(delta.get("add_routes") or ()) != surface:
            problems.append("intended_delta.add_routes is not the package's own published surface "
                            "(%d declared, %d derived)" % (len(delta.get("add_routes") or ()), len(surface)))
    except Exception as exc:
        problems.append("the package does not index: %s" % str(exc)[:120])
        package_index = None
    parent = package.get("parent_live_state") or {}
    expected = live_state.to_dict()
    for field in ("live_deploy_id", "rollback_target", "source_commit", "total_profiles", "sitemap_route_count"):
        if parent.get(field) != expected.get(field):
            problems.append("parent_live_state.%s is %r, live is %r" % (field, parent.get(field), expected.get(field)))
    if list(parent.get("participating_markets") or ()) != list(expected["participating_markets"]):
        problems.append("parent_live_state.participating_markets differ from live")
    if _plain(parent.get("profile_counts") or {}) != _plain(expected["profile_counts"]):
        problems.append("parent_live_state.profile_counts differ from live")
    if parent.get("live_index_digest") != live_idx.digest():
        problems.append("parent_live_state.live_index_digest is stale")
    detail = OrderedDict((
        ("package_id", package.get("package_id")), ("package_digest", package.get("package_digest")),
        ("created_from_source_sha", package.get("created_from_source_sha")),
        ("pet_friendly_records", len(package.get("pet_friendly_records") or ())),
        ("verified_no_pets_records", len(package.get("verified_no_pets_records") or ())),
        ("census_count", (package.get("census") or {}).get("count")),
        ("declared_routes", len(delta.get("add_routes") or ())),
        ("parent_live_deploy_id", parent.get("live_deploy_id")),
    ))
    detail.update(lookup)
    if problems:
        return _result(False, "; ".join(problems[:5]), problems=problems, **detail)
    return _result(True, "package %s is sealed from exactly the head bytes, for REGISTERED_LIVE, declaring "
                         "one joining market against the current live parent" % package.get("package_id"), **detail)


def check_fast_receipt(package: Optional[Mapping], market_id: str, live_state: RI.LiveState,
                       live_idx: RI.ReleaseIndex) -> "OrderedDict[str, Any]":
    from scripts.pettripfinder import fast_release_lane as FL
    if package is None:
        return _result(False, "no package, so no receipt can bind one")
    receipts = FL.eligible_receipts(market_id, package["package_digest"])
    if not receipts:
        return _result(False, "no committed receipt says FAST_DATA_ONLY_RELEASE_ELIGIBLE = YES for %s"
                              % package["package_id"], package_id=package["package_id"])
    path = receipts[-1]
    doc = _json(path.read_text(encoding="utf-8-sig"))
    problems: List[str] = []
    expected_digest = SMP.sha256_text(SMP.canonical_json(
        OrderedDict((k, v) for k, v in doc.items()
                    if k not in ("TIMESTAMPS", "ENVIRONMENT", "PERFORMANCE", "RECEIPT_DIGEST"))))
    if doc.get("RECEIPT_DIGEST") != expected_digest:
        problems.append("the receipt does not hash to its own contents (corrupt)")
    results = doc.get("RESULTS") or {}
    statuses = OrderedDict((r, (results.get(r) or {}).get("status")) for r in FL.RULES)
    passed = [r for r, s in statuses.items() if s == FL.PASS]
    if len(passed) != len(FL.RULES):
        problems.append("rules passed %d/%d: %s" % (len(passed), len(FL.RULES),
                                                     {r: s for r, s in statuses.items() if s != FL.PASS}))
    if doc.get("UNKNOWN_RULES") or doc.get("FAILED_RULES"):
        problems.append("receipt lists UNKNOWN %s / FAILED %s" % (doc.get("UNKNOWN_RULES"), doc.get("FAILED_RULES")))
    if doc.get("MARKET_ID") != market_id:
        problems.append("receipt MARKET_ID is %r" % doc.get("MARKET_ID"))
    if doc.get("PACKAGE_DIGEST") != package["package_digest"] or doc.get("PACKAGE_ID") != package["package_id"]:
        problems.append("receipt binds another package")
    parent = doc.get("PARENT_RELEASE") or {}
    expected = live_state.to_dict()
    for field in ("live_deploy_id", "rollback_target", "source_commit"):
        if parent.get(field) != expected.get(field):
            problems.append("PARENT_RELEASE.%s is %r, live is %r (stale or wrong parent)"
                            % (field, parent.get(field), expected.get(field)))
    if parent.get("live_index_digest") != live_idx.digest():
        problems.append("PARENT_RELEASE.live_index_digest is stale")
    delta_digest = SMP.sha256_text(SMP.canonical_json(package.get("intended_delta") or {}))
    if doc.get("INTENDED_DELTA_DIGEST") != delta_digest:
        problems.append("INTENDED_DELTA_DIGEST does not bind the package's intended delta")
    if doc.get("DEPENDENCY_DIGEST") != FL.dependency_digest(package):
        problems.append("DEPENDENCY_DIGEST does not bind the package's inputs")
    if doc.get("VALIDATION_POLICY_VERSION") != FL.LANE_VERSION:
        problems.append("receipt lane version %r is not %s" % (doc.get("VALIDATION_POLICY_VERSION"), FL.LANE_VERSION))
    env = doc.get("ENVIRONMENT") or {}
    if env.get("builder_version") != package.get("builder_version") or env.get("builder_version") != SMP.BUILDER_VERSION:
        problems.append("receipt builder_version %r does not bind the package writer %s"
                        % (env.get("builder_version"), SMP.BUILDER_VERSION))
    if _plain(env.get("contract_versions")) != _plain(package.get("contract_versions")):
        problems.append("receipt contract_versions differ from the package's")
    if env.get("created_from_source_sha") != package.get("created_from_source_sha"):
        problems.append("receipt was made for a package sealed from another source sha")
    artifacts = doc.get("ARTIFACT_DIGESTS") or {}
    a, b = artifacts.get("changed_market_bundle_sha256_a"), artifacts.get("changed_market_bundle_sha256_b")
    if not a or a != b:
        problems.append("the two cold builds did not produce one bundle digest (determinism)")
    if doc.get("DETERMINISM_RESULT") not in ("BYTE_IDENTICAL", FL.PASS):
        problems.append("DETERMINISM_RESULT is %r" % doc.get("DETERMINISM_RESULT"))
    try:
        receipt_rel = path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        receipt_rel = path.as_posix()
    detail = OrderedDict((
        ("receipt", receipt_rel), ("receipt_digest", doc.get("RECEIPT_DIGEST")),
        ("rules", statuses), ("rules_passed", len(passed)), ("unknown", list(doc.get("UNKNOWN_RULES") or ())),
        ("failed", list(doc.get("FAILED_RULES") or ())), ("determinism", doc.get("DETERMINISM_RESULT")),
        ("changed_market_bundle_sha256", a), ("parent_live_deploy_id", parent.get("live_deploy_id")),
        ("lane_version", doc.get("VALIDATION_POLICY_VERSION")), ("builder_version", env.get("builder_version")),
        ("fast_lane_seconds", (doc.get("PERFORMANCE") or {}).get("total_seconds")),
    ))
    if problems:
        return _result(False, "; ".join(problems[:5]), problems=problems, **detail)
    return _result(True, "receipt %s: 15/15 PASS, 0 UNKNOWN, 0 FAILED, bound to the package, the live parent, "
                         "the intended delta and the current lane and builder versions" % path.name, **detail)


# --------------------------------------------------------------------------- #
# 8. The independent expected release and 9. the identity/route scan.
# --------------------------------------------------------------------------- #

def expected_and_actual(package: Mapping, market_id: str, live_idx: RI.ReleaseIndex,
                        live_state: RI.LiveState) -> Tuple[RI.ReleaseIndex, RI.ReleaseIndex]:
    """EXPECTED = trusted live parent + the sealed package. ACTUAL = every
    registered market's COMMITTED authority at head with the new market
    participating. The new market's entry comes from the package on one side
    and from the committed tree on the other; nothing is shared between them."""
    package_index = RI.index_from_package(package, participating=True)
    expected = RI.compose(live_idx, package_index, participates=True)
    expected.label = "EXPECTED"
    actual = RI.ReleaseIndex(label="ACTUAL_CANDIDATE")
    for mid, idx in live_idx.markets.items():
        if mid == market_id:
            actual.markets[mid] = RI.MarketIndex(**{**idx.__dict__, "participating": True})
        else:
            actual.markets[mid] = idx
    actual.markets = OrderedDict(sorted(actual.markets.items()))
    return expected, actual


def compare_complete(expected: RI.ReleaseIndex, actual: RI.ReleaseIndex) -> "OrderedDict[str, Any]":
    """Every difference between two releases, as complete sets -- never totals."""
    market_findings: List[str] = []
    profile_findings: List[str] = []
    route_findings: List[str] = []
    if set(expected.markets) != set(actual.markets):
        market_findings.append("market sets differ: %s" % sorted(set(expected.markets) ^ set(actual.markets)))
    for mid in sorted(set(expected.markets) & set(actual.markets)):
        e, a = expected.markets[mid], actual.markets[mid]
        if e.participating != a.participating:
            market_findings.append("%s: participation expected %r, actual %r" % (mid, e.participating, a.participating))
        if e.market_slug != a.market_slug or e.route_mode != a.route_mode:
            market_findings.append("%s: slug/route mode differ" % mid)
        if e.verified_no_pets != a.verified_no_pets:
            market_findings.append("%s: verified_no_pets expected %d, actual %d" % (mid, e.verified_no_pets, a.verified_no_pets))
        if e.census_count != a.census_count:
            market_findings.append("%s: census expected %r, actual %r" % (mid, e.census_count, a.census_count))
        for key in sorted(set(e.profiles) - set(a.profiles)):
            profile_findings.append("%s: expected profile %r absent" % (mid, key))
        for key in sorted(set(a.profiles) - set(e.profiles)):
            profile_findings.append("%s: unexpected profile %r present" % (mid, key))
        for key in sorted(set(e.profiles) & set(a.profiles)):
            ep, ap = e.profiles[key], a.profiles[key]
            if ep.route != ap.route:
                route_findings.append("%s: profile %r route expected %s, actual %s" % (mid, key, ep.route, ap.route))
            if ep.record_digest != ap.record_digest:
                profile_findings.append("%s: profile %r record differs" % (mid, key))
            if ep.market_id != ap.market_id:
                profile_findings.append("%s: profile %r ownership differs" % (mid, key))
        for route in sorted(set(e.routes) ^ set(a.routes)):
            route_findings.append("%s: route %s %s" % (mid, route, "missing" if route in e.routes else "unexpected"))
    e_routes = {r for i in expected.markets.values() if i.participating for r in i.routes}
    a_routes = {r for i in actual.markets.values() if i.participating for r in i.routes}
    return OrderedDict((
        ("expected_markets", len(expected.participating)), ("actual_markets", len(actual.participating)),
        ("expected_profiles", expected.total_profiles), ("actual_profiles", actual.total_profiles),
        ("expected_routes", len(e_routes)), ("actual_routes", len(a_routes)),
        ("unexpected_market_changes", len(market_findings)),
        ("unexpected_profile_changes", len(profile_findings)),
        ("unexpected_route_changes", len(route_findings)),
        ("findings", market_findings[:20] + profile_findings[:20] + route_findings[:20]),
        ("passed", not (market_findings or profile_findings or route_findings)),
    ))


def check_expected_release(package: Optional[Mapping], market_id: str, live_idx: RI.ReleaseIndex,
                           live_state: RI.LiveState) -> Tuple["OrderedDict[str, Any]", Optional[Tuple[RI.ReleaseIndex, RI.ReleaseIndex]]]:
    if package is None:
        return _result(False, "no sealed package to derive the expected release from"), None
    expected, actual = expected_and_actual(package, market_id, live_idx, live_state)
    report = compare_complete(expected, actual)
    problems: List[str] = []
    if not report["passed"]:
        problems.append("expected and actual releases differ: %s" % report["findings"][:3])
    package_profiles = len(package.get("pet_friendly_records") or ())
    live_routes = {r for i in live_idx.markets.values() if i.participating for r in i.routes}
    new_routes = set(expected.markets[market_id].routes)
    aggregate = OrderedDict((
        ("parent_markets", len(live_state.participating_markets)),
        ("parent_profiles", live_state.total_profiles), ("parent_routes", len(live_routes)),
        ("package_profiles", package_profiles), ("package_routes", len(new_routes)),
        ("expected_markets", len(live_state.participating_markets) + 1),
        ("expected_profiles", live_state.total_profiles + package_profiles),
        ("expected_routes", len(live_routes) + len(new_routes)),
    ))
    if report["actual_markets"] != aggregate["expected_markets"]:
        problems.append("market count expected %d, actual %d" % (aggregate["expected_markets"], report["actual_markets"]))
    if report["actual_profiles"] != aggregate["expected_profiles"]:
        problems.append("profile count expected %d, actual %d" % (aggregate["expected_profiles"], report["actual_profiles"]))
    if report["actual_routes"] != aggregate["expected_routes"]:
        problems.append("route count expected %d, actual %d" % (aggregate["expected_routes"], report["actual_routes"]))
    if live_routes & new_routes:
        problems.append("the joining market claims %d route(s) the live release already serves" % len(live_routes & new_routes))
    if market_id in live_state.participating_markets:
        problems.append("%s already participates in the live release" % market_id)
    detail = OrderedDict((("expected_digest", expected.digest()), ("actual_digest", actual.digest()),
                          ("aggregate", aggregate)))
    detail.update((k, v) for k, v in report.items() if k != "passed")
    detail["complete_sets_equal"] = report["passed"]
    if problems:
        return _result(False, "; ".join(problems[:4]), problems=problems, **detail), (expected, actual)
    return _result(True, "EXPECTED (live parent + sealed package) and ACTUAL (committed authority) agree as "
                         "complete sets: %d markets, %d profiles, %d routes; 0 unexpected changes"
                         % (report["actual_markets"], report["actual_profiles"], report["actual_routes"]),
                   **detail), (expected, actual)


def check_identity_routes(package: Optional[Mapping], market_id: str, live_idx: RI.ReleaseIndex,
                          releases: Optional[Tuple[RI.ReleaseIndex, RI.ReleaseIndex]]) -> "OrderedDict[str, Any]":
    if package is None or releases is None:
        return _result(False, "no expected release to scan")
    expected, actual = releases
    delta = package.get("intended_delta") or {}
    reports = OrderedDict((
        ("expected", RI.compare(live_idx, expected, package_market=market_id, intended_delta=delta)),
        ("actual", RI.compare(live_idx, actual, package_market=market_id, intended_delta=delta)),
    ))
    problems: List[str] = []
    for label, report in reports.items():
        if not report["passed"]:
            problems.append("%s release: %s" % (label, ["%s %s: %s" % (f["code"], f["market_id"], f["detail"][:80])
                                                          for f in report["findings"][:3]]))
    detail = OrderedDict((label, OrderedDict((("passed", r["passed"]), ("finding_counts", r["finding_counts"]),
                                              ("live_digest", r["live_digest"]), ("proposed_digest", r["proposed_digest"]),
                                              ("seconds", r["seconds"]))))
                         for label, r in reports.items())
    if problems:
        return _result(False, "; ".join(problems), problems=problems, **detail)
    return _result(True, "release_index.compare is clean over both the expected and the actual release: no "
                         "cross-market identity collision, no duplicate route, no ownership movement, every "
                         "live member preserved, every change declared", **detail)


# --------------------------------------------------------------------------- #
# 10. The market-state pin, checked against the package rather than the tree.
# --------------------------------------------------------------------------- #

def expected_pin_block(package: Mapping) -> "OrderedDict[str, int]":
    """What the sealed package says the market's reviewed counts must be."""
    from scripts.pettripfinder import hotel_exclusions as HE
    package_index = RI.index_from_package(package, participating=True)
    exclusions = package.get("verified_no_pets_records") or ()
    pet_friendly = len(package.get("pet_friendly_records") or ())
    no_pets = sum(1 for e in exclusions if e.get("exclusion_state") == HE.VERIFIED_NO_PETS)
    out_of_category = sum(1 for e in exclusions if e.get("exclusion_state") == HE.OUT_OF_CURRENT_CATEGORY)
    census = int((package.get("census") or {}).get("count") or len((package.get("census") or {}).get("hotels") or ()))
    unresolved = len(package.get("unresolved_rows") or ())
    return OrderedDict((
        ("census", census), ("pet_friendly", pet_friendly), ("verified_no_pets", no_pets),
        ("resolved", pet_friendly + no_pets + out_of_category), ("unresolved", unresolved),
        ("out_of_category", out_of_category), ("profiles", len(package_index.profiles)),
        ("corridor_routes", len(package_index.corridor_routes)),
    ))


def check_market_state_pin(base_bytes: bytes, head_bytes: bytes, market_id: str, package: Optional[Mapping],
                           contract_bytes: Optional[bytes]) -> "OrderedDict[str, Any]":
    base = _json(base_bytes.decode("utf-8-sig"))
    head = _json(head_bytes.decode("utf-8-sig"))
    problems: List[str] = []
    for key in base:
        if key in ("reviewed_by", "markets"):
            continue
        if _plain(base.get(key)) != _plain(head.get(key)):
            problems.append("pin.%s changed" % key)
    if set(head) != set(base):
        problems.append("pin keys changed: %s" % sorted(set(head) ^ set(base)))
    if not _work_order_id(head.get("reviewed_by")):
        problems.append("reviewed_by %r is not a work-order id" % head.get("reviewed_by"))
    base_markets = base.get("markets") or {}
    head_markets = head.get("markets") or {}
    if set(head_markets) != set(base_markets) | {market_id}:
        problems.append("pinned markets must be the base set plus %s" % market_id)
    if market_id in base_markets:
        problems.append("%s was already pinned at the base" % market_id)
    for mid, block in base_markets.items():
        if _plain(head_markets.get(mid)) != _plain(block):
            problems.append("existing pin block %s changed" % mid)
    if list(head_markets) != sorted(head_markets):
        problems.append("pin blocks are not sorted by market id")
    block = head_markets.get(market_id) or {}
    expected: Optional[Mapping] = None
    if package is None:
        problems.append("no sealed package to derive the expected block from")
    else:
        expected = expected_pin_block(package)
        for field, value in expected.items():
            if block.get(field) != value:
                problems.append("pin.%s is %r, the sealed package derives %r" % (field, block.get(field), value))
        if set(block) != set(expected) | {"last_moved_by"}:
            problems.append("pin block fields are %s" % sorted(block))
    if not _work_order_id(block.get("last_moved_by")):
        problems.append("last_moved_by %r is not a work-order id" % block.get("last_moved_by"))
    if isinstance(block.get("census"), int) and isinstance(block.get("resolved"), int) \
            and isinstance(block.get("unresolved"), int) and block["census"] != block["resolved"] + block["unresolved"]:
        problems.append("pin arithmetic: census != resolved + unresolved")
    if contract_bytes is not None:
        contract = _json(contract_bytes.decode("utf-8-sig"))
        rec = contract.get("reconciliation") or {}
        pairs = (
            (rec.get("confirmed_identities"), block.get("census"), "reconciliation.confirmed_identities/census"),
            (rec.get("published_pet_friendly"), block.get("pet_friendly"), "reconciliation.published_pet_friendly/pet_friendly"),
            (rec.get("verified_no_pets"), block.get("verified_no_pets"), "reconciliation.verified_no_pets"),
            (rec.get("resolved"), block.get("resolved"), "reconciliation.resolved"),
            (rec.get("unresolved"), block.get("unresolved"), "reconciliation.unresolved"),
            ((contract.get("identity_census") or {}).get("expected_count"), block.get("census"), "identity_census.expected_count"),
            ((contract.get("policy_package") or {}).get("expected_record_count"), block.get("pet_friendly"), "policy_package.expected_record_count"),
            ((contract.get("public_surface") or {}).get("public_hotel_profile_count"), block.get("profiles"), "public_surface.public_hotel_profile_count"),
            ((contract.get("routes") or {}).get("hotel_route_count"), block.get("profiles"), "routes.hotel_route_count"),
            ((contract.get("routes") or {}).get("published_corridor_route_count"), block.get("corridor_routes"), "routes.published_corridor_route_count"),
        )
        for stated, pinned, label in pairs:
            if stated != pinned:
                problems.append("release contract %s=%r disagrees with the pin %r" % (label, stated, pinned))
    else:
        problems.append("no release contract to hold the pin to")
    detail = OrderedDict((("pinned", _plain(block)), ("expected_from_package", _plain(expected)),
                          ("reviewed_by", head.get("reviewed_by")), ("blocks_base", len(base_markets)),
                          ("blocks_head", len(head_markets))))
    if problems:
        return _result(False, "; ".join(problems[:5]), problems=problems, **detail)
    return _result(True, "the pin gains exactly one block whose eight counts equal what the sealed package "
                         "derives, agrees with the release contract, and every other block is byte-identical",
                   **detail)


# --------------------------------------------------------------------------- #
# 11. Release integrity: nothing an authorization protects moved.
# --------------------------------------------------------------------------- #

def check_release_integrity(rows: Sequence[Mapping], live_state: RI.LiveState,
                            participation_result: Mapping) -> "OrderedDict[str, Any]":
    problems: List[str] = []
    touched = [r["path"] for r in rows if any(_posix(r["path"]).startswith(p) for p in PROTECTED_PREFIXES)]
    if touched:
        problems.append("protected release state changed: %s" % touched[:3])
    if live_state.problems:
        problems.append("the live release is not verified: %s" % list(live_state.problems)[:2])
    if not (participation_result.get("detail") or {}).get("founder_authorized_unchanged", False):
        problems.append("the founder-authorized set is not proven unchanged")
    detail = OrderedDict((("live_deploy_id", live_state.deploy_id), ("live_verified", not live_state.problems),
                          ("protected_paths_touched", touched)))
    if problems:
        return _result(False, "; ".join(problems), problems=problems, **detail)
    return _result(True, "no deployment authorization, record, manifest, activation flag, production gate or "
                         "deployment pin moved; the live parent is verified and the authorized set is unchanged",
                   **detail)


# --------------------------------------------------------------------------- #
# The whole proof.
# --------------------------------------------------------------------------- #

def _run(name: str, fn: Callable[[], Any]) -> Any:
    try:
        return fn()
    except Exception as exc:                      # a check that cannot run is UNKNOWN
        return _result(None, "%s could not be established: %s: %s" % (name, type(exc).__name__, str(exc)[:200]))


def evaluate(rows: Sequence[Mapping], base: str, head: str = WORKTREE, *,
             blockers: Sequence[str] = ()) -> "OrderedDict[str, Any]":
    """The NEW_MARKET_REGISTRATION_DATA_ONLY proof over a classified change set.

    Always returns a document; ``ELIGIBLE`` is YES only when every check is
    PASS. The path-level gate runs first so a change set that is not a
    registration costs one registry listing and nothing else.
    """
    started = time.perf_counter()
    checks: "OrderedDict[str, OrderedDict]" = OrderedDict()
    gate = classify_change_set(rows, base=base, head=head, blockers=blockers)
    market_id = gate["market_id"]
    checks["change_set"] = gate["result"]
    roles = gate["roles"]
    gate_detail = gate["result"].get("detail") or {}
    partition = gate_detail.get("partition") or OrderedDict((b, []) for b in BUCKETS)
    registration_paths = [p for p, role in roles.items()
                          if role not in (ROLE_COMPANION, ROLE_MARKET_LOCAL, ROLE_DISCOVERY_MARKET_CONFIG)]
    market_local_paths = list(partition.get(BUCKET_MARKET_LOCAL) or ())
    change_class = gate_detail.get("change_class") or CLASS_REGISTRATION

    package: Optional[Mapping] = None
    live_idx: Optional[RI.ReleaseIndex] = None
    live_state: Optional[RI.LiveState] = None
    releases = None
    if gate["result"]["pass"]:
        contract_rel = "deploy/netlify/release_contracts/%s.json" % market_id

        def _read(rev: str, rel: str) -> bytes:
            data = bytes_at(rev, rel)
            if data is None:
                raise RegistrationProofError("%s is absent at %s" % (rel, rev))
            return data

        checks["market_local_zone"] = _run("market_local_zone", lambda: check_market_local_zone(gate))
        checks["discovery_config"] = _run("discovery_config", lambda: check_discovery_config(rows, base, head, market_id))
        checks["registration_input"] = _run("registration_input", lambda: check_registration_input(rows, head, market_id))
        checks["identity_resolutions"] = _run("identity_resolutions", lambda: check_identity_resolutions(
            rows, base, head, market_id))
        checks["participation"] = _run("participation", lambda: check_participation(
            _read(base, PARTICIPATION_PATH), _read(head, PARTICIPATION_PATH), market_id))

        def _contracts() -> "OrderedDict[str, bytes]":
            out: "OrderedDict[str, bytes]" = OrderedDict()
            for mid in release_contract_ids_at(base):
                data = bytes_at(base, "deploy/netlify/release_contracts/%s.json" % mid)
                if data is not None:
                    out[mid] = data
            return out

        checks["release_contract"] = _run("release_contract", lambda: check_release_contract(
            _read(head, contract_rel), market_id, _contracts(),
            verify=(RC.verify_contract if head == WORKTREE else None)))
        checks["build_closure"] = _run("build_closure", lambda: check_build_closure(
            _read(base, CLOSURE_PATH), _read(head, CLOSURE_PATH), market_id,
            exists=lambda rel: bytes_at(head, rel) is not None))
        checks["derived_globals"] = _run("derived_globals", lambda: check_derived_globals(rows, market_id, head))

        def _live() -> Tuple[RI.ReleaseIndex, RI.LiveState]:
            idx, state, problems = live_index()
            if problems:
                raise RegistrationProofError("CURRENT_VERIFIED_LIVE could not be established: %s" % problems[:2])
            return idx, state

        try:
            live_idx, live_state = _live()
        except Exception as exc:
            live_failure = _result(None, "%s: %s" % (type(exc).__name__, str(exc)[:200]))
            for name in ("sealed_package", "fast_receipt", "expected_release", "identity_routes",
                         "market_state_pin", "release_integrity"):
                checks[name] = live_failure
        else:
            if head == WORKTREE:
                package, lookup = find_covering_package(market_id, head)
            else:
                package, lookup = None, OrderedDict((("why", "packages are read from the working tree only"),))
            checks["sealed_package"] = _run("sealed_package", lambda: check_sealed_package(
                package, market_id, live_state, live_idx, lookup))
            checks["fast_receipt"] = _run("fast_receipt", lambda: check_fast_receipt(
                package, market_id, live_state, live_idx))

            def _expected():
                nonlocal releases
                result, releases = check_expected_release(package, market_id, live_idx, live_state)
                return result

            checks["expected_release"] = _run("expected_release", _expected)
            checks["identity_routes"] = _run("identity_routes", lambda: check_identity_routes(
                package, market_id, live_idx, releases))
            checks["market_state_pin"] = _run("market_state_pin", lambda: check_market_state_pin(
                _read(base, MARKET_STATE_PIN_PATH), _read(head, MARKET_STATE_PIN_PATH), market_id, package,
                bytes_at(head, contract_rel)))
            checks["release_integrity"] = _run("release_integrity", lambda: check_release_integrity(
                rows, live_state, checks["participation"]))
    for name in CHECKS:
        if name not in checks:
            checks[name] = _result(False, "not evaluated: the change set is not a registration")

    eligible = all(c["pass"] for c in checks.values())
    unknown = [n for n, c in checks.items() if c["status"] == UNKNOWN]
    failed = [n for n, c in checks.items() if c["status"] == FAIL]
    if eligible:
        why = ("every %s check passed for %s: the change set is one market's %s, proven by field, with a sealed "
               "package, an eligible FAST receipt, and an independently derived expected release that the "
               "committed candidate matches as complete sets"
               % (change_class, market_id,
                  "first registration (market-local zone + registration zone + derived outputs)"
                  if change_class == CLASS_COMPOSITE else "registration"))
    else:
        first = failed[0] if failed else (unknown[0] if unknown else "change_set")
        why = "%s: %s" % (first, checks[first]["why"])
    expected_detail = (checks["expected_release"].get("detail") or {}) if eligible else {}
    return OrderedDict((
        ("schema", SCHEMA),
        ("proof_version", PROOF_VERSION),
        ("market_id", market_id),
        ("base", base), ("head", head),
        ("CHANGE_CLASS", change_class if eligible else None),
        ("candidate_change_class", change_class),
        ("registration_paths", registration_paths),
        ("market_local_paths", market_local_paths),
        ("narrowed_paths", sorted(set(registration_paths) | set(market_local_paths))),
        ("companion_paths", [p for p, role in roles.items() if role == ROLE_COMPANION]),
        ("partition", partition),
        ("accounting", gate_detail.get("accounting")),
        ("checks", checks),
        ("failed_checks", failed), ("unknown_checks", unknown),
        ("ELIGIBLE", YES if eligible else NO),
        ("FULL_REGRESSION_REQUIRED", NO if eligible else YES),
        ("REMOTE_BROAD_JOBS_REQUIRED", 0 if eligible else None),
        ("UNCHANGED_MARKETS_REBUILT", 0 if eligible else None),
        ("REACHES", "AUTHORIZATION_READY" if eligible else "NOT_ELIGIBLE"),
        ("authorizes_deployment", False),
        ("package_id", package.get("package_id") if package else None),
        ("package_digest", package.get("package_digest") if package else None),
        ("receipt", (checks["fast_receipt"].get("detail") or {}).get("receipt")),
        ("live_deploy_id", live_state.deploy_id if live_state else None),
        ("expected_release", OrderedDict((k, expected_detail.get(k)) for k in (
            "expected_digest", "actual_digest", "actual_markets", "actual_profiles", "actual_routes",
            "unexpected_market_changes", "unexpected_profile_changes", "unexpected_route_changes")) if eligible else None),
        ("seconds", round(time.perf_counter() - started, 3)),
        ("why", why),
    ))


# --------------------------------------------------------------------------- #
# The committed contract: what the class permits, by document and by field.
# --------------------------------------------------------------------------- #

FIELD_DATA = "DATA_NARROWABLE"
FIELD_DERIVED = "DERIVED_CHECKED_INDEPENDENTLY"
FIELD_BEHAVIOR = "BEHAVIOR_WIDENS"
FIELD_PROTECTED = "PROTECTED_INDEPENDENTLY"


def field_level_eligibility_matrix() -> List["OrderedDict[str, str]"]:
    rows: List[Tuple[str, str, str, str]] = [
        # participation
        (PARTICIPATION_PATH, "markets[<new>] (market_id, launch_status, note)", FIELD_DATA,
         "exactly one new row at SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH"),
        (PARTICIPATION_PATH, "markets[<existing>]", FIELD_PROTECTED, "byte-identical to the base row"),
        (PARTICIPATION_PATH, "markets[*].launch_status = FOUNDER_AUTHORIZED_FOR_LAUNCH", FIELD_PROTECTED,
         "never written by a registration; the authorized set must equal the base's"),
        (PARTICIPATION_PATH, "decision.work_order / decided_by / decided_on / reason", FIELD_DATA,
         "decided_by must be the writing work order and must not name the founder"),
        (PARTICIPATION_PATH, "decision.markets_added / founder_authorized_set_unchanged", FIELD_DATA,
         "[<new>] and true"),
        (PARTICIPATION_PATH, "decision.supersedes", FIELD_DERIVED, "sha256 of the exact base bytes, base work order, base authorized set"),
        (PARTICIPATION_PATH, "decision.lineage.records", FIELD_DERIVED, "the base chain (repair-resolved) plus the base record"),
        (PARTICIPATION_PATH, "decision.<any other key>", FIELD_BEHAVIOR, "unknown decision field widens"),
        (PARTICIPATION_PATH, "schema / what_this_is / launch_statuses", FIELD_BEHAVIOR, "semantics; any change widens"),
        # release contract
        ("deploy/netlify/release_contracts/<new>.json", "schema / market_id / contract_id / product", FIELD_DATA,
         "the registration shape for <new>"),
        ("deploy/netlify/release_contracts/<new>.json", "release_name_prefix / description / *.note", FIELD_DATA, "free text"),
        ("deploy/netlify/release_contracts/<new>.json", "identity_census / reconciliation / policy_package / public_surface / routes",
         FIELD_DERIVED, "recognized sub-keys only; every count agrees with release_contracts.derive_authority"),
        ("deploy/netlify/release_contracts/<new>.json", "final_partition (optional; path / schema / expected_sha256 / expected_count / note)",
         FIELD_DERIVED, "the market's own <us>_final_partition_*.json role file; path, schema, content digest and count "
                        "agree with the committed file (release_contracts.final_partition_disagreements); the "
                        "whole-site assembler resolves the partition from this block, never from a table"),
        ("deploy/netlify/release_contracts/<new>.json", "canonical / minimum_release_gates / forbidden_output_tokens / publish",
         FIELD_BEHAVIOR, "must EQUAL the single value every base contract carries"),
        ("deploy/netlify/release_contracts/<new>.json", "deployment_authorization.grants_deployment / asserts_market_complete",
         FIELD_BEHAVIOR, "must be false / false, as every base contract states"),
        ("deploy/netlify/release_contracts/<new>.json", "<any other top-level key>", FIELD_BEHAVIOR, "unknown configuration widens"),
        ("deploy/netlify/release_contracts/<existing>.json", "*", FIELD_PROTECTED, "an existing contract may not change"),
        # closure
        (CLOSURE_PATH, "shared_data_inputs", FIELD_DATA, "base inputs plus exactly the market's contract and market document, sorted"),
        (CLOSURE_PATH, "remeasured_by", FIELD_DATA, "one appended note"),
        (CLOSURE_PATH, "code_modules / per_market_data_inputs / schema / measured_from / staged_tree_note / what_this_is",
         FIELD_BEHAVIOR, "build controls; any change widens"),
        # pin
        (MARKET_STATE_PIN_PATH, "markets[<new>].census/pet_friendly/verified_no_pets/resolved/unresolved/out_of_category/profiles/corridor_routes",
         FIELD_DERIVED, "equal to what the sealed package derives; equal to the release contract"),
        (MARKET_STATE_PIN_PATH, "markets[<new>].last_moved_by / reviewed_by", FIELD_DATA, "a work-order id"),
        (MARKET_STATE_PIN_PATH, "markets[<existing>]", FIELD_PROTECTED, "byte-identical to the base block"),
        (MARKET_STATE_PIN_PATH, "schema / what_this_is / fields", FIELD_BEHAVIOR, "semantics; any change widens"),
        (DEPLOYMENT_STATE_PIN_PATH, "*", FIELD_PROTECTED, "the live pin never moves at registration"),
        # market data
        ("launch_packages/pettripfinder/markets/<new>.json", "*", FIELD_DATA, "the new market's own registry document (sealed into the package)"),
        ("launch_packages/pettripfinder/markets/authority/<new>/*", "*", FIELD_DATA, "the new market's own shard (sealed into the package)"),
        ("launch_packages/pettripfinder/{identity_census/<new>.json,hotel_policy_facts_<new>.json,<new>_final_partition_*.json}",
         "*", FIELD_DATA, "the new market's own authority (sealed into the package)"),
        ("launch_packages/pettripfinder/{identity_routing.json,hotel_exclusions.json,seed_businesses.csv,ptf_global_authority_manifest.json}",
         "*", FIELD_DERIVED, "byte-identical to a regeneration from the shards; no other shard changed"),
        ("launch_packages/pettripfinder/markets/authority/<existing>/*", "*", FIELD_PROTECTED, "another market's shard may not change"),
        # protected
        ("deploy/netlify/deployment_authorizations/*, deployment_records/*, global_deployment_manifest.json", "*",
         FIELD_PROTECTED, "founder authorization and deployment records never move at registration"),
        ("launch_packages/pettripfinder/{fast_release_activation.json,release_production_gate.json}", "*",
         FIELD_PROTECTED, "activation and the production gate never move at registration"),
        ("tests/**, scripts/**, *.py", "*", FIELD_BEHAVIOR, "code and test expectations are never registration data "
                                                            "-- unless the path is the registering market's own and "
                                                            "passes all five isolation conditions in registration mode"),
        # PTF-FINAL-FRESH-MARKET-REGISTRATION-REENGINEERING-001: the composite zones
        ("scripts/pettripfinder/<new_us>_*.py, markets/reports/<new_us>_*.json, markets/{packages,staging,receipts}/<new>/**",
         "*", FIELD_DERIVED, "MARKET_LOCAL_ACQUISITION: proven by market_local_isolation in registration mode -- "
                             "namespace (the registering market's template zone), imports (stdlib / allow-list / "
                             "transaction modules), writes (zone roots / this change set's registration data), "
                             "reachability (nothing shared names it; subprocesses read-only), registration "
                             "(unregistered at the base, registered by this set)"),
        ("scripts/pettripfinder/<new_us>_*.py", "imports assemble_* / generate_* / renderers / readers / policy / routing",
         FIELD_BEHAVIOR, "a helper that imports or runs site runtime is rejected for that dependency"),
        (DISCOVERY_CONFIG_PATTERN, "*", FIELD_DERIVED, "loads through discovery.market_config for exactly <new>; also market-local"),
        (OSM_EXTRACTS_PATH, "extracts[<new row>]", FIELD_DATA, "exactly one new row, markets == [<new>], its own index_path"),
        (OSM_EXTRACTS_PATH, "extracts[<existing>]", FIELD_PROTECTED, "semantically identical to the base row"),
        (OSM_EXTRACTS_PATH, "schema / what_this_is / provenance", FIELD_BEHAVIOR, "semantics; any change widens"),
        ("scripts/pettripfinder/discovery/**", "*", FIELD_BEHAVIOR, "discovery code and provider configuration; any change widens"),
        (REGISTRATION_INPUT_PATTERN, "schema / market_id", FIELD_DATA, "ptf-market-proposed-authority/1.0 for exactly <new>"),
        (REGISTRATION_INPUT_PATTERN, "pet_friendly[] / verified_no_pets[] / *_count / authority_total", FIELD_DERIVED,
         "counts reconcile; every identity is in <new>'s census; the shard binds (market_registration_cli.verify)"),
        ("launch_packages/pettripfinder/<other_us>_proposed_authority_*.json", "*", FIELD_PROTECTED, "another market's input may not change"),
        ("scripts/pettripfinder/market_registration_cli.py, market_proposed_authority_cli.py", "*", FIELD_BEHAVIOR,
         "the input's reader and writer; any change widens"),
        (IDENTITY_RESOLUTIONS_PATH, "resolutions[<new>]", FIELD_DERIVED,
         "market_id == <new>; validates under publication_guard; names exact committed identities; DISTINCT pairwise "
         "under hotel_exclusions.co_located_distinct; resolution_hash re-derives; no slug/name collision"),
        (IDENTITY_RESOLUTIONS_PATH, "resolutions[<existing>]", FIELD_PROTECTED, "byte-identical and in place"),
        (IDENTITY_RESOLUTIONS_PATH, "schema / contract / market / note", FIELD_BEHAVIOR, "semantics; any change widens"),
    ]
    return [OrderedDict((("document", d), ("field", f), ("policy", p), ("rule", r))) for d, f, p, r in rows]


def contract_document() -> "OrderedDict[str, Any]":
    """The committed, machine-readable registration-data-only contract."""
    return OrderedDict((
        ("schema", CONTRACT_SCHEMA),
        ("work_order", "PTF-NEW-MARKET-REGISTRATION-DATA-ONLY-POLICY-001"),
        ("extended_by", "PTF-FINAL-FRESH-MARKET-REGISTRATION-REENGINEERING-001"),
        ("proof_version", PROOF_VERSION),
        ("change_class", "NEW_MARKET_REGISTRATION_DATA_ONLY"),
        ("composite_change_class", CLASS_COMPOSITE),
        ("composite_buckets", list(BUCKETS)),
        ("narrow_buckets", sorted(NARROW_BUCKETS)),
        ("composite_rule", "the change set narrows only when SHARED_BEHAVIOR_CHANGE = 0 and UNKNOWN = 0, the bucket "
                           "sizes sum to the changed-path count, every market-local path passes all five isolation "
                           "conditions in registration mode, and every typed input passes its field check"),
        ("fresh_market_roles", [OrderedDict((("role", role), ("path", pattern), ("required", required),
                                             ("statuses", list(statuses))))
                                for role, pattern, required, statuses in FRESH_MARKET_ROLE_PATTERNS]),
        ("original_checks_unchanged", list(ORIGINAL_CHECKS)),
        ("what_this_is", "The one permitted registration operation Regression V2 may narrow: exactly ONE "
                         "previously absent market joins the registry, the participation record, the build "
                         "closure and the market-state pin, with a sealed package and an eligible FAST receipt, "
                         "and every changed field is proven by this contract's field policy. Granted to a whole "
                         "change set, never to a path; UNKNOWN is a failure; the class reaches "
                         "AUTHORIZATION_READY and authorizes nothing."),
        ("registration_roles", [OrderedDict((("role", role), ("path", pattern), ("required", required),
                                             ("statuses", list(statuses))))
                                for role, pattern, required, statuses in ROLE_PATTERNS]),
        ("companion_classes", sorted(COMPANION_CLASSES)),
        ("registration_owned_blockers", list(REGISTRATION_OWNED_BLOCKERS)),
        ("protected_paths", list(PROTECTED_PREFIXES)),
        ("checks", list(CHECKS)),
        ("field_policies", OrderedDict(((FIELD_DATA, "a registration fact; narrowable when it takes the permitted value"),
                                        (FIELD_DERIVED, "checked against an independent derivation (the sealed package, "
                                                        "the base record's bytes, the shards, derive_authority)"),
                                        (FIELD_BEHAVIOR, "behavior-bearing; any change ends the narrowing"),
                                        (FIELD_PROTECTED, "keeps its own independent protection; any change ends the narrowing")))),
        ("field_level_eligibility_matrix", field_level_eligibility_matrix()),
        ("verdict", OrderedDict((("ELIGIBLE", "YES only when every check is PASS"),
                                 ("FULL_REGRESSION_REQUIRED", "NO when eligible"),
                                 ("REMOTE_BROAD_JOBS_REQUIRED", 0),
                                 ("UNCHANGED_MARKETS_REBUILT", 0),
                                 ("reaches", "AUTHORIZATION_READY"),
                                 ("does_not", "authorize deployment, move a live pin, enable activation, or "
                                              "relax the current-parent, exact-bytes or rollback guards")))),
        ("fallback", "any UNKNOWN or failed check leaves every path in its path class; the existing "
                     "DEPLOYMENT_CHANGE / AUTHORITY_CHANGE rows then require the broad regression"),
    ))


def main(argv: Optional[Sequence[str]] = None) -> int:  # pragma: no cover - CLI
    import argparse
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("contract", help="print or export the registration-data-only contract")
    s.add_argument("--out")
    s = sub.add_parser("evaluate", help="run the proof over a change set, standalone")
    s.add_argument("--base", required=True)
    s.add_argument("--head", default=WORKTREE)
    s.add_argument("--out")
    args = p.parse_args(argv)
    if args.command == "contract":
        doc = contract_document()
        text = json.dumps(doc, indent=1, ensure_ascii=False) + "\n"
        if args.out:
            Path(args.out).write_text(text, encoding="utf-8", newline="\n")
            print("%s: %d field rows" % (args.out, len(doc["field_level_eligibility_matrix"])))
        else:
            print(text)
        return 0
    from scripts.pettripfinder import regression_delta as RD
    files = RD.changed_files(args.base, args.head)
    rows = []
    for rel, status in files.items():
        classes, rule = RD.classify_path(rel)
        rows.append(OrderedDict((("path", rel), ("status", status), ("classes", list(classes)), ("rule", rule))))
    blockers = [rel for rel in files if RD.is_narrowing_blocker(rel)]
    doc = evaluate(rows, args.base, args.head, blockers=blockers)
    if args.out:
        Path(args.out).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n",
                                  encoding="utf-8", newline="\n")
    for name, check in doc["checks"].items():
        print("%-8s %-20s %s" % (check["status"], name, check["why"][:100]))
    print("ELIGIBLE: %s (%.1fs)" % (doc["ELIGIBLE"], doc["seconds"]))
    return 0 if doc["ELIGIBLE"] == YES else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = [
    "SCHEMA", "PROOF_VERSION", "CONTRACT_SCHEMA", "CONTRACT_PATH", "CHECKS", "ROLE_PATTERNS",
    "REGISTRATION_OWNED_BLOCKERS", "PROTECTED_PREFIXES", "COMPANION_CLASSES",
    "role_of", "classify_change_set", "check_participation", "check_release_contract",
    "check_build_closure", "check_derived_globals", "authority_digests", "reseal_from_head", "find_covering_package",
    "check_sealed_package", "check_fast_receipt", "expected_and_actual", "compare_complete",
    "check_expected_release", "check_identity_routes", "expected_pin_block", "check_market_state_pin",
    "check_release_integrity", "evaluate", "field_level_eligibility_matrix", "contract_document",
    "check_market_local_zone", "check_discovery_config", "check_registration_input", "check_identity_resolutions",
    "BUCKETS", "CLASS_COMPOSITE", "CLASS_REGISTRATION", "FRESH_MARKET_ROLE_PATTERNS", "bucket_of_role",
]
