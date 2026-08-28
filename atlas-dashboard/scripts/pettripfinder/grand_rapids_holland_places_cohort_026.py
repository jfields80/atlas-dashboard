# -*- coding: utf-8 -*-
"""PTF-GRAND-RAPIDS-HOLLAND-PLACES-PILOT-026 -- the 20 rows, chosen before the money.

WHY THE COHORT IS A SEPARATE, COMMITTED DOCUMENT
------------------------------------------------
The work order authorises 20 Google Places ``searchText`` requests and no more.
A sample chosen while the run is executing is a sample that can be steered, and
a rate measured on a steered sample is not a rate. So the cohort is built here,
written to disk, and committed; the runner then REFUSES to execute a cohort of
any other size and reads its rows from this file rather than re-deriving them.

WHAT "REPRESENTATIVE" HAD TO MEAN
----------------------------------
The order forbids cherry-picking easy properties. Four axes decide whether a
Places lookup succeeds in this project's experience, so the sample is built to
hold all four in proportion to the 76-row pool it is drawn from:

  EVIDENCE      25 of the 76 state a telephone. Telephone is the strongest key
                the binder has -- Indianapolis bound 5 of 5 on it and 4 of 18
                on name-and-postal -- so a sample that over-weighted phone rows
                would measure a rate this market cannot repeat. The target is
                the pool's own share: 7 of 20.

  FAMILY        nine brand families are present, from 24 independents down to a
                single Motel 6. Every one of them appears, because a family that
                is absent from the pilot is a family the projection is guessing
                about.

  GEOGRAPHY     seven municipalities across the corridor -- Grand Rapids,
                Kentwood, Wyoming, Holland, Grandville, Walker, Comstock Park.

  NAME SHAPE    17 of the 76 carry a name that is a STRICT TOKEN SUBSET of
                another property's name in this same market: "Comfort Suites"
                beside "Comfort Suites Grand Rapids North". Those are the rows
                a places provider is most likely to answer with the WRONG
                BUILDING, which makes them the ones worth buying. Leaving them
                out would have produced a flattering rate and no false-binding
                evidence at all.

WHO IS KEPT OUT, AND ON WHOSE RULING
-------------------------------------
Nothing is excluded on this module's own judgement. Each exclusion cites a
decision that already exists:

  IDENTITY_HOLD          the two pairs held open by 019, and the third
                         same-switchboard pair 025 named. Buying a lookup for a
                         row whose identity is an open question spends money on
                         a question the lookup cannot answer.
  DEDUP_SAFE_MERGE       ``identity_dedup.analyse`` merged three bare/qualified
                         pairs. The absorbed half is not a second hotel.
  ALREADY_LOOKED_UP      the cross-run discovery ledger has already paid to find
                         this page. (Zero rows today: this market has never
                         bought a Places lookup.)

A fourth guard is a SAMPLING rule and is labelled as one, because it rules on
nothing: where two rows share a street number and a municipality, only one is
sampled. They may well be two hotels -- the dedup gate says several of them are
-- but spending two of twenty authorised requests on one doorway would measure
the provider twice and the market once. The deferred sibling stays in the pool
for a later batch.

THE SELECTION IS DETERMINISTIC
-------------------------------
Rows are taken one at a time, and the row taken is always the one that closes
the largest remaining gap against the four targets above, ties broken by
identity key ascending. Re-running this module on the same census produces the
same twenty rows in the same order.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Sequence, Set, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import discovery_attempt_ledger as DAL  # noqa: E402
from scripts.pettripfinder.cincinnati_url_routing_progress_001 import (        # noqa: E402
    brand_of, street_number)
from scripts.pettripfinder.discovery import census_url_recovery as URC         # noqa: E402
from scripts.pettripfinder.discovery import constants as C                     # noqa: E402
from scripts.pettripfinder.discovery import identity_dedup as DEDUP            # noqa: E402

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
CENSUS_PATH = LP / "identity_census" / "grand-rapids-holland-mi.json"
RECOVERY_025 = LP / "grand_rapids_holland_mi_target_recovery_025.json"
HOLDS_019 = LP / "grand_rapids_holland_mi_identity_holds_019.json"
LEDGER_PATH = LP / "ptf_discovery_attempt_ledger_001.json"
COHORT_PATH = LP / "grand_rapids_holland_mi_places_pilot_cohort_026.json"

SCHEMA = "ptf-places-pilot-cohort/1.0"
WORK_ORDER = "PTF-GRAND-RAPIDS-HOLLAND-PLACES-PILOT-026"
MARKET = "grand-rapids-holland-mi"

#: The authorised sample. Twenty identities, twenty requests, and the runner
#: refuses a cohort that is not exactly this long.
SAMPLE_SIZE = 20

PROVIDER = "GOOGLE_PLACES"
DISCOVERY_METHOD = "searchText"

#: What the pilot asks Google for. Identical to the mask Indianapolis bought
#: under, so the two markets' rates are measured on the same thing.
FIELD_MASK: Tuple[str, ...] = (
    "places.id", "places.displayName", "places.formattedAddress",
    "places.addressComponents", "places.location", "places.primaryType",
    "places.types", "places.nationalPhoneNumber", "places.websiteUri",
    "places.businessStatus",
)

EXCLUDED_IDENTITY_HOLD = "IDENTITY_HOLD"
EXCLUDED_DEDUP_SAFE_MERGE = "DEDUP_SAFE_MERGE"
EXCLUDED_ALREADY_LOOKED_UP = "ALREADY_LOOKED_UP_BY_THIS_METHOD"
DEFERRED_SHARED_DOORWAY = "DEFERRED_SHARED_DOORWAY"

#: The third same-switchboard pair. 019 held two and 025 recorded that this one
#: "is the same shape and has had no separate reading", which is the definition
#: of an identity question nobody has answered.
BUDGETEL_PAIR = ("budgetel grand rapids", "budgetel inn and suites hotel")


# --------------------------------------------------------------------------- #
# Reading what other passes decided
# --------------------------------------------------------------------------- #

def _load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def census_rows() -> Dict[str, Dict]:
    return {h["identity_key"]: h for h in _load(CENSUS_PATH)["hotels"]}


def url_less_keys() -> List[str]:
    """The 76. Read from 025's audit rather than recomputed, so the pilot and
    the audit that sized it are talking about the same population."""
    doc = _load(RECOVERY_025)
    return sorted(doc["unresolved_populations"]["no_url"]["identity_keys"])


def held_identities() -> Dict[str, str]:
    """Every identity this market has an OPEN question about."""
    out: Dict[str, str] = {}
    for hold in _load(HOLDS_019)["holds"]:
        for key in hold["identity_keys"]:
            out[key] = ("one half of an unresolved identity pair held open by "
                        "019 (%s); a lookup cannot answer an identity question"
                        % ", ".join(hold["identity_keys"]))
    for key in BUDGETEL_PAIR:
        out.setdefault(key, (
            "the third pair sharing an identical switchboard, recorded by 025 "
            "as having had no separate reading; the same shape as the two "
            "named holds"))
    return out


def merged_away(rows: Sequence[Mapping]) -> Dict[str, str]:
    """The halves ``identity_dedup`` absorbed. Its ruling, not this module's."""
    analysis = DEDUP.analyse(list(rows))
    return {m["absorbed"]: ("absorbed into %r by the pre-acquisition dedup gate "
                            "on %s; not a second hotel"
                            % (m["into"], m["signal"]))
            for m in analysis["merges"]}


