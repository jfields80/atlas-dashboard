"""PTF-DALLAS-FORT-WORTH-TX-HARDENED-SOURCE-READY-001 -- Phase 38: the clone-residue scan, run BEFORE the first seal.

This market's lanes were cloned from Fort Myers' source-ready scripts (commit f0096324) and San Antonio's (823e0ba4),
which were themselves cloned through the earlier markets. A clone carries its parent's market text, its parent's coordinates and its
parent's boundary (the Minneapolis lesson: a cloned census kept Portland's pin envelope and refused 101 Twin Cities
rows). Three counts must read 0 before anything is sealed:

  CLONE MARKET TEXT RESIDUE   another registered market's primary city, market name or state name inside this
                              market's DATA documents (the proposed market, the census, the discovery config, the
                              staged policy package, the proposed authority, the partition and the shard documents),
                              or inside an executable STRING LITERAL of this market's own scripts (comments and
                              docstrings are design history and are reported, never counted, when they cite where
                              a rule was learned).
  CLONE COORDINATE RESIDUE    a latitude/longitude outside this market's own North Texas observation box -- in any data
                              document's coordinate field, or as a numeric literal pair in this market's scripts
                              (Texas shares its state with two live markets, so the STATE's extent would hide an
                              Austin or San Antonio pin; the market's own box does not).
  CLONE BOUNDARY RESIDUE      a postal code outside the Dallas / Fort Worth sectional centers (750-753, 760-762) in the
                              market's corridors, its census rows or its staged records; or another registered
                              market's corridor ZIP as a literal in this market's scripts.

Reads only committed files. Nothing fetches or writes outside the report.

Output: launch_packages/pettripfinder/markets/reports/dallas_fort_worth_tx_clone_residue_scan_001.json
"""
from __future__ import annotations

import ast
import io
import json
import os
import re
import sys
import tokenize
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
WORK_ORDER = "PTF-DALLAS-FORT-WORTH-TX-HARDENED-SOURCE-READY-001"
MARKET_ID = "dallas-fort-worth-tx"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
SCRIPTS = os.path.join(_DASH, "scripts", "pettripfinder")
OUT = os.path.join(PKG, "markets", "reports", "dallas_fort_worth_tx_clone_residue_scan_001.json")
STAGING = os.path.join(PKG, "markets", "staging", MARKET_ID)

DATA_DOCUMENTS = [
    os.path.join(PKG, "markets", "proposed", MARKET_ID + ".json"),
    os.path.join(PKG, "identity_census_proposed", MARKET_ID + ".json"),
    os.path.join(SCRIPTS, "discovery", "config", "dallas_fort_worth_tx.json"),
    os.path.join(STAGING, "launch_package", "hotel_policy_facts_%s.json" % MARKET_ID),
    os.path.join(STAGING, "dallas_fort_worth_tx_proposed_authority_001.json"),
    os.path.join(STAGING, "launch_package", "dallas_fort_worth_tx_final_partition_001.json"),
]
#: The market's own North Texas observation box (the geography module's BOUNDS: 32.25 N to 33.45 N, 97.85 W to
#: 96.25 W) widened to the OSM lane's AUDIT box (31.45 N to 33.82 N, 97.95 W to 96.00 W), whose outer-place counts
#: (Waco, Sherman / Denison, Corsicana) are this market's own boundary audit. The variable names are the parent's.
UT_LAT = (31.45, 33.82)
UT_LNG = (-97.95, -96.00)
UT_ZIP_PREFIXES = ("750", "751", "752", "753", "760", "761", "762")
#: Words that are another market's name AND an ordinary word this market legitimately uses.
#: Each is listed with the reason; nothing else is excused.
EXCUSED_WORDS = {
    "greenville": "a live market's name that is ALSO two Metroplex places: Greenville, Texas (Hunt County, prefix 754 -- "
                  "refused here as the future greenville-tx market) and Dallas's own Greenville Avenue / Lower "
                  "Greenville neighbourhood (75206). Every hit names one of those two, never the South Carolina market.",
    "austin": "a live market's name that is ALSO a Dallas place (the Austin Street Center shelter, refused as "
              "non-public lodging) and the provenance of the owned Texas OSM extract the Austin order downloaded "
              "and this order hard-links (no Austin data, route or identity is read).",
}
#: Named constants whose PURPOSE is to name other markets -- the isolation statements this market's own geography
#: makes about live markets that share no state with it. Their strings are reported, never counted.
CROSS_MARKET_REFERENCE_CONSTANTS = {
    # the live markets this market is isolated from, and the refused Texas prefixes (Austin and San Antonio are LIVE
    # markets whose 786 / 787 / 782 prefixes this market refuses) -- refusal geometry, never their identity.
    "dallas_fort_worth_tx_geography_001.py": ("EXISTING_LIVE_MARKETS", "OUTSIDE_PREFIXES"),
    # PBFS names the order whose owned Texas download this order hard-links (provenance, zero requests).
    "dallas_fort_worth_tx_osm_lane_001.py": ("STATEWIDE_REGIONS", "PBFS"),
    # the brand lead filter's NEGATIVE table refuses other Texas markets' route tokens ("austin", "san-antonio").
    "dallas_fort_worth_tx_brand_inventory_001.py": ("NEGATIVE", "_TITLE_REFUSED"),
}
CROSS_MARKET_REFERENCES = []
_LAT_LNG_PAIR = re.compile(r"(?<![\d.])(-?\d{2,3}\.\d{2,})\s*,\s*(-?\d{2,3}\.\d{2,})(?![\d.])")


