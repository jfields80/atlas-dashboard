"""Where a market's identity census lives -- and where a REBUILD writes its own.

PTF-INDIANAPOLIS-HARDENED-RECENSUS-002 found the trap. Indianapolis is a
REGISTERED market: ``markets/indianapolis-in.json`` exists, its policy package is
``published: true`` in source, and ``deploy/netlify/release_contracts/
indianapolis-in.json`` pins ``identity_census/indianapolis-in.json`` at
``expected_count: 153``. Every generic factory tool reads and writes the census
at ``launch_packages/pettripfinder/identity_census/<market>.json`` by
convention, so re-censusing the market on the generic path would have
overwritten the pinned file, and the Louisville rebuild already showed what a
release contract that no longer matches its market does: ``verify_all()`` raises
for EVERY market, Columbus included.

Louisville dodged this by moving its contract to ``markets/pending/`` -- it was
not yet a founder-registered market. A registered (or live: Pittsburgh) market
cannot be de-registered to be re-censused. So the census location is a
run-level setting:

    PTF_IDENTITY_CENSUS_DIR=launch_packages/pettripfinder/identity_census_proposed

points every generic tool at a proposed-census directory for the duration of a
rebuild. The committed census is never touched; promoting the proposed census
over it is a founder step, taken together with the release contract and the
registration row it invalidates, and never by a factory run.

Unset, this resolves to the committed directory and nothing changes.
"""

from __future__ import annotations

import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_DIR = _REPO_ROOT / "launch_packages" / "pettripfinder"

#: The committed census directory: the one the release contracts pin.
COMMITTED_CENSUS_DIR = PACKAGE_DIR / "identity_census"

#: Set this to re-census a registered market without touching its committed census.
ENV = "PTF_IDENTITY_CENSUS_DIR"

#: The conventional proposed-census directory a rebuild of a registered market uses.
PROPOSED_CENSUS_DIR = PACKAGE_DIR / "identity_census_proposed"


def identity_census_dir() -> Path:
    """The directory every generic tool reads and writes ``<market>.json`` in."""
    raw = os.environ.get(ENV, "").strip()
    if not raw:
        return COMMITTED_CENSUS_DIR
    path = Path(raw)
    return path if path.is_absolute() else (_REPO_ROOT / path)


def identity_census_path(market_id: str) -> Path:
    return identity_census_dir() / ("%s.json" % market_id)


def is_overridden() -> bool:
    return identity_census_dir().resolve() != COMMITTED_CENSUS_DIR.resolve()


def relative_census_path(market_id: str) -> str:
    """Repo-relative POSIX path, for provenance strings in written documents."""
    path = identity_census_path(market_id)
    try:
        return path.resolve().relative_to(_REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


__all__ = ["ENV", "COMMITTED_CENSUS_DIR", "PROPOSED_CENSUS_DIR", "PACKAGE_DIR",
           "identity_census_dir", "identity_census_path", "is_overridden",
           "relative_census_path"]
