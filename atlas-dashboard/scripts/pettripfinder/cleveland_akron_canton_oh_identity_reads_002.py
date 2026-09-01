"""PTF-CLEVELAND-AKRON-CANTON-HARDENED-APPLICATION-002 -- Phase 4 (ruling E).

ONE zero-cost first-party identity read per TRUE_MISSING premises (Order 001
reconciliation) plus the Marriott coded-directory leads that matched nothing.

    cohort           build the read cohort: best free first-party URL per row
                     (owned page > first-party sitemap/directory > OSM website)
    run-static       one HTTPS GET per row whose host answers a plain client;
                     read the page's OWN name/street/postal/phone/code
    ingest-attended  one attended Chrome payload (same shape as 009b)
    classify         compare every read against the pinned census, the shadow
                     census, exclusions, live authority and every other
                     market's census; classify:
                       CONFIRMED_TRUE_MISSING / ALREADY_REGISTERED_ALIAS /
                       DUPLICATE_OF_EXISTING / REBRAND_SUCCESSOR /
                       SAME_CAMPUS_DISTINCT_ENTITY / OUTSIDE_MARKET /
                       CLOSED_OR_CONVERTED / IDENTITY_UNRESOLVED
                     plus GEOGRAPHY_FOUNDER_HOLD (ruling G) as an overlay.

No paid provider. Nothing is admitted here; phase 5 admits.
"""
from __future__ import annotations

import argparse
import dataclasses
import glob
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
from scripts.pettripfinder.discovery.duplicates import normalize_phone, normalize_street  # noqa: E402
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key  # noqa: E402

WORK_ORDER = "PTF-CLEVELAND-AKRON-CANTON-HARDENED-APPLICATION-002"
MARKET_ID = "cleveland-akron-canton-oh"
M = MARKET_ID.replace("-", "_")
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
AUTH = os.path.join(PKG, "markets", "authority", MARKET_ID)
REPORTS = os.path.join(PKG, "markets", "reports")
COHORT = os.path.join(REPORTS, f"{M}_identity_read_cohort_002.json")
READS = os.path.join(REPORTS, f"{M}_identity_reads_002.json")
CACHE = os.path.join(_DASH, "data", "discovery", f"{M}_identity_reads_002")
RAW = os.path.join(_DASH, "data", "worker_runs", "pettripfinder", "cleveland-hardened-identity-reads-002", "raw")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
GEOGRAPHY_HOLD_POSTALS = {"44136", "44212", "44011", "44012", "44092", "44035", "44052", "44074", "44041", "44001"}
ATTENDED_HOSTS = ("hilton.com", "marriott.com", "ihg.com", "choicehotels.com", "bestwestern.com", "radissonhotels", "redroof.com", "extendedstayamerica.com", "hyatt.com", "sonesta.com")
THIRD_PARTY = ("booking.com", "expedia", "hotels.com", "tripadvisor", "facebook.com", "yelp.com", "google.com")
CORE_TOKENS = ("cleveland", "akron", "canton", "solon", "willoughby", "mentor", "independence", "beachwood", "westlake", "stow", "hudson", "streetsboro", "twinsburg", "macedonia", "richfield", "fairlawn", "olmsted", "middleburg", "lakewood", "mayfield", "massillon", "alliance", "painesville", "oakwood", "brooklyn", "parma", "fairview", "randall")
BRANDS = [("MARRIOTT", r"marriott|courtyard|residence inn|springhill|fairfield|towneplace|ac hotel|aloft|westin|sheraton|moxy|element|ritz|autograph|tribute"),
          ("HILTON", r"hilton|hampton|embassy suites|homewood|home2|doubletree|tru by|tapestry|canopy"),
          ("IHG", r"holiday inn|crowne plaza|staybridge|candlewood|even hotel|avid|intercontinental|kimpton|hotel indigo"),
          ("CHOICE", r"comfort inn|comfort suites|quality inn|sleep inn|clarion|cambria|mainstay|suburban|econo lodge|rodeway|woodspring|country inn"),
          ("WYNDHAM", r"wyndham|baymont|days inn|super 8|ramada|travelodge|la quinta|microtel|howard johnson|hawthorn|americinn|knights inn"),
          ("ESA", r"extended stay america"), ("BEST_WESTERN", r"best western|surestay"), ("MOTEL6", r"motel 6|studio 6"), ("RED_ROOF", r"red roof"),
          ("SONESTA", r"sonesta"), ("RADISSON", r"radisson|park inn"), ("DRURY", r"drury"), ("HYATT", r"hyatt"), ("MAGNUSON", r"magnuson")]


