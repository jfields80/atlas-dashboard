"""PTF-INDEPENDENT-POLICY-URL-DISCOVERY-014 -- is there a better URL to point at?

PTF-GENERIC-READER-FIRECRAWL-DIAGNOSTIC-013 found nine of eleven Milwaukee
independents pointed at a homepage or a contact page. Firecrawl fetched every
one successfully -- 200, hydrated, correct property -- and there was no pet
policy on those pages, because a homepage is not where a hotel writes one.

That is not a provider problem and not a reader problem. It is a URL problem,
and this work order measures whether the URL problem is solvable.

THE LADDER, AND WHY IT STOPS WHERE IT DOES
-------------------------------------------
Candidates come from the property's OWN page: its links, its anchors, its site
structure. Nothing is guessed. A conventional path like ``/pet-policy`` is not
tried merely because it often exists -- a URL must be discovered from evidence,
or the discovery rate measures the convention rather than the corpus.

Every candidate is scored by what the site itself calls it. A link whose path
or anchor text says ``dogs`` or ``pets`` outranks one that says ``faq``, which
outranks ``amenities``. The ordering is fixed here, before any page is fetched.

FIRST-PARTY IS A CLASSIFICATION, NOT AN ASSUMPTION
---------------------------------------------------
Three of these hotels are operated by Marcus Hotels, and their pages link to
marcushotels.com. An operator domain is not automatically first-party evidence
for one property: a corporate privacy policy binds nothing about pets at the
Pfister. So each candidate is classified SAME_DOMAIN, OPERATOR_DOMAIN or
THIRD_PARTY, and only a same-domain page -- or an operator page that names the
property explicitly -- can become POLICY_URL_FOUND.

WHAT THIS WORK ORDER MAY NOT DO
--------------------------------
It measures. It does not edit a single source URL, touch routes.json, change
the reader, or publish anything. Neither Bright Data provider is importable
from here and a test asserts it.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import firecrawl_capture as FC          # noqa: E402
from scripts.pettripfinder.acquisition import generic_reader_diagnostic_013 as D13  # noqa: E402
from scripts.pettripfinder.brightdata import unlocker_capture as UC            # noqa: E402

WORK_ORDER = "PTF-INDEPENDENT-POLICY-URL-DISCOVERY-014"
MARKET = "milwaukee-wi"
REPORTS = REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
RUN_ROOT = REPO / "data" / "acquisition" / "independent-url-discovery-014"
CACHE_013 = (REPO / "data" / "acquisition" / "generic-reader-diagnostic-013"
             / "generic-diagnostic-013")

EXPECTED_COHORT = 11

#: How many candidates a property may cost. Fixed before the run so the spend
#: is bounded and the same for every property -- a property that gets more
#: attempts would report a better discovery rate for that reason alone.
MAX_CANDIDATES_PER_PROPERTY = 3

#: Discovery ladder. Higher scores are tried first. Ordered by how specifically
#: the SITE ITSELF names the surface, not by what we hope to find there.
_LADDER: Tuple[Tuple[int, re.Pattern], ...] = (
    (100, re.compile(r"pet-?polic|pets?-?friendly|/pets?/|/dogs?/|dog-?friendly",
                     re.IGNORECASE)),
    (90, re.compile(r"\bpets?\b|\bdogs?\b", re.IGNORECASE)),
    (70, re.compile(r"hotel-?polic|property-?polic|hotel-?information"
                    r"|guest-?information|house-?rules|reservations?-?polic",
                    re.IGNORECASE)),
    (60, re.compile(r"faqs?\b|frequently-?asked", re.IGNORECASE)),
    (40, re.compile(r"amenit|accommodation|services", re.IGNORECASE)),
    (20, re.compile(r"\bterms\b|\brules\b|guest-?info", re.IGNORECASE)),
)

#: Never a policy surface, however well it scores on a keyword.
_EXCLUDE = re.compile(
    r"privacy|terms-of-use|cookie|careers|gift-?card|press|blog|sitemap"
    r"|/book|reserv(?:ation)?s?\.|login|account|instagram|facebook|twitter",
    re.IGNORECASE)

_LINK_RE = re.compile(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                      re.IGNORECASE | re.DOTALL)


def cohort() -> List[Dict]:
    """The eleven remaining Milwaukee independents, derived not listed."""
    rows = [r for r in D13.generic_universe() if r["class"] == "INDEPENDENT"]
    if len(rows) != EXPECTED_COHORT:
        raise SystemExit("ABORT: expected %d independents, derived %d"
                         % (EXPECTED_COHORT, len(rows)))
    return sorted(rows, key=lambda r: r["identity_key"])


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def cached_document(entry: Dict) -> Optional[str]:
    """The homepage 013 already paid for, if it exists."""
    path = CACHE_013 / _slug(entry["canonical_name"]) / "rendered.html"
    if path.is_file():
        return path.read_text(encoding="utf-8", errors="replace")
    return None


# --------------------------------------------------------------------------- #
# Candidate discovery -- from the page's own links, never guessed
# --------------------------------------------------------------------------- #

def domain_relationship(candidate: str, home: str) -> str:
    c, h = urlparse(candidate).netloc.lower(), urlparse(home).netloc.lower()
    if not c or c == h:
        return "SAME_DOMAIN"
    if c.lstrip("www.") == h.lstrip("www."):
        return "SAME_DOMAIN"
    root = ".".join(h.lstrip("www.").split(".")[-2:])
    if c.endswith(root):
        return "SAME_DOMAIN"
    return "THIRD_PARTY"


def discover_candidates(html: str, base_url: str) -> List[Dict]:
    """Rank the page's own links by how specifically the SITE names them."""
    seen: Dict[str, Dict] = {}
    for href, label in _LINK_RE.findall(html or ""):
        if href.lower().startswith(("mailto:", "tel:", "javascript:")):
            continue
        url = urljoin(base_url, href.split("#")[0]).rstrip()
        if not url.lower().startswith("http"):
            continue
        text = re.sub(r"<[^>]+>", " ", label)
        text = " ".join(text.split()).lower()[:60]
        haystack = "%s %s" % (url, text)
        if _EXCLUDE.search(haystack):
            continue
        score = 0
        matched = ""
        for value, pattern in _LADDER:
            if pattern.search(haystack):
                score, matched = value, pattern.pattern[:40]
                break
        if not score:
            continue
        if url == base_url.rstrip("/") or url.rstrip("/") == base_url.rstrip("/"):
            continue
        prior = seen.get(url)
        if prior is None or score > prior["score"]:
            seen[url] = {"url": url, "anchor_text": text, "score": score,
                         "matched_rule": matched,
                         "relationship": domain_relationship(url, base_url)}
    ranked = sorted(seen.values(), key=lambda c: (-c["score"], c["url"]))
    return ranked


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #

