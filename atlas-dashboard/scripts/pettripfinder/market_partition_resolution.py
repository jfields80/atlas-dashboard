"""PTF-FINAL-ASSEMBLER-REGISTERED-MARKET-DISCOVERY-001 -- one generic answer to
"which committed final partition is this registered market's?"

WHAT WAS WRONG
--------------
``assemble_production_site._partition_path`` answered that question with a
hand-maintained table of thirteen market ids followed by a filename glob that
stripped the last segment of the market id. Every market since Indianapolis
needed a table entry, because the glob could not spell a modern partition
name: it looked for ``<first segment>_final_partition_*`` while the committed
file is named for the WHOLE market id, underscored, with its own sequence
number. A table entry is a shared-code DEPLOYMENT_CHANGE and a broad run, so
a freshly registered market -- AUTHORIZATION_READY, sealed, FAST 15/15,
0 broad -- was still not assemblable into the whole-site artifact without
editing the assembler. Raleigh stopped at exactly that line.

WHAT OWNS THE ANSWER NOW
------------------------
The market's own release contract, ``deploy/netlify/release_contracts/
<market_id>.json``. That document already binds the market's identity census
(``identity_census.path``) and its policy package (``policy_package.path`` +
``expected_sha256``); the final partition is the third leg of the same
reconciliation, and it is now bound the same way::

    "final_partition": {
      "path": "launch_packages/pettripfinder/<market id, underscored>_final_"
              "partition_<nnn>.json",
      "schema": "ptf-market-final-partition/1.1",
      "expected_sha256": "<content sha256, CRLF-normalised like the policy package>",
      "expected_count": "<the identity count the partition itself carries>",
      "note": "..."
    }

NO MARKET IS NAMED IN AN EXAMPLE HERE, ON PURPOSE. A shared module that spells
a market helper's stem -- and a partition's filename is its helper's stem --
makes that helper fail the market-local isolation proof's reachability
condition, which is how the first run of this module was caught: one docstring
line naming a real partition file turned a registering market's own helper
into a SHARED_BEHAVIOR_CHANGE and cost the registration its narrowing. The
frozen table below names committed DATA files of markets already registered,
which is a different thing and the whole point of the table.

The chain is

    REGISTERED MARKET (launch_packages/pettripfinder/markets/<id>.json)
      -> MARKET RELEASE CONTRACT (deploy/netlify/release_contracts/<id>.json)
        -> final_partition reference (path + content digest)
          -> the partition file, verified to be THIS market's
            -> assembler

No filename is guessed for a modern market. The reference is a decision the
market's contract helper wrote from the committed file
(:func:`release_contracts.final_partition_block`), the resolver verifies that
the referenced file exists, carries this market's ``market_id`` and the
stated digest, and refuses on any gap: no reference, a reference to a
missing file, a reference to another market's partition, an ambiguous
reference, or a reference that disagrees with the legacy table below.

LEGACY FALLBACK (explicit, frozen, observable)
----------------------------------------------
Fifteen markets were registered before contracts carried the reference. Their
partitions are named in :data:`LEGACY_PARTITION_TABLE` -- the assembler's old
named table plus the two markets the old glob happened to resolve (Milwaukee,
Pittsburgh), each recorded as the file the old lookup returned on the day this
module was written, so removing the glob changed nothing for them. The table
is FROZEN: ``tests/pettripfinder/test_registered_market_partition_resolution_001.py``
pins its exact key set, so a new entry is a visible test-expectation change
and never a quiet one. A market not in the table resolves through its
contract or not at all; there is no third path.

Every resolution reports its ``source`` (``CONTRACT`` or ``LEGACY_TABLE``) so
the assembler's eligibility rows, its bundle manifest and the registration
lane can say which path a market took. When a legacy market's contract later
gains the reference, the two must agree; a disagreement fails closed rather
than picking one.

WHAT THIS MODULE DOES NOT DO
----------------------------
It does not read hotel policy, census membership, geography or routing. It
does not decide whether a market participates in a release. It does not
import the assembler, the generator or the deployer. It only answers which
file is the market's partition, and refuses when that answer is not owned by
a registration artifact.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

from scripts.pettripfinder import release_contracts as RC
from scripts.pettripfinder.markets import contract as MC

REPO_ROOT = Path(__file__).resolve().parents[2]


def default_package_dir() -> Path:
    """Where committed partitions live, resolved AT CALL TIME from the
    contract module's repository root.

    Deliberately not a module constant. ``package_staging`` builds a market
    from a staging tree by pointing every path constant on the build path at
    that tree, and one constant nobody remembered to add to its list is how a
    staged build silently reads committed authority instead. Deriving the
    directory from ``release_contracts.REPO_ROOT`` -- which the overlay
    already redirects, because the contracts themselves live under it -- means
    this module follows a staging tree with no entry of its own to maintain.
    """
    return Path(RC.REPO_ROOT) / "launch_packages" / "pettripfinder"

#: The repository-relative prefix every partition reference must carry.
PACKAGE_PREFIX = "launch_packages/pettripfinder/"

#: The schema family a referenced partition must declare.
PARTITION_SCHEMA_PREFIX = "ptf-market-final-partition/"

#: The contract block that carries the reference.
CONTRACT_BLOCK = "final_partition"

#: Resolution sources.
SOURCE_CONTRACT = "CONTRACT"
SOURCE_LEGACY_TABLE = "LEGACY_TABLE"
SOURCE_UNRESOLVED = "UNRESOLVED"

#: Failure codes, one per way the answer can fail to be owned.
EMPTY_MARKET_ID = "EMPTY_MARKET_ID"
UNREGISTERED_MARKET = "UNREGISTERED_MARKET"
NO_RELEASE_CONTRACT = "NO_RELEASE_CONTRACT"
MISSING_PARTITION_REFERENCE = "MISSING_PARTITION_REFERENCE"
MALFORMED_REFERENCE = "MALFORMED_REFERENCE"
AMBIGUOUS_REFERENCE = "AMBIGUOUS_REFERENCE"
REFERENCE_NOT_FOUND = "REFERENCE_NOT_FOUND"
WRONG_MARKET_PARTITION = "WRONG_MARKET_PARTITION"
WRONG_PARTITION_SCHEMA = "WRONG_PARTITION_SCHEMA"
UNREADABLE_PARTITION = "UNREADABLE_PARTITION"
UNREADABLE_CONTRACT = "UNREADABLE_CONTRACT"
REFERENCE_DIGEST_MISMATCH = "REFERENCE_DIGEST_MISMATCH"
REFERENCE_COUNT_MISMATCH = "REFERENCE_COUNT_MISMATCH"
CONTRACT_TABLE_DISAGREEMENT = "CONTRACT_TABLE_DISAGREEMENT"
LEGACY_PARTITION_MISSING = "LEGACY_PARTITION_MISSING"

FAILURE_CODES: Tuple[str, ...] = (
    EMPTY_MARKET_ID, UNREGISTERED_MARKET, NO_RELEASE_CONTRACT,
    MISSING_PARTITION_REFERENCE, MALFORMED_REFERENCE, AMBIGUOUS_REFERENCE,
    REFERENCE_NOT_FOUND, WRONG_MARKET_PARTITION, WRONG_PARTITION_SCHEMA,
    UNREADABLE_PARTITION, UNREADABLE_CONTRACT,
    REFERENCE_DIGEST_MISMATCH, REFERENCE_COUNT_MISMATCH,
    CONTRACT_TABLE_DISAGREEMENT, LEGACY_PARTITION_MISSING,
)

#: FROZEN. The partition each pre-reference market's old lookup returned,
#: recorded once so that removing the assembler's table and glob moved no
#: market. Thirteen rows are the assembler's former named table verbatim; the
#: last two are what the former glob resolved for the two markets that had no
#: entry (``milwaukee-wi`` -> ``milwaukee_final_partition_*``,
#: ``pittsburgh-pa`` -> ``pittsburgh_final_partition_*``). Nothing is added
#: here for a new market: a new market's contract names its partition.
LEGACY_PARTITION_TABLE: Mapping[str, str] = OrderedDict((
    ("columbus-oh", "columbus_final_partition_001.json"),
    ("cleveland-akron-canton-oh", "cleveland_final_partition_002.json"),
    ("dayton-oh", "dayton_final_partition_001.json"),
    ("cincinnati-oh", "cincinnati_final_partition_001.json"),
    ("louisville-ky", "louisville_final_partition_001.json"),
    ("detroit-ann-arbor-mi", "detroit_ann_arbor_final_partition_001.json"),
    ("charlotte-nc", "charlotte_nc_final_partition_007.json"),
    ("st-louis-mo", "st_louis_mo_final_partition_007.json"),
    ("grand-rapids-holland-mi", "grand_rapids_holland_mi_final_partition_002.json"),
    ("indianapolis-in", "indianapolis_in_final_partition_023.json"),
    ("toledo-oh", "toledo_oh_final_partition_001.json"),
    ("lexington-ky", "lexington_ky_final_partition_001.json"),
    ("nashville-tn", "nashville_tn_final_partition_001.json"),
    # The two markets the former glob served. Frozen as the glob's answer.
    ("milwaukee-wi", "milwaukee_final_partition_001.json"),
    ("pittsburgh-pa", "pittsburgh_final_partition_001.json"),
))

LEGACY_MARKET_IDS = frozenset(LEGACY_PARTITION_TABLE)


class PartitionResolutionError(RuntimeError):
    """The market's partition is not owned by a registration artifact."""

    def __init__(self, code: str, market_id: str, message: str):
        if code not in FAILURE_CODES:
            raise ValueError("unknown failure code %r" % code)
        self.code = code
        self.market_id = market_id
        super().__init__("%s: %s: %s" % (code, market_id, message))


