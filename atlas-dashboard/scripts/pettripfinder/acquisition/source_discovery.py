"""First-party policy-URL discovery. Reusable, deterministic, evidence-only.

PTF-INDEPENDENT-POLICY-URL-DISCOVERY-014 measured this algorithm on eleven
Milwaukee independents and recovered a property-specific policy page for eight
of them. This module is that algorithm promoted to production code, with
nothing added: the ranking, the identity rules and the presence classification
are the ones that were measured, and a replay test pins them to the eight URLs
014 actually selected.

WHY THE LAYER EXISTS
--------------------
Nine of those eleven properties pointed at a homepage or a contact page.
Firecrawl fetched every one perfectly -- 200, hydrated, right property -- and
there was no pet policy on them, because a homepage is not where a hotel writes
one. No provider change and no reader change can fix that. The acquisition
pipeline was simply aimed at the wrong page.

THREE RULES THAT COST SOMETHING TO LEARN
-----------------------------------------
1. A candidate must come from a link the property's own page CONTAINS. A
   conventional path like ``/pet-policy`` is never tried on spec, or the
   discovery rate measures how common that convention is rather than what this
   corpus exposes.

2. Same-domain is NOT property binding. Two of the measured operators run
   several hotels on one domain, and an earlier version selected an Iowa FAQ
   for a Wisconsin hotel because the domain matched. A candidate naming a
   different location has to earn its binding from the page text.

3. A page that disclaims specificity -- "restrictions may vary by location" --
   can never be property-specific evidence, however many times the property's
   name appears in its location picker.

And the correction for (2) nearly broke a fourth thing: treating every
unrecognised path segment as a location read ``/contact/`` against
``/amenities/`` as two different places. Page types are enumerated separately
from places for that reason.

WHAT THIS MODULE DOES NOT DO
-----------------------------
It does not fetch by itself: the caller injects a fetcher, so a replay can run
entirely from cache and a test can run with no network at all. It does not
touch routes, readers, the census or any authority file. It returns a result;
what anyone does with it is a separate decision.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

CONTRACT = "ptf-source-discovery/1.0"

#: Terminal statuses. The same vocabulary 014 measured; no new words.
POLICY_URL_FOUND = "POLICY_URL_FOUND"
AMENITY_URL_ONLY = "AMENITY_URL_ONLY"
NO_POLICY_URL_FOUND = "NO_POLICY_URL_FOUND"
IDENTITY_AMBIGUOUS = "IDENTITY_AMBIGUOUS"
DISCOVERY_BLOCKED = "DISCOVERY_BLOCKED"

STATUSES: Tuple[str, ...] = (POLICY_URL_FOUND, AMENITY_URL_ONLY,
                             NO_POLICY_URL_FOUND, IDENTITY_AMBIGUOUS,
                             DISCOVERY_BLOCKED)

#: How many candidates one property may cost. Fixed, and equal for every
#: property: a property allowed more attempts would report a better discovery
#: rate for that reason alone. This is the budget 014 measured under.
CANDIDATE_BUDGET = 3

#: Ranking. Higher first. Ordered by how specifically the SITE ITSELF names the
#: surface, never by what we hope to find behind it.
RANKING: Tuple[Tuple[int, str, re.Pattern], ...] = (
    (100, "names pets or dogs in the path",
     re.compile(r"pet-?polic|pets?-?friendly|/pets?/|/dogs?/|dog-?friendly",
                re.IGNORECASE)),
    (90, "names pets or dogs anywhere",
     re.compile(r"\bpets?\b|\bdogs?\b", re.IGNORECASE)),
    (70, "a policy or hotel-information surface",
     re.compile(r"hotel-?polic|property-?polic|hotel-?information"
                r"|guest-?information|house-?rules|reservations?-?polic",
                re.IGNORECASE)),
    (60, "a frequently-asked-questions surface",
     re.compile(r"faqs?\b|frequently-?asked", re.IGNORECASE)),
    (40, "an amenities or accommodations surface",
     re.compile(r"amenit|accommodation|services", re.IGNORECASE)),
    (20, "a terms or rules surface",
     re.compile(r"\bterms\b|\brules\b|guest-?info", re.IGNORECASE)),
)

#: Never a policy surface, however well it scores on a keyword.
EXCLUDED = re.compile(
    r"privacy|terms-of-use|cookie|careers|gift-?card|press|blog|sitemap"
    r"|/book|reserv(?:ation)?s?\.|login|account|instagram|facebook|twitter",
    re.IGNORECASE)

_LINK = re.compile(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                   re.IGNORECASE | re.DOTALL)

#: PAGE TYPES, not places. Separating these is what stops ``/contact/`` and
#: ``/amenities/`` reading as two different locations.
PAGE_TYPE_SEGMENTS = frozenset({
    "", "en", "us", "hotels", "hotel", "locations", "location", "property",
    "properties", "stay", "accommodations", "accommodation", "offers", "offer",
    "faqs", "faq", "contact", "about", "rooms", "room", "suites", "dining",
    "restaurant", "gallery", "events", "meetings", "weddings", "specials",
    "packages", "amenities", "amenity", "services", "policies", "policy",
    "hotel-information", "guest-information", "house-rules", "terms", "rates",
    "spa", "blog", "news", "pets", "pet", "dogs", "dog", "dog-friendly",
    "pet-friendly", "pet-friendly-hotel", "extended-stay-hotels",
    "reservations-policy", "frequently-asked-questions",
})

#: A page telling you, in its own words, that it does not state THIS
#: property's terms.
DISCLAIMER = re.compile(
    r"vary\s+by\s+location|varies\s+by\s+location"
    r"|may\s+differ\s+by\s+(?:hotel|location|property)", re.IGNORECASE)

_NAME_STOPWORDS = frozenset({
    "the", "hotel", "inn", "suites", "milwaukee", "wi", "on", "of", "at",
    "and", "lodge", "casino", "arts", "extended", "stay"})


# --------------------------------------------------------------------------- #
# Contract
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Candidate:
    url: str
    anchor_text: str
    score: int
    matched_rule: str
    relationship: str

    def to_dict(self) -> Dict:
        return {"url": self.url, "anchor_text": self.anchor_text,
                "score": self.score, "matched_rule": self.matched_rule,
                "relationship": self.relationship}


@dataclass(frozen=True)
class DiscoveryResult:
    """What discovery concluded for one property, and why."""

    contract: str
    identity_key: str
    property_name: str
    starting_url: str
    starting_domain: str
    status: str
    discovered_url: Optional[str] = None
    discovered_domain: str = ""
    first_party: bool = False
    identity_confirmed: bool = False
    identity_reason: str = ""
    policy_presence: str = ""
    source_quality: str = ""
    discovery_reason: str = ""
    candidates_considered: int = 0
    candidates_fetched: int = 0
    policy_snippets: Dict = field(default_factory=dict)
    rejected: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "contract": self.contract, "identity_key": self.identity_key,
            "property_name": self.property_name,
            "starting_url": self.starting_url,
            "starting_domain": self.starting_domain, "status": self.status,
            "discovered_url": self.discovered_url,
            "discovered_domain": self.discovered_domain,
            "first_party": self.first_party,
            "identity_confirmed": self.identity_confirmed,
            "identity_reason": self.identity_reason,
            "policy_presence": self.policy_presence,
            "source_quality": self.source_quality,
            "discovery_reason": self.discovery_reason,
            "candidates_considered": self.candidates_considered,
            "candidates_fetched": self.candidates_fetched,
            "policy_snippets": dict(self.policy_snippets),
            "rejected": list(self.rejected),
        }


# --------------------------------------------------------------------------- #
# Candidate discovery
# --------------------------------------------------------------------------- #

def domain_relationship(candidate_url: str, home_url: str) -> str:
    c = urlparse(candidate_url).netloc.lower()
    h = urlparse(home_url).netloc.lower()
    if not c or c == h:
        return "SAME_DOMAIN"
    if c.removeprefix("www.") == h.removeprefix("www."):
        return "SAME_DOMAIN"
    root = ".".join(h.removeprefix("www.").split(".")[-2:])
    return "SAME_DOMAIN" if c.endswith(root) else "THIRD_PARTY"


def rank_candidates(html: str, base_url: str) -> List[Candidate]:
    """The page's OWN links, ranked. Nothing is synthesised."""
    best: Dict[str, Candidate] = {}
    for href, label in _LINK.findall(html or ""):
        if href.lower().startswith(("mailto:", "tel:", "javascript:")):
            continue
        url = urljoin(base_url, href.split("#")[0]).strip()
        if not url.lower().startswith("http"):
            continue
        text = " ".join(re.sub(r"<[^>]+>", " ", label).split()).lower()[:60]
        haystack = "%s %s" % (url, text)
        if EXCLUDED.search(haystack):
            continue
        if url.rstrip("/") == base_url.rstrip("/"):
            continue
        for score, why, pattern in RANKING:
            if pattern.search(haystack):
                found = Candidate(url=url, anchor_text=text, score=score,
                                  matched_rule=why,
                                  relationship=domain_relationship(url, base_url))
                if url not in best or score > best[url].score:
                    best[url] = found
                break
    return sorted(best.values(), key=lambda c: (-c.score, c.url))


