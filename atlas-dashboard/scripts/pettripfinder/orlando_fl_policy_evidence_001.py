"""PTF-ORLANDO-FL-PARALLEL-SOURCE-READY-001 -- durable policy evidence for the orlando-fl shadow build.

Reads ONLY committed raw captures:

    raw_captures/evidence_pages_001.jsonl.gz   stored page bodies + capture metadata
    raw_captures/hilton_inventory_001.json     Hilton property codes (hotel-info pages)
    evidence_rulings_001.json                  the exact first-party sentences that operate

and produces one evidence record per (identity anchor, page). Every record
carries requested/final URL, lane, capture timestamp, body hash + byte length,
identity signals read from the page, the operative quote, the facts the SHARED
readers extracted, and the decision.

The shared readers (``prose_facts``, ``prose_fee_ladder``) are called, never
edited. Their acceptance pattern does not see negation ("not pet-friendly",
"do not allow pets"), so this module overrules a reader "true" TOWARD A HOLD
when such negation is present. It never overrules toward publication.
"""

from __future__ import annotations

import gzip
import hashlib
import html
import json
import re
import sys
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import prose_facts, prose_fee_ladder  # noqa: E402

MARKET_ID = "orlando-fl"
STAGING = _REPO_ROOT / "launch_packages" / "pettripfinder" / "markets" / "staging" / MARKET_ID
RAW = STAGING / "raw_captures"

LABEL_ALLOWED = re.compile(r"\bpets\s+allowed\s*:\s*(yes|no)\b", re.I)
NEGATION = re.compile(
    r"\bnot\s+(?:a\s+)?(?:pet|dog)[-\s]friendly\b|\bdo(?:es)?\s+not\s+(?:allow|accept|permit|welcome)\s+(?:any\s+)?pets?\b"
    r"|\bnot\s+(?:allow|accept)\s+pets?\b|\bunable\s+to\s+accommodate\s+pets?\b|\bpets?\s+(?:are\s+)?prohibited\b"
    r"|\bbut\s+not\s+pets?\b|\bno\s+pets?\b|\bpets?\s+(?:are\s+)?not\s+(?:permitted|allowed|accepted)\b", re.I)


