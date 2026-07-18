"""AES-DATA-004A discovery -- market geography configuration (Task 2).

Loads the committed, reviewable JSON market configuration (e.g.
``config/columbus_oh.json``) into frozen dataclasses. The observation date
is never read from this file -- it is supplied explicitly at runtime by the
caller (CLI ``--observed-at`` / test fixtures), per mission Task 2.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

_CONFIG_DIR = Path(__file__).resolve().parent / "config"


@dataclass(frozen=True)
class GeoBounds:
    min_lat: float
    max_lat: float
    min_lng: float
    max_lng: float

    def contains(self, lat: float, lng: float) -> bool:
        return (self.min_lat <= lat <= self.max_lat
                and self.min_lng <= lng <= self.max_lng)


@dataclass(frozen=True)
class MarketCell:
    cell_id: str
    municipality: str
    label: str
    center_lat: float
    center_lng: float
    radius_meters: int


@dataclass(frozen=True)
class MarketConfig:
    market_id: str
    market_name: str
    state: str
    country: str
    center_lat: float
    center_lng: float
    bounds: GeoBounds
    included_municipalities: Tuple[str, ...]
    cells: Tuple[MarketCell, ...]

    def cell_by_id(self, cell_id: str):
        for cell in self.cells:
            if cell.cell_id == cell_id:
                return cell
        return None


def load_market_config(market_id: str, config_dir: Path = None) -> MarketConfig:
    """Load a committed market JSON config by ``market_id`` (the file's own
    stem, e.g. ``columbus-oh`` -> ``config/columbus_oh.json`` is looked up
    via an explicit registry rather than a filename transform, so config
    filenames and market IDs stay independently reviewable)."""
    path = _resolve_config_path(market_id, config_dir)
    data = json.loads(path.read_text(encoding="utf-8"))
    bounds = data["geographic_bounds"]
    cells = tuple(
        MarketCell(
            cell_id=c["cell_id"], municipality=c["municipality"], label=c["label"],
            center_lat=float(c["center_lat"]), center_lng=float(c["center_lng"]),
            radius_meters=int(c["radius_meters"]),
        )
        for c in data["cells"]
    )
    return MarketConfig(
        market_id=data["market_id"], market_name=data["market_name"],
        state=data["state"], country=data["country"],
        center_lat=float(data["market_center"]["lat"]),
        center_lng=float(data["market_center"]["lng"]),
        bounds=GeoBounds(
            min_lat=float(bounds["min_lat"]), max_lat=float(bounds["max_lat"]),
            min_lng=float(bounds["min_lng"]), max_lng=float(bounds["max_lng"])),
        included_municipalities=tuple(data["included_municipalities"]),
        cells=cells,
    )


_MARKET_FILENAMES = {
    "columbus-oh": "columbus_oh.json",
}


def _resolve_config_path(market_id: str, config_dir: Path = None) -> Path:
    base = config_dir or _CONFIG_DIR
    filename = _MARKET_FILENAMES.get(market_id)
    if filename is None:
        raise KeyError("unknown market_id: %r" % market_id)
    return base / filename
