"""PTF-MILWAUKEE-FINAL-PREPUBLICATION-NORMALIZATION-041 -- pay the debt, then measure.

Milwaukee carried two written-down debts into this work order and neither is
allowed to survive it.

THE DEFERRED PROJECTION
------------------------
038 found that re-projecting the store onto a repaired reader withdrew sixteen
founder decisions -- fifteen of them over ``reader_commit``, a provenance stamp
the projection re-derives every run. It refused to project and wrote the reason
down instead of letting the store drift silently.

Both halves of that blocker are now gone, for two independent reasons:

  * 039 replaced the binding with ``semantic-approval/1.0``, so a
    provenance-only difference no longer withdraws anything; and
  * 040's founder read the ONE row whose meaning actually changed -- Saint
    Kate -- and approved the corrected reading.

So the projection no longer moves a single approved meaning that a person has
not already agreed to. That is checked here rather than asserted: every row is
classified, and a substantive change nobody approved would stop this work
order rather than be normalized away.

THE STALE PUBLICATION PACKAGE
------------------------------
037 prepared a release contract against a seventy-record authority. There are
seventy-three records now. The old contract is not edited -- a historical
artifact that quietly grows a new number is worse than a stale one -- it is
SUPERSEDED by sha256 in a registry the contract loader consults, so the
document cannot be used by placing it in the live directory.

WHAT THIS IS NOT
----------------
Not publication and not deployment. The simulation below runs the real
builders against the inventory publication WOULD produce, in process, writing
nothing: the seed shard stays empty, the package stays ``published: false``,
and no route reaches a site.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, Iterator, List, Mapping, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder import approval_binding as AB                     # noqa: E402
from scripts.pettripfinder import market_authority as MA                     # noqa: E402
from scripts.pettripfinder.acquisition import approval_rebinding_039 as R39  # noqa: E402
from scripts.pettripfinder.acquisition import authority_build_036 as A36     # noqa: E402
from scripts.pettripfinder.acquisition import authority_build_040 as A40     # noqa: E402
from scripts.pettripfinder.acquisition import closure_038 as C38             # noqa: E402
from scripts.pettripfinder.acquisition import founder_decisions_040 as D40   # noqa: E402
from scripts.pettripfinder.acquisition import founder_review_036 as F36      # noqa: E402
from scripts.pettripfinder.acquisition import publication_037 as P37         # noqa: E402
from scripts.pettripfinder.acquisition import store_integration_025 as S25   # noqa: E402

WORK_ORDER = "PTF-MILWAUKEE-FINAL-PREPUBLICATION-NORMALIZATION-041"
MARKET = "milwaukee-wi"

PKG = F36.PKG / "milwaukee_normalization_041"
PROJECTION_REPORT = PKG / "milwaukee-store-projection-041.json"
FRESH_CONTRACT = PKG / ("release_contract.%s.prepared-041.json" % MARKET)
SIMULATION = PKG / "milwaukee-publication-simulation-041.json"
REPORT_MD = PKG / "milwaukee-normalization-041-report.md"

#: Contracts that must never gate a build again, by content hash. The loader
#: consults this, so a superseded document cannot be resurrected by copying it
#: into the live directory.
SUPERSEDED_REGISTRY = F36.PKG / "release_contracts_superseded.json"

NEWLINE = chr(10)

SEMANTICS_IDENTICAL = "A_SEMANTICS_IDENTICAL"
SEMANTICS_CHANGED = "B_SEMANTICS_CHANGED_REQUIRES_FOUNDER_REVIEW"
PROVENANCE_ONLY = "C_PROVENANCE_ONLY_CHANGE"
OTHER_BLOCKER = "D_OTHER_BLOCKER"

#: A fifth label, because the four above cannot describe Saint Kate honestly.
#: Its meaning DID move, so it is not (A); it does NOT need review, because a
#: founder read this exact reading and approved it in 040, so it is not (B).
#: Filing it under either would be a false statement in the artifact that
#: exists to be read later, and the distinction is the whole reason the
#: projection is safe now and was not in 038.
SEMANTICS_CHANGED_ALREADY_APPROVED = "E_SEMANTICS_CHANGED_ALREADY_APPROVED"


class NormalizationError(RuntimeError):
    """Raised rather than normalizing something nobody approved."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------- #
