"""PTF-ORLANDO-FL-HARDENED-V2-SOURCE-READY-001 -- Phase 12G: independents' own policy / FAQ / pet pages (plain client).

A property's own home page often says nothing about pets while its own "Pet Policy", "Dog Policy", "Policies" or
"FAQ" page does. For every admitted census identity routed to an INDEPENDENT first-party site (not a brand host), this
lane:

  1. fetches the route (following redirects -- a bureau link can be a click-tracker that lands on the hotel's own site);
  2. binds the site to the identity: the census street's house number AND postal code (or the census phone) must
     appear on the site's own home or policy page -- a name never binds;
  3. follows at most three same-site links whose text or path names pets, dogs, policies or an FAQ;
  4. copies, verbatim, every sentence on those pages that names pets or dogs (bounded, deduplicated).

The sentences are the candidate quote; facts are read by the shared reader in orlando_fl_v2_policy_reads_001 and
judged by the first-party gate and the negation guard in the clean authority. Documents persisted by sha256 under
data/acquisition/orlando_fl_v2_policy_pages_001/.

Output:
  launch_packages/pettripfinder/markets/staging/orlando-fl/raw_captures/policy_pages_rows.json
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

from scripts.pettripfinder import orlando_fl_v2_brand_inventory_001 as B  # noqa: E402

B.DOCS = os.path.join(_DASH, "data", "acquisition", "orlando_fl_v2_policy_pages_001")
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
ROUTING = os.path.join(PKG, "markets", "reports", "orlando_fl_v2_routing_001.json")
OUT = os.path.join(PKG, "markets", "staging", "orlando-fl", "raw_captures", "policy_pages_rows.json")
BRAND_HOSTS = re.compile(r"(marriott|hilton|ihg|holidayinn|choicehotels|wyndhamhotels|redroof|extendedstayamerica|"
                         r"bestwestern|hyatt|sonesta|motel6|radissonhotels|druryhotels|omnihotels|loewshotels|woodspring|"
                         r"universalorlando|disney\.go|intownsuites|westgateresorts|facebook|instagram|google|tripadvisor|"
                         r"booking\.com|expedia|h-rez\.com)", re.I)
# minified sites write an unquoted href (the Rosen footers' "Dog Policy" link); both spellings are read
_LINK = re.compile(r'<a[^>]+href=(?:"([^"#]+)"|([^\s">#]+))[^>]*>(.*?)</a>', re.I | re.S)
_WANT = re.compile(r"\b(pet|pets|dog|dogs|polic(y|ies)|faq|frequently asked|rules)\b", re.I)
_SENT = re.compile(r"[^.!?]{0,240}\b(pets?|dogs?|animals?)\b[^.!?]{0,240}[.!?]", re.I)


def _decode(body):
    t = body.decode("utf-8", "replace")
    return body.decode("cp1252", "replace") if "�" in t else t


def _text(doc):
    t = re.sub(r"(?s)<script.*?</script>|<style.*?</style>|<noscript.*?</noscript>", " ", doc)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", t)).split())


def _digits(s):
    return re.sub(r"\D", "", s or "")[-10:]


def main():
    routing = json.load(open(ROUTING, encoding="utf-8"))
    targets = [r for r in routing["routes"] + routing.get("identity_fill_routes", [])
               if r.get("url") and not BRAND_HOSTS.search(r["url"]) and r.get("street")]
    st = B.Stats()
    rows, seen = [], set()
    for t in targets:
        if t["identity_key"] in seen:
            continue
        seen.add(t["identity_key"])
        time.sleep(0.6)
        row, body = B.fetch(t["url"], st, timeout=25)
        rec = OrderedDict([("identity_key", t["identity_key"]), ("name", t["canonical_name"]), ("u", t["url"]),
                           ("final_url", row["final_url"]), ("s", row["status"]), ("h", row["sha256"]), ("b", row["bytes"]),
                           ("street", t["street"]), ("postal", t["postal_code"]), ("phone", t.get("phone")),
                           ("pages", []), ("bound", False), ("sentences", [])])
        if row["status"] != 200 or not body:
            rows.append(rec)
            continue
        home = _decode(body)
        final = row["final_url"] or t["url"]
        host = urllib.parse.urlparse(final).netloc.lower().replace("www.", "")
        if BRAND_HOSTS.search(host):
            rec["note"] = "the route lands on a brand or third-party host; read by that family's lane, not here"
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
            time.sleep(0.6)
            prow, pbody = B.fetch(u, st, timeout=25)
            if prow["status"] == 200 and pbody:
                texts.append((prow["final_url"] or u, prow["sha256"], prow["bytes"], _text(_decode(pbody))))
        num = (t["street"].split() or [""])[0]
        allt = " ".join(x[3] for x in texts)
        z = (t["postal_code"] or "")[:5]
        # the site's own structured address counts as its page (the Rosen Inn sites print the address only in their
        # hotel JSON-LD): streetAddress must open with the census house number and postalCode must equal the ZIP
        ld_streets = re.findall(r'"streetAddress"\s*:\s*"([^"]+)"', home)
        ld_zips = [x[:5] for x in re.findall(r'"postalCode"\s*:\s*"([^"]+)"', home)]
        rec["bound"] = bool((num and re.search(r"\b%s\b" % re.escape(num), allt) and z and z in allt)
                            or (_digits(t.get("phone")) and _digits(t.get("phone")) in re.sub(r"\D", "", allt))
                            or (num and z and z in ld_zips and any(s.split()[:1] == [num] for s in ld_streets)))
        for url, sha, nbytes, txt in texts:
            sents = []
            for m in _SENT.finditer(txt):
                s = m.group(0).strip()
                if re.search(r"service animal|emotional support", s, re.I) and not re.search(r"\bpets?\b|\bdogs?\b", s, re.I):
                    continue
                if s not in sents and len(sents) < 8:
                    sents.append(s)
            rec["pages"].append(OrderedDict([("url", url), ("sha256", sha), ("bytes", nbytes), ("pet_sentences", sents)]))
        rows.append(rec)
        print(rec["s"], rec["bound"], t["canonical_name"][:40], sum(len(p["pet_sentences"]) for p in rec["pages"]), flush=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(OrderedDict([("free_http_requests", st.requests), ("rows", rows)]), fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("targets", len(rows), "bound", sum(1 for r in rows if r["bound"]),
          "with pet sentences", sum(1 for r in rows if any(p["pet_sentences"] for p in r["pages"])))


if __name__ == "__main__":
    main()
