"""
snapshots.py — Atlas v3 Portfolio State Layer
"""

from dataclasses import dataclass
from typing import List, Dict, Any
import uuid
from datetime import datetime


# ─────────────────────────────
# PORTFOLIO ASSET
# ─────────────────────────────

@dataclass
class PortfolioAsset:
    asset_id: str
    name: str
    category: str
    status: str
    revenue: float


# ─────────────────────────────
# SNAPSHOT OBJECT
# ─────────────────────────────

@dataclass
class PortfolioSnapshot:
    snapshot_id: str
    created_at: str
    assets: List[PortfolioAsset]


# ─────────────────────────────
# FACTORY (THIS IS WHAT YOU WERE MISSING)
# ─────────────────────────────

class PortfolioSnapshotFactory:

    def create_snapshot(self, assets: List[Dict[str, Any]]) -> PortfolioSnapshot:

        parsed_assets = []

        for a in assets:
            parsed_assets.append(
                PortfolioAsset(
                    asset_id=a.get("asset_id", str(uuid.uuid4())),
                    name=a.get("name", ""),
                    category=a.get("category", "unknown"),
                    status=a.get("status", "unknown"),
                    revenue=a.get("revenue", 0.0),
                )
            )

        return PortfolioSnapshot(
            snapshot_id=str(uuid.uuid4()),
            created_at=datetime.utcnow().isoformat(),
            assets=parsed_assets
        )