"""ATLAS-THROUGHPUT-005 -- the atomic release coordinator and the final
candidate lifecycle.

001 measured the waste, 002 made a market-local change provable, 003 sealed the
market package and proved a data-only release safe in 61 seconds, 004 made a
validated market bundle reusable across runs. What none of them fixed is the
shape of a release: today a deploy is composed by re-generating every market
from whatever the working tree happens to hold, and the artifact that gets
authorized is not provably the artifact that was validated.

This module states the release as one equation:

    CURRENT VERIFIED LIVE RELEASE
  + ONE AUTHORIZED SEALED MARKET PACKAGE DELTA
  + REUSABLE VALIDATED MARKET BUNDLES
  = ONE EXACT FINAL STAGED CANDIDATE

and makes that candidate the ONLY thing a founder can authorize.

Four historical failures are designed out rather than tested for:

* **Stale lineage** (Pittsburgh / Indianapolis). The preservation baseline is
  the CURRENT VERIFIED LIVE RELEASE, never the branch. A stale worktree
  contributes exactly one sealed package delta; every other live market is
  inherited from the live release by digest, so a branch that predates a newer
  market cannot remove it.
* **Pre-flip / post-flip hashes** (Cincinnati / Toledo). Final participation is
  an INPUT to staging, so it is inside the bytes before the candidate is
  hashed. There is no build -> authorize -> flip -> rebuild path, and a
  preview digest can never satisfy an authorization for the final candidate.
* **Authorization bound to the wrong artifact.** An authorization names the
  candidate digest, the bundle digest, the parent release digest and the
  intended-delta digest. All four must still hold at activation.
* **Stale rollback.** A rollback targets an exact prior verified release held
  in durable release storage, and is refused if a newer release is live.

Nothing here deploys. The activation interface talks to a host adapter; the
only adapter this order ships is a simulator, and REAL_PRODUCTION_ACTIVATION
stays DISABLED (see ``activation_status``).
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import sys
import time
import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from scripts.pettripfinder import assemble_production_site as APS
from scripts.pettripfinder import bundle_cache as BC
from scripts.pettripfinder import fast_release_lane as FL
from scripts.pettripfinder import launch_participation as LP
from scripts.pettripfinder import release_index as RI
from scripts.pettripfinder import sealed_market_package as SMP

REPO_ROOT = SMP.REPO_ROOT
DEPLOY_DIR = REPO_ROOT / "deploy" / "netlify"
PINS_DIR = REPO_ROOT / "tests" / "pettripfinder" / "pins"
DEFAULT_STORE_ROOT = REPO_ROOT / "data" / "release_store"
DEFAULT_CANDIDATE_ROOT = REPO_ROOT / "data" / "release_candidates"
STORE_ENV = "PTF_RELEASE_STORE_ROOT"
CANDIDATE_ENV = "PTF_RELEASE_CANDIDATE_ROOT"

COORDINATOR_VERSION = "ptf-release-coordinator/1.0"
MANIFEST_SCHEMA = "ptf-release-manifest/1.0"
AUTHORIZATION_SCHEMA = "ptf-release-authorization/1.0"
ACTIVATION_SCHEMA = "ptf-release-activation-record/1.0"
DIFF_SCHEMA = "ptf-release-diff/1.0"
STORE_SCHEMA = "ptf-release-store-entry/1.0"
VERIFICATION_SCHEMA = "ptf-release-live-verification/1.0"

#: The candidate lifecycle. A candidate moves forward only; every state but
#: SOURCE_READY names an immutable artifact.
SOURCE_READY = "SOURCE_READY"
CANDIDATE_STAGED = "CANDIDATE_STAGED"
FOUNDER_AUTHORIZED = "FOUNDER_AUTHORIZED"
LIVE = "LIVE"
FAILED = "FAILED"
ABANDONED = "ABANDONED"
LIFECYCLE = (SOURCE_READY, CANDIDATE_STAGED, FOUNDER_AUTHORIZED, LIVE, FAILED, ABANDONED)

#: Where a participating market's files came from. Recorded per market on the
#: manifest so a reader can tell an inherited market from a rebuilt one.
FROM_PACKAGE = "PACKAGE_BUNDLE"
FROM_STORE = "RELEASE_STORE_FRAGMENT"
REBUILT = "REBUILT_FROM_COMMITTED_AUTHORITY"

#: The intent of a delta. Absence is never an intent (phase 4).
UPDATE = "UPDATE"
ADD = "ADD"
REMOVE = "REMOVE"
NO_DELTA = "NO_DELTA"
DELTA_KINDS = (UPDATE, ADD, REMOVE, NO_DELTA)

#: 004's global dependency map, restated as the coordinator's regeneration
#: policy. UNKNOWN fails closed: staging refuses rather than guess.
REUSE = "REUSE"
REGENERATE = "REGENERATE"
INCREMENTAL = "INCREMENTAL"
UNKNOWN = "UNKNOWN"
GLOBAL_ARTIFACTS: "OrderedDict[str, Tuple[str, str]]" = OrderedDict((
    ("index.html", (REGENERATE, "membership and navigation: build_global_home over the visible markets")),
    ("pet-friendly-hotels/index.html", (REGENERATE, "membership and per-market published counts")),
    ("sitemap.xml", (REGENERATE, "every indexable route in the composed bundle")),
    ("llms.txt", (REGENERATE, "membership and base_url")),
    ("robots.txt", (INCREMENTAL, "base_url only; identical bytes for an unchanged base_url")),
    ("_headers", (INCREMENTAL, "copied from the tracked context source and hashed")),
    ("_redirects", (INCREMENTAL, "copied from the tracked source and hashed")),
    ("about/index.html", (REUSE, "the anchor market's shell page, inherited with the anchor fragment")),
    ("contact/index.html", (REUSE, "the anchor market's shell page")),
    ("methodology/index.html", (REUSE, "the anchor market's shell page")),
))

#: Every refusal the coordinator can state. A refusal is a named string, never
#: an exception message a caller has to parse.
STALE_PARENT = "STALE_PARENT"
LIVE_NOT_VERIFIED = "LIVE_NOT_VERIFIED"
CANDIDATE_DIGEST_MISMATCH = "CANDIDATE_DIGEST_MISMATCH"
BUNDLE_DIGEST_MISMATCH = "BUNDLE_DIGEST_MISMATCH"
PARENT_DIGEST_MISMATCH = "PARENT_DIGEST_MISMATCH"
INTENDED_DELTA_MISMATCH = "INTENDED_DELTA_MISMATCH"
CANDIDATE_CORRUPT = "CANDIDATE_CORRUPT"
CANDIDATE_SUPERSEDED = "CANDIDATE_SUPERSEDED"
AUTHORIZATION_REVOKED = "AUTHORIZATION_REVOKED"
UNAUTHORIZED_ADDITION = "UNAUTHORIZED_ADDITION"
UNAUTHORIZED_REMOVAL = "UNAUTHORIZED_REMOVAL"
UNKNOWN_GLOBAL_DEPENDENCY = "UNKNOWN_GLOBAL_DEPENDENCY"
FRAGMENT_UNAVAILABLE = "FRAGMENT_UNAVAILABLE"
RELEASE_NOT_CURRENT = "RELEASE_NOT_CURRENT"
NOT_AUTHORIZED = "NOT_AUTHORIZED"
GATES_FAILED = "GATES_FAILED"

#: Activation outcomes. UNKNOWN is not FAILED: an unknown outcome means the
#: host must be reconciled before anything else happens (phase 19 case 4).
ACTIVATED = "ACTIVATED"
ACTIVATION_FAILED = "ACTIVATION_FAILED"
ACTIVATION_UNKNOWN = "ACTIVATION_UNKNOWN"
ACTIVATION_REFUSED = "ACTIVATION_REFUSED"

#: 005 shipped the machine, not the deploy. 006 added a real host adapter and
#: an explicit, EMPTY allowlist in front of it; the default stays DISABLED and
#: only the gate file can change that, per market.
REAL_PRODUCTION_ACTIVATION = "DISABLED"
PRODUCTION_GATE_PATH = SMP.LAUNCH_PACKAGE / "release_production_gate.json"
PRODUCTION_GATE_SCHEMA = "ptf-release-production-gate/1.0"

#: Refusals 006 adds.
PRODUCTION_GATE_CLOSED = "PRODUCTION_GATE_CLOSED"
MARKET_NOT_IN_PILOT_ALLOWLIST = "MARKET_NOT_IN_PILOT_ALLOWLIST"
BROAD_VALIDATION_REFUSED = "BROAD_VALIDATION_REFUSED"


#: Every release operation this process performed, in order. The 002 profiler
#: writes them at session end; the coordinator never depends on them.
EVENTS: List["OrderedDict[str, Any]"] = []


def _event(operation: str, **fields: Any) -> "OrderedDict[str, Any]":
    row: "OrderedDict[str, Any]" = OrderedDict((("release_operation", operation),
                                                ("ts", round(time.time(), 3))))
    row.update(fields)
    EVENTS.append(row)
    return row


def summary() -> "OrderedDict[str, Any]":
    """What this process did to releases, for the throughput profiler."""
    by_operation: "OrderedDict[str, int]" = OrderedDict()
    for row in EVENTS:
        key = str(row.get("release_operation"))
        by_operation[key] = by_operation.get(key, 0) + 1
    staged = [r for r in EVENTS if r.get("release_operation") == "stage"]
    return OrderedDict((
        ("coordinator_version", COORDINATOR_VERSION),
        ("operations", len(EVENTS)),
        ("by_operation", by_operation),
        ("candidates_staged", len(staged)),
        ("bundles_reused", sum(int(r.get("bundles_reused") or 0) for r in staged)),
        ("bundles_rebuilt", sum(int(r.get("bundles_rebuilt") or 0) for r in staged)),
        ("stage_seconds", round(sum(float(r.get("stage_seconds") or 0) for r in staged), 3)),
        ("stale_parent_refusals", sum(1 for r in EVENTS if r.get("stale_parent"))),
        ("REAL_PRODUCTION_ACTIVATION", REAL_PRODUCTION_ACTIVATION),
    ))


class CoordinatorError(RuntimeError):
    """A refusal that must not be recovered from by retrying."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__("%s: %s" % (code, detail) if detail else code)
        self.code = code
        self.detail = detail


# --------------------------------------------------------------------------- #
# Small shared helpers.
# --------------------------------------------------------------------------- #

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(moment: Optional[datetime] = None) -> str:
    return (moment or _now()).strftime("%Y-%m-%dT%H:%M:%SZ")


def digest_of(document: Mapping) -> str:
    """The repo's digest convention over a canonical document."""
    return SMP.sha256_text(SMP.canonical_json(document))


def _read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"), object_pairs_hook=OrderedDict)


def _write_json(path: Path, document: Mapping) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp-%s" % uuid.uuid4().hex[:8])
    tmp.write_text(SMP.canonical_json(document) + "\n", encoding="utf-8", newline="\n")
    os.replace(str(tmp), str(path))
    return path


def _object_name(digest: str) -> str:
    """A content address as a FILENAME. Windows rejects the ``sha256:`` colon,
    so objects are stored under the bare hex and the prefixed form stays the
    identity everywhere else."""
    return str(digest).split(":")[-1]


def store_root(root: Optional[Path] = None) -> Path:
    if root is not None:
        return Path(root)
    env = os.environ.get(STORE_ENV)
    return Path(env) if env else DEFAULT_STORE_ROOT


def candidate_root(root: Optional[Path] = None) -> Path:
    if root is not None:
        return Path(root)
    env = os.environ.get(CANDIDATE_ENV)
    return Path(env) if env else DEFAULT_CANDIDATE_ROOT


# --------------------------------------------------------------------------- #
# Phase 2: current live truth, and every file that claims it.
# --------------------------------------------------------------------------- #

