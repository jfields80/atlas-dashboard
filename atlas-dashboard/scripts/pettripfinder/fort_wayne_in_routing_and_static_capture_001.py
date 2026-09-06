"""PTF-FORT-WAYNE-IN-NEW-MARKET-001 -- Phases 9, 10 and 13.

Route every confirmed Fort Wayne identity, then capture its policy through the
canonical FREE static lane, then classify the result.

ROUTING (phase 9), in ladder order. The first rung that yields a URL wins, and
the rung that produced it is recorded on the row:

  OWNED_ROUTE_REUSED       a route this repository already committed
  ROUTED_OFFICIAL_SITEMAP  the brand inventory lane -- a brand's own property
                           page, reached from its own sitemap, city page or a
                           committed harvest
  ROUTED_FREE_STATIC       an official website the CVB or OpenStreetMap states
  FREE_LANE_EXHAUSTED      no free lane yields a route
  INDEPENDENT_REVIEW       an independent with no stated website
  IDENTITY_REVIEW_FIRST    the identity is not settled, so routing it would
                           bind a policy to a question

A route is bound to the identity that produced it and to nothing else. A URL a
lane stated for a DIFFERENT identity is never borrowed, and a brand's generic
city or brand page is not a property route.

CAPTURE (phase 10) runs the same gates every paid lane uses:
``acquisition.direct_http_capture.run_attempt`` -- denial markers, page health,
identity read and assessment, policy locator, reader -- and then
``market_observation_store.observation_for`` for the publication grade. One
HTTPS GET per target per run; a rerun reuses the attempt on disk. No vendor, no
browser, no price.

CLASSIFICATION (phase 13) gives each reviewed property EXACTLY ONE result. Two
rules the vocabulary exists to enforce:

  * PETS_ALLOWED IS THE READER'S CALL, NOT A FEE'S. A fee, a weight limit or a
    pet count does not by itself say a hotel accepts pets, and a structured
    ``petsAllowed`` flag is not an operative policy. Only a reader extraction of
    ``pets_allowed`` decides, and only a publication-grade one is clean.
  * SILENCE IS NOT A REFUSAL. A page that states no pet policy is SOURCE_SILENT
    and stays unresolved. It is never VERIFIED_NO_PETS.

Nothing here writes authority. The output is one report keyed on each page's own
sha256.

Outputs:
  launch_packages/pettripfinder/markets/reports/fort_wayne_in_routing_and_static_capture_001.json
  data/acquisition/fort_wayne_in_free_static_001/<slug>/attempt-01/   (gitignored)
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter, OrderedDict
from pathlib import Path

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.acquisition import direct_http_capture as DHC  # noqa: E402
from scripts.pettripfinder.acquisition import market_observation_store as MOS  # noqa: E402
from scripts.pettripfinder.brightdata import browser_capture as BC  # noqa: E402
from scripts.pettripfinder.discovery import identity_dedup as DEDUP  # noqa: E402

WORK_ORDER = "PTF-FORT-WAYNE-IN-NEW-MARKET-001"
MARKET_ID = "fort-wayne-in"
SCHEMA = "ptf-routing-and-static-capture/1.0"
RUN_ID = "fort_wayne_in_free_static_001"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
RECON = os.path.join(REPORTS, "fort_wayne_in_census_reconciliation_001.json")
BRAND = os.path.join(REPORTS, "fort_wayne_in_brand_directory_harvest_001.json")
RUN_DIR = Path(_DASH) / "data" / "acquisition" / RUN_ID
SPACING_SECONDS = 1.5

BRANDS = [
    ("MARRIOTT", r"marriott|courtyard|residence inn|springhill|fairfield|towneplace|ac hotel|aloft|westin|sheraton|moxy|element"),
    ("HILTON", r"hilton|hampton|embassy suites|homewood|home2|doubletree|tru by|tapestry|canopy|spark by"),
    ("IHG", r"holiday inn|crowne plaza|staybridge|candlewood|even hotel|avid|intercontinental|kimpton|hotel indigo"),
    ("CHOICE", r"comfort inn|comfort suites|quality inn|sleep inn|clarion|cambria|mainstay|suburban|econo lodge|rodeway|woodspring|country hearth"),
    ("WYNDHAM", r"wyndham|baymont|days inn|super 8|ramada|travelodge|la quinta|microtel|howard johnson|hawthorn|americinn|wingate"),
    ("ESA", r"extended stay america"),
    ("BEST_WESTERN", r"best western|surestay"),
    ("MOTEL6", r"motel 6|studio 6"),
    ("RED_ROOF", r"red roof"),
    ("SONESTA", r"sonesta"),
    ("DRURY", r"drury"),
    ("HYATT", r"hyatt"),
    ("MAGNUSON", r"magnuson"),
]

#: Hosts that are a brand's OWN property surface. A URL on one of these is a
#: first-party route.
_BRAND_HOSTS = ("marriott.com", "hilton.com", "ihg.com", "choicehotels.com",
                "wyndhamhotels.com", "bestwestern.com", "hyatt.com",
                "extendedstayamerica.com", "redroof.com", "motel6.com",
                "sonesta.com", "druryhotels.com", "magnusonhotels.com",
                "woodspring.com", "staybridge.com", "intownsuites.com")

#: A URL that names no single property is a lead, never a route. The second
#: alternation is the one that matters here: WoodSpring's Fort Wayne CITY page
#: sits under the same /locations/indiana/fort-wayne/ prefix as its property
#: page and differs only by having no further segment, and a brand's city page
#: is exactly the "amenity chip" of routing -- it looks like an answer and binds
#: nothing.
_NOT_A_PROPERTY_ROUTE = re.compile(
    r"(?:/(?:locations?|destinations?|find-hotels|hotel-search|search|city|"
    r"state|offers?|deals?)/?$"
    r"|/locations?/[a-z-]+/[a-z-]+/?$"
    r"|^https?://[^/]+/?$)", re.I)

#: Hosts that are a DIRECTORY, never a property route. A listing page on one of
#: these describes a hotel; it is not the hotel speaking, and capturing it would
#: read a directory's words as the property's own policy. Recorded as a host
#: rule rather than a per-row exception so a new directory lane cannot quietly
#: reintroduce the mistake.
_DIRECTORY_HOSTS = ("visitfortwayne.com", "bringfido.com", "tripadvisor.com",
                    "yelp.com", "expedia.com", "booking.com", "hotels.com",
                    "trivago.com", "kayak.com", "google.com", "facebook.com")


def is_directory_host(url):
    host = host_of(url)
    return any(host == h or host.endswith("." + h) for h in _DIRECTORY_HOSTS)


#: A page title that means the brand did not serve the property we asked for.
#: Wyndham answers 200 with a search page for a retired slug, so status alone
#: would record a dead route as a live one.
_SOFT_404_TITLE = re.compile(
    r"^\s*(search results|hotels? in |find hotels|extended stay hotels in )", re.I)

#: Words that appear in so many hotel names they distinguish nothing, so a slug
#: match built only from these is not a match at all.
_UNDISTINGUISHING = frozenset({
    "hotel", "hotels", "inn", "inns", "suites", "suite", "and", "by", "the",
    "at", "of", "motel", "lodge", "fort", "wayne", "ft", "in", "indiana",
})


def brand_of(name):
    n = (name or "").lower()
    for family, pattern in BRANDS:
        if re.search(pattern, n):
            return family
    return "INDEPENDENT"


def host_of(url):
    m = re.match(r"https?://([^/]+)", url or "")
    return m.group(1).lower().replace("www.", "") if m else ""


def is_brand_host(url):
    host = host_of(url)
    return any(host.endswith(h) for h in _BRAND_HOSTS)


def read_json(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def as_plain(obj):
    if dataclasses.is_dataclass(obj):
        return {k: as_plain(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, (list, tuple)):
        return [as_plain(x) for x in obj]
    if isinstance(obj, dict):
        return {k: as_plain(v) for k, v in obj.items()}
    return obj


def sha256_file(p):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else ""


def _digits(v):
    return re.sub(r"\D", "", v or "")[-10:]


# --------------------------------------------------------------------------- #
# Phase 9 -- routing
# --------------------------------------------------------------------------- #

def brand_routes_by_identity():
    """Property routes the brand inventory lane confirmed, keyed by the address
    and phone the BRAND'S OWN PAGE stated.

    Keyed on the brand's evidence rather than on our census name, because the
    census name is what we are trying to bind. A brand page whose identity read
    produced no name is not a route: it settled nothing.
    """
    if not os.path.exists(BRAND):
        return {}, {}
    doc = read_json(BRAND)
    by_addr, by_phone = {}, {}
    for c in doc.get("candidates") or []:
        page = c.get("page") or {}
        ident = page.get("identity") or {}
        if page.get("status") != 200 or not ident.get("name_on_page"):
            continue
        if _SOFT_404_TITLE.search(page.get("title") or ""):
            continue
        url = page.get("final_url") or c["url"]
        if _NOT_A_PROPERTY_ROUTE.search(url):
            continue
        row = OrderedDict([
            ("url", url), ("family", c["family"]),
            ("property_code", ident.get("property_code_on_page") or c.get("property_code") or ""),
            ("name_on_page", ident.get("name_on_page")),
            ("street_on_page", ident.get("address_on_page") or ""),
            ("postal_on_page", (ident.get("postal_code") or "")[:5]),
            ("phone_on_page", ident.get("phone_on_page") or ""),
            ("rung", c.get("rung", "")),
        ])
        number = re.match(r"\s*(\d+)", row["street_on_page"] or "")
        if number and row["postal_on_page"]:
            by_addr.setdefault("%s|%s" % (number.group(1), row["postal_on_page"]), row)
        phone = _digits(row["phone_on_page"])
        if phone:
            by_phone.setdefault(phone, row)
    return by_addr, by_phone


ROUTE_STATES = (
    "ROUTED_OFFICIAL_SITEMAP", "ROUTED_FREE_STATIC", "OWNED_ROUTE_REUSED",
    "FREE_LANE_EXHAUSTED", "INDEPENDENT_REVIEW", "IDENTITY_REVIEW_FIRST",
)


def brand_slugs():
    """Brand inventory rows keyed by the distinctive words of the brand's OWN
    slug, for the families whose property pages refuse a plain client.

    Marriott and Hilton both answered 403 to all 27 of their Fort Wayne property
    pages, so neither states an address we can join on. Their INVENTORIES still
    do: a URL that Marriott's own sitemap and Hilton's own city page publish is
    first-party evidence that this property exists at this route, and the slug
    the brand authored names it.

    This is a routing rung and NOT an identity confirmation. Two guards keep it
    honest:

      * a slug binds only when EXACTLY ONE inventory row matches. "Hampton Inn"
        matches fwadphx, fwadthx, fwanohx and fwaswhx alike -- four different
        buildings -- so a bare brand name binds nothing and the row falls
        through to review rather than getting whichever URL sorted first;
      * words that distinguish nothing ("hotel", "inn", "suites", "fort",
        "wayne") cannot carry a match on their own.

    The capture's own identity gate still judges whatever the route returns.
    """
    if not os.path.exists(BRAND):
        return []
    doc = read_json(BRAND)
    rows = []
    for c in doc.get("candidates") or []:
        url = c["url"]
        if _NOT_A_PROPERTY_ROUTE.search(url):
            continue
        page = c.get("page") or {}
        if _SOFT_404_TITLE.search(page.get("title") or ""):
            continue
        m = re.search(r"/(?:hotels|locations)/(?:[a-z-]+/[a-z-]+/)?([a-z0-9-]+)/?$",
                      url.rstrip("/") + "/", re.I)
        slug = (m.group(1) if m else url.rstrip("/").rsplit("/", 1)[-1]).lower()
        words = {w for w in re.split(r"[^a-z0-9]+", slug) if w}
        rows.append(OrderedDict([
            ("url", url), ("family", c["family"]),
            ("property_code", c.get("property_code") or ""),
            ("slug", slug), ("slug_words", words), ("rung", c.get("rung", "")),
        ]))
    return rows


def match_by_slug(group, rows):
    """The one inventory row this identity's name uniquely selects, or None."""
    family = brand_of(group["canonical_name"])
    if family == "INDEPENDENT":
        return None, "independent name; no brand inventory to match against"
    tokens = {w for w in re.split(r"[^a-z0-9]+", (group["canonical_name"] or "").lower())
              if w}
    distinctive = tokens - _UNDISTINGUISHING
    if not distinctive:
        return None, ("the name carries no distinguishing word once generic hotel "
                      "words are removed")
    hits = [r for r in rows
            if r["family"] == family and distinctive.issubset(r["slug_words"])]
    if len(hits) == 1:
        return hits[0], "uniquely matched %r in the %s inventory" % (
            hits[0]["slug"], family)
    if len(hits) > 1:
        return None, ("ambiguous: %d %s inventory rows match this name (%s); a "
                      "bare brand name is not an identity"
                      % (len(hits), family, ", ".join(sorted(h["slug"] for h in hits))))
    return None, "no %s inventory row matches this name" % family


