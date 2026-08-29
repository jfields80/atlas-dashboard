"""PTF-MULTI-MARKET-ASSEMBLER-001 -- one bundle, many markets.

Until Phase E every PetTripFinder market generated a WHOLE SITE. Each build
wrote its own ``/``, its own ``/pet-friendly-hotels/``, its own
``sitemap.xml``, its own ``robots.txt`` -- each one describing the domain as
though its market were the only one on it. Deploying two of them was not a
merge, it was a race: whichever went last owned the apex.

This module ends that. It builds each market as a FRAGMENT, takes only the
routes that market legitimately owns, and composes the global surfaces itself,
exactly once:

    fragment (per market)          assembler (once)
    ---------------------          ----------------
    hotel profiles                 /
    corridor pages                 /about/  /contact/  /methodology/
    policy comparison              /pet-friendly-hotels/
    market hub                     sitemap.xml  robots.txt  llms.txt
    /go/ interstitials             _headers  _redirects
    market-only categories         global navigation

The split is enforced, not documented: a fragment that claims a global route
fails the build, and two fragments that claim the same route fail the build
naming both owners. Nothing is resolved by copy order.

The anchor market
-----------------
Exactly one registered market may use ``legacy_unprefixed`` (the market
contract enforces this), and that market's routes ARE the global namespace --
``market_route()`` returns ``/pet-friendly-hotels/`` for it. So the anchor is
not a favourite, it is a structural fact: the global category root is also the
anchor's market hub, and the global shell (navigation, about, contact,
methodology) is the shell the anchor already publishes. The assembler composes
the two global pages FROM the anchor's fragment and adds the market directory
on top, which is why adding Cleveland and Dayton inserts a section into the
live Columbus pages rather than replacing them.

Determinism
-----------
Same inputs, byte-identical bundle. No clock, no environment paths, no
iteration over a set without sorting it. Run it twice and diff -- there is a
gate for exactly that.

    python -m scripts.pettripfinder.assemble_production_site --output <dir>
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import shutil
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.markets import (                                  # noqa: E402
    MarketConfig, assign_hotels, corridor_route, hotel_route, load_markets,
    market_route,
)
from scripts.pettripfinder.markets.contract import (                         # noqa: E402
    ROUTE_MODE_LEGACY_UNPREFIXED,
)
from scripts.pettripfinder.market_ownership import owned_by                  # noqa: E402
from scripts.pettripfinder import launch_participation as LP                 # noqa: E402
from scripts.pettripfinder.site_data import (                                # noqa: E402
    load_published_hotel_policy_facts, read_production_rows,
    verified_public_hotels,
)

PACKAGE_DIR = _REPO_ROOT / "launch_packages" / "pettripfinder"
CENSUS_DIR = PACKAGE_DIR / "identity_census"

#: Routes no market fragment may own. The assembler writes every one of them.
GLOBAL_ROUTES = (
    "/",
    "/about/",
    "/contact/",
    "/methodology/",
    "/pet-friendly-hotels/",
)

#: Files no market fragment may contribute. Same rule, expressed for the
#: control files and machine surfaces that have no route.
GLOBAL_FILES = (
    "index.html",
    "about/index.html",
    "contact/index.html",
    "methodology/index.html",
    "pet-friendly-hotels/index.html",
    "sitemap.xml",
    "robots.txt",
    "llms.txt",
    "_headers",
    "_redirects",
)

#: Generator bookkeeping that is not part of the published site.
BUILD_INTERNAL_PREFIXES = ("_build_report", "_broken_link_report",
                           "_quality_report", "bundle_manifest",
                           ".assemble_work")

BUNDLE_SCHEMA = "ptf-global-bundle/1.1"

#: The deployment contexts this assembler understands. Anything else fails
#: closed: PTF-...-DEPLOYMENT-AND-LIVE-VERIFICATION-044 stopped because the
#: composed bundle carried no control files at all, and "whatever the
#: environment happens to be" is how a preview `noindex` reaches production.
VALID_CONTEXTS = ("production", "preview")

#: Tracked control-file sources. Owned by deploy/netlify/, copied verbatim --
#: never reconstructed from what a live response happened to show.
DEPLOY_NETLIFY_DIR = _REPO_ROOT / "deploy" / "netlify"
HEADERS_SOURCES = {
    "production": DEPLOY_NETLIFY_DIR / "headers.production",
    "preview": DEPLOY_NETLIFY_DIR / "headers.preview",
}
REDIRECTS_SOURCE = DEPLOY_NETLIFY_DIR / "redirects"

#: The live production route inventory this bundle must not silently drop.
#: Captured from the deployed sitemap; every entry must still resolve, because
#: an indexed URL that becomes a 404 is the one migration failure a build can
#: neither see nor undo.
LIVE_ROUTE_INVENTORY = (_REPO_ROOT / "deploy" / "netlify"
                        / "live_production_routes.txt")


class AssemblyError(RuntimeError):
    """A gate failed. Nothing is published; the output is left untouched."""


# --------------------------------------------------------------------------- #
# Market selection (Phase E section 27).
# --------------------------------------------------------------------------- #

def _partition_path(market_id: str) -> Optional[Path]:
    """The market's committed final partition, if it commits one."""
    matches = sorted(PACKAGE_DIR.glob("%s_final_partition_*.json"
                                      % market_id.rsplit("-", 1)[0].replace("-oh", "")))
    # Partition filenames are historical (``cleveland_final_partition_002``),
    # so a glob on the market id alone would miss them. Fall back to an
    # explicit table rather than guessing from a name.
    if matches:
        return matches[0]
    table = {
        "columbus-oh": "columbus_final_partition_001.json",
        "cleveland-akron-canton-oh": "cleveland_final_partition_002.json",
        "dayton-oh": "dayton_final_partition_001.json",
        "cincinnati-oh": "cincinnati_final_partition_001.json",
        # PTF-LOUISVILLE-MARKET-REBUILD-002: same mechanism, same reason --
        # "louisville-ky" strips to "louisville-ky" -> "louisville" only by
        # luck of the suffix, and the market commits exactly one partition.
        "louisville-ky": "louisville_final_partition_001.json",
        # St. Louis names its partitions with the FULL market id
        # (``st_louis_mo_final_partition_007``), which the prefix glob above
        # cannot reach: it strips the trailing segment and looks for
        # ``st-louis_...``. It is named here rather than by widening the glob
        # because this market commits FIVE partitions, one per founder sitting,
        # and the glob takes the first match in sorted order -- which would have
        # silently pinned 001, the partition from before any founder signed.
        "st-louis-mo": "st_louis_mo_final_partition_007.json",
        # Grand Rapids needs the table for the SAME reason and one more.
        # The glob strips the last segment and hyphenates:
        # "grand-rapids-holland-mi" -> "grand-rapids-holland_final_partition_*",
        # which no file matches because the filenames use underscores. It never
        # matched, so this market silently read as "no final partition" and was
        # not assemblable at all until PTF-GRAND-RAPIDS-LAUNCH-PARTICIPATION-032
        # went looking for why.
        #
        # And like St. Louis it commits more than one, so the entry names the
        # partition rather than letting sorted-order pick: 001 is the
        # PAID-ACQUISITION-AUTHORIZATION-009 partition from before any founder
        # signed, still carrying 42 rows as AWAITING_FOUNDER_DECISION. 002 is
        # rebuilt from the signed authority -- 43 published, 20 verified-no-pets.
        # Pinning 001 would assemble a market whose published hotels its own
        # partition says are waiting to be looked at.
        "grand-rapids-holland-mi": "grand_rapids_holland_mi_final_partition_002.json",
    }
    name = table.get(market_id)
    path = PACKAGE_DIR / name if name else None
    return path if path and path.is_file() else None


