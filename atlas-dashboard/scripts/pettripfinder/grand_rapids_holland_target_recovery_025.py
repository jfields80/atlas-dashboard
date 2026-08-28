# -*- coding: utf-8 -*-
"""PTF-GRAND-RAPIDS-TARGET-43-45-RECOVERY-025 -- the cheapest path to 43.

NO PROVIDER IS CALLED and nothing is spent. Every policy fact below is
re-located from HTML this project already bought and still holds on disk, and
the paid plan is priced and STOPPED before the money.

THE ANSWER THE AUDIT GIVES, WHICH IS NOT THE ONE THE TARGET WANTED
-------------------------------------------------------------------
The zero-cost pool cannot move the pet-friendly count at all. That is worth
stating first because it is the finding, not a preamble to one.

The 114 unresolved rows are four populations and only one of them is reachable
for nothing:

    76  state no official URL. The zero-cost recovery pass already ran and
        left exactly these 76 unknown, so a URL for any of them has to be
        bought before a policy can be.
    17  are duplicates the pre-acquisition dedup gate merged into rows this
        market already publishes. They can never become separate profiles.
     5  are ROUTE_BRAND_EXCLUDED. They HAVE property URLs; the registry
        excludes Hyatt and Best Western as premium domains under the current
        Bright Data plan -- "excluded on cost, not on capability".
    16  are routed with a saved capture, and this is the whole zero-cost pool.

Of those 16, six had their identity confirmed by 020 and their captures never
reached a policy locator, because the identity gate refused them BEFORE it ran.
Re-locating from the saved HTML is free and is what this pass does. Two of the
six state a policy, and both say the same thing:

    Baymont Inn & Suites GR Airport  "Sorry no other pets are allowed."
    Fairfield Inn & Suites Wyoming   "Pets Not Allowed"

Both are VERIFIED NO-PETS. They raise the exclusion count and the authority
total, and they move the pet-friendly count by zero. The other four never say
the word. The remaining ten of the sixteen are excluded by the order itself --
the Budgetel identity hold, the Comfort Suites half of an open pair, avid hotel
Zeeland's standing founder withholding, a dead route, a cross-brand route, two
redirects and the three silent Hilton-family pages.

So every one of the eight profiles the target needs must be bought, and the
rest of this module prices that as small as it can be made.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import lane_qualification as LQ    # noqa: E402
from scripts.pettripfinder.acquisition import paid_attempt_ledger as PAL  # noqa: E402
from scripts.pettripfinder.acquisition import providers as PROVIDERS      # noqa: E402

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
RUN_DIR = (_REPO_ROOT / "data" / "acquisition"
           / "grand_rapids_holland_mi_factory_001" / "pass1")

WORK_ORDER = "PTF-GRAND-RAPIDS-TARGET-43-45-RECOVERY-025"
MARKET = "grand-rapids-holland-mi"
PREFIX = "grand_rapids_holland_mi"

TARGET_MIN = 43
TARGET_MAX = 45

#: The six rows 020 confirmed the identity of. Their captures were declined at
#: the identity gate, which runs BEFORE the policy locator, so no policy block
#: was ever cut from HTML this project owns.
IDENTITY_CONFIRMED_020: Tuple[str, ...] = (
    "baymont inn and suites grand rapids airport",
    "fairfield inn and suites grand rapids wyoming",
    "haworth hotel", "the ada hotel", "the bluejay hotel", "the finnley hotel",
)

#: Rows the order excludes from automatic recovery, and why. Named rather than
#: filtered silently: a row absent from a recovery cohort should say which rule
#: kept it out.
EXCLUDED_BY_RULE: Tuple[Tuple[str, str], ...] = (
    ("budgetel grand rapids",
     "identity HOLD -- the order excludes it from automatic recovery"),
    ("comfort suites grandville grand rapids sw",
     "one half of an unresolved same-property pair; its evidence is clean and "
     "its identity is not"),
    ("avid hotel zeeland",
     "withheld from authority by the founder's standing ruling in 022: a "
     "confirmed identity does not make a POLICY_NOT_FOUND row publishable"),
    ("affordable suites", "the route resolves to the site's own 404 page"),
    ("best western",
     "the census row names one chain and its official_url is another's"),
    ("country inn and suites holland mi",
     "the route redirects off the property onto a brand page"),
    ("motel 6 grand rapids northeast",
     "the route redirects off the property onto a brand page"),
    ("doubletree by hilton hotel grand rapids airport",
     "POLICY_NOT_FOUND: the policy accordion never rendered into the page we "
     "saved, so a re-read cannot settle it"),
    ("drury inn and suites grand rapids",
     "POLICY_NOT_FOUND: the saved page never mentions a pet"),
    ("tulyp",
     "POLICY_NOT_FOUND: the policy accordion never rendered into the page we "
     "saved, so a re-read cannot settle it"),
)

#: A pet policy is stated on ONE LINE in the saved page text, so the reader
#: works line by line and no pattern may span a newline. Letting one span
#: newlines is how "Pets Not Allowed" first came back quoting "See Details /
#: Open in New Tab / Rooms & Suites".
#:
#: Neither pattern is applied to a fee, a service-animal sentence or an amenity
#: token: the line must be ABOUT pets, and the refusal is tested first.
_REFUSAL = re.compile(
    r"\b(?:no|not)\b[^.]{0,80}?\bpets?\b|"
    r"\bpets?\b[^.]{0,40}?\bnot\s+(?:allowed|permitted|accepted|welcome)\b|"
    r"\bpets?\s+not\s+allowed\b",
    re.IGNORECASE)
_ALLOWANCE = re.compile(
    r"\bpets?\b[^.]{0,60}?\b(?:are|is)\s+(?:allowed|welcome|permitted|accepted)\b|"
    r"\bwe\s+(?:welcome|allow)\s+pets?\b|"
    r"\bpets?\s+(?:are\s+)?welcome\b",
    re.IGNORECASE)
#: A service-animal sentence is a legal access category. It is never read as a
#: pet permission or as a refusal, so it is removed before either pattern runs.
_SERVICE_ANIMAL = re.compile(r"[^.]*\bservice animals?\b[^.]*\.?", re.IGNORECASE)
_PET_TOKEN = re.compile(r"\bpets?\b|\bdogs?\b", re.IGNORECASE)


class RecoveryError(RuntimeError):
    """A recovery the saved evidence does not support."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write(path: Path, document: Mapping) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def capture_dir(key: str) -> Optional[Path]:
    base = key.replace("&", "and")
    for slug in ("-".join(base.split()),
                 "-".join(w for w in base.split() if w != "and")):
        for sub in ("declined-01", "attempt-01"):
            path = RUN_DIR / slug / sub
            if path.is_dir():
                return path
    return None


