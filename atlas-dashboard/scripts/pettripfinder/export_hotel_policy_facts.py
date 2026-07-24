"""PTF-PROD-002A -- explicit exporter for the tracked publishable hotel-policy
facts package.

Reads the approved READY importer candidates from the gitignored operational
corpus (via site_data.load_hotel_policy_facts) and writes the deterministic,
tracked launch package launch_packages/pettripfinder/hotel_policy_facts.json,
which is the DEFAULT source the Columbus generator loads. Running this is the
ONLY step that touches operational data; normal site generation then depends
only on the committed package.

    python scripts/pettripfinder/export_hotel_policy_facts.py [--check]

--check exits non-zero if the tracked package is stale vs the operational corpus
(useful in CI where the corpus is present). No network. Writes only the tracked
package (never inventory, never operational data).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.site_data import (  # noqa: E402
    PUBLISHED_FACTS_PATH,
    load_hotel_policy_facts,
    normalize_name,
    read_production_rows,
)

SCHEMA_VERSION = "1.1"
MARKET = "columbus-oh"


def build_package() -> dict:
    """Deterministic publishable package from the approved READY facts. Exports
    only publishable content -- the supported structured policy fields (already
    filtered to the policy vocabulary by load_hotel_policy_facts), the exact
    evidence quote, verification state/date, and the official source -- never
    operational metadata (candidate paths, run ids, blocked-source internals)
    and never an invented fact."""
    facts = load_hotel_policy_facts()
    display = {normalize_name(r["name"]): r["name"]
               for r in read_production_rows() if r["category"] == "pet-friendly-hotels"}
    hotels = []
    for key in sorted(facts):
        e = facts[key]
        pets_allowed = e["facts"].get("pets_allowed")
        state = "VERIFIED_NO_PETS" if pets_allowed == "false" else "VERIFIED_PET_FRIENDLY"
        record = {
            "key": key,
            "name": display.get(key, ""),
            "verification_state": state,
            "facts": dict(e["facts"]),          # already filtered to the policy vocabulary
            "evidence_quote": e.get("evidence_quote") or "",
            "verified_at": e.get("verified_at", ""),
            "source_url": e.get("source_url", ""),
            "source_type": e.get("source_relationship", ""),
            "evidence_count": e.get("evidence_count", 0),
        }
        _add_worker_provenance(record, e)        # additive schema-1.1 fields (worker records only)
        hotels.append(record)
    return {"schema_version": SCHEMA_VERSION, "market": MARKET, "hotels": hotels}


def _add_worker_provenance(record: dict, entry: dict) -> None:
    """Attach the additive schema-1.1 provenance to a worker-promotion record.
    Importer-sourced records (no worker_provenance) are left untouched -- their
    schema-1.0 fields are preserved and no worker field is fabricated. Every value
    is copied verbatim from the operational corpus candidate; nothing is inferred,
    no fee is flattened, and no credential or raw model output is copied."""
    wp = entry.get("worker_provenance")
    if not wp:
        return
    approval = wp.get("approval", {})
    record["verification_date"] = entry.get("verified_at", "")
    record["worker_result_hash"] = wp.get("result_hash", "")
    record["worker_model_id"] = wp.get("model_id", "")
    record["worker_prompt_version"] = wp.get("prompt_version", "")
    record["worker_validator_version"] = wp.get("validator_version", "")
    record["worker_routing_version"] = wp.get("routing_version", "")
    record["evidence"] = [
        {"field": ev.get("field", ""), "value": ev.get("value", ""),
         "quote": ev.get("quote", ""), "source_url": ev.get("source_url", "")}
        for ev in entry.get("evidence", [])]
    record["approval"] = {
        "decision": approval.get("decision", ""),
        "operator": approval.get("operator", ""),
        "approval_date": approval.get("approval_date", ""),
    }


def serialize(package: dict) -> str:
    return json.dumps(package, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def write_package(path: Path = PUBLISHED_FACTS_PATH) -> int:
    text = serialize(build_package())
    path.write_text(text, encoding="utf-8", newline="\n")
    print("wrote %s (%d hotels)" % (path, len(json.loads(text)["hotels"])))
    return 0


def check(path: Path = PUBLISHED_FACTS_PATH) -> int:
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    expected = serialize(build_package())
    if current != expected:
        print("STALE: %s does not match the operational corpus; re-run without --check" % path)
        return 1
    print("OK: %s is up to date" % path)
    return 0


# --------------------------------------------------------------------------- #
# Zero-write preview (PROD-003 Gate 2 schema 1.1). Builds the full package in
# memory and writes ONLY to a gitignored review directory -- never the committed
# launch package, never a page, never a deployment file.
# --------------------------------------------------------------------------- #

DEFAULT_PREVIEW_DIR = _REPO_ROOT / "data" / "worker_runs" / "pettripfinder" / "prod003_package_preview"


def _sha256_text(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_preview(committed_path: Path = PUBLISHED_FACTS_PATH) -> dict:
    """Build the new package in memory and compare it to the committed package.
    Read-only: writes nothing."""
    old_text = committed_path.read_text(encoding="utf-8") if committed_path.exists() else ""
    old_pkg = json.loads(old_text) if old_text else {"schema_version": "", "hotels": []}
    new_pkg = build_package()
    new_text = serialize(new_pkg)

    old = {h["key"]: h for h in old_pkg.get("hotels", [])}
    new = {h["key"]: h for h in new_pkg["hotels"]}
    additions = sorted(set(new) - set(old))
    removals = sorted(set(old) - set(new))
    updated = []
    for k in sorted(set(old) & set(new)):
        changed = {f: [old[k].get(f), new[k].get(f)]
                   for f in old[k] if old[k].get(f) != new[k].get(f)}
        if changed:
            updated.append({"key": k, "changed": changed})
    worker_records = [h for h in new_pkg["hotels"] if "worker_result_hash" in h]
    missing_prov = [h["key"] for h in worker_records
                    if not (h.get("worker_result_hash") and h.get("evidence") and h.get("approval"))]
    seen, dupes = set(), set()
    for h in new_pkg["hotels"]:
        dupes.add(h["key"]) if h["key"] in seen else seen.add(h["key"])
    report = {
        "schema_version": new_pkg["schema_version"],
        "old_count": len(old),
        "new_count": len(new),
        "additions": additions,
        "additions_count": len(additions),
        "removals": removals,
        "removals_count": len(removals),
        "unintended_updates_to_existing": updated,
        "unintended_updates_count": len(updated),
        "worker_record_count": len(worker_records),
        "worker_provenance_complete_count": len(worker_records) - len(missing_prov),
        "missing_or_unmappable_provenance": sorted(missing_prov),
        "duplicate_keys": sorted(dupes),
        "before_package_sha256": _sha256_text(old_text),
        "after_package_sha256": _sha256_text(new_text),
        "committed_would_become_stale": old_text != new_text,
        "wrote_committed_package": False,
    }
    return {"package": new_pkg, "package_text": new_text, "report": report, "old_pkg": old_pkg}


def render_package_diff(pv: dict) -> str:
    r = pv["report"]
    lines = ["# PROD-003 launch-package preview (schema %s) -- ZERO committed-package write"
             % r["schema_version"], "",
             "- old count: **%d** -> new count: **%d**" % (r["old_count"], r["new_count"]),
             "- additions: **%d** | removals: **%d** | unintended updates to existing: **%d**"
             % (r["additions_count"], r["removals_count"], r["unintended_updates_count"]),
             "- committed package would become stale: **%s**" % r["committed_would_become_stale"],
             "- before sha256: `%s`" % r["before_package_sha256"],
             "- after  sha256: `%s`" % r["after_package_sha256"], "",
             "## Additions (%d)" % r["additions_count"]]
    new_by_key = {h["key"]: h for h in pv["package"]["hotels"]}
    for k in r["additions"]:
        h = new_by_key[k]
        lines.append("### %s" % (h["name"] or k))
        lines.append("- facts: %s" % h["facts"])
        if "worker_result_hash" in h:
            lines.append("- worker_result_hash: `%s`" % h["worker_result_hash"])
            lines.append("- worker versions: model=%s prompt=%s validator=%s routing=%s"
                         % (h["worker_model_id"], h["worker_prompt_version"],
                            h["worker_validator_version"], h["worker_routing_version"]))
            lines.append("- approval: %s" % h["approval"])
            lines.append("- evidence (%d):" % len(h["evidence"]))
            for ev in h["evidence"]:
                lines.append("    - `%s` = `%s`  <- \"%s\"  [%s]"
                             % (ev["field"], ev["value"], ev["quote"], ev["source_url"]))
        lines.append("")
    if r["unintended_updates_to_existing"]:
        lines.append("## UNINTENDED updates to existing records")
        for u in r["unintended_updates_to_existing"]:
            lines.append("- %s: %s" % (u["key"], u["changed"]))
    else:
        lines.append("## Existing records: 0 unintended updates (the five importer records are preserved)")
    return "\n".join(lines) + "\n"


def write_preview(out_dir: Path = DEFAULT_PREVIEW_DIR) -> dict:
    pv = build_preview()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "hotel_policy_facts.preview.json").write_text(pv["package_text"], encoding="utf-8", newline="\n")
    (out_dir / "package_validation_report.json").write_text(
        json.dumps(pv["report"], indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8", newline="\n")
    (out_dir / "package_diff.md").write_text(render_package_diff(pv), encoding="utf-8", newline="\n")
    return pv["report"]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true",
                   help="verify the tracked package matches the operational corpus (no write)")
    p.add_argument("--preview", action="store_true",
                   help="build the package in memory and write a preview + diff + validation "
                        "report to a gitignored review directory (never the committed package)")
    args = p.parse_args(argv)
    if args.preview:
        r = write_preview()
        print("PREVIEW: %d -> %d hotels (+%d/-%d), stale=%s; wrote preview to %s (committed package untouched)"
              % (r["old_count"], r["new_count"], r["additions_count"], r["removals_count"],
                 r["committed_would_become_stale"], DEFAULT_PREVIEW_DIR))
        return 0
    return check() if args.check else write_package()


if __name__ == "__main__":
    raise SystemExit(main())
