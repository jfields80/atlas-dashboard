"""Deterministic audit engine for the Website Intelligence subsystem.

AES-005A Part 3.

The audit engine is the deterministic "eyes" of Atlas. It inspects a
generated website (``WebsiteAuditInput``) and produces a complete
``WebsiteAuditReport``: findings, category scores, overall score, grade,
launch readiness, and recommendations.

Responsibilities (and nothing more):

- normalize the opaque website payloads into auditable views
- run deterministic checks and emit ``WebsiteAuditFinding`` contracts
- derive per-category scores from finding score impacts
- delegate score math to ``ScoringEngine`` (Part 1)
- delegate recommendation generation to ``RecommendationEngine`` (Part 2)
- assemble the immutable ``WebsiteAuditReport``

Division of responsibility (never duplicated):

- Audit engine: finds problems.
- Scoring engine: scores problems.
- Recommendation engine: explains problems.

Guarantees:

- Analysis only. Nothing is repaired, modified, written, or published.
- No AI. No I/O. No persistence. No HTTP. No side effects.
- No UUIDs. No timestamps. No randomness.
- Identical website -> identical findings -> identical scores ->
  identical recommendations -> identical report, byte for byte.
- Output ordering is total and independent of input ordering.

Payload interpretation:

``WebsiteAuditInput`` deliberately wraps its artifacts as opaque payloads
(Part 1: "zero import coupling to the manufacturing subsystems"), so this
module never imports Directory Builder / Website Generator models. Payloads
are read through a tolerant protocol that accepts mappings or attribute
objects and recognizes the documented field names below. Unrecognized or
absent fields normalize to empty values.

Recognized fields:

- static_site_package / preview_build:
  ``pages``, ``sitemap_paths`` (or ``sitemap``), ``robots``,
  ``cta_blocks``, ``monetization_sections``, ``contact_info``
- page: ``path``, ``title``, ``meta_description``, ``h1``, ``content``,
  ``links``, ``canonical``, ``breadcrumbs``
- project_assembly: ``slug`` (or ``name``), ``businesses``,
  ``categories``, ``locations``
- business: ``name``, ``category``, ``location``, ``description``

The frozen Part 1 finding contract carries no dedicated affected-path or
score-impact fields, so both are encoded deterministically inside
``evidence`` using the fixed format ``"path: {path}; impact: {impact}; ..."``.
"""

from typing import Any, Dict, List, Mapping, NamedTuple, Tuple

from engines.website_intelligence.constants import (
    CATEGORY_COMMERCIAL,
    CATEGORY_CONTENT,
    CATEGORY_DIRECTORY,
    CATEGORY_MONETIZATION,
    CATEGORY_NAVIGATION,
    CATEGORY_SEO,
    CATEGORY_UX,
    ENGINE_NAME,
    ENGINE_VERSION,
    SCORE_CATEGORIES,
    SCORE_MIN,
    SEVERITIES,
    SEVERITY_CRITICAL,
    SEVERITY_INFO,
    SEVERITY_WARNING,
)
from engines.website_intelligence.models import (
    WebsiteAuditFinding,
    WebsiteAuditInput,
    WebsiteAuditReport,
)
from engines.website_intelligence.recommendation_engine import RecommendationEngine
from engines.website_intelligence.scoring_engine import (
    ScoringEngine,
    round_score,
    stable_id,
)

# ---------------------------------------------------------------------------
# Deterministic audit constants (single source of truth for this engine)
# ---------------------------------------------------------------------------

# Fixed score impact per finding severity, deducted from the finding's
# category score (which starts at 100.0 and floors at SCORE_MIN).
SCORE_IMPACTS = {
    SEVERITY_CRITICAL: 25.0,
    SEVERITY_WARNING: 8.0,
    SEVERITY_INFO: 2.0,
}

# Paths recognized as the site homepage.
HOMEPAGE_PATHS = ("/", "/index.html", "index.html", "/index.htm")

# Minimum stripped content length below which a non-empty page is "thin".
THIN_CONTENT_MIN_CHARS = 200

# Lowercase tokens that mark unfinished placeholder content.
PLACEHOLDER_TOKENS = ("lorem ipsum", "placeholder", "todo", "tbd", "{{", "[[")

