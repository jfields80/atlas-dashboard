"""PTF-HYATT-BEST-WESTERN-PREMIUM-RESOLUTION-028 -- the last excluded bucket.

Milwaukee's routable subset has been 127 since the router integration, and 127
was never the market. The census holds 147 identities. Six of the fourteen
outside the routable subset were excluded for one reason only: Hyatt and Best
Western are premium domains under the Bright Data plan, and the exclusion was
recorded in ``routes.json`` as a COST decision, never a capability one.

The plan now covers those domains, so the reason has expired.

NO ROUTE CHANGES, AND NOTHING TO ENABLE IN CODE
-----------------------------------------------
``registry.resolve`` never blocked these brands. ``excluded_brands`` is
advisory metadata; the resolver falls through to the default lane and returns
exactly what the committed queue already records for all six -- Browser API
first, Web Unlocker as the permitted fallback, generic reader. Premium-domain
handling is an entitlement on the Bright Data ZONE, not a request parameter, so
there is no flag for this module to set and no provider for it to add. The lane
IS the premium lane once the zone carries the entitlement.

That also means the entitlement cannot be verified by reading configuration:
the CLI's zone view exposes ``plan.product`` and ``perm`` and no premium field.
What verifies it is the acquisition. Hyatt previously answered 403 behind
Kasada; a Hyatt property page that renders is the evidence, and this work order
does not spend a request reproducing the old block first.

IDENTITY: THE CODE WAS AVAILABLE ALL ALONG
-------------------------------------------
Both brands put a property code in every URL and the identity census already
holds it -- ``MKEZA``, ``50056`` -- but neither brand had a pattern in
``PROPERTY_CODE_PATTERNS``, so both would have taken the code-less route 027
repaired. Adding the two patterns binds them the way Marriott and Hilton are
bound, which is stronger, and is scoped to those two brands by construction.

THE DENOMINATOR
---------------
``observed + unresolved == 127`` was an equation about the routable subset. The
market equation is over 147, and every census identity resolves to exactly one
final state: observed, active-but-unresolved, or one of the non-active census
dispositions the partition already records.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import hilton_decision_023 as H      # noqa: E402
from scripts.pettripfinder.acquisition import identity_binding_027 as I27   # noqa: E402
from scripts.pettripfinder.acquisition import registry as REGISTRY          # noqa: E402
from scripts.pettripfinder.acquisition import router as ROUTER              # noqa: E402
from scripts.pettripfinder.acquisition import source_selection as SS        # noqa: E402
from scripts.pettripfinder.acquisition import store_integration_025 as S    # noqa: E402
from scripts.pettripfinder.brightdata import corpus as CORPUS               # noqa: E402
from scripts.pettripfinder.brightdata import cross_brand_pilot_002 as P2    # noqa: E402
from scripts.pettripfinder.brightdata import policy_locator as PL           # noqa: E402
from scripts.pettripfinder.brightdata import policy_surface as PS           # noqa: E402

WORK_ORDER = "PTF-HYATT-BEST-WESTERN-PREMIUM-RESOLUTION-028"
MARKET = "milwaukee-wi"

REPORTS = REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
QUEUE_PATH = REPORTS / ("%s_policy_acquisition_queue_001.json" % MARKET)
STORE = REPORTS / ("%s_policy_proposals_001.json" % MARKET)
COUNTS_027 = REPORTS / ("%s_counts_027.json" % MARKET)
RUN_REPORT = REPORTS / "ptf_premium_resolution_028.json"
CENSUS_REPORT = REPORTS / ("%s_full_census_028.json" % MARKET)

CENSUS_PATH = (REPO / "launch_packages" / "pettripfinder" / "identity_census"
               / ("%s.json" % MARKET))
PARTITION_PATH = (REPO / "launch_packages" / "pettripfinder"
                  / "milwaukee_final_partition_001.json")

RUN_ID = "milwaukee-premium-028"
RUN_ROOT = REPO / "data" / "acquisition" / RUN_ID
RUN_DIR = RUN_ROOT / RUN_ID
JOURNAL = RUN_ROOT / "journal.jsonl"
COST_PATH = RUN_ROOT / "cost.json"

EXPECTED_EXCLUDED = 6
PREMIUM_BRANDS: Tuple[str, ...] = ("HYATT", "BEST_WESTERN")
BILLABLE_ZONES = ("scraping_browser1", "mcp_unlocker", "cli_unlocker")

# --- Phase 2 dispositions ---------------------------------------------------
ACTIVE = "ACTIVE_POLICY_ACQUISITION_REQUIRED"
RETIRED = "RETIRED_OR_CONVERTED"
DUPLICATE = "DUPLICATE"
CATEGORY_EXCLUDED = "CATEGORY_EXCLUDED"
BOUNDARY_EXCLUDED = "BOUNDARY_EXCLUDED"
IDENTITY_UNRESOLVED = "IDENTITY_UNRESOLVED"

# --- Phase 7/8 premium audit verdicts ---------------------------------------
PREMIUM_ACCESS_SUCCESS = "PREMIUM_ACCESS_SUCCESS"
PREMIUM_ACCESS_BUT_POLICY_NOT_PRESENT = "PREMIUM_ACCESS_BUT_POLICY_NOT_PRESENT"
PREMIUM_ACCESS_BUT_READER_OR_LOCATOR_ISSUE = (
    "PREMIUM_ACCESS_BUT_READER_OR_LOCATOR_ISSUE")
PREMIUM_ACCESS_FAILURE = "PREMIUM_ACCESS_FAILURE"

# --- Phase 10 full-census final states ---------------------------------------
OBSERVED = "OBSERVED"
TOUCHED_UNRESOLVED = "TOUCHED_UNRESOLVED"
NO_OFFICIAL_URL = "NO_OFFICIAL_URL"
CENSUS_REVIEW = "CENSUS_REVIEW"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


# --------------------------------------------------------------------------- #
# Phase 1 -- preflight and the six.
# --------------------------------------------------------------------------- #

def queue() -> Dict[str, Dict]:
    doc = json.loads(QUEUE_PATH.read_text(encoding="utf-8-sig"))
    return {row["identity_key"]: row for row in doc["items"]}


def census() -> Dict[str, Dict]:
    doc = json.loads(CENSUS_PATH.read_text(encoding="utf-8-sig"))
    return {row["identity_key"]: row for row in doc["hotels"]}


def partition() -> Dict[str, Dict]:
    doc = json.loads(PARTITION_PATH.read_text(encoding="utf-8-sig"))
    return {row["identity_key"]: row for row in doc["items"]}


def excluded_bucket() -> List[Dict]:
    """The brand-excluded identities, derived from the committed queue.

    ``brand_excluded`` is a field the queue builder set from ``routes.json``'s
    ``excluded_brands``; nothing here names a brand or a property.
    """
    return sorted((row for row in queue().values() if row["brand_excluded"]),
                  key=lambda row: (row["brand"], row["identity_key"]))


def assert_bucket() -> List[Dict]:
    rows = excluded_bucket()
    if len(rows) != EXPECTED_EXCLUDED:
        raise SystemExit("ABORT: brand-excluded bucket is %d, expected %d"
                         % (len(rows), EXPECTED_EXCLUDED))
    brands = {row["brand"] for row in rows}
    if not brands <= set(PREMIUM_BRANDS):
        raise SystemExit("ABORT: bucket carries brands outside the premium "
                         "set: %s" % sorted(brands - set(PREMIUM_BRANDS)))
    return rows


def _store_rows_before() -> Optional[int]:
    """The row count the last store integration started from."""
    path = REPORTS / "ptf_milwaukee_store_integration_025.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig")).get("rows_before")


def preflight() -> Dict:
    from scripts.pettripfinder.acquisition import providers as PROVIDERS
    from scripts.pettripfinder.brightdata import client as CLIENT

    store = json.loads(STORE.read_text(encoding="utf-8-sig"))
    rows = excluded_bucket()
    queued = queue()
    health = PROVIDERS.get("brightdata_browser").health_check()
    return {
        "checked_at": _now(),
        "census_total": len(census()),
        "partition_total": len(partition()),
        "queue_total": len(queued),
        "routable": sum(1 for row in queued.values()
                        if not row["brand_excluded"]),
        "brand_excluded": len(rows),
        "store_rows": len(store["items"]),
        "store_rows_before_this_run": _store_rows_before(),
        "published": sum(1 for row in store["items"] if row.get("published")),
        "authority_written": bool(store.get("authority_written")),
        "authority_files": len(list(
            (REPO / "launch_packages" / "pettripfinder")
            .rglob("*hotel_policy_facts*milwaukee*"))),
        "browser_credential_present": CLIENT.credential_present(),
        "browser_zone": CLIENT.ZONE,
        "browser_provider_available": bool(health.available),
        # What the zone view actually exposes. Premium-domain handling is an
        # account entitlement and no field here reports it, so this records
        # what is verifiable and leaves the entitlement to be proved by the
        # acquisition rather than asserted from configuration.
        "premium_entitlement_verifiable_from_config": False,
        "premium_entitlement_verified_by": "live acquisition of a premium "
                                           "domain that previously refused us",
        "excluded_brands_in_routes": sorted(REGISTRY.excluded_brands()),
        "assertions": {
            "census_is_147": len(census()) == 147,
            "routable_is_127": sum(1 for row in queued.values()
                                   if not row["brand_excluded"]) == 127,
            "excluded_brand_count_is_6": len(rows) == EXPECTED_EXCLUDED,
            # The store this work order STARTED from. Asserted against the
            # integration report's own baseline rather than the live row
            # count, which this work order then moves -- a preflight that
            # fails once its own run succeeds is not a preflight.
            "store_before_this_run_was_110": _store_rows_before() == 110,
            "nothing_published": all(not row.get("published")
                                     for row in store["items"]),
            "authority_absent": not bool(store.get("authority_written")),
        },
    }


# --------------------------------------------------------------------------- #
# Phase 2 -- one disposition per excluded identity.
# --------------------------------------------------------------------------- #

def classify(key: str) -> Dict:
    """The single operational disposition of one excluded identity.

    Read from the committed census and partition, never decided here. An
    identity is only ACTIVE when the census confirms both that it IS this
    property and that it IS lodging, and the partition's block is the policy
    observation rather than an identity or category hold.
    """
    row = queue()[key]
    record = census()[key]
    part = partition().get(key, {})
    state = part.get("final_state", "")
    if record["identity_state"] == "IDENTITY_UNRESOLVED":
        disposition = IDENTITY_UNRESOLVED
    elif record["lodging_state"] != "LODGING_CONFIRMED":
        disposition = CATEGORY_EXCLUDED
    elif record["disposition"] != "canonical":
        disposition = DUPLICATE
    elif (record.get("former_name") or "") and not record.get("official_url"):
        disposition = RETIRED
    elif state == "AWAITING_POLICY_OBSERVATION":
        disposition = ACTIVE
    else:
        disposition = IDENTITY_UNRESOLVED
    return {
        "identity_key": key,
        "canonical_name": row["canonical_name"],
        "brand": row["brand"],
        "address": "%s, %s %s %s" % (row["address"], row["city"],
                                     row["state"], row["postal_code"]),
        "official_url": row["official_url"],
        "property_code": row["property_code"],
        "partition_state": state,
        "queue_state": row["queue_state"],
        "excluded_because": row["brand_exclusion_reason"],
        "identity_state": record["identity_state"],
        "lodging_state": record["lodging_state"],
        "collision_state": record["collision_state"],
        "census_disposition": record["disposition"],
        "census_source": record["source"],
        "corroborating_sources": list(record.get("corroborating_sources") or ()),
        "census_note": record.get("census_note") or "",
        "valid_lodging_inventory": record["lodging_state"] == "LODGING_CONFIRMED",
        "disposition": disposition,
        "acquisition_required": disposition == ACTIVE,
    }


def classified() -> List[Dict]:
    return [classify(row["identity_key"]) for row in assert_bucket()]


# --------------------------------------------------------------------------- #
# Phase 3 -- source identity, without reading a word of policy.
# --------------------------------------------------------------------------- #

def verify_source(entry: Mapping) -> Dict:
    """Does the first-party URL carry this property's own code?

    Structural only. Nothing here fetches a page, and nothing here looks at pet
    policy: a source is verified when the URL the census recorded resolves to
    the code the census recorded, on the brand's own host.
    """
    url = entry["official_url"]
    brand = entry["brand"]
    derived = PS.property_code(url, brand)
    census_code = (entry["property_code"] or "").lower()
    host = re.sub(r"^https?://", "", url or "").split("/")[0].lower()
    expected_host = {"HYATT": "www.hyatt.com",
                     "BEST_WESTERN": "www.bestwestern.com"}.get(brand, "")
    return {
        "identity_key": entry["identity_key"],
        "brand": brand,
        "official_url": url,
        "host": host,
        "first_party_host": bool(expected_host) and host == expected_host,
        "code_in_url": derived,
        "code_in_census": census_code,
        "code_binding": bool(derived) and derived == census_code,
        "brand_index_sources": ([entry["census_source"]]
                                + list(entry["corroborating_sources"])),
        "verified": (bool(expected_host) and host == expected_host
                     and bool(derived) and derived == census_code),
        "policy_wording_inspected": False,
    }


# --------------------------------------------------------------------------- #
# Phase 4 -- the lane, resolved from the committed registry.
# --------------------------------------------------------------------------- #

def lane(entry: Mapping) -> Dict:
    route = REGISTRY.resolve(brand=entry["brand"], url=entry["official_url"],
                             identity_key=entry["identity_key"])
    return {
        "identity_key": entry["identity_key"],
        "provider": route.provider,
        "ladder": list(route.ladder),
        "fallback_providers": list(route.fallback_providers),
        "forbidden_providers": list(route.forbidden_providers),
        "reader": route.reader,
        "resolved_by": route.resolved_by,
        "premium_domain": entry["brand"] in PREMIUM_BRANDS,
        "firecrawl_in_ladder": "firecrawl" in route.ladder,
    }


# --------------------------------------------------------------------------- #
# Phase 5 -- the cost guard.
# --------------------------------------------------------------------------- #

#: What a premium domain is assumed to multiply the standard Browser API rate
#: by. Bright Data does not expose a premium rate through the CLI or the zone
#: view, so this is an ASSUMPTION and is labelled one everywhere it is used.
#: It exists to bound the run before it starts, not to predict the invoice.
PREMIUM_MULTIPLIER_LOW = 2.0
PREMIUM_MULTIPLIER_EXPECTED = 2.5
PREMIUM_MULTIPLIER_HIGH = 3.0

#: Measured usd_minor per property on the standard Browser lane. The low figure
#: is the router-integration run's average and the high is 027's, which carried
#: several long navigations and three discarded captures.
STANDARD_LOW_USD_MINOR = 16
STANDARD_EXPECTED_USD_MINOR = 45
STANDARD_HIGH_USD_MINOR = 68


def cost_estimate(active: int) -> Dict:
    return {
        "active_properties": active,
        "basis": ("measured usd_minor per property on the standard Browser "
                  "lane across the router-integration run and 027"),
        "standard_usd_minor_per_property": {
            "low": STANDARD_LOW_USD_MINOR,
            "expected": STANDARD_EXPECTED_USD_MINOR,
            "high": STANDARD_HIGH_USD_MINOR,
        },
        "premium_multiplier": {
            "low": PREMIUM_MULTIPLIER_LOW,
            "expected": PREMIUM_MULTIPLIER_EXPECTED,
            "high": PREMIUM_MULTIPLIER_HIGH,
            "status": "ASSUMPTION -- Bright Data exposes no premium rate "
                      "through the CLI or the zone view",
        },
        "estimated_usd_minor": {
            "low": int(active * STANDARD_LOW_USD_MINOR
                       * PREMIUM_MULTIPLIER_LOW),
            "expected": int(active * STANDARD_EXPECTED_USD_MINOR
                            * PREMIUM_MULTIPLIER_EXPECTED),
            "high": int(active * STANDARD_HIGH_USD_MINOR
                        * PREMIUM_MULTIPLIER_HIGH),
        },
        "route_frozen_for_the_run": True,
    }


# --------------------------------------------------------------------------- #
# Phase 6 -- acquisition, on the committed route.
# --------------------------------------------------------------------------- #

def _record_for(row: Mapping) -> CORPUS.BenchmarkRecord:
    """A benchmark record carrying the census identity, and no policy value."""
    return CORPUS.BenchmarkRecord(
        identity_key=row["identity_key"], name=row["canonical_name"],
        market_id=MARKET, brand=row["brand"],
        bucket=CORPUS.bucket_of(row["brand"]), source_url=row["official_url"],
        pets_allowed=None, facts={}, quotes=(), withheld_fields={},
        service_animal_statement="", categories=frozenset(), origin="census",
        street=row.get("address", ""), postal_code=row.get("postal_code", ""),
        phone=row.get("phone", ""),
        locality="%s %s" % (row.get("city", ""), row.get("state", "")))


async def acquire(row: Mapping) -> Dict:
    selection = SS.select(row["identity_key"], row["official_url"],
                          market_id=MARKET)
    record = _record_for(row)
    target = P2.target_for(record)
    if selection.selected_url != row["official_url"]:
        target = SS._retargeted(target, selection.selected_url)

    began = time.monotonic()
    result = await ROUTER.route_property(
        record, target, run_dir=RUN_DIR, run_id=RUN_ID,
        registry=REGISTRY.load(), route_url=row["official_url"])
    document = result.document
    identity = dict((document.identity or {}) if document is not None else {})
    attempt_records = [attempt.to_dict() for attempt in (result.attempts or ())]
    verdict = I27.identity_verdict(attempt_records, identity)
    usable = I27.assess_usable(document, identity_confirmed=verdict == "PASS")
    return {
        "identity_key": row["identity_key"],
        "canonical_name": row["canonical_name"],
        "brand": row["brand"],
        "premium_domain": row["brand"] in PREMIUM_BRANDS,
        "source_url": selection.selected_url,
        "census_url": row["official_url"],
        "source_origin": selection.source,
        "overlay_status": selection.overlay_status,
        "provider_primary": (result.route or {}).get("provider", ""),
        "provider_used": (result.attempts[-1].provider
                          if result.attempts else ""),
        "providers_tried": list(result.providers_tried),
        "attempts": len(result.attempts),
        "attempt_records": attempt_records,
        "final_state": result.state,
        "acquisition_status": ("ACQUIRED" if document is not None
                               else "NOT_ACQUIRED"),
        "identity_verdict": verdict,
        "identity_confirmed": verdict == "PASS",
        "identity_binding_method": identity.get("binding_method", ""),
        "identity_matched": list(identity.get("matched", [])),
        "identity_conflicting": list(identity.get("conflicting", [])),
        "identity_reasons": list(identity.get("reasons", [])),
        "identity_signals": dict(identity.get("signals", {})),
        "policy_locator": (document.policy_locator if document else ""),
        "policy_block": usable.get("block_text", ""),
        "policy_block_chars": usable.get("block_chars", 0),
        "reader": (result.route or {}).get("reader", ""),
        "reader_fields": usable.get("substantive_fields", []),
        "reader_withheld": usable.get("withheld_fields", []),
        "states_a_refusal": usable.get("states_a_refusal", False),
        "reader_read_it_as_a_refusal": usable.get("reader_read_it_as_a_refusal"),
        "publication_grade": result.state == "ACQUIRED_PUBLICATION_GRADE",
        "usable_policy": usable["verdict"],
        "usable_policy_detail": usable,
        "canonical_artifacts": canonical_artifacts(target.slug),
        "failure": result.failure,
        "failure_class": result.failure_class,
        "elapsed_seconds": round(time.monotonic() - began, 3),
        "estimated_bytes": result.cost.estimated_bytes,
        "completed_at": _now(),
    }


def canonical_artifacts(slug: str) -> Dict:
    base = RUN_DIR / slug
    attempt = None
    if base.is_dir():
        for candidate in sorted(base.glob("attempt-*"), reverse=True):
            if (candidate / PL.BLOCK_ARTIFACT).is_file():
                attempt = candidate
                break
    if attempt is None:
        return {"present": False}
    replayed = PL.replay(attempt)
    return {
        "present": True,
        "attempt_dir": _rel(attempt),
        "policy_block": (attempt / PL.BLOCK_ARTIFACT).is_file(),
        "locator_json": (attempt / PL.LOCATOR_ARTIFACT).is_file(),
        "replay_status": replayed.status,
        "block_sha256": replayed.block_sha256,
        "canonical": replayed.canonical,
    }


def run(*, limit: int = 0) -> List[Dict]:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    done: Dict[str, Dict] = {}
    if JOURNAL.is_file():
        for line in JOURNAL.read_text(encoding="utf-8").splitlines():
            if line.strip():
                entry = json.loads(line)
                done[entry["identity_key"]] = entry

    rows = queue()
    plan = [entry for entry in classified() if entry["acquisition_required"]]
    todo = [entry for entry in plan if entry["identity_key"] not in done]
    if limit:
        todo = todo[:limit]
    for entry in todo:
        result = asyncio.run(acquire(rows[entry["identity_key"]]))
        with JOURNAL.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")
        done[result["identity_key"]] = result
    return [done[entry["identity_key"]] for entry in plan
            if entry["identity_key"] in done]


def journal_rows() -> List[Dict]:
    """Journalled acquisitions, with every verdict re-derived on load."""
    if not JOURNAL.is_file():
        return []
    latest: Dict[str, Dict] = {}
    for line in JOURNAL.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        verdict = I27.identity_verdict(row.get("attempt_records"),
                                       {"confirmed": False})
        row["identity_verdict"] = verdict
        row["identity_confirmed"] = verdict == "PASS"
        row["usable_policy_detail"] = I27._rescore_usable(
            row.get("usable_policy_detail") or {}, verdict == "PASS",
            withheld=row.get("reader_withheld") or ())
        row["usable_policy"] = row["usable_policy_detail"].get(
            "verdict", row.get("usable_policy", ""))
        latest[row["identity_key"]] = row
    return list(latest.values())


# --------------------------------------------------------------------------- #
# Phase 7 / 8 -- what the premium lane actually bought.
# --------------------------------------------------------------------------- #

def premium_audit(row: Mapping) -> Dict:
    """Access, identity, surface and structure, kept apart.

    A provider that retrieves the page it was asked for has succeeded, whatever
    the page then turns out to say. Calling that a provider failure is how a
    lane gets replaced for a problem it does not have.
    """
    reached = any(record.get("outcome") in ("VALID", "POLICY_NOT_FOUND",
                                            "IDENTITY_MISMATCH")
                  for record in row.get("attempt_records") or ())
    identity_ok = row["identity_verdict"] == "PASS"
    block = (row.get("policy_block") or "").strip()
    structured = row["usable_policy"] == H.USABLE
    if not reached:
        verdict = PREMIUM_ACCESS_FAILURE
    elif not identity_ok:
        verdict = PREMIUM_ACCESS_BUT_READER_OR_LOCATOR_ISSUE
    elif structured:
        verdict = PREMIUM_ACCESS_SUCCESS
    elif not block:
        verdict = PREMIUM_ACCESS_BUT_POLICY_NOT_PRESENT
    else:
        verdict = PREMIUM_ACCESS_BUT_READER_OR_LOCATOR_ISSUE
    return {
        "identity_key": row["identity_key"],
        "canonical_name": row["canonical_name"],
        "brand": row["brand"],
        "full_property_page": reached and row["acquisition_status"] == "ACQUIRED",
        "page_reached": reached,
        "correct_identity": identity_ok,
        "identity_binding_method": row.get("identity_binding_method", ""),
        "meaningful_policy_surface": bool(block),
        "policy_block_chars": row.get("policy_block_chars", 0),
        "usable_structured_policy": structured,
        "publication_grade": bool(row.get("publication_grade")),
        "verdict": verdict,
        "provider_used": row.get("provider_used", ""),
        "failure": row.get("failure", ""),
    }


def audits() -> List[Dict]:
    return [premium_audit(row) for row in journal_rows()]


# --------------------------------------------------------------------------- #
# Phase 10 -- the full 147.
# --------------------------------------------------------------------------- #

def full_census() -> Dict:
    """Every census identity in exactly one final operational state.

    The partition already resolves all 147 into four states; this maps them to
    operational meaning and splits the queued ones by whether an observation
    exists. No identity may appear twice and none may be missing, and the
    reconciliation asserts both rather than reporting a total that happens to
    add up.
    """
    records = census()
    parts = partition()
    queued = queue()
    store = json.loads(STORE.read_text(encoding="utf-8-sig"))
    observed = {item["identity_key"] for item in store["items"]}

    rows: List[Dict] = []
    for key, record in records.items():
        part = parts.get(key, {})
        state = part.get("final_state", "")
        brand = (queued.get(key) or {}).get("brand", "")
        if key in observed:
            final = OBSERVED
        elif state == "AWAITING_POLICY_OBSERVATION":
            final = TOUCHED_UNRESOLVED
        elif state == "AWAITING_OFFICIAL_URL":
            final = NO_OFFICIAL_URL
        elif state == "AWAITING_IDENTITY_RESOLUTION":
            final = IDENTITY_UNRESOLVED
        elif state == "AWAITING_CENSUS_REVIEW":
            final = CENSUS_REVIEW
        else:
            final = "UNCLASSIFIED"
        rows.append({
            "identity_key": key,
            "canonical_name": record["canonical_name"],
            "brand": brand,
            "partition_state": state,
            "identity_state": record["identity_state"],
            "lodging_state": record["lodging_state"],
            "in_queue": key in queued,
            "final_state": final,
            # Active eligible = the market we can actually work: confirmed
            # lodging, confirmed identity, and a first-party page to read.
            "active_eligible": (record["lodging_state"] == "LODGING_CONFIRMED"
                                and record["identity_state"]
                                == "IDENTITY_CONFIRMED"
                                and state == "AWAITING_POLICY_OBSERVATION"),
        })

    counts = Counter(row["final_state"] for row in rows)
    keys = [row["identity_key"] for row in rows]
    # The work order's taxonomy, answered in full -- including the buckets that
    # are empty. Reporting only the non-zero states would leave a reader to
    # guess whether "retired" was zero or unexamined.
    #
    # CENSUS_REVIEW is deliberately NOT folded into CATEGORY_EXCLUDED. Three
    # identities have lodging_state NEEDS_REVIEW, which says the category is in
    # QUESTION; an exclusion says it was settled. Those are different claims
    # and only one of them is true here.
    phase11 = {
        "CENSUS_TOTAL": len(rows),
        "ACTIVE_ELIGIBLE_TOTAL": sum(1 for row in rows
                                     if row["active_eligible"]),
        "OBSERVED": counts.get(OBSERVED, 0),
        "TOUCHED_UNRESOLVED": counts.get(TOUCHED_UNRESOLVED, 0),
        "RETIRED_OR_CONVERTED": counts.get(RETIRED, 0),
        "DUPLICATE": counts.get(DUPLICATE, 0),
        "CATEGORY_EXCLUDED": counts.get(CATEGORY_EXCLUDED, 0),
        "BOUNDARY_EXCLUDED": counts.get(BOUNDARY_EXCLUDED, 0),
        "IDENTITY_UNRESOLVED": counts.get(IDENTITY_UNRESOLVED, 0),
        "OTHER": counts.get(NO_OFFICIAL_URL, 0) + counts.get(CENSUS_REVIEW, 0),
    }
    mutually_exclusive = [k for k in phase11
                          if k not in ("CENSUS_TOTAL",
                                       "ACTIVE_ELIGIBLE_TOTAL")]
    return {
        "phase11_final_states": phase11,
        "phase11_sum": sum(phase11[k] for k in mutually_exclusive),
        "other_breakdown": {"NO_OFFICIAL_URL": counts.get(NO_OFFICIAL_URL, 0),
                            "CENSUS_REVIEW": counts.get(CENSUS_REVIEW, 0)},
        "census_total": len(rows),
        "unique_identities": len(set(keys)),
        "each_identity_exactly_once": len(keys) == len(set(keys)),
        "final_state_counts": dict(counts),
        "sum_of_final_states": sum(counts.values()),
        "active_eligible_total": sum(1 for row in rows if row["active_eligible"]),
        "active_eligible_observed": sum(1 for row in rows
                                        if row["active_eligible"]
                                        and row["final_state"] == OBSERVED),
        "active_eligible_unresolved": sum(1 for row in rows
                                          if row["active_eligible"]
                                          and row["final_state"]
                                          == TOUCHED_UNRESOLVED),
        "rows": rows,
    }


def exception_queue() -> Dict:
    """Active acquisition exceptions, kept apart from census dispositions."""
    reconciliation = full_census()
    active: List[Dict] = []
    for row in reconciliation["rows"]:
        if row["final_state"] != TOUCHED_UNRESOLVED:
            continue
        reason, detail = I27.unresolved_reason(row["identity_key"])
        fresh = {entry["identity_key"]: entry for entry in journal_rows()}
        if row["identity_key"] in fresh:
            entry = fresh[row["identity_key"]]
            audit = premium_audit(entry)
            reason = (PREMIUM_ACCESS_FAILURE
                      if audit["verdict"] == PREMIUM_ACCESS_FAILURE
                      else "POLICY_NOT_PRESENT"
                      if audit["verdict"] == PREMIUM_ACCESS_BUT_POLICY_NOT_PRESENT
                      else "INSUFFICIENT_EVIDENCE"
                      if audit["correct_identity"] else "IDENTITY_FAILURE")
            detail = {"source_run": RUN_ID,
                      "final_state": entry.get("final_state", "")}
        active.append({
            "identity_key": row["identity_key"],
            "canonical_name": row["canonical_name"],
            "brand": row["brand"],
            "reason": reason or "INSUFFICIENT_EVIDENCE",
            "source_run": detail.get("source_run", ""),
            "final_state": detail.get("final_state", ""),
        })
    non_active = [
        {"identity_key": row["identity_key"],
         "canonical_name": row["canonical_name"],
         "disposition": row["final_state"]}
        for row in reconciliation["rows"]
        if row["final_state"] in (NO_OFFICIAL_URL, IDENTITY_UNRESOLVED,
                                  CENSUS_REVIEW)]
    return {
        "active_acquisition_exceptions": {
            "count": len(active),
            "by_reason": dict(Counter(row["reason"] for row in active)),
            "queue": sorted(active, key=lambda row: row["identity_key"]),
        },
        "non_active_census_dispositions": {
            "count": len(non_active),
            "by_disposition": dict(Counter(row["disposition"]
                                           for row in non_active)),
            "queue": sorted(non_active, key=lambda row: row["identity_key"]),
        },
    }


def held_structured_data() -> Dict:
    store = json.loads(STORE.read_text(encoding="utf-8-sig"))
    counts = Counter(item["review_status"] for item in store["items"])
    return {
        "note": ("observation and review states, not unattempted acquisition; "
                 "every row counted here HAS a current-state observation"),
        "HELD_SCHEMA_CANNOT_REPRESENT": counts.get(
            "HELD_SCHEMA_CANNOT_REPRESENT", 0),
        "HELD_INSUFFICIENT_EVIDENCE": counts.get(
            "HELD_INSUFFICIENT_EVIDENCE", 0),
        "HELD_SEMANTIC_REVIEW": counts.get("HELD_SEMANTIC_REVIEW", 0),
        "CURRENT_STATE_CONFLICT": counts.get("CURRENT_STATE_CONFLICT", 0),
        "all_review_states": dict(counts),
    }


# --------------------------------------------------------------------------- #
# Cost.
# --------------------------------------------------------------------------- #

def record_spend(label: str) -> Dict:
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    ledger = {}
    if COST_PATH.is_file():
        ledger = json.loads(COST_PATH.read_text(encoding="utf-8"))
    ledger[label] = I27.read_spend(label)
    if "before" in ledger and "after" in ledger:
        ledger["delta"] = I27.spend_delta(ledger["before"], ledger["after"])
    COST_PATH.write_text(json.dumps(ledger, indent=2), encoding="utf-8")
    return ledger


def usage_summary() -> Dict:
    rows = journal_rows()
    requests = sum(len(row.get("attempt_records") or ()) for row in rows)
    browser = sum(1 for row in rows
                  for record in (row.get("attempt_records") or ())
                  if record.get("provider") == "brightdata_browser")
    unlocker = sum(1 for row in rows
                   for record in (row.get("attempt_records") or ())
                   if record.get("provider") == "brightdata_web_unlocker")
    firecrawl = sum(1 for row in rows
                    for record in (row.get("attempt_records") or ())
                    if record.get("provider") == "firecrawl")
    moved = sum(row.get("estimated_bytes") or 0 for row in rows)
    ledger = json.loads(COST_PATH.read_text(encoding="utf-8")) \
        if COST_PATH.is_file() else {}
    return {
        "premium_browser_requests": browser,
        "standard_browser_requests": 0,
        "web_unlocker_requests": unlocker,
        "firecrawl_requests": firecrawl,
        "total_provider_requests": requests,
        "cdp_reported_bytes": moved,
        "cdp_reported_gb": round(moved / 1e9, 4),
        "cdp_caveat": ("CDP under-reports billable traffic; these bytes are "
                       "what the browser saw, never a billing figure"),
        "meter": ledger,
        "attribution": ("the meter delta spans this run's window only; prior "
                        "Milwaukee spend is not attributed here"),
    }


# --------------------------------------------------------------------------- #
# Reporting.
# --------------------------------------------------------------------------- #

def premium_entitlement_evidence() -> Dict:
    """Which zone actually carries premium access, measured rather than assumed.

    The zone view exposes no premium field, so the entitlement is read off the
    attempts. Two things fell out of the run that no configuration would have
    told us:

    * ``cli_unlocker`` refused bestwestern.com by name -- "requires Premium
      permissions" -- while ``mcp_unlocker`` fetched hyatt.com without
      complaint. The entitlement is per-zone, and one of the two unlocker zones
      does not have it.
    * The two brands need OPPOSITE lanes. The Browser API rendered Best Western
      three times out of three and returned a BLANK PAGE on every Hyatt attempt;
      the Web Unlocker did the reverse. Kasada was never a premium-domain
      problem, and premium access did not solve it -- the escalation ladder did.

    Recorded as a finding. Routing is not changed here.
    """
    rows = journal_rows()
    by_zone: Dict[str, Dict] = {}
    for row in rows:
        for record in row.get("attempt_records") or ():
            zone = ""
            for note in record.get("interactions") or ():
                if "zone '" in note:
                    zone = note.split("zone '")[1].split("'")[0]
            key = zone or record.get("provider", "")
            slot = by_zone.setdefault(key, {"attempts": 0, "outcomes": {},
                                            "premium_permission_error": False})
            slot["attempts"] += 1
            outcome = record.get("outcome", "")
            slot["outcomes"][outcome] = slot["outcomes"].get(outcome, 0) + 1
            if "requires Premium permissions" in (record.get("detail") or ""):
                slot["premium_permission_error"] = True
    lane_by_brand: Dict[str, Dict] = {}
    for row in rows:
        slot = lane_by_brand.setdefault(row["brand"], {})
        for record in row.get("attempt_records") or ():
            provider = record.get("provider", "")
            entry = slot.setdefault(provider, {"attempts": 0, "valid": 0})
            entry["attempts"] += 1
            if record.get("outcome") == "VALID":
                entry["valid"] += 1
    return {
        "verifiable_from_zone_config": False,
        "by_zone": by_zone,
        "lane_that_worked_by_brand": lane_by_brand,
        "finding": ("premium access is per-zone: cli_unlocker refused "
                    "bestwestern.com by name -- 'requires Premium "
                    "permissions' -- while scraping_browser1 and "
                    "mcp_unlocker reached their targets"),
        "finding_provenance": (
            "the cli_unlocker refusal was observed in this run's FIRST Best "
            "Western pass, which was discarded and re-run when the "
            "locator-brand/identity-brand defect was corrected. It is "
            "therefore not reproducible from the retained journal below, and "
            "is reported as an observation rather than as evidence this "
            "artifact carries. The retained journal shows only the zones that "
            "succeeded, because the corrected run never needed the second "
            "unlocker zone."),
        "second_finding": ("the two brands need opposite lanes -- the Browser "
                           "API rendered Best Western and blank-paged every "
                           "Hyatt attempt, and the Web Unlocker did the "
                           "reverse; the committed escalation ladder covered "
                           "both without a route change"),
    }


def build_report() -> Dict:
    entries = classified()
    active = [entry for entry in entries if entry["acquisition_required"]]
    rows = journal_rows()
    audit_rows = audits()
    by_brand = Counter(entry["brand"] for entry in active)
    acquired = Counter(row["brand"] for row in rows
                       if row["acquisition_status"] == "ACQUIRED")
    return {
        "schema": "ptf-premium-resolution/1.0",
        "work_order": WORK_ORDER,
        "market": MARKET,
        "run_id": RUN_ID,
        "generated_at": _now(),
        "preflight": preflight(),
        "bucket": entries,
        "dispositions": dict(Counter(entry["disposition"]
                                     for entry in entries)),
        "source_verification": [verify_source(entry) for entry in active],
        "lanes": [lane(entry) for entry in active],
        "cost_estimate": cost_estimate(len(active)),
        "attempted_by_brand": dict(by_brand),
        "acquired_by_brand": dict(acquired),
        "premium_audit": audit_rows,
        "premium_entitlement": premium_entitlement_evidence(),
        "premium_audit_counts": dict(Counter(row["verdict"]
                                             for row in audit_rows)),
        "usable_policy": sum(1 for row in rows
                             if row["usable_policy"] == H.USABLE),
        "publication_grade": sum(1 for row in rows if row["publication_grade"]),
        "full_census": full_census(),
        "exception_queue": exception_queue(),
        "held_structured_data": held_structured_data(),
        "cost": usage_summary(),
        "authority_written": False,
        "published": 0,
        "rows": rows,
    }


def write_report() -> Dict:
    doc = build_report()
    RUN_REPORT.write_text(json.dumps(doc, indent=2, ensure_ascii=False),
                          encoding="utf-8")
    reconciliation = doc["full_census"]
    CENSUS_REPORT.write_text(
        json.dumps({"schema": "ptf-milwaukee-full-census/1.0",
                    "work_order": WORK_ORDER, "market": MARKET,
                    "generated_at": doc["generated_at"],
                    **reconciliation}, indent=2, ensure_ascii=False),
        encoding="utf-8")
    return doc


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=WORK_ORDER)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--classify", action="store_true")
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--meter", choices=("before", "after"))
    parser.add_argument("--acquire", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--census", action="store_true")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args(argv)

    if args.preflight:
        print(json.dumps(preflight(), indent=2))
    if args.classify:
        for entry in classified():
            print("%-12s %-52s %-34s active=%s"
                  % (entry["brand"], entry["canonical_name"],
                     entry["disposition"], entry["acquisition_required"]))
    if args.plan:
        active = [entry for entry in classified()
                  if entry["acquisition_required"]]
        for entry in active:
            print(json.dumps(verify_source(entry)))
            print(json.dumps(lane(entry)))
        print(json.dumps(cost_estimate(len(active)), indent=2))
    if args.meter:
        print(json.dumps(record_spend(args.meter), indent=2))
    if args.acquire:
        for row in run(limit=args.limit):
            print("%-52s %-28s %-10s %s"
                  % (row["canonical_name"], row["final_state"],
                     row["identity_verdict"], row["usable_policy"]))
    if args.audit:
        for row in audits():
            print("%-52s %-44s id=%s block=%s"
                  % (row["canonical_name"], row["verdict"],
                     row["correct_identity"], row["policy_block_chars"]))
    if args.census:
        doc = full_census()
        print(json.dumps({k: v for k, v in doc.items() if k != "rows"},
                         indent=2))
    if args.report:
        doc = write_report()
        print(json.dumps({k: v for k, v in doc.items()
                          if k not in ("rows", "bucket", "preflight",
                                       "full_census", "source_verification",
                                       "lanes", "premium_audit")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
