"""PTF-MARKET-AUTHORITY-SHARDING-001 -- per-market authority storage.

WHY THIS EXISTS
---------------
Three PetTripFinder authority files were written by every market at once:

  * ``launch_packages/pettripfinder/identity_routing.json``
  * ``launch_packages/pettripfinder/hotel_exclusions.json``
  * ``launch_packages/pettripfinder/seed_businesses.csv``

Nothing about their CONTENT is shared -- every routing record, every exclusion
and every seed row already carries a ``market_id`` and is read back through it.
What was shared was the FILE. Two markets worked in parallel, each appended its
own records to the same array, and git reported a conflict in a file where no
two records had anything to say to each other. Cleveland Pass 4, Cincinnati
routing recovery, Indianapolis and Detroit-Ann Arbor each paid that cost, and
the resolution was always the same mechanical union.

This module makes the ownership that already existed in the data true of the
storage as well:

    markets/authority/<market_id>/identity_routing.json
    markets/authority/<market_id>/hotel_exclusions.json
    markets/authority/<market_id>/seed_businesses.csv

A market writer touches exactly one directory, so two markets writing at the
same time touch disjoint paths and cannot conflict.

WHAT THIS MODULE IS NOT
-----------------------
* Not a schema change. A sharded routing record is validated by
  ``identity_routing.validate_authority`` and a sharded exclusion by
  ``hotel_exclusions.validate`` -- the same contracts, unchanged. Sharding moves
  records between files; it never rewrites one.
* Not a reader migration. The legacy global files remain, byte-for-byte
  regenerable from the shards, and every existing consumer keeps reading them.
  Phase 1 is:

      per-market shards -> deterministic assembler -> legacy global artifacts
      -> existing consumers

  A big-bang reader migration is a separate decision and is deliberately not
  taken here.
* Not a source of truth for market REGISTRATION. ``markets/contract.py`` owns
  which markets exist; a shard directory for an unregistered market is an
  error, not a registration.

DETERMINISM
-----------
Assembly is a pure function of the committed shards. Markets are unioned in
sorted ``market_id`` order and each market's records keep their shard order, so
the same shards always produce the same bytes on every machine, in any checkout
order, with no clock and no filesystem-iteration dependence.

Pure and deterministic: no network, no clock. Reading and writing the committed
files is the only IO.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import sys
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import hotel_exclusions as HE          # noqa: E402
from scripts.pettripfinder import identity_routing as IR          # noqa: E402
from scripts.pettripfinder.markets.contract import load_markets   # noqa: E402
from scripts.pettripfinder.site_data import normalize_name        # noqa: E402

SCHEMA = "ptf-market-authority/1.0"

LAUNCH_PACKAGE = _REPO_ROOT / "launch_packages" / "pettripfinder"
AUTHORITY_DIR = LAUNCH_PACKAGE / "markets" / "authority"

#: The legacy global artifacts. Generated from the shards; never hand-edited.
GLOBAL_ROUTING_PATH = LAUNCH_PACKAGE / "identity_routing.json"
GLOBAL_EXCLUSIONS_PATH = LAUNCH_PACKAGE / "hotel_exclusions.json"
GLOBAL_SEED_PATH = LAUNCH_PACKAGE / "seed_businesses.csv"
MANIFEST_PATH = LAUNCH_PACKAGE / "ptf_global_authority_manifest.json"

ROUTING_SHARD_NAME = "identity_routing.json"
EXCLUSIONS_SHARD_NAME = "hotel_exclusions.json"
SEED_SHARD_NAME = "seed_businesses.csv"

#: The seed CSV's frozen column order. A shard that disagrees is refused rather
#: than silently reordered -- the global CSV's header is a public contract.
SEED_COLUMNS: Tuple[str, ...] = (
    "name", "category", "address", "city", "state", "postal_code", "phone",
    "website_url", "source_url", "source_type", "observed_at", "rating",
    "amenities", "pet_policy", "canonical", "market_id",
)

# --------------------------------------------------------------------------- #
# Global-document prose. Contract-level, not market-level: no market writer has
# a reason to change these, so they live here rather than being fought over in a
# shared file. Values are the ones committed on main at baseline
# 20279f4b6f66a073f69823275c23f5c3481f173b and are reproduced verbatim so the
# generated artifacts stay byte-comparable with what consumers already read.
# --------------------------------------------------------------------------- #

_ROUTING_NOTE = (
    "Official property endpoints for CONFIRMED hotel identities that are not "
    "publication inventory. A record here says WHERE a property speaks for "
    "itself. It is not publication, not policy, and not a second identity "
    "system: nothing in the publication path reads this file, and the join key "
    "remains hotel_ref.normalized_name + market_id. Adding a record here cannot "
    "create a hotel profile, a route, a sitemap entry, or a held-inventory "
    "count -- held inventory is derived from seed_businesses.csv alone. "
    "identity_context exists solely so the capture queue can satisfy its own "
    "required fields without a seed row, and is read by nothing that publishes."
)
_ROUTING_BINDING_METHOD_NOTE = (
    "binding_method is per-record and categorical, never a confidence score and "
    "never upgraded merely because a record became authoritative. Most records "
    "are BRAND_INDEX_BINDING: the brand refused automated requests, so identity "
    "was bound through brand-domain index content, property codes read from "
    "discovered links, and explicit same-brand disambiguation. A record is "
    "PAGE_RENDERED only where the property's own page actually served its "
    "content to us on re-probe -- in this authority that is the independent "
    "first-party B&B/motel sites and Drury."
)
_ROUTING_IDENTITY_KEY_CONTRACT = "ptf_identity_key/1.0"

#: Legacy field. The exclusions authority carried a single ``market`` string
#: from when Columbus was the only market; it is multi-market now and every
#: record carries its own ``market_id``. Preserved verbatim because it is part
#: of the committed artifact consumers already read, and deliberately NOT
#: derived from the shards -- deriving it would make an already-meaningless
#: field change whenever a market is added.
_EXCLUSIONS_LEGACY_MARKET = "columbus-oh"
_EXCLUSIONS_NOTE = (
    "Identities disqualified by evidence or by category ruling. Separate from "
    "seed_businesses.csv and hotel_policy_facts.json: an exclusion needs no "
    "seed row, never enters the policy package, and never creates a public "
    "route. A capture that FAILED is not an exclusion and must never appear "
    "here."
)


class MarketAuthorityError(ValueError):
    """A shard is malformed, misfiled, or collides with another market's."""


