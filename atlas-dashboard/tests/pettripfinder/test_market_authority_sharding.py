"""PTF-MARKET-AUTHORITY-SHARDING-001 -- the per-market authority contract.

Three questions, and nothing else:

1. Is each market's shard well-formed and does it own only its own records?
2. Does assembling the shards reproduce the legacy global artifacts exactly,
   deterministically, on every run?
3. Does a collision BETWEEN two markets still fail closed, even though neither
   shard is wrong by itself?

The third is the one sharding could plausibly have broken. Splitting a file is
only safe if the rules that were enforced across the whole file are still
enforced across the whole union -- one URL binding two identities, one property
code binding two, one identity excluded twice, one street identity excluded
twice. Those checks now run on the assembled document, and these tests prove it
by building a colliding pair and requiring a refusal.
"""

from __future__ import annotations

import ast
import copy
import csv
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pettripfinder import hotel_exclusions as HE          # noqa: E402
from scripts.pettripfinder import identity_routing as IR          # noqa: E402
from scripts.pettripfinder import market_authority as MA          # noqa: E402

BASELINE_PATH = (MA.LAUNCH_PACKAGE / "markets" / "reports"
                 / "ptf_market_authority_sharding_001_baseline.json")


@pytest.fixture(scope="module")
def baseline():
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def market_ids():
    return MA.sharded_market_ids()


# --------------------------------------------------------------------------- #
# 1. Shard validation
# --------------------------------------------------------------------------- #

class TestShardsAreWellFormed:

    def test_every_registered_market_owns_a_shard_directory(self, market_ids):
        """A market with no records still owns its directory. Sharding is about
        WHERE a market writes, and a market whose first record has nowhere to go
        is a market whose first work order edits a shared file again."""
        assert set(market_ids) == set(MA.registered_market_ids())

    def test_every_shard_directory_holds_all_three_shards(self, market_ids):
        for market_id in market_ids:
            for path in (MA.routing_shard_path(market_id),
                         MA.exclusions_shard_path(market_id),
                         MA.seed_shard_path(market_id)):
                assert path.is_file(), path

    @pytest.mark.parametrize("market_id", MA.sharded_market_ids())
    def test_routing_shard_validates_under_the_unchanged_contract(self, market_id):
        document = MA.load_market_routing_document(market_id)
        assert document["schema"] == IR.SCHEMA
        # The shard is validated by the SAME validator the global file uses.
        # Sharding moved records; it did not fork the contract.
        assert IR.validate_authority(document) == document["routes"]

    @pytest.mark.parametrize("market_id", MA.sharded_market_ids())
    def test_exclusions_shard_validates_under_the_unchanged_contract(self, market_id):
        document = MA.load_market_exclusions_document(market_id)
        assert document["schema"] == HE.SCHEMA
        assert HE.validate(document) == document["exclusions"]

    @pytest.mark.parametrize("market_id", MA.sharded_market_ids())
    def test_a_shard_carries_only_its_own_market(self, market_id):
        for record in MA.load_market_routes(market_id):
            assert record["market_id"] == market_id
        for record in MA.load_market_exclusions(market_id):
            assert record["market_id"] == market_id
        for row in MA.load_market_seed_rows(market_id):
            assert row["market_id"] == market_id

    def test_seed_shards_keep_the_frozen_column_order(self, market_ids):
        for market_id in market_ids:
            with MA.seed_shard_path(market_id).open(encoding="utf-8", newline="") as f:
                assert tuple(csv.reader(f).__next__()) == MA.SEED_COLUMNS

    def test_a_shard_in_the_wrong_directory_is_refused(self, tmp_path):
        (tmp_path / "columbus-oh").mkdir()
        (tmp_path / "columbus-oh" / MA.ROUTING_SHARD_NAME).write_text(
            MA.render_json(MA.build_routing_shard("dayton-oh", [])), encoding="utf-8")
        with pytest.raises(MA.MarketAuthorityError, match="shard directory"):
            MA.load_market_routing_document("columbus-oh", authority_dir=tmp_path)

    def test_a_declared_count_that_lies_is_refused(self, tmp_path):
        (tmp_path / "columbus-oh").mkdir()
        document = MA.build_routing_shard("columbus-oh", [])
        document["count"] = 7
        (tmp_path / "columbus-oh" / MA.ROUTING_SHARD_NAME).write_text(
            MA.render_json(document), encoding="utf-8")
        with pytest.raises(MA.MarketAuthorityError, match="declares count"):
            MA.load_market_routing_document("columbus-oh", authority_dir=tmp_path)

    def test_an_unregistered_market_directory_is_refused(self, tmp_path):
        (tmp_path / "toledo-oh").mkdir()
        with pytest.raises(MA.MarketAuthorityError, match="unregistered market"):
            MA.sharded_market_ids(authority_dir=tmp_path)

    def test_a_missing_authority_directory_fails_closed(self, tmp_path):
        with pytest.raises(MA.MarketAuthorityError, match="does not exist"):
            MA.sharded_market_ids(authority_dir=tmp_path / "absent")


