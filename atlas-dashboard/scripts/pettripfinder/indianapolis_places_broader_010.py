# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-PLACES-BROADER-RECOVERY-010 -- the remaining 118, and nothing else.

The qualification sample measured what a targeted Places lookup is worth once
names are compared by identity rather than by presentation: 8 of 18 on the
name-and-postal key, with every wrong-hotel control still refusing. This runs
the rest of the unroutable universe on that rule.

ROUTING DISCOVERY ONLY. It asks where a hotel's website is. It fetches no
policy, reads no pet rule, and touches no authority.

THE COHORT IS DERIVED, NOT TYPED
--------------------------------
143 unroutable identities minus the 25 already attempted = 118. The subtraction
is done against the committed inventory and the committed sample, and the run
refuses to start unless the arithmetic lands exactly. Then every row is put
through the discovery ledger before the money: a row the ledger already covers
cannot enter the cohort, and payable + suppressed has to equal the whole
remaining universe or nothing runs.

THE FALSE-BINDING TRIPWIRE
--------------------------
008 found two wrong hotels offered by name alone -- a Hampton Inn for a Cambria,
a Homewood Suites for a Hampton Inn. Those were caught by hand, on 25 rows. At
118 nobody reads every row, so the run watches for the same shape mechanically:
if bound rows start disagreeing with the census on the brand word that opens
their name, it stops and reports rather than spending the rest of the cap
contaminating the routing table.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import discovery_attempt_ledger as DAL  # noqa: E402
from scripts.pettripfinder.acquisition import market_routing as MR             # noqa: E402
from scripts.pettripfinder.discovery import census_url_recovery as URC         # noqa: E402
from scripts.pettripfinder.discovery import constants as C                     # noqa: E402
from scripts.pettripfinder.discovery.cache import DiscoveryCache               # noqa: E402
from scripts.pettripfinder.discovery.google_places import GooglePlacesClient   # noqa: E402
from scripts.pettripfinder.discovery.models import DiscoverySourceQuery        # noqa: E402
from scripts.pettripfinder.discovery.query_plan import RequestBudget           # noqa: E402

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
LEDGER_PATH = LP / "ptf_discovery_attempt_ledger_001.json"
CACHE_DIR = _REPO_ROOT / "data" / "discovery" / "indianapolis_places_010" / "cache"

SCHEMA = "ptf-places-broader-recovery/1.0"
WORK_ORDER = "PTF-INDIANAPOLIS-PLACES-BROADER-RECOVERY-010"
RUN_ID = "indianapolis-in-places-010"
MARKET = "indianapolis-in"

MAX_REQUESTS = 118
UNIVERSE = 143
ALREADY_ATTEMPTED = 25

#: How many bound rows may disagree with the census on their opening brand word
#: before the run stops. One is a rename; a run of them is a rule that has
#: started matching on locality alone.
BRAND_DISAGREEMENT_LIMIT = 3


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _query(row: Dict) -> str:
    parts = [row.get("canonical_name") or "", row.get("street") or "",
             row.get("city") or "", "IN", row.get("postal_code") or ""]
    return ", ".join(p for p in parts if p)


def _census_row(row: Dict) -> Dict:
    return {"identity_key": row["identity_key"],
            "canonical_name": row["canonical_name"],
            "address": row.get("street") or "", "street": row.get("street") or "",
            "city": row.get("city") or "", "state": "IN",
            "postal_code": row.get("postal_code") or "",
            "phone": row.get("telephone") or "",
            "telephone": row.get("telephone") or "", "official_url": ""}


def _postal_of(address: str) -> str:
    for token in reversed((address or "").replace(",", " ").split()):
        if len(token) == 5 and token.isdigit():
            return token
    return ""


def _observations(records) -> List[URC.Observation]:
    return [URC.Observation(provider=URC.GOOGLE_PLACES,
                            source="places:%s" % (r.provider_record_id or "?"),
                            name=r.name, phone=r.phone,
                            postal=r.postal_code or _postal_of(r.address_line),
                            url=r.website_url, street=r.address_line)
            for r in records]


def _bind(census: Dict, records) -> Tuple[Optional[object], str, List[Dict], Optional[object]]:
    observations = _observations(records)
    pairs = list(zip(observations, records))

    def acceptable(observation) -> Tuple[bool, str]:
        url = MR.normalize_source_url(observation.url)
        if not url:
            return (False, "the place carries no website at all")
        shape = MR.classify_url_shape(url)
        if shape not in MR.ROUTABLE_SHAPES:
            return (False, "the website is a %s, which no lane can fetch as "
                           "this hotel's page" % shape)
        return URC.url_names_the_property(census.get("canonical_name", ""), url)

    rejected: List[Dict] = []
    observation, binding = URC.bind(census, observations,
                                    unambiguous_streets=None,
                                    acceptable=acceptable, rejected=rejected,
                                    presentation_variants=True)
    matched = None
    if observation is not None:
        for candidate, record in pairs:
            if candidate is observation:
                matched = record
                break
    return (observation, binding, rejected, matched)


