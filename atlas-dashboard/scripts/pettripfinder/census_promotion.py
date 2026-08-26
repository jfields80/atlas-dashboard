"""Apply a founder-approved promotion plan to a proposed census -- into a SHADOW census.

    python scripts/pettripfinder/census_promotion.py \\
      --market indianapolis-in \\
      --plan launch_packages/pettripfinder/indianapolis_in_census_promotion_plan_003.json \\
      --census launch_packages/pettripfinder/identity_census_proposed/indianapolis-in.json \\
      --pilot launch_packages/pettripfinder/indianapolis_in_acquisition_merged_closeout_002.json \\
      --prior-census launch_packages/pettripfinder/identity_census/indianapolis-in.json \\
      --out-census launch_packages/pettripfinder/identity_census_promotion/indianapolis-in.json \\
      --out-pilot launch_packages/pettripfinder/indianapolis_in_acquisition_merged_promotion_003.json \\
      --out-report launch_packages/pettripfinder/indianapolis_in_census_promotion_report_003.json

WHY A SHADOW
------------
A registered market's census is pinned by its release contract (``expected_count``), and every
generic tool reads it by convention. Promotion is therefore never an edit in place: the plan is
applied to a COPY, the copy is validated against the census contract, and replacing the pinned
file stays a separate, founder-authorised step (PTF-INDIANAPOLIS-HARDENED-RECENSUS-002).

WHAT THE PLAN MAY DO, IN THIS ORDER
-----------------------------------
1. ``retirements`` -- remove a stale twin row in favour of a surviving key.
2. ``merges``      -- fold a duplicate row into its survivor; the survivor keeps its own values and
                      takes the listed fields from the retired row only where it has none.
3. ``renames``     -- give a row the name its own page states. The identity key is DERIVED from
                      the name (``ptf_identity_key/1.0``), so a rename re-keys the row, and the old
                      and new keys are recorded in the key map every downstream artifact must use.
                      A rename whose new key still exists is a collision and refuses.
4. ``phone_corrections`` / ``url_corrections`` -- clear a value proven wrong, or set the one the
                      acquisition actually used. Nothing is invented: a cleared URL returns the row
                      to NEEDS_OFFICIAL_URL.
5. ``address_supersessions`` -- VERIFIED, not applied: the proposed census already carries the
                      first-party address; the prior census carried the stale one. The report shows both.

The acquisition pilot (the merged closeout) is re-keyed by the same map so the observation store
built from it joins the shadow census row for row; a result whose identity was merged away is
recorded as superseded, never silently dropped.

Nothing here fetches, spends, edits the pinned census, or writes authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.contracts import census as CENSUS          # noqa: E402
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key  # noqa: E402

PLAN_SCHEMA = "ptf-census-promotion-plan/1.0"
REPORT_SCHEMA = "ptf-census-promotion-report/1.0"


class PromotionError(ValueError):
    """The plan asks for something the census cannot support; nothing is written."""


def _sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _slug(identity_key: str) -> str:
    return identity_key.replace(" ", "-")


def _require(rows: Mapping[str, Dict], key: str, what: str) -> Dict:
    if key not in rows:
        raise PromotionError("%s names identity key %r, which is not in the census" % (what, key))
    return rows[key]


def apply_plan(plan: Mapping, census: Mapping, *, prior_census: Optional[Mapping] = None
               ) -> Tuple[Dict, Dict, Dict]:
    """``(shadow_census, key_map, report)``. Pure; nothing is written."""
    if plan.get("schema") != PLAN_SCHEMA:
        raise PromotionError("plan schema is %r, expected %s" % (plan.get("schema"), PLAN_SCHEMA))
    if plan.get("market_id") != census.get("market_id"):
        raise PromotionError("plan is for %r, census is for %r"
                             % (plan.get("market_id"), census.get("market_id")))
    rows: "OrderedDict[str, Dict]" = OrderedDict(
        (h["identity_key"], json.loads(json.dumps(h))) for h in census.get("hotels") or ())
    if len(rows) != len(census.get("hotels") or ()):
        raise PromotionError("the census carries duplicate identity keys; promotion refuses")
    prior_rows = {h["identity_key"]: h for h in (prior_census or {}).get("hotels") or ()}
    key_map: "OrderedDict[str, str]" = OrderedDict()      # old key -> surviving key
    retired: List[Dict] = []
    merged: List[Dict] = []
    renamed: List[Dict] = []
    corrected: List[Dict] = []
    verified_addresses: List[Dict] = []

    # 1. retirements ------------------------------------------------------------------------
    for item in plan.get("retirements") or ():
        row = _require(rows, item["retired_identity_key"], "retirement")
        rows.pop(item["retired_identity_key"])
        key_map[item["retired_identity_key"]] = item["in_favour_of"]
        retired.append(OrderedDict((
            ("retired_identity_key", item["retired_identity_key"]),
            ("canonical_name", row.get("canonical_name", "")),
            ("address", row.get("address", "")),
            ("in_favour_of", item["in_favour_of"]),
            ("why", item.get("why", "")),
        )))

    # 2. merges -----------------------------------------------------------------------------
    for item in plan.get("merges") or ():
        survivor = _require(rows, item["surviving_identity_key"], "merge survivor")
        gone = _require(rows, item["retired_identity_key"], "merge retired row")
        taken = OrderedDict()
        for name in item.get("census_fields_from_retired_row") or ():
            if not survivor.get(name) and gone.get(name):
                survivor[name] = gone[name]
                taken[name] = gone[name]
        rows.pop(item["retired_identity_key"])
        key_map[item["retired_identity_key"]] = item["surviving_identity_key"]
        survivor.setdefault("promotion", OrderedDict())
        survivor["promotion"].setdefault("merged_from", []).append(item["retired_identity_key"])
        merged.append(OrderedDict((
            ("surviving_identity_key", item["surviving_identity_key"]),
            ("retired_identity_key", item["retired_identity_key"]),
            ("observation_from_identity_key", item.get("observation_from_identity_key", "")),
            ("fields_taken_from_retired_row", taken),
            ("ledger_rows", list(item.get("ledger_rows") or ())),
        )))

    # 3. renames ----------------------------------------------------------------------------
    for item in plan.get("renames") or ():
        old_key, new_name = item["identity_key"], item["to"]
        new_key = ptf_identity_key(new_name)
        if new_key != item.get("new_identity_key", new_key):
            raise PromotionError("rename %r: plan says new key %r but %r derives from the name"
                                 % (old_key, item.get("new_identity_key"), new_key))
        row = _require(rows, old_key, "rename")
        if new_key in rows:
            raise PromotionError("rename %r -> %r collides with an existing census row"
                                 % (old_key, new_key))
        rows.pop(old_key)
        row["name_before_promotion"] = row.get("canonical_name", "")
        row["canonical_name"] = new_name
        row["display_name"] = new_name
        row["identity_key"] = new_key
        row["normalized_name"] = new_key
        row["slug"] = _slug(new_key)
        row.setdefault("promotion", OrderedDict())["renamed_from"] = old_key
        rows[new_key] = row
        key_map[old_key] = new_key
        for other in list(key_map):
            if key_map[other] == old_key:
                key_map[other] = new_key
        renamed.append(OrderedDict((
            ("from_identity_key", old_key), ("to_identity_key", new_key),
            ("from_name", item["from"]), ("to_name", new_name),
            ("ledger_row", item.get("ledger_row", "")),
        )))

    # 4. phone / url corrections ------------------------------------------------------------
    for item in plan.get("phone_corrections") or ():
        row = _require(rows, item["identity_key"], "phone correction")
        if row.get("phone") != item["clear_phone"]:
            raise PromotionError("phone correction %r: row carries %r, not %r"
                                 % (item["identity_key"], row.get("phone"), item["clear_phone"]))
        row["phone"] = ""
        row.setdefault("promotion", OrderedDict())["phone_cleared"] = item["clear_phone"]
        corrected.append(OrderedDict((("identity_key", item["identity_key"]), ("field", "phone"),
                                      ("from", item["clear_phone"]), ("to", ""), ("why", item.get("why", "")))))
    for item in plan.get("url_corrections") or ():
        row = _require(rows, item["identity_key"], "url correction")
        if row.get("official_url") != item["from"]:
            raise PromotionError("url correction %r: row carries %r, not %r"
                                 % (item["identity_key"], row.get("official_url"), item["from"]))
        row["official_url"] = item["to"]
        row.setdefault("promotion", OrderedDict())["official_url_was"] = item["from"]
        corrected.append(OrderedDict((("identity_key", item["identity_key"]), ("field", "official_url"),
                                      ("from", item["from"]), ("to", item["to"]), ("why", item.get("why", "")))))

    # 5. address supersessions: verified, never applied ------------------------------------
    for item in plan.get("address_supersessions") or ():
        row = _require(rows, item["identity_key"], "address supersession")
        first_party = item["first_party_address"]
        street = first_party.split(",")[0].strip().lower()
        postal = first_party.split(",")[-1].strip()[:5]
        agrees = (row.get("address", "").strip().lower() == street
                  and (row.get("postal_code") or "")[:5] == postal)
        if not agrees:
            raise PromotionError("address supersession %r: the proposed row carries %r %r, not %r"
                                 % (item["identity_key"], row.get("address"), row.get("postal_code"), first_party))
        prior = prior_rows.get(item["identity_key"], {})
        verified_addresses.append(OrderedDict((
            ("identity_key", item["identity_key"]),
            ("prior_census_address", "%s, %s" % (prior.get("address", ""), prior.get("postal_code", ""))
             if prior else item.get("prior_census_address", "")),
            ("shadow_census_address", "%s, %s" % (row.get("address", ""), row.get("postal_code", ""))),
            ("superseded", True),
        )))

    # validation against the census contract -----------------------------------------------
    # The census builder writes rows in identity-key order; a shadow that keeps
    # that order diffs cleanly against the census it came from.
    hotels = [rows[key] for key in sorted(rows)]
    shadow = OrderedDict(census)
    shadow["hotels"] = hotels
    shadow["count"] = len(hotels)
    shadow["work_order"] = plan.get("work_order", "")
    shadow["promotion"] = OrderedDict((
        ("what_this_is", "a SHADOW promotion census: the proposed census with the founder-approved "
                         "plan applied; the pinned census is untouched"),
        ("plan_work_order", plan.get("work_order", "")),
        ("decided_by", plan.get("decided_by", "")),
        ("from_count", len(census.get("hotels") or ())),
        ("to_count", len(hotels)),
        ("key_map", key_map),
    ))
    before = {(i.path.split(".")[0] if hasattr(i, "path") else "", getattr(i, "code", "")) for i in CENSUS.validate(census)}
    after_issues = list(CENSUS.validate(shadow))
    new_issue_codes = sorted({getattr(i, "code", "") for i in after_issues}
                             - {code for _, code in before})
    if new_issue_codes:
        raise PromotionError("the shadow census introduces contract issues the proposed census "
                             "did not have: %s" % new_issue_codes)

    report = OrderedDict((
        ("schema", REPORT_SCHEMA),
        ("market_id", census.get("market_id", "")),
        ("work_order", plan.get("work_order", "")),
        ("from_count", len(census.get("hotels") or ())),
        ("to_count", len(hotels)),
        ("retired", retired), ("merged", merged), ("renamed", renamed),
        ("corrections", corrected), ("address_supersessions_verified", verified_addresses),
        ("key_map", key_map),
        ("contract_issues_before", len(list(CENSUS.validate(census)))),
        ("contract_issues_after", len(after_issues)),
    ))
    return shadow, key_map, report


def rekey_pilot(pilot: Mapping, plan: Mapping, key_map: Mapping[str, str],
                shadow: Mapping) -> Tuple[Dict, Dict]:
    """The merged acquisition report under the shadow census's keys.

    A renamed identity keeps its result under the new key and name. A merged
    identity's SURVIVING observation is the one the plan names
    (``observation_from_identity_key``); it is re-keyed to the survivor, and
    any other result under either key is recorded as superseded.
    """
    names = {h["identity_key"]: h.get("canonical_name", "") for h in shadow.get("hotels") or ()}
    survivor_source = {m["surviving_identity_key"]: m.get("observation_from_identity_key", "")
                       for m in plan.get("merges") or ()}
    results: List[Dict] = []
    superseded: List[Dict] = []
    seen = set()
    for result in pilot.get("results") or ():
        old = result["identity_key"]
        new = key_map.get(old, old)
        row = dict(result)
        if new in survivor_source and survivor_source[new] and old != survivor_source[new]:
            superseded.append(OrderedDict((("identity_key", old), ("surviving_identity_key", new),
                                           ("outcome", result.get("outcome", "")),
                                           ("why", "the plan names %r as the surviving observation"
                                            % survivor_source[new]))))
            continue
        if new != old:
            row["identity_key"] = new
            row["promotion_identity_key_was"] = old
            if result.get("outcome") == "VALID":
                row["canonical_name"] = names.get(new, result.get("canonical_name", ""))
        if new in seen:
            raise PromotionError("two results would share key %r after re-keying" % new)
        seen.add(new)
        results.append(row)
    out = OrderedDict(pilot)
    out["results"] = results
    out["promotion"] = OrderedDict((("key_map", dict(key_map)), ("superseded_results", superseded),
                                    ("work_order", plan.get("work_order", ""))))
    return out, OrderedDict((("results_in", len(pilot.get("results") or ())),
                             ("results_out", len(results)), ("superseded", superseded)))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--market", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--census", required=True, help="the proposed census the plan applies to")
    parser.add_argument("--pilot", required=True, help="the merged acquisition report to re-key")
    parser.add_argument("--prior-census", default="", help="the pinned census, for address-supersession reporting only")
    parser.add_argument("--out-census", required=True)
    parser.add_argument("--out-pilot", required=True)
    parser.add_argument("--out-report", required=True)
    args = parser.parse_args(argv)

    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    census = json.loads(Path(args.census).read_text(encoding="utf-8"))
    pilot = json.loads(Path(args.pilot).read_text(encoding="utf-8"))
    prior = json.loads(Path(args.prior_census).read_text(encoding="utf-8")) if args.prior_census else None
    if census.get("market_id") != args.market:
        raise PromotionError("census is for %r, not %r" % (census.get("market_id"), args.market))
    out_census = Path(args.out_census)
    if out_census.resolve() == Path(args.census).resolve():
        raise PromotionError("refusing to overwrite the input census; promotion writes a shadow")
    shadow, key_map, report = apply_plan(plan, census, prior_census=prior)
    rekeyed, pilot_report = rekey_pilot(pilot, plan, key_map, shadow)
    report["pilot"] = pilot_report
    report["inputs"] = OrderedDict((("plan", args.plan), ("plan_sha256", _sha256_of(Path(args.plan))),
                                    ("census", args.census), ("census_sha256", _sha256_of(Path(args.census))),
                                    ("pilot", args.pilot), ("pilot_sha256", _sha256_of(Path(args.pilot)))))
    out_census.parent.mkdir(parents=True, exist_ok=True)
    out_census.write_text(json.dumps(shadow, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    Path(args.out_pilot).write_text(json.dumps(rekeyed, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    report["outputs"] = OrderedDict((("shadow_census", args.out_census), ("shadow_census_sha256", _sha256_of(out_census)),
                                     ("pilot", args.out_pilot), ("pilot_sha256", _sha256_of(Path(args.out_pilot)))))
    Path(args.out_report).write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("shadow census: %d -> %d rows (retired %d, merged %d, renamed %d, corrections %d); pilot %d -> %d results"
          % (report["from_count"], report["to_count"], len(report["retired"]), len(report["merged"]),
             len(report["renamed"]), len(report["corrections"]), pilot_report["results_in"], pilot_report["results_out"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