# --------------------------------------------------------------------------- #
# 2. Deterministic assembly, and equivalence with the recorded baseline
# --------------------------------------------------------------------------- #

class TestAssemblyIsDeterministic:

    def test_two_assemblies_are_byte_identical(self):
        first = [(str(p), t) for p, t in MA.generated_artifacts()]
        second = [(str(p), t) for p, t in MA.generated_artifacts()]
        assert first == second

    def test_market_union_order_does_not_depend_on_the_filesystem(self, market_ids):
        assert list(market_ids) == sorted(market_ids)

    def test_committed_global_artifacts_are_what_the_shards_produce(self):
        """The enforcement rule of write discipline (SS13). A market writer that
        hand-edits a generated global file instead of its shard makes this fail
        on the very next run -- exactly, not heuristically."""
        assert MA.check_generated_artifacts() == []

    def test_global_route_count_is_the_sum_of_the_shards(self, market_ids):
        expected = sum(len(MA.load_market_routes(m)) for m in market_ids)
        assert len(IR.load_routes()) == expected

    def test_global_exclusion_count_is_the_sum_of_the_shards(self, market_ids):
        expected = sum(len(MA.load_market_exclusions(m)) for m in market_ids)
        assert len(HE.load_exclusions()) == expected

    def test_global_seed_count_is_the_sum_of_the_shards(self, market_ids):
        expected = sum(len(MA.load_market_seed_rows(m)) for m in market_ids)
        with MA.GLOBAL_SEED_PATH.open(encoding="utf-8", newline="") as f:
            assert len(list(csv.DictReader(f))) == expected


class TestNothingMovedBetweenMarkets:
    """SS10. The baseline manifest was written before the split; every number in
    it must still hold, market by market. This is what makes "no per-market
    authority movement" a checked fact rather than a claim."""

    # PTF-CINCINNATI-PASS1-AUTHORITY-APPLICATION-001 legitimately grew
    # Cincinnati's shard after the sharding baseline was captured: 20 seed
    # rows and 6 VERIFIED_NO_PETS exclusions, from the founder's Pass 1
    # decisions. PTF-CINCINNATI-CATEGORY-EXIT-REGISTRY-REPAIR-001 then
    # registered 6 more -- OUT_OF_CURRENT_CATEGORY records for a disposition
    # the partition already carried, mechanically completed so
    # derive_authority() reconciles, matching Columbus/Pittsburgh's own
    # category-exit registration. Routing is unchanged (210) -- retiring a
    # route is a status flip, not a count change. That is same-market
    # growth, not cross-market movement, so it is named here explicitly
    # rather than silently baked into the frozen baseline file, which stays
    # a true historical snapshot of the sharding moment itself.
    _CINCINNATI_POST_BASELINE_DELTA = {"routing": 0, "exclusions": 12, "seed": 20}

    def test_per_market_totals_match_the_pre_split_baseline(self, baseline, market_ids):
        for market_id in market_ids:
            expected = dict(baseline["per_market_totals"][market_id])
            if market_id == "cincinnati-oh":
                for key, delta in self._CINCINNATI_POST_BASELINE_DELTA.items():
                    expected[key] += delta
            assert len(MA.load_market_routes(market_id)) == expected["routing"], market_id
            assert len(MA.load_market_exclusions(market_id)) == expected["exclusions"], market_id
            assert len(MA.load_market_seed_rows(market_id)) == expected["seed"], market_id

    def test_global_totals_match_the_pre_split_baseline(self, baseline):
        totals = baseline["global_totals"]
        assert len(IR.load_routes()) == totals["routing"] + self._CINCINNATI_POST_BASELINE_DELTA["routing"]
        assert len(HE.load_exclusions()) == totals["exclusions"] + self._CINCINNATI_POST_BASELINE_DELTA["exclusions"]
        assert len(MA.assemble_seed_rows()) == totals["seed_rows"] + self._CINCINNATI_POST_BASELINE_DELTA["seed"]

    def test_the_registered_market_set_is_unchanged(self, baseline):
        assert list(MA.registered_market_ids()) == baseline["registered_market_ids"]


