"""PTF-TAMPA-FL-V2-TERMINAL-HOLD-CLOSURE-003 -- Phase 6 targeting-gap fix.

Pass 2's tampa_fl_v2_closure_static_001 excluded any Places website_uri whose
RAW URL STRING matched a brand/OTA/social regex -- but the regex was applied
to the full URL including UTM tracking query parameters, not the hostname.
Many independents' own Google Business Profile links carry
"utm_source=google" / "utm_medium=GoogleMyBusiness" etc., so their genuine
first-party domain (doncesar.com, opalcollection.com, kasa.com, ...) was
skipped as if it were a brand/OTA host, purely because of a tracking
parameter. Separately, several *bona fide* single-property brand pages
(Choice, Wyndham sub-brands not already read, Red Roof, Motel 6, Drury,
Extended Stay America, Intown Suites) were skipped entirely because the old
regex is host-based-by-design but too broad -- the exclusion was meant for
brand HUBS this market reads through a dedicated lane, not for every URL
that happens to sit on a brand-chain's shared domain.

This module re-derives the exclusion on the parsed HOSTNAME only, keeps
Marriott/Hilton/IHG excluded here (those three need the supported-browser
lane in this market, confirmed by both the source-ready build and pass 2 --
see tampa_fl_v2_closure_browser_reads_002.py), and treats a genuinely
non-first-party host (facebook/instagram/tripadvisor/yelp/booking.com/
expedia/airbnb/vrbo/h-rez.com) as terminal, never fetched as policy
authority. Every other OTHER_EXPLICIT_REASON row's own URL is now fetched
with the identical binding and sentence-extraction discipline as pass 2's
lane (house number + postal code, phone digits, or JSON-LD street/postal --
never name alone; every pets/dogs/animals sentence copied verbatim;
classification is left entirely to clean_authority's shared gate and
negation guard).

Output: merges new rows into the existing
  launch_packages/pettripfinder/markets/staging/tampa-fl/raw_captures/closure_static_rows.json
(clean_authority_001 already reads this one file; no reader change needed).
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

B.DOCS = os.path.join(_DASH, "data", "acquisition", "tampa_fl_v2_closure_static_002")
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CLEAN_AUTHORITY = os.path.join(REPORTS, "tampa_fl_v2_clean_authority_001.json")
PLACES = os.path.join(REPORTS, "tampa_fl_v2_closure_places_lookup_001.json")
ROUTING_CLASS = os.path.join(REPORTS, "tampa_fl_v2_closure_routing_classification_001.json")
OUT = os.path.join(PKG, "markets", "staging", "tampa-fl", "raw_captures", "closure_static_rows.json")
OUT_TERMINAL = os.path.join(REPORTS, "tampa_fl_v2_closure_terminal_not_first_party_001.json")

# Needs the supported-browser lane in this market (confirmed both by the
# source-ready build and pass 2): excluded here, not fetched by this lane.
BROWSER_ONLY_HOSTS = re.compile(r"marriott|hilton|(^|\.)ihg\.com", re.I)
# Genuinely not a first-party policy source at any URL on this host.
NON_FIRST_PARTY_HOSTS = re.compile(
    r"facebook|instagram|tripadvisor|yelp|booking\.com|expedia|h-rez\.com|airbnb|vrbo", re.I)

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
    ca = json.load(open(CLEAN_AUTHORITY, encoding="utf-8"))
    ca_by_key = {r["identity_key"]: r for r in ca["rows"]}
    places = json.load(open(PLACES, encoding="utf-8"))
    places_by_key = {r["identity_key"]: r for r in places["rows"]}
    rcls = json.load(open(ROUTING_CLASS, encoding="utf-8"))
    other_keys = [r["identity_key"] for r in rcls["rows"] if r["closure_classification"] == "OTHER_EXPLICIT_REASON"]

    existing = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {"free_http_requests": 0, "rows": []}
    already = {r["identity_key"] for r in existing.get("rows", [])
               if r.get("note") != "brand/OTA/social host, not read here"}

    st = B.Stats()
    new_rows = []
    terminal_not_first_party = []
    for key in other_keys:
        if key in already:
            continue
        p = places_by_key.get(key)
        ca_row = ca_by_key.get(key)
        if not p or not p.get("website_uri") or not ca_row:
            continue
        url = p["website_uri"]
        host = urllib.parse.urlparse(url).netloc.lower().replace("www.", "")
        if BROWSER_ONLY_HOSTS.search(host):
            continue  # handled by the closure browser-reads lane instead
        if NON_FIRST_PARTY_HOSTS.search(host):
            terminal_not_first_party.append(OrderedDict([
                ("identity_key", key), ("canonical_name", ca_row["canonical_name"]), ("url", url), ("host", host),
                ("reason", "the only route Google Places returned is a third-party OTA/social listing, never a "
                           "first-party site; BringFido-style rule applies: identity/discovery only, never policy "
                           "authority"),
            ]))
            continue

        t = ca_row
        time.sleep(0.4)
        row, body = B.fetch(url, st, timeout=20)
        rec = OrderedDict([("identity_key", key), ("name", t["canonical_name"]), ("u", url),
                           ("final_url", row["final_url"]), ("s", row["status"]), ("h", row["sha256"]),
                           ("b", row["bytes"]), ("street", t.get("street", "")), ("postal", t.get("postal_code", "")),
                           ("phone", t.get("phone")), ("pages", []), ("bound", False),
                           ("note", "closure pass 003: fixed hostname-only brand exclusion")])
        if row["status"] != 200 or not body:
            rec["error"] = row.get("error")
            new_rows.append(rec)
            continue
        home = _decode(body)
        final = row["final_url"] or url
        fhost = urllib.parse.urlparse(final).netloc.lower().replace("www.", "")
        if BROWSER_ONLY_HOSTS.search(fhost) or NON_FIRST_PARTY_HOSTS.search(fhost):
            rec["note"] = "redirected to a browser-only or non-first-party host; not read here"
            new_rows.append(rec)
            continue
        texts = [(final, row["sha256"], row["bytes"], _text(home))]
        links = []
        for quoted, bare, label in _LINK.findall(home):
            href = quoted or bare
            lab = _text(label)
            absu = urllib.parse.urljoin(final, href)
            h2 = urllib.parse.urlparse(absu).netloc.lower().replace("www.", "")
            if h2 != fhost or absu.rstrip("/") == final.rstrip("/"):
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
        num = _house_number(t.get("street", ""))
        allt = " ".join(x[3] for x in texts)
        z = (t.get("postal_code") or "")[:5]
        ld_streets = re.findall(r'"streetAddress"\s*:\s*"([^"]+)"', home)
        ld_zips = [x[:5] for x in re.findall(r'"postalCode"\s*:\s*"([^"]+)"', home)]
        rec["bound"] = bool((num and z and re.search(r"\b%s\b" % re.escape(num), allt) and z in allt)
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
        new_rows.append(rec)

    merged_rows = list(existing.get("rows", [])) + new_rows
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(OrderedDict([("free_http_requests", existing.get("free_http_requests", 0) + st.requests),
                               ("rows", merged_rows)]), fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    with open(OUT_TERMINAL, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(OrderedDict([
            ("schema", "ptf-tampa-fl-v2-closure-terminal-not-first-party/1.0"),
            ("work_order", "PTF-TAMPA-FL-V2-TERMINAL-HOLD-CLOSURE-003"),
            ("count", len(terminal_not_first_party)),
            ("rows", terminal_not_first_party),
        ]), fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    print("new_targets", len(new_rows), "newly_bound", sum(1 for r in new_rows if r["bound"]),
          "with_pet_sentences", sum(1 for r in new_rows if any(p.get("pet_sentences") for p in r.get("pages", []))),
          "terminal_not_first_party", len(terminal_not_first_party))


if __name__ == "__main__":
    main()
