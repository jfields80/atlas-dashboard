"""PTF-MEASUREMENT-001 -- the measurement configuration contract.

WHY THIS EXISTS
---------------
``commercial_actions.py`` has carried a complete, vendor-neutral analytics
contract since AES-SITE-001: ten event names, ten dimensions, and
``window.ptfAnalytics.emit`` forwarding to ``window.__ptfAnalyticsProvider``.
Nothing ever assigned that provider. Every emit on the live site is a no-op,
no page carries a ``page_view``, and the only pages that load the contract at
all are the ``/go/`` interstitials and the hotel category page.

This module is where a provider WOULD be attached -- and, deliberately, is
not. It owns:

* the committed configuration (``deploy/netlify/measurement.json``), loaded
  and validated fail-closed;
* the build-time state idiom this layer already uses (``set_go_market_prefix``,
  ``set_market_labels``): one explicit ``set_measurement_config`` per build;
* the page injection helper, whose DISABLED path is the identity function on
  the HTML bytes -- the property the whole work order rests on;
* the ENABLED path's shape, so a later release can turn it on without
  re-deciding anything: a provider script on content pages, an adapter that
  assigns ``__ptfAnalyticsProvider``, a ``page_view`` per page, and an INLINE
  ``navigator.sendBeacon`` adapter on ``/go/`` pages;
* ``build_id``: a market-local, content-bound release identity.

THE /go/ RACE
-------------
A ``/go/`` page runs ``ptfAnalytics.emit(...)`` and then, on the very next
statement, ``location.replace(destination)``. A vendor script loaded with
``defer`` or ``async`` is not initialised by then, so a conventional tag would
lose essentially every outbound click -- the one event the site exists to
count. The enabled path therefore never depends on an external script being
ready on a ``/go/`` page: the provider there is an inline function that hands
the event to ``navigator.sendBeacon``, which the browser delivers after the
navigation has begun.

BUILD ID
--------
``build_id`` is the first twelve hex characters of the owning market's
committed policy-package SHA-256 (the ``policy_package.expected_sha256`` its
release contract pins; the package file itself when no contract exists). It
is deterministic, carries no clock, and -- the constraint that decides the
derivation -- does NOT depend on which other markets are in the bundle, so
``test_adding_a_market_moves_no_earlier_market_owned_byte`` keeps holding
once measurement is enabled. Global pages use the anchor market's id.

DISABLED BY DEFAULT
-------------------
``enabled: false`` with ``provider.kind: none`` produces NO generated HTML
change: no script, no provider, no ``page_view``, no ``build_id`` markup. The
acceptance test for this work order is that the composed production bundle
hash does not move.

Pure and deterministic: no network, no clock, no environment reads.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import urlsplit

REPO_ROOT = Path(__file__).resolve().parents[2]

MEASUREMENT_CONFIG_SCHEMA = "ptf-measurement-config/1.0"
CONFIG_PATH = REPO_ROOT / "deploy" / "netlify" / "measurement.json"

PROVIDER_KIND_NONE = "none"
PROVIDER_KIND_BEACON_SCRIPT = "beacon_script"
PROVIDER_KINDS = frozenset({PROVIDER_KIND_NONE, PROVIDER_KIND_BEACON_SCRIPT})

#: Length of the truncated policy-package hash used as ``build_id``.
BUILD_ID_LENGTH = 12

#: The attribute that marks an injected measurement block. The once-per-page
#: gate counts it; it is never present while measurement is disabled.
SNIPPET_MARKER = 'data-ptf-measurement="page"'
GO_ADAPTER_MARKER = "/* ptf-measurement go-adapter */"

#: Page types the injection helper understands. ``go_redirect`` is listed so
#: a caller cannot pass a /go/ page through the content-page path by accident.
PAGE_TYPE_HOME = "home"
PAGE_TYPE_EDITORIAL = "editorial"
PAGE_TYPE_CATEGORY = "category"
PAGE_TYPE_MARKET_HUB = "market_hub"
PAGE_TYPE_CORRIDOR = "corridor"
PAGE_TYPE_POLICY_COMPARISON = "policy_comparison"
PAGE_TYPE_HOTEL_PROFILE = "hotel_profile"
PAGE_TYPE_PLACE_PROFILE = "place_profile"
PAGE_TYPE_GO_REDIRECT = "go_redirect"
PAGE_TYPES = frozenset({
    PAGE_TYPE_HOME, PAGE_TYPE_EDITORIAL, PAGE_TYPE_CATEGORY, PAGE_TYPE_MARKET_HUB,
    PAGE_TYPE_CORRIDOR, PAGE_TYPE_POLICY_COMPARISON, PAGE_TYPE_HOTEL_PROFILE,
    PAGE_TYPE_PLACE_PROFILE, PAGE_TYPE_GO_REDIRECT,
})

#: Events a content page emits on load, by page type, AFTER the universal
#: ``page_view``. Declared here rather than inferred so the enabled output is
#: a committed decision.
_PAGE_TYPE_EXTRA_EVENT = {
    PAGE_TYPE_HOTEL_PROFILE: "listing_profile_view",
    PAGE_TYPE_POLICY_COMPARISON: "policy_comparison_view",
}

_ALLOWED_TOP_KEYS = frozenset({
    "schema", "what_this_is", "enabled", "provider", "build_id", "go_pages",
})
_ALLOWED_PROVIDER_KEYS = frozenset({
    "kind", "script_src", "event_endpoint", "site_domain", "allowed_hosts",
})
_HOST_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$")
_HEAD_CLOSE = "</head>"


class MeasurementConfigError(ValueError):
    """The committed configuration cannot be trusted; the build stops."""


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class ProviderConfig:
    kind: str = PROVIDER_KIND_NONE
    script_src: str = ""
    event_endpoint: str = ""
    site_domain: str = ""
    allowed_hosts: Tuple[str, ...] = ()


@dataclass(frozen=True)
class MeasurementConfig:
    enabled: bool = False
    provider: ProviderConfig = field(default_factory=ProviderConfig)
    build_id_length: int = BUILD_ID_LENGTH

    @property
    def active(self) -> bool:
        """Enabled AND backed by a real provider. ``enabled: true`` with
        ``kind: none`` never validates, so this is equivalent to ``enabled``
        for a loaded config; the double condition is what makes a hand-built
        config in a test unable to inject by accident."""
        return bool(self.enabled) and self.provider.kind != PROVIDER_KIND_NONE


DISABLED = MeasurementConfig()


def _host_of(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def validate_config_document(doc: Mapping) -> List[str]:
    """Every way the document is wrong, or ``[]``. Fail-closed: unknown keys,
    wrong types and an enabled config without a usable provider all count."""
    problems: List[str] = []
    if not isinstance(doc, Mapping):
        return ["document is not an object"]
    if doc.get("schema") != MEASUREMENT_CONFIG_SCHEMA:
        problems.append("schema is %r, expected %r"
                        % (doc.get("schema"), MEASUREMENT_CONFIG_SCHEMA))
    unknown = sorted(set(doc) - _ALLOWED_TOP_KEYS)
    if unknown:
        problems.append("unknown top-level keys: %s" % unknown)
    enabled = doc.get("enabled")
    if not isinstance(enabled, bool):
        problems.append("enabled must be a boolean, got %r" % (enabled,))
        enabled = False

    provider = doc.get("provider")
    if not isinstance(provider, Mapping):
        problems.append("provider must be an object")
        provider = {}
    unknown = sorted(set(provider) - _ALLOWED_PROVIDER_KEYS)
    if unknown:
        problems.append("unknown provider keys: %s" % unknown)
    kind = provider.get("kind")
    if kind not in PROVIDER_KINDS:
        problems.append("provider.kind is %r, expected one of %s"
                        % (kind, sorted(PROVIDER_KINDS)))
    script_src = provider.get("script_src", "")
    endpoint = provider.get("event_endpoint", "")
    site_domain = provider.get("site_domain", "")
    hosts = provider.get("allowed_hosts", [])
    for name, value in (("script_src", script_src), ("event_endpoint", endpoint),
                        ("site_domain", site_domain)):
        if not isinstance(value, str):
            problems.append("provider.%s must be a string" % name)
    if not isinstance(hosts, list) or any(not isinstance(h, str) for h in hosts):
        problems.append("provider.allowed_hosts must be a list of strings")
        hosts = []
    for host in hosts:
        if not _HOST_RE.match(host):
            problems.append("provider.allowed_hosts entry is not a bare lowercase "
                            "hostname: %r" % host)

    if kind == PROVIDER_KIND_NONE:
        # A "none" provider that still names a script or endpoint is a config
        # somebody half-edited; refuse it rather than guess which half wins.
        if script_src or endpoint or hosts:
            problems.append("provider.kind none must carry no script_src, "
                            "event_endpoint or allowed_hosts")
        if enabled:
            problems.append("enabled is true but provider.kind is none")
    elif kind == PROVIDER_KIND_BEACON_SCRIPT:
        if not hosts:
            problems.append("beacon_script provider needs allowed_hosts")
        for name, value in (("script_src", script_src), ("event_endpoint", endpoint)):
            if not isinstance(value, str) or not value:
                problems.append("beacon_script provider needs provider.%s" % name)
                continue
            parts = urlsplit(value)
            if parts.scheme != "https" or not parts.hostname:
                problems.append("provider.%s must be an https URL" % name)
            elif _host_of(value) not in hosts:
                problems.append("provider.%s host %r is not in allowed_hosts"
                                % (name, _host_of(value)))
        if not site_domain:
            problems.append("beacon_script provider needs provider.site_domain")

    build_id = doc.get("build_id", {})
    if build_id != {} and build_id is not None:
        if not isinstance(build_id, Mapping):
            problems.append("build_id must be an object")
        else:
            if build_id.get("source") not in (None, "market_policy_package_sha256"):
                problems.append("build_id.source %r is not supported"
                                % build_id.get("source"))
            length = build_id.get("length", BUILD_ID_LENGTH)
            if not isinstance(length, int) or not (8 <= length <= 64):
                problems.append("build_id.length must be an integer in [8, 64]")
    go_pages = doc.get("go_pages", {})
    if go_pages not in ({}, None):
        if not isinstance(go_pages, Mapping) or \
                go_pages.get("adapter") not in (None, "inline_send_beacon"):
            problems.append("go_pages.adapter must be inline_send_beacon")
    return problems


def config_from_document(doc: Mapping) -> MeasurementConfig:
    problems = validate_config_document(doc)
    if problems:
        raise MeasurementConfigError("measurement config refused: %s"
                                     % "; ".join(problems))
    provider = doc["provider"]
    length = (doc.get("build_id") or {}).get("length", BUILD_ID_LENGTH)
    return MeasurementConfig(
        enabled=bool(doc["enabled"]),
        provider=ProviderConfig(
            kind=provider["kind"],
            script_src=provider.get("script_src", ""),
            event_endpoint=provider.get("event_endpoint", ""),
            site_domain=provider.get("site_domain", ""),
            allowed_hosts=tuple(provider.get("allowed_hosts", [])),
        ),
        build_id_length=length,
    )


def load_measurement_config(path: Optional[Path] = None) -> MeasurementConfig:
    """The committed configuration, validated. A missing or malformed file
    raises: a build that cannot read its measurement contract must not decide
    for itself whether measurement is on."""
    path = Path(path) if path is not None else CONFIG_PATH
    if not path.is_file():
        raise MeasurementConfigError("no measurement config at %s" % path)
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except ValueError as exc:
        raise MeasurementConfigError("measurement config is not JSON: %s" % exc)
    return config_from_document(doc)


def config_sha256(path: Optional[Path] = None) -> str:
    path = Path(path) if path is not None else CONFIG_PATH
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------- #
# Build state (the layer's established idiom: one explicit call per build).
# --------------------------------------------------------------------------- #

_CONFIG: MeasurementConfig = DISABLED


def set_measurement_config(config: Optional[MeasurementConfig] = None) -> None:
    """Scope every subsequent injection under ``config``. ``None`` resets to
    the disabled default, which is also what a build that never calls this
    gets -- so forgetting the call can only ever UNDER-measure."""
    global _CONFIG
    _CONFIG = config if config is not None else DISABLED


def get_measurement_config() -> MeasurementConfig:
    return _CONFIG


# --------------------------------------------------------------------------- #
# build_id
# --------------------------------------------------------------------------- #

def build_id_for(market_id: str, *, length: Optional[int] = None) -> str:
    """The market-local release identity (see module docstring).

    Source of truth, in order: the market's committed release contract
    (``policy_package.expected_sha256``), else the committed package file's
    own hash, else ``""`` (a market with no published package has nothing to
    identify). Never reads another market's files.
    """
    from scripts.pettripfinder.release_contracts import (
        ReleaseContractError, contract_path, load_contract,
    )
    from scripts.pettripfinder.site_data import published_facts_path

    length = length or _CONFIG.build_id_length
    sha = ""
    if contract_path(market_id).is_file():
        try:
            sha = str((load_contract(market_id).get("policy_package") or {})
                      .get("expected_sha256") or "")
        except ReleaseContractError:
            sha = ""
    if not sha:
        package = published_facts_path(market_id)
        if package.is_file():
            sha = hashlib.sha256(package.read_bytes()).hexdigest()
    if not sha:
        return ""
    if not re.match(r"^[0-9a-f]{64}$", sha):
        raise MeasurementConfigError(
            "policy package sha for %s is not a sha256 hex digest: %r"
            % (market_id, sha))
    return sha[:length]


# --------------------------------------------------------------------------- #
# Page context and route classification
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class PageContext:
    market: str
    page_type: str
    route: str
    listing_id: str = ""
    category: str = ""
    corridor: str = ""
    verification_status: str = ""
    build_id: str = ""

    def dimensions(self) -> Dict[str, str]:
        """The event payload, in the contract's key set. Every key from
        ``EVENT_DIMENSIONS`` is present (values may be ``""``)."""
        return {
            "market": self.market, "page_type": self.page_type,
            "route": self.route, "listing_id": self.listing_id,
            "listing_state": self.verification_status,
            "category": self.category, "corridor": self.corridor,
            "action_position": "page_load",
            "verification_status": self.verification_status,
            "affiliate_provider": "", "build_id": self.build_id,
        }


def classify_route(route: str, *, market_slug: str, legacy_unprefixed: bool,
                   published_categories: Sequence[str] = ()) -> str:
    """Which page type a route is, from its shape alone.

    The generator knows exactly what it wrote at each route; this is the
    fallback for a post-pass that sees only the file tree, and it is exact
    for every route shape the generator produces today.
    """
    if route.startswith("/go/"):
        return PAGE_TYPE_GO_REDIRECT
    if route == "/":
        return PAGE_TYPE_HOME
    if route in ("/about/", "/contact/", "/methodology/"):
        return PAGE_TYPE_EDITORIAL
    parts = [p for p in route.split("/") if p]
    category_root = "pet-friendly-hotels"
    if parts[0] != category_root and parts[0] in set(published_categories):
        return PAGE_TYPE_CATEGORY if len(parts) == 1 else PAGE_TYPE_PLACE_PROFILE
    if parts[0] != category_root:
        return PAGE_TYPE_EDITORIAL
    rest = parts[1:]
    if not legacy_unprefixed:
        if not rest:
            return PAGE_TYPE_CATEGORY
        if rest[0] != market_slug:
            return PAGE_TYPE_EDITORIAL
        rest = rest[1:]
        if not rest:
            return PAGE_TYPE_MARKET_HUB
    else:
        if not rest:
            return PAGE_TYPE_CATEGORY
    if rest == ["policy-comparison"]:
        return PAGE_TYPE_POLICY_COMPARISON
    if len(rest) == 1:
        # Corridor pages and hotel profiles share one depth; the caller that
        # knows its corridor slugs refines this. Profiles dominate.
        return PAGE_TYPE_HOTEL_PROFILE
    return PAGE_TYPE_EDITORIAL


# --------------------------------------------------------------------------- #
# Snippets (enabled path). Nothing here runs while disabled.
# --------------------------------------------------------------------------- #

def _js_safe(obj) -> str:
    # Same rule as commercial_actions: "</" inside a JS string would let the
    # HTML parser close the <script> early.
    return json.dumps(obj, sort_keys=True).replace("</", "<\\/")


def provider_adapter_js(config: MeasurementConfig) -> str:
    """The inline ``window.__ptfAnalyticsProvider`` for CONTENT pages.

    Delivers through ``navigator.sendBeacon`` when available (the same path
    the /go/ adapter uses, so the two never disagree about the wire format)
    and falls back to a keepalive ``fetch``. The vendor's own deferred script,
    if it exposes a richer API, may replace this function once it loads;
    until then nothing is lost.
    """
    if not config.active:
        return ""
    return (
        "window.__ptfAnalyticsProvider=function(n,d){try{"
        "var p=JSON.stringify({name:n,url:location.href,domain:%s,"
        "referrer:document.referrer||'',props:d||{}});"
        "if(navigator.sendBeacon){navigator.sendBeacon(%s,new Blob([p],{type:'text/plain'}));}"
        "else if(window.fetch){fetch(%s,{method:'POST',body:p,keepalive:true,"
        "headers:{'Content-Type':'text/plain'}});}"
        "}catch(e){}};"
    ) % (_js_safe(config.provider.site_domain), _js_safe(config.provider.event_endpoint),
         _js_safe(config.provider.event_endpoint))


def inline_beacon_provider_js(config: MeasurementConfig) -> str:
    """The inline ``/go/`` adapter. No external script, no readiness wait:
    ``sendBeacon`` is the only delivery path that survives the immediate
    ``location.replace`` that follows the emit. ``""`` while disabled, which
    is what keeps today's /go/ bytes unchanged."""
    if not config.active:
        return ""
    return (
        GO_ADAPTER_MARKER +
        "window.__ptfAnalyticsProvider=function(n,d){try{"
        "var p=JSON.stringify({name:n,url:location.href,domain:%s,"
        "referrer:document.referrer||'',props:d||{}});"
        "if(navigator.sendBeacon){navigator.sendBeacon(%s,new Blob([p],{type:'text/plain'}));}"
        "}catch(e){}};"
    ) % (_js_safe(config.provider.site_domain), _js_safe(config.provider.event_endpoint))


