"""PTF-BRIGHTDATA-CROSS-BRAND-PILOT-002 -- thirty properties, six buckets.

WHAT THE FIVE-PROPERTY PILOT LEFT OPEN
--------------------------------------
PTF-BRIGHTDATA-MARRIOTT-PILOT-001 showed that everything Bright Data reached,
it read exactly: identity, critical fields, literal quotes, artifacts and
publication grade all landed at 100% of pages reached. What it could not settle
was FETCH RELIABILITY -- 5/5 then 4/5, where one property moves the score
twenty points -- and it measured one brand's template.

So this pilot varies both: thirty properties across Marriott, Hilton, IHG,
Choice, Wyndham and a mixed bucket, with the exit geography pinned to the
United States because an unpinned exit is what cost the previous pilot its one
failure.

THE BENCHMARK IS THE CORPUS
---------------------------
Nothing here is hand-written. The thirty properties are selected from this
repository's own founder-reviewed policy records and exclusion registries by
``corpus.select_sample``, and the facts they are compared against are the facts
already committed. Capture first, compare second, and a field Bright Data did
not find is never filled in from what we knew.

WHAT IS DELIBERATELY NOT BUILT
------------------------------
Six brand scrapers. The capture uses one bounded, structural strategy for every
brand and RECORDS which locator, which disclosure and which parser patterns
fired, per brand. Whether that justifies a ``PTF_HILTON`` adapter is the
question; writing the adapter first would answer it by assumption.

RESUMABILITY IS A COST CONTROL
------------------------------
Thirty properties take long enough that the process can be killed mid-run, and
the first execution of this benchmark was -- at nineteen paid captures, all of
which were lost because the results existed only in memory. Every finished
property is now journalled immediately, and a resumed run skips what the
journal holds and reuses the first leg's usage baseline so the reported cost
still covers the whole benchmark.
"""

from __future__ import annotations

import argparse
import asyncio
import collections
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.brightdata import browser_capture as BC     # noqa: E402
from scripts.pettripfinder.brightdata import client                    # noqa: E402
from scripts.pettripfinder.brightdata import corpus as CORPUS          # noqa: E402
from scripts.pettripfinder.brightdata import cross_brand_capture as CBC  # noqa: E402
from scripts.pettripfinder.brightdata import marriott_surface as MS    # noqa: E402
from scripts.pettripfinder.brightdata import outcomes as O             # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR      # noqa: E402
from scripts.pettripfinder.brightdata import policy_surface as PS      # noqa: E402
from scripts.pettripfinder.brightdata import publication_grade as PG   # noqa: E402
from scripts.pettripfinder.contracts import enums                      # noqa: E402
from scripts.pettripfinder.contracts import evidence as EV             # noqa: E402
from scripts.pettripfinder.policy import policy_membrane as MEMBRANE   # noqa: E402
from scripts.pettripfinder.policy import policy_observation as PO      # noqa: E402
from scripts.pettripfinder.policy import readiness as READINESS        # noqa: E402
from scripts.pettripfinder.site_data import normalize_name             # noqa: E402

WORK_ORDER = "PTF-BRIGHTDATA-CROSS-BRAND-PILOT-002"
PILOT_ID = "brightdata-cross-brand-pilot-002"
PILOT_SIZE = 30
PER_BUCKET = 5

RAW_ROOT = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
            / PILOT_ID / "raw")
REPORT_DIR = (_REPO_ROOT / "launch_packages" / "pettripfinder" / "markets"
              / "reports")
_STEM = PILOT_ID.replace("-", "_")

#: Per-property results, appended as each property finishes. Lives beside the
#: raw tree and is gitignored with it.
PROGRESS_JOURNAL = RAW_ROOT.parent / "progress.jsonl"
#: The usage snapshot taken before the FIRST leg, so a resumed run measures the
#: whole benchmark rather than only its last leg.
BASELINE_USAGE = RAW_ROOT.parent / "usage-baseline.json"

SUMMARY_REPORT = REPORT_DIR / ("%s_summary.json" % _STEM)
PROPERTY_REPORT = REPORT_DIR / ("%s_properties.json" % _STEM)
BRAND_REPORT = REPORT_DIR / ("%s_brands.md" % _STEM)
SAMPLE_REPORT = REPORT_DIR / ("%s_sample.json" % _STEM)

#: The §4 variety floor. Checked against the built sample before a single
#: session is opened, so a sample that quietly lost its hard cases fails loudly
#: rather than producing a flattering number.
SAMPLE_MINIMUMS: Dict[str, int] = {
    CORPUS.CAT_NO_PETS: 5,
    CORPUS.CAT_STRUCTURED_POSITIVE: 5,
    CORPUS.CAT_CONTRADICTION: 3,
    CORPUS.CAT_DYNAMIC: 3,
    CORPUS.CAT_DIFFICULT: 3,
}

CLAUDE_FALLBACK_REQUIRED = "CLAUDE_FALLBACK_REQUIRED"
PUBLICATION_CANDIDATE = "PUBLICATION_CANDIDATE"
VERIFIED_NO_PETS_CANDIDATE = "VERIFIED_NO_PETS_CANDIDATE"
HOLD = "HOLD"

MATCH = "MATCH"
MISMATCH = "MISMATCH"
CAPTURE_ABSENT = "CAPTURE_ABSENT"
BENCHMARK_SILENT = "BENCHMARK_SILENT"
NOT_COMPARABLE = "NOT_COMPARABLE"

#: The fields the pass gate is measured on -- the same five the Marriott pilot
#: used, so the two runs are comparable.
CRITICAL_FIELDS: Tuple[str, ...] = ("pets_allowed", "pet_fee_minor",
                                    "fee_basis", "weight_limit_value",
                                    "pet_count_limit")

#: Reported, but NOT part of the pass gate. These measure how far a generic
#: reader carries across brands, which is an adapter question rather than an
#: acquisition one.
EXTENDED_FIELDS: Tuple[str, ...] = ("fee_scope", "species_dogs", "species_cats")


class PilotError(ValueError):
    """The pilot cannot run as specified."""


# --------------------------------------------------------------------------- #
# Targets.
# --------------------------------------------------------------------------- #