# --------------------------------------------------------------------------- #
# Phase 1 -- re-locating a policy from HTML we already own
# --------------------------------------------------------------------------- #

def relocate_policy(key: str) -> Dict:
    """What the SAVED page says about pets, if anything.

    A re-locate, never a re-parse: the bytes are the ones the paid run brought
    back, their hash is recorded, and no provider is asked for them again. The
    identity gate refused these captures before the locator ever ran, so there
    is no earlier reading for this to disagree with -- which is the one case
    PTF-INDIANAPOLIS-HOME2-KEYSTONE-REPARSE-014 established is safe.
    """
    path = capture_dir(key)
    if path is None:
        return OrderedDict((("identity_key", key), ("capture", ""),
                            ("verdict", "NO_SAVED_CAPTURE")))
    text_path = path / "page-text.txt"
    text = (text_path.read_text(encoding="utf-8", errors="replace")
            if text_path.is_file() else "")
    refusals: List[str] = []
    allowances: List[str] = []
    mentions = False
    for raw in text.splitlines():
        line = _SERVICE_ANIMAL.sub(" ", raw).strip()
        if not _PET_TOKEN.search(line):
            continue
        mentions = True
        # A refusal wins outright on its own line: "Sorry no other pets are
        # allowed" CONTAINS the substring an allowance pattern matches, and
        # reading it as a permission would publish the opposite of what the
        # hotel says.
        if _REFUSAL.search(line):
            refusals.append(line)
        elif _ALLOWANCE.search(line):
            allowances.append(line)

    if refusals and allowances:
        verdict = "AMBIGUOUS_BOTH_STATED"
        quote = "%s || %s" % (refusals[0], allowances[0])
    elif refusals:
        verdict, quote = "VERIFIED_NO_PETS", refusals[0]
    elif allowances:
        verdict, quote = "PET_FRIENDLY", allowances[0]
    elif mentions:
        verdict, quote = "MENTIONS_PETS_STATES_NO_POLICY", ""
    else:
        verdict, quote = "SOURCE_SILENT", ""

    return OrderedDict((
        ("identity_key", key),
        ("capture", str(path.relative_to(_REPO_ROOT).as_posix())),
        ("page_text_sha256", _sha256(text_path) if text_path.is_file() else ""),
        ("rendered_html_sha256",
         _sha256(path / "rendered.html") if (path / "rendered.html").is_file() else ""),
        ("verdict", verdict),
        ("quote", quote),
        ("refusal_lines", refusals),
        ("allowance_lines", allowances),
        ("service_animal_sentences_removed_first", True),
        ("provider_calls", 0),
    ))


