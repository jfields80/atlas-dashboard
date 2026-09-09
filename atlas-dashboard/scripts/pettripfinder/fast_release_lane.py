"""ATLAS-THROUGHPUT-003 -- FAST_DATA_ONLY_RELEASE: the critical release-safety
lane for a sealed market package, and the machine-readable receipt it writes.

Fifteen rules, A to O, each answering one release hazard of the 001 safety
map with a direct check instead of a broad regression:

    A  package schema valid            sealed_market_package.validate (H10)
    B  identity valid                  the typed writer's identity rules (H1, H4)
    C  first-party binding valid       first_party_binding.evaluate_package (H2)
    D  policy semantics valid          policy_schema + evidence contracts (H3)
    E  route references valid          routing authority + census binding (H5, H7)
    F  market partition valid          partition contract + reconciliation (H5)
    G  whole-release indexes clean     release_index.compare collisions (H4, H5)
    H  unrelated live members kept     release_index.compare preservation (H6, H7)
    I  every removal intended          intended delta accounting (H8)
    J  changed market builds           the real per-market assembler, staged (H3, H10)
    K  changed market deterministic    two COLD builds, digests equal (H9)
    L  hashes internally consistent    seal, evidence index, artifacts (H10)
    M  evidence fresh, not revoked     capture age + revocation registry (H2)
    N  rollback / current live valid   parent live state == live records (H11, H12)
    O  paid provenance                 reservation key per paid capture (H13)

A rule is PASS, FAIL or UNKNOWN. UNKNOWN means the rule could not be
established -- a live state the records disagree on, a build that was not
run -- and it makes the package NOT ELIGIBLE exactly as a FAIL does. The
receipt names every rule, its result, its cost, the digests it saw, and the
conditions under which it stops being true.

The lane never renders an unchanged market and never touches committed
authority: the changed market is staged into a temporary tree and built
there (package_staging), the live release is read from the committed
records, and the receipt is written to the market's own receipts directory.

The lane PROVES eligibility. Whether a Regression V2 plan may act on the
proof is a separate, closed decision: ``fast_release_activation.json``
(FAST_PATH_PRODUCTION_ACTIVATION = DISABLED, empty pilot allowlist).
"""

from __future__ import annotations

import json
import platform
import shutil
import sys
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from scripts.pettripfinder import first_party_binding as FPB
from scripts.pettripfinder import market_package_writer as WRITER
from scripts.pettripfinder import package_staging as STAGING
from scripts.pettripfinder import release_index as RI
from scripts.pettripfinder import sealed_market_package as SMP
from scripts.pettripfinder.acquisition.paid_attempt_ledger import attempt_id as paid_attempt_id
from scripts.pettripfinder.contracts import evidence as EVIDENCE

REPO_ROOT = SMP.REPO_ROOT
LAUNCH_PACKAGE = SMP.LAUNCH_PACKAGE

LANE = "FAST_DATA_ONLY_RELEASE"
LANE_VERSION = "ptf-fast-data-only-release/1.0"
RECEIPT_SCHEMA = "ptf-fast-release-receipt/1.0"
ACTIVATION_PATH = LAUNCH_PACKAGE / "fast_release_activation.json"
REVOCATIONS_PATH = LAUNCH_PACKAGE / "evidence_revocations.json"

PASS = "PASS"
FAIL = "FAIL"
UNKNOWN = "UNKNOWN"
YES = "YES"
NO = "NO"

#: Evidence older than this, relative to the validation time, no longer
#: supports a release without re-capture.
EVIDENCE_MAX_AGE_DAYS = 365

RULES: "OrderedDict[str, str]" = OrderedDict((
    ("A", "package schema valid"),
    ("B", "identity valid"),
    ("C", "first-party policy binding valid"),
    ("D", "policy semantics valid"),
    ("E", "route references valid"),
    ("F", "market partition valid"),
    ("G", "proposed whole-release identity/route indexes contain no forbidden collision"),
    ("H", "every unrelated live market/member is preserved"),
    ("I", "every removal is explicitly intended"),
    ("J", "changed-market artifact builds successfully"),
    ("K", "changed-market output deterministic"),
    ("L", "package/artifact hashes internally consistent"),
    ("M", "required evidence freshness/revocation rules satisfied"),
    ("N", "rollback/current-live preservation metadata valid"),
    ("O", "paid acquisitions used by the package satisfy reservation provenance"),
))

#: Writer issue codes by the rule that owns them.
_B_CODES = frozenset({"DUPLICATE_IDENTITY", "MISSING_IDENTITY", "IDENTITY_NOT_CANONICAL",
                      "SAME_PREMISES_DUPLICATE", "SAME_PREMISES_UNPROVEN", "SENTINEL_VALUE",
                      "MARKET_CONTRACT", "WRONG_MARKET"})
_D_CODES = frozenset({"PUBLICATION_BLOCKED", "FEE_DEPOSIT_CONFLATION", "INVALID_POLICY_STATUS",
                      "CONFLICTING_STATUS", "EXCLUSION_CONTRACT"})
_E_CODES = frozenset({"INVALID_ROUTE", "ROUTING_CONTRACT", "ROUTE_IDENTITY_NOT_IN_CENSUS",
                      "INVALID_MARKET_ASSIGNMENT"})
