"""The one record that says a multi-market bundle may be deployed.

WHY THIS EXISTS
---------------
Release contracts are PER MARKET, and correctly so: a market's published
population, routes and reconciliation are its own facts, reviewed by whoever
reviewed that market. The deployable artifact is not per market. It is one
bundle on one domain composed from every published market at once, and nothing
described the artifact itself -- so PTF-...-DEPLOYMENT-AND-LIVE-VERIFICATION-044
found a composed bundle that satisfied eight gates and would have stripped every
security header from production.

This does not copy any market's facts. It records which markets participated,
proves each one independently passed its own contract, and pins the properties
that only exist once the fragments are composed: the bundle hash, the control
files, the sitemap, and the global gates.

WHAT IT DELIBERATELY DOES NOT DO
---------------------------------
Authorize a deployment. ``deployment_authorized`` is false here and stays false
until a work order whose purpose is deployment flips it against a named commit
and a named bundle hash. A manifest that arrives pre-authorized is a manifest
nobody reads.
"""

from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = (REPO_ROOT / "deploy" / "netlify"
                 / "global_deployment_manifest.json")

#: 1.1 (PTF-046): pins the founder launch participation record alongside the
#: control files and names each excluded market's launch status.
MANIFEST_SCHEMA = "ptf-global-deployment-manifest/1.1"

#: Gates the composed artifact must pass before it is deployable. Named here so
#: the requirement is a committed list rather than whatever the assembler
#: happened to run: a gate that silently stops running is the failure this
#: catalogue exists to make impossible.
REQUIRED_GLOBAL_GATES = (
    # composition
    "assembly.no_route_collisions",
    "assembly.no_global_shadowing",
    "assembly.anchor_supplies_global_shell",
    # participation
    "global.every_included_market_has_a_contract",
    "global.every_included_market_contract_verifies",
    "global.no_ineligible_market_included",
    "global.market_profile_counts_match_contracts",
    "global.live_routes_preserved",
    # founder participation (PTF-046): every registered market carries an
    # explicit launch status, and no status contradicts the market's source.
    "global.launch_participation_explicit",
    "global.launch_participation_agrees_with_source",
    # publishable shape
    "publish.control_files_present",
    "publish.headers_match_tracked_source",
    "publish.redirects_match_tracked_source",
    "publish.no_forbidden_files",
    "publish.no_build_reports_in_site",
    # The production _headers must not carry the preview noindex, and the
    # preview _headers must. Ran on every composed bundle since 045 but was
    # never catalogued (25 ran, 24 required) -- found by PTF-046, which
    # requires the list of gates that ran to BE this list.
    "headers.context_noindex_preview_only",
    # content
    "content.zero_broken_links",
    "content.canonical_uniqueness",
    "content.sitemap_is_the_site",
    "content.sitemap_excludes_go",
    "content.go_routes_unique",
    # measurement (PTF-MEASUREMENT-001): the committed contract is valid, a
    # content page carries its block exactly once when enabled and never when
    # disabled, and a disabled bundle loads no external script.
    "measurement.config_valid",
    "measurement.snippet_once_per_content_page",
    "measurement.no_external_script_when_disabled",
    # affiliate (Phase 1b): every mapped destination points at an allowlisted
    # host of an ENROLLED provider and is bound to the property it was mapped
    # against. All three pass vacuously at zero destinations.
    "affiliate.destinations_allowlisted",
    "affiliate.identity_bound",
    "affiliate.no_destination_without_enrolled_provider",
)


