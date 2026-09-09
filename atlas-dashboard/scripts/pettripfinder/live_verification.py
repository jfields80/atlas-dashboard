"""ATLAS-THROUGHPUT-006 -- the production host adapter and the live HTTP
verification client.

005 defined nine post-activation checks and ran them against staged bytes with
a simulator. This module supplies the two real halves that were missing: an
adapter that speaks the deployment host's actual semantics, and an HTTP client
that asks production the nine questions.

Neither of them deploys anything here. ``NetlifyHost`` is constructed with
``enabled=False`` by default and refuses to run a mutating command in that
state; the verification client is pointed at a local or staged origin unless a
caller explicitly authorises production. 006 ships the machine and leaves the
switch off.

**Netlify's semantics, read from this repository rather than assumed** (the
committed records, authorizations and ``netlify.toml``):

* Deploys are PREBUILT and manual: ``netlify deploy --prod --no-build --dir
  <bundle>/site --site <site>``. The ``--dir`` value is the binding publish
  source; ``--no-build`` is mandatory, because without it the CLI runs a git
  build and uploads nothing from the directory.
* The site is ``pettripfinder-prod``, linked at deploy time through the
  ``NETLIFY_SITE_ID`` environment variable, never a committed
  ``.netlify/state.json``. The CLI scaffolds a gitignored ``.netlify/`` that
  fails the assembler gate, so it is removed after every deploy.
* A deploy id is 24 hex characters. Production serves ``https://pettripfinder.com``
  and any individual deploy stays reachable at ``https://<deploy-id>--<site>.netlify.app``,
  which is what lets a verification compare the new release against the one it
  replaced.
* Upload and publish are ONE operation for ``--prod``; there is no separate
  activate step to hold. Rollback is therefore "publish an earlier deploy"
  (restore), not "undo" -- which is exactly why 005 keeps the previous release
  in durable storage rather than trusting the host to remember it.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from collections import OrderedDict
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from scripts.pettripfinder import sealed_market_package as SMP

HOST_ADAPTER_SCHEMA = "ptf-host-adapter/1.0"
VERIFICATION_SCHEMA = "ptf-live-http-verification/1.0"

DEFAULT_SITE = "pettripfinder-prod"
DEFAULT_PRODUCTION_URL = "https://pettripfinder.com"
DEPLOY_ID = re.compile(r"^[0-9a-f]{24}$")

#: Outcomes. UNKNOWN is a first-class answer: a timeout is not a failure and
#: certainly not a pass, and treating it as either is how a good release gets
#: rolled back or a bad one gets kept.
OK = "OK"
FAILED = "FAILED"
UNKNOWN = "UNKNOWN"
REFUSED = "REFUSED"

HOST_DISABLED = "HOST_DISABLED"
NOT_AUTHORISED = "NOT_AUTHORISED"
CLI_MISSING = "CLI_MISSING"
SITE_UNSET = "SITE_UNSET"


class HostError(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__("%s: %s" % (code, detail) if detail else code)
        self.code = code
        self.detail = detail


# --------------------------------------------------------------------------- #
# The host adapter.
# --------------------------------------------------------------------------- #

class NetlifyHost:
    """The real deployment host, with its switch off by default.

    Every mutating operation goes through ``_run``, which refuses unless the
    adapter was constructed ``enabled=True`` AND the operation was explicitly
    authorised. A disabled adapter still builds and returns the exact command
    it WOULD run, which is what makes the plan reviewable before anyone gives
    it permission.
    """

    def __init__(self, *, site: str = DEFAULT_SITE, production_url: str = DEFAULT_PRODUCTION_URL,
                 enabled: bool = False, authorised_markets: Sequence[str] = (),
                 runner: Optional[Callable[[Sequence[str]], subprocess.CompletedProcess]] = None,
                 timeout_seconds: int = 900) -> None:
        self.site = site
        self.production_url = production_url
        self.enabled = bool(enabled)
        self.authorised_markets = tuple(authorised_markets)
        self.timeout_seconds = timeout_seconds
        self._runner = runner
        self.calls: List[List[str]] = []

    # ---- description ------------------------------------------------------ #
    def describe(self) -> "OrderedDict[str, Any]":
        return OrderedDict((
            ("schema", HOST_ADAPTER_SCHEMA),
            ("host", "netlify"),
            ("site", self.site),
            ("site_id_source", "the NETLIFY_SITE_ID environment variable at deploy time; "
                               "never a committed .netlify/state.json"),
            ("production_url", self.production_url),
            ("deploy_command", "netlify deploy --prod --no-build --dir <candidate>/site --site <site>"),
            ("no_build_required", "without --no-build the CLI runs a git build and uploads nothing "
                                  "from --dir, so the deployed bytes would not be the tested bytes"),
            ("deploy_id_shape", "24 hex characters"),
            ("per_deploy_url", "https://<deploy-id>--<site>.netlify.app"),
            ("upload_and_publish", "ONE operation for --prod: the host offers no separate activate "
                                   "step to hold, so the coordinator's parent guard runs immediately "
                                   "before the call"),
            ("rollback", "publish an earlier deploy (restore); the host does not undo, which is why "
                         "the previous release lives in durable release storage"),
            ("scaffolding_side_effect", "the CLI writes a gitignored .netlify/ that fails the "
                                        "assembler gate; remove it after every deploy"),
            ("enabled", self.enabled),
            ("authorised_markets", list(self.authorised_markets)),
        ))

    # ---- command construction (always safe) ------------------------------- #
    def deploy_command(self, site_dir: Path, *, production: bool = True) -> List[str]:
        argv = ["netlify", "deploy", "--no-build", "--dir", str(Path(site_dir)), "--site", self.site]
        if production:
            argv.insert(2, "--prod")
        return argv

    def restore_command(self, deploy_id: str) -> List[str]:
        return ["netlify", "api", "restoreSiteDeploy", "--data",
                json.dumps({"site_id": self.site, "deploy_id": deploy_id})]

    # ---- gated execution -------------------------------------------------- #
    def _run(self, argv: Sequence[str], *, market_id: Optional[str],
             authorised: bool) -> "OrderedDict[str, Any]":
        self.calls.append(list(argv))
        if not self.enabled:
            return OrderedDict((("outcome", REFUSED), ("refusal", HOST_DISABLED),
                                ("command", list(argv)),
                                ("detail", "the host adapter is constructed disabled; 006 ships the "
                                           "machine with the switch off")))
        if not authorised:
            return OrderedDict((("outcome", REFUSED), ("refusal", NOT_AUTHORISED),
                                ("command", list(argv)),
                                ("detail", "no explicit authorisation for this operation")))
        if market_id is not None and market_id not in self.authorised_markets:
            return OrderedDict((("outcome", REFUSED), ("refusal", NOT_AUTHORISED),
                                ("command", list(argv)),
                                ("detail", "%s is not in the pilot allowlist %s"
                                           % (market_id, list(self.authorised_markets)))))
        if not os.environ.get("NETLIFY_SITE_ID"):
            return OrderedDict((("outcome", REFUSED), ("refusal", SITE_UNSET),
                                ("command", list(argv)),
                                ("detail", "NETLIFY_SITE_ID is unset; the site is linked at deploy time")))
        runner = self._runner or (lambda a: subprocess.run(
            list(a), capture_output=True, text=True, timeout=self.timeout_seconds))
        try:
            proc = runner(argv)
        except FileNotFoundError:
            return OrderedDict((("outcome", REFUSED), ("refusal", CLI_MISSING),
                                ("command", list(argv)), ("detail", "the netlify CLI is not installed")))
        except subprocess.TimeoutExpired:
            return OrderedDict((("outcome", UNKNOWN), ("command", list(argv)),
                                ("detail", "the deploy did not report before the deadline; the host "
                                           "must be reconciled before any retry")))
        text = (getattr(proc, "stdout", "") or "") + (getattr(proc, "stderr", "") or "")
        found = re.search(r"\b([0-9a-f]{24})\b", text)
        return OrderedDict((
            ("outcome", OK if getattr(proc, "returncode", 1) == 0 else FAILED),
            ("command", list(argv)),
            ("exit_status", getattr(proc, "returncode", None)),
            ("host_deployment_id", found.group(1) if found else None),
        ))

    def deploy(self, site_dir: Path, *, market_id: Optional[str] = None,
               authorised: bool = False, production: bool = True) -> "OrderedDict[str, Any]":
        result = self._run(self.deploy_command(site_dir, production=production),
                           market_id=market_id, authorised=authorised)
        if result.get("outcome") == OK:
            self._remove_scaffolding(Path(site_dir))
        return result

    def restore(self, deploy_id: str, *, market_id: Optional[str] = None,
                authorised: bool = False) -> "OrderedDict[str, Any]":
        if not DEPLOY_ID.match(str(deploy_id)):
            raise HostError("BAD_DEPLOY_ID", str(deploy_id))
        return self._run(self.restore_command(deploy_id), market_id=market_id, authorised=authorised)

    @staticmethod
    def _remove_scaffolding(site_dir: Path) -> None:
        for candidate in (Path(site_dir) / ".netlify", Path(site_dir).parent / ".netlify"):
            if candidate.is_dir():
                shutil.rmtree(candidate, ignore_errors=True)

    def current(self, *, fetch: Optional[Callable[[str], Optional[bytes]]] = None
                ) -> "OrderedDict[str, Any]":
        """What production serves now, read over HTTP -- never mutating."""
        client = HTTPProbe(fetch=fetch)
        result = client.get(self.production_url + "/sitemap.xml")
        return OrderedDict((("url", self.production_url), ("outcome", result["outcome"]),
                            ("status", result.get("status")),
                            ("bytes", result.get("bytes"))))


# --------------------------------------------------------------------------- #
# The HTTP client.
# --------------------------------------------------------------------------- #

class HTTPProbe:
    """Bounded, retrying GETs whose failure mode is UNKNOWN, not FAILED."""

    def __init__(self, *, timeout: float = 10.0, retries: int = 2, backoff: float = 0.5,
                 fetch: Optional[Callable[[str], Optional[bytes]]] = None,
                 sleep: Optional[Callable[[float], None]] = None) -> None:
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self._fetch = fetch
        self._sleep = sleep or time.sleep
        self.requests: List[str] = []

    def get(self, url: str) -> "OrderedDict[str, Any]":
        self.requests.append(url)
        last: Optional[str] = None
        for attempt in range(self.retries + 1):
            try:
                if self._fetch is not None:
                    body = self._fetch(url)
                    if body is None:
                        return OrderedDict((("url", url), ("outcome", FAILED), ("status", 404),
                                            ("detail", "not served")))
                    return OrderedDict((("url", url), ("outcome", OK), ("status", 200),
                                        ("bytes", len(body)), ("body", body)))
                request = urllib.request.Request(url, headers={"User-Agent": "ptf-release-verify/1.0"})
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    body = response.read()
                    return OrderedDict((("url", url), ("outcome", OK), ("status", response.status),
                                        ("bytes", len(body)), ("body", body)))
            except urllib.error.HTTPError as exc:
                return OrderedDict((("url", url), ("outcome", FAILED), ("status", exc.code),
                                    ("detail", "HTTP %s" % exc.code)))
            except Exception as exc:                      # timeout, DNS, reset
                last = type(exc).__name__
                if attempt < self.retries:
                    self._sleep(self.backoff * (2 ** attempt))
        return OrderedDict((("url", url), ("outcome", UNKNOWN), ("status", None),
                            ("detail", "no answer after %d attempts (%s); UNKNOWN is not a failure "
                                       "and not a pass" % (self.retries + 1, last))))


def verify_release(manifest: Mapping, *, base_url: str, probe: Optional[HTTPProbe] = None,
                   expected_deploy_id: Optional[str] = None,
                   host_state: Optional[Mapping] = None,
                   sample: int = 3, hub_routes: Optional[Mapping[str, str]] = None
                   ) -> "OrderedDict[str, Any]":
    """005's nine checks, asked of a real origin over HTTP.

    ``base_url`` is whatever origin the caller authorises -- a local static
    server, a per-deploy Netlify URL, or production. This function does not
    decide that production is a safe target; the caller does.
    """
    started = time.perf_counter()
    probe = probe or HTTPProbe()
    checks: "OrderedDict[str, Any]" = OrderedDict()
    unknowns: List[str] = []

    def record(name: str, outcome: str, detail: str = "", **extra: Any) -> None:
        row = OrderedDict((("outcome", outcome), ("detail", detail)))
        row.update(extra)
        checks[name] = row
        if outcome == UNKNOWN:
            unknowns.append(name)

    markets = list(manifest.get("participating_markets") or ())
    routes = dict(hub_routes or {m: "/pet-friendly-hotels/%s/" % m for m in markets})
    delta_market = (manifest.get("intended_delta") or {}).get("market_id")

    sitemap = probe.get(base_url.rstrip("/") + "/sitemap.xml")
    if sitemap["outcome"] == OK:
        text = sitemap["body"].decode("utf-8", "replace")
        locs = re.findall(r"<loc>([^<]+)</loc>", text)
        served = {re.sub(r"^https?://[^/]+", "", loc) for loc in locs}
        record("release_marker", OK if locs else FAILED,
               "sitemap lists %d routes; expected %s" % (len(locs), manifest.get("sitemap_route_count")),
               served_routes=len(locs),
               matches_manifest=len(locs) == manifest.get("sitemap_route_count"))
        missing_markets = sorted(m for m in markets if routes.get(m) not in served)
        record("membership", OK if not missing_markets else FAILED,
               "markets with no hub route in the sitemap: %s" % missing_markets)
        if delta_market:
            record("sitemap_includes_changed_market",
                   OK if routes.get(delta_market) in served else FAILED, str(routes.get(delta_market)))
        else:
            record("sitemap_includes_changed_market", OK, "no market delta in this release")
    else:
        for name in ("release_marker", "membership", "sitemap_includes_changed_market"):
            record(name, sitemap["outcome"], sitemap.get("detail", ""))

    if delta_market:
        hub = probe.get(base_url.rstrip("/") + routes.get(delta_market, "/"))
        record("changed_market_hub", hub["outcome"], str(hub.get("detail") or hub.get("status")))
        profiles = [r for r in (manifest.get("sample_profile_routes") or [])][:sample]
        if profiles:
            results = [probe.get(base_url.rstrip("/") + r) for r in profiles]
            worst = (FAILED if any(r["outcome"] == FAILED for r in results)
                     else UNKNOWN if any(r["outcome"] == UNKNOWN for r in results) else OK)
            record("changed_market_profiles", worst, "%d sampled" % len(results))
        else:
            record("changed_market_profiles", OK, "no profile sample supplied")
    else:
        record("changed_market_hub", OK, "no market delta")
        record("changed_market_profiles", OK, "no market delta")

    unrelated = [m for m in markets if m != delta_market]
    if unrelated:
        probe_market = unrelated[0]
        result = probe.get(base_url.rstrip("/") + routes.get(probe_market, "/"))
        record("unrelated_market_sample", result["outcome"],
               "%s -> %s" % (probe_market, result.get("status")))
        record("unrelated_route_count",
               OK if checks.get("release_marker", {}).get("matches_manifest") else
               checks.get("release_marker", {}).get("outcome", UNKNOWN),
               "the sitemap route count is the release's own count")
    else:
        record("unrelated_market_sample", OK, "single-market release")
        record("unrelated_route_count", OK, "single-market release")

    asset = probe.get(base_url.rstrip("/") + "/robots.txt")
    record("asset_integrity", asset["outcome"], str(asset.get("status")))

    if expected_deploy_id:
        actual = (host_state or {}).get("host_deployment_id")
        record("host_deployment_id", OK if actual == expected_deploy_id else FAILED,
               "host reports %s, the activation recorded %s" % (actual, expected_deploy_id))
    else:
        record("host_deployment_id", UNKNOWN, "no deployment id supplied to compare")

    failing = sorted(n for n, r in checks.items() if r["outcome"] == FAILED)
    outcome = FAILED if failing else (UNKNOWN if unknowns else OK)
    return OrderedDict((
        ("schema", VERIFICATION_SCHEMA),
        ("base_url", base_url),
        ("checks", checks),
        ("failing", failing),
        ("unknown", sorted(unknowns)),
        ("outcome", outcome),
        ("passed", outcome == OK),
        ("rollback_permitted", outcome == FAILED),
        ("requests", len(probe.requests)),
        ("seconds", round(time.perf_counter() - started, 3)),
        ("note", "UNKNOWN never permits a rollback: reconcile the host first. Only a definite "
                 "FAILED on a critical check does, and only while the failed release is still current."),
    ))


def main(argv: Optional[Sequence[str]] = None) -> int:  # pragma: no cover - CLI
    parser = argparse.ArgumentParser(
        description="ATLAS-THROUGHPUT-006 -- host adapter description and live HTTP verification")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("describe-host", help="the deployment host's semantics, as read from this repo")
    p = sub.add_parser("verify", help="run the nine checks against an origin")
    p.add_argument("--manifest", required=True)
    p.add_argument("--base-url", required=True)
    args = parser.parse_args(argv)
    if args.command == "describe-host":
        print(SMP.canonical_json(NetlifyHost().describe()))
        return 0
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8-sig"))
    result = verify_release(manifest, base_url=args.base_url)
    print(SMP.canonical_json(OrderedDict((k, v) for k, v in result.items() if k != "checks")))
    return 0 if result["passed"] else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