@dataclass(frozen=True)
class PartitionResolution:
    """Which file, by which source, verified how."""

    market_id: str
    source: str
    path: Path
    name: str
    #: The contract block as written, or None for a legacy resolution.
    reference: Optional[Mapping[str, Any]]
    #: The legacy table's entry for this market, if any (reported even when
    #: the contract decided, so agreement is visible).
    legacy_entry: Optional[str]
    #: What was verified about the file: existence for a legacy resolution;
    #: existence, market_id, schema, digest and count for a contract one.
    verified: Tuple[str, ...]

    def as_row(self) -> "OrderedDict[str, Any]":
        return OrderedDict((
            ("market_id", self.market_id),
            ("source", self.source),
            ("partition", self.name),
            ("path", PACKAGE_PREFIX + self.name),
            ("legacy_entry", self.legacy_entry),
            ("verified", list(self.verified)),
        ))


def content_sha256(data: bytes) -> str:
    """The policy package's digest rule, applied to a partition: BOM and CRLF
    are checkout artifacts, not content (assemble_netlify_bundle.content_sha256
    states the rule; restated here so this module imports no build code)."""
    if data[:3] == b"\xef\xbb\xbf":
        data = data[3:]
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


# --------------------------------------------------------------------------- #
# The reference.
# --------------------------------------------------------------------------- #

