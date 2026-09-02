"""PTF-DAYTON-OH-HARDENED-APPLICATION-002 -- Phase 9.

Extend Dayton's seed/display inventory to cover the seven identities this order
published.

The seed shard and the policy package are two authorities, not one:
``site_data.verified_public_hotels()`` publishes an identity only where BOTH
carry it, so a policy record without a seed row publishes nothing and a seed row
without a policy record is a held row. This pass adds exactly the rows needed to
close that gap and nothing else.

Every field is copied from an authority that already holds it -- the pinned
census for the premises and telephone, the applied policy record for the source
URL and the policy sentence. No value is invented here, and no existing seed row
is touched.

Guards, all fail-closed:
  * a row is added only for an identity the policy package publishes;
  * never for an identity the exclusion shard carries;
  * one row per identity, no duplicate name and no duplicate premises;
  * the resulting inventory must match the published set exactly.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, OrderedDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.site_data import normalize_name  # noqa: E402
from scripts.pettripfinder import hotel_exclusions as HX  # noqa: E402
from scripts.pettripfinder import market_authority as MA  # noqa: E402

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
MARKET = "dayton-oh"
#: Resolved by the sharding module rather than rebuilt here. Building the path
#: locally would also make this module indistinguishable, to the write-discipline
#: scan, from one that writes the GENERATED global seed file -- and the whole
#: point of this pass is that it writes a shard and lets
#: build_global_authority.py regenerate the globals from it.
SEED = MA.seed_shard_path(MARKET)
CENSUS = LP / "identity_census" / ("%s.json" % MARKET)
POLICY = LP / ("hotel_policy_facts_%s.json" % MARKET)
EXCL = MA.exclusions_shard_path(MARKET)
COLUMNS = list(MA.SEED_COLUMNS)


def _load(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def build(write: bool):
    census = {h["identity_key"]: h for h in _load(CENSUS)["hotels"]}
    policy = {r["identity_key"]: r for r in _load(POLICY)["hotels"]}
    excluded = {e["normalized_name"] for e in _load(EXCL)["exclusions"]}
    rows = MA.load_market_seed_rows(MARKET)
    have = {normalize_name(r["name"]) for r in rows}

    added, skipped = [], []
    for key in sorted(set(policy) - have):
        crow = census.get(key)
        prec = policy[key]
        if crow is None:
            skipped.append((key, "IDENTITY_NOT_IN_PINNED_CENSUS"))
            continue
        if HX.normalize_name(crow["canonical_name"]) in excluded:
            skipped.append((key, "IDENTITY_IS_EXCLUDED"))
            continue
        added.append(OrderedDict([
            ("name", crow["canonical_name"]),
            ("category", "pet-friendly-hotels"),
            ("address", crow.get("address", "")),
            ("city", crow.get("city", "")),
            ("state", crow.get("state", "")),
            ("postal_code", crow.get("postal_code", "")),
            ("phone", crow.get("phone", "")),
            ("website_url", prec.get("source_url", "")),
            ("source_url", prec.get("source_url", "")),
            ("source_type", "OFFICIAL_PROPERTY"),
            ("observed_at", prec.get("verified_at", "")),
            ("rating", ""),
            ("amenities", ""),
            ("pet_policy", (prec.get("evidence_quote") or "")[:400]),
            ("canonical", ""),
            ("market_id", MARKET),
        ]))

    out = rows + added
    # --- guards -----------------------------------------------------------
    names = Counter(normalize_name(r["name"]) for r in out)
    dup_names = [n for n, c in names.items() if c > 1]
    premises = Counter((r["address"].strip().lower(), r["postal_code"].strip())
                       for r in out if r["address"].strip())
    dup_prem = [p for p, c in premises.items() if c > 1]
    seed_keys = set(names)
    only_seed = sorted(seed_keys - set(policy))
    only_policy = sorted(set(policy) - seed_keys)
    excluded_in_seed = sorted(n for n in seed_keys if n in excluded)

    problems = []
    if dup_names:
        problems.append("duplicate seed names: %s" % dup_names)
    if dup_prem:
        problems.append("duplicate premises: %s" % dup_prem)
    if only_seed:
        problems.append("seed rows with no policy record: %s" % only_seed)
    if only_policy:
        problems.append("policy records with no seed row: %s" % only_policy)
    if excluded_in_seed:
        problems.append("excluded identities present in seed inventory: %s" % excluded_in_seed)

    print("seed rows %d -> %d (added %d, skipped %d)"
          % (len(rows), len(out), len(added), len(skipped)))
    for k, why in skipped:
        print("   skipped", k, why)
    if problems:
        for p in problems:
            print("  PROBLEM:", p)
        raise SystemExit("seed inventory guards failed")
    print("guards: one row per published identity, no duplicate name, no duplicate premises, "
          "no excluded identity, seed set == policy set (%d)" % len(out))

    if write:
        SEED.write_bytes(MA.render_seed_csv(
            [{c: r.get(c, "") for c in COLUMNS} for r in out]).encode("utf-8"))
        print("WRITTEN", SEED.relative_to(_REPO_ROOT).as_posix())
    return len(rows), len(out), added


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    build(args.write)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