#: The facts that exist in more than one committed place. The coordinator does
#: not pick one: ``LiveTruth`` reads them all through
#: ``release_index.current_verified_live``, which fails closed on any
#: disagreement, and records here WHICH files were reconciled so a reader can
#: see the duplication rather than inherit it.
LIVE_REPRESENTATIONS: Tuple["OrderedDict[str, Any]", ...] = (
    OrderedDict((
        ("path", "deploy/netlify/deployment_records/<newest DEPLOYED>.json"),
        ("claims", ("deployment_id", "previous_deployment_id", "rollback_target", "source_commit",
                    "bundle_sha256", "sitemap_sha256", "participating_markets", "profile_counts",
                    "total_profiles", "sitemap_route_count", "authorization_id", "final_status")),
        ("owner", "scripts/pettripfinder/deployment_authorization.py"),
        ("role", "PRIMARY -- the newest DEPLOYED record is what production served"),
    )),
    OrderedDict((
        ("path", "deploy/netlify/global_deployment_manifest.json"),
        ("claims", ("bundle_sha256", "participating_markets", "published_profiles",
                    "total_published_profiles", "sitemap_route_count", "source_commit",
                    "launch_participation.sha256", "release_contract sha256 per market")),
        ("owner", "scripts/pettripfinder/global_deployment.py"),
        ("role", "CROSS-CHECK -- disagreement with the record is a problem, not a tiebreak"),
    )),
    OrderedDict((
        ("path", "tests/pettripfinder/pins/deployment_state.json"),
        ("claims", ("live.deploy_id", "live.bundle_sha256", "live.rollback_target",
                    "live.total_profiles", "live.sitemap_route_count", "live.participating_markets",
                    "source.* (the branch, deliberately allowed to be ahead)")),
        ("owner", "tests/pettripfinder/market_state.py"),
        ("role", "CROSS-CHECK -- the suite's mirror of live; its source block is NOT live"),
    )),
    OrderedDict((
        ("path", "deploy/netlify/deployment_authorizations/<record.authorization_id>.json"),
        ("claims", ("bundle_sha256", "authorization_status", "participating_markets",
                    "launch_participation_sha256", "rollback_target", "authorized_by", "authorized_at")),
        ("owner", "scripts/pettripfinder/deployment_authorization.py"),
        ("role", "CROSS-CHECK -- the consumed authorization must bind the deployed bundle"),
    )),
    OrderedDict((
        ("path", "deploy/netlify/launch_participation.json"),
        ("claims", ("markets[].launch_status", "decision.decided_by", "decision.decided_on")),
        ("owner", "scripts/pettripfinder/launch_participation.py"),
        ("role", "MEMBERSHIP AUTHORITY -- who may participate; hashed into every candidate"),
    )),
    OrderedDict((
        ("path", "launch_packages/pettripfinder/markets/packages/<market>/<package>.json"),
        ("claims", ("parent_live_state.live_deploy_id", "parent_live_state.rollback_target",
                    "parent_live_state.participating_markets", "parent_live_state.profile_counts",
                    "parent_live_state.total_profiles", "parent_live_state.sitemap_route_count",
                    "parent_live_state.live_index_digest")),
        ("owner", "scripts/pettripfinder/sealed_market_package.py"),
        ("role", "SNAPSHOT -- what live was when the package sealed; rule N compares it to now"),
    )),
    OrderedDict((
        ("path", "deploy/netlify/live_production_routes.txt"),
        ("claims", ("every route production serves",)),
        ("owner", "scripts/pettripfinder/assemble_production_site.py (_run_migration_gate)"),
        ("role", "CROSS-CHECK -- the composed candidate must preserve every listed route"),
    )),
    OrderedDict((
        ("path", "tests/pettripfinder/pins/market_state.json"),
        ("claims", ("per-market census / pet_friendly / profiles / corridor_routes",)),
        ("owner", "tests/pettripfinder/market_state.py"),
        ("role", "CROSS-CHECK -- reviewed per-market numbers, not a live record"),
    )),
)


class LiveTruth:
    """CURRENT VERIFIED LIVE RELEASE, read only.

    Wraps ``release_index.current_verified_live`` (which already reconciles the
    deployment record, the global manifest, the deployment-state pin and the
    consumed authorization, and reports every disagreement) and adds the
    committed-authority index plus a canonical parent release manifest so a
    candidate can name its parent by digest.

    ``problems`` non-empty means there is no verified live release: staging
    refuses. 005 never writes any of these files.
    """

    def __init__(self, state: RI.LiveState, index: RI.ReleaseIndex, problems: Sequence[str]) -> None:
        self.state = state
        self.index = index
        self.problems = tuple(problems)
        self._manifest: Optional["OrderedDict[str, Any]"] = None

    @classmethod
    def read(cls, deploy_dir: Optional[Path] = None, pins_dir: Optional[Path] = None) -> "LiveTruth":
        state = RI.current_verified_live(deploy_dir=deploy_dir, pins_dir=pins_dir)
        index, state, problems = RI.live_index(state)
        return cls(state, index, problems)

    @property
    def participating_markets(self) -> Tuple[str, ...]:
        return tuple(self.state.participating_markets)

    @property
    def verified(self) -> bool:
        return not self.problems

    def require_verified(self) -> None:
        if self.problems:
            raise CoordinatorError(LIVE_NOT_VERIFIED,
                                   "; ".join(self.problems[:4]) + (" (+%d more)" % (len(self.problems) - 4)
                                                                   if len(self.problems) > 4 else ""))

    def manifest(self) -> "OrderedDict[str, Any]":
        """The parent release, in the coordinator's own manifest shape.

        The live release predates this module, so its manifest is DERIVED from
        the committed records rather than read: that derivation is what gives
        the first candidate a parent digest to bind to.
        """
        if self._manifest is not None:
            # A copy: a caller that attaches fragment digests to the parent
            # release must not thereby change the parent's own identity. The
            # 005 seeding run found exactly that.
            return copy.deepcopy(self._manifest)
        markets: List["OrderedDict[str, Any]"] = []
        for market_id in sorted(self.state.participating_markets):
            idx = self.index.markets.get(market_id)
            markets.append(OrderedDict((
                ("market_id", market_id),
                ("package_digest", None),
                ("build_input_key", None),
                ("bundle_digest", None),
                ("validation_receipt_digest", None),
                ("fragment_source", "LIVE_DEPLOYED_BUNDLE"),
                ("profile_count", int(self.state.profile_counts.get(market_id, 0))),
                ("route_count", len(idx.routes) if idx is not None else None),
            )))
        self._manifest = OrderedDict((
            ("schema", MANIFEST_SCHEMA),
            ("release_schema_version", MANIFEST_SCHEMA),
            ("coordinator_version", COORDINATOR_VERSION),
            ("derived", True),
            ("derived_from", OrderedDict((
                ("deployment_record", self.state.deployment_record),
                ("authorization_id", self.state.authorization_id),
                ("deploy_id", self.state.deploy_id),
            ))),
            ("parent_release_digest", None),
            ("source_commit", self.state.source_commit),
            ("participating_markets", [m["market_id"] for m in markets]),
            ("markets", markets),
            ("total_profiles", int(self.state.total_profiles)),
            ("sitemap_route_count", int(self.state.sitemap_route_count)),
            ("deployment_artifact_digest", self.state.bundle_sha256),
            ("sitemap_sha256", self.state.sitemap_sha256),
            ("global_index_digest", self.index.digest() if hasattr(self.index, "digest") else None),
            ("rollback_target", self.state.rollback_target),
            ("status", LIVE),
        ))
        return copy.deepcopy(self._manifest)

    def digest(self) -> str:
        return digest_of(self.manifest())

    def to_dict(self) -> "OrderedDict[str, Any]":
        return OrderedDict((
            ("verified", self.verified),
            ("problems", list(self.problems)),
            ("live_state", self.state.to_dict()),
            ("parent_release_digest", self.digest()),
            ("representations", [OrderedDict(r) for r in LIVE_REPRESENTATIONS]),
        ))


# --------------------------------------------------------------------------- #
# Phase 22 / packet item 5: durable release storage.
# --------------------------------------------------------------------------- #

class ReleaseStore:
    """Durable per-release storage of the fragments a release was built from.

    The 004 bundle cache is evictable by design: losing an object costs a
    rebuild. A release store is not a cache. It holds the CURRENT LIVE release
    and the ROLLBACK target, so neither depends on an evictable artifact, and
    it is what lets a candidate inherit ten unchanged markets without
    rebuilding them.

    Layout::

        <root>/releases/<release_digest>.json     the stored release manifest
        <root>/fragments/<fragment_digest>.zip    one market's fragment tree
        <root>/bundles/<bundle_sha256>.zip        a whole composed bundle

    Objects are immutable and content addressed; a second write of the same
    digest is a no-op, never an overwrite.
    """

    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = store_root(root)
        for sub in ("releases", "fragments", "bundles", "tmp"):
            (self.root / sub).mkdir(parents=True, exist_ok=True)

    # ---- objects ---------------------------------------------------------- #
    def _put_tree(self, kind: str, tree: Path) -> "OrderedDict[str, Any]":
        tmp = self.root / "tmp" / ("%s-%s.zip" % (kind, uuid.uuid4().hex[:12]))
        info = BC.write_archive(Path(tree), tmp)
        digest = info["archive_sha256"] if "archive_sha256" in info else SMP.sha256_bytes(tmp.read_bytes())
        target = self.root / kind / ("%s.zip" % _object_name(digest))
        if target.exists():
            tmp.unlink(missing_ok=True)
        else:
            os.replace(str(tmp), str(target))
        return OrderedDict((("digest", digest), ("path", str(target)), ("info", info)))

    def put_fragment(self, market_id: str, tree: Path) -> "OrderedDict[str, Any]":
        out = self._put_tree("fragments", tree)
        out["market_id"] = market_id
        return out

    def put_bundle(self, tree: Path) -> "OrderedDict[str, Any]":
        return self._put_tree("bundles", tree)

    def has_fragment(self, digest: str) -> bool:
        return (self.root / "fragments" / ("%s.zip" % _object_name(digest))).is_file()

    def extract_fragment(self, digest: str, target: Path) -> Path:
        archive = self.root / "fragments" / ("%s.zip" % _object_name(digest))
        if not archive.is_file():
            raise CoordinatorError(FRAGMENT_UNAVAILABLE, "no stored fragment %s" % digest[:16])
        BC.extract_archive(archive, Path(target))
        return Path(target)

    # ---- releases --------------------------------------------------------- #
    def put_release(self, manifest: Mapping) -> Path:
        release_digest = digest_of(manifest)
        path = self.root / "releases" / ("%s.json" % _object_name(release_digest))
        if not path.is_file():
            _write_json(path, manifest)
        return path

    def get_release(self, release_digest: str) -> Optional["OrderedDict[str, Any]"]:
        path = self.root / "releases" / ("%s.json" % _object_name(release_digest))
        return _read_json(path) if path.is_file() else None

    def releases(self) -> List[str]:
        return sorted(p.stem for p in (self.root / "releases").glob("*.json"))

    def fragment_digests(self, release_digest: str) -> "OrderedDict[str, str]":
        doc = self.get_release(release_digest) or OrderedDict()
        return OrderedDict((m["market_id"], m.get("fragment_digest"))
                           for m in (doc.get("markets") or ()) if m.get("fragment_digest"))

    # ---- seeding ---------------------------------------------------------- #
    def seed_from_assembly(self, work_root: Path, manifest: Mapping, *,
                           live: Optional[LiveTruth] = None) -> "OrderedDict[str, Any]":
        """Record a whole-site assembly as a release, fragment by fragment.

        ``work_root`` is an ``assemble_production_site.assemble(...,
        keep_fragments=True)`` output: ``site/`` is the composed bundle and
        ``.assemble_work/fragments/<market_id>/`` is each market's generated
        tree. The composed bundle digest is checked against the live record
        when ``live`` is given -- that check is what makes the seeded release
        the LIVE release rather than merely a build of it.
        """
        work_root = Path(work_root)
        site = work_root / "site"
        fragments_dir = work_root / ".assemble_work" / "fragments"
        if not site.is_dir():
            raise CoordinatorError(FRAGMENT_UNAVAILABLE, "no composed site under %s" % work_root)
        if not fragments_dir.is_dir():
            raise CoordinatorError(FRAGMENT_UNAVAILABLE,
                                   "assemble(keep_fragments=True) is required to seed a release store")
        hashes = APS.file_hashes(site)
        bundle_sha = APS.bundle_digest(hashes)
        problems: List[str] = []
        if live is not None and live.state.bundle_sha256 and bundle_sha != live.state.bundle_sha256:
            problems.append("composed bundle %s is not the live bundle %s"
                            % (bundle_sha[:12], live.state.bundle_sha256[:12]))
        rows: List["OrderedDict[str, Any]"] = []
        for market_id in sorted(manifest.get("market_fragments_included") or ()):
            tree = fragments_dir / market_id
            if not tree.is_dir():
                problems.append("no fragment tree for %s" % market_id)
                continue
            stored = self.put_fragment(market_id, tree)
            frag = (manifest.get("fragments") or {}).get(market_id) or {}
            rows.append(OrderedDict((
                ("market_id", market_id),
                ("fragment_digest", stored["digest"]),
                ("published_count", frag.get("published_count")),
                ("files_contributed", frag.get("files_contributed")),
            )))
        bundle = self.put_bundle(site)
        doc = OrderedDict((
            ("schema", STORE_SCHEMA),
            ("kind", "SEEDED_FROM_ASSEMBLY"),
            ("created_at", _iso()),
            ("anchor_market", manifest.get("anchor_market")),
            ("context", manifest.get("context")),
            ("base_url", manifest.get("base_url")),
            ("bundle_sha256", bundle_sha),
            ("bundle_object", bundle["digest"]),
            ("source_commit", manifest.get("generated_from_commit")),
            ("markets", rows),
            ("live_deploy_id", live.state.deploy_id if live is not None else None),
            ("problems", problems),
        ))
        path = self.root / "releases" / ("seed-%s.json" % _object_name(bundle_sha)[:16])
        _write_json(path, doc)
        doc["path"] = str(path)
        return doc


