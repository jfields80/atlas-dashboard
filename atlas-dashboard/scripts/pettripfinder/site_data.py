"""AES-SITE-001 -- Columbus site build: deterministic data helpers.

Pure functions only (no network, no writes). Loads the exact structured
pet-policy evidence already produced by the importer (READY candidates from
the 004D/004E/004G operational waves) and matches it to the 25 promoted
production hotel rows by normalized name -- the SAME matching discipline
``lodging_reconciliation.py`` uses. This lets hotel profile pages show a
real fact TABLE (species/fee/fee-basis/count/weight/restrictions/verified
date/evidence count) instead of only the flat composed sentence already in
the seed CSV, without ever inventing a fact the importer didn't evidence.

Also provides the corridor-grouping compatibility wrapper (assignment
itself now lives in the ``scripts/pettripfinder/markets`` configuration
layer, PTF-CORRIDORS-002) and city-based "nearby" grouping (no coordinates
exist in the production schema, so distance is never fabricated -- see the
module docstring in ``site_enrichment.py`` for the doctrine this follows).
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

# fee_tiers (PTF-WORKERS-FEE-TERMS) is a LIST of typed tier dicts, not a
# string like the others -- a stay-length ladder cannot be a scalar without
# losing the thing that makes it a ladder. It is absent on scalar-fee hotels,
# so their records are unchanged.
_POLICY_FIELDS = ("pets_allowed", "species_allowed", "pet_fee", "fee_basis", "fee_tiers", "fee_cap", "fee_conflict", "fee_withheld",
                  "pet_count_limit", "weight_limit", "weight_limit_operator",
                  # PTF-COLUMBUS-HYATT-002. A fact absent from this allowlist
                  # reaches the record and never the page, which is how a
                  # published combined limit would silently vanish.
                  "weight_limit_combined", "weight_limit_combined_operator",
                  "breed_restrictions",
                  # PTF-POLICY-PRECISION-001. Three additive names, each of which
                  # records something a source SAID that the vocabulary could not
                  # previously carry:
                  #   pet_count_scope                the unit the count applies to
                  #                                  (a suite is not a room)
                  #   weight_limit_stated_none       "no weight restrictions" --
                  #   breed_restrictions_stated_none an affirmative statement, not
                  #                                  a gap in the record
                  # Absent means unstated, exactly as before, so every existing
                  # record renders unchanged.
                  "pet_count_scope",
                  "weight_limit_stated_none", "breed_restrictions_stated_none",
                  "unattended_policy", "general_restrictions",
                  # PTF-COLUMBUS-STRUCTURAL-UNRESOLVED-001. Three names South
                  # Wind Motel's policy depends on and Candlewood Suites
                  # Columbus - Grove City's own captured evidence already
                  # populates (pet_room_restriction, reservation_requirement)
                  # but which this allowlist previously dropped on the way
                  # from the authority file into the render layer. Absent
                  # means unstated, exactly as before, so every existing
                  # record renders unchanged.
                  "pet_room_restriction", "eligible_room_types",
                  "reservation_requirement")


def normalize_name(name: str) -> str:
    n = (name or "").lower().replace("&", "and")
    n = re.sub(r"[^a-z0-9 ]+", " ", n)
    return " ".join(n.split())


def read_production_rows() -> List[Dict[str, str]]:
    with PRODUCTION_CSV.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def verified_public_hotels(hotel_rows: List[Dict[str, str]],
                           policy_facts: Dict[str, Dict],
                           *, exclusions: Optional[List[Dict]] = None,
                           check_exclusions: bool = True) -> List[Dict[str, str]]:
    """Deterministic verified-only public-hotel collection (PROD-004): the seed
    hotel display rows whose normalized name matches a committed hotel-policy
    package record. The committed package is the authority -- a seed hotel row
    absent from it is excluded (kept non-public), while a committed policy record
    with no matching display row FAILS CLOSED (raises) rather than silently
    dropping a verified hotel. Never hard-codes a hotel identity; the returned
    rows preserve the seed display order for determinism."""
    rows_by_name: Dict[str, List[Dict[str, str]]] = {}
    for r in hotel_rows:
        rows_by_name.setdefault(normalize_name(r.get("name", "")), []).append(r)
    matched_keys, unmatched, ambiguous = set(), [], []
    for key in sorted(policy_facts):
        matches = rows_by_name.get(key, [])
        if len(matches) == 0:
            unmatched.append(key)
        elif len(matches) > 1:
            ambiguous.append(key)
        else:
            matched_keys.add(key)
    if unmatched or ambiguous:
        raise ValueError(
            "verified-only hotel join failed (fail-closed): committed policy records "
            "with no display row=%s; ambiguous display matches=%s"
            % (sorted(unmatched), sorted(ambiguous)))
    selected = [r for r in hotel_rows if normalize_name(r.get("name", "")) in matched_keys]

    # PTF-EXCLUSIONS-002 -- defence in depth, not a substitute for the
    # promotion-time gate. This is the single join every public hotel surface is
    # derived from (profiles, index, corridors, comparison page, sitemap, and the
    # Netlify release assembler), so an excluded identity that reached BOTH
    # authorities is caught here before a route exists for it.
    #
    # It REFUSES rather than omitting. Silent omission is the documented
    # behaviour for a seed row that is merely unverified -- absent from the
    # policy package, held, and correctly non-public. An identity that is present
    # in both authorities AND excluded is not a held record; it is a
    # contradiction between two authorities, and quietly dropping it would hide
    # the contradiction instead of surfacing it.
    if check_exclusions and selected:
        from scripts.pettripfinder.publication_guard import assert_publishable
        assert_publishable(
            [{"name": r.get("name", ""), "address": r.get("address", ""),
              "postal_code": r.get("postal_code", ""), "category": "pet-friendly-hotels"}
             for r in selected],
            exclusions=exclusions, check_collisions=False)
    return selected


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
                # Additive pass-through (PROD-003 Gate 2 schema 1.1): the raw
                # per-field evidence list and the worker provenance block, present
                # only on worker-promotion candidates (None/[] for importer rows).
                # Existing callers ignore these keys.
                "evidence": list(d.get("evidence", [])),
                "worker_provenance": d.get("worker_provenance"),
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

    # PTF-BREWDOG-PROMOTION-001. A record may carry same_campus_resolution: the
    # id of the reviewed decision that lets it share a street address with a
    # different business. It is the only thing that explains the coexistence to a
    # reader, so an unresolvable reference is worse than none -- it asserts a
    # review that cannot be produced. Validated on every read of the package, so
    # the generator and the release assembler both fail closed, and validated
    # against the SEED address so a reference cannot be pointed at some other
    # campus. Records with no reference are untouched.
    from scripts.pettripfinder.publication_guard import assert_resolution_references

    seed_by_key = {normalize_name(r.get("name", "")): r for r in read_production_rows()
                   if r.get("category") == "pet-friendly-hotels"}
    referenced = [
        {"name": h.get("name") or h.get("key", ""),
         "address": seed_by_key.get(h.get("key", ""), {}).get("address", ""),
         "postal_code": seed_by_key.get(h.get("key", ""), {}).get("postal_code", ""),
         "same_campus_resolution": h["same_campus_resolution"]}
        for h in data.get("hotels", []) if h.get("same_campus_resolution")]
    if referenced:
        assert_resolution_references(referenced)

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
# Corridor grouping (PTF-CORRIDORS-002). The address-token classifier this
# module used to carry is retired: assignment now lives in the shared
# market/corridor configuration layer (``scripts/pettripfinder/markets``),
# driven by the committed ptf-market/1.0 config under
# ``launch_packages/pettripfinder/markets/``. That layer is the ONE
# assignment authority for routes, sitemap, navigation, and display labels;
# this wrapper keeps the historical (hotel_rows) -> {corridor name: rows}
# grouping surface used by the Netlify assembler compatibility path and the
# tests. The doctrine is unchanged: deterministic city/ZIP/explicit
# matching only, never a marketing name, never fuzzy.
# --------------------------------------------------------------------------- #

# Default per-corridor publication minimum (Task 7's original threshold).
# It is now the ptf-market config DEFAULT; each corridor may override it in
# its committed configuration.
CORRIDOR_MIN_PROPERTIES = 5


def group_by_corridor(hotel_rows: List[Dict[str, str]],
                      market=None) -> Dict[str, List[Dict[str, str]]]:
    """Published corridor name -> member rows for ``market``, via the shared
    deterministic assignment. Suppressed corridors (below their configured
    minimum, or empty) are omitted; an ambiguous multi-corridor match fails
    closed (raises) rather than guessing.

    PTF-MULTIMARKET-001: ``market`` is explicit context. Omitted, it is this
    build's named production market -- never 'the only configured one', so
    registering a second market cannot change this grouping."""
    from scripts.pettripfinder.market_context import resolve_market
    from scripts.pettripfinder.markets import assign_hotels
    market = resolve_market(market)
    assignment = assign_hotels(market, hotel_rows)
    return {market.corridor_by_id(cid).name: list(assignment.members_of(cid))
            for cid in assignment.published}


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
