"""PTF-TAMPA-FL-V2-TERMINAL-HOLD-CLOSURE-003 -- static-fetch acquisition for
the non-Wyndham newly-admitted hotels from tampa_fl_v2_closure_census_additions_002
(Sonesta Simply Suites, 3 Extended Stay America, 1 independent). Same binding
and sentence-extraction discipline as every other closure static lane: house
number + postal code, phone digits, or JSON-LD street/postal -- never name
alone. Merges into closure_static_rows.json (clean_authority_001 already
reads this one file).
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

B.DOCS = os.path.join(_DASH, "data", "acquisition", "tampa_fl_v2_closure_additions_static_002")
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
ADDITIONS = os.path.join(REPORTS, "tampa_fl_v2_closure_census_additions_002.json")
OUT = os.path.join(PKG, "markets", "staging", "tampa-fl", "raw_captures", "closure_static_rows.json")

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
    additions = json.load(open(ADDITIONS, encoding="utf-8"))["additions"]
    targets = [a for a in additions if a.get("brand") != "WYNDHAM" and a.get("official_url")]

    existing = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {"free_http_requests": 0, "rows": []}
    already = {r["identity_key"] for r in existing.get("rows", [])}

    st = B.Stats()
    new_rows = []
    for t in targets:
        key = t["identity_key"]
        if key in already:
            continue
        url = t["official_url"]
        time.sleep(0.4)
        row, body = B.fetch(url, st, timeout=20)
        rec = OrderedDict([("identity_key", key), ("name", t["canonical_name"]), ("u", url),
                           ("final_url", row["final_url"]), ("s", row["status"]), ("h", row["sha256"]),
                           ("b", row["bytes"]), ("street", t.get("street", "")), ("postal", t.get("postal_code", "")),
                           ("phone", t.get("phone")), ("pages", []), ("bound", False),
                           ("note", "closure pass 003: newly-admitted BringFido/Places addition")])
        if row["status"] != 200 or not body:
            rec["error"] = row.get("error")
            new_rows.append(rec)
            continue
        home = _decode(body)
        final = row["final_url"] or url
        host = urllib.parse.urlparse(final).netloc.lower().replace("www.", "")
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
    print("new_targets", len(new_rows), "newly_bound", sum(1 for r in new_rows if r["bound"]),
          "with_pet_sentences", sum(1 for r in new_rows if any(p.get("pet_sentences") for p in r.get("pages", []))))


if __name__ == "__main__":
    main()
