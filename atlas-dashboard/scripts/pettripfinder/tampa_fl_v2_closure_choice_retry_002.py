"""PTF-TAMPA-FL-V2-TERMINAL-HOLD-CLOSURE-003 -- Phase 6 actionable-lane
review: 17 choicehotels.com property pages timed out at the static lane's
20s timeout (a slow/throttled response, not a definitive 403/block like
Marriott/Hilton's Akamai wall). A retry at the SAME lane with a longer
timeout is a legitimate unexhausted-lane check, not a new capability.
Replaces the timed-out rows in closure_static_rows.json in place.
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

B.DOCS = os.path.join(_DASH, "data", "acquisition", "tampa_fl_v2_closure_choice_retry_002")
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
CLEAN_AUTHORITY = os.path.join(PKG, "markets", "reports", "tampa_fl_v2_clean_authority_001.json")
STATIC_OUT = os.path.join(PKG, "markets", "staging", "tampa-fl", "raw_captures", "closure_static_rows.json")

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
    static_doc = json.load(open(STATIC_OUT, encoding="utf-8"))
    rows = static_doc["rows"]
    ca = json.load(open(CLEAN_AUTHORITY, encoding="utf-8"))
    ca_by_key = {r["identity_key"]: r for r in ca["rows"]}

    retry_targets = [r for r in rows if r.get("error") and "Timeout" in str(r.get("error"))
                     and "choicehotels" in (r.get("u") or "")]
    st = B.Stats()
    retried = 0
    fixed = 0
    for rec in retry_targets:
        key = rec["identity_key"]
        t = ca_by_key.get(key, {})
        url = rec["u"]
        retried += 1
        time.sleep(0.5)
        row, body = B.fetch(url, st, timeout=45)
        rec["s"] = row["status"]
        rec["final_url"] = row["final_url"]
        rec["h"] = row["sha256"]
        rec["b"] = row["bytes"]
        rec["note"] = "closure pass 003: retried at 45s timeout (Choice throttling)"
        if row["status"] != 200 or not body:
            rec["error"] = row.get("error")
            continue
        del rec["error"]
        fixed += 1
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
            time.sleep(0.5)
            prow, pbody = B.fetch(u, st, timeout=45)
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
        rec["pages"] = []
        for u2, sha, nbytes, txt in texts:
            sents = []
            for m in _SENT.finditer(txt):
                s = m.group(0).strip()
                if re.search(r"service animal|emotional support", s, re.I) and not re.search(r"\bpets?\b|\bdogs?\b", s, re.I):
                    continue
                if s not in sents and len(sents) < 8:
                    sents.append(s)
            rec["pages"].append(OrderedDict([("url", u2), ("sha256", sha), ("bytes", nbytes), ("pet_sentences", sents)]))

    static_doc["free_http_requests"] = static_doc.get("free_http_requests", 0) + st.requests
    with open(STATIC_OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(static_doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("retried", retried, "now_200", fixed, "still_timeout_or_error", retried - fixed,
          "with_pet_sentences", sum(1 for r in retry_targets if any(p.get("pet_sentences") for p in r.get("pages", []))))


if __name__ == "__main__":
    main()