# --------------------------------------------------------------------------- #
# 3. Cross-market collisions still fail closed
# --------------------------------------------------------------------------- #

def _shard_fixture(tmp_path, market_a="columbus-oh", market_b="dayton-oh"):
    for market_id in (market_a, market_b):
        (tmp_path / market_id).mkdir()
    return tmp_path


def _write_routing(tmp_path, market_id, routes):
    (tmp_path / market_id / MA.ROUTING_SHARD_NAME).write_text(
        MA.render_json(MA.build_routing_shard(market_id, routes)), encoding="utf-8")


class TestCollisionsBetweenMarketsAreCaught:

    def test_one_url_bound_by_two_markets_is_refused(self, tmp_path):
        _shard_fixture(tmp_path)
        columbus = next(r for r in MA.load_market_routes("columbus-oh")
                        if r.get("official_property_url"))
        intruder = copy.deepcopy(columbus)
        intruder["routing_id"] = "route-dayton-oh-intruder"
        intruder["market_id"] = "dayton-oh"
        intruder["hotel_ref"] = dict(intruder["hotel_ref"],
                                     market_id="dayton-oh",
                                     canonical_name="Intruder Inn",
                                     normalized_name="intruder inn",
                                     identity_key="intruder inn")
        _write_routing(tmp_path, "columbus-oh", [columbus])
        _write_routing(tmp_path, "dayton-oh", [intruder])
        # Neither shard is wrong on its own...
        MA.load_market_routing_document("columbus-oh", authority_dir=tmp_path)
        MA.load_market_routing_document("dayton-oh", authority_dir=tmp_path)
        # ...and the union still refuses them.
        with pytest.raises(IR.IdentityRoutingError, match="two different identities"):
            MA.assemble_routing_document(authority_dir=tmp_path)

    def test_one_identity_excluded_by_two_markets_is_refused(self, tmp_path):
        _shard_fixture(tmp_path)
        original = MA.load_market_exclusions("columbus-oh")[0]
        intruder = copy.deepcopy(original)
        intruder["market_id"] = "dayton-oh"
        for market_id, records in (("columbus-oh", [original]), ("dayton-oh", [intruder])):
            (tmp_path / market_id / MA.EXCLUSIONS_SHARD_NAME).write_text(
                MA.render_json(MA.build_exclusions_shard(market_id, records)),
                encoding="utf-8")
        with pytest.raises(HE.ExclusionContractError, match="duplicate"):
            MA.assemble_exclusions_document(authority_dir=tmp_path)

    def test_one_identity_seeded_by_two_markets_is_refused(self, tmp_path):
        _shard_fixture(tmp_path)
        original = MA.load_market_seed_rows("columbus-oh")[0]
        intruder = dict(original, market_id="dayton-oh")
        for market_id, rows in (("columbus-oh", [original]), ("dayton-oh", [intruder])):
            (tmp_path / market_id / MA.SEED_SHARD_NAME).write_text(
                MA.render_seed_csv(rows), encoding="utf-8")
        with pytest.raises(MA.MarketAuthorityError, match="one identity is one listing"):
            MA.assemble_seed_rows(authority_dir=tmp_path)


# --------------------------------------------------------------------------- #
# 4. The manifest
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def manifest():
    return json.loads(MA.MANIFEST_PATH.read_text(encoding="utf-8"))


class TestManifest:

    def test_manifest_is_committed_and_current(self, manifest):
        assert manifest == MA.build_manifest()

    def test_manifest_carries_no_wall_clock_timestamp(self, manifest):
        """A timestamp would change the manifest on a rebuild that changed
        nothing, which is precisely the question the manifest exists to answer."""
        text = json.dumps(manifest)
        assert "generated_at" not in manifest
        assert "T00:00" not in text

    def test_manifest_counts_agree_with_the_shards(self, manifest, market_ids):
        by_id = {m["market_id"]: m for m in manifest["markets"]}
        assert list(by_id) == list(market_ids)
        for market_id in market_ids:
            entry = by_id[market_id]
            assert entry["routing_count"] == len(MA.load_market_routes(market_id))
            assert entry["exclusions_count"] == len(MA.load_market_exclusions(market_id))
            assert entry["seed_count"] == len(MA.load_market_seed_rows(market_id))
        assert manifest["global_routing_count"] == sum(
            e["routing_count"] for e in manifest["markets"])
        assert manifest["global_exclusions_count"] == sum(
            e["exclusions_count"] for e in manifest["markets"])
        assert manifest["global_seed_count"] == sum(
            e["seed_count"] for e in manifest["markets"])

    def test_generated_artifact_hashes_match_the_committed_files(self, manifest):
        for entry in manifest["generated_artifacts"]:
            path = REPO_ROOT / entry["path"]
            assert MA._sha256(path.read_text(encoding="utf-8")) == entry["hash"], entry["path"]


