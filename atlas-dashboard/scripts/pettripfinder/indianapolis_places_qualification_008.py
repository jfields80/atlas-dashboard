# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-PLACES-QUALIFICATION-008 -- 25 targeted Places lookups, and no more.

A controlled experiment, not a discovery run. It asks one question: can a paid
Google Places lookup reliably recover an OFFICIAL property URL for an
Indianapolis identity that has none? 143 rows are waiting on the answer, and
118 of them will not be touched until a human reads this report.

WHAT KEEPS IT HONEST
--------------------
Nothing here re-derives a matching rule. Binding is
``census_url_recovery.bind`` -- the committed function, with its committed
hierarchy: telephone, then name-and-postal-code, and street only if a caller
opts in, which this one does not. URL acceptability is
``market_routing.classify_url_shape`` against ``ROUTABLE_SHAPES``, so a booking
aggregator or a brand index is refused as loudly as it is elsewhere. Corroboration
is ``url_names_the_property``, so a returned page must NAME the hotel and not
merely resemble it.

THE TWO CONTROLS ARE THE POINT
-------------------------------
"aloft" and "ashley motel" are bare names that identify no building. They are in
the sample because they SHOULD NOT bind. If either does, the rule is too
permissive, the run stops where it stands, and the other 118 are not bought --
which is a cheaper thing to learn at 25 requests than at 143.

THE CAP
-------
One ``RequestBudget(max_requests=25)`` is shared by every query and each query
asks for one page. The budget is the enforceable ceiling; there is no USD meter
on this path and this module does not pretend otherwise.
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
from scripts.pettripfinder.discovery import constants as C                     # noqa: E402
from scripts.pettripfinder.discovery import census_url_recovery as URC         # noqa: E402
from scripts.pettripfinder.discovery import identity_dedup as DEDUP            # noqa: E402
from scripts.pettripfinder.discovery.cache import DiscoveryCache               # noqa: E402
from scripts.pettripfinder.discovery.google_places import GooglePlacesClient   # noqa: E402
from scripts.pettripfinder.discovery.models import DiscoverySourceQuery        # noqa: E402
from scripts.pettripfinder.discovery.query_plan import RequestBudget           # noqa: E402

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
LEDGER_PATH = LP / "ptf_discovery_attempt_ledger_001.json"
SAMPLE_DOC = "indianapolis_in_discovery_replay_007.json"
CACHE_DIR = _REPO_ROOT / "data" / "discovery" / "indianapolis_places_008" / "cache"

SCHEMA = "ptf-places-qualification-run/1.0"
WORK_ORDER = "PTF-INDIANAPOLIS-PLACES-QUALIFICATION-008"
RUN_ID = "indianapolis-in-places-008"
MARKET = "indianapolis-in"

#: The authorised ceiling. The only control on this path that is enforced by
#: code rather than by intention.
MAX_REQUESTS = 25

CONTROLS = ("aloft", "ashley motel")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_of(sample_row: Dict) -> Dict:
    """The census-shaped row the committed binder and ledger both expect."""
    evidence = sample_row["binding_evidence_available"]
    return {
        "identity_key": sample_row["identity_key"],
        "canonical_name": sample_row["canonical_name"],
        "address": evidence["street"], "street": evidence["street"],
        "city": evidence["city"], "state": "IN",
        "postal_code": evidence["postal_code"],
        "phone": evidence["telephone"], "telephone": evidence["telephone"],
        "official_url": "",
    }


def _observations(records) -> List[URC.Observation]:
    """Places results, reduced to what the committed binder can read."""
    out = []
    for record in records:
        out.append(URC.Observation(
            provider=C.PROVIDER_GOOGLE_PLACES,
            source="places:%s" % (record.provider_record_id or "?"),
            name=record.name, phone=record.phone,
            postal=record.postal_code, url=record.website_url,
            street=record.address_line))
    return out


def _bind(row: Dict, records) -> Tuple[Optional[object], str, List[Dict], Optional[object]]:
    """``(observation, binding, rejections, record)`` using the COMMITTED rule.

    ``unambiguous_streets`` is deliberately left at ``None``: street-and-postal
    is an opt-in third key and this experiment measures the two the project
    already relies on.
    """
    observations = _observations(records)
    by_url = {o.url: r for o, r in zip(observations, records)}

    def acceptable(observation) -> Tuple[bool, str]:
        url = MR.normalize_source_url(observation.url)
        if not url:
            return (False, "the place carries no website at all")
        shape = MR.classify_url_shape(url)
        if shape not in MR.ROUTABLE_SHAPES:
            return (False, "the website is a %s, which no lane can fetch as "
                           "this hotel's page" % shape)
        return URC.url_names_the_property(row.get("canonical_name", ""), url)

    rejections: List[Dict] = []
    observation, binding = URC.bind(row, observations, unambiguous_streets=None,
                                    acceptable=acceptable, rejected=rejections)
    record = by_url.get(observation.url) if observation is not None else None
    return (observation, binding, rejections, record)