# --------------------------------------------------------------------------- #
# Paths and discovery
# --------------------------------------------------------------------------- #

def market_shard_dir(market_id: str, authority_dir: Optional[Path] = None) -> Path:
    base = Path(authority_dir) if authority_dir is not None else AUTHORITY_DIR
    return base / market_id


def routing_shard_path(market_id: str, authority_dir: Optional[Path] = None) -> Path:
    return market_shard_dir(market_id, authority_dir) / ROUTING_SHARD_NAME


def exclusions_shard_path(market_id: str, authority_dir: Optional[Path] = None) -> Path:
    return market_shard_dir(market_id, authority_dir) / EXCLUSIONS_SHARD_NAME


def seed_shard_path(market_id: str, authority_dir: Optional[Path] = None) -> Path:
    return market_shard_dir(market_id, authority_dir) / SEED_SHARD_NAME


def registered_market_ids() -> Tuple[str, ...]:
    """Every market the market contract defines, sorted. Registration is the
    market contract's job; this module only reads it."""
    return tuple(sorted(m.market_id for m in load_markets()))


def sharded_market_ids(authority_dir: Optional[Path] = None) -> Tuple[str, ...]:
    """Every market that owns an authority shard directory, sorted.

    Discovery is by directory, not by a central list, so registering a market's
    authority costs a directory rather than an edit to a shared Python dict.
    A shard directory the market contract does not know about fails closed:
    silently assembling records for an unregistered market is how a market ends
    up publishing without a config.
    """
    base = Path(authority_dir) if authority_dir is not None else AUTHORITY_DIR
    if not base.is_dir():
        raise MarketAuthorityError(
            "market authority directory does not exist: %s -- a build must "
            "never silently run with zero shards because of a path typo" % base)
    found = tuple(sorted(p.name for p in base.iterdir() if p.is_dir()))
    registered = set(registered_market_ids())
    unknown = [m for m in found if m not in registered]
    if unknown:
        raise MarketAuthorityError(
            "authority shard directory for unregistered market(s) %s -- the "
            "market contract (launch_packages/pettripfinder/markets/*.json) "
            "decides which markets exist" % unknown)
    return found


# --------------------------------------------------------------------------- #
# Rendering. One place decides the bytes, so "regenerate" is reproducible.
# --------------------------------------------------------------------------- #

def render_json(document: Mapping) -> str:
    """The committed JSON style: two-space-free, one-space indent, UTF-8 kept
    as UTF-8, one trailing newline. Matches the artifacts already on main."""
    return json.dumps(document, indent=1, ensure_ascii=False) + "\n"