def brand_of(name):
    n = (name or "").lower()
    for fam, rx in BRANDS:
        if re.search(rx, n):
            return fam
    return "INDEPENDENT"


def read_json(p):
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as fh:
        fh.write((json.dumps(d, indent=1, ensure_ascii=False, default=str) + "\n").encode("utf-8"))


def host_of(url):
    m = re.match(r"https?://([^/]+)", url or "")
    return m.group(1).lower().replace("www.", "") if m else ""


def digits(v):
    return re.sub(r"[^0-9]", "", v or "")[-10:]


def house_number(addr):
    m = re.match(r"\s*(\d+)", addr or "")
    return m.group(1) if m else ""


def tokens(s):
    return set(re.findall(r"[a-z0-9]+", (s or "").lower())) - {"by", "the", "and", "of", "inn", "hotel", "suites", "hotels", "an"}


def as_plain(obj):
    if dataclasses.is_dataclass(obj):
        return {k: as_plain(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, (list, tuple)):
        return [as_plain(x) for x in obj]
    if isinstance(obj, dict):
        return {k: as_plain(v) for k, v in obj.items()}
    return obj


# --------------------------------------------------------------------------- cohort
def cmd_cohort(args):
    recon = read_json(os.path.join(REPORTS, f"{M}_shadow_reconciliation_004.json"))
    harvest = read_json(os.path.join(REPORTS, f"{M}_brand_directory_harvest_003.json"))["candidates"]
    rows = []
    for r in recon["results"]:
        if r["classification"] != "TRUE_MISSING_IDENTITY":
            continue
        fam = r["brand_family"]
        name = r["name"]
        num = house_number(r["address"])
        cands = []
        # (b) a first-party brand page whose own identity already names the premises
        for c in harvest:
            page = c.get("page") or {}
            ident = page.get("identity") or {}
            if page.get("status") == 200 and (ident.get("postal_code") or "")[:5] == r["postal_code"] and house_number(ident.get("street") or ident.get("street_address") or "") == num and num:
                cands.append(("FIRST_PARTY_PAGE_PREMISES_MATCH", c["url"]))
        # (c) a brand directory / sitemap URL whose slug names the property (family + locality/name tokens)
        for c in harvest:
            if c["family"] != fam:
                continue
            path = c["url"].lower()
            slug = re.sub(r"/overview/?$", "", c["url"].rstrip("/")).rsplit("/", 1)[-1].lower()
            st = set(slug.replace("-", " ").split())
            nt = tokens(name)
            city_tok = next((t for t in re.findall(r"[a-z]+", (r.get("city") or "").lower()) if len(t) >= 4 and t not in ("north", "south", "east", "west", "heights", "township", "village")), "")
            # the URL must name the LOCALITY (city token in the path) and share two name tokens; a brand token alone never matches
            if city_tok and city_tok in path and len(nt & st) >= 2:
                cands.append(("FIRST_PARTY_DIRECTORY_SLUG_MATCH", c["url"]))
        # (d) the OSM website when it is first-party
        w = r.get("website_url") or ""
        if w and not any(t in w.lower() for t in THIRD_PARTY):
            cands.append(("OSM_WEBSITE_FIRST_PARTY", w))
        seen, uniq = set(), []
        for s, u in cands:
            if u not in seen:
                seen.add(u)
                uniq.append(OrderedDict([("source", s), ("url", u), ("method", "ATTENDED" if any(h in host_of(u) for h in ATTENDED_HOSTS) else "STATIC")]))
        rows.append(OrderedDict([
            ("cohort_id", "TM-%03d" % (len(rows) + 1)), ("origin", "TRUE_MISSING_IDENTITY"), ("name", name), ("proposed_identity_key", r["identity_key"]), ("brand_family", fam),
            ("premises", OrderedDict([("address", r["address"]), ("city", r["city"]), ("postal_code", r["postal_code"]), ("phone", r["phone"])])),
            ("corridor", r.get("corridor")), ("geography_hold", r["postal_code"] in GEOGRAPHY_HOLD_POSTALS),
            ("first_party_directory_listing", r.get("first_party_directory_listing")), ("candidates", uniq),
            ("read_method", uniq[0]["method"] if uniq else "DIRECTORY_LOOKUP_ATTENDED"),
        ]))
    census_names = [h["canonical_name"] for h in read_json(os.path.join(PKG, "identity_census", f"{MARKET_ID}.json"))["hotels"]]
    seen_codes = set()
    leads = []
    for l in (recon.get("coded_brand_directory_listings") or {}).get("listings_matching_nothing", []):
        nm = l["slug_name"]
        if not any(t in nm for t in CORE_TOKENS) or l["code"] in seen_codes:
            continue
        seen_codes.add(l["code"])
        brand_words = ("courtyard", "residence", "towneplace", "fairfield", "springhill", "ac", "aloft", "westin", "sheraton", "ritz", "blu", "autograph", "tribute", "moxy", "element")
        lead_brand = next((t for t in tokens(nm) if t in brand_words), "")
        locality = tokens(nm) - set(brand_words) - {"cleveland", "north", "south", "east", "west", "a", "portfolio", "collection", "hotel", "akron"}
        alias_of = next((cn for cn in census_names if lead_brand and lead_brand in tokens(cn) and locality and locality <= tokens(cn)), None)
        if not alias_of and "autograph" in nm and any(tokens(cn) >= locality and "autograph" in tokens(cn) | {"cleveland"} for cn in census_names if locality):
            alias_of = next((cn for cn in census_names if locality <= tokens(cn) and "hotel" in tokens(cn) and "cleveland" in tokens(cn)), None)
        if alias_of:
            leads.append(OrderedDict([("lead", nm), ("code", l["code"]), ("disposition", "ALIAS_LEAD_NO_READ"), ("registered_row", alias_of), ("url", l["url"])]))
            continue
        if any(t in nm for t in ("youngstown", "sandusky", "new philadelphia", "medina")):
            leads.append(OrderedDict([("lead", nm), ("code", l["code"]), ("disposition", "OUTSIDE_MARKET_NO_READ"), ("url", l["url"])]))
            continue
        if any(t in nm for t in ("elyria", "avon", "lorain", "oberlin", "strongsville", "brunswick", "wickliffe", "geneva")):
            leads.append(OrderedDict([("lead", nm), ("code", l["code"]), ("disposition", "GEOGRAPHY_FOUNDER_HOLD_NO_READ"), ("url", l["url"])]))
            continue
        if sum(1 for r in rows if r["origin"] == "MARRIOTT_DIRECTORY_LEAD") >= 6:
            leads.append(OrderedDict([("lead", nm), ("code", l["code"]), ("disposition", "CAP_REACHED_NO_READ"), ("url", l["url"])]))
            continue
        rows.append(OrderedDict([
            ("cohort_id", "TM-%03d" % (len(rows) + 1)), ("origin", "MARRIOTT_DIRECTORY_LEAD"), ("name", nm.title()), ("proposed_identity_key", ptf_identity_key(nm)), ("brand_family", l["family"]),
            ("premises", OrderedDict([("address", ""), ("city", ""), ("postal_code", ""), ("phone", "")])), ("corridor", ""), ("geography_hold", any(t in nm for t in ("avon", "elyria", "sandusky", "medina"))),
            ("first_party_directory_listing", l), ("candidates", [OrderedDict([("source", "FIRST_PARTY_DIRECTORY_CODED_URL"), ("url", l["url"]), ("method", "ATTENDED")])]), ("read_method", "ATTENDED"),
        ]))
    doc = OrderedDict([("schema", "ptf-identity-read-cohort/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID), ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
                       ("rows", len(rows)), ("marriott_directory_leads_not_read", leads), ("by_method", OrderedDict(sorted(Counter(r["read_method"] for r in rows).items()))),
                       ("geography_holds", sum(1 for r in rows if r["geography_hold"])), ("cohort", rows)])
    write_json(COHORT, doc)
    print("cohort", len(rows), dict(doc["by_method"]), "geo holds", doc["geography_holds"])
    for r in rows:
        print(" ", r["cohort_id"], r["brand_family"], "|", r["name"][:40], "|", r["premises"]["postal_code"], "|", r["read_method"], "|", (r["candidates"][0]["url"] if r["candidates"] else "-")[:80])
    return 0


# --------------------------------------------------------------------------- reads
def get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*", "Accept-Language": "en-US,en;q=0.9"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.geturl(), r.read()
    except urllib.error.HTTPError as e:
        return e.code, url, b""
    except Exception as e:  # noqa: BLE001
        return "ERR:" + type(e).__name__, url, b""


def page_identity(html, final_url, brand):
    title_m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    title = " ".join(title_m.group(1).split()) if title_m else ""
    try:
        sig = as_plain(PS.read_identity(html, final_url=final_url, title=title, brand=brand))
    except Exception as exc:  # noqa: BLE001
        sig = {"error": repr(exc)}
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return OrderedDict([("title", title[:160]), ("name", sig.get("name_on_page") or sig.get("name")), ("street", sig.get("address_on_page") or sig.get("street") or sig.get("street_address")), ("locality", sig.get("locality") or sig.get("city")),
                        ("postal_code", (sig.get("postal_code") or "")[:5]), ("phone", sig.get("phone_on_page") or sig.get("telephone") or sig.get("phone")), ("property_code", sig.get("property_code_on_page") or sig.get("property_code")),
                        ("canonical_url", sig.get("canonical_url")),
                        ("jsonld_present", sig.get("jsonld_present")), ("soft_404", bool(re.search(r"<title[^>]*>\s*(search results|hotels? in|find hotels|page not found)", html, re.I))),
                        ("text_excerpt_address_lines", [ln for ln in re.findall(r"[^.]{0,80}\b\d{5}\b[^.]{0,20}", text)][:4])]), text


def load_reads():
    return read_json(READS) if os.path.exists(READS) else OrderedDict([("schema", "ptf-identity-reads/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID), ("provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", 0), ("reads", [])])


def upsert(doc, rec):
    doc["reads"] = [r for r in doc["reads"] if r["cohort_id"] != rec["cohort_id"]] + [rec]
    write_json(READS, doc)


def cmd_run_static(args):
    cohort = read_json(COHORT)["cohort"]
    doc = load_reads()
    done = {r["cohort_id"] for r in doc["reads"]}
    os.makedirs(CACHE, exist_ok=True)
    for row in cohort:
        if args.cohort_id and row["cohort_id"] != args.cohort_id:
            continue
        if row["cohort_id"] in done and not args.refetch and not args.url:
            continue
        cands = [c for c in row["candidates"] if c["method"] == "STATIC"]
        if args.url and args.cohort_id == row["cohort_id"]:
            cands = [OrderedDict([("source", "OPERATOR_SUPPLIED_FIRST_PARTY_URL"), ("url", args.url), ("method", "STATIC")])]
        if not cands:
            continue
        c = cands[0]
        time.sleep(2.0)
        st, final, body = get(c["url"])
        doc["free_http_requests"] += 1
        html = body.decode("utf-8", "replace") if body else ""
        sha = hashlib.sha256(body).hexdigest() if body else None
        if body:
            open(os.path.join(CACHE, hashlib.sha256(c["url"].encode()).hexdigest() + ".html"), "wb").write(body)
        rec = OrderedDict([("cohort_id", row["cohort_id"]), ("name", row["name"]), ("read_method", "STATIC"), ("url", c["url"]), ("url_source", c["source"]), ("http_status", st), ("final_url", final),
                           ("document_sha256", sha), ("read_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))])
        if st == 200 and html:
            ident, text = page_identity(html, final, row["brand_family"])
            rec["page_identity"] = ident
            rec["text_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
        upsert(doc, rec)
        print(" ", row["cohort_id"], st, row["name"][:40], "->", (rec.get("page_identity") or {}).get("street"), (rec.get("page_identity") or {}).get("postal_code"))
    return 0


def cmd_ingest_attended(args):
    cohort = {r["cohort_id"]: r for r in read_json(COHORT)["cohort"]}
    row = cohort[args.cohort_id]
    payload = read_json(args.payload)
    doc = load_reads()
    os.makedirs(RAW, exist_ok=True)
    fname = "%s-%s.json" % (args.cohort_id, re.sub(r"[^a-z0-9]+", "-", row["proposed_identity_key"]).strip("-"))
    artifact = OrderedDict([("schema", "ptf-attended-capture/2.1-text-windows"), ("work_order", WORK_ORDER), ("cohort_id", args.cohort_id), ("captured_at", payload.get("captured_at")),
                            ("requested_url", args.requested_url or payload.get("url")), ("final_url", payload.get("url")), ("title", payload.get("title")), ("capture_method", "attended_browser"),
                            ("interaction", args.interaction or ""), ("html_sha256", payload.get("html_sha256")), ("text_sha256", payload.get("text_sha256")), ("jsonld", payload.get("jsonld")),
                            ("address_lines", payload.get("address_lines")), ("pet_windows", payload.get("pet_windows"))])
    blob = (json.dumps(artifact, indent=1, ensure_ascii=False) + "\n").encode("utf-8")
    open(os.path.join(RAW, fname), "wb").write(blob)
    ld = payload.get("jsonld") or {}
    addr = ld.get("address") if isinstance(ld.get("address"), dict) else {}
    lines = " | ".join(payload.get("address_lines") or [])
    ident = OrderedDict([("title", payload.get("title")), ("name", ld.get("name") or args.page_name), ("street", addr.get("streetAddress") or args.page_street),
                         ("locality", addr.get("addressLocality") or args.page_city), ("postal_code", (addr.get("postalCode") or args.page_postal or (re.search(r"\b(44\d{3})\b", lines) or [None, ""])[1])[:5]),
                         ("phone", ld.get("telephone") or args.page_phone), ("property_code", ld.get("identifier") or args.property_code), ("jsonld_present", bool(ld)), ("soft_404", False),
                         ("text_excerpt_address_lines", payload.get("address_lines"))])
    rec = OrderedDict([("cohort_id", args.cohort_id), ("name", row["name"]), ("read_method", "ATTENDED"), ("url", args.requested_url or payload.get("url")), ("url_source", "ATTENDED"),
                       ("http_status", 200 if not args.outcome else args.outcome), ("final_url", payload.get("url")), ("document_sha256", payload.get("html_sha256")), ("text_sha256", payload.get("text_sha256")),
                       ("read_at", payload.get("captured_at")), ("artifact_file", fname), ("artifact_sha256", hashlib.sha256(blob).hexdigest()), ("page_identity", ident), ("note", args.note or "")])
    upsert(doc, rec)
    print(json.dumps(OrderedDict([("cohort_id", args.cohort_id), ("name", row["name"]), ("page", ident)]), default=str)[:600])
    return 0


# --------------------------------------------------------------------------- classify
def cmd_classify(args):
    cohort = read_json(COHORT)["cohort"]
    doc = load_reads()
    reads = {r["cohort_id"]: r for r in doc["reads"]}
    census = read_json(os.path.join(PKG, "identity_census", f"{MARKET_ID}.json"))["hotels"]
    shadow_p = os.path.join(PKG, "identity_census", "recensus", f"{MARKET_ID}.json")
    excl = {ptf_identity_key(e["canonical_name"]): e for e in read_json(os.path.join(AUTH, "hotel_exclusions.json"))["exclusions"]}
    policy = {p["identity_key"] for p in read_json(os.path.join(PKG, f"hotel_policy_facts_{MARKET_ID}.json"))["hotels"]}
    market = read_json(os.path.join(PKG, "markets", f"{MARKET_ID}.json"))
    corridor_postals = {pc for c in market["corridors"] for pc in (c.get("included_postal_codes") or [])}
    census_postals = {(h.get("postal_code") or "")[:5] for h in census}
    # other markets' censuses, for cross-market collision
    others = []
    for p in glob.glob(os.path.join(PKG, "identity_census", "*.json")):
        d = read_json(p)
        if isinstance(d, dict) and d.get("market_id") and d.get("market_id") != MARKET_ID:
            for h in d.get("hotels", []):
                others.append((d["market_id"], h))
    by_num, by_phone, by_url, by_key = {}, {}, {}, {}
    for h in census:
        by_key[h["identity_key"]] = h
        n = house_number(h.get("address"))
        if n and h.get("postal_code"):
            by_num.setdefault((n, h["postal_code"][:5]), []).append(h["identity_key"])
        ph = normalize_phone(h.get("phone") or "")
        if ph:
            by_phone.setdefault(ph, []).append(h["identity_key"])
        u = (h.get("official_url") or "").lower().rstrip("/")
        if u:
            by_url[re.sub(r"^https?://(www\.)?", "", u)] = h["identity_key"]
    results = []
    seen_premises = {}
    for row in cohort:
        rd = reads.get(row["cohort_id"])
        pi = (rd or {}).get("page_identity") or {}
        res = OrderedDict([("cohort_id", row["cohort_id"]), ("name", row["name"]), ("proposed_identity_key", row["proposed_identity_key"]), ("brand_family", row["brand_family"]),
                           ("premises_proposed", row["premises"]), ("read", OrderedDict([("method", (rd or {}).get("read_method")), ("url", (rd or {}).get("final_url") or (rd or {}).get("url")), ("http_status", (rd or {}).get("http_status")),
                                                                                          ("document_sha256", (rd or {}).get("document_sha256")), ("artifact_file", (rd or {}).get("artifact_file"))])), ("page_identity", pi)])
        signals = []
        if rd is None:
            cls, why = "IDENTITY_UNRESOLVED", "no free first-party page could be located for this premises (no owned page, no directory URL, no first-party website); a page read needs paid discovery or an operator lookup"
        elif isinstance(rd.get("http_status"), str) and rd["http_status"].startswith("CONVERTED"):
            cls, why = "CLOSED_OR_CONVERTED", "the brand's own locator no longer lists this property (%s); the property URL redirects to the locator" % (rd.get("note") or "")[:160]
        elif rd.get("http_status") != 200 or not pi:
            cls, why = "IDENTITY_UNRESOLVED", "the located page did not serve to a plain client (%s); attended read not yet performed" % rd.get("http_status")
        elif pi.get("soft_404"):
            slug_brand = brand_of(re.sub(r"[/-]", " ", rd.get("url") or ""))
            if rd.get("url_source") == "OPERATOR_SUPPLIED_FIRST_PARTY_URL":
                cls, why = "IDENTITY_UNRESOLVED", "the guessed brand slug is a soft 404 and the brand's Westlake locator renders client-side (browser permission not granted for this host); no page for this premises was located"
            elif rd.get("url_source") == "FIRST_PARTY_DIRECTORY_SLUG_MATCH" and brand_of(re.sub(r"[/-]", " ", (rd.get("url") or "").split("/")[-2] if (rd.get("url") or "").endswith("/overview") else (rd.get("url") or ""))) == brand_of(row["name"]) and not any(t in (rd.get("url") or "").lower() for t in ("wingate", "super 8", "ramada", "days inn", "la quinta", "baymont", "microtel", "travelodge") if t.replace(" ", "-") in (row["name"].lower().replace(" ", "-")) and t.replace(" ", "-") in (rd.get("url") or "").lower()):
                cls, why = "IDENTITY_UNRESOLVED", "the only directory lead was another property's delisted page; no page for this premises was located"
            else:
                cls, why = "CLOSED_OR_CONVERTED", "the brand page for this slug is a soft 404 (delisted)"
        else:
            p_num, p_pc, p_ph = house_number(pi.get("street")), (pi.get("postal_code") or "")[:5], digits(pi.get("phone"))
            page_name = pi.get("name") or pi.get("title") or ""
            own_num, own_pc = house_number(row["premises"]["address"]), row["premises"]["postal_code"]
            premises_agree = bool(p_num and p_pc and ((p_num == own_num and p_pc == own_pc) or not own_num))
            # who already holds this premises?
            hits = set()
            if p_num and p_pc and (p_num, p_pc) in by_num:
                hits |= set(by_num[(p_num, p_pc)])
                signals.append("STREET_NUMBER_AND_POSTAL")
            if p_ph and p_ph in by_phone:
                hits |= set(by_phone[p_ph])
                signals.append("TELEPHONE")
            fu = re.sub(r"^https?://(www\.)?", "", (rd.get("final_url") or "").lower().rstrip("/"))
            if fu and fu in by_url:
                hits.add(by_url[fu])
                signals.append("CANONICAL_URL")
            code = pi.get("property_code") or DEDUP.property_code({"official_url": rd.get("final_url") or ""})
            for k, h in by_key.items():
                if code and DEDUP.property_code({"official_url": h.get("official_url") or ""}) == code:
                    hits.add(k)
                    signals.append("PROPERTY_CODE")
            cross = [(mid, h["identity_key"]) for mid, h in others if p_num and p_pc and house_number(h.get("address")) == p_num and (h.get("postal_code") or "")[:5] == p_pc]
            res["cross_market_collisions"] = cross
            res["registered_rows_sharing_premises"] = sorted(hits)
            in_market = bool(p_pc and (p_pc in corridor_postals or p_pc in census_postals))
            res["in_market"] = in_market
            lodging = not re.search(r"\b(restaurant|bar|grill|apartments?|daycare|kennel)\b", page_name, re.I)
            if not p_num or not p_pc:
                cls, why = "IDENTITY_UNRESOLVED", "the page states no numbered street + postal of its own"
            elif own_num and p_num == own_num and p_pc != own_pc and sorted(p_pc) == sorted(own_pc):
                cls, why = "IDENTITY_UNRESOLVED", "street number %s agrees but the page states postal %s where the premises propose %s (digits transposed on the page); one more first-party source needed before admission" % (p_num, p_pc, own_pc)
            elif own_num and not premises_agree:
                held = [by_key[k]["canonical_name"] for k in hits]
                cls, why = "IDENTITY_UNRESOLVED", "the located page names a DIFFERENT building (%s %s%s) than the proposed premises (%s %s); the lead did not resolve" % (p_num, p_pc, (", registered as " + held[0]) if held else "", own_num, own_pc)
            elif hits:
                names = [by_key[k]["canonical_name"] for k in hits]
                compat = any(DEDUP.names_compatible(page_name, n) for n in names)
                fams = {brand_of(n) for n in names}
                if compat or brand_of(page_name) in fams:
                    cls, why = "ALREADY_REGISTERED_ALIAS", "the page's own premises are registered as %s (%s)" % (names[0], "+".join(sorted(set(signals))))
                elif "STREET_NUMBER_AND_POSTAL" in signals and brand_of(page_name) != "INDEPENDENT":
                    cls, why = "SAME_CAMPUS_DISTINCT_ENTITY", "same premises as %s under a different brand family; two hotels unless ruled otherwise" % names[0]
                else:
                    cls, why = "DUPLICATE_OF_EXISTING", "premises signal %s already registered as %s" % ("+".join(sorted(set(signals))), names[0])
            elif cross:
                cls, why = "OUTSIDE_MARKET", "premises registered in another market: %s" % cross[0][0]
            elif not in_market:
                cls, why = "OUTSIDE_MARKET", "page postal %s is outside every corridor and every registered postal" % p_pc
            elif not lodging:
                cls, why = "IDENTITY_UNRESOLVED", "the page names a non-lodging business"
            elif not premises_agree and own_num:
                cls, why = "IDENTITY_UNRESOLVED", "the page's premises (%s %s) differ from the proposed premises (%s %s); the lead does not resolve to the proposed building" % (p_num, p_pc, own_num, own_pc)
            elif (p_num, p_pc) in seen_premises:
                cls, why = "DUPLICATE_OF_EXISTING", "the same premises were already confirmed in this cohort as %s" % seen_premises[(p_num, p_pc)]
            else:
                cls, why = "CONFIRMED_TRUE_MISSING", "first-party page states name, numbered street, postal%s; no registered row in any market shares the premises" % (", phone" if p_ph else "")
                seen_premises[(p_num, p_pc)] = row["cohort_id"]
        geo_hold = row["geography_hold"] or ((pi.get("postal_code") or "")[:5] in GEOGRAPHY_HOLD_POSTALS)
        res["classification"] = cls
        res["why"] = why
        res["geography_hold"] = geo_hold
        if cls == "CONFIRMED_TRUE_MISSING" and geo_hold:
            res["admission"] = "GEOGRAPHY_FOUNDER_HOLD"
        elif cls == "CONFIRMED_TRUE_MISSING":
            res["admission"] = "ELIGIBLE_FOR_SHADOW_ADMISSION"
        else:
            res["admission"] = "NOT_ADMITTED"
        results.append(res)
    counts = OrderedDict(sorted(Counter(r["classification"] for r in results).items()))
    adm = OrderedDict(sorted(Counter(r["admission"] for r in results).items()))
    doc["classification"] = results
    doc["classification_counts"] = counts
    doc["admission_counts"] = adm
    doc["reads_attempted"] = len(reads)
    doc["cohort_size"] = len(cohort)
    write_json(READS, doc)
    print("reads attempted", len(reads), "of", len(cohort))
    print("classification:", dict(counts))
    print("admission:", dict(adm))
    for r in results:
        print(" ", r["cohort_id"], r["classification"], "|", r["name"][:38], "|", r["why"][:110])
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("cohort")
    s = sub.add_parser("run-static")
    s.add_argument("--refetch", action="store_true")
    s.add_argument("--cohort-id", default="")
    s.add_argument("--url", default="")
    a = sub.add_parser("ingest-attended")
    a.add_argument("--cohort-id", required=True)
    a.add_argument("--payload", required=True)
    a.add_argument("--requested-url", default="")
    a.add_argument("--interaction", default="")
    a.add_argument("--note", default="")
    a.add_argument("--outcome", default="")
    for f in ("page-name", "page-street", "page-city", "page-postal", "page-phone", "property-code"):
        a.add_argument("--" + f, default="")
    sub.add_parser("classify")
    args = ap.parse_args(argv)
    return {"cohort": cmd_cohort, "run-static": cmd_run_static, "ingest-attended": cmd_ingest_attended, "classify": cmd_classify}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