_F_CODES = frozenset({"ORPHAN_PARTITION", "UNRESOLVED_PROMOTED_CLEAN", "NO_DISPLAY_ROW",
                      "AMBIGUOUS_DISPLAY_ROW", "SEED_COLUMNS"})
_L_CODES = frozenset({"MISSING_EVIDENCE_BINDING", "POLICY_EVIDENCE_IDENTITY_MISMATCH", "DUPLICATE_REF"})


def _owner_rule(code: str) -> str:
    if code in _B_CODES or code.startswith("CENSUS_"):
        return "B"
    if code in _D_CODES or code.startswith("POLICY_") or code.startswith("EVIDENCE_"):
        return "D"
    if code in _E_CODES:
        return "E"
    if code in _F_CODES or code.startswith("PARTITION_"):
        return "F"
    if code in _L_CODES:
        return "L"
    return "D"


class RuleResult(OrderedDict):
    """``rule``, ``name``, ``status``, ``seconds``, ``detail``, ``problems``."""


def _result(rule: str, status: str, started: float, detail: Mapping = (),
            problems: Sequence[str] = ()) -> RuleResult:
    return RuleResult((("rule", rule), ("name", RULES[rule]), ("status", status),
                       ("seconds", round(time.perf_counter() - started, 3)),
                       ("detail", OrderedDict(detail)), ("problems", list(problems)[:50]),
                       ("problem_count", len(problems))))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


# --------------------------------------------------------------------------- #
# Policy files.
# --------------------------------------------------------------------------- #

def load_activation(path: Optional[Path] = None) -> "OrderedDict[str, Any]":
    p = Path(path) if path else ACTIVATION_PATH
    if not p.is_file():
        return OrderedDict((("FAST_PATH_PRODUCTION_ACTIVATION", "DISABLED"), ("pilot_allowlist", [])))
    doc = json.loads(p.read_text(encoding="utf-8-sig"), object_pairs_hook=OrderedDict)
    if doc.get("FAST_PATH_PRODUCTION_ACTIVATION") not in ("DISABLED", "ENABLED"):
        doc["FAST_PATH_PRODUCTION_ACTIVATION"] = "DISABLED"
    return doc


def production_activation_allowed(market_id: str, activation: Optional[Mapping] = None) -> bool:
    doc = activation if activation is not None else load_activation()
    return doc.get("FAST_PATH_PRODUCTION_ACTIVATION") == "ENABLED" \
        and market_id in (doc.get("pilot_allowlist") or ())


def load_revocations(path: Optional[Path] = None) -> Dict[str, Mapping]:
    p = Path(path) if path else REVOCATIONS_PATH
    if not p.is_file():
        return {}
    doc = json.loads(p.read_text(encoding="utf-8-sig"))
    return {SMP.normalise_sha256(str(r.get("artifact_sha256") or "")): r
            for r in (doc.get("revoked") or ()) if isinstance(r, Mapping)}


# --------------------------------------------------------------------------- #
# Re-validation: the package through the typed writer.
# --------------------------------------------------------------------------- #

def inputs_from_package(package: Mapping) -> WRITER.PackageInputs:
    """The package's own sections as writer inputs, so the writer can prove
    the package re-derives (and re-validates) from what it carries."""
    reservations = {}
    for ref in package.get("evidence_references") or ():
        if ref.get("paid_reservation"):
            reservations[str(ref["artifact_sha256"])] = ref["paid_reservation"]
    relations = {r["identity_key"]: r["relation"] for r in package.get("identity_records") or ()
                 if isinstance(r, Mapping) and r.get("relation")}
    scorecard = OrderedDict(package.get("coverage_scorecard") or {})
    scorecard.pop("counts_by_partition_state", None)
    return WRITER.PackageInputs(
        market_id=str(package["market_id"]),
        execution_zone=str(package["execution_zone"]),
        created_from_source_sha=str(package["created_from_source_sha"]),
        market=package["market"], census=package["census"],
        pet_friendly_records=package["pet_friendly_records"],
        verified_no_pets_records=package["verified_no_pets_records"],
        official_routes=package["official_routes"], seed_rows=package["seed_rows"],
        partition=package["partition"], intended_delta=package["intended_delta"],
        parent_live_state=package["parent_live_state"],
        dependency_input_digests=package["dependency_input_digests"],
        evidence_references=package["evidence_references"],
        paid_reservations=reservations, founder_holds=package["founder_holds"],
        relations=relations, coverage_scorecard=scorecard,
    )


def revalidate(package: Mapping) -> Tuple[List[SMP.Issue], Optional[str]]:
    """``(issues, re-derived digest)`` -- the writer over the package's own
    sections. An empty issue list with a matching digest means the package
    IS what its sections say."""
    try:
        resealed = WRITER.build_sealed_package(inputs_from_package(package),
                                              sealed_at=str(package.get("sealed_at") or ""))
    except WRITER.PackageWriteError as exc:
        return list(exc.issues), None
    return [], resealed["package_digest"]


# --------------------------------------------------------------------------- #
# The lane.
# --------------------------------------------------------------------------- #

