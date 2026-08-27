# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-PAID-OFFICIAL-URL-DISCOVERY-007 -- what buying the 143 URLs would cost.

Indianapolis is not short of pet-friendly profiles because of budget, readers or
routing bugs. It is short because 143 of its 257 identities name no website, and
006 proved no free evidence names one. The remaining lever is a PAID discovery
lookup: ask a places provider for the property and read back its ``websiteUri``.

This module plans that purchase. IT SPENDS NOTHING AND CALLS NO PROVIDER.

TWO THINGS IT REFUSES TO INVENT
-------------------------------
A UNIT PRICE. This repo budgets Google Places in REQUESTS -- ``RequestBudget``
counts calls, and no USD rate for Places is recorded anywhere in it. The field
mask that makes this work at all (``places.websiteUri`` plus
``places.nationalPhoneNumber``) is what puts the call in a higher-priced Google
SKU, and which price that is depends on the operator's own Google Cloud
contract and monthly allotment. So the plan is denominated in requests and the
USD line is left for the operator to fill from their billing console.

A YIELD. The only time this project ever recovered a URL from Google Places was
St. Louis, which got 5 -- and all five bound on TELEPHONE. Only 5 of these 143
rows state a telephone. That single number is the reason this plan opens with a
sample instead of a cohort: the honest expected yield here is UNKNOWN, and
Option A exists to measure it rather than to guess it.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.cincinnati_url_routing_progress_001 import brand_of  # noqa: E402
from scripts.pettripfinder.discovery import constants as C                      # noqa: E402

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
SCHEMA = "ptf-market-url-discovery-plan/1.0"
WORK_ORDER = "PTF-INDIANAPOLIS-PAID-OFFICIAL-URL-DISCOVERY-007"
MARKET = "indianapolis-in"

#: One targeted text search per identity. The provider returns up to
#: GOOGLE_PAGE_SIZE places for it, so a single call is enough to find one hotel;
#: nothing here plans a second page.
REQUESTS_PER_IDENTITY = 1

#: Option A. Big enough that a measured hit rate means something and small
#: enough to abandon cheaply, stratified so the answer is not one brand's luck.
SAMPLE_SIZE = 25


def _load(name):
    return json.loads((LP / name).read_text(encoding="utf-8"))