def published_hotels(market: MarketConfig) -> List[Dict]:
    """This market's published hotel rows, by its own committed authority."""
    rows = owned_by(read_production_rows(), market.market_id,
                    context="global assembly inventory")
    hotels = [r for r in rows if r.get("category") == "pet-friendly-hotels"]
    return verified_public_hotels(hotels, load_published_hotel_policy_facts(market.market_id))


def _launch_status_of(market_id: str) -> str:
    """The founder's recorded launch status, or UNLISTED; never raises here.

    A missing or malformed record reads as "nobody is authorized" -- the
    participation gates report WHY, but selection itself must fail closed.
    """
    try:
        return LP.launch_status(market_id)
    except LP.LaunchParticipationError:
        return LP.UNLISTED


def market_eligibility(market: MarketConfig) -> "OrderedDict[str, object]":
    """Why this market is or is not assemblable, stated per condition.

    Every condition is reported even when an earlier one already failed, so
    the report says what is missing rather than only what was noticed first.
    Cincinnati must come out of this as "registered, below threshold, not
    assembled" -- an honest zero, not an error (Phase E section 25).

    ``assemblable`` is a SOURCE fact: the four conditions below. Whether the
    market joins the composed production bundle is additionally the founder's
    call, recorded in ``deploy/netlify/launch_participation.json`` (PTF-046):
    ``participates`` is ``assemblable`` AND ``founder_authorized_for_launch``.
    The two are reported apart so a market the founder withheld is never
    mistaken for one whose source is broken.
    """
    census = CENSUS_DIR / ("%s.json" % market.market_id)
    partition = _partition_path(market.market_id)
    try:
        hotels = published_hotels(market)
        published, inventory_error = len(hotels), ""
    except Exception as exc:                       # inventory refuses to join
        published, inventory_error = 0, str(exc)

    conditions = OrderedDict([
        ("census_present", census.is_file()),
        ("final_partition_present", partition is not None),
        ("policy_authority_present", not inventory_error),
        ("meets_minimum_published",
         published >= market.minimum_published_hotels),
    ])
    assemblable = all(conditions.values())
    status = _launch_status_of(market.market_id)
    authorized = status == LP.FOUNDER_AUTHORIZED_FOR_LAUNCH
    return OrderedDict([
        ("market_id", market.market_id),
        ("published_count", published),
        ("minimum_published_hotels", market.minimum_published_hotels),
        ("conditions", conditions),
        ("assemblable", assemblable),
        ("launch_status", status),
        ("founder_authorized_for_launch", authorized),
        ("participates", assemblable and authorized),
        ("show_in_navigation", market.show_in_navigation),
        ("inventory_error", inventory_error),
    ])