def route(group, by_addr, by_phone, slug_rows):
    """One route decision for one identity."""
    if group["classification"] != "EXACT_UNIQUE_IDENTITY":
        return OrderedDict([
            ("route_state", "IDENTITY_REVIEW_FIRST"), ("url", ""),
            ("route_basis", ""),
            ("why", "the identity is %s; routing it would bind a policy to an "
                    "unsettled question" % group["classification"])])

    number = re.match(r"\s*(\d+)", group.get("street") or "")
    addr_key = ("%s|%s" % (number.group(1), group["postal_code"])
                if number and group["postal_code"] else "")
    phone = _digits(group.get("phone"))

    hit = (by_addr.get(addr_key) if addr_key else None) or \
          (by_phone.get(phone) if phone else None)
    if hit:
        return OrderedDict([
            ("route_state", "ROUTED_OFFICIAL_SITEMAP"), ("url", hit["url"]),
            ("route_basis", "brand property page whose OWN address/phone matches "
                            "this identity"),
            ("brand_family", hit["family"]), ("property_code", hit["property_code"]),
            ("brand_rung", hit["rung"]),
            ("why", "bound on %s stated by the brand's own page"
                    % ("street number + postal" if addr_key and by_addr.get(addr_key)
                       else "telephone"))])

    hit, why = match_by_slug(group, slug_rows)
    if hit:
        return OrderedDict([
            ("route_state", "ROUTED_OFFICIAL_SITEMAP"), ("url", hit["url"]),
            ("route_basis", "brand's own inventory slug, uniquely matched -- the "
                            "property page refuses a plain client, so this is a "
                            "ROUTE and not an identity confirmation"),
            ("brand_family", hit["family"]), ("property_code", hit["property_code"]),
            ("brand_rung", hit["rung"]), ("identity_confirmed_by_brand_page", False),
            ("why", why)])

    url = (group.get("official_url") or "").strip()
    if url and is_directory_host(url):
        url = ""
    if url and not _NOT_A_PROPERTY_ROUTE.search(url):
        return OrderedDict([
            ("route_state", "ROUTED_FREE_STATIC"), ("url", url),
            ("route_basis", "official website stated by OpenStreetMap for this "
                            "identity"),
            ("why", "first-party website on %s" % (host_of(url) or "an unknown host"))])

    family = brand_of(group["canonical_name"])
    if family == "INDEPENDENT":
        return OrderedDict([
            ("route_state", "INDEPENDENT_REVIEW"), ("url", ""), ("route_basis", ""),
            ("why", "independent property; no free lane stated a website for it")])
    return OrderedDict([
        ("route_state", "FREE_LANE_EXHAUSTED"), ("url", ""), ("route_basis", ""),
        ("why", "%s property, and no free lane resolved it: %s" % (family, why))])


