"""PTF-ORLANDO-FL-HARDENED-V2-SOURCE-READY-001 -- Phase 13D: IHG property pages rendered by Firecrawl, re-read offline.

Both Firecrawl passes persisted each IHG page's text and the identity signals the page itself states. IHG's operative
pet statement is the property FAQ's own answer to "Can I bring my pet to <hotel>?" followed by the hotel's "Pet policy
description." and labelled rows ("Pet fee per stay: 150 USD", "Pet weight limit: 25", "2 pets allowed", "Pets allowed:
Only dogs and cats allowed"). This helper copies exactly that block, line by line, from the persisted page text. No
request is made and no credit is spent.

Output: launch_packages/pettripfinder/markets/staging/orlando-fl/raw_captures/ihg_rows.json
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
REPORTS = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports")
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "staging", "orlando-fl", "raw_captures", "ihg_rows.json")
PASSES = ("orlando_fl_v2_firecrawl_pass_001.json", "orlando_fl_v2_firecrawl_pass_002.json")


def block(text):
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.match(r"\s*Can I bring my pet to\b", line, re.I):
            out = [line.strip()]
            for nxt in lines[i + 1:i + 12]:
                s = nxt.strip()
                if not s or re.match(r"(Can I|Does |Is there|What |How |Pet policy$)", s):
                    break
                out.append(s)
            return out
    return []


def main():
    rows, seen = [], set()
    for name in PASSES:
        p = os.path.join(REPORTS, name)
        if not os.path.exists(p):
            continue
        doc = json.load(open(p, encoding="utf-8"))
        for r in doc["rows"]:
            if "ihg.com" not in (r.get("requested_url") or "") or r.get("outcome") not in ("VALID", "IDENTITY_MISMATCH"):
                continue
            slug = re.sub(r"[^a-z0-9]+", "-", r["identity_key"]).strip("-")[:80]
            base = os.path.join(_DASH, "data", "acquisition", doc["run_id"], slug)
            sub = next((s for s in ("attempt-01", "declined-01") if os.path.exists(os.path.join(base, s, "page-text.txt"))), None)
            if not sub:
                continue
            sig = (r.get("identity_assessment") or {}).get("signals") or {}
            code = (re.search(r"/([a-z0-9]{5})/hoteldetail", r["requested_url"]) or [None, ""])[1]
            if code in seen:
                continue
            seen.add(code)
            text = open(os.path.join(base, sub, "page-text.txt"), encoding="utf-8", errors="replace").read()
            html_path = os.path.join(base, sub, "rendered.html")
            raw = open(html_path, "rb").read() if os.path.exists(html_path) else b""
            b = block(text)
            rows.append(OrderedDict([
                ("c", code), ("u", r["requested_url"]), ("final_url", r.get("final_url")), ("n", sig.get("name_on_page")),
                ("st", sig.get("address_on_page")), ("z", (sig.get("postal_code") or "")[:5]), ("ph", sig.get("phone_on_page")),
                ("q", b[0] if b else ""), ("p", "\n".join(b[1:]) if b else ""),
                ("h", hashlib.sha256(raw).hexdigest() if raw else r.get("page_sha256")), ("b", len(raw) or None),
                ("artifact", os.path.relpath(os.path.join(base, sub), _DASH).replace("\\", "/")),
                ("firecrawl_outcome", r.get("outcome")), ("pass", name),
            ]))
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rows, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("ihg pages", len(rows), "with FAQ pet block", sum(1 for x in rows if x["p"]))


if __name__ == "__main__":
    main()
