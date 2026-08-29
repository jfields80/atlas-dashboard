# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-PLACES-SAVED-PAYLOAD-REBIND-011 -- read the 143 again, for nothing.

Every Google Places response Indianapolis will ever have is already on disk:
25 from the qualification sample and 118 from the broader cohort, all paid for,
all protected from re-buy by the discovery ledger. 47 of those bound. This asks
what the other 96 refused over, and whether any of it is presentation rather
than identity.

IT MAKES NO REQUEST AND SPENDS NOTHING.

WHAT THE PAYLOADS ACTUALLY SAID
-------------------------------
77 of the refusals returned a place at the right postal code, with a routable
property page, whose URL names the property -- and the name still differed. It
would be easy to read that as 77 recoverable rows. It is not. Most of those 77
are DIFFERENT HOTELS sharing a postal code: a Clarion Pointe offered for a
Comfort Inn, a Red Roof for a Comfort, a La Quinta for a Comfort, a Courtyard
for a Comfort Suites. A postal code holds many hotels, which is exactly why the
name has to agree as well.

Three deterministic patterns survived that reading, and they are worth five
rows between them. That is the honest yield of this pass.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import Counter, OrderedDict
from typing import Dict, List

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import indianapolis_routing_gain_010 as GAIN        # noqa: E402
from scripts.pettripfinder.acquisition import cohort_cost_plan as CP           # noqa: E402
from scripts.pettripfinder.acquisition import market_routing as MR             # noqa: E402
from scripts.pettripfinder.acquisition import paid_attempt_ledger as PAL       # noqa: E402
from scripts.pettripfinder.acquisition import registry as REGISTRY             # noqa: E402
from scripts.pettripfinder.acquisition.market_paid_acquisition import family_of  # noqa: E402
from scripts.pettripfinder.brightdata import corpus as CORPUS                  # noqa: E402
from scripts.pettripfinder.discovery import census_url_recovery as URC         # noqa: E402

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
CACHES = ("data/discovery/indianapolis_places_008/cache",
          "data/discovery/indianapolis_places_010/cache")
SCHEMA = "ptf-market-payload-rebind/1.0"
WORK_ORDER = "PTF-INDIANAPOLIS-PLACES-SAVED-PAYLOAD-REBIND-011"
MARKET = "indianapolis-in"
TARGET = 50

#: Must not bind. The four committed controls plus the two brand-vs-brand cases
#: the payloads themselves produced.
PROTECTED = OrderedDict((
    ("aloft", "a bare brand word"),
    ("ashley motel", "the place carries no website"),
    ("cambria hotel westfield indianapolis north", "Places offered a Hampton Inn"),
    ("hampton inn and suites indianapolis carmel", "Places offered the Homewood Suites"),
    ("best western plus indianapolis north at broad ripple",
     "Places offered the same brand at a different landmark, the Pyramids"),
    ("courtyard by marriott indianapolis airport plainfield",
     "Places offered the Plainfield Courtyard, which is not the Airport one"),
))


def _load(name):
    return json.loads((LP / name).read_text(encoding="utf-8"))


def _payloads() -> Dict[str, Dict]:
    out: Dict[str, Dict] = {}
    for root in CACHES:
        for path in (_REPO_ROOT / root).rglob("*.json"):
            document = json.loads(path.read_text(encoding="utf-8"))
            if document.get("query_id"):
                out.setdefault(document["query_id"], document)
    return out


def _postal(address: str) -> str:
    for token in reversed((address or "").replace(",", " ").split()):
        if len(token) == 5 and token.isdigit():
            return token
    return ""


def _observations(places) -> List[URC.Observation]:
    return [URC.Observation(
        provider=URC.GOOGLE_PLACES,
        source="places:%s" % (p.get("id") or "?"),
        name=(p.get("displayName") or {}).get("text", ""),
        phone=p.get("nationalPhoneNumber", "") or "",
        postal=_postal(p.get("formattedAddress", "")),
        url=p.get("websiteUri", "") or "",
        street=p.get("formattedAddress", "") or "") for p in places]


