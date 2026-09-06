"""PTF-FORT-WAYNE-IN-NEW-MARKET-001 -- Phase 6 (competitor directory, LEAD LANE).

A competitor pet-travel directory is a DISCOVERY LEAD SOURCE and nothing else.
It is never policy authority, and a row here cannot enter Fort Wayne authority
without first-party identity confirmation. This lane exists to answer one
question: does a competitor name a Fort Wayne lodging identity that our own
free lanes did not find?

Two measured traps, both recorded rather than assumed:

1. THE HEADLINE COUNT IS NOT THE SERVED COHORT. The Fort Wayne city page says
   "41 pet friendly hotels" in its own copy while the ItemList it actually
   serves a plain client carries 19. Both numbers are recorded. The served
   cohort is the only thing this report treats as leads; the headline is
   recorded as the competitor's own claim and is not reconciled against.

2. A CITY PAGE IS NOT A CITY. The New Haven page serves mostly Fort Wayne rows,
   plus Auburn rows -- Auburn is forty kilometres north and outside this market
   -- plus vacation rentals that are not the hotel category at all. Every lead
   is therefore carried with the page that served it, and geography is decided
   downstream by the market's own membership test, never by which city page a
   competitor filed a row under.

robots.txt is read and the lodging city paths it allows are the only ones
fetched. Review paths, booking paths and user paths are all Disallow and are
not touched. No policy text is extracted, quoted or stored: a competitor's
policy snippet is at most a targeting hint, and this order does not need one.

Output:
  launch_packages/pettripfinder/markets/reports/fort_wayne_in_competitor_leads_001.json
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-FORT-WAYNE-IN-NEW-MARKET-001"
MARKET_ID = "fort-wayne-in"
SCHEMA = "ptf-competitor-lead-harvest/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
SPACING_SECONDS = 2.5

ROBOTS = "https://www.bringfido.com/robots.txt"
#: Only the two city pages that name this market's own municipalities.
PAGES = OrderedDict([
    ("fort_wayne_in_us", "https://www.bringfido.com/lodging/city/fort_wayne_in_us/"),
    ("new_haven_in_us", "https://www.bringfido.com/lodging/city/new_haven_in_us/"),
])


def get(url, timeout=30):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "text/html,*/*", "Accept-Encoding": "gzip",
        "Accept-Language": "en-US,en;q=0.9"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
            if r.headers.get("Content-Encoding") == "gzip" or data[:2] == b"\x1f\x8b":
                try:
                    data = gzip.GzipFile(fileobj=io.BytesIO(data)).read()
                except Exception:  # noqa: BLE001
                    pass
            return r.status, r.geturl(), data
    except urllib.error.HTTPError as e:
        return e.code, url, b""
    except Exception as e:  # noqa: BLE001
        return "ERR:" + type(e).__name__, url, b""


def _disallowed(robots_txt, agent="*"):
    """The Disallow rules of the group that applies to ``agent``, and only that
    group.

    Reading every Disallow line in the file is wrong and this lane proved it:
    bringfido.com grants ``User-agent: *`` a short deny list and then denies
    ``/`` outright to five named crawlers (sleepbot, aranet, linkupbot,
    bytespider, meta-externalagent). Pooling the groups makes ``/`` look
    universally forbidden and refuses a page the site actually allows. Grouping
    is what robots.txt means; a rule addressed to another agent is not a rule
    addressed to us.
    """
    groups, agents, rules, in_group = [], [], [], False
    for raw in robots_txt.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        field, _, value = line.partition(":")
        field = field.strip().lower()
        value = value.strip()
        if field == "user-agent":
            if in_group:                       # a new group starts here
                groups.append((agents, rules))
                agents, rules, in_group = [], [], False
            agents.append(value.lower())
        elif field == "disallow":
            in_group = True
            rules.append(value)
    if agents or rules:
        groups.append((agents, rules))
    for names, group_rules in groups:
        if agent.lower() in names:
            return tuple(sorted(set(group_rules)))
    return ()


def _item_list(html):
    for block in re.findall(
            r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html, re.I | re.S):
        try:
            data = json.loads(block.strip())
        except Exception:  # noqa: BLE001
            continue
        if isinstance(data, dict) and data.get("@type") == "ItemList":
            return data.get("itemListElement") or []
    return []


def _headline(html):
    """The count the page prints in its own copy, if it prints one."""
    m = re.search(r"(\d[\d,]*)\s+pet friendly hotels", html, re.I)
    return int(m.group(1).replace(",", "")) if m else None


#: A served row that is plainly not the hotel category. Recorded, not silently
#: dropped: the competitor counted them, and that is part of why its headline
#: and its list disagree.
_NON_HOTEL_RE = re.compile(r"\b(vrbo|airbnb|rentals?|home|cabin|cottage|apartment|"
                           r"bedroom|campground|rv park|tudor|craftsman)\b", re.I)


def build(args):
    stats = {"requests": 0}
    st, _, body = get(ROBOTS)
    stats["requests"] += 1
    robots_txt = body.decode("utf-8", "replace") if body else ""
    disallowed = _disallowed(robots_txt)
    for page_url in PAGES.values():
        path = page_url.split("bringfido.com", 1)[-1]
        for rule in disallowed:
            bare = rule.rstrip("*")
            if bare and not bare.startswith("*") and path.startswith(bare):
                raise SystemExit("robots.txt disallows %s (%r)" % (path, rule))

    pages = OrderedDict()
    leads = []
    for key, url in PAGES.items():
        time.sleep(SPACING_SECONDS)
        st, final, body = get(url)
        stats["requests"] += 1
        html = body.decode("utf-8", "replace") if body else ""
        items = _item_list(html)
        rows = []
        for it in items:
            hotel = it.get("item") or {}
            addr = hotel.get("address") or {}
            if not isinstance(addr, dict):
                addr = {}
            name = str(hotel.get("name") or "").strip()
            if not name:
                continue
            rows.append(OrderedDict([
                ("name", name),
                ("street", str(addr.get("streetAddress") or "").strip()),
                ("city", str(addr.get("addressLocality") or "").strip()),
                ("postal_code", str(addr.get("postalCode") or "").strip()[:5]),
                ("shape", "NON_HOTEL_SHAPE" if _NON_HOTEL_RE.search(name)
                 else "HOTEL_SHAPE"),
                ("served_by_page", key),
            ]))
        pages[key] = OrderedDict([
            ("url", url), ("status", st),
            ("page_sha256", hashlib.sha256(body).hexdigest() if body else None),
            ("headline_count_claimed", _headline(html)),
            ("item_list_served", len(rows)),
            ("fetched_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        ])
        leads.extend(rows)
        print(key, st, "headline", pages[key]["headline_count_claimed"],
              "served", len(rows), flush=True)

    # One lead per distinct name; a row served by both city pages is one lead.
    unique = OrderedDict()
    for row in leads:
        prior = unique.get(row["name"].lower())
        if prior is None:
            row = OrderedDict(row)
            row["served_by_pages"] = [row.pop("served_by_page")]
            unique[row["name"].lower()] = row
        elif row["served_by_page"] not in prior["served_by_pages"]:
            prior["served_by_pages"].append(row["served_by_page"])
    unique_rows = sorted(unique.values(), key=lambda r: r["name"].lower())

    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER),
        ("phase", "6 -- competitor directory challenge, LEAD LANE ONLY"),
        ("market_id", MARKET_ID), ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("competitor", "BringFido (bringfido.com)"),
        ("what_this_is",
         "Competitor city pages read as DISCOVERY LEADS. Never policy authority: no "
         "policy text is extracted or stored, and no row here may enter Fort Wayne "
         "authority without first-party identity confirmation. The headline count a "
         "page prints and the ItemList it actually serves are recorded separately "
         "because they disagree. Which city page served a row is recorded but decides "
         "nothing: the New Haven page serves Fort Wayne rows, Auburn rows from outside "
         "this market, and vacation rentals outside the hotel category."),
        ("policy_evidence_extracted", False),
        ("robots_disallowed_paths", list(disallowed)),
        ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("free_http_requests", stats["requests"]),
        ("pages", pages),
        ("counts", OrderedDict([
            ("headline_claimed_total",
             sum(p["headline_count_claimed"] or 0 for p in pages.values())),
            ("served_rows_total", len(leads)),
            ("unique_leads", len(unique_rows)),
            ("by_shape", OrderedDict(sorted(Counter(r["shape"] for r in unique_rows).items()))),
        ])),
        ("leads", unique_rows),
    ])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(
        REPORTS, "fort_wayne_in_competitor_leads_001.json"))
    args = ap.parse_args(argv)
    rep = build(args)
    with open(args.out, "wb") as fh:
        fh.write((json.dumps(rep, indent=1, ensure_ascii=False, default=str) + "\n").encode("utf-8"))
    print("written", os.path.relpath(args.out, _DASH))
    print(json.dumps(rep["counts"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
