"""PTF-CINCINNATI-HARDENED-REVALIDATION-001 -- Phase 5 / 6.

Reconcile the free OpenStreetMap recensus against Cincinnati's PINNED census.

The harvest is a LEAD generator, not an admission mechanism. An OSM node says
somebody mapped a lodging feature at a coordinate; it does not say a hotel
trades there today, what its legal identity is, or that our census is missing
it. So every candidate is classified against the census on evidence THE
CANDIDATE ITSELF CARRIES -- its normalized name, its coordinate, and where OSM
recorded them, its address and postal code -- and anything that cannot be
settled on that evidence is returned NAME_ONLY_UNRESOLVED rather than guessed.

What bounds this pass, stated rather than papered over:

  * OSM lodging nodes in this extract are sparsely addressed. Most carry a
    name and a coordinate and nothing else, so a name that does not match
    cannot be promoted to TRUE_MISSING_IDENTITY on geometry alone -- "Motel 6"
    at a coordinate is a chain instance, not an identity.
  * The census stores no coordinates. Geographic agreement is therefore
    computed against the market's own discovery CELL boundaries, which is a
    scope test, not a proximity test between two records.

The consequence: this pass can say with confidence which candidates the census
ALREADY EXPLAINS, and it returns the rest as review leads. Nothing is written
to authority and the pinned census does not move.
"""
from __future__ import annotations

import argparse
import io
import json
import math
import os
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-CINCINNATI-HARDENED-REVALIDATION-001"
MARKET_ID = "cincinnati-oh"
SCHEMA = "ptf-recensus-reconciliation/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CENSUS = os.path.join(PKG, "identity_census", MARKET_ID + ".json")
QUARANTINE = os.path.join(PKG, "identity_census", MARKET_ID + "-quarantine.json")
CELLS = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config",
                     "cincinnati_oh.json")

#: A bare chain name with no address is an instance of a brand, not an
#: identity. Promoting one to TRUE_MISSING on a coordinate is how a market
#: acquires a hotel that does not exist.
CHAIN_STEMS = (
    "motel 6", "super 8", "days inn", "red roof", "quality inn", "comfort inn",
    "comfort suites", "holiday inn", "hampton inn", "best western", "econo lodge",
    "rodeway inn", "travelodge", "knights inn", "microtel", "baymont", "ramada",
    "la quinta", "sleep inn", "clarion", "americas best value", "studio 6",
    "extended stay america", "candlewood suites", "staybridge suites",
    "fairfield inn", "courtyard", "residence inn", "springhill suites",
    "towneplace suites", "hilton garden inn", "homewood suites", "home2 suites",
    "doubletree", "embassy suites", "tru by hilton", "hyatt place", "hyatt house",
    "wingate", "howard johnson", "budget host", "suburban", "woodspring suites",
    "drury inn", "sonesta", "hotel", "motel", "inn",
)

_STOP = re.compile(r"\b(the|a|an|of|at|by|and|near|hotel|motel|inn|suites|suite|"
                   r"resort|lodge|hostel|oh|ohio|ky|kentucky|in|indiana)\b")

#: Words that say WHERE, never WHICH. Two lodging records sharing only these
#: are two hotels in the same town, which is the normal case in this market
#: and not an alias.
_GENERIC_PLACE = {"north", "south", "east", "west", "downtown", "uptown",
                  "midtown", "airport", "central", "greater", "county",
                  "riverfront", "river", "park", "hills", "heights", "center",
                  "centre", "township", "village", "city", "area", "plaza",
                  "square", "mall", "convention"}


