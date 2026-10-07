"""PTF-SALT-LAKE-CITY-UT-HARDENED-SOURCE-READY-001 -- Phase 17: the FIRST-PARTY READS, assembled for the census.

THE PIPELINE IS census -> routing -> capture -> census, AND THIS IS THE JOIN.
--------------------------------------------------------------------------
The census reconciliation reads a single document of first-party page reads (``PROPERTY_PAGE``, tier 1) -- the
only lane allowed to overwrite a premises, because the address a property's OWN page states outranks a state
licence, a map pin and a bureau listing alike. Every other market's source-ready order fed that document by
hand; this one assembles it mechanically from the captures this order actually took, so the second census pass
sees exactly what the capture lanes read and nothing else.

WHAT IT CARRIES, AND WHY EACH ONE IS FIRST-PARTY
------------------------------------------------
  browser_closure_rows.json   the attended-browser reads of Marriott, Hilton, Hyatt, Best Western, Red Roof and
                              Motel 6 property pages -- the brand's own page for the brand's own property code.
  brand_page_rows.json        the Choice and IHG property pages read through Firecrawl, each carrying the
                              address its OWN page states (``address_basis: PAGE_OWN_ADDRESS_LINE``).
  firecrawl_pass_001.json     the routed Firecrawl reads whose identity the shared gate CONFIRMED.
  free_static_capture         the plain-client reads whose identity the shared gate CONFIRMED.
  policy_pages / closure      the independents' own sites, bound by the site's own house number + ZIP or phone.

WHAT IT REFUSES TO CARRY
------------------------
  * a read with NO address on the page -- it can confirm nothing and would overwrite a premises with a blank;
  * a read the shared identity gate did not confirm (``identity_confirmed`` false), including every
    IDENTITY_MISMATCH -- a page that names a different building is evidence about that building, not this one;
  * every DENIED, CAPTCHA and error row -- a wall is not a read;
  * a POLICY. Nothing in this document is a pet fact. The clean authority still adjudicates policy from the
    capture reports themselves; this document exists so the CENSUS can learn a premises and a route.

A MEASURED LIMIT OF THIS RUN, STATED RATHER THAN PAPERED OVER
-------------------------------------------------------------
SAN DIEGO's browser transcription records each page's own NAME (its title heading) and its own one-line
ADDRESS, so every attended-browser page that rendered both is carried. A read with no name is still refused and
counted (the shared identity-key contract refuses an empty name outright: "an empty key would match every other
empty key"); a name is never invented from the census row, the route slug or the brand.

WHY THE ROUTE MATTERS AS MUCH AS THE ADDRESS
--------------------------------------------
Six rows were HELD on the first adjudication for ROUTE_DOMAIN_CONFLICT: the census bound the identity to a
vanity or legacy domain the destination bureau published (``hiexpress.com/jaxmayportbch``,
``jacksonvillewyndhamgarden.com``, ``hyattstudios...com``) while the capture lane read the brand's own
canonical page (``ihg.com``, ``wyndhamhotels.com``, ``hyatt.com``). Both pages are the property's, and the
package contract requires a published record to cite the route the census binds -- so the census has to learn
the canonical route rather than the adjudicator being allowed to repoint one. A tier-1 PROPERTY_PAGE
observation carries that route, and the census's own route preference ranks it above a bureau link.

Output:
  launch_packages/pettripfinder/markets/reports/salt_lake_city_ut_policy_reads_001.json
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

WORK_ORDER = "PTF-SALT-LAKE-CITY-UT-HARDENED-SOURCE-READY-001"
MARKET_ID = "salt-lake-city-ut"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
STAGING = os.path.join(PKG, "markets", "staging", MARKET_ID, "raw_captures")
OUT = os.path.join(REPORTS, "salt_lake_city_ut_policy_reads_001.json")

_ZIP = re.compile(r"\b(\d{5})(?:-\d{4})?\b")
#: SALT LAKE CITY: the state is Utah. "UT" is matched as a whole word only, and "UT" is also a STATE ROUTE prefix in
#: this market's addresses ("4377 UT-224", "UT 248" -- Park City's own spines), so the abbreviation must not be followed
#: by a route NUMBER (one to four digits); a five-digit run after the state is the POSTAL CODE and must stay a state.
_STATE_WORDS = r"(UT|Utah)\b(?!\.?\s*(?:Hwy|Highway|-?\s*\d{1,4}\b))"
_STATE = re.compile(r"\b" + _STATE_WORDS)
_STATE_CODE = {"ut": "UT", "utah": "UT"}
#: The Salt Lake City / Park City municipalities its pages print as a city, for the IHG address shape (and the refused
#: neighbours, so a page that names one is still split correctly and then refused by its own postal code). Longest
#: names first, so "West Valley City" is never cut to "Valley City".
_MUNICIPALITY_TAIL = re.compile(
    r"\s(Salt Lake City|South Salt Lake|North Salt Lake|West Valley City|Cottonwood Heights|West Jordan|"
    r"South Jordan|West Bountiful|Woods Cross|Park City|Millcreek|Holladay|Taylorsville|Murray|Midvale|Sandy|"
    r"Draper|Kearns|Riverton|Herriman|Bluffdale|Lehi|Bountiful|Magna|Heber City|Midway|Provo|Orem|Ogden|Layton|"
    r"Farmington|Tooele|Alta|Snowbird)$", re.I)

#: Browser outcomes whose page rendered the property's OWN name and address. Walls and mismatches are absent.
_IDENTITY_BEARING_OUTCOMES = ("READ", "NO_OPERATIVE_STATEMENT", "IDENTITY_BOUND_POLICY_SOURCE_SILENT",
                              "AMENITY_CHIP_ONLY_NOT_OPERATIVE")


def _state_for(postal):
    """Utah for an 840-847 code: the state a postal code belongs to, used only where a lane's row states no state
    of its own."""
    z = "".join(ch for ch in str(postal or "") if ch.isdigit())[:3]
    return "UT" if z.isdigit() and 840 <= int(z) <= 847 else ""


def _load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _s(v):
    return " ".join(str(v or "").split())


#: PORTLAND: an independent's own policy / FAQ subpage is titled for the SECTION or for search ("FAQs - Hotel Grand
#: Stark", "Portland Hotels' Contemporary Amenities | Eastside Lodge", "Hotel Policies | Hyatt House Portland /
#: Beaverton", "Extended Stay Hotel in Vancouver, WA | WoodSpring Suites Portland Vancouver"). The census name contest
#: keeps the LONGEST name, so a section label or a search phrase left in the title would rename the hotel. Only the
#: property's own name survives: section / search segments are dropped and section words trimmed off each end.
_TITLE_GENERIC_SEGMENT = re.compile(
    r"^(?:our\s+)?(?:policies|policy|faqs?|frequently asked questions|amenities|contact(?:\s+us)?|home|"
    r"guest policies|official site|hotel policies(?:\s*&\s*house rules)?|salt lake city|park city|slc|deer valley|"
    r"staypineapple hotels|"
    # the OPERATOR of two guesthouses (Evermore and Bluebird), never the name of the one premises a read binds
    r"division inns)$", re.I)
_TITLE_SEARCH_SEGMENT = re.compile(r"\bhotels?\s+in\b|\bhotels'|^(?:salt lake city|park city|deer valley|downtown salt lake)\b.*\bhotels?$", re.I)
_TITLE_LEAD = re.compile(r"^(?:faqs?(?:\s+about\s+our\s+[^-–—]+)?|accommodations|amenities and services at|"
                         r"[a-z' ]+\scollection(?=\s*[-–—]))"
                         r"\s*[-–—:]?\s*", re.I)
_TITLE_TAIL = re.compile(r"\s*[-–—]?\s*(?:faqs?|amenities|terms\s*(?:&|and)\s*conditions|reservation policy|"
                         r"terms, payments & cancellation policies|official site)?\s*[-–—]?\s*$",
                         re.I)
_TITLE_MCMENAMINS = re.compile(r"^(.*?)(?:\s+hotel)?\s*-\s*mcmenamins$", re.I)


def _title_name(title):
    """The property's own name out of a page title, or "" when the title names only a section or a search phrase."""
    segs = []
    for seg in (title or "").replace("�", "-").split("|"):
        seg = " ".join(seg.split())
        if not seg or _TITLE_GENERIC_SEGMENT.match(seg) or _TITLE_SEARCH_SEGMENT.search(seg):
            continue
        seg = _TITLE_TAIL.sub("", _TITLE_LEAD.sub("", seg)).strip()
        _mc = _TITLE_MCMENAMINS.match(seg)
        if _mc:
            seg = "McMenamins %s" % _mc.group(1).strip()
        if seg and not _TITLE_GENERIC_SEGMENT.match(seg):
            segs.append(seg)
    return segs[0] if segs else ""