def select_markets(markets: Optional[Sequence[MarketConfig]] = None
                   ) -> Tuple[List[MarketConfig], List["OrderedDict[str, object]"]]:
    """``(participating, eligibility_rows)`` in registration order.

    A market participates when its source is assemblable AND the founder has
    authorized it for launch. ``show_in_navigation`` is deliberately NOT a
    condition: a market may be assembled and still hidden from navigation, and
    conflating the two would make a visibility decision silently change what
    the bundle contains.
    """
    markets = list(markets) if markets is not None else list(load_markets())
    rows = [market_eligibility(m) for m in markets]
    by_id = {m.market_id: m for m in markets}
    chosen = [by_id[r["market_id"]] for r in rows if r["participates"]]
    return chosen, rows


def anchor_market(markets: Sequence[MarketConfig]) -> MarketConfig:
    """The single legacy_unprefixed market, whose routes are the global ones."""
    legacy = [m for m in markets if m.route_mode == ROUTE_MODE_LEGACY_UNPREFIXED]
    if len(legacy) != 1:
        raise AssemblyError(
            "exactly one assembled market must use %s (the global category root is "
            "that market's hub); found %d: %s"
            % (ROUTE_MODE_LEGACY_UNPREFIXED, len(legacy),
               [m.market_id for m in legacy]))
    return legacy[0]


# --------------------------------------------------------------------------- #
# Fragments.
# --------------------------------------------------------------------------- #

def _route_of(root: Path, path: Path) -> str:
    """The public route a generated file publishes at."""
    rel = path.relative_to(root).as_posix()
    if rel.endswith("/index.html"):
        return "/" + rel[: -len("index.html")]
    if rel == "index.html":
        return "/"
    return "/" + rel


def owned_routes(market: MarketConfig) -> "OrderedDict[str, str]":
    """Every public route this market may claim, mapped to what it is.

    Derived from the same helpers the generator writes with, so the manifest
    and the disk cannot disagree about a namespace.
    """
    hotels = published_hotels(market)
    assignment = assign_hotels(market, hotels, fail_closed=False)
    table: "OrderedDict[str, str]" = OrderedDict()
    if market.route_mode != ROUTE_MODE_LEGACY_UNPREFIXED:
        table[market_route(market)] = "market_hub"
    for cid in sorted(assignment.published):
        table[corridor_route(market, market.corridor_by_id(cid))] = "corridor"
    for row in sorted(hotels, key=lambda r: r["name"]):
        table[hotel_route(market, row["name"])] = "hotel_profile"
    table[market_route(market) + "policy-comparison/"] = "policy_comparison"
    return table


def build_fragment(market: MarketConfig, dest: Path) -> Path:
    """Generate ``market`` into ``dest`` and return the fragment root."""
    from scripts.generate_pettripfinder_columbus_site import run as generate_site

    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    rc = generate_site(str(dest), market=market)
    if rc != 0:
        raise AssemblyError("fragment generation failed for %s (exit %s)"
                            % (market.market_id, rc))
    return dest


def fragment_files(root: Path) -> "OrderedDict[str, Path]":
    """``{relative_posix_path: absolute_path}`` for the publishable files."""
    out: "OrderedDict[str, Path]" = OrderedDict()
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if any(rel.startswith(p) or rel.split("/")[-1].startswith(p)
               for p in BUILD_INTERNAL_PREFIXES):
            continue
        out[rel] = path
    return out


def classify_fragment(market: MarketConfig, root: Path
                      ) -> Tuple["OrderedDict[str, Path]", List[str], List[str]]:
    """``(market_owned, discarded_globals, shadowing_violations)``.

    A fragment inevitably GENERATES the global pages -- it runs a whole-site
    generator. What it may not do is CLAIM them, so the assembler drops those
    files and checks the market's declared route table against the global set.
    A violation there means a market config has been given a namespace that
    overlaps the site's, which no amount of copy ordering can make safe.
    """
    declared = owned_routes(market)
    violations = sorted(r for r in declared if r in GLOBAL_ROUTES)
    owned: "OrderedDict[str, Path]" = OrderedDict()
    discarded: List[str] = []
    for rel, path in fragment_files(root).items():
        if rel in GLOBAL_FILES:
            discarded.append(rel)
        else:
            owned[rel] = path
    return owned, discarded, violations


# --------------------------------------------------------------------------- #
# Global surfaces.
# --------------------------------------------------------------------------- #

def _e(text: str) -> str:
    return html.escape(str(text or ""), quote=True)


def market_directory_section(entries: Sequence[Dict], *, heading: str,
                             intro: str) -> str:
    """The markets block inserted into the two global pages.

    Conservative by construction: it states each market's name, its scope, the
    number of hotels PUBLISHED there, and links to where they are. It makes no
    claim the market's own pages do not already make.
    """
    cards = []
    for entry in entries:
        cards.append(
            '<li class="ptf-market-card">'
            '<h3><a href="%s">%s</a></h3>'
            '<p class="ptf-market-scope">%s</p>'
            '<p class="ptf-market-count">%d verified pet-friendly hotel%s</p>'
            '</li>'
            % (_e(entry["route"]), _e(entry["name"]), _e(entry["scope"]),
               entry["published"], "" if entry["published"] == 1 else "s"))
    return (
        '<section class="ptf-markets" id="markets">'
        '<h2>%s</h2><p class="ptf-markets-intro">%s</p>'
        '<ul class="ptf-market-list">%s</ul></section>'
        % (_e(heading), _e(intro), "".join(cards)))