def build_sample() -> Tuple[CORPUS.BenchmarkRecord, ...]:
    """The thirty, and a refusal if the variety floor is not met."""
    sample = CORPUS.select_sample(CORPUS.load_corpus(), per_bucket=PER_BUCKET,
                                  minimums=SAMPLE_MINIMUMS)
    if len(sample) != PILOT_SIZE:
        raise PilotError("expected %d properties, built %d"
                         % (PILOT_SIZE, len(sample)))
    counts = collections.Counter(r.bucket for r in sample)
    if any(counts[b] != PER_BUCKET for b in CORPUS.BUCKETS):
        raise PilotError("brand distribution is %s, expected %d each"
                         % (dict(counts), PER_BUCKET))
    excluded = [r.name for r in sample if r.brand in CORPUS.EXCLUDED_BRANDS]
    if excluded:
        raise PilotError("excluded brands present in the sample: %s" % excluded)
    coverage = CORPUS.coverage(sample)
    short = {c: (coverage[c], n) for c, n in SAMPLE_MINIMUMS.items()
             if coverage[c] < n}
    if short:
        raise PilotError("the sample misses its variety floor: %s" % short)
    return sample


def target_for(record: CORPUS.BenchmarkRecord) -> BC.CaptureTarget:
    """A capture target carrying inputs only.

    The same structural guarantee as the Marriott pilot: a ``CaptureTarget``
    has no field a policy value could occupy, so the benchmark cannot ride
    along into the capture.
    """
    return BC.CaptureTarget(
        slug=record.slug[:80],
        hotel=record.name,
        requested_url=record.source_url,
        property_code=PS.property_code(record.source_url, record.brand),
        market_id=record.market_id,
        normalized_name=normalize_name(record.name),
        identity_key=record.identity_key,
        census_matched=True,
        census_note="identity taken from the committed %s authority"
                    % record.market_id)


# --------------------------------------------------------------------------- #
# Comparison.
# --------------------------------------------------------------------------- #

def _benchmark_value(field: str, record: CORPUS.BenchmarkRecord):
    facts = record.facts or {}
    if field == "pets_allowed":
        return facts.get("pets_allowed")
    if field == "pet_fee_minor":
        fee = facts.get("pet_fee")
        return fee.get("amount_cents") if isinstance(fee, Mapping) else None
    if field == "fee_basis":
        fee = facts.get("pet_fee")
        return fee.get("basis") if isinstance(fee, Mapping) else None
    if field == "fee_scope":
        fee = facts.get("pet_fee")
        return fee.get("scope") if isinstance(fee, Mapping) else None
    if field == "weight_limit_value":
        limit = facts.get("weight_limit")
        return limit.get("value") if isinstance(limit, Mapping) else None
    if field == "pet_count_limit":
        return facts.get("pet_count_limit")
    if field in ("species_dogs", "species_cats"):
        species = facts.get("species")
        if not isinstance(species, Mapping):
            return None
        return species.get("dogs" if field == "species_dogs" else "cats")
    return None


def _captured_value(field: str, extraction: Mapping):
    if field == "pets_allowed":
        return extraction.get("pets_allowed")
    if field == "pet_fee_minor":
        return extraction.get("pet_fee")
    if field == "fee_basis":
        return extraction.get("fee_basis")
    if field == "fee_scope":
        return extraction.get("fee_scope")
    if field == "weight_limit_value":
        limit = extraction.get("weight_limit")
        return limit.get("value") if isinstance(limit, Mapping) else None
    if field == "pet_count_limit":
        return extraction.get("pet_count_limit")
    if field == "species_dogs":
        allowed = extraction.get("species_allowed")
        return "accepted" if allowed and "dog" in allowed else None
    if field == "species_cats":
        if extraction.get("cats_allowed") is False:
            return "prohibited"
        allowed = extraction.get("species_allowed")
        return "accepted" if allowed and "cat" in allowed else None
    return None


#: Which benchmark ``withheld_fields`` key governs which comparison field. A
#: benchmark that WITHHELD a value expects the capture to withhold it too --
#: that is the contradiction-preservation test, and it is the one comparison
#: where producing a value is the failure.
_WITHHELD_KEY_FOR: Dict[str, Tuple[str, ...]] = {
    "pet_fee_minor": ("pet_fee",),
    "fee_basis": ("fee_basis", "pet_fee"),
    "fee_scope": ("fee_scope", "pet_fee"),
    "weight_limit_value": ("weight_limit",),
    "pets_allowed": ("pets_allowed",),
}


def compare(record: CORPUS.BenchmarkRecord, *, extraction: Mapping,
            withheld: Mapping, block_text: str) -> Dict:
    """Capture against committed facts. Runs only after the artifacts exist."""
    facts = record.facts or {}
    tiered = bool(facts.get("fee_tiers"))
    fields: Dict[str, Dict] = {}

    for field in CRITICAL_FIELDS + EXTENDED_FIELDS:
        expected = _benchmark_value(field, record)
        got = _captured_value(field, extraction)
        withheld_keys = _WITHHELD_KEY_FOR.get(field, ())
        benchmark_withheld = next(
            (k for k in withheld_keys if k in (record.withheld_fields or {})),
            None)

        if benchmark_withheld:
            # The committed record refused to publish this. A capture that
            # produces a value has resolved a contradiction the corpus
            # deliberately left open.
            verdict = MATCH if got is None else MISMATCH
            fields[field] = {
                "expected": "ABSENT (withheld: %s)" % benchmark_withheld,
                "captured": got, "verdict": verdict,
                "note": "the committed record withholds this field; producing "
                        "a value here would resolve a contradiction the corpus "
                        "left open"}
            continue

        if tiered and field in ("pet_fee_minor", "fee_basis"):
            fields[field] = {"expected": "TIERED LADDER", "captured": got,
                             "verdict": NOT_COMPARABLE,
                             "note": "the committed record carries a fee "
                                     "ladder; a flat fee and a ladder are not "
                                     "the same claim and are not compared"}
            continue

        if expected is None:
            fields[field] = {"expected": None, "captured": got,
                             "verdict": BENCHMARK_SILENT}
            continue
        if got is None:
            fields[field] = {"expected": expected, "captured": None,
                             "verdict": CAPTURE_ABSENT}
            continue
        same = (float(got) == float(expected)
                if isinstance(expected, (int, float))
                and isinstance(got, (int, float))
                and not isinstance(expected, bool) and not isinstance(got, bool)
                else got == expected)
        fields[field] = {"expected": expected, "captured": got,
                         "verdict": MATCH if same else MISMATCH}

    scored_critical = [fields[f] for f in CRITICAL_FIELDS
                       if fields[f]["verdict"] not in (BENCHMARK_SILENT,
                                                       NOT_COMPARABLE)]
    critical_exact = bool(scored_critical) and all(
        f["verdict"] == MATCH for f in scored_critical)

    collapsed = MS.collapse(block_text)
    quote_results = {}
    for quote in record.quotes:
        if quote.strip():
            quote_results[quote[:160]] = EV.quote_is_contiguous(quote, collapsed)
    reproduced = sum(1 for v in quote_results.values() if v)

    return {
        "identity_key": record.identity_key,
        "fields": fields,
        "critical_field_exactness": critical_exact,
        "scored_critical_fields": len(scored_critical),
        "mismatched_fields": sorted(k for k, v in fields.items()
                                    if v["verdict"] == MISMATCH),
        "absent_fields": sorted(k for k, v in fields.items()
                                if v["verdict"] == CAPTURE_ABSENT),
        "benchmark_quotes": len(quote_results),
        "benchmark_quotes_reproduced": reproduced,
        "policy_text_match": reproduced >= 1,
        "quote_detail": quote_results,
        "benchmark_withheld_fields": sorted(record.withheld_fields or {}),
        "contradiction_preserved": (
            all(fields[f]["verdict"] == MATCH
                for f in CRITICAL_FIELDS + EXTENDED_FIELDS
                if str(fields[f]["expected"]).startswith("ABSENT (withheld"))
            if record.withheld_fields else None),
    }