def _bind_state(observation, binding: str, records, rejections) -> str:
    if observation is not None and binding:
        return DAL.BIND_BOUND
    if not records:
        return DAL.BIND_NO_RESULT
    if rejections:
        shapes = " ".join(r["why"] for r in rejections)
        if "no website at all" in shapes:
            return DAL.BIND_NO_WEBSITE
        return DAL.BIND_REJECTED_URL_SHAPE
    if not any(r.website_url for r in records):
        return DAL.BIND_NO_WEBSITE
    return DAL.BIND_NO_SANCTIONED_KEY


def run(*, live: bool) -> Dict:
    sample = json.loads((LP / SAMPLE_DOC).read_text(encoding="utf-8"))
    rows = sample["qualification_sample"]["rows"]
    field_mask = tuple(sample["field_mask"])
    provider, method = sample["provider"], sample["discovery_method"]

    if len(rows) != MAX_REQUESTS:
        raise SystemExit("the committed sample is %d rows, not %d; refusing to "
                         "run a sample that is not the authorised one"
                         % (len(rows), MAX_REQUESTS))

    ledger = DAL.load(LEDGER_PATH)
    index = DAL.DiscoveryIndex(ledger)
    budget = RequestBudget(max_requests=MAX_REQUESTS)
    cache = DiscoveryCache(CACHE_DIR)
    client = GooglePlacesClient()
    observed_at = _now()[:10]

    results: List[Dict] = []
    new_records: List[Dict] = []
    aborted = ""
    suppressed_duplicates = 0

    for sample_row in rows:
        row = _row_of(sample_row)
        key = row["identity_key"]
        expected = sample_row["expected_binding_method"]
        fingerprint = DAL.query_fingerprint(row, provider=provider, method=method,
                                            field_mask=field_mask)

        # The ledger is consulted BEFORE the money, every time.
        decision = DAL.decide(row, index, provider=provider, method=method,
                              field_mask=field_mask)
        if decision["decision"] not in DAL.ALLOWED_DECISIONS:
            suppressed_duplicates += 1
            results.append(OrderedDict((
                ("identity_key", key), ("expected_binding_method", expected),
                ("query_fingerprint", fingerprint),
                ("suppressed_by_ledger", True),
                ("decision", decision["decision"]), ("reason", decision["reason"]),
                ("requests_made", 0),
            )))
            continue

        query = DiscoverySourceQuery(
            query_id=key.replace(" ", "-")[:80], provider=C.PROVIDER_GOOGLE_PLACES,
            canonical_category="lodging", query_text=sample_row["query"],
            market_id=MARKET, max_pages=1)

        if not live:
            results.append(OrderedDict((
                ("identity_key", key), ("expected_binding_method", expected),
                ("query", sample_row["query"]),
                ("query_fingerprint", fingerprint),
                ("dry_run", True), ("requests_made", 0),
            )))
            continue

        if not budget.can_spend(1):
            aborted = "REQUEST_BUDGET_EXHAUSTED"
            break

        outcome = client.search(query, cache=cache, budget=budget,
                                observed_at=observed_at)
        records = list(outcome.records)
        observation, binding, rejections, matched = _bind(row, records)
        state = _bind_state(observation, binding, records, rejections)
        bound = state == DAL.BIND_BOUND

        website = MR.normalize_source_url(observation.url) if observation else ""
        place_id = getattr(matched, "provider_record_id", "") if matched else ""
        result = OrderedDict((
            ("identity_key", key), ("canonical_name", row["canonical_name"]),
            ("family", sample_row["family"]),
            ("expected_binding_method", expected),
            ("query", sample_row["query"]), ("query_fingerprint", fingerprint),
            ("provider_state", outcome.state),
            ("requests_made", outcome.requests_made),
            ("cache_hits", outcome.cache_hits),
            ("places_returned", len(records)),
            ("returned", [OrderedDict((
                ("place_id", r.provider_record_id), ("name", r.name),
                ("address", r.address_line), ("phone", r.phone),
                ("website_uri", r.website_url),
                ("business_status", r.business_status),
            )) for r in records]),
            ("bound", bound), ("bind_method", binding),
            ("bind_state", state),
            ("place_id", place_id),
            ("returned_business_name", getattr(matched, "name", "") if matched else ""),
            ("returned_address", getattr(matched, "address_line", "") if matched else ""),
            ("returned_phone", getattr(matched, "phone", "") if matched else ""),
            ("website_uri", website),
            ("official_property_url_candidate", website if bound else ""),
            ("url_shape", MR.classify_url_shape(website) if website else ""),
            ("routing_becomes_usable", bool(bound and website)),
            ("binding_signals", OrderedDict((
                ("census_phone", URC.digits(row["phone"])),
                ("census_postal", row["postal_code"]),
                ("census_name", URC.normalise(row["canonical_name"])),
                ("matched_phone", getattr(matched, "phone", "") if matched else ""),
                ("matched_postal", getattr(matched, "postal_code", "") if matched else ""),
                ("names_compatible", DEDUP.names_compatible(
                    DAL.normalized_name(row),
                    URC.normalise(getattr(matched, "name", "")) if matched else "")),
            ))),
            ("rejections", rejections),
            ("reason", "bound on %s" % binding if bound else
                       (rejections[0]["why"] if rejections else
                        "no returned place matched on a sanctioned key")),
            ("measured_cost_usd", None),
        ))
        results.append(result)

        new_records.append(DAL.build_attempt(
            row, market_id=MARKET, work_order=WORK_ORDER, run_id=RUN_ID,
            provider=provider, method=method, field_mask=field_mask,
            attempted_at=_now(), place_id=place_id, website_uri=website,
            national_phone_number=getattr(matched, "phone", "") if matched else "",
            bind_state=state, bind_method=binding,
            bind_result=result["reason"], outcome=state,
            cache_pointer=CACHE_DIR.relative_to(_REPO_ROOT).as_posix(),
            paid_requests=outcome.requests_made, cost_usd_minor=None))

        # THE CONTROL. A bare name that binds means the rule is too permissive,
        # and every remaining request would be spent on a rule we no longer
        # trust.
        if key in CONTROLS and bound:
            aborted = "FAILURE_CONTROL_BOUND"
            break

    if live and new_records:
        DAL.save(LEDGER_PATH, DAL.merge(ledger, new_records))

    executed = [r for r in results if r.get("requests_made")]
    bound_rows = [r for r in executed if r.get("bound")]
    by_expected = lambda group: [r for r in executed  # noqa: E731
                                 if r["expected_binding_method"] == group]

    def rate(rows_):
        got = [r for r in rows_ if r.get("bound")]
        return OrderedDict((("attempted", len(rows_)), ("bound", len(got)),
                            ("rate", round(len(got) / len(rows_), 4) if rows_ else None)))

    place_ids = Counter(r["place_id"] for r in bound_rows if r.get("place_id"))
    collisions = {p: c for p, c in place_ids.items() if c > 1}

    return OrderedDict((
        ("schema", SCHEMA), ("market_id", MARKET), ("work_order", WORK_ORDER),
        ("run_id", RUN_ID), ("live", live),
        ("authorised_request_cap", MAX_REQUESTS),
        ("requests_made", budget.used),
        ("cap_held", budget.used <= MAX_REQUESTS),
        ("aborted", aborted),
        ("suppressed_duplicate_queries", suppressed_duplicates),
        ("ledger_rows_written", len(new_records)),
        ("totals", OrderedDict((
            ("executed", len(executed)), ("bound", len(bound_rows)),
            ("overall", rate(executed)),
            ("PHONE", rate(by_expected("PHONE"))),
            ("NAME_AND_POSTAL_CODE", rate(by_expected("NAME_AND_POSTAL_CODE"))),
            ("EXPECTED_TO_FAIL", rate(by_expected("EXPECTED_TO_FAIL"))),
        ))),
        ("official_property_urls_recovered",
         [OrderedDict((("identity_key", r["identity_key"]),
                       ("url", r["official_property_url_candidate"]),
                       ("bind_method", r["bind_method"])))
          for r in bound_rows]),
        ("identities_made_routable", sum(1 for r in bound_rows
                                         if r["routing_becomes_usable"])),
        ("place_id_collisions", collisions),
        ("measured_billing", None),
        ("rows", results),
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true",
                        help="actually call the provider; without it nothing "
                             "is fetched and no budget is spent")
    parser.add_argument("--out", default="")
    args = parser.parse_args(argv)
    if args.live and not os.environ.get(C.GOOGLE_PLACES_API_KEY_ENV, "").strip():
        raise SystemExit("no %s in the environment" % C.GOOGLE_PLACES_API_KEY_ENV)
    report = run(live=args.live)
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("live                %s" % report["live"])
    print("requests made       %d / %d  (cap held: %s)"
          % (report["requests_made"], report["authorised_request_cap"],
             report["cap_held"]))
    print("aborted             %s" % (report["aborted"] or "no"))
    print("ledger rows written %d" % report["ledger_rows_written"])
    for group in ("overall", "PHONE", "NAME_AND_POSTAL_CODE", "EXPECTED_TO_FAIL"):
        stat = report["totals"][group]
        print("  %-22s %s/%s  rate=%s"
              % (group, stat["bound"], stat["attempted"], stat["rate"]))
    print("routable identities %d" % report["identities_made_routable"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