def parse_reference(market_id: str, block: Any) -> "OrderedDict[str, Any]":
    """The contract block, checked for shape only (no file is read here).

    A reference is one object naming ONE file under the launch package by a
    plain filename and stating the digest it expects. Anything that could name
    more than one file -- a list, a glob, several path keys -- is ambiguous
    and refused; a reference without a digest is a name, not a decision.
    """
    if isinstance(block, (list, tuple)):
        raise PartitionResolutionError(
            AMBIGUOUS_REFERENCE, market_id,
            "final_partition is a list of %d entries; a reference names exactly one file" % len(block))
    if not isinstance(block, Mapping):
        raise PartitionResolutionError(
            MALFORMED_REFERENCE, market_id, "final_partition is %s, not an object" % type(block).__name__)
    alternates = [k for k in ("paths", "candidates", "files", "glob", "pattern") if k in block]
    if alternates:
        raise PartitionResolutionError(
            AMBIGUOUS_REFERENCE, market_id,
            "final_partition carries %s; a reference names exactly one file by 'path'" % alternates)
    if "path" not in block:
        raise PartitionResolutionError(
            MALFORMED_REFERENCE, market_id, "final_partition carries no 'path'")
    rel = block.get("path")
    if isinstance(rel, (list, tuple)):
        raise PartitionResolutionError(
            AMBIGUOUS_REFERENCE, market_id, "final_partition.path names %d files" % len(rel))
    if not isinstance(rel, str) or not rel.strip():
        raise PartitionResolutionError(
            MALFORMED_REFERENCE, market_id, "final_partition.path must be a non-empty string")
    rel = rel.strip().replace("\\", "/")
    if any(ch in rel for ch in "*?[]{}"):
        raise PartitionResolutionError(
            AMBIGUOUS_REFERENCE, market_id, "final_partition.path %r is a pattern, not a filename" % rel)
    if not rel.startswith(PACKAGE_PREFIX):
        raise PartitionResolutionError(
            MALFORMED_REFERENCE, market_id,
            "final_partition.path %r is not under %s" % (rel, PACKAGE_PREFIX))
    name = rel[len(PACKAGE_PREFIX):]
    if not name or "/" in name or name in (".", "..") or not name.endswith(".json"):
        raise PartitionResolutionError(
            MALFORMED_REFERENCE, market_id,
            "final_partition.path %r must name one .json file directly under %s" % (rel, PACKAGE_PREFIX))
    digest = block.get("expected_sha256")
    if digest is None:
        # Indianapolis's contract carried a {path, expected_count} block before
        # this module existed (PTF-INDIANAPOLIS-PROMOTION-REMEDIATION-005). A
        # legacy market may keep that shape -- the frozen table must agree
        # with it -- but a market registered after the table was frozen must
        # state the digest: a reference without one is a name, not a decision.
        if market_id not in LEGACY_MARKET_IDS:
            raise PartitionResolutionError(
                MALFORMED_REFERENCE, market_id,
                "final_partition.expected_sha256 is required for a market outside the frozen legacy "
                "table (a reference without a digest is a name, not a decision)")
    elif not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise PartitionResolutionError(
            MALFORMED_REFERENCE, market_id,
            "final_partition.expected_sha256 must be a 64-hex content digest, got %r" % (digest,))
    return OrderedDict((("path", rel), ("name", name), ("expected_sha256", digest),
                        ("expected_count", block.get("expected_count")),
                        ("schema", block.get("schema"))))