# Phase 2 -- classify every projection difference.
# --------------------------------------------------------------------------- #

def founder_approved_semantics() -> Dict[str, Dict]:
    """What a founder has actually agreed a row SAYS, by identity.

    Read from 040's candidate package rather than from the store, because the
    whole question is whether the store agrees with it.
    """
    out: Dict[str, Dict] = {}
    if not D40.LEDGER.is_file():
        return out
    for decision in D40.load_ledger()["decisions"]:
        if decision["decision"] == D40.HOLD:
            continue
        candidate = A40.candidate_for(decision["identity_key"])
        out[decision["identity_key"]] = {
            "facts": candidate["proposed_publication_facts"],
            "withheld_fields": candidate["withheld_fields"],
            "decision": decision["decision"],
            "work_order": D40.WORK_ORDER,
            "decided_at": decision["decided_at"],
        }
    return out


def classify_projection() -> List[Dict]:
    """Every store row, committed against projected, one classification each."""
    committed = R39.store_rows()
    projected = R39.projected_rows()
    approved = founder_approved_semantics()
    pending = set(C38.PENDING_PROJECTION)
    out: List[Dict] = []
    for key in sorted(committed):
        before = committed[key]
        after = projected.get(key)
        row = OrderedDict([
            ("identity_key", key),
            ("canonical_name", before.get("canonical_name", "")),
            ("named_in_038_register", key in pending),
        ])
        if after is None:
            row.update({
                "classification": OTHER_BLOCKER,
                "why": "the projection produces no row for this identity",
                "safe_to_apply": False,
            })
            out.append(row)
            continue

        difference = AB.semantic_difference(before, after)
        identical = (json.dumps(before, sort_keys=True, default=str)
                     == json.dumps(after, sort_keys=True, default=str))
        if not difference and identical:
            row.update({"classification": SEMANTICS_IDENTICAL,
                        "why": "nothing moved at all",
                        "safe_to_apply": True})
            out.append(row)
            continue
        if not difference:
            row.update({
                "classification": PROVENANCE_ONLY,
                "why": "only implementation provenance moved (%s); "
                       "semantic-approval/1.0 does not withdraw an approval "
                       "for that" % ", ".join(
                           R39._provenance_that_moved(before, after)),
                "safe_to_apply": True,
            })
            out.append(row)
            continue

        # The meaning moved. The only safe reason to apply it is that a
        # founder has already read this exact reading and approved it.
        agreed = approved.get(key)
        matches = bool(agreed) and (
            json.dumps(agreed["facts"], sort_keys=True, default=str)
            == json.dumps(after["proposed_facts"], sort_keys=True, default=str)
            and json.dumps(agreed["withheld_fields"], sort_keys=True,
                           default=str)
            == json.dumps(after["withheld_fields"], sort_keys=True,
                          default=str))
        row.update({
            "classification": SEMANTICS_CHANGED_ALREADY_APPROVED if matches
                              else SEMANTICS_CHANGED,
            "semantic_difference": {field: {"before": value["before"],
                                            "after": value["after"]}
                                    for field, value in difference.items()},
            "founder_approved_this_reading": matches,
            "why": ("the meaning moved, and it moved TO the reading %s "
                    "approved on %s -- projecting it brings the store into "
                    "agreement with the authority rather than away from it"
                    % (agreed["work_order"], agreed["decided_at"])) if matches
                   else ("the meaning moved and no founder has approved the "
                         "new reading; this is a governance event, not a "
                         "normalization"),
            "safe_to_apply": matches,
        })
        out.append(row)
    return out