def run_fast_lane(package: Mapping, *, work_dir: Path,
                  live: Optional[Tuple[RI.ReleaseIndex, RI.LiveState, List[str]]] = None,
                  build: bool = True, determinism: bool = True,
                  now: Optional[datetime] = None,
                  revocations: Optional[Mapping[str, Mapping]] = None,
                  activation: Optional[Mapping] = None,
                  ledger_lookup: Optional[Callable[[Mapping], Optional[bool]]] = None,
                  participates: Optional[bool] = None,
                  bundle_cache: Any = None) -> "OrderedDict[str, Any]":
    """Run rules A-O over ``package`` and return the receipt.

    ``bundle_cache`` (ATLAS-THROUGHPUT-004, a ``bundle_cache.BundleCache``)
    lets rule J be satisfied by a TRUSTED persistent bundle whose input key
    matches this package -- MARKET_BUILD_REQUIRED = NO -- and rule K by the
    determinism proof that bundle's receipt carries. Without it (the
    default) J and K are the two cold builds 003 specified. A cache hit is
    artifact identity, never release safety: rules A-I and L-O still run.

    ``live`` may be supplied (a test fixture, or one index shared by several
    packages); otherwise it is read from the committed records. ``build`` and
    ``determinism`` exist so a caller can DECLARE a rule not run -- the rule
    is then UNKNOWN and the package NOT ELIGIBLE; there is no way to pass J
    or K without executing them.
    """
    moment = now or _now()
    started_at = _iso(moment)
    lane_started = time.perf_counter()
    work = Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    results: "OrderedDict[str, RuleResult]" = OrderedDict()
    legacy_exceptions: List["OrderedDict[str, Any]"] = []
    market_id = str(package.get("market_id") or "")
    activation_doc = activation if activation is not None else load_activation()

    # ---- A: schema and seal ---------------------------------------------- #
    t = time.perf_counter()
    a_issues = SMP.validate(package)
    results["A"] = _result("A", PASS if not a_issues else FAIL, t,
                           detail=(("schema", package.get("schema")),
                                   ("package_id", package.get("package_id")),
                                   ("package_digest", package.get("package_digest"))),
                           problems=[str(i) for i in a_issues])
    if a_issues:
        # Nothing below can be trusted about a document that is not a package.
        for rule in RULES:
            if rule not in results:
                results[rule] = _result(rule, UNKNOWN, t, problems=["rule A failed; not evaluated"])
        return _receipt(package, results, legacy_exceptions, moment, started_at, lane_started,
                        activation_doc, extra=OrderedDict())

    # ---- B, D, E, F, L (writer part): the typed writer over the package ---- #
    t = time.perf_counter()
    issues, resealed_digest = revalidate(package)
    by_rule: Dict[str, List[str]] = {"B": [], "D": [], "E": [], "F": [], "L": []}
    for issue in issues:
        by_rule[_owner_rule(issue.code)].append(str(issue))
    writer_seconds = round(time.perf_counter() - t, 3)
    identity_records = package["identity_records"]
    declared_defects = [r["identity_key"] for r in identity_records
                        if r.get("identity_key") != RI.canonical_identity(str(r.get("canonical_name") or ""))]
    if declared_defects:
        by_rule["B"].append("identity key(s) not canonical for their name: %s" % declared_defects[:5])
    results["B"] = _result("B", PASS if not by_rule["B"] else FAIL, t,
                           detail=(("identity_records", len(identity_records)),
                                   ("census_count", package["census"].get("count")),
                                   ("declared_relations", sum(1 for r in identity_records if r.get("relation"))),
                                   ("writer_seconds", writer_seconds)),
                           problems=by_rule["B"])

    # ---- C: first-party binding ------------------------------------------- #
    t = time.perf_counter()
    binding = FPB.evaluate_package(package)
    results["C"] = _result("C", PASS if binding["passed"] else FAIL, t,
                           detail=(("records_evaluated", binding["records_evaluated"]),
                                   ("eligible", binding["eligible"]), ("ineligible", binding["ineligible"]),
                                   ("classes", binding["classes"])),
                           problems=["%s (%s): %s -- %s" % (f["identity_key"], f["kind"], f["classification"], f["why"])
                                     for f in binding["failures"]])

    t = time.perf_counter()
    results["D"] = _result("D", PASS if not by_rule["D"] else FAIL, t,
                           detail=(("pet_friendly_records", len(package["pet_friendly_records"])),
                                   ("verified_no_pets_records", len(package["verified_no_pets_records"])),
                                   ("policy_schema", package["contract_versions"].get("policy_schema"))),
                           problems=by_rule["D"])
    results["E"] = _result("E", PASS if not by_rule["E"] else FAIL, t,
                           detail=(("official_routes", len(package["official_routes"])),
                                   ("public_routes", package["coverage_scorecard"].get("public_routes"))),
                           problems=by_rule["E"])
    results["F"] = _result("F", PASS if not by_rule["F"] else FAIL, t,
                           detail=(("partition_count", package["partition"].get("count")),
                                   ("unresolved_rows", len(package["unresolved_rows"])),
                                   ("counts_by_partition_state",
                                    package["coverage_scorecard"].get("counts_by_partition_state"))),
                           problems=by_rule["F"])

    # ---- G, H, I, N: the live release ------------------------------------- #
    t = time.perf_counter()
    if live is None:
        try:
            live = RI.live_index()
        except Exception as exc:
            live = (RI.ReleaseIndex(), None, ["live index unavailable: %s" % str(exc)[:200]])
    live_idx, live_state, live_problems = live
    compare_report: Optional[Mapping] = None
    package_index: Optional[RI.MarketIndex] = None
    if live_state is None or live_problems:
        for rule in ("G", "H", "I", "N"):
            results[rule] = _result(rule, UNKNOWN, t,
                                    detail=(("live_problems", list(live_problems)),),
                                    problems=["CURRENT_VERIFIED_LIVE could not be established"] + list(live_problems))
    else:
        delta = package["intended_delta"]
        joins = participates
        if joins is None:
            intent = {str(p.get("market_id")): p.get("to") for p in (delta.get("expected_participation_delta") or ())
                      if isinstance(p, Mapping)}
            joins = bool(intent.get(market_id, market_id in live_state.participating_markets))
        try:
            package_index = RI.index_from_package(package, participating=joins)
            proposed = RI.compose(live_idx, package_index, participates=joins)
            compare_report = RI.compare(live_idx, proposed, package_market=market_id, intended_delta=delta)
        except Exception as exc:
            for rule in ("G", "H", "I"):
                results[rule] = _result(rule, FAIL, t, problems=["release index failed: %s" % str(exc)[:200]])
        if compare_report is not None:
            findings = compare_report["findings"]
            g_codes = {RI.CROSS_MARKET_IDENTITY_COLLISION, RI.DUPLICATE_ROUTE, RI.OWNERSHIP_MOVEMENT}
            h_codes = {RI.MISSING_LIVE_MARKET, RI.MISSING_UNRELATED_PROFILE, RI.MISSING_UNRELATED_ROUTE,
                       RI.UNRELATED_MARKET_CHANGED}
            g = [f for f in findings if f["code"] in g_codes
                 and (f["market_id"] == market_id or f.get("other_market") == market_id
                      or f.get("from_market") == market_id)]
            g_legacy = [f for f in findings if f["code"] in g_codes and f not in g]
            for f in g_legacy:
                legacy_exceptions.append(OrderedDict((("rule", "G"), ("touches", "identity"),
                                                      ("code", f["code"]), ("market_id", f["market_id"]),
                                                      ("detail", f["detail"]))))
            h = [f for f in findings if f["code"] in h_codes
                 or (f["code"] == RI.UNEXPECTED_MEMBERSHIP_CHANGE and f["market_id"] != market_id)]
            i = [f for f in findings if f["code"] not in g_codes and f not in h]
            removal_authority = delta.get("removal_authority") if isinstance(delta.get("removal_authority"), Mapping) else {}
            if (delta.get("remove_property_ids") or delta.get("remove_routes")) \
                    and not (removal_authority.get("ruling_ref") and removal_authority.get("reason")):
                i.append(RI._finding(RI.UNEXPECTED_PROPERTY_DELETION, market_id,
                                     "declared removals carry no removal_authority ruling"))
            results["G"] = _result("G", PASS if not g else FAIL, t,
                                   detail=(("live_digest", compare_report["live_digest"]),
                                           ("proposed_digest", compare_report["proposed_digest"]),
                                           ("proposed_participating", compare_report["proposed_participating"]),
                                           ("proposed_total_profiles", compare_report["proposed_total_profiles"]),
                                           ("legacy_collisions_outside_package", len(g_legacy)),
                                           ("compare_seconds", compare_report["seconds"])),
                                   problems=[f["detail"] for f in g])
            results["H"] = _result("H", PASS if not h else FAIL, t,
                                   detail=(("live_participating", compare_report["live_participating"]),
                                           ("live_total_profiles", compare_report["live_total_profiles"]),
                                           ("finding_counts", compare_report["finding_counts"])),
                                   problems=["%s: %s" % (f["market_id"], f["detail"]) for f in h])
            results["I"] = _result("I", PASS if not i else FAIL, t,
                                   detail=(("intended_delta", OrderedDict(
                                       (k, delta.get(k)) for k in SMP.INTENDED_DELTA_FIELDS)),
                                           ("actual_delta", compare_report["actual_delta"]),
                                           ("removal_authority", removal_authority)),
                                   problems=[f["detail"] for f in i])
        # N: the package's parent live state IS the current live state.
        t = time.perf_counter()
        parent = package["parent_live_state"]
        expected = live_state.to_dict()
        n_problems: List[str] = []
        for field in ("live_deploy_id", "rollback_target", "source_commit", "total_profiles", "sitemap_route_count"):
            if parent.get(field) != expected.get(field):
                n_problems.append("%s: package parent %r, live %r" % (field, parent.get(field), expected.get(field)))
        if list(parent.get("participating_markets") or ()) != list(expected["participating_markets"]):
            n_problems.append("participating_markets differ from live")
        if OrderedDict(parent.get("profile_counts") or {}) != expected["profile_counts"]:
            n_problems.append("profile_counts differ from live")
        if parent.get("live_index_digest") != live_idx.digest():
            n_problems.append("live_index_digest: package parent %s, live %s"
                              % (str(parent.get("live_index_digest"))[:23], live_idx.digest()[:23]))
        if not live_state.rollback_record or not live_state.rollback_markets:
            n_problems.append("the rollback target has no verified record with a market set")
        results["N"] = _result("N", PASS if not n_problems else FAIL, t,
                               detail=(("live", expected), ("stale_parent", bool(n_problems))),
                               problems=n_problems)

    # ---- J, K: build the changed market, twice, cold ---------------------- #
    t = time.perf_counter()
    build_a: Optional[Mapping] = None
    cached: Optional[Mapping] = None
    if build and bundle_cache is not None:
        try:
            cached = bundle_cache.build_or_reuse(package, work_dir=work / "bc", cold_required=False,
                                                 require_determinism=determinism, revocations=revocations, now=now)
        except Exception as exc:
            cached = None
            results["J"] = _result("J", FAIL, t, problems=["persistent cache request failed: %s" % str(exc)[:300]])
    if cached is not None:
        reused = cached["cache_status"] in ("HIT", "HIT_AFTER_WAIT", "REVALIDATE")
        j_problems = [] if reused or cached.get("trust_state") == "TRUSTED" else \
            ["cached build not trusted: %s" % cached.get("untrusted_because")]
        results["J"] = _result("J", PASS if not j_problems else FAIL, t,
                               detail=(("MARKET_BUILD_REQUIRED", "NO" if reused else "YES"),
                                       ("cache_status", cached["cache_status"]),
                                       ("build_input_key", cached["build_input_key"]),
                                       ("bundle_sha256", cached["bundle_sha256"]),
                                       ("file_count", cached.get("file_count")),
                                       ("receipt_digest", cached.get("receipt_digest")),
                                       ("builder_invocations", cached.get("builder_invocations")),
                                       ("build_seconds", cached.get("build_seconds")),
                                       ("lookup_seconds", cached.get("lookup_seconds"))),
                               problems=j_problems)
        t = time.perf_counter()
        determinism_result = (cached.get("determinism") or {}).get("result")
        if reused:
            receipt_doc = bundle_cache.read_receipt(str(cached.get("receipt_digest") or "")) or {}
            determinism_result = ((receipt_doc.get("results") or {}).get("determinism") or {}).get("result")
        k_ok = determinism and determinism_result == "BYTE_IDENTICAL"
        results["K"] = _result("K", PASS if k_ok else (UNKNOWN if not determinism else FAIL), t,
                               detail=(("result", determinism_result or UNKNOWN),
                                       ("inherited_from_bundle_receipt", bool(reused)),
                                       ("output_digest_a", cached["bundle_sha256"]),
                                       ("output_digest_b", cached["bundle_sha256"] if determinism_result == "BYTE_IDENTICAL" else None),
                                       ("cold_builds_executed", cached.get("builder_invocations")),
                                       ("reuse_hits", 1 if reused else 0)),
                               problems=[] if k_ok else ["determinism %s" % (determinism_result or "not proven")])
    elif not build:
        results["J"] = _result("J", UNKNOWN, t, problems=["changed-market build not executed (build=False)"])
    elif "J" in results:
        pass
    else:
        try:
            # Short directory names on purpose: a Windows path is limited to 260
            # characters and a generated profile route is ~90 of them.
            build_a = STAGING.build_changed_market(package, work / "sa", work / "oa", cold=True)
            executed = [e for e in build_a["cache_events"] if e["assembly_kind"] == "market_bundle"]
            problems = list(build_a["gates_failing"])
            if not executed or any(e["verdict"] != "BUILD_EXECUTED" for e in executed):
                problems.append("the market bundle was not built cold: %s" % executed)
            results["J"] = _result("J", PASS if not problems else FAIL, t,
                                   detail=(("bundle_sha256", build_a["bundle_sha256"]),
                                           ("file_count", build_a["file_count"]),
                                           ("html_count", build_a["html_count"]),
                                           ("staged_input_digest", build_a["staged_input_digest"]),
                                           ("contract_sha256", build_a["contract_sha256"]),
                                           ("release_name", build_a["release_name"]),
                                           ("cache_events", build_a["cache_events"]),
                                           ("build_seconds", build_a["seconds"])),
                                   problems=problems)
        except Exception as exc:
            results["J"] = _result("J", FAIL, t, problems=["build failed: %s" % str(exc)[:400]])
    t = time.perf_counter()
    if "K" in results:
        pass
    elif not determinism or build_a is None:
        results["K"] = _result("K", UNKNOWN, t,
                               problems=["determinism not executed" if determinism else
                                         "determinism proof not executed (determinism=False)"])
    else:
        try:
            build_b = STAGING.build_changed_market(package, work / "sb", work / "ob", cold=True)
            executed = [e for e in build_b["cache_events"] if e["assembly_kind"] == "market_bundle"]
            problems: List[str] = []
            if not executed or any(e["verdict"] != "BUILD_EXECUTED" for e in executed):
                problems.append("second build was not cold: %s" % executed)
            if build_b["staged_input_digest"] != build_a["staged_input_digest"]:
                problems.append("staged inputs differed between builds")
            if build_b["bundle_sha256"] != build_a["bundle_sha256"]:
                problems.append("bundle digests differ: %s vs %s"
                                % (build_a["bundle_sha256"][:16], build_b["bundle_sha256"][:16]))
            results["K"] = _result("K", PASS if not problems else FAIL, t,
                                   detail=(("input_digest", build_a["staged_input_digest"]),
                                           ("output_digest_a", build_a["bundle_sha256"]),
                                           ("output_digest_b", build_b["bundle_sha256"]),
                                           ("result", "BYTE_IDENTICAL" if not problems else "DIFFERENT"),
                                           ("cold_builds_executed", len([e for e in build_a["cache_events"] + build_b["cache_events"]
                                                                         if e["verdict"] == "BUILD_EXECUTED"])),
                                           ("reuse_hits", len([e for e in build_a["cache_events"] + build_b["cache_events"]
                                                               if e["verdict"] == "REUSE_HIT"])),
                                           ("build_seconds", build_b["seconds"])),
                                   problems=problems)
        except Exception as exc:
            results["K"] = _result("K", FAIL, t, problems=["second build failed: %s" % str(exc)[:400]])

    # ---- L: hashes ------------------------------------------------------- #
    t = time.perf_counter()
    l_problems = list(by_rule["L"])
    if resealed_digest is not None and resealed_digest != package["package_digest"]:
        l_problems.append("the package does not re-derive from its own sections: %s vs %s"
                          % (resealed_digest[:23], str(package["package_digest"])[:23]))
    refs = {(str(r["identity_key"]), str(r["artifact_sha256"])): r for r in package["evidence_references"]}
    for record in package["pet_friendly_records"]:
        for entry in record.get("evidence") or ():
            if not isinstance(entry, Mapping) or entry.get("artifact_class") != "PUBLICATION_GRADE_EVIDENCE":
                continue
            digest = SMP.normalise_sha256(str(entry.get("artifact_sha256") or ""))
            if (str(record.get("identity_key")), digest) not in refs:
                l_problems.append("evidence %s of %r is not in the reference index"
                                  % (entry.get("evidence_ref"), record.get("identity_key")))
    artifacts_checked = 0
    for ref in package["evidence_references"]:
        if ref.get("artifact_available") and ref.get("artifact_path"):
            path = Path(str(ref["artifact_path"]))
            if not path.is_absolute():
                path = REPO_ROOT / path
            if not path.is_file():
                l_problems.append("artifact %s declared available but missing at %s" % (ref["evidence_ref"], path))
                continue
            data = path.read_bytes()
            if SMP.sha256_bytes(data) != ref["artifact_sha256"]:
                l_problems.append("artifact %s bytes hash to %s, reference says %s"
                                  % (ref["evidence_ref"], SMP.sha256_bytes(data)[:23], ref["artifact_sha256"][:23]))
                continue
            artifacts_checked += 1
            text = data.decode("utf-8", errors="replace")
            for record in package["pet_friendly_records"]:
                if str(record.get("identity_key")) != str(ref["identity_key"]):
                    continue
                for entry in record.get("evidence") or ():
                    if isinstance(entry, Mapping) and SMP.normalise_sha256(str(entry.get("artifact_sha256") or "")) \
                            == ref["artifact_sha256"] and not EVIDENCE.quote_is_contiguous(str(entry.get("quote") or ""), text):
                        l_problems.append("quote of %s is not contiguous in artifact %s"
                                          % (entry.get("evidence_ref"), ref["evidence_ref"]))
    results["L"] = _result("L", PASS if not l_problems else FAIL, t,
                           detail=(("package_digest", package["package_digest"]),
                                   ("rederived_digest", resealed_digest),
                                   ("evidence_references", len(package["evidence_references"])),
                                   ("artifacts_available", sum(1 for r in package["evidence_references"] if r.get("artifact_available"))),
                                   ("artifacts_checked", artifacts_checked),
                                   ("dependency_inputs", len(package["dependency_input_digests"])),
                                   ("dependency_digest", dependency_digest(package))),
                           problems=l_problems)

    # ---- M: freshness and revocation -------------------------------------- #
    t = time.perf_counter()
    revoked = revocations if revocations is not None else load_revocations()
    m_problems: List[str] = []
    earliest_expiry: Optional[datetime] = None
    for ref in package["evidence_references"]:
        captured = FPB.parse_timestamp(str(ref.get("captured_at") or ""))
        if captured is None:
            m_problems.append("%s has no parseable captured_at (%r)" % (ref["evidence_ref"], ref.get("captured_at")))
            continue
        if captured.tzinfo is None:
            captured = captured.replace(tzinfo=timezone.utc)
        expiry = captured + timedelta(days=EVIDENCE_MAX_AGE_DAYS)
        if expiry < moment:
            m_problems.append("%s captured %s is older than %d days" % (ref["evidence_ref"], ref["captured_at"], EVIDENCE_MAX_AGE_DAYS))
        if captured > moment + timedelta(days=1):
            m_problems.append("%s captured_at %s is in the future" % (ref["evidence_ref"], ref["captured_at"]))
        earliest_expiry = expiry if earliest_expiry is None or expiry < earliest_expiry else earliest_expiry
        if str(ref["artifact_sha256"]) in revoked:
            m_problems.append("%s artifact %s is REVOKED: %s" % (ref["evidence_ref"], str(ref["artifact_sha256"])[:23],
                                                                 revoked[str(ref["artifact_sha256"])].get("reason")))
    results["M"] = _result("M", PASS if not m_problems else FAIL, t,
                           detail=(("max_age_days", EVIDENCE_MAX_AGE_DAYS),
                                   ("references", len(package["evidence_references"])),
                                   ("revoked_registry_size", len(revoked)),
                                   ("earliest_expiry", _iso(earliest_expiry) if earliest_expiry else None)),
                           problems=m_problems)

    # ---- O: paid provenance ------------------------------------------------ #
    t = time.perf_counter()
    o_problems: List[str] = []
    paid = [r for r in package["evidence_references"] if WRITER.is_paid_lane(str(r.get("capture_lane") or ""))]
    ledger_checked = 0
    ledger_unknown = 0
    for ref in paid:
        reservation = ref.get("paid_reservation")
        if not isinstance(reservation, Mapping):
            o_problems.append("%s was captured through paid lane %r without a reservation"
                              % (ref["evidence_ref"], ref.get("capture_lane")))
            continue
        expected = paid_attempt_id(market_id, str(reservation.get("run_id") or ""),
                                   str(ref.get("identity_key") or ""), str(reservation.get("lane") or ""))
        if reservation.get("attempt_id") != expected:
            o_problems.append("%s reservation attempt_id %r does not re-derive (%s)"
                              % (ref["evidence_ref"], reservation.get("attempt_id"), expected))
        if not SMP.is_sha256(SMP.normalise_sha256(str(reservation.get("request_envelope_sha256") or ""))):
            o_problems.append("%s reservation has no request envelope hash" % ref["evidence_ref"])
        if ledger_lookup is not None:
            verdict = ledger_lookup(reservation)
            if verdict is False:
                o_problems.append("%s reservation %s is not in the paid ledger" % (ref["evidence_ref"], reservation.get("attempt_id")))
            elif verdict is None:
                ledger_unknown += 1
            else:
                ledger_checked += 1
    status = PASS if not o_problems and not ledger_unknown else (FAIL if o_problems else UNKNOWN)
    results["O"] = _result("O", status, t,
                           detail=(("paid_references", len(paid)),
                                   ("ledger_cross_checked", ledger_checked),
                                   ("ledger_unknown", ledger_unknown)),
                           problems=o_problems + (["%d reservation(s) could not be found in a ledger" % ledger_unknown]
                                                  if ledger_unknown else []))

    ordered = OrderedDict((rule, results[rule]) for rule in RULES)
    extra: "OrderedDict[str, Any]" = OrderedDict((
        ("global_index_digest", OrderedDict((("live", compare_report["live_digest"] if compare_report else None),
                                             ("proposed", compare_report["proposed_digest"] if compare_report else None)))),
        ("package_index_digest", package_index.digest() if package_index is not None else None),
    ))
    return _receipt(package, ordered, legacy_exceptions, moment, started_at, lane_started, activation_doc, extra=extra)