def provider_head_snippet(config: MeasurementConfig, ctx: PageContext) -> str:
    """The block a CONTENT page gets before ``</head>`` when measurement is
    active: the vendor script (deferred -- page load is never blocked), the
    adapter, the shared ``ptfAnalytics`` interface, then the page's events."""
    if not config.active:
        return ""
    if ctx.page_type == PAGE_TYPE_GO_REDIRECT:
        raise MeasurementConfigError("a /go/ page takes the inline adapter, "
                                     "never the content-page snippet")
    from scripts.pettripfinder.commercial_actions import ANALYTICS_JS
    dims = ctx.dimensions()
    events = ["page_view"]
    extra = _PAGE_TYPE_EXTRA_EVENT.get(ctx.page_type)
    if extra:
        events.append(extra)
    emits = "".join("ptfAnalytics.emit(%s,%s);" % (_js_safe(e), _js_safe(dims))
                    for e in events)
    return (
        '<script defer src="%s" data-domain="%s" %s></script>'
        "<script %s>%s%s\n%s</script>"
    ) % (config.provider.script_src.replace('"', "&quot;"),
         config.provider.site_domain.replace('"', "&quot;"), SNIPPET_MARKER,
         SNIPPET_MARKER, provider_adapter_js(config), ANALYTICS_JS, emits)


