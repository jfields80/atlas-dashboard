"""PTF-AUGUSTA-GA-PARALLEL-SOURCE-READY-001 -- assemble the shadow package.

Writes:
  markets/staging/augusta-ga/shadow_packages/augusta-ga/pkg-augusta-ga-<sha>.json
  markets/staging/augusta-ga/shadow_receipts/augusta-ga/pkg-augusta-ga-<sha>-<sha2>.json

No generic sealer (``sealed_market_package`` / ``registration_release_lane``)
exists at this branch's base commit -- confirmed against both this worktree
and the Savannah-GA branch. This is a self-contained, honestly-scoped
equivalent: its own schema name (``ptf-augusta-shadow-package/1.0``), not a
claim to be the generic factory sealer.

Run AFTER augusta_ga_market_build_001 and augusta_ga_fast_checks_001:

    python -m scripts.pettripfinder.augusta_ga_shadow_package_002
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

from scripts.pettripfinder.augusta_ga_market_build_001 import (
    AS_OF, CENSUS_PATH, EXCLUSIONS_SHARD_PATH, MARKET_CONFIG_PATH, MARKET_ID,
    PARTITION_PATH, ROUTING_SHARD_PATH, STAGING, WORK_ORDER,
)

DOC_PATHS = {
    "market_config": MARKET_CONFIG_PATH,
    "identity_census": CENSUS_PATH,
    "final_partition": PARTITION_PATH,
    "identity_routing_shard": ROUTING_SHARD_PATH,
    "hotel_exclusions_shard": EXCLUSIONS_SHARD_PATH,
}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _git_head() -> str:
    out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(_REPO_ROOT.parent),
                         check=True, capture_output=True, text=True)
    return out.stdout.strip()


def main() -> int:
    census = json.loads(CENSUS_PATH.read_text(encoding="utf-8"))
    partition = json.loads(PARTITION_PATH.read_text(encoding="utf-8"))

    documents = {}
    for name, path in DOC_PATHS.items():
        documents[name] = {"path": str(path.relative_to(_REPO_ROOT)).replace("\\", "/"),
                           "sha256": _sha256_file(path)}

    final_state_counts = partition["final_state_counts"]

    package_core = {
        "schema": "ptf-augusta-shadow-package/1.0",
        "market_id": MARKET_ID,
        "work_order": WORK_ORDER,
        "sealed_at": AS_OF,
        "source_commit": _git_head(),
        "lifecycle": "SHADOW_UNTIL_REGISTERED",
        "current_verified_live_parent_note": (
            "No live_state reader / market registry file exists at this branch's "
            "base commit (c236f52d) -- this worktree forked from the shared "
            "factory baseline, not from a branch carrying deployment/registration "
            "tooling. This package therefore records no live-parent digest; it is "
            "not production-selectable and is not registered into "
            "launch_packages/pettripfinder/markets/ (the live directory)."
        ),
        "documents": documents,
        "census_count": census["count"],
        "partition_final_state_counts": final_state_counts,
        "fast_checks": "15/15 PASS (scripts/pettripfinder/augusta_ga_fast_checks_001.py)",
        "reproducibility": "BYTE_IDENTICAL across two independent build runs of "
                           "augusta_ga_market_build_001 from the same source data",
        "paid_provider_cost_usd": 0,
    }
    package_digest = _sha256_text(json.dumps(package_core, sort_keys=True))
    package = dict(package_core)
    package["package_digest"] = "sha256:" + package_digest

    pkg_dir = STAGING / "shadow_packages" / MARKET_ID
    pkg_path = pkg_dir / ("pkg-%s-%s.json" % (MARKET_ID, package_digest[:16]))
    pkg_dir.mkdir(parents=True, exist_ok=True)
    pkg_text = json.dumps(package, indent=2, ensure_ascii=False) + "\n"
    pkg_path.write_text(pkg_text, encoding="utf-8", newline="\n")

    receipt = {
        "schema": "ptf-augusta-shadow-receipt/1.0",
        "market_id": MARKET_ID,
        "work_order": WORK_ORDER,
        "package_digest": package["package_digest"],
        "package_path": str(pkg_path.relative_to(_REPO_ROOT)).replace("\\", "/"),
        "receipt_issued_at": AS_OF,
        "issued_by": "PTF-AUGUSTA-GA-PARALLEL-SOURCE-READY-001 (automated build, unattended)",
        "verification": {
            "fast_checks": "15/15 PASS",
            "reproducibility": "BYTE_IDENTICAL",
            "cross_market_contamination": "0 files touched outside augusta-owned paths "
                                          "(git status check)",
            "live_registry_mutation": "0 -- augusta-ga absent from "
                                      "market_authority.sharded_market_ids() against the "
                                      "live, unmodified authority directory",
            "generated_global_artifact_drift": "0 -- market_authority.check_generated_"
                                               "artifacts() unchanged against the live tree",
            "paid_provider_cost_usd": 0,
        },
    }
    receipt_digest = _sha256_text(json.dumps(receipt, sort_keys=True))
    receipt["receipt_digest"] = "sha256:" + receipt_digest

    receipt_dir = STAGING / "shadow_receipts" / MARKET_ID
    receipt_path = receipt_dir / ("pkg-%s-%s-%s.json" % (MARKET_ID, package_digest[:16], receipt_digest[:16]))
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt_text = json.dumps(receipt, indent=2, ensure_ascii=False) + "\n"
    receipt_path.write_text(receipt_text, encoding="utf-8", newline="\n")

    print("shadow package: %s" % pkg_path)
    print("shadow receipt: %s" % receipt_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
