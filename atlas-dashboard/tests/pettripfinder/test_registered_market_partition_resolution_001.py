"""PTF-FINAL-ASSEMBLER-REGISTERED-MARKET-DISCOVERY-001 -- the whole-site
assembler resolves a registered market's final partition through the market's
own release contract, never through a table in its own source.

The property under test is the one that matters for a market factory: a market
registered by the ordinary lane -- market document, census, policy package,
partition, contract carrying the ``final_partition`` reference -- becomes
assemblable with ZERO edits to assembler code and ZERO static-table entries.
Two synthetic markets prove it. ``westlake-xx`` is registered the modern way
and resolves; ``boise-id`` commits a partition spelled so the OLD glob would
have matched it (``boise_final_partition_001.json``) and no reference, and is
refused -- a new market cannot fall through to a legacy path.

Every failure the resolver can report is exercised by name, the fifteen
legacy markets are pinned to exactly the files the old lookup returned, and
the assembler's source is checked to name no partition file at all.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import time
from collections import OrderedDict
from pathlib import Path

import pytest

from scripts.pettripfinder import assemble_production_site as gasm
from scripts.pettripfinder import market_partition_resolution as MPR
from scripts.pettripfinder import registration_data_only as RD
from scripts.pettripfinder import release_contracts as RC
from scripts.pettripfinder import site_data as SD
from scripts.pettripfinder.markets import contract as MC
from scripts.pettripfinder.markets import load_markets

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_PKG = REPO_ROOT / "launch_packages" / "pettripfinder"
REAL_CONTRACTS = REPO_ROOT / "deploy" / "netlify" / "release_contracts"

#: What the assembler's former table + glob returned on the day the lookup was
#: replaced. The FROZEN legacy set; a new key here is a visible decision.
FROZEN_LEGACY = OrderedDict((
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
    ("milwaukee-wi", "milwaukee_final_partition_001.json"),
    ("pittsburgh-pa", "pittsburgh_final_partition_001.json"),
))

MODERN = "westlake-xx"          # registered the modern way; never hard-coded anywhere
GLOB_SHAPED = "boise-id"        # its file would have matched the old glob; no reference


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=OrderedDict)


SEED_HEADER = ("name,category,address,city,state,postal_code,phone,website_url,source_url,"
               "source_type,observed_at,rating,amenities,pet_policy,canonical,market_id")


def _write(path: Path, doc) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8", newline="\n")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _partition_doc(market_id: str, count: int = 3):
    return OrderedDict((
        ("schema", "ptf-market-final-partition/1.1"),
        ("work_order", "TEST-FIXTURE"),
        ("market_id", market_id),
        ("count", count),
        ("counts_by_state", OrderedDict((("PUBLISHED_PET_FRIENDLY", count),))),
        ("resolved", count), ("unresolved", 0),
        ("items", [OrderedDict((("identity_key", "hotel %d" % i), ("final_state", "PUBLISHED_PET_FRIENDLY"),
                                ("resolved", True))) for i in range(count)]),
    ))


class Fixture:
    """A repository-shaped tree with only what the resolver reads."""

    def __init__(self, root: Path, monkeypatch):
        self.root = root
        self.pkg = root / "launch_packages" / "pettripfinder"
        self.markets = self.pkg / "markets"
        self.contracts = root / "deploy" / "netlify" / "release_contracts"
        self.markets.mkdir(parents=True)
        self.contracts.mkdir(parents=True)
        monkeypatch.setattr(MC, "MARKETS_DIR", self.markets)
        monkeypatch.setattr(RC, "RELEASE_CONTRACTS_DIR", self.contracts)
        monkeypatch.setattr(RC, "REPO_ROOT", self.root)
        # No MPR path constant to patch: the resolver derives its package
        # directory from release_contracts.REPO_ROOT at call time, patched
        # above, exactly as package_staging's overlay redirects it.
        monkeypatch.setattr(gasm, "PACKAGE_DIR", self.pkg)
        monkeypatch.setattr(gasm, "CENSUS_DIR", self.pkg / "identity_census")
        # The inventory side of market_eligibility: an empty production CSV and
        # an empty policy package make "policy_authority_present" a real read
        # that raises nothing, and leave the fixture at an HONEST ZERO -- the
        # state the assembler documents for a registered market below its own
        # threshold. Raleigh proves the loaded case with 63 profiles.
        monkeypatch.setattr(SD, "PRODUCTION_CSV", self.pkg / "seed_businesses.csv")
        monkeypatch.setattr(SD, "PUBLISHED_FACTS_PATH", self.pkg / "hotel_policy_facts.json")
        self._seed_rows = []
        _write_text(self.pkg / "seed_businesses.csv", SEED_HEADER + chr(10))
        self._template_market = _json(REAL_PKG / "markets" / "nashville-tn.json")
        self._template_contract = _json(REAL_CONTRACTS / "nashville-tn.json")

    def register(self, market_id: str, *, census: bool = True, policy: bool = True) -> None:
        """Register the market the ordinary way: the market document, its
        identity census, its policy package and its seed inventory row -- the
        four things a registration commits that the assembler's eligibility
        conditions read. One published profile against the contract's minimum
        of one, so the fixture is genuinely ASSEMBLABLE rather than an
        eligibility row with a hole in it."""
        text = json.dumps(self._template_market).replace("nashville-tn", market_id)
        doc = json.loads(text, object_pairs_hook=OrderedDict)
        doc["market_name"] = "Fixture %s" % market_id
        doc["minimum_published_hotels"] = 1
        _write(self.markets / ("%s.json" % market_id), doc)
        if census:
            _write(self.pkg / "identity_census" / ("%s.json" % market_id), OrderedDict((
                ("schema", "ptf-market-identity-census/1.1"), ("market_id", market_id),
                ("count", 1), ("hotels", []))))
        if policy:
            name = "Fixture Inn %s" % market_id.replace("-", " ")
            key = SD.normalize_name(name)
            _write(self.pkg / ("hotel_policy_facts_%s.json" % market_id), OrderedDict((
                ("schema_version", "1.3"), ("market", market_id), ("market_id", market_id),
                ("hotels", [OrderedDict((
                    ("key", key), ("identity_key", key), ("name", name),
                    ("market_id", market_id), ("schema_version", "1.3"),
                    ("facts", OrderedDict((("pets_allowed", True),)))))]))))
            self._seed_rows.append(
                "%s,pet-friendly-hotels,%d Fixture Way,Fixtureville,XX,00001,,"
                "https://example.invalid/,https://example.invalid/,first_party,2026-01-01,,,"
                "Pets allowed.,true,%s" % (name, 100 + len(self._seed_rows), market_id))
            _write_text(self.pkg / "seed_businesses.csv",
                        chr(10).join([SEED_HEADER] + self._seed_rows) + chr(10))

    def partition(self, market_id: str, name: str = None, count: int = 3, doc=None) -> Path:
        name = name or "%s_final_partition_001.json" % market_id.replace("-", "_")
        path = self.pkg / name
        _write(path, doc if doc is not None else _partition_doc(market_id, count))
        return path

    def contract(self, market_id: str, block=None, *, with_block: bool = True, position: str = "policy_package"):
        text = json.dumps(self._template_contract).replace("nashville-tn", market_id).replace("nashville_tn", market_id.replace("-", "_"))
        doc = json.loads(text, object_pairs_hook=OrderedDict)
        doc.pop("reconciliation_cross_checks", None)
        if with_block:
            block = block if block is not None else RC.final_partition_block(market_id)
            out = OrderedDict()
            for key, value in doc.items():
                out[key] = value
                if key == position:
                    out["final_partition"] = block
            doc = out
        _write(self.contracts / ("%s.json" % market_id), doc)
        return doc

    def market_config(self, market_id: str):
        return MC.parse_market(_json(self.markets / ("%s.json" % market_id)), source=market_id)


@pytest.fixture
def fx(tmp_path, monkeypatch):
    MPR._CACHE.clear()
    yield Fixture(tmp_path, monkeypatch)
    MPR._CACHE.clear()


# --------------------------------------------------------------------------- #
# The legacy set is frozen, and moved no market.
# --------------------------------------------------------------------------- #

class TestTheFrozenLegacyTable:
    def test_the_table_is_exactly_the_frozen_set(self):
        assert OrderedDict(MPR.LEGACY_PARTITION_TABLE) == FROZEN_LEGACY
        assert MPR.LEGACY_MARKET_IDS == frozenset(FROZEN_LEGACY)

    def test_every_registered_market_resolves_to_the_file_the_old_lookup_returned(self):
        MPR._CACHE.clear()
        report = MPR.resolution_report([m.market_id for m in load_markets()])
        assert report["counts"][MPR.SOURCE_UNRESOLVED] == 0, report["markets"]
        for market_id, expected in FROZEN_LEGACY.items():
            assert report["markets"][market_id]["partition"] == expected, market_id
        # Indianapolis's contract already carried {path, expected_count}
        # (PTF-INDIANAPOLIS-PROMOTION-REMEDIATION-005); it agrees with the
        # table and therefore resolves by CONTRACT. Every other legacy market
        # resolves by the table, and says so.
        assert report["markets"]["indianapolis-in"]["source"] == MPR.SOURCE_CONTRACT
        assert report["counts"][MPR.SOURCE_LEGACY_TABLE] == len(FROZEN_LEGACY) - 1

    def test_a_legacy_live_market_resolves_through_the_permitted_fallback_and_says_so(self):
        res = MPR.resolve_registered_market_partition("milwaukee-wi")
        assert res.source == MPR.SOURCE_LEGACY_TABLE
        assert res.name == "milwaukee_final_partition_001.json"
        assert res.verified == ("exists",)
        assert res.legacy_entry == res.name
        assert gasm._partition_path("milwaukee-wi") == res.path

    def test_the_assembler_source_names_no_partition_file_and_no_glob(self):
        source = Path(gasm.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        literals = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        assert not [s for s in literals if "final_partition_" in s and s.endswith(".json")]
        assert not [s for s in literals if "_final_partition_*" in s]
        assert "rsplit(\"-\", 1)" not in source

    def test_the_resolver_imports_no_build_deploy_or_generator_code(self):
        tree = ast.parse(Path(MPR.__file__).read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
                imported.update("%s.%s" % (node.module, a.name) for a in node.names)
            elif isinstance(node, ast.Import):
                imported.update(a.name for a in node.names)
        project = {m for m in imported if m.startswith("scripts.")}
        assert project == {"scripts.pettripfinder", "scripts.pettripfinder.release_contracts",
                           "scripts.pettripfinder.markets", "scripts.pettripfinder.markets.contract"}


# --------------------------------------------------------------------------- #
# A modern market: registered, contract-referenced, no table entry anywhere.
# --------------------------------------------------------------------------- #

class TestAModernRegisteredMarket:
    def test_resolves_without_any_table_entry(self, fx):
        fx.register(MODERN)
        fx.partition(MODERN)
        fx.contract(MODERN)
        assert MODERN not in MPR.LEGACY_PARTITION_TABLE
        res = MPR.resolve_registered_market_partition(MODERN)
        assert res.source == MPR.SOURCE_CONTRACT
        assert res.name == "westlake_xx_final_partition_001.json"
        assert res.verified == ("exists", "schema", "market_id", "sha256", "count")
        assert res.legacy_entry is None
        assert res.path.is_file()

    def test_the_assembler_discovers_it_with_zero_code_and_zero_table_changes(self, fx):
        before = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
                  for p in (gasm.__file__, MPR.__file__)}
        table_before = dict(MPR.LEGACY_PARTITION_TABLE)
        # -- register the market the ordinary way: document, partition, contract
        fx.register(MODERN)
        fx.partition(MODERN)
        fx.contract(MODERN)
        # -- the assembler sees it
        assert gasm._partition_path(MODERN).name == "westlake_xx_final_partition_001.json"
        row = gasm.market_eligibility(fx.market_config(MODERN))
        assert row["conditions"]["final_partition_present"] is True
        assert row["partition_source"] == MPR.SOURCE_CONTRACT
        assert row["partition_path"] == "westlake_xx_final_partition_001.json"
        assert row["partition_error"] == ""
        assert list(row["conditions"]) == ["census_present", "final_partition_present",
                                           "policy_authority_present", "meets_minimum_published"]
        # PHASE 6, the property that matters: an arbitrary market id the
        # assembler has never heard of is ASSEMBLABLE on its registration
        # alone -- census, partition, policy authority and its own published
        # minimum, all four true, with no edit to any shared module.
        assert row["conditions"] == {"census_present": True, "final_partition_present": True,
                                     "policy_authority_present": True, "meets_minimum_published": True}
        assert row["assemblable"] is True
        assert row["published_count"] == 1 and row["inventory_error"] == ""
        # -- and nothing in code or table moved to make that happen
        after = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in before}
        assert after == before
        assert dict(MPR.LEGACY_PARTITION_TABLE) == table_before
        assert MODERN not in Path(gasm.__file__).read_text(encoding="utf-8")
        assert MODERN not in Path(MPR.__file__).read_text(encoding="utf-8")

    def test_a_second_synthetic_market_resolves_generically(self, fx):
        other = "harbor-town-qq"
        fx.register(other)
        fx.partition(other, "harbor_town_qq_final_partition_004.json", count=7)
        fx.contract(other)
        res = MPR.resolve_registered_market_partition(other)
        assert res.source == MPR.SOURCE_CONTRACT and res.name == "harbor_town_qq_final_partition_004.json"
        assert res.reference["expected_count"] == 7

    def test_a_partition_filename_change_follows_the_contract_reference(self, fx):
        fx.register(MODERN)
        old = fx.partition(MODERN, "westlake_xx_final_partition_001.json")
        fx.contract(MODERN)
        assert MPR.resolve_registered_market_partition(MODERN).name.endswith("_001.json")
        # The partition of record moves to 002; the old file is kept, as every
        # market keeps its earlier partitions. Until the contract is reissued
        # the old reference still resolves (to 001) -- a rename is a decision.
        new = fx.partition(MODERN, "westlake_xx_final_partition_002.json", count=4)
        MPR._CACHE.clear()
        assert MPR.resolve_registered_market_partition(MODERN).name.endswith("_001.json")
        with pytest.raises(RC.ReleaseContractError, match="name the partition of record"):
            RC.final_partition_block(MODERN)                       # two candidates: decide
        fx.contract(MODERN, RC.final_partition_block(MODERN, "westlake_xx_final_partition_002.json"))
        MPR._CACHE.clear()
        res = MPR.resolve_registered_market_partition(MODERN)
        assert res.name == "westlake_xx_final_partition_002.json" and res.path == new
        assert old.is_file()
        # Now the old file is removed and the contract still names 002: fine.
        old.unlink()
        MPR._CACHE.clear()
        assert MPR.resolve_registered_market_partition(MODERN).name.endswith("_002.json")

    def test_the_memo_never_serves_a_stale_answer(self, fx):
        fx.register(MODERN)
        fx.partition(MODERN)
        fx.contract(MODERN)
        first = MPR.resolve_registered_market_partition(MODERN)
        assert MPR.resolve_registered_market_partition(MODERN) is first          # cached
        time.sleep(0.01)
        fx.partition(MODERN, count=5)                                            # bytes moved
        with pytest.raises(MPR.PartitionResolutionError) as err:
            MPR.resolve_registered_market_partition(MODERN)
        assert err.value.code == MPR.REFERENCE_DIGEST_MISMATCH


# --------------------------------------------------------------------------- #
# Every refusal, by name.
# --------------------------------------------------------------------------- #

def _problems(result) -> list:
    return list((result.get("detail") or {}).get("problems") or [])


def _code(fx, market_id: str) -> str:
    with pytest.raises(MPR.PartitionResolutionError) as err:
        MPR.resolve_registered_market_partition(market_id)
    return err.value.code


class TestEveryRefusal:
    def test_a_missing_partition_reference_fails(self, fx):
        fx.register(MODERN)
        fx.partition(MODERN)
        fx.contract(MODERN, with_block=False)
        assert _code(fx, MODERN) == MPR.MISSING_PARTITION_REFERENCE
        assert gasm._partition_path(MODERN) is None
        row = gasm.market_eligibility(fx.market_config(MODERN))
        assert row["conditions"]["final_partition_present"] is False
        assert row["partition_source"] == MPR.SOURCE_UNRESOLVED
        assert MPR.MISSING_PARTITION_REFERENCE in row["partition_error"]

    def test_a_new_market_cannot_silently_rely_on_the_legacy_path(self, fx):
        # boise_final_partition_001.json is exactly what the OLD glob built
        # for "boise-id" (strip the last segment). No reference -> refused.
        fx.register(GLOB_SHAPED)
        fx.partition(GLOB_SHAPED, "boise_final_partition_001.json")
        fx.contract(GLOB_SHAPED, with_block=False)
        assert GLOB_SHAPED not in MPR.LEGACY_PARTITION_TABLE
        assert _code(fx, GLOB_SHAPED) == MPR.MISSING_PARTITION_REFERENCE
        assert gasm._partition_path(GLOB_SHAPED) is None

    def test_a_reference_to_a_missing_file_fails(self, fx):
        fx.register(MODERN)
        fx.partition(MODERN)
        block = RC.final_partition_block(MODERN)
        block["path"] = "launch_packages/pettripfinder/westlake_xx_final_partition_009.json"
        fx.contract(MODERN, block)
        assert _code(fx, MODERN) == MPR.REFERENCE_NOT_FOUND

    def test_a_wrong_market_partition_reference_fails(self, fx):
        fx.register(MODERN)
        fx.partition(MODERN, "westlake_xx_final_partition_001.json", doc=_partition_doc("harbor-town-qq"))
        block = OrderedDict((
            ("path", "launch_packages/pettripfinder/westlake_xx_final_partition_001.json"),
            ("schema", "ptf-market-final-partition/1.1"),
            ("expected_sha256", MPR.content_sha256((fx.pkg / "westlake_xx_final_partition_001.json").read_bytes())),
            ("expected_count", 3), ("note", "typed on purpose")))
        fx.contract(MODERN, block)
        assert _code(fx, MODERN) == MPR.WRONG_MARKET_PARTITION
        with pytest.raises(RC.ReleaseContractError, match="not market"):
            RC.final_partition_block(MODERN)

    @pytest.mark.parametrize("block, code", [
        ([{"path": "launch_packages/pettripfinder/a.json"}, {"path": "launch_packages/pettripfinder/b.json"}],
         MPR.AMBIGUOUS_REFERENCE),
        ({"paths": ["launch_packages/pettripfinder/westlake_xx_final_partition_001.json"], "expected_sha256": "0" * 64},
         MPR.AMBIGUOUS_REFERENCE),
        ({"path": "launch_packages/pettripfinder/westlake_xx_final_partition_*.json", "expected_sha256": "0" * 64},
         MPR.AMBIGUOUS_REFERENCE),
        ({"path": ["launch_packages/pettripfinder/westlake_xx_final_partition_001.json"], "expected_sha256": "0" * 64},
         MPR.AMBIGUOUS_REFERENCE),
        ("launch_packages/pettripfinder/westlake_xx_final_partition_001.json", MPR.MALFORMED_REFERENCE),
        ({"expected_sha256": "0" * 64}, MPR.MALFORMED_REFERENCE),
        ({"path": "elsewhere/westlake_xx_final_partition_001.json", "expected_sha256": "0" * 64},
         MPR.MALFORMED_REFERENCE),
        ({"path": "launch_packages/pettripfinder/sub/westlake_xx_final_partition_001.json", "expected_sha256": "0" * 64},
         MPR.MALFORMED_REFERENCE),
        ({"path": "launch_packages/pettripfinder/westlake_xx_final_partition_001.json"}, MPR.MALFORMED_REFERENCE),
        ({"path": "launch_packages/pettripfinder/westlake_xx_final_partition_001.json", "expected_sha256": "abc"},
         MPR.MALFORMED_REFERENCE),
    ])
    def test_an_ambiguous_or_malformed_reference_fails(self, fx, block, code):
        fx.register(MODERN)
        fx.partition(MODERN)
        fx.contract(MODERN, block)
        assert _code(fx, MODERN) == code

    def test_a_digest_mismatch_fails_closed(self, fx):
        fx.register(MODERN)
        fx.partition(MODERN)
        block = RC.final_partition_block(MODERN)
        fx.contract(MODERN, block)
        time.sleep(0.01)
        fx.partition(MODERN, count=4)                       # regenerated, contract not reissued
        assert _code(fx, MODERN) == MPR.REFERENCE_DIGEST_MISMATCH
        assert RC.final_partition_disagreements(_json(fx.contracts / (MODERN + ".json")), MODERN)

    def test_a_count_mismatch_fails_closed(self, fx):
        fx.register(MODERN)
        fx.partition(MODERN)
        block = RC.final_partition_block(MODERN)
        block["expected_count"] = 99
        fx.contract(MODERN, block)
        assert _code(fx, MODERN) == MPR.REFERENCE_COUNT_MISMATCH

    def test_a_wrong_schema_fails(self, fx):
        fx.register(MODERN)
        doc = _partition_doc(MODERN)
        doc["schema"] = "ptf-market-identity-census/1.1"
        fx.partition(MODERN, doc=doc)
        raw = (fx.pkg / "westlake_xx_final_partition_001.json").read_bytes()
        fx.contract(MODERN, OrderedDict((("path", "launch_packages/pettripfinder/westlake_xx_final_partition_001.json"),
                                         ("expected_sha256", MPR.content_sha256(raw)))))
        assert _code(fx, MODERN) == MPR.WRONG_PARTITION_SCHEMA

    def test_contract_and_legacy_table_disagreement_fails(self, fx):
        legacy = "nashville-tn"                       # a frozen legacy id, staged in the fixture
        fx.register(legacy)
        fx.partition(legacy, "nashville_tn_final_partition_001.json")
        fx.partition(legacy, "nashville_tn_final_partition_002.json", count=4)
        fx.contract(legacy, RC.final_partition_block(legacy, "nashville_tn_final_partition_002.json"))
        assert _code(fx, legacy) == MPR.CONTRACT_TABLE_DISAGREEMENT
        assert gasm._partition_path(legacy) is None                 # neither side is chosen

    def test_contract_and_legacy_table_agreement_resolves_by_contract(self, fx):
        legacy = "nashville-tn"
        fx.register(legacy)
        fx.partition(legacy, "nashville_tn_final_partition_001.json")
        fx.contract(legacy, RC.final_partition_block(legacy, "nashville_tn_final_partition_001.json"))
        res = MPR.resolve_registered_market_partition(legacy)
        assert res.source == MPR.SOURCE_CONTRACT
        assert res.legacy_entry == "nashville_tn_final_partition_001.json" == res.name

    def test_a_legacy_market_may_keep_a_digestless_block_but_a_new_market_may_not(self, fx):
        legacy = "indianapolis-in"
        fx.register(legacy)
        fx.partition(legacy, "indianapolis_in_final_partition_023.json", count=264)
        fx.contract(legacy, OrderedDict((("path", "launch_packages/pettripfinder/indianapolis_in_final_partition_023.json"),
                                         ("expected_count", 264))))
        res = MPR.resolve_registered_market_partition(legacy)
        assert res.source == MPR.SOURCE_CONTRACT and "sha256" not in res.verified
        fx.register(MODERN)
        fx.partition(MODERN)
        fx.contract(MODERN, OrderedDict((("path", "launch_packages/pettripfinder/westlake_xx_final_partition_001.json"),
                                         ("expected_count", 3))))
        assert _code(fx, MODERN) == MPR.MALFORMED_REFERENCE

    def test_an_unreadable_partition_or_contract_is_a_named_refusal_not_a_traceback(self, fx):
        fx.register(MODERN)
        fx.partition(MODERN)
        fx.contract(MODERN)
        (fx.pkg / "westlake_xx_final_partition_001.json").write_text("{not json", encoding="utf-8")
        MPR._CACHE.clear()
        assert _code(fx, MODERN) == MPR.UNREADABLE_PARTITION
        # A CORRUPT contract must not fall through to the legacy table: a
        # document that cannot be read has not said "nothing".
        legacy = "nashville-tn"
        fx.register(legacy)
        fx.partition(legacy, "nashville_tn_final_partition_001.json")
        (fx.contracts / (legacy + ".json")).write_text("{not json", encoding="utf-8")
        MPR._CACHE.clear()
        assert _code(fx, legacy) == MPR.UNREADABLE_CONTRACT
        # and the assembler reports it rather than aborting the composition
        row = gasm.market_eligibility(fx.market_config(legacy))
        assert row["conditions"]["final_partition_present"] is False
        assert row["partition_source"] == MPR.SOURCE_UNRESOLVED
        assert MPR.UNREADABLE_CONTRACT in row["partition_error"]

    def test_a_legacy_market_whose_file_is_missing_fails(self, fx):
        fx.register("milwaukee-wi")
        fx.contract("milwaukee-wi", with_block=False)
        assert _code(fx, "milwaukee-wi") == MPR.LEGACY_PARTITION_MISSING

    def test_an_unregistered_market_fails_even_with_a_contract_and_a_file(self, fx):
        fx.partition(MODERN)
        fx.register(MODERN)                       # needed to write the block from the file
        fx.contract(MODERN)
        (fx.markets / (MODERN + ".json")).unlink()
        assert _code(fx, MODERN) == MPR.UNREGISTERED_MARKET
        assert _code(fx, "") == MPR.EMPTY_MARKET_ID

    def test_a_registered_market_without_a_contract_fails(self, fx):
        fx.register(MODERN)
        fx.partition(MODERN)
        assert _code(fx, MODERN) == MPR.NO_RELEASE_CONTRACT

    def test_a_contract_for_another_market_is_never_read_as_this_ones(self, fx):
        fx.register(MODERN)
        fx.partition(MODERN)
        doc = fx.contract(MODERN)
        doc["market_id"] = "harbor-town-qq"
        _write(fx.contracts / (MODERN + ".json"), doc)
        assert _code(fx, MODERN) == MPR.NO_RELEASE_CONTRACT


# --------------------------------------------------------------------------- #
# The contract side: the block is derived, verified, and shaped for the proof.
# --------------------------------------------------------------------------- #

class TestTheContractBlock:
    def test_the_block_is_written_from_the_committed_file(self, fx):
        fx.register(MODERN)
        path = fx.partition(MODERN, count=3)
        block = RC.final_partition_block(MODERN)
        assert list(block) == ["path", "schema", "expected_sha256", "expected_count", "note"]
        assert block["path"] == "launch_packages/pettripfinder/westlake_xx_final_partition_001.json"
        assert block["schema"] == "ptf-market-final-partition/1.1"
        assert block["expected_sha256"] == MPR.content_sha256(path.read_bytes())
        assert block["expected_count"] == 3
        assert "rather than from a table in its own source" in block["note"]

    def test_the_digest_ignores_checkout_line_endings(self, fx):
        fx.register(MODERN)
        path = fx.partition(MODERN)
        lf = path.read_bytes().replace(b"\r\n", b"\n")
        assert MPR.content_sha256(lf) == MPR.content_sha256(lf.replace(b"\n", b"\r\n"))
        assert MPR.content_sha256(b"\xef\xbb\xbf" + lf) == MPR.content_sha256(lf)

    def test_disagreements_are_empty_for_a_legacy_contract_and_named_for_a_drifted_one(self, fx):
        fx.register(MODERN)
        fx.partition(MODERN)
        assert RC.final_partition_disagreements({"market_id": MODERN}, MODERN) == []
        doc = fx.contract(MODERN)
        assert RC.final_partition_disagreements(doc, MODERN) == []
        doc["final_partition"]["expected_count"] = 4
        assert any("expected_count" in p for p in RC.final_partition_disagreements(doc, MODERN))
        doc["final_partition"]["path"] = "launch_packages/pettripfinder/nope.json"
        assert RC.final_partition_disagreements(doc, MODERN) == ["final_partition.path missing: launch_packages/pettripfinder/nope.json"]

    def test_the_registration_proof_accepts_the_block_in_its_place_and_nowhere_else(self, fx):
        fx.register(MODERN)
        fx.partition(MODERN)
        base = {"nashville-tn": (REAL_CONTRACTS / "nashville-tn.json").read_bytes()}
        doc = fx.contract(MODERN)
        problems = RD.check_release_contract(json.dumps(doc).encode("utf-8"), MODERN, base)
        shape = [p for p in _problems(problems) if "registration shape" in p or "final_partition" in p]
        assert shape == [], problems
        assert RD.contract_key_order(doc) == list(doc)
        misplaced = fx.contract(MODERN, position="routes")
        problems = RD.check_release_contract(json.dumps(misplaced).encode("utf-8"), MODERN, base)
        assert any("registration shape" in p for p in _problems(problems))
        wrong_role = fx.contract(MODERN, OrderedDict((
            ("path", "launch_packages/pettripfinder/other_final_partition_001.json"),
            ("schema", "x"), ("expected_sha256", "0" * 64), ("expected_count", 1), ("note", ""))))
        problems = RD.check_release_contract(json.dumps(wrong_role).encode("utf-8"), MODERN, base)
        assert any("final_partition.path" in p for p in _problems(problems))
        extra = fx.contract(MODERN)
        extra["final_partition"]["glob"] = "*"
        problems = RD.check_release_contract(json.dumps(extra).encode("utf-8"), MODERN, base)
        assert any("final_partition carries unknown" in p for p in _problems(problems))
        without = fx.contract(MODERN, with_block=False)
        problems = RD.check_release_contract(json.dumps(without).encode("utf-8"), MODERN, base)
        assert not [p for p in _problems(problems) if "final_partition" in p]

    def test_the_committed_registration_contract_document_states_the_optional_key(self):
        doc = RD.contract_document()
        rows = [r for r in doc["field_level_eligibility_matrix"]
                if r["document"] == "deploy/netlify/release_contracts/<new>.json"
                and r["field"].startswith("final_partition")]
        assert rows and all(r["policy"] == RD.FIELD_DERIVED for r in rows)
        committed = _json(REAL_PKG / "registration_data_only_contract.json")
        assert committed["field_level_eligibility_matrix"] == doc["field_level_eligibility_matrix"]


# --------------------------------------------------------------------------- #
# The staged-build path: no constant of its own to forget.
# --------------------------------------------------------------------------- #

class TestUnderAStagingOverlay:
    def test_the_resolver_follows_a_staging_tree_with_no_patch_entry(self, tmp_path):
        """package_staging redirects every path constant on the build path at a
        staging tree. The resolver holds no such constant: it derives its
        package directory from release_contracts.REPO_ROOT at call time, which
        the overlay already redirects. A market therefore resolves to the
        STAGED partition, and the default is restored on exit."""
        import shutil
        from scripts.pettripfinder import package_staging as PS

        stage = tmp_path / "stage"
        lp = stage / "launch_packages" / "pettripfinder"
        (lp / "markets").mkdir(parents=True)
        (stage / "deploy" / "netlify" / "release_contracts").mkdir(parents=True)
        market, partition = "nashville-tn", "nashville_tn_final_partition_001.json"
        shutil.copyfile(REAL_PKG / "markets" / ("%s.json" % market), lp / "markets" / ("%s.json" % market))
        shutil.copyfile(REAL_PKG / partition, lp / partition)
        shutil.copyfile(REAL_CONTRACTS / ("%s.json" % market),
                        stage / "deploy" / "netlify" / "release_contracts" / ("%s.json" % market))

        outside = MPR.default_package_dir()
        assert outside == REAL_PKG
        MPR._CACHE.clear()
        with PS.overlay(stage):
            assert MPR.default_package_dir() == lp
            res = MPR.resolve_registered_market_partition(market)
            assert res.name == partition
            assert res.path == lp / partition          # the STAGED file, not the committed one
        MPR._CACHE.clear()
        assert MPR.default_package_dir() == outside

    def test_the_staged_build_path_never_loads_the_resolver(self):
        """The assembler imports this module inside the one function that
        resolves a partition, so a staged per-market build -- which imports the
        assembler but never selects markets -- does not load it. That is what
        keeps the resolver out of bundle_cache_closure.code_modules, and an
        undeclared load would publish every staged bundle UNTRUSTED."""
        import ast
        import importlib
        import sys as _sys
        from scripts.pettripfinder import package_staging as PS

        tree = ast.parse(Path(gasm.__file__).read_text(encoding="utf-8"))
        top_level = {a.name for n in tree.body if isinstance(n, ast.Import) for a in n.names}
        top_level |= {n.module for n in tree.body if isinstance(n, ast.ImportFrom) and n.module}
        top_level |= {"%s.%s" % (n.module, a.name) for n in tree.body
                      if isinstance(n, ast.ImportFrom) and n.module for a in n.names}
        assert "scripts.pettripfinder.market_partition_resolution" not in top_level

        loaded = set(_sys.modules)
        for module_name, _attr, _value in PS._patch_targets(Path("C:/nonexistent-stage")):
            importlib.import_module(module_name)
        assert "scripts.pettripfinder.market_partition_resolution" not in (set(_sys.modules) - loaded)

    def test_the_committed_closure_declares_no_partition_resolver(self):
        closure = _json(REAL_PKG / "bundle_cache_closure.json")
        assert "scripts/pettripfinder/assemble_production_site.py" in closure["code_modules"]
        assert "scripts/pettripfinder/market_partition_resolution.py" not in closure["code_modules"]


# --------------------------------------------------------------------------- #
# Performance: the generic resolution is negligible.
# --------------------------------------------------------------------------- #

class TestPerformance:
    def test_fifteen_markets_resolve_in_well_under_a_second_cold_and_milliseconds_warm(self):
        ids = [m.market_id for m in load_markets()]
        MPR._CACHE.clear()
        t = time.perf_counter()
        report = MPR.resolution_report(ids)
        cold = time.perf_counter() - t
        t = time.perf_counter()
        for _ in range(3):
            MPR.resolution_report(ids)
        warm = (time.perf_counter() - t) / 3
        assert report["counts"][MPR.SOURCE_UNRESOLVED] == 0
        assert cold < 1.0, cold
        assert warm < 0.25, warm
