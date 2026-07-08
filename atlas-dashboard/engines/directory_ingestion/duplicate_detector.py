"""
Module 3 — Duplicate Detection
==============================

Detects duplicate listings using deterministic blocking + weighted fuzzy
similarity, clusters them via union-find, selects a canonical record, and
emits a merge recommendation per cluster.

Pure Python — no external fuzzy-matching dependency.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Optional

from engines.directory_ingestion.ingestion_models import (
    DuplicateCluster,
    DuplicatePair,
    DuplicateReport,
    MergeRecommendation,
    NormalizedListing,
)

# ---------------------------------------------------------------------------
# Named constants — signal weights sum to 1.0
# ---------------------------------------------------------------------------

_WEIGHT_NAME = 0.35
_WEIGHT_PHONE = 0.20
_WEIGHT_WEBSITE = 0.15
_WEIGHT_ADDRESS = 0.15
_WEIGHT_GEO = 0.10
_WEIGHT_CITY_STATE = 0.05

# A pair is a duplicate candidate above this weighted similarity.
DUPLICATE_THRESHOLD = 0.60
# Above this, the cluster can be auto-merged; between thresholds → REVIEW.
AUTO_MERGE_THRESHOLD = 0.85

# Exact contact matches are decisive even if other signals are weak.
_EXACT_PHONE_SIMILARITY = 1.0
_EXACT_WEBSITE_SIMILARITY = 1.0

# Geo proximity: full credit within this radius (km), zero beyond max.
_GEO_FULL_CREDIT_KM = 0.15
_GEO_ZERO_CREDIT_KM = 2.0
_EARTH_RADIUS_KM = 6371.0

_NAME_STOPWORDS = frozenset(
    {"llc", "inc", "co", "corp", "company", "the", "and", "&", "of", "ltd", "llp"}
)


class DuplicateDetector:
    """Stateless duplicate detector for normalized listings."""

    def detect(self, listings: list[NormalizedListing]) -> DuplicateReport:
        by_id = {l.listing_id: l for l in listings}
        candidate_pairs = self._blocked_pairs(listings)

        scored: list[DuplicatePair] = []
        for id_a, id_b in sorted(candidate_pairs):
            pair = self._score_pair(by_id[id_a], by_id[id_b])
            if pair.similarity >= DUPLICATE_THRESHOLD:
                scored.append(pair)

        clusters = self._build_clusters(scored, by_id)
        duplicate_ids = {lid for c in clusters for lid in c.listing_ids}
        return DuplicateReport(
            clusters=tuple(clusters),
            total_listings=len(listings),
            duplicate_listings=len(duplicate_ids),
            unique_listings=len(listings) - len(duplicate_ids) + len(clusters),
        )

    def canonical_listings(
        self, listings: list[NormalizedListing], report: DuplicateReport
    ) -> list[NormalizedListing]:
        """Collapse each cluster to its canonical record; keep singletons."""
        by_id = {l.listing_id: l for l in listings}
        drop: set[str] = set()
        for cluster in report.clusters:
            for lid in cluster.listing_ids:
                if lid != cluster.canonical_listing_id:
                    drop.add(lid)
        return [l for l in listings if l.listing_id not in drop and l.listing_id in by_id]

    # -- blocking ---------------------------------------------------------------

    def _blocked_pairs(self, listings: list[NormalizedListing]) -> set[tuple[str, str]]:
        """
        Candidate generation via blocking keys. Avoids O(n²) comparison at
        scale while remaining fully deterministic.
        """
        blocks: dict[str, list[str]] = {}

        def add(key: Optional[str], listing_id: str) -> None:
            if key:
                blocks.setdefault(key, []).append(listing_id)

        for l in listings:
            add(self._phone_key(l), l.listing_id)
            add(self._domain_key(l), l.listing_id)
            add(self._name_city_key(l), l.listing_id)
            add(self._geo_key(l), l.listing_id)

        pairs: set[tuple[str, str]] = set()
        for ids in blocks.values():
            ids_sorted = sorted(set(ids))
            for i in range(len(ids_sorted)):
                for j in range(i + 1, len(ids_sorted)):
                    pairs.add((ids_sorted[i], ids_sorted[j]))
        return pairs

    @staticmethod
    def _phone_key(l: NormalizedListing) -> Optional[str]:
        if not l.phone.value:
            return None
        return "ph:" + re.sub(r"\D", "", l.phone.value)

    @staticmethod
    def _domain_key(l: NormalizedListing) -> Optional[str]:
        if not l.website.value:
            return None
        domain = l.website.value.split("//", 1)[-1].split("/", 1)[0]
        return "dm:" + domain.removeprefix("www.")

    def _name_city_key(self, l: NormalizedListing) -> Optional[str]:
        tokens = self._name_tokens(l.business_name)
        if not tokens:
            return None
        city = (l.city.value or "").lower()
        return f"nc:{sorted(tokens)[0]}:{city}"

    @staticmethod
    def _geo_key(l: NormalizedListing) -> Optional[str]:
        if l.latitude is None or l.longitude is None:
            return None
        # ~1km grid cells
        return f"geo:{round(l.latitude, 2)}:{round(l.longitude, 2)}"

    # -- pair scoring -------------------------------------------------------------

    def _score_pair(self, a: NormalizedListing, b: NormalizedListing) -> DuplicatePair:
        signals: list[str] = []

        name_sim = self._token_similarity(
            self._name_tokens(a.business_name), self._name_tokens(b.business_name)
        )
        if name_sim >= 0.8:
            signals.append("name")

        phone_sim = 0.0
        if a.phone.value and b.phone.value:
            phone_sim = _EXACT_PHONE_SIMILARITY if a.phone.value == b.phone.value else 0.0
            if phone_sim:
                signals.append("phone")

        website_sim = 0.0
        if self._domain_key(a) and self._domain_key(a) == self._domain_key(b):
            website_sim = _EXACT_WEBSITE_SIMILARITY
            signals.append("website")

        address_sim = self._token_similarity(
            self._address_tokens(a.address.value), self._address_tokens(b.address.value)
        )
        if address_sim >= 0.8:
            signals.append("address")

        geo_sim = self._geo_similarity(a, b)
        if geo_sim >= 0.8:
            signals.append("coordinates")

        city_state_sim = self._city_state_similarity(a, b)
        if city_state_sim == 1.0:
            signals.append("city_state")

        similarity = round(
            name_sim * _WEIGHT_NAME
            + phone_sim * _WEIGHT_PHONE
            + website_sim * _WEIGHT_WEBSITE
            + address_sim * _WEIGHT_ADDRESS
            + geo_sim * _WEIGHT_GEO
            + city_state_sim * _WEIGHT_CITY_STATE,
            4,
        )
        return DuplicatePair(
            listing_id_a=min(a.listing_id, b.listing_id),
            listing_id_b=max(a.listing_id, b.listing_id),
            similarity=similarity,
            matched_signals=tuple(signals),
        )

    # -- clustering ----------------------------------------------------------------

    def _build_clusters(
        self, pairs: list[DuplicatePair], by_id: dict[str, NormalizedListing]
    ) -> list[DuplicateCluster]:
        parent: dict[str, str] = {}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x: str, y: str) -> None:
            rx, ry = find(x), find(y)
            if rx != ry:
                # deterministic: smaller id becomes root
                if rx < ry:
                    parent[ry] = rx
                else:
                    parent[rx] = ry

        for p in pairs:
            parent.setdefault(p.listing_id_a, p.listing_id_a)
            parent.setdefault(p.listing_id_b, p.listing_id_b)
            union(p.listing_id_a, p.listing_id_b)

        members: dict[str, list[str]] = {}
        for lid in parent:
            members.setdefault(find(lid), []).append(lid)

        clusters: list[DuplicateCluster] = []
        for root, ids in sorted(members.items()):
            if len(ids) < 2:
                continue
            ids_sorted = tuple(sorted(ids))
            cluster_pairs = tuple(
                p for p in pairs
                if p.listing_id_a in ids_sorted and p.listing_id_b in ids_sorted
            )
            confidence = round(
                sum(p.similarity for p in cluster_pairs) / len(cluster_pairs), 4
            )
            recommendation = (
                MergeRecommendation.AUTO_MERGE
                if confidence >= AUTO_MERGE_THRESHOLD
                else MergeRecommendation.REVIEW
            )
            canonical = self._select_canonical([by_id[i] for i in ids_sorted])
            clusters.append(
                DuplicateCluster(
                    cluster_id="dup_" + hashlib.sha256("|".join(ids_sorted).encode()).hexdigest()[:12],
                    listing_ids=ids_sorted,
                    canonical_listing_id=canonical,
                    confidence=confidence,
                    merge_recommendation=recommendation,
                    pairs=cluster_pairs,
                )
            )
        return clusters

    @staticmethod
    def _select_canonical(listings: list[NormalizedListing]) -> str:
        """
        Canonical record = most trustworthy + most complete.
        Order: verified desc, confidence desc, populated fields desc, id asc.
        """
        def populated(l: NormalizedListing) -> int:
            fields = (l.address, l.city, l.state, l.zip_code, l.phone,
                      l.website, l.email, l.description, l.hours)
            return sum(1 for tv in fields if tv.value) + (
                1 if l.latitude is not None else 0
            )

        ranked = sorted(
            listings,
            key=lambda l: (-int(l.verified), -l.confidence, -populated(l), l.listing_id),
        )
        return ranked[0].listing_id

    # -- similarity primitives ---------------------------------------------------------

    @staticmethod
    def _name_tokens(name: str) -> frozenset[str]:
        tokens = re.sub(r"[^a-z0-9\s]", " ", name.lower()).split()
        return frozenset(t for t in tokens if t not in _NAME_STOPWORDS)

    @staticmethod
    def _address_tokens(address: Optional[str]) -> frozenset[str]:
        if not address:
            return frozenset()
        return frozenset(re.sub(r"[^a-z0-9\s]", " ", address.lower()).split())

    @staticmethod
    def _token_similarity(a: frozenset[str], b: frozenset[str]) -> float:
        """Jaccard similarity over token sets. 0.0 when either side empty."""
        if not a or not b:
            return 0.0
        return len(a & b) / len(a | b)

    def _geo_similarity(self, a: NormalizedListing, b: NormalizedListing) -> float:
        if None in (a.latitude, a.longitude, b.latitude, b.longitude):
            return 0.0
        km = self._haversine_km(a.latitude, a.longitude, b.latitude, b.longitude)
        if km <= _GEO_FULL_CREDIT_KM:
            return 1.0
        if km >= _GEO_ZERO_CREDIT_KM:
            return 0.0
        return round(
            1.0 - (km - _GEO_FULL_CREDIT_KM) / (_GEO_ZERO_CREDIT_KM - _GEO_FULL_CREDIT_KM),
            4,
        )

    @staticmethod
    def _city_state_similarity(a: NormalizedListing, b: NormalizedListing) -> float:
        if not (a.city.value and b.city.value and a.state.value and b.state.value):
            return 0.0
        same = (
            a.city.value.lower() == b.city.value.lower()
            and a.state.value == b.state.value
        )
        return 1.0 if same else 0.0

    @staticmethod
    def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        p1, p2 = math.radians(lat1), math.radians(lat2)
        dp = math.radians(lat2 - lat1)
        dl = math.radians(lng2 - lng1)
        h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        return 2 * _EARTH_RADIUS_KM * math.asin(math.sqrt(h))