def zero_cost_recovery() -> Dict:
    """Every row the order lets this pass re-read, and what it found."""
    rows = [relocate_policy(key) for key in IDENTITY_CONFIRMED_020]
    counts = Counter(r["verdict"] for r in rows)
    return OrderedDict((
        ("reviewed", len(rows)),
        ("by_verdict", OrderedDict(sorted(counts.items()))),
        ("pet_friendly", counts.get("PET_FRIENDLY", 0)),
        ("verified_no_pets", counts.get("VERIFIED_NO_PETS", 0)),
        ("still_unresolved", counts.get("SOURCE_SILENT", 0)
         + counts.get("MENTIONS_PETS_STATES_NO_POLICY", 0)
         + counts.get("AMBIGUOUS_BOTH_STATED", 0)),
        ("finding",
         "the zero-cost pool moves the PET-FRIENDLY count by zero. Both rows "
         "that state a policy state a refusal, so what they raise is the "
         "exclusion count."),
        ("excluded_by_rule", [OrderedDict((("identity_key", key), ("why", why)))
                              for key, why in EXCLUDED_BY_RULE]),
        ("rows", rows),
    ))


# --------------------------------------------------------------------------- #
# Phase 2 -- pricing the gap, conservatively
# --------------------------------------------------------------------------- #

def wilson_lower(successes: int, trials: int, z: float = 1.96) -> float:
    """The LOWER bound of a Wilson interval, which is what a cohort is sized on.

    Sizing on the point estimate is how a plan that needs eight profiles buys
    exactly enough rows to get eight on a good day. PTF-INDIANAPOLIS-BACKLOG-
    COST-PLAN-015 established the rule for this corpus: denominate the rate in
    ATTEMPTS and size on the lower bound.
    """
    if trials <= 0:
        return 0.0
    p = successes / trials
    denominator = 1 + z * z / trials
    centre = p + z * z / (2 * trials)
    margin = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials))
    return max(0.0, (centre - margin) / denominator)


def wilson_upper(successes: int, trials: int, z: float = 1.96) -> float:
    """The UPPER bound, which is what a BUDGET is sized on.

    Yield and cost want opposite ends of the same interval: plan the profiles
    on the fewest that might come back, and the money on the most rows that
    might route. Using one bound for both is how a plan under-delivers and
    overruns at the same time.
    """
    if trials <= 0:
        return 0.0
    p = successes / trials
    denominator = 1 + z * z / trials
    centre = p + z * z / (2 * trials)
    margin = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials))
    return min(1.0, (centre + margin) / denominator)


def measured_rates() -> Dict:
    """Every rate this plan uses, with the run that measured it named.

    The pet-friendly rate is THIS market's own. The URL-recovery rate is not:
    Grand Rapids has never bought a Places lookup, so the only measurement that
    exists is Indianapolis's, and a rate borrowed from another market is
    labelled as borrowed rather than quietly adopted.
    """
    package = _load(LP / ("%s_founder_review_packet_001.json" % PREFIX))
    counts = package["recommendation_counts"]
    pet_friendly = int(counts.get("RECOMMEND_AUTHORITY_PET_FRIENDLY", 0))
    attempted = int(_load(LP / ("%s_market_acquisition_pass1_001.json" % PREFIX))
                    ["attempted"])
    return OrderedDict((
        ("pet_friendly_per_attempt", OrderedDict((
            ("successes", pet_friendly), ("trials", attempted),
            ("point", round(pet_friendly / attempted, 4)),
            ("wilson_lower_95", round(wilson_lower(pet_friendly, attempted), 4)),
            ("wilson_upper_95", round(wilson_upper(pet_friendly, attempted), 4)),
            ("measured_by", "this market's own paid run, "
                            "PTF-GRAND-RAPIDS-HOLLAND-PAID-ACQUISITION-"
                            "AUTHORIZATION-009"),
        ))),
        ("url_recovered_per_discovery_lookup", OrderedDict((
            ("successes", 34), ("trials", 118),
            ("point", round(34 / 118, 4)),
            ("wilson_lower_95", round(wilson_lower(34, 118), 4)),
            ("wilson_upper_95", round(wilson_upper(34, 118), 4)),
            ("measured_by", "PTF-INDIANAPOLIS-PLACES-BROADER-RECOVERY-010"),
            ("borrowed", True),
            ("caveat", "another market's rate. Grand Rapids has never bought a "
                       "Places lookup, so this is the only measurement that "
                       "exists -- it is not a settled rate for this market and "
                       "the first paid batch should re-measure it."),
        ))),
    ))