_STOP = {"the", "hotel", "inn", "suites", "milwaukee", "wi", "on", "of", "at",
         "and", "lodge", "casino", "arts", "extended", "stay"}


def identity_tokens(name: str) -> List[str]:
    return [t for t in re.findall(r"[a-z]+", name.lower())
            if t not in _STOP and len(t) > 3]


#: A page that disclaims being about any particular property. WoodSpring's
#: brand offers page says so in as many words.
_VARIES_RE = re.compile(r"vary\s+by\s+location|varies\s+by\s+location"
                        r"|may\s+differ\s+by\s+(?:hotel|location|property)",
                        re.IGNORECASE)

#: A path segment that names WHICH location on a multi-location domain:
#: /pewaukee/, /clive/, /locations/wisconsin/Menomonee-Falls/.
#: Everything here is a PAGE TYPE, not a place. An earlier version omitted the
#: page types and read "/contact/" versus "/amenities/" as two different
#: locations, which wrongly disqualified a hotel whose own site simply has more
#: than one page.
_GENERIC_SEGMENTS = {
    "", "en", "us", "hotels", "hotel", "locations", "location", "property",
    "properties", "stay", "accommodations", "accommodation", "offers", "offer",
    "faqs", "faq", "contact", "about", "rooms", "room", "suites", "dining",
    "restaurant", "gallery", "events", "meetings", "weddings", "specials",
    "packages", "amenities", "amenity", "services", "policies", "policy",
    "hotel-information", "guest-information", "house-rules", "terms", "rates",
    "spa", "blog", "news", "pets", "pet", "dogs", "dog", "dog-friendly",
    "pet-friendly", "pet-friendly-hotel", "extended-stay-hotels",
    "reservations-policy", "frequently-asked-questions",
}


def location_segments(url: str) -> List[str]:
    """The path segments that could name a specific location."""
    return [seg.lower() for seg in urlparse(url).path.split("/")
            if seg and seg.lower() not in _GENERIC_SEGMENTS]