MARKETS_CSS = """
.ptf-markets{margin:2.5rem 0;padding:0 1rem}
.ptf-markets h2{font-size:1.5rem;margin:0 0 .35rem}
.ptf-markets-intro{margin:0 0 1.25rem;color:#4a5568}
.ptf-market-list{list-style:none;margin:0;padding:0;display:grid;gap:1rem;
  grid-template-columns:repeat(auto-fit,minmax(16rem,1fr))}
.ptf-market-card{border:1px solid #e2e8f0;border-radius:.5rem;padding:1rem 1.15rem;
  background:#fff}
.ptf-market-card h3{margin:0 0 .3rem;font-size:1.1rem}
.ptf-market-card a{color:#1a365d;text-decoration:none}
.ptf-market-card a:hover{text-decoration:underline}
.ptf-market-scope{margin:0 0 .35rem;color:#4a5568;font-size:.92rem}
.ptf-market-count{margin:0;font-weight:600;font-size:.92rem}
"""


def _insert_after_main(page: str, block: str) -> str:
    anchor = '<main id="main">'
    if anchor not in page:
        raise AssemblyError("global page has no <main id=\"main\"> insertion anchor")
    return page.replace(anchor, anchor + block, 1)


def _insert_before_main_close(page: str, block: str) -> str:
    if "</main>" not in page:
        raise AssemblyError("global page has no </main> insertion anchor")
    return page.replace("</main>", block + "</main>", 1)


def _inject_css(page: str, css: str) -> str:
    if "</head>" not in page:
        raise AssemblyError("global page has no </head> to carry its styles")
    return page.replace("</head>", "<style>%s</style></head>" % css, 1)


def market_scope_line(market: MarketConfig) -> str:
    """A market's geographic scope, from its own configuration."""
    states = ", ".join(market.states)
    return "%s and surrounding corridors (%s)" % (market.primary_city, states)


def build_global_home(anchor_page: str, entries: Sequence[Dict]) -> str:
    """The site homepage: the approved design plus the market directory.

    Phase E is structural, not a redesign (section 11), and the homepage is a
    founder-approved asset. So this ADDS -- it does not replace. What changes
    is that the page now names every market the site serves instead of leaving
    a reader to infer there is only one.
    """
    block = market_directory_section(
        entries,
        heading="Markets we cover",
        intro="Every hotel below was verified against the property's own "
              "official source. Choose a market to see its full list.")
    return _inject_css(_insert_before_main_close(anchor_page, block), MARKETS_CSS)


def build_global_hotel_index(anchor_page: str, entries: Sequence[Dict]) -> str:
    """``/pet-friendly-hotels/`` -- the market index.

    This route is also the anchor market's hub, because ``market_route()``
    returns the category root for a legacy_unprefixed market. It therefore
    keeps the anchor's listing (removing it would delete a live directory and
    strand its inbound links) and gains the market index above it, so the page
    indexes the site's markets instead of implying the site has one.
    """
    block = market_directory_section(
        entries,
        heading="Pet-friendly hotels by market",
        intro="PetTripFinder publishes verified pet policies in the markets "
              "below.")
    return _inject_css(_insert_after_main(anchor_page, block), MARKETS_CSS)


_ROBOTS_TXT = """\
User-agent: *
Allow: /
Disallow: /go/

User-agent: GPTBot
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: anthropic-ai
Allow: /

User-agent: Googlebot
Allow: /

User-agent: Bingbot
Allow: /

Sitemap: %s/sitemap.xml
"""


def build_global_llms(entries: Sequence[Dict], base_url: str) -> str:
    """One llms.txt for the domain, naming only surfaces that exist."""
    lines = ["- Verified pet-friendly hotels: /pet-friendly-hotels/"]
    for entry in entries:
        lines.append("- %s: %s" % (entry["name"], entry["route"]))
        lines.append("- %s pet-policy comparison: %s"
                     % (entry["name"], entry["comparison_route"]))
    lines.append("- Verification methodology: /methodology/")
    return (
        "# PetTripFinder\n\n"
        "PetTripFinder verifies pet policies directly from each business's own\n"
        "official website. See /methodology/ for the full verification standard.\n\n"
        + "\n".join(lines) + "\n\n"
        "This file is informational only; it does not guarantee inclusion in any\n"
        "AI system's output.\n")


def build_global_sitemap(routes: Sequence[str], base_url: str) -> str:
    """One sitemap, from the routes that are actually on disk.

    Built from the bundle rather than from any builder's intentions: a sitemap
    is a claim about what the site serves, and the only honest source for that
    claim is the site.
    """
    body = "".join("  <url><loc>%s%s</loc></url>\n" % (base_url, r)
                   for r in routes)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + body + '</urlset>\n')


# --------------------------------------------------------------------------- #
# Gates.
# --------------------------------------------------------------------------- #

def _gate(gates: "OrderedDict[str, Dict]", gate_id: str, passed: bool,
          detail: str = "") -> bool:
    gates[gate_id] = {"pass": bool(passed), "detail": detail}
    return bool(passed)