class GlobalDeploymentError(RuntimeError):
    """Raised rather than describing a bundle nobody can reproduce."""


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_manifest(bundle_manifest: Mapping) -> Dict:
    """The durable record, derived from one assembler run.

    ``bundle_manifest`` is what ``assemble_production_site.assemble`` returned.
    Everything here comes from it or from committed files; nothing is measured
    a second time, because two measurements of one build are two chances to
    disagree.
    """
    from scripts.pettripfinder.release_contracts import contract_path

    context = bundle_manifest.get("context")
    if context != "production":
        raise GlobalDeploymentError(
            "a deployment manifest describes the PRODUCTION artifact; this "
            "bundle was assembled for context %r" % context)

    gates = bundle_manifest.get("gates") or {}
    missing = [gate for gate in REQUIRED_GLOBAL_GATES if gate not in gates]
    failing = sorted(gid for gid, res in gates.items() if not res.get("pass"))

    markets = []
    for row in bundle_manifest.get("participating_markets") or ():
        path = contract_path(row["market_id"])
        markets.append(OrderedDict([
            ("market_id", row["market_id"]),
            ("published_profiles", row["published_profiles"]),
            # The contract is REFERENCED and hashed, never copied. A market's
            # facts stay in the market's own document.
            ("release_contract",
             path.relative_to(REPO_ROOT).as_posix()),
            ("release_contract_sha256", _sha256_file(path)),
            ("contract_disagreements", list(row["contract_disagreements"])),
        ]))

    return OrderedDict([
        ("schema", MANIFEST_SCHEMA),
        ("what_this_is",
         "The composed multi-market production artifact. Per-market release "
         "contracts remain the authority for each market's own facts; this "
         "proves each participated cleanly and pins what only exists once "
         "they are composed."),
        ("context", context),
        ("base_url", bundle_manifest["base_url"]),
        ("anchor_market", bundle_manifest["anchor_market"]),
        # Informational. The BINDING identity is bundle_sha256: these are
        # code-only commits that do not change a byte of the site, so the
        # commit a manifest names and the commit a deployer checks out can
        # differ by one without describing different artifacts. A deployment
        # work order authorizes the HASH and states the commit it built from.
        ("source_commit", bundle_manifest["generated_from_commit"]),
        ("binding_identity", "bundle_sha256"),
        ("bundle_sha256", bundle_manifest["bundle_sha256"]),
        ("sitemap_sha256", bundle_manifest["sitemap_sha256"]),
        ("control_files", OrderedDict(bundle_manifest["control_files"])),
        # PTF-MEASUREMENT-001: the measurement contract the bundle was built
        # under, pinned like a control file. A config edit after stamping is a
        # different artifact, and verify_manifest says so.
        ("measurement", OrderedDict(bundle_manifest["measurement"])),
        # PTF-046: the founder's participation record, pinned. A market the
        # founder withheld is listed under excluded_markets with its launch
        # status, so "excluded" never reads as "broken".
        ("launch_participation",
         OrderedDict(bundle_manifest["launch_participation"])),
        ("participating_markets", markets),
        ("total_published_profiles",
         sum(row["published_profiles"] for row in markets)),
        ("total_html_pages", bundle_manifest["total_html_pages"]),
        ("total_files", bundle_manifest["total_files"]),
        ("sitemap_route_count", bundle_manifest["sitemap_route_count"]),
        ("excluded_markets", [
            OrderedDict([
                ("market_id", row["market_id"]),
                ("launch_status", row.get("launch_status")),
                ("why", sorted(k for k, v in row["conditions"].items() if not v)
                 + ([] if row.get("founder_authorized_for_launch")
                    else ["founder_authorized_for_launch"])),
            ])
            for row in bundle_manifest.get("markets_registered_but_excluded")
            or ()]),
        ("required_gates", list(REQUIRED_GLOBAL_GATES)),
        ("gates_missing", missing),
        ("gates_failing", failing),
        ("all_required_gates_pass", not missing and not failing),
        # The line 044 stopped at, stated as data.
        ("deployment_authorized", False),
        ("deployment_authorization_note",
         "Assembly is not authorization. A later work order whose purpose is "
         "deployment authorizes THIS source_commit and THIS bundle_sha256, "
         "and nothing else."),
    ])


def write_manifest(bundle_manifest: Mapping) -> Dict:
    doc = build_manifest(bundle_manifest)
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    # newline="\n" so the committed bytes do not depend on the platform that
    # stamped them (the file is eol=lf in .gitattributes).
    MANIFEST_PATH.write_text(json.dumps(doc, indent=1, ensure_ascii=False)
                             + chr(10), encoding="utf-8", newline="\n")
    return doc


def load_manifest() -> Dict:
    if not MANIFEST_PATH.is_file():
        raise GlobalDeploymentError("no global deployment manifest committed")
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8-sig"))


