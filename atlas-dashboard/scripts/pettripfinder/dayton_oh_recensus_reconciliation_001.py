"""PTF-DAYTON-OH-HARDENED-REVALIDATION-001 -- Phase 4 (reconciliation half).

Reconcile the free brand-directory harvest against Dayton's pinned census.

The harvest is a LEAD generator, not an admission mechanism. A directory URL
says a brand publishes a page whose path names an Ohio locality this market
lists; it does not say a hotel exists, where it is, or that the census is
missing it. So every candidate is classified against the census on evidence the
candidate itself carries -- its URL, and where the page served, its own
structured identity -- and anything that cannot be resolved on that evidence is
returned as NAME_ONLY_UNRESOLVED rather than guessed at.

Two properties of this particular harvest bound what it can conclude:

  * Marriott answered the sitemap walk but refused 244 of the 252 property
    pages selected for this market (HTTP 403). A refusal is a fetch outcome and
    proves nothing about the property, so those rows stay leads.
  * The pages that DID serve mostly carried no JSON-LD hotel node, so the
    harvest has a URL and a slug for them and no address, postal or telephone.

The consequence is stated rather than papered over: this pass CANNOT establish
TRUE_MISSING_IDENTITY for Dayton, and it does not claim to. It narrows 17,928
brand URLs to a reviewable set and says which of those the census already
explains.

Nothing is written to authority.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-DAYTON-OH-HARDENED-REVALIDATION-001"
MARKET_ID = "dayton-oh"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
HARVEST = os.path.join(REPORTS, "dayton_oh_brand_directory_harvest_001.json")


def read_json(p, d=None):
    if not os.path.exists(p):
        return d
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def norm_url(u):
    u = (u or "").lower().split("?")[0].rstrip("/")
    return re.sub(r"^https?://(www\.)?", "", u)


def tokens(s):
    return set(re.sub(r"[^a-z0-9 ]", " ", (s or "").lower()).split())


STOP = {"hotel", "hotels", "inn", "suites", "and", "the", "by", "of", "at", "oh", "ohio",
        "overview", "en", "us", "com", "www", "https", "extended", "stay"}


def slug_tokens(url):
    tail = norm_url(url).split("/")
    parts = [p for p in tail if p and p not in ("overview", "hoteldetail")]
    return tokens(" ".join(parts[-2:]).replace("-", " ")) - STOP


def build() -> OrderedDict:
    harvest = read_json(HARVEST)
    if harvest is None:
        raise SystemExit("harvest report not found: " + HARVEST)
    census = read_json(os.path.join(PKG, "identity_census", MARKET_ID + ".json"))["hotels"]
    census_urls = {norm_url(h.get("official_url")): h for h in census if h.get("official_url")}
    census_by_key = {h["identity_key"]: h for h in census}

    rows = []
    for c in harvest["candidates"]:
        if c["selected_by"] == "STATE_TOKEN_ONLY":
            continue
        page = c.get("page") or {}
        status = page.get("status")
        ident = page.get("identity") or {}
        nu = norm_url(c["url"])
        row = OrderedDict([
            ("family", c["family"]), ("url", c["url"]), ("selected_by", c["selected_by"]),
            ("locality_token", c.get("locality_token")), ("property_code", c.get("property_code")),
            ("page_status", status), ("page_sha256", page.get("page_sha256")),
            ("page_title", (page.get("title") or "")[:120]),
            ("soft_404_suspected", page.get("soft_404_suspected")),
            ("page_declared_identity", ident or None),
        ])
        hit = census_urls.get(nu)
        if hit is None:
            # a census row whose official_url differs only by locale segment
            for cu, h in census_urls.items():
                if cu.replace("/en-us/", "/").replace("/en_us/", "/") == nu.replace("/en-us/", "/").replace("/en_us/", "/"):
                    hit = h
                    break
        if hit is not None:
            row["classification"] = "EXACT_EXISTING"
            row["census_identity_key"] = hit["identity_key"]
            row["why"] = "this exact URL is already this identity's official_url in the pinned census"
            rows.append(row)
            continue
        if page.get("soft_404_suspected"):
            row["classification"] = "NAME_ONLY_UNRESOLVED"
            row["why"] = "the brand served a search/listing page, not a property page; the slug names no confirmed property"
            rows.append(row)
            continue
        if status == 403:
            row["classification"] = "NAME_ONLY_UNRESOLVED"
            row["why"] = "the brand refused the property page (HTTP 403). A refusal is a fetch outcome and proves nothing about the property"
            rows.append(row)
            continue
        # the page served: try a token overlap against census names
        st = slug_tokens(c["url"])
        best, best_n = None, 0
        for h in census:
            n = len(st & (tokens(h["canonical_name"]) - STOP))
            if n > best_n:
                best, best_n = h, n
        if best is not None and best_n >= 2:
            row["classification"] = "ALIAS_OF_EXISTING"
            row["census_identity_key"] = best["identity_key"]
            row["name_token_overlap"] = best_n
            row["why"] = ("the slug shares %d significant name tokens with a census identity. A NAME PROPOSES an "
                          "identity and never decides one: this is a review lead, and admitting it would require "
                          "the page's own address, postal or telephone, which it does not declare" % best_n)
        else:
            row["classification"] = "NAME_ONLY_UNRESOLVED"
            row["why"] = ("the page served but declares no address, postal or telephone of its own, and its slug "
                          "matches no census identity. Nothing here can confirm or deny a missing hotel")
        rows.append(row)

    counts = Counter(r["classification"] for r in rows)
    return OrderedDict([
        ("schema", "ptf-recensus-reconciliation/1.0"), ("work_order", WORK_ORDER),
        ("phase", "4 -- free recensus reconciliation"), ("market_id", MARKET_ID),
        ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("free_http_requests_in_harvest", harvest["free_http_requests"]),
        ("harvest_candidates_total", harvest["candidate_counts"]["total"]),
        ("candidates_scoped_to_this_market", len(rows)),
        ("page_status", harvest["candidate_counts"]["page_status"]),
        ("classification_counts", OrderedDict(sorted(counts.items()))),
        ("true_missing_identities", 0),
        ("census_change_proposed", 0),
        ("what_this_can_and_cannot_conclude", OrderedDict([
            ("can", "it narrows 17,928 harvested brand URLs to %d that name this market's geography, and says which the pinned census already explains" % len(rows)),
            ("cannot", "it cannot establish TRUE_MISSING_IDENTITY. Marriott refused 244 of its %d selected property pages, and most pages that did serve declare no address, postal or telephone, so no candidate reached the evidence bar an admission requires." % sum(1 for r in rows if r["family"] == "MARRIOTT")),
            ("consequence", "Dayton's 129-row census is carried forward as PINNED AND UNCHALLENGED, not as confirmed complete. A completed recensus is the first item of the next order."),
        ])),
        ("rows", rows),
    ])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPORTS, "dayton_oh_recensus_reconciliation_001.json"))
    args = ap.parse_args(argv)
    rep = build()
    with open(args.out, "wb") as fh:
        fh.write((json.dumps(rep, indent=1, ensure_ascii=False, default=str) + "\n").encode("utf-8"))
    print("written", os.path.relpath(args.out, _DASH))
    print("scoped candidates:", rep["candidates_scoped_to_this_market"])
    print("classification:", json.dumps(rep["classification_counts"]))
    print("TRUE_MISSING_IDENTITY:", rep["true_missing_identities"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