def canonical_violations(bundle: Path, base_url: str) -> List[str]:
    """Pages whose canonical does not name the route they are served at."""
    import re
    problems: List[str] = []
    seen: Dict[str, str] = {}
    for path in sorted(bundle.rglob("index.html")):
        route = _route_of(bundle, path)
        if route.startswith("/go/"):
            continue
        text = path.read_text(encoding="utf-8")
        found = re.findall(r'<link rel="canonical" href="([^"]+)"', text)
        if len(found) > 1:
            problems.append("%s declares %d canonicals" % (route, len(found)))
            continue
        if not found:
            continue                      # absence is a separate, older gap
        want = base_url + route
        if found[0] != want:
            problems.append("%s declares canonical %s" % (route, found[0]))
        elif found[0] in seen and seen[found[0]] != route:
            problems.append("%s and %s share canonical %s"
                            % (seen[found[0]], route, found[0]))
        else:
            seen[found[0]] = route
    return problems


def broken_internal_links(bundle: Path) -> List[str]:
    """Every internal href that resolves to nothing in the bundle."""
    import re
    from urllib.parse import urlsplit

    known = set()
    for path in bundle.rglob("*"):
        if path.is_file():
            rel = path.relative_to(bundle).as_posix()
            known.add("/" + rel)
            if rel.endswith("index.html"):
                known.add("/" + rel[: -len("index.html")])
    broken: List[str] = []
    for path in sorted(bundle.rglob("*.html")):
        source = path.relative_to(bundle).as_posix()
        text = path.read_text(encoding="utf-8")
        for href in re.findall(r'href="([^"]+)"', text):
            if not href.startswith("/"):
                continue
            target = urlsplit(href).path
            if target and target not in known:
                broken.append("%s -> %s" % (source, href))
    return sorted(set(broken))


def file_hashes(root: Path) -> "OrderedDict[str, str]":
    out: "OrderedDict[str, str]" = OrderedDict()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            out[path.relative_to(root).as_posix()] = hashlib.sha256(
                path.read_bytes()).hexdigest()
    return out


def bundle_digest(hashes: Mapping[str, str]) -> str:
    """The bundle identity: one digest over the sorted per-file digests.

    Defined once so a deployer re-hashing a directory on disk (PTF-047's
    ``verify_bundle_directory``) computes exactly what the assembler wrote.
    """
    return hashlib.sha256(
        "\n".join("%s %s" % (k, v) for k, v in hashes.items()).encode("utf-8")
    ).hexdigest()


# --------------------------------------------------------------------------- #
# Assembly.
# --------------------------------------------------------------------------- #

def _contract_disagreements(market_id: str) -> List[str]:
    """What this market's own contract disagrees with, or []."""
    from scripts.pettripfinder.release_contracts import verify_contract
    try:
        return list(verify_contract(market_id))
    except Exception as exc:                                  # noqa: BLE001
        return ["contract could not be verified: %s" % exc]


def _run_global_publish_gates(gates, chosen, context, bundle, headers_bytes,
                              redirects_bytes) -> None:
    """The five publish gates, reused rather than reimplemented.

    ``assemble_netlify_bundle._run_publish_gates`` is the one implementation of
    "does this directory look like a publishable Netlify site". It needs a
    contract only for its shared ``publish`` section -- forbidden basenames,
    extensions and path segments -- which every market states identically, so
    a participating market's contract is the right input and copying the rules
    here would be a second answer to a settled question.
    """
    from scripts.pettripfinder.assemble_netlify_bundle import _run_publish_gates
    from scripts.pettripfinder.release_contracts import load_contract
    contract = load_contract(sorted(m.market_id for m in chosen)[0])
    _run_publish_gates(gates, contract, context, bundle, headers_bytes,
                       redirects_bytes)


def _run_participation_gates(gates, chosen, eligibility) -> None:
    """Only approved markets, and every one of them contract-clean.

    ``select_markets`` asks whether a market can ASSEMBLE. It does not ask
    whether the market has a reviewed release contract, so today Cincinnati and
    Detroit are kept out of the bundle only because they publish nothing --
    incidental protection that would evaporate the moment either gained
    inventory. This makes the contract a condition of participation.
    """
    from scripts.pettripfinder.release_contracts import available_market_ids
    contracted = set(available_market_ids())
    included = sorted(m.market_id for m in chosen)

    missing = [mid for mid in included if mid not in contracted]
    _gate(gates, "global.every_included_market_has_a_contract",
          not missing, "without a contract: %s" % missing)

    disagreeing = {mid: _contract_disagreements(mid) for mid in included}
    disagreeing = {mid: rows for mid, rows in disagreeing.items() if rows}
    _gate(gates, "global.every_included_market_contract_verifies",
          not disagreeing,
          "; ".join("%s: %s" % (mid, rows[0])
                    for mid, rows in list(disagreeing.items())[:3]))

    ineligible = sorted(row["market_id"] for row in eligibility
                        if not row["participates"])
    leaked = sorted(set(included) & set(ineligible))
    _gate(gates, "global.no_ineligible_market_included",
          not leaked, "ineligible but present: %s" % leaked)

    # PTF-046: participation is the founder's recorded decision, stated for
    # EVERY registered market. An unlisted market is excluded (fail closed),
    # and the silence is what this gate refuses; a status that claims a
    # readiness the source does not have is refused too, so the record can
    # neither admit a broken market nor describe a withheld one as broken.
    try:
        checks = LP.verify_participation(
            [m.market_id for m in load_markets()],
            {row["market_id"]: bool(row["assemblable"]) for row in eligibility})
        explicit_problem = [("unlisted", checks["unlisted"]),
                            ("unregistered", checks["unregistered"])]
        explicit_problem = ["%s: %s" % (k, v) for k, v in explicit_problem if v]
        source_problem = list(checks["source_disagreement"])
    except LP.LaunchParticipationError as exc:
        explicit_problem = [str(exc)]
        source_problem = ["record unreadable: %s" % exc]
    _gate(gates, "global.launch_participation_explicit",
          not explicit_problem, "; ".join(explicit_problem))
    _gate(gates, "global.launch_participation_agrees_with_source",
          not source_problem, "; ".join(source_problem[:4]))

    # What each market's own contract says it publishes must be what the
    # composed bundle actually carries for it.
    from scripts.pettripfinder.release_contracts import load_contract
    mismatched = []
    for market in chosen:
        stated = (load_contract(market.market_id).get("public_surface") or {}
                  ).get("public_hotel_profile_count")
        actual = len(published_hotels(market))
        if stated is not None and stated != actual:
            mismatched.append("%s states %s, bundle carries %d"
                              % (market.market_id, stated, actual))
    _gate(gates, "global.market_profile_counts_match_contracts",
          not mismatched, "; ".join(mismatched))


