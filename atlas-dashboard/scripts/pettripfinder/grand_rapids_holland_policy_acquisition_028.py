# -*- coding: utf-8 -*-
"""PTF-GRAND-RAPIDS-POLICY-ACQUISITION-028 -- fetch the twenty pages already paid to find.

Batches 026 and 027 spent 40 Google Places requests and came back with 20
official property URLs. Finding a page publishes nothing: every one of them
still has to be FETCHED, read, classified and reviewed. This order does the
fetching, for those twenty and nothing else.

WHAT THIS MODULE IS, AND WHAT IT REFUSES TO BE
-----------------------------------------------
It is a PRE-FLIGHT and a COHORT BUILDER. The acquisition itself is
``acquisition.market_paid_acquisition``, the committed runner every market has
used, driven through its own contracts:

    --url-overlay     the 20 recovered URLs, layered over the census IN MEMORY.
                      The census file is the record of what discovery OBSERVED
                      and is not edited: a URL bound from a Places result is a
                      proposal, and writing it into the census would make a
                      derivation indistinguishable from an observation.
    --only-cohort     a ptf-authorized-cohort naming the exact 20 identities.
                      An authorisation names identities, never a count, so the
                      run can only ever be a SUBSET of what it found eligible.
    --cost-plan       mandatory for a spending run, fingerprinted over exactly
                      what will be bought.
    --cap-usd 6.50    the founder's ceiling, enforced by the runner's own
                      spend meter against the vendor's own cost endpoint.
    --paid-ledger     the cross-run ledger, re-run over the intersection
                      immediately before spending.

Nothing here re-derives a lane, a binding rule, a reader or a price.

THE FOUR PRE-FLIGHT QUESTIONS
------------------------------
Each is answered against a committed authority, not against this module's
opinion:

    twenty unique identities and twenty unique pages
        ``identity_dedup`` page keys -- CANONICAL_URL and PROPERTY_CODE -- so
        two census rows that turn out to name one page cannot both be bought.

    every identity still passes its binding
        the Places bind is re-run from the saved evidence, so a URL that only
        bound under a rule this branch has since changed is caught here rather
        than after the money.

    nothing already paid for
        ``paid_attempt_ledger.suppress`` over the whole cohort. Its match
        hierarchy is CANONICAL_URL > PROPERTY_CODE > PROPERTY_IDENTITY >
        PREMISES_EVIDENCE, and only the first two decide alone.

    no publication-grade evidence already owned
        the market's own observation store. A row this market has already read
        at publication grade is REUSABLE, and buying it again buys nothing.

THE LANE PLAN IS DERIVED, NOT CHOSEN
-------------------------------------
``lane_qualification`` reads the cross-run corpus and returns which
(lane, family) pairs have earned their qualification. Cheapest QUALIFIED lane
wins, credit-billed ahead of dollar-billed. On today's evidence that is
Firecrawl for CHOICE, IHG and WYNDHAM and the Bright Data browser for
everything else -- and the browser is not a preference, it is what a family
with no qualified cheaper lane falls back to.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import authorized_cohort as AUTH        # noqa: E402
from scripts.pettripfinder.acquisition import lane_qualification as LQ         # noqa: E402
from scripts.pettripfinder.acquisition import market_routing as MR             # noqa: E402
from scripts.pettripfinder.acquisition import paid_attempt_ledger as PAL       # noqa: E402
from scripts.pettripfinder.acquisition import registry as REG                  # noqa: E402
from scripts.pettripfinder.brightdata.corpus import brand_of                   # noqa: E402
from scripts.pettripfinder.discovery import census_url_recovery as URC         # noqa: E402
from scripts.pettripfinder.discovery import identity_dedup as DEDUP            # noqa: E402

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
CENSUS_PATH = LP / "identity_census" / "grand-rapids-holland-mi.json"
PILOT_026 = LP / "grand_rapids_holland_mi_places_pilot_026.json"
BATCH_027 = LP / "grand_rapids_holland_mi_places_batch_027_run.json"
PAID_LEDGER = LP / "ptf_paid_attempt_ledger_001.json"
OBSERVATION_STORE = LP / "grand_rapids_holland_mi_observation_store_022.json"

OVERLAY_PATH = LP / "grand_rapids_holland_mi_recovered_url_overlay_028.json"
COHORT_PATH = LP / "grand_rapids_holland_mi_authorized_cohort_028.json"
PREFLIGHT_PATH = LP / "grand_rapids_holland_mi_acquisition_preflight_028.json"

SCHEMA = "ptf-policy-acquisition-preflight/1.0"
OVERLAY_SCHEMA = "ptf-census-url-recovery/1.0"
WORK_ORDER = "PTF-GRAND-RAPIDS-POLICY-ACQUISITION-028"
RUN_ID = "grand-rapids-holland-mi-acquisition-028"
MARKET = "grand-rapids-holland-mi"

#: The founder's ceiling, in cents. The runner meters against the vendor's own
#: cost endpoint; this module only plans under it and refuses a plan that
#: cannot fit.
CAP_USD_MINOR = 650

#: Publication-grade evidence this market already owns needs no second purchase.
REUSABLE_GRADES = frozenset({"PUBLICATION_GRADE"})

PAYABLE = "GENUINELY_PAYABLE"
REUSABLE = "REUSABLE_POLICY_EVIDENCE"
ALREADY_PAID = "ALREADY_PAID"
DUPLICATE_PAGE = "DUPLICATE_PAGE_IN_COHORT"
BINDING_LAPSED = "BINDING_NO_LONGER_HOLDS"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


# --------------------------------------------------------------------------- #
# The twenty, read from the two batches that bought them
# --------------------------------------------------------------------------- #

def recovered_rows() -> List[Dict]:
    """The 20 URLs, joined back to their census rows.

    Read from the two run reports rather than re-derived, because the report is
    what the founder authorised against and a second derivation could disagree
    with it silently.
    """
    census = {h["identity_key"]: h for h in _load(CENSUS_PATH)["hotels"]}
    runs = ((_load(PILOT_026), "PTF-GRAND-RAPIDS-HOLLAND-PLACES-PILOT-026"),
            (_load(BATCH_027), "PTF-GRAND-RAPIDS-PLACES-BATCH-027"))
    out: List[Dict] = []
    for document, order in runs:
        detail = {row["identity_key"]: row for row in document["rows"]
                  if row.get("requests_made")}
        for row in document["recovered_urls"]:
            key = row["identity_key"]
            hotel = census[key]
            evidence = detail[key]
            out.append(OrderedDict((
                ("identity_key", key),
                ("canonical_name", hotel["canonical_name"]),
                ("city", hotel.get("city", "")),
                ("state", hotel.get("state", "")),
                ("postal_code", hotel.get("postal_code", "")),
                ("address", hotel.get("address", "")),
                ("phone", hotel.get("phone", "")),
                ("corridor", hotel.get("corridor", "")),
                ("recovered_url", row["url"]),
                ("url_shape", MR.classify_url_shape(row["url"])),
                ("brand", brand_of(row["url"])),
                ("binding", row["bind_method"]),
                ("recovered_by", order),
                ("place_id", evidence.get("place_id", "")),
                ("returned_business_name",
                 evidence.get("returned_business_name", "")),
                ("returned_address", evidence.get("returned_address", "")),
                ("returned_phone", evidence.get("returned_phone", "")),
                ("premises_agreement", evidence.get("premises_agreement", {})),
            )))
    return out


# --------------------------------------------------------------------------- #
# Pre-flight
# --------------------------------------------------------------------------- #

def binding_still_holds(row: Mapping) -> Tuple[bool, str]:
    """Re-run the Places bind from the saved evidence.

    A URL that bound under a rule this branch has since changed would otherwise
    be bought on a binding nobody can reproduce. Cheap, and it runs before the
    money rather than after it.
    """
    census_row = {
        "identity_key": row["identity_key"],
        "canonical_name": row["canonical_name"],
        "address": row["address"], "street": row["address"],
        "city": row["city"], "state": row["state"],
        "postal_code": row["postal_code"], "phone": row["phone"],
        "official_url": "",
    }
    sighting = URC.Observation(
        provider="GOOGLE_PLACES",
        source="places:%s" % (row.get("place_id") or "?"),
        name=row.get("returned_business_name", ""),
        phone=URC.digits(row.get("returned_phone", "")),
        postal=(row.get("premises_agreement", {}) or {}).get("place_postal", ""),
        url=row["recovered_url"],
        street=row.get("returned_address", ""))

    def acceptable(observation) -> Tuple[bool, str]:
        url = MR.normalize_source_url(observation.url)
        if not url:
            return (False, "the place carries no website at all")
        if MR.classify_url_shape(url) not in MR.ROUTABLE_SHAPES:
            return (False, "the website is not a shape a lane can fetch")
        return URC.url_names_the_property(row["canonical_name"], url)

    rejected: List[Dict] = []
    observation, binding = URC.bind(census_row, [sighting],
                                    unambiguous_streets=None,
                                    acceptable=acceptable, rejected=rejected,
                                    presentation_variants=True)
    if observation is None:
        return (False, (rejected[0]["why"] if rejected
                        else "no sanctioned key binds this sighting today"))
    if binding != row["binding"]:
        return (True, "binds today on %s, recorded as %s" % (binding, row["binding"]))
    return (True, "binds on %s, as recorded" % binding)


def duplicate_pages(rows: Sequence[Mapping]) -> Dict[str, str]:
    """Two identities that name ONE page. Page keys decide alone.

    ``identity_dedup`` treats CANONICAL_URL and PROPERTY_CODE as page signals:
    a shared street or a shared switchboard only PROPOSES, but a shared page is
    the same page and buying it twice buys the same bytes twice.
    """
    out: Dict[str, str] = {}
    for signal, reader in (("CANONICAL_URL", DEDUP.canonical_url),
                           ("PROPERTY_CODE", DEDUP.property_code)):
        seen: Dict[str, str] = {}
        for row in rows:
            probe = dict(row, official_url=row["recovered_url"],
                         url=row["recovered_url"])
            value = reader(probe)
            if not value:
                continue
            if value in seen and seen[value] != row["identity_key"]:
                out.setdefault(row["identity_key"],
                               "shares one %s (%s) with %r; a page bought once "
                               "is a page bought"
                               % (signal, value, seen[value]))
            else:
                seen.setdefault(value, row["identity_key"])
    return out


def already_publication_grade() -> Dict[str, str]:
    """Rows this market has already read at publication grade."""
    out: Dict[str, str] = {}
    if not OBSERVATION_STORE.is_file():
        return out
    store = _load(OBSERVATION_STORE)
    for record in (store.get("observations") or store.get("records") or ()):
        key = record.get("identity_key") or ""
        grade = str(record.get("evidence_grade") or "")
        if key and grade in REUSABLE_GRADES:
            out[key] = ("this market already owns %s evidence for it; a second "
                        "purchase would buy the same answer" % grade)
    return out


def ledger_suppressions(rows: Sequence[Mapping]) -> Dict[str, Dict]:
    """The cross-run paid ledger's own verdict. Pay once per page, ever."""
    ledger = PAL.load(PAID_LEDGER)
    cohort = [dict(row, official_url=row["recovered_url"],
                   url=row["recovered_url"],
                   lane=row.get("lane", ""), lanes_tried=[])
              for row in rows]
    payable, suppressed = PAL.suppress(cohort, ledger)
    payable_keys = {r["identity_key"] for r in payable}
    out: Dict[str, Dict] = {}
    for row in suppressed:
        key = row.get("identity_key") or ""
        if key and key not in payable_keys:
            out[key] = OrderedDict((
                ("decision", row.get("decision", "")),
                ("reason", row.get("reason", "")),
                ("matched_on", row.get("matched_on", "")),
            ))
    return out


