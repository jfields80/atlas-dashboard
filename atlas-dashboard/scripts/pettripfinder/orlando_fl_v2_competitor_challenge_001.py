"""PTF-ORLANDO-FL-HARDENED-V2-SOURCE-READY-001 -- Phase 10: the BringFido competitor challenge set.

BringFido is IDENTITY DISCOVERY / GAP CHALLENGE ONLY. Never pet-policy authority: no fee, weight, count or "pet
friendly" claim BringFido prints is read, stored or used. Only the listing NAME is kept.

HOW THE SET WAS OBTAINED
------------------------
BringFido's Orlando city page (https://www.bringfido.com/lodging/city/orlando_fl_us/, "There are 417 pet friendly
hotels in Orlando", 2026-09-15) was read in the supported attended browser lane: navigate to ?page=1..20 (page 21
answered 404), scroll the lazily rendered card grid, and read each card's name heading from the accessibility tree.
No page script was run and nothing was relayed. The accessibility reader returns at most twenty headings per query and
the grid renders lazily, so a few cards on the rental-heavy tail pages (19, 20) were not captured; this is recorded
as a coverage caveat, not hidden. BringFido files Kissimmee, Lake Buena Vista, Celebration and Davenport under their
own city pages; those were not enumerated by this order.

The raw transcription is ``data/orlando_fl_v2/bringfido_pages.txt`` (gitignored); this report commits every name with
its page number and a first-pass lead class (a HOTEL_LEAD needs first-party verification; a RENTAL_LISTING is a
vacation-rental / condo / home / Airbnb card that could never be a hotel identity).

Output:
  launch_packages/pettripfinder/markets/reports/orlando_fl_v2_competitor_challenge_001.json
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
RAW = os.path.join(_DASH, "data", "orlando_fl_v2", "bringfido_pages.txt")
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                   "orlando_fl_v2_competitor_challenge_001.json")
WORK_ORDER = "PTF-ORLANDO-FL-HARDENED-V2-SOURCE-READY-001"
SOURCE = "https://www.bringfido.com/lodging/city/orlando_fl_us/"

_HOTEL = re.compile(
    r"\b(hotel|inn|suites|resort|lodge|motel|marriott|hilton|hyatt|ihg|wyndham|rosen|loews|hampton|homewood|home2|"
    r"embassy|doubletree|aloft|element|residence inn|towneplace|springhill|fairfield|sheraton|la quinta|baymont|"
    r"days inn|super 8|clarion|comfort|quality|country inn|sonesta|extended stay|woodspring|stayable|red roof|"
    r"motel 6|oyo|spark|tru by|signia|waldorf|ritz|jw|autograph|tribute|ascend|everhome|drury|staybridge|"
    r"candlewood|crowne plaza|holiday inn|caribe royale|delaney|beauden|castle|avanti|westgate|floridays|"
    r"legacy vacation|villatel|sunstyle|spot x|b&b hotel|garnet|countryside|lake nona wave|landy|daskk|koa)\b", re.I)
_RENTAL = re.compile(
    r"(\bcondo\b|\bhome\b|\bhouse\b|townho|\bstudio\b|\bbedroom\b|\b\dbr\b|\d/\d|\bvilla\b|cottage|apartment|airbnb|"
    r"vrbo|\bcabin\b|retreat|\bvc-?\d|#\d|\b\d{3,4}\b$|\blakes resort - |palace resort|westgate lakes resort -|"
    r"lakefront|lakeview|tiny house|guest house|\bestate\b|getaway|discount|staycation|\bspot\b$|compound|"
    r"\bkoa\b|vista cay (?!resort by)|\bthe (swan|ritz|universal|bermuda|ivanhoe)\b|oasis|adventure awaits|"
    r"family fun|look no further|dream vacation|sun chaser|tropical treasure|sea escape|vista dreams|ana's joy|"
    r"nora's|hole in one|hemispheres|international sights|pompeii|waterside stay|eastpark|mills |"
    r"pineapple suite|pet friendly in orlando|orlando hotel by parks|minutes to|near attractions|"
    r"enjoy the free breakfast|apalone|units minutes)", re.I)


#: Chain names that decide the lead class before any rental word does ("Hyatt House", "The Ritz-Carlton").
_STRONG_HOTEL = re.compile(r"\b(hyatt (house|place|regency)|ritz-carlton|renaissance|marriott|hilton|by ihg|by wyndham)\b", re.I)


def classify(name):
    if _STRONG_HOTEL.search(name):
        return "HOTEL_LEAD"
    if re.search(r"\d\s*bed\b|\bbed lakes\b", name, re.I):
        return "RENTAL_LISTING"
    if _RENTAL.search(name):
        return "RENTAL_LISTING"
    if _HOTEL.search(name):
        return "HOTEL_LEAD"
    return "RENTAL_LISTING"


def build():
    raw = open(RAW, encoding="utf-8-sig").read()
    page, leads = 0, []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"#page (\d+)", line)
        if m:
            page = int(m.group(1))
            continue
        if line.startswith("#"):
            continue
        leads.append(OrderedDict([("name", line), ("page", page), ("source_url", SOURCE + ("?page=%d" % page if page > 1 else "")),
                                  ("lead_class", classify(line))]))
    seen, uniq, dups = set(), [], 0
    for l in leads:
        k = re.sub(r"[^a-z0-9]+", " ", l["name"].lower()).strip()
        if k in seen:
            dups += 1
            continue
        seen.add(k)
        uniq.append(l)
    hotels = [l for l in uniq if l["lead_class"] == "HOTEL_LEAD"]
    return OrderedDict([
        ("schema", "ptf-competitor-challenge/1.0"), ("work_order", WORK_ORDER), ("market_id", "orlando-fl"),
        ("competitor", "BringFido"), ("source", SOURCE), ("observed_at", "2026-09-15"),
        ("competitor_stated_total", 417),
        ("capture_lane", "supported attended browser: navigate + accessibility-tree read of card name headings; no page script"),
        ("raw_transcription_sha256", hashlib.sha256(raw.encode("utf-8")).hexdigest()),
        ("never_policy_authority",
         "Names only. A competitor lead proposes an identity and is reconciled against the census; its pet claims are "
         "never read and can never publish a policy."),
        ("coverage_caveat",
         "20 result pages (page 21 answered 404). The accessibility reader returned 16-20 of the 20 cards on a few "
         "rental-dominated pages, so the captured raw count is below the competitor's stated 417; every uncaptured card "
         "sat among vacation-rental listings. Kissimmee, Lake Buena Vista, Celebration and Davenport city pages were not "
         "enumerated."),
        ("raw_captured", len(leads)), ("duplicates_removed", dups), ("normalized_unique", len(uniq)),
        ("by_lead_class", OrderedDict(sorted(Counter(l["lead_class"] for l in uniq).items()))),
        ("hotel_leads", len(hotels)),
        ("leads", hotels),
        ("rental_listings", [l["name"] for l in uniq if l["lead_class"] == "RENTAL_LISTING"]),
    ])


def main():
    rep = build()
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rep, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("raw", rep["raw_captured"], "unique", rep["normalized_unique"], dict(rep["by_lead_class"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