# --------------------------------------------------------------------------- #
# 5. Write discipline (SS13)
# --------------------------------------------------------------------------- #

#: Modules that wrote a global artifact directly BEFORE sharding existed. Each
#: is a completed, already-run market integration; they are grandfathered rather
#: than rewritten because rewriting a script whose only remaining value is the
#: record of what it did would destroy that record. This list may SHRINK --
#: never grow. A NEW module that writes a generated global instead of its own
#: shard is the exact regression this test exists to catch.
#:
#: Frozen at PTF-MARKET-AUTHORITY-SHARDING-001 against baseline
#: 20279f4b6f66a073f69823275c23f5c3481f173b.
LEGACY_GLOBAL_WRITERS = frozenset({
    "scripts/pettripfinder/cincinnati_url_routing_finalize_001.py",
    "scripts/pettripfinder/cleveland_pass2_decision_application.py",
    "scripts/pettripfinder/cleveland_pass3_decision_application.py",
    "scripts/pettripfinder/cleveland_pass4_decision_application.py",
    "scripts/pettripfinder/cleveland_routing_repair_001.py",
    "scripts/pettripfinder/indianapolis_decision_application_001.py",
    "scripts/pettripfinder/indianapolis_live_publication_001.py",
    "scripts/pettripfinder/integrate_cleveland_authority.py",
    "scripts/pettripfinder/integrate_cleveland_capture_003.py",
    "scripts/pettripfinder/migrate_market_ownership.py",
    "scripts/pettripfinder/pittsburgh_pass1_decision_application.py",
    "scripts/pettripfinder/pittsburgh_pass2_decision_application.py",
    "scripts/pettripfinder/upgrade_identity_routing.py",
})

_GLOBAL_BASENAMES = ("identity_routing.json", "hotel_exclusions.json",
                     "seed_businesses.csv")
_WRITE_ATTRS = {"write_text", "write_bytes", "writelines", "write"}
_WRITE_CALLS = {"write_lf", "write_json", "write_csv", "dump", "_write", "_dump"}


def _is_global_artifact_path(value) -> bool:
    """True when this expression BUILDS a path to a generated global file.

    Structural rather than textual on purpose: several modules mention
    ``seed_businesses.csv`` inside a provenance note or a source-authority list,
    and a note is not a write. What identifies a path is the join --
    ``<something> / "identity_routing.json"`` -- or a bare filename constant.
    """
    if isinstance(value, ast.Constant) and value.value in _GLOBAL_BASENAMES:
        return True
    for node in ast.walk(value):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div) \
                and isinstance(node.right, ast.Constant) \
                and node.right.value in _GLOBAL_BASENAMES:
            return True
    return False


#: The published names of the global-artifact path constants. A module that
#: imports one of these writes the same file as a module that rebuilds the path
#: itself, so the scan has to follow both.
_GLOBAL_PATH_NAMES = frozenset({
    "ROUTING_PATH", "EXCLUSIONS_PATH", "SEED_PATH", "PRODUCTION_CSV",
    "GLOBAL_ROUTING_PATH", "GLOBAL_EXCLUSIONS_PATH", "GLOBAL_SEED_PATH",
})


def _names_bound_to_a_global_artifact(tree):
    """Local names that refer to a generated global file's path.

    Three ways a module gets one: it builds the path, it imports the constant,
    or it aliases a name that already refers to one.
    """
    bound = set()
    assigns = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name in _GLOBAL_PATH_NAMES:
                    bound.add(alias.asname or alias.name)
        elif isinstance(node, ast.Assign):
            assigns.append(node)
    # To a fixed point: ``ast.walk`` does not visit in source order, so an alias
    # chain would otherwise resolve or not depending on tree shape.
    changed = True
    while changed:
        changed = False
        for node in assigns:
            aliased = (isinstance(node.value, ast.Name)
                       and node.value.id in bound) or (
                       isinstance(node.value, ast.Attribute)
                       and node.value.attr in _GLOBAL_PATH_NAMES)
            if not (_is_global_artifact_path(node.value) or aliased):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id not in bound:
                    bound.add(target.id)
                    changed = True
    return bound