def render_seed_csv(rows: Sequence[Mapping[str, str]]) -> str:
    """The committed CSV style: LF line endings, minimal quoting, frozen
    column order."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(SEED_COLUMNS), lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({c: row.get(c, "") for c in SEED_COLUMNS})
    return buf.getvalue()


def _sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_if_changed(path: Path, text: str) -> bool:
    """Write LF-exact bytes; return True when the file actually changed."""
    data = text.encode("utf-8")
    if path.exists() and path.read_bytes() == data:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        f.write(data)
    return True


# --------------------------------------------------------------------------- #
# Shard documents
# --------------------------------------------------------------------------- #

def build_routing_shard(market_id: str, routes: Sequence[Mapping],
                        source_batches: Sequence[str] = ()) -> Dict:
    return {
        "schema": IR.SCHEMA,
        "contract": IR.SCHEMA,
        "market_id": market_id,
        "note": ("This market's slice of the identity-routing authority. The "
                 "global launch_packages/pettripfinder/identity_routing.json is "
                 "generated from every market's shard and must not be "
                 "hand-edited."),
        "source_batches": list(source_batches),
        "count": len(routes),
        "routes": [dict(r) for r in routes],
    }


def build_exclusions_shard(market_id: str, exclusions: Sequence[Mapping]) -> Dict:
    return {
        "schema": HE.SCHEMA,
        "contract": HE.SCHEMA,
        "market_id": market_id,
        "note": ("This market's slice of the hotel-exclusions authority. The "
                 "global launch_packages/pettripfinder/hotel_exclusions.json is "
                 "generated from every market's shard and must not be "
                 "hand-edited."),
        "count": len(exclusions),
        "exclusions": [dict(e) for e in exclusions],
    }


def _read_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_market_routing_document(market_id: str,
                                 authority_dir: Optional[Path] = None) -> Dict:
    """This market's validated routing shard. A missing shard is an EMPTY
    authority, exactly as ``identity_routing.load_routes`` treats a missing
    global file: routing is additive and its absence must never break a
    caller."""
    path = routing_shard_path(market_id, authority_dir)
    if not path.exists():
        return build_routing_shard(market_id, [])
    document = _read_json(path)
    declared = document.get("market_id")
    if declared != market_id:
        raise MarketAuthorityError(
            "%s declares market_id %r but lives in the %r shard directory"
            % (path, declared, market_id))
    routes = IR.validate_authority(document)
    foreign = sorted({r["market_id"] for r in routes if r["market_id"] != market_id})
    if foreign:
        raise MarketAuthorityError(
            "%s carries route(s) for foreign market(s) %s -- a market shard owns "
            "only its own records" % (path, foreign))
    if document.get("count") != len(routes):
        raise MarketAuthorityError(
            "%s declares count %r but carries %d routes"
            % (path, document.get("count"), len(routes)))
    return document


def load_market_routes(market_id: str,
                       authority_dir: Optional[Path] = None) -> List[Dict]:
    return list(load_market_routing_document(market_id, authority_dir)["routes"])


def load_market_exclusions_document(market_id: str,
                                    authority_dir: Optional[Path] = None) -> Dict:
    """This market's validated exclusions shard; a missing shard is empty."""
    path = exclusions_shard_path(market_id, authority_dir)
    if not path.exists():
        return build_exclusions_shard(market_id, [])
    document = _read_json(path)
    declared = document.get("market_id")
    if declared != market_id:
        raise MarketAuthorityError(
            "%s declares market_id %r but lives in the %r shard directory"
            % (path, declared, market_id))
    records = HE.validate(document)
    foreign = sorted({r.get("market_id") for r in records
                      if r.get("market_id") != market_id})
    if foreign:
        raise MarketAuthorityError(
            "%s carries exclusion(s) for foreign market(s) %s -- a market shard "
            "owns only its own records" % (path, foreign))
    if document.get("count") != len(records):
        raise MarketAuthorityError(
            "%s declares count %r but carries %d exclusions"
            % (path, document.get("count"), len(records)))
    return document


def load_market_exclusions(market_id: str,
                           authority_dir: Optional[Path] = None) -> List[Dict]:
    return list(load_market_exclusions_document(market_id, authority_dir)["exclusions"])