# --------------------------------------------------------------------------- #
# Identity
# --------------------------------------------------------------------------- #

def location_segments(url: str) -> List[str]:
    return [seg.lower() for seg in urlparse(url).path.split("/")
            if seg and seg.lower() not in PAGE_TYPE_SEGMENTS]


def distinctive_tokens(name: str) -> List[str]:
    return [t for t in re.findall(r"[a-z]+", name.lower())
            if t not in _NAME_STOPWORDS and len(t) > 3]


def validate_identity(property_name: str, starting_url: str,
                      candidate_url: str, page_text: str) -> Dict:
    """Does this page belong to THIS property? Same-domain is not an answer."""
    tokens = distinctive_tokens(property_name)
    matched = [t for t in tokens if t in page_text.lower()]
    names_property = bool(tokens and len(matched) == len(tokens))
    same_domain = domain_relationship(candidate_url, starting_url) == "SAME_DOMAIN"

    start_loc = set(location_segments(starting_url))
    cand_loc = set(location_segments(candidate_url))
    conflict = bool(start_loc and cand_loc and not (start_loc & cand_loc))
    disclaims = bool(DISCLAIMER.search(page_text))

    if disclaims:
        confirmed, reason = False, ("the page disclaims property specificity in "
                                    "its own words")
    elif conflict:
        confirmed, reason = False, ("the page names a different location on the "
                                    "same domain (%s, where this property is %s)"
                                    % (sorted(cand_loc), sorted(start_loc)))
    elif same_domain:
        confirmed, reason = True, "same-domain page, no location conflict"
    elif names_property:
        confirmed, reason = True, "an off-domain page that names the property"
    else:
        confirmed, reason = False, "no binding to this property"

    return {"confirmed": confirmed, "reason": reason, "same_domain": same_domain,
            "location_conflict": conflict, "disclaims": disclaims,
            "distinctive_tokens": tokens, "tokens_found": matched,
            "names_property": names_property}