def _split_address_line(line):
    """(street, locality, region, postal) from a page's own one-line address.

    The brands print it four ways in this market:
      "4670 Salisbury Road, Jacksonville, Florida, USA, 32256"      (Marriott)
      "1201 Riverplace Boulevard, Jacksonville, Florida, 32207, USA" (Hilton)
      "225 East Coastline Drive, Jacksonville, FL 32202, United States of America" (Hyatt)
      "1063 Airport Rd, Jacksonville FL"                             (Red Roof -- no postal code)
    The POSTAL CODE IS THE LAST five-digit run, never the first: a five-digit house number is ordinary here
    ("14565 Duval Road"), and taking the first run read the house number as the ZIP in the browser lane's own
    first cut.
    """
    line = _s(line)
    if not line:
        return "", "", "", ""
    # NEW ORLEANS (kept): the accessibility tree joins a footer's separate street and city elements with no space at
    # all ("...BoulevardNew Orleans, ..." was the first seen), which glues the city into the street's last word. A lower-case letter directly
    # followed by a capitalised municipality name is that seam; only the market's own municipality names split it.
    line = re.sub(r"(?<=[a-z])(?=(?:%s)\b)" % _MUNICIPALITY_TAIL.pattern[3:-2], " ", line)
    zips = _ZIP.findall(line)
    postal = zips[-1] if zips else ""
    if postal and line.split()[0].isdigit() and line.split()[0] == postal and len(zips) == 1:
        postal = ""                      # the only five-digit run IS the house number
    # SEATTLE (kept): Hotel Andra's own page printed "2000 4th Avenue - Seattle WA 98121" -- a dash, not a comma,
    # between the street and the locality. With no comma at all the whole line became the street.
    if "," not in line and " - " in line:
        line = line.replace(" - ", ", ", 1)
    # SEATTLE (kept): a footer can print "12035 Aurora Ave N Seattle WA 9813" -- no comma at all. The municipality
    # before the state is the locality; a short code is never a ZIP.
    if "," not in line:
        m = re.match(r"^(.*?)%s\s+%s(.*)$" % (_MUNICIPALITY_TAIL.pattern[:-1], _STATE_WORDS), line, re.I)
        if m:
            line = "%s, %s, %s%s" % (m.group(1).strip(), m.group(2), _STATE_CODE[m.group(3).lower()], m.group(4))
    # ("401 Lenora Street, ..." -- Warwick's footer cuts itself off; an ellipsis is never a locality.)
    parts = [p.strip() for p in line.split(",") if p.strip().strip(".…")]
    street = parts[0] if parts else ""
    locality, region = "", ""
    # IHG prints "2725 Palomar Airport Road Carlsbad, CA 92009 United States": no comma between the street and
    # the city, so the city rides on the street and splits the building from its own census row. When the second
    # part opens with the state, the first part's trailing municipality is the locality.
    if len(parts) > 1 and re.match(_STATE_WORDS, parts[1], re.I):
        m = _MUNICIPALITY_TAIL.search(street)
        if m:
            street, locality = street[:m.start()].strip(), m.group(1)
    for p in parts[1:]:
        if _STATE.search(p) and not region:
            m = _STATE.search(p)
            region = _STATE_CODE[m.group(1).lower()]
            head = p[:m.start()].strip()
            if head and not locality:
                locality = head
        elif not locality and not _ZIP.search(p) and "united states" not in p.lower() and p.upper() != "USA":
            locality = p
    return street, locality, region, postal


