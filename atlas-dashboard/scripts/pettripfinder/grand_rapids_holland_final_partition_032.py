# -*- coding: utf-8 -*-
"""PTF-GRAND-RAPIDS-LAUNCH-PARTICIPATION-032 -- the final partition, from what is signed now.

The committed Grand Rapids partition was written by
PTF-GRAND-RAPIDS-HOLLAND-PAID-ACQUISITION-AUTHORIZATION-009, before any founder
signed anything. It still carries 42 rows as AWAITING_FOUNDER_DECISION, and 40
of those have since been decided: 30 publish and 10 are excluded. A market
cannot be assembled on a partition that says its published hotels are waiting to
be looked at.

WHAT THIS REBUILDS, AND WHAT IT REFUSES TO
-------------------------------------------
The 63 rows the founder has ruled on move to their terminal state, read from
the DECISION LEDGERS rather than from the shards. The ledgers are the only
artifact that carries an identity_key beside a class: the exclusions shard keys
on normalized_name, and 020's name corrections moved some of those, so matching
a partition row to an exclusion by name would silently mis-assign a corrected
row.

  PUBLISHED_PET_FRIENDLY   43
  VERIFIED_NO_PETS         20

The other 100 keep the state they already carry. THIS PASS RE-ADJUDICATES
NOTHING. A row nobody has ruled on since 009 is a row whose blocker has not
changed, and inventing a fresher-looking state for it would be writing a
finding no work order made. Two of them stay AWAITING_FOUNDER_DECISION and both
are honest:

  avid hotel zeeland -- the founder withdrew it in
    PTF-GRAND-RAPIDS-SOURCE-PROMOTION-022 "for now", which is precisely a
    decision still owed.
  comfort suites grandville grand rapids sw -- one half of an identity pair 019
    holds open, with clean policy evidence and an unsettled identity.

THE WITHDRAWN ROW IS NOT PUBLISHED AND NOT FORGOTTEN. avid hotel zeeland was
signed and then withdrawn, so it is absent from the effective authority and
present here in the state that says what it is waiting for.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import census_partition_builder as CPB  # noqa: E402
from scripts.pettripfinder.contracts import enums                  # noqa: E402

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
MARKET = "grand-rapids-holland-mi"
CENSUS = LP / "identity_census" / ("%s.json" % MARKET)
STALE = LP / "grand_rapids_holland_mi_final_partition_001.json"
LEDGERS = ("grand_rapids_holland_mi_founder_decision_ledger_021.json",
           "grand_rapids_holland_mi_founder_decision_ledger_030.json")
WITHDRAWAL = LP / "grand_rapids_holland_mi_founder_withdrawal_022.json"
OUT = LP / "grand_rapids_holland_mi_final_partition_002.json"

WORK_ORDER = "PTF-GRAND-RAPIDS-LAUNCH-PARTICIPATION-032"
AS_OF = "2026-08-29"


def _load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def effective_authority() -> Dict[str, str]:
    """``identity_key -> terminal state``, from the ledgers minus withdrawals.

    Read from the decision ledgers because they are the only artifact that puts
    an identity_key beside a class. A signature is a dated act and a withdrawal
    supersedes it without erasing it, so the effective set is
    (union of signed) MINUS (withdrawn) -- the same arithmetic
    market_proposed_authority_cli performs.
    """
    signed: Dict[str, str] = {}
    for name in LEDGERS:
        for row in _load(LP / name)["signed"]:
            signed[row["identity_key"]] = row["proposes_authority"]
    withdrawn = {w["retired_identity_key"]
                 for w in (_load(WITHDRAWAL).get("withdrawals") or ())}
    return {key: state for key, state in signed.items() if key not in withdrawn}


def build() -> Dict:
    census = {h["identity_key"]: h for h in _load(CENSUS)["hotels"]}
    prior = {i["identity_key"]: i for i in _load(STALE)["items"]}
    ruled = effective_authority()

    missing = sorted(set(ruled) - set(census))
    if missing:
        raise SystemExit("ruled identities absent from the pinned census: %s"
                         % missing)
    unpartitioned = sorted(set(census) - set(prior))
    if unpartitioned:
        raise SystemExit("census identities the prior partition never named: %s"
                         % unpartitioned)

    items: List[Dict] = []
    for key in sorted(census):
        row, before = census[key], prior[key]
        state = ruled.get(key, before["final_state"])
        items.append(CPB.partition_item(
            identity_key=key,
            canonical_name=row.get("canonical_name", before["canonical_name"]),
            slug=CPB.slugify(row.get("canonical_name", "")) or before["slug"],
            city=row.get("city", ""), state=row.get("state", ""),
            postal_code=row.get("postal_code", ""),
            final_state=state,
            next_action_source=("" if key in ruled
                                else before.get("next_action_source", "")),
            determined_by=(WORK_ORDER if key in ruled
                           else before.get("determined_by", "")),
            updated_at=AS_OF if key in ruled else before.get("updated_at", AS_OF),
            official_url=row.get("official_url", "") or before.get("official_url", ""),
            state_override_reason=before.get("state_override_reason", ""),
        ))

    document = CPB.partition_document(
        MARKET, items, as_of=AS_OF,
        note=("Rebuilt from the founder-signed authority. The partition this "
              "supersedes was written before any founder signed and still "
              "carried 42 rows as AWAITING_FOUNDER_DECISION, 40 of which have "
              "since been decided. The 63 ruled rows are read from the decision "
              "ledgers, which are the only artifact carrying an identity_key "
              "beside a class; the other 100 keep the state they already had, "
              "because nothing has ruled on them and a fresher-looking state "
              "would be a finding no work order made."),
        source_authorities=[
            "PTF-GRAND-RAPIDS-FOUNDER-SIGNATURE-PASS-021",
            "PTF-GRAND-RAPIDS-SOURCE-PROMOTION-022",
            "PTF-GRAND-RAPIDS-CENSUS-PIN-AND-RELEASE-CONTRACT-024",
            "PTF-GRAND-RAPIDS-FOUNDER-SIGNATURE-PASS-030",
            "PTF-GRAND-RAPIDS-FEE-CAP-QUALIFIER-RULING-031",
            "PTF-GRAND-RAPIDS-HOLLAND-PAID-ACQUISITION-AUTHORIZATION-009"
            " (superseded; the states of rows nobody has ruled on since)",
        ])
    document["supersedes"] = OrderedDict((
        ("path", STALE.relative_to(_REPO_ROOT).as_posix()),
        ("work_order", _load(STALE).get("work_order", "")),
        ("why", "it predates every founder signature this market has"),
    ))
    return document


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(OUT))
    args = parser.parse_args(argv)
    document = build()
    counts = document["final_state_counts"]
    ruled = effective_authority()

    published = counts.get(enums.PUBLISHED_PET_FRIENDLY, 0)
    no_pets = counts.get(enums.VERIFIED_NO_PETS, 0)
    awaiting = counts.get("AWAITING_FOUNDER_DECISION", 0)
    resolved_awaiting = [i["identity_key"] for i in document["items"]
                         if i["identity_key"] in ruled
                         and i["final_state"] == "AWAITING_FOUNDER_DECISION"]
    if resolved_awaiting:
        raise SystemExit("ruled rows left AWAITING_FOUNDER_DECISION: %s"
                         % resolved_awaiting)

    CPB.write_json(Path(args.out), document)
    print("count                      %d" % document["count"])
    print("PUBLISHED_PET_FRIENDLY     %d" % published)
    print("VERIFIED_NO_PETS           %d" % no_pets)
    print("resolved (terminal)        %d" % (published + no_pets))
    print("unresolved                 %d" % (document["count"] - published - no_pets))
    print("AWAITING_FOUNDER_DECISION  %d (none of them ruled)" % awaiting)
    print("states:", dict(counts))
    print("written:", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