# --------------------------------------------------------------------------- #
# Strata
# --------------------------------------------------------------------------- #

def has_phone(row: Mapping) -> bool:
    return bool(URC.digits(row.get("phone", "")))


def doorway_keys(row: Mapping) -> List[str]:
    """The ways two census rows can turn out to be standing in one doorway.

    A street number with a postal code, AND a street number with a
    municipality. Both are needed and neither is enough: 4155 28th Street is
    filed under "Grand Rapids" on one row and "Kentwood" on the other, so the
    municipality key misses it and the postal key catches it; 83 Monroe Center
    states no postal code on one of its two rows, so the postal key misses it
    and the municipality key catches it.

    Not an identity claim. Two hotels genuinely share some of these -- the
    dedup gate has ruled several such pairs DISTINCT_PROPERTIES and this
    module does not overrule it. The keys exist so that twenty authorised
    requests reach twenty doorways.
    """
    number = street_number(row.get("address", ""))
    if not number:
        return []
    postal = (row.get("postal_code") or "").strip()[:5]
    city = URC.normalise(row.get("city", ""))
    keys = []
    if postal:
        keys.append("%s|%s" % (number, postal))
    if city:
        keys.append("%s|%s" % (number, city))
    return keys


def doorway_groups(keys: Sequence[str], census: Mapping[str, Mapping]
                   ) -> List[List[str]]:
    """Rows joined into one group when they share ANY doorway key.

    Transitive on purpose: if A and B share a postal key and B and C share a
    municipality key, all three are one doorway and one of them is sampled.
    """
    parent: Dict[str, str] = {key: key for key in keys}

    def find(key: str) -> str:
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    seen: Dict[str, str] = {}
    for key in keys:
        for door in doorway_keys(census[key]):
            if door in seen:
                a, b = find(key), find(seen[door])
                if a != b:
                    parent[a] = b
            else:
                seen[door] = key

    groups: Dict[str, List[str]] = OrderedDict()
    for key in keys:
        groups.setdefault(find(key), []).append(key)
    return list(groups.values())