def inject_page_measurement(html_text: str, ctx: PageContext,
                            config: Optional[MeasurementConfig] = None) -> str:
    """Returns the page with its measurement block, or -- while disabled --
    the INPUT, byte for byte, with no read of the page at all.

    Idempotent: a page that already carries the marker is returned unchanged,
    so a post-pass that runs twice cannot double-count. A content page with no
    ``</head>`` is a page this module does not understand; it raises rather
    than silently leaving one page unmeasured.
    """
    config = config if config is not None else _CONFIG
    if not config.active:
        return html_text
    if ctx.page_type not in PAGE_TYPES:
        raise MeasurementConfigError("unknown page_type %r" % ctx.page_type)
    if ctx.page_type == PAGE_TYPE_GO_REDIRECT:
        return html_text
    if SNIPPET_MARKER in html_text:
        return html_text
    if _HEAD_CLOSE not in html_text:
        raise MeasurementConfigError("no </head> on %s; cannot measure it" % ctx.route)
    return html_text.replace(_HEAD_CLOSE, provider_head_snippet(config, ctx) + _HEAD_CLOSE, 1)


# --------------------------------------------------------------------------- #
# Gates. Shared by the composed assembler and the single-market assembler.
# --------------------------------------------------------------------------- #

GATE_CONFIG_VALID = "measurement.config_valid"
GATE_SNIPPET_ONCE = "measurement.snippet_once_per_content_page"
GATE_NO_EXTERNAL_WHEN_DISABLED = "measurement.no_external_script_when_disabled"
MEASUREMENT_GATES = (GATE_CONFIG_VALID, GATE_SNIPPET_ONCE,
                     GATE_NO_EXTERNAL_WHEN_DISABLED)