def _rebind(row: Dict, places) -> Dict:
    census = {"identity_key": row["identity_key"],
              "canonical_name": row["canonical_name"],
              "address": row.get("street", ""), "city": row.get("city", ""),
              "state": "IN", "postal_code": row.get("postal_code", ""),
              "phone": row.get("telephone", "")}
    observations = _observations(places)
    by_url = {o.url: p for o, p in zip(observations, places)}

    def acceptable(observation):
        url = MR.normalize_source_url(observation.url)
        if not url:
            return (False, "the place carries no website at all")
        if MR.classify_url_shape(url) not in MR.ROUTABLE_SHAPES:
            return (False, "the website is a %s" % MR.classify_url_shape(url))
        return URC.url_names_the_property(census["canonical_name"], url)

    rejected: List[Dict] = []
    observation, binding = URC.bind(census, observations,
                                    unambiguous_streets=None,
                                    acceptable=acceptable, rejected=rejected,
                                    presentation_variants=True)
    if observation is None:
        return {"bound": False, "binding": "",
                "why": rejected[0]["why"] if rejected else
                       "no returned place matched on a sanctioned key"}
    place = by_url.get(observation.url, {})
    return {"bound": True, "binding": binding,
            "url": MR.normalize_source_url(observation.url),
            "place_id": place.get("id", ""),
            "places_name": (place.get("displayName") or {}).get("text", ""),
            "places_address": place.get("formattedAddress", ""),
            "places_postal": _postal(place.get("formattedAddress", "")),
            "why": ""}


def _rule_for(census_name: str, places_name: str) -> str:
    """Which of the three 011 transformations made these two names equal."""
    reasons = []
    a = URC.presentation_key(census_name, state_code="IN")
    b = URC.presentation_key(places_name, state_code="IN")
    low = places_name.lower() + " " + census_name.lower()
    if "an ihg hotel" in low:
        reasons.append("dropped the operator suffix 'an IHG Hotel'")
    if "& suites" in low or "and suites" in low:
        reasons.append("'Inn & Suites' and 'Inn' are one designation")
    if a != b and sorted(a.split()) == sorted(b.split()):
        reasons.append("the same words in a different order")
    return "; ".join(reasons) or "an earlier 009 rule"


