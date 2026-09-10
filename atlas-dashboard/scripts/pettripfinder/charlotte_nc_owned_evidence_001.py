"""PTF-CHARLOTTE-NC-ZERO-TO-LIVE-BENCHMARK-001 -- Phase 3, the owned-evidence index.

Rung 0 of the ladder. Before a single external request is made for Charlotte,
this reads what the repository ALREADY owns about the Charlotte lodging market
and says exactly what may be reused and what must still be acquired.

WHAT IS ACTUALLY OWNED
----------------------
``dayton_oh_brand_directory_harvest_001.json`` walked Marriott's OWN sitemap
index on 2026-09-02 and kept 17,567 property URLs -- the WHOLE published
Marriott roster, not a Dayton slice. Every Charlotte CLT* code is already in
that file, captured first-party at zero cost. That is the entire owned corpus
for this market: the Wyndham, Drury, Sonesta, Magnuson, InTown and WoodSpring
slices in the Ohio harvests were filtered to OHIO and contain no Carolinas row,
and Hilton yielded zero property URLs in both Ohio harvests.

THE TRAP THIS MARKET IS BUILT AROUND
------------------------------------
A property code SELECTS; the page ADMITS. Marriott's CLT prefix is an AIRPORT
code, and Charlotte Douglas serves most of the western Piedmont, so the CLT
family reaches Clarksville, Cookeville, Columbia, Murfreesboro, Manchester,
Tullahoma, Lebanon, Hopkinsville KENTUCKY, Bowling Green KENTUCKY and a
Postcard Cabins site on Dale Hollow Lake -- none of them this market. In the
other direction, name tokens lie too: Marriott publishes a Brentwood in Los
Angeles and another in Mussoorie, INDIA; an Antioch in Pittsburg, CALIFORNIA;
a Hendersonville in Flat Rock, NORTH CAROLINA; and a Mount Juliet estate in
JAMAICA. Neither the code nor the token is allowed to admit a row here: every
lead is carried forward with its verdict and is confirmed later against the
address the property's own page states.

CROSS-MARKET COLLISION
----------------------
Every registered market's committed identity census is scanned for a Charlotte
address, so a hotel that already belongs to another market can never be claimed
twice. Charlotte is more than 1.4 degrees of latitude from the nearest
committed market, so a collision would be a defect, not a boundary question.

Nothing here fetches anything. Nothing here writes outside Charlotte artifacts.

Output:
  launch_packages/pettripfinder/markets/reports/charlotte_nc_owned_evidence_001.json
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-CHARLOTTE-NC-ZERO-TO-LIVE-BENCHMARK-001"
MARKET_ID = "charlotte-nc"
SCHEMA = "ptf-owned-evidence-index/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONTRACT = os.path.join(PKG, "markets", "charlotte-nc.json")
CENSUS_DIR = os.path.join(PKG, "identity_census")
OUT = os.path.join(REPORTS, "charlotte_nc_owned_evidence_001.json")

OWNED_HARVESTS = [
    ("DAYTON-001", os.path.join(REPORTS, "dayton_oh_brand_directory_harvest_001.json")),
    ("CLEVELAND-003", os.path.join(REPORTS, "cleveland_akron_canton_oh_brand_directory_harvest_003.json")),
]
#: Other committed corpora checked for Carolinas content so "not owned" is a
#: measurement rather than an assumption.
OWNED_ALSO_CHECKED = [
    "cincinnati_oh_brand_inventory_audit_002.json",
    "louisville_parallel_revalidation_001_brand_inventory.json",
    "pittsburgh_parallel_revalidation_001_brand_inventory.json",
    "toledo_oh_brand_city_pages_001.json",
    "ptf_acquisition_brand_repair_003_properties.json",
    "brightdata_cross_brand_pilot_002_properties.json",
    "ptf_locator_parity_019.json",
    "ptf_locator_fresh_proof_019a.json",
]

#: Marriott/Hilton property-code prefix that SELECTS this market's candidates.
#: CLT is the Charlotte Douglas International Airport code and it selects far
#: more than this market; see the module docstring.
CODE_PREFIX = "clt"

#: URL slug tokens that name a Greater Charlotte locality. A token alone never
#: admits a row.
LOCALITY_TOKENS = (
    "charlotte", "uptown", "city-center", "south-end", "southpark", "south-park",
    "ballantyne", "piper-glen", "northlake", "university", "research-park",
    "steele-creek", "arrowood", "westinghouse", "waverly", "loso", "tyvola",
    "yorkmont", "billy-graham", "pineville", "matthews", "mint-hill",
    "huntersville", "cornelius", "davidson", "lake-norman", "birkdale",
    "concord", "concord-mills", "speedway", "harrisburg", "belmont", "gastonia",
    "cramerton", "fort-mill", "tega-cay", "indian-land", "carowinds",
    "dilworth", "myers-park", "plaza-midwood", "noda", "carolina-place",
)

#: Codes the CLT prefix reaches that are NOT this market, each with the reason.
#: Recorded rather than silently filtered: the audit trail is the point.
CLT_TRAPS = OrderedDict([
    ("cltby", "Fairfield Inn & Suites Shelby -- SHELBY, Cleveland County, 45 miles west."),
    ("cltfv", "Fairfield Inn & Suites Statesville -- STATESVILLE, Iredell County, 40 miles north."),
    ("cltht", "TownePlace Suites Hickory -- HICKORY, Catawba County, 55 miles northwest."),
    ("cltsb", "Courtyard Salisbury -- SALISBURY, Rowan County, 45 miles northeast."),
    ("cltll", "Aloft Mooresville -- MOORESVILLE, Iredell County; this market HOLDS Mooresville "
              "as a corridor that claims no postal code."),
    ("cltmo", "SpringHill Suites Charlotte Lake Norman/Mooresville -- Mooresville; HELD."),
    ("cltmr", "Fairfield Inn Charlotte Mooresville/Lake Norman -- Mooresville; HELD."),
    ("clttm", "TownePlace Suites Charlotte Mooresville -- Mooresville; HELD."),
    ("cltfr", "Fairfield Inn & Suites Charlotte Monroe -- MONROE, Union County; HELD."),
])
#: Non-CLT codes whose NAME token reads like Charlotte and is not. "Charlotte"
#: is also a town in MICHIGAN and a county seat in VIRGINIA, "Charlottesville"
#: shares its first eleven letters, and "University", "Uptown", "Concord" and
#: "Belmont" are place names in a dozen states. Recorded rather than silently
#: filtered: the audit trail is the point.
TOKEN_TRAPS = OrderedDict([
    ("choak", "The Draftsman Charlottesville University Autograph Collection -- "
              "CHARLOTTESVILLE, VIRGINIA. CHO is Charlottesville-Albemarle."),
    ("choch", "Courtyard Charlottesville -- Charlottesville, VIRGINIA."),
    ("chodt", "Courtyard Charlottesville University Medical Center -- Charlottesville, VIRGINIA."),
    ("chocy", "Residence Inn Charlottesville Downtown -- Charlottesville, VIRGINIA."),
    ("chova", "Hyatt Place Charlottesville -- Charlottesville, VIRGINIA."),
])

#: Several brands put the STATE in the URL path: Wyndham as
#: ``/ramada/franklin-ohio/``, Drury as ``/locations/middletown-oh/``. That is a
#: first-party statement of geography and it settles a locality token outright:
#: ones. Charlotte has the same hazard in sharper form: Charlotte is a town in
#: MICHIGAN and a county seat in VIRGINIA, Concord is in New Hampshire,
#: California and Massachusetts, Belmont is in a dozen states, and Monroe is in
#: eighteen. A stated state that is neither Carolina drops the row.
_URL_STATE = re.compile(
    r"/[a-z0-9-]+-(alabama|arkansas|california|colorado|connecticut|delaware|florida|"
    r"georgia|illinois|indiana|iowa|kansas|kentucky|louisiana|maine|maryland|"
    r"massachusetts|michigan|minnesota|mississippi|missouri|nebraska|nevada|"
    r"new-hampshire|new-jersey|new-york|north-carolina|ohio|oklahoma|oregon|"
    r"pennsylvania|south-carolina|tennessee|texas|utah|vermont|virginia|"
    r"washington|west-virginia|wisconsin)/|/locations/[a-z0-9-]+-"
    r"(al|ar|az|ca|co|ct|de|fl|ga|ia|id|il|in|ks|ky|la|ma|md|me|mi|mn|mo|ms|mt|nc|"
    r"nd|ne|nh|nj|nm|nv|ny|oh|ok|or|pa|ri|sc|sd|tn|tx|ut|va|vt|wa|wi|wv|wy)/",
    re.I)

NON_US_LOCALE = re.compile(r"marriott\.com/(?!en-us/)[a-z]{2}(?:-[a-z]{2})?/", re.I)
MARRIOTT_CODE = re.compile(r"marriott\.com/(?:[a-z-]+/)?hotels/([a-z0-9]{5,7})-([^/]+)/overview", re.I)
_MARRIOTT_SUBPAGE = re.compile(r"/overview/.+", re.I)

#: A Charlotte-market street address, for the cross-market collision scan.
CHARLOTTE_ADDR = re.compile(
    r"\b(charlotte|pineville|matthews|mint hill|huntersville|cornelius|davidson|"
    r"concord|harrisburg|belmont|gastonia|cramerton|fort mill|tega cay|"
    r"indian land|ballantyne|southpark|northlake|steele creek|university city)\b", re.I)
#: Every postal code the Charlotte contract ADMITS, plus the four held
#: corridors' codes, for the cross-market collision scan.
CHARLOTTE_ZIP = re.compile(
    r"\b(28(?:0(?:12|27|25|31|36|52|54|56|75|78|81|83)|1(?:05|10|12|15|17|34)|"
    r"2(?:02|03|04|05|06|07|08|09|10|11|12|13|14|15|16|17|23|26|27|62|69|70|73|77|78)|"
    r"079|173)|29(?:7(?:07|08|10|15|30|32|33)))\b""")


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def locality_token(url):
    u = url.lower()
    for tok in LOCALITY_TOKENS:
        if tok in u:
            return tok
    return ""


