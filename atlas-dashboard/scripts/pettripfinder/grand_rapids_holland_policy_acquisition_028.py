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
import re
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


# --------------------------------------------------------------------------- #
# What the run came back with
# --------------------------------------------------------------------------- #

ACQUISITION_REPORT = LP / "grand_rapids_holland_mi_market_acquisition_028.json"
STORE_028 = LP / "grand_rapids_holland_mi_observation_store_028.json"
RESULT_PATH = LP / "grand_rapids_holland_mi_policy_acquisition_028.json"
RUN_DIR = _REPO_ROOT / "data" / "acquisition" / "gr_028"

PUBLISHED_TODAY = 35
TARGET = 43
OPERATING_CAP_USD_MINOR = 400

PET_FRIENDLY = "PET_FRIENDLY"
VERIFIED_NO_PETS = "VERIFIED_NO_PETS"
POLICY_NOT_FOUND = "POLICY_NOT_FOUND"
HOLD = "HOLD"
IDENTITY_OR_ROUTING = "IDENTITY_OR_ROUTING_ISSUE"

#: The readiness states that route themselves, and the one that needs a person.
_PET = frozenset({"POLICY_CONFIRMED", "POLICY_CONFIRMED_WITH_AMBIGUITY"})
_NO_PETS = frozenset({"POLICY_NEGATIVE_CONFIRMED"})
_SELF_ROUTING = frozenset({"POLICY_CONFIRMED", "POLICY_NEGATIVE_CONFIRMED"})


def classify(record: Mapping) -> Tuple[str, str]:
    """One acquired row, in the vocabulary the work order asked for.

    The class is read off the READINESS STATE and the ruled fact together.
    Neither alone is enough: 020 published a VERIFIED_NO_PETS off a store the
    ruling had not edited, and the guard against repeating that is to require
    the state and the fact to agree before either is believed.
    """
    state = str((record.get("readiness") or {}).get("state") or "")
    allowed = ((record.get("observation") or {})
               .get("extraction", {}).get("pets_allowed"))
    if state in _PET and allowed is True:
        return (PET_FRIENDLY,
                "readiness %s on a publication-grade block that states pets "
                "are allowed" % state)
    if state in _NO_PETS and allowed is False:
        return (VERIFIED_NO_PETS,
                "readiness %s on a publication-grade block that states pets "
                "are not allowed" % state)
    if state == "POLICY_NOT_FOUND":
        return (POLICY_NOT_FOUND,
                "the page was acquired and states no pet policy this reader "
                "can locate")
    return (HOLD,
            "readiness %r with pets_allowed %r is not a combination that "
            "routes itself" % (state, allowed))


def declined_evidence(run_dir: Path = RUN_DIR) -> Dict[str, Dict]:
    """What each REFUSED capture kept, and whether its bytes survive.

    This is the difference between a finding worth acting on for nothing and
    one that costs money to act on. A declined capture that kept its rendered
    HTML can be re-read once its identity question is settled; one that kept
    only hashes has to be bought again. Read from disk rather than assumed,
    because both cases exist in this project's history.
    """
    out: Dict[str, Dict] = {}
    if not run_dir.is_dir():
        return out
    for declined in sorted(run_dir.glob("*/declined-*/declined.json")):
        document = json.loads(declined.read_text(encoding="utf-8-sig"))
        folder = declined.parent
        signals = (document.get("identity") or {}).get("signals") or {}
        out[folder.parent.name] = OrderedDict((
            ("outcome", document.get("outcome", "")),
            ("detail", document.get("detail", "")),
            ("title", document.get("title", "")),
            ("name_on_page", signals.get("name_on_page", "")),
            ("address_on_page", signals.get("address_on_page", "")),
            ("rendered_html_on_disk", (folder / "rendered.html").is_file()),
            ("page_text_on_disk", (folder / "page-text.txt").is_file()),
            ("page_text_chars", document.get("page_text_chars", 0)),
            ("directory", folder.relative_to(_REPO_ROOT).as_posix()),
            ("pet_lines_in_the_saved_text", saved_pet_lines(folder)),
        ))
    return out


