"""Run the paid lanes over a market's remaining routed cohort, under a hard cap.

    python scripts/pettripfinder/acquisition/market_paid_acquisition.py \
      --market st-louis-mo --cap-usd 10.00 \
      --prior launch_packages/pettripfinder/st_louis_mo_direct_http_pilot_001.json \
      --run-dir data/acquisition/st_louis_paid_002 \
      --out launch_packages/pettripfinder/st_louis_mo_paid_acquisition_002.json

WHY THIS EXISTS AS A GENERIC MODULE
-----------------------------------
``milwaukee_acquisition_run_001.py`` already proved this shape and is the source
of every safety rule below. It is also welded to one market: its queue path, its
cost anchor, its cap and its market id are module constants. St. Louis is the
first market built with no market-specific factory script, so the paid run is
the last piece that had to become generic. Nothing here knows what a St. Louis
is; it takes a census, a routing pass, a prior-acquisition report and a cap.

WHICH PROPERTIES ARE IN THE COHORT, AND WHY THE ANSWER IS SUBTRACTION
---------------------------------------------------------------------
The cohort is every ROUTED identity MINUS the ones whose question is already
answered. Three prior outcomes are TERMINAL and re-fetching them buys nothing:

    VALID              the page served and its policy was located and read.
    POLICY_NOT_FOUND   the page served its content and was silent. The router's
                       own escalation rule -- a refusal escalates, a silence
                       does not -- says a costlier lane receives the same
                       nothing.
    IDENTITY_MISMATCH  the page served and is about a DIFFERENT hotel. That is
                       a routing defect, and no crawler fixes a wrong URL. Those
                       rows belong to source discovery, not to a paid lane.

Everything else -- never attempted, unhydrated, access denied, navigation
failed, unexpected page -- is a statement about OUR ACCESS, which is exactly
what a paid lane is for. ``--terminal`` can widen or narrow that set; it may not
be inferred, so it is named.

THE CAP IS ENFORCED ON THE LARGER OF TWO NUMBERS
------------------------------------------------
PTF-MILWAUKEE-ACQUISITION-ROUTER-INTEGRATION-001 established that the ACCOUNT
BALANCE is not a spend meter: it lags roughly 3x, and a mid-run top-up makes
drawdown go negative. Per-zone month-to-date cost replaced it, because it only
increases and a top-up cannot touch it.

PTF-CANONICAL-LOCATOR-FRESH-PROOF-019A then established that the zone meter
itself LAGS: a settled 9.3 MB session read $0.00 in-run and 17c four minutes
later. A cap enforced on a lagging meter is a cap that overshoots.

So spend is tracked twice and the cap is checked against the MAXIMUM:

    measured    summed per-zone month-to-date growth since this run's anchor.
                Authoritative once billing catches up, and never early.
    estimated   each attempt priced at its provider's own measured
                ``usd_minor_per_property``. Available immediately, and it is
                the only number that exists during the lag.

Neither alone is safe. ``max()`` of the two is: it stops early under lag and it
stops correctly once billing settles. Both are reported so the gap stays visible.

Firecrawl bills plan CREDITS, not dollars, and ``providers.CostMetadata``
refuses to mix the two currencies. Credits are metered against their own cap and
never converted; a dollar figure for a credit lane would be invented.

A WHOLE FAMILY THAT FAILS SYSTEMATICALLY IS STOPPED, NOT RETRIED FORTY TIMES
----------------------------------------------------------------------------
An individual property failing is an ordinary outcome: classified and continued.
A brand family whose first ``--breaker-window`` properties ALL fail the same way
is a capability wall, and spending the rest of the market's budget re-proving it
is the exact mistake the Choice lane cost fifteen attempts to learn. The breaker
trips per family, records what tripped it, and the run continues with unrelated
families -- which is the escalation rule applied one level up.

EVERY COMPLETED PROPERTY IS JOURNALLED BEFORE THE NEXT ONE STARTS. A paid
capture held only in memory is money a kill destroys.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from collections import Counter, OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import journal as JOURNAL      # noqa: E402
from scripts.pettripfinder.acquisition import market_routing as MR    # noqa: E402
from scripts.pettripfinder.acquisition import providers as PROVIDERS  # noqa: E402
from scripts.pettripfinder.brightdata import browser_capture as BC    # noqa: E402
from scripts.pettripfinder.brightdata import client as CLIENT         # noqa: E402
from scripts.pettripfinder.brightdata import corpus as CORPUS         # noqa: E402
from scripts.pettripfinder.brightdata import declined_capture as DECLINED  # noqa: E402
from scripts.pettripfinder.brightdata import outcomes as O            # noqa: E402
from scripts.pettripfinder.brightdata import policy_surface as PS     # noqa: E402
from scripts.pettripfinder.discovery.property_identity import street_identity  # noqa: E402
from scripts.pettripfinder.site_data import normalize_name            # noqa: E402

SCHEMA = "ptf-market-paid-acquisition/1.0"
CENSUS_DIR = _REPO_ROOT / "launch_packages" / "pettripfinder" / "identity_census"

#: Prior capture outcomes that answer the question. See the module docstring.
DEFAULT_TERMINAL: Tuple[str, ...] = (O.VALID, O.POLICY_NOT_FOUND,
                                     O.IDENTITY_MISMATCH)

#: Every Bright Data zone this run can bill to. The Browser API bills to the
#: first; the Web Unlocker alternates across the other two. Summing all three is
#: what makes one meter cover every lane the router may choose.
BILLABLE_ZONES: Tuple[str, ...] = ("scraping_browser1", "mcp_unlocker",
                                   "cli_unlocker")

INDEPENDENT = "INDEPENDENT"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def family_of(brand: str) -> str:
    """The breaker and the report group by FAMILY, not by host.

    Every independent hotel carries its own ``INDEP:<host>`` brand, so grouping
    by brand would give each one a family of one -- the breaker could never trip
    on them, and could never wrongly stop thirty-four unrelated businesses
    because three of them were down. Chains keep their own name.
    """
    return INDEPENDENT if brand.startswith(CORPUS.INDEPENDENT_PREFIX) else brand


# --------------------------------------------------------------------------- #
# Cohort
# --------------------------------------------------------------------------- #

def derive_cohort(entries: Sequence[Mapping], prior: Mapping, *,
                  terminal: Sequence[str] = DEFAULT_TERMINAL
                  ) -> Tuple[List[Dict], List[Dict]]:
    """``(cohort, settled)`` over the routed population.

    Both lists are returned because a cohort is only trustworthy beside the
    reason each excluded row was excluded. ``cohort + settled`` is every ROUTED
    identity, and a test asserts it.
    """
    terminal_set = frozenset(terminal)
    prior_by_key = {r["identity_key"]: r for r in (prior.get("results") or ())}
    cohort: List[Dict] = []
    settled: List[Dict] = []
    for entry in entries:
        if entry["routing_state"] != MR.ROUTED:
            continue
        previous = prior_by_key.get(entry["identity_key"])
        outcome = previous["outcome"] if previous else ""
        row = OrderedDict((
            ("identity_key", entry["identity_key"]),
            ("canonical_name", entry["canonical_name"]),
            ("brand", entry["brand"]),
            ("family", family_of(entry["brand"])),
            ("corridor", entry["corridor"]),
            ("source_url", entry["source_url"]),
            ("provider", entry["provider"]),
            ("reader", entry["reader"]),
            ("prior_outcome", outcome or "NEVER_ATTEMPTED"),
        ))
        if outcome in terminal_set:
            row["settled_because"] = (
                "a prior capture already answered this property's question "
                "(%s); a paid lane would buy nothing" % outcome)
            settled.append(row)
        else:
            cohort.append(row)
    return (cohort, settled)


def apply_url_overlay(rows: List[Dict], overlay_path: str) -> Dict:
    """Layer recovered URLs over a census IN MEMORY, and report what moved.

    The census file on disk is the record of what discovery OBSERVED and is not
    edited here: a URL recovered by re-reading a cached payload is a proposal,
    and writing it into the census would make a derivation indistinguishable
    from an observation. Only rows that currently have no URL are touched, so
    an overlay can never displace something discovery actually found.
    """
    applied: List[Dict] = []
    if not overlay_path:
        return OrderedDict((("overlay", ""), ("applied", 0), ("rows", applied)))
    document = json.loads(Path(overlay_path).read_text(encoding="utf-8"))
    proposed = {r["identity_key"]: r for r in (document.get("recoveries") or ())}
    for row in rows:
        candidate = proposed.get(row["identity_key"])
        if candidate is None or (row.get("official_url") or "").strip():
            continue
        row["official_url"] = candidate["recovered_url"]
        applied.append(OrderedDict((
            ("identity_key", row["identity_key"]),
            ("url", candidate["recovered_url"]),
            ("binding", candidate.get("binding", "")),
            ("evidence", candidate.get("evidence", {})),
        )))
    return OrderedDict((
        ("overlay", Path(overlay_path).as_posix()),
        ("contract", document.get("schema", "")),
        ("offered", len(proposed)),
        ("applied", len(applied)),
        ("note", "layered for routing only; the census file is unchanged"),
        ("rows", applied),
    ))


def order_queue(cohort: Sequence[Mapping], priority: Sequence[str]) -> List[Dict]:
    """Cheapest currency first, then measured yield, then everything else.

    Order matters only because the cap will bind before the cohort ends, so it
    decides WHICH properties go unfetched. Credit-billed lanes run first because
    they do not draw on the dollar cap at all; within the dollar lanes, families
    the registry has actually measured on that lane come before families it has
    not.
    """
    rank = {name: index for index, name in enumerate(priority)}

    def key(row: Mapping) -> Tuple:
        try:
            cost = PROVIDERS.get(row["provider"]).cost_metadata()
            dollars = cost.usd_minor_per_property is not None
        except PROVIDERS.ProviderError:
            dollars = True
        return (1 if dollars else 0,
                rank.get(row["family"], len(rank)),
                row["identity_key"])

    return sorted(cohort, key=key)


# --------------------------------------------------------------------------- #
# Spend
# --------------------------------------------------------------------------- #

@dataclass
class SpendMeter:
    """Two spend numbers and one cap, deliberately.

    ``anchor_path`` outlives the process: a cap is "this much for this work
    order", not "this much per invocation", so ten runs of ten properties must
    not each be allowed the whole cap.
    """

    anchor_path: Path
    zones: Tuple[str, ...] = BILLABLE_ZONES
    estimated_usd_minor: float = 0.0
    estimated_credits: float = 0.0
    samples: List[Dict] = field(default_factory=list)
    latest: Optional[CLIENT.UsageSnapshot] = None
    #: The last vendor reading, kept because taking a fresh one costs six CLI
    #: round-trips (~6 s). See ``spend_view``.
    last_measured: Optional[int] = None
    reads: int = 0

    # -- the vendor's own numbers ------------------------------------------ #

    def zone_costs(self, label: str) -> Dict[str, Optional[int]]:
        out: Dict[str, Optional[int]] = {}
        for zone in self.zones:
            snap = CLIENT.read_usage("%s:%s" % (label, zone), zone=zone)
            if zone == self.zones[0]:
                self.latest = snap
            out[zone] = snap.cost_month_usd_minor
        return out

    def anchor(self, label: str) -> Dict:
        """Write the per-zone baseline once, then never again.

        Written EXPLICITLY as ``zone_costs_usd_minor``. ``UsageSnapshot.to_dict``
        carries one zone's cost under a different key, and an anchor that stores
        it there reads back as "no anchor" -- which makes measured spend unknown
        for the whole run.
        """
        if self.anchor_path.is_file():
            try:
                return json.loads(self.anchor_path.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                pass
        costs = self.zone_costs(label)
        snap = self.latest
        document = OrderedDict((
            ("label", label),
            ("captured_at", _now()),
            ("zones", list(self.zones)),
            ("zone_costs_usd_minor", costs),
            ("balance_usd_minor", snap.balance_usd_minor if snap else None),
            ("note", "the per-zone month-to-date baseline this work order's "
                     "spend is measured from; written once, never rewritten"),
        ))
        self.anchor_path.parent.mkdir(parents=True, exist_ok=True)
        self.anchor_path.write_text(json.dumps(document, indent=1) + "\n",
                                    encoding="utf-8", newline="\n")
        return document

    def measured_usd_minor(self, label: str) -> Optional[int]:
        """Summed per-zone growth since the anchor, or ``None``.

        ``None`` means UNKNOWN and callers must stop on it. Under a hard cap an
        unknown spend and a zero spend must never look the same.
        """
        if not self.anchor_path.is_file():
            return None
        try:
            base = json.loads(self.anchor_path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return None
        before = base.get("zone_costs_usd_minor")
        if not isinstance(before, dict):
            return None
        now = self.zone_costs(label)
        total = 0
        for zone in self.zones:
            a, b = before.get(zone), now.get(zone)
            if a is None or b is None:
                return None
            total += max(0, b - a)
        self.samples.append({"label": label, "at": _now(),
                             "zone_costs_usd_minor": now,
                             "measured_usd_minor": total})
        return total

    # -- our own estimate, which exists during the vendor's lag ------------- #

    def charge(self, attempts: Sequence) -> None:
        """Price one property at each provider's own measured unit cost.

        Charged once per (property, provider), NOT once per attempt, because
        that is what the unit is: ``CostMetadata.basis`` reads "zone delta /
        properties attempted", an average already inclusive of the retries and
        the failures inside a property. Charging every attempt would bill a
        three-attempt property triple a figure that already counts its retries,
        and the cap would bind at roughly a third of the money actually spent.

        Failed providers ARE charged. Bright Data bills bandwidth, so a refusal
        is nearly free -- but "nearly" is not "certainly", and Firecrawl's own
        observation that failed scrapes went unbilled is an observation and not
        a billing guarantee. A cap must not be enforced on a vendor's goodwill.
        """
        for provider_id in {a.provider for a in attempts}:
            try:
                cost = PROVIDERS.get(provider_id).cost_metadata()
            except PROVIDERS.ProviderError:
                continue
            if cost.usd_minor_per_property is not None:
                self.estimated_usd_minor += cost.usd_minor_per_property
            if cost.credits_per_property is not None:
                self.estimated_credits += cost.credits_per_property

    def spend_view(self, label: str, *, refresh: bool = True) -> Dict:
        """Both numbers, the one the cap binds on, and why.

        ``refresh=False`` reuses the last vendor reading. One reading is six CLI
        round-trips and about six seconds; taking one before every property adds
        twenty minutes to a two-hundred-property run for a number that only
        moves once billing settles. The ESTIMATE is recomputed every time
        regardless -- it is the number that exists during the lag, and it is
        never stale, so the cap is still checked on fresh information at every
        single property. The caller decides how often the vendor is asked, and
        the report records how many times it was.
        """
        if refresh or self.last_measured is None:
            self.last_measured = self.measured_usd_minor(label)
            self.reads += 1
        measured = self.last_measured
        estimated = round(self.estimated_usd_minor, 2)
        binding = max(measured, estimated) if measured is not None else estimated
        return OrderedDict((
            ("measured_usd_minor", measured),
            ("estimated_usd_minor", estimated),
            ("binding_usd_minor", binding),
            ("binding_source", "measured"
             if measured is not None and measured >= estimated else "estimated"),
            ("telemetry_live", measured is not None),
            ("estimated_plan_credits", round(self.estimated_credits, 2)),
            ("vendor_reads", self.reads),
            ("lag_note", "the vendor's zone meter settles minutes after a "
                         "session; until it does the estimate is the only "
                         "number that exists, so the cap binds on the larger"),
        ))


# --------------------------------------------------------------------------- #
# Systematic-failure breaker
# --------------------------------------------------------------------------- #

@dataclass
class FamilyBreaker:
    """Stop a family the moment it looks like a wall, not like a bad property."""

    window: int = 6
    seen: Dict[str, List[str]] = field(default_factory=dict)
    tripped: "OrderedDict" = field(default_factory=OrderedDict)

    def record(self, family: str, *, acquired: bool, failure: str) -> None:
        history = self.seen.setdefault(family, [])
        history.append("" if acquired else (failure or "UNCLASSIFIED"))
        if family in self.tripped or len(history) < self.window:
            return
        if any(entry == "" for entry in history):
            return                      # something worked; this is not a wall
        if len(set(history)) != 1:
            return                      # failing variously is not a wall either
        self.tripped[family] = OrderedDict((
            ("family", family),
            ("failure", history[0]),
            ("consecutive", len(history)),
            ("why", "every one of the first %d properties in this family failed "
                    "identically (%s); that is a capability wall, and re-proving "
                    "it would spend the rest of the cap"
                    % (len(history), history[0])),
        ))

    def is_open(self, family: str) -> bool:
        return family in self.tripped


# --------------------------------------------------------------------------- #
# Capture target
# --------------------------------------------------------------------------- #

def record_for(row: Mapping, entry: Mapping) -> CORPUS.BenchmarkRecord:
    """A capture record for a property with NO committed benchmark.

    ``facts``, ``quotes`` and ``withheld_fields`` are empty on purpose: a market
    being acquired for the first time has no policy authority to compare
    against, and an empty benchmark cannot leak an expected answer into a
    capture the way a populated one could.
    """
    return CORPUS.BenchmarkRecord(
        identity_key=row["identity_key"],
        name=row["canonical_name"],
        market_id=row["market_id"],
        brand=entry["brand"],
        bucket=CORPUS.bucket_of(entry["brand"]),
        source_url=entry["source_url"],
        pets_allowed=None,
        facts={}, quotes=(), withheld_fields={},
        service_animal_statement="",
        categories=frozenset(),
        origin="census",
        street=row.get("address", "") or "",
        postal_code=row.get("postal_code", "") or "",
        phone=row.get("phone", "") or "",
        locality=", ".join(x for x in (row.get("city", ""), row.get("state", ""))
                           if x))


def target_for(record: CORPUS.BenchmarkRecord) -> BC.CaptureTarget:
    """Inputs only. A ``CaptureTarget`` has no field a policy value could sit in.

    ``identity_brand`` is blanked for independents. It is an identity signal --
    "this page should name this chain" -- and ``INDEP:jondonproperties.com`` is
    a routing label, not a name any page will ever print.
    """
    chain = ("" if record.brand.startswith(CORPUS.INDEPENDENT_PREFIX)
             else record.brand)
    return BC.CaptureTarget(
        slug=record.slug[:80],
        hotel=record.name,
        requested_url=record.source_url,
        property_code=PS.property_code(record.source_url, chain),
        market_id=record.market_id,
        normalized_name=normalize_name(record.name),
        identity_key=record.identity_key,
        street_identity=(street_identity(record.street, record.postal_code)
                         if record.street else ""),
        expected_street=record.street,
        expected_postal_code=record.postal_code,
        expected_phone=record.phone,
        expected_locality=record.locality,
        identity_brand=chain,
        census_matched=True,
        census_note="identity taken from the committed %s census"
                    % record.market_id)


# --------------------------------------------------------------------------- #
# The run
# --------------------------------------------------------------------------- #

def _declined_dir_for(run_dir: Path, slug: str, result) -> str:
    """Where a decline preserved its document, when the contract keeps it.

    Derived rather than returned: ``ProviderAttempt`` is a frozen contract and
    widening it to carry a path would change an artifact five markets read.
    """
    found = ""
    for attempt in result.attempts:
        candidate = run_dir / slug / ("declined-%02d" % attempt.attempt)
        if (attempt.outcome in DECLINED.KEEPABLE_OUTCOMES
                and (candidate / DECLINED.DECLINED_ARTIFACT).is_file()):
            found = str(candidate)
    return found


def _artifact_dir_for(run_dir: Path, slug: str, result) -> str:
    """The attempt directory of the successful capture, or ""."""
    for attempt in result.attempts:
        if attempt.outcome != O.VALID:
            continue
        candidate = run_dir / slug / ("attempt-%02d" % attempt.attempt)
        if (candidate / "policy-block.txt").is_file():
            return str(candidate)
    return ""


def _result_row(*, row: Mapping, entry: Mapping, result, run_dir: Path,
                slug: str, began: float) -> "OrderedDict":
    """One property, in the shape every downstream reader already consumes.

    The observation store, the closure ledger and the founder-review builder all
    read ``ptf-direct-http-pilot/1.0`` result rows. Emitting that shape -- with
    the paid lane's provider and reader filled in rather than assumed -- is what
    lets a paid run reuse four committed modules instead of forking them.
    """
    last = result.attempts[-1] if result.attempts else None
    success = next((a for a in result.attempts if a.outcome == O.VALID), None)
    chosen = success or last
    document = result.document
    return OrderedDict((
        ("identity_key", entry["identity_key"]),
        ("canonical_name", entry["canonical_name"]),
        ("brand", entry["brand"]),
        ("corridor", entry["corridor"]),
        ("source_url", entry["source_url"]),
        ("outcome", chosen.outcome if chosen else "CAPTURE_FAILED"),
        ("attempts", len(result.attempts)),
        ("final_url", chosen.final_url if chosen else ""),
        ("title", chosen.title if chosen else ""),
        ("body_chars", chosen.body_chars if chosen else 0),
        ("detail", (chosen.detail or "")[:400] if chosen else ""),
        ("identity_confirmed", document is not None),
        ("identity_reasons", []),
        ("artifact_dir", _artifact_dir_for(run_dir, slug, result)),
        ("declined_dir", _declined_dir_for(run_dir, slug, result)),
        ("bytes_received", sum(a.estimated_bytes for a in result.attempts)),
        ("elapsed_seconds", round(time.monotonic() - began, 2)),
        ("policy_block", ""),
        ("locator_strategy", document.policy_locator if document is not None
                             else ""),
        # Paid-lane provenance. The downstream store defaults these when a row
        # does not carry them, so adding them widens the contract without
        # breaking the four markets that never had them.
        ("provider", chosen.provider if chosen else ""),
        ("providers_tried", list(result.providers_tried)),
        ("reader", (result.route or {}).get("reader", "")),
        ("final_state", result.state),
        ("publication_grade", result.state == "ACQUIRED_PUBLICATION_GRADE"),
        ("failure", result.failure),
        ("failure_class", result.failure_class),
        ("escalation_stopped_because", result.escalation_stopped_because),
        ("content_hash", document.content_hash if document is not None else ""),
    ))


async def run(*, rows: Sequence[Mapping], queue: Sequence[Mapping],
              run_dir: Path, run_id: str, meter: SpendMeter,
              cap_usd_minor: int, credit_cap: Optional[int],
              breaker: FamilyBreaker, journal: JOURNAL.Journal,
              resume: bool, meter_every: int = 5) -> Dict:
    """The paid section. Reached only once every gate has passed."""
    from scripts.pettripfinder.acquisition import router as ROUTER

    by_key = {r["identity_key"]: r for r in rows}
    done = journal.completed_keys() if resume else set()
    pending = [e for e in queue if e["identity_key"] not in done]

    report: Dict = OrderedDict((
        ("run_id", run_id),
        ("queue_total", len(queue)),
        ("already_completed", len(done)),
        ("planned_this_batch", len(pending)),
        ("attempted", 0),
        ("outcome", ""),
        ("stop_reason", ""),
        ("deferred", []),
    ))
    results: List[Dict] = []

    # Ask the vendor again every ``meter_every`` properties, and additionally
    # the moment the estimate crosses a quarter of the cap it has not crossed
    # before -- so the approach to the ceiling is always checked against the
    # vendor, never against our own arithmetic alone.
    crossed: set = set()

    for index, entry in enumerate(pending, 1):
        family = entry["family"]
        quarter = int(4 * meter.estimated_usd_minor / cap_usd_minor) if cap_usd_minor else 0
        due = (index == 1 or index % meter_every == 0 or quarter not in crossed)
        crossed.add(quarter)
        spend = meter.spend_view("%s:before:%d" % (run_id, index), refresh=due)
        if not spend["telemetry_live"]:
            report["outcome"] = "STOPPED_TELEMETRY_LOST"
            report["stop_reason"] = (
                "the vendor's per-zone cost became unreadable mid-run; stopped "
                "rather than spend against a cap nobody can measure")
            report["deferred"] = [e["identity_key"] for e in pending[index - 1:]]
            break
        if spend["binding_usd_minor"] >= cap_usd_minor:
            report["outcome"] = "STOPPED_HARD_CAP"
            report["stop_reason"] = (
                "hard cap reached: %s of %d cents (%s)"
                % (spend["binding_usd_minor"], cap_usd_minor,
                   spend["binding_source"]))
            report["deferred"] = [e["identity_key"] for e in pending[index - 1:]]
            break
        if credit_cap is not None and spend["estimated_plan_credits"] >= credit_cap:
            report["outcome"] = "STOPPED_CREDIT_CAP"
            report["stop_reason"] = (
                "plan-credit cap reached: %s of %d credits"
                % (spend["estimated_plan_credits"], credit_cap))
            report["deferred"] = [e["identity_key"] for e in pending[index - 1:]]
            break
        if breaker.is_open(family):
            report["deferred"].append(entry["identity_key"])
            print("[%3d/%3d] %-22s %-12s SKIPPED (family breaker open)"
                  % (index, len(pending), "BREAKER", family), flush=True)
            continue

        row = by_key[entry["identity_key"]]
        record = record_for(row, entry)
        target = target_for(record)
        began = time.monotonic()
        try:
            result = await ROUTER.route_property(
                record, target, run_dir=run_dir, run_id=run_id)
            meter.charge(result.attempts)
            item = _result_row(row=row, entry=entry, result=result,
                               run_dir=run_dir, slug=target.slug, began=began)
        except Exception as exc:                                  # noqa: BLE001
            # A crash must still be journalled. An unrecorded paid attempt is
            # money that a resume would spend a second time.
            item = OrderedDict((
                ("identity_key", entry["identity_key"]),
                ("canonical_name", entry["canonical_name"]),
                ("brand", entry["brand"]),
                ("corridor", entry["corridor"]),
                ("source_url", entry["source_url"]),
                ("outcome", O.CAPTURE_FAILED),
                ("attempts", 0), ("final_url", ""), ("title", ""),
                ("body_chars", 0),
                ("detail", CLIENT.redact_truncate(
                    "%s: %s" % (type(exc).__name__, exc), 400)),
                ("identity_confirmed", False), ("identity_reasons", []),
                ("artifact_dir", ""), ("declined_dir", ""),
                ("bytes_received", 0),
                ("elapsed_seconds", round(time.monotonic() - began, 2)),
                ("policy_block", ""), ("locator_strategy", ""),
                ("provider", entry["provider"]), ("providers_tried", []),
                ("reader", entry["reader"]),
                ("final_state", "TECHNICAL_FALLBACK_REQUIRED"),
                ("publication_grade", False),
                ("failure", "RUNNER_EXCEPTION"),
                ("failure_class", "RUNNER_EXCEPTION"),
                ("escalation_stopped_because", ""), ("content_hash", ""),
            ))
        item["family"] = family
        item["completed_at"] = _now()
        journal.append(item)              # durable BEFORE the next property
        results.append(item)
        report["attempted"] += 1
        breaker.record(family, acquired=bool(item["publication_grade"]),
                       failure=item["failure"] or item["outcome"])
        print("[%3d/%3d] %-14s %-12s %-22s %s"
              % (index, len(pending), item["outcome"][:14], family[:12],
                 (item["provider"] or "-")[:22],
                 entry["canonical_name"][:44]), flush=True)
    else:
        report["outcome"] = "BATCH_COMPLETE"

    report.setdefault("outcome", "BATCH_COMPLETE")
    report["results"] = results
    return report


# --------------------------------------------------------------------------- #
# Gates
# --------------------------------------------------------------------------- #

def preflight(meter: SpendMeter, *, run_id: str, cap_usd_minor: int) -> Dict:
    """Everything that must be true before one cent is spent."""
    checks: List[Dict] = []
    meter.anchor("%s:anchor" % run_id)
    measured = meter.measured_usd_minor("%s:preflight" % run_id)
    snap = meter.latest

    checks.append(OrderedDict((
        ("check", "cost_telemetry_live"),
        ("ok", measured is not None),
        ("detail", "per-zone month-to-date cost readable across %s"
                   % ", ".join(meter.zones) if measured is not None
                   else "the vendor's per-zone cost could not be read; a cap "
                        "cannot be enforced against an unknown spend"),
    )))
    balance = snap.balance_usd_minor if snap else None
    checks.append(OrderedDict((
        ("check", "balance_covers_the_remaining_cap"),
        ("ok", balance is not None and balance >= cap_usd_minor),
        ("detail", ("balance %d cents against a %d cent cap"
                    % (balance, cap_usd_minor)) if balance is not None
                   else "balance unreadable"),
    )))
    healthy: List[str] = []
    detail: Dict[str, Dict] = {}
    for provider_id in PROVIDERS.all_ids():
        health = PROVIDERS.get(provider_id).health_check()
        detail[provider_id] = {"available": bool(health.available),
                               "detail": health.detail}
        if health.available:
            healthy.append(provider_id)
    checks.append(OrderedDict((
        ("check", "at_least_one_provider_available"),
        ("ok", bool(healthy)),
        ("detail", ("available: %s" % ", ".join(sorted(healthy))) if healthy
                   else "no provider passed its own health check"),
    )))
    return OrderedDict((
        ("ok", all(c["ok"] for c in checks)),
        ("checks", checks),
        ("providers", detail),
        ("already_spent_usd_minor", measured),
    ))


def _finalise(document: Dict, *, meter: SpendMeter, journal: JOURNAL.Journal,
              run_id: str, started: float, out: Path) -> None:
    """Close the report, whichever path produced it.

    Shared by the run loop and by ``--report-only``, so an interrupted run and a
    completed one are described in exactly the same fields. Two code paths each
    building their own summary is two chances to describe one run differently.
    """
    final = meter.spend_view("%s:final" % run_id)
    document["spend"] = final
    document["cost_samples"] = meter.samples
    document["journal_total"] = journal.count()
    document["run_end"] = _now()
    document["elapsed_seconds"] = round(time.monotonic() - started, 1)
    results = document.get("results") or ()
    document["outcome_counts"] = OrderedDict(
        sorted(Counter(r["outcome"] for r in results).items()))
    document["publication_grade"] = sum(
        1 for r in results if r.get("publication_grade"))

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print()
    print("cohort    : %d (settled %d)"
          % (document["cohort_size"], document["settled_size"]))
    print("attempted : %d" % document.get("attempted", 0))
    print("outcome   : %s %s" % (document.get("outcome"),
                                 document.get("stop_reason", "")))
    print("outcomes  : %s" % dict(document["outcome_counts"]))
    print("pub-grade : %d" % document["publication_grade"])
    print("spend     : measured %s / estimated %s cents, %s credits"
          % (final["measured_usd_minor"], final["estimated_usd_minor"],
             final["estimated_plan_credits"]))
    print("written   : %s" % out)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--market", required=True)
    parser.add_argument("--prior", required=True,
                        help="a prior acquisition report whose results settle "
                             "part of the routed population")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--work-order", default="")
    parser.add_argument("--cap-usd", type=float, required=True,
                        help="hard ceiling on ADDITIONAL dollar spend")
    parser.add_argument("--credit-cap", type=int, default=None,
                        help="hard ceiling on plan credits, metered separately")
    parser.add_argument("--priority", default="MARRIOTT,HILTON,RED_ROOF,"
                                              "MOTEL6,SONESTA,DRURY,ESA,"
                                              "INDEPENDENT",
                        help="family order within the dollar lanes; families "
                             "the registry has measured on that lane first")
    parser.add_argument("--terminal", default=",".join(DEFAULT_TERMINAL),
                        help="prior outcomes that settle a property")
    parser.add_argument("--breaker-window", type=int, default=6)
    parser.add_argument("--meter-every", type=int, default=5,
                        help="how often the VENDOR is asked for its cost; the "
                             "estimate is checked at every property regardless")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--url-overlay", default="",
                        help="a ptf-census-url-recovery report; its recovered "
                             "URLs are layered over the census for ROUTING "
                             "ONLY, and the census file is never edited")
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true",
                        help="derive the cohort and run the gates; spend zero")
    parser.add_argument("--report-only", action="store_true",
                        help="build the report from the journal alone and "
                             "spend nothing; how a killed run still produces "
                             "its artifact")
    args = parser.parse_args(argv)

    run_id = args.run_id or ("%s-paid" % args.market)
    started = time.monotonic()
    census = json.loads((CENSUS_DIR / ("%s.json" % args.market))
                        .read_text(encoding="utf-8"))
    prior = json.loads(Path(args.prior).read_text(encoding="utf-8"))
    overlay = apply_url_overlay(census["hotels"], args.url_overlay)
    entries, routing_summary = MR.route_census(census["hotels"])
    cohort, settled = derive_cohort(
        entries, prior, terminal=[t for t in args.terminal.split(",") if t])
    queue = order_queue(cohort, args.priority.split(","))
    if args.limit:
        queue = queue[:args.limit]

    run_dir = Path(args.run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    meter = SpendMeter(anchor_path=run_dir / "market_cost_anchor.json")
    journal = JOURNAL.Journal(path=run_dir / "journal.jsonl")
    cap_usd_minor = int(round(args.cap_usd * 100))

    document: Dict = OrderedDict((
        ("schema", SCHEMA),
        ("what_this_is",
         "One paid acquisition pass over a market's remaining routed cohort, "
         "under a hard spend cap enforced on the larger of the vendor's "
         "measured cost and this run's own estimate. It changes no route."),
        ("market_id", args.market),
        ("work_order", args.work_order or run_id),
        ("run_id", run_id),
        ("run_start", _now()),
        ("dry_run", bool(args.dry_run)),
        ("prior_report", str(Path(args.prior).as_posix())),
        ("cost_policy", OrderedDict((
            ("hard_cap_usd_minor", cap_usd_minor),
            ("plan_credit_cap", args.credit_cap),
            ("measured_from", "per-zone month-to-date cost summed over %s"
                              % ", ".join(BILLABLE_ZONES)),
            ("enforced_on", "max(measured, estimated) -- the vendor's meter "
                            "lags a session by minutes and a cap enforced on a "
                            "lagging meter overshoots"),
        ))),
        ("url_overlay", overlay),
        ("routing_summary", routing_summary),
        ("cohort_rule", OrderedDict((
            ("terminal_prior_outcomes", args.terminal.split(",")),
            ("why", "a page that served and was read, was silent, or was about "
                    "another hotel has already answered its question; a paid "
                    "lane is for properties we could not REACH"),
        ))),
        ("cohort_size", len(cohort)),
        ("settled_size", len(settled)),
        ("cohort_by_provider", OrderedDict(
            sorted(Counter(r["provider"] for r in cohort).items()))),
        ("cohort_by_family", OrderedDict(
            sorted(Counter(r["family"] for r in cohort).items()))),
        ("settled_by_prior_outcome", OrderedDict(
            sorted(Counter(r["prior_outcome"] for r in settled).items()))),
        ("queue_order", args.priority.split(",")),
        ("cohort", cohort),
        ("settled", settled),
    ))

    if args.report_only:
        # A run can be killed -- by a cap, an operator, a machine. The money it
        # spent is already spent and its captures are already on disk, so the
        # report must be derivable from the journal alone. Building it here
        # rather than only at the end of a successful loop is what stops a kill
        # from turning paid evidence into an unreadable pile of directories.
        completed = journal.read()
        results = [completed[key] for key in sorted(completed)]
        attempted = {r["identity_key"] for r in results}
        document["preflight"] = {"ok": True, "checks": [], "providers": {},
                                 "note": "not run: --report-only spends nothing"}
        document["outcome"] = "REPORT_FROM_JOURNAL"
        document["stop_reason"] = (
            "the run was interrupted after %d of %d cohort properties; this "
            "document is built from the journal, which is durable by design, "
            "so nothing that was paid for is missing from it"
            % (len(results), len(queue)))
        document["results"] = results
        document["attempted"] = len(results)
        document["planned_this_batch"] = len(queue)
        document["deferred"] = [r["identity_key"] for r in queue
                                if r["identity_key"] not in attempted]
        document["family_attempt_history"] = OrderedDict(
            (family, [("" if r["publication_grade"]
                       else (r.get("failure") or r["outcome"]))
                      for r in results if r.get("family") == family])
            for family in sorted({r.get("family", "") for r in results}))
        document["family_breakers_tripped"] = []
        for row in results:
            provider = row.get("provider")
            if provider:
                meter.charge([type("A", (), {"provider": p})()
                              for p in (row.get("providers_tried") or [provider])])
        _finalise(document, meter=meter, journal=journal, run_id=run_id,
                  started=started, out=Path(args.out))
        return 0

    pre = preflight(meter, run_id=run_id, cap_usd_minor=cap_usd_minor)
    document["preflight"] = pre
    if not pre["ok"]:
        document["outcome"] = "STOPPED_BEFORE_SPENDING"
        document["stop_reason"] = "; ".join(
            "%s: %s" % (c["check"], c["detail"]) for c in pre["checks"]
            if not c["ok"])
        document["results"] = []
        document["attempted"] = 0
    elif args.dry_run:
        document["outcome"] = "DRY_RUN_ONLY"
        document["results"] = []
        document["attempted"] = 0
    else:
        breaker = FamilyBreaker(window=args.breaker_window)
        result = asyncio.run(run(
            rows=census["hotels"], queue=queue, run_dir=run_dir, run_id=run_id,
            meter=meter, cap_usd_minor=cap_usd_minor,
            credit_cap=args.credit_cap, breaker=breaker, journal=journal,
            resume=not args.no_resume, meter_every=args.meter_every))
        document.update(result)
        document["family_breakers_tripped"] = list(breaker.tripped.values())
        document["family_attempt_history"] = OrderedDict(
            (family, list(history)) for family, history
            in sorted(breaker.seen.items()))

    _finalise(document, meter=meter, journal=journal, run_id=run_id,
              started=started, out=Path(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