def _bind_state(observation, binding, records, rejected) -> str:
    if observation is not None and binding:
        return DAL.BIND_BOUND
    if not records:
        return DAL.BIND_NO_RESULT
    if rejected:
        if any("no website at all" in r["why"] for r in rejected):
            return DAL.BIND_NO_WEBSITE
        return DAL.BIND_REJECTED_URL_SHAPE
    if not any(r.website_url for r in records):
        return DAL.BIND_NO_WEBSITE
    return DAL.BIND_NO_SANCTIONED_KEY


def _brand_word(name: str) -> str:
    """The first token that is not a generic lodging word -- the brand a guest
    would say. Used only as a tripwire, never as a binding key."""
    for token in URC.presentation_key(name, state_code="IN").split():
        if token not in URC._GENERIC_NAME_WORDS:
            return token
    return ""


def build_cohort() -> List[Dict]:
    inventory = json.loads(
        (LP / "indianapolis_in_url_recovery_report_006.json").read_text(encoding="utf-8")
    )["phase_1_unroutable_inventory"]["rows"]
    sampled = {r["identity_key"] for r in json.loads(
        (LP / "indianapolis_in_discovery_replay_007.json").read_text(encoding="utf-8")
    )["qualification_sample"]["rows"]}
    if len(inventory) != UNIVERSE:
        raise SystemExit("the committed unroutable universe is %d, not %d"
                         % (len(inventory), UNIVERSE))
    if len(sampled) != ALREADY_ATTEMPTED:
        raise SystemExit("the committed sample is %d rows, not %d"
                         % (len(sampled), ALREADY_ATTEMPTED))
    remaining = [r for r in inventory if r["identity_key"] not in sampled]
    if len(remaining) != UNIVERSE - ALREADY_ATTEMPTED:
        raise SystemExit("%d - %d did not leave %d"
                         % (UNIVERSE, ALREADY_ATTEMPTED, MAX_REQUESTS))
    return remaining