def _row(lane, brand, requested, final, name, street, locality, region, postal, phone, code,
         binding, sha="", nbytes=0, lat=None, lng=None):
    """A read row, or None when the page names nothing.

    A READ WITH NO NAME ON ITS PAGE CANNOT OPEN AN IDENTITY. The shared identity-key contract refuses an empty
    name outright -- "an empty key would match every other empty key" -- and it is right to: a page that states
    an address but no establishment name is evidence that SOMETHING is at that address, not that this row is.
    Measured here on Choice property pages whose own name field came back blank through the renderer.
    """
    if not _s(name):
        return None
    return OrderedDict([
        ("lane", lane),
        ("brand", brand or ""),
        ("requested_url", requested or ""),
        ("final_url", final or requested or ""),
        ("identity_confirmed", True),
        ("identity_binding_method", binding),
        ("document_sha256", sha or ""),
        ("document_bytes", nbytes or 0),
        ("identity_signals", OrderedDict([
            ("name_on_page", _s(name)),
            ("address_on_page", _s(street)),
            ("locality", _s(locality)),
            ("region", _s(region)),
            ("postal_code", _s(postal)[:5]),
            ("phone_on_page", _s(phone)),
            ("property_code_on_page", _s(code)),
            ("lat", lat), ("lng", lng),
        ])),
    ])