def _read_partition(market_id: str, path: Path, rel: str) -> Tuple[bytes, Dict[str, Any]]:
    """The referenced bytes and document. A file that cannot be read or parsed
    is a named refusal, not a traceback out of the assembler's selection."""
    try:
        raw = path.read_bytes()
        return raw, json.loads(raw.decode("utf-8-sig"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise PartitionResolutionError(
            UNREADABLE_PARTITION, market_id,
            "%s could not be read as JSON: %s" % (rel, str(exc)[:160]))


def verify_reference(market_id: str, reference: Mapping[str, Any], package_dir: Path) -> Tuple[Path, Tuple[str, ...]]:
    """The referenced file exists, is a partition, is THIS market's, and is the
    bytes the contract expected. Returns ``(path, verified facts)``."""
    path = Path(package_dir) / reference["name"]
    if not path.is_file():
        raise PartitionResolutionError(
            REFERENCE_NOT_FOUND, market_id,
            "the contract references %s but no such file is committed" % reference["path"])
    raw, doc = _read_partition(market_id, path, reference["path"])
    if not isinstance(doc, Mapping):
        raise PartitionResolutionError(
            WRONG_PARTITION_SCHEMA, market_id, "%s is not a JSON object" % reference["path"])
    schema = str(doc.get("schema") or "")
    if not schema.startswith(PARTITION_SCHEMA_PREFIX):
        raise PartitionResolutionError(
            WRONG_PARTITION_SCHEMA, market_id,
            "%s declares schema %r, not a %s* partition" % (reference["path"], schema, PARTITION_SCHEMA_PREFIX))
    declared = str(doc.get("market_id") or "")
    if declared != market_id:
        raise PartitionResolutionError(
            WRONG_MARKET_PARTITION, market_id,
            "%s declares market_id %r; a partition may never stand in for another market's"
            % (reference["path"], declared))
    verified = ["exists", "schema", "market_id"]
    if reference.get("expected_sha256") is not None:
        actual = content_sha256(raw)
        if actual != reference["expected_sha256"]:
            raise PartitionResolutionError(
                REFERENCE_DIGEST_MISMATCH, market_id,
                "%s hashes to %s but the contract expects %s -- the partition moved without the "
                "contract being reissued" % (reference["path"], actual, reference["expected_sha256"]))
        verified.append("sha256")
    expected_count = reference.get("expected_count")
    if expected_count is not None:
        if doc.get("count") != expected_count:
            raise PartitionResolutionError(
                REFERENCE_COUNT_MISMATCH, market_id,
                "%s carries count %r but the contract expects %r"
                % (reference["path"], doc.get("count"), expected_count))
        verified.append("count")
    return path, tuple(verified)


# --------------------------------------------------------------------------- #
# The resolver.
# --------------------------------------------------------------------------- #

_CACHE: Dict[Tuple[Any, ...], PartitionResolution] = {}
_CACHE_LIMIT = 256


def _stat_key(path: Path) -> Tuple[Any, ...]:
    try:
        st = os.stat(path)
        return (str(path), st.st_mtime_ns, st.st_size)
    except OSError:
        return (str(path), None, None)


def is_registered(market_id: str, markets_dir: Optional[Path] = None) -> bool:
    directory = Path(markets_dir) if markets_dir else MC.MARKETS_DIR
    return (directory / ("%s.json" % market_id)).is_file()


def resolve_registered_market_partition(market_id: str, *, package_dir: Optional[Path] = None,
                                        markets_dir: Optional[Path] = None) -> PartitionResolution:
    """The one generic lookup. Registered market -> its release contract ->
    its ``final_partition`` reference -> the verified file. Legacy markets
    without a reference resolve through the frozen table, and say so.

    Raises :class:`PartitionResolutionError` with a code from
    :data:`FAILURE_CODES` on every gap; never guesses a filename.
    """
    mid = (market_id or "").strip()
    if not mid:
        raise PartitionResolutionError(EMPTY_MARKET_ID, market_id or "", "a market id is required")
    pkg = Path(package_dir) if package_dir else default_package_dir()
    if not is_registered(mid, markets_dir):
        directory = Path(markets_dir) if markets_dir else MC.MARKETS_DIR
        raise PartitionResolutionError(
            UNREGISTERED_MARKET, mid,
            "no market document at %s; only a registered market has a partition" % (directory / ("%s.json" % mid)))

    contract_path = RC.contract_path(mid)
    legacy_name = LEGACY_PARTITION_TABLE.get(mid)
    # The memo is keyed on the FILES the answer depends on (path, mtime,
    # size): a contract hit is stored under this key plus the referenced
    # partition's stat, a legacy hit under this key alone. A rewritten
    # contract or partition changes the key, so nothing stale is served.
    key = (mid, str(pkg), _stat_key(contract_path),
           _stat_key(pkg / legacy_name) if legacy_name else None)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached

    contract: Optional[Dict[str, Any]] = None
    contract_error = ""
    try:
        contract = RC.load_contract(mid)
    except RC.ReleaseContractError as exc:
        # A market with no contract, a wrong schema or a contract that names
        # another market. Legacy markets may still resolve by the table below;
        # a modern one has nothing to resolve from and is refused there.
        contract_error = str(exc)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        # A contract that exists but cannot be read is NOT an absent contract:
        # falling through to the legacy table here would let a corrupt
        # document resolve as though it had said nothing.
        raise PartitionResolutionError(
            UNREADABLE_CONTRACT, mid,
            "%s could not be read: %s" % (contract_path.name, str(exc)[:160]))

    block = contract.get(CONTRACT_BLOCK) if contract is not None else None
    if block is not None:
        reference = parse_reference(mid, block)
        full_key = key + (_stat_key(pkg / reference["name"]),)
        cached = _CACHE.get(full_key)
        if cached is not None:
            return cached
        path, verified = verify_reference(mid, reference, pkg)
        if legacy_name is not None and legacy_name != reference["name"]:
            raise PartitionResolutionError(
                CONTRACT_TABLE_DISAGREEMENT, mid,
                "the contract references %s but the legacy table names %s; neither is chosen over "
                "the other -- reissue the contract or retire the table row" % (reference["name"], legacy_name))
        resolution = PartitionResolution(
            market_id=mid, source=SOURCE_CONTRACT, path=path, name=reference["name"],
            reference=OrderedDict(block), legacy_entry=legacy_name, verified=verified)
        _remember(full_key, resolution)
        return resolution

    if legacy_name is not None:
        path = pkg / legacy_name
        if not path.is_file():
            raise PartitionResolutionError(
                LEGACY_PARTITION_MISSING, mid,
                "the legacy table names %s but no such file is committed" % legacy_name)
        resolution = PartitionResolution(
            market_id=mid, source=SOURCE_LEGACY_TABLE, path=path, name=legacy_name,
            reference=None, legacy_entry=legacy_name, verified=("exists",))
        _remember(key, resolution)
        return resolution

    if contract is None:
        raise PartitionResolutionError(
            NO_RELEASE_CONTRACT, mid,
            "no release contract to read a partition reference from (%s); a market registered after "
            "the legacy table was frozen must reference its partition there" % contract_error)
    raise PartitionResolutionError(
        MISSING_PARTITION_REFERENCE, mid,
        "the release contract carries no %r block and %s is not a legacy market; the assembler never "
        "guesses a filename -- write the reference with release_contracts.final_partition_block"
        % (CONTRACT_BLOCK, mid))


def _remember(key: Tuple[Any, ...], resolution: PartitionResolution) -> None:
    if len(_CACHE) >= _CACHE_LIMIT:
        _CACHE.clear()
    _CACHE[key] = resolution


def partition_path_or_none(market_id: str, *, package_dir: Optional[Path] = None) -> Optional[Path]:
    """The resolved partition path, or None on any failure -- for callers that
    only ask "is a partition present" and report the reason elsewhere."""
    try:
        return resolve_registered_market_partition(market_id, package_dir=package_dir).path
    except PartitionResolutionError:
        return None


def resolution_report(market_ids: Sequence[str], *, package_dir: Optional[Path] = None) -> "OrderedDict[str, Any]":
    """Every market's resolution and the per-source counts, for observability."""
    rows: "OrderedDict[str, Any]" = OrderedDict()
    counts = OrderedDict(((SOURCE_CONTRACT, 0), (SOURCE_LEGACY_TABLE, 0), (SOURCE_UNRESOLVED, 0)))
    for mid in market_ids:
        try:
            res = resolve_registered_market_partition(mid, package_dir=package_dir)
            rows[mid] = res.as_row()
            counts[res.source] += 1
        except PartitionResolutionError as exc:
            rows[mid] = OrderedDict((("market_id", mid), ("source", SOURCE_UNRESOLVED),
                                     ("code", exc.code), ("error", str(exc))))
            counts[SOURCE_UNRESOLVED] += 1
    return OrderedDict((("counts", counts), ("markets", rows),
                        ("legacy_table_size", len(LEGACY_PARTITION_TABLE))))


__all__ = [
    "CONTRACT_BLOCK", "FAILURE_CODES", "LEGACY_MARKET_IDS", "LEGACY_PARTITION_TABLE",
    "PACKAGE_PREFIX", "PARTITION_SCHEMA_PREFIX", "default_package_dir",
    "PartitionResolution", "PartitionResolutionError",
    "SOURCE_CONTRACT", "SOURCE_LEGACY_TABLE", "SOURCE_UNRESOLVED",
    "content_sha256", "is_registered", "parse_reference", "partition_path_or_none",
    "resolution_report", "resolve_registered_market_partition", "verify_reference",
]