# Lowercase tokens that mark unresolved affiliate placeholders.
AFFILIATE_PLACEHOLDER_TOKENS = (
    "affiliate_placeholder",
    "affiliate-placeholder",
    "[affiliate]",
)

# Link prefixes that are external or non-navigational and never audited.
EXTERNAL_LINK_PREFIXES = ("http://", "https://", "mailto:", "tel:", "#")

# Prefixes for stable IDs, following the Part 1 stable_id convention.
_FINDING_ID_PREFIX = "find"
_REPORT_ID_PREFIX = "rpt"

# Fixed deterministic evidence format. Never generated prose.
_EVIDENCE_TEMPLATE = "path: {path}; impact: {impact:.1f}; {detail}"

_SITE_PATH = "(site)"

_CATEGORY_RANK = {category: rank for rank, category in enumerate(SCORE_CATEGORIES)}
_SEVERITY_RANK = {severity: rank for rank, severity in enumerate(SEVERITIES)}


# ---------------------------------------------------------------------------
# Tolerant payload extraction (mappings or attribute objects)
# ---------------------------------------------------------------------------


def _get(payload: Any, field: str, default: Any = None) -> Any:
    """Read a field from a mapping or attribute-style object."""
    if payload is None:
        return default
    if isinstance(payload, Mapping):
        return payload.get(field, default)
    return getattr(payload, field, default)


def _as_text(value: Any) -> str:
    """Normalize an optional text value to a stripped string."""
    if value is None:
        return ""
    return str(value).strip()


def _as_items(value: Any) -> Tuple[Any, ...]:
    """Normalize an optional collection to a tuple (never a string split)."""
    if value is None:
        return ()
    if isinstance(value, (str, bytes)):
        return (value,)
    try:
        return tuple(value)
    except TypeError:
        return (value,)


def _item_name(item: Any) -> str:
    """Extract a name from a plain string or a named object/mapping."""
    if isinstance(item, (str, bytes)):
        return _as_text(item)
    return _as_text(_get(item, "name", ""))


class PageView(NamedTuple):
    """Normalized, auditable view of one generated page."""

    path: str
    title: str
    meta_description: str
    h1: str
    content: str
    links: Tuple[str, ...]
    canonical: str
    breadcrumbs: Tuple[str, ...]


class BusinessView(NamedTuple):
    """Normalized, auditable view of one directory business."""

    name: str
    category: str
    location: str
    description: str


class SiteView(NamedTuple):
    """Normalized, auditable view of the entire website input."""

    site_name: str
    pages: Tuple[PageView, ...]
    sitemap_paths: Tuple[str, ...]
    robots: str
    cta_blocks: Tuple[str, ...]
    monetization_sections: Tuple[str, ...]
    contact_info: str
    businesses: Tuple[BusinessView, ...]
    categories: Tuple[str, ...]
    locations: Tuple[str, ...]


def _normalize_page(raw: Any) -> PageView:
    return PageView(
        path=_as_text(_get(raw, "path", "")),
        title=_as_text(_get(raw, "title", "")),
        meta_description=_as_text(_get(raw, "meta_description", "")),
        h1=_as_text(_get(raw, "h1", "")),
        content=_as_text(_get(raw, "content", "")),
        links=tuple(_as_text(link) for link in _as_items(_get(raw, "links", ()))),
        canonical=_as_text(_get(raw, "canonical", "")),
        breadcrumbs=tuple(
            _as_text(crumb) for crumb in _as_items(_get(raw, "breadcrumbs", ()))
        ),
    )


def _normalize_business(raw: Any) -> BusinessView:
    return BusinessView(
        name=_as_text(_get(raw, "name", "")),
        category=_as_text(_get(raw, "category", "")),
        location=_as_text(_get(raw, "location", "")),
        description=_as_text(_get(raw, "description", "")),
    )


