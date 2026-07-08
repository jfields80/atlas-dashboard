"""
atlas/engines/expansion_classifier.py

Expansion Classifier — deterministic rule table implementing the
Investment OS classification:

    Flagship | Portfolio | Local | Micro | Expansion

Rules:
  - Pure function. Zero I/O, zero database access.
  - Takes evidence (market capacity ceiling, revenue projections,
    geographic scope) + a SynergyReport + PortfolioSnapshot.
  - Returns ExpansionClass with full rationale (explainability rule).
  - The Expansion class is definitionally relative to the portfolio,
    which is why SynergyReport is a required input — not optional.

Classification definitions (from Investment OS design session):
  Flagship   — Top-tier opportunity. High market ceiling (>$10k/mo),
               national/global scope, strong standalone economics.
               May or may not have synergy — it stands alone.
  Portfolio  — Solid standalone opportunity that also fits the portfolio
               mosaic. Lower ceiling than Flagship but reliable.
  Local      — Geographically scoped opportunity (city/region).
               Viable with local monetisation; limited exit multiple.
  Micro      — Small market, fast to launch, low capital.
               Pure machine-gun bet; expect some to fail.
  Expansion  — Adjacent move from an existing owned asset.
               Requires meaningful synergy score; classified as
               Expansion only when synergy is the primary investment
               thesis, not just a nice-to-have.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Avoid circular imports — these types come from other modules
    from engines.portfolio_synergy import SynergyReport
    from services.portfolio_service import PortfolioSnapshot


# ---------------------------------------------------------------------------
# Output type
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ClassificationFactor:
    """One named factor that contributed to the classification decision."""
    name: str
    observed_value: str     # human-readable, e.g. "$8,400/mo ceiling"
    rule_threshold: str     # the threshold this factor tests against
    passed: bool
    rationale: str


@dataclass(frozen=True)
class ExpansionClass:
    label: str                              # Flagship | Portfolio | Local | Micro | Expansion
    confidence: float                       # 0.0–1.0 (how cleanly it fits the class)
    factors: tuple[ClassificationFactor, ...]
    plain_english: str                      # one-sentence summary for the investment memo
    synergy_driven: bool                    # True when synergy was the determining factor


# ---------------------------------------------------------------------------
# Thresholds (named constants — bump version if you change these)
# ---------------------------------------------------------------------------

# Monthly revenue ceiling thresholds (USD)
FLAGSHIP_CEILING_MIN   = 10_000.0
PORTFOLIO_CEILING_MIN  =  3_000.0
LOCAL_CEILING_MIN      =  1_000.0
# Below LOCAL_CEILING_MIN → Micro

# Synergy score thresholds
EXPANSION_SYNERGY_MIN  = 0.55   # synergy must be strong to drive an Expansion label
PORTFOLIO_SYNERGY_MIN  = 0.25   # any meaningful synergy qualifies for Portfolio boost

# Geographic scope values that indicate a local/regional bet
LOCAL_SCOPES = frozenset({"local", "regional"})


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

def classify(
    *,
    market_ceiling_monthly_usd: float,
    geographic_scope: str,              # local | regional | national | global
    conservative_monthly_revenue: float,
    synergy_report: "SynergyReport",
    portfolio_snapshot: "PortfolioSnapshot",
) -> ExpansionClass:
    """
    Classify an opportunity into one of five Investment OS labels.

    Classification is hierarchical — each class is evaluated in order
    from most specific (Expansion) down.  The first label whose conditions
    are fully satisfied is returned, with a confidence score reflecting
    how cleanly the inputs fit.

    Args:
        market_ceiling_monthly_usd: Market Capacity Engine ceiling output.
        geographic_scope:            Scout / DNA geographic scope string.
        conservative_monthly_revenue: Valuation Engine conservative revenue.
        synergy_report:              Output of PortfolioSynergyEngine.score().
        portfolio_snapshot:          The same snapshot consumed by synergy.

    Returns:
        ExpansionClass (frozen dataclass, fully explainable).
    """

    factors: list[ClassificationFactor] = []
    synergy_score = synergy_report.total_score
    has_owned_assets = len(portfolio_snapshot.owned) > 0
    is_local = geographic_scope in LOCAL_SCOPES

    # -----------------------------------------------------------------------
    # Factor evaluation helpers
    # -----------------------------------------------------------------------

    def _factor(
        name: str,
        observed: str,
        threshold: str,
        passed: bool,
        rationale: str,
    ) -> ClassificationFactor:
        f = ClassificationFactor(
            name=name,
            observed_value=observed,
            rule_threshold=threshold,
            passed=passed,
            rationale=rationale,
        )
        factors.append(f)
        return f

    # -----------------------------------------------------------------------
    # Evaluate all factors (all are always evaluated for full explainability)
    # -----------------------------------------------------------------------

    f_ceiling_flagship = _factor(
        name="market_ceiling_flagship",
        observed=f"${market_ceiling_monthly_usd:,.0f}/mo",
        threshold=f">= ${FLAGSHIP_CEILING_MIN:,.0f}/mo",
        passed=market_ceiling_monthly_usd >= FLAGSHIP_CEILING_MIN,
        rationale=(
            f"Market ceiling of ${market_ceiling_monthly_usd:,.0f}/mo "
            f"{'meets' if market_ceiling_monthly_usd >= FLAGSHIP_CEILING_MIN else 'falls short of'} "
            f"the ${FLAGSHIP_CEILING_MIN:,.0f}/mo Flagship threshold."
        ),
    )

    f_ceiling_portfolio = _factor(
        name="market_ceiling_portfolio",
        observed=f"${market_ceiling_monthly_usd:,.0f}/mo",
        threshold=f">= ${PORTFOLIO_CEILING_MIN:,.0f}/mo",
        passed=market_ceiling_monthly_usd >= PORTFOLIO_CEILING_MIN,
        rationale=(
            f"Market ceiling {'exceeds' if market_ceiling_monthly_usd >= PORTFOLIO_CEILING_MIN else 'is below'} "
            f"the ${PORTFOLIO_CEILING_MIN:,.0f}/mo Portfolio floor."
        ),
    )

    f_scope_local = _factor(
        name="geographic_scope_local",
        observed=geographic_scope,
        threshold=f"scope in {sorted(LOCAL_SCOPES)}",
        passed=is_local,
        rationale=(
            f"Geographic scope is '{geographic_scope}', "
            f"which {'is' if is_local else 'is not'} a locally-scoped opportunity."
        ),
    )

    f_synergy_expansion = _factor(
        name="synergy_score_expansion",
        observed=f"{synergy_score:.2f}",
        threshold=f">= {EXPANSION_SYNERGY_MIN:.2f} with owned assets present",
        passed=(synergy_score >= EXPANSION_SYNERGY_MIN and has_owned_assets),
        rationale=(
            f"Synergy score {synergy_score:.2f} "
            f"{'meets' if synergy_score >= EXPANSION_SYNERGY_MIN else 'falls short of'} "
            f"the {EXPANSION_SYNERGY_MIN:.2f} Expansion threshold "
            f"({'owned assets present' if has_owned_assets else 'no owned assets in portfolio'})."
        ),
    )

    f_synergy_portfolio = _factor(
        name="synergy_score_portfolio",
        observed=f"{synergy_score:.2f}",
        threshold=f">= {PORTFOLIO_SYNERGY_MIN:.2f}",
        passed=synergy_score >= PORTFOLIO_SYNERGY_MIN,
        rationale=(
            f"Synergy score {synergy_score:.2f} "
            f"{'exceeds' if synergy_score >= PORTFOLIO_SYNERGY_MIN else 'falls short of'} "
            f"the {PORTFOLIO_SYNERGY_MIN:.2f} Portfolio synergy floor."
        ),
    )

    f_conservative_viable = _factor(
        name="conservative_revenue_viable",
        observed=f"${conservative_monthly_revenue:,.0f}/mo",
        threshold=f"> $0/mo",
        passed=conservative_monthly_revenue > 0,
        rationale=(
            f"Conservative revenue estimate ${conservative_monthly_revenue:,.0f}/mo "
            f"{'is positive — economic viability established' if conservative_monthly_revenue > 0 else 'is zero — no economic viability established'}."
        ),
    )

    # -----------------------------------------------------------------------
    # Classification hierarchy
    # -----------------------------------------------------------------------

    # 1. EXPANSION — synergy is the investment thesis
    #    Condition: strong synergy AND owned assets exist
    #    Note: Expansion can coexist with any ceiling — a $500/mo micro-niche
    #    adjacent to an owned asset is still an Expansion play.
    if f_synergy_expansion.passed:
        # Confidence scales with how far above the threshold synergy sits
        confidence = min(1.0, 0.70 + (synergy_score - EXPANSION_SYNERGY_MIN) * 0.60)
        # Expansion confidence is capped at 0.90 — the portfolio could change
        confidence = min(0.90, confidence)
        return ExpansionClass(
            label="Expansion",
            confidence=round(confidence, 3),
            factors=tuple(factors),
            plain_english=(
                f"Strong portfolio synergy ({synergy_score:.2f}) makes this a natural "
                f"adjacency play off existing owned assets in "
                f"{', '.join(a.primary_category for a in portfolio_snapshot.owned[:2])}."
            ),
            synergy_driven=True,
        )

    # 2. FLAGSHIP — high ceiling, national+, standalone economics
    if f_ceiling_flagship.passed and not is_local:
        bonus = 0.05 if f_synergy_portfolio.passed else 0.0
        confidence = min(1.0, 0.80 + bonus)
        return ExpansionClass(
            label="Flagship",
            confidence=round(confidence, 3),
            factors=tuple(factors),
            plain_english=(
                f"${market_ceiling_monthly_usd:,.0f}/mo national market ceiling — "
                f"standalone Flagship economics"
                f"{', with portfolio synergy bonus' if f_synergy_portfolio.passed else ''}."
            ),
            synergy_driven=False,
        )

    # 3. LOCAL — geographically scoped
    if is_local:
        # Local with synergy is still Local (geographic constraint dominates)
        confidence = 0.75 if market_ceiling_monthly_usd >= LOCAL_CEILING_MIN else 0.55
        return ExpansionClass(
            label="Local",
            confidence=round(confidence, 3),
            factors=tuple(factors),
            plain_english=(
                f"Geographically scoped ({geographic_scope}) opportunity. "
                f"${market_ceiling_monthly_usd:,.0f}/mo local ceiling — "
                f"viable as a regional asset, limited exit multiple."
            ),
            synergy_driven=False,
        )

    # 4. PORTFOLIO — solid standalone with meaningful synergy
    if f_ceiling_portfolio.passed and f_synergy_portfolio.passed:
        confidence = min(1.0, 0.65 + (synergy_score - PORTFOLIO_SYNERGY_MIN) * 0.40)
        return ExpansionClass(
            label="Portfolio",
            confidence=round(confidence, 3),
            factors=tuple(factors),
            plain_english=(
                f"${market_ceiling_monthly_usd:,.0f}/mo ceiling with meaningful synergy "
                f"({synergy_score:.2f}) — reliable mosaic fit."
            ),
            synergy_driven=False,
        )

    # 5. PORTFOLIO — solid standalone, no meaningful synergy
    if f_ceiling_portfolio.passed:
        return ExpansionClass(
            label="Portfolio",
            confidence=0.60,
            factors=tuple(factors),
            plain_english=(
                f"${market_ceiling_monthly_usd:,.0f}/mo ceiling qualifies as a "
                f"Portfolio asset. Low synergy ({synergy_score:.2f}) — standalone thesis only."
            ),
            synergy_driven=False,
        )

    # 6. MICRO — everything below Portfolio floor
    confidence = 0.80 if market_ceiling_monthly_usd >= LOCAL_CEILING_MIN else 0.65
    return ExpansionClass(
        label="Micro",
        confidence=round(confidence, 3),
        factors=tuple(factors),
        plain_english=(
            f"${market_ceiling_monthly_usd:,.0f}/mo ceiling — Micro bet. "
            f"Fast to launch, low capital, accept binary outcome."
        ),
        synergy_driven=False,
    )


# ---------------------------------------------------------------------------
# Utility: batch classify from a list of opportunity dicts
# ---------------------------------------------------------------------------

def classify_batch(
    opportunities: list[dict],
    portfolio_snapshot: "PortfolioSnapshot",
) -> list[tuple[str, ExpansionClass]]:
    """
    Convenience wrapper for batch classification.

    Each dict in opportunities must have keys:
        opportunity_id, market_ceiling_monthly_usd, geographic_scope,
        conservative_monthly_revenue, synergy_report (SynergyReport instance)

    Returns list of (opportunity_id, ExpansionClass) tuples, sorted by label
    then ceiling descending.
    """
    from engines.portfolio_synergy import SynergyReport  # local import to avoid circularity

    results: list[tuple[str, ExpansionClass]] = []
    for opp in opportunities:
        ec = classify(
            market_ceiling_monthly_usd=opp["market_ceiling_monthly_usd"],
            geographic_scope=opp["geographic_scope"],
            conservative_monthly_revenue=opp["conservative_monthly_revenue"],
            synergy_report=opp["synergy_report"],
            portfolio_snapshot=portfolio_snapshot,
        )
        results.append((opp["opportunity_id"], ec))

    label_order = {"Expansion": 0, "Flagship": 1, "Portfolio": 2, "Local": 3, "Micro": 4}
    results.sort(key=lambda x: (
        label_order.get(x[1].label, 99),
        -opportunities[next(i for i, o in enumerate(opportunities) if o["opportunity_id"] == x[0])]["market_ceiling_monthly_usd"]
    ))
    return results


# ---------------------------------------------------------------------------
# Compatibility wrapper
#
# Thin class shim for older call sites / tests that expect an
# ExpansionClassifier class instance rather than the module-level
# classify() / classify_batch() functions. Contains zero business
# logic — every method delegates directly to the function of the
# same name above. The functional API remains canonical and is
# unchanged; the classification hierarchy and thresholds live only
# in classify() above.
# ---------------------------------------------------------------------------

class ExpansionClassifier:
    """
    Compatibility wrapper around the module-level classify() and
    classify_batch() functions.

    Usage:
        classifier = ExpansionClassifier()
        result = classifier.classify(
            market_ceiling_monthly_usd=...,
            geographic_scope=...,
            conservative_monthly_revenue=...,
            synergy_report=...,
            portfolio_snapshot=...,
        )

    This class holds no state and performs no logic of its own —
    it exists solely so that code written against a class-based
    interface continues to work unchanged.
    """

    def classify(
        self,
        *,
        market_ceiling_monthly_usd: float,
        geographic_scope: str,
        conservative_monthly_revenue: float,
        synergy_report: "SynergyReport",
        portfolio_snapshot: "PortfolioSnapshot",
    ) -> ExpansionClass:
        return classify(
            market_ceiling_monthly_usd=market_ceiling_monthly_usd,
            geographic_scope=geographic_scope,
            conservative_monthly_revenue=conservative_monthly_revenue,
            synergy_report=synergy_report,
            portfolio_snapshot=portfolio_snapshot,
        )

    def classify_batch(
        self,
        opportunities: list[dict],
        portfolio_snapshot: "PortfolioSnapshot",
    ) -> list[tuple[str, ExpansionClass]]:
        return classify_batch(opportunities, portfolio_snapshot)
