"""PTF-ORLANDO-FL-HARDENED-V2-SOURCE-READY-001 -- Phase 13B: the Choice identity-fill pages, re-read offline (no request, no credit).

The Firecrawl pass fetched each Choice property route the brand's own city pages list. Those rows carried no census
expectation (a property code selects; the page admits), so the adapter's identity gate DECLINED them as
IDENTITY_MISMATCH -- but it persisted the rendered page, its text and the identity signals the page itself states
(name, street, ZIP, phone, the Choice property code). This helper reads those persisted artifacts only:

  identity  the signals the adapter recorded from the page's own structured data
  policy    the page's own "Pets" item: "Pets Allowed: Yes|No" and its "General:" line, verbatim. Room-type labels
            ("No Pets Allowed" on a room card) and "Pet Friendly*" amenity chips are never read as the policy.

Output:
  launch_packages/pettripfinder/markets/staging/orlando-fl/raw_captures/choice_rows.json
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
REPORTS = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports")
FC = os.path.join(REPORTS, "orlando_fl_v2_firecrawl_pass_001.json")
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "staging", "orlando-fl", "raw_captures", "choice_rows.json")


def main():
    doc = json.load(open(FC, encoding="utf-8"))
    rows = []
    for r in doc["rows"]:
        if "choicehotels.com" not in (r.get("requested_url") or "") or r.get("outcome") not in ("IDENTITY_MISMATCH", "VALID"):
            continue
        slug = re.sub(r"[^a-z0-9]+", "-", r["identity_key"]).strip("-")[:80]
        base = os.path.join(_DASH, "data", "acquisition", doc["run_id"], slug)
        sub = next((s for s in ("attempt-01", "declined-01") if os.path.exists(os.path.join(base, s, "page-text.txt"))), None)
        if not sub:
            continue
        text = open(os.path.join(base, sub, "page-text.txt"), encoding="utf-8", errors="replace").read()
        html_path = os.path.join(base, sub, "rendered.html")
        raw = open(html_path, "rb").read() if os.path.exists(html_path) else b""
        sig = (r.get("identity_assessment") or {}).get("signals") or {}
        m = re.search(r"^Pets\s*\n(Pets Allowed:\s*(?:Yes|No)[^\n]*)\n(General:[^\n]*)?", text, re.M)
        pet = ""
        if m:
            pet = m.group(1).strip() + ((" / " + m.group(2).strip()) if m.group(2) else "")
        rows.append(OrderedDict([
            ("c", sig.get("property_code_on_page") or r.get("property_code")), ("u", r["requested_url"]),
            ("final_url", r.get("final_url")), ("s", 200), ("n", sig.get("name_on_page")), ("st", sig.get("address_on_page")),
            ("z", (sig.get("postal_code") or "")[:5]), ("ph", sig.get("phone_on_page")), ("ci", ""),
            ("pet", pet), ("h", hashlib.sha256(raw).hexdigest() if raw else r.get("page_sha256")), ("b", len(raw) or None),
            ("artifact", os.path.relpath(os.path.join(base, sub), _DASH).replace("\\", "/")),
            ("firecrawl_outcome", r.get("outcome")),
        ]))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rows, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("choice pages", len(rows), "with Pets item", sum(1 for x in rows if x["pet"]))


if __name__ == "__main__":
    main()