def load_market_seed_rows(market_id: str,
                          authority_dir: Optional[Path] = None) -> List[Dict[str, str]]:
    """This market's seed rows, in shard order. A missing shard is empty."""
    path = seed_shard_path(market_id, authority_dir)
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        columns = tuple(reader.fieldnames or ())
        if columns != SEED_COLUMNS:
            raise MarketAuthorityError(
                "%s: seed columns %s do not match the frozen contract %s"
                % (path, list(columns), list(SEED_COLUMNS)))
        rows = [dict(r) for r in reader]
    foreign = sorted({r.get("market_id") for r in rows
                      if r.get("market_id") != market_id})
    if foreign:
        raise MarketAuthorityError(
            "%s carries seed row(s) for foreign market(s) %s -- a market shard "
            "owns only its own records" % (path, foreign))
    return rows


# --------------------------------------------------------------------------- #
# Assembly. Shards in, legacy global artifacts out.
# --------------------------------------------------------------------------- #

def assemble_routing_document(authority_dir: Optional[Path] = None) -> Dict:
    """The legacy global routing authority, assembled from every shard.

    Validation happens twice on purpose: each shard alone (so a broken shard
    names its own market) and then the union (so a collision between two
    markets -- one URL bound to two identities, one property code bound to two
    -- is caught even though neither shard is wrong by itself)."""
    routes: List[Dict] = []
    batches: List[str] = []
    for market_id in sharded_market_ids(authority_dir):
        document = load_market_routing_document(market_id, authority_dir)
        routes.extend(document["routes"])
        for batch in document.get("source_batches") or ():
            if batch not in batches:
                batches.append(batch)
    global_document = {
        "schema": IR.SCHEMA,
        "contract": IR.SCHEMA,
        "note": _ROUTING_NOTE,
        "binding_method_note": _ROUTING_BINDING_METHOD_NOTE,
        "source_batches": batches,
        "count": len(routes),
        "routes": routes,
        "identity_key_contract": _ROUTING_IDENTITY_KEY_CONTRACT,
    }
    IR.validate_authority(global_document)
    return global_document


def assemble_exclusions_document(authority_dir: Optional[Path] = None) -> Dict:
    """The legacy global exclusions authority, assembled from every shard.

    ``hotel_exclusions.validate`` on the union is what enforces the global
    uniqueness rules: no duplicate ``exclusion_id``, no identity excluded
    twice, no two exclusions sharing one street identity."""
    records: List[Dict] = []
    for market_id in sharded_market_ids(authority_dir):
        records.extend(load_market_exclusions_document(market_id, authority_dir)["exclusions"])
    global_document = {
        "schema": HE.SCHEMA,
        "contract": HE.SCHEMA,
        "market": _EXCLUSIONS_LEGACY_MARKET,
        "note": _EXCLUSIONS_NOTE,
        "exclusions": records,
    }
    HE.validate(global_document)
    return global_document


def assemble_seed_rows(authority_dir: Optional[Path] = None) -> List[Dict[str, str]]:
    """The legacy global seed inventory, assembled from every shard.

    The seed has no contract module of its own, so the two rules that publication
    actually depends on are enforced here: an identity may hold at most one seed
    row per category, and every row must name a registered market."""
    rows: List[Dict[str, str]] = []
    for market_id in sharded_market_ids(authority_dir):
        rows.extend(load_market_seed_rows(market_id, authority_dir))
    seen: Dict[Tuple[str, str], str] = {}
    for row in rows:
        key = (row.get("category", ""), normalize_name(row.get("name", "")))
        if key in seen:
            raise MarketAuthorityError(
                "two seed rows claim identity %r in category %r (markets %s and "
                "%s) -- one identity is one listing"
                % (key[1], key[0], seen[key], row.get("market_id")))
        seen[key] = row.get("market_id", "")
    return rows


# --------------------------------------------------------------------------- #
# The manifest
# --------------------------------------------------------------------------- #

