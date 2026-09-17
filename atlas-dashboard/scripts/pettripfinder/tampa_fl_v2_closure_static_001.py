"""PTF-TAMPA-FL-V2-COVERAGE-CLOSURE-002 -- Phase 4/6/9 static acquisition
over the routes the Places lookup lane (tampa_fl_v2_closure_places_lookup_001)
discovered for previously-ROUTING_HOLD independents.

Same binding and sentence-extraction discipline as the source-ready build's
own tampa_fl_v2_policy_pages_lane_001: a site binds to a census identity only
on house number + postal code, phone digits, or JSON-LD street/postal -- never
on name alone. Every sentence naming pets/dogs/animals is copied verbatim;
classification (accept/refuse/held) is left to clean_authority's shared gate
and negation guard, never decided here.

Output:
  launch_packages/pettripfinder/markets/staging/tampa-fl/raw_captures/closure_static_rows.json
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
import time
import urllib.parse
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import tampa_fl_v2_brand_inventory_001 as B  # noqa: E402

B.DOCS = os.path.join(_DASH, "data", "acquisition", "tampa_fl_v2_closure_static_001")
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
WORKLIST = os.path.join(REPORTS, "tampa_fl_v2_closure_worklist_001.json")
PLACES = os.path.join(REPORTS, "tampa_fl_v2_closure_places_lookup_001.json")
OUT = os.path.join(PKG, "markets", "staging", "tampa-fl", "raw_captures", "closure_static_rows.json")

BRAND_HOSTS = re.compile(r"(marriott|hilton|ihg|holidayinn|choicehotels|wyndhamhotels|redroof|extendedstayamerica|"
                         r"bestwestern|hyatt|sonesta|motel6|radissonhotels|druryhotels|omnihotels|loewshotels|woodspring|"
                         r"intownsuites|facebook|instagram|google|tripadvisor|yelp|"
                         r"booking\.com|expedia|h-rez\.com|airbnb|vrbo)", re.I)
_LINK = re.compile(r'<a[^>]+href=(?:"([^"#]+)"|([^\s">#]+))[^>]*>(.*?)</a>', re.I | re.S)
_WANT = re.compile(r"\b(pet|pets|dog|dogs|polic(y|ies)|faq|frequently asked|rules|amenit)\b", re.I)
_SENT = re.compile(r"[^.!?]{0,240}\b(pets?|dogs?|animals?)\b[^.!?]{0,240}[.!?]", re.I)


def _decode(body):
    t = body.decode("utf-8", "replace")
    return body.decode("cp1252", "replace") if "�" in t else t


def _text(doc):
    t = re.sub(r"(?s)<script.*?</script>|<style.*?</style>|<noscript.*?</noscript>", " ", doc)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", t)).split())


def _digits(s):
    return re.sub(r"\D", "", s or "")[-10:]


def _house_number(street):
    m = re.match(r"\s*(\d+)", street or "")
    return m.group(1) if m else ""


def main():
    worklist = json.load(open(WORKLIST, encoding="utf-8"))
    by_key = {r["property_id"]: r for r in worklist["items"]}
    places = json.load(open(PLACES, encoding="utf-8"))
    targets = [r for r in places["rows"] if r.get("matched") and r.get("website_uri")]

    st = B.Stats()
    rows = []
    for p in targets:
        key = p["identity_key"]
        t = by_key.get(key)
        if not t:
            continue
        url = p["website_uri"]
        if BRAND_HOSTS.search(url):
            rows.append(OrderedDict([("identity_key", key), ("u", url), ("bound", False),
                                     ("note", "brand/OTA/social host, not read here")]))
            continue
        time.sleep(0.4)
        row, body = B.fetch(url, st, timeout=20)
        rec = OrderedDict([("identity_key", key), ("name", t["canonical_name"]), ("u", url),
                           ("final_url", row["final_url"]), ("s", row["status"]), ("h", row["sha256"]),
                           ("b", row["bytes"]), ("street", t["street"]), ("postal", t["postal_code"]),
                           ("phone", t.get("phone")), ("pages", []), ("bound", False)])
        if row["status"] != 200 or not body:
            rec["error"] = row.get("error")
            rows.append(rec)
            continue
        home = _decode(body)
        final = row["final_url"] or url
        host = urllib.parse.urlparse(final).netloc.lower().replace("www.", "")
        if BRAND_HOSTS.search(host):
            rec["note"] = "redirected to a brand/OTA host; not read here"
            rows.append(rec)
            continue
        texts = [(final, row["sha256"], row["bytes"], _text(home))]
        links = []
        for quoted, bare, label in _LINK.findall(home):
            href = quoted or bare
            lab = _text(label)
            absu = urllib.parse.urljoin(final, href)
            h2 = urllib.parse.urlparse(absu).netloc.lower().replace("www.", "")
            if h2 != host or absu.rstrip("/") == final.rstrip("/"):
                continue
            if _WANT.search(lab) or _WANT.search(urllib.parse.urlparse(absu).path.replace("-", " ").replace("/", " ")):
                if absu not in links:
                    links.append(absu)
        links.sort(key=lambda u: (0 if re.search(r"pet|dog", u, re.I) else 1 if re.search(r"polic", u, re.I) else 2, u))
        for u in links[:3]:
            time.sleep(0.4)
            prow, pbody = B.fetch(u, st, timeout=20)
            if prow["status"] == 200 and pbody:
                texts.append((prow["final_url"] or u, prow["sha256"], prow["bytes"], _text(_decode(pbody))))
        num = _house_number(t["street"])
        allt = " ".join(x[3] for x in texts)
        z = (t["postal_code"] or "")[:5]
        ld_streets = re.findall(r'"streetAddress"\s*:\s*"([^"]+)"', home)
        ld_zips = [x[:5] for x in re.findall(r'"postalCode"\s*:\s*"([^"]+)"', home)]
        rec["bound"] = bool((num and re.search(r"\b%s\b" % re.escape(num), allt) and z and z in allt)
                            or (_digits(t.get("phone")) and _digits(t.get("phone")) in re.sub(r"\D", "", allt))
                            or (num and z and z in ld_zips and any((s.split() or [""])[0] == num for s in ld_streets)))
        for u2, sha, nbytes, txt in texts:
            sents = []
            for m in _SENT.finditer(txt):
                s = m.group(0).strip()
                if re.search(r"service animal|emotional support", s, re.I) and not re.search(r"\bpets?\b|\bdogs?\b", s, re.I):
                    continue
                if s not in sents and len(sents) < 8:
                    sents.append(s)
            rec["pages"].append(OrderedDict([("url", u2), ("sha256", sha), ("bytes", nbytes), ("pet_sentences", sents)]))
        rows.append(rec)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(OrderedDict([("free_http_requests", st.requests), ("rows", rows)]), fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("targets", len(rows), "bound", sum(1 for r in rows if r["bound"]),
          "with pet sentences", sum(1 for r in rows if any(p.get("pet_sentences") for p in r.get("pages", []))))


if __name__ == "__main__":
    main()
