"""AES-SITE-001 (Task 6/7/14) -- comparison, corridor, and methodology page
generators. Fully custom static HTML assembled by this module (not routed
through the AES-WEB component/content-block pipeline, to avoid any risk of
its content-escaping conventions double-escaping a hand-built HTML table --
see ``site_enrichment.py``'s module docstring for the overall design
rationale). Reuses the exact same visual shell classes/CSS custom
properties already shipped in the real bundle's ``styles.css`` so these
pages are visually consistent with the rest of the site, not a foreign
template.
"""

from __future__ import annotations

import html
from typing import Dict, List, Optional, Tuple

from scripts.pettripfinder.site_data import normalize_name
from scripts.pettripfinder.structured_data import breadcrumb_ld, to_script_tag

BASE_URL = "https://pettripfinder.com"
SITE_NAME = "PetTripFinder"

_NAV = (
    '<header><nav aria-label="Main" class="ac-nav ac-nav--header-standard ac-nav--standard">'
    "<ul><li><a href=\"/\">PetTripFinder</a></li>"
    '<li><a href="/pet-friendly-hotels/">Pet-Friendly Hotels</a></li>'
    '<li><a href="/pet-friendly-parks/">Pet-Friendly Parks</a></li>'
    '<li><a href="/pet-friendly-restaurants/">Pet-Friendly Restaurants</a></li>'
    "</ul></nav></header>"
)
_FOOTER = (
    "<footer><div class=\"ac-legal ac-legal--footer-directory ac-legal--standard\">"
    "<p>(c) 2026 PetTripFinder. All rights reserved.</p>"
    "<p>Some listings are sponsored placements or contain affiliate links, always clearly "
    "labeled. Pet policies may change; confirm directly with the business before you travel.</p>"
    "<ul><li><a href=\"/\">PetTripFinder</a></li><li><a href=\"/about/\">About PetTripFinder</a></li>"
    "<li><a href=\"/contact/\">Contact Us</a></li><li><a href=\"/methodology/\">Our Methodology</a></li>"
    "<li><a href=\"/pet-friendly-hotels/\">Pet-Friendly Hotels</a></li>"
    "<li><a href=\"/pet-friendly-parks/\">Pet-Friendly Parks</a></li>"
    "<li><a href=\"/pet-friendly-restaurants/\">Pet-Friendly Restaurants</a></li></ul>"
    "</div></footer>"
)


def _e(text: str) -> str:
    return html.escape(text or "", quote=False)


# --------------------------------------------------------------------------- #
# Extra CSS (Task 17) -- appended to the real bundle's own styles.css, using
# ONLY that stylesheet's existing custom-property design tokens (colors,
# radii, shadows, spacing, typography) so every new element looks native to
# the site rather than a bolted-on foreign style. No new frontend framework,
# no external font/asset dependency (Task 16).
# --------------------------------------------------------------------------- #

