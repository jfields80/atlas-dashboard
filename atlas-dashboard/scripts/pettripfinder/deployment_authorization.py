"""Deployment authorization and deployment record contracts.

WHY THIS EXISTS
---------------
Everything below the line was already true by PTF-046:

    market release contracts          (each market's own facts)
        -> global deployment manifest (one composed artifact, every gate)
        -> founder launch participation (which markets the founder admits)

What did not exist was the step that says "THIS artifact may be written to
production" in a way a machine can refuse. ``deployment_authorized`` was a
boolean nobody could legitimately flip: ``verify_manifest`` rejected ``true``
outright, and a deployer who wanted to proceed had nothing to bind the founder's
decision to except a chat transcript. PTF-047 closes that:

    -> deployment authorization  (ptf-deployment-authorization/1.0)
    -> production deployment     (netlify deploy --prod, outside this file)
    -> deployment record         (ptf-deployment-record/1.0)

An authorization AUTHORIZES THE ALREADY-VERIFIED ARTIFACT; it recomputes no
policy truth. It copies every binding the manifest pins -- bundle hash, source
commit, participation set, profile counts, sitemap, control files, measurement
config, launch participation record, release contract hashes, gate count -- plus
the production target and the rollback deploy, and ``verify_authorization``
fails closed the moment any of them disagrees with the manifest or with the
repository as it stands now. A one-byte change anywhere is a different artifact
and needs a new authorization.

STATE MODEL
-----------
    PREPARED   -> AUTHORIZED | SUPERSEDED
    AUTHORIZED -> DEPLOYED | FAILED | SUPERSEDED
    DEPLOYED   -> ROLLED_BACK

Only AUTHORIZED may be deployed, and only while no later authorization for the
same target is AUTHORIZED or DEPLOYED. DEPLOYED is consumed: a production
authorization is used once, so nobody inherits an endlessly reusable one. The
deployment record is written only after the real production outcome is known
and names the authorization it consumed.

Nothing here holds a credential. The Netlify site is identified by its public
name and domain; the site ID stays in the environment.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
DEPLOY_DIR = REPO_ROOT / "deploy" / "netlify"
AUTHORIZATIONS_DIR = DEPLOY_DIR / "deployment_authorizations"
RECORDS_DIR = DEPLOY_DIR / "deployment_records"

AUTHORIZATION_SCHEMA = "ptf-deployment-authorization/1.0"
RECORD_SCHEMA = "ptf-deployment-record/1.0"

PREPARED = "PREPARED"
AUTHORIZED = "AUTHORIZED"
DEPLOYED = "DEPLOYED"
ROLLED_BACK = "ROLLED_BACK"
FAILED = "FAILED"
SUPERSEDED = "SUPERSEDED"
STATUSES = (PREPARED, AUTHORIZED, DEPLOYED, ROLLED_BACK, FAILED, SUPERSEDED)
TRANSITIONS = {
    PREPARED: (AUTHORIZED, SUPERSEDED),
    AUTHORIZED: (DEPLOYED, FAILED, SUPERSEDED),
    DEPLOYED: (ROLLED_BACK,),
    ROLLED_BACK: (),
    FAILED: (),
    SUPERSEDED: (),
}
#: The only status a production write may proceed from.
DEPLOYABLE_STATUSES = (AUTHORIZED,)
#: Statuses under which a manifest may say deployment_authorized: true.
MANIFEST_AUTHORIZED_STATUSES = (AUTHORIZED, DEPLOYED)
#: A later authorization in one of these supersedes every earlier one.
SUPERSEDING_STATUSES = (AUTHORIZED, DEPLOYED)

RECORD_FINAL_STATUSES = (DEPLOYED, ROLLED_BACK, FAILED)

_NETLIFY_DEPLOY_ID = re.compile(r"^[0-9a-f]{24}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{7,40}$")

AUTHORIZATION_REQUIRED_FIELDS = (
    "schema", "authorization_id", "authorized_by", "authorized_at",
    "work_order", "source_commit", "manifest_source_commit", "bundle_sha256",
    "production_context", "participating_markets", "profile_counts",
    "total_profiles", "total_html_pages", "total_files", "sitemap_route_count",
    "sitemap_sha256", "headers_sha256", "redirects_sha256",
    "measurement_config_sha256", "measurement", "affiliate",
    "launch_participation_sha256", "release_contracts", "global_gate_count",
    "required_gates", "rollback_target", "target_site", "target_domain",
    "authorization_status", "status_history",
)
RECORD_REQUIRED_FIELDS = (
    "schema", "deployment_record_id", "authorization_id", "source_commit",
    "bundle_sha256", "deployment_id", "previous_deployment_id",
    "rollback_target", "target_site", "production_url", "deployed_at",
    "deployer", "deployed_directory", "command", "participating_markets",
    "profile_counts", "total_profiles", "sitemap_route_count",
    "global_gate_results", "live_verification_results", "final_status",
    "rollback_used", "rollback_reason", "restored_deployment_id",
)


class DeploymentAuthorizationError(RuntimeError):
    """Raised rather than letting an unbound authorization reach a deploy."""


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _now_iso() -> str:
    import datetime as _dt
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def _write_json(path: Path, doc: Mapping) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + chr(10),
                    encoding="utf-8", newline="\n")


def _read_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


# --------------------------------------------------------------------------- #
# Authorization: build, persist, transition.
# --------------------------------------------------------------------------- #

def authorization_path(authorization_id: str) -> Path:
    return AUTHORIZATIONS_DIR / ("%s.json" % authorization_id)


def build_authorization(manifest: Mapping, *, authorization_id: str,
                        work_order: str, authorized_by: str,
                        source_commit: str, rollback_target: str,
                        target_site: str, target_domain: str,
                        authorized_at: Optional[str] = None,
                        authorization_source: str = "",
                        note: str = "") -> Dict:
    """Bind every pinned input of ``manifest`` into a PREPARED authorization.

    ``manifest`` is the committed global deployment manifest (already verified
    by the caller -- this does not re-run its gates). ``source_commit`` is the
    lineage the founder named; ``manifest_source_commit`` is what the manifest
    itself says produced the bundle, and both are bound exactly. They may
    differ by the established one-commit lag (a deployment-metadata commit
    that moves no site byte), which is why the BINDING identity remains
    ``bundle_sha256``.
    """
    from scripts.pettripfinder import affiliate_destinations as AD
    control = manifest["control_files"]
    measurement = manifest["measurement"]
    participation = manifest["launch_participation"]
    markets = [row["market_id"] for row in manifest["participating_markets"]]
    counts = OrderedDict((row["market_id"], row["published_profiles"])
                         for row in manifest["participating_markets"])
    contracts = [OrderedDict([
        ("market_id", row["market_id"]),
        ("path", row["release_contract"]),
        ("sha256", row["release_contract_sha256"]),
    ]) for row in manifest["participating_markets"]]
    when = authorized_at or _now_iso()
    return OrderedDict([
        ("schema", AUTHORIZATION_SCHEMA),
        ("what_this_is",
         "Founder authorization to write ONE exact composed artifact to ONE "
         "production target. Every field under bindings is copied from the "
         "verified global deployment manifest and re-checked against the "
         "repository by verify_authorization; any disagreement refuses the "
         "deploy. Used once: DEPLOYED consumes it."),
        ("authorization_id", authorization_id),
        ("authorized_by", authorized_by),
        ("authorization_source", authorization_source),
        ("authorized_at", when),
        ("work_order", work_order),
        ("note", note),
        ("source_commit", source_commit),
        ("manifest_source_commit", manifest["source_commit"]),
        ("binding_identity", "bundle_sha256"),
        ("bundle_sha256", manifest["bundle_sha256"]),
        ("production_context", manifest["context"]),
        ("participating_markets", markets),
        ("profile_counts", counts),
        ("total_profiles", manifest["total_published_profiles"]),
        ("total_html_pages", manifest["total_html_pages"]),
        ("total_files", manifest["total_files"]),
        ("sitemap_route_count", manifest["sitemap_route_count"]),
        ("sitemap_sha256", manifest["sitemap_sha256"]),
        ("headers_source", control["headers_source"]),
        ("headers_sha256", control["headers_sha256"]),
        ("redirects_source", control["redirects_source"]),
        ("redirects_sha256", control["redirects_sha256"]),
        ("measurement_config_source", measurement["config_source"]),
        ("measurement_config_sha256", measurement["config_sha256"]),
        ("measurement", OrderedDict([
            ("enabled", measurement["enabled"]),
            ("provider_kind", measurement["provider_kind"]),
        ])),
        ("affiliate", OrderedDict([
            ("providers_enrolled",
             sum(1 for p in AD.load_providers().values() if p.enrolled)),
            ("destinations_active", len(AD.assemble_global_view())),
        ])),
        ("launch_participation_source", participation["source"]),
        ("launch_participation_sha256", participation["sha256"]),
        ("founder_authorized_markets", list(participation["founder_authorized"])),
        ("release_contracts", contracts),
        ("global_gate_count", len(manifest["required_gates"])),
        ("required_gates", list(manifest["required_gates"])),
        ("rollback_target", rollback_target),
        ("target_site", target_site),
        ("target_domain", target_domain),
        ("authorization_status", PREPARED),
        ("status_history", [OrderedDict([
            ("status", PREPARED), ("at", when),
            ("note", "bound to the verified manifest"),
        ])]),
    ])


def transition(auth: Mapping, to_status: str, *, note: str = "",
               at: Optional[str] = None, **facts) -> Dict:
    """A new document in ``to_status``; refuses any move the model forbids."""
    if to_status not in STATUSES:
        raise DeploymentAuthorizationError("unknown status %r" % to_status)
    current = auth.get("authorization_status")
    if to_status not in TRANSITIONS.get(current, ()):
        raise DeploymentAuthorizationError(
            "authorization %s cannot move %s -> %s (allowed: %s)"
            % (auth.get("authorization_id"), current, to_status,
               list(TRANSITIONS.get(current, ()))))
    doc = OrderedDict(auth)
    doc["authorization_status"] = to_status
    entry = OrderedDict([("status", to_status), ("at", at or _now_iso()),
                         ("note", note)])
    for key in sorted(facts):
        entry[key] = facts[key]
    doc["status_history"] = list(auth.get("status_history") or ()) + [entry]
    return doc


def write_authorization(auth: Mapping) -> Path:
    problems = _shape_problems(auth)
    if problems:
        raise DeploymentAuthorizationError(
            "refusing to write a malformed authorization: %s" % problems)
    path = authorization_path(auth["authorization_id"])
    _write_json(path, auth)
    return path


def load_authorization(authorization_id: str) -> Dict:
    path = authorization_path(authorization_id)
    if not path.is_file():
        raise DeploymentAuthorizationError(
            "no deployment authorization %r at %s" % (authorization_id, path))
    return _read_json(path)


def list_authorizations() -> List[Dict]:
    if not AUTHORIZATIONS_DIR.is_dir():
        return []
    return [_read_json(p) for p in sorted(AUTHORIZATIONS_DIR.glob("*.json"))]


def supersede_earlier(auth: Mapping, *, at: Optional[str] = None) -> List[str]:
    """Mark every other PREPARED/AUTHORIZED authorization for the same target
    SUPERSEDED. Returns the ids moved. DEPLOYED ones are history, untouched."""
    moved = []
    for other in list_authorizations():
        if other["authorization_id"] == auth["authorization_id"]:
            continue
        if other.get("target_site") != auth.get("target_site"):
            continue
        if other.get("authorization_status") in (PREPARED, AUTHORIZED):
            write_authorization(transition(
                other, SUPERSEDED, at=at,
                note="superseded by %s" % auth["authorization_id"]))
            moved.append(other["authorization_id"])
    return moved


# --------------------------------------------------------------------------- #
# Authorization: verification (fail closed).
# --------------------------------------------------------------------------- #

def _shape_problems(auth: Mapping) -> List[str]:
    problems = []
    if auth.get("schema") != AUTHORIZATION_SCHEMA:
        problems.append("schema is %r, expected %r"
                        % (auth.get("schema"), AUTHORIZATION_SCHEMA))
    for key in AUTHORIZATION_REQUIRED_FIELDS:
        if key not in auth or auth[key] in ("", None):
            problems.append("missing required field %r" % key)
    if auth.get("authorization_status") not in STATUSES:
        problems.append("authorization_status %r is not one of %s"
                        % (auth.get("authorization_status"), list(STATUSES)))
    for key in ("bundle_sha256", "sitemap_sha256", "headers_sha256",
                "redirects_sha256", "measurement_config_sha256",
                "launch_participation_sha256"):
        if not _SHA256.match(str(auth.get(key, ""))):
            problems.append("%s is not a sha256" % key)
    for key in ("source_commit", "manifest_source_commit"):
        if not _COMMIT.match(str(auth.get(key, ""))):
            problems.append("%s is not a commit id" % key)
    if not _NETLIFY_DEPLOY_ID.match(str(auth.get("rollback_target", ""))):
        problems.append("rollback_target is not a Netlify deploy id")
    if auth.get("production_context") != "production":
        problems.append("production_context is %r" % auth.get("production_context"))
    for key in ("authorization_id", "authorized_by", "work_order", "target_site",
                "target_domain"):
        if not isinstance(auth.get(key), str) or not auth.get(key):
            problems.append("%s must be a non-empty string" % key)
    return problems


def _same_commit(a: str, b: str) -> bool:
    a, b = str(a), str(b)
    return a == b or a.startswith(b) or b.startswith(a)


def verify_authorization(auth: Mapping, manifest: Optional[Mapping] = None,
                         *, check_manifest: bool = True) -> List[str]:
    """Every way this authorization disagrees with the artifact, or ``[]``.

    Checked against the committed manifest (the artifact's description) AND
    against the repository files the manifest pins, so neither a stale
    manifest nor a stale authorization can pass. ``check_manifest=False`` is
    for ``global_deployment.verify_manifest``, which is the caller then.
    """
    from scripts.pettripfinder import global_deployment as GD
    from scripts.pettripfinder import affiliate_destinations as AD

    problems = _shape_problems(auth)
    if problems:
        return problems
    doc = dict(manifest or GD.load_manifest())
    if check_manifest:
        problems.extend("manifest: %s" % p for p in GD.verify_manifest(
            dict(doc, deployment_authorized=False,
                 deployment_authorization=None)))

    def bind(key, actual, label=None):
        if auth.get(key) != actual:
            problems.append("%s: authorization binds %r, artifact has %r"
                            % (label or key, auth.get(key), actual))

    bind("bundle_sha256", doc.get("bundle_sha256"))
    if not _same_commit(auth["manifest_source_commit"], doc.get("source_commit")):
        problems.append("manifest_source_commit: authorization binds %r, manifest "
                        "says %r" % (auth["manifest_source_commit"],
                                     doc.get("source_commit")))
    bind("production_context", doc.get("context"))
    bind("participating_markets",
         [r["market_id"] for r in doc.get("participating_markets") or ()])
    bind("profile_counts", {r["market_id"]: r["published_profiles"]
                            for r in doc.get("participating_markets") or ()})
    bind("total_profiles", doc.get("total_published_profiles"))
    if sum((auth.get("profile_counts") or {}).values()) != auth.get("total_profiles"):
        problems.append("total_profiles does not equal the sum of profile_counts")
    bind("total_html_pages", doc.get("total_html_pages"))
    bind("total_files", doc.get("total_files"))
    bind("sitemap_route_count", doc.get("sitemap_route_count"))
    bind("sitemap_sha256", doc.get("sitemap_sha256"))
    control = doc.get("control_files") or {}
    bind("headers_sha256", control.get("headers_sha256"))
    bind("redirects_sha256", control.get("redirects_sha256"))
    measurement = doc.get("measurement") or {}
    bind("measurement_config_sha256", measurement.get("config_sha256"))
    if (auth.get("measurement") or {}).get("enabled") is not False or \
            (auth.get("measurement") or {}).get("provider_kind") != "none":
        problems.append("measurement: this authorization schema binds a DISABLED "
                        "measurement layer; enabling is its own release")
    if measurement.get("enabled") is not False:
        problems.append("measurement: manifest says enabled")
    affiliate = auth.get("affiliate") or {}
    enrolled = sum(1 for p in AD.load_providers().values() if p.enrolled)
    active = len(AD.assemble_global_view())
    if affiliate.get("providers_enrolled") != enrolled:
        problems.append("affiliate.providers_enrolled: authorization binds %r, "
                        "repository has %d" % (affiliate.get("providers_enrolled"), enrolled))
    if affiliate.get("destinations_active") != active:
        problems.append("affiliate.destinations_active: authorization binds %r, "
                        "repository has %d" % (affiliate.get("destinations_active"), active))
    participation = doc.get("launch_participation") or {}
    bind("launch_participation_sha256", participation.get("sha256"))
    bind("founder_authorized_markets", list(participation.get("founder_authorized") or ()))
    if sorted(auth.get("participating_markets") or ()) != \
            sorted(auth.get("founder_authorized_markets") or ()):
        problems.append("participating_markets is not the founder-authorized set")

    # Files on disk, independently of the manifest: a stale manifest and a
    # stale authorization must not be allowed to agree with each other.
    for key, source in (("headers_sha256", auth.get("headers_source")),
                        ("redirects_sha256", auth.get("redirects_source")),
                        ("measurement_config_sha256", auth.get("measurement_config_source")),
                        ("launch_participation_sha256", auth.get("launch_participation_source"))):
        path = REPO_ROOT / str(source or "")
        if not source or not path.is_file():
            problems.append("%s: source %r missing" % (key, source))
        elif _sha256_file(path) != auth.get(key):
            problems.append("%s: %s has changed since authorization" % (key, source))

    manifest_contracts = {r["market_id"]: r for r in doc.get("participating_markets") or ()}
    auth_contracts = {r["market_id"]: r for r in auth.get("release_contracts") or ()}
    if sorted(auth_contracts) != sorted(manifest_contracts):
        problems.append("release_contracts: authorization names %s, manifest %s"
                        % (sorted(auth_contracts), sorted(manifest_contracts)))
    for mid, row in auth_contracts.items():
        pinned = manifest_contracts.get(mid, {}).get("release_contract_sha256")
        if row.get("sha256") != pinned:
            problems.append("release_contracts[%s]: authorization binds %r, manifest %r"
                            % (mid, row.get("sha256"), pinned))
        path = REPO_ROOT / str(row.get("path") or "")
        if not path.is_file():
            problems.append("release_contracts[%s]: %s missing" % (mid, row.get("path")))
        elif _sha256_file(path) != row.get("sha256"):
            problems.append("release_contracts[%s]: contract has changed since "
                            "authorization" % mid)

    bind("required_gates", list(doc.get("required_gates") or ()))
    if auth.get("global_gate_count") != len(doc.get("required_gates") or ()):
        problems.append("global_gate_count: authorization binds %r, manifest requires %d"
                        % (auth.get("global_gate_count"), len(doc.get("required_gates") or ())))
    if sorted(auth.get("required_gates") or ()) != sorted(GD.REQUIRED_GLOBAL_GATES):
        problems.append("required_gates: authorization's catalogue differs from "
                        "global_deployment.REQUIRED_GLOBAL_GATES")
    if not doc.get("all_required_gates_pass"):
        problems.append("manifest does not claim a clean assembly")

    bind("target_domain", doc.get("base_url"))
    return problems


def deployability_problems(auth: Mapping,
                           manifest: Optional[Mapping] = None) -> List[str]:
    """``verify_authorization`` plus the state rules: AUTHORIZED, not consumed,
    not superseded by a later AUTHORIZED/DEPLOYED authorization."""
    problems = verify_authorization(auth, manifest)
    status = auth.get("authorization_status")
    if status not in DEPLOYABLE_STATUSES:
        problems.append("authorization_status is %s; only %s may deploy"
                        % (status, list(DEPLOYABLE_STATUSES)))
    for other in list_authorizations():
        if other["authorization_id"] == auth.get("authorization_id"):
            continue
        if other.get("target_site") != auth.get("target_site"):
            continue
        if other.get("authorization_status") in SUPERSEDING_STATUSES and \
                str(other.get("authorized_at")) > str(auth.get("authorized_at")):
            problems.append("superseded by later authorization %s (%s)"
                            % (other["authorization_id"], other["authorization_status"]))
    return problems


def verify_target(auth: Mapping, site_info: Mapping) -> List[str]:
    """The live Netlify site, as the API reports it, is the authorized target
    and still serves the rollback deploy. ``site_info`` is the getSite body;
    nothing secret is read from it."""
    problems = []
    if site_info.get("name") != auth.get("target_site"):
        problems.append("target_site: authorized %r, live site is %r"
                        % (auth.get("target_site"), site_info.get("name")))
    live_domain = site_info.get("ssl_url") or site_info.get("url")
    if live_domain != auth.get("target_domain"):
        problems.append("target_domain: authorized %r, live site serves %r"
                        % (auth.get("target_domain"), live_domain))
    published = (site_info.get("published_deploy") or {}).get("id")
    if published != auth.get("rollback_target"):
        problems.append("rollback_target: authorized %r, live published deploy is %r "
                        "-- production moved since authorization"
                        % (auth.get("rollback_target"), published))
    return problems


def verify_bundle_directory(auth: Mapping, site_dir: Path) -> List[str]:
    """The directory about to be uploaded IS the authorized bundle."""
    from scripts.pettripfinder.assemble_production_site import (
        bundle_digest, file_hashes)
    site_dir = Path(site_dir)
    if not site_dir.is_dir():
        return ["bundle directory %s does not exist" % site_dir]
    hashes = file_hashes(site_dir)
    digest = bundle_digest(hashes)
    problems = []
    if digest != auth.get("bundle_sha256"):
        problems.append("bundle directory hashes to %s, authorization binds %s"
                        % (digest, auth.get("bundle_sha256")))
    if len(hashes) != auth.get("total_files"):
        problems.append("bundle directory has %d files, authorization binds %r"
                        % (len(hashes), auth.get("total_files")))
    sitemap = site_dir / "sitemap.xml"
    if not sitemap.is_file() or _sha256_file(sitemap) != auth.get("sitemap_sha256"):
        problems.append("sitemap.xml is not the authorized sitemap")
    for name, key in (("_headers", "headers_sha256"), ("_redirects", "redirects_sha256")):
        path = site_dir / name
        if not path.is_file() or _sha256_file(path) != auth.get(key):
            problems.append("%s is not the authorized control file" % name)
    return problems


# --------------------------------------------------------------------------- #
# Manifest integration.
# --------------------------------------------------------------------------- #

def authorize_manifest(auth: Mapping) -> Dict:
    """Flip the committed manifest to authorized, referencing ``auth``.

    Refused unless the authorization verifies against the manifest and is
    AUTHORIZED: the flag is a mirror of the record, never a decision.
    """
    from scripts.pettripfinder import global_deployment as GD
    doc = GD.load_manifest()
    problems = verify_authorization(auth, doc)
    if problems:
        raise DeploymentAuthorizationError(
            "authorization does not bind this manifest: %s" % problems)
    if auth.get("authorization_status") not in MANIFEST_AUTHORIZED_STATUSES:
        raise DeploymentAuthorizationError(
            "authorization is %s; the manifest may only reference an "
            "AUTHORIZED or DEPLOYED authorization" % auth.get("authorization_status"))
    out = OrderedDict()
    for key, value in doc.items():
        if key == "deployment_authorized":
            out[key] = True
            out["deployment_authorization"] = OrderedDict([
                ("path", authorization_path(auth["authorization_id"])
                 .relative_to(REPO_ROOT).as_posix()),
                ("authorization_id", auth["authorization_id"]),
                ("bundle_sha256", auth["bundle_sha256"]),
            ])
        elif key in ("deployment_authorization", "deployment_authorization_note"):
            continue
        else:
            out[key] = value
    out["deployment_authorization_note"] = (
        "deployment_authorized mirrors the referenced authorization record; "
        "verify_manifest re-verifies that record against this manifest and "
        "the repository, and the record's own status says whether it may "
        "still be deployed or has been consumed.")
    GD.MANIFEST_PATH.write_text(json.dumps(out, indent=1, ensure_ascii=False)
                                + chr(10), encoding="utf-8", newline="\n")
    return dict(out)


def manifest_authorization_problems(doc: Mapping) -> List[str]:
    """What ``global_deployment.verify_manifest`` asks about the flag."""
    flag = doc.get("deployment_authorized")
    ref = doc.get("deployment_authorization")
    if flag is False:
        return [] if not ref else [
            "manifest references an authorization but says deployment_authorized false"]
    if flag is not True:
        return ["deployment_authorized must be true or false, got %r" % (flag,)]
    if not ref or not ref.get("authorization_id"):
        return ["manifest arrives pre-authorized: deployment_authorized is true "
                "with no deployment_authorization record to bind it"]
    try:
        auth = load_authorization(ref["authorization_id"])
    except DeploymentAuthorizationError as exc:
        return ["manifest arrives pre-authorized: %s" % exc]
    problems = ["authorization %s: %s" % (ref["authorization_id"], p)
                for p in verify_authorization(auth, doc, check_manifest=False)]
    if ref.get("bundle_sha256") != doc.get("bundle_sha256"):
        problems.append("deployment_authorization.bundle_sha256 does not match the manifest")
    if auth.get("authorization_status") not in MANIFEST_AUTHORIZED_STATUSES:
        problems.append("authorization %s is %s; a manifest may only stay authorized "
                        "under %s" % (ref["authorization_id"],
                                      auth.get("authorization_status"),
                                      list(MANIFEST_AUTHORIZED_STATUSES)))
    return problems


# --------------------------------------------------------------------------- #
# Deployment record.
# --------------------------------------------------------------------------- #

def record_path(deployment_record_id: str) -> Path:
    return RECORDS_DIR / ("%s.json" % deployment_record_id)


def build_deployment_record(auth: Mapping, *, deployment_record_id: str,
                            deployment_id: str, previous_deployment_id: str,
                            deployed_at: str, deployer: Mapping,
                            production_url: str, deployed_directory: str,
                            command: str, global_gate_results: Mapping,
                            live_verification_results: Mapping,
                            final_status: str, rollback_used: bool,
                            rollback_reason: Optional[str] = None,
                            restored_deployment_id: Optional[str] = None,
                            exit_status: Optional[int] = None) -> Dict:
    """The durable record of what actually happened, written after the fact."""
    return OrderedDict([
        ("schema", RECORD_SCHEMA),
        ("what_this_is",
         "What a production deployment actually did, written only after the "
         "outcome was known. Names the authorization it consumed; holds no "
         "credential."),
        ("deployment_record_id", deployment_record_id),
        ("authorization_id", auth["authorization_id"]),
        ("work_order", auth.get("work_order")),
        ("source_commit", auth["source_commit"]),
        ("manifest_source_commit", auth.get("manifest_source_commit")),
        ("bundle_sha256", auth["bundle_sha256"]),
        ("sitemap_sha256", auth.get("sitemap_sha256")),
        ("deployment_id", deployment_id),
        ("previous_deployment_id", previous_deployment_id),
        ("rollback_target", auth["rollback_target"]),
        ("target_site", auth["target_site"]),
        ("production_url", production_url),
        ("deployed_at", deployed_at),
        ("deployer", OrderedDict(deployer)),
        ("deployed_directory", deployed_directory),
        ("command", command),
        ("exit_status", exit_status),
        ("participating_markets", list(auth["participating_markets"])),
        ("profile_counts", OrderedDict(auth["profile_counts"])),
        ("total_profiles", auth["total_profiles"]),
        ("sitemap_route_count", auth["sitemap_route_count"]),
        ("global_gate_results", OrderedDict(global_gate_results)),
        ("measurement", OrderedDict(auth.get("measurement") or {})),
        ("affiliate", OrderedDict(auth.get("affiliate") or {})),
        ("live_verification_results", OrderedDict(live_verification_results)),
        ("final_status", final_status),
        ("rollback_used", bool(rollback_used)),
        ("rollback_reason", rollback_reason),
        ("restored_deployment_id", restored_deployment_id),
    ])


def verify_record(record: Mapping, auth: Optional[Mapping] = None) -> List[str]:
    problems = []
    if record.get("schema") != RECORD_SCHEMA:
        problems.append("schema is %r, expected %r" % (record.get("schema"), RECORD_SCHEMA))
    for key in RECORD_REQUIRED_FIELDS:
        if key not in record:
            problems.append("missing required field %r" % key)
    if problems:
        return problems
    if record["final_status"] not in RECORD_FINAL_STATUSES:
        problems.append("final_status %r is not one of %s"
                        % (record["final_status"], list(RECORD_FINAL_STATUSES)))
    if not _NETLIFY_DEPLOY_ID.match(str(record["deployment_id"] or "")) and \
            record["final_status"] != FAILED:
        problems.append("deployment_id is not a Netlify deploy id")
    if record["deployment_id"] == record["previous_deployment_id"]:
        problems.append("deployment_id equals previous_deployment_id")
    if record["previous_deployment_id"] != record["rollback_target"]:
        problems.append("previous_deployment_id is not the rollback_target")
    if record["final_status"] == DEPLOYED:
        if record["rollback_used"] or record["rollback_reason"] or \
                record["restored_deployment_id"]:
            problems.append("a DEPLOYED record may not claim a rollback")
        failures = [k for k, v in (record.get("live_verification_results") or {}).items()
                    if isinstance(v, Mapping) and v.get("pass") is False]
        if failures:
            problems.append("DEPLOYED with failed live checks: %s" % failures)
    else:
        if not record["rollback_used"]:
            problems.append("%s without rollback_used" % record["final_status"])
        if not record["rollback_reason"]:
            problems.append("%s without a rollback_reason" % record["final_status"])
        if record["final_status"] == ROLLED_BACK and \
                record["restored_deployment_id"] != record["rollback_target"]:
            problems.append("ROLLED_BACK must restore the rollback_target")
    deployer = record.get("deployer") or {}
    if not isinstance(deployer, Mapping) or not deployer:
        problems.append("deployer must be a non-empty mapping")
    blob = json.dumps(record).lower()
    for needle in ("nfp_", "netlify_auth_token", "bearer "):
        if needle in blob:
            problems.append("record appears to contain a credential (%r)" % needle)
    if auth is None:
        try:
            auth = load_authorization(record["authorization_id"])
        except DeploymentAuthorizationError as exc:
            problems.append(str(exc))
            return problems
    for key in ("source_commit", "bundle_sha256", "rollback_target", "target_site",
                "participating_markets", "total_profiles", "sitemap_route_count"):
        if record.get(key) != auth.get(key):
            problems.append("%s: record has %r, authorization %r"
                            % (key, record.get(key), auth.get(key)))
    if dict(record.get("profile_counts") or {}) != dict(auth.get("profile_counts") or {}):
        problems.append("profile_counts differ from the authorization")
    if record["final_status"] == DEPLOYED and auth.get("authorization_status") != DEPLOYED:
        problems.append("record says DEPLOYED but authorization %s is %s"
                        % (auth.get("authorization_id"), auth.get("authorization_status")))
    return problems


def write_record(record: Mapping) -> Path:
    problems = verify_record(record)
    if problems:
        raise DeploymentAuthorizationError(
            "refusing to write an inconsistent deployment record: %s" % problems)
    path = record_path(record["deployment_record_id"])
    _write_json(path, record)
    return path


def list_records() -> List[Dict]:
    if not RECORDS_DIR.is_dir():
        return []
    return [_read_json(p) for p in sorted(RECORDS_DIR.glob("*.json"))]


def main(argv: Optional[Sequence[str]] = None) -> int:  # pragma: no cover
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", metavar="AUTHORIZATION_ID")
    parser.add_argument("--deployable", metavar="AUTHORIZATION_ID")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args(argv)
    if args.list:
        for auth in list_authorizations():
            print(auth["authorization_id"], auth["authorization_status"],
                  auth["bundle_sha256"][:16], auth["target_site"])
        for rec in list_records():
            print(rec["deployment_record_id"], rec["final_status"],
                  rec["deployment_id"], rec["bundle_sha256"][:16])
        return 0
    if args.verify:
        problems = verify_authorization(load_authorization(args.verify))
        print(json.dumps({"disagreements": problems}, indent=2))
        return 1 if problems else 0
    if args.deployable:
        problems = deployability_problems(load_authorization(args.deployable))
        print(json.dumps({"blockers": problems}, indent=2))
        return 1 if problems else 0
    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
