# -*- coding: utf-8 -*-
"""PTF-GENERIC-CROSS-RUN-DISCOVERY-ATTEMPT-LEDGER-001 -- the Indianapolis replay.

Runs the new discovery ledger over the 143 Indianapolis identities that name no
website, offline. NO PROVIDER IS CALLED and nothing is spent.

The replay answers the question the ledger exists for -- how many of these have
we already paid to look up? -- and then builds the 25-row qualification sample
that PTF-INDIANAPOLIS-PAID-OFFICIAL-URL-DISCOVERY-007 asked for.

WHAT THE SAMPLE IS FOR, WHICH IS NOT WHAT IT LOOKS LIKE
--------------------------------------------------------
It is not a cheap slice of the cohort. It is an experiment with a control.

Every URL this project has ever recovered from Google Places -- all five, in
St. Louis -- bound on TELEPHONE, and only 5 of these 143 rows state one. So the
sample deliberately contains three groups: every row that can bind on the
strong key, a stratified set that must bind on name and postal code, and two
bare two-word names that SHOULD fail. If the bare names bind to something, the
binding rule is too loose and the run has told us that before we spend on 143.
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

from scripts.pettripfinder.acquisition import discovery_attempt_ledger as DAL  # noqa: E402
from scripts.pettripfinder.discovery import constants as C                     # noqa: E402

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
LEDGER_PATH = LP / "ptf_discovery_attempt_ledger_001.json"
SCHEMA = "ptf-market-discovery-replay/1.0"
WORK_ORDER = "PTF-GENERIC-CROSS-RUN-DISCOVERY-ATTEMPT-LEDGER-001"
MARKET = "indianapolis-in"

PROVIDER = "GOOGLE_PLACES"
METHOD = "searchText"
FIELD_MASK = tuple(C.GOOGLE_FIELD_MASK.split(","))

SAMPLE_SIZE = 25
BARE_NAME_CONTROLS = 2

STRONG = "PHONE"
WEAK = "NAME_AND_POSTAL_CODE"
CONTROL = "EXPECTED_TO_FAIL"


def _load(name):
    return json.loads((LP / name).read_text(encoding="utf-8"))


def _query(row: Mapping) -> str:  # noqa: F821
    parts = [row.get("canonical_name") or "", row.get("street") or "",
             row.get("city") or "", "IN", row.get("postal_code") or ""]
    return ", ".join(p for p in parts if p)


def _is_bare(row) -> bool:
    return len((row.get("canonical_name") or "").split()) <= 2


def build() -> Dict:
    report = _load("indianapolis_in_url_recovery_report_006.json")
    rows = [dict(r) for r in report["phase_1_unroutable_inventory"]["rows"]]
    for row in rows:
        row.setdefault("state", "IN")
    ledger = DAL.load(LEDGER_PATH)

    payable, suppressed = DAL.suppress(rows, ledger, provider=PROVIDER,
                                       method=METHOD, field_mask=FIELD_MASK)
    history = DAL.summary(payable, suppressed)

    # Rows that would collapse onto ONE question -- two census identities whose
    # premises fingerprint identically are one lookup, not two.
    by_fingerprint: Dict[str, List[str]] = {}
    for row in rows:
        fingerprint = DAL.query_fingerprint(row, provider=PROVIDER, method=METHOD,
                                            field_mask=FIELD_MASK)
        by_fingerprint.setdefault(fingerprint, []).append(row["identity_key"])
    collisions = {f: keys for f, keys in by_fingerprint.items() if len(keys) > 1}

    # Rows carrying a prior-census alias: the rename case the ledger protects.
    aliased = [r for r in rows if r.get("prior_census_aliases")]

    with_phone = [r for r in rows if (r.get("telephone") or "").strip()]
    bare = [r for r in rows if _is_bare(r)]
    families = Counter(r["family"] for r in rows)

    # ---------------------------------------------------------------- sample
    chosen: List[Dict] = []
    taken = set()

    def take(row, group, why):
        if row["identity_key"] in taken or len(chosen) >= SAMPLE_SIZE:
            return
        taken.add(row["identity_key"])
        chosen.append(OrderedDict((
            ("identity_key", row["identity_key"]),
            ("canonical_name", row["canonical_name"]),
            ("family", row["family"]),
            ("query", _query(row)),
            ("binding_evidence_available", OrderedDict((
                ("telephone", row.get("telephone") or ""),
                ("street", row.get("street") or ""),
                ("postal_code", row.get("postal_code") or ""),
                ("city", row.get("city") or ""),
                ("prior_census_aliases", row.get("prior_census_aliases") or []),
            ))),
            ("expected_binding_method", group),
            ("query_fingerprint", DAL.query_fingerprint(
                row, provider=PROVIDER, method=METHOD, field_mask=FIELD_MASK)),
            ("why_selected", why),
        )))

    # 1. every row that can bind on the strong key. Five exist; they measure
    #    the ceiling, because this is the key that produced every Places URL
    #    this project has ever kept.
    for row in sorted(with_phone, key=lambda r: r["identity_key"]):
        take(row, STRONG, "states a telephone -- the only key that has ever "
                          "bound a Places result in this project, and the "
                          "ceiling this experiment measures")

    # 2. two bare two-word names, as controls that SHOULD NOT bind.
    for row in sorted(bare, key=lambda r: r["identity_key"])[:BARE_NAME_CONTROLS]:
        take(row, CONTROL, "a bare two-word brand name that names no building; "
                           "included deliberately as a failure control -- if "
                           "this binds, the rule is too loose and the other 141 "
                           "must not be bought")

    # 3. the rest, name-and-postal only. EVERY family gets a seat before any
    #    family gets a second one: a rate measured mostly on Choice would say
    #    what Google knows about Choice, not what it knows about this market.
    def pool_for(family):
        return sorted((r for r in rows
                       if r["family"] == family and r["identity_key"] not in taken
                       and not _is_bare(r)),
                      key=lambda r: r["identity_key"])

    for family, _n in families.most_common():
        for row in pool_for(family)[:1]:
            take(row, WEAK, "name and postal code only -- the untested key that "
                            "138 of the 143 depend on. Family %r is seated "
                            "before any family gets a second row, so no one "
                            "brand decides the measured rate" % family)

    # Then fill what is left proportionally, largest families first.
    while len(chosen) < SAMPLE_SIZE:
        progressed = False
        for family, _n in families.most_common():
            if len(chosen) >= SAMPLE_SIZE:
                break
            for row in pool_for(family)[:1]:
                take(row, WEAK, "fills the sample to %d, weighted toward family "
                                "%r because it holds the most unroutable rows"
                                % (SAMPLE_SIZE, family))
                progressed = True
        if not progressed:
            break

    return OrderedDict((
        ("schema", SCHEMA), ("market_id", MARKET), ("work_order", WORK_ORDER),
        ("nothing_was_fetched", True), ("provider_calls", 0), ("usd_spent", 0.0),
        ("this_is_not_an_authorization", True),
        ("provider", PROVIDER), ("discovery_method", METHOD),
        ("field_mask", list(FIELD_MASK)),
        ("ledger", OrderedDict((
            ("path", LEDGER_PATH.relative_to(_REPO_ROOT).as_posix()),
            ("schema", ledger.get("schema")),
            ("recorded_attempts", len(ledger.get("attempts") or ())),
            ("why_it_is_empty",
             "no paid discovery lookup has ever been made by this project. The "
             "ledger starts empty ON PURPOSE and is committed empty, so the "
             "first Indianapolis run writes into a store that already exists "
             "rather than inventing one afterwards."),
        ))),
        ("replay", OrderedDict((
            ("url_less_identities", len(rows)),
            ("already_covered_by_prior_discovery_history", len(suppressed)),
            ("genuinely_new_paid_lookups", len(payable)),
            ("duplicates_that_would_be_suppressed", sum(
                len(keys) - 1 for keys in collisions.values())),
            ("query_fingerprint_collisions", OrderedDict(
                (f, keys) for f, keys in sorted(collisions.items()))),
            ("distinct_query_fingerprints", len(by_fingerprint)),
            ("renamed_identities_protected_from_rebuy", OrderedDict((
                ("rows_carrying_a_prior_census_alias", len(aliased)),
                ("identity_keys", sorted(r["identity_key"] for r in aliased)),
                ("how", "the fingerprint is built from the PREMISES -- name, "
                        "street, city, state, postal code, telephone -- and "
                        "never from the identity key, so a rename produces the "
                        "same question and matches the same prior lookup."),
            ))),
            ("history_summary", history),
        ))),
        ("binding_readiness", OrderedDict((
            ("can_bind_on_telephone", len(with_phone)),
            ("must_bind_on_name_and_postal", len(rows) - len(with_phone)),
            ("bare_two_word_names", len(bare)),
            ("by_family", OrderedDict(sorted(families.items(),
                                             key=lambda kv: (-kv[1], kv[0])))),
        ))),
        ("qualification_sample", OrderedDict((
            ("size", len(chosen)),
            ("by_expected_binding_method", OrderedDict(sorted(
                Counter(r["expected_binding_method"] for r in chosen).items()))),
            ("families_covered", OrderedDict(sorted(
                Counter(r["family"] for r in chosen).items()))),
            ("families_in_the_cohort", len(families)),
            ("provider_requests_if_authorised", len(chosen)),
            ("not_executed", True),
            ("rows", chosen),
        ))),
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="")
    args = parser.parse_args(argv)
    result = build()
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    replay = result["replay"]
    print("url-less identities            %d" % replay["url_less_identities"])
    print("already covered by history     %d" % replay["already_covered_by_prior_discovery_history"])
    print("genuinely new paid lookups     %d" % replay["genuinely_new_paid_lookups"])
    print("duplicates suppressed          %d" % replay["duplicates_that_would_be_suppressed"])
    print("distinct query fingerprints    %d" % replay["distinct_query_fingerprints"])
    print("renamed rows protected         %d"
          % replay["renamed_identities_protected_from_rebuy"]["rows_carrying_a_prior_census_alias"])
    sample = result["qualification_sample"]
    print("sample                         %d rows, %d families, methods %s"
          % (sample["size"], len(sample["families_covered"]),
             dict(sample["by_expected_binding_method"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