PTF_EXTRA_CSS = """
.ptf-breadcrumbs{padding:var(--spacing-inline-default) var(--spacing-stack-default);font-size:14px;color:var(--color-text-muted)}
.ptf-breadcrumbs ol{display:flex;flex-wrap:wrap;gap:4px;list-style:none;margin:0;padding:0}
.ptf-breadcrumbs li:not(:last-child)::after{content:"/";margin-left:4px;color:var(--color-border-strong)}
.ptf-breadcrumbs a{color:var(--color-text-link);text-decoration:underline}
.ptf-badge{display:flex;align-items:center;gap:8px;margin:var(--spacing-stack-default) 0;padding:12px 16px;border-radius:var(--radius-control);font-size:15px}
.ptf-badge--verified{background:var(--color-surface-featured);color:var(--color-text-success);border:1px solid var(--color-text-success)}
.ptf-badge--no-pets{background:#fbeceb;color:var(--color-text-error);border:1px solid var(--color-text-error)}
.ptf-badge--unverified{background:var(--color-surface-raised);color:var(--color-text-muted);border:1px dashed var(--color-border-strong)}
.ptf-badge a{color:inherit;text-decoration:underline}
.ptf-badge-icon{font-weight:700}
.ptf-policy-table{width:100%;max-width:520px;border-collapse:collapse;margin:var(--spacing-stack-default) 0;box-shadow:var(--shadow-raised);border-radius:var(--radius-card);overflow:hidden}
.ptf-policy-table th,.ptf-policy-table td{padding:10px 14px;text-align:left;border-bottom:1px solid var(--color-border-default)}
.ptf-policy-table th{background:var(--color-surface-featured);font-weight:600;width:44%}
.ptf-unknown{color:var(--color-text-muted);font-style:italic}
.ptf-visually-hidden{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap}
.ptf-nearby{margin:var(--spacing-section-small) 0}
.ptf-nearby h2{font:var(--typography-heading-3)}
.ptf-nearby ul{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:6px}
.ptf-nearby a{color:var(--color-text-link);text-decoration:underline}
.ptf-nearby-city{color:var(--color-text-muted)}
.ptf-report-change{margin-top:var(--spacing-section-xsmall)}
.ptf-report-change a{color:var(--color-text-muted);font-size:14px}
.ptf-toolbar{display:flex;flex-direction:column;gap:12px;padding:12px 16px;margin-bottom:var(--spacing-stack-default);background:var(--color-surface-raised);border-radius:var(--radius-card);box-shadow:var(--shadow-raised)}
.ptf-toolbar a{color:var(--color-text-link);text-decoration:underline;font-weight:600}
.ptf-filter-group{display:flex;flex-wrap:wrap;gap:8px}
.ptf-filter-btn{border:1px solid var(--color-border-default);background:var(--color-surface-elevated);color:var(--color-text-default);border-radius:var(--radius-badge);padding:6px 14px;font-size:14px;cursor:pointer;min-height:44px}
.ptf-filter-btn:hover{border-color:var(--color-action-primary)}
.ptf-filter-btn:focus-visible{outline:var(--focus-ring-default);outline-color:var(--color-focus-ring)}
.ptf-filter-btn--active{background:var(--color-action-primary);border-color:var(--color-action-primary);color:var(--color-text-inverse)}
.ptf-hub-intro{padding:var(--spacing-section-small) var(--spacing-stack-default);max-width:760px}
.ptf-hub-intro a{color:var(--color-text-link);text-decoration:underline}
.ptf-hub-links{list-style:none;margin:var(--spacing-stack-default) 0 0;padding:0;display:flex;flex-wrap:wrap;gap:12px}
.ptf-hub-links a{display:inline-block;padding:8px 16px;border-radius:var(--radius-badge);background:var(--color-surface-featured);text-decoration:none;color:var(--color-text-default);min-height:44px;line-height:28px}
.ptf-card-grid{display:grid;grid-template-columns:var(--grid-columns-3);gap:var(--grid-gap-default)}
@media (max-width:640px){.ptf-card-grid{grid-template-columns:1fr}}
.ptf-table-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
.ptf-comparison-table{width:100%;min-width:720px;border-collapse:collapse;box-shadow:var(--shadow-raised);border-radius:var(--radius-card)}
.ptf-comparison-table caption{text-align:left;padding:8px 0;color:var(--color-text-muted);font-size:14px;caption-side:bottom}
.ptf-comparison-table th,.ptf-comparison-table td{padding:10px 14px;border-bottom:1px solid var(--color-border-default);text-align:left;white-space:nowrap}
.ptf-comparison-table thead th{background:var(--color-surface-featured);position:sticky;top:0}
.ptf-comparison-table a{color:var(--color-text-link);text-decoration:underline}
@media (prefers-reduced-motion:reduce){.ptf-filter-btn{transition:none}}
a:focus-visible,button:focus-visible{outline:var(--focus-ring-default);outline-color:var(--color-focus-ring);outline-offset:2px}
.ptf-skip-link{position:absolute;left:-9999px;top:0;background:var(--color-action-primary);color:var(--color-text-inverse);padding:8px 16px;z-index:100}
.ptf-skip-link:focus{left:8px;top:8px}
"""


def _shell(*, title: str, meta_description: str, route: str, body: str,
          ld_objects: Optional[List[Dict]] = None, robots: str = "index, follow") -> str:
    ld_script = to_script_tag(ld_objects or [])
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<title>%s</title>"
        "<meta name=\"description\" content=\"%s\">"
        "<meta name=\"robots\" content=\"%s\">"
        "<link rel=\"canonical\" href=\"%s%s\">"
        "<link rel=\"stylesheet\" href=\"/styles.css\">"
        "%s</head><body class=\"ac-layout ac-layout--shell-page\">"
        "%s<main id=\"main\">%s</main>%s</body></html>"
    ) % (_e(title), html.escape(meta_description, quote=True), robots,
         BASE_URL, route, ld_script, _NAV, body, _FOOTER)