def run(*, live: bool) -> Dict:
    remaining = build_cohort()
    field_mask = tuple(C.GOOGLE_FIELD_MASK.split(","))
    ledger = DAL.load(LEDGER_PATH)

    census_rows = [_census_row(r) for r in remaining]
    payable, suppressed = DAL.suppress(census_rows, ledger, provider="GOOGLE_PLACES",
                                       method="searchText", field_mask=field_mask)
    if len(payable) + len(suppressed) != len(remaining):
        raise SystemExit("the ledger split is not a partition of the remaining "
                         "universe; refusing to spend")
    if len(payable) > MAX_REQUESTS:
        raise SystemExit("payable %d exceeds the authorised cap %d"
                         % (len(payable), MAX_REQUESTS))

    budget = RequestBudget(max_requests=MAX_REQUESTS)
    cache = DiscoveryCache(CACHE_DIR)
    client = GooglePlacesClient()
    observed_at = _now()[:10]
    by_key = {r["identity_key"]: r for r in remaining}

    results: List[Dict] = []
    new_records: List[Dict] = []
    aborted = ""
    brand_disagreements: List[Dict] = []

    for census in payable:
        row = by_key[census["identity_key"]]
        if not live:
            results.append(OrderedDict((
                ("identity_key", census["identity_key"]), ("dry_run", True),
                ("query", _query(row)), ("requests_made", 0))))
            continue
        if not budget.can_spend(1):
            aborted = "REQUEST_BUDGET_EXHAUSTED"
            break

        query = DiscoverySourceQuery(
            query_id=census["identity_key"].replace(" ", "-")[:80],
            provider=C.PROVIDER_GOOGLE_PLACES, canonical_category="lodging",
            query_text=_query(row), market_id=MARKET, max_pages=1)
        outcome = client.search(query, cache=cache, budget=budget,
                                observed_at=observed_at)
        records = list(outcome.records)
        observation, binding, rejected, matched = _bind(census, records)
        state = _bind_state(observation, binding, records, rejected)
        bound = state == DAL.BIND_BOUND
        url = MR.normalize_source_url(observation.url) if observation else ""
        place_id = getattr(matched, "provider_record_id", "") if matched else ""
        returned_name = getattr(matched, "name", "") if matched else ""

        if bound:
            want, got = _brand_word(census["canonical_name"]), _brand_word(returned_name)
            if want and got and want != got:
                brand_disagreements.append(OrderedDict((
                    ("identity_key", census["identity_key"]),
                    ("census_brand", want), ("returned_brand", got),
                    ("returned_name", returned_name), ("bind_method", binding))))

        results.append(OrderedDict((
            ("identity_key", census["identity_key"]),
            ("canonical_name", census["canonical_name"]),
            ("family", row.get("family", "")),
            ("query", _query(row)),
            ("query_fingerprint", DAL.query_fingerprint(
                census, provider="GOOGLE_PLACES", method="searchText",
                field_mask=field_mask)),
            ("requests_made", outcome.requests_made),
            ("places_returned", len(records)),
            ("place_id", place_id),
            ("returned_name", returned_name),
            ("returned_address", getattr(matched, "address_line", "") if matched else ""),
            ("returned_postal_code",
             (getattr(matched, "postal_code", "") or
              _postal_of(getattr(matched, "address_line", ""))) if matched else ""),
            ("returned_phone", getattr(matched, "phone", "") if matched else ""),
            ("website_uri", url),
            ("bind_method", binding), ("bind_state", state), ("bound", bound),
            ("official_property_url_candidate", url if bound else ""),
            ("url_shape", MR.classify_url_shape(url) if url else ""),
            ("routing_state", "ROUTABLE" if bound else "UNROUTED"),
            ("refusal_reason", "" if bound else
             (rejected[0]["why"] if rejected else
              "no returned place matched on a sanctioned key")),
        )))

        new_records.append(DAL.build_attempt(
            census, market_id=MARKET, work_order=WORK_ORDER, run_id=RUN_ID,
            provider="GOOGLE_PLACES", method="searchText", field_mask=field_mask,
            attempted_at=_now(), place_id=place_id, website_uri=url,
            national_phone_number=getattr(matched, "phone", "") if matched else "",
            bind_state=state, bind_method=binding,
            bind_result=results[-1]["refusal_reason"] or "bound on %s" % binding,
            outcome=state,
            cache_pointer=CACHE_DIR.relative_to(_REPO_ROOT).as_posix(),
            paid_requests=outcome.requests_made, cost_usd_minor=None))

        if len(brand_disagreements) >= BRAND_DISAGREEMENT_LIMIT:
            aborted = "SYSTEMATIC_BRAND_DISAGREEMENT"
            break

    if live and new_records:
        DAL.save(LEDGER_PATH, DAL.merge(ledger, new_records))

    executed = [r for r in results if r.get("requests_made")]
    bound_rows = [r for r in executed if r.get("bound")]
    place_ids = Counter(r["place_id"] for r in bound_rows if r["place_id"])

    return OrderedDict((
        ("schema", SCHEMA), ("market_id", MARKET), ("work_order", WORK_ORDER),
        ("run_id", RUN_ID), ("live", live),
        ("preflight", OrderedDict((
            ("universe", UNIVERSE), ("already_attempted", ALREADY_ATTEMPTED),
            ("remaining", len(remaining)),
            ("ledger_attempts_before", len(ledger.get("attempts") or ())),
            ("payable", len(payable)), ("suppressed_before_run", len(suppressed)),
            ("partition_holds", len(payable) + len(suppressed) == len(remaining)),
            ("presentation_variants", True),
        ))),
        ("authorised_request_cap", MAX_REQUESTS),
        ("requests_made", budget.used),
        ("cap_held", budget.used <= MAX_REQUESTS),
        ("aborted", aborted),
        ("brand_disagreements", brand_disagreements),
        ("totals", OrderedDict((
            ("executed", len(executed)), ("bound", len(bound_rows)),
            ("bind_rate", round(len(bound_rows) / len(executed), 4) if executed else None),
            ("by_bind_method", OrderedDict(sorted(
                Counter(r["bind_method"] for r in bound_rows).items()))),
            ("by_bind_state", OrderedDict(sorted(
                Counter(r["bind_state"] for r in executed).items()))),
        ))),
        ("official_property_urls_recovered", [OrderedDict((
            ("identity_key", r["identity_key"]), ("url", r["website_uri"]),
            ("bind_method", r["bind_method"]))) for r in bound_rows]),
        ("place_id_collisions", {p: c for p, c in place_ids.items() if c > 1}),
        ("ledger_rows_written", len(new_records)),
        ("duplicate_discovery_attempts_prevented", len(suppressed)),
        ("rows", results),
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--out", default="")
    args = parser.parse_args(argv)
    if args.live and not os.environ.get(C.GOOGLE_PLACES_API_KEY_ENV, "").strip():
        raise SystemExit("no %s in the environment" % C.GOOGLE_PLACES_API_KEY_ENV)
    report = run(live=args.live)
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    pre = report["preflight"]
    print("preflight   %d - %d = %d, partition %s, payable %d, suppressed %d"
          % (pre["universe"], pre["already_attempted"], pre["remaining"],
             pre["partition_holds"], pre["payable"], pre["suppressed_before_run"]))
    print("requests    %d / %d  (cap held %s)  aborted: %s"
          % (report["requests_made"], report["authorised_request_cap"],
             report["cap_held"], report["aborted"] or "no"))
    print("bound       %d of %d  rate=%s"
          % (report["totals"]["bound"], report["totals"]["executed"],
             report["totals"]["bind_rate"]))
    print("by state    %s" % dict(report["totals"]["by_bind_state"]))
    print("brand disagreements %d" % len(report["brand_disagreements"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