def grade_source(candidate: Candidate, identity: Dict) -> str:
    if candidate.relationship == "THIRD_PARTY":
        return "third_party_page"
    if identity["disclaims"] or identity["location_conflict"]:
        return "generic_brand_or_operator_page"
    if candidate.score >= 90:
        return "property_specific_first_party_policy_page"
    if identity["same_domain"]:
        return "exact_property_page"
    if identity["tokens_found"]:
        return "operator_page_explicitly_tied_to_the_property"
    return "generic_brand_or_operator_page"


ACCEPTABLE_QUALITY = frozenset({
    "property_specific_first_party_policy_page", "exact_property_page",
    "operator_page_explicitly_tied_to_the_property"})


# --------------------------------------------------------------------------- #
# Discovery
# --------------------------------------------------------------------------- #

#: (text, identity_ok) -> {"presence": ..., "why": ..., "concepts": {...}}
PresenceClassifier = Callable[[str, bool], Dict]
#: url -> {"html": str, "final_url": str, "requested": bool}
Fetcher = Callable[[str], Dict]
#: html -> text
TextExtractor = Callable[[str], str]

_PRESENCE_RANK = {"FULL_POLICY_PRESENT": 3, "PARTIAL_POLICY_PRESENT": 2,
                  "AMENITY_ONLY": 1}


def discover(*, identity_key: str, property_name: str, starting_url: str,
             home_html: str, fetch: Fetcher, to_text: TextExtractor,
             classify_presence: PresenceClassifier,
             budget: int = CANDIDATE_BUDGET) -> DiscoveryResult:
    """One property, all the way down the ladder. Deterministic and injected.

    ``fetch`` is supplied by the caller so a replay can run entirely from
    cached documents and a test can run with no network at all.
    """
    base = DiscoveryResult(
        contract=CONTRACT, identity_key=identity_key,
        property_name=property_name, starting_url=starting_url,
        starting_domain=urlparse(starting_url).netloc.lower(),
        status=NO_POLICY_URL_FOUND)

    ranked = rank_candidates(home_html, starting_url)
    first_party = [c for c in ranked if c.relationship != "THIRD_PARTY"]
    if not first_party:
        return _replace(base, status=NO_POLICY_URL_FOUND,
                        candidates_considered=len(ranked),
                        discovery_reason="the property page exposes no "
                                         "first-party candidate link")

    best: Optional[Tuple[int, Candidate, Dict, Dict, str]] = None
    rejected: List[Dict] = []
    fetched = 0
    blocked = 0

    for candidate in first_party[:budget]:
        got = fetch(candidate.url)
        fetched += 1
        html = got.get("html") or ""
        if not html:
            blocked += 1
            rejected.append({"url": candidate.url, "why": "no document returned"})
            continue
        text = to_text(html)
        identity = validate_identity(property_name, starting_url,
                                     got.get("final_url") or candidate.url, text)
        presence = classify_presence(text, identity["confirmed"])
        quality = grade_source(candidate, identity)
        rank = _PRESENCE_RANK.get(presence["presence"], 0)

        if not identity["confirmed"] or quality not in ACCEPTABLE_QUALITY:
            rejected.append({"url": candidate.url, "why": identity["reason"],
                             "source_quality": quality,
                             "presence": presence["presence"]})
            continue
        if rank == 0:
            rejected.append({"url": candidate.url,
                             "why": "no pet-policy content on the page",
                             "source_quality": quality,
                             "presence": presence["presence"]})
            continue
        if best is None or rank > best[0]:
            best = (rank, candidate, identity, presence, quality)
        if rank == 3:
            break

    if best is None:
        status = DISCOVERY_BLOCKED if blocked and blocked == fetched \
            else NO_POLICY_URL_FOUND
        reason = ("every candidate failed to return a document"
                  if status == DISCOVERY_BLOCKED else
                  "no first-party candidate carried pet-policy content bound "
                  "to this property")
        return _replace(base, status=status, candidates_considered=len(ranked),
                        candidates_fetched=fetched, discovery_reason=reason,
                        rejected=rejected)

    rank, candidate, identity, presence, quality = best
    status = AMENITY_URL_ONLY if rank == 1 else POLICY_URL_FOUND
    return _replace(
        base, status=status, discovered_url=candidate.url,
        discovered_domain=urlparse(candidate.url).netloc.lower(),
        first_party=candidate.relationship == "SAME_DOMAIN",
        identity_confirmed=identity["confirmed"],
        identity_reason=identity["reason"],
        policy_presence=presence["presence"], source_quality=quality,
        discovery_reason="%s (anchor %r, score %d)"
                         % (candidate.matched_rule, candidate.anchor_text,
                            candidate.score),
        candidates_considered=len(ranked), candidates_fetched=fetched,
        policy_snippets={k: v[:2] for k, v in
                         (presence.get("concepts") or {}).items()},
        rejected=rejected)