# --------------------------------------------------------------------------- #
# The lane plan
# --------------------------------------------------------------------------- #

def lane_plan(rows: Sequence[Mapping]) -> Dict:
    """Cheapest QUALIFIED lane per family, derived from the committed corpus."""
    ledger = PAL.load(PAID_LEDGER)
    evidence = LQ.summarise([dict(a, provider=a.get("lane", ""))
                             for a in ledger["attempts"] if a.get("outcome")])
    costs = LQ.lane_costs()
    verdicts = LQ.qualify(evidence, available={p: c["available"]
                                               for p, c in costs.items()})
    by_family: "OrderedDict[str, Dict]" = OrderedDict()
    for family in sorted({row["brand"] for row in rows}):
        by_family[family] = LQ.plan_lane(family, verdicts, costs)

    assignments: List[Dict] = []
    for row in rows:
        plan = by_family[row["brand"]]
        route = REG.resolve(brand=row["brand"], url=row["recovered_url"],
                            identity_key=row["identity_key"])
        assignments.append(OrderedDict((
            ("identity_key", row["identity_key"]),
            ("family", row["brand"]),
            ("primary_lane", plan["primary_lane"]),
            ("fallback_lane", plan["fallback_lane"]),
            ("registry_route", route.provider),
            ("registry_forbids", list(route.forbidden_providers)),
            ("credit_billed", plan["primary_credit_billed"]),
            ("usd_minor", plan["primary_usd_minor"]),
            ("fallback_usd_minor", plan["fallback_usd_minor"]),
            ("qualification_reason", plan["qualification_reason"]),
        )))

    firecrawl = [a for a in assignments if a["primary_lane"] == "firecrawl"]
    browser = [a for a in assignments if a["primary_lane"] == "brightdata_browser"]
    unlocker = [a for a in assignments
                if a["primary_lane"] == "brightdata_web_unlocker"]
    other = [a for a in assignments
             if a["primary_lane"] not in ("firecrawl", "brightdata_browser",
                                          "brightdata_web_unlocker")]

    projected = sum(float(a["usd_minor"] or 0) for a in browser + unlocker)
    # If every credit-billed row exhausted its primary and fell to its dollar
    # fallback. This is the number an authorisation has to survive.
    fallback = projected + sum(float(a["fallback_usd_minor"] or 0)
                               for a in firecrawl)
    # And if every dollar row ALSO needed its own fallback after failing.
    worst = fallback + sum(float(a["fallback_usd_minor"] or 0)
                           for a in browser + unlocker)

    return OrderedDict((
        ("qualified_pairs", sorted("%s/%s" % (p, f) for (p, f), v
                                   in verdicts.items() if v["qualified"])),
        ("lane_costs", costs),
        ("by_family", by_family),
        ("firecrawl_rows", len(firecrawl)),
        ("firecrawl_credits_required", float(len(firecrawl))),
        ("brightdata_browser_rows", len(browser)),
        ("brightdata_web_unlocker_rows", len(unlocker)),
        ("other_rows", len(other)),
        ("projected_usd_minor", projected),
        ("fallback_usd_minor", fallback),
        ("worst_case_usd_minor", worst),
        ("authorised_cap_usd_minor", CAP_USD_MINOR),
        ("worst_case_fits_under_the_cap", worst <= CAP_USD_MINOR),
        ("firecrawl_families_are_all_qualified",
         all(("firecrawl", a["family"]) in
             {(p, f) for (p, f), v in verdicts.items() if v["qualified"]}
             for a in firecrawl)),
        ("assignments", assignments),
    ))


