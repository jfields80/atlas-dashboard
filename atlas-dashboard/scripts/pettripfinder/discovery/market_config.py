"""AES-DATA-004A discovery -- market geography configuration (Task 2).

Loads the committed, reviewable JSON market configuration (e.g.
``config/columbus_oh.json``) into frozen dataclasses. The observation date
is never read from this file -- it is supplied explicitly at runtime by the
caller (CLI ``--observed-at`` / test fixtures), per mission Task 2.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Tuple

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


def _norm_municipality(name: str) -> str:
    """Case, spacing and punctuation only. Nothing about MEANING --
    two different places must never collapse here."""
    return " ".join(
        "".join(ch.lower() if (ch.isalnum() or ch.isspace()) else " "
                for ch in str(name or "")).split())


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
    #: PTF-DETROIT-ANN-ARBOR-FOUNDER-RULINGS-AND-SHADOW-PROMOTION-006. Spellings
    #: that ARE a municipality this market already contains, mapped to it.
    #:
    #: A source is not obliged to spell a place the way a market registered it.
    #: OpenStreetMap calls Farmington Hills "Farmington Hill" on at least one
    #: node, and a market that cannot say "those are the same place" has only
    #: two bad options: admit the misspelling as a 23rd municipality, which is a
    #: boundary claim nobody made, or hold a real hotel in a registered city as
    #: BORDERLINE forever. An alias is neither -- it is a statement about
    #: SPELLING, and it is declared, never inferred from string similarity.
    municipality_aliases: Mapping[str, str] = field(default_factory=dict)

    def canonical_municipality(self, name: str) -> str:
        """``name`` with any declared alias resolved. Unknown names pass
        through unchanged: an alias map answers "is this a spelling of
        something I contain", never "is this in the market"."""
        if not name:
            return ""
        want = _norm_municipality(name)
        for alias, canonical in self.municipality_aliases.items():
            if _norm_municipality(alias) == want:
                return canonical
        return name

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
        # Optional: a market that declares none behaves exactly as before.
        municipality_aliases=dict(data.get("municipality_aliases") or {}),
    )


_MARKET_FILENAMES = {
    "columbus-oh": "columbus_oh.json",
    # PTF-DAYTON-MARKET-FACTORY-001: worker-proposed; Opus integrates.
    "dayton-oh": "dayton_oh.json",
    # PTF-INDIANAPOLIS-MARKET-REVALIDATION-001.
    "indianapolis-in": "indianapolis_in.json",
    # PTF-CINCINNATI-CENSUS-RECONCILIATION-001 ported the tri-state config off
    # worker/ptf-cincinnati-market-001 and registered it here. Without this
    # entry the file existed but no caller could ever load it, which is how a
    # market ends up with a census built from its own corridor registry instead
    # of from discovery.
    "cincinnati-oh": "cincinnati_oh.json",
    # PTF-PITTSBURGH-MARKET-REVALIDATION-001.
    "pittsburgh-pa": "pittsburgh_pa.json",
    # PTF-DETROIT-ANN-ARBOR-MARKET-FACTORY-001.
    "detroit-ann-arbor-mi": "detroit_ann_arbor_mi.json",
}


def conventional_config_filename(market_id: str) -> str:
    """The filename a market's discovery config gets when nobody names it.

    Every entry in ``_MARKET_FILENAMES`` already follows this rule; stating it
    as a function is what lets a new market ship a config file without also
    editing a shared Python dict that every parallel market branch touches.
    """
    return "%s.json" % (market_id or "").replace("-", "_")


def _resolve_config_path(market_id: str, config_dir: Path = None) -> Path:
    """Resolve a market's discovery config.

    PTF-MARKET-AUTHORITY-SHARDING-001. Two layers, explicit first:

    1. ``_MARKET_FILENAMES`` -- the registry above. Kept, and still wins, so
       every market registered before this change resolves exactly as it did
       and a config filename may still deliberately differ from its market id.
    2. The conventional filename, if that file actually exists on disk.

    The second layer is the point: registering market N+1 used to require an
    edit to this dict from that market's branch, which is a guaranteed conflict
    with every other market's branch doing the same thing for no benefit --
    every entry was the mechanical id-to-filename transform anyway. Discovery
    by convention costs a file, not a merge.

    An unknown market still fails closed: a market id with no registry entry
    AND no file on disk raises, so a typo can never resolve to nothing quietly.
    """
    base = config_dir or _CONFIG_DIR
    filename = _MARKET_FILENAMES.get(market_id)
    if filename is not None:
        return base / filename
    if not (market_id or "").strip():
        raise KeyError("unknown market_id: %r" % market_id)
    discovered = base / conventional_config_filename(market_id)
    if discovered.is_file():
        return discovered
    raise KeyError("unknown market_id: %r" % market_id)