def check_identity(entry: Dict, text: str, final_url: str) -> Dict:
    """Does this page belong to THIS property, or merely to its domain?

    Same-domain is not property binding. Two of this cohort's operators run
    several hotels on one domain -- one has a /pewaukee/ and a /clive/, the
    other a brand-wide offers page for a chain -- and an earlier version of
    this check accepted "same domain" as identity. It selected an Iowa FAQ for
    a Wisconsin hotel and a chain page for one property, and both would have
    been reported as discoveries.

    So when the STARTING url names a location, a candidate that names a
    DIFFERENT one has to earn its binding from the page text instead. And a
    page that disclaims property specificity in its own words -- "restrictions
    may vary by location" -- can never be property-specific evidence.
    """
    tokens = identity_tokens(entry["canonical_name"])
    low = text.lower()
    matched = [t for t in tokens if t in low]
    same_domain = domain_relationship(final_url, entry["official_url"]) == "SAME_DOMAIN"

    start_loc = set(location_segments(entry["official_url"]))
    cand_loc = set(location_segments(final_url))
    # A conflict is a candidate that names a location the start does not, when
    # the start named one at all.
    location_conflict = bool(start_loc and cand_loc and not (start_loc & cand_loc))
    disclaims = bool(_VARIES_RE.search(text))
    names_property = bool(tokens and len(matched) == len(tokens))

    if disclaims:
        # A page that says its own terms vary by location has told us it does
        # not state THIS property's terms. That beats a token match: the
        # property name on such a page is a location picker, not a binding.
        confirmed, why = False, ("the page disclaims property specificity in "
                                 "its own words, so it states no terms for "
                                 "this property")
    elif location_conflict:
        confirmed, why = False, ("the page names a different location on the "
                                 "same domain (%s, where this property is %s)"
                                 % (sorted(cand_loc), sorted(start_loc)))
    elif same_domain:
        confirmed, why = True, "same-domain page, no location conflict"
    elif names_property:
        confirmed, why = True, "an off-domain page that names the property"
    else:
        confirmed, why = False, "no binding to this property"

    return {"confirmed": confirmed, "why": why, "same_domain": same_domain,
            "location_conflict": location_conflict,
            "disclaims_property_specificity": disclaims,
            "starting_location": sorted(start_loc),
            "candidate_location": sorted(cand_loc),
            "distinctive_tokens": tokens, "tokens_found": matched,
            "final_url": final_url}


def source_quality(entry: Dict, candidate: Dict, identity: Dict) -> str:
    if candidate["relationship"] == "THIRD_PARTY":
        return "third_party_page"
    if identity.get("disclaims_property_specificity"):
        return "generic_brand_or_operator_page"
    if identity.get("location_conflict"):
        return "generic_brand_or_operator_page"
    path = urlparse(candidate["url"]).path.lower()
    if candidate["score"] >= 90:
        return "property_specific_first_party_policy_page"
    if identity["same_domain"] and path not in ("", "/"):
        return "exact_property_page"
    if identity["tokens_found"]:
        return "operator_page_explicitly_tied_to_the_property"
    return "generic_brand_or_operator_page"


# --------------------------------------------------------------------------- #
# Acquisition -- Firecrawl only, gate-free, cached
# --------------------------------------------------------------------------- #

def fetch(url: str, run_dir: Path, key: str) -> Dict:
    out = run_dir / key
    out.mkdir(parents=True, exist_ok=True)
    target = out / "rendered.html"
    if target.is_file():
        return {"html": target.read_text(encoding="utf-8", errors="replace"),
                "status": 200, "final_url": url, "credits": 0, "source": "CACHED"}
    try:
        result = FC.fetch(url, profile=FC.ROUTED_PROFILE)
    except Exception as exc:                                     # noqa: BLE001
        return {"html": "", "status": None, "final_url": "", "credits": 1,
                "source": "FETCH_FAILED",
                "error": "%s: %s" % (type(exc).__name__, FC.redact(str(exc)))}
    html = result.get("html") or ""
    if html:
        target.write_bytes(html.encode("utf-8"))
    return {"html": html, "status": result.get("status"),
            "final_url": result.get("final_url") or url,
            "credits": 1, "source": "FIRECRAWL"}