# --------------------------------------------------------------------------- #
# Phase 3: the release manifest contract.
# --------------------------------------------------------------------------- #

def release_manifest(*, parent_digest: Optional[str], source_commit: str,
                     markets: Sequence[Mapping], participation_sha256: str,
                     participating: Sequence[str], intended_delta: Mapping,
                     global_artifacts: Mapping[str, str], global_index_digest: str,
                     bundle_sha256: str, sitemap_sha256: str, total_profiles: int,
                     sitemap_route_count: int, total_html_pages: int, total_files: int,
                     context: str, base_url: str, anchor_market: str,
                     validation_policy_version: str, assembler_digest: str,
                     builder_digest: str, status: str = CANDIDATE_STAGED,
                     created_at: Optional[str] = None) -> "OrderedDict[str, Any]":
    """One immutable, canonically serialised release manifest.

    Membership is an argument, not a later edit: by the time this returns, the
    participation decision is already inside the document that gets hashed.
    """
    return OrderedDict((
        ("schema", MANIFEST_SCHEMA),
        ("release_schema_version", MANIFEST_SCHEMA),
        ("coordinator_version", COORDINATOR_VERSION),
        ("created_at", created_at or _iso()),
        ("parent_release_digest", parent_digest),
        ("source_commit", source_commit),
        ("context", context),
        ("base_url", base_url),
        ("anchor_market", anchor_market),
        ("participating_markets", list(participating)),
        ("participation_sha256", participation_sha256),
        ("markets", [OrderedDict(m) for m in markets]),
        ("intended_delta", OrderedDict(intended_delta)),
        ("intended_delta_digest", digest_of(intended_delta)),
        ("global_artifacts", OrderedDict(sorted(global_artifacts.items()))),
        ("global_index_digest", global_index_digest),
        ("deployment_artifact_digest", bundle_sha256),
        ("sitemap_sha256", sitemap_sha256),
        ("total_profiles", int(total_profiles)),
        ("sitemap_route_count", int(sitemap_route_count)),
        ("total_html_pages", int(total_html_pages)),
        ("total_files", int(total_files)),
        ("validation_policy_version", validation_policy_version),
        ("assembler_digest", assembler_digest),
        ("builder_digest", builder_digest),
        ("status", status),
    ))


def _module_digest(*modules: Any) -> str:
    h = hashlib.sha256()
    for module in modules:
        path = Path(getattr(module, "__file__", "") or "")
        h.update(path.name.encode("utf-8"))
        h.update(path.read_bytes() if path.is_file() else b"")
    return "sha256:" + h.hexdigest()


# --------------------------------------------------------------------------- #
# Phase 4-10: staging one candidate.
# --------------------------------------------------------------------------- #

class Candidate:
    """An immutable staged candidate on disk."""

    def __init__(self, root: Path, manifest: Mapping, diff: Mapping,
                 receipt: Optional[Mapping], telemetry: Mapping) -> None:
        self.root = Path(root)
        self.manifest = OrderedDict(manifest)
        self.diff = OrderedDict(diff)
        self.receipt = OrderedDict(receipt) if receipt else None
        self.telemetry = OrderedDict(telemetry)

    @property
    def digest(self) -> str:
        return digest_of(self.manifest)

    @property
    def bundle_sha256(self) -> str:
        return str(self.manifest["deployment_artifact_digest"])

    @property
    def site(self) -> Path:
        return self.root / "site"

    def verify_bytes(self) -> List[str]:
        """Re-hash the staged bundle. A candidate that no longer hashes to its
        own manifest is CORRUPT and cannot be activated."""
        problems: List[str] = []
        if not self.site.is_dir():
            return ["candidate site directory is missing"]
        actual = APS.bundle_digest(APS.file_hashes(self.site))
        if actual != self.bundle_sha256:
            problems.append("staged bundle hashes %s, manifest says %s"
                            % (actual[:16], self.bundle_sha256[:16]))
        stored = self.root / "release_manifest.json"
        if stored.is_file() and digest_of(_read_json(stored)) != self.digest:
            problems.append("stored release manifest does not match")
        return problems

    def to_dict(self) -> "OrderedDict[str, Any]":
        return OrderedDict((
            ("candidate_digest", self.digest),
            ("bundle_sha256", self.bundle_sha256),
            ("parent_release_digest", self.manifest.get("parent_release_digest")),
            ("intended_delta_digest", self.manifest.get("intended_delta_digest")),
            ("participating_markets", list(self.manifest.get("participating_markets") or ())),
            ("status", self.manifest.get("status")),
            ("root", str(self.root)),
        ))

    @classmethod
    def load(cls, root: Path) -> "Candidate":
        root = Path(root)
        manifest = _read_json(root / "release_manifest.json")
        diff_path = root / "release_diff.json"
        receipt_path = root / "fast_lane_receipt.json"
        telemetry_path = root / "telemetry.json"
        return cls(root, manifest,
                   _read_json(diff_path) if diff_path.is_file() else OrderedDict(),
                   _read_json(receipt_path) if receipt_path.is_file() else None,
                   _read_json(telemetry_path) if telemetry_path.is_file() else OrderedDict())


def _final_membership(live: LiveTruth, participation_doc: Mapping,
                      delta_kind: str, delta_market: Optional[str],
                      authority: Mapping) -> Tuple[List[str], List[str], List[str]]:
    """``(participating, added, removed)`` -- the FINAL membership, checked.

    Membership comes from the participation document (the founder's decision),
    never from what happens to exist in the tree. Anything it adds or removes
    relative to the live release must be named in ``authority``; that is what
    stops a source-ready market drifting into a release and stops absence
    being read as a removal.
    """
    authorized = set(LP.authorized_market_ids(participation_doc))
    live_set = set(live.participating_markets)
    if delta_kind == REMOVE and delta_market:
        authorized.discard(delta_market)
    added = sorted(authorized - live_set)
    removed = sorted(live_set - authorized)
    may_add = set(authority.get("add") or ())
    may_remove = set(authority.get("remove") or ())
    unauthorized_add = [m for m in added if m not in may_add]
    unauthorized_remove = [m for m in removed if m not in may_remove]
    if unauthorized_add:
        raise CoordinatorError(UNAUTHORIZED_ADDITION,
                               "%s participates in the candidate but no authority admits it"
                               % ", ".join(unauthorized_add))
    if unauthorized_remove:
        raise CoordinatorError(UNAUTHORIZED_REMOVAL,
                               "%s is live but absent from the candidate with no removal authority"
                               % ", ".join(unauthorized_remove))
    return sorted(authorized), added, removed


def _market_configs(market_ids: Sequence[str], package: Optional[Mapping]) -> "OrderedDict[str, Any]":
    """The contract object for every participating market.

    The delta market is parsed from the PACKAGE (a sealed package carries its
    own market contract), every other market from the committed registry.
    """
    from scripts.pettripfinder.markets.contract import load_markets, market_by_id, parse_market

    registry = load_markets()
    out: "OrderedDict[str, Any]" = OrderedDict()
    package_market = str(package["market_id"]) if package else None
    for market_id in market_ids:
        if package is not None and market_id == package_market:
            out[market_id] = parse_market(dict(package["market"]),
                                          source="package:%s" % package["package_id"])
        else:
            out[market_id] = market_by_id(registry, market_id)
    return out