def lane_plan_for(brands: Sequence[str]) -> Dict:
    """The cheapest QUALIFIED lane per brand family, from committed evidence."""
    ledger = PAL.load(LP / "ptf_paid_attempt_ledger_001.json")
    evidence = LQ.summarise([dict(a, provider=a.get("lane", ""))
                             for a in ledger["attempts"] if a.get("outcome")])
    costs = LQ.lane_costs()
    verdicts = LQ.qualify(evidence, available={p: c["available"]
                                               for p, c in costs.items()})
    out: "OrderedDict[str, Dict]" = OrderedDict()
    for family in sorted(set(brands)):
        out[family] = LQ.plan_lane(family, verdicts, costs)
    return OrderedDict((
        ("qualified_pairs", sorted("%s/%s" % (p, f) for (p, f), v
                                   in verdicts.items() if v["qualified"])),
        ("lane_costs", costs),
        ("by_family", out),
    ))


def paid_plan(gap: int, unresolved: Mapping[str, Sequence[str]],
              census: Mapping[str, Mapping]) -> Dict:
    """The smallest cohort that closes ``gap`` profiles, and what it costs.

    Two populations, and only one of them can be priced in dollars today.
    """
    rates = measured_rates()
    p_pf = rates["pet_friendly_per_attempt"]["wilson_lower_95"]
    p_url = rates["url_recovered_per_discovery_lookup"]["wilson_lower_95"]

    brand_excluded = list(unresolved["brand_excluded"])
    no_url = list(unresolved["no_url"])
    brands = [str(census.get(k, {}).get("canonical_name") or "") for k in brand_excluded]
    families = []
    for key in brand_excluded:
        name = str(census.get(key, {}).get("canonical_name") or "").lower()
        families.append("HYATT" if "hyatt" in name else "BEST_WESTERN")
    lanes = lane_plan_for(families)

    p_pf_high = rates["pet_friendly_per_attempt"]["wilson_upper_95"]
    p_url_high = rates["url_recovered_per_discovery_lookup"]["wilson_upper_95"]

    # How many lookups eight profiles would need at the conservative rate, and
    # how many rows actually exist to look up. The first number is larger, and
    # that is the whole shape of this plan: there is no cohort smaller than the
    # entire remaining pool that reaches the target, so the order's stop rule
    # never gets to bite.
    per_lookup = p_url * p_pf
    lookups_for_the_gap = math.ceil(gap / per_lookup) if per_lookup else 0
    lookups = len(no_url)

    urls_low = math.floor(lookups * p_url)
    urls_high = math.ceil(lookups * p_url_high)
    b_low = math.floor(urls_low * p_pf)
    b_high = math.floor(urls_high * p_pf_high)

    # Lane A: the five rows that already hold a property URL. Not optional
    # arithmetic -- lane B alone falls short at the conservative rate, and
    # counting on the point estimate to cover the difference is the optimism
    # the bound exists to refuse.
    a_low = math.floor(len(brand_excluded) * p_pf)
    a_high = math.floor(len(brand_excluded) * p_pf_high)

    costs = lanes["lane_costs"]
    browser = float(costs["brightdata_browser"]["usd_minor_per_property"])
    unlocker = float(costs["brightdata_web_unlocker"]["usd_minor_per_property"])

    # Yield and cost take opposite ends of the same interval: the profiles are
    # planned on the fewest that might come back, the money on the most rows
    # that might route. Every acquisition is priced at the DEFAULT lane because
    # a row whose URL nobody has seen has no brand family to qualify yet --
    # Firecrawl is preferred wherever a family IS qualified, and none can be
    # here until the lookups return.
    projected = round(urls_high * browser, 2)
    worst = round(urls_high * (browser + unlocker), 2)

    return OrderedDict((
        ("gap_to_close", gap),
        ("rates", rates),
        ("lane_a_rows_that_already_hold_a_url", OrderedDict((
            ("candidates", len(brand_excluded)),
            ("identity_keys", brand_excluded),
            ("families", OrderedDict(sorted(Counter(families).items()))),
            ("expected_pet_friendly_at_the_lower_bound", a_low),
            ("expected_pet_friendly_at_the_upper_bound", a_high),
            ("required_not_optional",
             "lane B alone reaches %d more profiles at the conservative rate "
             "and the target needs %d. These five are the difference."
             % (b_low, gap)),
            ("never_attempted", True),
            ("priceable_today", False),
            ("why_not_priceable",
             "the routing registry excludes HYATT and BEST_WESTERN as PREMIUM "
             "DOMAINS under the current Bright Data plan, and the registry says so "
             "in words: excluded on "
             "cost, not on capability. This repository commits no premium-"
             "domain unit price, so a dollar figure for these five would be "
             "invented. What they need first is that rate, or a founder "
             "decision to buy them at whatever the plan charges."),
            ("lane_qualification", lanes),
        ))),
        ("lane_b_rows_with_no_url_at_all", OrderedDict((
            ("population", len(no_url)),
            ("discovery_lookups_required", lookups),
            ("is_the_entire_remaining_pool", True),
            ("lookups_eight_profiles_would_need_at_the_lower_bound",
             lookups_for_the_gap),
            ("rows_that_actually_exist_to_look_up", len(no_url)),
            ("expected_urls_at_the_lower_bound", urls_low),
            ("expected_urls_at_the_upper_bound", urls_high),
            ("expected_pet_friendly_at_the_lower_bound", b_low),
            ("expected_pet_friendly_at_the_upper_bound", b_high),
            ("discovery_priced_in", "REQUESTS"),
            ("discovery_usd", None),
            ("why_no_discovery_dollar_figure",
             "this repository commits no USD rate for a Google Places "
             "searchText request; PTF-INDIANAPOLIS-PAID-OFFICIAL-URL-"
             "DISCOVERY-007 priced the same work in requests for the same "
             "reason. A dollar figure here would be invented."),
            ("acquisition_firecrawl_rows", 0),
            ("acquisition_brightdata_rows_at_the_upper_bound", urls_high),
            ("firecrawl_credits_required", 0),
            ("why_no_firecrawl",
             "Firecrawl is preferred wherever a family is already qualified, "
             "and no family can be known before its lookup returns a page. The "
             "plan therefore prices every acquisition at the SAFE DEFAULT lane; "
             "the real mix will be cheaper, and re-planning after the lookups "
             "is what makes that a measurement rather than a hope."),
            ("projected_brightdata_usd_minor", projected),
            ("worst_case_usd_minor", worst),
        ))),
        ("reaching_the_target", OrderedDict((
            ("target", TARGET_MIN),
            ("today", TARGET_MIN - gap),
            ("lane_b_alone_at_the_lower_bound", (TARGET_MIN - gap) + b_low),
            ("lane_a_plus_lane_b_at_the_lower_bound",
             (TARGET_MIN - gap) + b_low + a_low),
            ("lane_a_plus_lane_b_at_the_upper_bound",
             (TARGET_MIN - gap) + b_high + a_high),
            ("reaches_the_target_conservatively",
             (TARGET_MIN - gap) + b_low + a_low >= TARGET_MIN),
            ("finding",
             "the target is reachable only by buying the ENTIRE remaining "
             "market -- all %d rows that state no URL, plus the five "
             "premium-domain rows -- and even then it clears %d with no "
             "margin at the conservative rate. There is no smaller cohort, so "
             "the order's stop rule never binds."
             % (len(no_url), TARGET_MIN)),
        ))),
        ("recommended_hard_cap_usd_minor", int(math.ceil(worst))),
        ("recommended_authorization", OrderedDict((
            ("shape", "two authorizations, not one"),
            ("first",
             "a DISCOVERY authorization for %d Google Places searchText "
             "lookups over every row that states no URL, priced in requests, "
             "with the URL-recovery rate RE-MEASURED on the first batch before "
             "the rest run" % lookups),
            ("second",
             "an ACQUISITION authorization sized from that measured rate, "
             "capped at %d cents, with the lane mix re-planned once each row's "
             "brand family is known" % int(math.ceil(worst))),
            ("and_separately",
             "a decision on the five premium-domain rows, which need a rate "
             "this repository does not hold"),
        ))),
        ("stop_rule",
         "the cohort is sized to reach %d pet-friendly and no further; the "
         "order's stop rule forbids expanding it toward 50 merely because "
         "more rows exist" % TARGET_MIN),
    ))