def _run_migration_gate(gates, bundle) -> None:
    """Every route the live site publishes must still exist here.

    PTF-...-DEPLOYMENT-AND-LIVE-VERIFICATION-044 found production serving 132
    Columbus routes under the unprefixed namespace. Columbus is the anchor, so
    the multi-market bundle keeps every one of them -- but "keeps" is a claim
    about a specific list, and the list is committed so a later change that
    drops one fails here instead of in a search index.

    A route that genuinely retires needs a redirect or a recorded decision, not
    a silent 404.
    """
    if not LIVE_ROUTE_INVENTORY.is_file():
        _gate(gates, "global.live_routes_preserved", False,
              "no live route inventory committed at %s"
              % LIVE_ROUTE_INVENTORY.name)
        return
    live = [line.strip() for line
            in LIVE_ROUTE_INVENTORY.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")]
    on_disk = {_route_of(bundle, p) for p in bundle.rglob("index.html")}
    missing = sorted(route for route in live if route not in on_disk)
    _gate(gates, "global.live_routes_preserved", not missing,
          "live routes with no successor: %s" % missing[:6])


def assemble(output: str, *, context: str = "production",
             base_url: str = "https://pettripfinder.com",
             markets: Optional[Sequence[MarketConfig]] = None,
             keep_fragments: bool = False) -> Dict:
    """Build every assemblable market and compose ONE bundle at ``output``.

    Returns the global bundle manifest. Raises :class:`AssemblyError` on any
    failed gate, leaving the destination untouched -- a partially merged
    multi-market bundle is worse than none, because it looks complete.
    """
    if context not in VALID_CONTEXTS:
        raise AssemblyError(
            "context must be one of %s, got %r -- a deployable bundle states "
            "which context it is FOR, and inferring it is how a preview "
            "noindex reaches production" % (list(VALID_CONTEXTS), context))
    out_root = Path(output)
    work = out_root / ".assemble_work"
    bundle = work / "site"
    gates: "OrderedDict[str, Dict]" = OrderedDict()

    chosen, eligibility = select_markets(markets)
    if not chosen:
        raise AssemblyError("no market satisfies the assembly conditions: %s"
                            % json.dumps(eligibility))
    anchor = anchor_market(chosen)

    if work.exists():
        shutil.rmtree(work)
    bundle.mkdir(parents=True)

    fragments: "OrderedDict[str, Dict]" = OrderedDict()
    route_owner: "OrderedDict[str, str]" = OrderedDict()
    collisions: List[str] = []
    shadowing: List[str] = []
    anchor_pages: Dict[str, str] = {}

    for market in chosen:
        frag_root = build_fragment(market, work / "fragments" / market.market_id)
        owned, discarded, violations = classify_fragment(market, frag_root)
        shadowing.extend("%s claims global route %s" % (market.market_id, r)
                         for r in violations)
        if market.market_id == anchor.market_id:
            for rel in GLOBAL_FILES:
                path = frag_root / rel
                if path.is_file() and rel.endswith(".html"):
                    anchor_pages[rel] = path.read_text(encoding="utf-8")

        for rel, path in owned.items():
            dest = bundle / rel
            if rel in route_owner:
                # Shared, byte-identical assets (the stylesheets, the review
                # imagery) are not a collision: they are the same file. A
                # DIFFERING file at one route is, and it names both owners.
                if path.read_bytes() == dest.read_bytes():
                    continue
                collisions.append(
                    "%s claimed by %s and %s" % (_route_of(frag_root, path),
                                                 route_owner[rel], market.market_id))
                continue
            route_owner[rel] = market.market_id
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, dest)

        declared = owned_routes(market)
        fragments[market.market_id] = OrderedDict([
            ("market_id", market.market_id),
            ("market_name", market.market_name),
            ("route_mode", market.route_mode),
            ("hub_route", market_route(market)),
            ("comparison_route", market_route(market) + "policy-comparison/"),
            ("hotel_routes", sorted(r for r, k in declared.items()
                                    if k == "hotel_profile")),
            ("corridor_routes", sorted(r for r, k in declared.items()
                                       if k == "corridor")),
            ("published_count", sum(1 for k in declared.values()
                                    if k == "hotel_profile")),
            ("files_contributed", len(owned)),
            ("globals_discarded", sorted(discarded)),
        ])

    _gate(gates, "assembly.no_route_collisions", not collisions,
          "; ".join(collisions[:6]))
    _gate(gates, "assembly.no_global_shadowing", not shadowing,
          "; ".join(shadowing[:6]))
    missing_pages = [rel for rel in ("index.html", "pet-friendly-hotels/index.html",
                                     "about/index.html", "contact/index.html",
                                     "methodology/index.html")
                     if rel not in anchor_pages]
    if not _gate(gates, "assembly.anchor_supplies_global_shell", not missing_pages,
                 "missing=%s" % missing_pages):
        raise AssemblyError("anchor market %s did not generate the global shell: %s"
                            % (anchor.market_id, missing_pages))

    # ---- global surfaces, written exactly once --------------------------
    entries = [OrderedDict([
        ("market_id", m.market_id),
        ("name", m.market_name),
        ("route", market_route(m)),
        ("comparison_route", market_route(m) + "policy-comparison/"),
        ("scope", market_scope_line(m)),
        ("published", fragments[m.market_id]["published_count"]),
    ]) for m in chosen]
    # Navigation visibility is a separate decision from assembly (section 13).
    visible = [e for e, m in zip(entries, chosen) if m.show_in_navigation]

    (bundle / "index.html").write_text(
        build_global_home(anchor_pages["index.html"], visible),
        encoding="utf-8", newline="\n")
    (bundle / "pet-friendly-hotels").mkdir(parents=True, exist_ok=True)
    (bundle / "pet-friendly-hotels" / "index.html").write_text(
        build_global_hotel_index(anchor_pages["pet-friendly-hotels/index.html"], visible),
        encoding="utf-8", newline="\n")
    for rel in ("about/index.html", "contact/index.html", "methodology/index.html"):
        target = bundle / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(anchor_pages[rel], encoding="utf-8", newline="\n")

    (bundle / "robots.txt").write_text(_ROBOTS_TXT % base_url,
                                       encoding="utf-8", newline="\n")
    (bundle / "llms.txt").write_text(build_global_llms(visible, base_url),
                                     encoding="utf-8", newline="\n")

    # Control files, from the TRACKED sources, before the sitemap is built so
    # the bundle on disk is the bundle that gets gated and hashed.
    headers_bytes = HEADERS_SOURCES[context].read_bytes()
    redirects_bytes = REDIRECTS_SOURCE.read_bytes()
    (bundle / "_headers").write_bytes(headers_bytes)
    (bundle / "_redirects").write_bytes(redirects_bytes)

    indexable = sorted(
        r for r in (_route_of(bundle, p) for p in bundle.rglob("index.html"))
        if not r.startswith("/go/"))
    (bundle / "sitemap.xml").write_text(build_global_sitemap(indexable, base_url),
                                        encoding="utf-8", newline="\n")

    # ---- gates over the composed bundle ---------------------------------
    # The five publish gates are the SAME implementation the per-market
    # assembler runs, called with a participating market's contract. Their
    # publish section is a shared one -- PTF-...-VOCABULARY-043 proved every
    # market states it identically -- so this is one rule applied to the
    # composed artifact, not a second copy of it.
    _run_global_publish_gates(gates, chosen, context, bundle,
                              headers_bytes, redirects_bytes)
    _run_participation_gates(gates, chosen, eligibility)
    _run_migration_gate(gates, bundle)
    # PTF-MEASUREMENT-001. The measurement contract and the affiliate
    # authority are gated on the COMPOSED bundle, the artifact that ships.
    # Both modules own their gates; the assembler only records them.
    from scripts.pettripfinder.affiliate_destinations import run_affiliate_gates
    from scripts.pettripfinder.measurement import (
        config_sha256 as measurement_config_sha256, run_measurement_gates,
    )
    measurement = run_measurement_gates(gates, _gate, bundle)
    run_affiliate_gates(gates, _gate, market_ids=[m.market_id for m in chosen])

    broken = broken_internal_links(bundle)
    _gate(gates, "content.zero_broken_links", not broken, "; ".join(broken[:6]))

    canon = canonical_violations(bundle, base_url)
    _gate(gates, "content.canonical_uniqueness", not canon, "; ".join(canon[:6]))

    sitemap_routes = set(indexable)
    on_disk = {r for r in (_route_of(bundle, p) for p in bundle.rglob("index.html"))
               if not r.startswith("/go/")}
    _gate(gates, "content.sitemap_is_the_site", sitemap_routes == on_disk,
          "only_in_sitemap=%s only_on_disk=%s"
          % (sorted(sitemap_routes - on_disk)[:4], sorted(on_disk - sitemap_routes)[:4]))
    _gate(gates, "content.sitemap_excludes_go",
          not any("/go/" in r for r in sitemap_routes), "")

    go_routes = [r for r in (_route_of(bundle, p) for p in bundle.rglob("index.html"))
                 if r.startswith("/go/")]
    _gate(gates, "content.go_routes_unique", len(go_routes) == len(set(go_routes)), "")

    failing = {gid: res for gid, res in gates.items() if not res["pass"]}
    hashes = file_hashes(bundle)
    manifest = OrderedDict([
        ("schema", BUNDLE_SCHEMA),
        ("generated_from_commit", _git_head()),
        ("context", context),
        ("base_url", base_url),
        ("anchor_market", anchor.market_id),
        ("market_fragments_included", [m.market_id for m in chosen]),
        ("markets_registered_but_excluded",
         [r for r in eligibility if not r["participates"]]),
        ("markets_publicly_navigable", [e["market_id"] for e in visible]),
        ("fragments", fragments),
        ("global_routes", list(GLOBAL_ROUTES)),
        ("total_html_pages", sum(1 for p in bundle.rglob("*.html"))),
        ("total_files", len(hashes)),
        ("sitemap_route_count", len(indexable)),
        ("broken_links", len(broken)),
        ("collision_count", len(collisions)),
        ("global_shadowing_count", len(shadowing)),
        ("canonical_violations", len(canon)),
        ("bundle_sha256", bundle_digest(hashes)),
        ("control_files", OrderedDict([
            ("headers_source",
             HEADERS_SOURCES[context].relative_to(_REPO_ROOT).as_posix()),
            ("headers_sha256", hashlib.sha256(headers_bytes).hexdigest()),
            ("redirects_source",
             REDIRECTS_SOURCE.relative_to(_REPO_ROOT).as_posix()),
            ("redirects_sha256", hashlib.sha256(redirects_bytes).hexdigest()),
        ])),
        ("sitemap_sha256", hashlib.sha256(
            (bundle / "sitemap.xml").read_bytes()).hexdigest()),
        # PTF-MEASUREMENT-001: which measurement contract this bundle was
        # built under. Pinned so a deployer can tell a measured bundle from an
        # unmeasured one without diffing 2,000 pages.
        ("measurement", OrderedDict([
            ("config_source", "deploy/netlify/measurement.json"),
            ("config_sha256", measurement_config_sha256()),
            ("enabled", measurement.active),
            ("provider_kind", measurement.provider.kind),
        ])),
        # PTF-046: the founder's participation record this bundle was composed
        # under, pinned like a control file. A different record is a different
        # participation set and therefore a different artifact.
        ("launch_participation", OrderedDict([
            ("source", LP.PARTICIPATION_PATH.relative_to(_REPO_ROOT).as_posix()),
            ("sha256", LP.participation_sha256()),
            ("founder_authorized", LP.authorized_market_ids()),
        ])),
        ("participating_markets", [
            OrderedDict([
                ("market_id", m.market_id),
                ("published_profiles", len(published_hotels(m))),
                ("release_contract",
                 "deploy/netlify/release_contracts/%s.json" % m.market_id),
                ("contract_disagreements", _contract_disagreements(m.market_id)),
            ]) for m in chosen]),
        ("all_gates_pass", not failing),
        ("gates", dict(gates)),
        # Phase E assembles; it does not authorize a deploy.
        ("deployment_authorized", False),
    ])

    if failing:
        raise AssemblyError("global assembly gates failed: %s" % list(failing))

    final = out_root / "site"
    if final.exists():
        shutil.rmtree(final)
    final.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(bundle), str(final))
    (out_root / "global_bundle_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    (out_root / "file_hash_manifest.json").write_text(
        json.dumps({"files": dict(hashes)}, indent=2) + "\n",
        encoding="utf-8", newline="\n")
    if not keep_fragments:
        shutil.rmtree(work, ignore_errors=True)
    return dict(manifest)


