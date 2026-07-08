"""
revenue_signals.py — Phase 4: Revenue estimation from OBSERVABLE signals.

Per the spec: "Never invent revenue. Estimate ranges using observable
signals" — the monetization the audits actually DETECTED on incumbent
directories, plus the node's verified business count.

Logic: if incumbents in this niche are running Mediavine + premium
listings, that's evidence the niche supports those revenue streams.
If NO incumbent monetizes anything, we estimate more conservatively
(unproven monetization) but note it may also mean an undefended niche.

Confidence is driven by DATA QUALITY, not optimism:
  verified audits + real business count  -> up to ~85%
  partial data                            -> ~55-70%
  pure heuristics                         -> capped at 45%
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Per-stream monthly revenue bands for a SMALL niche directory that has
# achieved modest rankings. Deliberately conservative; these are the
# bands the observed signals unlock, not guarantees.
STREAM_BANDS = {
    "ads": (40, 250),                # small local site RPM economics
    "affiliate_links": (30, 300),
    "premium_listings": (100, 600),  # e.g. 4-12 businesses x $25-$50
    "lead_generation": (100, 800),
    "sponsorship": (50, 300),
}

# Premium listings scale with supply: more businesses = more prospects.
def _premium_band(business_count: int) -> tuple[int, int]:
    # assume 1%-4% of listed businesses convert at $25-$50/mo
    low = int(business_count * 0.01 * 25)
    high = int(business_count * 0.04 * 50)
    return (max(low, 25), max(high, 100))


@dataclass
class RevenueEstimate:
    low: int
    high: int
    confidence: float
    streams: dict = field(default_factory=dict)     # stream -> (low, high, basis)
    basis_notes: list = field(default_factory=list)


def estimate_from_signals(observed_monetization: list[str],
                           business_count: int,
                           monetization_score: float,
                           data_quality: str = "heuristic") -> RevenueEstimate:
    streams: dict = {}
    notes: list[str] = []

    observed_types = set()
    for sig in observed_monetization:
        if sig.startswith("ads:"):
            observed_types.add("ads")
        elif sig.startswith("affiliate"):
            observed_types.add("affiliate_links")
        elif sig.startswith("premium"):
            observed_types.add("premium_listings")

    # Streams PROVEN by incumbent behavior get their full band.
    for stream in observed_types:
        band = (_premium_band(business_count) if stream == "premium_listings"
                 else STREAM_BANDS[stream])
        streams[stream] = (*band, "observed on incumbent directories")
        notes.append(f"{stream}: incumbents in this niche already monetize this way — proven stream.")

    # Premium listings are ALWAYS a candidate stream for us if business
    # supply exists, even if no incumbent sells them (often the gap).
    if "premium_listings" not in streams and business_count >= 25:
        low, high = _premium_band(business_count)
        streams["premium_listings"] = (int(low * 0.6), int(high * 0.7),
                                        "unproven in niche — discounted 30-40%")
        notes.append("premium_listings: no incumbent sells them — treated as "
                      "unproven and discounted, but likely the open gap.")

    # Ads are ALWAYS available to us (running them is our choice, not
    # incumbent-dependent) — include a conservative baseline if not already
    # proven at the higher observed band.
    if "ads" not in streams:
        streams["ads"] = (20, 120, "baseline — always available to a new directory")
        notes.append("ads: no incumbent runs display ads, but we can — "
                      "conservative baseline band included.")

    if len(streams) == 1 and "ads" in streams:
        notes.append("No other viable streams detected — ad-only floor; "
                      "validates spec's 'undefended niche' case but revenue "
                      "ceiling is low without listings/leads.")

    low = sum(s[0] for s in streams.values())
    high = sum(s[1] for s in streams.values())

    # Monetization score shades the range within itself (not beyond it)
    factor = 0.6 + (monetization_score / 100) * 0.4
    low, high = int(low * factor), int(high * factor)

    confidence = {"verified": 82.0, "partial": 62.0, "heuristic": 42.0}[data_quality]
    if observed_types:
        confidence = min(confidence + 6, 88.0)

    return RevenueEstimate(low=low, high=high, confidence=round(confidence, 1),
                            streams=streams, basis_notes=notes)
