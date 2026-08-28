# -*- coding: utf-8 -*-
"""PTF-GRAND-RAPIDS-HOLLAND-PLACES-PILOT-026 -- 20 Google Places lookups, and no more.

A measurement, not a recovery run. Grand Rapids / Holland holds 76 identities
that name no website, and 025 proved the market cannot reach 43 published
hotels without buying URLs for most of them. Nobody knows what a Places lookup
recovers HERE: the only rate this project owns is Indianapolis's 34 of 118, and
025 said so in the same breath as it used it. Twenty requests buy that number
for this market.

WHAT THIS MODULE DOES NOT DECIDE
---------------------------------
The cohort. ``grand_rapids_holland_places_cohort_026`` chose the twenty rows
before a cent was spent and wrote them to a committed document; this runner
reads that file and REFUSES to execute a cohort of any other length. A sample
chosen while the run executes is a sample that can be steered.

The matching rules. Binding is ``census_url_recovery.bind`` with its committed
hierarchy -- telephone, then name-and-postal-code, street left opted out. URL
acceptability is ``market_routing.classify_url_shape`` against
``ROUTABLE_SHAPES``. Corroboration is ``url_names_the_property``. The
dual-brand refusal ``names_may_share_a_url`` runs inside ``bind`` on every
candidate, which is what stops a Comfort Inn taking a Comfort Suites page.

ONE THING IS NEW HERE, AND IT IS OPT-IN
----------------------------------------
``presentation_variants=True``. Indianapolis measured that thirteen of its
fourteen name-and-postal misses had returned a REAL property page under the
brand's current marketing name -- "Fairfield by Marriott Inn & Suites" against
a census that says "Fairfield Inn & Suites". ``presentation_key`` closes that
gap with three named transformations and nothing else: ``by <operator>``
dropped, a bare state code dropped, one chain re-presentation table. It widens
what counts as the SAME name. It does not widen what may lend a URL to what --
``names_may_share_a_url`` still runs, and airport, downtown, the compass words
and every locality still separate two buildings.

There is no fuzzy matching in this module, no embedding, and no similarity
threshold. Every comparison is token equality.

THE CAP
-------
One ``RequestBudget(max_requests=20)``, shared by every query, one page per
query. The budget is the ceiling the code enforces; the twenty-row cohort is
the ceiling the document enforces. There is no USD meter on this path and this
module does not invent one -- ``measured_cost_usd`` stays ``None`` on every row.

STOPPING EARLY
--------------
A wrong binding that repeats is worth more than the remaining requests. Two
signals stop the run where it stands:

  PLACE_ID_COLLISION      two identities bound to one Google place. One of them
                          is the wrong hotel, and the rule that did it would do
                          it again on the other 56.
  PREMISES_DISAGREEMENT   two bound places state a street number or postal code
                          that contradicts the census row. One can be a census
                          error; two is a pattern.

Both are checked after every request, and either one aborts before the next.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import discovery_attempt_ledger as DAL  # noqa: E402
from scripts.pettripfinder.acquisition import market_routing as MR             # noqa: E402
from scripts.pettripfinder.cincinnati_url_routing_progress_001 import (        # noqa: E402
    street_number)
from scripts.pettripfinder.discovery import census_url_recovery as URC         # noqa: E402
from scripts.pettripfinder.discovery import constants as C                     # noqa: E402
from scripts.pettripfinder.discovery import identity_dedup as DEDUP            # noqa: E402
from scripts.pettripfinder.discovery.cache import DiscoveryCache               # noqa: E402
from scripts.pettripfinder.discovery.google_places import GooglePlacesClient   # noqa: E402
from scripts.pettripfinder.discovery.models import DiscoverySourceQuery        # noqa: E402
from scripts.pettripfinder.discovery.query_plan import RequestBudget           # noqa: E402
from scripts.pettripfinder import grand_rapids_holland_places_cohort_026 as COHORT  # noqa: E402

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
LEDGER_PATH = LP / "ptf_discovery_attempt_ledger_001.json"
COHORT_PATH = LP / "grand_rapids_holland_mi_places_pilot_cohort_026.json"
REPORT_PATH = LP / "grand_rapids_holland_mi_places_pilot_026.json"
CACHE_DIR = _REPO_ROOT / "data" / "discovery" / "grand_rapids_places_026" / "cache"

SCHEMA = "ptf-places-pilot-run/1.0"
WORK_ORDER = "PTF-GRAND-RAPIDS-HOLLAND-PLACES-PILOT-026"
RUN_ID = "grand-rapids-holland-mi-places-026"
MARKET = "grand-rapids-holland-mi"

#: The authorised ceiling. Enforced by code, not by intention.
MAX_REQUESTS = 20

#: Two of a kind is a pattern; one can be a census error.
FALSE_BINDING_THRESHOLD = 2

ABORT_PLACE_ID_COLLISION = "PLACE_ID_COLLISION"
ABORT_PREMISES_DISAGREEMENT = "SYSTEMATIC_PREMISES_DISAGREEMENT"
ABORT_BUDGET = "REQUEST_BUDGET_EXHAUSTED"

#: This market's own measured pet-friendly rate, from its paid acquisition run:
#: 34 publication-grade pet-friendly profiles out of 65 attempted properties.
#: The order requires the projection to use this and the pilot's own URL rate,
#: and nothing borrowed.
PET_FRIENDLY_SUCCESSES = 34
PET_FRIENDLY_TRIALS = 65

PUBLISHED_TODAY = 35
TARGET = 43


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
# The committed cohort
# --------------------------------------------------------------------------- #

def load_cohort(path: Optional[Path] = None) -> Dict:
    document = json.loads((path or COHORT_PATH).read_text(encoding="utf-8-sig"))
    rows = document["sample"]["rows"]
    if len(rows) != MAX_REQUESTS:
        raise SystemExit(
            "the committed cohort is %d rows and the authorisation is %d; "
            "refusing to run a sample that is not the authorised one"
            % (len(rows), MAX_REQUESTS))
    return document


def census_row(entry: Mapping) -> Dict:
    """The census-shaped row the committed binder and the ledger both read."""
    evidence = entry["binding_evidence_available"]
    return {
        "identity_key": entry["identity_key"],
        "canonical_name": entry["canonical_name"],
        "address": evidence["street"], "street": evidence["street"],
        "city": evidence["city"], "state": evidence["state"],
        "postal_code": evidence["postal_code"],
        "phone": evidence["telephone"], "telephone": evidence["telephone"],
        "official_url": "",
    }


# --------------------------------------------------------------------------- #
# Binding -- the committed rules, nothing re-derived
# --------------------------------------------------------------------------- #

def observations(records) -> List[URC.Observation]:
    return [URC.Observation(
        provider=C.PROVIDER_GOOGLE_PLACES,
        source="places:%s" % (record.provider_record_id or "?"),
        name=record.name, phone=record.phone, postal=record.postal_code,
        url=record.website_url, street=record.address_line)
        for record in records]


def bind_one(row: Mapping, records
             ) -> Tuple[Optional[URC.Observation], str, List[Dict], Optional[object]]:
    """``(observation, binding, rejections, record)``.

    ``unambiguous_streets`` stays ``None``: street-and-postal is an opt-in third
    key and this pilot measures the two the project already relies on, so the
    rate is comparable with Indianapolis's.
    """
    sightings = observations(records)
    by_url = {}
    for sighting, record in zip(sightings, records):
        by_url.setdefault(sighting.url, record)

    def acceptable(observation: URC.Observation) -> Tuple[bool, str]:
        url = MR.normalize_source_url(observation.url)
        if not url:
            return (False, "the place carries no website at all")
        shape = MR.classify_url_shape(url)
        if shape not in MR.ROUTABLE_SHAPES:
            return (False, "the website is a %s, which no lane can fetch as "
                           "this hotel's page" % shape)
        return URC.url_names_the_property(row.get("canonical_name", ""), url)

    rejections: List[Dict] = []
    observation, binding = URC.bind(
        row, sightings, unambiguous_streets=None, acceptable=acceptable,
        rejected=rejections, presentation_variants=True)
    record = by_url.get(observation.url) if observation is not None else None
    return (observation, binding, rejections, record)


def bind_state(observation, binding: str, records, rejections) -> str:
    if observation is not None and binding:
        return DAL.BIND_BOUND
    if not records:
        return DAL.BIND_NO_RESULT
    if not any(getattr(r, "website_url", "") for r in records):
        return DAL.BIND_NO_WEBSITE
    if rejections:
        if any("no website at all" in r["why"] for r in rejections):
            return DAL.BIND_NO_WEBSITE
        return DAL.BIND_REJECTED_URL_SHAPE
    return DAL.BIND_NO_SANCTIONED_KEY


def premises_agreement(row: Mapping, record) -> Dict:
    """Does the place Google returned stand where the census says the hotel is?

    RECORDED, NEVER ENFORCED. This pilot measures the committed binding rules,
    and a rule invented mid-run is a rule nothing has qualified. What the
    agreement does do is trip the early stop: two bound places that contradict
    the census on street number or postal code is the systematic false-binding
    pattern the work order asks to be watched for.
    """
    if record is None:
        return OrderedDict((("checked", False),))
    census_postal = (row.get("postal_code") or "").strip()[:5]
    place_postal = (getattr(record, "postal_code", "") or "").strip()[:5]
    census_number = street_number(row.get("address", ""))
    place_number = street_number(getattr(record, "address_line", ""))
    postal_conflict = bool(census_postal and place_postal
                           and census_postal != place_postal)
    street_conflict = bool(census_number and place_number
                           and census_number != place_number)
    return OrderedDict((
        ("checked", True),
        ("census_postal", census_postal), ("place_postal", place_postal),
        ("census_street_number", census_number),
        ("place_street_number", place_number),
        ("postal_conflict", postal_conflict),
        ("street_number_conflict", street_conflict),
        ("disagrees", postal_conflict or street_conflict),
    ))


# --------------------------------------------------------------------------- #
# The run
# --------------------------------------------------------------------------- #

def run(*, live: bool, cohort_path: Optional[Path] = None,
        work_order: str = WORK_ORDER, run_id: str = RUN_ID,
        cache_dir: Optional[Path] = None) -> Dict:
    """Execute a cohort. The defaults are 026's, and the four parameters exist
    so batch 027 runs THIS code rather than a copy of it -- the binding, the
    ledger discipline, the early stop and the arithmetic are all the ones 026
    proved, and nothing about them is re-derived per batch."""
    cache = cache_dir or CACHE_DIR
    document = load_cohort(cohort_path)
    entries = document["sample"]["rows"]
    provider, method = document["provider"], document["discovery_method"]
    field_mask = tuple(document["field_mask"])

    ledger = DAL.load(LEDGER_PATH)
    index = DAL.DiscoveryIndex(ledger)
    budget = RequestBudget(max_requests=MAX_REQUESTS)
    discovery_cache = DiscoveryCache(cache)
    client = GooglePlacesClient()
    observed_at = _now()[:10]

    results: List[Dict] = []
    new_records: List[Dict] = []
    bound_place_ids: Dict[str, str] = {}
    disagreements: List[str] = []
    aborted = ""
    abort_detail = ""
    suppressed = 0

    for entry in entries:
        row = census_row(entry)
        key = row["identity_key"]

        decision = DAL.decide(row, index, provider=provider, method=method,
                              field_mask=field_mask)
        if decision["decision"] not in DAL.ALLOWED_DECISIONS:
            suppressed += 1
            results.append(OrderedDict((
                ("identity_key", key), ("suppressed_by_ledger", True),
                ("decision", decision["decision"]),
                ("reason", decision["reason"]), ("requests_made", 0))))
            continue

        if not live:
            results.append(OrderedDict((
                ("identity_key", key), ("dry_run", True),
                ("query", entry["query"]),
                ("query_fingerprint", entry["query_fingerprint"]),
                ("ledger_decision", decision["decision"]),
                ("requests_made", 0))))
            continue

        if not budget.can_spend(1):
            aborted, abort_detail = ABORT_BUDGET, "the authorised cap is spent"
            break

        query = DiscoverySourceQuery(
            query_id=key.replace(" ", "-")[:80],
            provider=C.PROVIDER_GOOGLE_PLACES, canonical_category="lodging",
            query_text=entry["query"], market_id=MARKET, max_pages=1)
        outcome = client.search(query, cache=discovery_cache, budget=budget,
                                observed_at=observed_at)
        records = list(outcome.records)
        observation, binding, rejections, matched = bind_one(row, records)
        state = bind_state(observation, binding, records, rejections)
        bound = state == DAL.BIND_BOUND

        website = MR.normalize_source_url(observation.url) if observation else ""
        place_id = getattr(matched, "provider_record_id", "") if matched else ""
        premises = premises_agreement(row, matched)

        results.append(OrderedDict((
            ("identity_key", key), ("canonical_name", row["canonical_name"]),
            ("family", entry["family"]), ("strata", entry["strata"]),
            ("expected_binding_method", entry["expected_binding_method"]),
            ("query", entry["query"]),
            ("query_fingerprint", entry["query_fingerprint"]),
            ("provider_state", outcome.state),
            ("requests_made", outcome.requests_made),
            ("cache_hits", outcome.cache_hits),
            ("places_returned", len(records)),
            ("returned", [OrderedDict((
                ("place_id", r.provider_record_id), ("name", r.name),
                ("address", r.address_line), ("postal_code", r.postal_code),
                ("phone", r.phone), ("website_uri", r.website_url),
                ("business_status", r.business_status))) for r in records]),
            ("bound", bound), ("bind_method", binding), ("bind_state", state),
            ("place_id", place_id),
            ("returned_business_name", getattr(matched, "name", "") if matched else ""),
            ("returned_address", getattr(matched, "address_line", "") if matched else ""),
            ("returned_phone", getattr(matched, "phone", "") if matched else ""),
            ("website_uri", website),
            ("official_property_url_candidate", website if bound else ""),
            ("url_shape", MR.classify_url_shape(website) if website else ""),
            ("routing_becomes_usable", bool(bound and website)),
            ("premises_agreement", premises),
            ("binding_signals", OrderedDict((
                ("census_phone", URC.digits(row["phone"])),
                ("census_postal", row["postal_code"]),
                ("census_name", URC.normalise(row["canonical_name"])),
                ("census_presentation_key", URC.presentation_key(
                    row["canonical_name"], state_code=row["state"],
                    unordered=True)),
                ("matched_phone", getattr(matched, "phone", "") if matched else ""),
                ("matched_postal", getattr(matched, "postal_code", "") if matched else ""),
                ("matched_presentation_key", URC.presentation_key(
                    getattr(matched, "name", ""), state_code=row["state"],
                    unordered=True) if matched else ""),
                ("names_compatible", DEDUP.names_compatible(
                    DAL.normalized_name(row),
                    URC.normalise(getattr(matched, "name", "")) if matched else "")),
            ))),
            ("rejections", rejections),
            ("reason", ("bound on %s" % binding) if bound else
                       (rejections[0]["why"] if rejections else
                        "no returned place matched on a sanctioned key")),
            ("measured_cost_usd", None),
        )))

        # The ledger is written for every executed attempt, bound or not: a
        # lookup that found nothing is a lookup this project has already paid
        # for, and repeating it buys the same nothing twice.
        new_records.append(DAL.build_attempt(
            row, market_id=MARKET, work_order=work_order, run_id=run_id,
            provider=provider, method=method, field_mask=field_mask,
            attempted_at=_now(), place_id=place_id, website_uri=website,
            national_phone_number=getattr(matched, "phone", "") if matched else "",
            bind_state=state, bind_method=binding,
            bind_result=results[-1]["reason"], outcome=state,
            cache_pointer=cache.relative_to(_REPO_ROOT).as_posix(),
            paid_requests=outcome.requests_made, cost_usd_minor=None))
        DAL.save(LEDGER_PATH, DAL.merge(DAL.load(LEDGER_PATH), [new_records[-1]]))

        if bound and place_id:
            if place_id in bound_place_ids and bound_place_ids[place_id] != key:
                aborted = ABORT_PLACE_ID_COLLISION
                abort_detail = ("%r and %r bound to one Google place (%s); one "
                                "of them is the wrong hotel and the rule that "
                                "did it would do it again"
                                % (bound_place_ids[place_id], key, place_id))
                break
            bound_place_ids[place_id] = key
        if bound and premises.get("disagrees"):
            disagreements.append(key)
            if len(disagreements) >= FALSE_BINDING_THRESHOLD:
                aborted = ABORT_PREMISES_DISAGREEMENT
                abort_detail = ("%d bound places contradict the census on "
                                "street number or postal code (%s); one can be "
                                "a census error, this many is a pattern"
                                % (len(disagreements), ", ".join(disagreements)))
                break

    return report(document, results, budget, aborted, abort_detail, suppressed,
                  len(new_records), disagreements, live,
                  work_order=work_order, run_id=run_id,
                  cohort_path=cohort_path or COHORT_PATH)


# --------------------------------------------------------------------------- #
# Measuring, projecting, recommending
# --------------------------------------------------------------------------- #

def wilson_lower(successes: int, trials: int) -> float:
    if trials <= 0:
        return 0.0
    z, p, n = 1.959963984540054, successes / trials, float(trials)
    centre = p + z * z / (2 * n)
    spread = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return max(0.0, (centre - spread) / (1 + z * z / n))


def wilson_upper(successes: int, trials: int) -> float:
    if trials <= 0:
        return 0.0
    z, p, n = 1.959963984540054, successes / trials, float(trials)
    centre = p + z * z / (2 * n)
    spread = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return min(1.0, (centre + spread) / (1 + z * z / n))


def rate_block(successes: int, trials: int, what: str) -> Dict:
    return OrderedDict((
        ("what", what), ("successes", successes), ("trials", trials),
        ("point", round(successes / trials, 4) if trials else None),
        ("wilson_lower_95", round(wilson_lower(successes, trials), 4)),
        ("wilson_upper_95", round(wilson_upper(successes, trials), 4)),
    ))


NO_PAGE_EXISTS = "NO_PAGE_EXISTS_TO_RECOVER"
URL_UNREADABLE = "PAGE_RETURNED_BUT_ITS_URL_NAMES_NO_PROPERTY"
NAME_TOO_STRICT = "PAGE_RETURNED_BUT_NO_SANCTIONED_KEY_MATCHED"
REFUSED_ON_PURPOSE = "REFUSED_A_DIFFERENT_PROPERTY"


def why_it_missed(row: Mapping) -> Tuple[str, str]:
    """Why one unbound row is unbound, read off what the provider returned.

    The distinction that matters to a founder deciding whether to buy more:
    a row that HAS NO PAGE can never be recovered at any price, while a row
    whose page came back and was refused is headroom a rule repair could
    reach for nothing. Both are misses; only one of them is a dead end.
    """
    returned = row.get("returned") or []
    has_page = any(place.get("website_uri") for place in returned)
    state = row.get("bind_state")
    if not has_page:
        return (NO_PAGE_EXISTS,
                "every place Google returned states no website at all, so no "
                "lookup at any price can recover a URL for this identity")
    if state == DAL.BIND_REJECTED_URL_SHAPE:
        why = " ".join(j.get("why", "") for j in row.get("rejections") or ())
        if "two properties" in why:
            return (REFUSED_ON_PURPOSE, why.strip())
        return (URL_UNREADABLE,
                "a real page came back and no distinctive word of this "
                "property's name appears in its URL, so the corroboration "
                "check could not read it as being about this hotel")
    if state == DAL.BIND_NO_SANCTIONED_KEY:
        return (NAME_TOO_STRICT,
                "a real page came back and neither the telephone nor the "
                "name-and-postal-code key matched it")
    return (REFUSED_ON_PURPOSE,
            " ".join(j.get("why", "") for j in row.get("rejections") or ()).strip()
            or row.get("reason", ""))


def report(document: Mapping, results: Sequence[Dict], budget: RequestBudget,
           aborted: str, abort_detail: str, suppressed: int,
           ledger_rows: int, disagreements: Sequence[str], live: bool,
           work_order: str = WORK_ORDER, run_id: str = RUN_ID,
           cohort_path: Optional[Path] = None) -> Dict:
    executed = [r for r in results if r.get("requests_made")]
    bound = [r for r in executed if r.get("bound")]

    # TWO DENOMINATORS, BOTH REPORTED. The work order names 56 -- the 76
    # url-less identities less this pilot's 20. Seven of those 56 are held out
    # for cause (two identity pairs, the third same-switchboard pair, three
    # dedup merges), so the number of rows a next batch could actually be drawn
    # from is 49. Projecting on 56 would count rows nobody may buy; projecting
    # on 49 without saying so would look like the order was misread.
    remaining_named_by_the_order = (document["population"]["url_less_identities"]
                                    - len(executed))
    remaining = (document["population"]["eligible_after_exclusions"]
                 - len(executed))

    def by(field: str, group: str) -> List[Dict]:
        return [r for r in executed if r.get(field) == group]

    def rate(rows: Sequence[Dict], what: str) -> Dict:
        return rate_block(sum(1 for r in rows if r.get("bound")), len(rows), what)

    url_rate = rate(executed, "official property URLs recovered per Places "
                             "lookup, measured on this market's own pilot")
    pet_rate = rate_block(PET_FRIENDLY_SUCCESSES, PET_FRIENDLY_TRIALS,
                          "publication-grade pet-friendly profiles per property "
                          "attempted, measured on this market's own paid "
                          "acquisition run")

    def projected(bound_of: float, url_r: float, pet_r: float) -> int:
        return int(bound_of * url_r * pet_r)

    urls_low = remaining * url_rate["wilson_lower_95"]
    urls_high = remaining * url_rate["wilson_upper_95"]
    profiles_low = projected(remaining, url_rate["wilson_lower_95"],
                             pet_rate["wilson_lower_95"])
    profiles_high = projected(remaining, url_rate["wilson_upper_95"],
                              pet_rate["wilson_upper_95"])

    # THE DECISION RULE, AND WHY IT USES TWO DIFFERENT BOUNDS.
    #
    # 025 established that yield is SIZED on the Wilson lower bound. That rule
    # is about how many rows to buy to get N profiles; it is not the rule for
    # whether to buy any. Applied to a go/no-go it would stop every recovery
    # that is not already guaranteed, which is every recovery worth measuring.
    #
    # So feasibility is judged optimistically and sizing conservatively:
    #
    #   STOP if the run aborted on a false-binding pattern -- a rule that binds
    #        the wrong hotel would go on doing it, and no batch size fixes that.
    #   STOP if the target is out of reach even at the UPPER bound: the method
    #        cannot get there and 35 is the honest launch.
    #   Otherwise CONTINUE, and size the next batch on the LOWER bound.
    #
    # All three landings are reported, so a reader who prefers the conservative
    # test can apply it to the same numbers and see where it lands.
    feasible = PUBLISHED_TODAY + profiles_high >= TARGET
    assured = PUBLISHED_TODAY + profiles_low >= TARGET
    working = bool(executed) and len(bound) > 0
    stopped_on_a_pattern = aborted in (ABORT_PLACE_ID_COLLISION,
                                       ABORT_PREMISES_DISAGREEMENT)
    proceed = feasible and working and not stopped_on_a_pattern
    recommendation = ("CONTINUE_WITH_NEXT_SMALL_BATCH" if proceed
                      else "STOP_RECOVERY_AND_LAUNCH_35")

    # The next batch is the smallest cohort that could still reach the target at
    # the CONSERVATIVE rate -- never the whole remainder, and never more than
    # this pilot, whose cap is the only request ceiling this project has run.
    needed = max(0, TARGET - PUBLISHED_TODAY)
    per_lookup = url_rate["wilson_lower_95"] * pet_rate["wilson_lower_95"]
    next_batch = (min(remaining, MAX_REQUESTS,
                      int(-(-needed // per_lookup)) if per_lookup > 0 else remaining)
                  if proceed else 0)

    families = Counter(r.get("family") for r in executed)
    bound_families = Counter(r.get("family") for r in bound)

    return OrderedDict((
        ("schema", SCHEMA), ("market_id", MARKET), ("work_order", work_order),
        ("run_id", run_id), ("live", live),
        ("cohort_document",
         (cohort_path or COHORT_PATH).relative_to(_REPO_ROOT).as_posix()),
        ("authorised_request_cap", MAX_REQUESTS),
        ("requests_made", budget.used),
        ("cap_held", budget.used <= MAX_REQUESTS),
        ("aborted", aborted), ("abort_detail", abort_detail),
        ("suppressed_duplicate_queries", suppressed),
        ("ledger_rows_written", ledger_rows),
        ("billing", OrderedDict((
            ("usd_observable", False),
            ("measured_cost_usd", None),
            ("priced_in", "REQUESTS"),
            ("why", "this repository commits no USD rate for Google Places "
                    "searchText and the client exposes no billing meter, so "
                    "the only honest unit is the request count. No dollar "
                    "figure is invented here."),
        ))),
        ("results", OrderedDict((
            ("executed", len(executed)),
            ("urls_recovered", len(bound)),
            ("recovery_rate", url_rate["point"]),
            ("identities_made_routable",
             sum(1 for r in bound if r.get("routing_becomes_usable"))),
            ("wrong_property_refusals",
             sum(1 for r in executed for j in r.get("rejections", [])
                 if "may not" in j.get("why", "") or "two properties" in j.get("why", ""))),
            ("ambiguous_or_unbound_with_a_page",
             sum(1 for r in executed
                 if r.get("bind_state") in (DAL.BIND_NO_SANCTIONED_KEY,
                                            DAL.BIND_REJECTED_URL_SHAPE))),
            ("no_website_at_all",
             sum(1 for r in executed if r.get("bind_state") == DAL.BIND_NO_WEBSITE)),
            ("no_result_at_all",
             sum(1 for r in executed if r.get("bind_state") == DAL.BIND_NO_RESULT)),
            ("by_bind_state", OrderedDict(sorted(Counter(
                r.get("bind_state") for r in executed).items()))),
            ("by_bind_method", OrderedDict(sorted(Counter(
                r.get("bind_method") for r in bound if r.get("bind_method")).items()))),
            ("by_expected_binding_method", OrderedDict(
                (group, rate(by("expected_binding_method", group),
                             "bound per attempt, %s rows" % group))
                for group in sorted(set(r["expected_binding_method"]
                                        for r in executed)))),
            ("families_attempted", OrderedDict(sorted(families.items()))),
            ("families_recovered", OrderedDict(sorted(bound_families.items()))),
            ("place_id_collisions", OrderedDict(sorted(
                (place, count) for place, count in Counter(
                    r["place_id"] for r in bound if r.get("place_id")).items()
                if count > 1))),
            ("premises_disagreements", list(disagreements)),
        ))),
        ("recovered_urls", [OrderedDict((
            ("identity_key", r["identity_key"]),
            ("url", r["official_property_url_candidate"]),
            ("bind_method", r["bind_method"]),
            ("url_shape", r["url_shape"]),
            ("premises_agrees", not r["premises_agreement"].get("disagrees")),
        )) for r in bound]),
        ("why_the_misses_missed", OrderedDict((
            ("what_this_is", "the eleven unbound rows, split by whether the "
                             "identity HAS a page at all. A dead end and a "
                             "refusal are both misses; only one of them can "
                             "ever be recovered."),
            ("by_cause", OrderedDict(sorted(Counter(
                why_it_missed(r)[0] for r in executed
                if not r.get("bound")).items()))),
            ("no_page_exists_to_recover", sum(
                1 for r in executed
                if not r.get("bound") and why_it_missed(r)[0] == NO_PAGE_EXISTS)),
            ("a_page_came_back_and_a_rule_refused_it", sum(
                1 for r in executed if not r.get("bound")
                and why_it_missed(r)[0] != NO_PAGE_EXISTS)),
            ("headroom_note",
             "a page that came back and was refused is headroom a ZERO-COST "
             "re-read of these saved payloads could reach, exactly as "
             "PTF-INDIANAPOLIS-PLACES-SAVED-PAYLOAD-REBIND-011 recovered 5 "
             "URLs from 143 payloads for nothing. No rule is widened here: a "
             "rule widened during the run whose count it raises is a rule "
             "nothing has qualified."),
            ("rows", [OrderedDict((
                ("identity_key", r["identity_key"]),
                ("cause", why_it_missed(r)[0]),
                ("why", why_it_missed(r)[1]),
                ("returned_business_name", (r["returned"][0]["name"]
                                            if r.get("returned") else "")),
                ("returned_website", (r["returned"][0]["website_uri"]
                                      if r.get("returned") else "")),
            )) for r in executed if not r.get("bound")]),
        ))),
        ("projection", OrderedDict((
            ("basis", "this market's OWN measured rates only -- no rate is "
                      "borrowed from another market"),
            ("remaining_named_by_the_work_order", remaining_named_by_the_order),
            ("remaining_eligible_identities", remaining),
            ("why_the_two_differ",
             "%d of the %d rows the order counts are held out for cause -- two "
             "identity pairs 019 left open, the third same-switchboard pair, "
             "and three dedup merges. They are not buyable, so the projection "
             "runs on %d."
             % (remaining_named_by_the_order - remaining,
                remaining_named_by_the_order, remaining)),
            ("url_recovery_rate", url_rate),
            ("pet_friendly_rate", pet_rate),
            ("urls_expected_low", int(urls_low)),
            ("urls_expected_high", int(urls_high)),
            ("additional_profiles_low", profiles_low),
            ("additional_profiles_high", profiles_high),
            ("published_today", PUBLISHED_TODAY), ("target", TARGET),
            ("landing_at_the_lower_bound", PUBLISHED_TODAY + profiles_low),
            ("landing_at_the_point_estimate", PUBLISHED_TODAY + projected(
                remaining, url_rate["point"] or 0.0, pet_rate["point"] or 0.0)),
            ("landing_at_the_upper_bound", PUBLISHED_TODAY + profiles_high),
            ("reaches_the_target_conservatively", assured),
            ("reaches_the_target_optimistically", feasible),
            ("caveat", "a recovered URL is not a published profile: every one "
                       "still has to be fetched by a paid acquisition lane, "
                       "read, reviewed and signed, and that spend is not "
                       "authorised or priced here"),
        ))),
        ("recommendation", OrderedDict((
            ("decision", recommendation),
            ("rule", "STOP if the run aborted on a false-binding pattern, or "
                     "if the target is out of reach even at the upper bound. "
                     "Otherwise CONTINUE, sized on the lower bound."),
            ("the_method_recovered_something", working),
            ("stopped_on_a_false_binding_pattern", stopped_on_a_pattern),
            ("target_assured_at_the_lower_bound", assured),
            ("target_reachable_at_the_upper_bound", feasible),
            ("next_batch_size", next_batch),
            ("next_batch_is", "the smallest cohort that could still reach the "
                              "target at the conservative rate, capped at the "
                              "size of this pilot" if next_batch else
                              "no further batch is recommended"),
            ("this_is_not_an_authorization",
             "no further request may be made without a separate instruction"),
        ))),
        ("nothing_else_was_run", [
            "Bright Data: not called", "Firecrawl: not called",
            "policy acquisition: not run",
            "premium-domain acquisition: not run",
            "no authority was written, no market assembled, nothing deployed",
        ]),
        ("rows", list(results)),
    ))


def rebuild(path: Path, cohort_path: Optional[Path] = None) -> Dict:
    """Re-derive the report's arithmetic from the rows already bought.

    The ledger now suppresses every row this pilot executed, which is the whole
    point of it -- so re-running ``--live`` would make zero requests and produce
    a report of an empty run. When the reasoning about the SAME evidence has to
    change, the evidence is re-read from disk and the arithmetic re-run over it.
    Nothing here can call a provider.
    """
    prior = json.loads(path.read_text(encoding="utf-8-sig"))
    cohort = json.loads((cohort_path or COHORT_PATH).read_text(encoding="utf-8-sig"))
    rows = list(prior["rows"])
    budget = RequestBudget(max_requests=MAX_REQUESTS,
                           used=int(prior["requests_made"]))
    return report(cohort, rows, budget, prior["aborted"], prior["abort_detail"],
                  int(prior["suppressed_duplicate_queries"]),
                  int(prior["ledger_rows_written"]),
                  list(prior["results"]["premises_disagreements"]),
                  bool(prior["live"]),
                  work_order=prior["work_order"], run_id=prior["run_id"],
                  cohort_path=cohort_path or COHORT_PATH)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true",
                        help="actually call Google; without it nothing is "
                             "fetched and no budget is spent")
    parser.add_argument("--rebuild-report", action="store_true",
                        help="re-derive the arithmetic from the rows already "
                             "bought; makes no request and spends nothing")
    parser.add_argument("--out", default=str(REPORT_PATH))
    args = parser.parse_args(argv)
    if args.rebuild_report:
        document = rebuild(Path(args.out))
    else:
        if args.live and not os.environ.get(C.GOOGLE_PLACES_API_KEY_ENV, "").strip():
            raise SystemExit("no %s in the environment"
                             % C.GOOGLE_PLACES_API_KEY_ENV)
        document = run(live=args.live)
    if args.out:
        Path(args.out).write_text(json.dumps(document, indent=2) + "\n",
                                  encoding="utf-8")
    print("live                %s" % document["live"])
    print("requests made       %d / %d  (cap held: %s)"
          % (document["requests_made"], document["authorised_request_cap"],
             document["cap_held"]))
    print("aborted             %s" % (document["aborted"] or "no"))
    print("ledger rows written %d" % document["ledger_rows_written"])
    results = document["results"]
    print("urls recovered      %d / %d  rate=%s"
          % (results["urls_recovered"], results["executed"],
             results["recovery_rate"]))
    for group, block in results["by_expected_binding_method"].items():
        print("  %-32s %s/%s" % (group, block["successes"], block["trials"]))
    projection = document["projection"]
    print("projection          %d remaining -> %d..%d URLs -> %d..%d profiles"
          % (projection["remaining_eligible_identities"],
             projection["urls_expected_low"], projection["urls_expected_high"],
             projection["additional_profiles_low"],
             projection["additional_profiles_high"]))
    print("landing             %d .. %d  (target %d)"
          % (projection["landing_at_the_lower_bound"],
             projection["landing_at_the_upper_bound"], projection["target"]))
    print("RECOMMENDATION      %s (next batch %d)"
          % (document["recommendation"]["decision"],
             document["recommendation"]["next_batch_size"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
