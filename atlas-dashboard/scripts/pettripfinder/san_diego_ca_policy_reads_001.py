"""PTF-SAN-DIEGO-CA-HARDENED-SOURCE-READY-001 -- Phase 17: the FIRST-PARTY READS, assembled for the census.

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
  launch_packages/pettripfinder/markets/reports/san_diego_ca_policy_reads_001.json
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

WORK_ORDER = "PTF-SAN-DIEGO-CA-HARDENED-SOURCE-READY-001"
MARKET_ID = "san-diego-ca"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
STAGING = os.path.join(PKG, "markets", "staging", MARKET_ID, "raw_captures")
OUT = os.path.join(REPORTS, "san_diego_ca_policy_reads_001.json")

_ZIP = re.compile(r"\b(\d{5})(?:-\d{4})?\b")
_STATE = re.compile(r"\b(CA|California)\b")
#: San Diego County's municipalities and the communities its pages print as a city, for the IHG address shape.
_MUNICIPALITY_TAIL = re.compile(
    r"\s(San Diego|Carlsbad|Oceanside|Encinitas|Solana Beach|Del Mar|Coronado|Chula Vista|National City|"
    r"Imperial Beach|La Mesa|El Cajon|Santee|Lemon Grove|Poway|Escondido|San Marcos|Vista|La Jolla|"
    r"San Ysidro|Cardiff(?: by the Sea)?|Rancho Santa Fe|Spring Valley|Bonita)$", re.I)
#: Browser outcomes whose page rendered the property's OWN name and address. Walls and mismatches are absent.
_IDENTITY_BEARING_OUTCOMES = ("READ", "NO_OPERATIVE_STATEMENT", "IDENTITY_BOUND_POLICY_SOURCE_SILENT",
                              "AMENITY_CHIP_ONLY_NOT_OPERATIVE")


def _load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _s(v):
    return " ".join(str(v or "").split())


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
    zips = _ZIP.findall(line)
    postal = zips[-1] if zips else ""
    if postal and line.split()[0].isdigit() and line.split()[0] == postal and len(zips) == 1:
        postal = ""                      # the only five-digit run IS the house number
    parts = [p.strip() for p in line.split(",") if p.strip()]
    street = parts[0] if parts else ""
    locality, region = "", ""
    # IHG prints "2725 Palomar Airport Road Carlsbad, CA 92009 United States": no comma between the street and
    # the city, so the city rides on the street and splits the building from its own census row. When the second
    # part opens with the state, the first part's trailing municipality is the locality.
    if len(parts) > 1 and re.match(r"(CA|California)\b", parts[1]):
        m = _MUNICIPALITY_TAIL.search(street)
        if m:
            street, locality = street[:m.start()].strip(), m.group(1)
    for p in parts[1:]:
        if _STATE.search(p) and not region:
            m = _STATE.search(p)
            region = "CA"
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
        _r = _row("ATTENDED_BROWSER", r.get("family"), r.get("requested_url"), r.get("final_url"),
                         r.get("page_title"), street, locality, region, postal, "",
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
                         r.get("n"), r.get("st"), r.get("ci"), "CA", r.get("z"), r.get("ph"),
                  r.get("property_code"), "the address the brand's own property page states",
                  r.get("h"), r.get("b"))
        if _r is None:
            refused["brand_page_no_name_on_page"] += 1
        else:
            rows.append(_r)

    # ---------------------------------------------------------------- routed Firecrawl + static
    for path, lane in ((os.path.join(REPORTS, "san_diego_ca_firecrawl_pass_001.json"), "FIRECRAWL"),
                       (os.path.join(REPORTS, "san_diego_ca_free_static_capture_001.json"),
                        "DIRECT_STATIC_FETCH")):
        for r in (_load(path, {}) or {}).get("rows", []):
            if not r.get("identity_confirmed"):
                refused["%s_identity_not_confirmed" % lane.lower()] += 1
                continue
            sig = r.get("identity_assessment", {}).get("signals") or r.get("identity_signals") or {}
            street = _s(sig.get("address_on_page"))
            if not street:
                refused["%s_no_address_on_page" % lane.lower()] += 1
                continue
            _r = _row(lane, r.get("family"), r.get("requested_url"), r.get("final_url"),
                             sig.get("name_on_page"), street, sig.get("locality"), sig.get("region") or "CA",
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
                             r.get("name") or r.get("canonical_name"), street, r.get("city"), "CA",
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
                  r.get("ci"), r.get("rg") or "CA", r.get("z"), r.get("ph"), r.get("id"),
                  "the brand's own property service for the route's own property id",
                  r.get("h") or "", r.get("b") or 0)
        if _r is None:
            refused["wyndham_service_no_name"] += 1
        else:
            rows.append(_r)

    seen, deduped = set(), []
    for r in rows:
        k = (r["final_url"], r["identity_signals"]["address_on_page"])
        if k in seen:
            continue
        seen.add(k)
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