def _evidence_rank(row: Mapping) -> Tuple[int, int, int, str]:
    """Lower sorts first: telephone, then a postal code, then the fuller name.

    A longer canonical name is preferred only as the last tiebreak, and only
    because a name carrying a locality ("MainStay Suites GRAND RAPIDS") asks a
    places provider a more answerable question than the bare brand does.
    """
    return (0 if has_phone(row) else 1,
            0 if (row.get("postal_code") or "").strip() else 1,
            -len(URC.normalise(row.get("canonical_name", "")).split()),
            row["identity_key"])


def underspecified_names(census: Mapping[str, Mapping]) -> Set[str]:
    """Names that cannot, alone, tell this property from another in the market.

    A STRICT token subset, which is the same containment rule
    ``names_may_share_a_url`` and ``identity_dedup.names_compatible`` already
    use. "Comfort Suites" is a strict subset of "Comfort Suites Grand Rapids
    North", so the shorter name describes both buildings and is the row a
    places provider is most likely to answer wrongly.
    """
    tokens = {key: set(URC.normalise(row["canonical_name"]).split())
              for key, row in census.items()}
    return {key for key, mine in tokens.items()
            if mine and any(mine < theirs
                            for other, theirs in tokens.items() if other != key)}


def strata_of(key: str, row: Mapping, underspecified: Set[str]) -> Dict[str, str]:
    return OrderedDict((
        ("evidence", "TELEPHONE_STATED" if has_phone(row) else "POSTAL_AND_NAME_ONLY"),
        ("family", brand_of(row["canonical_name"])),
        ("municipality", row.get("city", "") or "UNSTATED"),
        ("name_shape", "UNDERSPECIFIED_IN_MARKET" if key in underspecified
                       else "DISTINCT_IN_MARKET"),
    ))


def targets(pool: Sequence[Tuple[str, Dict]], size: int) -> Dict[str, Dict[str, int]]:
    """How many of each stratum a sample of ``size`` should hold.

    Proportional, rounded to nearest, with one floor: a family present in the
    pool gets at least one seat. A family the pilot never asks about is a
    family the projection would be guessing about.
    """
    out: Dict[str, Dict[str, int]] = {}
    for axis in ("evidence", "family", "municipality", "name_shape"):
        counts = Counter(strata[axis] for _, strata in pool)
        share = {value: count * size / len(pool) for value, count in counts.items()}
        wanted = {value: max(1, int(round(portion))) if axis == "family"
                  else int(round(portion))
                  for value, portion in share.items()}
        out[axis] = wanted
    return out


def select(pool: Sequence[Tuple[str, Dict]], size: int,
           want: Mapping[str, Mapping[str, int]]) -> List[str]:
    """Twenty rows, in two phases, with no randomness anywhere.

    PHASE ONE -- COVERAGE. One row from every brand family present in the pool,
    families taken in name order. A family the pilot never asks about is a
    family the projection would be guessing about, and two of this market's
    nine hold a single hotel each: proportional rounding alone would have
    dropped Red Roof and Motel 6 entirely.

    PHASE TWO -- PROPORTION. The remaining seats go to whichever row closes the
    most stratum gaps against ``want``, so the sample drifts back towards the
    pool's own shape on evidence, geography and name shape.

    Ties are broken by identity key ascending in both phases. The same census
    produces the same twenty rows in the same order, which is what makes the
    cohort auditable BEFORE the first request rather than explicable after the
    last one.
    """
    chosen: List[str] = []
    held: Counter = Counter()
    remaining = list(pool)

    def take(candidate: Tuple[str, Dict]) -> None:
        remaining.remove(candidate)
        chosen.append(candidate[0])
        for axis, value in candidate[1].items():
            held[(axis, value)] += 1

    def closes(candidate: Tuple[str, Dict]) -> Tuple[float, str]:
        """How much of the remaining shortfall this row closes.

        Each axis contributes the FRACTION of its target still unfilled, not a
        flat one. Counting axes flatly made every Grand Rapids row look as
        useful as the market's only Walker row, because both merely "had a gap"
        -- and Walker, late in the alphabet, was never reached. A stratum that
        is entirely empty scores 1.0; one that is 8 of 9 filled scores 0.11.
        """
        _, strata = candidate
        score = 0.0
        for axis, value in strata.items():
            target = want[axis].get(value, 0)
            if target and held[(axis, value)] < target:
                score += (target - held[(axis, value)]) / float(target)
        return (-score, candidate[0])

    for family in sorted({strata["family"] for _, strata in pool}):
        if len(chosen) >= size:
            break
        candidates = [c for c in remaining if c[1]["family"] == family]
        if candidates:
            take(min(candidates, key=closes))

    while remaining and len(chosen) < size:
        take(min(remaining, key=closes))
    return chosen