# --------------------------------------------------------------------------- #
# The documents the runner reads
# --------------------------------------------------------------------------- #

def overlay_document(rows: Sequence[Mapping]) -> Dict:
    """A ptf-census-url-recovery the runner layers over the census IN MEMORY."""
    return OrderedDict((
        ("schema", OVERLAY_SCHEMA), ("market_id", MARKET),
        ("work_order", WORK_ORDER),
        ("what_this_is",
         "the 20 official property URLs recovered by Google Places batches 026 "
         "and 027, offered to the acquisition runner for ROUTING ONLY. The "
         "census file is not edited: a bound Places result is a proposal, and "
         "writing it into the census would make a derivation indistinguishable "
         "from an observation."),
        ("binding_rule",
         "census_url_recovery.bind with presentation_variants, telephone then "
         "name-and-postal-code, corroborated by url_names_the_property and "
         "refused by names_may_share_a_url"),
        ("recovered", len(rows)),
        ("routable_recoveries",
         sum(1 for r in rows
             if MR.classify_url_shape(r["recovered_url"]) in MR.ROUTABLE_SHAPES)),
        ("binding_counts", OrderedDict(sorted(Counter(
            r["binding"] for r in rows).items()))),
        ("recovered_url_shapes", OrderedDict(sorted(Counter(
            r["url_shape"] for r in rows).items()))),
        ("recoveries", list(rows)),
    ))