def normalize_input(audit_input: WebsiteAuditInput) -> SiteView:
    """Normalize a ``WebsiteAuditInput`` into an auditable ``SiteView``.

    Pages come from the static site package; if it carries none, the
    preview build is consulted. Directory data comes from the project
    assembly. All values are normalized deterministically.
    """
    if not isinstance(audit_input, WebsiteAuditInput):
        raise ValueError(
            f"audit_input must be a WebsiteAuditInput, got {audit_input!r}"
        )

    assembly = audit_input.project_assembly
    package = audit_input.static_site_package
    preview = audit_input.preview_build

    raw_pages = _as_items(_get(package, "pages", ()))
    if not raw_pages:
        raw_pages = _as_items(_get(preview, "pages", ()))

    sitemap = _as_items(_get(package, "sitemap_paths", None))
    if not sitemap:
        sitemap = _as_items(_get(package, "sitemap", None))

    site_name = _as_text(_get(assembly, "slug", "")) or _as_text(
        _get(assembly, "name", "")
    )

    return SiteView(
        site_name=site_name,
        pages=tuple(_normalize_page(page) for page in raw_pages),
        sitemap_paths=tuple(_as_text(path) for path in sitemap),
        robots=_as_text(_get(package, "robots", "")),
        cta_blocks=tuple(
            _as_text(block) for block in _as_items(_get(package, "cta_blocks", ()))
        ),
        monetization_sections=tuple(
            _as_text(section)
            for section in _as_items(_get(package, "monetization_sections", ()))
        ),
        contact_info=_as_text(_get(package, "contact_info", "")),
        businesses=tuple(
            _normalize_business(business)
            for business in _as_items(_get(assembly, "businesses", ()))
        ),
        categories=tuple(
            _item_name(category)
            for category in _as_items(_get(assembly, "categories", ()))
        ),
        locations=tuple(
            _item_name(location)
            for location in _as_items(_get(assembly, "locations", ()))
        ),
    )


# ---------------------------------------------------------------------------
# Finding construction
# ---------------------------------------------------------------------------


def _finding(
    check_code: str,
    category: str,
    severity: str,
    title: str,
    description: str,
    path: str,
    detail: str,
    *id_parts: str,
) -> WebsiteAuditFinding:
    """Build one deterministic finding.

    The affected path and score impact are encoded in ``evidence`` with a
    fixed format because the frozen Part 1 contract carries no dedicated
    fields for them.
    """
    impact = SCORE_IMPACTS[severity]
    return WebsiteAuditFinding(
        finding_id=stable_id(_FINDING_ID_PREFIX, check_code, *id_parts),
        category=category,
        severity=severity,
        title=title,
        description=description,
        evidence=_EVIDENCE_TEMPLATE.format(path=path, impact=impact, detail=detail),
    )


def _is_internal_link(target: str) -> bool:
    if not target:
        return False
    lowered = target.lower()
    return not any(lowered.startswith(prefix) for prefix in EXTERNAL_LINK_PREFIXES)


def _is_homepage(path: str) -> bool:
    return path in HOMEPAGE_PATHS


# ---------------------------------------------------------------------------
# Category checks (analysis only — nothing is ever repaired)
# ---------------------------------------------------------------------------