def projection_summary() -> Dict:
    rows = classify_projection()
    blocked = [row for row in rows if not row["safe_to_apply"]]
    return {
        "store_rows": len(rows),
        "by_classification": dict(Counter(row["classification"]
                                          for row in rows)),
        "named_in_038_register": sorted(C38.PENDING_PROJECTION),
        "safe_to_apply": sum(1 for row in rows if row["safe_to_apply"]),
        "blocked": [row["identity_key"] for row in blocked],
        "requires_founder_review": [row["identity_key"] for row in rows
                                    if row["classification"]
                                    == SEMANTICS_CHANGED],
    }


def assert_safe_to_normalize() -> Dict:
    summary = projection_summary()
    if summary["requires_founder_review"]:
        raise NormalizationError(
            "STOP: %s changed meaning and no founder approved the new "
            "reading. A re-review package is required before this market is "
            "normalized." % ", ".join(summary["requires_founder_review"]))
    if summary["blocked"]:
        raise NormalizationError("STOP: blocked rows: %s"
                                 % ", ".join(summary["blocked"]))
    return summary


# --------------------------------------------------------------------------- #
# Phase 3 and 5 -- apply, then retire the register.
# --------------------------------------------------------------------------- #

def normalize_store(apply: bool = False) -> Dict:
    summary = assert_safe_to_normalize()
    result = S25.integrate(write=apply)
    return {
        "applied": apply,
        "rows_before": result["rows_before"],
        "rows_after": result["rows_after"],
        "added": result["added"],
        "removed": result["removed"],
        "changed_facts": result["changed_facts"],
        "classification": summary["by_classification"],
    }


def retired_register_document() -> Dict:
    """038's register, marked resolved. History preserved, debt closed.

    The register is not deleted and its original population is not rewritten:
    a debt that vanishes leaves nobody able to check whether it was paid or
    just forgotten.
    """
    original = json.loads(
        C38.PENDING.read_text(encoding="utf-8")) if C38.PENDING.is_file() else {}
    summary = projection_summary()
    doc = OrderedDict(original)
    doc["status"] = "RESOLVED"
    doc["resolved_by"] = WORK_ORDER
    doc["resolved_how"] = OrderedDict([
        ("binding", "PTF-...-APPROVAL-BINDING-039 replaced the record hash "
                    "with semantic-approval/1.0, so the fifteen "
                    "provenance-only approvals the register was protecting "
                    "are no longer withdrawn by a projection."),
        ("the_one_semantic_change", "PTF-MILWAUKEE-FOUNDER-DECISION-040's "
                                    "founder read Saint Kate's corrected "
                                    "reading and approved it. Projecting the "
                                    "store onto it brings the store into "
                                    "agreement with the authority."),
        ("what_041_did", "re-classified every store row against the current "
                         "reader and applied the projection; a substantive "
                         "change nobody had approved would have stopped this "
                         "work order instead."),
    ])
    doc["original_population"] = list(original.get("rows") or {})
    doc["rows_pending_after_041"] = 0
    doc["classification_at_resolution"] = summary["by_classification"]
    doc["note"] = ("Kept rather than deleted. The register existed because a "
                   "reader repair would have withdrawn sixteen founder "
                   "decisions, and that reason is worth being able to read "
                   "later even though the debt is paid.")
    return doc


# --------------------------------------------------------------------------- #
# Phase 6 -- the stale package cannot come back.
# --------------------------------------------------------------------------- #

def superseded_document() -> Dict:
    stale = P37.PREPARED_CONTRACT
    stale_bytes = stale.read_bytes() if stale.is_file() else b""
    stale_doc = json.loads(stale_bytes.decode("utf-8")) if stale_bytes else {}
    return OrderedDict([
        ("schema", "ptf-superseded-release-contracts/1.0"),
        ("what_this_is",
         "Release contracts that must never gate a build again, by content "
         "hash. release_contracts.load_contract consults this, so a "
         "superseded document cannot be resurrected by copying it into the "
         "live directory. The originals are NOT edited: a historical artifact "
         "that quietly grows a new number is worse than a stale one."),
        ("contracts", [OrderedDict([
            ("path", stale.relative_to(REPO).as_posix()),
            ("contract_id", stale_doc.get("contract_id", "")),
            ("market_id", stale_doc.get("market_id", "")),
            ("sha256", _sha(stale_bytes)),
            ("superseded_by", WORK_ORDER),
            ("why", "prepared against a 70-record pet-friendly authority. "
                    "PTF-MILWAUKEE-FOUNDER-DECISION-040 admitted three more "
                    "and one more refusal, so its expected_record_count, its "
                    "expected_sha256 and its held-identity list all describe "
                    "a market that no longer exists."),
            ("stale_assertions", OrderedDict([
                ("expected_record_count",
                 (stale_doc.get("policy_package") or {}).get(
                     "expected_record_count")),
                ("expected_sha256",
                 (stale_doc.get("policy_package") or {}).get(
                     "expected_sha256")),
                ("held_identities",
                 (stale_doc.get("provenance") or {}).get("held_identities")),
            ])),
            ("replacement", FRESH_CONTRACT.relative_to(REPO).as_posix()),
        ])]),
    ])