# --------------------------------------------------------------------------- #
# Observation and contracts.
# --------------------------------------------------------------------------- #

def build_observation(record: CORPUS.BenchmarkRecord,
                      target: BC.CaptureTarget, attempt: BC.AttemptRecord,
                      payload: Mapping, *, run_id: str):
    """A ``ptf-policy-observation/1.0`` record. No key is invented."""
    reading = payload["reading"]
    surface = payload["surface"]
    artifacts = payload["artifacts"]
    signals = (attempt.identity or {}).get("signals") or {}

    result = PR.to_extraction(
        reading, location="bounded policy container (%s / %s)"
                          % (surface.strategy, surface.selector or "no path"))

    identity_check = {"name_on_page": signals.get("name_on_page")
                      or attempt.title or record.name}
    for source_key, target_key in (("address_on_page", "address_on_page"),
                                   ("property_code_on_page", "property_code"),
                                   ("phone_on_page", "phone_on_page")):
        value = str(signals.get(source_key) or "").strip()
        if value:
            identity_check[target_key] = value

    html_artifact = (artifacts.get("files") or {}).get(PG.PRIMARY_ARTIFACT) or {}
    observation = {
        "obs_id": "%s::%s::attempt-%02d" % (run_id, target.slug, attempt.attempt),
        "contract_version": PO.CONTRACT_VERSION,
        "hotel_ref": target.hotel_ref(),
        "identity_check": identity_check,
        "source_url": attempt.final_url or target.requested_url,
        "source_type": "official_property_page",
        "authority_tier": PO.PT1_OFFICIAL_PROPERTY,
        "observed_at": (attempt.started_at or "")[:10],
        "retrieved_at": attempt.started_at,
        "capture_method": PG.CAPTURE_METHOD,
        "evidence": [dict(item) for item in result.evidence],
        "extraction": dict(result.extraction),
        "extraction_confidence": "EXACT_QUOTE",
        "flags": [dict(flag) for flag in result.flags],
        "snapshot_hash": html_artifact.get("sha256", ""),
        "raw_pointer": artifacts.get("attempt_dir", ""),
        "capture_artifacts": artifacts.get("files") or {},
    }
    if result.parser_warnings:
        observation["parser_warnings"] = list(result.parser_warnings)
    return observation, result


def evaluate_contracts(observation: Mapping,
                       records: Sequence[BC.AttemptRecord]) -> Dict:
    verdict = MEMBRANE.evaluate(observation)
    transcript = [{"step": "A", "attempt": r.attempt,
                   "outcome": O.LADDER_OUTCOME_MAP[r.outcome],
                   "source_attempted": r.requested_url,
                   "capture_method": PG.CAPTURE_METHOD} for r in records]
    blocked = any(e["outcome"] in ("BLOCKED_403", "BLOCKED_CHALLENGE", "TIMEOUT")
                  for e in transcript)
    exhausted = all(e["outcome"] in ("SUCCESS", "NO_POLICY_SECTION")
                    for e in transcript)
    result = READINESS.derive([observation], blocked=blocked,
                              all_surfaces_reached=exhausted)
    return {"membrane": verdict.to_dict(), "readiness": result.to_dict(),
            "ladder_transcript": transcript}


def disposition_for(attempt: BC.AttemptRecord, observation: Optional[Mapping],
                    readiness_state: str) -> str:
    if not O.may_bear_evidence(attempt.outcome) or observation is None:
        return HOLD
    pets = (observation.get("extraction") or {}).get("pets_allowed")
    if pets is False and readiness_state in (READINESS.POLICY_NEGATIVE_CONFIRMED,
                                             READINESS.POLICY_CONFIRMED):
        return VERIFIED_NO_PETS_CANDIDATE
    if pets is True and readiness_state in READINESS.PUBLISHABLE_STATES:
        return PUBLICATION_CANDIDATE
    return HOLD


# --------------------------------------------------------------------------- #
# The run.
# --------------------------------------------------------------------------- #

def _artifact_path(artifacts: Mapping, name: str) -> Optional[Path]:
    entry = (artifacts.get("files") or {}).get(name)
    return Path(entry["path"]) if entry and entry.get("path") else None


def read_journal() -> Dict[str, Dict]:
    """Property results already recorded, by slug."""
    if not PROGRESS_JOURNAL.exists():
        return {}
    out: Dict[str, Dict] = {}
    for line in PROGRESS_JOURNAL.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if entry.get("slug"):
            out[entry["slug"]] = entry
    return out


def append_journal(entry: Mapping) -> None:
    PROGRESS_JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    with PROGRESS_JOURNAL.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(client.redact(entry), ensure_ascii=False) + "\n")


def _baseline_usage(fresh: client.UsageSnapshot) -> client.UsageSnapshot:
    """The before-snapshot for the WHOLE benchmark.

    Written once and reused by every resumed leg. Measuring from the last leg's
    start would report a fraction of what the benchmark actually spent.
    """
    if BASELINE_USAGE.exists():
        try:
            stored = json.loads(BASELINE_USAGE.read_text(encoding="utf-8"))
            return client.UsageSnapshot(
                label=stored.get("label", "PILOT_USAGE_BEFORE"),
                captured_at=stored.get("captured_at", ""),
                zone=stored.get("zone", client.ZONE),
                available=bool(stored.get("available")),
                cost_month_usd_minor=stored.get("cost_month_usd_minor"),
                bandwidth_bytes=stored.get("bandwidth_bytes"),
                bandwidth_display=stored.get("bandwidth_display", ""),
                cost_display=stored.get("cost_display", ""),
                balance_usd_minor=stored.get("balance_usd_minor"),
                pending_charge_usd_minor=stored.get("pending_charge_usd_minor"),
                notes=tuple(stored.get("notes") or ()))
        except (ValueError, TypeError):
            pass
    BASELINE_USAGE.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_USAGE.write_text(json.dumps(fresh.to_dict(), indent=2),
                              encoding="utf-8")
    return fresh