# --------------------------------------------------------------------------- #
# Phase 10 / 13 -- capture and classify
# --------------------------------------------------------------------------- #

def capture(row, group, args, stats):
    key = group["identity_key"]
    name = group["canonical_name"]
    family = brand_of(name)
    slug = group["slug"] or re.sub(r"[^a-z0-9]+", "-", key).strip("-")
    attempt_dir = RUN_DIR / slug / "attempt-01"
    target = BC.CaptureTarget(
        slug=slug, hotel=name, requested_url=row["url"],
        property_code=DEDUP.property_code({"official_url": row["url"]}),
        market_id=MARKET_ID, normalized_name=key, identity_key=key,
        street_identity="", expected_postal_code=group.get("postal_code") or "",
        expected_street=group.get("street") or "",
        expected_phone=group.get("phone") or "",
        expected_locality=group.get("city") or "",
        identity_brand=family, census_matched=True)
    record_path = RUN_DIR / slug / "attempt-01.record.json"
    if record_path.is_file() and not args.refetch:
        rec = json.loads(record_path.read_text(encoding="utf-8"))
    else:
        time.sleep(SPACING_SECONDS)
        attempt, payload = DHC.run_attempt(target, 1, run_dir=RUN_DIR, brand=family)
        stats["requests"] += 1
        a = as_plain(attempt)
        rec = OrderedDict([
            ("outcome", a.get("outcome")), ("final_url", a.get("final_url")),
            ("title", a.get("title")), ("detail", a.get("detail")),
            ("body_chars", a.get("body_chars")), ("identity", a.get("identity")),
            ("fetched_at", a.get("started_at"))])
        record_path.parent.mkdir(parents=True, exist_ok=True)
        record_path.write_text(json.dumps(rec, indent=1, ensure_ascii=False, default=str),
                               encoding="utf-8")

    row["brand"] = family
    row["outcome"] = rec.get("outcome")
    row["final_url"] = rec.get("final_url")
    row["title"] = (rec.get("title") or "")[:160]
    row["detail"] = (rec.get("detail") or "")[:300]
    row["identity_assessment"] = rec.get("identity")
    row["page_sha256"] = sha256_file(attempt_dir / "rendered.html")
    row["captured_at"] = rec.get("fetched_at")
    row["artifact_dir"] = (str(attempt_dir.relative_to(_DASH))
                           if attempt_dir.is_dir() else "")

    if rec.get("outcome") == "VALID" and (attempt_dir / "policy-block.txt").is_file():
        result = {
            "identity_key": key, "canonical_name": name, "brand": family,
            "corridor": "", "source_url": row["url"], "outcome": "VALID",
            "final_url": rec.get("final_url") or row["url"],
            "artifact_dir": str(attempt_dir),
            "identity_confirmed": bool((rec.get("identity") or {}).get("confirmed", True)),
            "locator_strategy": "",
        }
        census_row = {
            "canonical_name": name, "address": group.get("street") or "",
            "postal_code": group.get("postal_code") or "",
            "phone": group.get("phone") or "", "city": group.get("city") or "",
        }
        try:
            obs, grade, refusal = MOS.observation_for(
                result, run_id=RUN_ID, market_id=MARKET_ID, census_row=census_row)
            extraction = ((obs or {}).get("observation") or {}).get("extraction") or {}
            row["observation"] = OrderedDict([
                ("extraction", extraction),
                ("evidence", ((obs or {}).get("observation") or {}).get("evidence")),
                ("withheld_fields", (obs or {}).get("withheld_fields")),
                ("publication_grade", grade), ("refusal_reason", refusal),
                ("reader_provenance", (obs or {}).get("reader_provenance")),
            ])
            pets = extraction.get("pets_allowed")
            verdict = str((grade or {}).get("verdict")
                          or (grade or {}).get("grade") or "")
            publication_grade = bool(grade) and verdict.endswith("CONFIRMED")
            if pets is True:
                row["classification"] = ("CLEAN_PET_FRIENDLY" if publication_grade
                                         else "PET_FRIENDLY_NOT_PUBLICATION_GRADE")
            elif pets is False:
                row["classification"] = ("CLEAN_VERIFIED_NO_PETS" if publication_grade
                                         else "NO_PETS_NOT_PUBLICATION_GRADE")
            else:
                # A located policy block that never says whether pets are
                # accepted. Fees and weights may well be in it; none of them is
                # an acceptance, so the row stays unresolved.
                row["classification"] = "SOURCE_SILENT"
        except Exception as exc:  # noqa: BLE001
            row["observation_error"] = repr(exc)
            row["classification"] = "CAPTURE_FAILED"
    else:
        row["classification"] = {
            "POLICY_NOT_FOUND": "POLICY_NOT_FOUND",
            "UNHYDRATED": "NEEDS_ATTENDED_RENDER",
            "ACCESS_DENIED": "ACCESS_BLOCKED_PLAIN_CLIENT",
            "IDENTITY_MISMATCH": "IDENTITY_MISMATCH",
            "BLANK_PAGE": "NEEDS_ATTENDED_RENDER",
            "NAVIGATION_FAILED": "CAPTURE_FAILED",
            "UNEXPECTED_PAGE": "IDENTITY_MISMATCH",
        }.get(rec.get("outcome") or "", "CAPTURE_FAILED")
    return row