def superseded_hashes() -> Dict[str, Dict]:
    """sha256 -> the supersession record, for the contract loader."""
    if not SUPERSEDED_REGISTRY.is_file():
        return {}
    doc = json.loads(SUPERSEDED_REGISTRY.read_text(encoding="utf-8"))
    return {row["sha256"]: row for row in doc.get("contracts") or ()}


# --------------------------------------------------------------------------- #
# Phase 7 to 10 -- the simulation. Nothing is written to the repository.
# --------------------------------------------------------------------------- #

def prospective_package() -> Tuple[Dict, bytes]:
    """The policy package publication WOULD commit, and its bytes."""
    doc, changes = P37.published_document()
    if changes:
        raise NormalizationError("; ".join(changes))
    payload = (json.dumps(doc, indent=1, ensure_ascii=False)
               + NEWLINE).encode("utf-8")
    return doc, payload


def prospective_seed_rows() -> List[Dict]:
    rows, refused = P37.seed_rows()
    if refused:
        raise NormalizationError(
            "the derived inventory refuses %d row(s): %s"
            % (len(refused), "; ".join(row["identity_key"] for row in refused)))
    return rows


def _rebind(replacements: Mapping) -> List[Tuple]:
    """Rebind a name on every loaded ``scripts.`` module that holds it.

    Returns what to put back. A simulation that patches only the defining
    module silently measures the unpatched build, and a clean pass obtained
    that way is worse than a failure.
    """
    import types
    undo: List[Tuple] = []
    for module in list(sys.modules.values()):
        if not isinstance(module, types.ModuleType):
            continue
        if not (module.__name__ or "").startswith("scripts."):
            continue
        for name, replacement in replacements.items():
            current = getattr(module, name, None)
            if callable(current):
                undo.append((module, name, current))
                setattr(module, name, replacement)
    return undo


def route_facts() -> Dict:
    """This market's routes as the manifest builder computes them.

    Must be called with the inventory already substituted: it reads the
    production rows and the published package through the same functions the
    real build uses.
    """
    from scripts.pettripfinder.build_market_manifest import build_package
    package = build_package(MARKET)
    return {
        "hotel_routes": len(package.hotel_routes),
        "corridor_routes": len(package.corridor_routes),
        "corridor_unassigned_hotels": list(package.corridor_unassigned_hotels),
        "published_pet_friendly_count": package.published_pet_friendly_count,
        "verified_no_pets_count": package.verified_no_pets_count,
        "unresolved_count": package.unresolved_count,
    }