def dependency_digest(package: Mapping) -> str:
    return SMP.sha256_text(SMP.canonical_json(package.get("dependency_input_digests") or {}))


def _receipt(package: Mapping, results: "OrderedDict[str, RuleResult]",
             legacy_exceptions: List[Mapping], moment: datetime, started_at: str,
             lane_started: float, activation: Mapping, *, extra: Mapping) -> "OrderedDict[str, Any]":
    from scripts.pettripfinder.throughput_profile import peak_working_set_mb

    unknown = [r for r, res in results.items() if res["status"] == UNKNOWN]
    failed = [r for r, res in results.items() if res["status"] == FAIL]
    eligible = not unknown and not failed
    activation_state = str(activation.get("FAST_PATH_PRODUCTION_ACTIVATION") or "DISABLED")
    market_id = str(package.get("market_id") or "")
    parent = package.get("parent_live_state") or {}
    delta = package.get("intended_delta") or {}
    seconds = round(time.perf_counter() - lane_started, 3)
    receipt: "OrderedDict[str, Any]" = OrderedDict((
        ("schema", RECEIPT_SCHEMA),
        ("lane", LANE),
        ("PACKAGE_ID", package.get("package_id")),
        ("PACKAGE_DIGEST", package.get("package_digest")),
        ("MARKET_ID", market_id),
        ("PARENT_RELEASE", OrderedDict((("live_deploy_id", parent.get("live_deploy_id")),
                                        ("rollback_target", parent.get("rollback_target")),
                                        ("source_commit", parent.get("source_commit")),
                                        ("live_index_digest", parent.get("live_index_digest"))))),
        ("CHANGE_CLASS", "MARKET_AUTHORITY_DATA_ONLY"),
        ("DEPENDENCY_DIGEST", dependency_digest(package)),
        ("VALIDATION_POLICY_VERSION", LANE_VERSION),
        ("RULES_EXECUTED", [OrderedDict((("rule", r), ("name", RULES[r]))) for r in results]),
        ("RESULTS", results),
        ("TIMESTAMPS", OrderedDict((("started_at", started_at), ("finished_at", _iso(_now())),
                                    ("seconds", seconds)))),
        ("ARTIFACT_DIGESTS", OrderedDict((
            ("changed_market_bundle_sha256_a", results["K"]["detail"].get("output_digest_a")
             if results.get("K") else None),
            ("changed_market_bundle_sha256_b", results["K"]["detail"].get("output_digest_b")
             if results.get("K") else None),
            ("staged_input_digest", results["J"]["detail"].get("staged_input_digest") if results.get("J") else None),
            ("staged_contract_sha256", results["J"]["detail"].get("contract_sha256") if results.get("J") else None),
        ))),
        ("GLOBAL_INDEX_DIGEST", extra.get("global_index_digest")),
        ("PACKAGE_INDEX_DIGEST", extra.get("package_index_digest")),
        ("INTENDED_DELTA_DIGEST", SMP.sha256_text(SMP.canonical_json(delta))),
        ("DETERMINISM_RESULT", results["K"]["detail"].get("result", results["K"]["status"]) if results.get("K") else UNKNOWN),
        ("FIRST_PARTY_BINDING_RESULT", results["C"]["status"] if results.get("C") else UNKNOWN),
        ("COLLISION_RESULT", results["G"]["status"] if results.get("G") else UNKNOWN),
        ("REMOVAL_RESULT", results["I"]["status"] if results.get("I") else UNKNOWN),
        ("LEGACY_EXCEPTIONS", legacy_exceptions),
        ("ENVIRONMENT", OrderedDict((("python", sys.version.split()[0]), ("platform", platform.platform()),
                                     ("builder_version", package.get("builder_version")),
                                     ("contract_versions", package.get("contract_versions")),
                                     ("created_from_source_sha", package.get("created_from_source_sha")),
                                     ("peak_working_set_mb", peak_working_set_mb())))),
        ("EXPIRY_REVOCATION_CONDITIONS", OrderedDict((
            ("valid_while", ["the live deployment is %s" % parent.get("live_deploy_id"),
                             "the live index digest is %s" % parent.get("live_index_digest"),
                             "no referenced artifact is added to evidence_revocations.json",
                             "the evidence is younger than %d days" % EVIDENCE_MAX_AGE_DAYS,
                             "the owning contracts are at the versions recorded in ENVIRONMENT",
                             "the sealed package bytes are unchanged (digest above)"]),
            ("earliest_evidence_expiry", results["M"]["detail"].get("earliest_expiry") if results.get("M") else None),
            ("evidence_max_age_days", EVIDENCE_MAX_AGE_DAYS),
        ))),
        ("UNKNOWN_RULES", unknown),
        ("FAILED_RULES", failed),
        ("FAST_DATA_ONLY_RELEASE_ELIGIBLE", YES if eligible else NO),
        ("FULL_REGRESSION_REQUIRED_BY_LANE", NO if eligible else YES),
        ("FAST_PATH_PRODUCTION_ACTIVATION", activation_state),
        ("PRODUCTION_ACTIVATION_ALLOWED", YES if production_activation_allowed(market_id, activation) else NO),
        ("PERFORMANCE", OrderedDict((("total_seconds", seconds),
                                     ("per_rule_seconds", OrderedDict((r, res["seconds"]) for r, res in results.items())),
                                     ("changed_market_build_seconds", results["J"]["detail"].get("build_seconds")
                                      if results.get("J") else None),
                                     ("determinism_build_seconds", results["K"]["detail"].get("build_seconds")
                                      if results.get("K") else None)))),
    ))
    receipt["RECEIPT_DIGEST"] = SMP.sha256_text(SMP.canonical_json(
        OrderedDict((k, v) for k, v in receipt.items() if k not in ("TIMESTAMPS", "ENVIRONMENT", "PERFORMANCE"))))
    return receipt