_EXTERNAL_SCRIPT_RE = re.compile(
    r'<script\b[^>]*\bsrc\s*=\s*["\'](?:https?:)?//', re.IGNORECASE)


def _route_of(root: Path, path: Path) -> str:
    rel = path.parent.relative_to(root).as_posix()
    return "/" if rel == "." else "/%s/" % rel


def run_measurement_gates(gates, gate: Callable, site_dir: Path,
                          config_path: Optional[Path] = None) -> MeasurementConfig:
    """Record the three measurement gates into ``gates`` via the assembler's
    own ``_gate`` callable. Returns the loaded config (or DISABLED when the
    config itself failed, in which case the first gate already failed)."""
    site_dir = Path(site_dir)
    try:
        config = load_measurement_config(config_path)
        gate(gates, GATE_CONFIG_VALID, True, "enabled=%s kind=%s"
             % (config.enabled, config.provider.kind))
    except MeasurementConfigError as exc:
        config = DISABLED
        gate(gates, GATE_CONFIG_VALID, False, str(exc))

    wrong: List[str] = []
    external: List[str] = []
    for page in sorted(site_dir.rglob("*.html")):
        route = _route_of(site_dir, page)
        text = page.read_text(encoding="utf-8")
        if not route.startswith("/go/"):
            count = text.count(SNIPPET_MARKER)
            expected = 2 if config.active else 0   # marker sits on both tags
            if count != expected:
                wrong.append("%s carries %d marker(s), expected %d"
                             % (route, count, expected))
        if not config.active and _EXTERNAL_SCRIPT_RE.search(text):
            external.append(route)
    gate(gates, GATE_SNIPPET_ONCE, not wrong, "; ".join(wrong[:6]))
    gate(gates, GATE_NO_EXTERNAL_WHEN_DISABLED, not external,
         "external <script src> while disabled: %s" % external[:6])
    return config