@contextlib.contextmanager
def as_if_published(stage_contract: bool = True) -> Iterator[None]:
    """Run the real builders against the inventory publication would produce.

    In process and read-only: the seed shard on disk stays empty and the
    package stays ``published: false``. Substituting the two readers is what
    makes this a SIMULATION rather than a publication -- there is no state to
    roll back afterwards because none was written.
    """
    from scripts.pettripfinder import site_data as SD
    doc, _payload = prospective_package()
    rows = prospective_seed_rows()
    others = [row for row in SD.read_production_rows()
              if row.get("market_id") != MARKET]
    facts = {SD.normalize_name(record["name"]): record
             for record in doc["hotels"]}

    from scripts.pettripfinder import release_contracts as RC
    import shutil
    import tempfile

    real_rows = SD.read_production_rows
    real_facts = SD.load_published_hotel_policy_facts
    real_dir = RC.RELEASE_CONTRACTS_DIR

    def fake_rows():
        return others + [dict(row) for row in rows]

    def fake_facts(market_id=""):
        return dict(facts) if market_id == MARKET else real_facts(market_id)

    # Imported BEFORE the rebind, because they import the readers lazily
    # inside a function: a module that first loads AFTER the patch gets a
    # fresh binding of the real reader and quietly builds the committed
    # (empty) inventory instead. That is how the first attempt at this
    # simulation produced a clean pass that measured nothing.
    import importlib
    for name in ("scripts.generate_pettripfinder_columbus_site",
                 "scripts.generate_pettripfinder_pilot",
                 "scripts.pettripfinder.assemble_production_site",
                 "scripts.pettripfinder.assemble_netlify_bundle",
                 "scripts.pettripfinder.build_market_manifest",
                 "scripts.pettripfinder.release_contracts"):
        try:
            importlib.import_module(name)
        except Exception:                                     # noqa: BLE001
            pass

    # Rebound on EVERY module that imported the name, not just on site_data.
    # The site assembler does `from site_data import read_production_rows`, so
    # its module-level name is a separate binding and patching the source
    # module alone left the build reading the committed (empty) inventory --
    # which looked exactly like a clean pass.
    # The site generator does not go through read_production_rows at all: it
    # reads the seed CSV itself. Both doors have to be covered or the build
    # renders every other market from the substituted inventory and this one
    # from an empty file.
    from scripts.generate_pettripfinder_pilot import read_seed_businesses_csv
    real_csv = read_seed_businesses_csv

    def fake_csv(path):
        base = [row for row in real_csv(path)
                if row.get("market_id") != MARKET]
        return base + [dict(row) for row in rows]

    patched = _rebind({"read_production_rows": fake_rows,
                       "load_published_hotel_policy_facts": fake_facts,
                       "read_seed_businesses_csv": fake_csv})
    # A TEMPORARY live-contracts directory: every committed contract copied in,
    # plus Milwaukee's fresh one. Placing the real one in the repository's live
    # directory is a publication step, and this is not publication -- the temp
    # tree is deleted on the way out and the repository never held it.
    staging = Path(tempfile.mkdtemp(prefix="ptf-041-contracts-"))
    try:
        if stage_contract:
            if real_dir.is_dir():
                for path in real_dir.glob("*.json"):
                    shutil.copy2(path, staging / path.name)
            # Built INSIDE the data patch and outside any nested simulation:
            # the contract needs this market's route counts and the route
            # counts need the inventory substituted. Only one order works.
            (staging / ("%s.json" % MARKET)).write_text(
                json.dumps(fresh_contract(route_facts()), indent=1,
                           ensure_ascii=False) + NEWLINE, encoding="utf-8")
            RC.RELEASE_CONTRACTS_DIR = staging
        yield
    finally:
        for module, name, original in patched:
            setattr(module, name, original)
        RC.RELEASE_CONTRACTS_DIR = real_dir
        shutil.rmtree(staging, ignore_errors=True)