def build(args):
    recon = read_json(RECON)
    groups = recon["groups"]
    by_addr, by_phone = brand_routes_by_identity()
    slug_rows = brand_slugs()
    print("brand routes: %d by address, %d by phone, %d inventory slugs"
          % (len(by_addr), len(by_phone), len(slug_rows)), flush=True)

    rows = []
    for g in groups:
        r = route(g, by_addr, by_phone, slug_rows)
        r = OrderedDict([("identity_key", g["identity_key"]),
                         ("canonical_name", g["canonical_name"]),
                         ("street", g.get("street") or ""),
                         ("postal_code", g.get("postal_code") or ""),
                         ("census_classification", g["classification"])] + list(r.items()))
        rows.append(r)

    routable = [r for r in rows if r["url"]]
    if args.max_captures:
        routable = routable[: args.max_captures]
    print("routed", len(routable), "of", len(rows), "-- capturing", flush=True)

    stats = {"requests": 0}
    index = {g["identity_key"]: g for g in groups}
    for i, r in enumerate(routable):
        capture(r, index[r["identity_key"]], args, stats)
        if (i + 1) % 10 == 0:
            print("  captured", i + 1, "of", len(routable),
                  "requests", stats["requests"], flush=True)

    captured = [r for r in rows if r.get("classification")]
    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER),
        ("phase", "9/10/13 -- routing, free static policy capture, classification"),
        ("market_id", MARKET_ID), ("run_id", RUN_ID),
        ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("what_this_is",
         "Every confirmed identity routed by the ladder, then captured through the "
         "same canonical gates the paid lanes use, then given exactly one "
         "classification. A route is bound to the identity whose own address or "
         "telephone the brand page states, never borrowed from a neighbouring row. "
         "pets_allowed is decided ONLY by a reader extraction -- never by a fee, a "
         "weight limit, a pet count or a structured flag -- and a page that states no "
         "pet policy is SOURCE_SILENT, never VERIFIED_NO_PETS."),
        ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("free_http_requests", stats["requests"]),
        ("counts", OrderedDict([
            ("identities", len(rows)),
            ("by_route_state",
             OrderedDict(sorted(Counter(r["route_state"] for r in rows).items()))),
            ("routed", sum(1 for r in rows if r["url"])),
            ("captured", len(captured)),
            ("by_capture_outcome",
             OrderedDict(sorted(Counter(r.get("outcome") or "-" for r in captured).items()))),
            ("by_classification",
             OrderedDict(sorted(Counter(r["classification"] for r in captured).items()))),
        ])),
        ("rows", rows),
    ])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(
        REPORTS, "fort_wayne_in_routing_and_static_capture_001.json"))
    ap.add_argument("--max-captures", type=int, default=0)
    ap.add_argument("--refetch", action="store_true")
    args = ap.parse_args(argv)
    rep = build(args)
    with open(args.out, "wb") as fh:
        fh.write((json.dumps(rep, indent=1, ensure_ascii=False, default=str) + "\n").encode("utf-8"))
    print("written", os.path.relpath(args.out, _DASH))
    print(json.dumps(rep["counts"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