__all__ = [
    "MEASUREMENT_CONFIG_SCHEMA", "CONFIG_PATH", "PROVIDER_KIND_NONE",
    "PROVIDER_KIND_BEACON_SCRIPT", "PROVIDER_KINDS", "BUILD_ID_LENGTH",
    "SNIPPET_MARKER", "GO_ADAPTER_MARKER", "PAGE_TYPES",
    "PAGE_TYPE_HOME", "PAGE_TYPE_EDITORIAL", "PAGE_TYPE_CATEGORY",
    "PAGE_TYPE_MARKET_HUB", "PAGE_TYPE_CORRIDOR", "PAGE_TYPE_POLICY_COMPARISON",
    "PAGE_TYPE_HOTEL_PROFILE", "PAGE_TYPE_PLACE_PROFILE", "PAGE_TYPE_GO_REDIRECT",
    "MeasurementConfigError", "ProviderConfig", "MeasurementConfig", "DISABLED",
    "validate_config_document", "config_from_document", "load_measurement_config",
    "config_sha256", "set_measurement_config", "get_measurement_config",
    "build_id_for", "PageContext", "classify_route", "provider_adapter_js",
    "inline_beacon_provider_js", "provider_head_snippet", "inject_page_measurement",
    "GATE_CONFIG_VALID", "GATE_SNIPPET_ONCE", "GATE_NO_EXTERNAL_WHEN_DISABLED",
    "MEASUREMENT_GATES", "run_measurement_gates",
]