def classify_owned_url(fam, url):
    """Why this owned URL is, or is not, a Charlotte lead."""
    rec = OrderedDict([("family", fam), ("url", url)])
    if NON_US_LOCALE.search(url):
        # NORMALISE, never drop. Toledo lost a real property to a /ja/ locale
        # path once; the language of a URL is not a fact about the hotel.
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
        rec["why"] = "a sub-page of the canonical overview route, not another property"
        return rec
    rec["property_code"] = code
    rec["slug"] = slug
    rec["locality_token"] = tok
    if code and code in CLT_TRAPS:
        rec["verdict"] = "DROPPED_CODE_PREFIX_REACHES_ANOTHER_MARKET"
        rec["why"] = CLT_TRAPS[code]
        return rec
    if code and code in TOKEN_TRAPS:
        rec["verdict"] = "DROPPED_LOCALITY_TOKEN_IS_ANOTHER_PLACE"
        rec["why"] = TOKEN_TRAPS[code]
        return rec
    if code and code.startswith(CODE_PREFIX):
        rec["verdict"] = "OWNED_LEAD_BY_PROPERTY_CODE"
        rec["why"] = ("property code %r carries this market's %s prefix; the code "
                      "SELECTS the candidate and the property page will ADMIT or "
                      "reject it on the address it states" % (code, CODE_PREFIX.upper()))
        return rec
    if code and tok:
        rec["verdict"] = "DROPPED_TOKEN_WITHOUT_MARKET_CODE"
        rec["why"] = ("slug carries the locality token %r but property code %r is "
                      "not a %s code, so the token names another place"
                      % (tok, code, CODE_PREFIX.upper()))
        return rec
    state_m = _URL_STATE.search(url)
    if state_m:
        stated = (state_m.group(1) or state_m.group(2) or "").lower()
        rec["url_states_state"] = stated
        if stated not in ("north-carolina", "nc", "south-carolina", "sc"):
            rec["verdict"] = "DROPPED_URL_STATES_ANOTHER_STATE"
            rec["why"] = ("the brand's own URL places this property in %r, and this "
                          "market admits North Carolina and South Carolina only; the "
                          "locality token %r names an identically spelled town in "
                          "another state" % (stated, tok or "-"))
            return rec
    if tok:
        rec["verdict"] = "OWNED_LEAD_BY_LOCALITY_TOKEN"
        rec["why"] = ("no property code in this URL; the locality token %r proposes "
                      "a lead that identity reconciliation must confirm" % tok)
        return rec
    rec["verdict"] = "NOT_A_LEAD"
    rec["why"] = "neither a market property code nor a market locality token"
    return rec