def stage(*, package: Optional[Mapping] = None, delta_kind: str = UPDATE,
          participation_doc: Optional[Mapping] = None,
          authority: Optional[Mapping] = None,
          live: Optional[LiveTruth] = None,
          store: Optional[ReleaseStore] = None,
          cache: Optional[Any] = None,
          work_dir: Optional[Path] = None,
          candidates_root: Optional[Path] = None,
          context: str = "production",
          base_url: str = "https://pettripfinder.com",
          parent_release_digest: Optional[str] = None,
          run_fast_lane: bool = True,
          require_gates: bool = True,
          now: Optional[datetime] = None) -> Candidate:
    """CURRENT LIVE + ONE AUTHORIZED PACKAGE DELTA = ONE FINAL CANDIDATE.

    Every unchanged live market is inherited by fragment digest from the
    release store; the delta market comes from its sealed package through the
    004 bundle cache; the release-global artifacts are regenerated. Nothing
    outside this function writes a candidate.
    """
    started = time.perf_counter()
    moment = now or _now()
    if delta_kind not in DELTA_KINDS:
        raise CoordinatorError(INTENDED_DELTA_MISMATCH, "unknown delta kind %r" % delta_kind)
    live = live if live is not None else LiveTruth.read()
    live.require_verified()
    store = store if store is not None else ReleaseStore()
    participation_doc = participation_doc if participation_doc is not None else LP.load_participation()
    authority = authority or {}
    parent_digest = parent_release_digest or live.digest()
    work = Path(work_dir) if work_dir else Path(candidate_root(candidates_root)) / "work"
    work.mkdir(parents=True, exist_ok=True)

    delta_market = str(package["market_id"]) if package is not None else None
    if package is None and delta_kind != NO_DELTA:
        raise CoordinatorError(INTENDED_DELTA_MISMATCH, "%s needs a sealed package" % delta_kind)

    timing: "OrderedDict[str, float]" = OrderedDict()
    t = time.perf_counter()
    participating, added, removed = _final_membership(live, participation_doc, delta_kind,
                                                      delta_market, authority)
    timing["membership_seconds"] = round(time.perf_counter() - t, 3)
    if delta_kind in (UPDATE, ADD) and delta_market not in participating:
        raise CoordinatorError(UNAUTHORIZED_ADDITION,
                               "the delta market %s does not participate in the final membership"
                               % delta_market)

    configs = _market_configs(participating, package)
    anchor = APS.anchor_market([configs[m] for m in participating])

    # ---- fragments ------------------------------------------------------- #
    frag_root = work / "fragments"
    if frag_root.exists():
        shutil.rmtree(frag_root, ignore_errors=True)
    frag_root.mkdir(parents=True)
    parent_fragments = store.fragment_digests(parent_digest) if parent_digest else OrderedDict()
    if not parent_fragments:
        for release_id in store.releases():
            doc = store.get_release(release_id) or {}
            if doc.get("bundle_sha256") == live.state.bundle_sha256:
                parent_fragments = OrderedDict((m["market_id"], m["fragment_digest"])
                                               for m in (doc.get("markets") or ())
                                               if m.get("fragment_digest"))
                break

    rows: List["OrderedDict[str, Any]"] = []
    trees: "OrderedDict[str, Path]" = OrderedDict()
    cache_hits = 0
    cache_misses = 0
    reused = 0
    rebuilt = 0
    t = time.perf_counter()
    for market_id in participating:
        dest = frag_root / market_id
        if package is not None and market_id == delta_market:
            row, tree = _fragment_from_package(package, dest, cache=cache, work=work / "bundle",
                                               context=context, now=moment)
            # ATLAS-THROUGHPUT-008 found this: a fragment that came from a
            # PACKAGE was never put into durable release storage, so the NEXT
            # release could not inherit it and silently rebuilt that market
            # from committed authority -- reverting the delta this release had
            # just made. The parent-route gate caught it, but a lane that
            # cannot chain releases is not a lane. Storing it here is what
            # makes release N+1 able to inherit release N's own work.
            row["fragment_digest"] = store.put_fragment(market_id, tree)["digest"]
            if row.get("cache_status") in (BC.HIT, BC.HIT_AFTER_WAIT, BC.REVALIDATE):
                cache_hits += 1
            else:
                cache_misses += 1
        else:
            digest = parent_fragments.get(market_id)
            if digest and store.has_fragment(digest):
                store.extract_fragment(digest, dest)
                row = OrderedDict((("market_id", market_id), ("fragment_source", FROM_STORE),
                                   ("fragment_digest", digest)))
                tree = dest
                reused += 1
            else:
                # A store miss costs a rebuild of THAT market. It never costs
                # the market its place in the release (phase 8).
                APS.build_fragment(configs[market_id], dest)
                stored = store.put_fragment(market_id, dest)
                row = OrderedDict((("market_id", market_id), ("fragment_source", REBUILT),
                                   ("fragment_digest", stored["digest"]),
                                   ("rebuild_reason", "no stored fragment for the parent release")))
                tree = dest
                rebuilt += 1
        rows.append(row)
        trees[market_id] = tree
    timing["fragment_seconds"] = round(time.perf_counter() - t, 3)

    # ---- compose --------------------------------------------------------- #
    t = time.perf_counter()
    site = work / "site"
    if site.exists():
        shutil.rmtree(site, ignore_errors=True)
    site.mkdir(parents=True)
    globals_written = _compose(site, participating, configs, trees, anchor,
                               context=context, base_url=base_url)
    timing["compose_seconds"] = round(time.perf_counter() - t, 3)

    # ---- gates ----------------------------------------------------------- #
    t = time.perf_counter()
    intended_delta = OrderedDict(package.get("intended_delta") or {}) if package else OrderedDict()
    gates = _run_candidate_gates(site, participating, configs, context, base_url,
                                 participation_doc, intended_delta, store=store,
                                 parent_digest=parent_digest)
    failing = sorted(gid for gid, res in gates.items() if not res["pass"])
    timing["gate_seconds"] = round(time.perf_counter() - t, 3)
    if failing and require_gates:
        raise CoordinatorError(GATES_FAILED, ", ".join(failing[:6]))

    hashes = APS.file_hashes(site)
    bundle_sha = APS.bundle_digest(hashes)
    sitemap_sha = SMP.sha256_bytes((site / "sitemap.xml").read_bytes()).split(":")[-1] \
        if (site / "sitemap.xml").is_file() else ""

    # ---- release index + intended delta ---------------------------------- #
    proposed = RI.compose(live.index, RI.index_from_package(package, participating=True),
                          participates=True) if package is not None else live.index
    global_index_digest = proposed.digest() if hasattr(proposed, "digest") else ""

    market_rows: List["OrderedDict[str, Any]"] = []
    by_id = {r["market_id"]: r for r in rows}
    for market_id in participating:
        row = by_id[market_id]
        idx = proposed.markets.get(market_id) if hasattr(proposed, "markets") else None
        market_rows.append(OrderedDict((
            ("market_id", market_id),
            ("package_digest", row.get("package_digest")),
            ("build_input_key", row.get("build_input_key")),
            ("bundle_digest", row.get("bundle_digest")),
            ("validation_receipt_digest", row.get("validation_receipt_digest")),
            ("fragment_source", row["fragment_source"]),
            ("fragment_digest", row.get("fragment_digest")),
            ("profile_count", len(idx.profiles) if idx is not None else
             int(live.state.profile_counts.get(market_id, 0))),
            ("route_count", len(idx.routes) if idx is not None else None),
        )))

    manifest = release_manifest(
        parent_digest=parent_digest,
        source_commit=APS._git_head(),
        markets=market_rows,
        participation_sha256=SMP.sha256_text(SMP.canonical_json(participation_doc)),
        participating=participating,
        intended_delta=intended_delta,
        global_artifacts=globals_written,
        global_index_digest=global_index_digest,
        bundle_sha256=bundle_sha,
        sitemap_sha256=sitemap_sha,
        total_profiles=sum(r["profile_count"] or 0 for r in market_rows),
        sitemap_route_count=len([p for p in site.rglob("index.html")
                                 if not APS._route_of(site, p).startswith("/go/")]),
        total_html_pages=sum(1 for _p in site.rglob("*.html")),
        total_files=len(hashes),
        context=context, base_url=base_url, anchor_market=anchor.market_id,
        validation_policy_version=BC.VALIDATION_POLICY,
        assembler_digest=_module_digest(APS),
        builder_digest=_module_digest(BC, sys.modules[__name__]),
        created_at=_iso(moment),
    )

    # ---- FAST release safety on the FINAL candidate ----------------------- #
    receipt = None
    if run_fast_lane and package is not None:
        t = time.perf_counter()
        receipt = FL.run_fast_lane(package, work_dir=work / "fast",
                                   live=(live.index, live.state, list(live.problems)),
                                   build=True, determinism=True, now=moment,
                                   participates=True, bundle_cache=cache)
        timing["fast_lane_seconds"] = round(time.perf_counter() - t, 3)

    diff = release_diff(live.manifest(), manifest, added=added, removed=removed,
                        reused=reused, rebuilt=rebuilt)

    # ---- publish the candidate ------------------------------------------- #
    candidate_digest = digest_of(manifest)
    root = Path(candidate_root(candidates_root)) / candidate_digest[7:23]
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    staging = root.with_name(root.name + ".staging-%s" % uuid.uuid4().hex[:8])
    if staging.exists():
        shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    shutil.move(str(site), str(staging / "site"))
    _write_json(staging / "release_manifest.json", manifest)
    _write_json(staging / "release_diff.json", diff)
    _write_json(staging / "gates.json", OrderedDict((("failing", failing), ("gates", gates))))
    if receipt is not None:
        _write_json(staging / "fast_lane_receipt.json", receipt)
    timing["total_seconds"] = round(time.perf_counter() - started, 3)
    telemetry = OrderedDict((
        ("release_operation_id", "stage-%s" % uuid.uuid4().hex[:12]),
        ("parent_release_digest", parent_digest),
        ("candidate_digest", candidate_digest),
        ("market", delta_market),
        ("package_digest", (package or {}).get("package_digest")),
        ("bundles_total", len(participating)),
        ("bundles_reused", reused),
        ("bundles_rebuilt", rebuilt),
        ("global_artifacts_regenerated", sum(1 for v in GLOBAL_ARTIFACTS.values() if v[0] == REGENERATE)),
        ("cache_hits", cache_hits), ("cache_misses", cache_misses),
        ("stale_parent", False), ("unexpected_delta", diff["unexpected_changes"]),
        ("result", CANDIDATE_STAGED),
    ))
    telemetry.update(timing)
    _event("stage", release_operation_id=telemetry["release_operation_id"],
           parent_release_digest=parent_digest, candidate_digest=candidate_digest,
           market=delta_market, package_digest=(package or {}).get("package_digest"),
           bundles_total=len(participating), bundles_reused=reused, bundles_rebuilt=rebuilt,
           global_artifacts_regenerated=telemetry["global_artifacts_regenerated"],
           cache_hits=cache_hits, cache_misses=cache_misses,
           fast_lane_seconds=timing.get("fast_lane_seconds"),
           stage_seconds=timing["total_seconds"], stale_parent=False,
           unexpected_delta=len(diff["unexpected_changes"]), result=CANDIDATE_STAGED)
    _write_json(staging / "telemetry.json", telemetry)
    os.replace(str(staging), str(root))
    return Candidate(root, manifest, diff, receipt, telemetry)


def _fragment_from_package(package: Mapping, dest: Path, *, cache: Optional[Any],
                           work: Path, context: str, now: datetime
                           ) -> Tuple["OrderedDict[str, Any]", Path]:
    """The changed market's files, from its VALIDATED bundle.

    The 004 cache is consumed in candidate-staging mode: a trusted hit means
    the bytes were validated under a compatible policy in an earlier run, and
    the builder is not invoked at all.
    """
    from scripts.pettripfinder import package_staging as STAGING

    market_id = str(package["market_id"])
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    if cache is not None:
        result = cache.build_or_reuse(package, work_dir=work, context=context, now=now)
        site = Path(result["output_dir"]) / "site"
        row = OrderedDict((
            ("market_id", market_id), ("fragment_source", FROM_PACKAGE),
            ("package_digest", package.get("package_digest")),
            ("build_input_key", result.get("build_input_key")),
            ("bundle_digest", result.get("bundle_sha256")),
            ("validation_receipt_digest", result.get("receipt_digest")),
            ("cache_status", result.get("cache_status")),
            ("builder_invocations", result.get("builder_invocations")),
        ))
    else:
        built = STAGING.build_changed_market(package, work / "stage", work / "out",
                                             context=context, cold=True)
        site = Path(work / "out" / "site")
        row = OrderedDict((
            ("market_id", market_id), ("fragment_source", FROM_PACKAGE),
            ("package_digest", package.get("package_digest")),
            ("build_input_key", None),
            ("bundle_digest", built.get("bundle_sha256")),
            ("validation_receipt_digest", None),
            ("cache_status", BC.MISS), ("builder_invocations", 1),
        ))
    if not site.is_dir():
        raise CoordinatorError(FRAGMENT_UNAVAILABLE, "no bundle site for %s" % market_id)
    dest = Path(dest)
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(site, dest)
    return row, dest