def simulate() -> Dict:
    """What publication would produce, measured with the real builders."""
    from scripts.pettripfinder.assemble_netlify_bundle import content_sha256
    from scripts.pettripfinder.listing_dataset_builder import build_listing_dataset
    from scripts.pettripfinder import publication_guard as PG
    from scripts.generate_pettripfinder_pilot import load_launch_package

    doc, payload = prospective_package()
    rows = prospective_seed_rows()
    exclusions = MA.load_market_exclusions(MARKET)
    held = set(P37.held_identities())

    with as_if_published(stage_contract=False):
        routes = route_facts()
        launch = load_launch_package()
        dataset = build_listing_dataset(
            seed_businesses=rows,
            categories=launch["categories"],
            locations=launch["locations"],
            distinct_entity_groups=PG.distinct_entity_groups())

    names = {listing.business_name for listing in dataset.dataset.listings}
    by_name = {row["name"]: row for row in rows}
    excluded_names = {row["canonical_name"] for row in exclusions}
    closure = {row["identity_key"]: row["disposition"]
               for row in C38.active_rows()}
    leaked = sorted(name for name in names
                    if closure.get(_key_for(name, by_name)) not in
                    (C38.AUTHORITY_PET_FRIENDLY,))
    return OrderedDict([
        ("policy_package_sha256", content_sha256(payload)),
        ("policy_package_record_count", len(doc["hotels"])),
        ("pet_friendly_profiles", len(rows)),
        ("verified_no_pets", len(exclusions)),
        ("listings_built", len(dataset.dataset.listings)),
        ("listing_errors", list(dataset.errors)),
        ("rejected_duplicates", [str(item) for item in
                                 dataset.rejected_duplicates]),
        ("hotel_routes", routes["hotel_routes"]),
        ("corridor_routes", routes["corridor_routes"]),
        ("corridor_unassigned_hotels",
         routes["corridor_unassigned_hotels"]),
        ("published_pet_friendly_count",
         routes["published_pet_friendly_count"]),
        ("unresolved_count", routes["unresolved_count"]),
        ("held_identities", sorted(held)),
        ("held_leaked_into_inventory",
         sorted(name for name in names
                if _key_for(name, by_name) in held)),
        ("exclusion_leaked_into_inventory",
         sorted(names & excluded_names)),
        ("non_authority_leaked_into_inventory", leaked),
        ("dual_brand_jefferson_present", sorted(
            name for name in names if "Home2 Suites by Hilton Milwaukee "
            "Downtown" == name or "Tru by Hilton Milwaukee Downtown" == name)),
        ("saint_kate_present",
         "Saint Kate - The Arts Hotel" in names),
        # The PROSPECTIVE package's own flag -- what publication would
        # write. The committed package on disk is still published:false
        # and 041 did not touch it.
        ("prospective_package_published_flag", doc["published"]),
        ("committed_package_published", json.loads(
            A36.AUTHORITY.read_text(encoding="utf-8"))["published"]),
    ])


def _key_for(name: str, by_name: Mapping) -> str:
    from scripts.pettripfinder.contracts.identity_key import ptf_identity_key
    row = by_name.get(name)
    return ptf_identity_key(row["name"]) if row else ptf_identity_key(name)


def simulate_twice() -> Dict:
    first = simulate()
    second = simulate()
    stable = json.dumps(first, sort_keys=True, default=str) == \
        json.dumps(second, sort_keys=True, default=str)
    return {"deterministic": stable, "first": first, "second": second}


def dry_run_site(times: int = 2, root: str = "") -> Dict:
    """Build the whole multi-market site as publication would, twice.

    Into a scratch tree outside the repository, with the inventory
    substituted in process. Nothing is written to the repository and no
    contract is moved into the live directory; the run measures the pages,
    routes and gates the real assembler produces and then deletes them.

    The BASELINE build is measured too, because "Milwaukee adds 438 pages and
    breaks nothing" is a claim about a difference, and a difference needs both
    sides.
    """
    import shutil
    from scripts.pettripfinder.assemble_production_site import assemble

    # A SHORT path outside the repository: the generated tree nests deeply
    # enough that a long root trips the Windows 260-character path limit
    # mid-build, which surfaces as a missing file rather than as a path error.
    base = Path(root) if root else Path(chr(67) + ":/t/ptf041")
    shutil.rmtree(base, ignore_errors=True)
    base.mkdir(parents=True, exist_ok=True)
    try:
        baseline = assemble(output=str(base / "base"))
        runs = []
        for index in range(times):
            with as_if_published():
                runs.append(assemble(output=str(base / ("sim%d" % index))))
        first = runs[0]
        return OrderedDict([
            ("baseline", _bundle_facts(baseline)),
            ("with_milwaukee", _bundle_facts(first)),
            ("added_by_milwaukee", OrderedDict([
                ("html_pages", first["total_html_pages"]
                 - baseline["total_html_pages"]),
                ("sitemap_routes", first["sitemap_route_count"]
                 - baseline["sitemap_route_count"]),
            ])),
            ("runs", times),
            ("deterministic", len({run["bundle_sha256"] for run in runs}) == 1),
            ("bundle_sha256_each", [run["bundle_sha256"] for run in runs]),
            ("gates", OrderedDict((name, gate["pass"])
                                  for name, gate in first["gates"].items())),
            ("gates_failing", [name for name, gate in first["gates"].items()
                               if not gate["pass"]]),
        ])
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _bundle_facts(manifest: Mapping) -> Dict:
    return OrderedDict([
        ("markets", list(manifest["market_fragments_included"])),
        ("total_html_pages", manifest["total_html_pages"]),
        ("total_files", manifest["total_files"]),
        ("sitemap_route_count", manifest["sitemap_route_count"]),
        ("broken_links", manifest["broken_links"]),
        ("collision_count", manifest["collision_count"]),
        ("global_shadowing_count", manifest["global_shadowing_count"]),
        ("canonical_violations", manifest["canonical_violations"]),
        ("bundle_sha256", manifest["bundle_sha256"]),
        ("all_gates_pass", manifest["all_gates_pass"]),
        ("deployment_authorized", manifest["deployment_authorized"]),
    ])