def build_manifest(authority_dir: Optional[Path] = None) -> Dict:
    """A content-addressed description of what the shards contain and what was
    generated from them.

    Deliberately carries NO wall-clock timestamp. A manifest whose hash changes
    because it was rebuilt on a different afternoon cannot answer the only
    question it exists to answer -- "are these generated files still the ones
    these shards produce?" -- so the build marker is derived from the shard
    hashes instead.
    """
    market_ids = sharded_market_ids(authority_dir)
    markets: List[Dict] = []
    for market_id in market_ids:
        routing = load_market_routing_document(market_id, authority_dir)
        exclusions = load_market_exclusions_document(market_id, authority_dir)
        seed_rows = load_market_seed_rows(market_id, authority_dir)
        markets.append({
            "market_id": market_id,
            "routing_count": len(routing["routes"]),
            "routing_hash": _sha256(render_json(routing)),
            "exclusions_count": len(exclusions["exclusions"]),
            "exclusions_hash": _sha256(render_json(exclusions)),
            "seed_count": len(seed_rows),
            "seed_hash": _sha256(render_seed_csv(seed_rows)),
        })

    routing_doc = assemble_routing_document(authority_dir)
    exclusions_doc = assemble_exclusions_document(authority_dir)
    seed_rows = assemble_seed_rows(authority_dir)

    routing_text = render_json(routing_doc)
    exclusions_text = render_json(exclusions_doc)
    seed_text = render_seed_csv(seed_rows)

    build_marker = _sha256("\n".join(
        "%s|%s|%s|%s" % (m["market_id"], m["routing_hash"], m["exclusions_hash"],
                         m["seed_hash"])
        for m in markets))

    return {
        "schema": SCHEMA,
        "note": ("Generated by scripts/pettripfinder/build_global_authority.py "
                 "from the per-market shards under "
                 "launch_packages/pettripfinder/markets/authority/. Carries no "
                 "wall-clock timestamp on purpose: the build marker is derived "
                 "from shard content so a rebuild that changed nothing produces "
                 "an identical manifest."),
        "build_marker": build_marker,
        "source_market_ids": list(market_ids),
        "markets": markets,
        "global_routing_count": len(routing_doc["routes"]),
        "global_exclusions_count": len(exclusions_doc["exclusions"]),
        "global_seed_count": len(seed_rows),
        "generated_artifacts": [
            {"path": "launch_packages/pettripfinder/identity_routing.json",
             "hash": _sha256(routing_text)},
            {"path": "launch_packages/pettripfinder/hotel_exclusions.json",
             "hash": _sha256(exclusions_text)},
            {"path": "launch_packages/pettripfinder/seed_businesses.csv",
             "hash": _sha256(seed_text)},
        ],
    }


# --------------------------------------------------------------------------- #
# The generated compatibility artifacts
# --------------------------------------------------------------------------- #

def generated_artifacts(authority_dir: Optional[Path] = None) -> List[Tuple[Path, str]]:
    """(path, exact text) for every artifact generated from the shards."""
    return [
        (GLOBAL_ROUTING_PATH, render_json(assemble_routing_document(authority_dir))),
        (GLOBAL_EXCLUSIONS_PATH, render_json(assemble_exclusions_document(authority_dir))),
        (GLOBAL_SEED_PATH, render_seed_csv(assemble_seed_rows(authority_dir))),
        (MANIFEST_PATH, render_json(build_manifest(authority_dir))),
    ]


def check_generated_artifacts(authority_dir: Optional[Path] = None) -> List[str]:
    """Paths whose committed bytes are not what the shards produce. Empty means
    the generated artifacts are in sync with their authority."""
    stale: List[str] = []
    for path, text in generated_artifacts(authority_dir):
        expected = text.encode("utf-8")
        if not path.exists() or path.read_bytes() != expected:
            stale.append(str(path.relative_to(_REPO_ROOT)).replace("\\", "/"))
    return stale


def write_generated_artifacts(authority_dir: Optional[Path] = None) -> List[str]:
    """Regenerate every compatibility artifact. Returns the paths that changed."""
    changed: List[str] = []
    for path, text in generated_artifacts(authority_dir):
        if _write_if_changed(path, text):
            changed.append(str(path.relative_to(_REPO_ROOT)).replace("\\", "/"))
    return changed


__all__ = [
    "SCHEMA", "AUTHORITY_DIR", "MANIFEST_PATH", "SEED_COLUMNS",
    "GLOBAL_ROUTING_PATH", "GLOBAL_EXCLUSIONS_PATH", "GLOBAL_SEED_PATH",
    "ROUTING_SHARD_NAME", "EXCLUSIONS_SHARD_NAME", "SEED_SHARD_NAME",
    "MarketAuthorityError",
    "market_shard_dir", "routing_shard_path", "exclusions_shard_path",
    "seed_shard_path", "registered_market_ids", "sharded_market_ids",
    "render_json", "render_seed_csv",
    "build_routing_shard", "build_exclusions_shard",
    "load_market_routing_document", "load_market_routes",
    "load_market_exclusions_document", "load_market_exclusions",
    "load_market_seed_rows",
    "assemble_routing_document", "assemble_exclusions_document",
    "assemble_seed_rows",
    "build_manifest", "generated_artifacts",
    "check_generated_artifacts", "write_generated_artifacts",
]