def brand_generic_pairs(rows: Sequence[Mapping]) -> List[Dict]:
    """Two different properties whose saved pages state the IDENTICAL policy.

    That is the signature of brand boilerplate rather than a property's own
    answer, and it is why a page can name the right hotel and still be unable
    to speak for it. Recorded so the weaker cases are visible as weaker.
    """
    by_quote: Dict[str, List[str]] = {}
    for row in rows:
        quote = row.get("would_read_quote") or ""
        if quote:
            by_quote.setdefault(quote, []).append(row["identity_key"])
    return [OrderedDict((("shared_quote", quote[:180]),
                         ("identity_keys", sorted(keys)),
                         ("why", "two different properties returning the same "
                                 "sentence are reading a brand page, not their "
                                 "own")))
            for quote, keys in sorted(by_quote.items()) if len(keys) > 1]


_PET_LINE = re.compile(r"[^\n]*\bpets?\b[^\n]*", re.IGNORECASE)
_REFUSAL_LINE = re.compile(
    r"\bno\b[^.\n]{0,40}\bpets?\s+are\s+not\s+allowed|"
    r"\bpets?\s+are\s+not\s+allowed|\bpets?\s+not\s+allowed",
    re.IGNORECASE)
_ALLOWANCE_LINE = re.compile(
    r"\bpets?\s+are\s+welcome\b|\bpets?\s+are\s+allowed\b|"
    r"\bpet[- ]friendly\b|\bdogs\s+only\b|\bpet\s+charge\b|\bpet\s+fees?\b",
    re.IGNORECASE)


def saved_pet_lines(folder: Path, limit: int = 4) -> List[str]:
    """Lines mentioning a pet in a capture's SAVED page text. Reads only.

    This does not classify anything. It records what bytes this project
    already owns say, so a founder deciding whether to authorise an identity
    repair can see what the repair would be worth before paying for it.
    """
    text = folder / "page-text.txt"
    if not text.is_file():
        return []
    body = text.read_text(encoding="utf-8", errors="replace")
    out: List[str] = []
    for line in _PET_LINE.findall(body):
        line = " ".join(line.split())
        if len(line) > 12 and line not in out:
            out.append(line)
        if len(out) >= limit:
            break
    return out


def would_the_bytes_answer_it(lines: Sequence[str]) -> Tuple[str, str]:
    """What the saved lines say, if the identity question were settled.

    A refusal is tested BEFORE an allowance, because "no, pets are not allowed"
    contains the substring an allowance pattern matches and reading it as a
    permission would publish the opposite of what the hotel says. That defect
    was driven out of the 025 reader and is not repeated here.
    """
    for line in lines:
        if _REFUSAL_LINE.search(line):
            return ("WOULD_READ_NO_PETS", line)
    for line in lines:
        if _ALLOWANCE_LINE.search(line):
            return ("WOULD_READ_PET_FRIENDLY", line)
    return ("NO_POLICY_IN_THE_SAVED_BYTES", "")