# --------------------------------------------------------------------------- #
# Phase 11 -- a fresh contract for the CURRENT authority.
# --------------------------------------------------------------------------- #

def fresh_contract(routes: Optional[Mapping] = None) -> Dict:
    from scripts.pettripfinder.assemble_netlify_bundle import content_sha256
    from scripts.pettripfinder.contracts import enums
    stale = P37.PREPARED_CONTRACT
    stale_doc = json.loads(stale.read_text(encoding="utf-8")) \
        if stale.is_file() else {}
    doc, payload = prospective_package()
    if routes is None:
        with as_if_published(stage_contract=False):
            routes = route_facts()
    result = {
        "pet_friendly_profiles": len(doc["hotels"]),
        "verified_no_pets": len(MA.load_market_exclusions(MARKET)),
        "listings_built": len(doc["hotels"]),
        "hotel_routes": routes["hotel_routes"],
        "corridor_routes": routes["corridor_routes"],
    }
    return OrderedDict([
        ("schema", stale_doc.get("schema", "ptf-market-release-contract/1.0")),
        ("contract_id", "pettripfinder-milwaukee-wi-release/2.0"),
        ("market_id", MARKET),
        ("product", "pettripfinder-milwaukee-wi"),
        ("release_name_prefix", "prod-041-milwaukee"),
        ("status", "PREPARED_NOT_LIVE"),
        ("status_note",
         "Prepared against the CURRENT authority and deliberately not placed "
         "in the live contracts directory. It grants nothing: 041 published "
         "nothing and deployed nothing. The publication work order that runs "
         "next may move it, having re-derived it."),
        ("supersedes", OrderedDict([
            ("contract_id", stale_doc.get("contract_id", "")),
            ("path", stale.relative_to(REPO).as_posix()),
            ("sha256", _sha(stale.read_bytes()) if stale.is_file() else ""),
            ("why", "prepared against 70 pet-friendly records; the founders "
                    "have since approved 73"),
        ])),
        ("deployment_authorization", OrderedDict([
            ("grants_deployment", False),
            ("asserts_market_complete", False),
        ])),
        ("provenance", OrderedDict([
            ("authority_work_orders", [A36.WORK_ORDER, D40.WORK_ORDER]),
            ("decision_ledgers", [F36.LEDGER.name, D40.LEDGER.name]),
            ("binding_contract", AB.BINDING_CONTRACT_VERSION),
            ("normalization_work_order", WORK_ORDER),
            ("held_identities", sorted(P37.held_identities())),
            ("held_note",
             "Held rows reach no publication set. Hyatt Regency because a "
             "price is not permission; Knickerbocker and The Iron Horse "
             "because the identity gate declined their policy subpages and "
             "the founder would not bypass it by hand."),
        ])),
        ("policy_package", OrderedDict([
            ("path", A36.AUTHORITY.relative_to(REPO).as_posix()),
            ("expected_sha256", content_sha256(payload)),
            ("expected_schema_version", enums.POLICY_SCHEMA_VERSION),
            ("expected_record_count", len(doc["hotels"])),
            ("identity_authority", True),
        ])),
        ("public_surface", OrderedDict([
            ("pet_friendly_profiles", result["pet_friendly_profiles"]),
            ("verified_no_pets", result["verified_no_pets"]),
            ("listings", result["listings_built"]),
        ])),
        ("routes", OrderedDict([
            ("market_slug", MARKET),
            ("hotel_route_count", result["hotel_routes"]),
            ("corridor_route_count", result["corridor_routes"]),
        ])),
        ("reconciliation", OrderedDict([
            ("active_eligible", C38.reconciliation()["active_eligible"]),
            ("census_total", C38.reconciliation()["census_total"]),
            ("by_disposition", C38.reconciliation()["by_disposition"]),
        ])),
        ("publish", OrderedDict([("published", False)])),
    ])


