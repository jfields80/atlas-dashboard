"""PTF-MIAMI-FL-BROWSER-CLOSURE-002 -- the supported-browser closure pass over SOURCE-READY-001's browser queue.

SOURCE-READY-001 left 116 admitted identities in BROWSER_CAPTURE_NEEDED because the supported browser could not
read marriott.com, hilton.com, hyatt.com or bestwestern.com (extension read permission; plus one Akamai challenge
on marriott.com). The founder has since granted read access for those four domains. This helper takes the reads
this order made through the supported browser (navigate + accessibility-tree `find` only -- no page script, no
relay, no CAPTCHA or anti-bot bypass) and turns them into durable evidence rows the clean authority can bind.

WHAT BINDS A READ TO AN IDENTITY (PHASES 3, 5 and 7)
------------------------------------------------------
In this order, never on a partial address:

  1. PROPERTY CODE   the code in the page's own URL equals the code the census carries for the row; or
  2. NAME + POSTAL   the page's own name, folded to its location words, equals the census row's, AND the page's
                     own postal code equals the census row's; or
  3. FULL STREET     the shared ``address_key`` over the canonical street (house number AND street words) plus
                     the postal code agree.

A house number alone, a ZIP alone, a shared campus or a brand family NEVER bind (the SOURCE-READY-001 defect that
attached a Staybridge policy to Aloft Miami Doral). A page that binds to more than one census row binds to NONE of
them: two rows claiming one page is a census duplicate to be resolved, not a policy to be copied twice.

WHAT THIS DOES NOT DO
---------------------
It decides no policy. The quote goes to the clean authority, where the negation guard, the fee/weight/count
readers and the shared first_party_binding reader judge it exactly as they judge every other lane's evidence.

Output:
  launch_packages/pettripfinder/markets/staging/miami-fl/raw_captures/browser_closure_rows.jsonl
  launch_packages/pettripfinder/markets/reports/miami_fl_browser_closure_002.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.hotel_exclusions import address_key  # noqa: E402
from scripts.pettripfinder.miami_fl_census_reconciliation_001 import canonical_street  # noqa: E402

WORK_ORDER = "PTF-MIAMI-FL-BROWSER-CLOSURE-002"
MARKET_ID = "miami-fl"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
RAW = os.path.join(PKG, "markets", "staging", "miami-fl", "raw_captures")
CENSUS = os.path.join(PKG, "identity_census_proposed", "miami-fl.json")
CLEAN = os.path.join(REPORTS, "miami_fl_clean_authority_001.json")
ROUTING = os.path.join(REPORTS, "miami_fl_routing_001.json")
QUEUE = os.path.join(REPORTS, "miami_fl_browser_queue_002.json")
OUT_JSONL = os.path.join(RAW, "browser_closure_rows.jsonl")
OUT_REPORT = os.path.join(REPORTS, "miami_fl_browser_closure_002.json")
CAPTURE_LANE = "SUPPORTED_BROWSER (navigate + accessibility-tree find only; no page script, no relay, no bypass)"

_CODE_RX = (
    re.compile(r"marriott\.com/en-us/hotels/([a-z0-9]{5})-", re.I),
    re.compile(r"hilton\.com/en/hotels/([a-z0-9]{6,12})-", re.I),
    re.compile(r"hyatt\.com/(?:[^?#]*/)?([a-z]{3}[a-z0-9]{2})(?:[-/?#]|$)", re.I),
    re.compile(r"bestwestern\.com/.*?propertyCode\.(\d{4,6})\.", re.I),
)
#: GENERIC words only. The chain brand ("DoubleTree", "Marriott", "Hampton") is exactly what tells two hotels on
#: one street apart, so it is NEVER folded away: stripping it matched "DoubleTree by Hilton Grand Hotel Biscayne
#: Bay" to "Miami Marriott Biscayne Bay" in this order's first binding pass.
_BRAND_WORDS = re.compile(r"\b(hotel|hotels|inn|inns|suites?|by|the|and|a|an|of|at|on|resort|resorts|spa|"
                          r"collection|usa|united|states|florida|fl)\b", re.I)
_POSTAL_RX = re.compile(r"\b(\d{5})(?:-\d{4})?\b")
_STREET_RX = re.compile(r"^\s*(\d+[A-Za-z]?(?:-\d+)?\s+[^,]+?)\s*,", re.S)


def name_key(name):
    n = re.sub(r"[^a-z0-9 ]", " ", (name or "").lower())
    n = _BRAND_WORDS.sub(" ", n)
    return " ".join(sorted(t for t in n.split() if len(t) > 1))


def same_name(page_name, census_name):
    """Do the page's own name and the census row's name name one property? Location words decide; when a name is
    nothing but brand words ("Hyatt Regency Miami"), the whole normalised names must agree."""
    if not page_name or not census_name:
        return False
    a, b = name_key(page_name), name_key(census_name)
    if a and b and a == b:
        return True
    seq = lambda s: " ".join(re.sub(r"[^a-z0-9 ]", " ", s.lower()).split())  # noqa: E731
    pa, pb = seq(page_name), seq(census_name)
    if pa == pb:
        return True
    # The accessibility read truncates a long heading ("Best Western Plus Miami Airport North Hot"); a heading that
    # is a PREFIX of the census name (or the reverse), at least 12 characters of it, is the same name cut short.
    if len(pa) >= 12 and len(pb) >= 12 and (pb.startswith(pa) or pa.startswith(pb)):
        return True
    norm = lambda s: " ".join(sorted(re.sub(r"[^a-z0-9 ]", " ", s.lower()).split()))  # noqa: E731
    return norm(page_name) == norm(census_name)


def page_code(url):
    for rx in _CODE_RX:
        m = rx.search(url or "")
        if m:
            return m.group(1).lower()
    return ""


def page_street(address):
    m = _STREET_RX.match(address or "")
    return (m.group(1).strip() if m else "").replace("  ", " ")


def page_city(address):
    parts = [p.strip() for p in (address or "").split(",")]
    return " ".join(parts[1].lower().split()) if len(parts) > 1 else ""


def page_postal(address):
    codes = _POSTAL_RX.findall(address or "")
    return codes[-1] if codes else ""


def _load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def transcription_sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def bind(read, queue_row, census_row):
    """(basis, why) for a read against the census row it claims, or (None, why-not)."""
    url_code = page_code(read["url"])
    census_code = (census_row.get("property_code") or "").lower()
    if url_code and census_code:
        # A code the census carries decides both ways: the same code is the building, a different code is another.
        if url_code == census_code:
            return "PROPERTY_CODE", "the page's own property code %r is the census row's" % url_code
        return None, "the page's property code %r is not this row's %r" % (url_code, census_code)
    z_page, z_census = page_postal(read.get("address_on_page")), (census_row.get("postal_code") or "")[:5]
    names_agree = same_name(read.get("name_on_page"), census_row.get("canonical_name"))
    if names_agree and z_page and z_page == z_census:
        return "BRAND_PAGE_NAME_AND_POSTAL", ("the brand's own page names this one property (%r) at postal code %s"
                                              % (read["name_on_page"], z_page))
    st_page = page_street(read.get("address_on_page"))
    street_agrees = bool(st_page) and address_key(canonical_street(st_page), "") == \
        address_key(canonical_street(census_row.get("street") or ""), "")
    if street_agrees and z_page and z_page == z_census:
        return "FULL_STREET_AND_POSTAL", "the page's own street and postal code are the census row's"
    # A brand page that prints no postal code of its own (Best Western prints "City, Florida United States"):
    # its own NAME and its own FULL STREET together are the exact premises. A house number alone still never binds.
    if names_agree and street_agrees and not z_page:
        return "BRAND_PAGE_NAME_AND_FULL_STREET", ("the page states no postal code; its own name (%r) and its own "
                                                   "full street (%r) are the census row's" % (read["name_on_page"], st_page))
    # Still no postal code on the page and the heading is a marketing variant: the page's own FULL STREET plus its
    # own CITY is the premises. House number alone never reaches here -- address_key carries the street words too.
    city_page = page_city(read.get("address_on_page"))
    city_census = " ".join((census_row.get("city") or "").lower().split())
    if street_agrees and not z_page and city_page and city_census and city_page == city_census:
        return "BRAND_PAGE_FULL_STREET_AND_CITY", ("the page states no postal code; its own full street (%r) and "
                                                   "city (%r) are the census row's" % (st_page, city_page))
    return None, ("no exact-premises binding: page code %r vs census %r; page name %r; page address %r vs census %r"
                  % (url_code, census_code, read.get("name_on_page"), read.get("address_on_page"),
                     (census_row.get("street") or "") + " " + z_census))


def build(reads_paths):
    census = {h["identity_key"]: h for h in _load(CENSUS)["hotels"]}
    clean = {r["identity_key"]: r for r in _load(CLEAN)["rows"]}
    routing = {r["identity_key"]: r for r in _load(ROUTING)["routes"]}
    # The queue is FROZEN from the sealed base (miami_fl_browser_queue_002.json). Re-deriving it from the live
    # adjudication would shrink it as this pass resolves rows -- the cohort must stay the one SOURCE-READY-001 left.
    frozen = _load(QUEUE)["rows"]
    queue_by_i = [r for r in frozen if r["identity_key"] in census]
    dropped = [r["identity_key"] for r in frozen if r["identity_key"] not in census]
    reads = []
    for p in reads_paths:
        reads.extend(_load(p, []) or [])
    # A read is matched to the census row it BINDS to, never to a queue position: the queue is re-derived from the
    # current census, and an exact-premises binding is the only thing allowed to pair a page with an identity.
    read_for_key, unmatched_reads = {}, []
    for read in reads:
        if read.get("outcome") != "READ":
            hits = [q for q in queue_by_i if bind(read, q, census.get(q["identity_key"]) or {})[0]]
        else:
            hits = [q for q in queue_by_i if bind(read, q, census.get(q["identity_key"]) or {})[0]]
        if len(hits) == 1:
            read_for_key.setdefault(hits[0]["identity_key"], read)
        elif len(hits) > 1:
            for h in hits:
                read_for_key.setdefault(h["identity_key"], dict(read, outcome="SHARED_PAGE_CENSUS_DUPLICATE",
                                                                shared_with=[x["identity_key"] for x in hits]))
        else:
            unmatched_reads.append(OrderedDict([("url", read.get("url")), ("name_on_page", read.get("name_on_page")),
                                                ("address_on_page", read.get("address_on_page")),
                                                ("outcome", read.get("outcome"))]))

    rows, unbound, counts = [], [], Counter()
    bound_pages = {}
    for i, q in enumerate(queue_by_i):
        key = q["identity_key"]
        crow = census.get(key) or {}
        read = read_for_key.get(key)
        fam = q.get("family") or (routing.get(key, {}).get("brand_family") or "OTHER")
        base = OrderedDict([
            ("identity_key", key), ("canonical_name", q["canonical_name"]), ("family", fam),
            ("corridor", q.get("corridor", "")), ("queue_index", i),
            ("requested_url", q.get("url") or (routing.get(key, {}) or {}).get("url", "")),
            ("capture_lane", CAPTURE_LANE), ("work_order", WORK_ORDER),
            ("prior_disposition", "BROWSER_CAPTURE_NEEDED"),
            ("prior_hold_reason", q.get("hold_reason", "")),
        ])
        if read is None:
            base["outcome"] = "NOT_ATTEMPTED"
            counts["NOT_ATTEMPTED"] += 1
            rows.append(base)
            continue
        base["final_url"] = read.get("final_url") or read["url"]
        base["source_domain"] = re.sub(r"^https?://(www\.)?", "", read["url"]).split("/")[0]
        base["captured_at"] = read.get("captured_at") or read.get("captured_at_approx_utc") or ""
        base["outcome"] = read["outcome"]
        base["name_on_page"] = read.get("name_on_page", "")
        base["address_on_page"] = read.get("address_on_page", "")
        base["policy_nodes"] = read.get("nodes") or []
        if read.get("note"):
            base["note"] = read["note"]
        if read["outcome"] not in ("READ",):
            counts[read["outcome"]] += 1
            rows.append(base)
            continue
        basis, why = bind(read, q, crow)
        base["binding"] = basis or "NONE"
        base["binding_note"] = why
        if basis is None:
            counts["BOUND_NONE"] += 1
            unbound.append(OrderedDict([("identity_key", key), ("why", why)]))
            base["outcome"] = "IDENTITY_NOT_BOUND"
            rows.append(base)
            continue
        quote = " ".join(x.strip() for x in base["policy_nodes"] if x and x.strip())
        base["operative_quote"] = quote
        base["byte_length_of_quote"] = len(quote.encode("utf-8"))
        base["transcription_sha256"] = transcription_sha(OrderedDict([
            ("url", base["final_url"]), ("name", base["name_on_page"]), ("address", base["address_on_page"]),
            ("nodes", base["policy_nodes"])]))
        bound_pages.setdefault((base["final_url"], base["address_on_page"]), []).append(key)
        counts["BOUND"] += 1
        rows.append(base)

    # A page bound to more than one census row publishes for none of them.
    multi = {k: v for k, v in bound_pages.items() if len(v) > 1}
    shared = {key for keys in multi.values() for key in keys}
    for r in rows:
        if r.get("identity_key") in shared and r.get("outcome") == "READ":
            r["outcome"] = "SHARED_PAGE_CENSUS_DUPLICATE"
            r["binding_note"] += ("; this page bound %d census rows (%s) -- a duplicate identity, so no row "
                                  "publishes from it" % (len(multi[(r["final_url"], r["address_on_page"])]),
                                                         ", ".join(sorted(multi[(r["final_url"], r["address_on_page"])]))))
            counts["BOUND"] -= 1
            counts["SHARED_PAGE_CENSUS_DUPLICATE"] += 1

    os.makedirs(RAW, exist_ok=True)
    with open(OUT_JSONL, "w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    report = OrderedDict([
        ("schema", "ptf-browser-closure/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("lane", CAPTURE_LANE),
        ("authorization", "the founder granted the browser extension read access for marriott.com, hilton.com, "
                          "hyatt.com and bestwestern.com; no bypass of any challenge, CAPTCHA or authentication"),
        ("queue_total_frozen", len(frozen)),
        ("queue_total", len(queue_by_i)),
        ("queue_rows_merged_away_since_the_base", dropped),
        ("queue_by_family", OrderedDict(sorted(Counter(r.get("family") or "OTHER" for r in queue_by_i).items()))),
        ("outcomes", OrderedDict(sorted(Counter(r["outcome"] for r in rows).items()))),
        ("bindings", OrderedDict(sorted(Counter(r.get("binding", "-") for r in rows if r.get("binding")).items()))),
        ("unbound", unbound),
        ("reads_that_bound_no_queue_row", unmatched_reads),
        ("shared_page_census_duplicates", OrderedDict((json.dumps(list(k)), v) for k, v in multi.items())),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("firecrawl_credits_used", 0),
        ("raw_captures", os.path.relpath(OUT_JSONL, _DASH).replace("\\", "/")),
    ])
    with open(OUT_REPORT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    return report


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--reads", action="append", required=True, help="a JSON file of this order's browser reads")
    args = ap.parse_args(argv)
    rep = build(args.reads)
    print("queue", rep["queue_total"], dict(rep["queue_by_family"]))
    print("outcomes", dict(rep["outcomes"]))
    print("bindings", dict(rep["bindings"]))
    print("unbound", len(rep["unbound"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