def load_pages() -> Dict[str, dict]:
    pages = {}
    with gzip.open(RAW / "evidence_pages_001.jsonl.gz", "rt", encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            body = rec["body"]
            if hashlib.sha256(body.encode("utf-8")).hexdigest() != rec["body_sha256_utf8"]:
                raise ValueError("stored body hash mismatch for %s" % rec["requested_url"])
            pages[rec["requested_url"]] = rec
    return pages


def visible_text(body: str) -> str:
    b = re.sub(r"(?is)<(script|style|noscript|svg|nav|header|footer)[^>]*>.*?</\1>", " ", body)
    b = re.sub(r"(?s)<[^>]+>", " | ", b)
    b = html.unescape(b)
    return " ".join(b.split())


def read_facts(block: str) -> dict:
    facts = {}
    for name, fn in (("pet_count", prose_facts.extract_pet_count), ("weight_limit", prose_facts.extract_weight_limit),
                     ("species", prose_facts.extract_species), ("fee_with_basis", prose_facts.extract_fee_with_basis),
                     ("fee_cap", prose_facts.extract_fee_cap)):
        value = fn(block)
        if value is not None:
            facts[name] = value.to_dict()
    schedule = prose_fee_ladder.parse_prose_fee_schedule(block)
    if schedule is not None:
        facts["fee_schedule"] = {"is_staged": schedule.is_staged}
        facts.pop("fee_with_basis", None)
    rng = prose_facts.detect_unrepresentable_fee_range(block)
    if rng is not None:
        facts["unrepresentable_fee_range"] = rng.to_dict()
    m = re.search(r"non-?refundable\s+fee\s*:\s*\$\s*([\d,]+(?:\.\d{2})?)", block, re.I)
    if m:
        # A LABEL on the property's policy card, recorded as a label: basis and
        # scope are not stated by the label and are left absent.
        facts["labelled_non_refundable_fee"] = {"amount": m.group(1).replace(",", ""), "refundable": False, "quote": m.group(0)}
    m = re.search(r"max(?:imum)?\s+weight\s*:\s*(\d+)\s*lbs?", block, re.I)
    if m:
        facts["labelled_max_weight_lb"] = {"value": m.group(1), "quote": m.group(0)}
    return facts


def adjudicate(block: str) -> dict:
    if not block.strip():
        return {"decision": "SILENT", "note": "no operative pet wording captured on the page"}
    acc = prose_facts.extract_pets_allowed(block)
    label = LABEL_ALLOWED.search(block)
    negated = NEGATION.search(block)
    facts = read_facts(block)
    if acc is None:
        return {"decision": "EVIDENCE_HOLD", "facts": facts, "negation": negated.group(0) if negated else None,
                "note": "shared reader declined the first-party wording (no explicit welcome/refusal it can read, or contradictory); wording preserved"}
    out = {"acceptance": acc.to_dict(), "facts": facts}
    if label and (label.group(1).lower() == "yes") != (acc.value == "true"):
        out.update(decision="EVIDENCE_HOLD", note="labelled 'Pets allowed' value contradicts the shared reader")
    elif acc.value == "true" and negated:
        out.update(decision="EVIDENCE_HOLD", negation=negated.group(0),
                   note="shared reader read acceptance but the wording is negated ('%s'); overruled toward hold" % negated.group(0))
    elif acc.value == "true":
        out.update(decision="PET_FRIENDLY", note="explicit first-party acceptance read by the shared reader")
    else:
        out.update(decision="NO_PETS", note="explicit first-party refusal read by the shared reader")
    return out


def _page_meta(rec: dict) -> dict:
    return {"requested_url": rec["requested_url"], "final_url": rec.get("final_url"), "capture_lane": rec["lane"],
            "capture_timestamp": rec["captured_at"], "http_status": rec.get("status"),
            "content_sha256_utf8": rec["body_sha256_utf8"], "byte_length_utf8": rec["byte_length_utf8"],
            "content_sha256_in_capture_context": rec.get("body_sha256_in_capture_context"),
            "durable_content_reference": "raw_captures/evidence_pages_001.jsonl.gz#requested_url=%s" % rec["requested_url"]}


def hilton_records(pages: Dict[str, dict]) -> List[dict]:
    inv = json.loads((RAW / "hilton_inventory_001.json").read_text(encoding="utf-8"))["hotels"]
    by_url = {}
    for h in inv:
        if h.get("url"):
            by_url[h["url"].rstrip("/") + "/hotel-info/"] = h
    out = []
    for url, rec in sorted(pages.items()):
        if url not in by_url:
            continue
        h = by_url[url]
        body = rec["body"]
        m = re.search(r'<h3 class="heading--base heading--sm">Pets</h3>(.*?)</ul>', body, re.S)
        lines = []
        if m:
            for li in re.findall(r"<li>(.*?)</li>", m.group(1), re.S):
                lines.append(html.unescape(" ".join(re.sub(r"<[^>]+>", "", li.replace("<!-- -->", "")).split())))
        quote = " | ".join(lines)
        street = re.search(r'"streetAddress"\s*:\s*"([^"]+)"', body)
        postal = re.search(r'"postalCode"\s*:\s*"([^"]+)"', body)
        phone = re.search(r'"telephone"\s*:\s*"([^"]+)"', body)
        signals = {"page_street": html.unescape(street.group(1)) if street else None, "page_postal": postal.group(1) if postal else None,
                   "page_phone": phone.group(1) if phone else None, "brand_property_code": h["property_code"]}
        signals["street_matches_inventory"] = bool(street and h.get("street") and street.group(1).split()[0] == h["street"].split()[0])
        adj = adjudicate(quote) if rec.get("status") == 200 else {"decision": "FETCH_FAILED", "note": "HTTP %s" % rec.get("status")}
        if rec.get("status") == 200 and not quote:
            adj = {"decision": "SILENT", "note": "hotel-info page served; the policy card is rendered client-side (accordion) and was not in the captured markup"}
        out.append(dict(anchor="HILTON:" + h["property_code"], source_class="PT2_BRAND (property page on the brand's own site)",
                        operative_quote=quote or None, identity_signals=signals, **_page_meta(rec), **adj))
    return out


def ruling_records(pages: Dict[str, dict]) -> List[dict]:
    rulings = json.loads((STAGING / "evidence_rulings_001.json").read_text(encoding="utf-8"))["rulings"]
    out = []
    for r in rulings:
        rec = pages[r["url"]]
        text = visible_text(rec["body"])
        missing = [q for q in r["quotes"] if " ".join(q.split()) not in text]
        facts_extra = {}
        if r.get("facts_url"):
            ftext = visible_text(pages[r["facts_url"]]["body"])
            fmiss = [q for q in r["facts_quotes"] if " ".join(q.split()) not in ftext]
            missing += fmiss
            facts_extra = {"facts_page": _page_meta(pages[r["facts_url"]]), "facts_quotes": r["facts_quotes"],
                           "facts_from_facts_page": read_facts(" ".join(r["facts_quotes"]))}
        quote = " ".join(r["quotes"])
        if missing:
            adj = {"decision": "EVIDENCE_HOLD", "note": "quote not found verbatim on the stored page: %r" % missing}
        else:
            adj = adjudicate(quote)
            if r.get("force") and adj["decision"] == "PET_FRIENDLY":
                adj = dict(adj, decision=r["force"], note=r["force_reason"])
            elif r.get("force") and adj["decision"] != r["force"]:
                adj = dict(adj, decision="EVIDENCE_HOLD", note=r["force_reason"])
        num = re.findall(r"\b\d{3,5}\b", text)
        out.append(dict(anchor=r["anchor"], source_class="PT1_FIRST_PARTY (property's own website)" if "sonesta.com" not in r["url"] and "intownsuites.com" not in r["url"] and "woodspring.com" not in r["url"] and "loewshotels.com" not in r["url"] and "margaritavilleresorts.com" not in r["url"] else "PT2_BRAND (property page on the brand's own site)",
                        operative_quote=quote, quotes_verified_verbatim=not missing, identity_signals={"page_numbers_sample": sorted(set(num))[:12]},
                        **_page_meta(rec), **adj, **facts_extra))
    return out


def build() -> List[dict]:
    pages = load_pages()
    return sorted(hilton_records(pages) + ruling_records(pages), key=lambda e: (e["anchor"], e["requested_url"]))


if __name__ == "__main__":
    import collections
    recs = build()
    print(len(recs), collections.Counter(r["decision"] for r in recs))
    for r in recs:
        if not r["anchor"].startswith("HILTON:") or r["decision"] != "PET_FRIENDLY":
            print(r["anchor"], r["decision"], "|", (r.get("operative_quote") or "")[:90], "|", r.get("note", "")[:90])