def build() -> Dict:
    inventory = _load("indianapolis_in_url_recovery_report_006.json")
    rows = {r["identity_key"]: r
            for r in inventory["phase_1_unroutable_inventory"]["rows"]}
    already = {r["identity_key"]: r for r in GAIN.recovered_urls()}
    payloads = _payloads()

    new_binds: List[Dict] = []
    still: List[Dict] = []
    protected_bound: List[str] = []

    for key, row in sorted(rows.items()):
        if key in already:
            continue
        document = payloads.get(key.replace(" ", "-")[:80])
        places = (document or {}).get("payload", {}).get("places", []) or []
        result = _rebind(row, places)
        if not result["bound"]:
            still.append(OrderedDict((("identity_key", key),
                                      ("why", result["why"]))))
            continue
        if key in PROTECTED:
            protected_bound.append(key)
        new_binds.append(OrderedDict((
            ("identity_key", key), ("census_name", row["canonical_name"]),
            ("places_name", result["places_name"]),
            ("places_address", result["places_address"]),
            ("places_postal", result["places_postal"]),
            ("census_postal", row.get("postal_code", "")),
            ("website_uri", result["url"]),
            ("url_shape", MR.classify_url_shape(result["url"])),
            ("place_id", result["place_id"]),
            ("old_refusal", "no returned place matched on a sanctioned key"),
            ("new_census_key", URC.presentation_key(
                row["canonical_name"], state_code="IN", unordered=True)),
            ("new_places_key", URC.presentation_key(
                result["places_name"], state_code="IN", unordered=True)),
            ("rule", _rule_for(row["canonical_name"], result["places_name"])),
            ("binding_evidence", "postal %s on both sides, the URL names the "
                                 "property, and the names agree once the "
                                 "presentation is removed"
                                 % row.get("postal_code", "")),
            ("why_safe", "the postal codes match exactly, the page is a %s the "
                         "brand serves for this property, and nothing that "
                         "distinguishes buildings -- locality, compass word, "
                         "airport, downtown -- was normalised away"
                         % MR.classify_url_shape(result["url"])),
        )))

    # ---- routing impact, offline -----------------------------------------
    census = _load("identity_census/indianapolis-in.json")
    by_key = {h["identity_key"]: h for h in census["hotels"]}
    paid_ledger = _load("ptf_paid_attempt_ledger_001.json")

    cohort: List[Dict] = []
    for entry in new_binds:
        hotel = by_key.get(entry["identity_key"], {})
        brand = CORPUS.brand_of(entry["website_uri"])
        route = REGISTRY.resolve(brand=brand, url=entry["website_uri"],
                                 identity_key=entry["identity_key"])
        cohort.append(OrderedDict((
            ("identity_key", entry["identity_key"]),
            ("canonical_name", hotel.get("canonical_name", "")),
            ("source_url", entry["website_uri"]), ("brand", brand),
            ("family", family_of(brand)), ("provider", route.provider),
            ("street", hotel.get("address", "")),
            ("postal_code", hotel.get("postal_code", "")),
            ("telephone", hotel.get("phone", "")))))
    payable, suppressed = PAL.suppress(cohort, paid_ledger)
    reusable = [r for r in suppressed
                if r["paid_history"].get("reusable_evidence")]

    prior = _load("indianapolis_in_routing_gain_010.json")
    routing_before = prior["routing"]["routing_after"]
    url_less_before = prior["routing"]["url_less_after"]
    prepared_46 = prior["target_50"]["acquirable_cohort"]

    promoted = prior["target_50"]["current_promoted_pet_friendly"]
    pf_rate = prior["target_50"]["observed_pet_friendly_rate"]
    from_prepared = prior["target_50"]["expected_new_pet_friendly"]
    from_new = int(round(len(payable) * pf_rate))

    lanes = Counter(r["provider"] for r in payable)
    combined = [dict(r, family=family_of(r["brand"]))
                for r in prior["minimum_next_acquisition_cohort"]["rows"]] + \
               [dict(r, family=family_of(r["brand"])) for r in payable]
    plan = CP.build({"cohort": combined},
                    _load("indianapolis_in_market_acquisition_pass1_002.json"),
                    authorised_cap_usd=0.0, paid_ledger=paid_ledger,
                    available_lanes=("brightdata_browser",
                                     "brightdata_web_unlocker", "firecrawl"))

    return OrderedDict((
        ("schema", SCHEMA), ("market_id", MARKET), ("work_order", WORK_ORDER),
        ("provider_calls", 0), ("usd_spent", 0.0),
        ("saved_payloads_reviewed", len(payloads)),
        ("identities_re_examined", len(rows) - len(already)),
        ("new_rules", OrderedDict((
            ("an_operator_hotel",
             "'..., an IHG Hotel' is the same courtesy as 'by IHG', said the "
             "other way round. Dropped as an exact three-token run."),
            ("inn_and_suites",
             "'Comfort Inn & Suites Fishers' and 'Comfort Inn Fishers' are one "
             "hotel. The token is dropped ONLY when it directly follows 'inn', "
             "so 'Comfort Suites South' keeps its 'suites' and stays a "
             "different brand from 'Comfort Inn South'."),
            ("token_order",
             "Google writes 'Avon Indianapolis' where the census writes "
             "'Indianapolis Avon'. Compared as sorted tokens: exact multiset "
             "equality, so one extra or one missing word is still two hotels."),
            ("no_fuzzy_matching",
             "no edit distance, no similarity score, no overlap threshold"),
        ))),
        ("results", OrderedDict((
            ("already_bound_before", len(already)),
            ("new_binds", len(new_binds)),
            ("total_bound_after", len(already) + len(new_binds)),
            ("still_unbound", len(still)),
            ("false_or_ambiguous_binds", protected_bound),
            ("place_id_collisions", {p: c for p, c in Counter(
                b["place_id"] for b in new_binds if b["place_id"]).items() if c > 1}),
        ))),
        ("controls", OrderedDict((
            ("protected", list(PROTECTED)),
            ("protected_bound", protected_bound),
            ("all_held", not protected_bound),
        ))),
        ("routing", OrderedDict((
            ("routing_before", routing_before),
            ("newly_routable", len(new_binds)),
            ("routing_after", routing_before + len(new_binds)),
            ("url_less_before", url_less_before),
            ("url_less_after", url_less_before - len(new_binds)),
        ))),
        ("acquisition_impact", OrderedDict((
            ("prepared_cohort_before", prepared_46),
            ("newly_added_rows", len(payable)),
            ("already_reusable_policy_evidence", len(reusable)),
            ("total_acquisition_cohort", prepared_46 + len(payable)),
            ("new_rows_firecrawl", lanes.get("firecrawl", 0)),
            ("new_rows_brightdata", sum(v for k, v in lanes.items()
                                        if k.startswith("brightdata"))),
        ))),
        ("combined_cost_plan", OrderedDict((
            ("this_is_not_an_authorization", True),
            ("cohort_size", plan["cohort_size"]),
            ("cohort_by_provider", plan["cohort_by_provider"]),
            ("firecrawl_credits", plan["expected_firecrawl_credits"]),
            ("credit_billed_properties", plan["credit_billed_properties"]),
            ("dollar_billed_properties", plan["dollar_billed_properties"]),
            ("expected_brightdata_usd_minor", plan["expected_brightdata_usd_minor"]),
            ("projection", plan["projection"]),
            ("safe_cap_usd_minor",
             int(plan["projection"]["worst_case_usd_minor"]) + 15),
        ))),
        ("target_50", OrderedDict((
            ("current_promoted_pet_friendly", promoted),
            ("observed_pet_friendly_rate", pf_rate),
            ("expected_from_prepared_cohort", from_prepared),
            ("expected_from_newly_rebound", from_new),
            ("expected_total", promoted + from_prepared + from_new),
            ("target", TARGET),
            ("remaining_gap",
             max(0, TARGET - promoted - from_prepared - from_new)),
            ("this_is_an_estimate_not_an_approval",
             "the rate is this market's own history; no row here is approved, "
             "signed or publishable until a founder reviews the policy "
             "evidence an acquisition would produce"),
        ))),
        ("new_binds", new_binds),
        ("still_unbound", still),
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="")
    args = parser.parse_args(argv)
    report = build()
    if args.out:
        Path = pathlib.Path
        Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    results = report["results"]
    print("payloads reviewed   %d" % report["saved_payloads_reviewed"])
    print("re-examined         %d" % report["identities_re_examined"])
    print("new binds           %d   (total bound %d)"
          % (results["new_binds"], results["total_bound_after"]))
    print("still unbound       %d" % results["still_unbound"])
    print("controls held       %s" % report["controls"]["all_held"])
    routing = report["routing"]
    print("routing             %d -> %d   url-less %d -> %d"
          % (routing["routing_before"], routing["routing_after"],
             routing["url_less_before"], routing["url_less_after"]))
    target = report["target_50"]
    print("target 50           %d + %d + %d = %d (gap %d)"
          % (target["current_promoted_pet_friendly"],
             target["expected_from_prepared_cohort"],
             target["expected_from_newly_rebound"], target["expected_total"],
             target["remaining_gap"]))
    plan = report["combined_cost_plan"]
    print("combined cohort     %d rows | firecrawl %s credits | BD %d | worst %sc"
          % (plan["cohort_size"], plan["firecrawl_credits"],
             plan["dollar_billed_properties"],
             plan["projection"]["worst_case_usd_minor"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