def evaluate(entry: Dict, run_dir: Path) -> Dict:
    """One property, all the way down the ladder."""
    home_html = cached_document(entry)
    spent = 0
    if home_html is None:
        got = fetch(entry["official_url"], run_dir, _slug(entry["canonical_name"]) + "--home")
        spent += got["credits"]
        home_html = got["html"]
        home_source = got["source"]
    else:
        home_source = "REUSED_DIAGNOSTIC_013"

    candidates = discover_candidates(home_html, entry["official_url"])
    first_party = [c for c in candidates if c["relationship"] != "THIRD_PARTY"]
    tried, best = [], None

    for candidate in first_party[:MAX_CANDIDATES_PER_PROPERTY]:
        key = "%s--%s" % (_slug(entry["canonical_name"]),
                          _slug(urlparse(candidate["url"]).path) or "root")
        got = fetch(candidate["url"], run_dir, key[:120])
        spent += got["credits"]
        text = UC.html_to_text(got["html"]) if got["html"] else ""
        identity = check_identity(entry, text, got["final_url"] or candidate["url"])
        presence = D13.classify_presence(
            text, identity_ok=bool(text) and identity["confirmed"])
        reader = D13.read_generically(got["html"] or "")
        row = dict(candidate)
        row.update({
            "fetch_source": got["source"], "status": got.get("status"),
            "text_chars": len(text),
            "identity": identity,
            "presence": presence["presence"],
            "presence_why": presence["why"],
            "substantive_concepts": presence["substantive_concepts"],
            "snippets": {k: v[:2] for k, v in presence["concepts"].items()},
            "source_quality": source_quality(entry, candidate, identity),
            "reader_extraction": reader["extraction"],
            "reader_block": reader["block"][:220],
        })
        tried.append(row)
        rank = {"FULL_POLICY_PRESENT": 3, "PARTIAL_POLICY_PRESENT": 2,
                "AMENITY_ONLY": 1}.get(row["presence"], 0)
        if rank and (best is None or rank > best[0]):
            best = (rank, row)
        if rank == 3:
            break

    return finalise(entry, home_source, candidates, tried, best, spent)


def finalise(entry, home_source, candidates, tried, best, spent) -> Dict:
    if not candidates:
        outcome, chosen = "NO_POLICY_URL_FOUND", None
    elif best is None:
        blocked = [t for t in tried if t["fetch_source"] == "FETCH_FAILED"]
        outcome = "DISCOVERY_BLOCKED" if blocked and len(blocked) == len(tried) \
            else "NO_POLICY_URL_FOUND"
        chosen = None
    else:
        rank, chosen = best
        if not chosen["identity"]["confirmed"]:
            outcome = "IDENTITY_AMBIGUOUS"
        elif chosen["source_quality"] in ("third_party_page",
                                          "generic_brand_or_operator_page"):
            outcome = "IDENTITY_AMBIGUOUS"
        elif rank == 1:
            outcome = "AMENITY_URL_ONLY"
        else:
            outcome = "POLICY_URL_FOUND"

    # Separate the URL effect from the reader effect, which is the point.
    reader_effect = ""
    if outcome == "POLICY_URL_FOUND":
        fields = [f for f in ("pet_fee", "fee_basis", "weight_limit",
                              "pet_count_limit", "species_allowed", "deposit")
                  if f in (chosen["reader_extraction"] or {})]
        if not chosen["text_chars"]:
            reader_effect = "URL_FOUND_PROVIDER_LIMITED"
        elif len(fields) >= max(1, len(chosen["substantive_concepts"]) - 1):
            reader_effect = "URL_FIX_SUFFICIENT"
        else:
            reader_effect = "URL_FOUND_READER_STILL_MISSES"

    return {
        "identity_key": entry["identity_key"],
        "property_name": entry["canonical_name"],
        "starting_url": entry["official_url"],
        "starting_url_source": home_source,
        "candidates_discovered": len(candidates),
        "candidates_first_party": len([c for c in candidates
                                       if c["relationship"] != "THIRD_PARTY"]),
        "candidates_tried": tried,
        "outcome": outcome,
        "discovered_url": chosen["url"] if chosen else None,
        "discovery_evidence": ({"anchor_text": chosen["anchor_text"],
                                "matched_rule": chosen["matched_rule"],
                                "score": chosen["score"],
                                "found_on": entry["official_url"]}
                               if chosen else None),
        "identity_evidence": chosen["identity"] if chosen else None,
        "policy_presence": chosen["presence"] if chosen else None,
        "policy_snippets": chosen["snippets"] if chosen else {},
        "source_quality": chosen["source_quality"] if chosen else None,
        "reader_effect": reader_effect,
        "reader_extraction": chosen["reader_extraction"] if chosen else {},
        "credits": spent,
    }