def _seo_findings(site: SiteView) -> List[WebsiteAuditFinding]:
    findings: List[WebsiteAuditFinding] = []
    paths = {page.path for page in site.pages}

    for page in site.pages:
        if not page.title:
            findings.append(
                _finding(
                    "seo.missing_title",
                    CATEGORY_SEO,
                    SEVERITY_WARNING,
                    "Missing page title",
                    "The page defines no title.",
                    page.path,
                    "title is empty",
                    page.path,
                )
            )
        if not page.meta_description:
            findings.append(
                _finding(
                    "seo.missing_meta_description",
                    CATEGORY_SEO,
                    SEVERITY_WARNING,
                    "Missing meta description",
                    "The page defines no meta description.",
                    page.path,
                    "meta description is empty",
                    page.path,
                )
            )
        if not page.h1:
            findings.append(
                _finding(
                    "seo.missing_h1",
                    CATEGORY_SEO,
                    SEVERITY_WARNING,
                    "Missing H1 heading",
                    "The page defines no H1 heading.",
                    page.path,
                    "h1 is empty",
                    page.path,
                )
            )
        if (
            page.canonical
            and page.canonical.startswith("/")
            and page.canonical not in paths
        ):
            findings.append(
                _finding(
                    "seo.broken_canonical",
                    CATEGORY_SEO,
                    SEVERITY_WARNING,
                    "Broken canonical reference",
                    "The canonical URL points to a path that does not exist.",
                    page.path,
                    f"canonical -> {page.canonical}",
                    page.path,
                    page.canonical,
                )
            )

    findings.extend(
        _duplicate_value_findings(
            site,
            value_of=lambda page: page.title,
            check_code="seo.duplicate_title",
            title="Duplicate page titles",
            description="Multiple pages share the same title.",
        )
    )
    findings.extend(
        _duplicate_value_findings(
            site,
            value_of=lambda page: page.meta_description,
            check_code="seo.duplicate_meta_description",
            title="Duplicate meta descriptions",
            description="Multiple pages share the same meta description.",
        )
    )

    seen_paths: Dict[str, int] = {}
    for page in site.pages:
        seen_paths[page.path] = seen_paths.get(page.path, 0) + 1
    for path in sorted(path for path, count in seen_paths.items() if count > 1):
        findings.append(
            _finding(
                "seo.duplicate_path",
                CATEGORY_SEO,
                SEVERITY_CRITICAL,
                "Duplicate page paths",
                "Multiple pages are generated at the same path.",
                path,
                f"occurrences: {seen_paths[path]}",
                path,
            )
        )

    for path in sorted(set(site.sitemap_paths) - paths):
        findings.append(
            _finding(
                "seo.broken_sitemap_reference",
                CATEGORY_SEO,
                SEVERITY_WARNING,
                "Broken sitemap reference",
                "The sitemap references a path that does not exist.",
                path,
                "sitemap entry has no matching page",
                path,
            )
        )

    if site.pages and not site.robots:
        findings.append(
            _finding(
                "seo.missing_robots",
                CATEGORY_SEO,
                SEVERITY_INFO,
                "Missing robots directives",
                "The site defines no robots directives.",
                _SITE_PATH,
                "robots is empty",
            )
        )

    return findings


def _duplicate_value_findings(
    site: SiteView,
    value_of,
    check_code: str,
    title: str,
    description: str,
) -> List[WebsiteAuditFinding]:
    groups: Dict[str, List[str]] = {}
    for page in site.pages:
        value = value_of(page)
        if value:
            groups.setdefault(value, []).append(page.path)

    findings: List[WebsiteAuditFinding] = []
    for value in sorted(value for value, paths in groups.items() if len(paths) > 1):
        paths = sorted(groups[value])
        findings.append(
            _finding(
                check_code,
                CATEGORY_SEO,
                SEVERITY_WARNING,
                title,
                description,
                paths[0],
                f"value: {value}; pages: {', '.join(paths)}",
                value,
            )
        )
    return findings


def _navigation_findings(site: SiteView) -> List[WebsiteAuditFinding]:
    findings: List[WebsiteAuditFinding] = []
    paths = {page.path for page in site.pages}

    if not any(_is_homepage(page.path) for page in site.pages):
        findings.append(
            _finding(
                "navigation.missing_homepage",
                CATEGORY_NAVIGATION,
                SEVERITY_CRITICAL,
                "Missing homepage",
                "The site has no homepage.",
                _SITE_PATH,
                f"expected one of: {', '.join(HOMEPAGE_PATHS)}",
            )
        )

    inbound: Dict[str, int] = {}
    for page in site.pages:
        seen_targets: Dict[str, int] = {}
        for target in page.links:
            if not _is_internal_link(target):
                continue
            seen_targets[target] = seen_targets.get(target, 0) + 1
            if target != page.path:
                inbound[target] = inbound.get(target, 0) + 1
            if target not in paths:
                findings.append(
                    _finding(
                        "navigation.broken_link",
                        CATEGORY_NAVIGATION,
                        SEVERITY_WARNING,
                        "Broken internal link",
                        "The page links to a path that does not exist.",
                        page.path,
                        f"link -> {target}",
                        page.path,
                        target,
                    )
                )
        for target in sorted(t for t, count in seen_targets.items() if count > 1):
            findings.append(
                _finding(
                    "navigation.duplicate_link",
                    CATEGORY_NAVIGATION,
                    SEVERITY_INFO,
                    "Duplicate navigation paths",
                    "The page links to the same path more than once.",
                    page.path,
                    f"link -> {target}; occurrences: {seen_targets[target]}",
                    page.path,
                    target,
                )
            )

    for page in site.pages:
        if _is_homepage(page.path):
            continue
        if inbound.get(page.path, 0) == 0:
            findings.append(
                _finding(
                    "navigation.orphan_page",
                    CATEGORY_NAVIGATION,
                    SEVERITY_INFO,
                    "Orphan page",
                    "No other page links to this page.",
                    page.path,
                    "inbound links: 0",
                    page.path,
                )
            )
        if not page.breadcrumbs:
            findings.append(
                _finding(
                    "navigation.missing_breadcrumbs",
                    CATEGORY_NAVIGATION,
                    SEVERITY_INFO,
                    "Missing breadcrumbs",
                    "The page defines no breadcrumb trail.",
                    page.path,
                    "breadcrumbs are empty",
                    page.path,
                )
            )

    return findings