async def run_pilot(*, run_id: str, sample: Sequence[CORPUS.BenchmarkRecord],
                    raw_root: Path, resume: bool = False,
                    max_properties: Optional[int] = None) -> Dict:
    """Capture the sample, journalling each property as it finishes.

    ``max_properties`` bounds one INVOCATION, not the benchmark. A thirty-
    property run outlives the process budget in this environment and was killed
    twice; a bounded batch exits cleanly instead, and ``resume`` picks up the
    rest. The sample itself is never narrowed by it -- the returned run is
    marked incomplete and no report is written from a partial pass.
    """
    raw_root.mkdir(parents=True, exist_ok=True)

    geo = await BC.probe_exit_country(reads=3, max_sessions=6)
    if not geo.ok:
        return {"run_id": run_id, "work_order": WORK_ORDER,
                "us_geo_pin": geo.to_dict(), "aborted": True,
                "abort_reason": "US exit geography could not be established; "
                                "the benchmark did not run"}

    pilot_before = _baseline_usage(client.read_usage("PILOT_USAGE_BEFORE"))
    rate = client.implied_rate_usd_minor_per_gb(pilot_before)
    started = time.monotonic()
    already = read_journal() if resume else {}
    properties: List[Dict] = []
    captured_this_invocation = 0
    incomplete = False

    for record in sample:
        target = target_for(record)
        if resume and target.slug in already:
            properties.append(already[target.slug])
            continue
        if max_properties is not None and captured_this_invocation >= max_properties:
            incomplete = True
            continue
        captured_this_invocation += 1

        property_before = client.read_usage("PROPERTY_USAGE_BEFORE::%s"
                                            % target.slug)
        began = time.monotonic()
        attempts, payload = await CBC.capture_property(
            target, run_dir=raw_root, brand=record.brand)
        elapsed = time.monotonic() - began
        property_after = client.read_usage("PROPERTY_USAGE_AFTER::%s"
                                           % target.slug)

        successful = next((a for a in attempts if a.outcome == O.VALID), None)
        estimated_bytes = sum(int((a.network or {}).get("encoded_bytes") or 0)
                              for a in attempts)
        entry: Dict = {
            "slug": target.slug, "hotel": record.name,
            "identity_key": record.identity_key, "market_id": record.market_id,
            "brand": record.brand, "bucket": record.bucket,
            "categories": sorted(record.categories),
            "benchmark_origin": record.origin,
            "requested_url": target.requested_url,
            "property_code": target.property_code,
            "attempts": [a.to_dict() for a in attempts],
            "total_attempts": len(attempts),
            "failed_attempts": sum(1 for a in attempts if a.outcome != O.VALID),
            "successful_attempt": successful.attempt if successful else None,
            "outcomes": [a.outcome for a in attempts],
            "elapsed_seconds": round(elapsed, 3),
            "successful_attempt_seconds": (round(successful.elapsed_seconds, 3)
                                           if successful else None),
            "claude_fallback_required": successful is None,
            "usage": client.delta(property_before, property_after),
            "estimated_traffic": {
                "encoded_bytes_all_attempts": estimated_bytes,
                "encoded_bytes_successful_attempt": (
                    int((successful.network or {}).get("encoded_bytes") or 0)
                    if successful else 0),
                "estimated_cost_usd_minor": ((estimated_bytes / 1e9) * rate
                                             if rate else None),
                "label": "ESTIMATED_TRAFFIC_ONLY -- browser-reported transfer, "
                         "not Bright Data billing"},
        }

        if successful is None:
            entry["disposition"] = CLAUDE_FALLBACK_REQUIRED
            entry["note"] = ("three fresh US-pinned Bright Data sessions all "
                             "failed; no artifact was written. Claude's "
                             "attended browser was NOT used -- this benchmark "
                             "measures Bright Data standalone.")
            properties.append(entry)
            append_journal(entry)
            continue

        observation, extraction_result = build_observation(
            record, target, successful, payload, run_id=run_id)
        contracts = evaluate_contracts(observation, attempts)
        artifacts = payload["artifacts"]
        surface = payload["surface"]
        html_entry = (artifacts.get("files") or {}).get(PG.PRIMARY_ARTIFACT) or {}
        grade = PG.assess(
            evidence_items=observation["evidence"],
            extraction=observation["extraction"],
            source_url=observation["source_url"],
            captured_at=successful.started_at,
            ref_prefix="%s::%s" % (run_id, target.slug),
            artifact_path=_artifact_path(artifacts, PG.PRIMARY_ARTIFACT),
            recorded_sha256=str(html_entry.get("sha256") or ""),
            page_text_path=_artifact_path(artifacts, "page-text.txt"),
            identity_confirmed=bool((successful.identity or {}).get("confirmed")))
        comparison = compare(record, extraction=observation["extraction"],
                             withheld=extraction_result.withheld,
                             block_text=payload["reading"].block_text)

        entry.update({
            "surface": surface.to_dict(),
            "disclosures_opened": payload.get("disclosures_opened") or [],
            "patterns_fired": list(payload["reading"].patterns_fired),
            "policy_block_quote": payload["reading"].block_text,
            "observation": observation,
            "withheld_fields": dict(extraction_result.withheld),
            "non_inferences": list(extraction_result.non_inferences),
            "contracts": contracts,
            "publication_grade": grade.to_dict(),
            "benchmark_comparison": comparison,
            "artifacts": artifacts,
            "identity_binding": (successful.identity or {}).get("binding"),
            "disposition": disposition_for(successful, observation,
                                           contracts["readiness"]["state"]),
        })
        properties.append(entry)
        append_journal(entry)

    pilot_after = client.read_usage("PILOT_USAGE_AFTER")
    return {
        "run_id": run_id, "work_order": WORK_ORDER, "pilot_id": PILOT_ID,
        "us_geo_pin": geo.to_dict(), "aborted": False,
        "incomplete": incomplete,
        "properties_this_invocation": captured_this_invocation,
        "properties": properties,
        "pilot_elapsed_seconds": round(time.monotonic() - started, 3),
        "usage": client.delta(pilot_before, pilot_after),
        "implied_rate_usd_minor_per_gb": rate,
        "optimization_enabled": BC.OPTIMIZATION_ENABLED,
        "optimization_note": BC.OPTIMIZATION_NOTE,
    }


