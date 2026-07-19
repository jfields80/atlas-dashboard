"""AES-DATA-004I -- Columbus lodging launch-inventory reconciliation.

Pure, deterministic, zero-network logic that reconciles every verified
Columbus lodging record -- production seed rows plus the operational importer
candidates from the 004D/004E/004G waves -- into one canonical catalog with
conservative duplicate grouping, freshness precedence, a proposed promotion
set, and the fixed beta-threshold decision.

Mutation is NOT performed here: the proposed promotions flow through the
EXISTING, tested approve->staging->promote pipeline
(``scripts/approve_import_candidate.py`` / ``scripts/promote_import_candidates.py``),
which re-validates every row against the real launch build before the seed
CSV is ever touched. This module only decides WHAT should be promoted and
proves WHY, with a deterministic reason on every merge and exclusion.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlsplit

# --------------------------------------------------------------------------- #
# Source classes (Task 1).
# --------------------------------------------------------------------------- #

SOURCE_PRODUCTION_EXISTING = "PRODUCTION_EXISTING"
SOURCE_IMPORTER_READY = "IMPORTER_READY"
SOURCE_IMPORTER_REVIEW = "IMPORTER_REVIEW"
SOURCE_IMPORTER_REJECT_NO_PETS = "IMPORTER_REJECT_NO_PETS"
SOURCE_DISCOVERY_ONLY = "DISCOVERY_ONLY"
SOURCE_EXCLUDED = "EXCLUDED"
SOURCE_DUPLICATE = "DUPLICATE"

SOURCE_CLASSES = frozenset({
    SOURCE_PRODUCTION_EXISTING, SOURCE_IMPORTER_READY, SOURCE_IMPORTER_REVIEW,
    SOURCE_IMPORTER_REJECT_NO_PETS, SOURCE_DISCOVERY_ONLY, SOURCE_EXCLUDED,
    SOURCE_DUPLICATE,
})

# Threshold decision labels (Task 9; fixed before any result is seen).
DECISION_BETA_THRESHOLD_REACHED = "BETA_THRESHOLD_REACHED"
DECISION_ONE_MORE_BATCH = "ONE_MORE_ACCESSIBLE_BATCH_REQUIRED"
DECISION_STRATEGY_REVIEW = "LODGING_STRATEGY_REVIEW_REQUIRED"


# --------------------------------------------------------------------------- #
# Normalization helpers (aligned with lodging_accessibility_plan.py).
# --------------------------------------------------------------------------- #

def normalize_name(name: str) -> str:
    n = (name or "").lower().replace("&", "and")
    n = re.sub(r"[^a-z0-9 ]+", " ", n)
    return " ".join(n.split())


def normalize_url(url: str) -> str:
    parts = urlsplit(url or "")
    host = (parts.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = (parts.path or "").rstrip("/").lower()
    return host + path


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    return digits[-10:] if len(digits) >= 10 else digits


def _name_compatible(a: str, b: str) -> bool:
    """Compatible-name check for strong-signal corroboration: exact
    normalized equality, or one name's token set contained in the other's
    (brand-qualifier variants: "Aloft Columbus University District" vs
    "Aloft by Marriott Columbus University District"). Never used alone."""
    na, nb = normalize_name(a), normalize_name(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    ta, tb = set(na.split()), set(nb.split())
    return ta <= tb or tb <= ta


# --------------------------------------------------------------------------- #
# Duplicate grouping (Task 6): strong signals only.
# --------------------------------------------------------------------------- #

def _addresses_contradict(rec_a: Dict, rec_b: Dict) -> bool:
    """True when BOTH records carry a street address and those addresses
    describe clearly different locations (neither equal nor one contained in
    the other after normalization). Two sister properties of one chain often
    share a central reservations phone and near-identical names -- a stated,
    conflicting street address is the deterministic signal that they are
    different buildings (live case: InTown Suites I-70E vs InTown Suites
    Dublin, merged in error via the chain's shared 1-888 number until this
    guard). Formatting-only variants ("Rd" vs "Road") may defeat the
    containment check; that failure mode is conservative -- the records stay
    separate and the downstream proposed-inventory validation flags any
    resulting name+city collision instead of silently double-promoting."""
    addr_a = normalize_name(rec_a.get("address", ""))
    addr_b = normalize_name(rec_b.get("address", ""))
    if not addr_a or not addr_b:
        return False
    if addr_a == addr_b or addr_a in addr_b or addr_b in addr_a:
        return False
    return True


def duplicate_reason(rec_a: Dict, rec_b: Dict) -> str:
    """Return a deterministic strong-signal reason when two catalog records
    describe the same real-world property, else "". Weak signals (same
    chain/domain/city, similar name, nearby coordinates) NEVER merge alone;
    a stated address contradiction blocks every signal except an exact
    official-property-URL match."""
    # Property-page URL signal. ``dedup_url`` is the record's PROPERTY-
    # SPECIFIC page (a candidate's requested fetch URL; a production row's
    # website_url) -- never the site-declared canonical, which chains often
    # point at a shared city hub (live case: both Columbus InTown Suites
    # properties canonicalize to the same /ohio/columbus/ hub page, which
    # must not merge two different buildings).
    url_a = normalize_url(rec_a.get("dedup_url") or rec_a.get("official_url", ""))
    url_b = normalize_url(rec_b.get("dedup_url") or rec_b.get("official_url", ""))
    if url_a and url_a == url_b:
        return "same_official_property_url"
    if _addresses_contradict(rec_a, rec_b):
        return ""
    name_ok = _name_compatible(rec_a.get("canonical_name", ""), rec_b.get("canonical_name", ""))
    addr_a = normalize_name(rec_a.get("address", ""))
    addr_b = normalize_name(rec_b.get("address", ""))
    if addr_a and addr_a == addr_b and name_ok:
        return "same_normalized_address_and_compatible_name"
    phone_a, phone_b = normalize_phone(rec_a.get("phone", "")), normalize_phone(rec_b.get("phone", ""))
    if phone_a and len(phone_a) == 10 and phone_a == phone_b and name_ok:
        return "same_phone_and_compatible_name"
    # Exact-name-and-city match: catches production row vs candidate where
    # the URL differs (e.g. brand URL vs property-own-domain URL) and no
    # phone/address is available on one side. Exact normalized equality
    # only -- "similar" names never merge.
    if (normalize_name(rec_a.get("canonical_name", "")) == normalize_name(rec_b.get("canonical_name", ""))
            and normalize_name(rec_a.get("city", "")) == normalize_name(rec_b.get("city", ""))
            and normalize_name(rec_a.get("canonical_name", ""))):
        return "same_exact_name_and_city"
    return ""


def group_duplicates(records: Sequence[Dict]) -> List[Dict]:
    """Union-find over strong-signal pairs. Returns groups (size >= 2) with
    per-pair reasons; deterministic order by lowest member source_id."""
    parent = {r["source_id"]: r["source_id"] for r in records}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    by_id = {r["source_id"]: r for r in records}
    pair_reasons = []
    ids = sorted(by_id)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            reason = duplicate_reason(by_id[a], by_id[b])
            if reason:
                union(a, b)
                pair_reasons.append({"a": a, "b": b, "reason": reason})

    groups: Dict[str, List[str]] = {}
    for sid in ids:
        groups.setdefault(find(sid), []).append(sid)
    out = []
    for root, members in sorted(groups.items()):
        if len(members) < 2:
            continue
        out.append({
            "group_id": root,
            "members": sorted(members),
            "pair_reasons": [p for p in pair_reasons
                             if p["a"] in members and p["b"] in members],
        })
    return out


# --------------------------------------------------------------------------- #
# Freshness precedence (Task 7).
# --------------------------------------------------------------------------- #

_CLASS_PRECEDENCE = {
    # Only these classes can be canonical for a PET-FRIENDLY property.
    SOURCE_PRODUCTION_EXISTING: 0,
    SOURCE_IMPORTER_READY: 1,
    SOURCE_IMPORTER_REVIEW: 2,
    SOURCE_IMPORTER_REJECT_NO_PETS: 3,
}


def choose_canonical(members: List[Dict]) -> Tuple[Dict, List[Dict], str]:
    """Pick the canonical record of a duplicate group.

    Rules (Task 7, in order): a production record is retained over any
    candidate unless the candidate is READY *and* strictly newer *and* at
    least as rich (existing production continuity wins ties); a READY
    candidate is retained over a REVIEW/REJECT variant of the same property
    regardless of recency (doctrine #2: REVIEW is never promotable, so it
    can never supersede a promotable record -- its existence is preserved,
    not silently dropped)."""
    def sort_key(r):
        return (
            _CLASS_PRECEDENCE.get(r["source_class"], 9),
            # newer verification date wins WITHIN the same class
            "" if not r.get("verified_at") else "",
        )
    prod = [r for r in members if r["source_class"] == SOURCE_PRODUCTION_EXISTING]
    ready = [r for r in members if r["source_class"] == SOURCE_IMPORTER_READY]
    if prod:
        newer_ready = [
            r for r in ready
            if (r.get("verified_at", "") > max(p.get("verified_at", "") for p in prod))
            and len(r.get("policy_fields", {})) >= len(prod[0].get("policy_fields", {}))]
        if newer_ready:
            canonical = sorted(newer_ready, key=lambda r: r["source_id"])[0]
            reason = "newer_ready_candidate_supersedes_production"
        else:
            canonical = sorted(prod, key=lambda r: r["source_id"])[0]
            reason = "production_continuity_retained"
    elif ready:
        canonical = sorted(ready, key=lambda r: r["source_id"])[0]
        reason = "ready_candidate_over_non_promotable_variant" if len(members) > 1 else "only_ready"
    else:
        canonical = sorted(members, key=lambda r: (
            _CLASS_PRECEDENCE.get(r["source_class"], 9), r["source_id"]))[0]
        reason = "highest_class_precedence"
    superseded = [r for r in members if r["source_id"] != canonical["source_id"]]
    return (canonical, superseded, reason)


# --------------------------------------------------------------------------- #
# Threshold (Task 9). Fixed decision rule; never adjusted post hoc.
# --------------------------------------------------------------------------- #

def threshold_decision(total_verified_pet_friendly: int) -> str:
    if total_verified_pet_friendly >= 25:
        return DECISION_BETA_THRESHOLD_REACHED
    if total_verified_pet_friendly >= 15:
        return DECISION_ONE_MORE_BATCH
    return DECISION_STRATEGY_REVIEW


# --------------------------------------------------------------------------- #
# Launch-inventory validation (Task 10) -- proposed-set structural checks.
# The authoritative row-level validation still happens inside the existing
# promote pipeline; these checks catch reconciliation-level mistakes first.
# --------------------------------------------------------------------------- #

def validate_proposed_inventory(
    production_rows: Sequence[Dict], promotions: Sequence[Dict],
) -> List[str]:
    errors: List[str] = []
    seen_names = {}
    seen_urls = {}
    for row in list(production_rows) + list(promotions):
        key = (normalize_name(row.get("canonical_name") or row.get("name", "")),
               normalize_name(row.get("city", "")))
        if key in seen_names:
            errors.append("duplicate_property:%s|%s" % key)
        seen_names[key] = True
        u = normalize_url(row.get("official_url") or row.get("website_url", ""))
        if u:
            if u in seen_urls:
                errors.append("duplicate_official_url:%s" % u)
            seen_urls[u] = True
    for p in promotions:
        if p.get("source_class") != SOURCE_IMPORTER_READY:
            errors.append("non_ready_promotion:%s" % p.get("source_id"))
        if p.get("recommendation") != "READY":
            errors.append("non_ready_recommendation:%s" % p.get("source_id"))
        if p.get("pets_allowed") != "true":
            errors.append("pet_friendly_promotion_without_pets_allowed:%s" % p.get("source_id"))
        for field in ("canonical_name", "address", "city", "state", "official_url"):
            if not (p.get(field) or "").strip():
                errors.append("missing_identity_field:%s:%s" % (p.get("source_id"), field))
    return errors
