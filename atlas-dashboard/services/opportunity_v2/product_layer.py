"""
product_layer.py — Atlas Product Output Layer
"""

class ProductLayer:

    def build_card(self, market_capacity, decision, explanation):

        return {
            "niche_name": market_capacity["niche_name"],
            "score": market_capacity["market_capacity_score"],
            "recommendation": getattr(decision, "recommendation", "UNKNOWN"),
            "confidence": getattr(decision, "confidence", 0),

            "demand": market_capacity.get("demand_score", 0),
            "supply": market_capacity.get("supply_score", 0),
            "competition": market_capacity.get("competition_score", 0),

            "revenue_ceiling": market_capacity.get("revenue_ceiling", 0),

            "summary": getattr(explanation, "summary", ""),
            "risks": getattr(explanation, "risks", []),
            "drivers": getattr(explanation, "drivers", [])
        }