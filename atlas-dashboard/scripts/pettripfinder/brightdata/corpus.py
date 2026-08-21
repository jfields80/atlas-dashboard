"""The committed, manually validated PTF corpus, read as a BENCHMARK.

PTF-BRIGHTDATA-CROSS-BRAND-PILOT-002 does not invent what it measures against.
Its benchmark is what this repository already established by hand and by
founder review: 268 approved policy records across five markets, plus 75
exclusion-registry rows recording a captured refusal.

READ ONLY, IN BOTH DIRECTIONS
-----------------------------
Nothing here writes. It also never travels forward: a
:class:`BenchmarkRecord` is loaded so a capture can be COMPARED to it after
the fact, and the pilot's capture path cannot import this module. The rule the
Marriott pilot established stands unchanged -- capture first, compare second,
and a field Bright Data did not find is never filled in from what we knew.

WHY CLASSIFICATION LIVES HERE
-----------------------------
A thirty-property sample that happened to be thirty easy pages would measure
nothing. The work order asks for explicit no-pets rows, structured positives,
known contradictions, dynamic surfaces and historically difficult routes, so
those properties have to be RECOGNISED in the corpus rather than asserted
about it. Every category below is derived from committed data -- a
``withheld_fields`` entry, a ``fee_tiers`` array, an exclusion row -- except
the two access categories, which are derived from this repository's own
recorded operational history and say so.

The brands this pilot must not touch are named once, here: Hyatt and Best
Western are premium domains under the current Bright Data plan and cost more
per request. Excluding them is a budget decision, not a capability claim.
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, FrozenSet, Iterable, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

POLICY_GLOB = "launch_packages/pettripfinder/hotel_policy_facts*.json"
EXCLUSION_GLOB = ("launch_packages/pettripfinder/markets/authority/*/"
                  "hotel_exclusions.json")

#: host fragment -> brand bucket name. Ordered: the first match wins, so a
#: longer, more specific host is listed before a shorter one it contains.
BRAND_HOSTS: Tuple[Tuple[str, str], ...] = (
    ("marriott.com", "MARRIOTT"),
    ("hilton.com", "HILTON"),
    ("ihg.com", "IHG"),
    ("choicehotels.com", "CHOICE"),
    ("wyndhamhotels.com", "WYNDHAM"),
    ("sonesta.com", "SONESTA"),
    ("redroof.com", "RED_ROOF"),
    ("extendedstayamerica.com", "ESA"),
    ("motel6.com", "MOTEL6"),
    ("g6hospitality.com", "MOTEL6"),
    ("druryhotels.com", "DRURY"),
    ("hyatt.com", "HYATT"),
    ("bestwestern.com", "BEST_WESTERN"),
)

INDEPENDENT_PREFIX = "INDEP:"

#: The five named brand buckets. MIXED collects everything else.
NAMED_BUCKETS: Tuple[str, ...] = ("MARRIOTT", "HILTON", "IHG", "CHOICE",
                                  "WYNDHAM")
MIXED_BUCKET = "MIXED"
BUCKETS: Tuple[str, ...] = NAMED_BUCKETS + (MIXED_BUCKET,)

#: What "MIXED" should reach for, in order. The work order names these as the
#: preferred contents of the sixth bucket, so the preference is expressed as an
#: ORDER rather than left to whichever sub-brand happens to sort first. It is a
#: preference and not a rule: if the corpus cannot supply one of them the
#: bucket still fills, and the sample records what it actually got.
MIXED_PREFERRED_BRANDS: Tuple[str, ...] = ("SONESTA", "RED_ROOF", "ESA",
                                           "MOTEL6", INDEPENDENT_PREFIX)

#: Premium domains under the current Bright Data plan. Excluded from this
#: pilot on cost grounds and for no other reason; Hyatt additionally sits
#: behind Kasada and is ADR-blocked for automated access.
EXCLUDED_BRANDS: FrozenSet[str] = frozenset({"HYATT", "BEST_WESTERN"})

# --------------------------------------------------------------------------- #
# Categories.
# --------------------------------------------------------------------------- #

CAT_NO_PETS = "EXPLICIT_NO_PETS"
CAT_STRUCTURED_POSITIVE = "STRUCTURED_POSITIVE"
CAT_CONTRADICTION = "CONTRADICTION_OR_AMBIGUITY"
CAT_DYNAMIC = "DYNAMIC_SURFACE"
CAT_DIFFICULT = "HISTORICALLY_DIFFICULT"
CAT_SPECIES = "SPECIES_SPECIFIC"
CAT_DOGS_ONLY = "DOGS_ONLY"
CAT_TIERED_FEE = "TIERED_FEE"
CAT_SERVICE_ANIMAL = "SERVICE_ANIMAL_WORDING"
CAT_CLEANING = "CONDITIONAL_CLEANING_CHARGE"
CAT_COMBINED_WEIGHT = "COMBINED_WEIGHT"
CAT_DIMENSIONS = "DIMENSION_CONSTRAINTS"
CAT_INDEPENDENT = "INDEPENDENT_SITE"

CATEGORIES: Tuple[str, ...] = (
    CAT_NO_PETS, CAT_STRUCTURED_POSITIVE, CAT_CONTRADICTION, CAT_DYNAMIC,
    CAT_DIFFICULT, CAT_SPECIES, CAT_DOGS_ONLY, CAT_TIERED_FEE,
    CAT_SERVICE_ANIMAL, CAT_CLEANING, CAT_COMBINED_WEIGHT, CAT_DIMENSIONS,
    CAT_INDEPENDENT,
)

#: Brands whose policy surface this repository has recorded as client-rendered
#: or interaction-gated. Operational history, not a property of the corpus, and
#: labelled as such so a reader knows where the claim comes from:
#:
#: * IHG -- ``hoteldetail`` renders its policy through inline JS and freezes a
#:   CDP session on a full outerHTML read (PTF-CLEVELAND-PASS-4).
#: * CHOICE -- client-rendered; its sitemap needs a real navigation before
#:   same-origin fetch works at all (PTF-CINCINNATI-URL-ROUTING).
#: * HILTON -- JS-hydrated policy panel, and the JSON-LD and the visible text
#:   carry different halves of the answer (PTF-NEGATIVE-EVIDENCE-P0-001).
DYNAMIC_BRANDS: FrozenSet[str] = frozenset({"IHG", "CHOICE", "HILTON"})

#: Brands this repository has recorded actively refusing or throttling
#: automated access: Choice WAF-blocked an entire session, IHG 403s real
#: Chromium, Hilton throttles to roughly one fetch per navigation.
DIFFICULT_BRANDS: FrozenSet[str] = frozenset({"CHOICE", "IHG", "HILTON"})


def brand_of(url: str) -> str:
    """Brand bucket for a source URL, or ``INDEP:<host>``."""
    host = re.sub(r"^https?://", "", url or "").split("/")[0].lower()
    if not host:
        return "NO_URL"
    for fragment, brand in BRAND_HOSTS:
        if fragment in host:
            return brand
    return INDEPENDENT_PREFIX + host


def bucket_of(brand: str) -> str:
    return brand if brand in NAMED_BUCKETS else MIXED_BUCKET


@dataclass(frozen=True)
class BenchmarkRecord:
    """One manually validated property: what it is, and what it says.

    ``facts`` is the committed schema-1.2 fact block and ``quotes`` are the
    committed evidence quotes. Both are the COMPARISON target and neither may
    reach a capture.
    """

    identity_key: str
    name: str
    market_id: str
    brand: str
    bucket: str
    source_url: str
    pets_allowed: Optional[bool]
    facts: Mapping
    quotes: Tuple[str, ...]
    withheld_fields: Mapping
    service_animal_statement: str
    categories: FrozenSet[str]
    origin: str                     # "policy_record" | "exclusion_registry"
    #: What the identity census knows about WHERE this property is. Optional
    #: because records built from policy files carry no address; a builder that
    #: reads the census fills them and the capture's identity gate can then use
    #: a street and a telephone line instead of a URL path alone.
    street: str = ""
    postal_code: str = ""
    phone: str = ""
    locality: str = ""

    @property
    def slug(self) -> str:
        base = re.sub(r"[^a-z0-9]+", "-", (self.name or "").lower()).strip("-")
        return base or re.sub(r"[^a-z0-9]+", "-", self.identity_key)[:60]

    def to_dict(self) -> Dict:
        return {"identity_key": self.identity_key, "name": self.name,
                "market_id": self.market_id, "brand": self.brand,
                "bucket": self.bucket, "source_url": self.source_url,
                "pets_allowed": self.pets_allowed,
                "categories": sorted(self.categories), "origin": self.origin}

    def richness(self) -> int:
        """How much a record asserts. Used only to break selection ties, so a
        thin row never displaces a detailed one for the last free slot."""
        return len(self.facts or {}) + len(self.quotes)


def _repo_glob(pattern: str) -> List[str]:
    return sorted(glob.glob(str(_REPO_ROOT / pattern).replace("\\", "/")))


def _classify_policy(row: Mapping, brand: str) -> FrozenSet[str]:
    facts = row.get("facts") or {}
    withheld = row.get("withheld_fields") or {}
    cats: List[str] = []

    if facts.get("pets_allowed") is True:
        has = [k for k in ("pet_fee", "weight_limit", "pet_count_limit")
               if k in facts]
        if len(has) >= 3:
            cats.append(CAT_STRUCTURED_POSITIVE)
    if withheld:
        cats.append(CAT_CONTRADICTION)
    if facts.get("species"):
        cats.append(CAT_SPECIES)
        species = facts["species"]
        if isinstance(species, Mapping):
            dogs = species.get("dogs")
            cats_state = species.get("cats")
            if dogs == "accepted" and cats_state in ("prohibited", None):
                cats.append(CAT_DOGS_ONLY)
    if facts.get("fee_tiers"):
        cats.append(CAT_TIERED_FEE)
    if row.get("service_animal_statement"):
        cats.append(CAT_SERVICE_ANIMAL)
    if facts.get("combined_weight_limit"):
        cats.append(CAT_COMBINED_WEIGHT)
    if facts.get("dimension_constraints"):
        cats.append(CAT_DIMENSIONS)
    charges = facts.get("other_charges") or []
    named_cleaning = any((c or {}).get("kind") == "cleaning_fee"
                         for c in charges if isinstance(c, Mapping))
    if named_cleaning or "cleaning_fee" in withheld:
        cats.append(CAT_CLEANING)
    if brand in DYNAMIC_BRANDS:
        cats.append(CAT_DYNAMIC)
    if brand in DIFFICULT_BRANDS:
        cats.append(CAT_DIFFICULT)
    if brand.startswith(INDEPENDENT_PREFIX):
        cats.append(CAT_INDEPENDENT)
    return frozenset(cats)


def load_policy_records() -> Tuple[BenchmarkRecord, ...]:
    """Every committed, approved policy record, as a benchmark."""
    out: List[BenchmarkRecord] = []
    for path in _repo_glob(POLICY_GLOB):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        for row in data.get("hotels") or ():
            url = str(row.get("source_url") or "").strip()
            if not url.startswith("http"):
                continue
            brand = brand_of(url)
            facts = row.get("facts") or {}
            quotes = tuple(str(e.get("quote") or "")
                           for e in (row.get("evidence") or ())
                           if isinstance(e, Mapping) and e.get("quote"))
            out.append(BenchmarkRecord(
                identity_key=str(row.get("identity_key")
                                 or row.get("key") or ""),
                name=str(row.get("name") or ""),
                market_id=str(row.get("market_id") or ""),
                brand=brand, bucket=bucket_of(brand), source_url=url,
                pets_allowed=facts.get("pets_allowed"),
                facts=facts, quotes=quotes,
                withheld_fields=row.get("withheld_fields") or {},
                service_animal_statement=str(
                    row.get("service_animal_statement") or ""),
                categories=_classify_policy(row, brand),
                origin="policy_record"))
    return tuple(out)


def load_exclusions() -> Tuple[BenchmarkRecord, ...]:
    """Every committed VERIFIED_NO_PETS row, as a benchmark.

    The exclusion REGISTRY is the no-pets authority in this repository -- never
    a census annotation -- so this is the only place a no-pets benchmark comes
    from.
    """
    out: List[BenchmarkRecord] = []
    for path in _repo_glob(EXCLUSION_GLOB):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        market = str(data.get("market_id") or "")
        for row in data.get("exclusions") or ():
            url = str(row.get("source_url") or "").strip()
            if not url.startswith("http"):
                continue
            brand = brand_of(url)
            quote = str(row.get("evidence_quote") or "")
            cats = [CAT_NO_PETS]
            if brand in DYNAMIC_BRANDS:
                cats.append(CAT_DYNAMIC)
            if brand in DIFFICULT_BRANDS:
                cats.append(CAT_DIFFICULT)
            if brand.startswith(INDEPENDENT_PREFIX):
                cats.append(CAT_INDEPENDENT)
            out.append(BenchmarkRecord(
                identity_key=str(row.get("identity_key")
                                 or row.get("normalized_name") or ""),
                name=str(row.get("canonical_name") or ""),
                market_id=str(row.get("market_id") or market),
                brand=brand, bucket=bucket_of(brand), source_url=url,
                pets_allowed=False, facts={"pets_allowed": False},
                quotes=(quote,) if quote else (),
                withheld_fields={}, service_animal_statement="",
                categories=frozenset(cats), origin="exclusion_registry"))
    return tuple(out)


def load_corpus() -> Tuple[BenchmarkRecord, ...]:
    """Policy records and exclusions together, de-duplicated and ordered.

    De-duplication is by SOURCE URL: a property that appears both as a
    published policy and as an exclusion would otherwise be selectable twice
    with two contradictory benchmarks. The policy record wins, because it is
    the richer comparison and because an exclusion is the coarser statement.
    """
    seen: Dict[str, BenchmarkRecord] = {}
    for record in load_policy_records() + load_exclusions():
        if record.brand in EXCLUDED_BRANDS:
            continue
        key = record.source_url.rstrip("/").lower()
        if key not in seen:
            seen[key] = record
    return tuple(sorted(seen.values(),
                        key=lambda r: (r.bucket, r.brand, r.identity_key,
                                       r.source_url)))


# --------------------------------------------------------------------------- #
# Sampling.
# --------------------------------------------------------------------------- #

class CorpusError(ValueError):
    """The corpus cannot supply the sample that was asked for."""


def _sub_brand(record: BenchmarkRecord) -> str:
    """Within MIXED, the thing to spread across. A MIXED bucket of five Drury
    properties would measure Drury, not "everything else".

    Every independent site collapses to one group: five different one-property
    hotel websites are five instances of the same question ("can this reach an
    unbranded first-party page"), and treating them as five distinct
    sub-brands would let them crowd out the named chains the work order asks
    for.
    """
    return (INDEPENDENT_PREFIX if record.brand.startswith(INDEPENDENT_PREFIX)
            else record.brand)


def _mixed_preference(sub_brand: str) -> int:
    """Position in the work order's preferred MIXED list; last if unlisted."""
    try:
        return MIXED_PREFERRED_BRANDS.index(sub_brand)
    except ValueError:
        return len(MIXED_PREFERRED_BRANDS)


def select_sample(corpus: Sequence[BenchmarkRecord], *,
                  per_bucket: int,
                  minimums: Mapping[str, int]) -> Tuple[BenchmarkRecord, ...]:
    """Choose ``per_bucket`` properties from each bucket, deterministically.

    Two phases, and the order matters:

    1. COVERAGE. The required categories are satisfied first, rarest in the
       corpus first, because a category with four candidates loses every tie
       to one with ninety and would otherwise never be picked.
    2. FILL. Remaining slots go to the richest unselected candidate in each
       bucket.

    Every comparison ends in ``identity_key`` so the same corpus always yields
    the same thirty properties. A sample that changed between runs would make
    two runs incomparable, which is the whole point of running two.
    """
    by_bucket: Dict[str, List[BenchmarkRecord]] = {b: [] for b in BUCKETS}
    for record in corpus:
        by_bucket.setdefault(record.bucket, []).append(record)

    short = [b for b in BUCKETS if len(by_bucket.get(b, ())) < per_bucket]
    if short:
        raise CorpusError(
            "the corpus cannot fill %s: %s"
            % (short, {b: len(by_bucket.get(b, ())) for b in short}))

    chosen: Dict[str, List[BenchmarkRecord]] = {b: [] for b in BUCKETS}
    taken: set = set()

    def room(bucket: str) -> bool:
        return len(chosen[bucket]) < per_bucket

    def sub_brands(bucket: str) -> List[str]:
        return [_sub_brand(r) for r in chosen[bucket]]

    def rank(record: BenchmarkRecord) -> Tuple:
        # Inside MIXED: first take a sub-brand not yet represented, then work
        # down the work order's preferred list, then fall back to richness.
        # Both keys are inert outside MIXED.
        if record.bucket == MIXED_BUCKET:
            sub = _sub_brand(record)
            duplicate = sub in sub_brands(MIXED_BUCKET)
            preference = _mixed_preference(sub)
        else:
            duplicate, preference = False, 0
        return (duplicate, preference, -record.richness(),
                record.identity_key, record.source_url)

    availability = {category: sum(1 for r in corpus if category in r.categories)
                    for category in minimums}
    for category in sorted(minimums, key=lambda c: (availability[c], c)):
        needed = minimums[category]
        have = sum(1 for b in BUCKETS for r in chosen[b]
                   if category in r.categories)
        while have < needed:
            candidates = [r for r in corpus
                          if category in r.categories
                          and id(r) not in taken
                          and room(r.bucket)]
            if not candidates:
                raise CorpusError(
                    "cannot reach %d properties in category %r; the corpus "
                    "offers %d and the buckets with room hold none of them"
                    % (needed, category, availability[category]))
            # Prefer the bucket with the most room, so coverage does not
            # exhaust one brand before the fill phase starts.
            best = min(candidates,
                       key=lambda r: (-(per_bucket - len(chosen[r.bucket])),)
                       + rank(r))
            chosen[best.bucket].append(best)
            taken.add(id(best))
            have += 1

    for bucket in BUCKETS:
        while room(bucket):
            candidates = [r for r in by_bucket[bucket] if id(r) not in taken]
            if not candidates:
                raise CorpusError("bucket %r ran out of candidates" % bucket)
            best = min(candidates, key=rank)
            chosen[bucket].append(best)
            taken.add(id(best))

    ordered: List[BenchmarkRecord] = []
    for bucket in BUCKETS:
        ordered.extend(sorted(chosen[bucket],
                              key=lambda r: (r.brand, r.identity_key)))
    return tuple(ordered)


def coverage(sample: Sequence[BenchmarkRecord]) -> Dict[str, int]:
    return {category: sum(1 for r in sample if category in r.categories)
            for category in CATEGORIES}


__all__ = [
    "POLICY_GLOB", "EXCLUSION_GLOB", "BRAND_HOSTS", "NAMED_BUCKETS",
    "MIXED_BUCKET", "BUCKETS", "EXCLUDED_BRANDS", "INDEPENDENT_PREFIX",
    "MIXED_PREFERRED_BRANDS",
    "CATEGORIES", "CAT_NO_PETS", "CAT_STRUCTURED_POSITIVE", "CAT_CONTRADICTION",
    "CAT_DYNAMIC", "CAT_DIFFICULT", "CAT_SPECIES", "CAT_DOGS_ONLY",
    "CAT_TIERED_FEE", "CAT_SERVICE_ANIMAL", "CAT_CLEANING",
    "CAT_COMBINED_WEIGHT", "CAT_DIMENSIONS", "CAT_INDEPENDENT",
    "DYNAMIC_BRANDS", "DIFFICULT_BRANDS", "brand_of", "bucket_of",
    "BenchmarkRecord", "load_policy_records", "load_exclusions", "load_corpus",
    "CorpusError", "select_sample", "coverage",
]