def result(run_dir: Path = RUN_DIR) -> Dict:
    acquisition = _load(ACQUISITION_REPORT)
    store = _load(STORE_028)
    plan = _load(PREFLIGHT_PATH)
    records = store.get("observations") or store.get("records") or []

    classified: List[Dict] = []
    for record in records:
        verdict, why = classify(record)
        classified.append(OrderedDict((
            ("identity_key", record["identity_key"]),
            ("canonical_name", record.get("canonical_name", "")),
            ("brand", record.get("brand", "")),
            ("classification", verdict), ("why", why),
            ("readiness", (record.get("readiness") or {}).get("state", "")),
            ("membrane", str((record.get("membrane") or {}).get("verdict", ""))),
            ("pets_allowed", (record.get("observation") or {})
             .get("extraction", {}).get("pets_allowed")),
            ("publication_grade",
             (record.get("publication_grade") or {}).get("verdict", "")),
        )))

    failures = [r for r in acquisition["results"] if r["outcome"] != "VALID"]
    declined = declined_evidence(run_dir)
    folder_of = {}
    for row in failures:
        raw = (row.get("declined_dir") or "").replace("\\", "/")
        if raw:
            folder_of[row["identity_key"]] = Path(raw).parent.name

    unresolved: List[Dict] = []
    rereadable = 0
    for row in failures:
        evidence = declined.get(folder_of.get(row["identity_key"], ""), {})
        on_disk = bool(evidence.get("rendered_html_on_disk"))
        rereadable += 1 if on_disk else 0
        unresolved.append(OrderedDict((
            ("identity_key", row["identity_key"]),
            ("canonical_name", row.get("canonical_name", "")),
            ("brand", row.get("family", "")),
            ("classification", IDENTITY_OR_ROUTING),
            ("outcome", row["outcome"]),
            ("provider", row.get("provider", "")),
            ("why", row.get("detail", "")),
            ("page_title", evidence.get("title", row.get("title", ""))),
            ("name_on_page", evidence.get("name_on_page", "")),
            ("address_on_page", evidence.get("address_on_page", "")),
            ("bytes_are_on_disk", on_disk),
            ("declined_directory", evidence.get("directory", "")),
            ("pet_lines_in_the_saved_text",
             evidence.get("pet_lines_in_the_saved_text", [])),
        )))
        reading, quote = would_the_bytes_answer_it(
            evidence.get("pet_lines_in_the_saved_text", []))
        unresolved[-1]["would_read"] = reading
        unresolved[-1]["would_read_quote"] = quote

    counts = Counter(r["classification"] for r in classified)
    pet_friendly = counts.get(PET_FRIENDLY, 0)
    projected = PUBLISHED_TODAY + pet_friendly
    exceptions = [r for r in classified if r["readiness"] not in _SELF_ROUTING]

    spend = acquisition["spend"]
    measured = float(spend.get("measured_usd_minor") or 0)
    credits = float(spend.get("estimated_plan_credits") or 0)

    return OrderedDict((
        ("schema", "ptf-policy-acquisition-result/1.0"),
        ("market_id", MARKET), ("work_order", WORK_ORDER), ("run_id", RUN_ID),
        ("cohort", OrderedDict((
            ("size_before_suppression",
             plan["preflight"]["cohort_size_before_suppression"]),
            ("payable", plan["preflight"]["payable_size"]),
            ("reusable_or_suppressed", plan["preflight"]["withheld"]),
            ("by_preflight_verdict", plan["preflight"]["by_verdict"]),
            ("attempted", acquisition["attempted"]),
            ("publication_grade", acquisition["publication_grade"]),
            ("outcome_counts", acquisition["outcome_counts"]),
        ))),
        ("lanes", OrderedDict((
            ("firecrawl_rows", plan["lane_plan"]["firecrawl_rows"]),
            ("firecrawl_credits_used", credits),
            ("brightdata_rows", plan["lane_plan"]["brightdata_browser_rows"]),
            ("cohort_by_provider", acquisition["cohort_by_provider"]),
            ("providers_actually_used", OrderedDict(sorted(Counter(
                r.get("provider", "") for r in acquisition["results"]).items()))),
        ))),
        ("spend", OrderedDict((
            ("measured_usd_minor", measured),
            ("estimated_usd_minor", spend.get("estimated_usd_minor")),
            ("binding_usd_minor", spend.get("binding_usd_minor")),
            ("plan_credits", credits),
            ("operating_cap_usd_minor", OPERATING_CAP_USD_MINOR),
            ("founder_cap_usd_minor", CAP_USD_MINOR),
            ("cap_held", measured <= OPERATING_CAP_USD_MINOR),
            ("under_the_founder_cap", measured <= CAP_USD_MINOR),
            ("why_the_operating_cap_is_lower",
             "the runner's own preflight refuses to arm a cap the vendor "
             "balance cannot cover, and the Bright Data balance read 641 cents "
             "against the authorised 650. A cap is a maximum; spending under "
             "it needs no permission."),
            ("lag_note", spend.get("lag_note", "")),
        ))),
        ("classification", OrderedDict((
            ("counts", OrderedDict(sorted(counts.items()))),
            ("pet_friendly", pet_friendly),
            ("verified_no_pets", counts.get(VERIFIED_NO_PETS, 0)),
            ("policy_not_found", counts.get(POLICY_NOT_FOUND, 0)),
            ("holds", counts.get(HOLD, 0)),
            ("identity_or_routing_issues", len(unresolved)),
            ("rows", classified),
        ))),
        ("founder_review", OrderedDict((
            ("shape", "exception-only"),
            ("clean_rows_that_route_themselves",
             len(classified) - len(exceptions)),
            ("exceptions_needing_a_reading", exceptions),
            ("nothing_was_published",
             "a FACT ruling is not a RECORD approval: these %d rows are "
             "CANDIDATES and the published count stays at %d until the founder "
             "signs them" % (len(classified), PUBLISHED_TODAY)),
            ("founder_decision", ""), ("founder_reviewer_id", ""),
            ("review_status", "MACHINE_REVIEWED_PENDING_OPERATOR"),
        ))),
        ("target_43", OrderedDict((
            ("published_today", PUBLISHED_TODAY), ("target", TARGET),
            ("new_pet_friendly_candidates", pet_friendly),
            ("new_verified_no_pets", counts.get(VERIFIED_NO_PETS, 0)),
            ("holds", counts.get(HOLD, 0)),
            ("policy_not_found", counts.get(POLICY_NOT_FOUND, 0)),
            ("projected_final_pet_friendly", projected),
            ("target_reached", projected >= TARGET),
            ("short_by", max(0, TARGET - projected)),
        ))),
        ("unresolved_rows", OrderedDict((
            ("count", len(unresolved)),
            ("bytes_on_disk", rereadable),
            ("finding",
             "every one of the %d refused rows came back from a page whose own "
             "name is this property, and each was declined on a STREET "
             "SUFFIX: '4155 28th St., S.E.' against '4155 28th Street', '3063 "
             "Lake Eastbrook' against '3063 Lake Eastbrook Blvd SE'. The "
             "rendered HTML is on disk for %d of them, so settling the "
             "identity question costs nothing to READ -- but NO RULE IS "
             "WIDENED HERE, because a rule widened during the run whose count "
             "it raises is a rule nothing has qualified."
             % (len(unresolved), rereadable)),
            ("two_are_not_the_same_case",
             "the two Extended Stay America pages are titled 'Explore Our "
             "Nationwide Hotel Locations'. A policy read off an index that "
             "lists many properties could belong to any of them, so those two "
             "are a weaker case than the four single-property pages."),
            ("brand_generic_quotes_found", brand_generic_pairs(unresolved)),
            ("what_the_saved_bytes_would_read", OrderedDict(sorted(Counter(
                r.get("would_read", "") for r in unresolved
                if r.get("bytes_are_on_disk")).items()))),
            ("rows", unresolved),
        ))),
        ("if_the_identity_question_were_settled", OrderedDict((
            ("this_is_not_a_count",
             "NOTHING below is classified, published or added to any total. "
             "It is what bytes this project ALREADY OWNS would say if a "
             "separate work order settled the street-suffix identity question. "
             "The reported result of this run remains %d pet-friendly and a "
             "projected %d." % (pet_friendly, projected)),
            ("rows_whose_page_names_the_property_and_states_its_own_policy",
             [OrderedDict((("identity_key", r["identity_key"]),
                           ("would_read", r["would_read"]),
                           ("quote", r["would_read_quote"][:160])))
              for r in unresolved
              if r.get("bytes_are_on_disk")
              and r.get("would_read") != "NO_POLICY_IN_THE_SAVED_BYTES"
              and r.get("brand") != "ESA"]),
            ("rows_reading_brand_boilerplate_instead",
             [r["identity_key"] for r in unresolved if r.get("brand") == "ESA"]),
            ("potential_additional_pet_friendly", sum(
                1 for r in unresolved
                if r.get("bytes_are_on_disk") and r.get("brand") != "ESA"
                and r.get("would_read") == "WOULD_READ_PET_FRIENDLY")),
            ("potential_additional_verified_no_pets", sum(
                1 for r in unresolved
                if r.get("bytes_are_on_disk") and r.get("brand") != "ESA"
                and r.get("would_read") == "WOULD_READ_NO_PETS")),
            ("the_cost_of_finding_out", "zero: the bytes are already on disk. "
                                        "What is NOT free is the identity rule "
                                        "change that would let them be read, "
                                        "and that is a separate work order."),
        ))),
        ("nothing_else_was_run", [
            "no Google Places request: the 20 URLs were bought by 026 and 027",
            "no expansion beyond the authorised cohort",
            "no authority written, no market assembled, nothing deployed",
            "no row published: the review is exception-only and signs nothing",
        ]),
    ))


