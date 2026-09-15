"""PTF-TAMPA-FL-PARALLEL-SOURCE-READY-001 -- 15 applicable FAST checks for the tampa-fl shadow package.

No generic FAST / sealed-release lane exists at this branch's base (main @ c236f52d).
These checks are built from the contract validators that DO exist here
(``contracts.census``, ``contracts.partition``, ``contracts.identity_key``,
``identity_routing``, ``hotel_exclusions``, ``markets.contract``,
``market_authority``) plus Tampa-specific evidence and lodging-category
safety checks. Nothing shared is modified.

Modeled on orlando_fl_fast_checks_001.py (worker/ptf-orlando-fl-market-001).

Run:
    python -m scripts.pettripfinder.tampa_fl_fast_checks_001 [--skip-rebuild]
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import hotel_exclusions as HE  # noqa: E402
from scripts.pettripfinder import identity_routing as IR  # noqa: E402
from scripts.pettripfinder import market_authority as MA  # noqa: E402
from scripts.pettripfinder.contracts import census as CENSUS  # noqa: E402
from scripts.pettripfinder.contracts import enums  # noqa: E402
from scripts.pettripfinder.contracts import partition as PART  # noqa: E402
from scripts.pettripfinder.contracts.identity_key import key_collisions  # noqa: E402
from scripts.pettripfinder.markets import contract as MARKETS  # noqa: E402
from scripts.pettripfinder.tampa_fl_market_build_001 import MARKET_ID, REPORTS_REL, STAGING_REL  # noqa: E402
from scripts.pettripfinder import tampa_fl_policy_evidence_001 as EV  # noqa: E402

LP = STAGING_REL / "launch_package"
OUTPUTS = [
    LP / "identity_census" / "tampa-fl.json",
    LP / "tampa_fl_final_partition_001.json",
    LP / "markets" / "tampa-fl.json",
    LP / "markets" / "authority" / "tampa-fl" / "identity_routing.json",
    LP / "markets" / "authority" / "tampa-fl" / "hotel_exclusions.json",
    LP / "markets" / "authority" / "tampa-fl" / "seed_businesses.csv",
    LP / "tampa_fl_policy_evidence_ledger_001.json",
    STAGING_REL / "tampa_fl_identity_resolution_001.json",
    REPORTS_REL / "tampa_fl_source_ready_accounting_001.json",
]
RESULTS = []


def _load(rel):
    return json.loads((_REPO_ROOT / rel).read_text(encoding="utf-8"))


def check(n, name, fn):
    try:
        detail = fn()
        RESULTS.append((n, name, "PASS", detail or ""))
    except AssertionError as exc:
        RESULTS.append((n, name, "FAIL", str(exc)[:600]))
    except Exception as exc:  # noqa: BLE001
        RESULTS.append((n, name, "FAIL", "%s: %s" % (type(exc).__name__, str(exc)[:600])))


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    census_doc = _load(OUTPUTS[0])
    partition_doc = _load(OUTPUTS[1])
    market_doc = _load(OUTPUTS[2])
    routing_doc = _load(OUTPUTS[3])
    exclusions_doc = _load(OUTPUTS[4])
    ledger = _load(OUTPUTS[6])
    accounting = _load(OUTPUTS[8])
    items = {i["identity_key"]: i for i in partition_doc["items"]}

    def c1():
        issues = CENSUS.validate(census_doc, market_states=("FL",))
        assert not issues, issues[:5]
        return "%d rows" % len(census_doc["hotels"])

    def c2():
        issues = PART.validate(partition_doc)
        assert not issues, issues[:5]

    def c3():
        rec = PART.reconcile(CENSUS.identity_keys(census_doc), partition_doc, market_id=MARKET_ID)
        issues = PART.reconciliation_issues(rec)
        assert not issues, issues[:5]
        return "published %d / no-pets %d / unresolved %d" % (rec.published, rec.verified_no_pets, rec.unresolved)

    def c4():
        collisions = key_collisions([r["canonical_name"] for r in census_doc["hotels"]])
        assert not collisions, collisions

    def c5():
        assert IR.validate_authority(routing_doc) == []
        assert routing_doc["routes"] == [] and routing_doc["market_id"] == MARKET_ID

    def c6():
        assert HE.validate(exclusions_doc) == []
        assert exclusions_doc["exclusions"] == [] and exclusions_doc["market_id"] == MARKET_ID

    def c7():
        MARKETS.parse_market(market_doc, source=str(OUTPUTS[2]))
        return "%d corridors" % len(market_doc["corridors"])

    def c8():
        bad = [r["identity_key"] for r in census_doc["hotels"] if r["state"] != "FL" or r["geography_class"] not in ("CORE", "CORRIDOR", "FRINGE")]
        assert not bad, bad[:10]

    def c9():
        slugs = {r["identity_key"]: r for r in census_doc["hotels"]}
        by = {}
        for r in census_doc["hotels"]:
            if not r["corridor"]:
                assert items[r["identity_key"]]["final_state"] == enums.AWAITING_CENSUS_REVIEW, ("unassigned corridor not held", r["identity_key"])
                continue
            by.setdefault(r["corridor"], set()).add(r["identity_key"])
        for c in market_doc["corridors"]:
            assert set(c["explicit_hotel_ids"]) == by.get(c["slug"], set()), ("explicit ids drift", c["slug"])
            assert all(s in slugs for s in c["explicit_hotel_ids"])
            assert c["show_in_navigation"] is False and c["show_in_sitemap"] is False
        eligible = [k for k, v in accounting["corridor_pages"].items() if v["page_eligible"]]
        return "page-eligible corridors (PF >= 5): %d / %d" % (len(eligible), len(market_doc["corridors"]))

    def c10():
        assert MARKET_ID not in MA.sharded_market_ids()
        live = _REPO_ROOT / "launch_packages" / "pettripfinder" / "markets"
        assert not (live / "tampa-fl.json").exists()
        assert not (live / "authority" / "tampa-fl").exists()

    def c11():
        drift = MA.check_generated_artifacts()
        assert drift == [], drift

    def c12():
        if "--skip-rebuild" in argv:
            return "SKIPPED by flag"
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ)
            env["PYTHONIOENCODING"] = "utf-8"
            subprocess.run([sys.executable, "-m", "scripts.pettripfinder.tampa_fl_market_build_001", "--out-root", tmp],
                           cwd=str(_REPO_ROOT), check=True, capture_output=True, env=env)
            diffs = []
            for rel in OUTPUTS:
                a = hashlib.sha256((_REPO_ROOT / rel).read_bytes()).hexdigest()
                b = hashlib.sha256((Path(tmp) / rel).read_bytes()).hexdigest()
                if a != b:
                    diffs.append(str(rel))
            assert not diffs, diffs
        return "%d outputs byte-identical in an independent process" % len(OUTPUTS)

    def c13():
        out = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=str(_REPO_ROOT), check=True, capture_output=True, text=True).stdout
        bad = []
        for line in out.splitlines():
            path = line[3:].strip().strip('"')
            if path.startswith("atlas-dashboard/"):
                path = path[len("atlas-dashboard/"):]
            ok = (path.startswith("launch_packages/pettripfinder/markets/staging/tampa-fl/")
                  or path.startswith("launch_packages/pettripfinder/markets/reports/tampa_fl_")
                  or path.startswith("scripts/pettripfinder/tampa_fl_")
                  or path.startswith("../PTF-TAMPA-FL-") or path.startswith("PTF-TAMPA-FL-"))
            if not ok or line[:2].strip() not in ("??", "A", "M", "AM"):
                bad.append(line)
            if line[:2].strip() == "M" and "tampa" not in path:
                bad.append(line)
        assert not bad, bad[:10]

    def c14():
        pages = EV.load_pages()
        by_key = {}
        for row in ledger["rows"]:
            by_key.setdefault(row["identity_key"], []).append(row)
            rec = pages[row["requested_url"]]
            assert hashlib.sha256(rec["body"].encode("utf-8")).hexdigest() == row["content_sha256_utf8"]
            assert row["byte_length_utf8"] == len(rec["body"].encode("utf-8"))
            for f in ("requested_url", "final_url", "capture_lane", "capture_timestamp", "durable_content_reference", "decision"):
                assert row.get(f) is not None or f == "final_url", (f, row["requested_url"])
            assert "paid" not in row["capture_lane"]
        for key, item in items.items():
            rows = by_key.get(key, [])
            if item["final_state"] == enums.PUBLISHED_PET_FRIENDLY:
                ok = [r for r in rows if r["decision"] == "PET_FRIENDLY" and r.get("operative_quote") and r.get("acceptance", {}).get("value") == "true"]
                assert ok, ("published without operative first-party acceptance", key)
                assert not [r for r in rows if r["decision"] in ("NO_PETS", "EVIDENCE_HOLD")], ("published over a conflicting page", key)
            if item["final_state"] == enums.VERIFIED_NO_PETS:
                ok = [r for r in rows if r["decision"] == "NO_PETS" and r.get("acceptance", {}).get("value") == "false"]
                assert ok, ("no-pets without explicit refusal", key)
        with gzip.open(_REPO_ROOT / STAGING_REL / "raw_captures" / "evidence_pages_001.jsonl.gz", "rt", encoding="utf-8") as fh:
            n = sum(1 for _ in fh)
        assert accounting["evidence"]["usd_spent"] == 0 and accounting["evidence"]["paid_provider_calls"] == 0
        return "%d evidence rows over %d stored pages re-hashed" % (len(ledger["rows"]), n)

    def c15():
        for r in census_doc["hotels"]:
            ranks = {l["rank_code"] for l in r["dbpr_licences"]}
            state = items[r["identity_key"]]["final_state"]
            if r["lodging_class"] == "HOTEL":
                assert ranks & {"HOTL", "MOTL"}, ("hotel row without HOTL/MOTL licence", r["identity_key"])
                assert r["lodging_state"] == enums.LODGING_CONFIRMED
            else:
                assert r["lodging_class"] == "MIXED_RESORT_HOLD" and r["lodging_state"] == enums.LODGING_NEEDS_REVIEW and state == enums.AWAITING_CENSUS_REVIEW, r["identity_key"]
            assert not (ranks and ranks <= {"TAPT", "BNB", "CNDO", "DWEL", "NAPT"}), ("unit/non-hotel licence admitted", r["identity_key"])
            assert r["market_id"] == MARKET_ID
        for doc in (partition_doc, market_doc, routing_doc, exclusions_doc, accounting):
            assert doc["market_id"] == MARKET_ID
        assert accounting["reconciles"] is True
        return "0 timeshare / vacation-rental / resort-residence / unit identities admitted"

    check(1, "census.validate (FL-only)", c1)
    check(2, "partition.validate", c2)
    check(3, "partition.reconcile == census identity keys", c3)
    check(4, "identity_key.key_collisions empty", c4)
    check(5, "identity_routing.validate_authority (shadow shard)", c5)
    check(6, "hotel_exclusions.validate (shadow shard)", c6)
    check(7, "markets.contract.parse_market (staged config)", c7)
    check(8, "zero non-FL / OUTSIDE rows in census", c8)
    check(9, "corridor assignment complete; explicit ids == census; nothing navigable", c9)
    check(10, "tampa-fl absent from LIVE registry and sharded_market_ids()", c10)
    check(11, "zero drift in LIVE generated global artifacts", c11)
    check(12, "byte-reproducible rebuild in an independent process", c12)
    check(13, "git status touches only tampa-owned paths", c13)
    check(14, "evidence integrity: every terminal row backed by a re-hashed durable first-party page", c14)
    check(15, "lodging safety: no unit/timeshare/vacation rental admitted; accounting reconciles", c15)
    passed = sum(1 for r in RESULTS if r[2] == "PASS")
    for n, name, status, detail in RESULTS:
        print("%2d. [%s] %s%s" % (n, status, name, ("  -- " + detail) if detail else ""))
    print("\n%d / %d PASS" % (passed, len(RESULTS)))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
