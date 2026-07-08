"""
schema.py — Opportunity DNA framework schema.

Generic by construction: nothing here is travel-specific, restaurant-specific,
or therapist-specific. Every field is either a controlled-vocabulary enum
(intensity, cadence, etc.) or free-form structured content that any market
can populate.

The schema answers, for any market:
    Who buys?          -> Customer
    Why do they buy?   -> BuyingBehavior + IntentProfile
    What businesses?   -> BusinessEcosystem (nodes) + EcosystemEdges (graph)
    How do they search?-> SearchDNA (dimensions people think in)
    How does money flow? -> CommercialDNA
    What SHOULD Atlas build? -> AssetPreferences
    What has Atlas learned? -> LearningRecord (real storage; adjustment
                                              logic gated until real outcomes exist)

The engine reads these fields. It never assumes any particular market's
vocabulary. Dog Bakeries and Therapists must be expressible in exactly
this schema with no schema changes — that's the validation gate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Controlled vocabularies — the ONLY hardcoded axes. Kept intentionally short
# and market-agnostic. If a market can't be described with these, the
# vocabulary is wrong, not the market.
# ---------------------------------------------------------------------------

class Intensity(str, Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"
    EXTREME = "extreme"


class Cadence(str, Enum):
    ONE_TIME = "one_time"           # rarely repeat (roof replacement)
    OCCASIONAL = "occasional"        # once every 1-5 years
    SEASONAL = "seasonal"            # tied to a season/event
    REGULAR = "regular"              # weekly-monthly (restaurants, grooming)
    ONGOING = "ongoing"              # subscription-like (therapy, gym)


class BuyingCycle(str, Enum):
    IMMEDIATE = "immediate"          # order lunch, book same-day
    SHORT = "short"                  # days
    MEDIUM = "medium"                # weeks
    LONG = "long"                    # months (RV, therapist selection)


class PrimaryIntent(str, Enum):
    PROBLEM_SOLVING = "problem_solving"
    BUYING = "buying"
    RESEARCHING = "researching"
    PLANNING = "planning"
    COMPARING = "comparing"
    LOCAL_DISCOVERY = "local_discovery"
    INSPIRATION = "inspiration"
    OWNERSHIP = "ownership"          # RV/boat/pet owners maintaining a thing


class EdgeType(str, Enum):
    COMPLEMENTARY = "complementary"            # bought/used together
    SUBSTITUTE = "substitute"                  # alternative solution
    DEPENDS_ON = "depends_on"                  # A can't exist without B
    SERVES_SAME_CUSTOMER = "serves_same_customer"   # same buyer, different need
    UPSTREAM_SUPPLIER = "upstream_supplier"
    DOWNSTREAM_CONSUMER = "downstream_consumer"


# ---------------------------------------------------------------------------
# Core structural pieces
# ---------------------------------------------------------------------------

@dataclass
class CustomerProfile:
    """WHO is buying. Not a persona document — the fields the engine actually
    reasons about. All fields optional so simple markets aren't forced to
    invent complexity they don't have."""
    buyer_description: str                       # human-readable, one line
    influencers: list[str] = field(default_factory=list)   # spouse, vet, kids
    decision_maker_is_buyer: bool = True
    b2b: bool = False
    typical_lifecycle_stage: Optional[str] = None  # "new owner", "retiree", etc.


@dataclass
class BuyingBehavior:
    primary_intent: PrimaryIntent
    buying_cycle: BuyingCycle
    purchase_cadence: Cadence
    decision_complexity: Intensity
    customer_emotion: Intensity
    trust_importance: Intensity
    price_sensitivity: Intensity
    urgency_when_buying: Intensity


@dataclass
class IntentProfile:
    """The mental modes customers are in when they search. Free-form list
    of intent shapes with intensity. Universally applicable — every market
    has SOME dominant intents; the DNA just names them."""
    dominant_intents: list[str]                 # e.g. "find_nearby", "solve_problem"
    local_intent: Intensity
    commercial_intent: Intensity
    review_importance: Intensity
    visual_importance: Intensity
    content_appetite: Intensity                 # do they read long articles?


@dataclass
class EcosystemNode:
    """A business type in the market's commercial ecosystem. Generic: works
    for 'hotels' in pet travel, 'ABA centers' in therapy, 'RV solar' in RV."""
    name: str
    role: str                                    # 'primary supply', 'complement', 'adjacent service'
    supply_intensity: Intensity                  # roughly how many exist
    directory_potential: Intensity               # would this alone deserve one?
    gravity: str = "secondary"                   # core | secondary | peripheral — how central to the market
    notes: str = ""


@dataclass
class JourneyStage:
    """One step in the customer's decision-making journey through this
    market. Each stage produces opportunities regardless of dimensions —
    'find emergency vet during trip' is a legit opportunity even if
    'emergency vet' isn't in a search dimension. Fully generic: works
    for any market whose customers have a multi-step decision path."""
    name: str                                    # 'find lodging', 'insurance questions'
    description: str = ""
    generates_opportunities: list[str] = field(default_factory=list)  # ecosystem node names
    typical_asset_types: list[str] = field(default_factory=list)      # article, tool, comparison
    commercial_intensity: Intensity = Intensity.MEDIUM


