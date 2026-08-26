"""AES-SITE-001 (Task 10/11) -- commercial action layer + analytics event
contract.

Static-site-safe outbound action redirects. Every ``/go/<listing-id>/
<action>/`` page is generated at BUILD TIME ONLY from an already-approved
listing's own real official URL -- there is no user-controlled destination
parameter anywhere, so the classic open-redirect attack class (an attacker
supplying an arbitrary ``?url=`` to redirect through a trusted domain) is
structurally impossible here, not merely filtered. ``build_go_page`` refuses
to build a redirect to anything but an ``https``/``http`` URL already present
on the source listing record.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from urllib.parse import urlsplit

ACTION_OFFICIAL_WEBSITE = "official-website"
ACTION_BOOKING = "booking"
ACTION_DIRECTIONS = "directions"
ACTION_CALL = "call"
ACTION_REPORT_CHANGE = "report-change"

ACTION_TYPES = frozenset({
    ACTION_OFFICIAL_WEBSITE, ACTION_BOOKING, ACTION_DIRECTIONS,
    ACTION_CALL, ACTION_REPORT_CHANGE,
})

_SAFE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,79}$")


# --------------------------------------------------------------------------- #
# Analytics event contract (Task 11). Vendor-neutral: a bare JS interface
# with a no-op default; a real provider is attached only via
# ``window.__ptfAnalyticsProvider`` (a repository-configured integration
# point, never a hardcoded personal ID here).
# --------------------------------------------------------------------------- #

EVENT_PAGE_VIEW = "page_view"
EVENT_LISTING_IMPRESSION = "listing_impression"
EVENT_LISTING_PROFILE_VIEW = "listing_profile_view"
EVENT_FILTER_APPLIED = "filter_applied"
EVENT_OUTBOUND_OFFICIAL_CLICK = "outbound_official_click"
EVENT_OUTBOUND_BOOKING_CLICK = "outbound_booking_click"
EVENT_DIRECTIONS_CLICK = "directions_click"
EVENT_PHONE_CLICK = "phone_click"
EVENT_REPORT_CHANGE_CLICK = "report_change_click"
EVENT_POLICY_COMPARISON_VIEW = "policy_comparison_view"

EVENT_TYPES = frozenset({
    EVENT_PAGE_VIEW, EVENT_LISTING_IMPRESSION, EVENT_LISTING_PROFILE_VIEW,
    EVENT_FILTER_APPLIED, EVENT_OUTBOUND_OFFICIAL_CLICK,
    EVENT_OUTBOUND_BOOKING_CLICK, EVENT_DIRECTIONS_CLICK, EVENT_PHONE_CLICK,
    EVENT_REPORT_CHANGE_CLICK, EVENT_POLICY_COMPARISON_VIEW,
})

# Required dimensions (Task 11) -- every emitted event carries this shape
# (values may be "" when not applicable to that event, but the KEY is
# always present, so a downstream consumer's schema never has to guess).
EVENT_DIMENSIONS = (
    "market", "page_type", "route", "listing_id", "listing_state",
    "category", "corridor", "action_position", "verification_status",
    "affiliate_provider",
    # PTF-MEASUREMENT-001: the owning market's release identity (the first
    # twelve hex characters of its committed policy-package SHA-256 --
    # ``measurement.build_id_for``). Market-local on purpose: adding another
    # market to the bundle moves no byte of this one. The key is emitted only
    # when a build supplies it, so the live /go/ pages generated before
    # measurement was enabled are byte-identical to the ones generated after
    # with measurement still disabled.
    "build_id",
)

#: Dimensions an event MAY carry beyond the required set. ``filter_applied``
#: has carried ``filter_value`` since AES-SITE-001 without declaring it; a
#: consumer's schema should know the key exists.
EVENT_OPTIONAL_DIMENSIONS = ("filter_value",)

#: The ``rel`` an affiliate booking fallback link carries (search engines ask
#: for ``sponsored`` on paid links). Every other outbound link keeps the
#: ``noopener`` it has always had.
REL_AFFILIATE_LINK = "nofollow sponsored noopener"

_ACTION_TO_EVENT = {
    ACTION_OFFICIAL_WEBSITE: EVENT_OUTBOUND_OFFICIAL_CLICK,
    ACTION_BOOKING: EVENT_OUTBOUND_BOOKING_CLICK,
    ACTION_DIRECTIONS: EVENT_DIRECTIONS_CLICK,
    ACTION_CALL: EVENT_PHONE_CLICK,
    ACTION_REPORT_CHANGE: EVENT_REPORT_CHANGE_CLICK,
}

ANALYTICS_JS = """\
window.ptfAnalytics = window.ptfAnalytics || (function () {
  function emit(eventName, dimensions) {
    var provider = window.__ptfAnalyticsProvider;
    if (typeof provider === "function") {
      try { provider(eventName, dimensions || {}); } catch (e) { /* never block the page */ }
    }
  }
  return { emit: emit };
})();
"""


@dataclass(frozen=True)
class AffiliateConfig:
    """Empty/default = no affiliate program configured (doctrine: booking
    action falls back to the real official/property URL, honestly labeled,
    no fabricated "best price"/availability claim)."""

    network: str = ""
    campaign: str = ""
    param_name: str = ""
    param_value: str = ""

    @property
    def configured(self) -> bool:
        return bool(self.network and self.param_name and self.param_value)


def apply_affiliate_params(url: str, config: AffiliateConfig) -> str:
    if not config.configured or not url:
        return url
    sep = "&" if "?" in url else "?"
    return "%s%s%s=%s" % (url, sep, config.param_name, config.param_value)


def build_redirect_target(action: str, *, official_url: str, phone: str,
                          config: Optional[AffiliateConfig] = None,
                          booking_destination: str = "") -> str:
    """The REAL destination for one action, given an already-approved
    listing. Never accepts caller-supplied arbitrary URLs.

    ``booking_destination`` (PTF-MEASUREMENT-001 Phase 1b) is an affiliate
    destination ALREADY RESOLVED by ``affiliate_destinations.destination_for``
    -- enrolled provider, allowlisted host, identity-bound -- and is used for
    the booking action only. Empty, the default, keeps today's behaviour: the
    official URL, with the legacy one-parameter ``AffiliateConfig`` applied
    when one is configured (none is).
    """
    config = config or AffiliateConfig()
    if action in (ACTION_OFFICIAL_WEBSITE, ACTION_BOOKING):
        target = official_url
        if action == ACTION_BOOKING:
            target = booking_destination or apply_affiliate_params(official_url, config)
        return target
    if action == ACTION_CALL:
        digits = re.sub(r"\D", "", phone or "")
        return "tel:%s" % digits if digits else ""
    if action == ACTION_DIRECTIONS:
        return ""  # caller supplies a maps URL built from the approved address
    if action == ACTION_REPORT_CHANGE:
        return "/contact/"
    return ""


def _validate_destination(url: str) -> bool:
    """Fail-closed destination check: only http(s) with a real host, or an
    approved internal path, or tel:. Never javascript:/data:/relative
    parent-traversal tricks."""
    if not url:
        return False
    if url.startswith("tel:"):
        return bool(re.match(r"^tel:\+?\d{7,15}$", url))
    if url.startswith("/"):
        return True
    parts = urlsplit(url)
    return parts.scheme in ("http", "https") and bool(parts.hostname)


#: PTF-MULTI-MARKET-ASSEMBLER-001 (Phase E section 18). The /go/ namespace is
#: flat, so two markets holding a hotel with the same slug -- "hampton-inn-troy"
#: is not an unusual name -- would claim the same interstitial route, and the
#: combined bundle would resolve it by whichever fragment copied last. The
#: frozen strategy scopes prefixed markets:
#:
#:     Columbus legacy   /go/{hotel_slug}/{action}/
#:     prefixed markets  /go/{market_slug}/{hotel_slug}/{action}/
#:
#: The prefix is build state rather than a parameter because /go/ hrefs are
#: emitted from a dozen places inside the approved renderers, and threading a
#: market through markup builders that have no other reason to know about one
#: is how a renderer acquires a second identity. This follows the established
#: idiom in this layer (``set_market_labels``, ``set_published_categories``):
#: one explicit call per build, at the top, from the builder that owns it.
_GO_MARKET_PREFIX = ""


def set_go_market_prefix(prefix: str = "") -> None:
    """Scope every subsequent /go/ route under ``prefix`` (a market slug).

    Pass ``""`` for a legacy_unprefixed market, which keeps Columbus's live
    interstitial routes byte-identical.
    """
    global _GO_MARKET_PREFIX
    prefix = (prefix or "").strip("/")
    if prefix and not _SAFE_ID_RE.match(prefix):
        raise ValueError("unsafe market prefix for /go/ route: %r" % prefix)
    _GO_MARKET_PREFIX = prefix


def go_market_prefix() -> str:
    """The prefix currently in force (``""`` when unscoped)."""
    return _GO_MARKET_PREFIX


def go_route(listing_id: str, action: str) -> str:
    if not _SAFE_ID_RE.match(listing_id):
        raise ValueError("unsafe listing_id for /go/ route: %r" % listing_id)
    if action not in ACTION_TYPES:
        raise ValueError("unknown action type: %r" % action)
    if _GO_MARKET_PREFIX:
        return "/go/%s/%s/%s/" % (_GO_MARKET_PREFIX, listing_id, action)
    return "/go/%s/%s/" % (listing_id, action)


#: The market an analytics dimension names when no caller supplies one.
#:
#: This is a DEFAULT, not the market. It stayed correct for as long as
#: PetTripFinder had one market, and PTF-DAYTON-INTEGRATION-001 is where that
#: stopped being true: every one of the Dayton build's 165 /go/ pages emitted
#: ``"market": "columbus-oh"``, so an outbound click on a Dayton hotel would
#: have been attributed to Columbus. Callers that know their market now pass
#: it; the default is kept so the Columbus build's bytes do not move.
DEFAULT_ANALYTICS_MARKET = "columbus-oh"


def build_go_page(*, listing_id: str, listing_name: str, action: str,
                  destination: str, page_type: str, category: str,
                  corridor: str = "", verification_status: str = "",
                  market: str = DEFAULT_ANALYTICS_MARKET,
                  affiliate_provider: str = "", build_id: str = "",
                  provider_inline_js: str = "") -> Tuple[str, str]:
    """Returns ``(route, html)`` for one static outbound redirect page.
    Refuses (raises ``ValueError``) a destination that fails the fail-closed
    safety check -- never emits an unsafe redirect. The page fires an
    analytics event, then redirects via BOTH ``<meta refresh>`` (works with
    JavaScript disabled -- Task 15/16 progressive-enhancement requirement)
    and an immediate JS redirect (faster in practice); a visible fallback
    link is always present too.

    PTF-MEASUREMENT-001. Three optional inputs, every one of which defaults
    to today's output byte for byte:

    * ``affiliate_provider`` -- the resolved provider id for an affiliate
      booking destination; populates the dimension and switches the fallback
      link's ``rel`` to ``REL_AFFILIATE_LINK``. Meaningful for ``booking``
      only.
    * ``build_id`` -- the owning market's release identity; emitted as a
      dimension only when supplied, so disabled builds do not carry it.
    * ``provider_inline_js`` -- the inline ``window.__ptfAnalyticsProvider``
      adapter (``measurement.inline_beacon_provider_js``). It is placed BEFORE
      ``ANALYTICS_JS`` so the provider exists by the time ``emit`` runs, and
      it must not depend on any external script: ``location.replace`` follows
      the emit on the very next statement.
    """
    if not _validate_destination(destination):
        raise ValueError("refusing unsafe /go/ destination for %r/%s: %r"
                         % (listing_id, action, destination))
    if affiliate_provider and not _SAFE_ID_RE.match(affiliate_provider):
        raise ValueError("unsafe affiliate_provider id: %r" % affiliate_provider)
    if build_id and not re.match(r"^[0-9a-f]{8,64}$", build_id):
        raise ValueError("build_id must be a hex digest prefix: %r" % build_id)
    route = go_route(listing_id, action)
    event = _ACTION_TO_EVENT.get(action, "")
    safe_name = html.escape(listing_name)
    safe_dest = html.escape(destination, quote=True)
    dims = {
        "market": market, "page_type": page_type, "route": route,
        "listing_id": listing_id, "listing_state": verification_status,
        "category": category, "corridor": corridor,
        "action_position": "go_redirect", "verification_status": verification_status,
        "affiliate_provider": affiliate_provider,
    }
    if build_id:
        dims["build_id"] = build_id
    rel = REL_AFFILIATE_LINK if (affiliate_provider and action == ACTION_BOOKING) \
        else "noopener"
    # AES-SITE-001 defect fix: json.dumps does NOT escape "</" -- if a
    # destination URL ever contained a literal "</script>" substring, an
    # HTML PARSER (not the JS parser) would close the <script> tag early,
    # turning the remainder of the string into live markup. Escaping "</"
    # to "<\/" is valid inside a JS string literal (the backslash is a
    # no-op escape there) and defeats this HTML-parser-level injection --
    # the same fix already applied in structured_data.to_script_tag.
    def _js_safe(obj) -> str:
        return json.dumps(obj, sort_keys=True).replace("</", "<\\/")

    dims_json = _js_safe(dims)
    dest_js = _js_safe(destination)
    event_js = _js_safe(event)
    body = (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<meta http-equiv=\"refresh\" content=\"0; url=%s\">"
        "<title>Continuing to %s &hellip; | PetTripFinder</title>"
        "<meta name=\"robots\" content=\"noindex, nofollow\">"
        "</head><body>"
        "<p>Continuing to <a rel=\"%s\" href=\"%s\">%s</a>&hellip;</p>"
        "<script>%s%s\nptfAnalytics.emit(%s, %s);\nlocation.replace(%s);</script>"
        "</body></html>"
    ) % (safe_dest, safe_name, rel, safe_dest, safe_name,
         provider_inline_js, ANALYTICS_JS, event_js, dims_json, dest_js)
    return (route, body)