def _load(p):
    with open(p, encoding="utf-8-sig") as fh:
        return json.load(fh)


def other_markets():
    """(text tokens, corridor ZIPs) of every OTHER registered market, read from its own committed contract."""
    tokens, zips = {}, set()
    mdir = os.path.join(PKG, "markets")
    for fn in sorted(os.listdir(mdir)):
        if not fn.endswith(".json") or fn == MARKET_ID + ".json":
            continue
        doc = _load(os.path.join(mdir, fn))
        mid = doc.get("market_id") or fn[:-5]
        for field in ("primary_city", "market_name", "state_name"):
            v = (doc.get(field) or "").strip()
            if v and v.lower() not in ("texas",) and v.lower() not in EXCUSED_WORDS:
                tokens.setdefault(v.lower(), (mid, field))
        for c in doc.get("corridors") or ():
            for z in c.get("included_postal_codes") or c.get("postal_codes") or ():
                zips.add(str(z)[:5])
    return tokens, zips


def _token_rx(tokens):
    return re.compile(r"\b(%s)\b" % "|".join(re.escape(t) for t in sorted(tokens, key=len, reverse=True)), re.I)


def _walk(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk(v, "%s.%s" % (path, k) if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk(v, "%s[%d]" % (path, i))
    else:
        yield path, obj


#: Documents whose EVERY string is market-level text (the market's own definition and its discovery config).
MARKET_LEVEL = {"markets/proposed/%s.json" % MARKET_ID, "discovery/config/dallas_fort_worth_tx.json"}
#: Row collections inside the census and the staged documents, and the row fields that state WHERE a row is and
#: WHICH market owns it. A row's NAME or STREET may legitimately carry a word another market is named for
#: (Washington School House in Park City, Washington Boulevard in Ogden, Indiana Avenue in Salt Lake City);
#: its city, state, market and corridor may not.
ROW_COLLECTIONS = ("hotels", "pet_friendly", "verified_no_pets", "items")
ROW_PLACE_FIELDS = ("city", "state", "market_id", "corridor", "municipality", "county")
#: Top-level (non-row) text fields of the census and the staged documents.
META_SKIP = set(ROW_COLLECTIONS) | {"non_admitted", "unresolved"}


def scan_data(rx):
    text_hits, coord_hits, zip_hits = [], [], []
    for p in DATA_DOCUMENTS:
        rel = os.path.relpath(p, _DASH).replace("\\", "/")
        if not os.path.exists(p):
            text_hits.append((rel, "", "DOCUMENT MISSING"))
            continue
        doc = _load(p)
        market_level = any(rel.endswith(m) for m in MARKET_LEVEL)
        if market_level:
            for path, v in _walk(doc):
                if isinstance(v, str) and rx.search(v):
                    text_hits.append((rel, path, v[:200]))
        else:
            for k, v in (doc.items() if isinstance(doc, dict) else ()):
                if k in META_SKIP:
                    continue
                for path, leaf in _walk(v, k):
                    if isinstance(leaf, str) and rx.search(leaf):
                        text_hits.append((rel, path, leaf[:200]))
        for coll in ROW_COLLECTIONS:
            for i, row in enumerate((doc.get(coll) or []) if isinstance(doc, dict) else []):
                if not isinstance(row, dict):
                    continue
                for f in ROW_PLACE_FIELDS:
                    v = row.get(f)
                    if isinstance(v, str) and v:
                        if rx.search(v) or (f == "market_id" and v != MARKET_ID) or (
                                f == "corridor" and not v.startswith(MARKET_ID + "__")) or (
                                f == "state" and v.upper() not in ("TX", "TEXAS")):
                            text_hits.append((rel, "%s[%d].%s" % (coll, i, f), v))
                z = str(row.get("postal_code") or "")
                if z and z[:3] not in UT_ZIP_PREFIXES:
                    zip_hits.append((rel, "%s[%d].postal_code" % (coll, i), z))
                for f in ("latitude", "longitude"):
                    v = row.get(f)
                    if isinstance(v, (int, float)) and not isinstance(v, bool):
                        lo, hi = UT_LAT if f == "latitude" else UT_LNG
                        if not lo <= float(v) <= hi:
                            coord_hits.append((rel, "%s[%d].%s" % (coll, i, f), v))
        for path, v in _walk(doc):
            leaf = path.rsplit(".", 1)[-1].split("[")[0].lower()
            if isinstance(v, (int, float)) and not isinstance(v, bool) and leaf in (
                    "min_lat", "max_lat", "min_lng", "max_lng", "center_lat", "center_lng"):
                lo, hi = UT_LAT if "lat" in leaf else UT_LNG
                if not lo <= float(v) <= hi:
                    coord_hits.append((rel, path, v))
        for c in (doc.get("corridors") or []) if isinstance(doc, dict) else []:
            for z in (c.get("included_postal_codes") or c.get("postal_codes") or c.get("zip_codes") or ()):
                if str(z)[:3] not in UT_ZIP_PREFIXES:
                    zip_hits.append((rel, "corridors.%s" % c.get("corridor_id", c.get("id", "")), z))
            if c.get("state_code") and c["state_code"] != "TX":
                zip_hits.append((rel, "corridors.%s.state_code" % c.get("corridor_id", ""), c["state_code"]))
    return text_hits, coord_hits, zip_hits


def _strings_and_comments(src):
    """(executable string literals, comments+docstrings) of one module, with line numbers."""
    strings, notes = [], []
    prev_sig = None
    toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    for i, t in enumerate(toks):
        if t.type == tokenize.COMMENT:
            notes.append((t.start[0], t.string))
        elif t.type == tokenize.STRING:
            # a docstring is a string statement on its own: preceded by INDENT/NEWLINE/start and followed by NEWLINE
            nxt = next((x for x in toks[i + 1:] if x.type not in (tokenize.NL, tokenize.COMMENT)), None)
            is_doc = (prev_sig in (None, tokenize.INDENT, tokenize.NEWLINE, tokenize.DEDENT)
                      and nxt is not None and nxt.type in (tokenize.NEWLINE, tokenize.ENDMARKER))
            (notes if is_doc else strings).append((t.start[0], t.string))
        if t.type not in (tokenize.NL, tokenize.COMMENT):
            prev_sig = t.type
    return strings, notes


def scan_code(rx, zips):
    text_hits, coord_hits, zip_hits, provenance = [], [], [], 0
    for fn in sorted(os.listdir(SCRIPTS)):
        if not (fn.startswith("dallas_fort_worth_tx_") and fn.endswith(".py")) or fn == os.path.basename(__file__):
            continue
        src = open(os.path.join(SCRIPTS, fn), encoding="utf-8").read()
        strings, notes = _strings_and_comments(src)
        excused = set()
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in
                                                    CROSS_MARKET_REFERENCE_CONSTANTS.get(fn, ()) for t in node.targets):
                excused.update(range(node.lineno, node.end_lineno + 1))
        for line, s in strings:
            if line in excused:
                CROSS_MARKET_REFERENCES.append((fn, line, s[:120]))
                continue
            m = rx.search(s)
            if m:
                text_hits.append((fn, line, m.group(1), s[:160]))
            for z in re.findall(r"(?<!\d)(\d{5})(?!\d)", s):
                if z in zips and z[:3] not in UT_ZIP_PREFIXES:
                    zip_hits.append((fn, line, z, s[:120]))
        provenance += sum(1 for _l, s in notes if rx.search(s))
        # numeric literal pairs anywhere in the code (not in comments) that look like a coordinate
        code_only = re.sub(r"#[^\n]*", "", src)
        for m in _LAT_LNG_PAIR.finditer(code_only):
            a, b = float(m.group(1)), float(m.group(2))
            if 24 <= a <= 50 and -125 <= b <= -66 and not (UT_LAT[0] <= a <= UT_LAT[1] and UT_LNG[0] <= b <= UT_LNG[1]):
                coord_hits.append((fn, code_only[:m.start()].count("\n") + 1, m.group(0)))
        for m in re.finditer(r"(?<![\d.])(-?\d{2,3}\.\d{3,})(?![\d.])", code_only):
            v = float(m.group(1))
            line = code_only[:m.start()].count("\n") + 1
            ctx = code_only[max(0, m.start() - 40):m.start()].lower()
            if re.search(r"lat", ctx) and 24 <= v <= 50 and not (UT_LAT[0] <= v <= UT_LAT[1]):
                coord_hits.append((fn, line, m.group(1)))
            if re.search(r"(lng|lon)", ctx) and -125 <= v <= -66 and not (UT_LNG[0] <= v <= UT_LNG[1]):
                coord_hits.append((fn, line, m.group(1)))
    return text_hits, coord_hits, zip_hits, provenance


def main():
    tokens, zips = other_markets()
    rx = _token_rx(tokens)
    # In CODE only another market's CITY (its primary city or its market name) is residue: a state name appears in
    # this market's own out-of-market NEGATIVE tables (brand routes for "sandy-oregon", "murray-kentucky"), which is
    # this market's logic refusing other places, never another market's identity carried here.
    city_rx = _token_rx(({t for t, (_m, f) in tokens.items() if f != "state_name"} | {
        t.split(",")[0].strip() for t, (_m, f) in tokens.items() if f == "market_name"}) - set(EXCUSED_WORDS))
    d_text, d_coord, d_zip = scan_data(rx)
    c_text, c_coord, c_zip, provenance = scan_code(city_rx, zips)
    doc = OrderedDict([
        ("schema", "ptf-clone-residue-scan/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("parent_clone", "Fort Myers source-ready scripts at commit f0096324 and San Antonio's at 823e0ba4 (themselves "
                         "cloned through earlier markets)"),
        ("other_market_tokens", len(tokens)), ("other_market_corridor_zips", len(zips)),
        ("excused_words", EXCUSED_WORDS),
        ("data_documents", [os.path.relpath(p, _DASH).replace("\\", "/") for p in DATA_DOCUMENTS]),
        ("CLONE_MARKET_TEXT_RESIDUE", len(d_text) + len(c_text)),
        ("CLONE_COORDINATE_RESIDUE", len(d_coord) + len(c_coord)),
        ("CLONE_BOUNDARY_RESIDUE", len(d_zip) + len(c_zip)),
        ("provenance_comments_citing_other_markets",
         "%d comment/docstring lines name the market where a rule was learned (design history, never executable, "
         "never data) -- reported, not counted" % provenance),
        ("cross_market_reference_constants", CROSS_MARKET_REFERENCES),
        ("data_text_hits", d_text), ("code_text_hits", c_text),
        ("data_coordinate_hits", d_coord), ("code_coordinate_hits", c_coord),
        ("data_boundary_hits", d_zip), ("code_boundary_hits", c_zip),
    ])
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    for k in ("CLONE_MARKET_TEXT_RESIDUE", "CLONE_COORDINATE_RESIDUE", "CLONE_BOUNDARY_RESIDUE"):
        print(k, "=", doc[k])
    for name in ("data_text_hits", "code_text_hits", "data_coordinate_hits", "code_coordinate_hits",
                 "data_boundary_hits", "code_boundary_hits"):
        for h in doc[name][:40]:
            print("  ", name, h)
    print(doc["provenance_comments_citing_other_markets"])
    return 0 if not (doc["CLONE_MARKET_TEXT_RESIDUE"] or doc["CLONE_COORDINATE_RESIDUE"]
                     or doc["CLONE_BOUNDARY_RESIDUE"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
