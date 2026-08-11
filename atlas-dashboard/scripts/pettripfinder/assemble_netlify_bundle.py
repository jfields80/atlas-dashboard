"""PETTRIPFINDER-PROD-005A -- deterministic local Netlify bundle assembler.

Assembles one market's deployable PetTripFinder static bundle for a Netlify
manual (prebuilt) deploy. It REUSES the committed production generator
(``scripts.generate_pettripfinder_columbus_site.run``) -- no page-generation
logic is duplicated here -- then injects the tracked Netlify control files
(``site/_headers`` + ``site/_redirects``) and runs that market's release-gate
contract.

PTF-PER-MARKET-RELEASE-CONTRACTS-001: the contract is per market. This module
used to read one committed ``deploy/netlify/release_contract.json`` whose
numbers were Columbus's, so assembling Cleveland compared nineteen verified
hotels against Columbus's eighty-eight and failed closed on a figure that was
never about Cleveland. The contract for the market being assembled is now loaded
from ``deploy/netlify/release_contracts/<market_id>.json`` and is additionally
gated against that market's OWN derived authority; see
``scripts/pettripfinder/release_contracts.py`` for why both halves are required.

A passing contract is a STRUCTURAL statement -- the package is internally
consistent and safe to publish as a static bundle. It is not a deployment
authorization and it does not claim the market is complete; the contract's
``deployment_authorization`` block says so and is copied into the deployment
manifest.

Local-only and fail-closed:

* NO network request, NO Netlify API call, NO credential read.
* Never writes outside the requested ``--output`` root; refuses an output path
  inside the source tree, tests, launch package, or operational corpus, and
  refuses to overwrite tracked files (the only permitted in-repo location is the
  gitignored ``data/`` tree).
* Deterministic: two assemblies of the same context are byte-identical; no
  timestamps or machine-specific paths appear in the emitted artifacts.
* Atomic: the final ``site/`` is swapped into place ONLY after every release
  gate passes; a failure leaves any pre-existing output untouched.

Interface::

    python scripts/pettripfinder/assemble_netlify_bundle.py \\
        --context {preview|production} \\
        --market <market_id> \\
        --output data/deployment_staging/pettripfinder/prod005a_<context>

Output root contents (all deployable files live under ``site/``; the reports
stay OUTSIDE ``site/`` so they cannot be published)::

    <output>/site/                     the deployable website + _headers + _redirects
    <output>/deployment_manifest.json
    <output>/file_hash_manifest.json
    <output>/route_inventory.json
    <output>/validation_report.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.generate_pettripfinder_columbus_site import run as generate_site, _slug
from scripts.pettripfinder.market_context import PRODUCTION_MARKET_ID, resolve_market
from scripts.pettripfinder.market_ownership import owned_by
from scripts.pettripfinder.markets import (
    ROUTE_MODE_LEGACY_UNPREFIXED,
    MarketConfig,
    assign_hotels,
)
from scripts.pettripfinder.release_contracts import (
    RELEASE_CONTRACTS_DIR,
    contract_disagreements,
    contract_path,
    derive_authority,
    load_contract,
)
from scripts.pettripfinder.site_data import (
    load_published_hotel_policy_facts,
    normalize_name,
    read_production_rows,
    verified_public_hotels,
)

REPO_ROOT = _REPO_ROOT
DEPLOY_NETLIFY_DIR = REPO_ROOT / "deploy" / "netlify"
#: Columbus's contract path, kept as a module constant for the callers that only
#: ever ask about this repository's production market. Every other caller uses
#: ``release_contract_path(market_id)`` -- the constant is DERIVED from the named
#: production market, never a default that another market could silently inherit.
RELEASE_CONTRACT_PATH = contract_path(PRODUCTION_MARKET_ID)
HEADERS_PRODUCTION_PATH = DEPLOY_NETLIFY_DIR / "headers.production"
HEADERS_PREVIEW_PATH = DEPLOY_NETLIFY_DIR / "headers.preview"
REDIRECTS_PATH = DEPLOY_NETLIFY_DIR / "redirects"
NETLIFY_TOML_PATH = REPO_ROOT / "netlify.toml"

VALID_CONTEXTS = ("preview", "production")

# Build-internal artifacts the generator emits into the output dir. They are read
# for gating but MUST NOT ship in the publish root.
BUILD_INTERNAL_BASENAMES = frozenset({
    "_build_report.json",
    "_broken_link_report.json",
    "_quality_report.json",
    "bundle_manifest.json",
})

# Deployable text file types that are scanned for forbidden tokens.
_TEXT_SUFFIXES = frozenset({".html", ".css", ".txt", ".xml"})
_CONTROL_FILE_NAMES = frozenset({"_headers", "_redirects"})

_LOC_RE = re.compile(r"<loc>(.*?)</loc>")
# A Windows drive path (C:\ or C:/) -- a SINGLE letter not preceded by another
# letter, so URL schemes like ``http://`` (…p:/…) are never matched.
_DRIVE_PATH_RE = re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/]")


class AssembleError(RuntimeError):
    """Raised for any fail-closed condition (bad path, failed gate, etc.)."""


# --------------------------------------------------------------------------- #
# Shared parsers (also imported by the tests -- one parser, one behavior).
# --------------------------------------------------------------------------- #

def parse_headers_file(text: str) -> "OrderedDict[str, OrderedDict[str, str]]":
    """Parse a Netlify ``_headers`` file into ``{path_pattern: {header: value}}``.

    Blank lines and ``#`` comments are ignored, so a comment that merely mentions
    a header name (e.g. documenting why HSTS is omitted) is NOT treated as an
    active header. Path patterns are non-indented lines starting with ``/``;
    header directives are the indented ``Key: Value`` lines beneath them.
    """
    result: "OrderedDict[str, OrderedDict[str, str]]" = OrderedDict()
    current: Optional[str] = None
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indented = raw[:1].isspace()
        if not indented and stripped.startswith("/"):
            current = stripped
            result.setdefault(current, OrderedDict())
        elif indented and current is not None and ":" in stripped:
            key, value = stripped.split(":", 1)
            result[current][key.strip()] = value.strip()
    return result


def parse_redirects_file(text: str) -> List[Tuple[str, str, str]]:
    """Parse a Netlify ``_redirects`` file into ``[(from, to, status), ...]``.

    Blank lines and ``#`` comments are ignored. Status defaults to ``"301"`` when
    a rule omits it.
    """
    rules: List[Tuple[str, str, str]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 3:
            rules.append((parts[0], parts[1], parts[2]))
        elif len(parts) == 2:
            rules.append((parts[0], parts[1], "301"))
    return rules


def release_contract_path(market_id: str) -> Path:
    """The committed release-contract path for ``market_id``."""
    return contract_path(market_id)


def load_release_contract(market_id: str = PRODUCTION_MARKET_ID) -> Dict:
    """One market's committed release contract (fail closed).

    The market is EXPLICIT and defaults only to this repository's named
    production market. It is never "whichever contract happens to be there":
    a single shared contract is exactly what made a Cleveland assembly gate
    itself on Columbus's inventory size.
    """
    return load_contract(market_id)


# --------------------------------------------------------------------------- #
# Deterministic hashing helpers.
# --------------------------------------------------------------------------- #

def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def content_sha256(data: bytes) -> str:
    """SHA-256 of a text artifact's CONTENT, independent of line endings.

    PTF-SITE-005. The committed policy package was gated on a raw byte hash,
    which is not a stable identity for a text file under version control: git
    rewrites LF to CRLF on checkout when core.autocrlf is enabled, so the same
    reviewed package hashes differently in a fresh clone than in the working
    tree it was written from. The gate then failed closed and the assembler
    refused to build -- correct behaviour on a wrong premise.

    A CR before a LF is a checkout artifact, not content. Normalising it away
    still detects every change that matters: an altered fee, an added or
    removed hotel, a reordered key. Nothing about the package's meaning can
    change without changing this digest.

    A UTF-8 BOM is stripped for the same reason -- it is an encoding marker
    some editors add, not part of the document.
    """
    if data[:3] == b"\xef\xbb\xbf":
        data = data[3:]
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def bundle_hash(site_dir: Path) -> Tuple[str, "OrderedDict[str, str]"]:
    """Deterministic hash over the publishable ``site/`` tree.

    Returns ``(bundle_sha256, {relpath: file_sha256})``. The manifest is a sorted
    list of ``"<relpath>  <sha256>"`` lines (POSIX separators, content hashes, no
    timestamps), and the bundle hash is the sha256 of that manifest text.
    """
    files: "OrderedDict[str, str]" = OrderedDict()
    for path in sorted(site_dir.rglob("*"), key=lambda p: p.relative_to(site_dir).as_posix()):
        if path.is_file():
            rel = path.relative_to(site_dir).as_posix()
            files[rel] = _sha256_bytes(path.read_bytes())
    manifest = "".join("%s  %s\n" % (rel, digest) for rel, digest in files.items())
    return _sha256_bytes(manifest.encode("utf-8")), files


def _git_head() -> str:
    """Local ``git rev-parse HEAD`` (deterministic for a given checkout). Returns
    ``""`` if git is unavailable -- never a timestamp, so artifacts stay
    reproducible."""
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except Exception:
        return ""


# --------------------------------------------------------------------------- #
# Output-path safety.
# --------------------------------------------------------------------------- #

def _is_relative_to(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def validate_output_path(output: str) -> Path:
    """Resolve and safety-check the requested output root.

    Permitted: any path OUTSIDE the repository (e.g. a pytest tmp dir), or a path
    under the gitignored ``data/`` tree -- but never the operational corpus
    ``data/import/``. Everything else (repo root, source, tests, docs, launch
    package, engines, services) is rejected. ``.resolve()`` collapses ``..`` and
    follows symlinks, so a traversal/symlink escape is checked at its real
    target.
    """
    out = Path(output)
    if not out.is_absolute():
        out = REPO_ROOT / out
    out = out.resolve()
    repo = REPO_ROOT.resolve()

    if out == repo:
        raise AssembleError("output path may not be the repository root: %s" % out)

    if _is_relative_to(out, repo):
        parts = out.relative_to(repo).parts
        if not parts or parts[0] != "data":
            raise AssembleError(
                "in-repo output must live under the gitignored data/ tree "
                "(never the source, tests, docs, launch package, or engines): %s"
                % out.relative_to(repo).as_posix())
        if len(parts) >= 2 and parts[1] == "import":
            raise AssembleError(
                "output path may not be inside the operational corpus data/import/: %s"
                % out.relative_to(repo).as_posix())
    return out


# --------------------------------------------------------------------------- #
# Gate recording.
# --------------------------------------------------------------------------- #

def _gate(gates: "OrderedDict[str, Dict]", gate_id: str, passed: bool, detail: str = "") -> bool:
    gates[gate_id] = {"pass": bool(passed), "detail": str(detail)}
    return bool(passed)


# --------------------------------------------------------------------------- #
# Assembly.
# --------------------------------------------------------------------------- #

def assemble(context: str, output: str, contract: Optional[Dict] = None,
             market: Optional[MarketConfig] = None) -> Dict:
    """Assemble the deploy bundle for ``context`` into ``output``.

    Returns the deployment manifest dict. Raises ``AssembleError`` (fail-closed)
    on an unsafe path, a package/identity mismatch, or any failed release gate --
    leaving any pre-existing output untouched.
    """
    if context not in VALID_CONTEXTS:
        raise AssembleError("context must be one of %s, got %r" % (VALID_CONTEXTS, context))

    out_root = validate_output_path(output)
    # The market is resolved BEFORE the contract, because the market is what
    # selects the contract. Reversing that order is how one market's numbers
    # came to gate another market's build.
    _market = resolve_market(market)
    contract = contract if contract is not None else load_release_contract(_market.market_id)

    gates: "OrderedDict[str, Dict]" = OrderedDict()

    # ---- Phase 1: pre-generation authority + identity gates (fail early) ----
    # A contract may never stand in for another market's. This is checked before
    # anything is read THROUGH the contract, so a mismatched document cannot
    # first point the package gates at the wrong authority file.
    if not _gate(gates, "authority.contract_is_for_this_market",
                 contract.get("market_id") == _market.market_id,
                 "contract=%r market=%r" % (contract.get("market_id"), _market.market_id)):
        raise AssembleError(
            "release contract is for market %r but the assembly is for %r"
            % (contract.get("market_id"), _market.market_id))

    # The reviewed contract must agree with what this market's own committed
    # authority derives -- census, policy package, exclusion registry, seed
    # inventory, corridor routes, and any reconciliation manifest it commits.
    # A contract that merely parses proves nothing; a derivation that checks
    # only itself proves nothing either.
    disagreements = contract_disagreements(contract, derive_authority(_market.market_id))
    _gate(gates, "authority.reconciliation_matches_market_authority",
          not disagreements, "; ".join(disagreements[:6]))

    pkg_spec = contract["policy_package"]
    pkg_path = REPO_ROOT / pkg_spec["path"]
    if not _gate(gates, "authority.package_exists", pkg_path.exists(),
                 pkg_spec["path"]):
        raise AssembleError("committed policy package missing: %s" % pkg_path)

    pkg_bytes = pkg_path.read_bytes()
    # Content hash, not byte hash: see content_sha256. A raw byte hash made this
    # gate fail in any clone whose checkout used different line endings.
    pkg_sha = content_sha256(pkg_bytes)
    _gate(gates, "authority.package_sha256",
          pkg_sha == pkg_spec["expected_sha256"], pkg_sha)
    pkg = json.loads(pkg_bytes.decode("utf-8-sig"))
    # The expected schema version lives in the contract, never in the gate NAME.
    # It was ``authority.package_schema_1_1``, which would have been a false
    # statement for Dayton's schema-1.0 package -- the same defect the hotel
    # count already had when the gate was called ``..._14``.
    _gate(gates, "authority.package_schema_version",
          str(pkg.get("schema_version")) == str(pkg_spec["expected_schema_version"]),
          str(pkg.get("schema_version")))
    # The expected count lives in the contract, never in the gate NAME -- baking
    # it in made an intended inventory change present as a gate failure.
    _gate(gates, "authority.package_count",
          len(pkg.get("hotels", [])) == pkg_spec["expected_record_count"],
          str(len(pkg.get("hotels", []))))

    policy_facts = load_published_hotel_policy_facts(_market.market_id)
    # PTF-MULTI-MARKET-INVENTORY-SCOPING-001. The release gate must reason over
    # exactly the inventory the generator published, which is this market's
    # owned rows -- not every approved row in the file. Scoping here keeps the
    # gate and the build in agreement once a second market's rows exist; before
    # that they are the same set, which is why Columbus does not move.
    seed_rows = owned_by(read_production_rows(), _market.market_id,
                         context="release-gate seed inventory")
    hotel_seed = [r for r in seed_rows if r.get("category") == "pet-friendly-hotels"]
    # Fail-closed identity join (raises if a committed record has no display row).
    verified_rows = verified_public_hotels(hotel_seed, policy_facts)
    verified_slugs = {_slug(r["name"]) for r in verified_rows}
    held_rows = [r for r in hotel_seed if _slug(r["name"]) not in verified_slugs]
    held_slugs = {_slug(r["name"]) for r in held_rows}
    verified_names = {r["name"] for r in verified_rows}
    held_names = {r["name"] for r in held_rows if r.get("name")}
    # PTF-CORRIDORS-002: allowed corridor routes come from the SAME committed
    # market-config assignment the generator publishes from (config slugs,
    # published corridors only) -- the gate and the build can never disagree.
    _assignment = assign_hotels(_market, verified_rows)
    corridor_slugs = {_market.corridor_by_id(cid).slug for cid in _assignment.published}

    surface = contract["public_surface"]
    _gate(gates, "identity.verified_from_package",
          len(verified_slugs) == surface["public_hotel_profile_count"],
          str(len(verified_slugs)))
    _gate(gates, "identity.held_derived",
          len(held_slugs) == surface["excluded_public_profile_count"],
          str(len(held_slugs)))

    pre_failures = [gid for gid, res in gates.items() if not res["pass"]]
    if pre_failures:
        raise AssembleError(
            "pre-generation gate(s) failed (no site generated): %s -- details=%s"
            % (pre_failures, {g: gates[g] for g in pre_failures}))

    # ---- Phase 2: generate + build site/ + remaining gates ----
    work = out_root / ".assemble_work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    try:
        gen_dir = work / "generated"
        gen_dir.mkdir(parents=True)
        # The generator receives the SAME resolved market the gate above used,
        # so the route gate and the build it checks can never disagree about
        # which market's corridors are published (PTF-MULTIMARKET-001).
        rc = generate_site(str(gen_dir), market=_market)
        if rc != 0:
            raise AssembleError("generator returned non-zero exit code %s" % rc)

        # Reuse the generator's own reports for content gates.
        build_report = json.loads((gen_dir / "_build_report.json").read_text(encoding="utf-8"))
        broken_report = json.loads((gen_dir / "_broken_link_report.json").read_text(encoding="utf-8"))
        quality_report = json.loads((gen_dir / "_quality_report.json").read_text(encoding="utf-8"))
        # PTF-INVENTORY-001: the expected hotel count is read from the release
        # contract rather than hardcoded here (and in the gate's own NAME, which
        # previously said "_14"). The gate is just as strict -- the build must
        # match the contract exactly -- but an approved inventory change is now
        # a data edit in one place instead of a code edit plus a rename.
        #
        # PTF-PER-MARKET-RELEASE-CONTRACTS-001: read from the contract IN USE,
        # not by re-loading from disk. Re-loading fetched Columbus's document
        # regardless of which market was being assembled, so this gate compared
        # Cleveland's nineteen generated profiles against Columbus's 88 and was
        # the last failure standing in the way of a second market's bundle.
        expected_hotels = int(contract["policy_package"]["expected_record_count"])
        _gate(gates, "content.build_report_hotel_count_matches_contract",
              build_report.get("hotel_count") == expected_hotels
              and not build_report.get("warnings"),
              "hotel_count=%s expected=%s warnings=%s" % (build_report.get("hotel_count"),
                                                          expected_hotels,
                                                          build_report.get("warnings")))
        _gate(gates, "content.zero_broken_links",
              broken_report.get("broken_links") == [],
              str(broken_report.get("broken_links")))
        _gate(gates, "content.quality_report_clean",
              quality_report.get("failures") == [],
              str(quality_report.get("failures")))

        # Copy the generated static site into site/, excluding build-internal
        # artifacts, then inject the context-correct control files.
        site_dir = work / "site"
        site_dir.mkdir()
        site_root = site_dir.resolve()
        for src in sorted(gen_dir.rglob("*")):
            if src.is_dir():
                continue
            rel = src.relative_to(gen_dir)
            if rel.name in BUILD_INTERNAL_BASENAMES:
                continue
            dest = site_dir / rel
            if not _is_relative_to(dest.resolve(), site_root):
                raise AssembleError("refusing to write outside site/: %s" % rel.as_posix())
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)

        headers_src = HEADERS_PRODUCTION_PATH if context == "production" else HEADERS_PREVIEW_PATH
        headers_bytes = headers_src.read_bytes()
        redirects_bytes = REDIRECTS_PATH.read_bytes()
        (site_dir / "_headers").write_bytes(headers_bytes)
        (site_dir / "_redirects").write_bytes(redirects_bytes)

        _run_publish_gates(gates, contract, context, site_dir, headers_bytes, redirects_bytes)
        _run_route_gates(gates, contract, _market, site_dir, verified_slugs, held_slugs,
                         corridor_slugs, held_names, verified_names)
        _run_tech_gates(gates, contract, site_dir, held_slugs)

        # Every declared minimum gate must be present AND passing.
        minimum = contract["minimum_release_gates"]
        missing = [gid for gid in minimum if gid not in gates]
        failing = {gid: res for gid, res in gates.items() if not res["pass"]}
        all_pass = not missing and not failing

        bundle_sha, file_hashes = bundle_hash(site_dir)
        html_pages = sum(1 for p in site_dir.rglob("*.html"))
        total_files = sum(1 for p in site_dir.rglob("*") if p.is_file())
        sitemap_locs = _LOC_RE.findall((site_dir / "sitemap.xml").read_text(encoding="utf-8"))

        manifest = OrderedDict([
            ("product", contract["product"]),
            ("market_id", _market.market_id),
            ("contract_id", contract["contract_id"]),
            ("context", context),
            ("base_url", contract["canonical"]["base_url"]),
            ("publishable_root", "site/"),
            ("control_files", ["_headers", "_redirects"]),
            ("committed_package_path", pkg_spec["path"]),
            ("committed_package_schema", str(pkg.get("schema_version"))),
            ("committed_package_records", len(pkg.get("hotels", []))),
            ("committed_package_sha256", pkg_sha),
            ("generated_from_commit", _git_head()),
            ("hotel_profile_routes", len(verified_slugs)),
            ("excluded_hotel_profiles", len(held_slugs)),
            ("html_pages", html_pages),
            ("total_files", total_files),
            ("bundle_sha256", bundle_sha),
            ("all_gates_pass", all_pass),
            ("wrote_public_or_remote", False),
            ("release_name", _release_name(contract, _git_head(), pkg_sha, bundle_sha)),
            # The reconciliation travels WITH the bundle, so nobody reading the
            # manifest has to go looking for how much of the market is still
            # unanswered, and the authorization caveat cannot be separated from
            # the artifact it qualifies.
            ("reconciliation", OrderedDict(contract["reconciliation"])),
            ("release_authorization", OrderedDict(contract["deployment_authorization"])),
        ])
        route_inventory = OrderedDict([
            ("context", context),
            ("hotel_profile_routes", len(verified_slugs)),
            ("hotel_slugs", sorted(verified_slugs)),
            ("excluded_hotel_slugs", sorted(held_slugs)),
            ("corridor_slugs", sorted(corridor_slugs)),
            ("html_pages", html_pages),
            ("sitemap_loc_count", len(sitemap_locs)),
            ("total_files", total_files),
            ("control_files", ["_headers", "_redirects"]),
        ])
        file_hash_manifest = OrderedDict([
            ("bundle_sha256", bundle_sha),
            ("file_count", len(file_hashes)),
            ("files", dict(file_hashes)),
        ])
        validation_report = OrderedDict([
            ("context", context),
            ("all_gates_pass", all_pass),
            ("gates_total", len(gates)),
            ("gates_passed", sum(1 for r in gates.values() if r["pass"])),
            ("minimum_gates_declared", len(minimum)),
            ("minimum_gates_missing", missing),
            ("failing_gates", failing),
            ("gates", dict(gates)),
        ])

        if not all_pass:
            raise AssembleError(
                "release gates failed for context=%s: missing=%s failing=%s"
                % (context, missing, list(failing)))

        # ---- Phase 3: atomic publish of site/ + reports (gates all passed) ----
        _atomic_replace_dir(site_dir, out_root / "site")
        _write_json(out_root / "deployment_manifest.json", manifest)
        _write_json(out_root / "file_hash_manifest.json", file_hash_manifest)
        _write_json(out_root / "route_inventory.json", route_inventory)
        _write_json(out_root / "validation_report.json", validation_report)
        return dict(manifest)
    finally:
        if work.exists():
            shutil.rmtree(work, ignore_errors=True)


def _release_name(contract: Dict, commit: str, pkg_sha: str, bundle_sha: str) -> str:
    """``<prefix>-<commit7>-<pkg8>-<bundle8>``.

    The prefix is declared per contract rather than hard-coded, so each market
    names its own releases. Columbus's prefix is deliberately still
    ``prod-005-columbus``: its live releases are identified by that string, and
    renaming them to match a new convention would break the trail back to what
    is actually deployed.
    """
    return "%s-%s-%s-%s" % (contract["release_name_prefix"],
                            (commit or "nogit")[:7], pkg_sha[:8], bundle_sha[:8])


def _run_publish_gates(gates, contract, context, site_dir, headers_bytes, redirects_bytes):
    publish = contract["publish"]
    headers_present = (site_dir / "_headers").exists()
    redirects_present = (site_dir / "_redirects").exists()
    _gate(gates, "publish.control_files_present",
          headers_present and redirects_present,
          "_headers=%s _redirects=%s" % (headers_present, redirects_present))
    _gate(gates, "publish.headers_match_tracked_source",
          (site_dir / "_headers").read_bytes() == headers_bytes, "")
    _gate(gates, "publish.redirects_match_tracked_source",
          (site_dir / "_redirects").read_bytes() == redirects_bytes, "")

    leaked_reports = sorted(
        p.relative_to(site_dir).as_posix() for p in site_dir.rglob("*")
        if p.is_file() and p.name in BUILD_INTERNAL_BASENAMES)
    _gate(gates, "publish.no_build_reports_in_site", not leaked_reports, str(leaked_reports))

    forbidden_segments = set(publish["forbidden_path_segments"])
    forbidden_ext = set(publish["forbidden_extensions"])
    forbidden_basenames = set(publish["forbidden_basenames"])
    offenders: List[str] = []
    for p in site_dir.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(site_dir)
        if any(seg in forbidden_segments for seg in rel.parts):
            offenders.append(rel.as_posix())
        elif p.suffix.lower() in forbidden_ext:
            offenders.append(rel.as_posix())
        elif rel.name in forbidden_basenames:
            offenders.append(rel.as_posix())
    _gate(gates, "publish.no_forbidden_files", not offenders, str(sorted(offenders)[:20]))

    # Preview carries X-Robots-Tag noindex; production must NOT.
    header_map = parse_headers_file((site_dir / "_headers").read_text(encoding="utf-8"))
    root_headers = header_map.get("/*", {})
    has_noindex = "X-Robots-Tag" in root_headers and "noindex" in root_headers["X-Robots-Tag"].lower()
    if context == "preview":
        ok = has_noindex
    else:
        ok = not has_noindex
    _gate(gates, "headers.context_noindex_preview_only", ok,
          "context=%s X-Robots-Tag=%r" % (context, root_headers.get("X-Robots-Tag")))


def _run_route_gates(gates, contract, market, site_dir, verified_slugs, held_slugs,
                     corridor_slugs, held_names, verified_names):
    hotels_dir = site_dir / "pet-friendly-hotels"
    profile_dirs = {d.name for d in hotels_dir.iterdir()
                    if d.is_dir() and (d / "index.html").exists()}
    present_profiles = sorted(profile_dirs & verified_slugs)
    # Which directory names under the category root are legitimately NOT a hotel
    # profile depends on the market's route mode, so it is derived from the
    # market rather than listed. A market_prefixed market nests its hub,
    # corridor, and comparison pages under its own slug; a legacy_unprefixed
    # market (Columbus) puts corridors and the comparison page at this level.
    allowed_nonprofile = {"policy-comparison"} | corridor_slugs
    if market.route_mode != ROUTE_MODE_LEGACY_UNPREFIXED:
        allowed_nonprofile.add(market.market_slug)
    unexpected = sorted(profile_dirs - verified_slugs - allowed_nonprofile)

    # The gate names carry no count. ``route.exactly_14_hotel_profiles`` and
    # ``route.all_14_committed_present`` were already false for Columbus at 88,
    # and naming a number in an id shared by three markets guarantees at least
    # two of them are lying about what the gate checks.
    _gate(gates, "route.profile_count_matches_contract",
          len(present_profiles) == contract["public_surface"]["public_hotel_profile_count"]
          and not unexpected,
          "profiles=%d expected=%d unexpected=%s"
          % (len(present_profiles),
             contract["public_surface"]["public_hotel_profile_count"], unexpected))
    _gate(gates, "route.all_committed_profiles_present",
          set(present_profiles) == verified_slugs,
          str(sorted(verified_slugs - set(present_profiles))))

    held_present = sorted(profile_dirs & held_slugs)
    _gate(gates, "route.all_held_absent", not held_present and not unexpected,
          "held_present=%s unexpected=%s" % (held_present, unexpected))

    # PTF-COLUMBUS-SELECTOR-CLOSEOUT-001 retired ``route.drury_plaza_absent``.
    #
    # PROD-005A named Drury Plaza Hotel Columbus Downtown in the contract as a
    # sentinel: the flagship held record, hard-coded so a leak could not be
    # missed. It has since been captured, its policy located, its observation
    # passed by the membrane and its row cleared by the publication guard -- so
    # the gate now asserted that a legitimately verified hotel must not appear,
    # and there is no way to keep such a gate truthful.
    #
    # Nothing is lost. ``route.all_held_absent`` above is the same rule stated
    # generally, and it DERIVES the held set (seed hotels minus verified) rather
    # than naming one hotel. Any record that is held is covered by it; a record
    # that is no longer held should no longer be covered.

    # No reference to any held hotel on any surface. Slug-in-href is the precise
    # check; display-name matching adds coverage but skips names that overlap a
    # verified name (avoids false positives from shared brand tokens).
    safe_held_names = [
        hn for hn in held_names
        if not any(hn in vn or vn in hn for vn in verified_names)
    ]
    refs: Dict[str, List[str]] = {}
    for p in site_dir.rglob("*.html"):
        text = p.read_text(encoding="utf-8")
        rel = p.relative_to(site_dir).as_posix()
        for hs in held_slugs:
            if ("/pet-friendly-hotels/%s/" % hs) in text or ("/go/%s/" % hs) in text:
                refs.setdefault(rel, []).append(hs)
        for hn in safe_held_names:
            if hn in text:
                refs.setdefault(rel, []).append(hn)
    _gate(gates, "route.no_excluded_reference_on_any_surface", not refs,
          str(dict(sorted(refs.items())[:10])))


def _run_tech_gates(gates, contract, site_dir, held_slugs):
    base_url = contract["canonical"]["base_url"]

    go_dir = site_dir / "go"
    go_pages = list(go_dir.rglob("index.html")) if go_dir.exists() else []
    noindex_bad = [p.relative_to(site_dir).as_posix() for p in go_pages
                   if 'content="noindex, nofollow"' not in p.read_text(encoding="utf-8")]
    _gate(gates, "tech.go_pages_noindex", bool(go_pages) and not noindex_bad,
          "%d go pages, %d not-noindex" % (len(go_pages), len(noindex_bad)))

    sitemap = (site_dir / "sitemap.xml").read_text(encoding="utf-8")
    locs = _LOC_RE.findall(sitemap)
    bad_locs = [l for l in locs if not l.startswith(base_url) or "/go/" in l]
    held_locs = [l for l in locs if any(("/%s/" % hs) in l for hs in held_slugs)]
    _gate(gates, "tech.sitemap_public_canonical_only",
          bool(locs) and not bad_locs and not held_locs,
          "%d locs, %d bad, %d held" % (len(locs), len(bad_locs), len(held_locs)))

    robots = (site_dir / "robots.txt").read_text(encoding="utf-8")
    _gate(gates, "tech.robots_sitemap_host_apex",
          ("Sitemap: %s/sitemap.xml" % base_url) in robots, "")

    # Token scans over every deployable text file.
    cred_tokens = ("NETLIFY_AUTH_TOKEN", "NETLIFY_SITE_ID", "nfp_")
    win_tokens = ("C:\\Atlas", "C:/Atlas", "\\Users\\")
    runtime_tokens = ("AppData", "/Users/", str(REPO_ROOT), str(REPO_ROOT.as_posix()))
    cred_hits: List[str] = []
    win_hits: List[str] = []
    runtime_hits: List[str] = []
    for p in site_dir.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in _TEXT_SUFFIXES and p.name not in _CONTROL_FILE_NAMES:
            continue
        text = p.read_text(encoding="utf-8")
        rel = p.relative_to(site_dir).as_posix()
        if any(tok in text for tok in cred_tokens):
            cred_hits.append(rel)
        if any(tok in text for tok in win_tokens) or _DRIVE_PATH_RE.search(text):
            win_hits.append(rel)
        if any(tok in text for tok in runtime_tokens):
            runtime_hits.append(rel)
    _gate(gates, "tech.no_credentials", not cred_hits, str(sorted(cred_hits)[:20]))
    _gate(gates, "tech.no_windows_local_paths", not win_hits, str(sorted(win_hits)[:20]))
    _gate(gates, "tech.no_runtime_paths", not runtime_hits, str(sorted(runtime_hits)[:20]))


def _atomic_replace_dir(src: Path, dst: Path) -> None:
    """Move ``src`` onto ``dst`` atomically (same filesystem). Any pre-existing
    ``dst`` is renamed aside first and only removed after the swap succeeds, so a
    failure restores the previous directory."""
    backup: Optional[Path] = None
    if dst.exists():
        backup = dst.with_name(dst.name + ".old")
        if backup.exists():
            shutil.rmtree(backup)
        os.replace(dst, backup)
    try:
        os.replace(src, dst)
    except Exception:
        if backup is not None:
            os.replace(backup, dst)
        raise
    if backup is not None:
        shutil.rmtree(backup, ignore_errors=True)


def _write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8", newline="\n")


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--context", required=True, choices=VALID_CONTEXTS,
                   help="header context to assemble")
    p.add_argument("--output", required=True,
                   help="output root (must be under the gitignored data/ tree or "
                        "outside the repo)")
    p.add_argument("--market", default=PRODUCTION_MARKET_ID,
                   help="market_id to assemble (PTF-MULTIMARKET-001: explicit, never "
                        "inferred from how many markets are configured). Its release "
                        "contract is read from %s/<market_id>.json"
                        % RELEASE_CONTRACTS_DIR.relative_to(REPO_ROOT).as_posix())
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        manifest = assemble(args.context, args.output,
                            market=resolve_market(market_id=args.market))
    except AssembleError as exc:
        print("ASSEMBLY FAILED (fail-closed): %s" % exc, file=sys.stderr)
        return 2
    recon = manifest["reconciliation"]
    fmt = lambda v: "n/a" if v is None else str(v)
    print("Netlify bundle assembled (market=%s context=%s)"
          % (manifest["market_id"], manifest["context"]))
    print("  release contract:     %s" % manifest["contract_id"])
    print("  output root:          %s" % Path(args.output))
    print("  publishable root:     site/")
    print("  hotel profile routes: %s" % manifest["hotel_profile_routes"])
    print("  excluded profiles:    %s" % manifest["excluded_hotel_profiles"])
    print("  html pages:           %s" % manifest["html_pages"])
    print("  total files:          %s" % manifest["total_files"])
    print("  bundle sha256:        %s" % manifest["bundle_sha256"])
    print("  release name:         %s" % manifest["release_name"])
    print("  all gates pass:       %s" % manifest["all_gates_pass"])
    print("  reconciliation:       %s confirmed / %s published / %s no-pets / "
          "%s resolved / %s unresolved"
          % (fmt(recon["confirmed_identities"]), recon["published_pet_friendly"],
             recon["verified_no_pets"], recon["resolved"], fmt(recon["unresolved"])))
    # Printed on success, every time. A green build is the moment somebody is
    # most likely to read "all gates pass" as "ship it".
    print("  NOT a deployment authorization: passing gates mean the package is")
    print("  structurally deployable. They do not authorize a deploy and do not")
    print("  claim this market's identity universe is resolved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