def _writes_a_global_artifact(path: Path) -> bool:
    source = path.read_text(encoding="utf-8")
    if not any(b in source for b in _GLOBAL_BASENAMES) \
            and not any(n in source for n in _GLOBAL_PATH_NAMES):
        return False
    tree = ast.parse(source)
    bound = _names_bound_to_a_global_artifact(tree)
    if not bound:
        return False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # <bound>.write_text(...) / .open("wb") etc.
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) \
                and func.value.id in bound:
            if func.attr in _WRITE_ATTRS:
                return True
            # ``.open()`` is how these files are READ far more often than
            # written, so the mode decides. No mode is "r".
            if func.attr == "open" and node.args:
                mode = node.args[0]
                if isinstance(mode, ast.Constant) and isinstance(mode.value, str) \
                        and set(mode.value) & set("wax+"):
                    return True
        # write_lf(<bound>, ...) / json.dump(doc, <bound>) etc.
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        if name in _WRITE_CALLS:
            for arg in node.args:
                if isinstance(arg, ast.Name) and arg.id in bound:
                    return True
    return False


class TestWriteDiscipline:
    """SS13. After sharding, a market work order updates ONLY its own shard.

    Two layers, and the weaker one is named as weaker. The EXACT enforcement is
    ``test_committed_global_artifacts_are_what_the_shards_produce`` above: a
    hand-edit to a generated file fails it immediately and cannot be argued
    with. The static scan below is an earlier, deliberately incomplete warning
    -- it recognises the write idioms these scripts actually use, and a
    sufficiently indirect writer will slip past it. It is worth having anyway
    because it names the offending FILE, which the byte check cannot.
    """

    def test_the_scan_recognises_a_writer(self, tmp_path):
        """Positive control. Without this, a detector that had quietly stopped
        matching anything would report a clean repository forever."""
        module = tmp_path / "pretend_market_writer.py"
        module.write_text(
            "from pathlib import Path\n"
            "LP = Path('launch_packages/pettripfinder')\n"
            "ROUTES = LP / 'identity_routing.json'\n"
            "ROUTES.write_text('{}', encoding='utf-8')\n", encoding="utf-8")
        assert _writes_a_global_artifact(module)

    def test_the_scan_does_not_fire_on_a_reader(self, tmp_path):
        module = tmp_path / "pretend_reader.py"
        module.write_text(
            "from pathlib import Path\n"
            "LP = Path('launch_packages/pettripfinder')\n"
            "SEED = LP / 'seed_businesses.csv'\n"
            "rows = SEED.open(encoding='utf-8').readlines()\n", encoding="utf-8")
        assert not _writes_a_global_artifact(module)

    def test_the_legacy_list_is_exactly_what_the_scan_finds(self):
        """The exemption may not be padded. An entry for a module the scan does
        not flag exempts a filename rather than a known writer, and would
        silently cover a future file that reuses the name."""
        found = {p.relative_to(REPO_ROOT).as_posix()
                 for p in (REPO_ROOT / "scripts" / "pettripfinder").rglob("*.py")
                 if _writes_a_global_artifact(p)}
        assert found == set(LEGACY_GLOBAL_WRITERS)

    def test_no_new_module_writes_a_generated_global_artifact(self):
        offenders = []
        for path in sorted((REPO_ROOT / "scripts" / "pettripfinder").rglob("*.py")):
            rel = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
            if rel in LEGACY_GLOBAL_WRITERS:
                continue
            if _writes_a_global_artifact(path):
                offenders.append(rel)
        assert offenders == [], (
            "these modules write a GENERATED global authority file directly. A "
            "market writer updates launch_packages/pettripfinder/markets/"
            "authority/<market_id>/ and then runs build_global_authority.py: %s"
            % offenders)

    def test_the_legacy_writer_list_only_shrinks(self):
        """Every grandfathered module must still exist. A stale entry would
        silently widen the exemption for a future file of the same name."""
        for rel in sorted(LEGACY_GLOBAL_WRITERS):
            assert (REPO_ROOT / rel).is_file(), rel