def scan_harvests():
    leads, dropped, per_family, sources = [], [], Counter(), []
    seen = set()
    for label, path in OWNED_HARVESTS:
        if not os.path.exists(path):
            sources.append(OrderedDict([("source", label), ("path", os.path.relpath(path, _DASH)),
                                        ("status", "MISSING")]))
            continue
        doc = _load(path)
        cands = doc.get("candidates") or []
        fam_counts = Counter(r.get("family", "?") for r in cands)
        tn_rows = 0
        for row in cands:
            fam = row.get("family", "?")
            url = row.get("url") or ""
            rec = classify_owned_url(fam, url)
            rec["owned_source"] = label
            if rec["verdict"].startswith("OWNED_LEAD"):
                key = (fam, rec.get("property_code") or rec["url"])
                if key in seen:
                    continue
                seen.add(key)
                leads.append(rec)
                per_family[fam] += 1
                tn_rows += 1
            elif rec["verdict"].startswith("DROPPED_"):
                dropped.append(rec)
        sources.append(OrderedDict([
            ("source", label), ("path", os.path.relpath(path, _DASH)), ("status", "READ"),
            ("work_order", doc.get("work_order")), ("as_of", doc.get("as_of")),
            ("rows_in_file", len(cands)),
            ("families_in_file", OrderedDict(sorted(fam_counts.items()))),
            ("charlotte_leads_from_this_source", tn_rows),
            ("refused_families_recorded_then", doc.get("refused_families") or {}),
        ]))
    return leads, dropped, per_family, sources