def _breadcrumb_html(crumbs: List[Tuple[str, str]]) -> str:
    items = "".join(
        '<li><a href="%s">%s</a></li>' % (r, _e(n)) if r else '<li aria-current="page">%s</li>' % _e(n)
        for n, r in crumbs
    )
    return '<nav aria-label="Breadcrumb" class="ptf-breadcrumbs"><ol>%s</ol></nav>' % items


# --------------------------------------------------------------------------- #
# Policy comparison page (Task 6).
# --------------------------------------------------------------------------- #

_COMPARISON_COLUMNS = (
    ("name", "Hotel"),
    ("area", "Area"),
    ("species_allowed", "Pets accepted"),
    ("pet_fee", "Fee"),
    ("fee_basis", "Fee basis"),
    ("pet_count_limit", "Max pets"),
    ("weight_limit", "Weight limit"),
    ("verified_at", "Verified"),
)


def build_comparison_page(rows: List[Dict]) -> str:
    """``rows``: one dict per verified pet-friendly hotel with keys
    matching ``_COMPARISON_COLUMNS`` plus ``route``/``corridor``. Sorted by
    name -- a deterministic, non-"best"-implying default order (Task 6:
    "Do not sort by best unless objective criteria are explicitly
    defined")."""
    rows_sorted = sorted(rows, key=lambda r: normalize_name(r.get("name", "")))
    header = "".join("<th scope=\"col\">%s</th>" % _e(label) for _, label in _COMPARISON_COLUMNS)
    body_rows = []
    for r in rows_sorted:
        cells = []
        for key, _ in _COMPARISON_COLUMNS:
            if key == "name":
                cells.append('<th scope="row"><a href="%s">%s</a></th>' % (r["route"], _e(r["name"])))
                continue
            value = (r.get(key) or "").strip()
            cells.append("<td>%s</td>" % (_e(value) if value else '<span class="ptf-unknown">Not stated</span>'))
        body_rows.append("<tr>%s</tr>" % "".join(cells))
    table = (
        '<div class="ptf-table-scroll"><table class="ptf-comparison-table">'
        "<caption>Verified pet-friendly hotel policies in Columbus, compared side by side. "
        "Fees and limits can change &mdash; always confirm directly with the hotel before booking."
        "</caption><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>"
    ) % (header, "".join(body_rows))
    intro = (
        "<h1>Compare Verified Hotel Pet Policies in Columbus, Ohio</h1>"
        "<p>Every row below comes from that hotel's own official website, checked and quoted "
        "directly &mdash; never estimated. Rows without a stated value show "
        '<span class="ptf-unknown">Not stated</span> rather than a guess. '
        '<a href="/methodology/">Read our verification methodology</a>.</p>'
    )
    body = _breadcrumb_html([("PetTripFinder", "/"), ("Pet-Friendly Hotels", "/pet-friendly-hotels/"),
                            ("Policy Comparison", "")]) + intro + table
    ld = [breadcrumb_ld(BASE_URL, [("PetTripFinder", "/"), ("Pet-Friendly Hotels", "/pet-friendly-hotels/"),
                                   ("Policy Comparison", "/pet-friendly-hotels/policy-comparison/")])]
    return _shell(
        title="Hotel Pet Policy Comparison | PetTripFinder Columbus",
        meta_description="Compare verified pet fees, weight limits, and pet counts across "
                          "every evidence-backed pet-friendly hotel in Columbus, Ohio.",
        route="/pet-friendly-hotels/policy-comparison/", body=body, ld_objects=ld)


# --------------------------------------------------------------------------- #
# Corridor pages (Task 7).
# --------------------------------------------------------------------------- #