def rederive_journal() -> Dict:
    """Recompute every reading from the PERSISTED block text. No network.

    The capture is the expensive, non-reproducible half; the reading is a pure
    function of bytes already on disk. When a parser defect is found after a
    run -- as one was, a house rule about unattended pets read as a blanket
    refusal -- re-deriving is the honest repair: the artifacts, their hashes and
    the attempt records are untouched, and only the interpretation of the text
    they already contain changes.

    Rewrites the journal in place and reports what moved, so a reader can see
    exactly which properties a correction affected rather than being told the
    numbers improved.
    """
    sample = {target_for(r).slug: r for r in build_sample()}
    journal = read_journal()
    changes: List[Dict] = []
    rewritten: List[Dict] = []

    for slug, entry in journal.items():
        record = sample.get(slug)
        if record is None or not entry.get("successful_attempt"):
            rewritten.append(entry)
            continue

        attempt_dict = next(a for a in entry["attempts"]
                            if a["outcome"] == O.VALID)
        attempt = BC.AttemptRecord(
            attempt=attempt_dict["attempt"], outcome=O.VALID,
            started_at=attempt_dict["started_at"],
            ended_at=attempt_dict["ended_at"],
            elapsed_seconds=float(attempt_dict["elapsed_seconds"]),
            requested_url=attempt_dict["requested_url"],
            final_url=attempt_dict.get("final_url", ""),
            title=attempt_dict.get("title", ""),
            body_chars=int(attempt_dict.get("body_chars") or 0),
            identity=attempt_dict.get("identity"),
            network=attempt_dict.get("network"),
            artifact_dir=attempt_dict.get("artifact_dir", ""))
        surface_dict = entry.get("surface") or {}
        surface = PS.SurfaceHit(
            found=bool(surface_dict.get("found")),
            text=entry.get("policy_block_quote", ""),
            strategy=surface_dict.get("strategy", ""),
            selector=surface_dict.get("selector", ""),
            matched_phrase=surface_dict.get("matched_phrase", ""),
            container_chars=int(surface_dict.get("container_chars") or 0),
            policy_features=int(surface_dict.get("policy_features") or 0),
            brand_generic=bool(surface_dict.get("brand_generic")))
        reading = PR.parse(entry.get("policy_block_quote", ""),
                           strategy=surface.strategy)
        payload = {"reading": reading, "surface": surface,
                   "artifacts": entry.get("artifacts") or {}}

        before = dict((entry.get("observation") or {}).get("extraction") or {})
        observation, result = build_observation(
            record, target_for(record), attempt, payload,
            run_id=(entry.get("observation") or {}).get("obs_id", "").split("::")[0]
            or "REDERIVED")
        contracts = evaluate_contracts(observation, [attempt])
        artifacts = entry.get("artifacts") or {}
        html_entry = (artifacts.get("files") or {}).get(PG.PRIMARY_ARTIFACT) or {}
        grade = PG.assess(
            evidence_items=observation["evidence"],
            extraction=observation["extraction"],
            source_url=observation["source_url"],
            captured_at=attempt.started_at,
            ref_prefix="rederived::%s" % slug,
            artifact_path=_artifact_path(artifacts, PG.PRIMARY_ARTIFACT),
            recorded_sha256=str(html_entry.get("sha256") or ""),
            page_text_path=_artifact_path(artifacts, "page-text.txt"),
            identity_confirmed=bool((attempt.identity or {}).get("confirmed")))
        comparison = compare(record, extraction=observation["extraction"],
                             withheld=result.withheld,
                             block_text=reading.block_text)

        if before != observation["extraction"]:
            changes.append({"slug": slug, "hotel": entry.get("hotel"),
                            "before": before,
                            "after": dict(observation["extraction"]),
                            "grade_before": (entry.get("publication_grade")
                                             or {}).get("verdict"),
                            "grade_after": grade.verdict})
        entry.update({
            "patterns_fired": list(reading.patterns_fired),
            "observation": observation,
            "withheld_fields": dict(result.withheld),
            "non_inferences": list(result.non_inferences),
            "contracts": contracts,
            "publication_grade": grade.to_dict(),
            "benchmark_comparison": comparison,
            "rederived": True,
        })
        rewritten.append(entry)

    PROGRESS_JOURNAL.write_text(
        "".join(json.dumps(client.redact(e), ensure_ascii=False) + chr(10)
                for e in rewritten), encoding="utf-8")
    return {"properties": len(rewritten), "changed": changes}


# --------------------------------------------------------------------------- #
# Metrics.
# --------------------------------------------------------------------------- #

def _brand_metrics(properties: Sequence[Mapping], bucket: str) -> Dict:
    rows = [p for p in properties if p.get("bucket") == bucket]
    ok = [p for p in rows if p.get("successful_attempt")]
    comparisons = [p.get("benchmark_comparison") or {} for p in ok]
    grades = [p.get("publication_grade") or {} for p in ok]
    attempts = sum(int(p.get("total_attempts") or 0) for p in rows)
    est = sum(int((p.get("estimated_traffic") or {}).get(
        "encoded_bytes_all_attempts") or 0) for p in rows)
    zone_cost = sum(int((p.get("usage") or {}).get("cost_delta_usd_minor") or 0)
                    for p in rows)
    return {
        "bucket": bucket,
        "total": len(rows),
        "fetch_success": len(ok),
        "identity_match": sum(
            1 for p in ok
            if ((next((a for a in p["attempts"] if a["outcome"] == O.VALID), {})
                 or {}).get("identity") or {}).get("confirmed")),
        "policy_found": sum(1 for p in ok if (p.get("surface") or {}).get("found")),
        "policy_text_match": sum(1 for c in comparisons
                                 if c.get("policy_text_match")),
        "critical_field_match": sum(1 for c in comparisons
                                    if c.get("critical_field_exactness")),
        "publication_grade_confirmed": sum(
            1 for g in grades if g.get("verdict") == PG.CONFIRMED),
        "fallback_required": sum(1 for p in rows
                                 if p.get("claude_fallback_required")),
        "total_attempts": attempts,
        "failed_attempts": sum(int(p.get("failed_attempts") or 0) for p in rows),
        "avg_attempts": round(attempts / len(rows), 2) if rows else 0,
        "avg_seconds": round(sum(float(p.get("elapsed_seconds") or 0)
                                 for p in rows) / len(rows), 1) if rows else 0,
        "zone_cost_usd_minor": zone_cost,
        "estimated_traffic_bytes": est,
        "outcomes": dict(collections.Counter(
            o for p in rows for o in (p.get("outcomes") or ()))),
    }