# --------------------------------------------------------------------------- #
# The run
# --------------------------------------------------------------------------- #

def populations() -> Tuple[Dict[str, List[str]], Dict, Dict]:
    """The 114 unresolved rows, split by the cheapest path each one has."""
    census_doc = _load(LP / "identity_census" / ("%s.json" % MARKET))
    census = {h["identity_key"]: h for h in census_doc["hotels"]}
    package = _load(LP / ("hotel_policy_facts_%s.json" % MARKET))
    authority = _load(LP / ("%s_proposed_authority_022.json" % PREFIX))
    routing = {e["identity_key"]: e for e in
               _load(LP / ("%s_routing_recovered_001.json" % PREFIX))["entries"]}
    dry_run = _load(LP / ("%s_acquisition_dry_run_replay_018.json" % PREFIX))
    merged = {r["identity_key"] for r in dry_run["settled"]}

    published = {h["identity_key"] for h in package["hotels"]}
    excluded = {r["normalized_name"] for r in authority["verified_no_pets"]}
    unresolved = sorted(set(census) - published - excluded)

    buckets: Dict[str, List[str]] = {"dedup_merged_duplicate": [],
                                     "routed_with_a_saved_capture": [],
                                     "brand_excluded": [], "no_url": []}
    for key in unresolved:
        state = str(routing.get(key, {}).get("routing_state") or "")
        if key in merged:
            buckets["dedup_merged_duplicate"].append(key)
        elif state == "ROUTED":
            buckets["routed_with_a_saved_capture"].append(key)
        elif state == "ROUTE_BRAND_EXCLUDED":
            buckets["brand_excluded"].append(key)
        else:
            buckets["no_url"].append(key)
    return (buckets, census, OrderedDict((
        ("census", len(census)),
        ("published_pet_friendly", len(published)),
        ("verified_no_pets", len(excluded)),
        ("unresolved", len(unresolved)),
    )))


