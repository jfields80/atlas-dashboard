"""PTF-TOLEDO-OH-NEW-MARKET-001 -- Phase 3, the owned-evidence index.

Rung 0 of the ladder. Before a single external request is made for Toledo, this
reads what the repository ALREADY owns about the Toledo lodging market and says
exactly what may be reused and what must still be acquired.

What it finds, and why it is real evidence rather than a coincidence:

* ``dayton_oh_brand_directory_harvest_001.json`` walked Marriott's own sitemap
  index and kept 17,567 property URLs -- the WHOLE published Marriott roster,
  not a Dayton slice. Every Toledo TOL* code is already in that file, captured
  first-party on 2026-09-02 at zero cost.
* the same file and ``cleveland_akron_canton_oh_brand_directory_harvest_003.json``
  each walked Wyndham, Drury, Sonesta, Magnuson, InTown and WoodSpring filtered
  to OHIO, not to their own market. Toledo rows are in both.
* Hilton yielded ZERO property URLs in both harvests, so Hilton is NOT owned and
  must be walked fresh. IHG, Hyatt, Best Western, ESA, Red Roof, Choice, Motel 6
  and Radisson were recorded as refusing a plain client.

Cross-market collision risk is checked directly: every registered market's
committed identity census is scanned for a Toledo-area address, so a hotel that
already belongs to Cleveland, Dayton or Detroit can never be claimed twice.

Nothing here fetches anything. Nothing here writes outside Toledo artifacts.

Output:
  launch_packages/pettripfinder/markets/reports/toledo_oh_owned_evidence_001.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-TOLEDO-OH-NEW-MARKET-001"
MARKET_ID = "toledo-oh"
SCHEMA = "ptf-owned-evidence-index/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")

OWNED_HARVESTS = [
    ("DAYTON-001", os.path.join(REPORTS, "dayton_oh_brand_directory_harvest_001.json")),
    ("CLEVELAND-003", os.path.join(REPORTS, "cleveland_akron_canton_oh_brand_directory_harvest_003.json")),
]

#: The market's own postal partition, read from the proposed contract so the two
#: files can never drift apart.
PROPOSED_CONTRACT = os.path.join(PKG, "markets", "proposed", "toledo-oh.json")

#: URL slug tokens that name a Toledo-market locality. A token alone never
#: admits a coded row -- see TOLEDO_TRAPS.
LOCALITY_TOKENS = (
    "toledo", "sylvania", "maumee", "perrysburg", "rossford", "northwood",
    "monclova", "waterville", "whitehouse", "swanton", "walbridge", "millbury",
    "bowling-green", "holland", "oregon", "lambertville", "temperance",
)
#: Where a locality token lies. Marriott publishes Toledo, SPAIN and two Bowling
#: Green, KENTUCKY code families; a market that trusts the token alone imports
#: all three.
TOLEDO_TRAPS = OrderedDict([
    ("madto", "AC Hotel Ciudad de Toledo -- Toledo, SPAIN. Marriott MAD* is Madrid."),
    ("bwgcy", "Courtyard Bowling Green Convention Center -- Bowling Green, KENTUCKY (BWG)."),
    ("bwgfb", "Fairfield Inn & Suites Bowling Green -- Bowling Green, KENTUCKY (BWG)."),
    ("bwgts", "TownePlace Suites Bowling Green -- Bowling Green, KENTUCKY (BWG)."),
    ("bnabh", "SpringHill Suites Bowling Green -- Bowling Green, KENTUCKY (BNA is Nashville)."),
])
#: Marriott/Hilton property-code prefix for this market. Toledo Express is TOL;
#: Bowling Green, OHIO is TOLBG, which is why the fringe hold matters.
CODE_PREFIX = "tol"
NON_US_LOCALE = re.compile(r"marriott\.com/(?!en-us/)[a-z]{2}(?:-[a-z]{2})?/", re.I)
MARRIOTT_CODE = re.compile(r"marriott\.com/(?:[a-z-]+/)?hotels/([a-z0-9]{5,7})-([^/]+)/overview", re.I)
#: Marriott's sitemap carries sub-pages of the overview route (``/sports-teams/``
#: and the like). They are the same property, not another one; the canonical
#: route is the bare overview.
_MARRIOTT_SUBPAGE = re.compile(r"/overview/.+", re.I)

CENSUS_DIR = os.path.join(PKG, "identity_census")
TOLEDO_ADDR = re.compile(
    r"\b(toledo|maumee|perrysburg|rossford|sylvania,|northwood|walbridge|millbury|"
    r"whitehouse|waterville|monclova|swanton|bowling green)\b", re.I)
TOLEDO_ZIP = re.compile(r"\b(434(?:47|60|65)|435(?:28|37|42|51|58|60|66|71)|436(?:0[2-9]|1[0-7]|19|20|23)|43402)\b")


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def locality_token(url: str) -> str:
    u = url.lower()
    for tok in LOCALITY_TOKENS:
        if tok in u:
            return tok
    return ""


def classify_owned_url(fam: str, url: str) -> OrderedDict:
    """Why this owned URL is, or is not, a Toledo lead."""
    rec = OrderedDict([("family", fam), ("url", url)])
    if NON_US_LOCALE.search(url):
        # NORMALISE, never drop. Marriott's harvest carries tolrw (Residence Inn
        # Toledo West) only under the /ja/ locale; dropping the row would have
        # lost a real Toledo property because of the language of its URL.
        url = NON_US_LOCALE.sub("marriott.com/en-us/", url)
        rec["url"] = url
        rec["locale_normalised_from"] = "a non-en-us Marriott locale path"
    code, slug = "", ""
    m = MARRIOTT_CODE.search(url)
    if m:
        code, slug = m.group(1).lower(), m.group(2).lower()
    tok = locality_token(url)
    if m and _MARRIOTT_SUBPAGE.search(url):
        rec["verdict"] = "DROPPED_SUBPAGE_OF_OVERVIEW"
        rec["why"] = ("a sub-page beneath the property's own overview route; the canonical route "
                      "is the bare /overview/, and this is the same property")
        return rec
    if code and code in TOLEDO_TRAPS:
        rec.update([("property_code", code), ("locality_token", tok),
                    ("verdict", "DROPPED_LOCALITY_TOKEN_TRAP"), ("why", TOLEDO_TRAPS[code])])
        return rec
    if code and not code.startswith(CODE_PREFIX):
        rec.update([("property_code", code), ("locality_token", tok),
                    ("verdict", "DROPPED_CODE_OUTSIDE_MARKET"),
                    ("why", "Marriott code %r does not carry the TOL prefix this market owns." % code)])
        return rec
    if not tok and not code:
        rec["verdict"] = "NOT_A_TOLEDO_LEAD"
        return rec
    if code:
        rec.update([("property_code", code), ("locality_token", tok),
                    ("verdict", "OWNED_LEAD"), ("admitted_by", "PROPERTY_CODE_PREFIX"),
                    ("slug", slug)])
    else:
        rec.update([("locality_token", tok), ("verdict", "OWNED_LEAD"),
                    ("admitted_by", "LOCALITY_TOKEN")])
    return rec


def scan_owned_harvests():
    seen = OrderedDict()
    provenance = OrderedDict()
    for label, path in OWNED_HARVESTS:
        if not os.path.exists(path):
            provenance[label] = {"path": path, "status": "ABSENT"}
            continue
        doc = _load(path)
        fams = doc.get("families") or {}
        provenance[label] = OrderedDict([
            ("path", os.path.relpath(path, _DASH).replace("\\", "/")),
            ("work_order", doc.get("work_order")),
            ("as_of", doc.get("as_of")),
            ("usd_spent", doc.get("usd_spent")),
            ("free_http_requests", doc.get("free_http_requests")),
            ("families_with_property_urls", OrderedDict(
                (f, len(h.get("property_urls") or [])) for f, h in fams.items())),
            ("refused_families", doc.get("refused_families") or {}),
        ])
        for fam, h in fams.items():
            for url in (h.get("property_urls") or []):
                rec = classify_owned_url(fam, url)
                if rec["verdict"] == "NOT_A_TOLEDO_LEAD":
                    continue
                prior = seen.get(url)
                if prior:
                    prior["seen_in"].append(label)
                else:
                    rec["seen_in"] = [label]
                    seen[url] = rec
    return seen, provenance


def scan_cross_market_collisions():
    """Every registered market's committed census, scanned for a Toledo address."""
    hits = []
    scanned = []
    if not os.path.isdir(CENSUS_DIR):
        return hits, scanned
    for name in sorted(os.listdir(CENSUS_DIR)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(CENSUS_DIR, name)
        scanned.append(name)
        try:
            doc = _load(path)
        except Exception:  # noqa: BLE001
            continue
        rows = doc.get("hotels") or doc.get("identities") or doc.get("rows") or doc.get("census") or []
        if isinstance(rows, dict):
            rows = list(rows.values())
        for row in rows:
            if not isinstance(row, dict):
                continue
            blob = " ".join(str(row.get(k) or "") for k in
                            ("name", "canonical_name", "street", "street_address", "address",
                             "city", "locality", "postal_code", "postal", "zip"))
            if TOLEDO_ADDR.search(blob) or TOLEDO_ZIP.search(blob):
                hits.append(OrderedDict([
                    ("census_file", name),
                    ("market_id", doc.get("market_id") or name.replace(".json", "")),
                    ("name", row.get("name") or row.get("canonical_name")),
                    ("address", row.get("street") or row.get("street_address") or row.get("address")),
                    ("city", row.get("city") or row.get("locality")),
                    ("postal_code", row.get("postal_code") or row.get("postal") or row.get("zip")),
                    ("identity_key", row.get("identity_key")),
                ]))
    return hits, scanned


def build() -> OrderedDict:
    leads, provenance = scan_owned_harvests()
    admitted = [r for r in leads.values() if r["verdict"] == "OWNED_LEAD"]
    dropped = [r for r in leads.values() if r["verdict"] != "OWNED_LEAD"]
    interesting_dropped = [r for r in dropped if r.get("locality_token")]
    collisions, censuses = scan_cross_market_collisions()
    contract = _load(PROPOSED_CONTRACT) if os.path.exists(PROPOSED_CONTRACT) else {}
    zips = sorted({z for c in contract.get("corridors", []) for z in c.get("included_postal_codes", [])})

    owned_families = Counter(r["family"] for r in admitted)
    # Which families this market must still acquire for itself.
    not_owned = []
    for fam in ("HILTON", "IHG", "CHOICE", "HYATT", "BEST_WESTERN", "ESA", "RED_ROOF",
                "MOTEL6", "RADISSON", "MY_PLACE"):
        if owned_families.get(fam):
            continue
        not_owned.append(fam)

    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER),
        ("phase", "3 -- owned evidence search, rung 0 of the acquisition ladder"),
        ("market_id", MARKET_ID),
        ("what_this_is",
         "What the repository already owns about Toledo, read before any external request. Owned "
         "first-party brand inventory is REUSED, not reacquired; families with no owned rows are "
         "named so the fresh lane knows exactly what it is for."),
        ("owned_evidence_is_not_policy",
         "Every row here is an identity/routing LEAD from a brand's own published sitemap. None of "
         "it is policy evidence and none of it may publish a pet policy."),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("http_requests", 0),
        ("prior_toledo_market_work", "NONE -- toledo-oh has no market contract, no discovery "
                                     "config prior to this order, no census, no routes, no policy "
                                     "evidence and no provider attempts in any committed ledger."),
        ("sources_scanned", provenance),
        ("registered_censuses_scanned", censuses),
        ("proposed_contract_postal_codes", zips),
        ("counts", OrderedDict([
            ("owned_leads", len(admitted)),
            ("owned_leads_by_family", OrderedDict(sorted(owned_families.items()))),
            ("dropped", len(dropped)),
            ("dropped_by_verdict", OrderedDict(sorted(Counter(r["verdict"] for r in dropped).items()))),
            ("cross_market_collision_hits", len(collisions)),
        ])),
        ("families_not_owned_must_acquire_fresh", not_owned),
        ("owned_leads", admitted),
        ("dropped_with_reason_note",
         "Only rows carrying a Toledo LOCALITY TOKEN are listed. The other %d dropped rows are "
         "the rest of the world: a global Marriott roster and non-en-us locale duplicates, "
         "dropped because their property code carries no TOL prefix." % (len(dropped) - len(interesting_dropped))),
        ("dropped_with_reason", interesting_dropped),
        ("cross_market_collisions", collisions),
    ])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPORTS, "toledo_oh_owned_evidence_001.json"))
    args = ap.parse_args(argv)
    rep = build()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1)
        fh.write("\n")
    c = rep["counts"]
    print("owned leads           :", c["owned_leads"], dict(c["owned_leads_by_family"]))
    print("dropped               :", c["dropped"], dict(c["dropped_by_verdict"]))
    print("cross-market hits     :", c["cross_market_collision_hits"])
    print("must acquire fresh    :", rep["families_not_owned_must_acquire_fresh"])
    print("written               :", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