def _content_findings(site: SiteView) -> List[WebsiteAuditFinding]:
    findings: List[WebsiteAuditFinding] = []

    for page in site.pages:
        if not page.content:
            findings.append(
                _finding(
                    "content.empty_page",
                    CATEGORY_CONTENT,
                    SEVERITY_CRITICAL,
                    "Empty page",
                    "The page has no content.",
                    page.path,
                    "content length: 0",
                    page.path,
                )
            )
        elif len(page.content) < THIN_CONTENT_MIN_CHARS:
            findings.append(
                _finding(
                    "content.thin_page",
                    CATEGORY_CONTENT,
                    SEVERITY_WARNING,
                    "Thin page content",
                    "The page content is below the minimum length.",
                    page.path,
                    f"content length: {len(page.content)}; "
                    f"minimum: {THIN_CONTENT_MIN_CHARS}",
                    page.path,
                )
            )
        lowered = page.content.lower()
        for token in PLACEHOLDER_TOKENS:
            if token in lowered:
                findings.append(
                    _finding(
                        "content.placeholder",
                        CATEGORY_CONTENT,
                        SEVERITY_WARNING,
                        "Placeholder content",
                        "The page contains unfinished placeholder content.",
                        page.path,
                        f"token: {token}",
                        page.path,
                        token,
                    )
                )

    for business in site.businesses:
        if not business.description:
            findings.append(
                _finding(
                    "content.missing_business_description",
                    CATEGORY_CONTENT,
                    SEVERITY_WARNING,
                    "Missing business description",
                    "The business listing has no description.",
                    _SITE_PATH,
                    f"business: {business.name}",
                    business.name,
                    business.category,
                    business.location,
                )
            )

    description_groups: Dict[str, List[str]] = {}
    for business in site.businesses:
        if business.description:
            description_groups.setdefault(business.description, []).append(
                business.name
            )
    for description in sorted(
        value for value, names in description_groups.items() if len(names) > 1
    ):
        names = sorted(description_groups[description])
        findings.append(
            _finding(
                "content.duplicate_business_description",
                CATEGORY_CONTENT,
                SEVERITY_INFO,
                "Duplicate business descriptions",
                "Multiple business listings share the same description.",
                _SITE_PATH,
                f"businesses: {', '.join(names)}",
                description,
            )
        )

    return findings