def adapter_observations(properties: Sequence[Mapping]) -> Dict[str, Dict]:
    """Per brand, the pattern that actually worked.

    This is the evidence an adapter decision rests on. It is COLLECTED, not
    designed: every field is a tally of what the generic strategy did, so a
    brand that needed no help and a brand that needed three interactions look
    different in the report rather than the same.
    """
    out: Dict[str, Dict] = {}
    for bucket in CORPUS.BUCKETS:
        rows = [p for p in properties if p.get("bucket") == bucket]
        ok = [p for p in rows if p.get("successful_attempt")]
        strategies = collections.Counter(
            (p.get("surface") or {}).get("strategy") for p in ok)
        phrases = collections.Counter(
            (p.get("surface") or {}).get("matched_phrase") for p in ok)
        patterns = collections.Counter(
            pattern for p in ok for pattern in (p.get("patterns_fired") or ()))
        disclosures = collections.Counter(
            control.split(":")[0]
            for p in ok for control in (p.get("disclosures_opened") or ()))
        hydration = sum(
            1 for p in ok
            for a in p["attempts"] if a["outcome"] == O.VALID
            and any("signal phrase appeared" in step
                    for step in a.get("interactions") or ()))
        blocks = [int((p.get("surface") or {}).get("container_chars") or 0)
                  for p in ok]
        out[bucket] = {
            "captured": len(ok),
            "locator_strategies": dict(strategies),
            "matched_signal_phrases": dict(phrases),
            "parser_patterns_fired": dict(patterns),
            "disclosure_controls_opened": dict(disclosures),
            "hydrated_before_timeout": hydration,
            "policy_block_chars_min": min(blocks) if blocks else None,
            "policy_block_chars_max": max(blocks) if blocks else None,
            "brand_generic_blocks": sum(
                1 for p in ok if (p.get("surface") or {}).get("brand_generic")),
            "identity_bindings": dict(collections.Counter(
                p.get("identity_binding") for p in ok)),
            "property_code_available": sum(1 for p in rows
                                           if p.get("property_code")),
            "failure_outcomes": dict(collections.Counter(
                o for p in rows for o in (p.get("outcomes") or ())
                if o != O.VALID)),
        }
    return out


def field_verdict_tallies(properties: Sequence[Mapping]) -> Dict:
    """Field-level precision and recall, kept apart on purpose.

    The per-property ``critical_field_exactness`` flag is all-or-nothing: one
    field the reader did not find drops the whole property. That is the right
    gate for "could this record be published as-is", and the wrong number for
    "did the reader get anything WRONG", because it scores a miss and a
    contradiction identically.

    So both are reported. PRECISION is agreement where the reader produced a
    value; RECALL is how much of the benchmark it produced at all. A reader
    with perfect precision and partial recall is a coverage problem, which an
    adapter fixes. A reader with imperfect precision is a correctness problem,
    which no adapter fixes.
    """
    per_field: Dict[str, Dict[str, int]] = {}
    for prop in properties:
        comparison = prop.get("benchmark_comparison") or {}
        for field, result in (comparison.get("fields") or {}).items():
            bucket = per_field.setdefault(field, collections.Counter())
            bucket[result.get("verdict")] += 1

    def rollup(fields: Sequence[str]) -> Dict:
        match = sum(per_field.get(f, {}).get(MATCH, 0) for f in fields)
        mismatch = sum(per_field.get(f, {}).get(MISMATCH, 0) for f in fields)
        absent = sum(per_field.get(f, {}).get(CAPTURE_ABSENT, 0) for f in fields)
        produced = match + mismatch
        recoverable = match + mismatch + absent
        return {
            "match": match, "mismatch": mismatch, "capture_absent": absent,
            "precision_percent": (round(100.0 * match / produced, 1)
                                  if produced else None),
            "recall_percent": (round(100.0 * match / recoverable, 1)
                               if recoverable else None),
        }

    return {
        "per_field": {f: dict(v) for f, v in sorted(per_field.items())},
        "critical": rollup(CRITICAL_FIELDS),
        "extended": rollup(EXTENDED_FIELDS),
        "all": rollup(CRITICAL_FIELDS + EXTENDED_FIELDS),
    }