def build_corridor_page(corridor_name: str, corridor_slug: str, hotel_rows: List[Dict]) -> str:
    items = "".join(
        '<article class="ac-listing ac-listing--card-standard"><h2><a href="%s">%s</a></h2>'
        '<p class="ac-listing ac-listing--area">%s, OH</p></article>'
        % (r["route"], _e(r["name"]), _e(r.get("city", "")))
        for r in sorted(hotel_rows, key=lambda r: normalize_name(r["name"]))
    )
    intro = (
        "<h1>Verified Pet-Friendly Hotels in %s</h1>"
        "<p>%d verified pet-friendly hotels in the %s area. Every listing links to its full, "
        "evidence-backed pet policy. See the "
        '<a href="/pet-friendly-hotels/policy-comparison/">full comparison table</a> to check '
        "fees and limits at a glance.</p>"
    ) % (_e(corridor_name), len(hotel_rows), _e(corridor_name))
    body = _breadcrumb_html([("PetTripFinder", "/"), ("Pet-Friendly Hotels", "/pet-friendly-hotels/"),
                            (corridor_name, "")]) + intro + '<div class="ptf-card-grid">%s</div>' % items
    route = "/pet-friendly-hotels/%s/" % corridor_slug
    ld = [breadcrumb_ld(BASE_URL, [("PetTripFinder", "/"), ("Pet-Friendly Hotels", "/pet-friendly-hotels/"),
                                   (corridor_name, route)])]
    return _shell(
        title="Pet-Friendly Hotels in %s | PetTripFinder Columbus" % corridor_name,
        meta_description="Verified pet-friendly hotels in the %s area of Columbus, Ohio, "
                          "with real pet fees and policies from each hotel's own website." % corridor_name,
        route=route, body=body, ld_objects=ld)


# --------------------------------------------------------------------------- #
# Methodology page rewrite (Task 14) -- replaces the stale pre-verification
# era text ("we do not currently operate a formal verification program")
# with the real, now-operating evidence pipeline.
# --------------------------------------------------------------------------- #

def build_methodology_page() -> str:
    body = (
        "<h1>Our Methodology</h1>"
        "<p>PetTripFinder verifies pet policies directly from each business's own official "
        "website. For a listing marked <strong>Policy verified</strong>, we fetched the "
        "business's official page, located the exact sentence stating its pet policy, and "
        "recorded the fee, pet count, weight limit, and restrictions exactly as stated &mdash; "
        "never estimated or inferred from the business's name, category, or general "
        "reputation.</p>"
        "<h2>What each status means</h2>"
        "<ul>"
        "<li><strong>Policy verified</strong>: the pet policy shown was read directly from the "
        "business's own official website on the date shown.</li>"
        "<li><strong>Verified: pets not accepted</strong>: the business's official website "
        "explicitly states pets are not allowed. This is distinct from a service-animal "
        "policy, which is a separate legal category we never treat as a pet-acceptance "
        "signal.</li>"
        "<li><strong>Policy not independently verified</strong>: we have identified and listed "
        "the business, but have not yet confirmed its pet policy from an official source. "
        "Confirm directly with the business before booking.</li>"
        "</ul>"
        "<h2>What we never do</h2>"
        "<ul>"
        "<li>We never mark a business pet-friendly because of its brand, category, or "
        "marketing language alone.</li>"
        "<li>We never use third-party directories, review sites, or general search results as "
        "pet-policy evidence &mdash; only the business's own official page.</li>"
        "<li>We never fabricate a fee, weight limit, or pet count that the source did not "
        "state; unstated fields are shown as <span class=\"ptf-unknown\">Not stated</span>, "
        "never a default or estimate.</li>"
        "</ul>"
        "<h2>Freshness and corrections</h2>"
        "<p>Pet policies can change. Every verified listing shows the date it was checked. If "
        "you find a policy that has changed, use the <strong>Report an outdated or incorrect "
        "policy</strong> link on that listing's page.</p>"
        "<h2>Limitations</h2>"
        "<p>Some official hotel-chain websites actively block automated access; for those "
        "properties we list identifying information but do not display an unverified pet "
        "policy. We do not attempt to bypass these blocks.</p>"
    )
    full_body = _breadcrumb_html([("PetTripFinder", "/"), ("Our Methodology", "")]) + body
    return _shell(
        title="Our Methodology | PetTripFinder",
        meta_description="How PetTripFinder verifies pet policies directly from official "
                          "business websites, and what each verification status means.",
        route="/methodology/", body=full_body)