@dataclass
class BusinessModelOption:
    """A specific way to make money in THIS market. Higher-fidelity than
    the generic monetization streams — names the actual product/offering
    a Business Brief would recommend."""
    offering: str                                # 'booking affiliate', 'featured hotel listing'
    fit: Intensity
    typical_price_or_cut: str = ""              # '$40/mo per listing', '4-5% commission'
    depends_on_stream: str = ""                  # ties back to CommercialDNA.streams
    notes: str = ""


@dataclass
class EcosystemEdge:
    from_node: str                               # names must match EcosystemNode.name
    to_node: str
    edge_type: EdgeType
    strength: Intensity
    notes: str = ""


@dataclass
class SearchDimension:
    """How customers MENTALLY organize this market. Not modifier keywords —
    the axes of thought. Every market has 3-8 of these."""
    name: str                                    # 'problem', 'insurance', 'signature dish'
    description: str
    examples: list[str] = field(default_factory=list)
    intent_type: str = "structural"              # structural | attribute | intent | occasion
    typically_produces_asset: str = "category"   # what asset does this dimension usually generate?


@dataclass
class MonetizationStream:
    """Any revenue model. The type is a free-form string so new models can
    be added per market without schema changes; 'strength' says how well
    this market supports it."""
    stream: str                                  # 'ads' | 'premium_listings' | 'lead_gen' | 'affiliate_booking' | anything
    strength: Intensity
    typical_monthly_range_low: int
    typical_monthly_range_high: int
    notes: str = ""


@dataclass
class CommercialDNA:
    lead_value: Intensity                        # $ per qualified lead if lead-gen is viable
    lead_value_estimate_usd: Optional[int] = None
    recurring_revenue_potential: Intensity = Intensity.LOW
    regulated: bool = False
    regulatory_notes: str = ""
    streams: list[MonetizationStream] = field(default_factory=list)


@dataclass
class AssetPreference:
    """Which digital asset types make sense for THIS market. Weight 0-100
    for how well the market supports each. The engine uses this to shade
    asset-type recommendations — not every market wants a directory."""
    asset_type: str      # directory | category | filter | seo_page | article | comparison | buying_guide | marketplace | lead_gen | affiliate_hub | tool
    fit_weight: int      # 0-100
    rationale: str = ""


@dataclass
class ScoringWeights:
    """Override the engine's default 6-factor weights per market. Must sum
    to ~1.0. Therapists weight lead_value + trust; restaurants weight
    reviews + supply; RV weights recurring + adjacent markets."""
    search_demand: float = 0.20
    competition: float = 0.25
    directory_weakness: float = 0.20
    business_count: float = 0.15
    monetization: float = 0.15
    automation_fit: float = 0.05

    def normalized(self) -> "ScoringWeights":
        total = (self.search_demand + self.competition + self.directory_weakness
                  + self.business_count + self.monetization + self.automation_fit)
        if total == 0:
            return self
        return ScoringWeights(
            self.search_demand / total, self.competition / total,
            self.directory_weakness / total, self.business_count / total,
            self.monetization / total, self.automation_fit / total)


@dataclass
class LearningRecord:
    """Structured slot for real outcome data. This exists on day one because
    schema-later is much worse than schema-early — but nothing in the engine
    USES it until real published-directory outcomes exist to feed it.
    That honest wall lives in learning.py, not here."""
    published_assets: list[dict] = field(default_factory=list)
    observed_outcomes: list[dict] = field(default_factory=list)
    adjustment_history: list[dict] = field(default_factory=list)
    frozen: bool = True    # True = don't apply adjustments to scoring; day-one default


# ---------------------------------------------------------------------------
# Top-level: the DNA profile itself
# ---------------------------------------------------------------------------

@dataclass
class OpportunityDNA:
    slug: str                                    # 'pet_friendly_travel', 'dog_bakeries'
    display_name: str
    version: str = "1.0"
    author: str = ""
    summary: str = ""

    customer: Optional[CustomerProfile] = None
    behavior: Optional[BuyingBehavior] = None
    intent: Optional[IntentProfile] = None

    ecosystem_nodes: list[EcosystemNode] = field(default_factory=list)
    ecosystem_edges: list[EcosystemEdge] = field(default_factory=list)
    customer_journey: list[JourneyStage] = field(default_factory=list)
    business_model_options: list[BusinessModelOption] = field(default_factory=list)

    search_dimensions: list[SearchDimension] = field(default_factory=list)
    commercial: Optional[CommercialDNA] = None
    asset_preferences: list[AssetPreference] = field(default_factory=list)
    scoring_weights: ScoringWeights = field(default_factory=ScoringWeights)

    seed_geography_hint: Optional[str] = None    # "US", "Ohio" — starting scope
    learning: LearningRecord = field(default_factory=LearningRecord)

    def asset_weight(self, asset_type: str) -> int:
        for p in self.asset_preferences:
            if p.asset_type == asset_type:
                return p.fit_weight
        return 50  # neutral default — market didn't opine

    def ecosystem_siblings_of(self, node_name: str, edge_types: Optional[list[EdgeType]] = None) -> list[str]:
        allowed = set(edge_types) if edge_types else set(EdgeType)
        return [e.to_node for e in self.ecosystem_edges
                 if e.from_node == node_name and e.edge_type in allowed]

    def nodes_by_gravity(self, gravity: str) -> list[EcosystemNode]:
        return [n for n in self.ecosystem_nodes if n.gravity == gravity]