def summarize(run: Mapping) -> Dict:
    properties = list(run.get("properties") or ())
    total = len(properties)
    ok = [p for p in properties if p.get("successful_attempt")]
    comparisons = [p.get("benchmark_comparison") or {} for p in ok]
    grades = [p.get("publication_grade") or {} for p in ok]

    attempts = sum(int(p.get("total_attempts") or 0) for p in properties)
    failed = sum(int(p.get("failed_attempts") or 0) for p in properties)
    est_all = sum(int((p.get("estimated_traffic") or {}).get(
        "encoded_bytes_all_attempts") or 0) for p in properties)
    est_ok = sum(int((p.get("estimated_traffic") or {}).get(
        "encoded_bytes_successful_attempt") or 0) for p in properties)
    rate = run.get("implied_rate_usd_minor_per_gb")
    zone = (run.get("usage") or {})
    zone_cost = zone.get("cost_delta_usd_minor")

    failed_share = (est_all - est_ok) / est_all if est_all else 0.0
    contradiction_rows = [c for c in comparisons
                          if c.get("contradiction_preserved") is not None]

    return {
        "schema": "ptf-brightdata-cross-brand-summary/1.0",
        "work_order": WORK_ORDER, "pilot_id": PILOT_ID,
        "run_id": run.get("run_id"),
        "us_geo_pin": ("PASS" if (run.get("us_geo_pin") or {}).get("ok")
                       else "FAIL"),
        "us_geo_detail": (run.get("us_geo_pin") or {}).get("detail"),
        "total": total,
        "fetch_success": len(ok),
        "identity_match": sum(
            1 for p in ok
            if ((next((a for a in p["attempts"] if a["outcome"] == O.VALID), {})
                 or {}).get("identity") or {}).get("confirmed")),
        "policy_found": sum(1 for p in ok if (p.get("surface") or {}).get("found")),
        "policy_text_match": sum(1 for c in comparisons
                                 if c.get("policy_text_match")),
        "critical_field_match": sum(1 for c in comparisons
                                    if c.get("critical_field_exactness")),
        "field_verdicts": field_verdict_tallies(properties),
        "critical_field_mismatches": sum(
            1 for c in comparisons
            for f in (c.get("mismatched_fields") or ())
            if f in CRITICAL_FIELDS),
        "publication_grade_confirmed": sum(
            1 for g in grades if g.get("verdict") == PG.CONFIRMED),
        "publication_grade_among_valid": (
            round(100.0 * sum(1 for g in grades
                              if g.get("verdict") == PG.CONFIRMED) / len(ok), 1)
            if ok else None),
        "claude_fallback_required": sum(
            1 for p in properties if p.get("claude_fallback_required")),
        "verified_no_pets_candidates": sum(
            1 for p in properties
            if p.get("disposition") == VERIFIED_NO_PETS_CANDIDATE),
        "false_verified_no_pets": sum(
            1 for p in properties
            if p.get("disposition") == VERIFIED_NO_PETS_CANDIDATE
            and (p.get("observation") or {}).get(
                "extraction", {}).get("pets_allowed") is not False),
        "contradictions_expected": len(contradiction_rows),
        "contradictions_preserved": sum(
            1 for c in contradiction_rows if c.get("contradiction_preserved")),
        "benchmark_quotes_reproduced": sum(
            int(c.get("benchmark_quotes_reproduced") or 0) for c in comparisons),
        "benchmark_quotes_total": sum(
            int(c.get("benchmark_quotes") or 0) for c in comparisons),
        "brand_generic_blocks": sum(
            1 for p in ok if (p.get("surface") or {}).get("brand_generic")),
        "total_attempts": attempts,
        "failed_attempts": failed,
        "avg_attempts_per_property": round(attempts / total, 3) if total else 0,
        "avg_seconds_per_property": round(
            sum(float(p.get("elapsed_seconds") or 0)
                for p in properties) / total, 1) if total else 0,
        "avg_seconds_per_successful_property": round(
            sum(float(p.get("successful_attempt_seconds") or 0)
                for p in ok) / len(ok), 1) if ok else None,
        "pilot_elapsed_seconds": run.get("pilot_elapsed_seconds"),
        "brightdata_reported": zone,
        "run_cost_usd_minor": zone_cost,
        "cost_status": zone.get("cost_status"),
        "avg_cost_per_property_usd_minor": (round(zone_cost / total, 2)
                                            if zone_cost and total else None),
        "avg_cost_per_successful_property_usd_minor": (
            round(zone_cost / len(ok), 2) if zone_cost and ok else None),
        "cost_of_failed_attempts_usd_minor": (
            round(zone_cost * failed_share, 2) if zone_cost else None),
        "percent_cost_from_failed_attempts": round(100.0 * failed_share, 1),
        "estimated_traffic_bytes": est_all,
        "estimated_traffic_cost_usd_minor": (round((est_all / 1e9) * rate, 2)
                                             if rate else None),
        "implied_rate_usd_minor_per_gb": round(rate, 2) if rate else None,
        "rendered_html": sum(1 for p in ok
                             if PG.PRIMARY_ARTIFACT in
                             ((p.get("artifacts") or {}).get("files") or {})),
        "full_page_screenshot": sum(
            1 for p in ok if "full-page.png" in
            ((p.get("artifacts") or {}).get("files") or {})),
        "policy_section_screenshot": sum(
            1 for p in ok if "policy-section.png" in
            ((p.get("artifacts") or {}).get("files") or {})),
        "hash_validation": sum(1 for g in grades if g.get("hash_rederived")),
        "brands": {b: _brand_metrics(properties, b) for b in CORPUS.BUCKETS},
        "adapter_observations": adapter_observations(properties),
        "contract_integration_gaps": (
            grades[0].get("contract_integration_gaps") if grades
            else [g.to_dict() for g in PG.detect_gaps()]),
        "optimization_enabled": run.get("optimization_enabled"),
        "policy_authority_changed": False,
        "exclusions_changed": False,
        "seed_changed": False,
        "approvals_changed": False,
        "partition_changed": False,
        "routing_authority_changed": False,
        "promotion_performed": False,
        "promotion_note": ("this benchmark stops before founder review. "
                           "Nothing here writes to a market authority and no "
                           "disposition above is a decision."),
    }


# --------------------------------------------------------------------------- #
# Reports.
# --------------------------------------------------------------------------- #

def _write_json(path: Path, payload: Mapping) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(client.redact(payload), indent=2,
                               ensure_ascii=False) + "\n", encoding="utf-8")


