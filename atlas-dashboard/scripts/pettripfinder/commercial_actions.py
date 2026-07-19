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
)

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
                          config: Optional[AffiliateConfig] = None) -> str:
    """The REAL destination for one action, given an already-approved
    listing. Never accepts caller-supplied arbitrary URLs."""
    config = config or AffiliateConfig()
    if action in (ACTION_OFFICIAL_WEBSITE, ACTION_BOOKING):
        target = official_url
        if action == ACTION_BOOKING:
            target = apply_affiliate_params(official_url, config)
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


def go_route(listing_id: str, action: str) -> str:
    if not _SAFE_ID_RE.match(listing_id):
        raise ValueError("unsafe listing_id for /go/ route: %r" % listing_id)
    if action not in ACTION_TYPES:
        raise ValueError("unknown action type: %r" % action)
    return "/go/%s/%s/" % (listing_id, action)


def build_go_page(*, listing_id: str, listing_name: str, action: str,
                  destination: str, page_type: str, category: str,
                  corridor: str = "", verification_status: str = "",
                  market: str = "columbus-oh") -> Tuple[str, str]:
    """Returns ``(route, html)`` for one static outbound redirect page.
    Refuses (raises ``ValueError``) a destination that fails the fail-closed
    safety check -- never emits an unsafe redirect. The page fires an
    analytics event, then redirects via BOTH ``<meta refresh>`` (works with
    JavaScript disabled -- Task 15/16 progressive-enhancement requirement)
    and an immediate JS redirect (faster in practice); a visible fallback
    link is always present too."""
    if not _validate_destination(destination):
        raise ValueError("refusing unsafe /go/ destination for %r/%s: %r"
                         % (listing_id, action, destination))
    route = go_route(listing_id, action)
    event = _ACTION_TO_EVENT.get(action, "")
    safe_name = html.escape(listing_name)
    safe_dest = html.escape(destination, quote=True)
    dims = {
        "market": market, "page_type": page_type, "route": route,
        "listing_id": listing_id, "listing_state": verification_status,
        "category": category, "corridor": corridor,
        "action_position": "go_redirect", "verification_status": verification_status,
        "affiliate_provider": "",
    }
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
        "<p>Continuing to <a rel=\"noopener\" href=\"%s\">%s</a>&hellip;</p>"
        "<script>%s\nptfAnalytics.emit(%s, %s);\nlocation.replace(%s);</script>"
        "</body></html>"
    ) % (safe_dest, safe_name, safe_dest, safe_name,
         ANALYTICS_JS, event_js, dims_json, dest_js)
    return (route, body)