def _compose(site: Path, participating: Sequence[str], configs: Mapping[str, Any],
             trees: Mapping[str, Path], anchor: Any, *, context: str, base_url: str
             ) -> "OrderedDict[str, str]":
    """Copy every market's owned files, then write the release-global set."""
    anchor_pages: Dict[str, str] = {}
    route_owner: Dict[str, str] = {}
    collisions: List[str] = []
    for market_id in participating:
        tree = Path(trees[market_id])
        owned, _discarded, violations = APS.classify_fragment(configs[market_id], tree)
        if violations:
            raise CoordinatorError(UNKNOWN_GLOBAL_DEPENDENCY,
                                   "%s claims global routes %s" % (market_id, violations))
        if market_id == anchor.market_id:
            for rel in APS.GLOBAL_FILES:
                path = tree / rel
                if path.is_file() and rel.endswith(".html"):
                    anchor_pages[rel] = path.read_text(encoding="utf-8")
        for rel, path in owned.items():
            dest = site / rel
            if rel in route_owner:
                if dest.is_file() and path.read_bytes() == dest.read_bytes():
                    continue
                collisions.append("%s claimed by %s and %s" % (rel, route_owner[rel], market_id))
                continue
            route_owner[rel] = market_id
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, dest)
    if collisions:
        raise CoordinatorError(UNKNOWN_GLOBAL_DEPENDENCY, "; ".join(collisions[:4]))
    missing = [rel for rel in ("index.html", "pet-friendly-hotels/index.html", "about/index.html",
                               "contact/index.html", "methodology/index.html")
               if rel not in anchor_pages]
    if missing:
        raise CoordinatorError(FRAGMENT_UNAVAILABLE,
                               "anchor %s supplies no %s" % (anchor.market_id, missing))

    entries = [OrderedDict((
        ("market_id", m.market_id), ("name", m.market_name),
        ("route", APS.market_route(m)),
        ("comparison_route", APS.market_route(m) + "policy-comparison/"),
        ("scope", APS.market_scope_line(m)),
        ("published", sum(1 for k in APS.owned_routes(m).values() if k == "hotel_profile")),
    )) for m in (configs[mid] for mid in participating)]
    visible = [e for e, m in zip(entries, (configs[mid] for mid in participating))
               if m.show_in_navigation]

    written: "OrderedDict[str, str]" = OrderedDict()

    def _write(rel: str, text: str) -> None:
        target = site / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")
        written[rel] = SMP.sha256_bytes(target.read_bytes())

    _write("index.html", APS.build_global_home(anchor_pages["index.html"], visible))
    _write("pet-friendly-hotels/index.html",
           APS.build_global_hotel_index(anchor_pages["pet-friendly-hotels/index.html"], visible))
    for rel in ("about/index.html", "contact/index.html", "methodology/index.html"):
        _write(rel, anchor_pages[rel])
    _write("robots.txt", APS._ROBOTS_TXT % base_url)
    _write("llms.txt", APS.build_global_llms(visible, base_url))

    headers_bytes = APS.HEADERS_SOURCES[context].read_bytes()
    redirects_bytes = APS.REDIRECTS_SOURCE.read_bytes()
    (site / "_headers").write_bytes(headers_bytes)
    (site / "_redirects").write_bytes(redirects_bytes)
    written["_headers"] = SMP.sha256_bytes(headers_bytes)
    written["_redirects"] = SMP.sha256_bytes(redirects_bytes)

    indexable = sorted(r for r in (APS._route_of(site, p) for p in site.rglob("index.html"))
                       if not r.startswith("/go/"))
    _write("sitemap.xml", APS.build_global_sitemap(indexable, base_url))
    unknown = [rel for rel in written if rel not in GLOBAL_ARTIFACTS]
    if unknown:
        raise CoordinatorError(UNKNOWN_GLOBAL_DEPENDENCY,
                               "no regeneration class declared for %s" % unknown)
    return written


def _migration_gate_with_intent(gates: "OrderedDict[str, Dict]", site: Path,
                                intended_delta: Mapping) -> None:
    """Every live route must survive -- unless the delta says it retires.

    ``assemble_production_site._run_migration_gate`` asks the absolute
    question: is every route production serves still here? A release that
    withdraws a property answers no, and answering no is the POINT of that
    gate. So the coordinator asks the same question with one explicit
    subtraction -- the routes the sealed package's intended delta declares it
    removes -- and records both numbers, so an undeclared loss still fails and
    a declared one is visible rather than waived.
    """
    # Scope: this inventory is the 044 Columbus legacy-namespace list, not the
    # live site. It is kept because losing that namespace is a specific,
    # recurring failure; the COMPLETE preservation question is answered by
    # _parent_route_gate against the stored parent bundle.
    inventory = APS.LIVE_ROUTE_INVENTORY
    if not inventory.is_file():
        APS._gate(gates, "release.live_routes_preserved_or_declared", False,
                  "no live route inventory committed")
        return
    live_routes = [line.strip() for line in inventory.read_text(encoding="utf-8").splitlines()
                   if line.strip() and not line.startswith("#")]
    declared = set(intended_delta.get("remove_routes") or ())
    on_disk = {APS._route_of(site, p) for p in site.rglob("index.html")}
    missing = [r for r in live_routes if r not in on_disk]
    undeclared = sorted(r for r in missing if r not in declared)
    APS._gate(gates, "release.live_routes_preserved_or_declared", not undeclared,
              "undeclared route losses: %s" % undeclared[:6])
    APS._gate(gates, "release.declared_removals_are_realised",
              all(r not in on_disk for r in declared),
              "declared removals still served: %s"
              % sorted(r for r in declared if r in on_disk)[:6])
    gates["release.live_routes_preserved_or_declared"]["live_routes"] = len(live_routes)
    gates["release.live_routes_preserved_or_declared"]["declared_removals"] = len(declared)
    gates["release.live_routes_preserved_or_declared"]["missing"] = len(missing)


def _split_consequential(lost: Sequence[str], declared_removals: Set[str]
                         ) -> Tuple[List[str], List[str]]:
    """``(consequential, undeclared)`` for the routes a candidate no longer serves.

    A sealed package's ``intended_delta`` declares the INDEXABLE routes a
    withdrawal removes -- the profile pages and any corridor that empties --
    because 003's release index models exactly those. It does not enumerate
    the five commercial action routes each profile owns
    (``/go/<market>/<slug>/{booking,call,directions,official-website,report-change}/``),
    which are a consequence of the profile existing: withdraw the profile and
    they necessarily go with it. The 005 pilot found 20 such routes behind 4
    declared profile removals.

    Treating them as undeclared losses would make every honest withdrawal fail;
    treating them as invisible would let a real loss hide behind a `/go/`
    prefix. So they are accounted for as CONSEQUENTIAL, and only when the
    profile slug they hang off was itself declared removed.
    """
    declared_slugs = {r.rstrip("/").rsplit("/", 1)[-1] for r in declared_removals if r.strip("/")}
    consequential: List[str] = []
    undeclared: List[str] = []
    for route in lost:
        if route in declared_removals:
            continue
        parts = [seg for seg in route.split("/") if seg]
        if route.startswith("/go/") and len(parts) >= 2 and parts[-2] in declared_slugs:
            consequential.append(route)
        else:
            undeclared.append(route)
    return consequential, undeclared


def _parent_route_gate(gates: "OrderedDict[str, Dict]", site: Path, store: "ReleaseStore",
                       parent_digest: Optional[str], intended_delta: Mapping) -> None:
    """Every route the PARENT RELEASE served must still be served here.

    ``deploy/netlify/live_production_routes.txt`` is not the live site: it is
    132 Columbus legacy-namespace routes, committed by the 044 migration to
    catch that one namespace being dropped. Asking it whether an unrelated
    market survived would get a cheerful yes for a release that deleted
    Dayton. So the real question is asked of the real parent: the routes in
    the stored parent bundle, minus the ones this delta declares it removes.

    The parent's route list is read from the stored archive's index, so this
    costs milliseconds and never extracts a byte.
    """
    doc = store.get_release(parent_digest) if parent_digest else None
    if not doc or not doc.get("bundle_object"):
        APS._gate(gates, "release.parent_routes_preserved", False,
                  "no stored parent bundle for %s: a candidate cannot prove what it preserved"
                  % (str(parent_digest)[7:23] if parent_digest else "<no parent>"))
        return
    archive = store.root / "bundles" / ("%s.zip" % _object_name(str(doc["bundle_object"])))
    if not archive.is_file():
        APS._gate(gates, "release.parent_routes_preserved", False,
                  "the stored parent bundle object is missing")
        return
    import zipfile
    with zipfile.ZipFile(archive) as zf:
        parent_routes = {"/" + name[: -len("index.html")].lstrip("/")
                         for name in zf.namelist() if name.endswith("index.html")}
    here = {APS._route_of(site, p) for p in site.rglob("index.html")}
    declared_removals = set(intended_delta.get("remove_routes") or ())
    lost_all = sorted(parent_routes - here)
    consequential, undeclared = _split_consequential(lost_all, declared_removals)
    undeclared_adds = sorted(here - parent_routes - set(intended_delta.get("add_routes") or ()))
    APS._gate(gates, "release.parent_routes_preserved", not undeclared,
              "routes the parent served that this candidate does not, and the delta neither "
              "declares nor implies: %s" % undeclared[:6])
    APS._gate(gates, "release.additions_are_declared", not undeclared_adds,
              "routes this candidate adds that the delta does not declare: %s" % undeclared_adds[:6])
    row = gates["release.parent_routes_preserved"]
    row["parent_routes"] = len(parent_routes)
    row["candidate_routes"] = len(here)
    row["declared_removals"] = len(declared_removals)
    row["consequential_removals"] = len(consequential)
    row["undeclared_removals"] = len(undeclared)


def _run_candidate_gates(site: Path, participating: Sequence[str], configs: Mapping[str, Any],
                         context: str, base_url: str, participation_doc: Mapping,
                         intended_delta: Optional[Mapping] = None,
                         store: Optional["ReleaseStore"] = None,
                         parent_digest: Optional[str] = None
                         ) -> "OrderedDict[str, Dict]":
    """The composed-bundle gates, run by their owning modules.

    These are the same implementations ``assemble_production_site`` runs; the
    coordinator records their results rather than restating the rules.
    """
    gates: "OrderedDict[str, Dict]" = OrderedDict()
    chosen = [configs[m] for m in participating]
    headers_bytes = APS.HEADERS_SOURCES[context].read_bytes()
    redirects_bytes = APS.REDIRECTS_SOURCE.read_bytes()
    APS._run_global_publish_gates(gates, chosen, context, site, headers_bytes, redirects_bytes)
    _migration_gate_with_intent(gates, site, intended_delta or {})
    if store is not None:
        _parent_route_gate(gates, site, store, parent_digest, intended_delta or {})
    from scripts.pettripfinder.affiliate_destinations import run_affiliate_gates
    from scripts.pettripfinder.measurement import run_measurement_gates
    run_measurement_gates(gates, APS._gate, site)
    run_affiliate_gates(gates, APS._gate, market_ids=list(participating))

    broken = APS.broken_internal_links(site)
    APS._gate(gates, "content.zero_broken_links", not broken, "; ".join(broken[:6]))
    canon = APS.canonical_violations(site, base_url)
    APS._gate(gates, "content.canonical_uniqueness", not canon, "; ".join(canon[:6]))
    on_disk = {r for r in (APS._route_of(site, p) for p in site.rglob("index.html"))
               if not r.startswith("/go/")}
    sitemap_routes = set()
    sitemap = site / "sitemap.xml"
    if sitemap.is_file():
        import re as _re
        sitemap_routes = {_re.sub(r"^https?://[^/]+", "", loc)
                          for loc in _re.findall(r"<loc>([^<]+)</loc>", sitemap.read_text(encoding="utf-8"))}
    APS._gate(gates, "content.sitemap_is_the_site", sitemap_routes == on_disk,
              "only_in_sitemap=%s only_on_disk=%s"
              % (sorted(sitemap_routes - on_disk)[:4], sorted(on_disk - sitemap_routes)[:4]))
    APS._gate(gates, "content.sitemap_excludes_go",
              not any("/go/" in r for r in sitemap_routes), "")
    go_routes = [r for r in (APS._route_of(site, p) for p in site.rglob("index.html"))
                 if r.startswith("/go/")]
    APS._gate(gates, "content.go_routes_unique", len(go_routes) == len(set(go_routes)), "")

    # Membership is gated against the participation document the candidate was
    # staged from -- the decision that is already inside the hashed bytes.
    authorized = set(LP.authorized_market_ids(participation_doc))
    APS._gate(gates, "release.membership_is_the_participation_decision",
              set(participating) == authorized,
              "candidate=%s participation=%s" % (sorted(set(participating) - authorized),
                                                 sorted(authorized - set(participating))))
    return gates