def build() -> Dict:
    report = _load("indianapolis_in_url_recovery_report_006.json")
    census = _load("identity_census/indianapolis-in.json")
    ledger = _load("ptf_paid_attempt_ledger_001.json")
    rows = report["phase_1_unroutable_inventory"]["rows"]
    by_key = {h["identity_key"]: h for h in census["hotels"]}

    # ---- what the ledger can and cannot tell us about discovery spend -------
    lanes = sorted({a["lane"] for a in ledger["attempts"] if a["lane"]})
    cache_root = _REPO_ROOT / "data" / "discovery" / "indianapolis_rebuild_002" / "cache"
    cached_providers = sorted(p.name for p in cache_root.iterdir()) if cache_root.is_dir() else []

    # ---- binding readiness, which is the whole risk ------------------------
    with_phone = [r for r in rows if (r.get("telephone") or "").strip()]
    with_name_and_postal = [r for r in rows
                            if (r.get("canonical_name") or "").strip()
                            and (r.get("postal_code") or "").strip()]
    bare_name = [r for r in rows
                 if len((r.get("canonical_name") or "").split()) <= 2]

    families = Counter(r["family"] for r in rows)
    # Stratify the sample by family, largest first, at least one from each.
    sample: List[Dict] = []
    per_family = {f: max(1, round(SAMPLE_SIZE * n / len(rows))) for f, n in families.items()}
    for family, _count in families.most_common():
        picks = [r for r in rows if r["family"] == family][:per_family[family]]
        for pick in picks:
            if len(sample) < SAMPLE_SIZE:
                sample.append(pick)
    # Prefer rows that carry a telephone: they are the only ones that can bind
    # on the strong key, so they measure the ceiling as well as the floor.
    phone_keys = {r["identity_key"] for r in with_phone}
    sample.sort(key=lambda r: (r["identity_key"] not in phone_keys, r["family"]))

    options = OrderedDict((
        ("A_qualification_sample", OrderedDict((
            ("identities", len(sample)),
            ("provider_requests", len(sample) * REQUESTS_PER_IDENTITY),
            ("purpose", "measure the hit rate and, more importantly, the BIND "
                        "rate: how often a returned websiteUri can be attached "
                        "to the census row on a sanctioned key rather than on a "
                        "name that merely looks right"),
            ("stratified_by_family", OrderedDict(sorted(
                Counter(r["family"] for r in sample).items()))),
            ("carries_a_telephone",
             sum(1 for r in sample if r["identity_key"] in phone_keys)),
            ("decision_it_unlocks",
             "if the bind rate is high, Option C is worth authorising; if it is "
             "near zero, the 143 are not recoverable by this method at any "
             "price and the target has to be met another way"),
        ))),
        ("B_enough_to_unlock_about_30_candidates", OrderedDict((
            ("identities", None), ("provider_requests", None),
            ("why_it_cannot_be_sized_yet",
             "sizing this needs a bind rate, and no measurement of a TARGETED "
             "per-identity Places lookup exists for any market. Naming a number "
             "here would be a fabricated yield, which this work order forbids. "
             "Option A produces the rate that sizes Option B."),
        ))),
        ("C_full_cohort", OrderedDict((
            ("identities", len(rows)),
            ("provider_requests", len(rows) * REQUESTS_PER_IDENTITY),
            ("note", "the whole unroutable pool in one pass; cheapest per row "
                     "and the only option that can close the gap, but it buys "
                     "138 lookups whose binding key is unproven"),
        ))),
    ))

    return OrderedDict((
        ("schema", SCHEMA), ("market_id", MARKET), ("work_order", WORK_ORDER),
        ("nothing_was_fetched", True), ("usd_spent", 0.0), ("provider_calls", 0),
        ("this_is_not_an_authorization", True),
        ("url_less_identities", len(rows)),
        ("method", OrderedDict((
            ("provider", "GOOGLE_PLACES"),
            ("product", "Google Places API (New) Text Search"),
            ("endpoint", C.GOOGLE_SEARCH_TEXT_URL),
            ("implemented_in", "scripts/pettripfinder/discovery/google_places.py"),
            ("credential_present", True),
            ("field_that_answers_this", "places.websiteUri"),
            ("field_that_binds_it", "places.nationalPhoneNumber"),
            ("field_mask", C.GOOGLE_FIELD_MASK.split(",")),
            ("requests_per_identity", REQUESTS_PER_IDENTITY),
            ("query_shape", "canonical name + street + city + state + postal code"),
            ("why_this_one", "it is the only implemented provider in this repo "
                             "that returns a first-party website for a named "
                             "property. The three acquisition providers "
                             "(brightdata_browser, brightdata_web_unlocker, "
                             "firecrawl) all FETCH a page you already have a URL "
                             "for; none of them can find one."),
            ("rejected_url_shapes", OrderedDict((
                ("third_party_booking", sorted(C.THIRD_PARTY_BOOKING_DOMAINS)),
                ("social_or_directory", sorted(C.SOCIAL_OR_DIRECTORY_DOMAINS)),
            ))),
        ))),
        ("repeat_spend_guard", OrderedDict((
            ("paid_attempt_ledger_lanes", lanes),
            ("ledger_covers_discovery_lookups", False),
            ("already_paid_reusable_discovery_lookups", 0),
            ("true_new_paid_lookup_cohort", len(rows)),
            ("discovery_cache_providers_present", cached_providers),
            ("discovery_idempotency",
             "the discovery layer has its OWN guard: cache.py stores raw "
             "responses under a sha256 request fingerprint, so an identical "
             "query inside the retention window is served from disk and costs "
             "nothing."),
            ("google_cache_retention_days", C.GOOGLE_CACHE_RETENTION_DAYS),
            ("THE GAP", "the cross-run paid-attempt ledger records only "
                        "brightdata_browser, brightdata_web_unlocker and "
                        "firecrawl -- POLICY fetches. A discovery lookup is "
                        "invisible to it. Buy these 143 today and a re-census "
                        "in six weeks, past the %d-day cache retention, will "
                        "buy them again under renamed keys, which is precisely "
                        "the failure PTF-GENERIC-CROSS-RUN-PAID-ATTEMPT-LEDGER-001 "
                        "was written to end. Extend the ledger with a discovery "
                        "lane BEFORE authorising any spend."
                        % C.GOOGLE_CACHE_RETENTION_DAYS),
        ))),
        ("unit_cost", OrderedDict((
            ("denominated_in", "provider requests"),
            ("usd_per_request", None),
            ("recorded_in_this_repo", False),
            ("why_unknown", "no USD rate for Google Places is recorded anywhere "
                            "in this repository -- RequestBudget counts calls, "
                            "not dollars. The field mask requests websiteUri and "
                            "nationalPhoneNumber, which places the call in a "
                            "higher-priced Google SKU than an id-only search, and "
                            "the applicable rate depends on the operator's Google "
                            "Cloud contract and monthly free allotment. This must "
                            "be read from the billing console before authorising; "
                            "it is not a number to estimate."),
            ("what_to_confirm", "the per-1000 price of Places API (New) Text "
                                "Search at a field mask that includes "
                                "websiteUri, and the remaining monthly allotment"),
        ))),
        ("binding_readiness", OrderedDict((
            ("identities", len(rows)),
            ("can_bind_on_telephone", len(with_phone)),
            ("must_bind_on_name_and_postal", len(rows) - len(with_phone)),
            ("carry_a_bare_two_word_name", len(bare_name)),
            ("sanctioned_keys", ["PHONE", "NAME_AND_POSTAL_CODE",
                                 "STREET_AND_POSTAL_CODE (corroboration required)"]),
            ("the_risk", "every URL St. Louis ever recovered from Google Places "
                         "-- all 5 of them -- bound on TELEPHONE, and only %d of "
                         "these %d rows state one. The other %d must bind on name "
                         "and postal code, which is untested for this provider, "
                         "and %d of them carry a bare two-word name like 'Comfort "
                         "Suites' that names no building at all."
                         % (len(with_phone), len(rows), len(rows) - len(with_phone),
                            len(bare_name))),
        ))),
        ("expected_yield", OrderedDict((
            ("targeted_lookup_hit_rate", "UNKNOWN"),
            ("targeted_lookup_bind_rate", "UNKNOWN"),
            ("basis", "no market has ever run a TARGETED per-identity Places "
                      "lookup, so there is no measurement to extrapolate from."),
            ("the_one_historical_datum", OrderedDict((
                ("market", "st-louis-mo"),
                ("artifact", "st_louis_mo_url_recovery_002.json"),
                ("url_less_rows", 60), ("recovered", 5),
                ("rate", 0.083),
                ("binding_counts", {"PHONE": 5}),
                ("why_it_does_not_transfer",
                 "that was MINING a cache built by broad area searches for a "
                 "census pass, not asking the provider about one named hotel. "
                 "The operations differ, so the rate does not carry across -- "
                 "a targeted lookup should do better, and saying how much "
                 "better without measuring it is the fabrication this work "
                 "order rules out."),
            ))),
        ))),
        ("options", options),
        ("worst_case", OrderedDict((
            ("full_cohort_requests", len(rows) * REQUESTS_PER_IDENTITY),
            ("worst_case_outcome", "143 requests billed and 0 usable URLs bound "
                                   "-- the provider answers, but the answers "
                                   "cannot be attached to a census row on a "
                                   "sanctioned key, or every answer is an OTA "
                                   "or directory page"),
            ("what_bounds_it", "RequestBudget caps the run at a request count "
                               "the operator sets, and every response is cached "
                               "under its fingerprint, so a failed run is never "
                               "paid for twice inside the retention window"),
        ))),
        ("rows", rows),
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="")
    args = parser.parse_args(argv)
    plan = build()
    if args.out:
        Path(args.out).write_text(json.dumps(plan, indent=2), encoding="utf-8")
    print("url-less identities        %d" % plan["url_less_identities"])
    print("true new paid cohort       %d" % plan["repeat_spend_guard"]["true_new_paid_lookup_cohort"])
    print("provider                   %s" % plan["method"]["product"])
    print("usd per request            %s" % plan["unit_cost"]["usd_per_request"])
    print("can bind on telephone      %d" % plan["binding_readiness"]["can_bind_on_telephone"])
    print("must bind on name+postal   %d" % plan["binding_readiness"]["must_bind_on_name_and_postal"])
    print("expected yield             %s" % plan["expected_yield"]["targeted_lookup_bind_rate"])
    for name, opt in plan["options"].items():
        print("  %-38s identities=%s requests=%s"
              % (name, opt["identities"], opt["provider_requests"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
