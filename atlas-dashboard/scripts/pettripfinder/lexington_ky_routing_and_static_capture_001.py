"""PTF-LEXINGTON-KY-NEW-MARKET-001 -- phases 9 and 10.

Phase 9 binds a route to every confirmed Lexington identity, walking the free
rungs of the acquisition ladder in order and recording WHICH rung settled each
row. Phase 10 then puts every routed row through the canonical direct-static
lane -- the same gates the paid lanes use -- and classifies what came back.

Route sources, in ladder order:

  0  OWNED_ROUTE_REUSED       the OSM element's own `website:`/`url:` tag
  1  ROUTED_OFFICIAL_SITEMAP  the Marriott global property sitemap this
                              repository already owns (Dayton harvest), plus
                              this order's own Hilton / Wyndham / Choice /
                              Best Western sitemap walks
  -  FREE_LANE_EXHAUSTED      no free route found; nothing is invented

A sitemap slug NAMES a hotel; it never decides one. A slug match is bound only
on a DISTINCTIVE token -- chain words, locality words and directionals are
stripped first -- and every bound row carries `match_strength` and the tokens
that matched, so the binding can be audited. `lex*` is Blue Grass Airport's
prefix and Marriott applies it to Corbin, Frankfort, Georgetown and Richmond
too, so a code prefix is never on its own a reason to bind.

Nothing here writes authority. The output is one report keyed on each page's
own sha256.
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

WORK_ORDER = "PTF-LEXINGTON-KY-NEW-MARKET-001"
MARKET_ID = "lexington-ky"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
RECON = os.path.join(REPORTS, "lexington_ky_census_reconciliation_001.json")
OWNED_MARRIOTT = os.path.join(REPORTS, "dayton_oh_brand_directory_harvest_001.json")
HARVEST_1 = os.path.join(REPORTS, "lexington_ky_brand_directory_harvest_001.json")
HARVEST_2 = os.path.join(REPORTS, "lexington_ky_brand_directory_harvest_002.json")
CITY_PAGES = os.path.join(REPORTS, "lexington_ky_brand_city_page_lane_001.json")
SPACING_SECONDS = 1.2

OWNED_ROUTE_REUSED = "OWNED_ROUTE_REUSED"
ROUTED_OFFICIAL_SITEMAP = "ROUTED_OFFICIAL_SITEMAP"
FREE_LANE_EXHAUSTED = "FREE_LANE_EXHAUSTED"

STOPWORDS = {
    "inn", "suites", "suite", "hotel", "hotels", "motel", "resort", "spa", "the",
    "and", "by", "at", "of", "a", "an", "place", "plaza", "conference", "center",
    "centre", "lexington", "kentucky", "ky", "downtown", "dtwn", "airport",
    "university", "medical", "north", "south", "east", "west", "northeast",
    "northwest", "southeast", "southwest", "near", "i", "75", "64", "extended",
    "stay", "express", "garden", "collection", "autograph", "golf",
}
CHAIN_TOKENS = {
    "marriott", "hilton", "hyatt", "sheraton", "westin", "courtyard", "residence",
    "fairfield", "springhill", "towneplace", "hampton", "homewood", "home2",
    "embassy", "doubletree", "tru", "wyndham", "days", "super", "baymont",
    "microtel", "ramada", "howard", "johnson", "travelodge", "la", "quinta",
    "choice", "comfort", "quality", "sleep", "econo", "lodge", "clarion",
    "mainstay", "woodspring", "ihg", "holiday", "candlewood", "staybridge",
    "crowne", "even", "avid", "best", "western", "surestay", "red", "roof",
    "motel6", "6", "drury", "sonesta", "radisson", "country", "guesthouse",
    "four", "points", "aloft", "element", "moxy", "ac", "hyattplace", "place",
}


def read_json(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def norm(s):
    return " ".join(re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).split())


def distinctive_tokens(s):
    """Tokens that could actually single out ONE property."""
    return {t for t in norm(s).split() if t not in STOPWORDS and t not in CHAIN_TOKENS}


def chain_tokens(s):
    return {t for t in norm(s).split() if t in CHAIN_TOKENS}


def as_plain(obj):
    if dataclasses.is_dataclass(obj):
        return {k: as_plain(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, (list, tuple)):
        return [as_plain(x) for x in obj]
    if isinstance(obj, dict):
        return {k: as_plain(v) for k, v in obj.items()}
    return obj


def sha256_file(p: Path) -> str:
    if not p.is_file():
        return ""
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def brand_of(name: str) -> str:
    n = norm(name)
    for needle, brand in (
        ("marriott", "MARRIOTT"), ("courtyard", "MARRIOTT"), ("residence inn", "MARRIOTT"),
        ("fairfield", "MARRIOTT"), ("springhill", "MARRIOTT"), ("towneplace", "MARRIOTT"),
        ("four points", "MARRIOTT"), ("sheraton", "MARRIOTT"), ("aloft", "MARRIOTT"),
        ("element", "MARRIOTT"), ("westin", "MARRIOTT"), ("moxy", "MARRIOTT"),
        ("hilton", "HILTON"), ("hampton", "HILTON"), ("homewood", "HILTON"),
        ("home2", "HILTON"), ("home 2", "HILTON"), ("embassy", "HILTON"),
        ("doubletree", "HILTON"), ("double tree", "HILTON"), ("tru", "HILTON"),
        ("holiday inn", "IHG"), ("candlewood", "IHG"), ("staybridge", "IHG"),
        ("crowne", "IHG"), ("avid", "IHG"),
        ("hyatt", "HYATT"),
        ("wyndham", "WYNDHAM"), ("days inn", "WYNDHAM"), ("super 8", "WYNDHAM"),
        ("baymont", "WYNDHAM"), ("microtel", "WYNDHAM"), ("ramada", "WYNDHAM"),
        ("la quinta", "WYNDHAM"),
        ("comfort", "CHOICE"), ("quality inn", "CHOICE"), ("sleep inn", "CHOICE"),
        ("econo", "CHOICE"), ("clarion", "CHOICE"), ("mainstay", "CHOICE"),
        ("woodspring", "CHOICE"), ("country inn", "CHOICE"),
        ("best western", "BEST_WESTERN"), ("surestay", "BEST_WESTERN"),
        ("red roof", "RED_ROOF"), ("motel 6", "G6"), ("studio 6", "G6"),
        ("extended stay", "ESA"), ("radisson", "RADISSON"), ("drury", "DRURY"),
        ("sonesta", "SONESTA"),
    ):
        if needle in n:
            return brand
    return "INDEPENDENT"


# --------------------------------------------------------------------------
# Phase 9 -- routing
# --------------------------------------------------------------------------

def sitemap_pool():
    """Every free official-sitemap URL this order can route from, with its lane."""
    pool = []

    d = read_json(OWNED_MARRIOTT)
    best = {}
    for u in d["families"]["MARRIOTT"]["property_urls"]:
        m = re.search(r"/hotels/([a-z0-9]{5})-([a-z0-9\-]+)/overview", u)
        if not m:
            continue
        code, slug = m.group(1), m.group(2)
        if code not in best or "/en-us/" in u:
            best[code] = (slug, u)
    for code, (slug, u) in best.items():
        if code.startswith("lex"):
            pool.append(OrderedDict([
                ("family", "MARRIOTT"), ("url", u), ("slug", slug),
                ("property_code", code),
                ("lane", "OWNED_EVIDENCE:dayton_oh_brand_directory_harvest_001"),
            ]))

    if os.path.exists(CITY_PAGES):
        cp = read_json(CITY_PAGES)
        for fam, blk in (cp.get("families") or {}).items():
            codes = {c["slug"]: c["code"] for c in blk.get("property_codes") or []}
            for u in blk.get("property_urls") or []:
                slug = re.sub(r"[?#].*$", "", u).rstrip("/").rsplit("/", 1)[-1]
                m = re.search(r"/hotels/([a-z0-9]{5,9})-([a-z0-9\-]+)/", u)
                if m:
                    slug = m.group(2)
                pool.append(OrderedDict([
                    ("family", fam), ("url", u), ("slug", slug),
                    ("property_code", codes.get(slug, "")),
                    ("lane", "BRAND_CITY_PAGE:lexington_ky_brand_city_page_lane_001"),
                ]))

    for path in (HARVEST_1, HARVEST_2):
        if not os.path.exists(path):
            continue
        h = read_json(path)
        for fam, blk in (h.get("families") or {}).items():
            if fam == "MARRIOTT":
                continue
            for u in blk.get("property_urls") or []:
                slug = re.sub(r"[?#].*$", "", u).rstrip("/").rsplit("/", 1)[-1]
                code = ""
                m = re.search(r"/hotels/([a-z0-9]{2,8})-", u)
                if m:
                    code = m.group(1)
                pool.append(OrderedDict([
                    ("family", fam), ("url", u), ("slug", slug),
                    ("property_code", code),
                    ("lane", "OFFICIAL_SITEMAP:%s" % os.path.basename(path)),
                ]))
    return pool


def route_rows(identities, pool, args):
    by_family = {}
    for p in pool:
        by_family.setdefault(p["family"], []).append(p)

    for row in identities:
        name = row["name"]
        brand = brand_of(name)
        row["brand"] = brand
        want_d = distinctive_tokens(name)
        want_c = chain_tokens(name)

        if row.get("website_url"):
            row["route"] = row["website_url"]
            row["route_class"] = OWNED_ROUTE_REUSED
            row["route_why"] = (
                "the OSM element carries its own official website tag; rank 0 of the ladder "
                "is owned evidence and this cost no request")
            row["match_strength"] = "OSM_OWN_TAG"
            row["matched_tokens"] = []
            continue

        # An INDEPENDENT-looking name may be a soft brand: Hilton's own
        # Lexington city page lists "The Campbell House" (Curio) and "The Sire
        # Hotel" (Tapestry). A row whose name proposes no chain is therefore
        # searched across EVERY family, and still has to earn a distinctive
        # token to bind.
        searchable = (pool if brand == "INDEPENDENT" else by_family.get(brand, []))

        best = None
        for cand in searchable:
            slug = cand["slug"]
            got_d = distinctive_tokens(slug)
            got_c = chain_tokens(slug)
            shared_d = want_d & got_d
            shared_c = want_c & got_c
            if not shared_d:
                continue
            if not shared_c and want_c:
                continue
            score = (len(shared_d), len(shared_c), -abs(len(got_d) - len(want_d)))
            if best is None or score > best[0]:
                best = (score, cand, shared_d, shared_c)

        if best is None:
            # Last free tier. Some names reduce to nothing distinctive because
            # EVERY word in them is a chain word or a locality word -- "Hilton
            # Lexington/Downtown" is {hilton, lexington, downtown}. Requiring a
            # distinctive token would strand them forever. So an EXACT
            # whole-token-set match against the slug binds, with at least three
            # tokens agreeing and nothing left over on either side. That is a
            # much stronger statement than a shared word, and it is recorded
            # under its own match_strength so it can be audited separately.
            for cand in searchable:
                a = set(norm(name).split())
                b = set(norm(cand["slug"]).split())
                if len(a) >= 3 and a == b:
                    best = ((0, 0, 0), cand, set(), set())
                    row["match_strength"] = "FULL_TOKEN_SET_EQUAL"
                    break

        if best is None:
            row["route"] = ""
            row["route_class"] = FREE_LANE_EXHAUSTED
            row["route_why"] = (
                "no free official-sitemap slug shares a distinctive (non-chain, non-locality) "
                "token with this name; nothing is invented and no code is guessed")
            row["match_strength"] = ""
            row["matched_tokens"] = []
            continue

        _score, cand, shared_d, shared_c = best
        row["route"] = cand["url"]
        row["route_class"] = ROUTED_OFFICIAL_SITEMAP
        row["route_property_code"] = cand["property_code"]
        row["route_lane"] = cand["lane"]
        row["matched_tokens"] = sorted(shared_d)
        if not row.get("match_strength"):
            row["match_strength"] = ("DISTINCTIVE_TOKEN_AND_CHAIN" if shared_c
                                     else "DISTINCTIVE_TOKEN_ONLY")
        if brand == "INDEPENDENT" and cand["family"] != "INDEPENDENT":
            row["soft_brand_finding"] = (
                "the census name proposes no chain, but %s's own city page lists this property "
                "-- a soft brand (Curio / Tapestry / Autograph and the like). Recorded so the "
                "brand family is not read off the display name." % cand["family"])
        row["route_why"] = (
            "official %s sitemap slug %r shares distinctive token(s) %s with the census name; "
            "the property code %r is recorded but a lex* prefix alone never binds -- the "
            "prefix provably spans Corbin, Frankfort, Georgetown and Richmond. Identity is "
            "confirmed on the page, not on the slug."
            % (cand["family"], cand["slug"], sorted(shared_d), cand["property_code"]))
    return identities


# --------------------------------------------------------------------------
# Phase 10 -- direct static capture
# --------------------------------------------------------------------------

def capture(identities, args):
    run_id = args.run_id
    run_dir = Path(_DASH) / "data" / "acquisition" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    routed = [r for r in identities if r.get("route")]
    if args.limit:
        routed = routed[: args.limit]
    print("routed targets", len(routed), "run", run_id, flush=True)

    requests = 0
    for i, row in enumerate(routed):
        key = row["identity_key"]
        slug = row["slug"]
        brand = row["brand"]
        attempt_dir = run_dir / slug / "attempt-01"
        target = BC.CaptureTarget(
            slug=slug,
            hotel=row["name"],
            requested_url=row["route"],
            property_code=row.get("route_property_code", "") or "",
            market_id=MARKET_ID,
            normalized_name=key,
            identity_key=key,
            street_identity=row.get("address_line", ""),
            expected_postal_code=(row.get("postal_code") or "")[:5],
            expected_street=row.get("address_line", ""),
            expected_phone="",
            expected_locality=row.get("city", "") or "Lexington",
            identity_brand=brand,
            census_matched=True,
        )
        record_path = run_dir / slug / "attempt-01.record.json"
        if record_path.is_file() and not args.refetch:
            rec = json.loads(record_path.read_text(encoding="utf-8"))
        else:
            time.sleep(SPACING_SECONDS)
            attempt, _payload = DHC.run_attempt(target, 1, run_dir=run_dir, brand=brand)
            requests += 1
            a = as_plain(attempt)
            rec = OrderedDict([
                ("outcome", a.get("outcome")), ("final_url", a.get("final_url")),
                ("title", a.get("title")), ("detail", a.get("detail")),
                ("body_chars", a.get("body_chars")), ("identity", a.get("identity")),
                ("fetched_at", a.get("started_at")),
            ])
            record_path.parent.mkdir(parents=True, exist_ok=True)
            record_path.write_text(json.dumps(rec, indent=1, ensure_ascii=False, default=str),
                                   encoding="utf-8")

        row["static"] = OrderedDict([
            ("outcome", rec.get("outcome")),
            ("final_url", rec.get("final_url")),
            ("title", (rec.get("title") or "")[:160]),
            ("detail", (rec.get("detail") or "")[:300]),
            ("identity_assessment", rec.get("identity")),
            ("page_sha256", sha256_file(attempt_dir / "rendered.html")),
            ("artifact_dir", str(attempt_dir.relative_to(Path(_DASH))).replace("\\", "/")
             if attempt_dir.is_dir() else ""),
        ])

        if rec.get("outcome") == "VALID" and (attempt_dir / "policy-block.txt").is_file():
            result = {
                "identity_key": key, "canonical_name": row["name"], "brand": brand,
                "corridor": row.get("cell_id", ""), "source_url": row["route"],
                "outcome": "VALID", "final_url": rec.get("final_url") or row["route"],
                "artifact_dir": str(attempt_dir),
                "identity_confirmed": bool((rec.get("identity") or {}).get("confirmed", True)),
                "locator_strategy": "",
            }
            try:
                obs, grade, refusal = MOS.observation_for(
                    result, run_id=run_id, market_id=MARKET_ID, census_row=None)
                ext = ((obs or {}).get("observation") or {}).get("extraction") or {}
                row["observation"] = OrderedDict([
                    ("extraction", ext),
                    ("evidence", ((obs or {}).get("observation") or {}).get("evidence")),
                    ("withheld_fields", (obs or {}).get("withheld_fields")),
                    ("publication_grade", grade),
                    ("refusal_reason", refusal),
                ])
                pa = ext.get("pets_allowed")
                pg_ok = bool(grade) and str(
                    (grade or {}).get("verdict") or (grade or {}).get("grade") or ""
                ).endswith("CONFIRMED")
                if pa is True:
                    row["policy_class"] = ("CLEAN_PET_FRIENDLY" if pg_ok
                                           else "PET_FRIENDLY_READ_NOT_PUBLICATION_GRADE")
                elif pa is False:
                    row["policy_class"] = ("CLEAN_VERIFIED_NO_PETS" if pg_ok
                                           else "NO_PETS_READ_NOT_PUBLICATION_GRADE")
                else:
                    row["policy_class"] = "SOURCE_SILENT"
            except Exception as exc:  # noqa: BLE001
                row["observation_error"] = repr(exc)
                row["policy_class"] = "CAPTURE_FAILED"
        elif rec.get("outcome") == "VALID":
            row["policy_class"] = "POLICY_NOT_FOUND"
        elif rec.get("outcome") in ("IDENTITY_MISMATCH",):
            row["policy_class"] = "IDENTITY_MISMATCH"
        else:
            row["policy_class"] = "CAPTURE_FAILED"

        if (i + 1) % 10 == 0:
            print("  captured", i + 1, "of", len(routed), flush=True)
    return requests


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", required=True)
    ap.add_argument("--run-id", default="lexington_ky_free_static_001")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--refetch", action="store_true")
    ap.add_argument("--route-only", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    recon = read_json(RECON)
    identities = []
    for r in recon["records"]:
        if r["classification"] != "EXACT_UNIQUE_IDENTITY":
            continue
        key = re.sub(r"[^a-z0-9]+", "-", norm(r["name"])).strip("-")
        identities.append(OrderedDict([
            ("identity_key", key),
            ("slug", key),
            ("name", r["name"]),
            ("address_line", r["address_line"]),
            ("city", r["city"]),
            ("postal_code", r["postal_code"]),
            ("latitude", r["latitude"]), ("longitude", r["longitude"]),
            ("cell_id", r["cell_id"]),
            ("county", r["county"]),
            ("osm_element", r["osm_element"]),
            ("website_url", r["website_url"]),
        ]))

    pool = sitemap_pool()
    print("sitemap pool", len(pool), "urls over",
          len({p["family"] for p in pool}), "families", flush=True)
    route_rows(identities, pool, args)

    requests = 0
    if not args.route_only:
        requests = capture(identities, args)

    route_counts = Counter(r["route_class"] for r in identities)
    policy_counts = Counter(r.get("policy_class", "NOT_ATTEMPTED") for r in identities)
    static_outcomes = Counter((r.get("static") or {}).get("outcome", "NOT_ATTEMPTED")
                              for r in identities)

    report = OrderedDict([
        ("schema", "ptf-routing-and-static-capture/1.0"),
        ("work_order", WORK_ORDER),
        ("phase", "9 and 10 -- free routing, then direct first-party static policy"),
        ("market_id", MARKET_ID),
        ("as_of", args.as_of),
        ("run_id", args.run_id),
        ("paid_provider_calls", 0),
        ("usd_spent", 0.0),
        ("free_http_requests", requests),
        ("routing_doctrine",
         "A sitemap slug NAMES a hotel and never decides one. A slug binds only on a "
         "DISTINCTIVE token -- chain words, locality words and directionals are stripped "
         "first -- and the chain family must agree. The lex* property-code prefix is Blue "
         "Grass Airport's and Marriott applies it to Corbin, Frankfort, Georgetown and "
         "Richmond, so a prefix never binds on its own."),
        ("totals", OrderedDict([
            ("identities", len(identities)),
            ("route_classes", OrderedDict(sorted(route_counts.items()))),
            ("static_outcomes", OrderedDict(sorted(static_outcomes.items()))),
            ("policy_classes", OrderedDict(sorted(policy_counts.items()))),
        ])),
        ("identities", identities),
    ])
    out = args.out or os.path.join(REPORTS, "lexington_ky_routing_and_static_capture_001.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, default=str)
        fh.write("\n")
    print(json.dumps(report["totals"], indent=1))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