def founder_review(recovery: Mapping) -> Dict:
    """Exception-only, on the doctrines this market has already ruled.

    A row that states an affirmative refusal in its own words needs no reading:
    020's corrections established that a quoted sentence about pets is the
    fact, and both recoveries here are one. A row whose page never mentions a
    pet is the SOURCE SILENCE case the founder ruled on in 020 -- it stays
    unresolved and is not read as a refusal.

    Nothing is signed. Both clean rows would become EXCLUSIONS rather than
    profiles, and an exclusion is authority: it needs the same founder decision
    every other row got.
    """
    clean, exceptions = [], []
    for row in recovery["rows"]:
        entry = OrderedDict((
            ("identity_key", row["identity_key"]),
            ("verdict", row["verdict"]),
            ("quote", row["quote"]),
            ("capture", row["capture"]),
            ("rendered_html_sha256", row["rendered_html_sha256"]),
        ))
        if row["verdict"] == "VERIFIED_NO_PETS":
            entry["proposes"] = "VERIFIED_NO_PETS"
            entry["why"] = ("the property's own page states the refusal in "
                            "words, quoted above; nothing is inferred from a "
                            "fee or from a service-animal sentence")
            clean.append(entry)
        elif row["verdict"] == "SOURCE_SILENT":
            entry["proposes"] = "REMAINS_UNRESOLVED"
            entry["why"] = ("the saved page never mentions a pet. Source "
                            "silence is not a refusal -- the founder ruled "
                            "that in 020 and this pass does not reopen it")
            exceptions.append(entry)
        else:
            entry["proposes"] = "FOUNDER_READING_REQUIRED"
            exceptions.append(entry)
    return OrderedDict((
        ("binding_contract", "semantic-approval/1.0"),
        ("review_status", "MACHINE_REVIEWED_PENDING_OPERATOR"),
        ("founder_decision", ""),
        ("founder_reviewer_id", ""),
        ("clean_rows_needing_no_reading", clean),
        ("exceptions_needing_a_reading", exceptions),
        ("note",
         "both clean rows become EXCLUSIONS, not profiles. An exclusion is "
         "authority and needs the same founder decision every published row "
         "got, so nothing here is signed and the shard is unchanged."),
        ("would_move", OrderedDict((
            ("pet_friendly", 0),
            ("verified_no_pets", len(clean)),
        ))),
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)

    buckets, census, counts = populations()
    recovery = zero_cost_recovery()

    pet_friendly_now = counts["published_pet_friendly"]
    projected = pet_friendly_now + recovery["pet_friendly"]
    gap = max(TARGET_MIN - projected, 0)
    plan = paid_plan(gap, buckets, census) if gap else None

    report = OrderedDict((
        ("schema", "ptf-market-target-recovery/1.0"),
        ("what_this_is",
         "The cheapest path from %d pet-friendly profiles to %d. Every policy "
         "fact is re-located from HTML this project already owns; the paid "
         "cohort is priced and stopped before the money."
         % (pet_friendly_now, TARGET_MIN)),
        ("market_id", MARKET),
        ("work_order", WORK_ORDER),
        ("provider_calls", 0),
        ("usd_spent", 0.0),
        ("plan_credits_spent", 0.0),
        ("target", OrderedDict((("minimum", TARGET_MIN), ("maximum", TARGET_MAX)))),
        ("starting", counts),
        ("unresolved_populations", OrderedDict(
            (name, OrderedDict((("count", len(keys)), ("identity_keys", keys))))
            for name, keys in sorted(buckets.items()))),
        ("zero_cost_recovery", recovery),
        ("founder_review", founder_review(recovery)),
        ("projected_pet_friendly_after_zero_cost", projected),
        ("remaining_gap_to_%d" % TARGET_MIN, gap),
        ("authority_after_zero_cost", OrderedDict((
            ("pet_friendly", projected),
            ("verified_no_pets",
             counts["verified_no_pets"] + recovery["verified_no_pets"]),
            ("total", projected + counts["verified_no_pets"]
             + recovery["verified_no_pets"]),
        ))),
        ("paid_plan", plan),
        ("nothing_was_run", [
            "no provider was called",
            "no discovery lookup was bought",
            "no acquisition was run",
            "no founder decision was written",
            "the exclusion shard and the policy package are unchanged",
        ]),
    ))
    _write(LP / ("%s_target_recovery_025.json" % PREFIX), report)

    print("starting pet-friendly     : %d" % pet_friendly_now)
    print("zero-cost candidates      : %d" % recovery["reviewed"])
    for name, value in recovery["by_verdict"].items():
        print("   %-34s %d" % (name.lower(), value))
    print("zero-cost pet-friendly    : %d" % recovery["pet_friendly"])
    print("projected pet-friendly    : %d" % projected)
    print("remaining gap to %d       : %d" % (TARGET_MIN, gap))
    print("unresolved populations    :")
    for name, keys in sorted(buckets.items()):
        print("   %-34s %d" % (name, len(keys)))
    if plan:
        a = plan["lane_a_rows_that_already_hold_a_url"]
        b = plan["lane_b_rows_with_no_url_at_all"]
        print("lane A (already have a URL): %d rows, priceable=%s"
              % (a["candidates"], a["priceable_today"]))
        print("lane B (no URL)           : %d lookups -> %d-%d urls -> %d-%d profiles"
              % (b["discovery_lookups_required"],
                 b["expected_urls_at_the_lower_bound"],
                 b["expected_urls_at_the_upper_bound"],
                 b["expected_pet_friendly_at_the_lower_bound"],
                 b["expected_pet_friendly_at_the_upper_bound"]))
        print("firecrawl / brightdata    : %d / %d"
              % (b["acquisition_firecrawl_rows"],
                 b["acquisition_brightdata_rows_at_the_upper_bound"]))
        t = plan["reaching_the_target"]
        print("reaches 43 conservatively : %s  (lane B alone %d, +lane A %d, "
              "upper bound %d)"
              % (t["reaches_the_target_conservatively"],
                 t["lane_b_alone_at_the_lower_bound"],
                 t["lane_a_plus_lane_b_at_the_lower_bound"],
                 t["lane_a_plus_lane_b_at_the_upper_bound"]))
        print("projected / worst case    : %s / %s cents"
              % (b["projected_brightdata_usd_minor"], b["worst_case_usd_minor"]))
        print("recommended hard cap      : %d cents"
              % plan["recommended_hard_cap_usd_minor"])
    print("spend this order          : $0.00")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