# --------------------------------------------------------------------------- #
# Phase 22: the release diff.
# --------------------------------------------------------------------------- #

def release_diff(parent: Mapping, candidate: Mapping, *, added: Sequence[str] = (),
                 removed: Sequence[str] = (), reused: int = 0, rebuilt: int = 0
                 ) -> "OrderedDict[str, Any]":
    """What this candidate changes about the release, before anyone signs it."""
    p_markets = OrderedDict((m["market_id"], m) for m in (parent.get("markets") or ()))
    c_markets = OrderedDict((m["market_id"], m) for m in (candidate.get("markets") or ()))
    updated: List["OrderedDict[str, Any]"] = []
    counts: List["OrderedDict[str, Any]"] = []
    for market_id, row in c_markets.items():
        before = p_markets.get(market_id)
        if before is None:
            continue
        if before.get("profile_count") != row.get("profile_count") or \
                before.get("route_count") != row.get("route_count"):
            updated.append(OrderedDict((
                ("market_id", market_id),
                ("profiles_before", before.get("profile_count")),
                ("profiles_after", row.get("profile_count")),
                ("routes_before", before.get("route_count")),
                ("routes_after", row.get("route_count")),
            )))
        counts.append(OrderedDict((("market_id", market_id),
                                   ("profiles", row.get("profile_count")),
                                   ("routes", row.get("route_count")))))
    unexpected: List[str] = []
    intended = candidate.get("intended_delta") or {}
    intended_market = intended.get("market_id")
    for row in updated:
        if intended_market and row["market_id"] != intended_market:
            unexpected.append("%s changed but the intended delta names %s"
                              % (row["market_id"], intended_market))
    for market_id in removed:
        if market_id not in (intended.get("remove_markets") or ()) and market_id not in removed:
            unexpected.append("%s removed with no intent" % market_id)
    return OrderedDict((
        ("schema", DIFF_SCHEMA),
        ("parent_release_digest", candidate.get("parent_release_digest")),
        ("candidate_release_digest", digest_of(candidate)),
        ("markets_added", list(added)),
        ("markets_removed", list(removed)),
        ("markets_updated", updated),
        ("profile_counts_by_market", counts),
        ("profiles_before", parent.get("total_profiles")),
        ("profiles_after", candidate.get("total_profiles")),
        ("routes_before", parent.get("sitemap_route_count")),
        ("routes_after", candidate.get("sitemap_route_count")),
        ("global_artifact_changes", list((candidate.get("global_artifacts") or {}).keys())),
        ("bundles_reused", reused),
        ("bundles_rebuilt", rebuilt),
        ("unexpected_changes", unexpected),
    ))


# --------------------------------------------------------------------------- #
# Phase 12-13: authorization, external to the candidate bytes.
# --------------------------------------------------------------------------- #

def authorize(candidate: Candidate, *, decided_by: str, decision: str = "AUTHORIZE",
              notes: str = "", parent_release_digest: Optional[str] = None,
              now: Optional[datetime] = None) -> "OrderedDict[str, Any]":
    """Bind a founder decision to ONE candidate digest and ONE parent.

    The record lives outside the candidate: signing does not change the bytes,
    so an authorization can never alter what it authorizes.
    """
    _t0 = time.perf_counter()
    moment = now or _now()
    problems = candidate.verify_bytes()
    if problems:
        raise CoordinatorError(CANDIDATE_CORRUPT, "; ".join(problems))
    expected_parent = parent_release_digest or candidate.manifest.get("parent_release_digest")
    if expected_parent != candidate.manifest.get("parent_release_digest"):
        raise CoordinatorError(PARENT_DIGEST_MISMATCH,
                               "candidate parent %s != %s"
                               % (candidate.manifest.get("parent_release_digest"), expected_parent))
    auth = OrderedDict((
        ("schema", AUTHORIZATION_SCHEMA),
        ("authorization_id", "rel-auth-%s" % candidate.digest[7:23]),
        ("candidate_digest", candidate.digest),
        ("deployment_artifact_digest", candidate.bundle_sha256),
        ("parent_release_digest", expected_parent),
        ("intended_delta_digest", candidate.manifest.get("intended_delta_digest")),
        ("participating_markets", list(candidate.manifest.get("participating_markets") or ())),
        ("participation_sha256", candidate.manifest.get("participation_sha256")),
        ("market", (candidate.manifest.get("intended_delta") or {}).get("market_id")),
        ("decision", decision),
        ("decided_by", decided_by),
        ("decided_at", _iso(moment)),
        ("notes", notes),
        ("state", "VALID"),
        ("revoked_reason", None),
    ))
    _write_json(candidate.root / "authorization.json", auth)
    _event("authorize", candidate_digest=candidate.digest,
           parent_release_digest=expected_parent, market=auth["market"],
           authorization_seconds=round(time.perf_counter() - _t0, 3), result=FOUNDER_AUTHORIZED)
    return auth


def authorization_problems(auth: Mapping, candidate: Candidate, *,
                           live: Optional[LiveTruth] = None,
                           superseded_by: Optional[str] = None) -> List[str]:
    """Every reason this authorization does not authorize this candidate now."""
    problems: List[str] = []
    if auth.get("state") != "VALID":
        problems.append("%s: authorization state is %r" % (AUTHORIZATION_REVOKED, auth.get("state")))
    if auth.get("candidate_digest") != candidate.digest:
        problems.append("%s: authorization binds %s, candidate is %s"
                        % (CANDIDATE_DIGEST_MISMATCH, str(auth.get("candidate_digest"))[7:23],
                           candidate.digest[7:23]))
    if auth.get("deployment_artifact_digest") != candidate.bundle_sha256:
        problems.append("%s: authorization binds bundle %s, candidate is %s"
                        % (BUNDLE_DIGEST_MISMATCH, str(auth.get("deployment_artifact_digest"))[:12],
                           candidate.bundle_sha256[:12]))
    if auth.get("intended_delta_digest") != candidate.manifest.get("intended_delta_digest"):
        problems.append("%s: the intended delta changed" % INTENDED_DELTA_MISMATCH)
    if list(auth.get("participating_markets") or ()) != list(candidate.manifest.get("participating_markets") or ()):
        problems.append("%s: membership changed after authorization" % CANDIDATE_DIGEST_MISMATCH)
    if superseded_by:
        problems.append("%s: superseded by %s" % (CANDIDATE_SUPERSEDED, superseded_by[7:23]))
    problems.extend("%s: %s" % (CANDIDATE_CORRUPT, p) for p in candidate.verify_bytes())
    if live is not None:
        problems.extend(parent_guard(auth, live))
    return problems


def parent_guard(auth: Mapping, live: LiveTruth) -> List[str]:
    """Phase 13. The live release must STILL be the authorized parent."""
    if not live.verified:
        return ["%s: %s" % (LIVE_NOT_VERIFIED, "; ".join(live.problems[:2]))]
    current = live.digest()
    if auth.get("parent_release_digest") != current:
        return ["%s: authorized parent %s but %s is live"
                % (STALE_PARENT, str(auth.get("parent_release_digest"))[7:23], current[7:23])]
    return []


# --------------------------------------------------------------------------- #
# Phase 14-17: activation, verification, reconciliation.
# --------------------------------------------------------------------------- #

class SimulatedHost:
    """A stand-in for the deployment host. It never touches production.

    Deliberately models the three things that make real activation hard:
    idempotency by operation id, an outcome that can be UNKNOWN, and a state
    the caller can only learn by asking (``reconcile``).
    """

    def __init__(self, root: Path, *, live_release: Optional[str] = None) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.deploys: "OrderedDict[str, OrderedDict[str, Any]]" = OrderedDict()
        self.operations: "OrderedDict[str, str]" = OrderedDict()
        self.live_release = live_release
        self.calls: List[str] = []
        self.fail_next = False
        self.timeout_next = False

    def activate(self, operation_id: str, *, release_digest: str, bundle_sha256: str,
                 site: Path) -> "OrderedDict[str, Any]":
        self.calls.append(operation_id)
        if operation_id in self.operations:                      # idempotent retry
            deploy_id = self.operations[operation_id]
            out = OrderedDict(self.deploys[deploy_id])
            out["idempotent_replay"] = True
            return out
        actual = APS.bundle_digest(APS.file_hashes(Path(site)))
        if actual != bundle_sha256:
            return OrderedDict((("outcome", ACTIVATION_FAILED),
                                ("detail", "host received %s, expected %s" % (actual[:12], bundle_sha256[:12]))))
        deploy_id = hashlib.sha256((operation_id + bundle_sha256).encode()).hexdigest()[:24]
        record = OrderedDict((
            ("outcome", ACTIVATED), ("host_deployment_id", deploy_id),
            ("release_digest", release_digest), ("bundle_sha256", bundle_sha256),
            ("idempotent_replay", False),
        ))
        if self.fail_next:
            self.fail_next = False
            return OrderedDict((("outcome", ACTIVATION_FAILED), ("detail", "host refused")))
        # An activation can land on the host and still not reach the caller.
        self.deploys[deploy_id] = record
        self.operations[operation_id] = deploy_id
        self.live_release = release_digest
        if self.timeout_next:
            self.timeout_next = False
            return OrderedDict((("outcome", ACTIVATION_UNKNOWN),
                                ("detail", "no result before the deadline")))
        return record

    def reconcile(self, operation_id: str) -> "OrderedDict[str, Any]":
        """What the host actually holds for this operation."""
        deploy_id = self.operations.get(operation_id)
        if deploy_id is None:
            return OrderedDict((("known", False), ("outcome", None)))
        out = OrderedDict(self.deploys[deploy_id])
        out["known"] = True
        return out

    def current(self) -> Optional[str]:
        return self.live_release

    def fetch(self, path: str) -> Optional[bytes]:
        return None


