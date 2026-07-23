"""AES-SITE-001 -- Columbus site build: deterministic data helpers.

Pure functions only (no network, no writes). Loads the exact structured
pet-policy evidence already produced by the importer (READY candidates from
the 004D/004E/004G operational waves) and matches it to the 25 promoted
production hotel rows by normalized name -- the SAME matching discipline
``lodging_reconciliation.py`` uses. This lets hotel profile pages show a
real fact TABLE (species/fee/fee-basis/count/weight/restrictions/verified
date/evidence count) instead of only the flat composed sentence already in
the seed CSV, without ever inventing a fact the importer didn't evidence.

Also provides deterministic, address-based (never name-based) corridor
assignment and city-based "nearby" grouping (no coordinates exist in the
production schema, so distance is never fabricated -- see the module
docstring in ``site_enrichment.py`` for the doctrine this follows).
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_CSV = REPO_ROOT / "launch_packages" / "pettripfinder" / "seed_businesses.csv"
# Tracked, publishable verified hotel-policy facts (PTF-PROD-002A). Exported
# from the approved READY importer candidates by
# scripts/pettripfinder/export_hotel_policy_facts.py. This is the DEFAULT source
# the Columbus generator loads -- it is committed, so normal site generation
# never requires the gitignored operational data/import corpus.
PUBLISHED_FACTS_PATH = REPO_ROOT / "launch_packages" / "pettripfinder" / "hotel_policy_facts.json"

# Isolated worker-promotion corpus root (PETTRIPFINDER-PROD-003 Gate 2). It is
# STRICTLY ADDITIVE and LOWEST precedence: it may introduce a NEW hotel but never
# overrides an existing importer record for the same normalized name (see the
# additive_only guard in load_hotel_policy_facts). Like every candidate root it
# is optional -- an absent directory is skipped, and reading never creates it.
# This is operational data, not committed production authority; site generation
# still reads only the committed launch package (load_published_hotel_policy_facts).
WORKER_PROMOTION_ROOT = REPO_ROOT / "data" / "import" / "columbus_worker_promotion"

CANDIDATE_ROOTS = (
    REPO_ROOT / "data" / "import" / "columbus_lodging_wave1",
    REPO_ROOT / "data" / "import" / "columbus_lodging_source_strategy_validation",
    REPO_ROOT / "data" / "import" / "columbus_accessible_lodging_wave" / "run_001",
    WORKER_PROMOTION_ROOT,   # final, lowest-precedence, additive-only (never overrides)
)

_POLICY_FIELDS = ("pets_allowed", "species_allowed", "pet_fee", "fee_basis",
                  "pet_count_limit", "weight_limit", "breed_restrictions",
                  "unattended_policy", "general_restrictions")


def normalize_name(name: str) -> str:
    n = (name or "").lower().replace("&", "and")
    n = re.sub(r"[^a-z0-9 ]+", " ", n)
    return " ".join(n.split())


def read_production_rows() -> List[Dict[str, str]]:
    with PRODUCTION_CSV.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_hotel_policy_facts() -> Dict[str, Dict]:
    """normalized production hotel name -> {facts, verified_at,
    evidence_count, source_relationship, source_url, candidate_provenance}.
    Only READY candidates are considered (the same promotion gate already
    enforced in production); a production row with no matching READY
    candidate (should not happen post-004I, but handled honestly) is simply
    absent from the returned map -- callers must fall back to the CSV's
    composed ``pet_policy`` sentence, never fabricate a table."""
    out: Dict[str, Dict] = {}
    for root in CANDIDATE_ROOTS:
        # The worker-promotion root is additive-only: it never overrides a name
        # already provided by an earlier importer root, and within itself the
        # deterministic sorted-first candidate wins a normalized-name collision.
        additive_only = root == WORKER_PROMOTION_ROOT
        cand_dir = root / "candidates"
        if not cand_dir.exists():
            continue
        for path in sorted(cand_dir.glob("*.json")):
            with path.open(encoding="utf-8") as f:
                d = json.load(f)
            if d.get("recommendation") != "READY":
                continue
            proposed = dict(d.get("proposed_fields", []))
            facts = dict(d.get("pet_facts", []))
            name = normalize_name(proposed.get("name", ""))
            if not name:
                continue
            if additive_only and name in out:
                continue                    # fail closed: never overwrite an existing record
            out[name] = {
                "facts": {k: v for k, v in facts.items() if k in _POLICY_FIELDS},
                "verified_at": d.get("snapshot", {}).get("observed_at", ""),
                "evidence_count": len(d.get("evidence", [])),
                "source_relationship": d.get("source_relationship", ""),
                "source_url": proposed.get("source_url", ""),
                "candidate_id": d.get("candidate_id", ""),
                # The exact composed policy sentence recorded for the READY
                # candidate -- surfaced so the profile renderer can show the
                # verbatim "exact recorded wording" evidence toggle (parity with
                # the approved design). None when the source stated nothing.
                "evidence_quote": proposed.get("pet_policy", "") or None,
            }
    return out


def load_published_hotel_policy_facts() -> Dict[str, Dict]:
    """The DEFAULT verified-facts source for the Columbus generator: the tracked
    launch package (PUBLISHED_FACTS_PATH), keyed by normalized name in the exact
    shape build_vm_from_production consumes. Committed, deterministic, and free
    of any operational/import dependency -- normal generation works in a clean
    checkout. Returns {} if the package is absent (e.g. before its first export)."""
    if not PUBLISHED_FACTS_PATH.exists():
        return {}
    data = json.loads(PUBLISHED_FACTS_PATH.read_text(encoding="utf-8"))
    out: Dict[str, Dict] = {}
    for h in data.get("hotels", []):
        out[h["key"]] = {
            "facts": dict(h.get("facts", {})),
            "verified_at": h.get("verified_at", ""),
            "evidence_count": h.get("evidence_count", 0),
            "source_relationship": h.get("source_type", ""),
            "source_url": h.get("source_url", ""),
            "evidence_quote": h.get("evidence_quote") or None,
        }
    return out


# --------------------------------------------------------------------------- #
# Corridor assignment (Task 7). Address-token based ONLY -- the classifier
# never reads the business name, so a hotel named "... Downtown" is placed
# in the Downtown corridor because its STREET carries a downtown signal, not
# because of its marketing name (doctrine: "Do not assign areas merely from
# property marketing names").
# --------------------------------------------------------------------------- #

CORRIDOR_DOWNTOWN = "Downtown Columbus"
CORRIDOR_DUBLIN = "Dublin"

# "nationwide blvd"/"state street"/"capitol square" are unambiguous -- those
# streets exist only in/immediately around downtown Columbus. "high st"
# alone is NOT unambiguous: High Street runs the entire north-south length
# of the city (Worthington, Clintonville, Short North, downtown, German
# Village), so a bare substring match would misclassify a property miles
# away (live case: "7480 North High St" is Worthington, not downtown).
# Columbus's street numbering originates at the Broad & High intersection
# downtown and increases with distance from it -- an address-derived,
# non-fabricated proxy: only a LOW High Street number is treated as
# downtown, never High Street alone.
_DOWNTOWN_UNAMBIGUOUS_MARKERS = ("nationwide blvd", "state street", "capitol square")
_HIGH_ST_DOWNTOWN_NUMBER_CEILING = 1000
_HIGH_ST_RE = re.compile(r"^\s*(\d+)\s+(?:north|south|n|s)?\.?\s*high\s+st", re.I)


def assign_corridor(address: str, city: str) -> str:
    """Returns a corridor label or "" (no corridor). City=="Dublin" is
    itself a committed, unambiguous corridor signal (Dublin is a distinct
    named suburb, not a Columbus street). Downtown is address-street-token
    based within Columbus city only -- never the business name."""
    city_norm = (city or "").strip().lower()
    if city_norm == "dublin":
        return CORRIDOR_DUBLIN
    if city_norm == "columbus":
        addr_norm = (address or "").strip().lower()
        if any(marker in addr_norm for marker in _DOWNTOWN_UNAMBIGUOUS_MARKERS):
            return CORRIDOR_DOWNTOWN
        m = _HIGH_ST_RE.match(addr_norm)
        if m and int(m.group(1)) < _HIGH_ST_DOWNTOWN_NUMBER_CEILING:
            return CORRIDOR_DOWNTOWN
    return ""


# Minimum properties required before a corridor becomes an indexable route
# (Task 7's explicit threshold).
CORRIDOR_MIN_PROPERTIES = 5


def group_by_corridor(hotel_rows: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    groups: Dict[str, List[Dict[str, str]]] = {}
    for row in hotel_rows:
        corridor = assign_corridor(row.get("address", ""), row.get("city", ""))
        if corridor:
            groups.setdefault(corridor, []).append(row)
    return {c: rows for c, rows in groups.items() if len(rows) >= CORRIDOR_MIN_PROPERTIES}


# --------------------------------------------------------------------------- #
# Nearby relationships (Task 9). City-based grouping only -- the production
# schema carries no coordinates, so a precise "X miles away" claim would be
# fabricated. "Also in <city>" is the honest, approved-data equivalent.
# --------------------------------------------------------------------------- #

NEARBY_MAX_RESULTS = 4


def nearby_same_city(all_rows: List[Dict[str, str]], subject: Dict[str, str],
                     other_category: Optional[str] = None) -> List[Dict[str, str]]:
    """Deterministic same-city neighbors for ``subject``, optionally
    restricted to a different category (e.g. parks near a hotel). Excludes
    the subject itself (by name+category, never by list identity, so a
    record appearing twice in a caller-supplied list is still excluded).
    Alphabetical by name (a stable, content-derived tiebreak -- never
    insertion order, which is not a "real fact"). Capped at
    ``NEARBY_MAX_RESULTS``."""
    city = (subject.get("city", "") or "").strip().lower()
    if not city:
        return []
    subj_key = (normalize_name(subject.get("name", "")), subject.get("category", ""))
    candidates = [
        r for r in all_rows
        if (r.get("city", "") or "").strip().lower() == city
        and (normalize_name(r.get("name", "")), r.get("category", "")) != subj_key
        and (other_category is None or r.get("category") == other_category)
    ]
    candidates.sort(key=lambda r: normalize_name(r.get("name", "")))
    return candidates[:NEARBY_MAX_RESULTS]