def _directory_findings(site: SiteView) -> List[WebsiteAuditFinding]:
    findings: List[WebsiteAuditFinding] = []
    categories = set(site.categories)
    locations = set(site.locations)

    seen_businesses: Dict[Tuple[str, str], int] = {}
    for business in site.businesses:
        if not business.category:
            findings.append(
                _finding(
                    "directory.missing_category",
                    CATEGORY_DIRECTORY,
                    SEVERITY_WARNING,
                    "Business without category",
                    "The business listing has no category.",
                    _SITE_PATH,
                    f"business: {business.name}",
                    business.name,
                    business.location,
                )
            )
        elif categories and business.category not in categories:
            findings.append(
                _finding(
                    "directory.broken_category_relationship",
                    CATEGORY_DIRECTORY,
                    SEVERITY_WARNING,
                    "Broken category relationship",
                    "The business references a category that is not defined.",
                    _SITE_PATH,
                    f"business: {business.name}; category: {business.category}",
                    business.name,
                    business.category,
                )
            )
        if not business.location:
            findings.append(
                _finding(
                    "directory.missing_location",
                    CATEGORY_DIRECTORY,
                    SEVERITY_WARNING,
                    "Business without location",
                    "The business listing has no location.",
                    _SITE_PATH,
                    f"business: {business.name}",
                    business.name,
                    business.category,
                )
            )
        elif locations and business.location not in locations:
            findings.append(
                _finding(
                    "directory.broken_location_relationship",
                    CATEGORY_DIRECTORY,
                    SEVERITY_WARNING,
                    "Broken location relationship",
                    "The business references a location that is not defined.",
                    _SITE_PATH,
                    f"business: {business.name}; location: {business.location}",
                    business.name,
                    business.location,
                )
            )
        key = (business.name.lower(), business.location.lower())
        seen_businesses[key] = seen_businesses.get(key, 0) + 1

    for name, location in sorted(
        key for key, count in seen_businesses.items() if count > 1
    ):
        findings.append(
            _finding(
                "directory.duplicate_business",
                CATEGORY_DIRECTORY,
                SEVERITY_WARNING,
                "Duplicate businesses",
                "Multiple listings share the same business name and location.",
                _SITE_PATH,
                f"business: {name}; location: {location}; "
                f"occurrences: {seen_businesses[(name, location)]}",
                name,
                location,
            )
        )

    return findings


def _commercial_findings(site: SiteView) -> List[WebsiteAuditFinding]:
    findings: List[WebsiteAuditFinding] = []

    for page in site.pages:
        lowered = page.content.lower()
        for token in AFFILIATE_PLACEHOLDER_TOKENS:
            if token in lowered:
                findings.append(
                    _finding(
                        "commercial.affiliate_placeholder",
                        CATEGORY_COMMERCIAL,
                        SEVERITY_WARNING,
                        "Unresolved affiliate placeholder",
                        "The page contains an unresolved affiliate placeholder.",
                        page.path,
                        f"token: {token}",
                        page.path,
                        token,
                    )
                )

    if site.pages and not site.cta_blocks:
        findings.append(
            _finding(
                "commercial.missing_cta_blocks",
                CATEGORY_COMMERCIAL,
                SEVERITY_WARNING,
                "Missing CTA blocks",
                "The site defines no call-to-action blocks.",
                _SITE_PATH,
                "cta blocks: 0",
            )
        )

    return findings


def _monetization_findings(site: SiteView) -> List[WebsiteAuditFinding]:
    findings: List[WebsiteAuditFinding] = []
    if site.pages and not site.monetization_sections:
        findings.append(
            _finding(
                "monetization.missing_sections",
                CATEGORY_MONETIZATION,
                SEVERITY_WARNING,
                "Missing monetization sections",
                "The site defines no monetization sections.",
                _SITE_PATH,
                "monetization sections: 0",
            )
        )
    return findings


def _ux_findings(site: SiteView) -> List[WebsiteAuditFinding]:
    findings: List[WebsiteAuditFinding] = []
    paths = {page.path for page in site.pages}

    has_contact_page = any("contact" in page.path.lower() for page in site.pages)
    if site.pages and not has_contact_page and not site.contact_info:
        findings.append(
            _finding(
                "ux.missing_contact_information",
                CATEGORY_UX,
                SEVERITY_WARNING,
                "Missing contact information",
                "The site provides no contact page or contact information.",
                _SITE_PATH,
                "no contact page and no contact info",
            )
        )

    for page in site.pages:
        segments = [segment for segment in page.path.split("/") if segment]
        if len(segments) >= 2:
            parent = "/" + "/".join(segments[:-1])
            if parent not in paths:
                findings.append(
                    _finding(
                        "ux.broken_page_hierarchy",
                        CATEGORY_UX,
                        SEVERITY_INFO,
                        "Broken page hierarchy",
                        "The page has no parent page in the hierarchy.",
                        page.path,
                        f"missing parent: {parent}",
                        page.path,
                        parent,
                    )
                )
        if page.path and page.path in page.links:
            findings.append(
                _finding(
                    "ux.navigation_inconsistency",
                    CATEGORY_UX,
                    SEVERITY_INFO,
                    "Navigation inconsistency",
                    "The page links to itself.",
                    page.path,
                    "self link",
                    page.path,
                )
            )

    return findings


