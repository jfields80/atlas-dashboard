"""PTF-CLEVELAND-AKRON-CANTON-HARDENED-POLICY-003 -- Phases 10 / 11.

Free policy evidence for the shadow-admitted Cleveland identities (the 23
rows admitted by Order 002, plus any further row the founder admits), through
the same two lanes Order 001 used:

    run-static        acquisition.direct_http_capture.run_attempt (one HTTPS
                      GET; the paid lanes' own gates: denial -> health ->
                      identity -> locator -> reader) followed by
                      market_observation_store.observation_for (reader ->
                      publication_grade); artifacts land under
                      data/acquisition/<run>/<slug>/attempt-01/
    ingest-attended   one attended Chrome payload (document sha256, JSON-LD,
                      address lines, pet text windows) read by the canonical
                      reader over the visible-text windows, identity bound on
                      the page's OWN street number + postal (+ phone)
    classify          exactly one of CLEAN_PET_FRIENDLY / CLEAN_VERIFIED_NO_PETS /
                      POLICY_NOT_FOUND / SOURCE_SILENT / SOURCE_CONTRADICTORY /
                      FOUNDER_EXCEPTION / IDENTITY_MISMATCH / CAPTURE_FAILED

Owned evidence is reused before any fetch. No paid provider. Nothing is
written to live authority.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter, OrderedDict
from pathlib import Path

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.acquisition import direct_http_capture as DHC  # noqa: E402
from scripts.pettripfinder.acquisition import market_observation_store as MOS  # noqa: E402
from scripts.pettripfinder.brightdata import browser_capture as BC  # noqa: E402
from scripts.pettripfinder.brightdata import unlocker_capture as UC  # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR  # noqa: E402
from scripts.pettripfinder.brightdata import marriott_surface as MS  # noqa: E402
from scripts.pettripfinder.discovery import identity_dedup as DEDUP  # noqa: E402

WORK_ORDER = "PTF-CLEVELAND-AKRON-CANTON-HARDENED-POLICY-003"
MARKET_ID = "cleveland-akron-canton-oh"
M = MARKET_ID.replace("-", "_")
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
ADMISSION = os.path.join(PKG, "identity_census_admission", f"{MARKET_ID}.json")
RESULTS = os.path.join(REPORTS, f"{M}_policy_reads_003.json")
RUN_ID = f"{M}_policy_reads_003"
RAW = os.path.join(_DASH, "data", "worker_runs", "pettripfinder", "cleveland-hardened-policy-003", "raw")
ATTENDED_HOSTS = ("hilton.com", "marriott.com", "ihg.com", "choicehotels.com", "bestwestern.com", "radissonhotels", "redroof.com", "extendedstayamerica.com", "hyatt.com", "ritzcarlton.com")
BRANDS = [("MARRIOTT", r"marriott|courtyard|residence inn|springhill|fairfield|towneplace|ac hotel|aloft|westin|sheraton|ritz|autograph"),
          ("HILTON", r"hilton|hampton|embassy suites|homewood|home2|doubletree|tru by"), ("IHG", r"holiday inn|crowne plaza|staybridge|candlewood|kimpton|hotel indigo"),
          ("CHOICE", r"comfort inn|comfort suites|quality inn|sleep inn|clarion|cambria|mainstay|suburban|econo lodge|country inn"),
          ("WYNDHAM", r"wyndham|baymont|days inn|super 8|ramada|travelodge|la quinta|microtel|wingate"), ("ESA", r"extended stay america"),
          ("BEST_WESTERN", r"best western"), ("SONESTA", r"sonesta"), ("RED_ROOF", r"red roof"), ("MOTEL6", r"motel 6")]
SERVICE_ONLY = re.compile(r"\bservice animals?\b", re.I)
GENERIC = re.compile(r"varies by (hotel|property)|contact the (hotel|property)|policies vary", re.I)


def brand_of(name):
    n = (name or "").lower()
    for fam, rx in BRANDS:
        if re.search(rx, n):
            return fam
    return "INDEPENDENT"


def host_of(url):
    m = re.match(r"https?://([^/]+)", url or "")
    return m.group(1).lower().replace("www.", "") if m else ""


def read_json(p):
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as fh:
        fh.write((json.dumps(d, indent=1, ensure_ascii=False, default=str) + "\n").encode("utf-8"))


def as_plain(o):
    if dataclasses.is_dataclass(o):
        return {k: as_plain(v) for k, v in dataclasses.asdict(o).items()}
    if isinstance(o, (list, tuple)):
        return [as_plain(x) for x in o]
    if isinstance(o, dict):
        return {k: as_plain(v) for k, v in o.items()}
    return o


def digits(v):
    return re.sub(r"[^0-9]", "", v or "")[-10:]


def targets():
    shadow = read_json(ADMISSION)
    return [h for h in shadow["hotels"] if (h.get("admission") or {}).get("status", "").startswith("SHADOW_ADMITTED")]


def load():
    return read_json(RESULTS) if os.path.exists(RESULTS) else OrderedDict([("schema", "ptf-shadow-policy-reads/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID), ("run_id", RUN_ID),
                                                                             ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", 0), ("rows", [])])


def upsert(doc, row):
    doc["rows"] = [r for r in doc["rows"] if r["identity_key"] != row["identity_key"]] + [row]
    write_json(RESULTS, doc)


def cmd_run_static(args):
    doc = load()
    done = {r["identity_key"] for r in doc["rows"]}
    run_dir = Path(_DASH) / "data" / "acquisition" / RUN_ID
    run_dir.mkdir(parents=True, exist_ok=True)
    for h in targets():
        key = h["identity_key"]
        url = h.get("official_url") or ""
        if not url or (key in done and not args.refetch) or any(x in host_of(url) for x in ATTENDED_HOSTS):
            continue
        brand = brand_of(h["canonical_name"])
        target = BC.CaptureTarget(slug=h["slug"], hotel=h["canonical_name"], requested_url=url, property_code=DEDUP.property_code({"official_url": url}), market_id=MARKET_ID,
                                  normalized_name=key, identity_key=key, street_identity=h.get("street_identity", ""), expected_postal_code=h["postal_code"], expected_street=h["address"],
                                  expected_phone=h.get("phone", ""), expected_locality=h.get("city", ""), identity_brand=brand, census_matched=True)
        time.sleep(2.0)
        attempt, payload = DHC.run_attempt(target, 1, run_dir=run_dir, brand=brand)
        doc["free_http_requests"] += 1
        a = as_plain(attempt)
        attempt_dir = run_dir / h["slug"] / "attempt-01"
        row = OrderedDict([("identity_key", key), ("canonical_name", h["canonical_name"]), ("brand", brand), ("lane", "STATIC"), ("requested_url", url), ("final_url", a.get("final_url")),
                           ("outcome", a.get("outcome")), ("detail", (a.get("detail") or "")[:300]), ("identity_assessment", a.get("identity")),
                           ("document_sha256", hashlib.sha256((attempt_dir / "rendered.html").read_bytes()).hexdigest() if (attempt_dir / "rendered.html").is_file() else None),
                           ("artifact_dir", str(attempt_dir.relative_to(_DASH)) if attempt_dir.is_dir() else ""), ("captured_at", a.get("started_at"))])
        if a.get("outcome") == "VALID" and (attempt_dir / "policy-block.txt").is_file():
            result = {"identity_key": key, "canonical_name": h["canonical_name"], "brand": brand, "corridor": h.get("corridor", ""), "source_url": url, "outcome": "VALID",
                      "final_url": a.get("final_url") or url, "artifact_dir": str(attempt_dir), "identity_confirmed": bool((a.get("identity") or {}).get("confirmed", True)), "locator_strategy": ""}
            try:
                obs, grade, refusal = MOS.observation_for(result, run_id=RUN_ID, market_id=MARKET_ID, census_row=h)
                o = (obs or {}).get("observation") or {}
                row["observation"] = OrderedDict([("extraction", o.get("extraction")), ("evidence", o.get("evidence")), ("withheld_fields", (obs or {}).get("withheld_fields")),
                                                  ("publication_grade", grade), ("refusal_reason", refusal), ("reader_provenance", (obs or {}).get("reader_provenance"))])
            except Exception as exc:  # noqa: BLE001
                row["observation_error"] = repr(exc)
        upsert(doc, row)
        print(" ", key, a.get("outcome"), (row.get("observation") or {}).get("extraction"))
    return 0


def read_windows(windows, brand):
    text = "\n\n".join(windows or [])
    if not text.strip():
        return None
    hit = UC.locate_policy_in_text(text)
    if not hit.found:
        return OrderedDict([("found", False)])
    reader_used = "generic"
    reading = PR.parse(hit.text, strategy=hit.strategy or WORK_ORDER)
    result = PR.to_extraction(reading, location=MARKET_ID)
    if brand == "MARRIOTT":
        # Marriott's own reader first; the generic reader is kept only where the
        # Marriott surface leaves pets_allowed unstated (the FAQ answer form).
        m_reading = MS.parse_policy_block(hit.text, locator_id=WORK_ORDER)
        m_result = MS.to_extraction(m_reading, location=MARKET_ID)
        if m_result.extraction.get("pets_allowed") is not None or result.extraction.get("pets_allowed") is None:
            reading, result, reader_used = m_reading, m_result, "marriott"
        else:
            reader_used = "generic (marriott reader left pets_allowed SOURCE_SILENT on the FAQ form)"
    return OrderedDict([("found", True), ("reader_used", reader_used), ("block", hit.text[:700]), ("pets_allowed", result.extraction.get("pets_allowed")), ("pets_allowed_quote", (getattr(reading, "pets_allowed_quote", "") or "")[:300]),
                        ("extraction", result.extraction), ("withheld", dict(result.withheld)), ("evidence_quotes", [e.get("quote", "")[:300] for e in result.evidence][:8]),
                        ("service_animal_quote", (getattr(reading, "service_animal_quote", "") or "")[:200]), ("brand_generic", bool(getattr(reading, "brand_generic", False))),
                        ("contradictions", list(getattr(reading, "contradictions", ()) or ())), ("parser_warnings", list(result.parser_warnings))])


def cmd_ingest_attended(args):
    rows = {h["identity_key"]: h for h in targets()}
    h = rows[args.identity_key]
    payload = read_json(args.payload)
    doc = load()
    os.makedirs(RAW, exist_ok=True)
    brand = brand_of(h["canonical_name"])
    fname = "PR-%s.json" % re.sub(r"[^a-z0-9]+", "-", h["identity_key"]).strip("-")
    artifact = OrderedDict([("schema", "ptf-attended-capture/2.1-text-windows"), ("work_order", WORK_ORDER), ("identity_key", h["identity_key"]), ("captured_at", payload.get("captured_at")),
                            ("requested_url", args.requested_url or payload.get("url")), ("final_url", payload.get("url")), ("title", payload.get("title")), ("capture_method", "attended_browser"),
                            ("interaction", args.interaction or ""), ("html_sha256", payload.get("html_sha256")), ("text_sha256", payload.get("text_sha256")), ("jsonld", payload.get("jsonld")),
                            ("address_lines", payload.get("address_lines")), ("pet_windows", payload.get("pet_windows")), ("pet_windows_hidden", payload.get("pet_windows_hidden"))])
    blob = (json.dumps(artifact, indent=1, ensure_ascii=False) + "\n").encode("utf-8")
    open(os.path.join(RAW, fname), "wb").write(blob)
    hay = "\n".join(payload.get("address_lines") or []) + "\n" + json.dumps(payload.get("jsonld") or "")
    c_num = (re.match(r"\s*(\d+)", h["address"]) or [None, ""])[1]
    c_pc, c_ph = h["postal_code"], digits(h.get("phone"))
    parts = h["address"].split()
    street_ok = bool(c_num) and len(parts) > 1 and bool(re.search(r"\b" + re.escape(c_num) + r"\b[^\n]{0,40}" + re.escape(parts[1][:4]), hay, re.I))
    postal_ok = bool(re.search(r"\b" + c_pc + r"\b", hay))
    phone_ok = bool(c_ph) and c_ph in re.sub(r"[^0-9]", "", hay)
    binding = OrderedDict([("street_number_agrees", street_ok), ("postal_agrees", postal_ok), ("phone_agrees", phone_ok), ("bound", (street_ok and postal_ok) or (phone_ok and (postal_ok or street_ok)))])
    rd = read_windows(payload.get("pet_windows"), brand) or OrderedDict([("found", False)])
    src = "visible_text"
    if not rd.get("found") and payload.get("pet_windows_hidden"):
        rd2 = read_windows(payload.get("pet_windows_hidden"), brand)
        if rd2 and rd2.get("found"):
            rd, src = rd2, "hidden_text"
    row = OrderedDict([("identity_key", h["identity_key"]), ("canonical_name", h["canonical_name"]), ("brand", brand), ("lane", "ATTENDED"), ("requested_url", args.requested_url or payload.get("url")),
                       ("final_url", payload.get("url")), ("outcome", args.outcome or ("VALID" if rd.get("found") else "POLICY_NOT_FOUND")), ("identity_binding", binding), ("document_sha256", payload.get("html_sha256")),
                       ("text_sha256", payload.get("text_sha256")), ("artifact_file", fname), ("artifact_sha256", hashlib.sha256(blob).hexdigest()), ("captured_at", payload.get("captured_at")),
                       ("interaction", args.interaction or ""), ("reader", rd), ("reader_source", src), ("note", args.note or "")])
    upsert(doc, row)
    print(json.dumps(OrderedDict([("identity_key", h["identity_key"]), ("bound", binding["bound"]), ("pets_allowed", rd.get("pets_allowed")), ("quote", rd.get("pets_allowed_quote")), ("extraction", rd.get("extraction"))]), default=str)[:600])
    return 0


def cmd_classify(args):
    doc = load()
    have = {r["identity_key"]: r for r in doc["rows"]}
    out = []
    for h in targets():
        key = h["identity_key"]
        r = have.get(key)
        rec = OrderedDict([("identity_key", key), ("canonical_name", h["canonical_name"]), ("official_url", h.get("official_url") or ""), ("lane", (r or {}).get("lane"))])
        if r is None:
            url = h.get("official_url") or ""
            if url and any(x in host_of(url) for x in ATTENDED_HOSTS):
                cls, why = "CAPTURE_FAILED", "attended lane unavailable this order (browser extension dropped/permission prompt); first-party URL known: %s" % url
            elif not url:
                cls, why = "CAPTURE_FAILED", "no property page URL on the row (admitted from a brand locator); property page must be located first"
            else:
                cls, why = "CAPTURE_FAILED", "no read performed this order"
        elif r["lane"] == "STATIC":
            o = r.get("observation") or {}
            ext = o.get("extraction") or {}
            pa = ext.get("pets_allowed")
            grade = str((o.get("publication_grade") or {}).get("verdict") or (o.get("publication_grade") or {}).get("grade") or "")
            if r["outcome"] == "IDENTITY_MISMATCH":
                cls, why = "IDENTITY_MISMATCH", r.get("detail")
            elif r["outcome"] in ("ACCESS_DENIED", "NAVIGATION_FAILED", "CAPTURE_FAILED", "BLANK_PAGE", "UNEXPECTED_PAGE"):
                cls, why = "CAPTURE_FAILED", "%s: %s" % (r["outcome"], r.get("detail"))
            elif r["outcome"] == "UNHYDRATED":
                cls, why = "CAPTURE_FAILED", "static lane cannot read it: the policy region is a client-rendered template; attended lane needed (wyndhamhotels.com is not permitted in the browser extension this session)"
            elif r["outcome"] == "POLICY_NOT_FOUND":
                cls, why = "POLICY_NOT_FOUND", r.get("detail")
            elif pa is not None and grade.endswith("CONFIRMED") and all(len((e.get("quote") or "").split()) <= 2 for e in (o.get("evidence") or [])):
                cls, why = "FOUNDER_EXCEPTION", "the only quote is a phrase (%s), marketing copy rather than a policy statement with terms; Wyndham injects the real policy client-side" % ", ".join(repr(e.get("quote")) for e in (o.get("evidence") or []))
            elif pa is True and grade.endswith("CONFIRMED"):
                cls, why = "CLEAN_PET_FRIENDLY", "static first-party capture, publication grade"
            elif pa is False and grade.endswith("CONFIRMED"):
                cls, why = "CLEAN_VERIFIED_NO_PETS", "static first-party capture, publication grade"
            elif pa is None:
                cls, why = "SOURCE_SILENT", "block found but no pets statement"
            else:
                cls, why = "FOUNDER_EXCEPTION", "policy read but not publication grade: %s" % o.get("refusal_reason")
        else:
            rd = r.get("reader") or {}
            pa = rd.get("pets_allowed")
            bound = (r.get("identity_binding") or {}).get("bound")
            if r.get("outcome") == "IDENTITY_MISMATCH" or not bound:
                cls, why = "IDENTITY_MISMATCH", "page's own address does not bind to the admitted premises"
            elif r.get("outcome") == "CAPTURE_FAILED":
                cls, why = "CAPTURE_FAILED", r.get("note") or r.get("interaction")
            elif rd.get("contradictions"):
                cls, why = "SOURCE_CONTRADICTORY", "; ".join(str(c) for c in rd["contradictions"])[:200]
            elif not rd.get("found"):
                cls, why = ("SOURCE_SILENT", "page(s) read; no pet or animal policy statement") if r.get("note", "").startswith("SILENT") else ("POLICY_NOT_FOUND", "no bounded policy block on the page(s) read")
            elif rd.get("brand_generic"):
                cls, why = "FOUNDER_EXCEPTION", "block is brand-generic copy, not this property's policy"
            elif pa is True and r.get("reader_source") == "visible_text":
                cls, why = "CLEAN_PET_FRIENDLY", "attended first-party capture; identity bound on street+postal; property policy sentence quoted"
            elif pa is False and r.get("reader_source") == "visible_text":
                cls, why = "CLEAN_VERIFIED_NO_PETS", "attended first-party capture; identity bound; refusal sentence quoted"
            elif pa in (True, False):
                cls, why = "FOUNDER_EXCEPTION", "policy read only from collapsed (hidden) page text: %s" % ("pets allowed" if pa else "no pets")
            elif rd.get("service_animal_quote"):
                cls, why = "SOURCE_SILENT", "only service-animal language; no ordinary pet statement"
            else:
                cls, why = "SOURCE_SILENT", "block found but no pets statement"
        rec["classification"], rec["why"] = cls, why
        if r:
            rec["evidence"] = OrderedDict([("document_sha256", r.get("document_sha256")), ("artifact", r.get("artifact_file") or r.get("artifact_dir")), ("final_url", r.get("final_url")),
                                           ("quote", (r.get("reader") or {}).get("pets_allowed_quote") or ((r.get("observation") or {}).get("evidence") or [{}])[0].get("quote") if r.get("observation") else (r.get("reader") or {}).get("pets_allowed_quote")),
                                           ("extraction", (r.get("reader") or {}).get("extraction") or ((r.get("observation") or {}).get("extraction")))])
        out.append(rec)
    doc["classification"] = out
    doc["classification_counts"] = OrderedDict(sorted(Counter(x["classification"] for x in out).items()))
    doc["rows_attempted"] = len(have)
    doc["targets"] = len(out)
    write_json(RESULTS, doc)
    print("attempted", len(have), "of", len(out), dict(doc["classification_counts"]))
    for x in out:
        print(" ", x["classification"], "|", x["identity_key"][:40], "|", (x["why"] or "")[:90])
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("run-static")
    s.add_argument("--refetch", action="store_true")
    a = sub.add_parser("ingest-attended")
    a.add_argument("--identity-key", required=True)
    a.add_argument("--payload", required=True)
    a.add_argument("--requested-url", default="")
    a.add_argument("--interaction", default="")
    a.add_argument("--note", default="")
    a.add_argument("--outcome", default="")
    sub.add_parser("classify")
    args = ap.parse_args(argv)
    return {"run-static": cmd_run_static, "ingest-attended": cmd_ingest_attended, "classify": cmd_classify}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
