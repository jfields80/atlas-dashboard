"""
Scout Decision Engine

ONLY responsibility:
- Convert Google / Scout signals → VERIFIED / BUILD / HEURISTIC

NO data fetching
NO intelligence providers
NO scoring systems
"""

from typing import Optional, Dict


def compute_verification_level(google_result: Optional[Dict]) -> str:
    """
    Classification engine:
    VERIFIED / BUILD / HEURISTIC
    """

    if not google_result:
        return "HEURISTIC"

    business_count = google_result.get("business_count", 0)
    review_count   = google_result.get("average_review_count", 0)
    rating_avg     = google_result.get("average_rating", 0)

    # VERIFIED
    if business_count >= 10 and review_count >= 50 and rating_avg >= 4.0:
        return "VERIFIED"

    # BUILD
    if business_count >= 5 and review_count >= 20:
        return "BUILD"

    return "HEURISTIC"


def compute_market_strength(google_result: Optional[Dict]) -> float:
    """
    0–100 signal strength score (NOT classification)
    """

    if not google_result:
        return 0.0

    business_count = google_result.get("business_count", 0)
    review_count   = google_result.get("average_review_count", 0)
    rating_avg     = google_result.get("average_rating", 0)

    score = 0.0
    score += min(business_count * 4, 40)
    score += min(review_count * 0.5, 30)
    score += (rating_avg / 5.0) * 30

    return round(min(score, 100.0), 2)