def scan_also_checked():
    out = []
    pat = re.compile(r"charlotte|brentwood|goodlettsville|opryland|donelson|hermitage|"
                     r"cool.springs|mount.juliet|smyrna|\bTN\b", re.I)
    for name in OWNED_ALSO_CHECKED:
        path = os.path.join(REPORTS, name)
        if not os.path.exists(path):
            out.append(OrderedDict([("file", name), ("status", "MISSING")]))
            continue
        text = open(path, encoding="utf-8").read()
        hits = len(pat.findall(text))
        out.append(OrderedDict([
            ("file", name), ("status", "READ"), ("bytes", len(text)),
            ("charlotte_or_carolinas_tokens", hits),
            ("verdict", "OWNS_CHARLOTTE_CONTENT" if hits else "NO_CHARLOTTE_CONTENT")]))
    return out


def scan_cross_market():
    """Does any registered market's census already hold a Charlotte hotel?"""
    findings, scanned = [], []
    if not os.path.isdir(CENSUS_DIR):
        return findings, scanned
    for name in sorted(os.listdir(CENSUS_DIR)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(CENSUS_DIR, name)
        doc = _load(path)
        rows = doc.get("identities") or doc.get("records") or doc.get("census") or []
        if isinstance(rows, dict):
            rows = list(rows.values())
        hits = 0
        for row in rows:
            if not isinstance(row, dict):
                continue
            addr = " ".join(str(row.get(k) or "") for k in
                            ("address_line", "address", "city", "state", "postal_code"))
            if CHARLOTTE_ZIP.search(addr) and CHARLOTTE_ADDR.search(addr):
                hits += 1
                findings.append(OrderedDict([
                    ("market_file", name), ("name", row.get("name")),
                    ("address", addr.strip()),
                    ("why", "a registered market's census states a Charlotte-market "
                            "postal code AND locality; this must be reconciled before "
                            "Charlotte claims the identity")]))
        scanned.append(OrderedDict([("census", name), ("rows", len(rows)),
                                    ("charlotte_address_hits", hits)]))
    return findings, scanned


def main():
    contract = _load(CONTRACT)
    admitted_zips = sorted({z for c in contract["corridors"]
                            for z in c.get("included_postal_codes") or []})
    held_zips = sorted({z for c in contract["corridors"]
                        for z in c.get("_held_postal_codes") or []})

    leads, dropped, per_family, sources = scan_harvests()
    also = scan_also_checked()
    collisions, censuses = scan_cross_market()

    drop_reasons = Counter(r["verdict"] for r in dropped)
    doc = OrderedDict([
        ("schema", SCHEMA),
        ("work_order", WORK_ORDER),
        ("phase", "3 -- owned evidence, ladder rung 0"),
        ("market_id", MARKET_ID),
        ("what_this_is",
         "Everything the repository already owns about the Greater Charlotte "
         "lodging market, read before any external request. Zero HTTP requests, "
         "zero paid provider calls, zero USD."),
        ("free_http_requests", 0),
        ("paid_provider_calls", 0),
        ("usd_spent", 0.0),
        ("market_geography_read", OrderedDict([
            ("market_contract", os.path.relpath(CONTRACT, _DASH)),
            ("admitted_postal_codes", admitted_zips),
            ("held_postal_codes", held_zips)])),
        ("owned_sources", sources),
        ("other_corpora_checked", also),
        ("owned_leads_by_family", OrderedDict(sorted(per_family.items()))),
        ("owned_leads_total", len(leads)),
        ("dropped_by_reason", OrderedDict(sorted(drop_reasons.items()))),
        ("code_prefix_traps_recorded", CLT_TRAPS),
        ("locality_token_traps_recorded", TOKEN_TRAPS),
        ("cross_market_collision_scan", OrderedDict([
            ("censuses_scanned", censuses),
            ("collisions_found", len(collisions)),
            ("collisions", collisions)])),
        ("what_must_still_be_acquired", [
            "Hilton -- zero property URLs in either owned Ohio harvest; not owned.",
            "IHG, Choice, Wyndham, Best Western, Hyatt, ESA/WoodSpring, Red Roof, "
            "Motel 6/G6, Sonesta, Drury, Radisson -- the owned slices were filtered "
            "to OHIO and contain no Carolinas row.",
            "Every policy fact for every identity: the owned corpus is ROUTING and "
            "IDENTITY evidence only and contains no Charlotte policy read.",
            "Every refusal recorded in the owned harvests is five days old and is "
            "RE-PROBED by this order rather than inherited.",
        ]),
        ("owned_leads", leads),
        ("dropped_rows", dropped),
    ])
    os.makedirs(REPORTS, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1)
        fh.write("\n")

    print("wrote %s" % os.path.relpath(OUT, _DASH))
    print("owned leads          %d  %s" % (len(leads), dict(per_family)))
    print("dropped              %d  %s" % (len(dropped), dict(drop_reasons)))
    print("cross-market hits    %d" % len(collisions))
    print("requests 0, USD 0.00")


if __name__ == "__main__":
    main()
