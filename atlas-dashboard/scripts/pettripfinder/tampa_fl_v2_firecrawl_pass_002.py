"""PTF-TAMPA-FL-V2-TERMINAL-HOLD-CLOSURE-003 -- Phase 5/6: a second Firecrawl
pass over the 18 rows (17 Choice-family + 1 Motel 6) whose plain-HTTP
closure-static fetch timed out at both 20s and a 45s retry, and whose
supported-browser read hit choicehotels.com's Akamai bot-check page
(reproduced identically to Orlando's own documented Choice wall). Firecrawl
is the router's own documented next rung for exactly this family
("IHG/Wyndham/Choice may route through Firecrawl where factory rules
permit") and existing plan credits are used -- 1 credit per page, spent
only on success (bimodal cost, per the standing rule).

This closure pass uses a leaner extraction than the source-ready build's
own tampa_fl_v2_firecrawl_pass_001 (which called the shared BrightData
policy reader for a structured multi-field extraction): it captures the raw
Firecrawl HTML, verbatim-quotes every operative pets sentence, and binds
identity the same way every other closure lane does (house number + postal,
phone, or JSON-LD) before accepting. It writes rows compatible with the
exact fields tampa_fl_v2_clean_authority_001's Firecrawl evidence index
consumes (firecrawl_class, pets_allowed, observation.evidence,
final_url/requested_url, page_sha256) -- merged into the SAME
tampa_fl_v2_firecrawl_pass_001.json file clean_authority already reads, so
no reader change was needed.
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import sys
import time
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.acquisition import firecrawl_capture as FC  # noqa: E402

PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CLEAN_AUTHORITY = os.path.join(REPORTS, "tampa_fl_v2_clean_authority_001.json")
STATIC = os.path.join(PKG, "markets", "staging", "tampa-fl", "raw_captures", "closure_static_rows.json")
FIRECRAWL_OUT = os.path.join(REPORTS, "tampa_fl_v2_firecrawl_pass_001.json")

_SENT = re.compile(r"[^.!?]{0,240}\b(pets?|dogs?|animals?)\b[^.!?]{0,240}[.!?]", re.I)
_REFUSAL = re.compile(r"pets allowed\s*:\s*no\b|no,?\s+pets are not allowed|pets? (?:are|is) not (?:allowed|permitted)|"
                      r"we do not allow pets|no pets permitted|pets? (?:are|is) prohibited", re.I)
_ACCEPT = re.compile(r"pets allowed\s*:\s*yes\b|pets? (?:are|is) welcome|we (?:welcome|allow) pets|pet-friendly", re.I)
_FEE_RX = re.compile(r"pet (fee|deposit)", re.I)
_WEIGHT_RX = re.compile(r"weight limit|\d+\s*lbs?\b", re.I)


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
    static_doc = json.load(open(STATIC, encoding="utf-8"))
    static_by_key = {r["identity_key"]: r for r in static_doc["rows"]}

    targets = [r for r in static_doc["rows"]
               if r.get("error") and "Timeout" in str(r.get("error")) and r["identity_key"] in ca_by_key]

    fc_doc = json.load(open(FIRECRAWL_OUT, encoding="utf-8"))
    already = {r["identity_key"] for r in fc_doc.get("rows", []) if r.get("firecrawl_class")}
    credits_before = FC.credits_remaining()

    new_rows = []
    for t in targets:
        key = t["identity_key"]
        if key in already:
            continue
        ca_row = ca_by_key[key]
        url = t["u"]
        try:
            result = FC.fetch(url)
        except Exception as exc:  # noqa: BLE001 -- recorded, never silently swallowed
            new_rows.append(OrderedDict([("identity_key", key), ("requested_url", url),
                                         ("firecrawl_class", "FIRECRAWL_FAILED"),
                                         ("detail", "exception:%s" % type(exc).__name__)]))
            continue
        if not result.get("ok") or result.get("status") != 200 or not result.get("html"):
            new_rows.append(OrderedDict([("identity_key", key), ("requested_url", url),
                                         ("final_url", result.get("final_url") or url),
                                         ("firecrawl_class", "FIRECRAWL_FAILED"),
                                         ("detail", "status=%r error=%r" % (result.get("status"), result.get("error")))]))
            continue
        doc = result["html"]
        text = _text(doc)
        num = _house_number(ca_row.get("street", ""))
        z = (ca_row.get("postal_code") or "")[:5]
        ld_streets = re.findall(r'"streetAddress"\s*:\s*"([^"]+)"', doc)
        ld_zips = [x[:5] for x in re.findall(r'"postalCode"\s*:\s*"([^"]+)"', doc)]
        bound = bool((num and z and re.search(r"\b%s\b" % re.escape(num), text) and z in text)
                    or (num and z and z in ld_zips and any((s.split() or [""])[0] == num for s in ld_streets)))
        if not bound:
            new_rows.append(OrderedDict([("identity_key", key), ("requested_url", url),
                                         ("final_url", result.get("final_url") or url),
                                         ("firecrawl_class", "FIRECRAWL_MISMATCH"),
                                         ("detail", "captured page did not confirm this identity "
                                                    "(no matching house number + postal or JSON-LD address)")]))
            continue
        sents = []
        for m in _SENT.finditer(text):
            s = m.group(0).strip()
            if re.search(r"service animal|emotional support", s, re.I) and not re.search(r"\bpets?\b|\bdogs?\b", s, re.I):
                continue
            if s not in sents and len(sents) < 8:
                sents.append(s)
        joined = " ".join(sents)
        if _REFUSAL.search(joined):
            pets_allowed = False
        elif _ACCEPT.search(joined) or _FEE_RX.search(joined) or _WEIGHT_RX.search(joined):
            pets_allowed = True
        else:
            new_rows.append(OrderedDict([("identity_key", key), ("requested_url", url),
                                         ("final_url", result.get("final_url") or url),
                                         ("firecrawl_class", "FIRECRAWL_SOURCE_SILENT"),
                                         ("detail", "page captured and identity-bound but no operative pet "
                                                    "sentence found")]))
            continue
        page_sha256 = hashlib.sha256(doc.encode("utf-8", "replace")).hexdigest()
        new_rows.append(OrderedDict([
            ("identity_key", key), ("requested_url", url), ("final_url", result.get("final_url") or url),
            ("page_sha256", page_sha256), ("pets_allowed", pets_allowed),
            ("observation", OrderedDict([
                ("evidence", [OrderedDict([("quote", joined[:500]), ("field_refs", ["pets_allowed"])])]),
            ])),
            ("captured_via", "Firecrawl rendered scrape (raw HTML), existing plan credits, terminal-hold "
                             "closure pass -- Choice/Motel6 Akamai wall bypassed"),
            ("firecrawl_class", "FIRECRAWL_PUBLICATION_GRADE"),
        ]))
        time.sleep(0.3)

    credits_after = FC.credits_remaining()
    merged = list(fc_doc.get("rows", [])) + new_rows
    fc_doc["rows"] = merged
    with open(FIRECRAWL_OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(fc_doc, f, indent=1, ensure_ascii=False)
        f.write("\n")

    print("targets", len(targets), "attempted", len(new_rows),
          "publication_grade", sum(1 for r in new_rows if r.get("firecrawl_class") == "FIRECRAWL_PUBLICATION_GRADE"),
          "mismatch", sum(1 for r in new_rows if r.get("firecrawl_class") == "FIRECRAWL_MISMATCH"),
          "source_silent", sum(1 for r in new_rows if r.get("firecrawl_class") == "FIRECRAWL_SOURCE_SILENT"),
          "failed", sum(1 for r in new_rows if r.get("firecrawl_class") == "FIRECRAWL_FAILED"))
    print("credits", credits_before, "->", credits_after)


if __name__ == "__main__":
    main()
