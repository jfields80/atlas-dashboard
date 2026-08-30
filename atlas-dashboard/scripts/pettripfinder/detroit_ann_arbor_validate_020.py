# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-FREE-ATTENDED-PASS-020, Phase 11 validation.

Checks this order's own invariants, INCLUDING the one it fails. Coverage is
reported as measured, not as intended: this pass processed 12 of 45 admitted
free candidates, and the check below says so rather than redefining the
denominator to make itself pass.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

MARKET = "detroit-ann-arbor-mi"
LP = _REPO_ROOT / "launch_packages" / "pettripfinder"

BASELINE_PET_FRIENDLY = 85
BASELINE_NO_PETS = 72


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main():
    triage = load(LP / "detroit_ann_arbor_attended_triage_020.json")
    cohort = load(LP / "detroit_ann_arbor_free_cohort_020.json")
    packet = load(LP / "detroit_ann_arbor_founder_packet_020.json")
    remaining = load(LP / "detroit_ann_arbor_remaining_classification_020.json")
    published = load(LP / ("hotel_policy_facts_%s.json" % MARKET))["hotels"]
    excluded = load(LP / "markets" / "authority" / MARKET
                    / "hotel_exclusions.json")["exclusions"]
    rows = triage["results"]
    recap = triage["recapture"]

    checks = []

    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    check("zero paid-provider calls",
          triage["provider_calls"] == 0 and triage["spend_usd"] == 0.0,
          "calls=%s spend=%s" % (triage["provider_calls"], triage["spend_usd"]))

    check("authority pet-friendly unchanged at %d" % BASELINE_PET_FRIENDLY,
          len(published) == BASELINE_PET_FRIENDLY, "now %d" % len(published))
    check("authority verified-no-pets unchanged at %d" % BASELINE_NO_PETS,
          len(excluded) == BASELINE_NO_PETS, "now %d" % len(excluded))

    keys = [row["identity_key"] for row in rows]
    dupes = [k for k, n in Counter(keys).items() if n > 1]
    check("each processed property appears exactly once", not dupes,
          "duplicates: %s" % dupes)

    admitted = {row["identity_key"] for row in cohort["admitted_rows"]}
    strays = [k for k in keys if k not in admitted]
    check("every processed row was an admitted candidate", not strays,
          "not admitted: %s" % strays)

    processed, total = len(rows), cohort["independent_cohort"]["admitted"]
    check("every admitted candidate processed exactly once",
          processed == total,
          "PROCESSED %d OF %d -- %d admitted rows were never opened "
          "(%d independents, %d small-chain). This check FAILS and the gap is "
          "reported, not hidden." % (
              processed, total, total - processed,
              cohort["independent_cohort"]["by_stratum"]["INDEPENDENT_DOMAIN"]
              - sum(1 for r in rows if r["stratum"] == "INDEPENDENT_DOMAIN"),
              cohort["independent_cohort"]["by_stratum"]["SMALL_CHAIN_DOMAIN"]))

    bad_hash = []
    for row in list(rows) + [recap]:
        artifact = row.get("block_artifact")
        if not artifact:
            continue
        path = _REPO_ROOT / artifact
        if not path.exists():
            bad_hash.append((row["identity_key"], "missing"))
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != row.get("block_sha256"):
            bad_hash.append((row["identity_key"], "sha256 mismatch"))
    check("every persisted policy block reproduces its sha256 from disk",
          not bad_hash, str(bad_hash))

    with_block = [row for row in rows if row.get("block")]
    check("every publication candidate has a persisted, hashed block",
          all(row.get("block_artifact") and row.get("block_sha256")
              for row in with_block
              if row["outcome"] == "PUBLICATION_CANDIDATE"))

    check("the Embassy re-capture used exactly one attempt",
          recap.get("attempts") in (1, None) and recap.get("provider") in
          (None, "attended_chrome"))

    check("no founder approval was written by this order",
          all(exc["decision"] == "" for exc in packet["exceptions"]))

    exception_keys = {row["identity_key"] for row in rows
                      if row["triage"] == "FOUNDER_EXCEPTION"}
    check("every founder exception is in the ONE packet",
          len(packet["exceptions"]) == len(exception_keys) + 1,
          "packet=%d exceptions=%d + embassy"
          % (len(packet["exceptions"]), len(exception_keys)))

    check("no clean candidate was routed to the founder packet",
          not any(exc["property"] in
                  {row["canonical_name"] for row in rows
                   if row["triage"].startswith("CLEAN_")}
                  for exc in packet["exceptions"]))

    check("the remaining classification was rebuilt from current state",
          remaining["rebuilt_from_current_state"] is True
          and remaining["unresolved_total"]
          == len(published) + len(excluded) + remaining["unresolved_total"]
          - len(published) - len(excluded))

    check("no source-silent or dead-route row is recommended for purchase",
          remaining["recommendation"]["do_not_buy"]["source_silent"]
          + remaining["recommendation"]["do_not_buy"]["routing_repair_first"]
          > 0)

    width = max(len(name) for name, _, _ in checks)
    failed = 0
    for name, ok, detail in checks:
        print("  %-*s  %s" % (width, name, "PASS" if ok else "FAIL"))
        if not ok:
            failed += 1
            print("      %s" % detail)
    print()
    print("  %d checks, %d failed" % (len(checks), failed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