def _git_head() -> str:
    import subprocess
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(_REPO_ROOT),
                              capture_output=True, check=True).stdout.decode().strip()
    except Exception:                                # pragma: no cover - git absent
        return "unknown"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True,
                        help="bundle destination (use a SHORT path on Windows)")
    parser.add_argument("--base-url", default="https://pettripfinder.com")
    parser.add_argument("--keep-fragments", action="store_true")
    args = parser.parse_args(argv)

    manifest = assemble(args.output, base_url=args.base_url,
                        keep_fragments=args.keep_fragments)
    print("=== GLOBAL BUNDLE ===")
    print("  anchor market      :", manifest["anchor_market"])
    print("  markets assembled  :", ", ".join(manifest["market_fragments_included"]))
    for row in manifest["markets_registered_but_excluded"]:
        print("  excluded           : %s (published %d < %d)"
              % (row["market_id"], row["published_count"],
                 row["minimum_published_hotels"]))
    for mid, frag in manifest["fragments"].items():
        print("    %-28s %3d hotels, %2d corridors, hub %s"
              % (mid, frag["published_count"], len(frag["corridor_routes"]),
                 frag["hub_route"]))
    print("  html pages         :", manifest["total_html_pages"])
    print("  sitemap routes     :", manifest["sitemap_route_count"])
    print("  broken links       :", manifest["broken_links"])
    print("  collisions         :", manifest["collision_count"])
    print("  global shadowing   :", manifest["global_shadowing_count"])
    print("  canonical problems :", manifest["canonical_violations"])
    print("  bundle sha256      :", manifest["bundle_sha256"][:16])
    print("  deployment         : NOT AUTHORIZED (Phase E assembles only)")
    return 0


if __name__ == "__main__":                            # pragma: no cover
    raise SystemExit(main())