def run(args) -> Dict:
    subjects = cohort()
    print("independent cohort: %d (asserted)" % len(subjects))
    run_dir = RUN_ROOT / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    credits_before = FC.credits_remaining()
    rows, began = [], time.monotonic()

    for entry in subjects:
        row = evaluate(entry, run_dir)
        rows.append(row)
        print("  %-44s %-22s %-24s %s"
              % (row["property_name"][:44], row["outcome"],
                 row["policy_presence"] or "-",
                 (row["discovered_url"] or "")[:60]), flush=True)
        time.sleep(args.pace)

    credits_after = FC.credits_remaining()

    # Cost is measured when the requests are made. A later rebuild runs from
    # cache and has nothing left to measure, so it must not overwrite the
    # measurement with its own near-zero delta -- which is exactly what the
    # first version of this module did, recording 2 for a 23-document run.
    # The per-document count is the durable figure and survives any rebuild.
    fetched = len(list((RUN_ROOT / args.run_id).rglob("rendered.html")))
    return report(rows, credits_before=credits_before,
                  credits_after=credits_after, documents_fetched=fetched,
                  elapsed=round(time.monotonic() - began, 1))


def report(rows: List[Dict], *, credits_before, credits_after, elapsed,
           documents_fetched: Optional[int] = None) -> Dict:
    outcomes = Counter(r["outcome"] for r in rows)
    found = [r for r in rows if r["outcome"] == "POLICY_URL_FOUND"]
    acquirable = [r for r in found if r["policy_presence"] in
                  ("FULL_POLICY_PRESENT", "PARTIAL_POLICY_PRESENT")]
    effects = Counter(r["reader_effect"] for r in found if r["reader_effect"])
    n = len(rows) or 1

    discovery_rate = round(100.0 * len(found) / n, 1)
    viability = (round(100.0 * len(acquirable) / len(found), 1) if found else 0.0)
    recovery = (round(100.0 * effects.get("URL_FIX_SUFFICIENT", 0) / len(acquirable), 1)
                if acquirable else 0.0)

    if discovery_rate >= 60:
        decision = "BUILD_URL_DISCOVERY_LAYER"
    elif discovery_rate >= 30:
        decision = "MIXED"
    elif discovery_rate > 0:
        decision = "MANUAL_SOURCE_ROUTING"
    else:
        decision = "SOURCE_SCARCITY"

    doc = {
        "schema": "ptf-source-url-discovery/1.0",
        "work_order": WORK_ORDER,
        "market_id": MARKET,
        "note": ("Measurement only. No source URL was edited, no route changed, "
                 "the reader is untouched and nothing was published. Candidates "
                 "come from each property's OWN links; no URL was guessed from "
                 "convention."),
        "cohort_size": len(rows),
        "discovery_ladder": [{"score": s, "rule": p.pattern[:70]} for s, p in _LADDER],
        "max_candidates_per_property": MAX_CANDIDATES_PER_PROPERTY,
        "outcomes": dict(outcomes),
        "rates": {
            "policy_url_discovery_rate_pct": discovery_rate,
            "firecrawl_viability_after_url_correction_pct": viability,
            "current_reader_recovery_rate_pct": recovery,
        },
        "reader_effects": dict(effects),
        "architectural_recommendation": decision,
        "boundaries_respected": {
            "routes_changed": False, "reader_changed": False,
            "source_urls_changed": False, "authority_written": False,
            "policies_published": False, "bright_data_attempts": 0,
        },
        "cost": {"firecrawl_credits": (documents_fetched
                                      if documents_fetched is not None
                                      else sum(r["credits"] for r in rows)),
                 "credits_measured_how": ("one credit per document fetched, "
                                          "counted from the persisted files so "
                                          "a cache-only rebuild cannot "
                                          "overwrite it"),
                 "credits_before": credits_before, "credits_after": credits_after,
                 "bright_data_attempts": 0, "bright_data_usd": 0.0},
        "total_elapsed_seconds": elapsed,
        "properties": rows,
    }
    out = REPORTS / "ptf_independent_url_discovery_014.json"
    out.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
                    .encode("utf-8"))
    return doc


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="url-discovery-014")
    parser.add_argument("--pace", type=float, default=4.0)
    args = parser.parse_args(argv)
    if not FC.credential_present():
        print("%s is not set" % FC.KEY_ENV)
        return 2
    doc = run(args)
    print()
    print("outcomes:", doc["outcomes"])
    r = doc["rates"]
    print("discovery %.1f%% | firecrawl viability %.1f%% | reader recovery %.1f%%"
          % (r["policy_url_discovery_rate_pct"],
             r["firecrawl_viability_after_url_correction_pct"],
             r["current_reader_recovery_rate_pct"]))
    print("reader effects:", doc["reader_effects"])
    print("credits:", doc["cost"]["firecrawl_credits"])
    print()
    print("RECOMMENDATION: %s" % doc["architectural_recommendation"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