# --------------------------------------------------------------------------- #
# The document
# --------------------------------------------------------------------------- #

def query_text(row: Mapping) -> str:
    """Name, street, municipality, state, postal -- everything the census states.

    Nothing is invented and nothing is dropped: a query that omitted the postal
    code would return more places and bind fewer of them.
    """
    parts = [row["canonical_name"], row.get("address", ""), row.get("city", ""),
             row.get("state", ""), row.get("postal_code", "")]
    return ", ".join(part.strip() for part in parts if (part or "").strip())


def expected_binding(row: Mapping, underspecified: Set[str], key: str) -> str:
    if has_phone(row):
        return "PHONE"
    if key in underspecified:
        return "NAME_AND_POSTAL_CODE_AT_RISK"
    return "NAME_AND_POSTAL_CODE"


def build(*, work_order: str = WORK_ORDER) -> Dict:
    """The next ``SAMPLE_SIZE`` rows this market may buy a lookup for.

    ``work_order`` only labels the document. Everything else -- the exclusions,
    the strata, the selection -- is unchanged, which is the point: batch 027
    runs the SAME selector over a pool the ledger has already shrunk, rather
    than a second selector nobody has qualified.
    """
    census = census_rows()
    keys = url_less_keys()
    rows = [census[key] for key in keys]

    holds = held_identities()
    merges = merged_away(rows)
    ledger = DAL.load(LEDGER_PATH)
    index = DAL.DiscoveryIndex(ledger)

    underspecified = underspecified_names(census)

    excluded: List[Dict] = []
    eligible: List[str] = []
    for key in keys:
        if key in holds:
            excluded.append(OrderedDict((("identity_key", key),
                                         ("rule", EXCLUDED_IDENTITY_HOLD),
                                         ("why", holds[key]))))
            continue
        if key in merges:
            excluded.append(OrderedDict((("identity_key", key),
                                         ("rule", EXCLUDED_DEDUP_SAFE_MERGE),
                                         ("why", merges[key]))))
            continue
        decision = DAL.decide(census[key], index, provider=PROVIDER,
                              method=DISCOVERY_METHOD, field_mask=FIELD_MASK)
        if decision["decision"] not in DAL.ALLOWED_DECISIONS:
            excluded.append(OrderedDict((
                ("identity_key", key), ("rule", EXCLUDED_ALREADY_LOOKED_UP),
                ("why", decision["reason"]),
                ("ledger_decision", decision["decision"]))))
            continue
        eligible.append(key)

    # The sampling guard. One doorway, one request -- and the row that goes is
    # the BEST-EVIDENCED one, never whichever happened to sort first. A bare
    # "MainStay Suites" that states no telephone and a "MainStay Suites Grand
    # Rapids" that states one describe the same doorway, and buying the lookup
    # against the weaker of the two would measure this method at its worst for
    # no reason.
    deferred: List[Dict] = []
    sampleable: List[str] = []
    for group in doorway_groups(eligible, census):
        keeper = min(group, key=lambda k: _evidence_rank(census[k]))
        sampleable.append(keeper)
        for key in sorted(k for k in group if k != keeper):
            deferred.append(OrderedDict((
                ("identity_key", key), ("rule", DEFERRED_SHARED_DOORWAY),
                ("doorway_keys", doorway_keys(census[key])),
                ("sampled_instead", keeper),
                ("why", "stands in the same doorway as %r, which states more "
                        "binding evidence; this defers it to a later batch and "
                        "rules nothing about whether the two are one hotel"
                        % keeper))))
    sampleable.sort()

    pool = [(key, strata_of(key, census[key], underspecified))
            for key in sampleable]
    want = targets(pool, SAMPLE_SIZE)
    chosen = select(pool, SAMPLE_SIZE, want)
    strata_by_key = dict(pool)

    cohort: List[Dict] = []
    for key in chosen:
        row = census[key]
        strata = strata_by_key[key]
        cohort.append(OrderedDict((
            ("identity_key", key),
            ("canonical_name", row["canonical_name"]),
            ("family", strata["family"]),
            ("query", query_text(row)),
            ("binding_evidence_available", OrderedDict((
                ("telephone", URC.digits(row.get("phone", ""))),
                ("street", row.get("address", "")),
                ("postal_code", row.get("postal_code", "")),
                ("city", row.get("city", "")),
                ("state", row.get("state", "")),
            ))),
            ("expected_binding_method", expected_binding(row, underspecified, key)),
            ("strata", strata),
            ("query_fingerprint", DAL.query_fingerprint(
                row, provider=PROVIDER, method=DISCOVERY_METHOD,
                field_mask=FIELD_MASK)),
            ("why_selected", _why(strata, key in underspecified)),
        )))

    def held(axis: str) -> Dict[str, int]:
        return OrderedDict(sorted(Counter(
            r["strata"][axis] for r in cohort).items()))

    def pooled(axis: str) -> Dict[str, int]:
        return OrderedDict(sorted(Counter(
            strata[axis] for _, strata in pool).items()))

    return OrderedDict((
        ("schema", SCHEMA), ("market_id", MARKET), ("work_order", work_order),
        ("nothing_was_fetched", True), ("provider_calls", 0), ("usd_spent", 0.0),
        ("this_is_not_an_authorization",
         "the work order authorises 20 requests; this document names WHICH 20 "
         "identities they may be spent on, and is committed before the first "
         "one is made"),
        ("provider", PROVIDER), ("discovery_method", DISCOVERY_METHOD),
        ("field_mask", list(FIELD_MASK)),
        ("population", OrderedDict((
            ("url_less_identities", len(keys)),
            ("excluded", len(excluded)),
            ("deferred_to_a_later_batch", len(deferred)),
            ("eligible_after_exclusions", len(eligible)),
            ("sampleable_doorways", len(pool)),
            ("remaining_after_this_pilot", len(eligible) - SAMPLE_SIZE),
        ))),
        ("excluded_rows", excluded),
        ("deferred_rows", deferred),
        ("representativeness", OrderedDict(
            (axis, OrderedDict((("pool", pooled(axis)),
                                ("target", OrderedDict(sorted(want[axis].items()))),
                                ("cohort", held(axis)))))
            for axis in ("evidence", "family", "municipality", "name_shape"))),
        ("sample", OrderedDict((
            ("size", len(cohort)),
            ("provider_requests_if_authorised", len(cohort)),
            ("families_covered", len(set(r["family"] for r in cohort))),
            ("families_in_the_pool", len(set(s["family"] for _, s in pool))),
            ("by_expected_binding_method", OrderedDict(sorted(Counter(
                r["expected_binding_method"] for r in cohort).items()))),
            ("not_executed", "no request has been made"),
            ("rows", cohort),
        ))),
    ))


