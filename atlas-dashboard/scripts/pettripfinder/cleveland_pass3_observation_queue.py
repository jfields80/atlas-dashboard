"""PTF-CLEVELAND-ATTENDED-PASS-3-001 -- the 68-row observation/artifact queue.

Mechanically derived, never hand-curated: every identity whose final state is
AWAITING_POLICY_OBSERVATION (the route is sound, the page serves, no policy has
ever been observed) plus every AWAITING_POLICY_ARTIFACT identity whose pass-001
wording was AFFIRMATIVE_MARKETING_ONLY (a capture alone cannot publish it; the
actual policy surface has to be found and read). Everything else -- the
ADR-blocked Hyatts, the policy-silent Economy Inn, routing replacements,
missing or brand-level URLs, contradictions, census reviews, access blocks --
is deliberately out of scope and listed with its reason.

Run:  python -m scripts.pettripfinder.cleveland_pass3_observation_queue [--apply]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

MARKET = "cleveland-akron-canton-oh"
WORK_ORDER = "PTF-CLEVELAND-ATTENDED-PASS-3-001"
AS_OF = "2026-08-16"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
PARTITION_PATH = LP / "cleveland_final_partition_002.json"
CENSUS_PATH = LP / "identity_census" / ("%s.json" % MARKET)
QUEUE_PATH = LP / "cleveland_pass3_queue.json"

OBSERVATION = "AWAITING_POLICY_OBSERVATION"
MARKETING = "AWAITING_POLICY_ARTIFACT"

EXCLUDED_STATES = {
    "PUBLISHED_PET_FRIENDLY": "already published",
    "VERIFIED_NO_PETS": "already excluded",
    "AWAITING_ATTENDED_CAPTURE": "Economy Inn: site is policy-silent; founder "
                                 "ruled no automated retry",
    "AWAITING_ROUTING_REPLACEMENT": "URL provably wrong; routing lane",
    "AWAITING_ROUTING_REVIEW": "Hyatt Westlake: ADR-forbidden, operator-manual",
    "AWAITING_OFFICIAL_URL": "no URL; discovery lane",
    "AWAITING_PROPERTY_LEVEL_URL": "brand-level URL only; discovery lane",
    "AWAITING_CONTRADICTION_RESOLUTION": "approval_resolution lane",
    "AWAITING_CENSUS_REVIEW": "census lane",
    "ACCESS_BLOCKED": "no lawful automated path",
}


def load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> Dict:
    partition = load(PARTITION_PATH)
    census = {r["identity_key"]: r for r in load(CENSUS_PATH)["hotels"]}

    observation = sorted(
        (i for i in partition["items"] if i["final_state"] == OBSERVATION),
        key=lambda i: i["identity_key"])
    marketing = sorted(
        (i for i in partition["items"]
         if i["final_state"] == MARKETING
         and i.get("policy_wording_shape") == "AFFIRMATIVE_MARKETING_ONLY"),
        key=lambda i: i["identity_key"])
    hyatt_artifact = [i for i in partition["items"]
                      if i["final_state"] == MARKETING
                      and i.get("policy_wording_shape")
                      != "AFFIRMATIVE_MARKETING_ONLY"]

    rows: List[Dict] = []
    for group, items in (("OBSERVATION", observation),
                         ("MARKETING_ONLY_ARTIFACT", marketing)):
        for item in items:
            row = census[item["identity_key"]]
            if not (item.get("official_url") or "").strip():
                raise SystemExit("STOP: %s queued without a URL"
                                 % item["identity_key"])
            rows.append(OrderedDict([
                ("queue_id", "CLE-P3-%03d" % (len(rows) + 1)),
                ("group", group),
                ("identity_key", item["identity_key"]),
                ("name", row["canonical_name"]),
                ("slug", row["slug"]),
                ("official_url", item["official_url"]),
                ("address", row["address"]),
                ("city", row["city"]),
                ("postal_code", row["postal_code"]),
                ("phone", row["phone"]),
                ("prior_state", item["final_state"]),
                ("prior_wording_shape", item.get("policy_wording_shape") or ""),
            ]))

    if not (len(observation) == 30 and len(marketing) == 38
            and len(rows) == 68):
        raise SystemExit("STOP: expected 30+38=68 rows, derived %d+%d=%d"
                         % (len(observation), len(marketing), len(rows)))
    keys = [r["identity_key"] for r in rows]
    if len(set(keys)) != 68:
        raise SystemExit("STOP: duplicate identity in the queue")

    excluded = OrderedDict()
    for item in partition["items"]:
        state = item["final_state"]
        if state in (OBSERVATION,):
            continue
        if state == MARKETING and item in marketing:
            continue
        if state == MARKETING and item in hyatt_artifact:
            reason = ("Hyatt: ADR-forbidden for automation; operator-manual "
                      "screenshot route")
        else:
            reason = EXCLUDED_STATES.get(state, state)
        excluded.setdefault(reason, []).append(item["identity_key"])

    return OrderedDict([
        ("schema", "ptf-cleveland-pass3-queue/1.0"),
        ("work_order", WORK_ORDER),
        ("as_of", AS_OF),
        ("market_id", MARKET),
        ("derived_from", "cleveland_final_partition_002.json at b4d48e3"),
        ("rule", "Every AWAITING_POLICY_OBSERVATION identity plus every "
                 "marketing-only AWAITING_POLICY_ARTIFACT identity, each "
                 "exactly once, each with a property-level URL. Nothing is "
                 "hand-added and nothing driveable is skipped."),
        ("totals", OrderedDict([
            ("observation", len(observation)),
            ("marketing_only_artifact", len(marketing)),
            ("queue_total", len(rows)),
        ])),
        ("deliberately_not_queued",
         OrderedDict((reason, sorted(keys))
                     for reason, keys in excluded.items())),
        ("rows", rows),
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    doc = build()
    print("queue_total: %d (observation %d + marketing-only %d)"
          % (doc["totals"]["queue_total"], doc["totals"]["observation"],
             doc["totals"]["marketing_only_artifact"]))
    if args.apply:
        QUEUE_PATH.write_bytes(
            (json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
            .encode("utf-8"))
        print("wrote %s" % QUEUE_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