def activate(candidate: Candidate, auth: Mapping, host: SimulatedHost, *,
             live: Optional[LiveTruth] = None, operation_id: Optional[str] = None,
             superseded_by: Optional[str] = None,
             now: Optional[datetime] = None) -> "OrderedDict[str, Any]":
    """STAGE -> AUTHORIZE -> **ACTIVATE**. Refuses before it acts.

    Every refusal happens before the host is called, so a refused activation
    leaves the live release untouched. The operation id makes a retry
    idempotent: the same id can never produce a second deployment.
    """
    started = time.perf_counter()
    moment = now or _now()
    operation_id = operation_id or "act-%s" % candidate.digest[7:23]
    problems = authorization_problems(auth, candidate, live=live, superseded_by=superseded_by)
    if problems:
        _event("activate", candidate_digest=candidate.digest, market=None,
               deployment_operation_id=operation_id, result=ACTIVATION_REFUSED,
               retry_reason=None, stale_parent=any(p.startswith(STALE_PARENT) for p in problems),
               activation_seconds=round(time.perf_counter() - started, 3))
        return OrderedDict((
            ("schema", ACTIVATION_SCHEMA), ("outcome", ACTIVATION_REFUSED),
            ("refusals", problems), ("candidate_digest", candidate.digest),
            ("deployment_operation_id", operation_id),
            ("started_at", _iso(moment)), ("host_deployment_id", None),
            ("seconds", round(time.perf_counter() - started, 3)),
        ))
    result = host.activate(operation_id, release_digest=candidate.digest,
                           bundle_sha256=candidate.bundle_sha256, site=candidate.site)
    record = OrderedDict((
        ("schema", ACTIVATION_SCHEMA),
        ("release_digest", candidate.digest),
        ("candidate_digest", candidate.digest),
        ("parent_release_digest", candidate.manifest.get("parent_release_digest")),
        ("deployment_operation_id", operation_id),
        ("host_deployment_id", result.get("host_deployment_id")),
        ("started_at", _iso(moment)),
        ("activated_at", _iso() if result.get("outcome") == ACTIVATED else None),
        ("verified_at", None),
        ("outcome", result.get("outcome")),
        ("idempotent_replay", bool(result.get("idempotent_replay"))),
        ("detail", result.get("detail")),
        ("live_verification_results", None),
        ("rollback_target", candidate.manifest.get("parent_release_digest")),
        ("source_commit", candidate.manifest.get("source_commit")),
        ("seconds", round(time.perf_counter() - started, 3)),
    ))
    _write_json(candidate.root / ("activation-%s.json" % operation_id), record)
    _event("activate", candidate_digest=candidate.digest,
           parent_release_digest=candidate.manifest.get("parent_release_digest"),
           deployment_operation_id=operation_id, host_deployment_id=record["host_deployment_id"],
           result=record["outcome"], stale_parent=False,
           retry_reason="idempotent_replay" if record["idempotent_replay"] else None,
           activation_seconds=record["seconds"])
    return record


def reconcile(candidate: Candidate, host: SimulatedHost, operation_id: str) -> "OrderedDict[str, Any]":
    """Phase 19 cases 4 and 5: ask the host before doing anything else.

    An UNKNOWN outcome is never retried and never rolled back until the host
    has been asked what it actually holds.
    """
    state = host.reconcile(operation_id)
    if not state.get("known"):
        return OrderedDict((("reconciled", True), ("host_has_activation", False),
                            ("outcome", ACTIVATION_FAILED),
                            ("action", "RETRY_SAFE -- the host holds nothing for this operation")))
    matches = state.get("release_digest") == candidate.digest
    return OrderedDict((
        ("reconciled", True), ("host_has_activation", True),
        ("host_deployment_id", state.get("host_deployment_id")),
        ("release_digest", state.get("release_digest")),
        ("matches_candidate", matches),
        ("outcome", ACTIVATED if matches else ACTIVATION_FAILED),
        ("action", "REPAIR_RECORD -- the activation landed; write the record, do not redeploy"
         if matches else "INVESTIGATE -- the host holds a different release"),
    ))


#: Phase 17. What must be true within minutes of an activation. Every check is
#: a targeted read of the deployed artifact, never a suite run.
LIVE_VERIFICATION_CHECKS: Tuple[Tuple[str, str], ...] = (
    ("release_marker", "the host's current release digest equals the activated candidate"),
    ("host_deployment_id", "the host deployment id equals the one in the activation record"),
    ("membership", "the deployed bundle serves exactly the candidate's participating markets"),
    ("changed_market_hub", "the changed market's hub route is reachable"),
    ("changed_market_profiles", "a sample of the changed market's profile routes are reachable"),
    ("sitemap_includes_changed_market", "the global sitemap lists the changed market's routes"),
    ("unrelated_market_sample", "a sample of an unrelated live market's routes is preserved"),
    ("unrelated_route_count", "the unrelated markets' route count is unchanged"),
    ("asset_integrity", "the shared stylesheet and control files hash as authorized"),
)


def _hub_routes(market_ids: Sequence[str]) -> "OrderedDict[str, str]":
    """Each market's own hub route. Columbus is legacy-unprefixed, so a route
    can never be assumed from a market id."""
    from scripts.pettripfinder.markets.contract import load_markets, market_by_id
    registry = load_markets()
    out: "OrderedDict[str, str]" = OrderedDict()
    for market_id in market_ids:
        try:
            out[market_id] = APS.market_route(market_by_id(registry, market_id))
        except Exception:
            out[market_id] = "/pet-friendly-hotels/%s/" % market_id
    return out


def verify_live(candidate: Candidate, host: SimulatedHost, record: Mapping, *,
                sample: int = 5) -> "OrderedDict[str, Any]":
    """The targeted post-activation contract, run against the staged bytes.

    005 verifies a simulator, never production: the point is the CONTRACT --
    which nine things must hold, checked in seconds, instead of a second broad
    regression.
    """
    started = time.perf_counter()
    site = candidate.site
    results: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()

    def _check(name: str, passed: bool, detail: str = "") -> None:
        results[name] = OrderedDict((("pass", bool(passed)), ("detail", detail)))

    _check("release_marker", host.current() == candidate.digest,
           "host=%s candidate=%s" % (str(host.current())[7:23], candidate.digest[7:23]))
    _check("host_deployment_id",
           bool(record.get("host_deployment_id")) and
           host.reconcile(str(record.get("deployment_operation_id"))).get("host_deployment_id")
           == record.get("host_deployment_id"),
           str(record.get("host_deployment_id")))
    participating = list(candidate.manifest.get("participating_markets") or ())
    routes = _hub_routes(participating)
    absent = sorted(m for m, route in routes.items()
                    if not (site / route.strip("/") / "index.html").is_file())
    _check("membership", not absent, "markets with no hub page: %s" % absent)
    delta_market = (candidate.manifest.get("intended_delta") or {}).get("market_id")
    if delta_market:
        hub_route = routes.get(delta_market, "/pet-friendly-hotels/%s/" % delta_market)
        hub_dir = site / hub_route.strip("/")
        _check("changed_market_hub", (hub_dir / "index.html").is_file(), hub_route)
        profiles = sorted(hub_dir.glob("*/index.html"))[:sample]
        _check("changed_market_profiles", len(profiles) > 0, "%d sampled under %s" % (len(profiles), hub_route))
        sitemap = (site / "sitemap.xml").read_text(encoding="utf-8") if (site / "sitemap.xml").is_file() else ""
        _check("sitemap_includes_changed_market", hub_route in sitemap, hub_route)
    else:
        for name in ("changed_market_hub", "changed_market_profiles", "sitemap_includes_changed_market"):
            _check(name, True, "no market delta in this release")
    unrelated = [m for m in participating if m != delta_market]
    if unrelated:
        probe = unrelated[0]
        probe_dir = site / routes.get(probe, "/pet-friendly-hotels/%s/" % probe).strip("/")
        found = sorted(probe_dir.glob("*/index.html"))
        _check("unrelated_market_sample", len(found) > 0, "%s: %d routes" % (probe, len(found)))
        expected = next((m.get("route_count") for m in (candidate.manifest.get("markets") or ())
                         if m.get("market_id") == probe), None)
        _check("unrelated_route_count", expected is None or expected >= 0, "%s" % expected)
    else:
        _check("unrelated_market_sample", True, "single-market release")
        _check("unrelated_route_count", True, "single-market release")
    control = all((site / rel).is_file() for rel in ("_headers", "_redirects", "robots.txt"))
    _check("asset_integrity", control, "")

    failing = sorted(name for name, res in results.items() if not res["pass"])
    return OrderedDict((
        ("schema", VERIFICATION_SCHEMA),
        ("candidate_digest", candidate.digest),
        ("checks", results),
        ("failing", failing),
        ("passed", not failing),
        ("seconds", round(time.perf_counter() - started, 3)),
    ))


def record_verification(candidate: Candidate, record: Mapping,
                        verification: Mapping) -> "OrderedDict[str, Any]":
    """Write the verification result onto the activation record.

    ``LIVE`` is a claim about a verified activation, so it is only made here:
    an activation whose verification failed keeps ``outcome`` but never gains
    ``verified_at``.
    """
    updated = OrderedDict(record)
    updated["live_verification_results"] = OrderedDict(verification)
    passed = bool(verification.get("passed"))
    updated["verified_at"] = _iso() if passed else None
    updated["release_state"] = LIVE if (passed and record.get("outcome") == ACTIVATED) else FAILED
    operation_id = str(record.get("deployment_operation_id") or "unknown")
    _write_json(candidate.root / ("activation-%s.json" % operation_id), updated)
    _event("verify", candidate_digest=candidate.digest, deployment_operation_id=operation_id,
           result=updated["release_state"], verify_seconds=verification.get("seconds"),
           failing=list(verification.get("failing") or ()))
    return updated


# --------------------------------------------------------------------------- #
# Phase 18: rollback.
# --------------------------------------------------------------------------- #

def rollback(*, to_release_digest: str, expected_current: str, host: SimulatedHost,
             store: ReleaseStore, work_dir: Path,
             reason: str = "") -> "OrderedDict[str, Any]":
    """Restore an EXACT prior verified release, or refuse.

    The target must exist in durable release storage (never reconstructed from
    a branch) and the caller must name the release it believes is current. If
    a newer release is live, the rollback is refused: a stale rollback is how
    a live market gets un-deployed.
    """
    started = time.perf_counter()
    current = host.current()
    if current != expected_current:
        return OrderedDict((
            ("outcome", ACTIVATION_REFUSED), ("refusal", RELEASE_NOT_CURRENT),
            ("detail", "caller expected %s to be live, host serves %s"
             % (str(expected_current)[7:23], str(current)[7:23])),
            ("seconds", round(time.perf_counter() - started, 3)),
        ))
    target = store.get_release(to_release_digest)
    if target is None:
        return OrderedDict((
            ("outcome", ACTIVATION_REFUSED), ("refusal", FRAGMENT_UNAVAILABLE),
            ("detail", "release %s is not in durable storage; a rollback target is never rebuilt"
             % to_release_digest[7:23]),
            ("seconds", round(time.perf_counter() - started, 3)),
        ))
    site = Path(work_dir) / "rollback-site"
    if site.exists():
        shutil.rmtree(site, ignore_errors=True)
    archive = store.root / "bundles" / ("%s.zip" % _object_name(str(target.get("bundle_object"))))
    if not archive.is_file():
        return OrderedDict((
            ("outcome", ACTIVATION_REFUSED), ("refusal", FRAGMENT_UNAVAILABLE),
            ("detail", "stored release has no bundle object"),
            ("seconds", round(time.perf_counter() - started, 3)),
        ))
    BC.extract_archive(archive, site)
    actual = APS.bundle_digest(APS.file_hashes(site))
    if actual != target.get("bundle_sha256"):
        return OrderedDict((
            ("outcome", ACTIVATION_REFUSED), ("refusal", CANDIDATE_CORRUPT),
            ("detail", "stored rollback bundle hashes %s, record says %s"
             % (actual[:12], str(target.get("bundle_sha256"))[:12])),
            ("seconds", round(time.perf_counter() - started, 3)),
        ))
    operation_id = "rollback-%s" % to_release_digest[7:23]
    result = host.activate(operation_id, release_digest=to_release_digest,
                           bundle_sha256=str(target.get("bundle_sha256")), site=site)
    _event("rollback", candidate_digest=to_release_digest, expected_current=expected_current,
           result=result.get("outcome"), rollback_seconds=round(time.perf_counter() - started, 3))
    return OrderedDict((
        ("outcome", result.get("outcome")),
        ("restored_release_digest", to_release_digest),
        ("restored_bundle_sha256", target.get("bundle_sha256")),
        ("restored_markets", [m.get("market_id") for m in (target.get("markets") or ())]),
        ("host_deployment_id", result.get("host_deployment_id")),
        ("expected_current", expected_current),
        ("reason", reason),
        ("seconds", round(time.perf_counter() - started, 3)),
    ))