def _why(strata: Mapping[str, str], underspecified: bool) -> str:
    if underspecified:
        return ("its name is a strict token subset of another property's name "
                "in this market, so a places provider may answer with the wrong "
                "building -- the case worth buying, not the case to avoid")
    if strata["evidence"] == "TELEPHONE_STATED":
        return ("states a telephone, the strongest key the committed binder "
                "holds, and the pool's own share of such rows is 25 of 76")
    return ("carries a postal code and a name and nothing stronger, which is "
            "two thirds of the pool and the harder half of the measurement")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(COHORT_PATH))
    parser.add_argument("--work-order", default=WORK_ORDER,
                        help="the order this cohort is drawn for; it labels "
                             "the document and changes nothing else")
    args = parser.parse_args(argv)
    document = build(work_order=args.work_order)
    Path(args.out).write_text(json.dumps(document, indent=2) + "\n",
                              encoding="utf-8")
    population = document["population"]
    print("url-less identities   %d" % population["url_less_identities"])
    print("excluded              %d" % population["excluded"])
    print("deferred (doorway)    %d" % population["deferred_to_a_later_batch"])
    print("eligible              %d" % population["eligible_after_exclusions"])
    print("cohort                %d" % document["sample"]["size"])
    print("families covered      %d of %d"
          % (document["sample"]["families_covered"],
             document["sample"]["families_in_the_pool"]))
    for axis in ("evidence", "name_shape"):
        block = document["representativeness"][axis]
        print("  %-12s pool=%s cohort=%s"
              % (axis, dict(block["pool"]), dict(block["cohort"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