PACKET_PATH = LP / "grand_rapids_holland_mi_founder_review_packet_028.json"


def founder_packet(document: Mapping) -> Dict:
    """Exception-only, and it signs nothing.

    TWO LISTS, BECAUSE THEY ASK DIFFERENT THINGS OF A PERSON. The exceptions
    need a READING: a human has to look at the evidence and say what it means.
    The clean rows need only a RECORD APPROVAL -- 020's lesson is that a FACT
    ruling is not a record approval, so a row whose facts route themselves
    still needs a signature before it publishes, but it does not need anyone to
    re-read its page.
    """
    klass = document["classification"]
    review = document["founder_review"]
    exceptions = list(review["exceptions_needing_a_reading"])
    exception_keys = {r["identity_key"] for r in exceptions}
    clean = [r for r in klass["rows"] if r["identity_key"] not in exception_keys]

    return OrderedDict((
        ("schema", "ptf-founder-review-packet/1.0"),
        ("market_id", MARKET), ("work_order", WORK_ORDER),
        ("what_this_is",
         "the 13 rows PTF-GRAND-RAPIDS-POLICY-ACQUISITION-028 acquired at "
         "publication grade, presented exception-only. Nothing here is signed, "
         "published or promoted, and the published pet-friendly count stays at "
         "%d until a founder rules." % PUBLISHED_TODAY),
        ("provider_calls", 0), ("usd_spent", 0.0),
        ("counts", OrderedDict((
            ("acquired_at_publication_grade", len(klass["rows"])),
            ("needing_a_reading", len(exceptions)),
            ("needing_only_a_record_approval", len(clean)),
            ("pet_friendly", klass["pet_friendly"]),
            ("verified_no_pets", klass["verified_no_pets"]),
            ("policy_not_found", klass["policy_not_found"]),
            ("holds", klass["holds"]),
        ))),
        ("exceptions_needing_a_reading", [OrderedDict((
            ("identity_key", r["identity_key"]),
            ("canonical_name", r["canonical_name"]),
            ("brand", r["brand"]),
            ("proposed_class", r["classification"]),
            ("readiness", r["readiness"]),
            ("why_it_is_an_exception",
             "readiness is %s: the page states a policy AND states something "
             "the reader could not resolve without a person" % r["readiness"]),
            ("founder_decision", ""), ("founder_note", ""),
        )) for r in exceptions]),
        ("clean_rows_for_record_approval", [OrderedDict((
            ("identity_key", r["identity_key"]),
            ("canonical_name", r["canonical_name"]),
            ("brand", r["brand"]),
            ("proposed_class", r["classification"]),
            ("readiness", r["readiness"]),
            ("founder_decision", ""),
        )) for r in clean]),
        ("for_information_not_for_decision", OrderedDict((
            ("unresolved_identity_or_routing",
             document["unresolved_rows"]["count"]),
            ("note", "these 7 are NOT in this packet's counts and NOT "
                     "publishable. They are listed so the packet is not "
                     "silently narrower than the run."),
            ("identity_keys", [r["identity_key"]
                               for r in document["unresolved_rows"]["rows"]]),
        ))),
        ("target", OrderedDict((
            ("published_today", PUBLISHED_TODAY), ("target", TARGET),
            ("if_every_row_here_is_approved",
             document["target_43"]["projected_final_pet_friendly"]),
            ("target_reached", document["target_43"]["target_reached"]),
            ("short_by", document["target_43"]["short_by"]),
        ))),
        ("founder_decision", ""), ("founder_reviewer_id", ""),
        ("founder_reviewed_at", ""),
        ("review_status", "MACHINE_REVIEWED_PENDING_OPERATOR"),
        ("nothing_is_signed_here",
         "never sign an approval in the operator's name: the reviewer id and "
         "the decision are left empty for a human to fill"),
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", action="store_true",
                        help="build the post-run result from the acquisition "
                             "report and the observation store; reads only")
    parser.add_argument("--out", default=str(PREFLIGHT_PATH))
    args = parser.parse_args(argv)
    if args.result:
        document = result()
        RESULT_PATH.write_text(json.dumps(document, indent=2) + "\n",
                               encoding="utf-8")
        PACKET_PATH.write_text(
            json.dumps(founder_packet(document), indent=2) + "\n",
            encoding="utf-8")
        cohort, spend = document["cohort"], document["spend"]
        klass, target = document["classification"], document["target_43"]
        print("cohort before suppression  %d" % cohort["size_before_suppression"])
        print("payable / reusable         %d / %d"
              % (cohort["payable"], cohort["reusable_or_suppressed"]))
        print("attempted / pub-grade      %d / %d  %s"
              % (cohort["attempted"], cohort["publication_grade"],
                 dict(cohort["outcome_counts"])))
        print("firecrawl rows / credits   %d / %s"
              % (document["lanes"]["firecrawl_rows"],
                 document["lanes"]["firecrawl_credits_used"]))
        print("bright data rows           %d" % document["lanes"]["brightdata_rows"])
        print("measured spend             %.0fc  operating cap %dc held=%s  "
              "founder cap %dc"
              % (spend["measured_usd_minor"], spend["operating_cap_usd_minor"],
                 spend["cap_held"], spend["founder_cap_usd_minor"]))
        print("pet-friendly               %d" % klass["pet_friendly"])
        print("verified no-pets           %d" % klass["verified_no_pets"])
        print("policy-not-found / holds   %d / %d"
              % (klass["policy_not_found"], klass["holds"]))
        print("identity/routing issues    %d  (bytes on disk: %d)"
              % (klass["identity_or_routing_issues"],
                 document["unresolved_rows"]["bytes_on_disk"]))
        print("projected final            %d   target %d reached=%s short_by=%d"
              % (target["projected_final_pet_friendly"], target["target"],
                 target["target_reached"], target["short_by"]))
        settled = document["if_the_identity_question_were_settled"]
        print("POTENTIAL only, not counted: +%d pet-friendly / +%d no-pets "
              "from bytes already on disk"
              % (settled["potential_additional_pet_friendly"],
                 settled["potential_additional_verified_no_pets"]))
        packet = json.loads(PACKET_PATH.read_text(encoding="utf-8-sig"))
        print("founder packet             %d needing a reading, %d for record "
              "approval"
              % (packet["counts"]["needing_a_reading"],
                 packet["counts"]["needing_only_a_record_approval"]))
        return 0
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