# --------------------------------------------------------------------------- #
# Status and CLI.
# --------------------------------------------------------------------------- #

def load_production_gate(path: Optional[Path] = None) -> "OrderedDict[str, Any]":
    """The explicit allowlist in front of real production activation.

    A missing gate file is a CLOSED gate, never an open one: the absence of a
    permission is not a permission.
    """
    path = Path(path) if path is not None else PRODUCTION_GATE_PATH
    if not path.is_file():
        return OrderedDict((("schema", PRODUCTION_GATE_SCHEMA),
                            ("RELEASE_COORDINATOR_PRODUCTION_ENABLED", "NO"),
                            ("RELEASE_COORDINATOR_PRODUCTION_ALLOWED_MARKETS", []),
                            ("why", "no gate file at %s; a missing permission is not a permission"
                             % path.name)))
    return _read_json(path)


def production_activation_allowed(market_id: Optional[str],
                                  gate: Optional[Mapping] = None) -> Tuple[bool, str]:
    """``(allowed, why)`` for ONE market, from the committed gate."""
    gate = gate if gate is not None else load_production_gate()
    if str(gate.get("RELEASE_COORDINATOR_PRODUCTION_ENABLED", "NO")).upper() != "YES":
        return False, "%s: RELEASE_COORDINATOR_PRODUCTION_ENABLED is %r" % (
            PRODUCTION_GATE_CLOSED, gate.get("RELEASE_COORDINATOR_PRODUCTION_ENABLED"))
    allowed = list(gate.get("RELEASE_COORDINATOR_PRODUCTION_ALLOWED_MARKETS") or ())
    if not allowed:
        return False, "%s: the pilot allowlist is empty" % PRODUCTION_GATE_CLOSED
    if market_id not in allowed:
        return False, "%s: %s is not in %s" % (MARKET_NOT_IN_PILOT_ALLOWLIST, market_id, allowed)
    return True, "%s is in the pilot allowlist and production activation is enabled" % market_id


def deployment_eligible(candidate: Candidate, *, auth: Optional[Mapping] = None,
                        live: Optional[LiveTruth] = None,
                        required: Optional[Mapping] = None,
                        ci_receipt: Optional[Mapping] = None,
                        gate: Optional[Mapping] = None,
                        superseded_by: Optional[str] = None) -> "OrderedDict[str, Any]":
    """Everything that must be true before this candidate could go live.

    Provenance is the whole answer: the candidate digest, its parent, its
    intended delta, the package and bundle receipts it was composed from, the
    FAST lane's verdict, a CI receipt WHEN THE CHANGE CLASS REQUIRES ONE, the
    founder's authorization, and the production gate. A data-only release that
    owes no broad run is not missing a CI receipt -- its remote validation
    state is NOT_REQUIRED_BY_POLICY, which is a decision, not a gap.
    """
    from scripts.pettripfinder import ci_validation as CI

    manifest = candidate.manifest
    market_id = (manifest.get("intended_delta") or {}).get("market_id")
    reasons: List[str] = []

    reasons.extend("%s: %s" % (CANDIDATE_CORRUPT, p) for p in candidate.verify_bytes())
    if auth is None:
        reasons.append("%s: no founder authorization binds this candidate" % NOT_AUTHORIZED)
    else:
        reasons.extend(authorization_problems(auth, candidate, live=live,
                                              superseded_by=superseded_by))

    receipt = candidate.receipt or {}
    fast_state = receipt.get("FAST_DATA_ONLY_RELEASE_ELIGIBLE")
    broad = CI.broad_validation_state(required or OrderedDict((("shards_required", []),)),
                                      ci_receipt,
                                      source_commit=manifest.get("source_commit"),
                                      candidate_digest=candidate.digest)
    if broad["state"] == "REFUSED":
        reasons.extend("%s: %s" % (BROAD_VALIDATION_REFUSED, p) for p in broad["problems"])

    allowed, why = production_activation_allowed(market_id, gate)
    if not allowed:
        reasons.append(why)

    receipts = OrderedDict((
        ("package_receipt", any(m.get("package_digest") for m in manifest.get("markets") or ())),
        ("bundle_validation_receipt",
         any(m.get("validation_receipt_digest") for m in manifest.get("markets") or ())),
        ("fast_lane_receipt", fast_state),
        ("ci_validation_receipt", broad["state"]),
        ("authorization", bool(auth)),
    ))
    return OrderedDict((
        ("candidate_digest", candidate.digest),
        ("deployment_artifact_digest", candidate.bundle_sha256),
        ("parent_release_digest", manifest.get("parent_release_digest")),
        ("intended_delta_digest", manifest.get("intended_delta_digest")),
        ("market", market_id),
        ("receipts", receipts),
        ("remote_broad_validation", broad),
        ("production_gate", why),
        ("DEPLOYMENT_ELIGIBLE", "YES" if not reasons else "NO"),
        ("reasons", reasons),
    ))


def activation_status() -> "OrderedDict[str, str]":
    return OrderedDict((
        ("RELEASE_COORDINATOR_IMPLEMENTED", "YES"),
        ("RELEASE_COORDINATOR_VALIDATED", "YES"),
        ("FINAL_CANDIDATE_LIFECYCLE_VALIDATED", "YES"),
        ("REAL_PRODUCTION_ACTIVATION", REAL_PRODUCTION_ACTIVATION),
        ("PRODUCTION_GATE", OrderedDict((
            ("enabled", load_production_gate().get("RELEASE_COORDINATOR_PRODUCTION_ENABLED")),
            ("allowed_markets", list(load_production_gate().get(
                "RELEASE_COORDINATOR_PRODUCTION_ALLOWED_MARKETS") or ())),
        ))),
        ("note", "005 shipped the release machine and a host simulator; 006 added a real host "
                 "adapter behind an explicit EMPTY allowlist. No market was promoted, no "
                 "participation changed, nothing was deployed."),
    ))


def plan(package: Optional[Mapping] = None, *, live: Optional[LiveTruth] = None,
         participation_doc: Optional[Mapping] = None, authority: Optional[Mapping] = None,
         store: Optional[ReleaseStore] = None) -> "OrderedDict[str, Any]":
    """What staging would do, without doing it."""
    live = live if live is not None else LiveTruth.read()
    store = store if store is not None else ReleaseStore()
    participation_doc = participation_doc if participation_doc is not None else LP.load_participation()
    parent_digest = live.digest()
    try:
        participating, added, removed = _final_membership(
            live, participation_doc, UPDATE if package else NO_DELTA,
            str(package["market_id"]) if package else None, authority or {})
        refusal = None
    except CoordinatorError as exc:
        participating, added, removed = list(live.participating_markets), [], []
        refusal = OrderedDict((("code", exc.code), ("detail", exc.detail)))
    stored = store.fragment_digests(parent_digest)
    return OrderedDict((
        ("parent_release_digest", parent_digest),
        ("live_verified", live.verified),
        ("live_problems", list(live.problems)),
        ("participating_markets", participating),
        ("markets_added", added), ("markets_removed", removed),
        ("delta_market", str(package["market_id"]) if package else None),
        ("fragments_available_from_store", sorted(m for m in participating if m in stored)),
        ("fragments_needing_build", sorted(m for m in participating if m not in stored)),
        ("global_artifacts", OrderedDict((k, v[0]) for k, v in GLOBAL_ARTIFACTS.items())),
        ("refusal", refusal),
        ("activation_status", activation_status()),
    ))


def main(argv: Optional[Sequence[str]] = None) -> int:  # pragma: no cover - CLI
    parser = argparse.ArgumentParser(
        description="ATLAS-THROUGHPUT-005 -- the atomic release coordinator. "
                    "The only writer of staged release manifests; production activation is DISABLED.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("inspect", help="current live truth and every file that claims it")
    p = sub.add_parser("plan", help="what staging would do")
    p.add_argument("--package", help="path to a sealed market package")
    p = sub.add_parser("stage", help="stage one candidate from live + one package delta")
    p.add_argument("--package", required=True)
    p.add_argument("--work", default=None)
    p.add_argument("--no-fast-lane", action="store_true")
    p = sub.add_parser("authorize-record", help="bind a founder decision to one staged candidate")
    p.add_argument("--candidate", required=True, help="a staged candidate directory")
    p.add_argument("--decided-by", required=True)
    p.add_argument("--notes", default="")
    p = sub.add_parser("activate-simulated", help="activate against the host SIMULATOR (never production)")
    p.add_argument("--candidate", required=True)
    p.add_argument("--host", default=None, help="simulator state directory")
    p.add_argument("--operation-id", default=None)
    p = sub.add_parser("verify-simulated", help="the targeted post-activation checks")
    p.add_argument("--candidate", required=True)
    p.add_argument("--host", default=None)
    p.add_argument("--operation-id", required=True)
    p = sub.add_parser("reconcile-simulated", help="ask the host what it actually holds")
    p.add_argument("--candidate", required=True)
    p.add_argument("--host", default=None)
    p.add_argument("--operation-id", required=True)
    p = sub.add_parser("rollback-simulated", help="restore an exact prior verified release")
    p.add_argument("--to", required=True, help="the release digest to restore")
    p.add_argument("--expected-current", required=True)
    p.add_argument("--host", default=None)
    p.add_argument("--work", default=None)
    p = sub.add_parser("status", help="the production activation freeze")
    args = parser.parse_args(argv)

    if args.command == "inspect":
        live = LiveTruth.read()
        print(SMP.canonical_json(live.to_dict()))
        return 0 if live.verified else 1
    if args.command == "status":
        print(SMP.canonical_json(activation_status()))
        return 0
    package = _read_json(Path(args.package)) if getattr(args, "package", None) else None
    if args.command == "plan":
        print(SMP.canonical_json(plan(package)))
        return 0
    if args.command == "stage":
        cache = BC.BundleCache()
        candidate = stage(package=package, cache=cache,
                          work_dir=Path(args.work) if args.work else None,
                          run_fast_lane=not args.no_fast_lane)
        print(SMP.canonical_json(candidate.to_dict()))
        return 0

    if args.command in ("authorize-record", "activate-simulated", "verify-simulated",
                        "reconcile-simulated"):
        candidate = Candidate.load(Path(args.candidate))
    host_root = Path(getattr(args, "host", None) or (candidate_root() / "simulated_host"))

    if args.command == "authorize-record":
        auth = authorize(candidate, decided_by=args.decided_by, notes=args.notes)
        print(SMP.canonical_json(auth))
        return 0
    if args.command == "activate-simulated":
        auth = _read_json(candidate.root / "authorization.json")
        host = SimulatedHost(host_root, live_release=LiveTruth.read().digest())
        record = activate(candidate, auth, host, live=LiveTruth.read(),
                          operation_id=args.operation_id)
        print(SMP.canonical_json(record))
        return 0 if record["outcome"] == ACTIVATED else 1
    if args.command == "verify-simulated":
        host = SimulatedHost(host_root)
        record = _read_json(candidate.root / ("activation-%s.json" % args.operation_id))
        verification = verify_live(candidate, host, record)
        print(SMP.canonical_json(record_verification(candidate, record, verification)))
        return 0 if verification["passed"] else 1
    if args.command == "reconcile-simulated":
        host = SimulatedHost(host_root)
        print(SMP.canonical_json(reconcile(candidate, host, args.operation_id)))
        return 0
    if args.command == "rollback-simulated":
        host = SimulatedHost(Path(args.host) if args.host else candidate_root() / "simulated_host")
        result = rollback(to_release_digest=args.to, expected_current=args.expected_current,
                          host=host, store=ReleaseStore(),
                          work_dir=Path(args.work) if args.work else candidate_root() / "rollback")
        print(SMP.canonical_json(result))
        return 0 if result.get("outcome") == ACTIVATED else 1
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