def preflight(rows: Sequence[Mapping]) -> Dict:
    """Every reason a row may NOT be bought, each citing its own authority."""
    duplicates = duplicate_pages(rows)
    owned = already_publication_grade()
    suppressed = ledger_suppressions(rows)

    verdicts: List[Dict] = []
    payable: List[Dict] = []
    withheld: List[Dict] = []
    for row in rows:
        key = row["identity_key"]
        holds, why_binding = binding_still_holds(row)
        if not holds:
            verdict, why = BINDING_LAPSED, why_binding
        elif key in duplicates:
            verdict, why = DUPLICATE_PAGE, duplicates[key]
        elif key in owned:
            verdict, why = REUSABLE, owned[key]
        elif key in suppressed:
            verdict, why = ALREADY_PAID, suppressed[key]["reason"]
        else:
            verdict, why = PAYABLE, "no prior purchase, no owned evidence, no "\
                                    "duplicate page: this run must buy it"
        entry = OrderedDict((
            ("identity_key", key), ("canonical_name", row["canonical_name"]),
            ("brand", row["brand"]), ("recovered_url", row["recovered_url"]),
            ("url_shape", row["url_shape"]), ("binding", row["binding"]),
            ("binding_still_holds", holds),
            ("binding_check", why_binding),
            ("verdict", verdict), ("why", why),
        ))
        verdicts.append(entry)
        (payable if verdict == PAYABLE else withheld).append(entry)

    return OrderedDict((
        ("cohort_size_before_suppression", len(rows)),
        ("unique_identities", len({r["identity_key"] for r in rows})),
        ("unique_canonical_urls", len({r["recovered_url"] for r in rows})),
        ("every_identity_still_binds",
         all(v["binding_still_holds"] for v in verdicts)),
        ("payable_size", len(payable)),
        ("withheld", len(withheld)),
        ("by_verdict", OrderedDict(sorted(Counter(
            v["verdict"] for v in verdicts).items()))),
        ("payable_identity_keys", [v["identity_key"] for v in payable]),
        ("withheld_rows", withheld),
        ("rows", verdicts),
    ))