# --------------------------------------------------------------------------- #
# Receipt storage.
# --------------------------------------------------------------------------- #

def receipt_dir(market_id: str, receipts_dir: Optional[Path] = None) -> Path:
    return (Path(receipts_dir) if receipts_dir else SMP.RECEIPTS_DIR) / market_id


def write_receipt(receipt: Mapping, receipts_dir: Optional[Path] = None) -> Path:
    directory = receipt_dir(str(receipt["MARKET_ID"]), receipts_dir)
    directory.mkdir(parents=True, exist_ok=True)
    name = "%s-%s.json" % (receipt["PACKAGE_ID"], str(receipt["RECEIPT_DIGEST"]).split(":", 1)[1][:16])
    path = directory / name
    path.write_text(json.dumps(receipt, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def eligible_receipts(market_id: str, package_digest: str,
                      receipts_dir: Optional[Path] = None) -> List[Path]:
    """Committed receipts that say ELIGIBLE = YES for exactly this package."""
    out: List[Path] = []
    directory = receipt_dir(market_id, receipts_dir)
    if not directory.is_dir():
        return out
    for path in sorted(directory.glob("pkg-*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8-sig"))
        except ValueError:
            continue
        if doc.get("schema") == RECEIPT_SCHEMA and doc.get("PACKAGE_DIGEST") == package_digest \
                and doc.get("FAST_DATA_ONLY_RELEASE_ELIGIBLE") == YES and not doc.get("UNKNOWN_RULES"):
            out.append(path)
    return out


__all__ = [
    "LANE", "LANE_VERSION", "RECEIPT_SCHEMA", "RULES", "PASS", "FAIL", "UNKNOWN", "YES", "NO",
    "EVIDENCE_MAX_AGE_DAYS", "ACTIVATION_PATH", "REVOCATIONS_PATH", "RuleResult",
    "load_activation", "production_activation_allowed", "load_revocations",
    "inputs_from_package", "revalidate", "run_fast_lane", "dependency_digest",
    "receipt_dir", "write_receipt", "eligible_receipts",
]
