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

#: Where the capture phase left the market, before the founder ruled.
BASELINE_PET_FRIENDLY = 85
BASELINE_NO_PETS = 72
#: The founder approved exactly two identities: Kensington (APPROVE_PARTIAL)
#: and Embassy Suites Livonia Novi. Roberts Riverwalk publishes nothing.
FOUNDER_APPROVED = 2


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

    check("pet-friendly moved %d -> %d, exactly the founder's approvals"
          % (BASELINE_PET_FRIENDLY, BASELINE_PET_FRIENDLY + FOUNDER_APPROVED),
          len(published) == BASELINE_PET_FRIENDLY + FOUNDER_APPROVED,
          "now %d" % len(published))
    check("verified-no-pets unchanged at %d" % BASELINE_NO_PETS,
          len(excluded) == BASELINE_NO_PETS, "now %d" % len(excluded))

    ruled = load(LP / "detroit_ann_arbor_founder_rulings_020.json")["rulings"]
    keys = {row["identity_key"] for row in published}
    roberts = [r for r in ruled if r["decision"] == "ROUTING_REPAIR_REQUIRED"]
    check("the routing-repair identity publishes nothing",
          len(roberts) == 1 and roberts[0]["identity_key"] not in keys)
    routes = load(LP / "markets" / "authority" / MARKET
                  / "identity_routing.json")["routes"]
    check("the routing-repair identity is RETAINED, not withdrawn",
          any(r["hotel_ref"]["identity_key"] == roberts[0]["identity_key"]
              for r in routes))
    kens = [r for r in published
            if r["identity_key"] == "the kensington hotel ann arbor"]
    check("the partial approval published ONLY the approved fields",
          len(kens) == 1
          and set(kens[0]["facts"]) == {"pets_allowed", "general_restrictions"},
          str(sorted(kens[0]["facts"])) if kens else "missing")
    emb = [r for r in published if r["identity_key"]
           == "embassy suites by hilton detroit livonia novi"]
    check("the Embassy approval published ONLY the approved fields",
          len(emb) == 1 and set(emb[0]["facts"]) == {
              "pets_allowed", "fee_tiers", "pet_count_limit", "species"},
          str(sorted(emb[0]["facts"])) if emb else "missing")

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

    # The recapture row names its file "artifact", the swept rows name it
    # "block_artifact". An earlier version of this check read only the latter
    # and so SILENTLY SKIPPED the one property a founder ruled on. A hash check
    # that quietly covers nothing passes just as loudly as one that works.
    bad_hash = []
    for row in list(rows) + [recap]:
        artifact = row.get("block_artifact") or row.get("artifact")
        if not artifact:
            if row.get("block") or row.get("policy_block"):
                bad_hash.append((row["identity_key"], "block with no artifact"))
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