def build() -> Dict:
    rows = recovered_rows()
    checks = preflight(rows)
    payable = [r for r in rows
               if r["identity_key"] in set(checks["payable_identity_keys"])]
    lanes = lane_plan(payable)
    return OrderedDict((
        ("schema", SCHEMA), ("market_id", MARKET), ("work_order", WORK_ORDER),
        ("run_id", RUN_ID), ("generated_at", _now()),
        ("nothing_was_fetched", True), ("usd_spent", 0.0),
        ("plan_credits_spent", 0.0),
        ("this_is_not_an_authorization",
         "the founder authorised this exact recovered-URL cohort under a "
         "$6.50 ceiling; this document names WHICH rows are payable under it "
         "and what they should cost, and buys nothing"),
        ("source_batches", OrderedDict((
            ("places_026", PILOT_026.relative_to(_REPO_ROOT).as_posix()),
            ("places_027", BATCH_027.relative_to(_REPO_ROOT).as_posix()),
            ("urls_recovered", len(rows)),
        ))),
        ("preflight", checks),
        ("lane_plan", lanes),
        ("no_additional_places_lookup",
         "this order runs no Google Places request; the 20 URLs were already "
         "bought by 026 and 027 and the discovery ledger suppresses all 40 "
         "identities either way"),
    ))


def write_documents(document: Mapping, rows: Sequence[Mapping]) -> Dict:
    payable_keys = document["preflight"]["payable_identity_keys"]
    OVERLAY_PATH.write_text(
        json.dumps(overlay_document(rows), indent=2) + "\n", encoding="utf-8")
    cohort = AUTH.build(
        payable_keys, market_id=MARKET, work_order=WORK_ORDER, run_id=RUN_ID,
        cap_usd_minor=CAP_USD_MINOR,
        plan_credit_cap=int(document["lane_plan"]["firecrawl_credits_required"]),
        generated_at=document["generated_at"],
        provenance=OrderedDict((
            ("recovered_by", ["PTF-GRAND-RAPIDS-HOLLAND-PLACES-PILOT-026",
                              "PTF-GRAND-RAPIDS-PLACES-BATCH-027"]),
            ("preflight", PREFLIGHT_PATH.relative_to(_REPO_ROOT).as_posix()),
        )))
    COHORT_PATH.write_text(json.dumps(cohort, indent=2) + "\n", encoding="utf-8")
    return cohort


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(PREFLIGHT_PATH))
    args = parser.parse_args(argv)
    rows = recovered_rows()
    document = build()
    Path(args.out).write_text(json.dumps(document, indent=2) + "\n",
                              encoding="utf-8")
    cohort = write_documents(document, rows)

    checks, lanes = document["preflight"], document["lane_plan"]
    print("cohort before suppression  %d" % checks["cohort_size_before_suppression"])
    print("unique identities / urls   %d / %d"
          % (checks["unique_identities"], checks["unique_canonical_urls"]))
    print("every identity still binds %s" % checks["every_identity_still_binds"])
    print("payable                    %d   withheld %d  %s"
          % (checks["payable_size"], checks["withheld"],
             dict(checks["by_verdict"])))
    print("firecrawl rows             %d   credits %s"
          % (lanes["firecrawl_rows"], lanes["firecrawl_credits_required"]))
    print("bright data browser rows   %d" % lanes["brightdata_browser_rows"])
    print("web unlocker rows          %d" % lanes["brightdata_web_unlocker_rows"])
    print("other rows                 %d" % lanes["other_rows"])
    print("projected / fallback / worst  %.0fc / %.0fc / %.0fc   cap %dc  fits=%s"
          % (lanes["projected_usd_minor"], lanes["fallback_usd_minor"],
             lanes["worst_case_usd_minor"], lanes["authorised_cap_usd_minor"],
             lanes["worst_case_fits_under_the_cap"]))
    print("authorized cohort          %d keys, fingerprint %s"
          % (len(cohort["identity_keys"]), cohort.get("cohort_fingerprint", "")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