# --------------------------------------------------------------------------- #
# Writing.
# --------------------------------------------------------------------------- #

def write(apply: bool = False) -> Dict:
    summary = assert_safe_to_normalize()
    # Captured BEFORE the store moves. Classifying afterwards reports the
    # outcome ("everything is identical") instead of the decision, and the
    # decision is the thing a later reader needs to audit.
    rows_before = classify_projection()
    store = normalize_store(apply=apply)
    simulation = simulate_twice()
    site = dry_run_site()
    contract = fresh_contract()
    if apply:
        PKG.mkdir(parents=True, exist_ok=True)
        PROJECTION_REPORT.write_text(
            json.dumps(OrderedDict([
                ("schema", "ptf-store-projection-resolution/1.0"),
                ("work_order", WORK_ORDER),
                ("market_id", MARKET),
                ("summary", summary),
                ("store", store),
                ("classified_before_normalizing", True),
                ("rows", rows_before),
            ]), indent=1, ensure_ascii=False) + NEWLINE, encoding="utf-8")
        C38.PENDING.write_text(
            json.dumps(retired_register_document(), indent=1,
                       ensure_ascii=False) + NEWLINE, encoding="utf-8")
        SUPERSEDED_REGISTRY.write_text(
            json.dumps(superseded_document(), indent=1, ensure_ascii=False)
            + NEWLINE, encoding="utf-8")
        FRESH_CONTRACT.write_text(
            json.dumps(contract, indent=1, ensure_ascii=False) + NEWLINE,
            encoding="utf-8")
        SIMULATION.write_text(
            json.dumps(OrderedDict([
                ("schema", "ptf-publication-simulation/1.0"),
                ("work_order", WORK_ORDER),
                ("market_id", MARKET),
                ("published", 0),
                ("deployed", 0),
                ("provider_calls", 0),
                ("cost_usd", 0.0),
                ("simulation", simulation),
                ("site_dry_run", site),
            ]), indent=1, ensure_ascii=False) + NEWLINE, encoding="utf-8")
    return {
        "applied": apply,
        "projection": summary,
        "store": store,
        "deterministic": simulation["deterministic"],
        "simulation": simulation["first"],
        "site_dry_run": site,
        "fresh_contract": FRESH_CONTRACT.relative_to(REPO).as_posix(),
        "superseded_contracts": len(superseded_document()["contracts"]),
        "published": 0,
        "deployed": 0,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=WORK_ORDER)
    parser.add_argument("--classify", action="store_true")
    parser.add_argument("--simulate", action="store_true")
    parser.add_argument("--site", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    if args.classify:
        print(json.dumps(projection_summary(), indent=2, default=str))
    if args.simulate:
        print(json.dumps(simulate_twice()["first"], indent=2, default=str))
    if args.site:
        print(json.dumps(dry_run_site(), indent=2, default=str))
    if args.apply:
        print(json.dumps(write(apply=True), indent=2, default=str))
    return 0


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(main())
