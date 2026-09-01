"""PTF-CLEVELAND-AKRON-CANTON-HARDENED-REVALIDATION-001 -- Phase 8.

Zero-cost routing recovery for every Cleveland-Akron-Canton row the phase-7
rebuild put in ROUTING_REPAIR_FIRST (plus any row whose static capture was
refused and whose route is therefore in question). Search order, exactly as
the order states it:

  1. an owned artifact whose page bound to this identity
  2. a URL nested inside the census / manifest / routing-repair / work-browser
     evidence objects
  3. routing history (the shard, including retired rows -- never reused
     when the retirement reason is a lapsed or poisoned domain)
  4/5. robots.txt + sitemap children  -> the phase-3 brand-directory harvest
  6/7. first-party brand directory / property finder -> the same harvest
  8. deterministic property-code route (only where a code is known)
  9. physical binding: the candidate page's OWN street number / postal /
     telephone against the census row, read statically

ROUTING_CONFIRMED requires a physical signal. A brand-parent host is never
enough on its own. Poisoned routes are preserved as history and never sent
to capture. No paid provider is called; nothing is written to authority.
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
import urllib.error
import urllib.request
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.brightdata import policy_surface as PS  # noqa: E402
from scripts.pettripfinder.discovery import identity_dedup as DEDUP  # noqa: E402
from scripts.pettripfinder.discovery.duplicates import normalize_phone  # noqa: E402
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key  # noqa: E402

WORK_ORDER = "PTF-CLEVELAND-AKRON-CANTON-HARDENED-REVALIDATION-001"
MARKET_ID = "cleveland-akron-canton-oh"
SCHEMA = "ptf-zero-cost-routing-recovery/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
AUTH = os.path.join(PKG, "markets", "authority", MARKET_ID)
REPORTS = os.path.join(PKG, "markets", "reports")
CACHE = os.path.join(_DASH, "data", "discovery", f"{MARKET_ID.replace('-', '_')}_routing_008", "pages")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
SPACING = 2.0
POISON_MARKERS = re.compile(r"lapsed|hugedomains|for sale|gambling|parked|expired|casino|redirects to an online", re.I)
ATTENDED_HOSTS = ("hilton.com", "marriott.com", "ihg.com", "choicehotels.com", "bestwestern.com", "radissonhotels", "redroof.com",
                  "extendedstayamerica.com", "hyatt.com", "sonesta.com")
BRANDS = [
    ("MARRIOTT", r"marriott|courtyard|residence inn|springhill|fairfield|towneplace|ac hotel|aloft|westin|sheraton|moxy|element"),
    ("HILTON", r"hilton|hampton|embassy suites|homewood|home2|doubletree|tru by|tapestry|canopy"),
    ("IHG", r"holiday inn|crowne plaza|staybridge|candlewood|even hotel|avid|intercontinental|kimpton|hotel indigo"),
    ("CHOICE", r"comfort inn|comfort suites|quality inn|sleep inn|clarion|cambria|mainstay|suburban|econo lodge|rodeway|woodspring"),
    ("WYNDHAM", r"wyndham|baymont|days inn|super 8|ramada|travelodge|la quinta|microtel|howard johnson|hawthorn|americinn|knights inn"),
    ("ESA", r"extended stay america"), ("BEST_WESTERN", r"best western|surestay"), ("MOTEL6", r"motel 6|studio 6"),
    ("RED_ROOF", r"red roof"), ("SONESTA", r"sonesta"), ("RADISSON", r"radisson|country inn"), ("DRURY", r"drury"), ("HYATT", r"hyatt"), ("MAGNUSON", r"magnuson"),
]


def brand_of(name):
    n = name.lower()
    for fam, rx in BRANDS:
        if re.search(rx, n):
            return fam
    return "INDEPENDENT"


def host_of(url):
    m = re.match(r"https?://([^/]+)", url or "")
    return m.group(1).lower().replace("www.", "") if m else ""


def read_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def as_plain(obj):
    if dataclasses.is_dataclass(obj):
        return {k: as_plain(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, (list, tuple)):
        return [as_plain(x) for x in obj]
    if isinstance(obj, dict):
        return {k: as_plain(v) for k, v in obj.items()}
    return obj


def get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*", "Accept-Language": "en-US,en;q=0.9"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.geturl(), r.read()
    except urllib.error.HTTPError as e:
        return e.code, url, b""
    except Exception as e:  # noqa: BLE001
        return "ERR:" + type(e).__name__, url, b""


def fetch_cached(url, stats):
    os.makedirs(CACHE, exist_ok=True)
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()
    meta_p = os.path.join(CACHE, key + ".json")
    html_p = os.path.join(CACHE, key + ".html")
    if os.path.exists(meta_p):
        meta = read_json(meta_p)
    else:
        time.sleep(SPACING)
        st, final, body = get(url)
        stats["requests"] += 1
        meta = {"url": url, "status": st, "final_url": final, "bytes": len(body)}
        if body:
            open(html_p, "wb").write(body)
        json.dump(meta, open(meta_p, "w", encoding="utf-8"))
    html = open(html_p, "rb").read().decode("utf-8", "replace") if os.path.exists(html_p) else ""
    return meta, html


def digits(v):
    return re.sub(r"[^0-9]", "", v or "")[-10:]


def bind(html, final_url, crow, brand):
    """Physical binding of a page to a census row: street number+postal, or phone."""
    title_m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    title = " ".join(title_m.group(1).split()) if title_m else ""
    try:
        sig = as_plain(PS.read_identity(html, final_url=final_url, title=title, brand=brand))
    except Exception as exc:  # noqa: BLE001
        sig = {"error": repr(exc)}
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    c_street = crow.get("address") or ""
    c_num = (re.match(r"\s*(\d+)", c_street) or [None, ""])[1] if c_street else ""
    c_postal = (crow.get("postal_code") or "")[:5]
    c_phone = digits(crow.get("phone") or "")
    page_num = (re.match(r"\s*(\d+)", sig.get("street") or sig.get("street_address") or "") or [None, ""])[1]
    parts = c_street.split()
    street_ok = bool(c_num) and (page_num == c_num or (len(parts) > 1 and bool(re.search(r"\b" + re.escape(c_num) + r"\b[^\n]{0,40}" + re.escape(parts[1][:4]), text, re.I))))
    postal_ok = bool(c_postal) and ((sig.get("postal_code") or "")[:5] == c_postal or bool(re.search(r"\b" + c_postal + r"\b", text)))
    phone_ok = bool(c_phone) and (digits(sig.get("telephone") or sig.get("phone") or "") == c_phone or c_phone in re.sub(r"[^0-9]", "", text))
    name_ok = DEDUP.names_compatible(crow["canonical_name"], sig.get("name") or title or "") if (sig.get("name") or title) else False
    soft404 = bool(re.search(r"<title[^>]*>\s*(search results|hotels? in|find hotels|page not found)", html, re.I))
    bound = (street_ok and postal_ok) or (phone_ok and (postal_ok or street_ok))
    return OrderedDict([("title", title[:140]), ("page_name", sig.get("name")), ("page_street", sig.get("street") or sig.get("street_address")),
                        ("page_postal", sig.get("postal_code")), ("page_phone", sig.get("telephone") or sig.get("phone")),
                        ("street_number_agrees", street_ok), ("postal_agrees", postal_ok), ("phone_agrees", phone_ok), ("names_compatible", name_ok),
                        ("soft_404_suspected", soft404), ("bound", bound and not soft404)])


def locality_tokens(crow):
    toks = set()
    for v in (crow.get("city") or "", crow.get("canonical_name") or ""):
        toks.update(re.findall(r"[a-z0-9]+", v.lower()))
    return toks - {"inn", "hotel", "suites", "the", "and", "by", "of", "at", "oh", "ohio"}


def build(args) -> OrderedDict:
    census = {r["identity_key"]: r for r in read_json(os.path.join(PKG, "identity_census", f"{MARKET_ID}.json"))["hotels"]}
    routing = read_json(os.path.join(AUTH, "identity_routing.json"))["routes"]
    routing_by_key = {r["hotel_ref"]["identity_key"]: r for r in routing}
    rebuild = read_json(os.path.join(REPORTS, f"{MARKET_ID.replace('-', '_')}_unresolved_rebuild_007.json"))
    replay = read_json(os.path.join(REPORTS, f"{MARKET_ID.replace('-', '_')}_evidence_replay_006.json"))
    manifest = {ptf_identity_key(i["canonical_name"]): i for i in read_json(os.path.join(PKG, "cleveland_unresolved_manifest.json"))["items"]}
    rr = {r["identity_key"]: r for r in read_json(os.path.join(PKG, "cleveland_routing_repair_001_results.json"))["results"]}
    wb = read_json(os.path.join(PKG, "cleveland_work_browser_pass_001.json"))
    wb_by_key = {}
    for it in wb.get("items", []):
        k = ptf_identity_key(it.get("canonical_name") or it.get("normalized_name") or "")
        if k:
            wb_by_key[k] = it
    harvest_path = os.path.join(REPORTS, f"{MARKET_ID.replace('-', '_')}_brand_directory_harvest_003.json")
    harvest = read_json(harvest_path)["candidates"] if os.path.exists(harvest_path) else []
    static_path = os.path.join(REPORTS, f"{MARKET_ID.replace('-', '_')}_free_static_capture_009.json")
    static_rows = {r["identity_key"]: r for r in read_json(static_path)["rows"]} if os.path.exists(static_path) else {}
    replay_by_key = {}
    for rec in replay["records"]:
        replay_by_key.setdefault(rec["identity_key"], []).append(rec)

    targets = [r for r in rebuild["rows"] if r["lane"] == "ROUTING_REPAIR_FIRST"]
    if args.identity_keys:
        targets += [OrderedDict([("identity_key", k), ("canonical_name", census[k]["canonical_name"]), ("lane", "REQUESTED")]) for k in args.identity_keys if k in census]
    stats = {"requests": 0}
    rows = []
    recovered = []
    for t in targets:
        key = t["identity_key"]
        crow = census[key]
        fam = brand_of(crow["canonical_name"])
        trace = []
        candidates = []  # (step, url, note)
        # 1. owned artifacts bound to this identity
        for rec in replay_by_key.get(key, []):
            ident = rec.get("identity", {})
            if (ident.get("confirmed") or (ident.get("physical_binding") or {}).get("bound")) and rec.get("final_url"):
                candidates.append(("1_OWNED_ARTIFACT", rec["final_url"], rec["artifact_file"]))
        # 2. nested URLs
        for src, u in (("census.official_url", crow.get("official_url")), ("manifest.official_url", (manifest.get(key) or {}).get("official_url")),
                       ("routing_repair.new_candidate_url", (rr.get(key) or {}).get("new_candidate_url")), ("routing_repair.final_url", (rr.get(key) or {}).get("final_url")),
                       ("work_browser.source_url", (wb_by_key.get(key) or {}).get("source_url"))):
            if u and u.startswith("http"):
                candidates.append(("2_NESTED_URL:" + src, u, ""))
        # 3. routing history
        rt = routing_by_key.get(key)
        if rt:
            note = rt.get("notes") or ""
            if rt["status"] == "ROUTING_CONFIRMED":
                candidates.append(("3_ROUTING_HISTORY", rt["official_property_url"], "status ROUTING_CONFIRMED"))
            elif POISON_MARKERS.search(note):
                trace.append("routing history holds a POISONED route %s -- preserved, never queued" % rt["official_property_url"])
            else:
                candidates.append(("3_ROUTING_HISTORY_" + rt["status"], rt["official_property_url"], note[:120]))
        # 4-7. sitemap / brand directory harvest (free families only)
        toks = locality_tokens(crow)
        for c in harvest:
            if c["family"] != fam:
                continue
            u = c["url"].lower()
            page = c.get("page") or {}
            ident = page.get("identity") or {}
            postal_hit = (ident.get("postal_code") or "")[:5] == (crow.get("postal_code") or "")[:5]
            phone_hit = digits(ident.get("telephone") or ident.get("phone") or "") == digits(crow.get("phone") or "") and bool(digits(crow.get("phone") or ""))
            tok_hit = any(tok in u for tok in toks if len(tok) > 3)
            if postal_hit or phone_hit or tok_hit:
                candidates.append(("4_7_BRAND_SITEMAP_DIRECTORY", c["url"], "postal" if postal_hit else "phone" if phone_hit else "locality-token"))
        if fam != "INDEPENDENT" and not any(c[0].startswith("4_7") for c in candidates):
            trace.append("brand family %s: no sitemap/directory candidate (family refused a plain client or holds no page for this locality)" % fam)
        # 8. deterministic property-code route
        code = DEDUP.property_code({"official_url": crow.get("official_url") or ""})
        if code:
            trace.append("property code %s known from census URL" % code)
        # 9. physical binding of each distinct candidate
        seen = set()
        outcome = None
        for step, url, note in candidates:
            if url in seen:
                continue
            seen.add(url)
            host = host_of(url)
            entry = OrderedDict([("step", step), ("url", url), ("note", note)])
            if any(h in host for h in ATTENDED_HOSTS):
                entry["binding"] = "HOST_REFUSES_PLAIN_CLIENT -- route proposed, attended binding required"
                entry["status"] = "ROUTE_PROPOSED_UNBOUND"
            else:
                meta, html = fetch_cached(url, stats)
                entry["http_status"] = meta.get("status")
                entry["final_url"] = meta.get("final_url")
                if meta.get("status") == 200 and html:
                    b = bind(html, meta.get("final_url") or url, crow, fam)
                    entry["binding"] = b
                    if b["bound"]:
                        entry["status"] = "ROUTING_CONFIRMED"
                    elif b["soft_404_suspected"]:
                        entry["status"] = "SOFT_404"
                    elif b["names_compatible"]:
                        entry["status"] = "NAME_ONLY_NOT_CONFIRMED"
                    else:
                        entry["status"] = "PAGE_DOES_NOT_BIND"
                else:
                    entry["status"] = "UNREACHABLE_PLAIN_CLIENT"
            trace.append(entry)
            if entry["status"] == "ROUTING_CONFIRMED" and outcome is None:
                outcome = entry
        if outcome is not None:
            state = "ROUTING_CONFIRMED"
            recovered.append(OrderedDict([("identity_key", key), ("canonical_name", crow["canonical_name"]), ("url", outcome["url"]), ("status", "ROUTING_CONFIRMED"),
                                          ("recovered_by", outcome["step"]), ("binding", outcome.get("binding")), ("brand", fam)]))
        elif any(isinstance(e, dict) and e.get("status") == "ROUTE_PROPOSED_UNBOUND" for e in trace):
            state = "ROUTE_PROPOSED_ATTENDED_BINDING_REQUIRED"
        elif fam == "INDEPENDENT" and not candidates:
            state = "NO_FREE_ROUTE_INDEPENDENT_PAID_DISCOVERY_REQUIRED"
        elif fam != "INDEPENDENT" and not any(c[0].startswith("4_7") for c in candidates):
            state = "NO_FREE_ROUTE_BRAND_DIRECTORY_REFUSED"
        else:
            state = "CANDIDATES_DID_NOT_BIND"
        rows.append(OrderedDict([("identity_key", key), ("canonical_name", crow["canonical_name"]), ("brand", fam), ("city", crow.get("city")), ("postal_code", crow.get("postal_code")),
                                 ("phase7_lane", t.get("lane")), ("state", state), ("candidates_considered", len(seen)), ("trace", trace)]))

    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER), ("phase", "8 -- zero-cost routing recovery"), ("market_id", MARKET_ID), ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", stats["requests"]),
        ("rows", len(rows)), ("state_counts", OrderedDict(sorted(Counter(r["state"] for r in rows).items()))),
        ("routes_recovered", recovered), ("details", rows),
    ])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPORTS, f"{MARKET_ID.replace('-', '_')}_routing_recovery_008.json"))
    ap.add_argument("--identity-keys", nargs="*", default=None)
    args = ap.parse_args(argv)
    rep = build(args)
    with open(args.out, "wb") as fh:
        fh.write((json.dumps(rep, indent=1, ensure_ascii=False, default=str) + "\n").encode("utf-8"))
    print("written", os.path.relpath(args.out, _DASH))
    print("states:", dict(rep["state_counts"]), "recovered", len(rep["routes_recovered"]), "requests", rep["free_http_requests"])
    for r in rep["routes_recovered"]:
        print("  ROUTED", r["identity_key"], "->", r["url"], "via", r["recovered_by"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