def build():
    rows, refused = [], Counter()

    # ---------------------------------------------------------------- attended browser
    # A PAGE THAT STATES NO POLICY STILL STATES ITS PREMISES. The brand's own property page that rendered its own
    # name and address but no operative pet statement (Coronado Island Marriott, window 4) is identity evidence
    # exactly as good as one that did; only a WALL (denial, CAPTCHA, error page) or a page naming a DIFFERENT
    # building is refused. This document never carries a policy either way.
    for r in (_load(os.path.join(STAGING, "browser_closure_rows.json"), {}) or {}).get("rows", []):
        if r.get("outcome") not in _IDENTITY_BEARING_OUTCOMES:
            refused["browser_not_a_read"] += 1
            continue
        street, locality, region, postal = _split_address_line(r.get("page_address_line"))
        if not street:
            refused["browser_no_address_on_page"] += 1
            continue
        # SEATTLE (kept): a page that prints its street and city but NO postal code (Red Roof, Best Western) and that the
        # browser lane BOUND to one census row by the page's own house number and street words carries that bound
        # row's postal code -- never a guessed one; an unbound page stays without a ZIP and joins nothing.
        if not postal and r.get("identity_key") and r.get("census_postal"):
            postal = r.get("census_postal")
        # SEATTLE (kept): a policy SUBPAGE's title names the section first ("OUR POLICIES | Beston Inn"); the property's own
        # name is the part after the bar, never the section label.
        _name = _title_name(r.get("page_title") or "")
        _r = _row("ATTENDED_BROWSER", r.get("family"), r.get("requested_url"), r.get("final_url"),
                         _name, street, locality, region, postal, "",
                  r.get("property_code"), "the brand's own page for its own property code",
                  r.get("transcription_sha256"), r.get("quote_byte_length"))
        if _r is None:
            refused["browser_no_name_on_page"] += 1
        else:
            rows.append(_r)

    # ---------------------------------------------------------------- Choice / IHG brand pages (Firecrawl)
    bp = _load(os.path.join(STAGING, "brand_page_rows.json"), {}) or {}
    for r in (bp.get("rows") if isinstance(bp, dict) else bp) or []:
        if not r.get("ok") or not _s(r.get("st")):
            refused["brand_page_no_address_on_page"] += 1
            continue
        _r = _row("FIRECRAWL_BRAND_PAGE", r.get("family"), r.get("u"), r.get("final_url"),
                         r.get("n"), r.get("st"), r.get("ci"), _state_for(r.get("z")), r.get("z"), r.get("ph"),
                  r.get("property_code"), "the address the brand's own property page states",
                  r.get("h"), r.get("b"))
        if _r is None:
            refused["brand_page_no_name_on_page"] += 1
        else:
            rows.append(_r)

    # ---------------------------------------------------------------- routed Firecrawl + static
    for path, lane in ((os.path.join(REPORTS, "salt_lake_city_ut_firecrawl_pass_001.json"), "FIRECRAWL"),
                       # DENVER: the follow-up pass over rows the rerouted census opened after the first pass.
                       (os.path.join(REPORTS, "salt_lake_city_ut_firecrawl_pass_002.json"), "FIRECRAWL"),
                       (os.path.join(REPORTS, "salt_lake_city_ut_free_static_capture_001.json"),
                        "DIRECT_STATIC_FETCH")):
        for r in (_load(path, {}) or {}).get("rows", []):
            if not (r.get("identity_confirmed") or (r.get("identity_assessment") or {}).get("confirmed")):
                refused["%s_identity_not_confirmed" % lane.lower()] += 1
                continue
            sig = r.get("identity_assessment", {}).get("signals") or r.get("identity_signals") or {}
            street = _s(sig.get("address_on_page"))
            if not street:
                refused["%s_no_address_on_page" % lane.lower()] += 1
                continue
            _r = _row(lane, r.get("family"), r.get("requested_url"), r.get("final_url"),
                             sig.get("name_on_page"), street, sig.get("locality"),
                             sig.get("region") or _state_for(sig.get("postal_code")),
                             sig.get("postal_code"), sig.get("phone_on_page"),
                             sig.get("property_code_on_page"),
                             "the shared identity gate confirmed the page against this row's premises",
                      r.get("document_sha256") or r.get("page_sha256") or "",
                      r.get("document_bytes") or r.get("bytes") or 0)
            if _r is None:
                refused["%s_no_name_on_page" % lane.lower()] += 1
            else:
                rows.append(_r)

    # ---------------------------------------------------------------- the independents' own sites
    for fname in ("policy_pages_rows.json", "closure_static_rows.json"):
        for r in (_load(os.path.join(STAGING, fname), {}) or {}).get("rows", []):
            if not r.get("bound"):
                refused["independent_site_not_bound"] += 1
                continue
            street = _s(r.get("address_on_page") or r.get("street"))
            if not street:
                refused["independent_site_no_address_on_page"] += 1
                continue
            _r = _row("DIRECT_STATIC_FETCH", "INDEPENDENT", r.get("url"), r.get("final_url"),
                             r.get("name") or r.get("canonical_name"), street, r.get("city"),
                             _state_for(r.get("postal_code") or r.get("postal")),
                             r.get("postal_code") or r.get("postal"), r.get("phone"), "",
                      "the site's own house number + postal code or telephone",
                      r.get("sha256") or "", r.get("bytes") or 0)
            if _r is None:
                refused["independent_site_no_name_on_page"] += 1
            else:
                rows.append(_r)

    # ---------------------------------------------------------------- Wyndham's own property service
    # SAN DIEGO: the Wyndham lane reads the brand's OWN property service (the JSON its overview page renders),
    # which states the property's own name, street and postal code. It was never carried to the census, so La
    # Quinta Carlsbad kept a map ZIP (92009) its brand states as 92011, and the Days Inn Chula Vista route stayed
    # on a 699 E Street row although the brand's own service places that route at 394 Broadway.
    wyn = _load(os.path.join(STAGING, "wyndham_rows.json"), {}) or {}
    for r in wyn.get("rows", []):
        if not _s(r.get("st")):
            refused["wyndham_service_no_address"] += 1
            continue
        _r = _row("WYNDHAM_PROPERTY_SERVICE", "WYNDHAM", r.get("u"), r.get("u"), r.get("n"), r.get("st"),
                  r.get("ci"), r.get("rg") or _state_for(r.get("z")), r.get("z"), r.get("ph"), r.get("id"),
                  "the brand's own property service for the route's own property id",
                  r.get("h") or "", r.get("b") or 0)
        if _r is None:
            refused["wyndham_service_no_name"] += 1
        else:
            rows.append(_r)

    # NEW ORLEANS: a later read of the same page that states the postal code an earlier read lacked REPLACES it.
    # Marriott's Residence Inn Metairie footer was first transcribed "Three Galleria Boulevard," (the line cut at
    # the comma) and re-read in full ("..., Metairie, Louisiana, USA, 70001"); keeping the first read left the brand
    # row with no postal code, so it never met its own premises and the row read as still awaiting the browser.
    seen, deduped = {}, []
    for r in rows:
        k = (r["final_url"], r["identity_signals"]["address_on_page"])
        if k in seen:
            i = seen[k]
            if r["identity_signals"].get("postal_code") and not deduped[i]["identity_signals"].get("postal_code"):
                deduped[i] = r
            continue
        seen[k] = len(deduped)
        deduped.append(r)

    return OrderedDict([
        ("schema", "ptf-first-party-reads/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("phase", "17 -- the first-party page reads this order took, assembled for the census's second pass"),
        ("what_this_is",
         "Tier-1 PROPERTY_PAGE observations: the premises and the route a property's OWN page states. The "
         "address a property's own page states outranks a state licence, a map pin and a bureau listing, and "
         "this is the only lane the census lets overwrite one."),
        ("this_document_carries_no_policy",
         "Not one pet fact is here. Policy stays with the capture reports and is adjudicated by the clean "
         "authority; this document exists so the census can learn a premises and a canonical route."),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", 0),
        ("rows_kept", len(deduped)),
        ("rows_by_lane", OrderedDict(sorted(Counter(r["lane"] for r in deduped).items()))),
        ("rows_refused", OrderedDict(sorted(refused.items()))),
        ("rows_refused_total", sum(refused.values())),
        ("why_rows_are_refused",
         "A read with no address on its page can confirm nothing and would overwrite a premises with a blank; "
         "a read the shared identity gate did not confirm names a different building; a wall is not a read."),
        ("rows", deduped),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)
    doc = build()
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("kept", doc["rows_kept"], dict(doc["rows_by_lane"]))
    print("refused", doc["rows_refused_total"], dict(doc["rows_refused"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
