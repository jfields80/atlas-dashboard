"""PTF-AUGUSTA-GA-PARALLEL-SOURCE-READY-001 -- 15 FAST-equivalent checks.

No generic ``FAST``/sealed-release-lane module exists at this branch's base
commit (c236f52d) -- confirmed by grep across this worktree and the
Savannah-GA market branch. These 15 checks are built directly from the
contract validators that DO exist here (``contracts.census``,
``contracts.partition``, ``identity_routing``, ``hotel_exclusions``,
``markets.contract``, ``market_authority``), covering the same ground a
generic FAST lane would: schema validity, cross-document reconciliation,
zero cross-market/geography leakage, and reproducibility.

Run:

    python -m scripts.pettripfinder.augusta_ga_fast_checks_001
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import hotel_exclusions as HE
from scripts.pettripfinder import identity_routing as IR
from scripts.pettripfinder import market_authority as MA
from scripts.pettripfinder.augusta_ga_market_build_001 import (
    CENSUS_PATH, EXCLUSIONS_SHARD_PATH, MARKET_CONFIG_PATH, MARKET_ID,
    PARTITION_PATH, ROUTING_SHARD_PATH,
)
from scripts.pettripfinder.contracts import census as CENSUS
from scripts.pettripfinder.contracts import partition as PART
from scripts.pettripfinder.contracts.identity_key import key_collisions
from scripts.pettripfinder.markets import contract as MARKETS


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


RESULTS = []


def check(n, name, fn):
    try:
        fn()
        RESULTS.append((n, name, "PASS", ""))
    except AssertionError as exc:
        RESULTS.append((n, name, "FAIL", str(exc)))
    except Exception as exc:  # noqa: BLE001
        RESULTS.append((n, name, "FAIL", "%s: %s" % (type(exc).__name__, exc)))


def main() -> int:
    census_doc = _load(CENSUS_PATH)
    partition_doc = _load(PARTITION_PATH)
    market_doc = _load(MARKET_CONFIG_PATH)
    routing_doc = _load(ROUTING_SHARD_PATH)
    exclusions_doc = _load(EXCLUSIONS_SHARD_PATH)

    def c1():
        issues = CENSUS.validate(census_doc, market_states=("GA",))
        assert not issues, issues

    def c2():
        issues = PART.validate(partition_doc)
        assert not issues, issues

    def c3():
        rec = PART.reconcile(CENSUS.identity_keys(census_doc), partition_doc, market_id=MARKET_ID)
        assert not PART.reconciliation_issues(rec), rec

    def c4():
        names = [r["canonical_name"] for r in census_doc["hotels"]]
        collisions = key_collisions(names)
        assert not collisions, collisions

    def c5():
        records = IR.validate_authority(routing_doc)
        assert records == []
        for r in routing_doc["routes"]:
            assert r.get("market_id") == MARKET_ID

    def c6():
        records = HE.validate(exclusions_doc)
        assert records == []
        for r in exclusions_doc["exclusions"]:
            assert r.get("record_hash") == HE.record_hash(r)
            assert r.get("approval_hash") == HE.approval_hash(r)

    def c7():
        MARKETS.parse_market(market_doc, source=str(MARKET_CONFIG_PATH))

    def c8():
        bad = [r["state"] for r in census_doc["hotels"] if r["state"] != "GA"]
        assert not bad, bad

    def c9():
        by_corridor = {}
        for r in census_doc["hotels"]:
            by_corridor.setdefault(r["corridor"], 0)
            by_corridor[r["corridor"]] += 1
        for corridor in market_doc["corridors"]:
            slug = corridor["slug"]
            n = by_corridor.get(slug, 0)
            assert n >= corridor["minimum_hotel_count"], (slug, n, corridor["minimum_hotel_count"])
            assert n >= 1, slug

    def c10():
        live_ids = MA.sharded_market_ids()
        assert MARKET_ID not in live_ids, live_ids

    def c11():
        drift = MA.check_generated_artifacts()
        assert drift == [], drift

    def c12():
        import hashlib
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            env_paths = [CENSUS_PATH, PARTITION_PATH, MARKET_CONFIG_PATH,
                        ROUTING_SHARD_PATH, EXCLUSIONS_SHARD_PATH]
            before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in env_paths}
            subprocess.run([sys.executable, "-m",
                           "scripts.pettripfinder.augusta_ga_market_build_001"],
                          cwd=str(_REPO_ROOT), check=True, capture_output=True)
            after = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in env_paths}
            assert before == after, {str(p): (before[p], after[p]) for p in env_paths if before[p] != after[p]}

    def c13():
        import subprocess
        out = subprocess.run(["git", "status", "--short", "--untracked-files=all"],
                             cwd=str(_REPO_ROOT), check=True, capture_output=True, text=True).stdout
        allowed_prefixes = (
            "launch_packages/pettripfinder/markets/staging/",
            "launch_packages/pettripfinder/markets/reports/augusta_ga_",
            "scripts/pettripfinder/augusta_ga_",
        )
        bad = []
        for line in out.splitlines():
            path = line[3:].strip()
            if "augusta" in path.lower() or path.upper().startswith("PTF-AUGUSTA"):
                continue
            if any(path.startswith(p) for p in allowed_prefixes):
                continue
            bad.append(line)
        assert not bad, bad

    def c14():
        for r in census_doc["hotels"]:
            assert r["policy_state"] in (enums_module.POLICY_NOT_VERIFIED,), r["identity_key"]
        terminal = [i for i in partition_doc["items"]
                   if i["final_state"] in ("PUBLISHED_PET_FRIENDLY", "VERIFIED_NO_PETS")]
        assert not terminal, terminal

    def c15():
        assert routing_doc["market_id"] == MARKET_ID
        assert exclusions_doc["market_id"] == MARKET_ID
        assert census_doc["market_id"] == MARKET_ID
        assert partition_doc["market_id"] == MARKET_ID
        assert market_doc["market_id"] == MARKET_ID

    from scripts.pettripfinder.contracts import enums as enums_module

    check(1, "census.validate (GA-only)", c1)
    check(2, "partition.validate", c2)
    check(3, "partition.reconcile == census identity keys", c3)
    check(4, "identity_key.key_collisions empty", c4)
    check(5, "identity_routing.validate_authority (shard)", c5)
    check(6, "hotel_exclusions.validate + hash re-derivation (shard)", c6)
    check(7, "markets.contract.parse_market (staged config)", c7)
    check(8, "zero non-GA census rows", c8)
    check(9, "every corridor meets its own minimum_hotel_count", c9)
    check(10, "augusta-ga absent from LIVE sharded_market_ids()", c10)
    check(11, "zero drift in LIVE generated global artifacts", c11)
    check(12, "byte-reproducible rebuild (2nd run matches 1st)", c12)
    check(13, "git status touches only augusta-owned paths", c13)
    check(14, "zero fabricated policy facts (all POLICY_NOT_VERIFIED, zero terminal partition rows)", c14)
    check(15, "market_id consistent across all 5 documents", c15)

    passed = sum(1 for _, _, s, _ in RESULTS if s == "PASS")
    for n, name, status, detail in RESULTS:
        line = "%2d. [%s] %s" % (n, status, name)
        if detail:
            line += "  -- %s" % detail
        print(line)
    print("\n%d / %d PASS" % (passed, len(RESULTS)))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