def verify_manifest(manifest: Optional[Mapping] = None) -> List[str]:
    """What the committed manifest disagrees with, or ``[]``.

    Checked against the repository as it stands now -- the contracts it
    references, the control files it pins -- so a manifest describing a state
    the repository has left is caught before a deploy is planned around it.
    The BUNDLE hash is not re-derived here: that costs a full build, and the
    deployment work order re-assembles anyway.
    """
    doc = dict(manifest or load_manifest())
    problems: List[str] = []

    if doc.get("schema") != MANIFEST_SCHEMA:
        problems.append("schema is %r, expected %r"
                        % (doc.get("schema"), MANIFEST_SCHEMA))
    if doc.get("context") != "production":
        problems.append("context is %r" % doc.get("context"))
    # PTF-047: ``deployment_authorized`` is a mirror of a deployment
    # authorization record, never a decision. True without a record that
    # verifies against THIS manifest is what "pre-authorized" means.
    from scripts.pettripfinder.deployment_authorization import (
        manifest_authorization_problems)
    problems.extend(manifest_authorization_problems(doc))

    for row in doc.get("participating_markets") or ():
        path = REPO_ROOT / row["release_contract"]
        if not path.is_file():
            problems.append("%s: contract missing at %s"
                            % (row["market_id"], row["release_contract"]))
            continue
        if _sha256_file(path) != row["release_contract_sha256"]:
            problems.append("%s: release contract has changed since the "
                            "manifest was written" % row["market_id"])
        if row["contract_disagreements"]:
            problems.append("%s: contract disagreed at assembly time"
                            % row["market_id"])

    control = doc.get("control_files") or {}
    for kind in ("headers", "redirects"):
        source = control.get("%s_source" % kind)
        pinned = control.get("%s_sha256" % kind)
        if not source or not pinned:
            problems.append("control file %s is not pinned" % kind)
            continue
        path = REPO_ROOT / source
        if not path.is_file():
            problems.append("control file source missing: %s" % source)
        elif _sha256_file(path) != pinned:
            problems.append("%s has changed since the manifest was written"
                            % source)

    measurement = doc.get("measurement") or {}
    source = measurement.get("config_source")
    pinned = measurement.get("config_sha256")
    if not source or not pinned:
        problems.append("measurement config is not pinned")
    else:
        path = REPO_ROOT / source
        if not path.is_file():
            problems.append("measurement config source missing: %s" % source)
        elif _sha256_file(path) != pinned:
            problems.append("%s has changed since the manifest was written" % source)

    # PTF-046: the participation record is an input to the artifact. If it
    # has changed, or it now authorizes a different set than the manifest
    # says participated, this manifest describes a bundle nobody would build.
    participation = doc.get("launch_participation") or {}
    source = participation.get("source")
    pinned = participation.get("sha256")
    if not source or not pinned:
        problems.append("launch participation record is not pinned")
    else:
        path = REPO_ROOT / source
        if not path.is_file():
            problems.append("launch participation source missing: %s" % source)
        elif _sha256_file(path) != pinned:
            problems.append("%s has changed since the manifest was written" % source)
        else:
            from scripts.pettripfinder.launch_participation import (
                LaunchParticipationError, authorized_market_ids)
            try:
                authorized = authorized_market_ids()
            except LaunchParticipationError as exc:
                problems.append("launch participation record unreadable: %s" % exc)
            else:
                participated = sorted(row["market_id"] for row
                                      in doc.get("participating_markets") or ())
                if authorized != participated:
                    problems.append(
                        "founder authorizes %s but the manifest's participating "
                        "set is %s" % (authorized, participated))

    missing = [gate for gate in REQUIRED_GLOBAL_GATES
               if gate not in (doc.get("required_gates") or ())]
    if missing:
        problems.append("manifest omits required gates: %s" % missing)
    if doc.get("gates_failing"):
        problems.append("gates failed at assembly: %s" % doc["gates_failing"])
    if doc.get("gates_missing"):
        problems.append("gates never ran: %s" % doc["gates_missing"])
    if not doc.get("all_required_gates_pass"):
        problems.append("the manifest does not claim a clean assembly")
    return problems


def main(argv: Optional[Sequence[str]] = None) -> int:  # pragma: no cover
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--show", action="store_true")
    args = parser.parse_args(argv)
    if args.verify:
        problems = verify_manifest()
        print(json.dumps({"disagreements": problems}, indent=2))
        return 1 if problems else 0
    if args.show:
        doc = load_manifest()
        print(json.dumps({k: v for k, v in doc.items()
                          if k != "participating_markets"}, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