def _replace(result: DiscoveryResult, **changes) -> DiscoveryResult:
    data = result.to_dict()
    data.pop("contract", None)
    data.update(changes)
    return DiscoveryResult(contract=CONTRACT, **data)


# --------------------------------------------------------------------------- #
# Usage accounting -- requests and documents are different numbers
# --------------------------------------------------------------------------- #

@dataclass
class UsageLedger:
    """Provider REQUESTS, kept apart from documents on disk, and monotonic.

    PTF-INDEPENDENT-POLICY-URL-DISCOVERY-014 recorded 2 credits for a
    23-document run: its final report rebuild ran entirely from cache,
    measured its own near-zero delta and overwrote the real figure. Cost is
    measured when requests are made, so this ledger persists and can only
    increase -- a rebuild that makes no request adds nothing and erases
    nothing.
    """

    path: Path
    provider_requests: int = 0
    cache_hits: int = 0

    def load(self) -> "UsageLedger":
        if self.path.is_file():
            try:
                stored = json.loads(self.path.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                return self
            self.provider_requests = int(stored.get("provider_requests") or 0)
            self.cache_hits = int(stored.get("cache_hits") or 0)
        return self

    def record(self, *, requested: bool) -> None:
        if requested:
            self.provider_requests += 1
        else:
            self.cache_hits += 1

    def save(self) -> None:
        prior = UsageLedger(path=self.path).load()
        # Monotonic: a rebuild can never lower the historical request count.
        merged = {"contract": "ptf-discovery-usage/1.0",
                  "provider_requests": max(self.provider_requests,
                                           prior.provider_requests),
                  "cache_hits": self.cache_hits,
                  "note": ("provider_requests counts REQUESTS, not documents on "
                           "disk, and never decreases. A report rebuilt from "
                           "cache makes no request and must not overwrite "
                           "historical usage.")}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes((json.dumps(merged, indent=1) + "\n").encode("utf-8"))
        self.provider_requests = merged["provider_requests"]


# --------------------------------------------------------------------------- #
# The source-routing overlay
# --------------------------------------------------------------------------- #

OVERLAY_CONTRACT = "ptf-discovered-source-urls/1.0"


def overlay_path(repo: Path, market_id: str) -> Path:
    return (repo / "launch_packages" / "pettripfinder" / "markets"
            / "discovered_policy_urls" / ("%s.json" % market_id))


def load_overlay(repo: Path, market_id: str) -> Dict:
    path = overlay_path(repo, market_id)
    if not path.is_file():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    return {r["identity_key"]: r for r in doc.get("records", [])}


def resolve_source_url(repo: Path, market_id: str, identity_key: str,
                       census_url: str) -> str:
    """The URL acquisition should start from.

    The census URL remains canonical and is never edited; this overlay is a
    routing preference layered on top of it, so history stays intact and a
    discovery can be withdrawn by deleting one row.
    """
    row = load_overlay(repo, market_id).get(identity_key)
    if row and row.get("status") == POLICY_URL_FOUND and row.get("discovered_url"):
        return row["discovered_url"]
    return census_url