# ---------------------------------------------------------------------------
# Findings -> scores
# ---------------------------------------------------------------------------


def generate_findings(site: SiteView) -> Tuple[WebsiteAuditFinding, ...]:
    """Run every deterministic check and return ordered findings.

    Findings are ordered by category (``SCORE_CATEGORIES`` order), then
    severity (``SEVERITIES`` order), then title, then finding ID. The
    ordering is total, so output is independent of input ordering.
    """
    findings: List[WebsiteAuditFinding] = []
    findings.extend(_seo_findings(site))
    findings.extend(_navigation_findings(site))
    findings.extend(_content_findings(site))
    findings.extend(_directory_findings(site))
    findings.extend(_commercial_findings(site))
    findings.extend(_monetization_findings(site))
    findings.extend(_ux_findings(site))
    findings.sort(
        key=lambda finding: (
            _CATEGORY_RANK[finding.category],
            _SEVERITY_RANK[finding.severity],
            finding.title,
            finding.finding_id,
        )
    )
    return tuple(findings)


def category_scores_from_findings(
    findings: Tuple[WebsiteAuditFinding, ...],
) -> Dict[str, float]:
    """Derive per-category raw scores from finding score impacts.

    Every category starts at 100.0. Each finding deducts its severity's
    fixed ``SCORE_IMPACTS`` value from its category. Scores floor at
    ``SCORE_MIN`` and are rounded to the engine precision. Score math
    beyond this derivation (weighting, grading, readiness) belongs to the
    Part 1 scoring engine and is never duplicated here.
    """
    scores = {category: 100.0 for category in SCORE_CATEGORIES}
    for finding in findings:
        scores[finding.category] -= SCORE_IMPACTS[finding.severity]
    return {
        category: round_score(max(SCORE_MIN, scores[category]))
        for category in SCORE_CATEGORIES
    }


# ---------------------------------------------------------------------------
# Audit engine facade
# ---------------------------------------------------------------------------


class AuditEngine:
    """Deterministic website auditor: findings, scores, recommendations.

    Composes the Part 1 scoring engine and the Part 2 recommendation
    engine. Performs analysis only — nothing is repaired, written,
    persisted, or published.
    """

    engine_name = ENGINE_NAME
    engine_version = ENGINE_VERSION

    def __init__(self) -> None:
        self._scoring_engine = ScoringEngine()
        self._recommendation_engine = RecommendationEngine()

    def audit(self, audit_input: WebsiteAuditInput) -> WebsiteAuditReport:
        """Audit a generated website and return the complete report.

        Identical website input always yields an identical report:
        same findings, same scores, same recommendations, same IDs.
        """
        site = normalize_input(audit_input)
        findings = generate_findings(site)
        category_scores = category_scores_from_findings(findings)
        scoring = self._scoring_engine.score(category_scores)
        recommendations = self._recommendation_engine.recommend(findings)

        report_id = stable_id(
            _REPORT_ID_PREFIX,
            site.site_name,
            *sorted(finding.finding_id for finding in findings),
        )
        scores = scoring.category_scores_dict()
        return WebsiteAuditReport(
            report_id=report_id,
            engine_name=ENGINE_NAME,
            engine_version=ENGINE_VERSION,
            seo_score=scores[CATEGORY_SEO],
            navigation_score=scores[CATEGORY_NAVIGATION],
            content_score=scores[CATEGORY_CONTENT],
            directory_score=scores[CATEGORY_DIRECTORY],
            commercial_score=scores[CATEGORY_COMMERCIAL],
            monetization_score=scores[CATEGORY_MONETIZATION],
            ux_score=scores[CATEGORY_UX],
            overall_score=scoring.overall_score,
            grade=scoring.grade,
            launch_readiness=scoring.launch_readiness,
            findings=findings,
            recommendations=recommendations,
            work_orders=(),
        )
