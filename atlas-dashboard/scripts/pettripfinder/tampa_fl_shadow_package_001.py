"""PTF-TAMPA-FL-PARALLEL-SOURCE-READY-001 -- assemble the tampa-fl SHADOW_UNTIL_REGISTERED package + receipt.

Own schema names (``ptf-tampa-fl-shadow-package/1.0``): no generic sealer exists
at this branch's base. The package digest is the sha256 of the canonical JSON of
the file manifest (path + sha256 + bytes), so it is independent of wall clock and
machine. Written only under the Tampa staging tree.

Modeled on orlando_fl_shadow_package_001.py (worker/ptf-orlando-fl-market-001).

Run:
    python -m scripts.pettripfinder.tampa_fl_shadow_package_001 <fast_result_json>
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.tampa_fl_market_build_001 import AS_OF, MARKET_ID, REPORTS_REL, STAGING_REL, WORK_ORDER  # noqa: E402

INPUTS = sorted([
    STAGING_REL / "raw_captures" / "dbpr_lodging_inscope_001.json", STAGING_REL / "raw_captures" / "osm_overpass_lodging_001.json",
    STAGING_REL / "raw_captures" / "visittampabay_hotels_001.json", STAGING_REL / "raw_captures" / "visitstpeteclearwater_hotels_001.json",
    STAGING_REL / "raw_captures" / "hilton_inventory_001.json", STAGING_REL / "raw_captures" / "marriott_owned_harvest_codes_001.json",
    STAGING_REL / "raw_captures" / "evidence_pages_001.jsonl.gz", STAGING_REL / "raw_captures" / "lane_attempts_001.json",
], key=str)
CODE = sorted([Path("scripts") / "pettripfinder" / n for n in (
    "tampa_fl_identity_rules_001.py", "tampa_fl_policy_evidence_001.py", "tampa_fl_market_build_001.py",
    "tampa_fl_fast_checks_001.py", "tampa_fl_shadow_package_001.py")], key=str)
OUTPUTS = sorted([
    STAGING_REL / "launch_package" / "identity_census" / "tampa-fl.json", STAGING_REL / "launch_package" / "tampa_fl_final_partition_001.json",
    STAGING_REL / "launch_package" / "markets" / "tampa-fl.json", STAGING_REL / "launch_package" / "markets" / "authority" / "tampa-fl" / "identity_routing.json",
    STAGING_REL / "launch_package" / "markets" / "authority" / "tampa-fl" / "hotel_exclusions.json",
    STAGING_REL / "launch_package" / "markets" / "authority" / "tampa-fl" / "seed_businesses.csv",
    STAGING_REL / "launch_package" / "tampa_fl_policy_evidence_ledger_001.json", STAGING_REL / "tampa_fl_identity_resolution_001.json",
    REPORTS_REL / "tampa_fl_source_ready_accounting_001.json",
], key=str)


def _entry(rel: Path) -> dict:
    data = (_REPO_ROOT / rel).read_bytes()
    if rel.suffix in (".py", ".json", ".csv"):
        assert b"\r\n" not in data, "CRLF in %s" % rel
    return {"path": rel.as_posix(), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    fast = json.loads(Path(argv[0]).read_text(encoding="utf-8")) if argv else None
    base = subprocess.run(["git", "merge-base", "HEAD", "origin/main"], cwd=str(_REPO_ROOT), capture_output=True, text=True).stdout.strip()
    # CURRENT VERIFIED LIVE at the time this shadow package was assembled (read for
    # context only -- see note below; a later registration order MUST re-read live
    # state before this parent is trusted, since new markets go live continuously).
    parent = subprocess.run(["git", "rev-parse", "worker/ptf-savannah-ga-market-001"], cwd=str(_REPO_ROOT), capture_output=True, text=True).stdout.strip()
    manifest = {"inputs": [_entry(p) for p in INPUTS], "code": [_entry(p) for p in CODE], "outputs": [_entry(p) for p in OUTPUTS]}
    canon = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(canon).hexdigest()
    accounting = json.loads((_REPO_ROOT / REPORTS_REL / "tampa_fl_source_ready_accounting_001.json").read_text(encoding="utf-8"))
    package = {
        "schema": "ptf-tampa-fl-shadow-package/1.0", "market_id": MARKET_ID, "work_order": WORK_ORDER, "as_of": AS_OF,
        "lifecycle": "SHADOW_UNTIL_REGISTERED", "production_selectable": False,
        "source_commit_base": base,
        "current_live_parent_context": {"read_for_context_only": True, "ref": "worker/ptf-savannah-ga-market-001", "commit": parent,
                                        "note": "Latest verified live launch known to this fleet at package-assembly time (Savannah, FL launch 003, 27/1802/2081). No CURRENT VERIFIED LIVE reader exists at this base; a release order MUST re-read live state and invalidate this parent before registering Tampa."},
        "package_digest_sha256": digest, "manifest": manifest,
        "summary": {k: accounting[k] for k in ("TOTAL_DISCOVERED", "PROPOSED_CENSUS", "VALID_PET_FRIENDLY", "VALID_VERIFIED_NO_PETS", "RESOLVED", "UNRESOLVED")},
        "registration_required_before_release": ["register tampa-fl market config", "authority shards + build_global_authority --write/--check",
                                                 "participation + release contracts", "fresh reseal against then-current live", "FAST", "candidate", "independent reproduction", "founder packet"],
    }
    pkg_rel = STAGING_REL / "shadow_packages" / ("pkg-tampa-fl-%s.json" % digest[:16])
    (_REPO_ROOT / pkg_rel).parent.mkdir(parents=True, exist_ok=True)
    pkg_bytes = (json.dumps(package, indent=1, ensure_ascii=False) + "\n").encode("utf-8")
    (_REPO_ROOT / pkg_rel).write_bytes(pkg_bytes)
    receipt = {"schema": "ptf-tampa-fl-shadow-receipt/1.0", "market_id": MARKET_ID, "work_order": WORK_ORDER, "package": pkg_rel.as_posix(),
               "package_digest_sha256": digest, "package_file_sha256": hashlib.sha256(pkg_bytes).hexdigest(), "lifecycle": "SHADOW_UNTIL_REGISTERED",
               "fast": fast}
    rec_rel = STAGING_REL / "shadow_receipts" / ("pkg-tampa-fl-%s-receipt.json" % digest[:16])
    (_REPO_ROOT / rec_rel).parent.mkdir(parents=True, exist_ok=True)
    (_REPO_ROOT / rec_rel).write_bytes((json.dumps(receipt, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    print("package", pkg_rel.as_posix())
    print("digest ", digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