def render_brand_markdown(run: Mapping, summary: Mapping) -> str:
    lines = [
        "# %s -- Bright Data across six brand buckets" % WORK_ORDER,
        "",
        "Run `%s`. US exit pin: **%s** (%s)."
        % (run.get("run_id"), summary.get("us_geo_pin"),
           summary.get("us_geo_detail")),
        "",
        "Benchmark: this repository's own founder-reviewed policy records and "
        "exclusion registries, read only after every artifact was on disk.",
        "",
        "| Bucket | Fetch | Identity | Policy | Text | Critical | Pub grade | "
        "Fallback | Attempts | Avg s | Zone cost |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for bucket in CORPUS.BUCKETS:
        m = summary["brands"][bucket]
        lines.append("| %s | %d/%d | %d | %d | %d | %d | %d | %d | %d | %.0f | $%.2f |"
                     % (bucket, m["fetch_success"], m["total"],
                        m["identity_match"], m["policy_found"],
                        m["policy_text_match"], m["critical_field_match"],
                        m["publication_grade_confirmed"],
                        m["fallback_required"], m["total_attempts"],
                        m["avg_seconds"], m["zone_cost_usd_minor"] / 100.0))

    tallies = summary.get("field_verdicts") or {}
    critical = tallies.get("critical") or {}
    lines += ["", "## Field-level precision and recall", "",
              "The per-property column above is all-or-nothing: one field the "
              "reader did not find drops the whole property. These two numbers "
              "separate *wrong* from *not found*, which is the difference "
              "between a correctness problem and a coverage problem.", "",
              "| Set | Matched | Mismatched | Not found | Precision | Recall |",
              "| --- | --- | --- | --- | --- | --- |"]
    for label, key in (("critical", "critical"), ("extended", "extended"),
                       ("all", "all")):
        roll = tallies.get(key) or {}
        lines.append("| %s | %s | %s | %s | %s%% | %s%% |"
                     % (label, roll.get("match"), roll.get("mismatch"),
                        roll.get("capture_absent"), roll.get("precision_percent"),
                        roll.get("recall_percent")))

    lines += ["", "## Adapter observations", "",
              "What the ONE generic strategy actually did, per brand. An "
              "adapter is justified where this shows the generic path "
              "struggling, and is not where it shows the generic path "
              "working.", ""]
    for bucket in CORPUS.BUCKETS:
        obs = summary["adapter_observations"][bucket]
        lines += ["### %s" % bucket, "",
                  "- captured: %d of %d" % (obs["captured"], PER_BUCKET),
                  "- locator strategies: %s" % (obs["locator_strategies"] or "-"),
                  "- signal phrases matched: %s"
                  % (obs["matched_signal_phrases"] or "-"),
                  "- disclosure controls opened: %s"
                  % (obs["disclosure_controls_opened"] or "none needed"),
                  "- hydrated before the signal timeout: %d of %d"
                  % (obs["hydrated_before_timeout"], obs["captured"]),
                  "- policy block size: %s-%s chars"
                  % (obs["policy_block_chars_min"], obs["policy_block_chars_max"]),
                  "- brand-generic blocks: %d" % obs["brand_generic_blocks"],
                  "- identity binding: %s" % (obs["identity_bindings"] or "-"),
                  "- property code in URL: %d of %d"
                  % (obs["property_code_available"], PER_BUCKET),
                  "- parser patterns fired: %s" % (obs["parser_patterns_fired"] or "-"),
                  "- failure outcomes: %s" % (obs["failure_outcomes"] or "none"),
                  ""]

    lines += ["", "## Properties", "",
              "| Bucket | Property | Outcome(s) | Locator | Critical | Pub grade "
              "| Disposition |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for prop in run.get("properties") or ():
        comparison = prop.get("benchmark_comparison") or {}
        grade = prop.get("publication_grade") or {}
        lines.append("| %s | %s | %s | %s | %s | %s | %s |" % (
            prop.get("bucket"), prop.get("hotel", "")[:44],
            ", ".join(prop.get("outcomes") or []),
            (prop.get("surface") or {}).get("strategy", "-"),
            ("exact" if comparison.get("critical_field_exactness")
             else ", ".join(comparison.get("mismatched_fields")
                            or comparison.get("absent_fields") or ["-"])
             if comparison else "-"),
            grade.get("verdict", "-"), prop.get("disposition")))

    lines += ["", "## Authority", "",
              "POLICY_AUTHORITY_CHANGED: NO  ", "EXCLUSIONS_CHANGED: NO  ",
              "SEED_CHANGED: NO  ", "APPROVALS_CHANGED: NO  ",
              "PARTITION_CHANGED: NO  ", "ROUTING_AUTHORITY_CHANGED: NO", ""]
    return "\n".join(lines)


def write_reports(run: Mapping, summary: Mapping,
                  sample: Sequence[CORPUS.BenchmarkRecord]) -> Dict[str, str]:
    _write_json(SAMPLE_REPORT, {
        "schema": "ptf-brightdata-cross-brand-sample/1.0",
        "work_order": WORK_ORDER, "pilot_size": PILOT_SIZE,
        "per_bucket": PER_BUCKET, "minimums": SAMPLE_MINIMUMS,
        "excluded_brands": sorted(CORPUS.EXCLUDED_BRANDS),
        "coverage": CORPUS.coverage(sample),
        "properties": [r.to_dict() for r in sample]})
    _write_json(SUMMARY_REPORT, summary)
    _write_json(PROPERTY_REPORT, {
        "schema": "ptf-brightdata-cross-brand-properties/1.0",
        "work_order": WORK_ORDER, "run_id": run.get("run_id"),
        "properties": run.get("properties") or []})
    BRAND_REPORT.parent.mkdir(parents=True, exist_ok=True)
    BRAND_REPORT.write_text(client.redact(render_brand_markdown(run, summary)),
                            encoding="utf-8")
    return {"sample": str(SAMPLE_REPORT), "summary": str(SUMMARY_REPORT),
            "properties": str(PROPERTY_REPORT), "brands": str(BRAND_REPORT)}


def default_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--raw-root", default=str(RAW_ROOT))
    parser.add_argument("--only-bucket", action="append", default=None,
                        help="restrict to one bucket; repeatable. Narrowing is "
                             "allowed for debugging, widening is not.")
    parser.add_argument("--resume", action="store_true",
                        help="skip properties already in the progress journal "
                             "and reuse the first leg's usage baseline")
    parser.add_argument("--max-properties", type=int, default=None,
                        help="bound ONE invocation to N new captures and exit "
                             "cleanly; --resume continues the rest")
    parser.add_argument("--rederive", action="store_true",
                        help="recompute every reading from the persisted block "
                             "text and rewrite the journal; no network")
    parser.add_argument("--geo-check-only", action="store_true",
                        help="verify the US exit pin and stop")
    parser.add_argument("--no-reports", action="store_true")
    args = parser.parse_args(argv)

    if not client.credential_present():
        print("ERROR: %s is not set." % client.AUTH_ENV, file=sys.stderr)
        return 2

    if args.rederive:
        result = rederive_journal()
        print("re-derived %d journalled properties from persisted text"
              % result["properties"])
        for change in result["changed"]:
            print("  CHANGED %s" % change["hotel"])
            print("     before: %s" % json.dumps(change["before"], sort_keys=True))
            print("     after : %s" % json.dumps(change["after"], sort_keys=True))
            print("     grade : %s -> %s" % (change["grade_before"],
                                             change["grade_after"]))
        if not result["changed"]:
            print("  no reading changed")
        return 0

    if args.geo_check_only:
        geo = asyncio.run(BC.probe_exit_country(reads=3, max_sessions=6))
        print(json.dumps(geo.to_dict(), indent=2))
        print("US_GEO_PIN: %s" % ("PASS" if geo.ok else "FAIL"))
        return 0 if geo.ok else 1

    sample = build_sample()
    if args.only_bucket:
        wanted = set(args.only_bucket)
        sample = tuple(r for r in sample if r.bucket in wanted)

    run_id = args.run_id or default_run_id()
    run = asyncio.run(run_pilot(run_id=run_id, sample=sample,
                                raw_root=Path(args.raw_root),
                                resume=args.resume,
                                max_properties=args.max_properties))
    if run.get("aborted"):
        print("ABORTED: %s" % run.get("abort_reason"), file=sys.stderr)
        print("US_GEO_PIN: FAIL")
        return 1

    if run.get("incomplete"):
        done = len(read_journal())
        print("BATCH DONE: %d new this invocation, %d of %d journalled. "
              "Re-run with --resume to continue; no report written from a "
              "partial pass." % (run.get("properties_this_invocation"), done,
                                 PILOT_SIZE))
        return 0

    summary = summarize(run)
    if not args.no_reports:
        for label, path in write_reports(run, summary, sample).items():
            print("wrote %s -> %s" % (label, path))
    print(json.dumps({k: v for k, v in summary.items()
                      if k not in ("brands", "adapter_observations",
                                   "contract_integration_gaps",
                                   "brightdata_reported")}, indent=2))
    return 0


__all__ = [
    "WORK_ORDER", "PILOT_ID", "PILOT_SIZE", "PER_BUCKET", "SAMPLE_MINIMUMS",
    "CRITICAL_FIELDS", "EXTENDED_FIELDS", "MATCH", "MISMATCH", "CAPTURE_ABSENT",
    "BENCHMARK_SILENT", "NOT_COMPARABLE", "CLAUDE_FALLBACK_REQUIRED",
    "PUBLICATION_CANDIDATE", "VERIFIED_NO_PETS_CANDIDATE", "HOLD", "PilotError",
    "PROGRESS_JOURNAL", "BASELINE_USAGE", "read_journal", "append_journal",
    "build_sample", "target_for", "compare", "build_observation",
    "evaluate_contracts", "disposition_for", "run_pilot", "summarize",
    "rederive_journal",
    "adapter_observations", "field_verdict_tallies", "write_reports",
    "render_brand_markdown", "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