def norm(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def tokens(s: str):
    return {t for t in _STOP.sub(" ", norm(s)).split() if len(t) > 2}


def chain_stem(name: str) -> str:
    """The brand a name is an instance of, longest stem first, or ""."""
    n = " " + norm(name) + " "
    for s in sorted(CHAIN_STEMS, key=len, reverse=True):
        if (" " + s + " ") in n:
            return s
    return ""


def distinctive(name: str, geo_words) -> set:
    """The tokens that say WHICH hotel: not a place, not the brand's own words."""
    stem_words = set(chain_stem(name).split())
    return {t for t in tokens(name)
            if t not in geo_words and t not in _GENERIC_PLACE and t not in stem_words}


def J(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def cell_of(lat, lng, cells):
    """The nearest discovery cell whose radius contains the point.

    Cells are centre-plus-radius, not boxes, and they overlap by design (the
    planner reports seven overlapping pairs for this market), so the nearest
    containing cell is the answer and the first one found is not.
    """
    best, best_d = "", None
    for c in cells:
        dlat = (lat - c["center_lat"]) * 111_320.0
        dlng = (lng - c["center_lng"]) * 111_320.0 * math.cos(math.radians(lat))
        d = math.hypot(dlat, dlng)
        if d <= c.get("radius_meters", 0) and (best_d is None or d < best_d):
            best, best_d = c.get("cell_id", ""), d
    return best


def build(args) -> OrderedDict:
    census = J(CENSUS)["hotels"]
    by_norm = {}
    for h in census:
        by_norm.setdefault(norm(h["canonical_name"]), []).append(h)
        if h.get("prior_identity_key"):
            by_norm.setdefault(norm(h["prior_identity_key"]), []).append(h)
    quarantined = set()
    if os.path.exists(QUARANTINE):
        q = J(QUARANTINE)
        for r in (q.get("hotels") or q.get("rows") or []):
            quarantined.add(norm(r.get("canonical_name") or r.get("identity_key") or ""))

    cfg = J(CELLS)
    cells = cfg.get("cells") or []
    bounds = cfg["geographic_bounds"]

    # The market's OWN place vocabulary: its municipality list, its cell
    # labels and every city its census names. A token in here LOCATES a hotel
    # and never identifies one, so an overlap on these alone is not an alias.
    geo_words = set(_GENERIC_PLACE)
    for m in cfg.get("included_municipalities") or []:
        text = m if isinstance(m, str) else (m.get("name") or "")
        geo_words |= {w for w in norm(text).split() if len(w) > 2}
    for c in cells:
        geo_words |= {w for w in norm("%s %s" % (c.get("label", ""),
                                                 c.get("municipality", ""))).split()
                      if len(w) > 2}
    for h in census:
        geo_words |= {w for w in norm(h.get("city", "")).split() if len(w) > 2}

    census_distinctive = [(h, distinctive(h["canonical_name"], geo_words),
                           chain_stem(h["canonical_name"])) for h in census]

    candidates = J(args.candidates)
    rows = []
    for c in candidates:
        name = c.get("name") or ""
        n = norm(name)
        lat, lng = c.get("latitude"), c.get("longitude")
        in_box = (lat is not None and lng is not None
                  and bounds["min_lat"] <= lat <= bounds["max_lat"]
                  and bounds["min_lng"] <= lng <= bounds["max_lng"])
        cell = cell_of(lat, lng, cells) if in_box else ""
        stem = chain_stem(name)
        cand_distinctive = distinctive(name, geo_words)
        # A name with nothing distinctive left is a brand instance -- "Comfort
        # Suites", "Days Inn", "Motel 6". It can never be aliased onto ONE
        # census row, because every row of that brand fits it equally well.
        is_chain_bare = not cand_distinctive

        exact = by_norm.get(n) or []
        cls, matched, why = "", "", ""
        if not in_box:
            cls, why = "OUTSIDE_MARKET", "coordinate lies outside the market's own bounding box"
        elif exact:
            cls, matched, why = "EXACT_EXISTING", exact[0]["identity_key"], "normalized canonical name matches the census exactly"
        elif n in quarantined:
            cls, why = "CLOSED_OR_CONVERTED", "the identity is in this market's census quarantine"
        elif is_chain_bare:
            cls = "NAME_ONLY_UNRESOLVED"
            why = ("nothing distinctive survives the brand and the place: an "
                   "instance of a chain, not an identity, and never promotable "
                   "onto one census row on a coordinate")
        else:
            # An alias must agree on WHICH hotel, not merely on where it is.
            # A shared DISTINCTIVE token is required, and the brands must not
            # disagree: two hotels of one brand in one town is the normal case
            # here, and a shared town name is evidence of nothing.
            strong = []
            for h, hd, hstem in census_distinctive:
                shared = cand_distinctive & hd
                if not shared:
                    continue
                if stem and hstem and stem != hstem:
                    continue
                cp = (c.get("postal_code") or "")[:5]
                hp = (h.get("postal_code") or "")[:5]
                if cp and hp and cp != hp:
                    continue      # a postal disagreement is a different building
                strong.append((h, shared))
            if len(strong) == 1:
                cls, matched = "ALIAS_OF_EXISTING", strong[0][0]["identity_key"]
                why = ("distinctive token(s) %s identify one census row of a "
                       "brand that does not disagree" % sorted(strong[0][1]))
            elif len(strong) > 1:
                cls = "IDENTITY_REVIEW_REQUIRED"
                why = ("distinctive token(s) %s fit %d census rows; an alias "
                       "that fits more than one identity names none of them"
                       % (sorted(strong[0][1]), len(strong)))
            elif not (c.get("address_line") or "").strip():
                cls = "NAME_ONLY_UNRESOLVED"
                why = "OSM node carries a name and a coordinate and no address"
            else:
                cls = "IDENTITY_REVIEW_REQUIRED"
                why = ("named and addressed, and no census identity shares a "
                       "distinctive token -- a genuine review lead")
        rows.append(OrderedDict((
            ("candidate_id", c.get("candidate_id")),
            ("name", name), ("normalized_name", n),
            ("address_line", c.get("address_line", "")),
            ("city", c.get("city", "")), ("postal_code", c.get("postal_code", "")),
            ("latitude", lat), ("longitude", lng),
            ("cell_id", cell),
            ("categories", c.get("category_candidates") or []),
            ("provider_ids", c.get("provider_ids") or []),
            ("classification", cls),
            ("matched_identity_key", matched),
            ("why", why),
        )))

    counts = Counter(r["classification"] for r in rows)
    explained = sum(counts[k] for k in ("EXACT_EXISTING", "ALIAS_OF_EXISTING",
                                        "CLOSED_OR_CONVERTED", "OUTSIDE_MARKET"))
    return OrderedDict((
        ("schema", SCHEMA),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("phase", "5 / 6 -- free OSM recensus reconciled against the pinned census"),
        ("lane", "overpass (free); 38 requests, 0 rate limits, no paid discovery"),
        ("usd_spent", 0.0),
        ("authority_mutation", "NONE"),
        ("pinned_census", len(census)),
        ("candidates", len(rows)),
        ("classification_counts", OrderedDict(sorted(counts.items()))),
        ("census_explains", explained),
        ("true_missing_identity", 0),
        ("why_no_true_missing",
         "TRUE_MISSING_IDENTITY requires an identity, and an OSM lodging node in "
         "this extract carries a name and a coordinate. A name that does not "
         "match the census is a lead; calling it a missing hotel would admit "
         "chain instances and duplicates. The %d rows classified "
         "IDENTITY_REVIEW_REQUIRED are the reviewable residue and are reported "
         "as leads, not as census growth."
         % counts.get("IDENTITY_REVIEW_REQUIRED", 0)),
        ("rows", rows),
    ))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", default=os.path.join(
        _DASH, "data", "discovery", "cincinnati_recensus_001", "candidates",
        "cincinnati-oh_candidates.json"))
    ap.add_argument("--out", default=os.path.join(
        REPORTS, "cincinnati_oh_recensus_reconciliation_001.json"))
    args = ap.parse_args(argv)
    rep = build(args)
    with io.open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(rep, indent=1, ensure_ascii=False, default=str) + "\n")
    print("written", os.path.relpath(args.out, _DASH))
    print("candidates", rep["candidates"], "explained", rep["census_explains"])
    print("classes:", dict(rep["classification_counts"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
